from azure.keyvault import KeyVaultClient

from runway.ApplicationVersion import ApplicationVersion
from runway.azure.credentials.service_principal import ServicePrincipalCredentials
from runway.azure.util import get_keyvault_name


class KeyvaultClient(object):
    @staticmethod
    def vault_and_client(config: dict, env: ApplicationVersion = None):
        vault = get_keyvault_name(config, env)
        keyvault_client = KeyVaultClient(
            ServicePrincipalCredentials().credentials(config, env.environment_lower)
        )

        return vault, keyvault_client
