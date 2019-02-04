#!/usr/bin/python3 

import json
import sys
import glob

from lib.CalibLib import reduce_object
from lib.FileIO import setup_dirs, cfe, save_failed_detection, save_meteor
from lib.DetectLib import check_for_motion2, id_object, object_report, parse_motion 
from lib.MeteorTests import test_objects
from lib.FileIO import load_json_file,archive_meteor 
from lib.VideoLib import load_video_frames , doHD
from lib.ImageLib import stack_frames, draw_stack
from lib.UtilLib import convert_filename_to_date_cam


# Copyright (C) 2018 Mike Hankey - AllSkyCams.com
# Meteor Camera Software 

"""
These executable scripts rely on functions held in these libraries.
libs/BatchLib.py -- holds functions for batch processing data pipeline/flow 
libs/CalibLib.py -- holds functions specifcally for dealing with calibration and solving images
libs/CloudLib.py -- holds functions specifcally for communicating with cloud APIs 
libs/DetectLib.py -- holds functions for detecting and classifing objects 
libs/FileIO.py -- holds functions for grabbing and manipulating various files
libs/ImageLib.py -- holds common functions for dealing with images: median_frames, best_thresh, etc
libs/VideoLib.py -- holds generic functions for dealing with video (get frames, ffmpeg functions, finding HD files, splitting, merging, stacking video etc) 
libs/UtilLib.py -- Holds various utlity functions


"""

def scan_dir(dir, show):
   files = glob.glob(dir + "*trim*.mp4")
   for file in files:
      print(file)
      scan_file(file, show)

def scan_file(video_file, show):
   (base_fn, base_dir, image_dir, data_dir,failed_dir,passed_dir) = setup_dirs(video_file)
   (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(video_file)

   if cfe(video_file) == 0:
      print("Error: Input file does not exist!", video_file)
      exit()
   frames = load_video_frames(video_file, json_conf)
   print("SHOW:", show)
   show = int(show)
   objects = check_for_motion2(frames, video_file,cam, json_conf,show)

   if len(objects) > 0:
      objects,meteor_found = test_objects(objects,frames)
   else:
      objects = []
      meteor_found = 0


   if meteor_found == 1:
      print("Meteor Test Passed.")
      stack_file,stack_img = stack_frames(frames, video_file)
      draw_stack(objects,stack_img,stack_file)
      save_meteor(video_file,objects)
      # hd_meteor_processing(video_file,objects)
      # reduce meteor / solve meteor
      # upload meteor
   else:
      print("Meteor Test Failed.")
      stack_file, stack_img = stack_frames(frames, video_file)
      draw_stack(objects,stack_img,stack_file)
      print("SAVE FAILED")
      save_failed_detection(video_file,objects)
      print("MIKE")
   obj_report = object_report(objects)
   print(obj_report)
   if meteor_found == 1:
      print("Meteor Test Passed.")
   else:
      print("Meteor Test Failed.")
     
def do_all(json_conf): 
   show = 0
   proc_dir = json_conf['site']['proc_dir']
   temp_dirs = glob.glob(proc_dir + "/*")
   proc_days = []
   for proc_day in temp_dirs :
      if "daytime" not in proc_day and "json" not in proc_day and "meteors" not in proc_day and cfe(proc_day, 1) == 1:
         proc_days.append(proc_day+"/")
   for proc_day in sorted(proc_days,reverse=True):
      print("SCAN DIR:", proc_day)
      scan_dir(proc_day, show)

def reduce_hd_meteor(video_file, hd_file, hd_trim, hd_crop_file, hd_box,json_conf):
   (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(video_file)
   frames = load_video_frames(hd_crop_file, json_conf)
   objects = check_for_motion2(frames, hd_trim,cam, json_conf,0)
   if len(objects) > 0:
      objects,meteor_found = test_objects(objects,frames)
   else:
      objects = []
      meteor_found = 0
   print("METEOR FOUND:", meteor_found)
   for object in objects:
      if object['meteor'] == 1:
         print(object)
         hd = 1
         crop = 1
         hd_object = reduce_object(object, video_file, hd_file, hd_trim, hd_crop_file, hd_box, json_conf)
   return(hd_object)




if __name__ == "__main__":
   show = 0
   json_conf = load_json_file("../conf/as6.json") 
   cmd = sys.argv[1]
   if len(sys.argv) >=3:
      video_file = sys.argv[2]
   if len(sys.argv) == 4:
       show = sys.argv[3]
   if cmd == 'sf':
      scan_file(video_file, show)
   if cmd == 'sd':
      dir = sys.argv[2]
      scan_dir(dir, show)
   if cmd == 'do_all':
      do_all(json_conf)
   if cmd == 'pm':
      parse_motion(video_file, json_conf)
   if cmd == 'dohd' or cmd == 'doHD':
      video_file = sys.argv[2] 
      hd_file, hd_trim, hd_crop_file,hd_box = doHD(video_file, json_conf)
 
      hd_objects = reduce_hd_meteor(video_file, hd_file, hd_trim, hd_crop_file, hd_box, json_conf)
      archive_meteor (video_file,hd_file,hd_trim,hd_crop_file,hd_box,hd_objects,json_conf)
