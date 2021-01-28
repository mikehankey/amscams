
# script used to install WMPL tools by Denis Vida

mkdir /home/ams/dvida
cd /home/ams/dvida; 
git clone --recursive https://github.com/wmpg/WesternMeteorPyLib.git


sudo apt-get install build-essential autoconf libtool pkg-config python-opengl python-imaging python-pyrex python-pyside.qtopengl idle-python2.7 qt4-dev-tools qt4-designer libqtgui4 libqtcore4 libqt4-xml libqt4-test libqt4-script libqt4-network libqt4-dbus python-qt4 python-qt4-gl libgle3 python-dev
sudo apt-get install libgeos*
sudo apt-get install python-dev
sudo apt-get install -y python-subprocess32

sudo pip install numpy
sudo pip install scipy
sudo pip install cython
sudo python -m pip install -U matplotlib
sudo pip install jplephem
sudo pip install pyephem
sudo pip install ephem
sudo pip install ephem
sudo pip install pyproj
sudo pip install -U git+https://github.com/matplotlib/basemap.git
#sudo pip install basemap-data-hires

cd /home/ams/dvida/WesternMeteorPyLib/
sudo python setup.py install


#sudo apt-get install python-matplotlib
#sudo apt-get install build-essential autoconf libtool pkg-config python-opengl python-pyrex python-pyside.qtopengl idle-python2.7 qt4-dev-tools qt4-designer libqtgui4 libqtcore4 libqt4-xml libqt4-test libqt4-script libqt4-network libqt4-dbus python-qt4 python-qt4-gl libgle3 python-dev
#858  sudo apt-get remove python-mpltoolkits.basemap

