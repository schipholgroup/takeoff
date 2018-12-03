import logging
import os
import subprocess

from sdh_deployment.ApplicationVersion import ApplicationVersion
from sdh_deployment.DeploymentStep import DeploymentStep

logger = logging.getLogger(__name__)


class PublishArtifact(DeploymentStep):
    def __init__(self, env: ApplicationVersion, config: dict):
        super().__init__(env, config)

    def run(self):
        if self.env.on_feature_branch:
            logging.info("Not on a release tag, not publishing an artifact.")
        else:
            self.build_package()
            self.publish_package()

    def build_package(self):
        # First make sure the correct version number is used.
        with open('/root/version.py', 'w+') as f:
            f.write(f"__version__='{self.env.version}'")
        cmd = ['python', 'setup.py', 'bdist_wheel']

        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, cwd='/root/')
        logging.info(p.communicate())

    def publish_package(self):
        cmd = ['twine', 'upload', '/root/dist/*',
               '--username', os.environ['ARTIFACT_STORE_USERNAME'],
               '--password', os.environ['ARTIFACT_STORE_PASSWORD'],
               '--repository-url', f'{os.environ["ARTIFACT_STORE_URL"]}/upload']

        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        logging.info(p.communicate())
