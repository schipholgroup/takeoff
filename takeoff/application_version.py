import re
from dataclasses import dataclass

from takeoff.util import get_tag


@dataclass(frozen=True)
class ApplicationVersion(object):
    environment: str
    version: str
    branch: str

    @property
    def on_feature_branch(self) -> bool:
        tag_pattern = re.compile("[0-9a-f]{7}")
        return True if tag_pattern.match(self.version) else False

    @property
    def on_release_tag(self):
        tag = get_tag()
        return tag is not None

    @property
    def artifact_tag(self) -> str:
        if self.on_feature_branch:
            return self.branch
        else:
            return self.version

    @property
    def environment_formatted(self):
        return self.environment.lower()
