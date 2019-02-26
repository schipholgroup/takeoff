import glob
import logging

from azure.storage.blob import BlockBlobService

from runway.ApplicationVersion import ApplicationVersion
from runway.DeploymentStep import DeploymentStep
from runway.credentials.application_name import ApplicationName
from runway.credentials.azure_storage_account import BlobStore

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
            container = self.config['runway_common']['artifacts_shared_blob_container_name']
        logger.info(
            f"""uploading artifact from
         | from ${source}
         | to ${destination}
         | in container {container}"""
        )

        client.create_blob_from_path(
            container_name=container, blob_name=destination, file_path=source
        )

    @staticmethod
    def _get_jar(lang: str) -> str:
        if lang == "sbt":
            jars = glob.glob("target/scala-2.*/*-assembly-*.jar")
        elif lang == "maven":
            jars = glob.glob("target/*-uber.jar")
        else:
            raise ValueError(f"Unknown language {lang}")

        if len(jars) != 1:
            raise FileNotFoundError(
                f"jars found: {jars}; There can (and must) be only one!"
            )

        return jars[0]

    @staticmethod
    def _get_egg():
        eggs = glob.glob("dist/*.egg")
        if len(eggs) != 1:
            raise FileNotFoundError(
                f"Eggs found: {eggs}; There can (and must) be only one!"
            )
        return eggs[0]

    def upload_application_to_blob(self):
        build_definition_name = ApplicationName().get(self.config)
        blob_service = BlobStore(self.vault_name, self.vault_client).service_client(self.config)

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
            egg = UploadToBlob._get_egg()
            self._upload_file_to_blob(blob_service, egg, filename_library)

            # only upload a py file if the path has been specified
            if 'python_file_path' in self.config.keys():
                filename_main = (
                    f"{build_definition_name}/{build_definition_name}-main-{self.env.artifact_tag}.py"
                )
                self._upload_file_to_blob(
                    blob_service, f"{self.config['python_file_path']}", filename_main
                )
