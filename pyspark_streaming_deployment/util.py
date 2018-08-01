import os
from typing import Pattern

from azure.common.credentials import UserPassCredentials, ServicePrincipalCredentials
from databricks_cli.sdk import ApiClient
from git import Repo

RESOURCE_GROUP = 'sdh{dtap}'


def get_branch() -> str:
    return os.environ['BUILD_SOURCEBRANCHNAME']


def get_tag() -> str:
    repo = Repo(search_parent_directories=True)
    return next((tag for tag in repo.tags if tag.commit == repo.head.commit), None)


def get_application_name() -> str:
    return os.environ['BUILD_DEFINITIONNAME']


def get_subscription_id() -> str:
    return os.environ['SUBSCRIPTION_ID']


def get_azure_sp_credentials(dtap: str) -> ServicePrincipalCredentials:
    if dtap.lower() == 'dev':
        azure_sp_username = os.environ['AZURE_SP_USERNAME']
        azure_sp_password = os.environ['AZURE_SP_PASSWORD']
        azure_sp_tenantid = os.environ['AZURE_SP_TENANTID']
    elif dtap.lower() == 'prd':  # Prematurely include logic for multiple service principles
        azure_sp_username = os.environ['AZURE_SP_USERNAME']
        azure_sp_password = os.environ['AZURE_SP_PASSWORD']
        azure_sp_tenantid = os.environ['AZURE_SP_TENANTID']

    return ServicePrincipalCredentials(client_id=azure_sp_username,
                                       secret=azure_sp_password,
                                       tenant=azure_sp_tenantid)


def get_azure_user_credentials(dtap: str) -> UserPassCredentials:
    return UserPassCredentials(
        os.environ[f'AZURE_USERNAME_{dtap.upper()}'],
        os.environ[f'AZURE_PASSWORD_{dtap.upper()}']
    )


def get_databricks_client(dtap: str) -> ApiClient:
    databricks_token = os.environ[f'AZURE_DATABRICKS_TOKEN_{dtap.upper()}']
    databricks_host = os.environ[f'AZURE_DATABRICKS_HOST_{dtap.upper()}']
    return ApiClient(host=databricks_host, token=databricks_token)


def get_matching_group(find_in: str, pattern: Pattern[str], group: int):
    match = pattern.search(find_in)

    if not match:
        raise ValueError(f"Couldn't find a match")

    found_groups = len(match.groups())
    if found_groups < group:
        raise IndexError(f"Couldn't find that many groups, the number of groups found is: {found_groups}")
    return match.groups()[group]


def has_prefix_match(find_in: str, to_find: str, pattern: Pattern[str]):
    match = pattern.search(find_in)

    if match:
        return match.groups()[0] == to_find
    return False
