import logging

from azure.mgmt.applicationinsights import ApplicationInsightsManagementClient
from azure.mgmt.applicationinsights.models import ApplicationInsightsComponent

from sdh_deployment.create_databricks_secrets import Secret, CreateDatabricksSecrets
from sdh_deployment.util import (
    get_application_name,
    get_subscription_id,
    get_databricks_client,
    get_azure_user_credentials,
    AZURE_LOCATION,
)
from sdh_deployment.run_deployment import ApplicationVersion

logger = logging.getLogger(__name__)


class CreateApplicationInsights:
    @staticmethod
    def __create_client(dtap: str) -> ApplicationInsightsManagementClient:
        return ApplicationInsightsManagementClient(
            get_azure_user_credentials(dtap), get_subscription_id()
        )

    @staticmethod
    def __find(client: ApplicationInsightsManagementClient, name: str):
        for insight in client.components.list():
            if insight.name == name:
                return insight
        return None

    @staticmethod
    def create_application_insights(
        env: ApplicationVersion, kind: str, application_type: str
    ) -> ApplicationInsightsComponent:

        # Check some values
        if kind not in {"web", "ios", "other", "store", "java", "phone"}:
            raise ValueError("Unknown application insights kind: {}".format(kind))

        if application_type not in {"web", "other"}:
            raise ValueError(
                "Unknown application insights application_type: {}".format(
                    application_type
                )
            )

        application_name = get_application_name()
        client = CreateApplicationInsights.__create_client(env.environment)

        insight = CreateApplicationInsights.__find(client, application_name)
        if not insight:
            logger.info("Creating new Application Insights...")
            # Create a new Application Insights
            comp = ApplicationInsightsComponent(
                location=AZURE_LOCATION, kind=kind, application_type=application_type
            )
            insight = client.components.create_or_update(
                f"sdh{env.environment.lower()}", application_name, comp
            )
        return insight

    @staticmethod
    def create_databricks_application_insights(env: ApplicationVersion):
        application_name = get_application_name()
        insight = CreateApplicationInsights.create_application_insights(
            env, "other", "other"
        )

        instrumentation_secret = Secret(
            "instrumentation-key", insight.instrumentation_key
        )

        databricks_client = get_databricks_client(env.environment)

        CreateDatabricksSecrets._create_scope(databricks_client, application_name)
        CreateDatabricksSecrets._add_secrets(
            databricks_client, application_name, [instrumentation_secret]
        )
