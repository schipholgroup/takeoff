import configparser
import json
import logging
import re
from dataclasses import dataclass
from typing import List

from databricks_cli.jobs.api import JobsApi
from databricks_cli.runs.api import RunsApi
from databricks_cli.sdk import ApiClient

from runway import util
from runway.ApplicationVersion import ApplicationVersion
from runway.DeploymentStep import DeploymentStep
from runway.credentials.azure_databricks import DatabricksClient
from runway.credentials.azure_keyvault import azure_keyvault_client
from runway.util import (
    get_application_name,
    has_prefix_match,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class JobConfig(object):
    name: str
    job_id: int


class DeployToDatabricks(DeploymentStep):
    def __init__(self, env: ApplicationVersion, config: dict):
        super().__init__(env, config)

    def run(self):
        config_file_fn = self.config['config_file_fn']
        self.deploy_to_databricks(config_file_fn)

    @staticmethod
    def _job_is_streaming(job_config: dict):
        """
        If there is no schedule, the job would not run periodically, therefore we assume that is a
        streaming job
        :param job_config: the configuration of the Databricks job
        :return: (bool) if it is a streaming job
        """
        return "schedule" not in job_config.keys()

    def deploy_to_databricks(self, config_file_fn: str):
        """
        The application parameters (cosmos and eventhub) will be removed from this file as they
        will be set as databricks secrets eventually
        If the job is a streaming job this will directly start the new job_run given the new
        configuration. If the job is batch this will not start it manually, assuming the schedule
        has been set correctly.
        """
        application_name = get_application_name()

        root_library_folder = self.config['runway_common_keys']['databricks_library_path']
        job_config = DeployToDatabricks._construct_job_config(
            config_file_fn=config_file_fn,
            name=application_name,
            version=self.env.artifact_tag,
            egg=f"{root_library_folder}/{application_name}/{application_name}-{self.env.artifact_tag}.egg",
            python_file=f"{root_library_folder}/{application_name}/{application_name}-main-{self.env.artifact_tag}.py",
        )

        vault, client = azure_keyvault_client(self.config, self.env)
        databricks_client = DatabricksClient(vault, client).credentials(self.config)

        is_streaming = self._job_is_streaming(job_config)
        logger.info("Removing old job")

        self.__remove_job(databricks_client, application_name, self.env.branch, is_streaming=is_streaming)

        logger.info("Submitting new job with configuration:")
        logger.info(str(job_config))

        self._submit_job(databricks_client, job_config, is_streaming)

    @staticmethod
    def _read_application_config(fn: str):
        config = configparser.ConfigParser()
        config.read(fn)

        return config

    @staticmethod
    def _construct_job_config(config_file_fn: str, name: str, version: str, egg: str, python_file: str) -> dict:
        params = {
            "application_name": f"{name}-{version}",
            "log_destination": name,
            "python_file": python_file,
            "egg_file": egg
        }
        job_config = util.render_file_with_jinja(config_file_fn, params, json.loads)
        return job_config

    @staticmethod
    def __remove_job(client, application_name: str, branch: str, is_streaming: bool):
        """
        Removes the existing job and cancels any running job_run if the application is streaming.
        If the application is batch, it'll let the batch job finish but it will remove the job,
        making sure no other job_runs can start for that old job.
        """
        jobs_api = JobsApi(client)
        runs_api = RunsApi(client)

        job_configs = [
            JobConfig(_["settings"]["name"], _["job_id"])
            for _ in jobs_api.list_jobs()["jobs"]
        ]
        job_id = DeployToDatabricks._application_job_id(application_name, branch, job_configs)

        if job_id:
            if is_streaming:
                DeployToDatabricks._kill_it_with_fire(runs_api, job_id)
            jobs_api.delete_job(job_id)

    @staticmethod
    def _application_job_id(application_name: str, branch: str, jobs: List[JobConfig]) -> int:
        snapshot = "SNAPSHOT"
        tag = "\d+\.\d+\.\d+|"
        pattern = re.compile(rf"^({application_name})-({snapshot}|{tag}|{branch})$")

        return next(
            (
                _.job_id
                for _ in jobs
                if has_prefix_match(_.name, application_name, pattern)
            ),
            None,
        )

    @staticmethod
    def _kill_it_with_fire(runs_api, job_id):
        runs = runs_api.list_runs(
            job_id, active_only=True, completed_only=None, offset=None, limit=None
        )
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
            jobs_api.run_now(job_id=job_resp["job_id"],
                             jar_params=None,
                             notebook_params=None,
                             python_params=None,
                             spark_submit_params=None)
