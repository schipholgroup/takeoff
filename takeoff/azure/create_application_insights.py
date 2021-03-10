import logging
from typing import Union

import voluptuous as vol
from azure.mgmt.applicationinsights import ApplicationInsightsManagementClient
from azure.mgmt.applicationinsights.models import ApplicationInsightsComponent

from takeoff.application_version import ApplicationVersion
from takeoff.azure.create_databricks_secrets import CreateDatabricksSecretFromValue
from takeoff.azure.credentials.keyvault import KeyVaultClient
from takeoff.azure.credentials.subscription_id import SubscriptionId
from takeoff.azure.util import get_resource_group_name, get_azure_credentials_object
from takeoff.credentials.secret import Secret
from takeoff.schemas import TAKEOFF_BASE_SCHEMA
from takeoff.step import Step

logger = logging.getLogger(__name__)

SCHEMA = TAKEOFF_BASE_SCHEMA.extend(
    {
        vol.Required("task"): "create_application_insights",
        vol.Required("kind"): vol.Any("web", "ios", "other", "store", "java", "phone"),
        vol.Required("application_type"): vol.Any("web", "other"),
        vol.Optional("create_databricks_secret", default=False): bool,
    },
    extra=vol.ALLOW_EXTRA,
)


class CreateApplicationInsights(Step):
    """Create an Application Insights service

    Credentials for an AAD user (username, password) must be available
    in your cloud vault.

    Optionally propagate the instrumentation key to Databricks as secret.
    """

    def __init__(self, env: ApplicationVersion, config: dict):
        super().__init__(env, config)
        self.vault_name, self.vault_client = KeyVaultClient.vault_and_client(self.config, self.env)

    def schema(self) -> vol.Schema:
        return SCHEMA

    def run(self):
        self.create_application_insights()

    def create_application_insights(self):
        client = self._create_client()

        insight = self._find_existing_instance(client, self.application_name)
        if not insight:
            logger.info("Creating new Application Insights...")
            # Create a new Application Insights
            comp = ApplicationInsightsComponent(
                location=self.config["azure"]["location"],
                kind=self.config["kind"],
                application_type=self.config["application_type"],
            )
            insight = client.components.create_or_update(
                get_resource_group_name(self.config, self.env), self.application_name, comp
            )

        if self.config["create_databricks_secret"]:
            instrumentation_secret = Secret("instrumentation-key", insight.instrumentation_key)
            self.create_databricks_secret(self.application_name, instrumentation_secret)

    def create_databricks_secret(self, application_name: str, instrumentation_secret: Secret):
        """Create Databricks secret for Application Insights connectivity

        Args:
            application_name: Name of the application
            instrumentation_secret: Secret to connect to Application Insights
        """
        db = CreateDatabricksSecretFromValue(self.env, self.config)
        db._create_scope(application_name)
        db._add_secrets(application_name, [instrumentation_secret])

    def _create_client(self) -> ApplicationInsightsManagementClient:
        """Construct Application Insights management client

        Returns:
            An Application Insights management client
        """
        credentials = get_azure_credentials_object(self.config, self.vault_name, self.vault_client)

        return ApplicationInsightsManagementClient(
            credentials,
            SubscriptionId(self.vault_name, self.vault_client).subscription_id(self.config),
        )

    def _find_existing_instance(
        self, client: ApplicationInsightsManagementClient, name: str
    ) -> Union[None, ApplicationInsightsComponent]:
        """Tries to find an existing Application Insights

        Args:
            client: an Application Insights management client
            name: The name of the Application Insights service to search for

        Returns:
            Either an Application Insights Component or None
        """
        for insight in client.components.list():
            if insight.name == name:
                return insight
        return None
