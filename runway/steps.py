from runway.azure.build_docker_image import DockerImageBuilder
from runway.azure.create_application_insights import CreateDatabricksApplicationInsights
from runway.azure.create_databricks_secrets import CreateDatabricksSecrets
from runway.azure.create_eventhub_consumer_groups import CreateEventhubConsumerGroups
from runway.azure.create_eventhub_producer_policies import CreateEventhubProducerPolicies
from runway.azure.deploy_to_databricks import DeployToDatabricks
from runway.azure.deploy_to_k8s import DeployToK8s
from runway.azure.k8s_image_rolling_update import K8sImageRollingUpdate
from runway.azure.publish_artifact import PublishArtifact
from runway.build_artifact import BuildArtifact

steps = {
    "buildArtifact": BuildArtifact,
    "buildDockerImage": DockerImageBuilder,
    "createApplicationInsights": CreateDatabricksApplicationInsights,
    "createDatabricksSecrets": CreateDatabricksSecrets,
    "createEventhubConsumerGroups": CreateEventhubConsumerGroups,
    "createEventhubProducerPolicies": CreateEventhubProducerPolicies,
    "deployToDatabricks": DeployToDatabricks,
    "deployToK8s": DeployToK8s,
    "k8sImageRollingUpdate": K8sImageRollingUpdate,
    "publishArtifact": PublishArtifact,
}
