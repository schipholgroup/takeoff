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
        self.build_package()
        self.publish_package()

    def build_package(self):
        # First make sure the correct version number is used.
        with open('/root/version.py', 'w+') as f:
            f.write("__version__='0.0.3'")
        cmd = ['cd', '/root/', '&&', 'python', 'setup.py', 'bdist_wheel']

        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
        logging.info(p.communicate())

    def publish_package(self):
        cmd = ['twine', 'upload', '/root/dist/*',
               '--username', os.environ['ARTIFACT_STORE_USERNAME'],
               '--password', os.environ['ARTIFACT_STORE_PASSWORD'],
               '--repository-url', os.environ['ARTIFACT_STORE_URL']]

        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        logging.info(p.communicate())
