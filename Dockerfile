FROM python:3.7

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

COPY setup.py /
COPY README.md /
COPY scripts /scripts
COPY runway /runway

RUN python setup.py install
RUN pip install azure==4.0.0 --force-reinstall

RUN pip install azure-mgmt-containerservice==4.2.2 kubernetes==7.0.0

# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends lsb-release apt-transport-https \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*


# Install kubectl
RUN curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -
RUN touch /etc/apt/sources.list.d/kubernetes.list
RUN echo "deb http://apt.kubernetes.io/ kubernetes-xenial main" | tee -a /etc/apt/sources.list.d/kubernetes.list
RUN apt-get update && apt-get install -y --no-install-recommends kubectl=1.11.3-00 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
