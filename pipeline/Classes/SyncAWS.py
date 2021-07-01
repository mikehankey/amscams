#!/usr/bin/python3
import numpy as np
import os
import glob
from decimal import Decimal
import simplejson as json
from datetime import datetime
import datetime as dt 
import math
import requests
from lib.PipeUtil import load_json_file, save_json_file,cfe
from lib.PipeImage import stack_frames
import sys
import cv2
from lib.FFFuncs import best_crop_size, crop_video, resize_video, splice_video, lower_bitrate, ffprobe
from lib.PipeVideo import load_frames_simple
from pushAWS import make_obs_data, push_obs
#import aws

# TWO TYPES OF PUSH REQUESTS ARE POSSIBLE.
# PUSH OBS and PUSH EVENT
# PUSH OBS REQUESTS ARE ONLY ALLOWED WITH A KEY THAT MATCHES THE STATION'S OR AN ADMIN KEY
# EVENTS ARE ONLY ALLOWED TO BE PUSH WITH ADMIN KEYS
API_URL = "https://kyvegys798.execute-api.us-east-1.amazonaws.com/api/allskyapi"

class SyncAWS():

   def __init__(self, station_id,api_key):
      self.API_URL = "https://kyvegys798.execute-api.us-east-1.amazonaws.com/api/allskyapi"
      self.media_types = ['HD-crop.jpg', 'HD-crop.mp4', 'HD.jpg', 'HD.mp4', 'SD-crop.mp4', 'SD.jpg', 'SD.mp4', 'prev-crop.jpg', 'prev-vid.mp4', 'prev.jpg']
      self.my_sync_profile = "normal"
      self.sync_log_file = "../conf/sync_log.json"
      if cfe(self.sync_log_file) == 1:
         self.sync_log = load_json_file(self.sync_log_file)
      else:
         self.sync_log = {} 
      self.cloud_policy = {}
      self.json_conf = load_json_file("../conf/as6.json")
      if "registration" not in self.json_conf:
         os.system("python3 Register.py")
      self.json_conf = load_json_file("../conf/as6.json")
      self.cloud_policy['non_confirmed'] = {}
      self.cloud_policy['confirmed'] = {}
      self.cloud_policy['non_confirmed']['none'] = []
      self.cloud_policy['non_confirmed']['low'] = ['prev.jpg', 'prev-crop.jpg', 'SD-crop.mp4']
      self.cloud_policy['non_confirmed']['normal'] = ['prev.jpg', 'prev-crop.jpg', 'SD-crop.mp4', 'SD.mp4', 'SD.jpg']
      self.cloud_policy['confirmed']['none'] = []
      self.cloud_policy['confirmed']['low'] = ['prev.jpg', 'prev-crop.jpg', 'SD-crop.mp4', 'SD.mp4', 'SD.jpg', 'HD-crop.mp4', 'HD-crop.jpg']
      self.cloud_policy['confirmed']['normal'] = ['prev.jpg', 'prev-crop.jpg', 'SD-crop.mp4', 'SD.mp4', 'SD.jpg', 'HD-crop.mp4', 'HD-crop.jpg', 'HD.jpg', 'HD.mp4']
      self.TINY_W = 256
      self.TINY_H = 144
      self.BIT_RATE = 30
      self.JPG_QUALITY = 60
      self.FSD_W = 640
      self.FSD_H = 360
      self.PREV_W = 320
      self.PREV_H = 180
      self.today = dt.datetime.now().strftime("%Y_%m_%d")
      self.station_id = station_id
      self.api_key = api_key
      self.mdirs = []
      self.mfiles = []
      self.AWS_DIR = "/mnt/ams2/AWS/"
      self.my_policy = None
      if cfe(self.AWS_DIR,1) == 0:
         os.makedirs(self.AWS_DIR)

  

   def rebuild_meteor_index(self,):
      mdirs = self.get_mdirs()

   def get_mdirs(self):
      temp = glob.glob("/mnt/ams2/meteors/*")
      for md in temp:
         if cfe(md, 1) == 1:
            self.mdirs.append(md)

   def get_mfiles(self, mdir):
      self.mfiles = []
      temp = glob.glob(mdir + "/*.json")
      for json_file in temp:
          if "reduced" not in json_file and "calparams" not in json_file and "manual" not in json_file and "starmerge" not in json_file and "master" not in json_file:
            vfn = json_file.split("/")[-1].replace(".json", ".mp4")
            print("JSF:", json_file) 
            self.mfiles.append(vfn)

   def push_obs_OLD(self, api_key,station_id,meteor_file,mj=None):
      # USE FUNCTION INSIDE pushAWS.py NOT THIS ONE
      date = meteor_file[0:10]
      if "sd_video_file" not in mj:
         return()
      obs_data = self.make_obs_data(station_id, meteor_file,mj)
      obs_data['cmd'] = "put_obs"
      obs_data['station_id'] = station_id
      aws_post_data = {
         "body": json.dumps(obs_data)
      }     
      headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
      print(json.dumps(obs_data))
      headers = {'Content-type': 'application/json'}
      response = requests.post(API_URL, data=json.dumps(obs_data) , headers=headers)
      #response = requests.post(API_URL, json.dumps(obs_data) )

      print(response.content.decode())

   
   def purge_deleted_cloud_files(self, day):
      mdir = "/mnt/ams2/meteors/" + day + "/" 
      self.get_mfiles(mdir)
      cloud_files = glob.glob(mdir + "cloud_files/*")
      cloud_stage_files = glob.glob(mdir + "cloud_stage/*")
      print(mdir + "cloud_files/*")
      good_roots = []
      for mf in sorted(self.mfiles):
         el = mf.split("-")
         root = el[0]
         good_roots.append(self.station_id + "_" + root)
         print(self.station_id + "_" + root)
      pr = 0
      deleted = 0
      for cf in sorted(cloud_stage_files):
         cfn = cf.split("/")[-1]
         el = cfn.split("-")
         root = el[0]
         if root in good_roots:
            print("GOOD", root)
         else:
            print("BAD:", root)
            cmd = "rm " + cf
            print(cmd)
            os.system(cmd)

      for cf in sorted(cloud_files):
         cfn = cf.split("/")[-1]
         el = cfn.split("-")
         root = el[0]
         if "prev.jpg" in cfn:
            pr += 1
         if root in good_roots:
            print("GOOD", root)
         else:
            print("BAD:", root)
            cmd = "rm " + cf
            print(cmd)
            os.system(cmd)
            deleted += 1
      self.cloud_files = cloud_files 
      if deleted > 0:
         year = day[0:4]
         lcdir = "/mnt/ams2/meteors/" + day + "/cloud_files/"
         year = day[0:4]
         cloud_dir = "/mnt/archive.allsky.tv/" + self.station_id + "/METEORS/" + year + "/" + day + "/"
         #cmd = "rsync -av " + lcdir + " " + cloud_dir + " --delete "
         #print("NEED TO RESYNC CLOUD DIR!")
         #print(cmd)
         #os.system(cmd)
   


   def get_meteor_media_sync_status(self, sd_vid, cfs = []):
      # determine the current sync status for this meteor. 
      # does the meteor exist in dynamo with the right version?
      # is the media fully uploaded to the cloud drive (tiny jpg, prev_jpg, prev_vid, final_vid)
      day = sd_vid[0:10]
      lcdir = "/mnt/ams2/meteors/" + day + "/cloud_files/"
      cloud_files = []
      if True:
         wild = sd_vid.replace(".mp4", "")
         print("GLOB", lcdir + "/*" + wild  + "*")
         cfs = glob.glob(lcdir + "/*" + wild + "*")
         for cf in cfs:
            el = cf.split("-")
            ext = el[-1]
            if ext == "vid.mp4" :
               ext = el[-2] + "-" + el[-1]
            if ext == "crop.jpg" or ext == "crop.mp4":
               ext = el[-2] + "-" + el[-1]
            cloud_files.append(ext)

      
      sync_status = cloud_files
      return(sync_status)

   def get_obs_edits(self):
      url = API_URL + "?cmd=get_obs_edits&station_id=" + self.station_id + "&api_key=" + self.json_conf['api_key']
      response = requests.get(url)
      content = response.content.decode()
      content = content.replace("\\", "")
      if content[0] == "\"":
         content = content[1:]
         content = content[0:-1]
      if "not found" in content:
         data = {}
         data['aws_status'] = False
      else:
         data = json.loads(content)
      for row in data['all_vals']:
         remote_key, remote_value = row
         redis_prefix, station_id, sd_video_file, remote_user, remote_command = remote_key.split(":")
         print("REMOTE EDIT:", remote_command, sd_video_file, remote_user, remote_value)
         if "trusted_users" not in self.json_conf:
            self.trusted_users = []
            self.trusted_users.append('mhankey') 
         if remote_user == self.json_conf['username'] or remote_user in self.json_conf['trusted_users']:
            # THIS REMOTE CALL WAS FROM US!
            print("TRUSTED USER!", remote_user)
            if remote_command == "recrop":
               mjf = "/mnt/ams2/meteors/" + sd_video_file[0:10] + "/" + sd_video_file.replace(".mp4", ".json")
               print("UPDATE ROI TO :", remote_value, mjf)
               if cfe(mjf) == 1:
                  try:
                     mj = load_json_file(mjf)
                     mj['roi'] = remote_value
                     mj['hc'] = 1
                     save_json_file(mjf,mj)
                     # now rescan the meteor with the new crop
                     os.system("python3 Meteor.py 3 " + sd_video_file.replace(".mp4", ".json"))
                  except:
                     print("BAD MJ!", mjf)
               else:
                  print("BAD MJ!", mjf)
         

  
   def get_aws_obs(self,sd_vid):
      url = API_URL + "?cmd=get_obs&station_id=" + self.station_id + "&sd_video_file=" + sd_vid
      response = requests.get(url)
      content = response.content.decode()
      content = content.replace("\\", "")
      if content[0] == "\"":
         content = content[1:]
         content = content[0:-1]
      if "not found" in content:
         data = {}
         data['aws_status'] = False
      else:
         data = json.loads(content)
         data['aws_status'] = True
      return(data)

   def delete_aws_meteors(self, day):
      # Need to do 2 things here
      # 1 -- if the meteor is in the AWS DB but not locally, we need to del_commit it from the AWS DB
      # 2 -- if the meteor is tagged as DELETED in AWS, but still exists locally, it means it was deleted from the cloud 
      #    - that means we need to delete it locally and the commit the delete on the cloud end. 
      # TODO / FUTURE -- 1) this needs to be locked down with perms 2) Delete commits should move the deleted data to trash. 

      
      url = self.API_URL + "?cmd=get_obs_for_day&station_id=" + self.station_id + "&day=" + day
      response = requests.get(url)
      content = response.content.decode()
      content = content.replace("\\", "")
      print(content)
      if "nothing" not in content:
         jdata = json.loads(content)
      else: 
         jdata = {}
         jdata['all_vals'] = []
         jdata['total_records'] = 0
      if jdata is not None:
         print(jdata)
         data = jdata['all_vals']
      else: 
         data = []
      aws_obs = data
      mdir = "/mnt/ams2/meteors/" + day + "/" 

      # delete AWS meteors that don't exist locally
      for row in data:
         vid = row['vid']
         json_file = vid.replace(".mp4", ".json")
         if cfe(mdir + json_file) == 0:
            print("AWS METEOR EXISTS BUT NOT ON LOCAL STATION. IT MUST BE DELETED?")
            url = API_URL + "?cmd=del_obs_commit&station_id=" + self.station_id + "&sd_video_file=" + vid + "&api_key=" + self.json_conf['api_key']
            print(url)

            response = requests.get(url)
            content = response.content.decode()
            
         else:
            print("AWS METEOR IS GOOD!")
      # delete local meteors that are tagged in AWS as deletes
      url = self.API_URL + "?cmd=get_del_obs&station_id=" + self.station_id + "&date=" + day
      #print(url)
      response = requests.get(url)
      content = response.content.decode()
      content = content.replace("\\", "")
      print(content)
      jdata = json.loads(content)
      data = jdata
      print("DEL:", data)
      need = 0
      for row in data:
         print("NEED TO DELETE", row)
         need += 1
         url = self.API_URL + "?cmd=del_obs_commit&station_id=" + self.station_id + "&sd_video_file=" + row['vid'] + "&api_key=" + self.json_conf['api_key']
         response = requests.get(url)
         content = response.content.decode()
         content = content.replace("\\", "")
         print(content)
         print(url)
         self.delete_local_meteor(row['vid'])
      print("AWS DELETE METEORS DONE.")
      print(len(aws_obs), "AWS METEORS ")
      self.get_mfiles("/mnt/ams2/meteors/" + day + "/")
      print("MF:", self.mfiles)
      print(len(self.mfiles), "LOCAL STATION METEORS")
      for mf in self.mfiles:
         mff = "/mnt/ams2/meteors/" + day + "/" + mf.replace(".mp4", ".json") 
         if cfe(mff) == 1:
            print("JSON YES", mf)
         else:
            print("JSON NO", mf)
      if need > 0:
         os.system("./Process.py purge_meteors")

   def delete_local_meteor(self, sd_video_file):
      resp = {}
      json_conf = load_json_file("../conf/as6.json")
      amsid = self.station_id
      print("VID:", sd_video_file)
      delete_log = "/mnt/ams2/SD/proc2/json/" + amsid + ".del"
      if cfe(delete_log) == 1:
         try:
            del_data = load_json_file(delete_log)
         except:
            del_data = {}
      else:
         del_data = {}
      el = sd_video_file.split(".")
      base = el[0]
      del_data[base] = 1

      save_json_file(delete_log, del_data)
      print("SAVED DEL LOG:", delete_log)

   def sync_meteor(self, sd_vid):
     print("SYNC METEOR:", sd_vid)
     aws_sync_needed = 0
     date = sd_vid[0:10]
     mdir = "/mnt/ams2/meteors/" + date + "/" 
     jsf = sd_vid.replace(".mp4", ".json")
     json_file = mdir + jsf
     aws_data = self.get_aws_obs(sd_vid)
     if cfe(mdir + jsf) == 1:
        mj = load_json_file(mdir + jsf)
     else:
        return("METEOR DOES NOT EXIST! DELETE IT FROM THE AWS DB!")
     media_sync_status = self.get_meteor_media_sync_status(sd_vid)
     if "sync_status" not in aws_data:
        aws_data['sync_status'] = []
     print("AWS:", aws_data['sync_status'])

     mj['sync_status'] = media_sync_status

     if "dfv" not in mj:
        mj['dfv'] = 1.0
     if "dfv" not in aws_data:
        aws_data['dfv'] = 0
     if "revision" not in mj:
        mj['revision'] = 1
     if "revision" not in aws_data:
        aws_data['revision'] = 0

     print("AWS:", aws_data['sync_status'])
     sync_needed = 0 
     if mj['revision'] > aws_data['revision']:
        sync_needed = 1
     if "sync_status" not in aws_data:
        sync_needed = 1
     else:
        if len(mj['sync_status']) != len(aws_data['sync_status']):
           sync_needed = 1
           print("LOCAL/AWS:", mj['sync_status'], aws_data['sync_status'])

     sync_needed = 1

     print("AWS:", aws_data['sync_status'])
     print("Data Revisions (local/aws):", mj['revision'], aws_data['revision'])
     print("Data Format Version (local/aws):", mj['dfv'], aws_data['dfv'])
     print("SYNC Status (local/aws):", mj['sync_status'], aws_data['sync_status'])
     #sync_needed = 1
     if mj['revision'] > aws_data['revision'] or mj['dfv'] > aws_data['dfv'] or sync_needed == 1:
        print("WE NEED TO PUSH THIS DATA TO AWS!", sync_needed, jsf)
        push_obs(self.api_key, self.station_id, jsf)
     print("AWS:", aws_data['sync_status'])


   def sync_prev(self, sd_video_file ):
     # SYNC AT LEAST THE PREV FILE IF IT EXISTS & MAKE IT IF IT DOES NOT
     date = sd_video_file[0:10]
     mdir = "/mnt/ams2/meteors/" + date + "/" 
     if cfe(mdir + "cloud_files", 1) == 0:
        os.makedirs(mdir + "cloud_files")
     prev_file = mdir + "cloud_files/" + self.station_id + "_" + sd_video_file.replace(".mp4", "-prev.jpg")
     cloud_prev = "/mnt/archive.allsky.tv/" + self.station_id + "/METEORS/" + date[0:4] + "/" + date + "/" + self.station_id + "_" + sd_video_file.replace(".mp4", "-prev.jpg") 
     print("PREV:", prev_file)
     print("CL PREV:", cloud_prev)
     if cfe(prev_file) == 0:
        stack_file = sd_video_file.replace(".mp4", "-stacked.jpg")
        if cfe(mdir + stack_file) == 1:
           img = cv2.imread(mdir + stack_file)
           img = cv2.resize(img, (self.PREV_W, self.PREV_H))
           cv2.imwrite(prev_file, img) 
        else:
           print("NO STACK FILE:", mdir + stack_file)
     if cfe(cloud_prev) == 0:
        print("NO CLOUD PREV")
        cmd = "cp " + prev_file + " " + cloud_prev
        print(cmd)
        os.system(cmd)
     else:
        print("cloud prev already xists? " + cloud_prev)

   def find_hd_crop_area(self, mj):
      hdxs = []
      hdys = []
      hdmx = 1920 / int(mj['ffp']['sd'][0])
      hdmy = 1080 / int(mj['ffp']['sd'][1])
      if "best_meteor" not in mj:
         return([0,0,0,0])
      for i in range(0, len(mj['best_meteor']['oxs'])):
         hdxs.append(mj['best_meteor']['oxs'][i]*hdmx)
         hdys.append(mj['best_meteor']['oys'][i]*hdmy)
      mx = np.mean(hdxs)
      my = np.mean(hdys)
      bcw, bch = best_crop_size(hdxs, hdys, 1920,1080)
      x1 = int(mx - (bcw / 2))
      y1 = int(my - (bch / 2))
      x2 = int(mx + (bcw / 2))
      y2 = int(my + (bch / 2))
      if x1 < 0:
         x1 = 0
         x2 = x1 + bcw
      if y1 < 0:
         y1 = 0
         y2 = y1 + bch
      if x2 >= 1920:
         x1 = 1919 - bcw
         x2 = 1919
      if y2 >= 1920:
         y1 = 1079 - bch
         y2 = 1079
      return(x1,y1,x2,y2)

   def OLD_set_cloud_policy(self):
      """
         CLOUD POLICY RULES

         NON CONFIRMED METEORS: For new meteors that come into the system what media do you want to upload? 

         payload: none  -- NO media files are sent to the server only text
         payload: tiny -- only 1 tiny preview thumb is sent to the server
            AMS1_2021_05_02_00_42_00_000_010004-trim-0439-tiny.jpg

         payload: minimal - 1 prev jpg and 1 prev crop 
            AMS1_2021_05_02_00_42_00_000_010004-trim-0439-prev.jpg
            AMS1_2021_05_02_00_42_00_000_010004-trim-0439-prev-crop.jpg

         payload: full - 1 prev jpg and 1 prev crop and the double trimmed SD video
            AMS1_2021_05_02_00_42_00_000_010004-trim-0439-prev.jpg
            AMS1_2021_05_02_00_42_00_000_010004-trim-0439-prev-crop.jpg
            AMS1_2021_05_02_00_42_00_000_010004-trim-0439-SD.mp4

         CONFIRMED: Once a meteor has been confirmed via human or multi-station event what media do you want to upload? 

         payload: minimal (2 prev jpgs, SD vid, HD crop vid)
            AMS1_2021_05_02_00_42_00_000_010004-trim-0439-prev.jpg
            AMS1_2021_05_02_00_42_00_000_010004-trim-0439-prev-crop.jpg
            AMS1_2021_05_02_00_42_00_000_010004-trim-0439-SD.mp4
            AMS1_2021_05_02_00_42_00_000_010004-trim-0439-HD-crop.mp4  

         payload: full (1 tiny jpg 2 prev jpgs, SD vid, HD crop vid, HD VID)
            AMS1_2021_05_02_00_42_00_000_010004-trim-0439-tiny.jpg
            AMS1_2021_05_02_00_42_00_000_010004-trim-0439-prev.jpg
            AMS1_2021_05_02_00_42_00_000_010004-trim-0439-prev-crop.jpg
            AMS1_2021_05_02_00_42_00_000_010004-trim-0439-SD.mp4
            AMS1_2021_05_02_00_42_00_000_010004-trim-0439-HD-crop.mp4  
            AMS1_2021_05_02_00_42_00_000_010004-trim-0439-HD.mp4       

      """

      if self.my_policy is None:
         self.my_policy = {}
         self.my_policy['non_confirmed'] = "full"
         self.my_policy['confirmed'] = "full"
         self.my_policy['max_detect_thresh'] = "100"
         self.my_policy['exception_override_dates'] = ["08-12", "08-13", "12-13", "12-14"]
         self.cloud_policy = {
               "non_confirmed" : {
                  "nocloud": {
                     "file_types": []
                  },
                  "minimal": {
                     "file_types": ["prev.jpg", "prev-crop.jpg"]
                  },
                  "full": {
                     "file_types": ["prev.jpg", "prev-crop.jpg", "SD.mp4"]
                  },
               },
               "confirmed" : {
                  "nocloud": {
                     "file_types": []
                  },
                  "minimal": {
                     "file_types": ["prev.jpg", "prev-crop.jpg", "SD.mp4", "SD-crop.mp4", "SD.jpg", "HD-crop.mp4", "HD-crop.jpg"]
                  },
                  "full": {
                     "file_types": ["prev.jpg", "prev-crop.jpg", "SD.mp4", "SD.jpg", "SD-crop.mp4", "HD-crop.mp4", "HD-crop.jpg", "HD.mp4", "HD.jpg"]
                  }
               }
            }               

   def find_event(self,frames):
      max_vals = []
      sum_vals = []
      pos_vals = []
      first_frame = None
      for frame in frames:
         bw_frame =  cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
         if first_frame is None:
            first_frame = bw_frame
         sub_frame = cv2.subtract(bw_frame, first_frame)
         sum_val = cv2.sumElems(sub_frame)[0]
         min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(sub_frame)

         pos_vals.append((mx,my))
         sum_vals.append(sum_val)
         max_vals.append(max_val)
      avg_sum_val = np.mean(sum_vals[0:5])
      avg_max_val = np.mean(max_vals[0:5])
      start_frame = None
      end_frame = None
      unq_pos = {}
      peak_val = 0
      peak_frame = 0
      for i in range(0, len(sum_vals)):
         sdiff = sum_vals[i] / avg_sum_val
         mdiff = max_vals[i] / avg_max_val
         pos_key = str(pos_vals[i][0]) + ":" + str(pos_vals[i][1])
         if pos_key not in unq_pos:
            unq_pos[pos_key] = 1
         else:
            unq_pos[pos_key]  += 1
         if max_vals[i] > peak_val:
            peak_val = max_vals[i]
            peak_frame = i
            desc = "PEAK"
         else:
            desc = ""
         if peak_val != 0:
            after_peak_mdiff = max_vals[i] / peak_val 
         else:
            after_peak_mdiff = 0

         if mdiff > 3 and start_frame is None:
            start_frame = i
            desc += "START:"
         if start_frame is not None and end_frame is None and (unq_pos[pos_key] >= 5 or after_peak_mdiff <= .22):
            end_frame = i
            desc += "END"
         print(i, desc, sum_vals[i], max_vals[i], pos_vals[i], sdiff, mdiff, unq_pos[pos_key], after_peak_mdiff)
      print(start_frame, end_frame)
      return(start_frame, end_frame)

   def get_local_media_day(self,day):
      csdir = "/mnt/ams2/meteors/" + day + "/cloud_stage/"
      cfdir = "/mnt/ams2/meteors/" + day + "/cloud_files/"
      csf = glob.glob(csdir + "*")
      cff = glob.glob(cfdir + "*")
      all_med = csf + cff
      local_media = {}
      for mf in all_med:
         mf = mf.replace(self.station_id + "_", "")
         mfn = mf.split("/")[-1]
         el = mfn.split("-")
         if "crop" in el[-1] or "vid" in el[-1]:
            ext = el[-2] + "-" + el[-1]
         else:
            ext = el[-1]
         root = mfn.replace("-" + ext, "")
         if root not in local_media:
            local_media[root] = []
         print(root, ext)
         local_media[root].append(ext)
      for root in sorted(local_media.keys()):
         print(root, sorted(local_media[root]))

      return(local_media)

   def sync_meteor_wild(self, wild):
      meteor_dirs = []
      mdirs = glob.glob("/mnt/ams2/meteors/" + wild + "*")
      for mdir in sorted(mdirs, reverse=True):
         if cfe(mdir,1) == 1:
            meteor_dirs.append(mdir)
      for md in meteor_dirs:
         day = md.split("/")[-1]
         self.sync_meteor_day(day)

   def sync_meteor_day_data_only(self, day):
      
      mdir = "/mnt/ams2/meteors/" + day + "/"
      self.get_mfiles(mdir)
      for mf in self.mfiles:
         update = 0         
         meteor_file = mf.replace(".mp4", ".json")
         if cfe(mdir + meteor_file) == 1:
            mj = load_json_file(mdir + meteor_file)
            if "ffp" not in mj:
               sd_vid = mj['sd_video_file']
               hd_vid = mj['hd_trim']
               ffp = {}
               sd_start = None
               if cfe(hd_vid) == 1:
                  ffp['hd'] = ffprobe(hd_vid)
               else:
                  hd_vid = None
               if cfe(sd_vid) == 1:
                  ffp['sd'] = ffprobe(sd_vid)
               mj['ffp'] = ffp
               update = 1

            #if "crop_box" not in mj:
            if True:
               x1, y1, x2, y2 = self.find_hd_crop_area(mj)
               mj['crop_box'] = [x1,y1,x2,y2]
               print("CROP:", meteor_file, mj['crop_box'])
               update = 1

            if update == 1:
               save_json_file(mdir + meteor_file, mj)
            push_obs(self.api_key, self.station_id, meteor_file)
         print(mf)


   def sync_meteor_day(self, day):
      # remove deleted meteor cloud media
      self.purge_deleted_cloud_files(day)
      
      # load up the needed vars
      url = API_URL + "?cmd=get_obs_for_day&station_id=" + self.station_id + "&day=" + day
      mdir = "/mnt/ams2/meteors/" + day + "/"
      lcdir_stage = "/mnt/ams2/meteors/" + day + "/cloud_stage/"
      lcdir = "/mnt/ams2/meteors/" + day + "/cloud_files/"
      cloud_dir = "/mnt/archive.allsky.tv/" + self.station_id + "/METEORS/" + day[0:4] + "/" + day + "/"
      cloud_url = "https://archive.allsky.tv/" + self.station_id + "/METEORS/" + day[0:4] + "/" + day + "/"

      # get local meteors for this day
      self.get_mfiles(mdir)

      # check if there are too many meteors for the day. 
      # if more than 80 exist we should abort until the 
      # operator cleans up the station
      # FUTURE: log error message 
      if (len(self.mfiles)) > 90:
         print("There are too many meteors detected for this day!", len(self.mfiles)) 
         print("Clean out the dir before sync can happen!") 
         self.bad_day_filter(day)

      # check to see if a "cloud_files.info" exists in this dir. 
      # if not, the dir is not up to the current standard.  

      response = requests.get(cloud_url + "cloud_files.info")
      content = response.content.decode()
      if "NoSuchKey" in content:
         print("There is no remote cloud files index. make it.")
         cfs = glob.glob(cloud_dir + "*")
         cloud_files = []
         for cf in cfs:
            cloud_files.append(cf.split("/")[-1])
         #print(cloud_dir + "cloud_files.info")
         if cfe(cloud_dir, 1) == 0:
            os.makedirs(cloud_dir)
         save_json_file(cloud_dir + "cloud_files.info", cloud_files)
         print("SAVED:", cloud_dir + "cloud_files.info")
      else:
         cloud_files = json.loads(content)

      # delete meteors inside AWS that no longer exist on the local station
      self.delete_aws_meteors(day)

      # make staging and cloud dirs if they don't exist
      if cfe(lcdir_stage, 1) == 0:
         os.system("mkdir " + lcdir_stage)
      if cfe(lcdir, 1) == 0:
         os.system("mkdir " + lcdir)


      # DETERMINE IF WE NEED TO MAKE MEDIA IMAGES
      # OR CLIP VIDS

      local_media = self.get_local_media_day(day)
      # build local file dict 
      all_files = {}

      # loop over all meteors in the days dir 
      #  and build arrays      
      for mf in self.mfiles:
         fn = mf.split("/")[-1]
         print("SYNC PREV:", fn)
         self.sync_prev(fn)
         print("DONE SYNC PREV")
         root = fn.replace(".mp4", "")
         mjf = mdir + root + ".json"
         print("ROOT IS:", root)
         if root not in all_files:
            print("ROOT AD:", root)
            all_files[root] = {}
         if cfe(mjf) == 1:
            #all_files[root]['mj'] = {}
            try:
               all_files[root]['mj'] = load_json_file(mjf)
            except:
               print("CORUPT JSON!")
               del all_files[root]
               continue
         else:
            all_files[root]['mj'] = {}

         if "revision" in all_files[root]['mj']:
            all_files[root]['local_rev'] = all_files[root]['mj']['revision']
         else:
            all_files[root]['local_rev'] = 1

         if root not in all_files:
            print("ROOT FILE MISSING????")
            print("ROOT IS:", root)
            exit()


         if root in local_media:
            all_files[root]['local_media'] = local_media[root]
            if root in local_media:
               all_files[root]['mj']['sync_status'] = local_media[root]
         else:
            all_files[root]['local_media'] = []
            if "root" in local_media:
               all_files[root]['mj']['sync_status'] = local_media[root]

         all_files[root]['local_file'] = root
         all_files[root]['aws_file'] = {}
         all_files[root]['aws_data'] = {}
         all_files[root]['actions'] = []
         all_files[root]['aws_rev'] = 0
         all_files[root]['local_cloud_files'] = []
         all_files[root]['aws_sync_status'] = []

      # Generate local media where it is missing
      new_media_made = 0
      for root in sorted(all_files.keys()):
         make_media = 0

         if root in local_media:
            all_files[root]['local_media'] = local_media[root]
         else:
            all_files[root]['local_media'] = []
            local_media[root] = []
            make_media = 1

         if len(all_files[root]['local_media']) < len(self.media_types)-1:
            make_media = 1
         if root != all_files[root]['local_file']:
            make_media = 0
            print("THIS FILE SHOULD BE DELETED FROM AWS!")


         if make_media == 1:
            json_file = mdir + root + ".json"
            all_files[root]['mj']['local_media'] = all_files[root]['local_media']
            new_media_made = 1    
            print("MAKE CM ALLFILES:", root, all_files[root])
            #self.make_cloud_media(lcdir_stage, json_file, all_files[root]['mj'])
      if new_media_made == 1:
         local_media = self.get_local_media_day(day)
         for root in local_media:
            if "root" in all_files:
               all_files[root]['local_media'] = local_media[root]

      # get meteors and data already logged in AWS and populate the main dict
      response = requests.get(url)
      content = response.content.decode()
      content = content.replace("\\", "")
      data = json.loads(content)
      mdir = "/mnt/ams2/meteors/" + day + "/" 
      if "all_vals" not in data:
         print("ERROR all_vals missing?", data)
         input()

      for row in data['all_vals']:
         if "vid" not in row:
            print(row)
            print("VID MISSING FROM ROW!")
            exit()
         vid = row['vid']
         root = vid.replace(".mp4", "")
         if root not in all_files:
            all_files[root] = {}
            all_files[root]['aws_file'] = root
            all_files[root]['local_file'] = {}
            all_files[root]['aws_data'] = row
         else:
            all_files[root]['aws_file'] = root
            all_files[root]['aws_data'] = row

      # loop over all local files and determine actions needed
      for root in all_files:
         actions = []
         if all_files[root]['local_file'] == 0:
            all_files[root]['actions'].append( "del_aws_obs")
         elif all_files[root]['aws_file'] == 0:
            all_files[root]['actions'].append("insert_aws_obs")

         if "rv" in all_files[root]['aws_data']:
            all_files[root]['aws_rev'] = all_files[root]['aws_data']['rv']
         else:
            all_files[root]['aws_rev'] = 0
         if "ss" in all_files[root]['aws_data']:
            all_files[root]['aws_sync_status'] = all_files[root]['aws_data']['ss']
         else:
            all_files[root]['aws_sync_status'] = []

         local_sync_status = self.get_meteor_media_sync_status(root + ".mp4") 
         media_missing = self.compare_sync_media(local_sync_status,  all_files[root]['aws_sync_status'])
         if media_missing > 0:
            all_files[root]['media_sync_needed'] = 1
         else:
            all_files[root]['media_sync_needed'] = 0
         if "ev" in all_files[root]['aws_data']:
            aws_event_id =  all_files[root]['aws_data']['ev']
         else:
            aws_event_id = 0
         if "hc" in all_files[root]['aws_data']:
            aws_human_confirmed =  all_files[root]['aws_data']['hc']
         else:
            aws_human_confirmed = 0

         print("ROOT IS:", root)
         if "mj" not in all_files[root]:
            continue
         if "human_confirmed" in all_files[root]['mj']:
            local_human_confirmed =  all_files[root]['mj']['human_confirmed']
         else:
            local_human_confirmed = 0

         if "multi_station_event" in all_files[root]['mj']:
            local_event_id =  all_files[root]['mj']['multi_station_event']['event_id']
         else:
            local_event_id = 0
         if (all_files[root]['local_rev'] > all_files[root]['aws_rev']):
            all_files[root]['actions'].append("update_aws_obs")
         if all_files[root]['media_sync_needed'] == 1:
            all_files[root]['actions'].append("media_sync_needed")
            all_files[root]['actions'].append("update_aws_obs")
         all_files[root]['meteor_confirmed'] = 0
         if local_event_id != 0 or aws_event_id != 0 or local_human_confirmed != 0 or aws_human_confirmed != 0:
            meteor_confirm_status = "METEOR_CONFIRMED"
            all_files[root]['meteor_confirmed'] = 1
         else:
            meteor_confirm_status = "METEOR_NOT_CONFIRMED"
            all_files[root]['meteor_confirmed'] = 0

         #print(all_files[root]['meteor_confirmed'], root, all_files[root]['actions'], all_files[root]['local_rev'], all_files[root]['aws_rev'],  all_files[root]['media_sync_needed'], local_event_id, aws_event_id,aws_human_confirmed,local_human_confirmed, all_files[root]['local_media'] )

      # stage the media files for upload based on the confirmation of each meteor ? 
      # this should be called "prep" we will upload later
      self.upload_cloud_media(day, all_files)

      for root in all_files:
         meteor_file = root + ".json"
         if "mj" not in all_files[root]:
            continue
         if "local_sync_status" in root:
            all_files[root]['mj']['sync_status'] = all_files[root]['local_sync_status']
         else:
            all_files[root]['mj']['sync_status']  = []

         sync_status = []
         if root in local_media:
            print("LOCAL MEDIA:", local_media[root]) 
            for ext in local_media[root]:
               cf = lcdir + self.station_id + "_" + root + "-" + ext
               if cfe(cf) == 1:
                  print("CLOUD FILE IS IN UPLOAD DIR!", cf)
                  sync_status.append(ext)
               #else:
               #   print("CLOUD FILE IS IN NOT IN UPLOAD DIR!", cf)

         else:
            print("ROOT NOT IN LOCAL MEDIA!?", root)
         all_files[root]['mj']['sync_status'] = sync_status
         del all_files[root]['mj']
         print(root, all_files[root])
         if "mj" in all_files[root]:
            save_json_file(meteor_file,all_files[root]['mj'])
         push_obs(self.api_key, self.station_id, meteor_file)
      if day not in self.sync_log:
         self.sync_log[day] = {}
         self.sync_log[day]['updates'] = []
      update_time = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
      self.sync_log[day]['updates'].append(update_time)
      self.sync_log[day]['last_update'] = update_time
      self.sync_log[day]['last_update_version'] = 1
      save_json_file(self.sync_log_file, self.sync_log)
      print("DONE.")

   def bad_day_filter(self, day):
      print(len(self.mfiles))
      bad_zero = 0
      report = {}
      crops = {}
      for mf in sorted(self.mfiles):
         report[mf] = {}
         mfile = "/mnt/ams2/meteors/" + day + "/" + mf.replace(".mp4", ".json")
         if cfe(mfile) == 0:
            continue
         mj = load_json_file(mfile)
         if "confirmed_meteors" not in mj:
            continue
         print(mf, "\n  CM:", len(mj['confirmed_meteors']))
         report[mf]['meteors_in_file'] = len(mj['confirmed_meteors'])
         report[mf]['bad_zero'] = 0
         for cm in mj['confirmed_meteors']:
            if "report" in cm:
               print("   REPORT", cm['report']['meteor'])
            if "best_meteor" in mj:
               if "crop_box" in mj['best_meteor']:
                  print("   BEST", mj['best_meteor']['crop_box'])
                  crop_key = str(int(mj['best_meteor']['crop_box'][0]/10)) + "." + str(int(mj['best_meteor']['crop_box'][1]/10))
                  print("CROP KEY", crop_key)
                  if crop_key in crops:
                     crops[crop_key] += 1
                  else:
                     crops[crop_key] = 1

            print("   FN", cm['ofns'])
            print("   XS", cm['oxs'])
            print("   YS", cm['oys'])
            print("   OW", cm['ows'])
            print("   OH", cm['ows'])
            print("   OINT", cm['oint'])
            print("   SEGS", cm['segs'])

            # check for 0 xs
            zero_x = 0
            zero_y = 0
            for x in cm['oxs']:
               if x == 0:
                  zero_x += 1
            for y in cm['oys']:
               if y == 0:
                  zero_y += 1
            zero_x_p = zero_x / len(cm['oxs'])
            zero_y_p = zero_y / len(cm['oys'])
            print("   ZEROXP:", zero_x_p)
            print("   ZEROYP:", zero_x_p)
            if zero_x_p > .5 or zero_y_p > .5:
               report[mf]['bad_zero'] = 1
               bad_zero += 1
            else:
               report[mf]['bad_zero'] = 0
      print("BAD ZEROS:", bad_zero)
      c = 0
      for key in crops:
         print(key, crops[key])

      for mf in report:
         if "bad_zero" not in report[mf]:
            continue
         mfile = "/mnt/ams2/meteors/" + day + "/" + mf.replace(".mp4", ".json")
         if cfe(mfile) == 0:
            continue
         mj = load_json_file("/mnt/ams2/meteors/" + day + "/" + mf.replace(".mp4", ".json"))
         print(c, mf, report[mf])
         c = c + 1
         if "best_meteor" in mj:
            if "crop_box" in mj['best_meteor']:
               crop_key = str(int(mj['best_meteor']['crop_box'][0]/10)) + "." + str(int(mj['best_meteor']['crop_box'][1]/10))
               if crop_key in crops:
                  crop_val = crops[crop_key]
               else:
                  crop_val = 0
            else:
               crop_val = 0
         else:
            crop_val = 0
         #if crop_val > 2:
         #   print("BAD CROP VAL!", crop_val, mf)
         if (report[mf]['bad_zero'] == 1 and report[mf]['meteors_in_file'] > 1) or report[mf]['meteors_in_file'] > 3 or crop_val > 2:
            mff = "/mnt/ams2/meteors/" + day + "/" + mf.replace(".mp4", ".json")
            mff_trash = "/mnt/ams2/meteors/" + day + "/" + mf.replace(".mp4", ".trash")
            cmd = "mv " + mff + " " + mff_trash
            os.system(cmd)
            print(cmd)

   def compare_sync_media(self, local, aws):
      missing = 0
      if local == 0 or aws == 0:
         missing = 1
      elif len(local) == 0 or len(aws) == 0 :
         missing = 1
      for media in local:
         if aws == 0:
            missing = 1
         elif media not in aws:
            missing = 1
      return(missing)

   def sync_meteor_media(self, meteor_files):
      if len(meteor_files) == 0:
         print("NO METEORS FOR THIS DAY!")
         return()
      sync_days = {}
      html = ""
      for mf in sorted(meteor_files):
         day = mf[0:10]
         lcdir_stage = "/mnt/ams2/meteors/" + day + "/cloud_stage/"
         lcdir = "/mnt/ams2/meteors/" + day + "/cloud_files/"
         if cfe(lcdir,1) == 0:
            os.makedirs(lcdir)
         if cfe(lcdir_stage,1) == 0:
            os.makedirs(lcdir_stage)
         json_file = "/mnt/ams2/meteors/" + day + "/" + mf
         json_file = json_file.replace(".mp4", ".json")
         mj = load_json_file(json_file)

         #self.make_cloud_media(lcdir_stage, json_file, mj)
      
         continue 

         # FILES WE WANT: tiny jpg, tiny vid, hd crop vid, hd crop jpg
         tiny_file = "/mnt/ams2/meteors/" + day + "/cloud_files/" + self.station_id + "_" + mf 
         tiny_file = tiny_file.replace(".mp4", "-tiny.jpg")
         tiny_crop_file = tiny_file.replace(".jpg", "-HD-crop.jpg")
         hd_crop_vid = tiny_file.replace("tiny.jpg", "HD-crop-vid.mp4")
         tiny_vid = tiny_file.replace(".jpg", "-vid.mp4")
         stack_file = "/mnt/ams2/meteors/" + day + "/" + mf
         stack_file = stack_file.replace(".mp4", "-stacked.jpg")
         #if cfe(tiny_file) == 0:

         if True:
            if cfe(stack_file) == 1:
               sync_days[day] = 1
               img = cv2.imread(stack_file)
               sm_img = cv2.resize(img, (self.TINY_W,self.TINY_H))
               if cfe(tiny_vid) == 0:
                  resize_video(mj['sd_video_file'], tiny_vid, self.TINY_W, self.TINY_H, bit_rate=20)
               if "hd_stack" in mj:
                  hd_img = cv2.imread(mj['hd_stack'])
                  hd_img = cv2.resize(img, (1920,1080))
               else:
                  hd_img = cv2.resize(img, (1920,1080))
               cv2.imwrite(tiny_file, sm_img, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
               ih,iw = img.shape[:2]
            # do the crop too
            if "best_meteor" in mj:
               hdxs = []
               hdys = []
               hdmx = 1920 / iw
               hdmy = 1080 / ih
               for i in range(0, len(mj['best_meteor']['oxs'])):
                  hdxs.append(mj['best_meteor']['oxs'][i]*hdmx)
                  hdys.append(mj['best_meteor']['oys'][i]*hdmy)
               mx = np.mean(hdxs)
               my = np.mean(hdys)
               bcw, bch = best_crop_size(hdxs, hdys, 1920,1080)
               x1 = int(mx - (bcw / 2))
               y1 = int(my - (bch / 2))
               x2 = int(mx + (bcw / 2))
               y2 = int(my + (bch / 2))
               if x1 < 0:
                  x1 = 0 
                  x2 = x1 + bcw
               if y1 < 0:
                  y1 = 0 
                  y2 = y1 + bch
               if x2 >= 1920:
                  x1 = 1919 - bcw 
                  x2 = 1919
               if y2 >= 1920:
                  y1 = 1079 - bch
                  y2 = 1079
               crop_img = hd_img[y1:y2,x1:x2]
               crop_img = cv2.resize(crop_img, (self.TINY_W, self.TINY_H))
               cv2.imwrite(tiny_crop_file, crop_img, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
               #cv2.rectangle(hd_img, (x1,y1), (x2,y2), (255, 255, 255), 1)
               #cv2.imwrite(tiny_crop_file, hd_img, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
               if cfe(hd_crop_vid) == 0:
                  crop_video(mj['hd_trim'], hd_crop_vid, [x1,y1,x2-x1,y2-y1])
               tiny_crop_fn = tiny_crop_file.split("/")[-1]
               tiny_fn = tiny_file.split("/")[-1]
               html += "<img src=" + tiny_fn + "?xx>"
               html += "<img src=" + tiny_crop_fn + "?xx>"
               show_vid = hd_crop_vid.split("/")[-1]
               show_tiny_vid = tiny_vid.split("/")[-1]
               show_crop_vid = hd_crop_vid.split("/")[-1]
               html += """<video id="video" width=""" + str(self.TINY_W) + " height=""" + str(self.TINY_H) + """ src='""" + show_tiny_vid + """' controls="true"></video>"""
               html += """<video id="video" width=""" + str(self.TINY_W) + " height=""" + str(self.TINY_H) + """ src='""" + show_crop_vid + """' controls="true"></video><br>"""
         else:
            print("DONE: ", tiny_file)

      print(html)
      #fp = open(lcdir + "imgs.html", "w")
      #fp.write(html)
      cloud_files = []
      for day in sync_days:
         year = day[0:4]
         lcdir = "/mnt/ams2/meteors/" + day + "/cloud_files/"
         cloud_dir = "/mnt/archive.allsky.tv/" + self.station_id + "/METEORS/" + year + "/" + day + "/"
         cfs = glob.glob(lcdir + "*")
         for cff in cfs:
            cf = cff.split("/", cff)
            cloud_files.append(cf)
         save_json_file(lcdir + self.station_id + "_" + day + "_cloud_files.json")
         print("SAVED:", lcdir + self.station_id + "_" + day + "_cloud_files.json")
         cmd = "rsync -av " + lcdir + " " + cloud_dir
         print(cmd)

   def delete_cloud_media(self, day):
      file_types = self.cloud_policy['confirmed']['full']['file_types']
      lcdir_stage = "/mnt/ams2/meteors/" + day + "/cloud_stage/"

      cloud_dir = "/mnt/archive.allsky.tv/" + self.station_id + "/METEORS/" + day[0:4] + "/" + day + "/"
      lcdir = lcdir_stage.replace("cloud_stage", "cloud_files")
      mdir = lcdir.replace("cloud_files/", "")
      cfs = glob.glob(lcdir + "*")
      css = glob.glob(lcdir_stage + "*")
      media = {}
      for cf in cfs:
         if "html" in cf:
            continue
         el = cf.split("/")[-1]
         for ft in file_types:
            if ft in el:
               el = el.replace("-" + ft, "")
         media[el] = 1
      for cf in css:
         if "html" in cf:
            continue
         el = cf.split("/")[-1]
         for ft in file_types:
            if ft in el:
               el = el.replace("-" + ft, "")
         media[el] = 1

      del_roots = {}
      for root in media: 
         mfile = mdir + root + ".json"
         mfile = mfile.replace(self.station_id + "_", "")
         print("ROOT", root)
         if cfe(mfile) == 0:
            print("MEDIA FILE EXISTS BUT NO METEOR ANYMORE. MUST HAVE BEEN DELETED!", mfile)
            del_roots[root] = 1
         else:
            print("This meteor is still good.")

      for mroot in del_roots:
         if len(glob.glob(lcdir_stage + mroot + "*")) > 0:
            cmd = "rm " + lcdir_stage  + mroot + "*"
            print(cmd)
            print(cmd)
            os.system(cmd)
         if len(glob.glob(lcdir + mroot + "*")) > 0:
            cmd = "rm " + lcdir + mroot + "*"
            print(cmd)
            os.system(cmd)

   def upload_cloud_media(self, day, all_files):
      cloud_dir = "/mnt/archive.allsky.tv/" + self.station_id + "/METEORS/" + day[0:4] + "/" + day + "/"
      lcdir_stage = "/mnt/ams2/meteors/" + day + "/cloud_stage/"
      lcdir = "/mnt/ams2/meteors/" + day + "/cloud_files/"
      for mf in all_files :
         base_file = self.station_id + "_" + mf 
         if mf not in all_files:
            continue
         if "meteor_confirmed" in all_files[mf]:
            confirmed = all_files[mf]['meteor_confirmed']
         else:
            confirmed = 0
         if confirmed == 1:
            exts = self.cloud_policy['confirmed'][self.my_sync_profile]
            for ext in exts:
               media_file = base_file + "-" + ext
               if cfe(lcdir + media_file) == 0:
                  if cfe(lcdir_stage + media_file) == 1:
                     cmd = "mv " + lcdir_stage + media_file + " " + lcdir 
                     print(cmd)
                     os.system(cmd)


         else:
            exts = self.cloud_policy['non_confirmed'][self.my_sync_profile]
            for ext in exts:
               media_file = base_file + "-" + ext
               if cfe(lcdir + media_file) == 0:
                  if cfe(lcdir_stage + media_file) == 1:
                     cmd = "mv " + lcdir_stage + media_file + " " + lcdir 
                     print(cmd)
                     os.system(cmd)

      print("STAGE FILES MOVED!")
      print("SKIP RYSNC FOR NOW!")
      total_local_cloud_files = len(glob.glob(lcdir + "*"))
      if total_local_cloud_files != len(self.cloud_files) :
         rsync_cmd = "rsync -auv " + lcdir + "* " + cloud_dir
         print("Cloud media files and local meida files are NOT in sync. rsync needed!")
         print(rsync_cmd)
         # MAIN UPLOADER HERE!!!
         #os.system(rsync_cmd)
      else:
         print("Cloud media files and local meida files are in sync. no rsync needed.")

   def upload_cloud_media_old(self, day, mfiles):
      year = day[0:4]
      file_types_nc = self.cloud_policy['non_confirmed'][self.my_policy['non_confirmed']]
      file_types_cf = self.cloud_policy['confirmed'][self.my_policy['confirmed']] 
      print("CONFIRMED TYPES:", file_types_cf )
      print("NON CONFIRMED TYPES:", file_types_nc )
      # loop over each meteor and see if it is confirmed or not. 
      # move relevant files to the "cloud_files" dir based on policy and meteor type
      # call rsync when done with auvD (delete)
      mdir = "/mnt/ams2/meteors/" + day + "/"

      for mf in mfiles:
         mf = mf.replace(".mp4", ".json")
         print("MF:", mdir + mf)
         if cfe(mdir + mf) == 1:
            mj = load_json_file(mdir + mf)
            if "multi_station_event" in mj:
               print("CONFIRMED METEOR")
               meteor_confirmed = 1
               file_types = self.cloud_policy['confirmed'][self.my_policy['confirmed']]['file_types']
               print("UPLOAD FILE TYPES:", file_types)
            else:
               print("NON CONFIRMED METEOR")
               print(mj.keys())
               meteor_confirmed = 0
               file_types = self.cloud_policy['non_confirmed'][self.my_policy['non_confirmed']]['file_types'] 
            root = mf.replace(".json", "")
            root = self.station_id + "_" + root
            for ft in file_types:
               cs_file = mdir + "cloud_stage/" + root + "-" + ft
               cf_file = mdir + "cloud_files/" + root + "-" + ft
               print("SYNC THIS FILE:", cs_file)
               if cfe(cs_file) == 1:
                  cmd = "mv " + cs_file + " " + cf_file
                  print(cmd)
                  os.system(cmd)
               else:
                  print("FILE COULD NOT BE MOVED FROM STAGING DIR.", cs_file)
      local_cloud = mdir + "cloud_files/"
      remote_cloud = "/mnt/archive.allsky.tv/" + self.station_id + "/METEORS/" + year + "/" + day + "/"
      cloud_files = glob.glob(local_cloud + "*")
      save_json_file(local_cloud + self.station_id + "_" + day + "_cloud_files.json", cloud_files)

      rsync_cmd = "/usr/bin/rsync -avh " + local_cloud + " " + remote_cloud + " --delete"
      print(rsync_cmd)
      os.system(rsync_cmd)
            
      



   def make_cloud_media (self,lcdir_stage, json_file, mj):
      print("\n\n CLOUD MAKE MEDIA FOR :", json_file)
      errors= {}
      lcdir = lcdir_stage.replace("cloud_stage", "cloud_files")
      root_file = json_file.split("/")[-1].replace(".json", "")
      if "sd_video_file" not in mj:
         return()
      sd_vid = mj['sd_video_file']
      hd_vid = mj['hd_trim']
      ffp = {}
      sd_start = None
      if cfe(hd_vid) == 1:
         ffp['hd'] = ffprobe(hd_vid)   
      else:
         hd_vid = None
      if cfe(sd_vid) == 1:
         ffp['sd'] = ffprobe(sd_vid)   
      else:
         sd_vid = None
      mj['ffp'] = ffp
      print("**** 1 *****")
      cloud_stage_files = {}
      work_needed = 0
      work_files = []
      for file_type in self.media_types:
         filename = self.station_id + "_" + root_file + "-" + file_type
         cloud_stage_files[file_type] = lcdir_stage + filename
         if cfe(lcdir_stage + filename) == 0 and cfe(lcdir + filename) == 0:
            work_needed += 1
            work_files.append(file_type)

      print("**** WORKING ON", work_needed, sd_vid)
      if work_needed == 0:
         print("**** ALREADY DONE!")
         return()

      if "best_meteor" in mj:
         x1, y1, x2, y2 = self.find_hd_crop_area(mj)
         crop_box = [x1, y1, x2, y2]  
         sd_start = mj['best_meteor']['ofns'][0] 
         sd_end = mj['best_meteor']['ofns'][-1] 
      else:
         x1 = 0
         x2 = 1920
         y1 = 0 
         y2 = 1080
      hdmx = 1920/self.FSD_W
      hdmy = 1080/self.FSD_H
      sx1 = int(x1 / hdmx)
      sy1 = int(y1 / hdmy)
      sx2 = int(x2 / hdmx)
      sy2 = int(y2 / hdmy)

      # load and resize the sd & hd stacks
      cf = cloud_stage_files['prev.jpg'].replace("cloud_stage", "cloud_files")

      # make images if they don't exist yet
      if True:
         if cfe(mj['sd_stack']) == 1:
            sd_stack_img = cv2.imread(mj['sd_stack'])
         else:
            sd_stack = None
         if cfe(mj['hd_stack']) == 1:
            hd_stack_img = cv2.imread(mj['hd_stack'])
         else:
            hd_stack = None
         #tiny_img = cv2.resize(sd_stack_img, (self.TINY_W, self.TINY_H)) 
         #cv2.imwrite(cloud_stage_files['tiny.jpg'], tiny_img, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
        
         if "prev.jpg" in work_files and sd_stack_img is not None:
            prev_img = cv2.resize(sd_stack_img, (self.PREV_W, self.PREV_H)) 
            cv2.imwrite(cloud_stage_files['prev.jpg'], prev_img, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
         if ("SD.jpg" in work_files or "SD-prev.jpg" in work_files) and sd_stack_img is not None:
            sd_stack_img = cv2.resize(sd_stack_img, (self.FSD_W, self.FSD_H)) 
            cv2.imwrite(cloud_stage_files['SD.jpg'], sd_stack_img, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
         if "prev-crop.jpg" in work_files :
            print("prev CROP:",  [sx1,sy1,sx2-sx1,sy2-sy1])
            print(work_files)
            sd_crop_img = sd_stack_img[sy1:sy2,sx1:sx2]
            cv2.imwrite(cloud_stage_files['prev-crop.jpg'], sd_crop_img)

      if "hd_stack" in mj and ("HD.jpg" in work_files or "HD-crop.jpg" in work_files or "HD.mp4" in work_files or "HD-crop.mp4" in work_files):
         if mj['hd_stack'] != 0:
            if cfe(mj['hd_stack']) == 1:
               hd_stack_img = cv2.imread(mj['hd_stack'])
               cv2.imwrite(cloud_stage_files['HD.jpg'], hd_stack_img, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
      
    
      # SD VIDEO PROCESS
      if "SD.mp4" in work_files:
         resize_video(sd_vid, cloud_stage_files['SD.mp4'], self.FSD_W, self.FSD_H, bit_rate=self.BIT_RATE)
         print("SAVED:", cloud_stage_files['SD.mp4'])

      #if ("SD-crop.mp4" not in work_files and "SD.mp4" not in work_files and "HD.mp4" not in work_files and "HD-crop.mp4" not in work_files):
      #   print("ALL WORK IS DONE!")
      #   return()

      if "best_meteor" not in mj :
         # if meteor is not reduced

         print("NO BEST METEOR.")
         return()

      # need to get the crop area if we can.


      # make sd crop
      final_trim = {}
      if sd_vid is not None:

         crop_video(cloud_stage_files['SD.mp4'], cloud_stage_files['SD-crop.mp4'], [sx1,sy1,sx2-sx1,sy2-sy1])
         sd_crop_frames = load_frames_simple( cloud_stage_files['SD-crop.mp4'])
         new_sd_start,new_sd_end = self.find_event(sd_crop_frames)
         if new_sd_start is None:
            new_sd_start = sd_start
         if new_sd_end is None:
            new_sd_end = sd_end
         if new_sd_start < sd_start:
            sd_start = new_sd_start
         if new_sd_end > sd_end:
            sd_end = new_sd_end
         if sd_start is None:
            sd_start = 25
         if sd_end is None:
            sd_end = mj['ffp']['sd'][3]

         sd_start -= 5
         sd_end += 5
         if sd_start < 0:
            sd_start = 0
         if sd_end >= mj['ffp']['sd'][3]:
            sd_end = mj['ffp']['sd'][3]
         final_trim['sd'] = [sd_start,sd_end]
         temp = cloud_stage_files['SD-crop.mp4'].replace(".mp4", "-temp.mp4")
         splice_video(cloud_stage_files['SD-crop.mp4'], sd_start, sd_end, temp, "frame")
         os.system("mv " + temp + " " + cloud_stage_files['SD-crop.mp4'] )

         temp = cloud_stage_files['SD.mp4'].replace(".mp4", "-temp.mp4")
         splice_video(cloud_stage_files['SD.mp4'], sd_start, sd_end, temp, "frame")
         os.system("mv " + temp + " " + cloud_stage_files['SD.mp4'] )

      if hd_vid is not None:
         crop_video(hd_vid, cloud_stage_files['HD-crop.mp4'], [x1,y1,x2-x1,y2-y1])
         hd_crop_img = hd_stack_img[y1:y2,x1:x2]
         try:
            cv2.imwrite(cloud_stage_files['HD-crop.jpg'], hd_crop_img)
         except:
            print("failed to wite HD stack image!", cloud_stage_files['HD-crop.jpg'])
            error_key = self.station_id + ":" + root_file + ":"
            errors['error_key'] = "HD create img failed."
            return()

         # NOW HD PROCESSING
         hd_crop_frames = load_frames_simple( cloud_stage_files['HD-crop.mp4'])
         hd_start,hd_end = self.find_event(hd_crop_frames)

         if hd_start is None:
            print("WE COULDN'T FIND THE HD EVENT START!?")
            hd_start = 25
         if hd_end is None:
            hd_end = mj['ffp']['hd'][3]
         hd_start -= 5
         hd_end += 5
         final_trim['hd'] = [hd_start,hd_end]
         if hd_start < 0:
            hd_start = 0
         if hd_end >= mj['ffp']['hd'][3]:
            hd_end = mj['ffp']['hd'][3]

         temp = cloud_stage_files['HD-crop.mp4'].replace(".mp4", "-temp.mp4")
         splice_video(cloud_stage_files['HD-crop.mp4'], hd_start, hd_end, temp, "frame")
         os.system("mv " + temp + " " + cloud_stage_files['HD-crop.mp4'] )

         temp = cloud_stage_files['HD.mp4'].replace(".mp4", "-temp.mp4")
         splice_video(hd_vid, hd_start, hd_end, temp, "frame")
         os.system("mv " + temp + " " + cloud_stage_files['HD.mp4'] )
         lower_bitrate(cloud_stage_files['HD-crop.mp4'], 30)
         lower_bitrate(cloud_stage_files['HD.mp4'], 30)
      if sd_start is not None:
         mj['final_trim'] = final_trim
         mj['crop_box'] = crop_box
         save_json_file(json_file, mj)


   def make_obs_data_OLD(self, station_id, meteor_file,mj):
      # USE THE FUNCTION INSIDE pushAWS.py to push obs not this one!
      jsf = meteor_file.split("/")[-1] 
      date = jsf[0:10]
      update_time = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
      meteor_file = "/mnt/ams2/meteors/" + date + "/" + jsf
      event_id = 0

      if cfe(meteor_file) == 1:
         red_file = meteor_file.replace(".json", "-reduced.json")
         if "multi_station_event" in mj:
            event_id = mj['multi_station_event']['event_id']
         if "revision" not in mj:
            mj['revision'] = 1
         if "dfv" not in mj:
            mj['dfv'] = 1.0

         if "cp" in mj:
            cp = mj['cp']
            if "total_res_px" not in cp:
               cp['total_res_px'] = 9999
            if "cat_image_stars" not in cp:
               cp['cat_image_stars'] = []
            if math.isnan(cp['total_res_px']):
               cp['total_res_px'] = 9999
            calib = [cp['ra_center'], cp['dec_center'], cp['center_az'], cp['center_el'], cp['position_angle'], cp['pixscale'], float(len(cp['cat_image_stars'])), float(cp['total_res_px'])]
            if "cat_image_stars" in cp:
               cat_stars = cp['cat_image_stars']
            else:
               cat_stars = []
         else:
            calib = []
         if cfe(red_file) == 1:
            mjr = load_json_file(red_file)
         else:
            mjr = {}
            print("NO RED FILE:", red_file)
         sd_vid = mj['sd_video_file'].split("/")[-1]
         hd_vid = mj['hd_trim'].split("/")[-1]
         if "meteor_frame_data" in mjr:
            meteor_frame_data = mjr['meteor_frame_data']
            duration = len(mjr['meteor_frame_data']) / 25
            event_start_date, event_start_time = mjr['meteor_frame_data'][0][0].split(" ")
         else:
            meteor_frame_data = []
            event_start_time = ""
            duration = 99

         date = jsf[0:10]
         mdir = "/mnt/ams2/meteors/" + date + "/"
         cloud_dir = "/mnt/ams2/meteors/" + date + "/cloud_files/"

      if "best_meteor" in mj:
         peak_int = max(mj['best_meteor']['oint'])
      else:
         peak_int = 0
      if "final_trim" in mj:
         final_trim = mj['final_trim'] 
      else: 
         final_trim = {}
         #"cat_stars": cat_stars,
      obs_data = {
         "station_id": station_id,
         "sd_video_file": sd_vid,
         "hd_video_file": hd_vid,
         "event_start_time": event_start_time,
         "event_id": event_id,
         "dur": duration,
         "peak_int": peak_int,
         "calib": calib,
         "final_trim": final_trim,
         "cat_image_stars": cat_stars,
         "meteor_frame_data": meteor_frame_data,
         "revision": mj['revision'],
         "dfv": mj['dfv'],
         "sync_status": mj['sync_status'],
         "last_update": update_time
      }
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
