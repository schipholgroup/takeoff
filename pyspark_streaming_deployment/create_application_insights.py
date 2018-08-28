import logging

from azure.mgmt.applicationinsights import ApplicationInsightsManagementClient
from azure.mgmt.applicationinsights.models import ApplicationInsightsComponent

from pyspark_streaming_deployment.create_databricks_secrets import __create_scope, __add_secrets, Secret
from pyspark_streaming_deployment.util import get_application_name, get_subscription_id, \
    get_databricks_client, get_azure_user_credentials, AZURE_LOCATION

logger = logging.getLogger(__name__)


def __create_client(dtap: str) -> ApplicationInsightsManagementClient:
    return ApplicationInsightsManagementClient(get_azure_user_credentials(dtap), get_subscription_id())


def __find(client: ApplicationInsightsManagementClient, name: str):
    for insight in client.components.list():
        if insight.name == name:
            return insight
    return None


def create_application_insights(dtap: str):
    application_name = get_application_name()
    client = __create_client(dtap)

    insight = __find(client, application_name)
    if not insight:
        logger.info("Creating new Application Insights...")
        # Create a new Application Insights
        comp = ApplicationInsightsComponent(
            location=AZURE_LOCATION,
            kind='other',
            application_type='other'
        )
        insight = client.components.create_or_update(f'sdh{dtap.lower()}', application_name, comp)

    instrumentation_secret = Secret('instrumentation-key', insight.instrumentation_key)

    databricks_client = get_databricks_client(dtap)

    __create_scope(databricks_client, application_name)
    __add_secrets(databricks_client, application_name, [instrumentation_secret])
