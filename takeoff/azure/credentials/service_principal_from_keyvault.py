from takeoff.azure.credentials.keyvault_credentials_provider import KeyVaultCredentialsMixin
from msrestazure.azure_active_directory import ServicePrincipalCredentials as SpCredentials


class ServicePrincipalCredentialsFromVault(KeyVaultCredentialsMixin):
    def credentials(self, config: dict) -> SpCredentials:
        credential_kwargs = super()._transform_key_to_credential_kwargs(
            # config[f"ci_environment_keys_{env}"]["service_principal"]
            config["azure"]["keyvault_keys"]["service_principal"]
        )
        return SpCredentials(**credential_kwargs)
