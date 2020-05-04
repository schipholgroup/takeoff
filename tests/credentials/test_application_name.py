import os
from unittest import mock


from takeoff.credentials.application_name import ApplicationName as victim
from tests.credentials.base_environment_keys_test import EnvironmentKeyBaseTest, CONFIG, OS_KEYS


class TestApplicationName(EnvironmentKeyBaseTest):
    def call_victim(self, config):
        return victim(config=config, app_version=None).get()

    @mock.patch.dict(os.environ, OS_KEYS)
    def test_credentials(self):
        assert self.call_victim(CONFIG) == "test-project"
