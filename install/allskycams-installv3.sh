# ALLSKYCAMS INSTALL SCRIPT FOR NATIVE OR VM UBUNTU INSTALL
# START WITH BASE ubuntu_18.04 AND THEN RUN THIS SCRIPT
# TO INSTALL THE PREREQUISTS AND CODE NEEDED TO RUN THE 
# ALLSKYCAMS SYSTEM
# MUST RUN AS SUDO



#sudo apt-get update 
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install apt-utils apt-transport-https ca-certificates curl software-properties-common 
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install vim sudo curl openssh-server git build-essential cmake pkg-config 


apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install python3
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install python3-dev
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install libjpeg-dev libtiff-dev libpng-dev libgtk2.0-dev
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install libavcodec-dev libavformat-dev libswscale-dev libv4l-dev
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install libxvidcore-dev libx264-dev
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install libgtk2.0-dev
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install libatlas-base-dev gfortran
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install tesseract-ocr libtesseract-dev libleptonica-dev

apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install libcairo2-dev libnetpbm10-dev netpbm 



apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install apache2 
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install ffmpeg
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install wcslib-dev
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install net-tools
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install vlc 
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install libcairo2-dev libnetpbm10-dev netpbm 
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install libpng-dev libjpeg-dev python-numpy zlib
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install libbz2-dev swig libcfitsio-dev

apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install libavresample-dev

apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install libgtk-3-dev
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install libdc1394-22
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install libdc1394-utils
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install unzip
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install python python-dev

# PIP installs
wget https://bootstrap.pypa.io/get-pip.py 
python3 get-pip.py && \
mv /usr/local/bin/pip /usr/local/bin/pip3

pip3 install numpy daemon pyephem netifaces pathlib fitsio pyfits pillow numpy scipy pandas matplotlib requests scikit-image sklearn wand pytesseract pycrypto astropy sympy vtk ephem


apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install libtbb2 \
libtbb-dev \
libjpeg-dev \
libpng-dev \
libtiff-dev \
libdc1394-22-dev \
ocl-icd-opencl-dev \
libopenblas-base \
libopenblas-dev \
cifs-utils 




cd /home/ams && git clone https://github.com/mikehankey/fireball_camera && \
git clone https://github.com/mikehankey/amscams
run cd /home/ams/amscams && git pull
#USER root
ln -s /usr/include/wcslib-5.18 /usr/local/include/wcslib-5.15
/home/ams/amscams/install/astrometry-install.sh
#docker run -dit -P --name ubuntu-test -v ~/container-data:/data ubuntu
cd /home/ams/amscams/install && ./install-wasabi.py

ln -s /home/ams/amscams/install/README /home/ams/Desktop/README.txt

