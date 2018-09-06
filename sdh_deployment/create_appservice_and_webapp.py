from azure.mgmt.web import WebSiteManagementClient
import os
from azure.mgmt.web.models import AppServicePlan, SkuDescription, Site, SiteConfig
from dataclasses import dataclass
from sdh_deployment.util import (
    get_subscription_id,
    get_azure_user_credentials,
    RESOURCE_GROUP,
    AZURE_LOCATION,
    get_application_name,
    SHARED_REGISTRY,
)
from sdh_deployment.run_deployment import ApplicationVersion


@dataclass(frozen=True)
class AppServiceSKU(object):
    name: str
    capacity: int
    tier: str


appservice_sku_defaults = {
    "prd": AppServiceSKU(name="S1", capacity=2, tier="Standard"),
    "acp": AppServiceSKU(name="S1", capacity=1, tier="Standard"),
    "dev": AppServiceSKU(name="B1", capacity=1, tier="Basic"),
}


@dataclass(frozen=True)
class AppService(object):
    name: str
    sku: AppServiceSKU


@dataclass(frozen=True)
class WebApp(object):
    resource_group: str
    name: str
    site: Site


class CreateAppserviceAndWebapp:
    @staticmethod
    def _create_or_update_appservice(
        web_client: WebSiteManagementClient, dtap: str, service_to_create: AppService) -> str:
        service_plan_async_operation = web_client.app_service_plans.create_or_update(
            RESOURCE_GROUP.format(dtap=dtap.lower()),
            service_to_create.name,
            AppServicePlan(
                app_service_plan_name=service_to_create.name,
                location=AZURE_LOCATION,
                reserved=True,  # This is the way to specify that it's a linux app-service-plan
                sku=SkuDescription(
                    name=service_to_create.sku.name,
                    capacity=service_to_create.sku.capacity,
                    tier=service_to_create.sku.tier,
                ),
            ),
        )
        result = service_plan_async_operation.result()
        return result.id

    @staticmethod
    def _parse_appservice_parameters(dtap: str, config: dict) -> AppService:
        """
        Parse parameters to use from environment variables. Defaults are provided for all required SKU parameters and
        for the location
        :return: AppService object created based on env parameters
        """
        provided_config = config.get('appService')

        # check if there is any config available for sku for this environment.
        if 'sku' in provided_config and dtap in provided_config['sku']:
            config = provided_config.get('sku').get(dtap)
            sku_config = AppServiceSKU(config.get('name'), config.get('capacity'), config.get('tier'))
        else:
            sku_config = appservice_sku_defaults[dtap]

        return AppService(
            name=get_application_name(),
            sku=AppServiceSKU(
                name=sku_config.name,
                capacity=sku_config.capacity,
                tier=sku_config.tier,
            ),
        )

    @staticmethod
    def _get_site_config(build_definition_name: str, env: ApplicationVersion) -> SiteConfig:
        docker_registry_username = os.environ["REGISTRY_USERNAME"]
        docker_registry_password = os.environ["REGISTRY_PASSWORD"]
        return SiteConfig(
            # this syntax seems to be necessary
            linux_fx_version="DOCKER|{registry_url}/{build_definition_name}:{tag}".format(
                registry_url=SHARED_REGISTRY,
                build_definition_name=build_definition_name,
                tag=env.version
            ),
            app_settings=[
                {
                    "name": "DOCKER_ENABLE_CI",  # we always want this to be enabled
                    "value": True,
                },
                {
                    "name": "DOCKER_REGISTRY_SERVER_URL",
                    # This MUST start with https://
                    "value": "https://" + SHARED_REGISTRY,
                },
                {
                    "name": "DOCKER_REGISTRY_SERVER_USERNAME",
                    "value": docker_registry_username,
                },
                {
                    "name": "DOCKER_REGISTRY_SERVER_PASSWORD",
                    "value": docker_registry_password,
                },
                {"name": "WEBSITE_HTTPLOGGING_RETENTION_DAYS", "value": 7},
            ],
        )

    @staticmethod
    def _get_webapp_to_create(appservice_id: str, dtap: str, env: ApplicationVersion) -> WebApp:
        # use build definition name as default web app name
        application_name = get_application_name()
        webapp_name = "{name}-{env}".format(
            name=application_name.lower(), env=dtap.lower()
        )
        return WebApp(
            resource_group=RESOURCE_GROUP.format(dtap=dtap.lower()),
            name=webapp_name,
            site=Site(
                location=AZURE_LOCATION,
                site_config=CreateAppserviceAndWebapp._get_site_config(
                    application_name, env
                ),
                server_farm_id=appservice_id,
            ),
        )

    @staticmethod
    def _get_appservice(
        web_client: WebSiteManagementClient, dtap: str, config: dict) -> str:
        service_to_create = CreateAppserviceAndWebapp._parse_appservice_parameters(
            dtap, config
        )
        app_service_id = CreateAppserviceAndWebapp._create_or_update_appservice(
            web_client, dtap, service_to_create
        )
        return app_service_id

    @staticmethod
    def _create_or_update_webapp(web_client: WebSiteManagementClient,
                                 appservice_id: str,
                                 dtap: str,
                                 env: ApplicationVersion) -> Site:
        webapp_to_create = CreateAppserviceAndWebapp._get_webapp_to_create(
            appservice_id, dtap, env
        )
        return web_client.web_apps.create_or_update(
            webapp_to_create.resource_group,
            webapp_to_create.name,
            webapp_to_create.site,
        )

    @staticmethod
    def _get_website_management_client(dtap) -> WebSiteManagementClient:
        subscription_id = get_subscription_id()
        credentials = get_azure_user_credentials(dtap)

        web_client = WebSiteManagementClient(credentials, subscription_id)
        return web_client

    @staticmethod
    def create_appservice_and_webapp(env: ApplicationVersion, config: dict) -> Site:
        formatted_dtap = env.environment.lower()
        web_client = CreateAppserviceAndWebapp._get_website_management_client(
            formatted_dtap
        )

        appservice_id = CreateAppserviceAndWebapp._get_appservice(
            web_client, formatted_dtap, config
        )

        return CreateAppserviceAndWebapp._create_or_update_webapp(
            web_client, appservice_id, formatted_dtap, env
        )
