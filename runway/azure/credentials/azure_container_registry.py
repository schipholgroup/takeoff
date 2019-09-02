from dataclasses import dataclass

from runway.azure.credentials.AzureKeyVaultCredentialsMixin import AzureKeyVaultCredentialsMixin
from runway.util import current_filename


@dataclass(frozen=True)
class DockerCredentials(object):
    username: str
    password: str
    registry: str


class DockerRegistry(AzureKeyVaultCredentialsMixin):
    def credentials(self, config) -> DockerCredentials:
        credential_kwargs = super()._transform_key_to_credential_kwargs(
            config["azure_keyvault_keys"][current_filename(__file__)]
        )
        return DockerCredentials(**credential_kwargs)
