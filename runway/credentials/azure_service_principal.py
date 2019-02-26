import logging

from msrestazure.azure_active_directory import ServicePrincipalCredentials

from runway.credentials.EnvironmentCredentialsMixin import EnvironmentCredentialsMixin
from runway.util import current_filename


class AzureServicePrincipalCredentials(EnvironmentCredentialsMixin):
    def credentials(self, config, dtap) -> ServicePrincipalCredentials:
        credential_kwargs = super()._transform_environment_key_to_credential_kwargs(
            config[f"devops_environment_keys_{dtap.lower()}"][current_filename(__file__)]
        )
        logging.info(credential_kwargs)
        return ServicePrincipalCredentials(**credential_kwargs)
