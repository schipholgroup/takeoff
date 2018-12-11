import base64
import os
from dataclasses import dataclass
from typing import Pattern, Callable

from azure.common.credentials import UserPassCredentials, ServicePrincipalCredentials
from azure.storage.blob import BlockBlobService
from databricks_cli.sdk import ApiClient
from git import Repo
from jinja2 import Template
from twine.settings import Settings
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
    from runway.credentials import common_credentials, CommonCredentials
    creds = common_credentials('dev')
    return DockerCredentials(
        username=creds[CommonCredentials.registry_username],
        password=creds[CommonCredentials.registry_password],
        registry=SHARED_REGISTRY,
    )


def get_subscription_id() -> str:
    from runway.credentials import common_credentials, CommonCredentials
    creds = common_credentials('dev')
    return creds[CommonCredentials.subscription_id]


def get_azure_sp_credentials(dtap: str) -> ServicePrincipalCredentials:
    azure_sp = read_azure_sp(dtap)

    return ServicePrincipalCredentials(
        client_id=azure_sp.username, secret=azure_sp.password, tenant=azure_sp.tenant
    )


def read_azure_sp(dtap: str) -> AzureSp:
    azure_sp_tenantid = os.environ["AZURE_TENANTID"]
    azure_sp_username = os.environ[f"AZURE_KEYVAULT_USERNAME_{dtap.upper()}"]
    azure_sp_password = os.environ[f"AZURE_KEYVAULT_PASSWORD_{dtap.upper()}"]

    return AzureSp(azure_sp_tenantid, azure_sp_username, azure_sp_password)


def get_shared_blob_service() -> BlockBlobService:
    from runway.credentials import common_credentials, CommonCredentials
    creds = common_credentials('dev')
    return BlockBlobService(
        account_name=creds[CommonCredentials.azure_shared_blob_username],
        account_key=creds[CommonCredentials.azure_shared_blob_password],
    )


def b64_encode(s: str):
    return base64.b64encode(s.encode()).decode()


def get_azure_user_credentials(dtap: str) -> UserPassCredentials:
    from runway.credentials import common_credentials, CommonCredentials
    creds = common_credentials(dtap)
    return UserPassCredentials(
        creds[CommonCredentials.azure_username],
        creds[CommonCredentials.azure_password]
    )


def get_databricks_client(dtap: str) -> ApiClient:
    from runway.credentials import common_credentials, CommonCredentials
    creds = common_credentials(dtap)
    databricks_token = creds[CommonCredentials.azure_databricks_token]
    databricks_host = creds[CommonCredentials.azure_databricks_host]
    return ApiClient(host=databricks_host, token=databricks_token)


def get_artifact_store_settings() -> Settings:
    from runway.credentials import common_credentials, CommonCredentials
    creds = common_credentials('dev')
    return Settings(repository_url=creds[CommonCredentials.artifact_store_upload_url],
                    username=creds[CommonCredentials.artifact_store_username],
                    password=creds[CommonCredentials.artifact_store_password])


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


def log_docker(logs_iter):
    from pprint import pprint
    for line in logs_iter:
        pprint(line)
