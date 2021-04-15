# -*- coding: utf-8 -*-
"""
Created on Thu Apr 15 12:57:18 2021

@author: Rabea Sennlaub
"""
import numpy as np
import cv2
import os
from lib.PipeVideo import load_frames_fast, ffprobe
from lib.PipeUtil import load_json_file
from lib.PipeDetect import load_mask_imgs, get_contours_in_image, find_object, analyze_object

def crop_video(in_file, out_file, x,y,w,h):
   crop = "crop=" + str(w) + ":" + str(h) + ":" + str(x) + ":" + str(y)
   cmd = "/usr/bin/ffmpeg -i " + in_file + " -filter:v \"" + crop + "\" -y " + out_file + " > /dev/null 2>&1"
   os.system(cmd)


def process_trash(video_file):
    # load frames/sub frames and vals
    hd_frames,hd_color_frames,subframes,sum_vals,max_vals,pos_vals = load_frames_fast(video_file, json_conf, 0, 0, 1, 1,[])

    # make dict
    objects = {}

    # set frame # start value
    fn = 0

    # Load masks to block out mask areas
    sd_mask_imgs = load_mask_imgs(json_conf)
    mask = sd_mask_imgs[0]["010320"]

    if mask.shape[0] != subframes[0].shape[0]:
       mask = cv2.resize(mask, (subframes[0].shape[1], subframes[0].shape[0]))
    if len(mask.shape) == 3:
        mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)


    bg_img = hd_frames[0]
    intense = []
    full_bg_avg = np.mean(bg_img)
    for frame in subframes:
       frame = cv2.subtract(frame, mask)
       min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(frame)
       thresh = max_val - 10
       if thresh < 10:
          thresh = 10
       if thresh > 10:
          thresh = 10
       _, threshold = cv2.threshold(frame, thresh, 255, cv2.THRESH_BINARY)
       cnts = get_contours_in_image(threshold)
       for x,y,w,h in cnts:
          if w < 2 or h < 2:
             continue
          cnt_img = hd_frames[fn][y:y+h,x:x+h]
          bg_cnt_img = bg_img[y:y+h,x:x+h]
          int_cnt = cv2.subtract(cnt_img, bg_cnt_img)
          cx = int(x + (w/2))
          cy = int(y + (h/2))
          cval = hd_frames[fn][cy,cx]
          oint = int(np.sum(int_cnt))
          avg_px_int = int(oint / (cnt_img.shape[0] * cnt_img.shape[1]))
          avg_bg_px = int(np.sum(bg_cnt_img) / (cnt_img.shape[0] * cnt_img.shape[1]))
          #print("INTENSITY:", fn, oint, avg_bg_px, cval, avg_px_int)
          # useful to see what is going on sometimes . print rectangles on cnts and show here if desired.
          #cv2.imshow('pepe', int_cnt)
          #cv2.waitKey(30)
          object, objects = find_object(objects, fn,x, y, w, h, oint, 0, 0, None)
       #cv2.imshow('pepe', frame)
       #cv2.waitKey(30)
       fn += 1

    found = 0

    return objects


# load station json_conf
json_conf = load_json_file("../conf/as6.json")
video_file = "/mnt/ams2/trash/test/2021_02_13_01_48_01_000_010320-trim-1396.mp4"

objects = process_trash(video_file)

for obj_id in objects:
  objects[obj_id] = analyze_object(objects[obj_id])


for obj_id in objects:
   if objects[obj_id]['report']['meteor'] == 1:
      # do ffmpeg call
      min_x = min(objects[obj_id]['oxs'])
      max_x = max(objects[obj_id]['oxs']) 
      min_y = min(objects[obj_id]['oys'])
      max_y = max(objects[obj_id]['oys'])  
      w = max_x-min_x
      h = max_y-min_y
      
      crop_video("/mnt/ams2/trash/test/2021_02_13_01_48_01_000_010320-trim-1396.mp4", "/mnt/ams2/trash/test/2021_02_13_01_48_01_000_010320-trim-1396_crop.mp4", min_x,min_y,w,h)
      print("/mnt/ams2/trash/test/2021_02_13_01_48_01_000_010320-trim-1396.mp4", "/mnt/ams2/trash/test/2021_02_13_01_48_01_000_010320-trim-1396_crop.mp4", min_x,min_y,w,h)


