import logging
from dataclasses import dataclass
from typing import List, Set

import voluptuous as vol
from azure.mgmt.eventhub import EventHubManagementClient
from azure.mgmt.relay.models import AccessRights

from runway.application_version import ApplicationVersion
from runway.azure.create_databricks_secrets import CreateDatabricksSecrets
from runway.azure.credentials.active_directory_user import ActiveDirectoryUserCredentials
from runway.azure.credentials.databricks import Databricks
from runway.azure.credentials.subscription_id import SubscriptionId
from runway.azure.util import get_resource_group_name, get_eventhub_name
from runway.credentials.Secret import Secret
from runway.credentials.application_name import ApplicationName
from runway.schemas import RUNWAY_BASE_SCHEMA
from runway.step import Step

logger = logging.getLogger(__name__)

SCHEMA = RUNWAY_BASE_SCHEMA.extend(
    {
        vol.Required("task"): "configureEventhub",
        vol.Optional("createConsumerGroups"): vol.All(
            vol.Length(min=1),
            [
                {
                    vol.Required("eventhubEntity"): str,
                    vol.Required("consumerGroup"): str,
                    vol.Optional("createDatabricksSecret", default=False): bool,
                }
            ],
        ),
        vol.Optional("createProducerPolicies"): vol.All(
            vol.Length(min=1),
            [
                {
                    vol.Required("eventhubEntity"): str,
                    vol.Required("producerPolicy"): str,
                    vol.Optional("createDatabricksSecret", default=False): bool,
                }
            ],
        ),
        "azure": {
            vol.Required(
                "eventhub_naming",
                description=(
                    "Naming convention for the resource."
                    "This should include the {env} parameter. For example"
                    "myeventhub_{env}"
                ),
            ): str
        },
    },
    extra=vol.ALLOW_EXTRA,
)


@dataclass(frozen=True)
class EventHub(object):
    resource_group: str
    eventhub_namespace: str
    eventhub_entity: str


@dataclass(frozen=True)
class EventHubConsumerGroup(object):
    eventhub_entity_name: str
    consumer_group: str
    eventhub_namespace: str
    resource_group: str
    create_databricks_secret: bool


@dataclass(frozen=True)
class EventHubProducerPolicy(object):
    eventhub_entity_name: str
    create_databricks_secret: bool


@dataclass(frozen=True)
class ConnectingString(object):
    eventhub_entity: str
    connection_string: str

    @property
    def eventhub_entity_without_environment(self):
        """The eventhub entity is postfixed with the environment, for example: 'eventhubdev'.
        To have secrets in databricks environment agnostic, we remove that postfix.
        """
        return self.eventhub_entity[:-3]


class ConfigureEventhub(Step):
    def __init__(self, env: ApplicationVersion, config: dict):
        super().__init__(env, config)

        self.eventhub_client = self._get_eventhub_client()

    def schema(self) -> vol.Schema:
        return SCHEMA

    def run(self):
        self._setup_consumer_groups()
        self._setup_producer_policies()

    def _setup_consumer_groups(self):
        eventhub_namespace = get_eventhub_name(self.config, self.env)
        resource_group = get_resource_group_name(self.config, self.env)

        groups = [
            EventHubConsumerGroup(
                group["eventhubEntity"] + self.env.environment_formatted,
                group["consumerGroup"],
                eventhub_namespace,
                resource_group,
                group["createDatabricksSecret"],
            )
            for group in self.config["createConsumerGroups"]
        ]
        self.create_eventhub_consumer_groups(groups)

    def _setup_producer_policies(self):
        policies = [
            EventHubProducerPolicy(policy["eventhubEntity"], policy["createDatabricksSecret"])
            for policy in self.config["createProducerPolicies"]
        ]
        self.create_eventhub_producer_policies(policies)

    def create_eventhub_producer_policies(self, producer_policies: List[EventHubProducerPolicy]):
        eventhub_namespace = get_eventhub_name(self.config, self.env)
        resource_group = get_resource_group_name(self.config, self.env)
        application_name = ApplicationName().get(self.config)

        logger.info(f"Using Azure resource group: {resource_group}")
        logger.info(f"Using Azure Eventhub namespace: {eventhub_namespace}")

        for policy in producer_policies:
            self._create_producer_policy(policy, resource_group, eventhub_namespace, application_name)

    def _create_producer_policy(
        self,
        policy: EventHubProducerPolicy,
        resource_group: str,
        eventhub_namespace: str,
        application_name: str,
    ):
        common_azure_parameters = {
            "resource_group_name": resource_group,
            "namespace_name": eventhub_namespace,
            "event_hub_name": policy.eventhub_entity_name + self.env.environment_formatted,
            "authorization_rule_name": f"{application_name}-send-policy",
        }

        try:
            self.eventhub_client.event_hubs.create_or_update_authorization_rule(
                **common_azure_parameters, rights=[AccessRights.send]
            )
            connection_string = self.eventhub_client.event_hubs.list_keys(
                **common_azure_parameters
            ).primary_connection_string
        except Exception as e:
            logger.info("Could not create connection String. Make sure the Eventhub exists.")
            raise

        if policy.create_databricks_secret:
            secret = Secret(f"{policy.eventhub_entity_name}-connection-string", connection_string)
            self.create_databricks_secrets([secret], application_name)

    def _eventhub_exists(self, group: EventHubConsumerGroup) -> bool:
        hubs = list(
            self.eventhub_client.event_hubs.list_by_namespace(group.resource_group, group.eventhub_namespace)
        )
        if group.eventhub_entity_name in set(_.name for _ in hubs):
            return True
        raise ValueError(
            f"Eventhub with name {group.eventhub_entity_name} does not exist. " f"Please create it first"
        )

    def _group_exists(self, group: EventHubConsumerGroup) -> bool:
        consumer_groups = list(
            self.eventhub_client.consumer_groups.list_by_event_hub(
                group.resource_group, group.eventhub_namespace, group.eventhub_entity_name
            )
        )

        if group.consumer_group in set(_.name for _ in consumer_groups):
            logging.warning(
                f"Consumer group with name {group.consumer_group} in hub {group.eventhub_entity_name}"
                " already exists, not creating."
            )
            return True
        return False

    def _authorization_rules_exists(self, group: EventHub, name: str) -> bool:
        logging.info(
            f"Retrieving rules, Resource Group {group.resource_group}, "
            f"Eventhub Namespace {group.eventhub_namespace}, "
            f"Eventhub Entity: {group.eventhub_entity}"
        )
        existing_policies = list(
            self.eventhub_client.event_hubs.list_authorization_rules(
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

    def create_databricks_secrets(self, secrets: List[Secret], application_name):
        databricks_client = Databricks(self.vault_name, self.vault_client).api_client(self.config)
        CreateDatabricksSecrets._create_scope(databricks_client, application_name)
        CreateDatabricksSecrets._add_secrets(databricks_client, application_name, secrets)

    def _create_consumer_group(self, group: EventHubConsumerGroup):
        self.eventhub_client.consumer_groups.create_or_update(
            group.resource_group, group.eventhub_namespace, group.eventhub_entity_name, group.consumer_group
        )
        if group.create_databricks_secret:
            application_name = ApplicationName().get(self.config)
            entities = self._get_unique_eventhubs([group])
            connection_strings = self._create_connection_strings(eventhub_entities=entities)
            secrets = [
                Secret(f"{_.eventhub_entity_without_environment}-connection-string", _.connection_string)
                for _ in connection_strings
            ]

            self.create_databricks_secrets(secrets, application_name)

    def _create_connection_strings(self, eventhub_entities: Set[EventHub]) -> List[ConnectingString]:
        policy_name = f"{ApplicationName().get(self.config)}-policy"

        for group in eventhub_entities:
            if not self._authorization_rules_exists(group, policy_name):
                self.eventhub_client.event_hubs.create_or_update_authorization_rule(
                    group.resource_group,
                    group.eventhub_namespace,
                    group.eventhub_entity,
                    policy_name,
                    [AccessRights.listen],
                )

        connection_strings = [
            self.eventhub_client.event_hubs.list_keys(
                group.resource_group, group.eventhub_namespace, group.eventhub_entity, policy_name
            ).primary_connection_string
            for group in eventhub_entities
        ]

        return [
            ConnectingString(hub.eventhub_entity, conn)
            for hub, conn in zip(eventhub_entities, connection_strings)
        ]

    @staticmethod
    def _get_unique_eventhubs(consumer_groups_to_create: List[EventHubConsumerGroup]) -> Set[EventHub]:
        return set(
            EventHub(_.resource_group, _.eventhub_namespace, _.eventhub_entity_name)
            for _ in consumer_groups_to_create
        )

    def _get_eventhub_client(self):
        credentials = ActiveDirectoryUserCredentials(
            vault_name=self.vault_name, vault_client=self.vault_client
        ).credentials(self.config)
        return EventHubManagementClient(
            credentials, SubscriptionId(self.vault_name, self.vault_client).subscription_id(self.config)
        )

    def create_eventhub_consumer_groups(self, consumer_groups: List[EventHubConsumerGroup]):
        for group in consumer_groups:
            if self._eventhub_exists(group) and not self._group_exists(group):
                self._create_consumer_group(group=group)
