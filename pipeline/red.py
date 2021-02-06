#!/usr/bin/python3

from lib.PipeUtil import load_json_file,save_json_file, cfe
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


   # GET ALL NETWORK EVENTS FOR THE DAY
   dc_file = dyn_cache + date + "_events.json"
   if cfe(dc_file) == 1:
      size, tdiff = get_file_info(dc_file)
      hours_old = tdiff / 60
      if hours_old < 4:
         print("USING EVENT DYCACHE:", dc_file)
         use_cache = 1
         events = load_json_file(dc_file)


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
   

def load_meteor_index(r ):
   json_conf = load_json_file("../conf/as6.json")
   amsid = json_conf['site']['ams_id']
   index_file = "/mnt/ams2/meteors/" + amsid + "-meteors.info"
   index = load_json_file(index_file)
   for row in index:
      if len(row) == 8:
         (meteor, reduced, start_time, dur, ang_vel, ang_dist, hotspot,msm) = row
      else:
         (meteor, reduced, start_time, dur, ang_vel, ang_dist, hotspot) = row
         msm = 0

      mfn,dd = fn_dir(meteor)
      key = "mi:" + mfn
      val = str([reduced,start_time,dur,ang_vel,ang_dist,hotspot,msm])
      r.mset({key: val})
      print("setting.", meteor, start_time)


if __name__ == "__main__":
   cmd = sys.argv[1]
   if cmd == "refresh_day" or cmd == "rd":
      refresh_day(sys.argv[2])
