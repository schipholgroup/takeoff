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

K8S_NAMESPACE = os.getenv('K8S_NAMESPACE', 'default')


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
    def _k8s_deployment_exists(deployment_name: str, namespace: str, api_instance: ExtensionsV1beta1Api) -> bool:
        existing_deployments = api_instance.list_namespaced_deployment(namespace=namespace).to_dict()

        for dep in existing_deployments['items']:
            if dep['metadata']['name'] == deployment_name:
                return True
        return False

    @staticmethod
    def _create_or_patch_deployment(deployment: dict, deployment_name: str, env: ApplicationVersion):
        api_instance = client.ExtensionsV1beta1Api()

        # set the right version
        deployment['spec']['template']['spec']['containers'][0]['image'] = "{registry}/{image}:{tag}".format(
            registry=SHARED_REGISTRY,
            image=deployment_name,
            tag=env.version
        )

        # to patch or not to patch
        if DeployToK8s._k8s_deployment_exists(deployment_name, K8S_NAMESPACE, api_instance):
            logger.info(f"Found existing k8s deployment: {deployment_name}")
            api_instance.patch_namespaced_deployment(name=deployment_name,
                                                     namespace=K8S_NAMESPACE,
                                                     body=deployment)
        else:
            logger.info(f"No existing k8s deployment found, creating deployment: {deployment_name}")
            api_instance.create_namespaced_daemon_set(name=deployment_name,
                                                      namespace=K8S_NAMESPACE,
                                                      body=deployment)

    @staticmethod
    def deploy_to_k8s(env: ApplicationVersion, deploy_config: dict):
        # 1: get kubernetes credentials with azure credentials for vsts user
        DeployToK8s._authenticate_with_k8s(env.environment)

        # load the kubeconfig we just fetched
        config.load_kube_config()

        # 2: create OR patch kubernetes deployment
        DeployToK8s._create_or_patch_deployment(deploy_config, get_application_name(), env)
