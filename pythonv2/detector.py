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
from lib.Video_Tools_cv import remaster
from lib.VideoLib import get_masks, find_hd_file_new, load_video_frames, sync_hd_frames, make_movie_from_frames, add_radiant

from lib.UtilLib import check_running, angularSeparation, bound_cnt
from lib.CalibLib import radec_to_azel, clean_star_bg, get_catalog_stars, find_close_stars, XYtoRADec, HMS2deg, AzEltoRADec, get_active_cal_file

from lib.ImageLib import mask_frame , stack_frames, preload_image_acc
from lib.ReducerLib import setup_metframes, detect_meteor , make_crop_images, perfect, detect_bp, best_fit_slope_and_intercept, id_object, metframes_to_mfd

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

def check_conversion(json_conf, extra):
   dirs = glob.glob("/mnt/ams2/conversion/*")
   good = 0
   bad = 0
   for dir in dirs:
      pub_files = glob.glob(dir + "/*pub.mp4")
      if len(pub_files) > 0:
         good = good + 1
      else:
         bad = bad + 1
         status = "pub file missing\n"
         hd_files = glob.glob(dir + "/*HD.mp4") 
         if len(hd_files) < 2:
            print("HD DETECTION FILE IS MISSING.")
         print(dir, len(pub_files))
   print("GB:", good, bad)

def convert_data(sd_video_file, json_conf):
   sd_fn = sd_video_file.split("/")[-1]
   sd_dir = sd_video_file.replace(sd_fn, "")

   meteor_json_filename = sd_video_file.replace(".mp4", ".json")
   reduced_json_filename = sd_video_file.replace(".mp4", "-reduced.json")
   mj = load_json_file(meteor_json_filename)
   if cfe(reduced_json_filename) == 1:
      rd = load_json_file(reduced_json_filename)
   else:
      rd = {}
   tmp_dir =  "/mnt/ams2/conversion/" + sd_fn
   tmp_dir = tmp_dir.replace(".mp4", "")
   hd_video_file = mj['hd_trim']
   if "hd_video_file" in rd:
      hd_video_file = rd['hd_video_file']
      hd_fn = hd_video_file.split("/")[-1]
      print("FROMRED")
   else:
      if "hd_trim" in mj:
         hd_video_file = mj['hd_trim'] 
         hd_fn = hd_video_file.split("/")[-1]
         hd_video_file = sd_dir + "/" + hd_fn
         print("TRIM", hd_video_file)
       
      else:
         hd_video_file = None

   print("HD VIDEO:", hd_video_file)

   if cfe(tmp_dir, 1) == 0:
      os.system("mkdir " + tmp_dir)
   if cfe(sd_video_file) :
      cmd = "cp " + sd_video_file + " " + tmp_dir
      os.system(cmd)
      js = sd_video_file.replace(".mp4", "-reduced.json")
      cmd = "cp " + js + " " + tmp_dir
   else:
      print("Bad file", sd_video_file)
      exit()
   if hd_video_file is not None: 
      cmd = "cp " + hd_video_file + " " + tmp_dir
      os.system(cmd)

   cmd = "./detector.py rd " + tmp_dir + "/" + sd_fn
   os.system(cmd)
 
   if hd_video_file is not None:
      if cfe(hd_video_file) :
         cmd = "./detector.py rd " + tmp_dir + "/" + hd_fn
         os.system(cmd)
      else:
         print("HD VIDEO FILE DOES NOT EXIST?")
         exit()

   new_sd_file = None
   new_hd_file = None
   all_files = glob.glob(tmp_dir + "/" + "*") 
   for file in all_files:
      print(file)
      file_name = file.split("/")[-1]
      if "mp4" in file and "SD" in file:
         new_sd_file = file
      if "mp4" in file and "HD" in file and "trim" not in file_name and "pub" not in file_name:
         print("HD FOUND", file)
         new_hd_file = file
   if new_sd_file is None:
      print("FAILED TO CONVERT SD!", new_sd_file)
      exit()
   if new_hd_file is None:
      print("FAILED TO CONVERT HD!", new_hd_file)
      exit()

   new_sd_json_file = new_sd_file.replace(".mp4", ".json")
   new_hd_json_file = new_hd_file.replace(".mp4", ".json")
   new_sd_json = load_json_file(new_sd_json_file)
   if cfe(new_hd_json_file) == 0:
      print("FAILED TO MAKE HD JSON", new_hd_json_file) 
      exit()
   
   new_hd_json = load_json_file(new_hd_json_file)


   final_json = new_hd_json
   for fn in final_json['metframes']:
      if fn in final_json['metframes'][fn]:
         final_json['metframes'][fn]['sd_x'] = new_sd_json['metframes'][fn]['sd_x'] 
         final_json['metframes'][fn]['sd_y'] = new_sd_json['metframes'][fn]['sd_y'] 
         final_json['metframes'][fn]['sd_inenstity'] = new_sd_json['metframes'][fn]['sd_intensity'] 
         final_json['metframes'][fn]['hd_inenstity'] = new_hd_json['metframes'][fn]['sd_intensity'] 

   temp = new_sd_file.replace("SD", "HD")
   if temp != new_hd_file:
      new_new_sd_file = new_hd_file.replace("HD", "SD")
      os.system("mv " + new_sd_file + " " + new_new_sd_file)
      new_sd_file = new_new_sd_file
      os.system("rm " + new_sd_json_file)
      new_sd_json_file = new_sd_file.replace(".mp4", ".json")

   new_json_file = new_sd_json_file
   new_json_red_file = new_sd_json_file.replace(".json", "-reduced.json")
   save_json_file(new_json_file, final_json)
   save_json_file(new_json_red_file, final_json)

   data = {}
   data['video_file'] = new_hd_file
   data['json_conf'] = json_conf

   #perseids radiant
   ra = 46
   dec = 59
   new_frame = np.zeros((1080,1920),dtype=np.uint8)
   new_frame, rad_x, rad_y = add_radiant(ra,dec,new_frame,new_json_file, final_json,json_conf)
   data['rad_x'] = rad_x
   data['rad_y'] = rad_y
   data['rad_name'] = "Perseids" 


   remaster(data )

   # Now move the files from this dir to the meteor_archive dir



def update(file, json_conf):
   # Update the new reduction files with any missing info.
   meteor_video_filename = file 
   meteor_json_filename = file.replace(".mp4", ".json")
   meteor_json = load_json_file(meteor_json_filename)
   meteor_json['metframes'] = update_intensity(meteor_json['metframes'], meteor_video_filename, 0)
   meteor_json = make_reduce_files(meteor_json, meteor_json_filename, json_conf)
   save_json_file(meteor_json_filename, meteor_json)



def batch_best(day, json_conf):
   files = glob.glob("/mnt/ams2/meteor_archive/" + day + "/" + day + "*.mp4")
   for file in files:
      if "allmeteors" not in file and "pub" not in file:
         dist = check_dist(file, json_conf)
         print(file, dist)

def check_dist(video_file, json_conf):
   json_file = video_file.replace(".mp4", ".json")
   print(json_file)
   json_data = load_json_file(json_file)
   sx = json_data['metconf']['mxs'][0] 
   sy = json_data['metconf']['mys'][0] 
   ex = json_data['metconf']['mxs'][-1] 
   ey = json_data['metconf']['mys'][-1] 
   dist = calc_dist((sx,sy),(ex,ey))

   return(dist) 

def batch_check_reject(day, json_conf):
   files = glob.glob("/mnt/ams2/meteor_archive/" + day + "/" + day + "*.mp4")
   for file in files:
      if "allmeteors" not in file:
         check_reject(file, json_conf)

def check_reject(video_file, json_conf):
   json_file = video_file.replace(".mp4", ".json")
   json_data = load_json_file(json_file)
   #print(json_data['metconf'])
   #for test in json_data['objects']['test_results']:
   #   print(test[0], test[1], test[2])
   metconf = json_data['metconf']
   mxs = metconf['mxs']
   mys = metconf['mys']
   min_x = min(mxs)
   min_y = min(mys)
   max_x = max(mxs)
   max_y = max(mys)
   dist = calc_dist((min_x, min_y), (max_x,max_y))
   x1,y1,x2,y2,dist = make_crop_box(json_data, 1920,1080)
   print("DIST:", dist, video_file)
   #print("DIST PER FRAME:", dist/len(mxs))
   if dist < 5:
      cmd = "mv " + video_file + "/mnt/ams2/bad/"
      print(cmd)
      #os.system(cmd)
      cmd = "mv " + json_file + "/mnt/ams2/bad/"
      print(cmd)
      #os.system(cmd)


def reduce_acl(this_poly, metframes,metconf,frames,mode=0,show=0,key_field = "m"):
   xs = []
   ys = []
   err = []
   fcc = 0
   m_10 = metconf['m']
   b_10 = metconf['b']
   acl_poly = this_poly[1]
  
   key_x = key_field + "x"
   key_y = key_field + "y"

   if "acl_med_seg_len" in metconf:
      med_seg = (this_poly[0] + np.float64(metconf['acl_med_seg_len']))
   else:
      med_seg = (this_poly[0] + np.float64(metconf['med_seg_len']))

   for fn in metframes:
      est_res = 0
      ifn = int(fn) -1
      img = frames[ifn].copy()
      img = cv2.resize(img, (1920,1080))
      if len(img.shape) == 2:
         img_gray = img
         img = cv2.cvtColor(img,cv2.COLOR_GRAY2RGB)
      else:
         img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

      est_x = int( metconf['fx'] + (metconf['x_dir_mod'] * (med_seg*fcc)) + (acl_poly * (fcc*fcc)) )
      est_y = int((m_10*est_x)+b_10)

      cv2.circle(img,(est_x,est_y), 4, (0,255,255), 1)
      bp_x = metframes[fn][key_x]
      bp_y = metframes[fn][key_y]
      cv2.circle(img,(bp_x,bp_y), 4, (0,0,255), 1)
      xs.append(bp_x)
      ys.append(bp_y)

      bp_est_res = calc_dist((bp_x,bp_y), (est_x,est_y))
      hd_est_res = bp_est_res

      if mode == 1:
         metframes[fn]['est_x'] = est_x
         metframes[fn]['est_y'] = est_y
         metframes[fn]['acl_res'] = hd_est_res

      err.append(hd_est_res)

      cv2.putText(img, str(med_seg) + " " + str(acl_poly),  (10,10), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,0,255), 1)

      if show == 1:
         cv2.imshow('pepe', img)
         cv2.moveWindow('pepe',25,25)
         cv2.waitKey(0)
      fcc = fcc + 1

      if len(xs) > 10:
         n_m_10,n_b_10 = best_fit_slope_and_intercept(xs[-10:],ys[-10:])
         if abs(n_b_10 - b_10) < 200:
            m_10 = n_m_10
            b_10 = n_b_10
   #print("ACL RES:", np.mean(err))
   if mode == 0:
      return(np.mean(err))
   else:
      return(np.mean(err), metframes)


def reduce_fov_pos(this_poly, cal_params, cal_params_file, oimage, json_conf, paired_stars, min_run = 1, show=0):
   print("LEN PAIRED STARS:", len(paired_stars))
   in_cal_params = cal_params.copy()
   image = oimage.copy()
   image = cv2.resize(image, (1920,1080))
   # cal_params_file should be 'image' filename
   #org_az = in_cal_params['center_az']
   #org_el = in_cal_params['center_el']
   org_pixscale = in_cal_params['orig_pixscale']
   #org_pos_angle = in_cal_params['orig_pos_ang']
   new_az = in_cal_params['center_az'] + this_poly[0]
   new_el = in_cal_params['center_el'] + this_poly[1]

   position_angle = float(in_cal_params['position_angle']) + this_poly[2]
   pixscale = float(in_cal_params['orig_pixscale']) + this_poly[3]

   #position_angle = float(in_cal_params['position_angle']) 
   #pixscale = float(org_pixscale)

   rah,dech = AzEltoRADec(new_az,new_el,cal_params_file,in_cal_params,json_conf)
   rah = str(rah).replace(":", " ")
   dech = str(dech).replace(":", " ")
   ra_center,dec_center = HMS2deg(str(rah),str(dech))

   in_cal_params['position_angle'] = position_angle
   in_cal_params['ra_center'] = ra_center
   in_cal_params['dec_center'] = dec_center
   in_cal_params['center_az'] = new_az 
   in_cal_params['center_el'] = new_el
   in_cal_params['pixscale'] = pixscale
   in_cal_params['device_lat'] = json_conf['site']['device_lat']
   in_cal_params['device_lng'] = json_conf['site']['device_lng']
   in_cal_params['device_alt'] = json_conf['site']['device_alt']

   for data in paired_stars:
      iname,mag,o_ra,o_dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,old_cat_x,old_cat_y,six,siy,cat_dist  = data
      cv2.rectangle(image, (old_cat_x-5, old_cat_y-5), (old_cat_x + 5, old_cat_y + 5), (255), 1)
      cv2.line(image, (six,siy), (old_cat_x,old_cat_y), (255), 1)
      cv2.circle(image,(six,siy), 10, (255), 1)

   fov_poly = 0
   pos_poly = 0
   x_poly = in_cal_params['x_poly']
   y_poly = in_cal_params['y_poly']
   #print(in_cal_params['ra_center'], in_cal_params['dec_center'], in_cal_params['center_az'], in_cal_params['center_el'], in_cal_params['position_angle'], in_cal_params['pixscale'], this_poly)
   cat_stars = get_catalog_stars(fov_poly, pos_poly, in_cal_params,"x",x_poly,y_poly,min=0)
   new_res = []
   new_paired_stars = []
   used = {}
   org_star_count = len(paired_stars)
   for cat_star in cat_stars:
      (name,mag,ra,dec,new_cat_x,new_cat_y) = cat_star
      dname = name.decode("utf-8")
      for data in paired_stars:
         iname,mag,o_ra,o_dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,old_cat_x,old_cat_y,six,siy,cat_dist  = data
#dname == iname:
         if (ra == o_ra and dec == o_dec) or (iname == dname and iname != ''):
            pdist = calc_dist((six,siy),(new_cat_x,new_cat_y))
            if pdist <= 20:
               new_res.append(pdist)
               used_key = str(six) + "." + str(siy)
               if used_key not in used:
                  new_paired_stars.append((iname,mag,ra,dec,new_cat_x,new_cat_y,six,siy,pdist))

                  used[used_key] = 1
                  new_cat_x,new_cat_y = int(new_cat_x), int(new_cat_y)
                  cv2.rectangle(image, (new_cat_x-5, new_cat_y-5), (new_cat_x + 5, new_cat_y + 5), (255), 1)
                  cv2.line(image, (six,siy), (new_cat_x,new_cat_y), (255), 1)
                  cv2.circle(image,(six,siy), 10, (255), 1)

   paired_stars = new_paired_stars
   tres  =0
   for iname,mag,ra,dec,new_cat_x,new_cat_y,six,siy,pdist in new_paired_stars:
      tres = tres + pdist

   orig_star_count = len(in_cal_params['cat_image_stars'])

   if len(paired_stars) > 0:
      avg_res = tres / len(paired_stars)
   else:
      avg_res = 9999999
      res = 9999999

   if orig_star_count > len(paired_stars):
      pen = orig_star_count - len(paired_stars)
   else:
      pen = 0
   pen = 0
   avg_res = avg_res + (pen * 10)
   show_res = avg_res - (pen*10)
   desc = "RES: " + str(show_res) + " " + str(len(new_paired_stars)) + " " + str(orig_star_count) + " PEN:" + str(pen)
   cv2.putText(image, desc,  (10,50), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 1)
   desc2 = "CENTER AZ/EL/POS" + str(new_az) + "/" + str(new_el) + "/" + str(in_cal_params['position_angle'])
   cv2.putText(image, desc2,  (10,80), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 1)

   desc2 = "PX SCALE:" + str(in_cal_params['pixscale'])
   cv2.putText(image, desc2,  (10,110), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 1)

   print("AVG RES:", avg_res, len(paired_stars), "/", org_star_count, new_az, new_el, ra_center, dec_center, position_angle)
   print("POLY:", x_poly, y_poly)
   if show == 1:
      show_img = cv2.resize(image, (960,540))
      if "cam_id" in in_cal_params:
         if show == 1:
            cv2.imshow(cam_id, show_img)
      else:
         if show == 1:
            cv2.imshow('pepe', show_img)
      if min_run == 1:
         if show == 1:
            cv2.waitKey(70)
      else:
         if show == 1:
            cv2.waitKey(1)

   if min_run == 1:
      return(avg_res)
   else:
      return(show_res)


def remove_dupe_img_stars(img_stars):
   index = {}
   new_list = []
   #print(img_stars)
#   for x,y,flux in img_stars:
   for x,y in img_stars:
      key = str(x) + ":" + str(y)
      if key not in index:
         bad = 0
         for lx,ly in new_list:
            dist = calc_dist((x,y), (lx,ly))
            if dist < 10:
               bad = 1
         if bad == 0:
            new_list.append((x,y))
         index[key] = 1
   return(new_list)



def lookup_star_in_cat(ix,iy,cat_stars,no_poly_cat_stars, star_dist=20,):
   #print("LOOKUP:", ix,iy)
   close = []
   for cat_star in cat_stars:
      name,mag,ra,dec,new_cat_x,new_cat_y = cat_star
      # to get the plus do ra,dec fwd and then compare that to ix,iy to get the distance? Big improvement?
      px_dist = calc_dist((ix,iy),(new_cat_x,new_cat_y))
      close.append((ix,iy,px_dist,name,mag,ra,dec,new_cat_x,new_cat_y))
   temp = sorted(close, key=lambda x: x[2], reverse=False)
   closest = temp[0]
   six,siy,spx_dist,sname,smag,sra,sdec,snew_cat_x,snew_cat_y = closest

   key = str(closest[5]) + ":" + str(closest[6])
   if key in no_poly_cat_stars:
      no_poly_star = no_poly_cat_stars[key]
      np_name,np_mag,np_ra,np_dec,np_new_cat_x,np_new_cat_y = no_poly_star
      np_angle_to_center = find_angle((960,540), (np_new_cat_x, np_new_cat_y))
      istar_angle_to_center = find_angle((960, 540), (ix,iy))
      istar_dist_to_center = calc_dist((ix, iy), (960,540))
      ang_diff =  abs(np_angle_to_center - istar_angle_to_center)
      #if ang_diff < 30:
      print("STAR: ", spx_dist, ang_diff)


   else:
      print("NO POLY CAT STAR KEY FOUND FOR KEY:", key)
   star_dist = 20
   if key in no_poly_cat_stars and closest[2] < star_dist and ang_diff < 10:
      #print("NP STAR ANGLE/ I STAR ANG TO CENTER:", ix, iy, np_new_cat_x, np_new_cat_y, np_angle_to_center, istar_angle_to_center, istar_dist_to_center , closest[2] )
      #print("CLOSEST:", closest)
      return(1, closest)
   else:
      #print("FAIL NP STAR ANGLE/ I STAR ANG TO CENTER:", ix, iy, np_new_cat_x, np_new_cat_y, np_angle_to_center, istar_angle_to_center, istar_dist_to_center , closest[2] )

      return(0, closest)


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
   clip_start_time, clip_start_time_str = get_clip_time(video_file)
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

   objects = []
   for frame in frames:
      extra_meteor_sec = int(fn) / 25
      meteor_frame_time = clip_start_time + datetime.timedelta(0,extra_meteor_sec)
      meteor_frame_time_str = meteor_frame_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]


      show_frame = frame 
      crop_img = np.zeros((200,200),dtype=np.uint8)
      orig_frames.append(frame.copy())
      frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
      frame = mask_frame(frame, mask_points, masks,mask_size)
      show_frame = frame.copy()

      frame_data[fn] = {}
      frame_data[fn]['fn'] = fn
      frame_data[fn]['ft'] = meteor_frame_time_str
      frame_data[fn]['frame_time'] = meteor_frame_time_str
      frame_data[fn]['frame_time_str'] = meteor_frame_time_str
      blur_frame = cv2.GaussianBlur(frame, (7, 7), 0)
      blur_last = cv2.GaussianBlur(last_frame, (7, 7), 0)

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
      print("MAX:", max_val, avg_val)
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
         #thresh_val = 10

         _, subframe_thresh = cv2.threshold(subframe.copy(), thresh_val, 255, cv2.THRESH_BINARY)

         frame_cnts = do_contours(subframe_thresh)
         frame_data[fn]['frame_cnts'] = frame_cnts
         print("CNTS:", frame_cnts)
         obj_cnts = []
         for cnt in frame_cnts:
            cx, cy, cw, ch = cnt
            object, objects = id_object(None, objects,fn, (int(cx),int(cy)), int(max_val), int(sum_val), img_w, img_h)
            if "oid" in object:
               cv2.rectangle(show_frame, (cx, cy), (cx+cw, cy+ch), (128,128,128), 1)
               cv2.putText(show_frame, str(object['oid']),  (cx,cy), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1) 
               obj_cnts.append((object['oid'], cx,cy,cw,ch))
               frame_data[fn]['obj_cnts'] = obj_cnts

         cv2.imshow('pepe', show_frame)
         cv2.waitKey(0)

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

      frame_data[fn]['cm'] = cm
      frame_data[fn]['nonmo'] = nomo
      print(fn, max_val, cm, nomo)
      fn = fn + 1
      last_x = mx
      last_y = my
      cropframes.append(crop_img)

   if cm >= 2 :
      print("Add Final Event.")
      events.append([first_eframe, fn])
      stacks.append(stack_img)
      motion = 0

   print("FRAMES:", len(frames))
   print("BP EVENTS:", len(events))
   video_data = {}
   video_data['masks'] = masks
   video_data['mask_points'] = mask_points
   video_data['frame_data'] = frame_data
   video_data['events'] = events
   video_data['objects'] = objects
   return(video_data, subframes, cropframes )







def check_video_status(file):
   frm_fn = file.split("/")[-1]
   frm_dir = file.replace(frm_fn, "")
   frm_fn = frm_fn.replace(".mp4", "-framedata.json")
   frame_data_file = frm_dir + frm_fn
   processed = 0
   if cfe(file) == 0:
      desc = "File does not exist! " + file
      print(desc)
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

def get_clip_time(video_file):
   hd_datetime, hd_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(video_file)
   if "trim" not in video_file:
      orig_trim_num = 0
   else:
      ttt = video_file.split("trim")

      if "HD" in ttt[-1]:
         el = ttt[-1].split("-")
         orig_trim_num = int(el[1])
      else:
         orig_trim_num = int(ttt[-1].replace(".mp4", ""))

   orig_trim_seconds = orig_trim_num / 25

   orig_clip_start_time = hd_datetime + datetime.timedelta(0,orig_trim_seconds)

   day = orig_clip_start_time.strftime('%Y_%m_%d')
   orig_clip_start_time_str = orig_clip_start_time.strftime('%Y_%m_%d_%H_%M_%S_%f')[:-3]
   
   return(orig_clip_start_time, orig_clip_start_time_str)

def run_detect(video_file, show):
   # check the file exists and current processing status
   print("RUN DETECT")
   status, mode, hd, processed, video_data, video_data_file, desc = check_video_status(video_file)
   #load the frames
   frames = load_video_frames(video_file, json_conf, 0, 0, [], 1)
   img_h, img_w = frames[0].shape[:2]
   if img_w > 1000:
      hd = 1
      hdm_x = 1
      hdm_y = 1
   else:
      hd = 0
      hdm_x = 1920 / img_w
      hdm_y = 1080  / img_h

   #check for a bright pixel detection inside the frame set
   #processed = 0
   if processed != 1:
      print("Not processed!")
      video_data, subframes, cropframes = process_video_frames(frames, video_file)
      video_data['hd'] = hd
    
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
            if show == 1:
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

   meteor_events = []
   for obj in objects:
      if obj['meteor'] == 1:
         print(obj)
         for test in obj['test_results']:
            print("METEOR:", obj['oid']) 
            print("METEOR:", test[0], test[1], test[2])
         meteor_in_clip = 1
         meteor_objs.append(obj['oid'])
         hist = obj['history']
         first = hist[0][0]
         last = hist[-1][0]
         meteor_events.append((first,last))
      else:
         print(obj['oid']) 
         print(obj)
         score = 0
         for test in obj['test_results']:
            print(test[0], test[1], test[2])
            if test[0] == "CM/Gaps" and test[1] == 0:
               score = score - 10
            if test[0] == "Dist" and test[1] == 0:
               score = score - 10
            score = score + int(test[1])
         if score > 9:
            meteor_objs.append(obj['oid'])
            meteor_found = 1
            meteor_in_clip = 1
            hist = obj['history']
            first = hist[0][0]
            last = hist[-1][0]
            meteor_events.append((first,last))

         print("OBJECT SCORE:", score)

   if meteor_in_clip == 0:
      save_json_file(video_data_file, video_data)
      print("NO meteors here.")
      exit()

   print("METEOR OBJS:", meteor_objs)
   print("METEOR EVENTS:", meteor_events)
   video_data['events'] = meteor_events

   video_data['sd_objects'] = objects

   # determine the blob positions if it hasn't been done yet
   #cropframes = make_cropframes(frames, video_data['frame_data'])

   #frame_data = find_blobs_in_crops(cropframes, video_data['frame_data'])

   #video_data['frame_data'] = frame_data


   # TRIM OUT A VIDEO FILE FOR EACH METEOR EVENT IN THIS CLIP IF IT DOESN'T EXIST YET
   
   ec = 0
   for event in video_data['events']:
      start, end = event
      is_meteor = 1
      # make sure the object inside this event is actually a meteor and not something else. 

      #for fc in range(start,end):
      #   if fc not in frame_data:
      #      fc = str(fc )
      #   if "obj_cnts" in frame_data[fc]:
      #      these_objs = []
      #      for cnt in frame_data[fc]['obj_cnts']:
      #         oid = cnt[0]
      #         if int(oid) in meteor_objs or str(oid) in meteor_objs:
      #            is_meteor = 1
      #            if ec in video_data['event_data']:
      #               video_data['event_data'][ec]['meteor'] = 1
      #            if str(ec) in video_data['event_data']:
      #               ec = str(ec)
      #               video_data['event_data'][ec]['meteor'] = 1

      if is_meteor == 1:
         print("METEOR FOUND!:")
         video_data = setup_calib(video_data, frames[0])     

         meteor_video_filename, event_start_time = make_meteor_video_filename(video_file, start, hd)
         fns, start_buff, end_buff = add_frame_buffer(len(frames), start, end)

         meteor_json_filename = meteor_video_filename.replace(".mp4", ".json")
         if cfe(meteor_json_filename) == 0:
            meteor_json = make_meteor_json(event, video_data, event_start_time, meteor_video_filename ) 
         else:
            meteor_json = load_json_file(meteor_json_filename)
            meteor_json = post_load_mj(meteor_json)

         # now smooth out the metframes and make sure all of the points are good. 
         metconf = update_metconf(meteor_json)
         meteor_json['metconf'] = metconf
         meteor_json['avg_res'] = 9999 
         print("MIKE SMOTH")

         meteor_json['hd'] = hd
         if hd == 0:
            meteor_json['hdm_x'] = hdm_x
            meteor_json['hdm_y'] = hdm_y
         else:
            meteor_json['hdm_x'] = 1
            meteor_json['hdm_y'] = 1
         meteor_json = smooth_points_new(meteor_json, frames)

         meteor_json['metconf']['video_data_file'] = video_data_file
         meteor_json['cal_params'] = video_data['cal_params']
         meteor_json['start_buff'] = start_buff 
         meteor_json['end_buff'] = end_buff 
         
         print("MIKE SMOTH")


         # now convert the x,y points to az,el

         meteor_json = reduce_metframes(meteor_json, meteor_json_filename, video_data['cal_params'])
         print("MIKE REDUCE")
         meteor_json = remap_metframes(meteor_json)

     
         if cfe(meteor_video_filename) == 0:
            make_movie_from_frames(frames, fns, meteor_video_filename)
         print("Meteor Movie Made:", meteor_video_filename)
         print("Meteor JSON Saved:", meteor_json_filename)
         save_json_file(meteor_json_filename, meteor_json)
         
         meteor_json = make_reduce_files(meteor_json, meteor_json_filename, json_conf)
         meteor_json['metframes'] = update_intensity(meteor_json['metframes'], meteor_video_filename, hd, hdm_x, hdm_y, 0)
         meteor_json['sd_objects'] = objects
         save_json_file(meteor_json_filename, meteor_json)
      ec = int(ec) + 1

   # do final review of frames and points

   video_data['sd_objects'] = objects
   video_data['meteor_found'] = meteor_found
   print("VIDEO DATA FILE:", video_data_file)
   save_json_file(video_data_file, video_data)    
   #review_meteor(meteor_json, frames)
   #os.system("./detector.py rv " + meteor_json_filename) 

def update_intensity(metframes, video_file,hd, hdm_x, hdm_y, show = 0):

   sd_frames = load_video_frames(video_file, json_conf, 0, 0, [], 1)

   base_img = sd_frames[0].copy()
   base_img = cv2.cvtColor(base_img, cv2.COLOR_BGR2GRAY)
   for fn in metframes:
      ifn = int(fn) - 1
      sd_img = sd_frames[ifn].copy()
      sd_img = cv2.cvtColor(sd_img, cv2.COLOR_BGR2GRAY)
      img_h, img_w = sd_img.shape[:2]
      if "w" in metframes:
         w = metframes[fn]['w']
         h = metframes[fn]['h']
      else:
         w = 5 
         h = 5 
      cnt_x = metframes[fn]['hd_x'] - int(w / 2)
      cnt_y = metframes[fn]['hd_y'] - int(h / 2)
      print("CNTX:", cnt_x, cnt_y, w, h, sd_img.shape)
      #cv2.rectangle(sd_img, (int(cnt_x), int(cnt_y)), (int(cnt_x+w), int(cnt_y+h)), (100,100,100), 1)

      x1,y1,x2,y2 = bound_cnt(metframes[fn]['hd_x'],metframes[fn]['hd_y'],img_w,img_h,50)
      base_cnt_img = base_img[y1:y2,x1:x2]
      cnt_img = sd_img[y1:y2,x1:x2]
      subimage = cv2.subtract(cnt_img,base_cnt_img)


      min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(subimage)
     # cv2.imshow('pepe', subimage)
      #cv2.waitKey(80)
      #print("INTENSITY:", fn, cnt_x, cnt_y, np.sum(cnt_img) , np.sum(base_cnt_img) )
      #metframes[fn]['sd_intensity'] = float(np.sum(cnt_img)) - float(np.sum(base_cnt_img))
      if subimage is not None:
         metframes[fn]['sd_intensity'] = float(np.sum(subimage)) 
      else:
         metframes[fn]['sd_intensity'] = 0
      metframes[fn]['sd_max_px'] = float(max_val)
      metframes[fn]['x1'] = x1 
      metframes[fn]['y1'] = y1 
      metframes[fn]['x2'] = x2
      metframes[fn]['y2'] = y2
      if hd == 1:
         metframes[fn]['sd_x'] = int(x1/hdm_x)
         metframes[fn]['sd_y'] = int(y1/hdm_y)
      else:
         metframes[fn]['sd_x'] = x1
         metframes[fn]['sd_y'] = y1
      metframes[fn]['sd_w'] = 5
      metframes[fn]['sd_h'] = 5
    #  metframes[fn]['ft'] = metframes[fn]['frame_time'] 

      cnt_thumb = video_file.replace(".mp4", "-frm" + str(fn) + ".png")
      metframes[fn]['cnt_thumb'] = cnt_thumb

      #print("Intensity:",  metframes[fn]['sd_intensity'])
   return(metframes)


def clean_points(video_data, frames):
   print("clean")
   events = video_data['events']
   for key in video_data :
      print(key)
   print(video_data['events'])
   for event in events:
      for fn in range(event[0], event[1]):
         img = frames[fn]
         cv2.imshow('pepe', img)
         cv2.waitKey(0) 
   exit()
   return(video_data)

def remap_metframes(meteor_json):
   start_buff = meteor_json['start_buff']
   new_metframes = {}
   metframes = meteor_json['metframes']
   first_frame = None
   remap = 0
   for fn in metframes:    
      if first_frame is None:
         if int(fn) != int(start_buff):
            print("These frames need to be remapped to line up with the meteor clip!")
            remap = 1
         first_frame = fn
   new_fn = start_buff + 1
   if remap == 1:
      for fn in metframes:
         new_metframes[new_fn] = metframes[fn]
         new_fn = new_fn + 1
         
   
   meteor_json['metframes'] = new_metframes
   return(meteor_json)

def quick_review(meteor_json_file, frames, video_file = None, show = 1): 
   meteor_json = load_json_file(meteor_json_file)
   metconf = meteor_json['metconf']
   if frames is None:
    
      print("Loading: ", video_file)
      frames = load_video_frames(video_file, json_conf, 0, 0, [], 1)
      
   
   print("Review meteor.", len(frames))
   mf = meteor_json['metframes']
   fn = 1
   fc = 0
   for frame in frames:
      ifn = int(fn)
      sfn = str(fn)
      #print("FN:", fn, ifn)
      frame = frames[fc]
      show_frame = frames[fc].copy()
      if sfn in mf:
         if "est_x" in mf[sfn]:
            est_x = mf[sfn]['est_x'] 
            est_y = mf[sfn]['est_y'] 
            cv2.circle(show_frame,(est_x,est_y), 10, (0,255,255), 1)
         hd_x = mf[sfn]['hd_x'] 
         hd_y = mf[sfn]['hd_y'] 
         cv2.circle(show_frame,(hd_x,hd_y), 10, (0,0,255), 1)
         if show == 1:
            cv2.imshow('pepe', show_frame)
            cv2.waitKey(0)
      fn = fn + 1
      fc = fc + 1

def review_meteor(meteor_json_file, frames, video_file = None, show = 1): 
   meteor_json = load_json_file(meteor_json_file)
   metconf = meteor_json['metconf']
   if frames is None:
    
      print("Loading: ", video_file)
      frames = load_video_frames(video_file, json_conf, 0, 0, [], 1)
      
   
   print("Review meteor.", len(frames))
   mf = meteor_json['metframes']
   fn = 1
   fc = 0
   for frame in frames:
      ifn = int(fn)
      sfn = str(fn)
      print("FN:", fn, ifn)
      frame = frames[fc]
      show_frame = frames[fc].copy()
      if fc + 1 < len(frames) - 1:
         nf = fc + 1
         next_frame = frames[nf]
      if sfn in mf: 
         if "mx" in mf[sfn]:
            mx = mf[sfn]['mx'] 
            my = mf[sfn]['my'] 
            est_x = mf[sfn]['est_x'] 
            est_y = mf[sfn]['est_y'] 
            cv2.circle(show_frame,(mx,my), 10, (255,0,0), 1)
            cv2.circle(show_frame,(est_x,est_y), 10, (255,255,0), 1)
            fx1 = est_x
            fy1 = est_y
            fx2 = est_x + (metconf['x_dir_mod'] * 20)
            fy2 = est_y + (metconf['y_dir_mod'] * 20)
            fx1,fy1,fx2,fy2 = bound_points((fx1,fy1,fx2,fy2))

            print("CROP:", fx1,fy1,fx2,fy2)
            cv2.rectangle(show_frame, (int(fx1), int(fy1)), (int(fx2), int(fy2)), (100,100,100), 1)

            img_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            fine_crop = img_gray[fy1:fy2,fx1:fx2]
            fine_crop_show = cv2.cvtColor(fine_crop,cv2.COLOR_GRAY2RGB)
            px1 = 5
            py1 = 5
            px2 = 5 + fine_crop.shape[1]
            py2 = 5 + fine_crop.shape[0]
            show_frame[py1:py2,px1:px2] = fine_crop_show
            cv2.rectangle(show_frame, (int(px1), int(py1)), (int(px2), int(py2)), (100,100,100), 1)

            min_val, max_val, min_loc, (fx,fy)= cv2.minMaxLoc(fine_crop)
            new_x = fx1 + fx
            new_y = fy1 + fy
            print("NEW XY:", new_x, new_y)
            cv2.circle(show_frame,(new_x,new_y), 10, (0,255,0), 1)
 
            ifn = fn
            if fn not in mf:
               ifn = str(fn)
               
            if "bx" not in mf[ifn]:
               mf[ifn]['bx'] = new_x
               mf[ifn]['by'] = new_y
            else:
               bx = mf[ifn]['bx']
               by = mf[ifn]['by']
               cv2.circle(show_frame,(bx,by), 5, (0,0,255), 1)


      if show == 1:
         cv2.imshow('pepe', show_frame)
         if ifn in mf:
            cv2.waitKey(70)
         else:
            cv2.waitKey(50)
      fn = fn + 1
      fc = fc + 1
   meteor_json['metframes'] = mf 

   # test the acl_reduction with the b_key 
   key_field = "b"
   meteor_json['metconf']['acl_poly'] = .5
   meteor_json['metconf']['acl_med_seg_len'] = 5
   b_result,this_poly = test_acl_res(meteor_json,frames,key_field)
   b_acl_res = b_result['fun']
   key_field = "m"
   meteor_json['metconf']['acl_poly'] = .5
   meteor_json['metconf']['acl_med_seg_len'] = 5
   m_result, this_poly = test_acl_res(meteor_json,frames,key_field)
   m_acl_res = m_result['fun']


   if float(b_acl_res) < float(m_acl_res):
      best_key_field = "b"
      key_x = "bx"
      key_y = "by"
   else:
      best_key_field = "m"
      key_x = "mx"
      key_y = "my"

   for fn in mf:
      print("FN HD:", fn, key_x, key_y) 
      mf[fn]['hd_x'] = mf[fn][key_x]
      mf[fn]['hd_y'] = mf[fn][key_y]

   key_field = "hd_"
   hd_result,poly = test_acl_res(meteor_json,frames,key_field)
   hd_acl_res = hd_result['fun']

   print("B ACL RES IS : ", b_acl_res)
   print("M ACL RES IS : ", m_acl_res)
   print("HD ACL RES IS : ", hd_acl_res)
   print("BEST KEY FIELD: ", best_key_field, key_x, key_y)
   meteor_json['metconf']['b_acl_res'] = b_acl_res
   meteor_json['metconf']['m_acl_res'] = m_acl_res
   meteor_json['metconf']['hd_acl_res'] = hd_acl_res
   meteor_json['metframes'] = mf

   metconf['acl_med_seg_len'] = float(metconf['med_seg_len'] + poly[0])
   metconf['med_seg_len'] = float(metconf['med_seg_len'] + poly[0])
   metconf['acl_poly'] = poly[1]
   metconf['acl_res'] = hd_result['fun']

   meteor_json['metconf'] = metconf
   metconf = update_metconf(meteor_json)
   meteor_json['metconf'] = metconf



   avg_res,metframes = reduce_acl(this_poly, meteor_json['metframes'],meteor_json['metconf'],frames, 1,1, key_field)
   meteor_json['metframes'] = metframes
   meteor_json['metconf']['hd_acl_res'] = avg_res 

   save_json_file(meteor_json_file, meteor_json)
   
   # final review / step through   
   fn = 1
   for frame in frames:
      ifn = int(fn)
      sfn = str(fn)
      print("FN:", fn, ifn)
      show_image= frame.copy()
      if sfn in metframes:
         hd_x = metframes[sfn]['hd_x']
         hd_y = metframes[sfn]['hd_y']
         est_x = metframes[sfn]['est_x']
         est_y = metframes[sfn]['est_y']
         cv2.circle(show_image,(est_x,est_y), 10, (0,255,255), 1)
         cv2.circle(show_image,(hd_x,hd_y), 10, (0,0,255), 1)
         if show == 1:
            cv2.imshow('pepe', show_image)
            cv2.waitKey(70)
      fn = fn + 1


def test_acl_res(meteor_json,frames,key_field):
   metconf = meteor_json['metconf']

   metconf = update_metconf(meteor_json)
   meteor_json['metconf'] = metconf
   this_poly = np.zeros(shape=(2,), dtype=np.float64)
   #if "acl_poly" in metconf:
   #   this_poly[0] = np.float64(0)
   #   this_poly[1] = np.float64(metconf['acl_poly'])
   #else:
   #   print("NO ACL POLY!" )

   avg_res = reduce_acl(this_poly, meteor_json['metframes'],meteor_json['metconf'],frames, 0,1, key_field)

   avg_res = scipy.optimize.minimize(reduce_acl, this_poly, args=( meteor_json['metframes'], meteor_json['metconf'],frames,0,1,key_field), method='Nelder-Mead')

   this_poly = np.zeros(shape=(2,), dtype=np.float64)
   if "acl_poly" in metconf:
      this_poly[0] = np.float64(0)
      this_poly[1] = np.float64(metconf['acl_poly'])
   else:
      print("NO POLY!", metconf)

   
   return(avg_res, this_poly)
      
def bound_points(pts):
   x1,y1,x2,y2 = pts
   if x1 < 0:
      x1 = 0 
   if x2 < 0:
      x2 = 0 
   if x1 > 1919:
      x1 = 1919 
   if x2 > 1919:
      x2 = 1919 
   if y1 < 0:
      y1 = 0 
   if y1 > 1079:
      y1 = 1079 
   if y2 < 0:
      y2 = 0 
   if y2 > 1079:
      y2 = 1079 
 
   bxs = [x1,x2]
   bys = [y1,y2]
   bxs.sort()
   bys.sort()

   return(bxs[0],bys[0],bxs[1],bys[1])
       

def post_load_mj(meteor_json):
   mf = meteor_json['metframes']
   new_mf = {}
   for fn in mf:
      print(fn)
      ifn = int(fn)
      new_mf[ifn] = mf[fn]
   meteor_json['metframes'] = new_mf
   return(meteor_json)

def make_reduce_files(meteor_json, meteor_json_filename, json_conf):
   print("REDUCE FILES")
   video_filename = meteor_json_filename.replace(".json", ".mp4")
   stack_filename = meteor_json_filename.replace(".json", "-stacked.png")
   reduce_filename = meteor_json_filename.replace(".json", "-reduced.json")

   video_filename = video_filename.replace("meteor_archive", "meteors")
   stack_filename = video_filename.replace("meteor_archive", "meteors")
   reduce_filename = video_filename.replace("meteor_archive", "meteors")

   hd_datetime, hd_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(video_filename)

   meteor_json['api_key'] = json_conf['site']['api_key']
   meteor_json['station_name'] = json_conf['site']['ams_id']
   meteor_json['device_name'] = hd_cam 

   meteor_json['sd_video_file'] = video_filename 
   meteor_json['hd_video_file'] = video_filename 
   meteor_json['hd_crop_file'] = video_filename 
   meteor_json['hd_file'] = video_filename 
   meteor_json['hd_trim'] = video_filename 
   meteor_json['sd_stack'] = stack_filename 
   meteor_json['hd_stack'] = stack_filename 
   meteor_json['reduce_stack'] = stack_filename 
   meteor_json['reduced_video'] = video_filename
   if "HD" in meteor_json_filename:
      meteor_json['vf_type'] = "HD" 
   else:
      meteor_json['vf_type'] = "SD" 
   meteor_json['event_start_time'] = hd_y + "-" + hd_m + "-" + hd_d + " " + hd_h + ":" + hd_M + ":" + hd_s
   meteor_json['event_duration'] = len(meteor_json['metframes'])/25
   meteor_json['peak_magnitude'] = 0

   
   mfd, metframes,metconf = metframes_to_mfd(meteor_json['metframes'], meteor_json['metconf'], meteor_json_filename,json_conf)
   meteor_json['meteor_frame_data'] = mfd
   meteor_json['metframes'] = metframes
   meteor_json['metconf'] = metconf 
   meteor_json['start_az'] = mfd[0][7]
   meteor_json['start_el'] = mfd[0][8]
   meteor_json['start_ra'] = mfd[0][9]
   meteor_json['start_dec'] = mfd[0][10]

   meteor_json['end_az'] = mfd[-1][7]
   meteor_json['end_el'] = mfd[-1][8]
   meteor_json['end_ra'] = mfd[-1][9]
   meteor_json['end_dec'] = mfd[-1][10]
   return(meteor_json) 

def smooth_points_new(meteor_json, frames ):
   img_h, img_w = frames[0].shape[0], frames[0].shape[1] 
   metframes = meteor_json['metframes']
   metconf = meteor_json['metconf']

   for fn in metframes:
      #print (fn, metframes[fn]['mx'], metframes[fn]['my'], metframes[fn]['obj_cnts'])
      oxs = []
      oys = []
      ows = []
      ohs = []
      cnt_maxpx_agree = 0
      # Hanle Non CNT Detections...
      if "obj_cnts" in metframes[fn]:
         for obj in metframes[fn]['obj_cnts']:
            oid, ox, oy, ow, oh = obj
            ocx = int(ox + (ow/2))
            ocy = int(oy + (oh/2))
            oxs.append(ocy)
            oys.append(ocy)
            ows.append(ow)
            ohs.append(oh)

            # check distance from the object and brightest pixel
            odist = calc_dist((ocx,ocy), (metframes[fn]['mx'], metframes[fn]['my']))
            if odist < 5:
               cnt_maxpx_agree = 1


      if cnt_maxpx_agree == 1:
         metframes[fn]['hd_x'] = metframes[fn]['mx']
         metframes[fn]['hd_y'] = metframes[fn]['my']
      else:
         if len(oxs) > 1:
            metframes[fn]['hd_x'] = int(np.mean(oxs))
            metframes[fn]['hd_y'] = int(np.mean(oys))
         else:
            metframes[fn]['hd_x'] = metframes[fn]['mx']
            metframes[fn]['hd_y'] = metframes[fn]['my']
            metframes[fn]['sd_x'] = metframes[fn]['mx']
            metframes[fn]['sd_y'] = metframes[fn]['my']
            metframes[fn]['sd_cx'] = metframes[fn]['mx']
            metframes[fn]['sd_cy'] = metframes[fn]['my']
            metframes[fn]['sd_w'] = 10 
            metframes[fn]['sd_h'] = 10
      if len(oxs) > 1:
         metframes[fn]['w'] = int(np.mean(ows))
         metframes[fn]['h'] = int(np.mean(ohs))
      else:
         metframes[fn]['w'] = 10 
         metframes[fn]['h'] = 10 
      metframes[fn]['max_px'] = metframes[fn]['max_val'] 
      if meteor_json['hd'] == 0:
         metframes[fn]['hd_x'] = int(metframes[fn]['hd_x'] * meteor_json['hdm_x'])
         metframes[fn]['hd_y'] = int(metframes[fn]['hd_y'] * meteor_json['hdm_y'])
         
      
   meteor_json['metframes'] = metframes 
   meteor_json['metconf'] = metconf
   return(meteor_json)


def smooth_points(meteor_json, frames):
   img_h, img_w = frames[0].shape[0], frames[0].shape[1] 
   metframes = meteor_json['metframes']
   metconf = meteor_json['metconf']

   for fn in metframes:
      print (fn, metframes[fn]['mx'], metframes[fn]['my'], metframes[fn]['obj_cnts'])



   first_fn = None
   first_x = None
   first_y = None
   last_fn = None
   last_x = None
   last_y = None

   mxs = []
   mys = []
   fixsegs = []
   for fn in metframes:
      mx = metframes[fn]['mx'] 
      my = metframes[fn]['my'] 
      mxs.append(mx)
      mys.append(my)

      if first_fn is None:
         first_fn = fn
         first_x = mx 
         first_y = my
      if "x1" not in metframes[fn]:
         x1,y1,x2,y2 = bound_cnt(mx,my,img_w,img_h,100)
         print("FRAME ", fn, "MISSING X1 VARS", mx, my ) 

         metframes[fn]['x1']  = x1
         metframes[fn]['y1']  = y1
         metframes[fn]['x2']  = x2
         metframes[fn]['y2']  = y2
      else:
         print(fn, mx, my )
      if "last_seg_dist" in metframes[fn]:
         print("Last Seg:", metframes[fn]['last_seg_dist'])
         fixsegs.append(metframes[fn]['last_seg_dist']) 
      else:
         if fn == first_fn:
            next_fn = str(int(fn) + 1)
            if next_fn in metframes:
               nx = metframes[next_fn]['mx'] 
               ny = metframes[next_fn]['my'] 
               last_seg_dist = calc_dist((mx,my), (nx,ny))
               metframes[fn]['last_seg_dist'] = last_seg_dist
               fixsegs.append(last_seg_dist) 

   min_mx = min(mxs)
   min_my = min(mys)
   max_mx = max(mxs)
   max_my = max(mys)

   avg_seg_dist = np.median(fixsegs)

   # fix any frames where the seg_dist is > 30 px
   last_x = None
   first_x = None
   fc = 0
   img_h, img_w = frames[0].shape[0], frames[0].shape[1]

   for fn in metframes:
      ifn = int(fn)
      pfn = ifn - 2 
      if pfn > 0:
         last_frame = frames[pfn]
      
      mx = metframes[fn]['mx']
      my = metframes[fn]['my']
      frame = frames[ifn].copy()
      frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
      last_frame = cv2.cvtColor(last_frame, cv2.COLOR_BGR2GRAY)
      subframe = cv2.subtract(frame,last_frame)
      if first_x is None:
         first_x = mx
         first_y = my
      if "last_seg_dist" in metframes[fn]:
         print("TRY TO FIX Last Seg:", metframes[fn]['last_seg_dist'], avg_seg_dist)
         last_seg_dist = float(metframes[fn]['last_seg_dist'])
         if last_seg_dist > avg_seg_dist * 2.5:
            print("FIX BAD POINT!")
            if last_x is not None:
               fx1,fy1,fx2,fy2 = bound_cnt(last_x+ (metconf['x_dir_mod'] * 5),(last_y + metconf['y_dir_mod'] * 5),img_w,img_h,5)
               ifn = int(fn)
               crop_img = frame[fy1:fy2,fx1:fx2]
               avg_val = np.mean(crop_img)
               min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(crop_img)
               mx = fx1 + mx
               my = fy1 + my

               #metframes[fn]['mx'] = mx
               #metframes[fn]['my'] = my
               print("FIXED FRAME: ", fn, mx, my)
               
      if show == 1:
         cv2.imshow('pepe', subframe)
         cv2.waitKey(70)
      last_x = mx
      last_y = my
      fc = fc + 1 


   crop_box = [min_mx, min_my, max_mx, max_my]
   meteor_json['crop_box'] = crop_box
   for fn in meteor_json['metframes']:
      mx = metframes[fn]['mx'] 
      my = metframes[fn]['my'] 
      last_seg = metframes[fn]['last_seg_dist']
      x1 = metframes[fn]['x1']
      y1 = metframes[fn]['y1']
      x2 = metframes[fn]['x2'] 
      y2 = metframes[fn]['y2']  
      ifn = int(fn)
      show_image = frames[ifn].copy()
      cv2.circle(show_image,(mx,my), 10, (255), 1)
      print("CROP BOX:", crop_box)

      hdm_x = 1920 / 1280
      hdm_y = 1080 / 720
     
      disp_image = cv2.resize(show_image, (1280,720))
      #crop_img = show_image[min_my:max_my,min_mx:max_mx]
      crop_img = show_image[y1:y2,x1:x2]
      print(crop_img.shape)
      dx1 = 5
      dy1 = 5
      dx2 = 5 + crop_img.shape[1]
      dy2 = 5 + crop_img.shape[0]

      if crop_img.shape[0] > 0 and crop_img.shape[1] > 0:

         disp_image[dy1:dy2,dx1:dx2] = crop_img
         if show == 1:
            cv2.rectangle(disp_image, (int(dx1), int(dy1)), (int(dx2), int(dy2)), (100,100,100), 1)
            cv2.rectangle(disp_image, (int(min_mx/hdm_x), int(min_my/hdm_y)), (int(max_mx/hdm_x), int(max_my/hdm_y)), (100,100,100), 1)
            cv2.imshow('pepe', disp_image)
            cv2.waitKey(70)
      else:
         print("BAD CROP:", fn, y1,y2,x1,x2)
      print(fn, mx, my, last_seg)

   meteor_json['metframes'] = metframes 
   metconf = meteor_json['metconf']

   metconf = update_metconf(meteor_json)
   meteor_json['metconf'] = metconf
   this_poly = np.zeros(shape=(2,), dtype=np.float64)
   if "acl_poly" in metconf:
      this_poly[0] = np.float64(0)
      this_poly[1] = np.float64(metconf['acl_poly'])
   else:
      print("NO POLY!", metconf)

   avg_res = reduce_acl(this_poly, meteor_json['metframes'],meteor_json['metconf'],frames, 0,1)
   print("AVG RES:", avg_res)
   print("POLY:", this_poly)
   print("ACL RES:", avg_res)
   if "acl_med_seg_len" in metconf:
      print("MED SEG LEN:", metconf['acl_med_seg_len'] )
   else:
      print("MED SEG LEN:", metconf['med_seg_len'] )

   if 'acl_poly' in metconf:
      this_poly[0] = 0
      this_poly[1] = np.float64(metconf['acl_poly'])
  
   else:
      this_poly[0] = -1
      this_poly[1] = -.5

   res = scipy.optimize.minimize(reduce_acl, this_poly, args=( metframes, metconf,frames,0,1), method='Nelder-Mead')
   poly = res['x']
   fun = res['fun']
   metconf['acl_med_seg_len'] = float(metconf['med_seg_len'] + poly[0])
   metconf['med_seg_len'] = float(metconf['med_seg_len'] + poly[0])
   metconf['acl_poly'] = poly[1]
   metconf['acl_res'] = float(fun)
   print(res)
   this_poly[0] = 0
   this_poly[1] = poly[1] 

   meteor_json['metconf'] = metconf

   this_poly[0] = 0
   avg_res,metframes = reduce_acl(this_poly, meteor_json['metframes'],meteor_json['metconf'],frames, 1,1)
   meteor_json['metframes'] = metframes
   print("AVG RES:", avg_res)
   print("POLY:", this_poly)
   print("ACL RES:", avg_res)
   print("MED SEG LEN:", metconf['med_seg_len'] )
   meteor_json = update_frame_est(meteor_json, frames)
   return(meteor_json)

def update_frame_est(meteor_json, frames):
   hdm_x = 2.7272
   hdm_y = 1.875
   first_x = None
   last_x = None
   img_h, img_w = frames[0].shape[0], frames[0].shape[1]
   metframes = meteor_json['metframes']
   metconf = meteor_json['metconf']
   fcc = 0
   for fn in metframes:
      mx = metframes[fn]['mx']
      my = metframes[fn]['my']
      if first_x is None:
         first_x = mx
         first_y = my
         est_x = int( metconf['fx'] + (metconf['x_dir_mod'] * (metconf['acl_med_seg_len']*fcc)) + (metconf['acl_poly'] * (fcc*fcc)) )
         est_y = int((metconf['m']*est_x)+metconf['b'])

         #fx1,fy1,fx2,fy2 = bound_cnt(last_x,last_y,img_w,img_h,20)
         fx1 = est_x
         fy1 = est_y
         fx2 = est_x + (metconf['x_dir_mod'] * 20)
         fy2 = est_y + (metconf['y_dir_mod'] * 20)
         ifn = int(fn)
         frame = frames[ifn].copy()
         frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
         crop_img = frame[fy1:fy2,fx1:fx2]
         avg_val = np.mean(crop_img)
         min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(crop_img)
         if crop_img.shape[0] > 0 and crop_img.shape[1] > 0:
            cv2.imshow('pepe', crop_img)
            cv2.waitKey(70)
         print("ESTXY:", mx,my,est_x,est_y)
         metframes[fn]['est_x'] = est_x
         metframes[fn]['est_y'] = est_y
         metframes[fn]['mx'] = fx1 + mx 
         metframes[fn]['my'] = fy1 + my 
         metframes[fn]['acl_res'] = calc_dist((est_x,est_y),(mx,my))

      last_x = mx
      last_y = my
      fcc = fcc + 1
   meteor_json['metframes'] = metframes
   return(meteor_json)


def update_metconf(meteor_json):
   mxs = []
   mys = []
   segs = []
   if "metconf" not in meteor_json:
      print(meteor_json)
      metconf = {}
   else:
      metconf = meteor_json['metconf']
   mf = meteor_json['metframes']
   for fn in mf:
      mxs.append(mf[fn]['mx'])    
      mys.append(mf[fn]['my'])    
      if "last_seg_dist" in mf[fn]:
         segs.append(mf[fn]['last_seg_dist'])

   metconf['mxs'] = mxs
   metconf['mys'] = mys
   if "acl_med_seg_len" in metconf:
      metconf['med_seg_len'] = metconf['acl_med_seg_len']
   else:
      metconf['med_seg_len'] = float(np.median(segs)) 
   good_xs = []
   good_ys = []
   for fn in mf:
      mx = mf[fn]['mx']    
      my = mf[fn]['my']
      if "last_seg_dist" in mf[fn]:
         last_seg_dist = mf[fn]['last_seg_dist']
         if last_seg_dist < metconf['med_seg_len'] * 2.5:
            good_xs.append(mx)
            good_ys.append(my)


   metconf['m'], metconf['b'] = best_fit_slope_and_intercept(good_xs,good_ys)

   dir_x = mxs[0] - mxs[-1] 
   dir_y = mys[0] - mys[-1] 
   if dir_x < 0:
      x_dir_mod = 1
   else:
      x_dir_mod = -1
   if dir_y < 0:
      y_dir_mod = 1
   else:
      y_dir_mod = -1
   metconf['x_dir_mod'] = x_dir_mod
   metconf['y_dir_mod'] = y_dir_mod
   metconf['fx'] = mxs[0] 
   metconf['fy'] = mys[0] 

   return(metconf)

def reduce_metframes(meteor_json, meteor_json_filename, cal_params):
   metframes = meteor_json['metframes']
   metconf = meteor_json['metconf']
   azs = []
   els = []
   ras = []
   decs = []
   for fn in metframes:
      print(fn, metframes[fn])
      if "hd_x" in metframes[fn]:
         hd_x = metframes[fn]['hd_x']
         hd_y = metframes[fn]['hd_y']
      else:
         hd_x = metframes[fn]['mx']
         hd_y = metframes[fn]['my']
      nx, ny, ra ,dec , az, el= XYtoRADec(hd_x,hd_y,meteor_json['metconf']['video_data_file'],meteor_json['cal_params'],json_conf)
      metframes[fn]['ra'] = ra
      metframes[fn]['dec'] = dec
      metframes[fn]['az'] = az
      metframes[fn]['el'] = el
      azs.append(az)
      els.append(el)
      ras.append(ra)
      decs.append(dec)

   metconf['azs'] = azs
   metconf['els'] = els 
   metconf['ras'] = ras
   metconf['decs'] = decs  
   meteor_json['metconf'] = metconf
   meteor_json['metframes'] = metframes
   print("DONE REDUCE")
   return(meteor_json)

def setup_calib(video_data, image):
   print("Reduce Points.")
   # check if calparams exists in video data file 
   if "cal_params" in video_data:
      cal_params = video_data['cal_params']
      print("Usinging the existing cal params.")
      #exit()
   else:
      # find the best cal params file
      print("FIND BEST CAL FILE FOR THIS METEOR")
      video_data_file = video_data['video_data_file']
      poss = get_active_cal_file(video_data_file)
      cal_params_file = poss[0][0]
      cal_params = load_json_file(cal_params_file)
      video_data['cal_params_file'] = cal_params_file

      print(cal_params)
      #exit()
   org_x_poly = cal_params['x_poly']
   org_y_poly = cal_params['y_poly']

   center_az = cal_params['center_az']
   center_el = cal_params['center_el']
   cal_params['orig_center_az'] = center_az
   cal_params['orig_center_el'] = center_el
   rah,dech = AzEltoRADec(center_az,center_el,video_data['video_data_file'],cal_params,json_conf)
   rah = str(rah).replace(":", " ")
   dech = str(dech).replace(":", " ")
   ra_center,dec_center = HMS2deg(str(rah),str(dech))
   cal_params['ra_center'] = ra_center
   cal_params['dec_center'] = dec_center

   new_cal_params = {}
   new_cal_params['device_lat'] = json_conf['site']['device_lat']
   new_cal_params['device_lng'] = json_conf['site']['device_lng']
   new_cal_params['device_alt'] = json_conf['site']['device_alt']
   new_cal_params['center_az'] = cal_params['center_az']
   new_cal_params['center_el'] = cal_params['center_el']
   new_cal_params['ra_center'] = cal_params['ra_center']
   new_cal_params['dec_center'] = cal_params['dec_center']
   new_cal_params['position_angle'] = cal_params['position_angle']
   new_cal_params['pixscale'] = cal_params['pixscale']
   new_cal_params['orig_pixscale'] = cal_params['pixscale']
   new_cal_params['orig_center_az'] = cal_params['orig_center_az']
   new_cal_params['orig_center_el'] = cal_params['orig_center_el']
   new_cal_params['imagew'] = cal_params['imagew']
   new_cal_params['imageh'] = cal_params['imageh']
   new_cal_params['x_poly'] = cal_params['x_poly']
   new_cal_params['y_poly'] = cal_params['y_poly']
   new_cal_params['x_poly_fwd'] = cal_params['x_poly_fwd']
   new_cal_params['y_poly_fwd'] = cal_params['y_poly_fwd']
   if "cfit_tries" in cal_params:
      new_cal_params['cfit_tries'] = cal_params['cfit_tries']
   cal_params = new_cal_params

   video_data['cal_params'] = cal_params


   print("CAL PARAMS FOUND!", video_data['cal_params_file'])

   image = mask_frame(image, [], video_data['masks'], 10)
   cat_img_stars, avg_res = find_cat_stars_from_points(video_data, image) 
 
   cal_params['cat_image_stars'] = cat_img_stars
   cal_params['total_res_px'] = avg_res
   cal_params['total_res_deg'] = 9999

   video_data['cal_params'] = cal_params
   this_poly = np.zeros(shape=(4,), dtype=np.float64)
   
   print("CAT:", len(cal_params['cat_image_stars']))
   cal_params['x_poly'] = org_x_poly
   cal_params['y_poly'] = org_y_poly
   if "cfit_tries" in cal_params:
      cfit_tries = int(cal_params['cfit_tries'])
   else:
      cfit_tries = 0
   
   do_cfit = 0 
   if cfit_tries < 5 and len(cal_params['cat_image_stars']) >= 7 and do_cfit == 1:
      start_res = reduce_fov_pos(this_poly, cal_params,video_data['video_data_file'],image,json_conf, cal_params['cat_image_stars'],1,1)
 
      res = scipy.optimize.minimize(reduce_fov_pos, this_poly, args=( cal_params,video_data['video_data_file'],image,json_conf, cal_params['cat_image_stars'],1,1), method='Nelder-Mead')
      fov_pos_poly = res['x']

      cal_params['center_az'] = float(cal_params['orig_center_az']) + float(fov_pos_poly[0] )
      cal_params['center_el'] = float(cal_params['orig_center_el']) + float(fov_pos_poly[1] )
      cal_params['position_angle'] = float(cal_params['position_angle']) + float(fov_pos_poly[2] )

      cfit_tries = cfit_tries + 1
      cal_params['cfit_tries'] = cfit_tries 

   video_data['cal_params'] = cal_params 

    
   return(video_data)


def find_cat_stars_from_points(video_data, show_image = None):
   show_image = cv2.cvtColor(show_image, cv2.COLOR_BGR2GRAY)
   cal_params_file = video_data['cal_params_file']
   in_cal_params = video_data['cal_params']
   fov_poly = 0
   pos_poly = 0
   x_poly = in_cal_params['x_poly']
   y_poly = in_cal_params['y_poly']
   no_poly_cal_params = in_cal_params

   cat_stars = get_catalog_stars(fov_poly, pos_poly, in_cal_params,"x",x_poly,y_poly,min=0)
   cal_params = video_data['cal_params']
   #x_poly = np.zeros(shape=(15,), dtype=np.float64)
   #cal_params['x_poly'] = x_poly.tolist()
   #y_poly = np.zeros(shape=(15,), dtype=np.float64)
   #cal_params['y_poly'] = y_poly.tolist()

   img_h, img_w = show_image.shape
   # try to find some extra stars
   img_points = []
   for cat_star in cat_stars:
      (name,mag,ra,dec,new_cat_x,new_cat_y) = cat_star
   
      x1,y1,x2,y2 = bound_cnt(new_cat_x,new_cat_y,img_w,img_h,10)
      print("CROP:", x1,y1,x2,y2)
      crop_img = show_image[y1:y2,x1:x2]
      avg_val = np.mean(crop_img)
      min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(crop_img)
      px_diff = max_val - avg_val
      print(max_val, avg_val, px_diff)
      if px_diff > 10:
         ix = x1 + mx
         iy = y1 + my
         video_data['mask_points'].append((ix, iy))
         img_points.append((ix, iy))



   new_res = []
   new_paired_stars = []
   used = {}
   #video_data['mask_points'] = remove_dupe_img_stars(video_data['mask_points'])
   video_data['mask_points'] = img_points

   #cv2.rectangle(show_image, (int(x1), int(y1)), (int(x2), int(y2)), (100,100,100), 1)

   # Load NO poly cat stars
   x_poly = np.zeros(shape=(15,), dtype=np.float64)
   no_poly_cal_params['x_poly'] = x_poly.tolist()
   y_poly = np.zeros(shape=(15,), dtype=np.float64)
   no_poly_cal_params['y_poly'] = y_poly.tolist()

   np_cat_stars = get_catalog_stars(fov_poly, pos_poly, no_poly_cal_params,"x",x_poly,y_poly,min=0)
   no_poly_cat_stars = {}
   for cat_star in np_cat_stars:
      (name,mag,ra,dec,new_cat_x,new_cat_y) = cat_star
      key = str(ra) + ":" + str(dec)
      no_poly_cat_stars[key] = cat_star
      #cv2.rectangle(show_image, (int(new_cat_x+5), int(new_cat_y+5)), (int(new_cat_x-5), int(new_cat_y-5)), (0,255,255), 1)

   cat_image_stars = []
   total_res = 0
   for ix,iy in video_data['mask_points']:
   
      status, star_info = lookup_star_in_cat(ix,iy,cat_stars,no_poly_cat_stars, star_dist=20)
      if status == 1:
         (ix,iy,px_dist,iname,mag,ra,dec,new_cat_x,new_cat_y) = star_info
         #(name,mag,ra,dec,new_cat_x,new_cat_y) = cat_star
         iname = iname.decode("utf-8")
         new_cat_x,new_cat_y = int(new_cat_x), int(new_cat_y)
         star_edge = test_star_edge(ix,iy,show_image)
         if px_dist < 10 and star_edge == 1: 
            total_res = total_res + px_dist
            cat_image_stars.append((iname,mag,ra,dec,new_cat_x,new_cat_y,ix,iy,px_dist,cal_params_file))

     

      print("STARS:", status, star_info)
      if show_image is not None:
         ix, iy = int(ix), int(iy)
         cv2.circle(show_image,(ix,iy), 10, (255), 1)
         #cv2.circle(show_image,(star_info[0],star_info[1]), 10, (128,128), 1)
         sx = star_info[7]
         sy = star_info[8]
         print("STARS:", status, star_info, ix, iy, sx, sy )
         res = calc_dist((ix,iy), (sx,sy))
         if res < 5:
            cv2.rectangle(show_image, (int(sx+5), int(sy+5)), (int(sx-5), int(sy-5)), (255,255,255), 1)
   real_cat_image_stars = []
   for name,mag,ra,dec,new_cat_x,new_cat_y,ix,iy,px_dist,cal_params_file in cat_image_stars:
      real_cat_image_stars.append(( name,mag,ra,dec,0,0,px_dist,int(new_cat_x),int(new_cat_y),0,0,int(new_cat_x),int(new_cat_y),int(ix),int(iy),px_dist))

  
   if len(cat_image_stars) > 0:
      avg_res = float(total_res / len(cat_image_stars))
   else:
      avg_res =9999
   if show == 1: 
      cv2.imshow('pepe', show_image)
      cv2.waitKey(1)
   return(real_cat_image_stars, avg_res)

def test_star_edge(ix,iy,image):
   star_edge = 1 
   tx = ix + 20
   ty = iy
   try:
      if tx > 1919 or image[ty,tx] == 0 :
         star_edge = 0
      tx = ix - 20
      ty = iy
      if tx < 0 or image[ty,tx] == 0:
         star_edge = 0

      tx = ix 
      ty = iy + 20
      if ty > 1079: 
         star_edge = 0
      elif image[ty,tx] == 0:
         star_edge = 0
      tx = ix 
      ty = iy - 20
      if ty < 0 or image[ty,tx] == 0:
         star_edge = 0
   except:
      star_edge = 0
   return(star_edge)


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
   if start_frame - 5 > 0:
      first_frame = start_frame - 5
      start_buff = 5
   if end_frame + 5 <= total_frames-1:
      last_frame = end_frame + 5
      end_buff = 5


   if start_frame - 10 > 0:
      first_frame = start_frame - 10
      start_buff = 10
   if end_frame + 10 <= total_frames-1:
      last_frame = end_frame + 10
      end_buff = 10
   if start_frame - 25 > 0:
      first_frame = start_frame - 25
      start_buff = 25 
   if end_frame + 25 <= total_frames:
      last_frame = end_frame + 25
      end_buff = 25 
   fns = []
   for i in range (first_frame , last_frame ):
      fns.append(i) 

   return(fns, start_buff, end_buff)


def make_meteor_video_filename(video_file, start, hd):
   hd_datetime, hd_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(video_file)
   vid_fn = video_file.split("/")[-1]
   vid_dir = video_file.replace(vid_fn, "")

   if "trim" not in video_file:
      orig_trim_num = 0
   else:
      ttt = video_file.split("trim")
 
      if "HD" in ttt[-1]:
         el = ttt[-1].split("-")
         orig_trim_num = int(el[1])
      else:
         orig_trim_num = int(ttt[-1].replace(".mp4", ""))
         #print("SD NOT DONE YET:", orig_trim_num, video_file, ttt[-1])
         #exit()

   new_trim_num = orig_trim_num + start
   trim_seconds = new_trim_num / 25
   orig_trim_seconds = orig_trim_num / 25

   event_start_time = hd_datetime + datetime.timedelta(0,trim_seconds)
   orig_clip_start_time = hd_datetime + datetime.timedelta(0,orig_trim_seconds)

   day = event_start_time.strftime('%Y_%m_%d')
   event_start_time_str = event_start_time.strftime('%Y_%m_%d_%H_%M_%S_%f')[:-3]
   if hd == 1:
      hd_str = "HD"
   else:
      hd_str = "SD"

   meteor_filename = event_start_time_str + "_" + hd_cam + "_" + json_conf['site']['ams_id'] + "_" + hd_str + ".mp4"
   #meteor_dir = "/mnt/ams2/meteor_archive/" + day + "/" 
   meteor_dir = vid_dir 
   if "json" in vid_dir:
      vid_dir = vid_dir.replace(".json", ".mp4")
   if cfe(meteor_dir, 1) == 0:
      os.system("mkdir " + meteor_dir)

   print("METEOR FILENAME IS:", meteor_filename)

   meteor_video_filename = meteor_dir + meteor_filename  
   return(meteor_video_filename, event_start_time )


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
         if fn in frame_data[fn]: 
            frame_data[fn]['cnt_x'] = cnt_x
            frame_data[fn]['cnt_y'] = cnt_y
            frame_data[fn]['cnt_w'] = cnt_w
            frame_data[fn]['cnt_h'] = cnt_h
            cv2.rectangle(image_thresh, (x, y), (x+w, y+h), (128,128,128), 1)
         

         print(my_cnts)

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
   if ".json" in file:
      file = file.replace(".json", ".mp4") 
   run_detect(file,show)
if cmd == 'rv' or cmd == 'review_meteor':
   if cfe(file) == 1:
      if ".mp4" in file:
         video_file = file
         file = file.replace(".mp4", ".json") 
      
      video_file = file.replace(".json", ".mp4")
      review_meteor(file,None, video_file, show)


if cmd == 'qr' or cmd == 'quick_review':
   if cfe(file) == 1:
      if ".mp4" in file:
         video_file = file
         file = file.replace(".mp4", ".json", show) 
      
      video_file = file.replace(".json", ".mp4")
   quick_review(file,None, video_file)


if cmd == 'rm' or cmd == 'remaster':
   pub_file = file.replace(".mp4", "-pub.mp4")

   data = {}
   data['video_file'] = file
   data['json_conf'] = json_conf

   #perseids radiant
   ra = 46
   dec = 59
   json_file = file.replace(".mp4", ".json")
   meteor_data = load_json_file(json_file)
   new_frame = np.zeros((1080,1920),dtype=np.uint8)
   new_frame, rad_x, rad_y = add_radiant(ra,dec,new_frame,json_file, meteor_data,json_conf)
   data['rad_x'] = rad_x
   data['rad_y'] = rad_y
   data['rad_name'] = "Perseids"
   print(data)
   remaster(data )


   #if cfe(pub_file) == 0:
   #   remaster(file, json_conf)
   #else:
   #   print("Skip already done.")


if cmd == 'rj' or cmd == 'reject':
   check_reject(file, json_conf)
if cmd == 'brj' or cmd == 'batch_reject':
   day = sys.argv[2]
   batch_check_reject(day, json_conf)
if cmd == 'bb' or cmd == 'batch_best':
   day = sys.argv[2]
   batch_best(day, json_conf)
if cmd == 'up' or cmd == 'update':
   file = sys.argv[2]
   update(file, json_conf)
if cmd == 'cn' or cmd == 'convert':
   file = sys.argv[2]
   convert_data(file, json_conf)

if cmd == 'cc' or cmd == 'check_conversion':
   check_conversion(json_conf, file)

