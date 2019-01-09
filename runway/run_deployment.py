import logging

from yaml import load

from runway.ApplicationVersion import ApplicationVersion
from runway.util import get_tag, get_branch, get_short_hash

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def load_yaml(path: str) -> dict:
    with open(path, "r") as f:
        config_file = f.read()
    return load(config_file)


def get_environment() -> ApplicationVersion:
    tag = get_tag()
    branch = get_branch()
    git_hash = get_short_hash()

    if tag:
        return ApplicationVersion("PRD", str(tag), branch)
    elif branch == "master":
        return ApplicationVersion("ACP", "SNAPSHOT", branch)
    else:
        return ApplicationVersion("DEV", git_hash, branch)


def main():
    env = get_environment()
    deployment_config = load_yaml("deployment.yml")
    runway_config = load_yaml("runway_config.yaml")

    for task_config in deployment_config["steps"]:
        task = task_config["task"]
        task_config.update(runway_config)
        logger.info("*" * 76)
        logger.info(
            "{:10s} {:13s} {:40s} {:10s}".format(
                "*" * 10, "RUNNING TASK:", task, "*" * 10
            )
        )
        logger.info("*" * 76)
        run_task(env, task, task_config)


def run_task(env: ApplicationVersion, task: str, task_config):
    from runway.deployment_step import deployment_steps
    if task not in deployment_steps:
        raise ValueError(
            f"Deployment step {task} is unknown, please check the config"
        )
    else:
        return deployment_steps[task](env, task_config).run()
