import logging
import subprocess

from twine.commands.upload import upload

from runway.ApplicationVersion import ApplicationVersion
from runway.DeploymentStep import DeploymentStep
from runway.util import get_artifact_store_settings, log_docker

logger = logging.getLogger(__name__)


class PublishArtifact(DeploymentStep):
    def __init__(self, env: ApplicationVersion, config: dict):
        super().__init__(env, config)

    def run(self):
        if not self.env.on_feature_branch:
            logging.info("Not on a release tag, not publishing an artifact.")
        else:
            self.build_package()
            self.publish_package()

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
        upload(upload_settings=get_artifact_store_settings(), dists=['/root/dist/*'])
