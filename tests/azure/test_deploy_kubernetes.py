import os
from dataclasses import dataclass
from typing import List
from unittest import mock

import pytest

from takeoff.application_version import ApplicationVersion
from takeoff.azure.credentials.container_registry import DockerCredentials
from takeoff.azure.deploy_to_kubernetes import DeployToKubernetes, BaseKubernetes
from takeoff.context import Context
from takeoff.util import run_shell_command
from tests.azure import takeoff_config

env_variables = {'AZURE_TENANTID': 'David',
                 'AZURE_KEYVAULT_SP_USERNAME_DEV': 'Doctor',
                 'AZURE_KEYVAULT_SP_PASSWORD_DEV': 'Who',
                 'CI_PROJECT_NAME': 'my_little_pony',
                 'CI_COMMIT_REF_SLUG': 'my-little-pony'}


@dataclass
class KubernetesResponse:
    namespace: str

    def to_dict(self):
        return {
            "items": [
                {
                    "metadata": {
                        "name": "something"
                    }
                }
            ]
        }


@dataclass
class RegistryCredentials:
    registry: str
    username: str
    password: str

    def credentials(self, config):
        return self


BASE_CONF = {'task': 'deploy_to_kubernetes', 'kubernetes_config_path': 'kubernetes_config/k8s.yml.j2'}


@pytest.fixture(scope="session")
def victim():
    with mock.patch.dict(os.environ, env_variables) and \
         mock.patch("takeoff.step.KeyVaultClient.vault_and_client", return_value=(None, None)):
        conf = {**takeoff_config(), **BASE_CONF}
        conf['azure'].update({"kubernetes_naming": "kubernetes{env}"})
        return DeployToKubernetes(ApplicationVersion("dev", "v", "branch"), conf)


class TestDeployToKubernetes(object):
    @mock.patch("takeoff.step.KeyVaultClient.vault_and_client", return_value=(None, None))
    def test_validate_minimal_schema(self, _):
        conf = {**takeoff_config(), **BASE_CONF}
        conf['azure'].update({"kubernetes_naming": "kubernetes{env}"})

        res = DeployToKubernetes(ApplicationVersion("dev", "v", "branch"), conf)
        assert res.config['kubernetes_config_path'] == "kubernetes_config/k8s.yml.j2"

    @mock.patch.dict(os.environ, env_variables)
    @mock.patch("takeoff.azure.deploy_to_kubernetes.DeployToKubernetes._get_docker_registry_secret", return_value="somebase64encodedstring")
    def test_create_docker_registry_secret(self, _, victim):
        Context().clear()
        with mock.patch("takeoff.azure.deploy_to_kubernetes.DeployToKubernetes._write_kubernetes_config") as m_write:
            victim._create_image_pull_secret("myapp")

        expected_result = """kind: Namespace
apiVersion: v1
metadata:
  name: default
---
kind: Secret
apiVersion: v1
type: kubernetes.io/dockerconfigjson
data:
  .dockerconfigjson: somebase64encodedstring
metadata:
  name: registry-auth
  namespace: default"""
        m_write.assert_called_once_with(expected_result)

    def test_render_kubernetes_config(self, victim):
        result = victim._render_kubernetes_config('tests/azure/files/valid_k8s.yml.j2', 'my-little-pony', {"secret_pull_policy": "Always"}, {})

        # we need this stupid formatting to make the test pass...
        expected_result = """apiVersion: extensions/v1beta1
kind: Deployment
metadata:
  name: my-app
spec:
  replicas: 2
  template:
    metadata:
      labels:
        app: my-app
    spec:
      containers:
        - name: my-app
          image: my-image:v
          imagePullPolicy: Always
          ports:
            - containerPort: 8080
      imagePullSecrets:
        - name: acr-auth"""

        assert result == expected_result

    @mock.patch("takeoff.azure.deploy_to_kubernetes.DockerRegistry.credentials",
                return_value=DockerCredentials("myuser", "secretpassword", "registry.io"))
    def test_get_docker_registry_secret(self, _, victim):
        result = victim._get_docker_registry_secret()
        assert result == "eyJhdXRocyI6IHsicmVnaXN0cnkuaW8iOiB7InVzZXJuYW1lIjogIm15dXNlciIsICJwYXNzd29yZCI6ICJzZWNyZXRwYXNzd29yZCIsICJhdXRoIjogImJYbDFjMlZ5T25ObFkzSmxkSEJoYzNOM2IzSmsifX19"

    @pytest.mark.skip(reason="kubectl can't work without a valid kube context :(")
    @mock.patch("takeoff.azure.deploy_to_kubernetes.DockerRegistry.credentials",
                return_value=DockerCredentials("myuser", "secretpassword", "registry.io"))
    def test_validate_yaml(self, _, victim):
        path = victim._create_image_pull_secret("myapp")

        cmd = ["kubectl", "apply", "--dry-run", "--validate", "-f", path]
        code, lines = run_shell_command(cmd)
        print(lines)
        assert code == 0

    @mock.patch.dict(os.environ, env_variables)
    @mock.patch("takeoff.step.KeyVaultClient.vault_and_client", return_value=(None, None))
    def test_get_custom_values(self, _):
        custom_conf = {'custom_values': {'dev': {'my_custom_value': 'hello'}}, **BASE_CONF}
        conf = {**takeoff_config(), **custom_conf}
        conf['azure'].update({"kubernetes_naming": "kubernetes{env}"})

        res = DeployToKubernetes(ApplicationVersion("dev", "v", "branch"), conf)

        result = res._get_custom_values()
        expected_result = {"my_custom_value": "hello"}

        assert result == expected_result

    @mock.patch.dict(os.environ, env_variables)
    @mock.patch("takeoff.step.KeyVaultClient.vault_and_client", return_value=(None, None))
    def test_get_custom_values_missing_config(self, _, victim):
        result = victim._get_custom_values()
        expected_result = {}

        assert result == expected_result

    @mock.patch.dict(os.environ, env_variables)
    @mock.patch("takeoff.step.KeyVaultClient.vault_and_client", return_value=(None, None))
    def test_get_custom_values_invalid_env(self, _):
        custom_conf = {'custom_values': {'invalid_env': {'my_custom_value': 'hello'}}, **BASE_CONF}
        conf = {**takeoff_config(), **custom_conf}
        conf['azure'].update({"kubernetes_naming": "kubernetes{env}"})

        res = DeployToKubernetes(ApplicationVersion("dev", "v", "branch"), conf)

        with pytest.raises(ValueError):
            res._get_custom_values()

@dataclass(frozen=True)
class MockValue:
    value: bytes


@dataclass(frozen=True)
class MockCredentialResults:
    kubeconfigs: List[MockValue]


class TestBaseKubernetes():
    @mock.patch.dict(os.environ, {"HOME": "myhome"})
    def test_write_kube_config(self, victim: BaseKubernetes):
        mopen = mock.mock_open()
        with mock.patch("os.mkdir") as m_mkdir:
            with mock.patch("builtins.open", mopen):
                victim._write_kube_config(MockCredentialResults([MockValue("foo".encode(encoding="UTF-8"))]))

        m_mkdir.assert_called_once_with("myhome/.kube")
        mopen.assert_called_once_with("myhome/.kube/config", "w")
        mopen().write.assert_called_once_with("foo")
