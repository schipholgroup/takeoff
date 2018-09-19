import os
from unittest import mock

from yaml import load

from sdh_deployment.ApplicationVersion import ApplicationVersion
from sdh_deployment.DeploymentStep import DeploymentStep
from sdh_deployment.create_appservice_and_webapp import CreateAppserviceAndWebapp
from sdh_deployment.create_databricks_secrets import CreateDatabricksSecrets
from sdh_deployment.create_eventhub_consumer_groups import (
    CreateEventhubConsumerGroups,
)
from sdh_deployment.deploy_to_databricks import DeployToDatabricks

environment_variables = {
    "WEBAPP_NAME": "my-app",
    "APPSERVICE_LOCATION": "west europe",
    "BUILD_DEFINITIONNAME": "my-build",
    "BUILD_SOURCEBRANCHNAME": "True",
    "REGISTRY_USERNAME": "user123",
    "REGISTRY_PASSWORD": "supersecret123",
}

env = ApplicationVersion("DEV", "abc123githash", 'some-branch')


@mock.patch.dict(os.environ, environment_variables)
@mock.patch("sdh_deployment.run_deployment.get_environment")
@mock.patch("sdh_deployment.run_deployment.load_yaml")
def test_deploy_web_app_service(mock_load_yaml, mock_get_version):
    mock_load_yaml.return_value = load(
        """
steps:
- task: deployWebAppService
    """
    )
    mock_get_version.return_value = env

    from sdh_deployment.run_deployment import main

    with mock.patch.object(CreateAppserviceAndWebapp, "run", return_value=None) as mock_task:
        main()
        mock_task.assert_called_once_with(env, {"task": "deployWebAppService"})


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

    with mock.patch.object(CreateEventhubConsumerGroups, "run", return_value=None) as mock_task:
        main()
        mock_task.assert_called_once_with(
            env, {
                'task': 'createEventhubConsumerGroups',
                'groups': [
                    {'eventhubEntity': 'sdhdevciss',
                     'consumerGroup': 'consumerGroupName1'},
                    {'eventhubEntity': 'sdhdevciss',
                     'consumerGroup': 'consumerGroupName2'}]
            }
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

    with mock.patch.object(CreateDatabricksSecrets, "run", return_value=None) as mock_task:
        main()
        mock_task.assert_called_once_with(env, {'task': 'createDatabricksSecrets'})


@mock.patch.dict(os.environ, environment_variables)
@mock.patch("sdh_deployment.run_deployment.get_environment")
@mock.patch("sdh_deployment.run_deployment.load_yaml")
def test_deploy_to_databricks(mock_load_yaml, mock_get_version):
    mock_load_yaml.return_value = load(
        """
steps:
- task: deployToDatabricks
  config_file_fn: databricks_job_config.json.j2
   """
    )
    mock_get_version.return_value = env

    from sdh_deployment.run_deployment import main

    with mock.patch.object(
            DeployToDatabricks, "run", return_value=None
    ) as mock_task:
        main()
        mock_task.assert_called_once_with(
            env,
            {
                'task': 'deployToDatabricks',
                'config_file_fn': 'databricks_job_config.json.j2'
            },
        )


def test_version_no_feature():
    env = ApplicationVersion("DEV", "SNAPSHOT", 'some-branch')
    assert not env.on_feature_branch


def test_version_is_feature():
    env = ApplicationVersion("DEV", "108fba3", 'some-branch')
    assert env.on_feature_branch


class MockedClass(DeploymentStep):
    def run(self, env: ApplicationVersion, config: dict):
        return 'yeah, science!'


@mock.patch.dict('sdh_deployment.deployment_step.deployment_steps', {'mocked': MockedClass})
def test_run_task():
    from sdh_deployment.run_deployment import run_task
    res = run_task(env, 'mocked', {'task': 'mocked', 'some_param': 'foo'})

    assert res == 'yeah, science!'
