#!/bin/bash
set -e

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