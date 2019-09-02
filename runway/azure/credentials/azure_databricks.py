from databricks_cli.sdk import ApiClient

from runway.azure.credentials.AzureKeyVaultCredentialsMixin import AzureKeyVaultCredentialsMixin
from runway.util import current_filename


class Databricks(AzureKeyVaultCredentialsMixin):
    def api_client(self, config) -> ApiClient:
        credential_kwargs = super()._transform_key_to_credential_kwargs(
            config["azure_keyvault_keys"][current_filename(__file__)]
        )
        return ApiClient(**credential_kwargs)
