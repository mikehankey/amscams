#!/usr/bin/python3
import keydb
import json
import os
# functions for loading data in and out of redis
import datetime
from lib.PipeUtil import load_json_file,save_json_file, cfe, convert_filename_to_date_cam
from lib.PipeDetect import get_trim_num
from lib.PipeAutoCal import fn_dir 
import redis
r = redis.Redis(decode_responses=True)

import boto3
import socket
import subprocess
from boto3.dynamodb.conditions import Key
from lib.PipeUtil import get_file_info
import sys


def refresh_day(date, dynamodb=None, use_cache=0):
   """ download fresh DYNA data for 1 day and load it into redis
      meteor(obs)
      obs: OBS:AMSXX:SD_VIDEO_FILE = "[meteor start_time, station, duration, revision, cat_star_total, res_error, azs, els]
      event: EV:EVENT_ID = "[event start_time, stations, duration, revision, solve_status, vinit, vavg, start ele, end ele, a, e, i,shower ]

   """
   json_conf = load_json_file("../conf/as6.json")
   stations = json_conf['site']['multi_station_sync']
   amsid = json_conf['site']['ams_id']
   if amsid not in stations:
      stations.append(amsid)
      stations = sorted(stations)
   if dynamodb is None:
      dynamodb = boto3.resource('dynamodb')

   print("Refresh day:", date)
   # Get DYNA events for this day:

   dyn_cache = "/mnt/ams2/DYCACHE/"

   if cfe(dyn_cache, 1) == 0:
      os.makedirs(dyn_cache)



   if use_cache == 0:
      print("NO CACHE: query table: x_meteor_event")
      table = dynamodb.Table('x_meteor_event')
      response = table.query(
         KeyConditionExpression='event_day= :date',
         ExpressionAttributeValues={
           ':date': date,
         }
      )
      events = response['Items']

   for ev in events:
      print(ev['event_id'])
      # HERE WE SHOULD UPDATE "OUR" METEOR.JSON FILES WITH THE MSE INFO
      print(ev['stations'])
      print(ev['files'])
      print(ev['start_datetime'])
      for key in ev:
         print("     " + key)
   
   # GET OBS FROM DYNA FOR ALL METEORS IN MY NETWORK
   for station_id in stations:
 
      obs = get_dyna_obs (dynamodb, station_id, date, force_update=0)
      print("OBS:", station_id, len(obs))

def get_dyna_obs (dynamodb, station_id, date, force_update=0):

   use_cache = 0
   dyn_cache = "/mnt/ams2/DYCACHE/"
   if cfe(dyn_cache, 1) == 0:
      os.makedirs(dyn_cache)
   dc_file = dyn_cache + date + "_" + station_id + "_obs.json"
   if cfe(dc_file) == 1:
      size, tdiff = get_file_info(dc_file)
      hours_old = tdiff / 60
      if hours_old < 4:
         use_cache = 1
   if use_cache == 0 or force_update==1:
      print("NO CACHE: query table: meteor_obs")
      if dynamodb is None:
         dynamodb = boto3.resource('dynamodb')

      table = dynamodb.Table('meteor_obs')
      response = table.query(
         KeyConditionExpression='station_id = :station_id AND begins_with(sd_video_file, :date)',
         ExpressionAttributeValues={
            ':station_id': station_id,
            ':date': date,
         }
      )
      save_json_file(dc_file, response['Items'])
      return(response['Items'])
   else:
      return(load_json_file(dc_file))
   
def load_meteor_index_all(r):
   cmd = "find /mnt/ams2/meteors |grep .json |grep -v reduced |grep -v star |grep -v manual |grep -v error |grep -v cloud_files |grep -v final |grep -v report | grep -v mi_day | grep -v events |grep -v frame |grep -v cal | grep -v test | grep -v mi_day | grep -v HD > /mnt/ams2/all_meteors.txt"
   #os.system(cmd)
   fp = open("/mnt/ams2/all_meteors.txt")
   meteor_db = []
   meteors = []
   for line in fp:
      line = line.replace("\n", "")
      meteor_file = line
      meteors.append(line)
   for meteor_file in sorted(meteors):
      data = {}
      meteor_root = meteor_file.replace(".json", "")
      meteor_key = meteor_root.split("/")[-1]
      data['sd'] = meteor_key + ".mp4" 
      mj = load_json_file(meteor_file)

      # base datetime of the minute clip that captured the event
      (f_datetime, cam, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(meteor_file)
      trim_num = int(get_trim_num(meteor_file))
      # add extra seconds for trim start 
      extra_sec = int(trim_num) / 25
      print("EXT:", trim_num , extra_sec)
      start_time_dt = f_datetime + datetime.timedelta(0,extra_sec)

      start_time = start_time_dt.strftime('%Y-%m-%d %H:%M:%S')

      data['tme'] = start_time

      if "hd_trim" in mj:
         if mj['hd_trim'] is not None and mj['hd_trim'] != 0:
            hd_fn = mj['hd_trim'].split("/")[-1]
            data['hd'] = hd_fn
         #else:
            #print("NO HD:")
            #for key in mj:
            #   print(key, mj[key])
            #xxx = input("Enter to continue.")
      #else:
         #print("NO HD:")
         #for key in mj:
         #   print(key, mj[key])
         #xxx = input("Enter to continue.")
      if "final_vid" in mj:
         fv_fn = mj['final_vid'].split("/")[-1]
         data['fv'] = fv_fn
      if "multi_station_event" in mj:
         if "total_stations" in mj['multi_station_event']:
            if mj['multi_station_event']['total_stations'] >= 2:
               data['ms'] = 1
      if "best_meteor" not in mj:
         # meteor has not been reduced
         data['rd'] = 0
      else:
         data['rd'] = 1
         data['dur'] = len(mj['best_meteor']['ofns']) / 25
         if "dts" in mj['best_meteor']:
            data['tme'] = mj['best_meteor']['dts'][0] 
         if "report" in mj['best_meteor']:
            if "ang_vel" in mj['best_meteor']['report']:
               data['av'] = mj['best_meteor']['report']['ang_vel']
                
      if "cp" in mj:
         if mj['cp'] is not None:
            if "total_res_px" in mj['cp']:
               data['res'] = mj['cp']['total_res_px']
            if "cat_image_stars" in mj['cp']:
               data['st'] = len(mj['cp']['cat_image_stars'])
      
      print(meteor_key, data)
      meteor_db.append(data)
      #exit()
   save_json_file("/mnt/ams2/all_meteors.json", meteor_db)
   print("Saved: /mnt/ams2/all_meteors.json" )

def test(r):
   load = 1
   scan = 0
   if load == 1:
      am = load_json_file("/mnt/ams2/all_meteors.json")
      am = sorted(am, key=lambda x: x['tme'], reverse=False)
      for data in am:
         key = "OB:" + data['sd']
         del data['sd']
         jdata = json.dumps(data)
         val = str(jdata)
         r.mset({key: val})
      print("Loaded redis.")
      exit()

   # SCAN!
   if scan == 1:
      result = []
      count =10
      pattern = ""
      data = r.scan_iter(match="OB:*" )
      for x in data:
         print(x)
   exit()
   start_date = "2021-01-01"
   end_date = "2021-12-31"
   start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d")
   end_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d")

   # show top 100 most recent meteors
   am = sorted(am, key=lambda x: x['tme'], reverse=True)
   for data in am:
      if "." in data['tme']:
         event_datetime = datetime.datetime.strptime(data['tme'], "%Y-%m-%d %H:%M:%S.%f")
      else:
         event_datetime = datetime.datetime.strptime(data['tme'], "%Y-%m-%d %H:%M:%S")
      if start_dt <= event_datetime <= end_dt:
         print(data)

def load_meteor_index(day, r ):
   json_conf = load_json_file("../conf/as6.json")
   amsid = json_conf['site']['ams_id']
   index_file = "/mnt/ams2/meteors/" + day + "/" + day + "-" + amsid + ".meteors"
   index = load_json_file(index_file)
   for row in index:
      if len(row) == 8:
         (meteor, reduced, start_time, dur, ang_vel, ang_dist, hotspot,msm) = row
      else:
         (meteor, reduced, start_time, dur, ang_vel, ang_dist, hotspot) = row
         msm = 0

      mfn,dd = fn_dir(meteor)
      key = "OBS:" + mfn
      val = str([reduced,start_time,dur,ang_vel,ang_dist,hotspot,msm])
      r.mset({key: val})
      print("setting.", mfn, val)



def get_meteor_index(day, r):
   print("hi")

if __name__ == "__main__":
   cmd = sys.argv[1]
   if cmd == "refresh_day" or cmd == "rd":
      refresh_day(sys.argv[2])
   if cmd == "meteor_index" or cmd == 'mi':
      load_meteor_index(sys.argv[2], r)
   if cmd == "meteor_index_all" or cmd == 'mia':
      load_meteor_index_all(r)
   if cmd == "test":
      test(r)
