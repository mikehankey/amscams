#!/bin/bash
echo "Starting installation of packages..."
while IFS= read -r package
do
   echo "Installing $package..."
   sudo apt-get install -y "$package"
done < "apt-ubuntu-24.conf"
echo "All packages installed."
