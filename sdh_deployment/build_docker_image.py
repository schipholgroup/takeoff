import logging
from dataclasses import dataclass
from typing import List

import docker
from docker import DockerClient

from sdh_deployment.ApplicationVersion import ApplicationVersion
from sdh_deployment.DeploymentStep import DeploymentStep
from sdh_deployment.util import get_application_name, get_docker_credentials

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DockerFile(object):
    dockerfile: str
    postfix: str


class DockerImageBuilder(DeploymentStep):
    def run(self, env: ApplicationVersion, config: dict):
        client: DockerClient = docker.from_env()
        docker_credentials = get_docker_credentials()
        client.login(
            username=docker_credentials.username,
            password=docker_credentials.password,
            registry=docker_credentials.registry,
        )
        dockerfiles = [
            DockerFile(df["file"], df.get("postfix")) for df in config["dockerfiles"]
        ]
        self.deploy(env, dockerfiles, docker_credentials, client)

    @staticmethod
    def deploy(env: ApplicationVersion,
               dockerfiles: List[DockerFile],
               docker_credentials,
               docker_client):
        application_name = get_application_name()
        for df in dockerfiles:
            tag = env.docker_tag

            # only append a postfix if there is one provided
            if df.postfix:
                tag += df.postfix

            repository = f"{docker_credentials.registry}/{application_name}"

            logger.info(f"Building docker image for {df.dockerfile}")
            docker_client.images.build(
                path="/root",
                tag=f"{repository}:{tag}",
                dockerfile=f"/root/{df.dockerfile}",
            )

            logger.info(f"Uploading docker image for {df.dockerfile}")
            result = docker_client.images.push(repository=repository, tag=tag)
            print(result)
            print(type(result))
