#!/usr/bin/python3
# load all stations, all profiles, all obs and all events into text file backups!

""" 
   OCCASSIONALLY
   This script should be run to do a full backup of the dynamodb and push it into 
   json files for each stations and other groupings
"""

import numpy as np
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

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return json.JSONEncoder.default(self, obj)

r = redis.Redis("allsky-redis.d2eqrc.0001.use1.cache.amazonaws.com", port=6379, decode_responses=True)
dynamodb = boto3.resource('dynamodb')
from decimal import Decimal

def minimize_item(item):
   new_item = {}
   new_ar = []
   new_item['ob'] = item['ob']
   new_item['es'] = item['es']
   new_item['ei'] = item['event_id']
   new_item['ss'] = item['solve_status']
   new_item['sh'] = item['shower']
   new_item['rd'] = item['solution']['rad']
   traj = item['solution']['traj']
   orb = item['solution']['orb']
   new_traj = [item['solution']['duration'],round(traj['v_init'],2),round(traj['v_avg'],2),round(traj['start_lat'],4),round(traj['start_lon'],4),round(traj['start_ele'],2),round(traj['end_lat'],4),round(traj['end_lon'],4),round(traj['end_ele'],2)]

   new_item['tj'] = new_traj
   #new_orb = [['mean_anomaly', 'jd_ref', 'a', 'true_anomaly', 'e', 'link', 'i', 'la_sun', 'node', 'q', 'Q', 'T', 'peri', 'eccentric_anomaly', 'pi']
   for key in orb:
      if orb[key] is None:
         orb[key] = 0
   new_orb = [orb['jd_ref'],round(orb['a'],2),round(orb['i'],2),round(orb['e'],2),round(orb['q'],2),round(orb['Q'],2),round(orb['peri'],2),round(orb['node'],2),round(orb['la_sun'],2),round(orb['T'],2),round(orb['true_anomaly'],2),round(orb['mean_anomaly'],2),round(orb['eccentric_anomaly'],2), round(orb['pi'],2)]
   new_item['or'] = new_orb
   if orb['e'] > .95 or orb['a'] < 0:
      new_item['bo'] = 1
   else:
      new_item['bo'] = 0
   new_ar = [new_item['ob'],new_item['es'],new_item['ei'],new_item['ss'],new_item['sh'],new_item['rd'],new_item['tj'],new_item['or'],new_item['bo']]

           
   return(new_ar)

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
   #"2021_10_02_07_12_00_000_010002-trim-1363.mp4:20211002_071256:SUCCESS"
   by_station = {}
   for key in all_obs_events:
      el = key.split("_")
      st = el[0]
      vid = key.replace(st + "_", "")
      event_id, event_status = all_obs_events[key].split(":")
      if st not in by_station:
         by_station[st] = {}
         by_station[st]['events'] = []

      new_val = vid + ":" + event_id + ":" + event_status
      by_station[st]['events'].append(new_val)
   save_json_file("dumps/all_station_events.json", by_station)
   print("dumps/all_station_events.json")
   for station_id in by_station:
      print("saving:", station_id)
      print("/mnt/ams2/EVENTS/STATIONS/ALL_EVENTS_" + station_id + ".json")
      save_json_file("/mnt/ams2/EVENTS/STATIONS/ALL_EVENTS_" + station_id + ".json", by_station[station_id])
      os.system("gzip -f /mnt/ams2/EVENTS/STATIONS/ALL_EVENTS_" + station_id + ".json")
      print("gzip -f /mnt/ams2/EVENTS/STATIONS/ALL_EVENTS_" + station_id + ".json")
      os.system("cp /mnt/ams2/EVENTS/STATIONS/ALL_EVENTS_" + station_id + ".json.gz /mnt/archive.allsky.tv/EVENTS/STATIONS/")


def make_shower_indexes():
   fp = open("dumps/x_meteor_event.txt")
   shower_dir = "/mnt/ams2/EVENTS/SHOWERS/"
   if cfe(shower_dir,1) == 0:
      os.makedirs(shower_dir)
   all_obs_events = {}
   ic = 1
   by_shower = {}
   bad_orbs = []
   for line in fp:
      item = json.loads(line)
      item = json.loads(json.dumps(item, cls=DecimalEncoder))
      if item is None:
         print("ITEM IS NONE!", line)
         exit()
      if "stations" not in item:
         continue
      if "final_vids" in item:
         del(item['final_vids'])
      if "obs" in item:
         del(item['obs'])
      if "solution" in item:
         if "simple_solve" in item['solution']:
            del(item['solution']['simple_solve'])
         if "kml" in item['solution']:
            del(item['solution']['kml'])
         if "plot" in item:
            del(item['plot'])

      if "solution" in item:
         if "rad" in item['solution']:
            rad = item['solution']['rad']
            if rad is None:
               print("RAD IS NONE:", rad)
               new_rad = [0,0,0,0,0,0]
            else:
               if rad['geocentric']['ra_g'] is not None:
                  geo_ra = np.radians(np.degrees(rad['geocentric']['ra_g'])-180)
                  geo_ra = np.degrees(geo_ra)
                  geo_dec = rad['geocentric']['dec_g']
               else:
                  geo_ra = 0
                  geo_dec = 0
               if "apparent_ECI" in rad:
                  ap_ra = np.radians(np.degrees(rad['apparent_ECI']['ra'])-180)
                  ap_ra = np.degrees(ap_ra)
                  ap_dec = rad['apparent_ECI']['dec']

               if "ecliptic_helio" in rad:
                  if rad['ecliptic_helio']['L_h'] is not None:
                     hl_ra = np.radians(np.degrees(rad['ecliptic_helio']['L_h']))
                     hl_ra = np.degrees(hl_ra)
                     hl_dec = rad['ecliptic_helio']['B_h']
                  else:
                     hl_dec = 0
                     hl_ra = 0

               new_rad = [round(geo_ra,2),round(geo_dec,2),round(ap_ra,2),round(ap_dec,2),round(hl_ra,2),round(hl_dec,2)]
            item['solution']['rad'] = new_rad
         if "lats" in item:
            del(item['lats'])
         if "lons" in item:
            del(item['lons'])
         item['ob'] = []
         for i in range(0, len(item['stations'])):
            okey = item['stations'][i] + "_" + item['files'][i].replace("_","")
            okey = okey.replace("-", "")
            okey = okey.replace("AMS", "")
            okey = okey.replace("trim", "t")
            okey = okey.replace(".mp4", "")
            item['ob'].append(okey)
         del(item['files'])
         del(item['stations'])
         event_start_time = min(item['start_datetime'])
         event_start_time = event_start_time.replace(":", "")
         event_start_time = event_start_time.replace("-", "")
         event_start_time = event_start_time.replace(" ", "")
         month = event_start_time[4:6]
         item['es'] = event_start_time
         del(item['start_datetime'])



         if "shower" in item['solution']:
            if item['solution']['shower']['shower_code'] == "...":
               item['solution']['shower'] = "SPO-" + month
               shower = "SPO-" + month
            else:
               shower = item['solution']['shower']['shower_code'] 
         else:
            shower = None
         item['shower'] = shower

         if shower is not None and "shower" in item['solution']:
            if shower not in by_shower:
               by_shower[shower] = []
            item = minimize_item(item)
            if item[-1] == 0:
               by_shower[shower].append(item)
            else:
               shower = "PROB-" + shower
               if shower not in by_shower:
                  by_shower[shower] = []

               by_shower[shower].append(item)

      ic += 1
      if ic > 1000:
         print(ic)
   bfile = shower_dir + "PROB" + ".json"
   save_json_file(bfile, bad_orbs,True)
   stats = {}
   for shower in by_shower:
      sfile = shower_dir + shower + ".json"
      stats[shower] = len(by_shower[shower])
      save_json_file(sfile, by_shower[shower],True)
      print("saved ", sfile)
   stats_file = shower_dir + "STATS" + ".json"
   save_json_file(stats_file, stats)

def make_shower_main_page():
   shower_dir = "/mnt/ams2/EVENTS/SHOWERS/"
   html = """
   <h1>Solved Events by Shower</h1>
   """
   #showers = glob.glob(shower_dir + "*.json")
   stats = load_json_file(shower_dir + "STATS.json")
   sorted_stats = []
   for key in stats:
      sorted_stats.append((key, stats[key]))
   sorted_stats = sorted(sorted_stats, key=lambda x: x[1], reverse=True)
   for row in sorted_stats:
      print(row)

# WE SHOULD RUN THIS AT LEAST 1x PER DAY
dump_events(dynamodb)
make_all_obs_events()
#make_shower_indexes()
#index_all_obs_events()

#make_shower_main_page()
