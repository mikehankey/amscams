#!/bin/sh

# make the install work directory
mkdir ~/allsky6-install
cd ~/allsky6-install

#APT UPDATE 
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages update
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages dist-upgrade


#APT PRE-REQUISTES
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages upgrade
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install python2.7-dev python3.5-dev
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install curl -y
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install lynx -y

apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install openssh-server 
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install git
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install build-essential cmake pkg-config
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install libjpeg-dev libtiff5-dev libjasper-dev libpng12-dev
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install libavcodec-dev libavformat-dev libswscale-dev libv4l-dev
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install libxvidcore-dev libx264-dev
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install libgtk2.0-dev
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install libatlas-base-dev gfortran
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install -y tesseract-ocr libtesseract-dev libleptonica-dev
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install python3-dateutil
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install python3-pil
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install libwcs4
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install wcslib-dev
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install libcairo2-dev libnetpbm10-dev netpbm \

apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install isc-dhcp-server
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install xfce4 xfce4-goodies vnc4server
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install ubuntu-gnome-desktop -y
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install gnome-menu-editor -y
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install gnome-panel -y
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install curl -y
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install lynx -y
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install python3-tk
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install apache2 
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install ffmpeg
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install libwcs4
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install wcslib-dev

apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install libcairo2-dev libnetpbm10-dev netpbm \
                       libpng12-dev libjpeg-dev python-numpy \
                       python-pyfits python-dev zlib1g-dev \
                       libbz2-dev swig libcfitsio-dev
apt-get --yes install gcc-6 g++-6 g++-6-multilib gfortran-6
update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-6 60 --slave /usr/bin/g++ g++ /usr/bin/g++-6

# Python
apt-get --yes install python3-dev
apt-get --yes install python-dev

#PIP
wget https://bootstrap.pypa.io/get-pip.py
python3 get-pip.py
mv /usr/local/bin/pip /usr/local/bin/pip3
python get-pip.py

#PIP INSTALLS
pip3 install dropbox
pip3 install pyephem
pip3 install fitsio 
pip3 install matplotlib
pip3 install netifaces
pip3 install numpy
pip3 install pathlib
pip3 install Pillow
pip3 install pytesseract
pip3 install requests
pip3 install scikit-image
pip3 install scipy
pip3 install sklearn
pip3 install --upgrade google-api-python-client
pip3 install wand
pip3 install netifaces
pip3 install numpy
pip3 install pathlib
pip3 install pyephem
pip3 install pytesseract
#pip3 install opencv-python
pip3 install pycrypto

sudo pip3 install --ignore-installed scipy
sudo pip3 install astropy
sudo pip3 install pycrypto 
sudo pip3 install astride 
sudo pip3 install fitsio
#sudo apt-get install python3-pil.imagetk
apt-get --yes install scikit-image

#pip3 install scipy
#pip3 uninstall scipy
pip3 install python-imaging-tk
pip3 install pillow
pip3 install astride
pip3 install sympy 

#


#clone repos
cd ~
git clone https://github.com/mikehankey/fireball_camera
git clone https://github.com/mikehankey/amscams
