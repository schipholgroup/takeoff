import re
from dataclasses import dataclass
from typing import List, Dict, Optional, Iterator, Union, Tuple

from takeoff.util import run_shell_command, inverse_dictionary
from takeoff.credentials.credential_provider import BaseProvider
from takeoff.credentials.secret import Secret


@dataclass(frozen=True)
class IdAndKey:
    keyvault_id: str
    databricks_secret_key: str


@dataclass
class KeyVaultSecrets:
    secrets: List[Secret]


class GoogleCloudSecretManagerProvider(BaseProvider):
    def __init__(self, config, app_version):
        super().__init__(config, app_version)

        # TODO: this needs to be formalized
        self.login()

    def login(self):
        import os
        sp_username = os.environ['google_sp']
        sp_pw = os.environ['google_pw']
        path_to_keyfile = "/gcp.json"

        with open(path_to_keyfile, 'w') as f:
            f.write(sp_pw)

        _, res = run_shell_command(["gcloud", "auth", "activate-service-account", sp_username, "--key-file", path_to_keyfile, "--project=danieltesttakeoff"], quiet=True)
        print(res)

    def _credentials(self, keys: List[str], prefix: str = None) -> Dict[str, str]:
        """
        Args:
            keys (List[str]): A list containing the keys to search for in the keyvault
            prefix (str, optional): A prefix to filter keyvault keys on

        Returns:
            Dict[str: Secret]: A dictionary of all secrets matching the keys and prefix, indexed on the key
        """
        secrets = self.get_secrets(prefix)
        indexed = {_.key: _ for _ in secrets}
        return {_: self._find_secret(_, indexed) for _ in keys}

    def _find_secret(self, secret_key, secrets: Dict[str, Secret]) -> str:
        if secret_key not in secrets:
            raise ValueError(f"Could not find required key {secret_key}")
        return secrets[secret_key].val

    def _transform_key_to_credential_kwargs(self, keys: Dict[str, str]):
        """
        in: takeoff config. key -> secret-manager name


        out: key -> secret-value
        Args:
            keys:

        Returns:

        """
        credentials: Dict[str, str] = self._credentials(list(keys.values()))
        credential_kwargs = {
            function_argument: credentials[env_variable]
            for env_variable, function_argument in inverse_dictionary(keys).items()
        }
        return credential_kwargs

    def get_credentials(self, lookup: Union[str, Dict[str, str], Tuple[str, str]]):
        if not isinstance(lookup, str):
            raise ValueError("Please provide a string")
        return self._transform_key_to_credential_kwargs(self.config["google_cloud"]["secret_names"][lookup])

    def parse_shell_command_response(self, response: List) -> Iterator[str]:
        return map(str.strip, response)

    def get_latest_secret_version(self, secret_name: str) -> str:
        _, res = run_shell_command(["gcloud", "beta", "secrets", "versions", "list", secret_name, "--limit", "1", "--format=value(name)"], quiet=True)
        res2 = list(self.parse_shell_command_response(res))
        return res2[0]

    def get_secret_names(self, prefix: Optional[str] = ""):
        _, res = run_shell_command(["gcloud", "beta", "secrets", "list", "--format=value(name)"], quiet=True)
        res = list(self.parse_shell_command_response(res))

        if prefix:
            pattern = re.compile(f'^{prefix}')
            return [s for s in res if pattern.match(s)]
        return res

    def get_secret_value(self, secret_name: str, secret_version: str) -> str:
        _, res = run_shell_command(["gcloud", "beta", "secrets", "versions", "access", secret_version, f"--secret={secret_name}"], quiet=True)
        res = list(self.parse_shell_command_response(res))
        return res[0]

    def get_secrets(self, prefix: Optional[str] = "") -> List[Secret]:
        secret_names = self.get_secret_names(prefix)

        secrets = []
        # create the list of secrets objects
        for secret in secret_names:
            secret_version = self.get_latest_secret_version(secret)
            secret_value = self.get_secret_value(secret, secret_version)
            secrets.append(Secret(secret, secret_value, secret_version))
        return secrets
