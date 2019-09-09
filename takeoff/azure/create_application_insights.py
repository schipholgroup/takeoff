import logging

import voluptuous as vol
from azure.mgmt.applicationinsights import ApplicationInsightsManagementClient
from azure.mgmt.applicationinsights.models import ApplicationInsightsComponent

from takeoff.application_version import ApplicationVersion
from takeoff.azure.create_databricks_secrets import CreateDatabricksSecretFromValue
from takeoff.azure.credentials.active_directory_user import ActiveDirectoryUserCredentials
from takeoff.azure.credentials.subscription_id import SubscriptionId
from takeoff.azure.util import get_resource_group_name
from takeoff.credentials.Secret import Secret
from takeoff.credentials.application_name import ApplicationName
from takeoff.schemas import TAKEOFF_BASE_SCHEMA
from takeoff.step import Step

logger = logging.getLogger(__name__)

SCHEMA = TAKEOFF_BASE_SCHEMA.extend(
    {
        vol.Required("task"): "createApplicationInsights",
        vol.Required("kind"): vol.Any("web", "ios", "other", "store", "java", "phone"),
        vol.Required("applicationType"): vol.Any("web", "other"),
        vol.Optional("createDatabricksSecret", default=False): bool,
    },
    extra=vol.ALLOW_EXTRA,
)


class CreateApplicationInsights(Step):
    def __init__(self, env: ApplicationVersion, config: dict):
        super().__init__(env, config)

    def schema(self) -> vol.Schema:
        return SCHEMA

    def run(self):
        self.create_application_insights()

    def create_application_insights(self):
        application_name = ApplicationName().get(self.config)
        client = self._create_client()

        insight = self._find_existing_instance(client, application_name)
        if not insight:
            logger.info("Creating new Application Insights...")
            # Create a new Application Insights
            comp = ApplicationInsightsComponent(
                location=self.config["azure"]["location"],
                kind=self.config["kind"],
                application_type=self.config["applicationType"],
            )
            insight = client.components.create_or_update(
                get_resource_group_name(self.config, self.env), application_name, comp
            )
            if self.config["createDatabricksSecret"]:
                instrumentation_secret = Secret("instrumentation-key", insight.instrumentation_key)
                self.create_databricks_secret(application_name, instrumentation_secret)

    def create_databricks_secret(self, application_name, instrumentation_secret):
        db = CreateDatabricksSecretFromValue(self.env, self.config)
        db._create_scope(application_name)
        db._add_secrets(application_name, [instrumentation_secret])

    def _create_client(self) -> ApplicationInsightsManagementClient:
        azure_user_credentials = ActiveDirectoryUserCredentials(
            vault_name=self.vault_name, vault_client=self.vault_client
        ).credentials(self.config)

        return ApplicationInsightsManagementClient(
            azure_user_credentials,
            SubscriptionId(self.vault_name, self.vault_client).subscription_id(self.config),
        )

    def _find_existing_instance(self, client: ApplicationInsightsManagementClient, name: str):
        for insight in client.components.list():
            if insight.name == name:
                return insight
        return None
