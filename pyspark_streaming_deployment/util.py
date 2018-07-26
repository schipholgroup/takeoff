import os

from git import Repo


def get_branch():
    return os.environ['BUILD_SOURCEBRANCHNAME']


def get_tag():
    repo = Repo(search_parent_directories=True)
    return next((tag for tag in repo.tags if tag.commit == repo.head.commit), None)
