from takeoff.azure.credentials.keyvault_credentials_provider import AzureKeyVaultProvider
from takeoff.credentials.credential_provider import BaseProvider
from takeoff.credentials.environment_credentials_provider import EnviromentCredentialsProvider


class TakeoffCredentials:
    def __init__(self, config, env):
        self.config = config
        self.env = env
        self.provider = self.credential_provider()

    def credential_provider(self) -> BaseProvider:
        creds = self.config["credentials"]
        if creds == "azure_keyvault":
            return AzureKeyVaultProvider(self.config, self.env)
        elif creds == "environment_variables":
            return EnviromentCredentialsProvider(self.config, self.env)
        raise ValueError("Other credential type not supported")
