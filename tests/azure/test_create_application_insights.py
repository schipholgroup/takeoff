import mock
import os
import pytest

from dataclasses import dataclass
from voluptuous import MultipleInvalid

from takeoff.application_version import ApplicationVersion
from takeoff.azure.create_application_insights import CreateApplicationInsights
from takeoff.credentials.Secret import Secret
from tests.azure import takeoff_config

BASE_CONF = {'task': 'createApplicationInsights',
             'applicationType': 'other',
             'kind': 'other'
             }

TEST_ENV_VARS = {'AZURE_TENANTID': 'David',
                 'AZURE_KEYVAULT_SP_USERNAME_DEV': 'Doctor',
                 'AZURE_KEYVAULT_SP_PASSWORD_DEV': 'Who',
                 'CI_PROJECT_NAME': 'my_little_pony',
                 'CI_COMMIT_REF_SLUG': 'my-little-pony'}


@dataclass
class MockApplicationInsights:
    name: str
    instrumentation_key: str = "great_key"


@pytest.fixture(autouse=True)
@mock.patch.dict(os.environ, TEST_ENV_VARS)
def victim():
    conf = {**takeoff_config(), **BASE_CONF}

    with mock.patch("takeoff.step.KeyVaultClient.vault_and_client", return_value=(None, None)):
        return CreateApplicationInsights(ApplicationVersion("dev", "0.0.0", "my-branch"), conf)


class TestCreateApplicationInsights(object):
    @mock.patch("takeoff.step.KeyVaultClient.vault_and_client", return_value=(None, None))
    def test_validate_minimal_schema(self, _):
        conf = {**takeoff_config(), **BASE_CONF}

        CreateApplicationInsights(ApplicationVersion("dev", "v", "branch"), conf)

    # @mock.patch("takeoff.step.KeyVaultClient.vault_and_client", return_value=(None, None))
    def test_validate_invalid_schema(self):
        INVALID_CONF = {
             'task': 'createApplicationInsights',
             'applicationType': 'invalid',
             'kind': 'invalid'
        }
        conf = {**takeoff_config(), **INVALID_CONF}
        with pytest.raises(MultipleInvalid):
            CreateApplicationInsights(ApplicationVersion("dev", "v", "branch"), conf)

    @mock.patch.dict(os.environ, TEST_ENV_VARS)
    @mock.patch("takeoff.azure.create_application_insights.CreateApplicationInsights._create_client")
    @mock.patch("takeoff.azure.create_application_insights.CreateApplicationInsights._find_existing_instance")
    def test_application_insight_existing(self, _, __, victim):
        with mock.patch("takeoff.azure.create_application_insights.ApplicationInsightsComponent") as m_app_insights_component:
            victim.create_application_insights()

        m_app_insights_component.assert_not_called()

    @mock.patch.dict(os.environ, TEST_ENV_VARS)
    @mock.patch("takeoff.azure.create_application_insights.CreateApplicationInsights._find_existing_instance", return_value=None)
    def test_application_insights_non_existing(self, _, victim):
        m_client = mock.MagicMock()
        m_client.components.create_or_update.return_value = []

        with mock.patch("takeoff.azure.create_application_insights.CreateApplicationInsights._create_client", return_value=m_client):
            with mock.patch("takeoff.azure.create_application_insights.ApplicationInsightsComponent") as m_app_insights_component:
                victim.create_application_insights()

        m_app_insights_component.assert_called_once_with(application_type='other', kind='other', location='west europe')

    @mock.patch.dict(os.environ, TEST_ENV_VARS)
    @mock.patch("takeoff.step.KeyVaultClient.vault_and_client", return_value=(None, None))
    @mock.patch("takeoff.azure.create_application_insights.CreateApplicationInsights._find_existing_instance", return_value=None)
    def test_application_insights_with_databricks_secret(self, _, __):
        conf = {**takeoff_config(), **BASE_CONF, 'createDatabricksSecret': True}
        target = CreateApplicationInsights(ApplicationVersion("dev", "0.0.0", "my-branch"), conf)

        m_client = mock.MagicMock()
        m_client.components.create_or_update.return_value = MockApplicationInsights("something", "my-key")

        with mock.patch("takeoff.azure.create_application_insights.CreateApplicationInsights._create_client", return_value=m_client):
            with mock.patch("takeoff.azure.create_application_insights.ApplicationInsightsComponent") as m_app_insights_component:
                with mock.patch("takeoff.azure.create_application_insights.CreateApplicationInsights.create_databricks_secret") as m_create_databricks_secret:
                    target.create_application_insights()

        m_app_insights_component.assert_called_once_with(application_type='other', kind='other', location='west europe')

        m_create_databricks_secret.assert_called_once_with('my_little_pony', Secret("instrumentation-key", "my-key"))

    def test_find_existing_instance_found(self, victim):
        m_client = mock.MagicMock()
        m_client.components.list.return_value = [MockApplicationInsights("insights1"),
                                                 MockApplicationInsights("insights2")]

        result = victim._find_existing_instance(m_client, "insights1")

        assert result == MockApplicationInsights("insights1")

    def test_find_non_existing_instance_not_found(self, victim):
        m_client = mock.MagicMock()
        m_client.components.list.return_value = []

        result = victim._find_existing_instance(m_client, "insights1")

        assert result is None

