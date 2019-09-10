---
layout: page
title: Getting started
rank: 1
permalink: getting-started
---

# Getting started

The easiest way to use Takeoff for your project is to use the prebuilt Docker image available [here](DOCKERHUB LINK). Using this prebuilt image, you'll
need to add 2 additional files to your project in order for Runway to function correctly.

## Takeoff Files
Takeoff needs two files in the `.takeoff` directory:

`deployment.yml`
```yaml
steps:
```

{:.table}
| field | description | values
| ----- | ----------- |
| `steps` | A list containing tasks | See [Deployment steps](deployment-steps)

This is the heart of Takeoff where you can specify what must happen with your project.
As an example, let's say your project is a REST API that needs to be deployed on Kubernetes as a Docker container. Your `deployment.yml` would be something like this:
```yaml
steps:
  - task: build_docker_image
  - task: deploy_to_kubernetes
```
This example is very simple, and can be extended through various configuration options per step, as well as adding further steps.

The  other file that Takeoff requires is `config.yml`. This file is needed for 2 main reasons:
1. It tells Takeoff where it can find the credentials to your cloud vault. You define these as environment variables in your CI, which enables Takeoff to access them from within
your CI runs.
2. Once Takeoff has logged into your cloud vault, it needs to know what names have been given to the credentials and other secrets that you've stored in the vault. 

An example of a `config.yml` file is provided here. Please note that this is an Azure-specific example, and that you may need to add further lines, depending on what tasks you would
like Takeoff to execute for you.

`config.yml`
```yaml

azure:
  resource_group: "my-rg"
  location: "west europe"
  vault_name: "https://my-vault{dtap}.vault.azure.net/"
  common:
    shared_registry: acr.azurecr.io

  keyvault_keys:
    container_registry:
      username: "registry-username"
      password: "registry-password"
      registry: "registry-server"

environment_keys:
  application_name: CI_PROJECT_NAME
  branch_name: CI_COMMIT_REF_SLUG

ci_environment_keys_dev:
  azure_service_principal:
    tenant: "AZURE_TENANTID"
    client_id: "AZURE_KEYVAULT_SP_USERNAME_DEV"
    secret: "AZURE_KEYVAULT_SP_PASSWORD_DEV"

ci_environment_keys_acp:
  azure_service_principal:
    tenant: "AZURE_TENANTID"
    client_id: "AZURE_KEYVAULT_SP_USERNAME_ACP"
    secret: "AZURE_KEYVAULT_SP_PASSWORD_ACP"

ci_environment_keys_prd:
  azure_service_principal:
    tenant: "AZURE_TENANTID"
    client_id: "AZURE_KEYVAULT_SP_USERNAME_PRD"
    secret: "AZURE_KEYVAULT_SP_PASSWORD_PRD"
```

See [Takeoff config](takeoff-config) for a more detailed guide.


## Time for Takeoff!
Once you have added the aforementioned files, you're almost ready to take off. The only thing missing is for you to add
the Takeoff step to your CI configuration. Naturally every CI provider is slightly different, so your mileage may vary. The one
key feature your CI provider does need to offer is Docker support. Moreover, if you wish to build Docker images with Takeoff,
your CI provider also needs to support docker-in-docker. As an example, this is what the configuration looks like for a project
using Gitlab CI:
`.gitlab-ci.yml`
```yaml
runway:
  image: <<<DOCKERHUBLINKHERE>>>/takeoff:<<<VERSION_HERE>>>
  variables:
    DOCKER_HOST: tcp://localhost:2375
  stage: deploy
  script:
    - runway
```

You will also need to ensure that the environment variables you've told Takeoff are available (see `config.yml` above). For most 
CI providers, this means defining environment variables in your "runner" environment.
