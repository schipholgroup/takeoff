import abc

import voluptuous as vol

from runway import ApplicationVersion
# TODO move away from hardcoded depencendy on azure keyvault in this file
from runway.azure.credentials.keyvault import KeyVaultClient


class Step(object):
    def __init__(self, env: ApplicationVersion, config: dict):
        self.env = env
        self.config = self.validate(config)
        self.vault_name, self.vault_client = KeyVaultClient.vault_and_client(self.config, self.env)

    @abc.abstractmethod
    def run(self):
        raise NotImplementedError

    def validate(self, config) -> dict:
        return self.schema()(config)

    @abc.abstractmethod
    def schema(self) -> vol.Schema:
        raise NotImplementedError
