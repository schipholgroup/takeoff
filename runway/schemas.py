import voluptuous as vol

BASE_SCHEMA = vol.Schema(
    {
        vol.Required("runway_azure"): vol.Schema(
            {
                vol.Required("resource_group"): str,
                vol.Required("vault_name"): str,
                vol.Optional("location", default="west europe"): str,
            }
        ),
        vol.Required("azure_keyvault_keys"): vol.Schema(
            {
                vol.Required("azure_active_directory_user"): vol.Schema(
                    {
                        vol.Required("username", default="azure-username"),
                        vol.Required("password", default="azure_password"),
                    }
                ),
                vol.Optional("azure_databricks"): vol.Schema(
                    {
                        vol.Required("host", default="azure-databricks-host"): str,
                        vol.Required("token", default="azure-databricks-token"): str,
                    }
                ),
                vol.Optional("azure_container_registry"): vol.Schema(
                    {
                        vol.Required("username", default="registry-username"): str,
                        vol.Required("password", default="registry-password"): str,
                        vol.Required("registry", default="registry-server"): str,
                    }
                ),
                vol.Optional("azure_storage_account"): vol.Schema(
                    {
                        vol.Required("account_name", default="azure-shared-blob-username"): str,
                        vol.Required("account_key", default="azure-shared-blob-password"): str,
                    }
                ),
                vol.Optional("azure_devops_artifact_store"): vol.Schema(
                    {
                        vol.Required("repository_url", default="artifact-store-upload-url"): str,
                        vol.Required("username", default="artifact-store-username"): str,
                        vol.Required("password", default="artifact-store-password"): str,
                    }
                ),
                vol.Optional("azure_subscription_id", default="subscription-id"): str,
            }
        ),
        vol.Required("devops_environment_keys_dev"): vol.Schema(
            {
                vol.Required("azure_service_principal"): vol.Schema(
                    {
                        vol.Required("tenant", default="AZURE_TENANTID"): str,
                        vol.Required("client_id", default="AZURE_KEYVAULT_SP_USERNAME_DEV"): str,
                        vol.Required("secret", default="AZURE_KEYVAULT_SP_PASSWORD_DEV"): str,
                    }
                )
            }
        ),
        vol.Required("devops_environment_keys_acp"): vol.Schema(
            {
                vol.Required("azure_service_principal"): vol.Schema(
                    {
                        vol.Required("tenant", default="AZURE_TENANTID"): str,
                        vol.Required("client_id", default="AZURE_KEYVAULT_SP_USERNAME_ACP"): str,
                        vol.Required("secret", default="AZURE_KEYVAULT_SP_PASSWORD_ACP"): str,
                    }
                )
            }
        ),
        vol.Required("devops_environment_keys_prd"): vol.Schema(
            {
                vol.Required("azure_service_principal"): vol.Schema(
                    {
                        vol.Required("tenant", default="AZURE_TENANTID"): str,
                        vol.Required("client_id", default="AZURE_KEYVAULT_SP_USERNAME_PRD"): str,
                        vol.Required("secret", default="AZURE_KEYVAULT_SP_PASSWORD_PRD"): str,
                    }
                )
            }
        ),
        vol.Optional("runway_common"): vol.Schema(
            {
                vol.Optional("shared_registry", default="sdhcontainerregistryshared.azurecr.io"): str,
                vol.Optional("k8s_vnet_name", default="sdh-kubernetes"): str,
                vol.Optional("k8s_name", default="sdhkubernetes{dtap}"): str,
                vol.Optional("artifacts_shared_blob_container_name", default="libraries"): str,
                vol.Optional("databricks_library_path", default="dbfs:/mnt/libraries"): str,
                vol.Optional("eventhub_namespace", default="sdheventhub{dtap}"): str,
            }
        ),
    },
    extra=vol.ALLOW_EXTRA,
)
