import logging
from pprint import pprint
from typing import List

from databricks_cli.sdk import ApiClient
from databricks_cli.secrets.api import SecretApi

from runway.ApplicationVersion import ApplicationVersion
from runway.DeploymentStep import DeploymentStep
from runway.credentials.KeyVaultCredentialsMixin import Secret, KeyVaultCredentialsMixin
from runway.credentials.application_name import ApplicationName
from runway.credentials.azure_databricks import Databricks

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class CreateDatabricksSecrets(DeploymentStep):
    def __init__(self, env: ApplicationVersion, config: dict):
        super().__init__(env, config)

    def run(self):
        self.create_databricks_secrets()

    @staticmethod
    def _scope_exists(scopes: dict, scope_name: str):
        return scope_name in set(_["name"] for _ in scopes["scopes"])

    @staticmethod
    def _create_scope(client: ApiClient, scope_name: str):
        api = SecretApi(client)
        scopes = api.list_scopes()
        if not CreateDatabricksSecrets._scope_exists(scopes, scope_name):
            api.create_scope(scope_name, None)

    @staticmethod
    def _add_secrets(client: ApiClient, scope_name: str, secrets: List[Secret]):
        api = SecretApi(client)
        for secret in secrets:
            logger.info(f"Set secret {scope_name}: {secret.key}")
            api.put_secret(scope_name, secret.key, secret.val, None)

    @staticmethod
    def _list_secrets(client, scope_name):
        api = SecretApi(client)
        return api.list_secrets(scope_name)

    def create_databricks_secrets(self):
        application_name = ApplicationName().get(self.config)

        secrets = KeyVaultCredentialsMixin(self.vault_name, self.vault_client).get_keyvault_secrets(application_name)
        databricks_client = Databricks(self.vault_name, self.vault_client).api_client(self.config)

        self._create_scope(databricks_client, application_name)
        self._add_secrets(databricks_client, application_name, secrets)

        logging.info(f'------  {len(secrets)} secrets created in "{self.env.environment}"')
        pprint(self._list_secrets(databricks_client, application_name))
