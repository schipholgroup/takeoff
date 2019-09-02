import unittest

import mock
import pytest
import voluptuous as vol

from runway.ApplicationVersion import ApplicationVersion
from runway.build_artifact import BuildArtifact as victim
from tests.azure import runway_config

BASE_CONF = {"task": "buildArtifact", "lang": "python"}


class TestBuildArtifact(unittest.TestCase):
    @mock.patch("runway.DeploymentStep.KeyvaultClient.vault_and_client", return_value=(None, None))
    def test_validate_minimal_schema(self, _):
        conf = {**runway_config(), **BASE_CONF}

        victim(ApplicationVersion("dev", "v", "branch"), conf)
