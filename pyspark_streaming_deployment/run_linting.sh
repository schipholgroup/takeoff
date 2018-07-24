#!/usr/bin/env bash

cd /root

echo 'checking if code compiles and install package'
python setup.py develop

echo 'checking if style is correct'
pip install -e .[lint]
flake8 structured_streaming_poc/
