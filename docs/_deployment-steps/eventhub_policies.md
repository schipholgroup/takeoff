---
layout: page
title: Create producer policies
date: 2019-01-16
summary: Create Eventhub producer policies
permalink: deployment-step/eventhub-producer-policies
category: Eventhub
---

# Create producer policies for pushing to eventhub

This is only used to create producer policies. Consumer policies are automatically created when creating an [EventHub consumer group](eventhub-consumer-groups)

## Deployment

Add the following task to `deployment.yaml`:

```yaml
- task: createEventhubProducerPolicies
  policies:
  - eventhubEntity: my-eventhub-entity
```

{:.table}
| field | description
| ----- | -----------
| `policies` | A list of key-value pairs containing the eventhub entities for which to create a producer policies
| `policies[].eventhubEntity` | The name of the existing EventHub 

## Takeoff config
Make sure `takeoff_config.yaml` contains the following `azure_keyvault_keys`:

  ```yaml
  azure_databricks:
    host: "azure-databricks-host"
    token: "azure-databricks-token"
  azure_subscription_id: "subscription-id"
  ```
 
and these `takeoff_common` keys:
  ```yaml
  eventhub_namespace: sdheventhub{dtap}
  ```
