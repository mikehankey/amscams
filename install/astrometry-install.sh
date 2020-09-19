#!/bin/sh


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

mkdir /home/ams/astrometry/
cd /home/ams/astrometry/

#wget http://astrometry.net/downloads/astrometry.net-latest.tar.gz
wget http://192.168.1.4/mnt/ams2/astrometry.net-mike.tar.gz
gunzip astrometry.net-mike.tar.gz
tar xf astrometry.net-mike.tar


cd /home/ams/astrometry/astrometry.net-0.73/
wget http://archive.allsky.tv/APPS/INSTALL/plot-constellations.c
cp plot-constellations.c blind
cp plot-constellations.c astrometry/blind
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
mv index-4119.fits /usr/local/astrometry/datado mv index-4119.fits /usr/local/astrometry/data
