#! /bin/bash

osip=$1
host_patch=$2

# master or slave
node_tpye=$3
# master control ip
controller_ip=$4

devices=$5
model_names=$6
image_version=$7

docker_name=seafarer_medical_ai-${node_tpye}-${osip}
user_name=user-${osip}
docker_patch=/home/workspace
models_patch=${docker_patch}/medical_models/

echo osip=$osip
echo host_patch=$host_patch
echo docker_name=$docker_name
echo user_name=$user_name

docker_run=`docker ps -a | grep $docker_name`
if [  "$docker_run" ]; then
    echo "need docker rm -f $docker_name"
    docker rm -f $docker_name
fi

docker run -itd  \
    -v ${host_patch}:${docker_patch} \
    -v /root/.ssh:/root/.ssh \
    -v /etc/localtime:/etc/localtime \
    -v /etc/timezone:/etc/timezone \
    -e IEI_VISIBLE_MODELS_PATH=$models_patch \
    -e IEI_VISIBLE_OS_IP=$osip \
    -e IEI_VISIBLE_OS_USER_NAME=$user_name \
    -e IEI_VISIBLE_OS_DOCKER_NAME=$docker_name \
    -e IEI_VISIBLE_NODE_TYPE=$node_tpye \
    -e IEI_VISIBLE_CONTROLLER_IP=$controller_ip \
    -e IEI_VISIBLE_DEVICES=$devices    \
    -e IEI_VISIBLE_MODELS_NAME=$model_names    \
    --gpus all \
    --pid=host \
    --user=root \
    --cap-add=SYS_PTRACE \
    --privileged=true \
    --name $docker_name \
    --ipc=host \
    --network=host \
    --restart=always \
    --ulimit stack=68719476736 \
    --shm-size=100G \
    -w=$docker_patch \
    seafarer_medical_ai_l20_base_offline:$image_version \
    /bin/bash
