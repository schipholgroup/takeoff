import os
import unittest

import pytest
import voluptuous
from mock import mock

from runway.ApplicationVersion import ApplicationVersion
from runway.deploy_to_databricks import JobConfig, SCHEMA, DeployToDatabricks as victim

jobs = [
    JobConfig("foo-SNAPSHOT", 1),
    JobConfig("bar-0.3.1", 2),
    JobConfig("foobar-0.0.2", 3),
    JobConfig("barfoo-0.0.2", 4),
    JobConfig("daniel-branch-name", 5),
    JobConfig("tim-postfix-SNAPSHOT", 6),
    JobConfig("tim-postfix-SNAPSHOT", 7),
]

streaming_job_config = "tests/test_job_config.json.j2"
batch_job_config = "tests/test_job_config_scheduled.json.j2"


class TestDeployToDatabricks(unittest.TestCase):
    def test_find_application_job_id_if_snapshot(self):
        assert victim._application_job_id("foo", "master", jobs) == [1]

    def test_find_application_job_id_if_version(self):
        assert victim._application_job_id("bar", "0.3.1", jobs) == [2]

    def test_find_application_job_id_if_version_not_set(self):
        assert victim._application_job_id("bar", "", jobs) == [2]

    def test_find_application_job_id_if_branch(self):
        assert victim._application_job_id("daniel", "branch-name", jobs) == [5]

    def test_find_application_job_id_if_branch_if_no_version(self):
        assert victim._application_job_id("daniel", "", jobs) == []

    def test_find_application_job_id_if_postfix(self):
        assert victim._application_job_id("tim-postfix", "SNAPSHOT", jobs) == [6, 7]

    @mock.patch("runway.DeploymentStep.AzureKeyvaultClient.vault_and_client", return_value=(None, None))
    @mock.patch.dict(os.environ, {"BUILD_DEFINITIONNAME": "app-name"})
    def test_construct_name(self, _):
        assert victim(ApplicationVersion("env", "1b8e36f1", "some-branch"), {})._construct_name("") == "app-name"
        assert victim(ApplicationVersion("env", "1b8e36f1", "some-branch"), {})._construct_name("foo") == "app-name-foo"

    def test_is_streaming_job(self):
        job_config = victim._construct_job_config(config_file=streaming_job_config)
        assert victim._job_is_streaming(job_config) is True

        job_config = victim._construct_job_config(config_file=batch_job_config)
        assert victim._job_is_streaming(job_config) is False

    def test_construct_job_config(self):
        job_config = victim._construct_job_config(
            config_file=streaming_job_config,
            application_name="app-42",
            log_destination="app",
            egg_file="some.egg",
            python_file="some.py",
            parameters=["--foo", "bar"],
        )

        assert {
            "name": "app-42",
            "libraries": [{"egg": "some.egg"}, {"jar": "some.jar"}],
            "new_cluster": {
                "spark_version": "4.1.x-scala2.11",
                "spark_conf": {"spark.sql.warehouse.dir": "/some_", "some.setting": "true"},
                "cluster_log_conf": {"dbfs": {"destination": "dbfs:/mnt/sdh/logs/app"}},
            },
            "some_int": 5,
            "spark_python_task": {"python_file": "some.py", "parameters": ["--foo", "bar"]},
        } == job_config

    @mock.patch("runway.DeploymentStep.AzureKeyvaultClient.vault_and_client", return_value=(None, None))
    def test_invalid_config_empty_schema(self, _):
        config = {"runway_common": {"databricks_library_path": "/path"}}
        with pytest.raises(voluptuous.error.MultipleInvalid):
            victim(ApplicationVersion("foo", "bar", "baz"), config).validate()

    @mock.patch("runway.DeploymentStep.AzureKeyvaultClient.vault_and_client", return_value=(None, None))
    def test_invalid_config_empty_jobs(self, _):
        config = {"runway_common": {"databricks_library_path": "/path"}, "jobs": []}
        with pytest.raises(voluptuous.error.MultipleInvalid):
            victim(ApplicationVersion("foo", "bar", "baz"), config).validate()

    @mock.patch("runway.DeploymentStep.AzureKeyvaultClient.vault_and_client", return_value=(None, None))
    def test_valid_config(self, _):
        config = {
            "runway_common": {"databricks_library_path": "/path"},
            "task": "databricks",
            "jobs": [{"main_name": "pyfile"}],
        }
        run_config = victim(ApplicationVersion("foo", "bar", "baz"), config).validate()
        assert run_config["jobs"][0]["lang"] == "python"

    def test_create_arguments(self):
        assert victim._construct_arguments([{"foo": "bar"}]) == ["--foo", "bar"]
        assert victim._construct_arguments([{"foo": "bar"}, {"baz": "foobar"}]) == ["--foo", "bar", "--baz", "foobar"]

    def test_schema_validity(self):
        res = SCHEMA({"jobs": [{"main_name": "foo", "name": "some-name"}]})["jobs"][0]
        assert res["arguments"] == [{}]
        assert res["lang"] == "python"

        res = SCHEMA({"jobs": [{"main_name": "foo", "name": "some-name", "arguments": [{"key": "val"}]}]})["jobs"][0]
        assert res["arguments"] == [{"key": "val"}]

        res = SCHEMA(
            {"jobs": [{"main_name": "foo", "name": "some-name", "arguments": [{"key": "val"}, {"key2": "val2"}]}]}
        )["jobs"][0]
        assert res["arguments"] == [{"key": "val"}, {"key2": "val2"}]

    @mock.patch("runway.DeploymentStep.AzureKeyvaultClient.vault_and_client", return_value=(None, None))
    def test_yaml_to_databricks_json(self, _):
        config = {"runway_common": {"databricks_library_path": "/path"}}
        conf = {
            "main_name": "foo.class",
            "config_file": "tests/test_databricks.json.j2",
            "lang": "scala",
            "arguments": [{"key": "val"}, {"key2": "val2"}],
        }

        res = victim(ApplicationVersion("foo", "bar", "baz"), config)._create_config("job_name", conf, "app_name")

        assert res == {
            "name": "job_name",
            "new_cluster": {
                "spark_version": "4.1.x-scala2.11",
                "spark_conf": {"spark.sql.warehouse.dir": "/some_", "some.setting": "true"},
                "cluster_log_conf": {"dbfs": {"destination": "dbfs:/mnt/sdh/logs/job_name"}},
            },
            "some_int": 5,
            "libraries": [{"jar": "/path/app_name/app_name-bar.jar"}],
            "spark_jar_task": {"main_class_name": "foo.class", "parameters": ["--key", "val", "--key2", "val2"]},
        }
