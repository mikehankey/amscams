from scipy import signal
from PIL import Image
import os
import math
import operator
import datetime
from lib.FileIO import load_json_file, save_json_file, cfe
import numpy as np
import cv2
from lib.UtilLib import calc_dist, better_parse_file_date, bound_cnt, convert_filename_to_date_cam
from lib.VideoLib import load_video_frames , get_masks, make_movie_from_frames
from lib.ImageLib import adjustLevels , mask_frame, median_frames, stack_stack
from lib.UtilLib import find_slope 
from lib.CalibLib import radec_to_azel, clean_star_bg, get_catalog_stars, find_close_stars, XYtoRADec, HMS2deg, AzEltoRADec

import scipy.optimize

def get_hdm_xy(sd_video_file = None, frame = None, json_conf = None):
   if frame is not None:
      ih, iw = frame.shape[:2]
      hdm_x = 1920 / iw
      hdm_y = 1080 / ih
   if sd_video_file is not None:
      from lib.VideoLib import load_video_frames
      frames = load_video_frames(sd_video_file, json_conf, 2)
      frame = frames[0]
      ih, iw = frame.shape[:2]
      hdm_x = 1920 / iw
      hdm_y = 1080 / ih

   return(hdm_x, hdm_y)   

def stack_frames(frames):
   stacked_image = None

   for frame in frames:
      frame_pil = Image.fromarray(frame)
      if stacked_image is None:
         stacked_image = stack_stack(frame_pil, frame_pil)
      else:
         stacked_image = stack_stack(stacked_image, frame_pil)
   return(np.asarray(stacked_image))


def update_intensity(metframes, sd_frames,show = 0):
   base_img = sd_frames[0].copy()
   for fn in metframes:
      sd_img = sd_frames[fn].copy()
      if "sd_w" in metframes[fn]:
         w = metframes[fn]['sd_w']
         h = metframes[fn]['sd_h']
      else:
         w = metframes[fn]['w']
         h = metframes[fn]['h']
      if "sd_x" in metframes[fn]:
         x = metframes[fn]['sd_x']
         y = metframes[fn]['sd_y']
         base_cnt_img = base_img[y:y+h,x:x+w]
         cnt_img = sd_img[y:y+h,x:x+w]
         min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(cnt_img)

         print("INTENSITY:", fn, x, y, np.sum(cnt_img) , np.sum(base_cnt_img) )
         metframes[fn]['sd_intensity'] = float(np.sum(cnt_img)) - float(np.sum(base_cnt_img))
         metframes[fn]['sd_max_px'] = float(max_val)
         metframes[fn]['sd_max_x'] = float(mx) + x
         metframes[fn]['sd_max_y'] = float(my) + y
         print("Intensity:",  metframes[fn]['sd_intensity'])
      else:
         print("Frame is missing:", fn)
   return(metframes)    

def make_light_curve(metframes,sd_video_file):
   iis = []
   fns = []
   for fn in metframes:
      print(fn, metframes[fn])
      if "sd_intensity" in metframes[fn]:
         iis.append(int(metframes[fn]['sd_intensity']))
         fns.append(int(fn))

   import matplotlib
   matplotlib.use('Agg')
   import matplotlib.pyplot as plt
   #fig = plt.figure()
   print(fns,iis)
   plt.plot(fns,iis)
   curve_file = sd_video_file.replace(".mp4", "-lightcurve.png")
   plt.savefig(curve_file)


def find_best_match(matches, cnt, objects):
   # eval the following things. 
   # - distance from object
   # - slope from start in relation to current point 
   # - brightness of object? 
   # - if the original object is moving or not? 
   # - the last size of the object and the current size? 

   mscore = {}
   bscore = {}
   for match in matches:
      xs = []
      ys = []
      for hs in match['history']:
         oid = match['oid']
         if len(hs) == 9:
            fn,x,y,w,h,mx,my,max_px,intensity = hs
         if len(hs) == 8:
            fn,x,y,w,h,mx,my,max_px = hs
         xs.append(x)
         ys.append(y)
      m,b = best_fit_slope_and_intercept(xs,ys)
      cntx,cnty,cntw,cnth = cv2.boundingRect(cnt)
      cnt_cx,cnt_cy = center_point(cntx,cnty,cntw,cnth)
      txs = [xs[0], cnt_cx]
      tys = [ys[0], cnt_cy]
      tm,tb = best_fit_slope_and_intercept(txs,tys)
      mscore[oid] = abs(tm-m)
      bscore[oid] = abs(tb-b)
      print("M,B for this object is: ", m,b,tm,tb)
   best_mids = sorted(mscore.items(), key=operator.itemgetter(1))
   best_bids = sorted(bscore.items(), key=operator.itemgetter(1))
   best_mid = best_bids[0][0]
   for obj in matches:
      #print("OBJ:", obj['oid'], best_mid)
      if int(obj['oid']) == int(best_mid):
         return(obj)

def build_thresh_frames(sd_frames):
   thresh_frames = []
   for frame in sd_frames:
      hd_img = frame
      if len(hd_img.shape) == 3:
         gray_frame = cv2.cvtColor(hd_img, cv2.COLOR_BGR2GRAY)
         gray_frame = cv2.convertScaleAbs(gray_frame)
      else:
         gray_frame = hd_img
      #frames.append(hd_img)

      # do image acc / diff
      blur_frame = cv2.GaussianBlur(frame, (7, 7), 0)
      level_frame = adjustLevels(blur_frame, 30,1,255)
      level_frame = cv2.convertScaleAbs(level_frame)
      gray_frame = level_frame

      #if image_acc is None:
      #   image_acc = np.float32(gray_frame)

      #alpha = .1
      #hello = cv2.accumulateWeighted(gray_frame, image_acc, alpha)

      #image_diff = cv2.absdiff(image_acc.astype(gray_frame.dtype), gray_frame,)
      #first_image_diff = cv2.absdiff(first_gray_frame.astype(gray_frame.dtype), gray_frame,)
      #image_diff = first_image_diff

      #thresh = np.max(image_diff) * .95
      ithresh = np.max(gray_frame) * .8
      #if thresh < 20:
      #   thresh = 20
      _, image_thresh = cv2.threshold(gray_frame.copy(), ithresh, 255, cv2.THRESH_BINARY)
      #show_img2 = cv2.resize(cv2.convertScaleAbs(image_thresh), (960,540))
      thresh_frames.append(image_thresh)
   return(thresh_frames)

def clean_object(obj):
   # remove duplicate cnts
   # if more than one cnt exists for a given frame, pick the one that is farthest from 1st frame
   # if cnts are not moving in the desired direction remove them
   last_fn = None
   first_fn = None
   first_x = None

   frame_data = {}

   for hs in obj['history']:
      fn,x,y,w,h,mx,my,max_px,intensity = hs
      frame_data[fn] = {}
      frame_data[fn]['cnts'] = []
      if first_x is None:
         first_x = x
         first_y = y
         first_fn = fn
      if last_fn is not None:
         if last_fn == fn:
            frame_data[fn]['cnts'].append(hs)
         else:
            frame_data[fn]['cnts'].append(hs)
      last_fn = fn

   clean_hist = []
   for fn in frame_data:
      if len(frame_data[fn]['cnts']) > 1:
         best_cnt = pick_best_cnt(frame_data[fn]['cnts'], first_x, first_y)
         clean_hist.append(best_cnt)
      else:
         if len(frame_data[fn]['cnts']) > 0:
            clean_hist.append(frame_data[fn]['cnts'][0])

   first_fn = None
   last_c_dist = None

   best_hist = []

   for hs in clean_hist:
      dist_bad = 0
      fn,x,y,w,h,mx,my,max_px,intensity = hs
      if first_fn is None:
         first_fn = fn
         first_x = x
         first_y = y
      else:
         c_dist = calc_dist((x,y),(first_x,first_y))
         if last_c_dist is not None:
            c_dist_diff = c_dist - last_c_dist
            #print("C DIST DIFF:", fn, c_dist_diff)
            if c_dist_diff <= 0:
               dist_bad = 1
      
         last_c_dist = c_dist 
      if dist_bad == 0:
         #print("BEST CNT:", hs)
         best_hist.append(hs)

   obj['history'] = best_hist
   return(obj)

def pick_best_cnt(cnts, first_x, first_y):
   max_dist = 0
   for hs in cnts:
      fn,x,y,w,h,mx,my,max_px,intensity = hs
      c_dist = calc_dist((x,y),(first_x,first_y))
      if c_dist > max_dist:
         max_dist = c_dist
         best_cnt = hs
   return(best_cnt)
 

def find_blob_center(frame, x,y,max_val):
   h,w = frame.shape
   size=100
   x1,y1,x2,y2 = bound_cnt(x,y,w,h,size)
   crop_img = frame[y1:y2,x1:x2]
   _, image_thresh = cv2.threshold(crop_img.copy(), max_val - 10, 255, cv2.THRESH_BINARY)
   cnt_res = cv2.findContours(image_thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

   if len(cnt_res) == 3:
      (_, cnts, xx) = cnt_res
   elif len(cnt_res) == 2:
      (cnts, xx) = cnt_res
   pos_cnts = []
   real_cnts = []
   xs = []
   ys = []
   ws = []
   hs = []
   if len(cnts) > 0:
      for (i,c) in enumerate(cnts):
         x,y,w,h = cv2.boundingRect(cnts[i])
         x = int(x + (w/2))
         y = int(y + (h/2))
         if w > 1 and h > 1:
            cv2.circle(crop_img,(x,y), 5, (255), 1)
            xs.append(x)
            ys.append(y)
            ws.append(w)
            hs.append(w)

   if len(xs) > 0:
      mean_x = int(np.mean(xs)) 
      mean_y = int(np.mean(ys)) 
      mean_w = int(np.mean(ws))
      mean_h = int(np.mean(hs))
   else: 
      mean_x = 0
      mean_y = 0
      mean_w = 0
      mean_h = 0
   cv2.circle(crop_img,(mean_x,mean_y), mean_w, (255), 1)
   print("CNTS:", pos_cnts)
   #cv2.imshow('pepe', crop_img)
   #cv2.waitKey(100)
   return(mean_x+x1,mean_y+y1,mean_w,mean_h)


 
def detect_bp(video_file,json_conf, retrim=0) :
   objects = []
   hd_datetime, hd_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(video_file)      
   masks = get_masks(hd_cam,json_conf)
   if cfe(video_file) == 0:
      print("This file does not exist!")
      exit()

   print("Bright pixel detection.")
   sd_frames = load_video_frames(video_file, json_conf, 0, 0, [], 1)
   cm = 0
   nomo = 0
   motion = 0
   masked_frames = []
   mask_points = []
   last_frame = cv2.cvtColor(sd_frames[0], cv2.COLOR_BGR2GRAY)
   h,w = last_frame.shape
   img_w = w
   img_h = h
   stack_img = np.zeros((h,w),dtype=np.uint8)
   fn = 0
   events = []
   frame_data = {}
   orig_frames = []
   stacks = []
   subframes = []
   max_vals = []
   last_x = None
   last_y = None

   for frame in sd_frames:
      orig_frames.append(frame.copy())
      frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
      frame = mask_frame(frame, [], masks,5)

      frame_data[fn] = {}
      frame_data[fn]['fn'] = fn
      blur_frame = cv2.GaussianBlur(frame, (7, 7), 0)
      blur_last = cv2.GaussianBlur(last_frame, (7, 7), 0)
      subframe = cv2.subtract(frame,last_frame)
      subframes.append(subframe)
      #cv2.imshow('pepe', subframe)
      #cv2.waitKey(120)

      avg_val = np.mean(frame)
      sum_val = np.sum(subframe)
      min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(subframe) 
      frame_data[fn]['avg_val'] = float(avg_val)
      frame_data[fn]['min_val'] = float(min_val)
      frame_data[fn]['max_val'] = float(max_val)
      frame_data[fn]['sum_val'] = float(sum_val)
      frame_data[fn]['mx'] = int(mx)
      frame_data[fn]['my'] = int(my)
      last_frame = frame
      #cv2.imshow("pepe", subframe)
      print("MAX VAL: ", max_val, avg_val, max_val - avg_val)
      if max_val - avg_val > 10:
         motion = 1
         print("DETECTION!:")
         if motion == 1:
            if cm == 0:
               print("START FIRST EVENT.")
               first_eframe = fn -1 
            cm = cm + 1
            object, objects = id_object(None, objects,fn, (int(mx),int(my)), int(max_val), int(sum_val), img_w, img_h)
            if "oid" in frame_data[fn]:
               frame_data[fn]['oid'] = object['oid']
            if "oid" in object:
               print("OBJECT:", object['oid'])


         blob_x, blob_y,blob_w,blob_h = find_blob_center(frame, mx,my,max_val)
         avg_x = int(blob_x + mx / 2)
         avg_y = int(blob_y + my / 2)
         #cv2.circle(stack_img,(avg_x,avg_y), 20, (255), -1)

         frame_data[fn]['blob_x'] = int(blob_x)
         frame_data[fn]['blob_y'] = int(blob_y)
         frame_data[fn]['blob_w'] = int(blob_w)
         frame_data[fn]['blob_h'] = int(blob_h)

         #cv2.circle(stack_img,(blob_x,blob_y), blob_w, (255), -1)
         if last_x is not None:
            #print("LINE:", blob_x, blob_y, last_x, last_y)
            cv2.line(stack_img, (blob_x,blob_y), (last_x,last_y), (255), 2)
            cv2.line(stack_img, (mx,my), (last_x,last_y), (255), 2)


         max_vals.append(max_val) 
         #if cm >= 1:
            #print(fn, max_val - avg_val, cm)
            #cv2.waitKey(100)
         nomo = 0
      else:
         #cv2.waitKey(10)
         if cm >= 2 and nomo >=2 :
            print("Add Event.")
            events.append([first_eframe, fn])
            stacks.append(stack_img)
            stack_img = np.zeros((h,w),dtype=np.uint8)
            motion = 0
            cm = 0
         if cm == 1 and nomo > 3:
            cm = 0
         nomo = nomo + 1
         blob_x = None
         blob_y = None
      frame_data[fn]['cm'] = cm
      frame_data[fn]['nonmo'] = nomo
      print(fn, max_val, cm, nomo)
      fn = fn + 1
      if blob_x is not None:
         last_x = blob_x
         last_y = blob_y
      else:
         last_x = mx
         last_y = my
      
   if cm >= 2 :
      print("Add Final Event.")
      events.append([first_eframe, fn])
      stacks.append(stack_img)
      motion = 0
     
   print("FRAMES:", len(sd_frames))
   print("BP EVENTS:", len(events))

   event_data = {}
   event_data['frame_data'] = frame_data
   event_data['events'] = events
   if len(events) > 0:
      print("Events detected.")
      event_file = video_file.replace(".mp4", "-events.json")
   else:
      print("No events detected.")
      event_file = video_file.replace(".mp4", "-noevents.json")

   my_lines = []
   event_data['objects'] = objects
   save_json_file(event_file, event_data)
   ec = 0


   if len(events) == 0:
      if "proc2" in video_file and "trim" in video_file:
         print("NO DETECTS MOVE TO FAIL!")
         ddd = video_file.split("/")
         dfn = ddd[-1]
         proc_dir = video_file.replace(dfn, "")
         cmd = "mv " + video_file + " " + proc_dir + "failed/"
         print("COMMAND:", cmd)
         os.system(cmd)


   print("EVENTS:", events)
   for ev in events:
      stack_img = stacks[ec]
      real_stack_img = stack_frames(subframes[ev[0]:ev[1]])
      thresh_val = min(max_vals) 
      _, image_thresh = cv2.threshold(real_stack_img.copy(), thresh_val, 255, cv2.THRESH_BINARY)

      #cv2.imshow("pepe", real_stack_img)
      #cv2.waitKey(100)
      #cv2.imshow("pepe", image_thresh)
      #cv2.waitKey(100)

      image_thresh_dil = cv2.dilate(image_thresh, None , iterations=1)
      image_thresh_dil = cv2.convertScaleAbs(image_thresh_dil)

      #my_lines = hough_lines(stack_img)
      ec = ec + 1
   my_lines = []
   print(my_lines)

   #hd_datetime, hd_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(video_file)      
   orig_fn = video_file.split("/")[-1]
   out_dir = video_file.replace(orig_fn, "")

   retrim = 1
   if retrim == 1:
      print("RETRIM")
      for start_frame, end_frame in events:
         status = test_frame_seq(start_frame, end_frame, frame_data, sd_frames)
         if status == 1:
            (start_frame, end_frame, start_buff, end_buff, orig_trim_num)  = get_new_trim_num(start_frame, end_frame ,len(sd_frames), video_file)


            new_trim_num = start_frame + orig_trim_num
            new_fn = out_dir + "/" + hd_y + "_" + hd_m + "_" + hd_d + "_" + hd_h + "_" + hd_d + "_" + hd_M + "_" + hd_s + "_000_" + hd_cam + "-TRIM-" + str(new_trim_num) + ".mp4"
            new_json = new_fn.replace(".mp4", ".json")
            new_json_data = {}
            new_json_data['frame_data'] = frame_data
            new_json_data['hough_lines'] = my_lines
            save_json_file(new_json, new_json_data)

            print("NEW:", new_fn)
            fns = []
            for i in range(start_frame, end_frame):
               fns.append(i)
            make_movie_from_frames(orig_frames, fns, new_fn)
            print("FRAMES:", fns)
            print("NEW OUT:", new_fn)
            # New TRIM file has been created. Let's move the old one.
            if "proc2" in video_file and "trim" in video_file:
               new_new_fn = new_fn.replace("TRIM", "trim")
               ddd = video_file.split("/")
               dfn = ddd[-1]
               proc_dir = video_file.replace(dfn, "")
               cmd = "mv " + video_file + " " + proc_dir + "/failed/"
               print(cmd)
               #os.system(cmd)
               cmd = "mv " + new_fn + " " + proc_dir + "/" + new_new_fn
               print(cmd)
               #os.system(cmd)
            
            exit()
         else:
            new_trim_num = 0
            new_fn = out_dir + "/" + hd_y + "_" + hd_m + "_" + hd_d + "_" + hd_h + "_" + hd_d + "_" + hd_M + "_" + hd_s + "_000_" + hd_cam + "-TRIM-" + str(new_trim_num) + ".mp4"
            new_json = new_fn.replace(".mp4", ".json")
            new_json_data = {}
            new_json_data['frame_data'] = frame_data
            new_json_data['hough_lines'] = my_lines
            if "proc2" in video_file and "trim" in video_file:
               print("NO METEOR DETECTS MOVE TO FAIL!")
               new_new_fn = new_fn.replace("TRIM", "trim")
               ddd = video_file.split("/")
               dfn = ddd[-1]
               proc_dir = video_file.replace(dfn, "")
               cmd = "mv " + video_file + " " + proc_dir + "/failed/"
               print(cmd)
               #os.system(cmd)
               cmd = "mv " + new_fn + " " + proc_dir + "/" + new_new_fn
               print(cmd)
               #os.system(cmd)

   

def hough_lines(image):

   #edges = cv2.Canny(image,50,150,apertureSize = 3)
   edges = image
   minLineLength = 2 
   maxLineGap = 20
   h,w = image.shape
   hough_img = np.zeros((h,w),dtype=np.uint8)
   hough_img = cv2.cvtColor(hough_img,cv2.COLOR_GRAY2RGB)
   lines = cv2.HoughLinesP(edges,1,np.pi/180,50,np.array([]),minLineLength,maxLineGap)
   x1s = [] 
   y1s = [] 
   x2s = [] 
   y2s = [] 
   mylines = []
   if lines is not None:
      for line in lines:
         for x1,y1,x2,y2 in line:
            cv2.line(hough_img,(x1,y1),(x2,y2),(255,0,0),1)
            x1s.append(x1)
            x2s.append(x2)
            y1s.append(y1)
            y2s.append(y2)
            mylines.append(((int(x1),int(y1)),(int(x2),int(y2))))
   
   if len(x1s) > 0:
      mx1 = int(np.median(x1s))
      my1 = int(np.median(y1s))
      mx2 = int(np.median(x2s))
      my2 = int(np.median(y2s))
   
   #cv2.imshow("pepe", hough_img)
   #cv2.waitKey(100)

   return(mylines)

def test_frame_seq(start_frame, end_frame, frame_data, sd_frames):
   status = 1
   dur = end_frame - start_frame
   xs = []
   ys = []
   cms = []
   for i in range (start_frame, end_frame):
      xs.append(frame_data[i]['mx'])
      ys.append(frame_data[i]['my'])
      cms.append(frame_data[i]['cm'])

   max_cm = np.max(cms)
   max_x = np.max(xs)
   max_y = np.max(ys)
   min_x = np.min(xs)
   min_y = np.min(ys)
   print("TEST:", start_frame, end_frame)
   print("MAX XY:", max_x, max_y)
   print("MIN XY:", min_x, min_y)
   print("MAX CM:", max_cm)
   print("DUR:", dur)
   cm_dur_ratio = max_cm / dur
   if cm_dur_ratio < .5:
      print("NON METEOR.")
      status = 0
   else:
      print("METEOR.")
      status = 1
   return(status)

def get_new_trim_num(start_frame, end_frame, total_frames, sd_video_file):
   if "trim" in sd_video_file and "HD" not in sd_video_file:
      el = sd_video_file.split("-trim")
      min_file = el[0] + ".mp4"
      ttt = el[1].split(".")
      orig_trim_num = int(ttt[0])
   elif "HD-meteor" in sd_video_file: 
      el = sd_video_file.split("-trim")
      ttt = el[1].split("-")
      orig_trim_num = int(ttt[1])

   else:
      orig_trim_num = 0


   if start_frame - 10 > 0:
      first_frame = start_frame - 10
      start_buff = 10
   if end_frame + 10 <= total_frames-1:
      last_frame = end_frame + 10
      end_buff = 10
   if start_frame - 25 > 0:
      first_frame = start_frame - 25
   if last_frame + 25 <= total_frames:
      last_frame = end_frame + 25

   return(first_frame, last_frame, start_buff, end_buff, orig_trim_num) 
 
           

def detect_from_bright_pixels(masked_frames, show = 0):
   max_vals = []
   avg_vals = []
   px_diffs = []
   objects = []
   for gray_frame in masked_frames:
      mxv = np.max(gray_frame)
      avgv = np.mean(gray_frame)
      #print("MAX/AVG VAL:", mxv, avgv, mxv - avgv)
      max_vals.append(mxv)
      avg_vals.append(avgv)
      px_diffs.append(mxv-avgv)

   master_marked_image = masked_frames[0].copy()
   avg_pxd = np.mean(px_diffs)  
   avg_val = np.mean(avg_vals)  
   for i in range(0,len(px_diffs)-1):
      marked_image = masked_frames[i]
      px_increase = px_diffs[i] / avg_pxd 
      if px_increase > 1.25: 
         min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(masked_frames[i])
         #print("PXI:", i, max_vals[i], px_diffs[i], px_increase, mx,my)
         ithresh=max_vals[i] * .95
         if ithresh < 20:
            ithresh = 20
         _, image_thresh = cv2.threshold(masked_frames[i].copy(), ithresh, 255, cv2.THRESH_BINARY)
         cnts,pos_cnts = find_contours(image_thresh, gray_frame)
         if len(cnts) == 0:
            ithresh=max_vals[i] * .9
            _, image_thresh = cv2.threshold(masked_frames[i].copy(), ithresh, 255, cv2.THRESH_BINARY)
            cnts,pos_cnts = find_contours(image_thresh, gray_frame)
            if len(cnts) == 0:
               ithresh=max_vals[i] * .85
               _, image_thresh = cv2.threshold(masked_frames[i].copy(), ithresh, 255, cv2.THRESH_BINARY)
               cnts,pos_cnts = find_contours(image_thresh, gray_frame)
               if len(cnts) == 0:
                  ithresh=max_vals[i] * .80
                  _, image_thresh = cv2.threshold(masked_frames[i].copy(), ithresh, 255, cv2.THRESH_BINARY)
                  cnts,pos_cnts = find_contours(image_thresh, gray_frame)
                  if len(cnts) == 0:
                     ithresh=max_vals[i] * .75
                     _, image_thresh = cv2.threshold(masked_frames[i].copy(), ithresh, 255, cv2.THRESH_BINARY)
                     cnts,pos_cnts = find_contours(image_thresh, gray_frame)
                     if len(cnts) == 0:
                        ithresh=max_vals[i] * .70
                        _, image_thresh = cv2.threshold(masked_frames[i].copy(), ithresh, 255, cv2.THRESH_BINARY)
                        cnts,pos_cnts = find_contours(image_thresh, gray_frame)
         for cnt in cnts:
            x,y,w,h = cv2.boundingRect(cnt)
            cnt_img = masked_frames[i][y:y+h,x:x+w]
            intensity = np.sum(cnt_img)
            object, objects = id_object(cnt, objects,i, (mx,my), max_val, intensity, 0)
            #cv2.rectangle(marked_image, (x, y), (x+w, y+h), (128), 1)
            cv2.rectangle(master_marked_image, (x, y), (x+w, y+h), (128), 1)
      if show == 1:
         cv2.imshow('Bright Pixel Detect', master_marked_image)
         cv2.waitKey(30)

   meteors = []
   for obj in objects:
      obj = clean_object(obj)
      print("CLEAN OBJECT:", obj)
      


      obj['debug'] = "Hist len: " + str(obj['hist_len']) + " Straight: " + str(obj['is_straight']) + " Dist: " + str(obj['dist']) + " Max CM:" + str(obj['max_cm']) + " Gaps: " + str(obj['gaps']) + " Gap Events: " + str(obj['gap_events']) + " Gap frame ratio:" + str(obj['cm_hist_len_ratio'])
 
      if obj['dist'] > 0 and obj['max_cm'] > 2:
         # object is a meteor!?!
         print(obj['oid'], obj['debug'])
         meteors.append(obj)
      for hs in obj['history']:
         x = hs[1]
         y = hs[2]
         w = hs[3]
         h = hs[4]
         #cv2.rectangle(marked_image, (x, y), (x+w, y+h), (128), 1)
      if show == 1:
         cv2.imshow('Bright Pixel Detect', marked_image)
         cv2.waitKey(30)
   
   return(meteors)

def detect_from_thresh_diff(masked_frames, show = 0):
   print("Detect from thresh.")
   first_gray_frame = None
   image_acc = None
   last_image_thresh = None
   objects = []
   fc = 0
  
   master_marked_image = masked_frames[0] 
   for gray_frame in masked_frames:
      # do image acc / diff
      blur_frame = cv2.GaussianBlur(gray_frame, (7, 7), 0)
      level_frame = adjustLevels(blur_frame, 50,1,255)
      level_frame = cv2.convertScaleAbs(level_frame)
      gray_frame = level_frame

      if first_gray_frame is None:
         first_gray_frame = gray_frame

      if image_acc is None:
         image_acc = np.float32(gray_frame)

      alpha = .1
      hello = cv2.accumulateWeighted(gray_frame, image_acc, alpha)

      image_diff = cv2.absdiff(image_acc.astype(gray_frame.dtype), gray_frame,)
      first_image_diff = cv2.absdiff(first_gray_frame.astype(gray_frame.dtype), gray_frame,)
      image_diff = first_image_diff

      thresh = np.max(image_diff) * .95
      ithresh = np.max(gray_frame) * .5
      if thresh < 20:
         thresh = 20

      _, image_thresh = cv2.threshold(gray_frame.copy(), ithresh, 255, cv2.THRESH_BINARY)
      if last_image_thresh is not None:
         image_thresh_diff = cv2.absdiff(image_thresh.astype(gray_frame.dtype), last_image_thresh,)
      else:
         image_thresh_diff = image_thresh

      _, diff_thresh = cv2.threshold(image_diff.copy(), thresh, 255, cv2.THRESH_BINARY)
      #show_img2 = cv2.resize(cv2.convertScaleAbs(image_thresh_diff), (960,540))

      # find contours and ID objects
      diff_thresh = image_thresh
      cnts,pos_cnts = find_contours(diff_thresh, gray_frame)
      #if len(pos_cnts) > 1:
      #   _, diff_thresh = cv2.threshold(image_diff.copy(), 30, 255, cv2.THRESH_BINARY)
      #   cnts,pos_cnts = find_contours(diff_thresh, gray_frame)

      ic = 0
      marked_image = gray_frame.copy()


      print("CNTS:", len(cnts))
  
      for cnt in cnts:
         x,y,w,h,size,mx,my,max_val,intensity = pos_cnts[ic]
         object, objects = id_object(cnt, objects,fc, (mx,my), max_val, intensity, 0)
         print(object)
         if "oid" in object:
            name = str(object['oid'])
            cv2.putText(marked_image, name ,  (x-5,y-12), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
         cv2.rectangle(master_marked_image, (x, y), (x+w, y+h), (128), 1)

         ic = ic + 1
      if show == 1:
         cv2.imshow('Detect From Thresh Diff', master_marked_image)
         cv2.waitKey(30)
      fc = fc + 1
      print("FRAME:", fc)
   meteors = []
   for obj in objects:
      obj = clean_object(obj)
      points = hist_to_points(obj['history'])
      print("POINTS:", points) 
      obj['is_straight'] = arecolinear(points)
      obj['max_cm'],obj['gaps'],obj['gap_events'],obj['cm_hist_len_ratio'] = meteor_test_cm_gaps(obj)
      
      print("DETECT FROM THRESH:", obj)
      meteor_score = test_for_meteor(obj) 
      if meteor_score >= 4:
         meteors.append(obj)

   return(meteors) 

def test_for_meteor(obj):
   obj['sci_peaks'], obj['peak_to_frame'] = meteor_test_peaks(obj)
   obj['max_cm'],obj['gaps'],obj['gap_events'],obj['cm_hist_len_ratio'] = meteor_test_cm_gaps(obj)
   obj['moving'],obj['moving_desc'] = meteor_test_moving(obj['history'])
   points = hist_to_points(obj['history'])
   obj['is_straight'] = arecolinear(points)

   meteor_score = 0
   if obj['is_straight'] is True:
      meteor_score = meteor_score + 2
      print("PLUS 2 for STRAIGHT!", meteor_score)
   if obj['moving'] == 1:
      meteor_score = meteor_score + 2
      print("PLUS 2 for MOVING!", meteor_score)
   if 1 < obj['dist_per_frame'] < 10:
      meteor_score = meteor_score + 1
      print("PLUS 1 for good speed!", meteor_score)

   if obj['cm_hist_len_ratio'] < .5:
      print("MINUS 1 for for bad cm/hist ratio!", meteor_score)
      meteor_score = meteor_score - 1
   else:
      print("PLUS 1 for for good cm/hist ratio!", meteor_score)
      meteor_score = meteor_score + 1
   

   if obj['max_cm'] < 3:
      meteor_score = 0
      print("ZERO FOR LOW CM!", meteor_score)
   if obj['moving'] == 0:
      meteor_score = 0
      print("ZERO FOR NOT MOVING!", meteor_score)
   if obj['gap_events'] > 3:
      print("ZERO FOR TO MANY GAP EVENTS!", meteor_score)
      meteor_score = 0
   if obj['dist'] < 5:
      print("ZERO FOR SHORT DISTANCE!", meteor_score)
      meteor_score = 0

   if 1 < obj['dist_per_frame'] > 10:
      print("ZERO FOR TOO FAST !", meteor_score)
      meteor_score = 0
 


   for key in obj:
      print("MTEST:", key, obj[key])
   print("METEOR SCORE:", meteor_score)

   return(meteor_score)

def mfd_to_points(mfd):
   points = []
   for hs in mfd:
      points.append((hs[2], hs[3]))
   return(points)



def hist_to_points(hist):
   points = []
   for hs in hist:
      points.append((hs[1], hs[2]))
   return(points)

def detect_from_img_acc_diff(masked_frames):
   print("Detect from img_acc_diff.")

def detect_meteor(video_file, json_conf, show = 0):
   red_file = video_file.replace(".mp4", "-reduced.json")
   met_file = video_file.replace(".mp4", ".json")
   if cfe(red_file) == 0:
      print("No reduction file yet.")
      red_data = {}
   else:
      print("Loading red data.")
      red_data = load_json_file(red_file)
   if cfe(met_file) == 0:
      print("No meteor file yet.")
      met_data = {}
   else:
      print("Loading met data.")
      met_data = load_json_file(met_file)
      for key in met_data:
         print(key, met_data[key])
   #exit()
   #cv2.namedWindow('pepe') 
   print("Play meteor:", video_file)
   sd_frames = load_video_frames(video_file, json_conf)
   frames = []

   image_acc = None
   fc = 0
   objects = []
   # find max px value
   mxpx = []
   for frame in sd_frames:
      max_px_diff = np.max(frame)
      mxpx.append(max_px_diff)

   min_px = min(mxpx)
   max_px = min(mxpx)
   thresh = min_px * .5
   first_gray_frame = None
   last_image_thresh = None

   #thresh_frames = build_thresh_frames(sd_frames)
   #exit()
   print("LEN FRAMES:", len(sd_frames))
   mask_image = median_frames(sd_frames)
   #mask_image = cv2.convertScaleAbs(mask_image)

   print("MS:", mask_image.shape)



   ithresh = np.max(mask_image) * .5
   avg_thresh = np.mean(mask_image) + 15
   if ithresh > 50:
      ithresh = 50

   print("ITHRESH:", ithresh,show)
   if ithresh < 20:
      ithresh = 20
   if avg_thresh > ithresh:
      ithresh = avg_thresh

   _, mask_thresh = cv2.threshold(mask_image.copy(), ithresh, 255, cv2.THRESH_BINARY)
   mask_cnts,mask_pos_cnts = find_contours(mask_thresh, mask_thresh)
   
   mask_points = []
   masks = []
   for msk in mask_pos_cnts:
      mask_points.append((msk[0], msk[1]))
      if msk[2] < 150 and msk[3] < 150:
         msk_str = str(msk[0]) + "," +  str(msk[1]) + "," + str(msk[2]) + "," + str(msk[3])
         masks.append((msk_str))

   if show == 1:
      img = mask_frame(mask_image, mask_points, masks,5)

   masked_frames = []
   for frame in sd_frames:
      #hd_img = cv2.resize(frame, (1920,1080))
      hd_img = mask_frame(frame, mask_points, masks,5)
      masked_frames.append(hd_img)
  
   print("YO") 
   bp_meteors = detect_from_bright_pixels(masked_frames)
   #dtd_meteors = []
   print("YO2") 
   dtd_meteors = detect_from_thresh_diff(masked_frames)
   exit()
   print("YO3") 

   orig_meteors = []
   if "meteor_frame_data" in red_data:
      orig_meteors.append(red_data['meteor_frame_data'])
   else:
      orig_meteors = []

   if len(dtd_meteors) > 0:
      if len(dtd_meteors[0]['history']) > 1:
         x_dir_mod, y_dir_mod = find_dir_mod(dtd_meteors[0]['history'])
   elif len(bp_meteors) > 0:
      if len(bp_meteors[0]['history']) > 1:
         x_dir_mod, y_dir_mod = find_dir_mod(bp_meteors[0]['history'])
   elif len(orig_meteors) > 0:
      print(orig_meteors)
      if len(orig_meteors[0]) > 1:
         x_dir_mod, y_dir_mod = find_dir_mod(orig_meteors[0], 1)


   # MERGE ALL OF THE DETECT METHOD RESULTS INTO ONE FINAL 
   ih, iw = sd_frames[0].shape[:2]
   hdm_x = 1920 / iw
   hdm_y = 1080 / ih
   metconf = {}
   metframes = {}
   bp_metframes = {}
   dtd_metframes = {}
   orig_metframes = {}
   metconf['x_dir_mod'] = x_dir_mod 
   metconf['y_dir_mod'] = y_dir_mod
   if len(bp_meteors) > 0:
      bp_metframes,metconf = hist_to_metframes(bp_meteors[0],bp_metframes,metconf,sd_frames[0])
   else:
      bp_metframes = {}
   if len(dtd_meteors) > 0:
      dtd_metframes,metconf = hist_to_metframes(dtd_meteors[0],dtd_metframes,metconf, sd_frames[0])
   else:
      dtd_metframes = {}
   orig_obj = {}
   orig_obj['history'] = orig_meteors[0]
   orig_metframes,metconf = hist_to_metframes(orig_obj,orig_metframes,metconf, sd_frames[0])
   for fn in bp_metframes:
      if fn not in metframes:
         metframes[fn] = {}
      if 'tx' not in metframes[fn]:
         metframes[fn]['tx'] = []
         metframes[fn]['ty'] = []
         metframes[fn]['tw'] = []
         metframes[fn]['th'] = []

      if bp_metframes[fn]['sd_x'] > 1 and bp_metframes[fn]['sd_y'] > 1:
         metframes[fn]['tx'].append(int(bp_metframes[fn]['sd_x'] + (bp_metframes[fn]['sd_w']/2)))
         metframes[fn]['ty'].append(int(bp_metframes[fn]['sd_y'] + (bp_metframes[fn]['sd_h']/2)))
         metframes[fn]['tw'].append(int(bp_metframes[fn]['sd_w']))
         metframes[fn]['th'].append(int(bp_metframes[fn]['sd_h']))

   for fn in dtd_metframes:
      if fn not in metframes:
         metframes[fn] = {}
      if 'tx' not in metframes[fn]:
         metframes[fn]['tx'] = []
         metframes[fn]['ty'] = []
         metframes[fn]['tw'] = []
         metframes[fn]['th'] = []

      if dtd_metframes[fn]['sd_x'] > 1 and dtd_metframes[fn]['sd_y'] > 1:
         metframes[fn]['tx'].append(int(dtd_metframes[fn]['sd_x'] + (dtd_metframes[fn]['sd_w']/2)))
         metframes[fn]['ty'].append(int(dtd_metframes[fn]['sd_y'] + (dtd_metframes[fn]['sd_h']/2)))
         metframes[fn]['tw'].append(int(dtd_metframes[fn]['sd_w']))
         metframes[fn]['th'].append(int(dtd_metframes[fn]['sd_h']))

   for fn in orig_metframes:
      show_img = sd_frames[fn].copy()
      if fn not in metframes:
         metframes[fn] = {}
      if 'tx' not in metframes[fn]:
         metframes[fn]['tx'] = []
         metframes[fn]['ty'] = []
         metframes[fn]['tw'] = []
         metframes[fn]['th'] = []

      if orig_metframes[fn]['sd_x'] > 1 and orig_metframes[fn]['sd_y'] > 1:
         tx =  orig_metframes[fn]['sd_x'] + (orig_metframes[fn]['sd_w']/2)
        # tx = int(tx / hdm_x)
         ty =  orig_metframes[fn]['sd_y'] + (orig_metframes[fn]['sd_h']/2)
        # ty = int(ty / hdm_y)
      
         cv2.rectangle(show_img, (int(tx), int(ty)), (int(tx)+5, int(ty)+5), (255), 1)
         metframes[fn]['tx'].append( tx)
         metframes[fn]['ty'].append(ty)
         metframes[fn]['tw'].append(int(orig_metframes[fn]['sd_w']/hdm_x))
         metframes[fn]['th'].append(int(orig_metframes[fn]['sd_h']/hdm_y))
         if show == 1:
            print("ishow:", show)
            cv2.imshow("Orig Points", show_img)
            cv2.waitKey(100)
    
       

   metframes = sort_metframes(metframes)

   total_frames = len(metframes)

   print("FINAL METFRAMES:")
   fc = 0
   missing_frames = []
   bad_frames = []
   for fn in metframes:
      next_fn = fn + 1
      if fc < total_frames - 1:
         if next_fn not in metframes:
            missing_frames.append(next_fn)
      if 'tx' in metframes[fn]:
         if len(metframes[fn]['tx']) > 0: 
            metframes[fn]['ax'] = int(np.median(metframes[fn]['tx']))
            metframes[fn]['ay'] = int(np.median(metframes[fn]['ty']))
            metframes[fn]['aw'] = int(np.median(metframes[fn]['tw']))
            metframes[fn]['ah'] = int(np.median(metframes[fn]['th']))
         else:
            bad_frames.append(fn)
      else:
         bad_frames.append(fn)
   
      fc = fc + 1
   for bf in bad_frames:
      del(metframes[bf])
   print("BAD FRAMES:", bad_frames)
   print("MISSING FRAMES:", missing_frames)
   for msf in missing_frames:
      before = msf - 1
      after = msf + 1
      if before in metframes and after in metframes:
         metframes[msf] = {}
         metframes[msf]['ax'] = int((metframes[before]['ax'] + metframes[after]['ax']) / 2)
         metframes[msf]['ay'] = int((metframes[after]['ay'] + metframes[after]['ay']) / 2)
         metframes[msf]['aw'] = int(metframes[before]['aw'])
         metframes[msf]['ah'] = int(metframes[before]['ah'])
   
         metframes[msf]['fixed'] = 1 

   metframes = sort_metframes(metframes)
   xdm = metconf['x_dir_mod']
   ydm = metconf['y_dir_mod']
   for fn in metframes:
      img = sd_frames[fn] 
      x = metframes[fn]['ax']
      y = metframes[fn]['ay']
      w = metframes[fn]['aw']
      h = metframes[fn]['ah']
      if w < 4:
         w = 4
      if h < 4:
         h = 4
      metframes[fn]['hd_x'] = x * hdm_x
      metframes[fn]['hd_y'] = y * hdm_y
      metframes[fn]['sd_cx'] = x 
      metframes[fn]['sd_cy'] = y 
      metframes[fn]['sd_x'] = int(x - int(metframes[fn]['aw'])/2 )
      metframes[fn]['sd_y'] = int(y - int(metframes[fn]['ah'])/2 )
      metframes[fn]['sd_w'] = int(w)
      metframes[fn]['sd_h'] = int(h)
      metframes[fn]['w'] = int(w)
      metframes[fn]['h'] = int(h)
      if xdm < 0:
         lc_x = metframes[fn]['sd_x']
      else:
         lc_x = metframes[fn]['sd_x'] + metframes[fn]['sd_w']
      if ydm < 0:
         lc_y = metframes[fn]['sd_y']
      else:
         lc_y = metframes[fn]['sd_y'] + metframes[fn]['sd_h']

      metframes[fn]['sd_lc_x'] = int(lc_x)
      metframes[fn]['sd_lc_y'] = int(lc_y)
      metframes[fn]['lc_x'] = int(lc_x)
      metframes[fn]['l_cy'] = int(lc_y)

      metframes[fn]['sd_intensity'] = 0
      metframes[fn]['hd_intensity'] = 0
      metframes[fn]['sd_max_px'] = 0
      metframes[fn]['hd_max_px'] = 0
      metframes[fn]['magnitude'] = 0
      metframes[fn]['ra'] = 0
      metframes[fn]['dec'] = 0
      metframes[fn]['az'] = 0
      metframes[fn]['el'] = 0
     
      print("MF:", fn, metframes[fn])

      #cv2.circle(img,(x,y), 3, (255,255,255), 1)
      #cv2.rectangle(img, (x-2, y-2), (x+2, y+2), (128), 1)

   # FINISH UP AND SAVE!
   print("METFRAME LEN:", len(metframes))
   mfd, metframes,metconf = metframes_to_mfd(metframes, metconf, video_file,json_conf)
   print("METFRAME LEN:", len(metframes))


   cmp_imgs,metframes = make_meteor_cnt_composite_images(json_conf, mfd, metframes, metconf, sd_frames, video_file)
   prefix = red_data['sd_video_file'].replace(".mp4", "-frm")
   prefix = prefix.replace("SD/proc2/", "meteors/")
   prefix = prefix.replace("/passed", "")
   for fn in cmp_imgs:
      cv2.imwrite(prefix  + str(fn) + ".png", cmp_imgs[fn])
      print("UPDATING!", prefix + str(fn) + ".png")
      metframes[fn]['cnt_thumb'] = prefix + str(fn) + ".png"

   metframes = update_intensity(metframes, sd_frames)
   #metframes, metconf = minimize_start_len(metframes,sd_frames,metconf,show)

   red_data['metconf'] = metconf
   red_data['metframes'] = metframes
   red_data['meteor_frame_data'] = mfd
   make_light_curve(metframes,video_file)
   save_json_file(red_file, red_data)
   print("saving json:", red_file)


   exit()

   for frame in sd_frames:
      #hd_img = cv2.resize(frame, (1920,1080))
      hd_img = mask_frame(frame, mask_points, masks,5)

      hd_img = frame
      if len(hd_img.shape) == 3:
         gray_frame = cv2.cvtColor(hd_img, cv2.COLOR_BGR2GRAY)
         gray_frame = cv2.convertScaleAbs(gray_frame)
      else:
         gray_frame = hd_img
      frames.append(hd_img)


      # do image acc / diff
      blur_frame = cv2.GaussianBlur(gray_frame, (7, 7), 0)
      level_frame = adjustLevels(blur_frame, 50,1,255)
      level_frame = cv2.convertScaleAbs(level_frame)
      gray_frame = level_frame

      if first_gray_frame is None:
         first_gray_frame = gray_frame 

      if image_acc is None:
         image_acc = np.float32(gray_frame)

      alpha = .1
      hello = cv2.accumulateWeighted(gray_frame, image_acc, alpha)

      image_diff = cv2.absdiff(image_acc.astype(gray_frame.dtype), gray_frame,)
      first_image_diff = cv2.absdiff(first_gray_frame.astype(gray_frame.dtype), gray_frame,)
      image_diff = first_image_diff

      thresh = np.max(image_diff) * .95
      ithresh = np.max(gray_frame) * .5
      if thresh < 20:
         thresh = 20

      _, image_thresh = cv2.threshold(gray_frame.copy(), ithresh, 255, cv2.THRESH_BINARY)

      if last_image_thresh is not None:
         image_thresh_diff = cv2.absdiff(image_thresh.astype(gray_frame.dtype), last_image_thresh,)
      else:
         image_thresh_diff = image_thresh

      _, diff_thresh = cv2.threshold(image_diff.copy(), thresh, 255, cv2.THRESH_BINARY)
      #show_img2 = cv2.resize(cv2.convertScaleAbs(image_thresh_diff), (960,540))

      # find contours and ID objects
      diff_thresh = image_thresh
      cnts,pos_cnts = find_contours(diff_thresh, gray_frame)
      if len(pos_cnts) > 1:
         _, diff_thresh = cv2.threshold(image_diff.copy(), 30, 255, cv2.THRESH_BINARY)
         cnts,pos_cnts = find_contours(diff_thresh, gray_frame)

      ic = 0
      marked_image = image_diff.copy()
      for cnt in cnts:
         x,y,w,h,size,mx,my,max_val,intensity = pos_cnts[ic]
         object, objects = id_object(cnt, objects,fc, (mx,my), max_val, intensity, 0)
         print(object)
         if "oid" in object:
            name = str(object['oid'])
            cv2.putText(marked_image, name ,  (x-5,y-12), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
         #cv2.rectangle(marked_image, (x, y), (x+w, y+h), (128), 1)

         ic = ic + 1
      #print("OBJECTS:", fc, len(objects))
      #print("CNTS:", len(pos_cnts), pos_cnts)


      if show == 1:
         show_img = cv2.resize(cv2.convertScaleAbs(diff_thresh), (960,540))
         show_img2 = cv2.resize(cv2.convertScaleAbs(marked_image), (960,540))
         print("ishow:", show)
         cv2.imshow('diff image', show_img2) 
         cv2.waitKey(1)
      last_image_thresh = image_thresh
      fc = fc + 1


   meteors = []

   for obj in objects:
      iis = []
      fns = []
      elp_fr = obj['history'][-1][0] - obj['history'][0][0]
      #print(obj)
      #for hs in obj['history']:
         #print(obj['oid'], hs[-1])
         #iis.append(hs[-1])
         #fns.append(hs[0])

      sci_peaks, peak_to_frame = meteor_test_peaks(obj)

   #exit()
   for obj in objects:
      print(obj['oid'], obj['history'])

   for obj in objects:
      elp_fr = obj['history'][-1][0] - obj['history'][0][0]
      hist_len = len(obj['history'])

      (max_cm,gaps,gap_events,cm_hist_len_ratio) = meteor_test_cm_gaps(obj)
      obj['max_cm'] = max_cm  
      obj['gaps'] = gaps
      obj['gap_events'] = gap_events
      obj['cm_hist_len_ratio'] = cm_hist_len_ratio

      if elp_fr > 0:
         elp_fr_to_hist_len_ratio = len(obj['history']) / elp_fr
         obj['elp_fr_to_hist_len_ratio'] = elp_fr_to_hist_len_ratio
         print("ELP HIST:", obj['oid'], elp_fr_to_hist_len_ratio)
      if obj['max_cm'] >= 3 and obj['gaps'] < 10 and (.7 <= elp_fr_to_hist_len_ratio <= 2):

         print(obj['oid'], obj['status'], obj['hist_len'], obj['is_straight'], obj['dist'], obj['max_cm'], obj['gaps'], obj['gap_events'], obj['cm_hist_len_ratio'])     
         x_dir_mod, y_dir_mod = find_dir_mod(obj['history'])
         obj['x_dir_mod'] = x_dir_mod
         obj['y_dir_mod'] = y_dir_mod
         obj['debug'] = "Meteor"
         meteors.append(obj)
      else:
         obj['debug'] = "Hist len: " + str(obj['hist_len']) + " Straight: " + str(obj['is_straight']) + " Dist: " + str(obj['dist']) + " Max CM:" + str(obj['max_cm']) + " Gaps: " + str(obj['gaps']) + " Gap Events: " + str(obj['gap_events']) + " Gap frame ratio:" + str(obj['cm_hist_len_ratio'])
   if len(meteors) == 0:
      print("No meteors found.") 
      for obj in objects:
         print(obj['oid'], obj['debug'], obj['history'])
      exit()
   elif len(meteors) == 1:

      ih, iw = sd_frames[0].shape[:2]
      hdm_x = 1920 / iw
      hdm_y = 1080 / ih

      hdxs = []
      hdys = []
      metconf = {}
      metconf['x_dir_mod'] = meteors[0]['x_dir_mod']
      metconf['y_dir_mod'] = meteors[0]['y_dir_mod']
      metframes,xs,ys,fns = hist_to_metframes(meteors[0],metconf, sd_frames[0])
      m,b = best_fit_slope_and_intercept(xs,ys)
      for i in range(0,len(xs)-1):
         hd_x = xs[i] * hdm_x
         hd_y = ys[i] * hdm_y
         hdxs.append(hd_x)
         hdys.append(hd_y)
      
      hd_m,hd_b = best_fit_slope_and_intercept(hdxs,hdys)

      metconf['m'] = hd_m
      metconf['b'] = hd_b
      metconf['sd_m'] = m
      metconf['sd_b'] = b
      metconf['sd_xs'] = xs
      metconf['sd_ys'] = ys
      metconf['sd_fns'] = fns
      metconf['sd_fx'] = xs[0]
      metconf['sd_fy'] = ys[0]
      metconf['first_frame'] = fns[0]
      metconf['sd_acl_poly'] = 0

      sd_dist = calc_dist(( metconf['sd_xs'][0], metconf['sd_ys'][0]),( metconf['sd_xs'][-1], metconf['sd_ys'][-1]))
      hd_dist = calc_dist(( metconf['sd_xs'][0]*hdm_x, metconf['sd_ys'][0]*hdm_y),( metconf['sd_xs'][-1]*hdm_x, metconf['sd_ys'][-1]*hdm_y))
      metconf['sd_dist'] = sd_dist
      metconf['hist_len'] = meteors[0]['hist_len']
      elp_fr = meteors[0]['history'][-1][0] - meteors[0]['history'][0][0]
      metconf['sd_seg_len'] = sd_dist / elp_fr 
      metconf['med_seg_len'] = hd_dist / elp_fr 
#(meteors[0]['hist_len'] )
      #metconf['sd_seg_len'] = 2

      fc = 0
      for frame in frames:   
         orig_image = cv2.cvtColor(frame,cv2.COLOR_GRAY2RGB)
         m = 0
         if fc in metframes:
            cnt_img = frame[y:y+h,x:x+w]
            x = metframes[fc]['sd_x']
            y = metframes[fc]['sd_y']
            w = metframes[fc]['sd_w']
            h = metframes[fc]['sd_h']
            mx = metframes[fc]['sd_max_x']
            my = metframes[fc]['sd_max_y']
            lc_x = metframes[fc]['sd_lc_x']
            lc_y = metframes[fc]['sd_lc_y']
            #lc_y = metframes[fc]['m'] = metconf['m']
            #lc_y = metframes[fc]['b'] = metconf['b']
            cx = int(x + (w/2))
            cy = int(y + (h/2))
            fcc = fc - metconf['first_frame']
            print("FCC:", fcc)
            print("EQ: est_x = ", metconf['sd_fx'], " + ", metconf['x_dir_mod'] , " * ",  metconf['sd_seg_len'], " + " , metconf['sd_acl_poly'], " * ", fcc)
            est_x = int(metconf['sd_fx']) + (metconf['x_dir_mod'] * (metconf['sd_seg_len']*fcc)) + (metconf['sd_acl_poly'] * fcc)
            est_y = (metconf['m']*est_x)+metconf['b']
            est_x = int(est_x)
            est_y = int(est_y)


            cv2.circle(orig_image,(lc_x,lc_y), 1, (255,0,0), 1)
            cv2.circle(orig_image,(est_x,est_y), 1, (0,128,128), 1)
            cv2.circle(orig_image,(cx,cy), 1, (0,128,0), 1)
            cv2.circle(orig_image,(mx,my), 1, (0,0,255), 1)
            cv2.rectangle(orig_image, (x, y), (x+w, y+h), (128,128,128), 1)
            m = 1
         if show == 1:
            desc = str("FN:" + str(fc))
            cv2.putText(orig_image, desc,  (10,10), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
            print("show", show) 
            cv2.imshow('final', orig_image)
            if m == 0:
               cv2.waitKey(10)  
            else: 
               cv2.waitKey(1)  
            fc = fc + 1
   else:
      print("More than 1 meteor found.")
      for obj in meteors:
         print(obj)

   iis = []
   fns = []
   for fn in metframes:
      print(fn, metframes[fn])
      if "sd_intensity" in metframes[fn]:
         iis.append(int(metframes[fn]['sd_intensity']))
         fns.append(int(fn))

   # make light curve:

   #for hs in obj['history']:
   #   print("HIST:", hs)
   #   iis.append(hs[-1])
   #   fns.append(hs[0])

   import matplotlib
   matplotlib.use('Agg')
   import matplotlib.pyplot as plt
   #fig = plt.figure()
   print(fns,iis)
   plt.plot(fns,iis)
   curve_file = video_file.replace(".mp4", "-lightcurve.png")
   plt.savefig(curve_file)


   print("")
   for key in metconf:
      print(key, metconf[key])
   metframes, metconf = clean_metframes(metframes,metconf,frames)
   #metframes, metconf = minimize_start_len(metframes,frames,metconf,show)

   print("METFRAME LEN:", len(metframes))
   mfd, metframes,metconf = metframes_to_mfd(metframes, metconf, video_file,json_conf)
   print("METFRAME LEN:", len(metframes))


   cmp_imgs,metframes = make_meteor_cnt_composite_images(json_conf, mfd, metframes, metconf, frames, video_file)
   prefix = red_data['sd_video_file'].replace(".mp4", "-frm")
   prefix = prefix.replace("SD/proc2/", "meteors/")
   prefix = prefix.replace("/passed", "")
   for fn in cmp_imgs:
      cv2.imwrite(prefix  + str(fn) + ".png", cmp_imgs[fn])
      print("UPDATING!", prefix + str(fn) + ".png")
      metframes[fn]['cnt_thumb'] = prefix + str(fn) + ".png"


   red_data['metconf'] = metconf
   red_data['metframes'] = metframes
   red_data['meteor_frame_data'] = mfd
   print("saving json:", red_file)
   save_json_file(red_file, red_data)

   exit()
   return(metframes, frames, metconf)
  
def clean_metframes(mf, metconf, frames):
   last_fn = None
   last_cx = None
   last_cy = None
   first_fn = None
   first_cx = None
   first_cy = None
   max_dist_from_start = 0
   last_dist_from_start = None
   fwdm = 1
   for fn in mf:
      if last_fn is not None :
         dist_from_last = calc_dist((mf[fn]['sd_cx'], mf[fn]['sd_cy']), (last_cx, last_cy))
         dist_from_start= calc_dist((mf[fn]['sd_cx'], mf[fn]['sd_cy']), (first_cx, first_cy))
         mf[fn]['sd_dist_from_last'] = dist_from_last
         mf[fn]['sd_dist_from_first'] = dist_from_start
         if last_dist_from_start is not None:
            seg_diff = dist_from_start - last_dist_from_start 
            mf[fn]['sd_seg_diff'] = dist_from_start - last_dist_from_start
         last_dist_from_start = dist_from_start 
         fwdm = 0
         if max_dist_from_start < dist_from_start:
            max_dist_from_start = dist_from_start
            fwdm = 1
      if first_fn is None :
         first_fn = fn
         first_cx = mf[fn]['sd_cx']
         first_cy = mf[fn]['sd_cy']
      if 'sd_seg_diff' in mf[fn]:
         if fwdm == 1:
            print(fn, mf[fn]['sd_dist_from_last'], mf[fn]['sd_seg_diff'], mf[fn]['sd_dist_from_first']) 
         else: 
            print(fn, "NO FWD MOTION.", mf[fn]['sd_seg_diff'], mf[fn]['sd_dist_from_first'])
            first_cy = mf[fn]['bad'] = 1
      else:
         print(fn)
      last_cx = mf[fn]['sd_cx']
      last_cy = mf[fn]['sd_cy']
      last_fn = fn 

   cleaning = 1
   while cleaning == 1:
      last_f = first_fn + (len(mf) - 1)
      if last_f in mf:
         if "bad" in mf[last_f]:
            del mf[last_f]
         else:
            cleaning = 0
      else:
         cleaning = 0

   segs = []
   for fn in mf:
      if "sd_seg_diff" in mf[fn]:
         print(fn, mf[fn]['sd_dist_from_last'], mf[fn]['sd_seg_diff'], mf[fn]['sd_dist_from_first'], mf[fn]['sd_intensity']) 
         segs.append(mf[fn]['sd_seg_diff'])
      else:
         print(fn)
   metconf['sd_seg_len'] = np.median(segs)   
   #exit()   
   return(mf, metconf) 

def minimize_start_len(metframes,frames,metconf,show=0):
   exit()
   this_poly = np.zeros(shape=(2,), dtype=np.float64)
   if "sd_seg_len" in metconf:
      this_poly[0] = np.float64(metconf['sd_seg_len'])
      this_poly[0] = 2
   else:
      this_poly[0] = np.float64(2)
   if "sd_acl_poly" in metconf:
      this_poly[1] = np.float64(metconf['sd_acl_poly'])
   else:
      this_poly[1] = np.float64(-.01)
   #err = reduce_start_len(metframes, frames, metconf,show)
   res = scipy.optimize.minimize(reduce_seg_acl, this_poly, args=( metframes, metconf,frames,show), method='Nelder-Mead', options={'maxiter':1000, 'xatol': .05})
   poly = res['x']
   fun = res['fun']

   print("ACL POLY:", poly[0], poly[1], fun)
   metconf['sd_seg_len'] = float(poly[0])
   metconf['sd_acl_poly'] = float(poly[1])
   metconf['sd_acl_res'] = fun
   return(metframes,metconf)


def reduce_seg_acl(this_poly,metframes,metconf,frames,show=0):
  
   metframes = sort_metframes(metframes)
   # update m/b
   m,b = best_fit_slope_and_intercept(metconf['sd_xs'],metconf['sd_ys'])
   metconf['sd_m'] = m
   metconf['sd_b'] = b
   print("METCONF:", m, b, metconf['sd_xs'], metconf['sd_ys'])
   
 
   fc = 0
   fcc = 0
   tot_res_err = 0
   for frame in frames:   
      orig_image = cv2.cvtColor(frame,cv2.COLOR_GRAY2RGB)
      met = 0
      if fc in metframes or str(fc) in metframes:
         if str(fc) not in metframes:
            fc = int(fc)
         elif int(fc) not in metframes:
            fc = str(fc)
      
         x = metframes[fc]['sd_x']
         y = metframes[fc]['sd_y']
         w = metframes[fc]['sd_w']
         h = metframes[fc]['sd_h']
         #mx = metframes[fc]['sd_max_x']
         #my = metframes[fc]['sd_max_y']
         mx = metframes[fc]['sd_x']
         my = metframes[fc]['sd_y']
         #lc_x = metframes[fc]['sd_lc_x']
         #lc_y = metframes[fc]['sd_lc_y']
         lc_x = metframes[fc]['sd_x']
         lc_y = metframes[fc]['sd_y']
         cx = int(x + (w/2))
         cy = int(y + (h/2))
         if "first_frame" not in metconf:
            metconf['first_frame'] = metconf['sd_fns'][0]
         if "sd_fx" not in metconf:
            metconf['sd_fx'] = metconf['sd_xs'][0]
            metconf['sd_fy'] = metconf['sd_ys'][0]
    
         fcc = fc - metconf['first_frame']
         cnt_img = frame[y:y+h,x:x+w]
         #est_x = int(metconf['sd_fx']) + (metconf['x_dir_mod'] * (this_poly[0]*fcc)) + (0 * fcc)
         est_x = int(metconf['sd_fx']) + (metconf['x_dir_mod'] * (this_poly[0]*fcc)) + (this_poly[1] * (fcc**2))
         est_y = (metconf['sd_m']*est_x)+metconf['sd_b']
         print("EST X/Y", metframes[fc]['sd_x'], metframes[fc]['sd_y'], est_x, est_y, metconf['sd_m'], metconf['sd_b'])
         est_x = int(est_x)
         est_y = int(est_y)
         #res_err = calc_dist((est_x,est_y),(lc_x,lc_y))
         res_err = calc_dist((est_x,est_y),(cx,cy))
         tot_res_err = tot_res_err + res_err
         #print("FCC:", fcc, this_poly[0], this_poly[1], res_err)
         cv2.circle(orig_image,(est_x,est_y), 1, (0,255,255), 1)
         cv2.circle(orig_image,(lc_x,lc_y), 1, (255,0,0), 1)
         cv2.circle(orig_image,(cx,cy), 1, (0,128,0), 1)
         cv2.circle(orig_image,(int(mx),int(my)), 1, (0,0,255), 1)
         cv2.rectangle(orig_image, (x, y), (x+w, y+h), (128,128,128), 1)
         met = 1
      if met == 0:
         skip = 1
      else: 
         if show == 1:
            print("swho", 1)
            cv2.imshow('final', orig_image)
            cv2.waitKey(100)  
      fc = fc + 1
   if fcc > 0:
      res_err = np.float64(tot_res_err / fcc)
   else:
      res_err = 0
   #res_err = np.float64(tot_res_err )
   print("RES:", res_err, this_poly[0], this_poly[1]) 
   return(res_err)

def hist_to_metframes(obj,metframes,metconf,frame):
   #metframes = {}

   ih, iw = frame.shape[:2]
   hdm_x = 1920 / iw
   hdm_y = 1080 / ih

   xs = []
   ys = []
   fns = []
   xdm = metconf['x_dir_mod']
   ydm = metconf['y_dir_mod']
   for hs in obj['history']:
      print(len(hs))
      intensity = 0
      if len(hs) == 9:
         fn,x,y,w,h,mx,my,max_px,intensity = hs
         fn = int(fn)
      if len(hs) == 8:
         fn,x,y,w,h,mx,my,max_px = hs
      if len(hs) == 11:
         ft,fn,x,y,w,h,max_px,ra,dec,az,el = hs
         x = int(x / hdm_x)
         y = int(y / hdm_y)
         w = int(w / hdm_x)
         h = int(h / hdm_y)
         mx = 0
         my = 0
      cx = int(x + (w/2))
      cy = int(y + (h/2))
      fn = int(fn)
      if xdm < 0:
         lc_x = x
      else:
         lc_x = x + w
      if ydm < 0:
         lc_y = y
      else:
         lc_y = y + h
      if fn not in metframes:
         metframes[fn] = {}
      
      metframes[fn]['sd_x'] = x
      metframes[fn]['sd_y'] = y
      metframes[fn]['sd_w'] = w
      metframes[fn]['sd_h'] = h
      metframes[fn]['sd_cx'] = cx
      metframes[fn]['sd_cy'] = cy
      metframes[fn]['sd_lc_x'] = lc_x
      metframes[fn]['sd_lc_y'] = lc_y
      metframes[fn]['sd_max_x'] = x + mx
      metframes[fn]['sd_max_y'] = y + my
      metframes[fn]['sd_px'] = max_px
      metframes[fn]['sd_intensity'] = float(intensity)
      xs.append(lc_x)
      ys.append(lc_y)
      fns.append(fn)
      metconf['sd_xs'] = xs
      metconf['sd_ys'] = ys
      metconf['sd_fns'] = fns
   return(metframes,metconf)

def setup_metframes(mfd,frame):

   ih, iw = frame.shape[:2]
   hdm_x = 1920 / iw
   hdm_y = 1080 / ih
   # establish initial first x,y last x,y
   fx = mfd[0][2]
   fy = mfd[0][3]
   lx = mfd[-1][2]
   ly = mfd[-1][3]

   dir_x = fx - lx
   dir_y = fy - ly
   if dir_x < 0:
      x_dir_mod = 1
   else:
      x_dir_mod = -1
   if dir_y < 0:
      y_dir_mod = 1
   else:
      y_dir_mod = -1


   # establish first frame number, last frame number and total frames
   ff = mfd[0][1]
   lf = mfd[-1][1]
   tf = lf - ff
   tf = tf + 1

   # establish initial line distance and x_incr
   line_dist = calc_dist((fx,fy),(lx,ly))
   x_incr = int(line_dist / (tf ))

   metframes = {}
   etime = 0
   for i in range(0,tf):
      fi = i + ff
      metframes[fi] = {}
      if i > 0:
         etime = i / 25
      else:
         etime = 0
      metframes[fi]['etime'] = etime
      metframes[fi]['fn'] = fi
      metframes[fi]['ft'] = 0
      metframes[fi]['hd_x'] = 0
      metframes[fi]['hd_y'] = 0
      metframes[fi]['w'] = 0
      metframes[fi]['h'] = 0
      metframes[fi]['max_px'] = 0
      metframes[fi]['ra'] = 0
      metframes[fi]['dec'] = 0
      metframes[fi]['az'] = 0
      metframes[fi]['el'] = 0
      metframes[fi]['len_from_last'] = 0
      metframes[fi]['len_from_start'] = 0
   sd_fns = []
   xs = []
   ys = []
   for fd in mfd:
      frame_time, fn, hd_x,hd_y,w,h,max_px,ra,dec,az,el = fd
      if w == 0:
         w = 6
      if h  == 0:
         h = 6
      sd_cx = int(hd_x / hdm_x)
      sd_cy = int(hd_y / hdm_y)
      fi = fn
      xs.append(hd_x)
      ys.append(hd_y)
      sd_fns.append(fn)
      metframes[fi]['fn'] = fi
      metframes[fi]['ft'] = frame_time
      metframes[fi]['hd_x'] = hd_x
      metframes[fi]['hd_y'] = hd_y
      metframes[fi]['sd_cx'] = int(hd_x / hdm_x)
      metframes[fi]['sd_cy'] = int(hd_y / hdm_y)
      metframes[fi]['sd_x'] = int(sd_cx - (w/2))
      metframes[fi]['sd_y'] = int(sd_cy - (h/2))
      metframes[fi]['w'] = w
      metframes[fi]['h'] = h
      metframes[fi]['sd_w'] = w
      metframes[fi]['sd_h'] = h
      metframes[fi]['max_px'] = max_px
      metframes[fi]['ra'] = ra
      metframes[fi]['dec'] = dec
      metframes[fi]['az'] = az
      metframes[fi]['el'] = el
   metconf = {}
   metconf['sd_xs'] = xs
   metconf['sd_ys'] = ys
   metconf['sd_fns'] = sd_fns
   metconf['fx'] = fx
   metconf['fy'] = fy
   metconf['lx'] = lx
   metconf['ly'] = ly
   metconf['tf'] = tf
   metconf['runs'] = 0
   metconf['line_dist'] = line_dist
   metconf['x_incr'] = x_incr
   metconf['x_dir_mod'] = x_dir_mod
   metconf['y_dir_mod'] = y_dir_mod
   m,b = best_fit_slope_and_intercept(xs,ys)
   metconf['sd_m'] = m
   metconf['sd_b'] = b
   metconf['sd_acl_poly'] = 0


   metconf['sd_seg_len'] = 2 

   # fill in missing frame values with previous value
   last_fn = None
   for fn in metframes:
      if last_fn is not None:
         if metframes[fn]['hd_x'] == 0:
            metframes[fn] = metframes[last_fn]
            metframes[fn]['fn'] = fn
      last_fn = fn

   metframes = sort_metframes(metframes)
   return(metframes, metconf)

def id_object(cnt, objects, fc,max_loc, max_px, intensity, img_w, img_h):
   
   mx,my= max_loc

   if cnt is not None:

      x,y,w,h = cv2.boundingRect(cnt)
      cx,cy = center_point(x,y,w,h)
   else:
      x1,y1,x2,y2 = bound_cnt(mx,my,img_w,img_h,10)
      x = x1
      y = y1
      w = x2 - x1
      h = y2 - y1
      cx = mx
      cy = my


   if fc < 0:
      return({},objects)


   if len(objects) == 0:
      oid = 1
      object = make_new_object(oid, fc,x,y,w,h,mx,my, max_px, intensity)
      objects.append(object)
      return(object, objects)


   # Find object or make new one
   obj_found = 0
   matches = []

   for obj in objects:
      dist = 0
      moid = obj['oid']
      oid = obj['oid']
      ox = obj['x']
      oy = obj['y']
      object_hist = obj['history']
      bx = x + mx
      by = y + my
      found = find_in_hist(obj,x,y,object_hist, img_w, img_h)
      if found == 1:
         matches.append(obj)
      #else:
   if len(matches) == 0:
      # NOT FOUND MAKE NEW
      max_id = max(objects, key=lambda x:x['oid'])
      oid= max_id['oid'] + 1
      object = make_new_object(oid,fc,x,y,w,h,mx,my,max_px,intensity)
      object['status'] = "new"
      objects.append(object)
      object['hist_len'] = 1
      return(object, objects)
   if len(matches) > 1:
      best_match = find_best_match(matches, cnt, objects)
      matches = []
      matches.append(best_match)

   if len(matches) == 1:
      object = matches[0]
      object_hist = object['history']
      this_hist = [fc,x,y,w,h,mx,my,max_px,intensity]
      object['status'] = "new-updated"
      hxs = []
      hys = []
      points = []
      for hs in object_hist:
         if len(hs) == 9:
            tfc,tx,ty,tw,th,tmx,tmy,t_max_px,t_int = hs
         if len(hs) == 8:
            tfc,tx,ty,tw,th,tmx,tmy,t_max_px = hs
         hxs.append(tx)
         hys.append(ty)
         points.append((tx,ty))
      if len(hxs) >= 2:
         min_hx = min(hxs)
         min_hy = min(hys)
         max_hx = max(hxs)
         max_hy = max(hys)
         
         dist = calc_dist((min_hx,min_hy),(max_hx,max_hy))
         object['dist'] = dist
         if dist < 5:
            object['status'] = "not_moving"
         else:
            object['status'] = "moving"

      object['hist_len'] = len(hys)   
      if len(hys) > 0: 
         object['dist_per_frame'] = dist / len(hys)
      if len(points) > 3:
         #print("STRAIGHT OBJ ID:", object['oid'])
         is_straight = arecolinear(points)
         object['is_straight'] =  is_straight
      else:
         object['is_straight'] =  False

      if len(object_hist) <= 300:
         object_hist.append(this_hist)

      object['history'] = object_hist
      object['hist_len'] = len(object_hist)
      objects = save_object(object,objects)
      obj_found = 1
      return(object, objects)

   if len(matches) > 1:
      best_match = find_best_match(matches, cnt, objects)
      #print(fc, "MORE THAN ONE MATCH for",x,y, len(matches))
      #print("--------------------")
      #print(matches)
      #print("--------------------")
      min_dist = 25
      match_total_hist = 0
      for match in matches:
         match_hist = match['history']
         last_hist = match_hist[-1]
         match_x = last_hist[1]
         match_y = last_hist[2]
         dist_to_obj = calc_dist((bx,by),(match_x,match_y))
         if dist_to_obj < min_dist:
            best_dist_obj = match
            min_dist = dist_to_obj
         if len(match_hist) > match_total_hist:
            best_hist_obj = match
            match_total_hist = len(match_hist)

      object = best_hist_obj
      object['status'] = "updated"
      object_hist = object['history']
      this_hist = [fc,x,y,w,h,mx,my,max_px]
      if len(object_hist) <= 150:
         object_hist.append(this_hist)
      object['history'] = object_hist
      object['hist_len'] = len(object_hist)
      objects = save_object(object,objects)
      return(object, objects)

def find_contours(image, orig_image):
   cnt_res = cv2.findContours(image.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
   if len(cnt_res) == 3:
      (_, cnts, xx) = cnt_res
   elif len(cnt_res) == 2:
      (cnts, xx) = cnt_res
   pos_cnts = []
   real_cnts = []
   if len(cnts) > 0:
      for (i,c) in enumerate(cnts):
         x,y,w,h = cv2.boundingRect(cnts[i])
         size = w + h
        
         cnt_img = orig_image[y:y+h,x:x+w]
         #cv2.imshow('cnt', cnt_img)
         #cv2.waitKey(0)
         min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(cnt_img)
         intensity = np.sum(cnt_img)
           

         if w > 1 and h > 1 and max_val > 30:
            pos_cnts.append((x,y,w,h,size,mx,my,max_val,intensity))
            real_cnts.append(cnts[i])
   print("find cnts")

   return(real_cnts,pos_cnts)

def make_new_object(oid, fc, x,y,w,h,max_x,max_y,max_px,intensity):
   object = {}
   object['oid'] = oid
   object['fc'] = fc
   object['x'] = x
   object['y'] = y
   object['w'] = w
   object['h'] = h
   object['max_cm'] = 0
   object['gaps'] = 0
   object['gap_events'] = 0 
   object['cm_hist_len_ratio'] = 0 
   object['is_straight'] =  0
   object['hist_len'] =  0
   object['dist'] =  0
   object['dist_per_frame'] =  0
   object['history'] = []
   object['history'].append([fc,x,y,w,h,max_x,max_y,max_px,intensity])
   return(object)

def center_point(x,y,w,h):
   cx = x + (w/2)
   cy = y + (h/2)
   return(cx,cy)

def find_in_hist(object,x,y,object_hist, img_w, img_h):
   if img_w > 1000:
      hd = 1
   else:
      hd = 0
   oid = object['oid']
   found = 0
   if hd == 1:
      md = 50 
   else:
      md = 30

   # check if this object_hist is stationary already.
   if len(object_hist) > 1:
      moving,desc = meteor_test_moving(object_hist)
      (max_cm,gaps,gap_events,cm_hist_len_ratio) = meteor_test_cm_gaps(object)
      object['max_cm'] = max_cm
      object['gaps'] = gaps
      object['gap_events'] = gap_events
      object['cm_hist_len_ratio'] = cm_hist_len_ratio
   else:
      moving = 0

   if moving == 1:
      fx = object_hist[0][1]
      fy = object_hist[0][2]
      lx = object_hist[-1][1]
      ly = object_hist[-1][2]
      first_last_slope = find_slope((fx,fy), (lx,ly))
      first_this_slope = find_slope((fx,fy), (x,y))
      last_this_slope = find_slope((lx,ly), (x,y))


   if len(object_hist) >=4:
      object_hist = object_hist[-3:]

   for hs in object_hist:
      w = 5
      h = 5
      if len(hs) == 9:
         fc,ox,oy,w,h,mx,my,max_px,intensity = hs
      if len(hs) == 8:
         fc,ox,oy,w,h,mx,my,max_px = hs
      
     
      cox = ox + int(w/2)
      coy = oy + int(h/2)
      dist = calc_dist((x,y), (cox,coy))
      print("DIST: ", object['oid'], dist, md, x,y,cox,coy)

      if dist < md:
         found = 1
         return(1)

   # if not found double distance and try again but only if moving!
   if moving == 1:
      md = md * 1.1
      for hs in object_hist:
         if len(hs) == 9:
            fc,ox,oy,w,h,mx,my,max_px, intensity = hs
         if len(hs) == 8:
            fc,ox,oy,w,h,mx,my,max_px = hs
         cox = ox + int(w/2)
         coy = oy + int(h/2)
         dist = calc_dist((x,y), (cox,coy))
         print("DIST: ", object['oid'], dist, md, x,y,cox,coy)
         if dist < md:
            found = 1
            return(1)


   return(found)

def save_object(object,objects):
   new_objects = []
   for obj in objects:
      if object['oid'] == obj['oid']:
         new_objects.append(object)
      else:
         new_objects.append(obj)
   return(new_objects)


def meteor_test_moving(hist):

   (max_x,max_y,min_x,min_y) = find_min_max_dist(hist)
   dist = calc_dist((min_x,min_y),(max_x,max_y))
   if dist <= 1:
      return 0, "Object is NOT moving."
   else:
      return 1, "Object is moving."

def find_min_max_dist(hist,mute_wh=0):
   max_x = 0
   max_y = 0
   min_x = 10000
   min_y = 10000
   #for hs in hist:
   #print("HIST: ", hs)

   for hs in hist:
      #print("HIST: ", len(hs))
      if len(hs) == 9:
         fn,x,y,w,h,mx,my,max_px,intensity = hs
      if len(hs) == 8:
         fn,x,y,w,h,mx,my,max_px = hs

      max_x, max_y,min_x,min_y = max_xy(x,y,w,h,max_x,max_y,min_x,min_y,mute_wh)

   return(max_x,max_y,min_x,min_y)

def max_xy(x,y,w,h,max_x,max_y,min_x,min_y,mute_wh=0):
   # ignore w,h
   if mute_wh == 1:
      w = 0
      h = 0

   if x + w > max_x:
      max_x = x + w
   if y + h > max_y:
      max_y = y + h
   if x < min_x:
      min_x = x
   if y < min_y:
      min_y = y
   return(max_x,max_y,min_x,min_y)


def arecolinear(points):
   xs = []
   ys = []
   is_straight = 0
   for x,y in points:
      xs.append(x)
      ys.append(y)
   ovall_m,ovall_b = best_fit_slope_and_intercept(xs,ys)
   if len(xs) > 2:
      fl_m,fl_b = best_fit_slope_and_intercept((xs[0],xs[-1]),(ys[0],ys[-1]))
   
      first_diff_m = abs(ovall_m - fl_m)
      first_diff_b = abs(ovall_b - fl_b)
   else:
      return(False)

   #print("STRAIGHT:", first_diff_m, first_diff_b)
   good = 0
   for i in range(0,len(xs)-1):
      if i > 0:
         tm,tb = best_fit_slope_and_intercept((xs[0],xs[i]),(ys[0],ys[i]))
         t_diff_m = abs(ovall_m - tm)
         t_diff_b = abs(ovall_b - tb)
         if t_diff_b <= 300 or t_diff_m <= .8:
            #print("GOOD STRAIGHT TM DIFF:", tm, tb, ovall_m, ovall_b, t_diff_m, t_diff_b)
            good = good + 1
         #else:
         #   print("BAD STRAIGHT TM DIFF:", tm, tb, ovall_m, ovall_b, t_diff_m, t_diff_b)
   perc_good = good / (len(xs) - 1)
   #print("STRAIGHT PERC GOOD:", perc_good, good, len(xs) -1)
   if perc_good > .8:
      return(True)
   else:
      return(False)
      

def arecolinear_old(points):
    xdiff1 = float(points[1][0] - points[0][0])
    ydiff1 = float(points[1][1] - points[0][1])
    xdiff2 = float(points[2][0] - points[1][0])
    ydiff2 = float(points[2][1] - points[1][1])

    # infinite slope?
    if xdiff1 == 0 or xdiff2 == 0:
        return xdiff1 == xdiff2
    elif ydiff1/xdiff1 == ydiff2/xdiff2:
        return True
    else:
        return False

def meteor_test_cm_gaps(object):
   hist = object['history']
   cm = 1
   max_cm = 0
   gaps = 0
   max_gaps = 0
   gap_events = 0
   last_frame = 0
   last_frame_diff = 0
   nomo = 0
   for hs in hist:
      if len(hs) == 9:
         fn,x,y,w,h,mx,my,max_px,intensity = hs
      if len(hs) == 8:
         fn,x,y,w,h,mx,my,max_px = hs
      #print("CM:", object['oid'], fn, last_frame, cm)
      if last_frame > 0:
         last_frame_diff = fn - last_frame - 1
      #print("LAST FRAME DIFF:", last_frame_diff) 
      if last_frame > 0 and last_frame_diff < 2:
         cm = cm + 1
         nomo = 0
         #print("YES CM!", fn, cm, nomo)
         if cm > max_cm:
            max_cm = cm
      else:
         #print("NO CM!", fn, cm, nomo)
         if last_frame != 0:
            nomo = fn - last_frame 
         
         if nomo > 1:
            cm = 0
            gaps = gaps + (fn - last_frame) - 1
            if fn - last_frame > 1:
               gap_events = gap_events + 1
            if fn - last_frame == 1:
               print("SINGLE FRAME GAP FIX IT!")
      if gaps > max_gaps:
         max_gaps = gaps
      last_frame = int(fn)

   # max cm per hist len 1 is best score. < .5 is fail.
   if max_cm > 0:
      cm_hist_len_ratio = max_cm / len(hist)
   else:
      cm_hist_len_ratio = 0
   max_cm = max_cm + 1
   return(max_cm,gaps,gap_events,cm_hist_len_ratio)

def find_dir_mod(mfd, mflag = 0):

   # [fc,x,y,w,h,mx,my,max_px]
   if mflag == 9:
      fx = mfd[0][1]
      fy = mfd[0][2]
      lx = mfd[-1][1]
      ly = mfd[-1][2]
   else:
      fx = mfd[0][2]
      fy = mfd[0][3]
      lx = mfd[-1][2]
      ly = mfd[-1][3]

   dir_x = fx - lx
   dir_y = fy - ly
   if dir_x < 0:
      x_dir_mod = 1
   else:
      x_dir_mod = -1
   if dir_y < 0:
      y_dir_mod = 1
   else:
      y_dir_mod = -1
   return(x_dir_mod, y_dir_mod)

def best_fit_slope_and_intercept(xs,ys):
    print("XS:", xs)
    print("YS:", ys)
    if xs[0] - xs[-1] == 0 and ys[0] - ys[-1] == 0:
       return(1,1)
    xs = np.array(xs, dtype=np.float64)
    ys = np.array(ys, dtype=np.float64)
    m = (((np.mean(xs)*np.mean(ys)) - np.mean(xs*ys)) /
         ((np.mean(xs)*np.mean(xs)) - np.mean(xs*xs)))

    b = np.mean(ys) - m*np.mean(xs)
    if math.isnan(m) is True:
       m = 1   
       b = 1   

    return m, b

def meteor_test_peaks(object):
   points = []
   sizes = []
   hist = object['history']
   for hs in hist:
      if len(hs) == 9:
         fn,x,y,w,h,mx,my,max_px,intensity = hs
      else:
         fn,x,y,w,h,mx,my,max_px = hs
      sizes.append(intensity)
      point = x+mx,y+my
      points.append(point)

   sci_peaks = signal.find_peaks(sizes)
   total_peaks = len(sci_peaks[0])
   total_frames = len(points)
   if total_frames > 0:
      peak_to_frame = total_peaks / total_frames
   else:
      peak_to_frame = 0

   return(sci_peaks, peak_to_frame)

def metframes_to_mfd(metframes, metconf, sd_video_file,json_conf,frame):
   metframes = sort_metframes(metframes)
   ih, iw = frame.shape[:2]
   hdm_x = 1920 / iw
   hdm_y = 1080 / ih
   red_file = sd_video_file.replace(".mp4", "-reduced.json")
   mjr = load_json_file(red_file)
   meteor_frame_data = []
   last_hd_x = None
   last_hd_y = None
   hd_segs = []
   xs = []
   ys = []
   azs = []
   els = []
   ras = []
   decs = []
   times = []

   hdxs = []
   hdys = []
   mags = []
   fcc = 0
   for fn in metframes:
      #if "HD" in sd_video_file or "SD" in sd_video_file: 
      #   frame_time,frame_time_str = calc_frame_time_new(sd_video_file, fn)
      #else:
      #   frame_time,frame_time_str = calc_frame_time(sd_video_file, fn)
      #metframes[fn]['ft'] = frame_time_str
      frame_time_str = metframes[fn]['ft']
      if "hd_x" not in metframes[fn] or 'x1' not in metframes[fn]:
         print("FRAME:", fn)
         metframes[fn]['x1'] = int(metframes[fn]['sd_x'] * hdm_x)
         metframes[fn]['y1'] = int(metframes[fn]['sd_y'] * hdm_y)
         metframes[fn]['hd_x'] = int(metframes[fn]['sd_cx'] * hdm_x)
         metframes[fn]['hd_y'] = int(metframes[fn]['sd_cy'] * hdm_y)
         metframes[fn]['w'] = metframes[fn]['sd_w']
         metframes[fn]['h'] = metframes[fn]['sd_h']

      if 'sd_intensity' in metframes[fn]:
         metframes[fn]['max_px'] = metframes[fn]['sd_intensity']
      else:
         print("Get missing intensity...")
      nx, ny, ra ,dec , az, el= XYtoRADec(metframes[fn]['hd_x'],metframes[fn]['hd_y'],sd_video_file,mjr['cal_params'],json_conf)
      metframes[fn]['ra'] = ra
      metframes[fn]['dec'] = dec
      metframes[fn]['az'] = az
      metframes[fn]['el'] = el
      azs.append(az)
      els.append(el)
      ras.append(ra)
      decs.append(dec)
      if 'sd_intensity' in metframes[fn]:
         mags.append(metframes[fn]['sd_intensity'])
      ftime = fcc / 25
      times.append(ftime)
      meteor_frame_data.append((frame_time_str,fn,int(metframes[fn]['hd_x']),int(metframes[fn]['hd_y']),int(metframes[fn]['w']),int(metframes[fn]['h']),int(metframes[fn]['max_px']),float(metframes[fn]['ra']),float(metframes[fn]['dec']),float(metframes[fn]['az']),float(metframes[fn]['el']) ))
      if last_hd_x is not None:
         hd_seg_len = calc_dist((last_hd_x, last_hd_y), (metframes[fn]['hd_x'], metframes[fn]['hd_y']))
         print("SEG:", fn, last_hd_x, last_hd_y, metframes[fn]['hd_x'], metframes[fn]['hd_y'], hd_seg_len)
         hd_segs.append(hd_seg_len)
      last_hd_x = metframes[fn]['hd_x']
      last_hd_y = metframes[fn]['hd_y']
      fcc = fcc + 1
   med_seg_len = float(np.median(hd_segs))
   metconf['hd_segs'] = hd_segs
   metconf['intensity'] = mags 
   metconf['azs'] = azs
   metconf['els'] = els
   metconf['ras'] = ras
   metconf['decs'] = decs
   metconf['times'] = times
   #metconf['med_seg_len'] = med_seg_len 
      
   return(meteor_frame_data, metframes, metconf)

def calc_frame_time_new(video_file, frame_num):
   (f_datetime, cam_id, f_date_str,Y,M,D, H, MM, S) = better_parse_file_date(video_file)
   extra_meteor_sec = int(frame_num) / 25
   meteor_frame_time = f_datetime + datetime.timedelta(0,extra_meteor_sec)
   meteor_frame_time_str = meteor_frame_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
   return(meteor_frame_time,meteor_frame_time_str)

def calc_frame_time(video_file, frame_num):
   (f_datetime, cam_id, f_date_str,Y,M,D, H, MM, S) = better_parse_file_date(video_file)
   el = video_file.split("-trim")
   min_file = el[0] + ".mp4"
   ttt = el[1].split(".")
   ttt[0] = ttt[0].replace("-stacked", "")
   trim_num = int(ttt[0])
   extra_sec = trim_num / 25
   start_trim_frame_time = f_datetime + datetime.timedelta(0,extra_sec)
   extra_meteor_sec = int(frame_num) / 25
   meteor_frame_time = start_trim_frame_time + datetime.timedelta(0,extra_meteor_sec)
   meteor_frame_time_str = meteor_frame_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]



   return(meteor_frame_time,meteor_frame_time_str)


def make_meteor_cnt_composite_images(json_conf, mfd, metframes, metconf, frames, sd_video_file):
   metframes = sort_metframes(metframes)
   cmp_images = {}
   cnt_max_w = 0
   cnt_max_h = 0
   for frame_data in mfd:
      
      frame_time, fn, hd_x,hd_y,w,h,max_px,ra,dec,az,el = frame_data
      print("MFD:", fn)
      if w > cnt_max_w:
         cnt_max_w = w
      if h > cnt_max_h:
         cnt_max_h = h

   cnt_w = int(cnt_max_w / 2)
   cnt_h = int(cnt_max_h / 2)
   #if cnt_w < 50 and cnt_h < 50:
   #   cnt_w = 50
   #   cnt_h = 50
   #if cnt_w < 40 and cnt_h < 40:
   #   cnt_w = 40
   #   cnt_h = 40
   if cnt_w < 25 and cnt_h < 25:
      cnt_w = 25
      cnt_h = 25
   else:
      cnt_w = 50
      cnt_h = 50
   #print(cnt_w,cnt_h)


   for frame_data in mfd:
      frame_time, fn, hd_x,hd_y,w,h,max_px,ra,dec,az,el = frame_data
      print("MFD:", fn)
      if fn not in metframes:
         fn = int(fn) 
      x1,y1,x2,y2 = bound_cnt(hd_x,hd_y,1920,1080,cnt_w)
      #x1 = hd_x - cnt_w
      #x2 = hd_x + cnt_w
      #y1 = hd_y - cnt_h
      #y2 = hd_y + cnt_h
      ifn = int(fn)
      print(ifn, len(frames))
      img = frames[ifn]
      hd_img = cv2.resize(img, (1920,1080))
      cnt_img = hd_img[y1:y2,x1:x2]
      metframes[fn]['x1'] = x1
      metframes[fn]['y1'] = y1
      metframes[fn]['x2'] = x2
      metframes[fn]['y2'] = y2
      print("X1:", x1,y1,x2,y2)
      print("CNT:", cnt_img.shape)
      cmp_images[fn] = cnt_img

   metframes = sort_metframes(metframes)
   mfd, metframes,metconf = metframes_to_mfd(metframes, metconf, sd_video_file,json_conf,frames[0])

   return(cmp_images, metframes)

def make_crop_images(sd_video_file, json_conf):
   if ".mp4" in sd_video_file:
      red_file = sd_video_file.replace(".mp4", "-reduced.json")
   elif "-reduced.json" in sd_video_file:
      red_file = sd_video_file
      sd_video_file = red_file.replace("-reduced.json", ".mp4")
   else:
      red_file = sd_video_file.replace(".json", "-reduced.json")



   frames = load_video_frames(sd_video_file, json_conf)
   red_data = load_json_file(red_file)

   cmp_imgs,metframes = make_meteor_cnt_composite_images(json_conf, red_data['meteor_frame_data'], red_data['metframes'], red_data['metconf'], frames, sd_video_file)

   metframes = sort_metframes(metframes)
   print("METFRAMES:", metframes)
   exit()

   prefix = red_data['sd_video_file'].replace(".mp4", "-frm")
   prefix = prefix.replace("SD/proc2/", "meteors/")
   prefix = prefix.replace("/passed", "")
   for fn in cmp_imgs:
      cv2.imwrite(prefix  + str(fn) + ".png", cmp_imgs[fn])
      print("UPDATING!", prefix + str(fn) + ".png")
      metframes[fn]['cnt_thumb'] = prefix + str(fn) + ".png"

   metframes = update_intensity(metframes, frames)
 
   mfd, metframes,metconf = metframes_to_mfd(metframes, red_data['metconf'], sd_video_file,json_conf,frames[0])
   print("LEN MET:", len(mfd), len(metframes))
   red_data['metconf'] = metconf
   red_data['metframes'] = metframes
   red_data['meteor_frame_data'] = mfd
   print("saving json:", red_file)
   make_light_curve(metframes,sd_video_file)
   save_json_file(red_file, red_data)

def sort_metframes(metframes):
   new_metframes = {}
   for key, mf in sorted(metframes.items()) :
      print("SORTED MF:", key, mf)
      new_metframes[key] = mf
   return(new_metframes)




   new_metframes = {}
   fns = []
   for fn in metframes:
      fns.append(int(fn))

   for fn in sorted(fns):
      ifn = int(fn)
      sfn = str(fn)
      if sfn in metframes :
         print("FN exists in metframes:", sfn, ifn)
         new_metframes[ifn] = metframes[sfn]
      elif ifn in metframes :
         print("FN int exists in metframes:", sfn, ifn)
         new_metframes[ifn] = metframes[ifn]
      else:
         print("FN does not exist in metframes!", sfn, ifn)
   return(new_metframes)

def perfect(video_file, json_conf):
   red_file = video_file.replace(".mp4", "-reduced.json")
   os.system("cd /home/ams/amscams/pythonv2/; ./autoCal.py cfit " + video_file)
   red_data = load_json_file(red_file)
   if "total_res_px" in red_data:
      xres = red_data['cal_params']['total_res_px']
   else: 
      xres = 9999
   if "total_stars" in red_data['cal_params']:
      total_stars = len(red_data['cal_params']['cat_image_stars'])
   else:
      print(video_file)
      exit()

   sd_frames = load_video_frames(video_file,json_conf)

   print("XY RES ERR:", xres , total_stars)
   for i in range(0,10):
      red_data = load_json_file(red_file)
      xres = red_data['cal_params']['total_res_px']
      total_stars = len(red_data['cal_params']['cat_image_stars'])
      print("TS/XRES:", xres)
      if total_stars > 6 and float(xres) > 2:
         os.system("cd /home/ams/amscams/pythonv2/; ./autoCal.py cfit " + video_file)
   print("RED:", red_file)
   red_data = load_json_file(red_file)
   #metframes, metconf = minimize_start_len(red_data['metframes'],sd_frames,red_data['metconf'],1)
   #red_data['metframes'] = metframes
   #red_data['metconf'] = metconf
   #save_json_file(red_file, red_data)


   os.system("cd /home/ams/amscams/pythonv2/; ./reducer3.py cm " + video_file)
       
   
