import logging
import shutil

import voluptuous as vol

from takeoff.application_version import ApplicationVersion
from takeoff.schemas import TAKEOFF_BASE_SCHEMA
from takeoff.step import Step
from takeoff.util import run_bash_command

logger = logging.getLogger(__name__)

SCHEMA = TAKEOFF_BASE_SCHEMA.extend(
    {vol.Required("task"): "buildArtifact", vol.Required("lang"): vol.All(str, vol.In(["python", "sbt"]))},
    extra=vol.ALLOW_EXTRA,
)


class BuildArtifact(Step):
    def __init__(self, env: ApplicationVersion, config: dict):
        super().__init__(env, config)

    def run(self):
        if self.config["lang"] == "python":
            self.build_python_wheel()
        elif self.config["lang"] == "sbt":
            self.build_sbt_assembly_jar()
        else:
            logging.info("Currently only python artifact building is supported")

    def schema(self) -> vol.Schema:
        return SCHEMA

    def _write_version(self):
        """First make sure the correct version number is used."""
        with open("version.py", "w+") as f:
            f.write(f"__version__='{self.env.version}'")

    @staticmethod
    def _remove_old_artifacts(path: str):
        """Ensure any old artifacts are gone"""
        shutil.rmtree(path, ignore_errors=True)

    def build_python_wheel(self):
        self._write_version()
        self._remove_old_artifacts("dist/")

        cmd = ["python", "setup.py", "bdist_wheel"]
        return_code = run_bash_command(cmd)

        if return_code != 0:
            raise ChildProcessError("Could not build the package for some reason!")

    def build_sbt_assembly_jar(self):
        # ensure any old artifacts are gone
        self._remove_old_artifacts("target/")

        cmd = ["sbt", "clean", "assembly"]
        return_code = run_bash_command(cmd)

        if return_code != 0:
            raise ChildProcessError("Could not build the package for some reason!")
