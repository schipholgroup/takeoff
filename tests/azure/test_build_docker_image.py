import unittest

import mock

from takeoff.application_version import ApplicationVersion
from takeoff.azure.build_docker_image import DockerImageBuilder as victim
from tests.azure import takeoff_config


class TestDockerImageBuilder(unittest.TestCase):
    @mock.patch("takeoff.step.KeyVaultClient.vault_and_client", return_value=(None, None))
    def test_validate_minimal_schema(self, _):
        conf = {**takeoff_config(), **{'task': 'buildDockerImage'}}

        res = victim(ApplicationVersion("dev", "v", "branch"), conf)
        assert res.config['dockerfiles'] == [{"file": "Dockerfile", "postfix": None, "custom_image_name": None}]

    @mock.patch("takeoff.step.KeyVaultClient.vault_and_client", return_value=(None, None))
    def test_validate_full_schema(self, _):
        conf = {**takeoff_config(),
                **{'task': 'buildDockerImage',
                   "dockerfiles": [{
                       "file": "Dockerfile_custom",
                       "postfix": "Dave",
                       "custom_image_name": "Mustaine"
                   }]}}

        victim(ApplicationVersion("dev", "v", "branch"), conf)
