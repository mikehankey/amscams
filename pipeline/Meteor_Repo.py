#!/usr/bin/python3
import glob
from lib.PipeUtil import load_json_file,save_json_file
import os
import sys
# SCRIPT TO BATCH BUILD ALL ROI FILES AND POPULATE
# THE LEARNING REPO FOR METEORS


def get_mfiles(mdir):
   temp = glob.glob(mdir + "/*.json")
   mfiles = []
   for json_file in temp:
      if "cloud" not in json_file and "import" not in json_file and "report" not in json_file and "reduced" not in json_file and "calparams" not in json_file and "manual" not in json_file and "starmerge" not in json_file and "master" not in json_file:
         vfn = json_file.split("/")[-1].replace(".json", ".mp4")
         mfiles.append(vfn)
   return(mfiles)

def load_meteors_for_day(date, station_id):
   mdir = "/mnt/ams2/meteors/" + date + "/"
   msdir = "/mnt/ams2/METEOR_SCAN/" + date + "/"
   print(mdir)
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
         roi_files.append(msdir + roi_file)
   learn_dir = "/mnt/ams2/datasets/images/repo/meteors/"
   if os.path.isdir(learn_dir) is False:
      os.makedirs(learn_dir)
   for rf in roi_files:
      fn = rf.split("/")[-1]
      learn_file = learn_dir + fn
      if os.path.exists(learn_file) is True:
         print("Learn file exists.", learn_file)
      else:
         print("Learn file not found.", learn_file)
         cmd = "cp " + rf + " " + learn_file
         print(cmd)
         os.system(cmd)
   model = "./first_try_model.h5"
   label = "meteors"

   #predict_images(roi_files, model, label )

json_conf = load_json_file("../conf/as6.json")
mdirs = glob.glob("/mnt/ams2/meteors/*")
for md in mdirs:
   if os.path.is_dir(md) is True:
      date = md.split("/")[-1]
      load_meteors_for_day(date, json_conf['site']['ams_id'])
