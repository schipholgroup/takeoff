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
from takeoff.azure.util import get_resource_group_name, get_eventhub_name, get_eventhub_entity_name
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
                    vol.Required("eventhub_entity_naming"): str,
                    vol.Required("consumer_group"): str,
                    vol.Optional("create_databricks_secret", default=False): bool,
                }
            ],
        ),
        vol.Optional("create_producer_policies"): vol.All(
            vol.Length(min=1),
            [
                {
                    vol.Required("eventhub_entity_naming"): str,
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
                    "myeventhub{env}"
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


class ConfigureEventHub(Step):
    """Configures EventHub

    Credentials for an AAD user (username, password) must be available
    in your cloud vault.

    Optionally propagate the consumer- or producer secrets to Databricks as secret.
    """

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
        """Constructs consumer groups for all EventHub entities requested."""
        groups = [
            EventHubConsumerGroup(
                EventHub(
                    get_resource_group_name(self.config, self.env),
                    get_eventhub_name(self.config, self.env),
                    get_eventhub_entity_name(group["eventhub_entity_naming"], self.env),
                ),
                group["consumer_group"],
                group["create_databricks_secret"],
            )
            for group in self.config["create_consumer_groups"]
        ]
        self.create_eventhub_consumer_groups(groups)

    def _setup_producer_policies(self):
        policies = [
            EventHubProducerPolicy(
                get_eventhub_entity_name(policy["eventhub_entity_naming"], self.env),
                policy["create_databricks_secret"],
            )
            for policy in self.config["create_producer_policies"]
        ]
        self.create_eventhub_producer_policies(policies)

    def create_eventhub_producer_policies(self, producer_policies: List[EventHubProducerPolicy]):
        """Constructs producer policies for all EventHub entities requested.

        Args:
            producer_policies: List of producer policies to create
        """
        eventhub_namespace = get_eventhub_name(self.config, self.env)
        resource_group = get_resource_group_name(self.config, self.env)

        logger.info(f"Using Azure resource group: {resource_group}")
        logger.info(f"Using Azure EventHub namespace: {eventhub_namespace}")

        for policy in producer_policies:
            self._create_producer_policy(policy, resource_group, eventhub_namespace, self.application_name)

    def _create_producer_policy(
        self,
        policy: EventHubProducerPolicy,
        resource_group: str,
        eventhub_namespace: str,
        application_name: str,
    ):
        """Creates given producer policy on EventHub. Optionally constructs Databricks secret
        containing the connection string for the policy.

        Args:
            policy: Name of the EventHub entity
            resource_group: The name of the resource group
            eventhub_namespace: The name of the EventHub namespace
            application_name: The name of this application
        """
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
            logger.info("Could not create connection String. Make sure the EventHub exists.")
            raise

        if policy.create_databricks_secret:
            secret = Secret(f"{policy.eventhub_entity_name}-connection-string", connection_string)
            self.create_databricks_secrets([secret], application_name)

    def _eventhub_exists(self, group: EventHubConsumerGroup) -> bool:
        """Checks if the EventHub entity exists

        Args:
            group: Object containing names of EventHub namespace and entity

        Returns:
            True if the entity exists, otherwise False
        """
        hubs = list(
            self.eventhub_client.event_hubs.list_by_namespace(
                group.eventhub.resource_group, group.eventhub.namespace
            )
        )
        if group.eventhub.name in set(_.name for _ in hubs):
            return True
        raise ValueError(
            f"EventHub with name {group.eventhub.name} does not exist. " f"Please create it first"
        )

    def _group_exists(self, group: EventHubConsumerGroup) -> bool:
        """Checks if the EventHub consumer group has already been made.
        Args:
            group: Object containing names of EventHub namespace and entity

        Returns:
            True if the consumer group exists, otherwise False
        """
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
        """Checks if the EventHub contains given authorization rule.

        Args:
            hub: Object containing information on the EventHub entity
            name: Name of the authorization rule

        Returns:
            True if the authorization rule exists, otherwise False
        """
        logging.info(
            f"Retrieving rules, Resource Group {hub.resource_group}, "
            f"EventHub Namespace {hub.namespace}, "
            f"EventHub Entity: {hub.name}"
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
        """Creates a Databricks secret from the provided secrets

        Args:
            secrets: A list of secrets
            application_name: The name of this application
        """
        databricks_secrets = CreateDatabricksSecretFromValue(self.env, self.config)
        databricks_secrets._create_scope(application_name)
        databricks_secrets._add_secrets(application_name, secrets)

    def _create_consumer_group(self, group: EventHubConsumerGroup):
        """Creates given consumer groups on EventHub. Optionally constructs Databricks secret
        containing the connection string for the consumer group.

        Args:
            group: Object containing names of EventHub namespace and entity
        """
        self.eventhub_client.consumer_groups.create_or_update(
            group.eventhub.resource_group, group.eventhub.namespace, group.eventhub.name, group.consumer_group
        )
        if group.create_databricks_secret:
            entities = self._get_unique_eventhubs([group])
            connection_strings = self._create_connection_strings(eventhub_entities=entities)
            secrets = [
                Secret(f"{_.eventhub_entity}-connection-string", _.connection_string)
                for _ in connection_strings
            ]

            self.create_databricks_secrets(secrets, self.application_name)

    def _create_connection_strings(self, eventhub_entities: Set[EventHub]) -> List[ConnectingString]:
        """Creates connections strings for all given EventHub entities.

        Args:
            eventhub_entities: List of objects containing EventHub metadata

        Returns:
            List of connection strings, one for each requested consumer group.
        """
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
    def _get_unique_eventhubs(eventhubs: List[EventHubConsumerGroup]) -> Set[EventHub]:
        """Deduplicated EventHub consumer groups from the Takeoff config

        Args:
            eventhubs: List of consumer groups to create

        Returns:
            Unique set of objects containing Evenhub metadata
        """
        return set(
            EventHub(_.eventhub.resource_group, _.eventhub.namespace, _.eventhub.name) for _ in eventhubs
        )

    def _get_eventhub_client(self) -> EventHubManagementClient:
        """Constructs an EventHub Management client

        Returns:
            An EventHub Management client
        """
        credentials = ActiveDirectoryUserCredentials(
            vault_name=self.vault_name, vault_client=self.vault_client
        ).credentials(self.config)
        return EventHubManagementClient(
            credentials, SubscriptionId(self.vault_name, self.vault_client).subscription_id(self.config)
        )

    def create_eventhub_consumer_groups(self, consumer_groups: List[EventHubConsumerGroup]):
        """Creates a new EventHub consumer group if one does not exist.

        Args:
            consumer_groups: A list of EventHubConsumerGroup containing the name of the consumer
            group to create.
        """
        for group in consumer_groups:
            if self._eventhub_exists(group) and not self._group_exists(group):
                self._create_consumer_group(group=group)
