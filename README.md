# Pyspark streaming deployment

What does it do?

![deployment](img/deployment_flow.png)

# Setting it up
This package is used as dependency in other project to consolidate deployment and testing in pyspark streaming applications (though batch applications are also supported)

To use this package for deployment simply add the following to your `setup.py`
```
extras_require={
    'deploy': [
        'pyspark-streaming-deployment==1.0'
    ]
},
dependency_links=[
    "git+https://{}@github.com/Schiphol-Hub/pyspark-streaming-deployment.git"
    "@master"
    "#egg=pyspark-streaming-deployment-1.0".format(os.environ['GITHUB_TOKEN'])
]
```
To finish setting up CI/CD VSTS must have a `GITHUB_TOKEN` passed to the docker-compose script containing a github token that has access to [https://github.com/Schiphol-Hub/](https://github.com/Schiphol-Hub/). This token is already available in VSTS;

1. Edit your build definition and navigate to `Variables`
2. Hit `Variable groups` and `Link variable group`
3. Choose `github` and save your definition

In your `.vsts-ci.yaml` you can use these steps and docker commands to (choose any of the following that are applicable to your application):

* Run linting

    To customise linting copy-paste the `.flake8` file to the root of your project, otherwise the defaults are ran (which you most likely don't want)
    ```
    - task: DockerCompose@0
      displayName: Run python linting
      inputs:
        dockerComposeCommand: |
          run --rm pyspark bash -c "pip install --process-dependency-links .[deploy] && run_linting"
    ```
* Run tests

    To customise code coverage settings copy-paste the `.coveragerc` file to the root of your project, otherwise the defaults are ran (which you most likely don't want)
    ```
    - task: DockerCompose@0
      displayName: Run python tests
      inputs:
        dockerComposeCommand: |
          run --rm pyspark bash -c "pip install --process-dependency-links .[deploy] && run_tests"
    ```

* Publish test results
    In order for VSTS to nicely display your test results, you need to publish the results of the tests (which is different than the results of the coverage). Obviously, your tests need to have run before you can publish the results.
    ```
    - task: PublishTestResults@2
      inputs:
        testResultsFiles: $(System.DefaultWorkingDirectory)/testresults.xml
    ```

* Publish code coverage
    In order to get your coverage picked up by VSTS, you need to 'publish' the results. This task should only be run after the tests have been (successfully) run and the coverage results are available.
    ```
    - task: PublishCodeCoverageResults@1
      displayName: 'Publish coverage results'
      inputs:
        codeCoverageTool: 'cobertura'
        summaryFileLocation: $(System.DefaultWorkingDirectory)/coverage.xml
        reportDirectory: $(System.DefaultWorkingDirectory)/htmlcov
        failIfCoverageEmpty: true
    ```

* Run deployment

    ```
    - task: DockerCompose@0
      displayName: Deploy to Databricks and Azure
      inputs:
        dockerComposeCommand: |
          run --rm python bash -c "pip install --process-dependency-links .[deploy] && run_deployment"
      env:
        AZURE_SP_USERNAME_DEV: $(azure_sp_username_dev)
        AZURE_SP_PASSWORD_DEV: $(azure_sp_password_dev)
        AZURE_SP_USERNAME_ACP: $(azure_sp_username_acp)
        AZURE_SP_PASSWORD_ACP: $(azure_sp_password_acp)
        AZURE_SP_USERNAME_PRD: $(azure_sp_username_prd)
        AZURE_SP_PASSWORD_PRD: $(azure_sp_password_prd)
        AZURE_SP_TENANTID: $(azure_sp_tenantid)
        AZURE_DATABRICKS_HOST: ${azure_databricks_host}
        AZURE_DATABRICKS_TOKEN_DEV: ${azure_databricks_token_dev}
        AZURE_DATABRICKS_TOKEN_ACP: ${azure_databricks_token_acp}
        AZURE_DATABRICKS_TOKEN_PRD: ${azure_databricks_token_prd}
        SUBSCRIPTION_ID: ${SUBSCRIPTION_ID}
        GITHUB_TOKEN: ${github_token}
        REGISTRY_USERNAME: ${registry_username}
        REGISTRY_PASSWORD: ${registry_password}
        AZURE_SHARED_BLOB_USERNAME: $(azure_shared_blob_username)
        AZURE_SHARED_BLOB_PASSWORD: $(azure_shared_blob_password)
    ```

This will run a deployment based on the `deployment.yml` in the root of your project, an example is:

```yaml
steps:
- task: deployToAdls
- task: deployWebAppService
- task: deployWebAppService
  appService:
    name: name
    sku:
      prd:
        name: B1
        capacity: 1
        tier: Basic
      acp:
        name: B1
        capacity: 1
        tier: Basic
      dev:
        name: B1
        capacity: 1
        tier: Basic
- task: createEventhubConsumerGroups
  groups:
    - eventhubEntity: sdhdevciss
      consumerGroup: consumerGroupName1
    - eventhubEntity: sdhdevciss
      consumerGroup: consumerGroupName2
- task: createDatabricksSecrets
- task: uploadToBlob
  lang: {sbt,maven,python}
- task: buildDockerImage
  dockerfiles:
    - file: Dockerfile
      postfix: ''
    - file: Dockerfile_pyspark
      postfix: 'pyspark'
- task: deployToDatabricks
  config:  >
    {
      "name": "__generated_value__",
      "new_cluster": {
        "spark_version": "4.2.x-scala2.11",
        "node_type_id": "Standard_DS3_v2",
        "spark_conf": {
          "spark.sql.warehouse.dir": "dbfs:/mnt/sdh/data/raw/managedtables",
          "spark.databricks.delta.preview.enabled": "true",
          "spark.sql.hive.metastore.jars": "builtin",
          "spark.sql.execution.arrow.enabled": "true",
          "spark.sql.hive.metastore.version": "1.2.1"
        },
        "spark_env_vars": {
          "PYSPARK_PYTHON": "/databricks/python3/bin/python3"
        },
        "num_workers": 2,
        "cluster_log_conf": {
          "dbfs": {
            "destination": "dbfs:/mnt/sdh/logs/{name}"
          }
        }
      },
      "email_notifications": {
        "on_start": ["b5u1o2u2g4r7q3c2@digital-airport.slack.com"],
        "on_success": ["b5u1o2u2g4r7q3c2@digital-airport.slack.com"],
        "on_failure": ["b5u1o2u2g4r7q3c2@digital-airport.slack.com"]
      },
      "max_retries": 5,
      "libraries": [
        {
          "jar": "dbfs:/mnt/sdh/libraries/spark-cosmos-sink/spark-cosmos-sink-0.2.5.jar"
        }
      ],
      "spark_python_task": {
        "python_file": "__generated_value__",
        "parameters": "__generated_list__"
      }
    }
```

# Local development

Make sure you have installed and updated docker

Run linting and tests with:

```bash
docker-compose run --rm python bash -c "pip install -e .[lint] && flake8"
docker-compose run --rm python bash -c "pip install -e .[test] && pytest tests"
```
