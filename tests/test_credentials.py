from unittest import mock

import pytest

from runway import credentials as victim

from runway.KeyVaultSecrets import Secret


@mock.patch(
    "runway.KeyVaultSecrets.KeyVaultSecrets.get_keyvault_secrets",
    return_value=[Secret("registry-username", "foo"), Secret("registry-password", "bar")]
)
def test_common_credentials_missing_values(_):
    with pytest.raises(ValueError):
        victim.common_credentials('dev')


@mock.patch(
    "runway.KeyVaultSecrets.KeyVaultSecrets.get_keyvault_secrets",
    return_value=[Secret(_, str(i)) for i, _ in enumerate(victim.CommonCredentials)]
)
def test_common_credentials(_):
    res = victim.common_credentials('dev')
    assert len(res) == 13
    assert type(res) == dict
