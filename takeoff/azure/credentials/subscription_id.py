from takeoff.azure.credentials.providers.keyvault_credentials_mixin import KeyVaultCredentialsMixin
from takeoff.util import current_filename


class SubscriptionId(KeyVaultCredentialsMixin):
    """Connects to the vault and grabs the Subscription ID."""

    def subscription_id(self, config: dict) -> str:
        return super()._credentials([config["azure"]["keyvault_keys"][current_filename(__file__)]])[
            "subscription-id"
        ]
