import glob
import logging

from azure.storage.blob import BlockBlobService

from runway.ApplicationVersion import ApplicationVersion
from runway.DeploymentStep import DeploymentStep
from runway.credentials.azure_keyvault import AzureKeyvaultClient
from runway.credentials.azure_storage_account import BlobStore
from runway.util import get_application_name

logger = logging.getLogger(__name__)


class UploadToBlob(DeploymentStep):
    def __init__(self, env: ApplicationVersion, config: dict):
        super().__init__(env, config)

    def run(self):
        self.upload_application_to_blob()

    def _upload_file_to_blob(self,
                             client: BlockBlobService,
                             source: str,
                             destination: str,
                             container: str = None):
        if not container:
            container = self.config['runway_common_keys']['artifacts_shared_blob_container_name']
        logger.info(
            f"""uploading artifact from
         | from ${source}
         | to ${destination}"""
        )

        client.create_blob_from_path(
            container_name=container, blob_name=destination, file_path=source
        )

    @staticmethod
    def _get_jar(lang: str) -> str:
        if lang == "sbt":
            jars = glob.glob("/root/target/scala-2.*/*-assembly-*.jar")
        elif lang == "maven":
            jars = glob.glob("/root/target/*-uber.jar")
        else:
            raise ValueError(f"Unknown language {lang}")

        if len(jars) != 1:
            raise FileNotFoundError(
                f"jars found: {jars}; There can (and must) be only one!"
            )

        return jars[0]

    @staticmethod
    def _get_egg():
        eggs = glob.glob("/root/dist/*.egg")
        if len(eggs) != 1:
            raise FileNotFoundError(
                f"Eggs found: {eggs}; There can (and must) be only one!"
            )
        return eggs[0]

    def upload_application_to_blob(self):
        build_definition_name = get_application_name()
        blob_service = BlobStore(*AzureKeyvaultClient.credentials(self.config, self.env)).credentials(self.config)

        filename_library = (
            f"{build_definition_name}/{build_definition_name}-{self.env.artifact_tag}"
        )

        if "lang" in self.config.keys() and self.config["lang"] in {"maven", "sbt"}:
            # it's a jar!
            filename_library += ".jar"
            jar = UploadToBlob._get_jar(self.config["lang"])
            self._upload_file_to_blob(blob_service, jar, filename_library)
        else:
            # it's an egg!
            filename_library += ".egg"
            filename_main = (
                f"{build_definition_name}/{build_definition_name}-main-{self.env.artifact_tag}.py"
            )

            egg = UploadToBlob._get_egg()
            self._upload_file_to_blob(blob_service, egg, filename_library)
            self._upload_file_to_blob(
                blob_service, "/root/main/main.py", filename_main
            )
