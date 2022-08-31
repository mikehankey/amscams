#!/usr/bin/python3

"""

2022 - recalibration script -- fixes / updates calibration

import features / functions
   - get / validate image stars (no catalog)
   - blind solve
   - get catalog stars
   - pair stars (image stars with catalog stars)
   - create lens distorition model from one image
   - create lens distorition model from multiple images
   - apply lens correction model
   - refit / refine fov pointing values (ra/dec/pos/pix)

"""
import datetime
from PIL import ImageFont, ImageDraw, Image, ImageChops
import imutils
import time
import json
import numpy as np
import glob
import cv2
import os, sys
import requests
from photutils import CircularAperture, CircularAnnulus
from photutils.aperture import aperture_photometry
import scipy.optimize
from PIL import ImageFont, ImageDraw, Image, ImageChops
import lib.brightstardata as bsd
from lib.PipeUtil import load_json_file, save_json_file,angularSeparation, calc_dist, convert_filename_to_date_cam , check_running
from lib.PipeAutoCal import distort_xy, insert_calib, minimize_poly_multi_star, view_calib, cat_star_report , update_center_radec, XYtoRADec, draw_star_image, make_lens_model, make_az_grid, make_cal_summary, quality_stars, make_cal_plots, find_stars_with_grid
import sqlite3 
from lib.DEFAULTS import *
from lib.PipeVideo import load_frames_simple
from Classes.MovieMaker import MovieMaker 

tries = 0

running = check_running("recal.py refit_meteor_day")
if running > 2:
   print("ALREADY RUNNING:", running)
   cmd = "echo " + str(running) + " >x"
   os.system(cmd)
   exit()



def refit_summary(log):
   #([cam_id, ff, last_cp['center_az'], last_cp['center_el'], last_cp['ra_center'], last_cp['dec_center'], last_cp['position_angle'], last_cp['pixscale'], len(last_cp['cat_image_stars']), last_cp['total_res_px']])
   cam_stats = {}
   used = {}
   for row in log:
      cam_id, ff, az, el, ra, dec, pos, pxs, star_count, res_px = row
      if ff in used:
         continue
      if cam_id not in cam_stats:
         cam_stats[cam_id] = {}
         cam_stats[cam_id]['files'] = []
         cam_stats[cam_id]['azs'] = []
         cam_stats[cam_id]['els'] = []
         cam_stats[cam_id]['poss'] = []
         cam_stats[cam_id]['pixs'] = []
         cam_stats[cam_id]['stars'] = []
         cam_stats[cam_id]['res'] = []
      cam_stats[cam_id]['files'].append(ff)
      cam_stats[cam_id]['azs'].append(az)
      cam_stats[cam_id]['els'].append(el)
      cam_stats[cam_id]['poss'].append(pos)
      cam_stats[cam_id]['pixs'].append(pxs)
      cam_stats[cam_id]['stars'].append(star_count)
      cam_stats[cam_id]['res'].append(res_px)
      used[ff] = 1

   for cam_id in cam_stats:
      print()
      med_az = np.median(cam_stats[cam_id]['azs'])
      med_el = np.median(cam_stats[cam_id]['els'])
      med_pos = np.median(cam_stats[cam_id]['poss'])
      med_px = np.median(cam_stats[cam_id]['pixs'])
      med_stars = np.median(cam_stats[cam_id]['stars'])
      med_res = np.median(cam_stats[cam_id]['res'])
      print(cam_id, "FILES", "", cam_stats[cam_id]['files'])
      print(cam_id, "AZS", med_az, cam_stats[cam_id]['azs'])
      print(cam_id, "ELS", med_el, cam_stats[cam_id]['els'])
      print(cam_id, "POS", med_pos, cam_stats[cam_id]['poss'])
      print(cam_id, "PX", med_px, cam_stats[cam_id]['pixs'])
      print(cam_id, "STARS", med_stars, cam_stats[cam_id]['stars'])
      print(cam_id, "RES", med_res, cam_stats[cam_id]['res'])
      print()
   return(cam_stats)

def star_track(cam_id, con, cur, json_conf ):
   MM = MovieMaker()
   wild = "/mnt/ams2/HD/*" + cam_id + "*.mp4"
   print(wild)
   hd_files = glob.glob(wild)
   for hdf in hd_files:
      print(hdf)
      MM.make_snap(hdf)
      exit()

def refit_meteor(meteor_file, con, cur, json_conf, mcp = None, last_best_dict = None):
   # meteor_file should end with .json and have no path info
   if "/" in meteor_file:
      meteor_file = meteor_file.split("/")[-1]
   if ".mp4" in meteor_file:
      meteor_file = meteor_file.replace(".mp4", ".json")
   
   (f_datetime, cam_id, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(meteor_file)

   default_cp = get_default_cal_for_file(cam_id, meteor_file, None, con, cur, json_conf)
   print(default_cp)
   
   extra_text = "Refit " +  meteor_file
   if last_best_dict is None:
      last_best_dict = {}

   autocal_dir = "/mnt/ams2/cal/" 
   if mcp is None:
      mcp_file = autocal_dir + "multi_poly-" + station_id + "-" + cam_id + ".info"
      if os.path.exists(mcp_file) == 1:
         mcp = load_json_file(mcp_file)

   day = meteor_file[0:10]
   mdir = "/mnt/ams2/meteors/" + day + "/" 
   fit_img_file = mdir + meteor_file.replace(".json", "-rfit.jpg")
   sd_vid = "/mnt/ams2/meteors/" + day + "/" + meteor_file
   json_file = "/mnt/ams2/meteors/" + day + "/" + meteor_file #.replace(".mp4", ".json")
   orig_res = 999
   if os.path.exists(json_file):
      try:
         mj = load_json_file(json_file)
      except:
         # corrupt mj remake!
         os.system("rm " + json_file)
         os.system("./Process.py fireball " + meteor_file) 
      if "meteor_refit_max" in mj and "cp" in mj:
         print("REFIT MAX DONE!")
         del(mj['meteor_refit_max'])
         #return(mj['cp'])
      else:
         if "meteor_refit_max" in mj:
            del(mj['meteor_refit_max'])
      mj = check_for_nan(json_file, mj)

      # if the CP has not been assigned to the meteor give it the default cal
      if "cp" not in mj:
         cp = default_cp #get_default_cal_for_file(cam_id, meteor_file, None, con, cur, json_conf)
         if cp is None:
            print("CAN'T REFIT!")
            return(None) 
         mj['cp'] = cp
         
      red_file = json_file.replace(".json", "-reduced.json")
      if os.path.exists(red_file):
         red = load_json_file(red_file)
      else:
         red = {}
      print("LOADED:", red_file)
      if "total_res_px" not in mj['cp']:
         # There are no stars so there is no res??
         mj['cp']['total_res_px'] = 999
         mj['cp']['total_res_deg'] = 999

      if mj['cp']['total_res_px'] > 15:
         # res is too high, use the default
         mj['cp'] = default_cp #get_default_cal_for_file(cam_id, meteor_file, None, con, cur, json_conf)
      
         print("USING DEFAULT CP! RES HIGH", mj['cp']['total_res_px'])
         print("OK")

      #if cam_id in last_best_dict : 
      #   if "total_res_px" not in mj['cp']:
      #      mj['cp']['total_res_px'] = 999
      #      mj['cp']['total_res_deg'] = 999

         # NEED TO TEST THIS BETTER. NOT SURE THIS IS WORKING AS DESIRED?
      #   if mj['cp']['total_res_px'] > last_best_dict[cam_id]['total_res_px']:
      #      print("USING LAST BEST CP!?", mj['cp']['total_res_px'], last_best_dict[cam_id]['total_res_px']) 
      #      last_best_dict[cam_id] = update_center_radec(json_file,last_best_dict[cam_id],json_conf)
      #      mj['cp'] = last_best_dict[cam_id]
      #   else:
      #      print("Use the MJ over the last dict default")
      #      print(mj['cp']['total_res_px'] , last_best_dict[cam_id]['total_res_px'])
      #else:
      #   print("Cam not in last dict yet", cam_id, last_best_dict.keys())

   orig_res = mj['cp']['total_res_px']


   print("ORG RES:", orig_res)
   if orig_res > 2:
      mj['cp'] = default_cp

   if "hd_trim" in mj:
      if os.path.exists(mj['hd_trim']) is True:
         frames = load_frames_simple(mj['hd_trim'])
      elif os.path.exists(sd_vid) is True:
         frames = load_frames_simple(sd_vid)
      else:
         print("ERROR NO VIDEO FRAMES!", sd_vid)
         return()
   elif os.path.exists(sd_vid) is True:
      frames = load_frames_simple(sd_vid)
   else:
      print("ERROR NO VIDEO FRAMES!", sd_vid)
      return()

   #print("FILE:", meteor_file)
   #print("FRAMES:", len(frames))

   median_frame = cv2.convertScaleAbs(np.median(np.array(frames[0:10]), axis=0))
   median_frame = cv2.resize(median_frame, (1920,1080))

   #cv2.imshow('pepe', median_frame)
   #cv2.waitKey(30)
   
   if "star_points" not in mj:
      stars = find_stars_with_grid(median_frame)
      mj['star_points'] = stars
      mj['user_stars'] = stars
   else:
      stars = mj['star_points']

   # get a few cal files
   try:
      #print("RANGE DEFAULT CAL")
      range_data = get_cal_range(meteor_file, median_frame, con, cur, json_conf)
   except:
      # couldn't get range data because pic failed???
      #print("RANGE FAILED")
      range_data = []

   #default_cp = mcp
   #default_cp['user_stars'] = stars
   #print(default_cp)
   #print("XPOLY:", default_cp['x_poly'])

   if False:
      best_res = 999
      best_stars = 0
      best_cal = None
      #   something not right here...
      for row_data in range_data:
         show_img = median_frame.copy() 
         rcam_id, rend_dt, rstart_dt, elp, az, el, pos, pxs, res = row_data
         default_cp['center_az'] = az
         default_cp['center_el'] = el
         default_cp['position_angle'] = pos
         default_cp['pixscale'] = pxs
         #for key in default_cp:
         #   print(key, default_cp[key])

         default_cp = update_center_radec(meteor_file,default_cp,json_conf)

         #print("updated ra/dec")
         default_cp['cat_image_stars'], default_cp['user_stars'] = get_image_stars_with_catalog(meteor_file, default_cp, show_img)
         #print("got stars with cat")

         # USE MEDIAN RES!
         if len(default_cp['cat_image_stars']) == 0:
            rez = 9999
         else:
            rez = np.median([row[-2] for row in default_cp['cat_image_stars']])

         default_cp['total_res_px'] = rez 
         if rez < best_res:
            best_res = rez
            best_stars = len(default_cp['cat_image_stars'])
            best_cal = dict(default_cp)
            #print("THIS CAL RES VS BEST RES:", best_stars, rez, best_res)

   if "cat_image_stars" in default_cp:
      for row in default_cp['cat_image_stars']:
         print("CAT", row)
   else:
      print("NO CAT STARS!")
   
   show_frame = median_frame.copy()
   if SHOW == 1:
      cv2.imshow('pepe', show_frame)
      cv2.waitKey(30)
      for star in stars:
         x,y,i = star
         cv2.circle(show_frame, (int(x),int(y)), 15, (128,255,128),1)

   star_img = draw_star_image(median_frame.copy(), mj['cp']['cat_image_stars'],mj['cp'], json_conf, extra_text) 
   print(fit_img_file)
   cv2.imwrite(fit_img_file, star_img, [int(cv2.IMWRITE_JPEG_QUALITY), 70])

   if SHOW == 1 :
      cv2.imshow('pepe', star_img)
      cv2.waitKey(30)


   

   if "cp" in mj:
      cp = mj['cp']
   else:
      cp = None

   if cp is None:
      cp = get_default_cal_for_file(meteor_file, median_frame.copy(), con, cur, json_conf)
      mj['cp'] = cp

   # Try to add more stars if we have less than 25
   if len(cp['cat_image_stars']) < 20:
      #print("METEOR FILE:", meteor_file)
      star_objs, bad_star_objs = find_stars_with_catalog(meteor_file.replace(".mp4", ".json"), con, cur, json_conf,mcp, cp, median_frame) 
      #print("STAR OBJS:", len(star_objs))
      #print("BAD STAR OBJS:", len(bad_star_objs))

      cat_image_stars = []
      user_stars = []

      for star_obj in bad_star_objs:
         x = star_obj['star_x']
         y = star_obj['star_y']
         cnts = star_obj['cnts']
         cv2.circle(show_frame, (int(x),int(y)), 15, (0,0,255),1)

         #print("BAD STAR:", star_obj['reject_reason'], star_obj['pxd'], star_obj['star_name'], star_obj['star_x'], star_obj['star_y'], cnts, star_obj['mag'], star_obj['star_flux'])

      for star_obj in star_objs:
         cat_image_stars.append((star_obj['star_name'],star_obj['mag'],star_obj['ra'],star_obj['dec'],star_obj['img_ra'],star_obj['img_dec'],star_obj['total_res_deg'],star_obj['proj_x'],star_obj['proj_y'],star_obj['img_az'],star_obj['img_el'],star_obj['cat_x'],star_obj['cat_y'],star_obj['star_x'],star_obj['star_y'],star_obj['total_res_px'],star_obj['star_flux']))
         user_stars.append((star_obj['star_x'], star_obj['star_y'], star_obj['star_flux']))
         x = star_obj['star_x']
         y = star_obj['star_y']
         cnts = star_obj['cnts']
         #print("GOOD STAR:", star_obj['pxd'], star_obj['star_name'], star_obj['star_x'], star_obj['star_y'], cnts, star_obj['mag'], star_obj['star_flux'])
         if SHOW == 1:
            cv2.circle(show_frame, (int(x),int(y)), 5, (0,255,0),1)
            cv2.imshow('pepe', show_frame)
            cv2.waitKey(40)
      mj['cp']['cat_image_stars'] = cat_image_stars     
      mj['cp']['user_stars'] = user_stars 


      if SHOW == 1:
         cv2.imshow('pepe', show_frame)
         cv2.waitKey(30)

   # remove really bad cat stars
   if True:
      temp = []
      rez = np.median([row[-2] for row in cp['cat_image_stars']])
      if rez < 1:
         rez = 1

      for row in cp['cat_image_stars']:
         #print(row)
         if row[-2] < rez * 2:
            temp.append(row)
         else:
            print("skip bad res:", row[-2])

      cp['cat_image_stars'] = temp

   if len(mj['cp']['cat_image_stars']) < 5: 
      print("NOT ENOUGH STARS TO CUSTOM FIT. USE DEFAULT CAL!")
      mj['cp'] = default_cp
      mj['cat_image_stars'] = []

      red['cal_params'] = default_cp
      red['cal_params']['cat_image_stars'] = []

      print("DEFAULT CP:", default_cp)

      if "cp" in red:
         del(red['cp'])
      save_json_file(red_file, red)
      print("SAVED RED:", red_file)
   else:
      temp_cp = minimize_fov(meteor_file, mj['cp'], meteor_file,median_frame.copy(),json_conf, False,mcp, "", SHOW)
      if temp_cp['total_res_px'] <= mj['cp']['total_res_px']: 
         mj['cp'] = temp_cp

   new_cat_image_stars = []
   if "cat_image_stars" not in mj['cp']:
      mj['cp']['cat_image_stars'] = []

   for star in mj['cp']['cat_image_stars']:
      (dcname,mag,ra,dec,img_ra,img_dec,match_dist,up_cat_x,up_cat_y,img_az,img_el,up_cat_x,up_cat_y,six,siy,res_px,bp) = star
      new_cat_x, new_cat_y = get_xy_for_ra_dec(mj['cp'], ra, dec)
      res_px = calc_dist((six,siy),(new_cat_x,new_cat_y))
      new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(six,siy,meteor_file,mj['cp'],json_conf)
      match_dist = angularSeparation(ra,dec,img_ra,img_dec)
      real_res_px = res_px
      new_cat_image_stars.append((dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,real_res_px,bp))
   mj['cp']['cat_image_stars'] = new_cat_image_stars

   rez = [row[-2] for row in mj['cp']['cat_image_stars'] ]
   med_rez = np.median(rez) ** 2
   if med_rez < 2:
      med_rez = 2 

   new_cat_image_stars = []
   for star in mj['cp']['cat_image_stars']:
      if star[-2] <= med_rez :
         print("KEEP", star[0], star[-2], med_rez)
         new_cat_image_stars.append(star)
      else:
         print("REJECT", star[0], star[-2], med_rez)

   mj['cp']['cat_image_stars'] = new_cat_image_stars
   # now apply the new cp to the existing points!

   
   if os.path.exists(red_file) is True:
      if "meteor_frame_data" in red:
         red = update_mfd(meteor_file, red, cp)
         print("NEW RED")
   for row in red['meteor_frame_data']:
      print(row)
   if os.path.exists(red_file) is True:
      red['cal_params'] = mj['cp']
      print(red_file, red)
      save_json_file(red_file, red)      
   if "cp" not in mj:
      mj['cp'] = get_default_cal_for_file(cam_id, meteor_file, None, con, cur, json_conf)
      red['cal_params'] = mj['cp']
      save_json_file(red_file, red)      

   save_json_file(json_file, mj)      
   if False:
      if orig_res > mj['cp']['total_res_px']:
         print("SAVED/DONE", orig_res, mj['cp']['total_res_px'])
         save_json_file(json_file, mj)      
      else:
         mj = load_json_file(json_file)      
         mj['meteor_refit_max'] = True
         mj['cp'] = default_cp 
         save_json_file(json_file, mj)      
         if "cp" in mj:
            print("NO SAVE/DONE (orig is better)", orig_res, mj['cp']['total_res_px'])
         else:
            print("PROBLEM no mj/cp")

   return(mj['cp'])

def update_mfd(meteor_file, mjr, cp):

   mjr['meteor_frame_data'] = sorted(mjr['meteor_frame_data'], key=lambda x: (x[1]), reverse=False)
   updated_frame_data = []
   for row in mjr['meteor_frame_data']:
      (dt, fn, x, y, w, h, oint, ra, dec, az, el) = row
      tx, ty, ra ,dec , az, el = XYtoRADec(x,y,meteor_file,mjr['cal_params'],json_conf)
      updated_frame_data.append((dt, int(fn), x, y, w, h, oint, ra, dec, az, el))
   mjr['meteor_frame_data'] = updated_frame_data
   return(mjr)

def check_for_nan(mjf, mj):
   mjrf = mjf.replace(".json", "-reduced.json")
   nan_found = False
   if os.path.exists(mjrf) is True:
      try:
         mjr = load_json_file(mjrf)
      except:
         nan_found = True
         mjr = {}
      if "meteor_frame_data" in mjr:
         for row in mjr['meteor_frame_data']:
            for val in row:
               if type(val) != str:
                  res = np.isnan(val)
                  if res == True:
                     nan_found = True

   if "cp" in mj:
      if mj['cp'] is None:
         del(mj['cp'] )

   if "cp" in mj:
      for field in mj['cp']:
         val = mj['cp'][field]
         if type(val) == float: 
            res = np.isnan(val)
         else:
            res = False
         if res == True:
            nan_found = True

   if nan_found == True:
      os.system("rm " + mjrf)
      del mj['cp']
      save_json_file(mjf, mj)
   return(mj)

def make_photo_credit(json_conf, cam_id=None):
   if json_conf is not None:
      station_id = json_conf['site']['ams_id'] 
      if cam_id is not None:
         station_id += "-" + cam_id
      if "operator_name" in json_conf['site']:
         name = json_conf['site']['operator_name']

      if "operator_country" in json_conf['site']:
         city = json_conf['site']['operator_city']
      if "operator_state" in json_conf['site']:
         state = json_conf['site']['operator_state']
      if "operator_country" in json_conf['site']:
         country = json_conf['site']['operator_country']
      if "US" in country or "United States" in country:
         country = "US"
         photo_credit = station_id + " - " + name + ", " + city + ", " + state + " " + country
      else:
         photo_credit = station_id + " - " + name + ", " + city + ", " + country
   return(photo_credit)

def draw_text_on_image(img, text_data) :
   image = Image.fromarray(img)
   draw = ImageDraw.Draw(image)
   font = ImageFont.truetype("/usr/share/fonts/truetype/DejaVuSans.ttf", 20, encoding="unic" )
   for tx,ty,text in text_data:
      draw.text((tx, ty), str(text), font = font, fill="white")

   return_img = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)
   return(return_img)

def draw_stars_on_image(img, cat_image_stars,cp=None,json_conf=None,extra_text=None,img_w=1920,img_h=1080) :
   photo_credit = ""
   station_id = ""
   name = ""
   city = ""
   state = ""
   country = ""
   hdm_x = img_w / 1920
   hdm_y = img_h / 1080
   #print(cp.keys())
   #print(json_conf.keys())
   if json_conf is not None:
      station_id = json_conf['site']['ams_id']
      if "operator_name" in json_conf['site']:
         name = json_conf['site']['operator_name']

      if "operator_country" in json_conf['site']:
         city = json_conf['site']['operator_city']
      if "operator_state" in json_conf['site']:
         state = json_conf['site']['operator_state']
      if "operator_country" in json_conf['site']:
         country = json_conf['site']['operator_country']
      if "US" in country or "United States" in country:
         country = "US"
         photo_credit = station_id + " - " + name + ", " + city + ", " + state + " " + country
      else:
         photo_credit = station_id + " - " + name + ", " + city + ", " + country
   for star in cat_image_stars:
      if len(star) == 9:
         dcname,mag,ra,dec,new_cat_x,new_cat_y,six,siy,cat_dist = star
      else:
         dcname,mag,ra,dec,img_ra,img_dec,match_dist,org_x,org_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int = star
      if 0 <= six <= 1920 and 0 <= siy <= 1080:
         img[int(siy*hdm_y),int(six*hdm_x)] = [0,0,255]

   image = Image.fromarray(img)
   draw = ImageDraw.Draw(image)
   #font = ImageFont.truetype("/usr/share/fonts/truetype/freefont/FreeSans.ttf", 20, encoding="unic" )
   font = ImageFont.truetype("/usr/share/fonts/truetype/DejaVuSans.ttf", 20, encoding="unic" )
   org_x = None
   org_y = None
   for star in cat_image_stars:
      if len(star) == 9:
         dcname,mag,ra,dec,new_cat_x,new_cat_y,six,siy,cat_dist = star
      else:
         dcname,mag,ra,dec,img_ra,img_dec,match_dist,org_x,org_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int = star


      match_dist = calc_dist((new_cat_x,new_cat_y), (six,siy))
      cat_dist = match_dist
      if cat_dist <= .5:
         color = "#add900"
      if .5 < cat_dist <= 1:
         color = "#708c00"
      if 1 < cat_dist <= 2:
         color = "#0000FF"
      if 2 < cat_dist <= 3:
         color = "#FF00FF"
      if 3 < cat_dist <= 4:
         color = "#FF0000"
      if cat_dist > 4:
         color = "#ff0000"



      dist = calc_dist((six,siy), (new_cat_x,new_cat_y))
     
      six = int(six * hdm_x)
      siy = int(siy * hdm_y)
      org_x = int(org_x * hdm_x)
      org_y = int(org_y * hdm_y)
      new_cat_x = int(new_cat_x * hdm_x)
      new_cat_y = int(new_cat_y * hdm_y)

      res_line = [(six,siy),(new_cat_x,new_cat_y)]
      draw.rectangle((six-7, siy-7, six+7, siy+7), outline='white')
      draw.rectangle((new_cat_x-7, new_cat_y-7, new_cat_x + 7, new_cat_y + 7), outline=color)
      #draw.ellipse((six-5, siy-5, six+7, siy+7),  outline ="white")
      draw.line(res_line, fill=color, width = 0)
      draw.text((new_cat_x, new_cat_y), str(dcname), font = font, fill="white")
      if org_x is not None:
         org_res_line = [(six,siy),(org_x,org_y)]
         draw.rectangle((org_x-5, org_y-5, org_x + 5, org_y + 5), outline="gray")
         draw.line(org_res_line, fill="gray", width = 0)
      if cp is not None:
         ltext0 = "Images / Res Px:"
         text0 =  str(len(cp['cat_image_stars'])) + " / " + str(cp['total_res_px'])[0:7]
         ltext1 = "Center RA/DEC:"
         text1 =  str(cp['ra_center'])[0:7] + " / " + str(cp['dec_center'])[0:7]
         ltext2 = "Center AZ/EL:"
         text2 =  str(cp['center_az'])[0:7] + " / " + str(cp['center_el'])[0:7]
         ltext3 = "Position Angle:"
         text3 =  str(cp['position_angle'])[0:7]
         ltext4 = "Pixel Scale:"
         text4 =  str(cp['pixscale'])[0:7]
         draw.text((800, 20), str(extra_text), font = font, fill="white")


         draw.text((20, 950), str(ltext0), font = font, fill="white")
         draw.text((20, 975), str(ltext1), font = font, fill="white")
         draw.text((20, 1000), str(ltext2), font = font, fill="white")
         draw.text((20, 1025), str(ltext3), font = font, fill="white")
         draw.text((20, 1050), str(ltext4), font = font, fill="white")
         draw.text((200, 950), str(text0), font = font, fill="white")
         draw.text((200, 975), str(text1), font = font, fill="white")
         draw.text((200, 1000), str(text2), font = font, fill="white")
         draw.text((200, 1025), str(text3), font = font, fill="white")
         draw.text((200, 1050), str(text4), font = font, fill="white")

         draw.text((1520, 1050), str(photo_credit), font = font, fill="white")
   return_img = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)

   return(return_img)


def make_grid_stars(merged_stars, mpc = None, factor = 2, gsize=50, limit=3):
   merged_stars = sorted(merged_stars, key=lambda x: x[-2], reverse=False)
   if mpc is None:
      print("FIRST TIME CAL!")
      gsize = 80
      factor = 2
      max_dist = 35
   else:
      print("MULTI-X CAL!", mpc['cal_version'])
      if mpc['cal_version'] < 3:
         gsize= 100
         factor = 2
         max_dist = 5
      else:
         gsize= 100
         factor = 1
         max_dist = 5

   all_res = [row[-2] for row in merged_stars]
   res1 = []
   res2 = []
   for star in merged_stars:
      (cal_file , center_az, center_el, ra_center, dec_center, position_angle, pixscale, dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int) = star
      center_dist = calc_dist((six,siy), (1920/2, 1080/2))
      cat_dist = calc_dist((six,siy), (new_cat_x,new_cat_y))
      if center_dist < 800:
         res1.append(cat_dist)
      else:
         res2.append(cat_dist)

   med_res = np.mean(all_res) ** 2
   med_res1 = np.mean(res1) ** factor
   med_res2 = np.mean(res2) ** factor
   if med_res1 > max_dist:
      med_res1 = max_dist
   if med_res2 > max_dist:
      med_res2 = max_dist

   qual_stars = []
   grid = {}
   for w in range(0,1920):
      for h in range(0,1080):
         if (w == 0 and h == 0) or (w % gsize == 0 and h % gsize == 0):
            x1 = w
            x2 = w + gsize
            y1 = h
            y2 = h + gsize
            if x2 > 1920:
               x2 = 1920
            if y2 > 1080:
               y2 = 1080
            grid_key = str(x1) + "_" + str(y1) + "_" + str(x2) + "_" + str(y2)

            if grid_key not in grid:
               grid[grid_key] = [] 

            for star in merged_stars:
               (cal_file , center_az, center_el, ra_center, dec_center, position_angle, pixscale, dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int) = star
               cat_dist = calc_dist((six,siy), (new_cat_x,new_cat_y))

               res_limit = med_res
               #print("RES:", res_limit, cat_dist)
               if x1 <= six <= x2 and y1 <= siy <= y2 : #and cat_dist < res_limit:
                  grid[grid_key].append(star)
                  #break
   
   print("med res1:", med_res1)
   print("med res2:", med_res2)
   print("MS:", len(merged_stars))
   print("QS:", len(qual_stars))


   return(grid)


def minimize_fov(cal_file, cal_params, image_file,img,json_conf,zero_poly=False, mcp=None, extra_text=None,show=0):
   orig_cal = dict(cal_params)

   cal_params = update_center_radec(cal_file,cal_params,json_conf)

   #all_res, inner_res, middle_res, outer_res = recalc_res(cal_params)
   all_res, inner_res, middle_res, outer_res,cal_params = recalc_res(cal_file, cal_params, json_conf)
   cal_params['total_res_px'] = all_res

   az = np.float64(orig_cal['center_az'])
   el = np.float64(orig_cal['center_el'])
   pos = np.float64(orig_cal['position_angle'])
   pixscale = np.float64(orig_cal['pixscale'])
   if mcp is not None:
      x_poly = np.float64(mcp['x_poly'])
      y_poly = np.float64(mcp['y_poly'])
   else:
      x_poly = np.float64(orig_cal['x_poly'])
      y_poly = np.float64(orig_cal['y_poly'])


   this_poly = np.zeros(shape=(4,), dtype=np.float64)
   this_poly = [.0001,.0001,.0001,.0001]


   if zero_poly is True:
      cal_params['x_poly'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params['y_poly'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params['x_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params['y_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)

      x_poly = np.zeros(shape=(15,), dtype=np.float64)
      y_poly = np.zeros(shape=(15,), dtype=np.float64)
      x_poly_fwd = np.zeros(shape=(15,), dtype=np.float64)
      y_poly_fwd = np.zeros(shape=(15,), dtype=np.float64)
   else:
      x_poly = mcp['x_poly']
      y_poly = mcp['y_poly']
      x_poly_fwd = mcp['x_poly_fwd']
      y_poly_fwd = mcp['y_poly_fwd']

      cal_params['x_poly'] = mcp['x_poly']
      cal_params['y_poly'] = mcp['y_poly']
      cal_params['x_poly_fwd'] = mcp['x_poly_fwd']
      cal_params['y_poly_fwd'] = mcp['y_poly_fwd']


   print("ZERO:", zero_poly)
   print(cal_params['x_poly'])


   # MINIMIZE!
   tries = 0

   orig_res = []
   orig_cat_image_stars = []

   # CALC RES
   for star in cal_params['cat_image_stars']:
      (dcname,mag,ra,dec,img_ra,img_dec,match_dist,up_cat_x,up_cat_y,img_az,img_el,up_cat_x,up_cat_y,six,siy,res_px,bp) = star
      new_cat_x, new_cat_y = get_xy_for_ra_dec(cal_params, ra, dec)
      res_px = calc_dist((six,siy),(new_cat_x,new_cat_y))

      new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(six,siy,cal_file,cal_params,json_conf)
      match_dist = angularSeparation(ra,dec,img_ra,img_dec)

      orig_res.append(res_px)
      orig_cat_image_stars.append((dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,res_px,bp)) 
   old_res = np.mean(orig_res)
   # END CALC RES
   print("ORIG RES:", old_res) 
   orig_info = [cal_params['center_az'], cal_params['center_el'], cal_params['ra_center'], cal_params['dec_center'], cal_params['position_angle'], cal_params['pixscale'], old_res ]
   print(cal_params['x_poly'])
   print("ORIG INFO :", orig_info)

   check_cal_params, check_report_txt, check_show_img = cal_params_report(image_file, cal_params, json_conf, img.copy(), 30, mcp)

   print("ORIG RECALC'D INFO :", check_cal_params['total_res_px'])
   ores = check_cal_params['total_res_px']

   print(x_poly, y_poly)
   print("MCP:", mcp)
   res = scipy.optimize.minimize(reduce_fov_pos, this_poly, args=( az,el,pos,pixscale,x_poly, y_poly, x_poly_fwd, y_poly_fwd, image_file,img,json_conf, cal_params['cat_image_stars'],extra_text,0), method='Nelder-Mead')
   print(res)

   if isinstance(cal_params['x_poly'], list) is not True:
      cal_params['x_poly'] = x_poly.tolist()
      cal_params['y_poly'] = x_poly.tolist()
      cal_params['x_poly_fwd'] = x_poly.tolist()
      cal_params['y_poly_fwd'] = x_poly.tolist()

   adj_az, adj_el, adj_pos, adj_px = res['x']

   print("ADJUSTMENTS:", adj_az, adj_el, adj_pos, adj_px )
   print("ORIG VALS:", az, el, pos, pixscale)
   new_az = az + (adj_az*az)
   new_el = el + (adj_el*el)
   new_position_angle = pos + (adj_pos*pos)
   new_pixscale = pixscale + (adj_px*pixscale)

   print("NEW VALS:", new_az, new_el, new_position_angle, new_pixscale)

   cal_params['center_az'] =  new_az
   cal_params['center_el'] =  new_el
   cal_params['position_angle'] =  new_position_angle
   cal_params['pixscale'] =  new_pixscale
   cal_params['total_res_px'] = res['fun']
   cal_params = update_center_radec(cal_file,cal_params,json_conf)
   #print("NEW INFO :", cal_file, cal_params['center_az'], cal_params['center_el'], cal_params['ra_center'], cal_params['dec_center'], cal_params['position_angle'], cal_params['pixscale'], cal_params['total_res_px'] ) 
   return(cal_params)


def reduce_fov_pos(this_poly,az,el,pos,pixscale, x_poly, y_poly, x_poly_fwd, y_poly_fwd, cal_params_file, oimage, json_conf, cat_image_stars, extra_text="", show=0):
   cal_fn = cal_params_file
   #extra_text = cal_fn[0:20]
   global tries
   tries = tries + 1
   image = oimage.copy()
   image = cv2.resize(image, (1920,1080))

   only_center = False 

   new_az = az + (this_poly[0]*az)
   new_el = el + (this_poly[1]*el)
   new_position_angle = pos + (this_poly[2]*pos)
   new_pixscale = pixscale + (this_poly[3]*pixscale)


   lat,lng,alt = json_conf['site']['device_lat'], json_conf['site']['device_lng'], json_conf['site']['device_alt']

   temp_cal_params = {}
   #temp_cal_params['ra_center'] = ra_center
   #temp_cal_params['dec_center'] = dec_center
   temp_cal_params['center_az'] = new_az
   temp_cal_params['center_el'] = new_el
   temp_cal_params['pixscale'] = new_pixscale
   temp_cal_params['position_angle'] = new_position_angle
   temp_cal_params['device_lat'] = json_conf['site']['device_lat']
   temp_cal_params['device_lng'] = json_conf['site']['device_lng']
   temp_cal_params['device_alt'] = json_conf['site']['device_alt']
   temp_cal_params['imagew'] = 1920
   temp_cal_params['imageh'] = 1080
   temp_cal_params['x_poly'] = x_poly
   temp_cal_params['y_poly'] = y_poly
   temp_cal_params['x_poly_fwd'] = x_poly_fwd 
   temp_cal_params['y_poly_fwd'] = y_poly_fwd
   temp_cal_params['cat_image_stars'] = cat_image_stars 
   temp_cal_params = update_center_radec(cal_fn,temp_cal_params,json_conf)

   #show_calparams(temp_cal_params)

   all_res = []
   new_cat_image_stars = []
   for star in cat_image_stars:
      (dcname,mag,ra,dec,img_ra,img_dec,match_dist,up_cat_x,up_cat_y,img_az,img_el,up_cat_x,up_cat_y,six,siy,res_px,bp) = star
      new_cat_x, new_cat_y = get_xy_for_ra_dec(temp_cal_params, ra, dec)
      res_px = calc_dist((six,siy),(new_cat_x,new_cat_y))

      new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(six,siy,cal_fn,temp_cal_params,json_conf)
      match_dist = angularSeparation(ra,dec,img_ra,img_dec)
      real_res_px = res_px
      if only_center is True:
         center_dist = calc_dist((960,540),(six,siy))
         if center_dist > 800:
            real_res_px = res_px
            res_px = 0

      all_res.append(res_px)
      new_cat_image_stars.append((dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,real_res_px,bp)) 
   mean_res = np.median(all_res)
   temp_cal_params['cat_image_stars'] = new_cat_image_stars 
   temp_cal_params['total_res_px'] = mean_res
   if SHOW == 1 or show == 1:
      star_img = draw_star_image(image, new_cat_image_stars,temp_cal_params, json_conf, extra_text) 
      cv2.imshow('pepe', star_img)
      cv2.waitKey(30)
   print(mean_res, len(new_cat_image_stars), extra_text, x_poly[0], y_poly[0])
   return(mean_res)


def delete_cal_file(cal_fn, con, cur, json_conf):
   cal_dir = "/mnt/ams2/cal/freecal/" + cal_fn.replace("-stacked-calparams.json", "")
   #if os.path.exists(cal_dir) is False:
   if True:
      sql = "DELETE FROM calibration_files where cal_fn = ?"
      dvals = [cal_fn]
      cur.execute(sql, dvals)
      print(sql, dvals)
      sql = "DELETE FROM calfile_paired_stars where cal_fn = ?"
      dvals = [cal_fn]
      cur.execute(sql, dvals)
      con.commit()
      print(sql, dvals)

def start_calib(cal_fn, json_conf, calfiles_data, mcp=None):
   autocal_dir = "/mnt/ams2/cal/"
   station_id = json_conf['site']['ams_id']
   (f_datetime, cam_id, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(cal_fn)

   cal_img, cal_params = view_calfile(cam_id, cal_fn, con, cur, json_conf, calfiles_data, None, mcp)
   #print("OK")
   #exit()

   if cal_img is False:
      print("FAILED")
      return(False)

   cal_img_fn = cal_fn.replace("-calparams.json", ".png")
   cal_image_file = cal_fn.replace("-calparams.json", ".png")
   cal_dir = cal_dir_from_file(cal_image_file)
   cal_json_file = get_cal_json_file(cal_dir)
   cal_json_fn = cal_json_file.split("/")[-1]
   if os.path.exists(cal_dir + cal_img_fn):
      clean_cal_img = cv2.imread(cal_dir + cal_img_fn)

   mask_file = "/mnt/ams2/meteor_archive/{}/CAL/MASKS/{}_mask.png".format(station_id, cam_id)
   if os.path.exists(mask_file) is True:
      mask = cv2.imread(mask_file)
      mask = cv2.resize(mask, (1920,1080))
   else:
      mask = np.zeros((1080,1920),dtype=np.uint8)
   clean_cal_img = cv2.subtract(clean_cal_img, mask)

   if mcp is None:
      mcp_file = autocal_dir + "multi_poly-" + station_id + "-" + cam_id + ".info"
      if os.path.exists(mcp_file) == 1:
         mcp = load_json_file(mcp_file)

   if mcp is not None:
      cal_params['x_poly'] = mcp['x_poly']
      cal_params['y_poly'] = mcp['y_poly']
      cal_params['x_poly_fwd'] = mcp['x_poly_fwd']
      cal_params['y_poly_fwd'] = mcp['y_poly_fwd']

      if "cal_version" not in mcp:
         mcp['cal_version'] = 0
      mcp['cal_version'] += 1
   else:
      mcp = None
      cal_params['x_poly'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params['y_poly'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params['x_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params['y_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
   

   
   return(station_id, cal_dir, cal_json_file, cal_image_file, cal_params, cal_img, clean_cal_img, mask_file, mcp)

def cal_status_report(cam_id, con, cur, json_conf): 
   station_id = json_conf['site']['ams_id']


   autocal_dir = "/mnt/ams2/cal/"
   # get all call files for this cam
   print("LOAD CAL FILES :", cam_id)
   calfiles_data = load_cal_files(cam_id, con, cur)

   mcp_file = autocal_dir + "multi_poly-" + station_id + "-" + cam_id + ".info"
   if os.path.exists(mcp_file) == 1:
      mcp = load_json_file(mcp_file)
      if "cal_version" not in mcp:
         mcp['cal_version'] = 0
   else:
      mcp = None

   if mcp is None:
      print("Can't update until the MCP is made!", cam_id)
      cmd = "python3 Process.py deep_init " + cam_id
      print(cmd)
      os.system(cmd)
      return()

   # get all paired stars by file 
   cal_files = []
   sql = """
      SELECT cal_fn, count(*) as ss, avg(res_px) as arp,  count(*) / avg(res_px) as score
        FROM calfile_paired_stars
       WHERE cal_fn like ?
         AND res_px is not NULL
       GROUP bY cal_fn
    ORDER BY score DESC
   """

   dvals = ["%" + cam_id + "%"]
   cur.execute(sql, dvals)
   rows = cur.fetchall()
   cal_fns = []

   calfile_paired_star_stats = {}
   stats_res = []
   stats_stars = []
   for row in rows:
      cal_fn, total_stars, avg_res , score = row
      cal_files.append((cal_fn, total_stars, avg_res , score))
      calfile_paired_star_stats[cal_fn] = [cal_fn,total_stars,avg_res] 
      stats_res.append(avg_res)
      stats_stars.append(total_stars)

   avg_res = np.mean(stats_res)
   avg_stars = np.mean(stats_stars)
   # get all files from the cal-index / filesystem
   freecal_index = load_json_file("/mnt/ams2/cal/freecal_index.json") 
  
   need_to_load = {}
   cal_files_count = 0
   for key in freecal_index:
      data = freecal_index[key]
      if data['cam_id'] == cam_id:
        cal_fn = key.split("/")[-1]
        if cal_fn not in calfiles_data:
           need_to_load[cal_fn] = {}
           need_to_load[cal_fn]['cal_dir'] = data['base_dir']
           need_to_load[cal_fn]['cal_fn'] = cal_fn
        if cal_fn not in calfile_paired_star_stats:
           need_to_load[cal_fn] = {}
           need_to_load[cal_fn]['cal_dir'] = data['base_dir']
           need_to_load[cal_fn]['cal_fn'] = cal_fn
        cal_files_count += 1

   print("TOTAL FILES", cal_files_count)
   print("FILES TO LOAD", len(need_to_load.keys()))

   lc = 1 
   for cal_fn in sorted(need_to_load, reverse=True):
      #print(lc, need_to_load[cal_fn]['cal_dir'] + cal_fn)
      cal_dir = need_to_load[cal_fn]['cal_dir'] + "/"
      print("import", cal_dir, cal_fn)
      import_cal_file(cal_fn, cal_dir, mcp)
      lc += 1

   print("All files loaded...")
   #os.system("clear")


   sql = """
      SELECT avg(res_px) as avg_res from calfile_paired_stars where cal_fn like ?
   """

   dvals = ["%" + cam_id + "%"]
   cur.execute(sql, dvals)
   rows = cur.fetchall()
   avg_res_2 = rows[0][0]


  
   from prettytable import PrettyTable as pt
   tb = pt()
   tb.field_names = ["Field", "Value"]

   tb.add_row(["Station ID", station_id])
   tb.add_row(["Camera ID", cam_id])
   tb.add_row(["Calfiles loaded in DB", len(calfiles_data.keys())])
   tb.add_row(["Calfiles with star data", len(calfile_paired_star_stats.keys())])
   tb.add_row(["Freecal source files", len(freecal_index.keys())])
   rr = str(round(avg_res,2)) + "/" + str(round(avg_res,2) )
   tb.add_row(["Average Res", rr])

   tb2 = pt()
   tb2.field_names = ["File", "Stars", "Res Px", "AZ", "EL", "Angle", "Scale", "Version", "Last Updated (Days)"]
   print("CAL FILES:", cal_files)
   cal_files = sorted(cal_files, key=lambda x: x[0], reverse=True)
   for row in cal_files:
      cal_fn, total_stars, avg_res , score = row
      if cal_fn not in calfiles_data:
         continue
      (station_id, camera_id, cal_fn, cal_ts, az, el, ra, dec, position_angle,\
         pixel_scale, zp_az, zp_el, zp_ra, zp_dec, zp_position_angle, zp_pixel_scale, x_poly, \
         y_poly, x_poly_fwd, y_poly_fwd, res_px, res_deg, ai_weather, ai_weather_conf, cal_version, last_update) = calfiles_data[cal_fn]

      tdiff = str((time.time() - last_update ) / 60 / 60 / 24)[0:5]

      tb2.add_row([cal_fn, str(total_stars), str(avg_res), az, el, position_angle, pixel_scale, cal_version, tdiff])


   #print("IN DB:", len(calfiles_data.keys()) )
   #print("WITH STAR DATA:", len(calfile_paired_star_stats.keys()))
   #print("IN FOLDER :", len(freecal_index.keys()) )
   print(tb)
   print(tb2)

   batch_apply(cam_id, con,cur, json_conf, 30, True)

def import_cal_file(cal_fn, cal_dir, mcp):

   # load json, insert into main table, insert stars into pairs table
   delete_cal_file(cal_fn, con, cur, json_conf)
   
   print("IMPORT:", cal_fn) 
   cal_img_file = cal_dir + cal_fn.replace("-calparams.json", ".png")
   if os.path.exists(cal_img_file) is True:
      cal_img = cv2.imread(cal_img_file)
      if SHOW == 1:
         cv2.imshow('pepe', cal_img)
         cv2.waitKey(10)
   else:
      print("failed to import:", cal_img_file, "not found")
      cmd = "mv " + cal_dir + " /mnt/ams2/cal/extracal/"
      os.system(cmd)
      return()
   if os.path.exists(cal_dir + cal_fn) is True:
      insert_calib(cal_dir + cal_fn , con, cur, json_conf)
      con.commit()

      cal_params = load_json_file(cal_dir + cal_fn)
      cal_params_nlm = cal_params.copy()
      cal_params_nlm['x_poly'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params_nlm['y_poly'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params_nlm['x_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params_nlm['y_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
      sc = 0
      for star in cal_params['cat_image_stars']:
         (dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,res_px,bp) = star
         print("IMPORT STAR:", dcname)
         img_x = six
         img_y = siy
         ra_key = str(ra) + "_" + str(dec)
         rx1 = int(new_cat_x - 16)
         rx2 = int(new_cat_x + 16)
         ry1 = int(new_cat_y - 16)
         ry2 = int(new_cat_y + 16)

         if rx1 <= 0 or ry1 <= 0 or rx2 >= 1920 or ry2 >= 1080:
            continue
         star_crop = cal_img[ry1:ry2,rx1:rx2]
         star_cat_info = [dcname,mag,ra,dec]
         star_obj = eval_star_crop(star_crop, cal_fn, rx1, ry1, rx2, ry2, star_cat_info)

         zp_x, zp_y, zp_img_ra,zp_img_dec, zp_img_az, zp_img_el = XYtoRADec(img_x,img_y,cal_fn,cal_params_nlm,json_conf)
         zp_cat_x, zp_cat_y = get_xy_for_ra_dec(cal_params_nlm, ra, dec)

         zp_res_px = calc_dist((img_x,img_y), (zp_cat_x,zp_cat_y))
         try:
            res_deg = angularSeparation(ra,dec,img_ra,img_dec)
         except:
            print("RES DEG FAILED TO COMPUTE!")
            continue
         star_obj["cal_fn"] = cal_fn
         star_obj["name"]  = dcname
         star_obj["mag"] = mag
         star_obj["ra"]  = ra
         star_obj["dec"] = dec
         star_obj["new_cat_x"] = new_cat_x
         star_obj["new_cat_y"] = new_cat_y
         star_obj["zp_cat_x"]  = zp_cat_x
         star_obj["zp_cat_y"] = zp_cat_y
         star_obj["img_x"] = img_x
         star_obj["img_y"] = img_y
         star_obj["star_flux"] = star_obj['star_flux']
         star_obj["star_yn"]  = star_obj['star_yn']
         star_obj["star_pd"] = star_obj['pxd']
         star_obj["star_found"] = 1
         if mcp is None:
            star_obj["lens_model_version"] = 1
         else:
            if "cal_version" not in mcp:
               mcp['cal_version'] = 1
            star_obj["lens_model_version"] = mcp['cal_version']
         if new_cat_x == 0 or zp_cat_x == 0:
            continue
       
         try:
            slope = (img_y - new_cat_y) / (img_x - new_cat_x)
         except:
            continue
         try:
            zp_slope = (img_y - zp_cat_y) / (img_x - zp_cat_x)
         except:
            continue

         star_obj["slope"] = slope
         star_obj["zp_slope"] = zp_slope
         star_obj["res_px"] = res_px
         star_obj["zp_res_px"] = zp_res_px
         star_obj["res_deg"] = res_deg
         insert_paired_star(cal_fn, star_obj, con, cur, json_conf)
         sc += 1
         
   else:
      print("failed to import :", cal_dir + cal_fn)
      return()


def batch_review(station_id, cam_id, con, cur, json_conf, limit=50, work_type="most_recent"):

   mask_file = "/mnt/ams2/meteor_archive/{}/CAL/MASKS/{}_mask.png".format(station_id, cam_id)
   if os.path.exists(mask_file) is True:
      mask = cv2.imread(mask_file)
      #mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
      mask = cv2.resize(mask, (1920,1080))
   else:
      mask = np.zeros((1080,1920),dtype=np.uint8)

   my_limit = limit
   # styles/work type = most_recent , top_20, best, worst
   last_cal = None
   autocal_dir = "/mnt/ams2/cal/"

   print("LOAD CAL FILES :", cam_id)

   calfiles_data = load_cal_files(cam_id, con, cur)

   mcp_file = autocal_dir + "multi_poly-" + station_id + "-" + cam_id + ".info"
   if os.path.exists(mcp_file) == 1:
      mcp = load_json_file(mcp_file)
      if "cal_version" not in mcp:
         mcp['cal_version'] = 0
   else:
      mcp = None

   all_stars = []
   all_res = []
   sql = """
      SELECT cal_fn, count(*) as ss, avg(res_px) as arp,  (count(*) / avg(res_px)) as score
        FROM calfile_paired_stars
       WHERE cal_fn like ?
         AND res_px is not NULL
   """

   sql += """
       GROUP bY cal_fn
   """
   if work_type == "most_recent":
      sql += """
         ORDER BY cal_fn DESC 
         LIMIT {}
      """.format(limit)
   elif work_type == "top":
      sql += """
         ORDER BY ss DESC 
         LIMIT {}
      """.format(limit)
   elif work_type == "worst":
      sql += """
         ORDER BY arp DESC 
         LIMIT {}
      """.format(limit)
   else: 
      sql += """
         ORDER BY ss DESC 
         LIMIT {}
      """.format(limit)

   dvals = ["%" + cam_id + "%"]
   cur.execute(sql, dvals)
   rows = cur.fetchall()
   cal_fns = []
   for row in rows:
      cal_fn, t_stars, avg_res,score = row
      all_stars.append(t_stars)
      all_res.append(avg_res)

   med_all_stars = np.median(all_stars)
   med_all_res = np.median(all_res)

   #for cal_fn in calfiles_data:
   sql = """
      SELECT cal_fn, count(*) as ss, avg(res_px) as arp,  (count(*) / avg(res_px)) as score
        FROM calfile_paired_stars
       WHERE cal_fn like ?
         AND res_px is not NULL
   """
   #if work_type == "top":
   #   sql += "AND ss > {}".format(med_all_res)

   sql += """
       GROUP bY cal_fn
       """
   if work_type == "most_recent":
      sql += """
         ORDER BY cal_fn DESC 
         LIMIT {}
      """.format(limit)
   elif work_type == "top":
      sql += """
         ORDER BY ss DESC 
         LIMIT {}
      """.format(limit)
   elif work_type == "worst":
      sql += """
         ORDER BY arp desc 
         LIMIT {}
      """.format(limit)
   else: 
      sql += """
         ORDER BY ss DESC 
         LIMIT {}
      """.format(limit)

   dvals = ["%" + cam_id + "%"]
   cur.execute(sql, dvals)
   rows = cur.fetchall()
   cal_fns = []
   cc = 0
   for row in rows:
      more_stars = False
      cal_fn, total_stars, avg_res,score = row
      if total_stars < med_all_stars or total_stars < 20:
         print("SKIP LOW STARS.")
         more_stars = True 
         #continue
      if cal_fn not in calfiles_data:
         print("MISSING", cal_fn,  "from calfiles_data???")
         continue
      if avg_res is None:
         print("ERROR", cal_fn, avg_res)
         exit()
         continue
      print("REVIEW", cal_fn, total_stars, avg_res)
      extra_text = cal_fn + " ( " + str(cc) + " / " + str(len(rows)) + ")"

      # -- RECENTER -- #
      cal_image_file = cal_fn.replace("-calparams.json", ".png")
      cal_dir = cal_dir_from_file(cal_image_file)
      cal_json_file = get_cal_json_file(cal_dir)
      cal_json_fn = cal_json_file.split("/")[-1]
      oimg = cv2.imread(cal_dir + cal_image_file)
      try:
         cal_params = load_json_file(cal_json_file)
         ores = cal_params['total_res_px']
      except:
         print("BAD FILE:", cal_json_file)
         print("BAD DIR :", cal_dir)
         continue
      if mcp is not None:
         cal_params['x_poly'] = mcp['x_poly']
         cal_params['y_poly'] = mcp['y_poly']
         cal_params['y_poly_fwd'] = mcp['y_poly_fwd']
         cal_params['x_poly_fwd'] = mcp['x_poly_fwd']
      else:
         cal_params['x_poly'] = np.zeros(shape=(15,), dtype=np.float64)
         cal_params['y_poly'] = np.zeros(shape=(15,), dtype=np.float64)
         cal_params['x_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
         cal_params['y_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)



      cat_stars, short_bright_stars, cat_image = get_catalog_stars(cal_params)
      cal_params['short_bright_stars'] = short_bright_stars



      stars,cat_stars = get_paired_stars(cal_fn, cal_params, con, cur)
      cal_params['cat_image_stars'] = cat_stars
      # Need to modes here?
      

      if cal_params['total_res_px'] > med_all_res and last_cal is not None:
         # use last best
         if False: # More work is needed to test vals after! 
            cal_params['center_az'] = last_cal['center_az']
            cal_params['center_el'] = last_cal['center_el']
            cal_params['position_angle'] = last_cal['position_angle']
            cal_params['pixscale'] = last_cal['pixscale']
            cal_params = update_center_radec(cal_fn,cal_params,json_conf)
            print("USING DEFAULT LAST BEST")

      print("RES/MED RES:", cal_params['total_res_px'], med_all_res)

      star_img = draw_star_image(oimg, cal_params['cat_image_stars'],cal_params, json_conf, extra_text) 
      if SHOW == 1:
         cv2.imshow('pepe', star_img)
         cv2.waitKey(30)


      #if len(cat_stars) < 60:
      #   catalog_image(cal_fn, con, cur, json_conf, mcp, True, True)
      if "cal_fn" not in cal_params:
         cal_params['cal_fn'] = cal_fn

      #
      #image_stars, star_objs = get_stars_from_image(oimg, cal_params)

      #if "star_points" not in cal_params:
      #cal_params['star_points'], star_image = get_star_points(cal_fn, oimg, cal_params, station_id, cam_id, json_conf)
      #pair_star_points(cal_fn, star_image, cal_params, json_conf, con, cur, mcp)

      #continue
      


      if len(cal_params['cat_image_stars']) < med_all_stars or more_stars is True:
         cal_params = catalog_image(cal_fn, con, cur, json_conf, mcp, True, True)
      #   star_points = get_star_points(cal_fn, oimg, cal_params, station_id, cam_id, json_conf)
      #   cat_image_stars = pair_star_points(star_points, cal_fn, star_img, cal_params, json_conf, con, cur, mcp)


      if False:
         if len(cal_params['cat_image_stars']) < med_all_stars or more_stars is True:
            cal_params = catalog_image(cal_fn, con, cur, json_conf, mcp, True, True)

         if len(cal_params['cat_image_stars']) < 15:
            print("SKIP LOW STARS!")
            if len(cal_params['cat_image_stars']) * 2 < med_all_stars:
               print("MOVE THIS CAL TO EXTRA POOL DIR")
               cmd = "mv " + cal_dir + " /mnt/ams2/cal/extracal/"
               print(cmd)
               os.system(cmd)


         continue


      #print("START:", cal_params['total_res_px'], ores)

      # check / remove dupes
      used = {}
      dupes = {}
      new_stars = []
      for star in cal_params['cat_image_stars'] :
         (dcname,mag,ra,dec,img_ra,img_dec,match_dist,up_cat_x,up_cat_y,img_az,img_el,up_cat_x,up_cat_y,six,siy,res_px,bp) = star
         key = str(ra) + "_" + str(dec)
         if key not in used:
            new_stars.append(star)
            used[key] = 1
         else:
            if key not in dupes:
               dupes[key] = 1
            else:
               dupes[key] += 1
            print("DUPE:", star)

      cal_params['cat_image_stars'] = new_stars
      print("NEW STARS:", len(new_stars))

      new_cal_params, del_stars = delete_bad_stars (cal_fn, cal_params, con,cur,json_conf, mcp)

      new_cal_params = minimize_fov(cal_fn, cal_params, cal_image_file,oimg,json_conf, False,mcp, extra_text)

      #if mcp is not None:
      #   new_cal_params = minimize_fov(cal_fn, new_cal_params, cal_image_file,oimg,json_conf, mcp)


      print("NEW:", new_cal_params['total_res_px'], "OLD:", cal_params['total_res_px'])
      # ALWAYS SAVE!

      if True: #new_cal_params['total_res_px'] <= ores: #cal_params['total_res_px']:
         up_stars, cat_image_stars = update_paired_stars(cal_fn, new_cal_params, stars, con, cur, json_conf)
         new_cal_params['cat_image_stars'] = cat_image_stars
         update_calibration_file(cal_fn, new_cal_params, con,cur,json_conf,mcp)
         save_json_file(cal_json_file, new_cal_params)
         print("SAVED:", cal_json_file)
      #elif new_cal_params['total_res_px'] == ores:
         #print("OLD IS SAME!", cal_params.keys())
      #else:
         #print("OLD IS BETTER (old,new)", ores, new_cal_params['total_res_px'])
      last_cal = dict(new_cal_params)

      # OLD WAY
      #new_cal_params, cat_stars = recenter_fov(cal_fn, cal_params, oimg.copy(), stars, json_conf)

      #print("AFTER CENTER NEW/OLD",  cal_params['total_res_px'], new_cal_params['total_res_px'])

      # -- END RECENTER -- #
      if cal_fn in calfiles_data:
         cal_fns.append(cal_fn)
      #exit()
      cc += 1
      if len(cal_params['cat_image_stars']) * 2 < med_all_stars:
         #print("MOVE THIS CAL TO EXTRA POOL DIR")
         cmd = "mv " + cal_dir + " /mnt/ams2/cal/extracal/"
         #print(cmd)
         os.system(cmd)
      #pair_star_points(cal_fn, oimg, cal_params, json_conf, con, cur, mcp)
   return(cal_fns)

def pair_star_points(cal_fn, oimg, cal_params, json_conf, con, cur, mcp):
   show_img = oimg.copy()
   cat_stars, short_bright_stars, cat_image = get_catalog_stars(cal_params)
   for star in cat_stars:
      (name,mag,ra,dec,new_cat_x,new_cat_y,zp_cat_x,zp_cat_y) = star
      if new_cat_x < 10 or new_cat_y < 10 or new_cat_x > 1910 or new_cat_y > 1070:
         continue

      desc = name + " " + str(mag)
      sql = """
               INSERT INTO calfile_catalog_stars (
                      cal_fn,
                      name,
                      mag,
                      ra,
                      dec,
                      new_cat_x,
                      new_cat_y,
                      zp_cat_x,
                      zp_cat_y 
               ) 
               VALUES (?,?,?,?,?,?,?,?,?)
      """
      ivals = [cal_fn, name,mag,ra,dec,new_cat_x,new_cat_y,zp_cat_x,zp_cat_y]
      try:
         cur.execute(sql, ivals)
      except:
         print("Must be done already")

   con.commit()

   up_cat_image_stars = []
   for img_x,img_y,star_flux in cal_params['star_points']:
      star_obj = {}
      star_obj['cal_fn'] = cal_fn
      star_obj['x'] = img_x
      star_obj['y'] = img_y
      star_obj['star_flux'] = star_flux
      close_stars = find_close_stars(star_obj)
      if len(close_stars) == 1:
         for star in close_stars:

            cal_fn, name, mag, ra, dec, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, \
            x_img_x, x_img_y, star_flux, star_yn, star_pd, star_found, lens_model_version, \
            slope, zp_slope, dist, zp_dist = star



            #print("STAR:", star)
            if new_cat_x is not None and img_x is not None:
               cv2.line(show_img, (int(zp_cat_x),int(zp_cat_y)), (int(img_x),int(img_y)), (128,128,128), 1)
               cv2.putText(show_img, str(dist)[0:4],  (int(new_cat_x),int(new_cat_y)), cv2.FONT_HERSHEY_SIMPLEX, .4, (200,200,200), 1)
      
               new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(img_x,img_y,cal_fn,cal_params,json_conf)

               res_px = calc_dist((img_x,img_y),(new_cat_x,new_cat_y))
               match_dist = angularSeparation(ra,dec,img_ra,img_dec)

               if res_px < 5:
                  up_cat_image_stars.append((name,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,img_x,img_y,res_px,star_flux) )


            if SHOW == 1:
               cv2.imshow('pepe', show_img)
               cv2.waitKey(30)


   # save the cal params file with latest cat_image_stars and then re-import it
   cal_dir = "/mnt/ams2/cal/freecal/" + cal_fn.replace("-stacked-calparams.json", "/")
   cal_params['cat_image_stars'] = up_cat_image_stars
   save_json_file(cal_dir + cal_fn, cal_params)
   
   #import_cal_file(cal_fn, cal_dir, mcp)

   return()
      

def re_pair_stars(cal_fn, cp, json_conf, show_img, con, cur,mcp):
   # NOT WORKING!
   star_cat_dict = {}
   star_img_dict = {}
   new_cat_stars = []
   # if already there we can skip!
   for star in cp['cat_image_stars']:
      (dcname,mag,ra,dec,img_ra,img_dec,match_dist,up_cat_x,up_cat_y,img_az,img_el,up_cat_x,up_cat_y,six,siy,res_px,bp) = star
      ra_key = str(ra) + "_" + str(dec)
      img_key = str(int(six)) + "_" + str(int(siy))
      if ra_key not in star_cat_dict:
         star_cat_dict[ra_key] = star
      if img_key not in star_img_dict:
         star_img_dict[img_key] = star
      new_cat_stars.append((dcname,mag,ra,dec,img_ra,img_dec,match_dist,up_cat_x,up_cat_y,img_az,img_el,up_cat_x,up_cat_y,six,siy,res_px,bp))

   for star in cp['star_points']:
      x, y, bp = star
      print("TRY:", x,y)
      new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(x,y,cal_fn,cp,json_conf)
      img_key = str(int(x)) + "_" + str(int(y))
      if img_key in star_img_dict:
         cv2.circle(show_img, (int(x),int(y)), 15, (128,255,128),1)
         print("--- GOT IT SKIP", x,y)
         continue 
      
      matches = []
      for cat_star in cp['short_bright_stars']:
         (name, name2, ra, dec, mag) = cat_star
         ra_key = str(ra) + "_" + str(dec)
         if ra_key in star_cat_dict:
            #print("--- GOT RA SKIP", ra_key)
            #cv2.circle(show_img, (int(x),int(y)), 15, (0,255,0),2)
            continue 

         new_cat_x, new_cat_y = get_xy_for_ra_dec(cp, ra, dec)
         res_px = calc_dist((x,y),(new_cat_x,new_cat_y))
         match_dist = angularSeparation(ra,dec,img_ra,img_dec)
         if match_dist < .5 or res_px <= 10:
            print("--- NEW ---", name, match_dist, res_px)
            matches.append((cat_star, match_dist))
            cv2.circle(show_img, (int(x),int(y)), 15, (255,255,0),2)
            cv2.line(show_img, (int(new_cat_x),int(new_cat_y)), (int(x),int(y)), (128,128,128), 1)
            cv2.circle(show_img, (int(x),int(y)), 5, (255,255,255),1)
            cv2.circle(show_img, (int(new_cat_x),int(new_cat_y)), 5, (128,128,255),1)
            if SHOW == 1:
               cv2.imshow('pepe', show_img)
               cv2.waitKey(10)
            star_cat_dict[ra_key] = star
            star_img_dict[img_key] = star
      matches = sorted(matches, key=lambda x: x[1], reverse=False)
      if len(matches) > 0:
         print("CLOSESEST:", matches[0])
         new_cat_stars.append((dcname,mag,ra,dec,img_ra,img_dec,match_dist,up_cat_x,up_cat_y,img_az,img_el,up_cat_x,up_cat_y,six,siy,res_px,bp))
         new_star = (dcname,mag,ra,dec,img_ra,img_dec,match_dist,up_cat_x,up_cat_y,img_az,img_el,up_cat_x,up_cat_y,six,siy,res_px,bp)
         insert_paired_star_full(new_star, cal_fn, cp, mcp, json_conf)

   cp['cat_image_stars'] = new_cat_stars

   print("REPAIR DONE")
   print("NEW CAT IMG STARS!", len(cp['cat_image_stars']))

   return(cp)

def make_plate(cal_fn, json_conf, con, cur):

   (f_datetime, cam_id, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(cal_fn)
   mcp = get_mcp(cam_id) 

   calfiles_data = load_cal_files(cam_id, con, cur)

   plate_img = np.zeros((1080,1920),dtype=np.uint8)

   resp = start_calib(cal_fn, json_conf, calfiles_data, mcp)
   if resp is False:
      print(resp)
      print("start Calib failed!")
      return(False)
   else:
      (station_id, cal_dir, cal_json_file, cal_img_file, cal_params, cal_img, clean_cal_img, mask_file,mcp) = resp

   plate_file = cal_dir + "/" + cal_fn.replace("-stacked-calparams.json", "-plate.png")
   gray_img = cv2.cvtColor(clean_cal_img, cv2.COLOR_BGR2GRAY)

   resp = get_star_points(cal_fn, clean_cal_img, cal_params, station_id, cam_id, json_conf)

   if resp is not None:
      star_points, star_img = resp
   else:
      print("GET STAR POINTS RESP:", resp)
      star_points = []
      

   for x,y,bp in star_points:
      x1 = x - 2
      y1 = y - 2
      x2 = x + 2
      y2 = y + 2
      plate_img[y1:y2,x1:x2] = gray_img[y1:y2,x1:x2]
      if x1 <= 0 or x2 >= 1920 or y1 < 0 or y2 >= 1080:
         continue
   if SHOW == 1:
      cv2.imshow('pepe', plate_img)
      cv2.waitKey(30)
   print(plate_file)
   cv2.imwrite(plate_file, plate_img)

def ui_frame():
   logo = cv2.imread("ALLSKY_LOGO.png")
   logo = imutils.resize(logo, width=1280)
   ui = np.zeros((1080,1920,3),dtype=np.uint8)
   # main
   cv2.rectangle(ui, (0,0), (1280,720) , [255,255,255], 1)
   # logo right top
   #cv2.rectangle(ui, (1280,0), (1920,158) , [255,255,255], 1)
   # 2nd frame (with logo right top)
   #cv2.rectangle(ui, (1280,158), (1920,360+158) , [255,255,255], 1)

   cv2.rectangle(ui, (1280,0), (1920,360) , [255,255,255], 1)
   cv2.rectangle(ui, (1280,360), (1920,720) , [255,255,255], 1)
   cv2.rectangle(ui, (0,720), (1280,317+720) , [255,255,255], 1)
   ui[740:317+740,2:1282] = logo
   cv2.rectangle(ui, (1280,720), (1920,1080) , [255,255,255], 1)
   
   #make empty ui frame
   return(ui)

def star_points_report(cam_id, json_conf, con, cur):
   mcp = get_mcp(cam_id)
   ui_img = ui_frame()
   #cv2.imshow('pepe', ui_img)
   #cv2.waitKey(30)
   if SHOW == 1:
      cv2.namedWindow("pepe")
      cv2.resizeWindow("pepe", 1920, 1080)
      cv2.moveWindow("pepe", 1400,100)


   hdmx_360 = 640 / 1920
   hdmy_360 = 360 / 1080
   photo_credit = make_photo_credit(json_conf, cam_id)

   calfiles_data = load_cal_files(cam_id, con, cur)
   mcp = get_mcp(cam_id) 
   station_id = json_conf['site']['ams_id']
   # make / verify star points and associated files for all cal_files in the system!

   all_merged_stars = []
   all_merged_stars_file = "/mnt/ams2/cal/" + station_id + "_" + cam_id + "_MERGED_STARS.json"

   console_image = np.zeros((360,640,3),dtype=np.uint8)


   zp_image = np.zeros((1080,1920,3),dtype=np.uint8)
   zp_image_small = np.zeros((360,640,3),dtype=np.uint8)
   for cal_fn in calfiles_data:
      cal_dir = "/mnt/ams2/cal/freecal/" + cal_fn.replace("-stacked-calparams.json", "/")
      cal_img_file = cal_dir + cal_fn.replace("-calparams.json", ".png")
      cal_json_file = cal_dir + cal_fn
      star_points_file = cal_dir + cal_fn.replace("-calparams.json", "-star-points.json")
      star_pairs_file = cal_dir + cal_fn.replace("-calparams.json", "-star-pairs.json")
      star_points_image_file = cal_dir + cal_fn.replace("-calparams.json", "-star-points.jpg")
      star_pairs_image_file = cal_dir + cal_fn.replace("-calparams.json", "-star-pairs.jpg")



      if os.path.exists(cal_img_file):
         cal_img = cv2.imread(cal_img_file)

      if os.path.exists(star_points_image_file):
         star_points_img = cv2.imread(star_points_image_file)
      if os.path.exists(star_pairs_image_file):
         star_pairs_img = cv2.imread(star_pairs_image_file)
      if os.path.exists(star_points_file):
         cp = load_json_file(cal_json_file)

         before_ra = cp['ra_center']
         before_dec = cp['dec_center']
         before_pos = cp['position_angle']
         before_pxs = cp['pixscale']
         before_res = cp['total_res_px']

         if mcp is not None:
            cp['x_poly'] = mcp['x_poly']
            cp['y_poly'] = mcp['y_poly']
            cp['y_poly_fwd'] = mcp['y_poly_fwd']
            cp['x_poly_fwd'] = mcp['x_poly_fwd']
         else:
            cp['x_poly'] = np.zeros(shape=(15,), dtype=np.float64)
            cp['y_poly'] = np.zeros(shape=(15,), dtype=np.float64)
            cp['x_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
            cp['y_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)



         try:
            star_pairs= load_json_file(star_pairs_file)
            star_points = load_json_file(star_points_file)
         except:
            print("FAILED:", star_pairs_file)
            continue

         cat_image_stars = []

         # HERE WE SHOULD DO SOMETHING..
         # TO UPDATE WITH THE LATEST PARAMS
         # AND RESAVE THE PAIRS!
         new_star_pairs = []
         for star in star_pairs:
            (hip_id, name_ascii, cons, mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,x,y,zp_cat_x,zp_cat_y,slope,zp_slope,res_px,flux) = star

            new_cat_x, new_cat_y = get_xy_for_ra_dec(cp, ra, dec)
            new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(x,y,cal_fn,cp,json_conf)
            img_new_cat_x, img_new_cat_y = get_xy_for_ra_dec(cp, img_ra, img_dec)
            new_star_pairs.append((hip_id, name_ascii, cons, mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,x,y,zp_cat_x,zp_cat_y,slope,zp_slope,res_px,flux)) 

            cat_image_stars.append((name_ascii,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,x,y,res_px,flux))

          
            all_merged_stars.append((cal_fn, cp['center_az'], cp['center_el'], cp['ra_center'], cp['dec_center'], cp['position_angle'], cp['pixscale'], name_ascii, mag,ra,dec,ra,dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,x,y,res_px,flux))

            if res_px <= 5:
               color = [20,255,57]
               bad = False 
            elif 5 < res_px <= 10:
               color = [152,251,152]
               bad = False 
            else:
               bad = True
               color = [0,0,255]
            cv2.line(zp_image, (int(zp_cat_x),int(zp_cat_y)), (int(x),int(y)), color, 1)
           
            zp_cat_x_sm = int(zp_cat_x * hdmx_360)
            zp_cat_y_sm = int(zp_cat_y * hdmy_360)
            x_sm = int(x * hdmx_360)
            y_sm = int(y * hdmy_360)

            cv2.line(zp_image_small, (int(zp_cat_x_sm),int(zp_cat_y_sm)), (int(x_sm),int(y_sm)), color, 1)

         desc = str(len(star_pairs)) + " / " + str(len(star_points))
         perc_good = int((len(star_pairs) / len(star_points)) * 100)
         desc += " = " + str(perc_good) + "%"
         if perc_good < 50:
            color = [0,0,255]
         else:
            color = [0,255,0]

         cp['cat_image_stars'] = cat_image_stars

         # all_res, inner_res, middle_res, outer_res = recalc_res(cp)
         all_res, inner_res, middle_res, outer_res,cp = recalc_res(cal_fn, cp , json_conf)
         #print("RES:", all_res)

         cal_img_720 = cv2.resize(cal_img, (1280,720))
         stars_image = draw_stars_on_image(cal_img_720, cat_image_stars,cp,json_conf,extra_text=None,img_w=1280,img_h=720) 

         final_img = ui_img.copy()
         main_frame_img = cv2.resize(star_pairs_img,(1280,720))
         sub_frame_img_2 = cv2.resize(cal_img, (640,360))
         sub_frame_img_1 = zp_image_small 


         text_data = []
         text_data.append((20,10,photo_credit))

         az = round(cp['center_az'],1)
         el = round(cp['center_el'],1)
         ra = round(float(cp['ra_center']),1)
         dec = round(float(cp['dec_center']),1)
         pos = round(float(cp['position_angle']),1)
         pixscale = round(float(cp['pixscale']),1)
         all_res = round(all_res,1)

         text_data.append((20,50,"Total Stars"))
         text_data.append((250,50,str(len(cp['cat_image_stars']))))
         text_data.append((20,75,"Residuals"))
         text_data.append((250,75,str(all_res)))
         text_data.append((20,100,"Azimuth"))
         text_data.append((250,100,str(az)))
         text_data.append((20,125,"Elevation"))
         text_data.append((250,125,str(el)))
         text_data.append((20,150,"Ra"))
         text_data.append((250,150,str(ra)))
         text_data.append((20,175,"Dec"))
         text_data.append((250,175,str(dec)))
         text_data.append((20,200,"Position Angle"))
         text_data.append((250,200,str(pos)))
         text_data.append((20,225,"Pixel Scale"))
         text_data.append((250,225,str(pixscale)))


         console_frame = draw_text_on_image(console_image.copy(), text_data)

         final_img[0:720,0:1280] = stars_image #main_frame_img
         final_img[0:360,1280:1920] = sub_frame_img_1 
         final_img[360:720,1280:1920] = sub_frame_img_2
         final_img[720:1080,1280:1920] = console_frame 
       
         if SHOW == 1:
            cv2.imshow('pepe', final_img)
            cv2.waitKey(30)

         center_stars = cp['cat_image_stars']

         extra_text = "minimize cal params"

         new_cp = minimize_fov(cal_fn, cp, cal_fn,cal_img,json_conf, False,mcp, extra_text, show=0)

         stars_image = draw_stars_on_image(cal_img_720, new_cp['cat_image_stars'],new_cp,json_conf,extra_text=None,img_w=1280,img_h=720) 
         final_img[0:720,0:1280] = stars_image #main_frame_img
         if SHOW == 1:
            cv2.imshow('pepe', final_img)
            cv2.waitKey(30)
         #SHOW = 1

         # save new / updated json file 
         # and also update the DB
         save_json_file(cal_json_file, new_cp)
         update_calibration_file(cal_fn, new_cp, con,cur,json_conf,mcp)


         print("SAVING NEW JSON FILE!", cal_json_file)
         save_json_file(star_pairs_file, new_star_pairs)

         #cv2.imshow('pepe', final_img)
         #cv2.waitKey(30)

   save_json_file(all_merged_stars_file, all_merged_stars)
   print("saved", len(all_merged_stars), "stars", all_merged_stars_file)


def star_points_all(cam_id, json_conf, con, cur):
   calfiles_data = load_cal_files(cam_id, con, cur)
   mcp = get_mcp(cam_id) 
   station_id = json_conf['site']['ams_id']
   # make / verify star points and associated files for all cal_files in the system!

   zp_image_file = "/mnt/ams2/cal/plots/" + station_id + "_" + cam_id + "_ZP_STARS.jpg"
   zp_image = np.zeros((1080,1920,3),dtype=np.uint8)
   for cal_fn in calfiles_data:
      cal_dir = "/mnt/ams2/cal/freecal/" + cal_fn.replace("-stacked-calparams.json", "/")
      cal_img_file = cal_dir + cal_fn.replace("-calparams.json", ".png")
      cal_json_file = cal_dir + cal_fn
      star_points_file = cal_dir + cal_fn.replace("-calparams.json", "-star-points.json")
      star_pairs_file = cal_dir + cal_fn.replace("-calparams.json", "-star-pairs.json")
      star_points_image_file = cal_dir + cal_fn.replace("-calparams.json", "-star-points.jpg")
      star_pairs_image_file = cal_dir + cal_fn.replace("-calparams.json", "-star-pairs.jpg")

      cal_params = cal_data_to_cal_params(cal_fn, calfiles_data[cal_fn],json_conf, mcp)


      if mcp is not None:
         cal_params['x_poly'] = mcp['x_poly']
         cal_params['y_poly'] = mcp['y_poly']
         cal_params['y_poly_fwd'] = mcp['y_poly_fwd']
         cal_params['x_poly_fwd'] = mcp['x_poly_fwd']
      else:
         cal_params['x_poly'] = np.zeros(shape=(15,), dtype=np.float64)
         cal_params['y_poly'] = np.zeros(shape=(15,), dtype=np.float64)
         cal_params['x_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
         cal_params['y_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)

      if os.path.exists(star_points_file) is False:
         if os.path.exists(cal_img_file):
            cal_img = cv2.imread(cal_img_file)
         if os.path.exists(cal_json_file):
            try:
               cp = load_json_file(cal_json_file)
            except:
               return

         star_points, star_image = get_star_points(cal_fn,  cal_img, cp, station_id, cam_id, json_conf)
         cv2.imwrite(star_points_image_file, star_image)
         save_json_file(star_points_file, star_points)
         print("saved", star_points_file)
      else:
         star_points = load_json_file(star_points_file)
         star_image = cv2.imread(star_points_image_file)

      if SHOW == 1:
         cv2.imshow('pepe', star_image)
         cv2.waitKey(30)

      if True:
      #if os.path.exists(star_pairs_file) is False:
         star_pairs = []
      else:
         try:
            star_pairs = load_json_file(star_pairs_file)
            #continue 
         except:
             
            star_pairs = []
            print("DONE", star_pairs_file)

      # pair stars
      if len(star_pairs) == 0:
         resp = pair_points(cal_fn, star_points, star_pairs_file, star_pairs_image_file, cal_params, star_image, zp_image)
         if resp is not None:
            star_pairs,show_image,zp_image = resp
         else:
            print(resp)

      else:
         print("WE did everything for this file already")
         img = cv2.imread(star_pairs_image_file)
         if SHOW == 1:
            cv2.imshow('pepe', img)
            cv2.waitKey(30)
   cv2.imwrite(zp_image_file, zp_image)

def pair_points(cal_fn, star_points, star_pairs_file, star_pairs_image_file, cal_params,star_image, zp_image):
      show_img = star_image.copy()
      star_pairs = []
      cal_params_nlm = cal_params.copy()
      cal_params_nlm['x_poly'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params_nlm['y_poly'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params_nlm['x_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params_nlm['y_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)


      cat_stars, short_bright_stars, cat_image = get_catalog_stars(cal_params)
      for star in cat_stars:
         (name,mag,ra,dec,new_cat_x,new_cat_y,zp_cat_x,zp_cat_y) = star

         #zp_x, zp_y, zp_img_ra,zp_img_dec, zp_img_az, zp_img_el = XYtoRADec(x,y,cal_fn,cal_params_nlm,json_conf)
         zp_cat_x, zp_cat_y = get_xy_for_ra_dec(cal_params_nlm, ra, dec)

         sql = """
               INSERT INTO calfile_catalog_stars (
                      cal_fn,
                      name,
                      mag,
                      ra,
                      dec,
                      new_cat_x,
                      new_cat_y,
                      zp_cat_x,
                      zp_cat_y
               )
               VALUES (?,?,?,?,?,?,?,?,?)
         """
         ivals = [cal_fn, name,mag,ra,dec,new_cat_x,new_cat_y,zp_cat_x,zp_cat_y]
         try:
            cur.execute(sql, ivals)
         except:
            print("Must be done already")
      con.commit()

      cc = 0
      for x,y,flux in star_points:
         new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(x,y,cal_fn,cal_params,json_conf)
         img_new_cat_x, img_new_cat_y = get_xy_for_ra_dec(cal_params, img_ra, img_dec)


         # try to find it from the reverse ra/dec of the bright point
         sql = """
            SELECT hip_id, mag, iau_ra, iau_decl, name_ascii, constellation 
              FROM catalog_stars 
             WHERE iau_ra > ?
               AND iau_ra < ?
               AND iau_decl > ?
               AND iau_decl < ?
          ORDER BY mag ASC
         """
         svals = [img_ra-5, img_ra+5, img_dec-5, img_dec+5]
         cur.execute(sql, svals)
         rows = cur.fetchall()

         # try to find it from the reverse ra/dec of the bright point
         sql = """
            SELECT name, mag, ra, dec, name, name  
              FROM calfile_catalog_stars 
             WHERE new_cat_x > ?
               AND new_cat_x < ?
               AND new_cat_y > ?
               AND new_cat_y < ?
               AND cal_fn = ?
          ORDER BY mag ASC
         """
         res = 25
         svals = [x-res, x+res, y-res, y+res, cal_fn]
         cur.execute(sql, svals)
         rows2 = cur.fetchall()
         print(sql)
         print(svals)
         print("ROWS1", len(rows))
         print("ROWS2", len(rows2))
         if len(rows) == 0 and len(rows2) > 0:
            print("ROWS2 OVERRIDE!", rows2)
            rows = rows2


         #(116727, 3.21, 354.836655, 77.632313, 'Errai', 'Cep')
         for row in rows:
            hip_id, mag, ra, dec, name_ascii, cons = row 
            new_cat_x, new_cat_y = get_xy_for_ra_dec(cal_params, ra, dec)
            x1 = new_cat_x - 16 
            x2 = new_cat_x + 16 
            y1 = new_cat_y - 16 
            y2 = new_cat_y + 16 
            if name_ascii == "":
               name_ascii = hip_id
            zp_x, zp_y, zp_img_ra,zp_img_dec, zp_img_az, zp_img_el = XYtoRADec(x,y,cal_fn,cal_params_nlm,json_conf)
            zp_cat_x, zp_cat_y = get_xy_for_ra_dec(cal_params_nlm, img_ra, img_dec)


            res_px = calc_dist((new_cat_x,new_cat_y),(x,y))
            if res_px <= 5:
               color = [20,255,57]
               bad = False 
            elif 5 < res_px <= 10:
               color = [152,251,152]
               bad = False 
            else:
               bad = True
               color = [0,0,255]

            print("RES", res_px, color)
            # NEED TO HANDLE MULTI'S BETTER HERE!
            #cv2.rectangle(show_img, (int(x1), int(y1)), (int(x2) , int(y2) ), color, 1)
            if bad is False:
               cv2.rectangle(show_img, (int(new_cat_x-2), int(new_cat_y-2)), (int(new_cat_x+2) , int(new_cat_y+2) ), color, 1)
               cv2.line(show_img, (int(new_cat_x),int(new_cat_y)), (int(x),int(y)), color, 1)

               cv2.rectangle(show_img, (int(zp_cat_x-2), int(zp_cat_y-2)), (int(zp_cat_x+2) , int(zp_cat_y+2) ), [192,240,208], 1)

               cv2.line(show_img, (int(zp_cat_x),int(zp_cat_y)), (int(x),int(y)), color, 1)
               cv2.line(zp_image, (int(zp_cat_x),int(zp_cat_y)), (int(x),int(y)), color, 1)

               desc = name_ascii + " (" + str(int(mag)) + ") " + str(int(ra)) + " / " + str(int(dec))
               cv2.putText(show_img, desc,  (int(x1-10),int(y2+10)), cv2.FONT_HERSHEY_SIMPLEX, .4, color, 1)

               match_dist = angularSeparation(ra,dec,img_ra,img_dec)
               res_px = calc_dist((x,y),(new_cat_x,new_cat_y))

               slope = (y - new_cat_y) / (x - new_cat_x)
               zp_slope = (y - zp_cat_y) / (x - zp_cat_x)


               star_pairs.append((hip_id, name_ascii, cons, mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,x,y,zp_cat_x,zp_cat_y,slope,zp_slope,res_px,flux)) 

            #else:
            #   cv2.putText(show_img, "X: " + str(int(res_px)),  (int(x+5),int(y+5)), cv2.FONT_HERSHEY_SIMPLEX, .4, color, 1)
               #cv2.line(show_img, (int(new_cat_x),int(new_cat_y)), (int(x),int(y)), color, 1)
            #cv2.circle(show_img, (int(x1 + mx),int(y1 + my)), 5, (128,128,128),1)
            #desc2 = "IMG: " + str(img_ra)[0:5] + " " + str(img_dec)[0:5]
            #cv2.putText(show_img, desc2,  (int(x1),int(y2+20)), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,0,255), 1)


         if len(rows) > 0 or len(rows2) > 0 :
             foo = 1
         #   print("CLOSE:", rows)
         else:
         #   print("NO CLOSE STARS IN RA/DEC:", svals)
            desc = "X - No close stars" 
            cv2.putText(show_img, desc,  (int(x),int(y)), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,0,255), 1)
         if SHOW == 1:
            if cc % 50 == 0:
               cv2.imshow('pepe', show_img)
               cv2.imshow('pepe2', zp_image)
               cv2.waitKey(30)


         cc += 1
      cv2.waitKey(90)

      save_json_file(star_pairs_file, star_pairs)
      cv2.imwrite(star_pairs_image_file, show_img)
      print("SAVED:", star_pairs_file, len(star_pairs))
      print("SAVED:", star_pairs_image_file)


def get_star_points(cal_fn, oimg, cp, station_id, cam_id, json_conf):
   gsize = 50
   mask_file = "/mnt/ams2/meteor_archive/{}/CAL/MASKS/{}_mask.png".format(station_id, cam_id)
   if os.path.exists(mask_file) is True:
      mask = cv2.imread(mask_file)
      #mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
      mask = cv2.resize(mask, (1920,1080))
   else:
      mask = np.zeros((1080,1920),dtype=np.uint8)

   # fastest possible way to get STAR POINTS (Possible stars) from the image
   gray_orig = cv2.cvtColor(oimg, cv2.COLOR_BGR2GRAY)
   gray_img = cv2.cvtColor(oimg, cv2.COLOR_BGR2GRAY)
   if len(mask.shape) == 3:
      mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
   gray_img = cv2.subtract(gray_img, mask)
   star_points = []
   c = 0
   show_img = oimg.copy()
   for w in range(0,1920):
      for h in range(0,1080):
         found = False
         if (w == 0 and h == 0) or (w % gsize == 0 and h % gsize == 0):
            x1 = w
            x2 = w + gsize
            y1 = h
            y2 = h + gsize
            if x2 > 1920:
               x2 = 1920
            if y2 > 1080:
               y2 = 1080
            grid_key = str(x1) + "_" + str(y1) + "_" + str(x2) + "_" + str(y2)
            crop = gray_img[y1:y2,x1:x2]
            low_row = np.mean(crop[-1,:])
            if low_row == 0 or crop[-1,0] == 0 or crop[-1,-1] == 0:
               continue
            min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(crop)
            avg_val = np.mean(crop)
            pxd = max_val - avg_val
            cv2.rectangle(show_img, (int(x1), int(y1)), (int(x2) , int(y2) ), (255, 255, 255), 1)
            if pxd > 15 and avg_val < 80:
               found = True 
               cv2.circle(show_img, (int(x1 + mx),int(y1 + my)), 5, (128,128,128),1)
               star_points.append((x1+mx,y1+my,max_val))
            if c % 25 == 0:
               if SHOW == 1: 
                  cv2.imshow('pepe', show_img)
                  if avg_val < 10 or found is False:
                     cv2.waitKey(1)
                  else:
                     cv2.waitKey(1)
            c += 1

   if SHOW == 1:
      cv2.waitKey(100)
   #show_img = oimg.copy()
   return(star_points, show_img )

   for star in star_points:
      x,y,bp = star
      cv2.circle(show_img, (int(x),int(y)), 15, (88,88,88),1)

      x1 = w
      x2 = w + gsize
      y1 = h
      y2 = h + gsize
      if x2 > 1920:
         x2 = 1920
      if y2 > 1080:
         y2 = 1080
      grid_key = str(x1) + "_" + str(y1) + "_" + str(x2) + "_" + str(y2)
      crop = gray_img[y1:y2,x1:x2]

      rx1 = int(x - 16)
      rx2 = int(x + 16)
      ry1 = int(y - 16)
      ry2 = int(y + 16)
      if rx1 < 0 or ry1 < 0:
         continue
      if rx2 >= 1920 or ry2 >= 1080 :
         continue
      star_crop = gray_img[ry1:ry2,rx1:rx2]

      star_obj = eval_star_crop(star_crop, cal_fn, rx1, ry1, rx2, ry2)
      print("")
      if star_obj['valid_star'] is True:
         if star_obj['star_yn'] > 50:
            cv2.rectangle(show_img, (int(star_obj['x1']), int(star_obj['y1'])), (int(star_obj['x2']) , int(star_obj['y2']) ), (0, 255, 0), 1)
         else:
            cv2.rectangle(show_img, (int(star_obj['x1']), int(star_obj['y1'])), (int(star_obj['x2']) , int(star_obj['y2']) ), (0, 128, 0), 1)
      else:
         cv2.rectangle(show_img, (int(star_obj['x1']), int(star_obj['y1'])), (int(star_obj['x2']) , int(star_obj['y2']) ), (0, 0, 255), 1)
      #if SHOW == 1:
      #   cv2.imshow('pepe', show_img)
      #   cv2.waitKey(10)

      # ROUNDED POINT! (for flux!)
      sx = int(star_obj['star_x'])
      sy = int(star_obj['star_y'])
      #show_img[sy, sx] = [0,0,255]
      cv2.circle(show_img, (int(sx),int(sy)), int(star_obj['radius']), (0,0,255),1)

      # ANNULUS
      cv2.circle(show_img, (int(sx),int(sy)), int(star_obj['radius'])+2, (128,128,128),1)
      cv2.circle(show_img, (int(sx),int(sy)), int(star_obj['radius'])+4, (128,128,128),1)



      desc = str(int(star_obj['star_yn'])) + "%"
      desc2 = str(int(star_obj['star_flux']))  #+ " / " + str(len(star_obj['cnts'])) + " / " + str(star_obj['radius'])
      cv2.putText(show_img, desc,  (star_obj['x1'],star_obj['y2']+10), cv2.FONT_HERSHEY_SIMPLEX, .4, (200,200,200), 1)
      cv2.putText(show_img, desc2,  (star_obj['x1'],star_obj['y1']-10), cv2.FONT_HERSHEY_SIMPLEX, .4, (200,200,200), 1)
      for key in star_obj:
         print("   STAR: ", key, star_obj[key])



   if SHOW == 1:
      cv2.imshow('pepe', show_img)
      cv2.waitKey(30)
   return(star_points)


def get_stars_from_image(oimg, cp):
   cat_image_stars = cp['cat_image_stars']
   cal_fn = cp['cal_fn']
   image_stars = []
   star_objs = []
   # make list of star points from cat stars and whatever else we can find
   gray_orig = cv2.cvtColor(oimg, cv2.COLOR_BGR2GRAY)
   gray_img = cv2.cvtColor(oimg, cv2.COLOR_BGR2GRAY)
   for star in cat_image_stars:
      (dcname,mag,ra,dec,img_ra,img_dec,match_dist,up_cat_x,up_cat_y,img_az,img_el,up_cat_x,up_cat_y,six,siy,res_px,bp) = star
      x1 = int(six - 25)
      x2 = int(six + 25)
      y1 = int(siy - 25)
      y2 = int(siy + 25)
      if x1 < 0:
         x1 = 0
      if y1 < 0:
         y1 = 0
      if x2 >= 1920:
         x2 = 1920 
      if y2 >= 1080:
         y2 = 1080
      gray_img[y1:y2,x1:x2] = 0
      image_stars.append((six,siy,bp))
      if SHOW == 1:
         cv2.imshow("pepe", gray_img)
         cv2.waitKey(30)

   show_img = oimg.copy()
   # check top 100 brightest points in the image
   for i in range(0,200):
      if SHOW == 1:
         cv2.imshow("gray", gray_img)
      min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(gray_img)
      resp = make_star_roi(mx,my,32)
      sbx = mx
      sby = my
      status,x1,y1,x2,y2 = resp
      valid = False
      if status is True:
         crop_img = gray_orig[y1:y2,x1:x2]
         avg_val = np.mean(crop_img)
         min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(crop_img)
         pxd = max_val - avg_val

         _, crop_thresh = cv2.threshold(crop_img, max_val * .85, 255, cv2.THRESH_BINARY)
         cnts = get_contours_in_image(crop_thresh)

         if pxd > 20 and len(cnts) == 1:
            valid = True

         if len(cnts) == 1:
            x,y,w,h = cnts[0]
            cx = x + (w/2)
            cy = y + (h/2)
            if w > h:
               radius = w
            else:
               radius = h
            try:
               star_flux = do_photo(crop_img, (cx,cy), radius)
            except:
               star_flux = 0
            if star_flux > 0:
               #star_yn = ai_check_star(crop_img, cal_fn)
               star_yn = -1 
            else:
               star_yn = -1 
               valid = False
         else:
            valid = False

         if valid is True:

            print("FLUX / YN:", star_flux, star_yn)

            star_obj = {}
            star_obj['cal_fn'] = cp['cal_fn'] 
            star_obj['x'] = x1 + (x) + (w/2)
            star_obj['y'] = y1 + (y) + (h/2)
            star_obj['star_flux'] = star_flux
            star_obj['star_yn'] = star_yn
            star_obj['star_radius'] = radius
            image_stars.append((star_obj['x'], star_obj['y'], star_obj['star_flux']))
            star_objs.append(star_obj)
            desc = str(int(star_flux)) + " " + str(int(star_yn))
            if SHOW == 1:
               if star_yn > 90:
                  print("ST:", star_yn)
                  cv2.putText(show_img, desc,  (x1,y1), cv2.FONT_HERSHEY_SIMPLEX, .4, (128,128,128), 1)
                  cv2.rectangle(show_img, (int(x1), int(y1)), (int(x2) , int(y2) ), (255, 255, 255), 1)
               else:
                  print("ST:", star_yn)
                  cv2.putText(show_img, desc,  (x1,y1), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,0,0), 1)
                  cv2.rectangle(show_img, (int(x1), int(y1)), (int(x2) , int(y2) ), (0, 0, 0), 1)
               print(star_obj)
               if SHOW == 1:
                  cv2.imshow("pepe", show_img)
                  cv2.waitKey(30)

      gray_img[y1:y2,x1:x2] = 0
   if SHOW == 1:
      cv2.imshow("pepe", show_img)
      cv2.waitKey(30)
   return(image_stars, star_objs)

def catalog_image(cal_fn, con, cur, json_conf,mcp=None, add_more=False,del_more=False ):
   fine_tune = False
   (f_datetime, cam_id, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(cal_fn)

   if SHOW == 1:
      cv2.namedWindow("pepe")
      cv2.resizeWindow("pepe", 1920, 1080)

   calfiles_data = load_cal_files(cam_id , con, cur )

   resp = start_calib(cal_fn, json_conf, calfiles_data, mcp)
   if resp is False:
      print(resp)
      print("start Calib failed!")
      return(False)
   else:
      (station_id, cal_dir, cal_json_file, cal_img_file, cal_params, cal_img, clean_cal_img, mask_file,mcp) = resp


   if fine_tune is True:
      if cal_params['total_res_px'] > 20:
         tuner = 10
      elif 10 < cal_params['total_res_px'] <= 20:
         tuner = 100
      else:
         tuner = 1000
      if len(cal_params['cat_image_stars']) is None:
         print("BAD CAL: NO CAT IMAGE STARS!")
         print(cal_dir + cal_fn)
         exit()
      if len(cal_params['cat_image_stars']) >80:
         add_more = False

      print("TUNE:", len(cal_params['cat_image_stars']), cal_params['total_res_px'], tuner)
      new_cal_params, report_txt, show_img = cal_params_report(cal_fn, cal_params, json_conf, clean_cal_img.copy(), 30, mcp)

      # AUTO TWEEK THE CAL!

      best_res_px = new_cal_params['total_res_px']
      best_res_deg = new_cal_params['total_res_deg']
      best_az = 9999
      best_el = 9999
      best_ra = 9999
      best_dec = 9999
      best_pos = 9999
      best_pxs = 9999

      if len(cal_params['cat_image_stars']) > 60 and cal_params['total_res_px'] > 10:
         cal_params, del_stars = delete_bad_stars (cal_fn, cal_params, con,cur,json_conf)
   
      if cal_params['cat_image_stars'] == 0:
         print(cal_params)
         print("NO STARS FAIL")
         exit()

      for i in range(-10,10):
         v = i / tuner
         nc = cal_params.copy()
         nc['center_az'] = nc['center_az'] + v
         nc = update_center_radec(cal_fn,nc,json_conf)
         nc, report_txt, show_img = cal_params_report(cal_fn, nc, json_conf, clean_cal_img.copy(), 30, mcp)
         if nc['total_res_px'] < best_res_px:
            best_res_px = nc['total_res_px']
            best_res_deg = nc['total_res_deg']
            best_az = nc['center_az']
            best_ra = nc['ra_center']
            best_dec = nc['dec_center']
            print("BEST!", best_az, best_ra)
         print("CAT IMAGE RES PX/RES DEG", nc['total_res_px'], nc['total_res_deg'])

      if best_az != 9999:
         print("UPDATE BETTER CAL")
         cal_params = nc.copy()
         cal_params['center_az'] = best_az
         cal_params['ra_center'] = best_ra
         cal_params['dec_center'] = best_dec
         cal_params['total_res_px'] = best_res_px 
         cal_params['total_res_deg'] = best_res_deg 

      cal_params, report_txt, show_img = cal_params_report(cal_fn, cal_params, json_conf, clean_cal_img.copy(), 30, mcp)
      best_res_px = cal_params['total_res_px']


      for i in range(-10,10):
         v = i / tuner
         nc = cal_params.copy()
         nc['center_el'] = nc['center_el'] + v
         nc = update_center_radec(cal_fn,nc,json_conf)
         nc, report_txt, show_img = cal_params_report(cal_fn, nc, json_conf, clean_cal_img.copy(), 30, mcp)
         if nc['total_res_px'] < best_res_px:
            best_res_px = nc['total_res_px']
            best_el = nc['center_el']
            best_ra = nc['ra_center']
            best_dec = nc['dec_center']
            print("BEST!", best_el, best_ra)
         #print("RES", nc['total_res_px'], nc['total_res_deg'])

      if best_el != 9999:
         print("UPDATE BETTER CAL")
         cal_params = nc.copy()
         cal_params['center_el'] = best_el
         cal_params['ra_center'] = best_ra
         cal_params['dec_center'] = best_dec
         cal_params['total_res_px'] = best_res_px 
         cal_params['total_res_deg'] = best_res_deg 


      cal_params, report_txt, show_img = cal_params_report(cal_fn, cal_params, json_conf, clean_cal_img.copy(), 30, mcp)
      best_res_px = cal_params['total_res_px']

      for i in range(-10,10):
         v = i / tuner
         nc = cal_params.copy()
      
         nc['position_angle'] = nc['position_angle'] + v
         nc = update_center_radec(cal_fn,nc,json_conf)
         nc, report_txt, show_img = cal_params_report(cal_fn, nc, json_conf, clean_cal_img.copy(), 30, mcp)
         if nc['total_res_px'] < best_res_px:
            best_res_px = nc['total_res_px']
            best_pos = nc['position_angle']
            best_ra = nc['ra_center']
            best_dec = nc['dec_center']
            print("BEST!", best_pos, best_ra, best_dec)
         #print("RES", nc['total_res_px'], nc['total_res_deg'])

      if best_pos != 9999:
         print("UPDATE BETTER CAL")
         cal_params = nc.copy()
         cal_params['position_angle'] = best_pos
         cal_params['ra_center'] = best_ra
         cal_params['dec_center'] = best_dec
         cal_params['total_res_px'] = best_res_px 
         cal_params['total_res_deg'] = best_res_deg 

      cal_params, report_txt, show_img = cal_params_report(cal_fn, cal_params, json_conf, clean_cal_img.copy(), 30, mcp)
      best_res_px = cal_params['total_res_px']
      print("LAST BEST:", best_res_px)

      for i in range(-10,10):
         v = i / tuner
         nc = cal_params.copy()
         nc['pixscale'] = nc['pixscale'] + v
         nc = update_center_radec(cal_fn,nc,json_conf)
         nc, report_txt, show_img = cal_params_report(cal_fn, nc, json_conf, clean_cal_img.copy(),30,mcp)
         if nc['total_res_px'] < best_res_px:
            best_res_px = nc['total_res_px']
            best_pxs = nc['pixscale']
            best_ra = nc['ra_center']
            best_dec = nc['dec_center']
            print("BEST!", best_pxs, best_ra, best_dec)
         #print("RES", nc['total_res_px'], nc['total_res_deg'])

      if best_pxs != 9999:
         print("UPDATE BETTER CAL")
         cal_params['pixscale'] = best_pxs
         cal_params['total_res_px'] = best_res_px 
         cal_params['total_res_deg'] = best_res_deg 

      print("DONE")
      cal_params = update_center_radec(cal_fn,cal_params,json_conf)
      # final before delete
      cal_params, report_txt, show_img = cal_params_report(cal_fn, cal_params, json_conf, clean_cal_img.copy(), 30, mcp)
      best_res_px = cal_params['total_res_px']

   # DELETE BAD STARS
   if del_more is True:
      cal_params, del_stars = delete_bad_stars (cal_fn, cal_params, con,cur,json_conf)

   # final after delete
   cal_params, report_txt, show_img = cal_params_report(cal_fn, cal_params, json_conf, clean_cal_img.copy(), 30, mcp)
   if SHOW == 1:
      cv2.imshow('pepe', show_img)
      cv2.waitKey(30)

   print("BEFORE UPDATE RES:", cal_fn, cal_params['total_res_px'], cal_params['total_res_deg'])
   cal_params = update_center_radec(cal_fn,cal_params,json_conf)
   update_calibration_file(cal_fn, cal_params, con,cur,json_conf,mcp)

   save_json_file(cal_dir + cal_fn, cal_params)


   print("AFTER UPDATE RES:", cal_dir + cal_fn, cal_params['total_res_px'], cal_params['total_res_deg'])
   #add_more = False 

   if add_more is False:
      print("WE HAVE ENOUGH STARS!")
      return()
   ### ADD MORE STARS IF WE CAN ###
   ### GET MORE STARS IF WE CAN ###
   cat_stars, short_bright_stars, cat_image = get_catalog_stars(cal_params)
   blend_img = cv2.addWeighted(show_img, .5, cat_image, .5,0)
   cat_show_img = show_img.copy()

   last_best_res = cal_params['total_res_px'] + 2

   cal_params_nlm = cal_params.copy()
   cal_params_nlm['x_poly'] = np.zeros(shape=(15,), dtype=np.float64)
   cal_params_nlm['y_poly'] = np.zeros(shape=(15,), dtype=np.float64)
   cal_params_nlm['x_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
   cal_params_nlm['y_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
   #all_res, inner_res, middle_res, outer_res = recalc_res(cal_params)
   all_res, inner_res, middle_res, outer_res,cal_params= recalc_res(cal_fn, cal_params, json_conf)


   used = {}
   new_stars = []
   for star in cal_params['cat_image_stars']: 
      (dcname,mag,ra,dec,img_ra,img_dec,match_dist,up_cat_x,up_cat_y,img_az,img_el,up_cat_x,up_cat_y,six,siy,res_px,bp) = star
      # ONLY TRY TO ADD EDGE STARS! 
      


      ra_key = str(ra) + "_" + str(dec)
      used[ra_key] = {}


   print("LAST BEST RES:", inner_res, middle_res, outer_res)
   rejected = 0
   for star in cat_stars[0:30]:
      if rejected > 20:
         print("NO MORE STARS CAN BE ADDED!")
         continue
      (name,mag,ra,dec,new_cat_x,new_cat_y,zp_cat_x,zp_cat_y) = star 
      ra_key = str(ra) + "_" + str(dec)
      rx1 = int(new_cat_x - 16)
      rx2 = int(new_cat_x + 16)
      ry1 = int(new_cat_y - 16)
      ry2 = int(new_cat_y + 16)

      if (new_cat_x < 300 or new_cat_x > 1620) and (new_cat_y < 200 or new_cat_y > 880):
         print("EDGE")
      else:
         print("NOT EDGE")
         #continue

      if rx1 <= 0 or ry1 <= 0 or rx2 >= 1920 or ry2 >= 1080:
         continue
      if ra_key in used:
         cv2.rectangle(cat_show_img, (int(rx1), int(ry1)), (int(rx2) , int(ry2) ), (0, 255, 0), 2)
      else:
         star_crop = clean_cal_img[ry1:ry2,rx1:rx2]
         star_obj = eval_star_crop(star_crop, cal_fn, rx1, ry1, rx2, ry2)
         if star_obj['valid_star'] is True:
            star_obj['cx'] = star_obj['cx'] + rx1
            star_obj['cy'] = star_obj['cy'] + ry1
            cv2.rectangle(cat_show_img, (int(rx1), int(ry1)), (int(rx2) , int(ry2) ), (128, 200, 128), 1)
            star_yn = star_obj['star_yn'] 
            img_x= star_obj['cx'] 
            img_y = star_obj['cy'] 
            bp = star_obj['star_flux']
            star_flux = star_obj['star_flux']

            res_px = calc_dist((star_obj['cx'],star_obj['cy']),(new_cat_x,new_cat_y))
            print("RE PXS/ LAST BEST RES:", res_px, last_best_res)

            center_dist = calc_dist((960,540),(img_x,img_y))
            if center_dist < 400: 
               act_res = inner_res ** 2
            elif 400 <= center_dist < 600: 
               act_res = middle_res  ** 2
            else:

               act_res = (outer_res ** 2) + outer_res

            if res_px <= act_res :
               print("ADD NEW INCLUDE:", act_res, res_px)

               new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(img_x,img_y,cal_fn,cal_params,json_conf)
               match_dist = angularSeparation(ra,dec,img_ra,img_dec)
               res_deg = match_dist
               cal_params['cat_image_stars'].append((name,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,img_x,img_y,res_px,bp)) 
               print("ADD NEW STAR!", name, res_px)

               zp_x, zp_y, zp_img_ra,zp_img_dec, zp_img_az, zp_img_el = XYtoRADec(img_x,img_y,cal_fn,cal_params_nlm,json_conf)
               zp_cat_x, zp_cat_y = get_xy_for_ra_dec(cal_params_nlm, ra, dec)

               zp_res_px = res_px
               slope = (img_y - new_cat_y) / (img_x - new_cat_x)
               zp_slope = (img_y - zp_cat_y) / (img_x - zp_cat_x)


               new_stars.append((cal_fn, name, mag, star_yn, ra, dec, star_flux, img_x, img_y, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, res_px, zp_res_px, res_deg, slope, zp_slope, star_obj['pxd']))

               cv2.rectangle(cat_show_img, (int(rx1), int(ry1)), (int(rx2) , int(ry2) ), (0,255, 0), 1)
               cv2.line(cat_show_img, (int(new_cat_x),int(new_cat_y)), (int(star_obj['cx']),int(star_obj['cy'])), (255,255,255), 2)
               cv2.putText(cat_show_img, str(round(res_px,1)) + "px",  (int(new_cat_x + 5),int(new_cat_y)), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,255,0), 1)
            else:
               # NOT VALID PER EVAL
               print("FAILED EVAL!", star_obj)
               print("REJECT:", act_res, res_px)
               cv2.putText(cat_show_img, str(round(res_px,1)) + "px",  (int(new_cat_x + 5),int(new_cat_y)), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,0,128), 1)
               cv2.rectangle(cat_show_img, (int(rx1), int(ry1)), (int(rx2) , int(ry2) ), (0,0, 255), 1)
         else:

            print("REJECT: not valid" )
            for key in star_obj:
               print(key, star_obj[key])

            cv2.putText(cat_show_img, "X",  (int(rx1),int(ry1)), cv2.FONT_HERSHEY_SIMPLEX, .5, (0,0,255), 2)
            rejected += 1
            continue
            #cv2.putText(cat_show_img, str(round(res_px,1)) + "px",  (int(new_cat_x + 5),int(new_cat_y)), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,0,255), 1)
            cv2.rectangle(cat_show_img, (int(rx1), int(ry1)), (int(rx2) , int(ry2) ), (64,64, 128), 1)
         if SHOW == 1:
            cv2.imshow('pepe', cat_show_img)
            cv2.waitKey(10)


   update_calibration_file(cal_fn, cal_params, con,cur,json_conf,mcp)


   save_json_file(cal_dir + cal_fn, cal_params)

   if SHOW == 1:      
      cv2.imshow('pepe', blend_img)
      cv2.waitKey(100)

      cv2.imshow('pepe', cat_show_img)
      cv2.waitKey(30)



   # INSERT NEW STARS!
   for star in new_stars:
      (cal_fn, name, mag, star_yn, ra, dec, star_flux, img_x, img_y, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, res_px, zp_res_px, res_deg, slope, zp_slope,star_pd) = star

      zp_x, zp_y, zp_img_ra,zp_img_dec, zp_img_az, zp_img_el = XYtoRADec(img_x,img_y,cal_fn,cal_params_nlm,json_conf)
      zp_cat_x, zp_cat_y = get_xy_for_ra_dec(cal_params_nlm, ra, dec)

      zp_res_px = calc_dist((img_x,img_y), (zp_cat_x,zp_cat_y))
      star_obj["cal_fn"] = cal_fn
      star_obj["name"]  = name
      star_obj["mag"] = mag
      star_obj["ra"]  = ra 
      star_obj["dec"] = dec
      star_obj["new_cat_x"] = new_cat_x 
      star_obj["new_cat_y"] = new_cat_y 
      star_obj["zp_cat_x"]  = zp_cat_x 
      star_obj["zp_cat_y"] = zp_cat_y 
      star_obj["img_x"] = img_x 
      star_obj["img_y"] = img_y 
      star_obj["star_flux"] = star_flux 
      star_obj["star_yn"]  = star_yn 
      star_obj["star_pd"] = star_pd 
      star_obj["star_found"] = 1 
      if mcp is None:
         star_obj["lens_model_version"] = 1
      else:
         star_obj["lens_model_version"] = mcp['cal_version']
      star_obj["slope"] = slope
      star_obj["zp_slope"] = zp_slope
      star_obj["res_px"] = res_px
      star_obj["zp_res_px"] = zp_res_px
      star_obj["res_deg"] = res_deg
      #print("INSERT NEW STAR!", star_obj)
      insert_paired_star(cal_fn, star_obj, con, cur, json_conf )
   return(cal_params)

def recalc_res(cal_fn, cal_params, json_conf):
   all_deg = []
   all_res = []
   inner_res = []
   middle_res = []
   outer_res = []
   updated_stars = []

   cal_params = update_center_radec(cal_fn,cal_params,json_conf)

   for star in cal_params['cat_image_stars']:
      (dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,res_px,bp) = star
      center_dist = calc_dist((960,540),(six,siy))
      
      new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(six,siy,cal_fn,cal_params,json_conf)
      new_cat_x,new_cat_y = get_xy_for_ra_dec(cal_params, ra, dec)

      res_px = calc_dist((six,siy), (new_cat_x,new_cat_y))
      match_dist = angularSeparation(ra,dec,img_ra,img_dec)

      updated_stars.append((dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,res_px,bp))

      all_res.append(res_px)
      all_deg.append(match_dist)
      if center_dist < 400:
         inner_res.append(res_px)
      elif 400 <= center_dist < 800:
         middle_res.append(res_px)
      else:
         outer_res.append(res_px)
   if len(all_res) > 3:
      all_res_mean = np.mean(all_res)
   else:
      all_res_mean = 5

   if len(inner_res) > 3:
      inner_res_mean = np.mean(inner_res)
   else:
      inner_res_mean = 5

   if len(middle_res) > 3:
      middle_res_mean = np.mean(middle_res)
   else:
      middle_res_mean = 15

   if len(outer_res) > 3:
      outer_res_mean = np.mean(outer_res)
   else:
      outer_res_mean = 36 

   if inner_res_mean < 5:
      inner_res_mean = 5 

   cal_params['cat_image_stars'] = updated_stars
   cal_params['total_res_px'] = np.mean(all_res)
   cal_params['total_res_deg'] = np.mean(all_deg)
   return(all_res_mean, inner_res_mean, middle_res_mean, outer_res_mean, cal_params)

def delete_bad_stars (cal_fn, cal_params, con,cur,json_conf, factor =2):
   new_stars = []
   del_stars = []



   all_res, inner_res, middle_res, outer_res,cal_params = recalc_res(cal_fn, cal_params, json_conf)
   print(all_res, inner_res, middle_res, outer_res)
   mean_all_res = all_res
   if np.isnan(outer_res) :
      outer_res = 35
   print("ALL RES:", all_res)
   print("INNER RES:", inner_res)
   print("MIDDLE RES:", middle_res)
   print("OUTER RES:", outer_res)

   if sum(cal_params['x_poly'] ) == 0:
      first_time_cal = True
   else:
      first_time_cal = False 
   print("FIRST TIME CAL?:", first_time_cal)

   if all_res > 10:
      factor = 2 
   else:
      factor = 2 

   if first_time_cal is True:
      factor = 4 


   for star in cal_params['cat_image_stars']:
      (dcname,mag,ra,dec,img_ra,img_dec,match_dist,up_cat_x,up_cat_y,img_az,img_el,up_cat_x,up_cat_y,six,siy,res_px,bp) = star
      center_dist = calc_dist((960,540),(six,siy))
      if center_dist < 400:
         dist_limit =  inner_res ** factor 
         if dist_limit > 6:
            dist_limit = 6 
      elif 400 <= center_dist < 800:
         dist_limit =  middle_res ** factor
         if dist_limit > 10:
            dist_limit = 10
      else:
         dist_limit =  outer_res ** factor
         if dist_limit > 20:
            dist_limit = 20

      if dist_limit < 1:
         dist_limit = 2

      if star[-2] < dist_limit :
         print("KEEP", dist_limit, star[-2])
         new_stars.append(star)
      else:
         print("DELETE", dist_limit, star[-2])
         del_stars.append(star)
         sql = """DELETE FROM calfile_paired_stars 
                   WHERE ra = ?
                     AND dec = ?
                  AND cal_fn = ?
         """
         dvals = [ra, dec, cal_fn]
         cur.execute(sql, dvals)
   con.commit()
   cal_params['cat_image_stars'] = new_stars
   return(cal_params, del_stars)
 

def create_star_catalog_table(con, cur):
   #   (name,mag,ra,dec,new_cat_x,new_cat_y,zp_cat_x,zp_cat_y) = star
   sql = """
         DROP TABLE IF EXISTS "calfile_catalog_stars";
         CREATE TABLE IF NOT EXISTS "calfile_catalog_stars" (
            cal_fn text,
            name text,
            mag real,
            ra real,
            dec real,
            new_cat_x real,
            new_cat_y real,
            zp_cat_x real,
            zp_cat_y real,
            img_x real,
            img_y real,
            star_flux real,
            star_yn real,
            star_pd integer,
            star_found integer DEFAULT 0,
            lens_model_version integer,
            PRIMARY KEY(cal_fn,ra,dec)
         )

   """

def get_xy_for_ra_dec(cal_params, ra, dec):
   # pass in cal_params and ra, dec 
   # get back x,y!

   MAG_LIMIT = 8
   img_w = 1920
   img_h = 1080
   # setup astrometry and lens model variables
   catalog_stars = []
   cal_params['imagew'] = img_w
   cal_params['imageh'] = img_h 
   RA_center = float(cal_params['ra_center'])
   dec_center = float(cal_params['dec_center'])
   F_scale = 3600/float(cal_params['pixscale'])
   if "x_poly" in cal_params:
      x_poly = cal_params['x_poly']
      y_poly = cal_params['y_poly']
      x_poly_fwd = cal_params['x_poly_fwd']
      y_poly_fwd = cal_params['y_poly_fwd']
   else:
      x_poly = np.zeros(shape=(15,), dtype=np.float64)
      y_poly = np.zeros(shape=(15,), dtype=np.float64)
      x_poly_fwd = np.zeros(shape=(15,), dtype=np.float64)
      y_poly_fwd = np.zeros(shape=(15,), dtype=np.float64)

   zp_x_poly = np.zeros(shape=(15,), dtype=np.float64)
   zp_y_poly = np.zeros(shape=(15,), dtype=np.float64)

   fov_w = img_w / F_scale
   fov_h = img_h / F_scale
   fov_radius = np.sqrt((fov_w/2)**2 + (fov_h/2)**2)

   pos_angle_ref = cal_params['position_angle']
   x_res = int(cal_params['imagew'])
   y_res = int(cal_params['imageh'])

   center_x = int(x_res / 2)
   center_y = int(y_res / 2)
   new_cat_x, new_cat_y = distort_xy(0,0,ra,dec,RA_center, dec_center, x_poly, y_poly, x_res, y_res, pos_angle_ref,F_scale)

   return(new_cat_x, new_cat_y)

def get_catalog_stars(cal_params):
   mybsd = bsd.brightstardata()
   bright_stars = mybsd.bright_stars
   #if "short_bright_stars" not in cal_params :
   #   mybsd = bsd.brightstardata()
   #   bright_stars = mybsd.bright_stars
   #else:
   #   bright_stars = cal_params['short_bright_stars']

   cat_image = np.zeros((1080,1920,3),dtype=np.uint8)

   MAG_LIMIT = 8
   img_w = 1920
   img_h = 1080
   # setup astrometry and lens model variables
   catalog_stars = []
   cal_params['imagew'] = img_w
   cal_params['imageh'] = img_h 
   RA_center = float(cal_params['ra_center'])
   dec_center = float(cal_params['dec_center'])
   F_scale = 3600/float(cal_params['pixscale'])
   if "x_poly" in cal_params:
      x_poly = cal_params['x_poly']
      y_poly = cal_params['y_poly']
      x_poly_fwd = cal_params['x_poly_fwd']
      y_poly_fwd = cal_params['y_poly_fwd']
   else:
      x_poly = np.zeros(shape=(15,), dtype=np.float64)
      y_poly = np.zeros(shape=(15,), dtype=np.float64)
      x_poly_fwd = np.zeros(shape=(15,), dtype=np.float64)
      y_poly_fwd = np.zeros(shape=(15,), dtype=np.float64)

   zp_x_poly = np.zeros(shape=(15,), dtype=np.float64)
   zp_y_poly = np.zeros(shape=(15,), dtype=np.float64)

   fov_w = img_w / F_scale
   fov_h = img_h / F_scale
   fov_radius = np.sqrt((fov_w/2)**2 + (fov_h/2)**2)

   pos_angle_ref = cal_params['position_angle']
   x_res = int(cal_params['imagew'])
   y_res = int(cal_params['imageh'])

   center_x = int(x_res / 2)
   center_y = int(y_res / 2)

   bright_stars_sorted = sorted(bright_stars, key=lambda x: x[4], reverse=False)

   sbs = []
   for data in bright_stars_sorted:
      bname, cname, ra, dec, mag = data
      name = bname
      if mag > MAG_LIMIT:
         continue

      # decode name when needed
      if isinstance(name, str) is True:
         name = name
      else:
         name = name.decode("utf-8")

      # calc ang_sep of star's ra/dec from fov center ra/dec
      ang_sep = angularSeparation(ra,dec,RA_center,dec_center)
      if ang_sep < fov_radius and float(mag) <= MAG_LIMIT:
         sbs.append((name, name, ra, dec, mag))

         # get the star position with no distortion
         zp_cat_x, zp_cat_y = distort_xy(0,0,ra,dec,RA_center, dec_center, zp_x_poly, zp_y_poly, x_res, y_res, pos_angle_ref,F_scale)
         new_cat_x, new_cat_y = distort_xy(0,0,ra,dec,RA_center, dec_center, x_poly, y_poly, x_res, y_res, pos_angle_ref,F_scale)
         if zp_cat_x > 0 and zp_cat_y > 0 and zp_cat_x < 1920 and zp_cat_y < 1080:
            good = 1 
         else:
            continue

         catalog_stars.append((name,mag,ra,dec,new_cat_x,new_cat_y,zp_cat_x,zp_cat_y))
         if mag <= 5.5:
            cv2.line(cat_image, (int(new_cat_x),int(new_cat_y)), (int(zp_cat_x),int(zp_cat_y)), (255,255,255), 2)
            if new_cat_x < 300:
               rx1 = new_cat_x - 10
               rx2 = new_cat_x + 40
               ry1 = new_cat_y - 10 
               ry2 = new_cat_y + 40
            elif new_cat_x > 1620:
               rx1 = new_cat_x - 40
               rx2 = new_cat_x + 10
               ry1 = new_cat_y - 40 
               ry2 = new_cat_y + 10
            else:
               rx1 = new_cat_x - 25
               rx2 = new_cat_x + 25
               ry1 = new_cat_y - 25
               ry2 = new_cat_y + 25
            cv2.rectangle(cat_image, (int(rx1), int(ry1)), (int(rx2) , int(ry2) ), (255, 255, 255), 2)

   if len(catalog_stars) == 0:
      print("NO CATALOG STARS!?")

   catalog_stars = sorted(catalog_stars, key=lambda x: x[1], reverse=False)
   return(catalog_stars, sbs, cat_image)

def ai_check_star(img, img_file):

   # SHOULD CHACHE THESE!! 
   # AND LEARN FROM THEM 
   if os.path.exists(img_file) is False:
      temp_file = "/mnt/ams2/tempstar.jpg"
      cv2.imwrite(temp_file, img)
   else:
      temp_file = img_file

   url = "http://localhost:5000/AI/STAR_YN/?file={}".format(temp_file)
   if True:
      response = requests.get(url)
      content = response.content.decode()
      resp = json.loads(content)
   return(resp['star_yn'])

def do_photo(image, position, radius,r_in=10, r_out=12):
   #print("SHAPE:", image.shape)
   #print("POSITION,RADIUS", position, radius)
   if radius < 2:
      radius = 2

   if False:
      # debug display
      xx,yy = position
      xx = int(xx * 10)
      yy = int(yy * 10)

      disp_img = cv2.resize(image, (320,320))
      min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(disp_img)
      avg_val = np.mean(disp_img)
      pxd = max_val - avg_val 
      thresh_val = int(avg_val + (max_val/2))
      if thresh_val > max_val:
         thresh_val = max_val * .8

      _, thresh_image = cv2.threshold(disp_img, thresh_val, 255, cv2.THRESH_BINARY)
   
      #cv2.circle(disp_img, (int(xx),int(yy)), int(radius * 10), (128,128,128),1)
      #cv2.circle(disp_img, (int(xx),int(yy)), int((radius+2) * 10), (99,99,99),1)
      #cv2.circle(disp_img, (int(xx),int(yy)), int((radius+4) * 10), (88,88,88),1)
 
      #cv2.imshow("photo", disp_img)
      #cv2.waitKey(30)
      #cv2.imshow("thresh", thresh_image)
      #cv2.waitKey(30)
   r_in = radius + 2
   r_out = radius + 4

   aperture_area = np.pi * radius**2
   annulus_area = np.pi * (r_out**2 - r_in**2)

   # pass in BW crop image centered around the star
   
   aperture = CircularAperture(position,r=radius)
   bkg_aperture = CircularAnnulus(position,r_in=r_in,r_out=r_out)



   phot = aperture_photometry(image, aperture)
   bkg = aperture_photometry(image, bkg_aperture)

   #print("PH", phot['aperture_sum'][0])
   #print("BK", bkg['aperture_sum'][0])

   
   bkg_mean = bkg['aperture_sum'][0] / annulus_area
   bkg_sum = bkg_mean * aperture_area

   #print("AP AREA:", aperture_area)
   #print("AN AREA:", annulus_area)
   #print("BKG MEAN:", bkg_mean)
   #print("BKG SUM:", bkg_sum)

   flux_bkgsub = phot['aperture_sum'][0] - bkg_sum

   if SHOW == 1:
      xx,yy = position
      #cv2.putText(image, "T" + str(flux_bkgsub),  (int(xx),int(yy)), cv2.FONT_HERSHEY_SIMPLEX, .4, (255,255,255), 1)
      #cv2.circle(image, (int(xx),int(yy)), int(radius ), (128,128,128),1)
      #cv2.imshow("PPP", image)
      #cv2.waitKey(30)



   return(flux_bkgsub)

def get_contours_in_image(frame ):
   ih, iw = frame.shape[:2]

   cont = []
   if len(frame.shape) > 2:
      frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
   cnt_res = cv2.findContours(frame.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
   if len(cnt_res) == 3:
      (_, cnts, xx) = cnt_res
   elif len(cnt_res) == 2:
      (cnts, xx) = cnt_res
   for (i,c) in enumerate(cnts):
      x,y,w,h = cv2.boundingRect(cnts[i])
      if (w >= 1 or h >= 1) and (w < 10 and h < 10):
         cont.append((x,y,w,h))


   return(cont)

def cal_dir_from_file(cal_file):
   freecal_dir = "/mnt/ams2/cal/freecal/" 
   #2022_05_18_06_32_03_000_010001-stacked-fit.jpg
   if "trim" not in cal_file:
      cal_root_fn = cal_file.split("-")[0]
   else:
      print("CAL FILE:", cal_file)
      cal_root_fn = cal_file 
   
   cal_dir = freecal_dir + cal_root_fn + "/"
   if os.path.isdir(cal_dir):
      return(cal_dir)
   else:
      return(False)

def get_cal_json_file(cal_dir):
   if cal_dir is False:
      return()
   files = glob.glob(cal_dir + "*calparams.json")
   #print("(get_cal_json_file) CAL DIR", files)
   if len(files) == 1:
      return(files[0])
   else:
      return(False)

def make_star_roi(x,y,size):
   x1 = int(x - (size/2))
   x2 = int(x + (size/2))
   y1 = int(y - (size/2))
   y2 = int(y + (size/2))
   status = True
   if True:
      if x1 <= 0:
         x1 = 0
         x2 = size
         status = False 
      if x2 >= 1920:
         x1 = 1920 - size 
         x2 = 1920
         status = False 
      if y1 <= 0:
         y1 = 0
         y2 = size
         status = False 
      if y2 >= 1080:
         y1 = 1080 - size 
         y2 = 1080 
         status = False 
      return(status, x1,y1,x2,y2)

def get_mcp(cam_id) :

   autocal_dir = "/mnt/ams2/cal/"
   mcp_file = autocal_dir + "multi_poly-" + station_id + "-" + cam_id + ".info"
   if os.path.exists(mcp_file) == 1:
      mcp = load_json_file(mcp_file)
      if "cal_version" not in mcp:
         mcp['cal_version'] = 0
   else:
      mcp = None
   if mcp is None:
      print("Can't update until the MCP is made!")
   else:
      if type(mcp['cal_version']) != int:
         mcp['cal_version'] = 1
      
   return(mcp)

def batch_apply(cam_id, con,cur, json_conf, last=None, do_bad=False):
   print("DO BAD:", do_bad)
   # apply the latest MCP Poly to each cal file and then recenter them
   autocal_dir = "/mnt/ams2/cal/"
   station_id = json_conf['site']['ams_id']
   if SHOW == 1:
      cv2.namedWindow("pepe")
      cv2.resizeWindow("pepe", 1920, 1080)

   #if cam_id == "all":
   if cam_id == "all":
      cams_list = []
      for cam_num in json_conf['cameras']:
         cam_id = json_conf['cameras'][cam_num]['cams_id']
         cams_list.append(cam_id)
   else:
      cams_list = [cam_id]
   if True:
      for cam_id in cams_list:
         #cam_id = json_conf['cameras'][cam_num]['cams_id']

         if last is None:
            calfiles_data = load_cal_files(cam_id, con, cur)
         else:
            calfiles_data = load_cal_files(cam_id, con, cur, False, last)
         print(len(calfiles_data), "ok")
         mcp_file = autocal_dir + "multi_poly-" + station_id + "-" + cam_id + ".info"
         if os.path.exists(mcp_file) == 1:
            mcp = load_json_file(mcp_file)
            if "cal_version" not in mcp:
               mcp['cal_version'] = 0
         else:
            mcp = None
         if mcp is None:
            print("Can't update until the MCP is made!")

         cff = 0
         last_cal_params = None
         rc = 0

         for cf in sorted(calfiles_data, reverse=True):
            extra_text = cf + " " + str(rc) + " of " + str(len(calfiles_data))
            last_cal_params = apply_calib (cf, calfiles_data, json_conf, mcp, last_cal_params, extra_text, do_bad)
            rc += 1


def get_image_stars_with_catalog(obs_id, cal_params, show_img):
   clean_img = show_img.copy() 
   cal_fn = obs_id
   #star_obj = eval_star_crop(crop_img, cal_fn, mcx1, mcy1, mcx2, mcy2)

   star_points = cal_params['user_stars']
   user_stars = star_points
   ic = 0
 
   print(len(star_points), "star_points")
   print(len(user_stars), "user_stars")
   #star_points, show_img = get_star_points(cal_file, oimg, cal_params, station_id, camera_id, json_conf)

   if True:
      if True:
         cat_stars, short_bright_stars, cat_image = get_catalog_stars(cal_params)
         used = {}
         if True:
            for ix,iy,ii in star_points[0:50]:
               cv2.circle(show_img, (int(ix),int(iy)), int(5), (0,255,0),1)

         all_res = []
         cat_image_stars = []
         for star in cat_stars[0:100]:
            (name,mag,ra,dec,new_cat_x,new_cat_y,zp_cat_x,zp_cat_y) = star
            cv2.putText(show_img, str(name),  (int(new_cat_x-25),int(new_cat_y-25)), cv2.FONT_HERSHEY_SIMPLEX, .6, (255,255,255), 1)
            cv2.rectangle(show_img, (int(new_cat_x-25), int(new_cat_y-25)), (int(new_cat_x+25) , int(new_cat_y+25) ), (255, 255, 255), 1)

            # find closest image star!
            dist_arr = []
            # sort by brightest points
            star_points = sorted(star_points, key=lambda x: x[2], reverse=True)
            for ix,iy,ii in star_points[0:100]:
               this_dist = calc_dist((ix,iy),(new_cat_x,new_cat_y))
               if this_dist < 100:
                  print("STAR POINTS DIST:", this_dist)
                  dist_arr.append((this_dist, star, ii))
            dist_arr = sorted(dist_arr, key=lambda x: x[0], reverse=False)
            if len(dist_arr) > 0:
               closest_star = dist_arr[0][1]
               star_x = closest_star[4]
               star_y = closest_star[5]
               flux = dist_arr[0][2]
               res = dist_arr[0][0]
               all_res.append(res)


               x1 = int(star_x - 16)
               x2 = int(star_x + 16)
               y1 = int(star_y - 16)
               y2 = int(star_y + 16)
               if x1 < 0:
                  x1 = 0
                  x2 = 32
               if y1 < 0:
                  y1 = 0
                  y2 = 32
               if x2 > 1920:
                  x2 = 1920 
                  x1 = 1920 - 32
               if y2 > 1080:
                  y2 = 1080
                  y1 = 1080 - 32
               crop_img = clean_img[y1:y2,x1:x2]
               star_obj = eval_star_crop(crop_img, cal_fn, x1, y1, x2, y2)
               #print(star_obj)

               new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(new_cat_x,new_cat_y,obs_id,cal_params,json_conf)
               img_new_cat_x, img_new_cat_y = get_xy_for_ra_dec(cal_params, img_ra, img_dec)
               try:
                  match_dist = angularSeparation(ra,dec,img_ra,img_dec)
               except:
                  match_dist = 9999
               #cat_image_stars.append((name_ascii,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,x,y,res_px,flux))
               #print("PRINT STAR X,YS:", star_x, star_y, new_cat_x, new_cat_y)
               cv2.circle(show_img, (int(star_x),int(star_y)), 20, (255,0,0),2)
               star_obj['name'] = name
               star_obj['mag'] = mag
               star_obj['ra'] = ra
               star_obj['dec'] = dec
               star_obj['new_cat_x'] = new_cat_x
               star_obj['new_cat_y'] = new_cat_y
               star_obj['img_x'] = star_obj['star_x']
               star_obj['img_y'] = star_obj['star_y']

               star_obj['img_ra'] = img_ra 
               star_obj['img_dec'] = img_dec 
               star_obj['img_az'] = img_az
               star_obj['img_el'] = img_el
               star_obj['zp_cat_x'] = zp_cat_x 
               star_obj['zp_cat_y'] = zp_cat_y 
               star_obj['star_pd'] = 999 
               star_obj['lens_model_version'] = 999 
               print("STAR OBJ:", name, star_obj['valid_star'])
               res_px = calc_dist((star_obj['star_x'],star_obj['star_y']), (new_cat_x,new_cat_y))
               if res_px < 15: 
                  print("ADDING CAT STAR:", name, res_px)
                  cat_image_stars.append((name,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,star_obj['star_x'],star_obj['star_y'],res_px,star_obj['star_flux']))
                  user_stars.append((star_obj['star_x'], star_obj['star_y'], star_obj['star_flux']))
               else:
                  print("SKIPPING CAT STAR:", name, res_px)

               #insert_paired_star(cal_fn, star_obj, con, cur, json_conf)

               ic += 1
            else:
               print("No close star found.")
               #try:
               #   cur.execute(sql, ivals)
               #except:
               #   print("Must be done already")

               #print("CLOSEST MATCH:", res, closest_star)
   #con.commit()
   if SHOW == 1:
      cv2.imshow('pepe', show_img)
      cv2.waitKey(30)
   
   temp = []
   if True:
      rez = np.median([row[-2] for row in cal_params['cat_image_stars']])
      if rez < 1:
         rez = 1
      for row in cal_params['cat_image_stars']:
         if row[-2] < rez * 2:
            print("add good res:", row[-2])
            temp.append(row)
         else:
            print("skip bad res:", row[-2])

      cal_params['cat_image_stars'] = temp

   for cat_star in cat_image_stars:
      print("FINAL :", cat_star[-2])

   return(cat_image_stars, user_stars)


def apply_calib (cal_file, calfiles_data, json_conf, mcp, last_cal_params=None, extra_text= "", do_bad=False):
      cal_dir = cal_dir_from_file(cal_file)

      if cal_file in calfiles_data:
         (station_id, camera_id, cal_fn, cal_ts, az, el, ra, dec, position_angle,\
            pixel_scale, zp_az, zp_el, zp_ra, zp_dec, zp_position_angle, zp_pixel_scale, x_poly, \
            y_poly, x_poly_fwd, y_poly_fwd, res_px, res_deg, ai_weather, ai_weather_conf, cal_version, last_update) = calfiles_data[cal_file]
         cal_params = cal_data_to_cal_params(cal_file, calfiles_data[cal_file],json_conf, mcp)
      else:
         import_cal_file(cal_file, cal_dir, mcp)
         res_px = 999


      if res_px is None:
         res_px = 999
      if last_cal_params is not None and float(res_px) > 6:
         temp_cal_params = cal_params.copy()
         temp_cal_params['center_az'] = last_cal_params['center_az']
         temp_cal_params['center_el'] = last_cal_params['center_el']
         temp_cal_params['position_angle'] = last_cal_params['position_angle']
         temp_cal_params['pixscale'] = last_cal_params['pixscale']

      #show_calparams(cal_params)      
      if do_bad == True and res_px < 2:
         return(cal_params)

      print("START RES", cal_file, res_px)
      if res_px > 5:
         default_cp = get_default_cal_for_file(cam_id, cal_file, None, con, cur, json_conf)
         cal_params = default_cp
         if cal_params is None:
            print("NO CAL PARAMS!?", cam_id, cal_file)
            return(cal_params)
         cal_params= update_center_radec(cal_file,cal_params,json_conf )

      cal_image_file = cal_file.replace("-calparams.json", ".png")
      oimg = cv2.imread(cal_dir + cal_image_file)
      #print(cal_dir + cal_image_file)
      print("CF", len(calfiles_data))
      cal_img, cal_params = view_calfile(cam_id, cal_file, con, cur, json_conf,calfiles_data,cal_params,mcp)

      star_points, show_img = get_star_points(cal_file, oimg, cal_params, station_id, camera_id, json_conf)
      cal_params['user_stars'] = star_points
      cal_params['star_points'] = star_points
      if SHOW == 1:
         cv2.imshow('pepe', show_img)
         cv2.waitKey(30)

      before =  len(cal_params['cat_image_stars'])
      cal_params['cat_image_stars'], cal_params['user_stars'] = get_image_stars_with_catalog(cal_file, cal_params, oimg)

      if len(cal_params['cat_image_stars']) < 10:
         print("LOW STARS / BAD FILE MOVE")
         if os.path.exists("/mnt/ams2/cal/bad_cals/") is False:
            os.makedirs("/mnt/ams2/cal/bad_cals/")
         cmd = "mv " + cal_dir + " /mnt/ams2/cal/bad_cals/" 
         print(cmd)
         #os.system(cmd)

      temp = []
      rez = np.median([row[-2] for row in cal_params['cat_image_stars']])

      for row in cal_params['cat_image_stars']:
         #print(row)
         if row[-2] < rez * 2:
            print("add good res:", row[-2])
            temp.append(row)
         else:
            print("skip bad res:", row[-2])

      cal_params['cat_image_stars'] = temp
      cal_params['total_res_px'] = rez 
      cal_params['total_res_deg'] = (rez * (cal_params['pixscale'] / 3600) )

      print( cal_params['total_res_deg'])

      save_json_file(cal_dir + cal_file, cal_params)

      print(cal_dir + cal_file)
      print("SAVED JSON", len(cal_params['cat_image_stars']))
      # reload new data to db
      import_cal_file(cal_fn, cal_dir, mcp)


      if SHOW == 1:
         cv2.imshow('pepe', cal_img)
         cv2.resizeWindow("pepe", 1920, 1080)
     
         cv2.waitKey(30)
      if mcp is not None:
         cal_params['x_poly'] = mcp['x_poly']
         cal_params['y_poly'] = mcp['y_poly']
         cal_params['y_poly_fwd'] = mcp['y_poly_fwd']
         cal_params['x_poly_fwd'] = mcp['x_poly_fwd']
      else:
         cal_params['x_poly'] = np.zeros(shape=(15,), dtype=np.float64)
         cal_params['y_poly'] = np.zeros(shape=(15,), dtype=np.float64)
         cal_params['x_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
         cal_params['y_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)

      #if cal_version < mcp['cal_version']:
      #   print(cal_fn, "needs update!", cal_version, mcp['cal_version'])

      cat_stars, short_bright_stars, cat_image = get_catalog_stars(cal_params)
      if SHOW == 1:
         cv2.imshow('pepe', cat_image)
         cv2.waitKey(30)
    
      print("PXSCALE:", cal_params['pixscale'])

      cal_params['short_bright_stars'] = short_bright_stars
      cal_params['no_match_stars'] = [] 
      cal_image_file = cal_fn.replace("-calparams.json", ".png")
      cal_dir = cal_dir_from_file(cal_image_file)
      cal_json_file = get_cal_json_file(cal_dir)
      cal_json_fn = cal_json_file.split("/")[-1]
      oimg = cv2.imread(cal_dir + cal_image_file)
      cal_params_json = load_json_file(cal_json_file)

      print("PXSCALE:", cal_params['pixscale'])

      # this is the problem. what do we do?
      # need to load new cal stars into db before this is called in some cases?? 
      #stars,cat_stars = get_paired_stars(cal_fn, cal_params, con, cur)
      #stars = []
      #@MMM


      # Need to modes here?
      stars,cat_stars = get_paired_stars(cal_fn, cal_params, con, cur)

      print("PXSCALE:", cal_params['pixscale'])

      print("SAVED BEFORE UPDATE RECENTER", len(cal_params['cat_image_stars']))
      #for star in cal_params['cat_image_stars']:
      #   print(star)
      # BUG FOUND HERE!
     
      #cal_params= update_center_radec(cal_fn,cal_params,json_conf)

      print("PXSCALE:", cal_params['pixscale'])

      show_calparams(cal_params)
      cal_params, cat_stars = recenter_fov(cal_fn, cal_params, oimg.copy(), stars, json_conf, extra_text)

      print("PXSCALE:", cal_params['pixscale'])

      print(cal_params['total_res_px'])
      
      for star in cal_params['cat_image_stars']:
         print(star)
            
      print("SAVED JSON BEFORE UPDATE CAT STARS", len(cal_params['cat_image_stars']), len(cat_stars) )

      update_calibration_file(cal_fn, cal_params, con,cur,json_conf,mcp)
      save_json_file(cal_json_file, cal_params)
      print(cal_dir + cal_fn)
      print("SAVED JSON CAT STARS", len(cal_params['cat_image_stars']))
      #show_calparams(cal_params)      
 

      up_stars, cat_image_stars = update_paired_stars(cal_fn, cal_params, stars, con, cur, json_conf)
      cal_params['cat_image_stars'] = cat_image_stars

      save_json_file(cal_json_file, cal_params)

      #print("VIEW CAL 33:", cal_fn)
      #calfiles_data = load_cal_files(cam_id, con, cur)

      cal_img, cal_params = view_calfile(cam_id, cal_fn, con, cur, json_conf, calfiles_data, cal_params, mcp)

      #print("--------------")
      #print("AFTER VIEW CAL", cal_fn)
      #print("--------------")
      #show_calparams(cal_params)      

      #print(cal_dir + cal_fn)


      if SHOW == 1:
         cv2.imshow("pepe", cal_img)
         cv2.waitKey(30)
      #view_calib(cal_fn,json_conf, cal_params,oimg, 1)
      print("DONE APPLY")
      return(cal_params)
      #exit()

def show_calparams(cal_params):
   for key in cal_params:
      if "star" in key:
         print("CP", key, len(cal_params[key]))
      elif "poly" in cal_params:
         print("CP", key, cal_params[key][0])
      else:
         print("CP", key, cal_params[key])

def update_calfiles(cam_id, con,cur, json_conf):
   autocal_dir = "/mnt/ams2/cal/"
   station_id = json_conf['site']['ams_id']

   calfiles_data = load_cal_files(cam_id, con, cur)

   mcp_file = autocal_dir + "multi_poly-" + station_id + "-" + cam_id + ".info"
   if os.path.exists(mcp_file) == 1:
      mcp = load_json_file(mcp_file)
      if "cal_version" not in mcp:
         mcp['cal_version'] = 0
   else:
      mcp = None

   #if mcp is None:
   #   print("Can't update until the MCP is made!")

   cff = 0
   for cf in calfiles_data:
      (station_id, camera_id, cal_fn, cal_ts, az, el, ra, dec, position_angle,\
         pixel_scale, zp_az, zp_el, zp_ra, zp_dec, zp_position_angle, zp_pixel_scale, x_poly, \
         y_poly, x_poly_fwd, y_poly_fwd, res_px, res_deg, ai_weather, ai_weather_conf, cal_version, last_update) = calfiles_data[cf]
      if cal_version < mcp['cal_version']:
         print(cal_fn, "needs update!", cal_version, mcp['cal_version'])
         manual_tweek_calib(cal_fn, con, cur, json_conf, mcp, calfiles_data)

         #redo_calfile(cal_fn, con, cur, json_conf)
         #cv2.waitKey(30)
         print("ENDED HERE")
         #repair_calfile_stars(cal_fn, con, cur, json_conf, mcp)
      else:
         print(cal_fn, "is ok!", cal_version, mcp['cal_version'])
      cff += 1
      #if cff > 10:
      #   print("EXIT", cff)
         #exit()


def recenter_fov(cal_fn, cal_params, cal_img, stars, json_conf, extra_text=""):
   (f_datetime, cam_id, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(cal_fn)
   # make sure we are using the latest MCP!
   autocal_dir = "/mnt/ams2/cal/"
   mcp_file = autocal_dir + "multi_poly-" + station_id + "-" + cam_id + ".info"
   if os.path.exists(mcp_file) == 1:
      mcp = load_json_file(mcp_file)
      cal_params['x_poly'] = mcp['x_poly']
      cal_params['y_poly'] = mcp['y_poly']
      cal_params['x_poly_fwd'] = mcp['x_poly_fwd']
      cal_params['y_poly_fwd'] = mcp['y_poly_fwd']
   else:
      mcp = None


   if False: 
      cal_params['x_poly'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params['y_poly'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params['x_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params['y_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)


   this_poly = np.zeros(shape=(4,), dtype=np.float64)
   if cal_params['total_res_px'] < 1:
      this_poly = [.00001,.00001,.00001,.00001]
   elif 1 <= cal_params['total_res_px'] < 10:
      this_poly = [.0001,.0001,.0001,.0001]
   else:
      this_poly = [.001,.001,.001,.001]
  

   start_cp = dict(cal_params)
   start_res = cal_params['total_res_px']

   center_stars = []
   center_user_stars = []
   for star in cal_params['cat_image_stars']:
      dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,bp = star
      if 100 <= six <= 1820 and 100 <= siy <= 980:
         center_stars.append(star)
         center_user_stars.append((six,siy,bp))

   #extra_text = cal_fn + " "
   nc = dict(cal_params)
   #print(cal_params['center_az'],cal_params['center_el'],cal_params['position_angle'],cal_params['pixscale'])

   show_calparams(cal_params)
   res = scipy.optimize.minimize(reduce_fov_pos, this_poly, args=( np.float64(cal_params['center_az']),np.float64(cal_params['center_el']),np.float64(cal_params['position_angle']),np.float64(cal_params['pixscale']),cal_params['x_poly'], cal_params['y_poly'], cal_params['x_poly_fwd'], cal_params['y_poly_fwd'],cal_fn,cal_img,json_conf, center_stars, extra_text,0), method='Nelder-Mead')
   #print("RES FROM MINIMIZE:", res)

   #adj_az, adj_el, adj_pos, adj_px = res['x']
   this_poly = res['x']

   #print("Last poly:", this_poly)

   if type(nc['x_poly']) is not list:
      nc['x_poly'] = nc['x_poly'].tolist()
      nc['y_poly'] = nc['y_poly'].tolist()
      nc['y_poly_fwd'] = nc['y_poly_fwd'].tolist()
      nc['x_poly_fwd'] = nc['x_poly_fwd'].tolist()
   az = np.float64(cal_params['center_az'])
   el = np.float64(cal_params['center_el'])
   pos = np.float64(cal_params['position_angle'])
   pixscale = np.float64(cal_params['pixscale'])

   new_az = az + (this_poly[0]*az)
   new_el = el + (this_poly[1]*el)
   new_position_angle = pos + (this_poly[2]*pos)
   new_pixscale = pixscale + (this_poly[3]*pixscale)

   nc['center_az'] = new_az
   nc['center_el'] = new_el
   nc['position_angle'] = new_position_angle
   nc['pixscale'] = new_pixscale

   nc['total_res_px'] = res['fun']


   nc = update_center_radec(cal_fn,nc,json_conf)
   #print(""" FINAL!  AZ/EL {} {} RA/DEC {} {} POS {} PIX {} RES {}
   #""".format(nc['center_az'], nc['center_el'], nc['ra_center'], nc['dec_center'], nc['position_angle'], nc['pixscale'] , nc['total_res_px']))
 
   cat_stars, short_bright_stars, cat_image = get_catalog_stars(nc)
   #nc['short_bright_stars'] = short_bright_stars

   end_res = nc['total_res_px']
   if end_res > start_res:
      # IGNORE THE RUN!
      nc = start_cp 

   cat_stars, short_bright_stars, cat_image = get_catalog_stars(nc)

   
   up_stars, cat_image_stars = update_paired_stars(cal_fn, nc, stars, con, cur, json_conf)


   nc['cat_image_stars'] = cat_image_stars
   print("CAT IS:", len(up_stars), len(cat_image_stars))
   for star in cat_image_stars:
      print(star)
   #for star in cat_image_stars:
   #   (dcname,mag,ra,dec,img_ra,img_dec,match_dist,up_cat_x,up_cat_y,img_az,img_el,up_cat_x,up_cat_y,six,siy,res_px,bp) = star
   #   print(dcname, mag, res_px)

   # save the json file here too.
   #print("END RECENTER", nc['ra_center'], nc['dec_center'])

   return(nc, cat_stars)


def recenter_cal_file(cal_fn, con, cur, json_conf, mcp):

      cal_image_file = cal_fn.replace("-calparams.json", ".png")
      cal_dir = cal_dir_from_file(cal_image_file)
      cal_json_file = get_cal_json_file(cal_dir)
      cal_json_fn = cal_json_file.split("/")[-1]
      oimg = cv2.imread(cal_dir + cal_image_file)

      # APPLY LATEST MODEL AND RECENTER THE FOV
      # THEN SAVE THE CALP FILE AND UPDATE THE DB

      if os.path.exists(cal_json_file) is True:

         cal_params = load_json_file(cal_json_file)
         cat_stars, short_bright_stars, cat_image = get_catalog_stars(cal_params)
         cal_params['short_bright_stars'] = short_bright_stars

         view_calib(cal_fn,json_conf, cal_params,oimg, show = 0)
         this_poly = np.zeros(shape=(4,), dtype=np.float64)
         this_poly = [0,0,0,0]



         res = scipy.optimize.minimize(reduce_fov_pos, this_poly, args=( cal_params['center_az'],cal_params['center_el'],cal_params['position_angle'],cal_params['pixscale'],cal_params['x_poly'], cal_params['y_poly'], cal_image_file,oimg,json_conf, cal_params['cat_image_stars'],cal_params['user_stars'],1,SHOW,None,cal_params['short_bright_stars']), method='Nelder-Mead')
         #print("RES FROM MINIMIZE:", res)

         adj_az, adj_el, adj_pos, adj_px = res['x']

         #nc = minimize_fov(cal_fn, cal_params, cal_fn,oimg,json_conf )
         nc = cal_params.copy()

         nc['center_az'] = cal_params['center_az'] + (adj_az*cal_params['center_az'] )
         nc['center_el'] = cal_params['center_el'] + (adj_az*cal_params['center_el'] )
         nc['position_angle'] = cal_params['position_angle'] + (adj_az*cal_params['position_angle'] )
         nc['pixscale'] = cal_params['pixscale'] + (adj_az*cal_params['pixscale'] )
         nc = update_center_radec(cal_file,nc,json_conf)
         cat_stars, short_bright_stars, cat_image = get_catalog_stars(nc)
         nc['short_bright_stars'] = short_bright_stars

         print("BEFORE:")
         print("CAZ", cal_params['center_az'])
         print("CEL", cal_params['center_el'])
         print("POS", cal_params['position_angle'])
         print("PIX", cal_params['pixscale'])
         print("RES", cal_params['total_res_px'])

         print("AFTER:")

         nc['total_res_px'] = res_px
         nc['total_res_deg'] = res_deg

         print("CAZ", nc['center_az'])
         print("CEL", nc['center_el'])
         print("POS", nc['position_angle'])
         print("PIX", nc['pixscale'])
         print("RES", nc['total_res_px'])
         up_cat_image_stars = []
         for star in cal_params['cat_image_stars']:
            dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,bp = star
            sql = """
                   SELECT new_cat_x, new_cat_y 
                     FROM calfile_catalog_stars 
                    WHERE cal_fn = ? 
                      AND ra = ? 
                      AND dec = ?
            """
            svals = [cal_fn, ra, dec]
            cur.execute(sql, svals)
            rows = cur.fetchall()
            #print("NEW:", rows[0])
            up_cat_x, up_cat_y = rows[0]
            res_px = calc_dist((six,siy), (up_cat_x,up_cat_y))

            #print("OLD STAR:", dcname, new_cat_x, new_cat_y, cat_dist)
            #print("NEW STAR:", dcname, up_cat_x, up_cat_y, res_px)
            if res_px < 20:
               up_cat_image_stars.append((dcname,mag,ra,dec,img_ra,img_dec,match_dist,up_cat_x,up_cat_y,img_az,img_el,up_cat_x,up_cat_y,six,siy,res_px,bp) )

         nc['cat_image_stars'] = up_cat_image_stars
         temp_stars, total_res_px,total_res_deg = cat_star_report(nc['cat_image_stars'], 4)
         nc['total_res_px'] = total_res_px
         nc['total_res_deg'] = total_res_deg

         #print("OLD RES:", cal_params['total_res_px'] )
         #print("NEW RES:", nc['total_res_px'] )
         # only save if new is better than old
         if cal_params['total_res_px'] > total_res_px:
            cal_params = nc
            save_json_file(cal_json_file, cal_params)
            update_calfile(cal_fn, con, cur, json_conf, mcp)
            print("SAVED NEW BETTER")
         else:
            print("OLD BETTER")

         view_calib(cal_fn,json_conf, nc,oimg, show = 1)

def redo_calfile(cal_fn, con, cur, json_conf):
   cal_image_file = cal_fn.replace("-calparams.json", ".png")
   cal_dir = cal_dir_from_file(cal_image_file)
   cal_img = cv2.imread(cal_dir + cal_image_file)
   cal_json_file = get_cal_json_file(cal_dir)
   cal_json_fn = cal_json_file.split("/")[-1]

   sql = """
      DELETE FROM calfile_catalog_stars 
            WHERE cal_fn = ?
   """
   ivals = [cal_fn]
   cur.execute(sql, ivals)
   con.commit()

   sql = """
      DELETE FROM calibration_files 
            WHERE cal_fn = ?
   """
   ivals = [cal_fn]
   cur.execute(sql, ivals)
   con.commit()

   sql = """
      DELETE FROM calfile_paired_stars 
            WHERE cal_fn = ?
   """
   ivals = [cal_fn]
   cur.execute(sql, ivals)
   con.commit()

   if os.path.exists(cal_dir + cal_image_file):
      get_image_stars(cal_dir + cal_image_file, con, cur, json_conf)
   else:
      print("NO IMAGE", cal_dir + cal_image_file)






def repair_calfile_stars(cal_fn, con, cur, json_conf, mcp):
   # RE-PAIR STARS WITH LATESTS VALUES FROM DB OR JSON
   # AND MAKE SURE BOTH MATCH BY THE END!
   # COULD ALSO CALL THIS APPLY CAL 

   # LOAD THE FILES
   cal_image_file = cal_fn.replace("-calparams.json", ".png")
   cal_dir = cal_dir_from_file(cal_image_file)
   cal_img = cv2.imread(cal_dir + cal_image_file)
   cal_json_file = get_cal_json_file(cal_dir)
   cal_json_fn = cal_json_file.split("/")[-1]

   cal_params = load_json_file(cal_json_file)
   # RELOAD THE CATALOG STARS BASED ON JSON CAL PARAMS FILE (REFITS OR REMODEL UPDATES SHOULD HAVE ALREADY HAPPENED BEFORE THIS!")
   cat_stars, short_bright_stars = reload_calfile_catalog_stars(cal_fn, cal_params)


   
   # GET PAIRED STARS FROM THE DB
   # THIS IS WHAT WE HAVE CURRENTLY
   # LETS RE-PAIR EACH ONE TO GET THE BEST MATCH / VALUES
   stars,cat_stars = get_paired_stars(cal_fn, cal_params, con, cur)
   for star in stars:
      (cal_fn, name, mag, star_yn, ra, dec, star_flux, img_x, img_y, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, res_px, zp_res_px, slope, zp_slope) = star
      key = str(ra)[0:5] + "_" + str(dec)[0:5]
      print("ORIG:", cal_fn, name, mag, star_yn, img_x, img_y, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, res_px, zp_res_px)
      #cv2.line(cal_img, (int(new_cat_x),int(new_cat_y)), (int(zp_cat_x),int(zp_cat_y)), (255,255,255), 2)

      if res_px is not None:
         res_px = calc_dist((img_x,img_y), (new_cat_x,new_cat_y))
         if 0 < res_px <= 1:
            color = [0,255,0]
         elif 1 < res_px <= 3:
            color = [255,0,0]
         elif res_px > 3:
            color = [0,0,255]
         else:
            color = [255,255,255]

      if img_x is not None:
         cv2.circle(cal_img, (int(img_x),int(img_y)), 3, (0,69,255),1)
      if new_cat_x is not None:
         cv2.circle(cal_img, (int(new_cat_x),int(new_cat_y)), 5, color,1)
      if zp_cat_x is not None:
         cv2.circle(cal_img, (int(zp_cat_x),int(zp_cat_y)), 3, (128,128,128),1)
      if zp_cat_x is not None:
         cv2.line(cal_img, (int(zp_cat_x),int(zp_cat_y)), (int(img_x),int(img_y)), (128,128,128), 2)
      if new_cat_x is not None:
         cv2.line(cal_img, (int(new_cat_x),int(new_cat_y)), (int(img_x),int(img_y)), color, 1)

      # get close stars from the latest refreshed catalog db 
      star_obj = {}
      star_obj['cal_fn'] = cal_fn
      star_obj['x'] = img_x
      star_obj['y'] = img_y
      star_obj['star_flux'] = star_flux
      close_stars = find_close_stars(star_obj)

      if len(close_stars) > 0:
         for cs in close_stars:
            (cs_cal_fn, cs_name, cs_mag, cs_ra, cs_dec, cs_new_cat_x, cs_new_cat_y, cs_zp_cat_x, cs_zp_cat_y, \
               cs_ximg_x, cs_ximg_y, cs_star_flux, cs_star_yn, cs_star_pd, cs_star_found, cs_lens_model_version, \
               cs_slope, cs_zp_slope, cs_dist, cs_zp_dist) = cs
            cv2.line(cal_img, (int(cs_new_cat_x),int(cs_new_cat_y)), (int(img_x),int(img_y)), [255,255,255], 3)
      else:
         cv2.putText(cal_img, "X",  (int(img_x),int(img_y)), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,0,255), 1)

   if SHOW == 1:
      cv2.imshow('pepe', cal_img)
      cv2.waitKey(30)
   #get_image_stars(cal_dir + cal_image_file, con, cur, json_conf, True)
   #view_calfile(cal_fn, con,cur,json_conf)
   #exit()

def cal_data_to_cal_params(cal_fn, cal_data,json_conf, mcp):
   (station_id, camera_id, cal_fn, cal_ts, az, el, ra, dec, position_angle,\
      pixel_scale, zp_az, zp_el, zp_ra, zp_dec, zp_position_angle, zp_pixel_scale, x_poly, \
      y_poly, x_poly_fwd, y_poly_fwd, res_px, res_deg, ai_weather, ai_weather_conf, cal_version, last_update) = cal_data

   x_poly = json.loads(x_poly)
   y_poly = json.loads(y_poly)
   x_poly_fwd = json.loads(x_poly_fwd)
   y_poly_fwd = json.loads(y_poly_fwd)
      
   if mcp is not None and mcp != 0:
      x_poly = mcp['x_poly']
      y_poly = mcp['y_poly']
      x_poly_fwd = mcp['x_poly_fwd']
      y_poly_fwd = mcp['y_poly_fwd']

   
   cal_params = {}
   cal_params['station_id'] = station_id
   cal_params['camera_id'] = camera_id
   cal_params['cal_fn'] = cal_fn
   cal_params['img_w'] = 1920
   cal_params['img_h'] = 1080 
   cal_params['cal_ts'] = cal_ts
   cal_params['center_az'] = az
   cal_params['center_el'] = el
   cal_params['ra_center'] = ra
   cal_params['dec_center'] = dec
   cal_params['position_angle'] = position_angle
   cal_params['pixscale'] = pixel_scale
   cal_params['total_res_px'] = res_px
   cal_params['total_res_deg'] = res_deg 
   cal_params['x_poly'] = x_poly 
   cal_params['y_poly'] = y_poly 
   cal_params['x_poly_fwd'] = x_poly_fwd 
   cal_params['y_poly_fwd'] = y_poly_fwd 
   cal_params['cal_version'] = y_poly_fwd 
   cal_params['last_update'] = last_update


   cal_params['user_stars'] = []
   cal_params['cat_image_stars'] = []

   stars,cat_stars = get_paired_stars(cal_fn, cal_params, con, cur)
   for star in stars:
      (x_cal_fn, name, mag, star_yn, ra, dec, star_flux, img_x, img_y, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, res_px, zp_res_px, slope, zp_slope) = star
      if ra is not None:
         cal_params['cat_image_stars'].append((name,mag,ra,dec,ra,dec,res_px,zp_cat_x,zp_cat_y,az,el,new_cat_x,new_cat_y,img_x,img_y,res_px,star_flux))
      cal_params['user_stars'].append((img_x,img_y,star_flux))

   #print("CAL PARAMS 1:", cal_fn, cal_params['ra_center'], cal_params['dec_center'])
   #print("AZ EL :", cal_fn, cal_params['center_az'], cal_params['center_el'])
   #cal_params = update_center_radec(cal_fn,cal_params,json_conf)
   #print("CAL PARAMS 2:", cal_fn, cal_params['ra_center'], cal_params['dec_center'])
   return(cal_params)

def make_help_img(cal_img):
   print("CI", cal_img.shape)
   x1 = int((1920 / 2) - 400)
   x2 = int((1920 / 2) + 400)
   y1 = int((1080/ 2) - 400)
   y2 = int((1080/ 2) + 400)
   if cal_img is not None:
      temp_img = cal_img.copy()
   else:
      temp_img = np.zeros((1080,1920,3),dtype=np.uint8) 


   bgimg = temp_img[y1:y2, x1:x2]
   help_image = np.zeros((800,800,3),dtype=np.uint8) 
   try:
      blend_img = cv2.addWeighted(bgimg, .5, help_image, .5,0)
   except:
      blend_img = np.zeros((800,800,3),dtype=np.uint8) 
   cv2.putText(blend_img, "ALLSKYOS - CALIBRATION TOOL",  (100,30), cv2.FONT_HERSHEY_SIMPLEX, .9, (128,128,128), 2)
   cv2.putText(blend_img, "[ESC] = Quit",  (120,100), cv2.FONT_HERSHEY_SIMPLEX, .7, (0,0,128), 2)
   cv2.putText(blend_img, "[F1]  = Display/Hide this help message",  (120,140), cv2.FONT_HERSHEY_SIMPLEX, .7, (0,0,128), 2)
   cv2.putText(blend_img, "[A]   = -Azimuth ",  (120,180), cv2.FONT_HERSHEY_SIMPLEX, .7, (0,0,128), 2)
   cv2.putText(blend_img, "[S]   = -Elevation",  (120,220), cv2.FONT_HERSHEY_SIMPLEX, .7, (0,0,128), 2)
   cv2.putText(blend_img, "[D]   = +Elevation",  (120,260), cv2.FONT_HERSHEY_SIMPLEX, .7, (0,0,128), 2)
   cv2.putText(blend_img, "[F]   = +Azimuth ",  (120,300), cv2.FONT_HERSHEY_SIMPLEX, .7, (0,0,128), 2)
   cv2.putText(blend_img, "[Q]   = -Pixel Scale",  (120,340), cv2.FONT_HERSHEY_SIMPLEX, .7, (0,0,128), 2)
   cv2.putText(blend_img, "[W]   = -Position Angle",  (120,380), cv2.FONT_HERSHEY_SIMPLEX, .7, (0,0,128), 2)
   cv2.putText(blend_img, "[E]   = +Position Angle",  (120,420), cv2.FONT_HERSHEY_SIMPLEX, .7, (0,0,128), 2)
   cv2.putText(blend_img, "[R]   = +Pixel Scale",  (120,460), cv2.FONT_HERSHEY_SIMPLEX, .7, (0,0,128), 2)
   cv2.putText(blend_img, "[C]   = Center FOV",  (120,500), cv2.FONT_HERSHEY_SIMPLEX, .7, (0,0,128), 2)
   cv2.putText(blend_img, "[P]   = Re-Fit",  (120,540), cv2.FONT_HERSHEY_SIMPLEX, .7, (0,0,128), 2)
   cv2.putText(blend_img, "[0]   = Set Interval to 1.0",  (120,580), cv2.FONT_HERSHEY_SIMPLEX, .7, (0,0,128), 2)
   cv2.putText(blend_img, "[1]   = Set Interval to 0.1",  (120,620), cv2.FONT_HERSHEY_SIMPLEX, .7, (0,0,128), 2)
   cv2.putText(blend_img, "[2]   = Set Interval to 0.01",  (120,660), cv2.FONT_HERSHEY_SIMPLEX, .7, (0,0,128), 2)
   cv2.putText(blend_img, "[3]   = Set Interval to 0.001",  (120,700), cv2.FONT_HERSHEY_SIMPLEX, .7, (0,0,128), 2)

   print(x1,y1,x2,y2)
   print("T", temp_img.shape)
   print("B", blend_img.shape)
   temp_img[y1:y2,x1:x2] = blend_img

   cv2.rectangle(temp_img, (int(x1), int(y1)), (int(x2) , int(y2) ), (255, 255, 255), 2)
   return(temp_img)

def show_message(cal_img, message, px, py):
   val = 255
   for i in range(0, 10):
      val = val - (i * 10)
      temp_img = cal_img.copy()
      color = [val,val,val]
      cv2.putText(temp_img, message,  (px,py), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
      if SHOW == 1:
         cv2.resizeWindow("TWEEK CAL", 1920, 1080)
         cv2.imshow("TWEEK CAL", temp_img)
         cv2.waitKey(30)



def cat_view(cal_fn, con, cur, json_conf, mcp=None):
   print("CAT VIEW")
   (f_datetime, cam_id, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(cal_fn)
   cal_img, cal_params = view_calfile(cam_id, cal_fn, con, cur, json_conf, None, None, mcp)

   cal_img_fn = cal_fn.replace("-calparams.json", ".png")
   cal_image_file = cal_fn.replace("-calparams.json", ".png")
   cal_dir = cal_dir_from_file(cal_image_file)
   cal_json_file = get_cal_json_file(cal_dir)
   cal_json_fn = cal_json_file.split("/")[-1]

   if os.path.exists(cal_dir + cal_img_fn):
      clean_cal_img = cv2.imread(cal_dir + cal_img_fn)

   cat_stars, short_bright_stars, cat_image = get_catalog_stars(cal_params)
   if SHOW == 1:
      cv2.imshow('pepe', cat_image)
      cv2.waitKey(30)
   for star in cat_stars:
      (name,mag,ra,dec,new_cat_x,new_cat_y,zp_cat_x,zp_cat_y) = star
      print(name,mag,new_cat_x,new_cat_y,zp_cat_x,zp_cat_y)

   

def manual_tweek_calib(cal_fn, con, cur, json_conf,mcp, calfiles_data):
   help_on = False
   (f_datetime, cam_id, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(cal_fn)

   cal_img, cal_params = view_calfile(cam_id, cal_fn, con, cur, json_conf, calfiles_data, None, mcp)


   if cal_img is not None:
      help_img = make_help_img(cal_img) 
   else:
      help_img = np.zeros((800,800,3),dtype=np.uint8)

   interval = .1

   cal_img_fn = cal_fn.replace("-calparams.json", ".png")
   cal_image_file = cal_fn.replace("-calparams.json", ".png")
   cal_dir = cal_dir_from_file(cal_image_file)
   cal_json_file = get_cal_json_file(cal_dir)
   cal_json_fn = cal_json_file.split("/")[-1]
   if os.path.exists(cal_dir + cal_img_fn):
      clean_cal_img = cv2.imread(cal_dir + cal_img_fn)

   cv2.namedWindow("TWEEK CAL")
   cv2.resizeWindow("TWEEK CAL", 1920, 1080)

   cat_stars, short_bright_stars, cat_image = get_catalog_stars(cal_params)
   cal_params['short_bright_stars'] = short_bright_stars
   stars,cat_image_stars = get_paired_stars(cal_fn, cal_params, con, cur)
   cal_params['cat_image_stars'] = cat_image_stars

   cat_on = False

   while True:
      if help_on is True and SHOW == 1:
         cv2.imshow("TWEEK CAL", help_img)
      elif SHOW == 1:
         cv2.imshow("TWEEK CAL", cal_img)
      key = cv2.waitKey(0)
      if key == 27:
         return()
      if key == 104 or key == 190:
         if help_on is False:
            help_on = True
            help_img = make_help_img(cal_img) 
            cv2.imshow('TWEEK CAL', help_img) 
         else:
            cv2.imshow('TWEEK CAL', cal_img) 
            help_on = False
      if key == 102:
         cal_params['center_az'] += interval

        # cal_img, cal_params = view_calfile(cam_id, cal_fn, con, cur, json_conf, calfiles_data, None, mcp)

         cal_img, cal_params = view_calfile(cam_id, cal_fn, con, cur, json_conf, calfiles_data, cal_params,mcp)
         show_message(cal_img, "AZ + " + str(interval),900,500 )
      if key == 97:
         cal_params['center_az'] -= interval
         cal_img, cal_params = view_calfile(cam_id, cal_fn, con, cur, json_conf, calfiles_data, cal_params,mcp)
         show_message(cal_img, "AZ - " + str(interval),900,500 )
      if key == 115:
         cal_params['center_el'] -= interval
         cal_img, cal_params = view_calfile(cam_id, cal_fn, con, cur, json_conf, calfiles_data, cal_params,mcp)
         show_message(cal_img, "EL - " + str(interval),900,500 )
      if key == 100:
         cal_params['center_el'] += interval

         print("CAM ID:", cam_id)
         print("CAL FN :", cal_fn)
         cal_img, cal_params = view_calfile(cam_id, cal_fn, con, cur, json_conf, calfiles_data, cal_params,mcp)
         show_message(cal_img, "EL + " + str(interval),900,500 )
      if key == 119:
         cal_params['position_angle'] -= interval
         cal_img, cal_params = view_calfile(cam_id, cal_fn, con, cur, json_conf, calfiles_data, cal_params,mcp)
         show_message(cal_img, "PA - " + str(interval),900,500 )
      if key == 101:
         cal_params['position_angle'] += interval
         cal_img, cal_params = view_calfile(cam_id, cal_fn, con, cur, json_conf, calfiles_data, cal_params,mcp)
         show_message(cal_img, "PA + " + str(interval),900,500 )
      if key == 113:
         cal_params['pixscale'] -= interval
         cal_img, cal_params = view_calfile(cam_id, cal_fn, con, cur, json_conf, calfiles_data, cal_params,mcp)
         show_message(cal_img, "PX - " + str(interval),900,500 )
      if key == 114:
         cal_params['pixscale'] += interval
         show_message(cal_img, "PX + " + str(interval),900,500 )

      if key == 99 or key == 191:
         show_message(cal_img, "Recenter FOV Fit" + str(interval),900,500 )
         cal_params, cat_stars = recenter_fov(cal_fn, cal_params, clean_cal_img.copy(), stars, json_conf)
         cal_params['short_bright_stars'] = short_bright_stars
         cal_img, cal_params = view_calfile(cam_id, cal_fn, con, cur, json_conf, calfiles_data, cal_params, mcp)


      if key == 112 or key == 192:
         show_message(cal_img, "Recenter Poly Vars" + str(interval),900,500 )
      if key == 193:
         if cat_on is True:
            cv2.imshow('TWEEK CAL', cal_img) 
            cat_on = False
         else:
            cv2.imshow('TWEEK CAL', catalog_image) 
            cat_on = True 





      if key == 48 :
         interval = 1
         show_message(cal_img, "Set interval to " + str(interval),900,500 )
      if key == 49 :
         interval = .1
         show_message(cal_img, "Set interval to " + str(interval),900,500 )
      if key == 50 :
         interval = .01
         show_message(cal_img, "Set interval to " + str(interval),900,500 )
      if key == 51 :
         interval = .001
         show_message(cal_img, "Set interval to " + str(interval),900,500 )

      cat_stars, short_bright_stars, cat_image = get_catalog_stars(cal_params)
      up_stars, cat_image_stars = update_paired_stars(cal_fn, cal_params, stars, con, cur, json_conf)
      cal_params['cat_image_stars'] = cat_image_stars
      #for xxx in up_stars:
      #   print("UPSTAR:", xxx)

      cal_params['short_bright_stars'] = short_bright_stars
      cal_img, cal_params = view_calfile(cam_id, cal_fn, con, cur, json_conf, calfiles_data, cal_params, mcp)


      blend_img = cv2.addWeighted(cal_img, .9, cat_image, .1,0)
      cal_img= blend_img

      #cv2.imshow("TWEEK CAL", blend_img)
      help_img = make_help_img(cal_img) 


def view_calfile(cam_id, cal_fn, con, cur, json_conf, calfiles_data= None, cp = None,mcp=None):
   print("start view calfiles ", cal_fn, len(calfiles_data))
   if calfiles_data is not None:
      # we are dealing with a cal-file not a meteor-file
      if cal_fn in calfiles_data:
         cal_data = calfiles_data[cal_fn]
      else:
         print("PROBLEM cal_fn is not in the cal data!?", cal_fn, calfiles_data.keys())
         exit()
         return(False, False)
   else:
      print("CAL files data is none!", calfiles_data)
      exit()

   if cp is None:
      cal_params = cal_data_to_cal_params(cal_fn, cal_data,json_conf, mcp)
   else:
      cal_params = cp.copy()

   cal_img_fn = cal_fn.replace("-calparams.json", ".png")
   cal_image_file = cal_fn.replace("-calparams.json", ".png")
   cal_dir = cal_dir_from_file(cal_image_file)
   cal_json_file = get_cal_json_file(cal_dir)
   cal_json_fn = cal_json_file.split("/")[-1]
   if os.path.exists(cal_dir + cal_img_fn):
      cal_img = cv2.imread(cal_dir + cal_img_fn)

   
   cal_params = update_center_radec(cal_fn,cal_params,json_conf)
   stars, cat_image_stars = get_paired_stars(cal_fn, cal_params, con, cur)
   cal_params['cat_image_stars'] = cat_image_stars

   rez = []

   for star in stars:
      (cal_fn, name, mag, star_yn, ra, dec, star_flux, img_x, img_y, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, res_px, zp_res_px, slope, zp_slope) = star
      if ra is not None:
         res_px = calc_dist((img_x,img_y), (new_cat_x,new_cat_y))
         zp_res_px = calc_dist((img_x,img_y), (zp_cat_x,zp_cat_y))
         rez.append(res_px)
      else:
         res_px = None
      if res_px is not None:
         if 0 < res_px <= 1:
            color = [0,255,0]
         elif 1 < res_px <= 3:
            color = [255,0,0]
         elif res_px > 3:
            color = [0,0,255]
         else:
            color = [255,255,255]
      else:
         # There is no match for this star
         cv2.putText(cal_img, "X",  (int(img_x + 5),int(img_y )), cv2.FONT_HERSHEY_SIMPLEX, .5, (0,0,128), 2)

      if img_x is not None:
         cv2.circle(cal_img, (int(img_x),int(img_y)), 3, (0,69,255),1)
      if new_cat_x is not None:
         cv2.circle(cal_img, (int(new_cat_x),int(new_cat_y)), 5, color,1)
      if zp_cat_x is not None:
         cv2.circle(cal_img, (int(zp_cat_x),int(zp_cat_y)), 3, (128,128,128),1)
      if zp_cat_x is not None:
         cv2.line(cal_img, (int(zp_cat_x),int(zp_cat_y)), (int(img_x),int(img_y)), (128,128,128), 2)
      if new_cat_x is not None:
         cv2.line(cal_img, (int(new_cat_x),int(new_cat_y)), (int(img_x),int(img_y)), color, 1)

   mean_res = np.mean(rez)
   cal_params['total_res_px'] = mean_res 
   desc = json_conf['site']['ams_id'] + " " + cal_fn.replace("-calparams.json", "")
   desc = desc.replace("-stacked", "")
   desc += " | "

   desc += "AZ {:.4f} | ".format(cal_params['center_az'])
   desc += "EL {:.4f} | ".format(cal_params['center_el'])
   desc += "RA {:.4f} | ".format(float(cal_params['ra_center']))
   desc += "DEC {:.4f} | ".format(float(cal_params['dec_center']))
   desc += "POS {:.4f} | ".format(cal_params['position_angle'])
   desc += "PIX {:.4f} | ".format(cal_params['pixscale'])
   desc += "RES {:.3f} | ".format(mean_res)
   cv2.putText(cal_img, desc,  (250,15), cv2.FONT_HERSHEY_SIMPLEX, .6, (128,128,128), 1)

   # todo add total_res_deg...
   return(cal_img, cal_params)

def update_paired_stars(cal_fn, cal_params, stars, con, cur, json_conf):
   # this will update existing paired stars with latest cat x,y based on provided cal_params


      # get stars from the cal_params

   up_stars = []
   up_cat_image_stars = []
   #print("CALP", cal_params['center_az'], cal_params['center_el'], cal_params['ra_center'], cal_params['dec_center'] )
   for star in stars:
      print("STAR 1 IS:", star)
      (cal_fn, name, mag, star_yn, ra, dec, star_flux, img_x, img_y, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, res_px, zp_res_px, slope, zp_slope) = star
      print("NAME IS:", name)

      n_new_cat_x,n_new_cat_y = get_xy_for_ra_dec(cal_params, ra, dec)


      if new_cat_x is None:
         continue
      if n_new_cat_x is not None:
         n_res_px = calc_dist((img_x,img_y), (n_new_cat_x,n_new_cat_y))
      else:
         n_res_px = 0

      #print("OLD {} {}".format(new_cat_x, new_cat_y))
      #print("NEW {} {}".format(n_new_cat_x, n_new_cat_y))
      #print("___")

      up_stars.append((cal_fn, name, mag, star_yn, ra, dec, star_flux, img_x, img_y, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, res_px, zp_res_px, slope, zp_slope))
      sql = """
         UPDATE calfile_paired_stars
            SET new_cat_x = ?,
                new_cat_y = ?,
                res_px = ?
          WHERE cal_fn = ?
            AND img_x = ?
            AND img_y = ?
      """
      uvals = [n_new_cat_x, n_new_cat_y, n_res_px, cal_fn, img_x, img_y]
      cur.execute(sql, uvals)
      #print(sql)
      #print(uvals)
      # temp holder / fix later

      new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(img_x,img_y,cal_fn,cal_params,json_conf)

      img_ra = img_ra
      img_dec = img_dec
      img_az = img_az
      img_el = img_el
      match_dist = zp_res_px
      cat_dist = res_px
      if ra is not None:
         print("NAME IS:", name)
         up_cat_image_stars.append((name,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,img_x,img_y,res_px,star_flux))
   con.commit()
   return(up_stars, up_cat_image_stars)


def get_image_stars(cal_image_file, con, cur, json_conf,force=False):
   # run this the first time the image is processed to extract stars and pairs?

   print("CAL IMAGE_FILE", cal_image_file)

   if "/" in cal_image_file:
      cal_image_file = cal_image_file.split("/")[-1]

   """
      in: image file to extract stars from
     output : x,y,intensity of each point that 'passes' the star tests
   """

   cal_fn = cal_image_file.split("-")[0]


   zp_star_chart_img = np.zeros((1080,1920,3),dtype=np.uint8)


   # this will update existing paired stars with latest cat x,y based on provided cal_params


      # get stars from the cal_params 

   up_stars = []
   up_cat_image_stars = []
   #print("CALP", cal_params['center_az'], cal_params['center_el'], cal_params['ra_center'], cal_params['dec_center'] )
   for star in stars:
      print("UPDATE:", star)
      (cal_fn, name, mag, star_yn, ra, dec, star_flux, img_x, img_y, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, res_px, zp_res_px, slope, zp_slope) = star

      n_new_cat_x,n_new_cat_y = get_xy_for_ra_dec(cal_params, ra, dec)


      if new_cat_x is None:
         continue
      if n_new_cat_x is not None:
         n_res_px = calc_dist((img_x,img_y), (n_new_cat_x,n_new_cat_y))
      else:
         n_res_px = 0

      #print("OLD {} {}".format(new_cat_x, new_cat_y))
      #print("NEW {} {}".format(n_new_cat_x, n_new_cat_y))
      #print("___")

      up_stars.append((cal_fn, name, mag, star_yn, ra, dec, star_flux, img_x, img_y, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, res_px, zp_res_px, slope, zp_slope)) 
      sql = """
         UPDATE calfile_paired_stars 
            SET new_cat_x = ?, 
                new_cat_y = ?, 
                res_px = ? 
          WHERE cal_fn = ? 
            AND img_x = ? 
            AND img_y = ?
      """
      uvals = [n_new_cat_x, n_new_cat_y, n_res_px, cal_fn, img_x, img_y]
      cur.execute(sql, uvals)
      #print(sql)
      #print(uvals)
      # temp holder / fix later

      new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(img_x,img_y,cal_fn,cal_params,json_conf)

      img_ra = img_ra 
      img_dec = img_dec 
      img_az = img_az 
      img_el = img_el 
      match_dist = zp_res_px
      cat_dist = res_px 
      if ra is not None:
         up_cat_image_stars.append((name,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,img_x,img_y,res_px,star_flux)) 
   con.commit()

   return(up_stars, up_cat_image_stars)

def update_calibration_file(cal_fn, cal_params, con,cur,json_conf,mcp):
   ts = time.time()

   if type(cal_params['x_poly']) is not list:
      cal_params['x_poly'] = cal_params['x_poly'].tolist()
      cal_params['y_poly'] = cal_params['y_poly'].tolist()
      cal_params['y_poly_fwd'] = cal_params['y_poly_fwd'].tolist()
      cal_params['x_poly_fwd'] = cal_params['x_poly_fwd'].tolist()

   if mcp is None:
      cv = 1
   else:
      cv = mcp['cal_version']

   uvals = [ts, cal_params['center_az'], cal_params['center_el'], cal_params['ra_center'], cal_params['dec_center'], \
            cal_params['position_angle'], cal_params['pixscale'], json.dumps(cal_params['x_poly']), json.dumps(cal_params['y_poly']), \
            json.dumps(cal_params['x_poly_fwd']), json.dumps(cal_params['y_poly_fwd']), cal_params['total_res_px'], cal_params['total_res_deg'], \
            cv, ts, cal_fn]
   sql = """
      UPDATE calibration_files 
         SET 
                 cal_ts = ?,
                     az = ?,
                     el = ?,
                     ra = ?,
                    dec = ?,
         position_angle = ?,
            pixel_scale = ?,
                 x_poly = ?,
                 y_poly = ?,
             x_poly_fwd = ?,
             y_poly_fwd = ?,
                 res_px = ?,
                res_deg = ?,
            cal_version = ?,
            last_update = ?
       WHERE cal_fn = ? 
   """

   #print(sql)
   #print(uvals)
   cur.execute(sql, uvals)
   con.commit()

def update_calfile(cal_fn, con, cur, json_conf, mcp):

   cal_root = cal_fn.split("-")[0]
   cal_dir = "/mnt/ams2/cal/freecal/" + cal_root + "/"  
   cal_img_fn = cal_fn.replace("-calparams.json", ".png")
   if os.path.exists(cal_dir + cal_img_fn):
      cal_img = cv2.imread(cal_dir + cal_img_fn)
   if os.path.exists(cal_dir + cal_fn) is True:
      cal_params = load_json_file(cal_dir + cal_fn)
   else:   
      print(cal_dir + cal_fn + " NOT FOUND.")
      exit()

   cal_params['x_poly'] = mcp['x_poly']
   cal_params['y_poly'] = mcp['y_poly']
   cal_params['x_poly_fwd'] = mcp['x_poly_fwd']
   cal_params['y_poly_fwd'] = mcp['y_poly_fwd']

   save_json_file(cal_dir + cal_fn, cal_params)

   sql = """UPDATE calibration_files SET az = ?, el = ?, ra = ?, dec = ?, position_angle = ?, pixel_scale = ?, x_poly = ?, y_poly = ?, x_poly_fwd = ?, y_poly_fwd = ?
            WHERE cal_fn = ?
   """

   uvals = [cal_params['center_az'], cal_params['center_el'], cal_params['ra_center'], cal_params['dec_center'], cal_params['position_angle'], cal_params['pixscale'], json.dumps(mcp['x_poly']), json.dumps(mcp['y_poly']), json.dumps(mcp['x_poly_fwd']), json.dumps(mcp['y_poly_fwd']), cal_fn ]
   #print(sql)
   #print(uvals)
   cur.execute(sql, uvals)

   sql = """
      SELECT station_id, camera_id, cal_fn, cal_ts, az, el, ra, dec, position_angle, pixel_scale, 
             zp_az, zp_el, zp_ra, zp_dec, zp_position_angle, zp_pixel_scale, x_poly, y_poly, x_poly_fwd, y_poly_fwd, 
             res_px, res_deg, ai_weather, ai_weather_conf, cal_version, last_update
        FROM calibration_files WHERE cal_fn = ?
   """
   svals = [cal_fn]
   cur.execute(sql, svals)
   rows = cur.fetchall()
   #print(rows[0])


   # UPDATE THE CATALOG
   cat_stars, short_bright_stars,calibration_image = get_catalog_stars(cal_params)
   for star in cat_stars:
      (name,mag,ra,dec,new_cat_x,new_cat_y,zp_cat_x,zp_cat_y) = star
      desc = name + " " + str(mag)
      #cv2.putText(zp_star_chart_img, desc,  (zp_cat_x,zp_cat_y), cv2.FONT_HERSHEY_SIMPLEX, .4, (128,128,128), 1)
      cv2.line(cal_img, (int(new_cat_x),int(new_cat_y)), (int(zp_cat_x),int(zp_cat_y)), (255,255,255), 2)
      sql = """
               INSERT OR REPLACE INTO calfile_catalog_stars (
                      cal_fn,
                      name,
                      mag,
                      ra,
                      dec,
                      new_cat_x,
                      new_cat_y,
                      zp_cat_x,
                      zp_cat_y
               )
               VALUES (?,?,?,?,?,?,?,?,?)
      """
      ivals = [cal_fn, name,mag,ra,dec,new_cat_x,new_cat_y,zp_cat_x,zp_cat_y]
      try:
         cur.execute(sql, ivals)
      except:
         print("Must be done already")
   con.commit()
   if SHOW == 1:
      cv2.imshow("calview", cal_img)
      cv2.waitKey(60)

   # GET THE CURRENT STARS, UPDATE THE PAIRS BASED ON NEWLY LOADED CAT STAR POSITIONS
   sql = """
      SELECT cal_fn, name, mag, star_yn, ra, dec, star_flux, img_x, img_y, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, res_px, zp_res_px, slope, zp_slope
        FROM calfile_paired_stars
       WHERE cal_fn = ?
   """
   svals = [cal_fn]
   #print(sql)
   #print(svals)
   cur.execute(sql, svals )

   # PAIR STARS AREA HERE..
   rows = cur.fetchall()
   all_good_stars = []
   for row in rows:
      cal_fn, name, mag, star_yn, ra, dec, star_flux, img_x, img_y, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, res_px, zp_res_px, slope, zp_slope = row

      if new_cat_x is not None and new_cat_y is not None and img_x is not None and img_y is not None:
         res_px = calc_dist((img_x,img_y), (new_cat_x,new_cat_y))
      else:
         res_px = None

      #print(name, new_cat_x, new_cat_y, img_x, img_y, res_px)
      star_obj = {}
      star_obj['x'] = img_x
      star_obj['y'] = img_y
      star_obj['star_flux'] = star_flux
      star_obj['cal_fn'] = cal_fn 
      close_stars = find_close_stars(star_obj)

      pp = 1
      for cs in close_stars:
         (cal_fn, name, mag, ra, dec, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, \
            ximg_x, ximg_y, star_flux, star_yn, star_pd, star_found, lens_model_version, \
            slope, zp_slope, dist, zp_dist) = cs
         #if new_cat_x is None or new_cat_y is None or img_x is None or img_y is None:
         #   continue
         res_px = calc_dist((img_x,img_y), (new_cat_x,new_cat_y))
         zp_dist = calc_dist((img_x,img_y), (zp_cat_x,zp_cat_y))
         slope = (img_y - new_cat_y) / (img_x - new_cat_x)
         zp_slope = (img_y - zp_cat_y) / (img_x - zp_cat_x)

         #print("   CLOSE:", name, mag, new_cat_x, new_cat_y, img_x, img_y, res_px)

         if pp == 1:
            # UPDATE THE calfile_paired_stars table
            sql = """
               UPDATE calfile_paired_stars SET name = ?, 
                                               mag = ?,
                                               ra = ?,
                                               dec = ?,
                                               new_cat_x = ?,
                                               new_cat_y = ?,
                                               zp_cat_x = ?,
                                               zp_cat_y = ?,
                                               slope = ?,
                                               zp_slope = ?,
                                               res_px = ?,
                                               zp_res_px = ?
                                         WHERE cal_fn = ?
                                           AND img_x = ?
                                           AND img_y = ?
            """
            uvals = [name, mag, ra, dec, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, slope, zp_slope, res_px, zp_dist, cal_fn, img_x, img_y]
            cur.execute(sql, uvals)
            #print(sql)
            #print(uvals)
         pp += 1


def reload_calfile_catalog_stars(cal_fn, cal_params):

   sql = """
      DELETE FROM calfile_catalog_stars 
            WHERE cal_fn = ?
   """
   ivals = [cal_fn]
   cur.execute(sql, ivals)
   con.commit()

   cat_stars, short_bright_stars = get_catalog_stars(cal_params)
   for star in cat_stars:
      (name,mag,ra,dec,new_cat_x,new_cat_y,zp_cat_x,zp_cat_y) = star
      sql = """
               INSERT OR REPLACE INTO calfile_catalog_stars (
                      cal_fn,
                      name,
                      mag,
                      ra,
                      dec,
                      new_cat_x,
                      new_cat_y,
                      zp_cat_x,
                      zp_cat_y
               )
               VALUES (?,?,?,?,?,?,?,?,?)
      """
      ivals = [cal_fn, name,mag,ra,dec,new_cat_x,new_cat_y,zp_cat_x,zp_cat_y]
      try:
         cur.execute(sql, ivals)
      except:
         print("Must be done already")
   con.commit()
   return(cat_stars, short_bright_stars)


def get_paired_stars(cal_fn, cal_params, con, cur):
   sql = """
      SELECT cal_fn, name, mag, star_yn, ra, dec, star_flux, img_x, img_y, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, res_px, zp_res_px, slope, zp_slope
        FROM calfile_paired_stars
       WHERE cal_fn = ?
   """
   svals = [cal_fn]
   #print(sql)
   #print(svals)
   cur.execute(sql, svals )
   up_cat_image_stars = []
   # PAIR STARS AREA HERE..
   rows = cur.fetchall()
   stars = []
   used = {}
   dupes = {}
   for row in rows:
      cal_fn, name, mag, star_yn, ra, dec, star_flux, img_x, img_y, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, res_px, zp_res_px, slope, zp_slope = row
      key = str(ra) + "_" + str(dec)
      if key not in used:
         print("STARS ADD ROWS:", cal_fn, name)
         print(cal_fn, name, mag, star_yn, ra, dec, star_flux, img_x, img_y, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, res_px, zp_res_px, slope, zp_slope)

         stars.append((cal_fn, name, mag, star_yn, ra, dec, star_flux, img_x, img_y, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, res_px, zp_res_px, slope, zp_slope))
         used[key] = 1
      else:
         dupes[key] = 1

      # temp holder / fix later
      new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(img_x,img_y,cal_fn,cal_params,json_conf)

      img_ra = img_ra
      img_dec = img_dec
      img_az = img_az
      img_el = img_el 
      if ra is not None and img_ra is not None:
         match_dist = angularSeparation(ra,dec,img_ra,img_dec)
      else:
         match_dist = 999


      cat_dist = res_px 
      if ra is not None:
         up_cat_image_stars.append((name,mag,ra,dec,img_ra,img_dec,match_dist,zp_cat_x,zp_cat_y,img_az,img_el,new_cat_x,new_cat_y,img_x,img_y,res_px,star_flux)) 

   if len(stars) > 0:
      print("STARS:", stars[0])
   if len(up_cat_image_stars) > 0:
      print("CATSTARS:", up_cat_image_stars[0])
   return(stars, up_cat_image_stars)


def get_image_stars(cal_image_file, con, cur, json_conf,force=False):
   # run this the first time the image is processed to extract stars and pairs?

   print("CAL IMAGE_FILE", cal_image_file)

   if "/" in cal_image_file:
      cal_image_file = cal_image_file.split("/")[-1]

   """
      in: image file to extract stars from
     output : x,y,intensity of each point that 'passes' the star tests
   """

   cal_fn = cal_image_file.split("-")[0]


   zp_star_chart_img = np.zeros((1080,1920,3),dtype=np.uint8)
   star_chart_img = np.zeros((1080,1920,3),dtype=np.uint8)

   image_stars = []
   cv2.namedWindow("calview")
   cv2.resizeWindow("calview", 1920, 1080)
   # setup values
   cal_dir = cal_dir_from_file(cal_image_file)
   if cal_dir is False:
      print("Corrupted files or not named right.")
      return()


   cal_json_file = get_cal_json_file(cal_dir)
   cal_json_fn = cal_json_file.split("/")[-1]

   print("CAL FN:", cal_fn)
   print("CAL DIR:", cal_dir)
   print("CAL JSON", cal_json_file)
   print("CAL IMAGE", cal_dir + cal_image_file)

   resp = check_calibration_file(cal_json_fn, con, cur)
   if resp is True and force is False:
      print("SKIP DONE!")
      #return() 
   if resp is False:
      insert_calib(cal_json_file, con, cur, json_conf)
      con.commit()
   print(cal_json_file)

   print("R", resp)

   # load the image
   if os.path.exists(cal_dir + cal_image_file) is True:
      cal_img = cv2.imread(cal_dir + cal_image_file)
      cal_img_orig = cal_img.copy()
   else:
      print("No image_file!")
      return(False) 


   if os.path.exists(cal_json_file) is True:
      cal_params = load_json_file(cal_json_file)
   else:
      return(False) 

   cat_stars, short_bright_stars, cat_image = get_catalog_stars(cal_params)
   for star in cat_stars:
      (name,mag,ra,dec,new_cat_x,new_cat_y,zp_cat_x,zp_cat_y) = star
      desc = name + " " + str(mag)
      #cv2.putText(zp_star_chart_img, desc,  (zp_cat_x,zp_cat_y), cv2.FONT_HERSHEY_SIMPLEX, .4, (128,128,128), 1)
      cv2.line(zp_star_chart_img, (int(new_cat_x),int(new_cat_y)), (int(zp_cat_x),int(zp_cat_y)), (255,255,255), 2)
      sql = """
               INSERT INTO calfile_catalog_stars (
                      cal_fn,
                      name,
                      mag,
                      ra,
                      dec,
                      new_cat_x,
                      new_cat_y,
                      zp_cat_x,
                      zp_cat_y 
               ) 
               VALUES (?,?,?,?,?,?,?,?,?)
      """
      ivals = [cal_json_fn, name,mag,ra,dec,new_cat_x,new_cat_y,zp_cat_x,zp_cat_y]
      try:
         cur.execute(sql, ivals)
      except:
         print("Must be done already")
   con.commit()
   if SHOW == 1:
      cv2.imshow("calview", zp_star_chart_img)
      cv2.waitKey(30)

   gray_orig = cv2.cvtColor(cal_img, cv2.COLOR_BGR2GRAY)
   gray_img  = cv2.cvtColor(cal_img, cv2.COLOR_BGR2GRAY)
   show_img = cal_img.copy()
   if SHOW == 1:
      cv2.imshow("calview", show_img)
      cv2.waitKey(30)

   # check top 100 brightest points in the image
   for i in range(0,200):
      min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(gray_img)
      resp = make_star_roi(mx,my,32)
      sbx = mx
      sby = my
      status,x1,y1,x2,y2 = resp
      valid = False
      if status is True:
         crop_img = gray_orig[y1:y2,x1:x2]
         avg_val = np.mean(crop_img)
         min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(gray_img)
         pxd = max_val - avg_val 

         _, crop_thresh = cv2.threshold(crop_img, max_val * .85, 255, cv2.THRESH_BINARY)
         #cv2.imshow('crop_thresh', crop_thresh)
         cnts = get_contours_in_image(crop_thresh)

         if pxd > 20 and len(cnts) == 1:
            valid = True

         star_yn = ai_check_star(crop_img, cal_fn)

         if len(cnts) == 1:
            x,y,w,h = cnts[0]
            cx = x + (w/2)
            cy = y + (h/2)
            if w > h:
               radius = w
            else:
               radius = h
            if True:
               star_flux = do_photo(crop_img, (cx,cy), radius+1)
            #try:
            #except:
            #   star_flux = 0

         else:
            valid = False

         if valid is True:

            print("FLUX / YN:", star_flux, star_yn)

            star_obj = {}
            star_obj['cal_fn'] = cal_json_fn 
            star_obj['x'] = x1 + (x) + (w/2)
            star_obj['y'] = y1 + (y) + (h/2)
            star_obj['star_flux'] = star_flux
            star_obj['star_yn'] = star_yn
            star_obj['star_radius'] = radius
            image_stars.append(star_obj)
            desc = str(int(star_flux)) + " " + str(int(star_yn)) 
            if star_yn > 90:
               cv2.putText(show_img, desc,  (x1,y1), cv2.FONT_HERSHEY_SIMPLEX, .4, (128,128,128), 1)
               cv2.rectangle(show_img, (int(x1), int(y1)), (int(x2) , int(y2) ), (255, 255, 255), 1)
            else:
               cv2.putText(show_img, desc,  (x1,y1), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,0,0), 1)
               cv2.rectangle(show_img, (int(x1), int(y1)), (int(x2) , int(y2) ), (0, 0, 0), 1)


            # Do an insert here into calfile_paired_stars table
            sql = """
               INSERT INTO calfile_paired_stars (
                           cal_fn, 
                           img_x, 
                           img_y, 
                           star_flux, 
                           star_yn, 
                           star_pd)
                    VALUES (?,?,?,?,?,?)
            """
            ivals = [cal_json_fn, star_obj['x'], star_obj['y'], star_flux, star_yn, pxd]
            print(sql)
            print(ivals)
            try:
               cur.execute(sql, ivals)
            except:
               print("Must be done already")


      gray_img[y1:y2,x1:x2] = 0
      if SHOW == 1:
         cv2.imshow("calview", show_img)
         cv2.waitKey(10)

   if SHOW == 1:
      cv2.waitKey(30)

   print("NOW LETS PAIR THE STARS!")
   for star_obj in image_stars:
      
      cal_fn = star_obj['cal_fn']
      x = star_obj['x']
      y = star_obj['y']
      star_flux = star_obj['star_flux']
      close_stars = find_close_stars(star_obj)

      pp = 1
      if len(close_stars) == 0:
         cv2.putText(show_img, "X",  (int(x + 5),int(y + 5)), cv2.FONT_HERSHEY_SIMPLEX, .5, (0,0,128), 2)
         continue

      for pstar in close_stars:
         (cal_fn, name, mag, ra, dec, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, \
         img_x, img_y, cat_star_flux, star_yn, star_pd, star_found, lens_model_version, \
         slope, zp_slope, dist, zp_dist) = pstar

         print("POSSIBLE STAR:", zp_cat_x, zp_cat_y)
        
         desc = str(int(mag))
         cv2.putText(show_img, desc,  (int(zp_cat_x+20),int(zp_cat_y)), cv2.FONT_HERSHEY_SIMPLEX, .5, (128,128,128), 2)
         cv2.line(show_img, (int(zp_cat_x),int(zp_cat_y)), (int(x),int(y)), (128,128,128), 2)
         if pp == 1:
            # UPDATE THE calfile_paired_stars table
            res_px = calc_dist((x,y), (new_cat_x,new_cat_y))
            sql = """
               UPDATE calfile_paired_stars SET name = ?, 
                                               mag = ?,
                                               ra = ?,
                                               dec = ?,
                                               new_cat_x = ?,
                                               new_cat_y = ?,
                                               zp_cat_x = ?,
                                               zp_cat_y = ?,
                                               slope = ?,
                                               zp_slope = ?,
                                               res_px = ?,
                                               zp_res_px = ?
                                         WHERE cal_fn = ?
                                           AND img_x = ?
                                           AND img_y = ?
            """
            uvals = [name, mag, ra, dec, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, slope, zp_slope, res_px, zp_dist, cal_json_fn, x, y]
            cur.execute(sql, uvals)
            #print(sql)
            #print(uvals)
            #cv2.line(cal_img_orig, (int(new_cat_x),int(new_cat_y)), (int(zp_cat_x),int(zp_cat_y)), (255,255,255), 2)



            #cv2.line(show_img, (int(new_cat_x),int(new_cat_y)), (int(x),int(y)), (0,128,0), 1)
            cv2.line(show_img, (int(new_cat_x),int(new_cat_y)), (int(x),int(y)), (203,192,255), 1)

         # extra close stars that are not choosen
         #else:
         #   if img_x is not None:
         #      cv2.putText(show_img, "X",  (int(img_x),int(img_y)), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,0,255), 1)
         #   cv2.line(show_img, (int(new_cat_x),int(new_cat_y)), (int(x),int(y)), (203,192,255), 1)
         cv2.imshow("calview", show_img)
         cv2.waitKey(30)
         pp += 1



      print("IMG STAR:", star_obj['x'], star_obj['y'])
   if SHOW == 1:
      cv2.waitKey(30)
   con.commit()


#   calib_info = get_calibration_file()

def insert_paired_star_full(cat_image_star, cal_fn, cal_params, mcp, json_conf):
   cal_params_nlm = cal_params.copy()
   cal_params_nlm['x_poly'] = np.zeros(shape=(15,), dtype=np.float64)
   cal_params_nlm['y_poly'] = np.zeros(shape=(15,), dtype=np.float64)
   cal_params_nlm['x_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
   cal_params_nlm['y_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
   star_yn = -1
   star_pd = -1
   slope = -1
   zp_slope = -1
   res_deg = -1
   if True:
      star_obj = {}
      (name,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,img_x,img_y,res_px,star_flux) = cat_image_star

      zp_x, zp_y, zp_img_ra,zp_img_dec, zp_img_az, zp_img_el = XYtoRADec(img_x,img_y,cal_fn,cal_params_nlm,json_conf)
      zp_cat_x, zp_cat_y = get_xy_for_ra_dec(cal_params_nlm, ra, dec)

      zp_res_px = calc_dist((img_x,img_y), (zp_cat_x,zp_cat_y))
      star_obj["cal_fn"] = cal_fn
      star_obj["name"]  = name
      star_obj["mag"] = mag
      star_obj["ra"]  = ra
      star_obj["dec"] = dec
      star_obj["new_cat_x"] = new_cat_x
      star_obj["new_cat_y"] = new_cat_y
      star_obj["zp_cat_x"]  = zp_cat_x
      star_obj["zp_cat_y"] = zp_cat_y
      star_obj["img_x"] = img_x
      star_obj["img_y"] = img_y
      star_obj["star_flux"] = star_flux
      star_obj["star_yn"]  = star_yn
      star_obj["star_pd"] = star_pd
      star_obj["star_found"] = 1
      if mcp is None:
         star_obj["lens_model_version"] = 1
      else:
         star_obj["lens_model_version"] = mcp['cal_version']
      star_obj["slope"] = slope
      star_obj["zp_slope"] = zp_slope
      star_obj["res_px"] = res_px
      star_obj["zp_res_px"] = zp_res_px
      star_obj["res_deg"] = res_deg
      insert_paired_star(cal_fn, star_obj, con, cur, json_conf )
   con.commit()

def insert_paired_star(cal_fn, star_obj, con, cur, json_conf):
   # Do an insert here into calfile_paired_stars table
   sql = """
               INSERT OR REPLACE INTO calfile_paired_stars (
                           cal_fn,
                           name,
                           mag,
                           ra,
                           dec,
                           new_cat_x,
                           new_cat_y,
                           zp_cat_x,
                           zp_cat_y,
                           img_x,
                           img_y,
                           star_flux,
                           star_yn,
                           star_pd,
                           star_found,
                           lens_model_version,
                           slope,
                           zp_slope,
                           res_px,
                           zp_res_px,
                           res_deg
                           )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
   """

   ivals = [star_obj["cal_fn"], star_obj["name"], star_obj["mag"], star_obj["ra"], star_obj["dec"], star_obj["new_cat_x"], star_obj["new_cat_y"], star_obj["zp_cat_x"], star_obj["zp_cat_y"], star_obj["img_x"], star_obj["img_y"], star_obj["star_flux"], star_obj["star_yn"], star_obj["star_pd"], 1, star_obj["lens_model_version"], star_obj["slope"], star_obj["zp_slope"], star_obj["res_px"], star_obj["zp_res_px"], star_obj["res_deg"]]

   if True:
      cur.execute(sql, ivals)
      #con.commit()
   #try:
   #except:
   #   print("record already exists.")

def check_calibration_file(cal_fn, con, cur):
   sql = "SELECT cal_fn FROM calibration_files where cal_fn = ?"
   uvals = [cal_fn]
   cur.execute(sql, uvals)
   #print(sql, cal_fn)
   rows = cur.fetchall()
   #print(rows)
   if len(rows) > 0:
      return(True)
   else:
      return(False)


def find_stars_with_catalog(cal_fn, con, cur, json_conf,mcp=None, cp=None, cal_img=None):
   # for each star in the catalog check a crop around that location for an image star
   # if found add to user_stars and cat_image_stars
   # calc final res


   (f_datetime, cam_id, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(cal_fn)
   font = ImageFont.truetype("/usr/share/fonts/truetype/DejaVuSans.ttf", 20, encoding="unic" )
   if cp is None:
      cal_img, cal_params = view_calfile(cam_id, cal_fn, con, cur, json_conf,None, None, mcp )
   else:
      cal_params = dict(cp)

   if cal_img is False:
      print("FAILED FIND")
      return()
   #help_img = make_help_img(cal_img)
   interval = .1
   cal_img = cv2.GaussianBlur(cal_img, (7, 7), 0)

   if "calparams" in cal_fn:
      cal_img_fn = cal_fn.replace("-calparams.json", ".png")
      cal_image_file = cal_fn.replace("-calparams.json", ".png")
   else:
      cal_img_fn = cal_fn.replace(".json", "-stacked.jpg")
      cal_image_file = cal_fn.replace(".json", "-stacked.jpg")

   # is this a meteor file or not!
   if "cal_params" in cal_fn:
      cal_dir = cal_dir_from_file(cal_image_file)
      cal_json_file = get_cal_json_file(cal_dir)
   else:
      date = cal_fn[0:10]
      cal_dir = "/mnt/ams2/meteors/" + date + "/"
      cal_json_file = cal_dir + cal_fn

   cal_json_fn = cal_json_file.split("/")[-1]
   if cal_img is not None:
      clean_cal_img = cal_img.copy()
   elif os.path.exists(cal_dir + cal_img_fn):
      clean_cal_img = cv2.imread(cal_dir + cal_img_fn)
   clean_cal_img = cv2.resize(clean_cal_img, (1920,1080))

   mask_file = "/mnt/ams2/meteor_archive/{}/CAL/MASKS/{}_mask.png".format(station_id, cam_id)
   if os.path.exists(mask_file) is True:
      mask = cv2.imread(mask_file)
      #mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
      mask = cv2.resize(mask, (1920,1080))
   else:
      mask = np.zeros((1080,1920),dtype=np.uint8)
   if len(mask.shape) == 3:
      mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
   if len(clean_cal_img.shape) == 3:
      clean_cal_img = cv2.cvtColor(clean_cal_img, cv2.COLOR_BGR2GRAY)


   clean_cal_img = cv2.subtract(clean_cal_img, mask)
   

   cat_stars, short_bright_stars, cat_image = get_catalog_stars(cal_params)

   good_stars = []
   star_objs = []
   bad_star_objs = []
   bad_count = 0
   for star in cat_stars[0:100]:
      name,mag,ra,dec,new_cat_x,new_cat_y,zp_cat_x,zp_cat_y = star
      #if bad_count > 25:
      #   continue 

      mcx1 = int(new_cat_x - 25)
      mcx2 = int(new_cat_x + 25)
      mcy1 = int(new_cat_y - 25)
      mcy2 = int(new_cat_y + 25)
      if mcx1 < 0 or mcx2 > 1920 or mcy1 < 0 or mcy2 > 1080:
         continue
      crop_img = clean_cal_img[mcy1:mcy2,mcx1:mcx2]
      # 10x bigger
      show_img = clean_cal_img.copy()
      cv2.rectangle(show_img, (int(mcx1), int(mcy1)), (int(mcx2) , int(mcy2) ), (255, 255, 255), 1)

      ow = mcx2 - mcx1
      oh = mcy2 - mcy1
      crop_img_big = cv2.resize(crop_img, (ow * 10,oh * 10))


      star_obj = eval_star_crop(crop_img, cal_fn, mcx1, mcy1, mcx2, mcy2)


      show_image_pil = Image.fromarray(show_img)
      show_image_draw = ImageDraw.Draw(show_image_pil)

      crop_image_pil = Image.fromarray(crop_img_big)
      crop_image_draw = ImageDraw.Draw(crop_image_pil)
    
      crop_text = "Star: {} Mag: {} X/Y {}/{}".format(name, mag , str(int(new_cat_x)), str(int(new_cat_y)))
      crop_text2 = "YN: {} Flux: {}".format(str(int(star_obj['star_yn'])) + "%", str(int(star_obj['star_flux'])))
    
      crop_image_draw.text((20, 10), str(crop_text), font = font, fill="white")
      crop_image_draw.text((20, 475), str(crop_text2), font = font, fill="white")

      crop_img_big = np.asarray(crop_image_pil) 
      if len(crop_img_big.shape) == 3:
         crop_img_big = cv2.cvtColor(crop_image_pil, cv2.COLOR_RGB2BGR)


      if len(star_obj['cnts']) >= 1:


         cx1 = star_obj['cnts'][0][0] * 10
         cy1 = star_obj['cnts'][0][1] * 10
         cx2 = cx1 + (star_obj['cnts'][0][2] * 10)
         cy2 = cy1 + (star_obj['cnts'][0][3] * 10)

         ccx = int((cx1 + cx2) / 2)
         ccy = int((cy1 + cy2) / 2)

         six = mcx1 + (ccx/10)
         siy = mcy1 + (ccy/10)

         cv2.rectangle(crop_img_big, (int(cx1), int(cy1)), (int(cx2) , int(cy2) ), (0, 0, 255), 2)


         cv2.circle(show_img, (int(star_obj['star_x']),int(star_obj['star_y'])), 10, (255,255,255),1)

         cv2.circle(crop_img_big, (int(ccx),int(ccy )), star_obj['radius']* 10, (0,69,255),1)

         cv2.line(crop_img_big, (int(250),int(0)), (int(250),int(500)), (255,255,255), 1)
         cv2.line(crop_img_big, (int(0),int(250)), (int(500),int(250)), (255,255,255), 1)

         cv2.line(crop_img_big, (int(250),int(250)), (ccx,ccy), (255,255,255), 1)

      #if star_obj['valid_star'] is True:
      #   print("GOOD STAR", mag, star_obj)
      if star_obj['valid_star'] is False:
         
         cv2.circle(show_img, (int(star_obj['star_x']),int(star_obj['star_y'])), 10, (0,0,255),1)
         cv2.rectangle(crop_img_big, (int(0), int(0)), (int(499) , int(499) ), (0, 0, 255), 2)
         #print("BAD STAR", mag, star_obj)
         bad_count += 1


         new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(star_obj['star_x'],star_obj['star_y'],cal_fn,cal_params,json_conf)
         match_dist = angularSeparation(ra,dec,img_ra,img_dec)
         cat_dist = calc_dist((star_obj['star_x'],star_obj['star_y']),(new_cat_x,new_cat_y))
         center_dist = calc_dist((960,540),(new_cat_x,new_cat_y))
         star_obj['star_name'] = name
         star_obj['mag'] = mag 
         star_obj['ra'] = ra
         star_obj['dec'] = dec
         star_obj['img_ra'] = img_ra
         star_obj['img_dec'] = img_dec
         star_obj['img_az'] = img_az
         star_obj['img_el'] = img_el
         star_obj['proj_x'] = new_x
         star_obj['proj_y'] = new_y
         star_obj['cat_x'] = new_cat_x
         star_obj['cat_y'] = new_cat_y
         
         star_obj['img_x'] = star_obj['star_x'] 
         star_obj['img_y'] = star_obj['star_y']
         star_obj['center_dist'] = int(center_dist)
         star_obj['total_res_deg'] = match_dist
         star_obj['total_res_px'] = cat_dist 

         bad_star_objs.append(star_obj)
      else:
         cv2.circle(show_img, (int(star_obj['star_x']),int(star_obj['star_y'])), 10, (0,255,0),1)
         cv2.rectangle(crop_img_big, (int(0), int(0)), (int(499) , int(499) ), (0, 255, 0), 2)
         new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(six,siy,cal_fn,cal_params,json_conf)

         match_dist = angularSeparation(ra,dec,img_ra,img_dec)
         cat_dist = calc_dist((six,siy),(new_cat_x,new_cat_y))
         center_dist = calc_dist((960,540),(new_cat_x,new_cat_y))
         good_stars.append(( name,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_obj['star_flux'] ))
         star_obj['star_name'] = name
         star_obj['mag'] = mag 
         star_obj['ra'] = ra
         star_obj['dec'] = dec
         star_obj['img_ra'] = img_ra
         star_obj['img_dec'] = img_dec
         star_obj['img_az'] = img_az
         star_obj['img_el'] = img_el
         star_obj['proj_x'] = new_x
         star_obj['proj_y'] = new_y
         star_obj['cat_x'] = new_cat_x
         star_obj['cat_y'] = new_cat_y
         star_obj['img_x'] = six 
         star_obj['img_y'] = siy 
         star_obj['center_dist'] = int(center_dist)
         star_obj['total_res_deg'] = match_dist
         star_obj['total_res_px'] = cat_dist 
         star_objs.append(star_obj)


      if SHOW == 1:
         cv2.imshow('pepe_crop', crop_img_big)
         cv2.imshow('pepe', show_img)
         cv2.resizeWindow("pepe", 1920, 1080)
         cv2.waitKey(30)

   show_img = clean_cal_img.copy()

   print("MAG TABLE!")
   star_objs = sorted(star_objs, key=lambda x: x['mag'], reverse=False)
   new_star_objs = []
   all_res = []
   for so in  star_objs:
      all_res.append(so["total_res_px"]) 
      if so['star_name'] == "":
         name = "---"
      else:
         name = so['star_name']
      #print("STAR:", name, so['mag'], so['star_flux'], so['center_dist'], round(so['total_res_deg'],2), round(so['total_res_px'],2), so['star_yn'] )
   final_res = np.mean(all_res) 
   if final_res < 2:
      final_res = 2

   if final_res > 9:
      final_res = 9
   if final_res < 1:
      final_res = 1 

   for so in  star_objs:
      if so["total_res_px"] <= final_res * 2:
         print("KEEP", so["total_res_px"], final_res)
         new_star_objs.append(so)
      else:
         print("REJECT", so["total_res_px"], final_res)
   star_objs = new_star_objs  

   star_obj_report(star_objs)
   #print("DIST TABLE!")
   #for star in good_stars:
   #   name,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_flux = star
   #   center_dist = int(calc_dist((960,540),(new_cat_x,new_cat_y)))
   #   print("STAR:", name, center_dist, match_dist, cat_dist)

   if SHOW == 1:
      cv2.imshow('pepe', show_img)
      cv2.waitKey(30)



   return(star_objs, bad_star_objs)

def cal_params_report(cal_fn, cal_params,json_conf, show_img, waitVal=30, mcp=None):
   from prettytable import PrettyTable as pt   

   cal_params_nlm = cal_params.copy()
   cal_params_nlm['x_poly'] = np.zeros(shape=(15,), dtype=np.float64)
   cal_params_nlm['y_poly'] = np.zeros(shape=(15,), dtype=np.float64)
   cal_params_nlm['x_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
   cal_params_nlm['y_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
   
   tb = pt()
   tb.field_names = ["Star","Magnitude", "Flux", "RA", "Dec", "Cat X", "Cat Y", "Img X", "Img Y", "Res PX", "Res Deg"]
   #print("CAL PARAMS FOR {}".format(cal_fn))
   res_pxs = []
   res_degs = []
   zp_res_pxs = []
   zp_res_degs = []
   new_cat_image_stars = []
   center_res_pxs = []

   for star in cal_params['cat_image_stars']:
      dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,bp = star
      new_cat_x, new_cat_y = get_xy_for_ra_dec(cal_params, ra, dec)

      # with the best lens model 
      new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(six,siy,cal_fn,cal_params,json_conf)

      # with NO lens model 
      zp_x, zp_y, zp_img_ra,zp_img_dec, zp_img_az, zp_img_el = XYtoRADec(six,siy,cal_fn,cal_params_nlm,json_conf)
      zp_cat_x, zp_cat_y = get_xy_for_ra_dec(cal_params_nlm, ra, dec)

      cat_dist = calc_dist((six,siy),(new_cat_x,new_cat_y))
      match_dist = angularSeparation(ra,dec,img_ra,img_dec)

      zp_cat_dist = calc_dist((six,siy),(zp_x,zp_y))
      zp_match_dist = angularSeparation(ra,dec,zp_img_ra,zp_img_dec)


      res_pxs.append(cat_dist)
      res_degs.append(match_dist)

      zp_res_pxs.append(zp_cat_dist)
      zp_res_degs.append(zp_match_dist)
      center_dist = calc_dist((six,siy),(1920/2,1080/2))

      if center_dist < 600:
         center_res_pxs.append(cat_dist)


      # image star point (yellow)
      cv2.circle(show_img, (int(six),int(siy)), 3, ( 0, 234, 255),1)

      # Projected image star point 
      cv2.putText(show_img, "+",  (int(new_x-5),int(new_y+4)), cv2.FONT_HERSHEY_SIMPLEX, .4, (255,255,255), 1)
      cv2.circle(show_img, (int(new_x),int(new_y)), 3, (255,69,255),1)

      # corrected catalog star point using lens model
      cv2.rectangle(show_img, (int(new_cat_x - 7), int(new_cat_y-7)), (int(new_cat_x+7) , int(new_cat_y+7) ), (255, 255, 255), 1)

      # zero poly catalog star point ( no lens model)
      cv2.rectangle(show_img, (int(zp_cat_x - 5), int(zp_cat_y-5)), (int(zp_cat_x+5) , int(zp_cat_y+5) ), (0, 0, 255), 1)

      tb.add_row([dcname, round(mag,2), int(bp), round(ra,2), round(dec,2), round(new_cat_x,2), round(new_cat_y,2), round(six,2), round(siy,2), round(cat_dist,2), round(match_dist,2)])
      new_cat_image_stars.append((dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,bp ))

   cv2.circle(show_img, (int(1920/2),int(1080/2)), 400, (128,128,128),1)
   cv2.circle(show_img, (int(1920/2),int(1080/2)), 800, (128,128,128),1)

   mean_center_res = np.mean(center_res_pxs)
   cal_params['mean_center_res'] = mean_center_res
   #print(tb)
   report_txt = str(tb)
   tb = pt()
   tb.field_names = ["Cal Paramater","Value"]
   # CENTER ??
   cal_params['total_res_px'] = mean_center_res
   #cal_params['total_res_px'] = np.mean(res_pxs)
   cal_params['total_res_deg'] = np.mean(res_degs)
   tb.add_row(["Center RA", cal_params['ra_center']] )
   tb.add_row(["Center Dec", cal_params['dec_center']])
   tb.add_row(["Center Az", cal_params['center_az']])
   tb.add_row(["Center El", cal_params['center_el']])
   tb.add_row(["Pixel Scale", cal_params['pixscale']])
   tb.add_row(["Residuals (Px)", cal_params['total_res_px']])
   tb.add_row(["Residuals (Deg)", cal_params['total_res_deg']])
   tb.add_row(["Residuals (Cnt PX)", cal_params['mean_center_res']])
   #print(tb)
   report_txt += str(tb)
   desc = "Stars: {} Res PX: {} Res Deg: {}".format(len(cal_params['cat_image_stars']), round(cal_params['total_res_px'],3), round(cal_params['total_res_deg'],3))
   cv2.putText(show_img, desc,  (int(10),int(1060)), cv2.FONT_HERSHEY_SIMPLEX, .4, (255,255,255), 1)

   cal_params['cat_image_stars'] = new_cat_image_stars
   #if SHOW == 1:
   #   cv2.imshow('pepe', show_img)
   #   cv2.waitKey(waitVal)

   return(cal_params, report_txt, show_img)


def star_obj_report(star_objs):
   #pip install prettytable
   from prettytable import PrettyTable as pt   
   tb = pt()
   tb.field_names = ["Star","Magnitude","Flux","Cen Dist", "Res Deg", "Res PX", "AI YN", "CRR"]

   star_objs = sorted(star_objs, key=lambda x: x['mag'], reverse=False)
   for so in  star_objs:
      if so['star_name'] == "":
         so['star_name'] = "---"
      center_res_ratio = round(so['total_res_px'] / so['center_dist'] , 2)
      tb.add_row([so['star_name'], so['mag'], round(so['star_flux'],2), so['center_dist'], round(so['total_res_deg'],3), round(so['total_res_px'],3), so['star_yn'], center_res_ratio])
   print(tb)


def eval_star_crop(crop_img, cal_fn, x1, y1,x2,y2, star_cat_info=None ):
   reject_reason = ""
   learn_dir = "/mnt/ams2/datasets/cal_stars/"
   if os.path.exists(learn_dir) is False:
      os.makedirs(learn_dir)
   roi_end = "_" + str(x1) + "_" + str(y1) + "_" + str(x2) + "_" + str(y2)
   star_key= cal_fn.replace("-stacked-calparams.json", roi_end)

   star_img_file = learn_dir + star_key + ".jpg"
   star_data_file = learn_dir + star_key + ".json"

   if False:
      try:
         if os.path.exists(star_data_file) is True:
            data = load_json_file(star_data_file) 
            print("USE EXISTING STAR DATA!")
            return(data)
      except:
         os.system("rm " + star_data_file)


   radius = 2
   star_flux = 0
   valid_star = True 
   if len(crop_img.shape) == 3:
      gray_img  = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
      gray_orig = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
   else:
      gray_img  = crop_img 
      gray_orig = crop_img 
   show_img = crop_img.copy()
   cx = 0
   cy = 0

   min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(gray_img)
   avg_val = np.mean(crop_img)
   if avg_val > 100:
      reject_reason = "AVG VAL TOO HIGH: " +  str(avg_val)
      valid_star = False
   min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(gray_img)
   pxd = max_val - avg_val

   if pxd < 15:
      reject_reason = "PXD TOO LOW: " +  str(pxd)
      valid_star = False

   cch, ccw = crop_img.shape[:2]
   #print(cch,ccw)
   #print(crop_img.shape)
   blval = gray_img[cch-1,0]
   brval = gray_img[cch-1,ccw-1]

   #print(blval)
   #print(brval)
   if blval == 0 or brval == 0:
      reject_reason += "too close to mask: " +  str(blval) + " " + str(brval)
      valid_star = False

   # check for cnt
   #thresh_val = max_val * .8

   thresh_val = find_best_thresh(gray_img)
   if thresh_val is None:
      thresh_val = 100
   _, crop_thresh = cv2.threshold(gray_img, thresh_val, 255, cv2.THRESH_BINARY)
   cnts = get_contours_in_image(crop_thresh)

   # lower sens if not found
   if len(cnts) == 0:
      thresh_val = max_val * .7

      _, crop_thresh = cv2.threshold(crop_img, thresh_val, 255, cv2.THRESH_BINARY)
      cnts = get_contours_in_image(crop_thresh)

   if pxd > 15:
      if len(cnts) == 0:
         cnts = [[mx,my,1,1]]

   if len(cnts) == 1:
      x,y,w,h = cnts[0]
      cx = x + (w/2)
      cy = y + (h/2)
      if w > h:
         radius = w 
      else:
         radius = h 
      if w > 4 or h > 4:
         valid_star = False 
      star_flux = do_photo(gray_img, (cx,cy), radius)
      #try:
      #except:
      #   star_flux = 0
   #else:
   #   cv2.imshow('thresh', crop_thresh)

   if star_flux > 0 and valid_star is True:
      # if you want AI write the file and call this
      #cv2.imwrite(star_img_file,crop_img)
      #star_yn = ai_check_star(crop_img, star_img_file)
      star_yn = -1
      #print("CHECK AI:", star_yn)
   else:
      star_yn = -1

   if pxd < 8 and (len(cnts) == 0):
      valid_star = False 
      reject_reason += "LOW PXD AND NO CNT"
   if pxd < 1 :
      valid_star = False 
      reject_reason += "LOW PXD "
   if star_flux <=  30:
      valid_star = False 
      reject_reason += "LOW FLUX " + str(star_flux)

   if radius < 1:
      radius = 1

   # return : cnts, star_flux, pxd, star_yn, radius
   star_obj = {}
   star_obj['cal_fn'] = cal_fn
   star_obj['star_x'] = x1 + cx
   star_obj['star_y'] = y1 + cy
   star_obj['x1'] = x1
   star_obj['y1'] = y1
   star_obj['x2'] = x2
   star_obj['y2'] = y2
   star_obj['cnts'] = cnts
   star_obj['star_flux'] = round(star_flux,2)
   star_obj['pxd'] = int(pxd)
   star_obj['brightest_point'] = [mx,my]
   star_obj['brightest_val'] = int(max_val)
   star_obj['bg_avg'] = int(avg_val)
   star_obj['star_yn'] = int(star_yn)
   star_obj['radius'] = radius
   star_obj['valid_star'] = valid_star
   star_obj['reject_reason'] = reject_reason
   star_obj['thresh_val'] = thresh_val
   star_obj['cx'] = cx 
   star_obj['cy'] = cy
   if star_cat_info is not None:
      name, mag, ra,dec = star_cat_info
      star_obj['name'] = name
      star_obj['mag'] = mag 
      star_obj['ra'] = ra
      star_obj['dec'] = dec

   else:
      star_obj['x'] = star_obj['star_x']
      star_obj['y'] = star_obj['star_y']
      #star_obj['close_stars'] = find_close_stars(star_obj)

   #for key in star_obj:
   #   print(key, star_obj[key])

   #star_obj['crop_thresh'] = crop_thresh

   #save_json_file(star_data_file, star_obj)
   #print("SAVED:", star_data_file)
   #print("STAR OBJ", star_obj)
   return ( star_obj)

def find_best_thresh(gray_img):

   min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(gray_img)
   avg_val = np.mean(gray_img)
   pxd = max_val - avg_val

   for i in range(0,5):
      fact = (i + 1 * 2) / 100
      thresh_val = max_val * (1-fact) 
      if pxd < 5:
         return(thresh_val)

      _, crop_thresh = cv2.threshold(gray_img, thresh_val, 255, cv2.THRESH_BINARY)
      cnts = get_contours_in_image(crop_thresh)
      #print("THRESH, PXD:", thresh_val, pxd)
      #cv2.imshow("crop", crop_thresh)
      #cv2.waitKey(30)
      if len(cnts) == 1:
         x,y,w,h = cnts[0]
         if w != gray_img.shape[1] and h != gray_img.shape[0]:
            return(thresh_val)


def find_close_stars(star_obj):
   cal_fn = star_obj['cal_fn']
   x = star_obj['x']
   y = star_obj['y']
   star_flux = star_obj['star_flux']
   sql = """
      SELECT cal_fn, name, mag, ra, dec, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, 
             img_x, img_y, star_flux, star_yn, star_pd, star_found, lens_model_version 
        FROM calfile_catalog_stars
       WHERE cal_fn = ?
         AND (new_cat_x > ? and new_cat_x < ?)
         AND (new_cat_y > ? and new_cat_y < ?)
   """
   center_dist = calc_dist((x,y),(1920/2,1080/2))
   if center_dist < 800:
      x1 = x - 50
      x2 = x + 50
      y1 = y - 50
      y2 = y + 50
   else:
      x1 = x - 75 
      x2 = x + 75
      y1 = y - 75
      y2 = y + 75

   # Adjust search box based on where the img star is
   # right side image, cat must be greater than source!
   if x > 1620:
      x1 = x 
      x2 = x1 + 50 
   # left side image, cat must be greater than source!
   if x < 300:
      x2 = x 
      x1 = x2 - 50 

   ivals = [cal_fn, x1, x2, y1, y2]
   cur.execute(sql, ivals)
   rows = cur.fetchall()
   stars = []
   #print(sql)
   #print(ivals)
   #print("ROWS", len(rows))
   for row in rows:
      cal_fn, name, mag, ra, dec, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, \
         img_x, img_y, cat_star_flux, star_yn, star_pd, star_found, lens_model_version  = row

      slope = (y - new_cat_y) / (x - new_cat_x)
      zp_slope = (y - zp_cat_y) / (x - zp_cat_x)
      dist = calc_dist((x,y),(new_cat_x,new_cat_y))
      zp_dist = calc_dist((x,y),(zp_cat_x,zp_cat_y))


      valid = True

      if center_dist > 600:
         if x < 600 and y < 400: # top left corner
            if new_cat_x > x:
               valid = False
            if new_cat_y > y:
               valid = False
         if x < 600 and y > 1080 - 400: # bottom left corner
            if new_cat_x > x:
               valid = False
            if new_cat_y < y:
               valid = False
         if x > 1920 - 600 and y < 400: # top right corner
            if new_cat_x < x:
               valid = False
            if new_cat_y > y:
               valid = False
         if x > 1920 - 600 and y > 1080- 400: # bottom right corner
            if new_cat_x < x:
               valid = False
            if new_cat_y < y:
               valid = False
         
         # y_dist should not be more than x_dist on edge
         y_dist = abs(new_cat_y - y)
         x_dist = abs(new_cat_x - x)
         if y_dist > x_dist:
            valid = False

      if star_flux is None:
         valid = False
      elif star_flux > 1000 and mag >= 4:
         valid = False
      if center_dist < 600:
         if zp_dist > 25:
            valid = False 

      if valid is True:
         stars.append(( cal_fn, name, mag, ra, dec, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, \
            img_x, img_y, star_flux, star_yn, star_pd, star_found, lens_model_version, \
            slope, zp_slope, dist, zp_dist))

   stars = sorted(stars, key=lambda x: x[-2], reverse=False)

   return(stars)

#def cal_main(cal_file):
#   print("Menu")

   # GET IMAGE STARS IS DONE. 

   # GET CATALOG STARS
def get_default_cal_for_file(cam_id, obs_file, img, con, cur, json_conf):

   sql = """
       SELECT substr(cal_fn, 0,11), az, el, position_angle,pixel_scale, res_px 
        FROM calibration_files
       WHERE cal_fn like ?
         AND cal_fn like ?
   """

   year_month = obs_file[0:7] 
   ivals = [year_month + "%", "%" + cam_id + "%"]

   print(sql, ivals)
   cur.execute(sql, ivals)
   rows = cur.fetchall()

   if len(rows) == 0:
      print("this method will not work. need to revert back to the range file", obs_file)
      default_cp = get_default_cal_for_file_with_range (cam_id, obs_file, None, con, cur, json_conf)
      return(default_cp)
   else:
      print("ROWS:", len(rows))

   #exit()

   best = []
   best_dict = {}
   dates = []
   azs = []
   els = []
   poss = []
   pxs = []
   ress = []

   best_dates = []
   best_azs = []
   best_els = []
   best_poss = []
   best_pxs = []
   best_ress = []

   for row in rows:
      print("ROW:", row)
      date, az, el, pos, px, res = row 
      dates.append(date)
      azs.append(az)
      els.append(el)
      poss.append(pos)
      pxs.append(px)
      if res is not None:
         ress.append(res)

   med_az = np.median(azs)
   med_el = np.median(els)
   med_pos = np.median(poss)
   med_pxs = np.median(pxs)

   print(ress)
   med_res = np.median(ress)


   for row in rows:
     
      date, az, el, pos, px, res = row 
      if res is None:
         continue
      print(med_res * 1.2, row)

      if res <= med_res * 1.2:
         best_dates.append(date)
         best_azs.append(az)
         best_els.append(el)
         best_poss.append(pos)
         best_pxs.append(pxs)
         best_ress.append(res)

   best_med_az = np.median(best_azs)
   best_med_el = np.median(best_els)
   best_med_pos = np.median(best_poss)
   best_med_pxs = np.median(best_pxs)
   best_med_res = np.median(best_ress)

   print("MED/BEST")
   print(med_az, best_med_az)
   print(med_el, best_med_el)
   print(med_pos, best_med_pos)
   print(med_pxs, best_med_pxs)
   print(med_res, best_med_res)

   autocal_dir = "/mnt/ams2/cal/"
   mcp_file = autocal_dir + "multi_poly-" + json_conf['site']['ams_id'] + "-" + cam_id + ".info"
   if os.path.exists(mcp_file) == 1:
      mcp = load_json_file(mcp_file)
      if "cal_version" not in mcp:
         mcp['cal_version'] = 0
   else:
      mcp = {} 
      mcp['x_poly'] = np.zeros(shape=(15,), dtype=np.float64).tolist()
      mcp['y_poly'] = np.zeros(shape=(15,), dtype=np.float64).tolist()
      mcp['x_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64).tolist()
      mcp['y_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64).tolist()


   mcp['center_az'] = best_med_az
   mcp['center_el'] = best_med_el
   mcp['position_angle'] = best_med_pos
   mcp['pixscale'] = best_med_pxs
   mcp['cat_image_stars'] = []
   mcp['user_stars'] = []
   mcp = update_center_radec(obs_file,mcp,json_conf)
   mcp['total_res_px'] = 0 
   mcp['total_res_deg'] = 0


   #exit()
   return(mcp)

def get_default_cal_for_file_with_range(cam_id, obs_file, img, con, cur, json_conf):
   # use this function to get a default cal when no stars or info 
   # is present

   autocal_dir = "/mnt/ams2/cal/"
   mcp_file = autocal_dir + "multi_poly-" + json_conf['site']['ams_id'] + "-" + cam_id + ".info"
   if os.path.exists(mcp_file) == 1:
      mcp = load_json_file(mcp_file)
      if "cal_version" not in mcp:
         mcp['cal_version'] = 0
   else:
      mcp = {} 
      mcp['x_poly'] = np.zeros(shape=(15,), dtype=np.float64).tolist()
      mcp['y_poly'] = np.zeros(shape=(15,), dtype=np.float64).tolist()
      mcp['x_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64).tolist()
      mcp['y_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64).tolist()

   try:
      range_data = get_cal_range(obs_file, img, con, cur, json_conf)
   except:
      print("No range data! for camera.")
      return(None)
   print("RANGE DATA")

   for row in range_data:
      print(row)
   ( rcam_id, rend_dt, rstart_dt, elp, az, el, pos, pxs, res) = range_data[0]

   if mcp is None:
      mcp = {}
   if mcp is not None:
      mcp['center_az'] = az
      mcp['center_el'] = el
      mcp['position_angle'] = pos
      mcp['pixscale'] = pxs 
      mcp['user_stars'] = []
      mcp['cat_image_stars'] = []
      mcp = update_center_radec(obs_file,mcp,json_conf)
      mcp['total_res_px'] = 999
      mcp['total_res_deg'] = 999

   return(mcp)

def get_cal_range(obs_file, img, con, cur, json_conf):

   #show_img = img.copy()

   (cal_date, cam_id, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(obs_file)
   lens_model = load_json_file("/mnt/ams2/cal/multi_poly-" + json_conf['site']['ams_id'] + "-" + cam_id + ".info")
   cal_range = load_json_file("/mnt/ams2/cal/" + json_conf['site']['ams_id'] + "_cal_range.json")
 
   #print("OBS FILE:", obs_file)
   #img = cv2.imread(obs_file.replace(".mp4", "-stacked.jpg"))

   #star_points,stars_image = get_star_points(obs_file, img, {}, station_id, cam_id, {})


   match_range_data = []
   for row in cal_range:
      rcam_id, rend_date, rstart_date, az, el, pos, pxs, res = row
      if np.isnan(az) is True:
         print("NAN SKIP")
         continue

      rcam_id = row[0]
      rend_date = row[1]
      rstart_date = row[2]

      rend_dt = datetime.datetime.strptime(rend_date, "%Y_%m_%d")
      rstart_dt = datetime.datetime.strptime(rstart_date, "%Y_%m_%d")

      if rcam_id == cam_id and np.isnan(az) == False:
         elp = abs((cal_date - rend_dt).total_seconds()) / 86400
         match_range_data.append(( rcam_id, rend_dt, rstart_dt, elp, az, el, pos, pxs, res))

   return(match_range_data)



def get_best_cal_files(cam_id, con, cur, json_conf, limit=500):
   sql = """
      SELECT cal_fn, count(*) AS ss, avg(res_px) as rs 
        FROM calfile_paired_stars 
       WHERE cal_fn like ?
         AND res_px IS NOT NULL
    GROUP BY cal_fn 
    ORDER BY ss desc, rs
    LIMIT ? 
   """
   dvals = ["%" + cam_id + "%", limit]
   cur.execute(sql, dvals)
   rows = cur.fetchall()
   best = []
   best_dict = {}
   for row in rows:
      x_cal_fn, total_stars, avg_res = row
      best.append((x_cal_fn, total_stars, avg_res))
      best_dict[x_cal_fn] = [x_cal_fn,total_stars,avg_res]
   return(best, best_dict)


def characterize_best(cam_id, con, cur, json_conf,limit=500, cal_fns=None):


   #(f_datetime, cam_id, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(cal_fn)
   # best 
   my_limit = limit
   limit = 500 
   calfiles_data  = load_cal_files(cam_id, con,cur)

   autocal_dir = "/mnt/ams2/cal/"
   mcp_file = autocal_dir + "multi_poly-" + json_conf['site']['ams_id'] + "-" + cam_id + ".info"
   if os.path.exists(mcp_file) == 1:
      mcp = load_json_file(mcp_file)
      if "cal_version" not in mcp:
         mcp['cal_version'] = 0
      mcp['cal_version'] += 1
   else:
      mcp = None


   station_id = json_conf['site']['ams_id']
   all_cal_files, best_dict = get_best_cal_files(cam_id, con, cur, json_conf)

   sql = """
      SELECT cal_fn, count(*) AS ss, avg(res_px) as rs 
        FROM calfile_paired_stars 
       WHERE cal_fn like ?
         AND res_px IS NOT NULL
    GROUP BY cal_fn 
    ORDER BY rs
    LIMIT {}
   """.format(limit)
   dvals = ["%" + cam_id + "%"]
   #print(sql)
   #print(dvals)
   cur.execute(sql, dvals)
   rows = cur.fetchall()

   for row in rows:
      print(row)
   if len(rows) == 0:
      print("FAILED no rows")
      exit()

   print("CHAR ROWS:", len(rows))
   updated_stars = []
   updated_stars_zp = []
   res_0 = []
   res_200 = []
   res_400 = []
   res_600 = []
   res_800 = []
   res_900 = []
   res_1000 = []
   
   #for cal_fn in best_dict:
   #if cal_fns is not None:
   #   rows = cal_fns
   good = 0
   bad = 0
   for row in rows:
      #print("ROW:", row)
      if row[2] is None:
         continue
      cal_fn = row[0]

      if False:
         # OLD / SLOW / NOT NEEDED
         resp = start_calib(cal_fn, json_conf, calfiles_data, mcp)

         if resp is not False:
            (station_id, cal_dir, cal_json_file, cal_img_file, cal_params, cal_img, clean_cal_img, mask_file,mcp) = resp
         else:
            print("STAR CALIB FAILED:", cal_fn)
            continue 
      # better way to do this
      if cal_fn in calfiles_data:
         cal_data = calfiles_data[cal_fn]
         cal_params = cal_data_to_cal_params(cal_fn, cal_data,json_conf, mcp)


      stars,cat_stars = get_paired_stars(cal_fn, cal_params, con, cur)

      cal_params_nlm = cal_params.copy()
      cal_params_nlm['x_poly'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params_nlm['y_poly'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params_nlm['x_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
      cal_params_nlm['y_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)


      for star in cat_stars:
         (dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,img_x,img_y,res_px,star_flux) = star
         new_cat_x, new_cat_y = get_xy_for_ra_dec(cal_params, ra, dec)
         new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(img_x,img_y,cal_fn,cal_params,json_conf)

         zp_cat_x, zp_cat_y = get_xy_for_ra_dec(cal_params_nlm, ra, dec)
         zp_x, zp_y, zp_img_ra,zp_img_dec, zp_img_az, zp_img_el = XYtoRADec(img_x,img_y,cal_fn,cal_params_nlm,json_conf)

         match_dist = angularSeparation(ra,dec,img_ra,img_dec)
         res_px = calc_dist((img_x,img_y),(new_cat_x,new_cat_y))

         zp_match_dist = angularSeparation(ra,dec,img_ra,img_dec)
         zp_res_px = calc_dist((img_x,img_y),(zp_cat_x,zp_cat_y))

         zp_center_dist = calc_dist((1920/2,1080/2),(zp_cat_x,zp_cat_y))
         if zp_center_dist < 200:
            res_0.append(zp_res_px)
         if 200 <= zp_center_dist < 400:
            res_200.append(zp_res_px)
         if 400 <= zp_center_dist < 600:
            res_400.append(zp_res_px)
         if 600 <= zp_center_dist < 800:
            res_600.append(zp_res_px)
         if 800 <= zp_center_dist < 900:
            res_800.append(zp_res_px)
         if 900 <= zp_center_dist < 1000:
            res_900.append(zp_res_px)
         if zp_center_dist >= 1000:
            res_1000.append(zp_res_px)

         updated_stars.append((cal_fn,dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,img_x,img_y,res_px,star_flux))
         updated_stars_zp.append((cal_fn,dcname,mag,ra,dec,zp_img_ra,zp_img_dec,zp_match_dist,zp_x,zp_y,zp_img_az,zp_img_el,zp_cat_x,zp_cat_y,img_x,img_y,zp_res_px,star_flux))


         #print("NEW/ZP:", new_cat_x, zp_cat_x, new_cat_y, zp_cat_y)
         #print("ZP CENTER/RES:", zp_center_dist, zp_res_px)

      #plot_star_chart(clean_cal_img, updated_stars, updated_stars_zp)

   print("RES ZONES:")
   print("0-200", np.median(res_0))
   print("200-400", np.median(res_200))
   print("400-600", np.median(res_400))
   print("600-800", np.median(res_600))
   print("800-900", np.median(res_800))
   print("900-1000", np.median(res_900))
   print("1000+", np.median(res_1000))

   try:
      base_image = clean_cal_img.copy()
   except:
      base_image = np.zeros((1080,1920,3),dtype=np.uint8)

   if False:
      cv2.circle(base_image, (int(1920/2),int(1080/2)), 200, (128,128,128),1)
      cv2.circle(base_image, (int(1920/2),int(1080/2)), 400, (128,128,128),1)
      cv2.circle(base_image, (int(1920/2),int(1080/2)), 600, (128,128,128),1)
      cv2.circle(base_image, (int(1920/2),int(1080/2)), 800, (128,128,128),1)
      cv2.circle(base_image, (int(1920/2),int(1080/2)), 900, (128,128,128),1)
      cv2.circle(base_image, (int(1920/2),int(1080/2)), 1000, (128,128,128),1)

      cv2.putText(base_image, str(int(np.median(res_0))),  (960,540), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 1)
      cv2.putText(base_image, str(int(np.median(res_200))),  (720,400), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 1)
      cv2.putText(base_image, str(int(np.median(res_400))),  (550,300), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 1)
      cv2.putText(base_image, str(int(np.median(res_600))),  (350,195), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 1)
      cv2.putText(base_image, str(int(np.median(res_800))),  (200,115), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 1)
      cv2.putText(base_image, str(int(np.median(res_900))),  (125,60), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 1)
      cv2.putText(base_image, str(int(np.median(res_1000))),  (55,30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 1)

      cv2.line(base_image, (int(0),int(0)), (int(1920/2),int(1080/2)), [255,255,255], 1)
   best_stars = []

   ic = 0
   for star in updated_stars_zp:
      (cal_fn,dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,zp_cat_x,zp_cat_y,img_x,img_y,res_px,star_flux) = star
      if True:
         zp_center_dist = calc_dist((1920/2,1080/2),(zp_cat_x,zp_cat_y))
         if zp_center_dist < 200:
            limit = np.median(res_0)
         if 200 <= zp_center_dist < 400:
            limit = np.median(res_200)
         if 400 <= zp_center_dist < 600:
            limit = np.median(res_400)
         if 600 <= zp_center_dist < 800:
            limit = np.median(res_600)
         if 800 <= zp_center_dist < 900:
            limit = np.median(res_800)
         if 900 <= zp_center_dist < 1000:
            limit = np.median(res_900)
         if zp_center_dist >= 1000:
            limit = np.median(res_1000)

      fact = abs(res_px / limit)
      if .7 <= fact <= 1.3:
         good += 1
      else:
         print("BAD Fact:", bad, res_px, limit, fact)
         bad += 1
      if .5 <= fact <= 1.5:
      #if True:
         #cv2.putText(base_image, str(int(res_px)),  (int(new_x),int(new_y)), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,255,0), 1)
         cv2.line(base_image, (int(zp_cat_x),int(zp_cat_y)), (int(img_x),int(img_y)), (0,255,0), 2)
         (cal_fn,dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,img_x,img_y,res_px,star_flux) = updated_stars[ic]
         best_stars.append((cal_fn,dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,zp_cat_x,zp_cat_y,img_x,img_y,res_px,star_flux)) 
      #else:
      #   cv2.putText(base_image, str(int(res_px)),  (int(new_x),int(new_y)), cv2.FONT_HERSHEY_SIMPLEX, .4, (255,255,255), 1)
      ic += 1

   if SHOW == 1:
      cv2.imshow('pepe', base_image)
      cv2.waitKey(30)



   merged_stars = []
   rez = [row[-2] for row in best_stars] 
   med_rez = np.median(rez) * 1.2
   print("CAM ID/START REZ/BEST STARS:", cam_id, med_rez, len(best_stars))

   for star in best_stars:

      (cal_fn, name,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,img_x,img_y,res_px,star_flux) = star
      #if cal_fn not in best_dict:
         #print("MISSING CAL FN!", cal_fn)
      #   continue

      if cal_fn in calfiles_data:
         #(cal_fn_ex, center_az,center_el, ra_center,dec_center, position_angle, pixscale) = calfiles_data[cal_fn]
         (station_id, camera_id, cal_fn, cal_ts, center_az, center_el, ra_center, dec_center, position_angle,\
            pixscale, zp_az, zp_el, zp_ra, zp_dec, zp_position_angle, zp_pixel_scale, x_poly, \
            y_poly, x_poly_fwd, y_poly_fwd, a_res_px, a_res_deg, ai_weather, ai_weather_conf, cal_version, last_update) = calfiles_data[cal_fn]


      #match_dist = zp_res_px

      match_dist = 9999
      if res_px < med_rez: 
         print("KEEP", res_px, med_rez)
         merged_stars.append((cal_file , center_az, center_el, ra_center, dec_center, position_angle, pixscale, name,mag,ra,dec,ra,dec,match_dist,new_x,new_y,center_az,center_el,new_cat_x,new_cat_y,img_x,img_y,res_px,star_flux))
      else:
         print("SKIP", res_px, med_rez)


   if len(merged_stars) > 400:
      grid = make_grid_stars(merged_stars, mpc = None, factor = 2, gsize=50, limit=10)
      best_stars = []
      for grid_key in grid:
         print(grid_key, len(grid[grid_key]))
         just_data = sorted(grid[grid_key], key=lambda x: x[-2], reverse=False)
         rc = 0
         if len(just_data ) > 0:
            for row in just_data:
               if rc < 5:
                  best_stars.append(row)
               else:
                  break 
               rc += 1
   else:
      best_stars = merged_stars

   print("BEST STARS:", len(best_stars))

   save_json_file("/mnt/ams2/cal/" + station_id + "_" + cam_id + "_MERGED_STARS.json", merged_stars)
   save_json_file("/mnt/ams2/cal/" + station_id + "_" + cam_id + "_MERGED_STARS.json", best_stars)
   print("SAVED STARS FOR MODEL! /mnt/ams2/cal/" + station_id + "_" + cam_id + "_MERGED_STARS.json", len(best_stars), "stars")


def plot_star_chart(base_image, cat_stars, zp_cat_stars):
   for star in zp_cat_stars:
      (dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,img_x,img_y,res_px,star_flux) = star

      cv2.circle(base_image, (int(img_x),int(img_y)), 4, (135,247,252),1) # yellow

      cv2.circle(base_image, (int(new_x),int(new_y)), 4, (0,0,200),1)
      #cv2.circle(base_image, (int(new_cat_x),int(new_cat_y)), 4, (0,255,255),1)

      x1 = new_cat_x - 4 
      x2 = new_cat_x + 4 
      y1 = new_cat_y - 4 
      y2 = new_cat_y + 4 
      cv2.rectangle(base_image, (int(x1), int(y1)), (int(x2) , int(y2) ), (0, 0, 200), 1)


   for star in cat_stars:
      (dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,img_x,img_y,res_px,star_flux) = star
      cv2.circle(base_image, (int(new_x),int(new_y)), 3, (0,68,255),1)
      #cv2.circle(base_image, (int(new_cat_x),int(new_cat_y)), 3, (0,0,255),1)

      x1 = new_cat_x - 5
      x2 = new_cat_x + 5
      y1 = new_cat_y - 5
      y2 = new_cat_y + 5
      cv2.rectangle(base_image, (int(x1), int(y1)), (int(x2) , int(y2) ), (255, 255, 255), 1)


   cv2.circle(base_image, (int(1920/2),int(1080/2)), 200, (128,128,128),1)
   cv2.circle(base_image, (int(1920/2),int(1080/2)), 400, (128,128,128),1)
   cv2.circle(base_image, (int(1920/2),int(1080/2)), 600, (128,128,128),1)
   cv2.circle(base_image, (int(1920/2),int(1080/2)), 800, (128,128,128),1)
   cv2.circle(base_image, (int(1920/2),int(1080/2)), 1000, (128,128,128),1)

   if SHOW == 1:
      cv2.imshow('pepe', base_image)
      cv2.waitKey(30)


def characterize_fov(cam_id, con, cur, json_conf):
   station_id = json_conf['site']['ams_id']
   autocal_dir = "/mnt/ams2/cal/"
   mcp_file = autocal_dir + "multi_poly-" + station_id + "-" + cam_id + ".info"
   if os.path.exists(mcp_file) == 1:
      mcp = load_json_file(mcp_file)
      if "cal_version" not in mcp:
         mcp['cal_version'] = 0
      mcp['cal_version'] += 1
   else:
      mcp = None

   photo_file = "/mnt/ams2/cal/plots/" + json_conf['site']['ams_id'] + "_" + cam_id + "_MAG_FLUX.png"
   best_cal_files, best_dict = get_best_cal_files(cam_id, con, cur, json_conf, 400)
   title = json_conf['site']['ams_id'] + " " + cam_id + " CALIBRATION FLUX MAGNITUDE PLOT"

   station_id = json_conf['site']['ams_id']
   import matplotlib.pyplot as plt
   grid_img = np.zeros((1080,1920,3),dtype=np.uint8)
   # flux / mag
         #AND star_yn >= 99
   sql = """
      SELECT cal_fn, star_flux, mag 
        FROM calfile_paired_stars
       WHERE star_flux is not NULL
         and cal_fn like ?
   """
   mag_db = {}
   med_flux_db = {}

   cur.execute(sql, [ "%" + cam_id + "%"])
   rows = cur.fetchall()
   xs = []
   ys = []
   for row in rows:
      cal_fn, flx, mag = row
      if mag is None:
         continue
      if mag not in mag_db:
         mag_db[mag] = []
      mag_db[mag].append(flx)

   for mag in sorted(mag_db):
      med_flux = np.median(mag_db[mag])
      mean_flux = np.mean(mag_db[mag])
      med_flux_db[mag] = med_flux
      num_samples = len(mag_db[mag])
      #print(mag, num_samples, mean_flux, med_flux)
      xs.append(mag)
      ys.append(mean_flux)

   plt.plot(xs,ys)
   plt.title(title)
   plt.ylabel("Flux")
   plt.xlabel("Magnitude")
   plt.savefig(photo_file)
   #plt.show()
   print("Saved", photo_file)

   # determine the avg, min, max zp_dist and zp_slope for each grid in the image!
   grid_size = 100
   grid_data = {}
   for y in range(0,1080) :
      if y == 0 or y % 100 == 0:
         for x in range(0,1920):
            if x == 0 or x % 100 == 0:
               x1 = x
               y1 = y
               x2 = x + grid_size
               y2 = y + grid_size


               sql = """
                  SELECT cal_fn, zp_res_px, zp_slope 
                    FROM calfile_paired_stars 
                   WHERE img_x > ? and img_x < ? 
                     AND img_y > ? and img_y < ?
                     AND zp_res_px is NOT NULL
                     AND cal_fn like ?
               """
               uvals = [x1,x2,y1,y2, "%" + cam_id + "%" ]
               cur.execute(sql, uvals)
               rows = cur.fetchall()
               dist_vals = []
               slope_vals = []
               for row in rows:
                  cal_fn = row[0] 
                  if cal_fn not in best_dict:
                     continue

                  dist_val = row[1] 
                  slope_val = row[2] 
                  dist_vals.append(dist_val)
                  slope_vals.append(slope_val)

               if len(dist_vals) > 2:
                  med_d_val = np.median(dist_vals)
                  mean_d_val = np.mean(dist_vals)
               else:
                  med_d_val = None
                  mean_d_val = None
               if len(slope_vals) > 2:
                  med_s_val = np.median(slope_vals)
                  mean_s_val = np.mean(slope_vals)
               else:
                  med_s_val = None
                  mean_s_val = None

               med_dist = med_d_val
               if mean_s_val is None:
                  cv2.rectangle(grid_img, (int(x1), int(y1)), (int(x2) , int(y2) ), (255, 255, 255), 1)
               elif mean_s_val < 0: 
                  cv2.rectangle(grid_img, (int(x1), int(y1)), (int(x2) , int(y2) ), (0, 255, 0), 1)
               else:
                  cv2.rectangle(grid_img, (int(x1), int(y1)), (int(x2) , int(y2) ), (0, 0, 255), 1)

               if med_dist is not None:
                  desc = str(int(med_dist)) + " " + str(med_s_val)[0:4]
               else:
                  desc = str(len(rows))
               cv2.putText(grid_img, desc,  (x1+15,y1+15), cv2.FONT_HERSHEY_SIMPLEX, .4, (255,255,255), 1)
               #cv2.imshow("pepper", grid_img)
               #cv2.waitKey(30)

               grid_key = str(x1) + "_" + str(y1) + "_" + str(x2) + "_" + str(y2)
               grid_data[grid_key] = [x1,y1,x2,y2,med_d_val, med_s_val]
               #print(x1,y1,x2,y2,med_d_val, med_s_val)


   sql = """
      SELECT cal_fn, name, mag, ra, dec, star_flux, img_x, img_y, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, zp_res_px, zp_slope
        FROM calfile_paired_stars
       WHERE star_flux is not NULL
         AND new_cat_x is not NULL
         AND star_yn >= 99
         AND cal_fn like ?
   """

   cur.execute(sql, ["%" + cam_id + "%"])
   rows = cur.fetchall()
   all_good_stars = []
   for row in rows:
      cal_fn, name, mag, ra, dec, star_flux, img_x, img_y, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, zp_res_px, zp_slope = row
      med_flux = med_flux_db[mag]
      if cal_fn not in best_dict:
         continue

      flux_diff = star_flux / med_flux

      grid_key = get_grid_key(grid_data, img_x, img_y, zp_res_px, zp_slope)
      [x1,y1,x2,y2,med_d_val, med_s_val] = grid_data[grid_key] 
      if med_d_val is None or zp_res_px is None:
         continue
      dist_diff = zp_res_px /  med_d_val
      scope_diff = zp_slope /  med_s_val
      dist = str(dist_diff)[0:4] + " " + str(scope_diff)[0:4]
      cv2.putText(grid_img, desc,  (x1+15,y1+25), cv2.FONT_HERSHEY_SIMPLEX, .4, (255,255,255), 1)

      cval = 128
      if .75 <= dist_diff <= 1.75:
         cval = cval + (cval/2)
      else:
         cval = cval - (cval /2)
      if .75 <= scope_diff <= 1.75:
         cval = cval + (cval/2)
      else:
         cval = cval - (cval /2)
      if .75 <= flux_diff <= 1.75:
         cval = cval + (cval/2)
      else:
         cval = cval - (cval /2)
      if cval > 245:
         cval = 250
         all_good_stars.append((cal_fn, name, mag, ra, dec, star_flux, img_x, img_y, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, zp_res_px, zp_slope)) 

      if cval < 0:
         cval = 64 

      if cval > 128:
         color = [0,cval, 0]
      else:
         color = [cval,cval, cval]


      cv2.line(grid_img, (int(zp_cat_x),int(zp_cat_y)), (int(img_x),int(img_y)), color, 2)

      #cv2.imshow("pepper", grid_img)
      #cv2.waitKey(30)
      sql = """UPDATE calfile_paired_stars set star_found = 1 where cal_fn = ? and img_x = ? and img_y = ?"""
      uvals = [cal_fn, img_x, img_y]
      cur.execute(sql, uvals )
      
   if SHOW == 1:
      cv2.imshow("pepper", grid_img)
      cv2.waitKey(90)
   cv2.imwrite("/mnt/ams2/cal/plots/" + station_id + "_" + cam_id + "_ALL_GOOD_STARS.jpg", grid_img)
   print("saved all stars image /mnt/ams2/cal/plots/" + station_id + "_" + cam_id + "_ALL_GOOD_STARS.jpg")
   save_json_file("/mnt/ams2/cal/" + station_id + "_" + cam_id + "_ALL_GOOD_STARS.json", all_good_stars)
   print("saved", "/mnt/ams2/cal/" + station_id + "_" + cam_id + "_ALL_GOOD_STARS.json")
   con.commit()
   # plot all stars?

   #(cal_file , center_az, center_el, ra_center, dec_center, position_angle, pixscale, dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int) = star

   calfiles_data  = load_cal_files(cam_id, con,cur)
   merged_stars = []
   for star in all_good_stars:

      (cal_fn, name, mag, ra, dec, star_flux, img_x, img_y, new_cat_x, new_cat_y, zp_cat_x, zp_cat_y, zp_res_px, zp_slope) = star
      if cal_fn not in best_dict:
         continue

      if cal_fn in calfiles_data:
         #(cal_fn_ex, center_az,center_el, ra_center,dec_center, position_angle, pixscale) = calfiles_data[cal_fn]
         (station_id, camera_id, cal_fn, cal_ts, center_az, center_el, ra_center, dec_center, position_angle,\
            pixscale, zp_az, zp_el, zp_ra, zp_dec, zp_position_angle, zp_pixel_scale, x_poly, \
            y_poly, x_poly_fwd, y_poly_fwd, res_px, res_deg, ai_weather, ai_weather_conf, cal_version, last_update) = calfiles_data[cal_fn] 


      #match_dist = zp_res_px

      match_dist = 9999
      merged_stars.append((cal_file , center_az, center_el, ra_center, dec_center, position_angle, pixscale, name,mag,ra,dec,ra,dec,match_dist,new_cat_x,new_cat_y,center_az,center_el,new_cat_x,new_cat_y,img_x,img_y,zp_res_px,star_flux)) 
   save_json_file("/mnt/ams2/cal/" + station_id + "_" + cam_id + "_MERGED_STARS.json", merged_stars)

   if mcp is not None:
      make_cal_summary(cam_id, json_conf)
      make_cal_plots(cam_id, json_conf)

   if mcp is not None:
      make_lens_model(cam_id, json_conf, merged_stars)
 
def load_cal_files(cam_id, con, cur, single=False,last=None):
   sql = """
      SELECT station_id,
             camera_id,
             cal_fn,
             cal_ts,
             az,
             el,
             ra,
             dec,
             position_angle,
             pixel_scale,
             zp_az,
             zp_el,
             zp_ra,
             zp_dec,
             zp_position_angle,
             zp_pixel_scale,
             x_poly,
             y_poly,
             x_poly_fwd,
             y_poly_fwd,
             res_px,
             res_deg,
             ai_weather,
             ai_weather_conf,
             cal_version,
             last_update
        FROM calibration_files
   """
   if single is False:
      sql += """
         WHERE cal_fn like ?
      """
      uvals = ["%" + cam_id + "%"]
   else:
      sql += """
         WHERE cal_fn = ?
      """
      uvals = [ cam_id  ]

   sql += """
    ORDER BY cal_fn DESC
   """
   if last is not None:
      sql += " LIMIT " + str(last)

   print(sql)
   print(uvals)
   cur.execute(sql, uvals )

   rows = cur.fetchall()
   calfiles_data = {}
   #print(rows)
   #print("NO CAL FILES DATA FOUND!?")

   for row in rows:
      failed = False
      (station_id, camera_id, cal_fn, cal_ts, az, el, ra, dec, position_angle,\
         pixel_scale, zp_az, zp_el, zp_ra, zp_dec, zp_position_angle, zp_pixel_scale, x_poly, \
         y_poly, x_poly_fwd, y_poly_fwd, res_px, res_deg, ai_weather, ai_weather_conf, cal_version, last_update) = row

      cal_dir = cal_dir_from_file(cal_fn)
      if cal_dir is False:
         print("FAILED load_cal_files ", cal_dir , cal_fn)
         failed = True 
      elif os.path.exists(cal_dir + cal_fn) is False: 
         print("FAILED load_cal_files", cal_dir + cal_fn)
         failed = True 

      if failed is True:
         print("DELETE", cal_fn)
         delete_cal_file(cal_fn, con, cur, json_conf)
         continue

      calfiles_data[cal_fn] = (station_id, camera_id, cal_fn, cal_ts, az, el, ra, dec, position_angle,\
         pixel_scale, zp_az, zp_el, zp_ra, zp_dec, zp_position_angle, zp_pixel_scale, x_poly, \
         y_poly, x_poly_fwd, y_poly_fwd, res_px, res_deg, ai_weather, ai_weather_conf, cal_version, last_update) 
     # row

   #worst_sort = sorted(calfiles_data, key=lambda x: x[-6], reverse=True)

   return(calfiles_data)       
   #return(calfiles_data)       
   



def get_grid_key(grid_data, img_x, img_y, zp_res_px, zp_slope):
   for gkey in grid_data:
      [x1,y1,x2,y2,med_d_val, med_s_val] = grid_data[gkey] 
      if x1 <= img_x <= x2 and y1 <= img_y <= y2:
         return(gkey)
      
def batch_calib(cam_id, con, cur, json_conf):
   free_cal_dir = "/mnt/ams2/cal/freecal/"
   cal_dirs = glob.glob(free_cal_dir + "*" + cam_id + "*")
   for ccd in sorted(cal_dirs, reverse=True):
      cal_fn = ccd.split("/")[-1]
      cal_img_file = ccd + "/" + cal_fn + "-stacked.png"
      cal_json_file = cal_img_file.replace(".png", "-calparams.json")
      cal_json_fn = cal_json_file.split("/")[-1]
      if os.path.exists(cal_img_file):
         print("JSON:", cal_json_fn)
         loaded = check_calibration_file(cal_json_fn, con, cur)
         if loaded is False:
            get_image_stars(cal_img_file, con, cur, json_conf)
         else:
            print("Already loaded")


def best_stars(merged_stars, mcp, factor = 2, gsize=50):
   #best = []

   rez = [row[-2] for row in merged_stars]
   med_rez = np.median([row[-2] for row in merged_stars])


   if True:
      grid = make_grid_stars(merged_stars, mpc = None, factor = 2, gsize=50, limit=10)
      best_stars = []
      for grid_key in grid:
         just_data = sorted(grid[grid_key], key=lambda x: x[-2], reverse=False)
         rc = 0
         if len(just_data) > 0:
            for row in just_data:
               if rc < 3:
                  best_stars.append(row)
               else:
                  break 
               rc += 1

   best = []

   med_rez = np.median([row[-2] for row in best_stars])

   res_limit = med_rez ** 2
   if res_limit < 3:
      res_limit = 3

   print("MED RES:", med_rez)
   print("RES LIMIT:", res_limit)

   for star in best_stars:
      (cal_file , center_az, center_el, ra_center, dec_center, position_angle, pixscale, name,mag,ra,dec,ra,dec,match_dist,new_cat_x,new_cat_y,center_az,center_el,new_cat_x,new_cat_y,img_x,img_y,res_px,star_flux) = star

      if res_px >  res_limit:
         print("SKIP:", res_px, res_limit)
         foo = 1
      else:
         best.append(star)


   return(best)

def lens_model(cam_id, con, cur, json_conf):
   station_id = json_conf['site']['ams_id']

   mask_file = "/mnt/ams2/meteor_archive/{}/CAL/MASKS/{}_mask.png".format(station_id, cam_id)
   print("MASK:", mask_file)
   if os.path.exists(mask_file) is True:
      mask = cv2.imread(mask_file)
      mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
      mask = cv2.resize(mask, (1920,1080))
   else:
      mask = np.zeros((1080,1920),dtype=np.uint8)

   autocal_dir = "/mnt/ams2/cal/"
   station_id = json_conf['site']['ams_id']
   print("LENS MODEL")

   mcp_file = autocal_dir + "multi_poly-" + station_id + "-" + cam_id + ".info"

   if os.path.exists(mcp_file) == 1:
      mcp = load_json_file(mcp_file)
      if "cal_version" not in mcp:
         mcp['cal_version'] = 0
      mcp['cal_version'] += 1
   else:
      mcp = None

   #if "cal_version" not in cal_params:
   #   cal_params['cal_version'] = mcp['cal_version'] 


   merged_stars = load_json_file("/mnt/ams2/cal/" + station_id + "_" + cam_id + "_MERGED_STARS.json")
   # 
   #if len(merged_stars) > 500:
   rez = [row[-2] for row in merged_stars]
   print("BEFORE BEST STARS RES:", len(merged_stars), np.median(rez))
   if len(merged_stars) > 1200:
      merged_stars = best_stars(merged_stars, mcp, factor = 2, gsize=50)
   print("AFTER BEST STARS RES:", len(merged_stars), np.median(rez))
   if len(merged_stars) > 1200:
      merged_stars = best_stars(merged_stars, mcp, factor = 2, gsize=50)
   print("AFTER BEST STARS RES:", len(merged_stars), np.median(rez))
   if len(merged_stars) > 1200:
      merged_stars = best_stars(merged_stars, mcp, factor = 2, gsize=50)
   print("AFTER BEST STARS RES:", len(merged_stars), np.median(rez))
   merged_stars = best_stars(merged_stars, mcp, factor = 2, gsize=50)
   print("AFTER BEST STARS RES:", len(merged_stars), np.median(rez))
   rez = [row[-2] for row in merged_stars]
   print("AFTER BEST STARS RES:", len(merged_stars), np.median(rez))



   status, cal_params,merged_stars = minimize_poly_multi_star(merged_stars, json_conf,0,0,cam_id,None,mcp,SHOW)

   if cal_params == 0:
      print("LENS MODEL MAKE FAILED")
      return() 

   if "cal_version" not in cal_params and mcp is None:
      cal_params['cal_version'] = 1 
   else:
      cal_params['cal_version'] =  mcp['cal_version']

   save_json_file(mcp_file, cal_params)
   print("SAVED:", mcp_file)

   # save the new merged stars!
   new_merged_stars = []

   rez = [row[-2] for row in merged_stars] 
   if len(merged_stars) > 1000:
      med_rez = np.median(rez) 
   else:
      med_rez = np.median(rez) * 2
   if med_rez < 2:
      med_rez = 2 


   for star in merged_stars:
      (cal_file , center_az, center_el, ra_center, dec_center, position_angle, pixscale, name,mag,ra,dec,ra,dec,match_dist,new_cat_x,new_cat_y,center_az,center_el,new_cat_x,new_cat_y,img_x,img_y,res_px,star_flux) = star
      cal_params['center_az'] = center_az
      cal_params['center_el'] = center_el
      cal_params['ra_center'] = ra_center
      cal_params['dec_center'] = dec_center
      cal_params['position_angle'] = position_angle 
      cal_params['pixscale'] = pixscale 
      #nc = update_center_radec(cal_fn,cal_params,json_conf)
      new_cat_x,new_cat_y = get_xy_for_ra_dec(cal_params, ra, dec)
      res_px = calc_dist((img_x,img_y),(new_cat_x,new_cat_y))
      if res_px <= med_rez:
         print("KEEP", res_px, med_rez)
         new_merged_stars.append((cal_file , center_az, center_el, ra_center, dec_center, position_angle, pixscale, name,mag,ra,dec,ra,dec,match_dist,new_cat_x,new_cat_y,center_az,center_el,new_cat_x,new_cat_y,img_x,img_y,res_px,star_flux))
      else:
         print("SKIP", res_px, med_rez)
  
   if len(new_merged_stars) > 500:
      save_json_file("/mnt/ams2/cal/" + station_id + "_" + cam_id + "_MERGED_STARS.json", new_merged_stars)

   rez = [row[-2] for row in new_merged_stars] 
   mean_rez = np.median(rez) 
   print("NEW STARS:", len(new_merged_stars))
   print("NEW REZ:", mean_rez)


def wizard(station_id, cam_id, con, cur, json_conf, limit=100):

   
   # review / apply the current lens model 
   # and calibration on the best 10 files

   cal_fns = batch_review(station_id, cam_id, con, cur, json_conf, limit)

   # characterize the current lens model 
   # and define best merge star values

   characterize_best(cam_id, con, cur, json_conf, limit, cal_fns)

   # run lens model with current stars
   lens_model(cam_id, con, cur, json_conf)

   # run lens model a second time
   lens_model(cam_id, con, cur, json_conf)

   # now remove the previous model
   autocal_dir = "/mnt/ams2/cal/"
   mcp_file = autocal_dir + "multi_poly-" + station_id + "-" + cam_id + ".info"
   print("rm " + mcp_file)
   os.system("rm " + mcp_file)

   # now remake it with the stars left over from the last run
   lens_model(cam_id, con, cur, json_conf)

   # run lens model a second time
   lens_model(cam_id, con, cur, json_conf)

   # now the lens model should be made within around to less than 1PX res. 
   # if it is less than 2px that is fine as each indiviual capture will
   # be specifically fined tuned. Remember the goal here is to make a generic model
   # that can be applied to any file at any time. Not to neccessarily get the minimize possible res

   # lens_model_final_report()
   lens_model_report(cam_id, con, cur, json_conf)
   merged_star_file = "/mnt/ams2/cal/" + station_id + "_" + cam_id + "_MERGED_STARS.json"
   merged_stars = load_json_file(merged_star_file)
   #make_lens_model(cam_id, json_conf, merged_stars)

   characterize_fov(cam_id, con, cur, json_conf)

def lens_model_report(cam_id, con, cur, json_conf):
   import matplotlib.pyplot as plt
   make_cal_summary(cam_id, json_conf)
   make_cal_plots(cam_id, json_conf)
   print("ENDED AFTER SUM")
   exit()
   grid_bg = np.zeros((1080,1920,3),dtype=np.uint8)
   autocal_dir = "/mnt/ams2/cal/"
   station_id = json_conf['site']['ams_id']
   mcp_file = autocal_dir + "multi_poly-" + station_id + "-" + cam_id + ".info"
   merged_star_file = "/mnt/ams2/cal/" + station_id + "_" + cam_id + "_MERGED_STARS.json"

   mstars = load_json_file(merged_star_file)
   mcp = load_json_file(mcp_file)
   print(mcp.keys())



   print("LENS MODEL REPORT FOR ", cam_id)
   print("--------------------- ")

   print("Stars used in final lens model:", len(mstars))
   print("Final Multi-Poly Res X (px):", mcp['x_fun'])
   print("Final Multi-Poly Res Y (px):", mcp['y_fun'])
   print("Final Multi-Poly Fwd Res X (deg):", mcp['x_fun_fwd'])
   print("Final Multi-Poly Fwd Res Y (deg):", mcp['y_fun_fwd'])
   print("Images")
   print("------")
   print("All Stars / Distortion Image")
   print("Final Multi-Image ")
   print("Final Multi-Image FWD")
   print("Grid Image")
   print("Graphs")
   print("Photometry")

   # Photometry report
   mags = []
   fluxs = []
   xs = []
   ys = []
   med_flux_db = {}
   mag_db = {}
   for star in mstars:
      (cal_file , center_az, center_el, ra_center, dec_center, position_angle, pixscale, dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,flx) = star
      mags.append(mag)
      fluxs.append(flx)
      if mag is None:
         continue
      if mag not in mag_db:
         mag_db[mag] = []
      mag_db[mag].append(flx)
   
   for mag in sorted(mag_db):
      med_flux = np.median(mag_db[mag])
      mean_flux = np.mean(mag_db[mag])
      med_flux_db[mag] = med_flux
      num_samples = len(mag_db[mag])
      #print(mag, num_samples, mean_flux, med_flux)
      xs.append(mag)
      ys.append(mean_flux)

   mj = {}
   mj['cp'] = mcp 
   mj['sd_trim'] = cal_file 


   plt.scatter(mags,fluxs)
   #plt.show()
   plt.plot(xs,ys)
   #plt.show()



def fix_cal(cal_fn, con, cur,json_conf):

   if "json" in cal_fn:
      cal_dir = "/mnt/ams2/cal/freecal/" + cal_fn.replace("-stacked-calparams.json", "/")
   cal_params = load_json_file(cal_dir + cal_fn)
   cal_img = cv2.imread(cal_dir + cal_fn.replace("-calparams.json", ".png"))
   range_data = get_cal_range(cal_fn, cal_img, con, cur, json_conf)
   for row_data in range_data:
      show_img = cal_img.copy()
      cp = dict(cal_params)
      rcam_id, rend_dt, rstart_dt, elp, az, el, pos, pxs, res = row_data
      cp['center_az'] = az
      cp['center_el'] = el
      cp['position_angle'] = pos
      cp['pixscale'] = pxs

      cp = update_center_radec(cal_fn,cp,json_conf)

      cp['cat_image_stars'], cp['user_stars'] = get_image_stars_with_catalog(cal_fn, cp, show_img)

      new_cat_image_stars = []
      for star in cp['cat_image_stars']:
         (dcname,mag,ra,dec,img_ra,img_dec,match_dist,up_cat_x,up_cat_y,img_az,img_el,up_cat_x,up_cat_y,six,siy,res_px,bp) = star
         new_cat_x, new_cat_y = get_xy_for_ra_dec(cp, ra, dec)
         res_px = calc_dist((six,siy),(new_cat_x,new_cat_y))
         new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(six,siy,cal_fn,cp,json_conf)
         match_dist = angularSeparation(ra,dec,img_ra,img_dec)
         real_res_px = res_px
         new_cat_image_stars.append((dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,real_res_px,bp))
      cp['cat_image_stars'] = new_cat_image_stars

      rez = [row[-2] for row in cp['cat_image_stars'] ]
      med_rez = np.median(rez) ** 2
      extra_text = str(med_rez) + " pixel median residual distance"
      print("MED REZ FOR THIS ROW IS:", med_rez)


      star_img = draw_star_image(show_img, cp['cat_image_stars'],cp, json_conf, extra_text) 
      if SHOW == 1:
         cv2.imshow('pepe', star_img)
         cv2.waitKey(30)

   


def find_best_calibration(cal_fn, orig_cal, list_of_cals, json_conf):
   # Not used...
   # input = cal filename and data, and list of cal_params to try
   for row in list_of_cals:
      [az,el,pos,pxs] = row
      cp = dict(orig_cal)
      cp['center_az'] = az
      cp['center_el'] = el
      cp['center_pos'] = pos
      cp['center_pxs'] = pxs
      cp = update_center_radec(cal_fn,cp,json_conf)
      new_cat_image_stars = []
      for star in cp['cat_image_stars']:
         (dcname,mag,ra,dec,img_ra,img_dec,match_dist,up_cat_x,up_cat_y,img_az,img_el,up_cat_x,up_cat_y,six,siy,res_px,bp) = star
         new_cat_x, new_cat_y = get_xy_for_ra_dec(mj['cp'], ra, dec)
         res_px = calc_dist((six,siy),(new_cat_x,new_cat_y))
         new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(six,siy,meteor_file,mj['cp'],json_conf)
         match_dist = angularSeparation(ra,dec,img_ra,img_dec)
         real_res_px = res_px
         new_cat_image_stars.append((dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,real_res_px,bp))
      mj['cp']['cat_image_stars'] = new_cat_image_stars

      rez = [row[-2] for row in mj['cp']['cat_image_stars'] ]
      med_rez = np.median(rez) ** 2
      print("MED REZ FOR THIS ROW IS:", med_rez)
       

def prune(cam_id, con, cur, json_conf):
   #print("Prune calfiles for cam_id")
   freecal_dir = "/mnt/ams2/cal/freecal/"
   extracal_dir = "/mnt/ams2/cal/extracal/"
   if os.path.exists(extracal_dir) is False:
      os.path.exists(extracal_dir)
   temp = os.listdir(freecal_dir)
   cal_files = []
   for xx in temp:
      if cam_id in xx:
         cal_files.append(xx)

   freecal_index = load_json_file("/mnt/ams2/cal/freecal_index.json") 
   month_dict = {}
   pruned = 0
   for cal_file in freecal_index:
      if cam_id not in cal_file:
         continue
      cal_fn = cal_file.split("/")[-1]
      day = cal_fn[0:10]
      month = cal_fn[0:7]
      if month not in month_dict:
         month_dict[month] = {}
         month_dict[month]['files'] = []
      data = freecal_index[cal_file]
      month_dict[month]['files'].append([cal_file, data])

   mc = 0
   for month in sorted(month_dict, reverse=True):
      if mc < 3:
         print("Skip most recent months!")
         mc += 1
         continue
      over_files = len(month_dict[month]['files']) - 15
      print(month, len(month_dict[month]['files']), "over", over_files )
      just_data = []
      for cal_file, data in month_dict[month]['files'] :
         just_data.append(data)
      if over_files <= 1:
         print("THIS MONTH IS GOOD", month)
         continue
      just_data = sorted(just_data, key=lambda x: x['total_stars'] / x['total_res_px'], reverse=True)

      for data in just_data[0:over_files]:
         if os.path.isdir(data['base_dir']) is True:
            cmd = "mv " + data['base_dir'] + " " + extracal_dir
            print(cmd)
            os.system(cmd)
            print(data['base_dir'], data['total_stars'], data['total_res_px'])
            pruned += 1
         else:
            print("DONE ALREADY!", data['base_dir'], data['total_stars'], data['total_res_px'])

      mc += 1
      
   print("Before prune total files:", len(cal_files))
   print("Suggest pruning:", pruned)
   print("After prune total files:", len(cal_files) - pruned)


if __name__ == "__main__":
   json_conf = load_json_file("../conf/as6.json")
   station_id = json_conf['site']['ams_id']
   db_file = station_id + "_CALIB.db" 
   #con = sqlite3.connect(":memory:")

   if os.path.exists(db_file) is False:
      cmd = "cat CALDB.sql |sqlite3 " + db_file
      print(cmd)
      os.system(cmd)
   else:
      print("CAL DB EXISTS ALREADY")

   con = sqlite3.connect(db_file)
   cur = con.cursor()

   cmd = sys.argv[1]
   cal_file = sys.argv[2]

   # batch = batch load cal files in DB / v2 structure
   # gis = process 1 file for first time
   # cal_main = main menu
   # char = recharacterize camera -- pre-req for lens_model 
   # lens_model = make multi-file lens model from best stars
   # update_calfiles = update all files with latest poly vals, re-center and re-pick/calc stars and res
   # view = view a file
   # man_tweek = tweek a file

   # cron process/es shoudl be: {
   #   batch
   #   char
   #   lens_model
   #   update
   # }
   # do this 3-5x and it should be good?!
   # 


   if cmd == "best" :
      cam_id = sys.argv[2]
      characterize_best(cam_id, con, cur, json_conf)

   if cmd == "batch" :
      # IMPORT FOR THE FIRST TIME
      # WORKS BUT OLD AND SLOW
      # USE status to get started and wiz to perfect!

      cam_id = sys.argv[2]
      batch_calib(cam_id, con, cur, json_conf)
   if cmd == "get_image_stars" or cmd == "gis":
      get_image_stars(cal_file, con, cur, json_conf)
   if cmd == "cal_main" :
      cal_main(cal_file)
   if cmd == "char" :
      cam_id = sys.argv[2]
      characterize_fov(cam_id, con, cur, json_conf)
   if cmd == "lens_model" :

      cam_id = sys.argv[2]
      if cam_id == "all":
         for cam_num in json_conf['cameras']:
            cam_id = json_conf['cameras'][cam_num]['cams_id']
            lens_model(cam_id, con, cur, json_conf)
      else:
         lens_model(cam_id, con, cur, json_conf)



   if cmd == "update" :
      cam_id = sys.argv[2]
      update_calfiles(cam_id, con, cur, json_conf)
   if cmd == "view" :
      view_calfile(cal_file, con, cur, json_conf)
   if cmd == "man_tweek" :
      manual_tweek_calib(cal_file, con, cur, json_conf)

   if cmd == "apply_calib" :
      cf = sys.argv[2]
      (f_datetime, cam_id, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(cf)
      autocal_dir = "/mnt/ams2/cal/"
      mcp_file = autocal_dir + "multi_poly-" + station_id + "-" + cam_id + ".info"
      print(mcp_file)
      if os.path.exists(mcp_file) == 1:
         mcp = load_json_file(mcp_file)

      calfiles_data = load_cal_files(cam_id, con, cur)
      last_cal_params = apply_calib (cf, calfiles_data, json_conf, mcp, None, "")

   if cmd == "batch_apply" :
      cam_id = sys.argv[2]
      if len(sys.argv) > 3:
         # do bad
         batch_apply(cam_id, con, cur, json_conf, None, True)
      else:
         batch_apply(cam_id, con, cur, json_conf)
   if cmd == "cat_view" :
      cal_fn = sys.argv[2]
      cat_view(cal_fn, con, cur, json_conf)
   if cmd == "find_stars_cat" :
      cal_fn = sys.argv[2]
      find_stars_with_catalog(cal_fn, con, cur, json_conf)
   if cmd == "cat_image" :
      cal_fn = sys.argv[2]
      catalog_image(cal_fn, con, cur, json_conf)

   if cmd == "batch_review" :
      cam_id = sys.argv[2]
      batch_review(station_id, cam_id, con, cur, json_conf)
   if cmd == "wiz" :
      cam_id = sys.argv[2]
      if len(sys.argv) > 3:
         limit = sys.argv[3]
      else:
         limit = 25

      if cam_id == "all":
         for cam_num in json_conf['cameras']:
            cam_id = json_conf['cameras'][cam_num]['cams_id']
            cmd = "python3 recal.py wiz {} {}".format(cam_id, limit)
            os.system(cmd)
            #wizard(cam_id, con, cur, json_conf, limit)
      else:
         wizard(station_id, cam_id, con, cur, json_conf, limit)

   if cmd == "status" :
      cam_id = sys.argv[2]
      print("CAM:", cam_id)
      if cam_id == "all":
         for cam_num in json_conf['cameras']:
            cam_id = json_conf['cameras'][cam_num]['cams_id']
            cal_status_report(cam_id, con, cur, json_conf)
      else:
         print("CAM:", cam_id)
         cal_status_report(cam_id, con, cur, json_conf)



   if cmd == "prune" :
      cam_id = sys.argv[2]
      prune(cam_id, con, cur, json_conf)
   if cmd == "lens_model_report" :
      cam_id = sys.argv[2]
      lens_model_report(cam_id, con, cur, json_conf)
   if cmd == "make_plate":
      cal_fn = sys.argv[2]
      make_plate(cal_fn, json_conf, con, cur)
   if cmd == "star_points":
      cam_id = sys.argv[2]
      if cam_id == "all":
         for cam_num in json_conf['cameras']:
            cam_id = json_conf['cameras'][cam_num]['cams_id']
            star_points_all(cam_id, json_conf, con, cur)
      else:
         star_points_all(cam_id, json_conf, con, cur)
   if cmd == "star_points_report":
      cam_id = sys.argv[2]
      if cam_id == "all":
         for cam_num in json_conf['cameras']:
            cam_id = json_conf['cameras'][cam_num]['cams_id']
            star_points_report(cam_id, json_conf, con, cur)
      else:
         star_points_report(cam_id, json_conf, con, cur)


   if cmd == "star_track" :
      cam_id = sys.argv[2]
      star_track(cam_id, con, cur, json_conf)
  

   if cmd == "fix_cal" :
      cal_file = sys.argv[2]
      fix_cal(cal_file, con, cur, json_conf)


   if cmd == "refit_meteor" :
      meteor_file = sys.argv[2]
      refit_meteor(meteor_file, con, cur, json_conf)

   if cmd == "refit_meteor_year":
      year = sys.argv[2]
      files = os.listdir("/mnt/ams2/meteors/")
      for ff in sorted(files, reverse=True):
         if year not in ff:
            continue
         if os.path.isdir("/mnt/ams2/meteors/" + ff + "/") is True :
            print(ff)
            print("/mnt/ams2/meteors/" + ff + "/refit_summary.log") 
            if os.path.exists("/mnt/ams2/meteors/" + ff + "/refit_summary.log") is False:
               cmd = "./recal.py refit_meteor_day " + ff
               print(cmd)
               os.system(cmd)
            else:
               print("Did already.")
            #exit() 
   if cmd == "refit_summary" :
      date = sys.argv[2]
      mdir = "/mnt/ams2/meteors/" + date + "/"
      refit_log_file = mdir + "refit.log"
      refit_sum_file = mdir + "refit_summary.log"
      if os.path.exists(refit_log_file) is True:
         refit_log = load_json_file(refit_log_file)
         report = refit_summary(refit_log)
         save_json_file(refit_sum_file, report)


   if cmd == "refit_meteor_day" :
      date = sys.argv[2]
      mdir = "/mnt/ams2/meteors/" + date + "/"
      files = os.listdir("/mnt/ams2/meteors/" + date + "/")
      refit_log_file = mdir + "refit.log"
      if os.path.exists(refit_log_file) is True:
         refit_log = load_json_file(refit_log_file)
         refit_summary(refit_log)
      else:
         refit_log = []
      last_best = {}

      print(refit_log_file)
      #exit()

      by_cam = {}
      for ff in files:
         (f_datetime, cam_id, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(ff)
         if "json" not in ff:
            continue
         if "reduced" in ff:
            continue

         if cam_id not in by_cam:
            by_cam[cam_id] = {}
         by_cam[cam_id][ff] = {}

      all_files = []
      for cam in by_cam:
         for ff in by_cam[cam]:
            all_files.append(ff) 

      last_cp = {}
      last_best = {}
      for ff in all_files:
         (f_datetime, cam_id, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(ff)
         last_cp = refit_meteor(ff, con, cur, json_conf, None, last_best)
         if last_cp is None:
            continue
         print("REFITTED") 
         last_cp = refit_meteor(ff, con, cur, json_conf, None, last_best)
         print("2x REFITTED") 

         if cam_id not in last_best:
            last_best[cam_id] = last_cp
         print("LAST CP", last_cp)
         if "center_az" in last_cp:
            refit_log.append([cam_id, ff, last_cp['center_az'], last_cp['center_el'], last_cp['ra_center'], last_cp['dec_center'], last_cp['position_angle'], last_cp['pixscale'], len(last_cp['cat_image_stars']), last_cp['total_res_px']])
         else:
            print("Refit failed", ff)
            continue

         if last_best[cam_id]['total_res_px'] > last_cp['total_res_px'] : 
            print("LAST/BEST:", last_cp['total_res_px'], last_best[cam_id]['total_res_px'] )
            last_best[cam_id] = last_cp
            print(" *(**** BETTER RES found!")
         print("LAST BEST:", last_best.keys())
      save_json_file(refit_log_file, refit_log)
      print(refit_log_file)
      os.system("./recal.py refit_summary " + date )
