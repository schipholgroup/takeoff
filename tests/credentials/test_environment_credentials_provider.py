import os
from unittest import mock

import pytest

from takeoff.application_version import ApplicationVersion
from takeoff.credentials.environment_credentials_provider import EnvironmentCredentialsMixin as victim, SingleEnviromentCredentialProvider, CIEnvironmentCredentials


class TestEnvironmentCredentialsMixin:
    @mock.patch.dict(os.environ, {"key1": "foo", "key2": "bar"})
    def test_read_os_variables(self):
        res = victim()._read_os_variables(["key1"])
        assert res == {"key1": "foo"}

    @mock.patch.dict(os.environ, {"key1": "foo", "key2": "bar"})
    def test_transform_environment_key_to_credential_kwargs(self):
        res = victim()._transform_environment_key_to_credential_kwargs({"arg1": "key1", "arg2": "key2"})
        assert res == {"arg1": "foo", "arg2": "bar"}

    @mock.patch.dict(os.environ, {"MY_KEY": "Bert", "key2": "bar"})
    def test_transform_environment_key_to_single_credential(self):
        assert victim()._transform_environment_key_to_single_credential("app-name", "MY_KEY") == {"app-name": "Bert"}

    @mock.patch.dict(os.environ, {"MY_KEY": "Bert", "key2": "bar"})
    def test_transform_environment_key_to_single_credential_not_found(self):
        with pytest.raises(ValueError):
            assert victim()._transform_environment_key_to_single_credential("app-name", "NONEXISTING_KEY")


class TestSingleEnviromentCredentialProvider:
    @mock.patch.dict(os.environ, {"MY_KEY": "Bert", "key2": "bar"})
    def test_get_credentials(self):
        assert SingleEnviromentCredentialProvider({}, None).get_credentials(("app-name", "MY_KEY")) == {"app-name": "Bert"}

    def test_get_credentials_invalid_type(self):
        with pytest.raises(ValueError):
            SingleEnviromentCredentialProvider({}, None).get_credentials("str")


class TestCIEnvironmentCredentials:
    def test_get_credentials_invalid_type(self):
        with pytest.raises(ValueError):
            CIEnvironmentCredentials({}, None).get_credentials({})

    @mock.patch.dict(os.environ, {"USER": "Bert", "PASS": "Ernie"})
    def test_get_credentials(self):
        conf = {"ci_environment_keys_dev": {"credentials": {"username": "USER", "password": "PASS"}}}
        res = CIEnvironmentCredentials(conf, ApplicationVersion("dev", "", "")).get_credentials("credentials")
        assert res == {"username": "Bert", "password": "Ernie"}
