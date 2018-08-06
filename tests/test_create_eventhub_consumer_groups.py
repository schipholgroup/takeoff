from unittest import mock

from pyspark_streaming_deployment import create_eventhub_consumer_groups as victim
from pyspark_streaming_deployment.create_eventhub_consumer_groups import ConsumerGroup

import importlib
import os


def test_get_consumer_groups_from_os_variables():
    eventhubs = 'hub1,hub2'.split(',')
    groups = 'hub1-your-app-name-group1,hub1-your-app-name-group2,hub2-your-app-name-group1'.split(',')
    consumer_groups = victim._get_requested_consumer_groups(eventhubs, groups, 'DEV')

    assert len(consumer_groups) == 3
    asserting_groups = [ConsumerGroup('hub1', 'your-app-name-group1', 'sdheventhubdev', 'sdhdev'),
                        ConsumerGroup('hub1', 'your-app-name-group2', 'sdheventhubdev', 'sdhdev'),
                        ConsumerGroup('hub2', 'your-app-name-group1', 'sdheventhubdev', 'sdhdev')]

    assert all(_ in consumer_groups for _ in asserting_groups)


def test_get_unique_eventhubs():
    groups = [ConsumerGroup('hub1', 'your-app-name-group1', 'sdheventhubdev', 'sdhdev'),
              ConsumerGroup('hub1', 'your-app-name-group2', 'sdheventhubdev', 'sdhdev'),
              ConsumerGroup('hub2', 'your-app-name-group1', 'sdheventhubdev', 'sdhdev')]

    uniques = victim._get_unique_eventhubs(groups)

    print(uniques)
    assert len(uniques) == 2
    assert all(_ in map(lambda x: x.eventhub_entity, uniques) for _ in ('hub1', 'hub2'))


@mock.patch.dict(os.environ, {'EVENTHUB_NAMESPACE': 'sdhcisseventhubnamespace'})
def test_get_custom_eventhub_namespace():
    # Make sure that the python module cache is flushed
    importlib.reload(victim)
    from pyspark_streaming_deployment.create_eventhub_consumer_groups import EVENTHUB_NAMESPACE
    assert EVENTHUB_NAMESPACE == 'sdhcisseventhubnamespace{dtap}'


def test_get_eventhub_namespace():
    # Make sure that the python module cache is flushed
    importlib.reload(victim)
    from pyspark_streaming_deployment.create_eventhub_consumer_groups import EVENTHUB_NAMESPACE
    assert EVENTHUB_NAMESPACE == 'sdheventhub{dtap}'
