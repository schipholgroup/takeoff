import abc


class DeploymentStep(object):
    @abc.abstractmethod
    def run(self):
        raise NotImplementedError
