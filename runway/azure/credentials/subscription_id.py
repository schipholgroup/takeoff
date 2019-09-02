from runway.azure.credentials.KeyVaultCredentialsMixin import KeyVaultCredentialsMixin
from runway.util import current_filename


class SubscriptionId(KeyVaultCredentialsMixin):
    def subscription_id(self, config) -> str:
        return super()._credentials([config[f"azure_keyvault_keys"][current_filename(__file__)]])[
            "subscription-id"
        ]
