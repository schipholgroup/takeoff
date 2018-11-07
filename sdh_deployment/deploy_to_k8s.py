import base64
import logging
import os

import yaml
from azure.mgmt.containerservice.container_service_client import ContainerServiceClient
from azure.mgmt.containerservice.models import CredentialResults
from kubernetes import client, config
from kubernetes.client import CoreV1Api

from sdh_deployment.ApplicationVersion import ApplicationVersion
from sdh_deployment.DeploymentStep import DeploymentStep
from sdh_deployment.KeyVaultSecrets import KeyVaultSecrets
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
        k8s_deployment = render_file_with_jinja(self.config["deployment_config_path"],
                                                {"docker_tag": self.env.artifact_tag},
                                                yaml.load)
        k8s_service = render_file_with_jinja(self.config["service_config_path"],
                                             {"service_ip": service_ip},
                                             yaml.load)

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

        self._write_kube_config(credential_results)

    @staticmethod
    def _find_needle(needle, haystack):
        # Helper method to abstract away checking for existence of a k8s entity
        # this assumes the k8s structure of entities (i.e. items->metadata->name
        for dep in haystack['items']:
            if dep['metadata']['name'] == needle:
                return True
        return False

    def _k8s_resource_exists(self, resource_name, namespace, list_function):
        existing_services = list_function(namespace=namespace).to_dict()
        return self._find_needle(resource_name, existing_services)

    def _k8s_namespace_exists(self, namespace: str, api_client: CoreV1Api):
        existing_namespaces = api_client.list_namespace().to_dict()
        return DeployToK8s._find_needle(namespace, existing_namespaces)

    def _create_namespace_if_not_exists(self, api_client: CoreV1Api, k8s_namespace: str):
        # very simple way to ensure the namespace exists
        if not self._k8s_namespace_exists(k8s_namespace, api_client):
            logger.info(f"No k8s namespace for this application. Creating namespace: {k8s_namespace}")
            namespace_to_create = client.V1Namespace(metadata={"name": k8s_namespace})
            api_client.create_namespace(body=namespace_to_create)

    def _create_or_patch_resource(self,
                                  client,
                                  resource_type: str,
                                  name: str,
                                  namespace: str,
                                  resource_config: dict):
        list_function = getattr(client, f'list_namespaced_{resource_type}')
        patch_function = getattr(client, f'patch_namespaced_{resource_type}')
        create_function = getattr(client, f'create_namespaced_{resource_type}')

        if self._k8s_resource_exists(name, namespace, list_function):
            # we need to patch the existing resource
            logger.info(f"Found existing k8s resource: {name} in namespace {namespace}")
            patch_function(name=name,
                           namespace=namespace,
                           body=resource_config)
        else:
            # the resource doesn't exist, we need to create it
            logger.info(f"No existing k8s resource found, creating resource: {name} in namespace {namespace}")
            create_function(namespace=namespace,
                            body=resource_config)

    def _create_or_patch_service(self, api_client: CoreV1Api, service_config: dict, k8s_namespace: str):
        service_name = service_config['metadata']['name']
        self._create_or_patch_resource(
            client=CoreV1Api(),
            resource_type="service",
            name=service_name,
            namespace=k8s_namespace,
            resource_config=service_config
        )

    def _create_or_patch_deployment(self, deployment: dict, k8s_namespace: str):
        api_instance = client.ExtensionsV1beta1Api()
        self._create_or_patch_resource(
            client=api_instance,
            resource_type="deployment",
            name=get_application_name(),
            namespace=k8s_namespace,
            resource_config=deployment
        )

    def _create_or_patch_secrets(self, k8s_namespace):
        secrets = KeyVaultSecrets.get_keyvault_secrets(self.env.environment)
        api_instance = client.CoreV1Api()
        application_name = get_application_name()
        secret_name = f"{application_name}-secret"

        secret = client.V1Secret(metadata=client.V1ObjectMeta(name=secret_name),
                                 type="Opaque",
                                 data={_.env_key: base64.b64encode(_.val) for _ in secrets})

        self._create_or_patch_resource(
            client=api_instance,
            resource_type="secret",
            name=get_application_name(),
            namespace=k8s_namespace,
            resource_config=secret.to_dict()
        )

    def deploy_to_k8s(self, deployment_config: dict, service_config: dict):
        k8s_namespace = f"{application_name}-{self.env.environment.lower()}"

        application_name = get_application_name()

        # 1: get kubernetes credentials with azure credentials for vsts user
        self._authenticate_with_k8s()

        # load the kubeconfig we just fetched
        config.load_kube_config()
        logger.info("Kubeconfig loaded")

        # create the core api client
        core_api_client = CoreV1Api()

        # 2: verify that the namespace exists, if not: create it
        self._create_namespace_if_not_exists(core_api_client, k8s_namespace)

        # 3: create kubernetes secrets from azure keyvault
        self._create_or_patch_secrets(k8s_namespace)

        # 4: create OR patch kubernetes deployment
        self._create_or_patch_deployment(deployment_config, k8s_namespace)

        # 5: create OR patch kubernetes service
        self._create_or_patch_service(core_api_client, service_config, k8s_namespace)
