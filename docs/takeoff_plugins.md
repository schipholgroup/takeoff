---
layout: page
title: Takeoff plugins
rank: 3
permalink: takeoff-plugins
---

# Takeoff plugins

Now, we know that not everyone has the same environments, or might want a different versioning tactic: maybe 

- _release_ versions should go to __acceptance__;
- and _SNAPSHOT_ should go to __testing__;
- feature branches should not be deployed
     
This is where Schiphol Takeoff plugins come in to play. Using Python, we allow you to write your own custom logic regarding what should go where and when. Regarding the where part: we also allow you to introduce your own naming conventions and logic by the form of a Python plugin. Writing your own plugin is quite easy, but to understand what plugins can mean for you a basic understanding of _how_ Schiphol Takeoff works is necessary. 

## Customization using plugins

Create a new folder in your repository prefixed with `takeoff_`, for example `takeoff_plugins` and in it an `__init__.py` file. This file will contain any custom function for Schiphol Takeoff which will scan and load these on runtime. To create you own logic for deployment simply override the default function. For the example stated above the new function looks like:

```python
import logging

from takeoff.application_version import ApplicationVersion
from takeoff.credentials.branch_name import BranchName
from takeoff.util import get_tag

logger = logging.getLogger(__name__)


def deploy_env_logic(config: dict) -> ApplicationVersion:
    branch = BranchName().get(config)
    tag = get_tag()

    if tag:
        return ApplicationVersion("acp", str(tag), branch)
    elif branch == "master":
        return ApplicationVersion("tst", "SNAPSHOT", branch)
    else:
        logger.info("Not deploying feature branches")
        exit(0)
```

Takeoff will pickup this function and use that one instead of the default one specified in [Deployment environments](deployment-environments-).

## Naming conventions

Other functions you can overwrite are the ones that use naming conventions. These are their function definitions

### For Azure
- Resource groups
    ```python
    def get_resource_group_name(config: dict, env: ApplicationVersion) -> str
    ```
- Keyvault 
    ```python
    def get_keyvault_name(config: dict, env: ApplicationVersion) -> str
    ```
- Cosmos
    ```python
    def get_cosmos_name(config: dict, env: ApplicationVersion) -> str
    ```
- EvenHub namespace 
    ```python
    def get_eventhub_name(config: dict, env: ApplicationVersion) -> sts
    ```
- EventHub entity (equivalent of a kafka topic)
    ```python
    def get_eventhub_entity_name(eventhub_entity_naming: str, env: ApplicationVersion) -> str
    ```
- Kubernetes (AKS)
    ```python
    def get_kubernetes_name(config: dict, env: ApplicationVersion) -> str
    ```
  
In all of the examples:
- `config: dict` is the full configuration of the __current__ [deployment step](deployment-steps). Including the full contents of `.takeoff/config.yml`. It does not contain any information about other steps. 
- `env: ApplicationVersion` is an instance of the class mentioned in [deployment environments](deployment-environments)
