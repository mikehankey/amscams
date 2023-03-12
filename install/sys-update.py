#!/usr/bin/python3 
import os

# update packages
os.system("sudo apt update")
os.system("sudo apt upgrade")

# update s3fs
os.system("cd /home/ams/s3fs; git update; ./autogen.sh; ./configure --prefix=/usr --with-openssl; make; sudo make install")
