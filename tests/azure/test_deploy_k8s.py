import os
from unittest import mock

import pytest
import voluptuous as vol
from kubernetes.client import CoreV1Api
from kubernetes.client import V1SecretList

from runway.ApplicationVersion import ApplicationVersion
from runway.azure.deploy_to_k8s import DeployToK8s
from tests.azure import runway_config

env_variables = {'AZURE_TENANTID': 'David',
                 'AZURE_KEYVAULT_SP_USERNAME_DEV': 'Doctor',
                 'AZURE_KEYVAULT_SP_PASSWORD_DEV': 'Who'}

BASE_CONF = {'task': 'deployToK8s'}


class TestDeployToK8s(object):

    @mock.patch("runway.DeploymentStep.KeyvaultClient.vault_and_client", return_value=(None, None))
    def test_validate_minimal_schema(self, _):
        conf = {**runway_config(), **BASE_CONF}

        res = DeployToK8s(ApplicationVersion("dev", "v", "branch"), conf)
        res.config['deployment_config_path'] = "k8s_config/deployment.yaml.j2"
        res.config["service_config_path"] = "k8s_config/service.yaml.j2"
        res.config['service'] = []

    @mock.patch("runway.DeploymentStep.KeyvaultClient.vault_and_client", return_value=(None, None))
    def test_validate_schema_invalid_ip(self, _):
        conf = {**runway_config(), **BASE_CONF, "service_ips": {"dev": "Dave"}}

        with pytest.raises(vol.MultipleInvalid):
            DeployToK8s(ApplicationVersion("dev", "v", "branch"), conf)

    @mock.patch("runway.DeploymentStep.KeyvaultClient.vault_and_client", return_value=(None, None))
    def test_k8s_resource_exists(self, _):
        haystack = {
            'items': [
                {
                    'metadata': {
                        'name': 'my-needle'
                    }
                }
            ]
        }

        config = {**runway_config(),
                  **BASE_CONF}
        victim = DeployToK8s(ApplicationVersion("dev", "v", "branch"), config)
        assert victim._find_needle('my-needle', haystack)

    @mock.patch("runway.DeploymentStep.KeyvaultClient.vault_and_client", return_value=(None, None))
    @mock.patch.dict(os.environ, env_variables)
    def test_k8s_resource_does_not_exist(self, _):
        haystack = {
            'items': [
                {
                    'metadata': {
                        'name': 'my-needle'
                    }
                }
            ]
        }
        needle = 'my-unfindable-needle'

        config = {**runway_config(),
                  **BASE_CONF}
        victim = DeployToK8s(ApplicationVersion("dev", "v", "branch"), config)
        assert not victim._find_needle(needle, haystack)

    @mock.patch.dict(os.environ, env_variables)
    @mock.patch("runway.DeploymentStep.KeyvaultClient.vault_and_client", return_value=(None, None))
    @mock.patch.object(DeployToK8s, "_find_needle", return_value=False)
    def test_create_resource(self, _, __):
        config = {**runway_config(),
                  **BASE_CONF}
        victim = DeployToK8s(ApplicationVersion("dev", "v", "branch"), config)
        with mock.patch.object(CoreV1Api, "list_namespaced_secret", return_value=(V1SecretList(items=[]))) as mock_list:
            with mock.patch.object(CoreV1Api, "patch_namespaced_secret", return_value=None) as mock_patch:
                with mock.patch.object(CoreV1Api, "create_namespaced_secret", return_value=None) as mock_create:
                    victim._create_or_patch_resource(
                        client=CoreV1Api,
                        resource_type="secret",
                        name="some_secret",
                        namespace="some_namespace",
                        resource_config={}
                    )
                    mock_list.assert_called_once_with(namespace="some_namespace")
                    mock_create.assert_called_once_with(namespace="some_namespace", body={})
                    mock_patch.assert_not_called()

    @mock.patch.dict(os.environ, env_variables)
    @mock.patch("runway.DeploymentStep.KeyvaultClient.vault_and_client", return_value=(None, None))
    @mock.patch.object(DeployToK8s, "_find_needle", return_value=True)
    def test_patch_resource(self, _, __):
        config = {**runway_config(),
                  **BASE_CONF}
        victim = DeployToK8s(ApplicationVersion("dev", "v", "branch"), config)
        with mock.patch.object(CoreV1Api, "list_namespaced_secret", return_value=(V1SecretList(items=[]))) as mock_list:
            with mock.patch.object(CoreV1Api, "patch_namespaced_secret", return_value=None) as mock_patch:
                with mock.patch.object(CoreV1Api, "create_namespaced_secret", return_value=None) as mock_create:
                    victim._create_or_patch_resource(
                        client=CoreV1Api,
                        resource_type="secret",
                        name="some_secret",
                        namespace="some_namespace",
                        resource_config={}
                    )
                    mock_list.assert_called_once_with(namespace="some_namespace")
                    mock_patch.assert_called_once_with(name="some_secret", namespace="some_namespace", body={})
                    mock_create.assert_not_called()
