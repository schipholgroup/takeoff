from azure.storage.blob import BlockBlobService

from runway.azure.credentials.KeyVaultCredentialsMixin import KeyVaultCredentialsMixin
from runway.util import current_filename


class BlobStore(KeyVaultCredentialsMixin):
    def service_client(self, config) -> BlockBlobService:
        credential_kwargs = super()._transform_key_to_credential_kwargs(
            config["azure_keyvault_keys"][current_filename(__file__)]
        )
        return BlockBlobService(**credential_kwargs)
