---
layout: page
title: Deploy to Kubernetes
date: 2019-09-13
summary: Deploy a provided Kubernetes deployment/service/secret 
permalink: deployment-step/deploy-to-kubernetes
category: Kubernetes
---

# Deploy to Kubernetes

Deploy a Kubernetes service or deployment, as well as a Kubernetes secret containing your Docker registry credentials. This
 secret containing the Docker registry credentials is always called "acr-auth". Also will create a Kubernetes secret
of any secrets available in your cloud vault that match the application name. This Kubernetes secret will be given the name: 
{application_name}-secret. All cloud vault secrets will be stored in a key-value form in this single Kubernetes Secret.
If any of the Kubernetes resources already exists, this step will update them where appropriate.

This task is usually used in combination with [Build Docker Image](build-docker-image) (assuming your Kubernetes config references the image that is built)

## Deployment
Add the following task to `deployment.yaml`:

```yaml
- task: deploy_to_kubernetes
  deployment_config_path: my_deployment_config.yml.j2
  service_config_path: my_service_config.yml.j2
```

This should be after the [build_docker_image](build-docker-image) task if used together.

{:.table}
| field | description | value
| ----- | ----------- 
| `deployment_config_path` | The path to a `yml` [jinja_templated](http://jinja.pocoo.org/) [Kubernetes deployment config]() | Mandatory value, must be a valid path in the repository |
| `service_config_path` | The path to a `yml` [jinja_templated](http://jinja.pocoo.org/) [Kubernetes service config]() | Mandatory value, must be a valid path in the repository |
| `service_ips` __[optional]__ | A list of IP addresses to user per environment. Can be useful if you have a static IP address per environment | A valid IP address |


An example of `my_deployment_config.yml.j2` 

```
apiVersion: extensions/v1beta1
kind: Deployment
metadata:
  name: my-app
spec:
  template:
    metadata:
      labels:
        app: my-app
    spec:
      containers:
      - name: my-app
        image: my-docker-image:{{docker_tag}}
        imagePullPolicy: Always
        ports:
        - containerPort: 8443
        env:
        - name: SOME_SECRET
          valueFrom:
            secretKeyRef:
              name: my-app-secret
              key: some-secret
      imagePullSecrets:
      - name: acr-auth
```

An explanation for the Jinja templated values. These values get resolved automatically during deployment.

{:.table}
| field | description 
| ----- | ----------- 
| `docker_tag` | The docker tag to apply. In a D/T/A/P setup, this will allow you to point to the image that was built in a previous step in your Takeoff config without explicitly specifying this


An example of `my_service_config.yml.j2` 
```
apiVersion: v1
kind: Service
metadata:
  name: my_service
spec:
  ports:
  - port: 443
    protocol: TCP
    targetPort: 8443
  selector:
    app: my_app
  type: LoadBalancer
  loadBalancerIP: {{service_ip}}
```

An explanation for the Jinja templated values. These values get resolved automatically during deployment.

{:.table}
| field | description 
| ----- | ----------- 
| `service_ip` | The IP address to use for this service. This should differ across environments. Per environment, the service's static IP address can be specified in the Takeoff deployment configuration

## Takeoff config
Make sure `.takeoff/config.yml` contains the following keys:

```yaml
azure:
  kubernetes_naming: "my_kubernetes{env}"
  keyvault_keys:
    container_registry:
      username: "registry-username"
      password: "registry-password"
      registry: "registry-server"
```

## Examples
Minimum Takeoff deployment configuration example to deploy a Kubernetes deployment and Service:
```yaml
steps:
- task: deploy_to_kubernetes
  deployment_config_path: my_deployment_config.yml.j2
  service_config_path: my_service_config.yml.j2
```

Extended configuration example, where we have defined a static IP address per environment for the service:

```yaml
steps:
- task: deploy_to_kubernetes
  deployment_config_path: my_deployment_config.yml.j2
  service_config_path: my_service_config.yml.j2
  service_ips:
    dev: "127.0.0.1"
    acp: "0.0.0.0"
    prd: "8.8.8.8"
```
In this case, depending on what branch of the code Takeoff is running, it will apply a different value for `service_ip` to
the Kubernetes service yaml Jinja template.
