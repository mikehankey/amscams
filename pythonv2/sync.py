#!/usr/bin/python3
from urllib import request, parse
import requests
from datetime import datetime
import sys
#import datetime
import time
import glob
import os
import math
import cv2
import math
import numpy as np
import scipy.optimize
from fitMulti import minimize_poly_params_fwd
from lib.VideoLib import get_masks, find_hd_file_new, load_video_frames
from lib.UtilLib import check_running, get_sun_info, fix_json_file, find_angle, convert_filename_to_date_cam

from lib.FileIO import load_json_file, save_json_file, cfe

json_conf = load_json_file("../conf/as6.json")
my_station = json_conf['site']['ams_id']
cmd = sys.argv[1]
if len(sys.argv) == 3:
   day = sys.argv[2]

def create_update_events (day, json_conf ):
   sync_urls = load_json_file("../conf/sync_urls.json")
   all_meteor_index = {}
   day_meteor_index = {}
   all_meteor_index = {}
   for station in sync_urls['sync_urls']:
      all_meteor_index[station] = load_json_file("/mnt/ams2/stations/data/" + station + "_meteor_index.json")

   station_meteors = {}
   for station in all_meteor_index:
      station_meteors[station] = all_meteor_index[station][day]

   for station in station_meteors:
      for station_meteor in station_meteors[station]:
         print(station, station_meteor)

def sync_meteor_index(json_conf):
   print("Sync meteor index.")
   index = "/mnt/ams2/cal/hd_images/meteor_index.json"
   index_gz = "/mnt/ams2/cal/hd_images/meteor_index.json.gz"
   json_data = load_json_file(index)

   # The File to send
   file = index_gz
   _file = {'files': open(file, 'rb')}

   os.system("gzip -fk " + index )

   # The Data to send with the file
   api_key = "test"
   station_name = json_conf['site']['ams_id'].upper()
   device_name = "na"
   event_id = "na"
   file_type = "idx"
   meteor_day = "na"
   _data= {'api_key': api_key, 'meteor_day': meteor_day, 'station_name': station_name, 'device_name': device_name, 'format' : 'json', 'event_id' : event_id, 'file_type': file_type}
   url = 'http://54.214.104.131/pycgi/api-meteor-index.py'

   session = requests.Session()
   del session.headers['User-Agent']
   del session.headers['Accept-Encoding']

   with requests.Session() as session:
      response = session.post(url, data= _data, files=_file)

   print (response.text)
   response.raw.close()



def check_for_event(day, stations, meteor, all_meteors, mse):
   status = 0
   my_meteor_datetime, my_cam1, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(meteor)

   # first check if this meteor belongs to an existing event!
   for ev in mse:
      ev_meteor_datetime, my_cam1, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(ev)
      tdiff = abs((my_meteor_datetime-ev_meteor_datetime).total_seconds())
      if tdiff < 60:
         if my_station not in mse[ev]['obs']:
            mse[ev]['obs'][my_station] = {}
            mse[ev]['obs'][my_station]['sd_video_file'] = ev 
   

   for station in stations:
      print ("CHECKING MY METEOR AT STATION:", station)
      if day not in all_meteors[station]:
         print("no meteors for this day / station.", station, day)
         continue 
      for st_meteor in all_meteors[station][day]:
         #print(station, meteor, st_meteor)
         if st_meteor != meteor:
            st_meteor_datetime, my_cam1, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(st_meteor)
             
            tdiff = abs((my_meteor_datetime-st_meteor_datetime).total_seconds())
            # get date for each from filename
            # find time distance for each
            if tdiff < 5:
               print("MULTI-STATION MATCH:", meteor, st_meteor, tdiff)
               if meteor not in mse:
                  mse[meteor] = {}
                  mse[meteor]['obs'] = {}
               if station not in mse[meteor]['obs']:
                  print("ADD")
                  mse[meteor]['obs'][station] = {}
               mse[meteor]['obs'][station]['sd_video_file'] = st_meteor
               status = 1
             

   return(mse, status)
   # return the event ID and matching station files if success
   # do something to handle 2x,3x captures from multi-cams at same station.  These should not be considered 'events'.

   # else return 0

def sync_stations(json_conf):
   api_host = "http://54.214.104.131/" 
   sync_urls = load_json_file("../conf/sync_urls.json")
   print("SYNC STATIONS")
   my_station_id = json_conf['site']['ams_id'].upper()
   stations = {}
   for station in sync_urls['sync_urls']:
      stations[station] = {}
      lfn = "/mnt/ams2/stations/data/" + station + "_meteor_index.json.gz"
      mi_url = api_host + "/stations/" + station + "_meteor_index.json.gz" 
      print(mi_url)
      cmd = "wget \"" + mi_url + "\" -O " + lfn 
      print(cmd)
      os.system(cmd)
      os.system("gunzip " + lfn)


   

def find_events_for_day(day,json_conf):
   print("FIND EVENTS FOR : ", day)
   my_station_id = json_conf['site']['ams_id'].upper()
   sync_urls = load_json_file("../conf/sync_urls.json")
   all_meteors = {}
   stations = {}
   all_meteors[my_station_id] = load_json_file("/mnt/ams2/cal/hd_images/meteor_index.json")
   for station in sync_urls['sync_urls']:
      all_meteors[station] = load_json_file("/mnt/ams2/stations/" + station + "/meteor_index.json")
      stations[station] = {}
   if day not in all_meteors[my_station_id]:
      print("There are no meteors for this day!")
      exit()
   my_meteors = all_meteors[my_station_id][day]
   mse = {}
   for meteor in my_meteors:
      print(meteor)
      red_meteor = meteor.replace(".json", "-reduced.json")
      if cfe(red_meteor) == 1:
         mse, status = check_for_event(day, stations, meteor, all_meteors, mse)
         if status == 1:
            print("SAVE THE EVENT INFO TO THE REDUCED FILE!")
            meteor_red = meteor.replace(".json", "-reduced.json")
            print("METEOR RED FILE:", meteor_red)
            red_data = load_json_file(meteor_red)
            red_data['multi_station'] = {}
            red_data['multi_station'] = mse[meteor]
            print(mse[meteor])
            save_json_file(meteor_red, red_data)
            print("SAVED:", meteor_red)

   print("SAVED: /mnt/ams2/stations/data/" + day + "-multi_station_data.json")
   save_json_file("/mnt/ams2/stations/data/" + day + "-multi_station_data.json", mse)

   sync_ms_json(day, mse, sync_urls)
   solve_events(day, mse, sync_urls)

def sync_ms_json(day, mse, sync_urls):
   for my_meteor in mse:
      print("Need to sync content for my meteor: ", my_meteor)
      for station in mse[my_meteor]['obs']: 
         if station != my_station:
            url = sync_urls['sync_urls'][station]
            st_video_url = mse[my_meteor]['obs'][station]['sd_video_file']
            fn = st_video_url.split("/")[-1]
            fn = fn.replace(".json", "-reduced.json") 
            st_video_url  = st_video_url.replace(".json", "-reduced.json") 
            lfdd = "/mnt/ams2/stations/" + station + "/" + day
            if cfe(lfdd, 1) == 0:
               os.system("mkdir " + lfdd)
            lfn  = "/mnt/ams2/stations/" + station + "/" + day + "/" + fn
            #if cfe(lfn) == 0:
            if True:
               sync_url = url + st_video_url
               print("NEED TO SYNC URL:", sync_url)
               cmd = "wget \"" + sync_url + "\" -O " + lfn 
               os.system(cmd)
            else: 
               print("Already have:", url + st_video_url)
  
def solve_events(day, mse,sync_urls):
   evs = []
   jobs = []
   for my_meteor in mse:
      tob = []
      my_red_meteor = my_meteor.replace(".json", "-reduced.json") 
      tob.append(my_red_meteor)
      for station in mse[my_meteor]['obs']: 
         red_file = mse[my_meteor]['obs'][station]['sd_video_file'].replace(".json", "-reduced.json")
         red_file = red_file.replace("/meteors/", "/stations/" + station + "/")
         tob.append(red_file)
      evs.append(tob)
         

   for ev in evs:
      arglist = ""
      for ob in ev:
         arglist = arglist + ob + " "
      cmd = "cd /home/ams/dvida/WesternMeteorPyLib/wmpl/Trajectory; python mikeTrajectory.py " + arglist
      jobs.append(cmd)

   for job in jobs:
      print(job)
   #os.system(cmd)

    
if cmd == "ss":
   sync_stations( json_conf)
         
if cmd == "smi":
   sync_meteor_index( json_conf)

if cmd == "find_events" or cmd == 'fe':
   find_events_for_day(day, json_conf)
if cmd == "cue" :
   create_update_events(day, json_conf)
