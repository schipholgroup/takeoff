import abc
from typing import Union, Tuple, Dict

from takeoff.application_version import ApplicationVersion


class BaseProvider:
    def __init__(self, config: dict, env: ApplicationVersion):
        self.config = config
        self.env = env

    @abc.abstractmethod
    def get_credentials(self, lookup: Union[str, Dict[str, str], Tuple[str, str]]):
        pass
