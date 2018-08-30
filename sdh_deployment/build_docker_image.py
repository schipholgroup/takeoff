import logging
from dataclasses import dataclass
from typing import List

import docker
from docker import DockerClient

from sdh_deployment.run_deployment import ApplicationVersion
from sdh_deployment.util import get_application_name, get_docker_credentials

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DockerFile(object):
    dockerfile: str
    postfix: str


class DockerImageBuilder(object):
    def __init__(self, env: ApplicationVersion):
        self.env = env
        self.client: DockerClient = docker.from_env()
        self.docker_credentials = get_docker_credentials()
        self.client.login(
            username=self.docker_credentials.username,
            password=self.docker_credentials.password,
            registry=self.docker_credentials.registry)

    def run(self, dockerfiles: List[DockerFile]):
        application_name = get_application_name()
        for df in dockerfiles:
            tag = f'{self.env.version}'

            # only append a postfix if there is one provided
            if df.postfix:
                tag += f'{df.postfix}'

            repository = f'{self.docker_credentials.registry}/{application_name}'

            logger.info(f"Building docker image for {df.dockerfile}")
            self.client.images.build(
                path='/root',
                tag=f'{repository}:{tag}',
                dockerfile=f'/root/{df.dockerfile}')

            logger.info(f"Uploading docker image for {df.dockerfile}")
            self.client.images.push(
                repository=repository,
                tag=tag)
