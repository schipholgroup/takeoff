from msrestazure.azure_active_directory import ServicePrincipalCredentials

from runway.credentials.EnvironmentCredentialsMixin import EnvironmentCredentialsMixin
from runway.util import current_filename


class AzureServicePrincipleCredentials(EnvironmentCredentialsMixin):
    def credentials(self, config, dtap) -> ServicePrincipalCredentials:
        credential_kwargs = super()._transform_environment_key_to_credential_kwargs(
            config[f'devops_environment_keys_dev_{dtap}'][current_filename(__file__)]
        )
        return ServicePrincipalCredentials(**credential_kwargs)
