#!/usr/bin/python3

from PIL import ImageFont, ImageDraw, Image, ImageChops
from datetime import datetime

import ephem
import numpy as np
#import datetime
import time
import sys
import os
import cv2
import glob


from lib.UtilLib import calc_dist,find_angle, best_fit_slope_and_intercept, check_running, logger
from lib.FileIO import load_json_file, save_json_file, cfe
from lib.flexLib import load_frames_fast, stack_frames_fast, convert_filename_to_date_cam, day_or_night, stack_stack
from lib.VIDEO_VARS import PREVIEW_W, PREVIEW_H, SD_W, SD_H

def stack_day_all():
   running = check_running("day_stack.py")
   print("RUNNING:", running)
   if running > 2:
      print("already running")
      exit()


   if cfe("fixed-day-pngs.txt") == 0:
      print("FIX PNGS.")
      os.system("./fix-day-pngs.py")

   exists = {}
   day_files = glob.glob("/mnt/ams2/SD/proc2/daytime/*.mp4")
   if cfe("/home/ams/tmp-stack/", 1) == 0:
      os.makedirs("/home/ams/tmp-stack")



   for df in day_files:
      st = os.stat(df)
      size = st.st_size
      if size < 1000:
         print("SIZE TO SMALL:", size)
         os.system("rm " + df)
         continue
      day = df.split("/")[-1][0:10] 
      day_dir = "/mnt/ams2/SD/proc2/daytime/" + day + "/"
      if day not in exists:
         if cfe(day_dir, 1) == 0:
            os.makedirs(day_dir)
            os.makedirs(day_dir + "images")
         exists[day] = 1
      stack_file, elp = day_stack(df, day)
      print(df, stack_file, elp)

def day_stack(video_file, day):


   start_time = time.time()
   day_dir = "/mnt/ams2/SD/proc2/daytime/" + day + "/"
    
   thumb_size = (306, 169)
   cmd = "rm /home/ams/tmp-stack/foo*"
   os.system(cmd)
   # stack 1 FPS
   #cmd = "/usr/bin/ffmpeg -i " + video_file + " -vf fps=1 /home/ams/tmp-stack/foo-%03d.jpg > /dev/null 2>&1"
   # stack just 1 frame 
   mia_out = "/home/ams/tmp-stack/foo-%03d.jpg"
   cmd = "/usr/bin/ffmpeg -ss 00:00:01.00 -i " + video_file + " -frames:v 1 " + mia_out
   print(cmd)
   os.system(cmd)
   files = glob.glob("/home/ams/tmp-stack/*.jpg")
   stack_file = video_file.replace(".mp4", "-stacked-tn.jpg")
   stack_fn = stack_file.split("/")[-1]
   stack_file = day_dir + "images/" + stack_fn 

   stacked_image = None
   for file in files: 
      frame_pil = Image.open(file)
      frame_pil = frame_pil.resize(thumb_size)
      if stacked_image is None:
         stacked_image = stack_stack(frame_pil, frame_pil)
      else:
         stacked_image = stack_stack(stacked_image, frame_pil)

   if stacked_image is None:
      os.system("rm " + video_file )
      print("BAD VIDEO FILE! ", video_file)

   else: 
      stacked_image.save(stack_file)
      os.system("mv " + video_file + " " + day_dir)
   return(stack_file, time.time() - start_time)

if len(sys.argv) > 1:
   (hd_datetime, cam, sd_date, sd_y, sd_m, sd_d, sd_h, sd_M, sd_s) = convert_filename_to_date_cam(sys.argv[2])
   day, tm = sd_date.split(" ")
   day_stack(sys.argv[2], day)
else:
   stack_day_all()
