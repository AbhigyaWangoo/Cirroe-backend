#!/bin/bash
set -e

# python3.12 -m venv venv
# source venv/bin/activate

# Install unzip
apt-get update && apt-get install -y unzip

# Download and install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
./aws/install

# Verify installation
aws --version

# Clean up
rm -rf aws awscliv2.zip

# pip3 install -r requirements.txt