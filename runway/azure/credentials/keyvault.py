from azure.keyvault import KeyVaultClient as AzureKeyVaultClient

from runway.application_version import ApplicationVersion
from runway.azure.credentials.service_principal import ServicePrincipalCredentials
from runway.azure.util import get_keyvault_name


class KeyVaultClient(object):
    @staticmethod
    def vault_and_client(config: dict, env: ApplicationVersion):
        vault = get_keyvault_name(config, env)
        keyvault_client = AzureKeyVaultClient(
            credentials=ServicePrincipalCredentials().credentials(config, env.environment_formatted)
        )

        return vault, keyvault_client
