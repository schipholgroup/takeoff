import base64
import os
import unittest
from unittest import mock
from unittest.mock import Mock

import yaml

from runway.ApplicationVersion import ApplicationVersion
from runway.create_appservice_and_webapp import (
    CreateAppserviceAndWebapp as victim)
from runway.create_appservice_and_webapp import (
    SiteConfig,
    AppService,
    AppServiceSKU,
    WebApp,
    Site
)
from runway.credentials.cosmos import CosmosCredentials

ENV = ApplicationVersion("env", "ver", 'branch')

VALID_SITE_CONFIG = SiteConfig(
    linux_fx_version=f"DOCKER|some-registry/my-app:{ENV.artifact_tag}",
    http_logging_enabled=True,
    always_on=True,
    app_settings=[
        {"name": "DOCKER_ENABLE_CI", "value": "true"},
        {"name": "BUILD_VERSION", "value": ENV.version},
        {"name": "DOCKER_REGISTRY_SERVER_URL", "value": "https://" + 'some-registry'},
        {"name": "DOCKER_REGISTRY_SERVER_USERNAME", "value": "awesomeperson"},
        {"name": "DOCKER_REGISTRY_SERVER_PASSWORD", "value": "supersecret42"},
        {"name": "WEBSITE_HTTPLOGGING_RETENTION_DAYS", "value": 7},
        {"name": "COSMOS_URI", "value": "https://localhost:443"},
        {"name": "COSMOS_KEY", "value": "secretcosmoskey"},
        {"name": "INSTRUMENTATION_KEY", "value": "secret-insturmentation-key"},
    ],
)

with open('tests/test_runway_config.yaml', 'r') as f:
    runway_config = yaml.safe_load(f.read())


class TestDeployToWebApp(unittest.TestCase):
    @mock.patch("runway.create_application_insights.CreateApplicationInsights.create_application_insights")
    @mock.patch("runway.credentials.cosmos.Cosmos.get_cosmos_read_only_credentials")
    @mock.patch.dict(
        os.environ,
        {
            "APPSERVICE_LOCATION": "west europe",
            "CI_PROJECT_NAME": "my-app",
            "REGISTRY_USERNAME": "awesomeperson",
            "REGISTRY_PASSWORD": "supersecret42",
        },
    )
    @mock.patch("runway.DeploymentStep.AzureKeyvaultClient.vault_and_client", return_value=(None, None))
    def test_build_site_config(
            self, _, _get_cosmos_credentials_mock, create_application_insights_mock
    ):
        _get_cosmos_credentials_mock.return_value = CosmosCredentials(
            "https://localhost:443", "secretcosmoskey"
        )
        create_application_insights_mock.return_value.instrumentation_key = (
            "secret-insturmentation-key"
        )

        result = victim(ENV, runway_config)._build_site_config({'YEAH': "SCIENCE!"})

        config = VALID_SITE_CONFIG
        config.app_settings = [{'name': 'YEAH', 'value': 'SCIENCE!'}] + config.app_settings

        assert result.app_settings == config.app_settings
        assert result == config

    @mock.patch.dict(os.environ, {"CI_PROJECT_NAME": "my-build"})
    @mock.patch("runway.DeploymentStep.AzureKeyvaultClient.vault_and_client", return_value=(None, None))
    def test_parse_appservice_parameters_defaults(self, _):
        expected_appservice_config = AppService(
            name="my-build", sku=AppServiceSKU(name="S1", capacity=2, tier="Standard")
        )

        config = {
            'appService': {'sku': {'name': 'S1', 'capacity': 2, 'tier': 'Standard'}}
        }
        config.update(runway_config)
        result = victim(ENV, config)._parse_appservice_parameters("prd")

        assert expected_appservice_config == result

    @mock.patch("runway.DeploymentStep.AzureKeyvaultClient.vault_and_client", return_value=(None, None))
    @mock.patch.dict(os.environ, {"CI_PROJECT_NAME": "my-build"})
    def test_parse_appservice_parameters_config_unavailable(self, _):
        expected_appservice_config = AppService(
            name="my-build", sku=AppServiceSKU(name="S1", capacity=2, tier="Standard")
        )

        config = {"appService": {"name": "my-build", "sku": {"acp": {"name": "I1", "capacity": 10, "tier": "uber"}}, }}
        config.update(runway_config)
        result = victim(ENV, config)._parse_appservice_parameters("prd")

        assert expected_appservice_config == result

    @mock.patch(
        "runway.create_appservice_and_webapp.CreateAppserviceAndWebapp._build_site_config"
    )
    @mock.patch(
        "runway.credentials.cosmos.Cosmos.get_cosmos_read_only_credentials"
    )
    @mock.patch.dict(
        os.environ,
        {
            "APPSERVICE_LOCATION": "west europe",
            "CI_PROJECT_NAME": "my-build",
            "REGISTRY_USERNAME": "user123",
            "REGISTRY_PASSWORD": "supersecret123",
        },
    )

    @mock.patch("runway.DeploymentStep.AzureKeyvaultClient.vault_and_client", return_value=(None, None))
    def test_get_webapp_to_create(
            self, _, get_cosmos_credentials_mock, get_site_config_mock
    ):
        get_site_config_mock.return_value = VALID_SITE_CONFIG
        get_cosmos_credentials_mock.return_value = CosmosCredentials(
            "https://localhost:443", "secretcosmoskey"
        )

        expected_result = WebApp(
            resource_group='sdh{dtap}'.format(dtap=ENV.environment.lower()),
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

        result = victim(ENV, runway_config)._get_webapp_to_create("appservice_id", mock_web_app)

        assert result == expected_result

        get_site_config_mock.assert_called_once()

    @mock.patch.dict(os.environ, {"CI_PROJECT_NAME": "my-build"})
    @mock.patch("runway.DeploymentStep.AzureKeyvaultClient.vault_and_client", return_value=(None, None))
    def test_linux_fx_version_docker(self, _):
        linux_fx = 'DOCKER|some-registry/my-build:ver'

        assert victim(ENV, runway_config)._get_linux_fx_version() == linux_fx

    @mock.patch.dict(os.environ, {"CI_PROJECT_NAME": "my-build"})
    @mock.patch("runway.DeploymentStep.AzureKeyvaultClient.vault_and_client", return_value=(None, None))
    def test_linux_fx_version_compose(self, _):
        compose = """version: '3.2'
services:
  app:
    image: {registry}/{application_name}:{tag}{app_postfix}""".format(registry='some-registry',
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
        config.update(runway_config)
        assert victim(ENV, config)._get_linux_fx_version() == linux_fx
