import logging

from msrestazure.azure_active_directory import ServicePrincipalCredentials

from runway.credentials.EnvironmentCredentialsMixin import EnvironmentCredentialsMixin
from runway.util import current_filename


class ApplicationName(EnvironmentCredentialsMixin):
    def get(self, config) -> str:
        credential_kwargs = super()._transform_environment_key_to_credential_kwargs(
            config['common_environment_keys'][current_filename(__file__)]
        )
        logging.info(credential_kwargs)
        return credential_kwargs[current_filename(__file__)]
