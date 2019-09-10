---
layout: page
title: Build Artifact
date: 2019-03-15
summary: Build python, sbt or maven artifacts
permalink: deployment-step/build-artifact
category: Artifacts
---

# Build Artifact

This will build a python wheel (`.whl`) or sbt/maven jar. 
This will upload a python, sbt or maven build artifact to an Azure Storage Account blob store path. This makes it, for example, possible to rely on the arfifacts in services that don't support private artifact repositories. 

<p class='note'>
  This step is only available in Takeoff >=10.0.0. Previous versions require you to build the artifact in your CI pipeline, outside of Takeoff.
</p>
<p class='note warning'>
  Currently, only support for Python wheels is implemented. Support for building JVM artifacts is not ready yet, but will be added in future
</p>


## Deployment
Add the following task to ``deployment.yaml``:

```yaml
- task: buildArtifact
  lang: python 
```

{:.table}
| field | description | values
| ----- | ----------- |
| `lang` | The language identifier of your project | Currently, only `python` is  supported

Takeoff will use your `setup.py` to build the python wheel. Therefore, it assumes this `setup.py` is valid and contains all necessary dependencies. As with other steps, Takeoff manages the version number used, based on the git branch/tag for which the CI build is taking place. In this case, you should have a file `version.py` in the root of your project, that contains:
```python
__version__ = 'ANYTHING_HERE'
``` 
This file should then be referenced in your `setup.py` as follows:
```python
from version import __version__
setup(
  ...
  version=__version__
  ...
)
```
