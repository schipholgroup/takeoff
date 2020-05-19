---
layout: page
title: Takeoff config
rank: 3
permalink: takeoff-config
---

# Overview
The `.takeoff/config.yaml` is the place put any variables that should not be hardcoded in python. Then you can use these variables in your component to authenticate against Cloud services.

<p class='note warning'>
  By default, Takeoff assumes the configuration is available in the `.takeoff` directory. You can configure this with the optional CLI parameter: `--takeoff_dir my_path`. For example: `takeoff --takeoff_dir my_path` will read both 
  of Takeoff's yaml files from the `my_path` directory
</p>

The basic setup contains:

```yaml
environment_keys:
common:
plugins:
ci_environment_keys_dev:
ci_environment_keys_tst:
ci_environment_keys_acp:
ci_environment_keys_prd:
azure:
```

{:.table}
| field | description | more info
| ----- | ----------- | ---------
| `environment_keys` | Mandatory Takeoff variables | [Jump to values](takeoff-config#environment_keys)
| `common` __[optional]__ | Evironment agnostic variables | [Jump to values](takeoff-config#common)
| `plugins` __[optional]__ | List of paths to Takeoff plugins | [Read more](takeoff-plugins)
| `ci_environment_keys_dev` __[optional]__ | Environment variables for your development environment | [Jump to values](takeoff-config#ci_environment_keys)
| `ci_environment_keys_tst` __[optional]__ | Environment variables for your test environment | [Jump to values](takeoff-config#ci_environment_keys)
| `ci_environment_keys_acp` __[optional]__ | Environment variables for your acceptance environment | [Jump to values](takeoff-config#ci_environment_keys)
| `ci_environment_keys_prd` __[optional]__ | Environment variables for your production environment | [Jump to values](takeoff-config#ci_environment_keys)
| `azure` __[optional]__ | Microsoft Azure specific values | [Jump to values](takeoff-config#azure)




## environment_keys

The mandatory fields are
```yaml
environment_keys:
  application_name: "CI_PROJECT_NAME"
  branch_name: "CI_BRANCH_NAME"
```

{:.table}
| field | description |
| ----- | ----------- |
| `application_name` | A CI environment variable containing your application name, advised is to use your repository name. This variable should be available on all CI providers
| `branch_name` |  A CI environment variable containing the current branch name


## common

The optional fields are
```yaml
common:
  databricks_fs_libraries_mount_path: "dbfs:/mnt/libraries"
```

{:.table}
| field | description |
| ----- | ----------- |
| `databricks_fs_libraries_mount_path` | Path on [`dbfs`](https://docs.databricks.com/user-guide/databricks-file-system.html) where libraries (such as wheels and jars) are stored. Usually this is a mounted cloud storage path.

## ci_environment_keys

These keys are meant to authenticate to cloud vaults using service accounts. Currently supported values are Azure service principals.

The optional fields are
```yaml
ci_environment_keys_*:
  service_principal: 
    tenant: "AZURE_TENANT_ID"
    client_id: "AZURE_SP_USERNAME"
    secret: "AZURE_SP_PASSWORD"
```

{:.table}
| field | description 
| ----- | ----------- 
| `service_principal` | Values used to authenticate against an [Azure Service Principal](https://docs.microsoft.com/en-us/azure/active-directory/develop/app-objects-and-service-principals)
| `service_principal.tenant` | CI environment variable containing the Azure Tenant ID (usually a UUID)
| `service_principal.client_id` | CI environment variable containing the client id (usually a UUID)
| `service_principal.secret` | CI environment variable containing the secret 

#### Example 

Assume you have two enviroments, a `dev` and `prd`. The following snippet could be part of your `.takeoff/config.yml`

```yaml
ci_environment_keys_dev:
  service_principal: 
    tenant: "AZURE_TENANT_ID"
    client_id: "AZURE_SP_USERNAME_DEV"
    secret: "AZURE_SP_PASSWORD_DEV"
ci_environment_keys_prd:
  service_principal: 
    tenant: "AZURE_TENANT_ID"
    client_id: "AZURE_SP_USERNAME_PRD"
    secret: "AZURE_SP_PASSWORD_PRD"
```

## azure

This section contains all specific values for deploying to Azure services.

```yaml
azure:
  resource_group_naming: "rg{env}"
  keyvault_naming: "https://keyvault{env}.vault.azure.net"
  location: "west europe"
  keyvault_keys: 
  common: 
```

{:.table}
| field | description | more info
| ----- | ----------- | ---------
| `resource_group_naming` | Naming convention for Azure resource groups, must contain `{env}` | See [deployment environments](deployment-environments) for more info
| `keyvault_naming` | Naming convention for Azure Keyvaults, must contain `{env}` | See [deployment environments](deployment-environments) for more info
| `location` __[optional]__ | [Location](https://azure.microsoft.com/en-us/global-infrastructure/locations/) of your Azure Data Center
| `keyvault_keys` __[optional]__ | Names of keys in the Azure KeyVault containing values for other Azure services | [Jump to values](takeoff-config#azure-keyvault_keys)
| `common` __[optional]__ | Names of common Azure names | [Jump to values](takeoff-config#azure-common)


### azure-keyvault_keys

Every key contains a mapping of credential parameters to KeyVault keys. Possible values are:

```yaml
azure:
  keyvault_keys: 
    active_directory_user:
      username: "azure-username"
      password: "azure-password"
    databricks:
      host: "azure-databricks-host"
      token: "azure-databricks-token"
    container_registry:
      username: "registry-username"
      password: "registry-password"
      registry: "registry-server"
    storage_account:
      account_name: "azure-shared-blob-username"
      account_key: "azure-shared-blob-password"
    artifact_store:
      repository_url: "artifact-store-upload-url"
      username: "artifact-store-username"
      password: "artifact-store-password"
    subscription_id: "subscription-id"
```

Concretely this means that, for example `azure-username` and `azure-password` must be valid secret keys in your Azure KeyVault.

{:.table}
| field | description | more info
| ----- | ----------- | ---------
| `active_directory_user` __[optional]__ | A registered AAD user, used for application to application authentication
| `active_directory_user.username` | Username of the AAD user
| `active_directory_user.password` | Password of the AAD user
| `databricks` __[optional]__ | A registered AAD user, used for application to application authentication
| `databricks.host` | Host of the Databricks (for "West Europe" this is `https://westeurope.azuredatabricks.net/`)
| `databricks.token` | [Token](https://docs.databricks.com/api/latest/authentication.html) for Databricks authentication
| `container_registry` __[optional]__ | An [Azure Container Registry (ACR)](https://azure.microsoft.com/en-us/services/container-registry/)
| `container_registry.username` | Username of the ACR
| `container_registry.password` | Password of the ACR
| `container_registry.registry` | The url for the ACR (looks like: `*.azurecr.io/`)

### azure-common
```yaml
azure:
  common:
    artifacts_shared_storage_account_container_name: "libraries"
```

{:.table}
| field | description 
| ----- | ----------- 
| `artifacts_shared_storage_account_container_name` __[optional]__ | Container name for an [Azure Storage Account V1](https://docs.microsoft.com/en-us/azure/storage/common/storage-account-overview). Useful for storing artifacts such as wheels and jars.

