from typing import List

from runway.application_version import ApplicationVersion
from runway.credentials.Secret import Secret


class DeploymentYamlEnvironmentVariablesMixin(object):
    def __init__(self, app_version: ApplicationVersion, config: dict):
        self.app_version = app_version
        self.config = config

    def get_deployment_secrets(self) -> List[Secret]:
        """
        Returns:
            List[Secret]: The list of all secrets from the environment part in the config
        """
        conf_secrets = self.config.get(self.app_version.environment.lower(), [])

        app_secrets = [Secret(k, v) for secret in conf_secrets for k, v in secret.items()]
        return app_secrets
