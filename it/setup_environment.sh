#!/usr/bin/env bash

echo "========================================="
echo "== Setting up mock webserver           =="
echo "========================================="

source ./setup/00-add-nginx-proxy.sh
source ./setup/01-setup-keyvault.sh
source ./setup/02-databricks.sh

