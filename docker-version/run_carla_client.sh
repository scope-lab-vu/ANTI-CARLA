#! /bin/bash

#run the docker container
docker run -it --rm \
    -v $(pwd)/ANTI-CARLA/:/ANTI-CARLA \
    -v $(pwd)/CARLA_0.9.10/:/CARLA_0.9.10 \
    --env="QT_X11_NO_MITSHM=1" \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    -e DISPLAY \
    --runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=2 \
    anti_carla:v1 bash
