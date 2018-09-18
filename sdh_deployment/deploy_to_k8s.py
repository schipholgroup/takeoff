import logging
import os

from azure.mgmt.containerservice.container_service_client import ContainerServiceClient
from azure.mgmt.containerservice.models import CredentialResults
from kubernetes import client, config
from kubernetes.client.apis import ExtensionsV1beta1Api

from sdh_deployment.util import (
    SHARED_REGISTRY,
    get_subscription_id,
    get_azure_user_credentials,
    get_application_name
)
from sdh_deployment.run_deployment import ApplicationVersion

logger = logging.getLogger(__name__)


# assumes kubectl is available
class DeployToK8s:

    @staticmethod
    def _write_kube_config(credential_results: CredentialResults):
        kubeconfig = credential_results.kubeconfigs[0].value.decode(encoding='UTF-8')

        kubeconfig_dir = os.path.expanduser("~/.kube")

        # assumption here that there is no existing kubeconfig (which makes sense, given this script should be run in
        # a docker container ;-) )
        os.mkdir(kubeconfig_dir)
        with open(kubeconfig_dir + "/config", "w") as f:
            f.write(kubeconfig)

        logger.info("Kubeconfig successfully written")

    @staticmethod
    def _authenticate_with_k8s(dtap: str):
        resource_group = os.getenv('RESOURCE_GROUP', f'sdh{dtap}')
        k8s_name = os.getenv('K8S_RESOURCE_NAME', 'sdh-kubernetes')
        # get azure container service client
        credentials = get_azure_user_credentials(dtap)

        client = ContainerServiceClient(
            credentials=credentials,
            subscription_id=get_subscription_id()
        )

        # authenticate with k8s
        credential_results = client.managed_clusters.list_cluster_user_credentials(resource_group_name=resource_group,
                                                                                   resource_name=k8s_name)

        DeployToK8s._write_kube_config(credential_results)

    @staticmethod
    def _k8s_resource_exists(needle, haystack):
        # Helper method to abstract away checking for existence of a k8s entity
        # this assumes the k8s structure of entities (i.e. items->metadata->name
        for dep in haystack['items']:
            if dep['metadata']['name'] == needle:
                return True
        return False

    @staticmethod
    def _k8s_deployment_exists(deployment_name: str, namespace: str, api_instance: ExtensionsV1beta1Api) -> bool:
        existing_deployments = api_instance.list_namespaced_deployment(namespace=namespace).to_dict()
        return DeployToK8s._k8s_resource_exists(deployment_name, existing_deployments)

    @staticmethod
    def _k8s_namespace_exists(namespace: str, core_api_client):
        existing_namespaces = core_api_client.list_namespace().to_dict()
        return DeployToK8s._k8s_resource_exists(namespace, existing_namespaces)

    @staticmethod
    def _create_or_patch_namespace(k8s_namespace: str):
        # very simple way to ensure the namespace exists
        core_api_client = client.CoreV1Api()

        if not DeployToK8s._k8s_namespace_exists(k8s_namespace, core_api_client):
            logger.info(f"No k8s namespace for this application. Creating namespace: {k8s_namespace}")
            namespace_to_create = client.V1Namespace(metadata={"name": k8s_namespace})
            core_api_client.create_namespace(body=namespace_to_create)

    @staticmethod
    def _create_or_patch_deployment(deployment: dict, application_name: str, env: ApplicationVersion, k8s_namespace: str):
        api_instance = client.ExtensionsV1beta1Api()

        # set the right version
        deployment['spec']['template']['spec']['containers'][0]['image'] = "{registry}/{image}:{tag}".format(
            registry=SHARED_REGISTRY,
            image=application_name,
            tag=env.version
        )

        # to patch or not to patch
        if DeployToK8s._k8s_deployment_exists(application_name, k8s_namespace, api_instance):
            logger.info(f"Found existing k8s deployment: {application_name} in namespace {k8s_namespace}")
            api_instance.patch_namespaced_deployment(name=application_name,
                                                     namespace=k8s_namespace,
                                                     body=deployment)
        else:
            logger.info(f"No existing k8s deployment found, creating deployment: {application_name} in namespace {k8s_namespace}")
            api_instance.create_namespaced_deployment(namespace=k8s_namespace,
                                                      body=deployment)

    @staticmethod
    def deploy_to_k8s(env: ApplicationVersion, deploy_config: dict):
        application_name = get_application_name()
        k8s_namespace = f"{application_name}-{env.environment.lower()}"
        # 1: get kubernetes credentials with azure credentials for vsts user
        DeployToK8s._authenticate_with_k8s(env.environment)

        # load the kubeconfig we just fetched
        config.load_kube_config()

        # 2: verify that the namespace exists, if not: create it
        DeployToK8s._create_or_patch_namespace(k8s_namespace)

        # 2: create OR patch kubernetes deployment
        DeployToK8s._create_or_patch_deployment(deploy_config, application_name, env, k8s_namespace)
