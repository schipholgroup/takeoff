import os

import mock

from takeoff.credentials.branch_name import BranchName as victim
from tests.credentials.base_environment_keys_test import EnvironmentKeyBaseTest, CONFIG, OS_KEYS


class TestBranchName(EnvironmentKeyBaseTest):
    def call_victim(self, config):
        return victim(config=config).get()

    @mock.patch.dict(os.environ, OS_KEYS)
    def test_credentials(self):
        assert self.call_victim(CONFIG) == "master"
