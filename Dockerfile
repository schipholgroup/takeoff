FROM sdhcontainerregistryshared.azurecr.io/runway-base-azure:SNAPSHOT

COPY setup.py /
COPY README.md /
COPY scripts /scripts
COPY runway /runway

RUN python setup.py install

RUN pip install azure-mgmt-containerservice==4.2.2 kubernetes==7.0.0

WORKDIR /src
