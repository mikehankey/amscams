#!/usr/bin/python3

import sys
import os
from pathlib import Path
import glob
import json
from lib.FileIO import load_json_file, save_json_file, cfe

WASABI_ROOT = "/mnt/wasabi/"
json_conf = load_json_file("../conf/as6.json")

def connect_wasabi():
   #sudo apt-get install build-essential libcurl4-openssl-dev libxml2-dev mime-support
   #sudo apt-get install s3fs # This needs to be s3fs-fuse https://github.com/s3fs-fuse/s3fs-fuse/wiki/Installation-Notes

   # Setup credentials file /home/ams/amscams/conf/wasabi.txt
   # XXX:YYYYY

   #chmod 600 ~/wasabi_ams1.txt
   #mkdir /mnt/wasabi

   #MOUNT COMMAND
   cmd = "s3fs meteor-archive /mnt/wasabi -o passwd_file=/home/ams/amscams/conf/wasabi.txt -o dbglevel=debug -o url=https://s3.wasabisys.com -o umask=0007,uid=$UID,gid=$GID"
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
