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
                    "prefix",
                    default=None,
                    description=(
                        "Prefix for the image name, will be added `between` the image name"
                        "and repository (e.g. myreg.io/prefix/my-app:tag"
                    ),
                ): vol.Any(None, str),
                vol.Optional(
                    "custom_image_name", default=None, description="A custom name for the image to be used."
                ): vol.Any(None, str),
                vol.Optional(
                    "tag_release_as_latest", default=True, description="Tag a release also as 'latest' image."
                ): vol.Any(None, bool),
            }
        ],
    },
    extra=vol.ALLOW_EXTRA,
)


@dataclass(frozen=True)
class DockerFile(object):
    dockerfile: str
    postfix: Union[str, None]
    prefix: Union[str, None]
    custom_image_name: Union[str, None]
    tag_release_as_latest: bool


class DockerImageBuilder(Step):
    """Builds and pushes one or more docker images.

     Depends on:
     - Credentials for a docker registry (username, password, registry) must be
       available in your cloud vault or as environment variables
     - The docker-cli must be available
     """

    def __init__(self, env: ApplicationVersion, config: dict):
        super().__init__(env, config)
        self.docker_credentials = DockerRegistry(self.config, self.env).credentials()

    def docker_login(self):
        login = [
            "docker",
            "login",
            self.docker_credentials.registry,
            "-u",
            self.docker_credentials.username,
            "-p",
            self.docker_credentials.password,
        ]

        logger.info(f"Logging in to registry")

        return_code, _ = run_shell_command(login)
        if return_code != 0:
            raise ChildProcessError("Could not login for some reason!")

    def schema(self) -> vol.Schema:
        return SCHEMA

    def _construct_docker_build_config(self):
        return [
            DockerFile(
                df["file"], df["postfix"], df["prefix"], df["custom_image_name"], df["tag_release_as_latest"]
            )
            for df in self.config["dockerfiles"]
        ]

    def run(self):
        self.docker_login()
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

    def push_image(self, tag: str):
        """Push the docker image

        This uses bash to run commands directly.

        Args:
            tag: The docker tag to upload
        """
        push = ["docker", "push", tag]

        logger.info(f"Uploading docker image {tag}")

        return_code, _ = run_shell_command(push)

        if return_code != 0:
            raise ChildProcessError("Could not push image for some reason!")

    def deploy(self, dockerfiles: List[DockerFile]):
        for df in dockerfiles:
            tag = self.env.artifact_tag

            repository = "/".join(
                [
                    _
                    for _ in (self.docker_credentials.registry, df.prefix, self.application_name)
                    if _ is not None
                ]
            )

            if df.custom_image_name:
                repository = df.custom_image_name

            if df.postfix:
                repository += df.postfix

            image_tag = f"{repository}:{tag}"
            self.build_image(df.dockerfile, image_tag)
            self.push_image(image_tag)

            if df.tag_release_as_latest and self.env.on_release_tag:
                latest_tag = f"{repository}:latest"
                self.push_image(latest_tag)
