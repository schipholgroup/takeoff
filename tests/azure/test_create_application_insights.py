import unittest

import mock

from runway.ApplicationVersion import ApplicationVersion
from runway.azure.create_application_insights import CreateApplicationInsights as victim
from tests.azure import runway_config


class TestCreateApplicationInsights(unittest.TestCase):
    @mock.patch("runway.DeploymentStep.KeyVaultClient.vault_and_client", return_value=(None, None))
    def test_validate_minimal_schema(self, _):
        conf = {**runway_config(), **{'task': 'createApplicationInsights'}}

        victim(ApplicationVersion("dev", "v", "branch"), conf)
