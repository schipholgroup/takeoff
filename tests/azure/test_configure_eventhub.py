import os
from dataclasses import dataclass

import mock
import pytest
import voluptuous as vol
from azure.mgmt.relay.models import AccessRights

from takeoff.application_version import ApplicationVersion
from takeoff.azure.configure_eventhub import (
    EventHub,
    EventHubConsumerGroup,
    ConfigureEventHub,
    EventHubProducerPolicy, ConnectingString)
from takeoff.context import Context, ContextKey
from takeoff.credentials.Secret import Secret
from tests.azure import takeoff_config

BASE_CONF = {'task': 'configure_eventhub',
             'create_consumer_groups': [{'eventhub_entity_naming': 'Dave{env}', 'consumer_group': 'Mustaine'}]}

TEST_ENV_VARS = {'AZURE_TENANTID': 'David',
                 'AZURE_KEYVAULT_SP_USERNAME_DEV': 'Doctor',
                 'AZURE_KEYVAULT_SP_PASSWORD_DEV': 'Who',
                 'CI_PROJECT_NAME': 'my_little_pony',
                 'CI_COMMIT_REF_SLUG': 'my-little-pony'}


@dataclass(frozen=True)
class MockEventHubClientResponse():
    name: str
    primary_connection_string: str = None


@pytest.fixture(scope="session")
@mock.patch.dict(os.environ, TEST_ENV_VARS)
def victim():
    m_client = mock.MagicMock()
    m_client.consumer_groups.list_by_event_hub.return_value = {MockEventHubClientResponse("group1"), MockEventHubClientResponse("group2")}
    m_client.consumer_groups.create_or_update.return_value = {}
    m_client.event_hubs.list_by_namespace.return_value = {MockEventHubClientResponse("hub1"), MockEventHubClientResponse("hub2")}
    m_client.event_hubs.list_authorization_rules.return_value = {MockEventHubClientResponse("rule1"), MockEventHubClientResponse("rule2")}
    m_client.event_hubs.list_keys.return_value = MockEventHubClientResponse('potatoes1', 'potato-connection')

    with mock.patch("takeoff.step.KeyVaultClient.vault_and_client", return_value=(None, None)), \
         mock.patch("takeoff.azure.configure_eventhub.ConfigureEventHub._get_eventhub_client", return_value=m_client):
        conf = {**takeoff_config(), **BASE_CONF}
        conf['azure'].update({"eventhub_naming": "eventhub{env}"})
        return ConfigureEventHub(ApplicationVersion('DEV', 'local', 'foo'), conf)


class TestConfigureEventHub(object):
    @mock.patch("takeoff.step.KeyVaultClient.vault_and_client", return_value=(None, None))
    @mock.patch("takeoff.azure.configure_eventhub.ConfigureEventHub._get_eventhub_client", return_value=None)
    def test_validate_minimal_schema(self, _, __):
        conf = {**takeoff_config(), **BASE_CONF}
        conf['azure'].update({"eventhub_naming": "eventhub{env}"})

        ConfigureEventHub(ApplicationVersion("dev", "v", "branch"), conf)

    @mock.patch("takeoff.step.KeyVaultClient.vault_and_client", return_value=(None, None))
    @mock.patch("takeoff.azure.configure_eventhub.ConfigureEventHub._get_eventhub_client", return_value=None)
    def test_validate_minimal_schema_missing_key(self, _, __):
        conf = {**takeoff_config(), 'task': 'createEventHubConsumerGroups'}
        conf['azure'].update({"eventhub_naming": "eventhub{env}"})

        with pytest.raises(vol.MultipleInvalid):
            ConfigureEventHub(ApplicationVersion("dev", "v", "branch"), conf)

    def test_get_unique_eventhubs(self, victim):
        groups = [
            EventHubConsumerGroup(
                EventHub("sdhdev", "sdheventhubdev", "hub1dev"), "your-app-name-group1", False
            ),
            EventHubConsumerGroup(
                EventHub("sdhdev", "sdheventhubdev", "hub1dev"), "your-app-name-group2", False
            ),
            EventHubConsumerGroup(
                EventHub("sdhdev", "sdheventhubdev", "hub2dev"), "your-app-name-group1", False
            ),
        ]

        uniques = victim._get_unique_eventhubs(groups)

        assert len(uniques) == 2
        assert all(
            _ in map(lambda x: x.name, uniques)
            for _ in ("hub1dev", "hub2dev")
        )

    @mock.patch.dict(os.environ, TEST_ENV_VARS)
    def test_eventhub_exists(self, victim):
        hub = EventHubConsumerGroup(EventHub('some_resource_group', 'some_namespace', 'hub1'), 'some_group', False)
        assert victim._eventhub_exists(hub)

    @mock.patch.dict(os.environ, TEST_ENV_VARS)
    def test_eventhub_not_exists(self, victim):
        group = EventHubConsumerGroup(EventHub('some_resource_group', 'some_namespace', 'idontexist'), 'some_group', False)
        with pytest.raises(ValueError):
            victim._eventhub_exists(group)

    @mock.patch.dict(os.environ, TEST_ENV_VARS)
    def test_group_exists(self, victim):
        group = EventHubConsumerGroup(EventHub('some_resource_group', 'some_namespace', 'some_hub'), 'group1', False)
        assert victim._group_exists(group)

    @mock.patch.dict(os.environ, TEST_ENV_VARS)
    def test_group_not_exists(self, victim):
        group = EventHubConsumerGroup(EventHub('some_resource_group', 'some_namespace', 'some_hub'), 'idontexist', False)
        assert not victim._group_exists(group)

    @mock.patch.dict(os.environ, TEST_ENV_VARS)
    def test_create_producer_policy_with_databricks(self, victim):
        policy = EventHubProducerPolicy('my-entity', True)

        with mock.patch('takeoff.azure.configure_eventhub.ConfigureEventHub.create_databricks_secrets') as databricks_call:
            victim._create_producer_policy(policy=policy,
                                           resource_group='my-group',
                                           eventhub_namespace='my-namespace',
                                           application_name='my-name'
                                           )

        victim.eventhub_client.event_hubs.create_or_update_authorization_rule.assert_called_with(
            authorization_rule_name='my-name-send-policy',
            event_hub_name='my-entitydev',
            namespace_name='my-namespace',
            resource_group_name='my-group',
            rights=[AccessRights.send]
        )
        victim.eventhub_client.event_hubs.list_keys.assert_called_with(
            authorization_rule_name='my-name-send-policy',
            event_hub_name='my-entitydev',
            namespace_name='my-namespace',
            resource_group_name='my-group',
        )

        databricks_call.assert_called_once()

    @mock.patch.dict(os.environ, TEST_ENV_VARS)
    def test_create_eventhub_producer_policies_secrets(self, victim):
        policies = [EventHubProducerPolicy('entity1', False), EventHubProducerPolicy('entity2', False)]

        victim.create_eventhub_producer_policies(policies)

        assert Context().get(ContextKey.EVENTHUB_PRODUCER_POLICY_SECRETS) == [Secret('entity1-connection-string', 'potato-connection'),
                                                                              Secret('entity2-connection-string', 'potato-connection')]

    @mock.patch.dict(os.environ, TEST_ENV_VARS)
    def test_create_producer_policy_without_databricks(self, victim):
        policy = EventHubProducerPolicy('my-entity', False)

        with mock.patch('takeoff.azure.configure_eventhub.ConfigureEventHub.create_databricks_secrets') as databricks_call:
            victim._create_producer_policy(policy=policy,
                                           resource_group='my-group',
                                           eventhub_namespace='my-namespace',
                                           application_name='my-name'
                                           )

        victim.eventhub_client.event_hubs.create_or_update_authorization_rule.assert_called_with(
            authorization_rule_name='my-name-send-policy',
            event_hub_name='my-entitydev',
            namespace_name='my-namespace',
            resource_group_name='my-group',
            rights=[AccessRights.send]
        )
        victim.eventhub_client.event_hubs.list_keys.assert_called_with(
            authorization_rule_name='my-name-send-policy',
            event_hub_name='my-entitydev',
            namespace_name='my-namespace',
            resource_group_name='my-group',
        )
        databricks_call.assert_not_called()

    def test_authorization_rules_exists(self, victim):
        group = EventHub('my-group', 'my-namespace', 'my-entity')
        assert victim._authorization_rules_exists(group, 'rule1')

    def test_authorization_rules_not_exists(self, victim):
        group = EventHub('my-group', 'my-namespace', 'my-entity')
        assert not victim._authorization_rules_exists(group, 'idontexist')

    @mock.patch.dict(os.environ, TEST_ENV_VARS)
    def test_create_connection_strings(self, victim):
        entities = [
            EventHub('my-group', 'my-namespace', 'my-entity'),
            EventHub('your-group', 'your-namespace', 'your-entity')
        ]

        expected_result = [
            ConnectingString('my-entity', 'potato-connection'),
            ConnectingString('your-entity', 'potato-connection')
        ]

        result = victim._create_connection_strings(entities)

        assert result == expected_result

    @mock.patch.dict(os.environ, TEST_ENV_VARS)
    @mock.patch("takeoff.azure.configure_eventhub.ConfigureEventHub._create_producer_policy")
    def test_create_eventhub_producer_policies(self, producer_policy_fun, victim):
        policies = [
            EventHubProducerPolicy('entity1', False),
            EventHubProducerPolicy('entity2', True)
        ]

        victim.create_eventhub_producer_policies(policies)

        calls = [mock.call(policies[0], 'rgdev', 'eventhubdev', 'my_little_pony'),
                 mock.call(policies[1], 'rgdev', 'eventhubdev', 'my_little_pony')]

        producer_policy_fun.assert_has_calls(calls)

    @mock.patch.dict(os.environ, TEST_ENV_VARS)
    @mock.patch("takeoff.azure.configure_eventhub.ConfigureEventHub._create_consumer_group")
    def test_create_eventhub_consumer_groups(self, consumer_group_fun, victim):
        groups = [
            EventHubConsumerGroup(EventHub('my-group', 'my-namespace', 'entity1'), 'group1', False),
            EventHubConsumerGroup(EventHub('my-group', 'my-namespace', 'entity2'), 'group2', True),
        ]

        with mock.patch("takeoff.azure.configure_eventhub.ConfigureEventHub._eventhub_exists", return_value=True):
            with mock.patch("takeoff.azure.configure_eventhub.ConfigureEventHub._group_exists", return_value=False):
                victim.create_eventhub_consumer_groups(groups)

        calls = [mock.call(group=EventHubConsumerGroup(EventHub('my-group', 'my-namespace', 'entity1'), 'group1', False)),
                 mock.call(group=EventHubConsumerGroup(EventHub('my-group', 'my-namespace', 'entity2'), 'group2', True))]

        consumer_group_fun.assert_has_calls(calls)

    @mock.patch.dict(os.environ, TEST_ENV_VARS)
    def test_create_eventhub_consumer_group(self, victim):
        group = EventHubConsumerGroup(EventHub('my-rg', 'my-namespace', 'my-entity'), 'my-group', False)
        with mock.patch('takeoff.azure.configure_eventhub.ConfigureEventHub.create_databricks_secrets') as databricks_call:
            victim._create_consumer_group(group)

        victim.eventhub_client.consumer_groups.create_or_update.assert_called_with('my-rg',
                                                                                   'my-namespace',
                                                                                   'my-entity',
                                                                                   'my-group')

        databricks_call.assert_not_called()

    @mock.patch.dict(os.environ, TEST_ENV_VARS)
    def test_create_eventhub_consumer_group(self, victim):
        group = EventHubConsumerGroup(EventHub('my-rg', 'my-namespace', 'my-entity'), 'my-group', True)
        with mock.patch('takeoff.azure.configure_eventhub.ConfigureEventHub.create_databricks_secrets') as databricks_call:
            victim._create_consumer_group(group)

        victim.eventhub_client.consumer_groups.create_or_update.assert_called_with('my-rg',
                                                                                   'my-namespace',
                                                                                   'my-entity',
                                                                                   'my-group')

        databricks_call.assert_called_once()
