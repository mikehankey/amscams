import cv2
import glob
import os
import numpy as np
from PIL import ImageFont, ImageDraw, Image, ImageChops

#from lib.PipeUtil import load_json_file, save_json_file , get_file_info
from lib.PipeUtil import load_json_file, save_json_file , get_file_info, mfd_roi
import tensorflow as tf
import os
from tensorflow import keras
from tensorflow.keras.models import *
import tensorflow.keras
from tensorflow.keras.models import load_model
from tensorflow.keras.models import Sequential
from tensorflow.keras.preprocessing.image import ImageDataGenerator, array_to_img, img_to_array, load_img


class MLMeteors():

   def __init__(self):
      print("ML Meteors.")


   def disable_meteor(self, meteor_file):
      print("Disable meteor")
      meteor_day = meteor_file[0:10]
      meteor_dir = "/mnt/ams2/meteors/" + meteor_day + "/"
      non_meteor_dir = "/mnt/ams2/non_meteors/" + meteor_day + "/"
      if os.path.exists(non_meteor_dir) is False:
         os.makedirs(non_meteor_dir)
      mjf = meteor_dir + meteor_file
      sd_wild = mjf.replace(".mp4", "*")
      mj = load_json_file(mjf)
      if "hd_trim" in mj:
         hd_trim = mj['hd_trim']
         hd_wild = hd_trim.replace(".mp4", "*")
      else:
         hd_trim = None
         hd_wild = None
      print("SD WILD:", sd_wild)
      print("HD WILD:", hd_wild)

      cmd1 = "mv " + sd_wild + " " + non_meteor_dir
      print(cmd1)
      os.system(cmd1)

      cmd2 = "mv " + hd_wild + " " + non_meteor_dir
      print(cmd2)
      os.system(cmd2)

   def enable_meteor(self, meteor_file):
      print("Enable meteor")
      meteor_day = meteor_file[0:10]
      meteor_dir = "/mnt/ams2/meteors/" + meteor_day + "/"
      non_meteor_dir = "/mnt/ams2/non_meteors/" + meteor_day + "/"
      if os.path.exists(meteor_dir) is False:
         os.makedirs(meteor_dir)
      mjf = non_meteor_dir + meteor_file
      sd_wild = mjf.replace(".mp4", "*")
      mj = load_json_file(mjf)
      if "hd_trim" in mj:
         hd_trim = mj['hd_trim']
         hd_wild = hd_trim.replace(".mp4", "*")
      else:
         hd_trim = None
         hd_wild = None
      print("SD WILD:", sd_wild)
      print("HD WILD:", hd_wild)

      cmd1 = "mv " + sd_wild + " " + meteor_dir
      print(cmd1)
      os.system(cmd1)

      cmd2 = "mv " + hd_wild + " " + meteor_dir
      print(cmd2)
      os.system(cmd2)

      

   

   def load_meteors_for_day(self, date, station_id):
      dataset_dir = "/mnt/ams2/datasets/"
      if os.path.isdir(dataset_dir) is False:
         os.makedirs(dataset_dir)
      if os.path.isdir(dataset_dir + "/images/") is False:
         os.makedirs(dataset_dir + "/images/")
      if os.path.isdir(dataset_dir + "/images/repo/") is False:
         os.makedirs(dataset_dir + "/images/repo/")
      if os.path.isdir(dataset_dir + "/images/repo/meteors/") is False:
         os.makedirs(dataset_dir + "/images/repo/meteors/")
      if os.path.isdir(dataset_dir + "/images/repo/nonmeteors/") is False:
         os.makedirs(dataset_dir + "/images/repo/nonmeteors/")
      if os.path.isdir(dataset_dir + "/images/repo/trash/") is False:
         os.makedirs(dataset_dir + "/images/repo/trash/")
   
   
      human_data_file = "/mnt/ams2/datasets/human_data.json"
      label = "meteors"
      machine_data_file = "/mnt/ams2/datasets/machine_data.json"
      if os.path.exists(human_data_file):
         human_data = load_json_file(human_data_file)
      else:
         human_data = {}
   
      mdir = "/mnt/ams2/meteors/" + date + "/"
      msdir = "/mnt/ams2/METEOR_SCAN/" + date + "/"
   
      ai_day_file = mdir + station_id + "_" + date + "_AI_SCAN.info"
      if os.path.exists(ai_day_file):
         ai_day_data = load_json_file(ai_day_file)
      else:
         ai_day_data = {}
   
   
      if os.path.isdir(msdir) is False:
         os.makedirs(msdir)
      mfiles = self.get_mfiles(mdir)
   
   
      roi_files = []
      non_reduced_files = []
      for ff in sorted(mfiles, reverse=True):
         print(ff)
         if "/" in ff:
            ff = ff.split("/")[-1]
         if "\\" in ff:
            ff = ff.split("\\")[-1]
         json_file = ff.replace(".mp4", ".json")
         roi_file = station_id + "_" + ff.replace(".mp4", "-ROI.jpg")
   
         stack_file = ff.replace(".mp4", "-stacked.jpg")
         mjrf = json_file.replace(".json", "-reduced.json")
         remake = 0
         roi = None
         if os.path.exists(msdir + roi_file) is True:
            roi = cv2.imread(msdir + roi_file)
            if roi is None:
               print("BAD ROI IMAGE!")
               continue
            if roi.shape[0] < 150 or roi.shape[1] < 150:
               print("BAD ROI SHAPE REMAKE!")
               remake = 1
            if roi.shape[0] != roi.shape[1]:
               remake = 1
               print("BAD SHAPE:", msdir + roi_file)
            print("CHECKROI")
         else:
            non_reduced_files.append(json_file)
         #if os.path.exists(msdir + roi_file) is True:
         #   if roi is None:
         #      roi = cv2.imread(msdir + roi_file)
            #roi = check_roi(roi, msdir + roi_file)
         if remake == 1:
            print("REMAKE ROI:", msdir + roi_file)
         if roi_file in ai_day_data:
            if "roi" not in ai_day_data[roi_file]:
               print("ROI DATA MISSING FROM AI DATA FILE!!!", roi_file)
               remake = 1
         if os.path.exists(msdir + roi_file) is False or remake == 1 or roi_file not in ai_day_data:
            if os.path.exists(mdir + mjrf):
               try:
                  mjr = load_json_file(mdir + mjrf)
               except:
                  continue
               if "meteor_frame_data" not in mjr:
                  continue
               #print("MFD:", len(mjr['meteor_frame_data']))
               if len(mjr['meteor_frame_data']) == 0:
                  continue
   
   
               x1,y1,x2,y2 = mfd_roi(mjr['meteor_frame_data'])
               img = cv2.imread(mdir + stack_file)
               nw = x2 - x1
               nh = y2 - y1
               if roi_file not in ai_day_data:
                  ai_day_data[roi_file] = {}
               ai_day_data[roi_file]['roi'] = [x1,y1,x2,y2]
               if nw != nh:
                  print("W/H CROP PROBLEM!", msdir + roi_file)
                  input("wait")
               print(mdir + stack_file)
               try:
                  img = cv2.resize(img, (1920,1080))
                  roi_img = img[y1:y2,x1:x2]
               except:
                  continue
   
               try:
                  #cv2.imshow('pepe', roi_img)
                  #cv2.waitKey(30)
                  cv2.imwrite(msdir + roi_file, roi_img)
               except:
                  continue
            else:
               print("NOT REDUCED :", mdir , mjrf)
         else:
            print("GOOD ROI !", msdir + roi_file)
         if os.path.exists(msdir + roi_file) is True:
            if roi_file not in human_data :
               roi_files.append(msdir + roi_file)

      print(len(roi_files), " ROI FILES READY TO ANALYZE")
      save_json_file(ai_day_file, ai_day_data)
      return(roi_files, non_reduced_files, ai_day_data, ai_day_file)
      #predict_images(roi_files, model, label )
   
   def get_mfiles(self, mdir):
      temp = glob.glob(mdir + "/*.json")
      mfiles = []
      for json_file in temp:
         if "import" not in json_file and "report" not in json_file and "reduced" not in json_file and "calparams" not in json_file and "manual" not in json_file and "starmerge" not in json_file and "master" not in json_file:
            vfn = json_file.split("/")[-1].replace(".json", ".mp4")
            mfiles.append(vfn)
      return(mfiles) 
