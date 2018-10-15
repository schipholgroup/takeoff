import logging
import os
import re
from dataclasses import dataclass
from typing import Pattern, Callable, List

from azure.common.credentials import UserPassCredentials, ServicePrincipalCredentials
from azure.keyvault import KeyVaultClient
from azure.keyvault.models import SecretBundle
from azure.mgmt.cosmosdb import CosmosDB
from azure.storage.blob import BlockBlobService
from databricks_cli.sdk import ApiClient
from git import Repo
from jinja2 import Template
from yaml import load

RESOURCE_GROUP = "sdh{dtap}"
EVENTHUB_NAMESPACE = "sdheventhub{dtap}"
AZURE_LOCATION = "west europe"  # default to this Azure location
SHARED_REGISTRY = "sdhcontainerregistryshared.azurecr.io"


@dataclass(frozen=True)
class AzureSp(object):
    tenant: str
    username: str
    password: str


@dataclass(frozen=True)
class DockerCredentials(object):
    username: str
    password: str
    registry: str


@dataclass(frozen=True)
class Secret:
    key: str
    val: str

    @property
    def env_key(self):
        return self.key.upper().replace('-', '_')


@dataclass(frozen=True)
class CosmosCredentials(object):
    uri: str
    key: str

    @staticmethod
    def _get_cosmos_management_client(dtap: str) -> CosmosDB:
        subscription_id = get_subscription_id()
        credentials = get_azure_user_credentials(dtap)

        return CosmosDB(credentials, subscription_id)

    @staticmethod
    def _get_cosmos_instance(dtap: str) -> dict:
        return {
            "resource_group_name": f"sdh{dtap}".format(dtap=dtap),
            "account_name": f"sdhcosmos{dtap}".format(dtap=dtap),
        }

    @staticmethod
    def _get_cosmos_endpoint(cosmos: CosmosDB, cosmos_instance: dict):
        return (cosmos
                .database_accounts
                .get(**cosmos_instance)
                .document_endpoint
                )

    @staticmethod
    def get_cosmos_write_credentials(dtap: str) -> 'CosmosCredentials':
        formatted_dtap = dtap.lower()
        cosmos = CosmosCredentials._get_cosmos_management_client(formatted_dtap)
        cosmos_instance = CosmosCredentials._get_cosmos_instance(formatted_dtap)
        endpoint = CosmosCredentials._get_cosmos_endpoint(cosmos, cosmos_instance)

        key = (cosmos
               .database_accounts
               .list_keys(**cosmos_instance)
               .primary_master_key
               )

        return CosmosCredentials(endpoint, key)

    @staticmethod
    def get_cosmos_read_only_credentials(dtap: str) -> 'CosmosCredentials':
        formatted_dtap = dtap.lower()
        cosmos = CosmosCredentials._get_cosmos_management_client(formatted_dtap)
        cosmos_instance = CosmosCredentials._get_cosmos_instance(formatted_dtap)
        endpoint = CosmosCredentials._get_cosmos_endpoint(cosmos, cosmos_instance)

        key = (cosmos
               .database_accounts
               .list_read_only_keys(**cosmos_instance)
               .primary_readonly_master_key
               )

        return CosmosCredentials(endpoint, key)


def render_string_with_jinja(path: str, params: dict) -> str:
    with open(path) as file_:
        template = Template(file_.read())
    rendered = template.render(**params)
    return rendered


def render_file_with_jinja(path: str, params: dict, parse_function: Callable) -> dict:
    rendered = render_string_with_jinja(path, params)
    return parse_function(rendered)


def get_branch() -> str:
    return os.environ["BUILD_SOURCEBRANCHNAME"]


def get_tag() -> str:
    repo = Repo(search_parent_directories=True)
    return next((tag for tag in repo.tags if tag.commit == repo.head.commit), None)


def get_short_hash(n: int = 7) -> str:
    repo = Repo(search_parent_directories=True)
    sha = repo.head.object.hexsha
    return repo.git.rev_parse(sha, short=n)


def get_application_name() -> str:
    return os.environ["BUILD_DEFINITIONNAME"]


def get_docker_credentials() -> DockerCredentials:
    return DockerCredentials(
        username=os.environ["REGISTRY_USERNAME"],
        password=os.environ["REGISTRY_PASSWORD"],
        registry=SHARED_REGISTRY,
    )


def get_subscription_id() -> str:
    return os.environ["SUBSCRIPTION_ID"]


def get_azure_sp_credentials(dtap: str) -> ServicePrincipalCredentials:
    azure_sp = read_azure_sp(dtap)

    return ServicePrincipalCredentials(
        client_id=azure_sp.username, secret=azure_sp.password, tenant=azure_sp.tenant
    )


def read_azure_sp(dtap: str) -> AzureSp:
    azure_sp_tenantid = os.environ["AZURE_SP_TENANTID"]
    azure_sp_username = os.environ[f"AZURE_SP_USERNAME_{dtap.upper()}"]
    azure_sp_password = os.environ[f"AZURE_SP_PASSWORD_{dtap.upper()}"]

    return AzureSp(azure_sp_tenantid, azure_sp_username, azure_sp_password)


def get_shared_blob_service() -> BlockBlobService:
    return BlockBlobService(
        account_name=os.environ["AZURE_SHARED_BLOB_USERNAME"],
        account_key=os.environ["AZURE_SHARED_BLOB_PASSWORD"],
    )


def get_azure_user_credentials(dtap: str) -> UserPassCredentials:
    return UserPassCredentials(
        os.environ[f"AZURE_USERNAME_{dtap.upper()}"],
        os.environ[f"AZURE_PASSWORD_{dtap.upper()}"],
    )


def get_databricks_client(dtap: str) -> ApiClient:
    databricks_token = os.environ[f"AZURE_DATABRICKS_TOKEN_{dtap.upper()}"]
    databricks_host = os.environ["AZURE_DATABRICKS_HOST"]
    return ApiClient(host=databricks_host, token=databricks_token)


def get_matching_group(find_in: str, pattern: Pattern[str], group: int):
    match = pattern.search(find_in)

    if not match:
        raise ValueError(f"Couldn't find a match")

    found_groups = len(match.groups())
    if found_groups < group:
        raise IndexError(
            f"Couldn't find that many groups, the number of groups found is: {found_groups}"
        )
    return match.groups()[group]


def has_prefix_match(find_in: str, to_find: str, pattern: Pattern[str]):
    match = pattern.search(find_in)

    if match:
        return match.groups()[0] == to_find
    return False


def load_yaml(path: str) -> dict:
    with open(path, "r") as f:
        config_file = f.read()
    return load(config_file)


def docker_logging(f):
    def wrap(self, *args, **kwargs):
        logs = f(self, *args, **kwargs)
        try:
            print(logs.decode())
        except Exception as e:
            logging.error(e)
        return logs
    return wrap


@dataclass(frozen=True)
class IdAndKey:
    keyvault_id: str
    databricks_secret_key: str


@dataclass
class KeyVaultSecrets:
    secrets: List[Secret]

    @staticmethod
    def _extract_keyvault_ids_from(secrets: List[SecretBundle]) -> List[str]:
        """The returned json from Azure KeyVault contains the ids for each secrets, prepended with
        the vault url.

        This functions extracts only the actual key from the url/id

        https://sdhkeyvaultdev.vault.azure.net/secrets/flights-arrivals-cosmos-collection
        to
        flights-arrivals-cosmos-collection
        """
        return [_.id.split("/")[-1] for _ in secrets]

    @staticmethod
    def _filter_keyvault_ids(keyvault_ids: List[str], application_name) -> List[IdAndKey]:
        """Extracts the actual keys from the prefixed ids

        flights-arrivals-cosmos-collection
        to
        (flights-arrivals-cosmos-collection, cosmos-collection)
        """
        pattern = re.compile(rf"^({application_name})-([-A-z0-9]+)*")

        return [
            IdAndKey(_, get_matching_group(_, pattern, 1))
            for _ in keyvault_ids
            if has_prefix_match(_, application_name, pattern)
        ]

    @staticmethod
    def _retrieve_secrets(client: KeyVaultClient,
                          vault: str,
                          application_name: str) -> List[Secret]:
        secrets = list(client.get_secrets(vault))
        secrets_ids = KeyVaultSecrets._extract_keyvault_ids_from(secrets)
        secrets_filtered = KeyVaultSecrets._filter_keyvault_ids(secrets_ids, application_name)

        app_secrets = [
            Secret(
                _.databricks_secret_key,
                client.get_secret(vault, _.keyvault_id, "").value,
            )
            for _ in secrets_filtered
        ]

        return app_secrets

    def get_keyvault_secrets(dtap: str):
        application_name = get_application_name()
        keyvault_client = KeyVaultClient(get_azure_sp_credentials(dtap))
        vault = f"https://sdhkeyvault{dtap.lower()}.vault.azure.net/"
        return KeyVaultSecrets._retrieve_secrets(keyvault_client, vault, application_name)
