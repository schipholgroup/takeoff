import glob
import logging

import voluptuous as vol
from azure.storage.blob import BlockBlobService
from twine.commands.upload import upload

from takeoff.application_version import ApplicationVersion
from takeoff.azure.credentials.artifact_store import ArtifactStore
from takeoff.azure.credentials.keyvault import KeyVaultClient
from takeoff.azure.credentials.storage_account import BlobStore
from takeoff.schemas import TAKEOFF_BASE_SCHEMA
from takeoff.step import Step
from takeoff.util import get_tag, get_whl_name, get_main_py_name, get_jar_name, run_shell_command

logger = logging.getLogger(__name__)


def language_must_match_target(fields):
    """Checks if incompatible lang/targets are used.

    SBT jars cannot be pushed to PyPi and Python wheels cannot be pushed to ivy repositories.
    """
    if "scala" == fields["language"] and "pypi" in fields["target"]:
        raise vol.Invalid("Cannot publish jars to PyPi")
    elif "python" == fields["language"] and "ivy" in fields["target"]:
        raise vol.Invalid("Cannot publish wheels to Ivy")
    return fields


SCHEMA = vol.All(
    TAKEOFF_BASE_SCHEMA,
    vol.Schema(
        vol.All(
            {
                vol.Required("task"): "publish_artifact",
                vol.Required("language", description="Programming language artifact was built in."): vol.All(
                    str, vol.In(["python", "scala"])
                ),
                vol.Required("target", description="List of targets to publish the artifact to"): vol.All(
                    [str, vol.In(["cloud_storage", "pypi", "ivy"])]
                ),
                vol.Optional(
                    "python_file_path",
                    description=(
                        "The path relative to the root of your project to the python script"
                        "that serves as entrypoint for a databricks job"
                    ),
                ): str,
                "azure": vol.All(
                    {
                        "common": {
                            vol.Optional(
                                "artifacts_shared_storage_account_container_name",
                                description="The container for a shared storage account",
                            ): str
                        }
                    }
                ),
            },
            language_must_match_target,
        ),
        extra=vol.ALLOW_EXTRA,
    ),
)


class PublishArtifact(Step):
    """Publish a prebuilt artifact.

    Credentials for an artifact store / PyPi (username, password) must be
    available in your cloud vault when pushing to any PyPi artifact store.

    When publishing to Azure Storage Account credentials to the account must be available, such
    as (account_name, account_key) or (sas_token).
    """

    def __init__(self, env: ApplicationVersion, config: dict):
        super().__init__(env, config)
        self.vault_name, self.vault_client = KeyVaultClient.vault_and_client(self.config, self.env)

    def run(self):
        if self.config["language"] == "python":
            self.publish_python_package()
        elif self.config["language"] in {"scala"}:
            self.publish_jvm_package()

    def schema(self) -> vol.Schema:
        return SCHEMA

    @staticmethod
    def _get_jar() -> str:
        """Finds the jar given default naming conventions for Scala-SBT

        Returns:
            The name of the jar in the target/scala-2.*/ folder

        Raises:
            FileNotFoundError if none or more than one jars are present.
        """
        jars = glob.glob("target/scala-2.*/*-assembly-*.jar")
        if len(jars) != 1:
            raise FileNotFoundError(f"jars found: {jars}; There can (and must) be only one!")

        return jars[0]

    @staticmethod
    def _get_wheel() -> str:
        """Finds the wheel given default naming conventions for Python setuptools

        Returns:
            The name of the wheel in the dist/ folder

        Raises:
            FileNotFoundError if none or more than one jars are present.
        """
        wheels = glob.glob("dist/*.whl")
        if len(wheels) != 1:
            raise FileNotFoundError(f"wheels found: {wheels}; There can (and must) be only one!")
        return wheels[0]

    def publish_python_package(self):
        """Publishes the Python wheel to all specified targets"""
        for target in self.config["target"]:
            if target == "pypi":
                self.publish_to_pypi()
            elif target == "cloud_storage":
                self.upload_to_cloud_storage(file=self._get_wheel(), file_extension=".whl")
                # only upload a py file if the path has been specified
                if "python_file_path" in self.config.keys():
                    self.upload_to_cloud_storage(
                        file=f"{self.config['python_file_path']}", file_extension=".py"
                    )
            else:
                logging.info("Invalid target for artifact")

    def publish_jvm_package(self):
        """Publishes the jar to all specified targets"""
        for target in self.config["target"]:
            if target == "cloud_storage":
                self.upload_to_cloud_storage(file=self._get_jar(), file_extension=".jar")
            elif target == "ivy":
                self.publish_to_ivy()
            else:
                logging.info("Invalid target for artifact")

    def upload_to_cloud_storage(self, file: str, file_extension: str):
        """
        Args:
            file: Name of file
            file_extension: Extension of the file, prefixed with `.`

        Raises:
            ValueError if the filetype is not supported.
        """
        blob_service = BlobStore(self.vault_name, self.vault_client).service_client(self.config)

        if file_extension == ".py":
            filename = get_main_py_name(self.application_name, self.env.artifact_tag, file_extension)
        elif file_extension == ".whl":
            filename = get_whl_name(self.application_name, self.env.artifact_tag, file_extension)
        elif file_extension == ".jar":
            filename = get_jar_name(self.application_name, self.env.artifact_tag, file_extension)
        else:
            raise ValueError(f"Unsupported filetype extension: {file_extension}")

        self._upload_file_to_azure_storage_account(blob_service, file, filename)

    def _upload_file_to_azure_storage_account(
        self, client: BlockBlobService, source: str, destination: str, container: str = None
    ):
        """Upload the file to the specified Azure Storage Account.

        Assumption is that any cloud environment has access to a shared repository of artifacts.

        Args:
            client: Azure Storage Account client
            destination: Name of the file
            container: Name of the container the file should be uploaded to
        """
        if not container:
            container = self.config["azure"]["common"]["artifacts_shared_storage_account_container_name"]
        logger.info(
            f"""uploading artifact from
             | from ${source}
             | to ${destination}
             | in container {container}"""
        )

        client.create_blob_from_path(container_name=container, blob_name=destination, file_path=source)

    def publish_to_pypi(self):
        """Uses `twine` to upload to PyPi"""
        if get_tag():
            credentials = ArtifactStore(
                vault_name=self.vault_name, vault_client=self.vault_client
            ).store_settings(self.config)
            upload(upload_settings=credentials, dists=["dist/*"])
        else:
            logging.info("Not on a release tag, not publishing artifact on PyPi.")

    def publish_to_ivy(self):
        """Uses `sbt` to upload to Ivy.

        The jar will be build as a result of calling `sbt publish`. This means a prebuilt
        artifact is NOT required to publish to Ivy. This will be a lean jar, containing
        only project code, no dependencies.

        This uses bash to run commands directly.

        Raises:
           ChildProcessError is the bash command was not successful
        """
        version = self.env.artifact_tag
        postfix = "-SNAPSHOT" if not get_tag() else ""
        cmd = ["sbt", f'set version := "{version}{postfix}"', "publish"]
        return_code, _ = run_shell_command(cmd)

        if return_code != 0:
            raise ChildProcessError("Could not publish the package for some reason!")
