# Upload to Blob

Upload an artifact to an blob location in Azure Storage Account.

## 

Add the following snippet to `.vsts-ci.yaml` to build a python egg
```yaml
- task: DockerCompose@0
  displayName: Build egg
  inputs:
    dockerComposeCommand: |
      run --rm python python setup.py bdist_egg
```

## Deployment

Example configuration for `deployment.yaml`
```yaml
- task: uploadToBlob
  lang: python
```

#### CONFIGURATION VARIABLES
**lang** (_string_) (_required_): The language identifier `[python, sbt, maven]`

