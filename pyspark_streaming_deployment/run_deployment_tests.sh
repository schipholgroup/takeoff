#!/usr/bin/env bash

cd /root

echo 'run unit tests and coverage checks'
pip install -e .[deploy_test]
pytest tests_deployment
