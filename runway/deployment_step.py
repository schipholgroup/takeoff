from runway.azure.build_docker_image import DockerImageBuilder
from runway.azure.create_application_insights import CreateDatabricksApplicationInsights
from runway.azure.create_databricks_secrets import CreateDatabricksSecrets
from runway.azure.configure_eventhub import ConfigureEventhub
from runway.azure.deploy_to_databricks import DeployToDatabricks
from runway.azure.deploy_to_k8s import DeployToK8s
from runway.azure.k8s_image_rolling_update import K8sImageRollingUpdate
from runway.azure.publish_artifact import PublishArtifact
from runway.build_artifact import BuildArtifact

deployment_steps = {
    "buildArtifact": BuildArtifact,
    "buildDockerImage": DockerImageBuilder,
    "createApplicationInsights": CreateDatabricksApplicationInsights,
    "createDatabricksSecrets": CreateDatabricksSecrets,
    "configureEventhub": ConfigureEventhub,
    "deployToDatabricks": DeployToDatabricks,
    "deployToK8s": DeployToK8s,
    "k8sImageRollingUpdate": K8sImageRollingUpdate,
    "publishArtifact": PublishArtifact,
}
