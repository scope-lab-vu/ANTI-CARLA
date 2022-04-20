#FROM ubuntu:18.04
FROM nvidia/cudagl:10.1-devel-ubuntu18.04
RUN mkdir -p ANTI-CARLA
WORKDIR ANTI-CARLA
RUN apt-get update && apt-get install apt-transport-https

#install pip
RUN apt-get install -y python3
RUN apt-get update && apt-get install -y  python3-pip
RUN apt-get install -y python3.7
RUN python3.7 -m pip install pip
RUN python3.7 -m pip install --upgrade pip
RUN apt-get install -y vim
#RUN apt-get install -y python3.7-lxml
COPY requirements.txt requirements.txt
RUN python3.7 -m pip install -r requirements.txt
RUN python3.7 -m pip install --upgrade torch
RUN python3.7 -m pip install --upgrade torchvision
RUN python3.7 -m pip install --upgrade setuptools
RUN python3.7 -m pip install --upgrade tensorboard
RUN apt install -y libtiff5-dev
RUN apt-get install -y libxerces-c3.2
RUN apt-get install -y libjpeg-turbo8
RUN apt-get install -y libpng16-16
RUN apt-get install -y libsm6 libxrender1 libfontconfig1
RUN apt-get install -y libxext6 libgl1-mesa-glx
ENV TZ=US/Central
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
RUN apt-get install -y python3.7-tk
RUN useradd -p vandy -ms /bin/bash  carla
RUN apt-get -y install sudo
RUN  usermod -aG sudo carla
RUN echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers
USER carla
