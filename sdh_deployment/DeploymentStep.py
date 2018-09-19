import abc

from sdh_deployment.ApplicationVersion import ApplicationVersion


class DeploymentStep(object):
    @abc.abstractmethod
    def run(self, env: ApplicationVersion, config: dict):
        raise NotImplementedError
