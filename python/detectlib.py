#!/usr/bin/python3 
import subprocess
import math
from PIL import Image, ImageChops
import numpy as np
import datetime
import json
import cv2
from pathlib import Path
import os
from scipy import signal
# Library for detect function


json_file = open('../conf/as6.json')
json_str = json_file.read()
json_conf = json.loads(json_str)
proc_dir = json_conf['site']['proc_dir']

def setup_dirs(filename):
   el = filename.split("/")
   fn = el[-1]
   working_dir = filename.replace(fn, "")
   data_dir = working_dir + "/data/"
   images_dir = working_dir + "/images/"
   file_exists = Path(data_dir)
   if file_exists.is_dir() == False:
      os.system("mkdir " + data_dir)

   file_exists = Path(images_dir)
   if file_exists.is_dir() == False:
      os.system("mkdir " + images_dir)


def get_image(image_file):
   open_cv_image = cv2.imread(image_file,1)   
   return(open_cv_image)

def get_masks(this_cams_id):
   my_masks = []
   cameras = json_conf['cameras']
   for camera in cameras:
      if str(cameras[camera]['cams_id']) == str(this_cams_id):
         masks = cameras[camera]['masks']
         for key in masks:
            my_masks.append((masks[key]))


   return(my_masks)


def convert_filename_to_date_cam(file):
   el = file.split("/")
   filename = el[-1]
   filename = filename.replace(".mp4" ,"")
   if "-" in filename:
      xxx = filename.split("-")
      filename = xxx[0]
   fy,fm,fd,fh,fmin,fs,fms,cam = filename.split("_")
   f_date_str = fy + "-" + fm + "-" + fd + " " + fh + ":" + fmin + ":" + fs
   f_datetime = datetime.datetime.strptime(f_date_str, "%Y-%m-%d %H:%M:%S")
   return(f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs)


def load_video_frames(trim_file):

   (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(trim_file)
   masks = get_masks(cam)

   cap = cv2.VideoCapture(trim_file)

   frames = []
   frame_count = 0
   go = 1
   while go == 1:
      _ , frame = cap.read()
      if frame is None:
         if frame_count <= 1:
            cap.release()
            return(frames)
         else:
            go = 0
      else:
         if len(frame.shape) == 3:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
         # apply masks for frame detection
         for mask in masks:
            mx,my,mw,mh = mask.split(",")
            frame[int(my):int(my)+int(mh),int(mx):int(mx)+int(mw)] = 0

         frames.append(frame)
         frame_count = frame_count + 1
   #cv2.imwrite("/mnt/ams2/tests/test" + str(frame_count) + ".png", frames[0])
   cap.release()
   return(frames)

def mask_frame(frame, mp):
   for x,y in mp:
      frame[y-3:y+3,x-3:x+3] = 0
   return(frame)

def check_for_motion(frames, video_file):
   cv2.namedWindow('pepe')
   # find trim number
   el = video_file.split("/")
   fn = el[-1]
   st = fn.split("trim")
   stf = st[1].split(".")

   if len(frames) > 200:
      med_stack_all = cv2.convertScaleAbs(np.median(np.array(frames[0:199]), axis=0))
   else:
      med_stack_all = cv2.convertScaleAbs(np.median(np.array(frames), axis=0))

   max_px = np.max(med_stack_all)
   avg_px = np.mean(med_stack_all)
   pdif = max_px - avg_px
   pdif = int(pdif / 10) + avg_px
   #star_bg = 255 - cv2.adaptiveThreshold(med_stack_all, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 3)
    
   _, star_bg = cv2.threshold(med_stack_all, pdif, 255, cv2.THRESH_BINARY)
   #star_bg = cv2.GaussianBlur(star_bg, (7, 7), 0)
   #thresh_obj = cv2.dilate(star_bg, None , iterations=1)
   thresh_obj= cv2.convertScaleAbs(star_bg)
   (_, cnts, xx) = cv2.findContours(thresh_obj.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
   masked_pixels = []
   for (i,c) in enumerate(cnts):
      x,y,w,h = cv2.boundingRect(cnts[i])
      cx = int(x + (w/2))
      cy = int(y + (h/2))
      masked_pixels.append((cx,cy))
      cv2.rectangle(star_bg, (x, y), (x + w, y + w), (255, 0, 0), 2)
   #med_stack_all = np.median(np.array(frames), axis=0)


   #med_stack_all = cv2.cvtColor(med_stack_all, cv2.COLOR_BGR2GRAY)


   cv2.imshow('pepe', med_stack_all)
   cv2.waitKey(1)
   cv2.imshow('pepe', star_bg)
   cv2.waitKey(1)

   trim_num = int(stf[0])
   tfc = trim_num
   frame_file_base = video_file.replace(".mp4", "")
   frame_data = []
   last_frame = None
   image_acc = None
   image_acc2 = None
   frame_count = 1
   good_cnts = []
   max_cons_motion = 0
   cons_motion = 0
   moving_objects = None
   object = None
   stacked_image = None

   for frame in frames:
      if len(frame.shape) == 3:
         frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
      #thresh_obj = cv2.dilate(star_bg, None , iterations=4)
      blur_frame = cv2.GaussianBlur(frame, (7, 7), 0)
      #image_diff = cv2.absdiff(star_bg.astype(frame.dtype), blur_frame,)
      frame = mask_frame(frame, masked_pixels)

      #frame = image_diff 
      #frame = image_diff
      data_str = []
      data_str.append(trim_num)
      data_str.append(frame_count)
      nice_frame = frame.copy()


      stacked_image = stack_image_PIL(nice_frame, stacked_image)
      stacked_image_np = np.asarray(stacked_image)

      gray_frame = frame
      frame_file = frame_file_base + "-fr" + str(frame_count) + ".png"

      frame = cv2.GaussianBlur(frame, (7, 7), 0)

      # setup image accumulation
      if last_frame is None:
         last_frame = frame
        
      if image_acc is None:
         image_acc = np.empty(np.shape(frame))
         alpha = .1
         xend = len(frames)
         xstart = xend - 30
         for i in range(xstart,xend):
            hello = cv2.accumulateWeighted(frames[i], image_acc, alpha)
            image_diff = cv2.absdiff(image_acc.astype(frame.dtype), frames[0],)
            _, threshold = cv2.threshold(image_diff, 5, 255, cv2.THRESH_BINARY)
            thresh_obj = cv2.dilate(threshold, None , iterations=4)
            (_, cnts, xx) = cv2.findContours(thresh_obj.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for (i,c) in enumerate(cnts):
               bad_cnt = 0
               x,y,w,h = cv2.boundingRect(cnts[i])
               #masked_pixels.append((x,y))
            frame = mask_frame(frame, masked_pixels)

      if image_acc2 is None:
         image_acc2 = np.empty(np.shape(frame))

      image_diff = cv2.absdiff(image_acc.astype(frame.dtype), frame,)
      image_diff2 = cv2.absdiff(image_acc2.astype(frame.dtype), frame,)
      alpha = .1
      alpha2 = .33
      hello = cv2.accumulateWeighted(frame, image_acc, alpha)
      hello = cv2.accumulateWeighted(frame, image_acc2, alpha2)
      _, threshold = cv2.threshold(image_diff, 5, 255, cv2.THRESH_BINARY)
      _, threshold2 = cv2.threshold(image_diff2, 5, 255, cv2.THRESH_BINARY)
      thresh_obj = cv2.dilate(threshold, None , iterations=4)
      thresh_obj2 = cv2.dilate(threshold2, None , iterations=4)
      (_, cnts, xx) = cv2.findContours(thresh_obj.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
      (_, cnts2, xx) = cv2.findContours(thresh_obj2.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

      #cv2.imshow('pepe', image_diff)
      #cv2.waitKey(0)
      #cv2.imshow('pepe', image_diff2)
      #cv2.waitKey(0)
      good_cnts = []
      #if len(cnts2) > len(cnts):
      #   cnts = cnts2
      cnt_cnt = 0
      #if len(cnts) > 0:
      #   print("CNT:", frame_count, len(cnts))
      # START CNT LOOP
      for (i,c) in enumerate(cnts):
         bad_cnt = 0
         x,y,w,h = cv2.boundingRect(cnts[i])

         if w <= 1 and h <= 1:
            bad_cnt = 1
            continue
         if w >= 630 or h >= 400:
            bad_cnt = 1
            continue


         if bad_cnt == 0:
            x2 = x + w
            y2 = y + h
            cnt_img = gray_frame[y:y2,x:x2]
            cnt_x, cnt_y,cnt_w,cnt_h =  find_center(cnt_img) 
            adj_x = x + cnt_x
            adj_y = y + cnt_y
            fx = test_cnt_flux(cnt_img, frame_count, cnt_cnt)
            bf = examine_cnt(cnt_img)
            if fx == 0 or bf < 1.5:
               bad_cnt = 1 
               #masked_pixels.append((x,y))

         if bad_cnt == 0:


            if frame_count > 5 and fx == 1 and bf >= 1.5:
               object, moving_objects = find_object(tfc,(adj_x,adj_y,cnt_w,cnt_h,fx), moving_objects)
            else:
               object, masked_objects = find_object(tfc,(adj_x,adj_y,cnt_w,cnt_h,fx), moving_objects)
            

            if object != None and bad_cnt == 0:

               x2 = x + w
               y2 = y + h
               if cnt_img.shape[0] > 0 and cnt_img.shape[1] > 0:
                  fx = test_cnt_flux(cnt_img, frame_count, cnt_cnt)
               else:
                  fx = 0
               if fx == 0:
                  bad_cnt = 1

            #cv2.imwrite("/mnt/ams2/tests/cnt" + str(frame_count) + "-" + str(cnt_cnt) + ".png", cnt_img)

            if bad_cnt == 0:


               good_cnts.append((frame_count,adj_x,adj_y,w,h,fx))
               cv2.rectangle(nice_frame, (x, y), (x + w, y + w), (255, 0, 0), 2)
               cv2.putText(nice_frame, str(object),  (x,y), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
               cv2.imshow('pepe', nice_frame)
               cv2.waitKey(1)


               #cv2.rectangle(stacked_image_np, (x, y), (x + w, y + w), (255, 0, 0), 2)
               #cv2.putText(stacked_image_np, str(object),  (x,y), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
            
               stacked_image = Image.fromarray(stacked_image_np)
               cnt_cnt = cnt_cnt + 1
      # END CNT LOOP!
      if len(good_cnts) > 10:
         #print ("NOISE!", video_file,frame_count, len(good_cnts))
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
      else:
         cons_motion = 0
      frame_count = frame_count + 1
      tfc = tfc + 1


   #cv2.imshow('pepe', stacked_image_np)
   #cv2.waitKey(3)

   return(max_cons_motion, frame_data, moving_objects, stacked_image)

def clean_hist(hist):
   print("CLEAN HIST")
   new_hist = []
   last_fn = 0
   last_hx = 0
   last_hy = 0
   last_h = None

   # remove duplicate points
   points = []
   new_hist = []
   for h in hist:
      fn,hx,hy,hw,hh,hf = h
      passed = 1 
      for point in points:
         px, py = point
         if px - 1 <= hx <= px + 1 and py -1 <= hy <= py + 1:
            # dupe
            passed = 0
         
      if len(new_hist) == 0:
         points.append((hx,hy))
      if passed == 1:
         new_hist.append((h))
      points.append((hx,hy))
     

   print ("NO DUPE HIST:", new_hist, len(new_hist)) 
   if len(new_hist) > 2:
      print ("HIST is subset of hist")
      hist = new_hist[1:-1] 
   else:
      print ("HIST is HIST")
      hist = new_hist

   #hist = new_hist


   return(hist)
      

def object_report (trim_file, frame_data):
   fc =1
   tfc =1
   moving_objects = None
   found_objects = []
   for fd in frame_data:

      fd_temp = sorted(fd[2], key=lambda x: x[3], reverse=True)
      if len(fd_temp) > 0 and len(fd_temp) < 8:
         for fn,x,y,w,h,fx in fd_temp:
            object, moving_objects = find_object(tfc, (x,y,w,h,fx), moving_objects)
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
      if len_test < .5 or len_test > 2:
         status.append(('reject', 'object flickers like a plane.'))
      if elp_frms > 200:
         status.append(('reject', 'object exists for too long to be a meteor.'))
      if px_per_frame <= .59:
         status.append(('reject', 'object does not move fast enough to be a meteor.'))
      if dist < 4:
         status.append(('reject', 'object does not move far enough to be a meteor.'))
      if hist_len < 3:
         status.append(('reject', 'object does not exist long enough.'))
      # (frame_num, count, first_frame, last_frame, slope, distance, elapsed_frames, px_per_frames, status)
      obj_data = (object[0],  hist_len,  first, last,  slope, dist,  elp_frms,  px_per_frame,  status)
      found_objects.append(obj_data)
   return(found_objects, moving_objects)

def find_center(cnt_img):
   max_px = np.max(cnt_img)
   mean_px = np.mean(cnt_img)
   max_diff = max_px - mean_px
   x = 0
   y = 0
   w = 0
   h = 0
   thresh = max_diff / 2
   _, threshold = cv2.threshold(cnt_img, thresh, 255, cv2.THRESH_BINARY)
   thresh_obj = cv2.dilate(threshold, None , iterations=4)
   (_, cnts, xx) = cv2.findContours(thresh_obj.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
   # START CNT LOOP
   bad_cnt = 0
   for (i,c) in enumerate(cnts):
      bad_cnt = 0
      x,y,w,h = cv2.boundingRect(cnts[i])

      if w <= 1 and h <= 1:
         bad_cnt = 1
      if w >= 630 or h >= 400:
         bad_cnt = 1
   if bad_cnt == 0 and len(cnts) > 0:
      nx = x + (w /2)
      ny = y + (h /2)
   else:
      nx = 0
      ny = 0
   return(int(nx),int(ny),w,h)
   

def find_object(fn, pt, moving_objects):
   x,y,w,h,fx = pt
   prox_match = 0
   if moving_objects is None:
      lenstr = "0"
   else:
      lenstr = str(len(moving_objects))

   if moving_objects is None:
      # there are no objects yet, so just add this one and return.
      oid = 0
      mo = []
      moving_objects = np.array([ [[oid],[x],[y],[[fn,x,y,w,h,fx],[fn,x,y,w,h,fx]] ]])
      return(oid, moving_objects)
   else:
      # match based on proximity to pixel history of each object
      rowc = 0
      match_id = None
      for (oid,ox,oy,hist) in moving_objects:
         found_in_hist = check_hist(x,y,hist)
         if found_in_hist == 1:
            prox_match = 1
            match_id = oid

   #can't find match so make new one
   if prox_match == 0:
      oid = new_obj_id((x,y), moving_objects)
      moving_objects = np.append(moving_objects, [ [[oid],[x],[y],[[fn,x,y,w,h,fx],[fn,x,y,w,h,fx]]] ], axis=0)
   else:
      oid,ox,oy,hist = moving_objects[match_id][0]
      hist.append([fn,x,y,w,h,fx])
      moving_objects[match_id][0] = [ [[oid],[ox],[oy],[hist]] ]

   return(oid, moving_objects)

def last_meteor_check (obj, moving_objects, frame_data, frames):
   #print("LAST METEOR CHECK!")
   object_id = obj[0][0]

   flx_check_total = 0
   fx_pass = 0
   avg_tbf = 0
   obj_hist = []
   for object in moving_objects:
      this_object_id = object[0][0]
      if object_id == this_object_id:
         this_hist = object[3]
         for hist in this_hist:
            fn, x,y,w,h,fx = hist
            flx_check_total = flx_check_total + fx
         if len(hist) > 1:
            fx_perc = flx_check_total / len(this_hist)
         if fx_perc > .6:
            fx_pass = 1
            obj_hist = this_hist

   # Examine each cnt to tell if it has a bright centroid or streak
   # or is more anomolous

   tbf = 0
   if fx_pass == 1:
      # make cnts images for each cnt (so we can examine/debug)
      for fn,x,y,w,h,fx in obj_hist:
         image = frames[fn]
         x2 = x + w + 5
         y2 = y + h + 5
         x1 = x  - 5
         y1 = y  - 5
         if x1 < 0:
            x1 = 0
         if y1 < 0:
            y1 = 0
         if x2 > image.shape[1]:
            x2 = image.shape[1]
         if y2 > image.shape[0]:
            y2 = image.shape[0]
         if w > 1 and h > 1:
            cnt_img = image[y1:y2,x1:x2]
            brightness_factor = examine_cnt(cnt_img)
            tbf = tbf + brightness_factor
         #cv2.imwrite("/mnt/ams2/tests/cnt" + str(fn) + ".jpg", cnt_img)

      if len(obj_hist) > 0:
         avg_tbf = tbf / len(obj_hist)

   if avg_tbf > 1.7:
      fx_pass = 1
   else:
      fx_pass = 0


   return(fx_pass)


def examine_cnt(cnt_img):
   max_px = np.max(cnt_img)
   avg_px = np.mean(cnt_img)
   if avg_px > 0:
      brightness_factor = max_px / avg_px
   else:
      brightness_factor = 0
   return(brightness_factor)


def ffmpeg_trim (filename, trim_start_sec, dur_sec, outfile):
   if int(trim_start_sec) < 10:
      trim_start_sec = "0" + str(trim_start_sec)
   if int(dur_sec) < 10:
      dur_sec = "0" + str(dur_sec)

   #outfile = filename.replace(".mp4", out_file_suffix + ".mp4")
   cmd = "/usr/bin/ffmpeg -i " + filename + " -y -ss 00:00:" + str(trim_start_sec) + " -t 00:00:" + str(dur_sec) + " -c copy " + outfile + ">/tmp/x 2>&1"
   os.system(cmd)
   return(outfile)

def test_cnt_flux(cnt_img, frame_count,cnt_cnt):

   cnt_show = cnt_img.copy()
   cnt_h, cnt_w = cnt_img.shape
   hull = 0
   brightness_passed = 0
   corner_passed = 0
   img_min = cnt_img.min()
   img_max = cnt_img.max()
   img_avg = cnt_img.mean()
   img_diff = img_max - img_avg
   thresh = int(img_avg + (img_diff / 2))
   thresh = img_avg


   lc = cnt_img[0,0]
   brc = cnt_img[-1,-1]
   rc = cnt_img[0,-1]
   blc = cnt_img[-1,0]
   total = int(lc) + int(brc) + int(rc) + int(blc)
   avg = total / 4
   passed = 0
   if img_min > 0:
      if img_max / img_min > 1.5:
         brightness_passed = 1
      else:
         brightness_passed = 0

   # cnt in cnt test
   #_, threshold = cv2.threshold(cnt_img.copy(), thresh, 255, cv2.THRESH_BINARY)
   if cnt_w % 2 == 0:
      cnt_w = cnt_w + 1

   thresh_obj = 255 - cv2.adaptiveThreshold(cnt_img.copy(), 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, cnt_w, 3)
   thresh_obj = cv2.dilate(thresh_obj, None , iterations=4)

   (_, cnts, xx) = cv2.findContours(thresh_obj.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
   if len(cnts) == 1:
      #BLOB DETECT INSIDE CNT
      params = cv2.SimpleBlobDetector_Params()
      params.filterByArea = True
      params.filterByInertia = False
      #params.filterByConvexity = False
      params.filterByCircularity = True
      params.minCircularity= .5
      params.minArea = 1

      params.minThreshold = img_min + 5
      params.maxThreshold = 255
      params.filterByConvexity = True
      params.minConvexity = .95
      detector = cv2.SimpleBlobDetector_create(params)
      keypoints = detector.detect(cnt_img)
      hull = len(keypoints)
      cnt_found = 1
   else:
      hull = 999
      cnt_found = 0


   # corner test
   if (avg - 10 < lc < avg + 10) and (avg - 10 < brc < avg + 10) and (avg - 10 < rc < avg + 10) and (avg - 10 < blc < avg + 10):
      corner_passed = 1
   else:
      corner_passed = 0
   if hull == 1:
      shull = 1
   else:
      shull = 0
   mean_px_all = np.mean(cnt_img)
   mean_px_in = 0
   tmp_cnt = cnt_img.copy()

   if len(cnts) > 0:
      for (i,c) in enumerate(cnts):
            
         x,y,w,h = cv2.boundingRect(cnts[i])
         nx = int(x + (w/2))
         ny = int(y + (h/2))
         cv2.rectangle(cnt_show , (nx - 3, ny - 3), (nx + 3, ny + 3), (255, 255, 255), 1)
         bpt_img = cnt_img[ny-3:ny+3,nx-3:nx+3]
            
         mean_px_in = np.mean(bpt_img)
         tmp_cnt[ny-3:ny+3,nx-3:nx+3] = mean_px_all


   mean_px_all = np.mean(tmp_cnt)

   if mean_px_all > 0 and img_avg > 0:
      #or img_max / img_avg < 1.2:
      if mean_px_in / mean_px_all < 1.01 :
         # Failed brightness check
         brightness_passed = 0
      else:
         brightness_passed = 1
   else:
      brightness_passed = 0

   score = brightness_passed + corner_passed + cnt_found + shull

   #cv2.imshow("pepe", cnt_show)
   #cv2.waitKey(0)

   #if score >= 3:
      #cv2.imwrite("/mnt/ams2/tests/cnt" + str(frame_count) + "_" + str(cnt_cnt) + "-" + str(brightness_passed) + "-" + str(corner_passed) + "-" + str(cnt_found) + "-" + str(hull) + ".png", cnt_img)

   if score >= 3:
      return(1)
   else:
      return(0)


def new_obj_id(pt, moving_objects):
   x,y = pt
   if len(moving_objects) > 0:
      max_id = np.max(moving_objects, axis=0)
      new_id = max_id[0][0] + 1
   else:
      new_id = 1
   return(new_id)


def check_hist(x,y,hist):

   for (fn,hx,hy,hw,hh,hf) in hist:
      if hx - 35 <= x <= hx + 35 and hy - 35 <= y <= hy +35:
         return(1)
   return(0)

def stack_stack(image, stacked_image):
   h,w = image.shape
   for x in range(0,w-1):
      for y in range(0,h-1):
         sp = stacked_image[y,x]
         ip = image[y,x]
         if ip > sp:
            stacked_image_PIL[y,x] = image[y,x]
            #stacked_image[y,x] = image[y,x]

def stack_frames(frames):
   stacked_image = None   
   fc = 1
   for frame in frames:
      if stacked_image == None:
         stacked_image = frame
      stacked_image = stack_stack(frame, stacked_image)
      fc = fc + 1
   return(stacked_image)

def stack_image_PIL(pic1, pic2):
   if len(pic1.shape) == 3:
      pic1 = cv2.cvtColor(pic1, cv2.COLOR_BGR2GRAY)
   frame_pil = Image.fromarray(pic1)
   if pic2 is None:
      stacked_image = frame_pil 
#np.asarray(frame_pil)
   else: 
      stacked_image = pic2 

   stacked_image=ImageChops.lighter(stacked_image,frame_pil)
   return(stacked_image)

def find_color(oc):
   if oc == 0:
      colors = 255,0,0
   if oc == 1:
      colors = 0,255,0
   if oc == 2:
      colors = 0,0,255
   if oc == 3: 
      colors = 255,255,0
   if oc == 4: 
      colors = 255,255,255
   if oc >= 5:
      colors = 100,100,255
   
   return(colors)

def slope_test(hist, trim_file):
   slopes = []
   cc = 0

   #overall slope and dist for first and last
   first = hist[0][1], hist[0][2]
   last = hist[-2][1], hist[-1][2]

   o_slope = find_slope(first, last)
   o_dist = calc_dist(first, last)
   o_ang = find_angle(first, last)


 
   if len(hist) > 0:
      e_dist = o_dist / len(hist) 
   else:
      e_dist = 0
   spass = 0
   dpass = 0

   for line in hist:
      fn, x,y,w,h,fx = line 
      if cc > 0:
         slope = find_slope((last_x,last_y), (x,y))
         dist = calc_dist((last_x,last_y), (x,y))
         ang = find_angle((last_x,last_y), (x,y))
         if o_ang - 10 < ang < o_ang + 10:
            spass = spass + 1
         if e_dist - 5 < dist < e_dist+ 5:
            dpass = dpass + 1
         #print("SLOPE:", cc, slope,dist,ang,last_x,last_y,x,y)
         #print("SLOPE/DIST:", cc, slope, dist, dpass, spass)
         slopes.append(slope)
      last_x = x
      last_y = y

      cc = cc + 1
   hl = len(hist)
   hl = hl - 1
   if hl > 0:
      d_perc = dpass / hl
      s_perc = spass / hl
   else:
      d_perc = 0
      s_perc = 0

   if s_perc < .5 or d_perc < .5:
      print("FINAL SLOPE DIST TEST FAILED: ", trim_file)
      print("FINAL SLOPE DIST TEST FAILED: ", s_perc, d_perc)
      print("FINAL SLOPE DIST TEST FAILED: ", len(hist) - 1, spass, dpass)
      s_test = 0
   else:
      s_test = 1
      print("FINAL SLOPE DIST TEST PASSED: ", trim_file)
      print("FINAL SLOPE DIST TEST PASSED: ", s_perc, d_perc)
      print("FINAL SLOPE DIST TEST PASSED: ", len(hist) - 1, spass, dpass)

   return(s_test)

def test_object(object, trim_file, stacked_np):
   w,h = stacked_np.shape
   status = []
   # distance of object
   # object speed / pixels per frame
   # linear motion -- does the object move in the same direction
   # straight line -- do 3 or more points fit a line

   oid, start_x, start_y, hist = object
   print("HIST:", hist)
   hist = clean_hist(hist)
   print("CLEANHIST:", hist)
   
   sl_test = 0
   straight_line = 99
   slope = 0
   dist = 0
   last_x = 0
   last_y = 0
   min_x = w
   min_y = h
   max_x = 0  
   max_y = 0
   print ("HIST0:", hist)
   first = hist[0]
   last = hist[-1]
   p1 = first[1], first[2]
   p2 = last[1], last[2]
   #hist_len = len(object[3]) - 1
   hist_len = len(hist)
   elp_frms = last[0] - first[0]
   cns_mo = 0
   max_cns_mo = 0
   peaks = 0
   last_fn = None
   size_frame_test = 0
   max_size = 0

   if elp_frms > 0:
      elp_time = elp_frms / 25
   else:
      elp_time = 0


   # length test
   if hist_len < 2:
      len_test = 0
   else:
      len_test = 1

   # does the object pass consecutive motion test
   if elp_frms > 0:
      cm_test = (hist_len-1) / elp_frms
   else:
      cm_test = 0

   if hist_len < 5:
      cm_test = 1


   if hist_len > 2:
      slope = find_slope(p1,p2)
      print("DIST: ", p1,p2)
      dist = calc_dist(p1,p2)

   sizes = []
   if hist_len > 2:
      if hist_len > 3:
         ix = int(hist_len/2)
      else:
         ix = 1
      straight_line = compute_straight_line2(hist[0][1],hist[0][2],hist[ix][1],hist[ix][2],hist[-1][1],hist[-1][2])
      peaks = 0
      max_size = 0
      last_size = 0
      bigger = 0
      for line in hist:
         fn, x,y,w,h,fx = line 
         #print("WIDTH,HEIGHT:", w,h)
         if last_x > 0 and last_y > 0:
            seg_dist = calc_dist((last_x,last_y),(x,y))
            #print ("SEG DIST:", oid, seg_dist)
         size = w * h
         sizes.append(size)
         if w * h > max_size:
            max_size = w * h
         if size > last_size and bigger == 0:
            bigger = 1
         else:
            bigger = 0
         if x > max_x:
            max_x = x 
         if y > max_y:
            max_y = y  
         if x < min_x:
            min_x = x 
         if y < min_y:
            min_y = y
    

            
         if last_fn is not None:
            if fn - 1 == last_fn or fn -2 == last_fn:
               cns_mo = cns_mo + 1
               if cns_mo > max_cns_mo:
                  max_cns_mo = cns_mo
            else:
               if cns_mo > max_cns_mo:
                  max_cns_mo = cns_mo
               cns_mo = 0

         last_x = x
         last_y = y
         print(line)
         last_fn = fn
         last_size = size

   if max_cns_mo > 0:
      max_cns_mo = max_cns_mo + 1

   if max_cns_mo > 5:
      cm_test = 1

  
   if len(sizes) > 1:
      sci_peaks = signal.find_peaks(sizes)
      peaks = len(sci_peaks[0])
      print("SCI:", sci_peaks)
 
   if peaks > 0 and max_cns_mo > 0:
      peaks_to_frame_ratio = peaks / max_cns_mo
   else:
      peaks_to_frame_ratio = 0

   if peaks > 0 and dist > 0:
      peaks_to_dist_ratio = peaks / dist 
   else:
      peaks_to_dist_ratio = 0
   if max_size > 0 and peaks > 0:
      size_to_peak_ratio = max_size/ peaks
   else:
      size_to_peak_ratio = 0
     
 
   if elp_frms < 7 and max_size > 1500:
      print("Too big for too short of frames")
      size_frame_test = 0
   else:
      size_frame_test = 1

   if max_cns_mo > 0:
      px_per_frame = dist / max_cns_mo 
   else:
      px_per_frame = 0
   if max_cns_mo > 10:
      px_per_frame = dist / max_cns_mo

    
   meteor_yn = 0
   if cm_test > .5 and max_cns_mo >= 3 and px_per_frame >= .6 and dist >= 4 and straight_line < 5 and elp_time < 7 and peaks_to_frame_ratio <= .5 and peaks_to_dist_ratio < .45 and size_frame_test == 1:
      print("METEOR")
      meteor_yn = 1
      sl_test =slope_test(hist, trim_file)
   else:
      print("METEOR TEST FAILED.")
      print("SLOPE TEST: ", sl_test)
      #if sl_test == 0:
      #   meteor_yn = 0
   meteor_data = {}
   meteor_data['oid'] = oid[0]
   meteor_data['cm_test'] = cm_test
   meteor_data['max_cns_mo'] = max_cns_mo 
   meteor_data['len_test'] = len_test
   meteor_data['len_hist'] = len(hist)
   meteor_data['elp_time'] = elp_time
   meteor_data['elp_frms'] = elp_frms
   meteor_data['box'] = [min_x,min_y,max_x,max_y]
   meteor_data['dist'] = dist
   meteor_data['sl_test'] = sl_test
   meteor_data['peaks'] = peaks
   meteor_data['peaks_to_frame_ratio'] = peaks_to_frame_ratio
   meteor_data['peaks_to_dist_ratio'] = peaks_to_dist_ratio
   meteor_data['size_to_peak'] = size_to_peak_ratio
   meteor_data['first'] = first
   meteor_data['last'] = last
   meteor_data['hist'] = hist
   meteor_data['max_size'] = max_size 
   meteor_data['size_frame_test'] = size_frame_test
   meteor_data['straight_line'] = straight_line
   meteor_data['px_per_frame'] = px_per_frame
   meteor_data['meteor_yn'] = meteor_yn
   meteor_data['tests'] = {} 

   #if first[0] > 20 and cm_test > .5 and max_cns_mo >= 3 and px_per_frame >= .6 and dist >= 4 and straight_line < 5 and elp_time < 7 and peaks_to_frame_ratio <= .4 and peaks_to_dist_ratio <.4 and size_frame_test == 1:

   if first[0] > 20:
      meteor_data['tests']['early_frame'] = 1
   else:
      meteor_data['tests']['early_frame'] = 0
   if cm_test > .5:
      meteor_data['tests']['cm'] = 1
   else:
      meteor_data['tests']['cm'] = 0
   if max_cns_mo >= 3:
      meteor_data['tests']['max_cns_mo'] = 1
   else:
      meteor_data['tests']['max_cns_mo'] = 0
   if px_per_frame >= .6:
      meteor_data['tests']['px_per_frame'] = 1
   else:
      meteor_data['tests']['px_per_frame'] = 0
   if dist >= .6:
      meteor_data['tests']['dist'] = 1
   else:
      meteor_data['tests']['dist'] = 0
   if straight_line <= 5 :
      meteor_data['tests']['straight_line'] = 1
   else:
      meteor_data['tests']['straight_line'] = 0
   if elp_time < 7  :
      meteor_data['tests']['elp_time'] = 1
   else:
      meteor_data['tests']['elp_time'] = 0
   if peaks_to_frame_ratio <= .5 :
      meteor_data['tests']['peaks_to_frame_ratio'] = 1
   else:
      meteor_data['tests']['peaks_to_frame_ratio'] = 0
   if peaks_to_dist_ratio < .4 :
      meteor_data['tests']['peaks_to_dist_ratio'] = 1
   else:
      meteor_data['tests']['peaks_to_dist_ratio'] = 0
   meteor_data['tests']['size_frame_test'] = 1
   meteor_data['tests']['sl_test'] = sl_test


   print("\n-----------------")
   print ("Object ID: ", oid)
   print("-----------------")
   print ("CM Test: ", cm_test)
   print ("Cons Mo: ", max_cns_mo)
   print ("LEN Test: ", len_test, len(hist))
   print ("Elapsed Time: ", elp_time)
   print ("Elapsed Frames: ", elp_frms)
   print ("Dist: ", dist)
   print ("Peaks: ", peaks)
   print ("Peak To Frame Ratio: ", peaks_to_frame_ratio, peaks, "/", max_cns_mo, )
   print ("Peak To Dist Ratio: ", peaks_to_dist_ratio)
   print ("Size To Peak: ", size_to_peak_ratio)
   print ("First: ", first)
   print ("Last: ", last)
   print ("History:")
   for h  in hist:
      print("HIST:", h)
   print ("Slope: ", slope)
   print ("Max Size: ", max_size)
   print ("Size Frame Test: ", size_frame_test)
   print ("Straight: ", straight_line)
   print ("PX Per Frame: ", px_per_frame)
   print ("Meteor Y/N: ", meteor_yn)
   print("")
   for test in meteor_data['tests']:
      print("TEST:", test, meteor_data['tests'][test])
      #print(test, meteor_data[test])
   return(meteor_yn, meteor_data)


def compute_straight_line2(x1,y1,x2,y2,x3,y3):
   if x1 - x2 == 0 :
      x1 = x1 + 1
   if x3 - x2 == 0 :
      x3 = x3 + 1
   print("X", x1,x2,x3)
   print("Y", y1,y2,y3)
   diff = math.atan((y2-y1)/(x2-x1)) - math.atan((y3-y2)/(x3-x2))
   return(diff)

def compute_straight_line(x1,y1,x2,y2,x3,y3):
   print ("COMP STRAIGHT", x1,y1,x2,y2,x3,y3)
   if x1 - x2 != 0:
      a = (y1 - y2) / (x1 - x2)
   else:
      a = (y1 - y2) / 1
   if x1 - x3 != 0:
      b = (y1 - y3) / (x1 - x3)
   else:
      b = (y1 - y3) / 1 
   straight_line = a - b
   if (straight_line < 1):
      straight = "Y"
   else:
      straight = "N"
   return(straight_line)
 

def calc_dist(p1,p2):
   x1,y1 = p1
   x2,y2 = p2
   dist = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
   return dist

def find_angle(p1,p2):
   myrad = math.atan2(p1[1]-p2[1],p1[0]-p2[0]) 
   mydeg = math.degrees(myrad)
   return(mydeg)

def find_slope(p1,p2):
   (x1,y1) = p1
   (x2,y2) = p2
   top = y2 - y1
   bottom = x2 - y2
   if bottom != 0:
      slope = top / bottom
   else:
      slope = 0
   #print("SLOPE: TOP/BOTTOM ", top, bottom)
   #print(x1,y1,x2,y2,slope)
   return(slope)

    
def object_box(object, stacked_image_np):
   oid, start_x, start_y, hist = object
   im_h, im_w = stacked_image_np.shape
   max_x = 0
   max_y = 0
   min_x = im_w
   min_y = im_h
   for line in hist:
      fn, x,y,w,h,fx = line 
      mx = x + w
      my = y + h
      if my > max_y:
         max_y = my
      if y < min_y:
         min_y = y
      if mx > max_x:
         max_x = mx
      if x < min_x:
         min_x = x 
   
   max_x = max_x + 10
   max_y = max_y + 10
   min_x = min_x - 10
   min_y = min_y - 10
   if max_x > im_w:
      max_x = im_w
   if max_y > im_h:
      max_y = im_h 
   if min_x < 0:
      min_x = 0
   if min_y < 0:
      min_y = 0
   return(int(min_x), int(min_y), int(max_x),int(max_y))

def test_objects(moving_objects, trim_file, stacked_np):
   all_objects = []
   passed = 0
   for object in moving_objects:
      meteor_yn,meteor_data = test_object(object, trim_file, stacked_np)
      if meteor_yn == 1:
         passed = 1
      all_objects.append(meteor_data)
   return(passed, all_objects)
   

def complete_scan(trim_file, meteor_found, found_objects):
   setup_dirs(trim_file)
   el = trim_file.split("/")
   fn = el[-1]
   base_dir = trim_file.replace(fn,"")
   confirm_file = base_dir + "/data/" + fn
   confirm_file = confirm_file.replace(".mp4", "-confirm.txt")
   meteor_file = confirm_file.replace("-confirm.txt", "-meteor.txt")
   obj_fail = confirm_file.replace("-confirm.txt", "-objfail.txt")



   if meteor_found >= 1:
      print ("METEOR")
      mt = open(meteor_file, "w")
      mt.write(str(found_objects))
      mt.close()
      trim_meteor(meteor_file)
   else:
      print ("NO METEOR")
      mt = open(obj_fail, "w")
      mt.write(str(found_objects))
      mt.close()

      cmd = "./stack-stack.py stack_vid " + trim_file + " mv"
      os.system(cmd)



def draw_obj_image(stacked_image_np, moving_objects,trim_file, stacked_np):
   colors = None
   stacked_image_np_gray = stacked_image_np
   stacked_image_np = cv2.cvtColor(stacked_image_np, cv2.COLOR_GRAY2RGB)
   oc = 0
   for object in moving_objects:
    
      meteor_yn,meteor_data = test_object(object,trim_file, stacked_np)
      oid, start_x, start_y, hist = object
      if len(hist) - 1 > 1:
         colors = find_color(oc)
         #print("HIST:", oid, hist)
         min_x, min_y, max_x, max_y = object_box(object, stacked_image_np_gray) 
         cv2.rectangle(stacked_image_np, (min_x, min_y), (max_x, max_y), (255,255,255), 2)
         for line in hist:
            fn, x,y,w,h,fx = line 
            #print(x,y)
            dd = int(w / 2)
            #cv2.rectangle(stacked_image_np, (x, y), (x + 3, y + 3), (colors), 2)
            cv2.circle(stacked_image_np, (x,y), dd, (255), 1)
            #cv2.putText(stacked_image_np, str(oid),  (x,y), cv2.FONT_HERSHEY_SIMPLEX, .4, (colors), 1)
            if min_y < 100:
               cv2.putText(stacked_image_np, str(oid),  (min_x,min_y+15), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,0,255), 1)
            else:
               cv2.putText(stacked_image_np, str(oid),  (min_x,min_y- 15), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,0,255), 1)
         if meteor_yn == 1:
            print ("XYMETEOR:", min_x, min_y)
            if min_y < 100:
               cv2.putText(stacked_image_np, str("Meteor"),  (min_x,min_y+ 15), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,0,255), 1)
            else:
               cv2.putText(stacked_image_np, str("Meteor"),  (min_x,min_y- 5), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,0,255), 1)
         oc = oc + 1
 
   return(stacked_image_np)


def trim_meteor(trim_file, start_frame, end_frame):
   meteor_video_file = trim_file.replace(".mp4", "-meteor.mp4")
   # buffer start / end time
   # adjust meteor trim number for exact time computations? Needed to support more than 1 meteor per trim file...
   start_frame = int(start_frame)
   end_frame = int(end_frame)
   elp_frames = end_frame - start_frame 
   if start_frame > 25:
      start_frame = start_frame - 50
      elp_frames = elp_frames + 75
   else:
      start_frame = 0
      elp_frames = elp_frames + 75
   start_sec = start_frame / 25
   elp_sec = elp_frames/25
   print ("START FRAME: ", start_frame)
   print ("END FRAME: ", end_frame)
   print ("DUR FRAMES: ", elp_frames)
   print ("START SEC: ", start_sec)
   print ("DUR SEC: ", elp_sec)
   if start_sec <= 0:
      start_sec = 0
   if elp_sec <= 2:
      elp_sec = 3
   ffmpeg_trim(trim_file, start_sec, elp_sec, meteor_video_file)
   cmd = "./stack-stack.py stack_vid " + meteor_video_file + " mv"
   os.system(cmd)
   print("STACK", cmd)



def trim_meteor_old(meteor_file):
   print ("TRIM METEOR", meteor_file)
   #el = meteor_file.split("/")
   eld = meteor_file.split("-meteor")
   base = eld[0]
   trim_file = base.replace("data/", "")
   trim_file = trim_file + ".mp4"

   #trim_file = meteor_file.replace("-meteor.txt", ".mp4")
   #trim_file = trim_file.replace("data/", "")

   meteor_video_file = meteor_file.replace(".txt", ".mp4")
   meteor_video_file = meteor_video_file.replace("data/", "")
   file_exists = Path(meteor_video_file)
   if file_exists.is_file() == True:
      print ("ALREADY DONE.")
      return()

   print ("TRIM FILE:", trim_file)
   dur = check_duration(trim_file)
   print ("DUR: ", dur)
   if int(dur) < 5:
      print ("Duration is less than 5.", dur)
      cmd = "cp " + trim_file + " " + meteor_video_file
      print(cmd)
      os.system(cmd)

      cmd = "./stack-stack.py stack_vid " + trim_file + " mv"
      os.system(cmd)
      print("STACK", cmd)
      cmd = "./stack-stack.py stack_vid " + meteor_video_file + " mv"
      os.system(cmd)
      print("STACK", cmd)

      return()
   else:
      print ("Duration is more than 5 sec", dur)
   fdf = open(meteor_file)
   d = {}
   code = "object_data= "
   for line in fdf:
      code = code + line
   exec (code,  d)
   print(d['object_data'])
   for object in d['object_data']:
      #print(object[0], object[1], object[2],object[3],object[8])
      print("OBJ8:", object[8])
      if len(object[8]) == 0:
         # meteor found
         print("meteor found", object[2], object[3])
         start_frame = object[2][0]
         end_frame = object[3][0]
         elp_frames = end_frame - start_frame
         if start_frame > 25:
            start_frame = start_frame - 50
            elp_frames = elp_frames + 75
         else:
            start_frame = 0
            elp_frames = elp_frames + 75
         start_sec = start_frame / 25
         elp_sec = elp_frames/25
         print ("START FRAME: ", start_frame)
         print ("END FRAME: ", end_frame)
         print ("DUR FRAMES: ", elp_frames)
         print ("START SEC: ", start_sec)
         print ("DUR SEC: ", elp_sec)
         if start_sec <= 0:
            start_sec = 0
         if elp_sec <= 2:
            elp_sec = 3
         ffmpeg_trim(trim_file, start_sec, elp_sec, meteor_video_file)
         cmd = "./stack-stack.py stack_vid " + trim_file + " mv"
         os.system(cmd)
         print("STACK", cmd)
         cmd = "./stack-stack.py stack_vid " + meteor_video_file + " mv"
         os.system(cmd)
         print(cmd)


def check_duration(trim_file):
   cmd = "/usr/bin/ffprobe " + trim_file + ">checks.txt 2>&1"
   print (cmd)
   s= 0
   try:
      output = subprocess.check_output(cmd, shell=True).decode("utf-8")
      efp = open("checks.txt")
      stream_found = 0
      for line in efp:
         if "Duration" in line:
            el = line.split(" ")
            dur_str = el[3]
            dur, rest = dur_str.split(".")
            h,m,s = dur.split(":")
            print(int(s))
   except:
      print("DUR CHECK FAILED")
      s = 0
   return(s)

def check_if_done(video_file):
   el = video_file.split("/")
   fn = el[-1]
   bd = video_file.replace(fn, "")
   fn = fn.replace(".mp4", "")
   meteor_file = bd + "data/" + fn + "-meteor.txt"
   objfail = bd + "data/" + fn + "-objfail.txt"
   confirm = bd + "data/" + fn + "-confirm.txt"
   reject = bd + "data/" + fn + "-reject.txt"
   file_exists = Path(meteor_file)
   if file_exists.is_file() is True:
      return(1)
   file_exists = Path(objfail)
   if file_exists.is_file() is True:
      return(1)
   file_exists = Path(confirm)
   if file_exists.is_file() is True:
      return(1)
   file_exists = Path(reject)
   if file_exists.is_file() is True:
      return(1)
   print(meteor_file)
   print(objfail)
   print(confirm)
   print(reject)
   return(0)

def check_final_stack(trim_stack, object):
   min_x, min_y, max_x, max_y = object['box']
   print("MIN/MAX:",min_x,min_y,max_x,max_y)
   trim_stack_np = np.asarray(trim_stack)
   crop_img = trim_stack_np[min_y:max_y,min_x:max_x] 

   max_px = np.max(crop_img)
   mean_px = np.mean(crop_img)
   max_diff = max_px - mean_px
   thresh = max_px - (max_diff/2)

   _, thresh_img = cv2.threshold(crop_img, thresh, 255, cv2.THRESH_BINARY)
   #thresh_obj = cv2.dilate(thresh_img.copy(), None , iterations=1)
   #(_, cnts, xx) = cv2.findContours(thresh_obj.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
   #print("LEN CNTS:", len(cnts))
   cv2.imshow("pepe", crop_img)
   cv2.waitKey(1)
   cv2.imshow("pepe", thresh_img)
   cv2.waitKey(1)
