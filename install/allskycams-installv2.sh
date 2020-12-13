# ALLSKYCAMS INSTALL SCRIPT FOR NATIVE OR VM UBUNTU INSTALL
# START WITH BASE ubuntu_18.04 AND THEN RUN THIS SCRIPT
# TO INSTALL THE PREREQUISTS AND CODE NEEDED TO RUN THE 
# ALLSKYCAMS SYSTEM
# MUST RUN AS SUDO



sudo apt-get update 
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install \
    apt-utils \
    apt-transport-https \
    ca-certificates \
    curl \
    software-properties-common \
    vim \ 
    sudo \
    python3 \
    python3-dev \
    curl \
    openssh-server \
    git \
    build-essential cmake pkg-config 


apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install libjpeg-dev libtiff-dev libpng-dev libg
tk2.0-dev
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install libavcodec-dev libavformat-dev libswsca
le-dev libv4l-dev
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install libxvidcore-dev libx264-dev
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install libgtk2.0-dev
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install libatlas-base-dev gfortran
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install -y tesseract-ocr libtesseract-dev lible
ptonica-dev

apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install libcairo2-dev libnetpbm10-dev netpbm 



apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install apache2 
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install ffmpeg
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install wcslib-dev
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install net-tools
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install vlc 
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install libcairo2-dev libnetpbm10-dev netpbm 
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install libpng-dev libjpeg-dev python-numpy zli
b1g-dev libbz2-dev swig libcfitsio-dev

apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install -y libavresample-dev

apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install libgtk-3-dev
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install -y libdc1394-22
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install  libdc1394-utils

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


apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install unzip

#wget -O opencv.zip https://github.com/opencv/opencv/archive/3.4.11.zip
#wget -O opencv_contrib.zip https://github.com/Itseez/opencv_contrib/archive/3.4.11.zip



#RUN FILE=/TEMP/; if [-f "$FILE" ]; then \
#   mkdir /TEMP/ && mkdir /TEMP/CV/; \
#fi
mkdir -p /TEMP/CV/ && mkdir -p /TEMP/AST/

# Use this if you have the opencv.tar on your network locally 
#cd /TEMP/CV/ && wget -O opencv.zip http://192.168.1.4/mnt/ams2/opencv.zip && \
#wget -O opencv_contrib.zip http://192.168.1.4/mnt/ams2/opencv_contrib.zip && \
#/usr/bin/unzip opencv.zip && /usr/bin/unzip opencv_contrib.zip 

# download opencv source
cd /TEMP/CV/ && wget -O opencv.zip https://github.com/opencv/opencv/archive/3.4.11.zip \ 
wget -O opencv_contrib.zip https://github.com/Itseez/opencv_contrib/archive/3.4.11.zip
/usr/bin/unzip opencv.zip && /usr/bin/unzip opencv_contrib.zip 

cd /TEMP/CV/opencv-3.4.11 && \
mkdir build && \
cd build 

#make clean \
#WORKDIR /TEMP/CV/opencv-3.4.11/build/
cmake -D CMAKE_BUILD_TYPE=RELEASE \
    -D CMAKE_INSTALL_PREFIX=/usr/local \
    -D BUILD_opencv_python2=OFF \
   -D WITH_LIBV4L=OFF\
    -D WITH_V4L=OFF \
    -D BUILD_opencv_python3=ON \
    -D WITH_OPENCL=OFF \
   -D MKL_USE_MULTITHREAD=ON \
    -D MKL_WITH_TBB=ON \
    -D WITH_FFMPEG=ON \
    -D WITH_GSTREAMER=OFF \
    -D INSTALL_PYTHON_EXAMPLES=ON \
    -D WITH_OPENMP=ON \
    -D BUILD_EXAMPLES=ON ..
cd /TEMP/CV/opencv-3.4.11/build/ && make && make install &&  /sbin/ldconfig 


pip3 install opencv-python


useradd -rm -d /home/ams -s /bin/bash -g root -G sudo -u 1001 ams
#USER ams
#WORKDIR /home/ams

apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install python python-dev

cd /home/ams && git clone https://github.com/mikehankey/fireball_camera && \
git clone https://github.com/mikehankey/amscams
run cd /home/ams/amscams && git pull
#USER root
ln -s /usr/include/wcslib-5.18 /usr/local/include/wcslib-5.15
/home/ams/amscams/install/astrometry-install.sh
#docker run -dit -P --name ubuntu-test -v ~/container-data:/data ubuntu
cd /home/ams/amscams/install && ./install-wasabi.py

ln -s /home/ams/amscams/install/README /home/ams/Desktop/README.txt

