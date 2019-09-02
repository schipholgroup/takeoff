from twine.settings import Settings

from runway.azure.credentials.AzureKeyVaultCredentialsMixin import AzureKeyVaultCredentialsMixin
from runway.util import current_filename


class ArtifactStore(AzureKeyVaultCredentialsMixin):
    def store_settings(self, config) -> Settings:
        credential_kwargs = super()._transform_key_to_credential_kwargs(
            config["azure_keyvault_keys"][current_filename(__file__)]
        )
        return Settings(**credential_kwargs)
