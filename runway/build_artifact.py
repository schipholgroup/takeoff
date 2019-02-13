import logging
import shutil
import subprocess

from runway.ApplicationVersion import ApplicationVersion
from runway.DeploymentStep import DeploymentStep
from runway.util import log_docker

logger = logging.getLogger(__name__)


class BuildArtifact(DeploymentStep):
    def __init__(self, env: ApplicationVersion, config: dict):
        super().__init__(env, config)

    def run(self):
        if self.config["lang"] == "python":
            self.build_python_wheel()
        else:
            logging.info("Currently only python artifact building is supported")
        # TODO: add support for building jars

    def build_python_wheel(self):
        # First make sure the correct version number is used.
        with open('/root/version.py', 'w+') as f:
            f.write(f"__version__='{self.env.version}'")
        # ensure any old artifacts are gone
        shutil.rmtree('/root/dist/', ignore_errors=True)

        cmd = ['python', 'setup.py', 'bdist_wheel']
        p = subprocess.Popen(cmd,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT,
                             cwd='/root/',
                             universal_newlines=True)
        log_docker(iter(p.stdout.readline, ''))
        return_code = p.wait()

        assert return_code == 0, 'Could not build the package for some reason!'
