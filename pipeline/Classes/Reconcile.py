from lib.PipeUtil import cfe, load_json_file, save_json_file, get_file_info, convert_filename_to_date_cam,get_trim_num
from lib.PipeAutoCal import XYtoRADec
import simplejson as json
import requests
import os
from pushAWS import make_obs_data
import glob
from datetime import datetime
import datetime as ddtt
import numpy as np
"""
 Reconcile -- Class for reconciling meteor data with latest detection, redis storage, calib, media, cloud, backup/archive and AWS. 



"""

class Reconcile():
   def __init__(self, year=None,month=None):
      self.year = year
      self.month = month
      self.API_URL = "https://kyvegys798.execute-api.us-east-1.amazonaws.com/api/allskyapi"
      self.data_dir = "/mnt/ams2/METEOR_SCAN/DATA/"
      if cfe(self.data_dir,1) == 0:
         os.makedirs(self.data_dir)
      self.media_exts = ['FRMS.jpg', 'HD.jpg', 'HD.mp4', 'prev.jpg', 'ROI.jpg', 'ROI.mp4', 'ROIHD.jpg', 'ROIHD.mp4', 'SD.jpg', 'SD.mp4']
      if cfe(self.data_dir, 1) == 0:
         os.makedirs(self.data_dir)
      if year is not None and month is None:
         self.rec_file = self.data_dir + "reconcile_" + year + ".json"
      elif year is not None and month is not None:
         self.rec_file = self.data_dir + "reconcile_" + year + "_" + month + ".json"
      else:
         self.rec_file = self.data_dir + "reconcile_ALL.json"
      self.json_conf = load_json_file("../conf/as6.json")
      self.station_id = self.json_conf['site']['ams_id']
      self.cloud_dir = "/mnt/archive.allsky.tv/" + self.station_id + "/METEORS/" 
      if cfe(self.cloud_dir,1) == 0:
         os.makedirs(self.cloud_dir)



      if cfe(self.rec_file) == 1:
         try:
            self.rec_data = load_json_file(self.rec_file)
         except:
            print("CORRUPT rec file?", self.rec_file)
            self.rec_data = {}
      else:
         self.rec_data = {}
      self.mfiles = []
      if "corrupt_json" not in self.rec_data:
         self.rec_data['corrupt_json'] = []

      if "needs_review" not in self.rec_data:
         self.rec_data['needs_review'] = []
      
      self.get_all_meteor_files(year, month)

      self.rec_data['mfiles'] = self.mfiles
      save_json_file(self.rec_file, self.rec_data, True)

      if "meteor_index" not in self.rec_data:
         self.rec_data['meteor_index'] = {}   
      c = 0

      # Build master index of cloud files.
      print("BUILDING CLOUD FILE INDEX!")
      self.get_cloud_media()

      new = 0

      print("REC DATA KEYS:", self.rec_data.keys()) 
      for root_file in self.rec_data['mfiles']:
         print("ROOT:", root_file)
         if root_file in self.rec_data['meteor_index']:
            print(root_file, self.rec_data['meteor_index'][root_file].keys())
         else:
            print("Root file not in meteor index.")

      for root_file in self.rec_data['mfiles']:
         date = root_file[0:10]
         meteor_file = "/mnt/ams2/meteors/" + date + "/" + root_file + ".json"
         mon = date[0:7]
         if c > 0 and last_month != mon and new >= 500:
            # incrementally save
            save_json_file(self.rec_file, self.rec_data,True)
            new = 0

         if root_file not in self.rec_data['meteor_index']:
            self.rec_data['meteor_index'][root_file] = {}
            self.rec_data['meteor_index'][root_file]['last_update'] = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
            print("LOADING FILE INTO REC DATA:", root_file)
            print("NEW FILE FOR REC DB:", self.rec_data['meteor_index'][root_file].keys())
            if "cloud_files" in self.rec_data['meteor_index'][root_file]:
               cloud_files = self.rec_data['meteor_index'][root_file]['cloud_files']
            else:
               cloud_files = []
            self.rec_data['meteor_index'][root_file]['obs_data'] = make_obs_data(self.station_id, date, meteor_file,cloud_files) 
            new = new + 1
         else:
            # This file was already in the rec data.
            print("FILE EXISTS IN REC DB:", self.rec_data['meteor_index'][root_file].keys())
            if "obs_data" not in self.rec_data['meteor_index'][root_file]:
               if "cloud_files" in self.rec_data['meteor_index'][root_file]:
                  cloud_files = self.rec_data['meteor_index'][root_file]['cloud_files']
               else:
                  cloud_files = []
               self.rec_data['meteor_index'][root_file]['obs_data'] = make_obs_data(self.station_id, date, meteor_file,cloud_files)

         c += 1
         last_month = mon
      print("SAVING REC DATA FILE.")
      save_json_file(self.rec_file, self.rec_data )
      #self.reconcile_scan_media(year,month)

   def index_all_meteors_aws(self):
      for mfile in self.mfiles:
         print(mfile)

   def media_make_roi_jpg(self,root_file):
      day = root_file[0:10]
      year = root_file[0:4]
      self.mdir = "/mnt/ams2/meteors/" + day + "/"
      self.scan_dir = "/mnt/ams2/METEOR_SCAN/" + day + "/" 
      self.cloud_dir = "/mnt/archive.allsky.tv/" + self.station_id + "/" + year + "/" + day + "/"
      roi_file = self.station_id + "_" + root_file + "-ROI.jpg"
      if cfe(roi_file) == 0:
         print("Make local ROI.jpg")
         mjf = self.mdir + root_file + ".json"
         mjrf = self.mdir + root_file + "-reduced.json"
         hd_roi = None
         if cfe(mjrf) == 1:
            mjr = load_json_file(mjrf)
            mj = load_json_file(mj)
            if "meteor_frame_data" in mjr:
               if len(mjr["meteor_frame_data"]) > 0:
                  hd_roi = self.mfd_roi(mjr["meteor_frame_data"])
                  self.make_roi_media(root_file,x1,y1,x2,y2,mj)
                  
               else:
                  print("MFD = 0")
            else:
               print("NO MFD ")
         else:
            print("NO RED FILE!", mjrf)
         if hd_roi is not None:
            print("HD ROI IS:", hd_roi)

          
      if cfe(cloud_dir + root_file + "-ROI.jpg") == 0:
         print("Copy ROI.jpg to cloud")

   def make_roi_media(self, mfd):
      print("MAKE ROI MEDIA")

   def mfd_roi(self, mfd):
      xs = [row[2] for row in mfd]
      ys = [row[3] for row in mfd]
      cx = np.mean(xs)
      cy = np.mean(ys)
      min_x = min(xs)
      max_x = max(xs)
      min_y = min(ys)
      max_y = max(ys)
      print("MFD AREA:", min_x, min_y, max_x, max_y)
      print("xs", xs)
      print("ys", ys)
      w = max_x - min_x
      h = max_y - min_y
      print("DIM:", w,h)
      if w > h:
         roi_size = int(w * 1.25)
      else:
         roi_size = int(h * 1.25)
      print(roi_size)

      x1 = int(cx - int(roi_size/2))
      x2 = int(cx + int(roi_size/2))
      y1 = int(cy - int(roi_size/2))
      y2 = int(cy + int(roi_size/2))
      print("HD ROI:", x1,y1,x2,y2)
      roi_w = x2 - x1
      roi_h = y2 - y1
      print("HD ROI W/H:", roi_w, roi_h)
      if roi_w != roi_h:
         print("HD ROI PROBLEM? W/H SHOULD BE THE SAME?")
         if roi_w < roi_h:
            roi_size = roi_w
         else:
            roi_size = roi_h
      else:
         roi_size = roi_w 
      if roi_size > 1070:
         print("METEOR IS TOO BIG TO MAKE AN ROI!")
         hd_roi = [0,0,1920,1080]
         return(hd_roi)
      # check if the ROI BOX extends offframe
      off_frame = self.check_off_frame(x1,y1,x2,y2,1920,1080) 
      if len(off_frame) > 0:
         x1,y1,x2,y2 = self.fix_off_frame(x1,y1,x2,y2,1920,1080, off_frame) 
      return(x1,y1,x2,y2)

   def fix_off_frame(self,x1,y1,x2,y2,w,h,off_frame):
      print("*********************************************")
      print("*            OFF FRAME ROI DETECTED         *")
      print("*********************************************")
      print(x1,y1,x2,y2,w,h,off_frame)
      input()
      w = x2 - x1
      h = y2 - y1
      roi_size = w
      if h > w:
         roi_size = h
      if len(off_frame) > 0:
         for off in off_frame:
            if off == "left": 
               x1 = 0 
               x2 = roi_size
            if off == "right": 
               x1 = 1919 - roi_size 
               x2 = 1919 
            if off == "top": 
               y1 = 0
               y2 = roi_size
            if off == "bottom": 
               y1 = 1079 - roi_size
               y2 = 1079 
 
      return(x1,y1,x2,y2)

   def check_off_frame(self,x1,y1,x2,y2,w,h):
      off_frame = []
      
      print("check_off_frame", x1,y1,x2,y2,w,h)
      if x1 < 0: 
         print("X1 < 0")
         off_frame.append('left')
      if x2 > w - 1: 
         print("X2 > W", x2, w)
         off_frame.append('right')
      if y1 < 0: 
         print("Y1 < 0")
         off_frame.append('top')
      if y2 > h - 1: 
         print("Y2 > H", y2, h)
         off_frame.append('bottom')
      print("OFF FRAME:", off_frame)
      return(off_frame)

   def rec_media(self,year,month):
      missing_media = {}
      self.get_cloud_media(year)
      for root_file in self.rec_data['meteor_index']:
         if root_file in self.rec_data['meteor_index']:
            if "cloud_files" in self.rec_data['meteor_index'][root_file]:
               print("CLOUD FILE:", root_file, self.rec_data['meteor_index'][root_file]['cloud_files'])
               if "prev.jpg" not in self.rec_data['meteor_index'][root_file]['cloud_files']:
                  print("MISSING PREV:", root_file)
                  if root_file not in missing_media:
                     missing_media[root_file] = {}
                  missing_media[root_file]['prev.jpg'] = 1
               if "ROI.jpg" not in self.rec_data['meteor_index'][root_file]['cloud_files']:
                  print("MISSING ROI JPG:", root_file)
                  if root_file not in missing_media:
                     missing_media[root_file] = {}
                  missing_media[root_file]['ROI.jpg'] = 1
               if "SD.mp4" not in self.rec_data['meteor_index'][root_file]['cloud_files']:
                  print("MISSING SD MP4:", root_file)
                  if root_file not in missing_media:
                     missing_media[root_file] = {}
                  missing_media[root_file]['SD.mp4'] = 1
               if "SD.jpg" not in self.rec_data['meteor_index'][root_file]['cloud_files']:
                  print("MISSING SD MP4:", root_file)
                  if root_file not in missing_media:
                     missing_media[root_file] = {}
                  missing_media[root_file]['SD.jpg'] = 1


               if "ROI.mp4" not in self.rec_data['meteor_index'][root_file]['cloud_files']:
                  print("MISSING ROI MP4:", root_file)
                  if root_file not in missing_media:
                     missing_media[root_file] = {}
                  missing_media[root_file]['ROI.jpg'] = 1
               if "360p.mp4" not in self.rec_data['meteor_index'][root_file]['cloud_files']:
                  print("MISSING 360p MP4:", root_file)
                  if root_file not in missing_media:
                     missing_media[root_file] = {}
                  missing_media[root_file]['360p.mp4'] = 1
            else:
               print("NO CLOUD FILES DATA STRUCTURE FOR ROOT FILE?", root_file)
         else:
            print("NO ROOT FILE in meteor_index?", root_file)

      # FIRST PUT IN THE ROI FILES
      for root_file in missing_media:
         for ext in missing_media[root_file]:
            if ext == "ROI.jpg":
               print("MAKE ROI FOR ", root_file)

               self.media_make_roi_jpg(root_file)
         #print(root_file, missing_media[root_file])

   def reconcile_scan_media(self, year, month):
      print("GETTING SCAN MEDIA...", year, month)
      #self.get_scan_media(year,month)
      #self.get_cloud_media(year)
      new = 1
      if new >= 1:    
         print("saving " + year + " data")
         save_json_file(self.rec_file, self.rec_data)

      # REMOVE DELETED METEORS FROM THE REC_DATA METEOR INDEX
      deleted_meteors = []
      for root_file in self.rec_data['meteor_index']:
         mfile = "/mnt/ams2/meteors/" + root_file[0:10] + "/" + root_file + ".json" 
         if cfe(mfile) == 0:
            print("   INFO: MFILE NO LONGER EXISTS. IT SHOULD BE DELETED FROM THE METEOR INDEX!")
            print("   ",mfile)
            deleted_meteors.append(root_file)
      for root_file in deleted_meteors:
         #print("   INFO: REMOVED FILE FROM INDEX", root_file) 
         #print(self.rec_data.keys())
         if root_file in self.rec_data['meteor_index']: 
            del(self.rec_data['meteor_index'][root_file])
         if root_file in self.rec_data['mfiles']: 
            del(self.rec_data['mfiles'][root_file])
         #if root_file in self.rec_data['needs_review']: 
         #   del(self.rec_data['needs_review'][root_file])
         #if root_file in self.rec_data['corrupt_json']: 
         #   del(self.rec_data['corrupt_json'][root_file])
      save_json_file(self.rec_file, self.rec_data)

   def get_aws_obs(self,day):
      url = self.API_URL + "?cmd=get_obs_for_day&station_id=" + self.station_id + "&day=" + day + "&api_key=" + self.json_conf['api_key']
      response = requests.get(url)
      content = response.content.decode()
      content = content.replace("\\", "")
      if "nothing" not in content:
         jdata = json.loads(content)
      else:
         jdata = {}
         jdata['all_vals'] = []
         jdata['total_records'] = 0
      if jdata is not None:
         data = jdata['all_vals']
      else:
         data = []
      aws_obs = data
      return(aws_obs)

   def reconcile_day(self, date):
      print("RECONCILE DAY.", date)

      self.mfiles = []
      self.aws_obs = []
      mdir = "/mnt/ams2/meteors/" + date
      self.get_mfiles(mdir)
      self.aws_obs = self.get_aws_obs(date)

      print("LOCAL FILES:", len(self.mfiles))
      print("AWS FILES:", len(self.aws_obs))

      # make sure sync status / cloud media is up to date
      year_mon = date[0:7]
      cloud_index_file = "/mnt/ams2/METEOR_SCAN/DATA/cloud_index_" + year_mon + ".json"
      if cfe(cloud_index_file) == 1 :
         cloud_index = load_json_file(cloud_index_file)
      else:
         cloud_index = {}
         print("NO CLOUD_INDEX", cloud_index_file)
         sync_status = []

      aws_dict = {}
      for aws_data in self.aws_obs:
         mkey = aws_data['station_id'] + "_" + aws_data['vid'].replace(".mp4", "")
         aws_dict[mkey] = aws_data

      for mfile in self.mfiles:
         mkey = self.station_id + "_" + mfile
         if mkey in cloud_index:
            if mkey in aws_dict:
               if cloud_index[mkey]['cloud_files'] == aws_dict[mkey]['ss']:
                  print("INSYNC!", mkey, cloud_index[mkey]['cloud_files'], aws_dict[mkey]['ss'] ) 
               else:
                  print("NOT IN SYNC!", mkey, cloud_index[mkey]['cloud_files'], aws_dict[mkey]['ss'] ) 
            else:
               print("FILE NOT IN AWS DICT?", mkey)
         else:
            print("NOT IN CLOUD INDEX", mkey)




   def rec_report(self ) :
      sum_rpt = {}
      sum_rpt['status'] = {}
      sum_rpt['days'] = {}
      print("REC REPORT FOR ", self.station_id, self.year, self.month)
      for key in sorted(self.rec_data['meteor_index'].keys(), reverse=True):
         if "scan_status" in self.rec_data['meteor_index'][key]['obs_data']:
            scan_status = self.rec_data['meteor_index'][key]['obs_data']['scan_status']['status']
         else:
            scan_status = self.get_scan_status(key)
            self.rec_data['meteor_index'][key]['obs_data']['scan_status'] = scan_status
            scan_status = scan_status['status']

         if scan_status not in sum_rpt['status']:
            sum_rpt['status'][scan_status] = 0
         else:
            sum_rpt['status'][scan_status] += 1 
         
      for key in sum_rpt['status']:
         print(key, sum_rpt['status'][key])


      save_json_file(self.rec_file, self.rec_data)
      print("SAVING:", self.rec_file)
      print("KEYS:", self.rec_data.keys())
      for key in self.rec_data.keys():
         print(key,len(self.rec_data[key]))
      for key in self.rec_data['meteor_index']:
         print(key, self.rec_data['meteor_index'][key]['obs_data']['scan_status'] )


   def reconcile_all_aws_obs(self):
      aws_local_file = "/mnt/ams2/METEOR_SCAN/DATA/ALL_AWS.json"
      if cfe(aws_local_file) == 0:
         cmd = "wget https://archive.allsky.tv/EVENTS/OBS/STATIONS/" + self.station_id + ".json -O " + aws_local_file
         os.system(cmd)
      all_aws_obs = load_json_file(aws_local_file)
      print(len(all_aws_obs))
      all_aws_obs = sorted(all_aws_obs, key=lambda x: (x[1]), reverse=True)
      deleted = 0
      for row in all_aws_obs:
         station_id, root_file, event, tme, revision , sync_status, peak_int,dur,res,stars = row
         vid = root_file + ".mp4"
         day = root_file[0:10]
         mf = "/mnt/ams2/meteors/" + day + "/" + root_file + ".json"
         if cfe(mf) == 0:
            print("AWS OBS NO LONGER ON LOCAL STATION.", mf)
            url = self.API_URL + "?cmd=del_obs_commit&station_id=" + self.station_id + "&sd_video_file=" + vid + "&api_key=" + self.json_conf['api_key']
            print(deleted, url)
            deleted += 1

            response = requests.get(url)
            content = response.content.decode()


   def save_rec_data(self):
      save_json_file(self.rec_file, self.rec_data)
      print("SAVED:", self.rec_file)

   def day_month_stats(self):
      for root_file in self.rec_data['meteor_index']:
         day = root_file[0:10]
         mon = root_file[0:7]
         if day not in self.rec_data['day_data']:
            self.rec_data['day_data'][day] = 1
         else:
            self.rec_data['day_data'][day] += 1
         if mon not in self.rec_data['month_data']:
            self.rec_data['month_data'][mon] = 1 
         else:
            self.rec_data['month_data'][mon] += 1 

      for day in self.rec_data['day_data']:
         print(day, self.rec_data['day_data'][day])
      for mon in self.rec_data['month_data']:
         print(mon, self.rec_data['month_data'][mon])



   def reconcile_report(self, year = None, month=None):
      print("RECONCILE REPORT FOR ", self.station_id, year, month)
      for root_file in sorted(self.rec_data['meteor_index'], reverse=True):
         obs_data = self.rec_data['meteor_index'][root_file]['obs_data']
         peak_int = 0
         ss = []
         mfd = 0
         remake_mfd = 0
         if "meteor_frame_data" in obs_data:
            mfd = len(obs_data['meteor_frame_data'])
            if mfd == 0:
               remake_mfd = 1
         else:
            print("   INFO: NO METEOR FRAME DATA!")
            remake_mfd = 1
         if remake_mfd == 1:
            meteor_file = "/mnt/ams2/meteors/" + root_file[0:10] + "/" + root_file + ".json"
            self.rec_data['meteor_index'][root_file]['obs_data'] = make_obs_data(self.station_id, root_file[0:10], meteor_file) 


            print("OBS DATA:", obs_data)
            print("NEW OBS DATA:", self.rec_data['meteor_index'][root_file]['obs_data'])

            meteor_frame_data = self.make_meteor_frame_data(obs_data, meteor_file)
            mfd = len(meteor_frame_data)
            if mfd == 0:
               self.rec_data['needs_review'].append(root_file)
               self.rec_data['needs_review'] = sorted(list(set(self.rec_data['needs_review'])))


         if "sync_status" in obs_data:
            sync_status = obs_data['sync_status']
          
         else:
            print("   INFO: GET SYNC STATUS!")

         if "peak_int" in obs_data:
            peak_int = obs_data['peak_int']
            self.rec_data['meteor_index'][root_file]['obs_data']['peak_int'] = peak_int
         else:
            print("   INFO: GET PEAK INT!")

         if "scan_status" in obs_data :
            scan_status = obs_data['scan_status'] 
            up = 0
            for ss in obs_data['scan_status']:
               if ss == 0:
                  up = 1
            if up == 1:
               scan_status = self.get_scan_status(root_file)
               self.rec_data['meteor_index'][root_file]['obs_data']['scan_status'] = scan_status
         else:
            print("   INFO: NEED TO GET SCAN STATUS!")
            scan_status = self.get_scan_status(root_file)
            self.rec_data['meteor_index'][root_file]['obs_data']['scan_status'] = scan_status
         scan_status = self.rec_data['meteor_index'][root_file]['obs_data']['scan_status']
         print(root_file, mfd, peak_int, scan_status )
      print("FILES NEEDING MANUAL REVIEW!")
      for root_file in self.rec_data['needs_review']:
         if "scan_status" in self.rec_data['meteor_index'][root_file]['obs_data']:
            scan_status = self.rec_data['meteor_index'][root_file]['obs_data']['scan_status']
         else:
            scan_status = 0
         print(root_file, scan_status)


   def get_scan_status(self, root_file):
      mfile = "/mnt/ams2/meteors/" + root_file[0:10] + "/" + root_file + ".json"
      scan_status = {}
      scan_status['jobs'] = [] 
      scan_status['mets'] = [] 
      scan_status['status'] = ""
      scan_status['problems'] = []
      meteor_scan_run = 0
      meteor_scan_meteors = 0
      meteor_crop_scan_run = 0
      meteor_crop_scan_meteors = 0
      meteor_hd_crop_scan_run = 0
      meteor_hd_crop_scan_meteors = 0
      resave_mj = 0
      if cfe(mfile) == 1:
         try:
            mj = load_json_file(mfile)
         except:
            mj = self.remake_mj(root_file)
            resave_mj = 1
            #exit()
         roi_good = 0
         if "roi" in mj:
            if sum(mj['roi']) > 0:
               roi_good = 1

         if "meteor_scan_meteors" in mj:
            meteor_scan_run = 1
            meteor_scan_meteors = len(mj['meteor_scan_meteors'])
         if "msc_meteors" in mj:
            meteor_crop_scan_run = 1
            if type(mj['msc_meteors']) == dict :
               mj['msc_meteors'] = self.fix_hd_scan_data(mj['msc_meteors'])
               print("FIXED MSC METEORS!")


            meteor_crop_scan_meteors = len(mj['msc_meteors'])

         if "meteor_scan_hd_crop_scan" in mj:
            if "meteors" in mj['meteor_scan_hd_crop_scan']:
               print("TYPE IS:",  type(mj['meteor_scan_hd_crop_scan']))
               mj['meteor_scan_hd_crop_scan'] = self.fix_hd_scan_data(mj['meteor_scan_hd_crop_scan']['meteors'])
               print("FIXED 1:", mfile)
            elif type(mj['meteor_scan_hd_crop_scan']) == dict :
               mj['meteor_scan_hd_crop_scan'] = self.fix_hd_scan_data(mj['meteor_scan_hd_crop_scan'])
               print("FIXED 2:", mfile)
            elif len(mj['meteor_scan_hd_crop_scan']) > 1:
               mj['meteor_scan_hd_crop_scan'] = self.only_meteors(mj['meteor_scan_hd_crop_scan'])

            meteor_hd_crop_scan_run = 1
            meteor_hd_crop_scan_meteors = len(mj['meteor_scan_hd_crop_scan'])
         scan_status['jobs'] = [meteor_scan_run, meteor_crop_scan_run, meteor_hd_crop_scan_run] 
         scan_status['mets'] = [meteor_scan_meteors, meteor_crop_scan_meteors, meteor_hd_crop_scan_meteors] 
         if sum(scan_status['jobs']) == 3 and sum(scan_status['mets']) == 3 and roi_good == 1:
            scan_status['status'] = "GOOD"
         elif sum(scan_status['jobs']) == 0:
            scan_status['status'] = "SCAN NOT RUN"
         elif 0 < sum(scan_status['jobs']) < 3:
            if meteor_scan_run == 0:
               scan_status['problems'].append("METEOR SCAN HAS NOT RUN")
            if meteor_crop_scan_run == 0:
               scan_status['problems'].append("CROP SCAN HAS NOT RUN")
               scan_status['status'] = "NEEDS REVIEW"
            if meteor_hd_crop_scan_run == 0:
               scan_status['problems'].append("HD CROP HAS NOT RUN")
               scan_status['status'] = "NEEDS REVIEW"
         else:
            scan_status['status'] = "NEEDS REVIEW"
         if roi_good == 0:
            scan_status['problems'].append("NO ROI")

         mj['scan_status'] = scan_status
         save_json_file(mfile, mj)
      else: 
         print("   ERROR MF NOT FOUND:", mfile )
      return(scan_status)

   def only_meteors(self, objects):
      final_meteors = []
      for obj in objects:
         if "report" in obj :
            if obj['report']['class'] == "meteor":
               final_meteors.append(obj)
      return(final_meteors)

   def fix_hd_scan_data(self, hd_scan_data):
      final_hd_meteors = []
      print(hd_scan_data)
      for obj_id in hd_scan_data:
         obj = hd_scan_data[obj_id]
         if "report" in obj:
            print(obj['report'])
            if obj['report']['class'] == "meteor":
               print("METEOR FOUND!")
               final_hd_meteors.append(obj)
      print("FINAL:", final_hd_meteors)
      return(final_hd_meteors)

            
   def get_cloud_media(self, year=None):
      if year is not None:
         cloud_files_file = "/mnt/ams2/METEOR_SCAN/DATA/cloud_files_" + year + ".txt"
         cloud_wild = "/mnt/archive.allsky.tv/" + self.station_id + "/METEORS/" + year + "/" 
      else:
         cloud_files_file = "/mnt/ams2/METEOR_SCAN/DATA/cloud_files_ALL.txt"
         cloud_wild = "/mnt/archive.allsky.tv/" + self.station_id + "/METEORS/"  
      if cfe(cloud_files_file) == 1:
         size, tdiff = get_file_info(cloud_files_file)
      if cfe(cloud_files_file) == 0 or tdiff > 10000:
         print("GETTING CLOUD FILES....")
         print ("find " + cloud_wild + " > " + cloud_files_file)
         os.system("find " + cloud_wild + " > " + cloud_files_file)
      fp = open(cloud_files_file)
      wild = year
      for line in fp:
         if wild is not None:
            if wild not in line:
               continue
         line = line.replace("\n", "")
         fn = line.split("/")[-1]
         fn = fn.replace(self.station_id + "_","")
         ext = fn.split("-")[-1]
         root = fn.replace("-" + ext, "")
         if root not in self.rec_data['meteor_index']:
            self.rec_data['meteor_index'][root] = {}
            self.rec_data['meteor_index'][root]['cloud_files'] = []
         if root in self.rec_data['meteor_index']:
            if "cloud_files" not in self.rec_data['meteor_index'][root]:
               self.rec_data['meteor_index'][root]['cloud_files'] = []
            self.rec_data['meteor_index'][root]['cloud_files'].append(ext)
            self.rec_data['meteor_index'][root]['cloud_files'] = sorted(list(set(self.rec_data['meteor_index'][root]['cloud_files'])))


   def get_scan_media(self, year, mon):
      media_files_file = "/mnt/ams2/METEOR_SCAN/DATA/media_files.txt"
      if mon is not None:
         wild = year + "_" + mon
      else :
         wild = year
      os.system("find /mnt/ams2/METEOR_SCAN/ > " + media_files_file)
      fp = open(media_files_file)
      for line in fp:
         if wild not in line:
            continue
         line = line.replace("\n", "")
         fn = line.split("/")[-1]
         fn = fn.replace(self.station_id + "_","")
         ext = fn.split("-")[-1]
         root = fn.replace("-" + ext, "")
         
         if root in self.rec_data['meteor_index']:
            if "exts" not in self.rec_data['meteor_index'][root]:
               self.rec_data['meteor_index'][root]['exts'] = []
               self.rec_data['meteor_index'][root]['cloud_files'] = []
            self.rec_data['meteor_index'][root]['exts'].append(ext)
            self.rec_data['meteor_index'][root]['exts'] = sorted(list(set(self.rec_data['meteor_index'][root]['exts'])))


   def update_cloud_index(self, year=None,month=None):
      if year is not None and month is not None:
         cloud_index_file = "/mnt/ams2/METEOR_SCAN/DATA/cloud_index_" + year + "_" + month + ".json"
      elif year is not None:
         cloud_index_file = "/mnt/ams2/METEOR_SCAN/DATA/cloud_index_" + year + ".json"
      else:
         cloud_index_file = "/mnt/ams2/METEOR_SCAN/DATA/cloud_index_ALL.json"
      if cfe(cloud_index_file) == 1:
         cloud_index = load_json_file(cloud_index_file)
      else:
         cloud_index = {}
      print("   FUNC: UPDATE CLOUD INDEX")
      if month is not None:
         wild = year + "_" + month
      else:
         wild = year 
      cloud_dir = "/mnt/archive.allsky.tv/" + self.station_id + "/METEORS/" + year + "/" 
      cloud_dirs = glob.glob(cloud_dir + wild + "*")
      for cdir in cloud_dirs:
         cfs = glob.glob(cdir + "/*") 
         for cff in cfs:
            if "info" in cff:
               continue
            cf = cff.split("/")[-1]
            elm = cf.split("-")
            ext = elm[-1]
            if "-SD-" in cf or "-HD-" in cf or "-prev-" in cf or "-crop" in cf:
               print("LEGACY FILE. SHOULD DELETE!", cff)
               cmd = "rm " + cff
               os.system(cmd)
               print(cmd)
            root_file = cf.replace("-" + ext, "")
            root_file = root_file.replace("-SD", "")
            root_file = root_file.replace("-HD", "")
            root_file = root_file.replace("-prev", "")
            if root_file not in cloud_index:
               cloud_index[root_file] = {}
               cloud_index[root_file]['cloud_files'] = []
       
            cloud_index[root_file]['cloud_files'].append(ext)
            cloud_index[root_file]['cloud_files'] = sorted(list(set(cloud_index[root_file]['cloud_files'])))
            
         print(cdir)
      save_json_file(cloud_index_file, cloud_index)
      print("SAVED:", cloud_index_file)

   def fix_missing_cloud_files(self, year,month):
      today = datetime.now().strftime("%Y_%m_%d")
      cur_y,cur_m,cur_d = today.split("_") 
      if cur_y == year and cur_m == month:
         
         day_limit = int(cur_d)
      else:
         day_limit = int(31)
      print(cur_y,cur_m,cur_d)
      print("DL:", day_limit)
      from calendar import monthrange
      num_days = monthrange(int(year), int(month))[1]
      for d in range(1,num_days+1):
         if d >= day_limit + 1:
            continue
         if d < 10:
            day = str(year) + "_" + str(month) + "_" + "0" + str(d)
         else:
            day = str(year) + "_" + str(month) + "_"  + str(d)

         cmd = "python3 Meteor.py 8 " + day 
         print(cmd)
         os.system(cmd)

   def reconcile_cloud_media(self, year, month):
      cloud_index_file = "/mnt/ams2/METEOR_SCAN/DATA/cloud_index_" + year + "_" + month
      if cfe(cloud_index_file) == 1:
         cloud_index = load_json_file(cloud_index_file)
      else:
         cloud_index = {}
      for root_file in self.rec_data['meteor_index']:
         date = root_file[0:10]
         meteor_file = "/mnt/ams2/meteors/" + date + "/" + root_file + ".json"
         if "cloud_files" in self.rec_data['meteor_index'][root_file]:
            if root_file in cloud_index:
               print("   *** USING CLOUD INDEX FILES!")
               self.rec_data['meteor_index'][root_file]['cloud_files'] = cloud_index[root_file]
            cloud_files = self.rec_data['meteor_index'][root_file]['cloud_files']
            ext_files = self.rec_data['meteor_index'][root_file]['exts']
         else:
            self.rec_data['meteor_index'][root_file]['cloud_files'] = []
            print("MISSING CLOUD FIELD!?", root_file)
            #continue 
         if "ROI.jpg" not in cloud_files or "ROI.mp4" not in cloud_files:
            if "hc" not in self.rec_data['meteor_index'][root_file]['obs_data']:
               self.rec_data['meteor_index'][root_file]['obs_data'] = make_obs_data(self.station_id, date, meteor_file) 

         # MAKE DECISION ABOUT WHAT TO UPLOAD. 
         # LEVEL 1 -- ALL FILES SHOULD AT LEAST HAVE THE prev.jpg file
         # LEVEL 2 -- ALL FILES WITH METEOR SCAN METEORS OR CROP METEORS SHOULD HAVE THE FULL SD SET (prev.jpg, SD.jpg, SD.mp4, ROI.mp4)
         # LEVEL 3 -- ALL FILES WITH MSM DETECTIONS OR A HUMAN CONFIRMED METEOR SHOULD HAVE THE FULL SD & HD SET (prev.jpg, SD.jpg, SD.mp4, ROI.mp4)
         scan_confirmed = 0
         human_confirmed = 0
         msm_confirmed = 0
         if "hc" in self.rec_data['meteor_index'][root_file]['obs_data']:
            if self.rec_data['meteor_index'][root_file]['obs_data']['hc'] == 1:
               #HUMAN CONFIRMED
               human_confirmed = 1

         if "roi" in self.rec_data['meteor_index'][root_file]['obs_data']:
            if sum(self.rec_data['meteor_index'][root_file]['obs_data']['roi']) > 0:
               #METEOR SCAN CONFIRMED
               scan_confirmed = 1
         if "event_id" in self.rec_data['meteor_index'][root_file]['obs_data']:
            if self.rec_data['meteor_index'][root_file]['obs_data']['event_id'] != 0:
               #MULTI-STATION CONFIRMED
               msm_confirmed = 1

         sync_level = 0
         if scan_confirmed == 0:
            sync_level = 1
         if scan_confirmed == 1:
            sync_level = 2
         if human_confirmed == 1 or msm_confirmed == 1:
            sync_level = 3
         print(root_file, "SYNC LEVEL:", sync_level, scan_confirmed, human_confirmed, msm_confirmed)
         if sync_level >= 1:
            # METEOR SCAN FAILED ONLY PUT UP THE prev.jpg
            ci_key = self.station_id + "_" + root_file 
            if ci_key in cloud_index:
               if "prev.jpg" not in cloud_index[ci_key]:
                  self.sync_prev(root_file)
         if sync_level >= 2:
            self.sync_sd_files(root_file, cloud_index)
            # SYNC PREV and ALL SD MEDIA: prev.jpg, SD.mp4, SD.jpg, ROI.jpg, ROI.mp4


   def sync_sd_files(self, root_file, cloud_index):
      sd_exts = ['prev.jpg', 'SD.mp4', 'SD.jpg', 'ROI.jpg', 'ROI.mp4']
      date = root_file[0:10]
      if root_file in cloud_index:
         self.rec_data['meteor_index'][root_file]['cloud_files'] = cloud_index[root_file]
      else:
         self.rec_data['meteor_index'][root_file]['cloud_files'] = []
         cloud_index[root_file] = []

      year = root_file[0:4]
      for ext in sd_exts:
         if ext == "prev.jpg":
            skiping = 1
         elif ext not in self.rec_data['meteor_index'][root_file]['cloud_files'] or (ext == "SD.mp4" and "ROI.mp4" not in self.rec_data['meteor_index'][root_file]['cloud_files'] ):
            ms_file = "/mnt/ams2/METEOR_SCAN/" + date + "/" + self.station_id + "_" + root_file + "-" + ext 
         
            if cfe(ms_file) == 0 and "SD.mp4" in ms_file:
               cmd = "python3 Meteor.py 3 " + root_file + ".json"
               print("SD FILE IS MISSING. TRY RESCAN", root_file)
               print(cmd)
               os.system(cmd)

            cloud_file = "/mnt/archive.allsky.tv/" + self.station_id + "/METEORS/" + date[0:4] + "/" + date + "/" + self.station_id + "_" + root_file + "-" + ext
            self.rec_data['meteor_index'][root_file]['cloud_files'] = cloud_index[root_file]
            if cfe(cloud_file) == 0:
               cmd = "cp " + ms_file + " " + cloud_file
               print(cmd)
               os.system(cmd)
         else:
            print("FILE IN CLOUD ALREADY", root_file, ext)
         

   def sync_prev(self, root_file):
      date = root_file[0:10]
      local_prev = "/mnt/ams2/meteors/" + date + "/cloud_files/" + self.station_id + "_" + root_file + "-prev.jpg"
      ms_prev = "/mnt/ams2/METEOR_SCAN/" + date + "/" + self.station_id + "_" + root_file + "-prev.jpg"
      cloud_prev = "/mnt/archive.allsky.tv/" + self.station_id + "/METEORS/" + date[0:4] + "/" + date + "/" + self.station_id + "_" + root_file + "-prev.jpg"
      if cfe(local_prev) == 1:
         print("LOCAL prev.jpg EXISTS", root_file)
         cmd = "cp " + local_prev + " " + cloud_prev
         print(cmd)
         os.system(cmd)
         self.rec_data['meteor_index'][root_file]['cloud_files'].append("prev.jpg")

      elif cfe(ms_prev) == 1:
         print("METEOR SCAN prev.jpg EXISTS", root_file)
         cmd = "cp " + local_prev + " " + cloud_prev
         print(cmd)
         os.system(cmd)
         self.rec_data['meteor_index'][root_file]['cloud_files'].append("prev.jpg")
      else:
         print("NO PREV FILE EXISTS YET!", root_file)
         cmd = "cp " + local_prev + " " + cloud_prev
         print(cmd)
         os.system(cmd)
      


   def reconcile_media(self):
      self.missing_scans = []
      print("REC MEDIA")
      """ 
          FOR MEDIA WE WANT TO DO THIS IN 3 PHASES
          1) Push the AWS data and prev thumbnail and that is it
          2) For successful meteor scan meteors upload the SD video, ROI video, ROI thumb, SD STACK IMAGE (here we wil have 5 total files: prev.jpg, SD.jpg, ROI.jpg SD.mp4 ROI.mp4
          3) For MSM or HC confirmed meteors, push the HD files too -- we will add HD.mp4 HDROI.mp4 HD.jpg and ROIHD.jpg (4 more files)
          If the meteor is confirmed and all media is sync'd there should be a total of 9 files for the meteor inside the METEOR_SCAN DIR
          If these don't exist yet, then the scan was not run, but should be. 

          * CAP THIS / ONLY DO OPTION 1 if there are more than 100 meteors for the day. 
          * IF THERE ARE MORE THAN 200 meteors, abort unless it is Aug 8-16 or Dec 10-16
      """
      for root_file in self.rec_data['meteor_index']:
         if "exts" not in self.rec_data['meteor_index'][root_file]:
            self.rec_data['meteor_index'][root_file]['exts'] = []
         obs_data = self.rec_data['meteor_index'][root_file]['obs_data']
         date = root_file[0:10]
         mdir = "/mnt/archive.allsky.tv/" + self.station_id + "/METEORS/" + date + "/" 
         if cfe(mdir, 1) == 0:
            os.makedirs(mdir)
         # IS THERE FRAME DATA?
         # AREA THERE EXTS? HAS ALL MEDIA BEEN MADE?
         # WHAT HAS BEEN SYNC'D?
         if "meteor_frame_data" in self.rec_data['meteor_index'][root_file]['obs_data']:
            mfd = len(self.rec_data['meteor_index'][root_file]['obs_data']['meteor_frame_data'])
         else:
            mfd = 0
         if "exts" in self.rec_data['meteor_index'][root_file]:
            ext = self.rec_data['meteor_index'][root_file]['exts']
         else:
            ext = 0
         if "cloud_files" in self.rec_data['meteor_index'][root_file]:
            cloud_files = self.rec_data['meteor_index'][root_file]['cloud_files']
         else: 
            cloud_files = {}
         if "ROI" not in cloud_files:
            cloud_missing = 1

         exts_missing = 0         
         missing_media = []
         for ext_type in self.media_exts: 
            if root_file in self.rec_data['meteor_index']:
               if "exts" not in self.rec_data['meteor_index'][root_file]:
                  self.rec_data['meteor_index'][root_file]['exts'] = []
               #print(self.rec_data['meteor_index'][root_file])
               #print("KEYS:", root_file, self.rec_data['meteor_index'][root_file].keys())
               if ext_type not in self.rec_data['meteor_index'][root_file]['exts']:
                  exts_missing = 1
                  missing_media.append(ext_type)

           
         if "ROI.jpg" in missing_media or "ROI.mp4" in missing_media:
            self.missing_scans.append(root_file)

         #print(root_file, mfd, exts_missing, cloud_missing, missing_media)
         #print(ext)
         #print(cloud_files)

      # SCAN METEORS THAT HAVEN'T BEEN SCANNED YET (this will create missing media) 
      mc = 0
      for root_file in self.missing_scans:
         if root_file in self.rec_data['corrupt_json']:
            continue 
         # before rescanning check 2 things. 
         # 1) has the scan already run but failed? if there is no "meteor_scan_meteors" meteors then this is the case
         # 2) is the ROI field missing or are they all zeros. If this is the case a meteor was not detected, so we shouldn't scan. 
         # 3) save as a 'scan_failure' so we don't redo this!
         # 4) scan failures will be treated as LEVEL 1 syncs. -- only thumb and data.
         date = root_file[0:10]
         meteor_file = "/mnt/ams2/meteors/" + date + "/" + root_file + ".json"
         scan_failed = 0
         if cfe(meteor_file) == 1:
            scan_failed = 0
            try:
               mj = load_json_file(meteor_file)
               if "roi" in mj:
                  sum_roi = sum(mj['roi'])
               if "meteor_scan_meteors" in mj:
                  if len(mj['meteor_scan_meteors']) == 0:
                     # the scan has run but it has failed. if the sum roi is 0 there is no hope for this file. 
                     scan_failed = 1
                     
               
            except:
               print("CORRUPT FILE or DELETED?", root_file)
               self.rec_data['corrupt_json'].append(root_file)
               continue
         if scan_failed != 1:
            cmd = "python3 Meteor.py 3 " + root_file + ".json"
            print(mc, cmd)
            os.system(cmd)
            self.rec_data['meteor_index'][root_file]['obs_data'] = make_obs_data(self.station_id, date, meteor_file) 
            mc += 1
         else:
            print("The scan for this meteor has failed and the ROI is 0. There is nothing we can do. Maybe it is a false or dim meteor.")
            print("This file needs review!")
             
            self.rec_data['needs_review'].append(root_file)

   def get_all_meteor_files(self, year=None, month=None ):
      if month is not None and year is not None:
         mdirs = glob.glob("/mnt/ams2/meteors/" + year + "_" + month + "*")
      elif year is not None:
         mdirs = glob.glob("/mnt/ams2/meteors/" + year + "*")
      else:
         mdirs = glob.glob("/mnt/ams2/meteors/*")
      mds = []
      for md in mdirs:
         if cfe(md,1) == 1:
            mds.append(md + "/")

      for md in sorted(mds,reverse=True):
         print(md)
         self.get_mfiles(md)

   def get_mfiles(self, mdir):
      temp = glob.glob(mdir + "/*.json")
      for json_file in temp:
          if "frame" not in json_file and "import" not in json_file and "report" not in json_file and "reduced" not in json_file and "calparams" not in json_file and "manual" not in json_file and "starmerge" not in json_file and "master" not in json_file:
            root = json_file.split("/")[-1].replace(".json", "")

            self.mfiles.append(root)

   def remake_mj(self, root_file):
      mfile = "/mnt/ams2/meteors/" + root_file[0:10] + "/" + root_file + ".json"
      (f_datetime, cam, f_date_str,fy,fmon,fd, fh, fm, fs) = convert_filename_to_date_cam(root_file)
      base_file = fy + "_" + fmon + "_" + fd + "_" + fh + "_" + fm
      hd_wild = "/mnt/ams2/meteors/" + root_file[0:10] + "/" + base_file + "*HD-meteor.mp4"
      pos_hds = glob.glob(hd_wild)
      def_mj = {}
      def_mj['sd_video_file'] = mfile.replace(".json", ".mp4")
      def_mj['sd_stack'] = mfile.replace(".json", "-stacked.jpg")

      if len(pos_hds) >= 1:
         def_mj['hd_trim'] = pos_hds[0]
         def_mj['hd_stack'] = pos_hds[0].replace(".mp4", "-stacked.mp4")
         def_mj['hd_video_file'] = pos_hds[0]
      return(def_mj)


   def make_meteor_frame_data(self, obj, mjf):
      (f_datetime, cam, f_date_str,fy,fmon,fd, fh, fm, fs) = convert_filename_to_date_cam(mjf)
      trim_num = get_trim_num(mjf)
      extra_sec = int(trim_num) / 25
      trim_start_time = f_datetime + ddtt.timedelta(0,extra_sec)
      print("TRIM START TIME IS:", trim_start_time)


      if cfe(mjf) == 1:
         try:
            mj = load_json_file(mjf)
         except:
            return([])

      if "oxs" not in obj:
         # current object doesn't have a meteor... try using the ms_crop or meteor_scan 
         found = 0
         if "msc_meteors" in mj:
            if len(mj['msc_meteors']) > 0:
               obj = mj['msc_meteors'][0]
               found = 1
         if found == 0:
            if "meteo_scan_meteors" in mj:
               if len(mj['msc_meteors']) > 0:
                  obj = mj['msc_meteors'][0]
                  found = 1
      if found == 0:
         # NO METEOR FOUND SO WE CAN'T MAKE MFD
         return([])

      if "cp" in mj:
         cp = mj['cp']
      sd_w = 704
      sd_h = 576
      if "ffp" in obj:
         if "sd" in obj['ffp']:
            sd_w,sd_h,br,fr = obj['ffp']['sd']
      self.hdm_x = 1920 / int(sd_w)
      self.hdm_y = 1080 / int(sd_h)
      # don't forget to add the user_mods / user overrides.
      obj['meteor_frame_data'] = []
      # for 720 to 1080
      #hdm_x = 1920 / 1280
      #hdm_y = 1080 / 720
      if True:
         min_x = min(obj['oxs'])
         max_x = max(obj['oxs'])
         min_y = min(obj['oys'])
         max_y = max(obj['oys'])
         self.crop_box = [int(min_x*self.hdm_x),int(min_y*self.hdm_y),int(max_x*self.hdm_x),int(max_y*self.hdm_y)]
         for i in range(0, len(obj['ofns'])):

            fn = obj['ofns'][i]
            extra_sec = fn / 25
            frame_time = trim_start_time + ddtt.timedelta(0,extra_sec)
            frame_time_str = frame_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            dt = frame_time_str


            ccx = int(obj['oxs'][i] + (obj['ows'][i]/2))
            ccy = int(obj['oys'][i] + (obj['ohs'][i]/2))

            x = int(ccx * self.hdm_x)
            y = int(ccy * self.hdm_y)

            w = obj['ows'][i]
            h = obj['ohs'][i]
            oint = obj['oint'][i]

            #sfn = str(fn)
            #if self.ufd is not None:
            #   if sfn in self.ufd:
            #      temp_x,temp_y = self.ufd[sfn]
            #      x = temp_x
            #      y = temp_y
            # need over rides for user_mods or human_points!

            tx, ty, ra ,dec , az, el = XYtoRADec(ccx,ccy,mjf,cp,self.json_conf)


            obj['meteor_frame_data'].append((dt, fn, x, y, w, h, oint, ra, dec, az, el))
      return(obj)
