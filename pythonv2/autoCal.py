#!/usr/bin/python3
import glob
import os
import math
import cv2
import math
import numpy as np
import scipy.optimize
from fitMulti import minimize_poly_params_fwd
from lib.VideoLib import get_masks, find_hd_file_new, load_video_frames

from lib.ImageLib import mask_frame , stack_frames

#import matplotlib.pyplot as plt
import sys
#from caliblib import distort_xy,
from lib.CalibLib import distort_xy_new, find_image_stars, distort_xy_new, XYtoRADec, radec_to_azel, get_catalog_stars,AzEltoRADec , HMS2deg, get_active_cal_file, RAdeg2HMS
from lib.UtilLib import calc_dist, find_angle

from lib.UtilLib import angularSeparation, convert_filename_to_date_cam, better_parse_file_date
from lib.FileIO import load_json_file, save_json_file, cfe
from lib.UtilLib import calc_dist,find_angle
import lib.brightstardata as bsd
from lib.DetectLib import eval_cnt

def multi_merge(all_stars, json_conf):

   cameras = json_conf['cameras']
   cam_ids = []
   multi_merge = {}
   cp_files = {}
   for camera in cameras:
      multi_merge[cameras[camera]['cams_id']]  = {}
      cp_files[cameras[camera]['cams_id']]  = ""

   for file in all_stars:
      (f_datetime, cam_id, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(file)
      multi_merge[cam_id][file] = [] 
      for star in all_stars[file]:
         print("STAR LEN:", len(star))
         print("STAR :", star)
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
         print("CENTER AZ/EL", img_az, img_el, ra_center, dec_center)

         if match_dist < 5:
            multi_merge[cam_id][file].append((cal_params_file,ra_center,dec_center,name,mag,ra,dec,img_ra,img_dec,match_dist,new_cat_x,new_cat_y,img_az,img_el,new_cat_x,new_cat_y,ix,iy, img_res))

   for cam_id in multi_merge:
      merge_file = "/mnt/ams2/cal/autocal/startrack/starmerge-" + cam_id + ".json"
      save_json_file(merge_file, multi_merge[cam_id])

      merged_stars = multi_merge[cam_id]
      cal_params_file = cp_files[cam_id] 
      cal_params = load_json_file(cal_params_file)
      orig_ra_center = cal_params['ra_center']
      orig_dec_center = cal_params['dec_center']

      multi_fit_merge = []
      for file in merged_stars:
         print(file)
         if cfe(file) == 1:
            img = cv2.imread(file, 0)
            img = cv2.resize(img, (1920,1080))
            for star in merged_stars[file]:
               cal_params_file,ra_center,dec_center,name,mag,ra,dec,img_ra,img_dec,match_dist,new_cat_x,new_cat_y,img_az,img_el,new_cat_x,new_cat_y,ix,iy, img_res = star

               print("MIKE:", file,ra_center,dec_center,img_az,img_el)
               cv2.circle(img,(ix,iy), 5, (128,128,128), 1)
               cv2.rectangle(img, (new_cat_x-2, new_cat_y-2), (new_cat_x + 2, new_cat_y + 2), (128, 128, 128), 1)
               cv2.line(img, (ix,iy), (new_cat_x,new_cat_y), (255), 2)
               multi_fit_merge.append(star)
            if show == 1:
               cv2.imshow('pepe', img)
               cv2.waitKey(1)

      new_cp = cal_params_file.replace("-calparams.json", "-calparams-master.json")
      if cfe(new_cp) == 1 and "010001" not in new_cp:
         new_multi_fit_merge = remove_bad_pairs(multi_fit_merge)
         print("MINIMIZE: ", cal_params_file, orig_ra_center, orig_dec_center)
         minimize_poly_params_fwd(new_multi_fit_merge, cal_params_file, cal_params,json_conf,orig_ra_center,orig_dec_center,show=0)
      else:
         print("SKIPPING ALREADY DONE!")

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
      (cal_file,ra_center,dec_center,dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy, img_res) = star
      angle = find_angle((new_cat_x, new_cat_y), (six,siy)) 
      quad = star_quad(six,siy)
      quad_ang[quad].append(angle)

   quad_avg[1] = np.mean(quad_ang[1])
   quad_avg[2] = np.mean(quad_ang[2])
   quad_avg[3] = np.mean(quad_ang[3])
   quad_avg[4] = np.mean(quad_ang[4])

   print("MERGED STARS:", len(merged_stars))

   for star in merged_stars:
      good = 1
      (cal_file,ra_center,dec_center,dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy, img_res) = star
      print("ANG: ", new_cat_x,new_cat_y,six,siy)
      angle = find_angle((new_cat_x, new_cat_y), (six,siy)) 
      quad = star_quad(six,siy)
      avg_ang = quad_avg[quad]
      if match_dist > 5:
         ang_diff = abs(angle - avg_ang)
         if ang_diff > 20:
            print("   ", dcname,quad,match_dist, angle,avg_ang, ang_diff)
            good = 0
      if good == 1:
         new_merged_stars.append(star) 


   return(new_merged_stars)


def minimize_lat_lon(json_conf,cal_params_file,all_paired_stars,show=0,latlon_poly=None):
   cal_params = load_json_file(cal_params_file)
   cal_params['device_lat'] = json_conf['site']['device_lat']
   cal_params['device_lon'] = json_conf['site']['device_lng']
   cal_params['device_alt'] = json_conf['site']['device_alt']
   cal_params['orig_ra_center'] = cal_params['ra_center']
   cal_params['orig_dec_center'] = cal_params['dec_center']

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

   
      min_mod = 60
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
      if "-tn" not in file and "-night-stack" not in file:
         sd_files.append(file)

   return(sd_files)

def track_stars (day,json_conf,scmd='',cal_params_file=None,show=0):

   if show == 1:
      cv2.namedWindow('pepe')
   min_mod = 120

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
            print("MIKE:", file)
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

def hd_cal(all_i_files, json_conf):
   print("HD CAL")
   for file in all_i_files:
      hd_stack_file = file.replace("-stacked.png", "-hd-stacked.png")
      if cfe(hd_stack_file) == 0:
         hd_file, hd_trim,time_diff_sec, dur = find_hd_file_new(file, 0, 10, 0)
         frames = load_video_frames(hd_file, json_conf)
         print(len(frames)) 
         stack_file, stack_img = stack_frames(frames, hd_file, 1)
         
         print(stack_file, stack_img.shape) 
         cv2.imwrite(hd_stack_file, stack_img)
 
         print(file, hd_file, hd_trim,time_diff_sec,dur)

   #for each hour of the night. 
   # if weather is good
   # stack 2x hd file per hour
   # attempt to solve each
   # save successful ones to new dir

def get_image_stars_from_catalog(file,json_conf,cal_params_file, masks = [], show = 0):
   img = cv2.imread(file,0)
   img = cv2.resize(img, (1920,1080))
   img = mask_frame(img, [], masks)
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
   
   #rahh = RAdeg2HMS(rah)
   ra_center,dec_center = HMS2deg(str(rah),str(dech))

   cal_params['ra_center'] = ra_center
   cal_params['dec_center'] = dec_center

   fov_poly = cal_params['fov_poly']
   pos_poly = cal_params['pos_poly']
   x_poly = cal_params['x_poly']
   y_poly = cal_params['y_poly']
   #print(x_poly, y_poly, cal_params, x_poly,y_poly)
   cat_stars = get_catalog_stars(fov_poly, pos_poly, cal_params,"x",x_poly,y_poly,min=0)
   cat_stars = cat_stars[0:50]

   cat_image_stars = []
   for cat_star in cat_stars:
      (name,mag,ra,dec,new_cat_x,new_cat_y) = cat_star
      name = name.decode("utf-8")
      #print(name,new_cat_x,new_cat_y)
      new_cat_x = int(new_cat_x)
      new_cat_y = int(new_cat_y)
      ix,iy = find_img_point_from_cat_star(new_cat_x,new_cat_y,img)
      if ix != 0 and iy != 0: 
         px_dist = calc_dist((ix,iy),(new_cat_x,new_cat_y))
         if px_dist < 25:
            cat_image_stars.append((name,mag,ra,dec,new_cat_x,new_cat_y,ix,iy,px_dist,cal_params_file))

   for pstar in cat_image_stars:
      (name,mag,ra,dec,new_cat_x,new_cat_y,ix,iy,px_dist,cp_file) = pstar

      cv2.rectangle(img, (new_cat_x-2, new_cat_y-2), (new_cat_x + 2, new_cat_y + 2), (128, 128, 128), 1)
      cv2.line(img, (ix,iy), (new_cat_x,new_cat_y), (255), 2)
      cv2.circle(img,(ix,iy), 5, (128,128,128), 1)

   #cv2.rectangle(img, (new_cat_x-2, new_cat_y-2), (new_cat_x + 2, new_cat_y + 2), (128, 128, 128), 1)

   return(cat_image_stars,img)
   
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
   if px_diff < 10:
      return(0,0)
   #cv2.imshow('pepe',cnt_img)
   #cv2.waitKey(0)
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

def test_star(cnt_img):
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

json_conf = load_json_file("../conf/as6.json")


cmd = sys.argv[1]
show = 0
date = sys.argv[2]
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
  all_i_files = track_stars(date, json_conf, scmd, None, show)
  hd_cal(all_i_files, json_conf)

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

