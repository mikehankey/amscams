import cv2
import numpy as np
import os
from lib.PipeUtil import load_json_file, save_json_file

# Semi generic meteor object for working with remote meteors

class MeteorObject:
   def __init__(self, station_id, meteor_fn, work_dir):
      self.station_id = station_id
      self.meteor_fn= meteor_fn
      self.date = self.meteor_fn[0:10]
      self.work_dir = work_dir 

   def load_meteor_data(self, mjf=None,mjrf=None ):
      self.meteor_json_file = self.work_dir + self.meteor_fn
      self.meteor_red_file = self.work_dir + self.meteor_fn.replace(".json", "-reduced.json")
      if os.path.exists(self.meteor_json_file) is True:
         self.mj = load_json_file(self.meteor_json_file)
      if os.path.exists(self.meteor_json_file) is True:
         self.red_data = load_json_file(self.meteor_red_file)

   def load_video_file(self, video_file):
      print("Load frames per video file)
