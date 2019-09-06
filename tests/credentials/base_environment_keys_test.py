import abc
import os
import unittest

import mock

OS_KEYS = {'AZ_SP_CLIENT_ID_ENV': 'd0aaa0de-c1ef-456f-a025-c5d6341193bb',
           'AZ_SP_CLIENT_SECRET_ENV': '3ceb401f-6462-48da-b42f-b1d1745c2590',
           'CI_PROJECT_NAME': 'test-project',
           'CI_BRANCH_NAME': 'master',
           }

CONFIG = {
    "azure": {
        "keyvault_naming": "myvault{env}"
    },
    "environment_keys": {
        "application_name": "CI_PROJECT_NAME",
        "branch_name": "CI_BRANCH_NAME"
    },
    "ci_environment_keys_env": {
        "service_principal":
            {"client_id": "AZ_SP_CLIENT_ID_ENV",
             "secret": "AZ_SP_CLIENT_SECRET_ENV"},
    }}


class EnvironmentKeyBaseTest(unittest.TestCase):

    @mock.patch.dict(os.environ, OS_KEYS)
    def execute(self, mock_class, assertion):
        with mock.patch(mock_class) as m:
            self.call_victim(CONFIG)
        m.assert_called_once_with(**assertion)

    @abc.abstractmethod
    def call_victim(self, config):
        pass
