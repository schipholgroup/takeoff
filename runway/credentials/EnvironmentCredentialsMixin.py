import os
from typing import Dict, List

from runway.util import inverse_dictionary


class EnvironmentCredentialsMixin(object):
    def _transform_environment_key_to_credential_kwargs(self, keys: Dict[str, str]):
        credentials: Dict[str, str] = self._read_os_variables(list(keys.values()))
        credential_kwargs = {function_arg: credentials[os_variable]
                             for os_variable, function_arg in inverse_dictionary(keys).items()}
        return credential_kwargs

    def _read_os_variables(self, environment_keys: List[str]):
        """
        Args:
            keys (List[str]): A list containing the enviroment keys to search for in os.environ

        Returns:
            Dict[str: str]: A dictionary of all secrets matching the keys, indexed on the key
        """
        return {key: os.environ[key] for key in environment_keys}
