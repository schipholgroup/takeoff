import logging
import os
import subprocess

from sdh_deployment.ApplicationVersion import ApplicationVersion
from sdh_deployment.DeploymentStep import DeploymentStep

logger = logging.getLogger(__name__)


class PublishArtifact(DeploymentStep):
    # this will assume the python package has already been built.
    def __init__(self, env: ApplicationVersion, config: dict):
        super().__init__(env, config)

    def run(self):
        self.publish_package()

    def publish_package(self):
        p = subprocess.Popen(['twine', 'upload', '/root/dist/*',
                         '--username', os.environ['ARTIFACT_STORE_USERNAME'],
                         '--password', os.environ['ARTIFACT_STORE_USERNAME'],
                         '--repository-url', os.environ['ARTIFACT_STORE_URL']], stdout=subprocess.PIPE)
        logging.info(p.communicate())
