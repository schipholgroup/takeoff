from dataclasses import dataclass

from azure.mgmt.cosmosdb import CosmosDB

from runway.ApplicationVersion import ApplicationVersion
from runway.credentials.azure_active_directory_user import AzureUserCredentials
from runway.credentials.azure_keyvault import azure_keyvault_client
from runway.util import subscription_id


@dataclass(frozen=True)
class CosmosInfo(object):
    client: CosmosDB
    instance: dict
    endpoint: str


@dataclass(frozen=True)
class CosmosCredentials(object):
    uri: str
    key: str


class Cosmos(object):
    def __init__(self, env: ApplicationVersion, config: dict):
        self.env = env
        self.config = config

    def _get_cosmos_management_client(self) -> CosmosDB:
        vault, client = azure_keyvault_client(self.config, self.env)
        credentials = AzureUserCredentials(vault_name=vault, vault_client=client).credentials(self.config)
        return CosmosDB(credentials, subscription_id(self.config))

    def _get_cosmos_instance(self) -> dict:
        dtap = self.env.environment.lower()
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

    def _get_instance(self) -> CosmosInfo:
        cosmos = self._get_cosmos_management_client()
        cosmos_instance = self._get_cosmos_instance()
        endpoint = self._get_cosmos_endpoint(cosmos, cosmos_instance)
        return CosmosInfo(cosmos, cosmos_instance, endpoint)

    def get_cosmos_write_credentials(self) -> CosmosCredentials:
        cosmos = self._get_instance()
        key = (cosmos.client
               .database_accounts
               .list_keys(**cosmos.instance)
               .primary_master_key
               )

        return CosmosCredentials(cosmos.endpoint, key)

    def get_cosmos_read_only_credentials(self) -> CosmosCredentials:
        cosmos = self._get_instance()

        key = (cosmos.client
               .database_accounts
               .list_read_only_keys(**cosmos.instance)
               .primary_readonly_master_key
               )

        return CosmosCredentials(cosmos.endpoint, key)
