import logging
import os
from typing import Dict, List, Union, Tuple

from takeoff.credentials.credential_provider import BaseProvider
from takeoff.util import inverse_dictionary

logger = logging.getLogger(__name__)


class EnvironmentCredentialsMixin(object):
    def _transform_environment_key_to_single_credential(self, name, os_key) -> Dict[str, str]:
        try:
            credentials: Dict[str, str] = self._read_os_variables([os_key])
        except KeyError:
            raise ValueError(f"Could not find environment variable {os_key}")
        value = list(credentials.values())[0]
        credential_kwargs = {name: value}
        return credential_kwargs

    def _transform_environment_key_to_credential_kwargs(self, keys: Dict[str, str]) -> Dict[str, str]:
        credentials: Dict[str, str] = self._read_os_variables(list(keys.values()))
        credential_kwargs = {
            function_arg: credentials[os_variable]
            for os_variable, function_arg in inverse_dictionary(keys).items()
        }
        return credential_kwargs

    def _read_os_variables(self, environment_keys: List[str]):
        """
        Args:
            keys (List[str]): A list containing the enviroment keys to search for in os.environ

        Returns:
            Dict[str: str]: A dictionary of all secrets matching the keys, indexed on the key
        """
        return {key: os.environ[key] for key in environment_keys}


class SingleEnviromentCredentialProvider(BaseProvider, EnvironmentCredentialsMixin):
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
