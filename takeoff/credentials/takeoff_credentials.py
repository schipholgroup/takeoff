from takeoff.application_version import ApplicationVersion
from takeoff.azure.credentials.keyvault_credentials_provider import AzureKeyVaultProvider
from takeoff.credentials.credential_provider import BaseProvider
from takeoff.credentials.environment_credentials_provider import CIEnvironmentCredentials
from takeoff.google_cloud.credentials.secret_manager_credentials_provider import GoogleCloudSecretManagerProvider


class TakeoffCredentials:
    def __init__(self, config: dict, app_version: ApplicationVersion):
        self.config = config
        self.env = app_version
        self.provider = self.__credential_provider()

    def __credential_provider(self) -> BaseProvider:
        """Looks in the step and tries to find out which credentials provider should be used.

        Returns:
            A BaseProvider that contains implements the `get_credentials` method
        """
        creds = self.config["credentials"]
        if creds == "azure_keyvault":
            return AzureKeyVaultProvider(self.config, self.env)
        elif creds == "google_cloud_secret_manager":
            return GoogleCloudSecretManagerProvider(self.config, self.env)
        elif creds == "environment_variables":
            return CIEnvironmentCredentials(self.config, self.env)
        raise ValueError("Other credential type not supported")
