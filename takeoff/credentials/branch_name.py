import logging

from takeoff.credentials.EnvironmentCredentialsMixin import EnvironmentCredentialsMixin
from takeoff.util import current_filename


class BranchName(EnvironmentCredentialsMixin):
    def get(self, config: dict) -> str:
        credential_kwargs = super()._transform_environment_key_to_credential_kwargs(
            config["environment_keys"]
        )
        logging.info(credential_kwargs)
        return credential_kwargs[current_filename(__file__)]
