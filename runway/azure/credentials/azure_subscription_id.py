from runway.azure.credentials.AzureKeyVaultCredentialsMixin import AzureKeyVaultCredentialsMixin
from runway.util import current_filename


class AzureSubscriptionId(AzureKeyVaultCredentialsMixin):
    def subscription_id(self, config) -> str:
        return super()._credentials([config[f"azure_keyvault_keys"][current_filename(__file__)]])[
            "subscription-id"
        ]
