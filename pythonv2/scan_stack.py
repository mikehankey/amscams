#!/usr/bin/python3

import datetime
import time
import sys
import os
import cv2
import glob

from lib.UtilLib import calc_dist,find_angle, best_fit_slope_and_intercept
from lib.FileIO import load_json_file, save_json_file, cfe
from lib.flexLib import load_frames_fast, stack_frames_fast, convert_filename_to_date_cam, day_or_night
from lib.VIDEO_VARS import PREVIEW_W, PREVIEW_H, SD_W, SD_H
hdm_x = 1920 / SD_W
hdm_y = 1080 / SD_H


json_conf = load_json_file("../conf/as6.json")

def batch_ss(wildcard=None):
   if wildcard is not None:
      glob_dir = "/mnt/ams2/SD/*wildcard*.mp4"
   else:
      glob_dir = "/mnt/ams2/SD/*.mp4"
   print(glob_dir)
   files = sorted(glob.glob(glob_dir), reverse=True)
   for file in files:
      (f_datetime, cam, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(file)
      sun_status = day_or_night(f_date_str, json_conf)
      cur_time = int(time.time())
      st = os.stat(file)
      size = st.st_size
      print ("SIZE:", size)
      mtime = st.st_mtime
      tdiff = cur_time - mtime
      tdiff = tdiff / 60
      
      if (tdiff > 3):
         scan_and_stack(file, sun_status)
      else:
         print(tdiff)

def scan_and_stack(video_file, sun_status):
   if cfe(video_file) == 0:
      print("File doesn't exist : ", video_file)
      return()
   vid_fn = video_file.split("/")[-1]   
   (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(video_file)

   proc_dir = "/mnt/ams2/SD/proc2/" + fy + "_" + fm + "_" + fd + "/"
   proc_img_dir = "/mnt/ams2/SD/proc2/" + fy + "_" + fm + "_" + fd + "/images/"
   proc_data_dir = "/mnt/ams2/SD/proc2/" + fy + "_" + fm + "_" + fd + "/data/"

   if cfe(proc_img_dir, 1)  == 0:
      os.makedirs(proc_img_dir)
   if cfe(proc_data_dir, 1)  == 0:
      os.makedirs(proc_data_dir)

   vals_fn = vid_fn.replace(".mp4", "-vals.json")
   stack_fn = vid_fn.replace(".mp4", "-stacked-tn.png")
   proc_vals_file = proc_data_dir + vals_fn
   proc_stack_file = proc_img_dir + stack_fn 
   proc_vid_file = proc_dir + vid_fn

   vals = {}
   start_time = time.time()
   sd_frames,sd_color_frames,sd_subframes,sum_vals,max_vals,pos_vals = load_frames_fast(video_file, json_conf, 0, 0, [], 1,[], sun_status)
   vals['sum_vals'] = sum_vals
   vals['max_vals'] = max_vals
   vals['pos_vals'] = pos_vals
   elapsed_time = time.time() - start_time
   print("LOAD & SCAN TIME:", elapsed_time)
   if sun_status == "day":
      skip = 5
   else:
      skip = 1
   stacked_image = stack_frames_fast(sd_color_frames, skip, [PREVIEW_W, PREVIEW_H])

   elapsed_time = time.time() - start_time
   stack_file = video_file.replace(".mp4", "-stacked.png")
   print(proc_stack_file)
   print(proc_vals_file)
   print(proc_vid_file)
   print("SCAN AND STACK TIME:", elapsed_time)

   cmd = "mv " + video_file + " " + proc_dir
   os.system(cmd)
   cv2.imwrite(proc_stack_file, stacked_image)
   save_json_file(proc_vals_file, vals, True)
   print(cmd)
   print(proc_stack_file)
   print(proc_vals_file)

   return(proc_vals_file)

if sys.argv[1] == "bs":
   if len(sys.argv) == 3:
      batch_ss(sys.argv[2])
   else:
      batch_ss()

if sys.argv[1] == "ss":
   scan_and_stack(sys.argv[2])
