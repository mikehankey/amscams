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

from lib.UtilLib import calc_dist,find_angle, best_fit_slope_and_intercept, check_running
from lib.FileIO import load_json_file, save_json_file, cfe
from lib.flexLib import load_frames_fast, stack_frames_fast, convert_filename_to_date_cam, day_or_night, stack_stack
from lib.VIDEO_VARS import PREVIEW_W, PREVIEW_H, SD_W, SD_H
# SD_16_W, SD_16_H
hdm_x = 1920 / SD_W
hdm_y = 1080 / SD_H


json_conf = load_json_file("../conf/as6.json")


def day_or_night(capture_date, json_conf):

   device_lat = json_conf['site']['device_lat']
   device_lng = json_conf['site']['device_lng']

   obs = ephem.Observer()

   obs.pressure = 0
   obs.horizon = '-0:34'
   obs.lat = device_lat
   obs.lon = device_lng
   obs.date = capture_date

   sun = ephem.Sun()
   sun.compute(obs)

   (sun_alt, x,y) = str(sun.alt).split(":")

   saz = str(sun.az)
   (sun_az, x,y) = saz.split(":")
   if int(sun_alt) < -1:
      sun_status = "night"
   else:
      sun_status = "day"
   return(sun_status)



def fix_missing_stacks(day):
   running = check_running("fms")
   if running > 2:
      print("ALREADY RUNNING:", running)
      exit()
   files = glob.glob("/mnt/ams2/SD/proc2/" + day + "/*.mp4" )
   missing = 0
   found = 0
   for file in files:
      file_name = file.split("/")[-1]
      file_dir = file.replace(file_name,"")
      tday = file_name[0:10]
      y,m,d = tday.split("_") 

      image_file_name = file_name.replace(".mp4", "-stacked-tn.png")
      image_file = file_dir + "/images/" + image_file_name
      vals_file_name = file_name.replace(".mp4", "-vals.json")
      vals_file = file_dir + "/data/" + image_file_name
      if tday != day:
         print("This file is in the wrong day????", day, file_name)

         right_dir = "/mnt/ams2/SD/proc2/" + tday + "/"
         right_img_dir = "/mnt/ams2/SD/proc2/" + tday + "/images/"
         right_data_dir = "/mnt/ams2/SD/proc2/" + tday + "/day/"
         if cfe(right_img_dir,1) == 0:
            os.makedirs(right_img_dir)
         if cfe(right_data_dir,1) == 0:
            os.makedirs(right_data_dir)
         cmd = "mv " + file + " " + right_dir 
         if file != right_dir:
            os.system(cmd)
         print(cmd)
         if cfe(image_file) == 1:
            cmd = "mv " + image_file + " " + right_img_dir 
            os.system(cmd)
            print(cmd)
            print("There is a stack in this dir too.")
         if cfe(vals_file) == 1:
            cmd = "mv " + vals_file + " " + right_data_dir 
            os.system(cmd)
            print(cmd)
            print("Vals in this dir too.")
         #exit()
      if cfe(image_file) == 0:
         #print("Stack missing for : ", image_file)
         (f_datetime, cam, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(file)
         sun_status = day_or_night(f_date_str, json_conf)
         if sun_status == 'day':
            sun_status = "1"
         else:
            sun_status = "0"
         os.system("./scan_stack.py ss " + file + " " + sun_status)
         missing += 1      
      else: 
         found += 1      
   print("Missing / Found:", missing, found)

def batch_ss(wildcard=None):
   running = check_running("scan_stack.py") 
   if running > 2:
      print("Running already.")
      exit()

   if wildcard is not None:
      glob_dir = "/mnt/ams2/SD/*" + wildcard + "*.mp4"
      #glob_dir = "/mnt/ams2/CAMS/queue/*" + wildcard + "*.mp4"
   else:
      glob_dir = "/mnt/ams2/SD/*.mp4"
      #glob_dir = "/mnt/ams2/CAMS/queue/*.mp4"
   print(glob_dir)
   files = sorted(glob.glob(glob_dir), reverse=True)
   new_files =[]
   for file in files:
      if "trim" not in file:
         new_files.append(file)

   for file in sorted(new_files, reverse=True):
      (f_datetime, cam, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(file)
      sun_status = day_or_night(f_date_str, json_conf)
      if sun_status == "day":
         sun_status = "1"
      else:
         sun_status = "0"
      cur_time = int(time.time())
      st = os.stat(file)
      size = st.st_size
      print ("SIZE:", size)
      mtime = st.st_mtime
      tdiff = cur_time - mtime
      tdiff = tdiff / 60

      if size < 100:
         print("BAD SIZE!")
      else: 
         try:
            scan_and_stack_fast(file, sun_status)
         except:
            print("FAILED! File must be bad???", file)

      #running = check_running("scan_stack.py") 
      if False:
      #if running > 2:
         wait = 1
         while(running > 2):
            time.sleep(2)
            running = check_running("scan_stack.py") 
            print("Running:", running)
         if (tdiff > 3):
            cmd = "./scan_stack.py ss " + file + " " + sun_status + " &"
            print(cmd)
            os.system("./scan_stack.py ss " + file + " " + sun_status + " &") 
            # exit()
            #scan_and_stack(file, sun_status)
         else:
            print(tdiff)

#def stack(file):
#   frames,color_frames,sd_subframes,sum_vals,max_vals,pos_vals = load_frames_fast(video_file, json_conf, 0, 0, [], 1,resize, sun_status)


def scan_and_stack_fast(file, day = 0):
   day = int(day)
   fn = file.split("/")[-1]
   day = fn[0:10]
   proc_dir = "/mnt/ams2/SD/proc2/" + day + "/" 
   proc_img_dir = "/mnt/ams2/SD/proc2/" + day + "/images/" 
   proc_data_dir = "/mnt/ams2/SD/proc2/" + day + "/data/" 
   if cfe(proc_img_dir, 1) == 0:
      os.makedirs(proc_img_dir)
   if cfe(proc_data_dir, 1) == 0:
      os.makedirs(proc_data_dir)
   stack_file = proc_img_dir + fn.replace(".mp4", "-stacked-tn.png")
   json_file = proc_data_dir + fn.replace(".mp4", "-vals.json")




   sum_vals = []
   max_vals = []
   pos_vals = []
   PREVIEW_W = 300
   PREVIEW_H = 169
   start_time = time.time()

   fc = 0
   print("Loading file:", file)
   cap = cv2.VideoCapture(file)
   frames = []
   gray_frames = []
   sub_frames = []
   fd = []
   stacked_image = None
   while True:
      grabbed , frame = cap.read()

      if not grabbed and fc > 5:
         print(fc)
         break


      if day == 1:
         small_frame = cv2.resize(frame, (0,0),fx=.5, fy=.5)
      else:
         small_frame = cv2.resize(frame, (0,0),fx=.5, fy=.5)


      if day != 1:
         gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
         if fc > 0:
            sub = cv2.subtract(gray, gray_frames[-1])
         else:
            sub = cv2.subtract(gray, gray)

         min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(sub)
         if max_val < 10:
            sum_vals.append(0)
            max_vals.append(0)
            pos_vals.append((0,0))
         else:
            _, thresh_frame = cv2.threshold(sub, 15, 255, cv2.THRESH_BINARY)
            #min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(thresh_frame)
            sum_val =cv2.sumElems(thresh_frame)[0]
            mx = mx * 2
            my = my * 2
            sum_vals.append(sum_val)
            max_vals.append(max_val)
            pos_vals.append((mx,my))
         gray_frames.append(gray)

      if day == 1:
         if fc % 10 == 1:
            frame_pil = Image.fromarray(small_frame)
            if stacked_image is None:
               stacked_image = stack_stack(frame_pil, frame_pil)
            else:
               stacked_image = stack_stack(stacked_image, frame_pil)
         sum_vals.append(0)
         max_vals.append(0)
         pos_vals.append((0,0))
      else:
         if max_val > 10 or fc < 10:
            frame_pil = Image.fromarray(small_frame)
            if stacked_image is None:
               stacked_image = stack_stack(frame_pil, frame_pil)
            else:
               stacked_image = stack_stack(stacked_image, frame_pil)

      frames.append(frame)
      if fc % 100 == 1:
         print(fc)
      fc += 1
   cv_stacked_image = np.asarray(stacked_image)
   cv_stacked_image = cv2.resize(cv_stacked_image, (PREVIEW_W, PREVIEW_H))
   cv2.imwrite(stack_file, cv_stacked_image)

   

   vals = {}
   vals['sum_vals'] = sum_vals
   vals['max_vals'] = max_vals
   vals['pos_vals'] = pos_vals

   save_json_file(json_file, vals)
   print("JSON FILE:", json_file)
   elapsed_time = time.time() - start_time
   print(stack_file)
   os.system("mv " + file + " " + proc_dir)

   print(proc_dir + fn)
   print(stack_file)
   print(json_file)
   print("Elp:", elapsed_time)


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

   if sun_status == "day":
      resize = [PREVIEW_W,PREVIEW_H]
   else:
      resize = []

   vals = {}
   start_time = time.time()

   sd_frames,sd_color_frames,sd_subframes,sum_vals,max_vals,pos_vals = load_frames_fast(video_file, json_conf, 0, 0, [], 1,resize, sun_status)
   vals['sum_vals'] = sum_vals
   vals['max_vals'] = max_vals
   vals['pos_vals'] = pos_vals
   elapsed_time = time.time() - start_time
   print("LOAD & SCAN TIME:", elapsed_time)
   print("FR:", len(sd_color_frames), sun_status, len(sum_vals), len(max_vals), len(pos_vals))
   if sun_status == "day":
      skip = 10 
      stacked_image = stack_frames_fast(sd_color_frames, skip, [PREVIEW_W, PREVIEW_H], sun_status,sum_vals)
      
   else:
      skip = 1
      stacked_image = stack_frames_fast(sd_color_frames, skip, [PREVIEW_W, PREVIEW_H], sun_status, sum_vals)

   stack_file = video_file.replace(".mp4", "-stacked.png")

   cmd = "mv " + video_file + " " + proc_dir
   os.system(cmd)

   cv2.imwrite(proc_stack_file, stacked_image)
   save_json_file(proc_vals_file, vals, True)

   elapsed_time = time.time() - start_time
   print("SCAN AND STACK TIME:", elapsed_time)
   vfn = video_file.split("/")[-1]
   print(proc_dir + vfn)

   return(proc_vals_file)

if sys.argv[1] == "bs":
   if len(sys.argv) == 3:
      batch_ss(sys.argv[2])
   else:
      batch_ss()

if sys.argv[1] == "ss":
   scan_and_stack_fast(sys.argv[2], sys.argv[3])
if sys.argv[1] == "fms":
   if len(sys.argv) < 3:
      now = datetime.now()
      today = now.strftime("%Y_%m_%d")

      fix_missing_stacks(today)
   else:
      fix_missing_stacks(sys.argv[2])
if sys.argv[1] == "dv":
   detect_in_vals(sys.argv[2])
if sys.argv[1] == "stack":
   stack(sys.argv[2])
