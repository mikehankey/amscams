#sudo apt-get install libcfitsio-dev
#sudo apt-get install libjpeg-dev

mkdir ~/allsky6-install
cd ~/allsky6-install
#wget http://astrometry.net/downloads/astrometry.net-latest.tar.gz
#gunzip astrometry.net-latest.tar.gz
#tar xf astrometry.net-latest.tar
wget http://archive.allsky.tv/APPS/INSTALL/plot-constellations.c
cp plot-constellations.c astrometry.net-0.78/blind/

cd astrometry.net-*
make
make py
make extra
sudo make install

wget https://sleaziest-somali-2255.dataplicity.io/mnt/ams2/index-4116.fits
wget https://sleaziest-somali-2255.dataplicity.io/mnt/ams2/index-4117.fits
wget https://sleaziest-somali-2255.dataplicity.io/mnt/ams2/index-4118.fits
wget https://sleaziest-somali-2255.dataplicity.io/mnt/ams2/index-4119.fits

#mv *index*.fits /usr/local/astrometry/data
