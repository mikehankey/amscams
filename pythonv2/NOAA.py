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

def get_latest_file(cam_id):
   files = glob.glob("/mnt/ams2/SD/*" + cam_id + "*.mp4")
   files = sorted(files, reverse=True)
   fc = 0
   for file in files:
      st = os.stat(file)
      size = st.st_size
      if size > 1000 and fc > 0:
         return(file)
      fc += 1


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

def update_live_html():
   """ This function will only be runby a manager's node. 
       The purpose is to update the HTML and json indexes for the live view
   """

   header_html, footer_html = html_header_footer() 
 
   now = datetime. now()
   day = now.strftime("%m_%d")
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
      NOAA_DIR =  "/mnt/archive.allsky.tv/" + station + "/NOAA/ARCHIVE/" + year + "/" + day + "/" 
      if cfe(NOAA_DIR, 1) == 0:
        
         os.makedirs(NOAA_DIR)
      day_index = NOAA_DIR + day + "_index.json"
      if cfe(day_index) == 0 or True:
         live_files = glob.glob(NOAA_DIR + "*.jpg")
         for file in live_files:
            print("ADDING FILES FOR : ", station, file)
            data['files'].append(file)
            status[station] = 1 
      all_station_data.append(data)

        #<meta http-equiv="Cache-Control" content="no-cache"/>
   live_now = """
     <head>
        <meta http-equiv="Cache-control" content="public, max-age=500, must-revalidate">
     </head>
   """ 
   for data in all_station_data:
      station = data['station']
      files = sorted(data['files'], reverse=True)
      data['files'] = files
      if len(files) > 0:
         fn = files[0].split("/")[-1]
         file_index = files[0].replace(fn, "")
         file_index = file_index.replace("/mnt/archive.allsky.tv", "")
         live_now +=  "<a href=" + file_index + "index.html><img src=" + files[0].replace("/mnt/archive.allsky.tv", "") + "></a><BR>\n"
    
      NOAA_DIR =  "/mnt/archive.allsky.tv/" + station + "/NOAA/ARCHIVE/" + year + "/" + day + "/" 
      day_index = NOAA_DIR + day + "_index.json"
      html_index = NOAA_DIR + "index.html"
      print(day_index)
      save_json_file(day_index, data)
      html = """
         <head>
            <meta http-equiv="Cache-control" content="public, max-age=500, must-revalidate">
         </head>
      """

   live_now += "<h2>Station Status</h2>\n"
   for sd in status:
      live_now += sd + " " + str(status[sd]) + "<BR>"
   fpo = open(html_index, "w")
   fpo.write(html)
   fpo.close() 
   print(html_index)

   MAIN_NOAA_DIR = "/mnt/archive.allsky.tv/LIVE/" + year + "/" 
   asd_file = "/mnt/archive.allsky.tv/LIVE/" + year + "/" + day + "_index.json"
   asd_html = "/mnt/archive.allsky.tv/LIVE/" + "index.html"
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
      latest_file = get_latest_file(cams_id)
      url = "rtsp://" + ip + sd_url
      outfile = MY_NOAA_DIR + time_file + "_" + cams_id + ".jpg"
      if latest_file is not None:
         tmp_list.append(outfile)

         cmd = "/usr/bin/ffmpeg -y -i '" + latest_file +  "' -vframes 1 -vf scale=320:180 " + outfile 
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

   # copy file to arhive.allsky.tv dir
   was_dir = MY_NOAA_DIR.replace("ams2/meteor_archive", "archive.allsky.tv")
   was_out = out_allout.replace("ams2/meteor_archive", "archive.allsky.tv")
   if cfe(was_dir, 1) == 0:
      os.makedirs(was_dir)
   os.system("cp " + out_allout + " " + was_out  )
   print(was_out)

def html_get_detects(day,tsid):
   year = day[0:4]
   prev_file = "/mnt/archive.allsky.tv/" + tsid + "/DETECTS/PREVIEW/" + year + "/" + day + "/" + "index.html"
   print("PREV FILE:", prev_file)
   html = ""
   if cfe(prev_file) == 1:
      fp = open(prev_file, "r")
      for line in fp:
         html += line
   return(html)
   

def html_header_footer(info=None):
   js = javascript()
   html_header = """
     <head>
        <meta http-equiv="Cache-control" content="public, max-age=500, must-revalidate">
   """
   html_header += js + """
     </head>
   """

   html_footer = """

   """
   return(html_header, html_footer)

def javascript():
   js = """
      <script>
      function showHideDiv(myDIV) {
         var x = document.getElementById(myDIV);
         if (x.style.display === "none") {
            x.style.display = "block";
         } else {
            x.style.display = "none";
         }
      }

      </script>
   """
   return(js)

os.system("./wasabi.py mnt")

if len(sys.argv) <= 1:
   update_live_view()
else:
   if sys.argv[1] == 'update_live_html' or sys.argv[1] == 'ulh':
      update_live_html()
