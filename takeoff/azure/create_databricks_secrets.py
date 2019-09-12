import abc
import logging
from pprint import pprint
from typing import List

import voluptuous as vol
from databricks_cli.secrets.api import SecretApi

from takeoff.application_version import ApplicationVersion
from takeoff.azure.credentials.databricks import Databricks
from takeoff.azure.credentials.keyvault import KeyVaultClient
from takeoff.azure.credentials.keyvault_credentials_provider import KeyVaultCredentialsMixin
from takeoff.credentials.DeploymentYamlEnvironmentVariablesMixin import (
    DeploymentYamlEnvironmentVariablesMixin,
)
from takeoff.credentials.secret import Secret
from takeoff.schemas import TAKEOFF_BASE_SCHEMA
from takeoff.step import Step, SubStep

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class CreateDatabricksSecretsMixin(object):
    def __init__(self):
        raise BaseException("Should not instantiate this class")

    def _scope_exists(self, scopes: dict, scope_name: str):
        return scope_name in set(_["name"] for _ in scopes["scopes"])

    @abc.abstractmethod
    def get_secret_api(self):
        pass

    def _create_scope(self, scope_name: str):
        scopes = self.get_secret_api().list_scopes()
        if not self._scope_exists(scopes, scope_name):
            self.get_secret_api().create_scope(scope_name, None)

    def _add_secrets(self, scope_name: str, secrets: List[Secret]):
        for secret in secrets:
            logger.info(f"Set secret {scope_name}: {secret.key}")
            self.get_secret_api().put_secret(scope_name, secret.key, secret.val, None)


SCHEMA = TAKEOFF_BASE_SCHEMA.extend(
    {vol.Required("task"): "create_databricks_secrets_from_vault"}, extra=vol.ALLOW_EXTRA
)


class CreateDatabricksSecretsFromVault(Step, CreateDatabricksSecretsMixin):
    """Will connect to the supplied vault and uses prefixed names to created databricks secrets.

    For example given list of secrets in the vault:

    - `this-app-name-secret-1`
    - `this-app-name-secret-2`
    - `a-different-app-name-secret-3`

    it will register `secret-1` and `secret-2` and their values under the databricks secret scope
    `this-app-name` and ignore all other secrets, such as `secret-3` as it does not match
    the `this-app-name` prefix.
    """

    def get_secret_api(self):
        return self.secret_api

    def __init__(self, env: ApplicationVersion, config: dict):
        super().__init__(env, config)
        self.vault_name, self.vault_client = KeyVaultClient.vault_and_client(self.config, self.env)
        self.databricks_client = Databricks(self.vault_name, self.vault_client).api_client(self.config)
        self.secret_api = SecretApi(self.databricks_client)

    def run(self):
        self.create_databricks_secrets()

    def create_databricks_secrets(self):
        secrets = self._combine_secrets(self.application_name)

        self._create_scope(self.application_name)
        self._add_secrets(self.application_name, secrets)

        logging.info(f'------  {len(secrets)} secrets created in "{self.env.environment}"')
        pprint(self.secret_api.list_secrets(self.application_name))

    def _combine_secrets(self, application_name: str):
        vault_secrets = KeyVaultCredentialsMixin(self.vault_name, self.vault_client).get_keyvault_secrets(
            application_name
        )
        deployment_secrets = DeploymentYamlEnvironmentVariablesMixin(
            self.env, self.config
        ).get_deployment_secrets()
        return list(set(vault_secrets + deployment_secrets))

    def schema(self) -> vol.Schema:
        return SCHEMA


class CreateDatabricksSecretFromValue(SubStep, CreateDatabricksSecretsMixin):
    """Not meant as a step but as a subconfiguration of an existing step such as `ConfigureEventhub`.

    This class will allow for the creation of databricks secrets related to a `Step`. For example the creation
    of eventhub connection strings as databricks secret.

    It will not do schema validation as it is assumed the schema has been validated by the `Step` itself.
    """

    def __init__(self, env: ApplicationVersion, config: dict):
        super().__init__(env, config)

        self.databricks_client = Databricks(self.vault_name, self.vault_client).api_client(self.config)
        self.secret_api = SecretApi(self.databricks_client)

    def get_secret_api(self):
        return self.secret_api
