
allsky_console = """
  ____  _      _      _____ __  _  __ __
 /    || |    | |    / ___/|  |/ ]|  |  |
|  o  || |    | |   (   \_ |  ' / |  |  |
|     || |___ | |___ \__  ||    \ |  ~  |
|  _  ||     ||     |/  \ ||     ||___, |
|  |  ||     ||     |\    ||  .  ||     |
|__|__||_____||_____| \___||__|\_||____/
*- O B S E R V I N G - S O F T W A R E -*

AllSky.com/ALLSKY7 - A.S.O.S.
Copywrite Mike Hankey LLC 2016-2022
Use permitted for licensed users only.
Contact mike.hankey@gmail.com for questions.
"""

docs = """
   MultiStationObs.py 
   Class for handling multi-station observations. 
       This class does follow up /QA work on obs that have been confirmed by other stations. 
       These are our 'best' obs and for these we want :
          - The full media (SD,HD,Stacks) SD/HD sync'd video? 
          - Confirmed / refit calibs 
          - Confirmed / Perfect points / QA points 
          - AI Confirmed?
          - In DynaDB and cloud?
          - Final status and event info, solved/failed/pending and solution
       We should also sync the solution for this event with the network db so changes sync back and forth. 
 
"""
import numpy as np
import cv2
import os
from lib.PipeUtil import load_json_file, save_json_file
from lib.roi_image import make_roi_image

class MultiStationObs():
   def __init__(self):

      # local station values
      self.json_conf = load_json_file("../conf/as6.json")
      self.station_id = self.json_conf['site']['ams_id']
      self.meteor_dir = "/mnt/ams2/meteors/"
      self.meteor_scan_dir = "/mnt/ams2/METEOR_SCAN/"
      self.event_dir = "/mnt/ams2/EVENTS/"

      # cloud values
      self.cloud_dir = "/mnt/archive.allsky.tv/"
      self.cloud_event_dir = "/mnt/archive.allsky.tv/EVENTS/"
      self.cloud_host = "https://archive.allsky.tv/"   

   def load_obs(self, obs_id):
      if "AMS" in obs_id:
         st = obs_id.split("_")[0]
         obs_id = obs_id.replace(st + "_", "")
      self.root_file = obs_id
      self.obs_id = self.station_id + "_" + self.root_file

      self.mdate = self.root_file[0:10]
      self.mdir = self.meteor_dir + self.mdate + "/" 
      self.myear = self.root_file[0:4]
      self.cloud_mdir = self.cloud_dir + self.station_id + "/METEORS/" + self.myear + "/" + self.mdate + "/"
      self.msdir = self.meteor_scan_dir + self.mdate + "/"
      self.meteor_file = self.mdir + self.root_file + ".json"
      self.meteor_reduced_file = self.mdir + self.root_file + "-reduced.json"
      self.meteor_stack_file = self.mdir + self.root_file + "-stacked.jpg"

      if os.path.exists(self.meteor_stack_file) is True:
         self.meteor_stack_image = cv2.imread(self.meteor_stack_file)
      else:
         self.meteor_stack_image = None
         exit()

      if os.path.exists(self.meteor_file) is True:
         try:
            self.meteor_json = load_json_file(self.meteor_file)
         except:
            self.meteor_json = None
            print("Could not load:", self.meteor_file)
            return()
      else:
         self.meteor_json = None
         print("Could not load:", self.meteor_file)
         return()
      if os.path.exists(self.meteor_reduced_file) is True:
         self.meteor_reduced_json = load_json_file(self.meteor_reduced_file)
      else:
         print("Could not load:", self.meteor_reduced_file)
         self.meteor_reduced_json = None
         return()

      self.sd_vid = self.meteor_file.replace(".json", ".mp4")
      if self.meteor_json is not None:
         if "hd_trim" in self.meteor_json:
            self.hd_vid = self.meteor_json['hd_trim']
            self.hd_stack = self.hd_vid.replace(".mp4", "-stacked.jpg")

      if "final_media" in self.meteor_json:
         self.final_media = self.meteor_json['final_media']
      else: 
         self.final_media = {}
      self.final_media_types = ['1080p.mp4', '360p.mp4', '180p.mp4', '1080p.jpg', '360p.jpg', 'prev.jpg', 'ROI.jpg']
      for mt in self.final_media_types:
         if mt not in self.final_media:
            self.final_media[mt] = {}
            self.final_media[mt]['local_file'] = self.msdir + self.obs_id + "-" + mt
            self.final_media[mt]['local_file_exists'] = os.path.exists(self.final_media[mt]['local_file'])
      for k in self.final_media:
         if k == "ROI.jpg":
            if self.final_media[k]['local_file_exists'] is False:
           
               if self.meteor_reduced_json is not None:
                  xs = [row[2] + int(row[4]/2) for row in self.meteor_reduced_json['meteor_frame_data']]
                  ys = [row[3] + int(row[5]/2) for row in self.meteor_reduced_json['meteor_frame_data']]
                  ax = int(np.mean(xs))
                  ay = int(np.mean(ys))
                  stacked_image_hd = cv2.resize(self.meteor_stack_image, (1920,1080))
                  x1,y1,x2,y2,roi_img = make_roi_image(ax,ay,1,1,224,stacked_image_hd,None, (1920,1080))
                  cv2.imwrite(self.final_media[mt]['local_file'], roi_img)
               else:
                  print("Meteor not reduced.")
      

