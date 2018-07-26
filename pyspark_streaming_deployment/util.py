import os
from dataclasses import dataclass

from databricks_cli.sdk import ApiClient
from git import Repo
from msrestazure.azure_active_directory import ServicePrincipalCredentials


def get_branch() -> str:
    return os.environ['BUILD_SOURCEBRANCHNAME']


def get_tag() -> str:
    repo = Repo(search_parent_directories=True)
    return next((tag for tag in repo.tags if tag.commit == repo.head.commit), None)


def get_application_name() -> str:
    return os.environ['BUILD_DEFINITIONNAME']


def get_azure_sp_credentials(dtap: str) -> ServicePrincipalCredentials:
    azure_sp_username = os.environ['AZURE_SP_USERNAME']
    azure_sp_password = os.environ['AZURE_SP_PASSWORD']
    azure_sp_tenantid = os.environ['AZURE_SP_TENANTID']

    return ServicePrincipalCredentials(client_id=azure_sp_username,
                                       secret=azure_sp_password,
                                       tenant=azure_sp_tenantid)


def get_databricks_client(dtap: str) -> ApiClient:
    databricks_token = os.environ[f'AZURE_DATABRICKS_TOKEN_{dtap.lower()}']
    databricks_host = os.environ[f'AZURE_DATABRICKS_HOST_{dtap.lower()}']
    return ApiClient(host=databricks_host, token=databricks_token)
