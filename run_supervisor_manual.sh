#!/bin/bash
set -e

# Manual supervisor start script
echo "Starting Home Assistant Supervisor..."

# Check required directories
sudo mkdir -p /mnt/supervisor
sudo chmod 777 /mnt/supervisor

# Get supervisor version
VERSION_INFO=$(curl -s https://version.home-assistant.io/dev.json)
SUPERVISOR_VERSION=$(echo ${VERSION_INFO} | jq -e -r '.supervisor')
SUPERVISOR_IMAGE=$(echo ${VERSION_INFO} | jq -e -r '.images.supervisor' | sed 's/{arch}/amd64/g')

echo "Supervisor version: $SUPERVISOR_VERSION"
echo "Supervisor image: $SUPERVISOR_IMAGE"

# Run supervisor container
sudo docker run -d --rm --privileged \
    --name hassio_supervisor \
    --security-opt seccomp=unconfined \
    --security-opt apparmor=unconfined \
    -v /run/docker.sock:/run/docker.sock:rw \
    -v /run/dbus:/run/dbus:ro \
    -v /run/udev:/run/udev:ro \
    -v /mnt/supervisor:/data:rw \
    -v /etc/machine-id:/etc/machine-id:ro \
    -e SUPERVISOR_SHARE="/mnt/supervisor" \
    -e SUPERVISOR_NAME=hassio_supervisor \
    -e SUPERVISOR_DEV=1 \
    -e SUPERVISOR_MACHINE="qemux86-64" \
    -p 4357:4357 \
    "${SUPERVISOR_IMAGE}:${SUPERVISOR_VERSION}"

echo "Supervisor container started!"
echo "Waiting for supervisor to be ready..."
sleep 15

# Start CLI container
sudo docker run -d --rm \
    --name hassio_cli \
    -v /run/docker.sock:/run/docker.sock:rw \
    -v /mnt/supervisor:/data:rw \
    homeassistant/amd64-hassio-cli:latest

echo "CLI container started!"
echo ""
echo "Check status with: sudo docker logs hassio_supervisor"
echo "You can now use: ha supervisor info"
