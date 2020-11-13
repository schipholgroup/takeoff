from typing import Dict, Union, Tuple

from takeoff.azure.credentials.keyvault import KeyVaultClient
from takeoff.azure.credentials.providers.keyvault_credentials_mixin import KeyVaultCredentialsMixin
from takeoff.credentials.credential_provider import BaseProvider


class AzureKeyVaultProvider(BaseProvider, KeyVaultCredentialsMixin):
    def __init__(self, config, app_version):
        super().__init__(config, app_version)
        self.vault_name, self.vault_client = KeyVaultClient.vault_and_client(self.config, self.env)

    def get_credentials(self, lookup: Union[str, Dict[str, str], Tuple[str, str]]):
        if not isinstance(lookup, str):
            raise ValueError("Please provide a string")
        return self._transform_key_to_credential_kwargs(self.config["azure"]["keyvault_keys"][lookup])
