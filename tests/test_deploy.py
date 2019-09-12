import os
import sys
from unittest import mock

import pytest
import voluptuous as vol

from takeoff.application_version import ApplicationVersion
from takeoff.azure.configure_eventhub import ConfigureEventhub
from takeoff.azure.create_databricks_secrets import CreateDatabricksSecretsFromVault
from takeoff.azure.deploy_to_databricks import DeployToDatabricks
from takeoff.deploy import main
from takeoff.deploy import run_task, add_takeoff_plugin_paths, find_env_function
from takeoff.step import Step
from tests.azure import takeoff_config

environment_variables = {
    "WEBAPP_NAME": "my-app",
    "APPSERVICE_LOCATION": "west europe",
    "CI_PROJECT_NAME": "my-build",
    "CI_COMMIT_REF_NAME": "True",
    "REGISTRY_USERNAME": "user123",
    "REGISTRY_PASSWORD": "supersecret123",
}

env = ApplicationVersion("DEV", "abc123githash", 'some-branch')

conf_ext = {"environment_keys": {"application_name": "CI_PROJECT_NAME"}}


def filename(s):
    return f".takeoff/{s}.yml"


def test_no_run_task():
    with pytest.raises(ValueError):
        run_task(env, 'foo', {})


@mock.patch.dict(os.environ, environment_variables)
@mock.patch("takeoff.deploy.get_full_yaml_filename", side_effect=filename)
@mock.patch("takeoff.deploy.get_environment")
@mock.patch("takeoff.deploy.load_yaml")
@mock.patch.object(ConfigureEventhub, 'run', return_value=None)
def test_create_eventhub_consumer_groups(_, mock_load_yaml, mock_get_version, __):
    def load(s):
        if s == '.takeoff/deployment.yml':
            return {'steps': [{'task': 'configureEventhub',
                               'createConsumerGroups': [{'eventhubEntity': 'sdhdevciss', 'consumerGroup': 'consumerGroupName1'},
                                                        {'eventhubEntity': 'sdhdevciss', 'consumerGroup': 'consumerGroupName2'}]
                               }]}
        elif s == '.takeoff/config.yml':
            return {}

    # Since we're loading 2 yamls we need a side effect that mocks both
    mock_load_yaml.side_effect = load

    mock_get_version.return_value = env

    with mock.patch.object(ConfigureEventhub, "__init__", return_value=None) as mock_task:
        main()
        mock_task.assert_called_once_with(
            env, {
                'task': 'configureEventhub',
                'createConsumerGroups': [
                    {'eventhubEntity': 'sdhdevciss',
                     'consumerGroup': 'consumerGroupName1'},
                    {'eventhubEntity': 'sdhdevciss',
                     'consumerGroup': 'consumerGroupName2'}]
            }
        )


@mock.patch.dict(os.environ, environment_variables)
@mock.patch("takeoff.deploy.get_full_yaml_filename", side_effect=filename)
@mock.patch("takeoff.deploy.get_environment")
@mock.patch("takeoff.deploy.load_yaml")
@mock.patch.object(CreateDatabricksSecretsFromVault, 'run', return_value=None)
def test_create_databricks_secret(_, mock_load_yaml, mock_get_version, __):
    def load(s):
        if s == '.takeoff/deployment.yml':
            return {'steps': [{'task': 'createDatabricksSecretsFromVault'}]}
        elif s == '.takeoff/config.yml':
            return {}

    # Since we're loading 2 yamls we need a side effect that mocks both
    mock_load_yaml.side_effect = load
    mock_get_version.return_value = env

    with mock.patch.object(CreateDatabricksSecretsFromVault, "__init__", return_value=None) as mock_task:
        main()
        mock_task.assert_called_once_with(env, {'task': 'createDatabricksSecretsFromVault'})


@mock.patch.dict(os.environ, environment_variables)
@mock.patch("takeoff.deploy.get_full_yaml_filename", side_effect=filename)
@mock.patch("takeoff.deploy.get_environment")
@mock.patch("takeoff.deploy.load_yaml")
@mock.patch.object(DeployToDatabricks, 'run', return_value=None)
def test_deploy_to_databricks(_, mock_load_yaml, mock_get_version, __):
    def load(s):
        if s == '.takeoff/deployment.yml':
            return {'steps': [{'task': 'deployToDatabricks', 'config_file_fn': 'databricks_job_config.json.j2'}]}
        elif s == '.takeoff/config.yml':
            return {}

    # Since we're loading 2 yamls we need a side effect that mocks both
    mock_load_yaml.side_effect = load
    mock_get_version.return_value = env

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


class MockedClass(Step):
    def __init__(self, env: ApplicationVersion, config: dict):
        super().__init__(env, config)

    def run(self):
        return 'yeah, science!'

    def schema(self) -> vol.Schema:
        return vol.Schema({}, extra=vol.ALLOW_EXTRA)


@mock.patch.dict(os.environ, environment_variables)
@mock.patch.dict('takeoff.steps.steps', {'mocked': MockedClass})
@mock.patch("takeoff.step.KeyVaultClient.vault_and_client", return_value=(None, None))
def test_run_task(_):
    from takeoff.deploy import run_task
    res = run_task(env, 'mocked', {'task': 'mocked', 'some_param': 'foo', **conf_ext})

    assert res == 'yeah, science!'


@mock.patch.dict(os.environ, environment_variables)
@mock.patch("takeoff.deploy.get_full_yaml_filename", side_effect=filename)
@mock.patch("takeoff.deploy.load_yaml")
@mock.patch.object(DeployToDatabricks, 'run', return_value=None)
def test_read_takeoff_plugins(_, mock_load_yaml, __):
    paths = [os.path.dirname(os.path.realpath(__file__))]

    def load(s):
        if s == '.takeoff/deployment.yml':
            return {"steps": []}
        elif s == '.takeoff/config.yml':
            return {**takeoff_config(),
                    "plugins": paths}

    mock_load_yaml.side_effect = load

    with mock.patch("takeoff.deploy.get_environment") as mock_env:
        with mock.patch("takeoff.deploy.add_takeoff_plugin_paths") as m:
            main()
    m.assert_called_once_with(paths)


@mock.patch.dict(os.environ, environment_variables)
def test_add_custom_path():
    paths = [os.path.dirname(os.path.realpath(__file__))]
    add_takeoff_plugin_paths(paths)

    env = find_env_function("_takeoff_")

    assert env(conf_ext).branch == "master"
    sys.path.remove(paths[0])
