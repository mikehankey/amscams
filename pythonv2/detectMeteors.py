#!/usr/bin/python3 
import os
import subprocess
import json
import sys
import glob

from lib.CalibLib import reduce_object
from lib.FileIO import setup_dirs, cfe, save_failed_detection, save_meteor
from lib.DetectLib import check_for_motion2, id_object, object_report, parse_motion 
from lib.MeteorTests import test_objects, validate_objects
from lib.FileIO import load_json_file,archive_meteor 
from lib.VideoLib import load_video_frames , doHD, get_masks
from lib.ImageLib import stack_frames, draw_stack
from lib.UtilLib import convert_filename_to_date_cam, check_running, fix_json_file
from lib.WebCalib import reduce_meteor_ajax, better_reduce


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
   print("GLOB:", dir)
   for file in files:
      print(file)
      scan_file(file, show)

def scan_file(video_file, show):
   (base_fn, base_dir, image_dir, data_dir,failed_dir,passed_dir) = setup_dirs(video_file)
   recheck = 0
   if "meteors" in video_file:
      print("METEORS HERE.")
      recheck = 1
   (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(video_file)
   masks = get_masks(cam, json_conf,1)

   if cfe(video_file) == 0:
      print("Error: Input file does not exist!", video_file)
      return()
   frames = load_video_frames(video_file, json_conf, 0, 1)
   print("SHOW:", show)
   show = int(show)
   if len(frames) > 0:
      objects = check_for_motion2(frames, video_file,cam, json_conf,show)
   else:
      objects = []

   if len(objects) > 0:
      objects,meteor_found = test_objects(objects,frames)
      objects,meteor_found = validate_objects(objects,frames)
      #print(objects)
   else:
      objects = []
      meteor_found = 0


   if meteor_found == 1 and recheck == 0:
      print("Original Meteor Test Passed. Complete process.")
      stack_file,stack_img = stack_frames(frames, video_file)
      draw_stack(objects,stack_img,stack_file)
      save_meteor(video_file,objects)
      # hd_meteor_processing(video_file,objects)
      # reduce meteor / solve meteor
      # upload meteor
   elif recheck == 0:
      print("Meteor Test Failed.")
      if len(frames) > 0:
         print("LEN FRM", len(frames),video_file)
         stack_file, stack_img = stack_frames(frames, video_file)
         draw_stack(objects,stack_img,stack_file)
      print("SAVE FAILED")
      save_failed_detection(video_file,objects)
   obj_report = object_report(objects,0)
   print(obj_report)
   if meteor_found == 1:
      print("Meteor Test Passed.")


   else:
      print("Meteor Test Failed.")
      if recheck == 1:
         json_file = video_file.replace(".mp4", ".json")
         jd = load_json_file(json_file)
         print("FAILED 2nd pass check. MOVE TO TRASH", jd['sd_video_file'], jd['hd_trim'])
         sd_file = jd['sd_video_file'].split("/")[-1]

         day = sd_file[0:10]
         sd_wild = sd_file.replace(".mp4", "*")
         cmd = "mv " + jd['sd_video_file'] +  " /mnt/ams2/trash"
         print("FAILED:", cmd)
         #os.system(cmd)
         cmd = "mv " + "/mnt/ams2/meteors/" + day + "/" + sd_wild + " /mnt/ams2/trash"
         print("FAILED:", cmd)
         #os.system(cmd)
         if 'hd_trim' in jd:
            hd_file = jd['hd_trim'].split("/")[-1]
            day = hd_file[0:10]
            (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(hd_file)
            hd_wild = fy + "_" + fm + "_" + fd + "_" + fh + "_" + fmin + "_*" + cam + "*" 
            cmd = "mv " + "/mnt/ams2/meteors/" + day + "/" + hd_wild + " /mnt/ams2/trash"
            print("FAILED:", cmd)
            #os.system(cmd)
   print("done scan file")     
   # Now lets refine and reduce the scan
   # link and sync the HD 
   # Remake and rename the trim file

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

def reduce_hd_meteor(video_file, hd_file, hd_trim, hd_crop_file, hd_box,json_conf,trim_time_offset):
   (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(video_file)
   frames = load_video_frames(hd_crop_file, json_conf)
   objects = check_for_motion2(frames, hd_trim,cam, json_conf,0)
   if len(objects) > 0:
      objects,meteor_found = test_objects(objects,frames)
   else:
      objects = []
      meteor_found = 0

   hd_object = []
   print("METEOR FOUND:", meteor_found)
   for object in objects:
      print(object)
      if object['meteor'] == 1:
         print("\n\n\nOBJECT: ", object)
         hd = 1
         crop = 1
         hd_object = reduce_object(object, video_file, hd_file, hd_trim, hd_crop_file, hd_box, json_conf,trim_time_offset)
   return(hd_object)

def fix_meteor_dir(date):
   good_meteors = {}   
   meteor_files =  glob.glob("/mnt/ams2/meteors/" + date + "/*.json")
   sd_passed_files =  glob.glob("/mnt/ams2/SD/proc2/" + date + "/passed/*.mp4")
   for meteor_file in meteor_files:
      if "reduced" not in meteor_file and "star" not in meteor_file and "manual" not in meteor_file:
         mfn = meteor_file.split("/")[-1]
         mfn = mfn.replace(".json", "")
         print(mfn)
         good_meteors[mfn] = {}
         sd_video_file = "/mnt/ams2/meteors/" + date + "/" + mfn + ".mp4"
         if cfe(sd_video_file) == 0:
            print("SD MISSING:", sd_video_file) 
         else:
            print("SD EXISTS:", sd_video_file) 

   print("FIX MD", len(good_meteors), len(sd_passed_files))

def junk(date):
   files =  glob.glob("/mnt/ams2/meteors/" + date + "/*.json")
   meteors = []
   for file in files:
      if "reduced" not in file and "manual" not in file and "star" not in file:
         if cfe(file) == 0:
            continue 
         js = load_json_file(file)
         jd = js
         for object in js['sd_objects']:
            if object['meteor'] == 1:
               for res in object['test_results']:
                  if res[0] == 'Distance':
                     if res[2] < 10:
                        print ("BAD CAP", res[2], file)
                        sd_file = jd['sd_video_file'].split("/")[-1]

                        day = sd_file[0:10]
                        sd_wild = sd_file.replace(".mp4", "*")
                        cmd = "mv " + jd['sd_video_file'] +  " /mnt/ams2/trash"
                        print(cmd)
                        os.system(cmd)
                        cmd = "mv " + "/mnt/ams2/meteors/" + day + "/" + sd_wild + " /mnt/ams2/trash"
                        print(cmd)
                        os.system(cmd)
                        cmd = "mv " + "/mnt/ams2/SD/proc2/" + day + "/passed/" + sd_wild + " /mnt/ams2/trash"
                        print(cmd)
                        os.system(cmd)
                        if 'hd_trim' in jd:
                           if jd['hd_trim'] != 0 and jd['hd_trim'] is not None:
                              print(jd['hd_trim'])
                              hd_file = jd['hd_trim'].split("/")[-1]
                              day = hd_file[0:10]
                              (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(hd_file)
                              hd_wild = fy + "_" + fm + "_" + fd + "_" + fh + "_" + fmin + "_*" + cam + "*"
                              cmd = "mv " + "/mnt/ams2/meteors/" + day + "/" + hd_wild + " /mnt/ams2/trash"
                              print(cmd)
                              os.system(cmd)
                              #exit()

                      


def reject(date):
   files =  glob.glob("/mnt/ams2/meteors/" + date + "/*.json")
   meteors = []
   for file in files:
      if "reduced" not in file and "manual" not in file and "star" not in file:
         file = file.replace(".json", ".mp4")
         meteors.append(file)
   for meteor in meteors:
      cmd = "./detectMeteors.py sf " + meteor
      print(cmd)
      os.system(cmd)


if __name__ == "__main__":
   show = 0
   json_conf = load_json_file("../conf/as6.json") 
   cmd = sys.argv[1]
   running = check_running("detectMeteors")
   if running > 2 and cmd != 'doHD' and cmd != 'sf' and cmd != 'raj' and cmd != 'br' and cmd != 'reject' and cmd != 'fix_meteor_dir':
      print("running ", running)
      exit()
   running = check_running("doHD")
   if running > 3:
      print("already running ", running)
      #exit()
   
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

   if cmd == 'br':
      meteor_json_file = sys.argv[2]
      if len(sys.argv) > 3:
         show = 1 
      better_reduce(json_conf, meteor_json_file, show)

   if cmd == 'raj':
      meteor_json_file = sys.argv[2]
      if len(sys.argv) >= 4:
         cal_params_file = sys.argv[3]
      else:
         cal_params_file = meteor_json_file.replace(".json", "-reduced.json")
      show = 0
      if len(sys.argv) > 4:
         show = 1 
      reduce_meteor_ajax(json_conf, meteor_json_file, cal_params_file, show)
   if cmd == 'fix_meteor_dir':
      date = sys.argv[2]
      fix_meteor_dir(date)
   if cmd == 'junk':
      date = sys.argv[2]
      junk(date)

   if cmd == 'reject':
      date = sys.argv[2]
      reject(date)
 


   if cmd == 'reduce':
      video_file = sys.argv[2]
      json_file = video_file.replace(".mp4", ".json")
      json_data = load_json_file(json_file)
      hd_objects = reduce_hd_meteor(video_file, json_data['hd_file'], json_data['hd_trim'], json_data['hd_crop_file'], json_data['hd_box'], json_conf,json_data['hd_trim_time_offset'])

   if cmd == 'dohd' or cmd == 'doHD':
      video_file = sys.argv[2] 
      json_file = video_file.replace(".mp4", ".json")
      #new_json = fix_json_file(json_file)
      #if new_json is not None:
      #   for line in new_json:
      #      print(new_json)
      #else:
      #   print("JSON GOOD")



      hd_file, hd_trim, hd_crop_file,hd_box,trim_time_offset,trim_dur  = doHD(video_file, json_conf)
      print("AFTER doHD HD TRIM: ", hd_trim)
      sd_json_file = video_file.replace(".mp4", ".json")
      sd_objects = load_json_file(sd_json_file)
      hd_objects = None
      if hd_file is not None and hd_file != 0:
         hd_objects = reduce_hd_meteor(video_file, hd_file, hd_trim, hd_crop_file, hd_box, json_conf,trim_time_offset)
         print("AFTER REDUCE HD TRIM: ", hd_trim)
      archive_meteor (video_file,hd_file,hd_trim,hd_crop_file,hd_box,hd_objects,sd_objects,json_conf,trim_time_offset,trim_dur)
