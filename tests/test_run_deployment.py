import os
from unittest import mock

from yaml import load

from sdh_deployment.deploy_to_adls import DeployToAdls
from sdh_deployment.create_appservice_and_webapp import (
    CreateAppserviceAndWebapp
)
from sdh_deployment.create_eventhub_consumer_groups import (
    CreateEventhubConsumerGroups,
    EventHubConsumerGroup,
)
from sdh_deployment.create_databricks_secrets import (
    CreateDatabricksSecrets
)
from sdh_deployment.deploy_to_databricks import DeployToDatabricks

from sdh_deployment.run_deployment import ApplicationVersion

environment_variables = {
    "WEBAPP_NAME": "my-app",
    "APPSERVICE_LOCATION": "west europe",
    "BUILD_DEFINITIONNAME": "my-build",
    "BUILD_SOURCEBRANCHNAME": "True",
    "DOCKER_REGISTRY_URL": "https://abc.frl",
    "DOCKER_REGISTRY_USERNAME": "user123",
    "DOCKER_REGISTRY_PASSWORD": "supersecret123",
}

env = ApplicationVersion("DEV", "abc123githash")


@mock.patch.dict(os.environ, environment_variables)
@mock.patch("sdh_deployment.run_deployment.get_environment")
@mock.patch("sdh_deployment.run_deployment.load_yaml")
def test_deploy_to_adls(mock_load_yaml, mock_get_version):
    mock_load_yaml.return_value = load(
        """
steps:
- task: deployToAdls
    """
    )
    mock_get_version.return_value = env

    from sdh_deployment.run_deployment import main

    with mock.patch.object(
        DeployToAdls, "deploy_to_adls", return_value=None
    ) as mock_task:
        main()
        mock_task.assert_called_once_with(env)


@mock.patch.dict(os.environ, environment_variables)
@mock.patch("sdh_deployment.run_deployment.get_environment")
@mock.patch("sdh_deployment.run_deployment.load_yaml")
def test_deploy_web_app_service(mock_load_yaml, mock_get_version):
    mock_load_yaml.return_value = load(
        """
steps:
- task: deployWebAppService
  appServiceName: name
  appServiceSkuName: S1
  appServiceSkuCapacity: 1
  appServiceSkuTier: Basic
    """
    )
    mock_get_version.return_value = env

    from sdh_deployment.run_deployment import main

    with mock.patch.object(
        CreateAppserviceAndWebapp, "create_appservice_and_webapp", return_value=None
    ) as mock_task:
        main()
        mock_task.assert_called_once_with(
            env,
            {
                "task": "deployWebAppService",
                "appServiceName": "name",
                "appServiceSkuName": "S1",
                "appServiceSkuCapacity": 1,
                "appServiceSkuTier": "Basic",
            },
        )


@mock.patch.dict(os.environ, environment_variables)
@mock.patch("sdh_deployment.run_deployment.get_environment")
@mock.patch("sdh_deployment.run_deployment.load_yaml")
def test_create_eventhub_consumer_groups(mock_load_yaml, mock_get_version):
    mock_load_yaml.return_value = load(
        """
steps:
- task: createEventhubConsumerGroups
  groups:
    - eventhubEntity: sdhdevciss
      consumerGroup: consumerGroupName1
    - eventhubEntity: sdhdevciss
      consumerGroup: consumerGroupName2
    """
    )
    mock_get_version.return_value = env

    from sdh_deployment.run_deployment import main

    with mock.patch.object(
        CreateEventhubConsumerGroups,
        "create_eventhub_consumer_groups",
        return_value=None,
    ) as mock_task:
        main()
        mock_task.assert_called_once_with(
            env,
            [
                EventHubConsumerGroup(
                    eventhub_entity_name="sdhdevciss",
                    consumer_group="consumerGroupName1",
                ),
                EventHubConsumerGroup(
                    eventhub_entity_name="sdhdevciss", consumer_group="consumerGroupName2"
                ),
            ],
        )


@mock.patch.dict(os.environ, environment_variables)
@mock.patch("sdh_deployment.run_deployment.get_environment")
@mock.patch("sdh_deployment.run_deployment.load_yaml")
def test_create_databricks_secret(mock_load_yaml, mock_get_version):
    mock_load_yaml.return_value = load(
        """
steps:
- task: createDatabricksSecrets
    """
    )
    mock_get_version.return_value = env

    from sdh_deployment.run_deployment import main

    with mock.patch.object(
        CreateDatabricksSecrets, "create_databricks_secrets", return_value=None
    ) as mock_task:
        main()
        mock_task.assert_called_once_with(env)


@mock.patch.dict(os.environ, environment_variables)
@mock.patch("sdh_deployment.run_deployment.get_environment")
@mock.patch("sdh_deployment.run_deployment.load_yaml")
def test_deploy_to_databricks(mock_load_yaml, mock_get_version):
    mock_load_yaml.return_value = load(
        """
steps:
- task: deployToDatabricks
  config:  >
    {
      "name": "__generated_value__",
      "new_cluster": {
        "spark_version": "4.2.x-scala2.11",
        "node_type_id": "Standard_DS3_v2",
        "spark_conf": {
          "spark.sql.warehouse.dir": "dbfs:/mnt/sdh/data/raw/managedtables",
          "spark.databricks.delta.preview.enabled": "true",
          "spark.sql.hive.metastore.jars": "builtin",
          "spark.sql.execution.arrow.enabled": "true",
          "spark.sql.hive.metastore.version": "1.2.1"
        },
        "spark_env_vars": {
          "PYSPARK_PYTHON": "/databricks/python3/bin/python3"
        },
        "num_workers": 2,
        "cluster_log_conf": {
          "dbfs": {
            "destination": "dbfs:/mnt/sdh/logs/{name}"
          }
        }
      },
      "email_notifications": {
        "on_start": ["b5u1o2u2g4r7q3c2@digital-airport.slack.com"],
        "on_success": ["b5u1o2u2g4r7q3c2@digital-airport.slack.com"],
        "on_failure": ["b5u1o2u2g4r7q3c2@digital-airport.slack.com"]
      },
      "max_retries": 5,
      "libraries": [
        {
          "jar": "dbfs:/mnt/sdh/libraries/spark-cosmos-sink/spark-cosmos-sink-0.2.5.jar"
        },
        {
          "jar": "dbfs:/FileStore/jars/08b488fa_3fff_46f9_ba99_177a5c7eb0b2-spark_flights_eventhub_source_assembly_0_0_3_5-f2e4b.jar"
        }
      ],
      "spark_python_task": {
        "python_file": "__generated_value__",
        "parameters": "__generated_list__"
      }
    }
    """
    )
    mock_get_version.return_value = env

    from sdh_deployment.run_deployment import main

    with mock.patch.object(
        DeployToDatabricks, "deploy_to_databricks", return_value=None
    ) as mock_task:
        main()
        mock_task.assert_called_once_with(
            env,
            {
                "name": "__generated_value__",
                "new_cluster": {
                    "spark_version": "4.2.x-scala2.11",
                    "node_type_id": "Standard_DS3_v2",
                    "spark_conf": {
                        "spark.sql.warehouse.dir": "dbfs:/mnt/sdh/data/raw/managedtables",
                        "spark.databricks.delta.preview.enabled": "true",
                        "spark.sql.hive.metastore.jars": "builtin",
                        "spark.sql.execution.arrow.enabled": "true",
                        "spark.sql.hive.metastore.version": "1.2.1",
                    },
                    "spark_env_vars": {
                        "PYSPARK_PYTHON": "/databricks/python3/bin/python3"
                    },
                    "num_workers": 2,
                    "cluster_log_conf": {
                        "dbfs": {"destination": "dbfs:/mnt/sdh/logs/{name}"}
                    },
                },
                "email_notifications": {
                    "on_start": ["b5u1o2u2g4r7q3c2@digital-airport.slack.com"],
                    "on_success": ["b5u1o2u2g4r7q3c2@digital-airport.slack.com"],
                    "on_failure": ["b5u1o2u2g4r7q3c2@digital-airport.slack.com"],
                },
                "max_retries": 5,
                "libraries": [
                    {
                        "jar": "dbfs:/mnt/sdh/libraries/spark-cosmos-sink/spark-cosmos-sink-0.2.5.jar"
                    },
                    {
                        "jar": "dbfs:/FileStore/jars/08b488fa_3fff_46f9_ba99_177a5c7eb0b2-spark_flights_eventhub_source_assembly_0_0_3_5-f2e4b.jar"
                    },
                ],
                "spark_python_task": {
                    "python_file": "__generated_value__",
                    "parameters": "__generated_list__",
                },
            },
        )
