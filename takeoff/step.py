import abc

import voluptuous as vol

from takeoff.application_version import ApplicationVersion

# TODO move away from hardcoded depencendy on azure keyvault in this file
from takeoff.azure.credentials.keyvault import KeyVaultClient


class Step(object):
    def __init__(self, env: ApplicationVersion, config: dict):
        self.env = env
        self.config = self.validate(config)
        self.vault_name, self.vault_client = KeyVaultClient.vault_and_client(self.config, self.env)

    @abc.abstractmethod
    def run(self):
        raise NotImplementedError

    def validate(self, config: dict) -> dict:
        return self.schema()(config)

    @abc.abstractmethod
    def schema(self) -> vol.Schema:
        raise NotImplementedError


class SubStep(object):
    """Convenience class to use in substeps that don't require schema validation and
    should not be `run`able as main `Step`"""

    def __init__(self, env: ApplicationVersion, config: dict):
        self.env = env
        self.config = config
        self.vault_name, self.vault_client = KeyVaultClient.vault_and_client(self.config, self.env)
