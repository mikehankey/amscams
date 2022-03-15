""" 

This is the main stacker program and should be running all the time to stay ontop of the incoming data.
This program will only do a few things:
   - stack the mp4 into a -stacked.jpg while also saving the first frame as -first.jpg
   - produce a per-subframe max pixel list and from that an 'events' array (3 or more consecutive frame groups)
   - save an in-memory list of images with higher than avg > max px in the bg subtracted frame 
   - run the in-memory frames through the motion detector / object identifier
   - save max px and moving object results. 
   - AFTER THIS PROCESS COMPLETES we will still need to:
      - run AI detects on the moving objects & detected stack img objects 
      - from these determine if the minute file contains 1 or more 'high confidence meteors' (HCM)
      - for each HCM -- validate and export the meteor (everything to reduce it, get it in the admin and uploaded to the cloud! 100% meteor injest)


"""

from stack_fast import stack_only, get_patch_objects_in_stack, get_stars_in_stack
import sqlite3
import json
from PIL import ImageFont, ImageDraw, Image, ImageChops
import os
import numpy as np 
import sys
from time import time
from Classes.ASAI import AllSkyAI
import cv2
ASAI = AllSkyAI()
ASAI.load_all_models()
from get_contours import get_contours
from collections import deque
from Classes.Detector import Detector
import socket
DD = Detector()

from Lib.Utils import save_json_file, load_json_file 
#from lib.PipeUtil import save_json_file, load_json_file 

LEARNING_DIR = "F:/AI/DATASETS/MinFiles/"
WEATHER_LEARNING_DIR = "F:/AI/DATASETS/MinFiles/"

def ai_client_program(roi_file=None):
   """ DELETE OUT OF HERE / MOVE???"""

   # connect to the local AI Program and run detection on input image
   host = socket.gethostname()  # as both code is running on same pc
   port = 5000  # socket server port number

   client_socket = socket.socket()  # instantiate
   client_socket.connect((host, port))  # connect to the server


   message = roi_file
   print("Send to AI server:", message)
   client_socket.send(message.encode())  # send message
   data = client_socket.recv(1024).decode()  # receive response

   print('Received from server: ' + data)  # show in terminal
   client_socket.close()  # close the connection
   data = json.loads(data)
   stars = data['stars']
   non_stars = data['non_stars']
   weather_condition = data['weather_condition']
   return(stars,non_stars, weather_condition)

def track_objects(saved_frames, first_frame, blank_image, stack_image):
   objects = {}
   for fn in saved_frames:
      show_frame = saved_frames[fn].copy()
      sub_frame = cv2.subtract(saved_frames[fn], first_frame)
      sub_frame = cv2.subtract(sub_frame, blank_image)
      gray = cv2.cvtColor(sub_frame, cv2.COLOR_BGR2GRAY)
      _, thresh_img = cv2.threshold(gray, 15, 255, cv2.THRESH_BINARY)


      obj_cnts = get_contours(thresh_img)
      for x,y,w,h,intensity in obj_cnts:
         cv2.rectangle(thresh_img, (x,y), (x+w, y+h) , (128, 128, 128), 1)
         cx = x + (w/2)
         cy = y + (h/2)
         oid, objects = Detector.find_objects(fn,x,y,w,h,cx,cy,intensity,objects, 50)
      #cv2.imshow('main', thresh_img)
      #cv2.waitKey(30)
   good_objs = {}
   bad_objs = {}
   for obj_id in objects:
      if len(objects[obj_id]['ofns']) >= 3:
         status, report = Detector.analyze_object(objects[obj_id])
         print("METEOR SCORE:", report['meteor_score'])

         # make roi image from stack
         x = min(objects[obj_id]['oxs'])
         y = min(objects[obj_id]['oys'])
         w = max(objects[obj_id]['oxs']) - min(objects[obj_id]['oxs'])
         h = max(objects[obj_id]['oys']) - min(objects[obj_id]['oys'])
         
         x1,y1,x2,y2, roi_img_1080p_224 = make_roi_img(x,y,w,h,224,stacked_image,thresh_img,(1920,1080))
         resp = ASAI.meteor_yn("temp.jpg", None, roi_img_1080p_224)   
         objects[obj_id]['mc_class'] = resp['mc_class']
         objects[obj_id]['mc_class_confidence'] = resp['mc_class_confidence']
         objects[obj_id]['meteor_yn'] = resp['meteor_yn_confidence']
         objects[obj_id]['meteor_fireball_yn'] = resp['meteor_fireball_yn_confidence']
         if report['meteor_score'] > 0:
            good_objs[obj_id] = objects[obj_id]
            good_objs[obj_id]['report'] = report
         else:
            bad_objs[obj_id] = objects[obj_id]
            bad_objs[obj_id]['report'] = report
   print("GOOD OBJS:", len(good_objs.keys()))
   return(good_objs, bad_objs)

def make_roi_img(x,y,w,h,roi_size,image,thresh_img, roi_src_image_size):

   """ DELETE OUT OF HERE / MOVE???"""
   cx = int(x + (w/2))
   cy = int(y + (h/2))
   new_w, new_h = roi_src_image_size
   org_h, org_w = image.shape[:2]
   hdm_x = new_w / org_w 
   hdm_y = new_h / org_h
   new_img = cv2.resize(image,(new_w,new_h))

   blank_image = np.zeros((new_h,new_w),dtype=np.uint8)
   blank_image[:] = 255
   gray = cv2.cvtColor(new_img, cv2.COLOR_BGR2GRAY)
   if len(thresh_img.shape) == 3:
      thresh_gray = cv2.cvtColor(thresh_img, cv2.COLOR_BGR2GRAY)
   else:
      thresh_gray = thresh_img
   hd_x = (cx * hdm_x)
   hd_y = (cy * hdm_y)


   x1 = int(hd_x - (roi_size / 2))
   y1 = int(hd_y - (roi_size / 2))
   x2 = int(hd_x + (roi_size / 2))
   y2 = int(hd_y + (roi_size / 2))

   if x1 < 0:
      x1 = 0 
      x2 = roi_size
   if y1 < 0:
      y1 = 0 
      y2 = roi_size
   if x2 >= new_w:
      x2 = new_w - 1 
      x1 = new_w - 1 - roi_size 
   if y2 > new_h:
      y2 = new_h - 1
      y1 = new_h - 1 - roi_size

   blank_image[y1:y2,x1:x2] = 0
   temp_img = cv2.subtract(gray, blank_image)
   thresh_gray = cv2.resize(thresh_gray,(gray.shape[1], gray.shape[0]))
   temp_img = cv2.subtract(gray, thresh_gray)

   min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(temp_img)       

   #cv2.rectangle(temp_img, (x1,y1), (x2, y2) , (0, 0, 0), 1)
   #cv2.imshow('main', temp_img)
   #cv2.waitKey(30)

   #x1 = int(mx - (roi_size / 2))
   #y1 = int(my - (roi_size / 2))
   #x2 = int(mx + (roi_size / 2))
   #y2 = int(my + (roi_size / 2))

   if x1 < 0:
      x1 = 0 
      x2 = roi_size
   if y1 < 0:
      y1 = 0 
      y2 = roi_size
   if x2 >= new_w:
      x2 = new_w - 1 
      x1 = new_w - 1 - roi_size 
   if y2 > new_h:
      y2 = new_h - 1
      y1 = new_h - 1 - roi_size

   #cv2.rectangle(new_img, (x1,y1), (x2, y2) , (0, 0, 0), 1)
   #cv2.imshow('main', new_img)
   #cv2.waitKey(30)

   roi_img = new_img[y1:y2,x1:x2] 

   return(x1,y1,x2,y2,roi_img)


def analyze_max_pxs(max_pxs):
   max_px = np.max(max_pxs)
   avg_px = np.mean(max_pxs)
   norm_pxs = []
   cm = 0
   last_mx = 0
   event = []
   events = []
   cms = []
   ec = 0
   fn = 0
   for mx in max_pxs:
      aa = mx - avg_px * 2
      if aa < 0:
         mx = 0
      if mx > 0:
         cm += 1
         if cm >= 3:
            if len(event) == 0:
               event.append(fn-2)
               event.append(fn-1)
               event.append(fn)
            else:
               event.append(fn)
      else:
         cm = 0 
         if len(event) >= 3:
            events.append(event)
         event = []
      cms.append(cm)
      fn += 1
      last_mx = mx
      norm_pxs.append(mx)
   
   return(events)

# MAIN PROGRAM HERE

vdir = sys.argv[1]
t_cam_id = sys.argv[2]
cv2.namedWindow('main')
tfiles = os.listdir(vdir)

if "\\" in vdir:
   vdir = vdir.replace("\\", "/")
date = vdir.split("/")[-1]
if date == "":
   date = vdir.split("/")[-2]
#tfiles = ['2022_03_05_09_01_01_000_010006.mp4']

"""
   for each minute file we want the following things:

   - stack.jpg 
   - first_frame.jpg 
   - json file containing
      - max vals array
      - stars
      - non_stars
      - objects

"""
data_dir = "Z:/"
db_dir = data_dir + "/DBS/"
db_file = db_dir + date + "_minfiles.db"

if os.path.exists(db_dir) is False:
   os.makedirs(db_dir)

sqlite3.connect(db_file)
db_con = sqlite3.connect(db_file)
db_con.row_factory = sqlite3.Row
db_cur = db_con.cursor()

# test_init_db 

blends = {} 
blend_files = deque(maxlen=10)
last_blend = None

mp4s = []

# load_min_files

# stack_min_files

# scan_min_frames

# scan_min_stack

for vfile in tfiles:
   if "trim" in vfile:
      continue
   if "mp4" not in vfile:
      continue
   if t_cam_id != "ALL" and t_cam_id not in vfile:
      continue 
   mp4s.append(vfile)
   
wc = 0
for tfile in sorted(mp4s):
   data = {}
   data['min_file'] = tfile
   vfile = vdir + tfile
   json_file = tfile.replace(".mp4", "-ai.json")

   if "trim" in vfile:
      print("Skip trim")
      continue
   if "mp4" not in vfile:
      print("Skip not mp4")
      continue
   if t_cam_id != "ALL" and t_cam_id not in vfile:
      print("Skip non matching cam")
      continue 
   print("LOG:", tfile, wc, len(mp4s))
   wc += 1
   jfile = vfile.replace(".mp4", "-stacked.jpg")
   stack_file = tfile.replace(".mp4", "-stacked.jpg")

   # THE IMAGE HAS BEEN STACKED AND MOTION FRAMES ANALYZED ALREADY, BUT WE MIGHT NEED TO DO THE REST OF THE AI CONFIRM AND METEOR FOLLOW UP STILL 
   # CONSIDER THIS THE MIN-FOLLOW-UP WORK

   if os.path.exists(vdir + json_file) is True and os.path.exists(vdir + stack_file) is True :
      # The stack is already done, now check the AI and display picture -- do each if needed!
      # else just show the results / save the result frame!

      """ continue for now, later remove / move this code block to the ai-object-detector """ 
      continue

      try:
         data = load_json_file(vdir + json_file)
      except:
         data = {}
      clean_img = cv2.imread(vdir + stack_file)

      clean_img = cv2.resize(clean_img, (640,360))
      print(vdir + tfile)

      if len(data['meteor_objs']) > 0:
         print("Motion Meteor")
         #input("Pause for motion meteor!")

      #if "non_stars" in data:
      done = False
      if "non_stars" in data:
         if len(data['non_stars']) > 0:
            if len(data['non_stars'][0]) == 8:
               done = True

      if done is True:
         for row in data['non_stars']:
            print(row)
            if len(row) == 8:
               x1,y1,x2,y2,label,conf,meteor_yn_conf,fireball_yn_conf = row
            #else:
            #   x1,y1,x2,y2,label,conf = row
            print("NON STAR ROW", row)
            if label == "meteor" and len(data['meteor_objs']) == 0:
               print("Don't pause for this AI Detected Stack meteor")
            elif len(data['meteor_objs']) > 0:
               print("Wow! Motion meteor AND AI Stack meteor in the same frame!")
               #input("Pause...")
            else:
               print("Nothing worth pausing for...")
      else:
         print("Need to run AI still for this data!")
         stars, non_stars,weather_condition = ai_client_program(vdir + stack_file)
         data['stars'] = stars
         data['non_stars'] = non_stars
         data['weather_condition'] = weather_condition
         print("SAVING:", vdir, json_file)
         save_json_file(vdir + json_file, data)

      marked_img, data = ASAI.render_minfile(vdir + tfile)
      meteor_found = False
      for row in data['non_stars']:
         x1,y1,x2,y2,mc_class,mc_conf,meteor_yn_conf,meteor_fb_conf = row
         if "meteor" in mc_class:
            meteor_found = True

      #if last_blend is not None:
      if False:
         blend = cv2.addWeighted(clean_img, .5, marked_img, .5, .3)
         lblend = cv2.addWeighted(blend, .5, last_blend, .5, .3)
         show_pic = cv2.resize(lblend, (1280,720))
         cv2.imshow('main', show_pic)
         cv2.waitKey(30)
      else:
         blend = cv2.addWeighted(clean_img, .5, marked_img, .5, .3)
         show_pic = cv2.resize(blend, (1280,720))

         if meteor_found is True:
            cv2.imshow('main', show_pic)
            cv2.waitKey(30)
         else:
            cv2.imshow('main', show_pic)
            cv2.waitKey(30)
      last_blend = blend

      continue
      # END FOLLOWUP BELOW HERE IS THE FIRST MIN STACK

   if os.path.exists(vdir + json_file) is True:
      print("missing:", vdir + json_file)
   if os.path.exists(vdir + stack_file) is True :
      print("missing:", vdir + stack_file)

   if os.path.exists(jfile) is True:
      foo = 1

   cam_id = vfile.split("_")[-1].replace(".mp4", "")
   station_id = "AMS1"
   mask_img = np.zeros((1080,1920,3),dtype=np.uint8)

   t = time()
   print("Stacking...")
   stacked_image, first_frame, max_pxs, saved_frames, total_frames = stack_only(vfile, mask_img )

   e = time() - t 
   print("STACKED ({:s}/{:s}) {:s} {:s} FRAMES in {:s} SECONDS.".format(str(wc), str(len(mp4s)), vfile, str(total_frames), str(round(e,2))))
   data['sd_total_frames'] = total_frames
   data['stack_time'] = round(e,2)
 
   if False:
      # WEATHER
      # lets get a weather status first!
      weather_snap = first_frame[50:274,100:324]
      learning_fn = tfile.replace(".mp4", "minsnap_50_224_100_324.jpg")
      weather_condition_class, weather_condition_conf = ASAI.weather_predict(None, weather_snap)
      weather_desc = weather_condition_class + " " + str(round(weather_condition_conf,2)) + "%"
      data['weather_condition'] = [weather_condition_class, weather_condition_conf]
      print("WEATHER:", weather_condition_class, weather_condition_conf)

      # THIS NEEDS TO MOVE INTO THE ASAI CLASS
      wdir = WEATHER_LEARNING_DIR + weather_condition_class + "/"
      if os.path.exists(wdir) is False:
         os.makedirs(wdir)
      if os.path.exists(wdir + learning_fn) is False:
         os.rename(learning_fn, wdir + learning_fn )
      else:
         os.remove(learning_fn)

   # CHECK MOTION IN SAVED FRAMES 

   # DILATE the FIRST FRAME SO WE CAN USE IT AS A MASK!
   first_frame = cv2.dilate(first_frame, None, iterations=4)
   first_frame = cv2.dilate(first_frame, None, iterations=4)
   first_frame = cv2.GaussianBlur(first_frame, (7, 7), 0)
   stacked_sub_image = cv2.subtract(stacked_image, first_frame)


   if cam_id not in blends:
      blends[cam_id] = stacked_sub_image
   else:
      temp = blends[cam_id].copy()
      temp = cv2.dilate(temp, None, iterations=4)
      temp = cv2.dilate(temp, None, iterations=4)

      blend_files.append(temp)

      _, thresh_img = cv2.threshold(temp, 15, 255, cv2.THRESH_BINARY)
       
      stacked_sub_image = cv2.subtract(stacked_sub_image, thresh_img)

   # Determine if motion events worth looking at based on the max pixel array
   events = analyze_max_pxs(max_pxs)
   data['max_pxs'] = max_pxs 
   data['events'] = events
   stack_file = vfile.replace(".mp4", "-stacked.jpg")

   # GET MOVING OBJECTS!
   # tracked objs will only contain those with meteor score > 0 
   # if there are no objs there are no meteors!

   # this is the dynamic mask to subtract from each frame to remove moon, stars and ground lights
   blank_image = first_frame

   if len(events) > 0:
      #input("before track objects")
      meteor_objs, non_meteor_objs = track_objects(saved_frames, first_frame, blank_image, stacked_image)
      #input("after track objects")
   else:
      meteor_objs = {}
      non_meteor_objs = {}

   data['meteor_objs'] = meteor_objs
   data['non_meteor_objs'] = non_meteor_objs
   if len(meteor_objs) > 0:
      print("MOVING METEOR OBJECT FOUND!?")
   SHOW = 0
   show_stacked_image = stacked_image.copy()


   data['saved_frames'] = []
   for key in sorted(saved_frames.keys()):
      data['saved_frames'].append(key)

   save_json_file(vdir + json_file, data)
   print("Saving:", vdir + json_file)

   # END HERE FOR STACK ONLY!
   # AT THIS POINT WE CAN SAVE EVERYTHING AFTER HERE SHOULD HAPPEN INSIDE THE AI SERVER STACK-IMAGE REQUEST 
   # 1-STACK-IMAGE, 1-FIRST FRAME - then get back all AI results!
   continue 

   if len(events) > 0:
      blank_image = np.zeros((stacked_image.shape[0],stacked_image.shape[1],3),dtype=np.uint8)
      blank_image[:] = 255
      for x1,y1,x2,y2,obj,conf in non_stars:
         blank_image[y1:y2,x1:x2] = 0


   if SHOW == 1:

      if len(meteor_objs.keys()) == 1:
         label_desc = str(len(meteor_objs.keys())) + " meteor "
      else:
         label_desc = str(len(meteor_objs.keys())) + " meteors "
      label_desc2 = str(len(non_meteor_objs.keys())) + " non meteors "

      cv2.putText(show_stacked_image, "Weather Condition: " + weather_desc,  (5,15), cv2.FONT_HERSHEY_SIMPLEX, .4, (128,128,128), 1)
      cv2.putText(show_stacked_image, "Moving Objects",  (5,35), cv2.FONT_HERSHEY_SIMPLEX, .4, (128,128,128), 1)
      cv2.putText(show_stacked_image, label_desc,  (5,55), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,255,0), 1)
      cv2.putText(show_stacked_image, label_desc2,  (5,75), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,0,255), 1)
      for obj_id in meteor_objs:
         obj = meteor_objs[obj_id]
         x = obj['oxs'][0]
         y = obj['oys'][0]
         
         ax = int(np.mean(obj['oxs']))
         ay = int(np.mean(obj['oys']))

         x1,y1,x2,y2,roi_img_1080p_224 = make_roi_img(ax,ay,1,1,224,stacked_image,thresh_mask,(1920,1080))
         roi_file = "_1080p_224_" + str(x1) + "_" + str(y1) + "_" + str(x2) + "_" + str(y2) 
         resp = ASAI.meteor_yn(tfile, None, roi_img_1080p_224)   

         cv2.putText(show_stacked_image, "meteor" ,  (x,y), cv2.FONT_HERSHEY_SIMPLEX, .6, (0,255,0), 1)
         meteor_objs[obj_id]['ai'] = resp

      for obj_id in non_meteor_objs:
         obj = non_meteor_objs[obj_id]
         x = obj['oxs'][0]
         y = obj['oys'][0]
         cv2.putText(show_stacked_image, "non-meteor" ,  (x,y), cv2.FONT_HERSHEY_SIMPLEX, .6, (0,0,255), 1)

   # here we should check the meteor and non-meteor moving objects and run them through the AI detect if they have not already been
   # MOVING OBJECTS AI



   # get stars and non-stars from stack image
   if True:
      try:
         #stars, non_stars, resp_image = get_stars_in_stack(stack_file, stacked_image, first_frame, ASAI)
         print("STARS:", stars)

         stars, non_stars,weather_condition = ai_client_program(stack_file)

      except:
         print("Failure to get stars / tensor flow!", stack_file)
         exit()
         continue 
      data['stars'] = stars
      data['non_stars'] = non_stars

   e = time() - t 
   print("Time up to get stars in stack", e) 

   # extract objects out of the stack 
   # SHOULD THIS HAPPEN INSIDE THE AI SERVER????

   dil_img = cv2.dilate(stacked_sub_image, None, iterations=4)
   dil_img = cv2.dilate(dil_img, None, iterations=4)
   dil_img = cv2.dilate(dil_img, None, iterations=4)
   dil_img = cv2.dilate(dil_img, None, iterations=4)
   _, thresh_img = cv2.threshold(dil_img.copy(), 15, 255, cv2.THRESH_BINARY)
   thresh_mask = ~thresh_img 
   show_stack_main = stacked_image.copy()
   if len(blend_files) > 3:
      blend_avg = cv2.convertScaleAbs(np.median(np.array(blend_files), axis=0))
      thresh_img = cv2.subtract(thresh_img, blend_avg)
   obj_cnts = get_contours(thresh_img)
   data['obj_cnts'] = [] 
   show_stack = stacked_sub_image.copy()
   learning_images = []
   if len(obj_cnts) > 0:
      for x,y,w,h,intensity in obj_cnts:

         cv2.rectangle(show_stacked_image, (x,y), (x+w, y+h) , (255, 255, 255), 1)
         cv2.rectangle(show_stack, (x,y), (x+w, y+h) , (255, 255, 255), 1)
         x1,y1,x2,y2, roi_img_1080p_224 = make_roi_img(x,y,w,h,224,stacked_image,thresh_mask,(1920,1080))
         roi_file = "_1080p_224_" + str(x1) + "_" + str(y1) + "_" + str(x2) + "_" + str(y2) 

         resp = ASAI.meteor_yn(tfile, None, roi_img_1080p_224)   

         cv2.imwrite("temp.jpg", roi_img_1080p_224, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
         resp = json.loads(resp)
         print("RESP!", resp)
         resp['cnt'] = [x,y,w,h,intensity]
         label = resp['mc_class']
         label_conf = resp['mc_class_confidence']
         label_desc = label + " " + str(round(label_conf,2)) + "%"
         if y < 100:
            cv2.putText(show_stacked_image, label_desc,  (x,y+h), cv2.FONT_HERSHEY_SIMPLEX, .8, (128,128,128), 1)
         else:
            cv2.putText(show_stacked_image, label_desc,  (x,y), cv2.FONT_HERSHEY_SIMPLEX, .8, (128,128,128), 1)
         if label_conf > 90:
            conf_dir = "high"
         elif conf_dir < 70:
            conf_dir = "low"
         else:
            conf_dir = "med"
         save_dir = LEARNING_DIR + conf_dir + "/" + label + "/" 
         obj_data = {}
         obj_data['cnt'] = [x,y,w,h,intensity]
         obj_data['mc_class'] = resp['mc_class']
         obj_data['mc_class_conf'] = float(round(resp['mc_class_confidence'],2))
         obj_data['meteor_yn'] = float(round(resp['meteor_yn_confidence'],2))
         obj_data['meteor_fireball_yn'] = float(round(resp['meteor_fireball_yn_confidence'],2))
 
         data['obj_cnts'].append(obj_data) 

         if os.path.exists(save_dir) is False:
            os.makedirs(save_dir)
         
         save_file = tfile.replace(".mp4", roi_file + ".jpg")

         learning_images.append((resp['mc_class'], resp['mc_class_confidence'], save_dir + save_file , roi_img_1080p_224))
         cv2.imwrite(save_dir + save_file , roi_img_1080p_224, [int(cv2.IMWRITE_JPEG_QUALITY), 70])

   if SHOW == 1:
      cv2.imshow('main', show_stacked_image)
      if "meteor" in resp['mc_class'] :
         cv2.waitKey(0)
      else:
         cv2.waitKey(30)

   
   _, stacked_sub_image = cv2.threshold(stacked_sub_image, 15, 255, cv2.THRESH_BINARY)
   blends[cam_id] = cv2.addWeighted(stacked_sub_image, .8, blends[cam_id], .2, .3)

   
      
   data['saved_frames'] = []
   for key in sorted(saved_frames.keys()):
      data['saved_frames'].append(key)

   save_json_file(vdir + json_file, data)
   obj_file = json_file.replace("-ai.json", "-obj.jpg")
   cv2.imwrite(vdir + obj_file, show_stack)


   for row in learning_images:
      print(row[0], row[1])

   #input("Waiting...")

   # DECISIONS AND SAVING!
   # only save the learning sample WHEN:
   # confidence is high > 99% --
   # Low confidence detects go to low conf dir!
   # meter detects -- if there is no motion it is false
   # meteor motion -- if motion exists but no AI detect then what!?
   e = time() - t 
   print("FULL TIME:", e)


