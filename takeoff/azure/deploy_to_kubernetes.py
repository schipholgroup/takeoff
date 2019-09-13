import json
import logging
import os
from pprint import pprint
from typing import Callable, List, Union

import kubernetes
import voluptuous as vol
import yaml
from azure.mgmt.containerservice.container_service_client import ContainerServiceClient
from azure.mgmt.containerservice.models import CredentialResults
from kubernetes.client import CoreV1Api, ExtensionsV1beta1Api

from takeoff.application_version import ApplicationVersion
from takeoff.azure.credentials.KeyVaultCredentialsMixin import KeyVaultCredentialsMixin
from takeoff.azure.credentials.active_directory_user import ActiveDirectoryUserCredentials
from takeoff.azure.credentials.container_registry import DockerRegistry
from takeoff.azure.credentials.subscription_id import SubscriptionId
from takeoff.azure.util import get_resource_group_name, get_kubernetes_name
from takeoff.credentials.Secret import Secret
from takeoff.credentials.application_name import ApplicationName
from takeoff.schemas import TAKEOFF_BASE_SCHEMA
from takeoff.step import Step
from takeoff.util import render_file_with_jinja, b64_encode

logger = logging.getLogger(__name__)


class BaseKubernetes(Step):
    """Base Kubernetes class

    This class is used by the two Kubernetes steps: deploy_to_kubernetes and kubernetes_image_rolling_update.
    It handles the authentication to the specified Kubernetes cluster

    Depends on:
    - Credentials for the kubernetes cluster (username, password) must be available in your cloud vault
    """

    def __init__(self, env: ApplicationVersion, config: dict):
        super().__init__(env, config)

    @staticmethod
    def _write_kube_config(credential_results: CredentialResults):
        """Creates ~/.kube/config and writes the credentials for the kubernetes cluster to the file

        Args:
            credential_results: the cluster credentials for the cluster
        """
        kubeconfig = credential_results.kubeconfigs[0].value.decode(encoding="UTF-8")

        kubeconfig_dir = os.path.expanduser("~/.kube")

        # assumption here that there is no existing kubeconfig (which makes sense, given this script should
        # be run in a docker container ;-) )
        os.mkdir(kubeconfig_dir)
        with open(kubeconfig_dir + "/config", "w") as f:
            f.write(kubeconfig)

        logger.info("Kubeconfig successfully written")

    def _authenticate_with_kubernetes(self):
        """Authenticate with the defined AKS cluster and write the configuration to a file"""
        resource_group = get_resource_group_name(self.config, self.env)
        cluster_name = get_kubernetes_name(self.config, self.env)

        # get azure container service client
        credentials = ActiveDirectoryUserCredentials(
            vault_name=self.vault_name, vault_client=self.vault_client
        ).credentials(self.config)

        client = ContainerServiceClient(
            credentials=credentials,
            subscription_id=SubscriptionId(self.vault_name, self.vault_client).subscription_id(self.config),
        )

        # authenticate with kubernetes
        credential_results = client.managed_clusters.list_cluster_user_credentials(
            resource_group_name=resource_group, resource_name=cluster_name
        )

        self._write_kube_config(credential_results)


IP_ADDRESS_MATCH = r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"
DEPLOY_SCHEMA = TAKEOFF_BASE_SCHEMA.extend(
    {
        vol.Required("task"): "deploy_to_kubernetes",
        vol.Optional("deployment_config_path", default="kubernetes_config/deployment.yaml.j2"): str,
        vol.Optional("service_config_path", default="kubernetes_config/service.yaml.j2"): str,
        vol.Optional("service_ips"): {
            vol.Optional("dev"): vol.All(str, vol.Match(IP_ADDRESS_MATCH)),
            vol.Optional("acp"): vol.All(str, vol.Match(IP_ADDRESS_MATCH)),
            vol.Optional("prd"): vol.All(str, vol.Match(IP_ADDRESS_MATCH)),
        },
        "azure": {
            vol.Required(
                "kubernetes_naming",
                description=(
                    "Naming convention for the resource."
                    "This should include the {env} parameter. For example"
                    "aks_{env}"
                ),
            ): str
        },
    },
    extra=vol.ALLOW_EXTRA,
)


class DeployToKubernetes(BaseKubernetes):
    """Deploys or updates deployments and services to/on a kubernetes cluster"""

    def __init__(self, env: ApplicationVersion, config: dict):
        super().__init__(env, config)

        self.core_v1_api = CoreV1Api()
        self.extensions_v1_beta_api = kubernetes.client.ExtensionsV1beta1Api()

    def schema(self) -> vol.Schema:
        return DEPLOY_SCHEMA

    def run(self):
        # get the ip address for this environment
        service_ip = None
        if "service_ips" in self.config:
            service_ip = self.config["service_ips"][self.env.environment.lower()]

        # load some kubernetes config
        application_name = ApplicationName().get(self.config)
        kubernetes_deployment = render_file_with_jinja(
            self.config["deployment_config_path"],
            {
                "docker_tag": self.env.artifact_tag,
                "namespace": self.kubernetes_namespace,
                "application_name": application_name,
            },
            yaml.load,
        )
        kubernetes_service = render_file_with_jinja(
            self.config["service_config_path"],
            {
                "service_ip": service_ip,
                "namespace": self.kubernetes_namespace,
                "application_name": application_name,
            },
            yaml.load,
        )
        logging.info("Deploying ----------------------------------------")
        pprint(kubernetes_deployment)
        pprint(kubernetes_service)
        logging.info("--------------------------------------------------")

        logging.info(f"Deploying to K8S. Environment: {self.env.environment}")

        self.deploy_to_kubernetes(deployment_config=kubernetes_deployment, service_config=kubernetes_service)

    @staticmethod
    def is_needle_in_haystack(needle: str, haystack: dict) -> bool:
        """Helper method to check for existence of a k8s entity

        Args:
            needle: name of the kubernetes entity you want to find
            haystack: dict of entities, in the kubernetes structure of entities (i.e. items->metadata->name)
        Returns:
            bool: whether or not the entity was found in the haystack
        """
        for dep in haystack["items"]:
            if dep["metadata"]["name"] == needle:
                return True
        return False

    def _kubernetes_resource_exists(
        self, resource_name: str, namespace: str, kubernetes_resource_listing_function: Callable
    ) -> bool:
        """Check if a kubernetes resource exists on the cluster

        This is a generic function that is used by functions that check for more specific resource existence

        Args:
            resource_name: the name of the resource for which you are checking existence
            namespace: kubernetes namespace in which to search
            kubernetes_resource_listing_function: the function to use to list resources. This function should
                return a type that can be converted to a dictionary.

        Returns:
            bool: whether or not the resource exists
        """
        existing_services = kubernetes_resource_listing_function(namespace=namespace).to_dict()
        return self.is_needle_in_haystack(resource_name, existing_services)

    def _kubernetes_namespace_exists(self, namespace: str):
        """Check if a kubernetes namespace exists on the cluster

        Args:
            namespace: name of the namespace for which to check existence

        Returns:
            bool: whether or not the namespace exists
        """
        existing_namespaces = self.core_v1_api.list_namespace().to_dict()
        return self.is_needle_in_haystack(namespace, existing_namespaces)

    def _create_namespace_if_not_exists(self, kubernetes_namespace: str):
        """Create a given namespace if it does not yet exist on the cluster

        If the namespace does already exist, this function does nothing

        Args:
            kubernetes_namespace: namespace to create if it doesn't exist
        """
        if not self._kubernetes_namespace_exists(kubernetes_namespace):
            logger.info(
                f"No kubernetes namespace for this application. Creating namespace: {kubernetes_namespace}"
            )
            namespace_to_create = kubernetes.client.V1Namespace(metadata={"name": kubernetes_namespace})
            self.core_v1_api.create_namespace(body=namespace_to_create)

    def _create_or_patch_resource(
        self,
        client: Union[CoreV1Api, ExtensionsV1beta1Api],
        resource_type: str,
        name: str,
        namespace: str,
        resource_config: dict,
    ):
        """Create or patch a given kubernetes resource

        This function will call the function associated with the provided resource type from the kubernetes
        client API provided. This means that the client needs to have the `list_namespaced_{resource_type}`
        function available for this to work. This function does not verify that the configuration provided
        makes sense for the given resource. That is left to the caller.

        Args:
            client: the kubernetes client to use. Currently one of: CoreV1Api or ExtensionsV1beta1Api
            resource_type: type of resource to target. Should be a valid kubernetes resource type
            name: name of the resource
            namespace: namespace of the resource
            resource_config: any configuration for the resource that is not covered by the other parameters
        """
        list_function = getattr(client, f"list_namespaced_{resource_type}")
        patch_function = getattr(client, f"patch_namespaced_{resource_type}")
        create_function = getattr(client, f"create_namespaced_{resource_type}")
        if self._kubernetes_resource_exists(name, namespace, list_function):
            # we need to patch the existing resource
            logger.info(
                f"Found existing kubernetes resource, patching resource {name} in namespace {namespace}"
            )
            patch_function(name=name, namespace=namespace, body=resource_config)
        else:
            # the resource doesn't exist, we need to create it
            logger.info(
                f"No existing kubernetes resource found, creating resource: {name} in namespace {namespace}"
            )
            create_function(namespace=namespace, body=resource_config)

    def _create_or_patch_service(self, service_config: dict, kubernetes_namespace: str):
        """Create or patch a kubernetes service

        Args:
            service_config: service configuration to use. Should contain [metadata][name]
            kubernetes_namespace: namespace to deploy service in
        """
        service_name = service_config["metadata"]["name"]
        self._create_or_patch_resource(
            client=self.core_v1_api,
            resource_type="service",
            name=service_name,
            namespace=kubernetes_namespace,
            resource_config=service_config,
        )

    def _create_or_patch_deployment(self, deployment: dict, kubernetes_namespace: str):
        """Create or patch a kubernetes deployment

        Args:
            deployment: deployment configuration to use. Name will be application name
            kubernetes_namespace: namespace to deploy service in
        """
        self._create_or_patch_resource(
            client=self.extensions_v1_beta_api,
            resource_type="deployment",
            name=ApplicationName().get(self.config),
            namespace=kubernetes_namespace,
            resource_config=deployment,
        )

    def _create_or_patch_secrets(
        self, secrets: List[Secret], kubernetes_namespace: str, name: str = None, secret_type: str = "Opaque"
    ):
        """Create or patch a list of secrets in a given kubernetes namespace

        When you provide multiple Secret objects in the list, these will be put into a single Kubernetes
        Secret object, where each object is available in key-value form.

        Args:
            secrets: list of secrets to create of patch
            kubernetes_namespace: namespace in which these secrets will be put
            name: name of the kubernetes secret. Defaults to {application-name}-secret
            secret_type: type of kubernetes secret. Defaults to Opaque.
        """
        application_name = ApplicationName().get(self.config)
        secret_name = f"{application_name}-secret" if not name else name

        secret = kubernetes.client.V1Secret(
            metadata=kubernetes.client.V1ObjectMeta(name=secret_name),
            type=secret_type,
            data={_.key: b64_encode(_.val) for _ in secrets},
        )

        self._create_or_patch_resource(
            client=self.core_v1_api,
            resource_type="secret",
            name=secret_name,
            namespace=kubernetes_namespace,
            resource_config=secret.to_dict(),
        )

    def _create_docker_registry_secret(self):
        """Create a secret containing credentials for logging into the defined docker registry

        The credentials are fetched from your keyvault provider, and are inserted into a secret called
        'acr-auth'
        """
        docker_credentials = DockerRegistry(self.vault_name, self.vault_client).credentials(self.config)
        secrets = [
            Secret(
                key=".dockerconfigjson",
                val=json.dumps(
                    {
                        "auths": {
                            docker_credentials.registry: {
                                "username": docker_credentials.username,
                                "password": docker_credentials.password,
                                "auth": b64_encode(
                                    f"{docker_credentials.username}:{docker_credentials.password}"
                                ),
                            }
                        }
                    }
                ),
            )
        ]
        secret_type = "kubernetes.io/dockerconfigjson"
        self._create_or_patch_secrets(
            secrets, self.kubernetes_namespace, name="acr-auth", secret_type=secret_type
        )

    def _create_keyvault_secrets(self):
        """Create kubernetes secrets of all secrets in the keyvault that match the application-name

        Adds build-version as a secret as well.
        """
        secrets = KeyVaultCredentialsMixin(self.vault_name, self.vault_client).get_keyvault_secrets(
            ApplicationName().get(self.config)
        )
        secrets.append(Secret("build-version", self.env.artifact_tag))
        self._create_or_patch_secrets(secrets, self.kubernetes_namespace)

    def deploy_to_kubernetes(self, deployment_config: dict, service_config: dict):
        """Run a full deployment to kubernetes, given configuration.

        Args:
            deployment_config: kubernetes deployment configuration to use
            service_config: kubernetes service ocnfiguration to use
        """
        self._authenticate_with_kubernetes()

        # load the kubeconfig we just fetched
        kubernetes.config.load_kube_config()
        logger.info("Kubeconfig loaded")

        self._create_namespace_if_not_exists(self.kubernetes_namespace)
        logger.info("Namespace available")

        self._create_keyvault_secrets()
        logger.info("Keyvault secrets available")

        self._create_docker_registry_secret()
        logger.info("Docker registry secret available")

        self._create_or_patch_deployment(deployment_config, self.kubernetes_namespace)
        logger.info("Deployment available")

        self._create_or_patch_service(service_config, self.kubernetes_namespace)
        logger.info("Service available")

    @property
    def kubernetes_namespace(self):
        return ApplicationName().get(self.config)

    @property
    def cluster_name(self):
        return get_kubernetes_name(self.config, self.env)
