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
   meteor_video_file = trim_file.replace(".mp4", "-meteor.mp4")
   base_file = base_trim_file.replace(".mp4", "")
   
   meteor_file = base_dir + "/data/" + base_file + "-meteor.txt"
   objfail_file = base_dir + "/data/" + base_file + "-objfail.txt"
   
   trim_stack_file = base_dir + "/images/" + base_file + "-stacked.png"
   trim_stack_meteor_file = base_dir + "/images/" + base_file + "-meteor-stacked.png"

   data_wildcard = base_dir + "/data/" + base_file + "*"
   vid_wildcard = base_dir + "/" + base_file + "*meteor*"

   print ("FILE:", trim_file)
   done_already = check_if_done(trim_file)
   if done_already == 1:
      if sys.argv[1] != "sf":
         print ("SKIP! Already done.")
         return()
      else:
         print ("SKIP! Already done.")
         return()

   cmd = "rm " + data_wildcard
   print(cmd)
   os.system(cmd)
   cmd = "rm " + vid_wildcard
   print(cmd)
   os.system(cmd)
   cmd = "rm " + trim_stack_file 
   print(cmd)
   os.system(cmd)
   cmd = "rm " + trim_stack_meteor_file
   print(cmd)
   os.system(cmd)


   frames = load_video_frames(trim_file)
   print("FRAMES: ", len(frames))

   height, width = frames[0].shape

   #max_cons_motion, frame_data, moving_objects, trim_stack = check_for_motion2(frames, trim_file)
   objects = check_for_motion2(frames, trim_file)
   print("Stacking...")
   #stacked_frame = stack_frames(frames)
   cmd = "./stack-stack.py stack_vid " + trim_file + " mv"
   os.system(cmd)
   stacked_frame = cv2.imread(trim_stack_file)  

   print("DOne Stacking...")
   meteor_objects = []
   meteor_found = 0
   for object in objects:
      status, reason, obj_data = test_object2(object)
      #print("TRIM FILE TESTS:", trim_file)
      print("Object Test Result: ", object['oid'], status, reason)
      if status == 1:
         min_x,min_y,max_x,max_y = obj_data['min_max_xy']
         ow = max_x - min_x
         oh = max_y - min_y
         ow = ow + (ow * 1.2)
         oh = oh + (oh * 1.2)
         if oh > ow:
            ow = oh
         else:
            oh = ow
         cx = (min_x + max_x) / 2
         cy = (min_y + max_y) / 2
         bmin_x = int(cx - (ow / 2 ))
         bmin_y = int(cy - (oh / 2 ))
         bmax_x = int(cx + (ow /2))
         bmax_y = int(cy + (oh /2))

         #print("OBJ_DATA:", obj_data['min_max_xy'])
         oid = object['oid']
         cv2.putText(stacked_frame, str(oid),  (int(cx+5),int(cy+5)), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,0,255), 1)
         cv2.circle(stacked_frame, (int(cx),int(cy)), 1, (255), 1)
         cv2.rectangle(stacked_frame, (bmin_x, bmin_y), (bmax_x, bmax_y), (255,255,255), 2) 
         box = [bmin_x,bmin_y,bmax_x,bmax_y]
         for hist in object['history']:
            fn,x,y,w,h,mx,my = hist
            cox = x + mx
            coy = y + my
            cv2.circle(stacked_frame, (int(cox),int(coy)), 1, (0,255,0), 1)
         meteor_objects.append(object)
         print(object)
         hist = object['history']
         start= hist[0][0] 
         end= hist[-1][0]
         elp_time = (end - start) / 25
         if elp_time < 2:
            elp_time = 2

         cmd = "./doHD.py " + meteor_video_file + " " + str(elp_time) + " " + str(box)
         print("DOHD:", cmd)
         meteor_found = 1
         #os.system(cmd)


   meteor_objects = merge_meteor_objects(meteor_objects) 
   #cv2.imshow('pepe', stacked_frame)
   #cv2.waitKey(100)

   if meteor_found >= 1:
      print ("METEOR", meteor_file)
      mt = open(meteor_file, "w")
      mt.write(str(objects))
      mt.close()
   else:
      print ("NO METEOR", objfail_file)
      mt = open(objfail_file, "w")
      mt.write(str(objects))
      mt.close()





   exit()
   stacked_image_np = np.asarray(trim_stack)
   found_objects, moving_objects = object_report(trim_file, frame_data)

   stacked_image = draw_obj_image(stacked_image_np, moving_objects,trim_file, stacked_image_np)

   if sys.argv[1] == 'sf':
      cv2.namedWindow('pepe')
      cv2.imshow('pepe', stacked_image)
      cv2.waitKey(0)
   passed,all_objects = test_objects(moving_objects, trim_file, stacked_image_np)

   meteor_found = 0
   meteor_objects = []
   for object in all_objects:
      #print("OID:", object['oid'])
      #print("METEOR YN:", object['meteor_yn'])
      if object['meteor_yn'] == 1:
         print("START: ", object['first']) 
         print("END: ", object['last']) 
         trim_meteor(trim_file, object['first'][0], object['last'][0])
         meteor_found = 1
         meteor_objects.append(object)


   cmd = "./stack-stack.py stack_vid " + trim_file + " mv"
   os.system(cmd)
   print("STACK", cmd)

   #for object in meteor_objects:
   #   check_final_stack(trim_stack,object)

   meteor_found = 0

   for object in meteor_objects:
      if object['meteor_yn'] == 1:
         for key in object:
            print(key,object[key])
         box = str(object['box'])
         elp_time = object['elp_time'] + 1
         box = box.replace(" ", "")
         box = box.replace("[", "")
         box = box.replace("]", "")
         cmd = "./doHD.py " + meteor_video_file + " " + str(elp_time) + " " + str(box)
         print("DOHD:", cmd)
         os.system(cmd)
         meteor_found = 1






   #complete_scan(trim_file, passed, found_objects)

def merge_meteor_objects(meteor_objects):
   print(meteor_objects)

def scan_dir(dir):
   files = glob.glob(dir + "/*trim*.mp4")
   for file in files:
     if "meteor" not in file:
        print(file)
        scan_trim_file(file) 

cmd = sys.argv[1]
if cmd == 'sf':
   trim_file = sys.argv[2]
   trim_file = trim_file.replace("-meteor.mp4", ".mp4")
   scan_trim_file(trim_file)
if cmd == 'scan_dir':
   sdir = sys.argv[2]
   scan_dir(sdir)
