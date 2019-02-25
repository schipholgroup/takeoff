import glob
import logging

from azure.storage.blob import BlockBlobService
from twine.commands.upload import upload

from runway.ApplicationVersion import ApplicationVersion
from runway.DeploymentStep import DeploymentStep
from runway.credentials.azure_devops_artifact_store import DevopsArtifactStore
from runway.credentials.azure_storage_account import BlobStore
from runway.util import get_tag, get_application_name


logger = logging.getLogger(__name__)


class PublishArtifact(DeploymentStep):
    def __init__(self, env: ApplicationVersion, config: dict):
        super().__init__(env, config)

    def run(self):
        if self.config["lang"] == "python":
            self.publish_python_package()
        elif self.config["lang"] in {"sbt", "maven"}:
            self.publish_jvm_package()

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
    def _get_wheel():
        wheels = glob.glob("/root/dist/*.whl")
        if len(wheels) != 1:
            raise FileNotFoundError(
                f"wheels found: {wheels}; There can (and must) be only one!"
            )
        return wheels[0]

    def publish_python_package(self):
        for target in self.config["target"]:
            if target == "pypi":
                self.publish_to_pypi()
            elif target == "blob":
                self.publish_to_blob(file=self._get_wheel(),
                                     file_ext=".whl")
                # only upload a py file if the path has been specified
                if 'python_file_path' in self.config.keys():
                    self.publish_to_blob(file=f"/root/{self.config['python_file_path']}",
                                         file_ext=".py")
            else:
                logging.info("Invalid target for artifact")

    def publish_jvm_package(self):
        for target in self.config["target"]:
            if target == "blob":
                self.publish_to_blob(file=self._get_jar(),
                                     file_ext=".jar")
            else:
                logging.info("Invalid target for artifact")

    def publish_to_blob(self, file, file_ext):
        build_definition_name = get_application_name()
        blob_service = BlobStore(self.vault_name, self.vault_client).service_client(self.config)
        # filename = f"{build_definition_name}/{file}"

        if file_ext == ".py":
            filename = (
                f"{build_definition_name}/{build_definition_name}-main-{self.env.artifact_tag}{file_ext}"
            )
        else:
            filename = (
                f"{build_definition_name}/{build_definition_name.replace('-', '_')}-{self.env.artifact_tag.replace('-', '_')}-py3-none-any{file_ext}"
                # f"{build_definition_name}/{build_definition_name}-{self.env.artifact_tag}-py3-none-any{file_ext}"
            )

        self._upload_file_to_blob(blob_service, file, filename)

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

    def publish_to_pypi(self):
        if get_tag():
            credentials = DevopsArtifactStore(vault_name=self.vault_name, vault_client=self.vault_client)\
                .store_settings(self.config)
            upload(upload_settings=credentials, dists=['/root/dist/*'])
        else:
            logging.info("Not on a release tag, not publishing artifact on pypi.")
