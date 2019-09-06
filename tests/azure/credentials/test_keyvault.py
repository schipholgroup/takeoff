import mock

from runway.ApplicationVersion import ApplicationVersion
from runway.azure.credentials.keyvault import KeyvaultClient as victim
from tests.credentials.base_environment_keys_test import EnvironmentKeyBaseTest


class TestKeyvaultClient(EnvironmentKeyBaseTest):
    def call_victim(self, config):
        env = ApplicationVersion("DEV", "04fab6", "my-branch")
        with mock.patch("runway.azure.credentials.keyvault.ServicePrincipalCredentials.credentials",
                        return_value="mylittlepony") as m_creds:
            victim.vault_and_client(config, env)
        m_creds.assert_called_once_with(config, "dev")

    def test_credentials(self):
        self.execute(
            "runway.azure.credentials.keyvault.KeyVaultClient",
            {"credentials": "mylittlepony"}
        )
