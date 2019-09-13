from takeoff.credentials.environment_credentials_provider import (
    SingleEnviromentCredentialProvider,
)
from takeoff.util import current_filename


class BranchName(SingleEnviromentCredentialProvider):
    def get(self) -> str:
        fn = current_filename(__file__)
        return self.get_credentials((fn, self.config["environment_keys"][fn]))[fn]
