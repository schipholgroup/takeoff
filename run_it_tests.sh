#!/usr/bin/env bash

echo "========================================="
echo "== Setting up environment              =="
echo "========================================="
docker build -t takeoff:it -f ./Dockerfile .
docker-compose -f it/docker-compose-takeoff.yml build
docker-compose -f it/docker-compose-dependencies.yml build


# wait for the mock server to start up
docker-compose -f it/docker-compose-dependencies.yml up -d

echo "========================================="
echo "== Taking off                          =="
echo "========================================="

docker-compose -f it/docker-compose-takeoff.yml up
