import unittest

import mock

from runway.application_version import ApplicationVersion
from runway.azure.create_application_insights import CreateApplicationInsights as victim
from tests.azure import runway_config


class TestCreateApplicationInsights(unittest.TestCase):
    @mock.patch("runway.step.KeyVaultClient.vault_and_client", return_value=(None, None))
    def test_validate_minimal_schema(self, _):
        conf = {**runway_config(), **{'task': 'createApplicationInsights'}}

        victim(ApplicationVersion("dev", "v", "branch"), conf)
