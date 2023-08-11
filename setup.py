import sys

from setuptools import setup, find_packages

with open("README.md", "r") as f:
    long_description = f.read()

"""
All setup dependencies are installed in the base docker image, removing the need to reinstall the same
dependencies every CI run.
Feel free to add missing ones to the dependencies here. As soon as these are stable move them to
https://github.com/schipholgroup/takeoff-base
"""
setup_dependencies = [
    "azure-mgmt-relay==1.0.0",
    "azure-mgmt-eventhub==2.2.0",
    "azure-mgmt-applicationinsights==1.0.0",
    "azure-mgmt-cosmosdb==0.9.0",
    "azure-keyvault==1.1.0",
    "azure-storage-blob==2.1.0",
    "azure-mgmt-containerservice==5.3.0",
    "msrestazure==0.6.4",
    "databricks-cli==0.9.0",
    "docker==4.0.2",
    "gitpython==3.1.32",
    "jinja2==2.11.3",
    "kubernetes==10.0.1",
    "py4j==0.10.7",
    "pyyaml==5.4",
    "requests>=2.20.0",
    "twine==1.14.0",
    "voluptuous==0.11.7"
]

test_dependencies = [
    "pytest==5.4.1",
    "pytest-cov==2.8.1"
]

lint_dependencies = [
    "flake8==3.9.0",
    "black==20.8b1"
]

if {"pytest", "test"}.intersection(sys.argv):
    setup_dependencies = ["pytest-runner==4.2"]
elif {"lint", "flake8"}.intersection(sys.argv):
    setup_dependencies = lint_dependencies

setup(
    name="Takeoff",
    description="A package to bundle deployment scripts for deploying application in the cloud",
    author="Schiphol Group",
    long_description=long_description,
    author_email="SDH-Support@schiphol.nl",
    packages=find_packages(exclude=("tests*",)),
    include_package_data=True,
    install_requires=setup_dependencies,
    setup_requires=setup_dependencies,
    tests_require=test_dependencies,
    scripts=["scripts/takeoff", "scripts/get_version"],
    extras_require={"test": test_dependencies, "lint": lint_dependencies},
)
