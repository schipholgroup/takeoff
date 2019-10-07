from enum import Enum, auto, unique
from typing import Any, Dict


@unique
class ContextKey(Enum):
    EVENTHUB_PRODUCER_POLICY_SECRETS = auto()


class Singleton(type):
    _instances: Dict[Any, Any] = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class Context(metaclass=Singleton):
    def __init__(self):
        self.__data = {}

    def create_or_update(self, key, value) -> "Context":
        """Creates a new key with value. If the key exists the value is updated

        Args:
            key: Key of the context variable
            value: Value of the context variable

        Returns:
            Updated Context
        """
        self.__data.update({key: value})
        return self

    def delete(self, key) -> "Context":
        """Delete a specific key from the Context

        Args:
            key: Key of the context variable

        Returns:
            Context without given key
        """
        del self.__data[key]
        return self

    def clear(self) -> "Context":
        """Clears the entire Context

        Returns:
            Empty Context
        """
        self.__data = {}
        return self

    def get(self, key) -> Any:
        """Convenience method

        Args:
            key: Key of the context variable

        Returns:
            The value if the key exists, None otherwise
        """
        return self.get_or_else(key, None)

    def get_or_else(self, key, _else: Any) -> Any:
        """Convenience method

        Args:
            key: Key of the context variable
            _else: If the key does not exists, return this value

        Returns:
            The value if the key exists, _else otherwise
        """
        return self.__data.get(key, _else)

    def exists(self, key) -> bool:
        """Convenience method

        Args:
            key: Key of the context variable

        Returns:
            True if the key exists, false otherwise
        """
        return key in self.__data
