from takeoff.azure.credentials.artifact_store import ArtifactStore as victim
from tests.azure.credentials.base_keyvault_test import KeyVaultBaseTest


class TestActiveDirectoryUserCredentials(KeyVaultBaseTest):
    def call_victim(self, m_client, config):
        victim("vault", m_client).store_settings(config)

    def test_credentials(self):
        self.execute(
            "takeoff.azure.credentials.artifact_store.Settings",
            {'username': "artifactuser", 'password': "artifactpass"}
        )
