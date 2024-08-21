#!/bin/bash

# to install / run this copy and past this command:
# wget https://archive.allsky.tv/APPS/INSTALL/apt-ubuntu-24.sh -O apt-ubuntu-24.sh ; chmod +x apt-ubuntu-24.sh; sudo ./apt-ubuntu-24.sh


echo "Starting installation of packages..."
wget https://archive.allsky.tv/APPS/INSTALL/apt-ubuntu-24.conf -O apt-ubuntu-24.conf
while IFS= read -r package
do
   echo "Installing $package..."
   sudo apt-get install -y "$package"
done < "apt-ubuntu-24.conf"
echo "All packages installed."

git pull
apt update
apt install -y make build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev libncursesw5-dev xz-utils tk-dev libffi-dev liblzma-dev python-openssl git
apt install -y make build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev libncursesw5-dev xz-utils tk-dev libffi-dev liblzma-dev python3-openssl git
curl -L https://github.com/pyenv/pyenv-installer/raw/master/bin/pyenv-installer | bash
echo 'export PATH="$HOME/.pyenv/bin:$PATH"' >> ~ams/.bashrc
echo 'eval "$(pyenv init --path)"' >> ~ams/.bashrc
echo 'eval "$(pyenv virtualenv-init -)"' >> ~ams/.bashrc


chown ams:ams ~ams/.bashrc
cd ~ams/
git clone https://github.com/mikehankey/amscams.git
cd amscams/install
./AS7Setup.py

cp /home/ams/amscams/pipeline/000-default.conf /etc/apache2/sites-enabled/000-default.conf
a2enmod rewrite
systemctl restart apache2
sudo umount /mnt/archive.allsky.tv
cd ~ams/amscams/install
./check_install.py
apt install apache2-utils
htpasswd -c /etc/apache2/.htpasswd AMS171
chown ams:ams /etc/apache2/.htpasswd
chmod 640 /etc/apache2/.htpasswd
systemctl restart apache2

