import voluptuous as vol

RUNWAY_COMMON_SCHEMA = vol.Schema(
    {
        vol.Optional("azure"): vol.Schema(
            {
                vol.Required(
                    "resource_group_naming",
                    description=(
                        "Naming convention for the resource."
                        "This should include the {env} parameter. For example"
                        "rg{env}"
                    ),
                ): str,
                vol.Required(
                    "keyvault_naming",
                    description=(
                        "Naming convention for the resource."
                        "This should include the {env} parameter. For example"
                        "keyvault{env}"
                    ),
                ): str,
                vol.Optional("location", default="west europe"): str,
            }
        ),
        vol.Optional("common"): vol.Schema(
            {
                vol.Optional("shared_registry"): str,
                vol.Optional("k8s_vnet_name"): str,
                vol.Optional("k8s_name"): str,
                vol.Optional("artifacts_shared_blob_container_name", default="libraries"): str,
                vol.Optional("databricks_library_path"): str,
            }
        ),
        vol.Optional("plugins", description="A list of absolute paths containing runway plugins"): vol.All(
            [str], vol.Length(min=1)
        ),
    },
    extra=vol.ALLOW_EXTRA,
)

ENVIROMENT_KEYS_SCHEMA = {
    vol.Required("common_environment_keys"): vol.Schema(
        {
            vol.Required("application_name", default="CI_PROJECT_NAME"): str,
            vol.Required("branch_name", default="CI_COMMIT_REF_SLUG"): str,
        }
    )
}

KEYVAULT_KEYS_SCHEMA = {
    vol.Required("azure_keyvault_keys"): vol.Schema(
        {
            vol.Required("azure_active_directory_user"): vol.Schema(
                {
                    vol.Required("username", default="azure-username"): str,
                    vol.Required("password", default="azure-password"): str,
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
            vol.Optional("artifact_store"): vol.Schema(
                {
                    vol.Required("repository_url", default="artifact-store-upload-url"): str,
                    vol.Required("username", default="artifact-store-username"): str,
                    vol.Required("password", default="artifact-store-password"): str,
                }
            ),
            vol.Optional("azure_subscription_id", default="subscription-id"): str,
        }
    )
}

CI_KEYS_SCHEMA = {
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
}

RUNWAY_BASE_SCHEMA = RUNWAY_COMMON_SCHEMA.extend(
    {**ENVIROMENT_KEYS_SCHEMA, **KEYVAULT_KEYS_SCHEMA, **CI_KEYS_SCHEMA}
)
