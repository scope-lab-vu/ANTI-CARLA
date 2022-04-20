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
