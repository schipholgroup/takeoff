import unittest
from dataclasses import dataclass

import mock

from runway.azure.credentials.active_directory_user import ActiveDirectoryUserCredentials as victim


@dataclass
class MockKeyVaultId:
    id: str


@dataclass
class MockKeyVaultSecret:
    value: str


class TestActiveDirectoryUserCredentials(unittest.TestCase):
    def test_credentials(self):
        config = {"azure": {"keyvault_keys": {"active_directory_user":
                                                  {"username": "az-username",
                                                   "password": "az-password"}
                                              }}}
        ids = [MockKeyVaultId("https://keyvaultdev.vault.azure.net/secrets/az-username"),
               MockKeyVaultId("https://keyvaultdev.vault.azure.net/secrets/az-password")]
        secrets = [MockKeyVaultSecret("user"),
                   MockKeyVaultSecret("pass")]

        m_client = mock.Mock()
        m_client.configure_mock(**{'get_secrets.return_value': ids, 'get_secret.side_effect': secrets})
        with mock.patch("runway.azure.credentials.active_directory_user.UserPassCredentials") as m:
            victim("vault", m_client).credentials(config)
        m.assert_called_once_with(username="user", password="pass")
