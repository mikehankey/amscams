#!/usr/bin/python3

from lib.MeteorTests import test_objects
import datetime
import time
import glob
import os
import math
import cv2
import math
import numpy as np
import scipy.optimize

from lib.VideoLib import get_masks, find_hd_file_new, load_video_frames, sync_hd_frames, make_movie_from_frames

from lib.UtilLib import check_running, angularSeparation, bound_cnt
from lib.CalibLib import radec_to_azel, clean_star_bg, get_catalog_stars, find_close_stars, XYtoRADec, HMS2deg, AzEltoRADec

from lib.ImageLib import mask_frame , stack_frames, preload_image_acc
from lib.ReducerLib import setup_metframes, detect_meteor , make_crop_images, perfect, detect_bp, best_fit_slope_and_intercept, id_object
from lib.MeteorTests import meteor_test_cm_gaps


import sys
from lib.CalibLib import distort_xy_new, find_image_stars, distort_xy_new, XYtoRADec, radec_to_azel, get_catalog_stars,AzEltoRADec , HMS2deg, get_active_cal_file, RAdeg2HMS, clean_star_bg
from lib.UtilLib import calc_dist, find_angle, bound_cnt, cnt_max_px

from lib.UtilLib import angularSeparation, convert_filename_to_date_cam, better_parse_file_date
from lib.FileIO import load_json_file, save_json_file, cfe
from lib.UtilLib import calc_dist,find_angle
import lib.brightstardata as bsd
from lib.DetectLib import eval_cnt


json_conf = load_json_file("../conf/as6.json")


def arecolinear(points ):
   xs = []
   ys = []
   is_straight = 0
   for x,y in points:
      xs.append(x)
      ys.append(y)

   tms = []
   tbs = []
   for i in range(0,len(xs)-1):
      if i > 0:
         tm,tb = best_fit_slope_and_intercept((xs[0],xs[i]),(ys[0],ys[i]))
         tms.append(tm)
         tbs.append(tb)

   avg_tm = np.median(tms)
   avg_tb = np.median(tbs)

   good_ms = 0
   good_bs = 0

   for tm in tms:
      if abs(tm-avg_tm) < 1:
         good_ms = good_ms + 1
         print("TM, AM, Diff:", tm, avg_tm, abs(tm-avg_tm))
      else:
         print("BAD TM, AM, Diff:", tm, avg_tm, abs(tm-avg_tm))

   for tb in tbs:
      if abs(tb-avg_tb) < 100:
         good_bs = good_bs + 1
         print("TB,AB, Diff:", tb, avg_tb, abs(tb-avg_tb))
      else:
         print("BAD TB,AB, Diff:", tb, avg_tb, abs(tb-avg_tb))

   tf = len(xs) - 2
   if tf > 0:
      b_perc = good_bs / tf
      m_perc = good_ms / tf
   print("PERC GOOD:", m_perc, b_perc)
   if m_perc + b_perc > 1:
      return(True)
   else:
      return(False)

def crop_frame(frame, cx,cy, crop_size=100):
   print(len(frame.shape), frame.shape)
   if len(frame.shape) == 2:
      h,w = frame.shape
   else:
      frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
      h,w = frame.shape

   x1,y1,x2,y2 = bound_cnt(cx,cy,w,h,crop_size)
   crop_img = frame[y1:y2,x1:x2]
   return(crop_img,x1,y1,x2,y2)

def make_cropframes(frames, frame_data):
   cropframes = []
   fc = 0
   for fn in frame_data: 
      if "x1" in frame_data[fn]:
         print("X1 found!")
         mx = int(frame_data[fn]['mx'])
         my = int(frame_data[fn]['my'])
         fc = int(fn) - 1
         crop_img,x1,y1,x2,y2 = crop_frame(frames[fc], mx, my, 100)
      else:
         crop_img = np.zeros((100,100),dtype=np.uint8)
      fc = fc + 1


      cropframes.append(crop_img)
   return(cropframes)

def process_video_frames(frames, video_file):
   cm = 0
   nomo = 0
   motion = 0
   masked_frames = []
   mask_points = []
   last_frame = cv2.cvtColor(frames[0], cv2.COLOR_BGR2GRAY)
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
   cropframes = []
   max_vals = []
   last_x = None
   last_y = None

   hd_datetime, hd_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(video_file)

   if "HD" in video_file:
      masks = get_masks(hd_cam,json_conf,1)
   else:
      masks = get_masks(hd_cam,json_conf)

   # build star mask
   median_frame = np.median(frames[:10], axis =0)
   median_frame = cv2.convertScaleAbs(median_frame)
   median_frame = cv2.cvtColor(median_frame, cv2.COLOR_BGR2GRAY)
   median_frame = cv2.GaussianBlur(median_frame, (7, 7), 0)

   min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(median_frame)
   px_diff = max_val - np.mean(median_frame)
   thresh_val = np.mean(median_frame) + (px_diff/5)
   _, image_thresh = cv2.threshold(median_frame.copy(), thresh_val, 255, cv2.THRESH_BINARY)
   mask_cnts =  do_contours(image_thresh)
   mask_points = []
   for pnt in mask_cnts:
      x,y,w,h = pnt
      mask_points.append((x,y))
   if "HD" in video_file:
      mask_size = 8
   else:
      mask_size = 5
   #median_frame = mask_frame(median_frame, mask_points, masks,mask_size)
   #cv2.imshow('pepe', median_frame)
   #cv2.waitKey(0)
   objects = []
   for frame in frames:
      
      crop_img = np.zeros((200,200),dtype=np.uint8)
      orig_frames.append(frame.copy())
      frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
      frame = mask_frame(frame, mask_points, masks,mask_size)
      show_frame = frame.copy()

      frame_data[fn] = {}
      frame_data[fn]['fn'] = fn
      blur_frame = cv2.GaussianBlur(frame, (7, 7), 0)
      blur_last = cv2.GaussianBlur(last_frame, (7, 7), 0)
      #subframe = cv2.subtract(frame,last_frame)
      subframe = cv2.subtract(frame,last_frame)
      subframes.append(subframe)



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
      if max_val - avg_val > 10:
         if last_x is not None:
            last_seg_dist = calc_dist((mx,my), (last_x,last_y))
            frame_data[fn]['last_seg_dist'] = last_seg_dist
         else:
            last_seg_dist = 0
            frame_data[fn]['last_seg_dist'] = last_seg_dist

         thresh_val = np.max(subframe) - 50
         if thresh_val < 10:
            thresh_val = 10

         _, subframe_thresh = cv2.threshold(subframe.copy(), thresh_val, 255, cv2.THRESH_BINARY)
         frame_cnts = do_contours(subframe_thresh)
         frame_data[fn]['frame_cnts'] = frame_cnts
         print("CNTS:", frame_cnts)
         obj_cnts = []
         for cnt in frame_cnts:
            cx, cy, cw, ch = cnt
            object, objects = id_object(None, objects,fn, (int(mx),int(my)), int(max_val), int(sum_val), img_w, img_h)
            if "oid" in object:
               obj_cnts.append((object['oid'], cx,cy,cw,ch))
               frame_data[fn]['obj_cnts'] = obj_cnts

         if 1 < last_seg_dist < 20 :
            motion = 1
            print("DETECTION!:", fn, max_val, sum_val)
         if motion == 1:
            if cm == 0:
               print("START FIRST EVENT.")
               first_eframe = fn -1
            cm = cm + 1
            #object, objects = id_object(None, objects,fn, (int(mx),int(my)), int(max_val), int(sum_val), img_w, img_h)
            #if "oid" in object:
            #   frame_data[fn]['oid'] = object['oid']
            #if "oid" in object:
            #   print("OBJECT:", object['oid'])

         #blob_x, blob_y,blob_w,blob_h = find_blob_center(frame, mx,my,max_val)
         #avg_x = int(blob_x + mx / 2)
         #avg_y = int(blob_y + my / 2)
         #cv2.circle(stack_img,(avg_x,avg_y), 20, (255), -1)
         crop_img, x1,y1,x2,y2 = crop_frame(frame, mx, my)
         frame_data[fn]['x1'] = x1
         frame_data[fn]['y1'] = y1
         frame_data[fn]['x2'] = x2
         frame_data[fn]['y2'] = y2
         frame_data[fn]['crop_intensity'] = int(np.sum(crop_img))
         cv2.rectangle(show_frame, (x1, y1), (x2, y2), (128,128,128), 1)
         cv2.rectangle(subframe, (x1, y1), (x2, y2), (128,128,128), 1)

         #frame_data[fn]['blob_x'] = int(blob_x)
         #frame_data[fn]['blob_y'] = int(blob_y)
         #frame_data[fn]['blob_w'] = int(blob_w)
         #frame_data[fn]['blob_h'] = int(blob_h)

         #cv2.circle(stack_img,(blob_x,blob_y), blob_w, (255), -1)
         if last_x is not None:
            #print("LINE:", blob_x, blob_y, last_x, last_y)
            #cv2.line(stack_img, (blob_x,blob_y), (last_x,last_y), (255), 2)
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
            events.append([first_eframe, fn-2])
            stacks.append(stack_img)
            stack_img = np.zeros((h,w),dtype=np.uint8)
            motion = 0
            cm = 0
         if cm == 1 and nomo > 3:
            cm = 0
         nomo = nomo + 1
         #blob_x = None
         #blob_y = None
      cv2.imshow('pepe2', subframe)
      cv2.waitKey(70)
      frame_data[fn]['cm'] = cm
      frame_data[fn]['nonmo'] = nomo
      print(fn, max_val, cm, nomo)
      fn = fn + 1
      last_x = mx
      last_y = my
      cropframes.append(crop_img)
      #cv2.imshow('pepe', show_frame)

   if cm >= 2 :
      print("Add Final Event.")
      events.append([first_eframe, fn])
      stacks.append(stack_img)
      motion = 0

   print("FRAMES:", len(frames))
   print("BP EVENTS:", len(events))
   video_data = {}
   video_data['frame_data'] = frame_data
   video_data['events'] = events
   video_data['objects'] = objects
   return(video_data, subframes, cropframes )







def check_video_status(file):
   frame_data_file = file.replace(".mp4", "-framedata.json")
   processed = 0
   if cfe(file) == 0:
      desc = "File does not exist! " + file
      exit()
   if "trim" in file:
      mode = "trim_file"
   else:
      mode = "min_file"
   if "HD" in file:
      hd = 1
   else:
      hd = 0
   if cfe(frame_data_file) == 1:
      frame_data = load_json_file(frame_data_file)
      processed = 1
   else:
      frame_data = {}
   return(1, mode, hd, processed, frame_data, frame_data_file, "file good.")
   

def run_detect(video_file, show):
   # check the file exists and current processing status
   status, mode, hd, processed, video_data, video_data_file, desc = check_video_status(video_file)

   #load the frames
   frames = load_video_frames(video_file, json_conf, 0, 0, [], 1)

   #check for a bright pixel detection inside the frame set
   if processed != 1:
      print("Not processed!")
      video_data, subframes, cropframes = process_video_frames(frames, video_file)
    
      meteor_objs = [] 
      # check if any of the objects are meteors
      for obj in video_data['objects']:
         if "meteor" in obj: 
            if obj['meteor'] == 1:
               meteor_objs.append(obj['oid'])
      

      for event in video_data['events']:
         start, end = event
         for fn in range(start-10, end):
            frame = cropframes[fn]
            if fn in video_data['frame_data']:
               print(video_data['frame_data'][fn])
            cv2.imshow('pepe', frame)
            cv2.waitKey(70)
         video_data['orig_video_file'] = video_file
         video_data['video_data_file'] = video_data_file
         video_data = evaluate_frames(video_data)
         print("FRAMES:", video_data['frame_data'])
         # see if trim file exists for meteor. if not make it.
   else: 
      subframes = []

   # check the objects and see if any of them are meteors. If not save the frame data file and exit.
   meteor_objs = []
   meteor_in_clip = 0
   objects,meteor_found = test_objects(video_data['objects'],frames) 

   for obj in objects:
      if obj['meteor'] == 1:
         meteor_in_clip = 1
         meteor_objs.append(obj['oid'])
   if meteor_in_clip == 0:
      save_json_file(video_data_file, video_data)
      print("NO meteors here.")
      exit()

   print("METEOR OBJS:", meteor_objs)

   # determine the blob positions if it hasn't been done yet
   cropframes = make_cropframes(frames, video_data['frame_data'])
   frame_data = find_blobs_in_crops(cropframes, video_data['frame_data'])
   video_data['frame_data'] = frame_data


   # TRIM OUT A VIDEO FILE FOR EACH METEOR EVENT IN THIS CLIP IF IT DOESN'T EXIST YET
   
   ec = 0
   for event in video_data['events']:
      start, end = event
      is_meteor = 0
      # make sure the object inside this event is actually a meteor and not something else. 
      for fc in range(start,end):
         if fc not in frame_data:
            fc = str(fc )
         if "obj_cnts" in frame_data[fc]:
            these_objs = []
            for cnt in frame_data[fc]['obj_cnts']:
               oid = cnt[0]
               if int(oid) in meteor_objs or str(oid) in meteor_objs:
                  is_meteor = 1
                  if ec in video_data['event_data']:
                     video_data['event_data'][ec]['meteor'] = 1
                  if str(ec) in video_data['event_data']:
                     ec = str(ec)
                     video_data['event_data'][ec]['meteor'] = 1

      if is_meteor == 1:
         print("METEOR FOUND!:")
         

         meteor_video_filename, event_start_time = make_meteor_video_filename(video_file, start, hd)
         fns, start_buff, end_buff = add_frame_buffer(len(frames), start, end)

         meteor_json = make_meteor_json(event, video_data, event_start_time, meteor_video_filename ) 
         meteor_json_filename = meteor_video_filename.replace(".mp4", ".json")
         save_json_file(meteor_json_filename, meteor_json)
     
         if cfe(meteor_video_filename) == 0:
            make_movie_from_frames(frames, fns, meteor_video_filename)
         print("Meteor Movie Made:", meteor_video_filename)
         print("Meteor JSON Saved:", meteor_json_filename)
      ec = int(ec) + 1


   video_data['sd_objects'] = objects
   video_data['meteor_found'] = meteor_found
   print("VIDEO DATA FILE:", video_data_file)
   save_json_file(video_data_file, video_data)    

def make_meteor_json(event, video_data, event_start_time, meteor_video_filename):
   meteor_json = {}
   meteor_json['metframes'] = {}
   meteor_json['metconf'] = {}
   start, end = event
   metframes = {}
   fd = video_data['frame_data']

   for fn in range(start, end):
      if fn not in fd:
         fn = str(fn)
      metframes[fn] = fd[fn]

   meteor_json['metframes'] = metframes
   return(meteor_json)

def add_frame_buffer(total_frames, start_frame, end_frame):
   first_frame = 0
   last_frame = end_frame
   start_buff = 0 
   end_buff = 0 
   if start_frame - 10 > 0:
      first_frame = start_frame - 10
      start_buff = 10
   if end_frame + 10 <= total_frames-1:
      last_frame = end_frame + 10
      end_buff = 10
   if start_frame - 25 > 0:
      first_frame = start_frame - 25
   if end_frame + 25 <= total_frames:
      last_frame = end_frame + 25
   fns = []
   for i in range (first_frame , last_frame ):
      fns.append(i) 

   return(fns, start_buff, end_buff)


def make_meteor_video_filename(video_file, start, hd):
   hd_datetime, hd_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(video_file)
   if "trim" not in video_file:
      orig_trim_num = 0
   else:
      ttt = video_file.split("trim")
 
      if "HD" in ttt[-1]:
         el = ttt[-1].split("-")
         orig_trim_num = int(el[1])
      else:
         print("SD NOT DONE YET:", ttt[-1])
         exit()

   new_trim_num = orig_trim_num + start
   trim_seconds = new_trim_num / 25

   event_start_time = hd_datetime + datetime.timedelta(0,trim_seconds)

   day = event_start_time.strftime('%Y_%m_%d')
   event_start_time_str = event_start_time.strftime('%Y_%m_%d_%H_%M_%S_%f')[:-3]
   if hd == 1:
      hd_str = "HD"
   else:
      hd_str = "SD"

   meteor_filename = event_start_time_str + "_" + hd_cam + "_" + json_conf['site']['ams_id'] + "_" + hd_str + ".mp4"
   meteor_dir = "/mnt/ams2/meteor_archive/" + day + "/" 
   if cfe(meteor_dir, 1) == 0:
      os.system("mkdir " + meteor_dir)

   print("METEOR FILENAME IS:", meteor_filename)
 
   meteor_video_filename = meteor_dir + meteor_filename  
   return(meteor_video_filename, event_start_time)


def do_contours(image_thresh):

   cnt_res = cv2.findContours(image_thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

   if len(cnt_res) == 3:
      (_, cnts, xx) = cnt_res
   elif len(cnt_res) == 2:
      (cnts, xx) = cnt_res
   my_cnts = []
   if len(cnts) > 0:
      for (i,c) in enumerate(cnts):
         x,y,w,h = cv2.boundingRect(cnts[i])
         my_cnts.append((x,y,w,h))
   return(my_cnts)


def find_blobs_in_crops(cropframes, frame_data):
   for fn in frame_data:
      if "x1" in frame_data[fn]:
         print("Look for blob: ", fn) 
         cfn = int(fn)
         crop_img = cropframes[cfn]

         min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(crop_img)
         avg_px = np.mean(crop_img) 
         px_diff = max_val - avg_px
         thresh_val = avg_px + (px_diff / 5)
         _, image_thresh = cv2.threshold(crop_img.copy(), thresh_val, 255, cv2.THRESH_BINARY)
         my_cnts = do_contours(image_thresh)
         #frame_data[fn]['my_cnts'] = my_cnts

         if len(my_cnts) > 0:
            cxs = []
            cys = []
            cws = []
            chs = []
            for x,y,w,h in my_cnts:
               #cv2.rectangle(image_thresh, (x, y), (x+w, y+h), (128,128,128), 1)
               cxs.append(x)
               cys.append(y)
               cws.append(w)
               chs.append(h)
            cnt_x = np.mean(cxs)
            cnt_y = np.mean(cys)
            cnt_w = np.mean(cws)
            cnt_h = np.mean(chs)
         frame_data[fn]['cnt_x'] = cnt_x
         frame_data[fn]['cnt_y'] = cnt_y
         frame_data[fn]['cnt_w'] = cnt_w
         frame_data[fn]['cnt_h'] = cnt_h
         cv2.rectangle(image_thresh, (x, y), (x+w, y+h), (128,128,128), 1)
         

         print(my_cnts)

         #cv2.imshow('pepe', image_thresh)
         #cv2.waitKey(70)
   return(frame_data)

def evaluate_frames(video_data):
   # Evaluate the events in the frame set to determine if they could be meteors.
   pos_meteors = []
   ec = 0
   maybe_meteors = []
   if "event_data" in video_data:
      event_data = video_data['event_data']
   else:   
      event_data = {}

   for start,end in video_data['events']:
      # check for basic stuff and weed out the obvious non meteors
      cm_end = int(end) -2
      if start not in video_data['frame_data']: 
         start = str(start)
         end = str(end)
         cm_end = str(cm_end)

      fd = video_data['frame_data']
      fxs = [] 
      fys = [] 
      fns = [] 
      segs = [] 
      start_segs = [] 
      first_x = None
      last_x = None
      for fc in range(start,end):
         if "mx" in fd[fc]:
            if first_x is None:
               first_x = fd[fc]['mx']
               first_y = fd[fc]['my']
            x = fd[fc]['mx']
            y = fd[fc]['my']
            fn = fd[fc]['fn']
            fxs.append(x)
            fys.append(y)
            fns.append(fn)
            if last_x is not None:
               dist = calc_dist((x,y), (last_x,last_y))
               dist_from_first = calc_dist((x,y), (first_x,first_y))
               seg = dist
               start_seg = dist_from_first
               segs.append(seg)
               start_segs.append(start_seg)
               fd[fc]['last_seg_dist'] = seg
               fd[fc]['dist_from_start'] = start_seg
            else:
               fd[fc]['last_seg_dist'] = 0

         last_x = x
         last_y = y
  
      video_data['frame_data'] = fd
      
      min_x = min(fxs)
      max_x = max(fxs)
      min_y = min(fxs)
      max_y = max(fxs)
      min_max_dist = calc_dist((min_x,min_y), (max_x,max_y))
        
      elp_frames = int(end) - int(start)
      print("END: ", end)
      max_cm = video_data['frame_data'][cm_end]['cm'] + 1
      motion_frame_ratio = max_cm / elp_frames
      print("Event #: ", ec)
      print("Event Start/End: ", start, end)
      print("Elapsed Frames: ", elp_frames)
      print("Consecutive Motion: ", max_cm)
      print("Motion/Frame Ratio: ", motion_frame_ratio)
      print("MAX Distance: ", min_max_dist)

      # first basic non meteor test on motion_frame_ratio
      if motion_frame_ratio < .6 or min_max_dist < 5 and elp_frames < 250:
         maybe_meteor = 0
      else:
         maybe_meteor = 1

      print("Maybe Meteor: ", maybe_meteor)
      if ec not in event_data:
         event_data[ec] = {}
         event_data[ec]['event_id'] = ec
         event_data[ec]['event_start'] = start
         event_data[ec]['event_end'] = end
         event_data[ec]['elp_frames'] = elp_frames 
         event_data[ec]['max_cm'] = max_cm
         event_data[ec]['motion_frame_ratio'] = motion_frame_ratio
         event_data[ec]['maybe_meteor'] = maybe_meteor
         event_data[ec]['xs'] = fxs 
         event_data[ec]['ys'] = fys 
         event_data[ec]['fns'] = fns
         event_data[ec]['segs'] = segs
         event_data[ec]['start_segs'] = start_segs
         event_data[ec]['min_max_dist'] = min_max_dist
      ec = ec + 1

   # do more specific tests if passed the first test
   points = []
   for ec in event_data:
      xs = []
      ys = []
      sum_vals = []
      max_vals = []
      start = int(event_data[ec]['event_start'])
      end = int(event_data[ec]['event_end'])

      for fn in range(start, end):
         if fn not in video_data['frame_data']:
            fn = str(fn)
         xs.append(video_data['frame_data'][fn]['mx'])
         ys.append(video_data['frame_data'][fn]['my'])
         points.append((video_data['frame_data'][fn]['mx'], video_data['frame_data'][fn]['my']))
         sum_vals.append(video_data['frame_data'][fn]['sum_val'])
         max_vals.append(video_data['frame_data'][fn]['max_val'])
      is_straight  = arecolinear(points) 
      event_data[ec]['xs'] = xs
      event_data[ec]['ys'] = ys
      event_data[ec]['sum_vals'] = sum_vals
      event_data[ec]['max_vals'] = max_vals
      event_data[ec]['is_straight'] = is_straight
 
   video_data['event_data'] = event_data
   return(video_data)


cmd = sys.argv[1]
file = sys.argv[2]
try:
   show = int(sys.argv[3])
except:
   show = 0

if cmd == 'rd' or cmd == 'run_detect':
   run_detect(file,show)


