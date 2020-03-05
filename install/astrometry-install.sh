#!/bin/sh
sudo apt-get install libcfitsio-dev
#sudo apt-get install libjpeg-dev

# Set gcc6 as CC env var
CC=/usr/bin/gcc-6
export CC

# MAKE SURE WE HAVE ALL PRE-REQS ELSE THIS WILL FAIL
# ESP GCC6! & CFITS IO
# MAKE SURE WE HAVE RIGHT VERSION OF wcslib in WCSLIB_INC line below
# MAKE SURE with have the python2 verison of pyfitsio


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

cd ~/allsky6-install
wget http://astrometry.net/downloads/astrometry.net-latest.tar.gz
gunzip astrometry.net-latest.tar.gz
tar xf astrometry.net-latest.tar

sudo pip install astropy

cd astrometry.net-*
make
make py
make extra
sudo make install

#need these catalogs index-4116.fits  index-4117.fits  index-4118.fits  index-4119.fits

wget http://broiler.astrometry.net/~dstn/4100/index-4116.fits
sudo mv index-4116.fits /usr/local/astrometry/data
wget http://broiler.astrometry.net/~dstn/4100/index-4117.fits
sudo mv index-4117.fits /usr/local/astrometry/data
wget http://broiler.astrometry.net/~dstn/4100/index-4118.fits
sudo mv index-4118.fits /usr/local/astrometry/data
wget http://broiler.astrometry.net/~dstn/4100/index-4119.fits
sudo mv index-4119.fits /usr/local/astrometry/data
