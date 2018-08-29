import glob

from azure.storage.blob import BlockBlobService

from pyspark_streaming_deployment.util import get_application_name, get_shared_blob_service

BLOB_CONTAINER_NAME = 'libraries'


def __upload_file_to_blob(client: BlockBlobService, source: str, destination: str):
    print(f"""uploading artifact from
     | from ${source}
     | to ${destination}""")

    client.create_blob_from_path(
        container_name=BLOB_CONTAINER_NAME,
        blob_name=destination,
        file_path=source)


def upload_application_to_blob(version: str, _: str):
    build_definitionname = get_application_name()
    blob_service = get_shared_blob_service()

    eggs = glob.glob('/root/dist/*.egg')
    if len(eggs) != 1:
        raise FileNotFoundError(f'Eggs found: {eggs}; There can (and must) be only one!')

    egg = eggs[0]
    main = '/root/main/main.py'

    __upload_file_to_blob(blob_service,
                          egg,
                          f'/libraries/{build_definitionname}/{build_definitionname}-{version}.egg')
    __upload_file_to_blob(blob_service,
                          main,
                          f'/libraries/{build_definitionname}/{build_definitionname}-main-{version}.py')
