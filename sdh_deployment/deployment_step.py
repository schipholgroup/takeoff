from sdh_deployment.api_load_testing import LoadTester
from sdh_deployment.build_docker_image import DockerImageBuilder
from sdh_deployment.create_application_insights import CreateDatabricksApplicationInsights
from sdh_deployment.create_appservice_and_webapp import CreateAppserviceAndWebapp
from sdh_deployment.create_databricks_secrets import CreateDatabricksSecrets
from sdh_deployment.create_eventhub_consumer_groups import CreateEventhubConsumerGroups
from sdh_deployment.deploy_to_databricks import DeployToDatabricks
from sdh_deployment.deploy_to_k8s import DeployToK8s
from sdh_deployment.upload_to_blob import UploadToBlob

deployment_steps = {
    "uploadToBlob": UploadToBlob,
    "buildDockerImage": DockerImageBuilder,
    "createApplicationInsights": CreateDatabricksApplicationInsights,
    "deployWebAppService": CreateAppserviceAndWebapp,
    "createDatabricksSecrets": CreateDatabricksSecrets,
    "createEventhubConsumerGroups": CreateEventhubConsumerGroups,
    "deployToDatabricks": DeployToDatabricks,
    "deployToK8s": DeployToK8s,
    "apiLoadTesting": LoadTester
}
