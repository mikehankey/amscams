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
from lib.flexLib import load_frames_fast, stack_frames_fast, convert_filename_to_date_cam, day_or_night, stack_stack, dark_stack_stack
from lib.VIDEO_VARS import PREVIEW_W, PREVIEW_H, SD_W, SD_H
SHOW = 0

def stack_day_all():
   running = check_running("day_stack.py")
   #day_dir = "/mnt/ams2/SD/proc2/daytime/" + day + "/"
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



   for df in sorted(day_files):
      st = os.stat(df)
      size = st.st_size
      if size < 1000:
         print("SIZE TO SMALL:", size)
         os.system("rm " + df)
         continue
      day = df.split("/")[-1][0:10] 
      if day not in exists:
         day_dir = "/mnt/ams2/SD/proc2/daytime/" + day + "/"
         if cfe(day_dir, 1) == 0:
            os.makedirs(day_dir)
            os.makedirs(day_dir + "images")
         exists[day] = 1
      stack_img, elp = day_stack(df, day)
      print("DAY STACK:", df, elp)

def day_stack(video_file, day, cam=None, last_blend=None):
   start_time = time.time()
   day_dir = "/mnt/ams2/SD/proc2/daytime/" + day + "/"

   stack_file = video_file.replace(".mp4", "-stacked.jpg")
   #stack_file_thumb = video_file.replace(".mp4", "-stacked-tn.jpg")
   snap_file = video_file.replace(".mp4", "-snap.jpg")
   stack_fn = stack_file.split("/")[-1]
   stack_file = day_dir + "images/" + stack_fn 
   stack_file_thumb = day_dir + "images/" + stack_fn.replace(".jpg", "-tn.jpg")

   if os.path.exists(stack_file) is True:
      img = cv2.imread(stack_file)
      if SHOW == 1:
         cv2.imshow('pepe', img)
         cv2.waitKey(30)
      print("SKIP DONE ALREADY", stack_file)
      return(np.array(img), time.time() - start_time)
   #else:
   #   print(stack_file)


   tt = time.time()

   day_dir = "/mnt/ams2/SD/proc2/daytime/" + day + "/"
    
   #thumb_size = (306, 169)
   thumb_size = (640, 360)
   #cmd = "rm /home/ams/tmp-stack/foo*"
   #os.system(cmd)
   # stack 1 FPS
   #cmd = "/usr/bin/ffmpeg -i " + video_file + " -vf fps=1 /home/ams/tmp-stack/foo-%03d.jpg > /dev/null 2>&1"
   # stack just 1 frame 
   #mia_out = "/home/ams/tmp-stack/foo-%03d.jpg"
   #cmd = "/usr/bin/ffmpeg -ss 00:00:01.00 -i " + video_file + " -frames:v 250 " + mia_out

   # select 1 frame out of 5 modulus 5 and put to a jpg then stack those files
   # would work better with pipe?
   #cmd = """/usr/bin/ffmpeg -i """ + video_file + """ -vf "select=not(mod(n\,25))" -vsync vfr -q:v 2 > /dev/null 2>&1 """ + mia_out
   #print(cmd)
   #os.system(cmd)

   #files = glob.glob("/home/ams/tmp-stack/*.jpg")

   cap = cv2.VideoCapture(video_file)
   total_frames = cap.get(7)
   images = []
   print("TOTAL FRAMES", total_frames)
   cap.set(1, 100)
   ret, frame = cap.read()
   images.append(frame)
   #cv2.imshow('pepe', frame)
   #cv2.waitKey(0)

   stacked_image = None
   dark_stacked_image = None
   print("IMGS", len(images))
   #for file in sorted(files): 
   for cv_image in sorted(images): 
      #frame_pil = Image.open(file)
      frame_pil = Image.fromarray(cv_image)
      frame_pil = frame_pil.resize(thumb_size)
      if stacked_image is None:
         stacked_image = stack_stack(frame_pil, frame_pil)
      else:
         stacked_image = stack_stack(stacked_image, frame_pil)

      if dark_stacked_image is None:
         dark_stacked_image = dark_stack_stack(frame_pil, frame_pil)
      else:
         dark_stacked_image = dark_stack_stack(dark_stacked_image, frame_pil)
   stacked_img = cv2.cvtColor(np.asarray(stacked_image), cv2.COLOR_RGB2BGR)
   dark_stacked_img = cv2.cvtColor(np.asarray(dark_stacked_image), cv2.COLOR_RGB2BGR)

   return_img = cv2.cvtColor(np.asarray(stacked_image), cv2.COLOR_RGB2BGR)
   dark_return_img = cv2.cvtColor(np.asarray(dark_stacked_image), cv2.COLOR_RGB2BGR)
   blend_return_img = cv2.addWeighted(return_img, .5, dark_return_img, .5,0)

   if SHOW == 1:

      cv2.imshow('pepe', np.array(blend_return_img))
      cv2.waitKey(30)
   if stacked_image is None:
      #os.system("rm " + video_file )
      print("BAD VIDEO FILE! ", video_file)

   else: 
      #stacked_image.save(stack_file)
      cv2.imwrite(stack_file, blend_return_img)
      blend_return_img_thumb = cv2.resize(blend_return_img, (320,180))
      cv2.imwrite(stack_file_thumb, blend_return_img_thumb)
      print("SAVED", stack_file)
      cmd = "mv " + video_file + " " + day_dir
      #os.system("mv " + video_file + " " + day_dir)
   print("Elapsed:", time.time() - tt)
   return(np.array(blend_return_img), time.time() - start_time)

if len(sys.argv) == 1:
   # do current work
   stack_day_all()
elif len(sys.argv) > 1:
   if sys.argv[1] == "sf":
      # stack 1 file
      (hd_datetime, cam, sd_date, sd_y, sd_m, sd_d, sd_h, sd_M, sd_s) = convert_filename_to_date_cam(sys.argv[2])
      day, tm = sd_date.split(" ")
      day = day.replace("-", "_")
      day_stack(sys.argv[2], day)
   elif sys.argv[1] == "sd":
      day = sys.argv[2]
      cam = sys.argv[3]
      print("stack 1 day", day)
      day_dir = "/mnt/ams2/SD/proc2/daytime/" + day + "/"  
      files = glob.glob(day_dir + "*" + cam + "*.mp4")
      print(day_dir, len(files) )
      last_stack = None
      for ff in sorted(files):
         last_stack, elp = day_stack(ff, day, cam, last_stack)
         print("LAST STACK ELP", ff, elp)

