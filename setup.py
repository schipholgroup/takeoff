import sys

from setuptools import setup, find_packages

with open("README.md", "r") as f:
    long_description = f.read()

"""
All setup dependencies are installed in the base docker image, removing the need to reinstall the same
dependencies every CI run.
Feel free to add missing ones to the dependencies here. As soon as these are stable move them to
https://github.com/Schiphol-Hub/runway-base-azure
"""
setup_dependencies = []
test_dependencies = [
    "databricks-cli==0.8.4",
    "jinja2==2.10",
    "gitpython==2.1.10",
    "mock==2.0.0",
    "kubernetes==7.0.0",
    "pytest==3.8.2",
    "pytest-cov==2.6.0",
    "py4j==0.10.7",
    "voluptuous==0.11.5",
    "twine",
    "black",
]

if {"pytest", "test"}.intersection(sys.argv):
    setup_dependencies = ["pytest-runner==4.2"]
elif {"lint", "flake8"}.intersection(sys.argv):
    setup_dependencies = ["flake8==3.5.0"]

setup(
    name="Runway",
    description="A package to bundle deployment scripts for Microsoft Azure",
    author="Schiphol Data Hub",
    long_description=long_description,
    author_email="SDH-Support@schiphol.nl",
    packages=find_packages(),
    install_requires=setup_dependencies,
    setup_requires=setup_dependencies,
    tests_require=test_dependencies,
    scripts=["scripts/runway", "scripts/get_version"],
    extras_require={
        "test": test_dependencies
    },
)
