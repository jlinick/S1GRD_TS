FROM ukhydrographicoffice/esa-snap7-snappy:latest
MAINTAINER jlinick@mit.edu

WORKDIR /workdir

# install required modules
RUN apt-get update && \
    apt-get -y install python3-pip git vim zip unzip

COPY ./ /S1GRD_TS

