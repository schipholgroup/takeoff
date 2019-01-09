import os
from unittest import mock

from runway.credentials.EnvironmentCredentialsMixin import EnvironmentCredentialsMixin as victim


class TestEnvironmentCredentialsMixin(object):
    @mock.patch.dict(os.environ, {'key1': 'foo', 'key2': 'bar'})
    def test_read_os_variables(self):
        res = victim()._read_os_variables(['key1'])
        assert res == {'key1': 'foo'}

    @mock.patch.dict(os.environ, {'key1': 'foo', 'key2': 'bar'})
    def test_transform_environment_key_to_credential_kwargs(self):
        res = victim()._transform_environment_key_to_credential_kwargs({
            'arg1': 'key1', 'arg2': 'key2'
        })
        assert res == {'arg1': 'foo', 'arg2': 'bar'}
