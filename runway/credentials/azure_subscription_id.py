from runway.credentials.KeyVaultCredentialsMixin import KeyVaultCredentialsMixin
from runway.util import current_filename


class AzureSubscriptionId(KeyVaultCredentialsMixin):
    def credentials(self, config) -> str:
        return super()._credentials([config[f'azure_keyvault_keys'][current_filename(__file__)]])[0]
