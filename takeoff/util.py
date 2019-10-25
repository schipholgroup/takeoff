import base64
import importlib
import logging
import os
import pkgutil
import subprocess
from dataclasses import dataclass
from typing import Callable, List, Pattern, Union, Tuple

from git import Repo
import jinja2
from yaml import load

logger = logging.getLogger(__name__)


DEFAULT_TAKEOFF_PLUGIN_PREFIX = "takeoff_"


@dataclass(frozen=True)
class AzureSp(object):
    tenant: str
    username: str
    password: str


def render_string_with_jinja(path: str, params: dict) -> str:
    """Read a file contents and render the jinja template

    Args:
        path: path to the file to render
        params: the values to fill into the jinja template

    Returns:
        str: rendered jinja template as a string
    """
    with open(path) as file_:
        template = jinja2.Template(file_.read())
    rendered = template.render(**params)
    return rendered


def render_file_with_jinja(path: str, params: dict, parse_function: Callable) -> dict:
    """Render a file with jinja, with a provided callable.

    The callable is used to parse the file into a python object, once the jinja template has been rendered

    Args:
        path: path to the file to render
        params: the values to fill into the jinja template
        parse_function: the function to use to parse the file into a python object

    Returns:
        dict: parsed values from the file
    """
    rendered = render_string_with_jinja(path, params)
    return parse_function(rendered)


def get_tag() -> Union[None, str]:
    repo = Repo(search_parent_directories=True)
    return next((tag for tag in repo.tags if tag.commit == repo.head.commit), None)


def get_short_hash(n: int = 7) -> str:
    repo = Repo(search_parent_directories=True)
    sha = repo.head.object.hexsha
    return repo.git.rev_parse(sha, short=n)


def b64_encode(s: str) -> str:
    """Apply base64 encoding to a given string

    Args:
        s: string to encode

    Returns:
        str: base64 encoded string
    """
    return base64.b64encode(s.encode()).decode()


def b64_decode(s: str) -> str:
    """Decode a given base64-encoded string

    Args:
        s: base64 encoded string to decode

    Returns:
        str: base64 decoded string
    """
    return base64.b64decode(s).decode()


# register as a jinja2 filter to allow usage within jinja2 templates
jinja2.filters.FILTERS["b64_encode"] = b64_encode
jinja2.filters.FILTERS["b64_decode"] = b64_decode


def is_base64(target: Union[str, bytes]) -> bool:
    """Determines whether a given target (either bytes or string) is base64 encoded
    Courtesy of
    https://stackoverflow.com/questions/12315398/verify-is-a-string-is-encoded-in-base64-python

    Args:
        target: str/bytes to check for base64 encoding

    Returns:
        bool: true if target is base64 encoded
    """
    try:
        if isinstance(target, str):
            # If there's any unicode here, an exception will be thrown and the function will return false
            target_bytes = bytes(target, "ascii")
        elif isinstance(target, bytes):
            target_bytes = target
        else:
            raise ValueError("Argument must be string or bytes")
        return base64.b64encode(base64.b64decode(target_bytes)) == target_bytes
    except Exception:
        return False


def ensure_base64(s: str) -> str:
    if not is_base64(s):
        return b64_encode(s)
    return s


def get_matching_group(find_in: str, pattern: Pattern[str], group: int):
    match = pattern.search(find_in)

    if not match:
        raise ValueError(f"Couldn't find a match")

    found_groups = len(match.groups())
    if found_groups < group:
        raise IndexError(f"Couldn't find that many groups, the number of groups found is: {found_groups}")
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
    # Wheels enforce a strict naming convention. This function helps us adhere to this naming convention
    # The convention is: {distribution}-{version}(-{build tag})?-{python tag}-{abi tag}-{platform tag}.whl
    # In our case, we need to use underscores to concatenate words within a package name and version name.
    # build-tag is optional, and we do not supply it.
    return (
        f"{build_definition_name}/{build_definition_name.replace('-', '_')}-"
        f"{artifact_tag.replace('-', '_')}-py3-none-any{file_ext}"
    )


def get_main_py_name(build_definition_name: str, artifact_tag: str, file_ext: str) -> str:
    return (
        f"{build_definition_name}/{build_definition_name.replace('-', '_')}-"
        f"main-{artifact_tag.replace('-', '_')}{file_ext}"
    )


def get_jar_name(build_definition_name: str, artifact_tag: str, file_ext: str) -> str:
    return f"{build_definition_name}/{build_definition_name}-{artifact_tag}{file_ext}"


def run_shell_command(command: List[str]) -> Tuple[int, List]:
    """Runs a shell command using `subprocess.Popen`

    In addition to running any bash command, the output of process is streamed directly to the stdout.

    Returns:
        The result of the bash command. 0 for success, >=1 for failure.
    """
    process = subprocess.Popen(command, stdout=subprocess.PIPE, cwd="./", universal_newlines=True)
    output_lines = []
    while True:
        output = process.stdout.readline()
        if output == "" and process.poll() is not None:
            break
        if output:
            print(output.strip())
            output_lines.append(output)
    return process.poll(), output_lines


def load_takeoff_plugins():
    """https://packaging.python.org/guides/creating-and-discovering-plugins/"""
    plugins = {
        name: importlib.import_module(name)
        for finder, name, ispkg in pkgutil.iter_modules()
        if name.startswith(DEFAULT_TAKEOFF_PLUGIN_PREFIX)
    }
    logging.info(f"Found Takeoff plugins {plugins}")
    return plugins
