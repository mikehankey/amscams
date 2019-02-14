#!/usr/bin/python3

import os
import math
import cv2
import math
import numpy as np
import scipy.optimize
import matplotlib.pyplot as plt
import sys
#from caliblib import distort_xy,
from lib.CalibLib import distort_xy_new, find_image_stars, distort_xy_new, XYtoRADec
from lib.UtilLib import angularSeparation
from lib.FileIO import load_json_file, save_json_file, cfe
from lib.UtilLib import calc_dist,find_angle
import lib.brightstardata as bsd
from lib.DetectLib import eval_cnt

def match_stars_fwd(im_stars, catalog_stars,fit_image,cal_params):
   fit_image = fit_image.copy()
   matched_stars = []
   total_res_x = 0
   total_res_y = 0
   scnt = 0
   for star in img_stars:
      x,y,w,h = star
      scx = int(x + w/2)
      scy = int(y + h/2)

      new_x, new_y, ra,dec, az, el = XYtoRADec(scx,scy,cal_param_file,cal_params,json_conf)
      print("MATCH STAR: ", x,y,ra,dec,az,el)
      star_point = (ra,dec)
      close_matches = find_close_stars_fwd(star_point, catalog_stars)


      if len(close_matches) >= 1:
         name,mag,ra,dec,cat_x,cat_y,cat_star_dist = close_matches[0]
         cat_x,cat_y = int(cat_x), int(cat_y) 
         cv2.rectangle(fit_image, (cat_x-8, cat_y-8), (cat_x + 8, cat_y + 8), (255, 255, 255), 1)
         cv2.putText(fit_image, name ,  (cat_x-5,cat_y-12), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
         cv2.line(fit_image, (scx,scy), (cat_x,cat_y), (255), 1) 
         matched_stars.append(( name,mag,ra,dec,cat_x,cat_y ,scx,scy,cat_star_dist,cat_star_dist))
         total_res_x = total_res_x + cat_star_dist 
         total_res_y = total_res_y + cat_star_dist
      scnt = scnt + 1

   desc = "Matched {:d} stars out of {:d} total image stars and {:d} total catalog stars. {:f} residual error.".format(len(matched_stars), len(img_stars), len(catalog_stars),total_res_x)
   cv2.putText(fit_image, desc,  (5,12), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
   show_img = cv2.resize(fit_image, (0,0),fx=.5, fy=.5)
   cv2.imshow('pepe', show_img)
   cv2.waitKey(1)

   return(matched_stars,total_res_x,total_res_y)
 
def match_stars(im_stars, catalog_stars,fit_image):
   fit_image = fit_image.copy()
   matched_stars = []
   total_res_x = 0
   total_res_y = 0
   for star in img_stars:
      x,y,w,h = star
      scx = int(x + w/2)
      scy = int(y + h/2)
      star_point = (scx,scy)
      close_matches = find_close_stars(star_point, catalog_stars)
      if len(close_matches) >= 1:
         name,mag,ra,dec,cat_x,cat_y,cat_star_dist = close_matches[0]
         res_x = abs(cat_x - scx)
         res_y = abs(cat_y - scy)
         matched_stars.append(( name,mag,ra,dec,cat_x,cat_y ,scx,scy,res_x,res_y))
         dist = calc_dist((cat_x,cat_y),(x,y))
         total_res_x = total_res_x + dist 
         total_res_y = total_res_y + dist 
         #for name,mag,ra,dec,cat_x,cat_y in close_matches:  
         #   cv2.rectangle(fit_image, (cat_x-2, cat_y-2), (cat_x + 2, cat_y + 2), (128, 128, 128), 1)
   for name,mag,ra,dec,cat_x,cat_y ,scx,scy,res_x,res_y in matched_stars:
      cv2.rectangle(fit_image, (cat_x-2, cat_y-2), (cat_x + 2, cat_y + 2), (255, 0, 0), 1)
      cv2.rectangle(fit_image, (scx-5, scy-5), (scx+ 5, scy+ 5), (255, 0, 0), 1)
      cv2.line(fit_image, (scx,scy), (cat_x,cat_y), (255), 2) 
      cv2.putText(fit_image, name ,  (cat_x-5,cat_y-12), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)

   show_img = cv2.resize(fit_image, (0,0),fx=.5, fy=.5)
   cv2.imshow('pepe', show_img)
   cv2.waitKey(10)
   return(matched_stars,total_res_x,total_res_y)

   
def minimize_poly_params_fwd(cal_param_file, cal_params,img_stars,catalog_stars,fit_image,json_conf):
   cv2.namedWindow('pepe')
   fov_poly = np.zeros(shape=(2,), dtype=np.float64)
   pos_poly = np.zeros(shape=(1,), dtype=np.float64)
   x_poly_fwd = np.zeros(shape=(15,), dtype=np.float64)
   y_poly_fwd = np.zeros(shape=(15,), dtype=np.float64)
   cal_params['x_poly_fwd'] = x_poly_fwd
   cal_params['y_poly_fwd'] = y_poly_fwd

   # do x poly fwd 

   field = 'x_poly_fwd'
   res = scipy.optimize.minimize(reduce_fit_fwd, x_poly_fwd, args=(field,img_stars, catalog_stars,cal_params, "x",x_poly_fwd,y_poly_fwd,fov_poly,pos_poly,fit_image), method='Nelder-Mead')
   x_poly_fwd = res['x']
   x_fun_fwd = res['fun']

   print(x_poly_fwd)
   print(x_fun_fwd)

   # do y poly fwd 
   field = 'y_poly_fwd'
   res = scipy.optimize.minimize(reduce_fit_fwd, y_poly_fwd, args=(field,img_stars, catalog_stars,cal_params, "x",x_poly_fwd,y_poly_fwd,fov_poly,pos_poly,fit_image), method='Nelder-Mead')
   y_poly_fwd = res['x']
   y_fun_fwd = res['fun']



   cal_params['x_poly_fwd'] = x_poly_fwd.tolist()
   cal_params['y_poly_fwd'] = y_poly_fwd.tolist()
   cal_params['x_fun_fwd'] = x_fun_fwd
   cal_params['y_fun_fwd'] = y_fun_fwd

   img_x = 960
   img_y = 540
   new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(img_x,img_y,cal_param_file,cal_params,json_conf)
   cal_params['center_az'] = img_az
   cal_params['center_el'] = img_el


   save_json_file(cal_param_file, cal_params)


def minimize_poly_params(cal_param_file, cal_params,img_stars,fit_image,json_conf):
   cv2.namedWindow('pepe')
   fov_poly = np.zeros(shape=(2,), dtype=np.float64)
   pos_poly = np.zeros(shape=(1,), dtype=np.float64)

   x_poly = np.zeros(shape=(15,), dtype=np.float64)
   y_poly = np.zeros(shape=(15,), dtype=np.float64)
   x_poly_fwd = np.zeros(shape=(15,), dtype=np.float64)
   y_poly_fwd = np.zeros(shape=(15,), dtype=np.float64)

   cal_params['x_poly_fwd'] = x_poly_fwd.tolist()
   cal_params['y_poly_fwd'] = y_poly_fwd.tolist()

   fatol = 7
   xatol_ang = 3

   img_x = 960
   img_y = 540
   #XYtoRADec(img_x,img_y,cal_param_file,cal_params,json_conf)
   #exit() 
   #minimize the fov center error 
   field = 'fov_center'
   res = scipy.optimize.minimize(reduce_fit, fov_poly, args=(field,img_stars, cal_params, "x",x_poly,y_poly,fov_poly,pos_poly,fit_image), method='Nelder-Mead')
   fov_poly = res['x']

   #minimize the pos_ang error 
    
   field = 'pos_ang'
   res = scipy.optimize.minimize(reduce_fit, pos_poly, args=(field, img_stars, cal_params, "x",x_poly,y_poly,fov_poly,pos_poly,fit_image), method='Nelder-Mead')
   pos_poly = res['x']

   # now do the x_poly & y_poly
   field = 'x_poly'
   res = scipy.optimize.minimize(reduce_fit, x_poly, args=(field, img_stars, cal_params, "x",x_poly,y_poly,fov_poly,pos_poly,fit_image), method='Nelder-Mead')
   x_poly = res['x']
   x_fun = res['fun']

   field = 'y_poly'
   res = scipy.optimize.minimize(reduce_fit, y_poly, args=(field, img_stars, cal_params, "x",x_poly,y_poly,fov_poly,pos_poly,fit_image), method='Nelder-Mead')
   y_poly = res['x']
   y_fun = res['fun']

   cal_params['fov_poly'] = fov_poly.tolist()
   cal_params['pos_ang'] = pos_poly.tolist()
   cal_params['x_poly'] = x_poly.tolist()
   cal_params['y_poly'] = y_poly.tolist()
   cal_params['x_fun'] = x_fun
   cal_params['y_fun'] = y_fun
   save_json_file(cal_param_file, cal_params)

def reduce_fit_fwd(this_poly,field, image_stars,catalog_stars,cal_params,dim,x_poly,y_poly,fov_poly,pos_poly,fit_image):
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
 

   matched_stars,total_res_x,total_res_y = match_stars_fwd(img_stars, catalog_stars,fit_image,cal_params)
   if len(matched_stars) > 0:
      matched_perc = len(matched_stars) / len(image_stars)
   else:
      total_res_x = 9999
   if matched_perc < .8:
      total_res_x = 9999
   print("RES X:", total_res_x)
   return(total_res_x)

def reduce_fit(this_poly,field, image_stars,cal_params,dim,x_poly,y_poly,fov_poly,pos_poly,fit_image):
   if field == 'fov_center':
      cat_stars = get_catalog_stars(this_poly, pos_poly, cal_params,"x", x_poly,y_poly,0)
   if field == 'pos_ang':
      cat_stars = get_catalog_stars(fov_poly, this_poly, cal_params,"x", x_poly,y_poly,0)
   if field == 'x_poly':
      cat_stars = get_catalog_stars(fov_poly, pos_poly, cal_params,"x", this_poly,y_poly,0)
   if field == 'y_poly':
      cat_stars = get_catalog_stars(fov_poly, pos_poly, cal_params,"x", x_poly,this_poly,0)


   match_perc  = 0
   matched_stars,total_res_x,total_res_y = match_stars(img_stars, cat_stars,fit_image)
   if len(matched_stars) > 0:
      score = total_res_x / len(matched_stars) 
      match_perc = len(matched_stars) / len(image_stars)
      if match_perc < 1:
         score = 9999
   else:
      score = 9999
   return(score)

def get_catalog_stars(fov_poly, pos_poly, cal_params,dimension,x_poly,y_poly,min=0):
   catalog_stars = []
   possible_stars = 0
   img_w = int(cal_params['imagew'])
   img_h = int(cal_params['imageh'])
   RA_center = float(cal_params['ra_center']) + (1000*fov_poly[0])
   dec_center = float(cal_params['dec_center']) + (1000*fov_poly[1])
   F_scale = 3600/float(cal_params['pixscale'])

   fov_w = img_w / F_scale
   fov_h = img_h / F_scale
   fov_radius = np.sqrt((fov_w/2)**2 + (fov_h/2)**2)

   pos_angle_ref = cal_params['position_angle'] + (1000*pos_poly[0])
   x_res = int(cal_params['imagew'])
   y_res = int(cal_params['imageh'])

   center_x = int(x_res / 2)
   center_y = int(x_res / 2)

   bright_stars_sorted = sorted(bright_stars, key=lambda x: x[4], reverse=False)

   for bname, cname, ra, dec, mag in bright_stars_sorted:
      dcname = cname.decode("utf-8")
      dbname = bname.decode("utf-8")
      if dcname == "":
         name = dbname
      else:
         name = dcname

      ang_sep = angularSeparation(ra,dec,RA_center,dec_center)
      if ang_sep < fov_radius-(fov_radius * 0) and float(mag) < 4:
         new_cat_x, new_cat_y = distort_xy_new (0,0,ra,dec,RA_center, dec_center, x_poly, y_poly, x_res, y_res, pos_angle_ref,F_scale)

         possible_stars = possible_stars + 1
         #print(name, mag, new_cat_x, new_cat_y)
         catalog_stars.append((name,mag,ra,dec,new_cat_x,new_cat_y))

   return(catalog_stars)

def find_close_stars_fwd(star_point, catalog_stars):
   star_ra, star_dec = star_point
   dt = 20
   temp= []
   matches = []
   print("\tFIND CLOSE STARS FWD:", star_ra, star_dec)
   for name,mag,ra,dec,cat_x,cat_y in catalog_stars:  
      #print(star_ra,star_dec,name,ra,dec)
      ra, dec= float(ra), float(dec)
      match_dist = abs(angularSeparation(star_ra,star_dec,ra,dec))
      if match_dist < 10:
      #if ra - dt < star_ra < ra + dt and dec -dt < star_dec < dec + dt:
         #star_dist = abs(ra - star_ra) + abs(dec - star_dec)
         #star_dist = angularSeparation(ra,dec,star_ra,star_dec)
         print("MATCH FOR ", star_ra, star_dec, name, ra, dec,match_dist)
         temp.append((name,mag,ra,dec,cat_x,cat_y,match_dist))

   matches = sorted(temp, key=lambda x: x[6], reverse=False)
   if len(matches) > 0:
      print("MATCHED: ", matches[0])

   return(matches[0:1])

def find_close_stars(star_point, catalog_stars):
   dt = 25
   scx,scy = star_point  
   scx,scy = int(scx), int(scy)

   center_dist = calc_dist((scx,scy),(960,540))
   if center_dist > 700:
      dt = 40
   if center_dist > 800:
      dt = 50
   if center_dist > 900:
      dt = 100

   matches = []
   #print("IMAGE STAR:", scx,scy) 
   for name,mag,ra,dec,cat_x,cat_y in catalog_stars:  
      cat_x, cat_y = int(cat_x), int(cat_y)
      if cat_x - dt < scx < cat_x + dt and cat_y -dt < scy < cat_y + dt:
         #print("\t{:s} at {:d},{:d} is CLOSE to image star {:d},{:d} ".format(name,cat_x,cat_y,scx,scy))
         cat_star_dist= calc_dist((cat_x,cat_y),(scx,scy))
         matches.append((name,mag,ra,dec,cat_x,cat_y,cat_star_dist))


   #if len(matches) == 0:
   #   print("\tNo close matches for image star {:d},{:d}".format(scx,scy))

   if len(matches) > 1:
      matches_sorted = sorted(matches, key=lambda x: x[6], reverse=False)
      # check angle back to center from cat star and then angle from cat star to img star and pick the one with the closest match for the star...
      for match in matches_sorted:
         print("MULTI MATCH:", scx,scy, match[0], match[6])
      matches = matches_sorted


   return(matches)
      

mybsd = bsd.brightstardata()
bright_stars = mybsd.bright_stars

json_conf = load_json_file("../conf/as6.json")

cal_param_file = sys.argv[1]
fit_file = sys.argv[2]

cal_params = load_json_file(cal_param_file)

fit_image = cv2.imread(fit_file,0)
fit_image_cp = fit_image.copy()
img_stars,star_img = find_image_stars(fit_image)
for star in img_stars:
   x,y,w,h = star
   cv2.rectangle(fit_image, (x-5, y-5), (x + 5, y + 5), (255, 0, 0), 1)

x_poly = np.zeros(shape=(15,), dtype=np.float64)
y_poly = np.zeros(shape=(15,), dtype=np.float64)
fov_poly = np.zeros(shape=(2,), dtype=np.float64)
pos_poly = np.zeros(shape=(1,), dtype=np.float64)

catalog_stars = get_catalog_stars(fov_poly,pos_poly,cal_params,"x",x_poly,y_poly)

paired_stars = []
for star in img_stars:
   x,y,w,h = star
   scx = int(x + w/2)
   scy = int(y + h/2)
   star_point = (scx,scy)
   close_matches = find_close_stars(star_point, catalog_stars)
   if len(close_matches) > 0:
      for name,mag,ra,dec,cat_x,cat_y,cat_star_dist in close_matches:  
         cv2.rectangle(fit_image, (cat_x-2, cat_y-2), (cat_x + 2, cat_y + 2), (128, 128, 128), 1)
         paired_stars.append((name,mag,ra,dec,cat_x,cat_y,scx,scy,cat_star_dist))

x_poly_fwd = np.zeros(shape=(15,), dtype=np.float64)
y_poly_fwd = np.zeros(shape=(15,), dtype=np.float64)
cal_params['x_poly_fwd'] = x_poly_fwd
cal_params['y_poly_fwd'] = y_poly_fwd

for pair in paired_stars:
   (name,mag,ra,dec,cat_x,cat_y,scx,scy,cat_star_dist) = pair
   new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(scx,scy,cal_param_file,cal_params,json_conf)
   #print("PAIR:", name, scx,scy,cat_x,cat_y,new_x,new_y ,ra,dec, img_ra,img_dec,img_az,img_el)
   print("PAIR:", name, ra,dec, img_ra,img_dec,img_az,img_el)

#exit()
show_img = cv2.resize(fit_image, (0,0),fx=.5, fy=.5)
cv2.namedWindow('pepe')
cv2.imshow('pepe', show_img)
cv2.waitKey(0)
print("LEN CAT:", len(catalog_stars))
minimize_poly_params(cal_param_file,cal_params,img_stars,fit_image,json_conf)
minimize_poly_params_fwd(cal_param_file,cal_params,img_stars,catalog_stars,fit_image_cp,json_conf)
