import logging
from dataclasses import dataclass
from typing import List

from azure.mgmt.eventhub import EventHubManagementClient
from azure.mgmt.relay.models import AccessRights

from sdh_deployment.ApplicationVersion import ApplicationVersion
from sdh_deployment.DeploymentStep import DeploymentStep
from sdh_deployment.create_databricks_secrets import Secret, CreateDatabricksSecrets
from sdh_deployment.util import (
    get_azure_user_credentials,
    RESOURCE_GROUP,
    EVENTHUB_NAMESPACE,
    get_application_name,
    get_databricks_client,
    get_subscription_id,
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


@dataclass(frozen=True)
class EventHubProducerPolicy(object):
    eventhub_entity: str

    @property
    def eventhub_entity_without_environment(self):
        """The eventhub entity is postfixed with the environment, for example: 'sdhcisseventhubdev'.
        To have secrets in databricks environment agnostic, we remove that postfix.
        """
        return self.eventhub_entity[:-3]


class CreateEventhubProducerPolicies(DeploymentStep):
    def __init__(self, env: ApplicationVersion, config: dict):
        super().__init__(env, config)

    def run(self):
        policies = [
            EventHubProducerPolicy(policy["eventhubEntity"])
            for policy in self.config["policies"]
        ]
        self.create_eventhub_producer_policies(policies)

    def create_eventhub_producer_policies(self, producer_policies: List[EventHubProducerPolicy]):
        logger.info(f"Using Azure resource group: {RESOURCE_GROUP}")
        logger.info(f"Using Azure namespace: {EVENTHUB_NAMESPACE}")

        formatted_dtap = self.env.environment.lower()
        eventhub_namespace = EVENTHUB_NAMESPACE.format(dtap=formatted_dtap)
        resource_group = RESOURCE_GROUP.format(dtap=formatted_dtap)

        credentials = get_azure_user_credentials(self.env.environment)
        eventhub_client = EventHubManagementClient(credentials, get_subscription_id())

        databricks_client = get_databricks_client(self.env.environment)
        application_name = get_application_name()

        CreateDatabricksSecrets._create_scope(databricks_client, application_name)

        for policy in producer_policies:
            eventhub_client.event_hubs.create_or_update_authorization_rule(
                resource_group,
                eventhub_namespace,
                policy.eventhub_entity,
                f"{get_application_name()}-send-policy",
                [AccessRights.send],
            )

            connection_string = eventhub_client.event_hubs.list_keys(
                resource_group,
                eventhub_namespace,
                policy.eventhub_entity,
                f"{get_application_name()}-send-policy",
            ).primary_connection_string

            secret = Secret(
                f"{policy.eventhub_entity_without_environment}-connection-string",
                connection_string)

            CreateDatabricksSecrets._add_secrets(databricks_client, application_name, [secret])
