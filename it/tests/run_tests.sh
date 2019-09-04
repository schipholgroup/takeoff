#!/usr/bin/env bash

exit_out() {
  exit 1
  cat ../logs
}

source ./tests/databricks.sh

