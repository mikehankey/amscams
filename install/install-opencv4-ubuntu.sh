sudo apt update
sudo apt install build-essential cmake git pkg-config libgtk-3-dev libavcodec-dev libavformat-dev libswscale-dev libv4l-dev libxvidcore-dev libx264-dev
sudo apt install libjpeg-dev libpng-dev libtiff-dev gfortran openexr libatlas-base-dev python3-dev python3-numpy libtbb2 libtbb-dev libdc1394-22-dev

$CV_DIR = ~/ams/opencv_base/
if [ -d "$CV_DIR" ]; then
    echo "$CV_DIR exist"
    cd ~ams/opencv_base/opencv
else
   echo "Cloning opencv source."
   mkdir ~ams/opencv_base
   cd ~ams/opencv_base/opencv
   #git clone https://github.com/opencv/opencv.git
   #git clone https://github.com/opencv/opencv_contrib.git
fi

mkdir build && cd build

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
    -D OPENCV_EXTRA_MODULES_PATH=~/opencv_base/opencv_contrib/modules \
    -D WITH_OPENMP=ON \
    -D BUILD_EXAMPLES=ON ..


make -j4
sudo make install
