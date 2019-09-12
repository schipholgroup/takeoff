from unittest import mock

from azure.keyvault.models import SecretBundle

from takeoff.azure.credentials.keyvault_credentials_provider import KeyVaultCredentialsMixin


class TestAzureKeyVaultCredentialsMixin(object):
    @mock.patch(
        "takeoff.azure.credentials.KeyVaultCredentialsMixin.KeyVaultCredentialsMixin._credentials",
        return_value={"key1": "foo", "key2": "bar"},
    )
    def test_transform_key_to_credential_kwargs(self, _):
        res = KeyVaultCredentialsMixin(None, None)._transform_key_to_credential_kwargs({"arg1": "key1"})
        assert res == {"arg1": "foo"}

    def test_filter_keyvault_ids(self):
        res = KeyVaultCredentialsMixin._filter_keyvault_ids(
            ["common-username", "common-password", "uncommon"], "common"
        )
        assert len(res) == 2
        assert res[0].databricks_secret_key == "username"

    @mock.patch("azure.keyvault.v7_0.key_vault_client.KeyVaultClient")
    def test_credentials(self, client):
        client.get_secrets.return_value = [
            SecretBundle(id="databricks-token"),
            SecretBundle(id="databricks-host"),
            SecretBundle(id="some-other"),
        ]

        res = KeyVaultCredentialsMixin(None, client)._credentials(["databricks-token", "databricks-host"])
        assert len(res) == 2
