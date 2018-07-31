import json
import re
from collections import ChainMap
from dataclasses import dataclass
from pprint import pprint
from typing import List

from azure.keyvault import KeyVaultClient
from azure.keyvault.models import SecretBundle
from databricks_cli.sdk import ApiClient
from databricks_cli.secrets.api import SecretApi

from pyspark_streaming_deployment.util import get_application_name, get_branch, get_azure_sp_credentials, get_tag, \
    get_databricks_client


@dataclass
class Secret:
    key: str
    val: str


@dataclass
class IdAndKey:
    id: str
    key: str


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
        api.put_secret(scope_name, secret.key, secret.val, None)


def __list_secrets(client, scope_name):
    api = SecretApi(client)
    return api.list_secrets(scope_name)


def __extract_ids_from_keys(keys: List[SecretBundle]) -> List[IdAndKey]:
    """The returned json from Azure KeyVault contains the ids for each secrets, prepended with
    the vault url.

    This functions extracts only the actual key from the url/id
    """
    return [IdAndKey(key.id,
                     key.id.split('/')[-1])
            for key in keys]


def __filter_ids(ids: List[IdAndKey], application_name) -> List[IdAndKey]:
    """Extracts the actual keys from the prefixed ids"""
    regex = re.compile(rf'^({application_name})-([-A-z0-9]+)*')

    def get_match(key_name, idx):
        match = regex.search(key_name)
        return match.groups()[idx]

    def has_match(key_name: str):
        match = regex.search(key_name)
        return match and match.groups()[0] == application_name

    return [IdAndKey(_.id, get_match(_.key, 1)) for _ in ids if has_match(_.key)]


def __get_keyvault_secrets(client: KeyVaultClient, vault: str, application_name: str) -> List[Secret]:
    secrets = list(client.get_secrets(vault))
    secrets_ids = __extract_ids_from_keys(secrets)
    secrets_filtered = __filter_ids(secrets_ids, application_name)

    app_secrets = [Secret(key.key, client.get_secret(vault, key.id, '').value) for key in secrets_filtered]

    return app_secrets


def main():
    branch = get_branch()
    tag = get_tag()

    if tag:
        create_secrets(dtap='PRD')
    else:
        if branch == 'master':
            create_secrets(dtap='DEV')
        else:
            print(f'''Not a release (tag not available),
            nor master branch (branch = "{branch}". Not deploying''')


def create_secrets(dtap: str):
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


if __name__ == '__main__':
    main()
