FROM sdhcontainerregistryshared.azurecr.io/runway-base-azure:4.0.0

COPY setup.py /
COPY README.md /
COPY scripts /scripts
COPY runway /runway

RUN python setup.py install

RUN pip install azure-mgmt-containerservice==4.2.2 kubernetes==7.0.0

# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends lsb-release apt-transport-https \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    apt-transport-https \
    ca-certificates \
    gnupg2 \
    software-properties-common \
    build-essential \
    && curl -fsSL https://download.docker.com/linux/debian/gpg | apt-key add - \
    && apt-key fingerprint 0EBFCD88 \
    && add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/debian  $(lsb_release -cs) stable" \
    && apt-get update \
    && apt-get install -y --no-install-recommends docker-ce




# Install kubectl
RUN curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -
RUN touch /etc/apt/sources.list.d/kubernetes.list
RUN echo "deb http://apt.kubernetes.io/ kubernetes-xenial main" | tee -a /etc/apt/sources.list.d/kubernetes.list
RUN apt-get update && apt-get install -y --no-install-recommends kubectl=1.11.3-00 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /src
