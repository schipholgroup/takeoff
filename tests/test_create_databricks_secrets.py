import unittest

from sdh_deployment.create_databricks_secrets import CreateDatabricksSecrets as victim


class TestCreateDatabricksSecrets(unittest.TestCase):
    def test_scope_exists(self):
        scopes = {"scopes": [{"name": "foo"}, {"name": "bar"}]}

        assert victim._scope_exists(scopes, "foo")
        assert not victim._scope_exists(scopes, "foobar")
