import glob
import logging
from azure.storage.blob import BlockBlobService

from sdh_deployment.util import get_application_name, get_shared_blob_service

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
    def upload_application_to_blob(version: str, _: str):
        build_definitionname = get_application_name()
        blob_service = get_shared_blob_service()

        eggs = glob.glob('/root/dist/*.egg')
        if len(eggs) != 1:
            raise FileNotFoundError(f'Eggs found: {eggs}; There can (and must) be only one!')

        egg = eggs[0]
        main = '/root/main/main.py'

        UploadToBlob._upload_file_to_blob(
            blob_service,
            egg,
            f'{build_definitionname}/{build_definitionname}-{version}.egg'
        )
        UploadToBlob._upload_file_to_blob(
            blob_service,
            main,
            f'{build_definitionname}/{build_definitionname}-main-{version}.py'
        )
