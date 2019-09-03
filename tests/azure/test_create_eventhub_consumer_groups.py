import os
import unittest
from unittest import mock

import pytest
import voluptuous as vol

from runway.ApplicationVersion import ApplicationVersion
from runway.azure.create_eventhub_consumer_groups import (
    ConsumerGroup,
    EventHubConsumerGroup,
    CreateEventhubConsumerGroups as victim,
)
from tests.azure import runway_config

BASE_CONF = {'task': 'createEventhubConsumerGroups',
             "groups": [{"eventhubEntity": "Dave", "consumerGroup": "Mustaine"}],
             }


class TestCreateEventhubConsumerGroups(unittest.TestCase):
    @mock.patch("runway.DeploymentStep.KeyvaultClient.vault_and_client", return_value=(None, None))
    def test_validate_minimal_schema(self, _):
        conf = {**runway_config(), **BASE_CONF}
        conf['runway_azure'].update({"eventhub_naming": "eventhub{env}"})

        victim(ApplicationVersion("dev", "v", "branch"), conf)

    @mock.patch("runway.DeploymentStep.KeyvaultClient.vault_and_client", return_value=(None, None))
    def test_validate_minimal_schema_missing_key(self, _):
        conf = {**runway_config(), 'task': 'createEventhubConsumerGroups'}
        with pytest.raises(vol.MultipleInvalid):
            victim(ApplicationVersion("dev", "v", "branch"), conf)

    @mock.patch("runway.DeploymentStep.KeyvaultClient.vault_and_client", return_value=(None, None))
    def test_get_requested_consumer_groups(self, _):
        env = ApplicationVersion('DEV', 'local', 'foo')
        config = {**runway_config(),
                  **BASE_CONF}
        config['runway_azure'].update({"eventhub_naming": "eventhub{env}"})
        consumer_groups = victim(env, config)._get_requested_consumer_groups(
            [EventHubConsumerGroup("hub1", "my-app-group1")])
        assert len(consumer_groups) == 1
        asserting_groups = [
            ConsumerGroup("hub1dev", "my-app-group1", "eventhubdev", "rgdev")
        ]
        assert all(_ in consumer_groups for _ in asserting_groups)

    def test_get_unique_eventhubs(self):
        groups = [
            ConsumerGroup(
                "hub1dev", "your-app-name-group1", "sdheventhubdev", "sdhdev"
            ),
            ConsumerGroup(
                "hub1dev", "your-app-name-group2", "sdheventhubdev", "sdhdev"
            ),
            ConsumerGroup(
                "hub2dev", "your-app-name-group1", "sdheventhubdev", "sdhdev"
            ),
        ]

        uniques = victim._get_unique_eventhubs(groups)

        assert len(uniques) == 2
        assert all(
            _ in map(lambda x: x.eventhub_entity, uniques)
            for _ in ("hub1dev", "hub2dev")
        )

    @mock.patch.dict(
        os.environ,
        {
            "EVENTHUB_CONSUMER_GROUPS": "hub1:group1-my-app,hub1:group2-my-app,hub2:group1-my-app"
        },
    )
    def test_valid_consumer_groups_parsing(self):
        expected_groups = [
            EventHubConsumerGroup("hub1", "group1-my-app"),
            EventHubConsumerGroup("hub1", "group2-my-app"),
            EventHubConsumerGroup("hub2", "group1-my-app"),
        ]
        consumer_groups = victim._parse_consumer_groups()
        assert len(consumer_groups) == 3
        assert all(_ in consumer_groups for _ in expected_groups)
