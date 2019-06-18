#!/usr/bin/python3
from lib.UtilLib import convert_filename_to_date_cam, haversine, calc_radiant
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

def get_cat_stars(file, cal_params_file, json_conf, cal_params = None):
   if cal_params == None:
      print("CAL PARAMS ARE NONE!")
      exit()
      cal_params = load_json_file(cal_params_file)

   if "lat" in cal_params:
      lat = cal_params['lat']
      lon = cal_params['lon']
      alt = cal_params['alt']
   else:
      lat = json_conf['site']['device_lat']
      lon = json_conf['site']['device_lng']
      alt = json_conf['site']['device_alt']

   ra_center = cal_params['ra_center']
   dec_center = cal_params['dec_center']
   center_az = cal_params['center_az']
   center_el = cal_params['center_el']
   rah,dech = AzEltoRADec(center_az,center_el,file,cal_params,json_conf)
   rah = str(rah).replace(":", " ")
   dech = str(dech).replace(":", " ")

   ra_center,dec_center = HMS2deg(str(rah),str(dech))

   cal_params['ra_center'] = ra_center
   cal_params['dec_center'] = dec_center
   fov_poly = 0
   pos_poly = 0
   x_poly = cal_params['x_poly']
   y_poly = cal_params['y_poly']

   cat_stars = get_catalog_stars(fov_poly, pos_poly, cal_params,"x",x_poly,y_poly,min=0)

   return(cat_stars)



def reduce_fit(this_poly,field, merged_stars, cal_params, fit_img, json_conf, cam_id=None,mode=0,show=0):
   print("SHOW IS:", show)
   this_fit_img = np.zeros((1080,1920),dtype=np.uint8)
   this_fit_img = cv2.cvtColor(this_fit_img,cv2.COLOR_GRAY2RGB)
   global tries

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
   new_merged_stars = []
   avgpixscale = 162
   for star in merged_stars:
      (cal_file,ra_center,dec_center,pos_angle,pixscale,dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy, old_img_res,np_new_cat_x, np_new_cat_y) = star
      #if 157 < float(pixscale) < 163 and old_img_res > 2:
      #   pixscale = avgpixscale
      #if 157 < float(pixscale) < 163 :
      #   pixscale = avgpixscale
 
      if field == 'x_poly' or field == 'y_poly':
         new_cat_x, new_cat_y = distort_xy_new (0,0,ra,dec,float(ra_center), float(dec_center), x_poly, y_poly, float(1920), float(1080), float(pos_angle),3600/float(pixscale))
         img_res = abs(calc_dist((six,siy),(new_cat_x,new_cat_y)))
         if img_res <= 1:
            color = [0,255,0]
         elif 1 < img_res <= 2:
            color = [0,200,0]
         elif 2 < img_res <= 3:
            #rgb
            color = [255,0,0]
         elif 3 <  img_res <= 4:
            color = [0,69,255]
         else:
            color = [0,0,255]

         desc = str(pixscale)[0:4]
         #cv2.putText(this_fit_img, desc,  (int(new_cat_x),int(new_cat_y)), cv2.FONT_HERSHEY_SIMPLEX, .5, (255, 255, 255), 1)
         cv2.rectangle(this_fit_img, (int(new_cat_x)-10, int(new_cat_y)-10), (int(new_cat_x) + 10, int(new_cat_y) + 10), color, 1)
         cv2.line(this_fit_img, (six,siy), (int(new_cat_x),int(new_cat_y)), color, 2) 
         new_y = new_cat_y
         new_x = new_cat_x
         #print("RES OLD/NEW:", old_img_res, img_res)
      else:

         #if 157 < float(pixscale) < 164 and float(old_img_res) > 1:
         #   pixscale = avgpixscale
         #if 157 < float(pixscale) < 163 :
         #   pixscale = avgpixscale

         cal_params['ra_center'] = ra_center
         cal_params['dec_center'] = dec_center
         cal_params['position_angle'] = pos_angle 
         cal_params['pixscale'] = pixscale 
         cal_params['imagew'] = 1920
         cal_params['imageh'] = 1080 
         new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(six,siy,cal_file,cal_params,json_conf)
         new_x, new_y= distort_xy_new (0,0,img_ra,img_dec,float(ra_center), float(dec_center), x_poly, y_poly, float(cal_params['imagew']), float(cal_params['imageh']), float(cal_params['position_angle']),3600/float(cal_params['pixscale']))

         img_res = abs(angularSeparation(ra,dec,img_ra,img_dec))

         if img_res <= .1:
            # gree
            color = [0,255,0]
         elif .1 < img_res <= .2:
            # blue 
            color = [0,200,0]
         elif .2 < img_res <= .3:
            # orange
            color = [0,69,255]
         elif img_res > .3:
            # red 
            color = [0,0,255]

         #img_res = abs(calc_dist((six,siy),(new_x,new_y)))

         cv2.rectangle(this_fit_img, (int(new_x)-10, int(new_y)-10), (int(new_x) + 10, int(new_y) + 10), color, 1)
         cv2.line(this_fit_img, (six,siy), (int(new_x),int(new_y)), color, 2) 
      cv2.circle(this_fit_img,(six,siy), 12, (128,128,128), 1)
      new_merged_stars.append((cal_file,ra_center,dec_center,pos_angle,pixscale,dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy, img_res, np_new_cat_x, np_new_cat_y))

      total_res = total_res + img_res
     
 


   total_stars = len(merged_stars)
   if total_stars > 0:
      avg_res = total_res/total_stars
   else:
      avg_res = 999

   desc = "Cam: " + str(cam_id) + " Stars: " + str(total_stars) + " " + field + " Res: " + str(avg_res)[0:6] + " Tries: " + str(tries)
   cv2.putText(this_fit_img, desc,  (5,1070), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 1)

   if show == 1:
      simg = cv2.resize(this_fit_img, (960,540))
      cv2.imshow(cal_params['cam_id'], simg) 
      cv2.waitKey(10)

   print("Total Residual Error:",field, total_res )
   print("Total Stars:", total_stars)
   print("Total Tries:", tries)
   print("Avg Residual Error:", avg_res )
   print("Show:", show)
   tries = tries + 1
   #print("Try:", tries)
   if mode == 0: 
      return(avg_res)
   else:
      return(avg_res, new_merged_stars)


def minimize_poly_params_fwd(merged_stars, json_conf,orig_ra_center=0,orig_dec_center=0,cam_id=None,master_file=None,show=1):
   if len(merged_stars) < 50:
      print("not enough stars to multi fit!")
      return(0,0,0)

   if master_file is None:
      master_fn = "master_cal_file_" + str(cam_id) + ".json"
      master_file = "/mnt/ams2/cal/hd_images/" + master_fn
   if cfe(master_file) == 1:
      first_run = 0
   else:
      first_run = 1

   merged_stars = clean_pairs(merged_stars,cam_id,5,first_run,show)

   img = np.zeros((1080,1920),dtype=np.uint8)
   img = cv2.cvtColor(img,cv2.COLOR_GRAY2RGB)

   err_list = []
   for star in merged_stars:
      print("STAR:", len(star))
      if len(star) == 23:
         (cal_file,ra_center,dec_center,position_angle,pixscale,dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy, img_res,np_new_cat_x,np_new_cat_y) = star
      elif len(merged_stars) == 21:
         (cal_file,ra_center,dec_center,position_angle,pixscale,dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy, img_res) = star
      err_list.append(img_res)
      cv2.circle(img,(six,siy), 10, (255), 1)
   #cv2.imshow("MIKE", img)
   #cv2.waitKey(0)
   #exit()
   std_dist = np.mean(err_list)
   cal_params = {}
   print("MS LEN:", len(merged_stars))
   if len(merged_stars) < 20:
      return(cal_params)

   #fit_img_file = cal_params_file.replace("-calparams.json", ".png")
   #fit_img = cv2.imread(fit_img_file)
   fit_img = np.zeros((1080,1920),dtype=np.uint8)
   fit_img = cv2.cvtColor(fit_img,cv2.COLOR_GRAY2RGB)

   if show == 1:
      cv2.namedWindow(cam_id)

   #close_stars = cal_params['close_stars']
   # do x poly fwd
   if show == 1:
      cv2.namedWindow(cam_id) 
   this_fit_img = fit_img.copy()
   for star in merged_stars:
      (cal_file,ra_center,dec_center,position_angle,pixscale,dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy, img_res,np_new_cat_x,np_new_cat_y) = star
      if img_res <= 1:
         color = [0,255,0]
      elif 1 < img_res <= 2:
         color = [0,200,0]
      elif 2 < img_res <= 3:
         color = [255,0,0]
      elif 3 <  img_res <= 4:
         color = [0,69,255]
      else:
         color = [0,0,255]
   cv2.imwrite("/mnt/ams2/test.png", this_fit_img)
   simg = cv2.resize(this_fit_img, (960,540))
   if show == 1:
      cv2.imshow(cam_id, simg)
      cv2.waitKey(10)


   # do x poly 
   field = 'x_poly'
   #cal_params['pixscale'] = 158.739329193

   if cfe(master_file) == 1:
      first_run = 0
      print(master_file)
      temp = load_json_file(master_file)

      x_poly_fwd = temp['x_poly_fwd'] 
      y_poly_fwd = temp['y_poly_fwd'] 
      x_poly = temp['x_poly'] 
      y_poly = temp['y_poly'] 
      strict = 1
   else:
      first_run = 1
      x_poly = np.zeros(shape=(15,), dtype=np.float64)
      y_poly = np.zeros(shape=(15,), dtype=np.float64)
      x_poly_fwd = np.zeros(shape=(15,), dtype=np.float64)
      y_poly_fwd = np.zeros(shape=(15,), dtype=np.float64)
      strict = 0
   cal_params['cam_id'] = cam_id 
   cal_params['x_poly'] = x_poly
   cal_params['y_poly'] = y_poly
   cal_params['x_poly_fwd'] = x_poly_fwd
   cal_params['y_poly_fwd'] = y_poly_fwd

   res,updated_merged_stars = reduce_fit(x_poly, "x_poly",merged_stars,cal_params,fit_img,json_conf,cam_id,1,show)

   #print("XP",x_poly)
   #exit()

   std_dist, avg_dist = calc_starlist_res(merged_stars)
   print("INITIAL RES: ", res, strict)
   print("STD/AVG DIST: ", std_dist, avg_dist)
   res,updated_merged_stars = reduce_fit(x_poly, "x_poly",merged_stars,cal_params,fit_img,json_conf,cam_id,1,show)

   # remove bad stars here (just a little)
   if first_run == 1:
      std_dev_dist = res * 6
   else:
      std_dev_dist = res * 6
   c = 0
   new_merged_stars = []
   #if std_dev_dist < 10:
   #   std_dev_dist = 10 
   
   #std_dev_dist = 100
   res,updated_merged_stars = reduce_fit(x_poly, "x_poly",merged_stars,cal_params,fit_img,json_conf,cam_id,1,show)
   for star in updated_merged_stars:
      (cal_file,ra_center,dec_center,pos_angle,pixscale,dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy, img_res,np_new_cat_x,np_new_cat_y) = star
      #new_merged_stars.append(star)
      if img_res < std_dev_dist :
         new_merged_stars.append(star)
      else:
         print("REMOVING: ", star)
   print("AVG RES:", res)
   print("OLD MERGED STARS:", len(merged_stars))
   print("NEW MERGED STARS:", len(new_merged_stars))
   merged_stars = new_merged_stars 
   options = {}
         
   mode = 0 
   res = scipy.optimize.minimize(reduce_fit, x_poly, args=(field,new_merged_stars,cal_params,fit_img,json_conf,cam_id,mode,show), method='Nelder-Mead', options={})
   x_poly = res['x']
   x_fun = res['fun']
   cal_params['x_poly'] = x_poly.tolist()
   cal_params['x_fun'] = x_fun

   # ok really remove bad stars now
   std_dist, avg_dist = calc_starlist_res(new_merged_stars)
   if first_run == 1:
      std_dev_dist = x_fun * 3
   else:
      std_dev_dist = x_fun * 2
   c = 0

   merged_stars =  new_merged_stars
   new_merged_stars = []
   res,updated_merged_stars = reduce_fit(x_poly, "x_poly",merged_stars,cal_params,fit_img,json_conf,cam_id,1,show)
   if res < 1:
      std_dev_dist = 2


   for star in updated_merged_stars:
      (cal_file,ra_center,dec_center,pos_angle,pixscale,dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy, img_res, np_new_cat_x,np_new_cat_y) = star
      new_merged_stars.append(star)
      #if img_res < std_dev_dist :
      #   new_merged_stars.append(star)
   print("AVG RES:", res)
   print("OLD MERGED STARS:", len(merged_stars))
   print("NEW MERGED STARS:", len(new_merged_stars))
   merged_stars = new_merged_stars 
   options = {}

   # now do x-poly again without the junk stars
   mode = 0 
   res = scipy.optimize.minimize(reduce_fit, x_poly, args=(field,merged_stars,cal_params,fit_img,json_conf,cam_id,mode,show), method='Nelder-Mead', options={})
   x_poly = res['x']
   x_fun = res['fun']
   cal_params['x_poly'] = x_poly.tolist()
   cal_params['x_fun'] = x_fun


      
   # do y poly 
   field = 'y_poly'
   res = scipy.optimize.minimize(reduce_fit, y_poly, args=(field,merged_stars,cal_params,fit_img,json_conf,cam_id,mode,show), method='Nelder-Mead', options={})
   y_poly = res['x']
   y_fun = res['fun']
   cal_params['y_poly'] = y_poly.tolist()
   cal_params['y_fun'] = y_fun
   


   # do x poly fwd
   field = 'x_poly_fwd'
   xa = .05
   fa = .05
   res = scipy.optimize.minimize(reduce_fit, x_poly_fwd, args=(field,merged_stars,cal_params,fit_img,json_conf,cam_id,mode,show), method='Nelder-Mead'  )
   x_poly_fwd = res['x']
   x_fun_fwd = res['fun']
   cal_params['x_poly_fwd'] = x_poly_fwd.tolist()
   cal_params['x_fun_fwd'] = x_fun_fwd

   # do y poly fwd
   field = 'y_poly_fwd'
   res = scipy.optimize.minimize(reduce_fit, y_poly_fwd, args=(field,merged_stars,cal_params,fit_img,json_conf,cam_id,mode,show), method='Nelder-Mead')
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
   #new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(img_x,img_y,cal_params_file,cal_params,json_conf)
   cal_params['center_az'] = img_az
   cal_params['center_el'] = img_el
   #cal_params['ra_center'] = orig_ra_center
   #cal_params['dec_center'] = orig_dec_center
   #cal_params_file = cal_params_file.replace("-calparams.json", "-calparams-master.json")
   #save_json_file(cal_params_file, cal_params)
   #print(cal_params_file)
   return(1, cal_params, merged_stars )


def calc_starlist_res(ms):

   # compute std dev distance
   tot_res = 0
   close_stars = []
   dist_list = []
   for star in ms:
      (cal_file,ra_center,dec_center,pos_angle,pixscale,dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy, img_res,np_new_cat_x,np_new_cat_y) = star
      #px_dist = calc_dist((six,siy),(new_cat_x,new_cat_y))
      dist_list.append(img_res)
   std_dev_dist = np.std(dist_list)
   avg_dev_dist = np.mean(dist_list)
   return(std_dev_dist, avg_dev_dist)


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

  
   print("TOTAL STARS FOR MULTI FIT: ", len(merged_stars))
#   for star in merged_stars:
#      print(star)
#Her', 3.9, 255.0725, 30.9264, 254.93918273042874, 31.134331748651338, 0.23724688302817137, 1241.672569534275, 499.3139621783825, 80.29912941591652, 41.13792480322102, 1233, 505, 1230, 501, 5.0)
#   exit()

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
      if cat_dist < 10: 
         merged_stars.append((cal_file,ra_center,dec_center, dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist))
      print("MIKE:", six,siy, cat_dist)
   

   return(merged_stars)

def find_matching_cal_files(date_str, cam_id):
   match = []
   glob_dir = "/mnt/ams2/cal/autocal/tmp/*calparams.json"
   print(glob_dir)
   #all_files = glob.glob("/mnt/ams2/cal/fit_pool/*.json")
   all_files = glob.glob(glob_dir)
   for file in all_files:
      if cam_id in file :
         match.append(file)
   return(match)

if __name__ == "__main__":

   tries = 0
   json_conf = load_json_file("../conf/as6.json")


   cal_params_file = sys.argv[1]
   try:
      cam_id = sys.argv[2]
   except:
      cam_id = None


   print(cal_params_file)
   cal_params = load_json_file(cal_params_file)
   total_res = 0
   total_res_fwd = 0

   merged_stars, merged_files, orig_ra_center, orig_dec_center = build_multi_cal(cal_params_file, json_conf)
   cal_params['merged_stars'] = merged_stars
   cal_params['merged_files'] = merged_files
   minimize_poly_params_fwd(merged_stars, cal_params_file, cal_params,json_conf,orig_ra_center,orig_dec_center,cam_id)


def collinear(x1, y1, x2, y2, x3, y3): 
   return ((y1 - y2) * (x1 - x3), (y1 - y3) * (x1 - x2));


def clean_pairs(merged_stars, cam_id = "", inc_limit = 5,first_run=1,show=0):
 
#   np_cat_stars = get_cat_stars(file,file,json_conf,cal_params)
#   np_name,np_mag,np_ra,np_dec,np_new_cat_x,np_new_cat_y = no_poly_star
#   np_angle_to_center = find_angle((960,540), (np_new_cat_x, np_new_cat_y))
#   no_poly_cat_stars = {}
#   for cat_star in np_cat_stars:
#      (name,mag,ra,dec,new_cat_x,new_cat_y) = cat_star
#      key = str(ra) + ":" + str(dec)
#      no_poly_cat_stars[key] = cat_star


   orig_merge_stars = merged_stars
   updated_merged_stars = []
   img = np.zeros((1080,1920),dtype=np.uint8)
   img = cv2.cvtColor(img,cv2.COLOR_GRAY2RGB)
   #np_ms = np.empty(shape=[21,0])
   np_ms = np.array([[0,0,0,0,0]])
   #print(np_ms.shape)
   ms_index = {}
   for star in merged_stars:
      print("STAR:", star)
      if len(star) == 23 or len(star) == 21:
         if len(star) == 23:
            (cal_file,ra_center,dec_center,position_angle,pixscale,dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy, img_res,np_new_cat_x,np_new_cat_y) = star
            ms_key = str(ra) + ":" + str(dec) + ":" + str(six) + ":" + str(siy)
            ms_index[ms_key] = star
         elif len(star) == 21:
            (cal_file,ra_center,dec_center,position_angle,pixscale,dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy, img_res) = star
            ms_key = str(ra) + ":" + str(dec) + ":" + str(six) + ":" + str(siy)
            ms_index[ms_key] = (cal_file,ra_center,dec_center,position_angle,pixscale,dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy, img_res,0,0)

         np_angle_to_center = find_angle((960,540), (np_new_cat_x, np_new_cat_y))
         img_angle_to_center = find_angle((960,540), (six, siy))
         ang_diff = abs(img_angle_to_center - np_angle_to_center)
         np_dist = calc_dist((six,siy), (np_new_cat_x, np_new_cat_y))
         col1,col2 = collinear(six,siy,np_new_cat_x,np_new_cat_y,960,540)
         print("COL:", col1,col2)
         if ang_diff > 1:

            #print("NPDIST:", np_dist)
            print("BAD ANG:", six, siy, dcname, new_cat_x, new_cat_y, np_new_cat_x, np_new_cat_y, " -- ", img_angle_to_center, np_angle_to_center, ang_diff)
            bad = 1
         elif np_dist < 50:
            print("GOOD ANG:", six, siy, dcname, new_cat_x, new_cat_y, np_new_cat_x, np_new_cat_y, " -- ", img_angle_to_center, np_angle_to_center, ang_diff)
            color = (255)
            #cv2.rectangle(img, (int(new_cat_x-2), int(new_cat_y-2)), (int(new_cat_x + 2), int(new_cat_y + 2)), color, 1)
            #cv2.rectangle(img, (six-4, siy-4), (six+4, siy+4), (128, 128, 128), 1)
            #cv2.line(img, (960,540), (int(np_new_cat_x),int(np_new_cat_y)), (128), 1) 

            cv2.rectangle(img, (int(new_x-2), int(new_y-2)), (int(new_x + 2), int(new_y + 2)), (255), 1)
            #cv2.line(img, (six,siy), (int(new_x),int(new_y)), (255), 1)
            line_dist = calc_dist((six,siy), (np_new_cat_x, np_new_cat_y))
            if line_dist > 20:
               cv2.line(img, (six,siy), (int(np_new_cat_x),int(np_new_cat_y)), (0,0,255), 1)
            else:
               cv2.line(img, (six,siy), (int(np_new_cat_x),int(np_new_cat_y)), (0,255,0), 1)
          
            print("LINE: ", six, siy, new_x, new_y, np_new_cat_x, np_new_cat_y)
            cv2.circle(img,(six,siy), 5, (255), 1)
            if line_dist < 50:  
               np_ms = np.append(np_ms, [[ra,dec,six,siy,img_res]],axis=0 )
      else: 
         print("STAR MISSING SOME FIELDS!", star)
         exit()

   show = 1
   if show == 1:
      simg = cv2.resize(img, (960,540))
      cv2.imshow(cam_id, simg)
      cv2.imwrite("/mnt/ams2/tmp/fitmovies/star_img1.png", img)
      cv2.waitKey(0)


   img = np.zeros((1080,1920),dtype=np.uint8)
   img = cv2.cvtColor(img,cv2.COLOR_GRAY2RGB)
   avg_res = np.mean(np_ms[:,4])
   std_res = np.std(np_ms[:,4])
   print(np_ms[4:,])
   for x in np_ms[:,4]:
      print(x)
   print("NP RES:", avg_res, std_res)
   if first_run == 0:
      std_res = std_res * 2 
   if std_res < 1:
      std_res = 1
   if first_run == 1:
      gsize = 200
   else:
      gsize = 50
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
            cv2.rectangle(img, (int(x1), int(y1)), (int(x2) , int(y2) ), (50, 50, 50), 1)
            matches = (np_ms[np.where((np_ms[:,2] > x1) & (np_ms[:,2] < x2) & (np_ms[:,3] > y1) & (np_ms[:,3] < y2)      )  ])
            if len(matches) > 0:
               bad = 0
               matches = sorted(matches, key=lambda x: x[4], reverse=False)
               match = matches[0]
               key = str(match[0]) + ":" + str(match[1]) + ":" + str(int(match[2])) + ":" + str(int(match[3]))
               info = ms_index[key]
               print("MATCH:", key, info)

               (cal_file,ra_center,dec_center,position_angle,pixscale,dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy, img_res,np_new_cat_x,np_new_cat_y) = info 
               cv2.rectangle(img, (int(new_x-2), int(new_y-2)), (int(new_x + 2), int(new_y + 2)), (255), 1)
               line_dist = calc_dist((six,siy),(new_x,new_y))
               if line_dist > 100:
                  cv2.line(img, (six,siy), (int(new_x),int(new_y)), (0,0,255), 1)
               else:
                  cv2.line(img, (six,siy), (int(new_x),int(new_y)), (255), 1)

               line_dist = calc_dist((six,siy),(np_new_cat_x,np_new_cat_y))
               if line_dist > 100:
                  #cv2.line(img, (six,siy), (int(np_new_cat_x),int(np_new_cat_y)), (0,0,255), 1)
                  bad = 1
               else:
                  cv2.line(img, (six,siy), (int(np_new_cat_x),int(np_new_cat_y)), (255,255,255), 1)

               #cv2.line(img, (960,540), (int(np_new_cat_x),int(np_new_cat_y)), (128), 1) 
               #cv2.line(img, (960,540), (int(six),int(siy)), (128), 1) 
               print("LINE: ", six, siy, new_x, new_y, np_new_cat_x, np_new_cat_y)
               cv2.circle(img,(six,siy), 5, (255), 1)
               if bad == 0:
                  updated_merged_stars.append((cal_file,ra_center,dec_center,position_angle,pixscale,dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy, img_res,np_new_cat_x,np_new_cat_y))

            else:   
               print("No match for grid square :(")
   show = 1
   if show == 1:
      simg = cv2.resize(img, (960,540))
      cv2.imshow(cam_id, simg)
      cv2.imwrite("/mnt/ams2/tmp/fitmovies/star_img2.png", img)
      cv2.waitKey(0)

   #return(merged_stars)
   return(updated_merged_stars)





