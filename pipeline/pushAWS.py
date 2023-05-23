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

def push_station_data(api_key, station_id, json_conf):
   data = {}
   data['station_id'] = json_conf['site']['ams_id']
   data['api_key'] = json_conf['api_key']
   data['lat'] = json_conf['site']['device_lat']
   data['lon'] = json_conf['site']['device_lng']
   data['alt'] = json_conf['site']['device_alt']
   data['last_updated'] = datetime.timestamp(datetime.now())
   json_conf['aws_last_updated'] = data['last_updated']
   save_json_file("../conf/as6.json", json_conf)
   # cameras
   data['cameras'] = []
   cam_ids_nums = {}
   mcps = load_all_mcps()

   for cam_num in json_conf['cameras']:
      dd = int(cam_num.replace("cam", ""))
      cams_id = json_conf['cameras'][cam_num]['cams_id']
      cam_obj = {}
      cam_obj['cam_num'] = dd
      cam_obj['cam_id'] = cams_id 
      cam_obj['calib'] = mcps[cams_id]
      data['cameras'].append(cam_obj)
      #cam_ids_nums[data['cameras'][dd]['cam_id']] = cam_num
   if "operator_city" in json_conf['site']:
      data['city'] = json_conf['site']['operator_city']
   if "operator_country" in json_conf['site']:
      data['country'] = json_conf['site']['operator_country']
   if "operator_email" in json_conf['site']:
      data['email'] = json_conf['site']['operator_email']
   if "mobile" in json_conf['site']:
      data['mobile'] = json_conf['site']['mobile']
   if "obs_name" in json_conf['site']:
      data['obs_name'] = json_conf['site']['obs_name']
   if "operator_name" in json_conf['site']:
      data['operator_name'] = json_conf['site']['operator_name']
   if "photo_credit" in json_conf['site']:
      data['photo_credit'] = json_conf['site']['photo_credit']
   if "operator_state" in json_conf['site']:
      data['op_state'] = json_conf['site']['operator_state']
   if "allsky_username" in json_conf['site']:
      data['username'] = json_conf['site']['allsky_username']

   # add calib info

   #data['calib'] = all_mcps 
   if "ml" in json_conf:
      data['ml'] = json_conf['ml']



   data['cmd'] = "update_station_data"
   data = json.loads(json.dumps(data), parse_float=Decimal)
   os.system("clear")

   print(json.dumps(data))
   headers = {
      'content-type': 'application/json'
   }
   headers = {'Content-type': 'application/json'}


   response = requests.post(API_URL, data=json.dumps(data) , headers=headers)

   print("\n\n\n")
   print("response:", response.content.decode())
   print(data)
   print("END \n\n\n")

def load_all_mcps():

   cal_dir = "/mnt/ams2/cal/"
   mcp_files = os.listdir("/mnt/ams2/cal/")

   all_mcps = {}
   for mcp_file in mcp_files :
      if "multi_poly" in mcp_file: 
         try:
            mcp = load_json_file(cal_dir + mcp_file) 
         except:
            print("Failed to load:", mcp_file)
            continue
      else:
         continue
      mcp_file = mcp_file.replace(".info", "")
      print(mcp_file)
      fn, station, cam = mcp_file.split("-")
      all_mcps[cam] = {}

      #cam_num = cam_ids_nums[cam] 

      print( mcp_file, mcp.keys())
      if "center_az" in mcp:
         all_mcps[cam]['az'] = str(mcp['center_az'])
      if "center_el" in mcp:
         all_mcps[cam]['el'] =  str(mcp['center_el'])
      if "position_angle" in mcp:
         all_mcps[cam]['pos'] =  str(mcp['position_angle'])
      if "pixscale" in mcp:
         all_mcps[cam]['px'] =  str(mcp['pixscale'])
      if "total_stars_used" in mcp:
         all_mcps[cam]['total_stars_used'] =  str(mcp['total_stars_used'])
      if "x_fun" in mcp:
         all_mcps[cam]['x_fun'] =  str(mcp['x_fun'])
      if "y_fun" in mcp:
         all_mcps[cam]['y_fun'] =  str(mcp['y_fun'])
      if "x_fun_fwd" in mcp:
         all_mcps[cam]['x_fun_fwd'] =  str(mcp['x_fun_fwd'])
      if "y_fun" in mcp:
         all_mcps[cam]['y_fun_fwd'] =  str(mcp['y_fun_fwd'])


      if "x_poly" in mcp:
         all_mcps[cam]['x_poly'] = str(mcp['x_poly'])
      if "y_poly" in mcp:
         all_mcps[cam]['y_poly'] = str(mcp['y_poly'])
      if "x_poly_fwd" in mcp:
         all_mcps[cam]['x_poly_fwd'] = str(mcp['x_poly_fwd'])
      if "y_poly_fwd" in mcp:
         all_mcps[cam]['y_poly_fwd'] = str(mcp['y_poly_fwd'])
      if "min_max_x_dist" in mcp:
         all_mcps[cam]['min_max_x_dist'] =  str(mcp['min_max_x_dist'])
      if "min_max_y_dist" in mcp:
         all_mcps[cam]['min_max_y_dist'] =  str(mcp['min_max_y_dist'])
      if "lens_model_datetime" in mcp:
         all_mcps[cam]['lens_model_datetime'] =  str(mcp['lens_model_datetime'])
      if "best_files" in mcp:
          all_mcps[cam]['best_files'] =  str(mcp['best_files'][-10:])
      if "good_files" in mcp:
          all_mcps[cam]['good_files'] =  str(mcp['good_files'][-10:])

      print(station, cam, all_mcps[cam]) 
   return(all_mcps)

def get_meteor_media_sync_status(station_id, sd_vid):
   # determine the current sync status for this meteor.
   # does the meteor exist in dynamo with the right version?
   # is the media fully uploaded to the cloud drive (tiny jpg, prev_jpg, prev_vid, final_vid)
   day = sd_vid[0:10]
   lcdir = "/mnt/ams2/METEOR_SCAN/" + day + "/"
   cloud_dir = "/mnt/archive.allsky.tv/" + station_id + "/METEORS/" + day[0:4] + "/" + day + "/"
   cloud_files = []


   # This will get it from the live file system but takes a long time! 
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

def dict_to_array(dict_data):
   adata = []
   print("DICT DATA:", dict_data)

   for key in dict_data:
      if "obj_id" in dict_data[key]:
         adata.append(dict_data[key])
      else:
         for obj_id in dict_data[key]:
            adata.append(dict_data[key][obj_id])

   return(adata)

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


def make_obs_data(station_id, date, meteor_file,cloud_files=None):
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
   if cloud_files is None:
      sync_status = get_meteor_media_sync_status(station_id, sd_vid)
   else:
      sync_status = cloud_files

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
         if hd_vid is not None:
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
         if isinstance(cp, dict) is True:
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
      if "sd_video_file" in mj:
         sd_vid = mj['sd_video_file'].split("/")[-1]
      else:
         sd_vid = None
      if "hd_trim" in mj:
         if mj['hd_trim'] is not None and mj['hd_trim'] != 0:
            hd_vid = mj['hd_trim'].split("/")[-1]
         else:
            hd_vid = None
      else:
         hd_vid = None
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
         if isinstance(mj['meteor_scan_meteors'], dict) is True:
            print("MSM:", type(mj['meteor_scan_meteors']), mj['meteor_scan_meteors'])
            mj['meteor_scan_meteors'] = dict_to_array(mj['meteor_scan_meteors'])
            save_json_file(meteor_file, mj)

         if len(mj['meteor_scan_meteors']) > 0:
            peak_int = max(mj['meteor_scan_meteors'][0]['oint'])
   if peak_int == 0:
      if "msc_meteors" in mj:
         if isinstance(mj['msc_meteors'], dict) is True:
            print("MSM:", type(mj['msc_meteors']), mj['msc_meteors'])
            mj['msc_meteors'] = dict_to_array(mj['msc_meteors'])
            save_json_file(meteor_file, mj)
         if len(mj['msc_meteors']) > 0:

            if "oint" in mj['msc_meteors'][0]:
               peak_int = max(mj['msc_meteors'][0]['oint'])
      if peak_int == 0:
         # grab peak int from the MFD if it exists
         if mjr is not None:
            if "meteor_frame_data" in mjr:
               peak_int = max([row[-1] for row in mjr['meteor_frame_data']])



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
         #print(mj['multi_station_event']['event_id'] , mj['multi_station_event']['solve_status']) 
         if "event_id" in mj['multi_station_event']:
            event_id = str(mj['multi_station_event']['event_id']) + ":" + str(mj['multi_station_event']['solve_status'])
         else:
            event_id = ""
   else:
      event_id = 0
   if "ffp" in mj:
      ffp = mj['ffp']
   else:
      ffp = {}
   if 'sd' not in ffp and sd_vid is not None:
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
   #if hd_vid is None:
   #   del (obs_data['hd_video_file'])
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
   if len(sys.argv) > 2:
      meteor_file = sys.argv[2]
   if cmd == "push_obs":
      push_obs(api_key, station_id, meteor_file)
   if cmd == "push_station_data":
      push_station_data(api_key, station_id, json_conf)
