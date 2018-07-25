from setuptools import setup

with open("README.md", 'r') as f:
    long_description = f.read()

setup(
    name='pyspark-streaming-deployment',
    version='0.0.1',
    description='A package to bundle deployment scripts',
    author='Schiphol Data Hub',
    long_description=long_description,
    author_email='SDH-Support@schiphol.nl',
    packages=['pyspark_streaming_deployment'],
    install_requires=[
        'gitpython==2.1.10',
        'databricks-cli==0.7.2',
        'azure-mgmt-datalake-store==0.3.0',
        'azure-mgmt-resource==1.2.2',
        'azure-datalake-store==0.0.24',
        'pytest==3.6.2',
        'pytest-cov==2.5.1',
        'flake8==3.5.0'
    ],
    extras_require={
        'test': {
            'pytest==3.6.2',
            'databricks-cli==0.7.2',
            'gitpython==2.1.10',
        },
        'lint': {
            'flake8==3.5.0'
        },
    },
    scripts=['scripts/deploy_to_adls',
             'scripts/deploy_to_databricks',
             'scripts/run_linting',
             'scripts/run_tests'],
)
