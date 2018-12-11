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
    return_value=[
        Secret('subscription-id', 1),
        Secret('azure-username', 2),
        Secret('azure-password', 3),
        Secret('azure-databricks-host', 4),
        Secret('azure-databricks-token', 5),
        Secret('azure-shared-blob-username', 6),
        Secret('azure-shared-blob-password', 7),
        Secret('registry-username', 8),
        Secret('registry-password', 9),
        Secret('artifact-store-username', 10),
        Secret('artifact-store-password', 11),
        Secret('artifact-store-index-url', 12),
        Secret('artifact-store-upload-url', 13)
    ]
)
def test_common_credentials(_):
    res = victim.common_credentials('dev')
    assert len(res) == 13
    assert type(res) == dict
    assert res[victim.CommonCredentials.subscription_id].key == 'subscription-id'
    assert res[victim.CommonCredentials.subscription_id].val == 1
