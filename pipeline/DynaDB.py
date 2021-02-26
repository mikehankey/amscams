#!/usr/bin/python3
import math
import os
from datetime import datetime
import json
from decimal import Decimal
import sys
import glob
from lib.PipeUtil import cfe, load_json_file, save_json_file
import boto3
import socket
import subprocess
from boto3.dynamodb.conditions import Key
from lib.PipeUtil import get_file_info, fn_dir



def create_tables(dynamodb):

   try:
   # station table
      table = dynamodb.create_table(
         TableName='station',
         BillingMode='PAY_PER_REQUEST',
         KeySchema=[
            {
               'AttributeName': 'station_id',
               'KeyType' : 'HASH'
            }
         ],
         AttributeDefinitions=[
            {
               'AttributeName': 'station_id',
               'AttributeType': 'S'
            }
         ]
      ) 
      table.meta.client.get_waiter('table_exists').wait(TableName='stations')
   except:
      print("Station table exists.")

   # obs table
   #if True:
   try:
      table = dynamodb.create_table(
         TableName='meteor_obs',
         BillingMode='PAY_PER_REQUEST',
         KeySchema=[
            {
               'AttributeName': 'station_id',
               'KeyType' : 'HASH'
            },
            {
               'AttributeName': 'sd_video_file',
               'KeyType' : 'RANGE'
            }
         ],
         AttributeDefinitions=[
            {
               'AttributeName': 'station_id',
               'AttributeType': 'S'
            },
            {
               'AttributeName': 'sd_video_file',
               'AttributeType': 'S'
            }
         ]
      ) 
      table.meta.client.get_waiter('table_exists').wait(TableName='meteor_obs')
   #try:
   except:
      print("meteor obs table exists already.")


   # event table
   try:
      table = dynamodb.create_table(
         TableName='x_meteor_event',
         BillingMode='PAY_PER_REQUEST',
         KeySchema=[
            {
               'AttributeName': 'event_day',
               'KeyType' : 'HASH'
            },
            {
               'AttributeName': 'event_id',
               'KeyType' : 'RANGE'
            }
         ],
         AttributeDefinitions=[
            {
               'AttributeName': 'event_day',
               'AttributeType': 'S',
            },
            {
               'AttributeName': 'event_id',
               'AttributeType': 'S',
            }
         ]
      ) 
      table.meta.client.get_waiter('table_exists').wait(TableName='x_meteor_event')
   except: 
      print("Event table exists.")
   print("Made tables.")

def load_obs_month(dynamodb, station_id, wild):
   files = glob.glob("/mnt/ams2/meteors/" + wild + "*")
   for file in sorted(files):
      if cfe(file, 1) == 1:
         day = file.split("/")[-1]
         load_meteor_obs_day(dynamodb, station_id,day)

def load_meteor_obs_day(dynamodb, station_id, day):
   files = glob.glob("/mnt/ams2/meteors/" + day + "/*.json")
   meteors = []
   for mf in files:
      if "reduced" not in mf and "stars" not in mf and "man" not in mf and "star" not in mf and "import" not in mf and "archive" not in mf and "frame" not in mf:
         meteors.append(mf)

   for meteor_file in meteors:
      print("loading", meteor_file) 
      insert_meteor_obs(dynamodb, station_id, meteor_file)

def insert_meteor_event(dynamodb, event_id, event_data):
   event_data = json.loads(json.dumps(event_data), parse_float=Decimal)
   table = dynamodb.Table('x_meteor_event')
   table.put_item(Item=event_data)

def insert_meteor_obs(dynamodb, station_id, meteor_file):
   update_time = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
   if "/mnt/ams2/meteors" not in meteor_file:
      date = meteor_file[0:10]
      meteor_file = "/mnt/ams2/meteors/" + date + "/" + meteor_file

   if cfe(meteor_file) == 1:
      red_file = meteor_file.replace(".json", "-reduced.json")
      mj = load_json_file(meteor_file)
      if "revision" not in mj:
         mj['revision'] = 1

      if "cp" in mj:
         cp = mj['cp']
         if "total_res_px" not in cp:
            cp['total_res_px'] = 9999
         if "cat_image_stars" not in cp:
            cp['cat_image_stars'] = []
         if math.isnan(cp['total_res_px']):
            cp['total_res_px'] = 9999
         calib = [cp['ra_center'], cp['dec_center'], cp['center_az'], cp['center_el'], cp['position_angle'], cp['pixscale'], float(len(cp['cat_image_stars'])), float(cp['total_res_px'])]
      else:
         calib = []
      if cfe(red_file) == 1:
         mjr = load_json_file(red_file)
      else:
         mjr = {}
      sd_vid,xxx = fn_dir(mj['sd_video_file'])
      hd_vid,xxx = fn_dir(mj['hd_trim'])
      if "meteor_frame_data" in mjr:
         meteor_frame_data = mjr['meteor_frame_data']
         duration = len(mjr['meteor_frame_data']) / 25
         event_start_time = mjr['meteor_frame_data'][0][0]
      else:
         meteor_frame_data = []
         event_start_time = ""
         duration = 99
   else:
      print("BAD FILE:", meteor_file)
      return()

   if "best_meteor" in mj:
      peak_int = max(mj['best_meteor']['oint'])
   else:
      peak_int = 0




   obs_data = {
      "sd_video_file": sd_vid,
      "hd_video_file": hd_vid,
      "station_id": station_id,
      "event_start_time": event_start_time,
      "duration": duration,
      "peak_int": peak_int,
      "calib": calib,
      "revision": mj['revision'],
      "last_update": update_time,
      "meteor_frame_data": meteor_frame_data
   }
   obs_data = json.loads(json.dumps(obs_data), parse_float=Decimal)
   table = dynamodb.Table('meteor_obs')
   print("SD VID:", sd_vid)
   table.put_item(Item=obs_data)
   mj['calib'] = calib
   mj['last_update'] = update_time
   save_json_file(meteor_file, mj)

def insert_station(dynamodb, station_id):

   conf_file = "/mnt/ams2/STATIONS/CONF/" + station_id + "_as6.json"
   jss = load_json_file(conf_file)
   js = jss['site'] 

   table = dynamodb.Table('station')
   if "operator_country" not in js:
      js['operator_country'] = ""
   if "obs_name" not in js:
      js['obs_name'] = ""

   station_data = {
      "station_id" : station_id,
      "name" : js['operator_name'],
      "city" : js['operator_city'],
      "state" : js['operator_state'],
      "country" : js['operator_country'],
      "obs_name" : js['obs_name'],
      "lat" : js['device_lat'],
      "lon" : js['device_lng'],
      "alt" : js['device_alt'],
      "passwd" : js['pwd']
   }
   table.put_item(Item=station_data)
   #   "local_ip" : ip,
   #   "vpn_ip" : js['vpn_ip'],
   #   "mac_addr" : js['mac_addr'],


def load_stations(dynamodb):
   files = glob.glob("/mnt/ams2/STATIONS/CONF/*_as6.json")
   for file in files:
      fn, dir = fn_dir(file)
      fn = fn.replace("_as6.json", "")
      print(fn)   
      insert_station(dynamodb, fn)


def delete_event(dynamodb, event_day, event_id):
   print("DELETE EVENT:", event_day, event_id)
   table = dynamodb.Table('x_meteor_event')
   response = table.delete_item(
      Key= {
         "event_day": event_day,
         "event_id": event_id
     }
   )
   print("DEL:", response)

def delete_obs(dynamodb, station_id, sd_video_file):
   print("DELETE:", station_id, sd_video_file)
   table = dynamodb.Table('meteor_obs')
   response = table.delete_item(
      Key= {
         "station_id": station_id,
         "sd_video_file": sd_video_file
     }
   )
   print("DEL:", response)


def cache_day(dynamodb, date, json_conf):
   # LOCAL EVENT DIR
   le_dir = "/mnt/ams2/meteor_archive/" + json_conf['site']['ams_id'] + "/EVENTS/" + date + "/"
   if cfe(le_dir, 1) == 0:
      os.makedirs(le_dir)
   stations = json_conf['site']['multi_station_sync']
   if json_conf['site']['ams_id'] not in stations:
      stations.append(json_conf['site']['ams_id'])
   events = search_events(dynamodb, date, stations)
   for event in events:
      print(event['event_id']) 
   event_file = le_dir + date + "_events.json"
   save_json_file(event_file, events)
   print("SAVED:", event_file)
   for station in stations:
      obs = search_obs(dynamodb, station, date)
      obs_file = le_dir + station + "_" + date + ".json"
      save_json_file(obs_file, obs)
      print("SAVED:", obs_file)

def search_events(dynamodb, date, stations):
   dyn_cache = "/mnt/ams2/DYCACHE/"
   use_cache = 0
   if cfe(dyn_cache, 1) == 0:
      os.makedirs(dyn_cache)
   dc_file = dyn_cache + date + "_events.json"   
   if cfe(dc_file) == 1:
      size, tdiff = get_file_info(dc_file)
      hours_old = tdiff / 60
      print("HOURS OLD:", hours_old)
      if hours_old < 4:
       
         use_cache = 1   

   use_cache = 0
   if use_cache == 0:
      if dynamodb is None:
         dynamodb = boto3.resource('dynamodb')


      table = dynamodb.Table('x_meteor_event')
      response = table.query(
         KeyConditionExpression='event_day= :date',
         ExpressionAttributeValues={
           ':date': date,
         } 
      )
      save_json_file(dc_file, response['Items'])
      return(response['Items'])
   else :
      print("we will use cache for events today" + date)
      return(load_json_file(dc_file))


def search_obs(dynamodb, station_id, date, no_cache=0):
   print(station_id, date)

   dyn_cache = "/mnt/ams2/DYCACHE/"
   use_cache = 0
   if cfe(dyn_cache, 1) == 0:
      os.makedirs(dyn_cache)
   dc_file = dyn_cache + date + "_" + station_id + "_obs.json"   
   if cfe(dc_file) == 1:
      size, tdiff = get_file_info(dc_file)
      hours_old = tdiff / 60
      print("HOURS OLD:", hours_old)
      if hours_old < 4:
         use_cache = 1   

   use_cache = 0
   if use_cache == 0 or no_cache == 1:
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
      print("USE DYNA OBS CALL:",date, station_id )
      return(response['Items'])
   else:
      print("USE OBS CACHE:", dc_file)
      return(load_json_file(dc_file))


def get_event(dynamodb, event_id, nocache=1):


   print("GET EVENT:", event_id)
   dyn_cache = "/mnt/ams2/DYCACHE/"
   use_cache = 0
   if cfe(dyn_cache, 1) == 0:
      os.makedirs(dyn_cache)

   y = event_id[0:4]
   m = event_id[4:6]
   d = event_id[6:8]
   date = y + "_" + m + "_" + d

   dc_file = dyn_cache + date + "_events.json"   
   if cfe(dc_file) == 1:
      size, tdiff = get_file_info(dc_file)
      hours_old = tdiff / 60
      print("HOURS OLD:", hours_old)
      if hours_old < 4:
         use_cache = 1   
   if nocache == 0:
      use_cache = 0 

   if use_cache == 1:
      evs = load_json_file(dc_file)
      for ev in evs:
         if ev['event_id'] == event_id:
            print("USE CACHE FOR EVENT PLEASE!", event_id)
            return(ev)

   if dynamodb is None:
      dynamodb = boto3.resource('dynamodb')

   print("GET EVENT WITHOUT USING THE CACHE!")

   table = dynamodb.Table('x_meteor_event')
   event_day = event_id[0:8]
   y = event_day[0:4]
   m = event_day[4:6]
   d = event_day[6:8]
   event_day = y + "_" + m + "_" + d
   print("GET EVENT:", event_day, event_id)
   response = table.query(
      KeyConditionExpression='event_day= :event_day AND event_id= :event_id',
      ExpressionAttributeValues={
         ':event_day': event_day,
         ':event_id': event_id,
      } 
   )
   print("GETTING EVENT FOR:", event_day, event_id)

   if len(response['Items']) > 0:
      return(response['Items'][0])
   else:
      print("Get event failed for :", event_id)
      print(response)
      return([])

def get_obs(dynamodb, station_id, sd_video_file):
   date= sd_video_file[0:10]
   dyn_cache = "/mnt/ams2/DYCACHE/"
   use_cache = 0
   if cfe(dyn_cache, 1) == 0:
      os.makedirs(dyn_cache)
   dc_file = dyn_cache + date + "_" + station_id + "_obs.json"   
   if cfe(dc_file) == 1:
      size, tdiff = get_file_info(dc_file)
      if tdiff / 60 < 4:
         dc_obs = load_json_file(dc_file)
         for obs in dc_obs:
            
            if obs['sd_video_file'] == sd_video_file:
               print("USE CACHE OBS:", station_id, sd_video_file)
               return(obs)

   if dynamodb is None:
      dynamodb = boto3.resource('dynamodb')
   table = dynamodb.Table('meteor_obs')
   response = table.query(
      KeyConditionExpression='station_id = :station_id AND sd_video_file = :sd_video_file',
      ExpressionAttributeValues={
         ':station_id': station_id,
         ':sd_video_file': sd_video_file,
      } 
   )
   if len(response['Items']) > 0:
      return(response['Items'][0])
   else:
      return(None)

def sync_db_day(dynamodb, station_id, day):
   # remove the cache 
   cmd = "rm /mnt/ams2/DYCACHE/*.json"
   os.system(cmd)
   cmd = "./DynaDB.py cd " + day 
   os.system(cmd)

   db_meteors = {}
   items = search_obs(dynamodb, station_id, day, 1)
   for item in items:
      db_meteors[item['sd_video_file']] = {}
      db_meteors[item['sd_video_file']]['dyna'] = 1
      if "revision" not in item:
         db_meteors[item['sd_video_file']]['revision'] = 1
      else:
         db_meteors[item['sd_video_file']]['revision'] = item['revision']

   files = glob.glob("/mnt/ams2/meteors/" + day + "/*.json")   
   meteors = []
   for mf in files:
      if "reduced" not in mf and "stars" not in mf and "man" not in mf and "star" not in mf and "import" not in mf and "archive" not in mf and "frame" not in mf:
         meteors.append(mf)

   local_meteors = {}
   for mf in meteors:
      fn, xxx = fn_dir(mf)
      sd_video_file = fn.replace(".json", ".mp4")
      mfr = mf.replace(".json", "-reduced.json")
      mj = load_json_file(mf)
      if cfe(mfr) == 1:
         mjr = load_json_file(mfr)
      else:
         mjr['meteor_frame_data'] = []
      if "revision" not in mj:
         mj['revision'] = 1
      local_meteors[sd_video_file] = {}
      local_meteors[sd_video_file]['revision'] = mj['revision']
      local_meteors[sd_video_file]['meteor_frame_data'] = mjr['meteor_frame_data']
      if "final_vid" in mj:
         local_meteors[sd_video_file]['final_vid'] = mj['final_vid']

   # Do all of the db meteors still exist locally, if not 
   # they have been deleted and should be removed from the remote db
   for dkey in db_meteors:
      if dkey not in local_meteors:
         print(dkey, "DELETE OBS: no longer exists locally and should be removed from the remote db." )
         meteor_file = dkey.replace(".mp4", ".json")
         video_file = dkey
         delete_obs(dynamodb, station_id, video_file)
      else:
         print(dkey, "GOOD: exists locally." )

   # Do all of the local meteors exist in the remote db?
   # if not add them in
   for lkey in local_meteors:
      if lkey not in db_meteors:
         print(lkey, "INSERT OBS: is not in the DB yet. We should add it." )
         meteor_file = lkey.replace(".mp4", ".json")
         insert_meteor_obs(dynamodb, station_id, meteor_file)
      else:
         print(lkey, "GOOD: exists in the remote db." )

   # Do all of the revision numbers match between the local and db meteors?
   # If the local revision is higher than the remote, we need to push the updates to the DB
   # BUT if the DB revision is higher than the local, we need to pull the MFD from the db and update the meteor objects (populate reduced file and manual overrides in mj) *** The PULL part is only needed once we have remote editing enabled. *** 
   for lkey in local_meteors:
      if lkey not in db_meteors:
         print(lkey, "IGNORE: is not in the DB yet. But should be added in this run." )
      else:
         force = 1
         if local_meteors[lkey]['revision'] > db_meteors[lkey]['revision'] or "final_data" not in db_meteors[lkey] or force == 1:
           
            print(lkey, "UPDATE REMOTE : The local DB has a newer version of this file. " , local_meteors[lkey]['revision'] ,   db_meteors[lkey]['revision'])
            meteor_file = lkey.replace(".mp4", ".json")
            #insert_meteor_obs(dynamodb, station_id, meteor_file)
            obs_data = {}
            obs_data['revision'] = local_meteors[lkey]['revision']
            obs_data['meteor_frame_data'] = local_meteors[lkey]['meteor_frame_data']
            obs_data['last_update'] = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
            if "final_vid" in local_meteors[lkey]:
               print("ADD FINAL DATA!")
               final_vid = local_meteors[lkey]['final_vid']
               final_vid_fn, xxx = fn_dir(final_vid)
               final_data_file = final_vid.replace(".mp4", ".json")
               final_data = load_json_file(final_data_file)
               obs_data['final_vid'] = final_vid_fn
               obs_data['final_data'] = final_data 
            else:
               print("No final data?")

             
            sd_video_file = meteor_file.replace(".json", ".mp4")
            update_meteor_obs(dynamodb, station_id, sd_video_file, obs_data)

         if local_meteors[lkey]['revision'] == db_meteors[lkey]['revision']:
            print(lkey, "GOOD: The remote and local revisions are the same." )

   print("SEARCH OBS:", station_id, day)
   items = search_obs(dynamodb, station_id, day, 1)
   for item in items:
      print("IN DB:", station_id, item['sd_video_file'], item['revision'])
   print(len(items), "items for", station_id)


def update_meteor_obs(dynamodb, station_id, sd_video_file, obs_data):

   dmfd = []
   for data in obs_data['meteor_frame_data']:
      (dt, fn, x, y, w, h, oint, ra, dec, az, el) = data
      dmfd.append((dt,float(fn),float(x),float(y),float(w),float(h),float(oint),float(ra),float(dec),float(az),float(el)))
   obs_data['meteor_frame_data'] = dmfd
 

   if dynamodb is None:
      dynamodb = boto3.resource('dynamodb')
   table = dynamodb.Table("meteor_obs")
   obs_data = json.loads(json.dumps(obs_data), parse_float=Decimal)
   print("REV:", obs_data['revision'])
   print("ST:", station_id)
   print("F:", sd_video_file)
   response = table.update_item(
      Key = {
         'station_id': station_id,
         'sd_video_file': sd_video_file 
      },
      UpdateExpression="set revision = :revision, last_update= :last_update, meteor_frame_data=:meteor_frame_data, final_vid=:final_vid, final_data=:final_data",
      ExpressionAttributeValues={
         ':meteor_frame_data': obs_data['meteor_frame_data'],
         ':final_vid': obs_data['final_vid'],
         ':final_data': obs_data['final_data'],
         ':revision': obs_data['revision'],
         ':last_update': obs_data['last_update']
      },
      ReturnValues="UPDATED_NEW"
   )
   print(response)

def update_event_sol(dynamodb, event_id, sol_data, obs_data, status):
   sol_data = json.loads(json.dumps(sol_data), parse_float=Decimal)
   #obs_data_save = json.loads(json.dumps(obs_data), parse_float=Decimal)
   if dynamodb is None:
      dynamodb = boto3.resource('dynamodb')

   table = dynamodb.Table("x_meteor_event")
   event_day = event_id[0:8]
   y = event_day[0:4]
   m = event_day[4:6]
   d = event_day[6:8]
   event_day = y + "_" + m + "_" + d

   print("STATUS:", status)
   print("SOL DATA:" ,sol_data)
   for key in sol_data:
      print("SOL:", key, sol_data[key], type(sol_data[key]))
      #for fkey in sol_data[key]:
      #   print("SOL:", sol_data[key][fkey])
   if "obs" in sol_data:
      del sol_data['obs']
   for key in obs_data:
      for fkey in obs_data[key]:
         obs_data[key][fkey]['calib'][6] = float(obs_data[key][fkey]['calib'][6])
         del obs_data[key][fkey]['calib']
         
   obs_data = json.loads(json.dumps(obs_data), parse_float=Decimal)
      
   #obs_data = {}
   #sol_data = {}

   response = table.update_item(
      Key = {
         'event_day': event_day ,
         'event_id': event_id
      },
      UpdateExpression="set solve_status=:status, solution=:sol_data, obs=:obs_data  ",
      ExpressionAttributeValues={
         ':status': status ,
         ':sol_data': sol_data,
         ':obs_data': obs_data
      },
      ReturnValues="UPDATED_NEW"
   )
   print(response)
         #':obs_data': obs_data,
   print("UPDATED EVENT WITH SOLUTION.")
   return response



def update_event(dynamodb, event_id, simple_status, wmpl_status, sol_dir):
   table = dynamodb.Table("x_meteor_event")
   event_day = event_id[0:8]
   y = event_day[0:4]
   m = event_day[4:6]
   d = event_day[6:8]
   event_day = y + "_" + m + "_" + d

   response = table.update_item(
      Key = {
         'event_day': event_day ,
         'event_id': event_id
      },
      UpdateExpression="set simple_solve=:simple_status, WMPL_solve=:wmpl_status, sol_dir=:sol_dir",
      ExpressionAttributeValues={
         ':simple_status': simple_status,
         ':wmpl_status': wmpl_status, 
         ':sol_dir': sol_dir 
      },
      ReturnValues="UPDATED_NEW"
   )
   print(response)
   return response

def do_dyna_day(dynamodb, day):
   # do everything to prep and load meteors
   # to get them ready for solving
   # and then also download event data for this site
   # and update the mse info in the json for each site
   # also sync prev imgs for mse events
   cmd = "./Process.py reject_masks " + day
   print(cmd)
   os.system(cmd)

   cmd = "./Process.py reject_planes " + day
   print(cmd)
   os.system(cmd)
   
   cmd = "./Process.py confirm " + day
   print(cmd)
   os.system(cmd)

   cmd = "./Process.py remaster_day " + day
   print(cmd)
   os.system(cmd)

   cmd = "./DynaDB.py sync_db_day " + day
   print(cmd)
   os.system(cmd)

   cmd = "./DynaDB.py cd " + day
   print(cmd)
   os.system(cmd)

   cmd = "./Process.py ded " + day
   print(cmd)
   os.system(cmd)

   cmd = "./Process.py sync_prev_all " + day
   print(cmd)
   os.system(cmd)

   cmd = "./Process.py sync_final_day " + day
   print(cmd)
   os.system(cmd)

   cmd = "./DynaDB.py cd " + day
   print(cmd)
   os.system(cmd)


def update_mj_events(dynamodb, date):
   print("UPDATE MJ FOR DYNA EVENTS FOR", date)
   json_conf = load_json_file("../conf/as6.json")
   stations = json_conf['site']['multi_station_sync']
   amsid = json_conf['site']['ams_id']
   if amsid not in stations:
      stations.append(amdid)
   events = search_events(dynamodb, date, stations)
   dyn_cache = "/mnt/ams2/DYCACHE/"
   if cfe(dyn_cache, 1) == 0:
      os.makedirs(dyn_cache)
   save_json_file(dyn_cache + date + "_events.json",events)
   my_files = []
   for event in events:
      mse = {}
      mse['start_datetime'] = []
      mse['stations'] = []
      mse['files'] = []
 
      if "solution" in event:
         mse['solution'] = event['solution']
      if "orb" in event:
         mse['orb'] = event['orb']
      for i in range(0, len(event['stations'])):
         mse['stations'].append(event['stations'][i])
         mse['files'].append(event['files'][i])
         mse['event_id'] = event['event_id']
      
         if event['stations'][i] == amsid:
            my_files.append((event['files'][i], mse))
            print("my files:", event['files'][i])
        
   mse_log = "/mnt/ams2/meteors/" + date + "/" + amsid + "_" + date + "_mse.info" 
   mse_db = {}
   print("SAVED:", dyn_cache + date + "_events.json")
   for file,ev in my_files:
      mse_db[file] = ev
      print("UPDATE LOCAL FILE:", file, ev)

   save_json_file(mse_log, mse_db)
   print("saved:", mse_log)

def orbs_for_day(date,json_conf):
   le_dir = "/mnt/ams2/meteor_archive/" + json_conf['site']['ams_id'] + "/EVENTS/" + date + "/"
   event_file = le_dir + date + "_events.json"
   orbs_file = le_dir + date + "_orbs.json"
   events = load_json_file(event_file)

   
   orbs = {}
   for ev in events:
      if "solution" in ev:
         if "orb" in ev['solution']:
            o = ev['solution']['orb']
            print(ev['event_id'],ev)
            event_url = ev['solution']['sol_dir'].replace("/mnt/ams2/meteor_archive/", "http://archive.allsky.tv/")
            print(event_url)
            op = {}
            op['name'] = ev['event_id']
            op['epoch'] = o['jd_ref']
            op['utc_date'] = min(ev['start_datetime'])
            op['T'] = o['jd_ref']
            op['vel'] = 0
            op['a'] = o['a']
            op['e'] = o['e']
            op['I'] = o['i']
            op['Peri'] = o['peri']
            op['Node'] = o['node']
            op['q'] = o['q']
            op['M'] = o['mean_anomaly']
            op['P'] = o['T']
            orbs[ev['event_id']] = op
   save_json_file(orbs_file, orbs)
   print("saved.", orbs_file)
 
if __name__ == "__main__":
   dynamodb = boto3.resource('dynamodb')
   json_conf = load_json_file("../conf/as6.json")
   cmd = sys.argv[1]
   if cmd == "sync_db_day" or cmd == "sdd":
      station_id = json_conf['site']['ams_id']
      sync_db_day(dynamodb, station_id, sys.argv[2])

   if cmd == "ct":
      create_tables(dynamodb)
   if cmd == "ls":
      load_stations(dynamodb)
   if cmd == "del_obs":
      station_id = json_conf['site']['ams_id']
      meteor_file = sys.argv[2]
      delete_obs(dynamodb, station_id, meteor_file)
   if cmd == "add_obs":
      station_id = json_conf['site']['ams_id']
      meteor_file = sys.argv[2]
      insert_meteor_obs(dynamodb, station_id, meteor_file)

   if cmd == "search_obs":
      station_id = json_conf['site']['ams_id']
      search_obs(dynamodb, station_id, sys.argv[2])
   if cmd == "load_day":
      station_id = json_conf['site']['ams_id']
      load_meteor_obs_day(dynamodb, station_id, sys.argv[2])
   if cmd == "load_month":
      station_id = json_conf['site']['ams_id']
      load_obs_month(dynamodb, station_id, sys.argv[2])
   if cmd == "ddd":
      do_dyna_day(dynamodb, sys.argv[2])
   if cmd == "dddm":
      wild = sys.argv[2]
      files = glob.glob("/mnt/ams2/meteors/" + wild + "*")
      for file in sorted(files):
         day = file.split("/")[-1]
         print(file, day)
         do_dyna_day(dynamodb, day)
   if cmd == "umje":
      update_mj_events(dynamodb, sys.argv[2])
   if cmd == "sync_year":
      wild = sys.argv[2]
      station_id = json_conf['site']['ams_id']
      files = glob.glob("/mnt/ams2/meteors/" + wild + "*")
      for file in sorted(files):
         day = file.split("/")[-1]
         print(file, day)
         sync_db_day(dynamodb, station_id, day)
   if cmd == "cache_day" or cmd == "cd":
      day = sys.argv[2]
      cache_day(dynamodb, day, json_conf)
   if cmd == "orbs_for_day" or cmd == "ofd":
      day = sys.argv[2]
      orbs_for_day(day, json_conf)
