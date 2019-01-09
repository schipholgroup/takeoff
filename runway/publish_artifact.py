import logging
import subprocess

from twine.commands.upload import upload

from runway.ApplicationVersion import ApplicationVersion
from runway.DeploymentStep import DeploymentStep
from runway.credentials.azure_devops_artifact_store import DevopsArtifactStore
from runway.util import log_docker, get_tag

logger = logging.getLogger(__name__)


class PublishArtifact(DeploymentStep):
    def __init__(self, env: ApplicationVersion, config: dict):
        super().__init__(env, config)

    def run(self):
        # if there's a tag, we're on a release.
        if get_tag():
            self.build_package()
            self.publish_package()
        else:
            logging.info("Not on a release tag, not publishing an artifact.")

    def build_package(self):
        # First make sure the correct version number is used.
        with open('/root/version.py', 'w+') as f:
            f.write(f"__version__='{self.env.version}'")
        cmd = ['python', 'setup.py', 'bdist_wheel']

        p = subprocess.Popen(cmd,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT,
                             cwd='/root/',
                             universal_newlines=True)
        log_docker(iter(p.stdout.readline, ''))
        return_code = p.wait()

        assert return_code == 0, 'Could not build the package for some reason!'

    def publish_package(self):
        credentials = DevopsArtifactStore(vault_name=self.vault_name, vault_client=self.vault_client).store_settings(self.config)
        upload(upload_settings=credentials, dists=['/root/dist/*'])
