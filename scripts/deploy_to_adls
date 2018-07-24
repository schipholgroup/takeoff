#!/usr/bin/env bash

cd /root

echo 'checking if code compiles and install package'
python setup.py develop

echo 'deploy to adls'
pip install -e .[deploy]
python /root/deployment/deploy_to_adls.py
