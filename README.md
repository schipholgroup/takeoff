# ![runway](img/runway.png) Runway

This package is used as dependency in other project to consolidate deployment of any application in the Azure Cloud.

Supported are:
- Azure Container Registry (building containers)
- Azure Databricks (deploying jobs)
- Azure Kubernetes Service (deploying kubernetes resources)
- Azure Applications Insights (deploying and connecting the Instrumentation Key)
- Azure Eventhub (creating policies and consumer groups)
- Azure Data Lake (uploading and downloading)

Secret/credential management is done using Azure KeyVault. Secrets are found by scanning the KeyVault and filtering on the `your-application-name-secret-name` pattern. For example: `runway-docker-password`.
Common secrets are foud using the `common-secret-name` pattern. Such as `common-azure-databricks-token-dev`. 

These values are then injected in de `Runway` container as environment variables as screaming snake case. For example `AZURE_DATABRICKS_TOKEN_DEV`.

To use this package for deployment you must have three files in your project repository.
- docker-compose.yml
- .vsts-ci.yml
- deployment.yml

For more information see the [Runway documentation](https://github.com/Schiphol-Hub/runway-docs)

## Local development

Make sure you have installed and updated docker and run linting and tests with:

```bash
docker-compose run --rm dockerception bash -c "python setup.py flake8"
docker-compose run --rm dockerception bash -c "python setup.py test"
```
