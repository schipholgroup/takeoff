from dataclasses import dataclass

from takeoff.credentials.takeoff_credentials import TakeoffCredentials


@dataclass(frozen=True)
class DockerCredentials(object):
    username: str
    password: str
    registry: str


class DockerRegistry(TakeoffCredentials):
    def __init__(self, config, env):
        super().__init__(config, env)

    def credentials(self):
        credential_kwargs = self.provider.get_credentials("container_registry")
        return DockerCredentials(**credential_kwargs)
