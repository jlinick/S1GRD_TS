FROM ukhydrographicoffice/esa-snap7-snappy:latest
MAINTAINER jlinick@mit.edu

WORKDIR /workdir

# install required modules
RUN apt-get update && \
    apt-get -y install python3-pip git vim zip unzip
RUN python3.6 -m pip install fiona shapely

# sets max mem of the jvc to 40GB.
RUN sed -i '3s/.*/java_max_mem: 30G/' /usr/lib/python3.6/dist-packages/snappy/snappy.ini

COPY ./ /S1GRD_TS

