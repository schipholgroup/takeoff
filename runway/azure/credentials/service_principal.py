import logging

from msrestazure.azure_active_directory import ServicePrincipalCredentials as SpCredentials

from runway.credentials.EnvironmentCredentialsMixin import EnvironmentCredentialsMixin
from runway.util import current_filename


class ServicePrincipalCredentials(EnvironmentCredentialsMixin):
    def credentials(self, config, env) -> SpCredentials:
        credential_kwargs = super()._transform_environment_key_to_credential_kwargs(
            config[f"ci_environment_keys_{env}"][current_filename(__file__)]
        )
        logging.info(credential_kwargs)
        return SpCredentials(**credential_kwargs)
