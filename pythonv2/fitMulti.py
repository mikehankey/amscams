#!/usr/bin/python3

import glob
import os
import math
import cv2
import math
import numpy as np
import scipy.optimize
import matplotlib.pyplot as plt
import sys
#from caliblib import distort_xy,
from lib.CalibLib import distort_xy_new, find_image_stars, distort_xy_new, XYtoRADec, AzEltoRADec, HMS2deg

from lib.UtilLib import angularSeparation, better_parse_file_date

from lib.FileIO import load_json_file, save_json_file, cfe
from lib.UtilLib import calc_dist,find_angle
import lib.brightstardata as bsd
from lib.DetectLib import eval_cnt
tries = 0

def reduce_fit(this_poly,field, merged_stars, cal_params, cal_params_file, fit_img, json_conf, show=0):
   this_fit_img = fit_img.copy()
   global tries
   pos_poly = cal_params['pos_poly']
   fov_poly = cal_params['fov_poly']

   if field == 'x_poly':
      x_poly_fwd = cal_params['x_poly_fwd']
      y_poly_fwd = cal_params['y_poly_fwd']
      x_poly = this_poly
      cal_params['x_poly'] = x_poly
      y_poly = cal_params['y_poly']

   if field == 'y_poly':
      x_poly_fwd = cal_params['x_poly_fwd']
      y_poly_fwd = cal_params['y_poly_fwd']
      y_poly = this_poly
      cal_params['y_poly'] = y_poly
      x_poly = cal_params['x_poly']

   if field == 'x_poly_fwd':
      x_poly = cal_params['x_poly']
      y_poly = cal_params['y_poly']
      x_poly_fwd = this_poly
      cal_params['x_poly_fwd'] = x_poly_fwd
      y_poly_fwd = cal_params['y_poly_fwd']

   if field == 'y_poly_fwd':
      x_poly = cal_params['x_poly']
      y_poly = cal_params['y_poly']
      y_poly_fwd = this_poly
      cal_params['y_poly_fwd'] = y_poly_fwd
      x_poly_fwd = cal_params['x_poly_fwd']

   # loop over each pair of img/cat star and re-compute distortion with passed 'this poly', calc error distance and return avg distance for all pairs set
   total_res = 0
   total_res_fwd = 0

   # OK. For multi-fit, we need to add the cal_file (includes date) to the front of this list. and then calulate the RA/DEC center on-the-fly based on the AZ/EL and date conversion. The update the calparams for this specific star before doing the distortion. 

   for star in merged_stars:
      (cal_file,ra_center,dec_center,dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy, img_res) = star
 
      if field == 'x_poly' or field == 'y_poly':
         new_cat_x, new_cat_y = distort_xy_new (0,0,ra,dec,float(ra_center), float(dec_center), x_poly, y_poly, float(cal_params['imagew']), float(cal_params['imageh']), float(cal_params['position_angle']),3600/float(cal_params['pixscale']))
         img_res = abs(calc_dist((six,siy),(new_cat_x,new_cat_y)))

      else:
         cal_params['ra_center'] = ra_center
         cal_params['dec_center'] = dec_center
         new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(six,siy,cal_file,cal_params,json_conf)
         new_x, new_y= distort_xy_new (0,0,img_ra,img_dec,float(ra_center), float(dec_center), x_poly, y_poly, float(cal_params['imagew']), float(cal_params['imageh']), float(cal_params['position_angle']),3600/float(cal_params['pixscale']))
         img_res = abs(angularSeparation(ra,dec,img_ra,img_dec))
         #img_res = abs(calc_dist((six,siy),(new_x,new_y)))

      cv2.rectangle(this_fit_img, (int(new_x)-2, int(new_y)-2), (int(new_x) + 2, int(new_y) + 2), (128, 128, 128), 1)
      cv2.rectangle(this_fit_img, (int(new_cat_x)-2, int(new_cat_y)-2), (int(new_cat_x) + 2, int(new_cat_y) + 2), (128, 128, 128), 1)
      cv2.rectangle(this_fit_img, (six-4, siy-4), (six+4, siy+4), (128, 128, 128), 1)
      cv2.line(this_fit_img, (six,siy), (int(new_cat_x),int(new_cat_y)), (255), 2) 
      total_res = total_res + img_res
      

   if tries % 10 == 0:
      if show == 1:
         show_img = cv2.resize(this_fit_img, (0,0),fx=.5, fy=.5)
         cv2.imshow('pepe', show_img) 
         cv2.waitKey(1)

   total_stars = len(cal_params['merged_stars'])
   avg_res = total_res/total_stars

   print("Total Residual Error:", total_res )
   print("Total Stars:", total_stars)
   print("Total Tries:", tries)
   print("Avg Residual Error:", avg_res )
   tries = tries + 1
   #print("Try:", tries)
 
   return(avg_res)


def minimize_poly_params_fwd(merged_stars, cal_params_file, cal_params,json_conf,orig_ra_center,orig_dec_center,show=0):
   fit_img_file = cal_params_file.replace("-calparams.json", ".png")
   fit_img = cv2.imread(fit_img_file)
   if show == 1:
      cv2.namedWindow('pepe')
   x_poly_fwd = cal_params['x_poly_fwd'] 
   y_poly_fwd = cal_params['y_poly_fwd'] 
   x_poly = cal_params['x_poly'] 
   y_poly = cal_params['y_poly'] 

   close_stars = cal_params['close_stars']
   # do x poly fwd
   if show == 1:
      cv2.namedWindow('pepe') 
   this_fit_img = fit_img.copy()
   for star in merged_stars:
      (cal_file,ra_center,dec_center,dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy, img_res) = star
      cv2.rectangle(this_fit_img, (new_cat_x-2, new_cat_y-2), (new_cat_x + 2, new_cat_y + 2), (128, 128, 128), 1)
      cv2.rectangle(this_fit_img, (six-4, siy-4), (six+4, siy+4), (128, 128, 128), 1)
      cv2.line(this_fit_img, (six,siy), (new_cat_x,new_cat_y), (255), 2) 
   cv2.imwrite("/mnt/ams2/test.png", this_fit_img)

   # do x poly 
   field = 'x_poly'
   res = scipy.optimize.minimize(reduce_fit, x_poly, args=(field,merged_stars,cal_params,cal_params_file,fit_img,json_conf), method='Nelder-Mead')
   x_poly = res['x']
   x_fun = res['fun']
   cal_params['x_poly'] = x_poly.tolist()
   cal_params['x_fun'] = x_fun

   # do y poly 
   field = 'y_poly'
   res = scipy.optimize.minimize(reduce_fit, y_poly, args=(field,merged_stars,cal_params,cal_params_file,fit_img,json_conf), method='Nelder-Mead')
   y_poly = res['x']
   y_fun = res['fun']
   cal_params['y_poly'] = y_poly.tolist()
   cal_params['y_fun'] = y_fun
   
   # do x poly fwd
   field = 'x_poly_fwd'
   res = scipy.optimize.minimize(reduce_fit, x_poly_fwd, args=(field,merged_stars,cal_params,cal_params_file,fit_img,json_conf), method='Nelder-Mead')
   x_poly_fwd = res['x']
   x_fun_fwd = res['fun']
   cal_params['x_poly_fwd'] = x_poly_fwd.tolist()
   cal_params['x_fun_fwd'] = x_fun_fwd

   # do y poly fwd
   field = 'y_poly_fwd'
   res = scipy.optimize.minimize(reduce_fit, y_poly_fwd, args=(field,merged_stars,cal_params,cal_params_file,fit_img,json_conf), method='Nelder-Mead')
   y_poly_fwd = res['x']
   y_fun_fwd = res['fun']
   cal_params['y_poly_fwd'] = y_poly_fwd.tolist()
   cal_params['y_fun_fwd'] = y_fun_fwd




   print("POLY PARAMS")
   print("X_POLY", x_poly)
   print("Y_POLY", y_poly)
   print("X_POLY_FWD", x_poly_fwd)
   print("Y_POLY_FWD", y_poly_fwd)
   print("X_POLY FUN", x_fun)
   print("Y_POLY FUN", y_fun)
   print("X_POLY FWD FUN", x_fun_fwd)
   print("Y_POLY FWD FUN", y_fun_fwd)


   img_x = 960
   img_y = 540
   new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(img_x,img_y,cal_params_file,cal_params,json_conf)
   cal_params['center_az'] = img_az
   cal_params['center_el'] = img_el
   cal_params['ra_center'] = orig_ra_center
   cal_params['dec_center'] = orig_dec_center
   cal_params_file = cal_params_file.replace("-calparams.json", "-calparams-master.json")
   save_json_file(cal_params_file, cal_params)

def build_multi_cal(cal_params_file, json_conf):
   (f_datetime, cam_id, f_date_str,Y,M,D, H, MM, S) = better_parse_file_date(cal_params_file)
   cal_params = load_json_file(cal_params_file)

   orig_ra_center = cal_params['ra_center']
   orig_dec_center = cal_params['dec_center']

   print(f_date_str)
   merged_stars = []

   # find all cal files from his cam for the same night
   date_str = str(Y) + "_" + str(M) + "_" + str(D)
   matches = find_matching_cal_files(date_str, cam_id)
   print(matches) 
   for match in matches:
      #el = match.split("/")
      #base_file = el[-1]
      #this_cal_params_file = match + "/" + base_file + "-stacked-calparams.json"
      this_cal_params_file = match
      print(match)
      merged_stars = load_merge_cal(this_cal_params_file, merged_stars)

   

#   for (cal_file,ra_center,dec_center, dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist) in merged_stars:
#      print(cal_file,ra_center,dec_center, dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist)
   return(merged_stars, matches, orig_ra_center, orig_dec_center)

def load_merge_cal(cal_params_file, merged_stars):
   cp = load_json_file(cal_params_file)
   cal_file = cal_params_file.replace("-calparams.json", ".png")
   tcs = cp['close_stars']
   center_az = cp['center_az']
   center_el = cp['center_el']
   rah,dech = AzEltoRADec(center_az,center_el,cal_params_file,cal_params,json_conf)
   rah = str(rah).replace(":", " ")
   dech = str(dech).replace(":", " ")
   ra_center,dec_center = HMS2deg(str(rah),str(dech))
   print("CENTER AZ/EL", center_az, center_el, ra_center, dec_center) 

   for (dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist) in tcs:
      merged_stars.append((cal_file,ra_center,dec_center, dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist))

   

   return(merged_stars)

def find_matching_cal_files(date_str, cam_id):
   match = []
   all_files = glob.glob("/mnt/ams2/cal/fit_pool/*.json")
   for file in all_files:
      if cam_id in file :
         match.append(file)
   return(match)


tries = 0
json_conf = load_json_file("../conf/as6.json")


cal_params_file = sys.argv[1]

print(cal_params_file)
cal_params = load_json_file(cal_params_file)
total_res = 0
total_res_fwd = 0

merged_stars, merged_files, orig_ra_center, orig_dec_center = build_multi_cal(cal_params_file, json_conf)
cal_params['merged_stars'] = merged_stars
cal_params['merged_files'] = merged_files
minimize_poly_params_fwd(merged_stars, cal_params_file, cal_params,json_conf,orig_ra_center,orig_dec_center)
exit()


for star in (cal_params['close_stars']):
   (dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy, img_res) = star
   img_res_fwd = abs(calc_dist((six,siy),(new_x,new_y)))
   #print(dcname, img_res,img_res,img_res_fwd)
   total_res = total_res + img_res
   total_res_fwd = total_res_fwd + img_res_fwd

total_stars = len(cal_params['close_stars'])
avg_res = total_res/total_stars
avg_res_fwd = total_res_fwd/total_stars
print("Total Residual Error:", total_res, total_res_fwd)
print("Avg Residual Error:", avg_res, avg_res_fwd)
minimize_poly_params_fwd(cal_params_file, cal_params,json_conf)

cmd = "./XYtoRAdecAzEl.py az_grid " + cal_params_file + ">/tmp/mike.txt 2>&1"
print(cmd)
os.system(cmd)

