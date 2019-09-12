import logging

import kubernetes
import voluptuous as vol

from takeoff.application_version import ApplicationVersion
from takeoff.azure.deploy_to_kubernetes import BaseKubernetes
from takeoff.schemas import TAKEOFF_BASE_SCHEMA
from takeoff.util import run_shell_command

logger = logging.getLogger(__name__)

ROLLING_UPDATE_SCHEMA = TAKEOFF_BASE_SCHEMA.extend(
    {
        vol.Required("task"): "kubernetes_image_rolling_update",
        vol.Required("deployment_name"): str,
        vol.Required("image"): str,
        vol.Optional("namespace", default="default"): str,
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


class KubernetesImageRollingUpdate(BaseKubernetes):
    def __init__(self, env: ApplicationVersion, config: dict):
        super().__init__(env, config)

    def schema(self) -> vol.Schema:
        return ROLLING_UPDATE_SCHEMA

    def run(self):
        self.update_image()

    def update_image(self):
        # get the ip address for this environment
        self._authenticate_with_kubernetes()
        # load the kubeconfig we just fetched
        kubernetes.config.load_kube_config()
        logger.info("Kubeconfig loaded")

        self._apply_rolling_update()

    def _apply_rolling_update(self):
        """
        https://kubernetes.io/docs/concepts/workloads/controllers/deployment/#updating-a-deployment
        """
        new_image = f"{self.config['image']}:{self.env.artifact_tag}"
        logger.info(f"Deploying image {new_image}")

        deployment = self.config["deployment_name"]
        cmd = [
            "kubectl",
            "--namespace",
            self.config["namespace"],
            "--record",
            f"deployment.apps/{deployment}",
            "set",
            "image",
            f"deployment.v1.apps/{deployment}",
            f"{deployment}={new_image}",
        ]
        return_code = run_shell_command(cmd)

        if return_code != 0:
            raise ChildProcessError("Could not update the image for some reason!")
