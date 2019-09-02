from azure.keyvault import KeyVaultClient
import logging
from runway.ApplicationVersion import ApplicationVersion
from runway.azure.credentials.service_principal import ServicePrincipalCredentials


class KeyvaultClient(object):
    @staticmethod
    def vault_and_client(config: dict, env: ApplicationVersion = None, dtap: str = None):
        if not env and not dtap:
            raise KeyError("At least one of 'dtap' or 'env' must be provided")
        if env:
            dtap = env.environment.lower()
        vault = config["runway_azure"]["vault_name"].format(dtap=dtap)
        logging.info(config)
        logging.info(dtap)
        keyvault_client = KeyVaultClient(ServicePrincipalCredentials().credentials(config, dtap))

        return vault, keyvault_client
