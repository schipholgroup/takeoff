#!/usr/bin/env bash

cd /root

echo 'checking if code compiles and install package'
python setup.py develop

echo 'run unit tests and coverage checks'
pip install -e .[test]
pytest --cov-config .coveragerc --cov=./structured_streaming_poc tests
