#!/bin/bash

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root"
    exit 1
fi

# Update packages
if [ -x "$(command -v apt)" ]; then
    echo "Updating packages..."
    apt update
else
    echo "apt is not available on this system."
    exit 1
fi

# Install required packages
echo "Installing required packages..."
apt install -y python3 python3-pip docker.io docker-compose

# Install Python requirements
echo "Installing Python requirements..."
pip3 install -r requirements.txt

# Create installation directory if needed
if [ ! -d "/opt/bask-e" ]; then
    echo "Creating installation directory..."
    mkdir -p /opt/bask-e
fi

# Enable and start Docker service
systemctl enable docker
systemctl start docker

# Copy files to installation directory
echo "Copying files to installation directory..."
cp -r * /opt/bask-e/

# Configure system services
echo "Configuring system services..."
cp services/etc/systemd/system/* /etc/systemd/system/
systemctl daemon-reload
systemctl enable ota_update.service app.service
systemctl start ota_update.service app.service

echo "Installation completed successfully!"