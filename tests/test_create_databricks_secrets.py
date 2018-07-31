from pyspark_streaming_deployment import create_databricks_secrets as victim


def test_scope_exists():
    scopes = {'scopes': [
        {'name': 'foo'},
        {'name': 'bar'},
    ]}

    assert victim.__scope_exists(scopes, 'foo')
    assert not victim.__scope_exists(scopes, 'foobar')


def test_filter_ids():
    ids = ['app-foo-key1', 'appfoo-key2', 'app-bar-key3', 'app-key4']

    filtered = victim.__filter_ids(ids, 'app')
    assert len(filtered) == 3
    assert all(_ in filtered for _ in ('foo-key1', 'bar-key3', 'key4'))

    filtered = victim.__filter_ids(ids, 'app-foo')
    assert len(filtered) == 1
    assert 'key1' in filtered
