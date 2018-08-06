import logging
import re
from azure.keyvault import KeyVaultClient
from azure.keyvault.models import SecretBundle
from databricks_cli.sdk import ApiClient
from databricks_cli.secrets.api import SecretApi
from dataclasses import dataclass
from pprint import pprint
from typing import List

from pyspark_streaming_deployment.util import get_application_name, get_azure_sp_credentials, get_databricks_client, \
    has_prefix_match, get_matching_group

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


@dataclass
class Secret:
    key: str
    val: str


@dataclass
class IdAndKey:
    keyvault_id: str
    databricks_secret_key: str


def __scope_exists(scopes: dict, scope_name: str):
    return scope_name in set(_['name'] for _ in scopes['scopes'])


def __create_scope(client: ApiClient, scope_name: str):
    api = SecretApi(client)
    scopes = api.list_scopes()
    if not __scope_exists(scopes, scope_name):
        api.create_scope(scope_name, None)


def __add_secrets(client: ApiClient, scope_name: str, secrets: List[Secret]):
    api = SecretApi(client)
    for secret in secrets:
        logger.info(f'Set secret {scope_name}: {secret.key}')
        api.put_secret(scope_name, secret.key, secret.val, None)


def __list_secrets(client, scope_name):
    api = SecretApi(client)
    return api.list_secrets(scope_name)


def __extract_keyvault_ids_from(secrets: List[SecretBundle]) -> List[str]:
    """The returned json from Azure KeyVault contains the ids for each secrets, prepended with
    the vault url.

    This functions extracts only the actual key from the url/id

    https://sdhkeyvaultdev.vault.azure.net/secrets/flights-arrivals-cosmos-collection
    to
    flights-arrivals-cosmos-collection
    """
    return [_.id.split('/')[-1] for _ in secrets]


def __filter_keyvault_ids(keyvault_ids: List[str], application_name) -> List[IdAndKey]:
    """Extracts the actual keys from the prefixed ids

    flights-arrivals-cosmos-collection
    to
    (flights-arrivals-cosmos-collection, cosmos-collection)
    """
    pattern = re.compile(rf'^({application_name})-([-A-z0-9]+)*')

    return [IdAndKey(_, get_matching_group(_, pattern, 1))
            for _ in keyvault_ids
            if has_prefix_match(_, application_name, pattern)]


def __get_keyvault_secrets(client: KeyVaultClient, vault: str, application_name: str) -> List[Secret]:
    secrets = list(client.get_secrets(vault))
    secrets_ids = __extract_keyvault_ids_from(secrets)
    secrets_filtered = __filter_keyvault_ids(secrets_ids, application_name)

    app_secrets = [Secret(_.databricks_secret_key, client.get_secret(vault, _.keyvault_id, '').value)
                   for _ in secrets_filtered]

    return app_secrets


def create_secrets(_: str, dtap: str):
    application_name = get_application_name()
    azure_credentials = get_azure_sp_credentials(dtap)
    keyvault_client = KeyVaultClient(azure_credentials)
    vault = f'https://sdhkeyvault{dtap.lower()}.vault.azure.net/'

    secrets = __get_keyvault_secrets(keyvault_client, vault, application_name)
    databricks_client = get_databricks_client(dtap)

    __create_scope(databricks_client, application_name)
    __add_secrets(databricks_client, application_name, secrets)

    print(f'------  {len(secrets)} secrets created in "{application_name}"')
    pprint(__list_secrets(databricks_client, application_name))
