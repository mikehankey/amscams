#!/usr/bin/python3

import subprocess
import sys
import os
from pathlib import Path
import glob
import json
from lib.FileIO import load_json_file, save_json_file, cfe

WASABI_ROOT = "/mnt/archive.allsky.tv/"
json_conf = load_json_file("/home/ams/amscams/conf/as6.json")

def check_mount():
   df_data = []
   mounts = {}
   wasabi = 0
   if True:
      cmd = "df -h "
      output = subprocess.check_output(cmd, shell=True).decode("utf-8")
      #Filesystem                 Size  Used Avail Use% Mounted on

      for line in output.split("\n"):
         file_system = line[0:20]
         size = line[20:26]
         used = line[27:38]
         avail = line[38:44]
         used_perc = line[44:49]
         mount = line[49:].replace(" ", "")
         if "/mnt/archive.allsky.tv" in line:
            wasabi = 1
   return(wasabi)

def cp_msd_from_wasabi():
   # all stations other than the master station need to do this 
   st = json_conf['site']['ams_id']
   cmd = "cp /mnt/archive.allsky.tv/" + st + "/DETECTS/ms_detects.json.gz /mnt/ams2/meteor_archive/" + st + "/DETECTS/"
   print(cmd)
   os.system(cmd)

   cmd = "gunzip -f /mnt/ams2/meteor_archive/" + st + "/DETECTS/ms_detects.json.gz"
   print(cmd)
   os.system(cmd)


   network_sites = json_conf['site']['network_sites'].split(",")
   for st in network_sites:
      cmd = "cp /mnt/archive.allsky.tv/" + st + "/DETECTS/ms_detects.json.gz /mnt/ams2/meteor_archive/" + st + "/DETECTS/"
      print(cmd)
      os.system(cmd)

      cmd = "gunzip -f /mnt/ams2/meteor_archive/" + st + "/DETECTS/ms_detects.json.gz"
      print(cmd)
      os.system(cmd)

def cp_msd2wasabi():
   # this should only be run from the central solving host for now...
   this_station = json_conf['site']['ams_id']
   cmd = "gzip -fk /mnt/ams2/meteor_archive/" + this_station + "/DETECTS/ms_detects.json"
   print(cmd)
   os.system(cmd)
   cmd = "cp /mnt/ams2/meteor_archive/" + this_station + "/DETECTS/ms_detects.json.gz /mnt/archive.allsky.tv/" + this_station + "/DETECTS/"
   print(cmd)
   os.system(cmd)

   network_sites = json_conf['site']['network_sites'].split(",")
   for st in network_sites:
      cmd = "gzip -fk /mnt/ams2/meteor_archive/" + st + "/DETECTS/ms_detects.json"
      print(cmd)
      os.system(cmd)
      cmd = "cp /mnt/ams2/meteor_archive/" + st + "/DETECTS/ms_detects.json.gz /mnt/archive.allsky.tv/" + st + "/DETECTS/"
      print(cmd)
      os.system(cmd)

def sync_archive(day):
   year = day[0:4]
   if day != "a":
      extra_day = "/" + day + "/" 
      extra_day_grep = "| grep " + day 
   else:
      extra_day = ""
      extra_day_grep = ""
   station_id = json_conf['site']['ams_id']

   # Sync Detect PREVIEWS 
   # get current detect wasabi index
   wasabi_detect_files = glob.glob("/mnt/archive.allsky.tv/" + station_id + "/DETECTS/PREVIEW/" + year + "/" + day + "/*.jpg")
   local_detect_files = glob.glob("/mnt/ams2/meteor_archive/" + station_id + "/DETECTS/PREVIEW/" + year + "/" + day + "/*.jpg")
   dw_idx = {}
   for ws in wasabi_detect_files:
      fn = ws.split("/")[-1]
      dw_idx[fn] = 1

   print("/mnt/ams2/meteor_archive/" + station_id + "/DETECTS/PREVIEW/" + year + "/" + day + "/*.jpg")
   print("LOCAL DETECT FILES:", len(local_detect_files))

   print("WASABI DETECT FILES:", len(wasabi_detect_files))
   # make sure wb dir exists for this day:
   html = "<h1>Detections for " + day + "</h1>"
   wb_dir = "/mnt/archive.allsky.tv/" + station_id + "/DETECTS/PREVIEW/" + year + "/" + day + "/" 
   if cfe(wb_dir,1) == 0:
      os.makedirs(wb_dir)
   else:
      print("WB DIR EXISTS!")
   for local in local_detect_files:
      lr = local.split("/")[-1]
      if lr in dw_idx:
         print("File is sync'd already:", lr)
      else: 
         print("File needs to be sync'd:", lr)
         cmd = "cp " + local + " " + wb_dir
         print(cmd)
         os.system(cmd)
      html += "<img src=" + lr + ">"

   fp = open(wb_dir + "index.html", "w")
   fp.write(html)
   fp.close()
   print(wb_dir + "index.html")

   exit()
   # Sync Meteors
   os.system("find /mnt/ams2/meteor_archive/" + station_id + " |grep METEOR | grep json  |grep trim > /mnt/ams2/tmp/arc.txt") 
   fp = open("/mnt/ams2/tmp/arc.txt", "r")
   for line in fp:
      line = line.replace("\n", "")
      wasabi_json = line.replace("ams2/meteor_archive", "archive.allsky.tv")
      if cfe(wasabi_json) == 0: 
         # need to copy files
         wf = wasabi_json.split("/")[-1]
         wd = wasabi_json.replace(wf, "")
         if cfe(wd, 1) == 0:
            print("make dir ", wd)
            os.makedirs(wd)
        
         cmd = "cp " + line + " " + wd
         os.system(cmd)

         sd_file = line.replace(".json", "-SD.mp4")
         cmd = "cp " + sd_file + " " + wd
         os.system(cmd)

         hd_file = line.replace(".json", "-HD.mp4")
         cmd = "cp " + hd_file + " " + wd
         os.system(cmd)
            
         print(cmd)
      else:
         print("Already exists!", wasabi_json)

      #print(line)
      #print(wasabi_json)

   # Sync Cal Dir
   

def wasabi_cp(file):
   if "meteor_archive" in file:
      wasabi_file = file.replace("ams2/meteor_archive", "archive.allsky.tv")
      cmd = "cp " + file + " " + wasabi_file
   else:
      ma_file = file.replace("archive.allsky.tv", "ams2/meteor_archive")
      cmd = "cp " + file + " " + ma_file
   print(cmd)
   os.system(cmd)

def install():
   cmd = """
   # THESE ARE THE COMMANDS:
   sudo mkdir /mnt/archive.allsky.tv
   sudo chown ams:ams /mnt/archive.allsky.tv/
   chmod 777 /mnt/archive.allsky.tv/
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
   #mkdir /mnt/archive.allsky.tv
   # Check if already mounted.
   mounted = check_mount()
   print("MOUNTED:", mounted)
   if mounted == 1:
      print("Wasabi is already mounted.")
      exit()
   

   #MOUNT COMMAND
   uid = os.getuid()
   gid = os.getgid()
   #cmd = "s3fs archive.allsky.tv /mnt/archive.allsky.tv -o passwd_file=/home/ams/amscams/conf/wasabi.txt -o dbglevel=debug -o url=https://s3.wasabisys.com -o umask=0007,uid="+str(uid)+",gid="+str(gid)
   #cmd = "s3fs -o use_path_request_style -o url=https://s3.wasabi.com archive.allsky.tv /mnt/archive.allsky.tv -o nonempty -o passwd_file=/home/ams/amscams/conf/wasabi.txt -o dbglevel=debug -o url=https://s3.wasabisys.com -o umask=0007,uid="+str(uid)+",gid="+str(gid)
   cmd = "s3fs -o use_path_request_style archive.allsky.tv /mnt/archive.allsky.tv -o nonempty -o passwd_file=/home/ams/amscams/conf/wasabi.txt -o dbglevel=debug -o url=https://s3.wasabisys.com -o umask=0007,uid="+str(uid)+",gid="+str(gid)
   print(cmd)
   os.system(cmd)


def setup_wasabi_dirs():
   print("SETUP")
   ams_id = json_conf['site']['ams_id'].upper()
   WASABI_DIR = WASABI_ROOT + ams_id + "/" 
   WASABI_CAL = WASABI_DIR + "CAL/" 
   WASABI_METEORS = WASABI_DIR + "METEOR/" 
   WASABI_CONF = WASABI_DIR + "CONF/" 
   


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

def make_indexes():
   make_ma_index()
   #make_wasabi_index()

def make_wasabi_index():
   os.system("find /mnt/archive.allsky.tv/ -ls > /mnt/archive.allsky.tv/wasbi_index.txt")

def make_ma_index():
   os.system("find /mnt/ams2/meteor_archive/ -ls > /mnt/ams2/meteor_archive/ma_index.txt")

if sys.argv[1] == "dirs":
   print("SETUP")
   setup_wasabi_dirs()
if sys.argv[1] == "mnt":
   connect_wasabi()
if sys.argv[1] == "cp":
   wasabi_cp(sys.argv[2])
if sys.argv[1] == "sa":
   sync_archive(sys.argv[2])
if sys.argv[1] == "ms2w" or sys.argv[1] == "cp_msd2wasabi":
   cp_msd2wasabi()
if sys.argv[1] == "cp_msd" or sys.argv[1] == "cp_msd_from_wasabi":
   cp_msd_from_wasabi()
if sys.argv[1] == "make_indexes" or sys.argv[1] == "mi":
   make_indexes()
