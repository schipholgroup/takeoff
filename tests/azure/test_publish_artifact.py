import glob
import unittest

import azure
import mock
import pytest
import voluptuous as vol

from takeoff.application_version import ApplicationVersion
from takeoff.azure.publish_artifact import PublishArtifact as victim
from takeoff.azure.publish_artifact import language_must_match_target
from tests.azure import takeoff_config

BASE_CONF = {"task": "publish_artifact", "language": "python", "target": ["cloud_storage"]}
FAKE_ENV = ApplicationVersion('env', 'v', 'branch')


class TestPublishArtifact(unittest.TestCase):
    def test_lang_must_match_target(self):
        config = {"language": "scala", "target": ["cloud_storage"]}
        language_must_match_target(config)

    def test_lang_must_match_target_wrong_sbt_target(self):
        config = {"language": "scala", "target": ["pypi"]}
        with pytest.raises(vol.Invalid):
            language_must_match_target(config)

    def test_lang_must_match_target_wrong_python_target(self):
        config = {"language": "python", "target": ["ivy"]}
        with pytest.raises(vol.Invalid):
            language_must_match_target(config)

    @mock.patch("takeoff.step.KeyVaultClient.vault_and_client", return_value=(None, None))
    def test_validate_minimal_schema(self, _):
        conf = {**takeoff_config(), **BASE_CONF}

        victim(ApplicationVersion("dev", "v", "branch"), conf)

    @mock.patch("takeoff.step.KeyVaultClient.vault_and_client", return_value=(None, None))
    def test_validate_schema_invalid_target(self, _):
        conf = {**takeoff_config(), **BASE_CONF, "target": ["WRONG"]}

        with pytest.raises(vol.MultipleInvalid):
            victim(ApplicationVersion("dev", "v", "branch"), conf)

    @mock.patch("takeoff.step.KeyVaultClient.vault_and_client", return_value=(None, None))
    def test_validate_schema_invalid_target(self, _):
        conf = {**takeoff_config(), **BASE_CONF, "target": ["ivy"]}

        with pytest.raises(vol.Invalid):
            victim(ApplicationVersion("dev", "v", "branch"), conf)

        conf = {**takeoff_config(), **BASE_CONF, **{"language": "sbt", "target": ["pypi"]}}

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

    @mock.patch("takeoff.step.KeyVaultClient.vault_and_client", return_value=(None, None))
    def test_publish_python_package_pypi(self, _):
        conf = {**takeoff_config(), **BASE_CONF, "target": ["pypi"]}

        with mock.patch.object(victim, 'publish_to_pypi') as m:
            victim(FAKE_ENV, conf).publish_python_package()

        m.assert_called_once()

    @mock.patch("takeoff.step.KeyVaultClient.vault_and_client", return_value=(None, None))
    @mock.patch.object(victim, "_get_wheel", return_value="some.whl")
    def test_publish_python_package_blob(self, _, __):
        conf = {**takeoff_config(), **BASE_CONF, "target": ["cloud_storage"]}

        with mock.patch.object(victim, 'upload_to_cloud_storage') as m:
            victim(FAKE_ENV, conf).publish_python_package()

        m.assert_called_once_with(file="some.whl", file_extension=".whl")

    @mock.patch("takeoff.step.KeyVaultClient.vault_and_client", return_value=(None, None))
    @mock.patch.object(victim, "_get_wheel", return_value="some.whl")
    def test_publish_python_package_blob_with_file(self, _, __):
        conf = {**takeoff_config(), **BASE_CONF, "target": ["cloud_storage"], "python_file_path": "main.py"}

        with mock.patch.object(victim, 'upload_to_cloud_storage') as m:
            victim(FAKE_ENV, conf).publish_python_package()

        calls = [mock.call(file="some.whl", file_extension=".whl"),
                 mock.call(file="main.py", file_extension=".py")]
        m.assert_has_calls(calls)

    @mock.patch("takeoff.step.KeyVaultClient.vault_and_client", return_value=(None, None))
    @mock.patch.object(victim, "_get_jar", return_value="some.jar")
    def test_publish_jar_to_blob(self, _, __):
        conf = {**takeoff_config(), **BASE_CONF, "language": "scala", "target": ["cloud_storage"]}

        with mock.patch.object(victim, 'upload_to_cloud_storage') as m:
            victim(FAKE_ENV, conf).publish_jvm_package()

        m.assert_called_once_with(file="some.jar", file_extension=".jar")

    @mock.patch("takeoff.step.KeyVaultClient.vault_and_client", return_value=(None, None))
    def test_publish_jar_package_ivy(self, _):
        conf = {**takeoff_config(), **BASE_CONF, "language": "scala", "target": ["ivy"]}

        with mock.patch.object(victim, 'publish_to_ivy') as m:
            victim(FAKE_ENV, conf).publish_jvm_package()

        m.assert_called_once()

    @mock.patch("takeoff.step.KeyVaultClient.vault_and_client", return_value=(None, None))
    def test_upload_file_to_blob(self, _):
        conf = {**takeoff_config(), **BASE_CONF, "language": "scala", "target": ["ivy"]}
        with mock.patch.object(azure.storage.blob, "BlockBlobService") as m:
            victim(FAKE_ENV, conf)._upload_file_to_azure_storage_account(m, "Dave", "Mustaine", "mylittlepony")
        m.create_blob_from_path.assert_called_once_with(container_name="mylittlepony", blob_name="Mustaine", file_path="Dave")

    @mock.patch("takeoff.step.KeyVaultClient.vault_and_client", return_value=(None, None))
    def test_publish_to_pypi_no_tag(self, _):
        conf = {**takeoff_config(), **BASE_CONF, "language": "python", "target": ["pypi"]}
        with mock.patch("takeoff.azure.publish_artifact.upload") as m:
            victim(FAKE_ENV, conf).publish_to_pypi()
        m.assert_not_called()

    @mock.patch("takeoff.step.KeyVaultClient.vault_and_client", return_value=(None, None))
    @mock.patch("takeoff.azure.publish_artifact.ArtifactStore.store_settings", return_value="foo")
    @mock.patch("takeoff.azure.publish_artifact.get_tag", return_value="a tag")
    def test_publish_to_pypi(self, _, __, ___):
        conf = {**takeoff_config(), **BASE_CONF, "language": "python", "target": ["pypi"]}
        env = ApplicationVersion('prd', '1.0.0', 'branch')
        with mock.patch("takeoff.azure.publish_artifact.upload") as m:
            victim(env, conf).publish_to_pypi()
        m.assert_called_once_with(upload_settings="foo", dists=["dist/*"])

    @mock.patch("takeoff.step.KeyVaultClient.vault_and_client", return_value=(None, None))
    def test_publish_to_ivy(self, _):
        conf = {**takeoff_config(), **BASE_CONF, "language": "scala", "target": ["ivy"]}
        with mock.patch("takeoff.azure.publish_artifact.run_shell_command", return_value=0) as m:
            victim(FAKE_ENV, conf).publish_to_ivy()
        m.assert_called_once_with(["sbt", 'set version := "v-SNAPSHOT"', "publish"])

    @mock.patch("takeoff.step.KeyVaultClient.vault_and_client", return_value=(None, None))
    @mock.patch("takeoff.azure.publish_artifact.get_tag", return_value="1.0.0")
    def test_publish_to_ivy_with_tag(self, _, __):
        conf = {**takeoff_config(), **BASE_CONF, "language": "scala", "target": ["ivy"]}
        env = ApplicationVersion('prd', '1.0.0', 'branch')
        with mock.patch("takeoff.azure.publish_artifact.run_shell_command", return_value=0) as m:
            victim(env, conf).publish_to_ivy()
        m.assert_called_once_with(["sbt", 'set version := "1.0.0"', "publish"])
