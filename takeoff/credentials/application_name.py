"""
Example:

    In `.takeoff/config.yml`::

        environment_keys:
            application_name: SOME_ENV_VARIABLE

This name is used throughout Takeoff anywhere a name is needed.
"""

from takeoff.credentials.environment_credentials_provider import (
    SingleEnviromentCredentialProvider,
)
from takeoff.util import current_filename


class ApplicationName(SingleEnviromentCredentialProvider):
    """Reads environment variables to determine the application name.

    Assumes there is an environment variable that exposes the name of the application. Most
    CI services do this by exposing the git repository name.
    """

    def get(self) -> str:
        fn = current_filename(__file__)
        return self.get_credentials((fn, self.config["environment_keys"][fn]))
