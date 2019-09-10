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
    {vol.Required("task"): "createApplicationInsights"}, extra=vol.ALLOW_EXTRA
)


class CreateApplicationInsights(Step):
    def __init__(self, env: ApplicationVersion, config: dict):
        super().__init__(env, config)

    def schema(self) -> vol.Schema:
        return SCHEMA

    def create_application_insights(self, kind: str, application_type: str) -> ApplicationInsightsComponent:

        # Check some values
        if kind not in {"web", "ios", "other", "store", "java", "phone"}:
            raise ValueError("Unknown application insights kind: {}".format(kind))

        if application_type not in {"web", "other"}:
            raise ValueError("Unknown application insights application_type: {}".format(application_type))

        application_name = ApplicationName().get(self.config)
        client = self.__create_client()

        insight = self.__find(client, application_name)
        if not insight:
            logger.info("Creating new Application Insights...")
            # Create a new Application Insights
            comp = ApplicationInsightsComponent(
                location=self.config["azure"]["location"], kind=kind, application_type=application_type
            )
            insight = client.components.create_or_update(
                get_resource_group_name(self.config, self.env), application_name, comp
            )
        return insight

    def __create_client(self) -> ApplicationInsightsManagementClient:
        azure_user_credentials = ActiveDirectoryUserCredentials(
            vault_name=self.vault_name, vault_client=self.vault_client
        ).credentials(self.config)

        return ApplicationInsightsManagementClient(
            azure_user_credentials,
            SubscriptionId(self.vault_name, self.vault_client).subscription_id(self.config),
        )

    def __find(self, client: ApplicationInsightsManagementClient, name: str):
        for insight in client.components.list():
            if insight.name == name:
                return insight
        return None


class CreateDatabricksApplicationInsights(CreateApplicationInsights):
    def run(self):
        self.create_databricks_application_insights()

    def create_databricks_application_insights(self):
        application_name = ApplicationName().get(self.config)
        insight = self.create_application_insights("other", "other")

        instrumentation_secret = Secret("instrumentation-key", insight.instrumentation_key)

        db = CreateDatabricksSecretFromValue(self.env, self.config)
        db._create_scope(application_name)
        db._add_secrets(application_name, [instrumentation_secret])
