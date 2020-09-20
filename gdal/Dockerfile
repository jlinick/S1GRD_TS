FROM osgeo/gdal:latest
MAINTAINER jlinick@mit.edu

# Set the working directory
WORKDIR /home

# Install necessary items
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
    apt-get install -y jq aria2 zip unzip curl git vim ffmpeg wget

# Install pip
RUN apt-get install -y software-properties-common && \
    apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y python3-distutils && \
    curl -s https://bootstrap.pypa.io/get-pip.py --output get-pip.py && \
    python3 get-pip.py && \
    rm -rf get-pip.py

RUN pip3 install --noinput numpy fiona shapely

COPY . /S1GRD_TS
