import os
from dataclasses import dataclass

from azure.common.credentials import UserPassCredentials, ServicePrincipalCredentials
from azure.storage.blob import BlockBlobService
from databricks_cli.sdk import ApiClient
from git import Repo
from typing import Pattern

RESOURCE_GROUP = "sdh{dtap}"
EVENTHUB_NAMESPACE = "sdheventhub{dtap}"
AZURE_LOCATION = "west europe"  # default to this Azure location


@dataclass(frozen=True)
class AzureSp(object):
    tenant: str
    username: str
    password: str


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
        account_name=os.environ['AZURE_SHARED_BLOB_USERNAME'],
        account_key=os.environ['AZURE_SHARED_BLOB_PASSWORD']
    )


def get_azure_user_credentials(dtap: str) -> UserPassCredentials:
    return UserPassCredentials(
        os.environ[f"AZURE_USERNAME_{dtap.upper()}"],
        os.environ[f"AZURE_PASSWORD_{dtap.upper()}"],
    )


def get_databricks_client(dtap: str) -> ApiClient:
    databricks_token = os.environ[f"AZURE_DATABRICKS_TOKEN_{dtap.upper()}"]
    databricks_host = os.environ[f"AZURE_DATABRICKS_HOST"]
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
