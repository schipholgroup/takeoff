import logging
from dataclasses import dataclass
from datetime import datetime
from glob import glob
from pprint import pprint

import docker
from docker import DockerClient

from sdh_deployment.ApplicationVersion import ApplicationVersion
from sdh_deployment.DeploymentStep import DeploymentStep
from sdh_deployment.upload_to_blob import UploadToBlob
from sdh_deployment.util import get_docker_credentials, CosmosCredentials, KeyVaultSecrets, get_application_name, \
    get_shared_blob_service

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DockerFile(object):
    dockerfile: str
    postfix: str


RESULTS_CSV_PATH = '/app/results/current.csv'


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

    @property
    def simulation_log(self):
        return glob('/app/results/current*/simulation.log')[0]

    def upload_results(self):
        build_definition_name = get_application_name()
        blob_service = get_shared_blob_service()

        now = datetime.now().isoformat()
        blob_simulation_path = f"{build_definition_name}/simulation-{now}.log"
        blob_csv_path = f"{build_definition_name}/results-{now}.csv"

        UploadToBlob._upload_file_to_blob(blob_service, self.simulation_log, blob_simulation_path, 'load-testing')
        UploadToBlob._upload_file_to_blob(blob_service, RESULTS_CSV_PATH, blob_csv_path, 'load-testing')

    def _run_scenario(self, client, scenario, image):
        logging.info(f"Running load test for {scenario}")

        envs = self.get_env_variables()
        envs['BASE_URL'] = envs['BASE_URL'].format(dtap=self.env.environment.lower())

        cmd = f'bash -c "java -cp /api-load-testing.jar io.gatling.app.Gatling -s {scenario} -on current"'
        container = client.containers.run(
            command=cmd,
            environment=envs,
            image=image,
            volumes={'/results/': {'bind': '/app/results', 'mode': 'rw'}},
            stdout=True,
            stderr=True,
        )
        try:
            pprint(container.logs())
        except Exception as e:
            logging.error(e)

    def _create_csv(self, client, image):
        logging.info(f"Creating csv from simulation.log")

        cmd = f'bash -c "java -jar /gatling_report.jar {self.simulation_log} > {RESULTS_CSV_PATH}"'
        container = client.containers.run(
            command=cmd,
            image=image,
            volumes={'/results/': {'bind': '/app/results', 'mode': 'rw'}},
            stdout=True,
            stderr=True,
        )
        try:
            pprint(container.logs())
        except Exception as e:
            logging.error(e)

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

        logging.info(f"Pulling {repository}")
        client.images.pull(repository, version)

        scenario = self.config['scenario']

        logging.info(f"Load test completed")

        self._run_scenario(
            client=client,
            scenario=scenario,
            image=f'{repository}:{version}')

        self._create_csv(client=client,
                         image=f'{repository}:{version}')

        self.upload_results()
