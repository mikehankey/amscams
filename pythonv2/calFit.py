#!/usr/bin/python3 

import math
import cv2
import math
import numpy as np
import scipy.optimize
import matplotlib.pyplot as plt
import sys
#from caliblib import distort_xy, 
from lib.CalibLib import distort_xy_new
from lib.FileIO import load_json_file, save_json_file, cfe
from lib.UtilLib import calc_dist 
import lib.brightstardata as bsd

mybsd = bsd.brightstardata()
bright_stars = mybsd.bright_stars



def calc_dist_residuals(mapped_stars_file, img_w=1920, img_h=1080, center_off_x=0, center_off_y=0, strength=1):
   #center_off_x = 88
   #center_off_y = 0
   #center_off_x = -6
   #center_off_y = 12
  
   msj = load_json_file(mapped_stars_file)

   x_res = []
   y_res = []
   for line in msj:
      (name2, name1, ra, dec, mag, cat_x, cat_y, img_x, img_y, az, el) = line
      xdiff = cat_x - img_x
      ydiff = cat_y - img_y

      source_x, source_y, new_x, new_y = distort_xy(cat_x,cat_y,img_w,img_h,center_off_x,center_off_y,0,strength)
      dist_xdiff = abs(source_x - img_x)
      dist_ydiff = abs(source_y - img_y)

      x_res.append(dist_xdiff) 
      y_res.append(dist_ydiff) 
      #print("DISTORTION RES X,Y: ", dist_xdiff, dist_ydiff)

   x_total = abs(sum(x_res))
   y_total = abs(sum(y_res))
   if len(x_res) > 0:
      avg_x =  x_total / len(x_res)
      avg_y = y_total / len(y_res)
   else:
      avg_x = "NA"
      avg_y = "NA"

   return(avg_x, avg_y)


def get_fov_stars(params, mapped_stars_file, dimension, other_poly, info_only = 0):
   show = 0
   if dimension == 'x':
      x_poly = params
      y_poly = other_poly
   else:
      y_poly = params
      x_poly = other_poly
   
   cal_params_file = mapped_stars_file.replace("-mapped-stars.json", "-calparams.json")
   cal_img_file = mapped_stars_file.replace("-mapped-stars.json", ".jpg")
   #msj = load_json_file(mapped_stars_file)
   cal_params = load_json_file(cal_params_file)
   cal_img = cv2.imread(cal_img_file)

   img_w = int(cal_params['imagew'])
   img_h = int(cal_params['imageh'])
   RA_center = float(cal_params['ra_center'])
   dec_center = float(cal_params['dec_center'])
   F_scale = 3600/float(cal_params['pixscale'])

   fov_w = img_w / F_scale
   fov_h = img_h / F_scale
   fov_radius = np.sqrt((fov_w/2)**2 + (fov_h/2)**2)

   pos_angle_ref = cal_params['position_angle']
   x_res = int(cal_params['imagew'])
   y_res = int(cal_params['imageh'])

   center_x = int(x_res / 2)
   center_y = int(x_res / 2)

   dist_thresh_base = 35 

   image_stars = find_image_stars(cal_img)
   #for x,y,w,h in image_stars:
   #   cv2.circle(cal_img, (int(x+(w/2)),int(y+(h/2))), 10, (255,255,0), 1)
   lines = []
   matched_stars = 0
   possible_stars = 0

   bright_stars_sorted = sorted(bright_stars, key=lambda x: x[4], reverse=True) 

   for bname, cname, ra, dec, mag in bright_stars_sorted:
      dcname = cname.decode("utf-8")
      dbname = bname.decode("utf-8")
      if dcname == "":
         name = dbname
      else:
         name = dcname

      ang_sep = angularSeparation(ra,dec,RA_center,dec_center)
      if ang_sep < fov_radius and float(mag) < 4:
         possible_stars = possible_stars + 1
         if ang_sep < fov_radius * .5:
            dist_thresh = dist_thresh_base - 20 
         else:
            dist_thresh = dist_thresh_base 
         if ang_sep > fov_radius * .76:
            dist_thresh = dist_thresh_base + 15
         new_cat_x, new_cat_y = distort_xy_new (0,0,ra,dec,RA_center, dec_center, x_poly, y_poly, x_res, y_res, pos_angle_ref,F_scale)
         if (new_cat_x > 0 and new_cat_y > 0) and (new_cat_x < x_res and new_cat_y < y_res):
            match_star, image_stars = pair_star(image_stars,new_cat_x,new_cat_y, dist_thresh) 
            if len(match_star) == 5:
               matched_stars = matched_stars + 1
               sx,sy,sw,sh,dis = match_star
               cv2.circle(cal_img, (int(new_cat_x),int(new_cat_y)), 10, (0,255,0), 1)
               cv2.circle(cal_img, (int(sx+(sw/2)),int(sy+(sh/2))), 10, (0,0,255), 1)
               cv2.line(cal_img, (int(sx+(sw/2)),int(sy+(sh/2))), (int(new_cat_x),int(new_cat_y)), (255), 2) 
               cv2.putText(cal_img, str(name),  (int(new_cat_x-10),int(new_cat_y+15)), cv2.FONT_HERSHEY_SIMPLEX, .4, (255,255,255), 1)

               line = calc_dist( (new_cat_x,new_cat_y), (int(sx+(sw/2)),int(sy+(sh/2)) ))
               lines.append(line)
 
   #if show == 0:
   #   cv2.namedWindow('pepe')
   #   cv2.imshow('pepe', cal_img)
   #   if info_only == 1:
   #      cv2.waitKey(0)
   #   else:
   #      cv2.waitKey(1)
   if len(lines) > 0:
      avg_lines = np.mean(lines)

   if len(lines) > 10:
      cost = (avg_lines**2)*(1.0/np.sqrt(matched_stars + 1))
   else:
      cost = 9999

   if info_only == 1:
      return(matched_stars, avg_lines, cost, possible_stars, cal_img)
   else:
      if len(lines) > 0:
         return(cost)
      else:
         return(cost)

def pair_star(image_stars, cat_x,cat_y, dist_thresh):
   non_matched_stars = []
   matched_stars = []
   for x,y,w,h in image_stars:
      dist = abs(calc_dist((cat_x,cat_y), (x+int(w/2),y+int(h/2))))
      if (cat_x - dist_thresh <= x <= cat_x + dist_thresh) and (cat_y - dist_thresh <= y <= cat_y + dist_thresh):
         matched_stars.append((x,y,w,h,dist))
      else:
         non_matched_stars.append((x,y,w,h))
   if len(matched_stars) == 1:
      return(matched_stars[0], non_matched_stars)
   elif len(matched_stars) > 1:
      fd_temp = sorted(matched_stars, key=lambda x: x[4], reverse=True) 
      return(fd_temp[0], non_matched_stars)

   else:
      return([0], non_matched_stars)
   

def find_image_stars(cal_img):
   if len(cal_img.shape) > 2:
      cal_img= cv2.cvtColor(cal_img, cv2.COLOR_BGR2GRAY)
   cal_img = cv2.GaussianBlur(cal_img, (7, 7), 0)
   #cal_img= cv2.convertScaleAbs(cal_img)
   cal_img = cv2.dilate(cal_img, None , iterations=4)
   (_, cnts, xx) = cv2.findContours(cal_img.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
   star_pixels = []
   non_star_pixels = []
   cloudy_areas = []
   for (i,c) in enumerate(cnts):
      x,y,w,h= cv2.boundingRect(cnts[i])
      if w > 1 and h > 1:
         star_pixels.append((x,y,w,h))
   return(star_pixels)

   

def angularSeparation(ra1,dec1, ra2,dec2):

   ra1 = math.radians(float(ra1))
   dec1 = math.radians(float(dec1))
   ra2 = math.radians(float(ra2))
   dec2 = math.radians(float(dec2))
   return math.degrees(math.acos(math.sin(dec1)*math.sin(dec2) + math.cos(dec1)*math.cos(dec2)*math.cos(ra2 - ra1)))
 

def denis(mapped_stars_file):
   cal_params_file = mapped_stars_file.replace("-mapped-stars.json", "-calparams.json")
   cal_img_file = mapped_stars_file.replace("-mapped-stars.json", ".jpg")
   #calc_dist_residuals(mapped_stars_file)
   cal_img = cv2.imread(cal_img_file)
   msj = load_json_file(mapped_stars_file)
   cal_params = load_json_file(cal_params_file)
   img_w = int(cal_params['imagew'])
   img_h = int(cal_params['imageh'])
   pos_angle_ref = cal_params['position_angle']
   RA_center = cal_params['ra_center']
   dec_center = cal_params['dec_center']
   F_scale = float(cal_params['pixscale'])
   x_res = 1920
   y_res = 1080
   for param in cal_params:
      print(param, cal_params[param])


   # Distortion fit
   x_poly = np.zeros(shape=(12,), dtype=np.float64)
   y_poly = np.zeros(shape=(12,), dtype=np.float64)
   # Set the first coeffs to 0.5, as that is the real centre of the FOV
   x_poly[0] = 1
   y_poly[0] = 3
   x_poly[1] = .00001
   y_poly[1] = .00001
   x_err = 0
   y_err = 0
   for line in msj:
      (name2, name1, ra, dec, mag, cat_x, cat_y, img_x, img_y, az, el) = line
      cat_x, cat_y = int(cat_x), int(cat_y)
      new_cat_x, new_cat_y = distort_xy_new (cat_x,cat_y,ra,dec,RA_center, dec_center, x_poly, y_poly, x_res, y_res, pos_angle_ref,F_scale)
      x_diff = cat_x - new_cat_x 
      y_diff = cat_y - new_cat_y
      #print(cat_x, cat_y, new_cat_x, new_cat_y)
      x_err = x_err + x_diff
      y_err = y_err + y_diff
      #cv2.circle(cal_img, (int(cat_x),int(cat_y)), 10, (0,255,0), 1)
      cv2.circle(cal_img, (int(new_cat_x),int(new_cat_y)), 10, (0,0,255), 1)
   #if show == 0:
   #   cv2.namedWindow('pepe')
   #   cv2.imshow('pepe', cal_img)
   #   cv2.waitKey(0)


def plot_stars(maped_stars_file, center_off_x=0, center_off_y = 0):
   show = 0
   cal_params_file = mapped_stars_file.replace("-mapped-stars.json", "-calparams.json")
   cal_img_file = mapped_stars_file.replace("-mapped-stars.json", ".jpg")
   #calc_dist_residuals(mapped_stars_file)
   print(cal_img_file)
   cal_img = cv2.imread(cal_img_file)
   msj = load_json_file(mapped_stars_file)
   cal_params = load_json_file(cal_params_file)
   img_w = int(cal_params['imagew'])
   img_h = int(cal_params['imageh'])
   strength = 1


   for line in msj:
      (name2, name1, ra, dec, mag, cat_x, cat_y, img_x, img_y, az, el) = line
      cat_x, cat_y = int(cat_x), int(cat_y)
      if name1 == "":
         name = name2
      else:
         name = name1
      cv2.circle(cal_img, (img_x,img_y), 5, (255,0,0), 1)
      #  cv2.circle(cal_img, (int(cat_x),int(cat_y)), 5, (0,0,255), 1)
      cv2.rectangle(cal_img, (cat_x - 3, cat_y - 3), (cat_x + 3, cat_y + 3), (255, 255, 255), 1)
      source_x, source_y, new_x, new_y = distort_xy(cat_x,cat_y,img_w,img_h,center_off_x,center_off_y,0,strength)
      cv2.circle(cal_img, (int(source_x),int(source_y)), 10, (0,255,0), 1)

      cv2.circle(cal_img, (int(img_w/2),int(img_h/2)), 100, (128,128,128), 1)
      cv2.circle(cal_img, (int(img_w/2),int(img_h/2)), 200, (128,128,128), 1)
      cv2.circle(cal_img, (int(img_w/2),int(img_h/2)), 300, (128,128,128), 1)
      cv2.circle(cal_img, (int(img_w/2),int(img_h/2)), 400, (128,128,128), 1)
      cv2.circle(cal_img, (int(img_w/2),int(img_h/2)), 500, (128,128,128), 1)
      cv2.circle(cal_img, (int(img_w/2),int(img_h/2)), 600, (128,128,128), 1)
      cv2.circle(cal_img, (int(img_w/2),int(img_h/2)), 700, (128,128,128), 1)
      cv2.circle(cal_img, (int(img_w/2),int(img_h/2)), 800, (128,128,128), 1)
      cv2.circle(cal_img, (int(img_w/2),int(img_h/2)), 900, (128,128,128), 1)
      cv2.circle(cal_img, (int(img_w/2),int(img_h/2)), 1000, (128,128,128), 1)
   #if show == 0: 
   #   cv2.namedWindow('pepe')
   #   cv2.imshow('pepe', cal_img)
      cv2.waitKey(0)

def minimize_poly(mapped_stars_file):
   show = 0
   cal_params_file = mapped_stars_file.replace("-mapped-stars.json", "-calparams.json")
   fit_image_file = mapped_stars_file.replace("-mapped-stars.json", "-calfit.jpg")
   cal_params = load_json_file(cal_params_file)

   x_poly = np.zeros(shape=(15,), dtype=np.float64)
   y_poly = np.zeros(shape=(15,), dtype=np.float64)

   nmatched, avg_dist, cost, possible_stars,cal_image = get_fov_stars(x_poly, mapped_stars_file,"x",y_poly, 1)
   #avg_dist = get_fov_stars(x_poly, mapped_stars_file,"x",y_poly)

   fov_w = 1920 / (3600/165)
   fatol = (45**2/np.sqrt(possible_stars)*2)
   xatol_ang = 45*fov_w/1920
   fatol = 7
   xatol_ang = 3
   print("FATOL:", fatol, xatol_ang)
   res = scipy.optimize.minimize(get_fov_stars, x_poly, args=(mapped_stars_file, "x", y_poly), method='Nelder-Mead', options={'fatol':fatol, 'xatol':xatol_ang})
   x_poly = res['x']
   x_fun = res['fun']
   print("RES:", res)
   res = scipy.optimize.minimize(get_fov_stars, y_poly, args=(mapped_stars_file, "y", x_poly), method='Nelder-Mead', options={'fatol':fatol, 'xatol':xatol_ang})

   print("RES:", res)
   y_poly = res['x']
   y_fun = res['fun']
   
  # res = scipy.optimize.minimize(get_fov_stars, x_poly, args=(mapped_stars_file, "x", y_poly), method='Nelder-Mead')
  # x_poly = res['x']
   
   nmatched, avg_dist, cost, possible_stars,fit_image = get_fov_stars(x_poly, mapped_stars_file,"x",y_poly, 1)
   cv2.imwrite(fit_image_file, fit_image)
   cal_params['x_poly'] = x_poly.tolist()
   cal_params['y_poly'] = y_poly.tolist()
   cal_params['x_fun'] = x_fun
   cal_params['y_fun'] = y_fun
   save_json_file(cal_params_file, cal_params) 

#cmd = sys.argv[1]
mapped_stars_file = sys.argv[1]

center_off_x = 1 
center_off_y = 75
#center_off_y = 0
#denis(mapped_stars_file)
#x_poly = np.zeros(shape=(12,), dtype=np.float64)
#y_poly = np.zeros(shape=(12,), dtype=np.float64)

#cal_params_file = mapped_stars_file.replace("-mapped-stars.json", "-calparams.json")
#cal_params = load_json_file(cal_params_file)
#x_poly = np.asarray(cal_params['x_poly'], dtype=np.float64)
#y_poly = np.asarray(cal_params['y_poly'], dtype=np.float64)

#nmatched, avg_dist, cost, possible_stars = get_fov_stars(x_poly, mapped_stars_file,"x",y_poly, 1)

minimize_poly(mapped_stars_file)
exit()
#calc_dist_residuals(mapped_stars_file, 1920, 1080, center_off_x, center_off_y)
#plot_stars(mapped_stars_file, center_off_x, center_off_y)
