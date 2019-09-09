import os

import mock

from takeoff.azure.credentials.service_principal import ServicePrincipalCredentials as victim
from tests.credentials.base_environment_keys_test import EnvironmentKeyBaseTest, OS_KEYS


class TestServicePrincipal(EnvironmentKeyBaseTest):
    def call_victim(self, config):
        victim().credentials(config, "env")

    @mock.patch.dict(os.environ, OS_KEYS)
    def test_credentials(self):
        self.execute(
            "takeoff.azure.credentials.service_principal.SpCredentials",
            {"client_id": "d0aaa0de-c1ef-456f-a025-c5d6341193bb", "secret": "3ceb401f-6462-48da-b42f-b1d1745c2590"}
        )
