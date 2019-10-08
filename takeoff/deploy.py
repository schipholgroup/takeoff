import logging
from typing import Callable, List

from takeoff.application_version import ApplicationVersion
from takeoff.credentials.branch_name import BranchName
from takeoff.util import get_tag, get_short_hash, get_full_yaml_filename, load_yaml, load_takeoff_plugins

logger = logging.getLogger(__name__)


def deploy_env_logic(config: dict) -> ApplicationVersion:
    branch = BranchName().get(config)
    tag = get_tag()
    git_hash = get_short_hash()

    if tag:
        return ApplicationVersion("PRD", str(tag), branch)
    elif branch == "master":
        return ApplicationVersion("ACP", "SNAPSHOT", branch)
    else:
        return ApplicationVersion("DEV", git_hash, branch)


def find_env_function() -> Callable:
    """Finds the `deploy_env_logic` function.

    Returns:
        Either the default function or the first plugin function if it is found.
    """
    for plugin in load_takeoff_plugins().values():
        if hasattr(plugin, "deploy_env_logic"):
            logging.info("Using plugin 'deploy_env_logic' function")
            return plugin.deploy_env_logic
    logging.info("Using default 'deploy_env_logic' function")
    return deploy_env_logic


def get_environment(config: dict) -> ApplicationVersion:
    env_fun = find_env_function()
    return env_fun(config)


def add_takeoff_plugin_paths(dirs: List[str]):
    import sys

    sys.path.extend(dirs)


def main():
    deployment = load_yaml(get_full_yaml_filename("deployment"))
    config = load_yaml(get_full_yaml_filename("config"))
    if "plugins" in config:
        paths = config["plugins"]
        logger.info(f"Adding plugins from {paths} and current working directory")
        add_takeoff_plugin_paths(paths + ["."])

    env = get_environment(config)
    logger.info(f"Running Takeoff with application version: {env}")

    for task_config in deployment["steps"]:
        task = task_config["task"]
        logger.info("*" * 76)
        logger.info("{:10s} {:13s} {:40s} {:10s}".format("*" * 10, "RUNNING TASK:", task, "*" * 10))
        logger.info("*" * 76)
        run_task(env, task, {**task_config, **config})


def run_task(env: ApplicationVersion, task: str, task_config: dict):
    from takeoff.steps import steps

    if task not in steps:
        raise ValueError(f"Deployment step {task} is unknown, please check the config")
    else:
        return steps[task](env, task_config).run()  # type: ignore
