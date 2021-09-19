#!/usr/bin/python3

# load all stations, all profiles, all obs and all events into text file backups!

""" 
   OCCASSIONALLY
   This script should be run to do a full backup of the dynamodb and push it into 
   json files for each stations and other groupings
"""

import os
import gc
import sys
from decimal import Decimal
import simplejson as json
import boto3
from boto3.dynamodb.conditions import Key
import datetime
import redis
from lib.PipeUtil import save_json_file, load_json_file, cfe,  convert_filename_to_date_cam, get_trim_num

r = redis.Redis("allsky-redis.d2eqrc.0001.use1.cache.amazonaws.com", port=6379, decode_responses=True)
dynamodb = boto3.resource('dynamodb')
from decimal import Decimal

def dump_events(dynamodb):
   ####
   #
   # GET EVENTS
   #
   ###
   input("Are you sure you want to dump all events? [CNTL-C] to quit or [ENTER] to continue.")
   dump_file = "dumps/x_meteor_event.txt"
   out = open(dump_file, "w")

   all_obs_events = {}
   bad_events = []
   table = dynamodb.Table('x_meteor_event')
   response = table.scan()
   data = response['Items']
   ic = 0

   for item in response['Items']:
      out.write(json.dumps(item) + "\n")
      ic += 1
      if "stations" not in item:
         print("NO STATIONS IN ITEM:", item.keys())
         bad_events.append(item['event_id'])
         continue
      for i in range(0, len(item['stations'])):
         st = item['stations'][i]
         sd_vid = item['files'][i]
         ev_id = item['event_id']
         obs_key = st + "_" + sd_vid
         if "solve_status" in item:
            obs_val = item['event_id'] + ":" + item['solve_status']
         else:
            obs_val = item['event_id'] + ":UNSOLVED"
         all_obs_events[obs_key] = obs_val


   while 'LastEvaluatedKey' in response:
      print("DUMPING EVENTS!", ic, response['LastEvaluatedKey'])
      response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
      for item in response['Items']:
         out.write(json.dumps(item) + "\n")
         ic += 1
         if "stations" not in item:
            print("NO STATIONS IN ITEM:", item.keys())
            bad_events.append(item['event_id'])
            continue
         for i in range(0, len(item['stations'])):
            st = item['stations'][i]
            sd_vid = item['files'][i]
            ev_id = item['event_id']
            obs_key = st + "_" + sd_vid
            if "solve_status" in item:
               obs_val = item['event_id'] + ":" + item['solve_status']
            else:
               obs_val = item['event_id'] + ":UNSOLVED"
            all_obs_events[obs_key] = obs_val


   print("SAVING dumps/bad_event_ids.json")
   save_json_file("dumps/bad_event_ids.json", bad_events)
   print("SAVING dumps/all_obs_events.json")
   save_json_file("dumps/all_obs_events.json", all_obs_events)

def index_all_obs_events():
   all_obs_events = load_json_file("dumps/all_obs_events.json")
   by_station = {}
   ic = 0
   for key in all_obs_events:
      el = key.split("_")
      st = el[0]
      nkey = key.replace(st + "_", "")
      nkey = nkey.replace(".mp4", "")
      if st not in by_station:
         by_station[st] = {}
      by_station[st][nkey] = all_obs_events[key] 
      if ic % 1000 == 0:
         print("Processed:", ic)
      ic += 1

   out_dir = "/mnt/ams2/EVENTS/OBS/STATIONS/"
   for key in by_station:
      out_file = out_dir + key + "_EVENTS.json"
      save_json_file(out_file, by_station[key], True)

      print(out_file, key, len(by_station[key].keys()))
   os.system("cp /mnt/ams2/EVENTS/OBS/STATIONS/*EVENTS.json /mnt/archive.allsky.tv/EVENTS/OBS/STATIONS/")

def make_all_obs_events():
   fp = open("dumps/x_meteor_event.txt")
   all_obs_events = {}
   ic = 1
   for line in fp:
      item = json.loads(line, parse_float=Decimal)
      if True:
         if "stations" not in item:
            continue
         for i in range(0, len(item['stations'])):
            st = item['stations'][i]
            sd_vid = item['files'][i]
            ev_id = item['event_id']
            obs_key = st + "_" + sd_vid
            if "solve_status" in item:
               obs_val = item['event_id'] + ":" + item['solve_status']
            else:
               obs_val = item['event_id'] + ":UNSOLVED"
            all_obs_events[obs_key] = obs_val
      ic += 1
      if ic % 1000 == 0:
         print(ic)
   print("SAVING dumps/all_obs_events.json")
   save_json_file("dumps/all_obs_events.json", all_obs_events)



#dump_events(dynamodb)
#make_all_obs_events()
index_all_obs_events()
