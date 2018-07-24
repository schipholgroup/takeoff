import argparse
from argparse import Namespace
from dataclasses import dataclass

from databricks_cli.sdk import ApiClient
from databricks_cli.secrets.api import SecretApi

from typing import List

from pprint import pprint


@dataclass
class Secret:
    key: str
    val: str


def __scope_exists(scopes: dict, scope_name: str):
    return len([_ for _ in scopes['scopes']
                if _['name'] == scope_name
                ]) >= 1


def create_scope(client: ApiClient, scope_name: str):
    api = SecretApi(client)
    scopes = api.list_scopes()
    if not __scope_exists(scopes, scope_name):
        api.create_scope(scope_name, None)


def add_secrets(client: ApiClient, scope_name: str, secrets: List[Secret]):
    api = SecretApi(client)
    for secret in secrets:
        api.put_secret(scope_name, secret.key, secret.val, None)


def list_secrets(client, scope_name):
    api = SecretApi(client)
    return api.list_secrets(scope_name)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--token')
    parser.add_argument('--scope')
    parser.add_argument('--secrets', nargs='+')
    args: Namespace = parser.parse_args()

    databricks_host = 'https://westeurope.azuredatabricks.net'
    client = ApiClient(host=databricks_host, token=(args.token))

    scope_name = args.scope
    create_scope(client, scope_name)

    split = [_.split('=', 1) for _ in args.secrets]
    secrets = [Secret(_[0], _[1]) for _ in split]
    add_secrets(client, scope_name, secrets)

    print(f'------  secrets created in "{scope_name}"')
    pprint(list_secrets(client, scope_name))
