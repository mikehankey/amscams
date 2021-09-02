#!/usr/bin/python3
import os
import glob
from decimal import Decimal
import simplejson as json
from datetime import datetime
import math
import requests
from lib.FFFuncs import ffprobe
from lib.PipeUtil import load_json_file, save_json_file,cfe
import sys
#import aws

# TWO TYPES OF PUSH REQUESTS ARE POSSIBLE.
# PUSH OBS and PUSH EVENT
# PUSH OBS REQUESTS ARE ONLY ALLOWED WITH A KEY THAT MATCHES THE STATION'S OR AN ADMIN KEY
# EVENTS ARE ONLY ALLOWED TO BE PUSH WITH ADMIN KEYS
API_URL = "https://kyvegys798.execute-api.us-east-1.amazonaws.com/api/allskyapi"

def get_meteor_media_sync_status(station_id, sd_vid):
   # determine the current sync status for this meteor.
   # does the meteor exist in dynamo with the right version?
   # is the media fully uploaded to the cloud drive (tiny jpg, prev_jpg, prev_vid, final_vid)
   day = sd_vid[0:10]
   lcdir = "/mnt/ams2/METEOR_SCAN/" + day + "/"
   cloud_dir = "/mnt/archive.allsky.tv/" + station_id + "/METEORS/" + day[0:4] + "/" + day + "/"
   cloud_files = []
   if True:
      wild = station_id + "_" + sd_vid.replace(".mp4", "")
      cfs = glob.glob(cloud_dir + wild + "*")
      print("PUSHGLOB:", cloud_dir + wild + "*")
      for cf in cfs:
         el = cf.split("-")
         ext = el[-1]
         if ext == "vid.mp4" :
            ext = el[-2] + "-" + el[-1]
         if ext == "crop.jpg" or ext == "crop.mp4":
            ext = el[-2] + "-" + el[-1]
         cloud_files.append(ext)


      sync_status = cloud_files
      print(sync_status)
      return(sync_status)


def push_obs(api_key,station_id,meteor_file):
   json_conf = load_json_file("../conf/as6.json")
   if "registration" not in json_conf:
      os.system("/usr/bin/python3 Register.py ")
      json_conf = load_json_file("../conf/as6.json")
      if "registration" not in json_conf:
         print("COULD NOT REGISTER THE DEVICE!")
         data = {}
         save_json_file("../conf/registration_failed.json", data)
         exit()

   date = meteor_file[0:10]
   meteor_file = "/mnt/ams2/meteors/" + date + "/" + meteor_file
   if cfe(meteor_file) == 1:
      obs_data = make_obs_data(station_id, date, meteor_file)
   else:
      obs_data = None
      print("No meteor file.", meteor_file)
      return()
   obs_data['station_id'] = station_id
   obs_data['api_key'] = json_conf['api_key']
   obs_data['cmd'] = "put_obs"
   obs_data = json.loads(json.dumps(obs_data), parse_float=Decimal)
   headers = {
      'content-type': 'application/json'
   }
   #aws_post_data = json.loads(json.dumps(obs_data), parse_float=Decimal) 
   headers = {'Content-type': 'application/json'}
   
   print(obs_data)
   response = requests.post(API_URL, data=json.dumps(obs_data) , headers=headers)
   print("response:", response.content.decode())
   #response = requests.get("https://kyvegys798.execute-api.us-east-1.amazonaws.com/api/allskyapi?cmd=get_event&event_date=2021_04_23&event_id=20210423_013032")


def make_obs_data(station_id, date, meteor_file):
   update_time = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
   mfn = meteor_file.split("/")[-1]


   #cloud_index_file = "/mnt/ams2/METEOR_SCAN/DATA/cloud_index_" + mfn[0:7] + ".json" 
   #input(cloud_index_file)
   #if cfe(cloud_index_file) == 1 :
   #   cloud_index = load_json_file(cloud_index_file)
   #   ci_root_file = station_id + "_" + mfn.replace(".json", "")
   #   ci_root_file = ci_root_file.replace(".mp4", "")
   #   if ci_root_file in cloud_index:
   #      sync_status = sorted(list(set(cloud_index[ci_root_file]['cloud_files'])))
   #   else:
   #      sync_status = []
   #   print(ci_root_file, sync_status)
   #else:
   #   cloud_index = {}
   #   print("NO CLOUD_INDEX", cloud_index_file)
   sd_vid = mfn.replace(".json", ".mp4")
   sync_status = get_meteor_media_sync_status(station_id, sd_vid)

   print("SYNC STATUS:", sync_status)

   if cfe(meteor_file) == 1:
      red_file = meteor_file.replace(".json", "-reduced.json")
      mfn = meteor_file.split("/")[-1]
      mdir = meteor_file.replace(mfn, "")
      try:
         mj = load_json_file(meteor_file)
      except:
         return({})
      if "revision" not in mj:
         mj['revision'] = 1

      reprobe = 0
      if "ffp" not in mj:
         reprobe = 1
      elif "sd" not in mj['ffp']:
         reprobe = 1
      elif "hd" not in mj['ffp']:
         reprobe = 1
      elif mj['ffp']['sd'][0] == 0:
         reprobe = 1

      if reprobe == 1:
         if "sd_video_file" in mj:
            sd_vid = mj['sd_video_file']
         else: 
            sd_vid = None
         if "hd_trim" in mj:
            hd_vid = mj['hd_trim']
         else:
            hd_vid = None
         ffp = {}
         sd_start = None
         if cfe(hd_vid) == 1:
            ffp['hd'] = ffprobe(hd_vid)
         else:
            hd_vid = None
         if sd_vid is not None:
            if cfe(sd_vid) == 1:
               ffp['sd'] = ffprobe(sd_vid)
         mj['ffp'] = ffp
         save_json_file(meteor_file, mj)



      if "cp" in mj:
         cp = mj['cp']
         if type(cp) == "dict":
            if "total_res_px" not in cp:
               cp['total_res_px'] = 9999
            if "cat_image_stars" not in cp:
               cp['cat_image_stars'] = []
            if math.isnan(cp['total_res_px']):
               cp['total_res_px'] = 9999
         if cp is not None and cp != 0:
            calib = [cp['ra_center'], cp['dec_center'], cp['center_az'], cp['center_el'], cp['position_angle'], cp['pixscale'], float(len(cp['cat_image_stars'])), float(cp['total_res_px'])]
         else:
            calib = [] 
      else:
         calib = []
      if cfe(red_file) == 1:
         mjr = load_json_file(red_file)
      else:
         mjr = {}
      sd_vid = mj['sd_video_file'].split("/")[-1]
      hd_vid = mj['hd_trim'].split("/")[-1]
      if "meteor_frame_data" in mjr:
         if len(mjr['meteor_frame_data']) > 0:
            meteor_frame_data = mjr['meteor_frame_data']
            duration = len(mjr['meteor_frame_data']) / 25
            event_start_time = mjr['meteor_frame_data'][0][0]
         else:
            meteor_frame_data = []
            event_start_time = ""
            duration = 99
      else:
         meteor_frame_data = []
         event_start_time = ""
         duration = 99
   else:
      print("BAD FILE:", meteor_file)
      return()

   crop_box = [0,0,0,0]
   if "crop_box" in mj:
      crop_box = mj['crop_box']
   if "roi" in mj:
      roi = mj['roi']
   else:
      roi = [0,0,0,0]

   if "hd_roi" in mj:
      hd_roi = mj['hd_roi']
   else:
      hd_roi = [0,0,0,0]
   if "best_meteor" in mj:
      peak_int = max(mj['best_meteor']['oint'])
   else:
      peak_int = 0
   if peak_int == 0:
      if "meteor_scan_meteors" in mj:
         if len(mj['meteor_scan_meteors']) > 0:
            peak_int = max(mj['meteor_scan_meteors'][0]['oint'])
   if peak_int == 0:
      if "msc_meteors" in mj:
         if len(mj['msc_meteors']) > 0:
            peak_int = max(mj['msc_meteors'][0]['oint'])



   if "revision" in mj:
      revision = mj['revision']
   else:
      revision = 1
   mfn = meteor_file.split("/")[-1].replace(".json", "")
   if "dfv" in mj:
      dfv = mj['dfv']
   else:
      dfv = 1
   if "cp" in mj:
      if cp is not None and cp != 0:
         if "cat_image_stars" in mj['cp']:
            cat_image_stars = mj['cp']['cat_image_stars']
         else:
            cat_image_stars = []
      else:
         cat_image_stars = []
   else:
      cat_image_stars = []
   if "multi_station_event" in mj:
      if mj['multi_station_event'] != 0:
         if "solve_status" not in mj['multi_station_event']:
            mj['multi_station_event']['solve_status'] = "UNSOLVED"
         print(mj['multi_station_event']['event_id'] , mj['multi_station_event']['solve_status']) 
         event_id = str(mj['multi_station_event']['event_id']) + ":" + str(mj['multi_station_event']['solve_status'])
   else:
      event_id = 0
   if "ffp" in mj:
      ffp = mj['ffp']
   else:
      ffp = {}
   if 'sd' not in ffp:
      ffp = {}
      ffp['sd'] = ffprobe(sd_vid)
   if 'hd' not in ffp:
      if hd_vid is not None:
         ffp['hd'] = ffprobe(hd_vid)
   if "final_trim" in mj:
      final_trim = mj['final_trim']
   else:
      final_trim = {}


   obs_data = {
      "station_id": station_id,
      "sd_video_file": sd_vid,
      "hd_video_file": hd_vid,
      "event_start_time": event_start_time,
      "event_id": event_id,
      "dur": duration,
      "peak_int": peak_int,
      "calib": calib,
      "crop_box": crop_box,
      "roi": roi,
      "hd_roi": hd_roi,
      "cat_image_stars": cat_image_stars,
      "ffp": ffp,
      "final_trim": final_trim,
      "meteor_frame_data": meteor_frame_data,
      "revision": revision,
      "dfv": dfv,
      "sync_status": sync_status,
      "last_update": update_time
   }
   if "human_points" in mj:
      obs_data['human_points'] = mj['human_points']
   if "hc" in mj:
      obs_data['hc'] = mj['hc']
   else:
      obs_data['hc'] = 0

   #obs_data = json.loads(json.dumps(obs_data), parse_float=Decimal)
   #table = dynamodb.Table('meteor_obs')
   #table.put_item(Item=obs_data)
   #mj['calib'] = calib
   #mj['last_update'] = update_time
   save_json_file(meteor_file, mj)
   return(obs_data)

if __name__ == "__main__":
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
