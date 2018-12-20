from pprint import pprint
from unittest import mock

from runway.credentials.KeyVaultCredentialsMixin import KeyVaultCredentialsMixin


class TestKeyVaultCredentialsMixin(object):
    @mock.patch('runway.credentials.KeyVaultCredentialsMixin.KeyVaultCredentialsMixin._credentials',
                return_value={'key1': 'foo', 'key2': 'bar'})
    def test_transform_key_to_credential_kwargs(self, _):
        res = KeyVaultCredentialsMixin(None, None)._transform_key_to_credential_kwargs({'arg1': 'key1'})
        assert res == {'arg1': 'foo'}
