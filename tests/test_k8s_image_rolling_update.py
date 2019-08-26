import os
from unittest import mock

import yaml

from runway.ApplicationVersion import ApplicationVersion
from runway.k8s_image_rolling_update import K8sImageRollingUpdate as victim

with open('tests/test_runway_config.yaml', 'r') as f:
    runway_config = yaml.safe_load(f.read())

env_variables = {'AZURE_TENANTID': 'David',
                 'AZURE_KEYVAULT_SP_USERNAME_DEV': 'Doctor',
                 'AZURE_KEYVAULT_SP_PASSWORD_DEV': 'Who'}


@mock.patch.dict(os.environ, env_variables)
class TestDeployToK8s(object):
    @mock.patch("runway.DeploymentStep.AzureKeyvaultClient.vault_and_client", return_value=(None, None))
    def test_validate_schema(self, _):
        conf = {**runway_config, **{'task': 'K8sImageRollingUpdate',
                                    'cluster_name': "Dave",
                                    'resource_group': "Mustaine",
                                    'deployment_name': "the-king",
                                    'image': 'docker-image'}}

        res = victim(ApplicationVersion("dev", "v", "branch"), conf).validate()
        assert res['namespace'] == 'default'
