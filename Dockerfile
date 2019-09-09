FROM sdhcontainerregistryshared.azurecr.io/takeoff-base-azure:SNAPSHOT

COPY setup.py /
COPY README.md /
COPY scripts /scripts
COPY takeoff /takeoff

RUN python setup.py install

RUN pip install --upgrade pip azure-mgmt-containerservice==4.2.2 kubernetes==7.0.0

WORKDIR /src
