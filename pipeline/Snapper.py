#!/usr/bin/python3

from lib.PipeUtil import check_running, load_json_file
import os
import time
from datetime import datetime
SNAP_DIR = "/mnt/ams2/SNAPS/"

# script for grabbing snaps every 30 seconds

def snap_runner():
   json_conf = load_json_file("../conf/as6.json")
   cams = {}
   for cam in json_conf['cameras']:
      id = json_conf['cameras'][cam]['cams_id']
      ip = json_conf['cameras'][cam]['ip']
      url = "rtsp://" + ip + json_conf['cameras'][cam]['hd_url']
      cams[id] = url
   running = check_running("Snapper.py")
   if running > 3:
      print("Snapper already running.")
      return()
   run = 1



   while run == 1:

      sec = int(datetime.now().strftime("%S"))
      if sec >= 50:
         sleep_time = 1
      elif 20 <= sec <= 30:
         sleep_time = 1
      else:
         sleep_time = 9


      if sec == 0 or sec == 30:
         for cam in cams:
            date_str = datetime.now().strftime("%Y_%m_%d_%H_%M_%S_000_")
            outfile = SNAP_DIR + date_str + cam + ".png"
            url = cams[cam]
            cmd = "/usr/bin/ffmpeg -y -i '" + url + "' -vframes 1 " + outfile + " >/dev/null 2>&1 &"
            print(cmd)
            os.system(cmd)
         time.sleep(20)
      print("Cur sec:", sec, "Sleeping for ", sleep_time)
      time.sleep(sleep_time)

snap_runner()
