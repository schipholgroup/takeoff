#!/usr/bin/env bash

echo "Checking if commit is release tag or master branch"

tag=`git describe --exact-match --tags HEAD`
branch=$(git rev-parse --abbrev-ref HEAD)

docker login -u ${REGISTRY_USERNAME} -p ${REGISTRY_PASSWORD} ${REGISTRY_LOGIN_SERVER}

function build_and_push(){

    version=$1
    postfix=$2
    docker_tag=${version}-${postfix}

    docker_image_name=${REGISTRY_LOGIN_SERVER}/${BUILD_DEFINITIONNAME}:${docker_tag}

    docker build -t ${docker_image_name} -f ./Dockerfile_${postfix} .
    docker push ${docker_image_name}

}

if [[ ${tag} =~ ^([0-9]{1,2}\.[0-9]{1,2}\.[0-9]{1,2})$ ]]
then
    build_and_push ${tag} "python"
    build_and_push ${tag} "pyspark"
elif [[ "$branch" = "master" ]]
then
    build_and_push "SNAPSHOT" "python"
    build_and_push "SNAPSHOT" "pyspark"
else
  echo "Commit is not a release nor master, not deploying artifact"
fi