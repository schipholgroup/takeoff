import os
from dataclasses import dataclass
from typing import List

from azure.mgmt.eventhub import EventHubManagementClient
from azure.mgmt.eventhub.models import AccessKeys
from azure.mgmt.relay.models import AccessRights

from pyspark_streaming_deployment.create_databricks_secrets import __create_scope, __add_secrets, Secret
from pyspark_streaming_deployment.util import get_azure_user_credentials, RESOURCE_GROUP, \
    get_application_name, get_databricks_client, get_subscription_id

EVENTHUB_NAMESPACE = 'sdheventhub{dtap}'


@dataclass
class ConsumerGroup(object):
    eventhub_entity: str
    consumer_group: str
    eventhub_namespace: str
    resource_group: str


@dataclass
class ConnectingString(object):
    eventhub_entity: str
    connection_string: str


def _eventhub_exists(client: EventHubManagementClient, group: ConsumerGroup) -> bool:
    hubs = list(client.event_hubs.list_by_namespace(group.resource_group,
                                                    group.eventhub_namespace))

    if group.eventhub_entity in set(_.name for _ in hubs):
        return True
    raise ValueError(f'Eventhub with name {group.eventhub_entity} does not exist. Please create it first')


def _group_exists(client: EventHubManagementClient, group: ConsumerGroup) -> bool:
    consumer_groups = list(client.consumer_groups.list_by_event_hub(group.resource_group,
                                                                    group.eventhub_namespace,
                                                                    group.eventhub_entity))

    if group.consumer_group in set(_.name for _ in consumer_groups):
        print(f'Consumer group with name {group.consumer_group} in hub {group.eventhub_entity}'
              'already exists, not creating.')
        return True
    return False


def _get_requested_consumer_groups(dtap) -> List[ConsumerGroup]:
    eventhub_names: List[str] = os.environ['EVENTHUB_ENTITIES']
    consumer_group_names: List[str] = os.environ['EVENTHUB_CONSUMER_GROUPS']

    eventhub_namespace = EVENTHUB_NAMESPACE.format(dtap=dtap)
    resource_group = RESOURCE_GROUP.format(dtap=dtap)

    return [ConsumerGroup(hub,
                          group.replace(hub, '', 1),
                          eventhub_namespace,
                          resource_group)
            for hub in eventhub_names
            for group in consumer_group_names]


def _authorization_rules_exists(client: EventHubManagementClient, group: ConsumerGroup, name: str) -> bool:
    existing_policies = list(client.event_hubs.list_authorization_rules(group.resource_group,
                                                                        group.eventhub_namespace,
                                                                        group.eventhub_entity
                                                                        ))
    if name in set(_.name for _ in existing_policies):
        print(f'Authorization rule with name {name} in hub {group.eventhub_entity}'
              'already exists, not creating.')
        return True
    return False


def _create_consumer_group(client: EventHubManagementClient, group: ConsumerGroup) -> ConnectingString:
    policy_name = f"{get_application_name().replace('-','')}-policy"

    if not _authorization_rules_exists(client, group, policy_name):
        client.event_hubs.create_or_update_authorization_rule(group.resource_group,
                                                              group.eventhub_namespace,
                                                              group.eventhub_entity,
                                                              policy_name,
                                                              [AccessRights.listen])

    client.consumer_groups.create_or_update(group.resource_group,
                                            group.eventhub_namespace,
                                            group.eventhub_entity,
                                            group.consumer_group)

    key: AccessKeys = client.event_hubs.list_keys(group.resource_group,
                                                  group.eventhub_namespace,
                                                  group.eventhub_entity,
                                                  policy_name)

    return ConnectingString(group.eventhub_entity, key.primary_connection_string)


def create_consumer_groups(_: str, dtap: str):
    credentials = get_azure_user_credentials(dtap)
    eventhub_client = EventHubManagementClient(credentials, get_subscription_id())

    consumer_groups_to_create = _get_requested_consumer_groups(dtap)

    connection_strings = set(
        _create_consumer_group(eventhub_client, group)
        for group in consumer_groups_to_create
        if _eventhub_exists(eventhub_client, group) and not _group_exists(eventhub_client, group))

    databricks_client = get_databricks_client(dtap)

    application_name = get_application_name()

    secrets = [Secret(f'{_.eventhub_entity}-connection-string',
                      _.connection_string)
               for _ in connection_strings]

    __create_scope(databricks_client, application_name)
    __add_secrets(databricks_client, application_name, secrets)
