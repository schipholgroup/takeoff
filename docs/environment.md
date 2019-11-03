---
layout: page
title: Environments
date: 2019-09-14
updated: 2019-09-14
rank: 2
permalink: deployment-environments
---

# How Takeoff works with DTAP environments

Schiphol Takeoff deploys your application to any environment on your cloud. Your CI provider pulls the Schiphol Takeoff image from [dockerhub](https://hub.docker.com/r/schipholhub/takeoff). Takeoff determines the state of your git repository (i.e. what branch your commit is on) and will decide where the deployment should go. 

![ci-envs](/assets/images/ci-envs.png)

For example, this is how one can use Schiphol Takeoff:

- feature branches will be deployed to your __development__ environment; 
- master branches will be deployed to __acceptance__;
- git tags are considered releases and are deployed to __production__. 

It will also make sure versions are preserved during deployment to these environments &mdash; given the previous example 

- __development__ will receive a version equal to the name of your feature branch; 
- __acceptance__ will receive the version _SNAPSHOT_; 
- __production__ will take the _git tag_ as version. 

Concretely this means that many feature branches may be running simultaneously, but only one _SNAPSHOT_ or _git tag_ will be running.

For this all to work, Schiphol Takeoff makes some assumptions about naming conventions. For example, in the case of Microsoft Azure, each of these environments basically mean a separate resource group. These resource groups are identical in the fact that they contain the same services, but otherwise might be different in terms of scaling and naming of services. Based on naming conventions Schiphol Takeoff determines during CI which service in which resource group it should deploy to.

_note_: The above holds for the defaults of Schiphol Takeoff, all of the above logic can be overridden by [plugins](takeoff-plugins).

## `ApplicationVersion`
One of the most important classes in Schiphol Takeoff is `ApplicationVersion`. It has the following signature:

```python
@dataclass(frozen=True)
class ApplicationVersion(object):
    environment: str
    version: str
    branch: str
```

- `environment` is the environment Schiphol Takeoff should deploy to. This value is used to resolve any naming rules set in [`.takeoff/config.yml`](takeoff-config). Examples of this value could be `dev`, `PRD`, `acceptance`;
- `version` is the version of the application and also the version each artifact or service should get;
- `branch` is the current git branch.

Here is an example of how Takeoff determines to which environment a deployment should go:

```python
from takeoff.application_version import ApplicationVersion
from takeoff.credentials.branch_name import BranchName
from takeoff.util import get_tag, get_short_hash

def deploy_env_logic(config: dict) -> ApplicationVersion:
    branch = BranchName().get(config)
    tag = get_tag()
    git_hash = get_short_hash()

    if tag:
        return ApplicationVersion("PRD", str(tag), branch)
    elif branch == "master":
        return ApplicationVersion("ACP", "SNAPSHOT", branch)
    else:
        return ApplicationVersion("DEV", git_hash, branch)
```

Without knowing too much about specifics of the code one can see that git tags go to __production__, master branches go to __acceptance__ and other features branches go to __development__.

