#!/usr/bin/env bash


app_name='structured-streaming-poc'

create_secrets(){
  env_fn=$1
  source ${env_fn}

  python create_databricks_secrets.py \
  --scope ${app_name} \
  --token ${token} \
  --secrets \
  cosmos_endpoint=${cosmos_endpoint} \
  cosmos_masterkey=${cosmos_masterkey} \
  cosmos_database=${cosmos_database} \
  cosmos_collection=${cosmos_collection} \
  eventhub_connection_string=${eventhub_connection_string}
}

create_secrets 'dev.env'
create_secrets 'prd.env'
