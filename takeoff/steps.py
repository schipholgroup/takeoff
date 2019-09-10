from takeoff.azure.build_docker_image import DockerImageBuilder
from takeoff.azure.configure_eventhub import ConfigureEventhub
from takeoff.azure.create_application_insights import CreateDatabricksApplicationInsights
from takeoff.azure.create_databricks_secrets import CreateDatabricksSecrets
from takeoff.azure.deploy_to_databricks import DeployToDatabricks
from takeoff.azure.deploy_to_kubernetes import DeployToKubernetes
from takeoff.azure.kubernetes_image_rolling_update import KubernetesImageRollingUpdate
from takeoff.azure.publish_artifact import PublishArtifact
from takeoff.build_artifact import BuildArtifact

steps = {
    "buildArtifact": BuildArtifact,
    "buildDockerImage": DockerImageBuilder,
    "createApplicationInsights": CreateDatabricksApplicationInsights,
    "createDatabricksSecrets": CreateDatabricksSecrets,
    "configureEventhub": ConfigureEventhub,
    "deployToDatabricks": DeployToDatabricks,
    "deployToKubernetes": DeployToKubernetes,
    "kubernetesImageRollingUpdate": KubernetesImageRollingUpdate,
    "publishArtifact": PublishArtifact,
}
