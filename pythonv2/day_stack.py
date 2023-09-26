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

def stack_day_all(interval):
   running = check_running("day_stack.py")
   #day_dir = "/mnt/ams2/SD/proc2/daytime/" + day + "/"
   print("RUNNING:", running)
   if running > 2:
      print("already running")
      exit()


   if cfe("fixed-day-pngs.txt") == 0:
      print("FIX PNGS.")
      os.system("./fix-day-pngs.py")

   night_files = glob.glob("/mnt/ams2/SD/*.mp4")
   if len(night_files) > 100:
      print("We have a lot of night files. Wait until they are done before doing the day stack!")
      return()


   exists = {}
   day_files = glob.glob("/mnt/ams2/SD/proc2/daytime/*.mp4")
   if cfe("/home/ams/tmp-stack/", 1) == 0:
      os.makedirs("/home/ams/tmp-stack")


   now = datetime.now()
   for df in sorted(day_files):
      (hd_datetime, cam, sd_date, sd_y, sd_m, sd_d, sd_h, sd_M, sd_s) = convert_filename_to_date_cam(df)
      elapsed = abs((now - hd_datetime).total_seconds())
      days_old = elapsed / 60 / 60 / 24
      if days_old > 3:
         cmd = "rm " + df
         print(cmd)
         os.system(cmd)
         continue

      if os.path.exists(df) is False:
         continue
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
      stack_img, elp = day_stack(df, day, interval=interval)
      print("DAY STACK:", df, elp)

def day_stack(video_file, day, cam=None, last_blend=None, interval=25):
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
      #if SHOW == 1:
      #   cv2.imshow('pepe', img)
      #   cv2.waitKey(30)
      day_dir = "/mnt/ams2/SD/proc2/daytime/" + day + "/"

      cmd = "mv " + video_file + " " + day_dir
      print(cmd)
      os.system("mv " + video_file + " " + day_dir)

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

   # get 1 image of every 10 frames
   #interval = 15 
   cap = cv2.VideoCapture(video_file)
   total_frames = cap.get(7)
   images = []
   stacked_image = None
   dark_stacked_image = None
   print("TOTAL FRAMES/ interval", total_frames, interval)
   count = 0
   for i in range(0,int(total_frames/interval)):
      fn = i * interval
      cap.set(1, fn)
      ret, frame = cap.read()
      if frame is None:
         continue
      frame = cv2.resize(frame, thumb_size)
      images.append(frame)
      if i == 0:
         snap_img = frame
      #if SHOW == 1:
      #   cv2.imshow('pepe', frame)
      #   cv2.waitKey(30)

      #frame_pil = Image.open(file)
      frame_pil = Image.fromarray(frame)
      #frame_pil = frame_pil.resize(thumb_size)
      if stacked_image is None:
         stacked_image = stack_stack(frame_pil, frame_pil)
      else:
         stacked_image = stack_stack(stacked_image, frame_pil)

      if dark_stacked_image is None:
         dark_stacked_image = dark_stack_stack(frame_pil, frame_pil)
      else:
         dark_stacked_image = dark_stack_stack(dark_stacked_image, frame_pil)
      count = count + 1
   #stacked_img = cv2.cvtColor(np.asarray(stacked_image), cv2.COLOR_RGB2BGR)
   if count == 0:
      return(None,  time.time() - start_time)
   dark_stacked_img_cv = cv2.cvtColor(np.asarray(dark_stacked_image), cv2.COLOR_RGB2BGR)
   stacked_img_cv = cv2.cvtColor(np.asarray(stacked_image), cv2.COLOR_RGB2BGR)


   blend_return_img = cv2.addWeighted(stacked_img_cv, .5, dark_stacked_img_cv, .5,0)
   blend_return_img = cv2.cvtColor(np.asarray(blend_return_img), cv2.COLOR_RGB2BGR)

   if SHOW == 1:
      foo = 1
      #cv2.imshow('pepe', np.array(blend_return_img))
      #cv2.waitKey(30)
   if stacked_image is None:
      #os.system("rm " + video_file )
      print("BAD VIDEO FILE! ", video_file)

   else: 
      #stacked_image.save(stack_file)
      stacked_img_cv = cv2.cvtColor(np.asarray(stacked_img_cv), cv2.COLOR_RGB2BGR)
      cv2.imwrite(stack_file, stacked_img_cv)
      cv2.imwrite(stack_file.replace("-stacked.jpg", "-snap.jpg"), snap_img)
      cv2.imwrite(stack_file.replace(".jpg", "-blend.jpg"), blend_return_img)
      dark_stacked_img_cv = cv2.cvtColor(np.asarray(dark_stacked_img_cv), cv2.COLOR_RGB2BGR)
      cv2.imwrite(stack_file.replace(".jpg", "-dark.jpg"), dark_stacked_img_cv)

      blend_return_img_thumb = cv2.resize(blend_return_img, (320,180))
      cv2.imwrite(stack_file_thumb, blend_return_img_thumb)
      print("SAVED", stack_file)
      if SHOW == 1:
         #cv2.imshow('pepe', snap_img)
         #cv2.waitKey(90)
         #cv2.imshow('pepe', stacked_img_cv)
         #cv2.waitKey(90)
         #cv2.imshow('pepe', dark_stacked_img_cv)
         #cv2.waitKey(90)
         cv2.imshow('pepe', blend_return_img)
         cv2.waitKey(30)



      cmd = "mv " + video_file + " " + day_dir
      os.system("mv " + video_file + " " + day_dir)
   print("Elapsed:", time.time() - tt)
   return(np.array(blend_return_img), time.time() - start_time)





if len(sys.argv) == 1:
   # do current work
   if True:
      day_dir = "/mnt/ams2/SD/proc2/daytime/" 
      files = glob.glob(day_dir + "*.mp4")
      print(day_dir, len(files) )
      last_stack = None
      for ff in sorted(files):
         if len(files) > 1000:
            interval = 50 
         elif 100 <= len(files) <= 1000:
            interval = 25
         elif len(files) < 100:
            interval = 5
         else:
            interval = 10
      print("FILES/INTERVAL:", len(files), interval)
      stack_day_all(interval)
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
         if len(files) > 1000:
            interval = 800 
         elif 100 <= len(files) <= 1000:
            interval = 25
         elif len(files) < 100:
            interval = 5
         else:
            interval = 10
         last_stack, elp = day_stack(ff, day, cam, last_stack, interval)
         print("LAST STACK ELP", ff, elp)

