from takeoff.azure.credentials.KeyVaultCredentialsMixin import KeyVaultCredentialsMixin
from takeoff.util import current_filename


class SubscriptionId(KeyVaultCredentialsMixin):
    def subscription_id(self, config: dict) -> str:
        return super()._credentials([config["azure"]["keyvault_keys"][current_filename(__file__)]])[
            "subscription-id"
        ]
