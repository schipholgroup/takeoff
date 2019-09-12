import os
from dataclasses import dataclass

import mock
import pytest

from takeoff.application_version import ApplicationVersion
from takeoff.azure.create_databricks_secrets import CreateDatabricksSecretsFromVault, CreateDatabricksSecretFromValue, CreateDatabricksSecretsMixin
from takeoff.credentials.secret import Secret
from tests.azure import takeoff_config


@dataclass
class MockDatabricksClient:
    def api_client(self, config):
        return None


BASE_CONF = {'task': 'createDatabricksSecretsFromVault'}

TEST_ENV_VARS = {'AZURE_TENANTID': 'David',
                 'AZURE_KEYVAULT_SP_USERNAME_DEV': 'Doctor',
                 'AZURE_KEYVAULT_SP_PASSWORD_DEV': 'Who',
                 'CI_PROJECT_NAME': 'my_little_pony',
                 'CI_COMMIT_REF_SLUG': 'my-little-pony'}


@mock.patch.dict(os.environ, TEST_ENV_VARS)
def setup_victim(add_secrets: bool):
    secrets_conf = {}
    if add_secrets:
        secrets_conf = {
            'task': 'createDatabricksSecretsFromVault',
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

    m_client = mock.MagicMock()
    m_client.consumer_groups.list_by_event_hub.return_value = {}
    m_client.list_scopes.return_value = {"scopes": [{"name": "scope1"}, {"name": " scope2"}]}
    m_client.create_scope.return_value = True
    m_client.put_secret.return_value = True

    with mock.patch("takeoff.step.KeyVaultClient.vault_and_client", return_value=(None, None)), \
         mock.patch("takeoff.azure.create_databricks_secrets.Databricks", return_value=MockDatabricksClient()), \
         mock.patch("takeoff.azure.create_databricks_secrets.SecretApi", return_value=m_client):
        conf = {**takeoff_config(), **BASE_CONF, **{"common": {"databricks_library_path": "/path"}}, **secrets_conf}
        return CreateDatabricksSecretsFromVault(ApplicationVersion('ACP', '0.0.0', 'my-branch'), conf)


@pytest.fixture(autouse=True)
def victim():
    return setup_victim(add_secrets=True)


@pytest.fixture(autouse=True)
def victim_without_secrets():
    return setup_victim(add_secrets=False)


class TestCreateDatabricksSecretsFromVault(object):
    @mock.patch("takeoff.step.KeyVaultClient.vault_and_client", return_value=(None, None))
    @mock.patch("takeoff.azure.create_databricks_secrets.Databricks", return_value=MockDatabricksClient())
    @mock.patch("takeoff.azure.create_databricks_secrets.SecretApi", return_value={})
    def test_validate_minimal_schema(self, _, __, ___):
        conf = {**takeoff_config(), **BASE_CONF}
        CreateDatabricksSecretsFromVault(ApplicationVersion('ACP', 'bar', 'foo'), conf)

    def test_scope_exists(self, victim):
        scopes = {"scopes": [{"name": "foo"}, {"name": "bar"}]}

        assert victim._scope_exists(scopes, "foo")
        assert not victim._scope_exists(scopes, "foobar")

    @mock.patch('takeoff.azure.credentials.KeyVaultCredentialsMixin.KeyVaultCredentialsMixin.get_keyvault_secrets',
                return_value=[Secret('key1', 'foo'), Secret('key2', 'bar')])
    def test_combine_secrets_without_deployment_secrets(self, _, victim_without_secrets):
        combined_secrets = victim_without_secrets._combine_secrets("some-app-name")
        assert len(combined_secrets) == 2

    @mock.patch('takeoff.azure.credentials.KeyVaultCredentialsMixin.KeyVaultCredentialsMixin.get_keyvault_secrets',
                return_value=[])
    def test_combine_secrets_without_deployment_and_keyvault_secrets(self, _, victim_without_secrets):
        combined_secrets = victim_without_secrets._combine_secrets("some-app-name")
        assert len(combined_secrets) == 0

    @mock.patch('takeoff.azure.credentials.KeyVaultCredentialsMixin.KeyVaultCredentialsMixin.get_keyvault_secrets',
                return_value=[])
    def test_combine_secrets_without_keyvault_secrets(self, _, victim):
        combined_secrets = victim._combine_secrets("some-app-name")
        assert len(combined_secrets) == 3

    @mock.patch('takeoff.azure.credentials.KeyVaultCredentialsMixin.KeyVaultCredentialsMixin.get_keyvault_secrets',
                return_value=[Secret('key1', 'foo'), Secret('key2', 'bar')])
    def test_combine_secrets_with_deployment_and_keyvault_secrets(self, _, victim):
        combined_secrets = victim._combine_secrets("some-app-name")
        assert len(combined_secrets) == 5

    @mock.patch('takeoff.azure.credentials.KeyVaultCredentialsMixin.KeyVaultCredentialsMixin.get_keyvault_secrets',
                return_value=[Secret('FOO', 'foo'), Secret('BAR', 'bar')])
    def test_combine_secrets_with_duplicate_deployment_and_keyvault_secrets(self, _, victim):
        combined_secrets = victim._combine_secrets("some-app-name")
        assert len(combined_secrets) == 3

    def test_create_scope(self, victim):
        victim._create_scope("my-awesome-scope")
        victim.secret_api.create_scope.assert_called_once_with("my-awesome-scope", None)

    def test_create_scope_already_exists(self, victim):
        victim._create_scope("scope1")
        victim.secret_api.create_scope.assert_not_called()

    def test_add_secrets(self, victim):
        secrets = [Secret("foo", "oof"), Secret("bar", "rab")]

        victim._add_secrets("my-scope", secrets)
        calls = [mock.call("my-scope", "foo", "oof", None),
                 mock.call("my-scope", "bar", "rab", None)]
        victim.secret_api.put_secret.assert_has_calls(calls)


class TestCreateDatabricksSecretFromVault(object):
    @mock.patch("takeoff.step.KeyVaultClient.vault_and_client", return_value=(None, None))
    @mock.patch("takeoff.azure.create_databricks_secrets.Databricks", return_value=MockDatabricksClient())
    @mock.patch("takeoff.azure.create_databricks_secrets.SecretApi", return_value={})
    def test_validate_minimal_schema(self, m_vault, m_db, m_secret):
        CreateDatabricksSecretFromValue(ApplicationVersion('ACP', 'bar', 'foo'), {})
        m_vault.assert_called_once()
        m_db.assert_called_once()
        m_secret.assert_called_once()


class TestCreateDatabricksSecretsMixin(object):
    def test_constructor(self):
        with pytest.raises(BaseException):
            CreateDatabricksSecretsMixin()
