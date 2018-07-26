from pyspark_streaming_deployment import create_databricks_secrets as victim


def test_scope_exists():
    scopes = {'scopes': [
        {'name': 'foo'},
        {'name': 'bar'},
    ]}

    assert victim.__scope_exists(scopes, 'foo')
    assert not victim.__scope_exists(scopes, 'foobar')


def test_parse_secrets_bundle():
    crap_json = "[{'id': 'https://sdhkeyvaultdev.vault.azure.net/secrets/hello', 'attributes': {'enabled': True, 'created': 1532524103, 'updated': 1532524103, 'recoveryLevel': 'Purgeable'}, 'tags': {'application': 'poc'}}, {'id': 'https://sdhkeyvaultdev.vault.azure.net/secrets/sdhappkeydatalakedev', 'attributes': {'enabled': True, 'created': 1526540091, 'updated': 1526540091, 'recoveryLevel': 'Purgeable'}}, {'id': 'https://sdhkeyvaultdev.vault.azure.net/secrets/sdhconnectionstringoracleacsmdev', 'attributes': {'enabled': True, 'created': 1528272980, 'updated': 1528272980, 'recoveryLevel': 'Purgeable'}}, {'id': 'https://sdhkeyvaultdev.vault.azure.net/secrets/sdhconnectionstringoracleblipdev', 'attributes': {'enabled': True, 'created': 1530797284, 'updated': 1530797284, 'recoveryLevel': 'Purgeable'}}, {'id': 'https://sdhkeyvaultdev.vault.azure.net/secrets/sdhconnectionstringoraclecdwdev', 'attributes': {'enabled': True, 'created': 1526481580, 'updated': 1526481580, 'recoveryLevel': 'Purgeable'}}, {'id': 'https://sdhkeyvaultdev.vault.azure.net/secrets/sdhconnectionstringoracleMaximodev', 'attributes': {'enabled': True, 'created': 1528276433, 'updated': 1528276433, 'recoveryLevel': 'Purgeable'}}, {'id': 'https://sdhkeyvaultdev.vault.azure.net/secrets/sdhconnectionstringoracleonexsdev', 'attributes': {'enabled': True, 'created': 1530797282, 'updated': 1530797282, 'recoveryLevel': 'Purgeable'}}, {'id': 'https://sdhkeyvaultdev.vault.azure.net/secrets/sdhconnectionstringoraclerisdev', 'attributes': {'enabled': True, 'created': 1527236078, 'updated': 1527236078, 'recoveryLevel': 'Purgeable'}}, {'id': 'https://sdhkeyvaultdev.vault.azure.net/secrets/sdhconnectionstringsqlazurewatermarkdev', 'attributes': {'enabled': True, 'created': 1526480877, 'updated': 1526480877, 'recoveryLevel': 'Purgeable'}}, {'id': 'https://sdhkeyvaultdev.vault.azure.net/secrets/sdhcredentialspwtdev', 'attributes': {'enabled': True, 'created': 1526390000, 'updated': 1526390000, 'recoveryLevel': 'Purgeable'}}]"

    pretty_json = victim.__parse_secret_bundle(crap_json)

    assert type(pretty_json) == list

    for key in pretty_json:
        assert 'id' in key


def test_extract_ids_from_keys():
    keys = [
        {'id': '/some/url/foo'},
        {'id': '/some/url/bar'}
    ]

    ids = victim.__extract_ids_from_keys(keys)

    assert all(_ in ids for _ in ('foo', 'bar'))


def test_filter_ids():
    ids = ['app-foo-key1', 'appfoo-key2', 'app-bar-key3', 'app-key4']

    filtered = victim.__filter_ids(ids, 'app')
    assert len(filtered) == 3
    assert all(_ in filtered for _ in ('foo-key1', 'bar-key3', 'key4'))

    filtered = victim.__filter_ids(ids, 'app-foo')
    assert len(filtered) == 1
    assert 'key1' in filtered
