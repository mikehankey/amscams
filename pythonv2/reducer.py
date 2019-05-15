#!/usr/bin/python3

"""
TODO: put in az/el lookups / updates based on new
 - refinement / bug fixes
 - 2nd res error test / line fit (in case est is off, but still good red). 
 - add mask block out the stars

"""



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

from lib.ImageLib import mask_frame , stack_frames

#import matplotlib.pyplot as plt
import sys
#from caliblib import distort_xy,
from lib.CalibLib import distort_xy_new, find_image_stars, distort_xy_new, XYtoRADec, radec_to_azel, get_catalog_stars,AzEltoRADec , HMS2deg, get_active_cal_file, RAdeg2HMS, clean_star_bg
from lib.UtilLib import calc_dist, find_angle, bound_cnt, cnt_max_px

from lib.UtilLib import angularSeparation, convert_filename_to_date_cam, better_parse_file_date
from lib.FileIO import load_json_file, save_json_file, cfe
from lib.UtilLib import calc_dist,find_angle
import lib.brightstardata as bsd
from lib.DetectLib import eval_cnt
json_conf = load_json_file("../conf/as6.json")

def best_fit_slope_and_intercept(xs,ys):
    xs = np.array(xs, dtype=np.float64)
    ys = np.array(ys, dtype=np.float64)
    m = (((np.mean(xs)*np.mean(ys)) - np.mean(xs*ys)) /
         ((np.mean(xs)*np.mean(xs)) - np.mean(xs*xs)))

    b = np.mean(ys) - m*np.mean(xs)

    return m, b


def cleanup_json_file(mf):

   if "close_stars" in mf['cal_params']:
      del mf['cal_params']['close_stars']
   if "cat_stars" in mf['cal_params']:
      del mf['cal_params']['cat_stars']
#   if "cat_image_stars" in mf['cal_params']:
#      del mf['cal_params']['cat_image_stars']
   if "fov_poly" in mf['cal_params']:
      del mf['cal_params']['fov_poly']
   if "pos_poly" in mf['cal_params']:
      del mf['cal_params']['pos_poly']
   if "user_stars" in mf['cal_params']:
      del mf['cal_params']['user_stars']
   if "api_key" in mf:
      del mf['api_key']


   return(mf)

def define_crop_box(mfd):
   temp = sorted(mfd, key=lambda x: x[2], reverse=False)
   min_x = temp[0][2]
   temp = sorted(mfd, key=lambda x: x[2], reverse=True)
   max_x = temp[0][2]
   temp = sorted(mfd, key=lambda x: x[3], reverse=False)
   min_y = temp[0][3]
   temp = sorted(mfd, key=lambda x: x[3], reverse=True)
   max_y = temp[0][3]
   w = max_x - min_x 
   h = max_y - min_y
#   if w > h:
#      h = w
#   else:
#      w = h
#   if w < 100 and h < 100:
#      w = 100
#      h = 100

   print(w,h)
   if w % 2 != 0:
      w = w + 1
   sz = int(w/2) + 50

   cx = int(min_x + ((max_x - min_x) / 2))
   cy = int(min_y + ((max_y - min_y) / 2))
   box_min_x = cx - sz
   box_min_y = cy - sz
   box_max_x = cx + sz
   box_max_y = cy + sz
   if box_min_x < 0: 
      mox_max_x = box_max_x + abs(box_min_x)
      box_min_x = 0
   if box_min_y < 0: 
      mox_max_y = box_max_y + abs(box_min_y)
      box_min_y = 0
   

   return(box_min_x,box_min_y,box_max_x,box_max_y)
   

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


def setup_json_frame_data(mfd):
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
   xs = []
   ys = []
   for fd in mfd:
      frame_time, fn, hd_x,hd_y,w,h,max_px,ra,dec,az,el = fd
      fi = fn
      xs.append(hd_x)
      ys.append(hd_y)
      metframes[fi]['fn'] = fi
      metframes[fi]['ft'] = frame_time
      metframes[fi]['hd_x'] = hd_x
      metframes[fi]['hd_y'] = hd_y
      metframes[fi]['w'] = w
      metframes[fi]['h'] = h
      metframes[fi]['max_px'] = max_px
      metframes[fi]['ra'] = ra
      metframes[fi]['dec'] = dec
      metframes[fi]['az'] = az
      metframes[fi]['el'] = el
   metconf = {}
   metconf['xs'] = xs
   metconf['ys'] = ys
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
   
   return(metframes, metconf )

def prep_image(img):
   work_img = img.copy()
   img2 = cv2.resize(img, (1920,1080))
   img2 = cv2.cvtColor(img2,cv2.COLOR_GRAY2RGB)
   work_img = cv2.resize(work_img, (1920,1080))
   return(img2, work_img)

def est_frame_pos(est_x, est_y, work_img, cnt_sz):
   # frame details are missing try to fix
   hd_y1 = est_y - cnt_sz
   hd_y2 = est_y + cnt_sz
   hd_x1 = est_x - cnt_sz
   hd_x2 = est_x + cnt_sz 
   hd_x1, hd_y1, hd_x2, hd_y2 = check_cnt_bounds(hd_x1, hd_y1, hd_x2, hd_y2)
   cnt_img = work_img[hd_y1:hd_y2,hd_x1:hd_x2]
   min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(cnt_img)
   px_diff = max_val - min_val
   hd_x = hd_x1 + mx
   hd_y = hd_y1 + my
   hd_x1, hd_y1, hd_x2, hd_y2 = check_cnt_bounds(hd_x1, hd_y1, hd_x2, hd_y2)

   return(hd_x, hd_y, hd_y1, hd_y2,hd_x1, hd_x2, max_val, px_diff)

def minimize_start_len(metframes,frames,metconf,mf,show=0):
   this_poly = np.zeros(shape=(2,), dtype=np.float64)

   #err = reduce_start_len(metframes, frames, metconf,show)
   res = scipy.optimize.minimize(reduce_start_len, this_poly, args=( metframes, frames,metconf,mf,show), method='Nelder-Mead')
   return(metframes,frames,metconf)

def reduce_start_len(poly, metframes,frames,metconf,mf,show=0):
   metconf['med_seg_len'] = float(metconf['med_seg_len'] + poly[0])
   metconf['acl_poly'] = poly[1]
   if metconf['runs'] < 10:
      metframes, metconf,avg_res = play_meteor(metframes,frames,metconf,mf,show)
      metconf['avg_res_diff'] = avg_res
   else:
      return(0)
   return(avg_res)

#def find_best_point_from_est(img2, est_x, est_y, last_x,last_y, med_seg_len, cnt_sz):
#   hd_y1 = est_y - cnt_sz 
#   hd_y2 = est_y + cnt_sz 
#   hd_x1 = est_x - cnt_sz 
#   hd_x2 = est_x + cnt_sz 

#   hd_x1, hd_y1, hd_x2, hd_y2 = check_cnt_bounds(hd_x1, hd_y1, hd_x2, hd_y2)
#   cnt_img = work_img[hd_y1:hd_y2,hd_x1:hd_x2]


def slope_fixes(metframes,metconf,mf,frames, show):
   fx = None
   slope_ms = []
   slope_bs = []
   xs = []
   ys = []
   acl_poly = metconf['acl_poly']

   # determine first x,y and initial slope of all points
   for fn in metframes:

      hd_x = metframes[fn]['hd_x']
      hd_y = metframes[fn]['hd_y']
      if fx is None:
         fx = hd_x
         fy = hd_y
      xs.append(hd_x)
      ys.append(hd_y)
   half_len = int(len(xs) / 2)
   if half_len > 4: 
      sxs = xs[0:4]
      sys = xs[0:4]
      m,b = best_fit_slope_and_intercept(sxs,sys)
   else:
      sxs = xs[0:half_len]
      sys = xs[0:half_len]
      m,b = best_fit_slope_and_intercept(sxs,sys)

   # compute and compare slope for each point and compare to main one 
   fc = 0
   xs = []
   ys = []
   for fn in metframes:
      hd_x = metframes[fn]['hd_x']
      hd_y = metframes[fn]['hd_y']
      if fc == 0:
         metframes[fn]['slope_m'] = m
         metframes[fn]['slope_b'] = b
         slope_ms.append(m)
         slope_bs.append(b)
      else:
         if len(xs) >= 4:
            sxs = xs[-4:]
            sys = ys[-4:]
            xm,xb = best_fit_slope_and_intercept([sxs[0],sxs[-1]],[sys[0],sys[-1]])
         else:
            xm,xb = best_fit_slope_and_intercept([fx,hd_x],[fy,hd_y])
         metframes[fn]['slope_m'] = xm
         metframes[fn]['slope_b'] = xb
         slope_ms.append(xm)
         slope_bs.append(xb)
      xs.append(hd_x)
      ys.append(hd_y)
      fc = fc + 1

   med_slope_m = np.mean(slope_ms)
   med_slope_b = np.mean(slope_bs)
   if "med_seg_len" in metconf:
      med_seg_len = metconf['med_seg_len']
   else: 
      med_seg_len = 0 
   x_dir_mod =  metconf['x_dir_mod']
   new_xs = []
   new_ys = []
   last_len_from_last = None
   last_diff = 0
   len_diff = 0
   fcc = 0
   total_res_err = 0
   avg_res_err = 0
   for fn in metframes:
      img = frames[fn]
      m = metframes[fn]['slope_m'] 
      b = metframes[fn]['slope_b'] 
      nice_img = frames[fn]
      img2 = cv2.resize(img, (1920,1080))
      nice_img2 = cv2.resize(nice_img, (1920,1080))
      img2 = cv2.cvtColor(img2,cv2.COLOR_GRAY2RGB)
      nice_img2 = cv2.cvtColor(nice_img2,cv2.COLOR_GRAY2RGB)
      status = ""
      print("MB:", m,b) 
      #est_x = int(fx + x_dir_mod * (med_seg_len*fcc))
      try:
         est_x = int((fx + x_dir_mod * (med_seg_len*fcc)) + acl_poly * fcc)
         est_y = int((m*est_x)+b)
         metframes[fn]['est_x'] = est_x
         metframes[fn]['est_y'] = est_y
      except:
         m = metconf['m']  
         b = metconf['b'] 
         est_x = int((fx + x_dir_mod * (med_seg_len*fcc)) + acl_poly * fcc)
         est_y = int((m*est_x)+b)
         metframes[fn]['est_x'] = est_x
         metframes[fn]['est_y'] = est_y

      if metframes[fn]['slope_b'] == 0 and fcc > 0:
         status = "BAD"
      if abs(abs(metframes[fn]['slope_b']) - abs(med_slope_b)) > 300 and fcc > 0:
         metframes[fn]['slope_status'] = "BAD"
         status = "BAD"
      if status == "BAD":
         #(hd_x, hd_y, hd_y1, hd_y2,hd_x1, hd_x2, max_px,px_diff) = est_frame_pos(est_x,est_y,work_img,cnt_sz)
         metframes[fn]['hd_x'] = est_x
         metframes[fn]['hd_y'] = est_y
         metframes[fn]['slope_status'] = "BAD"
      else:
         new_xs.append(metframes[fn]['hd_x'])
         new_ys.append(metframes[fn]['hd_y'])
         metframes[fn]['slope_status'] = "GOOD"

      # do len checks here
      len_from_last = metframes[fn]['len_from_last']
      if last_len_from_last is not None:
         len_diff = abs(len_from_last - last_len_from_last)
         if abs(last_len_from_last) > 0:
            diff_perc = len_diff / last_len_from_last
         else:
            diff_perc = 0
         if diff_perc < .5:
            colors = (0,0,255) 
            est_x = int(last_hd_x + x_dir_mod * (last_len_from_last))
            est_y = int((m*est_x)+b)
            desc = str(metconf['runs']) + " " + str(est_x) + "," + str(est_y) + " " + str(last_len_from_last)
            cv2.putText(img2, "EST INFO: "+ desc,  (400,600), cv2.FONT_HERSHEY_SIMPLEX, .8, colors, 1)
            cv2.circle(img2,(est_x,est_y), 2, (255,128,255), 2)
            len_from_last = last_len_from_last
            if metconf['runs'] >= 1:
               est_err = calc_dist((metframes[fn]['hd_x'],metframes[fn]['hd_y']),(metframes[fn]['est_x'],metframes[fn]['est_y']))
               if est_err < 10:
                  metframes[fn]['hd_x'] = est_x
                  metframes[fn]['hd_y'] = est_y
                  metframes[fn]['len_from_last'] = len_from_last 
         else:
            colors = (0,255,0) 
         desc = str(fn) + " " + str(len_from_last) + " " + str(last_len_from_last) + " " + str(len_diff) + " " + str(diff_perc*100) + "%"
         cv2.putText(img2, "LEN FROM LAST: "+ desc,  (400,500), cv2.FONT_HERSHEY_SIMPLEX, .8, colors, 1)
      print(fcc, fn, hd_x, hd_y, est_x, est_y, len_from_last, last_len_from_last, len_diff)
      last_len_from_last = len_from_last
      last_hd_x = metframes[fn]['hd_x'] 
      last_hd_y = metframes[fn]['hd_y'] 
      fcc = fcc + 1

      print("SLOPE:", fn, metframes[fn]['slope_m'], med_slope_m, metframes[fn]['slope_b'], med_slope_b,  metframes[fn]['slope_status'])

      # do len checks here
      #for fn in metframes:
      #   len_from_last = metframes['fn']['len_from_last']
      #   if last_len_from_last is not None:
      #      len_diff = len_from_last - last_len_from_last
      #   print(fn, len_from_last, last_len_from_last, len_diff)
      #   last_len_from_last = len_from_last


      cv2.circle(img2,(metframes[fn]['hd_x'],metframes[fn]['hd_y']), 10, (255,128,255), 1)
      cv2.circle(img2,(metframes[fn]['est_x'],metframes[fn]['est_y']), 8, (0,255,255), 1)
      est_err = calc_dist((metframes[fn]['hd_x'],metframes[fn]['hd_y']),(metframes[fn]['est_x'],metframes[fn]['est_y']))
      total_res_err = total_res_err + est_err
      avg_res_err = total_res_err / fcc
      if avg_res_err < 3:
         colors = (0,255,0)
      else:
         colors = (0,0,255)
      
      cv2.putText(img2, "EST RES ERROR: "+ str(avg_res_err),  (400,650), cv2.FONT_HERSHEY_SIMPLEX, .8, colors, 1)

      m = metconf['m']
      b = metconf['b']

      for xxx in range(0,len(metframes)):
         if xxx == 0:
            est_x = fx
            est_y = fy
         else:
            est_x = int((fx + x_dir_mod * (med_seg_len*xxx)) + (acl_poly * xxx))
            est_y = int((m*est_x)+b)
         if hd_x != 0 and hd_y != 0 and est_x != 0 and est_y != 0:
            desc = str(fx) + "," + " / " + str(est_x) + "," + str(est_y)
            cv2.putText(img2, desc,  (350,100+(xxx*25)), cv2.FONT_HERSHEY_SIMPLEX, .8, (0, 0, 255), 1)
            cv2.line(img2, (fx,fy), (est_x,est_y), (100,100,100), 1)

      min_x,min_y,max_x,max_y = metconf['crop_box']
      crop_frame = nice_img2[min_y:max_y,min_x:max_x]
      cv2.rectangle(img2, (min_x, min_y), (max_x, max_y), (128, 128, 128), 1)
      crop_h, crop_w, x = crop_frame.shape
      isx1 = 0
      isx2 = crop_w
      isy1 = 1080 - crop_h 
      isy2 = 1080 
      img2[isy1:isy2,isx1:isx2] = crop_frame
      cv2.rectangle(img2, (min_x, min_y), (max_x, max_y), (128, 128, 128), 1)

      cv2.imshow('pepe2', img2)
      if metconf['runs'] > 2:
         cv2.waitKey(0)
      else:
         cv2.waitKey(0)

   best_m,best_b = best_fit_slope_and_intercept(new_xs,new_ys)
   metconf['slope_m'] = best_m
   metconf['avg_res_diff'] = avg_res_err
   metconf['slope_b'] = best_b
   metconf['m'] = m 
   metconf['b'] = b 
   return(metframes, metconf) 

def find_best_point(metframes,metconf,img2,fn):
   before_hd_x = 0
   after_hd_x = 0
   if fn-1 in metframes:
      before_hd_x = metframes[fn-1]['hd_x']
      before_hd_y = metframes[fn-1]['hd_y']
   if fn+1 in metframes:
      after_hd_x = metframes[fn+1]['hd_x']
      after_hd_y = metframes[fn+1]['hd_y']
   m = metconf['m']
   b = metconf['b']
   x_dir_mod = metconf['x_dir_mod']
   med_seg_len = metconf['med_seg_len']
   acl_poly = metconf['med_seg_len']
   if before_hd_x != 0:
      #est_x = int((before_hd_x + x_dir_mod * (med_seg_len)) + acl_poly * fn-first_fn)
      est_x = int((before_hd_x + x_dir_mod * (med_seg_len)) )
      est_y = int((m*est_x)+b)
   else:
      est_x = 0
      est_y = 0
   return(est_x,est_y)

def check_frame_errors(metframes, frames,metconf,mf,show=0):
   min_x,min_y,max_x,max_y = metconf['crop_box']
   avg_res_diff = 0
   x_diff = 0
   y_diff = 0
   last_x = None
   last_y = None
   len_from_last = None
   last_len_from_last = None
   x_dir_mod = metconf['x_dir_mod'] 
   y_dir_mod = metconf['y_dir_mod'] 
   len_diff = 0
   if "med_seg_len" not in metconf:
      metconf['med_seg_len'] =  metconf['line_dist'] / metconf['tf']
   fcc = 0
   cnt_sz = 10
   for fn in metframes:
      hd_x = metframes[fn]['hd_x']
      hd_y = metframes[fn]['hd_y']
      if fcc == 0:
         fx = hd_x
         fy = hd_y
      img2, work_img = prep_image(frames[fn])
      (est_x, est_y, hd_y1, hd_y2,hd_x1, hd_x2, max_px,px_diff) = est_frame_pos(hd_x,hd_y,work_img,cnt_sz)
      cnt_img = work_img[hd_y1:hd_y2,hd_x1:hd_x2]
      min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(cnt_img)
      px_diff = max_val - min_val
      i_est_x, i_est_y = find_best_point(metframes,metconf,img2,fn)
      cv2.circle(img2,(hd_x,hd_y), 10, (255,0,0), 1)
      cv2.circle(img2,(i_est_x,i_est_y), 10, (0,255,255), 1)
      if hd_x != 0 and hd_y != 0:
         colors = (0,0,255) 
         # only add if there is a good px diff
         (est_x, est_y, hd_y1, hd_y2,hd_x1, hd_x2, max_px,px_diff) = est_frame_pos(hd_x,hd_y,work_img,cnt_sz)
         cnt_img = work_img[hd_y1:hd_y2,hd_x1:hd_x2]
         min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(cnt_img)
         est_x = hd_x1 + mx
         est_y = hd_y1 + my
         desc = "EST X,Y:" + str(est_x) + "," + str(est_y)
         px_diff = max_val - min_val
         cv2.circle(img2,(est_x,est_y), 10, (255,0,0), 1)


         if "point_status" not in metframes[fn]:
            metframes[fn]['point_status'] = "GOOD"
      else:
         # frame completely missing try to find a better frame
         colors = (255,255,255) 
         cnt_sz = 10
         est_x, est_y = find_best_point(metframes,metconf,img2,fn)
         (est_x, est_y, hd_y1, hd_y2,hd_x1, hd_x2, max_px,px_diff) = est_frame_pos(est_x,est_y,work_img,cnt_sz)
         # only add if there is a good px diff
         cnt_img = work_img[hd_y1:hd_y2,hd_x1:hd_x2]
         min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(cnt_img)
         desc = "EST X,Y:" + str(est_x) + "," + str(est_y)
         px_diff = max_val - min_val
         if px_diff > 10:
            cv2.circle(img2,(est_x,est_y), 10, (255,255,0), 1)
            cv2.putText(img2, desc,  (500,530), cv2.FONT_HERSHEY_SIMPLEX, .8, colors, 1)
            metframes[fn]['point_status'] = "CREATED"
            hd_x = est_x
            hd_y = est_y
         else:
            metframes[fn]['point_status'] = "DELETE"
      # check x dir is in right direction
      dir_status = "good"
      if last_x is not None:
         x_diff = hd_x - last_x 
         y_diff = hd_y - last_y
         if x_dir_mod > 0:
            if x_diff < 0:
               dir_status = "x diff err" 
         if x_dir_mod < 0:
            if x_diff > 0:
               dir_status = "x diff err" 
         if y_dir_mod > 0:
            if y_diff < 0:
               dir_status = dir_status + " y diff err" 
         if y_dir_mod < 0:
            if y_diff > 0:
               dir_status = dir_status + " y diff err" 
         if dir_status != "good":
            cnt_sz = 10
            est_x, est_y = find_best_point(metframes,metconf,img2,fn)
            (est_x, est_y, hd_y1, hd_y2,hd_x1, hd_x2, max_px,px_diff) = est_frame_pos(est_x,est_y,work_img,cnt_sz)
            cv2.circle(img2,(est_x,est_y), 10, (0,0,255), 1)
            hd_x = est_x
            hd_y = est_y
            metframes[fn]['point_status'] = "FIXED"
      metframes[fn]['hd_x'] = hd_x
      metframes[fn]['hd_y'] = hd_y


      # check LEN from last point and see how it compares. If off then fix it.]
      if fcc > 0:
         len_from_last = calc_dist((hd_x,hd_y),(last_x,last_y))
         len_from_start = calc_dist((fx,fy),(hd_x,hd_y))
      else:
         len_from_start = 0
         len_from_last = 0
      if last_len_from_last is not None:
         len_diff = len_from_last - last_len_from_last
      else:
         len_diff = len_from_last

      metframes[fn]['len_from_start'] = len_from_start
      metframes[fn]['len_from_last'] = len_from_last
      metframes[fn]['len_diff'] = len_diff 
           
      last_len_from_last = len_from_last
      last_x = hd_x 
      last_y = hd_y

      desc = "LEN FROM LAST: " + str(len_from_last)  
      cv2.putText(img2, desc,  (500,350), cv2.FONT_HERSHEY_SIMPLEX, .8, colors, 1)

      desc = "LEN DIFF: " + str(len_diff)  
      cv2.putText(img2, desc,  (500,380), cv2.FONT_HERSHEY_SIMPLEX, .8, colors, 1)

      desc = "DIR STATUS: " + str(dir_status)  
      cv2.putText(img2, desc,  (500,410), cv2.FONT_HERSHEY_SIMPLEX, .8, colors, 1)

      desc = "X,Y Diff: " + str(x_diff)  + "," + str(y_diff) + " X,Y DIR MOD:" + str(x_dir_mod) + "," + str(y_dir_mod)
      cv2.putText(img2, desc,  (500,440), cv2.FONT_HERSHEY_SIMPLEX, .8, colors, 1)

      desc = "FN: " + str(fn) 
      cv2.putText(img2, desc,  (500,470), cv2.FONT_HERSHEY_SIMPLEX, .8, colors, 1)
      desc = "X,Y: " + str(hd_x) + " " + str(hd_y)
      cv2.putText(img2, desc,  (500,500), cv2.FONT_HERSHEY_SIMPLEX, .8, colors, 1)
      cv2.rectangle(img2, (min_x, min_y), (max_x, max_y), (128, 128, 128), 1)
      cv2.imshow('pepe2', img2)
      cv2.waitKey(0)
      fcc = fcc + 1

   len_segs = []
   for fn in metframes:
      print (fn, metframes[fn]['hd_x'], metframes[fn]['hd_y'], metframes[fn]['len_from_start'], metframes[fn]['len_from_last'], metframes[fn]['max_px'], metframes[fn]['point_status'])
      len_segs.append(metframes[fn]['len_from_last'])

   med_seg_len = np.median(len_segs)
   print("MED SEG LEN:", med_seg_len)
   fcc = 0
   xs = []
   ys = []
   for fn in metframes:
      hd_x = metframes[fn]['hd_x']
      hd_y = metframes[fn]['hd_y']
      if med_seg_len > 0 and fcc > 0:  
         perc_match = metframes[fn]['len_from_last']  / med_seg_len
         if perc_match < .5 :
            est_x, est_y = find_best_point(metframes,metconf,img2,fn)
            metframes[fn]['hd_x'] = est_x
            metframes[fn]['hd_y'] = est_y
            hd_x = est_x
            hd_y = est_y
            metframes[fn]['len_from_last'] = calc_dist((est_x,est_y),(last_x,last_y))
            len_from_start = calc_dist((fx,fy),(est_x,est_y))
            metframes[fn]['point_status'] = "FIXED"
            if metframes[fn]['len_from_last'] < 0:
               metframes[fn]['point_status'] = "DELETE"
      else:
         perc_match = 0
      xs.append(hd_x)
      ys.append(hd_y)

      
      #print ("AFTER LAST CHECK:", fn, metframes[fn]['hd_x'], metframes[fn]['hd_y'], metframes[fn]['len_from_last'], metframes[fn]['max_px'], metframes[fn]['len_diff'], metframes[fn]['point_status'], perc_match)
      print ("AFTER LAST CHECK:", fn, metframes[fn]['len_from_last'], metframes[fn]['max_px'], px_diff, metframes[fn]['point_status'], perc_match)
      last_x = hd_x
      last_y = hd_y
      fcc = fcc + 1
   xm,xb = best_fit_slope_and_intercept(xs,ys)

   print(xs)
   print(ys)
   print(xm,xb)
   metconf['m'] = xm
   metconf['b'] = xb
   metconf['med_seg_len'] =  metconf['line_dist'] / metconf['tf']
   exit()
   return(metframes, metconf, avg_res_diff)


def play_meteor_clip(metframes,frames, metconf,mf,show=0):
   new_metframes = {}
   #metframes, metconf = slope_fixes(metframes, metconf,mf,frames,show)
   last_len = None
   last_x = None
   last_y = None
   last_fn = None
   last_len_diff = "" 
   lens = []
   fx = None
   med_seg_len =  metconf['med_seg_len']
   m =  metconf['m']
   b =  metconf['b']
   x_dir_mod =  metconf['x_dir_mod']
   acl_poly = metconf['acl_poly'] 
   fcc = 0

   min_x,min_y,max_x,max_y = metconf['crop_box']

   for fn in metframes:
      #print("FN:", fn)
      #fn = int(fn)
      img2, work_img = prep_image(frames[fn])
      cv2.rectangle(img2, (min_x, min_y), (max_x, max_y), (128, 128, 128), 1)
      blob_x = 0
      blob_y = 0
      new_metframes[fn] = metframes[fn]
      hd_x = metframes[fn]['hd_x']
      hd_y = metframes[fn]['hd_y']
      len_from_last = metframes[fn]['len_from_last']
      len_from_start = metframes[fn]['len_from_start']
      if fx is None: 
         fx = hd_x
         fy = hd_y
         ff = fn 
      for xxx in range(0,len(metframes)):
         #est_x = int((fx + x_dir_mod * (med_seg_len*xxx)) )
         est_x = int((fx + x_dir_mod * (med_seg_len*xxx)) + acl_poly * xxx)
         est_y = int((m*est_x)+b)
         if hd_x != 0 and hd_y != 0 and est_x != 0 and est_y != 0:
            cv2.line(img2, (hd_x,hd_y), (est_x,est_y), (255,255,255), 1)
      #cv2.imshow('pepe2', img2)
      #cv2.waitKey(10)

      if last_x != None:
         # SLOPE TESTS: check slope of this px compared to first and compare to original
         xm,xb = best_fit_slope_and_intercept([fx,hd_x],[fy,hd_y])
         m_dp = (xm * 10) / (m * 10)
         b_dp = (xb *10) / (b * 10)

         elp_f = fn - last_fn
         if len(lens) < 2:
            dist_factor = med_seg_len
         dist_factor = np.median(lens)
         #est_x = int(last_x + x_dir_mod * (dist_factor*elp_f))
         est_x = int((last_x + x_dir_mod * (dist_factor*elp_f)) + acl_poly * fcc)
         est_y = int((m*est_x)+b)
         cv2.circle(img2,(est_x,est_y), 10, (0,255,255), 1)
         cv2.line(img2, (hd_x,hd_y), (last_x,last_y), (255), 1)
      else:
         cv2.putText(img2, "LAST X IS NONE!?",  (400,400), cv2.FONT_HERSHEY_SIMPLEX, .8, (0, 0, 255), 1)


      if last_len is not None:
         last_len_diff = len_from_start - last_len 

      if last_len_diff != "":
         if last_len_diff > 0:
            cv2.circle(img2,(hd_x,hd_y), 10, (0,255,0), 1)
         else:
            # MAKE CORRECTION
            cv2.circle(img2,(hd_x,hd_y), 10, (0,0,255), 1)
            hd_x = est_x 
            hd_y = est_y
            len_from_last = calc_dist((last_x,last_y),(hd_x,hd_y))
            if fx is not None and (hd_x != 0 and hd_y != 0) :
               len_from_start = calc_dist((fx,fy),(hd_x,hd_y))
            cv2.circle(img2,(hd_x,hd_y), 8, (0,255,0), 1)
            # Improve estimate with blob / bright point detector here
            metframes[fn]['hd_x'] = hd_x 
            metframes[fn]['hd_y'] = hd_y 
      else:
         cv2.circle(img2,(hd_x,hd_y), 10, (0,255,0), 1)

      desc = "FN" + str(fn) 
      cv2.putText(img2, desc ,  (5,10), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
      desc = "X,Y" + str(hd_x) + "," + str(hd_y)
      cv2.putText(img2, desc ,  (5,30), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)

      desc = "Last Len" + str(len_from_last) 
      cv2.putText(img2, desc ,  (5,50), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
      desc = "Last Len Diff" + str(last_len_diff) 
      cv2.putText(img2, desc ,  (5,70), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)


      desc = str(med_seg_len)
      cv2.putText(img2, "MED SEG LEN:" + desc,  (5,90), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)


      last_len = len_from_start
      last_x = hd_x 
      last_y = hd_y
      last_fn = fn
      lens.append(len_from_last)
      cv2.rectangle(img2, (min_x, min_y), (max_x, max_y), (128, 128, 128), 1)
      if show == 1:
         cv2.imshow('pepe2', img2)
         cv2.waitKey(10)
      fcc = fcc + 1




   return(metframes, frames, metconf)

def play_meteor(metframes,frames, metconf, mf,show=0):
   if "med_seg_len" in metconf:
      med_seg_len = metconf['med_seg_len']
      m = metconf['m']
      b = metconf['b']
      x_dir_mod = metconf['x_dir_mod']
   else:
      med_seg_len = None
   fr_len = len(frames)
   half_fr = int(fr_len/5)
   median_frame = np.median(frames)
   cal_params = mf['cal_params']
   cal_params_file = mf['sd_video_file'].replace(".mp4", ".json")

   min_x,min_y,max_x,max_y = metconf['crop_box']

   median_frame = cv2.resize(median_frame, (1920,1080))

   fc = 0
   fx = None
   fy = None
   last_x = None
   last_y = None
   last_fn = None
   last_max_px = None
   max_val = None
   len_from_start = 0
   last_len_from_start = 0
   len_from_last = 0
   len_segs = []
   peak_br = 0
   confirmed_last_frame = None
   no_motion = 0 
   len_diff = 0
   px_diff = 0
   bdiff = 0
   new_metframes = {}
   best_x = None
   best_y = None
   status = "no meteor in frame" 
   total_res_diff = 0
   avg_res_diff = 0
   xs = []
   ys = []
   acl_poly = metconf['acl_poly']
   # loop over rach frame
   print("MF:", median_frame.shape, half_fr)
   
   image_acc = median_frame
   for fn in metframes:
      blob_x = 0
      blob_y = 0
      new_metframes[fn] = metframes[fn]
      hd_x = metframes[fn]['hd_x']
      hd_y = metframes[fn]['hd_y']

      # load and resize image
      img2, work_img = prep_image(frames[fn] )

      for mpx in metconf['mask_px']:
         msx,msy = mpx
         msx1 = msx-4
         msx2 = msx+4
         msy1 = msy-4
         msy2 = msy+4
         work_img[msy1:msy2,msx1:msx2] = 0

      frame = img2.copy()
      #frame = cv2.convertScaleAbs(frame)
      #blur_frame = cv2.GaussianBlur(frame, (7, 7), 0)
      gray_frame = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
      #gray_frame = adjustLevels(frame, 10,1,255)
      gray_frame = cv2.convertScaleAbs(gray_frame)

      image_diff = cv2.absdiff(image_acc.astype(gray_frame.dtype), gray_frame,)
      alpha = .5
      hello = cv2.accumulateWeighted(image_diff, image_acc, alpha)

      #_, diff_thresh = cv2.threshold(image_diff.copy(), 100, 255, cv2.THRESH_BINARY)
      #image_diff = diff_thresh
      #image_diff = cv2.cvtColor(image_diff, cv2.COLOR_BGR2GRAY)

      #img2 = cv2.cvtColor(image_diff,cv2.COLOR_GRAY2RGB)
      #work_img = image_diff

      # set first frame if not set
      if fx is None: 
         fx = hd_x
         fy = hd_y
         ff = fn 

      # calc len from start if past 1st frame
      if fx is not None and (hd_x != 0 and hd_y != 0) :
         len_from_start = calc_dist((fx,fy),(hd_x,hd_y))
      else: 
         len_from_start = 0

      # calc len from last
      if last_x is not None and (hd_x != 0 and hd_y != 0) :
         len_from_last = calc_dist((last_x,last_y),(hd_x,hd_y))
         elp_fr = fn - last_fn 
         len_from_last = len_from_last / elp_fr
         len_segs.append(len_from_last)
      else: 
         len_from_last = 0

      # calc last four length
      if len(len_segs) > 2:
         if len(len_segs) >= 4:
            last_four =np.median(len_segs[-4:])
            sxs = xs[-4:]
            sys = ys[-4:]
            seg_d = calc_dist((sxs[0],sys[0]),(sxs[-1],sys[-1]))
            if seg_d > 10:
               m,b = best_fit_slope_and_intercept(sxs,sys)
         else:
            last_four = np.median(len_segs)
         if last_four <= 0:
            last_four = 1
      else:
         last_four = med_seg_len
 
      # only do this loop on the 2nd pass
      if med_seg_len is not None and last_fn is not None:
         elp_f = fn - last_fn
      else:
         elp_f = 0

          

      if fc == 0:
         est_x = fx 
         est_y = fy 
      elif med_seg_len is not None and last_x is not None:           
         # recalc m,b based on last 4 instead of global.
         if last_four is not None and x_dir_mod is not None: 
            #est_x = int(last_x + x_dir_mod * (last_four*elp_f))
            est_x = int((last_x + x_dir_mod * (last_four*elp_f)) + acl_poly * fc)
         else:
           #est_x = int(last_x + x_dir_mod * (len_from_last*elp_f))
            est_x = int((last_x + x_dir_mod * (len_from_last*elp_f)) + acl_poly * fc)
         try: 
            est_y = int((m*est_x)+b)
         except:
            print("BAD SLOPE!")
            est_x = 0
            est_y = 0
            exit()

      if hd_x == 0 and hd_y == 0 and no_motion < 3 and med_seg_len is not None:
         # frame details are missing try to fix     
         print("TRY TO FIND POINT!", no_motion, metframes[fn]['point_status'])
         cv2.putText(img2, "FIND POINT!" ,  (900,500), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 1)
         cnt_sz = 40
         (hd_x, hd_y, hd_y1, hd_y2,hd_x1, hd_x2, max_px,px_diff) = est_frame_pos(est_x,est_y,work_img,cnt_sz)
         cv2.putText(img2, "PX DIFF:" + str(px_diff),  (960,540), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 1)
         if px_diff < 10 :
            print("POINT NOT FOUND", px_diff)
            hd_x = 0
            hd_y = 0
         else:
            no_motion = 0


         if px_diff > peak_br:
            peak_br = px_diff 
         if last_max_px is not None:
            bdiff = px_diff / peak_br 

         if min_val  >0:
            mdiff = max_val / min_val 
         else:
            mdiff = 0
            
         cv2.putText(img2, "B DIFF:" + str(bdiff),  (990,580), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 1)
         if last_fn is not None:
            len_from_last = calc_dist((last_x,last_y),(hd_x,hd_y))
         if last_four is not None:
            if last_four > 0:
               len_diff = len_from_last / last_four
            else:
               len_diff = 0
         new_x,new_y = hd_x, hd_y 

         test_len_from_last = calc_dist((last_x,last_y),(new_x,new_y))
         len_d = abs(test_len_from_last - len_from_last)
         cv2.putText(img2, "LEN D: " + str(len_d) + " " + str(test_len_from_last),  (500,620), cv2.FONT_HERSHEY_SIMPLEX, .8, (0, 0, 255), 1)
         if len_d < 20 and test_len_from_last > 1 and metframes[fn]['point_status'] != "FIXED":
            desc = str(len_d) + " " + str(new_x) + " " + str(new_y)
            cv2.putText(img2, "ADDING POINT: " + metframes[fn]['point_status'] + desc ,  (700,650), cv2.FONT_HERSHEY_SIMPLEX, .8, (0, 0, 255), 1)
            # TEMP DISABLE
            #new_metframes[fn]['hd_x'] = new_x
            #new_metframes[fn]['hd_y'] = new_y
            #new_metframes[fn]['max_px'] = int(max_val)
            #new_metframes[fn]['len_from_last'] = int(test_len_from_last)
            #hd_x = new_x
            #hd_y = new_y
            print("(disabled)point was found and updated.", metframes[fn]['point_status'])
            
         else:
            cv2.putText(img2, "SKIPED POONT: " + str(len_d) ,  (600,650), cv2.FONT_HERSHEY_SIMPLEX, .8, (0, 0, 255), 1)
            print("point not found.")

         cv2.circle(threshold,(new_x,new_y), 10, (0,0,255), 1)

         status = "point created"
      elif med_seg_len is not None and no_motion < 3 and metframes[fn]['point_status'] != 'FIXED':
         # frame details exist, just confirm / tighten up
         if metconf['runs'] > 4:
            cnt_sz = 20 
         else:
            cnt_sz = 40
         hd_y1 = hd_y - cnt_sz 
         hd_y2 = hd_y + cnt_sz 
         hd_x1 = hd_x - cnt_sz 
         hd_x2 = hd_x + cnt_sz 

         hd_x1, hd_y1, hd_x2, hd_y2 = check_cnt_bounds(hd_x1, hd_y1, hd_x2, hd_y2)
         cnt_img = work_img[hd_y1:hd_y2,hd_x1:hd_x2]
         min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(cnt_img)
         new_x = hd_x1 + mx
         new_y = hd_y1 + my
         px_diff = max_val - min_val

         if px_diff > peak_br:
            peak_br = px_diff 
         #print("LAST MAX PX:", last_max_px)
         if last_max_px is not None:
            bdiff = px_diff / peak_br 
         if min_val != 0:
   
            mdiff = max_val / min_val 

         status = "point updated"
         no_motion = 0
      else:
         cnt_sz = 40
         new_x, new_y = hd_x , hd_y 
         hd_y1 = hd_y - 40
         hd_y2 = hd_y + 40
         hd_x1 = hd_x - 40
         hd_x2 = hd_x + 40
         hd_x1, hd_y1, hd_x2, hd_y2 = check_cnt_bounds(hd_x1, hd_y1, hd_x2, hd_y2)

         no_motion = 0
         status = "first run"

      # make thresh of blob
      if hd_x != 0 and hd_y != 0:
         cnt_img = work_img[hd_y1:hd_y2,hd_x1:hd_x2]
         min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(cnt_img)
         px_diff = max_val - min_val
         if px_diff < 10:
            thresh_val = last_max_px
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
            blob_x = hd_x1 + mx
            blob_y = hd_y1 + my
            max_px = max_val 
            #new_x = hd_x
            #new_y = hd_y
            #best_x = hd_x 
            #best_y = hd_y 
   
            
         threshold = cv2.cvtColor(thresh_img,cv2.COLOR_GRAY2RGB)
         cv2.circle(threshold,(mx,my), 10, (0,255,255), 1)
         cnt_sz2 = cnt_sz * 2
         iy2 = 300 + cnt_sz2
         img2[300:iy2,0:cnt_sz2] = threshold 
   
      # quality check the final x,y position and fix if needed.
      orig_to_new_diff_x = hd_x - new_x
      orig_to_new_diff_y = hd_y - new_y
      orig_to_new_dist = calc_dist((hd_x,hd_y), (new_x,new_y))
      orig_to_est_diff_x = hd_x - est_x 
      orig_to_est_diff_y = hd_y - est_y 
      orig_to_est_dist = calc_dist((hd_x,hd_y), (est_x,est_y))
      new_to_est_diff_x = new_x - est_x 
      new_to_est_diff_y = new_y - est_y 
      new_to_est_dist = calc_dist((new_x,new_y), (est_x,est_y))

      if med_seg_len is not None:
         #new_metframes[fn]['hd_x'] = hd_x
         #new_metframes[fn]['hd_y'] = hd_y
         if hd_x != 0 and hd_y != 0 :
            if abs(new_to_est_dist) > abs(orig_to_est_dist):
               best_x = hd_x
               best_y = hd_y
            else:
               best_x = new_x 
               best_y = new_y 
            if abs(new_to_est_dist) > 7 and abs(orig_to_est_dist) > 7 and last_four is not None:
               best_x = est_x 
               best_y = est_y
               status = "point override, using estimate"
            #new_metframes[fn]['hd_x'] = best_x
            #new_metframes[fn]['hd_y'] = best_y

            if blob_x != 0 and blob_y != 0 and last_x != None and metframes[fn]['point_status'] != 'FIXED':

               test_len_from_last = calc_dist((last_x,last_y),(blob_x,blob_y))
               len_d = abs(test_len_from_last - len_from_last)
               if len_d < 10:
                  new_metframes[fn]['hd_x'] = blob_x
                  new_metframes[fn]['hd_y'] = blob_y
            if metconf['runs'] >= 2:
               if blob_x != 0 and blob_y != 0:
                  avg_x = int(blob_x + est_x / 2)
                  avg_y = int(blob_y + est_y / 2)
                  #print("AVG XY:", avg_x, avg_y)
                  status = "blob x,y"
                  #new_metframes[fn]['hd_x'] = avg_x
                  #new_metframes[fn]['hd_y'] = avg_y

         else:
            new_metframes[fn]['hd_x'] = 0 
            new_metframes[fn]['hd_y'] = 0 


      #if confirmed_last_frame is not None:
      if False:
         hd_x = 0
         hd_y = 0
         new_metframes[fn]['hd_x'] = hd_x
         new_metframes[fn]['hd_x'] = hd_y
         new_metframes[fn]['ft'] = 0
         new_metframes[fn]['w'] = 0
         new_metframes[fn]['h'] = 0
         new_metframes[fn]['max_px'] = 0
         new_metframes[fn]['ra'] = 0
         new_metframes[fn]['dec'] = 0
         new_metframes[fn]['az'] = 0
         new_metframes[fn]['el'] = 0

      if (bdiff < .2 and len_from_last <= 0) and fc > 3:
         #MIKE
         #print ("THERE IS NO FRAME BECAUSE BDIFF AND LEN:", bdiff, len_from_last, fc)
         no_motion = no_motion + 1
         hd_x = 0
         hd_y = 0
      elif no_motion < 3:
         no_motion = 0

      if no_motion > 3:
         event_ended = 1
   

      if med_seg_len is not None:
         if bdiff != 0 and len_from_last != 0:
            if bdiff < .2 :
               hd_x = 0
               hd_y = 0

      # find new len from last with ideal points
      if best_x is not None and last_x is not None:
         len_from_last = calc_dist((last_x,last_y),(best_x,best_y))
      if fc > 1:
         if last_len_diff <= 0:
            # picked bad / previous point , reject or find new
            print ("DELETE X,Y BAD LEN DIFF:", last_len_diff)
            #hd_x = 0
            #hd_y = 0

      #print("FRAME DATA:", no_motion, fn, hd_x, hd_y, new_x, new_y, best_x, best_y)
      if hd_x != 0 and hd_y != 0:
         res_diff = calc_dist((hd_x,hd_y),(est_x,est_y))
      else:
         res_diff = 0
      if hd_x != 0 and hd_y != 0:
         total_res_diff = total_res_diff + res_diff 
      if fc > 0 and hd_x != 0 and hd_y != 0:
         avg_res_diff = total_res_diff / fc
      else:
         avg_res_diff = avg_res_diff = avg_res_diff
      metconf['avg_res_diff'] = avg_res_diff
      if hd_x != 0 and hd_y != 0:
         # add rect for main ROI area
         cv2.rectangle(img2, (hd_x1, hd_y1), (hd_x2, hd_y2), (128, 128, 128), 1)

         # estimate circle yellow
         if est_x > 0 and est_y > 0:
            cv2.circle(img2,(est_x,est_y), 10, (0,255,255), 1)

         # original red
         cv2.circle(img2,(hd_x,hd_y), 5, (0,0,255), 1)
 
         # updated circle green 
         cv2.circle(img2,(new_x,new_y), 5, (0,255,0), 1)
   
         if blob_x > 0:
            # updated circle green 
            cv2.circle(img2,(new_x,new_y), 5, (255,0,0), 2)

         # blue circle best
         if med_seg_len is not None:
            if best_x > 0 and best_y > 0:
               cv2.circle(img2,(best_x,best_y), 5, (255,255,255), 1)
               cv2.putText(img2, "+" ,  (best_x-3,best_y+3), cv2.FONT_HERSHEY_SIMPLEX, .3, (0, 0, 255), 1)

         if blob_x != 0 and blob_y != 0:
            xs.append(blob_x)
            ys.append(blob_y)
            nx, ny, ra ,dec , az, el= XYtoRADec(blob_x,blob_y,cal_params_file,cal_params,json_conf)
            # add ang seperation for total meteor based on first and last ra/dec
            #ang_sep = angularSeparation(ra,dec,RA_center,dec_center)
            hd_x = blob_x
            hd_y = blob_y
         else:
            xs.append(new_x)
            ys.append(new_y)
            hd_x = new_x 
            hd_y = new_y 
            nx, ny, ra ,dec , az, el= XYtoRADec(new_x,new_y,cal_params_file,cal_params,json_conf)
         new_metframes[fn]['ra'] = ra
         new_metframes[fn]['dec'] = dec
         new_metframes[fn]['az'] = az
         new_metframes[fn]['el'] = el
         new_metframes[fn]['len_from_start'] = len_from_start
         new_metframes[fn]['len_from_last'] = len_from_last

      #if metconf['runs'] > 3 and hd_x == 0 and hd_y == 0:
      if metconf['runs'] > 3:
         new_metframes[fn]['hd_x'] = hd_x
         new_metframes[fn]['hd_y'] = hd_y

      #  Add text info to frame
      desc = "MAX PX: " + str(max_val) 
      cv2.putText(img2, desc,  (5,15), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)

      cv2.putText(img2, "FN:" + str(fn),  (5,50), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)

      desc = str(hd_x) + "," + str(hd_y)
      cv2.putText(img2, "X,Y:" + desc,  (5,70), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)

      desc = str(est_x) + "," + str(est_y)
      cv2.putText(img2, "EST X,Y:" + desc,  (5,90), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)

      cv2.putText(img2, "Status:" + status,  (5,110), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)

      desc = str(avg_res_diff)
      cv2.putText(img2, "AVG RES" + desc,  (5,130), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)

      desc = str(len_from_start)
      cv2.putText(img2, "LEN FROM START" + desc,  (5,150), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)

      desc = str(last_len_from_start)
      cv2.putText(img2, "LAST LEN FROM START" + desc,  (5,170), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
 
      last_len_diff = len_from_start - last_len_from_start
      desc = str(last_len_diff)
      cv2.putText(img2, "LAST LEN DIFF" + desc,  (5,190), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)

      desc = str(med_seg_len)
      cv2.putText(img2, "MED SEG LEN:" + desc,  (5,210), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)


      #if "med_seg_len" in metconf:
      #   desc = str(m) + "," + str(b)
      #   cv2.putText(img2, "M,B:" + desc,  (5,110), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
      #desc = str(bdiff)
      #cv2.putText(img2, "BDIFF:" + desc,  (5,130), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)

      #desc = str(len_from_last)
      #cv2.putText(img2, "LEN FROM LAST:" + desc,  (5,150), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)

      #desc = str(orig_to_new_dist)
      #cv2.putText(img2, "ORG TO NEW DIFF X,Y:" + desc,  (5,170), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)


      desc = str(avg_res_diff)
      if avg_res_diff > 5:
         color = (0,0,255)
      else  :
         color = (255,255,255)
      cv2.putText(img2, "AVG RES:" + desc,  (500,500), cv2.FONT_HERSHEY_SIMPLEX, .8, color, 1)
      if res_diff > 5:
         color = (0,0,255)
      else  :
         color = (255,255,255)
      desc = str(res_diff)
      cv2.putText(img2, "LAST RES:" + desc,  (500,540), cv2.FONT_HERSHEY_SIMPLEX, .8, color, 1)

      if res_diff > 10 or metframes[fn]['max_px'] == 0 and metconf['runs'] > 0:
         desc = str(res_diff) + " " + str(metframes[fn]['max_px'])
         cv2.putText(img2, "BAD POINT!:" + desc,  (400,400), cv2.FONT_HERSHEY_SIMPLEX, .8, (0,255,0), 1)
         hd_x = 0
         hd_y = 0
         new_metframes[fn]['hd_x'] = 0
         new_metframes[fn]['hd_y'] = 0

      cv2.rectangle(img2, (min_x, min_y), (max_x, max_y), (128, 128, 128), 1)
      if show == 1:
         cv2.imshow('pepe2', img2)
      if metconf['runs'] == "":
         metconf['runs'] = 1
      if int(metconf['runs']) < 1:
         cv2.waitKey(10)
      else:
         cv2.waitKey(0)
      if hd_x != 0 and hd_y != 0:
         if blob_x is None:
            last_x = hd_x 
            last_y = hd_y 
         else:
            last_x = blob_x 
            last_y = blob_y 
         last_fn = fn
         if max_val is not None:
            last_max_px = max_val
         last_len_from_start = len_from_start
      fc = fc + 1 
   #print("Confirmed last frame is:", confirmed_last_frame)
   tot = len(len_segs)
   half = int(tot/2)
   #metconf['med_seg_len'] = np.median(len_segs[0:half])
   metconf['med_seg_len'] = np.median(len_segs)
   metconf['runs'] = metconf['runs'] + 1



   bad_frms = []
   xs = [] 
   ys = [] 
   for frm in new_metframes:
      #print(frm, new_metframes[frm])
      hd_x = new_metframes[frm]['hd_x']
      hd_y = new_metframes[frm]['hd_y']
      if hd_x == 0 and hd_y == 0:
         bad_frms.append(frm)
      else:
         xs.append(hd_x)
         ys.append(hd_y)

   min_x = min(xs)
   max_x = max(xs)
   min_y = min(ys)
   max_y = max(ys)
   metconf['crop_box'] = (min_x,min_y,max_x,max_y)

   if metconf['runs'] > 3:
      metconf['bad_frames'] = bad_frms
      #for frm in bad_frms:
      #   print("BAD:", frm)
      #   del(new_metframes[frm])


   return(new_metframes, metconf, avg_res_diff)

def fine_reduce(meteor_red_file, show=0):

   #load reduction
   mf = load_json_file (meteor_red_file)
   mf = cleanup_json_file(mf) 

   # load frames
   frames = load_video_frames(mf['sd_video_file'], json_conf)
   mfd = mf['meteor_frame_data']

   # define first crop box area
   (min_x,min_y,max_x,max_y) = define_crop_box(mfd)

   # load frame data into json struct
   metframes, metconf = setup_json_frame_data (mfd)
   xs = metconf['xs']
   ys = metconf['ys']
   fx = metconf['fx']
   fy = metconf['fy']
   lx = metconf['lx']
   ly = metconf['ly']
   tf = metconf['tf']
   line_dist = metconf['line_dist']
   x_incr = metconf['x_incr']
   x_dir_mod = metconf['x_incr']
   y_dir_mod = metconf['x_incr']
   metconf['crop_box'] = (min_x,min_y,max_x,max_y)

   # check for median_len_seg
   m,b = best_fit_slope_and_intercept(xs,ys)
   metconf['m'] = m
   metconf['b'] = b
   metconf['acl_poly'] = 0

   # load up stars for mask
   mask_px = []
   for star in mf['cat_image_stars']:
      star_x = int(star[7])
      star_y = int(star[8])
      mask_px.append((star_x,star_y))

   metconf['mask_px'] = mask_px
   if "med_seg_len" not in "mf":
      metframes, metconf,avg_res = check_frame_errors(metframes,frames,metconf, mf,show)
      metframes, metconf,avg_res = check_frame_errors(metframes,frames,metconf, mf,show)
      metframes, metconf,avg_res = check_frame_errors(metframes,frames,metconf, mf,show)
      #metframes, frames, metconf = minimize_start_len(metframes,frames,metconf,mf,show)
      #metframes, metconf,avg_res = play_meteor(metframes,frames,metconf, mf,show)
      print("AVG RES:", avg_res)
      exit()
      metframes, metconf,avg_res = play_meteor(metframes,frames,metconf, mf,show)
      metframes, metconf = slope_fixes(metframes, metconf,mf,frames,show)
      metframes, metconf = slope_fixes(metframes, metconf,mf,frames,show)
      metframes, metconf = slope_fixes(metframes, metconf,mf,frames,show)
      exit()
      metframes, frames, metconf = minimize_start_len(metframes,frames,metconf,mf,show)

      #if metconf['runs'] > 3:
      #   bad_frms = metconf['bad_frames'] 
      #   for frm in bad_frms:
      #      print("BAD:", frm)
      #      del(metframes[frm])

      metframes, metconf = slope_fixes(metframes, metconf,mf,frames,show)
      if metconf['avg_res_diff'] > 5:
         metframes, metconf = slope_fixes(metframes, metconf,mf,frames,show)

      for fn in metframes:
         print(metframes[fn]['fn'], metframes[fn]['hd_x'], metframes[fn]['hd_y'], metframes[fn]['max_px'], metframes[fn]['len_from_start'], metframes[fn]['len_from_last'])

    
      mf['metframes'] = metframes
      mf['metconf'] = metconf 
      save_json_file(meteor_red_file, mf)
   print("med_seg_len:", metconf['med_seg_len'])
   print("avg res error:", metconf['avg_res_diff'])

   mf['fine_reduce'] = {}
   mf['fine_reduce']['metconf'] = metconf
   mf['fine_reduce']['metframes'] = metframes

   save_json_file(meteor_red_file, mf)



mrf = sys.argv[1]
if len(sys.argv) == 3:
   show = int(sys.argv[2])
else:
   show = 1
fine_reduce(mrf, show)

