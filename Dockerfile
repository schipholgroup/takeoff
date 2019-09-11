FROM schipholhub/takeoff-base:SNAPSHOT

COPY setup.py /
COPY README.md /
COPY scripts /scripts
COPY takeoff /takeoff

RUN python setup.py install

RUN pip install --ignore-installed azure-mgmt-containerservice==4.2.2 kubernetes==7.0.0

WORKDIR /src
