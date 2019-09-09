import glob
import unittest

import azure
import mock
import pytest
import voluptuous as vol

from runway.ApplicationVersion import ApplicationVersion
from runway.azure.publish_artifact import PublishArtifact as victim
from runway.azure.publish_artifact import lang_must_match_target
from tests.azure import runway_config

BASE_CONF = {"task": "publishArtifact", "lang": "python", "target": ["blob"]}
FAKE_ENV = ApplicationVersion('env', 'v', 'branch')


class TestPublishArtifact(unittest.TestCase):
    def test_lang_must_match_target(self):
        config = {"lang": "sbt", "target": ["blob"]}
        lang_must_match_target(config)

    def test_lang_must_match_target_wrong_sbt_target(self):
        config = {"lang": "sbt", "target": ["pypi"]}
        with pytest.raises(vol.Invalid):
            lang_must_match_target(config)

    def test_lang_must_match_target_wrong_python_target(self):
        config = {"lang": "python", "target": ["ivy"]}
        with pytest.raises(vol.Invalid):
            lang_must_match_target(config)

    @mock.patch("runway.Step.KeyVaultClient.vault_and_client", return_value=(None, None))
    def test_validate_minimal_schema(self, _):
        conf = {**runway_config(), **BASE_CONF}

        victim(ApplicationVersion("dev", "v", "branch"), conf)

    @mock.patch("runway.Step.KeyVaultClient.vault_and_client", return_value=(None, None))
    def test_validate_schema_invalid_target(self, _):
        conf = {**runway_config(), **BASE_CONF, "target": ["WRONG"]}

        with pytest.raises(vol.MultipleInvalid):
            victim(ApplicationVersion("dev", "v", "branch"), conf)

    @mock.patch("runway.Step.KeyVaultClient.vault_and_client", return_value=(None, None))
    def test_validate_schema_invalid_target(self, _):
        conf = {**runway_config(), **BASE_CONF, "target": ["ivy"]}

        with pytest.raises(vol.Invalid):
            victim(ApplicationVersion("dev", "v", "branch"), conf)

        conf = {**runway_config(), **BASE_CONF, **{"lang": "sbt", "target": ["pypi"]}}

        with pytest.raises(vol.Invalid):
            victim(ApplicationVersion("dev", "v", "branch"), conf)

    def test_get_jar(self):
        with mock.patch.object(glob, 'glob', return_value=['some-assembly-file.jar']):
            res = victim._get_jar()
            assert res == 'some-assembly-file.jar'

    def test_get_jar_too_many(self):
        with mock.patch.object(glob, 'glob', return_value=['some-assembly-file.jar',
                                                           'another-assembly-shizzle.jar']):
            with pytest.raises(FileNotFoundError):
                victim._get_jar()

    def test_get_jar_none_found(self):
        with mock.patch.object(glob, 'glob', return_value=[]):
            with pytest.raises(FileNotFoundError):
                victim._get_jar()

    def test_get_wheel(self):
        with mock.patch.object(glob, 'glob', return_value=['some.whl']):
            res = victim._get_jar()
            assert res == 'some.whl'

    def test_get_wheel_too_many(self):
        with mock.patch.object(glob, 'glob', return_value=['some.whl',
                                                           'another.whl']):
            with pytest.raises(FileNotFoundError):
                victim._get_jar()

    def test_get_wheel_none_found(self):
        with mock.patch.object(glob, 'glob', return_value=[]):
            with pytest.raises(FileNotFoundError):
                victim._get_jar()

    @mock.patch("runway.Step.KeyVaultClient.vault_and_client", return_value=(None, None))
    def test_publish_python_package_pypi(self, _):
        conf = {**runway_config(), **BASE_CONF, "target": ["pypi"]}

        with mock.patch.object(victim, 'publish_to_pypi') as m:
            victim(FAKE_ENV, conf).publish_python_package()

        m.assert_called_once()

    @mock.patch("runway.Step.KeyVaultClient.vault_and_client", return_value=(None, None))
    @mock.patch.object(victim, "_get_wheel", return_value="some.whl")
    def test_publish_python_package_blob(self, _, __):
        conf = {**runway_config(), **BASE_CONF, "target": ["blob"]}

        with mock.patch.object(victim, 'publish_to_blob') as m:
            victim(FAKE_ENV, conf).publish_python_package()

        m.assert_called_once_with(file="some.whl", file_ext=".whl")

    @mock.patch("runway.Step.KeyVaultClient.vault_and_client", return_value=(None, None))
    @mock.patch.object(victim, "_get_wheel", return_value="some.whl")
    def test_publish_python_package_blob_with_file(self, _, __):
        conf = {**runway_config(), **BASE_CONF, "target": ["blob"], "python_file_path": "main.py"}

        with mock.patch.object(victim, 'publish_to_blob') as m:
            victim(FAKE_ENV, conf).publish_python_package()

        calls = [mock.call(file="some.whl", file_ext=".whl"),
                 mock.call(file="main.py", file_ext=".py")]
        m.assert_has_calls(calls)

    @mock.patch("runway.Step.KeyVaultClient.vault_and_client", return_value=(None, None))
    @mock.patch.object(victim, "_get_jar", return_value="some.jar")
    def test_publish_python_package_pypi(self, _, __):
        conf = {**runway_config(), **BASE_CONF, "lang": "sbt", "target": ["blob"]}

        with mock.patch.object(victim, 'publish_to_blob') as m:
            victim(FAKE_ENV, conf).publish_jvm_package()

        m.assert_called_once_with(file="some.jar", file_ext=".jar")

    @mock.patch("runway.Step.KeyVaultClient.vault_and_client", return_value=(None, None))
    def test_publish_python_package_blob(self, _):
        conf = {**runway_config(), **BASE_CONF, "lang": "sbt", "target": ["ivy"]}

        with mock.patch.object(victim, 'publish_to_ivy') as m:
            victim(FAKE_ENV, conf).publish_jvm_package()

        m.assert_called_once()

    @mock.patch("runway.Step.KeyVaultClient.vault_and_client", return_value=(None, None))
    def test_upload_file_to_blob(self, _):
        conf = {**runway_config(), **BASE_CONF, "lang": "sbt", "target": ["ivy"]}
        with mock.patch.object(azure.storage.blob, "BlockBlobService") as m:
            victim(FAKE_ENV, conf)._upload_file_to_blob(m, "Dave", "Mustaine", "mylittlepony")
        m.create_blob_from_path.assert_called_once_with(container_name="mylittlepony", blob_name="Mustaine", file_path="Dave")

    @mock.patch("runway.Step.KeyVaultClient.vault_and_client", return_value=(None, None))
    def test_publish_to_pypi_no_tag(self, _):
        conf = {**runway_config(), **BASE_CONF, "lang": "python", "target": ["pypi"]}
        with mock.patch("runway.azure.publish_artifact.upload") as m:
            victim(FAKE_ENV, conf).publish_to_pypi()
        m.assert_not_called()

    @mock.patch("runway.Step.KeyVaultClient.vault_and_client", return_value=(None, None))
    @mock.patch("runway.azure.publish_artifact.ArtifactStore.store_settings", return_value="foo")
    @mock.patch("runway.azure.publish_artifact.get_tag", return_value="a tag")
    def test_publish_to_pypi(self, _, __, ___):
        conf = {**runway_config(), **BASE_CONF, "lang": "python", "target": ["pypi"]}
        env = ApplicationVersion('prd', '1.0.0', 'branch')
        with mock.patch("runway.azure.publish_artifact.upload") as m:
            victim(env, conf).publish_to_pypi()
        m.assert_called_once_with(upload_settings="foo", dists=["dist/*"])

    @mock.patch("runway.Step.KeyVaultClient.vault_and_client", return_value=(None, None))
    def test_publish_to_ivy(self, _):
        conf = {**runway_config(), **BASE_CONF, "lang": "python", "target": ["pypi"]}
        with mock.patch("runway.azure.publish_artifact.run_bash_command") as m:
            victim(FAKE_ENV, conf).publish_to_ivy()
        m.assert_called_once_with(["sbt", 'set version := "v-SNAPSHOT"', "publish"])

    @mock.patch("runway.Step.KeyVaultClient.vault_and_client", return_value=(None, None))
    @mock.patch("runway.azure.publish_artifact.get_tag", return_value="a tag")
    def test_publish_to_ivy_with_tag(self, _, __):
        conf = {**runway_config(), **BASE_CONF, "lang": "python", "target": ["pypi"]}
        env = ApplicationVersion('prd', '1.0.0', 'branch')
        with mock.patch("runway.azure.publish_artifact.run_bash_command") as m:
            victim(env, conf).publish_to_ivy()
        m.assert_called_once_with(["sbt", 'set version := "1.0.0"', "publish"])
