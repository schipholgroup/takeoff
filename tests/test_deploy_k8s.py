import os
import unittest
from unittest import mock

import pytest
from kubernetes.client import CoreV1Api
from kubernetes.client import V1SecretList

from runway.ApplicationVersion import ApplicationVersion
from runway.deploy_to_k8s import DeployToK8s

env_variables = {'AZURE_TENANTID': 'David',
                 'client_id': 'Doctor',
                 'secret': 'Who'}


class TestDeployToK8s(unittest.TestCase):

    def victim(self):
        return DeployToK8s(ApplicationVersion("dev", "v", "branch"), {
            'runway_azure': {'vault_name': 'gringotts'},
            'devops_environment_keys_dev': {'azure_service_principle': {'tenant': "AZURE_TENANTID",
                                                                        'client_id': "AZURE_KEYVAULT_SP_USERNAME_DEV",
                                                                        'secret': "AZURE_KEYVAULT_SP_PASSWORD_DEV"
                                                                        }
                                            }
        })

    @mock.patch.dict(os.environ, env_variables)
    def test_k8s_resource_exists(self):
        haystack = {
            'items': [
                {
                    'metadata': {
                        'name': 'my-needle'
                    }
                }
            ]
        }
        needle = 'my-needle'

        self.assertTrue(self.victim()._find_needle(needle, haystack))

    @mock.patch.dict(os.environ, env_variables)
    def test_k8s_resource_does_not_exist(self):
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

        self.assertFalse(self.victim()._find_needle(needle, haystack))

    @mock.patch.dict(os.environ, env_variables)
    @mock.patch.object(DeployToK8s, "_find_needle", return_value=False)
    def test_create_resource(self, _):
        with mock.patch.object(CoreV1Api, "list_namespaced_secret", return_value=(V1SecretList(items=[]))) as mock_list:
            with mock.patch.object(CoreV1Api, "patch_namespaced_secret", return_value=None) as mock_patch:
                with mock.patch.object(CoreV1Api, "create_namespaced_secret", return_value=None) as mock_create:
                    self.victim()._create_or_patch_resource(
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
    @mock.patch.object(DeployToK8s, "_find_needle", return_value=True)
    def test_patch_resource(self, _):
        with mock.patch.object(CoreV1Api, "list_namespaced_secret", return_value=(V1SecretList(items=[]))) as mock_list:
            with mock.patch.object(CoreV1Api, "patch_namespaced_secret", return_value=None) as mock_patch:
                with mock.patch.object(CoreV1Api, "create_namespaced_secret", return_value=None) as mock_create:
                    self.victim()._create_or_patch_resource(
                        client=CoreV1Api,
                        resource_type="secret",
                        name="some_secret",
                        namespace="some_namespace",
                        resource_config={}
                    )
                    mock_list.assert_called_once_with(namespace="some_namespace")
                    mock_patch.assert_called_once_with(name="some_secret", namespace="some_namespace", body={})
                    mock_create.assert_not_called()
