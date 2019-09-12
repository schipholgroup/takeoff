import os
from unittest import mock

import pytest

from takeoff.application_version import ApplicationVersion
from takeoff.azure.kubernetes_image_rolling_update import KubernetesImageRollingUpdate
from tests.azure import takeoff_config

env_variables = {'AZURE_TENANTID': 'David',
                 'AZURE_KEYVAULT_SP_USERNAME_DEV': 'Doctor',
                 'AZURE_KEYVAULT_SP_PASSWORD_DEV': 'Who'}


@pytest.fixture(autouse=True)
@mock.patch("takeoff.step.KeyVaultClient.vault_and_client", return_value=(None, None))
def victim(_):
    conf = {**takeoff_config(), **{'task': 'kubernetesImageRollingUpdate',
                                   'deployment_name': "the-king",
                                   'image': 'docker-image'}}

    conf['azure'].update({"kubernetes_naming": "aks{env}"})
    return KubernetesImageRollingUpdate(ApplicationVersion("dev", "1.0.2", "branch"), conf)


@mock.patch.dict(os.environ, env_variables)
class TestKubernetesImageRollingUpdate(object):
    def test_validate_schema(self, victim):
        assert victim.config['namespace'] == 'default'

    @mock.patch("takeoff.azure.kubernetes_image_rolling_update.run_shell_command", return_value=0)
    def test_apply_rolling_update_success(self, m_bash, victim: KubernetesImageRollingUpdate):
        victim._apply_rolling_update()
        cmd = [
            "kubectl",
            "--namespace",
            "default",
            "--record",
            f"deployment.apps/the-king",
            "set",
            "image",
            f"deployment.v1.apps/the-king",
            f"the-king=docker-image:1.0.2",
        ]
        m_bash.assert_called_once_with(cmd)

    @mock.patch("takeoff.azure.kubernetes_image_rolling_update.run_shell_command", return_value=1)
    def test_apply_rolling_update_failure(self, m_bash, victim: KubernetesImageRollingUpdate):
        with pytest.raises(ChildProcessError):
            victim._apply_rolling_update()
