import abc
from typing import Union, Tuple, Dict, Optional

from takeoff.application_version import ApplicationVersion


class BaseProvider:
    def __init__(self, config: dict, app_version: Optional[ApplicationVersion]):
        self.config = config
        self.env = app_version

    @abc.abstractmethod
    def get_credentials(self, lookup: Union[str, Dict[str, str], Tuple[str, str]]):
        pass
