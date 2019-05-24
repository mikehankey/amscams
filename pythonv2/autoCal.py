#!/usr/bin/python3
import datetime
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
from lib.UtilLib import check_running, get_sun_info, fix_json_file

from lib.ImageLib import mask_frame , stack_frames
#import matplotlib
#matplotlib.use('Agg')
#import matplotlib.pyplot as plt
import sys
#from caliblib import distort_xy,
from lib.CalibLib import distort_xy_new, find_image_stars, distort_xy_new, XYtoRADec, radec_to_azel, get_catalog_stars,AzEltoRADec , HMS2deg, get_active_cal_file, RAdeg2HMS, clean_star_bg, define_crop_box
from lib.UtilLib import calc_dist, find_angle, bound_cnt, cnt_max_px

from lib.UtilLib import angularSeparation, convert_filename_to_date_cam, better_parse_file_date
from lib.FileIO import load_json_file, save_json_file, cfe
from lib.UtilLib import calc_dist,find_angle
import lib.brightstardata as bsd
from lib.DetectLib import eval_cnt

def save_cal(starfile, master_cal_file, json_conf):
   print("Saving calibration files...")
   master_cal_params = load_json_file(master_cal_file)
   el = master_cal_file.split("/")
   fn = el[-1]
   date = fn[0:10]
   print("DATE:", date)

   cpm = {}
   for cam_id in master_cal_params:
      if "01" in cam_id:
         print(cam_id, len(master_cal_params[cam_id]))
         cpm[cam_id] = master_cal_params[cam_id]

   master_cal_params = cpm

   for cam_id in master_cal_params:
      print(cam_id, len(master_cal_params[cam_id]))
      if len(master_cal_params[cam_id]) > 6:
         cfbase = date + "_00_00_00_000_" + cam_id
         cf_dir = "/mnt/ams2/cal/freecal/" + cfbase + "/"
         cal_params_file = cf_dir + date + "_00_00_00_000_" + cam_id + "-calparams.json"
         cal_params = master_cal_params[cam_id]
         if cfe(cf_dir, 1) == 0:
            print("mkdir ", cf_dir)
            os.system("mkdir " + cf_dir)

         img_az = cal_params['center_az']
         img_el = cal_params['center_el']
         print("AZ:", img_az, img_el)
         rah,dech = AzEltoRADec(img_az,img_el,cal_params_file,cal_params,json_conf)
         rah = str(rah).replace(":", " ")
         dech = str(dech).replace(":", " ")
         ra_center,dec_center = HMS2deg(str(rah),str(dech))
         cal_params['ra_center'] = ra_center
         cal_params['dec_center'] = dec_center
         save_json_file(cal_params_file, cal_params)
         os.system("cp " + starfile + " " + cf_dir)


         os.system("./XYtoRAdecAzEl.py az_grid " + cal_params_file)

def multi_merge(all_stars, json_conf, day_dir, show = 0):
   cameras = json_conf['cameras']
   cam_ids = []
   x_fun = 4
   for cam_id in all_stars:
      master_cal_file = day_dir + "/" + "master_cal_file_" + cam_id + ".json"
      status = 0
      skip = 0
      if cfe(master_cal_file) == 1:
         mcj = load_json_file(master_cal_file)
         #x_fun = float(mcj['x_fun'])
         if mcj['x_fun'] < .5:
            print(" This master file is sub .8-pixel res, it is good for now. Skipping.")
            skip = 1
         #if x_fun < 2:
         #   x_fun = float(mcj['x_fun']) * 1.2
         #else:
         #   x_fun = float(mcj['x_fun']) * 2
      x_fun = 15
      merge_file = day_dir + "/starmerge-" + cam_id + ".json"
      print("CAMID",cam_id, x_fun, merge_file)

      merged_stars = all_stars[cam_id]

      multi_fit_merge = []
      for file in merged_stars:
         #print(file)
         if cfe(file) == 1:
            img = np.zeros((1080,1920),dtype=np.uint8)
            img = cv2.resize(img, (1920,1080))
            for star in merged_stars[file]:
               #print(star)
               cal_params_file,ra_center,dec_center,position_angle,pixscale,name,mag,ra,dec,img_ra,img_dec,match_dist,new_cat_x,new_cat_y,img_az,img_el,new_cat_x,new_cat_y,ix,iy, img_res = star

               cv2.circle(img,(ix,iy), 5, (128,128,128), 1)
               cv2.rectangle(img, (new_cat_x-2, new_cat_y-2), (new_cat_x + 2, new_cat_y + 2), (128, 128, 128), 1)
               cv2.line(img, (ix,iy), (new_cat_x,new_cat_y), (255), 2)
               multi_fit_merge.append(star)
            if show == 1:
               simg = cv2.resize(img, (960,540))
               cv2.imshow('pepe', simg)
               cv2.waitKey(0)

      new_cp = cal_params_file.replace("-calparams.json", "-calparams-master.json")
      master_cal_params = {}
      #if cfe(new_cp) == 0 :
      if True:
         #new_multi_fit_merge = remove_bad_pairs(multi_fit_merge)
         new_multi_fit_merge = clean_pairs(multi_fit_merge, x_fun)
         #new_multi_fit_merge = multi_fit_merge
         cal_params = {}
         cal_params = default_cal_params(cal_params,json_conf)
         # do 1 cam here
         merge_file = day_dir + "/starmerge-" + cam_id + ".json"
         save_json_file(merge_file, new_multi_fit_merge)
         
         if skip == 0:
           
            cmd = "./autoCal.py run_merge " + merge_file + " " + cam_id + " " + str(show) + " &"
            print(cmd)
            os.system(cmd)
      else:
         print("SKIPPING ALREADY DONE!")

def clean_pairs(merged_stars, inc_limit = 5):
   
   merged_stars = sorted(merged_stars, key=lambda x: x[19], reverse=False)

   multi = 0
   good_merge = []
   print("TOTAL MERGED STARS:", len(merged_stars))
   img = np.zeros((1080,1920),dtype=np.uint8)
   dupe_check = {}
   close_stars = {}

   dist_list = []
   for star in merged_stars:
      (cal_file,ra_center,dec_center,position_angle,pixscale,dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy, img_res) = star
      dist_list.append(img_res)
   std_dev_dist = np.std(dist_list) * 2 
   #std_dev_dist = std_dev_dist * 1.2 
   if std_dev_dist < 3:
      std_dev_dist = 3 



   for star in merged_stars:
      (cal_file,ra_center,dec_center,position_angle,pixscale,dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy, img_res) = star
      (f_datetime, cam_id, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(cal_file)
      print("STAR RES:", img_res)
      dupe_key = str(six) + "." + str(siy)
      dist_check = 0
      for key in dupe_check:
         ix, iy = key.split(".")
         dupe_dist = calc_dist((int(ix),int(iy)),(six,siy))
         if dupe_dist < 30 and dupe_dist != 0:
            dist_check = dist_check + 1
            print("STAR DUPE DIST:", cam_id, six,siy,ix,iy,dupe_dist)
         

      #if img_res <= inc_limit and dupe_key not in dupe_check and dist_check == 0:
      if dupe_key not in dupe_check and dist_check < 2 and img_res < std_dev_dist:
         good_merge.append(star)
         cv2.rectangle(img, (new_x-2, new_y-2), (new_x + 2, new_y + 2), (255), 1)
         cv2.line(img, (six,siy), (new_x,new_y), (255), 1)
         cv2.circle(img,(six,siy), 5, (255), 1)
      else:
         print("DUPE STAR DETECTED:", six,siy)

      if dupe_key not in dupe_check:
         dupe_check[dupe_key] = 1 
      else: 
         dupe_check[dupe_key] = dupe_check[dupe_key] + 1

   cv2.imshow('pepe', img)
   cv2.waitKey(1)
   print("TOTAL GOOD MERGED STARS:", len(good_merge))
   return(good_merge)

def star_quad(x,y):
   iw = 1920
   ih = 1080
   hw = int(iw / 2)
   hh = int(ih / 2)
   quad = 0
   if x < hw and y < hh:
      quad = 1
   if x > hw and y < hh:
      quad = 2
   if x < hw and y > hh:
      quad = 3
   if x > hw and y > hh:
      quad = 4
   return(quad)

def remove_bad_pairs(merged_stars):
   good_merge = []
   quad_ang = {}
   quad_avg = [] 
   quad_ang[0] = []
   quad_ang[1] = []
   quad_ang[2] = []
   quad_ang[3] = []
   quad_ang[4] = []
   quad_avg.append(0)
   quad_avg.append(0)
   quad_avg.append(0)
   quad_avg.append(0)
   quad_avg.append(0)
   new_merged_stars = []
   for star in merged_stars:
      (cal_file,ra_center,dec_center,position_angle,dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy, img_res) = star
      angle = find_angle((new_cat_x, new_cat_y), (six,siy)) 
      quad = star_quad(six,siy)
      quad_ang[quad].append(angle)

   quad_avg[1] = np.mean(quad_ang[1])
   quad_avg[2] = np.mean(quad_ang[2])
   quad_avg[3] = np.mean(quad_ang[3])
   quad_avg[4] = np.mean(quad_ang[4])

   #print("MERGED STARS:", len(merged_stars))

   for star in merged_stars:
      good = 1
      (cal_file,ra_center,dec_center,position_angle,dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy, img_res) = star
      #print("ANG: ", new_cat_x,new_cat_y,six,siy)
      angle = find_angle((new_cat_x, new_cat_y), (six,siy)) 
      quad = star_quad(six,siy)
      avg_ang = quad_avg[quad]
      if match_dist > 5:
         ang_diff = abs(angle - avg_ang)
         if ang_diff > 20:
            #print("   ", dcname,quad,match_dist, angle,avg_ang, ang_diff)
            good = 0
      if good == 1:
         new_merged_stars.append(star) 


   return(new_merged_stars)


def clone_cal_params(cal_params_file, child_file,json_conf):
   fn = child_file.split("/")[-1]
   el = fn.split("-")
   fn = el[0]
   print("BASE NAME: ", fn)    
   image_file = child_file.replace("-calparams.json", "-stacked.png")
   (f_datetime, cam_id, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(image_file)

   meteor_json_file = image_file.replace("-stacked.png", "-reduced.json")
   meteor_json = load_json_file(meteor_json_file)
   hd_video_file = meteor_json['hd_video_file']
   hd_stack_file = hd_video_file.replace(".mp4", "-stacked.png")

   if cfe(hd_stack_file) == 0:
      print("HD FILE NOT FOUND!")
      hd_stack_file = meteor_json_file.replace(".json", "-stacked.png")
   hd_star_img = cv2.imread(hd_stack_file, 0)

   masks = get_masks(cam_id, json_conf,1)
   hd_star_img = mask_frame(hd_star_img, [], masks)

   img = hd_star_img
   image_file = hd_stack_file
   print("HD STACK FILE", image_file)

   cal_dir = "/mnt/ams2/cal/freecal/" + fn + "/"
   if cfe(cal_dir, 1) == 0:
      os.system("mkdir " + cal_dir) 
   new_cal_file = cal_dir + fn + "-calparams.json"

   print("CLONE CP: ", cal_params_file)    
   cal_params = load_json_file(cal_params_file)
   new_cal_params = cal_params
   center_az = cal_params['center_az']
   center_el = cal_params['center_el']
   print(image_file)
   rah,dech = AzEltoRADec(center_az,center_el,image_file,cal_params,json_conf)
   rah = str(rah).replace(":", " ")
   dech = str(dech).replace(":", " ")
   ra_center,dec_center = HMS2deg(str(rah),str(dech))
   new_cal_params['ra_center'] = ra_center
   new_cal_params['dec_center'] = dec_center

   close_stars = []
   #cat_image_stars, img = get_image_stars_from_catalog(image_file,json_conf,cal_params_file, masks, show = 0)

   cat_image_stars, img, no_match, res_err, match_per,cp_data = get_stars_from_image(image_file,json_conf, masks , cal_params, show = 0)

   for name,mag,ra,dec,new_cat_x,new_cat_y,ix,iy,px_dist,cal_params_file in cat_image_stars:
      close_stars.append(( name,mag,ra,dec,0,0,px_dist,new_cat_x,new_cat_y,0,0,new_cat_x,new_cat_y,ix,iy,px_dist))

   print("AZ/EL/RA/DEC:", center_az, center_el, ra_center, dec_center, len(close_stars))


   new_cal_params['close_stars']  = close_stars 
   print("SAVING CLONE:", new_cal_file)
   save_json_file(new_cal_file, new_cal_params)
   return(new_cal_params, new_cal_file)


def minimize_fov_pos(meteor_json_file, image_file, json_conf, cal_params = None, show=0 ):
   debug = open("debug.txt", "w")
   if cal_params is None:
      cal_params = load_json_file(cal_params_file)
   #if "fov_fit" in cal_params:
   #   if cal_params['fov_fit'] == 1:
   #      print("Skip already done the best we could do.")
         #return(0,0)
   cal_params['device_lat'] = json_conf['site']['device_lat']
   cal_params['device_lng'] = json_conf['site']['device_lng']
   cal_params['device_alt'] = json_conf['site']['device_alt']
   cal_params['orig_ra_center'] = cal_params['ra_center']
   cal_params['orig_dec_center'] = cal_params['dec_center']

   cal_params['orig_az_center'] = cal_params['center_az']
   cal_params['orig_el_center'] = cal_params['center_el']
   cal_params['orig_pos_ang'] = cal_params['position_angle']
   cal_params['orig_pixscale'] = cal_params['pixscale']

   close_stars = cal_params['cat_image_stars'] 

   #print("BEFORE:", len(close_stars))

   close_stars = remove_dupe_cat_stars(close_stars)
   cal_params['close_stars'] = close_stars
   paired_stars = cal_params['close_stars']
   #print("AFTER:", len(close_stars))
   org_az = cal_params['center_az']
   org_el = cal_params['center_el']
   org_pos = cal_params['position_angle']
   
   (f_datetime, cam_id, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(image_file)
   masks = get_masks(cam_id, json_conf,1)

   
   this_poly = np.zeros(shape=(4,), dtype=np.float64)
   #this_poly[0] = 0 
   #this_poly[1] = 0
   #this_poly[2] = 0

   if type(meteor_json_file) is str:
      meteor_json_file = meteor_json_file.replace(".json", "-reduced.json")
      meteor_json = load_json_file(meteor_json_file)
      hd_video_file = meteor_json['hd_video_file']
      hd_stack_file = hd_video_file.replace(".mp4", "-stacked.png")
   else: 
      meteor_json = cal_params 
      image_file = image_file.replace("-calparams", "")
      meteor_json_file = image_file.replace("-stacked.png", "-calparams.json")
      print("MIKE MJF(calfile):", meteor_json_file)
      hd_stack_file = image_file
      hd_stack_file = hd_stack_file.replace("-stacked-stacked", "-stacked")
   if cfe(hd_stack_file) == 0:
      print("HD FILE NOT FOUND!", hd_stack_file)
      hd_stack_file = meteor_json_file.replace(".json", "-stacked.png")
   hd_star_img = cv2.imread(hd_stack_file, 0)
   img = hd_star_img
   image_file = hd_stack_file

   
   img = cv2.imread(image_file,0)
   oimg = img.copy()
   img = cv2.resize(img, (1920,1080))
   oimg = mask_frame(oimg, [], masks)
   img = mask_frame(img, [], masks)

  
   if show == 1:
      cv2.namedWindow('pepe')
      cv2.imshow('pepe', img)
      cv2.waitKey(1) 

   res = reduce_fov_pos(this_poly, cal_params,image_file,oimg,json_conf, paired_stars,0,show)

   total_dist = 0

   for data in paired_stars:
      iname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,old_cat_x,old_cat_y,six,siy,cat_dist  = data
      new_x = int(new_x)  
      new_y = int(new_y)  
      six = int(six)  
      siy = int(siy)  
      cv2.rectangle(img, (new_x-2, new_y-2), (new_x + 2, new_y + 2), (255), 1)
      cv2.line(img, (six,siy), (new_x,new_y), (255), 1)
      cv2.circle(img,(six,siy), 5, (255), 1)
      total_dist = total_dist + match_dist
      cv2.putText(img, iname,  (six,siy), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 1)

   desc = "Initial Res: " + str(res)
   cv2.putText(img, desc,  (20,50), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 1)
   show_img = cv2.resize(img, (960,540))
   if show == 1:
      cv2.imshow('pepe', show_img)
      cv2.waitKey(1) 

 
   print("START RES:", cam_id, res, len(paired_stars))   
   if res < .3: 
      # Res is good No need to recalibrate!
      print("Res is good no need to recal")
      return(0,cal_params)

   res = scipy.optimize.minimize(reduce_fov_pos, this_poly, args=( cal_params,image_file,oimg,json_conf, paired_stars,1,show), method='Nelder-Mead')


   fov_pos_poly = res['x']
   #print("FOV POS POLY:", float(fov_pos_poly[0]), float(fov_pos_poly[1]), float(fov_pos_poly[2]), float(fov_pos_poly[3])) 
   fov_pos_fun = res['fun']

   final_res = reduce_fov_pos(fov_pos_poly, cal_params,image_file,img,json_conf, paired_stars,0,show)

   cal_params['fov_pos_poly'] = fov_pos_poly.tolist()
   cal_params['fov_pos_fun'] = fov_pos_fun

   print("FOV POS POLY:", fov_pos_poly)
   print("EQUATION = " + str(cal_params['position_angle']) + " + " + str(fov_pos_poly[2] ))
   cal_params['center_az'] = float(cal_params['orig_az_center']) + float(fov_pos_poly[0] )
   cal_params['center_el'] = float(cal_params['orig_el_center']) + float(fov_pos_poly[1] )
   cal_params['position_angle'] = float(cal_params['position_angle']) + float(fov_pos_poly[2] )
   cal_params['pixscale'] = float(cal_params['pixscale']) + float(fov_pos_poly[3] )
   print("VALUE IS: ", cal_params['position_angle'])  

   if type(meteor_json_file) is str:
      rah,dech = AzEltoRADec(cal_params['center_az'],cal_params['center_el'],meteor_json_file,cal_params,json_conf)
   else: 
      rah,dech = AzEltoRADec(cal_params['center_az'],cal_params['center_el'],image_file,cal_params,json_conf)
   rah = str(rah).replace(":", " ")
   dech = str(dech).replace(":", " ")
   ra_center,dec_center = HMS2deg(str(rah),str(dech))
   cal_params['ra_center'] = ra_center
   cal_params['dec_center'] = dec_center


   cal_params['fov_fit'] = 1 
   close_stars = []
   cat_image_stars, img = get_image_stars_from_catalog(image_file,json_conf,meteor_json_file, masks, cal_params, show = 0)
   for name,mag,ra,dec,new_cat_x,new_cat_y,ix,iy,px_dist,cal_params_file in cat_image_stars:
      close_stars.append(( name,mag,ra,dec,0,0,px_dist,new_cat_x,new_cat_y,0,0,new_cat_x,new_cat_y,ix,iy,px_dist))

   cal_params['close_stars'] =  close_stars

   #print("ORIG MAZ:", cal_params['orig_az_center'], cal_params['orig_el_center'], cal_params['orig_pos_ang'])
   #print("ORIG RA:", cal_params['orig_ra_center'], cal_params['orig_dec_center'])
   #print("END MAZ:", cal_params['center_az'], cal_params['center_el'], cal_params['position_angle'])
   #print("END RA:", cal_params['ra_center'], cal_params['dec_center'] )

   cal_params['close_stars'] = paired_stars
   #this_poly = np.zeros(shape=(4,), dtype=np.float64)
   #this_poly[0] = 0
   #this_poly[1] = 0
   #this_poly[2] = 0
   #this_poly[3] = 0

   #final_res = reduce_fov_pos(this_poly, cal_params,image_file,oimg,json_conf, paired_stars,0,show)


   print("END RES:", cam_id, final_res, len(paired_stars)) 
   #print("END AZ:", cal_params['center_az']) 
   #print("END EL:", cal_params['center_el'] ) 
   #print("END POS:", cal_params['position_angle']) 
   #print("END PIXSCALE:", cal_params['pixscale']) 


   return(fov_pos_poly,cal_params)


def remove_dupe_cat_stars(paired_stars):
   used = {}
   new_paired_stars = []
   for data in paired_stars:
      iname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,old_cat_x,old_cat_y,six,siy,cat_dist  = data
      used_key = str(six) + "." + str(siy)
      if used_key not in used:
         new_paired_stars.append(data)
         used[used_key] = 1
   return(new_paired_stars)


def reduce_fov_pos(this_poly, in_cal_params, cal_params_file, oimage, json_conf, paired_stars, min_run = 1, show=0):
   image = oimage.copy()
   # cal_params_file should be 'image' filename
   org_az = in_cal_params['center_az'] 
   org_el = in_cal_params['center_el'] 
   org_pixscale = in_cal_params['orig_pixscale'] 
   org_pos_angle = in_cal_params['orig_pos_ang'] 
   new_az = in_cal_params['center_az'] + this_poly[0]
   new_el = in_cal_params['center_el'] + this_poly[1]
   #print("POSITION ANGLE:", in_cal_params['position_angle'], org_az, org_el)
   position_angle = float(in_cal_params['position_angle']) + this_poly[2]
   pixscale = float(in_cal_params['orig_pixscale']) + this_poly[3]



   rah,dech = AzEltoRADec(new_az,new_el,cal_params_file,in_cal_params,json_conf)
   rah = str(rah).replace(":", " ")
   dech = str(dech).replace(":", " ")
   ra_center,dec_center = HMS2deg(str(rah),str(dech))

   in_cal_params['position_angle'] = position_angle
   in_cal_params['ra_center'] = ra_center
   in_cal_params['dec_center'] = dec_center
   in_cal_params['pixscale'] = pixscale 
   in_cal_params['device_lat'] = json_conf['site']['device_lat']
   in_cal_params['device_lng'] = json_conf['site']['device_lng']
   in_cal_params['device_alt'] = json_conf['site']['device_alt']


   fov_poly = 0
   pos_poly = 0
   x_poly = in_cal_params['x_poly']
   y_poly = in_cal_params['y_poly']
   cat_stars = get_catalog_stars(fov_poly, pos_poly, in_cal_params,"x",x_poly,y_poly,min=0)
   new_res = []
   new_paired_stars = []
   used = {}
   org_star_count = len(paired_stars)
   for cat_star in cat_stars:
      (name,mag,ra,dec,new_cat_x,new_cat_y) = cat_star
      dname = name.decode("utf-8")
      for data in paired_stars:
         iname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,old_cat_x,old_cat_y,six,siy,cat_dist  = data
         if dname == iname:
            pdist = calc_dist((six,siy),(new_cat_x,new_cat_y))
            if pdist <= 15:
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
     
   orig_star_count = len(in_cal_params['close_stars'])

   if len(new_paired_stars) > 0:
      avg_res = tres / len(new_paired_stars) 
   else:
      avg_res = 9999999
      res = 9999999

   if orig_star_count > len(new_paired_stars):
      pen = orig_star_count - len(new_paired_stars)
   else:
      pen = 0
 
   avg_res = avg_res + (pen * 10)
   show_res = avg_res - (pen*10) 
   desc = "RES: " + str(show_res) + " " + str(len(new_paired_stars)) + " " + str(orig_star_count) + " PEN:" + str(pen)
   cv2.putText(image, desc,  (10,50), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 1)
   desc2 = "CENTER AZ/EL/POS" + str(new_az) + " " + str(new_el) + " " + str(cal_params['position_angle']) 
   cv2.putText(image, desc2,  (10,80), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 1)

   desc2 = "PX SCALE:" + str(cal_params['pixscale'])
   cv2.putText(image, desc2,  (10,110), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 1)


   #print("AVG RES:", avg_res, len(new_paired_stars), "/", org_star_count, new_az, new_el, ra_center, dec_center, position_angle )
   if show == 1:
      show_img = cv2.resize(image, (960,540))
      cv2.imshow('pepe', show_img)
      if min_run == 1:
         cv2.waitKey(1) 
      else:
         cv2.waitKey(1) 
   in_cal_params['position_angle'] = org_pos_angle
   if min_run == 1:
      return(avg_res)
   else:
      return(show_res)


def minimize_lat_lon(json_conf,cal_params_file,all_paired_stars,show=0,latlon_poly=None):
   cal_params = load_json_file(cal_params_file)
   cal_params['device_lat'] = json_conf['site']['device_lat']
   cal_params['device_lon'] = json_conf['site']['device_lng']
   cal_params['device_alt'] = json_conf['site']['device_alt']
   cal_params['orig_ra_center'] = cal_params['ra_center']
   cal_params['orig_dec_center'] = cal_params['dec_center']
   cal_params['orig_pos_ang'] = cal_params['position_angle']

   org_lat = json_conf['site']['device_lat'] 
   org_lon = json_conf['site']['device_lng'] 
   org_alt = json_conf['site']['device_alt'] 
   org_az = cal_params['center_az'] 
   org_el = cal_params['center_el'] 
   json_conf['site']['org_device_lat']  = org_lat
   json_conf['site']['org_device_lng']  = org_lon
   json_conf['site']['org_device_alt']  = org_alt

   if latlon_poly is None:
      this_poly = np.zeros(shape=(3,), dtype=np.float64)
      this_poly[0] = .1
      this_poly[1] = .1
      this_poly[2] = 1
   else:
      this_poly = latlon_poly


   res = scipy.optimize.minimize(reduce_latlon, this_poly, args=(cal_params,cal_params_file,json_conf, all_paired_stars,show), method='Nelder-Mead')
   latlon_poly = res['x']
   latlon_fun = res['fun']
   cal_params['latlon_poly'] = latlon_poly.tolist()
   cal_params['latlon_fun'] = latlon_fun
   print(latlon_poly)
   print(latlon_fun)
   return(latlon_poly)

def reduce_latlon(this_poly, cal_params, cal_params_file, json_conf, all_paired_stars, show=0):





   all_night_res = []
   for image_file in all_paired_stars:
      paired_stars = all_paired_stars[image_file]
      cal_params_file = paired_stars[0][-1]
      cal_params = load_json_file(cal_params_file)
      cal_params['orig_ra_center'] = cal_params['ra_center']
      cal_params['orig_dec_center'] = cal_params['dec_center']
      (f_datetime, cam_id, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(cal_params_file)
      date = fy + "_" + fm + "_" + fd
      org_cal_date = fy + "/" + fm + "/" + fd + " " + fh + ":" + fmin + ":" + fs
      (f_datetime, cam_id, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(image_file)
      date = fy + "_" + fm + "_" + fd
      new_cal_date = fy + "/" + fm + "/" + fd + " " + fh + ":" + fmin + ":" + fs
      org_lat = json_conf['site']['org_device_lat'] 
      org_lon = json_conf['site']['org_device_lng'] 
      org_alt = json_conf['site']['org_device_alt'] 
      org_az = cal_params['center_az'] 
      org_el = cal_params['center_el'] 

   
      min_mod = 30
      lat = float(org_lat) + float(this_poly[0])
      lon = float(org_lon) + float(this_poly[1])
      alt = float(org_alt) + float(this_poly[2])
      #print("ORG LAT,LON:", org_lat,org_lon)
      #print("NEW LAT,LON:", lat,lon)

      json_conf['site']['device_lat'] = str(lat)
      json_conf['site']['device_lng'] = str(lon)
      json_conf['site']['alt'] = str(alt )

      orig_ra_center = cal_params['orig_ra_center']
      orig_dec_center = cal_params['orig_dec_center']

      #print("REFIND ORG AZ, EL WITH NEW LAT LON", orig_ra_center,orig_dec_center,lat,lon,alt)
      new_az, new_el= radec_to_azel(orig_ra_center,orig_dec_center, org_cal_date,json_conf)
      #print("NEW ORIG AZ/EL:", new_az,new_el)
      # print("AVG RES LATLON AZ,EL:", lat,lon,alt,new_az,new_el)
  
      rah,dech = AzEltoRADec(new_az,new_el,image_file,cal_params,json_conf)
      rah = str(rah).replace(":", " ")
      dech = str(dech).replace(":", " ")

      #rahh = RAdeg2HMS(rah)
      ra_center,dec_center = HMS2deg(str(rah),str(dech))


      cal_params['ra_center'] = ra_center
      cal_params['dec_center'] = dec_center

      fov_poly = cal_params['fov_poly']
      pos_poly = cal_params['pos_poly']
      x_poly = cal_params['x_poly']
      y_poly = cal_params['y_poly']
      cat_stars = get_catalog_stars(fov_poly, pos_poly, cal_params,"x",x_poly,y_poly,min=0)

      new_res = []
      new_paired_stars = []
      used = {}
      for cat_star in cat_stars:
         (name,mag,ra,dec,new_cat_x,new_cat_y) = cat_star
         dname = name.decode("utf-8")
         for iname,imag,ira,idec,inew_cat_x,inew_cat_y,ix,iy,ipx_dist,cp_file in paired_stars:
            pdist = calc_dist((ix,iy),(new_cat_x,new_cat_y))
            if pdist <= 15:
               new_res.append(pdist)
               used_key = str(ix) + "." + str(iy)
               if used_key not in used: 
                  new_paired_stars.append((iname,imag,ira,idec,inew_cat_x,inew_cat_y,ix,iy,ipx_dist))
               used[used_key] = 1



      tres = np.sum(new_res)
      missing = len(paired_stars) - len(new_paired_stars)
      extra_bad = missing * 1
      avg_res = (tres / len(new_paired_stars)) + missing
      all_night_res.append(avg_res)

   all_night_avg_res  = np.sum(all_night_res) / len(all_night_res)
   print("ALL NIGHT AVG RES:", all_night_avg_res)
   return(all_night_avg_res)

def get_sd_files(day,cam_id,json_conf):
   base_dir = json_conf['site']['proc_dir'] + "/" + day + "/images/*" + cam_id +  "*.png"
   sd_files = []
   all_files = sorted(glob.glob(base_dir))
   for file in all_files:
      if "-tn" not in file and "-night-stack" not in file and "-hd-stack" not in file:
         sd_files.append(file)

   return(sd_files)

def track_stars (day,json_conf,scmd='',cal_params_file=None,show=0):
   if show == 1:
      cv2.namedWindow('pepe')
   min_mod = 60

   # for each cam! 
   cameras = json_conf['cameras']
   cam_ids = []
   for camera in cameras:
      cam_ids.append((cameras[camera]['cams_id']))

   all_i_files = {}
   for cam_id in cam_ids:
      masks = get_masks(cam_id, json_conf,1)
      sd_files = get_sd_files(day,cam_id,json_conf)
      #print("SD FILES:", len(sd_files))
      if len(sd_files) == 0:
         continue
      poss = get_active_cal_file(sd_files[4])
      cal_params_file = poss[0][0]

      #print("CAL FILE:", cal_params_file) 
      fc = 0
      res_night = 0
      tres = 0
      latlon_poly = np.zeros(shape=(3,), dtype=np.float64)
      ufc = 1
      for file in sd_files:
         if fc % min_mod == 0:
            if cal_params_file is None:
               stars = get_image_stars(file,show) 
            else:
    
               #print("INFO:", file, cal_params_file)
               stars,img = get_image_stars_from_catalog(file,json_conf,cal_params_file, masks, show)
               tres = 0
               #print("STARS:", len(stars))
               if len(stars) > 0:
                  for star in stars:
                     tres = float(tres) + float(star[-2])
                  tres_avg = tres / len(stars)
                  res_night = res_night + tres_avg
                  if ufc > 0:
                     res_night_avg =res_night / ufc
                  else:
                     res_night_avg = res_night
                  #print(len(stars) , "STARS:", "RES:", tres_avg, res_night_avg)
                  all_i_files[file] = stars
               else:
                  res_night_avg = 999
             

               simg = cv2.resize(img, (960,540))
               desc = str(res_night_avg)
               cv2.putText(simg, desc,  (480,270), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
               if show == 1:
                  cv2.imshow('pepe', simg)
                  cv2.waitKey(1)
            ufc = ufc + 1
         fc = fc + 1
      res_night = 1
   
   star_track_file = "/mnt/ams2/cal/autocal/startrack/" + day + "-startrack.json"
   save_json_file(star_track_file, all_i_files)




   if scmd == 'latlon':
      orig_lat = json_conf['site']['device_lat']
      orig_lon = json_conf['site']['device_lng']
      orig_alt = json_conf['site']['device_alt']

      latlon_poly = minimize_lat_lon(json_conf,cal_params_file,all_i_files,show,latlon_poly)

      print("FINAL LAT LON POLY")
      print("------------------")
      print("Lat Poly: ", latlon_poly[0])
      print("Lon Poly: ", latlon_poly[1])
      print("Alt Poly: ", latlon_poly[2])
      new_lat = float(json_conf['site']['device_lat']) + float(latlon_poly[0])
      new_lon = float(json_conf['site']['device_lng']) + float(latlon_poly[1])
      new_alt = float(json_conf['site']['device_alt']) + float(latlon_poly[2])
      print("Orig Lat,Lon:", orig_lat,orig_lon,orig_alt)
      print("JSON Lat,Lon:", json_conf['site']['device_lat'], json_conf['site']['device_lng'])
      print("Orig Alt:", json_conf['site']['device_alt'])
      print("New Lat,Lon:", new_lat,new_lon)
      print("New Alt:", new_alt)

   return(all_i_files) 

def flatten_all_stars(all_stars, json_conf):
   cameras = json_conf['cameras']
   cam_ids = []
   multi_merge = {}
   cp_files = {}
   for camera in cameras:
      multi_merge[cameras[camera]['cams_id']]  = {}
      cp_files[cameras[camera]['cams_id']]  = ""

   for file in all_stars:
      print(file, len(all_stars))
      (f_datetime, cam_id, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(file)
      multi_merge[cam_id][file] = []
      for star in all_stars[file]:
         name,mag,ra,dec,new_cat_x,new_cat_y,ix,iy,px_dist,cal_params_file = star
         (f_datetime, cam_id, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(cal_params_file)
         cal_params = load_json_file(cal_params_file)
         cp_files[cam_id] = cal_params_file
         img_ra = ra
         img_dec = dec
         match_dist = px_dist
         ra_center = cal_params['ra_center']
         dec_center = cal_params['dec_center']
         img_az = cal_params['center_az']
         img_el = cal_params['center_el']
         img_res = px_dist
         # find new ra/dec center
         rah,dech = AzEltoRADec(img_az,img_el,file,cal_params,json_conf)
         rah = str(rah).replace(":", " ")
         dech = str(dech).replace(":", " ")
         ra_center,dec_center = HMS2deg(str(rah),str(dech))
         #print("CENTER AZ/EL", img_az, img_el, ra_center, dec_center)

         if match_dist < 5:
            multi_merge[cam_id][file].append((cal_params_file,ra_center,dec_center,name,mag,ra,dec,img_ra,img_dec,match_dist,new_cat_x,new_cat_y,img_az,img_el,new_cat_x,new_cat_y,ix,iy, img_res))
   return(multi_merge) 

def hd_cal(all_i_files, json_conf, day, show = 0):
   print("HD CAL")
   hd_day_dir = "/mnt/ams2/cal/autocal/hdimages/" + day + "/"
   if cfe(hd_day_dir, 1) == 0: 
      os.system("mkdir " + hd_day_dir)

   good_hd_stacks = []

   all_new_i_files = {}

   for file in all_i_files:
      hd_stack_file = file.replace("-stacked.png", "-hd-stacked.png")
      total_stars = len(all_i_files[file])
      if cfe(hd_stack_file) == 0:
         print(file, total_stars)
         hd_file, hd_trim,time_diff_sec, dur = find_hd_file_new(file, 0, 10, 0)
         print("LOADING:", hd_file)
         if hd_file is not None and total_stars > 10:
            frames = load_video_frames(hd_file, json_conf, 150,0,[],1)
            print(len(frames)) 
            stack_file, stack_img = stack_frames(frames, hd_file, 1)
            exit() 
         #print(stack_file, stack_img.shape) 
            cv2.imwrite(hd_stack_file, stack_img)
            good_hd_stacks.append(hd_stack_file)
 
         #print(file, hd_file, hd_trim,time_diff_sec,dur)
      else:
         print("HD FILE ALREADY DONE:", hd_stack_file, total_stars)
         if total_stars > 10:
            good_hd_stacks.append(hd_stack_file)

   for hd_stack_file in good_hd_stacks:
      (f_datetime, cam_id, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(file)
      masks = get_masks(cam_id, json_conf,0)

      hd_stack_img = cv2.imread(hd_stack_file,0)
      hd_stack_img = mask_frame(hd_stack_img, [], masks)
      print("HD:", hd_stack_file)

      poss = get_active_cal_file(hd_stack_file)
      cal_params_file = poss[0][0]
      masks = []

      cat_image_stars,img = get_image_stars_from_catalog(hd_stack_file,json_conf,cal_params_file, masks, show)

      all_new_i_files[hd_stack_file] = cat_image_stars
   #flat_stars = flatten_all_stars(all_i_files, json_conf)
   for file in all_new_i_files:
      hd_stack_img = cv2.imread(file,0)
      print("HD FILE:", file)
      file_stars = all_new_i_files[file]
      for file_star in file_stars:
         (name,mag,ra,dec,new_cat_x,new_cat_y,ix,iy,px_dist,cal_params_file) = file_star
         #(cal_params_file,ra_center,dec_center,name,mag,ra,dec,img_ra,img_dec,match_dist,new_cat_x,new_cat_y,img_az,img_el,new_cat_x,new_cat_y,ix,iy, img_res) = file_star
         #if px_dist < 10:
         #   cv2.rectangle(hd_stack_img, (new_cat_x-2, new_cat_y-2), (new_cat_x + 2, new_cat_y + 2), (128, 128, 128), 1)
         #   cv2.line(hd_stack_img, (ix,iy), (new_cat_x,new_cat_y), (255), 2)
         #   cv2.circle(hd_stack_img,(ix,iy), 5, (128,128,128), 1)

      plate_img, user_stars = make_plate_image(hd_stack_img, file_stars)
      plate_img_file = file.replace(".png", ".jpg")
      cv2.imwrite(plate_img_file, plate_img)
     
      el = plate_img_file.split("/")
      day_dir = el[-3] 
      fn = el[-1] 
      hd_day_dir = "/mnt/ams2/cal/autocal/hdimages/" + day_dir + "/"
      new_plate_img_file = hd_day_dir + fn
      solved_file = new_plate_img_file.replace(".jpg", ".solved")
      failed_file = new_plate_img_file.replace(".jpg", ".failed")

      user_star_file = new_plate_img_file.replace(".jpg", "-user-stars.json")
      json_user_stars = {}
      json_user_stars['user_stars'] = user_stars
      save_json_file(user_star_file, json_user_stars)

      if cfe(failed_file) == 0 and cfe(solved_file) == 0:
         if cfe(hd_day_dir, 1) == 0: 
            os.system("mkdir " + hd_day_dir)
         os.system("cp " + plate_img_file + " " + hd_day_dir)
         os.system("cp " + file + " " + hd_day_dir)

         os.system("./plateSolve.py " + new_plate_img_file)
      else: 
         print("SKIP: Astrometry solver already run on file:", solved_file, failed_file)
   
     

      if show == 1:
         show_img = cv2.resize(plate_img, (960,540))
         cv2.imshow('pepe', show_img)
         cv2.waitKey(1) 

   master_cal_params = avg_cal_files(hd_day_dir,json_conf)
   master_cal_params_file = hd_day_dir + day_dir + "-master_cal_params.json"
   all_star_file = hd_day_dir + day_dir + "-allstars.json"
   save_json_file(all_star_file, all_new_i_files)
   save_json_file(master_cal_params_file, master_cal_params)
   print(master_cal_params_file)
   print(all_star_file)

   #multi_merge(all_i_files,master_cal_params,json_conf)

   #multifit?

def avg_cal_files(cal_dir,json_conf):
   cameras = json_conf['cameras']
   cam_ids = []
   multi_merge = {}
   cp_files = {}
   master_cal_params = {}
   for camera in cameras:
      cam_id = cameras[camera]['cams_id']
      master_cal_params[cam_id] = {}
      glob_dir = cal_dir + "/*" + cam_id + "*-calparams.json"
      cp_files = glob.glob(glob_dir)
      m_az, m_el, m_px, m_pa = avg_cal_files_cam(cp_files)
      master_cal_params[cam_id]['center_az'] = float(m_az)
      master_cal_params[cam_id]['center_el'] = float(m_el)
      master_cal_params[cam_id]['pixscale'] = float(m_px)
      master_cal_params[cam_id]['position_angle'] = float(m_pa)
      master_cal_params[cam_id]['imagew'] = 1920
      master_cal_params[cam_id]['imageh'] = 1080
   return(master_cal_params)



def avg_cal_files_cam(cp_files):
   azs = []
   els = []
   pxs = []
   pas = []
   for cal_param_file in cp_files:
      print(cal_param_file)
      cal_params = load_json_file(cal_param_file)
      center_az = cal_params['center_az']
      center_el = cal_params['center_el']
      pixscale = cal_params['pixscale']
      position_angle = cal_params['position_angle']
      azs.append(center_az)
      els.append(center_el)
      pxs.append(pixscale)
      pas.append(position_angle)
   m_az = float(np.median(np.array(azs).astype(np.float)))
   m_el = float(np.median(np.array(els).astype(np.float)))
   m_px = float(np.median(np.array(pxs).astype(np.float)))
   m_pa = float(np.median(np.array(pas).astype(np.float)))

   for cal_param_file in cp_files:
      print(cal_param_file)
      cal_params = load_json_file(cal_param_file)
      center_az = cal_params['center_az']
      center_el = cal_params['center_el']
      pixscale = cal_params['pixscale']
      position_angle = cal_params['position_angle']
      cal_params['orig_center_az'] = center_az
      cal_params['orig_center_el'] = center_el
      cal_params['orig_pixscale'] = pixscale 
      cal_params['orig_position_angle'] = position_angle
      cal_params['center_az'] = m_az 
      cal_params['center_el'] = m_el 
      cal_params['pixscale'] = m_px 
      cal_params['position_angle'] = m_pa 



   return(m_az,m_el,m_px,m_pa) 
   

def make_plate_image(image, file_stars): 
   ih, iw = image.shape
   for file_star in file_stars:
      (name,mag,ra,dec,new_cat_x,new_cat_y,ix,iy,px_dist,cal_params_file) = file_star

   plate_image = np.zeros((ih,iw),dtype=np.uint8)
   hd_stack_img = image
   hd_stack_img_an = hd_stack_img.copy()
   star_points = []
   for file_star in file_stars:
      (name,mag,ra,dec,new_cat_x,new_cat_y,ix,iy,px_dist,cal_params_file) = file_star
         
      x,y = int(ix),int(iy)
      #cv2.circle(hd_stack_img_an, (int(x),int(y)), 5, (128,128,128), 1)
      y1 = y - 15
      y2 = y + 15
      x1 = x - 15
      x2 = x + 15
      x1,y1,x2,y2= bound_cnt(x,y,iw,ih,15)
      cnt_img = hd_stack_img[y1:y2,x1:x2]
      ch,cw = cnt_img.shape
      max_pnt,max_val,min_val = cnt_max_px(cnt_img)
      mx,my = max_pnt
      mx = mx - 15
      my = my - 15
      cy1 = y + my - 15
      cy2 = y + my +15
      cx1 = x + mx -15
      cx2 = x + mx +15
      cx1,cy1,cx2,cy2= bound_cnt(x+mx,y+my,iw,ih)
      if ch > 0 and cw > 0:
         cnt_img = hd_stack_img[cy1:cy2,cx1:cx2]
         bgavg = np.mean(cnt_img)
         cnt_img = clean_star_bg(cnt_img, bgavg + 3)

         cv2.rectangle(hd_stack_img_an, (x+mx-5-15, y+my-5-15), (x+mx+5-15, y+my+5-15), (128, 128, 128), 1)
         cv2.rectangle(hd_stack_img_an, (x+mx-15-15, y+my-15-15), (x+mx+15-15, y+my+15-15), (128, 128, 128), 1)
         star_points.append([x+mx,y+my])
         plate_image[cy1:cy2,cx1:cx2] = cnt_img

   points_json = {}
   points_json['user_stars'] = star_points

   return(plate_image,star_points)

def test_star(cnt_img, max_loc ):
   max_x, max_y = max_loc
   ch, cw = cnt_img.shape
   avg_px = np.mean(cnt_img)
   #print("TEST STAR:", max_x, max_y)
   star_points = {}
   five_point_flux = 0

   if max_x + 1 < cw and max_y + 1 < ch and max_x - 1 > 0 and max_y - 1 > 0:
      # main center point
      #key = str(max_x) + "." + str(max_y)
      #val = cnt_img[max_y,max_x]
      #star_points[key] = val

      # directly above center
      key = str(max_x+1) + "." + str(max_y)
      val = cnt_img[max_y,max_x+1]
      star_points[key] = val

      # directly below center
      key = str(max_x-1) + "." + str(max_y)
      val = cnt_img[max_y,max_x-1]
      star_points[key] = val

      # directly left of center
      key = str(max_x) + "." + str(max_y-1)
      val = cnt_img[max_y-1,max_x]
      star_points[key] = val

      # directly right of center
      key = str(max_x) + "." + str(max_y+1)
      val = cnt_img[max_y+1,max_x]
      star_points[key] = val

      for key in star_points:
         px_diff = star_points[key] - avg_px
         #print("STAR POINTS:", key, avg_px, star_points[key], px_diff)
         five_point_flux = five_point_flux + px_diff
   return(five_point_flux)

def find_star_in_crop(cnt_img):
   mx = 0
   my = 0

   cnth,cntw = cnt_img.shape
   max_px = np.max(cnt_img)
   avg_px = np.mean(cnt_img)
   px_diff = max_px - avg_px
   min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(cnt_img)
   five_point_flux = test_star(cnt_img, max_loc)
   if five_point_flux < 60:
      return(0, 0,0,(0,0))
   #else:
   #   print("FLUX:", five_point_flux)
 

   thresh = int(max_px - (px_diff / 2))
   _, threshold = cv2.threshold(cnt_img.copy(), thresh, 255, cv2.THRESH_BINARY)

   #thresh_obj = cv2.dilate(threshold.copy(), None , iterations=4)
   cnt_res = cv2.findContours(threshold.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

   if len(cnt_res) == 3:
      (_, cnts, xx) = cnt_res
   elif len(cnt_res) == 2:
      (cnts, xx) = cnt_res
   if len(cnts) > 0:
      for (i,c) in enumerate(cnts):
         x,y,w,h = cv2.boundingRect(cnts[i])

      mx = int(x + (w / 2))
      my = int(y + (h / 2))

   ch,cw = cnt_img.shape
   if ch != cw:
      return(0, 0,0,(0,0))

   
   zx1 = []
   zx2 = []
   zy1 = []
   zy2 = []

   pxr = 3
   if max_px > 100:
      pxr = 5
   if max_px > 200:
      pxr = 6
   if max_px > 250:
      pxr = 9

   if px_diff > 5:
      for i in range (0,pxr):
         if mx + i < cw - 1:
            px_val = int(cnt_img[my,mx+i])
            zx1.append(px_val)
      for i in range (0,7):
         if mx - i >= 0:
            px_val = int(cnt_img[my,mx-i])
            zx2.append(px_val)
      for i in range (0,7):
         if my + i < ch - 1:
            px_val = int(cnt_img[my+i,mx])
            zy1.append(px_val)
      for i in range (0,7):
         if my - i >= 0:
            px_val = int(cnt_img[my-i,mx])
            zy2.append(px_val)

   if len(zx1) > 2 and len(zx2) > 2 and len(zy1) > 2 and len(zy2) > 2:
      sx1 = zx1[0] - zx1[-1]
      sx2 = zx2[0] - zx2[-1]

      sy1 = zy1[0] - zy1[-1]
      sy2 = zy2[0] - zy2[-1]
      # check total flux in each direction is high enough 

      # check shape is consistent each way
      shape_score = abs((sx1-sx2) - (sy1-sy2))
      brightness_score = sx1 + sx2 + sy1 + sy2

      #print("SCORE:", max_px, brightness_score, shape_score)
      #if max_px < 80:
      #   return(0, 0,0,(0,0))
      if brightness_score < 30:
         return(0, 0,0,(0,0))

      #if sx1 + sx2 + sy1 + sy2 < 30:
      #   return(0, 0,0,(0,0))
      ##if shape_score > 20 :
      #   return(0, 0,0,(0,0))


   else:
      return(0, 0,0,(0,0))

   return(max_px, avg_px,px_diff,(mx,my))

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

   #x_poly = np.zeros(shape=(15,), dtype=np.float64)
   #y_poly = np.zeros(shape=(15,), dtype=np.float64)
   #cal_params['x_poly'] = x_poly.tolist()
   #cal_params['y_poly'] = y_poly.tolist()

   cat_stars = get_catalog_stars(fov_poly, pos_poly, cal_params,"x",x_poly,y_poly,min=0)


   return(cat_stars)

def lookup_star_in_cat(ix,iy,cat_stars,star_dist=10):
   close = []
   for cat_star in cat_stars:
      name,mag,ra,dec,new_cat_x,new_cat_y = cat_star
      px_dist = calc_dist((ix,iy),(new_cat_x,new_cat_y))
      close.append((ix,iy,px_dist,name,mag,ra,dec,new_cat_x,new_cat_y)) 
   temp = sorted(close, key=lambda x: x[2], reverse=False)
   closest = temp[0]
   if closest[2] < star_dist:
      return(1, closest)
   else:
      return(0, closest)

def get_stars_from_image(file,json_conf,masks = [], cal_params = None, show = 0):
   user_stars = None
   if show == 1:
      cv2.namedWindow('pepe')
   print("FILE:",file)
   file = file.replace("-stacked-stacked", "-stacked")
   img = cv2.imread(file,0)
   img = cv2.resize(img, (1920,1080))
   mimg = mask_frame(img, [], masks)
   img = mimg.copy()
   (f_datetime, cam_id, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(file)

   if cal_params is None:
      poss = get_active_cal_file(file)
      cal_params_file = poss[0][0]
      cal_params = load_json_file(cal_params_file)
   else:
      cal_params_file = None

   if "user_stars" in cal_params:
      user_stars = cal_params['user_stars']
      img_stars = user_stars
   
   if "center_az" not in cal_params:
      print("NO CENTER AZ!")
      exit()
      poss = get_active_cal_file(file)
      cal_params_file = poss[0][0]
      temp = load_json_file(cal_params_file)
      cal_params['pixscale'] = temp['pixscale']
      cal_params['imagew'] = temp['imagew']
      cal_params['imageh'] = temp['imageh']
      cal_params['center_az'] = temp['center_az']
      cal_params['center_el'] = temp['center_el']
      cal_params['position_angle'] = temp['position_angle']
      cal_params['x_poly'] = temp['x_poly']
      cal_params['y_poly'] = temp['y_poly']
      cal_params['x_poly_fwd'] = temp['x_poly_fwd']
      cal_params['y_poly_fwd'] = temp['y_poly_fwd']
   

   cp_data = cal_params


   cat_stars = get_cat_stars(file,file,json_conf,cal_params)

   gsize = 25 

   wc = 0
   hc = 0
   if user_stars is None:
      img_stars = []
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
            crop_area = img[y1:y2,x1:x2]
            min_val, max_val, min_loc, (mx,my) = cv2.minMaxLoc(crop_area)
            mx1 = mx + w - 15
            mx2 = mx + w + 15
            my1 = my + h - 15
            my2 = my + h + 15
            if mx1 < 0:
               mx1 = 0 
            if mx2 > 1920:
               mx2 = 1920
            if my1 < 0:
               my1 = 0 
            if my2 > 1080:
               my2 = 1080 
            cnt_img = img[my1:my2,mx1:mx2]

            (max_px, avg_px,px_diff,(mx,my)) = find_star_in_crop(cnt_img)
            if px_diff > 10:
               ix = mx1 + mx
               iy = my1 + my
               img_stars.append((ix,iy))
         hc = hc + 1
      wc = wc + 1

   total_res = 0
   tstars = 0
   img_stars = remove_dupe_img_stars(img_stars)
   cat_img_stars = []
   no_match_stars = []
   star_dist = 20

   tstars = 0
   for star in img_stars:
      ix, iy = star
      status, star_info = lookup_star_in_cat(ix,iy,cat_stars,star_dist)
      if status == 1:
         (ix,iy,px_dist,iname,mag,ra,dec,new_cat_x,new_cat_y) = star_info
         iname = iname.decode("utf-8")
         new_cat_x,new_cat_y = int(new_cat_x), int(new_cat_y)
         total_res = total_res + px_dist
         tstars = tstars + 1 
         cat_img_stars.append((iname,mag,ra,dec,new_cat_x,new_cat_y,ix,iy,px_dist,cal_params_file))
      else:
         no_match_stars.append(star)
         (ix,iy,px_dist,iname,mag,ra,dec,new_cat_x,new_cat_y) = star_info
         new_cat_x,new_cat_y = int(new_cat_x), int(new_cat_y)

   # compute std dev distance
   tot_res = 0
   close_stars = []
   dist_list = []
   for name,mag,ra,dec,new_cat_x,new_cat_y,ix,iy,px_dist,cp_file in cat_img_stars:
      px_dist = calc_dist((ix,iy),(new_cat_x,new_cat_y))
      dist_list.append(px_dist)
   std_dev_dist = np.std(dist_list)
   std_dev_dist = std_dev_dist * 3
   desc = "STD DEV DIST:" + str(std_dev_dist)
   tot_res = 0
   close_stars = []
   if std_dev_dist < 5:
      std_dev_dist = 5 

  
   for name,mag,ra,dec,new_cat_x,new_cat_y,ix,iy,px_dist,cp_file in cat_img_stars:
      px_dist = calc_dist((ix,iy),(new_cat_x,new_cat_y))
      if px_dist <= std_dev_dist:
         new_cat_x,new_cat_y = int(new_cat_x), int(new_cat_y)
         if show == 1:
            cv2.circle(img,(ix,iy), 5, (128,128,128), 1)
            iname = name 
            cv2.putText(img, iname,  (ix,iy), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
            cv2.rectangle(img, (new_cat_x-5, new_cat_y-5), (new_cat_x+5, new_cat_y+5), (128, 128, 128), 1)
         close_stars.append((name,mag,ra,dec,new_cat_x,new_cat_y,ix,iy,px_dist,cp_file))
         tot_res = tot_res + px_dist
      else:
         no_match_stars.append((name,mag,ra,dec,new_cat_x,new_cat_y,ix,iy,px_dist,cp_file))
         cv2.circle(img,(ix,iy), 10, (128,128,128), 1)
         cv2.rectangle(img, (new_cat_x-10, new_cat_y-10), (new_cat_x+10, new_cat_y+10), (128, 128, 128), 1)
   
   tstars = len(close_stars)
   if tstars > 0:
      avg_res = tot_res / tstars
   else:
      avg_res = 9999

   nmt = len(no_match_stars)
   mt = len(close_stars)
   tt = nmt + mt
   match_per = mt / tt
   if show == 1:
      desc = "Match %: " + str(match_per)[0:4]
      cv2.putText(img, desc,  (10,90), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)

      desc = "Stars:" + str(tstars)[0:4]
      cv2.putText(img, desc,  (10,120), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)

      desc = "Res Err:" + str(avg_res)[0:4]
      cv2.putText(img, desc,  (10,150), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
   

   if show == 1:    
      show_img = cv2.resize(img, (0,0),fx=.5, fy=.5)
      cv2.imshow('pepe', show_img)
      cv2.waitKey(0) 
   #cp_data['cat_img_stars'] = close_stars 
   cal_params['cat_image_stars'] = close_stars 
   return(close_stars, img, no_match_stars, avg_res,match_per, cal_params)
   
def remove_dupe_img_stars(img_stars):
   index = {}
   new_list = []
   for x,y in img_stars:
      key = str(x) + ":" + str(y)
      if key not in index:
         new_list.append((x,y))
         index[key] = 1
      #else:
         #print("DUPE:",x,y)
   return(new_list)

def get_image_stars_from_catalog(file,json_conf,cal_params_file, masks = [], cal_params = None, show = 0):
   img = cv2.imread(file,0)
   img = cv2.resize(img, (1920,1080))
   img = mask_frame(img, [], masks)
   if cal_params is None: 
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
   #print("AZ CONVERT! ", file )
   rah,dech = AzEltoRADec(center_az,center_el,file,cal_params,json_conf)
   rah = str(rah).replace(":", " ")
   dech = str(dech).replace(":", " ")
   
   #rahh = RAdeg2HMS(rah)
   ra_center,dec_center = HMS2deg(str(rah),str(dech))


   #print("GET IMAGE STARS FROM CATALOG: ", center_az, center_el, ra_center, dec_center, file,cal_params_file)
   cal_params['ra_center'] = ra_center
   cal_params['dec_center'] = dec_center

   fov_poly = 0 
   pos_poly = 0 
   x_poly = cal_params['x_poly']
   y_poly = cal_params['y_poly']
   #print("GET CAT STARS:", ra_center, dec_center)
   cat_stars = get_catalog_stars(fov_poly, pos_poly, cal_params,"x",x_poly,y_poly,min=0)
   #cat_stars = cat_stars[0:50]

   cat_image_stars = []
   for cat_star in cat_stars:
      (name,mag,ra,dec,new_cat_x,new_cat_y) = cat_star
      name = name.decode("utf-8")
      new_cat_x = int(new_cat_x)
      new_cat_y = int(new_cat_y)
      ix,iy = find_img_point_from_cat_star(new_cat_x,new_cat_y,img)
      if ix != 0 and iy != 0: 
         px_dist = calc_dist((ix,iy),(new_cat_x,new_cat_y))
         if px_dist < 10:
            cat_image_stars.append((name,mag,ra,dec,new_cat_x,new_cat_y,ix,iy,px_dist,cal_params_file))


   # compute std dev distance
   tot_res = 0
   close_stars = []
   dist_list = []
   for name,mag,ra,dec,new_cat_x,new_cat_y,ix,iy,px_dist,cp_file in cat_image_stars:
      px_dist = calc_dist((ix,iy),(new_cat_x,new_cat_y))
      dist_list.append(px_dist)
   std_dev_dist = np.std(dist_list)
   desc = "STD DEV DIST:" + str(std_dev_dist)
   tot_res = 0
   close_stars = []
   
   cv2.putText(img, desc ,  (300,300), cv2.FONT_HERSHEY_SIMPLEX, .5, (255, 255, 255), 1)

   tot_res = 0
   for pstar in cat_image_stars:
      (name,mag,ra,dec,new_cat_x,new_cat_y,ix,iy,px_dist,cp_file) = pstar
      if px_dist <= std_dev_dist:
         cv2.rectangle(img, (new_cat_x-2, new_cat_y-2), (new_cat_x + 2, new_cat_y + 2), (128, 128, 128), 1)
         cv2.line(img, (ix,iy), (new_cat_x,new_cat_y), (255), 2)
         cv2.circle(img,(ix,iy), 5, (128,128,128), 1)
         tot_res = tot_res + px_dist
         close_stars.append(pstar)

   if len(close_stars) > 0:
      avg_res = tot_res / len(close_stars)
   else:
      avg_res = 9999
   desc = "AVG RES:" + str(avg_res)
   cv2.putText(img, desc ,  (400,400), cv2.FONT_HERSHEY_SIMPLEX, .5, (255, 255, 255), 1)
   #cv2.rectangle(img, (new_cat_x-2, new_cat_y-2), (new_cat_x + 2, new_cat_y + 2), (128, 128, 128), 1)

   return(close_stars,img)
   
def find_img_point_from_cat_star(cx,cy,img):
   ih, iw = img.shape
   sz = 20 
   x1 = cx - sz 
   x2 = cx + sz
   y1 = cy - sz
   y2 = cy + sz
   if x1 < 0 or y1 < 0:
      return(0,0)
   if x2 >= (iw -5) or y2 > (ih -5):
      return(0,0)
   cnt_img = img[y1:y2,x1:x2]
   max_px, avg_px, px_diff,max_loc = eval_cnt(cnt_img.copy())
   if px_diff < 20:
      return(0,0)
   #cv2.imshow('pepe',cnt_img)
   #cv2.waitKey(1)
   mx,my = max_loc
   nx = cx + mx - sz + 5
   ny = cy + my - sz + 5
   return(nx,ny) 

def get_image_stars(file,show=0):
   stars = []
   img = cv2.imread(file, 0)
   avg = np.mean(img) 
   best_thresh = avg + 12
   _, star_bg = cv2.threshold(img, best_thresh, 255, cv2.THRESH_BINARY)
   thresh_obj = cv2.dilate(star_bg, None , iterations=4)
   (_, cnts, xx) = cv2.findContours(thresh_obj.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
   cc = 0
   for (i,c) in enumerate(cnts):
      x,y,w,h = cv2.boundingRect(cnts[i])
      px_val = int(img[y,x])
      cnt_img = img[y:y+h,x:x+w]
      cnt_img = cv2.GaussianBlur(cnt_img, (7, 7), 0)
      max_px, avg_px, px_diff,max_loc = eval_cnt(cnt_img.copy())
      name = "/mnt/ams2/tmp/cnt" + str(cc) + ".png"
      #star_test = test_star(cnt_img)
      x = x + int(w/2)
      y = y + int(h/2)
      if px_diff > 5 and w > 1 and h > 1 and w < 50 and h < 50:
          stars.append((x,y,int(max_px)))
          cv2.circle(img,(x,y), 5, (128,128,128), 1)

      cc = cc + 1
   if show == 1:
      cv2.imshow('pepe', img)
      cv2.waitKey(1)

   temp = sorted(stars, key=lambda x: x[2], reverse=True)
   stars = temp[0:50]
   return(stars)

def test_star_old(cnt_img):
   ch,cw = cnt_img.shape
   avg = np.mean(cnt_img)
   min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(cnt_img)
   mx,my = max_loc
  
   #if abs(dx) > 2 or abs(dy) > 2:
      #print(x,y,cw,ch,"Failed bright center test ")
   #   return(0)

   px_diff = max_val - avg 
   if px_diff > 10:
      return(1)
   else: 
      return(0)

def sum_weather(all_i_files,json_conf):

   weather = {}
   weather_sum = {}
   for file in all_i_files:
      (f_datetime, cam_id, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(file)
      weather[fh] = []
      weather_sum[fh] = []
   for file in all_i_files:
      (f_datetime, cam_id, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(file)
      num_f = len(all_i_files[file])
      weather[fh].append(num_f)

   for fh in weather:
      if len(weather[fh]) > 5:
         avg_stars = np.sum(weather[fh]) / len(weather[fh])
      else:
         avg_stars = 0
      weather_sum[fh] = avg_stars
   return(weather_sum)

def default_cal_params(cal_params,json_conf):
   if 'fov_poly' not in cal_params:
      fov_poly = [0,0]
      cal_params['fov_poly'] = fov_poly
   if 'pos_poly' not in cal_params:
      pos_poly = [0]
      cal_params['pos_poly'] = pos_poly
   if 'x_poly' not in cal_params:
      x_poly = np.zeros(shape=(15,), dtype=np.float64)
      cal_params['x_poly'] = x_poly.tolist()
   if 'y_poly' not in cal_params:
      y_poly = np.zeros(shape=(15,), dtype=np.float64)
      cal_params['y_poly'] = x_poly.tolist()
   if 'x_poly_fwd' not in cal_params:
      x_poly = np.zeros(shape=(15,), dtype=np.float64)
      cal_params['x_poly_fwd'] = x_poly.tolist()
   if 'y_poly_fwd' not in cal_params:
      y_poly = np.zeros(shape=(15,), dtype=np.float64)
      cal_params['y_poly_fwd'] = x_poly.tolist()

   return(cal_params)

def star_res(meteor_json_file, json_conf, show):
   hdm_x = 2.7272
   hdm_y = 1.875
   (f_datetime, cam_id, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(meteor_json_file)

   if show == 1:
      cv2.namedWindow('pepe')
   if "-reduced" not in meteor_json_file :
      meteor_json_red_file = meteor_json_file.replace(".json", "-reduced.json")
   if cfe(meteor_json_file) == 0:
      print("Can't open :", meteor_json_file)
      exit()
   meteor_json = load_json_file(meteor_json_file) 
   if cfe(meteor_json_red_file) == 0:
      print("Can't open reduction file:", meteor_json_red_file)
      exit()

   print("loading:", meteor_json_red_file)
   meteor_json_red = load_json_file(meteor_json_red_file) 

   hd_video_file = meteor_json_red['hd_video_file']
   hd_stack_file = hd_video_file.replace(".mp4", "-stacked.png")
   if cfe(hd_stack_file) == 0:
      hd_stack_file = meteor_json_file.replace(".json", "-stacked.png")
   hd_star_img = cv2.imread(hd_stack_file, 0)
   masks = get_masks(cam_id, json_conf,1)
   mask_points = []
   for obj in meteor_json['sd_objects']:
      for data in obj['history']:
         ms_x= (data[1] +5 ) * hdm_x
         ms_y= (data[2] +5 ) * hdm_y
         mask_points.append((ms_x,ms_y))

   hd_star_img = mask_frame(hd_star_img, mask_points, masks)
   poss = get_active_cal_file(hd_video_file)
   cal_params_file = poss[0][0]
   cal_params = load_json_file(cal_params_file)
   if False:
      master_params_file = "master_cal_file_" + cam_id + ".json"
      master_params = load_json_file(master_params_file)
      cal_params['x_poly'] = master_params['x_poly']
      cal_params['y_poly'] = master_params['y_poly']
      cal_params['x_poly_fwd'] = master_params['x_poly_fwd']
      cal_params['y_poly_fwd'] = master_params['y_poly_fwd']
      save_json_file(cal_params_file, cal_params)
   #print("Closest Cal Params File:", cal_params_file)
   #cat_image_stars, img = get_image_stars_from_catalog(hd_stack_file,json_conf,cal_params_file, masks , show = 0)
   cat_image_stars, img, no_match, res_err, match_per = get_stars_from_image(hd_stack_file,json_conf, masks , cal_params, show = 0)
   total_res = 0
   #for x in cat_image_stars:
   #   print(x)

   found_stars = len(cat_image_stars)
   for pstar in cat_image_stars:
      (name,mag,ra,dec,new_cat_x,new_cat_y,ix,iy,px_dist,cp_file) = pstar
      total_res = total_res + px_dist
   if found_stars > 0:
      avg_res = total_res / found_stars
   else:
      avg_res = 9999

   meteor_json_red['residual_star_error'] = avg_res
   #save_json_file(meteor_json_red_file, meteor_json_red)

   #print("AVG RES FOR THIS METEOR REDUCTION IS: ", avg_res)
   

   if show == 1:
      show_img = cv2.resize(img, (0,0),fx=.5, fy=.5)
      cv2.imshow('pepe', show_img)
      cv2.waitKey(1)
   return(avg_res, found_stars,img)

def fix_js(json_file):
   new_json = fix_json_file(json_file)
   if new_json is not None:
      print("FIXED", json_file)
   else:
      print("JSON GOOD", json_file)


def batch_fix (json_conf):
   max_proc = 1
   meteor_dirs = glob.glob("/mnt/ams2/meteors/*")
   bad_files = [] 
   refit = 0

   jobs = []

   for meteor_dir in sorted(meteor_dirs,reverse=True):
      meteor_files = glob.glob(meteor_dir + "/*-reduced.json")
      for meteor_file in meteor_files:
         mf = meteor_file.replace("-reduced.json", ".json")
         fn = mf.split("/")[-1]
#         fix_js(mf)

         #cmd =  "./detectMeteors.py br " + mf + " 0"
         #jobs.append(cmd) 

         cmd = "./autoCal.py imgstars " + mf + " 0"
         jobs.append(cmd) 

         cmd =  "./autoCal.py cfit " + mf + " 0"
         jobs.append(cmd) 


         mfr = mf.replace(".json", "-reduced.json")
         #cmd = "./reducer.py " + mfr 
         #jobs.append(cmd) 

   running = check_running("autoCal.py")
   print("Jobs Running: ", running)

   jc = 0
   
   for job in jobs:
      while (check_running("autoCal.py")) > max_proc:       
         time.sleep(1)
      print(job)
      os.system(job + " &")
      #if jc > 10:
      #   print("Quit early.")
      #   exit()
      jc = jc + 1

def night_sum(date,json_conf, show=0):
   
   blank = np.zeros((1080,1920),dtype=np.uint8)
   if show == 1:
      cv2.namedWindow('pepe')
   night_sum_rpt = {}
   night_dir = "/mnt/ams2/cal/hd_images/" + date + "/*calparams.json"
   day_dir = "/mnt/ams2/cal/hd_images/" + date + "/"
   cal_files = glob.glob(night_dir) 
   merge_stars = {}
   for meteor_file in cal_files:
      (f_datetime, cam_id, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(meteor_file)
      if cam_id not in night_sum_rpt:
         night_sum_rpt[cam_id] = {}
      md = load_json_file(meteor_file)
      night_sum_rpt[cam_id][meteor_file] = {}
      night_sum_rpt[cam_id][meteor_file]['astro_res_err'] = md['astro_res_err'] 
      night_sum_rpt[cam_id][meteor_file]['total_stars'] = len(md['cat_image_stars']) 
      night_sum_rpt[cam_id][meteor_file]['center_az'] = str(md['center_az']) 
      night_sum_rpt[cam_id][meteor_file]['center_el'] = str(md['center_el']) 
      night_sum_rpt[cam_id][meteor_file]['position_angle'] = str(md['position_angle']) 
      night_sum_rpt[cam_id][meteor_file]['pixscale'] = str(md['pixscale']) 
      night_sum_rpt[cam_id][meteor_file]['cat_image_stars'] = md['cat_image_stars']

   master_imgs = {}
   last_imgs = {}
   best_cal = {}

   for cam_id in sorted(night_sum_rpt):
      print("cam_id","avg_res","total_stars")
      for mf in sorted(night_sum_rpt[cam_id]):
         img_file = mf.replace("-calparams.json", "-stacked.png")
         img = cv2.imread(img_file, 0)
         if cam_id not in master_imgs:
            master_imgs[cam_id] = blank.copy()
            last_imgs[cam_id] = img.copy()
         for star in night_sum_rpt[cam_id][mf]['cat_image_stars']: 
            #print(star)
            iname,mag,ra,dec,tmp1,tmp2,px_dist,new_cat_x,new_cat_y,tmp3,tmp4,new_cat_x,new_cat_y,ix,iy,px_dist = star

            cv2.circle(img,(ix,iy), 5, (128,128,128), 1)
            cv2.rectangle(img, (new_cat_x-2, new_cat_y-2), (new_cat_x + 2, new_cat_y + 2), (128, 128, 128), 1)
            cv2.putText(img, iname,  (ix,iy), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 1)

            cv2.circle(master_imgs[cam_id],(ix,iy), 5, (128,128,128), 1)
            cv2.rectangle(master_imgs[cam_id], (new_cat_x-2, new_cat_y-2), (new_cat_x + 2, new_cat_y + 2), (128, 128, 128), 1)
            #cv2.putText(master_imgs[cam_id], iname,  (ix,iy), cv2.FONT_HERSHEY_SIMPLEX, .3, (255, 255, 255), 1)
            blend_image = cv2.addWeighted(img, .7, master_imgs[cam_id], .3,0)
         if show == 1:
            cv2.imshow('pepe', blend_image)
            cv2.waitKey(120)
         print (cam_id, night_sum_rpt[cam_id][mf]['astro_res_err'],night_sum_rpt[cam_id][mf]['total_stars'],night_sum_rpt[cam_id][mf]['center_az'],night_sum_rpt[cam_id][mf]['center_el'])

   for cam_id in sorted(master_imgs):
      img = master_imgs[cam_id] 
      last = last_imgs[cam_id] 
      blend_image = cv2.addWeighted(last, .5, master_imgs[cam_id], .5,0)
      if show == 1:
         cv2.imshow('pepe', blend_image)
         cv2.waitKey(0)

   best_cal_res = {}
   best_cal_stars = {}
   best_cal_file = {}
   # find best file for each cam for the night 
   # and copy it to the freecal dir so it can be used
   for cam_id in sorted(master_imgs):
      if cam_id not in best_cal_res:
         best_cal_res[cam_id] = 9999
         best_cal_stars[cam_id] = 0
         best_cal_file[cam_id] = 0
      for mf in night_sum_rpt[cam_id]:
         astro_res_err = night_sum_rpt[cam_id][mf]['astro_res_err']
         total_stars = night_sum_rpt[cam_id][mf]['total_stars']
         if astro_res_err < best_cal_res[cam_id] and total_stars > best_cal_stars[cam_id]:
            best_cal_res[cam_id] = astro_res_err
            best_cal_stars[cam_id] = total_stars
            best_cal_file[cam_id] = mf 
         print(mf, astro_res_err)
   print("BEST CAL FILES FOR NIGHT!")
   for cam_id in best_cal_file:
      mf = best_cal_file[cam_id]
      cal_image = mf.replace("-calparams.json", "-stacked.png")
      fn = mf.split("/")[-1]
      base_name = fn[0:30]
      free_cal_dir = "/mnt/ams2/cal/freecal/" + base_name + "/"
      new_cal_file = free_cal_dir + base_name + "-calparams.json" 
      new_cal_image = free_cal_dir + base_name + "-stacked.png" 
      if cfe(free_cal_dir, 1) == 0:
          cmd = "mkdir " + free_cal_dir
          print(cmd)
          os.system(cmd)
      cmd = "cp " + mf + " " + new_cal_file
      print(cmd)
      os.system(cmd)

      cmd = "cp " + cal_image + " " + new_cal_image
      print(cmd)
      os.system(cmd)
      cmd = "./XYtoRAdecAzEl.py az_grid " + new_cal_file
      print(cmd)

      os.system(cmd)
      print(cam_id, base_name, night_sum_rpt[cam_id][mf]['astro_res_err'], night_sum_rpt[cam_id][mf]['total_stars'])
      

def night_cal(date,json_conf, show=0):
   night_dir = "/mnt/ams2/cal/hd_images/" + date + "/*calparams.json"
   day_dir = "/mnt/ams2/cal/hd_images/" + date + "/"
   cal_files = glob.glob(night_dir) 
   merge_stars = {}
   for meteor_file in cal_files:
      md = load_json_file(meteor_file)
      (f_datetime, cam_id, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(meteor_file)
      if cam_id not in merge_stars:
         merge_stars[cam_id] = {}
      merge_stars[cam_id][meteor_file] = [] 
      if 'cat_image_stars' in md:
         cat_image_stars = md['cat_image_stars']
      else:
         print("NO CAT IMAGE STARS IN FILE", meteor_file)
         cat_image_stars = []
   
      for star in cat_image_stars:
         name,mag,ra,dec,img_ra,img_dec,match_dist,new_cat_x,new_cat_y,img_az,img_el,new_cat_x,new_cat_y,ix,iy, img_res = star
         print(cam_id, meteor_file)
         merge_stars[cam_id][meteor_file].append((meteor_file,md['ra_center'],md['dec_center'],md['position_angle'],md['pixscale'],name,mag,ra,dec,img_ra,img_dec,match_dist,new_cat_x,new_cat_y,img_az,img_el,new_cat_x,new_cat_y,ix,iy, img_res))


   cc = 0


   multi_merge(merge_stars,json_conf,day_dir, show )

def meteor_cal(date,json_conf, show=0):

   meteor_dir = "/mnt/ams2/meteors/" + date + "/*reduced.json"
   meteor_files = glob.glob(meteor_dir) 
   merge_stars = {}
   for meteor_file in meteor_files:
      print(meteor_file)
      md = load_json_file(meteor_file)
      (f_datetime, cam_id, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(meteor_file)
      if cam_id not in merge_stars:
         merge_stars[cam_id] = {}
      merge_stars[cam_id][meteor_file] = [] 
      if 'cat_image_stars' in md['cal_params']:
         cat_image_stars = md['cal_params']['cat_image_stars']
      else:
         print("NO CAT IMAGE STARS IN FILE", meteor_file)
         cat_image_stars = []
   
      for star in cat_image_stars:
         name,mag,ra,dec,img_ra,img_dec,match_dist,new_cat_x,new_cat_y,img_az,img_el,new_cat_x,new_cat_y,ix,iy, img_res = star
         merge_stars[cam_id][meteor_file].append((meteor_file,md['cal_params']['ra_center'],md['cal_params']['dec_center'],md['cal_params']['position_angle'],name,mag,ra,dec,img_ra,img_dec,match_dist,new_cat_x,new_cat_y,img_az,img_el,new_cat_x,new_cat_y,ix,iy, img_res))

   cc = 0

   multi_merge(merge_stars,json_conf,show)


def meteor_cal_old(date,json_conf):
   print("Meteor cal:", date)
   merge_stars = {}
   cal_files = glob.glob("/mnt/ams2/cal/freecal/" + date + "*")
   print(cal_files)
   for cal_dir in cal_files:
      fn = cal_dir.split("/")[-1]
      cal_file = cal_dir + "/" + fn + "-calparams.json"
      if cfe(cal_file) == 0:
         cal_file = cal_dir + "/" + fn + "-stacked-calparams.json"
      print(cal_file)
      (f_datetime, cam_id, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(cal_file)
      if cam_id not in merge_stars:
         merge_stars[cam_id] = {}

      cp = load_json_file(cal_file)
      merge_stars[cam_id][cal_file] = [] 
      for name,mag,ra,dec,img_ra,img_dec,match_dist,new_cat_x,new_cat_y,img_az,img_el,new_cat_x,new_cat_y,ix,iy, img_res in cp['close_stars']:
         merge_stars[cam_id][cal_file].append((cal_file,cp['ra_center'],cp['dec_center'],cp['position_angle'],name,mag,ra,dec,img_ra,img_dec,match_dist,new_cat_x,new_cat_y,img_az,img_el,new_cat_x,new_cat_y,ix,iy, img_res))
            #merge_stars[cam_id][cal_file] = cp['close_stars']


   save_json_file("merge.txt", merge_stars)
   multi_merge(merge_stars,json_conf)
         
def get_hd_files_for_day_cam(day,cam_id ):
   glob_str = "/mnt/ams2/HD/" + day + "*" + cam_id + "*.mp4"
   print(glob_str)
   hd_files = glob.glob(glob_str)
   return(sorted(hd_files))

def make_hd_images(day, json_conf, mod=15):

   hd_cal_files = {}
   day_dir = "/mnt/ams2/cal/hd_images/" + day + "/"
   if cfe(day_dir, 1) == 0:
      os.system("mkdir " + day_dir )

   cameras = json_conf['cameras']
   for id in  cameras:
      cam_id = json_conf['cameras'][id]['cams_id'] 
      hd_cal_files[cam_id] = []
      print("CAM ID:", id, cam_id)
      hd_files = get_hd_files_for_day_cam(day,cam_id)
      fc = 0
      for hd_file in hd_files:
         (f_datetime, cam_id, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(hd_file)
         sun_status,sun_az,sun_el = get_sun_info(f_date_str, json_conf)
         if "trim" not in hd_file and sun_status == 'night':
            if fc % mod == 0:
               hd_cal_files[cam_id].append(hd_file) 
            fc = fc + 1

   for cam_id in hd_cal_files:
      for hd_file in hd_cal_files[cam_id]:
         new_file = hd_file.split("/")[-1]
         new_file = new_file.replace(".mp4", "-stacked.png")
         new_file = day_dir + new_file
         if cfe(new_file) == 0:
            frames = load_video_frames(hd_file, json_conf, 150,0,[],1)
            print(hd_file, len(frames))
            stack_file, stack_img = stack_frames(frames, hd_file, 0)
            print(stack_file)
            os.system("mv " + stack_file + " " + new_file)
            print(new_file)
         else:
            print("skip already done.")

def batch_hd_fit(day,json_conf):
   day_dir = "/mnt/ams2/cal/hd_images/" + day + "/"
   files = glob.glob(day_dir + "*calparams.json")
   jobs1 = []
   jobs2 = []
   jobs3 = []
   for file in files:
      #cmd = "./autoCal.py cfit_hdcal " + file + " 0"
      cmd = "./autoCal.py imgstars " + file + " 0"
      jobs1.append(cmd)

   jc = 0
   for job in jobs1:
      while (check_running("autoCal.py")) > 22:       
         #print("Waiting to run some jobs...")
         time.sleep(1)
      os.system(job + " &")
      jc = jc + 1
   jc = 0
   

def scan_hd_images(day,json_conf):
   cv2.namedWindow('pepe')
   day_dir = "/mnt/ams2/cal/hd_images/" + day + "/"
   cameras = json_conf['cameras']
   for id in  cameras:
      cam_id = json_conf['cameras'][id]['cams_id'] 
      masks = get_masks(cam_id, json_conf,1)
      hd_files = glob.glob(day_dir + "*" + cam_id + "*.png")
      for hd_file in sorted(hd_files):
         close_stars = []
         cp_file = hd_file.replace("-stacked.png", "-calparams.json")
         #if cfe(cp_file) == 0:
         if True:
            img = cv2.imread(hd_file, 0)
            img = mask_frame(img, [], masks)
            avg_br = np.mean(img) 
            if avg_br < 65:
               (cat_image_stars, img, no_match_stars, avg_res,match_per,cp_data) = get_stars_from_image(hd_file,json_conf, masks, None, 0)
               for name,mag,ra,dec,new_cat_x,new_cat_y,ix,iy,px_dist,cal_params_file in cat_image_stars:
                  close_stars.append(( name,mag,ra,dec,0,0,px_dist,new_cat_x,new_cat_y,0,0,new_cat_x,new_cat_y,ix,iy,px_dist))


               show_img = cv2.resize(img, (960,540))
               cv2.putText(show_img, hd_file,  (5,500), cv2.FONT_HERSHEY_SIMPLEX, .5, (255, 255, 255), 1)
               cv2.putText(show_img, "BR: " + str(avg_br),  (5,450), cv2.FONT_HERSHEY_SIMPLEX, .5, (255, 255, 255), 1)
               cv2.imshow('pepe', show_img) 
               cv2.waitKey(30)
               if 'cat_stars' in cp_data:
                  del cp_data['cat_stars'] 
               cp_data['cat_image_stars'] = close_stars
               if "cat_img_stars" in cp_data: 
                  del cp_data['cat_img_stars'] 
               #if "user_stars" in cp_data: 
               #   del cp_data['user_stars'] 
               if "close_stars" in cp_data: 
                  del cp_data['close_stars'] 
               
               save_json_file(cp_file, cp_data)

json_conf = load_json_file("../conf/as6.json")
cmd = sys.argv[1]
try:
   date = sys.argv[2]
except:
   date = None

try:
   show = int(sys.argv[3])
except: 
   show = 0
if cmd == 'weather':
   scmd = ""
   all_i_files = track_stars(date, json_conf, scmd, None, show)
   weather = sum_weather(all_i_files,json_conf)
   for key in sorted(weather):
      if weather[key] < 0:
         status = 'very bad' 
      if weather[key] < 10:
         status = 'bad' 
      if 10 < weather[key] < 20:
         status = 'ok' 
      if weather[key] >= 20:
         status = 'good' 
      if weather[key] >= 30:
         status = 'great' 
      print(key, weather[key], status)



if cmd == 'hd_cal':
  scmd = ''
  print("SHOW: ", show)
  all_i_files = track_stars(date, json_conf, scmd, None, show)
  hd_cal(all_i_files, json_conf, date,show)

if cmd == 'save_cal':
   starfile = sys.argv[2]
   master_cal_file = starfile.replace("-allstars.json", "-master_cal_params.json")
   save_cal(starfile, master_cal_file, json_conf)

if cmd == 'mm':
   starfile = sys.argv[2]
   master_cal_file = starfile.replace("-allstars.json", "-master_cal_params.json")
   all_i_files = load_json_file(starfile)
   master_cal_params = load_json_file(master_cal_file)
   multi_merge(all_i_files,master_cal_params,master_cal_file,json_conf)

if cmd == 'multi_fit':
   scmd = ''
   all_i_files = track_stars(date, json_conf, scmd, None, show)
   multi_merge(all_i_files,json_conf)

if cmd == 'all':
   cam_id = sys.argv[3]
   all_i_files = track_stars(date, json_conf, scmd, None, show)
   startrack_file = "/mnt/ams2/cal/autocal/startrack/" + date + "_" + cam_id + ".json"
   #save_json_file(startrack_file, starlist)
   #save_hd_files(starlist)
   #calibrate_hd_files(date,cam_id,json_conf)
if cmd == 'latlon':
   cal_params_file = sys.argv[2]
   #minimize_latlon(cal_params_file, json_conf)
if cmd == 'cfit':
   meteor_json = sys.argv[2]
   if len(sys.argv) == 4:
      show = int(sys.argv[3])
   meteor_json_file_red = meteor_json.replace(".json", "-reduced.json")
   mj = load_json_file(meteor_json_file_red)
   if 'hd_stack' in mj:
      image_file = mj['hd_stack']
   else:
      image_file = mj['sd_stack']
   if "cal_params" in mj:
      cal_params = mj['cal_params']
   else:
      print("run image stars first")
      os.system("./autoCal.py imgstars " + meteor_json)
      mj = load_json_file(meteor_json_file_red)
      cal_params = mj['cal_params']

   if "center_az" not in cal_params or "cat_image_stars" not in cal_params:
      os.system("./autoCal.py imgstars " + meteor_json)
      mj = load_json_file(meteor_json_file_red)
      cal_params = mj['cal_params']

   print("START AZ:", cal_params['center_az'])
   print("START EL:", cal_params['center_el'])
   print("START POS:", cal_params['position_angle'])
   print("STArt PIXSCALE:", cal_params['pixscale'])

   fov_poly, cal_params = minimize_fov_pos(meteor_json, image_file, json_conf, cal_params, show)
   mj['cal_params'] = cal_params 
   print("FINAL AZ:", cal_params['center_az'])
   print("FINAL EL:", cal_params['center_el'])
   print("FINAL POS:", cal_params['position_angle'])
   print("FINAL PIXSCALE:", cal_params['pixscale'])


   save_json_file(meteor_json_file_red, mj)
   cmd1 = "cd /home/ams/amscams/pythonv2/; ./autoCal.py imgstars " + meteor_json + " 0 > /mnt/ams2/tmp/autoCal.txt "
   #print(cmd1)
   os.system(cmd1)


if cmd == 'cfit_hdcal':
   cal_params_file = sys.argv[2]
   meteor_json = {}
   if len(sys.argv) == 4:
      show = int(sys.argv[3])
   cal_params = load_json_file(cal_params_file)
   image_file = cal_params_file.replace(".json", "-stacked.png")

   (f_datetime, cam_id, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(cal_params_file)
   fn = cal_params_file.split("/")[-1]
   day_dir = cal_params_file.replace(fn, "")
   master_cal_file = day_dir + "/master_cal_file_" + cam_id + ".json"
   if cfe(master_cal_file) == 1:
      #print ("USE MASTER _CAL", master_cal_file)
      mcf = load_json_file(master_cal_file)
      cal_params['x_poly'] = mcf['x_poly']
      cal_params['y_poly'] = mcf['y_poly']
      cal_params['x_poly_fwd'] = mcf['x_poly_fwd']
      cal_params['y_poly_fwd'] = mcf['y_poly_fwd']


   meteor_json['cat_image_stars'] = cal_params['cat_image_stars']
   image_file = image_file.replace("-calparams", "")
   #print("IMGAGE: ", image_file)

   (f_datetime, cam_id, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(cal_params_file)
   masks = get_masks(cam_id, json_conf,1)

   cat_image_stars, img, no_match, res_err, match_per,cp_data = get_stars_from_image(image_file, json_conf, masks, cal_params, show)
   close_stars = []
   for name,mag,ra,dec,new_cat_x,new_cat_y,ix,iy,px_dist,cp_file in cat_image_stars:
      close_stars.append(( name,mag,ra,dec,0,0,px_dist,new_cat_x,new_cat_y,0,0,new_cat_x,new_cat_y,ix,iy,px_dist))
   cal_params['cat_image_stars'] = close_stars 

   fov_poly, cal_params = minimize_fov_pos(cal_params, image_file, json_conf, cal_params, show)

   cat_image_stars, img, no_match, res_err, match_per,cp_data = get_stars_from_image(image_file, json_conf, masks, cal_params, show)
   close_stars = []
   for name,mag,ra,dec,new_cat_x,new_cat_y,ix,iy,px_dist,cp_file in cat_image_stars:
      close_stars.append(( name,mag,ra,dec,0,0,px_dist,new_cat_x,new_cat_y,0,0,new_cat_x,new_cat_y,ix,iy,px_dist))
   cal_params['cat_image_stars'] = close_stars 

   save_json_file(cal_params_file, cal_params)



if cmd == "batch_fix":
   batch_fix(json_conf)

if cmd == 'star_res':
   meteor_json_file = sys.argv[2]
   res,stars,img = star_res(meteor_json_file, json_conf, show)
   print("RES:", res)

if cmd == 'imgstars':
   meteor_mode = 0
   if len(sys.argv) == 4:
      show = int(sys.argv[3])
   meteor_json_file = sys.argv[2]
   if "calparams" not in meteor_json_file:
      meteor_mode = 1
      meteor_json_file_red = meteor_json_file.replace(".json", "-reduced.json")
      meteor_json = load_json_file(meteor_json_file_red)
      file = meteor_json['hd_stack']
      if cfe(file) == 0:
         file = file.replace(".png", "-stacked.png")
         meteor_json['hd_stack'] = file
      if "cal_params" in meteor_json:
         cal_params = meteor_json['cal_params']
      else:
         
         poss = get_active_cal_file(file)
         cal_params_file = poss[0][0]
         cal_params = load_json_file(cal_params_file)
         print("Try to use cal params:", cal_params_file)
         meteor_json['cal_params'] = cal_params
         if "tried_cal" not in meteor_json:
            meteor_json['tried_cal'] = []
            meteor_json['tried_cal'].append(cal_params_file)
         else:
            already_tried = 1
            next_one = len(meteor_json['tried_cal'])
            cal_params_file = poss[next_one][0]
            cal_params = load_json_file(cal_params_file)
            meteor_json['cal_params'] = cal_params
            meteor_json['tried_cal'].append(cal_params_file)
            
         if len(meteor_json['tried_cal']) > 3:
            meteor_json['tried_cal'] = []
 
         meteor_json['cal_params'] = cal_params 
         print("Saving json file....", meteor_json_file_red)
         save_json_file(meteor_json_file_red, meteor_json)
         print("Try to use cal params:", cal_params_file)
   else:
      meteor_json = load_json_file(meteor_json_file)
      meteor_json_file_red = meteor_json_file
      cal_params = meteor_json
      file = meteor_json_file.replace("-calparams.json", "-stacked.png")

   (f_datetime, cam_id, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(file)
   masks = get_masks(cam_id, json_conf,1)
   if "meteor_frame_data" in meteor_json:
      (box_min_x,box_min_y,box_max_x,box_max_y) = define_crop_box(meteor_json['meteor_frame_data'])
      meteor_json['crop_box'] = (box_min_x,box_min_y,box_max_x,box_max_y)
      box_w = box_max_x - box_min_x 
      box_h = box_max_y - box_min_y
      mask_s = str(box_min_x) + "," + str(box_min_y) + "," + str(box_w) + "," + str(box_h)
      masks.append(mask_s)


   if cal_params == 0:
      poss = get_active_cal_file(file)
      cal_params_file = poss[0][0]
      cal_params = load_json_file(cal_params_file)
   if "center_az" not in cal_params:
      poss = get_active_cal_file(file)
      cal_params_file = poss[0][0]
      cal_params = load_json_file(cal_params_file)
      if meteor_mode == 1:
         meteor_json['cal_params'] = cal_params


   center_az = cal_params['center_az']
   center_el = cal_params['center_el']
   rah,dech = AzEltoRADec(center_az,center_el,meteor_json_file,cal_params,json_conf)
   rah = str(rah).replace(":", " ")
   dech = str(dech).replace(":", " ")
   ra_center,dec_center = HMS2deg(str(rah),str(dech))
   cal_params['ra_center'] = ra_center
   cal_params['dec_center'] = dec_center


   fn = meteor_json_file.split("/")[-1]
   day_dir = meteor_json_file.replace(fn, "")
   master_cal_file = day_dir + "/master_cal_file_" + cam_id + ".json"
   if cfe(master_cal_file) == 1:
      #print("MASTER:", master_cal_file)
      mcf = load_json_file(master_cal_file)
      cal_params['x_poly'] = mcf['x_poly']
      cal_params['y_poly'] = mcf['y_poly']
      cal_params['x_poly_fwd'] = mcf['x_poly_fwd']
      cal_params['y_poly_fwd'] = mcf['y_poly_fwd']

   cat_image_stars, img, no_match, res_err, match_per,cp_data = get_stars_from_image(file, json_conf, masks, cal_params, show)
   print("MATCH/NO MATCH: ", len(cat_image_stars), len(no_match))
   if len(cat_image_stars) > 0 and len(no_match) > 0:
      good_perc = len(cat_image_stars) / len(no_match)
   else:
      good_perc = 0
   print("PERC GOOD:", good_perc)
   if good_perc < .25 and res_err > 8:
      print("Problem here. Let's clean up. try again...", meteor_json_file )
      del meteor_json['cal_params']  
      meteor_json['deleted_tries']  = 1
      meteor_json['tried_cal'] = []

      if "tried_cal" in meteor_json:
         if len(meteor_json['tried_cal']) < 4 and "deleted_tries" not in meteor_json:
            cmd = "./autoCal.py imgstars " + meteor_json_file + " 0"
            print(cmd)
            os.system(cmd)
      #else:
      #   meteor_json['tried_cal'] = []
      save_json_file(meteor_json_file_red, meteor_json)
     
      exit()


   # compute std dev distance
   tot_res = 0
   #close_stars = []
   dist_list = []
   for name,mag,ra,dec,new_cat_x,new_cat_y,ix,iy,px_dist,cp_file in cat_image_stars:
      px_dist = calc_dist((ix,iy),(new_cat_x,new_cat_y))
      dist_list.append(px_dist)
      tot_res = tot_res + px_dist
   std_dev_dist = np.std(dist_list)
   close_stars = []

   for name,mag,ra,dec,new_cat_x,new_cat_y,ix,iy,px_dist,cp_file in cat_image_stars:
      if meteor_mode == 0:
         close_stars.append(( name,mag,ra,dec,0,0,px_dist,new_cat_x,new_cat_y,0,0,new_cat_x,new_cat_y,ix,iy,px_dist))
      if meteor_mode == 1:
         close_stars.append(( name,mag,ra,dec,0,0,px_dist,new_cat_x,new_cat_y,0,0,new_cat_x,new_cat_y,ix,iy,px_dist))

   if "cat_stars" in cal_params: 
      del cal_params['cat_stars']
   if "cat_img_stars" in cal_params: 
      del cal_params['cat_img_stars']
   #print("CHECK FOR USER STARS:")
   #if "user_stars" in cal_params.keys(): 
      #print("DELETE user_stars")
      #del cal_params['user_stars']
   
   if len(cat_image_stars) > 0:
      res_err = tot_res / len(cat_image_stars)
   else:
      res_err = 9999
   center_az = cal_params['center_az']
   center_el = cal_params['center_el']
   rah,dech = AzEltoRADec(center_az,center_el,file,cal_params,json_conf)
   rah = str(rah).replace(":", " ")
   dech = str(dech).replace(":", " ")
   ra_center,dec_center = HMS2deg(str(rah),str(dech))
   cal_params['ra_center'] = ra_center
   cal_params['dec_center'] = dec_center
   cal_params['astro_res_err'] = res_err
   cal_params['cat_image_stars'] = close_stars 



   #print("FILE: ", file)
   print("RES ERR: ", cam_id, res_err, len(close_stars) )
   #print("MATCH STARS: ", len(close_stars))
   if meteor_mode == 0:     
      if "cal_params" in cal_params: 
         del cal_params['cal_params']
   if "close_stars" in cal_params: 
      del cal_params['close_stars']

   #print("Saving:", meteor_json_file_red)
   #save_json_file(meteor_json_file_red, meteor_json)
   if meteor_mode == 0:
      save_json_file(meteor_json_file_red, cal_params)
   else:
      meteor_json['cal_params'] = cal_params
      save_json_file(meteor_json_file_red, meteor_json)


if cmd == 'batch_hd_fit':
   date = sys.argv[2]
   print("BHD:", date)
   batch_hd_fit(date, json_conf)

if cmd == 'scan_hd_images':
   date = sys.argv[2]
   scan_hd_images(date, json_conf)
if cmd == 'make_hd_images':
   date = sys.argv[2]
   if date == "today":
      day = datetime.datetime.today().strftime('%Y_%m_%d')
      print(day)
   make_hd_images(day, json_conf)

if cmd == 'night_cal':
   date = sys.argv[2]
   if len(sys.argv) == 4:
      show = int(sys.argv[3])
   print("date:", date)
   night_cal(date, json_conf, show)

if cmd == 'night_sum':
   date = sys.argv[2]
   if len(sys.argv) == 4:
      show = int(sys.argv[3])
   night_sum(date, json_conf, show)

if cmd == 'meteor_cal':
   date = sys.argv[2]
   if len(sys.argv) == 4:
      show = int(sys.argv[3])
   print("date:", date)
   meteor_cal(date, json_conf, show)
if cmd == 'run_merge':
   merge_file = sys.argv[2]
   if len(sys.argv) == 5:
      show = int(sys.argv[4])
   cam_id = sys.argv[3]
   merge_stars = load_json_file(merge_file)
   cam_stars = {}
   master_cal_params = {}
   fn = merge_file.split("/")[-1]
   day_dir = merge_file.replace(fn, "")
   master_cal_file = day_dir + "/master_cal_file_" + cam_id + ".json"
   print("SHOW:", show)
   status, fin_cal_params = minimize_poly_params_fwd(merge_stars, json_conf,0,0,cam_id, master_cal_file,show)

   if type(fin_cal_params) is not int :
      for key in fin_cal_params:
         print(key)
         master_cal_params[key] = fin_cal_params[key]
      if status == 1 :
         print("SAVING MCF:", master_cal_file)
         save_json_file(master_cal_file, master_cal_params)


