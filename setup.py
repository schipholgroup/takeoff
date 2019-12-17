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
    "azure==4.0.0",
    "databricks-cli==0.9.0",
    "docker==4.0.2",
    "flake8==3.7.2",
    "gitpython==3.0.2",
    "jinja2==2.10.1",
    "kubernetes==10.0.1",
    "py4j==0.10.7",
    "pyyaml==5.1.2",
    "requests>=2.20.0",
    "twine==1.14.0",
    "voluptuous==0.11.7",
    "google-cloud-kms==1.2.1"
]

test_dependencies = [
    "mock==2.0.0",
    "pytest==3.8.2",
    "pytest-cov==2.6.0",
    "black==19.3b0"
]

if {"pytest", "test"}.intersection(sys.argv):
    setup_dependencies = ["pytest-runner==4.2"]
elif {"lint", "flake8"}.intersection(sys.argv):
    setup_dependencies = ["flake8==3.5.0"]

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
    extras_require={"test": test_dependencies},
)
