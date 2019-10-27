import logging
import os
from typing import Dict, List, Tuple, Union

from takeoff.credentials.credential_provider import BaseProvider
from takeoff.util import inverse_dictionary

logger = logging.getLogger(__name__)


class EnvironmentCredentialsMixin(object):
    def _transform_environment_key_to_single_credential(self, name: str, os_key: str) -> Dict[str, str]:
        """Transforms a specific name to the value of the environment variable.

        Example:

            - name: `application_name`
            - os_key: `CI_PROJECT_NAME` where environment variable `CI_PROJECT_NAME=myapp`

            will return a dictionary::

                { "application_name": "myapp" }


        Args:
            name: The name that represents the variable key
            os_key: The name of the environment variable

        Returns:
            A mapping of name to environment variable value
        """
        try:
            credentials: Dict[str, str] = self._read_os_variables([os_key])
        except KeyError:
            raise ValueError(f"Could not find environment variable {os_key}")
        return {name: credentials[os_key]}

    def _transform_environment_key_to_credential_kwargs(self, keys: Dict[str, str]) -> Dict[str, str]:
        """Transforms a mapping of name to environment variable to a mapping of name to value

        Example:

            keys::

                { "username": "USERNAME_DEV", "password": "PASSWORD_DEV" }

            where environment variables `USERNAME_DEV=user1` and `PASSWORD_DEV=randomuuid`
            will return a dictionary::

                { "username": "user1" "password": "randomuuid" }


        Args:
            keys: A dictionary containing the mapping of name to environment variable

        Returns:
            A mapping of name to environment variable value
        """
        credentials: Dict[str, str] = self._read_os_variables(list(keys.values()))
        credential_kwargs = {
            function_arg: credentials[os_variable]
            for os_variable, function_arg in inverse_dictionary(keys).items()
        }
        return credential_kwargs

    def _read_os_variables(self, environment_keys: List[str]) -> Dict[str, str]:
        """
        Example:
           environment_keys: `["CI_PROJECT_NAME", "CI_BRANCH"]`

           where environment variables `CI_PROJECT_NAME=myapp` and `CI_BRANCH=master` returns::

               { "CI_PROJECT_NAME: "myapp", "CI_BRANCH": "master" }


        Args:
            keys (List[str]): A list containing the enviroment keys to search for in os.environ

        Returns:
            Dict[str: str]: A dictionary of all secrets matching the keys, indexed on the key
        """
        return {key: os.environ[key] for key in environment_keys}


class SingleEnvironmentCredentialProvider(BaseProvider, EnvironmentCredentialsMixin):
    def get_credentials(self, lookup: Union[str, Dict[str, str], Tuple[str, str]]):
        if not isinstance(lookup, tuple):
            raise ValueError("Please provide a tuple")
        return self._transform_environment_key_to_single_credential(*lookup)


class CIEnvironmentCredentials(BaseProvider, EnvironmentCredentialsMixin):
    def get_credentials(self, lookup: Union[str, Dict[str, str], Tuple[str, str]]):
        if not isinstance(lookup, str):
            raise ValueError("Please provide a string")
        if not self.env:
            raise ValueError("Needs ApplicationVersion")
        credential_kwargs = super()._transform_environment_key_to_credential_kwargs(
            self.config[f"ci_environment_keys_{self.env.environment_formatted}"][lookup]
        )
        return credential_kwargs
