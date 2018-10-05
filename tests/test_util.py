import importlib
import re

import pytest

from sdh_deployment import util as victim
from sdh_deployment.util import KeyVaultSecrets


class TestPatternMatching(object):
    pattern = re.compile("(^foo)-([0-9]{1,3})-snapshot$")
    test_strings = [
        "foo-031-snapshot",
        "foo-12-snapshot",
        "foo-1234-snapshot",
        "foobar-309-snapshot",
        "foo-20-snap",
    ]

    def test_has_prefix_match(self):
        values = [True, True, False, False, False]
        for string, value in zip(self.test_strings, values):
            assert victim.has_prefix_match(string, "foo", self.pattern) == value

    def test_get_matching_group(self):
        values = [(1, "031"), (0, "foo")]
        for string, (idx, value) in zip(self.test_strings[:2], values):
            assert victim.get_matching_group(string, self.pattern, idx) == value

    def test_get_matches_no_group_found(self):
        values = [(1, "031"), (0, "foo"), (3, "snap")]
        for string, (idx, value) in zip(self.test_strings[2:], values):
            with pytest.raises(ValueError):
                assert victim.get_matching_group(string, self.pattern, idx) == value

    def test_get_matching_group_not_enough_groups(self):
        values = [(3, "031"), (7, "foo")]
        for string, (idx, value) in zip(self.test_strings[:2], values):
            with pytest.raises(IndexError):
                assert victim.get_matching_group(string, self.pattern, idx) == value


def test_get_eventhub_namespace():
    # Make sure that the python module cache is flushed
    importlib.reload(victim)
    from sdh_deployment.util import EVENTHUB_NAMESPACE

    assert EVENTHUB_NAMESPACE == "sdheventhub{dtap}"


def test_get_eventhub_resource_group():
    # Make sure that the python module cache is flushed
    importlib.reload(victim)
    from sdh_deployment.util import RESOURCE_GROUP

    assert RESOURCE_GROUP == "sdh{dtap}"


def test_filter_ids():
    ids = ["app-foo-key1", "appfoo-key2", "app-bar-key3", "app-key4"]

    filtered = [
        _.databricks_secret_key for _ in KeyVaultSecrets._filter_keyvault_ids(ids, "app")
    ]
    assert len(filtered) == 3
    assert all(_ in filtered for _ in ("foo-key1", "bar-key3", "key4"))

    filtered = [
        _.databricks_secret_key for _ in KeyVaultSecrets._filter_keyvault_ids(ids, "app-foo")
    ]
    assert len(filtered) == 1
    assert "key1" in filtered
