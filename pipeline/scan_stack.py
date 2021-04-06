
import sys
import glob
from MinFile import MinFile
import datetime
from lib.PipeUtil import cfe, load_json_file, save_json_file, fn_dir, load_mask_imgs
import cv2
import numpy as np

def run_analyzer(day, cam, file_limit=10):

   in_dir = "/mnt/ams2/SD/proc2/" + day + "/" 
   files = glob.glob(in_dir + "*" + cam + "*.mp4")
   for vfile in sorted(files, reverse=True):
      min_file = MinFile(vfile)
      if min_file.moving_objects is not None:
         for obj in min_file.moving_objects:
            if obj['report']['plane_score'] < 2:
               print(min_file.stack_file)
               img = cv2.imread(min_file.stack_file)
               cv2.imshow('pepe', img)
               for key in obj['report']:
                  print(key, obj['report'][key])
               print("")
               cv2.waitKey(0)
            #else: 
            #   print("plane:", obj['report']['plane_score'])



def run_scan_and_stack(day, cam, file_limit=10):
   json_conf = load_json_file("../conf/as6.json")
   mask_imgs, sd_mask_imgs = load_mask_imgs(json_conf)

   in_dir = "/mnt/ams2/SD/proc2/" + day + "/" 
   files = glob.glob(in_dir + "*" + cam + "*.mp4")

   #if len(files) > file_limit:
   #   files = files[0:file_limit]
      

   com_mask = None
   for vfile in sorted(files, reverse=True):
      fn = vfile.split("/")[-1]
      el = fn.split("_")
      cam = el[-1].replace(".mp4", "")
      if "trim" in vfile:
         continue
      print(cam, vfile, sd_mask_imgs[cam].shape)
      if cam in sd_mask_imgs:
         mask_img = sd_mask_imgs[cam]
      else:
         mask_img = None

      # run scan and stack
      start = datetime.datetime.now()
      min_file = MinFile(sd_filename= vfile)
      if com_mask is not None:
         min_file.scan_and_stack(com_mask)
      else:
         min_file.scan_and_stack(mask_img)

      if cfe(min_file.stack_file) == 1: 
         last_stack = cv2.imread(min_file.stack_file)
         print("LAST STACK FILE:", min_file.stack_file)
         last_stack = cv2.cvtColor(last_stack, cv2.COLOR_BGR2GRAY) 
         mean_val = np.mean(last_stack)
         thresh_val = mean_val + 50
         _   , last_stack_mask = cv2.threshold(last_stack.copy(), thresh_val, 255, cv2.THRESH_BINARY)
         min_file.mask_file = min_file.stack_file.replace(".jpg", "-mask.jpg")
         cv2.imwrite(min_file.mask_file, last_stack_mask,[cv2.IMWRITE_JPEG_QUALITY, 40] )
      else:
         print("LAST STACK DOESNT EXIST!", min_file.stack_file)
      
      #mask_img = np.concatenate((mask_img, last_stack_mask), axis=1)
      com_mask = cv2.addWeighted(mask_img, .5, last_stack_mask, .5, 0)
      _, com_mask = cv2.threshold(com_mask.copy(), 50, 255, cv2.THRESH_BINARY)
      com_mask = cv2.dilate(com_mask.copy(), None , iterations=4)
      
      show_image = last_stack_mask.copy()
      if cfe(min_file.moving_file) == 1:
         motion = load_json_file(min_file.moving_file)
         print(motion)
         for obj in motion:
            xs = []
            ys = []
            for i in range(0,len(obj['ofns'])):
               xs.append(obj['oxs'][i])
               xs.append(obj['oxs'][i] + obj['ows'][i])
               ys.append(obj['oys'][i])
               ys.append(obj['oys'][i] + obj['ohs'][i])
            cv2.rectangle(show_image, (min(xs),min(ys)), (max(xs) , max(ys) ), (255, 255, 255), 1) 
         #cv2.putText(show_image, str("MOTION DETECTED."),  (10, 30), cv2.FONT_HERSHEY_SIMPLEX, .3, (200, 200, 200), 1)
         #cv2.imshow('pepe5', show_image) 
         #cv2.imshow('pepe4', last_stack) 
         #cv2.waitKey(30)
      #else:
         #cv2.imshow('pepe4', last_stack) 
         #cv2.imshow('pepe5', show_image) 
         #cv2.waitKey(30)
      #cv2.imshow('pepe3', com_mask) 
      #cv2.waitKey(30)
      end = datetime.datetime.now()
      elp = (end - start).total_seconds()
      print("Elapsed:", elp)


# Usage : python3 scan_stack.py YYYY_MM_DD CAM_ID
day = sys.argv[1]
cam = sys.argv[2]
run_scan_and_stack(day,cam)
run_analyzer(day,cam)

