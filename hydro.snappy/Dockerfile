FROM ukhydrographicoffice/esa-snap7-snappy:latest
MAINTAINER jlinick@mit.edu

WORKDIR /workdir

# install required modules
RUN apt-get update && \
    apt-get -y install python3-pip git vim zip unzip
RUN python3.6 -m pip install fiona shapely

COPY ./ /S1GRD_TS

