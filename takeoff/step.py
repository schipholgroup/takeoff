import abc
import logging
import pprint

import voluptuous as vol

from takeoff.application_version import ApplicationVersion
from takeoff.azure.credentials.keyvault import KeyVaultClient

logger = logging.getLogger(__name__)


class Step(object):
    """Base class for any Takeoff step

    Inheriting from this class will allow the user to create a new Step that will validate the schema
    and expose the `run` function. After inheriting this, add the new class to `steps.py`. This will
    enable Takeoff to pick it up from the `.takeoff/deployment.yml`.
    """

    def __init__(self, env: ApplicationVersion, config: dict):
        self.env = env
        self.config = self.validate(config)

    @abc.abstractmethod
    def run(self):
        """The entrypoint to any step. Should contain the main logic for any Takeoff step"""
        raise NotImplementedError

    def validate(self, config: dict) -> dict:
        """Validates a given voluptuous schema

        Args:
            config: Takeoff configuration

        Returns:
            The validated schema

        Raises:
            MultipleInvalid
            Invalid
        """
        try:
            return self.schema()(config)
        except (vol.MultipleInvalid, vol.Invalid) as e:
            logger.error(e)
            logger.error(pprint.pformat(config))
            raise e

    @abc.abstractmethod
    def schema(self) -> vol.Schema:
        raise NotImplementedError


class SubStep(object):
    """Convenience class to use in substeps that don't require schema validation and
    should not be `run`able as main `Step`"""

    def __init__(self, env: ApplicationVersion, config: dict):
        self.env = env
        self.config = config
        self.vault_name, self.vault_client = KeyVaultClient.vault_and_client(self.config, self.env)
