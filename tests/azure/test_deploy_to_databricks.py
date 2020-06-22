import os
from dataclasses import dataclass
from unittest import mock

import pytest
import voluptuous as vol

from takeoff.application_version import ApplicationVersion
from takeoff.azure.deploy_to_databricks import JobConfig, SCHEMA, DeployToDatabricks
from tests.azure import takeoff_config

jobs = [
    JobConfig("foo-SNAPSHOT", 1),
    JobConfig("bar-0.3.1", 2),
    JobConfig("foobar-0.0.2", 3),
    JobConfig("barfoo-0.0.2", 4),
    JobConfig("daniel-branch-name", 5),
    JobConfig("tim-postfix-SNAPSHOT", 6),
    JobConfig("tim-postfix-SNAPSHOT", 7),
    JobConfig("michel-1.2.3--my-version-postfix", 8),
]

streaming_job_config = "tests/azure/files/test_job_config.json.j2"
batch_job_config = "tests/azure/files/test_job_config_scheduled.json.j2"
dynamic_schedule_job_config = "tests/azure/files/test_job_config_schedule_dynamically.json.j2"

BASE_CONF = {"task": "deploy_to_databricks", "jobs": [{"main_name": "Dave"}]}
TEST_ENV_VARS = {
    "AZURE_TENANTID": "David",
    "AZURE_KEYVAULT_SP_USERNAME_DEV": "Doctor",
    "AZURE_KEYVAULT_SP_PASSWORD_DEV": "Who",
    "CI_PROJECT_NAME": "my_little_pony",
    "CI_COMMIT_REF_SLUG": "my-little-pony",
}


@dataclass
class MockDatabricksClient:
    def api_client(self, config):
        return None


@pytest.fixture(autouse=True)
@mock.patch.dict(os.environ, TEST_ENV_VARS)
def victim():
    m_jobs_api_client = mock.MagicMock()
    m_runs_api_client = mock.MagicMock()

    m_jobs_api_client.list_jobs.return_value = {
        "jobs": [
            {"job_id": "id1", "settings": {"name": "job1"}},
            {"job_id": "id2", "settings": {"name": "job2"}},
        ]
    }
    m_jobs_api_client.delete_job.return_value = True
    m_jobs_api_client.create_job.return_value = {"job_id": "job1"}
    m_jobs_api_client.run_now.return_value = {"run_id": "run1"}

    m_runs_api_client.list_runs.return_value = {
        "runs": [{"run_id": "run1"}, {"run_id": "run2"}]
    }

    with mock.patch("takeoff.azure.deploy_to_databricks.KeyVaultClient.vault_and_client", return_value=(None, None)), \
         mock.patch("takeoff.step.ApplicationName.get", return_value="my_app"), \
         mock.patch("takeoff.azure.deploy_to_databricks.Databricks", return_value=MockDatabricksClient()), \
         mock.patch("takeoff.azure.deploy_to_databricks.JobsApi", return_value=m_jobs_api_client), \
         mock.patch("takeoff.azure.deploy_to_databricks.RunsApi", return_value=m_runs_api_client):
        conf = {**takeoff_config(), **BASE_CONF}
        return DeployToDatabricks(ApplicationVersion('ACP', 'bar', 'foo'), conf)


class TestDeployToDatabricks(object):
    @mock.patch(
        "takeoff.step.KeyVaultClient.vault_and_client", return_value=(None, None)
    )
    def test_validate_schema(self, _, victim):
        assert victim.config["jobs"][0]["config_file"] == "databricks.json.j2"
        assert victim.config["jobs"][0]["name"] == ""
        assert victim.config["jobs"][0]["lang"] == "python"
        assert victim.config["jobs"][0]["arguments"] == [{}]

    def test_find_application_job_id_if_snapshot(self, victim):
        assert victim._application_job_id("foo", "master", jobs) == [1]

    def test_find_application_job_id_if_version(self, victim):
        assert victim._application_job_id("bar", "0.3.1", jobs) == [2]

    def test_find_application_job_id_if_version_not_set(self, victim):
        assert victim._application_job_id("bar", "", jobs) == [2]

    def test_find_application_job_id_if_branch(self, victim):
        assert victim._application_job_id("daniel", "branch-name", jobs) == [5]

    def test_find_application_job_id_if_branch_if_no_version(self, victim):
        assert victim._application_job_id("daniel", "", jobs) == []

    def test_find_application_job_id_if_postfix(self, victim):
        assert victim._application_job_id("tim-postfix", "SNAPSHOT", jobs) == [6, 7]

    def test_find_application_job_id_if_version_postfix(self, victim):
        assert victim._application_job_id("michel", "1.2.3--my-version-postfix", jobs) == [8]

    def test_construct_name(self, victim):
        assert victim._construct_name("") == "my_app"
        assert victim._construct_name("foo") == "my_app-foo"

    def test_job_is_unscheduled(self, victim):
        job_config = victim._construct_job_config(config_file=streaming_job_config)
        assert victim._job_is_unscheduled(job_config) is True

        job_config = victim._construct_job_config(config_file=batch_job_config)
        assert victim._job_is_unscheduled(job_config) is False

    def test_construct_job_config(self, victim):
        job_config = victim._construct_job_config(
            config_file=streaming_job_config,
            application_name="app-42",
            log_destination="app",
            whl_file="some.whl",
            python_file="some.py",
            parameters=["--foo", "bar"],
        )

        assert {
                   "name": "app-42",
                   "libraries": [{"whl": "some.whl"}, {"jar": "some.jar"}],
                   "new_cluster": {
                       "spark_version": "4.1.x-scala2.11",
                       "spark_conf": {
                           "spark.sql.warehouse.dir": "/some_",
                           "some.setting": "true",
                       },
                       "cluster_log_conf": {"dbfs": {"destination": "dbfs:/mnt/sdh/logs/app"}},
                   },
                   "some_int": 5,
                   "spark_python_task": {
                       "python_file": "some.py",
                       "parameters": ["--foo", "bar"],
                   },
               } == job_config

    @mock.patch(
        "takeoff.step.KeyVaultClient.vault_and_client", return_value=(None, None)
    )
    def test_invalid_config_empty_jobs(self, _):
        config = {**takeoff_config(), **BASE_CONF, "jobs": []}
        with pytest.raises(vol.MultipleInvalid):
            DeployToDatabricks(ApplicationVersion("DEV", "local", "foo"), config)

    def test_create_arguments(self, victim):
        assert victim._construct_arguments([{"foo": "bar"}]) == ["--foo", "bar"]
        assert victim._construct_arguments([{"foo": "bar"}, {"baz": "foobar"}]) == [
            "--foo",
            "bar",
            "--baz",
            "foobar",
        ]

    def test_schema_validity(self, victim):
        conf = {
            **takeoff_config(),
            **{
                "task": "deploy_to_databricks",
                "jobs": [{"main_name": "foo", "name": "some-name"}],
            },
        }
        res = SCHEMA(conf)["jobs"][0]
        assert res["arguments"] == [{}]
        assert res["lang"] == "python"

        conf = {
            **takeoff_config(),
            **{
                "task": "deploy_to_databricks",
                "jobs": [
                    {
                        "main_name": "foo",
                        "name": "some-name",
                        "arguments": [{"key": "val"}],
                    }
                ],
            },
        }
        res = SCHEMA(conf)["jobs"][0]
        assert res["arguments"] == [{"key": "val"}]

        conf = {
            **takeoff_config(),
            **{
                "task": "deploy_to_databricks",
                "jobs": [
                    {
                        "main_name": "foo",
                        "name": "some-name",
                        "arguments": [{"key": "val"}, {"key2": "val2"}],
                    }
                ],
            },
        }
        res = SCHEMA(conf)["jobs"][0]
        assert res["arguments"] == [{"key": "val"}, {"key2": "val2"}]

        conf = {
            **takeoff_config(),
            **{
                "task": "deploy_to_databricks",
                "jobs": [{"main_name": "foo", "name": "some-name", 'is_batch': True}],
            },
        }
        res = SCHEMA(conf)["jobs"][0]
        assert res["is_batch"] is True

        conf = {
            **takeoff_config(),
            **{
                "task": "deploy_to_databricks",
                "jobs": [{"main_name": "foo", "name": "some-name"}],
            },
        }
        res = SCHEMA(conf)["jobs"][0]
        assert res["is_batch"] is False

    def test_yaml_to_databricks_json(self, victim):
        conf = {
            "main_name": "foo.class",
            "config_file": "tests/azure/files/test_databricks.json.j2",
            "lang": "scala",
            "arguments": [{"key": "val"}, {"key2": "val2"}],
        }

        res = victim.create_config("job_name", conf)

        assert res == {
            "name": "job_name",
            "new_cluster": {
                "spark_version": "4.1.x-scala2.11",
                "spark_conf": {
                    "spark.sql.warehouse.dir": "/some_",
                    "some.setting": "true",
                },
                "cluster_log_conf": {
                    "dbfs": {"destination": "dbfs:/mnt/sdh/logs/job_name"}
                },
            },
            "some_int": 5,
            "libraries": [{"jar": "dbfs:/mnt/libraries/my_app/my_app-bar.jar"}],
            "spark_jar_task": {"main_class_name": "foo.class", "parameters": ["--key", "val", "--key2", "val2"]},
        }

    def test_correct_schedule_as_parameter_in_databricks_json(self, victim):
        job_config = victim._construct_job_config(
            config_file=dynamic_schedule_job_config,
            application_name="job_with_schedule",
            log_destination="app",
            whl_file="some.whl",
            python_file="some.py",
            parameters=["--foo", "bar"],
            schedule={
                "quartz_cron_expression": "0 15 22 ? * *",
                "timezone_id": "America/Los_Angeles",
            },
        )

        assert job_config == {
            "new_cluster": {
                "spark_version": "4.1.x-scala2.11",
                "spark_conf": {
                    "spark.sql.warehouse.dir": "/some_",
                    "some.setting": "true",
                },
                "cluster_log_conf": {"dbfs": {"destination": "dbfs:/mnt/sdh/logs/app"}},
            },
            "name": "job_with_schedule",
            "libraries": [{"whl": "some.whl"}, {"jar": "some.jar"}],
            "schedule": {
                "quartz_cron_expression": "0 15 22 ? * *",
                "timezone_id": "America/Los_Angeles",
            },
            "spark_python_task": {
                "python_file": "some.py",
                "parameters": ["--foo", "bar"],
            },
        }

    def test_none_schedule_as_parameter_in_databricks_json(self, victim):
        job_config = victim._construct_job_config(
            config_file=dynamic_schedule_job_config,
            application_name="job_with_schedule",
            log_destination="app",
            whl_file="some.whl",
            python_file="some.py",
            parameters=["--foo", "bar"],
            schedule=None,
        )

        assert job_config == {
            "new_cluster": {
                "spark_version": "4.1.x-scala2.11",
                "spark_conf": {
                    "spark.sql.warehouse.dir": "/some_",
                    "some.setting": "true",
                },
                "cluster_log_conf": {"dbfs": {"destination": "dbfs:/mnt/sdh/logs/app"}},
            },
            "name": "job_with_schedule",
            "libraries": [{"whl": "some.whl"}, {"jar": "some.jar"}],
            "spark_python_task": {
                "python_file": "some.py",
                "parameters": ["--foo", "bar"],
            },
        }

    def test_missing_schedule_as_parameter_in_databricks_json(self, victim):
        job_config = victim._construct_job_config(
            config_file=dynamic_schedule_job_config,
            application_name="job_with_schedule",
            log_destination="app",
            whl_file="some.whl",
            python_file="some.py",
            parameters=["--foo", "bar"],
        )

        assert job_config == {
            "new_cluster": {
                "spark_version": "4.1.x-scala2.11",
                "spark_conf": {
                    "spark.sql.warehouse.dir": "/some_",
                    "some.setting": "true",
                },
                "cluster_log_conf": {"dbfs": {"destination": "dbfs:/mnt/sdh/logs/app"}},
            },
            "name": "job_with_schedule",
            "libraries": [{"whl": "some.whl"}, {"jar": "some.jar"}],
            "spark_python_task": {
                "python_file": "some.py",
                "parameters": ["--foo", "bar"],
            },
        }

    def test_correct_schedule_as_parameter_in_job_config_without_env(self, victim):
        conf = {
            "main_name": "some.py",
            "config_file": dynamic_schedule_job_config,
            "lang": "python",
            "arguments": [{"key": "val"}, {"key2": "val2"}],
            "schedule": {
                "quartz_cron_expression": "0 15 22 ? * *",
                "timezone_id": "America/Los_Angeles",
            },
        }

        res = victim.create_config("job_with_schedule", conf)

        assert res == {
            "new_cluster": {
                "spark_version": "4.1.x-scala2.11",
                "spark_conf": {
                    "spark.sql.warehouse.dir": "/some_",
                    "some.setting": "true",
                },
                "cluster_log_conf": {
                    "dbfs": {"destination": "dbfs:/mnt/sdh/logs/job_with_schedule"}
                },
            },
            "name": "job_with_schedule",
            "libraries": [
                {"whl": "dbfs:/mnt/libraries/my_app/my_app-bar-py3-none-any.whl"},
                {"jar": "some.jar"}
            ],
            "schedule": {
                "quartz_cron_expression": "0 15 22 ? * *",
                "timezone_id": "America/Los_Angeles",
            },
            "spark_python_task": {
                "python_file": "dbfs:/mnt/libraries/my_app/my_app-main-bar.py",
                "parameters": ["--key", "val", "--key2", "val2"]
            }
        }

    def test_correct_schedule_as_parameter_in_job_config_with_env_schedule(
            self, victim
    ):
        conf = {
            "main_name": "some.py",
            "config_file": dynamic_schedule_job_config,
            "lang": "python",
            "arguments": [{"key": "val"}, {"key2": "val2"}],
            "schedule": {
                "acp": {
                    "quartz_cron_expression": "0 15 22 ? * *",
                    "timezone_id": "America/Los_Angeles",
                }
            },
        }

        res = victim.create_config("job_with_schedule", conf)

        assert res == {
            "new_cluster": {
                "spark_version": "4.1.x-scala2.11",
                "spark_conf": {
                    "spark.sql.warehouse.dir": "/some_",
                    "some.setting": "true",
                },
                "cluster_log_conf": {
                    "dbfs": {"destination": "dbfs:/mnt/sdh/logs/job_with_schedule"}
                },
            },
            "name": "job_with_schedule",
            "libraries": [
                {"whl": "dbfs:/mnt/libraries/my_app/my_app-bar-py3-none-any.whl"},
                {"jar": "some.jar"}
            ],
            "schedule": {
                "quartz_cron_expression": "0 15 22 ? * *",
                "timezone_id": "America/Los_Angeles",
            },
            "spark_python_task": {
                "python_file": "dbfs:/mnt/libraries/my_app/my_app-main-bar.py",
                "parameters": ["--key", "val", "--key2", "val2"]
            }
        }

    def test_correct_schedule_as_parameter_in_job_config_with_env_schedule_for_other_env(
            self, victim
    ):
        conf = {
            "main_name": "some.py",
            "config_file": dynamic_schedule_job_config,
            "lang": "python",
            "arguments": [{"key": "val"}, {"key2": "val2"}],
            "schedule": {
                "dev": {
                    "quartz_cron_expression": "0 15 22 ? * *",
                    "timezone_id": "America/Los_Angeles",
                }
            },
        }

        res = victim.create_config("job_with_schedule", conf)

        assert res == {
            "new_cluster": {
                "spark_version": "4.1.x-scala2.11",
                "spark_conf": {
                    "spark.sql.warehouse.dir": "/some_",
                    "some.setting": "true",
                },
                "cluster_log_conf": {
                    "dbfs": {"destination": "dbfs:/mnt/sdh/logs/job_with_schedule"}
                },
            },
            "name": "job_with_schedule",
            "libraries": [
                {"whl": "dbfs:/mnt/libraries/my_app/my_app-bar-py3-none-any.whl"},
                {"jar": "some.jar"}
            ],
            "spark_python_task": {
                "python_file": "dbfs:/mnt/libraries/my_app/my_app-main-bar.py",
                "parameters": ["--key", "val", "--key2", "val2"]
            }
        }

    def test_no_schedule_as_parameter_in_job_config_without_env_schedule(self, victim):
        conf = {
            "main_name": "some.py",
            "config_file": dynamic_schedule_job_config,
            "lang": "python",
            "arguments": [{"key": "val"}, {"key2": "val2"}],
        }

        res = victim.create_config("job_with_schedule", conf)

        assert res == {
            "new_cluster": {
                "spark_version": "4.1.x-scala2.11",
                "spark_conf": {
                    "spark.sql.warehouse.dir": "/some_",
                    "some.setting": "true",
                },
                "cluster_log_conf": {
                    "dbfs": {"destination": "dbfs:/mnt/sdh/logs/job_with_schedule"}
                },
            },
            "name": "job_with_schedule",
            "libraries": [
                {"whl": "dbfs:/mnt/libraries/my_app/my_app-bar-py3-none-any.whl"},
                {"jar": "some.jar"}
            ],
            "spark_python_task": {
                "python_file": "dbfs:/mnt/libraries/my_app/my_app-main-bar.py",
                "parameters": ["--key", "val", "--key2", "val2"]
            }
        }

    def test_correct_schedule_from_template_in_job_config(self, victim):
        conf = {
            "main_name": "some.py",
            "config_file": batch_job_config,
            "lang": "python",
            "arguments": [{"key": "val"}, {"key2": "val2"}],
        }

        res = victim.create_config("job_with_schedule", conf)

        assert res == {
            "new_cluster": {
                "spark_version": "4.1.x-scala2.11",
                "spark_conf": {
                    "spark.sql.warehouse.dir": "/some_",
                    "some.setting": "true",
                },
                "cluster_log_conf": {
                    "dbfs": {"destination": "dbfs:/mnt/sdh/logs/job_with_schedule"}
                },
            },
            "some_int": 5,
            "name": "job_with_schedule",
            "libraries": [
                {"whl": "dbfs:/mnt/libraries/my_app/my_app-bar-py3-none-any.whl"},
                {"jar": "some.jar"}
            ],
            "schedule": {
                "quartz_cron_expression": "0 15 22 ? * *",
                "timezone_id": "America/Los_Angeles",
            },
            "spark_python_task": {
                "python_file": "dbfs:/mnt/libraries/my_app/my_app-main-bar.py",
                "parameters": ["--key", "val", "--key2", "val2"]
            }
        }

    @mock.patch.dict(os.environ, TEST_ENV_VARS)
    @mock.patch(
        "takeoff.step.KeyVaultClient.vault_and_client", return_value=(None, None)
    )
    def test_deploy_to_databricks(self, _, victim):
        job_config = {
            "new_cluster": {
                "spark_version": "4.1.x-scala2.11",
                "spark_conf": {
                    "spark.sql.warehouse.dir": "/some_",
                    "some.setting": "true",
                },
                "cluster_log_conf": {
                    "dbfs": {"destination": "dbfs:/mnt/sdh/logs/job_with_schedule"}
                },
            },
            "name": "job_with_schedule",
            "libraries": [
                {"whl": "dbfs:/mnt/libraries/version/version-bar-py3-none-any.whl"},
                {"jar": "some.jar"}
            ],
            "spark_python_task": {
                "python_file": "dbfs:/mnt/libraries/version/version-main-bar.py",
                "parameters": ["--key", "val", "--key2", "val2"]
            }
        }
        with mock.patch(
                "takeoff.azure.deploy_to_databricks.DeployToDatabricks.create_config",
                return_value=job_config,
        ) as config_mock:
            with mock.patch(
                    "takeoff.azure.deploy_to_databricks.DeployToDatabricks.remove_job"
            ) as remove_mock:
                with mock.patch(
                        "takeoff.azure.deploy_to_databricks.DeployToDatabricks._submit_job"
                ) as submit_mock:
                    victim.deploy_to_databricks()

        # TODO: make called_with
        remove_mock.assert_called_once()
        submit_mock.assert_called_once()

    @mock.patch.dict(os.environ, TEST_ENV_VARS)
    @mock.patch(
        "takeoff.step.KeyVaultClient.vault_and_client", return_value=(None, None)
    )
    def test_remove_job_batch(self, _, victim):
        with mock.patch(
                "takeoff.azure.deploy_to_databricks.DeployToDatabricks._application_job_id",
                return_value=["id1", "id2"],
        ):
            victim.remove_job("my-branch", {'name': ""}, False)

        calls = [mock.call("id1"), mock.call("id2")]

        victim.jobs_api.delete_job.assert_has_calls(calls)

    def test_remove_job_batch_with_name(self):
        res = DeployToDatabricks._application_job_id("tim-postfix", "master", jobs)

        assert len(res) == 2

    def test_remove_job_streaming(self, victim):
        with mock.patch(
                "takeoff.azure.deploy_to_databricks.DeployToDatabricks._application_job_id",
                return_value=["id1", "id2"],
        ):
            with mock.patch(
                    "takeoff.azure.deploy_to_databricks.DeployToDatabricks._kill_it_with_fire"
            ) as kill_mock:
                victim.remove_job("my-branch", {'name': ""}, True)

        calls = [mock.call("id1"), mock.call("id2")]

        victim.jobs_api.delete_job.assert_has_calls(calls)
        kill_mock.assert_has_calls(calls)

    def test_remove_non_existing_job(self, victim):
        with mock.patch(
                "takeoff.azure.deploy_to_databricks.DeployToDatabricks._application_job_id",
                return_value=[],
        ):
            victim.remove_job("my-branch", {'name': ""}, False)

        victim.jobs_api.delete_job.assert_not_called()

    def test_kill_it_with_fire(self, victim):
        victim._kill_it_with_fire("my-id")

        calls = [mock.call("run1"), mock.call("run2")]
        victim.runs_api.cancel_run.assert_has_calls(calls)

    def test_deploy_job_batch(self, victim):
        victim.deploy_job({}, False, True)

        victim.jobs_api.create_job.assert_called_with({})

        victim.jobs_api.run_now.assert_not_called()

    def test_submit_job_streaming(self, victim):
        victim.deploy_job({}, True, True)

        victim.jobs_api.create_job.assert_called_with({})

        victim.jobs_api.run_now.assert_called_with(
            jar_params=None,
            job_id="job1",
            notebook_params=None,
            python_params=None,
            spark_submit_params=None,
        )

    def test_submit_job_streaming_without_immediate_run(self, victim):
        victim.deploy_job({}, True, False)

        victim.jobs_api.create_job.assert_called_with({})

        victim.jobs_api.run_now.assert_not_called()
