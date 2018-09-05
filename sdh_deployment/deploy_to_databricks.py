import configparser
import logging
import re
import copy
from dataclasses import dataclass
from typing import List

from databricks_cli.jobs.api import JobsApi
from databricks_cli.runs.api import RunsApi
from databricks_cli.sdk import ApiClient

from sdh_deployment.util import (
    get_application_name,
    get_databricks_client,
    has_prefix_match,
)
from sdh_deployment.run_deployment import ApplicationVersion

logger = logging.getLogger(__name__)

ROOT_LIBRARY_FOLDER = "dbfs:/mnt/libraries"


@dataclass(frozen=True)
class JobConfig(object):
    name: str
    job_id: int


class DeployToDatabricks:
    @staticmethod
    def _job_is_streaming(job_config: dict):
        """
        If there is no schedule, the job would not run periodically, therefore we assume that is a
        streaming job
        :param job_config: the configuration of the Databricks job
        :return: (bool) if it is a streaming job
        """
        return "schedule" not in job_config.keys()

    @staticmethod
    def deploy_to_databricks(env: ApplicationVersion, config: dict):
        """
        The application parameters (cosmos and eventhub) will be removed from this file as they
        will be set as databricks secrets eventually
        If the job is a streaming job this will directly start the new job_run given the new
        configuration. If the job is batch this will not start it manually, assuming the schedule
        has been set correctly.
        """
        application_name = get_application_name()

        job_config = DeployToDatabricks._construct_job_config(
            job_config=config,
            name=application_name,
            version=env.version,
            egg=f"{ROOT_LIBRARY_FOLDER}/{application_name}/{application_name}-{env.version}.egg",
            python_file=f"{ROOT_LIBRARY_FOLDER}/{application_name}/{application_name}-main-{env.version}.py",
        )

        databricks_client = get_databricks_client(env.environment)

        is_streaming = DeployToDatabricks._job_is_streaming(job_config)
        logger.info("Removing old job")
        DeployToDatabricks.__remove_job(
            databricks_client, application_name, is_streaming=is_streaming
        )
        logger.info("Submitting new job with configuration:")
        logger.info(str(job_config))

        DeployToDatabricks._submit_job(databricks_client, job_config, is_streaming)

    @staticmethod
    def _read_application_config(fn: str):
        config = configparser.ConfigParser()
        config.read(fn)

        return config

    @staticmethod
    def _construct_job_config(
        job_config: dict, name: str, version: str, egg: str, python_file: str
    ) -> dict:
        # We want to do a copy, since we are going to append the dict
        # which is passed by reference
        job_config = copy.deepcopy(job_config)

        job_config["new_cluster"]["cluster_log_conf"]["dbfs"][
            "destination"
        ] = job_config["new_cluster"]["cluster_log_conf"]["dbfs"]["destination"].format(
            name=name
        )
        job_config["new_cluster"]["cluster_name"] = f"{name}-{version}"
        job_config["name"] = f"{name}-{version}"
        job_config["spark_python_task"]["python_file"] = python_file
        job_config["libraries"].append({"egg": egg})

        return job_config

    @staticmethod
    def __remove_job(client, application_name: str, is_streaming: bool):
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
        job_id = DeployToDatabricks._application_job_id(application_name, job_configs)

        if job_id:
            if is_streaming:
                DeployToDatabricks._kill_it_with_fire(runs_api, job_id)
            jobs_api.delete_job(job_id)

    @staticmethod
    def _application_job_id(application_name: str, jobs: List[JobConfig]) -> int:
        snapshot = "SNAPSHOT"
        tag = "\d+\.\d+\.\d+|"
        git_hash = "[a-f0-9]{7}"
        pattern = re.compile(rf"^({application_name})-({snapshot}|{tag}|{git_hash})$")

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
            jobs_api.run_now(job_resp["job_id"], None, None, None, None)
