import json
import logging
import pprint
import re
from dataclasses import dataclass
from typing import List, Optional

import voluptuous as vol
from databricks_cli.jobs.api import JobsApi
from databricks_cli.runs.api import RunsApi
from databricks_cli.sdk import ApiClient

from runway import util
from runway.ApplicationVersion import ApplicationVersion
from runway.DeploymentStep import DeploymentStep
from runway.azure.credentials.databricks import Databricks
from runway.credentials.application_name import ApplicationName
from runway.schemas import RUNWAY_BASE_SCHEMA
from runway.util import has_prefix_match, get_whl_name, get_main_py_name

logger = logging.getLogger(__name__)

SCHEMA = RUNWAY_BASE_SCHEMA.extend(
    {
        vol.Required("task"): "deployToDatabricks",
        vol.Required("jobs"): vol.All(
            [
                {
                    vol.Required("main_name"): str,
                    vol.Optional("config_file", default="databricks.json.j2"): str,
                    vol.Optional("name", default=""): str,
                    vol.Optional("lang", default="python"): vol.All(str, vol.In(["python", "scala"])),
                    vol.Optional("arguments", default=[{}]): [{}],
                    vol.Optional("schedule"): {
                        vol.Required("quartz_cron_expression"): str,
                        vol.Required("timezone_id"): str,
                    },
                }
            ],
            vol.Length(min=1),
        ),
    },
    extra=vol.ALLOW_EXTRA,
)


@dataclass(frozen=True)
class JobConfig(object):
    name: str
    job_id: int


class DeployToDatabricks(DeploymentStep):
    def __init__(self, env: ApplicationVersion, config: dict):
        super().__init__(env, config)

    def schema(self) -> vol.Schema:
        return SCHEMA

    def run(self):
        self.deploy_to_databricks()

    @staticmethod
    def _job_is_streaming(job_config: dict):
        """
        If there is no schedule, the job would not run periodically, therefore we assume that is a
        streaming job
        :param job_config: the configuration of the Databricks job
        :return: (bool) if it is a streaming job
        """
        return "schedule" not in job_config.keys()

    def deploy_to_databricks(self):
        """
        The application parameters (cosmos and eventhub) will be removed from this file as they
        will be set as databricks secrets eventually
        If the job is a streaming job this will directly start the new job_run given the new
        configuration. If the job is batch this will not start it manually, assuming the schedule
        has been set correctly.
        """

        application_name = ApplicationName().get(self.config)
        databricks_client = Databricks(self.vault_name, self.vault_client).api_client(self.config)

        for job in self.config["jobs"]:
            app_name = self._construct_name(job["name"])
            job_name = f"{app_name}-{self.env.artifact_tag}"
            job_config = self._create_config(job_name, job, application_name)
            is_streaming = self._job_is_streaming(job_config)

            logger.info("Removing old job")
            self.__remove_job(databricks_client, app_name, self.env.artifact_tag, is_streaming=is_streaming)

            logger.info("Submitting new job with configuration:")
            logger.info(pprint.pformat(job_config))
            self._submit_job(databricks_client, job_config, is_streaming)

    def _create_config(self, job_name: str, job_config: dict, application_name: str):
        common_arguments = dict(
            config_file=job_config["config_file"],
            application_name=job_name,
            log_destination=job_name,
            parameters=self._construct_arguments(job_config["arguments"]),
            schedule=self._get_schedule(job_config),
        )

        root_library_folder = self.config["runway_common"]["databricks_library_path"]
        storage_base_path = f"{root_library_folder}/{application_name}"
        artifact_path = f"{storage_base_path}/{application_name}-{self.env.artifact_tag}"

        build_definition_name = ApplicationName().get(self.config)
        if job_config["lang"] == "python":
            wheel_name = get_whl_name(build_definition_name, self.env.artifact_tag, ".whl")
            py_main_name = get_main_py_name(build_definition_name, self.env.artifact_tag, ".py")
            run_config = DeployToDatabricks._construct_job_config(
                **common_arguments,
                whl_file=f"{root_library_folder}/{wheel_name}",
                python_file=f"{root_library_folder}/{py_main_name}",
            )
        else:  # java/scala jobs
            run_config = DeployToDatabricks._construct_job_config(
                **common_arguments, class_name=job_config["main_name"], jar_file=f"{artifact_path}.jar"
            )
        return run_config

    def _get_schedule(self, job_config: dict) -> Optional[dict]:
        schedule = job_config.get("schedule", None)
        if schedule:
            if "quartz_cron_expression" in schedule:
                return schedule
            else:
                return schedule.get(self.env.environment.lower(), None)

        return schedule

    def _construct_name(self, name) -> str:
        postfix = f"-{name}" if name else ""
        return f"{ApplicationName().get(self.config)}{postfix}"

    @staticmethod
    def _construct_arguments(args: List[dict]) -> list:
        params = []
        for named_arguments_pair in args:
            for k, v in named_arguments_pair.items():
                params.extend([f"--{k}", v])

        return params

    @staticmethod
    def _construct_job_config(config_file: str, **kwargs) -> dict:
        return util.render_file_with_jinja(config_file, kwargs, json.loads)

    @staticmethod
    def __remove_job(client, application_name: str, branch: str, is_streaming: bool):
        """
        Removes the existing job and cancels any running job_run if the application is streaming.
        If the application is batch, it'll let the batch job finish but it will remove the job,
        making sure no other job_runs can start for that old job.
        """
        jobs_api = JobsApi(client)
        runs_api = RunsApi(client)

        job_configs = [JobConfig(_["settings"]["name"], _["job_id"]) for _ in jobs_api.list_jobs()["jobs"]]
        job_ids = DeployToDatabricks._application_job_id(application_name, branch, job_configs)

        if not job_ids:
            logger.info(f"Could not find jobs in list of {pprint.pformat(job_configs)}")

        for job_id in job_ids:
            logger.info(f"Found Job with ID {job_id} and removing it")
            if is_streaming:
                DeployToDatabricks._kill_it_with_fire(runs_api, job_id)
            jobs_api.delete_job(job_id)

    @staticmethod
    def _application_job_id(application_name: str, branch: str, jobs: List[JobConfig]) -> List[int]:
        snapshot = "SNAPSHOT"
        tag = "\d+\.\d+\.\d+"
        pattern = re.compile(rf"^({application_name})-({snapshot}|{tag}|{branch})$")

        return [_.job_id for _ in jobs if has_prefix_match(_.name, application_name, pattern)]

    @staticmethod
    def _kill_it_with_fire(runs_api, job_id):
        runs = runs_api.list_runs(job_id, active_only=True, completed_only=None, offset=None, limit=None)
        # If the runs is empty, there are no jobs at all
        # TODO: Check if the has_more flag is true, this means we need to go over the pages
        if "runs" in runs:
            active_run_ids = [_["run_id"] for _ in runs["runs"]]
            [runs_api.cancel_run(_) for _ in active_run_ids]

    @staticmethod
    def _submit_job(client: ApiClient, job_config: dict, is_streaming: bool):
        jobs_api = JobsApi(client)
        job_resp = jobs_api.create_job(job_config)

        if is_streaming:
            jobs_api.run_now(
                job_id=job_resp["job_id"],
                jar_params=None,
                notebook_params=None,
                python_params=None,
                spark_submit_params=None,
            )
