import numpy as np
import sys
from lib.PipeUtil import load_json_file, save_json_file
import os
import cv2
from lib.ASAI_Predict import predict_images
import glob

roi_files = []
machine_data_file = "/mnt/ams2/datasets/machine_data_meteors.json"
dataset = "/mnt/ams2/datasets/images/repo/meteors/"
machine_data = load_json_file(machine_data_file)

lfs = glob.glob(dataset + "*")
c = 0
for lf in lfs:
   if "/" in lf:
      fn = lf.split("/")[-1]
   if "\\" in lf:
      fn = lf.split("\\")[-1]

   if fn not in machine_data:
   #   print(c, "SKIP")
   #   if fn in machine_data:
   #      print("HAVE:", machine_data[fn])
   #      continue
   #   else:
   #      print("missing:", machine_data[fn])
      print(c, fn)
      roi_files.append(lf)
   elif machine_data[fn][1] > .5:
      print(c, fn)
      roi_files.append(lf)
   c += 1

model = "./first_try_model.h5"
label = "meteors"
predict_images(roi_files, model, label )
