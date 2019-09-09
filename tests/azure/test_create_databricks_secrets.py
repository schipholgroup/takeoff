import unittest

import mock

from takeoff.application_version import ApplicationVersion
from takeoff.azure.create_databricks_secrets import CreateDatabricksSecrets as victim
from takeoff.credentials.Secret import Secret
from tests.azure import takeoff_config

BASE_CONF = {'task': 'createDatabricksSecrets'}


class TestCreateDatabricksSecrets(unittest.TestCase):
    @mock.patch("takeoff.step.KeyVaultClient.vault_and_client", return_value=(None, None))
    def test_validate_minimal_schema(self, _):
        conf = {**takeoff_config(), **BASE_CONF}

        victim(ApplicationVersion("dev", "v", "branch"), conf)

    def test_scope_exists(self):
        scopes = {"scopes": [{"name": "foo"}, {"name": "bar"}]}

        assert victim._scope_exists(scopes, "foo")
        assert not victim._scope_exists(scopes, "foobar")

    @mock.patch('takeoff.azure.credentials.KeyVaultCredentialsMixin.KeyVaultCredentialsMixin.get_keyvault_secrets',
                return_value=[Secret('key1', 'foo'), Secret('key2', 'bar')])
    @mock.patch("takeoff.step.KeyVaultClient.vault_and_client", return_value=(None, None))
    def test_combine_secrets_without_deployment_secrets(self, mock_secrets, mock_client):
        config = {**takeoff_config(),
                  **BASE_CONF}
        create_secrets = victim(ApplicationVersion("DEV", "foo", "bar"), config)
        combined_secrets = create_secrets._combine_secrets("some-app-name")
        assert len(combined_secrets) == 2

    @mock.patch('takeoff.azure.credentials.KeyVaultCredentialsMixin.KeyVaultCredentialsMixin.get_keyvault_secrets',
                return_value=[])
    @mock.patch("takeoff.step.KeyVaultClient.vault_and_client", return_value=(None, None))
    def test_combine_secrets_without_deployment_and_keyvault_secrets(self, mock_secrets, mock_client):
        config = {**takeoff_config(),
                  **BASE_CONF}
        create_secrets = victim(ApplicationVersion("DEV", "foo", "bar"), config)
        combined_secrets = create_secrets._combine_secrets("some-app-name")
        assert len(combined_secrets) == 0

    @mock.patch('takeoff.azure.credentials.KeyVaultCredentialsMixin.KeyVaultCredentialsMixin.get_keyvault_secrets',
                return_value=[])
    @mock.patch("takeoff.step.KeyVaultClient.vault_and_client", return_value=(None, None))
    def test_combine_secrets_without_keyvault_secrets(self, mock_secrets, mock_client):
        conf = {
            'task': 'createDatabricksSecrets',
            'dev': [
                {'FOO': 'foo_value'},
                {'BAR': 'bar_value'},
                {'BAZ': 'baz_value'},
            ],
            'acc': [
                {'FOO': 'fooacc_value'},
                {'BAR': 'baracc_value'},
            ]
        }

        config = {**takeoff_config(),
                  **BASE_CONF,
                  **conf}

        create_secrets = victim(ApplicationVersion("DEV", "foo", "bar"), config)
        combined_secrets = create_secrets._combine_secrets("some-app-name")
        assert len(combined_secrets) == 3

    @mock.patch('takeoff.azure.credentials.KeyVaultCredentialsMixin.KeyVaultCredentialsMixin.get_keyvault_secrets',
                return_value=[Secret('key1', 'foo'), Secret('key2', 'bar')])
    @mock.patch("takeoff.step.KeyVaultClient.vault_and_client", return_value=(None, None))
    def test_combine_secrets_with_deployment_and_keyvault_secrets(self, mock_secrets, mock_client):
        conf = {
            'task': 'createDatabricksSecrets',
            'dev': [
                {'FOO': 'foo_value'},
                {'BAR': 'bar_value'},
                {'BAZ': 'baz_value'},
            ],
            'acc': [
                {'FOO': 'fooacc_value'},
                {'BAR': 'baracc_value'},
            ]
        }
        config = {**takeoff_config(),
                  **BASE_CONF,
                  **conf}

        create_secrets = victim(ApplicationVersion("DEV", "foo", "bar"), config)
        combined_secrets = create_secrets._combine_secrets("some-app-name")
        assert len(combined_secrets) == 5

    @mock.patch('takeoff.azure.credentials.KeyVaultCredentialsMixin.KeyVaultCredentialsMixin.get_keyvault_secrets',
                return_value=[Secret('FOO', 'foo'), Secret('BAR', 'bar')])
    @mock.patch("takeoff.step.KeyVaultClient.vault_and_client", return_value=(None, None))
    def test_combine_secrets_with_duplicate_deployment_and_keyvault_secrets(self, mock_secrets, mock_client):
        conf = {
            'task': 'createDatabricksSecrets',
            'dev': [
                {'FOO': 'foo_value'},
                {'BAR': 'bar_value'},
                {'BAZ': 'baz_value'},
            ],
            'acc': [
                {'FOO': 'fooacc_value'},
                {'BAR': 'baracc_value'},
            ]
        }

        config = {**takeoff_config(),
                  **BASE_CONF,
                  **conf}

        create_secrets = victim(ApplicationVersion("DEV", "foo", "bar"), config)
        combined_secrets = create_secrets._combine_secrets("some-app-name")
        assert len(combined_secrets) == 3
