import logging
import shutil

import voluptuous as vol

from takeoff.application_version import ApplicationVersion
from takeoff.schemas import TAKEOFF_BASE_SCHEMA
from takeoff.step import Step
from takeoff.util import run_shell_command

logger = logging.getLogger(__name__)

SCHEMA = TAKEOFF_BASE_SCHEMA.extend(
    {
        vol.Required("task"): "build_artifact",
        vol.Required("build_tool"): vol.All(str, vol.In(["python", "sbt"])),
        vol.Optional(
            "python_package_root",
            default="",
            description="(Optional) relative path to root of python package, defaults to top-level directory.",
        ): str,
    },
    extra=vol.ALLOW_EXTRA,
)


class BuildArtifact(Step):
    def __init__(self, env: ApplicationVersion, config: dict):
        """Build an artifact"""
        super().__init__(env, config)

    def run(self):
        if self.config["build_tool"] == "python":
            self.build_python_wheel()
        elif self.config["build_tool"] == "sbt":
            self.build_sbt_assembly_jar()

    def schema(self) -> vol.Schema:
        return SCHEMA

    def _write_version(self):
        """First make sure the correct version number is used."""
        with open("version.py", "w+") as f:
            f.write(f"__version__='{self.env.version}'")

    @staticmethod
    def _remove_old_artifacts(path: str):
        """Ensure any old artifacts are gone

        Args:
            path: absolute or relative path to folder containing artifacts
        """
        shutil.rmtree(path, ignore_errors=True)

    def build_python_wheel(self, package_root="./"):
        """Builds Python wheel

        This uses bash to run commands directly.

        Raises:
           ChildProcessError is the bash command was not successful
        """

        self._write_version()
        package_root = self.config["python_package_root"]
        self._remove_old_artifacts(f"{package_root}dist/")

        cmd = ["python", "setup.py", "bdist_wheel"]
        return_code, _ = run_shell_command(cmd, cwd=package_root)

        if return_code != 0:
            raise ChildProcessError("Could not build the package for some reason!")

    def build_sbt_assembly_jar(self):
        """Builds an SBT assembly jar

        This uses bash to run commands directly.

        Raises:
           ChildProcessError is the bash command was not successful
        """
        self._remove_old_artifacts("target/")

        cmd = ["sbt", "clean", "assembly"]
        return_code, _ = run_shell_command(cmd)

        if return_code != 0:
            raise ChildProcessError("Could not build the package for some reason!")
