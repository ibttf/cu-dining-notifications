#!/bin/bash

# Update system packages
sudo yum update -y

# Install Python 3 and pip if not already installed
sudo yum install python3 python3-pip -y

# Install required dependencies
sudo yum install -y \
    libX11 libXcomposite libXcursor libXdamage libXext libXi libXtst \
    cups-libs libXScrnSaver libXrandr alsa-lib pango atk at-spi2-atk gtk3 \
    wget unzip tar

# Create a temporary directory for downloads
mkdir -p ~/chrome_install
cd ~/chrome_install

# Install Chrome using RPM
wget https://dl.google.com/linux/direct/google-chrome-stable_current_x86_64.rpm
sudo yum localinstall -y google-chrome-stable_current_x86_64.rpm

# Get the Chrome version and install matching ChromeDriver
CHROME_VERSION=$(google-chrome-stable --version | cut -d' ' -f3)
CHROME_MAJOR_VERSION=$(echo $CHROME_VERSION | cut -d'.' -f1)
echo "Chrome version: $CHROME_VERSION (Major version: $CHROME_MAJOR_VERSION)"

# Download and install ChromeDriver
wget "https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/$CHROME_VERSION/linux64/chromedriver-linux64.zip"
unzip chromedriver-linux64.zip
sudo mv chromedriver-linux64/chromedriver /usr/local/bin/
sudo chown root:root /usr/local/bin/chromedriver
sudo chmod +x /usr/local/bin/chromedriver

# Clean up
cd ~
rm -rf ~/chrome_install

# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
python3 -m pip install --upgrade pip

# Install Python dependencies
pip install boto3 selenium webdriver_manager typing dataclasses

# Set up Chrome binary location and ChromeDriver path in environment
echo 'export CHROME_BINARY_LOCATION="/usr/bin/google-chrome-stable"' >> ~/.bashrc
echo 'export CHROMEDRIVER_PATH="/usr/local/bin/chromedriver"' >> ~/.bashrc
source ~/.bashrc

# Create directories for Chrome if they don't exist
sudo mkdir -p /usr/share/chrome
sudo chmod 777 /usr/share/chrome

# Verify installations
echo "Chrome version:"
google-chrome-stable --version
echo "ChromeDriver version:"
chromedriver --version
echo "Python version:"
python3 --version

# Print locations of binaries
echo "Chrome binary location:"
which google-chrome-stable
echo "ChromeDriver location:"
which chromedriver

# Print system resources
echo "System memory:"
free -h
echo "Disk space:"
df -h
