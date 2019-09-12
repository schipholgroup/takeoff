import abc
from dataclasses import dataclass

from takeoff.azure.credentials.KeyVaultCredentialsMixin import KeyVaultCredentialsMixin
from takeoff.azure.credentials.keyvault import KeyVaultClient
from takeoff.credentials.EnvironmentCredentialsMixin import EnvironmentCredentialsMixin
from takeoff.util import current_filename


@dataclass(frozen=True)
class DockerCredentials(object):
    username: str
    password: str
    registry: str


class BaseProvider:
    def __init__(self, config, env):
        self.config = config
        self.env = env

    @abc.abstractmethod
    def get_credentials(self, lookup: str):
        pass


class AzureKeyVaultProvider(BaseProvider, KeyVaultCredentialsMixin):
    def __init__(self, config, env):
        super().__init__(config, env)
        self.vault_name, self.vault_client = KeyVaultClient.vault_and_client(self.config, self.env)

    def get_credentials(self, lookup: str):
        credential_kwargs = super()._transform_key_to_credential_kwargs(
            self.config["azure"]["keyvault_keys"][lookup]
        )
        return DockerCredentials(**credential_kwargs)


class EnviromentCredentialsProvider(BaseProvider, EnvironmentCredentialsMixin):

    def get_credentials(self, lookup: str):
        self._transform_environment_key_to_credential_kwargs(lookup)


class TakeoffCredentials:
    def __init__(self, config, env):
        self.config = config
        self.env = env
        self.provider = self.credential_provider()

    def credential_provider(self) -> BaseProvider:
        creds = self.config['credentials']
        if creds == "azure_keyvault":
            return AzureKeyVaultProvider(self.config, self.env)
        elif creds == "environment_variables":
            return EnviromentCredentialsProvider(self.config, self.env)


class DockerRegistryNew(TakeoffCredentials):
    def __init__(self, config, env):
        super().__init__(config, env)

    def credentials(self):
        return self.provider.get_credentials('container_registry')


class DockerRegistry(KeyVaultCredentialsMixin):
    def credentials(self, config: dict) -> DockerCredentials:
        credential_kwargs = super()._transform_key_to_credential_kwargs(
            config["azure"]["keyvault_keys"][current_filename(__file__)]
        )
        return DockerCredentials(**credential_kwargs)
