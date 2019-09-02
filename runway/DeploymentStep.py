import abc
import voluptuous as vol

from runway import ApplicationVersion

# TODO move away from hardcoded depencendy on azure keyvault in this file
from runway.azure.credentials.azure_keyvault import AzureKeyvaultClient


class DeploymentStep(object):
    def __init__(self, env: ApplicationVersion, config: dict):
        self.env = env
        self.config = config
        self.vault_name, self.vault_client = AzureKeyvaultClient.vault_and_client(self.config, self.env)

    @abc.abstractmethod
    def run(self):
        raise NotImplementedError

    def validate(self) -> dict:
        return self.schema()(self.config)

    @abc.abstractmethod
    def schema(self) -> vol.Schema:
        raise NotImplementedError
