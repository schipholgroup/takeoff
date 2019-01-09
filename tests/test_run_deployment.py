import os
from unittest import mock

import pytest

from runway.ApplicationVersion import ApplicationVersion
from runway.DeploymentStep import DeploymentStep
from runway.create_appservice_and_webapp import CreateAppserviceAndWebapp
from runway.create_databricks_secrets import CreateDatabricksSecrets
from runway.create_eventhub_consumer_groups import (
    CreateEventhubConsumerGroups,
)
from runway.deploy_to_databricks import DeployToDatabricks
from runway.run_deployment import run_task

environment_variables = {
    "WEBAPP_NAME": "my-app",
    "APPSERVICE_LOCATION": "west europe",
    "BUILD_DEFINITIONNAME": "my-build",
    "BUILD_SOURCEBRANCHNAME": "True",
    "REGISTRY_USERNAME": "user123",
    "REGISTRY_PASSWORD": "supersecret123",
}

env = ApplicationVersion("DEV", "abc123githash", 'some-branch')


def test_no_run_task():
    with pytest.raises(ValueError):
        run_task(env, 'foo', {})


@mock.patch.dict(os.environ, environment_variables)
@mock.patch("runway.run_deployment.get_environment")
@mock.patch("runway.run_deployment.load_yaml")
@mock.patch.object(CreateAppserviceAndWebapp, 'run', return_value=None)
def test_deploy_web_app_service(_, mock_load_yaml, mock_get_version):
    mock_get_version.return_value = env

    def load(s):
        if s == 'deployment.yml':
            return {'steps': [{'task': 'deployWebAppService'}]}
        elif s == 'runway_config.yaml':
            return {}

    # Since we're loading 2 yamls we need a side effect that mocks both
    mock_load_yaml.side_effect = load

    from runway.run_deployment import main

    with mock.patch.object(CreateAppserviceAndWebapp, "__init__", return_value=None) as mock_task:
        main()
        mock_task.assert_called_once_with(env, {'task': 'deployWebAppService'})


@mock.patch.dict(os.environ, environment_variables)
@mock.patch("runway.run_deployment.get_environment")
@mock.patch("runway.run_deployment.load_yaml")
@mock.patch.object(CreateEventhubConsumerGroups, 'run', return_value=None)
def test_create_eventhub_consumer_groups(_, mock_load_yaml, mock_get_version):
    def load(s):
        if s == 'deployment.yml':
            return {'steps': [{'task': 'createEventhubConsumerGroups',
                               'groups': [{'eventhubEntity': 'sdhdevciss', 'consumerGroup': 'consumerGroupName1'},
                                          {'eventhubEntity': 'sdhdevciss', 'consumerGroup': 'consumerGroupName2'}]
                               }]}
        elif s == 'runway_config.yaml':
            return {}

    # Since we're loading 2 yamls we need a side effect that mocks both
    mock_load_yaml.side_effect = load

    mock_get_version.return_value = env

    from runway.run_deployment import main

    with mock.patch.object(CreateEventhubConsumerGroups, "__init__", return_value=None) as mock_task:
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
@mock.patch("runway.run_deployment.get_environment")
@mock.patch("runway.run_deployment.load_yaml")
@mock.patch.object(CreateDatabricksSecrets, 'run', return_value=None)
def test_create_databricks_secret(_, mock_load_yaml, mock_get_version):
    def load(s):
        if s == 'deployment.yml':
            return {'steps': [{'task': 'createDatabricksSecrets'}]}
        elif s == 'runway_config.yaml':
            return {}

    # Since we're loading 2 yamls we need a side effect that mocks both
    mock_load_yaml.side_effect = load
    mock_get_version.return_value = env

    from runway.run_deployment import main

    with mock.patch.object(CreateDatabricksSecrets, "__init__", return_value=None) as mock_task:
        main()
        mock_task.assert_called_once_with(env, {'task': 'createDatabricksSecrets'})


@mock.patch.dict(os.environ, environment_variables)
@mock.patch("runway.run_deployment.get_environment")
@mock.patch("runway.run_deployment.load_yaml")
@mock.patch.object(DeployToDatabricks, 'run', return_value=None)
def test_deploy_to_databricks(_, mock_load_yaml, mock_get_version):
    def load(s):
        if s == 'deployment.yml':
            return {'steps': [{'task': 'deployToDatabricks', 'config_file_fn': 'databricks_job_config.json.j2'}]}
        elif s == 'runway_config.yaml':
            return {}

    # Since we're loading 2 yamls we need a side effect that mocks both
    mock_load_yaml.side_effect = load
    mock_get_version.return_value = env

    from runway.run_deployment import main

    with mock.patch.object(
            DeployToDatabricks, "__init__", return_value=None
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
    def __init__(self, env: ApplicationVersion, config: dict):
        super().__init__(env, config)

    def run(self):
        return 'yeah, science!'


@mock.patch.dict('runway.deployment_step.deployment_steps', {'mocked': MockedClass})
@mock.patch("runway.DeploymentStep.AzureKeyvaultClient.credentials", return_value=(None, None))
def test_run_task(_):
    from runway.run_deployment import run_task
    res = run_task(env, 'mocked', {'task': 'mocked', 'some_param': 'foo'})

    assert res == 'yeah, science!'
