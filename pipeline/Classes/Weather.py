from decimal import Decimal
import pickle
import glob
import json
import math
import os
import scipy.optimize
import numpy as np
import datetime
import cv2
from sklearn import linear_model, datasets
from skimage.measure import ransac, LineModelND, CircleModel

from sklearn.linear_model import RANSACRegressor
from sklearn.datasets import make_regression

from PIL import ImageFont, ImageDraw, Image, ImageChops

from Classes.DisplayFrame import DisplayFrame
from Classes.Detector import Detector
from Classes.Camera import Camera
from Classes.Event import Event
from Classes.Calibration import Calibration
from lib.PipeAutoCal import gen_cal_hist,update_center_radec, get_catalog_stars, pair_stars, scan_for_stars, calc_dist, minimize_fov, AzEltoRADec , HMS2deg, distort_xy, XYtoRADec, angularSeparation
from lib.PipeUtil import load_json_file, save_json_file, cfe
from lib.FFFuncs import best_crop_size, ffprobe
import boto3
import socket
import sys



class Weather():

   def __init__(self):
      self.show = 1
      json_conf = load_json_file("../conf/as6.json")
      self.station_id = json_conf['site']['ams_id']
      self.cams = []
      for cam_num in json_conf['cameras']:
         cams_id = json_conf['cameras'][cam_num]['cams_id']
         self.cams.append(cams_id)

   def index_local_stacks(self):
      local_stack_dir = "/mnt/ams2/METEOR_ARCHIVE/" + self.station_id + "/STACKS/" 
      stack_hist_file = local_stack_dir + self.station_id + "_hour_stack_history.json"
      # day/night stack files
      dns_hist_file = local_stack_dir + self.station_id + "_day_night_stack_history.json"
      if cfe(stack_hist_file) == 1:
         sds = load_json_file(stack_hist_file)
      else:
         sds = {}
      if cfe(stack_hist_file) == 1:
         dns = load_json_file(dns_hist_file)
      else:
         dns = {}

      stack_dirs = glob.glob(local_stack_dir + "*") 
      dc = 0
      for sd in sorted(stack_dirs, reverse=True):
         if cfe(sd, 1) != 1:
            continue
         day = sd.split("/")[-1]
         if day in sds and dc > 3:
            print("This is already done.", day)
         else:
            sds[day] = {} 
            dns[day] = {} 
            sds[day]['hour_stack_files'] = []
            dns[day]['day_stacks'] = []
            dns[day]['night_stacks'] = []
            sfs = glob.glob(sd+ "/*.jpg")
            for sf in sfs:
               sfn = sf.split("/")[-1]
               sfn = sfn.replace(day + "_", "")
               sfn = sfn.replace(".jpg", "")
               if "night" in sfn:
                  dns[day]['night_stacks'].append(sfn)
               elif "day" in sfn:
                  dns[day]['day_stacks'].append(sfn)
               else :
                  sds[day]['hour_stack_files'].append(sfn)
            save_json_file(sd + "_hours.json", sds[day]['hour_stack_files'])
            dc += 1

      save_json_file(stack_hist_file, sds, True)
      save_json_file(dns_hist_file, dns, True)
      print(stack_hist_file)
      print(dns_hist_file)

   def index_weather_snaps_all(self):
      dirs = glob.glob("/mnt/ams2/latest/*")
      latest_dirs = []
      cc = 0
      for d in sorted(dirs,reverse=True):
         if cfe(d, 1) == 1:
            latest_dirs.append(d)
            save_file = d + "/history.json"
            if cfe(save_file) == 0 or cc < 2:
               self.index_weather_snaps_day(d)
            cc += 1

   def index_weather_snaps_day(self, day_dir):
      index = {}
      files = glob.glob(day_dir + "/*.jpg")
      for snap in sorted(files, reverse=True):
         snap_fn = snap.split("/")[-1]
         snap_el = snap_fn.split("_")
         
         key = snap_el[5] + snap_el[6][0]
         cam = snap_el[1]
         if key not in index:
            index[key] = {}
         if cam not in index[key]:
            index[key][cam] = {}
         index[key][cam]['snap_file'] = snap_fn

      final_index = {}
      for key in sorted(index.keys(), reverse=True):
         final_index[key] = {}
         print("IND", index[key])
         for cam in sorted(self.cams):
            if cam in index[key]:
               print("YES", key, cam, index[key][cam])
               final_index[key][cam] = index[key][cam]
            else:
               final_index[key][cam] = ""

         print(key, index[key])
      save_file = day_dir + "/history.json"
      save_json_file(save_file, final_index)
      cloud_file = save_file.replace("/mnt/ams2", "/mnt/archive.allsky.tv/" + self.station_id )
      cloud_file = cloud_file.replace("latest", "LATEST")
      print("SAVED:", save_file)
      cmd = "cp " + save_file + " " + cloud_file
      os.system(cmd)
 
