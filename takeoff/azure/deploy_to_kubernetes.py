import json
import logging
import os
from pprint import pprint

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
from takeoff.util import render_file_with_jinja, b64_encode

logger = logging.getLogger(__name__)


class BaseKubernetes(Step):
    def __init__(self, env: ApplicationVersion, config: dict):
        super().__init__(env, config)

    @staticmethod
    def _write_kube_config(credential_results: CredentialResults):
        kubeconfig = credential_results.kubeconfigs[0].value.decode(encoding="UTF-8")

        kubeconfig_dir = os.path.expanduser("~/.kube")

        # assumption here that there is no existing kubeconfig (which makes sense, given this script should
        # be run in a docker container ;-) )
        os.mkdir(kubeconfig_dir)
        with open(kubeconfig_dir + "/config", "w") as f:
            f.write(kubeconfig)

        logger.info("Kubeconfig successfully written")

    def _authenticate_with_kubernetes(self):
        resource_group = get_resource_group_name(self.config, self.env)

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
            resource_group_name=resource_group, resource_name=self.cluster_name
        )

        self._write_kube_config(credential_results)


IP_ADDRESS_MATCH = r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"
DEPLOY_SCHEMA = TAKEOFF_BASE_SCHEMA.extend(
    {
        vol.Required("task"): "deployToKubernetes",
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
    def __init__(self, env: ApplicationVersion, config: dict):
        super().__init__(env, config)

        self.add_application_insights = self.config.get("add_application_insights", False)
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
    def is_needle_in_haystack(needle, haystack):
        # Helper method to abstract away checking for existence of a kubernetes entity
        # this assumes the kubernetes structure of entities (i.e. items->metadata->name
        for dep in haystack["items"]:
            if dep["metadata"]["name"] == needle:
                return True
        return False

    def _kubernetes_resource_exists(
        self, resource_name: str, namespace: str, kubernetes_resource_listing_function
    ):
        existing_services = kubernetes_resource_listing_function(namespace=namespace).to_dict()
        return self.is_needle_in_haystack(resource_name, existing_services)

    def _kubernetes_namespace_exists(self, namespace: str):
        existing_namespaces = self.core_v1_api.list_namespace().to_dict()
        return self.is_needle_in_haystack(namespace, existing_namespaces)

    def _create_namespace_if_not_exists(self, kubernetes_namespace: str):
        # very simple way to ensure the namespace exists
        if not self._kubernetes_namespace_exists(kubernetes_namespace):
            logger.info(
                f"No kubernetes namespace for this application. Creating namespace: {kubernetes_namespace}"
            )
            namespace_to_create = kubernetes.client.V1Namespace(metadata={"name": kubernetes_namespace})
            self.core_v1_api.create_namespace(body=namespace_to_create)

    def _create_or_patch_resource(
        self, client, resource_type: str, name: str, namespace: str, resource_config: dict
    ):
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
        service_name = service_config["metadata"]["name"]
        self._create_or_patch_resource(
            client=self.core_v1_api,
            resource_type="service",
            name=service_name,
            namespace=kubernetes_namespace,
            resource_config=service_config,
        )

    def _create_or_patch_deployment(self, deployment: dict, kubernetes_namespace: str):
        self._create_or_patch_resource(
            client=self.extensions_v1_beta_api,
            resource_type="deployment",
            name=ApplicationName().get(self.config),
            namespace=kubernetes_namespace,
            resource_config=deployment,
        )

    def _create_or_patch_secrets(
        self, secrets, kubernetes_namespace, name: str = None, secret_type: str = "Opaque"
    ):
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
        secrets = KeyVaultCredentialsMixin(self.vault_name, self.vault_client).get_keyvault_secrets(
            ApplicationName().get(self.config)
        )
        secrets.append(Secret("build-version", self.env.artifact_tag))
        self._create_or_patch_secrets(secrets, self.kubernetes_namespace)

    def deploy_to_kubernetes(self, deployment_config: dict, service_config: dict):
        # 1: get kubernetes credentials
        self._authenticate_with_kubernetes()

        # load the kubeconfig we just fetched
        kubernetes.config.load_kube_config()
        logger.info("Kubeconfig loaded")

        # 2: verify that the namespace exists, if not: create it
        self._create_namespace_if_not_exists(self.kubernetes_namespace)

        # 3: create kubernetes secrets from azure keyvault
        self._create_keyvault_secrets()

        # 3.1: create kubernetes secrets for docker registry
        self._create_docker_registry_secret()

        # 4: create OR patch kubernetes deployment
        self._create_or_patch_deployment(deployment_config, self.kubernetes_namespace)

        # 5: create OR patch kubernetes service
        self._create_or_patch_service(service_config, self.kubernetes_namespace)

    @property
    def kubernetes_namespace(self):
        return ApplicationName().get(self.config)

    @property
    def cluster_name(self):
        return get_kubernetes_name(self.config, self.env)
