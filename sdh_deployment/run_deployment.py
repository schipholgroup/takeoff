import json
from yaml import load
from dataclasses import dataclass

from sdh_deployment.util import get_tag, get_branch, get_short_hash


@dataclass(frozen=True)
class ApplicationVersion(object):
    environment: str
    version: str


def load_yaml() -> dict:
    file = open("deployment.yml", "r")
    config_file = file.readlines()
    return load(config_file)


def get_environment() -> ApplicationVersion:
    tag = get_tag()
    branch = get_branch()
    git_hash = get_short_hash()

    if tag:
        return ApplicationVersion("PRD", tag)
    elif branch == "master":
        return ApplicationVersion("ACP", "SNAPSHOT")
    else:
        return ApplicationVersion("DEV", git_hash)


def main():
    env = get_environment()
    config = load_yaml()

    for step in config["steps"]:
        if step["task"] == "deployToAdls":
            from sdh_deployment.deploy_to_adls import DeployToAdls

            DeployToAdls.deploy_to_adls(env)

        elif step["task"] == "applicationInsights":
            from sdh_deployment.create_application_insights import (
                CreateApplicationInsights
            )

            CreateApplicationInsights.create_application_insights(env)

        elif step["task"] == "deployWebAppService":
            from sdh_deployment.create_appservice_and_webapp import (
                CreateAppserviceAndWebapp
            )

            CreateAppserviceAndWebapp.create_appservice_and_webapp(env, step)

        elif step["task"] == "createDatabricksSecrets":
            from sdh_deployment.create_databricks_secrets import (
                CreateDatabricksSecrets
            )

            CreateDatabricksSecrets.create_databricks_secrets(env)

        elif step["task"] == "createEventhubConsumerGroups":
            from sdh_deployment.create_eventhub_consumer_groups import (
                CreateEventhubConsumerGroups,
                EventHubConsumerGroup,
            )

            groups = [
                EventHubConsumerGroup(group["eventhubEntity"], group["consumerGroup"])
                for group in step["groups"]
            ]
            CreateEventhubConsumerGroups.create_eventhub_consumer_groups(env, groups)

        elif step["task"] == "deployToDatabricks":
            from sdh_deployment.deploy_to_databricks import (
                DeployToDatabricks
            )

            DeployToDatabricks.deploy_to_databricks(env, json.loads(step["config"]))

        else:
            task = step["task"]
            raise Exception(
                f"Deployment step {task} is unknown, please check the config"
            )
