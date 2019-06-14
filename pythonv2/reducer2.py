#!/usr/bin/python3

import datetime
import time
import glob
import os
import math
import cv2
import math
import numpy as np
import scipy.optimize
from fitMulti import minimize_poly_params_fwd
from lib.VideoLib import get_masks, find_hd_file_new, load_video_frames
from lib.UtilLib import check_running, angularSeparation
from lib.CalibLib import radec_to_azel, clean_star_bg, get_catalog_stars, find_close_stars, XYtoRADec, HMS2deg, AzEltoRADec

from lib.ImageLib import mask_frame , stack_frames, preload_image_acc
#from lib.ReducerLib import setup_metframes  
from lib.MeteorTests import meteor_test_cm_gaps 


#import matplotlib.pyplot as plt
import sys
#from caliblib import distort_xy,
from lib.CalibLib import distort_xy_new, find_image_stars, distort_xy_new, XYtoRADec, radec_to_azel, get_catalog_stars,AzEltoRADec , HMS2deg, get_active_cal_file, RAdeg2HMS, clean_star_bg
from lib.UtilLib import calc_dist, find_angle, bound_cnt, cnt_max_px

from lib.UtilLib import angularSeparation, convert_filename_to_date_cam, better_parse_file_date
from lib.FileIO import load_json_file, save_json_file, cfe
from lib.UtilLib import calc_dist,find_angle
import lib.brightstardata as bsd
from lib.DetectLib import eval_cnt, id_object
json_conf = load_json_file("../conf/as6.json")

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



def make_meteor_cnt_composite_images(json_conf, mfd, metframes, frames, sd_video_file):
   cmp_images = {}
   #frames = load_video_frames(sd_video_file, json_conf)
   cnt_max_w = 0
   cnt_max_h = 0
   for frame_data in mfd:
      frame_time, fn, hd_x,hd_y,w,h,max_px,ra,dec,az,el = frame_data
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
      x1,y1,x2,y2 = bound_cnt(hd_x,hd_y,1920,1080,cnt_w)
      #x1 = hd_x - cnt_w
      #x2 = hd_x + cnt_w
      #y1 = hd_y - cnt_h
      #y2 = hd_y + cnt_h
      ifn = int(fn)
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
   return(cmp_images, metframes)



def best_fit_slope_and_intercept(xs,ys):
    xs = np.array(xs, dtype=np.float64)
    ys = np.array(ys, dtype=np.float64)
    m = (((np.mean(xs)*np.mean(ys)) - np.mean(xs*ys)) /
         ((np.mean(xs)*np.mean(xs)) - np.mean(xs*xs)))

    b = np.mean(ys) - m*np.mean(xs)

    return m, b


def find_blob_center(cnt_img,img,norm_img,x1,y1,x2,y2,size):
   min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(cnt_img)
   px_diff = max_val - min_val
   if px_diff < 10:
      thresh_val = np.mean(cnt_img) - 5 
   else:
      thresh_val = max_val - int(px_diff /2)
   _ , thresh_img = cv2.threshold(cnt_img.copy(), thresh_val, 255, cv2.THRESH_BINARY)
   cnt_res = cv2.findContours(thresh_img.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
   if len(cnt_res) == 3:
      (_, cnts, xx) = cnt_res
   elif len(cnt_res) == 2:
      (cnts, xx) = cnt_res
   pos_cnts = []
   if len(cnts) > 0:
      for (i,c) in enumerate(cnts):
         x,y,w,h = cv2.boundingRect(cnts[i])
         size = w + h
         mx = int(x + (w / 2))
         my = int(y + (h / 2))
         pos_cnts.append((x,y,w,h,size,mx,my))
      temp = sorted(pos_cnts, key=lambda x: x[4], reverse=True)
      min_val, max_val, min_loc, (bmx,bmy)= cv2.minMaxLoc(cnt_img)
      (x,y,w,h,size,mx,my) = temp[0]
      blob_x = mx + x1
      blob_y = my + y1
      max_px = max_val
      blob_w = w
      blob_h = h
   # ok now do 2nd pass
   sz = 20
   nx1,ny1,nx2,ny2= bound_cnt(blob_x,blob_y,img.shape[1],img.shape[0],sz)
   cnt_img2 = img[ny1:ny2,nx1:nx2]
   min_val, max_val, min_loc, (bmx,bmy)= cv2.minMaxLoc(cnt_img2)
   thresh_val = max_px - 30
   _ , thresh_img2 = cv2.threshold(cnt_img2.copy(), thresh_val, 255, cv2.THRESH_BINARY)
   cnt_res = cv2.findContours(thresh_img2.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
   if len(cnt_res) == 3:
      (_, cnts, xx) = cnt_res
   elif len(cnt_res) == 2:
      (cnts, xx) = cnt_res
   pos_cnts = []
   if len(cnts) > 0:
      for (i,c) in enumerate(cnts):
         x,y,w,h = cv2.boundingRect(cnts[i])
         size = w + h
         mx = int(x + (w / 2))
         my = int(y + (h / 2))
         pos_cnts.append((x,y,w,h,size,mx,my))
      temp = sorted(pos_cnts, key=lambda x: x[4], reverse=True)
      norm_cnt_img = img[y1:y2,x1:x2]
      min_val, max_val, min_loc, (bmx,bmy)= cv2.minMaxLoc(norm_cnt_img)
      (x,y,w,h,size,mx,my) = temp[0]
      blob_x = mx + nx1
      blob_y = my + ny1
      max_px = max_val
   return(blob_x, blob_y,max_val,blob_w,blob_h)     


def check_cnt_bounds(hd_x1, hd_y1, hd_x2, hd_y2 ):
   if hd_x1 < 0:
      hd_x2 = hd_x2 + (hd_x1*-1)
      hd_x1 = 0
   if hd_y1 < 0:
      hd_y2 = hd_y2 + (hd_y1*-1)
      hd_y1 = 0

   if hd_x2 > 1920:
      hd_x1 = hd_x1 - (hd_x2 -  1920)
      hd_x2 = 1920
   if hd_y2 > 1080:
      hd_y1 = hd_y1 - (hd_y2 -  1080)
      hd_y2 = 1080

   return(hd_x1, hd_y1, hd_x2, hd_y2)

def find_cnts(fn,image, thresh_val, objects):

  
   min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(image)
   avg_val = np.mean(image)
   #px_diff = max_val - avg_val
   #thresh_val = avg_val + (px_diff / 2)
   thresh_val = 25
   _ , thresh_img = cv2.threshold(image.copy(), thresh_val, 255, cv2.THRESH_BINARY)
   marked_image = image.copy()
   cnt_res = cv2.findContours(thresh_img.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
   if len(cnt_res) == 3:
      (_, cnts, xx) = cnt_res
   elif len(cnt_res) == 2:
      (cnts, xx) = cnt_res
   pos_cnts = []
   if len(cnts) > 0:
      for (i,c) in enumerate(cnts):

         x,y,w,h = cv2.boundingRect(cnts[i])
         if w > 1 and h > 1 and w != image.shape[1] and h != image.shape[0]:
            object, objects = id_object(cnts[i], objects,fn, (x,y),1)
            print("OBJECT:", object)
            if "oid" in object:
               oid = object['oid']
            print("OBEJECTS:", len(objects))
            #print("OBJ:", object)
            size = w + h
            cx = int(x + (w / 2))
            cy = int(y + (h / 2))
            if "oid" in object:
               print("ADDING OID TEXT:", x,y, oid)
               if show == 1:
                  cv2.putText(marked_image, str(oid),  (cx,cy), cv2.FONT_HERSHEY_SIMPLEX, .8, (255,255,255), 1)
                  cv2.imshow("TEST", marked_image)
                  cv2.waitKey(1)
            cv2.rectangle(marked_image, (x, y), (x+w, y+h), (128), 1)
            cnt_img = image[y:y+h,x:x+w]
            min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(cnt_img)
            pos_cnts.append((x,y,w,h,cx,cy,x+mx,y+my))
   object_id = 0
   return(pos_cnts, marked_image, objects,object_id)

def fine_reduce(mrf, json_conf, show):
   print(mrf, show)
   objects = []
   if show == 1:
      cv2.namedWindow('pepe')
   mjr = load_json_file(mrf)
   sd_video_file = mjr['sd_video_file']
   sd_frames = load_video_frames(mjr['sd_video_file'], json_conf)
   frames = []
   for frame in sd_frames:
      #hd_img = frame
      hd_img = cv2.resize(frame, (1920,1080))
      frames.append(hd_img)


   #metframes, metconf = setup_metframes(mjr['meteor_frame_data'])
 
   #print(len(frames))
   cnt_objs = {}

   image_acc = preload_image_acc(frames)

   abs_image_acc = cv2.convertScaleAbs(image_acc)

   avg_px = np.mean(abs_image_acc)
   max_px = np.max(abs_image_acc)
   min_px = np.min(abs_image_acc)
   px_diff = max_px - min_px 
   thresh_val = avg_px + (px_diff / 4)
   #tmp_mask_points, marked_mask_image, objects, object_id= find_cnts(0,abs_image_acc, thresh_val, objects)
   tmp_mask_points, marked_mask_image, objects, object_id= find_cnts(0,frames[0], thresh_val, objects)
   nobjs = []
   for object in objects:
      object['status'] = 'star'
      nobjs.append(object)
   objects = nobjs


  
   mask_points = [] 
   for x,y,w,h,cx,cy,mx,my in tmp_mask_points:
      if w < 25 and h < 25:
         mask_points.append((x,y))
   mimg = mask_frame(abs_image_acc, mask_points, [],5)

   last_frame = None
   first_frame = None
   last_subtracted= None
   clean_frames = []
   fcc = 0
   for frame in frames:
      work_frame = frame.copy()
      work_frame = cv2.convertScaleAbs(work_frame)
      work_frame = mask_frame(work_frame, mask_points, [],5)
      color_frame = cv2.cvtColor(frame,cv2.COLOR_GRAY2RGB)
      blur_frame = cv2.GaussianBlur(work_frame, (7, 7), 0)
 
      #if show == 1:
         #if fcc in metframes:
         #   cv2.putText(color_frame, str(fcc),  (10,10), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,0,255), 1)
         #else:
         #   cv2.putText(color_frame, str(fcc),  (10,10), cv2.FONT_HERSHEY_SIMPLEX, .4, (255,255,255), 1)


      image_diff = cv2.absdiff(image_acc.astype(work_frame.dtype), work_frame,)
      alpha = .5
      hello = cv2.accumulateWeighted(image_diff, image_acc, alpha)

      if first_frame is not None:

         sub_first = cv2.subtract(work_frame,first_frame)
         sub_last = cv2.subtract(work_frame,last_frame)
         image_acc2 = cv2.convertScaleAbs(image_acc)
         sub_acc = cv2.subtract(work_frame,image_acc2)
         subtracted = sub_acc 

         thresh_val = 20
         #sub_first_cnts, marked_image_first,object,object_id = find_cnts(fcc,sub_first, thresh_val, objects)
         sub_last_cnts, marked_image_last,objects,sub_last_object_id = find_cnts(fcc,sub_last, thresh_val, objects)
         #subtracted_cnts, marked_image_subtracted,objects,object_id = find_cnts(fcc,subtracted, thresh_val, objects)


         if fcc not in cnt_objs:
            cnt_objs[fcc] = {}

         #cnt_objs[fcc]['sub_first'] = sub_first_cnts 
         cnt_objs[fcc]['sub_last'] = sub_last_cnts 
         #cnt_objs[fcc]['subtracted_cnts'] = subtracted_cnts
         #cnt_objs[fcc]['subtracted_cnts'] = subtracted_cnts
         cnt_objs[fcc]['sub_sub_cnts'] = []

         if last_frame is not None and last_subtracted is not None:
            sub_sub = cv2.subtract(subtracted,last_subtracted)
            if fcc > 5:
               sub_sub_cnts, marked_image_sub_sub,objects,object_id = find_cnts(fcc,sub_sub, thresh_val,objects)
               cnt_objs[fcc]['sub_sub_cnts'] = sub_sub_cnts
               if show == 1:
                  show_img = cv2.resize(marked_image_sub_sub, (960,540))
                  cv2.imshow('sub_sub', show_img)
                  cv2.moveWindow('sub_sub',1100,10)

                  show_img = cv2.resize(marked_image_last, (960,540))
                  cv2.imshow('last', show_img)
                  cv2.moveWindow('last',1800,10)

               clean_frames.append(sub_sub) 
            else:
               clean_frames.append(sub_last) 
         else:
            clean_frames.append(sub_last) 
         if show == 1:
            show_img = cv2.resize(color_frame, (960,540))
            cv2.imshow('color_frame', show_img)
            cv2.moveWindow('color_frame',10,10)
            cv2.waitKey(1)
      else:
         clean_frames.append(frame) 

      if last_frame is not None:
         last_subtracted = subtracted 
      last_frame = work_frame
      if first_frame is None:
         first_frame = work_frame
      fcc = fcc + 1

   fcc = 0
   mf_objs = {}
   for frame in frames:
      mf_objs[fcc] = {}
      mf_objs[fcc]['objects'] = []
      mf_objs[fcc]['object_ids'] = []
      mf_objs[fcc]['avg_x'] = 0
      mf_objs[fcc]['avg_y'] = 0
      fcc = fcc + 1
   new_objs = []
   meteor_objs = []
   fcc = 0

   for fn in cnt_objs:
      xs = []
      ys = []
      image = frames[fn].copy()
      #for cnt_o in cnt_objs[fn]['sub_first']:
      #   (x,y,w,h,cx,cy,mx,my) = cnt_o
      ##   xs.append(cx)
      #   xs.append(mx)
      #   ys.append(cy)
      #   ys.append(my)
      for cnt_o in cnt_objs[fn]['sub_last']:
         (x,y,w,h,cx,cy,mx,my) = cnt_o
         xs.append(cx)
         xs.append(mx)
         ys.append(cy)
         ys.append(my)
      #for cnt_o in cnt_objs[fn]['subtracted_cnts']:
      #   (x,y,w,h,cx,cy,mx,my) = cnt_o
      #   xs.append(cx)
      #   xs.append(mx)
      #   ys.append(cy)
      #   ys.append(my)
      for cnt_o in cnt_objs[fn]['sub_sub_cnts']:
         (x,y,w,h,cx,cy,mx,my) = cnt_o
         xs.append(cx)
         xs.append(mx)
         ys.append(cy)
         ys.append(my)

      cnt_objs[fn]['xs'] = xs
      cnt_objs[fn]['ys'] = ys
      if len(xs) > 0:
         cnt_objs[fn]['avg_x'] = int(np.median(xs))
         cnt_objs[fn]['avg_y'] = int(np.median(ys))
      else:
         cnt_objs[fn]['avg_x'] = 0
         cnt_objs[fn]['avg_y'] = 0

      if cnt_objs[fn]['avg_x'] != 0 and cnt_objs[fn]['avg_y'] != 0:
         cv2.rectangle(image, (x-5, y-5), (x+5, y+5), (128), 1)

      mf_objs[fn]['avg_x'] = cnt_objs[fn]['avg_x'] 
      mf_objs[fn]['avg_y'] = cnt_objs[fn]['avg_y'] 
      avg_x = mf_objs[fn]['avg_x'] 
      avg_y = mf_objs[fn]['avg_y'] 
      cv2.circle(color_frame,(avg_x,avg_y), 4, (0,255,0), 1)
      if show == 1:
         show_img = cv2.resize(color_frame, (960,540))
         cv2.imshow('color_frame', show_img)
         cv2.moveWindow('final',500,700)
         cv2.waitKey(1)
      #if fn in cnt_objs:
      #   print(fn, cnt_objs[fn]['avg_x'], cnt_objs[fn]['avg_y'], cnt_objs[fn]['xs'], cnt_objs[fn]['ys'])

   for mf in mf_objs:
      print("MF:", mf, mf_objs[mf])
      frame = frames[0]
      frame = cv2.resize(frame, (1920,1080))
      if "avg_x" in mf_objs[mf]:
         x = mf_objs[mf]['avg_x']
         y = mf_objs[mf]['avg_y']
         if show == 1:
            cv2.circle(frame,(x,y), 5, (0,255,0), 1)
            cv2.imshow('color_frame', show_img)
            cv2.moveWindow('final',500,700)
            cv2.waitKey(1)
  
   first_x = None    
   max_dist_from_start = 0
   for fn in cnt_objs:
      if cnt_objs[fn]['avg_x'] != 0:
         first_x = cnt_objs[fn]['avg_x'] 
         first_y = cnt_objs[fn]['avg_y'] 
         dist_from_start = calc_dist((first_x, first_y), (cnt_objs[fn]['avg_x'], cnt_objs[fn]['avg_x']))

         if dist_from_start > max_dist_from_start or max_dist_from_start == 0:
            max_dist_from_start = dist_from_start
            #print(fn, cnt_objs[fn]['avg_x'], cnt_objs[fn]['avg_y'], dist_from_start)

   for obj in objects:
      status = test_obj(obj)
      if status != 0:
         obj['status'] = "METEOR"
         meteor_objs.append(obj)
      else:
         obj['status'] = "NOT_METEOR"
      new_objs.append(obj)

   objects = new_objs 

   print("METO:", len(meteor_objs))
   max_len = 0
   if len(meteor_objs) != 1:
      print("METEOR DETECTION BAD! More than one meteor detect. Pick best one...")
      for mo in meteor_objs:
         print(mo)
         hist_len = len(mo['history'])
         if hist_len > max_len:
            max_len = hist_len 
            best = mo
      meteor_objs = []
      meteor_objs.append(best) 

   for meteor_obj in meteor_objs:
      hist = meteor_obj['history']
      print("METEOR HIST:", hist)
      oid = meteor_obj['oid']
      for row in hist:
         (fn,x,y,w,h,cx,cy) = row
         fn = int(fn)
         mf_objs[fn]['objects'].append(row)
         mf_objs[fn]['object_ids'].append(oid)
         mf_objs[fn]['med_x'] = cx 
         mf_objs[fn]['med_y'] = cy
       
  
   sz = 10
   first_frame = None
   last_frame = None
   last_len = None
   ecc = 0
   xs = []
   ys = []
   segs = []
   metframes = {}
   event_started = 0
   no_meteor = 0

   pre_met = 0 
   for fn in mf_objs:
      meteor_exists = 0
      fi = fn
      print(fn, mf_objs[fn])
      img = clean_frames[fn].copy()

      norm_img = frames[fn].copy()
      med_x, med_y = merge_frame_objects(mf_objs[fn])
      mf_objs[fn]['med_x'] = med_x
      mf_objs[fn]['med_y'] = med_y
      if med_x != 0 and med_y != 0 and no_meteor <= 5:
         event_started = 1
         meteor_exists = 1
         fn = int(fn)
         metframes[fn] = {}
         if first_frame is None:
            event_started = 1
            first_frame = fn
            etime = 0
         else:
            ecc = fn - first_frame
            etime = ecc / 25 
         x1,y1,x2,y2= bound_cnt(med_x,med_y,img.shape[1],img.shape[0],sz)
         cnt_img = img[y1:y2,x1:x2]
         blob_x, blob_y, blob_max, blob_w, blob_h= find_blob_center(cnt_img,img,norm_img,x1,y1,x2,y2,sz)
         if last_frame is not None:
            metframes[fn]['len_from_last'] = calc_dist((blob_x,blob_y), (last_x,last_y))
            if fn - last_frame > 1:
               metframes[fn]['len_from_last'] = metframes[fn]['len_from_last'] / (fn - last_frame)
            metframes[fn]['len_from_start'] = calc_dist((blob_x,blob_y), (first_x,first_y))
            if last_len is not None:
               metframes[fn]['last_len_diff'] = metframes[fn]['len_from_start'] - last_len
               segs.append(metframes[fn]['last_len_diff'])

            last_len = metframes[fn]['len_from_start']
         nx, ny, ra ,dec , az, el= XYtoRADec(blob_x,blob_y,mrf,mjr['cal_params'],json_conf)
         if fn == first_frame:
            first_x = blob_x 
            first_y = blob_y 
            first_ra = ra
            first_dec = dec
            first_az = az
            first_el = el 
         mf_objs[fn]['blob_x'] = blob_x
         mf_objs[fn]['blob_y'] = blob_y 

         metframes[fi]['etime'] = etime
         metframes[fi]['fn'] = fn
         metframes[fi]['hd_x'] = blob_x
         metframes[fi]['hd_y'] = blob_y
         metframes[fi]['max_px'] = blob_max
         metframes[fi]['w'] = w
         metframes[fi]['h'] = h
         metframes[fi]['ra'] = ra
         metframes[fi]['dec'] = dec
         metframes[fi]['az'] = az
         metframes[fi]['el'] = el
         #metframes[fi]['frame_crop'] = [x1,y1,x2,y2]
         xs.append(int(blob_x))
         ys.append(int(blob_y))
         last_frame = fn
         last_x = blob_x 
         last_y = blob_y 
         last_ra = ra
         last_dec = dec
         last_az = az
         last_el = el 

      else:
         #the meteor does not exist, lets see if we should fill in the frame, or if the event is over we can skip. 
         if event_started == 0:
            print("EVENT NOT STARTED YET. ")
            # just skip if event hasn't started yet
            continue
         if len(xs) < 3 and pre_met < 5:
            # this could be a pre meteor def add frame.
            ecc = fn - first_frame
            etime = ecc / 25 
            metframes[fn] = {}
            metframes[fi]['etime'] = etime
            metframes[fi]['fn'] = fn
            print("ADD PRE METEOR FRAME!")
            last_frame = fn
            pre_met = pre_met + 1
         elif no_meteor < 5:
            ecc = fn - first_frame
            etime = ecc / 25 
            metframes[fn] = {}
            metframes[fi]['etime'] = etime
            metframes[fi]['fn'] = fn
            print("ADD MISSING METEOR FRAME!")
            last_frame = fn



         no_meteor = no_meteor + 1

 


   metconf = {}

   dir_x = first_x - last_x 
   dir_y = first_y - last_y 
   if dir_x < 0:
      x_dir_mod = 1
   else:
      x_dir_mod = -1
   if dir_y < 0:
      y_dir_mod = 1
   else:
      y_dir_mod = -1

   ang_sep = angularSeparation(first_ra,first_dec,last_ra,last_dec)

   metconf['xs'] = xs
   metconf['ys'] = ys
   metconf['fx'] = int(first_x)
   metconf['fy'] = int(first_y)
   metconf['lx'] = int(last_x)
   metconf['ly'] = int(last_y)

   metconf['first_az'] = first_az
   metconf['first_el'] = first_el
   metconf['last_az'] = last_az
   metconf['last_el'] = last_el
   metconf['first_ra'] = first_ra
   metconf['first_dec'] = first_dec
   metconf['last_ra'] = last_ra
   metconf['last_dec'] = last_dec
   metconf['tf'] = last_frame - first_frame
   if metconf['tf'] == 0:
      metconf['tf'] = len(metframes)
   print("LAST/FIRST", first_frame,  metconf['tf'])
   metconf['runs'] = 0
   metconf['line_dist'] = calc_dist((first_x, first_y), (last_x,last_y))
   if metconf['tf'] > 0:
      metconf['x_incr'] = int(metconf['line_dist'] / metconf['tf'])
   else:
      metconf['x_incr'] = 2
    
   metconf['x_dir_mod'] = x_dir_mod
   metconf['y_dir_mod'] = y_dir_mod
   metconf['angular_separation'] = ang_sep
   metconf['acl_poly'] = np.float64(0)
   # OK ALMOST DONE! 
   # JUST NEED TO FIND ESTIMATE FOR MISSING FRAMES
   m,b = best_fit_slope_and_intercept(xs,ys)
   if len(xs) > 25:
      m_10,b_10 = best_fit_slope_and_intercept(xs[0:10],ys[0:10])
   else:
      m_10 = m
      b_10 = b
   metconf['m'] = m_10
   metconf['b'] = b_10

   fcc = 0
   acl_poly = 0 
   if len(xs) > 25:
      med_seg_len = np.median(segs[0:8])
   else:
      med_seg_len = np.median(segs)
   if len(segs) == 0:
      med_seg_len = 2

   xs = []
   ys = []
   metconf['med_seg_len'] = med_seg_len
   last_frame = None
   for fn in metframes:
      est_res = 0
      img = frames[fn].copy()
      img = cv2.resize(img, (1920,1080))
      img_gray = img
      img = cv2.cvtColor(img,cv2.COLOR_GRAY2RGB)
      print("MED:", med_seg_len)
      est_x = int((metconf['fx'] + metconf['x_dir_mod'] * (med_seg_len*fcc)) + acl_poly * fcc)
      print(est_x, m_10, b_10)
      est_y = int((m_10*est_x)+b_10)
      metframes[fn]['est_x'] = est_x
      metframes[fn]['est_y'] = est_y
      if "hd_x" in metframes[fn]:
         hd_x = metframes[fn]['hd_x'] 
         hd_y = metframes[fn]['hd_y'] 
         est_res = calc_dist((hd_x,hd_y), (est_x,est_y))
         metframes[fn]['est_res'] = est_res
         cv2.circle(img,(hd_x,hd_y), 4, (0,255,0), 1)
         xs.append(hd_x)
         ys.append(hd_y)
         nx1,ny1,nx2,ny2= bound_cnt(hd_x,hd_y,img.shape[1],img.shape[0],10)
      else:
         nx1,ny1,nx2,ny2= bound_cnt(est_x,est_y,img.shape[1],img.shape[0],10)
      fcc = fcc + 1
      cv2.circle(img,(est_x,est_y), 4, (0,255,255), 1)

      if est_res < 50 :
         #and metframes[fn]['last_len_diff'] > med_seg_len * 4:
         nx1,ny1,nx2,ny2= bound_cnt(est_x,est_y,img.shape[1],img.shape[0],10)
         min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(cnt_img)
      
      cnt_img = img_gray[ny1:ny2,nx1:nx2]
      print("LAST CNT:", ny1,ny2,nx1,nx2)
      if cnt_img.shape[0] > 0 and cnt_img.shape[1] > 0 :
         print(cnt_img.shape)
         min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(cnt_img)
         bp_x = nx1 + mx 
         bp_y = ny1 + my
         print("BP:", bp_x, bp_y)
         metframes[fn]['bp_x'] = bp_x
         metframes[fn]['bp_y'] = bp_y
         px_diff = max_val - min_val 
         bp_res = calc_dist((bp_x,bp_y), (est_x,est_y))
         if bp_res < est_res and px_diff > 10:
            metframes[fn]['orig_x'] = metframes[fn]['hd_x']
            metframes[fn]['orig_y'] = metframes[fn]['hd_y']
            metframes[fn]['hd_x'] = bp_x
            metframes[fn]['hd_y'] = bp_y
            metframes[fn]['px_diff'] = px_diff 
            cv2.circle(img,(bp_x,bp_y), 8, (255,128,0), 1)
         else:
            print("THIS FRAME IS BAD:", fn, bp_res, px_diff)
         #cv2.circle(img,(bp_x,bp_y), 4, (255,0,0), 1)
         #cv2.imshow('cnt', cnt_img)   
         #cv2.moveWindow('cnt',2200,10)


      if last_frame is not None:
         if "hd_x" in metframes[fn]:
            print("UPDATING LAST LEN")
            metframes[fn]['len_from_last'] = calc_dist((metframes[fn]['hd_x'],metframes[fn]['hd_y']), (last_x,last_y))
            if fn - last_frame > 1:
               metframes[fn]['len_from_last'] = metframes[fn]['len_from_last'] / (fn - last_frame)
            metframes[fi]['len_from_start'] = calc_dist((metframes[fn]['hd_x'],metframes[fn]['hd_y']), (first_x,first_y))
            if last_len is not None:
               metframes[fi]['last_len_diff'] = metframes[fi]['len_from_start'] - last_len
         else:
            print("MISSING HDX LETS SEE IF THIS IS REAL")
            metframes[fn]['len_from_last'] = calc_dist((metframes[fn]['bp_x'],metframes[fn]['bp_y']), (last_x,last_y))
            if fn - last_frame > 1:
               metframes[fn]['len_from_last'] = metframes[fn]['len_from_last'] / (fn - last_frame)
            metframes[fi]['len_from_start'] = calc_dist((metframes[fn]['hd_x'],metframes[fn]['hd_y']), (first_x,first_y))
            if last_len is not None:
               metframes[fi]['last_len_diff'] = metframes[fi]['len_from_start'] - last_len


      if show == 1:
         cv2.putText(img, str(fn),  (10,20), cv2.FONT_HERSHEY_SIMPLEX, .4, (255,255,255), 1)
         if "est_res" in metframes[fn]:
            cv2.putText(img, "EST RES: " + str(metframes[fn]['est_res']),  (10,60), cv2.FONT_HERSHEY_SIMPLEX, .4, (255,255,255), 1)
         if "last_len_diff" in metframes[fn]:
            cv2.putText(img, "LAST LEN DIFF: " + str(metframes[fn]['last_len_diff']),  (10,30), cv2.FONT_HERSHEY_SIMPLEX, .4, (255,255,255), 1)
         #cv2.imshow('pepe2', img)   
         #cv2.moveWindow('pepe2',25,40)
         #cv2.waitKey(10)

      if fcc > 10:
         n_m_10,n_b_10 = best_fit_slope_and_intercept(xs[-10:],ys[-10:])
         if abs(n_b_10 - b_10) < 200:
            m_10 = n_m_10
            b_10 = n_b_10
         med_seg_len = np.median(segs[-10:])
      if np.isnan(m_10 ) is True or np.isnan(b_10) is True:
         metframes[fn]['m_10'] = metframes['m'] 
         metframes[fn]['b_10'] = metframes['b'] 
      else:
         metframes[fn]['m_10'] = m_10 
         metframes[fn]['b_10'] = b_10
      if "hd_x" in metframes[fn]:
         last_fn = fn
         last_hd_x = metframes[fn]['hd_x']
         last_hd_y = metframes[fn]['hd_y']

      print(fn,metframes[fn])

   # OK LAST TIME
   meteor_frame_data = []
   bad_frames = []
   for fn in metframes:
      bad = 0
      print("MIKE:", fn, metframes[fn])
      est_res = 0
      img = frames[fn].copy()
      img = cv2.resize(img, (1920,1080))
      img_gray = img
      img = cv2.cvtColor(img,cv2.COLOR_GRAY2RGB)
      est_x = metframes[fn]['est_x']
      est_y = metframes[fn]['est_y']
      cv2.circle(img,(est_x,est_y), 4, (0,255,255), 1)
      if "bp_x" in metframes[fn]:
         bp_x = metframes[fn]['bp_x']
         bp_y = metframes[fn]['bp_y']
      else:
         bp_x = metframes[fn]['est_x']
         bp_y = metframes[fn]['est_y']
         metframes[fn]['bp_x'] = bp_x = metframes[fn]['est_x']

         metframes[fn]['bp_y'] = metframes[fn]['est_y']

      cv2.circle(img,(bp_x,bp_y), 4, (0,0,255), 1)
      if "hd_x" in metframes[fn]:
         hd_x = metframes[fn]['hd_x']
         hd_y = metframes[fn]['hd_y']
         cv2.circle(img,(hd_x,hd_y), 4, (0,255,0), 1)
         est_res = calc_dist((hd_x,hd_y), (est_x,est_y))
      else:
         bad= 1
         if "px_diff" in metframes[fn]: 
            if metframes[fn]['px_diff'] > 10:
               metframes[fn]['hd_x'] = bp_x
               metframes[fn]['hd_y'] = bp_y
               bad = 0
            else:         
               print("BAD FRAME:", fn)
               bad_frames.append(fn)
               bad = 1
         else:
            print("MIGHT BE BAD:", fn, metframes[fn])
            nx1,ny1,nx2,ny2= bound_cnt(bp_x,bp_y,img.shape[1],img.shape[0],10)
            cnt_img = img_gray[ny1:ny2,nx1:nx2]
            min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(cnt_img)
            px_diff = max_val - min_val
            metframes[fn]['px_diff'] = px_diff

            metframes[fn]['len_from_last'] = calc_dist((metframes[fn]['bp_x'],metframes[fn]['bp_y']), (last_x,last_y))
            if fn - last_frame > 1:
               metframes[fn]['len_from_last'] = metframes[fn]['len_from_last'] / (fn - last_frame)
             
            metframes[fn]['len_from_start'] = calc_dist((metframes[fn]['bp_x'],metframes[fn]['bp_y']), (first_x,first_y))
            if last_len is not None:
               metframes[fn]['last_len_diff'] = metframes[fn]['len_from_start'] - last_len
           
            if px_diff > 10:
               metframes[fn]['hd_x'] = bp_x
               metframes[fn]['hd_y'] = bp_y
               bad = 0
            else:
               bad = 1
               bad_frames.append(fn)
               print("BAD FRAME:", fn)
            
      if show == 1:
         cv2.imshow('last', img)   
         cv2.moveWindow('last',25,25)
         cv2.waitKey(10)
      if "w" not in metframes[fn]:
         metframes[fn]['w'] = 5 
         metframes[fn]['h'] = 5
 
      if "max_px" not in metframes[fn]:
         metframes[fn]['max_px'] = blob_max

      if bad == 0:
         nx, ny, ra ,dec , az, el= XYtoRADec(metframes[fn]['hd_x'],metframes[fn]['hd_y'], mrf,mjr['cal_params'],json_conf)
         metframes[fn]['ra'] = ra
         metframes[fn]['dec'] = dec
         metframes[fn]['az'] = az
         metframes[fn]['el'] = el
   
      if bad == 0:
         meteor_frame_data.append((metframes[fn]['etime'],fn,int(metframes[fn]['hd_x']),int(metframes[fn]['hd_y']),int(metframes[fn]['w']),int(metframes[fn]['h']),int(metframes[fn]['max_px']),float(metframes[fn]['ra']),float(metframes[fn]['dec']),float(metframes[fn]['az']),float(metframes[fn]['el']) ))
      if 'last_len_diff' in metframes[fn]:
         last_len  = metframes[fn]['len_from_start'] 

      last_frame = fn

   for bad_f in bad_frames:
      if bad_f in metframes:
         print("DELETE FN", bad_f)
         metframes.pop(bad_f)
      else:
         print("FN NOT THERE", bad_f)


   if "orig_meteor_frame_data" not in mjr:
      mjr['orig_meteor_frame_data'] = mjr['meteor_frame_data']
   mjr['meteor_frame_data'] = meteor_frame_data

   mjr['start_az'] = az
   mjr['start_el'] = el
   mjr['start_ra'] = ra
   mjr['start_dec'] = dec
   mjr['end_az'] = az
   mjr['end_el'] = el
   mjr['end_ra'] = ra
   mjr['end_dec'] = dec


   this_poly = np.zeros(shape=(2,), dtype=np.float64)
   avg_res = reduce_acl(this_poly, metframes,metconf,frames)
   this_poly[0] = -.5
   this_poly[1] = -.1
   #res = scipy.optimize.minimize(reduce_acl, this_poly, args=( metframes, metconf,frames,show), method='Nelder-Mead')
   #print(res)
   #poly = res['x']
   #metconf['med_seg_len'] = float(metconf['med_seg_len'] + poly[0])
   #metconf['acl_poly'] = poly[1]
   metconf['acl_poly'] = 0



   segs = []
   bad_frames = []
   med_seg = None
   for fn in metframes:
      bad = 0
      if "len_from_last" not in metframes[fn]:
         print(fn, "no len from last")
      else:

         if len(segs) > 1:
            if med_seg - (med_seg * .4)  <= metframes[fn]['last_len_diff'] <= med_seg + (med_seg * .4):
               print(fn, metframes[fn]['last_len_diff'], " is good.", med_seg,segs)                
            else:
               print(fn, metframes[fn]['last_len_diff'], " is bad.", med_seg,segs)                
               bad_frames.append(fn)
               bad = 1

         if bad == 0 and "last_len_diff" in metframes[fn] :
            if metframes[fn]['last_len_diff'] > 0:
               segs.append(metframes[fn]['last_len_diff'])
         med_seg = np.median(segs)

   for bf in bad_frames:
      if bf in metframes:
         metframes.pop(bf)
         print("DELETE FN:", bf) 

   for fn in metframes:
      last_frame = fn

   over =  0
   bad_frames = []
   for fn in metframes:
      frames_till_end = last_frame - fn
      if "last_len_diff" in metframes[fn]:
         print("FN ", fn," IS ", frames_till_end, "frames from the end with last_len_dif of ", metframes[fn]['last_len_diff'])
         if metframes[fn]['last_len_diff'] < 0:
            bad_frames.append(fn)
            if frames_till_end < 5:
               # event is over
               over = 1
      if over == 1:
         bad_frames.append(fn)

   for bf in bad_frames:
      if bf in metframes:
         metframes.pop(bf)
         print("DELETE FN:", bf) 

   print("BAD FRAMES:", bad_frames)
   # need to update final metconf values here too
   meteor_frame_data = []
   for fn in metframes:
      meteor_frame_data.append((metframes[fn]['etime'],fn,int(metframes[fn]['hd_x']),int(metframes[fn]['hd_y']),int(metframes[fn]['w']),int(metframes[fn]['h']),int(metframes[fn]['max_px']),float(metframes[fn]['ra']),float(metframes[fn]['dec']),float(metframes[fn]['az']),float(metframes[fn]['el']) ))

   cmp_imgs,metframes = make_meteor_cnt_composite_images(json_conf, meteor_frame_data, metframes, frames, mjr['sd_video_file'])

   mjr['metconf'] = metconf
   mjr['metframes'] = metframes
   prefix = mjr['sd_video_file'].replace(".mp4", "-frm")
   prefix = prefix.replace("SD/proc2/", "meteors/")
   prefix = prefix.replace("/passed", "")
   for fn in cmp_imgs:
      cv2.imwrite(prefix  + str(fn) + ".png", cmp_imgs[fn])
      print("UPDATING!")
      mjr['metframes'][fn]['cnt_thumb'] = prefix + str(fn) + ".png"


   mjr['metconf'] = metconf
   mjr['meteor_frame_data'] = meteor_frame_data
   save_json_file("test.json", mjr)
   print("SAVED:", mrf )
   save_json_file(mrf, mjr)



   #for fn in mf_objs:
   #   print(fn, mf_objs[fn])
   #exit()

def reduce_acl(this_poly, metframes,metconf,frames,show=0):
   xs = []
   ys = []
   err = []
   fcc = 0
   m_10 = metconf['m']
   b_10 = metconf['b']
   for fn in metframes:
      print(fn, metframes[fn])
      est_res = 0
      img = frames[fn].copy()
      img = cv2.resize(img, (1920,1080))
      img_gray = img
      img = cv2.cvtColor(img,cv2.COLOR_GRAY2RGB)

      med_seg = (this_poly[0] + metconf['med_seg_len'])
      acl_poly = this_poly[1] 

      est_x = int( metconf['fx'] + (metconf['x_dir_mod'] * (med_seg*fcc)) + (acl_poly * fcc) )
      est_y = int((m_10*est_x)+b_10)

      cv2.circle(img,(est_x,est_y), 4, (0,255,255), 1)
      bp_x = metframes[fn]['bp_x']
      bp_y = metframes[fn]['bp_y']
      cv2.circle(img,(bp_x,bp_y), 4, (0,0,255), 1)
      xs.append(bp_x)
      ys.append(bp_y)

      bp_est_res = calc_dist((bp_x,bp_y), (est_x,est_y)) 
      if "hd_x" in metframes[fn]:
         hd_x = metframes[fn]['hd_x']
         hd_y = metframes[fn]['hd_y']
         cv2.circle(img,(hd_x,hd_y), 4, (0,255,0), 1)
         hd_est_res = calc_dist((hd_x,hd_y), (est_x,est_y))
      else:
         hd_est_res = bp_est_res

      err.append(hd_est_res)

      cv2.putText(img, str(med_seg) + " " + str(acl_poly),  (10,10), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,0,255), 1)
      if show == 1:
         cv2.imshow('last', img)
         cv2.moveWindow('last',25,25)
         cv2.waitKey(1)
      fcc = fcc + 1
      
      if len(xs) > 10:
         n_m_10,n_b_10 = best_fit_slope_and_intercept(xs[-10:],ys[-10:])
         if abs(n_b_10 - b_10) < 200:
            m_10 = n_m_10
            b_10 = n_b_10



   return(np.mean(hd_est_res))

def merge_frame_objects(objects):
   xs = []
   ys = []
   for hist in objects['objects']:
      xs.append(hist[5])
      ys.append(hist[6])
   if len(xs) > 0:
      med_x = np.median(xs)
      med_y = np.median(ys)
   else:
      med_x = 0
      med_y = 0
   return(int(med_x),int(med_y))
 
def test_obj(obj):
   oid = obj['oid']
   if len(obj['history']) < 3:
      print("FAILED HIST LEN:", len(obj['history']))
      return(0)
   if len(obj['history']) > 250:
      print("FAILED HIST LEN:", len(obj['history']))
      return(0)
   f = obj['history'][0][0]
   l = obj['history'][-1][0]
   fx = obj['history'][0][1]
   fy = obj['history'][0][2]
   lx = obj['history'][-1][1]
   ly = obj['history'][-1][2]
   dist = calc_dist((fx,fy),(lx,ly))
   elp = l - f
   if elp < 4:
      print("Failed dist:", dist)
   if dist< 5:
      print("Failed dist:", dist)
   if elp > 0:
      speed = dist / elp
   else:
      speed = 0
   print("SPEED IS:", oid, speed)
   print("DIST IS:", oid, dist)
  

   if elp > 250:
      print("FAILED ELP:", elp)
      return(0)
   cm,gaps,gap_events,cm_hist_len_ratio = meteor_test_cm_gaps(obj)
   if cm < 4:
      print("FAILED CM:", cm)
      return(0)
   if elp > 0:
      cm_elp_ratio = cm / elp 
   else: 
      cm_elp_ratio = 0
   #print("CM: ", cm, gaps, gap_events, elp, len(obj['history']), cm_elp_ratio)
   if gaps > 5 or gap_events > 5:
      print("FAILED GAPS:", oid, gaps, gap_events)
      #return(0)

   print("PASSED METEOR:", obj)
   return(1)

def sort_metframes(metframes):
   new_metframes = {}
   fns = []
   for fn in metframes:
      fns.append(int(fn))
   for fn in sorted(fns):
      fn = str(fn)    
      if fn in metframes:
         new_metframes[fn] = metframes[fn]
   return(new_metframes)

def metframes_to_mfd(metframes, sd_video_file):
   meteor_frame_data = []
   for fn in metframes:
      frame_time,frame_time_str = calc_frame_time(sd_video_file, fn) 
      metframes[fn]['frame_time'] = frame_time_str
      meteor_frame_data.append((frame_time_str,fn,int(metframes[fn]['hd_x']),int(metframes[fn]['hd_y']),int(metframes[fn]['w']),int(metframes[fn]['h']),int(metframes[fn]['max_px']),float(metframes[fn]['ra']),float(metframes[fn]['dec']),float(metframes[fn]['az']),float(metframes[fn]['el']) ))
   return(meteor_frame_data, metframes)

def update_len_diff(metframes,metconf):


   last_frame = None
   last_len = None
   first_fn = None
   segs = []
   fcc = 0
   xs = []
   ys = []
   for fn in metframes:
      if "hd_x" not in metframes[fn]:
         print("MISSING HD_X:", metframes[fn]) 
         metframes[fn]['hd_x'] = metframes[fn]['hd_est_x']
         metframes[fn]['hd_y'] = metframes[fn]['hd_est_y']

      if first_fn is None:
         print("MIKE:", metframes[fn])
         first_fn = fn
         first_x = metframes[fn]['hd_x']
         first_y = metframes[fn]['hd_y']
      if last_frame is not None:
         metframes[fn]['len_from_last'] = calc_dist((metframes[fn]['hd_x'],metframes[fn]['hd_y']), (last_x,last_y))
         if int(fn) - int(last_frame) > 1:
            metframes[fn]['len_from_last'] = metframes[fn]['len_from_last'] / (int(fn) - int(last_frame))
            metframes[fn]['len_from_start'] = calc_dist((metframes[fn]['hd_x'],metframes[fn]['hd_y']), (first_x,first_y))
         if last_len is not None:
            if "len_from_start" in metframes[fn]:
               metframes[fn]['last_len_diff'] = metframes[fn]['len_from_start'] - last_len
               segs.append(metframes[fn]['last_len_diff'])

            if "len_from_start" in metframes[fn]:
               last_len = metframes[fn]['len_from_start']
      xs.append(metframes[fn]['hd_x'])
      ys.append(metframes[fn]['hd_y'])

      if fcc > 10:
         n_m_10,n_b_10 = best_fit_slope_and_intercept(xs[-10:],ys[-10:])
         if abs(n_b_10 - metconf['b']) < 200:
            metconf['m_10'] = n_m_10
            metconf['b_10'] = n_b_10

         med_seg_len = np.median(segs[-10:])
         metframes[fn]['b_10'] = med_seg_len 


      last_frame = fn 
      last_x = metframes[fn]['hd_x']
      last_y = metframes[fn]['hd_y']
      fcc = fcc + 1

   if len(xs) > 25:
      med_seg_len = np.median(segs[0:8])
   else:
      med_seg_len = np.median(segs)
   if len(segs) == 0:
      med_seg_len = 2


   metconf['med_seg_len'] = med_seg_len

   return(metframes,metconf)


def eval_metframes(mrf):
   mr = load_json_file(mrf)
   sd_video_file = mrf.replace("-reduced.json", ".mp4")
   if "metframes" not in mr:
      print("No metframes. Try reducing first? ", mrf)
      exit()
   mr['metframes'] = sort_metframes(mr['metframes'])
   mr['metframes'],mr['metconf'] = update_len_diff(mr['metframes'], mr['metconf'])

   if 'frames_missing_before' in mr:
      mr.pop("frames_missing_before")
      mr.pop("frames_missing_after")

   first_frame = None
   last_frame = None
   segs = []
   frames_missing_before = []
   frames_missing_after = []

   xs = []
   ys = []
   for fn in mr['metframes']:
      if "m_10" in mr['metframes'][fn]:
         print ("MB:", mr['metframes'][fn]['m_10'] , mr['metframes'][fn]['b_10'])
      if "hd_x" in mr['metframes'][fn]:
         xs.append(mr['metframes'][fn]['hd_x'])
         ys.append(mr['metframes'][fn]['hd_y'])

   m,b = best_fit_slope_and_intercept(xs,ys)
   if len(xs) > 25:
      m_10,b_10 = best_fit_slope_and_intercept(xs[0:10],ys[0:10])
   else:
      m_10 = m
      b_10 = b

   fcc = 0
   xs = []
   ys = []
   for fn in mr['metframes']:
      mr['metframes'][fn]['m_10'] = m_10
      mr['metframes'][fn]['b_10'] = b_10
      if fcc > 10:
        
         m_10,b_10 = best_fit_slope_and_intercept(xs[-10:],ys[-10:])
         mr['metframes'][fn]['m_10'] = m_10
         mr['metframes'][fn]['b_10'] = b_10
         print("MRB:", fcc, mr['metframes'][fn]['m_10'], mr['metframes'][fn]['b_10'] )
      fcc = fcc + 1
      xs.append(mr['metframes'][fn]['hd_x'])
      ys.append(mr['metframes'][fn]['hd_y'])

   for fn in mr['metframes']:
      print("MR:", mr['metframes'][fn]['m_10'], mr['metframes'][fn]['b_10'] )


   for fn in mr['metframes']:

      if "m_10" in mr['metframes'][fn]:
         if np.isnan(mr['metframes'][fn]['m_10'] ) is True or np.isnan(mr['metframes'][fn]['b_10']) is True:
            print("NAN IS TRUE!")
            mr['metframes'][fn]['m_10'] = metconf['m'] 
            mr['metframes'][fn]['b_10'] = metconf['b'] 
      else:
         mr['metframes'][fn]['m_10'] = metconf['m'] 
         mr['metframes'][fn]['b_10'] = metconf['b'] 

      if "hd_x" not in mr['metframes'][fn]:
         mr['metframes']['hd_x'] = mr['metframes']['hd_est_x']
         mr['metframes']['hd_y'] = mr['metframes']['hd_est_y']
      if last_frame is not None:
         if int(last_frame) + 1 != int(fn):
            print("Frame missing before fn", last_frame, fn)
            frames_missing_before.append(fn)
            frames_missing_after.append(last_frame)
         
      if "last_len_diff" in mr['metframes'][fn]: 
         print(fn, mr['metframes'][fn]['len_from_last'], mr['metframes'][fn]['last_len_diff'])
         segs.append( mr['metframes'][fn]['len_from_last'])
      elif "len_from_last" in mr['metframes'][fn]:
         print(fn, mr['metframes'][fn]['len_from_last'])
         segs.append( mr['metframes'][fn]['len_from_last'])
      else:
         print(fn, mr['metframes'][fn])
      last_frame = fn

   print("")
   avg_seg = np.mean(segs)
   all_seg_res = []
   for fn in mr['metframes']:

       
      if "len_from_last" in mr['metframes'][fn]:
         seg_res =  abs(mr['metframes'][fn]['len_from_last'] - avg_seg)
         if "last_len_diff" in mr['metframes'][fn]:
            lld = mr['metframes'][fn]['last_len_diff']
         else:
            lld = 0
         print(fn, "SEG RES", seg_res, lld)
         all_seg_res.append(seg_res)
      else: 
         print(fn)

   print("")
   avg_seg_res = np.mean(all_seg_res)
   print("AVG SEG RES:", avg_seg_res)
   print("MISSING FRAMES:", len(frames_missing_before))
   mr['red_seg_res'] = avg_seg_res
   if len(frames_missing_before) > 0:
      mr['frames_missing_before'] = frames_missing_before
      mr['frames_missing_after'] = frames_missing_after

   if len(frames_missing_before) == 1:
      missing_frame_gap = int(frames_missing_before[0]) -  int(frames_missing_after[0])
      print("Just 1 frame missing, lets fix it.", frames_missing_after[0], frames_missing_before[0])
      print("Missing frame gap is:", missing_frame_gap)
      if missing_frame_gap == 2:
         ms_fn = int(frames_missing_after[0]) + 1 
         bfn = frames_missing_after[0]
         afn = frames_missing_before[0]
         before_x = mr['metframes'][bfn]['hd_x']
         before_y = mr['metframes'][bfn]['hd_y']
         after_x = mr['metframes'][afn]['hd_x']
         after_y = mr['metframes'][afn]['hd_y']
         mid_x = int((before_x + after_x) / 2)
         mid_y = int((before_y + after_y) / 2)
         print("MID X :", before_x, after_x, mid_x)
         print("MID Y :", before_y, after_y, mid_y)

         ms_fn = str(ms_fn)
         mr['metframes'][ms_fn] = {}
         mr['metframes'][ms_fn]['hd_x'] = mid_x
         mr['metframes'][ms_fn]['hd_y'] = mid_y
         metframes = mr['metframes']
         metframes = make_metframe(mrf, mr, ms_fn, mid_x, mid_y, metframes) 
         mr['metframes'] = metframes
         print("FIXED:", ms_fn, mr['metframes'][ms_fn]) 

  
   print("LOAD:", sd_video_file) 
   sd_frames = load_video_frames(sd_video_file, json_conf)
   frames = []
   for frame in sd_frames:
      #hd_img = frame
      hd_img = cv2.resize(frame, (1920,1080))
      frames.append(hd_img)


   for fn in mr['metframes']:
      ifn = int(fn)
      hd_x = mr['metframes'][fn]['hd_x']
      hd_y = mr['metframes'][fn]['hd_y']
      cnt_w = 40
      size = 40
      x1,y1,x2,y2 = bound_cnt(hd_x,hd_y,1920,1080,cnt_w)
      print("FN:", ifn)
      cnt_img = frames[ifn][y1:y2,x1:x2]
      blob_x, blob_y, blob_max, blob_w, blob_h = find_blob_center(cnt_img,frames[ifn],frames[ifn],x1,y1,x2,y2,size)
      #if "hd_x" not in mr['metframes']:
      #   mr['metframes'][fn]['hd_x'] = blob_x 
      #   mr['metframes'][fn]['hd_y'] = blob_y 
      
      nx, ny, ra ,dec , az, el= XYtoRADec(hd_x,hd_y,mrf,mr['cal_params'],json_conf)
      mr['metframes'][fn]['az'] = az
      mr['metframes'][fn]['el'] = el
      mr['metframes'][fn]['ra'] = ra
      mr['metframes'][fn]['dec'] = dec 


   print("MFD!")
   mfd,mr['metframes'] = metframes_to_mfd(mr['metframes'], mr['sd_video_file'])
   cmp_imgs,mr['metframes'] = make_meteor_cnt_composite_images(json_conf, mfd, mr['metframes'], frames, sd_video_file)
   prefix = mr['sd_video_file'].replace(".mp4", "-frm")
   prefix = prefix.replace("SD/proc2/", "meteors/")
   prefix = prefix.replace("/passed", "")
   for fn in cmp_imgs:
      cv2.imwrite(prefix  + str(fn) + ".png", cmp_imgs[fn])
      mr['metframes'][fn]['cnt_thumb'] = prefix + str(fn) + ".png"



   mr['meteor_frame_data'] = mfd

   save_json_file(mrf, mr)
   save_json_file("test.json", mr)


def make_metframe(mrf, mr, fn, hd_x, hd_y, metframes):
   bfn = str(int(fn) - 1)
   afn = str(int(fn) + 1)
   cnt_w = 25
   x1,y1,x2,y2 = bound_cnt(hd_x,hd_y,1920,1080,cnt_w)

   for fn in metframes:
      print("MIKE1", fn, metframes[fn])

   print("METFRAMES:", bfn,metframes[bfn])
   if "len_from_last" in metframes[bfn]:
      metframes[fn]["len_from_last"] = metframes[bfn]['len_from_last']
   else:
      metframes[fn]["len_from_last"] = 1 
   if "len_from_start" in metframes[fn]:
      metframes[fn]["len_from_start"] = metframes[bfn]['len_from_start'] + metframes[bfn]['len_from_last']

   if "last_len_diff" in metframes[fn]:
      metframes[fn]["last_len_diff"] = metframes[bfn]['last_len_diff']
   else:
      metframes[fn]["last_len_diff"] = 1

   nx, ny, ra ,dec , az, el= XYtoRADec(hd_x,hd_y,mrf,mr['cal_params'],json_conf)

   #metframes[fn]["etime"] = metframes[bfn]['etime'] + 1/25
   metframes[fn]["etime"] = 0
   metframes[fn]["fn"] = fn
   metframes[fn]["max_px"] = 0
   metframes[fn]["w"] = 0
   metframes[fn]["h"] = 0
   metframes[fn]["ra"] = ra
   metframes[fn]["dec"] = dec
   metframes[fn]["az"] = az
   metframes[fn]["el"] = el
   metframes[fn]["est_x"] = 0
   metframes[fn]["est_y"] = 0
   metframes[fn]["est_res"] = 0
   metframes[fn]["bp_x"] = 0
   metframes[fn]["bp_y"] = 0
   metframes[fn]["px_diff"] = 0
   metframes[fn]["m_10"] =  0
   metframes[fn]["b_10"] =  0
   metframes[fn]["x1"] = x1
   metframes[fn]["y1"] = y1
   metframes[fn]["x2"] = x2
   metframes[fn]["y2"] = y2




   new_metframes = sort_metframes(metframes)

   return(new_metframes)

mrf = sys.argv[1]

if sys.argv[1] == 'eval':
   mrf = sys.argv[2]
   if "mp4" in mrf :
      mrf = mrf.replace(".mp4", "-reduced.json")
   eval_metframes(mrf)
   exit()
if "json" in mrf :
   if "reduced" not in mrf :
      mrf = mrf.replace(".json", "-reduced.json")
if "mp4" in mrf :
   mrf = mrf.replace(".mp4", "-reduced.json")
if len(sys.argv) == 3:

   show = int(sys.argv[2])
else:
   show = 0


fine_reduce(mrf, json_conf,show)


