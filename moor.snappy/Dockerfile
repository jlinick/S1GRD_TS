# use debian as base image
FROM mrmoor/esa-snap:latest
MAINTAINER jlinick@mit.edu

WORKDIR /workdir

# install jdk and python3 with required modules
RUN apt-get update && \
    apt-get -y install default-jdk python3 python3-pip git maven python3-jpy vim zip unzip
RUN python3 -m pip install --user --upgrade setuptools wheel

# set JDK_HOME env
ENV JDK_HOME="/usr/lib/jvm/default-java"
ENV JAVA_HOME=$JDK_HOME
ENV PATH=$PATH:/root/.local/bin

# install snappy the SNAP python module
RUN /usr/local/snap/bin/snappy-conf /usr/bin/python3
RUN cd /root/.snap/snap-python/snappy/ && python3 setup.py install
RUN ln -s /root/.snap/snap-python/snappy /usr/lib/python3/dist-packages/snappy

COPY ./ /S1GRD_TS

