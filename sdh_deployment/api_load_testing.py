import logging
import sys
from datetime import datetime
from glob import glob

import docker
import pandas as pd
from docker import DockerClient

from sdh_deployment.ApplicationVersion import ApplicationVersion
from sdh_deployment.DeploymentStep import DeploymentStep
from sdh_deployment.upload_to_blob import UploadToBlob
from sdh_deployment.util import get_docker_credentials, CosmosCredentials, KeyVaultSecrets, get_application_name, \
    get_shared_blob_service, docker_logging

logger = logging.getLogger(__name__)

VSTS_WORKING_DIR = '/home/vsts/work/1/s/'
CONTAINER_NAME = 'load-testing'


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
        return glob('results/current*/simulation.log')[0]

    def upload_results(self):
        build_definition_name = get_application_name()
        blob_service = get_shared_blob_service()

        now = datetime.now().isoformat()
        blob_simulation_path = f"{build_definition_name}/simulation-{now}.log"
        blob_csv_path = f"{build_definition_name}/results-{now}.csv"

        UploadToBlob._upload_file_to_blob(blob_service, self.simulation_log, blob_simulation_path, 'load-testing')
        UploadToBlob._upload_file_to_blob(blob_service, 'results/current.csv', blob_csv_path, 'load-testing')

    def download_metrics(self):
        build_definition_name = get_application_name()
        blob_service = get_shared_blob_service()

        blobs = [_.name for _ in blob_service.list_blobs(container_name=CONTAINER_NAME,
                                                         prefix=f"{build_definition_name}/results")]

        current = blobs[-1]
        previous = blobs[-2]
        if len(blobs) == 1:
            previous = current

        current_fn = 'current.tsv'
        previous_fn = 'previous.tsv'

        UploadToBlob._download_from_blob(blob_service, current, current_fn, CONTAINER_NAME)
        UploadToBlob._download_from_blob(blob_service, previous, previous_fn, CONTAINER_NAME)

        return previous_fn, current_fn

    def compare_to_previous(self):
        logging.info("------------- comparing load tests --------------")

        def read_file(fn):
            return (
                pd
                    .read_csv(fn, sep='\t')
                    .loc[lambda x: x['request'] == '_all']
                    .drop(['simulation', 'scenario', 'maxUsers', 'request', 'start',
                           'startDate', 'end', 'rating'], axis=1)
            )

        def log_diff(message, column, increase_pct=10):
            increase = diff[column][0] * 100
            if increase >= increase_pct:
                logging.error(message.format(increase=increase, current=current['avg'][0]))
                sys.exit(1)

        previous_fn, current_fn = self.download_metrics()
        previous = read_file(previous_fn)
        current = read_file(current_fn)

        diff = (current - previous) / previous

        log_diff("The average response time has gone up by {increase}% to {current} ms", 'avg')
        log_diff("The error count has gone up by {increase}% to {current}", 'errorCount')
        logging.info("'S all good man!!")

    @docker_logging(26)
    def _run_scenario(self, client, scenario, image):
        logging.info(f"Running load test for {scenario}")

        envs = self.get_env_variables()
        envs['BASE_URL'] = envs['BASE_URL'].format(dtap=self.env.environment.lower())
        logger.info(envs)

        cmd = f'bash -c "java -cp /api-load-testing.jar io.gatling.app.Gatling -s {scenario} -on current"'
        logs = client.containers.run(
            command=cmd,
            environment=envs,
            image=image,
            volumes={f'{VSTS_WORKING_DIR}/results': {'bind': '/app/results', 'mode': 'rw'}},
            stdout=True,
            stderr=True,
        )
        return logs

    @docker_logging()
    def _create_csv(self, client, image):
        logging.info(f"Creating csv from simulation.log")

        cmd = f'bash -c "java -jar /gatling_report.jar {self.simulation_log} > results/current.csv"'
        logs = client.containers.run(
            command=cmd,
            image=image,
            volumes={f'{VSTS_WORKING_DIR}/results/': {'bind': '/app/results', 'mode': 'rw'}},
            stdout=True,
            stderr=True,
        )

        logging.info(f"Load test completed")
        return logs

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

        self._run_scenario(
            client=client,
            scenario=scenario,
            image=f'{repository}:{version}')

        self._create_csv(client=client,
                         image=f'{repository}:{version}')

        self.upload_results()

        self.compare_to_previous()
