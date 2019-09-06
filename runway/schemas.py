import voluptuous as vol

AZURE_KEYVAULT_KEYS_SCHEMA = {
    vol.Optional("active_directory_user"): vol.Schema(
        {
            vol.Required("username", default="azure-username"): str,
            vol.Required("password", default="azure-password"): str,
        }
    ),
    vol.Optional("databricks"): vol.Schema(
        {
            vol.Required("host", default="azure-databricks-host"): str,
            vol.Required("token", default="azure-databricks-token"): str,
        }
    ),
    vol.Optional("container_registry"): vol.Schema(
        {
            vol.Required("username", default="registry-username"): str,
            vol.Required("password", default="registry-password"): str,
            vol.Required("registry", default="registry-server"): str,
        }
    ),
    vol.Optional("storage_account"): vol.Schema(
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
    vol.Optional("subscription_id", default="subscription-id"): str,
}

ENVIROMENT_KEYS_SCHEMA = {
    vol.Required("application_name", default="CI_PROJECT_NAME"): str,
    vol.Required("branch_name", default="CI_COMMIT_REF_SLUG"): str,
}

CI_KEYS_SCHEMA = {
    vol.Optional("ci_environment_keys_dev"): vol.Schema(
        {
            vol.Optional("service_principal"): vol.Schema(
                {
                    vol.Required("tenant", default="AZURE_TENANTID"): str,
                    vol.Required("client_id", default="AZURE_KEYVAULT_SP_USERNAME_DEV"): str,
                    vol.Required("secret", default="AZURE_KEYVAULT_SP_PASSWORD_DEV"): str,
                }
            )
        }
    ),
    vol.Optional("ci_environment_keys_tst"): vol.Schema(
        {
            vol.Optional("service_principal"): vol.Schema(
                {
                    vol.Required("tenant", default="AZURE_TENANTID"): str,
                    vol.Required("client_id", default="AZURE_KEYVAULT_SP_USERNAME_TST"): str,
                    vol.Required("secret", default="AZURE_KEYVAULT_SP_PASSWORD_TST"): str,
                }
            )
        }
    ),
    vol.Optional("ci_environment_keys_acp"): vol.Schema(
        {
            vol.Optional("service_principal"): vol.Schema(
                {
                    vol.Required("tenant", default="AZURE_TENANTID"): str,
                    vol.Required("client_id", default="AZURE_KEYVAULT_SP_USERNAME_ACP"): str,
                    vol.Required("secret", default="AZURE_KEYVAULT_SP_PASSWORD_ACP"): str,
                }
            )
        }
    ),
    vol.Optional("ci_environment_keys_prd"): vol.Schema(
        {
            vol.Optional("service_principal"): vol.Schema(
                {
                    vol.Required("tenant", default="AZURE_TENANTID"): str,
                    vol.Required("client_id", default="AZURE_KEYVAULT_SP_USERNAME_PRD"): str,
                    vol.Required("secret", default="AZURE_KEYVAULT_SP_PASSWORD_PRD"): str,
                }
            )
        }
    ),
}

AZURE_COMMON = {
    vol.Optional("shared_registry"): str,
    vol.Optional("artifacts_shared_blob_container_name", default="libraries"): str,
}

AZURE_SCHEMA = {
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
    vol.Optional("keyvault_keys"): AZURE_KEYVAULT_KEYS_SCHEMA,
    vol.Optional("common"): AZURE_COMMON,
}

COMMON_SCHEMA = {vol.Optional("databricks_library_path"): str}

RUNWAY_BASE_SCHEMA = vol.Schema(
    {
        vol.Required("environment_keys"): ENVIROMENT_KEYS_SCHEMA,
        vol.Optional("azure"): AZURE_SCHEMA,
        vol.Optional("common"): COMMON_SCHEMA,
        vol.Optional("plugins", description="A list of absolute paths containing runway plugins"): vol.All(
            [str], vol.Length(min=1)
        ),
        **CI_KEYS_SCHEMA,
    },
    extra=vol.ALLOW_EXTRA,
)
