import json
import logging
import os
from tempfile import NamedTemporaryFile
from typing import Callable, List

import kubernetes
import voluptuous as vol
import yaml
from azure.mgmt.containerservice.container_service_client import ContainerServiceClient
from azure.mgmt.containerservice.models import CredentialResults
from kubernetes.client import CoreV1Api

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
from takeoff.util import render_string_with_jinja, b64_encode, run_shell_command

logger = logging.getLogger(__name__)


class BaseKubernetes(Step):
    """Base Kubernetes class

    This class is used by the two Kubernetes steps: deploy_to_kubernetes and kubernetes_image_rolling_update.
    It handles the authentication to the specified Kubernetes cluster

    Depends on:
    - Credentials for the Kubernetes cluster (username, password) must be available in your cloud vault
    """

    def __init__(self, env: ApplicationVersion, config: dict):
        super().__init__(env, config)

    @staticmethod
    def _write_kube_config(credential_results: CredentialResults):
        """Creates ~/.kube/config and writes the credentials for the Kubernetes cluster to the file

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

        # authenticate with Kubernetes
        credential_results = client.managed_clusters.list_cluster_user_credentials(
            resource_group_name=resource_group, resource_name=cluster_name
        )

        self._write_kube_config(credential_results)


IP_ADDRESS_MATCH = r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"
DEPLOY_SCHEMA = TAKEOFF_BASE_SCHEMA.extend(
    {
        vol.Required("task"): "deploy_to_kubernetes",
        vol.Required("kubernetes_config_path"): str,
        vol.Optional("create_keyvault_secrets", default=True): bool,
        vol.Optional("create_image_pull_secret", default=True): bool,
        vol.Optional("restart_unchanged_resources", default=False): bool,
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
    """Deploys or updates deployments and services to/on a Kubernetes cluster"""

    def __init__(self, env: ApplicationVersion, config: dict):
        super().__init__(env, config)

        self.core_v1_api = CoreV1Api()

    def schema(self) -> vol.Schema:
        return DEPLOY_SCHEMA

    def run(self):
        # load some Kubernetes config
        application_name = ApplicationName().get(self.config)

        logging.info(f"Deploying to K8S. Environment: {self.env.environment}")

        self.deploy_to_kubernetes(self.config["kubernetes_config_path"], application_name)

    @staticmethod
    def is_needle_in_haystack(needle: str, haystack: dict) -> bool:
        """Helper method to check for existence of a k8s entity

        Args:
            needle: name of the Kubernetes entity you want to find
            haystack: dict of entities, in the Kubernetes structure of entities (i.e. items->metadata->name

        Returns:
            bool: True if the needle is in the haystack, False otherwise
        """
        for dep in haystack["items"]:
            if dep["metadata"]["name"] == needle:
                return True
        return False

    def _kubernetes_resource_exists(
        self, resource_name: str, namespace: str, kubernetes_resource_listing_function: Callable
    ) -> bool:
        """Check if a Kubernetes resource exists on the cluster

        This is a generic function that is used by functions that check for more specific resource existence

        Args:
            resource_name: the name of the resource for which you are checking existence
            namespace: Kubernetes namespace in which to search
            kubernetes_resource_listing_function: the function to use to list resources. This function should
                return a type that can be converted to a dictionary.

        Returns:
            bool: True if the resource exists, False otherwise
        """
        existing_services = kubernetes_resource_listing_function(namespace=namespace).to_dict()
        return self.is_needle_in_haystack(resource_name, existing_services)

    def _create_or_patch_resource(
        self, client: CoreV1Api, resource_type: str, name: str, namespace: str, resource_config: dict
    ):
        """Create or patch a given Kubernetes resource

        This function will call the function associated with the provided resource type from the Kubernetes
        client API provided. This means that the client needs to have the `list_namespaced_{resource_type}`
        function available for this to work. This function does not verify that the configuration provided
        makes sense for the given resource. That is left to the caller.

        Args:
            client: the Kubernetes client to use.
            resource_type: type of resource to target. Should be a valid Kubernetes resource type
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
                f"Found existing Kubernetes resource, patching resource {name} in namespace {namespace}"
            )
            patch_function(name=name, namespace=namespace, body=resource_config)
        else:
            # the resource doesn't exist, we need to create it
            logger.info(
                f"No existing Kubernetes resource found, creating resource: {name} in namespace {namespace}"
            )
            create_function(namespace=namespace, body=resource_config)

    def _create_or_patch_secrets(
        self, secrets: List[Secret], kubernetes_namespace: str, name: str = None, secret_type: str = "Opaque"
    ):
        """Create or patch a list of secrets in a given Kubernetes namespace

        When you provide multiple Secret objects in the list, these will be put into a single Kubernetes
        Secret object, where each object is available in key-value form.

        Args:
            secrets: list of secrets to create of patch
            kubernetes_namespace: namespace in which these secrets will be put
            name: name of the Kubernetes secret. Defaults to {application-name}-secret
            secret_type: type of Kubernetes secret. Defaults to Opaque.
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

        The credentials are fetched from your keyvault provider,
        and are inserted into a secret called 'acr-auth'
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
        """Create Kubernetes secrets of all secrets in the keyvault that match the application-name

        Adds build-version as a secret as well.
        """
        secrets = KeyVaultCredentialsMixin(self.vault_name, self.vault_client).get_keyvault_secrets(
            ApplicationName().get(self.config)
        )
        secrets.append(Secret("build-version", self.env.artifact_tag))
        self._create_or_patch_secrets(secrets, self.kubernetes_namespace)

    def _render_kubernetes_config(self, kubernetes_config_path: str, application_name: str) -> str:
        kubernetes_config = render_string_with_jinja(
            kubernetes_config_path,
            {
                "docker_tag": self.env.artifact_tag,
                "application_name": application_name,
                **self.config['template_values'][self.env.environment]
            },
        )
        return kubernetes_config

    def _write_kubernetes_config(self, kubernetes_config: str) -> str:
        rendered_kubernetes_config_path = NamedTemporaryFile(delete=False, mode="w")
        rendered_kubernetes_config_path.write(json.dumps(kubernetes_config))
        rendered_kubernetes_config_path.close()

        return rendered_kubernetes_config_path.name

    def _render_and_write_kubernetes_config(self, kubernetes_config_path: str, application_name: str) -> str:
        """
        Render the jinja-templated kubernetes configuration adn write it out to a temporary file.
        Args:
            kubernetes_config_path: The raw, jinja-templated kubernetes configuration path.
            application_name: Current application name

        Returns:
            The path to the temporary file where the rendered kubernetes configuration is stored.
        """
        kubernetes_config = self._render_kubernetes_config(kubernetes_config_path, application_name)
        return self._write_kubernetes_config(kubernetes_config)

    def _restart_unchanged_resources(self, output: List):
        """
        Trigger a restart of resources that were unchanges, given a list of output lines from the kubectl
        CLI client

        Args:
            output: List of output lines that kubectl produced when apply -f was run
        """
        for line in output:
            if "unchanged" in line:
                resource = line.split(" ")[0]
                cmd = ["kubectl", "rollout", "restart", resource]
                exit_code, output = run_shell_command(cmd)
                if exit_code == 0:
                    logger.info(f"Restarted: {resource}")
                else:
                    raise ChildProcessError(f"Couldn't restart Kubernetes resource: {resource}")

    def _apply_kubernetes_config_file(self, file_path: str):
        """
        Create/Update the kubernetes resources based on the provided file_path to the configuration. This
        function assumes that the file does NOT contain any Jinja-templated variables anymore (i.e. it's
        been rendered)

        Args:
            file_path: Path to the kubernetes configuration
        """
        # workaround for some CI runners that override the default k8s namespace
        cmd = ["kubectl", "config", "set-context", self.cluster_name, "--namespace", "default"]
        exit_code, _ = run_shell_command(cmd)
        if exit_code != 0:
            raise ChildProcessError(f"Couldn't set-context for cluster {self.cluster_name}")

        cmd = ["kubectl", "apply", "-f", file_path]
        exit_code, response = run_shell_command(cmd)
        if exit_code != 0:
            raise ChildProcessError(f"Couldn't apply Kubernetes config from path {file_path}")

        if self.config["restart_unchanged_resources"]:
            self._restart_unchanged_resources(response)

    def deploy_to_kubernetes(self, kubernetes_config_path: str, application_name: str):
        """Run a full deployment to Kubernetes, given configuration.

        Args:
            kubernetes_config_path: path to the jinja-templated kubernetes config
            application_name: current application name
        """
        self._authenticate_with_kubernetes()

        # load the kubeconfig we just fetched
        kubernetes.config.load_kube_config()
        logger.info("Kubeconfig loaded")

        rendered_kubernetes_config_path = self._render_and_write_kubernetes_config(
            kubernetes_config_path, application_name
        )
        logger.info("Kubernetes config rendered")

        if self.config["create_keyvault_secrets"]:
            self._create_keyvault_secrets()
            logger.info("Keyvault secrets available")

        if self.config["create_image_pull_secret"]:
            self._create_docker_registry_secret()
            logger.info("Docker registry secret available")

        self._apply_kubernetes_config_file(rendered_kubernetes_config_path)
        logger.info("Applied rendered Kubernetes config")

    @property
    def kubernetes_namespace(self):
        return ApplicationName().get(self.config)

    @property
    def cluster_name(self):
        return get_kubernetes_name(self.config, self.env)
