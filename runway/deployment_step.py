from runway.build_docker_image import DockerImageBuilder
from runway.create_application_insights import CreateDatabricksApplicationInsights
from runway.create_appservice_and_webapp import CreateAppserviceAndWebapp
from runway.create_databricks_secrets import CreateDatabricksSecrets
from runway.create_eventhub_consumer_groups import CreateEventhubConsumerGroups
from runway.create_eventhub_producer_policies import CreateEventhubProducerPolicies
from runway.deploy_to_databricks import DeployToDatabricks
from runway.deploy_to_k8s import DeployToK8s, DeployToVnetK8s
from runway.upload_to_blob import UploadToBlob
from runway.publish_artifact import PublishArtifact

deployment_steps = {
    "uploadToBlob": UploadToBlob,
    "buildDockerImage": DockerImageBuilder,
    "createApplicationInsights": CreateDatabricksApplicationInsights,
    "deployWebAppService": CreateAppserviceAndWebapp,
    "createDatabricksSecrets": CreateDatabricksSecrets,
    "createEventhubConsumerGroups": CreateEventhubConsumerGroups,
    "createEventhubProducerPolicies": CreateEventhubProducerPolicies,
    "deployToDatabricks": DeployToDatabricks,
    "deployToK8s": DeployToK8s,
    "deployToVnetK8s": DeployToVnetK8s,
    "publishArtifact": PublishArtifact,
}
