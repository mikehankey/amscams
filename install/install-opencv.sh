 sudo apt-get install libgtk-3-dev


sudo apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install python3.6-dev
sudo apt-get install libopenblas-dev
sudo apt-get install libvtk*
sudo apt-get install libvtk6-dev
sudo apt-get install vtk-6.3*
sudo apt-get install vtk*
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install libgtk3.0-dev
apt-get --yes --allow-downgrades --allow-remove-essential --allow-change-held-packages install gtk+-3.0
sudo apt-get install libgtk-3-dev
sudo apt-get install libv4l-devel
sudo apt-get install libv4l-dev
sudo apt-get install libv4l-0
sudo apt-get install libv4l*
sudo apt-get install python-vtk


update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-6 60 --slave /usr/bin/g++ g++ /usr/bin/g++-6

# INSTALL OPENCV

#wget -O opencv.zip https://github.com/Itseez/opencv/archive/3.1.0.zip
#unzip opencv.zip
#wget -O opencv_contrib.zip https://github.com/Itseez/opencv_contrib/archive/3.1.0.zip
#unzip opencv_contrib.zip

cd ~/opencv/
mkdir build
cd build
#make clean
cmake -D CMAKE_BUILD_TYPE=RELEASE \
    -D CMAKE_INSTALL_PREFIX=/usr/local \
    -D BUILD_opencv_python2=OFF \
    -D WITH_LIBV4L=OFF\
    -D WITH_V4L=OFF \
    -D BUILD_opencv_python3=ON \
    -D WITH_MKL=ON \
    -D MKL_USE_MULTITHREAD=ON \
    -D MKL_WITH_TBB=ON \
    -D WITH_FFMPEG=ON \
    -D WITH_GSTREAMER=ON \
    -D INSTALL_PYTHON_EXAMPLES=ON \
    -D OPENCV_EXTRA_MODULES_PATH=~/opencv_contrib/modules \
    -D WITH_OPENMP=ON \
    -D BUILD_EXAMPLES=ON ..
make -j4
make install
ldconfig
