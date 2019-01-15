# Examples

Contains examples and documentation for all steps Runway supports.

To get started. Have a `.vsts-ci.yaml` in the root of your project with the following content

```yaml
pool:
  vmImage: ubuntu-16.04

# This should always be the first task
- script: docker login --username ${REGISTRY_USERNAME} --password ${REGISTRY_PASSWORD} ${REGISTRY_LOGIN_SERVER}
  displayName: Login to registry

# This should always be the last task
- task: DockerCompose@0
  displayName: Deploy to Azure and Databricks
  inputs:
    dockerComposeCommand: |
      run --rm dockerception runway
  env:
    AZURE_TENANTID: ${azure_tenantid}
    AZURE_KEYVAULT_SP_USERNAME_DEV: $(azure_keyvault_sp_username_dev)
    AZURE_KEYVAULT_SP_PASSWORD_DEV: $(azure_keyvault_sp_password_dev)
    AZURE_KEYVAULT_SP_USERNAME_ACP: $(azure_keyvault_sp_username_acp)
    AZURE_KEYVAULT_SP_PASSWORD_ACP: $(azure_keyvault_sp_password_acp)
    AZURE_KEYVAULT_SP_USERNAME_PRD: $(azure_keyvault_sp_username_prd)
    AZURE_KEYVAULT_SP_PASSWORD_PRD: $(azure_keyvault_sp_password_prd)
```

- [Upload artifacts to shared azure blob store](./upload_to_blob/README.md)
