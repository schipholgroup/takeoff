import base64
import os
from dataclasses import dataclass
from typing import Pattern, Callable

from git import Repo
from jinja2 import Template
from yaml import load


@dataclass(frozen=True)
class AzureSp(object):
    tenant: str
    username: str
    password: str


def render_string_with_jinja(path: str, params: dict) -> str:
    with open(path) as file_:
        template = Template(file_.read())
    rendered = template.render(**params)
    return rendered


def render_file_with_jinja(path: str, params: dict, parse_function: Callable) -> dict:
    rendered = render_string_with_jinja(path, params)
    return parse_function(rendered)


def get_branch() -> str:
    return os.environ["BUILD_SOURCEBRANCHNAME"]


def get_tag() -> str:
    repo = Repo(search_parent_directories=True)
    return next((tag for tag in repo.tags if tag.commit == repo.head.commit), None)


def get_short_hash(n: int = 7) -> str:
    repo = Repo(search_parent_directories=True)
    sha = repo.head.object.hexsha
    return repo.git.rev_parse(sha, short=n)


def get_application_name() -> str:
    return os.environ["BUILD_DEFINITIONNAME"]


def b64_encode(s: str):
    return base64.b64encode(s.encode()).decode()


def get_matching_group(find_in: str, pattern: Pattern[str], group: int):
    match = pattern.search(find_in)

    if not match:
        raise ValueError(f"Couldn't find a match")

    found_groups = len(match.groups())
    if found_groups < group:
        raise IndexError(
            f"Couldn't find that many groups, the number of groups found is: {found_groups}"
        )
    return match.groups()[group]


def has_prefix_match(find_in: str, to_find: str, pattern: Pattern[str]):
    match = pattern.search(find_in)

    if match:
        return match.groups()[0] == to_find
    return False


def load_yaml(path: str) -> dict:
    with open(path, "r") as f:
        config_file = f.read()
    return load(config_file)


def log_docker(logs_iter):
    from pprint import pprint
    for line in logs_iter:
        pprint(line)


def current_filename(__fn):
    return os.path.basename(__fn).split('.')[0]


def inverse_dictionary(d: dict):
    return {v: k for k, v in d.items()}


def subscription_id(config: dict):
    return config['runway_azure']['subscription_id']
