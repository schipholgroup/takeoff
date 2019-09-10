---
layout: page
title: Create Databricks secrets
date: 2019-01-16
summary: Use Azure KeyVault secrets to create Databricks secrets
permalink: deployment-step/databricks-secrets
category: Databricks
---

# Create Databricks secrets

Takeoff can create []ataBricks secrets](https://docs.databricks.com/user-guide/secrets/index.html) automatically. In order to do so you must have create secrets in the Azure KeyVault prefixed with your application name (i.e. github repo).

For example if your repository is called `flight-predictions` that needs an API key to an external API, the Azure KeyVault secret name must be `flight-predictions-api-key`. 

During deployment Takeoff creates a Databricks secrets scope matching your repository name (e.g. `flight-predictions`) and creates all secrets that matches the previously mentioned pattern (e.g. `api-key`) in that scope.

## Deployment
Add the following task to ``deployment.yaml``:

```yaml
- task: createDatabricksSecrets
```

## Takeoff config
Make sure `takeoff_config.yaml` contains the following `azure_keyvault_keys`:

  ```yaml
  azure_databricks:
    host: "azure-databricks-host"
    token: "azure-databricks-token"
  ```
 
and these `takeoff_common` keys:
  ```yaml
  databricks_library_path: "dbfs:/mnt/libraries"
  ```
