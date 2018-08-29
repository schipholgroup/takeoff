from setuptools import setup

with open("README.md", "r") as f:
    long_description = f.read()

setup(
    name="sdh-deployment",
    version="0.0.1",
    description="A package to bundle deployment scripts",
    author="Schiphol Data Hub",
    long_description=long_description,
    author_email="SDH-Support@schiphol.nl",
    packages=["sdh_deployment"],
    install_requires=[
        'gitpython==2.1.10',
        'databricks-cli==0.7.2',
        'pytest==3.6.2',
        'pytest-cov==2.5.1',
        'flake8==3.5.0',
        'PyYAML==3.13'
    ],
    extras_require={
        'test': {
            'pytest==3.6.2',
            'databricks-cli==0.7.2',
            'gitpython==2.1.10',
            'py4j==0.10.7',
            'azure==4.0.0'
        },
        'lint': {
            'flake8==3.5.0'
        },
        "lint": {"flake8==3.5.0"},
    },
    scripts=["scripts/run_deployment", "scripts/run_linting", "scripts/run_tests"],
)
