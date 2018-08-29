#!/usr/bin/env bash

echo "Checking if commit is release tag"

tag=`git describe --exact-match --tags HEAD`
if [[ ${tag} =~ ^([0-9]{1,2}\.[0-9]{1,2}\.[0-9]{1,2})$ ]]
then
    docker login --username ${REGISTRY_USERNAME} --password ${REGISTRY_PASSWORD} ${REGISTRY_LOGIN_SERVER}

    docker_tag=${REGISTRY_LOGIN_SERVER}/${BUILD_DEFINITIONNAME}:${tag}

    docker build -t ${docker_tag}-python -f ./Dockerfile_python .
    docker push ${docker_tag}-python

    docker build -t ${docker_tag}-pyspark -f ./Dockerfile_pyspark .
    docker push ${docker_tag}-pyspark
else
  echo "Commit is not a release, not deploying artifact"
fi