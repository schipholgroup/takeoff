import logging
from dataclasses import dataclass

import docker
from docker import DockerClient

from sdh_deployment.ApplicationVersion import ApplicationVersion
from sdh_deployment.DeploymentStep import DeploymentStep
from sdh_deployment.util import get_docker_credentials, CosmosCredentials, KeyVaultSecrets

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DockerFile(object):
    dockerfile: str
    postfix: str


class LoadTester(DeploymentStep):
    def __init__(self, env: ApplicationVersion, config: dict):
        super().__init__(env, config)

    def get_env_variables(self) -> dict:
        keyvault_env_variables = {s.env_key: s.val for s in KeyVaultSecrets.get_keyvault_secrets('dev')}

        custom_env_variables = self.config['env']

        cosmos_creds = CosmosCredentials.get_cosmos_write_credentials(self.env.environment)

        auto_env_variables = {
            'AZURE_COSMOS_END_POINT': cosmos_creds.uri,
            'AZURE_COSMOS_MASTER_KEY': cosmos_creds.key,
            'API_VERSION': self.env.version
        }

        envs = auto_env_variables
        envs.update(keyvault_env_variables)
        envs.update(custom_env_variables)
        return envs

    def run(self):
        client: DockerClient = docker.from_env()
        docker_credentials = get_docker_credentials()
        client.login(
            username=docker_credentials.username,
            password=docker_credentials.password,
            registry=docker_credentials.registry,
        )

        repository = f"{docker_credentials.registry}/sdh-load-testing"
        version = self.config['version']

        client.images.pull(repository, version)

        scenario = self.config['scenario']
        cmd = f'bash -c "java -cp /api-load-testing.jar io.gatling.app.Gatling -s {scenario}'
        envs = self.get_env_variables()
        envs['BASE_URL'] = envs['BASE_URL'].format(dtap=self.env.environment.lower())

        container = client.containers.run(
            command=cmd,
            environment=envs,
            image=f'{repository}:{version}',
            stdout=True,
            stderr=True,
        )
        container.logs()
