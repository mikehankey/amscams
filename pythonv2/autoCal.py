#!/usr/bin/python3

import time
import subprocess
import math
from pathlib import Path
import datetime
import cv2
import numpy as np
import ephem
import glob
import os
from lib.VideoLib import load_video_frames, get_masks
from lib.ImageLib import stack_frames, median_frames, adjustLevels, mask_frame
from lib.UtilLib import convert_filename_to_date_cam, bound_cnt, check_running,date_to_jd, angularSeparation , calc_dist
from lib.FileIO import cfe, save_json_file, load_json_file
from lib.DetectLib import eval_cnt
from scipy import signal
from lib.CalibLib import find_best_thresh 
import lib.brightstardata as bsd

mybsd = bsd.brightstardata()
bright_stars = mybsd.bright_stars
json_conf = load_json_file("../conf/as6.json")

def star_test(cnt_img):
   PX = []
   PY = []
   ch,cw = cnt_img.shape
   my = int(ch / 2)
   mx = int(cw / 2)
   max_px = np.max(cnt_img)
   avg_px = np.mean(cnt_img)
   px_diff = max_px - avg_px

   for x in range(0,cw-1):
      px_val = cnt_img[my,x]
      PX.append(px_val)
      #cnt_img[my,x] = 255
   for y in range(0,ch-1):
      py_val = cnt_img[y,mx]
      PY.append(py_val)
      #cnt_img[y,mx] = 255

   ys_peaks = signal.find_peaks(PY)
   y_peaks = len(ys_peaks[0])
   xs_peaks = signal.find_peaks(PX)
   x_peaks = len(xs_peaks[0])


   if px_diff > 20:
      is_star = 1
   else:
      is_star = 0

   return(is_star)


def find_stars(med_stack_all, cam_num, center = 0, center_limit = 200, pdif_factor = 10):
   masks = get_masks(cam_num, json_conf,0)
   img_height, img_width= med_stack_all.shape
   hh = img_height / 2
   hw = img_width / 2
   max_px = np.max(med_stack_all)
   avg_px = np.mean(med_stack_all)
   med_cpy = med_stack_all.copy()
   pdif = max_px - avg_px
   pdif = int(pdif / pdif_factor) + avg_px
   bg_avg = 0
   print("FSTEST1")
   if avg_px > 60:
      return(0,[],[], [], [])
   best_thresh = find_best_thresh(med_stack_all, avg_px+5)
   _, star_bg = cv2.threshold(med_stack_all, best_thresh, 255, cv2.THRESH_BINARY)
   thresh_obj= cv2.convertScaleAbs(star_bg)
   (_, cnts, xx) = cv2.findContours(thresh_obj.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
   print("FSTEST2")
   star_pixels = []
   non_star_pixels = []
   cloudy_areas = []
   for (i,c) in enumerate(cnts):
      x,y,w,h= cv2.boundingRect(cnts[i])
      if w < 30 and h < 30:
         cnt_img = med_stack_all[y:y+h,x:x+w]
         (max_px, avg_px,px_diff,max_loc) = eval_cnt(cnt_img)
         mx,my = max_loc
         cx = x + int(w/2)
         cy = y + int(h/2)
         mnx,mny,mxx,mxy = bound_cnt(cx,cy,img_width,img_height)
         cnt_img = med_stack_all[mny:mxy,mnx:mxx]
         cnt_w,cnt_h = cnt_img.shape
         if cnt_w > 0 and cnt_h > 0:
            is_star = star_test(cnt_img)
            if is_star == 1:
               bg_avg = bg_avg + np.mean(cnt_img)
               star_pixels.append((cx,cy))
               cv2.circle(med_cpy, (int(cx),int(cy)), 5, (255,255,255), 1)
            else:
               cv2.rectangle(med_cpy, (cx-5, cy-5), (cx + 5, cy + 5), (255, 0, 0), 1)
               non_star_pixels.append((cx,cy))
      else:
         cloudy_areas.append((x,y,w,h))
         cv2.rectangle(med_cpy, (x, y), (x + w, y + w), (255, 0, 0), 3)

   center_stars = []
   for sx,sy in star_pixels:
      center_dist = calc_dist((hw,hh), (sx,sy))
      if abs(center_dist) < center_limit:
         center_stars.append((sx,sy))

   if len(non_star_pixels) > 0 and len(star_pixels) > 0:
      perc_cloudy = int(len(non_star_pixels) / len(star_pixels))  * 100
      desc = str(len(star_pixels)) + " stars " + str(len(non_star_pixels)) + " non stars " + str(perc_cloudy) + "% cloudy"

   else :
      perc_cloudy = 0
      perc_clear = 100
      desc = str(len(star_pixels)) + " stars " + str(len(non_star_pixels)) + " non stars " + str(perc_clear) + "% clear"

   status = ""

   if len(star_pixels) > 10:
      status = "clear"
   if len(non_star_pixels) > len(star_pixels) or len(star_pixels) <= 5:
      status = "cloudy"
   if len(non_star_pixels) == 0 and len(star_pixels) == 0:
      status = "cloudy"
   if len(non_star_pixels) >= 5 and len(star_pixels) <= 5:
       status = "partly cloudy "

   cv2.putText(med_cpy, str(status),  (10,300), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)
   return(status,star_pixels, center_stars, non_star_pixels, cloudy_areas)


def find_hd_file(sd_file):
   if "png" in sd_file:
      sd_file = sd_file.replace("-stacked.png", ".mp4")
      sd_file = sd_file.replace("/images", "")
   print("SD FILE: ", sd_file)
   (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(sd_file)

   glob_dir = "/mnt/ams2/HD/" + str(fy) + "_" + str(fm) + "_" + str(fd) + "_" + str(fh) + "_" + fmin + "*" + cam + "*.mp4"
   print(glob_dir)
   hdfiles = glob.glob(glob_dir)
   print(hdfiles)
   if len(hdfiles) > 0:
      return(hdfiles[0])
   else:
      return(0)


def check_for_stars(file, cam_num, hd=0):

   print("TEST", file)
   image = cv2.imread(file, 0)
   #image = magic_contrast(image)
   #cam_num  = "010004"

   hd_file = find_hd_file(file)

   masks = get_masks(cam_num, json_conf,hd)
   image = mask_frame(image, [], masks)

   print("TEST1")
   status, stars, center_stars, non_stars, cloudy_areas = find_stars(image, cam_num, 1, 200, 10)
   print("TEST2")
   image= mask_frame(image, non_stars, masks, 25)
   status, stars, center_stars, non_stars, cloudy_areas = find_stars(image, cam_num, 1, 200, 10)
   print("TEST3")
   #for (x,y) in stars:
   #   cv2.circle(image, (x,y), 3, (255), 1)
   #for (x,y) in center_stars:
   #   cv2.circle(image, (x,y), 6, (255), 1)
   #for (x,y,w,h) in cloudy_areas:
   #   cv2.rectangle(image, (x, y), (w, h), (200, 200, 200), 2)

   print("STARS:", center_stars, len(stars))

   if len(center_stars) > 10 or len(stars) > 30:
      print("CALIBRATE?: YES")
      print("STARS:", len(stars))
      print("CENTER STARS:", len(center_stars))
      cv2.putText(image, str("CALIBRATE"),  (100,120), cv2.FONT_HERSHEY_SIMPLEX, .8, (255,255,255), 1)
      status = "calibrate"
   elif len(stars) > 10:

      status = "clear"
      print("STATUS: CLEAR")
      cv2.putText(image, str("CLEAR"),  (100,100), cv2.FONT_HERSHEY_SIMPLEX, .8, (255,255,255), 1)
   else:
      status = "bad"


   #cv2.imshow('pepe', image)
   #cv2.waitKey(10)
   return(status,stars,center_stars,non_stars,cloudy_areas)


def summarize_weather(weather_data):
   hourly_weather = {}
   for wdata in weather_data:
      (file, status, stars, center_stars, non_stars, cloudy_areas) = wdata
      (fy,fm,fd,fh,fmin,fsec,cam_num) = get_time_for_file(file)
      key = fy + "_" + fm + "_" + fd + "_" + fh + "_" + cam_num
      if key not in hourly_weather:
         hourly_weather[key] = []
         hourly_weather[key].append(status)
      else:
         hourly_weather[key].append(status)
   for key in hourly_weather:
      print(key,hourly_weather[key])

def find_non_cloudy_times(cal_date,cam_num,json_conf):

   proc_dir = json_conf['site']['proc_dir']
   weather_data = []
   json_file = proc_dir + cal_date + "/" + "data/" + cal_date + "-weather-" + cam_num + ".json"
   found = cfe(json_file)
   found = 0
   if found == 0:
      glob_dir = proc_dir + cal_date + "/" + "images/*" + cal_date + "*" + cam_num + "*.png"
      files = glob.glob(glob_dir)
      files = sorted(files)
      fc = 0
      for file in files:
         if "trim" not in file:
            if fc % 10 == 0:
               status, stars, center_stars, non_stars, cloudy_areas = check_for_stars(file, cam_num, 0)
               print("MIKE",status,stars,center_stars,non_stars)
               weather_data.append((file, status, stars, center_stars, non_stars, cloudy_areas))
            fc = fc + 1
      save_json_file(json_file, weather_data)
   else:
      weather_data = load_json_file(json_file)

   print("WEATHER DATA: ", weather_data)
   print("WEATHER JSON: ", json_file)

   return(weather_data)



weather_data = find_non_cloudy_times("2019_03_27", "010001", json_conf)
#print(weather_data)
#summarize_weather_data(weather_data)
