import mock
import os
import pytest

from dataclasses import dataclass

from takeoff.application_version import ApplicationVersion
from takeoff.azure.create_databricks_secrets import CreateDatabricksSecrets
from takeoff.credentials.Secret import Secret
from tests.azure import takeoff_config


@dataclass
class MockDatabricksClient:
    def api_client(self, config):
        return None


BASE_CONF = {'task': 'createDatabricksSecrets'}

TEST_ENV_VARS = {'AZURE_TENANTID': 'David',
                 'AZURE_KEYVAULT_SP_USERNAME_DEV': 'Doctor',
                 'AZURE_KEYVAULT_SP_PASSWORD_DEV': 'Who',
                 'CI_PROJECT_NAME': 'my_little_pony',
                 'CI_COMMIT_REF_SLUG': 'my-little-pony'}

@pytest.fixture(autouse=True)
@mock.patch.dict(os.environ, TEST_ENV_VARS)
def victim():
    m_client = mock.MagicMock()
    m_client.consumer_groups.list_by_event_hub.return_value = {}

    secrets_conf = {
        'task': 'createDatabricksSecrets',
        'dev': [
            {'FOO': 'foo_value'},
            {'BAR': 'bar_value'},
        ],
        'acp': [
            {'FOO': 'fooacc_value'},
            {'BAR': 'baracc_value'},
            {'BAZ': 'baz_value'},
        ]
    }

    with mock.patch("takeoff.step.KeyVaultClient.vault_and_client", return_value=(None, None)), \
         mock.patch("takeoff.azure.create_databricks_secrets.Databricks", return_value=MockDatabricksClient()), \
         mock.patch("takeoff.azure.create_databricks_secrets.SecretApi", return_value={}):
        conf = {**takeoff_config(), **BASE_CONF, **{"common": {"databricks_library_path": "/path"}}, **secrets_conf}
        return CreateDatabricksSecrets(ApplicationVersion('ACP', 'bar', 'foo'), conf)


@pytest.fixture(autouse=True)
@mock.patch.dict(os.environ, TEST_ENV_VARS)
def victim_without_secrets():
    m_client = mock.MagicMock()
    m_client.consumer_groups.list_by_event_hub.return_value = {}

    with mock.patch("takeoff.step.KeyVaultClient.vault_and_client", return_value=(None, None)), \
         mock.patch("takeoff.azure.create_databricks_secrets.Databricks", return_value=MockDatabricksClient()), \
         mock.patch("takeoff.azure.create_databricks_secrets.SecretApi", return_value={}):
        conf = {**takeoff_config(), **BASE_CONF, **{"common": {"databricks_library_path": "/path"}}}
        return CreateDatabricksSecrets(ApplicationVersion('ACP', 'bar', 'foo'), conf)

class TestCreateDatabricksSecrets(object):
    @mock.patch("takeoff.step.KeyVaultClient.vault_and_client", return_value=(None, None))
    @mock.patch("takeoff.azure.create_databricks_secrets.Databricks", return_value=MockDatabricksClient())
    @mock.patch("takeoff.azure.create_databricks_secrets.SecretApi", return_value={})
    def test_validate_minimal_schema(self, _, __, ___):
        conf = {**takeoff_config(), **BASE_CONF}
        CreateDatabricksSecrets(ApplicationVersion('ACP', 'bar', 'foo'), conf)

    def test_scope_exists(self, victim):
        scopes = {"scopes": [{"name": "foo"}, {"name": "bar"}]}

        assert victim._scope_exists(scopes, "foo")
        assert not victim._scope_exists(scopes, "foobar")

    @mock.patch('takeoff.azure.credentials.KeyVaultCredentialsMixin.KeyVaultCredentialsMixin.get_keyvault_secrets',
                return_value=[Secret('key1', 'foo'), Secret('key2', 'bar')])
    def test_combine_secrets_without_deployment_secrets(self, mock_secrets, victim_without_secrets):
        combined_secrets = victim_without_secrets._combine_secrets("some-app-name")
        assert len(combined_secrets) == 2

    @mock.patch('takeoff.azure.credentials.KeyVaultCredentialsMixin.KeyVaultCredentialsMixin.get_keyvault_secrets',
                return_value=[])
    def test_combine_secrets_without_deployment_and_keyvault_secrets(self, mock_secrets, victim_without_secrets):
        combined_secrets = victim_without_secrets._combine_secrets("some-app-name")
        assert len(combined_secrets) == 0

    @mock.patch('takeoff.azure.credentials.KeyVaultCredentialsMixin.KeyVaultCredentialsMixin.get_keyvault_secrets',
                return_value=[])
    def test_combine_secrets_without_keyvault_secrets(self, mock_secrets, victim):
        combined_secrets = victim._combine_secrets("some-app-name")
        assert len(combined_secrets) == 3

    @mock.patch('takeoff.azure.credentials.KeyVaultCredentialsMixin.KeyVaultCredentialsMixin.get_keyvault_secrets',
                return_value=[Secret('key1', 'foo'), Secret('key2', 'bar')])
    def test_combine_secrets_with_deployment_and_keyvault_secrets(self, mock_secrets, victim):
        combined_secrets = victim._combine_secrets("some-app-name")
        assert len(combined_secrets) == 5

    @mock.patch('takeoff.azure.credentials.KeyVaultCredentialsMixin.KeyVaultCredentialsMixin.get_keyvault_secrets',
                return_value=[Secret('FOO', 'foo'), Secret('BAR', 'bar')])
    def test_combine_secrets_with_duplicate_deployment_and_keyvault_secrets(self, mock_secrets, victim):
        combined_secrets = victim._combine_secrets("some-app-name")
        assert len(combined_secrets) == 3
