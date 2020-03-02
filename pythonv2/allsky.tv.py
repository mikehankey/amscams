#!/usr/bin/python3


"""

This is the master publisher / updater for archive.allsky.tv 
Programs in this script should only be run by an admin server since they require full perms to the archive.

Use this program to:
  - update the LIVE page of the site
  - update the master list of meteors across stations per day
  - update the master list of meteors arcross stations per year

"""

import time
import cv2
from datetime import datetime
import sys
import random
import os
import glob

from lib.FileIO import load_json_file, save_json_file, cfe
 

LIVE_TEMPLATE = "templates/allsky.tv.live.html"
LIVE_DIR = "/mnt/archive.allsky.tv/LIVE/"

json_conf = load_json_file("../conf/as6.json")
station_id = json_conf['site']['ams_id'] 

def update_live_html():
   """ This function will only be runby a manager's node.
       The purpose is to update the HTML and json indexes for the live view
   """

   template = get_template(LIVE_TEMPLATE)
   now = datetime. now()
   mday = now.strftime("%m_%d")
   mon = now.strftime("%m")
   dom = now.strftime("%Y_%m_%d")
   year = now.strftime("%Y")

   all_stations_file = "../conf/all_stations.json"
   if cfe(all_stations_file) == 0:
      build_all_stations()
   all_stations = load_json_file(all_stations_file)
   status = {}
   all_station_data = []
   for sd in all_stations:
      station = sd['station']
      status[station] = 0
      data = {}
      data['station'] = station
      data['files'] = []
      NOAA_DIR =  "/mnt/archive.allsky.tv/" + station + "/NOAA/ARCHIVE/" + year + "/" + mday + "/"
      if cfe(NOAA_DIR, 1) == 0:
         os.makedirs(NOAA_DIR)
      day_index = NOAA_DIR + mday + "_index.json"
      live_files = glob.glob(NOAA_DIR + "*.jpg")
      for file in live_files:
         #print("ADDING FILES FOR : ", station, file)
         data['files'].append(file)
         status[station] = 1
      all_station_data.append(data)

   live_now = """
         <div class='d-flex align-content-start flex-wrap'>
   """ 



   data_per_station = {}

    
   for data in all_station_data:
      station = data['station']
      STATION_RPT_DIR =  "/mnt/archive.allsky.tv/" + station + "/REPORTS/" + year + "/" + mday + "/"
      STATION_RPT_VDIR =  "/" + station + "/REPORTS/" + year + "/" + mday + "/"
      files = sorted(data['files'], reverse=True)
      data['files'] = files 
      if len(files) > 0:
         fn = files[0].split("/")[-1]
         file_index = files[0].replace(fn, "")
         file_index = file_index.replace("/mnt/archive.allsky.tv", "")
         st = os.stat(files[0])
         size = st.st_size
         if size != 0:
            # Status
            stt = ""
            if(station in status):
               if(status[station]==1):
                  stt = 'ok';
               else:
                  stt = 'not_ok'
            
            live_now +=  "<div style='text-align: left; width:100%; margin: 0;' class='top_tool_bar'><h4 class='mb-0'>Station #"+station+"  "+ stt +"</h4></div>"
            live_now +=  "<div class='report_t'><a href=" + STATION_RPT_VDIR + "index.html><img src=" + files[0].replace("/mnt/archive.allsky.tv", "") + "></a></div>"
            data_per_station[station] = live_now 
            live_now = ''



   #for sd in status:
   # live_now += sd + " ******************************" + str(status[sd]) + "<BR>"
   live_now = ""
   for sd in status:
      if(sd in data_per_station):
         live_now += data_per_station[sd]
      else:
         live_now +=  "<div style='text-align: left; width:100%; margin: 0;' class='top_tool_bar'><h4 class='mb-0'>Station #"+station+"  DOWN</h4></div>"



   template = template.replace("{LIVE}", live_now+"</div>")

   # Cur Day
   template = template.replace("{DAY}",dom.replace('_','/')) 

   # nO cACHE
   template = template.replace("{RAND}",str(random.randint(0, 99999999)))

   fpo = open(LIVE_DIR + "index.html", "w")
   fpo.write(template)
   fpo.close()

def get_template(file):
   fp = open(file, "r")
   text = ""
   for line in fp:
      text += line
   return(text)

def build_all_stations():
   """ This function creates the master station index
   """
   all_stations_file = "../conf/all_stations.json"
   all_station_data = []
   lon_sat = []
   if cfe(all_stations_file) == 0:
      all_stations = []
      station_dirs = glob.glob("/mnt/archive.allsky.tv/AMS*")
      for sd in station_dirs:
         print("ST:", sd)
         station = sd.split("/")[-1]
         all_stations.append(station)
         data = {}
         data['station'] = station
         conf_file = "/mnt/archive.allsky.tv/" + station + "/CAL/as6.json"

         jsd = load_json_file(conf_file)
         if jsd == 0:
            print("CONF FILE MISSING:", conf_file)

         else:
            data['location'] = [float(jsd['site']['device_lat']), float(jsd['site']['device_lng']), float(jsd['site']['device_alt'])]
            all_station_data.append(data)

            lon_sat.append([station, jsd['site']['device_lng']])
   else:
      all_station_data = load_json_file(all_stations_file)

   temp = sorted(all_station_data, key=lambda x: x['location'][1], reverse=True)

   save_json_file(all_stations_file, temp)
   print(all_stations_file)



if sys.argv[1] == 'ulive':
   update_live_html()


