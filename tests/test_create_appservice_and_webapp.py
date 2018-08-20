from unittest import mock
import os
from pyspark_streaming_deployment import create_appservice_and_webapp as victim
from pyspark_streaming_deployment.create_appservice_and_webapp import SiteConfig, AppService, WebApp, Site, RESOURCE_GROUP


VALID_SITE_CONFIG = SiteConfig(
    linux_fx_version=f"DOCKER|https://my_registry.stuff.com/my-app:latest",
    app_settings=[
        {
            "name": "DOCKER_REGISTRY_SERVER_URL",
            "value": "https://my_registry.stuff.com"
        },
        {
            "name": "DOCKER_REGISTRY_SERVER_USERNAME",
            "value": "awesomeperson"
        },
        {
            "name": "DOCKER_REGISTRY_SERVER_PASSWORD",
            "value": "supersecret42"
        },
        {
            "name": "WEBSITE_HTTPLOGGING_RETENTION_DAYS",
            "value": 1
        }
    ]
)


@mock.patch.dict(os.environ, {'DOCKER_REGISTRY_URL': 'https://my_registry.stuff.com',
                              'DOCKER_REGISTRY_USERNAME': 'awesomeperson',
                              'DOCKER_REGISTRY_PASSWORD': 'supersecret42'})
def test_get_site_config():
    result = victim._get_site_config('my-app')

    assert result == VALID_SITE_CONFIG


@mock.patch.dict(os.environ, {'APPSERVICE_NAME': 'my_epic_app'})
def test_parse_appservice_parameters():
    expected_appservice_config = AppService(
        name="my_epic_app",
        sku_name="S1",
        sku_capacity=1,
        sku_tier="Standard"
    )

    result = victim._parse_appservice_parameters('prd')

    assert expected_appservice_config == result


@mock.patch('pyspark_streaming_deployment.create_appservice_and_webapp._get_site_config')
@mock.patch.dict(os.environ, {'WEBAPP_NAME': 'my-app', 'APPSERVICE_LOCATION': 'west europe', 'BUILD_DEFINITIONNAME': 'my-build'})
def test_get_webapp_to_create(get_site_config_mock):
    get_site_config_mock.return_value = VALID_SITE_CONFIG

    expected_result = WebApp(
        resource_group=RESOURCE_GROUP.format(dtap='dev'),
        name='my-app',
        site=Site(
            location='west europe',
            site_config=VALID_SITE_CONFIG,
            server_farm_id='appservice_id'
        )
    )

    result = victim._get_webapp_to_create('appservice_id', 'dev')

    assert result == expected_result

    get_site_config_mock.assert_called_once()
