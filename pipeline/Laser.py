#!/usr/bin/python3
import sys
import os
import numpy as np
from lib.PipeUtil import load_json_file, save_json_file, cfe
from lib.PipeWeather import color_thresh_new, get_contours
from lib.PipeVideo import load_frames_fast
import glob 
import cv2

json_conf = load_json_file("../conf/as6.json")
   
  
def detect_laser_in_thumbs(date,json_conf):
   ld = "/mnt/ams2/laser/" + date + "/"  
   if cfe(ld, 1) == 0:
      os.makedirs(ld)
   detects = []
   files = glob.glob("/mnt/ams2/SD/proc2/" + date + "/images/*tn.jpg")
   html = ""
   for file in files:
      val = detect_laser_in_img(file)
      if val > 0:
         detects.append((file, val))
   for file, val in detects:
      vf = file.replace("/mnt/ams2", "")
      html += "<div style='float: left'><img src=" + vf + "></div>"
   fp = open(ld + "laser.html", "w")
   fp.write(html)
   print("saved:", ld + "laser.html")
def detect_laser_in_img(file):
   frame = cv2.imread(file)
   matched = color_thresh_new(frame, (0,50,50), (45,255,255))
   return(np.sum(matched))
   
def detect_laser_activity(file, json_conf):
   
   hd_frames,hd_color_frames,subframes,sum_vals,max_vals,pos_vals = load_frames_fast(file, json_conf, 0, 0, 1, 1,[])
   
   mask = None
   fn = 0
   laser_detected = 0
   laser_activity = []
   for frame in hd_color_frames:
      matched = color_thresh_new(frame, (0,0,0), (45,255,255))
      #matched_inv = abs(matched - 255)
      if mask is None:
         mask = matched
         mask = cv2.cvtColor(mask,cv2.COLOR_GRAY2BGR)
         #xxx = input("MASK:" + str(np.sum(mask)))
         if np.sum(mask) > 20000000:
            laser_detected = 1
         sub = cv2.subtract(frame, mask)
         cnts = get_contours(sub)
         for x,y,w,h in cnts:
            mask[y:y+h,x:x+w] = 255
         sub_diff = sub 
      else:
         sub_diff = cv2.subtract(sub, last_sub)
         sub = cv2.subtract(frame, mask)
         cnts = get_contours(sub_diff)
         print(fn, np.sum(sub_diff))
         if len(cnts) > 0:
            print(fn, len(cnts))
            file_fn = file.split("/")[-1]
            laser_activity.append((file_fn,fn))
      last_sub = sub.copy()
      last_frame = frame.copy()
      fn += 1
   print("Laser Detected:", laser_detected)
   print("Laser Activity:", len(laser_activity))

cmd = sys.argv[1]
file = sys.argv[2]

if cmd == 'detect_laser':
   detect_laser_in_thumbs(file,json_conf)
if cmd == 'laser_activity':
   detect_laser_activity(file,json_conf)

