#!/usr/bin/env bash

exit_out() {
  docker-compose -f docker-compose-dependencies.yml down
  exit 1
}

source ./tests/databricks.sh

