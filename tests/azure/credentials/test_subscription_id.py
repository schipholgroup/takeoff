from takeoff.azure.credentials.subscription_id import SubscriptionId as victim
from tests.azure.credentials.base_keyvault_test import KeyVaultBaseTest, CONFIG


class TestSubscriptionId(KeyVaultBaseTest):
    def call_victim(self, m_client, config):
        return victim("vault", m_client).subscription_id(config)

    def test_credentials(self):
        m_client = self.construct_keyvault_mock()
        assert self.call_victim(m_client, CONFIG) == "09eaa212-d59f-4b00-8697-d21e52e9900d"
