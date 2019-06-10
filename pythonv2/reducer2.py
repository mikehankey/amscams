#!/usr/bin/python3


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
from lib.UtilLib import check_running
from lib.CalibLib import radec_to_azel, clean_star_bg, get_catalog_stars, find_close_stars, XYtoRADec, HMS2deg, AzEltoRADec

from lib.ImageLib import mask_frame , stack_frames, preload_image_acc
from lib.ReducerLib import setup_metframes  
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

def find_blob_center(cnt_img,img,x1,y1,x2,y2,size):
   print("SHAPE:", cnt_img.shape)
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

   print("FIRST BLOB XY:", blob_x, blob_y, x1,y1,x2,y2)
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
      min_val, max_val, min_loc, (bmx,bmy)= cv2.minMaxLoc(cnt_img)
      (x,y,w,h,size,mx,my) = temp[0]
      blob_x = mx + nx1
      blob_y = my + ny1
      max_px = max_val
   
   print("SECOND BLOB XY:", blob_x, blob_y, nx1,ny1,nx2,ny2)
   cv2.imshow('pepe2', cnt_img2)   
   cv2.moveWindow('pepe2',1600,210)

   cv2.waitKey(0)

   return(blob_x, blob_y,max_val)     


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
            object, objects = id_object(cnts[i], objects,fn, (x,y))
            #print("OBJ:", object)
            size = w + h
            cx = int(x + (w / 2))
            cy = int(y + (h / 2))
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
      hd_img = cv2.resize(frame, (1920,1080))
      frames.append(hd_img)


   metframes, metconf = setup_metframes(mjr['meteor_frame_data'])
 
   #print(len(frames))
   cnt_objs = {}

   image_acc = preload_image_acc(frames)

   abs_image_acc = cv2.convertScaleAbs(image_acc)

   avg_px = np.mean(abs_image_acc)
   max_px = np.max(abs_image_acc)
   px_diff = max_px - avg_px
   thresh_val = avg_px + (px_diff / 4)
   tmp_mask_points, marked_mask_image, objects, object_id= find_cnts(0,abs_image_acc, thresh_val, objects)
   #cv2.imshow('marked_mask_image', marked_mask_image)
   #cv2.waitKey(0)
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

   fcc = 0
   for frame in frames:
      work_frame = frame.copy()
      work_frame = cv2.convertScaleAbs(work_frame)
      work_frame = mask_frame(work_frame, mask_points, [],5)
      color_frame = cv2.cvtColor(frame,cv2.COLOR_GRAY2RGB)
      blur_frame = cv2.GaussianBlur(work_frame, (7, 7), 0)
 
      if show == 1:
         if fcc in metframes:
            cv2.putText(color_frame, str(fcc),  (10,10), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,0,255), 1)
         else:
            cv2.putText(color_frame, str(fcc),  (10,10), cv2.FONT_HERSHEY_SIMPLEX, .4, (255,255,255), 1)


      image_diff = cv2.absdiff(image_acc.astype(work_frame.dtype), work_frame,)
      alpha = .5
      hello = cv2.accumulateWeighted(image_diff, image_acc, alpha)

      if first_frame is not None:

         sub_first = cv2.subtract(work_frame,first_frame)
         sub_last = cv2.subtract(work_frame,last_frame)
         image_acc2 = cv2.convertScaleAbs(image_acc)
         sub_acc = cv2.subtract(work_frame,image_acc2)
         subtracted = sub_acc 

         thresh_val = 10
         sub_first_cnts, marked_image_first,object,object_id = find_cnts(fcc,sub_first, thresh_val, objects)
         sub_last_cnts, marked_image_last,objects,object_id = find_cnts(fcc,sub_last, thresh_val, objects)
         subtracted_cnts, marked_image_subtracted,objects,object_id = find_cnts(fcc,subtracted, thresh_val, objects)

         if fcc not in cnt_objs:
            cnt_objs[fcc] = {}

         cnt_objs[fcc]['sub_first'] = sub_first_cnts 
         cnt_objs[fcc]['sub_last'] = sub_last_cnts 
         cnt_objs[fcc]['subtracted_cnts'] = subtracted_cnts
         cnt_objs[fcc]['subtracted_cnts'] = subtracted_cnts
         cnt_objs[fcc]['sub_sub_cnts'] = []

         if last_frame is not None and last_subtracted is not None:
            sub_sub = cv2.subtract(subtracted,last_subtracted)
            sub_sub_cnts, marked_image_sub_sub,objects,object_id = find_cnts(fcc,sub_sub, thresh_val,objects)
            cnt_objs[fcc]['sub_sub_cnts'] = sub_sub_cnts

         show_img = cv2.resize(color_frame, (960,540))
         cv2.imshow('color_frame', show_img)
         cv2.moveWindow('color_frame',10,10)
         cv2.waitKey(30)
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
      for cnt_o in cnt_objs[fn]['sub_first']:
         (x,y,w,h,cx,cy,mx,my) = cnt_o
         xs.append(cx)
         xs.append(mx)
         ys.append(cy)
         ys.append(my)
      for cnt_o in cnt_objs[fn]['sub_last']:
         (x,y,w,h,cx,cy,mx,my) = cnt_o
         xs.append(cx)
         xs.append(mx)
         ys.append(cy)
         ys.append(my)
      for cnt_o in cnt_objs[fn]['subtracted_cnts']:
         (x,y,w,h,cx,cy,mx,my) = cnt_o
         xs.append(cx)
         xs.append(mx)
         ys.append(cy)
         ys.append(my)
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

      show_img = cv2.resize(color_frame, (960,540))
      cv2.imshow('color_frame', show_img)
      cv2.moveWindow('final',300,600)
      cv2.waitKey(10)
      #if fn in cnt_objs:
      #   print(fn, cnt_objs[fn]['avg_x'], cnt_objs[fn]['avg_y'], cnt_objs[fn]['xs'], cnt_objs[fn]['ys'])
  
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
      if "status" not in obj:
         status = test_obj(obj)
         if status != 0:
            print("METEOR:", obj)
            obj['status'] = "METEOR"
            meteor_objs.append(obj)
         else:
            obj['status'] = "PLANE"
      new_objs.append(obj)

   objects = new_objs 

   for meteor_obj in meteor_objs:
      hist = meteor_obj['history']
      oid = meteor_obj['oid']
      for row in hist:
         (fn,x,y,w,h,cx,cy) = row
         mf_objs[fn]['objects'].append(row)
         mf_objs[fn]['object_ids'].append(oid)
       
   for fn in mf_objs:
      #print(fn, mf_objs[fn])      
      med_x, med_y = merge_frame_objects(mf_objs[fn])
      mf_objs[fn]['med_x'] = med_x
      mf_objs[fn]['med_y'] = med_y

   sz = 50
   for fn in mf_objs:
      med_x = mf_objs[fn]['med_x']
      med_y = mf_objs[fn]['med_y']
      img = frames[fn].copy()
      cimg = cv2.cvtColor(img,cv2.COLOR_GRAY2RGB)
      if med_x != 0 and med_y != 0:
         x1,y1,x2,y2= bound_cnt(med_x,med_y,img.shape[1],img.shape[0],sz)
         cnt_img = img[y1:y2,x1:x2]
         print("MIKE:", fn, mf_objs[fn]['med_x'], mf_objs[fn]['med_y'])      
      
         blob_x, blob_y, blob_max = find_blob_center(cnt_img,img,x1,y1,x2,y2,sz)
         cv2.circle(cimg,(blob_x,blob_y), 4, (0,255,0), 1)
         cv2.imshow('pepe', cnt_img)
         cv2.moveWindow('pepe',1600,10)
         cv2.waitKey(0)
         cv2.circle(cimg,(mf_objs[fn]['med_x'],mf_objs[fn]['med_y']), 4, (0,0,255), 1)
      #if "avg_x" in mf_objs[fn]:
      #   cv2.circle(cimg,(mf_objs[fn]['avg_x'],mf_objs[fn]['avg_y']), 1, (0,255,0), 4)
      show_img = cv2.resize(cimg, (960,540))
      cv2.imshow('final', show_img)
      cv2.moveWindow('final',800,300)
      cv2.waitKey(0)

def merge_frame_objects(objects):
   xs = []
   ys = []
   for hist in objects['objects']:
      print("MERGE:", hist[5], hist[6])
      xs.append(hist[5])
      ys.append(hist[6])
   if len(xs) > 0:
      med_x = np.median(xs)
      med_y = np.median(ys)
   else:
      med_x = 0
      med_y = 0
   print("MERGED:", med_x, med_y)
   return(int(med_x),int(med_y))
 
def test_obj(obj):
   if len(obj['history']) < 3:
      return(0)
   if len(obj['history']) > 250:
      return(0)
   f = obj['history'][0][0]
   l = obj['history'][-1][0]
   elp = l - f
   if elp > 250:
      return(0)
   cm,gaps,gap_events,cm_hist_len_ratio = meteor_test_cm_gaps(obj)
   if elp > 0:
      cm_elp_ratio = cm / elp 
   else: 
      cm_elp_ratio = 0
   #print("CM: ", cm, gaps, gap_events, elp, len(obj['history']), cm_elp_ratio)
   if gaps > 5 or gap_events > 5:
      return(0)

   return(1)

mrf = sys.argv[1]
if "json" in mrf :
   if "reduced" not in mrf :
      mrf = mrf.replace(".json", "-reduced.json")
if "mp4" in mrf :
   mrf = mrf.replace(".mp4", "-reduced.json")
if len(sys.argv) == 3:

   show = int(sys.argv[2])
else:
   show = 1
fine_reduce(mrf, json_conf,show)

