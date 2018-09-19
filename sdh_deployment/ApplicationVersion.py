import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ApplicationVersion(object):
    environment: str
    version: str
    branch: str

    @property
    def on_feature_branch(self) -> bool:
        tag_pattern = re.compile('[0-9a-f]{7}')
        return True if tag_pattern.match(self.version) else False

    @property
    def docker_tag(self) -> str:
        if self.on_feature_branch:
            return self.branch
        else:
            return self.version
