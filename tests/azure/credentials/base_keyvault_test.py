import abc
import unittest
from dataclasses import dataclass
from unittest import mock


@dataclass
class MockKeyVaultId:
    id: str


@dataclass
class MockKeyVaultSecret:
    value: str


VALUES = [('az-username', 'azuser'),
          ('az-password', 'azpass'),
          ('artifact-store-username', 'artifactuser'),
          ('artifact-store-password', 'artifactpass'),
          ('container-registry-username', 'registryuser'),
          ('container-registry-password', 'registrypass'),
          ('databricks-host', 'dbhost'),
          ('databricks-token', 'dbtoken'),
          ('storage-account-name', 'blobname'),
          ('storage-account-key', 'blobkey'),
          ('subscription-id', '09eaa212-d59f-4b00-8697-d21e52e9900d')
          ]

PREFIX = "https://keyvaultdev.vault.azure.net/secrets/"

CONFIG = {"azure": {"keyvault_keys":
    {
        "artifact_store":
            {"username": "artifact-store-username",
             "password": "artifact-store-password"},
        "active_directory_user":
            {"username": "az-username",
             "password": "az-password"},
        "container_registry":
            {"username": "container-registry-username",
             "password": "container-registry-password"},
        "databricks":
            {"host": "databricks-host",
             "token": "databricks-token"},
        "storage_account":
            {"account_name": "storage-account-name",
             "account_key": "storage-account-key"},
        "subscription_id": "subscription-id",
    }}}


class KeyVaultBaseTest(unittest.TestCase):

    def construct_keyvault_mock(self):
        m_client = mock.Mock()
        m_client.configure_mock(
            **{'get_secrets.return_value':
                   list(map(MockKeyVaultId, map(lambda x: f"{PREFIX}{x[0]}", VALUES))),
               'get_secret.side_effect':
                   list(map(MockKeyVaultSecret, map(lambda x: x[1], VALUES)))
               })
        return m_client

    def execute(self, mock_class, assertion):
        m_client = self.construct_keyvault_mock()
        with mock.patch(mock_class) as m:
            self.call_victim(m_client, CONFIG)
        m.assert_called_once_with(**assertion)

    @abc.abstractmethod
    def call_victim(self, m_client, config):
        pass
