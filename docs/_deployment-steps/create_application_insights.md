---
layout: page
title: Create Application Insights
date: 2019-09-11
updated: 2019-09-11
summary: Create an Azure Application Insights client
permalink: deployment-step/application-insights
category: Azure
---

# Create Application Insights

This step allows you to create an [Azure Application Insights](https://docs.microsoft.com/en-us/azure/azure-monitor/app/app-insights-overview) service. It allows you to monitor any running APIs or streaming Spark jobs running on Databricks.

## Deployment
Add the following task to `deployment.yaml`

{:.table}
| field | description | values
| ----- | ----------- |
| `task` | `"create_application_insights"` |
| `kind` [optional]| Used to customize the UI | One of `web`, `ios`, `other`, `store`, `java`, `phone`
| `application_type` [optional] | Type of application being monitored |  One of `web`, `other`
| `create_databricks_secret` [optional] | Postfix for the image name, will be added before the tag | One of `true`, `false`

## Takeoff config
Credentials for an Azure Active Directory (AAD) user (username, password) must be available in your cloud vault. If `create_databricks_secret := true` credentials for Databricks (host, token) must also be available in your cloud vault.

Make sure `.takeoff/config.yaml` contains the following keys:

```yaml
azure:
    keyvault_keys:
        active_directory_user:
          username: "aad-username"
          password: "aad-password"
```

## Examples

Assume an application name `myapp` and version `1.2.0`. The `resouce_group_naming` parameter is `rg{env}`, where releases go to `env =: prd`

Minimum configuration example. This constructs an Application Insights service in the `rgprd` resource group with the name `myapp`.
```
steps:
  - task: create_application_insights
```

Full configuration example. This constructs an Application Insights service in the `rgprd` resource group with the name `myapp` with the UI tailored to Java applications, it also creates a Databricks secret under the scope `myapp` with name `instrumentation-key`.

```
steps:
  - task: create_application_insights
    kind: java
    application_type: other
    create_databricks_secret: true 
```
