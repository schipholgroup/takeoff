import base64
import json
import logging
import os
from dataclasses import dataclass
from typing import List, Union

import voluptuous as vol

from takeoff.application_version import ApplicationVersion
from takeoff.credentials.container_registry import DockerRegistry
from takeoff.schemas import TAKEOFF_BASE_SCHEMA
from takeoff.step import Step
from takeoff.util import run_shell_command

logger = logging.getLogger(__name__)

SCHEMA = TAKEOFF_BASE_SCHEMA.extend(
    {
        vol.Required("task"): "build_docker_image",
        vol.Optional("credentials", default="environment_variables"): vol.All(
            str, vol.In(["environment_variables", "azure_keyvault"])
        ),
        vol.Optional(
            "dockerfiles", default=[{"file": "Dockerfile", "postfix": None, "custom_image_name": None}]
        ): [
            {
                vol.Optional("file", default="Dockerfile", description="Alternative docker file name"): str,
                vol.Optional(
                    "postfix",
                    default=None,
                    description="Postfix for the image name, will be added `before` the tag",
                ): vol.Any(None, str),
                vol.Optional(
                    "custom_image_name", default=None, description="A custom name for the image to be used."
                ): vol.Any(None, str),
            }
        ],
    },
    extra=vol.ALLOW_EXTRA,
)


@dataclass(frozen=True)
class DockerFile(object):
    dockerfile: str
    postfix: Union[str, None]
    custom_image_name: Union[str, None]


class DockerImageBuilder(Step):
    """Builds and pushes one or more docker images.

     Depends on:
     - Credentials for a docker registry (username, password, registry) must be
       available in your cloud vault or as environment variables
     - The docker-cli must be available
     """

    def __init__(self, env: ApplicationVersion, config: dict):
        super().__init__(env, config)
        self.docker_credentials = DockerRegistry(config, env).credentials()

    def populate_docker_config(self):
        """Creates ~/.docker/config.json and writes the credentials for the registry to the file"""
        creds = f"{self.docker_credentials.username}:{self.docker_credentials.password}".encode()

        docker_json = {
            "auths": {self.docker_credentials.registry: {"auth": base64.b64encode(creds).decode()}}
        }

        home = os.environ["HOME"]
        docker_dir = f"{home}/.docker"
        if not os.path.exists(docker_dir):
            os.mkdir(docker_dir)
        with open(f"{docker_dir}/config.json", "w") as f:
            json.dump(docker_json, f)

    def schema(self) -> vol.Schema:
        return SCHEMA

    def _construct_docker_build_config(self):
        return [
            DockerFile(df["file"], df["postfix"], df["custom_image_name"])
            for df in self.config["dockerfiles"]
        ]

    def run(self):
        self.populate_docker_config()
        self.deploy(self._construct_docker_build_config())

    @staticmethod
    def build_image(docker_file: str, tag: str):
        """Build the docker image

        This uses bash to run commands directly.

        Args:
            docker_file: The name of the dockerfile to build
            tag: The docker tag to apply to the image name
        """
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

        return_code, _ = run_shell_command(cmd)

        if return_code != 0:
            raise ChildProcessError("Could not build the image for some reason!")

    @staticmethod
    def push_image(tag: str):
        """Push the docker image

        This uses bash to run commands directly.

        Args:
            tag: The docker tag to upload
        """
        cmd = ["docker", "push", tag]

        logger.info(f"Uploading docker image {tag}")

        return_code, _ = run_shell_command(cmd)

        if return_code != 0:
            raise ChildProcessError("Could not push image for some reason!")

    def deploy(self, dockerfiles: List[DockerFile]):
        for df in dockerfiles:
            tag = self.env.artifact_tag

            repository = f"{self.docker_credentials.registry}/{self.application_name}"

            if df.custom_image_name:
                repository = df.custom_image_name

            if df.postfix:
                repository += df.postfix

            image_tag = f"{repository}:{tag}"
            self.build_image(df.dockerfile, image_tag)
            self.push_image(image_tag)
