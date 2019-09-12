import abc
from typing import Union, Tuple, Dict


class BaseProvider:
    def __init__(self, config, env):
        self.config = config
        self.env = env

    @abc.abstractmethod
    def get_credentials(self, lookup: Union[str, Dict[str, str], Tuple[str, str]]):
        pass
