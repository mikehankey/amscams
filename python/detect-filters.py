#!/usr/bin/python3

import glob
import cv2
from detectlib import *
import sys
import datetime
import json


json_file = open('../conf/as6.json')
json_str = json_file.read()
json_conf = json.loads(json_str)
proc_dir = json_conf['site']['proc_dir']



def scan_trim_file(trim_file):



   el = trim_file.split("/")
   base_trim_file = el[-1]
   base_dir = trim_file.replace(base_trim_file, "")

   base_file = base_trim_file.replace(".mp4", "")
   
   meteor_file = base_dir + "/data/" + base_file + "-meteor.txt"
   objfail_file = base_dir + "/data/" + base_file + "-objfail.txt"

   data_wildcard = base_dir + "/data/" + base_file + "*"
   vid_wildcard = base_dir + "/" + base_file + "*meteor*"

   print ("FILE:", trim_file)
   done_already = check_if_done(trim_file)
   if done_already == 1:
      if sys.argv[1] != "sf":
         print ("SKIP! Already done.")
         return()

   cmd = "rm " + data_wildcard
   print(cmd)
   os.system(cmd)
   cmd = "rm " + vid_wildcard
   print(cmd)
   os.system(cmd)


   frames = load_video_frames(trim_file)
   print("FRAMES: ", len(frames))
   max_cons_motion, frame_data, moving_objects, trim_stack = check_for_motion(frames, trim_file)
   stacked_image_np = np.asarray(trim_stack)
   found_objects, moving_objects = object_report(trim_file, frame_data)

   stacked_image = draw_obj_image(stacked_image_np, moving_objects)

   if sys.argv[1] == 'sf':
      cv2.namedWindow('pepe')
      cv2.imshow('pepe', stacked_image)
      cv2.waitKey(1)
   passed,all_objects = test_objects(moving_objects)

   print("ALL OBJECTS", all_objects)
   meteor_found = 0
   for object in all_objects:
      print("OID:", object['oid'])
      print("METEOR YN:", object['meteor_yn'])
      if object['meteor_yn'] == 1:
         print("START: ", object['first']) 
         print("END: ", object['last']) 
         trim_meteor(trim_file, object['first'][0], object['last'][0])
         meteor_found = 1

   cmd = "./stack-stack.py stack_vid " + trim_file + " mv"
   os.system(cmd)
   print("STACK", cmd)

   if meteor_found >= 1:
      print ("METEOR")
      mt = open(meteor_file, "w")
      mt.write(str(found_objects))
      mt.close()
   else:
      print ("NO METEOR")
      mt = open(objfail_file, "w")
      mt.write(str(found_objects))
      mt.close()




   #complete_scan(trim_file, passed, found_objects)

def scan_dir(dir):
   files = glob.glob(dir + "/*trim*.mp4")
   for file in files:
     if "meteor" not in file:
        print(file)
        scan_trim_file(file) 

cmd = sys.argv[1]
if cmd == 'sf':
   trim_file = sys.argv[2]
   scan_trim_file(trim_file)
if cmd == 'scan_dir':
   sdir = sys.argv[2]
   scan_dir(sdir)
