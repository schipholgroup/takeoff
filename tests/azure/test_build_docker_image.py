import base64
import os

import mock
import pytest

from takeoff.application_version import ApplicationVersion
from takeoff.build_docker_image import DockerImageBuilder, DockerFile
from takeoff.credentials.container_registry import DockerCredentials
from tests.azure import takeoff_config

BASE_CONF = {"task": "build_docker_image", "credentials": "azure_keyvault"}

CREDS = DockerCredentials("My", "Little", "pony")
ENV_VARIABLES = {"HOME": "my_home",
                 "PIP_EXTRA_INDEX_URL": "url/to/artifact/store"}


@pytest.fixture(autouse=True)
@mock.patch.dict(os.environ, {"CI_PROJECT_NAME": "Elon"})
def victim() -> DockerImageBuilder:
    with mock.patch("takeoff.step.KeyVaultClient.vault_and_client", return_value=(None, None)), \
         mock.patch("takeoff.build_docker_image.DockerRegistry.credentials", return_value=CREDS):
        conf = {**takeoff_config(), **BASE_CONF}
        return DockerImageBuilder(ApplicationVersion('DEV', '2.1.0', 'MASTER'), conf)


def assert_docker_json(mopen, mjson):
    mopen.assert_called_once_with("my_home/.docker/config.json", "w")
    auth = base64.b64encode("My:Little".encode()).decode()
    jsn = {"auths": {"pony": {"auth": auth}}}
    mjson.assert_called_once_with(jsn, mopen())


def test_construct_docker_build_config(victim: DockerImageBuilder):
    res = victim._construct_docker_build_config()
    assert res == [DockerFile("Dockerfile", None, None)]


def assert_docker_push(m_bash):
    m_bash.assert_called_once_with(["docker", "push", "image/stag"])


def assert_docker_build(m_bash):
    m_bash.assert_called_once_with(["docker",
                                    "build",
                                    "--build-arg",
                                    "PIP_EXTRA_INDEX_URL=url/to/artifact/store",
                                    "-t",
                                    "stag",
                                    "-f",
                                    "./Thefile",
                                    "."])


class TestDockerImageBuilder:

    @mock.patch("takeoff.step.KeyVaultClient.vault_and_client", return_value=(None, None))
    @mock.patch("takeoff.azure.build_docker_image.DockerRegistry.credentials", return_value=CREDS)
    def test_validate_minimal_schema(self, _, __):
        conf = {**takeoff_config(), **{'task': 'build_docker_image'}}

        res = DockerImageBuilder(ApplicationVersion("dev", "v", "branch"), conf)
        assert res.config['dockerfiles'] == [{"file": "Dockerfile", "postfix": None, "custom_image_name": None}]

    @mock.patch("takeoff.step.KeyVaultClient.vault_and_client", return_value=(None, None))
    @mock.patch("takeoff.azure.build_docker_image.DockerRegistry.credentials", return_value=CREDS)
    def test_validate_full_schema(self, _, __):
        conf = {**takeoff_config(),
                **{'task': 'build_docker_image',
                   "dockerfiles": [{
                       "file": "Dockerfile_custom",
                       "postfix": "Dave",
                       "custom_image_name": "Mustaine"
                   }]}}

        DockerImageBuilder(ApplicationVersion("dev", "v", "branch"), conf)

    @mock.patch.dict(os.environ, ENV_VARIABLES)
    @mock.patch("os.path.exists", return_value=False)
    def test_populate_docker_config_no_dir(self, _, victim):
        mopen = mock.mock_open()
        with mock.patch("os.mkdir") as m_mkdir:
            with mock.patch("builtins.open", mopen):
                with mock.patch("json.dump") as mjson:
                    victim.populate_docker_config()

        m_mkdir.assert_called_once_with("my_home/.docker")
        assert_docker_json(mopen, mjson)

    @mock.patch.dict(os.environ, ENV_VARIABLES)
    @mock.patch("os.path.exists", return_value=True)
    def test_populate_docker_config_path_exists(self, _, victim):
        mopen = mock.mock_open()

        with mock.patch("os.mkdir") as m_mkdir:
            with mock.patch("builtins.open", mopen):
                with mock.patch("json.dump") as mjson:
                    victim.populate_docker_config()

        m_mkdir.assert_not_called()
        assert_docker_json(mopen, mjson)

    @mock.patch.dict(os.environ, ENV_VARIABLES)
    @mock.patch("takeoff.azure.build_docker_image.run_bash_command", return_value=0)
    def test_build_image_success(self, m_bash):
        DockerImageBuilder.build_image("Thefile", "stag")
        assert_docker_build(m_bash)

    @mock.patch.dict(os.environ, ENV_VARIABLES)
    @mock.patch("takeoff.azure.build_docker_image.run_bash_command", return_value=1)
    def test_build_image_failure(self, m_bash):
        with pytest.raises(ChildProcessError):
            DockerImageBuilder.build_image("Thefile", "stag")
        assert_docker_build(m_bash)

    @mock.patch("takeoff.azure.build_docker_image.run_bash_command", return_value=0)
    def test_push_image_success(self, m_bash):
        DockerImageBuilder.push_image("image/stag")
        assert_docker_push(m_bash)

    @mock.patch("takeoff.azure.build_docker_image.run_bash_command", return_value=1)
    def test_push_image_failure(self, m_bash):
        with pytest.raises(ChildProcessError):
            DockerImageBuilder.push_image("image/stag")
        assert_docker_push(m_bash)

    @mock.patch.dict(os.environ, {"PIP_EXTRA_INDEX_URL": "url/to/artifact/store",
                                  "CI_PROJECT_NAME": "myapp",
                                  "CI_COMMIT_REF_SLUG": "ignored"})
    @mock.patch("takeoff.azure.build_docker_image.run_bash_command", return_value=0)
    def test_deploy(self, m_bash, victim: DockerImageBuilder):
        files = [DockerFile("Dockerfile", None, None), DockerFile("File2", "-foo", "mycustom/repo")]
        victim.deploy(files)
        build_call_1 = ["docker", "build", "--build-arg", "PIP_EXTRA_INDEX_URL=url/to/artifact/store", "-t", "pony/myapp:2.1.0", "-f", "./Dockerfile", "."]
        build_call_2 = ["docker", "build", "--build-arg", "PIP_EXTRA_INDEX_URL=url/to/artifact/store", "-t", "mycustom/repo-foo:2.1.0", "-f", "./File2", "."]

        push_call_1 = ["docker", "push", "pony/myapp:2.1.0"]
        push_call_2 = ["docker", "push", "mycustom/repo-foo:2.1.0"]
        calls = list(map(mock.call, [build_call_1, push_call_1, build_call_2, push_call_2]))
        m_bash.assert_has_calls(calls)
