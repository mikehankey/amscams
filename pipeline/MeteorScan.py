#!/usr/bin/python3

# this script will scan a single meteor dir or all meteor dirs 
# and for each meteor it will run the AI image predict on the stack image.
# it will compile a list of files and results in each dir called AMSXX_YYYY_MM_DD_AI_SCAN.info
#

import numpy as np
import sys
from lib.PipeUtil import load_json_file, save_json_file , mfd_roi, get_file_info
import os
import cv2
from lib.ASAI_Predict import predict_images
import glob
import tensorflow as tf
import os
from tensorflow import keras
from tensorflow.keras.models import *
import tensorflow.keras
from tensorflow.keras.models import load_model
from tensorflow.keras.models import Sequential
from tensorflow.keras.preprocessing.image import ImageDataGenerator, array_to_img, img_to_array, load_img

from Classes.MLMeteors import MLMeteors
from Classes.ASAI import AllSkyAI 

def scan_meteors_for_day(station_id, date):
   
   ASAI = AllSkyAI()
   ASAI.load_all_models()
   MLM = MLMeteors()
   msdir = "/mnt/ams2/METEOR_SCAN/" + date + "/" 
   roi_files, non_reduced_files, ai_data, ai_data_file = MLM.load_meteors_for_day(date, station_id)

   print("ROI FILES:", len(roi_files))
   print("NON REDUCED METEORS:", len(non_reduced_files))
   print("AI DATA:", len(ai_data.keys()))
   print("AI DATA KEYS:", ai_data.keys())
   for mfile in non_reduced_files:
      print(mfile)
      ai_data[mfile] = {} 
   exit()
   for roi_f in roi_files:
      roi_fn = roi_f.split("/")[-1]
      #print(key, ai_data[key])
      roi_file = msdir + roi_fn 
      resp = ASAI.meteor_yn(roi_file)
      if roi_fn not in ai_data:
         ai_data[roi_fn] = {}
      ai_data[roi_fn]['classes'] = resp
   
   print("saved:", ai_data_file)
   save_json_file(ai_data_file, ai_data)
json_conf = load_json_file("../conf/as6.json")
meteor_dir = "/mnt/ams2/meteors/"

station_id = json_conf['site']['ams_id']
date = sys.argv[1]
if date != "ALL":
   scan_meteors_for_day(station_id, date)
else:
   all_dirs = os.listdir(meteor_dir)
   for date in sorted(all_dirs, reverse=True):
      print(date)
      if os.path.isdir(meteor_dir + date) is True:
         scan_meteors_for_day(station_id, date)
