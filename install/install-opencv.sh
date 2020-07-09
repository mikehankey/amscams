#!/bin/bash

sudo apt-get install libgtk-3-dev


sudo apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install libgtk-3-dev


sudo apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install python3.6-dev
sudo apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install libopenblas-dev
sudo apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install libvtk*
sudo apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install libvtk6-dev
sudo apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install vtk-6.3*
sudo apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install vtk*
sudo apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install libgtk3.0-dev
sudo apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install gtk+-3.0
sudo apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install libgtk-3-dev
<<<<<<< HEAD
sudo apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install libv4l-devel
=======
>>>>>>> fd67272194b9c6362888a8923c4b7d26be3e2b06
sudo apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install libv4l-dev
sudo apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install libv4l-0
sudo apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install libv4l*
sudo apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install python-vtk

sudo apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install libgstreamer1.0-0 gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly gstreamer1.0-libav gstreamer1.0-doc gstreamer1.0-tools gstreamer1.0-x gstreamer1.0-alsa gstreamer1.0-gl gstreamer1.0-gtk3 gstreamer1.0-qt5 gstreamer1.0-pulseaudio

sudo update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-6 60 --slave /usr/bin/g++ g++ /usr/bin/g++-6


# Install OPENCL run time
#cd ~/allsky6-install/
FILE=neo
FILE=~/allsky6-install/neo
if [ -f "$FILE" ]; then
    echo "$FILE exist"
else
    echo "$FILE does not exist"
    mkdir $FILE
    cd $FILE 
    #wget https://github.com/intel/compute-runtime/releases/download/20.07.15711/intel-gmmlib_19.4.1_amd64.deb
    #wget https://github.com/intel/compute-runtime/releases/download/20.07.15711/intel-igc-core_1.0.3342_amd64.deb
    #wget https://github.com/intel/compute-runtime/releases/download/20.07.15711/intel-igc-opencl_1.0.3342_amd64.deb
    #wget https://github.com/intel/compute-runtime/releases/download/20.07.15711/intel-opencl_20.07.15711_amd64.deb
    #wget https://github.com/intel/compute-runtime/releases/download/20.07.15711/intel-ocloc_20.07.15711_amd64.deb
    #wget https://github.com/intel/compute-runtime/releases/download/20.07.15711/ww07.sum
    #sha256sum -c ww07.sum
    #sudo dpkg -i *.deb
fi


cd ~/allsky6-install
FILE=~/allsky6-install/opencv
if [ -f "$FILE" ]; then
    echo "$FILE exist"
else
    echo "$FILE does not exist"
    wget -O opencv.zip https://github.com/Itseez/opencv/archive/3.1.0.zip
    unzip opencv.zip
    wget -O opencv_contrib.zip https://github.com/Itseez/opencv_contrib/archive/3.1.0.zip
    wget -O opencv.zip https://github.com/Itseez/opencv/archive/3.4.9.zip
    unzip opencv.zip
    wget -O opencv_contrib.zip https://github.com/Itseez/opencv_contrib/archive/3.4.9.zip
    unzip opencv_contrib.zip
fi


cd ~/opencv/
cd ~/allsky6-install/opencv/
mkdir build
cd build
make clean
cmake -D CMAKE_BUILD_TYPE=RELEASE \
    -D CMAKE_INSTALL_PREFIX=/usr/local \
    -D BUILD_opencv_python2=OFF \
    -D WITH_LIBV4L=OFF\
    -D WITH_V4L=OFF \
    -D BUILD_opencv_python3=ON \
    -D WITH_OPENCL=ON \
    -D MKL_USE_MULTITHREAD=ON \
    -D MKL_WITH_TBB=ON \
    -D WITH_FFMPEG=ON \
    -D WITH_GSTREAMER=ON \
    -D INSTALL_PYTHON_EXAMPLES=ON \
    -D OPENCV_EXTRA_MODULES_PATH=~/allsky6-install/opencv_contrib-3.4.9/modules \
    -D WITH_OPENMP=ON \
    -D BUILD_EXAMPLES=ON ..
make -j4
sudo make install
sudo ldconfig

sudo pip3 install opencv-python

#    -D WITH_MKL=ON \
