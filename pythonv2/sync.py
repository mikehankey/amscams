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


def id_event(meteor_events, station_name, meteor_file, event_start_time) :

   total_events = len(meteor_events)
   this_meteor_datetime, this_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(meteor_file)
   device_name = this_cam
   if total_events == 0:
      event_id = 1
      meteor_events[event_id] = {}
      meteor_events[event_id]['start_time'] = event_start_time
      meteor_events[event_id]['observations'] = {}
      meteor_events[event_id]['observations'][station_name]  = {}
      meteor_events[event_id]['observations'][station_name][device_name] = meteor_file
      return(meteor_events)

   for ekey in meteor_events:
      this_start_time = meteor_events[ekey]['start_time']
      evst_datetime = datetime.strptime(event_start_time, "%Y-%m-%d %H:%M:%S.%f")
      this_datetime = datetime.strptime(this_start_time, "%Y-%m-%d %H:%M:%S.%f")
      tdiff = (evst_datetime-this_datetime).total_seconds()
      if abs(tdiff) < 5:
         print("second capture of same event")
         if station_name not in meteor_events[ekey]['observations']:
            meteor_events[ekey]['observations'][station_name] = {}
         meteor_events[ekey]['observations'][station_name][device_name] = meteor_file 


         return(meteor_events)

   # no matches found so make new event
   event_id = total_events + 1
   print("new event:", event_id)
   meteor_events[event_id] = {}
   meteor_events[event_id]['start_time'] = event_start_time
   meteor_events[event_id]['observations'] = {}
   meteor_events[event_id]['observations'][station_name]  = {}
   meteor_events[event_id]['observations'][station_name][device_name] = meteor_file 

   return(meteor_events)



def create_update_events (day, json_conf ):
   meteor_events = {}
   my_station = json_conf['site']['ams_id'].upper()
   multi_station_events = {}
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
         if "event_start_time" in station_meteors[station][station_meteor]:
            meteor_events = id_event(meteor_events, station, station_meteor, station_meteors[station][station_meteor]['event_start_time'])
         else:
            print("METEOR NOT REDUCED!")

   msc = 1
   for meteor_event in meteor_events:
      if len(meteor_events[meteor_event]['observations']) > 1:
         print (msc, len(meteor_events[meteor_event]['observations']), meteor_events[meteor_event])
         multi_station_events[meteor_event] = meteor_events[meteor_event]
         msc = msc + 1

   print("MULTI-STATION METEORS")
   print("---------------------")
   msc = 1
   new_ms_events = {}
   for meteor_event in multi_station_events:
      lats = [] 
      lons = [] 
      if len(meteor_events[meteor_event]['observations']) > 1:
         print (msc, len(meteor_events[meteor_event]['observations']), meteor_events[meteor_event]['start_time'])
         multi_station_events[meteor_event] = meteor_events[meteor_event]
         msc = msc + 1
         for obs in multi_station_events[meteor_event]['observations']:
            print("OBS:", obs, sync_urls['sync_urls'][obs]['device_lat'], sync_urls['sync_urls'][obs]['device_lng'], sync_urls['sync_urls'][obs]['device_alt'])


            lats.append(abs(float(sync_urls['sync_urls'][obs]['device_lat'])))
            lons.append(abs(float(sync_urls['sync_urls'][obs]['device_lng'])))
         mlat = abs(np.mean(lats))
         mlon = abs(np.mean(lons))
         multi_station_events[meteor_event]['obs_mean_lat'] = abs(mlat)
         multi_station_events[meteor_event]['obs_mean_lon'] = abs(mlon)
         print("Mean lat/lon for event:", mlat, mlon)
         temp =  multi_station_events[meteor_event]['start_time'].replace(" ", "")
         ams_meteor_event_id,trash = temp.split(".")

         ams_meteor_event_id =  ams_meteor_event_id.replace(":", "")
         ams_meteor_event_id =  ams_meteor_event_id.replace("-", "")
         ams_meteor_event_id =  ams_meteor_event_id + "_" + str(int(mlat)) + "_" + str(int(mlon))
         print("AMS METEOR EVENT ID:", ams_meteor_event_id)
         multi_station_events[meteor_event]['ams_meteor_event_id'] = ams_meteor_event_id

         for obs in multi_station_events[meteor_event]['observations']:
            if obs == my_station:
               print("UPDATE RED FILE WITH ID", multi_station_events[meteor_event]['observations'][my_station])
               for tcam_id in multi_station_events[meteor_event]['observations'][my_station]:
                  red_file = multi_station_events[meteor_event]['observations'][my_station][tcam_id]
                  print("RED FILE:", red_file, multi_station_events[meteor_event])
                  red_file = red_file.replace(".json", "-reduced.json")
                  red_data = load_json_file(red_file)
                  red_data['event_info'] = multi_station_events[meteor_event]
                  red_data['sync_status'] = 0
                  save_json_file(red_file, red_data)
         new_ms_events[ams_meteor_event_id] = multi_station_events[meteor_event] = meteor_events[meteor_event]
         event_files = check_make_event(ams_meteor_event_id, json_conf)
         cloud_files = []
         for ef in event_files:
            fn = ef.split("/")[-1]
            cloud_files.append(fn)
         print("SYNC CONTENT")

         my_meteor_datetime, my_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(red_file)
         new_file = ams_meteor_event_id + "_" + my_station + "_" + my_cam + ".json"
         print("NF:", new_file)
         if new_file in cloud_files:
            print(new_file, "already exists in the cloud")
         else:
            sync_content(ams_meteor_event_id, my_station, red_file, ".json")

         hd_video_file = red_data['hd_video_file']
         hd_stack = red_data['hd_stack'].replace(".png", "-stacked.png")
         sd_stack = red_data['sd_stack'].replace(".png", "-stacked.png")

         video_file = red_file.replace("-reduced.json", ".mp4")

         new_file = ams_meteor_event_id + "_" + my_station + "_" + my_cam + ".mp4"
         if new_file in cloud_files:
            print(new_file, "already exists in the cloud")
         else:
            sync_content(ams_meteor_event_id, my_station, video_file, ".mp4")

         new_file = ams_meteor_event_id + "_" + my_station + "_" + my_cam + "-HD.mp4"
         if new_file in cloud_files:
            print(new_file, "already exists in the cloud")
         else:
            print(new_file, "disabled HD sync for now")
            #sync_content(ams_meteor_event_id, my_station, hd_video_file, "-HD.mp4")

         new_file = ams_meteor_event_id + "_" + my_station + "_" + my_cam + "-HD-stacked.png"

         if new_file in cloud_files:
            print(new_file, "already exists in the cloud")
         else:
            print("STACK ", new_file, hd_stack)
            if "stacked-stacked" in hd_stack:
               hd_stack = hd_stack.replace("-stacked", "")
            if "stacked" not in hd_stack:
               hd_stack = hd_stack.replace(".png", "-stacked.png")

            sync_content(ams_meteor_event_id, my_station, hd_stack, "-HD-stacked.png")

         new_file = ams_meteor_event_id + "_" + my_station + "_" + my_cam + "-stacked.png"
         if new_file in cloud_files:
            print(new_file, "already exists in the cloud")
         else:
            if "stacked-stacked" in sd_stack:
               sd_stack = hd_stack.replace("-stacked", "")
            sync_content(ams_meteor_event_id, my_station, sd_stack, "-stacked.png")



  
   save_json_file("/mnt/ams2/stations/data/" + day + "_events.json", new_ms_events)
   print("SAVED /mnt/ams2/stations/data/" + day + "_events.json")

def sync_content(event_id, station_name, upload_file, file_type):
   if cfe(upload_file) == 0:
      print("FAILED UPLOAD: file doesn't exist so can't upload it!", upload_file)
      return(0)
   my_meteor_datetime, my_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(upload_file)
   url = "http://54.214.104.131/pycgi/api-sync-content.py"
   # The File to send
   file = upload_file 
   _file = {'files': open(file, 'rb')}


   # The Data to send with the file
   api_key = "test"
   _data= {'api_key': api_key, 'station_name': station_name, 'device_name': my_cam, 'event_id' : event_id, 'file_type': file_type}

   print(url, _data)
   session = requests.Session()
   del session.headers['User-Agent']
   del session.headers['Accept-Encoding']

   with requests.Session() as session:
       response = session.post(url, data= _data, files=_file)

 
   print (response.text)
   response.raw.close()



def check_make_event(event_id, json_conf):
   file = "test.txt"
   _file = {'files': open(file, 'rb')}

   # os.system("gzip -fk " + index )

   # The Data to send with the file
   api_key = "test"
   station_name = json_conf['site']['ams_id'].upper()
   device_name = "na"
   file_type = "idx"
   meteor_day = "na"
   _data= {'api_key': api_key, 'station_name': station_name, 'event_id' : event_id }
   url = 'http://54.214.104.131/pycgi/api-make-check-event.py'
   print(url, _data)
   session = requests.Session()
   del session.headers['User-Agent']
   del session.headers['Accept-Encoding']

   with requests.Session() as session:
      response = session.post(url, data= _data, files=_file)
      #response = session.post(url, data= _data )

   resp = response.text
   files = resp.split("\n")
   response.raw.close()
   return(files)


 

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
      os.system("gunzip -f " + lfn)


   

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
  
def solve_events(day, json_conf):
   remote_host = "http://54.214.104.131/"
   my_station = json_conf['site']['ams_id']
   event_file = "/mnt/ams2/stations/data/" + day  + "_events.json"
   events = load_json_file(event_file)
   jobs = []
   for event in events:
      print(event )
      run_files = []
      for station in events[event]['observations']:
         print(station)
         if station != my_station:
            for cam_id in events[event]['observations'][station]:
               local_dir =  "/mnt/ams2/events/" + event 
               if cfe(local_dir,1) == 0:
                  cmd = "mkdir " + local_dir
                  os.system(cmd)
               local_file = local_dir + "/" + event + "_" + station + "_" + cam_id + ".json" 
               remote_url = remote_host + "/meteors/" + event + "/" + event + "_" + station + "_" + cam_id + ".json" 
               remote_url = remote_url.replace("/mnt/ams2", "")
               run_files.append(local_file)
               print(station, cam_id, remote_url, local_file)
               #if cfe(local_file) == 0:
               if True:
                  cmd = "wget \"" + remote_url + "\" -O " + local_file 
                  print(cmd)
                  os.system(cmd)
         else:
            for cam_id in events[event]['observations'][station]:
               print(cam_id, events[event]['observations'][station])
               run_files.append(events[event]['observations'][station][cam_id])
         arglist = ""
      for ob in run_files:
         arglist = arglist + ob + " "
      cmd = "cd /home/ams/dvida/WesternMeteorPyLib/wmpl/Trajectory; python mikeTrajectory.py " + arglist
      jobs.append(cmd)

   print("JOBS:")
   if 'max_procs' in json_conf['site']:
      max_procs = json_conf['site']['max_procs']
   else:
      max_procs = 4

   jc = 0
   job_name = "mikeTrajectory.py"
   for job in jobs:
      while check_running(job_name) > max_procs:
         time.sleep(1)
      print(job)
      #if "010002" in job:
      #os.system(job + " &")
      jc = jc + 1


    
if cmd == "ss":
   sync_stations( json_conf)
         
if cmd == "smi":
   sync_meteor_index( json_conf)

if cmd == "find_events" or cmd == 'fe':
   find_events_for_day(day, json_conf)
if cmd == "cue" :
   create_update_events(day, json_conf)
if cmd == "se" :
   solve_events(day, json_conf)
