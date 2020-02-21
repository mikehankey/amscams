#!/usr/bin/python3

from lib.UtilLib import convert_filename_to_date_cam
from datetime import datetime

from lib.VIDEO_VARS import PREVIEW_W, PREVIEW_H, SD_W, SD_H
import time
from PIL import Image
import glob
import numpy as np
import cv2
import os
import sys
import json



from lib.VideoLib import load_video_frames
from lib.ImageLib import stack_frames , stack_glob, stack_stack, make_10_sec_thumbs
from lib.FileIO import load_json_file , cfe
from lib.UtilLib import check_running
from lib.BatchLib import batch_obj_stacks

json_conf = load_json_file("../conf/as6.json")

def mont_min(files, cams):
   blank_image = np.zeros((PREVIEW_H,PREVIEW_W),dtype=np.uint8)
   mont_w = (PREVIEW_W * 3) 
   mont_h = (PREVIEW_H * 2) 
   mont_img = np.zeros((mont_h,mont_w),dtype=np.uint8)
   mont_img = cv2.cvtColor(mont_img,cv2.COLOR_GRAY2RGB)
   mont = {}
   #print("MONT W/H:", mont_w, mont_h)
   #print("PREV W/H:", PREVIEW_W, PREVIEW_H)
   for file in files:
      (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(file)
      stack_arc_dir = "/mnt/ams2/meteor_archive/" + json_conf['site']['ams_id'] + "/" + "NOAA" + "/ARCHIVE/" + fy + "/" + fm + "_" + fd + "/STACKS/" 
      mont[cam] = file
      min_mont_file = fy + "_" + fm + "_" + fd + "_" + fh + "_" + fmin + ".jpg"

   if cfe(stack_arc_dir + min_mont_file) == 1:
      return()

   #print(cams)
   #print(stack_arc_dir) 
   if cfe(stack_arc_dir, 1) == 0:
      os.makedirs(stack_arc_dir)
   max_c = 2
   max_r = 1
   rc = 0
   cc = 0
   cam_pos = {}
   cam_c = 0 
   for cam in cams:
      # North
      if cam_c == 0:
         cam_pos[cam] = [0,1]
      # North West
      if cam_c == 4:
         cam_pos[cam] = [0,0]
      # North East
      if cam_c == 1:
         cam_pos[cam] = [0,2]
      # South West
      if cam_c == 3:
         cam_pos[cam] = [1,0]
      # Zenit 
      if cam_c == 5:
         cam_pos[cam] = [1,1]
      # South East
      if cam_c == 2:
         cam_pos[cam] = [1,2]
      cam_c += 1

   for cam in cams:
      if cam in mont:
         #print(cam, mont[cam])
         thumb = cv2.imread(mont[cam])
         th, tw = thumb.shape[:2]
         if th != PREVIEW_H:
            thumb = cv2.resize(thumb, (PREVIEW_W,PREVIEW_H))
         th, tw = thumb.shape[:2]
         rc, cc = cam_pos[cam] 
         y1 = rc * th 
         y2 = (rc * th) + th 
         x1 = cc * tw  
         x2 = (cc * tw) + tw 
         if len(thumb.shape) == 3:
            mont_img[y1:y2,x1:x2] = thumb
         else:
            thumb = cv2.cvtColor(thumb,cv2.COLOR_GRAY2RGB)
            mont_img[y1:y2,x1:x2] = thumb
  
   mont_img = cv2.resize(mont_img, (900,506))
   cv2.imshow('pepe', mont_img)
   cv2.waitKey(70)
   print("MONT IMG:", mont_img.shape)
   cv2.imwrite(stack_arc_dir + min_mont_file , mont_img)
   print("SAVED:", stack_arc_dir + min_mont_file)

def montage_time_lapse(day):
   fy,fm,fd = day.split("_")
   dom = day
   night_dir = "/mnt/ams2/SD/proc2/" + day + "/images/*tn*.png"
   night_files = glob.glob(night_dir)
   min_data = {}
   cams = []
   for cc in json_conf['cameras']:
      cams.append(json_conf['cameras'][cc]['cams_id'])

   for file in night_files:
      fn = file.split("/")[-1]
      el = fn.split("_")   
      year, mon, day, hour, min, sec = el[0], el[1], el[2], el[3], el[4], el[5] 
      key = hour + "_" + min
      if key not in min_data:
         min_data[key] = []
      min_data[key].append(file)

   for key in sorted(min_data):
      mont_min(min_data[key], cams)
      print(key, min_data[key]) 

   stack_arc_dir = "/mnt/ams2/meteor_archive/" + json_conf['site']['ams_id'] + "/" + "NOAA" + "/ARCHIVE/" + fy + "/" + fm + "_" + fd + "/STACKS/" 
   TMP_DIR = stack_arc_dir
   outfile = TMP_DIR + dom + "-" + json_conf['site']['ams_id'] + "-timelapse.mp4"
   cmd = """/usr/bin/ffmpeg -y -framerate 25 -pattern_type glob -i '""" + TMP_DIR + """*.jpg' \
      -c:v libx264 -r 25 -vf scale='1280x720' -pix_fmt yuv420p """ + outfile
   os.system(cmd)
   print(cmd)

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

def move_day_files(day):

   proc_dir = "/mnt/ams2/SD/proc2/daytime/" + day + "/"
   day_stacks = glob.glob("/mnt/ams2/SD/proc2/daytime/" + day + "*.png")
   final_dir = "/mnt/ams2/SD/proc2/" + day + "/" 
   for stack in day_stacks:
      vid = stack.replace("-stacked.png", ".mp4")
      tn = stack.replace("-stacked.png", "-stacked-tn.png")
      tn_fn = tn.split("/")[-1]
      if cfe(vid) == 1:
         cmd = "mv " + vid + " " + final_dir
         print(cmd)
         os.system(cmd)
      if cfe(stack) == 1:
         cmd = "mv " + stack + " " + final_dir + "images/" + tn_fn
         print(cmd)
         os.system(cmd)
      

def stack_day(day):
   print("Stack day.", day)
   # first make sure the batch is not already running.
   running = check_running("stackVideo.py")
   print("Running:", running)
   if running > 1:
      print("Already running.")
      exit()



   if day == "all":
      day_files = sorted(glob.glob("/mnt/ams2/SD/proc2/daytime/*.mp4"), reverse=True)
      print("/mnt/ams2/SD/proc2/daytime/" + "*.mp4")
      now = datetime.now()
      day = now.strftime("%Y_%m_%d")
   else:
      day_files = sorted(glob.glob("/mnt/ams2/SD/proc2/daytime/" + day + "*.mp4"), reverse=True)
      print("/mnt/ams2/SD/proc2/daytime/" + day + "*.mp4")

   # Move day stacks and images to proc2 (or proc3) dir
   proc_dir = "/mnt/ams2/SD/proc2/" + day + "/"

   if cfe(proc_dir, 1) == 0:
      os.makedirs(proc_dir)
   if cfe(proc_dir + "images/", 1) == 0:
      os.makedirs(proc_dir + "images/")

   for file in day_files:
      stack = file.replace(".mp4", "-stacked.png") 
      if cfe(stack) == 0:
         start_time = time.time() 
         limit = 0
         mask = 0
         crop = []
         color = 1
         skip = 10
         resize = [PREVIEW_W,PREVIEW_H]
         #resize = None
         frames = load_video_frames(file, json_conf, limit, mask, crop, color, skip, resize)
         print("COLOR?", frames[0].shape)
         if len(frames) == 0:
            print("NO frames bad vid?", file)
         else:
            stack_frames(frames, stack)
            print("DAY STACK:", stack)
            elapsed_time = time.time() - start_time
            print("STACK TIME:", elapsed_time)
      # mv vid and stack files to proc dir
      cmd = "mv " + file + " " + proc_dir 
      print(cmd) 
      os.system(cmd)  
      cmd = "mv " + stack + " " + proc_dir + "images/"
      print(cmd) 
      os.system(cmd)  




cmd = sys.argv[1]


if cmd == 'sv':
   video_file = sys.argv[2]
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

if cmd == '10sec':
   sd_video_file = sys.argv[2]
   el = sd_video_file.split("/")
   fn = el[-1]
   out_file = "/mnt/ams2/trash/" + fn
   cmd = "/usr/bin/ffmpeg -i " + sd_video_file + " -vf scale=\"320:-1\" " + out_file + " >/dev/null 2>&1"
   os.system(cmd)
   frames = load_video_frames(out_file, json_conf)
   #print("frames:", len(frames))
   make_10_sec_thumbs(sd_video_file, frames, json_conf)

if cmd == 'stack_day' or cmd == 'sd':
   stack_day(sys.argv[2])
if cmd == 'move_day_files' or cmd == 'mdf':
   move_day_files(sys.argv[2])
if cmd == 'mtl' :
   montage_time_lapse(sys.argv[2])

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
