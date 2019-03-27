import logging
from typing import List

from azure.mgmt.eventhub import EventHubManagementClient
from azure.mgmt.relay.models import AccessRights

from runway.ApplicationVersion import ApplicationVersion
from runway.DeploymentStep import DeploymentStep
from runway.create_databricks_secrets import Secret, CreateDatabricksSecrets
from runway.credentials.application_name import ApplicationName
from runway.credentials.azure_active_directory_user import AzureUserCredentials
from runway.credentials.azure_databricks import Databricks
from runway.credentials.azure_subscription_id import AzureSubscriptionId

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class CreateEventhubProducerPolicies(DeploymentStep):
    def __init__(self, env: ApplicationVersion, config: dict):
        super().__init__(env, config)

    def run(self):
        policies = [policy["eventhubEntity"] for policy in self.config["policies"]]
        self.create_eventhub_producer_policies(policies)

    def create_eventhub_producer_policies(self, producer_policies: List[str]):
        formatted_dtap = self.env.environment.lower()
        eventhub_namespace = self.config["runway_common"]["eventhub_namespace"].format(dtap=formatted_dtap)
        resource_group = self.config["runway_azure"]["resource_group"].format(dtap=formatted_dtap)

        credentials = AzureUserCredentials(
            vault_name=self.vault_name, vault_client=self.vault_client
        ).credentials(self.config)
        eventhub_client = EventHubManagementClient(
            credentials, AzureSubscriptionId(self.vault_name, self.vault_client).subscription_id(self.config)
        )

        databricks_client = Databricks(self.vault_name, self.vault_client).api_client(self.config)
        application_name = ApplicationName().get(self.config)

        logger.info(f"Using Azure resource group: {resource_group}")
        logger.info(f"Using Azure namespace: {eventhub_namespace}")

        for policy in producer_policies:
            common_azure_parameters = {
                "resource_group_name": resource_group,
                "namespace_name": eventhub_namespace,
                "event_hub_name": policy + formatted_dtap,
                "authorization_rule_name": f"{ApplicationName().get(self.config)}-send-policy",
            }

            try:
                eventhub_client.event_hubs.create_or_update_authorization_rule(
                    **common_azure_parameters, rights=[AccessRights.send]
                )

                connection_string = eventhub_client.event_hubs.list_keys(
                    **common_azure_parameters
                ).primary_connection_string
            except Exception as e:
                logger.info("Could not create connection String. Make sure the Eventhub exists.")
                raise

            secret = Secret(f"{policy}-connection-string", connection_string)

            CreateDatabricksSecrets._add_secrets(databricks_client, application_name, [secret])
