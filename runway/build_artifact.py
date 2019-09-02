import logging
import shutil

from runway.ApplicationVersion import ApplicationVersion
from runway.DeploymentStep import DeploymentStep
from runway.schemas import RUNWAY_BASE_SCHEMA
from runway.util import run_bash_command
import voluptuous as vol

logger = logging.getLogger(__name__)

SCHEMA = RUNWAY_BASE_SCHEMA.extend(
    {
        vol.Required("task"): vol.All(str, vol.Match(r"buildArtifact")),
        vol.Required("lang"): vol.All(str, vol.In(["python", "sbt"])),
    },
    extra=vol.ALLOW_EXTRA,
)


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

    def build_python_wheel(self):
        # First make sure the correct version number is used.
        with open("version.py", "w+") as f:
            f.write(f"__version__='{self.env.version}'")
        # ensure any old artifacts are gone
        shutil.rmtree("dist/", ignore_errors=True)

        cmd = ["python", "setup.py", "bdist_wheel"]
        return_code = run_bash_command(cmd)

        if return_code != 0:
            raise ChildProcessError("Could not build the package for some reason!")

    def build_sbt_assembly_jar(self):
        # ensure any old artifacts are gone
        shutil.rmtree("target/", ignore_errors=True)

        cmd = ["sbt", "clean", "assembly"]
        return_code = run_bash_command(cmd)

        if return_code != 0:
            raise ChildProcessError("Could not build the package for some reason!")
