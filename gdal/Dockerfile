FROM osgeo/gdal:latest
MAINTAINER jlinick@mit.edu

# Set the working directory
WORKDIR /workdir

# Install necessary items
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
    apt-get install -y python3-pip jq aria2 zip unzip curl git vim ffmpeg wget
RUN pip3 install numpy fiona shapely requests

# Copy repo into image
COPY ./ /S1GRD_TS
