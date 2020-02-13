#!/usr/bin/python3

"""
   AllSkyCams.com NOAA Weather Module
   This feature will link your allskycamera system with the NOAA weather archives and : 
      - copy 1 multi-camera live view image to the archive, each minute. 
      - copy 1 multi-camera preview stack image to the archive, each minute. 
    
   This data will be used by NOAA to analyze forcasts and get visual confirmation on weather conditions around the country. 
   This API will also allow NOAA employees to request video files from your system, for moments of interest they may want to capture.
      - for example, if your system happened to catch a tornado, or other weather event that needed further inspection
      - this does not give away access to your system, rather a file is placed on the NOAA server, that lists video files in your system they would like to see
      - when entries exist that request video files from your station, your system will copy these files to the NOAA directory, so they can be reviewed by NOAA staff. 
   All video request transfers are logged so the operator can monitor transfers and avoid abuse. 

"""
import time
import cv2
from datetime import datetime
from lib.FileIO import load_json_file, save_json_file, cfe
import os

json_conf = load_json_file("../conf/as6.json")
station_id = json_conf['site']['ams_id']



def update_live_view():
   """ This function will make a 6 or 7 camera image for the current moment and copy to the NOAA dir 

   """
   MAIN_NOAA_DIR =  "/mnt/ams2/NOAA/STATIONS/" + station_id + "/" 
   MY_NOAA_DIR =  "/mnt/ams2/meteor_archive/" + station_id + "/NOAA/" 
   
   now = datetime. now()
   current_time = now.strftime("%Y-%m-%d %H:%M:%S")
   time_file = now.strftime("%Y_%m_%d_%H_%M_00")
   year = now.strftime("%Y")
   mon = now.strftime("%m")
   day = now.strftime("%d")
   LIVE_DIR =  MY_NOAA_DIR + "/LIVE/"
   MY_NOAA_DIR += "ARCHIVE/" + year + "/" + mon + "_" + day + "/" 
   if cfe(LIVE_DIR, 1) == 0:
      os.makedirs(LIVE_DIR)

   if cfe(MY_NOAA_DIR, 1) == 0:
      os.makedirs(MY_NOAA_DIR)
   tmp_list = []
   for cam in json_conf['cameras']:
      ip = json_conf['cameras'][cam]['ip'] 
      sd_url  = json_conf['cameras'][cam]['sd_url'] 
      cams_id = json_conf['cameras'][cam]['cams_id'] 
      url = "rtsp://" + ip + sd_url
      outfile = MY_NOAA_DIR + time_file + "_" + cams_id + ".jpg"
      tmp_list.append(outfile)


      cmd = "ffmpeg -y -i '" + url +  "' -vframes 1 -vf scale=320:180 " + outfile 
      os.system(cmd)

   outwild = MY_NOAA_DIR + time_file + "_0*.jpg"
   out_allout = MY_NOAA_DIR + time_file + "_all.jpg"

   if cfe(out_allout) == 1:
      os.system("rm " + out_allout)

   time.sleep(2)
   cmd = "montage -mode concatenate -tile 6x " + outwild + " " + out_allout 
   os.system(cmd)
   print(cmd)
   time.sleep(2)

   img = cv2.imread(out_allout)
   if "country" not in json_conf['site']:
      country = "USA"
   else:
      country = json_conf['site']['country']
  
   desc = current_time + " " + station_id + json_conf['site']['operator_city'] + "," + json_conf['site']['operator_state'] + " " + country 
   cv2.putText(img, desc,  (5,175), cv2.FONT_HERSHEY_SIMPLEX, .3, (255, 255, 255), 1)

   cv2.imwrite(out_allout, img)

   print(out_allout)

   #remove temp files
   for tmp in tmp_list:
      cmd = "rm " + tmp
      os.system(cmd)

   # copy file to wasabi dir
   was_dir = MY_NOAA_DIR.replace("ams2/meteor_archive", "wasabi")
   was_out = out_allout.replace("ams2/meteor_archive", "wasabi")
   if cfe(was_dir, 1) == 0:
      os.makedirs(was_dir)
   os.system("cp " + out_allout + " " + was_out  )
   print(was_out)


update_live_view()
