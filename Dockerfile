FROM schipholhub/takeoff-base:1.0.2

COPY setup.py /root
COPY README.md /root
COPY scripts /root/scripts
COPY takeoff /root/takeoff

WORKDIR /root

RUN python setup.py install

RUN pip install --ignore-installed azure-mgmt-containerservice==4.2.2 kubernetes==7.0.0

WORKDIR /src
