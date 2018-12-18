import base64
import os
import unittest
from unittest import mock
from unittest.mock import Mock

from runway.ApplicationVersion import ApplicationVersion
from runway.credentials.CosmosCredentials import CosmosCredentials
from runway.create_appservice_and_webapp import (
    CreateAppserviceAndWebapp as victim)
from runway.create_appservice_and_webapp import (
    SiteConfig,
    AppService,
    AppServiceSKU,
    WebApp,
    Site,
    RESOURCE_GROUP,
)
from runway.util import SHARED_REGISTRY

ENV = ApplicationVersion("env", "ver", 'branch')

VALID_SITE_CONFIG = SiteConfig(
    linux_fx_version=f"DOCKER|{SHARED_REGISTRY}/my-app:{ENV.artifact_tag}",
    http_logging_enabled=True,
    always_on=True,
    app_settings=[
        {"name": "DOCKER_ENABLE_CI", "value": "true"},
        {"name": "BUILD_VERSION", "value": ENV.version},
        {"name": "DOCKER_REGISTRY_SERVER_URL", "value": "https://" + SHARED_REGISTRY},
        {"name": "DOCKER_REGISTRY_SERVER_USERNAME", "value": "awesomeperson"},
        {"name": "DOCKER_REGISTRY_SERVER_PASSWORD", "value": "supersecret42"},
        {"name": "WEBSITE_HTTPLOGGING_RETENTION_DAYS", "value": 7},
        {"name": "COSMOS_URI", "value": "https://localhost:443"},
        {"name": "COSMOS_KEY", "value": "secretcosmoskey"},
        {"name": "INSTRUMENTATION_KEY", "value": "secret-insturmentation-key"},
    ],
)


class TestDeployToWebApp(unittest.TestCase):
    @mock.patch(
        "runway.create_application_insights.CreateApplicationInsights.create_application_insights"
    )
    @mock.patch(
        "runway.CosmosCredentials.CosmosCredentials.get_cosmos_read_only_credentials"
    )
    @mock.patch.dict(
        os.environ,
        {
            "APPSERVICE_LOCATION": "west europe",
            "BUILD_DEFINITIONNAME": "my-app",
            "REGISTRY_USERNAME": "awesomeperson",
            "REGISTRY_PASSWORD": "supersecret42",
        },
    )
    def test_build_site_config(
            self, _get_cosmos_credentials_mock, create_application_insights_mock
    ):
        _get_cosmos_credentials_mock.return_value = CosmosCredentials(
            "https://localhost:443", "secretcosmoskey"
        )
        create_application_insights_mock.return_value.instrumentation_key = (
            "secret-insturmentation-key"
        )

        result = victim(ENV, {})._build_site_config({'YEAH': "SCIENCE!"})

        config = VALID_SITE_CONFIG
        config.app_settings = [{'name': 'YEAH', 'value': 'SCIENCE!'}] + config.app_settings

        assert result.app_settings == config.app_settings
        assert result == config

    @mock.patch.dict(os.environ, {"BUILD_DEFINITIONNAME": "my-build"})
    def test_parse_appservice_parameters_defaults(self):
        expected_appservice_config = AppService(
            name="my-build", sku=AppServiceSKU(name="S1", capacity=2, tier="Standard")
        )

        config = {
            'appService': {'sku': {'name': 'S1', 'capacity': 2, 'tier': 'Standard'}}
        }
        result = victim(ENV, config)._parse_appservice_parameters("prd")

        assert expected_appservice_config == result

    @mock.patch.dict(os.environ, {"BUILD_DEFINITIONNAME": "my-build"})
    def test_parse_appservice_parameters_config_unavailable(self):
        expected_appservice_config = AppService(
            name="my-build", sku=AppServiceSKU(name="S1", capacity=2, tier="Standard")
        )

        config = {"appService": {"name": "my-build", "sku": {"acp": {"name": "I1", "capacity": 10, "tier": "uber"}}, }}
        result = victim(ENV, config)._parse_appservice_parameters("prd")

        assert expected_appservice_config == result

    @mock.patch(
        "runway.create_appservice_and_webapp.CreateAppserviceAndWebapp._build_site_config"
    )
    @mock.patch(
        "runway.CosmosCredentials.CosmosCredentials.get_cosmos_read_only_credentials"
    )
    @mock.patch.dict(
        os.environ,
        {
            "APPSERVICE_LOCATION": "west europe",
            "BUILD_DEFINITIONNAME": "my-build",
            "REGISTRY_USERNAME": "user123",
            "REGISTRY_PASSWORD": "supersecret123",
        },
    )
    def test_get_webapp_to_create(
            self, get_cosmos_credentials_mock, get_site_config_mock
    ):
        get_site_config_mock.return_value = VALID_SITE_CONFIG
        get_cosmos_credentials_mock.return_value = CosmosCredentials(
            "https://localhost:443", "secretcosmoskey"
        )

        expected_result = WebApp(
            resource_group=RESOURCE_GROUP.format(dtap=ENV.environment.lower()),
            name="my-build-env",
            site=Site(
                location="west europe",
                site_config=VALID_SITE_CONFIG,
                server_farm_id="appservice_id",
            ),
        )

        mock_web_app = Mock()
        mock_properties = Mock()

        mock_properties.properties = {}
        mock_web_app.web_apps.list_application_settings = Mock(return_value=mock_properties)

        result = victim(ENV, {})._get_webapp_to_create("appservice_id", mock_web_app)

        assert result == expected_result

        get_site_config_mock.assert_called_once()

    @mock.patch.dict(os.environ, {"BUILD_DEFINITIONNAME": "my-build"})
    def test_linux_fx_version_docker(self):
        linux_fx = 'DOCKER|sdhcontainerregistryshared.azurecr.io/my-build:ver'

        config = {}
        assert victim(ENV, config)._get_linux_fx_version() == linux_fx

    @mock.patch.dict(os.environ, {"BUILD_DEFINITIONNAME": "my-build"})
    def test_linux_fx_version_compose(self):
        compose = """version: '3.2'
services:
  app:
    image: {registry}/{application_name}:{tag}{app_postfix}""".format(registry=SHARED_REGISTRY,
                                                                      application_name='my-build',
                                                                      tag='ver',
                                                                      app_postfix='-flask')
        encoded = base64.b64encode(compose.encode()).decode()

        linux_fx = 'COMPOSE|{}'.format(encoded)

        config = {
            'compose': {
                'filename': 'tests/test_docker-compose.yml.j2',
                'variables': {
                    'app_postfix': '-flask'}
            }
        }
        assert victim(ENV, config)._get_linux_fx_version() == linux_fx
