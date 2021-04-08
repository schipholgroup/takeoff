---
layout: page
title: Publish artifacts
date: 2019-03-15
updated: 2019-09-10
summary: Publish Python or Scala artifacts
permalink: deployment-step/publish-artifact
category: Artifacts
---

# Publish Artifacts

This step allows you to publish artifacts for different languages to different targets:
- You can publish Python files and wheels to cloud storage, or to PyPi.
- You can publish Scala jars to cloud storage, or to Ivy

<p class='note warning'>
  There's an implicit dependency on [building artifacts](build-artifact) when publishing to PyPi and cloud storage
</p>

<p class='note warning'>
  Regarding Scala, only SBT is supported as build tool
</p>

<p class='note warning'>
  When uploading multiple Python files, make sure to set the `"use_original_python_filename"` flag to differentiate between the different Python files.
  By default a fixed name for the Python file is used, which in this case will cause files to be overwritten.
</p>

## Deployment
Add the following task to ``deployment.yaml``

{:.table}
| field | description | values
| ----- | ----------- |
| `task` | `"publish_artifact"`
| `language` | The language identifier of your project | One of `python`, `scala`
| `target` | List of targets to push the artifact to. For Python these can be: `cloud_storage`, `pypi`. For Scala artifacts these can be: `cloud_storage`, `ivy`
| `python_file_path` [optional] | The path relative to the root of your project to the python script that serves as entrypoint for a databricks job 
| `use_original_python_filename` [optional] | If you upload multiple unique Python files use this flag to include the original filename in the result. Only impacts Python files.

The behaviour of the `use_original_python_filename` flag:

{:.table}
| main_name | True | False
| ----------- | ----------- | -----------
| `script.py` | `project-main-1.0.0-script.py` | `project-main-1.0.0.py`
| `script.py` | `project-main-SNAPSHOT-script.py` | `project-main-SNAPSHOT.py`
| `script.py` | `project-main-my_branch-script.py` | `project-main-my_branch.py`

For all languages, the assumption is that the artifact has already been built, for example by the `build_artifact` step that Takeoff offers.

You can specify a main file (for Databricks jobs) by using the `python_file_path` key.
The path should be relative from the root of your project.

## Takeoff config

### Publish to Azure Storage Account V1
Credentials for the Azure Storage Account V1 must be available in your cloud vault when pushing to Azure `cloud_storage`.
Make sure `.takeoff/config.yaml` contains the following keys:

```yaml
azure:
  keyvault_keys:
    storage_account:
      account_name: "azure-shared-blob-username"
      account_key: "azure-shared-blob-password"
  common:
      artifacts_shared_storage_account_container_name: libraries
```

<p class='note warning'>
  For Scala, Takeoff assumes an assembly jar has been built.
</p>


### Publish to PyPi
Credentials for PyPi (username, password) must be available in your cloud vault when pushing to any PyPi artifact store. 
Make sure `takeoff_config.yaml` contains the following `azure_keyvault_keys`:
```yaml
azure:
  keyvault_keys:
    artifact_store:
      repository_url: "artifact-store-upload-url"
      username: "artifact-store-username"
      password: "artifact-store-password"
```

### Publish to Ivy
Credentials for your Ivy repository must be available as enviroment variables and your SBT project must be configured to read these and handle the `sbt publish` command.

## Examples

Minimum configuration example for Python. This pushes a Python wheel to PyPi.
```
steps:
- task: publish_artifact
  language: python
  target:
    - pypi
```

Extended configuration example for Scala. This pushes a jar to both cloud storage and your `ivy` repository
```yaml
- task: publish_artifact
  language: scala
  target:
    - cloud_storage
    - ivy
```
