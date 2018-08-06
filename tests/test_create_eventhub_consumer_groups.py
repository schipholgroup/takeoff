from pyspark_streaming_deployment import create_eventhub_consumer_groups as victim
from pyspark_streaming_deployment.create_eventhub_consumer_groups import ConsumerGroup


def test_get_consumer_groups_from_os_variables():
    eventhub_names = 'hub1,hub2'.split(',')
    consumer_group_names = 'hub1-your-app-name-group1,hub1-your-app-name-group2,hub2-your-app-name-group1'.split(',')
    consumer_groups = victim._get_requested_consumer_groups(eventhub_names, consumer_group_names, 'DEV')

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
