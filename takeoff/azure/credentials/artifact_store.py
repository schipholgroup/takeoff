from twine.settings import Settings

from takeoff.azure.credentials.providers.keyvault_credentials_mixin import KeyVaultCredentialsMixin
from takeoff.util import current_filename


class ArtifactStore(KeyVaultCredentialsMixin):
    """Connects to the vault and grabs the PyPi credentials.

    Values present in the vault must be:

    - username
    - password
    """

    def store_settings(self, config: dict) -> Settings:
        credential_kwargs = super()._transform_key_to_credential_kwargs(
            config["azure"]["keyvault_keys"][current_filename(__file__)]
        )
        return Settings(**credential_kwargs)
