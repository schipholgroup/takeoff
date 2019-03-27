import logging
import os
from dataclasses import dataclass
from typing import List

import docker
from docker import DockerClient

from runway.ApplicationVersion import ApplicationVersion
from runway.DeploymentStep import DeploymentStep
from runway.credentials.application_name import ApplicationName
from runway.credentials.azure_container_registry import DockerRegistry
from runway.util import run_bash_command

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DockerFile(object):
    dockerfile: str
    postfix: str


class DockerImageBuilder(DeploymentStep):
    def __init__(self, env: ApplicationVersion, config: dict):
        super().__init__(env, config)

    def run(self):
        client: DockerClient = docker.from_env()
        docker_credentials = DockerRegistry(self.vault_name, self.vault_client).credentials(self.config)
        client.login(
            username=docker_credentials.username,
            password=docker_credentials.password,
            registry=docker_credentials.registry,
        )
        dockerfiles = [DockerFile(df["file"], df.get("postfix")) for df in self.config["dockerfiles"]]
        self.deploy(dockerfiles, docker_credentials, client)

    def build_image(self, docker_file, tag):
        # Set these environment variables at build time only, they should not be available at runtime
        cmd = [
            "docker", "build",
            "--build-arg", f"PIP_EXTRA_INDEX_URL={os.getenv('PIP_EXTRA_INDEX_URL')}",
            "-t", tag,
            "-f", f"./{docker_file}",
            ".",
        ]

        logger.info(f"Building docker image for {docker_file} with command \n{' '.join(cmd)}")

        return_code = run_bash_command(cmd)

        if return_code != 0:
            raise ChildProcessError("Could not build the package for some reason!")

    def deploy(self, dockerfiles: List[DockerFile], docker_credentials, docker_client):
        application_name = ApplicationName().get(self.config)
        for df in dockerfiles:
            tag = self.env.artifact_tag

            # only append a postfix if there is one provided
            if df.postfix:
                tag += df.postfix

            repository = f"{docker_credentials.registry}/{application_name}"

            self.build_image(df.dockerfile, f"{repository}:{tag}")

            logger.info(f"Uploading docker image for {df.dockerfile}")

            docker_client.images.push(repository=repository, tag=tag)
