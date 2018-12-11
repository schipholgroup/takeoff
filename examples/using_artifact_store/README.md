# Using the artifact store

## Notes
There are some things to note:
1. This functionality is currently only available for publishing/consuming python packages.
2. Your package that needs consuming/publishing should be installed using `pip`.

## Use
Use of the artifact store with Runway comes in 2 forms:
1. Publishing a package to the artifact store
2. Consuming (i.e. using) a package from the artifact store.

Files are available in this example for both sides.

### Publishing
When publishing a package to the artifact store, you will need 3 environment variables to be available:
```yaml
  ARTIFACT_STORE_USERNAME: $(ARTIFACT_STORE_USERNAME) 
  ARTIFACT_STORE_PASSWORD: $(ARTIFACT_STORE_PASSWORD)
  ARTIFACT_STORE_UPLOAD_URL: $(ARTIFACT_STORE_UPLOAD_URL) 
```
Moreover, you will need to add the following task to your `deployment.yml`:
```yaml
- task: publishArtifact
```
All other configuration of this published package will be taken from your `setup.py`

### Consuming
When consuming a package from the artifact store, you will 1 environment variable to be available:
```yaml
  PIP_EXTRA_INDEX_URL: $(ARTIFACT_STORE_INDEX_URL)
```
Please note that this environment variable will be needed everywhere you need to install any dependencies for your tasks
(e.g. running tests, linting etc.)