---
layout: page
title: Configure EventHub
date: 2019-01-21
updated: 2019-09-13
summary: Configure EventHub with consumer groups and producer policies
permalink: deployment-step/configure-eventhub
category: EventHub
---

# Configure EventHub

Creates [Azure EventHub](https://docs.microsoft.com/en-us/azure/event-hubs/) consumer groups in a given EventHub namespace. This will also create one EventHub consumer policy per consumer group. The name of this policy equals the name of your application. In addition, also creates producer policies.

## Deployment
Add the following task to `deployment.yaml`:

```yaml
- task: configure_eventhub
  create_consumer_groups:
    - eventhub_entity_naming: some-eventhub
      consumer_group: some-consumer-group
      create_databricks_secret: false
  create_producer_policies:
    - eventhub_entity_naming: some-eventhub
      producer_policy: some-producer-policy
      create_databricks_secret: false
```

{:.table}
| field | description | values
| ----- | ----------- | ------
| `task` | `"configure_eventhub"`
| `credentials` __[optional]__ | The source of the credentials to use. | Defaults to `azure_keyvault`. One of: `azure_keyvault`
| `credentials_type` __[optional]__ | The type of the credentials to use. | Defaults to `active_directory_user`. One of: `service_principal`, `active_directory_user`
| `create_consumer_groups` __[optional]__ | Contains the specification for each consumer group 
| `create_consumer_groups.eventhub_entity_naming` | The name of the existing EventHub 
| `create_consumer_groups.consumer_group` __[optional]__ | The name of the consumer group to be created
| `create_consumer_groups.create_databricks_secret` | Whether a Databricks secret should be created for the consumer group | One of `true`, `false`
| `create_consumer_groups.append_env_to_databricks_secret_name` | Whether to append the Databricks secret name with the env | One of `true`, `false`
| `create_producer_policies` __[optional]__ | Contains the specification for each producer policy
| `create_producer_policies.eventhub_entity_naming` | The name of the existing EventHub 
| `create_producer_policies.producer_policy` | The name of producer policy to be created
| `create_producer_policies.create_databricks_secret` | Whether a Databricks secret should be created for the producer policy | One of `true`, `false`

## Takeoff Context
The producer connection string and consumer group secrets are also available during the [`deploy_to_kubernetes`][deployment-step/deploy-to-kubernetes] step. This makes it possible to inject them as templated secret to a kubernetes yaml. See the [`deploy_to_kubernetes`][deployment-step/deploy-to-kubernetes] page for more information.

## Takeoff config
Takeoff supports 2 authentication types. You can choose either:
1. Service Principal
2. Active Directory User
These credentials must be available in your Azure Keyvault, and the correct mapping with the secret names should be available in your `config.yaml`. Moreover, Databricks credentials configuration must also
be in place in order to allow for Databricks secret creation.

<p class='note warning'>
Currently Takeoff only supports Azure Keyvault as the source for credentials for use with `configure_eventhub`
</p>

The default is to use a Active Directory User. For a service principal, ensure the following `keyvault_keys` are defined in your `config.yaml`:
```yaml
azure:
  keyvault_keys:
    service_principal:
      client_id: "sp-client-id"
      secret: "sp-secret"
      tenant: "azure-tenant"
```
To use a service principal, you can add the following into your `deployment.yaml`:
```yaml
- task: configure_eventhub
  credentials: azure_keyvault
  credentials_type: service_principal
```

If you prefer to use an Active Directory User, please ensure the following `keyvault_keys` are defined:
```yaml
azure:
  keyvault_keys:
    active_directory_user:
      username: "aad-username"
      password: "aad-password"
```
To use a service principal, you can add the following into your `deployment.yaml`:
```yaml
- task: configure_eventhub
  credentials: azure_keyvault
  credentials_type: active_directory_user
```

A more complete `config.yaml` example:
```yaml
azure:
  eventhub_naming: "eventhub{env}"
  keyvault_keys:
    active_directory_user:
      username: "aad-username"
      password: "aad-password"
    databricks:
      host: "azure-databricks-host"
      token: "azure-databricks-token"
    subscription_id: "subscription-id"
```

Here `eventhub_naming` is the naming rule for your EventHub namespace.

## Examples

Assume an application name `myapp` and version `1.2.0`. This goes to `prd` environment.

Minimum configuration example for one consumer group. This will create a single consumer group (if it didn't already exists) for `some-eventhubprd` with name `some-eventhubprd-connection-string`
```yaml
- task: configure_eventhub
  credentials: azure_keyvault
  credentials_type: active_directory_user
  create_consumer_groups:
    - eventhub_entity_naming: some-eventhub{env}
      consumer_group: some-consumer-group
```

Full configuration example. This create one consumer group for `entity1prd` with name `consgroup1` and additionally create a Databricks secret in scope `myapp` with name `entity1prd-connection-string`
Also, this creates two producer policies for `entity2prd` with name `myapp-send-policy` and `entity3prd` with name `myapp-send-policy`. For the latter it creates a Databricks secret in scope `myapp` with name `entity3prd-connection-string`

```yaml
- task: configure_eventhub
  credentials: azure_keyvault
  credentials_type: active_directory_user
  create_consumer_groups:
    - eventhub_entity_naming: entity1{env}
      consumer_group: consgroup1
      create_databricks_secret: true
  create_producer_policies:
    - eventhub_entity_naming: entity3{env}
      create_databricks_secret: false
    - eventhub_entity_naming: entity2{env}
      create_databricks_secret: true
```