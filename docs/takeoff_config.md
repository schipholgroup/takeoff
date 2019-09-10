---
layout: page
title: Takeoff config
rank: 3
permalink: takeoff-config
---

# Overview
The `takeoff_config.yaml` is the place put any variables that should not be hardcoded in python. When [developing a new component for Takeoff](deveploment_guide) you can use these variables in your component authenticate against Azure services using the Azure KeyVault as central place to store these credentials.

The basic setup contains:

```yaml
takeoff_azure:
azure_keyvault_keys:
devops_environment_keys_dev:
devops_environment_keys_acp:
devops_environment_keys_prd:
```

{:.table}
| field | description | values
| ----- | ----------- |
| `takeoff_azure` | A dictionary containing mandatory Takeoff variables | [Jump to values](takeoff_config#takeoff_azure)

## takeoff_azure

The mandary fields are
```yaml
  resource_group: "sdh{dtap}"
  location: "west europe"
  vault_name: "https://sdhkeyvault{dtap}.vault.azure.net/"
```

{:.table}
| field | description |
| ----- | ----------- |
| `resource_group` | A python [format string](https://docs.python.org/3/library/stdtypes.html#str.format) capturing the naming conventions of the Azure resource groups across `DAP`
| `location` |  [Azure location](https://azure.microsoft.com/en-us/global-infrastructure/locations/) of the Data center 
| `vault_name` | A python [format string](https://docs.python.org/3/library/stdtypes.html#str.format) capturing the naming conventions of the Azure KeyVault across `DAP`

