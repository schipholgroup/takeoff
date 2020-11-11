---
layout: page
title: Build Artifact
date: 2019-03-15
summary: Build python, sbt or maven artifacts
permalink: deployment-step/build-artifact
category: Artifacts
---

# Build Artifact

This will build a Python wheel (`.whl`) or SBT jar (`.jar`). 

## Deployment
Add the following task to ``deployment.yaml``:

```yaml
- task: build_artifact
  build_tool: python 
```

{:.table}
| field | description | values
| ----- | ----------- |
| `task` | `"build_artifact"`
| `build_tool` | The language identifier of your project | One of `python`, `sbt`
| `python_setup_path`[optional] | Relative path to setup.py file, including the filename | By default `setup.py`

### Building Python wheels
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

### Building SBT jars
Takeoff will use your `build.sbt` to build an assembly jar. This means that the [assembly plugin](https://github.com/sbt/sbt-assembly) must have been configured for your project.

## Examples

Example for building an SBT assembly jar. 
```
steps:
- task: build_artifact
  build_tool: sbt
```
