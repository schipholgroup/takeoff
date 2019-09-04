#!/usr/bin/env bash

echo "========================================="
echo "== Setting up environment              =="
echo "========================================="
docker-compose -f docker-compose-dependencies.yml build
docker-compose -f docker-compose-dependencies.yml up -d

# wait for the mock server to start up
sleep 7
source ./setup_environment.sh


docker-compose -f docker-compose-takeoff.yml build
echo "========================================="
echo "== Taking off                          =="
echo "========================================="

docker-compose -f docker-compose-takeoff.yml up > logs

echo "========================================="
echo "== Running tests                       =="
echo "========================================="

source ./tests/run_tests.sh

echo "========================================="
echo "== Finished tests                      =="
echo "========================================="

docker-compose -f docker-compose-dependencies.yml down
