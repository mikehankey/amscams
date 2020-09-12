'''
   functions for making timelapse movies
'''

import glob
import sys
import os
from lib.PipeImage import  quick_video_stack, rotate_bound
import cv2
from lib.PipeUtil import cfe, save_json_file, convert_filename_to_date_cam
from lib.PipeAutoCal import fn_dir
from lib.DEFAULTS import *
import numpy as np

def tn_tl6(date,json_conf):
   day_dir = "/mnt/ams2/SD/proc2/daytime/" + date + "/images/*.png"
   night_dir = "/mnt/ams2/SD/proc2/" + date + "/images/*.png"
   day_files = glob.glob(day_dir)
   night_files = glob.glob(night_dir)
   print("D", len(day_files))
   print("N", len(night_files))
   all_files = []
   for file in sorted(day_files):
      all_files.append(file)
   for file in sorted(night_files):
      all_files.append(file)
   for file in all_files:
      print(file)

   matrix = {}

   cam_id_info = {}
   default_cams = {}
   for cam in sorted(json_conf['cameras'].keys()):
      cams_id = json_conf['cameras'][cam]['cams_id']
      cam_id_info[cams_id] = cam
      default_cams[cam] = ""

   for file in sorted(all_files):
      if "night" in file:
         continue
      fn, dir = fn_dir(file)
      (sd_datetime, sd_cam, sd_date, sd_y, sd_m, sd_d, sd_h, sd_M, sd_s) = convert_filename_to_date_cam(file)
      key = sd_h + "-" + sd_M
      print("KEY", file, sd_datetime, key, file)
      if key not in matrix:
         matrix[key] = {}
         for cam in sorted(json_conf['cameras'].keys()):
            matrix[key][cam] = ""
 
      cid = cam_id_info[sd_cam]
      print("MATRIX:", key, cid, file)
      matrix[key][cid] = file
   save_json_file("test.json", matrix)
   #os.system("rm tmp_vids/*")
   for key in sorted(matrix.keys()):
      row_pic = make_row_pic(matrix[key])
      cv2.imwrite("tmp_vids/" + key + ".jpg", row_pic)
      print(key)
   iwild = "/home/ams/amscams/pipeline/tmp_vids/*.jpg"
   tl_out = date + "_row_tl.mp4"
   #cmd = "/usr/bin/ffmpeg -framerate 12 -pattern_type glob -i '" + iwild + "' -c:v libx264 -pix_fmt yuv420p -y " + tl_out + " >/dev/null 2>&1"
   cmd = "/usr/bin/ffmpeg -framerate 12 -pattern_type glob -i \"" + iwild + "\" -c:v libx264 -pix_fmt yuv420p -y " + tl_out 
   print(cmd)
   os.system(cmd)
      

def make_row_pic(data):
   print(data)
   default_w = 300
   default_h = 168
   imgs = [] 
   for cam in sorted(data.keys()):
      file = data[cam]
      if file != "":
         img = cv2.imread(file)
      else:
         img = np.zeros((default_h,default_w,3),dtype=np.uint8)
      img = cv2.resize(img, (default_w, default_h))
      imgs.append(img)
   h,w = imgs[0].shape[:2]
   rw = w * len(data.keys())
   print("RW:", rw)
   blank_image = np.zeros((h,rw,3),dtype=np.uint8)
   x = 0
   y = 0 
   ic = 0
   for img in imgs:
      x1 = x + (ic * w)
      x2 = x1 + w
      print("XY:",ic,  y, y+h, x1, x2, w,h)
      blank_image[y:y+h,x1:x2] = img
      ic += 1
   #cv2.imshow('row', blank_image)
   #cv2.waitKey(30)
   return(blank_image)

def timelapse_all(date, json_conf):


   for cam in json_conf['cameras']:
      cams_id = json_conf['cameras'][cam]['cams_id']
      make_tl_for_cam(date, cams_id, json_conf)

def make_tl_for_cam(date,cam, json_conf):
   print("TL:", cam, date)
   hd_dir = "/mnt/ams2/HD/"
   files = glob.glob(hd_dir + date + "*" + cam + "*.mp4")
   tl_dir = TL_DIR + date + "/"
   if cfe(tl_dir, 1) == 0:
      os.makedirs(tl_dir)
   for file in sorted(files):
      if "trim" not in file:
         fn = file.split("/")[-1]
         out_file = tl_dir + fn
         out_file = out_file.replace(".mp4", ".jpg")
         try:
            image = quick_video_stack(file, 1)
         except:
            continue
     
         #rot_image = rotate_bound(image, 72)
         #img_sm = cv2.resize(rot_image, (640, 360))
         #cv2.imshow('pepe', img_sm)
         #cv2.waitKey(0)

         if cfe(out_file) == 0:
           print(fn, file, out_file )
           try:
              cv2.imwrite(out_file, image)
           except:
              print("FAILED TO WRITE OUT: ", out_file)
         #cv2.imshow('pepe', show_frame)
         #cv2.waitKey(30)
   video_from_images(date, cam, json_conf)

def video_from_images(date, wild, json_conf ):
   TL_DIR = "/mnt/ams2/meteor_archive/" + STATION_ID + "/TL/PICS/"
   tl_dir = TL_DIR + date + "/"
   tl_out = tl_dir + "tl_" + date + "_" + wild + ".mp4"

   iwild = tl_dir + "*" + wild + "*.png"

   print(iwild)
   cmd = "/usr/bin/ffmpeg -framerate 25 -pattern_type glob -i '" + iwild + "' -c:v libx264 -pix_fmt yuv420p -y " + tl_out + " >/dev/null 2>&1"
   print(cmd)
   os.system(cmd)
   print(tl_out)

def six_cam_video(date, json_conf):
   ### make 6 camera tl video for date

   lc = 1
   mc_layout = {}
   for cam_id in MULTI_CAM_LAYOUT:
      mc_layout[cam_id] = lc
      lc += 1
   
 

   tl_dir = TL_DIR + date + "/"
   all_vids = {}
   #files = glob.glob("/mnt/ams2/HD/*" + date + "*.mp4")
   files = glob.glob(tl_dir + "*.jpg")
   print(tl_dir)
   for file in sorted(files):
      if "trim" in file or "comp" in file:
          
         continue
      fn = file.split("/")[-1]
      key = fn[0:16]
      cam = fn[24:30]
      print(key,cam)
      if key not in all_vids:
         all_vids[key] = {}
      if cam not in all_vids[key]:
         pos = mc_layout[cam]
         all_vids[key][cam] = fn


   print("VIDS:", len(all_vids))
   #MULTI_CAM_LAYOUT
   #5 1 2 
   #3 6 4
   final_frames = {}
   for day in all_vids:
      for cam_id in all_vids[day]:
         fn = all_vids[day][cam_id]
         key = fn[0:16]
         cam = fn[24:30]
         print("KEY:", fn, key, cam )
         pos = str(mc_layout[cam])
         if key not in final_frames:
            final_frames[key] = { "1": "", "2": "", "3": "", "4": "", "5": "", "6": "" }
         final_frames[key][pos] = fn 


   save_json_file("test.json", final_frames)
   for min_key in final_frames:
      outfile = tl_dir + "comp_" + min_key + ".jpg"
      #if cfe(outfile) == 0:
      if True:
         make_six_image_comp(min_key, final_frames[min_key], 5)
      else:
         print("skip.", min_key)
   video_from_images(date, "comp", json_conf)
       

def make_six_image_comp(min_key, data,featured=0):  
   pos = {}
   if featured == 0:
      pos["1"] = [0,360,0,640]
      pos["2"] = [0,360,640,1280]
      pos["3"] = [0,360,1280,1920]
      pos["4"] = [360,720,0,640]
      pos["5"] = [360,720,640,1280]
      pos["6"] = [360,720,1280,1920]
      pos["7"] = [360,720,1280,1920]
   if featured == 6:
      pos["1"] = [0,360,0,640]
      pos["2"] = [0,360,640,1280]
      pos["3"] = [0,360,1280,1920]
      pos["4"] = [360,720,1280,1920]
      # FEATURED HERE! 
      pos["5"] = [360,1080,0,1280]
      pos["6"] = [720,1080,1280,1920]
      pos["7"] = [360,720,1280,1920]
   if featured == 5:
      pos["1"] = [0,360,0,640]
      pos["2"] = [0,360,640,1280]
      pos["3"] = [0,360,1280,1920]
      pos["4"] = [360,720,1280,1920]
      # FEATURED HERE! 
      pos["6"] = [360,1080,0,1280]
      pos["5"] = [720,1080,1280,1920]
      pos["7"] = [360,720,1280,1920]

   date = min_key[0:10]
   blank_image = np.zeros((1080,1920,3),dtype=np.uint8)
   tl_dir = TL_DIR + date + "/"
   outfile = tl_dir + "comp_" + min_key + ".jpg"
   for key in data:  
      y1,y2,x1,x2 = pos[key]
      w = x2 - x1
      h = y2 - y1
      imgf =  tl_dir + data[key]
      img = cv2.imread(imgf)
      try:
         img_sm = cv2.resize(img, (w, h))
         #print(y1,y2,x1,x2)
         #print(img_sm.shape)
      except:
         print("Can't make this file!", key, data[key])
         img_sm = np.zeros((h,w,3),dtype=np.uint8)
      blank_image[y1:y2,x1:x2] = img_sm
   #if cfe(outfile) == 0:
   if True:
      print("saving :", outfile)
      cv2.imwrite(outfile, blank_image)
      #cv2.imshow('pepe', blank_image)
      #cv2.waitKey(0)
   else:
      print("Skip.")
