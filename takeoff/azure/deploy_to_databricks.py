import json
import logging
import pprint
import re
from dataclasses import dataclass
from typing import List, Optional

import voluptuous as vol
from databricks_cli.jobs.api import JobsApi
from databricks_cli.runs.api import RunsApi

from takeoff import util
from takeoff.application_version import ApplicationVersion
from takeoff.azure.credentials.databricks import Databricks
from takeoff.azure.credentials.keyvault import KeyVaultClient
from takeoff.schemas import TAKEOFF_BASE_SCHEMA
from takeoff.step import Step
from takeoff.util import has_prefix_match, get_whl_name, get_main_py_name

logger = logging.getLogger(__name__)

SCHEMA = TAKEOFF_BASE_SCHEMA.extend(
    {
        vol.Required("task"): "deploy_to_databricks",
        vol.Required("jobs"): vol.All(
            [
                {
                    vol.Required("main_name"): str,
                    vol.Optional("config_file", default="databricks.json.j2"): str,
                    vol.Optional("name", default=""): str,
                    vol.Optional("lang", default="python"): vol.All(str, vol.In(["python", "scala"])),
                    vol.Optional("run_immediately", default=True): bool,
                    vol.Optional("arguments", default=[{}]): [{}],
                    vol.Optional("schedule"): {
                        vol.Required("quartz_cron_expression"): str,
                        vol.Required("timezone_id"): str,
                    },
                }
            ],
            vol.Length(min=1),
        ),
        "common": {vol.Optional("databricks_fs_libraries_mount_path"): str},
    },
    extra=vol.ALLOW_EXTRA,
)


@dataclass(frozen=True)
class JobConfig(object):
    name: str
    job_id: int


class DeployToDatabricks(Step):
    def __init__(self, env: ApplicationVersion, config: dict):
        super().__init__(env, config)
        self.vault_name, self.vault_client = KeyVaultClient.vault_and_client(self.config, self.env)
        self.databricks_client = Databricks(self.vault_name, self.vault_client).api_client(self.config)
        self.jobs_api = JobsApi(self.databricks_client)
        self.runs_api = RunsApi(self.databricks_client)

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
        for job in self.config["jobs"]:
            app_name = self._construct_name(job["name"])
            job_name = f"{app_name}-{self.env.artifact_tag}"
            job_config = self.create_config(job_name, job)
            is_streaming = self._job_is_streaming(job_config)
            run_immediately = job["run_immediately"]

            logger.info("Removing old job")
            self.remove_job(self.env.artifact_tag, job_config=job, is_streaming=is_streaming)

            logger.info("Submitting new job with configuration:")
            logger.info(pprint.pformat(job_config))
            self._submit_job(job_config, is_streaming, run_immediately)

    def create_config(self, job_name: str, job_config: dict):
        common_arguments = dict(
            config_file=job_config["config_file"],
            application_name=job_name,
            log_destination=job_name,
            parameters=self._construct_arguments(job_config["arguments"]),
            schedule=self._get_schedule(job_config),
            environment=self.env.environment_formatted,
        )

        root_library_folder = self.config["common"]["databricks_fs_libraries_mount_path"]
        storage_base_path = f"{root_library_folder}/{self.application_name}"
        artifact_path = f"{storage_base_path}/{self.application_name}-{self.env.artifact_tag}"

        if job_config["lang"] == "python":
            wheel_name = get_whl_name(self.application_name, self.env.artifact_tag, ".whl")
            py_main_name = get_main_py_name(self.application_name, self.env.artifact_tag, ".py")
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

    def _construct_name(self, name: str) -> str:
        postfix = f"-{name}" if name else ""
        return f"{self.application_name}{postfix}"

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

    def remove_job(self, branch: str, job_config: dict, is_streaming: bool):
        """
        Removes the existing job and cancels any running job_run if the application is streaming.
        If the application is batch, it'll let the batch job finish but it will remove the job,
        making sure no other job_runs can start for that old job.
        """

        job_configs = [
            JobConfig(_["settings"]["name"], _["job_id"]) for _ in self.jobs_api.list_jobs()["jobs"]
        ]
        job_ids = self._application_job_id(self._construct_name(job_config["name"]), branch, job_configs)

        if not job_ids:
            logger.info(f"Could not find jobs in list of {pprint.pformat(job_configs)}")

        for job_id in job_ids:
            logger.info(f"Found Job with ID {job_id}")
            if is_streaming:
                self._kill_it_with_fire(job_id)
            logger.info(f"Deleting Job with ID {job_id}")
            self.jobs_api.delete_job(job_id)

    @staticmethod
    def _application_job_id(application_name: str, branch: str, jobs: List[JobConfig]) -> List[int]:
        snapshot = "SNAPSHOT"
        tag = "\d+\.\d+\.\d+"
        pattern = re.compile(rf"^({application_name})-({snapshot}|{tag}|{branch})$")

        return [_.job_id for _ in jobs if has_prefix_match(_.name, application_name, pattern)]

    def _kill_it_with_fire(self, job_id):
        logger.info(f"Finding runs for job_id {job_id}")
        runs = self.runs_api.list_runs(job_id, active_only=True, completed_only=None, offset=None, limit=None)
        # If the runs is empty, there are no jobs at all
        # TODO: Check if the has_more flag is true, this means we need to go over the pages
        if "runs" in runs:
            active_run_ids = [_["run_id"] for _ in runs["runs"]]
            logger.info(f"Canceling active runs {active_run_ids}")
            [self.runs_api.cancel_run(_) for _ in active_run_ids]

    def _submit_job(self, job_config: dict, is_streaming: bool, run_immediately: bool):
        job_resp = self.jobs_api.create_job(job_config)
        logger.info(f"Created Job with ID {job_resp['job_id']}")

        if is_streaming or run_immediately:
            resp = self.jobs_api.run_now(
                job_id=job_resp["job_id"],
                jar_params=None,
                notebook_params=None,
                python_params=None,
                spark_submit_params=None,
            )
            logger.info(f"Created run with ID {resp['run_id']}")
