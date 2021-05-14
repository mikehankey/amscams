#!/usr/bin/python3
from decimal import Decimal
import simplejson as json
from datetime import datetime
import math
import requests
from lib.PipeUtil import load_json_file, save_json_file,cfe
import sys
#import aws

# TWO TYPES OF PUSH REQUESTS ARE POSSIBLE.
# PUSH OBS and PUSH EVENT
# PUSH OBS REQUESTS ARE ONLY ALLOWED WITH A KEY THAT MATCHES THE STATION'S OR AN ADMIN KEY
# EVENTS ARE ONLY ALLOWED TO BE PUSH WITH ADMIN KEYS
API_URL = "https://kyvegys798.execute-api.us-east-1.amazonaws.com/api/allskyapi"

def push_obs(api_key,station_id,meteor_file):
   date = meteor_file[0:10]
   meteor_file = "/mnt/ams2/meteors/" + date + "/" + meteor_file
   if cfe(meteor_file) == 1:
      obs_data = make_obs_data(station_id, date, meteor_file)
   else:
      obs_data = None
      print("No meteor file.", meteor_file)
      return()
   obs_data['cmd'] = "put_obs"
   obs_data['station_id'] = station_id
   obs_data = json.loads(json.dumps(obs_data), parse_float=Decimal)
   headers = {
      'content-type': 'application/json'
   }
   #aws_post_data = json.loads(json.dumps(obs_data), parse_float=Decimal) 
   headers = {'Content-type': 'application/json'}
   response = requests.post(API_URL, data=json.dumps(obs_data) , headers=headers)
   #print(obs_data)
   print(response.content.decode())
   #response = requests.get("https://kyvegys798.execute-api.us-east-1.amazonaws.com/api/allskyapi?cmd=get_event&event_date=2021_04_23&event_id=20210423_013032")
#def push_event(obs_file):


def make_obs_data(station_id, date, meteor_file):
   update_time = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")

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
      sd_vid = mj['sd_video_file'].split("/")[-1]
      hd_vid = mj['hd_trim'].split("/")[-1]
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
   if "revision" in mj:
      revision = mj['revision']
   else:
      revision = 1
   if "sync_status" in mj:
      sync_status = mj['sync_status']
   else:
      sync_status = []
   if "dfv" in mj:
      dfv = mj['dfv']
   else:
      dfv
   if "cat_image_stars" in mj['cp']:
      cat_image_stars = mj['cp']['cat_image_stars']
   else:
      cat_image_stars = []
   if "multi_station_meteor" in mj:
      event_id = mj['multi_station_meteor']
   else:
      event_id = 0

   obs_data = {
      "station_id": station_id,
      "sd_video_file": sd_vid,
      "hd_video_file": hd_vid,
      "event_start_time": event_start_time,
      "event_id": event_id,
      "dur": duration,
      "peak_int": peak_int,
      "calib": calib,
      "cat_image_stars": cat_image_stars,
      "meteor_frame_data": meteor_frame_data,
      "revision": revision,
      "dfv": dfv,
      "sync_status": sync_status,
      "last_update": update_time
   }
   #obs_data = json.loads(json.dumps(obs_data), parse_float=Decimal)
   #table = dynamodb.Table('meteor_obs')
   #table.put_item(Item=obs_data)
   #mj['calib'] = calib
   #mj['last_update'] = update_time
   save_json_file(meteor_file, mj)
   return(obs_data)

json_conf = load_json_file("../conf/as6.json")
if "api_key" in json_conf['site']:
   api_key = json_conf['site']['api_key']
else:
   api_key = None

station_id = json_conf['site']['ams_id']

cmd = sys.argv[1]
meteor_file = sys.argv[2]
if cmd == "push_obs":
   push_obs(api_key, station_id, meteor_file)
