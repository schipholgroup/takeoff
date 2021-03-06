import yaml

from takeoff.application_version import ApplicationVersion
from takeoff.credentials.DeploymentYamlEnvironmentVariablesMixin import DeploymentYamlEnvironmentVariablesMixin as victim
from takeoff.credentials.secret import Secret


class TestDeploymentYamlEnvironmentVariablesMixin(object):
    def test_get_secrets_from_config(self):
        env = ApplicationVersion("DEV", "foo", "bar")
        config = {
            "task": "create_databricks_secrets_from_vault",
            "dev": [{"FOO": "foo_value"}, {"BAR": "bar_value"}],
            "acc": [{"FOO": "fooacc_value"}, {"BAR": "baracc_value"}],
        }
        res = victim(env, config).get_deployment_secrets()
        assert res == [Secret("FOO", "foo_value"), Secret("BAR", "bar_value")]

    def test_get_secrets_from_empty_config(self):
        env = ApplicationVersion("DEV", "foo", "bar")
        config = {"task": "create_databricks_secrets_from_vault"}
        res = victim(env, config).get_deployment_secrets()
        assert res == []

    def test_get_secrets_from_config_without_env(self):
        env = ApplicationVersion("PRD", "foo", "bar")
        config = {
            "task": "create_databricks_secrets_from_vault",
            "dev": [{"FOO": "foo_value"}, {"BAR": "bar_value"}],
            "acc": [{"FOO": "fooacc_value"}, {"BAR": "baracc_value"}],
        }
        res = victim(env, config).get_deployment_secrets()
        assert res == []

    def test_get_secrets_from_config_with_empty_env(self):
        env = ApplicationVersion("DEV", "foo", "bar")
        config = {
            "task": "create_databricks_secrets_from_vault",
            "dev": [],
            "acc": [{"FOO": "fooacc_value"}, {"BAR": "baracc_value"}],
        }
        res = victim(env, config).get_deployment_secrets()
        assert res == []

    def test_create_secrets_from_yaml_file(self):
        with open("tests/test_deployment.yml", "r") as f:
            takeoff_config = yaml.safe_load(f.read())
            for task_config in takeoff_config["steps"]:
                if task_config["task"] == "create_databricks_secrets_from_vault":
                    res = victim(
                        ApplicationVersion("ACP", "foo", "bar"), task_config
                    ).get_deployment_secrets()
                    assert res == [Secret("FOO", "acp_bar"), Secret("BAR", "acp_foo")]
