FROM schipholhub/takeoff-base:SNAPSHOT

COPY setup.py /root
COPY README.md /root
COPY scripts /root/scripts
COPY takeoff /root/takeoff

RUN python setup.py install

RUN pip install --ignore-installed azure-mgmt-containerservice==4.2.2 kubernetes==7.0.0

WORKDIR /src
