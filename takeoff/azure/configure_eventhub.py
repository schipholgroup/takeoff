import logging
from dataclasses import dataclass
from typing import List, Set

import voluptuous as vol
from azure.mgmt.eventhub import EventHubManagementClient
from azure.mgmt.relay.models import AccessRights

from takeoff.application_version import ApplicationVersion
from takeoff.azure.create_databricks_secrets import CreateDatabricksSecretFromValue
from takeoff.azure.credentials.active_directory_user import ActiveDirectoryUserCredentials
from takeoff.azure.credentials.keyvault import KeyVaultClient
from takeoff.azure.credentials.subscription_id import SubscriptionId
from takeoff.azure.util import get_resource_group_name, get_eventhub_name
from takeoff.credentials.secret import Secret
from takeoff.schemas import TAKEOFF_BASE_SCHEMA
from takeoff.step import Step

logger = logging.getLogger(__name__)

SCHEMA = TAKEOFF_BASE_SCHEMA.extend(
    {
        vol.Required("task"): "configure_eventhub",
        vol.Optional("create_consumer_groups"): vol.All(
            vol.Length(min=1),
            [
                {
                    vol.Required("eventhub_entity"): str,
                    vol.Required("consumer_group"): str,
                    vol.Optional("create_databricks_secret", default=False): bool,
                }
            ],
        ),
        vol.Optional("create_producer_policies"): vol.All(
            vol.Length(min=1),
            [
                {
                    vol.Required("eventhub_entity"): str,
                    vol.Optional("producer_policy"): str,
                    vol.Optional("create_databricks_secret", default=False): bool,
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
    namespace: str
    name: str


@dataclass(frozen=True)
class EventHubConsumerGroup(object):
    eventhub: EventHub
    consumer_group: str
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
        self.vault_name, self.vault_client = KeyVaultClient.vault_and_client(self.config, self.env)
        self.eventhub_client = self._get_eventhub_client()

    def schema(self) -> vol.Schema:
        return SCHEMA

    def run(self):
        if "create_consumer_groups" in self.config:
            self._setup_consumer_groups()
        if "create_producer_policies" in self.config:
            self._setup_producer_policies()

    def _setup_consumer_groups(self):
        eventhub_namespace = get_eventhub_name(self.config, self.env)
        resource_group = get_resource_group_name(self.config, self.env)

        groups = [
            EventHubConsumerGroup(
                EventHub(
                    resource_group,
                    eventhub_namespace,
                    group["eventhub_entity"] + self.env.environment_formatted,
                ),
                group["consumer_group"],
                group["create_databricks_secret"],
            )
            for group in self.config["create_consumer_groups"]
        ]
        self.create_eventhub_consumer_groups(groups)

    def _setup_producer_policies(self):
        policies = [
            EventHubProducerPolicy(policy["eventhub_entity"], policy["create_databricks_secret"])
            for policy in self.config["create_producer_policies"]
        ]
        self.create_eventhub_producer_policies(policies)

    def create_eventhub_producer_policies(self, producer_policies: List[EventHubProducerPolicy]):
        eventhub_namespace = get_eventhub_name(self.config, self.env)
        resource_group = get_resource_group_name(self.config, self.env)

        logger.info(f"Using Azure resource group: {resource_group}")
        logger.info(f"Using Azure Eventhub namespace: {eventhub_namespace}")

        for policy in producer_policies:
            self._create_producer_policy(policy, resource_group, eventhub_namespace, self.application_name)

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
            self.eventhub_client.event_hubs.list_by_namespace(
                group.eventhub.resource_group, group.eventhub.namespace
            )
        )
        if group.eventhub.name in set(_.name for _ in hubs):
            return True
        raise ValueError(
            f"Eventhub with name {group.eventhub.name} does not exist. " f"Please create it first"
        )

    def _group_exists(self, group: EventHubConsumerGroup) -> bool:
        consumer_groups = list(
            self.eventhub_client.consumer_groups.list_by_event_hub(
                group.eventhub.resource_group, group.eventhub.namespace, group.eventhub.name
            )
        )

        if group.consumer_group in set(_.name for _ in consumer_groups):
            logging.warning(
                f"Consumer group with name {group.consumer_group} in hub {group.eventhub.name}"
                " already exists, not creating."
            )
            return True
        return False

    def _authorization_rules_exists(self, hub: EventHub, name: str) -> bool:
        logging.info(
            f"Retrieving rules, Resource Group {hub.resource_group}, "
            f"Eventhub Namespace {hub.namespace}, "
            f"Eventhub Entity: {hub.name}"
        )
        existing_policies = list(
            self.eventhub_client.event_hubs.list_authorization_rules(
                hub.resource_group, hub.namespace, hub.name
            )
        )
        if name in set(_.name for _ in existing_policies):
            print(f"Authorization rule with name {name} in hub {hub.name}" " already exists, not creating.")
            return True
        return False

    def create_databricks_secrets(self, secrets: List[Secret], application_name):
        databricks_secrets = CreateDatabricksSecretFromValue(self.env, self.config)
        databricks_secrets._create_scope(application_name)
        databricks_secrets._add_secrets(application_name, secrets)

    def _create_consumer_group(self, group: EventHubConsumerGroup):
        self.eventhub_client.consumer_groups.create_or_update(
            group.eventhub.resource_group, group.eventhub.namespace, group.eventhub.name, group.consumer_group
        )
        if group.create_databricks_secret:
            application_name = self.application_name
            entities = self._get_unique_eventhubs([group])
            connection_strings = self._create_connection_strings(eventhub_entities=entities)
            secrets = [
                Secret(f"{_.eventhub_entity_without_environment}-connection-string", _.connection_string)
                for _ in connection_strings
            ]

            self.create_databricks_secrets(secrets, application_name)

    def _create_connection_strings(self, eventhub_entities: Set[EventHub]) -> List[ConnectingString]:
        policy_name = f"{self.application_name}-policy"

        for hub in eventhub_entities:
            if not self._authorization_rules_exists(hub, policy_name):
                self.eventhub_client.event_hubs.create_or_update_authorization_rule(
                    hub.resource_group, hub.namespace, hub.name, policy_name, [AccessRights.listen]
                )

        connection_strings = [
            self.eventhub_client.event_hubs.list_keys(
                hub.resource_group, hub.namespace, hub.name, policy_name
            ).primary_connection_string
            for hub in eventhub_entities
        ]

        return [ConnectingString(hub.name, conn) for hub, conn in zip(eventhub_entities, connection_strings)]

    @staticmethod
    def _get_unique_eventhubs(consumer_groups_to_create: List[EventHubConsumerGroup]) -> Set[EventHub]:
        return set(
            EventHub(_.eventhub.resource_group, _.eventhub.namespace, _.eventhub.name)
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
