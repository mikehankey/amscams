#!/usr/bin/python3
import subprocess
from PIL import ImageFont, ImageDraw, Image, ImageChops
from datetime import datetime
import datetime as dt
import ephem
import numpy as np
#import datetime
import time
import sys
import os
import cv2
import glob

from lib.UtilLib import calc_dist,find_angle, best_fit_slope_and_intercept, check_running, logger
from lib.FileIO import load_json_file, save_json_file, cfe
from lib.flexLib import load_frames_fast, stack_frames_fast, convert_filename_to_date_cam, day_or_night, stack_stack
from lib.VIDEO_VARS import PREVIEW_W, PREVIEW_H, SD_W, SD_H
# SD_16_W, SD_16_H
hdm_x = 1920 / SD_W
hdm_y = 1080 / SD_H


json_conf = load_json_file("../conf/as6.json")

def ffprobe(video_file):
   default = [704,576]
   try:
   #if True:
      cmd = "/usr/bin/ffprobe " + video_file + " > /tmp/ffprobe72.txt 2>&1"
      output = subprocess.check_output(cmd, shell=True).decode("utf-8")
   except:
       print("Couldn't probe.")
       print(cmd)
       return(0,0,0,0)

   #try:
   #time.sleep(2)
   output = None
   if True:
      fpp = open("/tmp/ffprobe72.txt", "r")
      for line in fpp:
         if "Duration" in line:
            el = line.split(",")
            dur = el[0]
            dur = dur.replace("Duration: ", "")
            el = dur.split(":")
            tsec = el[2]
            tmin = el[1]
            tmin_sec = float(tmin) * 60
            total_frames = (float(tsec)+tmin_sec) * 25
         if "Stream" in line:
            output = line
      fpp.close()
      if output is None:
         print("FFPROBE PROBLEM:", video_file)
         return(0,0,0,0)

      el = output.split(",")
      for ee in el:
         if "x" in ee and "Stream" not in ee:
            dim = ee
            if "SAR" in el[2]:
               ddel = el[2].split(" ")
               for i in range(0, len(ddel)):
                  if "x" in ddel[i]:
                     el[2] = ddel[i]
         if "kb/s" in ee :
            bitrate = ee
            bitrate  = bitrate.split(" ")[1]

      w, h = dim.split("x")
   return(w,h, bitrate, int(total_frames))

def day_or_night(capture_date, json_conf):

   device_lat = json_conf['site']['device_lat']
   device_lng = json_conf['site']['device_lng']

   obs = ephem.Observer()

   obs.pressure = 0
   obs.horizon = '-0:34'
   obs.lat = device_lat
   obs.lon = device_lng
   obs.date = capture_date

   sun = ephem.Sun()
   sun.compute(obs)

   (sun_alt, x,y) = str(sun.alt).split(":")

   saz = str(sun.az)
   (sun_az, x,y) = saz.split(":")
   if int(sun_alt) < -1:
      sun_status = "night"
   else:
      sun_status = "day"
   return(sun_status)



def fix_missing_stacks(day):
   running = check_running("fms")
   if running > 2:
      print("ALREADY RUNNING:", running)
      exit()
   afiles = sorted(glob.glob("/mnt/ams2/SD/proc2/" + day + "/*.mp4" ), reverse=True)
   files = []
   for ff in afiles:
      if "-crop" not in ff and "trim" not in ff:
         files.append(ff)
   missing = 0
   found = 0
   for file in files:
      file_name = file.split("/")[-1]
      file_dir = file.replace(file_name,"")
      tday = file_name[0:10]
      y,m,d = tday.split("_") 

      image_file_name = file_name.replace(".mp4", "-stacked-tn.png")
      image_file = file_dir + "/images/" + image_file_name
      vals_file_name = file_name.replace(".mp4", "-vals.json")
      vals_file = file_dir + "/data/" + vals_file_name
      if tday != day:
         print("This file is in the wrong day????", day, file_name)
         exit()
         right_dir = "/mnt/ams2/SD/proc2/" + tday + "/"
         right_img_dir = "/mnt/ams2/SD/proc2/" + tday + "/images/"
         right_data_dir = "/mnt/ams2/SD/proc2/" + tday + "/day/"
         if cfe(right_img_dir,1) == 0:
            os.makedirs(right_img_dir)
         if cfe(right_data_dir,1) == 0:
            os.makedirs(right_data_dir)
         cmd = "mv " + file + " " + right_dir 
         if file != right_dir:
            os.system(cmd)
         print(cmd)
         if cfe(image_file) == 1:
            cmd = "mv " + image_file + " " + right_img_dir 
            os.system(cmd)
            print(cmd)
            print("There is a stack in this dir too.")
         if cfe(vals_file) == 1:
            cmd = "mv " + vals_file + " " + right_data_dir 
            os.system(cmd)
            print(cmd)
            print("Vals in this dir too.")
         #exit()
      if cfe(image_file) == 0:
 
         if cfe(vals_file) == 1:
            vals_js = load_json_file(vals_file)
            vals = vals_js['sum_vals']
         else:
            print("VALS:", vals_file)
            vals = [] 
         (f_datetime, cam, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(file)
         sun_status = day_or_night(f_date_str, json_conf)
         if sun_status == 'day':
            sun_status = "1"
         else:
            sun_status = "0"
         print("Missing:", file, sun_status )
         os.system("mv " + file + " /mnt/ams2/SD")
         #scan_and_stack_fast(file, sun_status, vals)

         missing += 1      
      else: 
         found += 1      
   print("Missing / Found:", missing, found)


def batch_ss(wildcard=None):
   running = check_running("scan_stack.py bs") 
   if running > 2:
      print("Running already.")
      exit()

   if wildcard is not None:
      glob_dir = "/mnt/ams2/SD/*" + wildcard + "*.mp4"
      #glob_dir = "/mnt/ams2/CAMS/queue/*" + wildcard + "*.mp4"
   else:
      glob_dir = "/mnt/ams2/SD/*.mp4"
      #glob_dir = "/mnt/ams2/CAMS/queue/*.mp4"
   print(glob_dir)
   files = sorted(glob.glob(glob_dir), reverse=True)
   new_files =[]
   for file in files:
      if "trim" not in file:
         new_files.append(file)

   for file in sorted(new_files, reverse=True)[0:1000]:
      ffp = ffprobe(file)
      if ffp[3] == 0:
         print("corrupt file")
         continue
      (f_datetime, cam, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(file)
      sun_status = day_or_night(f_date_str, json_conf)
      cur_time = int(time.time())
      st = os.stat(file)
      size = st.st_size
      mtime = st.st_mtime
      tdiff = cur_time - mtime
      tdiff = tdiff / 60
      if tdiff < 5:
         print("File too recent!", file)
         continue

      if sun_status == "day" :
         sun_status = "1"
         cmd = "mv " + file + " /mnt/ams2/SD/proc2/daytime/"
         print("MOVE DAYTIME FILE!")
         print(cmd)
         os.system(cmd)
         continue
      else:
         sun_status = "0"
      cur_time = int(time.time())
      st = os.stat(file)
      size = st.st_size
      print ("SIZE:", size)
      mtime = st.st_mtime
      tdiff = cur_time - mtime
      tdiff = tdiff / 60

      if size < 100:
         print("BAD SIZE!")
      else: 
         #try:
         if True:
            scan_and_stack_fast(file, sun_status)
         #else:
         #except:
         #   print("FAILED! File must be bad???", file)
         #   logger("scan_stack.py", "batch_ss / scan_and_stack_fast", "failed to scan and stack ")
            #exit()
         #   cmd = "mv " + file + " /mnt/ams2/bad/"
         #   os.system(cmd)
         #   continue

      #running = check_running("scan_stack.py") 
      if False:
      #if running > 2:
         wait = 1
         while(running > 2):
            time.sleep(2)
            running = check_running("scan_stack.py") 
            print("Running:", running)
         if (tdiff > 3):
            cmd = "./scan_stack.py ss " + file + " " + sun_status + " &"
            print(cmd)
            #os.system("./scan_stack.py ss " + file + " " + sun_status + " &") 
            # exit()
            scan_and_stack(file, sun_status)
         else:
            print(tdiff)

#def stack(file):
#   frames,color_frames,sd_subframes,sum_vals,max_vals,pos_vals = load_frames_fast(video_file, json_conf, 0, 0, [], 1,resize, sun_status)


def scan_and_stack_fast(file, sun_status = 0, vals = []):
   mask_imgs, sd_mask_imgs = load_mask_imgs(json_conf)

   # temp
   em = cv2.imread("/mnt/ams2/meteor_archive/AMS1/CAL/MASKS/010317_mask.png", 0)
   print(mask_imgs.keys())
   #cv2.imshow('pepe', em)
   #cv2.waitKey(0)

   mask_imgs["010317"] = em

   threshold = None

   (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(file)
   if int(fh) % 2 == 0 and (int(fmin) == 32 or int(fmin) == 33):
      sense_up = True
   else:
      sense_up = False

   if cam in mask_imgs:
      mask_img = mask_imgs[cam]
   else:
      mask_img = None

   print("VALS:", vals)
   fn = file.split("/")[-1]
   day = fn[0:10]
   proc_dir = "/mnt/ams2/SD/proc2/" + day + "/" 
   proc_img_dir = "/mnt/ams2/SD/proc2/" + day + "/images/" 
   proc_data_dir = "/mnt/ams2/SD/proc2/" + day + "/data/" 
   if cfe(proc_img_dir, 1) == 0:
      os.makedirs(proc_img_dir)
   if cfe(proc_data_dir, 1) == 0:
      os.makedirs(proc_data_dir)
   stack_file = proc_img_dir + fn.replace(".mp4", "-stacked-tn.jpg")
   json_file = proc_data_dir + fn.replace(".mp4", "-vals.json")




   sum_vals = []
   max_vals = []
   avg_max_vals = []
   pos_vals = []
   PREVIEW_W = 300
   PREVIEW_H = 169
   start_time = time.time()

   fc = 0
   print("Loading file:", file)
   cap = cv2.VideoCapture(file)
   frames = []
   gray_frames = []
   sub_frames = []
   fd = []
   stacked_image = None
   stacked_sub_np = None
   fb = 0
   mask_resized = 0
   small_thresh = None

   # for each frame
   while True:
      grabbed , frame = cap.read()
      ignore_stack = False
      if fc < len(vals):
         if vals[fc] == 0  and fc > 20:
            print("SKIP FRAME:", fc, vals[fc])
            fc = fc + 1
            continue

      if not grabbed and fc > 5:
         print("FRAME NOT GRABBED:", fc)
         break

      if sun_status == 1:
         daytime = True 
         yo = 1
      else:
         try:
            small_frame = cv2.resize(frame, (0,0),fx=.5, fy=.5)
         except:
            print("Bad video file:", file)
            cmd = "rm " + file
            #os.system(cmd)
            return()

      if mask_img is None:
         print("NO MASK!")
         mask_img = np.zeros((frame.shape[1],frame.shape[0]),dtype=np.uint8)
      if mask_img is not None and mask_resized == 0:
         mask_img = cv2.resize(mask_img, (frame.shape[1],frame.shape[0]))
         small_mask = cv2.resize(mask_img, (0,0),fx=.5, fy=.5)
         mask_resized = 1

      if sun_status != 1:
         # night time
         gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
         #try:
         #   em = cv2.resize(em, (gray.shape[1], gray.shape[0]))
         #   test = cv2.subtract(gray, em)
         #except:
         #   print("problem")
         #cv2.imshow('pepe', test)
         #cv2.waitKey(30)
         #gray = cv2.subtract(gray, last_gray)
         #gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
         if fc > 0:
            #sub = cv2.subtract(gray, em)
            masked_frame = cv2.subtract(gray, small_mask)
            #masked_frame = cv2.subtract(gray, mask_img)
            if mask_img is not None:
               sub = cv2.subtract(sub, small_mask)
            if small_thresh is not None:
               sub = cv2.subtract(sub, small_thresh)
               #debug only
               #ksmall_thresh_c = cv2.cvtColor(small_thresh, cv2.COLOR_GRAY2BGR)
               #small_frame = cv2.subtract(small_frame, small_thresh_c)
               #sub = cv2.subtract(sub, mask_img)
         else:
            sub = cv2.subtract(gray, gray)
         if stacked_sub_np is not None:
            sub = cv2.subtract(sub, stacked_sub_np)

         min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(sub)
         #cv2.imshow('sub', small_frame)
         #cv2.waitKey(30)
         #if stacked_sub_np is not None:
         #   cv2.imshow('stack', stacked_sub_np)
         #   cv2.waitKey(30)
         if max_val < 10:
            sum_vals.append(0)
            max_vals.append(max_val)
            avg_max_vals.append(max_val)
            pos_vals.append((0,0))
         else:
            _, thresh_frame = cv2.threshold(sub, 15, 255, cv2.THRESH_BINARY)
            #min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(thresh_frame)
            sum_val =cv2.sumElems(thresh_frame)[0]
            #print("SUM VAL:", sum_val)
            if sum_val > 5000:
               fb += 1
               print("FIREBALL:", fc, sum_val)
            if sum_val > 100000 and sense_up is True:
               fb += 1
               print("SENSE UP??:", fc, sum_val)
               ignore_stack = True

            mx = mx * 2
            my = my * 2
            sum_vals.append(sum_val)
            max_vals.append(max_val)
            if max_val > 1:
               avg_max_vals.append(max_val)
            pos_vals.append((mx,my))
      #gray_frames.append(gray)

      if int(sun_status) == 1:
         if fc % 25 == 1:
            print("DAY:", sun_status , fc)
            print("Stacking frame", fc)
            small_frame = cv2.resize(frame, (0,0),fx=.5, fy=.5)
            frame_pil = Image.fromarray(small_frame)
            if stacked_image is None:
               stacked_image = stack_stack(frame_pil, frame_pil)
            else:
               if ignore_stack is not True:
                  stacked_image = stack_stack(stacked_image, frame_pil)
         sum_vals.append(0)
         max_vals.append(0)
         pos_vals.append((0,0))
      else:
         if max_val > 10 or fc < 10:
            avg_max = np.median(avg_max_vals)
            if avg_max > 0:
               diff = (max_val / avg_max) * 100
            else:
               diff = 0
            if max_val > avg_max * 1.2 or fc <= 10:
               print("STAK THE FRAME", fc, avg_max, max_val, diff, fc)
               frame_pil = Image.fromarray(small_frame)
               sub_pil = Image.fromarray(sub)
               if stacked_image is None:
                  stacked_image = stack_stack(frame_pil, frame_pil)
                  stacked_sub = stack_stack(sub_pil, sub_pil)
               else:

                  if ignore_stack is not True:
                     stacked_image = stack_stack(stacked_image, frame_pil)
                  stacked_sub = stack_stack(stacked_sub, sub_pil)
               stacked_sub_np = np.array(stacked_sub)
            else:
               print("NO STAK THE FRAME", fc, avg_max, max_val, diff, fc)
               #cv2.imshow('pepe', stacked_sub_np)
               #cv2.waitKey(30)
      last_gray = gray
      cv_stacked_image = np.asarray(stacked_image)
      #cv2.imshow('pepe', cv_stacked_image)
      #cv2.waitKey(30)
      #frames.append(frame)
      if fc == 1:
         # add to the mask on the 1st frame.
         _, threshold = cv2.threshold(frame.copy(), 120, 255, cv2.THRESH_BINARY)
         small_thresh = cv2.resize(threshold, (0,0),fx=.5, fy=.5)
         small_thresh = cv2.cvtColor(small_thresh, cv2.COLOR_BGR2GRAY)

      if fc % 100 == 1:
         print(fc)
      fc += 1
   cv_stacked_image = np.asarray(stacked_image)
   cv_stacked_image = cv2.resize(cv_stacked_image, (PREVIEW_W, PREVIEW_H))
   cv2.imwrite(stack_file, cv_stacked_image)
   print(stack_file)
   

   vals = {}
   vals['sum_vals'] = sum_vals
   vals['max_vals'] = max_vals
   vals['pos_vals'] = pos_vals
   if cfe(stack_file) == 0:
      logger("scan_stack.py", "scan_and_stack_fast", "Image file not made! " + stack_file + " " )
      print("ERROR: Image file not made! " + stack_file)
      time.sleep(10)
   save_json_file(json_file, vals)
   print("JSON FILE:", json_file)
   elapsed_time = time.time() - start_time
   print(stack_file)
   print("DISABLED TEMPORARILY! mv " + file + " " + proc_dir)
   #os.system("mv " + file + " " + proc_dir)
   

   print("mv " + file + " " + proc_dir)
   print("PROC:", proc_dir + fn)
   print("STACK FILE:", stack_file)
   print("JSON FILE:", json_file)
   print("Elp:", elapsed_time)
   if cfe(stack_file) == 0:
      print("No stack file made!?")
      logger("scan_stack.py", "scan_and_stack_fast", "Image file not made! " + stack_file + " " )
      exit()


def scan_and_stack(video_file, sun_status):
   if cfe(video_file) == 0:
      print("File doesn't exist : ", video_file)
      return()
   vid_fn = video_file.split("/")[-1]   
   (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(video_file)

   proc_dir = "/mnt/ams2/SD/proc2/" + fy + "_" + fm + "_" + fd + "/"
   proc_img_dir = "/mnt/ams2/SD/proc2/" + fy + "_" + fm + "_" + fd + "/images/"
   proc_data_dir = "/mnt/ams2/SD/proc2/" + fy + "_" + fm + "_" + fd + "/data/"

   if cfe(proc_img_dir, 1)  == 0:
      os.makedirs(proc_img_dir)
   if cfe(proc_data_dir, 1)  == 0:
      os.makedirs(proc_data_dir)

   vals_fn = vid_fn.replace(".mp4", "-vals.json")
   stack_fn = vid_fn.replace(".mp4", "-stacked-tn.png")
   proc_vals_file = proc_data_dir + vals_fn
   proc_stack_file = proc_img_dir + stack_fn 
   proc_vid_file = proc_dir + vid_fn

   if sun_status == "day":
      resize = [PREVIEW_W,PREVIEW_H]
   else:
      resize = []

   vals = {}
   start_time = time.time()

   sd_frames,sd_color_frames,sd_subframes,sum_vals,max_vals,pos_vals = load_frames_fast(video_file, json_conf, 0, 0, [], 1,resize, sun_status )
   print(sum_vals, sun_status)
   i = 0
   cm = 0
   nomo = 0
   med_sum = np.median(sum_vals)
   max_times = 0
   max_cm = 0
   fb = 0
   cmdata = []
   event = []
   events = []
   for val in sum_vals:
      if val > 10000:
         fb += 1
      if med_sum > 0:
         times = val / med_sum
      else:
         times = 0
      if times >= 2:
         cm += 1
         nomo = 0
      else:
         nomo += 1
         if cm > 10 and nomo > 5:
            events.append(event)
            event = []
            cm = 0
         elif cm >= 3 and nomo >3:
            # event ended
            events.append(event)
            event = []
            cm = 0
      if times > max_times :
         max_times = times
      if cm > max_cm :
         max_cm = cm 
      if cm >= 3:
         print("SUM VAL:", i, med_sum, val, "X", int(times), nomo, int(cm), pos_vals[i])
         event.append((i,med_sum,val,times,nomo,cm,pos_vals[i][0],pos_vals[i][1]))
      cmdata.append((i,med_sum,val,times,nomo,cm,pos_vals[i]))
      i += 1
   vals['sum_vals'] = sum_vals
   vals['max_vals'] = max_vals
   vals['pos_vals'] = pos_vals
   ev = 0
   real_events = []
   for event in events:
       real_cm = calc_real_cm(event)
       if real_cm > 3:
          real_events.append(event)
          for data in event:

             print(ev, data)
       ev += 1
   elapsed_time = time.time() - start_time


   vals['events'] = real_events 

   print("LOAD & SCAN TIME:", elapsed_time)
   print("FR:", len(sd_color_frames), sun_status, len(sum_vals), len(max_vals), len(pos_vals))
   if sun_status == "day":
      skip = 10 
      stacked_image = stack_frames_fast(sd_color_frames, skip, [PREVIEW_W, PREVIEW_H], sun_status,sum_vals)
      
   else:
      skip = 1
      stacked_image = stack_frames_fast(sd_color_frames, skip, [PREVIEW_W, PREVIEW_H], sun_status, sum_vals)

   stack_file = video_file.replace(".mp4", "-stacked.png")

   cmd = "mv " + video_file + " " + proc_dir
   os.system(cmd)

   cv2.imwrite(proc_stack_file, stacked_image)
   save_json_file(proc_vals_file, vals, True)

   elapsed_time = time.time() - start_time
   print("SCAN AND STACK TIME:", elapsed_time)
   vfn = video_file.split("/")[-1]
   print(proc_dir + vfn)
   print(proc_vals_file)

   if max_times > 10 and max_cm > 10 and fb > 10:
      fb_vfn = proc_vals_file.replace(".json", "-fireball.json")
      fb_data = {}
      fb_data['events'] = real_events
      save_json_file(fb_vfn, fb_data)
      print("POSSIBLE FIREBALL!!!!", max_times, max_cm, fb, fb_vfn)
      clip_fireball(proc_dir, vfn, real_events)

   return(proc_vals_file)

def clip_fireball(proc_dir, vfn, events):
   for ev in events:
      fns = [row[0] for row in ev]
      start = min(fns) - 25
      end = max(fns) + 50
      if end > 1499:
         end = 1499
      if start < 0:
         start = 0 

      print("CLIP FIREBALL:", proc_dir + vfn, start, end)
      video_file = proc_dir + vfn
      outfile = video_file.replace(".mp4", "-trim-" + str(start) + ".mp4")
      jsf = outfile.replace(".mp4", ".json")
      cmd = "cd /home/ams/amscams/pipeline/; ./FFF.py splice_video " + video_file + " " + str(start) + " " + str(end) + " " + outfile + " " + "frame"
      hd_trim_clip = find_hd_min(video_file, start, end)

      os.system(cmd)
      print(cmd)
      print("SD:", outfile)
      print("HD:", hd_trim_clip)
      mj = make_base_meteor_json(outfile, hd_trim_clip )
      jsf = mj['sd_video_file'].replace(".mp4", ".json")
      cmd = "cp " + outfile + " " + mj['sd_video_file']
      print(cmd)
      os.system(cmd)
      if hd_trim_clip is not None:
         cmd = "cp " + hd_trim_clip + " " + mj['hd_trim']
         print(cmd)
         os.system(cmd)
         cmd = "./stack-full.py " + mj['hd_trim']
         os.system(cmd)
         
      cmd = "cp " + outfile + " " + mj['sd_video_file']
      save_json_file(jsf, mj)
      cmd = "./stack-full.py " + mj['sd_video_file']
      os.system(cmd)
      if cfe(mj['sd_stack']) == 1:
         simg = cv2.imread(mj['sd_stack'])
         thumb = cv2.resize(simg, (320,180))
         th_fn = mj['sd_stack'].replace(".jpg", "-tn.jpg")
         cv2.imwrite(th_fn, thumb)

      print("saved:", jsf)

def make_base_meteor_json(video_file, hd_video_file ):
   mj = {}
   sd_fn, dir = fn_dir(video_file)
   if hd_video_file is not None:
      hd_fn, dir = fn_dir(hd_video_file)
      hd_stack_fn = hd_fn.replace(".mp4", "-stacked.jpg")
   stack_fn = sd_fn.replace(".mp4", "-stacked.jpg")

   date = sd_fn[0:10]
   mdir = "/mnt/ams2/meteors/" + date + "/" 
   mj["sd_video_file"] = mdir + sd_fn 
   mj["sd_stack"] = mdir + stack_fn
   mj["sd_objects"] = []
   if hd_video_file is not None:
      mj["hd_trim"] = mdir + hd_fn
      mj["hd_stack"] = mdir + hd_stack_fn
      mj["hd_video_file"] = mdir + hd_fn
      mj["hd_trim"] = mdir + hd_fn
    #   mj["hd_trim_dir"]
    #   mj["hd_trim_time_offset"]
      mj["hd_objects"] = []
    #mj["status"]
    #mj["total_frames"]
   mj["meteor"] = 1
    #mj["test_results"]
    #mj["flex_detect"]
    #mj["archive_file"]

   return(mj)
def find_hd_min(sd_file, start_frame, end_frame):

   (sd_datetime, sd_cam, sd_date, sd_y, sd_m, sd_d, sd_h, sd_M, sd_s) = convert_filename_to_date_cam(sd_file)
   day = sd_y + "_" + sd_m + "_" + sd_d
   offset = int(start_frame) / 25
   dur_sec = (int(end_frame) - int(start_frame)) / 25
   meteor_datetime = sd_datetime + dt.timedelta(seconds=offset)
   hd_glob = "/mnt/ams2/HD/" + sd_y + "_" + sd_m + "_" + sd_d + "_*" + sd_cam + "*.mp4"
   hd_files = sorted(glob.glob(hd_glob))
   hd_files_time = []
   for hd_file in hd_files:
      el = hd_file.split("_")
      if len(el) == 8 and "meteor" not in hd_file and "crop" not in hd_file and "trim" not in hd_file and "TL" not in hd_file:

         hd_datetime, hd_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(hd_file)
         time_diff = meteor_datetime - hd_datetime
         time_diff_sec = time_diff.total_seconds()
         if 0 <= time_diff_sec <= 60:
            print("TIME DIFF SEC:", time_diff_sec)
            hd_files_time.append((hd_file, time_diff_sec, hd_datetime))

   print("SD FILES:", sd_file )
   print("SD START/end:", start_frame, end_frame)
   print("HD FILES:", hd_files_time)
   #for data in hd_files_time:
   #   print("HD DATA:", len(data), data)
   outfile = None   
   for hd_min_file, hd_start_sec, min_time in hd_files_time:
      print("HD TRIM:", hd_min_file, offset , offset + dur_sec)
      hd_fn = hd_min_file.split("/")[-1]
      outfile = "/mnt/ams2/SD/proc2/" + day + "/hd_save/" + hd_fn 
      outfile = outfile.replace(".mp4", "-trim-" + str(start_frame) + "-HD-meteor.mp4")
      cmd = "cd /home/ams/amscams/pipeline/; ./FFF.py splice_video " + hd_min_file + " " + str(hd_start_sec) + " " + str(hd_start_sec + dur_sec) + " " + outfile + " " + "sec"
      os.system(cmd)
      print(cmd)

   # check hd save dir
   if outfile is None:
      hd_glob = "/mnt/ams2/SD/proc2/" + sd_y + "_" + sd_m + "_" + sd_d + "/hd_save/"  + sd_y + "_" + sd_m + "_" + sd_d + "_" + sd_h + "_*" + sd_cam + "*.mp4"
      hd_files = sorted(glob.glob(hd_glob))
      print ("HD GLOB:", hd_glob)
      for hd_file in hd_files:
         print(hd_file)
         hd_datetime, hd_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(hd_file)
         time_diff = meteor_datetime - hd_datetime
         time_diff_sec = time_diff.total_seconds()
         if 0 <= time_diff_sec <= 60 and "HD" in hd_file and "crop" not in hd_file:

            print("HD SAVE DIR TIME DIFF SEC:", time_diff_sec)
            outfile = hd_file
            hd_files_time.append((hd_file, time_diff_sec, hd_datetime))


   return(outfile)

def load_mask_imgs(json_conf):
   mask_files = glob.glob("/mnt/ams2/meteor_archive/" + json_conf['site']['ams_id'] + "/CAL/MASKS/*mask*.png" )
   mask_imgs = {}
   sd_mask_imgs = {}
   for mf in mask_files:
      mi = cv2.imread(mf, 0)
      omh, omw = mi.shape[:2]
      fn,dir = fn_dir(mf)
      fn = fn.replace("_mask.png", "")
      mi = cv2.resize(mi, (1920, 1080))
      sd = cv2.resize(mi, (omw, omh))
      mask_imgs[fn] = mi
      sd_mask_imgs[fn] = sd
   return(mask_imgs, sd_mask_imgs)


def calc_real_cm(data):
   rc = []
   for row in data:
      i,med_sum,val,times,nomo,cm,x,y = row 
      rc.append(cm)
   real_cm = len(set(rc))
   return(real_cm)


def fn_dir(file):
   fn = file.split("/")[-1]
   dir = file.replace(fn, "")
   return(fn, dir)



if sys.argv[1] == "bs":
   if len(sys.argv) == 3:
      batch_ss(sys.argv[2])
   else:
      batch_ss()

if sys.argv[1] == "ss":
   scan_and_stack_fast(sys.argv[2], sys.argv[3])
   #scan_and_stack(sys.argv[2], sys.argv[3])
if sys.argv[1] == "fms":
   if len(sys.argv) < 3:
      now = datetime.now()
      today = now.strftime("%Y_%m_%d")

      fix_missing_stacks(today)
   else:
      fix_missing_stacks(sys.argv[2])
if sys.argv[1] == "dv":
   detect_in_vals(sys.argv[2])
if sys.argv[1] == "stack":
   stack(sys.argv[2])
