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
from takeoff.credentials.application_name import ApplicationName
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


class DeployToDatabricks(Step):
    """Deploy a job to Databricks, can be (scheduled) batch or streaming """
    def __init__(self, env: ApplicationVersion, config: dict):
        super().__init__(env, config)
        self.databricks_client = Databricks(self.vault_name, self.vault_client).api_client(self.config)
        self.jobs_api = JobsApi(self.databricks_client)
        self.runs_api = RunsApi(self.databricks_client)

    def schema(self) -> vol.Schema:
        return SCHEMA

    def run(self):
        self.deploy_to_databricks()

    @staticmethod
    def _job_is_streaming(job_config: dict) -> bool:
        """Determine if the job_config passed is for a batch or streaming job

        If there is no schedule, the job would not run periodically, therefore we assume that is a
        streaming job

        Args:
            job_config: the configuration of the Databricks job

        Returns:
            bool: True if the job is a streaming job, False otherwise.
        """
        return "schedule" not in job_config.keys()

    def deploy_to_databricks(self):
        """Deploy a (number of) jobs to Databricks, as configured in the config of this step"""
        application_name = ApplicationName().get(self.config)

        for job in self.config["jobs"]:
            app_name = self._construct_name(job["name"])
            job_name = f"{app_name}-{self.env.artifact_tag}"
            job_config = self.create_config(job_name, job, application_name)
            is_streaming = self._job_is_streaming(job_config)

            logger.info("Removing old job")
            self.remove_job(app_name, self.env.artifact_tag, is_streaming=is_streaming)

            logger.info("Submitting new job with configuration:")
            logger.info(pprint.pformat(job_config))
            self._submit_job(job_config, is_streaming)

    def create_config(self, job_name: str, job_config: dict, application_name: str) -> dict:
        """Create the Databricks config for the job to run

        Args:
            job_name: The name of the job
            job_config: The configuration of the job
            application_name: The name of the application

        Returns:
            dict: The Databricks job configuration created
        """
        common_arguments = dict(
            config_file=job_config["config_file"],
            application_name=job_name,
            log_destination=job_name,
            parameters=self._construct_arguments(job_config["arguments"]),
            schedule=self._get_schedule(job_config),
        )

        root_library_folder = self.config["common"]["databricks_library_path"]
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
        """Extract the schedule from the provided job config if available

        Args:
            job_config: The Databricks job config from which to extract the schedule

        Returns:
            The schedule if set in the job config, None otherwise
        """
        schedule = job_config.get("schedule", None)
        if schedule:
            if "quartz_cron_expression" in schedule:
                return schedule
            else:
                return schedule.get(self.env.environment.lower(), None)

        return schedule

    def _construct_name(self, name: str) -> str:
        """Construct the full job name, composed of the provided name appended to the application name

        Args:
            name: String to postfix (separated by `-`) to the application name to use as Databricks job name

        Returns:
            str: Constructed Databricks job name
        """
        postfix = f"-{name}" if name else ""
        return f"{ApplicationName().get(self.config)}{postfix}"

    @staticmethod
    def _construct_arguments(args: List[dict]) -> list:
        """Convert arguments passed in Takeoff configuration into parameters to be passed into the Databricks
        job that is to be run

        Args:
            args: List of key-value pairs of arguments as specified in Takeoff configuration

        Returns:
            List: List of argument names and values. Each argument name is prefixed with a `--`
        """
        params = []
        for named_arguments_pair in args:
            for k, v in named_arguments_pair.items():
                params.extend([f"--{k}", v])

        return params

    @staticmethod
    def _construct_job_config(config_file: str, **kwargs) -> dict:
        """Construct the Databricks job config from a Jinja-templated file

        The values to be rendered into the Jinja template can be passed as kwargs

        Args:
            config_file: The Databricks Jinja-templated configuration file
            **kwargs: Keyword arguments to be used as values for rendering the Jinja template

        Returns:
            dict: Rendered Databricks job configuration
        """
        return util.render_file_with_jinja(config_file, kwargs, json.loads)

    def remove_job(self, application_name: str, branch: str, is_streaming: bool):
        """Remove an existing Databricks job and cancel any running job_run if it's a streaming application.

        If the application is batch, it'll let the batch job finish but it will remove the job,
        making sure no other job_runs can start for that old job.

        This function finds the job by searching a list of all Databricks jobs currently active, and matching
        the application name with the jobs in hat list.

        Args:
            application_name: The name of the application for which to remove the jobs
            branch: The branch name for which to kill the jobs. This is used together with the application
                name to find the active jobs.
            is_streaming: True if the job to be removed is a streaming job, False otherwise
        """
        job_configs = [
            JobConfig(_["settings"]["name"], _["job_id"]) for _ in self.jobs_api.list_jobs()["jobs"]
        ]
        job_ids = self._application_job_id(application_name, branch, job_configs)

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
        """Extract the Databricks job id for a given application + branch combination from a list of
        Databricks jobs.

        This function will search for the application_name, combined with semantic version numbers,
        'SNAPSHOT', or the branch name.

        Args:
            application_name: The application name for which to extract the job id
            branch: The branch for which to search.
            jobs: The list of jobs in which to search

        Returns:
            List[int]: List of job id's that are running for this application_name
        """
        snapshot = "SNAPSHOT"
        tag = "\d+\.\d+\.\d+"
        pattern = re.compile(rf"^({application_name})-({snapshot}|{tag}|{branch})$")

        return [_.job_id for _ in jobs if has_prefix_match(_.name, application_name, pattern)]

    def _kill_it_with_fire(self, job_id: int):
        """Given a Databricks job id, kill all active job_runs for that job id

        Args:
            job_id: A valid Databricks job id
        """
        logger.info(f"Finding runs for job_id {job_id}")
        runs = self.runs_api.list_runs(job_id, active_only=True, completed_only=None, offset=None, limit=None)
        # If the runs is empty, there are no jobs at all
        # TODO: Check if the has_more flag is true, this means we need to go over the pages
        if "runs" in runs:
            active_run_ids = [_["run_id"] for _ in runs["runs"]]
            logger.info(f"Canceling active runs {active_run_ids}")
            [self.runs_api.cancel_run(_) for _ in active_run_ids]

    def _submit_job(self, job_config: dict, is_streaming: bool):
        """Submit a given job to Databricks

        For streaming jobs, the job is run immediately, as the stream should be started. For batch jobs, only
        a Databricks job is created. This means that a run will be created if there is a schedule set, but it
        will not run otherwise.

        Args:
            job_config: The Databricks job config
            is_streaming: True if the job is streaming, and should be run immediately, False otherwise
        """
        job_resp = self.jobs_api.create_job(job_config)
        logger.info(f"Created Job with ID {job_resp['job_id']}")

        if is_streaming:
            resp = self.jobs_api.run_now(
                job_id=job_resp["job_id"],
                jar_params=None,
                notebook_params=None,
                python_params=None,
                spark_submit_params=None,
            )
            logger.info(f"Created run with ID {resp['run_id']}")
