import logging

from runway.ApplicationVersion import ApplicationVersion
from runway.util import get_tag, get_branch, get_short_hash, get_full_yaml_filename, load_yaml

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


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
    deployment_config = load_yaml(get_full_yaml_filename("deployment"))
    runway_config = load_yaml(get_full_yaml_filename("runway_config"))

    for task_config in deployment_config["steps"]:
        task = task_config["task"]
        task_config.update(runway_config)
        logger.info("*" * 76)
        logger.info("{:10s} {:13s} {:40s} {:10s}".format("*" * 10, "RUNNING TASK:", task, "*" * 10))
        logger.info("*" * 76)
        run_task(env, task, task_config)


def run_task(env: ApplicationVersion, task: str, task_config):
    from runway.deployment_step import deployment_steps

    if task not in deployment_steps:
        raise ValueError(f"Deployment step {task} is unknown, please check the config")
    else:
        return deployment_steps[task](env, task_config).run()
