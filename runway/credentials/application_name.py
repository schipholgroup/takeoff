import logging

from runway.credentials.EnvironmentCredentialsMixin import EnvironmentCredentialsMixin
from runway.util import current_filename


class ApplicationName(EnvironmentCredentialsMixin):
    def get(self, config) -> str:
        credential_kwargs = super()._transform_environment_key_to_credential_kwargs(
            config["environment_keys"]
        )
        logging.info(credential_kwargs)
        return credential_kwargs[current_filename(__file__)]
