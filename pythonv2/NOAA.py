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
import sys
import os
import glob

from lib.FileIO import load_json_file, save_json_file, cfe


json_conf = load_json_file("../conf/as6.json")
station_id = json_conf['site']['ams_id']

def build_all_stations():
   """ This function creates the master station index
   """
   all_stations_file = "../conf/all_stations.json"
   all_station_data = []
   if cfe(all_stations_file) == 0:
      all_stations = []
      station_dirs = glob.glob("/mnt/wasabi/AMS*")
      for sd in station_dirs:

         station = sd.split("/")[-1]
         all_stations.append(station)
         data = {}
         data['station'] = station
         conf_file = "/mnt/wasabi/" + station + "/CAL/as6.json"

         jsd = load_json_file(conf_file)
         if jsd == 0:
            print("CONF FILE MISSING:", conf_file)
         else:
            data['location'] = [jsd['site']['device_lat'], jsd['site']['device_lng'], jsd['site']['device_alt']]
   else:
      all_stations = load_json_file(all_stations_file)
      all_station_data.append(data)
   save_json_file(all_stations_file, all_station_data)
   print(all_stations_file)
   exit()

def update_live_html():
   """ This function will only be runby a manager's node. 
       The purpose is to update the HTML and json indexes for the live view
   """
   now = datetime. now()
   day = now.strftime("%m_%d")
   year = now.strftime("%Y")

   all_stations_file = "../conf/all_stations.json" 
   if cfe(all_stations_file) == 0:
      build_all_stations()
   else:
      all_stations = load_json_file(all_stations_file)

   all_station_data = []
   for station in all_stations:
      data = {} 
      data['station'] = station 
      data['files'] = []
      NOAA_DIR =  "/mnt/wasabi/" + station + "/NOAA/ARCHIVE/" + year + "/" + day + "/" 
      if cfe(NOAA_DIR, 1) == 0:
        
         os.makedirs(NOAA_DIR)
      day_index = NOAA_DIR + day + "_index.json"
      if cfe(day_index) == 0 or True:
         live_files = glob.glob(NOAA_DIR + "*.jpg")
         for file in live_files:
            print("ADDING FILES FOR : ", station, file)
            data['files'].append(file)
      all_station_data.append(data)

   live_now = "" 
   for data in all_station_data:
      station = data['station']
      files = sorted(data['files'], reverse=True)
      data['files'] = files
      if len(files) > 0:
         fn = files[0].split("/")[-1]
         file_index = files[0].replace(fn, "")
         file_index = file_index.replace("mnt/wasabi", "meteor_archive")
         live_now +=  "<a href=" + file_index + "><img src=" + files[0].replace("mnt/wasabi", "meteor_archive") + "></a><BR>\n"
    
      NOAA_DIR =  "/mnt/wasabi/" + station + "/NOAA/ARCHIVE/" + year + "/" + day + "/" 
      day_index = NOAA_DIR + day + "_index.json"
      print(day_index)
      save_json_file(day_index, data)

   MAIN_NOAA_DIR = "/mnt/wasabi/NOAA/LIVE/" + year + "/" 
   asd_file = "/mnt/wasabi/NOAA/LIVE/" + year + "/" + day + "_index.json"
   asd_html = "/mnt/wasabi/NOAA/LIVE/" + year + "/index.html"
   if cfe(MAIN_NOAA_DIR, 1) == 0:
      os.makedirs(MAIN_NOAA_DIR)
   save_json_file(asd_file, all_station_data)
   out = open(asd_html, "w")
   out.write(live_now)
   out.close()
 
   
   print(asd_html)

   


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


      cmd = "/usr/bin/ffmpeg -y -i '" + url +  "' -vframes 1 -vf scale=320:180 " + outfile 
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
  
   desc = current_time + " " + station_id + " " + json_conf['site']['operator_city'] + "," + json_conf['site']['operator_state'] + " " + country 
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

if len(sys.argv) <= 1:
   update_live_view()
else:
   if sys.argv[1] == 'update_live_html' or sys.argv[1] == 'ulh':
      update_live_html()
