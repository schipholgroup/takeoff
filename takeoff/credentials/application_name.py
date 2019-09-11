"""
Example:

    In `.takeoff/config.yml`::

        environment_keys:
            application_name: SOME_ENV_VARIABLE

This name is used throughout Takeoff anywhere a name is needed.
"""
import logging

from takeoff.credentials.EnvironmentCredentialsMixin import EnvironmentCredentialsMixin
from takeoff.util import current_filename


class ApplicationName(EnvironmentCredentialsMixin):
    """Reads environment variables to determine the application name.

    Assumes there is an environment variable that exposes the name of the application. Most
    CI services do this by exposing the git repository name.
    """

    def get(self, config: dict) -> str:
        credential_kwargs = super()._transform_environment_key_to_credential_kwargs(
            config["environment_keys"]
        )
        logging.info(credential_kwargs)
        return credential_kwargs[current_filename(__file__)]
