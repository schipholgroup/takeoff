import os
from unittest import mock

from pyspark_streaming_deployment import create_eventhub_consumer_groups as victim
from pyspark_streaming_deployment.create_eventhub_consumer_groups import ConsumerGroup

from pyspark_streaming_deployment.create_eventhub_consumer_groups import EventHubConsumerGroup


def test_get_requested_consumer_groups():
    consumer_groups = victim._get_requested_consumer_groups([EventHubConsumerGroup('hub1', 'my-app-group1')], 'DEV')
    print(consumer_groups)
    assert len(consumer_groups) == 1
    asserting_groups = [ConsumerGroup('hub1dev', 'my-app-group1', 'sdheventhubdev', 'sdhdev')]
    assert all(_ in consumer_groups for _ in asserting_groups)


def test_get_unique_eventhubs():
    groups = [ConsumerGroup('hub1dev', 'your-app-name-group1', 'sdheventhubdev', 'sdhdev'),
              ConsumerGroup('hub1dev', 'your-app-name-group2', 'sdheventhubdev', 'sdhdev'),
              ConsumerGroup('hub2dev', 'your-app-name-group1', 'sdheventhubdev', 'sdhdev')]

    uniques = victim._get_unique_eventhubs(groups)

    assert len(uniques) == 2
    assert all(_ in map(lambda x: x.eventhub_entity, uniques) for _ in ('hub1dev', 'hub2dev'))


@mock.patch.dict(os.environ, {'EVENTHUB_CONSUMER_GROUPS': 'hub1:group1-my-app,hub1:group2-my-app,hub2:group1-my-app'})
def test_valid_consumer_groups_parsing():
    expected_groups = [EventHubConsumerGroup('hub1', 'group1-my-app'),
                       EventHubConsumerGroup('hub1', 'group2-my-app'),
                       EventHubConsumerGroup('hub2', 'group1-my-app')]
    consumer_groups = victim._parse_consumer_groups()
    assert len(consumer_groups) == 3
    assert all(_ in consumer_groups for _ in expected_groups)
