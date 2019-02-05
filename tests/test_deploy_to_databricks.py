import unittest

import pytest
import voluptuous
from mock import mock

from runway.ApplicationVersion import ApplicationVersion
from runway.deploy_to_databricks import JobConfig, DeployToDatabricks as victim

jobs = [
    JobConfig("foo-SNAPSHOT", 1),
    JobConfig("bar-0.3.1", 2),
    JobConfig("foobar-0.0.2", 3),
    JobConfig("barfoo-0.0.2", 4),
    JobConfig("daniel-branch-name", 5),
]

streaming_job_config = "tests/test_job_config.json.j2"
batch_job_config = "tests/test_job_config_scheduled.json.j2"


class TestDeployToDatabricks(unittest.TestCase):
    def test_find_application_job_id_if_snapshot(self):
        assert victim._application_job_id("foo", 'master', jobs) == 1

    def test_find_application_job_id_if_version(self):
        assert victim._application_job_id("bar", '0.3.1', jobs) == 2

    def test_find_application_job_id_if_version_not_set(self):
        assert victim._application_job_id("bar", '', jobs) == 2

    def test_find_application_job_id_if_branch(self):
        assert victim._application_job_id("daniel", 'branch-name', jobs) == 5

    def test_find_application_job_id_if_branch_if_no_version(self):
        assert victim._application_job_id("daniel", "", jobs) is None

    def test_is_streaming_job(self):
        job_config = victim._construct_job_config(
            config_file_fn=streaming_job_config
        )
        assert victim._job_is_streaming(job_config) is True

        job_config = victim._construct_job_config(
            config_file_fn=batch_job_config
        )
        assert victim._job_is_streaming(job_config) is False

    def test_construct_job_config(self):
        job_config = victim._construct_job_config(
            config_file_fn=streaming_job_config,
            application_name="app-42",
            log_destination="app",
            egg_file="some.egg",
            python_file="some.py",
        )

        assert {
                   "name": "app-42",
                   "libraries": [
                       {"egg": "some.egg"},
                       {"jar": "some.jar"}
                   ],
                   "new_cluster": {
                       "spark_version": "4.1.x-scala2.11",
                       "spark_conf": {
                           "spark.sql.warehouse.dir": "/some_",
                           "some.setting": "true",
                       },
                       "cluster_log_conf": {"dbfs": {"destination": "dbfs:/mnt/sdh/logs/app"}},
                   },
                   "some_int": 5,
                   "spark_python_task": {"python_file": "some.py"}} == job_config

    @mock.patch("runway.DeploymentStep.AzureKeyvaultClient.vault_and_client", return_value=(None, None))
    def test_invalid_config_emtpy_schema(self, _):
        config = {'runway_common': {'databricks_library_path': '/path'}}
        with pytest.raises(voluptuous.error.MultipleInvalid):
            victim(ApplicationVersion('foo', 'bar', 'baz'),
                   config).validate()

    @mock.patch("runway.DeploymentStep.AzureKeyvaultClient.vault_and_client", return_value=(None, None))
    def test_invalid_config_emtpy_jobs(self, _):
        config = {'runway_common': {'databricks_library_path': '/path'},
                  'jobs': []
                  }
        with pytest.raises(voluptuous.error.MultipleInvalid):
            victim(ApplicationVersion('foo', 'bar', 'baz'),
                   config).validate()

    @mock.patch("runway.DeploymentStep.AzureKeyvaultClient.vault_and_client", return_value=(None, None))
    def test_valid_config(self, _):
        config = {'runway_common': {'databricks_library_path': '/path'},
                  'task': 'databricks',
                  'jobs': [
                      {'main_name': 'pyfile'}
                  ]
                  }
        run_config = victim(ApplicationVersion('foo', 'bar', 'baz'),
               config).validate()
        assert run_config['jobs'][0]['lang'] == 'python'
