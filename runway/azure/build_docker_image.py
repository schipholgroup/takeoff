import base64
import json
import logging
import os
from dataclasses import dataclass
from typing import List

import voluptuous as vol

from runway.ApplicationVersion import ApplicationVersion
from runway.DeploymentStep import DeploymentStep
from runway.credentials.application_name import ApplicationName
from runway.azure.credentials.container_registry import DockerRegistry
from runway.schemas import BASE_SCHEMA
from runway.util import run_bash_command

logger = logging.getLogger(__name__)

SCHEMA = BASE_SCHEMA.extend(
    {
        vol.Required("task"): vol.All(str, vol.Match(r"buildDockerImage")),
        vol.Optional(
            "dockerfiles", default=[{"file": "Dockerfile", "postfix": None, "custom_image_name": None}]
        ): [
            {
                vol.Optional("file", default="Dockerfile"): str,
                vol.Optional("postfix", default=None): vol.Any(None, str),
                vol.Optional("custom_image_name", default=None): vol.Any(None, str),
            }
        ],
    },
    extra=vol.ALLOW_EXTRA,
)


@dataclass(frozen=True)
class DockerFile(object):
    dockerfile: str
    postfix: str
    custom_image_name: str


class DockerImageBuilder(DeploymentStep):
    def __init__(self, env: ApplicationVersion, config: dict):
        super().__init__(env, config)

    def populate_docker_config(self, docker_credentials):
        creds = f"{docker_credentials.username}:{docker_credentials.password}".encode()

        docker_json = {"auths": {docker_credentials.registry: {"auth": base64.b64encode(creds).decode()}}}

        home = os.environ["HOME"]
        docker_dir = f"{home}/.docker"
        if not os.path.exists(docker_dir):
            os.mkdir(docker_dir)
        with open(f"{docker_dir}/config.json", "w") as f:
            json.dump(docker_json, f)

    def schema(self) -> vol.Schema:
        return SCHEMA

    def run(self):
        run_config = self.validate()
        dockerfiles = [
            DockerFile(df["file"], df["postfix"], df["custom_image_name"]) for df in run_config["dockerfiles"]
        ]
        docker_credentials = DockerRegistry(self.vault_name, self.vault_client).credentials(run_config)

        self.populate_docker_config(docker_credentials)
        self.deploy(run_config, dockerfiles, docker_credentials)

    def build_image(self, docker_file: str, tag: str):
        # Set these environment variables at build time only, they should not be available at runtime
        cmd = [
            "docker",
            "build",
            "--build-arg",
            f"PIP_EXTRA_INDEX_URL={os.getenv('PIP_EXTRA_INDEX_URL')}",
            "-t",
            tag,
            "-f",
            f"./{docker_file}",
            ".",
        ]

        logger.info(f"Building docker image for {docker_file} with command \n{' '.join(cmd)}")

        return_code = run_bash_command(cmd)

        if return_code != 0:
            raise ChildProcessError("Could not build the image for some reason!")

    @staticmethod
    def push_image(tag):
        cmd = ["docker", "push", tag]

        logger.info(f"Uploading docker image {tag}")

        return_code = run_bash_command(cmd)

        if return_code != 0:
            raise ChildProcessError("Could not push image for some reason!")

    def deploy(self, config: dict, dockerfiles: List[DockerFile], docker_credentials):
        application_name = ApplicationName().get(config)
        for df in dockerfiles:
            tag = self.env.artifact_tag

            # only append a postfix if there is one provided
            if df.postfix:
                tag += df.postfix

            repository = f"{docker_credentials.registry}/{application_name}"

            if df.custom_image_name:
                repository = df.custom_image_name

            image_tag = f"{repository}:{tag}"
            self.build_image(df.dockerfile, image_tag)
            self.push_image(image_tag)
