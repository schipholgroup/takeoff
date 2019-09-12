---
layout: page
title: Create EventHub consumer groups
date: 2019-01-21
summary: Create EventHub consumer groups for given EventHub entities
permalink: deployment-step/eventhub-consumer-groups
category: Eventhub
---

# Create EventHub consumer groups

Creates [Azure EventHub](https://docs.microsoft.com/en-us/azure/event-hubs/) consumer groups in a given EventHub namespace. This will also create one EventHub consumer policy per consumer group. The name of this policy equals the name of your application.

## Deployment
Add the following task to `deployment.yaml`:

```yaml
- task: createEventhubConsumerGroups
  groups:
  - eventhub_entity: some-eventhub
    consumer_group: some-consumer-group
```

{:.table}
| field | description 
| ----- | ----------- 
| `groups` | Contains the specification for each consumer group 
| `groups[].eventhub_entity` | The name of the existing EventHub 
| `groups[].consumer_group` | The name of the consumer group to be created

## Takeoff config
Make sure `takeoff_config.yaml` contains the following `azure_keyvault_keys`:

  ```yaml
  azure_active_directory_user:
    username: "azure-username"
    password: "azure-password"
  azure_subscription_id: "subscription-id"
  ```

and these `takeoff_common` keys:
  ```yaml
  eventhub_namespace: sdheventhub{dtap}
  ```
