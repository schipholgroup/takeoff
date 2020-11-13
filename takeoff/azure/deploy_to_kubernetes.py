import json
import logging
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import List, Dict

import kubernetes
import voluptuous as vol
from azure.mgmt.containerservice.container_service_client import ContainerServiceClient
from azure.mgmt.containerservice.models import CredentialResults
from kubernetes.client import CoreV1Api

from takeoff.application_version import ApplicationVersion
from takeoff.azure.credentials.active_directory_user import ActiveDirectoryUserCredentials
from takeoff.azure.credentials.keyvault import KeyVaultClient
from takeoff.azure.credentials.providers.keyvault_credentials_mixin import KeyVaultCredentialsMixin
from takeoff.azure.credentials.service_principal import ServicePrincipalCredentialsFromVault
from takeoff.azure.credentials.subscription_id import SubscriptionId
from takeoff.azure.util import get_resource_group_name, get_kubernetes_name, get_azure_credentials_object
from takeoff.context import Context, ContextKey
from takeoff.credentials.container_registry import DockerRegistry
from takeoff.credentials.secret import Secret
from takeoff.schemas import TAKEOFF_BASE_SCHEMA
from takeoff.step import Step
from takeoff.util import b64_encode, ensure_base64, render_string_with_jinja, run_shell_command

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
        self.vault_name, self.vault_client = KeyVaultClient.vault_and_client(self.config, self.env)

    @staticmethod
    def _write_kube_config(credential_results: CredentialResults):
        """Creates ~/.kube/config and writes the credentials for the Kubernetes cluster to the file

        Args:
            credential_results: the cluster credentials for the cluster
        """
        kubeconfig = credential_results.kubeconfigs[0].value.decode(encoding="UTF-8")

        kubeconfig_dir = Path(os.environ["HOME"]) / ".kube"

        kubeconfig_dir.mkdir(exist_ok=True)

        with open(kubeconfig_dir / "config", "w") as f:
            f.write(kubeconfig)

        logger.info("Kubeconfig successfully written")

    def _authenticate_with_kubernetes(self):
        """Authenticate with the defined AKS cluster and write the configuration to a file"""
        resource_group = get_resource_group_name(self.config, self.env)
        cluster_name = get_kubernetes_name(self.config, self.env)

        credentials = get_azure_credentials_object(self.config, self.vault_name, self.vault_client)

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
        vol.Optional("credentials_type", default="active_directory_user"): vol.All(str, vol.In(
            ["active_directory_user", "service_principal"])
        ),
        vol.Optional("credentials", default="environment_variables"): vol.All(
            str, vol.In(["azure_keyvault"])
        ),
        vol.Required("kubernetes_config_path"): str,
        vol.Optional(
            "image_pull_secret",
            default={"create": True, "secret_name": "registry-auth", "namespace": "default"},
        ): {
            vol.Optional("create", default=True): bool,
            vol.Optional("secret_name", default="registry-auth"): str,
            vol.Optional("namespace", default="default"): str,
        },
        vol.Optional("custom_values", default={}): {},
        vol.Optional("restart_unchanged_resources", default=False): bool,
        vol.Optional("wait_for_rollout"): {
            vol.Optional("resource_name", default="foo/bar"): vol.All(str, vol.Match("^.*/.*$")),
            vol.Optional("resource_namespace", default=""): str,
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
    """Deploys or updates deployments and services to/on a Kubernetes cluster"""

    def __init__(self, env: ApplicationVersion, config: dict):
        super().__init__(env, config)

        self.vault_name, self.vault_client = KeyVaultClient.vault_and_client(self.config, self.env)
        self.core_v1_api = CoreV1Api()

    def schema(self) -> vol.Schema:
        return DEPLOY_SCHEMA

    def run(self):
        # load some Kubernetes config
        logging.info(f"Deploying to K8S. Environment: {self.env.environment}")

        self.deploy_to_kubernetes(self.config["kubernetes_config_path"], self.application_name)

    def _get_docker_registry_secret(self) -> str:
        """Create a secret containing credentials for logging into the defined docker registry"""
        docker_credentials = DockerRegistry(self.config, self.env).credentials()
        return b64_encode(
            json.dumps(
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
            )
        )

    def _render_kubernetes_config(
            self,
            kubernetes_config_path: str,
            application_name: str,
            secrets: Dict[str, str],
            custom_values: Dict[str, str],
    ) -> str:
        kubernetes_config = render_string_with_jinja(
            kubernetes_config_path,
            {
                "docker_tag": self.env.artifact_tag,
                "application_name": application_name,
                "env": self.env.environment,
                "build_env": {**os.environ},
                **secrets,
                **custom_values,
            },
        )
        return kubernetes_config

    def _write_kubernetes_config(self, kubernetes_config: str) -> str:
        rendered_kubernetes_config_path = NamedTemporaryFile(delete=False, mode="w")
        rendered_kubernetes_config_path.write(kubernetes_config)
        rendered_kubernetes_config_path.close()

        return rendered_kubernetes_config_path.name

    def _render_and_write_kubernetes_config(
            self,
            kubernetes_config_path: str,
            application_name: str,
            secrets: List[Secret],
            custom_values: Dict[str, str],
    ) -> str:
        """
        Render the jinja-templated kubernetes configuration adn write it out to a temporary file.
        Args:
            kubernetes_config_path: The raw, jinja-templated kubernetes configuration path.
            application_name: Current application name

        Returns:
            The path to the temporary file where the rendered kubernetes configuration is stored.
        """
        vault_values = {_.jinja_safe_key: ensure_base64(_.val) for _ in secrets}

        context_values = {
            **{
                _.jinja_safe_key: ensure_base64(_.val)
                for _ in Context().get_or_else(ContextKey.EVENTHUB_PRODUCER_POLICY_SECRETS, {})
            },
            **{
                _.jinja_safe_key: ensure_base64(_.val)
                for _ in Context().get_or_else(ContextKey.EVENTHUB_CONSUMER_GROUP_SECRETS, {})
            },
        }

        kubernetes_config = self._render_kubernetes_config(
            kubernetes_config_path, application_name, {**vault_values, **context_values}, custom_values
        )
        return self._write_kubernetes_config(kubernetes_config)

    def _restart_unchanged_resources(self, file_path: str):
        """
        Trigger a restart of all restartable resources.

        Args:
            output: List of output lines that kubectl produced when apply -f was run
        """
        cmd = ["kubectl", "rollout", "restart", "-f", file_path]
        run_shell_command(cmd)
        logger.info("Restarted all possible resources")

    def _await_rollout(self, target: str, target_namespace: str):
        """Await the rollout of a specified target to complete

        This function awaits the completion of the rollout of the target in the target_namespace. If it
        fails, or if it does not complete successfully within the default kubectl timeout, a
        ChildProcessorError is thrown.

        NOTE: This may be a bit 'racy', in the sense that if multiple CI pipelines are running simultaneously,
        the await may not always be correct (it may await a different revision than the one that this step had
        just deployed).

        Args:
            target: The resource to target. This resource should be named according to the
                    <resource_type>/name convention.
            target_namespace: The namespace of the resource

        Raises:
            ChildProcessError: if the rollout of the specified resource did not complete successfully.
        """
        cmd = ["kubectl", "rollout", "--namespace", target_namespace, "status", target, "--watch=True"]
        exit_code, _ = run_shell_command(cmd)
        if exit_code != 0:
            raise ChildProcessError(
                f"Specified deployment {target} in namespace {target_namespace} "
                "did not successfully rollout."
            )
        logger.info("Rollout successful")

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

    def _create_image_pull_secret(self, application_name: str) -> str:
        pull_secrets_yaml = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "assets", "kubernetes_image_pull_secrets.yml.j2"
        )
        return self._render_and_write_kubernetes_config(
            kubernetes_config_path=pull_secrets_yaml,
            application_name=application_name,
            secrets=[Secret("pull_secret", self._get_docker_registry_secret())],
            custom_values={
                "namespace": Secret("namespace", self.config["image_pull_secret"]["namespace"]).val,
                "secret_name": Secret("secret_name", self.config["image_pull_secret"]["secret_name"]).val,
            },
        )

    def _get_custom_values(self) -> Dict[str, str]:
        if self.config["custom_values"]:
            if self.env.environment in self.config["custom_values"]:
                return self.config["custom_values"][self.env.environment]
            else:
                raise ValueError(
                    "No matching environment was found for custom values. Check your Takeoff config"
                    f"and your environment names. Looking for environment: {self.env.environment}"
                )
        return {}

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

        if self.config["image_pull_secret"]["create"]:
            file_path = self._create_image_pull_secret(application_name)
            self._apply_kubernetes_config_file(file_path)
            logger.info("Docker registry secret available")

        secrets = KeyVaultCredentialsMixin(self.vault_name, self.vault_client).get_keyvault_secrets(
            self.application_name
        )

        custom_values = self._get_custom_values()

        rendered_kubernetes_config_path = self._render_and_write_kubernetes_config(
            kubernetes_config_path, application_name, secrets, custom_values
        )
        logger.info("Kubernetes config rendered")

        self._apply_kubernetes_config_file(rendered_kubernetes_config_path)
        logger.info("Applied rendered Kubernetes config")

        if self.config["restart_unchanged_resources"]:
            self._restart_unchanged_resources(rendered_kubernetes_config_path)

        if "wait_for_rollout" in self.config.keys():
            self._await_rollout(
                self.config["wait_for_rollout"]["resource_name"],
                self.config["wait_for_rollout"]["resource_namespace"],
            )

    @property
    def kubernetes_namespace(self):
        return self.application_name

    @property
    def cluster_name(self):
        return get_kubernetes_name(self.config, self.env)
