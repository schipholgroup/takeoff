from msrestazure.azure_active_directory import ServicePrincipalCredentials as SpCredentials

from takeoff.credentials.environment_credentials_provider import EnvironmentCredentialsMixin
from takeoff.util import current_filename


class ServicePrincipalCredentials(EnvironmentCredentialsMixin):
    def credentials(self, config: dict, env: str) -> SpCredentials:
        credential_kwargs = super()._transform_environment_key_to_credential_kwargs(
            config[f"ci_environment_keys_{env}"][current_filename(__file__)]
        )
        return SpCredentials(**credential_kwargs)


