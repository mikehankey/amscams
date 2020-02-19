#!/usr/bin/python3

"""
This script is the work manager for each day. 
  * Run this script through the day to keep data up to date and in sync.
  * Run this script after a day has finished to close out all work relating to that day. 
  * Script will perform the following functions.
     - Make sure all processed video files, stack images and data file are in the right place
     - Create archive time lapse videos of 24 hours of stack images for the day
     - Create meteor index for the day
     - Make sure all meteor thumbs exist
     - Make sure all meteors have been moved to the archive
     - Delete any false meteors tagged by admins or others
     - Sync all relevant files for the day to wasabi (archive meteors, preview images, NOAA files, event date
     - Run detections for the day (if master node)
     - Run all event solutions for the day
     - Stack daytime images
     - Produce Ops report for the day
     - Purge Disk Space



"""

import os
import glob
import sys
from lib.FileIO import load_json_file, save_json_file

json_conf = load_json_file("../conf/as6.json")


def get_processing_status(day):
   proc_dir = "/mnt/ams2/SD/proc2/" + day + "/*"
   proc_img_tn_dir = "/mnt/ams2/SD/proc2/" + day + "/images/*tn.png"
   proc_vids = glob.glob(proc_dir)
   proc_tn_imgs = glob.glob(proc_img_tn_dir)

   #proc_img_dir = "/mnt/ams2/SD/proc2/" + day + "/images/*.png"
   #proc_imgs = glob.glob(proc_img_dir)


   day_vids = glob.glob("/mnt/ams2/SD/proc2/daytime/" + day + "*.mp4")
   cams_queue = glob.glob("/mnt/ams2/CAMS/queue/" + day + "*.mp4")
   in_queue = glob.glob("/mnt/ams2/SD/" + day + "*.mp4")
   return(proc_vids, proc_tn_imgs, day_vids,cams_queue,in_queue)

def get_meteor_status(day):
   detect_files = []
   arc_file = []
   year, mon, dom = day.split("_")
   detect_dir = "/mnt/ams2/meteors/" + day + "/"
   arc_dir = "/mnt/ams2/meteor_archive/" + json_conf['site']['ams_id'] + "/METEOR/" + year + "/" + mon + "/" + dom + "/"
   
   # get detect and arc files
   dfiles = glob.glob(detect_dir + "*trim*.json")
   arc_files = glob.glob(detect_dir + "*trim*.json")

   # filter out non-meteor or dupe meteor json files
   for df in dfiles:
      if "reduced" not in df and "manual" not in df and "stars" not in df:
         detect_files.append(df)

   return(detect_files, arc_files)
   

def do_all(day):
   proc_vids, proc_tn_imgs, day_vids,cams_queue,in_queue = get_processing_status(day)
   detect_files, arc_files = get_meteor_status(day)

   # figure out how much of the day has completed processing
   print("Processing report for day: ", day)
   print("Processed Videos:", len(proc_vids))
   print("Processed Thumbs:", len(proc_tn_imgs))
   print("Un-Processed Daytime Videos:", len(day_vids))
   print("Un-Processed CAMS Queue:", len(cams_queue))
   print("Un-Processed IN Queue:", len(in_queue))
   print("Possible Meteor Detections:", len(detect_files))
   print("Archived Meteors :", len(arc_files))
   print("Unique Meteors: ???" )
   print("Multi-station Events: ???" )
   print("Solved Events: ???" )
   print("Events That Failed to Solve: ???" )

   if len(cams_queue) < 10 and len(in_queue) < 10:
      proc_status = "up-to-date"

 
   # make the meteor detection index for today
   os.system("./autoCal.py meteor_index " + day)

   # make the detection preview images for the day
   os.system("./flex-detect.py bmpi " + day)

   # make the detection preview images for the day
   os.system("./wasabi.py sa " + day)



cmd = sys.argv[1]

if cmd == "all":
   do_all(sys.argv[2])
