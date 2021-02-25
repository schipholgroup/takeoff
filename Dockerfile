FROM python:3.8

RUN apt-get update && apt-get install -y --no-install-recommends curl

## Java
RUN apt-get install -y openjdk-11-jdk
ENV JAVA_HOME=/usr/lib/openjdk-11
ENV PATH=$PATH:$JAVA_HOME/bin

## SBT
RUN echo "deb https://dl.bintray.com/sbt/debian /" | tee -a /etc/apt/sources.list.d/sbt.list
RUN curl -sL "https://keyserver.ubuntu.com/pks/lookup?op=get&search=0x2EE0EA64E40A89B84B2DF73499E82A75642AC823" | apt-key add
RUN apt-get update && apt-get install -y sbt

## Docker
RUN apt-get install -y \
        apt-transport-https \
        ca-certificates \
        curl \
        gnupg-agent \
        software-properties-common
RUN curl -fsSL https://download.docker.com/linux/debian/gpg | apt-key add -
RUN add-apt-repository \
       "deb [arch=amd64] https://download.docker.com/linux/debian \
       $(lsb_release -cs) \
       stable"
RUN apt-get update && apt-get install -y docker-ce

## Kubectl
RUN curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -
RUN touch /etc/apt/sources.list.d/kubernetes.list
RUN echo "deb http://apt.kubernetes.io/ kubernetes-xenial main" | tee -a /etc/apt/sources.list.d/kubernetes.list
RUN apt-get update && apt-get install -y --no-install-recommends kubectl=1.19.3-00

RUN apt-get clean && rm -rf /var/lib/apt/lists/*

## Takeoff
COPY setup.py /root
COPY MANIFEST.in /root
COPY README.md /root
COPY scripts /root/scripts
COPY takeoff /root/takeoff

WORKDIR /root

RUN python setup.py install

WORKDIR /src
