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
   dir_y = fx - ly
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
   this_poly = np.zeros(shape=(1,), dtype=np.float64)

   #err = reduce_start_len(metframes, frames, metconf,show)
   res = scipy.optimize.minimize(reduce_start_len, this_poly, args=( metframes, frames,metconf,mf,show), method='Nelder-Mead')
   #new_med_seg_len = res['x']
   return(metframes,frames,metconf)

def reduce_start_len(poly, metframes,frames,metconf,mf,show=0):
   metconf['med_seg_len'] = float(metconf['med_seg_len'] + poly[0])
   if metconf['runs'] < 5:
      metframes, metconf,avg_res = play_meteor(metframes,frames,metconf,mf)
      metconf['avg_res_diff'] = avg_res
   else:
      return(0)
   return(avg_res)

def slope_fixes(metframes,metconf,mf,show):
   fx = None
   slope_ms = []
   slope_bs = []
   xs = []
   ys = []

   # determine first x,y and initial slope of all points
   for fn in metframes:
      hd_x = metframes[fn]['hd_x']
      hd_y = metframes[fn]['hd_y']
      if fx is None:
         fx = hd_x
         fy = hd_y
      xs.append(hd_x)
      ys.append(hd_y)
   m,b = best_fit_slope_and_intercept(xs,ys)

   # compute and compare slope for each point and compare to main one 
   fc = 0
   for fn in metframes:
      hd_x = metframes[fn]['hd_x']
      hd_y = metframes[fn]['hd_y']
      if fc == 0:
         metframes[fn]['slope_m'] = m
         metframes[fn]['slope_b'] = b
         slope_ms.append(m)
         slope_bs.append(b)
      else:
         xm,xb = best_fit_slope_and_intercept([fx,hd_x],[fy,hd_y])
         metframes[fn]['slope_m'] = xm
         metframes[fn]['slope_b'] = xb
         slope_ms.append(xm)
         slope_bs.append(xb)
      fc = fc + 1

   med_slope_m = np.mean(slope_ms)
   med_slope_b = np.mean(slope_bs)
   print(med_slope_m, med_slope_b)
   new_xs = []
   new_ys = []
   for fn in metframes:
      status = ""
      if metframes[fn]['slope_b'] == 0:
         status = "BAD"
      if abs(abs(metframes[fn]['slope_b']) - abs(med_slope_b)) > 300:
         metframes[fn]['slope_status'] = "BAD"
         status = "BAD"
      if status == "BAD":
         metframes[fn]['hd_x'] = 0
         metframes[fn]['hd_y'] = 0
         metframes[fn]['slope_status'] = "BAD"
      else:
         new_xs.append(metframes[fn]['hd_x'])
         new_ys.append(metframes[fn]['hd_y'])
         metframes[fn]['slope_status'] = "GOOD"
      print(fn, metframes[fn]['slope_m'], med_slope_m, metframes[fn]['slope_b'], med_slope_b,  metframes[fn]['slope_status'])

   best_m,best_b = best_fit_slope_and_intercept([fx,hd_x],[fy,hd_y])
   metconf['slope_m'] = best_m
   metconf['slope_b'] = best_b
   return(metframes, metconf) 


def play_meteor_clip(metframes,frames, metconf,mf,show=0):
   new_metframes = {}
   metframes, metconf = slope_fixes(metframes, metconf,mf,show)
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
   for fn in metframes:
      #print("FN:", fn)
      #fn = int(fn)
      img2, work_img = prep_image(frames[fn])
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
         est_x = int(fx + x_dir_mod * (med_seg_len*xxx))
         est_y = int((m*est_x)+b)
         cv2.line(img2, (hd_x,hd_y), (est_x,est_y), (255,255,255), 1)
      #cv2.imshow('pepe2', img2)
      #cv2.waitKey(0)
         



      if last_x != None:
         # SLOPE TESTS: check slope of this px compared to first and compare to original
         xm,xb = best_fit_slope_and_intercept([fx,hd_x],[fy,hd_y])
         m_dp = (xm * 10) / (m * 10)
         b_dp = (xb *10) / (b * 10)
         print ("SLOPE TEST: ", m_dp, b_dp)

         elp_f = fn - last_fn
         if len(lens) < 2:
            dist_factor = med_seg_len
         dist_factor = np.median(lens)
         est_x = int(last_x + x_dir_mod * (dist_factor*elp_f))
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
      if show == 1:
         cv2.imshow('pepe2', img2)
         cv2.waitKey(0)
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
            est_x = int(last_x + x_dir_mod * (last_four*elp_f))
         else:
            est_x = int(last_x + x_dir_mod * (len_from_last*elp_f))
         try: 
            est_y = int((m*est_x)+b)
         except:
            print("BAD SLOPE!")
            est_x = 0
            est_y = 0
            exit()

      if hd_x == 0 and hd_y == 0 and no_motion < 3 and med_seg_len is not None:
         # frame details are missing try to fix     
         print("TRY TO FIND POINT!", no_motion)
         cnt_sz = 40
         (hd_x, hd_y, hd_y1, hd_y2,hd_x1, hd_x2, max_px,px_diff) = est_frame_pos(est_x,est_y,work_img,cnt_sz)
         cv2.putText(img2, "PX DIFF:" + str(px_diff),  (960,540), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 1)
         if px_diff < 10 :
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
            
         if last_fn is not None:
            len_from_last = calc_dist((last_x,last_y),(hd_x,hd_y))
         if last_four is not None:
            if last_four > 0:
               len_diff = len_from_last / last_four
            else:
               len_diff = 0
         new_x,new_y = hd_x, hd_y 
         new_metframes[fn]['hd_x'] = new_x
         new_metframes[fn]['hd_y'] = new_y
         new_metframes[fn]['max_px'] = int(max_px)
         new_metframes[fn]['len_from_last'] = int(len_from_last)

         cv2.circle(threshold,(new_x,new_y), 10, (0,0,255), 1)

         status = "point created"
      elif med_seg_len is not None and no_motion < 3:
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
         print("FIRST RUN!", hd_x, hd_y, no_motion, med_seg_len )
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
            (x,y,w,h,size,mx,my) = temp[0]
            blob_x = hd_x1 + mx
            blob_y = hd_y1 + my
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

            if blob_x != 0 and blob_y != 0:
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

      if (bdiff < .25 or len_from_last <= 0) and fc > 3:
         #print ("THERE IS NO FRAME BECAUSE BDIFF AND LEN:", bdiff, len_from_last, fc)
         no_motion = no_motion + 1
      elif no_motion < 3:
         no_motion = 0

      if no_motion > 3:
         event_ended = 1
   

      if med_seg_len is not None:
         if bdiff != 0 and len_from_last != 0:
            if bdiff < .3 :
               hd_x = 0
               hd_y = 0

      # find new len from last with ideal points
      if best_x is not None and last_x is not None:
         len_from_last = calc_dist((last_x,last_y),(best_x,best_y))
      if fc > 1:
         if last_len_diff <= 0:
            # picked bad / previous point , reject or find new
            hd_x = 0
            hd_y = 0

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
         else:
            xs.append(new_x)
            ys.append(new_y)
            nx, ny, ra ,dec , az, el= XYtoRADec(new_x,new_y,cal_params_file,cal_params,json_conf)
         new_metframes[fn]['ra'] = ra
         new_metframes[fn]['dec'] = dec
         new_metframes[fn]['az'] = az
         new_metframes[fn]['el'] = el
         new_metframes[fn]['len_from_start'] = len_from_start
         new_metframes[fn]['len_from_last'] = len_from_last


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


      #desc = str(avg_res_diff)
      #if avg_res_diff > 5:
      #   color = (0,0,255)
      #else  :
      #   color = (255,255,255)
      #cv2.putText(img2, "AVG RES:" + desc,  (5,210), cv2.FONT_HERSHEY_SIMPLEX, .4, color, 1)
      if show == 1:
         cv2.imshow('pepe2', img2)
      if metconf['runs'] == "":
         metconf['runs'] = 1
      if int(metconf['runs']) < 5:
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
   for frm in new_metframes:
      #print(frm, new_metframes[frm])
      hd_x = new_metframes[frm]['hd_x']
      hd_y = new_metframes[frm]['hd_y']
      if hd_x == 0 and hd_y == 0:
         bad_frms.append(frm)

   if med_seg_len is not None:
      for frm in bad_frms:
         print("BAD:", frm)
         #del(new_metframes[frm])


   return(new_metframes, metconf, avg_res_diff)

def fine_reduce(meteor_red_file, show=0):

   #load reduction
   mf = load_json_file (meteor_red_file)
   mf = cleanup_json_file(mf) 

   # open display windows
   if show == 1:
      cv2.namedWindow('pepe')
 
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


   # check for median_len_seg
   m,b = best_fit_slope_and_intercept(xs,ys)
   metconf['m'] = m
   metconf['b'] = b

   # load up stars for mask
   mask_px = []
   for star in mf['cat_image_stars']:
      star_x = int(star[7])
      star_y = int(star[8])
      mask_px.append((star_x,star_y))

   metconf['mask_px'] = mask_px
   if "med_seg_len" not in "mf":
      metframes, metconf,avg_res = play_meteor(metframes,frames,metconf, mf,show)
      metframes, frames, metconf = play_meteor_clip(metframes,frames,metconf,mf,show)
      metframes, metconf,avg_res = play_meteor(metframes,frames,metconf,mf,show)
      metframes, frames, metconf = minimize_start_len(metframes,frames,metconf,mf,show)
      metframes, frames, metconf = play_meteor_clip(metframes,frames,metconf,mf,show)
      for fn in metframes:
         print(metframes[fn]['fn'], metframes[fn]['hd_x'], metframes[fn]['hd_y'], metframes[fn]['max_px'], metframes[fn]['len_from_start'], metframes[fn]['len_from_last'])


      #exit()
      #metframes, frames, metconf = play_meteor_clip(metframes,frames,metconf)
      mf['metframes'] = metframes
      mf['metconf'] = metconf 
      save_json_file(meteor_red_file, mf)

   exit()
   save_json_file("test1.json", metframes)
   metframes, metconf,avg_res = play_meteor(metframes,frames,metconf)
   save_json_file("test2.json", metframes)
   
   metframes, metconf,avg_res = play_meteor(metframes,frames,metconf)
   metframes, metconf,avg_res = play_meteor(metframes,frames,metconf)
   metframes, metconf,avg_res = play_meteor(metframes,frames,metconf)

   exit()


   # Remove erroneous frames at end of file
   lc = 0
   last_x = None
   last_y = None
   roll_mag =[]
   bad_frames =[]
   prev_dist = None

   #ftx = last_x - (lc * x_incr)
   #ry = int((m*ftx)+b)
   

   for fn in metframes:
      hd_x = metframes[fn]['hd_x']
      hd_y = metframes[fn]['hd_y']

      if last_x is not None:
         prev_dist = calc_dist((last_x,last_y),(hd_x,hd_y))
         print("PREV DISTANCE: ", prev_dist)

      max_px = metframes[fn]['max_px']
      print(lc, hd_x, hd_y, line_dist, max_px)

      img = frames[fn]
      img2 = cv2.resize(img, (1920,1080))
      img2 = cv2.cvtColor(img2,cv2.COLOR_GRAY2RGB)

      hd_y1 = hd_y - 40
      hd_y2 = hd_y + 40
      hd_x1 = hd_x - 40
      hd_x2 = hd_x + 40
      if hd_x != 0:
         hd_x1, hd_y1, hd_x2, hd_y2 = check_cnt_bounds(hd_x1, hd_y1, hd_x2, hd_y2)
         cv2.circle(img2,(hd_x,hd_y), 1, (0,0,255), 1)
         cnt_img = img2[hd_y1:hd_y2,hd_x1:hd_x2]
         gray_cnt = cv2.cvtColor(cnt_img, cv2.COLOR_BGR2GRAY)
         min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(gray_cnt)
         pxd = max_val - min_val
         roll_mag.append(pxd)
         mag_avg = np.mean(roll_mag)
         new_x = hd_x1 + mx
         new_y = hd_y1 + my

         metframes[fn]['hd_x'] = new_x
         metframes[fn]['hd_y'] = new_y

         if mag_avg > 0:
            mag_perc = pxd / mag_avg
         else: 
            mag_perc = 1 
         if mag_perc < .33:
            cv2.putText(cnt_img, "X",  (5,5), cv2.FONT_HERSHEY_SIMPLEX, .2, (0, 0, 255), 1)
            bad_frames.append(fn)
         else:
            # HD_X = 0 / NO METEOR, TRY TO FIND BASED ON LAST SPOT
            if last_x is not None:
               print("LX: ", last_x, x_incr)
               new_x = last_x + x_incr
               new_y = int((m*new_x)+b)
               hd_x = new_x
               hd_y = new_y
               hd_y1 = hd_y - 40
               hd_y2 = hd_y + 40
               hd_x1 = hd_x - 40
               hd_x2 = hd_x + 40
               hd_x1, hd_y1, hd_x2, hd_y2 = check_cnt_bounds(hd_x1, hd_y1, hd_x2, hd_y2)
               cnt_img = img2[hd_y1:hd_y2,hd_x1:hd_x2]
               gray_cnt = cv2.cvtColor(cnt_img, cv2.COLOR_BGR2GRAY)
               min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(gray_cnt)

               cnew_x = hd_x1 + mx
               cnew_y = hd_y1 + my
               metframes[fn]['hd_x'] = new_x
               metframes[fn]['hd_y'] = new_y
               if confirmed_last_frame is None: 
                  cv2.circle(cnt_img,(mx,my), 1, (0,255,0), 1)
                  cv2.putText(cnt_img, str(pxd) + "/" + str(mag_avg),  (5,5), cv2.FONT_HERSHEY_SIMPLEX, .2, (255, 255, 255), 1)
                  cv2.putText(cnt_img, "?" + str(mag_avg),  (5,10), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
 
         if show == 1:
            cv2.imshow('pepe', cnt_img)
            cv2.waitKey(1)
         last_x = hd_x
         last_y = hd_y
      else:
         if last_x is not None: 
            ftx = last_x - (lc * x_incr)
            ry = int((m*ftx)+b)
            hd_y1 = ry - 20
            hd_y2 = ry + 20
            hd_x1 = ftx - 20
            hd_x2 = ftx + 20
            hd_x1, hd_y1, hd_x2, hd_y2 = check_cnt_bounds(hd_x1, hd_y1, hd_x2, hd_y2)
            cv2.circle(img2,(hd_x,hd_y), 1, (0,0,255), 1)
            cnt_img = img2[hd_y1:hd_y2,hd_x1:hd_x2]
            gray_cnt = cv2.cvtColor(cnt_img, cv2.COLOR_BGR2GRAY)

            min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(gray_cnt)
            new_x = mx + hd_x1
            new_y = my + hd_y1
            pxd = max_val - min_val
            roll_mag.append(pxd)
            mag_avg = np.mean(roll_mag)

            if mag_avg > 0:
               mag_perc = pxd / mag_avg
            else: 
               mag_perc = 1
            if mag_perc < .33:
               cv2.putText(cnt_img, "X",  (5,5), cv2.FONT_HERSHEY_SIMPLEX, .2, (0, 0, 255), 1)
               bad_frames.append(fn)
               metframes[fn]['hd_x'] = new_x
               metframes[fn]['hd_y'] = new_y
            else:
               metframes[fn]['hd_x'] = ftx 
               metframes[fn]['hd_y'] = ry
               metframes[fn]['max_px'] = max_val
               cv2.putText(cnt_img, str(pxd) + "/" + str(mag_avg),  (5,5), cv2.FONT_HERSHEY_SIMPLEX, .2, (255, 255, 255), 1)
            
            last_x = hd_x
            last_y = hd_y
            cv2.circle(cnt_img,(mx,my), 1, (0,255,0), 1)
            if show == 1:
               cv2.imshow('pepe', cnt_img)
               cv2.waitKey(0)

      lc = lc + 1


   exit()
   #DELETE BAD FRAMES
   for bad_fn in bad_frames:
      print("LINE DEL:", bad_fn)
      del metframes[bad_fn] 

   lc = 0
   xs = []
   ys = []
   for fn in metframes:
      if lc == 0:
         ff = fn
         fx = metframes[fn]['hd_x']
         fy = metframes[fn]['hd_y']
      lf = fn
      lx = metframes[fn]['hd_x']
      ly = metframes[fn]['hd_y']
      xs.append(metframes[fn]['hd_x'])
      ys.append(metframes[fn]['hd_y'])

      lc = lc + 1

   tf = lf - ff
   #tf = tf + 1

   line_dist = calc_dist((fx,fy),(lx,ly))
   x_incr = int(line_dist / (tf))
   print("LINE DIST:", line_dist, x_incr, lf, ff, tf)
   seg_d = calc_dist((xs[0],ys[0]),(xs[-1],ys[-1]))
   if seg_d > 5:
      m,b = best_fit_slope_and_intercept(xs,ys)

   regression_line = []

   ffn = mfd[0][1]
   for fn in metframes:
      cc = fn - ffn
      frame_time = metframes[fn]['etime']
      hd_x = metframes[fn]['hd_x']
      hd_y = metframes[fn]['hd_y']
      w = metframes[fn]['w']
      h = metframes[fn]['h']
      max_px = metframes[fn]['max_px']
      ra = metframes[fn]['ra']
      dec = metframes[fn]['dec']
      az = metframes[fn]['az']
      el = metframes[fn]['el']

      img = frames[fn]
      img2 = cv2.resize(img, (1920,1080))
      img2 = cv2.cvtColor(img2,cv2.COLOR_GRAY2RGB)

      tcc = 0
      print("MIKE FR LEN:", len(metframes))
      for tmp in metframes:
         x = metframes[tmp]['hd_x']
         y = metframes[tmp]['hd_y']
         ftx = fx - (tcc * x_incr)
         if x == 0:
            x = ftx
         ry = int((m*x)+b)
         print("MIKEXY: ", fn, x,y, ftx, ry, ff, lf)
         # BLUE 
         cv2.circle(img2,(x,ry), 1, (255,0,0), 1)
         cv2.putText(img2, str(tcc),  (ftx,ry-2), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
         cv2.circle(img2,(ftx,ry), 5, (238,128,0), 1)
         #RED MARK
         if fn < confirmed_last_frame:
            cv2.circle(img2,(x,y), 5, (0,0,255), 1)
         # GREEN
         cv2.circle(img2,(fx,fy), 1, (0,255,0), 1)
         cv2.circle(img2,(lx,ly), 1, (0,255,0), 1)
         tcc = tcc + 1
      

      cv2.rectangle(img2, (min_x, min_y), (max_x, max_y), (128, 128, 128), 1)
      cv2.rectangle(img2, (hd_x-10, hd_y-10), (hd_x+ 10, hd_y+ 10), (128, 128, 128), 1)
      cv2.circle(img2,(hd_x,hd_y), 1, (0,0,255), 1)
      crop_img = img2[min_y:max_y,min_x:max_x]
      ch,cw,x = crop_img.shape
      desc = str(cc) +" " + str(fn) + " " + str(frame_time)
      cv2.putText(crop_img, desc,  (5,ch-5), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
      if show == 1:
         cv2.imshow('pepe', crop_img)
         cv2.waitKey(0)

   # rewrite meteor Frame data
   new_mfd = []
   for fi in metframes:
      fn = metframes[fi]['fn'] 
      ft = metframes[fi]['ft'] 
      hd_x = metframes[fi]['hd_x'] 
      hd_y = metframes[fi]['hd_y'] 
      hd_w = metframes[fi]['w'] 
      hd_h = metframes[fi]['h'] 
      max_px = metframes[fi]['max_px'] 
      ra = metframes[fi]['ra'] 
      dec = metframes[fi]['dec'] 
      az = metframes[fi]['az'] 
      el = metframes[fi]['el'] 
      new_mfd.append((frame_time, fn, hd_x,hd_y,w,h,max_px,ra,dec,az,el))
   
   mf['meteor_frame_data'] = new_mfd   
   save_json_file(meteor_red_file, mf)
   save_json_file("test.json", metframes)

mrf = sys.argv[1]
if len(sys.argv) == 3:
   show = int(sys.argv[2])
else:
   show = 0
fine_reduce(mrf, show)

