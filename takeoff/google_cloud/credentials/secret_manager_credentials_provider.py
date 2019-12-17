import re
from dataclasses import dataclass
from typing import List, Dict, Optional, Union, Tuple

from google.cloud import kms_v1

from takeoff.util import run_shell_command

kms_v1.KeyManagementServiceClient


from takeoff.azure.credentials.keyvault import KeyVaultClient
from takeoff.credentials.credential_provider import BaseProvider
from takeoff.credentials.secret import Secret
from takeoff.util import get_matching_group, has_prefix_match, inverse_dictionary


@dataclass(frozen=True)
class IdAndKey:
    keyvault_id: str
    databricks_secret_key: str


@dataclass
class KeyVaultSecrets:
    secrets: List[Secret]


class SecretManagerCredentialsMixin(object):
    """Collection of Google Cloud Secret Manager helper functions"""

    # def __init__(self, vault_name: str, vault_client: AzureKeyVaultClient):
    #     self.vault_name = vault_name
    #     self.vault_client = vault_client

    def _transform_key_to_credential_kwargs(self, keys: Dict[str, str]):
        """
        Tranforms a list with Azure KeyVault secret keys to a dictionary
        containing a mapping from object argument name to Azure KeyVault
        secret value

        Args:
            keys (Dict[str, str]): A dictionary containing a mapping from function argument name
                                   to keyvault secret key

        Example:
            config = {
                "keyvault_keys": {
                    "aad_user": {
                        "username": "azure-username",
                        "password": "azure-password"
                    }
                }
            }
            keyvault_keys becomes -> {
                "username": "azure-username",
                "password": "azure-password"
            }
            credentials becomes -> {
                "azure-username": Secret("azure-username", "foo"),
                "azure-password": Secret("azure-password", "bar")
            }
            credentials_kwargs becomes -> {
                "username": "foo"),
                "password": "bar")
            }

        """
        credentials: Dict[str, str] = self._credentials(list(keys.values()))
        credential_kwargs = {
            function_argument: credentials[env_variable]
            for env_variable, function_argument in inverse_dictionary(keys).items()
        }
        return credential_kwargs

    def _credentials(self, keys: List[str], prefix: str = None) -> Dict[str, str]:
        """
        Args:
            keys (List[str]): A list containing the keys to search for in the keyvault
            prefix (str, optional): A prefix to filter keyvault keys on

        Returns:
            Dict[str: Secret]: A dictionary of all secrets matching the keys and prefix, indexed on the key
        """
        secrets = self.get_keyvault_secrets(prefix)
        indexed = {_.key: _ for _ in secrets}
        return {_: self._find_secret(_, indexed) for _ in keys}

    def _find_secret(self, secret_key, secrets: Dict[str, Secret]) -> str:
        if secret_key not in secrets:
            raise ValueError(f"Could not find required key {secret_key}")
        return secrets[secret_key].val

    def get_keyvault_secrets(self, prefix: Optional[str] = "") -> List[Secret]:
        """
        Args:
            prefix (str, optional): A prefix to filter keyvault keys on. Default is the application name

        Returns:
            List[Secret]: The list of all secrets matching the prefix
        """
        return self._retrieve_secrets(self.vault_client, self.vault_name, prefix)

    @staticmethod
    def _extract_keyvault_ids_from(secrets: List[SecretBundle]) -> List[str]:
        """The returned json from Azure KeyVault contains the ids for each secrets, prepended with
        the vault url.

        This functions extracts only the actual key from the url/id

        https://keyvaultdev.vault.azure.net/secrets/application-name-secret-collection
        to
        application-name-secret-collection
        """
        return [_.id.split("/")[-1] for _ in secrets]

    @staticmethod
    def _filter_keyvault_ids(keyvault_ids: List[str], prefix) -> List[IdAndKey]:
        """Extracts the actual keys from the prefixed ids

        flights-arrivals-cosmos-collection
        to
        (flights-arrivals-cosmos-collection, cosmos-collection)
        """
        if prefix:
            pattern = re.compile(rf"^({prefix})-([-A-z0-9]+)*")
            return [
                IdAndKey(_, get_matching_group(_, pattern, 1))
                for _ in keyvault_ids
                if has_prefix_match(_, prefix, pattern)
            ]
        return [IdAndKey(_, _) for _ in keyvault_ids]

    def _retrieve_secrets(
            self, client: AzureKeyVaultClient, vault: str, prefix: Optional[str]
    ) -> List[Secret]:
        secrets = list(client.get_secrets(vault))
        secrets_ids = self._extract_keyvault_ids_from(secrets)
        secrets_filtered = self._filter_keyvault_ids(secrets_ids, prefix)

        app_secrets = [
            Secret(_.databricks_secret_key, client.get_secret(vault, _.keyvault_id, "").value)
            for _ in secrets_filtered
        ]

        return app_secrets


class GoogleCloudSecretManagerProvider(BaseProvider):
    def __init__(self, config, app_version):
        super().__init__(config, app_version)
        self.vault_name, self.vault_client = KeyVaultClient.vault_and_client(self.config, self.env)

    def get_credentials(self, lookup: Union[str, Dict[str, str], Tuple[str, str]]):
        if not isinstance(lookup, str):
            raise ValueError("Please provide a string")
        return self.
        return self._transform_key_to_credential_kwargs(self.config["azure"]["keyvault_keys"][lookup])

    def get_secrets(self, project_id, prefix: Optional[str]):
        cmd = ["gcloud",
               "beta",
               "secrets",
               "list"]
        res = run_shell_command(command)


    def _retrieve_secrets(
            self, project_id: str, prefix: Optional[str]
    ) -> List[Secret]:
        secrets = list(client.get_secrets(vault))
        secrets_ids = self._extract_keyvault_ids_from(secrets)
        secrets_filtered = self._filter_keyvault_ids(secrets_ids, prefix)

        app_secrets = [
            Secret(_.databricks_secret_key, client.get_secret(vault, _.keyvault_id, "").value)
            for _ in secrets_filtered
        ]

        return app_secrets

