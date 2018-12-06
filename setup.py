import sys

from setuptools import setup

with open("README.md", "r") as f:
    long_description = f.read()

setup_dependencies = []
test_dependencies = ["pytest==3.8.2",
                     "pytest-cov==2.6.0",
                     "pyspark==2.3.1",
                     "databricks-cli==0.7.2",
                     "gitpython==2.1.10",
                     "py4j==0.10.7",
                     "azure==4.0.0",
                     "kubernetes==7.0.0",
                     "jinja2==2.10"]
if {'pytest', 'test'}.intersection(sys.argv):
    setup_dependencies = ['pytest-runner==4.2']
elif {'pep8', 'flake8'}.intersection(sys.argv):
    setup_dependencies = ['flake8==3.5.0']

setup(
    name="Runway",
    description="A package to bundle deployment scripts for Microsoft Azure",
    author="Schiphol Data Hub",
    long_description=long_description,
    author_email="SDH-Support@schiphol.nl",
    packages=["runway"],
    install_requires=[
        "azure==4.0.0",
        "gitpython==2.1.10",
        "databricks-cli==0.7.2",
        "pytest==3.8.2",
        "pytest-cov==2.6.0",
        "flake8==3.5.0",
        "PyYAML==3.13",
        "docker==3.5.0",
        "jinja2==2.10"
    ],
    extras_require={
        "test": test_dependencies,
        "lint": ["flake8==3.5.0"],
    },
    setup_requires=setup_dependencies,
    tests_require=test_dependencies,
    scripts=["scripts/runway",
             "scripts/run_linting",
             "scripts/run_tests"],
)
