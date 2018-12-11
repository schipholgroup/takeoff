import re
from dataclasses import dataclass
from typing import List

from azure.keyvault import KeyVaultClient
from azure.keyvault.models import SecretBundle

from runway.util import get_azure_sp_credentials, get_application_name, get_matching_group, has_prefix_match


@dataclass(frozen=True)
class IdAndKey:
    keyvault_id: str
    databricks_secret_key: str


@dataclass(frozen=True)
class Secret:
    key: str
    val: str

    @property
    def env_key(self):
        return self.key.upper().replace('-', '_')


@dataclass
class KeyVaultSecrets:
    secrets: List[Secret]

    @staticmethod
    def _extract_keyvault_ids_from(secrets: List[SecretBundle]) -> List[str]:
        """The returned json from Azure KeyVault contains the ids for each secrets, prepended with
        the vault url.

        This functions extracts only the actual key from the url/id

        https://sdhkeyvaultdev.vault.azure.net/secrets/flights-arrivals-cosmos-collection
        to
        flights-arrivals-cosmos-collection
        """
        return [_.id.split("/")[-1] for _ in secrets]

    @staticmethod
    def _filter_keyvault_ids(keyvault_ids: List[str], prefix) -> List[IdAndKey]:
        """Extracts the actual keys from the prefixed ids

        flights-arrivals-cosmos-collection
        to
        (flights-arrivals-cosmos-collection, cosmos-collection)
        """
        pattern = re.compile(rf"^({prefix})-([-A-z0-9]+)*")

        return [
            IdAndKey(_, get_matching_group(_, pattern, 1))
            for _ in keyvault_ids
            if has_prefix_match(_, prefix, pattern)
        ]

    @staticmethod
    def _retrieve_secrets(client: KeyVaultClient,
                          vault: str,
                          prefix: str) -> List[Secret]:
        secrets = list(client.get_secrets(vault))
        secrets_ids = KeyVaultSecrets._extract_keyvault_ids_from(secrets)
        secrets_filtered = KeyVaultSecrets._filter_keyvault_ids(secrets_ids, prefix)

        app_secrets = [
            Secret(
                _.databricks_secret_key,
                client.get_secret(vault, _.keyvault_id, "").value,
            )
            for _ in secrets_filtered
        ]

        return app_secrets

    def get_keyvault_secrets(dtap: str, prefix=None):
        if not prefix:
            prefix = get_application_name()
        keyvault_client = KeyVaultClient(get_azure_sp_credentials(dtap))
        vault = f"https://sdhkeyvault{dtap.lower()}.vault.azure.net/"
        return KeyVaultSecrets._retrieve_secrets(keyvault_client, vault, prefix)
