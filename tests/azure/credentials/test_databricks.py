from takeoff.azure.credentials.databricks import Databricks as victim
from tests.azure.credentials.base_keyvault_test import KeyVaultBaseTest


class TestDatabricks(KeyVaultBaseTest):
    def call_victim(self, m_client, config):
        victim("vault", m_client).api_client(config)

    def test_credentials(self):
        self.execute(
            "takeoff.azure.credentials.databricks.ApiClient",
            {'token': "dbtoken", 'host': "dbhost"}
        )
