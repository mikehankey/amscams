#!/usr/bin/python3


from PIL import Image
import glob
import numpy as np
import cv2
import os
import sys
import json


from lib.VideoLib import load_video_frames
from lib.ImageLib import stack_frames , stack_glob, stack_stack
from lib.FileIO import load_json_file , cfe
from lib.BatchLib import batch_obj_stacks

json_conf = load_json_file("../conf/as6.json")


def stack_all():
   proc_dir = json_conf['site']['proc_dir']
   cameras = json_conf['cameras']
   cam_ids = []
   for camera in cameras:
      cam_ids.append((cameras[camera]['cams_id']))

   temp_dirs = glob.glob(proc_dir + "/*")
   proc_days = []
   for proc_day in temp_dirs :
      if "daytime" not in proc_day and "json" not in proc_day and "meteors" not in proc_day and cfe(proc_day, 1) == 1:
         proc_days.append(proc_day+"/")
   for proc_day in sorted(proc_days,reverse=True):
      for cams_id in cam_ids:
         print("STACK NIGHT:", proc_day, cams_id)
         cmd = "./stackVideo.py sn " + proc_day + " " + cams_id
         os.system(cmd)



cmd = sys.argv[1]


if cmd == 'sv':
   video_file = sys.argv[1]
   frames = load_video_frames(video_file, json_conf, 0, 1)
   stack_frames(frames, video_file)
if cmd == 'sm':
   # stack meteors
   glob_dir = sys.argv[2] 
   cams_id = sys.argv[3] 
   img_dir = glob_dir.replace("passed", "images")
   glob_dir = glob_dir + "/*" + cams_id + "*-stacked.png"
   out_file = img_dir + cams_id + "-meteors-stack.png"
   print(glob_dir, out_file)
   stack_glob(glob_dir, out_file)

if cmd == 'bos':
   batch_obj_stacks(json_conf)

if cmd == 'sa':
   stack_all()

if cmd == 'sn':
   print ("stacking failures")
   # stack failed captures
   glob_dir = sys.argv[2] 
   cams_id = sys.argv[3] 
   img_dir = glob_dir + "/images/" 
   f_glob_dir = glob_dir + "/failed/*" + cams_id + "*-stacked.png"
   out_file = img_dir + cams_id + "-failed-stack.png"
   stack_glob(f_glob_dir, out_file)

   print ("stacking meteors")
   # then stack meteors, then join together
   glob_dir = f_glob_dir.replace("failed", "passed")
   print("GLOB:", glob_dir)
   meteor_out_file = img_dir + cams_id + "-meteors-stack.png"
   stack_glob(glob_dir, meteor_out_file)

   # now join the two together (if both exist)
   if cfe(out_file) == 1 and cfe(meteor_out_file) == 1:
      print ("Both files exist")
      im1 = cv2.imread(out_file, 0)
      im2 = cv2.imread(meteor_out_file, 0)
      im1p = Image.fromarray(im1)
      im2p = Image.fromarray(im2)

      print(out_file, meteor_out_file)
      final_stack = stack_stack(im1p,im2p)
      night_out_file = img_dir + cams_id + "-night-stack.png"
      final_stack_np = np.asarray(final_stack)
      cv2.imwrite(night_out_file, final_stack_np)
      print(night_out_file)
   elif cfe(out_file) == 1 and cfe(meteor_out_file) == 0:
      im1 = cv2.imread(out_file, 0)
      ih,iw = im1.shape
      empty = np.zeros((ih,iw),dtype=np.uint8)
      cv2.imwrite(meteor_out_file, empty)
      night_out_file = img_dir + cams_id + "-night-stack.png"
      print ("Only fails and no meteors exist")
      os.system("cp " + out_file + " " + night_out_file)
      print(night_out_file)
   elif cfe(out_file) == 0 and cfe(meteor_out_file) == 0:
      ih,iw = 576,704
      empty = np.zeros((ih,iw),dtype=np.uint8)
      night_out_file = img_dir + cams_id + "-night-stack.png"
      cv2.imwrite(meteor_out_file, empty)
      cv2.imwrite(out_file, empty)
      cv2.imwrite(night_out_file, empty)
      print(meteor_out_file)
      print(out_file)
      print(night_out_file)
