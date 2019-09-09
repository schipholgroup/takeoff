import yaml

from runway.ApplicationVersion import ApplicationVersion
from runway.credentials.DeploymentYamlEnvironmentVariablesMixin import DeploymentYamlEnvironmentVariablesMixin as victim
from runway.credentials.Secret import Secret


class TestDeploymentYamlEnvironmentVariablesMixin(object):
    def test_get_secrets_from_config(self):
        env = ApplicationVersion("DEV", "foo", "bar")
        config = {
            "task": "createDatabricksSecrets",
            "dev": [{"FOO": "foo_value"}, {"BAR": "bar_value"}],
            "acc": [{"FOO": "fooacc_value"}, {"BAR": "baracc_value"}],
        }
        res = victim(env, config).get_deployment_secrets()
        assert res == [Secret("FOO", "foo_value"), Secret("BAR", "bar_value")]

    def test_get_secrets_from_empty_config(self):
        env = ApplicationVersion("DEV", "foo", "bar")
        config = {"task": "createDatabricksSecrets"}
        res = victim(env, config).get_deployment_secrets()
        assert res == []

    def test_get_secrets_from_config_without_env(self):
        env = ApplicationVersion("PRD", "foo", "bar")
        config = {
            "task": "createDatabricksSecrets",
            "dev": [{"FOO": "foo_value"}, {"BAR": "bar_value"}],
            "acc": [{"FOO": "fooacc_value"}, {"BAR": "baracc_value"}],
        }
        res = victim(env, config).get_deployment_secrets()
        assert res == []

    def test_get_secrets_from_config_with_empty_env(self):
        env = ApplicationVersion("DEV", "foo", "bar")
        config = {
            "task": "createDatabricksSecrets",
            "dev": [],
            "acc": [{"FOO": "fooacc_value"}, {"BAR": "baracc_value"}],
        }
        res = victim(env, config).get_deployment_secrets()
        assert res == []

    def test_create_secrets_from_yaml_file(self):
        with open("tests/test_deployment.yml", "r") as f:
            runway_config = yaml.safe_load(f.read())
            for task_config in runway_config["steps"]:
                if task_config["task"] == "createDatabricksSecrets":
                    res = victim(
                        ApplicationVersion("ACP", "foo", "bar"), task_config
                    ).get_deployment_secrets()
                    assert res == [Secret("FOO", "acp_bar"), Secret("BAR", "acp_foo")]
