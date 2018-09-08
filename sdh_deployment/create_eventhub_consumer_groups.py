import logging
import os
from azure.mgmt.eventhub import EventHubManagementClient
from azure.mgmt.relay.models import AccessRights
from dataclasses import dataclass
from typing import List, Set

from sdh_deployment.create_databricks_secrets import Secret, CreateDatabricksSecrets
from sdh_deployment.util import (
    get_azure_user_credentials,
    RESOURCE_GROUP,
    EVENTHUB_NAMESPACE,
    get_application_name,
    get_databricks_client,
    get_subscription_id,
)
from sdh_deployment.run_deployment import ApplicationVersion

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


@dataclass(frozen=True)
class ConsumerGroup(object):
    eventhub_entity: str
    consumer_group: str
    eventhub_namespace: str
    resource_group: str


@dataclass(frozen=True)
class EventHub(object):
    resource_group: str
    eventhub_namespace: str
    eventhub_entity: str


@dataclass(frozen=True)
class ConnectingString(object):
    eventhub_entity: str
    connection_string: str

    @property
    def eventhub_entity_without_environment(self):
        """The eventhub entity is postfixed with the environment, for example: 'sdhcisseventhubdev'.
        To have secrets in databricks environment agnostic, we remove that postfix.
        """
        return self.eventhub_entity[:-3]


@dataclass(frozen=True)
class EventHubConsumerGroup(object):
    eventhub_entity_name: str
    consumer_group: str


class CreateEventhubConsumerGroups:
    @staticmethod
    def _eventhub_exists(
        client: EventHubManagementClient, group: ConsumerGroup
    ) -> bool:
        hubs = list(
            client.event_hubs.list_by_namespace(
                group.resource_group, group.eventhub_namespace
            )
        )

        if group.eventhub_entity in set(_.name for _ in hubs):
            return True
        raise ValueError(
            f"Eventhub with name {group.eventhub_entity} does not exist. Please create it first"
        )

    @staticmethod
    def _group_exists(client: EventHubManagementClient, group: ConsumerGroup) -> bool:
        consumer_groups = list(
            client.consumer_groups.list_by_event_hub(
                group.resource_group, group.eventhub_namespace, group.eventhub_entity
            )
        )

        if group.consumer_group in set(_.name for _ in consumer_groups):
            print(
                f"Consumer group with name {group.consumer_group} in hub {group.eventhub_entity}"
                " already exists, not creating."
            )
            return True
        return False

    @staticmethod
    def _parse_consumer_groups() -> List[EventHubConsumerGroup]:
        consumer_group_input = os.environ["EVENTHUB_CONSUMER_GROUPS"]
        # colon (:) is used as separator between hub and consumer group. Any additional :'s
        # after the first one will be treated as part of the consumer group name.
        return [
            EventHubConsumerGroup(*[part for part in hub_group_pair.split(":", 1)])
            for hub_group_pair in consumer_group_input.split(",")
        ]

    @staticmethod
    def _get_requested_consumer_groups(
        parsed_groups: List[EventHubConsumerGroup], dtap: str
    ) -> List[ConsumerGroup]:
        eventhub_namespace = EVENTHUB_NAMESPACE.format(dtap=dtap.lower())
        resource_group = RESOURCE_GROUP.format(dtap=dtap.lower())

        return [
            ConsumerGroup(
                group.eventhub_entity_name + dtap.lower(),
                group.consumer_group,
                eventhub_namespace,
                resource_group,
            )
            for group in parsed_groups
        ]

    @staticmethod
    def _authorization_rules_exists(
        client: EventHubManagementClient, group: EventHub, name: str
    ) -> bool:
        logging.info(
            f"Retrieving rules, Resource Group {group.resource_group}, "
            f"Eventhub Namespace {group.eventhub_namespace}, "
            f"Eventhub Entity: {group.eventhub_entity}"
        )
        existing_policies = list(
            client.event_hubs.list_authorization_rules(
                group.resource_group, group.eventhub_namespace, group.eventhub_entity
            )
        )
        if name in set(_.name for _ in existing_policies):
            print(
                f"Authorization rule with name {name} in hub {group.eventhub_entity}"
                " already exists, not creating."
            )
            return True
        return False

    @staticmethod
    def _create_consumer_group(client: EventHubManagementClient, group: ConsumerGroup):
        client.consumer_groups.create_or_update(
            group.resource_group,
            group.eventhub_namespace,
            group.eventhub_entity,
            group.consumer_group,
        )

    @staticmethod
    def _create_connection_strings(
        client: EventHubManagementClient, eventhub_entities: Set[EventHub]
    ) -> List[ConnectingString]:
        policy_name = f"{get_application_name()}-policy"

        for group in eventhub_entities:
            if not CreateEventhubConsumerGroups._authorization_rules_exists(
                client, group, policy_name
            ):
                client.event_hubs.create_or_update_authorization_rule(
                    group.resource_group,
                    group.eventhub_namespace,
                    group.eventhub_entity,
                    policy_name,
                    [AccessRights.listen],
                )

        connection_strings = [
            client.event_hubs.list_keys(
                group.resource_group,
                group.eventhub_namespace,
                group.eventhub_entity,
                policy_name,
            ).primary_connection_string
            for group in eventhub_entities
        ]

        return [
            ConnectingString(hub.eventhub_entity, conn)
            for hub, conn in zip(eventhub_entities, connection_strings)
        ]

    @staticmethod
    def _get_unique_eventhubs(
        consumer_groups_to_create: List[ConsumerGroup]
    ) -> Set[EventHub]:
        return set(
            EventHub(_.resource_group, _.eventhub_namespace, _.eventhub_entity)
            for _ in consumer_groups_to_create
        )

    @staticmethod
    def create_eventhub_consumer_groups(
        env: ApplicationVersion, consumer_groups: List[EventHubConsumerGroup]
    ):
        logger.info(f"Using Azure resource group: {RESOURCE_GROUP}")
        logger.info(f"Using Azure namespace: {EVENTHUB_NAMESPACE}")

        credentials = get_azure_user_credentials(env.environment)
        eventhub_client = EventHubManagementClient(credentials, get_subscription_id())

        consumer_groups_to_create = CreateEventhubConsumerGroups._get_requested_consumer_groups(
            consumer_groups, env.environment
        )

        connection_strings = CreateEventhubConsumerGroups._create_connection_strings(
            eventhub_client,
            CreateEventhubConsumerGroups._get_unique_eventhubs(
                consumer_groups_to_create
            ),
        )

        for group in consumer_groups_to_create:
            if CreateEventhubConsumerGroups._eventhub_exists(
                eventhub_client, group
            ) and not CreateEventhubConsumerGroups._group_exists(
                eventhub_client, group
            ):
                CreateEventhubConsumerGroups._create_consumer_group(
                    eventhub_client, group
                )

        databricks_client = get_databricks_client(env.environment)
        application_name = get_application_name()

        # For each Eventhub we have a separate connection string which is set by a shared access policy
        # The different consumer groups can use this same shared access policy
        secrets = [
            Secret(
                f"{_.eventhub_entity_without_environment}-connection-string",
                _.connection_string,
            )
            for _ in connection_strings
        ]

        CreateDatabricksSecrets._create_scope(databricks_client, application_name)
        CreateDatabricksSecrets._add_secrets(
            databricks_client, application_name, secrets
        )
