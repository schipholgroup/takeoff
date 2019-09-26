import unittest

import mock
import pytest

from takeoff.application_version import ApplicationVersion
from takeoff.build_artifact import BuildArtifact as victim
from tests.azure import takeoff_config

BASE_CONF = {"task": "build_artifact", "build_tool": "python"}
FAKE_ENV = ApplicationVersion('env', 'v', 'branch')


class TestBuildArtifact(unittest.TestCase):
    @mock.patch("takeoff.step.KeyVaultClient.vault_and_client", return_value=(None, None))
    def test_validate_minimal_schema(self, _):
        conf = {**takeoff_config(), **BASE_CONF}

        victim(FAKE_ENV, conf)

    @mock.patch("takeoff.step.KeyVaultClient.vault_and_client", return_value=(None, None))
    def test_build_python(self, _):
        conf = {**takeoff_config(), **BASE_CONF}

        with mock.patch.object(victim, "build_python_wheel") as m:
            victim(FAKE_ENV, conf).run()
        m.assert_called_once()

    @mock.patch("takeoff.step.KeyVaultClient.vault_and_client", return_value=(None, None))
    def test_build_sbt(self, _):
        conf = {**takeoff_config(), **BASE_CONF, "build_tool": "sbt"}

        with mock.patch.object(victim, "build_sbt_assembly_jar") as m:
            victim(FAKE_ENV, conf).run()
        m.assert_called_once()

    @mock.patch("takeoff.step.KeyVaultClient.vault_and_client", return_value=(None, None))
    @mock.patch.object(victim, "_write_version")
    @mock.patch.object(victim, "_remove_old_artifacts")
    def test_build_python_wheel(self, _, w, r):
        conf = {**takeoff_config(), **BASE_CONF}
        with mock.patch("takeoff.build_artifact.run_shell_command", return_value=(0, ['output_lines'])) as m:
            victim(FAKE_ENV, conf).build_python_wheel()
        m.assert_called_once_with(["python", "setup.py", "bdist_wheel"])

    @mock.patch("takeoff.step.KeyVaultClient.vault_and_client", return_value=(None, None))
    @mock.patch.object(victim, "_write_version")
    @mock.patch.object(victim, "_remove_old_artifacts")
    def test_build_python_wheel_fail(self, _, w, r):
        conf = {**takeoff_config(), **BASE_CONF}
        with pytest.raises(ChildProcessError):
            with mock.patch("takeoff.build_artifact.run_shell_command", return_value=(1, ['output_lines'])) as m:
                victim(FAKE_ENV, conf).build_python_wheel()
            m.assert_called_once_with(["python", "setup.py", "bdist_wheel"])

    @mock.patch("takeoff.step.KeyVaultClient.vault_and_client", return_value=(None, None))
    @mock.patch.object(victim, "_write_version")
    @mock.patch.object(victim, "_remove_old_artifacts")
    def test_build_python_wheel(self, _, w, r):
        conf = {**takeoff_config(), **BASE_CONF}
        with mock.patch("takeoff.build_artifact.run_shell_command", return_value=(0, ['output_lines'])) as m:
            victim(FAKE_ENV, conf).build_sbt_assembly_jar()
        m.assert_called_once_with(["sbt", "clean", "assembly"])

    @mock.patch("takeoff.step.KeyVaultClient.vault_and_client", return_value=(None, None))
    @mock.patch.object(victim, "_write_version")
    @mock.patch.object(victim, "_remove_old_artifacts")
    def test_build_python_wheel_fail(self, _, w, r):
        conf = {**takeoff_config(), **BASE_CONF}
        with pytest.raises(ChildProcessError):
            with mock.patch("takeoff.build_artifact.run_shell_command", return_value=(1, ['output_lines'])) as m:
                victim(FAKE_ENV, conf).build_sbt_assembly_jar()
            m.assert_called_once_with(["sbt", "clean", "assembly"])

    def test_remove_old_artifacts(self):
        with mock.patch("takeoff.build_artifact.shutil") as m:
            victim._remove_old_artifacts("some/path")
        m.rmtree.assert_called_once_with("some/path", ignore_errors=True)

    @mock.patch("takeoff.step.KeyVaultClient.vault_and_client", return_value=(None, None))
    def test_write_version(self, _):
        mopen = mock.mock_open()
        conf = {**takeoff_config(), **BASE_CONF}
        with mock.patch("builtins.open", mopen):
            victim(FAKE_ENV, conf)._write_version()

        mopen.assert_called_once_with("version.py", "w+")
        handle = mopen()
        handle.write.assert_called_once_with("__version__='v'")