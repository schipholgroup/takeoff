from unittest import mock
import os
import unittest
from sdh_deployment.create_appservice_and_webapp import (
    CreateAppserviceAndWebapp as victim
)
from sdh_deployment.create_appservice_and_webapp import (
    SiteConfig,
    AppService,
    AppServiceSKU,
    WebApp,
    Site,
    RESOURCE_GROUP,
)

VALID_SITE_CONFIG = SiteConfig(
    linux_fx_version=f"DOCKER|my_registry.stuff.com/my-app:latest",
    app_settings=[
        {"name": "DOCKER_ENABLE_CI", "value": True},
        {
            "name": "DOCKER_REGISTRY_SERVER_URL",
            "value": "https://my_registry.stuff.com",
        },
        {"name": "DOCKER_REGISTRY_SERVER_USERNAME", "value": "awesomeperson"},
        {"name": "DOCKER_REGISTRY_SERVER_PASSWORD", "value": "supersecret42"},
        {"name": "WEBSITE_HTTPLOGGING_RETENTION_DAYS", "value": 7},
    ],
)


class TestDeployToDatabricks(unittest.TestCase):
    @mock.patch.dict(
        os.environ,
        {
            "WEBAPP_NAME": "my-app",
            "APPSERVICE_LOCATION": "west europe",
            "BUILD_DEFINITIONNAME": "my-build",
            "DOCKER_REGISTRY_URL": "my_registry.stuff.com",
            "DOCKER_REGISTRY_USERNAME": "awesomeperson",
            "DOCKER_REGISTRY_PASSWORD": "supersecret42",
        },
    )
    def test_get_site_config(self):
        result = victim._get_site_config("my-app")
        assert result == VALID_SITE_CONFIG

    def test_parse_appservice_parameters_defaults(self):
        expected_appservice_config = AppService(
            name="my_epic_app",
            sku=AppServiceSKU(name="S1", capacity=2, tier="Standard"),
        )

        result = victim._parse_appservice_parameters(
            "prd", {"appService": {'name': expected_appservice_config.name}}
        )

        assert expected_appservice_config == result

    def test_parse_appservice_parameters_config_unavailable(self):
        expected_appservice_config = AppService(
            name="my_epic_app",
            sku=AppServiceSKU(name="S1", capacity=2, tier="Standard"),
        )

        result = victim._parse_appservice_parameters(
            "prd", {"appService": {'name': expected_appservice_config.name, 'sku': {'acp': {'name': 'I1', 'capacity': 10, 'tier': 'uber'}}}}
        )

        assert expected_appservice_config == result

    @mock.patch(
        "sdh_deployment.create_appservice_and_webapp.CreateAppserviceAndWebapp._get_site_config"
    )
    @mock.patch.dict(
        os.environ,
        {
            "WEBAPP_NAME": "my-app",
            "APPSERVICE_LOCATION": "west europe",
            "BUILD_DEFINITIONNAME": "my-build",
            "DOCKER_REGISTRY_URL": "https://abc.frl",
            "DOCKER_REGISTRY_USERNAME": "user123",
            "DOCKER_REGISTRY_PASSWORD": "supersecret123",
        },
    )
    def test_get_webapp_to_create(self, get_site_config_mock):
        get_site_config_mock.return_value = VALID_SITE_CONFIG

        expected_result = WebApp(
            resource_group=RESOURCE_GROUP.format(dtap="dev"),
            name="my-build-dev",
            site=Site(
                location="west europe",
                site_config=VALID_SITE_CONFIG,
                server_farm_id="appservice_id",
            ),
        )

        result = victim._get_webapp_to_create("appservice_id", "dev")

        assert result == expected_result

        get_site_config_mock.assert_called_once()
