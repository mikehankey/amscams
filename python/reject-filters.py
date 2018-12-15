#!/usr/bin/python3 

import math
from pathlib import Path
import os
import glob
import json
import cv2
import sys
import subprocess
import numpy as np


json_file = open('../conf/as6.json')
json_str = json_file.read()
json_conf = json.loads(json_str)
proc_dir = json_conf['site']['proc_dir']


def calc_dist(p1,p2):
   x1,y1 = p1
   x2,y2 = p2
   dist = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
   return dist


def find_slope(p1,p2):
   (x1,y1) = p1
   (x2,y2) = p2
   top = y2 - y1
   bottom = x2 - y2
   if bottom > 0:
      slope = top / bottom
   else:
      slope = "na"
   #print(x1,y1,x2,y2,slope)
   return(slope)


def new_obj_id(pt, moving_objects):
   x,y = pt
   #print ("<BR> MOVING OBJS : ", moving_objects)
   #np_mo = np.array([[[1],[44],[55],[1,44,55]],[[2],[33],[22],[2,33,22]]])
   max_id = np.max(moving_objects, axis=0)
   #print ("MAX:", max_id)
   new_id = max_id[0][0] + 1
   #print ("MAX ID IS : ", max_id)
   #print ("NEW ID IS : ", new_id)
   return(new_id)


def check_hist(x,y,hist):
   #print("<HR>LEN HIST: ", len(hist), "<HR>")
   for (fn,hx,hy) in hist:
      if hx - 20 <= x <= hx + 20 and hy - 20 <= y <= hy +20:
         return(1)
   return(0)


def get_frame_data(frame_data_file):
   print(frame_data_file)
   fdf = open(frame_data_file)
   d = {}
   code = "frame_data = "
   for line in fdf:
      code = code + line
   exec (code,  d)

   return(d['frame_data'])


def object_report (trim_file, frame_data):
   fc =1
   tfc =1
   moving_objects = None
   found_objects = []
   for fd in frame_data:
      print (str(fd[0]) + "," + str(fd[1]) + "," )

      fd_temp = sorted(fd[2], key=lambda x: x[3], reverse=True)
      if len(fd_temp) > 0 and len(fd_temp) < 8:
         for x,y,w,h in fd_temp:
            object, moving_objects = find_object(tfc, (x,y), moving_objects)
      fc = fc + 1
      tfc = tfc + 1
   try: 
      if moving_objects is None:
         moving_objects = []
   except:
      moving_objects = []
 

   for object in moving_objects:
      status = []
      hist = object[3]
      first = hist[0]
      last = hist[-1]
      p1 = first[1], first[2]
      p2 = last[1], last[2]
      hist_len = len(object[3]) - 1
      elp_frms = last[0] - first[0]


      if elp_frms > 0:
         len_test = hist_len / elp_frms
      else:
         len_test = 0

      if hist_len > 3:
         slope = find_slope(p1,p2)
         dist = calc_dist(p1,p2)
      else:
         slope = "na"
         dist = 0
      if elp_frms > 0 and dist != "na":
         px_per_frame =dist / elp_frms
      else:
         px_per_frame = 0
      if len_test < .8:
         status.append(('reject', 'object flickers like a plane.'))
      if elp_frms > 200:
         status.append(('reject', 'object exists for too long to be a meteor.'))
      if px_per_frame < 1:
         status.append(('reject', 'object does not move fast enough to be a meteor.'))
      if dist < 5:
         status.append(('reject', 'object does not move far enough to be a meteor.'))
      if hist_len < 3:
         status.append(('reject', 'object does not exist long enough.'))
      # (frame_num, count, first_frame, last_frame, slope, distance, elapsed_frames, px_per_frames, status)
      obj_data = (object[0],  hist_len,  first, last,  slope, dist,  elp_frms,  px_per_frame,  status)
      found_objects.append(obj_data) 
   return(found_objects)



def find_object(fn, pt, moving_objects):
   x,y = pt
   prox_match = 0
   if moving_objects is None:
      lenstr = "0"
   else:
      lenstr = str(len(moving_objects))

   print ("<h4>Current Known Objects that could match x,y " + str(x) + "," + str(y) + " " + lenstr + "</h4>")
   if moving_objects is None:
      # there are no objects yet, so just add this one and return.
      oid = 0
      mo = []
      moving_objects = np.array([ [[oid],[x],[y],[[fn,x,y],[fn,x,y]] ]])
      #print("NP SIZE & SHAPE:", np.size(moving_objects,0),np.size(moving_objects,1))
      return(oid, moving_objects)
   else:
      # match based on proximity to pixel history of each object
      #print("NP SIZE & SHAPE:", np.size(moving_objects,0),np.size(moving_objects,1))
      #print("MOVING OBJECTS:", moving_objects[0])
      rowc = 0
      match_id = None
      for (oid,ox,oy,hist) in moving_objects:
         found_in_hist = check_hist(x,y,hist)
         #print("<BR>FOUND IN HIST?" , found_in_hist, "<BR>")
         if found_in_hist == 1:
            prox_match = 1
            match_id = oid

   #can't find match so make new one
   if prox_match == 0:
      oid = new_obj_id((x,y), moving_objects)
      moving_objects = np.append(moving_objects, [ [[oid],[x],[y],[[fn,x,y],[fn,x,y]]] ], axis=0)
   else:
      oid,ox,oy,hist = moving_objects[match_id][0]
      hist.append([fn,x,y])
      moving_objects[match_id][0] = [ [[oid],[ox],[oy],[hist]] ]

   return(oid, moving_objects)


def check_running():
   cmd = "ps -aux |grep \"reject-filters.py\" | grep -v grep | wc -l"
   output = subprocess.check_output(cmd, shell=True).decode("utf-8")
   print(output)
   output = int(output.replace("\n", ""))
   
   return(output)


def check_for_motion(frames, video_file):
   #cv2.namedWindow('pepe')
   # find trim number
   el = video_file.split("/") 
   fn = el[-1]
   st = fn.split("trim")
   trim_num = st[1][0]
   print("TRIM NUM: ", trim_num)
   #median_image = np.median(np.array(frames), axis=0)
   frame_file_base = video_file.replace(".mp4", "")
   frame_data = []
   last_frame = None
   image_acc = None
   frame_count = 1
   good_cnts = [] 
   max_cons_motion = 0
   cons_motion = 0

   for frame in frames:
      data_str = []
      data_str.append(trim_num) 
      data_str.append(frame_count) 
      nice_frame = frame.copy()
      if len(frame.shape) == 3:
         frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
      gray_frame = frame
      frame_file = frame_file_base + "-fr" + str(frame_count) + ".png"
      frame[440:480, 0:360] = 0

      frame = cv2.GaussianBlur(frame, (7, 7), 0)

      # setup image accumulation
      if last_frame is None:
         last_frame = frame
      if image_acc is None:
         image_acc = np.empty(np.shape(frame))

      image_diff = cv2.absdiff(image_acc.astype(frame.dtype), frame,)
      alpha = .4
      hello = cv2.accumulateWeighted(frame, image_acc, alpha)
      _, threshold = cv2.threshold(image_diff, 5, 255, cv2.THRESH_BINARY)
      thresh= cv2.dilate(threshold, None , iterations=4)
      (_, cnts, xx) = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
      good_cnts = []
      cnt_cnt = 0
      for (i,c) in enumerate(cnts):
         bad_cnt = 0
         x,y,w,h = cv2.boundingRect(cnts[i])
         if w <= 1 and h <= 1:
            bad_cnt = 1
         if w >= 630 or h >= 400:
            bad_cnt = 1
         if bad_cnt == 0:
            x2 = x + w
            y2 = y + h
            print("IMG: ", y,y2,x,x2)
            cnt_img = gray_frame[y:y2,x:x2]            
            flux_status = test_cnt_flux(cnt_img)
            cv2.imwrite("/mnt/ams2/tests/cnt" + str(frame_count) + "-" + str(cnt_cnt) + ".png", cnt_img)


            #print("CNTS: ", frame_count, x,y,w,h)
            good_cnts.append((x,y,w,h)) 
            cv2.rectangle(nice_frame, (x, y), (x + w, y + w), (255, 0, 0), 2)
            cnt_cnt = cnt_cnt + 1
      if len(good_cnts) > 10:
         print ("NOISE!", frame_count, len(good_cnts))
         #noisy cnt group don't count it. 
         good_cnts = []
      #cv2.imwrite(frame_file, nice_frame)
      #frame_file_tn = frame_file.replace(".png", "-tn.png")
      #thumbnail = cv2.resize(nice_frame, (0,0), fx=0.5, fy=0.5)
      #cv2.imwrite(frame_file_tn, thumbnail)

      data_str.append(good_cnts)
      data_str.append(cons_motion)
      frame_data.append(data_str)   
      if cons_motion > max_cons_motion:
         max_cons_motion = cons_motion
      if len(good_cnts) >= 1:
         cons_motion = cons_motion + 1
         #print ("CNT: ", frame_count, x,y,w,h,cons_motion)
      else:
         cons_motion = 0
      frame_count = frame_count + 1
      #cv2.imshow('pepe', frame)
      #cv2.waitKey(1)
      print(frame_count, len(good_cnts), cons_motion)
   return(max_cons_motion, frame_data)


def test_cnt_flux(cnt_img):
   img_min = cnt_img.min()
   img_max = cnt_img.max()
   print("TEST Countour Flux, should be light in center and dark on edges all around.", img_min,img_max)
   lc = cnt_img[0,0]
   brc = cnt_img[-1,-1]
   rc = cnt_img[0,-1]
   blc = cnt_img[-1,0]
   print("4 CORNERS:", lc, brc, rc, blc)

def load_video_frames(trim_file):
   cap = cv2.VideoCapture(trim_file)

   frames = []
   frame_count = 0
   go = 1
   while go == 1:
      _ , frame = cap.read()
      if frame is None:
         if frame_count <= 1:
            cap.release()
            print("Bad file.")
            return(frames)
         else:
            go = 0
      else:
         if len(frame.shape) == 3:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
         frames.append(frame)
         frame_count = frame_count + 1
   return(frames)

def confirm_motion(trim_file,frame_data): 
   fel = trim_file.split("-trim")
   base_file = fel[0]
   main_confirm_file = base_file + "-confirm.txt"
 
   confirm_file = trim_file.replace(".mp4",  "-confirm.txt")
   print ("CONFIRMED:", confirm_file)
   out = open(confirm_file, "w")
   out.write(str(frame_data))
   out.close() 
   out = open(main_confirm_file, "w")
   out.write(str(frame_data))
   out.close() 

def move_rejects(trim_file, frame_data):
   proc_dir = json_conf['site']['proc_dir']

   fel = trim_file.split("-trim")
   base_file = fel[0]
   motion_file = base_file + "-motion.txt"

   reject_file = trim_file + "-rejected.txt"
   out = open(reject_file, "w")
   out.write(str(frame_data))
   out.close() 


 
   cmd = "mv " + motion_file + " " + proc_dir + "rejects/"
   print(cmd)
#   os.system(cmd)
   cmd = "mv " + trim_file + " " + proc_dir + "rejects/"
#   os.system(cmd)
   print(cmd)

def check_frame_rate(trim_file):
   cmd = "/usr/bin/ffprobe " + trim_file + ">checks.txt 2>&1"
   print(cmd)
   output = subprocess.check_output(cmd, shell=True).decode("utf-8")
   efp = open("checks.txt")
   #Stream #0:0(und): Video: h264 (Main) (avc1 / 0x31637661), yuvj420p(pc, bt709), 640x480, 649 kb/s, 18.66 fps, 25 tbr, 90k tbn, 180k tbc (default)
   stream_found = 0
   try:
      for line in efp:
         if "Stream" in line:
            el = line.split(",")
            fps = el[5]
            fps = fps.replace(" fps", "")
            fps = fps.replace(" ", "")
            stream_found = 1
      if stream_found == 0:
         fps = 0
      print(fps)
   except:
      fps = 0
   return(fps)

def apply_reject_filters(trim_file):
   frames = []
   print ("Apply reject filters for : ", trim_file)
   el = trim_file.split("/")
   fn = el[-1]
   base_dir = trim_file.replace(fn,"")
   confirm_file = base_dir + "/data/" + fn
   confirm_file = confirm_file.replace(".mp4", "-confirm.txt")
   meteor_file = confirm_file.replace("-confirm.txt", "-meteor.txt")
   obj_fail = confirm_file.replace("-confirm.txt", "-objfail.txt")

   el = trim_file.split("-trim")
   mf = el[0]
   clip_file = mf + ".mp4"

   motion_file = clip_file.replace(".mp4", "-motion.txt")
   el = motion_file.split("/")
   fn = el[-1]
   base = motion_file.replace(fn, "")
   new_motion_file = base + "/data/"  + fn
   



   file_exists = Path(confirm_file)
   if (file_exists.is_file() is True):
      print("DONE ALREADY!")
      #return()

  
   trim_fps = check_frame_rate(trim_file)
   clip_fps = check_frame_rate(clip_file)
   print ("Trim FPS: ", trim_fps)
   print ("Clip FPS: ", clip_fps)
   meteor_found = 0
   if int(float(trim_fps)) >= 20: 
      frames = load_video_frames(trim_file)


      if len(frames) > 5:
         max_cons_motion, frame_data = check_for_motion(frames, trim_file)
         print ("Max Cons Motion: ", max_cons_motion)

         found_objects = object_report(trim_file, frame_data)
         print ("FOUND:", found_objects)
         for obj in found_objects:
            (frame_num, count, first_frame, last_frame, slope, distance, elapsed_frames, px_per_frames, status) = obj
            print(status, len(status))
            if len(status) == 0:
               meteor_found = 1
               print ("METEOR FOUND.")

         if meteor_found == 1: 
            print ("METEOR")
            print (meteor_file)
            mt = open(meteor_file, "w")
            mt.write(str(found_objects))
            mt.close()
         else:
            print ("NO METEOR")
            print (obj_fail)
            mt = open(obj_fail, "w")
            mt.write(str(found_objects))
            mt.close()

      else:
         max_cons_motion = 0
         reject_reason = "no frames/bad file."
   else:
      print("SKIPPING FOR LOW FPS")
      frame_data = []
      max_cons_motion = 0
   if (max_cons_motion < 3) :
       print ("REJECTED not enough consectutive motion...")
       move_rejects(trim_file, frame_data)
   else:
       print ("PASSED")
       confirm_motion(trim_file, frame_data)
      
   # move motion file to data dir
   cmd = "mv " + motion_file + " " + new_motion_file
   os.system(cmd)

def do_batch():
   for filename in (glob.glob(proc_dir + "/*")):
      if 'daytime' not in filename and 'rejects' not in filename:
         scan_dir(filename)

def scan_dir(dir):
   for filename in (glob.glob(dir + '/*trim*.mp4')):   
      print(filename)
      apply_reject_filters(filename)


running = check_running()
if running > 3:
   print(running)
   print ("Already running.")
   exit()

cmd = sys.argv[1]

#apply_reject_filters(trim_file)

if cmd == 'do_batch':
   do_batch()
if cmd == 'scan_dir':
   file = sys.argv[2]
   scan_dir(file)
if cmd == 'scan_file':
   file = sys.argv[2]
   apply_reject_filters(file)
if cmd == 'motion_check':

   file = sys.argv[2]
   frames = load_video_frames(file)
   max_cons_motion = check_for_motion(frames, video_file)
   print(max_cons_motion)

