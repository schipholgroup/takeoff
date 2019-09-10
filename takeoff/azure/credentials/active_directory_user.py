from msrestazure.azure_active_directory import UserPassCredentials

from takeoff.azure.credentials.KeyVaultCredentialsMixin import KeyVaultCredentialsMixin
from takeoff.util import current_filename


class ActiveDirectoryUserCredentials(KeyVaultCredentialsMixin):
    def credentials(self, config: dict) -> UserPassCredentials:
        credential_kwargs = super()._transform_key_to_credential_kwargs(
            config["azure"]["keyvault_keys"][current_filename(__file__)]
        )
        return UserPassCredentials(**credential_kwargs)
