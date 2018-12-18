from azure.keyvault import KeyVaultClient
from typing import Union

from runway.ApplicationVersion import ApplicationVersion
from runway.credentials.azure_service_principle import AzureServicePrincipleCredentials


def azure_keyvault_client(config: dict, env: ApplicationVersion = None, dtap: str = None):
    if not env and not dtap:
        raise KeyError("At least one of 'dtap' or 'env' must be provided")
    if env:
        dtap = env.environment.lower()
    vault = config['runway_azure']['vault_name'].format(dtap=dtap)
    keyvault_client = KeyVaultClient(
        AzureServicePrincipleCredentials().credentials(config, env.environment)
    )

    return vault, keyvault_client
