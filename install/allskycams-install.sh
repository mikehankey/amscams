#!/bin/sh
mkdir allsky6-install
cd allsky6-install

apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages update
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages dist-upgrade
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

# install ffmpeg
git clone https://gist.github.com/e4f713c8cd1a389a5917.git
#e4f713c8cd1a389a5917/install_ffmpeg_ubuntu.sh

update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-6 60 --slave /usr/bin/g++ g++ /usr/bin/g++-6

# INSTALL OPENCV

wget -O opencv.zip https://github.com/Itseez/opencv/archive/3.1.0.zip
unzip opencv.zip
wget -O opencv_contrib.zip https://github.com/Itseez/opencv_contrib/archive/3.1.0.zip
unzip opencv_contrib.zip

cd ~/opencv-3.1.0/
mkdir build
cd build
#make clean
cmake -D CMAKE_BUILD_TYPE=RELEASE \
    -D CMAKE_INSTALL_PREFIX=/usr/local \
    -D INSTALL_PYTHON_EXAMPLES=ON \
    -D OPENCV_EXTRA_MODULES_PATH=~/opencv_contrib-3.1.0/modules \
    -D WITH_OPENMP=ON \
    -D BUILD_EXAMPLES=ON ..
make -j4
make install
ldconfig

# INSTALL ASTROMETRY.NET
# INSTALL ASTROMETRY.NET PRE-REQUISITS
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install libwcs4
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install wcslib-dev

# Set gcc6 as CC env var
CC=/usr/bin/gcc-6
export CC

NETPBM_INC=-I/usr/include
NETPBM_LIB=/usr/lib/libnetpbm.a
export NETPBM_INC
export NETPBM_LIB

WCS_SLIB="-Lwcs"
WCSLIB_INC="-I/usr/local/include/wcslib-5.15"
WCL_LIB="-Lwcs"
export WCS_SLIB
export WCSLIB_INC
export WCS_LIB

apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install libcairo2-dev libnetpbm10-dev netpbm \
                       libjpeg-dev \
                       python-dev zlib1g-dev \
                       libbz2-dev swig libcfitsio-dev

cd ~/allsky6-install
wget http://astrometry.net/downloads/astrometry.net-latest.tar.gz
gunzip astrometry.net-latest.tar.gz
tar xf astrometry.net-latest.tar

cd astrometry.net-*
make
make py
make extra
make install

#need these catalogs index-4116.fits  index-4117.fits  index-4118.fits  index-4119.fits

wget http://broiler.astrometry.net/~dstn/4100/index-4116.fits
mv index-4116.fits /usr/local/astrometry/data
wget http://broiler.astrometry.net/~dstn/4100/index-4117.fits
mv index-4117.fits /usr/local/astrometry/data
wget http://broiler.astrometry.net/~dstn/4100/index-4118.fits
mv index-4118.fits /usr/local/astrometry/data
wget http://broiler.astrometry.net/~dstn/4100/index-4119.fits
mv index-4119.fits /usr/local/astrometry/data

apt-get install python3-dev

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
pip3 install opencv-python
pip3 install pycrypto
pip3 install sympy
sudo apt-get install python3-pil.imagetk
apt-get install scikit-image

#pip3 install scipy
#pip3 uninstall scipy
pip3 install python-imaging-tk
pip3 install pillow
pip3 install astride
# clone fireball camera code
# configurations...
# setup webserver vhost
# setup NIC card/ eth1/eth2
# setup DNS
# setup CAM configs
# add crontabs
# make sure VNC is good version
# determine video volume save location


git clone https://github.com/mikehankey/fireball_camera
mkdir /var/www
mkdir /var/www/html
mkdir /var/www/html/out
mkdir /var/www/html/out/false
mkdir /var/www/html/out/maybe
mkdir /var/www/html/out/cal
chown -R ams:ams /var/www
chown -R ams:ams ~/fireball_camera
ln -s /home/ams/fireball_camera/pycgi /var/www/html/pycgi

# install sshd
# reinstall scipy
sudo pip3 install --ignore-installed scipy
sudo pip3 install astropy
sudo pip3 install pycrypto 
sudo pip3 install astride 
sudo pip3 install fitsio

# to fix autocomplete in shell 
# https://stackoverflow.com/questions/23418831/command-line-auto-complete-tab-key-not-work-in-terminal-for-ubuntu

# configure apache
./ap.sh

# setup allsky6 config files
cd ~/fireball_camera

mkdir conf
cat config-example.txt |grep -v cam_ip > conf/config-1.txt
echo "cam_ip=192.168.76.71" >> conf/config-1.txt
cat config-example.txt |grep -v cam_ip > conf/config-2.txt
echo "cam_ip=192.168.76.72" >> conf/config-2.txt
cat config-example.txt |grep -v cam_ip > conf/config-3.txt
echo "cam_ip=192.168.76.73" >> conf/config-3.txt
cat config-example.txt |grep -v cam_ip > conf/config-4.txt
echo "cam_ip=192.168.76.74" >> conf/config-4.txt
cat config-example.txt |grep -v cam_ip > conf/config-5.txt
echo "cam_ip=192.168.76.75" >> conf/config-5.txt
cat config-example.txt |grep -v cam_ip > conf/config-6.txt
echo "cam_ip=192.168.76.76" >> conf/config-6.txt
rm config.txt
ln -s conf/config-1.txt ./config.txt

# /etc/network/interfaces config
# dhcp config
