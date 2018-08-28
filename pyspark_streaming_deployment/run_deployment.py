from yaml import load, dump

from pyspark_streaming_deployment.util import get_tag, get_branch, get_short_hash


def main():
    tag = get_tag()
    branch = get_branch()
    git_hash = get_short_hash()

    if tag:
        environment = 'PRD'
        version = tag
    elif branch == 'master':
        environment = 'ACP'
        version = 'SNAPSHOT'
    else:
        environment = 'DEV'
        version = git_hash

    file = open("test.yml", "r")
    config_file = file.readlines()
    config = load(config_file)

    for step in config['steps']:
        if step['task'] == 'deployToAdls':
            from pyspark_streaming_deployment.deploy_to_adls import \
                deploy_to_adls
            deploy_to_adls(environment, version)
        elif step['task'] == 'applicationInsights':
            from pyspark_streaming_deployment.create_application_insights \
                import create_application_insights
            create_application_insights(environment)
        elif step['task'] == 'deployAppService':
            from pyspark_streaming_deployment.create_appservice_and_webapp \
                import create_appservice_and_webapp
            create_appservice_and_webapp(environment, step)
        elif step['task'] == 'createDatabricksSecrets':
            from pyspark_streaming_deployment.create_databricks_secrets \
                import create_databricks_secrets
            create_databricks_secrets(environment)
        elif step['task'] == 'createEventhubConsumerGroups':
            from pyspark_streaming_deployment.create_eventhub_consumer_groups \
                import create_eventhub_consumer_groups, EventHubConsumerGroup
            groups = [EventHubConsumerGroup(entity, group) for entity, group in step['groups'].items()]
            create_eventhub_consumer_groups(environment, groups)
        elif step['task'] == 'deployToDatabricks':
            from pyspark_streaming_deployment.deploy_to_databricks \
                import deploy_to_databricks
            deploy_to_databricks(version, environment, step['config'])
        else:
            task = step['task']
            raise Exception(f'Deployment step {task} is unknown, please check the config')
