import logging
import os

import yaml
from azure.mgmt.containerservice.container_service_client import ContainerServiceClient
from azure.mgmt.containerservice.models import CredentialResults
from kubernetes import client, config
from kubernetes.client import CoreV1Api
from kubernetes.client.apis import ExtensionsV1beta1Api

from sdh_deployment.ApplicationVersion import ApplicationVersion
from sdh_deployment.DeploymentStep import DeploymentStep
from sdh_deployment.util import (
    get_subscription_id,
    get_azure_user_credentials,
    get_application_name,
    render_file_with_jinja
)

logger = logging.getLogger(__name__)


# assumes kubectl is available
class DeployToK8s(DeploymentStep):
    def __init__(self, env: ApplicationVersion, config: dict):
        super().__init__(env, config)

    def run(self):
        # get the ip address for this environment
        service_ip = self.config["service_ips"][self.env.environment.lower()]

        # load some k8s config
        k8s_deployment = render_file_with_jinja(self.config["deployment_config_path"], {"docker_tag": self.env.docker_tag}, yaml.load)
        k8s_service = render_file_with_jinja(self.config["service_config_path"], {"service_ip": service_ip}, yaml.load)

        logging.info(f"Deploying to K8S. Environment: {self.env.environment}")

        self.deploy_to_k8s(deployment_config=k8s_deployment,
                           service_config=k8s_service)

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

    def _authenticate_with_k8s(self):
        resource_group = os.getenv('RESOURCE_GROUP', f'sdh{self.env.environment}')
        k8s_name = os.getenv('K8S_RESOURCE_NAME', 'sdh-kubernetes')

        # get azure container service client
        # For now, get the prd credentials by default, because we only have a single k8s cluster now
        credentials = get_azure_user_credentials(os.getenv('AZURE_CREDENTIALS_ENV', 'prd'))

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
    def _k8s_deployment_exists(deployment_name: str, namespace: str, api_client: ExtensionsV1beta1Api) -> bool:
        existing_deployments = api_client.list_namespaced_deployment(namespace=namespace).to_dict()
        return DeployToK8s._k8s_resource_exists(deployment_name, existing_deployments)

    @staticmethod
    def _k8s_namespace_exists(namespace: str, api_client: CoreV1Api):
        existing_namespaces = api_client.list_namespace().to_dict()
        return DeployToK8s._k8s_resource_exists(namespace, existing_namespaces)

    @staticmethod
    def _k8s_service_exists(service_name: str, namespace: str, api_client: CoreV1Api):
        existing_services = api_client.list_namespaced_service(namespace=namespace).to_dict()
        return DeployToK8s._k8s_resource_exists(service_name, existing_services)

    @staticmethod
    def _create_namespace_if_not_exists(api_client: CoreV1Api, k8s_namespace: str):
        # very simple way to ensure the namespace exists
        if not DeployToK8s._k8s_namespace_exists(k8s_namespace, api_client):
            logger.info(f"No k8s namespace for this application. Creating namespace: {k8s_namespace}")
            namespace_to_create = client.V1Namespace(metadata={"name": k8s_namespace})
            api_client.create_namespace(body=namespace_to_create)

    @staticmethod
    def _create_or_patch_service(api_client: CoreV1Api, service_config: dict, k8s_namespace: str):
        service_name = service_config['metadata']['name']
        if DeployToK8s._k8s_service_exists(service_name, k8s_namespace, api_client):
            # we need to patch the existing service
            logger.info(f"Found existing k8s service: {service_name} in namespace {k8s_namespace}")
            api_client.patch_namespaced_service(name=service_name,
                                                namespace=k8s_namespace,
                                                body=service_config)
        else:
            # the service doesn't exist, we need to create it
            logger.info(f"No existing k8s service found, creating service: {service_name} in namespace {k8s_namespace}")
            api_client.create_namespaced_service(namespace=k8s_namespace,
                                                 body=service_config)

    def _create_or_patch_deployment(self, deployment: dict, application_name: str, k8s_namespace: str):
        api_instance = client.ExtensionsV1beta1Api()
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

    def deploy_to_k8s(self, deployment_config: dict, service_config: dict):
        application_name = get_application_name()
        k8s_namespace = f"{application_name}-{self.env.environment.lower()}"

        # 1: get kubernetes credentials with azure credentials for vsts user
        self._authenticate_with_k8s()

        # load the kubeconfig we just fetched
        config.load_kube_config()
        logger.info("Kubeconfig loaded")

        # create the core api client
        core_api_client = CoreV1Api()

        # 2: verify that the namespace exists, if not: create it
        self._create_namespace_if_not_exists(core_api_client, k8s_namespace)

        # 3: create OR patch kubernetes deployment
        self._create_or_patch_deployment(deployment_config, application_name, k8s_namespace)

        # 4: create OR patch kubernetes service
        self._create_or_patch_service(core_api_client, service_config, k8s_namespace)
