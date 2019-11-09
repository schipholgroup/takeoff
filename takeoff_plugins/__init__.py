import logging

from takeoff.application_version import ApplicationVersion
from takeoff.credentials.branch_name import BranchName
from takeoff.util import get_tag

logger = logging.getLogger(__name__)


def deploy_env_logic(config: dict) -> ApplicationVersion:
    branch = BranchName(config).get()
    tag = get_tag()

    if tag:
        return ApplicationVersion("PRD", str(tag), branch)
    elif branch == "master":
        return ApplicationVersion("ACP", "SNAPSHOT", branch)
    else:
        logger.info("Not deploying feature branches")
        exit(0)
