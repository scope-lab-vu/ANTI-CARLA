#!/bin/bash

#pull carla image
if [ ! -d CARLA_0.9.10 ]
then
  echo $OSTYPE
  if [[ "$OSTYPE" == "linux-gnu"* ]];
  then
    echo "CARLA Simulator package not found. Downloading the simulator package"
    wget https://carla-releases.s3.eu-west-3.amazonaws.com/Linux/CARLA_0.9.10.tar.gz
    mkdir CARLA_0.9.10
    tar -xzvf CARLA_0.9.10.tar.gz -C CARLA_0.9.10
    rm -rf CARLA_0.9.10.tar.gz
  else
    wget https://carla-releases.s3.eu-west-3.amazonaws.com/Windows/CARLA_0.9.10.zip
    mkdir CARLA_0.9.10
    unzip -d CARLA_0.9.10 CARLA_0.9.10.zip
    rm -rf CARLA_0.9.10.zip
  fi
else
  echo "CARLA Simulator package found"

fi

#pull trained LEC weights
if [ -f $PWD/carla-challange/carla_project/model.ckpt ]
then
  echo "LEC model already exists"
else
  echo "Pulling the trained LEC model"
  wget "https://vanderbilt365-my.sharepoint.com/:u:/g/personal/shreyas_ramakrishna_vanderbilt_edu/Eaq1ptU-YJJPrqmEYUK_dx8Bad2KqhVQZJkKwngWnuMWRA?e=U3dtyf&download=1" -O model.zip
  unzip $PWD/model.zip -d $PWD/carla-challange/carla_project
  rm -rf model.zip
fi

#pull trained OOD detector weights
if [ -d $PWD/carla-challange/leaderboard/detector_code/ood_detector_weights ]
then
  echo "Trained OOD model already exists"
else
  echo "Pulling the trained OOD model"
  wget "https://vanderbilt365-my.sharepoint.com/:u:/g/personal/shreyas_ramakrishna_vanderbilt_edu/EbB6W8s1XgFJg0Uv762w3v0B8SVj2B8PtiX6tP2UbCn_dw?e=BPqmcX&download=1" -O ood_detector_weights.zip
  #mkdir $PWD/carla-challange/leaderboard/detector_code/ood_detector_weights
  unzip $PWD/ood_detector_weights.zip
  mv $PWD/B-VAE-weights  $PWD/carla-challange/leaderboard/detector_code/ood_detector_weights
  rm -rf ood_detector_weights.zip

fi
