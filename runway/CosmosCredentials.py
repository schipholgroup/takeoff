from dataclasses import dataclass

from azure.mgmt.cosmosdb import CosmosDB

from runway.util import get_subscription_id, get_azure_user_credentials


@dataclass(frozen=True)
class CosmosInfo(object):
    client: CosmosDB
    instance: dict
    endpoint: str


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
    def _get_instance(dtap) -> CosmosInfo:
        lowered_dtap = dtap.lower()
        cosmos = CosmosCredentials._get_cosmos_management_client(lowered_dtap)
        cosmos_instance = CosmosCredentials._get_cosmos_instance(lowered_dtap)
        endpoint = CosmosCredentials._get_cosmos_endpoint(cosmos, cosmos_instance)
        return CosmosInfo(cosmos, cosmos_instance, endpoint)

    @staticmethod
    def get_cosmos_write_credentials(dtap: str) -> 'CosmosCredentials':
        cosmos = CosmosCredentials._get_instance(dtap)
        key = (cosmos.client
               .database_accounts
               .list_keys(**cosmos.instance)
               .primary_master_key
               )

        return CosmosCredentials(cosmos.endpoint, key)

    @staticmethod
    def get_cosmos_read_only_credentials(dtap: str) -> 'CosmosCredentials':
        cosmos = CosmosCredentials._get_instance(dtap)

        key = (cosmos.client
               .database_accounts
               .list_read_only_keys(**cosmos.instance)
               .primary_readonly_master_key
               )

        return CosmosCredentials(cosmos.endpoint, key)
