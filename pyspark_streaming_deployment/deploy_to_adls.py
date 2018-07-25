import glob
import os

from azure.datalake.store import core, lib, multithread
from git import Repo


def main():
    repo = Repo(search_parent_directories=True)
    tag = next((tag for tag in repo.tags if tag.commit == repo.head.commit), None)
    branch = os.environ['BUILD_SOURCEBRANCHNAME']

    if tag:
        deploy_application_to_adls(tag)
    else:
        if branch == 'master':
            deploy_application_to_adls('SNAPSHOT')
        else:
            print(f'Not a release tag, nor master branch (branch = "{branch}". Not deploying')


def upload_to_adls(client, source: str, destination: str):
    print(f"""uploading artifact from
     | from ${source}
     | to ${destination}""")

    multithread.ADLUploader(client,
                            lpath=source,
                            rpath=destination,
                            overwrite=True)


def deploy_application_to_adls(version: str):
    print("Submitting job to databricks")

    azure_adls_name = os.environ['AZURE_ADLS_NAME']
    azure_sp_username = os.environ['AZURE_SP_USERNAME']
    azure_sp_password = os.environ['AZURE_SP_PASSWORD']
    azure_sp_tenantid = os.environ['AZURE_SP_TENANTID']
    build_definitionname = os.environ['BUILD_DEFINITIONNAME']

    adls_credentials = lib.auth(tenant_id=azure_sp_tenantid,
                                client_secret=azure_sp_password,
                                client_id=azure_sp_username,
                                resource='https://datalake.azure.net/')
    adls_client = core.AzureDLFileSystem(adls_credentials, store_name=azure_adls_name)

    eggs = glob.glob('/root/dist/*.egg')
    if len(eggs) != 1:
        raise FileNotFoundError(f'Eggs found: {eggs}; There can (and must) be only one!')

    egg = eggs[0]
    main = '/root/main/main.py'

    upload_to_adls(adls_client,
                   egg,
                   f'/libraries/{build_definitionname}/{build_definitionname}-{version}.egg')
    upload_to_adls(adls_client,
                   main,
                   f'/libraries/{build_definitionname}/{build_definitionname}-main-{version}.py')


if __name__ == '__main__':
    main()
