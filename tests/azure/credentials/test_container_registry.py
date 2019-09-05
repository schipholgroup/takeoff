from runway.azure.credentials.container_registry import DockerRegistry as victim
from tests.azure.credentials import KeyVaultBaseTest


class TestDockerRegistry(KeyVaultBaseTest):
    def call_victim(self, m_client, config):
        victim("vault", m_client).credentials(config)

    def test_credentials(self):
        self.execute(
            "runway.azure.credentials.container_registry.DockerCredentials",
            {'username': "registryuser", 'password': "registrypass"}
        )
