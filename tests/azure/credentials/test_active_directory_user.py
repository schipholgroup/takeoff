from runway.azure.credentials.active_directory_user import ActiveDirectoryUserCredentials as victim
from tests.azure.credentials import KeyVaultBaseTest


class TestActiveDirectoryUserCredentials(KeyVaultBaseTest):
    def call_victim(self, m_client, config):
        victim("vault", m_client).credentials(config)

    def test_credentials(self):
        self.execute(
            "runway.azure.credentials.active_directory_user.UserPassCredentials",
            {'username': "azuser", 'password': "azpass"}
        )
