#!/usr/bin/env bash
sleep 7
source ./setup_environment.sh

echo "========================================="
echo "== Running TakeOff                     =="
echo "========================================="

rm -rf logs
runway

echo "========================================="
echo "== Running tests                       =="
echo "========================================="

source ./tests/run_tests.sh

echo "========================================="
echo "== Finished tests                      =="
echo "========================================="
