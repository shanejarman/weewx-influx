#!/bin/bash
# Install system dependencies needed for building packages on Raspberry Pi

# Update package lists
sudo apt update

# Install dependencies for Pillow
sudo apt install -y python3-dev libjpeg-dev zlib1g-dev libfreetype6-dev

# Install dependencies for other packages
sudo apt install -y libusb-1.0-0-dev libudev-dev

# Install development tools
sudo apt install -y build-essential

# Now try poetry install again
cd /home/realwx/weewx-influx
poetry install