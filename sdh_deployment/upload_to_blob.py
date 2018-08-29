import glob
import logging
from azure.storage.blob import BlockBlobService

from sdh_deployment.util import get_application_name, get_shared_blob_service
from sdh_deployment.run_deployment import ApplicationVersion

BLOB_CONTAINER_NAME = 'libraries'

logger = logging.getLogger(__name__)


class UploadToBlob:

    @staticmethod
    def _upload_file_to_blob(client: BlockBlobService, source: str, destination: str):
        logger.info(f"""uploading artifact from
         | from ${source}
         | to ${destination}""")

        client.create_blob_from_path(
            container_name=BLOB_CONTAINER_NAME,
            blob_name=destination,
            file_path=source)

    @staticmethod
    def _get_jar(lang: str) -> str:
        if lang == 'sbt':
            jars = glob.glob('/root/target/*-assembly-*.jar')
        elif lang == 'maven':
            jars = glob.glob('/root/target/*-uber.jar')
        else:
            raise ValueError(f"Unknown language {lang}")

        if len(jars) != 1:
            raise FileNotFoundError(f'jars found: {jars}; There can (and must) be only one!')

        return jars[0]

    @staticmethod
    def _get_egg():
        eggs = glob.glob('/root/dist/*.egg')
        if len(eggs) != 1:
            raise FileNotFoundError(f'Eggs found: {eggs}; There can (and must) be only one!')
        return eggs[0]

    @staticmethod
    def upload_application_to_blob(env: ApplicationVersion, config: dict):
        build_definition_name = get_application_name()
        blob_service = get_shared_blob_service()

        filename_library = f'{build_definition_name}/{build_definition_name}-{env.version}'

        if 'lang' in config.keys() and config['lang'] in {'maven', 'sbt'}:
            # it's a jar!
            filename_library += '.jar'
            jar = UploadToBlob._get_jar(config['lang'])
            UploadToBlob._upload_file_to_blob(
                blob_service,
                jar,
                filename_library
            )
        else:
            # it's an egg!
            filename_library += '.egg'
            filename_main = f'{build_definition_name}/{build_definition_name}-main-{env.version}.py'

            egg = UploadToBlob._get_egg()
            UploadToBlob._upload_file_to_blob(
                blob_service,
                egg,
                filename_library
            )
            UploadToBlob._upload_file_to_blob(
                blob_service,
                '/root/main/main.py',
                filename_main
            )
