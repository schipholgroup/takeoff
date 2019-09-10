---
layout: page
title: Publish artifacts
date: 2019-03-15
summary: Publish python, sbt or maven artifacts
permalink: deployment-step/publish-artifact
category: Artifacts
---

# Publish Artifacts

This step allows you to publish artifacts for different languages to different targets. For example:
- You can publish python wheels to blob store, or to pypi.
- You can publish JVM jars to blob store (maven support coming soon)

<p class='note'>
  This step is only available in Takeoff >=10.0.0.
</p>
<p class='note warning'>
  Currently this is tailored to using the artifacts in Databricks, which does impose some assumptions. Read below what the impact is.
</p>
<p class='note warning'>
  For sbt/maven artifacts, Takeoff currently only supports publishing these to jar. Support for maven repositories will be implemented in future.
</p>
## Deployment
Add the following task to ``deployment.yaml``:

```yaml
- task: publishArtifact
  lang: python
  python_file_path: "main/main.py"
  target:
  - blob
  - pypi
```

{:.table}
| field | description | values
| ----- | ----------- |
| `lang` | The language identifier of your project | One of `python`, `maven`, `sbt`
| `target` | List of targets to push the artifact to. For Python this is one of: `blob`, `pypi`. For maven/sbt artifacts, this is one of: `blob`.
| `python_file_path` [OPTIONAL] | The path relative to the root of your project to the python script that serves as entrypoint for a databricks job |

For all languages, the assumption is that the artifact has already been built, for example by the `buildArtifact` step that Takeoff offers.

You can specify a main file (for Databricks jobs) by using the `python_file_path` key.
The path should be relative from the root of your project.

## Takeoff config
### Publish to Blob Store
Make sure `takeoff_config.yaml` contains the following `azure_keyvault_keys`:

  ```yaml
  azure_storage_account:
    account_name: "azure-shared-blob-username"
    account_key: "azure-shared-blob-password"
  ```
  
and these `takeoff_common` keys:
  ```yaml
  artifacts_shared_blob_container_name: libraries
  ```

### Publish to Pypi
Make sure `takeoff_config.yaml` contains the following `azure_keyvault_keys`:
  ```yaml
  azure_devops_artifact_store:
    repository_url: "artifact-store-upload-url"
    username: "artifact-store-username"
    password: "artifact-store-password"
  ```
