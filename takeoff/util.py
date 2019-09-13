import base64
import importlib
import logging
import os
import pkgutil
import subprocess
from dataclasses import dataclass
from typing import Callable, List, Pattern, Union

from git import Repo
from jinja2 import Template
from yaml import load

logger = logging.getLogger(__name__)


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


def get_tag() -> Union[None, str]:
    repo = Repo(search_parent_directories=True)
    return next((tag for tag in repo.tags if tag.commit == repo.head.commit), None)


def get_short_hash(n: int = 7) -> str:
    repo = Repo(search_parent_directories=True)
    sha = repo.head.object.hexsha
    return repo.git.rev_parse(sha, short=n)


def b64_encode(s: str):
    return base64.b64encode(s.encode()).decode()


def get_matching_group(find_in: str, pattern: Pattern[str], group: int):
    match = pattern.search(find_in)

    if not match:
        raise ValueError(f"Couldn't find a match")

    found_groups = len(match.groups())
    if found_groups < group:
        raise IndexError(f"Couldn't find that many groups, the number of groups found is: {found_groups}")
    return match.groups()[group]


def has_prefix_match(find_in: str, to_find: str, pattern: Pattern[str]) -> bool:
    """ Checks whether the first match of the provided pattern is the target string

    Args:
        find_in: String to search in
        to_find: Target string to compare the first match of the pattern to
        pattern: The pattern against which to match

    Returns:
        bool: True if the first match of the provided pattern is the target string, False otherwise
    """
    match = pattern.search(find_in)

    if match:
        return match.groups()[0] == to_find
    return False


def load_yaml(path: str) -> dict:
    with open(path, "r") as f:
        config_file = f.read()
    return load(config_file)


def current_filename(__fn):
    return os.path.basename(__fn).split(".")[0]


def inverse_dictionary(d: dict):
    return {v: k for k, v in d.items()}


def get_full_yaml_filename(filename: str) -> str:
    extensions = (".yaml", ".yml")
    for ext in extensions:
        concat_filename = os.path.join(".takeoff", f"{filename}{ext}")
        if os.path.isfile(concat_filename):
            return concat_filename
        else:
            logger.info(f"Could not find file: {concat_filename}")
    raise FileNotFoundError(f"Could not find any valid file for base_filename: {filename}")


def get_whl_name(build_definition_name: str, artifact_tag: str, file_ext: str) -> str:
    """Get the name of the whl file given an application and its current tag

    Wheels enforce a strict naming convention. This function helps us adhere to this naming convention
    The convention is: {distribution}-{version}(-{build tag})?-{python tag}-{abi tag}-{platform tag}.whl
    In our case, we need to use underscores to concatenate words within a package name and version name.
    build-tag is optional, and we do not supply it. We also assume the following values:
      - python tag = py3
      - abi tag = none
      - platform tag = any

    This function assumes that the wheel path is prefixed with the build_definition name, and therefore
    that whl's are stored in a directory named `build_definition_name`

    Args:
        build_definition_name: The base name to use. All hyphens are replaced with `_`s in the whl name to
            ensure compliance with the whl naming convention
        artifact_tag: The tag of the artifact to fetch.
        file_ext: the file extension to use. For whls this should be `.whl`
    Returns:
        str: the whl name
    """
    return (
        f"{build_definition_name}/{build_definition_name.replace('-', '_')}-"
        f"{artifact_tag.replace('-', '_')}-py3-none-any{file_ext}"
    )


def get_main_py_name(build_definition_name: str, artifact_tag: str, file_ext: str) -> str:
    """Get the name of the main_py file given an application and its current tag

    This function assumes that the main_py name follows the following pattern:
    {application_name}-main-{artifact_tag}.py

    This function assumes that the main_py path is prefixed with the build_definition name, and therefore
    that these files are stored in a directory named `build_definition_name`

    Args:
        build_definition_name: The base name to use. All hyphens are replaced with `_`s in the file name to
            ensure compliance with the naming convention
        artifact_tag: The tag of the artifact to fetch.
        file_ext: the file extension to use. For main_py this should be `.py`
    Returns:
        str: the whl name
    """
    return (
        f"{build_definition_name}/{build_definition_name.replace('-', '_')}-"
        f"main-{artifact_tag.replace('-', '_')}{file_ext}"
    )


def get_jar_name(build_definition_name: str, artifact_tag: str, file_ext: str) -> str:
    return f"{build_definition_name}/{build_definition_name}-{artifact_tag}{file_ext}"


def run_shell_command(command: List[str]) -> int:
    """Runs a shell command using `subprocess.Popen`

    In addition to running any bash command, the output of process is streamed directly to the stdout.

    Returns:
        The result of the bash command. 0 for success, >=1 for failure.
    """
    process = subprocess.Popen(command, stdout=subprocess.PIPE, cwd="./", universal_newlines=True)
    while True:
        output = process.stdout.readline()
        if output == "" and process.poll() is not None:
            break
        if output:
            print(output.strip())
    return process.poll()


def load_takeoff_plugins():
    """https://packaging.python.org/guides/creating-and-discovering-plugins/"""
    return {
        name: importlib.import_module(name)
        for finder, name, ispkg in pkgutil.iter_modules()
        if name.startswith("takeoff_")
    }
