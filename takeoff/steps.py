from takeoff.azure.build_docker_image import DockerImageBuilder
from takeoff.azure.configure_eventhub import ConfigureEventhub
from takeoff.azure.create_application_insights import CreateDatabricksApplicationInsights
from takeoff.azure.create_databricks_secrets import CreateDatabricksSecretsFromVault
from takeoff.azure.deploy_to_databricks import DeployToDatabricks
from takeoff.azure.deploy_to_k8s import DeployToK8s
from takeoff.azure.k8s_image_rolling_update import K8sImageRollingUpdate
from takeoff.azure.publish_artifact import PublishArtifact
from takeoff.build_artifact import BuildArtifact

steps = {
    "buildArtifact": BuildArtifact,
    "buildDockerImage": DockerImageBuilder,
    "createApplicationInsights": CreateDatabricksApplicationInsights,
    "createDatabricksSecretsFromVault": CreateDatabricksSecretsFromVault,
    "configureEventhub": ConfigureEventhub,
    "deployToDatabricks": DeployToDatabricks,
    "deployToK8s": DeployToK8s,
    "k8sImageRollingUpdate": K8sImageRollingUpdate,
    "publishArtifact": PublishArtifact,
}
