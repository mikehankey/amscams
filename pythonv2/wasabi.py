#!/usr/bin/python3

import sys
import os
from pathlib import Path
import glob
import json
from lib.FileIO import load_json_file, save_json_file, cfe

WASABI_ROOT = "/mnt/wasabi/"
json_conf = load_json_file("../conf/as6.json")

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

def connect_wasabi():
   #sudo apt-get install build-essential libcurl4-openssl-dev libxml2-dev mime-support
   #sudo apt-get install s3fs # This needs to be s3fs-fuse https://github.com/s3fs-fuse/s3fs-fuse/wiki/Installation-Notes

   # Setup credentials file /home/ams/amscams/conf/wasabi.txt
   # XXX:YYYYY

   #chmod 600 ~/wasabi_ams1.txt
   #mkdir /mnt/wasabi

   #MOUNT COMMAND
   cmd = "s3fs meteor-archive /mnt/wasabi -o passwd_file=/home/ams/amscams/conf/wasabi.txt -o dbglevel=debug -o url=https://s3.wasabisys.com -o umask=0007,uid=1000,gid=1000"
   print(cmd)
   os.system(cmd)


def setup_wasabi_dirs():
   print("SETUP")
   ams_id = json_conf['site']['ams_id'].upper()
   WASABI_DIR = WASABI_ROOT + ams_id + "/" 
   WASABI_CAL = WASABI_DIR + "cal/" 
   WASABI_METEORS = WASABI_DIR + "meteors/" 
   WASABI_CONF = WASABI_DIR + "conf/" 
   


   if cfe(WASABI_ROOT, 1) != 1:
      print("ERR: No wasabi root.", WASABI_ROOT)
      exit()
   if cfe(WASABI_DIR, 1) != 1:
      print("ERR: No wasabi user dir.", WASABI_DIR)
      exit()
   if cfe(WASABI_CAL, 1) != 1:
      print("mkdir " + WASABI_CAL)
      os.system("mkdir " + WASABI_CAL)
   if cfe(WASABI_METEORS, 1) != 1:
      print("mkdir " + WASABI_METEORS)
      os.system("mkdir " + WASABI_METEORS)
   if cfe(WASABI_CONF, 1) != 1:
      print("mkdir " + WASABI_CONF)
      os.system("mkdir " + WASABI_CONF)
   print("DONE SETUP")

if sys.argv[1] == "dirs":
   print("SETUP")
   setup_wasabi_dirs()
if sys.argv[1] == "mnt":
   connect_wasabi()
