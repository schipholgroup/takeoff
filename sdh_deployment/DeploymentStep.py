import abc

from sdh_deployment import ApplicationVersion


class DeploymentStep(object):
    def __init__(self, env: ApplicationVersion, config: dict):
        self.env = env
        self.config = config

    @abc.abstractmethod
    def run(self):
        raise NotImplementedError
