import unittest

import mock

from takeoff.application_version import ApplicationVersion
from takeoff.azure.create_application_insights import CreateApplicationInsights as victim
from tests.azure import takeoff_config


class TestCreateApplicationInsights(unittest.TestCase):
    @mock.patch("takeoff.step.KeyVaultClient.vault_and_client", return_value=(None, None))
    def test_validate_minimal_schema(self, _):
        conf = {**takeoff_config(), **{'task': 'createApplicationInsights'}}

        victim(ApplicationVersion("dev", "v", "branch"), conf)
