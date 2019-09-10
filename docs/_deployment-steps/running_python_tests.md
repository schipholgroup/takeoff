---
layout: page
title: Running python unit tests
date: 2019-01-17
summary: Run python tests and upload tests and coverage results
permalink: deployment-step/python-tests
category: CI/CD
---

# Python unit tests

Azure Pipelines supports publishing of unit tests results and code coverage summaries.

## CI/CD

### Unit tests
Insert the following to `.azure-pipelines.yml` if you want to run python unit tests and publish the results

```yaml
- task: DockerCompose@0
  displayName: Run Python tests
  inputs:
    dockerComposeCommand: |
      run --rm python bash -c "python setup.py test"

- task: PublishTestResults@2
  displayName: Publish test results
  inputs:
    testResultsFiles: $(System.DefaultWorkingDirectory)/testresults.xml
```

The first task will grab the Takeoff image and run python tests. This assumes you have a `setup.py` in your project folder and a correctly configured `setup.cfg` file that makes sure the test results summary is saved as JaCoCo format. The second task will upload the `testresults.xml` to Azure Pipelines.

A minimal `setup.py` and `setup.cfg` might look like this:

`setup.py`:
```python
import sys
from setuptools import setup

test_dependencies = [
    'pytest==3.8.2',
]
setup_dependencies = []

if {'test'}.intersection(sys.argv):
    setup_dependencies = ['pytest-runner==4.2']
elif {'pep8', 'flake8'}.intersection(sys.argv):
    setup_dependencies = ['flake8==3.5.0']

setup(
    name="",
    packages=[],
    install_requires=[],
    setup_requires=setup_dependencies,
    extras_require={
        'test': test_dependencies,
        'lint': [' flake8==3.5.0']
    },
    tests_require=test_dependencies
)
```

`setup.cfg`
```ini
[aliases]
test=pytest
pep8=flake8

[tool:pytest]
addopts = --junitxml testresults.xml -v
```


### Coverage
Insert the following to `.azure-pipelines.yml` if you want to publish code coverage results **in addition** to running tests.

```yaml
- script: sudo chmod 777 . -R
  displayName: Change permissions to allow DevOps access... sigh...

- task: PublishCodeCoverageResults@1
  displayName: 'Publish coverage results'
  inputs:
    codeCoverageTool: 'cobertura'
    summaryFileLocation: $(System.DefaultWorkingDirectory)/coverage.xml
    reportDirectory: $(System.DefaultWorkingDirectory)/htmlcov
    failIfCoverageEmpty: false
```

This also requires you to add `'pytest-cov==2.5.1'` to the `test_dependencies` in `setup.py`. And an amendment to `setup.cfg`:
```ini
[tool:pytest]
addopts = --cov=eventhub_to_adls --cov-report html --cov-report xml --cov-report term-missing --junitxml testresults.xml -v
```
