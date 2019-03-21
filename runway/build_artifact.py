import logging
import shutil
import subprocess
import sys
from typing import List

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
        elif self.config["lang"] == "sbt":
            self.build_sbt_assembly_jar()
        else:
            logging.info("Currently only python artifact building is supported")
        # TODO: add support for building jars

    @staticmethod
    def call_subprocess(cmd: List[str]) -> int:
        p = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd="./", universal_newlines=True
        )

        def is_end(p, type):
            msg = type.readline()
            if msg == '' and p.poll() != None:
                return True
            if msg != '':
                sys.stdout.write(msg)
            return False

        while True:
            if is_end(p, p.stdout):
                break
        return p.wait()

    def build_python_wheel(self):
        # First make sure the correct version number is used.
        with open("version.py", "w+") as f:
            f.write(f"__version__='{self.env.version}'")
        # ensure any old artifacts are gone
        shutil.rmtree("dist/", ignore_errors=True)

        cmd = ["python", "setup.py", "bdist_wheel"]
        return_code = self.call_subprocess(cmd)

        assert return_code == 0, "Could not build the package for some reason!"

    def build_sbt_assembly_jar(self):
        # ensure any old artifacts are gone
        shutil.rmtree("target/", ignore_errors=True)

        cmd = ["sbt", "clean", "assembly"]
        return_code = self.call_subprocess(cmd)

        assert return_code == 0, "Could not build the package for some reason!"
