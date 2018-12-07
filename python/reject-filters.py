#!/usr/bin/python3 

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
      for (i,c) in enumerate(cnts):
         bad_cnt = 0
         x,y,w,h = cv2.boundingRect(cnts[i])
         if w <= 1 and h <= 1:
            bad_cnt = 1
         if w >= 630 or h >= 400:
            bad_cnt = 1
         if bad_cnt == 0:
            #print("CNTS: ", frame_count, x,y,w,h)
            good_cnts.append((x,y,w,h)) 
            cv2.rectangle(nice_frame, (x, y), (x + w, y + w), (255, 0, 0), 2)
      if len(good_cnts) > 10:
         print ("NOISE!", frame_count, len(good_cnts))
         #noisy cnt group don't count it. 
         good_cnts = []
      cv2.imwrite(frame_file, nice_frame)
      frame_file_tn = frame_file.replace(".png", "-tn.png")
      thumbnail = cv2.resize(nice_frame, (0,0), fx=0.5, fy=0.5)
      cv2.imwrite(frame_file_tn, thumbnail)

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
   confirm_file = base_file + "-confirm.txt"
   out = open(confirm_file, "w")
   out.write(str(frame_data))
   out.close() 

def move_rejects(trim_file,frame_data):
   proc_dir = json_conf['site']['proc_dir']

   fel = trim_file.split("-trim")
   base_file = fel[0]
   motion_file = base_file + "-motion.txt"

   reject_file = base_file + "-rejected.txt"
   out = open(reject_file, "w")
   out.write(str(frame_data))
   out.close() 



   cmd = "mv " + motion_file + " " + proc_dir + "rejects/"
   print(cmd)
   os.system(cmd)
   cmd = "mv " + trim_file + " " + proc_dir + "rejects/"
   os.system(cmd)
   print(cmd)

def check_frame_rate(trim_file):
   cmd = "/usr/bin/ffprobe " + trim_file + ">checks.txt 2>&1"
   print(cmd)
   output = subprocess.check_output(cmd, shell=True).decode("utf-8")
   efp = open("checks.txt")
   #Stream #0:0(und): Video: h264 (Main) (avc1 / 0x31637661), yuvj420p(pc, bt709), 640x480, 649 kb/s, 18.66 fps, 25 tbr, 90k tbn, 180k tbc (default)
   stream_found = 0
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
   return(fps)

def apply_reject_filters(trim_file):
   frames = []
   print ("Apply reject filters for : ", trim_file)
   el = trim_file.split("-trim")
   mf = el[0]
   print(el)
   clip_file = mf + ".mp4"
   confirm_file = mf + "-confirm.txt"

   file_exists = Path(confirm_file)
   if (file_exists.is_file() is True):
      print("DONE ALREADY!")
      return()

  
   trim_fps = check_frame_rate(trim_file)
   clip_fps = check_frame_rate(clip_file)
   print ("Trim FPS: ", trim_fps)
   print ("Clip FPS: ", clip_fps)
   if int(float(trim_fps)) >= 20: 
      frames = load_video_frames(trim_file)
      if len(frames) > 5:
         max_cons_motion, frame_data = check_for_motion(frames, trim_file)
         print ("Max Cons Motion: ", max_cons_motion)
      else:
         max_cons_motion = 0
         reject_reason = "no frames/bad file."
   else:
      print("SKIPPING FOR LOW FPS")
      max_cons_motion = 0
   if (max_cons_motion < 7) :
       print ("REJECTED")
       move_rejects(trim_file, frame_data)
   else:
       print ("PASSED")
       confirm_motion(trim_file, frame_data)

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
