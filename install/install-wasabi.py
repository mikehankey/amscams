#!/usr/bin/python3

import os

def install():
   cmd = """
   # THESE ARE THE COMMANDS:
   sudo mkdir /mnt/wasabi
   sudo chown ams:ams /mnt/wasabi/
   chmod 777 /mnt/wasabi/
   sudo apt-get install build-essential git libfuse-dev libcurl4-openssl-dev libxml2-dev mime-support automake libtool
   sudo apt-get install pkg-config libssl-dev
   cd ../../
   git clone https://github.com/s3fs-fuse/s3fs-fuse
   cd s3fs-fuse/
   ./autogen.sh
   ./configure --prefix=/usr --with-openssl
   make
   sudo make install
   cd ../amscams
   cd conf
   ADD KEY TO CONF FILE
   vi wasabi.txt
   chmod 600 wasabi.txt 
   """

os.system("sudo mkdir /mnt/archive.allsky.tv")
os.system("sudo chown ams:ams /mnt/archive.allsky.tv")
os.system("sudo chown ams:ams /mnt/archive.allsky.tv")
os.system("chomd 777 /mnt/archive.allsky.tv")
os.system("sudo apt-get install build-essential git libfuse-dev libcurl4-openssl-dev libxml2-dev mime-support automake libtool")
os.system("sudo apt-get install pkg-config libssl-dev")
os.system("cd /home/ams/; git clone https://github.com/s3fs-fuse/s3fs-fuse;")
os.system("cd /home/ams/s3fs-fuse/; ./autogen.sh")
os.system("cd /home/ams/s3fs-fuse/; ./configure --prefix=/usr --with-openssl")
os.system("cd /home/ams/s3fs-fuse/; make")
os.system("cd /home/ams/s3fs-fuse/; sudo make install")


