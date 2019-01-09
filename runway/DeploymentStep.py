import abc

from runway import ApplicationVersion
from runway.credentials.azure_keyvault import AzureKeyvaultClient


class DeploymentStep(object):
    def __init__(self, env: ApplicationVersion, config: dict):
        self.env = env
        self.config = config
        self.vault_name, self.vault_client = AzureKeyvaultClient.vault_and_client(self.config, self.env)

    @abc.abstractmethod
    def run(self):
        raise NotImplementedError
