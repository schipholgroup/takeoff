import unittest

import mock
import pytest
import voluptuous as vol

from runway.ApplicationVersion import ApplicationVersion
from runway.azure.publish_artifact import PublishArtifact as victim
from runway.azure.publish_artifact import lang_must_match_target
from tests.azure import runway_config

BASE_CONF = {"task": "publishArtifact", "lang": "python", "target": ["blob"]}


class TestPublishArtifact(unittest.TestCase):
    def test_lang_must_match_target(self):
        config = {"lang": "sbt", "target": ["blob"]}
        lang_must_match_target(config)

    def test_lang_must_match_target_wrong_sbt_target(self):
        config = {"lang": "sbt", "target": ["pypi"]}
        with pytest.raises(vol.Invalid):
            lang_must_match_target(config)

    def test_lang_must_match_target_wrong_python_target(self):
        config = {"lang": "python", "target": ["ivy"]}
        with pytest.raises(vol.Invalid):
            lang_must_match_target(config)

    @mock.patch("runway.DeploymentStep.KeyvaultClient.vault_and_client", return_value=(None, None))
    def test_validate_minimal_schema(self, _):
        conf = {**runway_config(), **BASE_CONF}

        victim(ApplicationVersion("dev", "v", "branch"), conf)

    @mock.patch("runway.DeploymentStep.KeyvaultClient.vault_and_client", return_value=(None, None))
    def test_validate_schema_invalid_target(self, _):
        conf = {**runway_config(), **BASE_CONF, "target": ["WRONG"]}

        with pytest.raises(vol.MultipleInvalid):
            victim(ApplicationVersion("dev", "v", "branch"), conf)

    @mock.patch("runway.DeploymentStep.KeyvaultClient.vault_and_client", return_value=(None, None))
    def test_validate_schema_invalid_target(self, _):
        conf = {**runway_config(), **BASE_CONF, "target": ["ivy"]}

        with pytest.raises(vol.Invalid):
            victim(ApplicationVersion("dev", "v", "branch"), conf)

        conf = {**runway_config(), **BASE_CONF, **{"lang": "sbt", "target": ["pypi"]}}

        with pytest.raises(vol.Invalid):
            victim(ApplicationVersion("dev", "v", "branch"), conf)
