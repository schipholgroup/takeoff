import logging
from pprint import pprint
from typing import List

import voluptuous as vol
from databricks_cli.secrets.api import SecretApi

from takeoff.application_version import ApplicationVersion
from takeoff.azure.credentials.KeyVaultCredentialsMixin import KeyVaultCredentialsMixin
from takeoff.azure.credentials.databricks import Databricks
from takeoff.credentials.DeploymentYamlEnvironmentVariablesMixin import (
    DeploymentYamlEnvironmentVariablesMixin,
)
from takeoff.credentials.Secret import Secret
from takeoff.credentials.application_name import ApplicationName
from takeoff.schemas import TAKEOFF_BASE_SCHEMA
from takeoff.step import Step

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

SCHEMA = TAKEOFF_BASE_SCHEMA.extend({vol.Required("task"): "createDatabricksSecrets"}, extra=vol.ALLOW_EXTRA)


class CreateDatabricksSecrets(Step):
    def __init__(self, env: ApplicationVersion, config: dict):
        super().__init__(env, config)

        self.databricks_client = Databricks(self.vault_name, self.vault_client).api_client(self.config)
        self.secret_api = SecretApi(self.databricks_client)

    def schema(self) -> vol.Schema:
        return SCHEMA

    def run(self):
        self.create_databricks_secrets()

    def _scope_exists(self, scopes: dict, scope_name: str):
        return scope_name in set(_["name"] for _ in scopes["scopes"])

    def _create_scope(self, scope_name: str):
        scopes = self.secret_api.list_scopes()
        if not self._scope_exists(scopes, scope_name):
            self.secret_api.create_scope(scope_name, None)

    def _add_secrets(self, scope_name: str, secrets: List[Secret]):
        for secret in secrets:
            logger.info(f"Set secret {scope_name}: {secret.key}")
            self.secret_api.put_secret(scope_name, secret.key, secret.val, None)

    def create_databricks_secrets(self):
        application_name = ApplicationName().get(self.config)

        secrets = self._combine_secrets(application_name)

        self._create_scope(application_name)
        self._add_secrets(application_name, secrets)

        logging.info(f'------  {len(secrets)} secrets created in "{self.env.environment}"')
        pprint(self.secret_api.list_secrets(application_name))

    def _combine_secrets(self, application_name):
        vault_secrets = KeyVaultCredentialsMixin(self.vault_name, self.vault_client).get_keyvault_secrets(
            application_name
        )
        deployment_secrets = DeploymentYamlEnvironmentVariablesMixin(
            self.env, self.config
        ).get_deployment_secrets()
        print(vault_secrets)
        print(deployment_secrets)
        return list(set(vault_secrets + deployment_secrets))

