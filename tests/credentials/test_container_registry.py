import os

import mock

from takeoff.credentials.container_registry import DockerRegistry as victim, DockerCredentials
from tests.credentials.base_environment_keys_test import EnvironmentKeyBaseTest, OS_KEYS, CONFIG


class TestDockerRegistry(EnvironmentKeyBaseTest):
    def call_victim(self, config):
        return victim(config, None).credentials()

    @mock.patch.dict(os.environ, OS_KEYS)
    def test_credentials(self):
        assert self.call_victim(CONFIG) == DockerCredentials("dockeruser", "dockerpass", "mylittlepony")
