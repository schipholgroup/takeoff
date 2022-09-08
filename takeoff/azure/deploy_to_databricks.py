import json
import logging
import pprint
from dataclasses import dataclass
from typing import List, Optional, Dict

import voluptuous as vol
from databricks_cli.jobs.api import JobsApi
from databricks_cli.runs.api import RunsApi

from takeoff import util
from takeoff.application_version import ApplicationVersion
from takeoff.azure.credentials.databricks import Databricks
from takeoff.azure.credentials.keyvault import KeyVaultClient
from takeoff.schemas import TAKEOFF_BASE_SCHEMA
from takeoff.step import Step
from takeoff.util import get_whl_name, get_main_py_name

logger = logging.getLogger(__name__)

SCHEMA = TAKEOFF_BASE_SCHEMA.extend(
    {
        vol.Required("task"): "deploy_to_databricks",
        vol.Required("jobs"): vol.All(
            [
                {
                    vol.Required("main_name"): str,
                    vol.Optional(
                        "use_original_python_filename",
                        description=(
                            """If you upload multiple unique Python files use this flag to include the
                            original filename in the result. Only impacts Python files."""
                        ),
                        default=False,
                    ): bool,
                    vol.Optional("config_file", default="databricks.json.j2"): str,
                    vol.Optional("name", default=""): str,
                    vol.Optional("lang", default="python"): vol.All(str, vol.In(["python", "scala"])),
                    vol.Optional("run_stream_job_immediately", default=True): bool,
                    vol.Optional("is_batch", default=False): bool,
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
    def _job_is_unscheduled(job_config: dict):
        """
        Checks if a job is scheduled
        :param job_config: the configuration of the Databricks job
        :return: (bool) if it is scheduled
        """
        return "schedule" not in job_config.keys()

    def deploy_to_databricks(self):
        """
        The application parameters (cosmos and eventhub) will be removed from this file as they
        will be set as databricks secrets eventually
        If the job is a streaming job this will directly start the new job_run given the new
        configuration. If the job is batch this will not start it manually.
        """
        for job in self.config["jobs"]:
            app_name = self._construct_name(job["name"])
            job_config = self.create_config(app_name, job)
            is_streaming = self._job_is_unscheduled(job_config) and not job["is_batch"]
            run_stream_job_immediately = job["run_stream_job_immediately"]

            logger.info("Removing old job")
            self.remove_job(app_name, is_streaming=is_streaming)

            logger.info("Submitting new job with configuration:")
            logger.info(pprint.pformat(job_config))
            self.deploy_job(job_config, is_streaming, run_stream_job_immediately)

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
            py_main_name = get_main_py_name(
                self.application_name,
                self.env.artifact_tag,
                job_config["main_name"],
                job_config["use_original_python_filename"],
            )
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
        return f"{self.application_name}{postfix}-{self.env.artifact_tag}"

    def _construct_arguments(self, args: List[dict]) -> list:
        params = []
        for named_arguments_pair in args:
            for k, v in named_arguments_pair.items():
                params.extend([f"--{k}", v.format(env=self.env.environment_formatted)])

        return params

    @staticmethod
    def _construct_job_config(config_file: str, **kwargs) -> dict:
        return util.render_file_with_jinja(config_file, kwargs, json.loads)

    def remove_job(self, job_name: str, is_streaming: bool):
        """
        Removes the existing job and cancels any running job_run if the application is streaming.
        If the application is batch, it'll let the batch job finish but it will remove the job,
        making sure no other job_runs can start for that old job.
        """

        job_configs = [
            JobConfig(_["settings"]["name"], _["job_id"]) for _ in self.jobs_api.list_jobs()["jobs"]
        ]
        job_ids = self._application_job_id(job_name, job_configs)

        if not job_ids:
            logger.info(f"Could not find jobs in list of {pprint.pformat(job_configs)}")

        for job_id in job_ids:
            logger.info(f"Found Job with ID {job_id}")
            if is_streaming:
                self._kill_it_with_fire(job_id)
            logger.info(f"Deleting Job with ID {job_id}")
            self.jobs_api.delete_job(job_id)

    def _application_job_id(self, job_name: str, jobs: List[JobConfig]) -> List[int]:
        return [_.job_id for _ in jobs if job_name in _.name]

    def _kill_it_with_fire(self, job_id: int):
        logger.info(f"Finding runs for job_id {job_id}")
        runs = self.runs_api.list_runs(job_id, active_only=True, completed_only=None, offset=None, limit=None)
        # If the runs is empty, there are no jobs at all
        # TODO: Check if the has_more flag is true, this means we need to go over the pages
        if "runs" in runs:
            active_run_ids = [_["run_id"] for _ in runs["runs"]]
            logger.info(f"Canceling active runs {active_run_ids}")
            [self.runs_api.cancel_run(_) for _ in active_run_ids]

    def deploy_job(self, job_config: Dict, is_streaming: bool, run_stream_job_immediately: bool):
        job_id = self._submit_job(job_config)
        if is_streaming and run_stream_job_immediately:
            self._run_job(job_id)

    def _submit_job(self, job_config: Dict):
        job_resp = self.jobs_api.create_job(job_config)
        logger.info(f"Created Job with ID {job_resp['job_id']}")
        return job_resp["job_id"]

    def _run_job(self, job_id: str):
        resp = self.jobs_api.run_now(
            job_id=job_id, jar_params=None, notebook_params=None, python_params=None, spark_submit_params=None
        )
        logger.info(f"Created run with ID {resp['run_id']}")
