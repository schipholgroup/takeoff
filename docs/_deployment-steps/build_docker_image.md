---
layout: page
title: Build Docker image
date: 2019-09-10
updated: 2019-09-10
summary: Build and push Docker images
permalink: deployment-step/build-docker-image
category: Docker
---

# Build Docker image

This step allows you to build and push Docker images in your repository to your Docker registry.

## Deployment
Add the following task to `deployment.yaml`

{:.table}
| field | description | values
| ----- | ----------- |
| `task` | `"build_docker_image"`
| `credentials` | Select the credentials provider | `
| `dockerfiles` [optional]| List of more specific Docker file configurations. Consisting of:
| `dockerfiles[].file` [optional] | Alternative Docker file name
| `dockerfiles[].postfix` [optional] | Postfix for the image name, will be added before the tag
| `dockerfiles[].custom_image_name` [optional] | A custom name for the image to be used

## Takeoff config
Credentials for a Docker registry (username, password, registry) must be available in your cloud vault. Also, the [Docker cli](https://docs.docker.com/engine/reference/commandline/cli/) must be available. 

Make sure `.takeoff/config.yaml` contains the following keys:

```yaml
azure:
    keyvault_keys:
        container_registry:
          username: "acr-username"
          password: "acr-password"
          registry: "acr-registry"
```

## Examples

Assume an application name `myapp` and version `1.2.0`.
Assume a registry with name `acr.azurecr.io`

Minimum configuration example for Python. This pushes a Python wheel to PyPi. The wheel has name `myapp` and version `1.2.0`.
```
steps:
  - task: build_docker_image
```

Full configuration example. This builds and pushed two Docker images to `acr.azurecr.io/myimage-one:1.2.0` (from `Dockerfile_one`) and `acr.azurecr.io/myapp:1.2.0` (from `Dockerfile_two`) respectively

```
steps:
  - task: build_docker_image
    dockerfile:
      - file: Dockerfile_one
        postfix: "-one"
        custom_image_name: myimage
      - file: Dockerfile_two
```
