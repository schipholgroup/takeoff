from azure.mgmt.web import WebSiteManagementClient
from azure.mgmt.web.models import AppServicePlan, SkuDescription, Site, SiteConfig
from dataclasses import dataclass
import os
from pyspark_streaming_deployment.util import get_subscription_id, get_azure_user_credentials, RESOURCE_GROUP, AZURE_LOCATION, get_application_name


@dataclass
class AppService(object):
    name: str
    sku_name: str
    sku_capacity: int
    sku_tier: str


@dataclass
class WebApp(object):
    resource_group: str
    name: str
    site: Site


def _create_or_update_appservice(web_client: WebSiteManagementClient, dtap: str, service_to_create: AppService) -> str:
    service_plan_async_operation = web_client.app_service_plans.create_or_update(
        RESOURCE_GROUP.format(dtap=dtap.lower()),
        service_to_create.name,
        AppServicePlan(
            app_service_plan_name=service_to_create.name,
            location=AZURE_LOCATION,
            reserved=True,  # This is the way to specify that it's a linux app-service-plan
            sku=SkuDescription(
                name=service_to_create.sku_name,
                capacity=service_to_create.sku_capacity,
                tier=service_to_create.sku_tier
            )
        )
    )
    result = service_plan_async_operation.result()
    return result.id


def _parse_appservice_parameters(dtap: str) -> AppService:
    """
    Parse parameters to use from environment variables. Defaults are provided for all required SKU parameters and
    for the location
    :return: AppService object created based on env parameters
    """
    return AppService(
        name=os.getenv('APPSERVICE_NAME'),
        sku_name=os.getenv('APPSERVICE_SKU_NAME', 'S1' if dtap == 'prd' else 'B1'),
        sku_capacity=os.getenv('APPSERVICE_SKU_CAPACITY', 1),
        sku_tier=os.getenv('APPSERVICE_SKU_TIER', 'Standard' if dtap == 'prd' else 'Basic')
    )


def _get_site_config(build_definition_name: str) -> SiteConfig:
    docker_registry_url = os.environ['DOCKER_REGISTRY_URL']
    docker_registry_username = os.environ['DOCKER_REGISTRY_USERNAME']
    docker_registry_password = os.environ['DOCKER_REGISTRY_PASSWORD']

    return SiteConfig(
        # this syntax seems to be necessary
        linux_fx_version="DOCKER|{registry_url}/{build_definition_name}:latest".format(
            registry_url=docker_registry_url,
            build_definition_name=build_definition_name
        ),
        app_settings=[
            {
                "name": "DOCKER_REGISTRY_SERVER_URL",
                "value": docker_registry_url
            },
            {
                "name": "DOCKER_REGISTRY_SERVER_USERNAME",
                "value": docker_registry_username
            },
            {
                "name": "DOCKER_REGISTRY_SERVER_PASSWORD",
                "value": docker_registry_password
            },
            {
                "name": "WEBSITE_HTTPLOGGING_RETENTION_DAYS",
                "value": os.getenv("WEBAPP_HTTPLOG_RETENTION", 1)
            }]
    )


def _get_webapp_to_create(appservice_id: str, dtap: str) -> WebApp:
    # use build definition name as default web app name
    build_definition_name = get_application_name()
    webapp_name = os.getenv('WEBAPP_NAME', build_definition_name)
    return WebApp(
        resource_group=RESOURCE_GROUP.format(dtap=dtap.lower()),
        name=webapp_name,
        site=Site(
            location=AZURE_LOCATION,
            site_config=_get_site_config(build_definition_name),
            server_farm_id=appservice_id
        )
    )


def _get_appservice(web_client: WebSiteManagementClient, dtap: str) -> str:
    service_to_create = _parse_appservice_parameters(dtap)
    app_service_id = _create_or_update_appservice(web_client, dtap, service_to_create)
    return app_service_id


def _create_or_update_webapp(web_client: WebSiteManagementClient, appservice_id: str, dtap: str):
    webapp_to_create = _get_webapp_to_create(appservice_id, dtap)
    web_client.web_apps.create_or_update(webapp_to_create.resource_group, webapp_to_create.name, webapp_to_create.site)


def _get_website_management_client(dtap) -> WebSiteManagementClient:
    subscription_id = get_subscription_id()
    credentials = get_azure_user_credentials(dtap)

    web_client = WebSiteManagementClient(credentials, subscription_id)
    return web_client


def create_web_app_and_service(_: str, dtap: str):
    formatted_dtap = dtap.lower()
    web_client = _get_website_management_client(formatted_dtap)

    appservice_id = _get_appservice(web_client, formatted_dtap)

    _create_or_update_webapp(web_client, appservice_id, formatted_dtap)
