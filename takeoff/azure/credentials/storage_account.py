from azure.storage.blob import BlockBlobService

from takeoff.azure.credentials.providers.keyvault_credentials_mixin import KeyVaultCredentialsMixin
from takeoff.util import current_filename


class BlobStore(KeyVaultCredentialsMixin):
    def service_client(self, config: dict) -> BlockBlobService:
        credential_kwargs = super()._transform_key_to_credential_kwargs(
            config["azure"]["keyvault_keys"][current_filename(__file__)]
        )
        return BlockBlobService(**credential_kwargs)
