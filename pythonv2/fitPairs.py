#!/usr/bin/python3

import os
import math
import cv2
import math
import numpy as np
import scipy.optimize
#import matplotlib.pyplot as plt
import sys
#from caliblib import distort_xy,
from lib.CalibLib import distort_xy_new, find_image_stars, distort_xy_new, XYtoRADec
from lib.UtilLib import angularSeparation
from lib.FileIO import load_json_file, save_json_file, cfe
from lib.UtilLib import calc_dist,find_angle
import lib.brightstardata as bsd
from lib.DetectLib import eval_cnt

def reduce_fit(this_poly,field, cal_params, cal_params_file, fit_img, json_conf, show=1):
   global tries
   pos_poly = 0 
   fov_poly = 0
   fit_img = np.zeros((1080,1920),dtype=np.uint8)
   fit_img = cv2.cvtColor(fit_img, cv2.COLOR_GRAY2RGB)
   this_fit_img = fit_img.copy()
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
   ra_center = float(cal_params['ra_center'])
   dec_center = float(cal_params['dec_center'])

   for star in (cal_params['cat_image_stars']):
      (dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy, img_res) = star
 
      if field == 'x_poly' or field == 'y_poly':
         new_cat_x, new_cat_y = distort_xy_new (0,0,ra,dec,float(cal_params['ra_center']), float(cal_params['dec_center']), x_poly, y_poly, float(cal_params['imagew']), float(cal_params['imageh']), float(cal_params['position_angle']),3600/float(cal_params['pixscale']))
         img_res = abs(calc_dist((six,siy),(new_cat_x,new_cat_y)))

         if img_res < 1:
            color = (255,0,0)
         elif 1 < img_res < 2:
            color = (0,255,0)
         elif 3 < img_res < 4:
            color = (255,255,0)
         elif 5 < img_res < 6:
            color = (0,165,255)
         else :
            color = (0,0,255)

         cv2.line(this_fit_img, (six,siy), (int(new_cat_x),int(new_cat_y)), color, 2)
      else:
         new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(six,siy,cal_params_file,cal_params,json_conf)
         new_cat_x, new_cat_y = distort_xy_new (0,0,img_ra,img_dec,float(cal_params['ra_center']), float(cal_params['dec_center']), x_poly, y_poly, float(cal_params['imagew']), float(cal_params['imageh']), float(cal_params['position_angle']),3600/float(cal_params['pixscale']))
         img_res = abs(angularSeparation(ra,dec,img_ra,img_dec))
         if img_res < .1:
            color = (255,0,0)
         elif .1 < img_res < .2:
            color = (0,255,0)
         elif .2 < img_res < .3:
            color = (255,255,0)
         elif .4 < img_res < .5:
            color = (0,165,255)
         else:
            color = (0,0,255)
         cv2.line(this_fit_img, (six,siy), (int(new_cat_x),int(new_cat_y)), color, 2)
         #img_res = abs(calc_dist((six,siy),(new_x,new_y)))

      #cv2.rectangle(this_fit_img, (int(new_x)-2, int(new_y)-2), (int(new_x) + 2, int(new_y) + 2), (128, 128, 128), 1)
      cv2.rectangle(this_fit_img, (int(new_cat_x)-2, int(new_cat_y)-2), (int(new_cat_x) + 2, int(new_cat_y) + 2), (128, 128, 128), 1)
      #cv2.rectangle(this_fit_img, (six-4, siy-4), (six+4, siy+4), (128, 128, 128), 1)
      cv2.circle(this_fit_img, (six,siy), 5, (128,128,128), 1)

      total_res = total_res + img_res
   tries = tries + 1

   total_stars = len(cal_params['cat_image_stars'])
   avg_res = total_res/total_stars

   movie =0
   show_img = cv2.resize(this_fit_img, (0,0),fx=.5, fy=.5)
   cn = str(tries)
   cnp = cn.zfill(10)
   desc = field + " res: " + str(img_res) 
   cv2.putText(this_fit_img, desc, (int(50), int(50)),cv2.FONT_HERSHEY_SIMPLEX, 2, (255,255,255), 1)
   if movie == 1:
      if (field == 'xpoly' or field == 'ypoly'): 
         if img_res > 5:
            if tries % 1 == 0:
               cv2.imwrite("/mnt/ams2/fitmovies/fr" + str(cnp) + ".png", this_fit_img)
         else:
            if tries % 5 == 0:
               cv2.imwrite("/mnt/ams2/fitmovies/fr" + str(cnp) + ".png", this_fit_img)
      else: 
         if img_res > .3:
            if tries % 1 == 0:
               cv2.imwrite("/mnt/ams2/fitmovies/fr" + str(cnp) + ".png", this_fit_img)
         elif .08 < img_res < .3 :
            if tries % 5 == 0:
               cv2.imwrite("/mnt/ams2/fitmovies/fr" + str(cnp) + ".png", this_fit_img)
         else: 
            if tries % 1 == 0:
               cv2.imwrite("/mnt/ams2/fitmovies/fr" + str(cnp) + ".png", this_fit_img)
   #cv2.imshow('pepe', this_fit_img)
   #cv2.waitKey(1)
   #cv2.imshow('pepe', show_img)
   #cv2.waitKey(1)


   #print("Total Residual Error:", total_res )
   print("Avg Residual Error:", field, avg_res )
 
   return(avg_res)


def minimize_poly_params_fwd(cal_params_file, cal_params,json_conf,show=1):
   global tries
   tries = 0 
   #cv2.namedWindow('pepe')
   
   fit_img_file = cal_params_file.replace("-calparams.json", ".png")
   if cfe(fit_img_file) == 1:
      fit_img = cv2.imread(fit_img_file)
   else:
      fit_img = np.zeros((1080,1920),dtype=np.uint8)

   #if show == 1:
   #   cv2.namedWindow('pepe')
   x_poly_fwd = cal_params['x_poly_fwd'] 
   y_poly_fwd = cal_params['y_poly_fwd'] 
   x_poly = cal_params['x_poly'] 
   y_poly = cal_params['y_poly'] 

   close_stars = cal_params['cat_image_stars']
   # do x poly fwd

   x_poly_fwd = np.zeros(shape=(15,),dtype=np.float64)
   y_poly_fwd = np.zeros(shape=(15,),dtype=np.float64)
   x_poly = np.zeros(shape=(15,),dtype=np.float64)
   y_poly = np.zeros(shape=(15,),dtype=np.float64)



   # do x poly 
   field = 'x_poly'
   res = scipy.optimize.minimize(reduce_fit, x_poly, args=(field,cal_params,cal_params_file,fit_img,json_conf), method='Nelder-Mead')
   x_poly = res['x']
   x_fun = res['fun']
   cal_params['x_poly'] = x_poly.tolist()
   cal_params['x_fun'] = x_fun

   # do y poly 
   field = 'y_poly'
   res = scipy.optimize.minimize(reduce_fit, y_poly, args=(field,cal_params,cal_params_file,fit_img,json_conf), method='Nelder-Mead')
   y_poly = res['x']
   y_fun = res['fun']
   cal_params['y_poly'] = y_poly.tolist()
   cal_params['y_fun'] = y_fun

   # do x poly fwd
   field = 'x_poly_fwd'
   res = scipy.optimize.minimize(reduce_fit, x_poly_fwd, args=(field,cal_params,cal_params_file,fit_img,json_conf), method='Nelder-Mead')
   x_poly_fwd = res['x']
   x_fun_fwd = res['fun']
   cal_params['x_poly_fwd'] = x_poly_fwd.tolist()
   cal_params['x_fun_fwd'] = x_fun_fwd

   # do y poly fwd
   field = 'y_poly_fwd'
   res = scipy.optimize.minimize(reduce_fit, y_poly_fwd, args=(field,cal_params,cal_params_file,fit_img,json_conf), method='Nelder-Mead')
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


   #img_x = 960
   #img_y = 540
   #new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(img_x,img_y,cal_params_file,cal_params,json_conf)
   #cal_params['center_az'] = img_az
   #cal_params['center_el'] = img_el
   save_json_file(cal_params_file, cal_params)




json_conf = load_json_file("../conf/as6.json")


cal_params_file = sys.argv[1]
os.system("./autoCal.py cfit_hdcal " + cal_params_file)
print(cal_params_file)
cal_params = load_json_file(cal_params_file)
total_res = 0
total_res_fwd = 0
for star in (cal_params['cat_image_stars']):
   (dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy, img_res) = star
   img_res_fwd = abs(calc_dist((six,siy),(new_x,new_y)))
   #print(dcname, img_res,img_res,img_res_fwd)
   total_res = total_res + img_res
   total_res_fwd = total_res_fwd + img_res_fwd

total_stars = len(cal_params['cat_image_stars'])
avg_res = total_res/total_stars
avg_res_fwd = total_res_fwd/total_stars
print("Total Residual Error:", total_res, total_res_fwd)
print("Avg Residual Error:", avg_res, avg_res_fwd)
minimize_poly_params_fwd(cal_params_file, cal_params,json_conf)

cmd = "./XYtoRAdecAzEl.py az_grid " + cal_params_file + ">/tmp/mike.txt 2>&1"
print(cmd)
os.system(cmd)
cmd = "./autoCal.py cal_index"
os.system(cmd)

