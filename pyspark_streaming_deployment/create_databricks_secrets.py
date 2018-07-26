import json
from dataclasses import dataclass
from pprint import pprint
from typing import List

from azure.keyvault import KeyVaultClient
from databricks_cli.sdk import ApiClient
from databricks_cli.secrets.api import SecretApi

from pyspark_streaming_deployment.util import get_application_name, get_branch, get_azure_sp_credentials, get_tag, \
    get_databricks_client


@dataclass
class Secret:
    key: str
    val: str


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


def __get_keyvault_secrets(client: KeyVaultClient, vault: str, application_name: str) -> List[Secret]:
    secret_bundle = client.get_secret(vault, '', '')  # this gets ALL secrets in the vault
    secrets = json.loads(secret_bundle.value.replace("'", '"').lower())
    secret_ids = [secret['id'].split('/')[-1] for secret in secrets]

    filtered = [_.replace(application_name, '') for _ in secret_ids if _.startswith(application_name)]

    app_secrets = [Secret(key, client.get_secret(vault, key, '').value) for key in filtered]

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

    print(f'------  secrets created in "{scope_name}"')
    pprint(__list_secrets(databricks_client, application_name))


if __name__ == '__main__':
    main()
