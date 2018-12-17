from dataclasses import dataclass
from typing import Dict

from azure.mgmt.recoveryservicesbackup.models import Settings
from azure.storage.blob import BlockBlobService
from databricks_cli.sdk import ApiClient
from msrestazure.azure_active_directory import UserPassCredentials

from runway.ApplicationVersion import ApplicationVersion
from runway.KeyVaultSecrets import KeyVaultSecrets, Secret


@dataclass(frozen=True)
class DockerCredentials(object):
    username: str
    password: str
    registry: str


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class KeyVaultCredentialsMixin():
    def __init__(self, dtap, keys):
        self.secrets = self._common_credentials(dtap, keys)

    def _common_credentials(self, dtap, keys):
        secrets = KeyVaultSecrets.get_keyvault_secrets(dtap, 'common')
        indexed = {_.key: _ for _ in secrets}
        # Keyvault does not support _ and python does not support -, hence the 'replace'
        return {_: self._find_secret(_.name.replace('_', '-'), indexed) for _ in keys}

    def _find_secret(self, secret_key, secrets: Dict[str, Secret]):
        if secret_key not in secrets:
            raise ValueError(f"Could not find required key {secret_key}")
        return secrets[secret_key].val


class DtapKeyVaultCredentials(KeyVaultCredentialsMixin):
    def __init__(self, env: ApplicationVersion, config: dict):
        super().__init__(env.environment.lower(), config['runway_azure_keyvault_dtap_keys'])

    def azure_user_credentials(self) -> UserPassCredentials:
        return UserPassCredentials(
            self.secrets['azure_username'],
            self.secrets['azure_password']
        )

    def databricks_client(self) -> ApiClient:
        databricks_token = self.secrets['azure_databricks_token']
        databricks_host = self.secrets['azure_databricks_host']
        return ApiClient(host=databricks_host, token=databricks_token)


class SharedKeyvaultCredentials(KeyVaultCredentialsMixin):
    def __init__(self, config):
        self.config = config
        super().__init__('dev', config['runway_azure_keyvault_shared_keys'])

    def docker_credentials(self) -> DockerCredentials:
        return DockerCredentials(
            username=self.secrets['registry_username'],
            password=self.secrets['registry_password'],
            registry=self.config['runway_common_keys']['shared_registry']
        )

    def subscription_id(self) -> str:
        return self.secrets['subscription_id']

    def shared_blob_service(self) -> BlockBlobService:
        return BlockBlobService(
            account_name=self.secrets['azure_shared_blob_username'],
            account_key=self.secrets['azure_shared_blob_password'],
        )

    def artifact_store_settings(self) -> Settings:
        return Settings(repository_url=self.secrets['artifact_store_upload_url'],
                        username=self.secrets['artifact_store_username'],
                        password=self.secrets['artifact_store_password'])
