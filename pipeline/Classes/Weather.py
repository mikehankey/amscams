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




class Weather():

   def __init__(self):
      self.show = 1
      json_conf = load_json_file("../conf/as6.json")
      self.station_id = json_conf['site']['ams_id']
      self.cams = []
      for cam_num in json_conf['cameras']:
         cams_id = json_conf['cameras'][cam_num]['cams_id']
         self.cams.append(cams_id)


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
 
