from dataclasses import dataclass

from takeoff.azure.credentials.KeyVaultCredentialsMixin import KeyVaultCredentialsMixin
from takeoff.util import current_filename


@dataclass(frozen=True)
class DockerCredentials(object):
    username: str
    password: str
    registry: str


class DockerRegistry(KeyVaultCredentialsMixin):
    """Connects to the vault and grabs the docker credentials.

    Values present in the vault must be:

    - username
    - password
    - registry
    """

    def credentials(self, config: dict) -> DockerCredentials:
        credential_kwargs = super()._transform_key_to_credential_kwargs(
            config["azure"]["keyvault_keys"][current_filename(__file__)]
        )
        return DockerCredentials(**credential_kwargs)
