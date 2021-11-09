#!/usr/bin/python3 

import numpy as np
import sys
from lib.PipeUtil import load_json_file, save_json_file 
import os
import cv2
from lib.ASAI_Predict import predict_images
import glob

def get_mfiles(mdir):
   temp = glob.glob(mdir + "/*.json")
   mfiles = []
   for json_file in temp:
      if "import" not in json_file and "report" not in json_file and "reduced" not in json_file and "calparams" not in json_file and "manual" not in json_file and "starmerge" not in json_file and "master" not in json_file:
         vfn = json_file.split("/")[-1].replace(".json", ".mp4")
         mfiles.append(vfn)
   return(mfiles)

def mfd_roi(mfd=None, xs=None, ys=None):
   if mfd is not None:
      if len(mfd) == 0:
         return(0,0,1080,1080)
      xs = [row[2] for row in mfd]
      ys = [row[3] for row in mfd]
   x1 = min(xs) 
   y1 = min(ys) 
   x2 = max(xs) 
   y2 = max(ys) 
   mx = int(np.mean(xs))
   my = int(np.mean(ys))
   w = x2 - x1
   h = y2 - y1
   if w >= h:
      h = w
   else:
      w = h 
   if w < 150 or h < 150:
      w = 150
      h = 150
   if w > 1079 or h > 1079 : 
      w = 1060
      h = 1060 
   x1 = mx - int(w / 2)
   x2 = mx + int(w / 2)
   y1 = my - int(h / 2)
   y2 = my + int(h / 2)
   w = x2 - x1
   h = y2 - y1
   print("WH:", w,h)
   print("WH:", w,h)

   if x1 < 0:
      x1 = 0
      x2 = w
   if y1 < 0:
      y1 = 0
      y2 = h
   if x2 >= 1920:
      x2 = 1919 
      x1 = 1919 - w
   if y2 >= 1080:
      y2 = 1079 
      y1 = 1079 - h
   return(x1,y1,x2,y2)

def load_meteors_for_day(date, station_id):
   mdir = "Y:/meteors/" + date + "/"
   msdir = "Y:/METEOR_SCAN/" + date + "/"
   if os.path.isdir(msdir) is False:
      os.makedirs(msdir)
   mfiles = get_mfiles(mdir)
   roi_files = []
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

      if os.path.exists(msdir + roi_file) is False:
         print("NO ROI!", msdir + roi_file)
         if os.path.exists(mdir + mjrf):
            mjr = load_json_file(mdir + mjrf)      
            print("MFD:", len(mjr['meteor_frame_data']))
            if len(mjr['meteor_frame_data']) == 0:
               continue
               

            x1,y1,x2,y2 = mfd_roi(mjr['meteor_frame_data'])
            img = cv2.imread(mdir + stack_file)
            print(mdir + stack_file)
            img = cv2.resize(img, (1920,1080))
            roi_img = img[y1:y2,x1:x2]
            try:
               cv2.imshow('pepe', roi_img)
               cv2.waitKey(30)
               cv2.imwrite(msdir + roi_file, roi_img)
            except:
               continue
         else:
            print("NOT REDUCED :", mdir , mjrf)
      else:
         print("GOOD ROI !", msdir + roi_file)
      if os.path.exists(msdir + roi_file) is True:
         roi_files.append(msdir + roi_file)
   model = "./first_try_model.h5"
   label = "meteors"
   predict_images(roi_files, model, label )


if __name__ == "__main__":
   json_conf = load_json_file("../conf/as6.json")
   station_id = json_conf['site']['ams_id']
   date = sys.argv[1]

   all_days = glob.glob("Y:/meteors/*")
   for daydir in sorted(all_days, reverse=True):
      print(daydir)
      if os.path.isdir(daydir) is True:
         if "/" in daydir:
            date = daydir.split("/")[-1]
         if "\\" in daydir:
            date = daydir.split("\\")[-1]
         print(date)
         load_meteors_for_day(date, station_id)


