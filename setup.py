from setuptools import setup

with open("README.md", 'r') as f:
    long_description = f.read()

setup(
    name='structured_streaming_poc',
    version='0.0.1',
    description='A POC to test deploying a structured streaming application',
    author='Schiphol Data Hub',
    long_description=long_description,
    author_email='SDH-Support@schiphol.nl',
    packages=['structured_streaming_poc'],
    install_requires=[],
    extras_require={
        'test': {
            'pytest==3.6.2',
            'pytest-cov==2.5.1',
            'py4j==0.10.7'
        },
        'lint': {
            'flake8==3.5.0'
        },
        'deploy_test': {
            'pytest==3.6.2',
            'databricks-cli==0.7.2',
            'gitpython==2.1.10',
            'py4j==0.10.7'
        },
        'deploy': {
            'gitpython==2.1.10',
            'databricks-cli==0.7.2',
            'azure-mgmt-datalake-store==0.3.0',
            'azure-mgmt-resource==1.2.2',
            'azure-datalake-store==0.0.24'
        },
    }
)
