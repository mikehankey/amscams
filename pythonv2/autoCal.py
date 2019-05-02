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
from lib.CalibLib import distort_xy_new, find_image_stars, distort_xy_new, XYtoRADec, radec_to_azel, get_catalog_stars,AzEltoRADec , HMS2deg, get_active_cal_file, RAdeg2HMS, clean_star_bg
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

def multi_merge(all_stars, master_cal_params, master_cal_file, json_conf):
   show = 0
   cameras = json_conf['cameras']
   cam_ids = []
   multi_merge = {}
   cp_files = {}
   for camera in cameras:
      multi_merge[cameras[camera]['cams_id']]  = {}
      cam_id = cameras[camera]['cams_id']
 
      cp_files[cameras[camera]['cams_id']]  = ""


   bad_cams = {}
   for cam_id in master_cal_params:
      bad_cams[cam_id] = 0 
      if master_cal_params[cam_id]['center_az'] is None or str(master_cal_params[cam_id]['center_az']) == "nan" :
         print("GAY", cam_id, str(master_cal_params[cam_id]['center_az']))
         bad_cams[cam_id] = 1
         #sample_file = sample_files
         #poss = get_active_cal_file(sample_file)
         #cal_params_file = poss[0][0]

   for file in all_stars:
      (f_datetime, cam_id, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(file)
      if bad_cams[cam_id] == 0:

         multi_merge[cam_id][file] = [] 
         sc = 0
         print(file)
         for star in all_stars[file]:
            print(sc)
            name,mag,ra,dec,new_cat_x,new_cat_y,ix,iy,px_dist,cal_params_file = star
            (f_datetime, cam_id, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(cal_params_file)
            cal_params = master_cal_params[cam_id]
            cp_files[cam_id] = cal_params_file
            img_ra = ra
            img_dec = dec
            match_dist = px_dist
            img_az = cal_params['center_az']
            img_el = cal_params['center_el']
            img_res = px_dist
            # find new ra/dec center
            rah,dech = AzEltoRADec(img_az,img_el,file,cal_params,json_conf)
            rah = str(rah).replace(":", " ")
            dech = str(dech).replace(":", " ")
            ra_center,dec_center = HMS2deg(str(rah),str(dech))

            if match_dist < 5:
               multi_merge[cam_id][file].append((cal_params_file,ra_center,dec_center,name,mag,ra,dec,img_ra,img_dec,match_dist,new_cat_x,new_cat_y,img_az,img_el,new_cat_x,new_cat_y,ix,iy, img_res))
            sc = sc + 1

   for cam_id in multi_merge:
      merge_file = "/mnt/ams2/cal/autocal/startrack/starmerge-" + cam_id + ".json"
      save_json_file(merge_file, multi_merge[cam_id])

      merged_stars = multi_merge[cam_id]
      cal_params_file = cp_files[cam_id] 
      #cal_params = load_json_file(cal_params_file)
      cal_params = master_cal_params[cam_id]
      #orig_ra_center = cal_params['ra_center']
      #orig_dec_center = cal_params['dec_center']

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
               simg = cv2.resize(img, (960,540))
               cv2.imshow('pepe', simg)
               cv2.waitKey(30)

      new_cp = cal_params_file.replace("-calparams.json", "-calparams-master.json")
      if cfe(new_cp) == 0 :
         new_multi_fit_merge = remove_bad_pairs(multi_fit_merge)
         print("MINIMIZE: " )
         cal_params = default_cal_params(cal_params,json_conf)
         #cal_params['close_stars'] = user_stars
         fin_cal_params = minimize_poly_params_fwd(new_multi_fit_merge, cal_params_file, cal_params,json_conf,0,0,0)
         for key in fin_cal_params:
            master_cal_params[key] = fin_cal_params[key]
      else:
         print("SKIPPING ALREADY DONE!")
   save_json_file(master_cal_file, master_cal_params)

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

def minimize_fov_pos(cal_params_file, json_conf, show=0 ):
   fov_pos_poly = None
   print("CP:", cal_params_file)
   cal_params = load_json_file(cal_params_file)
   paired_stars = cal_params['close_stars']
   cal_params['device_lat'] = json_conf['site']['device_lat']
   cal_params['device_lng'] = json_conf['site']['device_lng']
   cal_params['device_alt'] = json_conf['site']['device_alt']
   cal_params['orig_ra_center'] = cal_params['ra_center']
   cal_params['orig_dec_center'] = cal_params['dec_center']
   cal_params['orig_pos_ang'] = cal_params['position_angle']
   org_az = cal_params['center_az']
   org_el = cal_params['center_el']
   org_pos = cal_params['position_angle']




   if fov_pos_poly is None:
      this_poly = np.zeros(shape=(3,), dtype=np.float64)
      this_poly[0] = -.01
      this_poly[1] = -.01
      this_poly[2] = -.01
   else:
      this_poly = fov_post_poly 
   res = reduce_fov_pos(this_poly, cal_params,cal_params_file,json_conf, paired_stars,show)
   print("Initial residual error.", res)   
   if res < 2.5:
      # Res is good No need to recalibrate!
      #print("Res is good no need to recal")
      exit()

   res = scipy.optimize.minimize(reduce_fov_pos, this_poly, args=(cal_params,cal_params_file,json_conf, paired_stars,show), method='Nelder-Mead')
   fov_pos_poly = res['x']
   fov_pos_fun = res['fun']
   cal_params['fov_pos_poly'] = fov_pos_poly.tolist()
   cal_params['fov_pos_fun'] = fov_pos_fun
   cal_params['center_az'] = cal_params['center_az'] + fov_pos_poly[0] 
   cal_params['center_el'] = cal_params['center_el'] + fov_pos_poly[1] 
   cal_params['position_angle'] = cal_params['position_angle'] + fov_pos_poly[2] 
   save_json_file(cal_params_file, cal_params)
   print("ORG/NEW AZ: ", org_az, cal_params['center_az'])
   print("ORG/NEW EL: ", org_el, cal_params['center_el'])
   print("ORG/NEW POS: ", org_pos, cal_params['position_angle'])
   print("FOV/POS POLY : ", fov_pos_poly)
   print("NEW AVG RES: ", fov_pos_fun)
   if fov_pos_fun < 2:
      # clone the calibration file to new day
      fn = cal_params_file.split("/")[-1]
      cal_dir = fn[0:30]
      stack = cal_params_file.replace("-calparams.json", ".png")
      free_cal_dir = "/mnt/ams2/cal/freecal/" + cal_dir + "/"
      new_cal_file = free_cal_dir + cal_dir + "-calparams.json"
      new_cal_stack = free_cal_dir + cal_dir + "-stacked.png"
      cmd = "mkdir " + free_cal_dir 
      print(cmd)
      os.system(cmd)
      cmd = "cp " + cal_params_file + " " + new_cal_file 
      print(cmd)
      os.system(cmd)
      cmd = "cp " + stack + " " + new_cal_stack 
      print(cmd)
      os.system(cmd)
      cmd = "./XYtoRAdecAzEl.py az_grid " + new_cal_file
      print(cmd)
      os.system(cmd)
   return(fov_pos_poly)

def reduce_fov_pos(this_poly, cal_params, cal_params_file, json_conf, paired_stars, show=0):
   # cal_params_file should be 'image' filename
   org_az = cal_params['center_az'] 
   org_el = cal_params['center_el'] 
   org_pos_angle = cal_params['orig_pos_ang'] 

   new_az = cal_params['center_az'] + this_poly[0]
   new_el = cal_params['center_el'] + this_poly[1]
   position_angle = cal_params['orig_pos_ang'] + this_poly[2]

   rah,dech = AzEltoRADec(new_az,new_el,cal_params_file,cal_params,json_conf)
   rah = str(rah).replace(":", " ")
   dech = str(dech).replace(":", " ")

   ra_center,dec_center = HMS2deg(str(rah),str(dech))

   #print(ra_center,dec_center,position_angle,this_poly[0], this_poly[1], this_poly[2])
   cal_params['position_angle'] = position_angle
   cal_params['ra_center'] = ra_center
   cal_params['dec_center'] = dec_center
   cal_params['device_lat'] = json_conf['site']['device_lat']
   cal_params['device_lng'] = json_conf['site']['device_lng']
   cal_params['device_alt'] = json_conf['site']['device_alt']


   fov_poly = cal_params['fov_poly']
   pos_poly = cal_params['pos_poly']
   x_poly = cal_params['x_poly']
   y_poly = cal_params['y_poly']
   cat_stars = get_catalog_stars(fov_poly, pos_poly, cal_params,"x",x_poly,y_poly,min=0)
   new_res = []
   new_paired_stars = []
   used = {}
   org_stars = len(paired_stars)
   for cat_star in cat_stars:
      (name,mag,ra,dec,new_cat_x,new_cat_y) = cat_star
      dname = name.decode("utf-8")
      for data in paired_stars:
         iname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,old_cat_x,old_cat_y,six,siy,cat_dist  = data
         if dname == iname:
            pdist = calc_dist((six,siy),(new_cat_x,new_cat_y))
            #print("match found", dname, iname, pdist)
            if pdist <= 15:
               new_res.append(pdist)
               used_key = str(six) + "." + str(siy)
               if used_key not in used: 
                  new_paired_stars.append((iname,mag,ra,dec,new_cat_x,new_cat_y,six,siy,pdist))
                  used[used_key] = 1

   tres  =0 
   for iname,mag,ra,dec,new_cat_x,new_cat_y,six,siy,pdist in new_paired_stars:
      tres = tres + pdist
     
   tres = tres + ((len(paired_stars) - len(new_paired_stars) ) * 99)

   if len(new_paired_stars) > 0:
      avg_res = tres / len(new_paired_stars) 
   else:
      avg_res = 9999999
      res = 9999999
   print("AVG RES:", avg_res, len(new_paired_stars))
   return(avg_res)


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
            frames = load_video_frames(hd_file, json_conf, 300)
            print(len(frames)) 
            stack_file, stack_img = stack_frames(frames, hd_file, 1)
         
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
   #cat_stars = cat_stars[0:50]

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
   if px_diff < 20:
      return(0,0)
   #print("PX DIFF:", px_diff)
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



json_conf = load_json_file("../conf/as6.json")


cmd = sys.argv[1]
date = sys.argv[2]
show = int(sys.argv[3])
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
   cal_params_file = sys.argv[2]
   minimize_fov_pos(cal_params_file, json_conf)

