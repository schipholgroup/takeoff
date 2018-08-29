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
    def upload_application_to_blob(env: ApplicationVersion, config: dict):
        build_definition_name = get_application_name()
        blob_service = get_shared_blob_service()

        if 'lang' in config.keys() and config['lang'] in {'maven', 'sbt'}:
            lang = config['lang']
            if lang == 'sbt':
                jars = glob.glob('target/*-assembly-*.jar')
            elif lang == 'maven':
                jars = glob.glob('target/*-uber.jar')
            else:
                raise ValueError(f"Unknown language {lang}")

            if len(jars) != 1:
                raise FileNotFoundError(f'jars found: {jars}; There can (and must) be only one!')
            jar = jars[0]

            UploadToBlob._upload_file_to_blob(
                blob_service,
                jar,
                f'{build_definition_name}/{build_definition_name}-{env.version}.jar'
            )
        else:
            eggs = glob.glob('/root/dist/*.egg')
            if len(eggs) != 1:
                raise FileNotFoundError(f'Eggs found: {eggs}; There can (and must) be only one!')
            egg = eggs[0]
            main = '/root/main/main.py'

            UploadToBlob._upload_file_to_blob(
                blob_service,
                egg,
                f'{build_definition_name}/{build_definition_name}-{env.version}.egg'
            )
            UploadToBlob._upload_file_to_blob(
                blob_service,
                main,
                f'{build_definition_name}/{build_definition_name}-main-{env.version}.py'
            )
