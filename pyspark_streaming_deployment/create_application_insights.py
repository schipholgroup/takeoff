from azure.applicationinsights import ApplicationInsightsManagementClient
from azure.mgmt.applicationinsights.models import ApplicationInsightsComponent

from pyspark_streaming_deployment.create_databricks_secrets import __create_scope, __add_secrets, Secret
from pyspark_streaming_deployment.util import get_application_name, get_branch, get_tag, get_subscription_id, \
    get_databricks_client, get_azure_credentials


def main():
    branch = get_branch()
    tag = get_tag()

    if tag:
        create_application_insights(dtap='PRD')
    else:
        if branch == 'master':
            create_application_insights(dtap='DEV')
        else:
            print(f'''Not a release (tag not available),
            nor master branch (branch = "{branch}". Not deploying''')


def __create_client(dtap: str) -> ApplicationInsightsManagementClient:
    return ApplicationInsightsManagementClient(get_azure_credentials(dtap), get_subscription_id())


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
        # Create a new Application Insights
        comp = ApplicationInsightsComponent(
            location='West Europe',
            kind='other',
            application_type='other'
        )
        insight = client.components.create_or_update(f'sdh{dtap}', application_name, comp)

    instrumentation_secret = Secret('instrumentation-key', insight.instrumentation_key)

    databricks_client = get_databricks_client(dtap)

    __create_scope(databricks_client, application_name)
    __add_secrets(databricks_client, application_name, [instrumentation_secret])


main()
