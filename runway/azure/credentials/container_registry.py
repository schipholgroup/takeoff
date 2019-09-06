from dataclasses import dataclass

from runway.azure.credentials.KeyVaultCredentialsMixin import KeyVaultCredentialsMixin
from runway.util import current_filename


@dataclass(frozen=True)
class DockerCredentials(object):
    username: str
    password: str
    registry: str


class DockerRegistry(KeyVaultCredentialsMixin):
    def credentials(self, config) -> DockerCredentials:
        credential_kwargs = super()._transform_key_to_credential_kwargs(
            config["azure"]["keyvault_keys"][current_filename(__file__)]
        )
        return DockerCredentials(**credential_kwargs)
