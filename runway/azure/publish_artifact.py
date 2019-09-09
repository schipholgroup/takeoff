import glob
import logging

import voluptuous as vol
from azure.storage.blob import BlockBlobService
from twine.commands.upload import upload

from runway.application_version import ApplicationVersion
from runway.azure.credentials.artifact_store import ArtifactStore
from runway.azure.credentials.storage_account import BlobStore
from runway.credentials.application_name import ApplicationName
from runway.schemas import RUNWAY_BASE_SCHEMA
from runway.step import Step
from runway.util import get_tag, get_whl_name, get_main_py_name, get_jar_name, run_bash_command

logger = logging.getLogger(__name__)


def lang_must_match_target(fields):
    if "sbt" == fields["lang"] and "pypi" in fields["target"]:
        raise vol.Invalid("Cannot publish jars to pypi")
    elif "python" == fields["lang"] and "ivy" in fields["target"]:
        raise vol.Invalid("Cannot publish wheels to ivy")
    return fields


SCHEMA = vol.All(
    RUNWAY_BASE_SCHEMA,
    vol.Schema(
        vol.All(
            {
                vol.Required("task"): "publishArtifact",
                vol.Required("lang"): vol.All(str, vol.In(["python", "sbt"])),
                vol.Required("target"): vol.All([str, vol.In(["blob", "pypi", "ivy"])]),
                vol.Optional(
                    "python_file_path",
                    description=(
                        "The path relative to the root of your project to the python script"
                        "that serves as entrypoint for a databricks job"
                    ),
                ): str,
            },
            lang_must_match_target,
        ),
        extra=vol.ALLOW_EXTRA,
    ),
)


class PublishArtifact(Step):
    def __init__(self, env: ApplicationVersion, config: dict):
        super().__init__(env, config)

    def run(self):
        if self.config["lang"] == "python":
            self.publish_python_package()
        elif self.config["lang"] in {"sbt"}:
            self.publish_jvm_package()

    def schema(self) -> vol.Schema:
        return SCHEMA

    @staticmethod
    def _get_jar() -> str:
        jars = glob.glob("target/scala-2.*/*-assembly-*.jar")
        if len(jars) != 1:
            raise FileNotFoundError(f"jars found: {jars}; There can (and must) be only one!")

        return jars[0]

    @staticmethod
    def _get_wheel():
        wheels = glob.glob("dist/*.whl")
        if len(wheels) != 1:
            raise FileNotFoundError(f"wheels found: {wheels}; There can (and must) be only one!")
        return wheels[0]

    def publish_python_package(self):
        for target in self.config["target"]:
            if target == "pypi":
                self.publish_to_pypi()
            elif target == "blob":
                self.publish_to_blob(file=self._get_wheel(), file_ext=".whl")
                # only upload a py file if the path has been specified
                if "python_file_path" in self.config.keys():
                    self.publish_to_blob(file=f"{self.config['python_file_path']}", file_ext=".py")
            else:
                logging.info("Invalid target for artifact")

    def publish_jvm_package(self):
        for target in self.config["target"]:
            if target == "blob":
                self.publish_to_blob(file=self._get_jar(), file_ext=".jar")
            elif target == "ivy":
                self.publish_to_ivy()
            else:
                logging.info("Invalid target for artifact")

    def publish_to_blob(self, file, file_ext):
        blob_service = BlobStore(self.vault_name, self.vault_client).service_client(self.config)

        build_definition_name = ApplicationName().get(self.config)
        if file_ext == ".py":
            filename = get_main_py_name(build_definition_name, self.env.artifact_tag, file_ext)
        elif file_ext == ".whl":
            filename = get_whl_name(build_definition_name, self.env.artifact_tag, file_ext)
        elif file_ext == ".jar":
            filename = get_jar_name(build_definition_name, self.env.artifact_tag, file_ext)
        else:
            raise ValueError(f"Unsupported filetype extension: {file_ext}")

        self._upload_file_to_blob(blob_service, file, filename)

    def _upload_file_to_blob(
        self, client: BlockBlobService, source: str, destination: str, container: str = None
    ):
        if not container:
            container = self.config["azure"]["common"]["artifacts_shared_blob_container_name"]
        logger.info(
            f"""uploading artifact from
             | from ${source}
             | to ${destination}
             | in container {container}"""
        )

        client.create_blob_from_path(container_name=container, blob_name=destination, file_path=source)

    def publish_to_pypi(self):
        if get_tag():
            credentials = ArtifactStore(
                vault_name=self.vault_name, vault_client=self.vault_client
            ).store_settings(self.config)
            upload(upload_settings=credentials, dists=["dist/*"])
        else:
            logging.info("Not on a release tag, not publishing artifact on pypi.")

    def publish_to_ivy(self):
        version = self.env.artifact_tag
        postfix = "-SNAPSHOT" if not get_tag() else ""
        cmd = ["sbt", f'set version := "{version}{postfix}"', "publish"]
        run_bash_command(cmd)
