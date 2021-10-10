import os
import scipy.optimize
import numpy as np
import datetime
import cv2
from pathlib import Path
import glob


from lib.PipeAutoCal import gen_cal_hist,update_center_radec, get_catalog_stars, pair_stars, scan_for_stars, calc_dist, minimize_fov, AzEltoRADec , HMS2deg, distort_xy , XYtoRADec, angularSeparation, use_default_cal
from lib.PipeUtil import load_json_file, save_json_file, cfe
from Classes.Camera import Camera

class CleanCal():
   def __init__(self, station_id):
      print("Clean Cal.")
      json_conf = load_json_file("../conf/as6.json")
      self.station_id = json_conf['site']['ams_id']
      self.lat = json_conf['site']['device_lat']
      self.lon = json_conf['site']['device_lng']
      self.alt = json_conf['site']['device_alt']
      self.fc_files = []
      self.fc_index = []
      self.bad_fc_files = []
      self.best_fc_files = []

   def load_freecal_files(self):
      fc_dirs = glob.glob("/mnt/ams2/cal/freecal/*")
      for fcd in fc_dirs:
         cal_name = fcd.split("/")[-1]
         cal_file1 = fcd + "/" + cal_name + "-stacked-calparams.json"
         cal_file2 = fcd + "/" + cal_name + "-calparams.json"
         if cfe(cal_file1) == 1:
            print("FOUND:", cal_file1)
            self.fc_files.append(cal_file1)
         elif cfe(cal_file2) == 1:
            print("FOUND:", cal_file2)
            self.fc_files.append(cal_file2)
         else:
            print("NO CAL FILE FOUND MISSING:", cal_file2, cal_file2)

   def load_freecal_index(self):
      temp = load_json_file("/mnt/ams2/cal/freecal_index.json")
      for key in temp:
         data = temp[key]
         data['key'] = key
         if "total_res_px" in data:
            self.fc_index.append(data)
         else:
            print("PX MISSING?", data)
      self.fc_index = sorted(self.fc_index, key=lambda x: x['total_res_px'], reverse=False)      
      for data in self.fc_index:
         print(data['cam_id'], data['total_res_px'], data['key'])


   
