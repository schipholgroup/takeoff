from azure.storage.blob import BlockBlobService

from runway.azure.credentials.AzureKeyVaultCredentialsMixin import AzureKeyVaultCredentialsMixin
from runway.util import current_filename


class BlobStore(AzureKeyVaultCredentialsMixin):
    def service_client(self, config) -> BlockBlobService:
        credential_kwargs = super()._transform_key_to_credential_kwargs(
            config["azure_keyvault_keys"][current_filename(__file__)]
        )
        return BlockBlobService(**credential_kwargs)
