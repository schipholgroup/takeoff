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
    ConfigureEventhub,
    EventHubProducerPolicy, ConnectingString)
from tests.azure import takeoff_config

BASE_CONF = {'task': 'configureEventhub',
             'createConsumerGroups': [{'eventhubEntity': 'Dave', 'consumerGroup': 'Mustaine'}]}

TEST_ENV_VARS = {'AZURE_TENANTID': 'David',
                 'AZURE_KEYVAULT_SP_USERNAME_DEV': 'Doctor',
                 'AZURE_KEYVAULT_SP_PASSWORD_DEV': 'Who',
                 'CI_PROJECT_NAME': 'my_little_pony',
                 'CI_COMMIT_REF_SLUG': 'my-little-pony'}


@dataclass(frozen=True)
class MockEventhubClientResponse():
    name: str
    primary_connection_string: str = None


@mock.patch.dict(os.environ, TEST_ENV_VARS)
@pytest.fixture(scope="session")
def victim():
    m_client = mock.MagicMock()
    m_client.consumer_groups.list_by_event_hub.return_value = {MockEventhubClientResponse("group1"), MockEventhubClientResponse("group2")}
    m_client.consumer_groups.create_or_update.return_value = {}
    m_client.event_hubs.list_by_namespace.return_value = {MockEventhubClientResponse("hub1"), MockEventhubClientResponse("hub2")}
    m_client.event_hubs.list_authorization_rules.return_value = {MockEventhubClientResponse("rule1"), MockEventhubClientResponse("rule2")}
    m_client.event_hubs.list_keys.return_value = MockEventhubClientResponse('potatoes1', 'potato-connection')

    with mock.patch("takeoff.step.ApplicationName.get", return_value="my_little_pony"), \
         mock.patch("takeoff.azure.configure_eventhub.ConfigureEventhub._get_eventhub_client", return_value=m_client), \
         mock.patch("takeoff.azure.configure_eventhub.KeyVaultClient.vault_and_client", return_value=(None, None)):
        conf = {**takeoff_config(), **BASE_CONF}
        conf['azure'].update({"eventhub_naming": "eventhub{env}"})
        return ConfigureEventhub(ApplicationVersion('DEV', 'local', 'foo'), conf)


class TestConfigureEventhub(object):
    @mock.patch.dict(os.environ, TEST_ENV_VARS)
    @mock.patch("takeoff.step.KeyVaultClient.vault_and_client", return_value=(None, None))
    @mock.patch("takeoff.azure.configure_eventhub.ConfigureEventhub._get_eventhub_client", return_value=None)
    def test_validate_minimal_schema(self, _, __):
        conf = {**takeoff_config(), **BASE_CONF}
        conf['azure'].update({"eventhub_naming": "eventhub{env}"})

        ConfigureEventhub(ApplicationVersion("dev", "v", "branch"), conf)

    @mock.patch("takeoff.step.KeyVaultClient.vault_and_client", return_value=(None, None))
    @mock.patch("takeoff.azure.configure_eventhub.ConfigureEventhub._get_eventhub_client", return_value=None)
    def test_validate_minimal_schema_missing_key(self, _, __):
        conf = {**takeoff_config(), 'task': 'createEventhubConsumerGroups'}
        conf['azure'].update({"eventhub_naming": "eventhub{env}"})

        with pytest.raises(vol.MultipleInvalid):
            ConfigureEventhub(ApplicationVersion("dev", "v", "branch"), conf)

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

        with mock.patch('takeoff.azure.configure_eventhub.ConfigureEventhub.create_databricks_secrets') as databricks_call:
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
    def test_create_producer_policy_without_databricks(self, victim):
        policy = EventHubProducerPolicy('my-entity', False)

        with mock.patch('takeoff.azure.configure_eventhub.ConfigureEventhub.create_databricks_secrets') as databricks_call:
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

    @mock.patch("takeoff.azure.configure_eventhub.ConfigureEventhub._create_producer_policy")
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
    @mock.patch("takeoff.azure.configure_eventhub.ConfigureEventhub._create_consumer_group")
    def test_create_eventhub_consumer_groups(self, consumer_group_fun, victim):
        groups = [
            EventHubConsumerGroup(EventHub('my-group', 'my-namespace', 'entity1'), 'group1', False),
            EventHubConsumerGroup(EventHub('my-group', 'my-namespace', 'entity2'), 'group2', True),
        ]

        with mock.patch("takeoff.azure.configure_eventhub.ConfigureEventhub._eventhub_exists", return_value=True):
            with mock.patch("takeoff.azure.configure_eventhub.ConfigureEventhub._group_exists", return_value=False):
                victim.create_eventhub_consumer_groups(groups)

        calls = [mock.call(group=EventHubConsumerGroup(EventHub('my-group', 'my-namespace', 'entity1'), 'group1', False)),
                 mock.call(group=EventHubConsumerGroup(EventHub('my-group', 'my-namespace', 'entity2'), 'group2', True))]

        consumer_group_fun.assert_has_calls(calls)

    @mock.patch.dict(os.environ, TEST_ENV_VARS)
    def test_create_eventhub_consumer_group(self, victim):
        group = EventHubConsumerGroup(EventHub('my-rg', 'my-namespace', 'my-entity'), 'my-group', False)
        with mock.patch('takeoff.azure.configure_eventhub.ConfigureEventhub.create_databricks_secrets') as databricks_call:
            victim._create_consumer_group(group)

        victim.eventhub_client.consumer_groups.create_or_update.assert_called_with('my-rg',
                                                                                   'my-namespace',
                                                                                   'my-entity',
                                                                                   'my-group')

        databricks_call.assert_not_called()

    @mock.patch.dict(os.environ, TEST_ENV_VARS)
    def test_create_eventhub_consumer_group(self, victim):
        group = EventHubConsumerGroup(EventHub('my-rg', 'my-namespace', 'my-entity'), 'my-group', True)
        with mock.patch('takeoff.azure.configure_eventhub.ConfigureEventhub.create_databricks_secrets') as databricks_call:
            victim._create_consumer_group(group)

        victim.eventhub_client.consumer_groups.create_or_update.assert_called_with('my-rg',
                                                                                   'my-namespace',
                                                                                   'my-entity',
                                                                                   'my-group')

        databricks_call.assert_called_once()
