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
| `create_consumer_groups` __[optional]__ | Contains the specification for each consumer group 
| `create_consumer_groups.eventhub_entity_naming` | The name of the existing EventHub 
| `create_consumer_groups.consumer_group` __[optional]__ | The name of the consumer group to be created
| `create_consumer_groups.create_databricks_secret` | Whether a Databricks secret should be created for the consumer group | One of `true`, `false`
| `create_producer_policies` __[optional]__ | Contains the specification for each producer policy
| `create_producer_policies.eventhub_entity_naming` | The name of the existing EventHub 
| `create_producer_policies.producer_policy` | The name of producer policy to be created
| `create_producer_policies.create_databricks_secret` | Whether a Databricks secret should be created for the producer policy | One of `true`, `false`

## Takeoff config
Credentials for a Azure Active Directory user (username, password) must be available in your cloud vault. In addition Databricks credentials and your subscription ID must be available in the KeyVault.

Make sure `.takeoff/config.yaml` contains the following keys:

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
  create_consumer_groups:
    - eventhub_entity_naming: some-eventhub{env}
      consumer_group: some-consumer-group
```

Full configuration example. This create one consumer group for `entity1prd` with name `consgroup1` and additionally create a Databricks secret in scope `myapp` with name `entity1prd-connection-string`
Also, this creates two producer policies for `entity2prd` with name `policy2` and `entity3prd` with name `policy2`. For the latter it creates a Databricks secret in scope `myapp` with name `entity3prd-connection-string`

```yaml
- task: configure_eventhub
  create_consumer_groups:
    - eventhub_entity_naming: entity1{env}
      consumer_group: consgroup1
      create_databricks_secret: true
  create_producer_policies:
    - eventhub_entity_naming: entity3{env}
      producer_policy: policy1
      create_databricks_secret: false
    - eventhub_entity_naming: entity2{env}
      producer_policy: policy2
      create_databricks_secret: true
```