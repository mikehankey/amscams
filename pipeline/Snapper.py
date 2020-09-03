#!/usr/bin/python3
"""
# CRONS
0 * * * * cd /home/ams/amscams/pipeline/; ./Snapper.py > /dev/null 2>&1
5 0 * * * cd /home/ams/amscams/pipeline/; ./Snapper.py tlm yest yest> /dev/null 2>&1
20 */2 * * * cd /home/ams/amscams/pipeline/; ./Snapper.py pd > /dev/null 2>&1


"""
import cv2
import numpy as np
from lib.DEFAULTS import *
import sys
from lib.PipeUtil import check_running, load_json_file, cfe, save_json_file
import os
import time
from datetime import datetime
from datetime import date
from datetime import timedelta
SNAP_DIR = "/mnt/ams2/SNAPS/"
import glob
# script for grabbing snaps every 30 seconds
json_conf = load_json_file("../conf/as6.json")

def purge_files():
   files = glob.glob(SNAP_DIR + "*")
   for file in files:
      if "comp" in file:
         cmd = "rm " + file
         print(cmd)
         os.system(cmd)
      else:
         fn = file.split("/")[-1]
         fnd = fn[0:13]
         dir_date = datetime.strptime(fnd , "%Y_%m_%d_%H")
         elp = dir_date - datetime.now()
         days_old = abs(elp.total_seconds()) / 86400
         if days_old > 1.5:
            print("DAYS OLD:", days_old)
            cmd = "rm " + file
            print(cmd)
            os.system(cmd)

def images_to_video(wild, cam, outfile, type="jpg"):
   if cam is not None:
      wild_str = wild + "*" + cam + "." + type 
      cmd = "/usr/bin/ffmpeg -framerate 25 -pattern_type glob -i '" + wild_str + "' -c:v libx264 -pix_fmt yuv420p -y " + outfile + " >/dev/null 2>&1"
   else:
      wild_str = wild + "." + type
      cmd = "/usr/bin/ffmpeg -framerate 25 -pattern_type glob -i '" + wild_str + "' -c:v libx264 -pix_fmt yuv420p -y " + outfile + " >/dev/null 2>&1"
   print(cmd)
   os.system(cmd)
   print(outfile)


def multi_cam_tl(date, outfile):
   print("DATE:", date)
   print("OUTFILE:", outfile)
   mc_layout = {}
   lc = 1
   for cam_id in MULTI_CAM_LAYOUT:
      mc_layout[cam_id] = lc
      lc += 1

   tc = len(mc_layout)

   tl_dir = "/mnt/ams2/SNAPS/"
   all_files = {}
   files = glob.glob(tl_dir + date + "*.png")
   print("GLOB:", tl_dir + date + "*.png")
   for file in sorted(files):
      if "trim" in file or "comp" in file:

         continue
      fn = file.split("/")[-1]
      key = fn[0:18]
      cam = fn[24:30]
      if key not in all_files:
         all_files[key] = {}
      if cam not in all_files[key]:
         pos = mc_layout[cam]
         all_files[key][cam] = fn


   #MULTI_CAM_LAYOUT
   #5 1 2
   #3 6 4
   final_frames = {}
   for day in all_files:
      for cam_id in all_files[day]:
         fn = all_files[day][cam_id]
         key = fn[0:18]
         cam = fn[24:30]
         pos = str(mc_layout[cam])
         if key not in final_frames:
            if tc == 7:
               final_frames[key] = { "1": "", "2": "", "3": "", "4": "", "5": "", "6": "", "7": ""}
               final_frames[key][pos] = fn
            if tc == 6:
               final_frames[key] = { "1": "", "2": "", "3": "", "4": "", "5": "", "6": "" }
               final_frames[key][pos] = fn
         else:
            final_frames[key][pos] = fn
   save_json_file("test.json", final_frames)

   mc = 0
   fc = 1
   for min_key in final_frames:
      outfile = tl_dir + "comp_" + min_key + ".jpg"
      if True:
         make_multi_image_comp(min_key, final_frames[min_key], str(fc))
      else:
         print("skip.", min_key)
      if mc % 600 == 0:
         fc += 1
      if fc > tc:
         fc = 1
      mc += 1
   images_to_video(tl_dir + "comp", None, "/mnt/ams2/SNAPS_TL/" + date + ".mp4")
    

def make_multi_image_comp(min_key, data,featured=0):
   pos = {}
   tl_dir = "/mnt/ams2/SNAPS/"
   outfile = tl_dir + "comp_" + min_key + ".jpg"
   # 6 cam layout
   if len(data) == 6:
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
   if len(data) == 7:
      if True:
         pos["1"] = [0,270,0,480]
         pos["2"] = [0,270,480,960]
         pos["3"] = [0,270,960,1440]
         pos["4"] = [0,270,1440,1920]
         pos["5"] = [270,540,1440,1920]
         pos["6"] = [540,810,1440,1920]
         pos["7"] = [810,1080,1440,1920]
         pos['featured'] = [0,270,1440,1080]
   date = min_key[0:10]
   blank_image = np.zeros((1080,1920,3),dtype=np.uint8)
   feature_file = tl_dir + data[featured]
   if cfe(feature_file) == 1:
      fimg = cv2.imread(feature_file)
      fb_img = cv2.resize(fimg, (1440, 810))
      fx1,fy1,fx2,fy2 = pos['featured']
      blank_image[fy1:fy2,fx1:fx2] = fb_img

   for key in data:
      y1,y2,x1,x2 = pos[key]
      w = x2 - x1
      h = y2 - y1
      imgf =  tl_dir + data[key]
      if cfe(imgf) == 1:
         img = cv2.imread(imgf)
         img_sm = cv2.resize(img, (w, h))
      else:
         img_sm = np.zeros((h,w,3),dtype=np.uint8)
      #except:
      #try:
      #   print("Can't make this file!", key, data[key])
      #   img_sm = np.zeros((h,w,3),dtype=np.uint8)
      blank_image[y1:y2,x1:x2] = img_sm
   #if cfe(outfile) == 0:
   if True:
      print("saving :", outfile)
      #cv2.imshow('pepe', blank_image)
      #cv2.waitKey(40)
      cv2.imwrite(outfile, blank_image)
      #cv2.imshow('pepe', blank_image)
      #cv2.waitKey(0)
   else:
      print("Skip.")





def snap_runner():
   cams = {}
   for cam in json_conf['cameras']:
      id = json_conf['cameras'][cam]['cams_id']
      ip = json_conf['cameras'][cam]['ip']
      url = "rtsp://" + ip + json_conf['cameras'][cam]['hd_url']
      cams[id] = url
   running = check_running("Snapper.py")
   if running > 3:
      print("Snapper already running.")
      return()
   run = 1



   while run == 1:

      sec = int(datetime.now().strftime("%S"))
      if sec >= 50:
         sleep_time = 1
      elif 20 <= sec <= 30:
         sleep_time = 1
      else:
         sleep_time = 9


      if sec == 0 or sec == 30:
         for cam in cams:
            date_str = datetime.now().strftime("%Y_%m_%d_%H_%M_%S_000_")
            outfile = SNAP_DIR + date_str + cam + ".png"
            url = cams[cam]
            cmd = "/usr/bin/ffmpeg -y -i '" + url + "' -vframes 1 " + outfile + " >/dev/null 2>&1 &"
            print(cmd)
            os.system(cmd)
         time.sleep(20)
      print("Cur sec:", sec, "Sleeping for ", sleep_time)
      time.sleep(sleep_time)

if len(sys.argv) == 1:
   snap_runner()
else:
   if sys.argv[1] == 'tl':
      usage = "./Snapper.py tl wild_card cam_no out \n DO NOT USE * in wild card";
      wild = sys.argv[2]
      cam = sys.argv[3]
      out = sys.argv[4]
      images_to_video(wild, cam, out) 
   if sys.argv[1] == 'tlm':
      date = sys.argv[2]
      outfile = sys.argv[3]
      if date == "yest":
         today = datetime.today() 
         yest = today - timedelta(days=1)
         date = str(yest)[0:10].replace("-", "_")
         outfile = "/mnt/ams2/SNAP_TL/" + date + ".mp4"
      multi_cam_tl(date, outfile)
   if sys.argv[1] == 'pd':
      purge_files()
