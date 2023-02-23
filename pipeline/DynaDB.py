#!/usr/bin/python3

### /usr/bin/env python3
from decimal import Decimal
import redis
import requests
from lib.PipeManager import dist_between_two_points
import math
import os
from datetime import datetime
import datetime as dt
import simplejson as json
from decimal import Decimal
import sys
import glob
from lib.PipeUtil import cfe, load_json_file, save_json_file, check_running, get_trim_num
import boto3
import socket
import subprocess
from boto3.dynamodb.conditions import Key, Attr
from lib.PipeUtil import get_file_info, fn_dir, convert_filename_to_date_cam
from Classes.SyncAWS import SyncAWS

r = redis.Redis("allsky-redis.d2eqrc.0001.use1.cache.amazonaws.com", port=6379, decode_responses=True)
API_URL = "https://kyvegys798.execute-api.us-east-1.amazonaws.com/api/allskyapi"

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return json.JSONEncoder.default(self, obj)

def all_deletes(dynamodb, json_conf):
   # build file for each station of all AWS deleted meteor detects
   table = dynamodb.Table('meteor_delete')
   response = table.scan()
   data = response['Items']
   c = 0
   all_items = []
   for item in response['Items']:
      all_items.append(item)

   while 'LastEvaluatedKey' in response:
      print("WHILE UPDATING ITEMS.", len(all_items))
      response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
      for item in response['Items']:
         all_items.append(item)
   save_json_file("/mnt/f/EVENTS/ALL_DELETES.json", all_items, True)

   deletes_by_station = {}
   for item in all_items:
      station_id = item['station_id']
      sd_video_file = item['sd_video_file']
      if "delete_committed" in item:
         delete_committed = item['delete_committed']
      else:
         delete_committed = 0
      if "label" in item:
         label = item['label']
      else:
         label = ""
      if station_id not in deletes_by_station:
         deletes_by_station[station_id] = []
      deletes_by_station[station_id].append((sd_video_file,label,delete_committed))
   out_dir = "/mnt/f/EVENTS/OBS/STATIONS/"
   cloud_out_dir = "/mnt/archive.allsky.tv/EVENTS/OBS/STATIONS/"
   for st in deletes_by_station:
      save_json_file(out_dir + st + "_DEL.json", deletes_by_station[st])
      cmd = "cp " + out_dir + st + "_DEL.json " + cloud_out_dir
      print(cmd)
      os.system(cmd)




def quick_event_report(date, dynamodb, json_conf):

   table = dynamodb.Table('x_meteor_event')
   year, mon, day = date.split("_")
   r = redis.Redis("allsky-redis.d2eqrc.0001.use1.cache.amazonaws.com", port=6379, decode_responses=True)
   cloud_dir = "/mnt/archive.allsky.tv/EVENTS/" + year + "/" + mon + "/" + day + "/"
   sdate = date.replace("_", "")
   keys = r.keys("E:" + sdate + "*")
   print("E:" + sdate)
   stats = {}
   print("KEYS:", len(keys))
   for key in keys:
      event_id = key.replace("E:", "")
      rval = r.get(key)
      if rval is not None:
         rval = json.loads(rval)
      else:
         continue
      if event_id != rval['event_id']:
         rval['event_id'] = event_id
         print("PROBLEM:", key, okey, event_id)
         if False:
            r.delete(key)
            okey = key.replace("A", "")
            r.delete(okey)
            print("DELETING: ", key, okey)

            # Need to delete from dynamo too
            delete_event(dynamodb, date, event_id)
            delete_event(dynamodb, date, event_id.replace("A", ""))

            print("DELETED:", key, okey, event_id)

      if "solve_status" in rval:
         print(key, rval['solve_status'])
         ss = rval['solve_status']
      else:
         print(key, "UNSOLVED")
         ss = "UNSOLVED"
      event_id = rval['event_id']
      event_dir = cloud_dir + event_id + "/"
      if ss == "UNSOLVED":
         print("UNSOLVED EVENT:", event_dir) 
    #     exit()

      if ss not in stats:
         stats[ss] = 0
      stats[ss] += 1
   for key in stats:
      print(key, stats[key])

def back_loader(dynamodb, json_conf):
   mdirs = glob.glob("/mnt/ams2/meteors/*")
   meteor_days = []
   update_time = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
   for mdir in mdirs:
      if cfe(mdir, 1) == 1:
         meteor_days.append(mdir)
   c = 0
   for day_dir in sorted(meteor_days, reverse=True):
      work_file = day_dir + "/" + "work.info"
      day = day_dir.split("/")[-1]
      if cfe(work_file) == 1:
         print("Work file exists we can skip.", day)
      else:
         print("Work file doesn't exist lets do the work.", day)
         os.system("./DynaDB.py ddd " + day)
         work = {}
         work['dyna-ddd'] = update_time
         save_json_file(work_file, work)
         c += 1
      if c > 10:
         print("That's enough for now!")
         exit()

def save_json_conf(dynamodb, json_conf):
   cams = []
   station_id = json_conf['site']['ams_id']
   for cam in json_conf['cameras']:
      cam_id = json_conf['cameras'][cam]['cams_id']
      cams.append(cam_id)
   conf_mini = {}
   conf_mini['station_id'] = json_conf['site']['ams_id']
   conf_mini['operator_name'] = json_conf['site']['operator_name']
   conf_mini['email'] = json_conf['site']['operator_email']
   if "obs_name" not in json_conf['site']:
      conf_mini['obs_name'] = ""
   conf_mini['city'] = json_conf['site']['operator_city']
   conf_mini['state'] = json_conf['site']['operator_state']
   if "operator_country" not in json_conf['site']:
      json_conf['site']['operator_country'] = ""
   conf_mini['country'] = json_conf['site']['operator_country']
   conf_mini['lat'] = float(json_conf['site']['device_lat'])
   conf_mini['lon'] = float(json_conf['site']['device_lng'])
   conf_mini['alt'] = float(json_conf['site']['device_alt'])
   conf_mini['passwd'] = json_conf['site']['pwd']
   conf_mini['cameras'] = cams

   conf_mini = json.loads(json.dumps(conf_mini), parse_float=Decimal)
   table = dynamodb.Table('station')
   table.put_item(Item=conf_mini)

   save_json_file("../conf/" + station_id + "_conf.json", conf_mini)

   local_conf = "../conf/" + station_id + "_conf.json"
   cloud_conf = "/mnt/archive.allsky.tv/" + station_id + "/CAL/" + station_id + "_conf.json"
   cloud_dir = "/mnt/archive.allsky.tv/" + station_id + "/CAL/" 
   os.system("cp " + local_conf + " " + cloud_conf)
   
   # CP CAL FILES
   os.system("cp /mnt/ams2/cal/multi* " + " " + cloud_dir)
   os.system("cp /mnt/ams2/cal/cal_day* " + " " + cloud_dir)
   os.system("cp /mnt/ams2/cal/cal_hist* " + " " + cloud_dir)
   

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
      insert_meteor_obs(dynamodb, station_id, meteor_file)

def insert_meteor_event(dynamodb=None, event_id=None, event_data=None):
   if cfe("admin_conf.json") == 0:
      print("feature for admin servers only.")
   else:
      admin_conf = load_json_file("admin_conf.json")
      import redis
      r = redis.Redis(admin_conf['redis_host'], port=6379, decode_responses=True)
      admin = 1
   if "A" in event_id: 
      event_data['event_id'] = event_id
   # first check if this event exists, if it does we don't want to wipe out the existing status!
   rkey = "E:" + event_id
   rval = r.get(rkey)
   if rval is not None:
      rval = json.loads(rval)
      #print("THIS EVENT ALREADY EXISTS!", event_id)
      #print("CURRENT DATA:", event_data)
      #print("EXISTING DATA:", rval)

   if dynamodb is None:
      dynamodb = boto3.resource('dynamodb')
   if event_id is not None and event_data is not None:
      event_data = json.loads(json.dumps(event_data), parse_float=Decimal)
      table = dynamodb.Table('x_meteor_event')
      table.put_item(Item=event_data)
      rkey = "E:" + event_id

      rval = json.dumps(event_data ,cls=DecimalEncoder)
      r.set(rkey,rval)
   # update all impacted obs
   for i in range(0, len(event_data['stations'])):
      # setup vars/values
      station_id = event_data['stations'][i]
      sd_video_file = event_data['files'][i]
      if "solve_status" in event_data:
         solve_status = event_data['solve_status']
      else:
         solve_status = "UNSOLVED"
      event_id_val = event_id + ":" + solve_status

      # setup redis keys for obs and get vals
      okey = "O:" + station_id + ":" + sd_video_file
      oikey = "OI:" + station_id + ":" + sd_video_file
      ro_val = r.get(okey)
      roi_val = r.get(oikey)
      if ro_val is not None:
         ro_val = json.loads(ro_val)
         ro_val['event_id'] = event_id_val
         ro_val = json.dumps(ro_val, cls=DecimalEncoder)
         r.set(okey, ro_val)
      if roi_val is not None:
         roi_val = json.loads(roi_val)
         roi_val['ei'] = event_id_val
         roi_val = json.dumps(roi_val, cls=DecimalEncoder)
         r.set(oikey, roi_val)

      # update DYNA OBS with EVENT ID

      table = dynamodb.Table('meteor_obs')
      response = table.update_item(
         Key = {
            'station_id': station_id,
            'sd_video_file': sd_video_file
         },
      UpdateExpression="set event_id = :event_id_val",
      ExpressionAttributeValues={
         ':event_id_val': event_id_val,
      },
      ReturnValues="UPDATED_NEW"
   )

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
   try:
      table.update_item(Item=obs_data)
   except:
      table.put_item(Item=obs_data)
   mj['calib'] = calib
   mj['last_update'] = update_time
   save_json_file(meteor_file, mj)

def update_station(dynamodb, station_id,json_conf):
    table = dynamodb.Table('station')

    try:
        response = table.get_item(Key={'station_id': station_id})
    except ClientError as e:
        print(e.response['Error']['Message'])
    if True:
        station_data = json.loads(json.dumps(response['Item']), parse_float=Decimal)
        rkey = "ST:" + station_id 
        rval = json.dumps(station_data)
        r.set(rkey, rval)
        print("SET:", rkey, rval)

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
   rkey = "ST:" + station_id
   r.set(rkey, json.dumps(station_data))
   #   "local_ip" : ip,
   #   "vpn_ip" : js['vpn_ip'],
   #   "mac_addr" : js['mac_addr'],


def load_stations(dynamodb):
   # This could be a bug! Don't use this anymore!
   files = glob.glob("/mnt/ams2/STATIONS/CONF/*_as6.json")
   for file in files:
      fn, dir = fn_dir(file)
      fn = fn.replace("_as6.json", "")
      #insert_station(dynamodb, fn)


def delete_event(dynamodb=None, event_day=None, event_id=None):
   admin_conf = load_json_file("admin_conf.json")
   if dynamodb is None:
      dynamodb = boto3.resource('dynamodb')
   print("DELETE DYN EVENT:", event_day, event_id)
   table = dynamodb.Table('x_meteor_event')
   response = table.delete_item(
      Key= {
         "event_day": event_day,
         "event_id": event_id
     }
   )
   rkey = "E:" + event_id
   #if "master" in admin_conf:
   #   r.delete(rkey)
   #else:
   #   print("no access to redis")

   print("AWS DYN RESP:", response)

def delete_obs(dynamodb, station_id, sd_video_file, delete_committed=0, delete_reason=""):

   # remove from meteor obs
   table = dynamodb.Table('meteor_obs')
   response = table.delete_item(
      Key= {
         "station_id": station_id,
         "sd_video_file": sd_video_file
     }
   )
   #try:
   #   r = redis.Redis("allsky-redis.d2eqrc.0001.use1.cache.amazonaws.com", port=6379, decode_responses=True)
   #   rkey = "OI:" + station_id + ":" + sd_video_file
   #   r.delete(rkey)
   #except:
   #   print("no redis connection")

   # keep log on meteor_delete table
   obs_data = {
      "station_id": station_id,
      "sd_video_file": sd_video_file,
      "delete_committed": delete_committed,
      "delete_reason": delete_reason,
   }
   obs_data = json.loads(json.dumps(obs_data), parse_float=Decimal)
   table = dynamodb.Table('meteor_delete')
   try:
      table.put_item(Item=obs_data)
   except:
      table.update_item(Item=obs_data)



def event_report(dynamodb, r, date):
   events = search_events(dynamodb, date, "" )
   for ev in events:
      if "solve_status" in ev:
         ss = ev['solve_status']
      else:
         ss = "UNSOVLED"
      #print(ev['event_id'], ss)


   ekey = "E:"+ date.replace("_", "")
   print(ekey)
   keys = r.keys(ekey + "*")
   c = 1
   for key in keys:
      rval = json.loads(r.get(key))
      print(rval.keys())
      if "solve_status" in rval:
         ss = rval['solve_status']
      else:
         ss = "UNSOVLED"
      print(c, key, ss)
      c += 1

def cache_day(dynamodb, date, json_conf):
   # LOCAL EVENT DIR
   le_dir = "/mnt/ams2/meteor_archive/" + json_conf['site']['ams_id'] + "/EVENTS/" + date + "/"
   if cfe(le_dir, 1) == 0:
      os.makedirs(le_dir)
   stations = json_conf['site']['multi_station_sync']
   if json_conf['site']['ams_id'] not in stations:
      stations.append(json_conf['site']['ams_id'])
   events = search_events(dynamodb, date, stations)
   event_file = le_dir + date + "_events.json"
   # DECIMAL ENCODE
   events = json.loads(json.dumps(events,cls=DecimalEncoder))
   for key in events:
      print(key) #, type(events[key]))

   save_json_file(event_file, events)
   for station in stations:
      obs = search_obs(dynamodb, station, date)
      obs_file = le_dir + station + "_" + date + ".json"
      obs = json.loads(json.dumps(obs,cls=DecimalEncoder))
      save_json_file(obs_file, obs)

def select_obs_files(dynamodb, station_id, event_day):
   table = dynamodb.Table("meteor_obs")
   all_items = []
   response = table.query(
      ProjectionExpression='station_id,sd_video_file,revision,event_id',
      KeyConditionExpression=Key('station_id').eq(station_id) & Key('sd_video_file').begins_with(event_day),
      )
   for it in response['Items']:
      all_items.append(it)
   while 'LastEvaluatedKey' in response:
      response = table.query(
         ProjectionExpression='station_id,sd_video_file,revision,event_id',
         KeyConditionExpression=Key('station_id').eq(station_id) & Key('sd_video_file').begins_with(event_day),
         ExclusiveStartKey=response['LastEvaluatedKey'],
         )
      for it in response['Items']:
         all_items.append(it)
   return(all_items)

def purge_auth(dynamodb):
   table = dynamodb.Table("authkeys")
   response = table.scan()
   items = response['Items']
   while 'LastEvaluatedKey' in response:
      response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
      items.extend(response['Items'])
   for item in items:
      resp = table.delete_item(Key={'auth_token': item['auth_token']})
      print(item['auth_token'], resp)


def get_all_events(dynamodb):
   table = dynamodb.Table("x_meteor_event")
   response = table.scan()
   items = response['Items']


   while 'LastEvaluatedKey' in response:
      response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
      items.extend(response['Items'])
   outfile = "/mnt/f/EVENTS/ALL_EVENTS.json"
   save_json_file(outfile, items)


def update_dyna_cache_for_day(dynamodb, date, stations, utype=None, cloud_copy=1):
   year, mon, day = date.split("_")
   cloud_dir = "/mnt/archive.allsky.tv/EVENTS/" + year + "/" + mon + "/" + day + "/"
   if cfe(cloud_dir, 1) == 0:
      os.makedirs(cloud_dir)

   json_conf = load_json_file("../conf/as6.json")
   station_id = json_conf['site']['ams_id']
   api_key = json_conf['api_key']
   if utype is None:
      do_obs = 1
      do_events = 1
   if utype == "events": 
      do_obs = 0
      do_events = 1
   year, mon, day = date.split("_")
   day_dir = "/mnt/f/EVENTS/" + year + "/" + mon + "/" + day + "/"
   dyn_cache = day_dir
   if cfe(dyn_cache, 1) == 0:
      os.makedirs(dyn_cache)

   del_file = dyn_cache + date + "_ALL_DEL.json" 
   obs_file = dyn_cache + date + "_ALL_OBS.json" 
   event_file = dyn_cache + date + "_ALL_EVENTS.json" 
   stations_file = dyn_cache + date + "_ALL_STATIONS.json" 

   # remove current files for the day

   # get station list of stations that could have shared obs
   # don't use the API anymore, it times out. Read direct from redis
   all_stations = glob.glob("/mnt/ams2/STATIONS/CONF/*")
   #for st in sorted(all_stations):
   API_URL = "https://kyvegys798.execute-api.us-east-1.amazonaws.com/api/allskyapi?cmd=get_stations&api_key=" + json_conf['api_key'] + "&station_id=" + json_conf['site']['ams_id']

   response = requests.get(API_URL)
   content = response.content.decode()
   content = content.replace("\\", "")
   if content[0] == "\"":
      content = content[1:]
      content = content[0:-1]
   jdata = json.loads(content)
   save_json_file("/mnt/f/EVENTS/ALL_STATIONS.json", jdata['all_vals'], True)
   os.system("cp /mnt/f/EVENTS/ALL_STATIONS.json /mnt/archive.allsky.tv/EVENTS/ALL_STATIONS.json")
   print("SAVED: /mnt/f/EVENTS/ALL_STATIONS.json")
   all_stations = jdata['all_vals']


   # load the deletes
   # skip for now
   if False:
      all_deletes = []
      del_keys = {}
      for data in all_stations:
         station_id = data['station_id']
         deletes = get_station_deletes(dynamodb, station_id, date)
         for del_item in deletes:
            all_deletes.append(del_item)
            obs_key = del_item['station_id'] + "_" + del_item['sd_video_file']
            if "label" in del_item:
               label = del_item['label']
            else:
               label = ""
            del_keys[obs_key] = label
      save_json_file(del_file, del_keys, True)
      cloud_del_file = del_file.replace("/ams2/", "/archive.allsky.tv/")
      os.system("cp " + del_file + " " + cloud_del_file)
      print("SAVED:", del_file)
   else:
      del_keys = {}

   # now purge any events that match these keys

   clusters = make_station_clusters(all_stations)


   #for cluster in clusters:
   #   print(cluster)
   cluster_stations = []
   stations = []
   for data in clusters:
      #('AMS8', 32.654, -99.844, 'Hawley', [])
      station, lat, lon, alt, city, partners = data
      #if station == "AMS110" or station == "AMS105" or station == "AMS20":
      #   print("ID ??", data)
      if len(partners) > 1:
         cluster_stations.append(data)
   save_json_file(stations_file, clusters, True)
   cloud_stations_file = stations_file.replace("/mnt/ams2/", "/mnt/archive.allsky.tv/")


   os.system("cp " + stations_file + " " + cloud_stations_file)

   # get the obs for each station for this day
   #print("DOOBS:", do_obs)
   #print("cluset:", len(cluster_stations))
   if do_obs == 1:
      #os.system("rm " + obs_file ) 
      all_obs = []
      unq_stations = {}
      for data in cluster_stations:
         station_id = data[0]
         print("STA:", station_id)
         #if station_id in unq_stations:
         #   continue
         unq_stations[station_id] = 1
         stations.append(station_id)
         obs = search_obs(dynamodb, station_id, date, 1)
         print("OBS TOTAL:", station_id, len(obs))
         unq_stations[station_id] = len(obs)
         for data in obs:
            obs_key =  data['station_id'] + "_" +  data['sd_video_file']
            if obs_key in del_keys:
               print("THIS OBS KEY IS DELETED!", obs_key)
            else:
               if "cat_image_stars" in data:
                  del data['cat_image_stars']
               if "crop_box" in data:
                  del data['crop_box']
               if "revision" in data:
                  del data['revision']
               if "dfv" in data:
                  del data['dfv']
               if "final_trim" in data:
                  del data['final_trim']
               if station_id == 'AMS64':
                  print("AMS64:", data['sd_video_file'])
               all_obs.append(data)

      #update_redis_obs(date, all_obs)
      all_obs = json.loads(json.dumps(all_obs,cls=DecimalEncoder))
      save_json_file(obs_file, all_obs, True)
      obs_file_zip = obs_file.replace(".json", ".json.gz")  
      os.system("gzip -k -f " + obs_file )
      print("SAVED:", obs_file)
      if cloud_copy == 1:
         cloud_obs_file = obs_file_zip.replace("/mnt/ams2/", "/mnt/archive.allsky.tv/")
         os.system("cp " + obs_file_zip + " " + cloud_obs_file)
         print("cp " + obs_file_zip + " " + cloud_obs_file)

   if do_events == 1:
      #os.system("rm " + event_file ) 
      # get all of the events for this day 
      events = search_events(dynamodb, date, stations, 1)
      ev_keys = {}
      deleted_events = {}
      for event in events:
         ev_keys[event['event_id']] = event
         if "stations" not in event:
            print("EVENT MISSING STATIONS!", event)
            #input("wait")
            continue
         for i in range(0, len(event['stations'])):
            st = event['stations'][i]
            vid = event['files'][i]
            obs_key = st + "_" + vid
            if obs_key in del_keys:
               print("THIS EVENT OBS HAS BEEN DELETED!", obs_key, event.keys())
               if event['event_id'] not in deleted_events:
                  delete_event(dynamodb, event['event_id'], date)

                  deleted_events[event['event_id']] = 1

      for evid in deleted_events:
         print("DELETE THIS EVENT!", evid, ev_keys[evid].keys() )
      events = sorted(events, key=lambda x: (x['event_id']), reverse=False) 
      events = json.loads(json.dumps(events,cls=DecimalEncoder))
      save_json_file(event_file, events, True)
      print("Saved:", event_file)
      cloud_event_file = event_file.replace("/mnt/f/", "/mnt/archive.allsky.tv/")
      os.system("cp " + event_file + " " + cloud_event_file)
      print("saved" + cloud_event_file)

def starttime_from_file( filename):
   (f_datetime, cam, f_date_str,fy,fmon,fd, fh, fm, fs) = convert_filename_to_date_cam(filename)
   trim_num = get_trim_num(filename)
   extra_sec = int(trim_num) / 25
   extra_sec += 2
   event_start_time = f_datetime + dt.timedelta(0,extra_sec)
   return(event_start_time)

def update_redis_obs(date, obs_data):

    rkeys = r.keys("OI:*" + date + "*")
    for key in rkeys:
       r.delete(key)
        

    print("TOTAL OBS IN FILE:", len(obs_data))
    if True:
      c = 0
      for item in obs_data:
          if True:
            if "deleted" in item:
               continue
            if "dur" in item:
               dur = float(item['dur'])
            else:
               dur = 0
            if "sync_status" in item:
               station_sync = item['sync_status']
            else:
               station_sync = 0
            if "event_id" in item:
               event_id = item['event_id']
            else:
               event_id = 0
            if "revision" in item:
               revision = item['revision']
            else:
               revision = 0
            if "calib" in item:
               calib = item['calib']
               res = 0
               stars = 0
               if len(calib) > 0:
                  res = float(calib[-1])
                  stars = int(calib[-2])
            else:
               prev_vid = 0
               res = 9999
               stars = 0
            if "peak_int" in item:
               pi = float(item['peak_int'])
            else:
               pi = 0

            if "event_start_time" in item:
               temp = item['event_start_time'].split(" ")
            else:
               temp = []
            if len(temp) == 2:
               event_time = temp[1]
            else:
               event_time = starttime_from_file(item['sd_video_file'])
               event_time = event_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
               temp = event_time.split(" ")
               if len(temp) == 2:
                  event_time = temp[1]
            key = "OI:" + item['station_id'] + ":" + item['sd_video_file']
            val = {}
            val['ei'] = event_id
            val['t'] = event_time
            val['rv'] = revision
            val['ss'] = station_sync
            val['pi'] = pi
            val['du'] = dur
            val['rs'] = float("{:0.2f}".format(res))
            val['st'] = stars

            r.set(key, json.dumps(val))
            print("SETTING:", c, key)
            c += 1


def delete_events_day(dynamodb, date):
   print("DATE?", date)
   table = dynamodb.Table('x_meteor_event')
   response = table.query(
      KeyConditionExpression='event_day= :date',
      ExpressionAttributeValues={
         ':date': date,
      } 
   )
   event_ids = []
   for item in response['Items']:
      event_ids.append(item['event_id'])
   for event_id in event_ids:

      event_day = event_id[0:8]
      y = event_day[0:4]
      m = event_day[4:6]
      d = event_day[6:8]
      event_day = y + "_" + m + "_" + d

      print(event_day, event_id)
      delete_event(dynamodb, event_day, event_id)


def search_events(dynamodb, date, stations, nocache=0):
   year, mon, day = date.split("_")
   day_dir = "/mnt/f/EVENTS/" + year + "/" + mon + "/" + day + "/"
   dyn_cache = day_dir
   if cfe(dyn_cache, 1) == 0:
      os.makedirs(dyn_cache)

   use_cache = 0
   if cfe(dyn_cache, 1) == 0:
      os.makedirs(dyn_cache)

   # This area should really only be used by the update dyna cache calls


   #use_cache = 0
   all_events = []
   if False:
      r = redis.Redis("allsky-redis.d2eqrc.0001.use1.cache.amazonaws.com", port=6379, decode_responses=True)
      rkey = "E:" + date.replace("_", "") + "*"
      keys = r.keys(rkey)
      for key in keys:
         rval = json.loads(r.get(key))
         all_events.append(rval)   

   if True:
      if dynamodb is None:
         dynamodb = boto3.resource('dynamodb')


      table = dynamodb.Table('x_meteor_event')
      response = table.query(
         KeyConditionExpression='event_day= :date',
         ExpressionAttributeValues={
           ':date': date,
         } , 
         Limit = 100
      )
      for item in response['Items']:
         if "obs" in item:
            del (item['obs'])
         all_events.append(item)
      while 'LastEvaluatedKey' in response:
         response = table.query(
           KeyConditionExpression='event_day= :date',
           ExpressionAttributeValues={
            ':date': date,
           } ,
           Limit=100 ,
           ExclusiveStartKey=response['LastEvaluatedKey']
         )
         for it in response['Items']:
            all_events.append(it)

      #save_json_file(dc_file, response['Items'])
   print("ALL EVENTS:", len(all_events))
   return(all_events)



def make_station_clusters(all_stations):
   st_lat_lon = []
   for station_data in all_stations:
      #jc = load_json_file(stc)
      station_id = station_data['station_id']
      if "lat" in station_data:
         try:
            lat = float(station_data['lat'])
            lon = float(station_data['lon'])
         except:
            continue
         if "city" in station_data:
            city = station_data['city']
         else:
            city = ""
         if "alt" in station_data:
            if isinstance(station_data['alt'], str) is True:
               if "meters" in station_data['alt']:
                  station_data['alt'] = station_data['alt'].replace("meters", "")
                  station_data['alt'] = station_data['alt'].replace(" ", "")
                  station_data['alt'] = station_data['alt'].replace("m", "")
            try:
               alt = float(station_data['alt'])
            except:
               alt = 100
            st_lat_lon.append((station_id, lat, lon, alt, city))
         else:
            print("NO ALT FOR THIS STATION?", station_data)
      else:
         print(station_id, "STATION DATA INCOMPLETE!")
   cluster_data = []
   for data in st_lat_lon:
      (station_id, lat, lon, alt, city) = data
      matches = []
      for sdata in st_lat_lon:
         (sid, tlat, tlon, talt, tcity) = sdata
         if sid == station_id :
            continue
         dist = dist_between_two_points(lat, lon, tlat, tlon)
         if dist < 600:
            matches.append((sid, dist))
      cluster_data.append((station_id, lat,lon,alt,city,matches))

   return(cluster_data)

def get_all_obs(dynamodb, date, json_conf):
   all_stations = glob.glob("/mnt/ams2/STATIONS/CONF/*")
   if cfe("/mnt/ams2/STATIONS/CONF/clusters.json") == 0:
      make_station_clusters(all_stations)

def get_rejected_meteors(self, date):
   if True:
      rejects = {}
      #for station_id in self.all_stations:
      #   print(station_id)
      for station_row in all_stations:
         station_id = station_row[0]
         print("DATE:", date)
         temp = search_trash(dynamodb, station_id, date, no_cache=0)
         for obj in temp:

            sd_vid = obj['sd_video_file']
            obs_key = station_id + "_" + sd_vid
            rejects[obs_key] = 1
   return(rejects)

def search_trash(dynamodb, station_id, date, no_cache=0   ):
   if dynamodb is None:
      dynamodb = boto3.resource('dynamodb')
   table = dynamodb.Table('meteor_review_delete')
   print("TRASH:", station_id, date)
   response = table.query(
         KeyConditionExpression='station_id = :station_id AND begins_with(sd_video_file, :date)',
         ExpressionAttributeValues={
            ':station_id': station_id,
            ':date': date,
         }
   )
      #save_json_file(dc_file, response['Items'])
   #reject_dict = {}
   #for item in response['Items']:
   #   st = item['station_id']:
   #   for row in 
   return(response['Items'])

def get_station_deletes(dynamodb, station_id, date ):
   all_items = []
   if dynamodb is None:
      dynamodb = boto3.resource('dynamodb')
   table = dynamodb.Table('meteor_delete')
   print("INPUT:", station_id, date)
   response = table.query(

      KeyConditionExpression='station_id = :station_id AND begins_with(sd_video_file, :date)',
      ExpressionAttributeValues={
         ':station_id': station_id,
         ':date': date,
      } ,
      Limit=100 
   )
   for item in response['Items']:
      all_items.append(item)
   while 'LastEvaluatedKey' in response:
      response = table.query(
         KeyConditionExpression='station_id = :station_id AND begins_with(sd_video_file, :date)',
         ExpressionAttributeValues={
            ':station_id': station_id,
            ':date': date,
         } ,
         Limit=100 ,
         ExclusiveStartKey=response['LastEvaluatedKey']
      )
      for it in response['Items']:
         all_items.append(it)


   print("DELETES FOR ", station_id, len(all_items))
   return(all_items)

def search_obs(dynamodb, station_id, date, no_cache=0):
   all_items = []
   year, mon, day = date.split("_")
   day_dir = "/mnt/f/EVENTS/" + year + "/" + mon + "/" + day + "/"
   dyn_cache = day_dir
   if cfe(dyn_cache, 1) == 0:
      os.makedirs(dyn_cache)

   if True:
      if dynamodb is None:
         dynamodb = boto3.resource('dynamodb')
      table = dynamodb.Table('meteor_obs')
      response = table.query(
         KeyConditionExpression='station_id = :station_id AND begins_with(sd_video_file, :date)',
         ExpressionAttributeValues={
            ':station_id': station_id,
            ':date': date,
         } ,
         Limit=100 
      )
      for item in response['Items']:
         all_items.append(item)
      while 'LastEvaluatedKey' in response:
         response = table.query(
           KeyConditionExpression='station_id = :station_id AND begins_with(sd_video_file, :date)',
           ExpressionAttributeValues={
            ':station_id': station_id,
            ':date': date,
           } ,
           Limit=100 ,
           ExclusiveStartKey=response['LastEvaluatedKey']
         )
         for it in response['Items']:
            all_items.append(it)

      #save_json_file(dc_file, response['Items'])
      print("SEARCH OBS:", station_id, date, len(all_items))
      return(all_items)


def get_event(dynamodb, event_id, nocache=1):
   year = event_id[0:4]
   mon = event_id[4:6]
   dom = event_id[6:8]
   date = year + "_" + mon + "_" + dom


   day_dir = "/mnt/f/EVENTS/" + year + "/" + mon + "/" + dom + "/"
   dyn_cache = day_dir
   if cfe(dyn_cache, 1) == 0:
      os.makedirs(dyn_cache)

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
      if hours_old < 4:
         use_cache = 1   
   if nocache == 0:
      use_cache = 0 

   if use_cache == 1:
      evs = load_json_file(dc_file)
      for ev in evs:
         if ev['event_id'] == event_id:
            return(ev)

   if dynamodb is None:
      dynamodb = boto3.resource('dynamodb')


   table = dynamodb.Table('x_meteor_event')
   event_day = event_id[0:8]
   y = event_day[0:4]
   m = event_day[4:6]
   d = event_day[6:8]
   event_day = y + "_" + m + "_" + d
   response = table.query(
      KeyConditionExpression='event_day= :event_day AND event_id= :event_id',
      ExpressionAttributeValues={
         ':event_day': event_day,
         ':event_id': event_id,
      } 
   )

   if len(response['Items']) > 0:
      return(response['Items'][0])
   else:
      return([])

def get_obs(station_id, sd_video_file):
   json_conf = load_json_file("../conf/as6.json")
   admin_station_id = json_conf['site']['ams_id']
   api_key = json_conf['api_key']
   if True:
      url = API_URL + "?cmd=get_obs&station_id=" + station_id + "&sd_video_file=" + sd_video_file 
     # + "&station_id=" + station_id + "&api_key=" + api_key
      print("GET OBS URL:", url) 
      response = requests.get(url)
      content = response.content.decode()
      content = content.replace("\\", "")
      if content[0] == "\"":
         content = content[1:]
         content = content[0:-1]
      if "not found" in content:
         data = {}
         data['aws_status'] = False
         print("FETCH FAILED")
      else:
         data = json.loads(content)
         data['aws_status'] = True
         print("FETCH GOOD")
      return(data)

def get_obs_old2(dynamodb, station_id, sd_video_file):
   date= sd_video_file[0:10]
   year, mon, day = date.split("_")
   obs_data = None
   day_dir = "/mnt/f/EVENTS/" + year + "/" + mon + "/" + day + "/"
   cl_day_dir = "/mnt/archive.allsky.tv/EVENTS/" + year + "/" + mon + "/" + day + "/"
   dyn_cache = day_dir
   all_obs_file = dyn_cache + date + "_ALL_OBS.json"   
   all_obs_cloud_file = cl_day_dir + date +"_ALL_OBS.json"   
   if cfe(dyn_cache, 1) == 0:
      os.makedirs(dyn_cache)
   if cfe(all_obs_file) == 0:
      if cfe(all_obs_cloud_file) == 1:
         os.system("cp " + all_obs_cloud_file + " " + all_obs_file) 

   use_cache = 0
   if cfe(dyn_cache, 1) == 0:
      os.makedirs(dyn_cache)
   if cfe(all_obs_file) == 0:
      print("NO OBS FILE!", all_obs_file)
      print(all_obs_cloud_file)
      exit()

   aod = load_json_file(all_obs_file)
   for row in aod:
      if row['station_id'] == station_id and row['sd_video_file'] == sd_video_file:
         obs_data = row
   return(obs_data)

def get_obs_old():
   if cfe(dc_file) == 1:
      size, tdiff = get_file_info(dc_file)
      if tdiff / 60 < 4:
         dc_obs = load_json_file(dc_file)
         for obs in dc_obs:
            
            if obs['sd_video_file'] == sd_video_file:
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


def sync_db_day_new(dynamodb, station_id, event_day):
   dyn_obs_index = select_obs_files(dynamodb, station_id, event_day)

def sync_db_day(dynamodb, station_id, day):
   # remove the cache 
   #cmd = "rm /mnt/ams2/DYCACHE/*.json"
   #os.system(cmd)
   #cmd = "./DynaDB.py cd " + day 
   #os.system(cmd)

   db_meteors = {}
   items = search_obs(dynamodb, station_id, day, 1)
   for item in items:
      db_meteors[item['sd_video_file']] = {}
      db_meteors[item['sd_video_file']]['dyna'] = 1
      if "meteor_frame_data" not in item:
         db_meteors[item['sd_video_file']]['meteor_frame_data'] = item['meteor_frame_data']
      else:
         db_meteors[item['sd_video_file']]['meteor_frame_data'] = []
      if "revision" not in item:
         db_meteors[item['sd_video_file']]['revision'] = 1
      else:
         db_meteors[item['sd_video_file']]['revision'] = item['revision']
   #   if "meteor_frame_data" in item:

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
         mjr = {}
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
         meteor_file = dkey.replace(".mp4", ".json")
         video_file = dkey
         delete_obs(dynamodb, station_id, video_file)

   # Do all of the local meteors exist in the remote db?
   # if not add them in
   for lkey in local_meteors:
      if lkey not in db_meteors:
         meteor_file = lkey.replace(".mp4", ".json")
         insert_meteor_obs(dynamodb, station_id, meteor_file)
      else:
         if len(db_meteors[lkey]['meteor_frame_data']) == 0:
            print("MISSING MFD!", lkey)

   # Do all of the revision numbers match between the local and db meteors?
   # If the local revision is higher than the remote, we need to push the updates to the DB
   # BUT if the DB revision is higher than the local, we need to pull the MFD from the db and update the meteor objects (populate reduced file and manual overrides in mj) *** The PULL part is only needed once we have remote editing enabled. *** 
   for lkey in local_meteors:
      if lkey not in db_meteors:
         print(lkey, "IGNORE: is not in the DB yet. But should be added in this run." )
      else:
         force = 0
         if local_meteors[lkey]['revision'] > db_meteors[lkey]['revision'] or force == 1:
          
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


def update_meteor_obs(dynamodb, station_id, sd_video_file, obs_data=None):

   if obs_data is None:
      day = sd_video_file[0:10]
      jsf = "/mnt/ams2/meteors/" + day + "/" + sd_video_file
      jsf = jsf.replace(".mp4", ".json")
      jsfr = jsf.replace(".json", "-reduced.json")
      mj = load_json_file(jsf)
      mjr = load_json_file(jsfr)
      obs_data = {}
      obs_data['revision'] = mj['revision']
      obs_data['meteor_frame_data'] = mjr['meteor_frame_data']
      obs_data['last_update'] = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
      if "final_vid" in mj:
         print("ADD FINAL DATA!")
         final_vid = mj['final_vid']
         final_vid_fn, xxx = fn_dir(final_vid)
         final_data_file = final_vid.replace(".mp4", ".json")
         final_data = load_json_file(final_data_file)
         obs_data['final_vid'] = final_vid_fn
         obs_data['final_data'] = final_data
      else:
         print("No final data?")



   dmfd = []
   for data in obs_data['meteor_frame_data']:
      (dt, fn, x, y, w, h, oint, ra, dec, az, el) = data
      dmfd.append((dt,float(fn),float(x),float(y),float(w),float(h),float(oint),float(ra),float(dec),float(az),float(el)))
   obs_data['meteor_frame_data'] = dmfd
   if "final_vid" not in obs_data:
      obs_data['final_vid'] = "" 
   if "final_data" not in obs_data:
      obs_data['final_data'] = {} 

   if dynamodb is None:
      dynamodb = boto3.resource('dynamodb')
   table = dynamodb.Table("meteor_obs")
   obs_data = json.loads(json.dumps(obs_data), parse_float=Decimal)
   print("REV:", obs_data['revision'])
   print("ST:", station_id)
   print("F:", sd_video_file)
   if True:
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



def update_event_id(dynamodb, event_id,event_day ):
   table = dynamodb.Table('x_meteor_event')
   response = table.update_item(
      Key = {
         'event_day': event_day ,
         'event_id': event_id
      },
      UpdateExpression="set event_id=:event_id ",
      ExpressionAttributeValues={
         ':event_id': event_id
      },
      ReturnValues="UPDATED_NEW"
   )

def update_dyna_table(dynamodb, table_name, keys, update_values):
   # fields/keys must exist before this will work!
   table = dynamodb.Table(table_name)
   update_vals = {}
   update_exp = "set " 
   for k in update_values:
      if update_exp != "set ":
         update_exp += "," 
      update_vals[":" + k] = update_values[k]
      update_exp += k + "=:" + k
   print(table_name)
   print(keys)
   print(update_exp)
   print(update_vals)

   response = table.update_item(
      Key = keys,
      UpdateExpression= update_exp,
      ExpressionAttributeValues=update_vals,
      ReturnValues="UPDATED_NEW")
   print("R", response)         
      
 
          


   

def update_event_sol(dynamodb, event_id, sol_data, obs_data, status):
   json_conf = load_json_file("../conf/as6.json")
   station_id =json_conf['site']['ams_id']
   api_key =json_conf['api_key']

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

   if "obs" in sol_data:
      del sol_data['obs']
   for key in obs_data:
      for fkey in obs_data[key]:
         
         #obs_data[key][fkey]['calib'][6] = float(obs_data[key][fkey]['calib'][6])
         if key in obs_data:
            if fkey in obs_data[key]:
               if 'calib' in obs_data[key][fkey]:
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
         ':obs_data': []
      },
      ReturnValues="UPDATED_NEW"
   )
         #':obs_data': obs_data,
   print("UPDATED EVENT WITH SOLUTION.")
   url = API_URL + "?recache=1&cmd=get_event&event_id=" + event_id + "&station_id=" + station_id + "&api_key=" + api_key
   print("RECACHE REDIS:", url)
   response = requests.get(url)
   content = response.content.decode()
   content = content.replace("\\", "")
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
   print("UPDATED EVENT WITH SOLUTION.")
   url = API_URL + "?recache=1&cmd=get_event&event_id=" + event_id
   print(url)
   response = requests.get(url)
   content = response.content.decode()
   content = content.replace("\\", "")
   #data = json.loads(content)
   print(content)

   return response

def do_dyna_day(dynamodb, day):
   json_conf = load_json_file("../conf/as6.json")
   # do everything to prep and load meteors
   # to get them ready for solving
   # and then also download event data for this site
   # and update the mse info in the json for each site
   # also sync prev imgs for mse events
   # check if the latest day,dawn,dusk,night stacks have been made. if not run that. 

   mdir = "/mnt/ams2/meteors/" + day + "/" 
   meteor_files = [] 
   red_files = [] 
   temp = os.listdir(mdir)

   if os.path.exists("rf.txt") is False:
      cmd = "./red-fix.py > rf.txt"
      print(cmd)
      os.system(cmd)

   for mf in temp:
      if "json" in mf and "reduced" not in mf:
         meteor_files.append(mf)
      elif "json" in mf and "reduced" in mf:
         red_files.append(mf)

   print("meteor files / reduced files on", day, len(meteor_files), len(red_files))

   # do recal jobs 
   #os.system("./recal.py status all > /home/ams/recal.txt &")

   recal_log_file = "../conf/recal_log.json"
   if os.path.exists(recal_log_file) is False:
      recal = {}
      recal['history'] = {}
      total_recal = True
   else:
      recal = load_json_file(recal_log_file)
      total_recal = False

   now = datetime.now()
   run_time = now.strftime("%Y_%m_%d_%H_%M_%S")   
   #recal['history']['run_time'] = {}
   #if total_recal is True:
   #   print("TOTAL RECAL")
   #   os.system("./recal.py batch_apply_bad all ")


   if cfe("../conf/hsha.txt") == 0:
      os.system("./Process.py hsha")
      os.system("touch ../conf/hsha.txt")
   

   if cfe("dyn.log") == 0:
      dyn_log = {}
   else:
      try:
         dyn_log = load_json_file("dyn.log")
      except:
         dyn_log = {}
   
   today = datetime.now().strftime("%Y_%m_%d")
   if today != day:
      if day not in dyn_log:
         dyn_log[day] = {}
   else:
      dyn_log[day] = {}
   if "reject_masks" not in dyn_log[day] or today == day:
      cmd = "./Process.py reject_masks " + day
      print(cmd)
      os.system(cmd)
   else:
      print("Already rejected masks for this day.", day)
   save_json_file("dyn.log", dyn_log)

   if today != day:
      if "reject_masks" not in dyn_log[day]:
         dyn_log[day]['reject_masks'] = 1

   if "reject_masks" not in dyn_log[day] or today == day:
      cmd = "./Process.py reject_planes " + day
      print(cmd)
      os.system(cmd)
   else:
      print("Already rejected planes for this day.", day)
   save_json_file("dyn.log", dyn_log)


   # reject meteors not matching strict rules
   if len(meteor_files) > 200:
      if today != day:
         if "strict" not in dyn_log[day]:
            dyn_log[day]['strict'] = 1

      if "strict" not in dyn_log[day] or today == day:
         cmd = "python3 ./meteors_strict.py " + day
         print(cmd)
         os.system(cmd)
   else:
      print("Already did strict rules for this day.", day)
   save_json_file("dyn.log", dyn_log)
   
   
   if "confirm" not in dyn_log[day] or today == day:
      cmd = "./Process.py confirm " + day
      print(cmd)
      os.system(cmd)
   else:
      print("already confirmed for this day.", day)
   save_json_file("dyn.log", dyn_log)

   if today != day:
      if "reject_planes" not in dyn_log[day] or today == day:
         dyn_log[day]['reject_planes'] = 1

   if today != day:
      if "confirm" not in dyn_log[day]:
         dyn_log[day]['confirm'] = 1

   if "filter" not in dyn_log[day] or today == day:
      cmd = "python3 Filter.py fd " + day
      print(cmd)
      #os.system(cmd)
   else:
      print("already filtered for this day.", day)

   if today != day:
      if "filter" not in dyn_log[day]:
         dyn_log[day]['filter'] = 1
   save_json_file("dyn.log", dyn_log)

   cmd = "./Process.py ded " + day
   print(cmd)
   os.system(cmd)

   save_json_file("dyn.log", dyn_log)

   # FAST SYNC
   cmd = "python3 ./Meteor.py 10 " + day
   os.system(cmd)
   save_json_file("dyn.log", dyn_log)

   # sync up dyna deletes with local deletes 
   cmd = "python3 Rec.py del_aws_day " + day 
   print(cmd)
   os.system(cmd) 

   # run my events!
   cmd = "python3 myEvents.py " + day 
   print(cmd)
   os.system(cmd) 

   save_json_file("dyn.log", dyn_log)

   #os.system("./rerun.py")
   # ROI / Meteor Scan Sync
   #cmd = "python3 ./Rec.py rec_day " + day
   #os.system(cmd)


   #cmd = "./DynaDB.py sync_db_day " + day
   #cmd = "/usr/bin/python3 AWS.py sd " + day
   #print(cmd)
   #os.system(cmd)

   #cmd = "./DynaDB.py cd " + day
   #print(cmd)
   #os.system(cmd)

   #cmd = "./Process.py remaster_day " + day
   #print(cmd)
   #os.system(cmd)


   #cmd = "./Process.py sync_prev_all " + day
   #print(cmd)
   #os.system(cmd)

   #cmd = "./Process.py sync_final_day " + day
   #print(cmd)
   #os.system(cmd)

   #cmd = "./DynaDB.py cd " + day
   #print(cmd)
   #os.system(cmd)
   if "ml" in json_conf:
      cmd = "/usr/bin/python3.6 ./AIDay.py " + day
      print(cmd)
      os.system(cmd)

      cmd = "/usr/bin/python3.6 ./AIDay.py all " + " 25 "
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
   year, mon, day = date.split("_")
   day_dir = "/mnt/f/EVENTS/" + year + "/" + mon + "/" + day + "/"
   dyn_cache = day_dir
   if cfe(dyn_cache, 1) == 0:
      os.makedirs(dyn_cache)

   if cfe(dyn_cache, 1) == 0:
      os.makedirs(dyn_cache)
   save_json_file(dyn_cache + date + "_events.json",events, True)
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

   save_json_file(mse_log, mse_db, True)
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
   save_json_file(orbs_file, orbs, True)
   print("saved.", orbs_file)
 
if __name__ == "__main__":



   # check running if it is already running abort.
   running= check_running("DynaDB.py")
   if running > 3:
      print("MORE THAN ", running, "DynaDB.py processes already. We must abort")
      exit()

   try:
      dynamodb = boto3.resource('dynamodb')
   except:
      dynamodb = None
   json_conf = load_json_file("../conf/as6.json")




   cmd = sys.argv[1]
   if cmd == "sync_db_day" or cmd == "sdd":
      station_id = json_conf['site']['ams_id']
      sync_db_day(dynamodb, station_id, sys.argv[2])
   if cmd == "sync_db_day_new" or cmd == "sdd":
      station_id = json_conf['site']['ams_id']
      sync_db_day_new(dynamodb, station_id, sys.argv[2])

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
   if cmd == "update_obs":
      station_id = json_conf['site']['ams_id']
      meteor_file = sys.argv[2]
      update_meteor_obs(dynamodb, station_id, meteor_file)

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

   if cmd == "dedm":
      wild = sys.argv[2]
      files = glob.glob("/mnt/ams2/meteors/" + wild + "*")
      for file in sorted(files):
         day = file.split("/")[-1]
         cmd = "./Process.py ded " + day
         os.system(cmd)

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
   if cmd == "save_conf":
      save_json_conf(dynamodb, json_conf)
   if cmd == "back_load":
      back_loader(dynamodb, json_conf)
   if cmd == "get_all_obs":
      get_all_obs(dynamodb, sys.argv[2], json_conf)
   if cmd == "event_report":
      event_report(dynamodb, r, sys.argv[2])
   if cmd == "get_all_events":
      get_all_events(dynamodb)
   if cmd == "select_obs_files":
      # station_id and then date please
      select_obs_files(dynamodb, sys.argv[2], sys.argv[3])
   if cmd == "update_station":
      # station_id and then date please
      update_station(dynamodb, sys.argv[2], json_conf)
   if cmd == "insert_station":
      # station_id and then date please
      insert_station(dynamodb, sys.argv[2] )
   if cmd == "all_deletes":
      # station_id and then date please
      all_deletes(dynamodb, json_conf)
   if cmd == "delete_events_day":
      # station_id and then date please
      delete_events_day(dynamodb, sys.argv[2])
   if cmd == "purge_auth":
      purge_auth(dynamodb)

   if cmd == "quick_event":
      # station_id and then date please
      quick_event_report(sys.argv[2], dynamodb, json_conf)
   if cmd == "udc":
      if len(sys.argv) > 3:
         utype = sys.argv[3]
      else:
         utype = None
      update_dyna_cache_for_day(dynamodb, sys.argv[2], json_conf, utype)
