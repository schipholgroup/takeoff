from takeoff.credentials.environment_credentials_provider import SingleEnvironmentCredentialProvider
from takeoff.util import current_filename


class BranchName(SingleEnvironmentCredentialProvider):
    def get(self) -> str:
        filename = current_filename(__file__)
        return self.get_credentials((filename, self.config["environment_keys"][filename]))[filename]
