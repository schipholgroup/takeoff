---
layout: page
title: Deploy to Kubernetes
date: 2019-09-13
summary: Deploy a provided Kubernetes deployment/service/secret 
permalink: deployment-step/deploy-to-kubernetes
category: Kubernetes
---

# Deploy to Kubernetes

Deploy a Kubernetes resource, as well as optionally a Kubernetes secret containing your Docker registry credentials. This
 secret containing the Docker registry credentials is always called "acr-auth". Also can create a Kubernetes secret
of any secrets available in your cloud vault that match the application name. This Kubernetes secret will be given the name: 
{application_name}-secret. All cloud vault secrets will be stored in a key-value form in this single Kubernetes Secret.
If any of the Kubernetes resources already exists, this step will update them where appropriate (similar to what the 
`kubectl apply -f` command will do. In some cases, you may wish to restart a Kubernetes resource, even if the Kubernetes 
yaml configuration has not changed. An example of this is if you build a new Docker image, with the same tag. The default Kubernetes 
behaviour is to not restart the resource. Takeoff allows you to override this behaviour if so desired. 

This task is usually used in combination with [Build Docker Image](build-docker-image) (assuming your Kubernetes config references the image that is built)

## Deployment
Add the following task to `deployment.yaml`:

```yaml
- task: deploy_to_kubernetes
  kubernetes_config_path: my_kubernetes_config.yml.j2
```

This should be after the [build_docker_image](build-docker-image) task if used together.

{:.table}
| field | description | value
| ----- | ----------- 
| `kubernetes_config_path` | The path to a `yml` [jinja_templated](http://jinja.pocoo.org/) Kubernetes deployment config | Mandatory value, must be a valid path in the repository |
| `image_pull_secret` | Whether or not to create Kubernetes image pull secret to allow pulling images from your container registry. | Defaults to True, with `secret_name=registry-auth` and `namespace=default` |
| `image_pull_secret.create` | Whether or not to create Kubernetes image pull secret to allow pulling images from your container registry. | Defaults to True
| `image_pull_secret.secret_name` | The name of secret | Defaults to `secret_name`
| `image_pull_secret.namespace` | The namespace where the secret should be created in | Default to `default` 
| `restart_unchanged_resources` | Whether or not to restart unchanged Kubernetes resources. Takeoff will attempt to restart all unchanged resources, which may result in error messages in the 
 logs, as not all resources are 'restartable' | Boolean, defaults to False. | 


An example of `kubernetes_config_path.yml.j2` 

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
        imagePullPolicy: {{secret_pull_policy}}
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
---
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
```

An explanation for the Jinja templated values. These values get resolved automatically during deployment.

{:.table}
| field | description 
| ----- | ----------- 
| `docker_tag` | The docker tag to apply. In a D/T/A/P setup, this will allow you to point to the image that was built in a previous step in your Takeoff config without explicitly specifying this

Any other templated variable, such as `{{secret_pull_policy}}` is a reference to a cloud vault key. The task will pull all secrets from the cloud vault prefixed with you application name and resolve them in the template.
For the example above, if your application name is `myapp`, then a secret in your cloud vault must be `myapp-secret-pull-policy` or `myapp-secret_pull_policy`. The prefix gets removed by Takeoff and key `secret_pull_policy` with it's value will be passed into the template. Hyphens `-` get normalized to underscores `_`.

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
Minimum Takeoff deployment configuration example to deploy Kubernetes resources. This will not create image pull secrets:
```yaml
steps:
- task: deploy_to_kubernetes
  kubernetes_config_path: my_kubernetes_config.yml.j2
  image_pull_secret: 
    create: False
```

Extended configuration example, where we have explicitly disabled the creation of kubernetes secrets by Takeoff. In this case,
we also want to restart the resources, even if their Kubernetes yaml config is unchanged. It will also create image pull secrets in namespace `default` with name `registry-auth`.

```yaml
steps:
- task: deploy_to_kubernetes
  kubernetes_config_path: my_kubernetes_config.yml.j2
  image_pull_secret: 
    create: True
    
  restart_unchanged_resources: true
```

### Eventhub producer policy secrets
Eventhub producer policy secrets from [`configure_eventhub`](deployment-step/configure-eventhub) are available during this task. This make is possible for the configuration below:
```yaml
steps:
  - task: configure_eventhub
    create_producer_policies:
      - eventhub_entity_naming: entity1
      - eventhub_entity_naming: entity2
  - task: deploy_to_kubernetes
    kubernetes_config_path: my_kubernetes_config.yml.j2
```
with `my_kubernetes_config.yml.j2`
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: armada-connections
data:
  entity1-secret: {{ entity1_connection_string }}
  entity2-secret: {{ entity2_connection_string }}
```

The jinja variables `entity1_connection_string` and `entity2_connection_string` are named by your `eventhub_entity_naming` in `create_producer_policies`, posfixed with `connection_string`.
