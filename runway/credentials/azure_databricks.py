from databricks_cli.sdk import ApiClient

from runway.credentials.KeyVaultCredentialsMixin import KeyVaultCredentialsMixin
from runway.util import current_filename


class DatabricksClient(KeyVaultCredentialsMixin):
    def credentials(self, config) -> ApiClient:
        credential_kwargs = super()._transform_key_to_credential_kwargs(
            config['azure_keyvault_keys'][current_filename(__file__)]
        )
        return ApiClient(**credential_kwargs)
