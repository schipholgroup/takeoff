from msrestazure.azure_active_directory import UserPassCredentials

from runway.azure.credentials.KeyVaultCredentialsMixin import KeyVaultCredentialsMixin
from runway.util import current_filename


class ActiveDirectoryUserCredentials(KeyVaultCredentialsMixin):
    def credentials(self, config) -> UserPassCredentials:
        credential_kwargs = super()._transform_key_to_credential_kwargs(
            config["azure_keyvault_keys"][current_filename(__file__)]
        )
        return UserPassCredentials(**credential_kwargs)
