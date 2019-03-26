<p align="center">
  <img width=250" height="250" src="https://raw.githubusercontent.com/Schiphol-Hub/runway/tvc-travis/img/runway.png?token=AJS0v09SYXZhOPcfGLObz2-le35CYdjZks5ckngxwA%3D%3D">
</p>
<h2 align="center">Schiphol Runway</h2>

<p align="center">
<a href="https://travis-ci.com/Schiphol-Hub/runway"><img alt="Build Status" src="https://travis-ci.com/Schiphol-Hub/runway.svg?token=Y1xSdb7sYXYbyQLwtbLj&branch=master"></a>
<img alt="" src="https://img.shields.io/badge/python-3.7-blue.svg">
<a href="https://github.com/ambv/black"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>
</p>

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
