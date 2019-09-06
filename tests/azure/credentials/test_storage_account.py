from runway.azure.credentials.storage_account import BlobStore as victim
from tests.azure.credentials.base_keyvault_test import KeyVaultBaseTest


class TestBlobStore(KeyVaultBaseTest):
    def call_victim(self, m_client, config):
        victim("vault", m_client).service_client(config)

    def test_credentials(self):
        self.execute(
            "runway.azure.credentials.storage_account.BlockBlobService",
            {'account_name': "blobname", 'account_key': "blobkey"}
        )
