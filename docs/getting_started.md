---
layout: page
title: Getting started
rank: 1
permalink: getting-started
---

# Getting started

To get started Takeoff needs 4 files in your project directory and setup of [Azure Pipelines](https://azure.microsoft.com/en-us/services/devops/pipelines/)

## CI / CD

To enable CI/CD for your project a few files are needed.
`docker-compose.yaml` containing: 

```yaml
version: "3.3"
services:
  pyspark:
    image: sdhcontainerregistryshared.azurecr.io/takeoff:{{ site.project.version | escape }}-pyspark
    working_dir: /root/
    volumes:
    - type: bind
      source: ./
      target: /root
    tty: true
  python:
    image: sdhcontainerregistryshared.azurecr.io/takeoff:{{ site.project.version | escape }}-python
    working_dir: /root/
    volumes:
    - type: bind
      source: ./
      target: /root
    tty: true
    environment:
    # default Azure variables
    - BUILD_SOURCEBRANCHNAME
    - BUILD_DEFINITIONNAME
    - AZURE_TENANTID
    # credentials to DAP Azure Keyvaults
    - AZURE_KEYVAULT_SP_USERNAME_DEV
    - AZURE_KEYVAULT_SP_PASSWORD_DEV
    - AZURE_KEYVAULT_SP_USERNAME_ACP
    - AZURE_KEYVAULT_SP_PASSWORD_ACP
    - AZURE_KEYVAULT_SP_USERNAME_PRD
    - AZURE_KEYVAULT_SP_PASSWORD_PRD
```
This gives Azure Devops access to Takeoff. Additionally you need `.azure-pipelines.yml` containing:

```yaml
pool:
  vmImage: ubuntu-16.04
  
trigger:
  branches:
    include:
      - refs/*
pr: none
  
variables:
- group: "keyvault-access"
- group: "container-registry-shared"

steps:
# This task must always be the FIRST task 
- script: docker login --username ${REGISTRY_USERNAME} --password ${REGISTRY_PASSWORD} ${REGISTRY_LOGIN_SERVER}
  displayName: Login to registry
  
# Add additional tasks here
  
# This task must always be the LAST task 
- task: DockerCompose@0
  displayName: Deploy to Azure and Databricks
  inputs:
    dockerComposeCommand: |
      run --rm python takeoff
  env:
    AZURE_TENANTID: ${azure_tenantid}
    AZURE_KEYVAULT_SP_USERNAME_DEV: $(azure_keyvault_sp_username_dev)
    AZURE_KEYVAULT_SP_PASSWORD_DEV: $(azure_keyvault_sp_password_dev)
    AZURE_KEYVAULT_SP_USERNAME_ACP: $(azure_keyvault_sp_username_acp)
    AZURE_KEYVAULT_SP_PASSWORD_ACP: $(azure_keyvault_sp_password_acp)
    AZURE_KEYVAULT_SP_USERNAME_PRD: $(azure_keyvault_sp_username_prd)
    AZURE_KEYVAULT_SP_PASSWORD_PRD: $(azure_keyvault_sp_password_prd)
```

To wrap up CI/CD, add your project to [Azure Devops](https://schiphol-hub.visualstudio.com/Schiphol%20Data%20Hub/_apps/hub/ms.vss-build-web.ci-designer-hub) 
1. Choose GitHub
2. Use the existing GitHub connection
3. Choose your repository (set the filter to `All`)
4. Make sure the name of the Azure Pipeline equals your github repository name

After that link the variable groups referenced in `.azure-pipelines.yml` as described [here](https://docs.microsoft.com/en-us/azure/devops/pipelines/library/variable-groups?view=vsts&tabs=designer#use-a-variable-group)

## Deployment

Takeoff needs an additional two files in the root of your directory

`deployment.yml`
```yaml
steps:
```

{:.table}
| field | description | values
| ----- | ----------- |
| `steps` | A list containing tasks | See [Deployment steps](deployment-steps)

This is the heart of Takeoff where you can specify what must happen with your project.

## Takeoff config

Lastly it needs `takeoff_config.yaml` which contains variables for Takeoff and the basic setup to access Azure KeyVault. This is a full example.
```yaml
takeoff_azure:
  resource_group: "sdh{dtap}"
  location: "west europe"
  vault_name: "https://sdhkeyvault{dtap}.vault.azure.net/"

azure_keyvault_keys:
  azure_active_directory_user:
    username: "azure-username"
    password: "azure-password"
  azure_databricks:
    host: "azure-databricks-host"
    token: "azure-databricks-token"
  azure_container_registry:
    username: "registry-username"
    password: "registry-password"
    registry: "registry-server"
  azure_storage_account:
    account_name: "azure-shared-blob-username"
    account_key: "azure-shared-blob-password"
  azure_devops_artifact_store:
    repository_url: "artifact-store-upload-url"
    username: "artifact-store-username"
    password: "artifact-store-password"
  azure_subscription_id: "subscription-id"

devops_environment_keys_dev:
  azure_service_principal:
    tenant: "AZURE_TENANTID"
    client_id: "AZURE_KEYVAULT_SP_USERNAME_DEV"
    secret: "AZURE_KEYVAULT_SP_PASSWORD_DEV"

devops_environment_keys_acp:
  azure_service_principal:
    tenant: "AZURE_TENANTID"
    client_id: "AZURE_KEYVAULT_SP_USERNAME_ACP"
    secret: "AZURE_KEYVAULT_SP_PASSWORD_ACP"

devops_environment_keys_prd:
  azure_service_principal:
    tenant: "AZURE_TENANTID"
    client_id: "AZURE_KEYVAULT_SP_USERNAME_PRD"
    secret: "AZURE_KEYVAULT_SP_PASSWORD_PRD"

takeoff_common:
  shared_registry: sdhcontainerregistryshared.azurecr.io
  k8s_name: sdhkubernetes{dtap}
  k8s_vnet_name: sdh-kubernetes
  artifacts_shared_blob_container_name: libraries
  eventhub_namespace: sdheventhub{dtap}
  databricks_library_path: "dbfs:/mnt/libraries"
```

See [Takeoff config](takeoff-config) for a more detailed guide.

