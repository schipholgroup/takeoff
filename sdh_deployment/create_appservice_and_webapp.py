import base64
import logging
import os
import sys
from dataclasses import dataclass

from azure.mgmt.web import WebSiteManagementClient
from azure.mgmt.web.models import AppServicePlan, SkuDescription, Site, SiteConfig
from msrestazure.azure_exceptions import CloudError

from sdh_deployment.ApplicationVersion import ApplicationVersion
from sdh_deployment.DeploymentStep import DeploymentStep
from sdh_deployment.create_application_insights import CreateApplicationInsights
from sdh_deployment.util import (
    get_subscription_id,
    get_azure_user_credentials,
    RESOURCE_GROUP,
    AZURE_LOCATION,
    get_application_name,
    SHARED_REGISTRY,
    render_string_with_jinja, get_cosmos_read_only_credentials)

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

logger = logging.getLogger(__name__)


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


class CreateAppserviceAndWebapp(DeploymentStep):
    def __init__(self, env: ApplicationVersion, config: dict):
        super().__init__(env, config)

    def run(self):
        self.create_appservice_and_webapp()

    def _create_or_update_appservice(self,
                                     web_client: WebSiteManagementClient,
                                     dtap: str,
                                     service_to_create: AppService) -> str:
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

    def _parse_appservice_parameters(self, dtap: str) -> AppService:
        """
        Parse parameters to use from environment variables. Defaults are provided for all required SKU parameters and
        for the location
        :return: AppService object created based on env parameters
        """
        provided_config = self.config.get("appService")

        # check if there is any config available for sku for this environment.
        if "sku" in provided_config and dtap in provided_config["sku"]:
            config = provided_config.get("sku").get(dtap)
            sku_config = AppServiceSKU(
                config.get("name"), config.get("capacity"), config.get("tier")
            )
        else:
            sku_config = appservice_sku_defaults[dtap]

        return AppService(
            name=get_application_name(),
            sku=AppServiceSKU(
                name=sku_config.name, capacity=sku_config.capacity, tier=sku_config.tier
            ),
        )

    def _get_linux_fx_version(self):
        if 'compose' in self.config:
            compose_config = self.config.get("compose")
            tag_config = compose_config.get("variables")
            tag_config.update({
                'registry': SHARED_REGISTRY,
                'application_name': get_application_name(),
                'tag': self.env.docker_tag
            })

            rendered_compose = render_string_with_jinja(compose_config['filename'], tag_config)
            return "COMPOSE|{compose}".format(compose=base64.b64encode(rendered_compose.encode()).decode())
        else:
            return "DOCKER|{registry_url}/{build_definition_name}:{tag}".format(
                registry_url=SHARED_REGISTRY,
                build_definition_name=get_application_name(),
                tag=self.env.docker_tag,
            )

    def _build_site_config(self, existing_properties: dict) -> SiteConfig:
        docker_registry_username = os.environ["REGISTRY_USERNAME"]
        docker_registry_password = os.environ["REGISTRY_PASSWORD"]

        cosmos_credentials = get_cosmos_read_only_credentials(self.env.environment.lower())
        application_insights = CreateApplicationInsights(self.env, {}).create_application_insights("web", "web")
        new_properties = {
            'DOCKER_ENABLE_CI': 'true',
            'BUILD_VERSION': self.env.version,
            'DOCKER_REGISTRY_SERVER_URL': "https://" + SHARED_REGISTRY,
            'DOCKER_REGISTRY_SERVER_USERNAME': docker_registry_username,
            "DOCKER_REGISTRY_SERVER_PASSWORD": docker_registry_password,
            "WEBSITE_HTTPLOGGING_RETENTION_DAYS": 7,
            "COSMOS_URI": cosmos_credentials.uri,
            "COSMOS_KEY": cosmos_credentials.key,
            "INSTRUMENTATION_KEY": application_insights.instrumentation_key
        }
        # This should make sure that properties set by other parties and other deployment scripts will not be removed
        # as this is the default Azure behaviour
        existing_properties.update(new_properties)

        def as_list(d: dict):
            return [{'name': k, 'value': v} for k, v in d.items()]

        return SiteConfig(
            linux_fx_version=self._get_linux_fx_version(),
            http_logging_enabled=True,
            always_on=True,
            app_settings=as_list(existing_properties)
        )

    def _get_webapp_to_create(self,
                              appservice_id: str,
                              web_client: WebSiteManagementClient) -> WebApp:
        # use build definition name as default web app name
        application_name = get_application_name()
        formatted_dtap = self.env.environment.lower()

        webapp_name = "{name}-{env}".format(
            name=application_name.lower(),
            env=formatted_dtap
        )

        existing_properties = {}
        try:
            existing_properties = web_client.web_apps.list_application_settings(formatted_dtap,
                                                                                webapp_name).properties
        except CloudError:
            logging.warning(f"{webapp_name} could not be found, skipping existing properties")

        return WebApp(
            resource_group=RESOURCE_GROUP.format(dtap=formatted_dtap),
            name=webapp_name,
            site=Site(
                location=AZURE_LOCATION,
                site_config=self._build_site_config(existing_properties=existing_properties),
                server_farm_id=appservice_id,
            ),
        )

    def _get_appservice(self,
                        web_client: WebSiteManagementClient,
                        dtap: str) -> str:
        service_to_create = self._parse_appservice_parameters(dtap)
        app_service_id = self._create_or_update_appservice(web_client, dtap, service_to_create)
        return app_service_id

    def _create_or_update_webapp(
            self,
            web_client: WebSiteManagementClient,
            webapp_to_create: WebApp) -> Site:

        return web_client.web_apps.create_or_update(
            webapp_to_create.resource_group,
            webapp_to_create.name,
            webapp_to_create.site,
        )

    def _get_website_management_client(self, dtap) -> WebSiteManagementClient:
        subscription_id = get_subscription_id()
        credentials = get_azure_user_credentials(dtap)

        return WebSiteManagementClient(credentials, subscription_id)

    def create_appservice_and_webapp(self) -> Site:
        formatted_dtap = self.env.environment.lower()

        web_client = self._get_website_management_client(
            dtap=formatted_dtap)

        appservice_id = self._get_appservice(
            web_client=web_client,
            dtap=formatted_dtap)

        webapp_to_create = self._get_webapp_to_create(
            appservice_id=appservice_id,
            web_client=web_client)

        site = self._create_or_update_webapp(
            web_client=web_client,
            webapp_to_create=webapp_to_create)

        # DOCKER_CI_ENABLE is kinda buggy and not documented, this assures the app is restarted for
        # sure when the deployment updates
        web_client.web_apps.restart(
            resource_group_name=(RESOURCE_GROUP.format(dtap=formatted_dtap)),
            name=webapp_to_create.name)

        return site
