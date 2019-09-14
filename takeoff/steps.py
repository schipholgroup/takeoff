from takeoff.azure.build_docker_image import DockerImageBuilder
from takeoff.azure.configure_eventhub import ConfigureEventHub
from takeoff.azure.create_application_insights import CreateApplicationInsights
from takeoff.azure.create_databricks_secrets import CreateDatabricksSecretsFromVault
from takeoff.azure.deploy_to_databricks import DeployToDatabricks
from takeoff.azure.deploy_to_kubernetes import DeployToKubernetes
from takeoff.azure.publish_artifact import PublishArtifact
from takeoff.build_artifact import BuildArtifact

steps = {
    "build_artifact": BuildArtifact,
    "build_docker_image": DockerImageBuilder,
    "create_application_insights": CreateApplicationInsights,
    "create_databricks_secrets_from_vault": CreateDatabricksSecretsFromVault,
    "configure_eventhub": ConfigureEventHub,
    "deploy_to_databricks": DeployToDatabricks,
    "deploy_to_kubernetes": DeployToKubernetes,
    "publish_artifact": PublishArtifact,
}
