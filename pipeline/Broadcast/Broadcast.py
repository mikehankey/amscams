#!/usr/bin/python3


import sys
import time


from lib.PipeLIVE import meteor_min_files, broadcast_live_meteors

'''

   Broadcast.py - Broadcast server script for Cloud Server.

'''

AMS_HOME = "/home/ams/amscams"
CONF_DIR = AMS_HOME + "/conf"
DATA_BASE_DIR = "/mnt/ams2"
PROC_BASE_DIR = "/mnt/ams2/SD/proc2"
PREVIEW_W = 300
PREVIEW_H = 169



if __name__ == "__main__":
   if len(sys.argv) >= 2:
      cmd = sys.argv[1]
   else:
      cmd = "default"

   if cmd == 'blm':
      broadcast_live_meteors()
