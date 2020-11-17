"""

Autocal functions

"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import time

import pickle
from lib.conversions import datetime2JD
from lib.cyFuncs import cyjd2LST, cyraDecToXY 
#from lib.cyjd2LST import *
from lib.conversions import JD2HourAngle
#from lib.cyraDecToXY import *
import scipy.optimize
import math
import cv2
import numpy as np
from lib.PipeUtil import bound_cnt, cnt_max_px, cfe, load_json_file, save_json_file, convert_filename_to_date_cam, angularSeparation, calc_dist, date_to_jd, get_masks , find_angle, collinear
from lib.PipeImage import mask_frame, quick_video_stack
from lib.DEFAULTS import *
import os
import ephem
import lib.brightstardata as bsd
from lib.PipeReport import autocal_report
from datetime import datetime
import glob
from PIL import ImageFont, ImageDraw, Image, ImageChops
tries = 0


def sync_back_admin_cals():
   cc_dir = "/mnt/archive.allsky.tv/" + STATION_ID + "/CAL/"
   lc_dir = "/mnt/ams2/meteor_archive/" + STATION_ID + "/CAL/"

   bcc_dir = "/mnt/archive.allsky.tv/" + STATION_ID + "/CAL/BEST/"
   blc_dir = "/mnt/ams2/meteor_archive/" + STATION_ID + "/CAL/BEST/"

   cmd = "/usr/bin/rsync -av " + cc_dir + "*.json " + lc_dir
   os.system(cmd)
   cmd = "/usr/bin/rsync -av " + bcc_dir + "*.json " + blc_dir
   os.system(cmd)


   new_files = glob.glob(blc_dir + "*")
   fc_dirs = None
   for file in new_files:
      rfn, dir = fn_dir(file)
      rfn = rfn.replace("-calparams.json", "")
      #print("RFN:", rfn, file)
      cps, imgs, fc_dirs = find_fc_files(rfn, fc_dirs)
      cp_file = cps[0]
      src_img_file = imgs[0]
      #print(file, cp_file, src_img_file)

      # copy the new json from BEST dir to the cp file (with right/new name)
      fc_d = "/mnt/ams2/cal/freecal/" + rfn + "/" 
      cmd = "cp " + file + " " + fc_d
      print(cmd)
      os.system(cmd)

      # open src image and resave as .png without -src.jpg (if it doesn't exist)
      jpg_src = fc_d + rfn + "-src.jpg"
      png_src = jpg_src.replace("-src.jpg", ".png")
      cp_file = jpg_src.replace("-src.jpg", "-calparams.json")
      if cfe(png_src) == 0 or cfe(jpg_src) == 0:
         print("saving jpg and png src", jpg_src, png_src)
         src_img = cv2.imread(src_img_file)
         cv2.imwrite(png_src, src_img)
         cv2.imwrite(jpg_src, src_img)

      # remake azgrid open src image and resave as .png without -src.jpg (if it doesn't exist)
      cmd = "./AzElGrid.py az_grid " + cp_file 
      print(cmd)
      os.system(cmd)

      # save user_stars file
      cp = load_json_file(cp_file)
      us = cp['user_stars']
      usf = cp_file.replace("-calparams.json", "-user-stars.json")
      ddd= {}
      ddd['user_stars'] = cp['user_stars'] 
      save_json_file(usf, ddd)

      # remove or rename (ra grid) old / stale files
      old_files = glob.glob(fc_d + "*stacked*")
      for of in old_files:
         print("OF:", of)
         cmd = "rm " + of
         os.system(cmd)
      print("DONE:", fc_d)
      #exit()


def find_fc_files(root_file, fcdirs = None):
   # find free cal files matching a root file
   fc_dir = "/mnt/ams2/cal/freecal/"
   fcdirs = glob.glob(fc_dir + "*")
   # first clean up any misnamed dirs
   for fcd in fcdirs:
      if "-" in fcd:
         root_dir = fcd.split("-")[0]
         cmd = "mv " + fcd + " " + root_dir
         os.system(cmd)

   fcdirs = glob.glob(fc_dir + "*")
   cps = []
   imgs = []
   for fcd in fcdirs:
      if root_file in fcd: 
         if cfe(fcd, 1) == 1:
            cps = glob.glob(fcd + "/*calparams.json")
            imgs = glob.glob(fcd + "/*src.jpg")
             
   return(cps, imgs, fcdirs)
def star_db_mag(cam, json_conf):
   year = datetime.now().strftime("%Y")
   autocal_dir = "/mnt/ams2/meteor_archive/" + STATION_ID + "/CAL/AUTOCAL/" + year + "/solved/"
   st_db = autocal_dir + "star_db-" + STATION_ID + "-" + cam + ".info"
   print(st_db)
   sdb = load_json_file(st_db)
   mags = []
   flux = []
   i = 0
   print(st_db)
   exit()
   for star in sdb['autocal_stars']:
      (cal_file , center_az, center_el, ra_center, dec_center, position_angle, pixscale, dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int) = star
      #if 100 < star_int < 10000:

      if "params" in cal_file:
         print(i, dcname, mag, star_int)
         mags.append(mag)
         flux.append(star_int)
         i = i + 1

   z = np.polyfit(mags, flux, 3)
   f = np.poly1d(z)
   x_new = np.linspace(mags[0], mags[-1], len(mags))
   y_new = f(x_new)

   plt.plot(mags, flux, 'o')
   plt.plot(x_new, y_new )
   plt.show()

def project_snaps(json_conf):
   matrix = make_file_matrix("today", json_conf)
   snaps = sorted(glob.glob("/mnt/ams2/SNAPS/*00_000*.png"))
   maps = {}
   for snap in sorted(snaps):
      (f_datetime, this_cam, f_date_str,y,m,d, h, mm, s) = convert_filename_to_date_cam(snap)
      make_gnome_map(snap, json_conf,None,None,None)
      exit()
      key = h + "-" + mm
      if key in matrix:
         if "files" not in matrix[key]:
            matrix[key]['files'] = []
         matrix[key]['files'].append(snap)
   save_json_file("test.json", matrix)
   print("Matrix saved")
   for key in matrix:
       h,m = key.split("-")
       #if h == "12":
       if True:
             print(key, len(matrix[key]['files']))
             asimg, ascp,maps = project_many(matrix[key]['files'][0:6], json_conf,maps)
             cx1 = 1000
             cx2 = 4000 
             cy1 = 1000
             cy2 = 4000 
             cv2.circle(asimg,(2500,2500), 1500, (128,128,128), 1)
             asimg_crop = asimg[cy1:cy2,cx1:cx2]
             print("ASIMG SIZE:", asimg_crop.shape)
             if SHOW == 1:
                disp_img = cv2.resize(asimg_crop, (800, 800))
           
                cv2.imshow('allsky', disp_img)
                cv2.waitKey(30)

def make_file_matrix(day,json_conf):
   today = datetime.now().strftime("%Y_%m_%d")
   if day == today:
      last_hour =  int(datetime.now().strftime("%H")) + 1
   else:
      last_hour = 24
   file_matrix = {}
   #sec_bin = [0,30]
   for hour in range (0, last_hour):
      for min in range(0,60):
         key = '{:02d}-{:02d}'.format(hour,min)
         file_matrix[key] = {}
         file_matrix[key]
         for cam in sorted(json_conf['cameras'].keys()):
            file_matrix[key][cam] = ""


   return(file_matrix)


def project_many(files, json_conf,maps=None):
   if maps is None:
      maps = {}
   asimg = None
   print("FILES:", len(files), files)
   for file in files:
      if asimg is None:
         asimg, ascp,maps = flatten_image(file, json_conf,None,None,maps)
      else:
         asimg, ascp,maps = flatten_image(file, json_conf,asimg,ascp,maps)
   return(asimg, ascp,maps)


def all_sky_image(file, cal_params, json_conf,pxscale_div,size=5000):
   aw = size 
   ah = size 
   asimg = np.zeros((ah,aw,3),dtype=np.uint8)
   cal_params['imagew'] = aw 
   cal_params['imageh'] = ah 
   cal_params['center_az'] = 0
   cal_params['center_el'] = 90
   cal_params['position_angle'] = 0 
   cal_params['pixscale'] = cal_params['pixscale'] * 1.5 * pxscale_div
   cal_params['x_poly'] = np.zeros(shape=(15,), dtype=np.float64)
   cal_params['y_poly'] = np.zeros(shape=(15,), dtype=np.float64)
   cal_params['x_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
   cal_params['y_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
   cal_params = update_center_radec(file,cal_params,json_conf)
   cat_stars = get_catalog_stars(cal_params)
   for cat_star in cat_stars:
      (name,mag,ra,dec,new_cat_x,new_cat_y) = cat_star
      new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(new_cat_x,new_cat_y,file,cal_params,json_conf)
      new_cat_x = int(new_cat_x)
      new_cat_y = int(new_cat_y)
      if img_el > 0:
         foo = "bar"
         #cv2.circle(asimg,(new_cat_x,new_cat_y), 7, (128,128,128), 10)
         #text = str(int(img_az)) + " " + str(int(img_el))
         #cv2.putText(asimg, str(text),  (int(new_cat_x),int(new_cat_y)), cv2.FONT_HERSHEY_SIMPLEX, .3, (255, 255, 255), 1)
      #else:
      #   print("SKIP:", img_az, img_el)
   return(asimg, cal_params)

def reverse_map(json_conf):
   save_dir = "/mnt/ams2/meteor_archive/CAL/REMAP/"
   asfiles = glob.glob(save_dir + "*asmap*.pickle")
   reverse_map = {}
   cam = 1
   for asf in sorted(asfiles):
      print(asf)
      with open(asf, 'rb') as handle:
         asmap= pickle.load(handle)

      cc = 0
      for ix in range(0,1920):
         for iy in range(0,1080):
            asx,asy = asmap[cc]
            key = str(asx) + "." + str(asy)
            if key not in reverse_map:
               reverse_map[key] = {}
               reverse_map[key]['cams'] = []
               reverse_map[key]['pix'] = []
            else:
               reverse_map[key]['cams'].append(cam)
               reverse_map[key]['pix'].append((ix,iy))
            cc = cc + 1
      cam = cam + 1
   rev_save_file = save_dir + "asmap_reverse.pickle"
   rev_save_js = rev_save_file.replace(".pickle", ".json") 
   with open(rev_save_file, 'wb') as handle:
      pickle.dump(reverse_map, handle, protocol=pickle.HIGHEST_PROTOCOL)
   save_json_file(rev_save_js, reverse_map)
   print(rev_save_js)

def make_gnome_map(file, json_conf,asimg=None,ascp=None,maps=None):
   img = cv2.imread(file)
   small_img = cv2.resize(img, (int(1920/2), int(1080/2)))
   jd = datetime2JD(f_datetime, 0.0)
   hour_angle = JD2HourAngle(jd)
   dist_type = "radial"
   save_dir = "/mnt/ams2/meteor_archive/CAL/REMAP/"
   save_file = save_dir + "map_" + this_cam + ".pickle" 
   as_save_file = save_dir + "asmap_" + this_cam + ".pickle" 

   cal_files= get_cal_files(None, this_cam)
   best_cal_file = cal_files[0][0]
   cal_params = load_json_file(best_cal_file)

   asimg, ascp = all_sky_image(file, cal_params.copy(), json_conf, 5, 1000)

   med_cal = get_med_cal(json_conf, this_cam)
   print("MEDCAL:", med_cal)
   cal_params['center_az'] = med_cal[0]
   cal_params['center_el'] = med_cal[1]
   cal_params['position_angle'] = med_cal[2]
   cal_params['pixscale'] = med_cal[3]

   cal_params = update_center_radec(file,cal_params,json_conf)
   year = datetime.now().strftime("%Y")
   autocal_dir = "/mnt/ams2/meteor_archive/" + STATION_ID + "/CAL/AUTOCAL/" + year + "/solved/"
   mcp_file = autocal_dir + "multi_poly-" + STATION_ID + "-" + this_cam + ".info"
   mcp = load_json_file(mcp_file)
   cal_params['x_poly'] = mcp['x_poly']
   cal_params['y_poly'] = mcp['y_poly']
   cal_params['x_poly_fwd'] = mcp['x_poly_fwd']
   cal_params['y_poly_fwd'] = mcp['y_poly_fwd']

   if True:
      for ix in range(0,img.shape[1]):
         for iy in range(0,img.shape[0]):
            ix2 = ix * 2
            iy2 = iy * 2
            new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(ix,iy,file,cal_params,json_conf )
            new_x = int(new_x) 
            new_y = int(new_y) 

            # MAP PIXEL TO ALL SKY IMG
            #as_az, as_el = radec_to_azel(img_ra,img_dec, f_date_str,json_conf)
            #as_rah,as_dech = AzEltoRADec(cal_params['center_az'],cal_params['center_el'],archive_file,cal_params,json_conf)
            #ra_data = np.ndarray
            #dec_data = np.ndarray

            ra_data = np.zeros(shape=(1,), dtype=np.float64)
            dec_data = np.zeros(shape=(1,), dtype=np.float64)
            ra_data[0] = img_ra
            dec_data[0] = img_dec
            degrees_per_pix = float(ascp['pixscale'])*0.000277778
            px_per_degree = 1 / degrees_per_pix
            #print("PX:", px_per_degree)

            x_data, y_data = cyraDecToXY(ra_data, \
               dec_data,
               jd, json_conf['site']['device_lat'], json_conf['site']['device_lng'], asimg.shape[1], \
               asimg.shape[0], hour_angle, float(ascp['ra_center']),  float(ascp['dec_center']), \
               float(ascp['position_angle']), \
               px_per_degree, \
               ascp['x_poly'], ascp['y_poly'], \
               dist_type, True, False, False)

            #print("ASXY:", ix, iy, img_az, img_el, x_data[0], y_data[0])
            asx = int(x_data[0])
            asy = int(y_data[0])
            asmap.append([asx,asy])
            #remap.append([new_x,new_y])
            if cc % 100000 == 0:
               print("100k pixels done.", cc)
            cc += 1





def flatten_image(file, json_conf,asimg=None,ascp=None,maps=None):

   flat = np.zeros((2920,2080,3),dtype=np.uint8)
#   file = "/mnt/ams2/meteor_archive/AMS1/CAL/AUTOCAL/2020/solved/2020_08_26_08_32_34_000_010005.png"
   img = cv2.imread(file)
   (f_datetime, this_cam, f_date_str,y,m,d, h, mm, s) = convert_filename_to_date_cam(file)
   # NEED JD, hour_angle and dist_type
   jd = datetime2JD(f_datetime, 0.0)
   hour_angle = JD2HourAngle(jd)
   dist_type = "radial"

   save_dir = "/mnt/ams2/meteor_archive/CAL/REMAP/"
   #save_file = save_dir + "map_" + this_cam + "_" + f_date_str[0:10] + ".json" 
   save_file = save_dir + "map_" + this_cam + ".pickle" 
   as_save_file = save_dir + "asmap_" + this_cam + ".pickle" 

   cal_files= get_cal_files(None, this_cam)
   best_cal_file = cal_files[0][0]
   cal_params = load_json_file(best_cal_file)

   med_cal = get_med_cal(json_conf, this_cam)
   print("MEDCAL:", med_cal)
   cal_params['center_az'] = med_cal[0]
   cal_params['center_el'] = med_cal[1]
   cal_params['position_angle'] = med_cal[2]
   cal_params['pixscale'] = med_cal[3]

   cal_params = update_center_radec(file,cal_params,json_conf)
   year = datetime.now().strftime("%Y")
   autocal_dir = "/mnt/ams2/meteor_archive/" + STATION_ID + "/CAL/AUTOCAL/" + year + "/solved/"
   mcp_file = autocal_dir + "multi_poly-" + STATION_ID + "-" + this_cam + ".info"
   mcp = load_json_file(mcp_file)
   cal_params['x_poly'] = mcp['x_poly']
   cal_params['y_poly'] = mcp['y_poly']
   cal_params['x_poly_fwd'] = mcp['x_poly_fwd']
   cal_params['y_poly_fwd'] = mcp['y_poly_fwd']

   #maps = {}

   if asimg is None or ascp is None:
      pxscale_div = 1
      asimg, ascp = all_sky_image(file, cal_params.copy(), json_conf, pxscale_div)


   if cfe(save_file) == 1: 
      if this_cam not in maps :
         maps[this_cam] = {}
         #with open(save_file, 'rb') as handle:
         #   remap = pickle.load(handle)
         with open(as_save_file, 'rb') as handle:
            asmap= pickle.load(handle)
         maps[this_cam]['asmap'] = asmap
      else:
         asmap = maps[this_cam]['asmap']

      new = 0
   else:
      new = 1
      remap = []
      asmap = []
      cc = 0
      for ix in range(0,img.shape[1]):
         for iy in range(0,img.shape[0]):
            new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(ix,iy,file,cal_params,json_conf )
            new_x = int(new_x) + 100
            new_y = int(new_y) + 100

            # MAP PIXEL TO ALL SKY IMG
            #as_az, as_el = radec_to_azel(img_ra,img_dec, f_date_str,json_conf)
            #as_rah,as_dech = AzEltoRADec(cal_params['center_az'],cal_params['center_el'],archive_file,cal_params,json_conf)
            #ra_data = np.ndarray
            #dec_data = np.ndarray

            ra_data = np.zeros(shape=(1,), dtype=np.float64)
            dec_data = np.zeros(shape=(1,), dtype=np.float64)
            ra_data[0] = img_ra
            dec_data[0] = img_dec
            degrees_per_pix = float(ascp['pixscale'])*0.000277778
            px_per_degree = 1 / degrees_per_pix
            #print("PX:", px_per_degree)

            x_data, y_data = cyraDecToXY(ra_data, \
               dec_data, 
               jd, json_conf['site']['device_lat'], json_conf['site']['device_lng'], asimg.shape[1], \
               asimg.shape[0], hour_angle, float(ascp['ra_center']),  float(ascp['dec_center']), \
               float(ascp['position_angle']), \
               px_per_degree, \
               ascp['x_poly'], ascp['y_poly'], \
               dist_type, True, False, False)

            #print("ASXY:", ix, iy, img_az, img_el, x_data[0], y_data[0])
            asx = int(x_data[0])
            asy = int(y_data[0])
            asmap.append([asx,asy])     
            #remap.append([new_x,new_y])
            if cc % 100000 == 0:
               print("100k pixels done.", cc)
            cc += 1
   cc = 0
   print("map done. re-drawing.")


   for ix in range(0,img.shape[1]):
      for iy in range(0,img.shape[0]):
         #cc_half = int(cc * 2)
         #new_x, new_y = remap[cc]
         asx, asy= asmap[cc]
         #flat[new_y,new_x] = img[iy,ix]
         #print("ASIMG:",  asimg[asy,asx])
         #if False:
         if asimg[asy,asx][0] != 0 :
            done_already = 1
            #ov = asimg[asy,asx]
            #nv = img[iy,ix]
            #val0 = int(np.mean([ov[0],nv[0]]))
            #val1 = int(np.mean([ov[1],nv[1]]))
            #val2 = int(np.mean([ov[2],nv[2]]))
            #asimg[asy,asx] = [val0,val1,val2] 
         else:
            asimg[asy,asx] = img[iy,ix]
         if cc % 100000 == 0:
            print("100k pixels done.")
         cc += 1
         
   if cfe(save_dir,1) == 0:
      os.makedirs(save_dir)
   if new == 1:
      save_json_file(save_file, remap) 
      save_json_file(as_save_file, asmap) 
      with open(save_file, 'wb') as handle:
         pickle.dump(remap, handle, protocol=pickle.HIGHEST_PROTOCOL)
      with open(as_save_file, 'wb') as handle:
         pickle.dump(asmap, handle, protocol=pickle.HIGHEST_PROTOCOL)

      print("Saved:", save_file) 
   return(asimg, ascp,maps)


def guess_cal(cal_file, json_conf, cal_params = None):
   print("GUESS", cal_file)
   cp_file = cal_file.replace(".png", "-calparams.json")
   (f_datetime, this_cam, f_date_str,y,m,d, h, mm, s) = convert_filename_to_date_cam(cal_file)
   img = cv2.imread(cal_file)
   orig_img = img.copy()
   gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
   stars = get_image_stars(cal_file, gray_img.copy(), json_conf, 0)
   for star in stars:
      x,y,intense = star
      cv2.circle(img,(x,y), 7, (128,128,128), 1)
   
   cv2.imshow('pepe', img)
   cv2.waitKey(30)
   print("GUSS CAM:", this_cam)
   az_guess, el_guess, pix_guess, pos_ang_guess = get_cam_best_guess(this_cam, json_conf)
   if "src.jpg" in cal_file:
      cp_file = cal_file.replace("-src.jpg", "-calparams.json")
   print("CP FILE:", cp_file)
   if cal_params is not None:
   #if cfe(cp_file) == 1:
      if az_guess == 0 and el_guess == 0:
         cp_file = cp_file.replace("-src", "") 
         print("CP FILE:", cp_file)
         cp = load_json_file(cp_file)
         az_guess = cp['center_az']
         el_guess = cp['center_el']
         pix_guess = cp['pixscale']
         pos_ang_guess = cp['position_angle']
         #cp = update_center_radec(file,cal_params,json_conf)
   else: 
      if az_guess == 0 and el_guess == 0:
         dc = get_default_calib(cp_file,json_conf)
         if dc is not None:
            az_guess, el_guess, pos_ang_guess, pix_guess = default_calib = dc
         else:
            az_guess = float(input("Enter the best guess for AZ: ") )
            el_guess = float(input("Enter the best guess for EL: ") )
            pos_ang_guess = float(input("Enter the best guess for POS ANG: ") )
            pix_guess = float(input("Enter the best guess for PIX SCALE: ") )
   
   guessing = 0
   az_guess, el_guess, pix_guess, pos_ang_guess = float( az_guess), float(el_guess), float(pix_guess), float(pos_ang_guess)
   
   gimg, avg_res, last_cal = make_guess(az_guess, el_guess, pix_guess, pos_ang_guess, this_cam, cal_file, orig_img.copy(), gray_img, stars, json_conf)
   ss = 1 
   while guessing == 0:
      print("RES:", avg_res)
      print("Waiting for input.", ss)
      key = cv2.waitKey(0)

      if key == ord('+'):
         ss = ss + .1
         print("SS:", ss)
      if key == ord('-'):
         ss = ss - .1
         print("SS:", ss)
      if key == ord('a'):
         az_guess = az_guess - ss
         gimg, avg_res, last_cal = make_guess(az_guess, el_guess, pix_guess, pos_ang_guess, this_cam, cal_file, orig_img.copy(), gray_img, stars, json_conf)
      if key == ord('f'):
         az_guess = az_guess + ss
         gimg, avg_res, last_cal = make_guess(az_guess, el_guess, pix_guess, pos_ang_guess, this_cam, cal_file, orig_img.copy(), gray_img, stars, json_conf)
      if key == ord('s'):
         el_guess = el_guess - ss
         gimg, avg_res, last_cal = make_guess(az_guess, el_guess, pix_guess, pos_ang_guess, this_cam, cal_file, orig_img.copy(), gray_img, stars, json_conf)
      if key == ord('d'):
         el_guess = el_guess + ss 
         gimg, avg_res, last_cal = make_guess(az_guess, el_guess, pix_guess, pos_ang_guess, this_cam, cal_file, orig_img.copy(), gray_img, stars, json_conf)
      if key == ord('o'):
         pos_ang_guess = pos_ang_guess - ss 
         gimg, avg_res, last_cal = make_guess(az_guess, el_guess, pix_guess, pos_ang_guess, this_cam, cal_file, orig_img.copy(), gray_img, stars, json_conf)
      if key == ord('p'):
         pos_ang_guess = pos_ang_guess + ss
         gimg, avg_res, last_cal = make_guess(az_guess, el_guess, pix_guess, pos_ang_guess, this_cam, cal_file, orig_img.copy(), gray_img, stars, json_conf)
      if key == ord('z'):
         pix_guess = pix_guess - ss 
         gimg, avg_res, last_cal = make_guess(az_guess, el_guess, pix_guess, pos_ang_guess, this_cam, cal_file, orig_img.copy(), gray_img, stars, json_conf)
      if key == ord('x'):
         pix_guess = pix_guess + ss
         gimg, avg_res, last_cal = make_guess(az_guess, el_guess, pix_guess, pos_ang_guess, this_cam, cal_file, orig_img.copy(), gray_img, stars, json_conf)

      if key == 27 or key == ord('q'):
         print("DONE!")
         guessing = 1
      if key == ord('m'):
         print("Minimize with these values!")
         guessing = 1
         cp = minimize_fov(cal_file, last_cal, cal_file,orig_img.copy(),json_conf )
      print("Got input.")
      print("AZ:", az_guess)    
      print("EL:", el_guess)    
      print("POS:", pos_ang_guess)    

   save_yn = input("Enter Y to save: ") 
   if save_yn == "Y" or save_yn == "y" or "y" in save_yn or "Y" in save_yn:
      last_cal['x_poly'] = cp['x_poly'].tolist()
      last_cal['y_poly'] = cp['y_poly'].tolist()
      last_cal['y_poly_fwd'] = cp['y_poly_fwd'].tolist()
      last_cal['x_poly_fwd'] = cp['x_poly_fwd'].tolist()
      save_json_file(cp_file, last_cal)
      print("saved:", cp_file)
      time.sleep(5)
   else:
      print("NOT SAVED!", save_yn)
   return(last_cal)

def min_fov(cp_file, json_conf):
   src_file = cp_file.replace("-calparams.json", "-src.jpg")
   if cfe(src_file) == 0:
      get_cal_img(src_file)
   cal_img = cv2.imread(src_file)
   gray_cal_img = cv2.cvtColor(cal_img, cv2.COLOR_BGR2GRAY)
   cal_params = load_json_file(cp_file)
   if "user_stars" not in cal_params:
      cal_params['user_stars'] = get_image_stars(cp_file, gray_cal_img.copy(), json_conf, 0)
   elif len(cal_params['user_stars'][0]) == 2:
      cal_params['user_stars'] = get_image_stars(cp_file, gray_cal_img.copy(), json_conf, 0)
   if "user_stars_v" not in cal_params:
      cp['user_stars_v'] = 1
   save_json_file(cp_file, cal_params)
   cp = minimize_fov(cp_file, cal_params, cp_file ,cal_img,json_conf )

def make_guess(az_guess, el_guess, pix_guess, pos_ang_guess, this_cam, cal_file, img, gray_img, stars, json_conf):

   temp_cal_params = {}
   temp_cal_params['position_angle'] = pos_ang_guess
   temp_cal_params['center_az'] = az_guess 
   temp_cal_params['center_el'] = el_guess
   temp_cal_params['pixscale'] = pix_guess
   temp_cal_params['device_lat'] = json_conf['site']['device_lat']
   temp_cal_params['device_lng'] = json_conf['site']['device_lng']
   temp_cal_params['device_alt'] = json_conf['site']['device_alt']
   temp_cal_params['imagew'] = 1920
   temp_cal_params['user_stars'] = stars
   temp_cal_params['imageh'] = 1080
   temp_cal_params['x_poly'] = np.zeros(shape=(15,), dtype=np.float64)
   temp_cal_params['y_poly'] = np.zeros(shape=(15,), dtype=np.float64)
   temp_cal_params['x_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
   temp_cal_params['y_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
   cal_params = update_center_radec(cal_file,temp_cal_params,json_conf)

   cp = pair_stars(temp_cal_params, cal_file, json_conf, gray_img)
   cp2, bad_stars,marked_img = eval_cal(cal_file,json_conf,temp_cal_params,gray_img)

   for star in cp['cat_image_stars']:
      dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,bp = star
      cv2.circle(img,(new_cat_x,new_cat_y), 7, (128,128,128), 1)
      cv2.rectangle(img, (new_cat_x-2, new_cat_y-2), (new_cat_x + 2, new_cat_y + 2), (0, 0, 128), 1)

   std_dist, avg_dist = calc_starlist_res(cp['cat_image_stars'])
   return(img, avg_dist, cp)

def blind_solve_meteors(day,json_conf,cam=None):

   pos_files = []
   mds = sorted(glob.glob("/mnt/ams2/meteors/" + day +"*"), reverse=True)
   all_meteor_imgs = []
   auto_cal_dir = "/mnt/ams2/meteor_archive/" + STATION_ID + "/CAL/AUTOCAL/" + day[0:4] + "/"  
   if cfe(auto_cal_dir,1) == 0:
      os.makedirs(auto_cal_dir)

   for md in mds[0:90]:
      if cam is None:
         jsfs = glob.glob(md + "/*.json")
      else:
         jsfs = glob.glob(md + "/*" + cam + "*.json")
      for jsf in jsfs:
         if "reduced" in jsf:
            continue
         print(jsf)
         try:
            js = load_json_file(jsf)
         except:
            print("BAD JSON:", jsf)
            continue
         if True:
            if "hd_trim" in js:
               if js['hd_trim'] == 0 or js['hd_trim'] is None:
                  continue
               fn, dir = fn_dir(js['hd_trim']) 
               js['hd_trim'] = md + "/" + fn
               stack_file = js['hd_trim'].replace(".mp4", "-stacked.png")
               if cfe(stack_file) == 0:
                  print(stack_file, " not found")
               
               if cfe(stack_file) == 1:
                  all_meteor_imgs.append(stack_file)

                  cal_img = cv2.imread(stack_file)
                  temp_img = cal_img.copy()
                  gray_cal_img = cv2.cvtColor(cal_img, cv2.COLOR_BGR2GRAY)
                  stars = get_image_stars(stack_file, gray_cal_img.copy(), json_conf, 0)
                  if SHOW == 1:
                     cv2.imshow('pepe', temp_img)
                     cv2.waitKey(30)
                  print("STARS:", len(stars))
                  if len(stars) >= CAL_STAR_LIMIT:
                     mfn, mdir = fn_dir(stack_file) 
                     year = mfn[0:4]
                     pos_files.append((stack_file, len(stars)))
                     #cmd = "cp " + stack_file + " /mnt/ams2/meteor_archive/" + STATION_ID + "/CAL/AUTOCAL/" + year + "/"  
                     #print(cmd)
                     #os.system(cmd)

   # now based on when the last cal for each cam was decide if we should blind solve it. 
   all_cams = get_all_cams(json_conf)
   cal_files= get_cal_files(None, cam)
   good_cals = {}
   for cam in all_cams:
      good_cals[cam] = []


   for mfile, stars in pos_files:
      (f_datetime, mcam, f_date_str,y,m,d, h, mm, s) = convert_filename_to_date_cam(mfile)
      for cal_file, td in cal_files:
         (c_datetime, ccam, c_date_str,cy,cm,cd, ch, cmm, cs) = convert_filename_to_date_cam(cal_file)
         if ccam == mcam:
            tdiff = f_datetime - c_datetime
            tdiff = tdiff.total_seconds()
            if tdiff < (86400 * 3) or (tdiff < 0 and tdiff > (-1*86400*3)):
               print("WE HAVE A CALIBRATION WITHIN THE LAST 3 DAYS FOR THIS CAM. SKIP!", ccam, mcam, mfile, tdiff, f_datetime, c_datetime )
               good_cals[mcam].append(cal_file)

   print("These cams have had a calibration within the last 3 days.")
   for cam in good_cals:
      print(cam, len(set(good_cals[cam])))

   pos_files = sorted(pos_files, key=lambda x: x[1], reverse=True)
   for mfile, stars in pos_files:
      (f_datetime, mcam, f_date_str,y,m,d, h, mm, s) = convert_filename_to_date_cam(mfile)
      if len(set(good_cals[mcam])) <= 15:
         if stars > CAL_STAR_LIMIT:
            cmd = "cp " + mfile + " /mnt/ams2/meteor_archive/" + STATION_ID + "/CAL/AUTOCAL/" + year + "/"  
            print("COPY A FILE FOR CALIB ", stars, cmd)
            os.system(cmd)
            good_cals[mcam].append((mfile, stars))
               
      
def get_all_cams(json_conf):
   all_cams = []
   for cam in json_conf['cameras']:
      cam_id = json_conf['cameras'][cam]['cams_id']
      all_cams.append(cam_id)
   return(all_cams)

def get_cam_best_guess(this_cam, json_conf):
   for cam in json_conf['cameras']:
      cam_id = json_conf['cameras'][cam]['cams_id']
      if cam_id == this_cam:
         if "best_guess" in json_conf['cameras'][cam]:
             return(json_conf['cameras'][cam]['best_guess'])
   return(0,0,0,0)

def super_cal(json_conf):
   #os.system("./Process.py ca")
   refit_all(json_conf)
   for cam in json_conf['cameras']:
      cams_id = json_conf['cameras'][cam]['cams_id']
      os.system("./Process.py deep_cal " + cams_id)
   refit_all(json_conf)

def check_all(json_conf, cam_id=None):
   if cam_id is not None:
      cams = [cam_id]
   else:
      cams = []
      for cam in json_conf['cameras']:

         cams_id = json_conf['cameras'][cam]['cams_id']
         cams.append(cams_id)
   print("CAMS:", cams)

   for cams_id in cams:

      cal_files= get_cal_files(None, cams_id)
      temp = sorted(cal_files, key=lambda x: x[0], reverse=True)
      print("CAL FILES:", temp)
      for data in temp:
         cal_file, xxx = data
         cp = load_json_file(cal_file)
         print (cal_file, cp['total_res_px'], cp['total_res_deg'])

def refit_all(json_conf, cam_id=None, type="all"):
   if cam_id is not None:
      cams = [cam_id]
   else:
      cams = []
      for cam in json_conf['cameras']:

         cams_id = json_conf['cameras'][cam]['cams_id']
         cams.append(cams_id)
   print("CAMS:", cams)

   for cams_id in cams:

      cal_files= get_cal_files(None, cams_id)

      temp = sorted(cal_files, key=lambda x: x[0], reverse=True)
      print("CAL FILES:", temp)
      for data in temp:
         redo = 0
         run = 0
         cal_file, xxx = data
         cp = load_json_file(cal_file)

         if "total_res_deg" not in cp:
            cp['total_res_deg'] = 999
         if "total_res_px" not in cp:
            cp['total_res_px'] = 9999
         elif "refit" not in cp:
            cp['refit'] = 1
         if type == "all":
            run = 1
         if run == 1:
            cmd = "./Process.py refit " + cal_file
            print(cmd)
            os.system(cmd)
               #exit()
   os.system("cd ../pythonv2/; ./autoCal.py cal_index")

def refit_fov(cal_file, json_conf):
   if "png" in cal_file:
      cal_file = cal_file.replace(".png", "-calparams.json")
   (f_datetime, cam, f_date_str,year,m,d, h, mm, s) = convert_filename_to_date_cam(cal_file)
   cal_params = load_json_file(cal_file)
   image_file = cal_file.replace("-calparams.json", ".png")

   print("START CP VALS:", cal_params['center_az'], cal_params['center_el'], cal_params['position_angle'], cal_params['pixscale'])

   img = cv2.imread(image_file)

   mask_file = MASK_DIR + cam + "_mask.png"
   if cfe(mask_file) == 1:
      mask_img = cv2.imread(mask_file)
      mask_img = cv2.resize(mask_img, (1920,1080))
   else:
      mask_img = None
   if mask_img is not None:
      img = cv2.subtract(img, mask_img)
      print("MASK SUBTRACTED.")

   print("REFIT CAM:", cam)
   #masks = get_masks(cam, json_conf,1)
   #print("MASKS:", masks)
   #img = mask_frame(img, [], masks, 5)


   gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
   cal_params['user_stars'] = get_image_stars(cal_file, img.copy(), json_conf, 0)

   print("STARTING RA/DEC:", cal_params['ra_center'], cal_params['dec_center'], cal_params['total_res_px'])
   cal_params = update_center_radec(cal_file,cal_params,json_conf)
   print("AFTER UPDATE RA/DEC:", cal_params['ra_center'], cal_params['dec_center'], cal_params['total_res_px'])
   ocp = dict(cal_params)
   cal_params['ra_center'] = float( cal_params['ra_center'])
   cal_params['dec_center'] = float( cal_params['dec_center'])

   cal_params = pair_stars(cal_params, image_file, json_conf, gray_img)
   print("FILE RES vs RECALC RES:", ocp['total_res_px'], cal_params['total_res_px'])
   print("OCP:", ocp['ra_center'], ocp['dec_center'], ocp['position_angle'], ocp['pixscale'], ocp['total_res_px'])
   #for star in ocp['cat_image_stars']:
   #   print(star)
   print("NEW CP:", cal_params['ra_center'], cal_params['dec_center'], cal_params['position_angle'], cal_params['pixscale'], cal_params['total_res_px'])
   #for star in ocp['cat_image_stars']:
      #print(star)
   #cont = input("continue...")
   #exit()
   usc = len( cal_params['user_stars'])
   cisc = len( cal_params['cat_image_stars'])
   usc_perc =  cisc / usc
   print("USC:", cisc, usc, usc_perc)
   print("STARTING RES:", cal_params['total_res_px'] )
   if usc_perc < .4 or cal_params['total_res_px'] > 4:
      bcp, acp = get_cal_params(cal_file)
      acp['user_stars'] = cal_params['user_stars']
      bcp['user_stars'] = cal_params['user_stars']
      acp['cat_image_stars'] = cal_params['cat_image_stars']
      bcp['cat_image_stars'] = cal_params['cat_image_stars']
      print(bcp['pixscale'])
      print(acp['pixscale'])
      data = [cal_file, bcp['center_az'], bcp['center_el'], bcp['position_angle'], bcp['pixscale'], len(bcp['user_stars']), len(bcp['cat_image_stars']), cal_params['total_res_px'],0]  
      tcp , bad_stars, marked_img = test_cal(cal_file, json_conf, bcp, img, data)
      print("BEFORE/CUR:", tcp['total_res_px'],  cal_params['total_res_px'])
      if tcp['total_res_px'] < cal_params['total_res_px']:
         cal_params = dict(tcp)
         print("BCP BETTER")
      data = [cal_file, acp['center_az'], acp['center_el'], acp['position_angle'], acp['pixscale'], len(acp['user_stars']), len(acp['cat_image_stars']), cal_params['total_res_px'],0]  
      tcp , bad_stars, marked_img = test_cal(cal_file, json_conf, acp, img, data)
      print("AFTER/CUR:", tcp['total_res_px'],  cal_params['total_res_px'])
      if tcp['total_res_px'] < cal_params['total_res_px']:
         cal_params = dict(tcp)
         print("ACP BETTER")

   if cal_params['total_res_px'] > 4:
      print("Not enough stars map or res px too high? Maybe a bad position angle or astrometry vars?")
      cp = dict(cal_params)
      cpr = optimize_var(cal_file,json_conf,"center_az",cal_params,img)

      if cpr is not None:
         print("CAL VALS:", cal_file, cpr['total_res_px'] ) 
         cp = dict(cpr)

      cpr = optimize_var(cal_file,json_conf,"center_el",cp,img)
      if cpr is not None:
         print("CAL VALS:", cal_file, cpr['total_res_px'] ) 
         cp = dict(cpr)
      
      cpr = optimize_var(cal_file,json_conf,"position_angle",cp,img)
      if cpr is not None:
         print("CAL VALS:", cal_file, cp['total_res_px'] ) 
         cp = dict(cpr)

      cpr = optimize_var(cal_file,json_conf,"pixscale",cp,img)
      if cpr is not None:
         print("CAL VALS:", cal_file, cp['total_res_px'] ) 
         cp = dict(cpr)
      new_cal_params = dict(cp)
      # get/test a cal file before / after this one

      if new_cal_params['total_res_px'] < ocp['total_res_px']:
         print("SAVE NEWER CP ITS BETTER THAN ORIGINAL FILE")
      
         print("ORIG:", ocp['az_center'], ocp['el_center'], ocp['position_angle'], ocp['pixscale'])
         print("NEW:", new_cal_params['az_center'], new_cal_params['el_center'], new_cal_params['position_angle'], new_cal_params['pixscale'])
         save_json_file(cal_file, new_cal_params)
         cal_params = dict(new_cal_params)
         exit()
      else:
          print("Orig better", ocp['total_res_px'], new_cal_params['total_res_px'])
          save_json_file(cal_file, new_cal_params)
          cal_params = dict(new_cal_params)
          #cont = input("continue...")
          #exit()

      if cal_params['total_res_px'] > 10:
         print("this file is bad and needs to be deleted or restarted.")
         exit()
         # try to resolve the image
         temp_dir = "/mnt/ams2/cal/temp/"
         if cfe("/mnt/ams2/cal/temp/", 1) == 0:
            os.makedirs("/mnt/ams2/cal/temp")
         cmd = "cp " + image_file + " /mnt/ams2/cal/temp/"
         fn, dir = fn_dir(image_file)
         temp_cal = temp_dir + fn
         print(cmd)
         os.system(cmd)
         plate_image, star_points = make_plate_image(img.copy(), cal_params['user_stars'])

         plate_file = temp_cal.replace(".png", ".jpg")
         cv2.imwrite(plate_file, plate_image)

         status, cal_params, wcs = solve_field(plate_file, cal_params['user_stars'], json_conf)
         if status == 0:
            exit()


   data = [cal_file, cal_params['center_az'], cal_params['center_el'], cal_params['position_angle'], cal_params['pixscale'], len(cal_params['user_stars']), len(cal_params['cat_image_stars']), cal_params['total_res_px'],0]  
   #cal_params, bad_stars, marked_img = test_cal(cal_file, json_conf, cal_params, img, data)
   #save_json_file(cal_file, cal_params)
   print("SAVED:", cal_file)
   for star in cal_params['cat_image_stars']:
      print(star)
   #exit()
   #print(bad_stars)

   autocal_dir = "/mnt/ams2/meteor_archive/" + STATION_ID + "/CAL/AUTOCAL/" + year + "/solved/"
   mcp_file = autocal_dir + "multi_poly-" + STATION_ID + "-" + cam + ".info"
   if cfe(mcp_file) == 1:
      mcp = load_json_file(mcp_file)
   else:
      mcp = None 
      print(mcp_file)
      #xxx = input("Wait.")

   if mcp is not None:
      if mcp != 0:
         cal_params['x_poly'] = mcp['x_poly']
         cal_params['y_poly'] = mcp['y_poly']
         cal_params['x_poly_fwd'] = mcp['x_poly_fwd']

         cal_params['y_poly_fwd'] = mcp['y_poly_fwd']

   if cal_params['position_angle'] <= 0 or cal_params['total_res_px'] >= 10:
      print("BAD POS.")
      #cal_params = optimize_matchs(cal_file,json_conf,cal_params,img)
      #az_guess, el_guess, pos_ang_guess, pix_guess = get_cam_best_guess(cam, json_conf)
      az_guess = 0
      if az_guess != 0:
         cal_params['center_az'] = float(az_guess)
         cal_params['center_el'] = float(el_guess)
         cal_params['position_angle'] = float(pos_ang_guess )
         cal_params['pixscale'] = float(pix_guess )
         cal_params = update_center_radec(cal_file,cal_params,json_conf)
         cal_params['ra_center'] = float( cal_params['ra_center'])
         cal_params['dec_center'] = float( cal_params['dec_center'])
 
 
         print("GUESS:", az_guess, el_guess, pos_ang_guess, pix_guess, cal_params['total_res_px'])
         print("GUESS:", cal_params)
      #exit()

   save_json_file(cal_file, cal_params)
   cal_params = minimize_fov(cal_file, cal_params, image_file,img,json_conf )
   cal_params['close_stars']  = cal_params['cat_image_stars']
   trash_stars, cal_params['total_res_px'], cal_params['total_res_deg'] = cat_star_report(cal_params['cat_image_stars'], 4)
   save_json_file(cal_file, cal_params)
   cmd = "./AzElGrid.py az_grid " + cal_file
   os.system(cmd)
   print(cmd)

def minimize_fov(cal_file, cal_params, image_file,img,json_conf ):
   orig_cal = dict(cal_params)
   #this_poly = [.25,.25,.25,.25]

   cal_params = update_center_radec(cal_file,cal_params,json_conf)
   std_dist, avg_dist = calc_starlist_res(cal_params['cat_image_stars'])
   az = np.float64(orig_cal['center_az'])
   el = np.float64(orig_cal['center_el'])
   pos = np.float64(orig_cal['position_angle'])
   pixscale = np.float64(orig_cal['pixscale'])
   x_poly = np.float64(orig_cal['x_poly'])
   y_poly = np.float64(orig_cal['y_poly'])



   this_poly = np.zeros(shape=(4,), dtype=np.float64)
   #this_poly = [.1,.1,.1,.1]
   res = scipy.optimize.minimize(reduce_fov_pos, this_poly, args=( az,el,pos,pixscale,x_poly, y_poly, image_file,img,json_conf, cal_params['cat_image_stars'],cal_params['user_stars'],1,SHOW), method='Nelder-Mead')
   #print("RESULT:", res)
   adj_az, adj_el, adj_pos, adj_px = res['x']
  
   new_az = az + (adj_az*az)
   new_el = el + (adj_el*el)
   new_position_angle = pos + (adj_pos*pos)
   new_pixscale = pixscale + (adj_px*pixscale)

   #print("AZ/NEW AZ:", az, new_az, float(this_poly[0]) * az ** 2)

   cal_params['center_az'] =  new_az 
   cal_params['center_el'] =  new_el
   cal_params['position_angle'] =  new_position_angle
   cal_params['pixscale'] =  new_pixscale
   cal_params = update_center_radec(cal_file,cal_params,json_conf)

   #print("BEFORE", orig_cal['ra_center'], orig_cal['dec_center'], orig_cal['center_az'], orig_cal['center_el'], orig_cal['position_angle'], orig_cal['pixscale'])
   #print("AFTER", cal_params['ra_center'], cal_params['dec_center'], cal_params['center_az'], cal_params['center_el'], cal_params['position_angle'], cal_params['pixscale'])
   if "fov_fit" not in cal_params:
      cal_params['fov_fit'] = 1 
   else:
      cal_params['fov_fit'] += 1 
   if len(img.shape) > 2:
      gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
   else:
      gray_img = img
   cp = pair_stars(cal_params, image_file, json_conf, gray_img)
   trash_stars, res_px,res_deg = cat_star_report(cp['cat_image_stars'], 4)

   print("TOTAL RES:", cal_params['position_angle'], res_px )
   cp['total_res_px'] = res_px 
   cp['total_res_deg'] = res_deg 

   return(cal_params)

def plot_user_stars(img, cal_params, cp_file, json_conf, wait=30):
   stars = cal_params['user_stars']
   new_cp = update_center_radec(cp_file,cal_params,json_conf)
   debug_txt = "RA/DEC: " + str(cal_params['ra_center'])[0:6]  + " / " + str(cal_params['dec_center'])[0:6] 
   debug_txt2 = "NEW RA/DEC: " + str(new_cp['ra_center'])[0:6]  + " / " + str(new_cp['dec_center'])[0:6] 
   debug_txt += " AZ: " + str(cal_params['center_az'])[0:6] + "EL : " + str(cal_params['center_el'])[0:6]
   debug_txt += " POS: " + str(cal_params['position_angle'])[0:6]
   debug_txt += " PX SCALE: " + str(cal_params['pixscale'])[0:6]
   temp_img = img.copy()
   cv2.putText(temp_img, str(debug_txt),  (int(50),int(50)), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 1)
   cv2.putText(temp_img, str(debug_txt2),  (int(50),int(100)), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 1)
   cv2.putText(temp_img, str(cp_file),  (int(50),int(150)), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 1)
   for star in stars:
      x,y,star_int = star
      cv2.circle(temp_img,(x,y), 7, (128,128,128), 1)
   return(temp_img)

def plot_cat_image_stars(img, cal_params, cp_file,json_conf):
   cat_image_stars = cal_params['cat_image_stars']
   temp_img = img.copy()
   new_cp = update_center_radec(cp_file,cal_params,json_conf)
   debug_txt = "RA/DEC: " + str(cal_params['ra_center'])[0:6]  + " / " + str(cal_params['dec_center'])[0:6] 
   debug_txt2 = "NEW RA/DEC: " + str(new_cp['ra_center'])[0:6]  + " / " + str(new_cp['dec_center'])[0:6] 
   debug_txt += " AZ: " + str(cal_params['center_az'])[0:6] + "EL : " + str(cal_params['center_el'])[0:6]
   debug_txt += "POS: " + str(cal_params['position_angle'])[0:6]
   debug_txt += "PX SCALE: " + str(cal_params['pixscale'])[0:6]
   cv2.putText(temp_img, str(debug_txt),  (int(50),int(50)), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 1)
   cv2.putText(temp_img, str(debug_txt2),  (int(50),int(100)), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 1)
   cv2.putText(temp_img, str(cp_file),  (int(50),int(150)), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 1)
   for star in cat_image_stars:
      dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,bp = star
      cv2.circle(temp_img,(six,siy), 7, (128,128,128), 1)
      cv2.rectangle(temp_img, (new_cat_x-2, new_cat_y-2), (new_cat_x + 2, new_cat_y + 2), (128, 128, 128), 1)
   return(temp_img)   

def print_rigid(cp):
   print("RA/DEC:", cp['ra_center'], cp['dec_center'])
   print("POS:", cp['position_angle'])
   print("PX:", cp['pixscale'])

def deep_cal_report(cam, json_conf):
   df = datetime.now().strftime("%Y_%m_%d_%H_%M_000_")
   year = datetime.now().strftime("%Y")
   dummy_file = df + "_cam.png"
   cal_files= get_cal_files(None, cam)
   print("CFs:", cal_files)
   autocal_dir = "/mnt/ams2/meteor_archive/" + STATION_ID + "/CAL/AUTOCAL/" + year + "/solved/"
   mcp_file = autocal_dir + "multi_poly-" + STATION_ID + "-" + cam + ".info"
   if cfe(mcp_file) == 1:
      mcp = load_json_file(mcp_file)
   else:
      mcp = None 
 
   #mcp = None 
   all_cal_files = []
   for cal,df in cal_files:
      cal_file = cal
      cp = load_json_file(cal)
      cal_img_file = cal.replace("-calparams.json", ".png")
      if cfe(cal_img_file) == 0:
         continue
      cal_img = cv2.imread(cal_img_file)
      gray_cal_img = cv2.cvtColor(cal_img, cv2.COLOR_BGR2GRAY)

      if "user_stars" not in cp:
         cp['user_stars'] = get_image_stars(cal, gray_cal_img.copy(), json_conf, 0)
         print("GET USER STARS1")
         exit()
      else:
         if len(cp['user_stars']) < 5:
            cp['user_stars'] = get_image_stars(cal, gray_cal_img.copy(), json_conf, 0)
            print("GET USER STARS2")
            exit()
      cp = pair_stars(cp, cal_file, json_conf, cal_img)

      before_std_dist, before_avg_dist = calc_starlist_res(cp['cat_image_stars'])
      if mcp is not None:
      #if False:
         if mcp != 0:
            cp['x_poly'] = mcp['x_poly']
            cp['y_poly'] = mcp['y_poly']
            cp['x_poly_fwd'] = mcp['x_poly_fwd']
            cp['y_poly_fwd'] = mcp['y_poly_fwd']

      #cp['x_poly'] = np.zeros(shape=(15,), dtype=np.float64)
      #cp['y_poly'] = np.zeros(shape=(15,), dtype=np.float64)
      #cp['x_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
      #cp['y_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
      
      cp = pair_stars(cp, cal_img_file, json_conf, gray_cal_img)

      std_dist, avg_dist = calc_starlist_res(cp['cat_image_stars'])
      if avg_dist < 3:
         all_cal_files.append((cal, avg_dist))
         continue

      before_std_dist, before_avg_dist = calc_starlist_res(cp['cat_image_stars'])

      if SHOW == 1:
         star_image = draw_star_image(cal_img, cp['cat_image_stars'], cp) 
         cv2.imshow('pepe', star_image)
         cv2.waitKey(100)
      if CAL_MOVIE == 1:
         star_image = draw_star_image(cal_img, cp['cat_image_stars'], cp) 
         fn, dir = fn_dir(cal_img_file)
         cv2.imwrite("tmp_vids/" + fn, star_image)


      if len(cp['cat_image_stars']) > 0:
         cat_match = len(cp['user_stars']) / len(cp['cat_image_stars'])
      else:
         cat_match = 0
      #plot_cat_image_stars(gray_cal_img, cp, cal, json_conf)
      if cat_match < .5:
         print("PROB:", cal )
         print("IMAGE STARS TO CAT STARS VERY LOW, COULD BE A BAD FILE.", len(cp['user_stars']), len(cp['cat_image_stars']), cat_match)
         exit()

      cal_img_file = cal.replace("-calparams.json", ".png")
      if cfe(cal_img_file) == 0:
         continue
      else:
         cal_img = cv2.imread(cal_img_file)
      print("CAL IMAGE:", cal_img.shape) 
      #if "cat_image_stars" not in cp:
      #   stars_from_cat,cp = get_image_stars_with_catalog(cal, cal_img, cp, json_conf, None,  0)
      #   plot_cat_image_stars(gray_cal_img, cp['cat_image_stars'])

      if mcp is not None:
         #cp = load_json_file(cal)
         if mcp != 0:
            cp['x_poly'] = mcp['x_poly']
            cp['y_poly'] = mcp['y_poly']
            cp['x_poly_fwd'] = mcp['x_poly_fwd']
            cp['y_poly_fwd'] = mcp['y_poly_fwd']
            #save_json_file(cal, cp)
            grid = cal.replace("-calparams.json", "-azgrid.png")
         
            cmd = "./AzElGrid.py az_grid " + cal 
            print(cmd)
            os.system(cmd)

         if cfe(grid) == 0:
            grid = grid.replace("-stacked", "")
        

      std_dist, avg_dist = calc_starlist_res(cp['cat_image_stars'])
      fov_done = 0
      if 'fov_fit' in cp:
         print("File FOV fitted ", cp['fov_fit'], " times")
         if cp['fov_fit'] > 33:
            print("File already FOV fitted ", cp['fov_fit'], " times")
            fov_done = 1
      else:
         print("File FOV has not been fitted yet.")
      if fov_done == 0:
         print(cal)
         print("BEFORE CP:", cp['center_az'], cp['center_el'], cp['position_angle'], cp['pixscale'], cal_img.shape)
 
         #cp = minimize_fov(cal, cp, cal,cal_img,json_conf )
         #save_json_file(cal, cp)
         print("AFTER CP:", cp['center_az'], cp['center_el'], cp['position_angle'], cp['pixscale'])
         print("SAVED CAL FILE:", cal)

      if SHOW == 1:
         star_image = draw_star_image(cal_img, cp['cat_image_stars'], cp) 
         cv2.imshow('pepe', star_image)
         cv2.waitKey(40)
      if CAL_MOVIE == 1:
         star_image = draw_star_image(cal_img, cp['cat_image_stars'], cp) 
         fn, dir = fn_dir(cal_img_file)
         cv2.imwrite("tmp_vids/" + fn, star_image)


      std_dist, avg_dist = calc_starlist_res(cp['cat_image_stars'])
      all_cal_files.append((cal, avg_dist))

   for cf in all_cal_files:
      print(cf)
   print("END DEEP CAL REPORT.")
   return(all_cal_files)

def deep_calib(cam, json_conf):
   """
      using an already calibrated camera, seek existing images (meteors, cal images, other? TL) 
      and register those stars into 1 massve star database that spans many days / images
      each star entry must log the star name, image x,y, cal_params at that time (ra,dec etc), time of image
   """
   data,ci_data = review_cals(json_conf, cam)

   #print(star_db)

   all_cal_files = []
   for tcam, file, res in data:
      if tcam == cam:
         all_cal_files.append((file,res))
   #all_cal_files = deep_cal_report(cam, json_conf)
   year = datetime.now().strftime("%Y")
   autocal_dir = "/mnt/ams2/meteor_archive/" + STATION_ID + "/CAL/AUTOCAL/" + year + "/solved/"
   mcp_file = autocal_dir + "multi_poly-" + STATION_ID + "-" + cam + ".info"
   if cfe(mcp_file) == 1:
      mcp = load_json_file (mcp_file)
   else:
      mcp = None
   all_stars = []   
   star_db_file = autocal_dir + "star_db-" + cam + ".info"
   if cfe(star_db_file) == 1:
      star_db = load_json_file(star_db_file)
      if "processed_files" not in star_db:
         star_db['processed_files'] = []
   else:
      star_db = {}
      star_db['processed_files'] = []
      if mcp is not None:
         star_db = {}
         star_db['meteor_stars'] = []
         star_db['processed_files'] = []
         #star_db = get_stars_from_meteors_new(cam, mcp, star_db, json_conf, ci_data)

   # First do it with all the autocal images. 
   autocal_images = glob.glob(autocal_dir + "*" + cam + "*calparams.json")
   cal_files= get_cal_files(None, cam)
   if (len(autocal_images)) <= 5:
      for res in cal_files:
         autocal_images.append(res[0])

   # GET STARS FROM CAL IMAGES

   #for cal_file in sorted(autocal_images, reverse=True):
   for cal_file, file_res in sorted(all_cal_files, reverse=True):
      print(cal_file)
      cp = load_json_file(cal_file)
      print("CF:", cal_file)
      if file_res > 10:
         print("DEEP CALIB", file_res)
         continue
      cal_fn,cal_dir = fn_dir(cal_file)
      if True:
      #if cal_fn not in star_db['processed_files']:
         cal_img_file = cal_file.replace("-calparams.json", ".png")
         if cfe(cal_img_file) == 0:
            cal_img_file = cal_file.replace("-calparams.json", "-stacked.png")
         if cfe(cal_img_file) == 0:
            continue
         
         cal_img = cv2.imread(cal_img_file)
         temp_img = cal_img.copy()
         gray_cal_img = cv2.cvtColor(cal_img, cv2.COLOR_BGR2GRAY)
         stars = get_image_stars(cal_file, gray_cal_img.copy(), json_conf, 0)
         if len(stars) < 5:
            continue
         print("STARS:", len(stars))
         cp = pair_stars(cp, cal_file, json_conf, gray_cal_img)
         if len(cp['cat_image_stars']) < 10:
            continue
         print("PAIRED STARS:", len(cp['cat_image_stars'])) 

         #cal_files= get_cal_files(cal_file)
         #if len(cal_files) > 5:
         #   cal_files = cal_files[0:5]
         #best_cal_file, cp = get_best_cal(cal_file, cal_files, stars, gray_cal_img, json_conf, mcp)
         #best_cal_file = cal_file
         #cp = load_json_file(cal_file)


         if mcp is not None and mcp != 0:
            cp['x_poly'] = mcp['x_poly']
            cp['x_poly_fwd'] = mcp['x_poly_fwd']
            cp['y_poly'] = mcp['y_poly']
            cp['y_poly_fwd'] = mcp['y_poly_fwd']

         #cal_params['x_poly'] = np.zeros(shape=(15,), dtype=np.float64)
         #cal_params['y_poly'] = np.zeros(shape=(15,), dtype=np.float64)
         #cal_params['x_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
         #cal_params['y_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)

         #if "fov_fit" not in cp:
         print("STARS:", len(stars), len(cp['cat_image_stars']))
         if len(cp['cat_image_stars']) > 10 and cp['total_res_px'] > 5:

            print("MIN FOV:")
            #os.system("./Process.py refit " + cal_file)
            #cp = minimize_fov(cal_file, cp, cal_file,cal_img,json_conf )
            #save_json_file(cal_file, cp)



         res = calc_starlist_res(cp['cat_image_stars'])

         for data in cp['cat_image_stars']:
   
            dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int = data
            cp = update_center_radec(cal_file,cp,json_conf)
            all_stars.append((cal_fn, cp['center_az'], cp['center_el'], cp['ra_center'], cp['dec_center'], cp['position_angle'], cp['pixscale'], dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int))
            if SHOW == 1:
               cv2.rectangle(temp_img, (new_cat_x-2, new_cat_y-2), (new_cat_x + 2, new_cat_y + 2), (128, 128, 128), 1)
               cv2.rectangle(temp_img, (six-2, siy-2), (six+ 2, siy+ 2), (255, 255, 255), 1)
               cv2.circle(temp_img,(six,siy), 7, (128,128,128), 1)
               cv2.putText(temp_img, str(dcname),  (int(new_cat_x),int(new_cat_y)), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 1)
               cv2.putText(temp_img, "RES: " +  str(res),  (int(300),int(300)), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 1)
         star_db['processed_files'].append(cal_fn)


   star_db['autocal_stars'] = all_stars
   star_db['all_stars'] = all_stars
   print("DONE LOADING CAL STARS.")

   # GET MORE STARS FROM METEOR IMAGES
   star_db['meteor_stars'] = []
   # GET METEOR STARS
   if False:
      star_db = get_stars_from_meteors(cam, mcp, star_db, json_conf)
      print("DONE GET STARS FROM EMETORS")
      for star in star_db['meteor_stars']:
         all_stars.append(star)
      print("ALL STARS:", len(all_stars))
      exit()
   #(cal_file,ra_center,dec_center,position_angle,pixscale,dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy, img_res,np_new_cat_x,np_new_cat_y) = star

   #remove the worse stars
   best_stars = []
   dists = [row[22] for row in all_stars]
   med_dist = np.median(dists)
   std_dist = np.std(dists)
   if len(all_stars) < 10:
      print("not enough stars. only ", len(autocal_images), " files " )
      return(0)
   for star in all_stars:
      (cal_file , center_az, center_el, ra_center, dec_center, position_angle, pixscale, dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int) = star
      if cat_dist < std_dist * 2:
         best_stars.append(star)
      else:
         print("STAR NOT GOOD ENOUGH:", cat_dist, std_dist)

   print("BEST STARS:", len(best_stars))
   status, cal_params,merged_stars = minimize_poly_multi_star(best_stars, json_conf,0,0,cam,None,mcp,SHOW)
   if status == 0:
      print("Multi star min failed.")
      exit()
   star_db['autocal_stars'] = merged_stars

   save_json_file (autocal_dir + "star_db-" + STATION_ID + "-" + cam + ".info", star_db)
   save_json_file (autocal_dir + "multi_poly-" + STATION_ID + "-" + cam + ".info", cal_params)
   mpf = autocal_dir + "multi_poly-" + STATION_ID + "-" + cam + ".info"
   for cal_file in autocal_images:
      cmd = "./AzElGrid.py az_grid " + cal_file + ">/tmp/mike.txt 2>&1"
      os.system(cmd)

def get_best_cp(mfile, json_conf, ci_data, stars,cal_img_file):
   print("GET BEST CAL:", mfile) 
   exit()
   cal_img = cv2.imread(cal_img_file)
   bd = []
   for data in ci_data:
      cp_file, az, el, pos, px, star_count, match, res = data
      #print("FINDING BEST CAL:", az, el, pos, px)
      cp = load_json_file(cp_file)
      cp = update_center_radec(mfile,cp,json_conf)
      cp['user_stars'] = stars

      cat_stars = get_catalog_stars(cp)

      #if mcp is not None and mcp != 0:
      #   if "x_poly" in mcp:
      #      cp['x_poly'] = mcp['x_poly']
      #      cp['y_poly'] = mcp['y_poly']
      #      cp['x_poly_fwd'] = mcp['x_poly_fwd']
      #      cp['y_poly_fwd'] = mcp['y_poly_fwd']

      cp = pair_stars(cp, mfile, json_conf, cal_img)
      fn, dir = fn_dir(mfile)
      #print("RES:", fn, cp['total_res_px'], len(cp['user_stars']), len(cp['cat_image_stars']))
      bd.append((cp_file, cp['total_res_px'], len(cp['user_stars']), len(cp['cat_image_stars'])))
   temp = sorted(bd, key=lambda x: x[1], reverse=False)
   best_cal_data = bd[0]
   return(best_cal_data, cal_img)


def get_stars_from_meteor(mfile,json_conf,ci_data,mcp):
   if cfe(mfile) == 1:
      print("LOADING:", mfile)
      mj = load_json_file(mfile)
      if 'hd_stack' in mj:
         if mj['hd_stack'] != 0:
             if cfe(mj['hd_stack']) == 1:
                calib = None
                stars = get_image_stars(mj['hd_stack'], None, json_conf, 0)
                
                #print(mj['hd_stack'], len(stars))
                if len(stars) > 10:
                   # use cal data saved in mj file if it exists (This means the mfit has already run)
                   if "caldata" in mj and "calib" in mj:
                   #if False:
                      #best_cal_data, cal_img = get_best_cp(mfile, json_conf, ci_data, stars, mj['hd_stack'])
                      cp_file = mj['caldata'][0]
                      cal_img = cv2.imread(mj['hd_stack'])
                      best_cal_data = mj['caldata']
                      if "calib" in mj:
                         print("USING METEOR CALIB INFO!")
                         calib = mj['calib']
                         mcp['center_az'] = calib['az']
                         mcp['center_el'] = calib['el']
                         mcp['position_angle'] = calib['pos']
                         mcp['pixel_scale'] = calib['pxs']
                         nc = mcp
                      else:
                         calib = None

                      print("BEST CAL DATA", mfile, best_cal_data)
                   else:
                      best_cal_data, cal_img = get_best_cp(mfile, json_conf, ci_data, stars, mj['hd_stack'])
                      cp_file = best_cal_data[0]

                   nc = load_json_file(cp_file)
                   if mcp is not None:
                      nc['x_poly'] = mcp['x_poly']
                      nc['y_poly'] = mcp['y_poly']
                      nc['x_poly_fwd'] = mcp['x_poly_fwd']
                      nc['y_poly_fwd'] = mcp['y_poly_fwd']
                      
                   nc['user_stars'] = stars
                   nc = update_center_radec(mfile,nc,json_conf)
                   nc = pair_stars(nc, mfile, json_conf, cal_img)
                   print("BEST CAL:", best_cal_data)
                   view_calib(cp_file,json_conf,nc,cal_img)
                   if len(nc['cat_image_stars']) > 10 and calib is None and nc['total_res_px'] < 15 and nc['total_res_px'] > 4:
                      nc = minimize_fov(mj['hd_stack'], nc, mj['hd_stack'],cal_img,json_conf )
                   mj['caldata'] = best_cal_data
                   print("NC:", nc)
                   mj['calib'] = {
                      "az": nc['center_az'],
                      "el": nc['center_el'],
                      "pos": nc['position_angle'],
                      "pxs": nc['pixscale'],
                   }
                   print(mfile)
                   mj['cp'] = nc
                   save_json_file(mfile, mj)
                   print(nc)
                   return(nc['cat_image_stars'])



def get_stars_from_meteors_new(cam, mcp, star_db, json_conf, ci_data):
   mds = sorted(glob.glob("/mnt/ams2/meteors/*"), reverse=True)
   for md in mds[0:90]:
      jsfs = glob.glob(md + "/*" + cam + "*.json")
      for jsf in jsfs: 
         stars = get_stars_from_meteor(jsf,json_conf, ci_data,mcp)
         if stars is not None:
            for star in stars:
               star_db['meteor_stars'].append(star)

         print("METEOR STARS:", len(star_db['meteor_stars']))
         if len(star_db['meteor_stars']) > 500:
            return(star_db)

def get_stars_from_meteors(cam, mcp, star_db, json_conf):
   mds = sorted(glob.glob("/mnt/ams2/meteors/*"), reverse=True)
   all_meteor_imgs = []

   print("METEOR STARS:", len(star_db['meteor_stars']))

   for md in mds[0:90]:
      jsfs = glob.glob(md + "/*" + cam + "*.json")
      for jsf in jsfs: 
         print(jsf)
         try:
            js = load_json_file(jsf)
         except:
            print("BAD JSON:", jsf)
            continue
         if True:
            if "hd_trim" in js:
               if js['hd_trim'] == 0 or js['hd_trim'] is None:
                  continue 
               #if "cp" in js:
               #   cp = js['cp']
               stack_file = js['hd_trim'].replace(".mp4", "-stacked.png")
               if cfe(stack_file) == 1:
                  all_meteor_imgs.append(stack_file)

                  cal_img = cv2.imread(stack_file)
                  temp_img = cal_img.copy()
                  gray_cal_img = cv2.cvtColor(cal_img, cv2.COLOR_BGR2GRAY)
                  stars = get_image_stars(stack_file, gray_cal_img.copy(), json_conf, 0)
                  skip = 0 
                  if len(stars) > 10:
                     # We should only get the best cal file, if cp is not already in the meteor...(fix later)
                     temp_img = cal_img.copy()
                     if "cp" in js:
                        cp = js['cp']
                        std_dist, avg_dist = calc_starlist_res(cp['cat_image_stars'])
                        if std_dist < 4 :
                           skip = 1
                        if "fov_fit" in cp:
                           if cp['fov_fit'] > 10:
                              skip = 1
                     if skip == 0:   
                        cal_files= get_cal_files(stack_file)
                        if len(cal_files) > 5:
                           cal_files = cal_files[0:5]
                        best_cal_file, cp = get_best_cal(stack_file, cal_files, stars, gray_cal_img, json_conf, mcp)
                        js['cp'] = cp
                        if len(stars) > 5:
                           cp = minimize_fov(stack_file, cp, stack_file,cal_img,json_conf )
                        save_json_file(jsf, js)
              
                     marked_img = make_fit_image(cal_img, cp['cat_image_stars']) 

                     stack_fn, stack_dir = fn_dir(stack_file)




                     for data in cp['cat_image_stars']:
   
                        dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int = data
                        cp = update_center_radec(jsf,cp,json_conf)
                        star_db['meteor_stars'].append((stack_fn, cp['center_az'], cp['center_el'], cp['ra_center'], cp['dec_center'], cp['position_angle'], cp['pixscale'], dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int))
                        if SHOW == 1:
                           cv2.rectangle(temp_img, (new_cat_x-4, new_cat_y-4), (new_cat_x + 2, new_cat_y + 2), (255, 0, 0), 1)
                           cv2.circle(temp_img,(six,siy), 7, (128,128,128), 1)
                           cv2.putText(temp_img, str(dcname),  (int(new_cat_x),int(new_cat_y)), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 1)
                     if SHOW == 1:
                        show_image(temp_img, 'pepe', 100)



                  else:  
                     show_image(cal_img, 'pepe', 30)
               print("METEOR STARS END LOOP:", len(star_db['meteor_stars']))
               if len(star_db['meteor_stars']) > 1000:
                  break
                 

         star_db['processed_files'].append(jsf)
   print("END GET METEOR STARS")
   return(star_db)

def index_failed(json_conf):
   year = datetime.now().strftime("%Y")
   failed_dir = ARC_DIR + "CAL/AUTOCAL/" + year + "/failed/"
   bad_dir = ARC_DIR + "CAL/AUTOCAL/" + year + "/bad/"
   files = glob.glob(failed_dir + "*.png")
   for file in files:
      good_stars = []
      stack_org = cv2.imread(file)
      stack = cv2.cvtColor(stack_org.copy(), cv2.COLOR_BGR2GRAY)
      stars = get_image_stars(file, stack.copy(), json_conf, 0)
      stars = validate_stars(stars, stack)
      for star in stars:
         x,y,i = star
         x1 = x - 10
         y1 = y - 10
         x2 = x + 10
         y2 = y + 10
         if x1 < 10 or y1 < 10 or x2 > stack_org.shape[1] - 10 or y2 > stack_org.shape[0] - 10:
            continue
         

         cv2.rectangle(stack_org, (x-10, y-10), (x+10, y+10), (200, 200, 200), 1)
      show_image(stack_org, 'pepe', 30)
      if len(stars) < 10:
         cmd = "mv " + file + " " + bad_dir
         os.system(cmd)

def validate_stars(stars, stack):
   good_stars = []
   if len(stars) >= 10:
      for star in stars:
         x,y,i = star
         x1 = x - 10
         y1 = y - 10
         x2 = x + 10
         y2 = y + 10
         if x1 < 10 or y1 < 10 or x2 > stack.shape[1] - 10 or y2 > stack.shape[0] - 10:
            continue

         cnt = stack[y1:y2,x1:x2]

         status = star_cnt(cnt)
         if status == 1:
            good_stars.append(star)
   return(good_stars)

def star_cnt(simg):
   status = 1
   avg = np.median(simg) 
   max_p = np.max(simg) 
   pd = max_p - avg
   best_thresh = avg + (pd /2)
   _, star_bg = cv2.threshold(simg, best_thresh, 255, cv2.THRESH_BINARY)
   #thresh_obj = cv2.dilate(star_bg, None , iterations=4)
   w = None

   res = cv2.findContours(star_bg.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
   if len(res) == 3:
      (_, cnts, xx) = res
   else:
      (cnts ,xx) = res
   cc = 0
   for (i,c) in enumerate(cnts):
      x,y,w,h = cv2.boundingRect(cnts[i])
      cc += 1

   if w == None:
      return(0)  

   if cc != 1:
      status = 0
   if w > 6 or h > 6:
      status = 0
   if pd < 25 :
      status = 0


   return(status)

def apply_calib(meteor_file, json_conf):
   if "json" in meteor_file:
      hd_file = meteor_file.replace(".json", "-HD.mp4")


   stack = quick_video_stack(hd_file) 
   stack = cv2.cvtColor(stack, cv2.COLOR_BGR2GRAY)
   stack_org = stack.copy()

   stars = get_image_stars(meteor_file, stack_org.copy(), json_conf, 1)
   cal_files= get_cal_files(meteor_file)
   best_cal_file, cp = get_best_cal(meteor_file, cal_files, stars, stack, json_conf)
   cp['user_stars'] = stars
   if best_cal_file == 0:

      
      return(0)

   mj = load_json_file(meteor_file)
   cp['best_cal'] = best_cal_file
   calib = cp_to_calib(cp, stack_org)   
   mj['calib'] = calib

   star_image = draw_star_image(None, stack, cp, 0) 
   if CAL_MOVIE == 1:
      fn, dir = fn_dir(meteor_file)
      fn = fn.replace(".json", "")
      cv2.imwrite("tmp_vids/" + fn, star_image)

   save_json_file(meteor_file, mj)


def get_cnt_intensity(image, x, y, size):
   #cv2.rectangle(image, (x-10, y-10), (x+10, y+10), (200, 200, 200), 1)
   x1,y1,x2,y2= bound_cnt(x,y,1920,1080,size)
   cnt = image[y1:y2,x1:x2]

def cp_to_calib(cp, cal_image = None):
   calib = {}
   calib['device'] = {}
   if 'site_lat' in cp:
      calib['device']['lat'] = cp['site_lat']
      calib['device']['lng'] = cp['site_lng']
      calib['device']['alt'] = cp['site_alt']
   elif 'device_lat' in cp:
      calib['device']['lat'] = cp['device_lat']
      calib['device']['lng'] = cp['device_lng']
      calib['device']['alt'] = cp['device_alt']

   calib['device']['angle'] = cp['position_angle']
   calib['device']['scale_px'] = cp['pixscale']
   calib['device']['orig_file'] = cp['best_cal']
   calib['device']['total_res_px'] = cp['total_res_px']
   calib['device']['total_res_deg'] = cp['total_res_deg']
   calib['device']['poly'] = {}
   calib['device']['poly']['x'] = cp['x_poly'] 
   calib['device']['poly']['y'] = cp['y_poly'] 
   calib['device']['poly']['x_fwd'] = cp['x_poly_fwd'] 
   calib['device']['poly']['y_fwd'] = cp['y_poly_fwd'] 
   calib['device']['center'] = {}
   calib['device']['center']['az'] = cp['center_az']
   calib['device']['center']['el'] = cp['center_el']
   calib['device']['center']['ra'] = cp['ra_center']
   calib['device']['center']['dec'] = cp['dec_center']
   calib['stars'] = []
   calib['img_dim'] = [cp['imagew'],cp['imageh']]


   for data in cp['cat_image_stars']:
      dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int = data
      star = {}
      star['name'] = dcname 
      star['mag'] = mag
      star['ra'] = ra
      star['dec'] = dec
      star['dist_px'] = cat_dist
      star['dist_px_fwd'] = match_dist
      star['intensity'] = star_int
      star['i_pos'] = [six,siy]
      star['cat_dist_pos'] = [new_x,new_y]
      star['cat_und_pos'] = [new_cat_x,new_cat_y]
      calib['stars'].append(star)


   
   return(calib)



def get_best_cal(meteor_file, cal_files, stars , cal_img, json_conf,mcp=None):

   cal_scores = []
   for data in cal_files:
      cf, td = data
      cp = load_json_file(cf)

      # change the CP center ra/dec to match the AZ,EL at the time of this meteor
      cp = update_center_radec(meteor_file,cp,json_conf)
      cp['user_stars'] = stars
       
      cat_stars = get_catalog_stars(cp)

      if mcp is not None and mcp != 0:
         if "x_poly" in mcp:
            cp['x_poly'] = mcp['x_poly']
            cp['y_poly'] = mcp['y_poly']
            cp['x_poly_fwd'] = mcp['x_poly_fwd']
            cp['y_poly_fwd'] = mcp['y_poly_fwd']

      cp = pair_stars(cp, meteor_file, json_conf, cal_img)
      if len(cp['user_stars']) > 0:
         match_perc = len(cp['cat_image_stars']) / len(cp['user_stars'])
      else:
         match_perc = 9999
      if len(cp['user_stars']) <= 0:
         cat_score = 9999

      if len(cp['cat_image_stars']) > 0:
         # lower is better
         cat_score = (cp['total_res_px'] * cp['total_res_deg'] / len(cp['cat_image_stars'])) / match_perc
      else:
         cat_score = 9999
      #print(cf, len(cp['user_stars']), len(cp['cat_image_stars']), match_perc, cp['total_res_px'], cp['total_res_deg'], cat_score)
      cal_scores.append((cf, cat_score,cp))
   cal_scores = sorted(cal_scores, key=lambda x: x[1], reverse=False)
   if len(cal_scores) > 0:
      cf,cs,cp = cal_scores[0]
      cp['user_stars'] = stars
      return(cf, cp)
   else:
      return(0)

def update_center_radec(archive_file,cal_params,json_conf):
   rah,dech = AzEltoRADec(cal_params['center_az'],cal_params['center_el'],archive_file,cal_params,json_conf)
   rah = str(rah).replace(":", " ")
   dech = str(dech).replace(":", " ")
   ra_center,dec_center = HMS2deg(str(rah),str(dech))
   cal_params['ra_center'] = ra_center
   cal_params['dec_center'] = dec_center

   return(cal_params)

def get_cal_files(meteor_file=None, cam=None):
   if meteor_file is not None:
      (f_datetime, cam, f_date_str,y,m,d, h, mm, s) = convert_filename_to_date_cam(meteor_file)
   pos_files = []
   if cam is None:
      cal_dirs = glob.glob("/mnt/ams2/cal/freecal/*")
   else:
      print("CAM:", cam)
      cal_dirs = glob.glob("/mnt/ams2/cal/freecal/*" + cam + "*")
   for cd in cal_dirs:
      root_file = cd.split("/")[-1]
      if cfe(cd, 1) == 1:
         cp_files = glob.glob(cd + "/" + root_file + "*calparams.json")
         if len(cp_files) == 1:
            cpf = cp_files[0]
         if len(cp_files) > 1:
            print("CAL ERROR :", cp_files)
            exit()
         if len(cp_files) == 0:
            print("CAL ERROR :", cd + "/" + root_file, cp_files)
            cmd = "rm -rf " + cd
            print(cmd)
            os.system(cmd)
            exit()
 
      if meteor_file is not None:
         (c_datetime, ccam, c_date_str,cy,cm,cd, ch, cmm, cs) = convert_filename_to_date_cam(cpf)
         time_diff = f_datetime - c_datetime
         pos_files.append((cpf, abs(time_diff.total_seconds())))
      else:
         pos_files.append((cpf, 0))




   pos_files = sorted(pos_files, key=lambda x: x[1], reverse=False)
   return(pos_files)
   

def solve_field(image_file, image_stars=[], json_conf={}):
   print("Solve field", image_file)
   ifn = image_file.split("/")[-1]
   idir = image_file.replace(ifn, "")
   idir += "temp/"
   if cfe(idir, 1) == 0:
      os.makedirs(idir)

   plate_file = idir + ifn
   print("NEW PLATE FILE:", plate_file)
   wcs_file = plate_file.replace(".jpg", ".wcs")
   grid_file = plate_file.replace(".jpg", "-grid.png")
   wcs_info_file = plate_file.replace(".jpg", "-wcsinfo.txt")
   solved_file = plate_file.replace(".jpg", ".solved")
   astrout = plate_file.replace(".jpg", "-astrout.txt")
   star_data_file = plate_file.replace(".jpg", "-stars.txt")

   print("SOLVED FILE:", solved_file)
   if len(image_stars) < 10:
      oimg = cv2.imread(image_file)
      print(image_file)
      print(oimg.shape)
      image_stars = get_image_stars(image_file, oimg, json_conf,0)
      plate_image, star_points = make_plate_image(oimg.copy(), image_stars)
      plate_file = image_file.replace(".png", ".jpg")
      cv2.imwrite(plate_file, plate_image)
      image_file = plate_file
   if len(image_stars) < 10:
      print("not enough stars", len(image_stars) )
      return(0, {}, "")

   cmd = "mv " + image_file + " " + idir
   os.system(cmd)
   image_file = idir + ifn

   # solve field
   cmd = "/usr/local/astrometry/bin/solve-field " + plate_file + " --crpix-center --cpulimit=30 --verbose --no-delete-temp --overwrite --width=" + str(HD_W) + " --height=" + str(HD_H) + " -d 1-40 --scale-units dw --scale-low 60 --scale-high 90 -S " + solved_file + " >" + astrout
   print(cmd)
   astr = cmd
   print(cmd)
   if cfe(solved_file) == 0:
      os.system(cmd)

   if cfe(solved_file) == 1:
      # get WCS info
      print("Solve passed.", solved_file)
      cmd = "/usr/bin/jpegtopnm " + plate_file + "|/usr/local/astrometry/bin/plot-constellations -w " + wcs_file + " -o " + grid_file + " -i - -N -C -G 600 > /dev/null 2>&1 "
      os.system(cmd)

      cmd = "/usr/local/astrometry/bin/wcsinfo " + wcs_file + " > " + wcs_info_file
      os.system(cmd)

      os.system("grep Mike " + astrout + " >" +star_data_file + " 2>&1" )

      cal_params = save_cal_params(wcs_file,json_conf)
      cal_params = default_cal_params(cal_params, json_conf)
      cal_params['user_stars'] = image_stars

      return(1, cal_params, wcs_file) 
   else:
      print("Solve failed.", solved_file)
      print(astr) 
      return(0, {}, "")
   
def show_image(img, win, time=0):
   #time = 300 
   #time = 0
   if img.shape[0] >= 1070:
      disp_img = cv2.resize(img, (1280, 720))
   else:
      disp_img = cv2.resize(img, (1280, 720))
 
   if SHOW == 1:
      try:
         cv2.imshow(win, disp_img)
         cv2.waitKey(time)  
      except:
         print("Bad image:", disp_img)

def view_calib(cp_file,json_conf,nc,oimg, show = 1):
   img = oimg.copy()
   tres = 0
   for star in nc['user_stars']:
      if len(star) == 3:
         x,y,flux = star
      else:
         x,y = star
         flux = 0
      cv2.circle(img,(x,y), 5, (128,128,128), 1)
   for star in nc['no_match_stars']:
      name,mag,ra,dec,new_cat_x,new_cat_y,six,siy,cat_dist = star
      cv2.circle(img,(int(new_cat_x),int(new_cat_y)), 5, (128,255,128), 1)

   for star in nc['cat_image_stars']:
      dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int = star
      cv2.circle(img,(six,siy), 10, (128,128,128), 1)
      cv2.circle(img,(int(new_x),int(new_y)), 10, (128,128,255), 1)
      cv2.circle(img,(int(new_cat_x),int(new_cat_y)), 10, (128,255,128), 1)
      cv2.line(img, (int(new_cat_x),int(new_cat_y)), (int(new_x),int(new_y)), (255), 2)
      cv2.line(img, (int(six),int(siy)), (int(new_cat_x),int(new_cat_y)), (255), 2)
      cv2.putText(img, str(dcname),  (int(new_cat_x),int(new_cat_y)), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 1)
      #cv2.line(marked_img, (six,siy), (new_x,new_y), (255), 2)
      tres += cat_dist

   fn, dir = fn_dir(cp_file)
   cv2.putText(img, "Res:" + str(nc['total_res_px'])[0:5],  (25,25), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 1)
   cv2.putText(img, "AZ/EL:" + str(nc['center_az'])[0:6] + "/" + str(nc['center_el'])[0:6],  (25,50), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 1)
   cv2.putText(img, "RA/DEC:" + str(nc['ra_center'])[0:6] + "/" + str(nc['dec_center'])[0:6],  (25,75), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 1)
   cv2.putText(img, "POS:" + str(nc['position_angle'])[0:6] ,  (25,100), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 1)
   cv2.putText(img, "PIX:" + str(nc['pixscale'])[0:6] ,  (25,125), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 1)
   cv2.putText(img, "File:" + str(fn),  (25,150), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 1)
   cv2.putText(img, "Match %:" + str(nc['match_perc']),  (25,175), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 1)
   cv2.putText(img, "POLY" +  str(nc['x_poly'][0]),  (25,200), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 1)

   if SHOW == 1:
      dimg = cv2.resize(img, (1280,720))
      cv2.imshow('pepe', dimg)
      cv2.waitKey(30)
   return(img)

def get_default_calib(file, json_conf):
   (f_datetime, cam, f_date_str,y,m,d, h, mm, s) = convert_filename_to_date_cam(file)
   for key in json_conf['cameras']:
      cams_id = json_conf['cameras'][key]['cams_id']
      if cam == cams_id:
         if "calib" in json_conf['cameras'][key]:
            return(json_conf['cameras'][key]['calib'])
   return(None)

def get_best_cal_new(cp_file, json_conf) :
   cp_img_file = cp_file.replace("-calparams.json", "-src.jpg")
   if cfe(cp_img_file) == 0:
      print("ERR:", cp_img_file, " not found")
      exit()
   cal_img = cv2.imread(cp_img_file)
   tcp = load_json_file(cp_file)
   # get 3 cals before and 3 after if possible
   bfiles = []
   afiles = []
   after_files = []
   before_files = []
   (m_datetime, cam, f_date_str,y,m,d, h, mm, s) = convert_filename_to_date_cam(cp_file)
   cal_index_file = "/mnt/ams2/meteor_archive/" + STATION_ID + "/CAL/" + STATION_ID + "_" + cam + "_CAL_INDEX.json"
   ci_data = load_json_file(cal_index_file)
   time_ci_data = load_json_file(cal_index_file)
   for data in ci_data:
      cpf = data[0]
      (f_datetime, cam, f_date_str,y,m,d, h, mm, s) = convert_filename_to_date_cam(cpf)

      elp = (f_datetime - m_datetime).total_seconds()
      print(m_datetime, f_datetime, elp)
      data.append(elp)
      print(len(data))
      if elp < 0 and len(bfiles) < 10:
         bfiles.append(data)
      if elp > 0 and len(bfiles) < 10:
         afiles.append(data)
   bfiles = sorted(bfiles, key=lambda x: x[8], reverse=False)
   afiles = sorted(afiles, key=lambda x: x[8], reverse=False)
   print(len(bfiles))
   before_files = bfiles
   after_files = afiles
   best_cp = {}
   best_cp['total_res_px'] = 9999
   for data in bfiles:
      ncp, bad_stars, marked_img = test_cal(cp_file, json_conf, tcp, cal_img, data)
      print("NEW RES:", ncp['total_res_px'])
      if float(ncp['total_res_px']) < float(best_cp['total_res_px']):
         print("RESET BEST CAL!", ncp['total_res_px'])
         best_cp = dict(ncp)
   for data in afiles:
      ncp, bad_stars, marked_img = test_cal(cp_file, json_conf, tcp, cal_img, data)
      print("NEW RES:", ncp['total_res_px'])
      if float(ncp['total_res_px']) < float(best_cp['total_res_px']):
         print("RESET BEST CAL!", ncp['total_res_px'])
         best_cp = dict(ncp)
   print("FINAL BEST CAL:", best_cp['total_res_px'])
   return(best_cp)

def test_cal(cp_file,json_conf,cp, cal_img, cdata ):
   print("TESTING CAL DATA", cdata)
   cfile, az, el, pos, px, num_ustars, num_cstars, res, tdiff = cdata
   cp['center_az'] = az 
   cp['center_el'] = el
   cp['position_angle'] = pos
   cp['pixscale'] = px
   cp = update_center_radec(cp_file,cp,json_conf)
   cp, bad_stars, marked_img = eval_cal(cp_file,json_conf,cp,cal_img, None)
   return(cp, bad_stars, marked_img)

def optimize_var(cp_file,json_conf,var,cp,img):
   cal_img_file = cp_file.replace("-calparams.json", ".png")
   ores = cp['total_res_px']
   best_cal_params = None
  
   tcal = dict(cp)
   for i in range (-25,25):
      val = i / 10
      tcal[var] = float(cp[var]) + val

      data = [cp_file, tcal['center_az'], tcal['center_el'], tcal['position_angle'], tcal['pixscale'], len(tcal['user_stars']), len(tcal['cat_image_stars']), tcal['total_res_px'],0]  
      tcal = update_center_radec(cp_file,tcal,json_conf)
      tcal['ra_center'] = float( tcal['ra_center'])
      tcal['dec_center'] = float( tcal['dec_center'])

      tcp , bad_stars, marked_img = test_cal(cp_file, json_conf, tcal, img, data)
      print("BEFORE/CUR:", tcp['total_res_px'],  cp['total_res_px'])
      if tcp['total_res_px'] < cp['total_res_px']:
         best_cal_params = dict(tcp)
         
         print("OPTIMIZIZE BETTER BETTER", cp[var], tcp[var] )
         cp = dict(tcp)

   return(best_cal_params)
   

def optimize_matchs(cp_file,json_conf,nc,oimg):
   cal_img_file = cp_file.replace("-calparams.json", ".png")
   img = oimg.copy()
   ora = nc['ra_center']
   odec = nc['dec_center']
   opos = nc['position_angle']
   opx = nc['pixscale']
   ores = nc['total_res_px']
   default_calib = get_default_calib(cp_file,json_conf)
   if default_calib is not None:
      default_pos_diff = abs(float(default_calib[2]) - float(opx) )
      if default_pos_diff > 20:
         nc['position_angle'] = default_calib[2] 

   if ores > 50:
      # revert to the defaults for this cam if they exist
      if default_calib is not None:
         nc['center_az'], nc['center_el'], nc['position_angle'], nc['pixscale'] = default_calib

   nc['user_stars'] = get_image_stars(cp_file, oimg, json_conf,0)
   if True:
      nc['x_poly'] = np.zeros(shape=(15,), dtype=np.float64)
      nc['y_poly'] = np.zeros(shape=(15,), dtype=np.float64)
      nc['x_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
      nc['y_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
   cat_stars = get_catalog_stars(nc)
   nc = pair_stars(nc, cp_file, json_conf, oimg)
   match_perc = len(nc['cat_image_stars']) / len(nc['user_stars']) 
   view_calib(cp_file,json_conf,nc,oimg)
   best_match_perc = match_perc
   if nc['total_res_px'] > 20:
      #yn = input ("This cal looks messed up. Press Y to manual calib")

      plate_image, star_points = make_plate_image(oimg.copy(), nc['user_stars'])
      plate_file = cal_img_file.replace(".png", ".jpg")
      cv2.imwrite(plate_file, plate_image)

      status, cal_params, wcs_file = solve_field(plate_file, nc['user_stars'], json_conf)
      print("PLATE STATUS:", status)

      if status == '1':
         nc = cal_params

      #if yn == "Y":
      #   nc = guess_cal(cal_img_file, json_conf)
         #nc = load_json_file(cp_file)

   # opt pos
   s = 0
   e = 360 
   opos = nc['position_angle']
   best_pos = nc['position_angle']
   best_res = nc['total_res_px']
   best_score = best_res / best_match_perc 
   for i in range (s,e):
      a = i  
      nc['position_angle'] = i
     
      print("NC P:", nc['position_angle'])
      cat_stars = get_catalog_stars(nc)
      nc = pair_stars(nc, cp_file, json_conf, oimg)
      print("NC P2:", nc['position_angle'])
      match_perc = len(nc['cat_image_stars']) / len(nc['user_stars']) 
      nc['match_perc'] = match_perc
      res = nc['total_res_px']
      score = res / match_perc 
      print("POS:",  nc['position_angle'], match_perc, res)
      if score < best_score :
         print("BETTER MATCH:", i, res, match_perc, score)
         best_score = score 
         best_pos = a + opos

   nc['position_angle'] = best_pos

   # opt az
   #s = int(nc['center_az']-10)
   #e = int(nc['center_az']+10)
   s = -10
   e = 10
   oaz = nc['center_az']
   best_az = nc['center_az']
   best_res = nc['total_res_px']
   best_score = best_res / best_match_perc 
   print("AZ", s,e)
   oaz = nc['center_az']
   for i in range (s,e):
      a = i / 100
      nc['center_az'] = oaz + a 
      nc = update_center_radec(cp_file,nc,json_conf)
      cat_stars = get_catalog_stars(nc)
      nc = pair_stars(nc, cp_file, json_conf, oimg)
      match_perc = len(nc['cat_image_stars']) / len(nc['user_stars']) 
      nc['match_perc'] = match_perc
      res = nc['total_res_px']
      score = res / match_perc 
      if score < best_score :
         print("BETTER AZ MATCH:", i, res, match_perc, score)
         best_score = score 
         best_az = oaz + a
      print("AZ:", best_az)

      view_calib(cp_file,json_conf,nc,oimg)

   nc['center_az'] = best_az

   s = -10
   e = 10
   oel = nc['center_el']
   best_el = nc['center_el']
   best_res = nc['total_res_px']
   best_score = best_res / best_match_perc
   print("EL", s,e)
   oel = nc['center_el']
   for i in range (s,e):
      a = i / 10
      nc['center_el'] = oel + a 
      nc = update_center_radec(cp_file,nc,json_conf)
      cat_stars = get_catalog_stars(nc)
      nc = pair_stars(nc, cp_file, json_conf, oimg)
      match_perc = len(nc['cat_image_stars']) / len(nc['user_stars'])
      nc['match_perc'] = match_perc
      res = nc['total_res_px']
      score = res / match_perc
      if score < best_score :
         print("BETTER EL MATCH:", i, res, match_perc, score)
         best_score = score
         best_el = oel + a
      print("EL:", best_el)

      view_calib(cp_file,json_conf,nc,oimg)
   nc['center_el'] = best_el

   s = -10
   e = 10
   ops = nc['pixscale']
   best_ps = nc['pixscale']
   best_res = nc['total_res_px']
   best_score = best_res / best_match_perc
   print("EL", s,e)
   oel = nc['pixscale']
   for i in range (s,e):
      a = i / 10
      nc['pixscale'] = ops + a
      nc = update_center_radec(cp_file,nc,json_conf)
      cat_stars = get_catalog_stars(nc)
      nc = pair_stars(nc, cp_file, json_conf, oimg)
      match_perc = len(nc['cat_image_stars']) / len(nc['user_stars'])
      nc['match_perc'] = match_perc
      res = nc['total_res_px']
      score = res / match_perc
      if score < best_score :
         print("BETTER PX MATCH:", i, res, match_perc, score)
         best_score = score
         best_ps = ops + a
      print("PS:", best_ps)

      view_calib(cp_file,json_conf,nc,oimg)
   nc['pixscale'] = best_ps




   cat_stars = get_catalog_stars(nc)
   nc = pair_stars(nc, cp_file, json_conf, oimg)
   match_perc = len(nc['cat_image_stars']) / len(nc['user_stars']) 
   nc['match_perc'] = match_perc
   view_calib(cp_file,json_conf,nc,oimg)



   #nc = minimize_fov(cp_file, nc, cp_file,oimg,json_conf )
   view_calib(cp_file,json_conf,nc,oimg)
   if type(nc['x_poly']) is not list:
      nc['x_poly'] = nc['x_poly'].tolist()
      nc['y_poly'] = nc['y_poly'].tolist()
      nc['y_poly_fwd'] = nc['y_poly_fwd'].tolist()
      nc['x_poly_fwd'] = nc['x_poly_fwd'].tolist()

   print(ora , nc['ra_center'])
   print(odec , nc['dec_center'])
   print(opos , nc['position_angle'])
   print(opx , nc['pixscale'])


   save_json_file(cp_file, nc)   
   return(nc)
   #exit()



def eval_cal(cp_file,json_conf,nc=None,oimg=None, mask_img=None):
   #print("EVAL CAL")
   if len(oimg.shape) == 3:
      gimg = cv2.cvtColor(oimg, cv2.COLOR_BGR2GRAY)
   else:
      gimg = oimg.copy()
   if oimg is not None:
      img = oimg.copy()
   if nc is None:
      print("LOADING CAL FILE:", cp_file)
      nc = load_json_file(cp_file)

   img_file = cp_file.replace("-calparams.json", ".png")
   if cfe(img_file) == 0:
      img_file = cp_file.replace("-calparams.json", "-src.jpg")
   if oimg is None:
      print("OPEN OIMG", img_file)
      img = cv2.imread(img_file)
      oimg = img.copy()
   if nc is None:
      print("NC IS NONE SO GETTING USER STARS...")
      nc['user_stars'] = get_image_stars(img_file, None, json_conf,0)

   elif "user_stars" not in nc:
      print("NC GETTING USER STARS.", nc)
      nc['user_stars'] = get_image_stars(img_file, None, json_conf,0)

   #print("UPDATING CENTER")
   nc = update_center_radec(cp_file,nc,json_conf)
   #print("GETTING CATALOG STARS")
   cat_stars = get_catalog_stars(nc)
   #if "user_stars" in nc:
   #   if len(nc['user_stars'][0]) == 2:
   #      print("GET STARS because BP missin?:", img_file)
   #      exit()
   #      nc['user_stars'] = get_image_stars(img_file, None, json_conf,0)
   #print("PAIRING STARS")
   nc = pair_stars(nc, cp_file, json_conf, gimg)
   #print("AFTER PAIR:")
   if len(nc['user_stars']) > 0:
      match_perc = len(nc['cat_image_stars']) / len(nc['user_stars']) 
   else:
      match_perc = 0
   nc['match_perc'] = match_perc


   tres = 0
   bad_stars = []
   #print("CALC RES:")
   for star in nc['cat_image_stars']:
      dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int = star
      tres += cat_dist
   if len(nc['cat_image_stars']) == 0:
      avg_res = 9999
   else:
      avg_res = tres / len(nc['cat_image_stars'])

   #print("BAD STARS:")
   for star in nc['cat_image_stars']:
      dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int = star
      if cat_dist > avg_res * 2:
         bad_stars.append(star)



   nc['total_res_px'] = avg_res
   nc['match_perc'] = match_perc

   #print("DONE EVAL")
   print("RES", nc['position_angle'], avg_res)
   marked_img = view_calib(cp_file,json_conf,nc,oimg)
   return(nc, bad_stars, marked_img)

      



def eval_cal_dupe(cp_file,json_conf,nc=None,oimg=None):
   if len(oimg.shape) == 3:
      gimg = cv2.cvtColor(oimg, cv2.COLOR_BGR2GRAY)
   else:
      gimg = oimg
   if oimg is not None:
      img = oimg.copy()
   if nc is None:
      nc = load_json_file(cp_file)

   img_file = cp_file.replace("-calparams.json", ".png")
   if oimg is None:
      img = cv2.imread(img_file)
   if nc is None:
      nc['user_stars'] = get_image_stars(img_file, None, json_conf,0)

   elif "user_stars" not in nc:
      nc['user_stars'] = get_image_stars(img_file, None, json_conf,0)
   cat_stars = get_catalog_stars(nc)
   nc = pair_stars(nc, cp_file, json_conf, gimg)

   nc['cat_image_stars'], bad_stars = mag_report(nc['cat_image_stars'], 0)
   if len(nc['cat_image_stars']) > 0:
      match_perc = len(nc['cat_image_stars']) / len(nc['user_stars']) 
   else:
      match_perc = .01

   tres = 0
   nc['match_perc'] = match_perc
   for star in nc['user_stars']:
      x,y,flux = star
      cv2.circle(img,(x,y), 5, (128,128,128), 1)
   for star in nc['no_match_stars']:
      name,mag,ra,dec,new_cat_x,new_cat_y,six,siy,cat_dist = star
      cv2.circle(img,(int(new_cat_x),int(new_cat_y)), 5, (128,255,128), 1)

   for star in nc['cat_image_stars']:
      dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int = star
      cv2.circle(img,(six,siy), 10, (128,128,128), 1)
      cv2.circle(img,(int(new_x),int(new_y)), 10, (128,128,255), 1)
      cv2.circle(img,(int(new_cat_x),int(new_cat_y)), 10, (128,255,128), 1)
      tres += cat_dist
   if len(nc['cat_image_stars']) == 0:
      avg_res = 9999
   else:
      avg_res = tres / len(nc['cat_image_stars'])
   fn, dir = fn_dir(cp_file)
   cv2.putText(img, "Res:" + str(avg_res)[0:5],  (25,25), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 1)
   cv2.putText(img, "AZ/EL:" + str(nc['center_az'])[0:6] + "/" + str(nc['center_el'])[0:6],  (25,50), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 1)
   cv2.putText(img, "RA/DEC:" + str(nc['ra_center'])[0:6] + "/" + str(nc['dec_center'])[0:6],  (25,75), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 1)
   cv2.putText(img, "POS:" + str(nc['position_angle'])[0:6] ,  (25,100), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 1)
   cv2.putText(img, "PIX:" + str(nc['pixscale'])[0:6] ,  (25,125), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 1)
   cv2.putText(img, "File:" + str(fn),  (25,150), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 1)
   cv2.putText(img, "Match %:" + str(nc['match_perc']),  (25,175), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 1)

   bad_stars = []
   for star in nc['cat_image_stars']:
      dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int = star
      if cat_dist > avg_res * 2:
         bad_stars.append(star)

   nc['total_res_px'] = avg_res
   nc['match_perc'] = match_perc
   if SHOW == 1:
      dimg = cv2.resize(img, (1280,720))
   
      cv2.imshow('pepe', dimg)
      cv2.waitKey(15)
   return(nc, bad_stars)

def remove_bad_stars(cp, bad_stars):
   good_stars = []
   for star in cp['cat_image_stars']:
      dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int = star
      bad = 0
      for bad_star in bad_stars:
         dcname,mag,bra,bdec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int = star
         if bra == ra and bdec == dec:
            bad = 1
      if bad == 0:
         good_stars.append((star))

   cp['cat_image_stars'] = good_stars
   return(cp)

def freecal_index(cam, json_conf, r_station_id = None):
   print("Wait.")

def get_cal_img(src_file):
   rf = src_file.replace("-src.jpg", "")
   img_file = None
   test_file = rf + ".png"
   if cfe(test_file) == 1:
      img_file = test_file
   test_file = rf + "-stacked.png"
   if cfe(test_file) == 1:
      img_file = test_file
   test_file = rf + "-stacked.jpg"
   if cfe(test_file) == 1:
      img_file = test_file
   test_file = rf + "-stacked-stacked.png"
   if cfe(test_file) == 1:
      img_file = test_file
   test_file = rf + "-stacked-stacked.jpg"
   if cfe(test_file) == 1:
      img_file = test_file
   if img_file is not None:
      img = cv2.imread(img_file)
      cv2.imwrite(src_file, img)      
   else:
      return(None)   

def cal_index(cam, json_conf, r_station_id = None):
   if r_station_id is None:
      save_file = "/mnt/ams2/meteor_archive/" + STATION_ID + "/CAL/" + STATION_ID + "_" + cam + "_CAL_INDEX.json"
   else:
      save_file = "/mnt/ams2/meteor_archive/" + r_station_id + "/CAL/" + r_station_id + "_" + cam + "_CAL_INDEX.json"
      r_cal_dir = "/mnt/ams2/meteor_archive/" + r_station_id + "/CAL/BEST/"
   cloud_save_file = save_file.replace("ams2/meteor_archive", "archive.allsky.tv")
   cfn, cdir = fn_dir(cloud_save_file)
   if r_station_id is None:
      print("GET CAL FILES:")
      cal_files= get_cal_files(None, cam)
   else:
      cal_files= glob.glob(r_cal_dir + "*" + cam + "*calparams.json")
      print("REMOTE CAL FILES:")

   ci_data = []
   for df in cal_files:
      if len(df) == 2:
         file, res = df
      else:
         file = df
      img_file = file.replace("-calparams.json", "-src.jpg")
      test_img = get_cal_img(img_file)
      if cfe(file) == 1 and cfe(img_file) == 1:
         cp = load_json_file(file)
         cmd = "./AzElGrid.py az_grid " + file
         #os.system(cmd)

         if "user_stars" not in cp:
            print("EVAL CAL: Get image stars", img_file)
            cp['user_stars'] = get_image_stars(img_file, None, json_conf,0)
         jpg_file = img_file.replace(".png", "-src.jpg")
         if cfe(jpg_file) == 0:
            cmd = "convert -quality 80 " + img_file + " " + jpg_file
            os.system(cmd)
         ci_data.append((file, cp['center_az'], cp['center_el'], cp['position_angle'], cp['pixscale'], len(cp['user_stars']), len(cp['cat_image_stars']), cp['total_res_px']))

   temp = sorted(ci_data, key=lambda x: x[0], reverse=True)
   save_json_file(save_file, temp)
   print(save_file)
   if cfe(cdir, 1) == 1:
      save_json_file(cloud_save_file, temp)
   return(temp)

def get_med_cal(json_conf, cam, ci_data=None, this_date= None):
   year = datetime.now().strftime("%Y")
   ci_dir = ARC_DIR + "CAL/AUTOCAL/" + year + "/solved/"
   ci_file = ci_dir + "cal_index-" + cam + ".json" 
   if ci_data is None:
      data = load_json_file(ci_file)
      ci_data = data['ci_data']
   ci_data = sorted(ci_data, key=lambda x: x[6], reverse=False)
   azs = []
   els = []
   poss = []
   pxs = []
   for data in ci_data:
      print(data)
      azs.append(float(data[1]))
      els.append(float(data[2]))
      poss.append(float(data[3]))
      pxs.append(float(data[4]))
   med_az = float(np.median(azs))
   med_el = float(np.median(els))
   med_pos = float(np.median(poss))
   med_px = float(np.median(pxs))
   return(med_az, med_el, med_pos, med_px)
   #save_json_file(ci_dir + "cal_index" + cam + ".json", ci_data)

def review_all_cals(json_conf):
   for cam in json_conf['cameras']:
      cams_id = json_conf['cameras'][cam]['cams_id']
      review_cals(json_conf, cams_id)

def review_cals(json_conf, cam=None):
   year = datetime.now().strftime("%Y")
   print("CAM:", cam)
   ci_data = cal_index(cam, json_conf)
   ci_dir = ARC_DIR + "CAL/AUTOCAL/" + year + "/solved/"
   ci_file = ci_dir + "cal_index-" + cam + ".json"
   med_data = get_med_cal(json_conf, cam, ci_data, this_date= None)
   data = {}
   data['ci_data'] = ci_data
   data['med_data'] = med_data
   save_json_file(ci_file, data)
   print(ci_file)
   
   mask_file = MASK_DIR + cam + "_mask.png"
   if cfe(mask_file) == 1:
      mask_img = cv2.imread(mask_file)
      mask_img = cv2.resize(mask_img, (1920,1080))
   else:
      mask_img = None



   if cam is None:
      cal_dir = ARC_DIR + "CAL/AUTOCAL/" + year + "/solved/*.png"
   else:
      cal_dir = ARC_DIR + "CAL/AUTOCAL/" + year + "/solved/*" + cam + "*.png"
   #files = glob.glob(cal_dir)
   files = []
   autocal_dir = "/mnt/ams2/meteor_archive/" + STATION_ID + "/CAL/AUTOCAL/" + year + "/solved/"
   cal_files= get_cal_files(None, cam)
   for data in ci_data:
      file = data[0]
      file = file.replace("-calparams.json", ".png")
      print(file)
      files.append(file)
   #ccc = input("continue")
   cal_files = []
   for file in sorted(files, reverse=True):
      if "grid" not in file and "tn" not in file and "stars" not in file and "blend" not in file:
         (f_datetime, cam, f_date_str,y,m,d, h, mm, s) = convert_filename_to_date_cam(file)
         cal_files.append((cam, file))

   # get the medians first
   temp = sorted(cal_files, key=lambda x: x[0], reverse=False)
   cal_data = []
   for cam, file in temp:
      cp_file = file.replace(".png", "-calparams.json")
      print(cp_file)
      cp = load_json_file(cp_file)
      if "total_res_px" not in cp:
         cp['total_res_px'] = 20
      cal_data.append((cam, file, cp['center_az'], cp['center_el'], cp['position_angle'], cp['pixscale'], cp['total_res_px']))
      #cp['user_stars'] = get_image_stars(file, None, json_conf,0)
      #print("UPDATING STAR DATA.")
      save_json_file(cp_file, cp)
   med_data = find_meds(cal_data)

   #print(med_data)
   #exit()
   good_cal_files = []

   mcp_file = autocal_dir + "multi_poly-" + STATION_ID + "-" + cam + ".info"
   if cfe(mcp_file) == 1:
      mcp = load_json_file(mcp_file)
      # GET EXTRA STARS?
   else:
      mcp = None

   for file in files:
      if "grid" not in file and "tn" not in file and "stars" not in file and "blend" not in file:
         (f_datetime, cam, f_date_str,y,m,d, h, mm, s) = convert_filename_to_date_cam(file)
         print("FILE:", file)


         cp_file = file.replace(".png", "-calparams.json")
         if cfe(file) == 0:
            cp_file = cp_file.replace("-stacked", "")
            cp_file = cp_file.replace("-stacked", "")
            if cfe(file) == 0:
               print("This cal file is bad and should be removed?", file)
               log = open("/mnt/ams2/logs/badcal.txt", "a")
               log.write(file)
               log.close()

            continue 
         cp = load_json_file(cp_file)
         if mcp is not None:
            cp['x_poly'] = mcp['x_poly']
            cp['y_poly'] = mcp['y_poly']
            cp['x_poly_fwd'] = mcp['x_poly_fwd']
            cp['y_poly_fwd'] = mcp['y_poly_fwd']

         if 'user_stars_v' not in cp:
            cp['user_stars'] = get_image_stars(file, None, json_conf,0)
            cp['user_stars_v'] = 1
            save_json_file(cp_file, cp)

         if cfe(file) == 0:
            print("WTF:", file)
            exit()
         cal_img = cv2.imread(file)
         #cal_img = cv2.cvtColor(cal_img, cv2.COLOR_BGR2GRAY)
         if mask_img is not None:
            cal_img = cv2.subtract(cal_img, mask_img)
         if cfe(cp_file) == 1:
            print("EVAL FILE:", file, cal_img.shape)
            cp, bad_stars, marked_img = eval_cal(cp_file,json_conf,cp,cal_img, mask_img)

            marked_img_file = cp_file.replace("-calparams.json", "-marked.jpg")
            cv2.imwrite(marked_img_file, marked_img)
            print("MARKED:", marked_img_file)

            #print("CAT ", cp['cat_image_stars'])
            #cp = remove_bad_stars(cp, bad_stars)
            print("CAT /USER ", len(cp['cat_image_stars']), len(cp['user_stars']))
            if len(cp['user_stars']) > 0:
               stars_matched = len(cp['cat_image_stars']) / len(cp['user_stars'])
            else:
               print("NO USER STARS????", cp_file)
               continue
               #exit()
            print("STARS MATCHED:", stars_matched)
            print("CP:", cp_file, cp['center_az'], cp['center_el'], cp['position_angle'], cp['pixscale'])
            if cp['total_res_px'] > 15:
               #cp = get_best_cal_new(cp_file, json_conf)
               #cp = optimize_matchs(cp_file,json_conf,cp,cal_img)
               az_guess, el_guess, pos_ang_guess, pix_guess = get_cam_best_guess(cam, json_conf)
               if az_guess != 0:
                  cp['center_az'] = float(az_guess)
                  cp['center_el'] = float(el_guess)
                  cp['position_angle'] = float(pos_ang_guess )
                  cp['pixscale'] = float(pix_guess )

                  cp = update_center_radec(cp_file,cp,json_conf)
                  cp['ra_center'] = float( cp['ra_center'])
                  cp['dec_center'] = float( cp['dec_center'])
            # END HERE FOR TESTING
            #continue

            #if stars_matched < .3:
               # BAD CAL PARAMS HERE?
            #   continue
            if len(cp['cat_image_stars']) > 5:
               cp['cat_image_stars'], bad_stars = mag_report(cp['cat_image_stars'], 0)
            else:
               print(cp)
               continue

            #if abs(med_data[cam]['med_pa'] - cp['position_angle']) > 10 and cp['total_res_px'] > 20:
            if False:
               print("POSSIBLE ERROR HERE. OVERRIDE POS ANG WITH MEDIAN.")
               cp['position_angle'] = med_data[cam]['med_pa']
               cp['center_az'] = med_data[cam]['med_az']
               cp['center_el'] = med_data[cam]['med_el']
               cp['pixscale'] = med_data[cam]['med_ps']
            print("BEFORE RES:", cp['total_res_px'])
            for st in bad_stars:
               print(st)
            if False:
            #if 'refit' in cp and cp['total_res_px'] < 3):
               print("SKIP REFIT!")
            else:
               start_res = cp['total_res_px']
               if "refit" in cp:
                  cp['refit'] = 1
               else:
                  cp['refit'] = 1

               new_cp = cp
               #new_cp = minimize_fov(cp_file, cp, cp_file,cal_img,json_conf )
               end_res = new_cp['total_res_px']
               #if len(new_cp['cat_image_stars']) > 5:
               #   new_cp['cat_image_stars'], bad_stars = mag_report(new_cp['cat_image_stars'], 0)
               if end_res < start_res:
                  print("SAVING CAL.")
                  cp = new_cp
                  save_json_file(cp_file, new_cp)
               else:
                  #print("AFTER RES NOT BETTER THAT BEFORE. :", cp['total_res_px'])
                  print("SAVING CAL.")
                  save_json_file(cp_file, cp)
            cal_files.append((cam, file))
            if "total_res_px" in cp and "cat_image_stars" in cp:
               if cp['total_res_px'] < 10 and len(cp['cat_image_stars']) > 10:
                  good_cal_files.append((cam, cp_file, cp['total_res_px']))
   print("CAL INDEX:", ci_dir + "cal_index-" + cam + ".json")


   return(good_cal_files, ci_data)

def cal_report(json_conf):
   ac_files = []
   for cam in json_conf['cameras']:
      cams_id = json_conf['cameras'][cam]['cams_id']
      cal_files= get_cal_files(None, cams_id)
      #print(cal_files)
      for ff in cal_files:
         print(ff[0])
         ac_files.append(ff[0])
   autocal_report("solved", ac_files)


def min_pos_angle(file,nc,json_conf):
   min_res = 9999999
   best_pos = None
   for pos in range(0,360):
      if pos % 10 == 0:
         nc['position_angle'] = pos
         cat_stars = get_catalog_stars(nc)
         cal_params = pair_stars(nc, file, json_conf)
         tres = 0
         for star in cal_params['cat_image_stars']:
            dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int = star
            #cv2.circle(img,(six,siy), 10, (128,128,128), 1)
            #cv2.circle(img,(int(new_x),int(new_y)), 10, (128,128,255), 1)
            #cv2.circle(img,(int(new_cat_x),int(new_cat_y)), 10, (128,255,128), 1)
            tres += cat_dist
         avg_res = tres / len(cal_params['cat_image_stars'])
         if avg_res < min_res:
            min_res = avg_res
            best_pos = pos
   print("BEST POS:", best_pos)
   return(best_pos)


def find_meds(cal_data):
   # find med val for each camera for each var
   med_data = {}
   for data in cal_data:
      (cam, file, center_az, center_el, position_angle, pixscale,res) = data
      if cam not in med_data:
         med_data[cam] = {}
         med_data[cam]['files'] = []
         med_data[cam]['az'] = []
         med_data[cam]['el'] = []
         med_data[cam]['pa'] = []
         med_data[cam]['ps'] = []
         med_data[cam]['res'] = []
      if res < 10:
         med_data[cam]['files'].append(file)
         med_data[cam]['az'].append(float(center_az))
         med_data[cam]['el'].append(float(center_el ))
         med_data[cam]['pa'].append(float(position_angle))
         med_data[cam]['ps'].append(float(pixscale))
         med_data[cam]['res'].append(float(res))
   for cam in med_data:
      med_data[cam]['med_az'] = np.median(med_data[cam]['az'])
      med_data[cam]['med_el'] = np.median(med_data[cam]['el'])
      med_data[cam]['med_pa'] = np.median(med_data[cam]['pa'])
      med_data[cam]['med_ps'] = np.median(med_data[cam]['ps'])
      med_data[cam]['std_az'] = np.std(med_data[cam]['az'])
      med_data[cam]['std_el'] = np.std(med_data[cam]['el'])
      med_data[cam]['std_pa'] = np.std(med_data[cam]['pa'])
      med_data[cam]['std_ps'] = np.std(med_data[cam]['ps'])
   return(med_data)

def cal_all(json_conf):
   year = datetime.now().strftime("%Y")
   cal_dir = ARC_DIR + "CAL/AUTOCAL/" + year + "/*.png"
   files = glob.glob(cal_dir)
   print(cal_dir)
   for file in files:
      print("TRYING.")
      autocal(file, json_conf, 1)
      #exit()


def autocal(image_file, json_conf, show = 0):
   print("Autocal.")
   '''
      Open the image and find stars in it. 
      If there are not enough stars move the image to the 'bad' dir and end. 

      Make plate from found stars
      Send plate through plate solve 
      If the plate fails move the file to the 'failed' dir and end.

      If plate is a success save the calib info. 

      Figure out the poly lens stuff later or can do manually. This is mostly for screening good images from sense up folder.
  
   '''

   img = cv2.imread(image_file, 0)

   (f_datetime, cam, f_date_str,y,m,d, h, mm, s) = convert_filename_to_date_cam(image_file)
   cam = cam.replace(".png", "")
   masks = get_masks(cam, json_conf,1)
   try:
      star_img = img.copy()
   except: 
      print("BAD INPUT FILE:", image_file)
      os.system("rm " + image_file) 
      return()

   #img = mask_frame(img, [], masks, 5)

   stars = get_image_stars(image_file, None, json_conf,0)
   print("STARS:", len(stars))
   year = datetime.now().strftime("%Y")
   autocal_dir = "/mnt/ams2/meteor_archive/" + STATION_ID + "/CAL/AUTOCAL/" + year + "/solved/"
   autocal_bad = "/mnt/ams2/meteor_archive/" + STATION_ID + "/CAL/AUTOCAL/" + year + "/bad/"
   autocal_fail = "/mnt/ams2/meteor_archive/" + STATION_ID + "/CAL/AUTOCAL/" + year + "/failed/"
   if cfe(autocal_dir, 1) == 0:
      os.makedirs(autocal_dir)
   if cfe(autocal_bad, 1) == 0:
      os.makedirs(autocal_bad)
   if cfe(autocal_fail, 1) == 0:
      os.makedirs(autocal_fail)
   if len(stars) < 7:
      print("Not enough stars to solve.")
      cmd = "mv " + image_file + " " + autocal_bad
      print(cmd)
      os.system(cmd)
      return(0)
   mcp_file = autocal_dir + "multi_poly-" + STATION_ID + "-" + cam + ".info"
   if cfe(mcp_file) == 1:
      mcp = load_json_file(mcp_file)
   else:
      mcp = None 


   if SHOW == 1:
      for star in stars:
         (x,y,sint) = star
         #cv2.circle(star_img,(x,y), 10, (128,128,255), 1)
          
      show_image(star_img, 'pepe', 300)


   plate_image, star_points = make_plate_image(img.copy(), stars )



   plate_file = image_file.replace(".png", ".jpg")
   cv2.imwrite(plate_file, plate_image)
   if SHOW == 1:
      show_image(img, 'pepe', 300)
      show_image(plate_image, 'pepe', 300)
   status, cal_params,wcs_file = solve_field(plate_file, stars, json_conf)
   if status == 1:
      if float(cal_params['position_angle']) < 0:
         cal_params['position_angle'] = float(cal_params['position_angle']) + 180
   print(cal_params)

   if mcp is not None:
      cal_params['x_poly'] = mcp['x_poly']
      cal_params['y_poly'] = mcp['x_poly']
      cal_params['x_poly_fwd'] = mcp['x_poly_fwd']
      cal_params['y_poly_fwd'] = mcp['y_poly_fwd']

   ifn = image_file.split("/")[-1]
   idir = image_file.replace(ifn, "")
   tdir = idir + "temp/"
   fdir = idir + "failed/"
   bdir = idir + "bad/"
   sdir = idir + "solved/"
   new_image_file = tdir + ifn
   if cfe(tdir, 1) == 0:
      os.makedirs(tdir)
   if cfe(fdir, 1) == 0:
      os.makedirs(fdir)
   if cfe(bdir, 1) == 0:
      os.makedirs(bdir)
   if cfe(sdir, 1) == 0:
      os.makedirs(sdir)
   os.system("cp " + image_file + " " + tdir)

   cal_params_file = wcs_file.replace(".wcs", "-calparams.json")

   if status == 1:
      print("Plate solve passed. Time for lens modeling!") 
      save_json_file(cal_params_file, cal_params)

      #if SHOW == 1:
      #   grid_file = wcs_file.replace(".wcs", "-grid.png")
      #   grid_image = cv2.imread(grid_file)
      #   show_image(grid_image, 'pepe', 90)


   else:
      print("Plate solve failed. Clean up the mess!") 
      # rm original file and temp files here
      cmd = "mv " + image_file + "* " + fdir
      print(cmd)
      #os.system(cmd)
      return()

   # code below this point should only happen on the files that passed the plate solve. 

   cat_stars = get_catalog_stars(cal_params)
   cal_params = pair_stars(cal_params, cal_params_file, json_conf)
   fn, dir = fn_dir(image_file)
   #guess_cal("temp/" + fn, json_conf, cal_params )

   for star in cal_params['cat_image_stars']:
      print(star)

   #cal_params['cat_image_stars']  = remove_dupe_cat_stars(cal_params['cat_image_stars'])


   if SHOW == 1:
      marked_img = make_fit_image(img, cal_params['cat_image_stars'])
      show_image(marked_img, 'pepe', 90)

   this_poly = np.zeros(shape=(4,), dtype=np.float64)
   cal_params['orig_pixscale'] = cal_params['pixscale']
   cal_params['orig_pos_ang'] = cal_params['position_angle']

   az = np.float64(cal_params['center_az'])
   el = np.float64(cal_params['center_el'])
   pos = np.float64(cal_params['position_angle'])
   pixscale = np.float64(cal_params['pixscale'])
   x_poly = np.float64(cal_params['x_poly'])
   y_poly = np.float64(cal_params['y_poly'])
   print("CAL PARAMS:", cal_params)
   print("CAL PARAMS FILE:", cal_params_file)
   #cal_params = minimize_fov(cal_params_file, cal_params, image_file,img,json_conf )
   cal_params = update_center_radec(cal_params_file,cal_params,json_conf)

   save_json_file(cal_params_file, cal_params)
   print("SAVED:", cal_params_file)
   #exit()
   if mcp is None:
      print("Skip mini poly")
      #status, cal_params  = minimize_poly_params_fwd(cal_params_file, cal_params,json_conf)
   else:
      status = 1
   if status == 0:
      # ABORT!   
      print("Fit Process Faild! Clean up the mess!")
      # rm original file and temp files here
      cmd = "mv " + image_file + "* " + fdir
      os.system(cmd)
      return()


   cmd = "./AzElGrid.py az_grid " + cal_params_file + ">/tmp/mike.txt 2>&1"
   print(cmd)
   os.system(cmd)

   cat_stars = get_catalog_stars(cal_params)
   cal_params = pair_stars(cal_params, cal_params_file, json_conf)
   print("SAVING:", cal_params_file)
   save_json_file(cal_params_file, cal_params)
   
   #star_image = draw_star_image(img, cal_params['cat_image_stars'], cal_params) 
   #if CAL_MOVIE == 1:
   #   fn, dir = fn_dir(image_file)
   #   cv2.imwrite("tmp_vids/" + fn, star_image)

   
   new_cal_file = freecal_copy(cal_params_file, json_conf)

   cpf = cal_params_file.split("/")[-1]
   pimf = cpf.replace("-calparams.json", ".jpg")
   imf = cpf.replace("-calparams.json", ".png")
   azf = cpf.replace("-calparams.json", "-azgrid.png")
   raf = cpf.replace("-calparams.json", "-grid.png")
   saf = cpf.replace("-calparams.json", "-stars.png")

   cmd = "mv " + idir + plate_file + " " + sdir
   os.system(cmd)

   cmd = "mv " + idir + pimf + " " + sdir
   os.system(cmd)

   cmd = "mv " + tdir + cpf + " " + sdir
   os.system(cmd)

   cmd = "mv " + idir + imf + " " + sdir
   os.system(cmd)

   cmd = "mv " + tdir + pimf + " " + sdir
   os.system(cmd)

   cmd = "mv " + tdir + azf + " " + sdir
   os.system(cmd)

   cmd = "mv " + tdir + raf + " " + sdir
   os.system(cmd)

   cmd = "mv " + tdir + saf + " " + sdir
   os.system(cmd)
   cmd = "./Process.py refit " + new_cal_file
   os.system(cmd)

def cat_star_report(cat_image_stars, multi=2.5):
   #multi = 100
   c_dist = []
   m_dist = []
   for star in cat_image_stars:
      dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int = star
      c_dist.append(abs(cat_dist))
      m_dist.append(abs(match_dist))
   med_c_dist = np.median(c_dist)
   med_m_dist = np.median(m_dist)
   if med_c_dist < 1:
      med_c_dist = 1 

   clean_stars = [] 
   c_dist = []
   m_dist = []
   for star in cat_image_stars:
      dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int = star
      if cat_dist > med_c_dist * multi:
         print("BAD", dcname, cat_dist, med_c_dist - cat_dist  )
      else:
         print(dcname, cat_dist, med_c_dist - cat_dist  )
         c_dist.append(abs(cat_dist))
         m_dist.append(abs(match_dist))
         clean_stars.append(star)
   return(clean_stars, np.mean(c_dist), np.mean(m_dist))
  
def make_fit_image(image, cat_image_stars) :
   marked_img = image.copy()
   for star in cat_image_stars:
      dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int = star

      new_x = int(new_x)
      new_y = int(new_y)


      # catalog star enhanced position
      cv2.rectangle(marked_img, (new_x-10, new_y-10), (new_x+10, new_y+10), (200, 200, 200), 1)

      # catalog original star position
      cv2.rectangle(marked_img, (new_cat_x-15, new_cat_y-15), (new_cat_x+15, new_cat_y+15), (90, 90, 90), 1)

      # image star location position
      cv2.circle(marked_img,(six,siy), 10, (128,128,255), 1)

      # draw line from original star to enhanced star locations
      #cv2.line(marked_img, (new_cat_x,new_cat_y), (new_x,new_y), (255), 2)

      # draw line from enhanced star locations to image star location. This is the value we want to minimize! Less is better
      cv2.line(marked_img, (six,siy), (new_x,new_y), (255), 2)
   return(marked_img)

def get_image_stars_with_catalog(file, img, cp, json_conf, cat_stars=None, show = 0):
   temp_img = img.copy()
   gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

   cat_stars = get_catalog_stars(cp)
   console_image = np.zeros((720,1280),dtype=np.uint8)

   sc = 0
   srow = 0
   scol = 0
   good_stars = []
   star_dict = {}
   all_points = []
   cat_image_stars = []
   for cat_star in cat_stars:
      (name,mag,ra,dec,new_cat_x,new_cat_y) = cat_star
      dcname = str(name.decode("utf-8"))
      dbname = dcname.encode("utf-8")

       
      new_cat_x = int(new_cat_x)
      new_cat_y = int(new_cat_y)
      x1 = new_cat_x-10
      x2 = new_cat_x+10
      y1 = new_cat_y-10
      y2 = new_cat_y+10
      cw = x2 - x1
      ch = y2 - y1
      if x1 < 0 or x2 >= gray_img.shape[1]:
         continue
      if y1 < 0 or y2 >= gray_img.shape[0]:
         continue
      star_img = gray_img[new_cat_y-10:new_cat_y+10,new_cat_x-10:new_cat_x+10]
      status = star_cnt(star_img)
      max_px, avg_px, px_diff,max_loc,star_int = eval_cnt(star_img)

      six = new_cat_x - 10 + max_loc[0]
      siy = new_cat_y - 10 + max_loc[1]
      res_x = abs(new_cat_x - six)
      res_y = abs(new_cat_y - siy)
      row_y =  sc * 25
      col_x =  300 * scol 
      if col_x + 25 <= 1920:
         console_image[row_y:row_y+ch, col_x:col_x+cw] = star_img
         flux = np.sum(star_img)
         avg = np.median(star_img)
         bg = avg * star_img.shape[0] * star_img.shape[1]
         intensity = flux - bg 
         if intensity > 100 and status == 1 and intensity < 5000:
            if SHOW == 1:
               desc = str(name) + " mag " + str(mag) + " " + str(int(intensity)) + "res x/y " + str(res_x) + " / " + str(res_y) 
               cv2.putText(console_image, desc,  (int(col_x+cw+25),int(row_y+12)), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
               cv2.imshow('pepe', console_image)
               cv2.waitKey(0)
            if row_y + 25 >= 720:
               sc = 0
               scol += 1
            else:
               sc += 1 
            key = str(six) 
            temp_key = key[0:-1]
            new_key = temp_key + "0"
            print("KEY/NEW KEY:", key, new_key)
            new_key = new_key + "-" +  str(siy)[0:-1]
            new_key += "0"
            print("KEY/TEMP KEY:", key, new_key)
            if key not in star_dict:
               star_dict[key] = {}
               star_dict[key]['data'] = [six,siy,star_int]
               star_dict[key]['count'] = 1
               star_dict[key]['cat_star'] = (dcname,mag,ra,dec,new_cat_x,new_cat_y) 

            else:
               print("DUPE STAR") 
               star_dict[key]['data'] = [six,siy,star_int]
               star_dict[key]['count'] = 2 
               star_dict[key]['cat_star'] = (dcname,mag,ra,dec,new_cat_x,new_cat_y) 
            all_points.append((six,siy))
         else: 
            cv2.rectangle(temp_img, (new_cat_x-10, new_cat_y-10), (new_cat_x + 10, new_cat_y + 10), (255, 0, 0), 1)

   good_stars = []
   for key in star_dict:
      if star_dict[key]['count'] == 1:
         name,mag,ra,dec,new_cat_x,new_cat_y = star_dict[key]['cat_star']
         six, siy, star_int = star_dict[key]['data']
         close = check_close (set(all_points), six,siy, 50)
         print("Stars close to this one including itself:", close)
         if close <= 1:
            new_cat_x, new_cat_y = int(new_cat_x), int(new_cat_y)
            good_stars.append(star_dict[key]['data'])
            cv2.circle(temp_img,(six,siy), 5, (128,128,128), 1)
            cv2.rectangle(temp_img, (new_cat_x-10, new_cat_y-10), (new_cat_x + 10, new_cat_y + 10), (0, 0, 255), 1)
            cv2.line(temp_img, (six,siy), (new_cat_x,new_cat_y), (128,128,128), 1)
            match_dist = calc_dist((new_cat_x,new_cat_y), (six,siy))
            cat_dist = calc_dist((new_cat_x,new_cat_y), (six,siy))
            cat_image_stars.append((name,mag,ra,dec,ra,dec,match_dist,new_cat_x,new_cat_y,0,0,new_cat_x,new_cat_y,six,siy,cat_dist,star_int))


   print("GOOD STARS:", good_stars)
   cp['cat_image_stars'] = cat_image_stars
   return(good_stars, cp)

def check_close(point_list, x, y, max_dist):
   count = 0
   for tx,ty in point_list:
      dist = calc_dist((tx,ty), (x,y))
      if dist <= max_dist:
         count += 1
   return(count)

def find_stars_with_grid_old(image):
   gsize = 640 
   height, width = image.shape[:2]
   best_stars = []

   sw = int(1920/gsize)  
   sh = int(1080/gsize)  
   for i in range(0,sw):
      for j in range(0,sh):
         x1 = i * gsize
         y1 = j * gsize
         x2 = x1 + gsize 
         y2 = y1 + gsize 
         if x2 >= 1920:
            x2 = 1920
         if y2 >= 1080:
            y2 = 1080 
         print(x1, x2, y1,y2)
         if True:
            if x2 <= width and y2 <= height:
               grid_img = image[y1:y2,x1:x2]
               grid_val = np.mean(grid_img)
               max_px, avg_px, px_diff,max_loc,grid_int = eval_cnt(grid_img.copy(), grid_val)
               bx, by = max_loc
               bx1 = bx - 5
               by1 = by - 5
               bx2 = bx + 5
               by2 = by + 5
               cv2.rectangle(grid_img, (bx1, by1), (bx2, by2 ), (255, 255, 255), 1)
               if 1000 < grid_int < 14000:
                  best_stars.append((bx+x1,by+y1,grid_int))
   temp = sorted(best_stars, key=lambda x: x[2], reverse=True)
   return(temp)

def find_stars_with_grid(img):
   raw_img = img.copy()
   gsize = 250,250
   ih,iw = img.shape[:2]
   rows = int(int(ih) / gsize[1])
   cols = int(int(iw) / gsize[0])
   stars = []
   bad_stars = []
   for col in range(0,cols+1):
      for row in range(0,rows+1):
         x1 = col * gsize[0]
         y1 = row * gsize[1]
         x2 = x1 + gsize[0]
         y2 = y1 + gsize[1]
         #print("GRID:", col,row)
         #print("GRID:",x1,y1,x2,y2)
         #print("GRID:",iw,ih)
         if x2 >= iw:
            x2 = iw
         if y2 >= ih:
            y2 = ih 
         gimg = img[y1:y2,x1:x2]
         avg = np.median(gimg)
         best_thresh = avg + 40 
         _, star_bg = cv2.threshold(gimg, best_thresh, 255, cv2.THRESH_BINARY)
         thresh_obj = cv2.dilate(star_bg, None , iterations=4)

         res = cv2.findContours(thresh_obj.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
         if len(res) == 3:
            (_, cnts, xx) = res
         else:
            (cnts ,xx) = res
         cc = 0
         huge = []
         for (i,c) in enumerate(cnts):
            x,y,w,h = cv2.boundingRect(cnts[i])
            px_val = int(img[y,x])
            cnt_img = gimg[y:y+h,x:x+w]
            cnt_img = cv2.GaussianBlur(cnt_img, (7, 7), 0)

            max_px, avg_px, px_diff,max_loc,star_int = eval_cnt(cnt_img.copy(), avg)
            bx,by = max_loc
            bx = bx + x
            by = by + y
            bx1,by1,bx2,by2= bound_cnt(bx,by,gsize[1],gsize[0],10)
            new_cnt_img = gimg[by1:by2,bx1:bx2]

            name = "/mnt/ams2/tmp/cnt" + str(cc) + ".png"
            if star_int > 50:
               stars.append((bx+x1,by+y1,int(star_int)))
            else:
               bad_stars.append((bx+x1,by+y1,int(star_int)))

   print("GRID STARS FOUND:", stars)
   print("BAD STARS::", bad_stars)
   return(stars)

def get_image_stars(file=None,img=None,json_conf=None,show=0):

   stars = []
   huge_stars = []
   if img is None:
      print("Loading image:", file)
      img = cv2.imread(file, 0)
   print("Loaded.")
   if img.shape[0] != '1080':
      img = cv2.resize(img, (1920,1080))

   if len(img.shape) > 2:
      img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
   show_pic = img.copy()
   print("Finding stars.")
   #exit()
   


   raw_img = img.copy()
   (f_datetime, cam, f_date_str,y,m,d, h, mm, s) = convert_filename_to_date_cam(file)
   cam = cam.replace(".png", "")
   #masks = get_masks(cam, json_conf,1)
   #img = mask_frame(img, [], masks, 5)

   mask_file = MASK_DIR + cam + "_mask.png"
   print("MASK FILE:", mask_file)
   if cfe(mask_file) == 1:
      mask_img = cv2.imread(mask_file, 0)
      mask_img = cv2.resize(mask_img, (1920,1080))
   else:
      mask_img = None
   if mask_img is not None:
      mask_img = cv2.resize(mask_img, (img.shape[1],img.shape[0]))
      print("IMAGER:", img.shape)
      print("MASK:", mask_img.shape)
      print("MASK SUBTRACTED.")
      img = cv2.subtract(img, mask_img)
   cv2.imwrite("/mnt/ams2/masked.jpg", img)
   #cv2.imshow('pepe', img)

   best_stars = find_stars_with_grid(img)
   print("FOUND:", len(best_stars ))
   for star in best_stars:
      x,y,z = star
      cv2.circle(img, (int(x),int(y)), 5, (128,128,128), 1)
      print(star)
   #cv2.imshow('pepe', img)
   #cv2.waitKey(0)
   return(best_stars)


   avg = np.median(img) 

   best_thresh = avg + 50
   _, star_bg = cv2.threshold(img, best_thresh, 255, cv2.THRESH_BINARY)
   thresh_obj = cv2.dilate(star_bg, None , iterations=4)
   #cv2.waitKey(0)

   res = cv2.findContours(thresh_obj.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
   if len(res) == 3:
      (_, cnts, xx) = res
   else:
      (cnts ,xx) = res
   cc = 0
   huge = []
   for (i,c) in enumerate(cnts):
      x,y,w,h = cv2.boundingRect(cnts[i])


      px_val = int(img[y,x])
      cnt_img = raw_img[y:y+h,x:x+w]
      cnt_img = cv2.GaussianBlur(cnt_img, (7, 7), 0)

      max_px, avg_px, px_diff,max_loc,star_int = eval_cnt(cnt_img.copy(), avg)
      bx,by = max_loc
      bx = bx + x
      by = by + y
      bx1,by1,bx2,by2= bound_cnt(bx,by,1920,1080,10)
      new_cnt_img = raw_img[by1:by2,bx1:bx2]
      print("GET USER STARS:", bx1,bx2,by1,by2)

      name = "/mnt/ams2/tmp/cnt" + str(cc) + ".png"
      #star_test = test_star(cnt_img)
      if star_int > 100:
          #cv2.rectangle(show_pic, (bx1, by1), (bx2, by2 ), (255, 255, 255), 1)
          stars.append((x,y,int(star_int)))

          show_pic[950:980,0:100] = 0
          cv2.putText(show_pic, str(star_int),  (int(10),int(980)), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 1)
          bcnt = cv2.resize(new_cnt_img, (100,100))
          show_pic[980:1080,0:100] = bcnt
          if SHOW == 1:
             dsp = cv2.resize(show_pic, (1280,720))
             cv2.imshow('pepe', dsp)
             cv2.waitKey(0)
      else:
          cv2.rectangle(show_pic, (bx1, by1), (bx2, by2 ), (150, 150, 150), 1)
      cc = cc + 1

   temp = sorted(stars, key=lambda x: x[2], reverse=True)
   stars = temp
   #stars = temp[0:50]
   
   #print("STARS BEFORE VAL:", len(stars))
   stars = validate_stars(stars, raw_img)
   #print("STARS AFTER VAL:", len(stars))

   return(stars)


def eval_cnt(cnt_img, avg_px=5 ):
   cnt_img = cv2.GaussianBlur(cnt_img, (7, 7), 0)
   cnth,cntw = cnt_img.shape
   max_px = np.max(cnt_img)
   avg_px = np.mean(cnt_img)
   med_int = np.median(cnt_img)
   #(cnt_img[0,0] + cnt_img[-1,0] + cnt_img[0,-1] + cnt_img[-1,-1]) / 4
   avg_int = med_int * cnt_img.shape[0] * cnt_img.shape[1]
   max_int = np.sum(cnt_img)

   px_diff = max_px - avg_px
   int_diff = max_int - avg_int

   int_cnt = cnt_img.copy()
   for x in range(0, int_cnt.shape[1]):
      for y in range(0, int_cnt.shape[0]):
         px = int_cnt[y,x]
         if px <= med_int + 5:
            int_cnt[y,x] = 0

   star_int = int(np.sum(int_cnt))
   min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(cnt_img)

   cnt_res = cv2.findContours(int_cnt.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
   if len(cnt_res) == 3:
      (_, cnts, xx) = cnt_res
   elif len(cnt_res) == 2:
      (cnts, xx) = cnt_res

   if len(cnts) == 1:
      for (i,c) in enumerate(cnts):
         px_diff = 0
         x,y,w,h = cv2.boundingRect(cnts[i])
         blob_x = int(x) + int(w/2) 
         blob_y = int(y) + int(h/2) 
         #cv2.rectangle(int_cnt, (blob_x-1, blob_y-1), (blob_x+1, blob_y+1), (255, 255, 255), 1)
   else:
      blob_x = int(max_loc[0])
      blob_y = int(max_loc[1])
   

   #print(blob_x, blob_y, star_int)

   return(max_px, avg_px,px_diff,(blob_x,blob_y),star_int)

def make_plate_image(image, file_stars): 
   ih, iw = image.shape[:2]
   if len(image.shape) > 2:
      image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
      

   plate_image = np.zeros((ih,iw),dtype=np.uint8)
   hd_stack_img = image
   hd_stack_img_an = hd_stack_img.copy()
   star_points = []
   print("TEST")
   for file_star in file_stars:
      (ix,iy,bp) = file_star
         
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
         try:
            cnt_img = clean_star_bg(cnt_img, bgavg + 3)

            #cv2.rectangle(hd_stack_img_an, (x+mx-5-15, y+my-5-15), (x+mx+5-15, y+my+5-15), (128, 128, 128), 1)
            #cv2.rectangle(hd_stack_img_an, (x+mx-15-15, y+my-15-15), (x+mx+15-15, y+my+15-15), (128, 128, 128), 1)
            star_points.append([x+mx,y+my])
            plate_image[cy1:cy2,cx1:cx2] = cnt_img
         except:
            print("Failed star")

   points_json = {}
   points_json['user_stars'] = star_points

   return(plate_image,star_points)


def clean_star_bg(cnt_img, bg_avg):
   max_px = np.max(cnt_img)
   min_px = np.min(cnt_img)
   avg_px = np.mean(cnt_img)
   halfway = int((max_px - min_px) / 2)
   cnt_img.setflags(write=1)
   for x in range(0,cnt_img.shape[1]):
      for y in range(0,cnt_img.shape[0]):
         px_val = cnt_img[y,x]
         if px_val < bg_avg + halfway:
            #cnt_img[y,x] = random.randint(int(bg_avg - 3),int(avg_px))
            pxval = cnt_img[y,x]
            pxval = int(pxval) / 2
            cnt_img[y,x] = 0
   return(cnt_img)

def save_cal_params(wcs_file,json_conf):
   wcs_info_file = wcs_file.replace(".wcs", "-wcsinfo.txt")
   cal_params_file = wcs_file.replace(".wcs", "-calparams.json")
   fp =open(wcs_info_file, "r")
   cal_params_json = {}
   for line in fp:
      line = line.replace("\n", "")
      field, value = line.split(" ")
      if field == "imagew":
         cal_params_json['imagew'] = value
      if field == "imageh":
         cal_params_json['imageh'] = value
      if field == "pixscale":
         cal_params_json['pixscale'] = value
      if field == "orientation":
         cal_params_json['position_angle'] = float(value) + 180
      if field == "ra_center":
         cal_params_json['ra_center'] = value
      if field == "dec_center":
         cal_params_json['dec_center'] = value
      if field == "fieldw":
         cal_params_json['fieldw'] = value
      if field == "fieldh":
         cal_params_json['fieldh'] = value
      if field == "ramin":
         cal_params_json['ramin'] = value
      if field == "ramax":
         cal_params_json['ramax'] = value
      if field == "decmin":
         cal_params_json['decmin'] = value
      if field == "decmax":
         cal_params_json['decmax'] = value

   ra = cal_params_json['ra_center']
   dec = cal_params_json['dec_center']
   lat = json_conf['site']['device_lat']
   lon = json_conf['site']['device_lng']
   alt = json_conf['site']['device_alt']

   (f_datetime, cam, f_date_str,y,m,d, h, mm, s) = convert_filename_to_date_cam(wcs_file)
   new_date = y + "/" + m + "/" + d + " " + h + ":" + mm + ":" + s
   az, el = radec_to_azel(ra,dec, new_date,json_conf)

   cal_params_json['center_az'] = az
   cal_params_json['center_el'] = el
   #cal_params = default_cal_params(cal_params, json_conf)

 

   save_json_file(cal_params_file, cal_params_json)
   return(cal_params_json)

def radec_to_azel(ra,dec, caldate,json_conf, lat=None,lon=None,alt=None):

   if lat is None:
      lat = json_conf['site']['device_lat']
      lon = json_conf['site']['device_lng']
      alt = json_conf['site']['device_alt']

   body = ephem.FixedBody()
   #print ("BODY: ", ra, dec)
   body._epoch=ephem.J2000

   rah = RAdeg2HMS(ra)
   dech= Decdeg2DMS(dec)

   body._ra = rah
   body._dec = dech

   

   obs = ephem.Observer()
   obs.lat = ephem.degrees(lat)
   obs.lon = ephem.degrees(lon)
   obs.date = caldate
   obs.elevation=float(alt)
   body.compute(obs)
   az = str(body.az)
   el = str(body.alt)

   #print("RADEC_2_AZEL BODY RA:", body._ra)
   #print("RADEC_2_AZEL BODY DEC:", body._dec)
   #print("RADEC_2_AZEL OBS DATE:", obs.date)
   #print("RADEC_2_AZEL OBS LAT:", obs.lat)
   #print("RADEC_2_AZEL OBS LON:", obs.lon)
   #print("RADEC_2_AZEL OBS EL:", obs.elevation)
   #print("RADEC_2_AZEL AZH AZH:", az)
   #print("RADEC_2_AZEL ELH ELH:", el)
   
   (d,m,s) = az.split(":")
   dd = float(d) + float(m)/60 + float(s)/(60*60)
   az = dd

   (d,m,s) = el.split(":")
   dd = float(d) + float(m)/60 + float(s)/(60*60)
   el = dd

   return(az,el)

def HMS2deg(ra='', dec=''):
  RA, DEC, rs, ds = '', '', 1, 1
  if dec:
    D, M, S = [float(i) for i in dec.split()]
    if str(D)[0] == '-':
      ds, D = -1, abs(D)
    deg = D + (M/60) + (S/3600)
    DEC = '{0}'.format(deg*ds)
  
  if ra:
    H, M, S = [float(i) for i in ra.split()]
    if str(H)[0] == '-':
      rs, H = -1, abs(H)
    deg = (H*15) + (M/4) + (S/240)
    RA = '{0}'.format(deg*rs)
  
  if ra and dec:
    return (RA, DEC)
  else:
    return RA or DEC

def RAdeg2HMS( RAin ):
   RAin = float(RAin)
   if(RAin<0):
      sign = -1
      ra   = -RAin
   else:
      sign = 1
      ra   = RAin

   h = int( ra/15. )
   ra -= h*15.
   m = int( ra*4.)
   ra -= m/4.
   s = ra*240.

   if(sign == -1):
      out = '-%02d:%02d:%06.3f'%(h,m,s)
   else: out = '+%02d:%02d:%06.3f'%(h,m,s)

   return out

def Decdeg2DMS( Decin ):
   Decin = float(Decin)
   if(Decin<0):
      sign = -1
      dec  = -Decin
   else:
      sign = 1
      dec  = Decin

   d = int( dec )
   dec -= d
   dec *= 100.
   m = int( dec*3./5. )
   dec -= m*5./3.
   s = dec*180./5.

   if(sign == -1):
      out = '-%02d:%02d:%06.3f'%(d,m,s)
   else: out = '+%02d:%02d:%06.3f'%(d,m,s)

   return out

def pair_stars(cal_params, cal_params_file, json_conf, cal_img=None, show = 0):
   dist_type = "radial"

   (f_datetime, cam, f_date_str,y,m,d, h, mm, s) = convert_filename_to_date_cam(cal_params_file)
   jd = datetime2JD(f_datetime, 0.0)
   hour_angle = JD2HourAngle(jd)

   if cal_img is None:
      img_file = cal_params_file.replace("-calparams.json", ".jpg")
      cal_img = cv2.imread(img_file)
   if len(cal_img.shape) > 2:
      cal_img = cv2.cvtColor(cal_img, cv2.COLOR_BGR2GRAY)

   temp_img = cal_img.copy()
   ih, iw= cal_img.shape[:2]
   ra_center = cal_params['ra_center']
   dec_center = cal_params['dec_center']
   center_az = cal_params['center_az']
   center_el = cal_params['center_el']
   star_matches = []
   my_close_stars = []
   total_match_dist = 0
   total_cat_dist = 0
   total_matches = 0
   cat_stars = get_catalog_stars(cal_params)

   #new_user_stars = []
   #new_stars = []
   #cal_params['user_stars'] = new_user_stars   

   used = {}
   no_match = []

   degrees_per_pix = float(cal_params['pixscale'])*0.000277778
   px_per_degree = 1 / degrees_per_pix

   for data in cal_params['user_stars']:
      if len(data) == 3:
         ix,iy,bp = data
      else:
         ix,iy = data
         bp = 0
      close_stars = find_close_stars((ix,iy), cat_stars)
      found = 0
      for name,mag,ra,dec,new_cat_x,new_cat_y,six,siy,cat_dist in close_stars:
         #dcname = str(name.decode("utf-8"))
         #dbname = dcname.encode("utf-8")
         new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(ix,iy,cal_params_file,cal_params,json_conf)

         ra_data = np.zeros(shape=(1,), dtype=np.float64)
         dec_data = np.zeros(shape=(1,), dtype=np.float64)
         ra_data[0] = ra 
         dec_data[0] = dec

         #ra_data = [cal_params['ra_center']]
         #dec_data = [cal_params['dec_center']]
         x_data, y_data = cyraDecToXY(ra_data, \
               dec_data,
               jd, json_conf['site']['device_lat'], json_conf['site']['device_lng'], cal_img.shape[1], \
               cal_img.shape[0], hour_angle, float(cal_params['ra_center']),  float(cal_params['dec_center']), \
               float(cal_params['position_angle']), \
               px_per_degree, \
               cal_params['x_poly'], cal_params['y_poly'], \
               dist_type, True, False, False)

         new_x = int(x_data[0])
         new_y = int(y_data[0])



         match_dist = abs(angularSeparation(ra,dec,img_ra,img_dec))
         # are all 3 sets of point on the same line
         points = [[ix,iy],[new_x,new_y], [1920/2, 1080/2]]
         xs = [ix,new_x,new_cat_x,1920/2]
         ys = [iy,new_y,new_cat_y,1080/2]
         #line_test = arecolinear(points) 

         lxs = [ix,1920/2]
         lys = [iy,1080/2]
         dist_to_line = poly_fit_check(lxs,lys, new_cat_x,new_cat_y)
         dist_to_line2 = poly_fit_check(lxs,lys, new_x,new_y)
         #cv2.circle(temp_img,(six,siy), 7, (128,128,128), 1)
         #cv2.circle(temp_img,(int(new_cat_x),int(new_cat_y)), 7, (255,128,128), 1)
         #cv2.circle(temp_img,(int(new_x),int(new_y)), 7, (128,128,255), 1)
         used_key = str(ra) + "-" + str(dec)

         if match_dist >= 10 or used_key in used:
            bad = 1
            #plt.plot(xs, ys)
            #plt.show()
         else:
            my_close_stars.append((name,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,bp))
            total_match_dist = total_match_dist + match_dist
            total_cat_dist = total_cat_dist + cat_dist
            total_matches = total_matches + 1
            used[used_key] = 1
            found = 1
      if found == 0:
         if len(close_stars) >= 1:
            no_match.append(close_stars[0])

   my_close_stars,bad_stars = qc_stars(my_close_stars)
   cal_params['bad_stars'] = bad_stars
   cal_params['no_match_stars'] = no_match
   if SHOW == 1:
      for star in my_close_stars:
         dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,bp = star
         cv2.rectangle(temp_img, (new_cat_x-2, new_cat_y-2), (new_cat_x + 2, new_cat_y + 2), (128, 128, 128), 1)
         cv2.rectangle(temp_img, (six-2, siy-2), (six+ 2, siy+ 2), (255, 255, 255), 1)
         cv2.circle(temp_img,(six,siy), 7, (128,128,128), 1)
         cv2.putText(temp_img, str(dcname),  (int(new_cat_x),int(new_cat_y)), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 1)
         debug_txt = "RA/DEC: " + str(cal_params['ra_center'])  + " / " + str(cal_params['dec_center'])
         debug_txt = "POS: " + str(cal_params['position_angle'])  
         debug_txt = "PX SCALE: " + str(cal_params['pixscale'])  
         cv2.putText(temp_img, str(dcname),  (int(new_cat_x),int(new_cat_y)), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 1)


      #show_image(temp_img,'pepe', 0) 


   cal_params['cat_image_stars'] = my_close_stars
   if total_matches > 0:
      cal_params['total_res_deg'] = total_match_dist / total_matches
      cal_params['total_res_px'] = total_cat_dist / total_matches
   else:
      cal_params['total_res_deg'] = 9999
      cal_params['total_res_px'] = 9999
   cal_params['cal_params_file'] = cal_params_file

   fit_on = 0
   if fit_on == 1:
      os.system("./fitPairs.py " + cal_params_file)
   cal_params['cat_image_stars'], bad = qc_stars(cal_params['cat_image_stars'])
   print("CAT STARS !", len(cal_params['cat_image_stars']))
   print("NO MATCH!", len(no_match))
   cal_params['cat_image_stars'], res_px,res_deg = cat_star_report(cal_params['cat_image_stars'], 4)
   cal_params['total_res_px'] = res_px
   cal_params['total_res_deg'] = res_deg

   return(cal_params)

def qc_stars(close_stars):
   rez = []
   bad_stars = []
   good_stars = []
   for star in close_stars:
      dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,bp = star
      rez.append(cat_dist)
   med_res = np.median(rez)
   max_cat_dist = med_res * 2
   if max_cat_dist < 5:
      max_cat_dist = 10 
   for star in close_stars:
      dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,bp = star
      res_diff = abs(cat_dist - med_res)
      cdist = calc_dist((six,siy),(960,540))
      res_times = abs(res_diff / med_res)
      #if (res_times > 2 and cdist < 400) or bp < 0 or (res_times > 4 and cdist >= 400):
      if (res_times > 2 or cat_dist > max_cat_dist or bp < 10 or bp > 10000):
         bad_stars.append(star)
         #print("FAILED QC:", dcname, med_res, res_times, cat_dist, res_diff, bp)
      else:
         #print("PASSED QC:", dcname, cat_dist, med_res, res_diff, res_times)
         good_stars.append(star)
   return(good_stars, bad_stars)

def mag_report(stars, plot=0):
   mags = []
   flux = []
   mag_data = []
   new_stars = []
   bad_stars = []

   for star in stars:
      dcname,mag,ra,dec,img_ra,img_dec,match_dist,org_x,org_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int = star
      bad = 0
      if 100 < star_int < 20000:
         if mag > 4 and star_int > 1500:
            bad = 1
         else:
            mag_data.append((dcname, mag, star_int,cat_dist))
            mags.append(mag)
            flux.append(star_int)
            new_stars.append(star)
      else:
         bad = 1
      if bad == 1:
         bad_stars.append(star)

   if plot == 1:
      # calculate polynomial
      z = np.polyfit(mags, flux, 3)
      f = np.poly1d(z)
      x_new = np.linspace(mags[0], mags[-1], len(mags))
      y_new = f(x_new)

      mag_data = sorted(mag_data, key=lambda x: x[2], reverse=True)
      #for data in mag_data:
      plt.plot(mags, flux, 'o')
      plt.plot(x_new, y_new )
      plt.show()
   return(new_stars, bad_stars)

def get_catalog_stars(cal_params):
 
   mybsd = bsd.brightstardata()
   bright_stars = mybsd.bright_stars
   
   catalog_stars = []
   possible_stars = 0
   img_w = int(cal_params['imagew'])
   img_h = int(cal_params['imageh'])
   RA_center = float(cal_params['ra_center']) 
   dec_center = float(cal_params['dec_center']) 
   F_scale = 3600/float(cal_params['pixscale'])
   if "x_poly" in cal_params:
      x_poly = cal_params['x_poly']
      y_poly = cal_params['y_poly']
   else:
      x_poly = np.zeros(shape=(15,), dtype=np.float64)
      y_poly = np.zeros(shape=(15,), dtype=np.float64)
      x_poly_fwd = np.zeros(shape=(15,), dtype=np.float64)
      y_poly_fwd = np.zeros(shape=(15,), dtype=np.float64)
   fov_w = img_w / F_scale
   fov_h = img_h / F_scale
   fov_radius = np.sqrt((fov_w/2)**2 + (fov_h/2)**2)

   pos_angle_ref = cal_params['position_angle'] 
   x_res = int(cal_params['imagew'])
   y_res = int(cal_params['imageh'])


   if img_w < 1920:
      center_x = int(x_res / 2)
      center_y = int(x_res / 2)

   bright_stars_sorted = sorted(bright_stars, key=lambda x: x[4], reverse=False)

   for bname, cname, ra, dec, mag in bright_stars_sorted:
      dcname = cname.decode("utf-8")
      dbname = bname.decode("utf-8")
      if dcname == "":
         name = bname
      else:
         name = cname

      ang_sep = angularSeparation(ra,dec,RA_center,dec_center)
      if ang_sep < fov_radius and float(mag) < 7:
         new_cat_x, new_cat_y = distort_xy(0,0,ra,dec,RA_center, dec_center, x_poly, y_poly, x_res, y_res, pos_angle_ref,F_scale)

         possible_stars = possible_stars + 1
         catalog_stars.append((name,mag,ra,dec,new_cat_x,new_cat_y))

   return(catalog_stars)

def default_cal_params(cal_params,json_conf):
   
   if 'lat' not in cal_params:
      cal_params['site_lat'] = json_conf['site']['device_lat']
      cal_params['device_lat'] = json_conf['site']['device_lat']
   if 'lon ' not in cal_params:
      cal_params['site_lng'] = json_conf['site']['device_lng']
      cal_params['device_lng'] = json_conf['site']['device_lng']
   if 'alt ' not in cal_params:
      cal_params['site_alt'] = json_conf['site']['device_alt']
      cal_params['device_alt'] = json_conf['site']['device_alt']

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


def distort_xy(sx,sy,ra,dec,RA_center, dec_center, x_poly, y_poly, x_res, y_res, pos_angle_ref,F_scale=1):

   ra_star = ra
   dec_star = dec

   #F_scale = F_scale/10
   w_pix = 50*F_scale/3600
   #F_scale = 158 * 2
   #F_scale = 155
   #F_scale = 3600/16
   #F_scale = 3600/F_scale
   #F_scale = 1

   # Gnomonization of star coordinates to image coordinates
   ra1 = math.radians(float(RA_center))
   dec1 = math.radians(float(dec_center))
   ra2 = math.radians(float(ra_star))
   dec2 = math.radians(float(dec_star))
   ad = math.acos(math.sin(dec1)*math.sin(dec2) + math.cos(dec1)*math.cos(dec2)*math.cos(ra2 - ra1))
   radius = math.degrees(ad)
   
   try:
      sinA = math.cos(dec2)*math.sin(ra2 - ra1)/math.sin(ad)
      cosA = (math.sin(dec2) - math.sin(dec1)*math.cos(ad))/(math.cos(dec1)*math.sin(ad))
   except:
      sinA = 0
      cosA = 0
   theta = -math.degrees(math.atan2(sinA, cosA))
   theta = theta + pos_angle_ref - 90.0
   #theta = theta + pos_angle_ref - 90 + (1000*x_poly[12]) + (1000*y_poly[12])
   #theta = theta + pos_angle_ref - 90



   dist = np.degrees(math.acos(math.sin(dec1)*math.sin(dec2) + math.cos(dec1)*math.cos(dec2)*math.cos(ra1 - ra2)))

   # Calculate the image coordinates (scale the F_scale from CIF resolution)
   X1 = radius*math.cos(math.radians(theta))*F_scale
   Y1 = radius*math.sin(math.radians(theta))*F_scale
   # Calculate distortion in X direction
   dX = (x_poly[0]
      + x_poly[1]*X1
      + x_poly[2]*Y1
      + x_poly[3]*X1**2
      + x_poly[4]*X1*Y1
      + x_poly[5]*Y1**2
      + x_poly[6]*X1**3
      + x_poly[7]*X1**2*Y1
      + x_poly[8]*X1*Y1**2
      + x_poly[9]*Y1**3
      + x_poly[10]*X1*math.sqrt(X1**2 + Y1**2)
      + x_poly[11]*Y1*math.sqrt(X1**2 + Y1**2))

   # Add the distortion correction and calculate X image coordinates
   #x_array[i] = (X1 - dX)*x_res/384.0 + x_res/2.0
   new_x = X1 - dX + x_res/2.0

   # Calculate distortion in Y direction
   dY = (y_poly[0]
      + y_poly[1]*X1
      + y_poly[2]*Y1
      + y_poly[3]*X1**2
      + y_poly[4]*X1*Y1
      + y_poly[5]*Y1**2
      + y_poly[6]*X1**3
      + y_poly[7]*X1**2*Y1
      + y_poly[8]*X1*Y1**2
      + y_poly[9]*Y1**3
      + y_poly[10]*Y1*math.sqrt(X1**2 + Y1**2)
      + y_poly[11]*X1*math.sqrt(X1**2 + Y1**2))

   # Add the distortion correction and calculate Y image coordinates
   #y_array[i] = (Y1 - dY)*y_res/288.0 + y_res/2.0
   new_y = Y1 - dY + y_res/2.0
   return(new_x,new_y)


def find_close_stars(star_point, catalog_stars,dt=100):

   scx,scy = star_point
   scx,scy = int(scx), int(scy)

   center_dist = calc_dist((scx,scy),(960,540))
   if center_dist > 500:
      dt = 120
   if center_dist > 700:
      dt = 140
   if center_dist > 800:
      dt = 160
   if center_dist > 900:
      dt = 180


   matches = []
   nomatches = []
   for name,mag,ra,dec,cat_x,cat_y in catalog_stars:
      dcname = str(name.decode("utf-8"))
      dbname = dcname.encode("utf-8")
      cat_x, cat_y = int(cat_x), int(cat_y)
      if cat_x - dt < scx < cat_x + dt and cat_y -dt < scy < cat_y + dt:
         cat_star_dist= calc_dist((cat_x,cat_y),(scx,scy))
         #print(dcname, cat_x, cat_y, scx, scy, cat_star_dist)
         matches.append((dcname,mag,ra,dec,cat_x,cat_y,scx,scy,cat_star_dist))
      else:
         cat_star_dist= calc_dist((cat_x,cat_y),(scx,scy))
         nomatches.append((dcname,mag,ra,dec,cat_x,cat_y,scx,scy,cat_star_dist))
      


   if len(matches) > 1:
      matches_sorted = sorted(matches, key=lambda x: x[8], reverse=False)
      # check angle back to center from cat star and then angle from cat star to img star and pick the one with the closest match for the star...
      #for match in matches_sorted:
     
      matches = matches_sorted
   else:
      matches_sorted = sorted(nomatches, key=lambda x: x[8], reverse=False)
   #print("MATCHES:", matches)
   #print("NO MATCHES:", matches_sorted)
   return(matches[0:1])


def AzEltoRADec(az,el,cal_file,cal_params,json_conf):
   azr = np.radians(az)
   elr = np.radians(el)
   hd_datetime, hd_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(cal_file)
   #hd_datetime = hd_y + "/" + hd_m + "/" + hd_d + " " + hd_h + ":" + hd_M + ":" + hd_s
   if "device_lat" in cal_params:
      device_lat = cal_params['device_lat']
      device_lng = cal_params['device_lng']
      device_alt = cal_params['device_alt']
   else:
      device_lat = json_conf['site']['device_lat']
      device_lng = json_conf['site']['device_lng']
      device_alt = json_conf['site']['device_alt']

   obs = ephem.Observer()


   obs.lat = str(device_lat)
   obs.lon = str(device_lng)
   obs.elevation = float(device_alt)
   obs.date = hd_datetime 
   #print("AZ/RA DEBUG: ", device_lat, device_lng, device_alt, hd_datetime, az, el)
   #print("AZ2RA DATETIME:", hd_datetime)
   #print("AZ2RA LAT:", obs.lat)
   #print("AZ2RA LON:", obs.lon)
   #print("AZ2RA ELV:", obs.elevation)
   #print("AZ2RA DATE:", obs.date)
   #print("AZ2RA AZ,EL:", az,el)
   #print("AZ2RA RAD AZ,EL:", azr,elr)

   ra,dec = obs.radec_of(azr,elr)
   
   #print("AZ2RA RA,DEC:", ra,dec)

   return(ra,dec)


def XYtoRADec(img_x,img_y,cal_file,cal_params,json_conf):
   #print("CAL FILE IS : ", cal_file)
   hd_datetime, hd_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(cal_file)
   F_scale = 3600/float(cal_params['pixscale'])
   #F_scale = 24

   total_min = (int(hd_h) * 60) + int(hd_M)
   day_frac = total_min / 1440 
   hd_d = int(hd_d) + day_frac
   #jd = date_to_jd(int(hd_y),int(hd_m),float(hd_d))

   (f_datetime, cam, f_date_str,y,m,d, h, mm, s) = convert_filename_to_date_cam(cal_file)
   jd = datetime2JD(f_datetime, 0.0)
   #hour_angle = JD2HourAngle(jd)

   lat = float(json_conf['site']['device_lat'])
   lon = float(json_conf['site']['device_lng'])

   # Calculate the reference hour angle
   T = (jd - 2451545.0)/36525.0
   Ho = (280.46061837 + 360.98564736629*(jd - 2451545.0) + 0.000387933*T**2 \
      - (T**3)/38710000.0)%360
   if "x_poly_fwd" in cal_params:
      x_poly_fwd = cal_params['x_poly_fwd']
      y_poly_fwd = cal_params['y_poly_fwd']
   else:
      x_poly_fwd = np.zeros(shape=(15,),dtype=np.float64)
      y_poly_fwd = np.zeros(shape=(15,),dtype=np.float64)
   
   dec_d = float(cal_params['dec_center']) 
   RA_d = float(cal_params['ra_center']) 

   dec_d = dec_d + (x_poly_fwd[13] * 100)
   dec_d = dec_d + (y_poly_fwd[13] * 100)

   RA_d = RA_d + (x_poly_fwd[14] * 100)
   RA_d = RA_d + (y_poly_fwd[14] * 100)

   pos_angle_ref = float(cal_params['position_angle']) + (1000*x_poly_fwd[12]) + (1000*y_poly_fwd[12])

   # Convert declination to radians
   dec_rad = math.radians(dec_d)

   # Precalculate some parameters
   sl = math.sin(math.radians(lat))
   cl = math.cos(math.radians(lat))


   x_det = img_x - int(cal_params['imagew'])/2
   y_det = img_y - int(cal_params['imageh'])/2

   dx = (x_poly_fwd[0]
      + x_poly_fwd[1]*x_det
      + x_poly_fwd[2]*y_det
      + x_poly_fwd[3]*x_det**2
      + x_poly_fwd[4]*x_det*y_det
      + x_poly_fwd[5]*y_det**2
      + x_poly_fwd[6]*x_det**3
      + x_poly_fwd[7]*x_det**2*y_det
      + x_poly_fwd[8]*x_det*y_det**2
      + x_poly_fwd[9]*y_det**3
      + x_poly_fwd[10]*x_det*math.sqrt(x_det**2 + y_det**2)
      + x_poly_fwd[11]*y_det*math.sqrt(x_det**2 + y_det**2))

   # Add the distortion correction
   x_pix = x_det + dx 

   #print("ORIG X:", img_x)
   #print("X DET:", x_det)
   #print("DX :", dx)
   #print("NEWX :", x_pix)

   dy = (y_poly_fwd[0]
      + y_poly_fwd[1]*x_det
      + y_poly_fwd[2]*y_det
      + y_poly_fwd[3]*x_det**2
      + y_poly_fwd[4]*x_det*y_det
      + y_poly_fwd[5]*y_det**2
      + y_poly_fwd[6]*x_det**3
      + y_poly_fwd[7]*x_det**2*y_det
      + y_poly_fwd[8]*x_det*y_det**2
      + y_poly_fwd[9]*y_det**3
      + y_poly_fwd[10]*y_det*math.sqrt(x_det**2 + y_det**2)
      + y_poly_fwd[11]*x_det*math.sqrt(x_det**2 + y_det**2))

   # Add the distortion correction
   y_pix = y_det + dy 

   x_pix = x_pix / F_scale
   y_pix = y_pix / F_scale

   ### Convert gnomonic X, Y to alt, az ###

   # Caulucate the needed parameters
   radius = math.radians(math.sqrt(x_pix**2 + y_pix**2))
   theta = math.radians((90 - pos_angle_ref + math.degrees(math.atan2(y_pix, x_pix)))%360)

   sin_t = math.sin(dec_rad)*math.cos(radius) + math.cos(dec_rad)*math.sin(radius)*math.cos(theta)
   Dec0det = math.atan2(sin_t, math.sqrt(1 - sin_t**2))

   sin_t = math.sin(theta)*math.sin(radius)/math.cos(Dec0det)
   cos_t = (math.cos(radius) - math.sin(Dec0det)*math.sin(dec_rad))/(math.cos(Dec0det)*math.cos(dec_rad))
   RA0det = (RA_d - math.degrees(math.atan2(sin_t, cos_t)))%360

   h = math.radians(Ho + lon - RA0det)
   sh = math.sin(h)
   sd = math.sin(Dec0det)
   ch = math.cos(h)
   cd = math.cos(Dec0det)

   x = -ch*cd*sl + sd*cl
   y = -sh*cd
   z = ch*cd*cl + sd*sl

   r = math.sqrt(x**2 + y**2)

   # Calculate azimuth and altitude
   azimuth = math.degrees(math.atan2(y, x))%360
   altitude = math.degrees(math.atan2(z, r))



   ### Convert alt, az to RA, Dec ###

   # Never allow the altitude to be exactly 90 deg due to numerical issues
   if altitude == 90:
      altitude = 89.9999

   # Convert altitude and azimuth to radians
   az_rad = math.radians(azimuth)
   alt_rad = math.radians(altitude)

   saz = math.sin(az_rad)
   salt = math.sin(alt_rad)
   caz = math.cos(az_rad)
   calt = math.cos(alt_rad)

   x = -saz*calt
   y = -caz*sl*calt + salt*cl
   HA = math.degrees(math.atan2(x, y))

   # Calculate the hour angle
   T = (jd - 2451545.0)/36525.0
   hour_angle = (280.46061837 + 360.98564736629*(jd - 2451545.0) + 0.000387933*T**2 - T**3/38710000.0)%360

   RA = (hour_angle + lon - HA)%360
   dec = math.degrees(math.asin(sl*salt + cl*calt*caz))

   ### ###




   return(x_pix+img_x,y_pix+img_y,RA,dec,azimuth,altitude)
def AzEltoRADec(az,el,cal_file,cal_params,json_conf):
   azr = np.radians(az)
   elr = np.radians(el)
   hd_datetime, hd_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(cal_file)
   #hd_datetime = hd_y + "/" + hd_m + "/" + hd_d + " " + hd_h + ":" + hd_M + ":" + hd_s
   if "device_lat" in cal_params:
      device_lat = cal_params['device_lat']
      device_lng = cal_params['device_lng']
      device_alt = cal_params['device_alt']
   else:
      device_lat = json_conf['site']['device_lat']
      device_lng = json_conf['site']['device_lng']
      device_alt = json_conf['site']['device_alt']

   obs = ephem.Observer()


   obs.lat = str(device_lat)
   obs.lon = str(device_lng)
   obs.elevation = float(device_alt)
   obs.date = hd_datetime 
   #print("AZ/RA DEBUG: ", device_lat, device_lng, device_alt, hd_datetime, az, el)
   #print("AZ2RA DATETIME:", hd_datetime)
   #print("AZ2RA LAT:", obs.lat)
   #print("AZ2RA LON:", obs.lon)
   #print("AZ2RA ELV:", obs.elevation)
   #print("AZ2RA DATE:", obs.date)
   #print("AZ2RA AZ,EL:", az,el)
   #print("AZ2RA RAD AZ,EL:", azr,elr)

   ra,dec = obs.radec_of(azr,elr)
   
   #print("AZ2RA RA,DEC:", ra,dec)

   return(ra,dec)


def XYtoRADecOLD(img_x,img_y,cal_file,cal_params,json_conf):
   #print("CAL FILE IS : ", cal_file)
   hd_datetime, hd_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(cal_file)
   F_scale = 3600/float(cal_params['pixscale'])
   #F_scale = 24

   total_min = (int(hd_h) * 60) + int(hd_M)
   day_frac = total_min / 1440 
   hd_d = int(hd_d) + day_frac
   jd = date_to_jd(int(hd_y),int(hd_m),float(hd_d))

   lat = float(json_conf['site']['device_lat'])
   lon = float(json_conf['site']['device_lng'])

   # Calculate the reference hour angle
   T = (jd - 2451545.0)/36525.0
   Ho = (280.46061837 + 360.98564736629*(jd - 2451545.0) + 0.000387933*T**2 \
      - (T**3)/38710000.0)%360

   if "x_poly_fwd" in cal_params:
      x_poly_fwd = cal_params['x_poly_fwd']
      y_poly_fwd = cal_params['y_poly_fwd']
   
   dec_d = float(cal_params['dec_center']) 
   RA_d = float(cal_params['ra_center']) 

   dec_d = dec_d + (x_poly_fwd[13] * 100)
   dec_d = dec_d + (y_poly_fwd[13] * 100)

   RA_d = RA_d + (x_poly_fwd[14] * 100)
   RA_d = RA_d + (y_poly_fwd[14] * 100)

   pos_angle_ref = float(cal_params['position_angle']) + (1000*x_poly_fwd[12]) + (1000*y_poly_fwd[12])

   # Convert declination to radians
   dec_rad = math.radians(dec_d)

   # Precalculate some parameters
   sl = math.sin(math.radians(lat))
   cl = math.cos(math.radians(lat))


   x_det = img_x - int(cal_params['imagew'])/2
   y_det = img_y - int(cal_params['imageh'])/2

   dx = (x_poly_fwd[0]
      + x_poly_fwd[1]*x_det
      + x_poly_fwd[2]*y_det
      + x_poly_fwd[3]*x_det**2
      + x_poly_fwd[4]*x_det*y_det
      + x_poly_fwd[5]*y_det**2
      + x_poly_fwd[6]*x_det**3
      + x_poly_fwd[7]*x_det**2*y_det
      + x_poly_fwd[8]*x_det*y_det**2
      + x_poly_fwd[9]*y_det**3
      + x_poly_fwd[10]*x_det*math.sqrt(x_det**2 + y_det**2)
      + x_poly_fwd[11]*y_det*math.sqrt(x_det**2 + y_det**2))

   # Add the distortion correction
   x_pix = x_det + dx 

   #print("ORIG X:", img_x)
   #print("X DET:", x_det)
   #print("DX :", dx)
   #print("NEWX :", x_pix)

   dy = (y_poly_fwd[0]
      + y_poly_fwd[1]*x_det
      + y_poly_fwd[2]*y_det
      + y_poly_fwd[3]*x_det**2
      + y_poly_fwd[4]*x_det*y_det
      + y_poly_fwd[5]*y_det**2
      + y_poly_fwd[6]*x_det**3
      + y_poly_fwd[7]*x_det**2*y_det
      + y_poly_fwd[8]*x_det*y_det**2
      + y_poly_fwd[9]*y_det**3
      + y_poly_fwd[10]*y_det*math.sqrt(x_det**2 + y_det**2)
      + y_poly_fwd[11]*x_det*math.sqrt(x_det**2 + y_det**2))

   # Add the distortion correction
   y_pix = y_det + dy 

   x_pix = x_pix / F_scale
   y_pix = y_pix / F_scale

   ### Convert gnomonic X, Y to alt, az ###

   # Caulucate the needed parameters
   radius = math.radians(math.sqrt(x_pix**2 + y_pix**2))
   theta = math.radians((90 - pos_angle_ref + math.degrees(math.atan2(y_pix, x_pix)))%360)

   sin_t = math.sin(dec_rad)*math.cos(radius) + math.cos(dec_rad)*math.sin(radius)*math.cos(theta)
   Dec0det = math.atan2(sin_t, math.sqrt(1 - sin_t**2))

   sin_t = math.sin(theta)*math.sin(radius)/math.cos(Dec0det)
   cos_t = (math.cos(radius) - math.sin(Dec0det)*math.sin(dec_rad))/(math.cos(Dec0det)*math.cos(dec_rad))
   RA0det = (RA_d - math.degrees(math.atan2(sin_t, cos_t)))%360

   h = math.radians(Ho + lon - RA0det)
   sh = math.sin(h)
   sd = math.sin(Dec0det)
   ch = math.cos(h)
   cd = math.cos(Dec0det)

   x = -ch*cd*sl + sd*cl
   y = -sh*cd
   z = ch*cd*cl + sd*sl

   r = math.sqrt(x**2 + y**2)

   # Calculate azimuth and altitude
   azimuth = math.degrees(math.atan2(y, x))%360
   altitude = math.degrees(math.atan2(z, r))



   ### Convert alt, az to RA, Dec ###

   # Never allow the altitude to be exactly 90 deg due to numerical issues
   if altitude == 90:
      altitude = 89.9999

   # Convert altitude and azimuth to radians
   az_rad = math.radians(azimuth)
   alt_rad = math.radians(altitude)

   saz = math.sin(az_rad)
   salt = math.sin(alt_rad)
   caz = math.cos(az_rad)
   calt = math.cos(alt_rad)

   x = -saz*calt
   y = -caz*sl*calt + salt*cl
   HA = math.degrees(math.atan2(x, y))

   # Calculate the hour angle
   T = (jd - 2451545.0)/36525.0
   hour_angle = (280.46061837 + 360.98564736629*(jd - 2451545.0) + 0.000387933*T**2 - T**3/38710000.0)%360

   RA = (hour_angle + lon - HA)%360
   dec = math.degrees(math.asin(sl*salt + cl*calt*caz))

   ### ###




   return(x_pix+img_x,y_pix+img_y,RA,dec,azimuth,altitude)


def get_device_lat_lon(json_conf):
   if "device_lat" in json_conf['site']:
      lat = json_conf['site']['device_lat']
      lng = json_conf['site']['device_lng']
      alt = json_conf['site']['device_alt']
   else:
      lat = json_conf['site']['site_lat']
      lng = json_conf['site']['site_lng']
      alt = json_conf['site']['site_alt'] 
   return(lat,lng,alt)



def reduce_fov_pos(this_poly, az,el,pos,pixscale, x_poly, y_poly, cal_params_file, oimage, json_conf, paired_stars, user_stars, min_run = 1, show=0, field = None):
   global tries
   #print("REDUCE FOV POS", tries)
   tries = tries + 1
   image = oimage.copy()
   image = cv2.resize(image, (1920,1080))
   #print("RUN:", az, el, pos, pixscale) 
   #new_az = az + (this_poly[0] * np.float64(az) ** 2)
   #new_el = el + (this_poly[1] * np.float64(el) ** 2) 
   #new_position_angle = pos + (this_poly[2] * np.float64(pos) ** 2)
   #new_position_angle = pos + (this_poly[2] * np.float64(pos) )
   #new_pixscale = pixscale + (this_poly[3] * np.float64(pixscale) ** 2)


   start_stars = len(paired_stars)

   if field is None:
      new_az = az + (this_poly[0]*az)
      new_el = el + (this_poly[1]*el)
      new_position_angle = pos + (this_poly[2]*pos)
      new_pixscale = pixscale + (this_poly[3]*pixscale)


   lat,lng,alt = get_device_lat_lon(json_conf)
   cal_temp = {
      'center_az' : new_az,
      'center_el' : new_el,
      'position_angle' : new_position_angle,
      'pxscale' : new_pixscale,
      'site_lat' : lat,
      'site_lng' : lng,
      'site_alt' : alt,
      'user_stars' : user_stars,
   } 

   rah,dech = AzEltoRADec(new_az,new_el,cal_params_file,cal_temp,json_conf)
   rah = str(rah).replace(":", " ")
   dech = str(dech).replace(":", " ")
   ra_center,dec_center = HMS2deg(str(rah),str(dech))

   temp_cal_params = {}
   temp_cal_params['position_angle'] = new_position_angle
   temp_cal_params['ra_center'] = ra_center
   temp_cal_params['dec_center'] = dec_center
   temp_cal_params['center_az'] = new_az
   temp_cal_params['center_el'] = new_el
   temp_cal_params['pixscale'] = new_pixscale 
   temp_cal_params['device_lat'] = json_conf['site']['device_lat']
   temp_cal_params['device_lng'] = json_conf['site']['device_lng']
   temp_cal_params['device_alt'] = json_conf['site']['device_alt']
   temp_cal_params['imagew'] = 1920
   temp_cal_params['imageh'] = 1080
   temp_cal_params['x_poly'] = x_poly
   temp_cal_params['y_poly'] = y_poly
   temp_cal_params['user_stars'] = user_stars


   fov_poly = 0
   pos_poly = 0
   cat_stars = get_catalog_stars(temp_cal_params)
   temp_cal_params, bad_stars, marked_img = eval_cal(cal_params_file, json_conf, temp_cal_params, oimage) 
   tstars = len(temp_cal_params['cat_image_stars'])
   print("CAL VALS:", cal_params_file, temp_cal_params['total_res_px'], start_stars, tstars) 
   sd = start_stars - tstars
   if sd <= 0:
      sd = 0
   match_val = 1 - temp_cal_params['match_perc'] 
   return(temp_cal_params['total_res_px'] +sd)
   #pair_stars(temp_cal_params, cal_params_file, json_conf, None)


   if len(cat_stars) == 0:
      return(999999)
   new_res = []
   new_paired_stars = []
   used = {}
   orig_star_count = len(paired_stars)
   for cat_star in cat_stars:
      (name,mag,ra,dec,new_cat_x,new_cat_y) = cat_star
      dname = name.decode("utf-8")
      for data in paired_stars:
         if len(data) == 16:
            iname,mag,o_ra,o_dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,old_cat_x,old_cat_y,six,siy,cat_dist  = data
         if len(data) == 17:
#dname == iname:
            iname,mag,o_ra,o_dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,old_cat_x,old_cat_y,six,siy,cat_dist,star_int  = data
         new_cat_x, new_cat_y = int(new_cat_x), int(new_cat_y)
         if (ra == o_ra and dec == o_dec) :
            #pdist = calc_dist((six,siy),(new_cat_x,new_cat_y))
            pdist = calc_dist((six,siy),(new_cat_x,new_cat_y))
            #if pdist <= 50:
            if True:
               new_res.append(pdist)
               used_key = str(six) + "." + str(siy)
               if used_key not in used: 
                  new_paired_stars.append((iname,mag,ra,dec,new_cat_x,new_cat_y,six,siy,pdist))
                   
                  used[used_key] = 1
                  new_cat_x,new_cat_y = int(new_cat_x), int(new_cat_y)
                  #cv2.rectangle(image, (new_cat_x-5, new_cat_y-5), (new_cat_x + 5, new_cat_y + 5), (255), 1)
                  #cv2.line(image, (six,siy), (new_cat_x,new_cat_y), (255), 1)
                  #cv2.circle(image,(six,siy), 10, (255), 1)



   paired_stars = new_paired_stars
   tres  =0 
   for iname,mag,ra,dec,new_cat_x,new_cat_y,six,siy,pdist in new_paired_stars:
      cdist = calc_dist((six,siy), (1920/2,1080/2))
      tres = tres + pdist
     

   if len(paired_stars) > 0:
      avg_res = tres / len(paired_stars) 
   else:
      avg_res = 9999999
      res = 9999999
   print("STAR RES:", tries, avg_res, start_stars, tstars)

   if orig_star_count > len(paired_stars):
      pen = orig_star_count - len(paired_stars)
   else:
      pen = 0

   temp_cal_params['total_res_px'] = avg_res
 
   avg_res = avg_res + (pen * 10)
   show_res = avg_res - (pen*10) 




   if SHOW == 1:
      if tries % 50 == 0:
         new_star_image = draw_star_image(image, new_paired_stars, temp_cal_params ) 

         cv2.imshow('pepe', new_star_image)
         cv2.waitKey(30)


   if CAL_MOVIE == 1:
      if tries % 100 == 0:   
         new_star_image = draw_star_image(image, new_paired_stars, temp_cal_params ) 
         fn, dir = fn_dir(cal_params_file)
         fn = fn.replace("-calparams.json", ".png")
         count = '{:06d}'.format(tries)
         fn = fn.replace(".png", "-" + str(count) + ".jpg")
         cv2.imwrite("tmp_vids/" + fn, new_star_image)
         print("SAVE VIDEO:", tries, tries % 100, fn)

   tries = tries + 1
   if tries % 25 == 0:
      print("RES:", tries, avg_res)
   if min_run == 1:
      return(avg_res)
   else:
      return(show_res)


def minimize_poly_params_fwd(cal_params_file, cal_params,json_conf,show=0):
   global tries
   tries = 0
   print("Minimize poly params!")
   #cv2.namedWindow('pepe')
   
   fit_img_file = cal_params_file.replace("-calparams.json", ".png")
   if cfe(fit_img_file) == 1:
      fit_img = cv2.imread(fit_img_file)
   else:
      fit_img = np.zeros((1080,1920),dtype=np.uint8)

   x_poly_fwd = cal_params['x_poly_fwd'] 
   y_poly_fwd = cal_params['y_poly_fwd'] 
   x_poly = cal_params['x_poly'] 
   y_poly = cal_params['y_poly'] 

   close_stars = cal_params['cat_image_stars']
   # do x poly fwd

   #x_poly_fwd = np.zeros(shape=(15,),dtype=np.float64)
   #y_poly_fwd = np.zeros(shape=(15,),dtype=np.float64)
   #x_poly = np.zeros(shape=(15,),dtype=np.float64)
   #y_poly = np.zeros(shape=(15,),dtype=np.float64)



   # do x poly 
   field = 'x_poly'
   res = scipy.optimize.minimize(reduce_fit, x_poly, args=(field,cal_params,cal_params_file,fit_img,json_conf), method='Nelder-Mead')
   x_poly = res['x']
   x_fun = res['fun']
   cal_params['x_poly'] = x_poly.tolist()
   cal_params['x_fun'] = x_fun

   print("RES:", res)


   (f_datetime, cam, f_date_str,y,m,d, h, mm, s) = convert_filename_to_date_cam(cal_params_file)
   cal_params['cal_date'] = f_date_str

   cal_params['cat_image_stars'], res_px,res_deg = cat_star_report(cal_params['cat_image_stars'], 4)
   cal_params['total_res_px'] = res_px
   cal_params['total_res_deg'] = res_deg
   cal_params['cal_params_file'] = cal_params_file


   if res_px > 20:
      print("Something is bad here. Abort!")
      return(0, cal_params)
   #exit()
   # do y poly 
   field = 'y_poly'
   res = scipy.optimize.minimize(reduce_fit, y_poly, args=(field,cal_params,cal_params_file,fit_img,json_conf), method='Nelder-Mead')
   y_poly = res['x']
   y_fun = res['fun']
   cal_params['y_poly'] = y_poly.tolist()
   cal_params['y_fun'] = y_fun

   cal_params['cat_image_stars'], res_px,res_deg = cat_star_report(cal_params['cat_image_stars'], 2.5)

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


   cal_params['cat_image_stars'], res_px,res_deg = cat_star_report(cal_params['cat_image_stars'], 2.5)


   print("POLY PARAMS")
   print("X_POLY", x_poly)
   print("Y_POLY", y_poly)
   print("X_POLY_FWD", x_poly_fwd)
   print("Y_POLY_FWD", y_poly_fwd)
   print("X_POLY FUN", x_fun)
   print("Y_POLY FUN", y_fun)
   print("X_POLY FWD FUN", x_fun_fwd)
   print("Y_POLY FWD FUN", y_fun_fwd)


   # FINAL RES & STARS UPDATE
   cal_params['cat_image_stars'], res_px,res_deg = cat_star_report(cal_params['cat_image_stars'], 4)
   cal_params['total_res_px'] = res_px
   cal_params['total_res_deg'] = res_deg


   #img_x = 960
   #img_y = 540
   #new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(img_x,img_y,cal_params_file,cal_params,json_conf)
   #cal_params['center_az'] = img_az
   #cal_params['center_el'] = img_el
   save_json_file(cal_params_file, cal_params)
   return(1, cal_params)

def reduce_fit(this_poly,field, cal_params, cal_params_file, fit_img, json_conf, show=0):
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
      if len(star) == 16:
         (dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,px_dist ) = star
      if len(star) == 17:
         (dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy, px_dist, img_res ) = star
      if len(star) == 24:
         (cal_file , center_az, center_el, ra_center, dec_center, position_angle, pixscale, dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int) = star
      if field == 'x_poly' or field == 'y_poly':
         new_cat_x, new_cat_y = distort_xy(0,0,ra,dec,float(cal_params['ra_center']), float(cal_params['dec_center']), x_poly, y_poly, float(cal_params['imagew']), float(cal_params['imageh']), float(cal_params['position_angle']),3600/float(cal_params['pixscale']))
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
         new_cat_x, new_cat_y = distort_xy(0,0,img_ra,img_dec,float(cal_params['ra_center']), float(cal_params['dec_center']), x_poly, y_poly, float(cal_params['imagew']), float(cal_params['imageh']), float(cal_params['position_angle']),3600/float(cal_params['pixscale']))
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
   if SHOW == 1:
      cv2.imshow('reduce_fit', show_img)
      cv2.waitKey(1)


   #print("Total Residual Error:", total_res )
   if tries % 100 == 0:
      print("Avg Residual Error:", tries, field, avg_res )
 
   return(avg_res)

def draw_star_image(img, cat_image_stars,cp=None) :

   image = Image.fromarray(img)
   draw = ImageDraw.Draw(image)
   font = ImageFont.truetype("/usr/share/fonts/truetype/freefont/FreeSans.ttf", 16, encoding="unic" )
   org_x = None
   org_y = None
   for star in cat_image_stars:
      if len(star) == 9:
         dcname,mag,ra,dec,new_cat_x,new_cat_y,six,siy,cat_dist = star
      else:
         dcname,mag,ra,dec,img_ra,img_dec,match_dist,org_x,org_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int = star
      if cat_dist <= 1:
         color = "#FF0000"
      if 1 < cat_dist <= 2:
         color = "#00FF00"
      if 2 < cat_dist <= 3:
         color = "#999900"
      if 3 < cat_dist <= 4:
         color = "#FFA500"
      if cat_dist > 4:
         color = "#0000FF"
      res_line = [(six,siy),(new_cat_x,new_cat_y)]
      draw.rectangle((new_cat_x-7, new_cat_y-7, new_cat_x + 7, new_cat_y + 7), outline=color)
      draw.ellipse((six-5, siy-5, six+7, siy+7),  outline ="white")
      draw.line(res_line, fill=color, width = 0) 
      draw.text((new_cat_x, new_cat_y), str(dcname), font = font, fill="white")
      if org_x is not None:
         org_res_line = [(six,siy),(org_x,org_y)]
         draw.rectangle((org_x-5, org_y-5, org_x + 5, org_y + 5), outline="gray")
         draw.line(org_res_line, fill="gray", width = 0) 
      if cp is not None:
         ltext0 = "Residual Error in Px:" 
         text0 =  str(cp['total_res_px'])[0:7] 
         ltext1 = "Center RA/DEC:" 
         text1 =  str(cp['ra_center'])[0:6] + "/" + str(cp['dec_center'])[0:6]
         ltext2 = "Center AZ/EL:" 
         text2 =  str(cp['center_az'])[0:6] + "/" + str(cp['center_el'])[0:6]
         ltext3 = "Position Angle:" 
         text3 =  str(cp['position_angle'])[0:6]
         ltext4 = "Pixel Scale:" 
         text4 =  str(cp['pixscale'])[0:6]
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


   return(np.asarray(image))




   # OLD
   if cal_params == None:
      cpfile = image_file.replace(".png", "-calparams.json")
      cal_params = load_json_file(cpfile)
   print("image:", image_file)
   if write == 1:
      star_file = image_file.replace(".png", "-stars.png")
   if image_file is not None: 
      img = Image.open(image_file)
   else:
      img = Image.fromarray(image)
   draw = ImageDraw.Draw(img)
   font = ImageFont.truetype(VIDEO_FONT, VIDEO_FONT_SMALL_SIZE) 

   c_dist = []
   m_dist = []
   if len(cal_params['cat_image_stars']) == 0:
      print("CAT IMAGE STARS 0!")
      exit()
   for star in cal_params['cat_image_stars']:
      dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int = star
      c_dist.append(cat_dist)
      m_dist.append(match_dist)
   med_c_dist = np.median(c_dist)
   med_m_dist = np.median(m_dist)

   for star in cal_params['cat_image_stars']:
      dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int = star
      print(dcname, match_dist - med_m_dist, cat_dist - med_c_dist)
      if cat_dist - med_c_dist < 20:
         draw.ellipse((six-5, siy-5, six+5, siy+5), outline ='blue')
         draw.rectangle([(new_cat_x-5,new_cat_y-5),(new_cat_x+5),(new_cat_y+5)], outline ="red") 
         draw.rectangle([(new_x-5,new_y-5),(new_x+5),(new_y+5)], outline ="green") 

         draw.text((six, siy), dcname, font=font)
   if write == 1:
      img.save(star_file)
      return(img)
   else:
      return(img)

def freecal_copy(cal_params_file, json_conf):
   cal_params = load_json_file(cal_params_file)
   user_stars = []
   for x,y,cp in cal_params['user_stars']:
      user_stars.append((x,y))
   
   cpf = cal_params_file.split("/")[-1]
   cprf = cpf.replace("-calparams.json", "")
   cpd = cal_params_file.replace(cpf, "")
   fc_dir = "/mnt/ams2/cal/freecal/" + cprf + "/" 
   if cfe(fc_dir, 1) == 0:
      os.makedirs(fc_dir)
   cmd = "cp " + cpd + cpf + " " + fc_dir + cprf + "-stacked-calparams.json"
   os.system(cmd)
   print(cmd)
   js = {}
   js['user_stars'] = user_stars

   new_cal_file = fc_dir + cprf + "-stacked-calparams.json"
   save_json_file(fc_dir + cprf + "-user-stars.json", js)
   print("SAVED:", fc_dir + cprf + "-user-stars.json")

   if cfe(cpd + cprf + "-azgrid.png") == 1:
      cmd = "cp " + cpd + cprf + "-azgrid.png" + " " + fc_dir + cprf + "-azgrid.png"
      os.system(cmd)
      print(cmd)

   cmd = "cp " + cpd + cprf + ".png" + " " + fc_dir + cprf + "-stacked.png"
   os.system(cmd)
   print(cmd)

   img = cv2.imread(fc_dir + cprf + ".png")
   
  # azimg = cv2.imread(fc_dir + cprf + "-azgrid.png")
  # azhalf = cv2.resize(azimg, (960, 540))
  # imghalf = cv2.resize(azimg, (960, 540))

  # imgaz_blend = cv2.addWeighted(imghalf, 0.5, azhalf, 0.5, 0.0)

  # cv2.imwrite(fc_dir + cprf + "-stacked-azgrid-half.png", azhalf)
  # cv2.imwrite(fc_dir + cprf + "-stacked-azgrid-half-blend.png", imgaz_blend)
  # cv2.imwrite(cpd + cprf + "-blend.png", imgaz_blend)
   return(new_cal_file)


def remove_dupe_cat_stars(paired_stars):
   iused = {}
   cused = {}
   new_paired_stars = []
   for data in paired_stars:
      if len(data) == 16:
         iname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,old_cat_x,old_cat_y,six,siy,cat_dist  = data
      if len(data) == 17:
         iname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,old_cat_x,old_cat_y,six,siy,cat_dist,bp  = data
      if len(data) == 10:
         name,mag,ra,dec,new_cat_x,new_cat_y,six,siy,px_dist,cp_file = data
      used_key = str(six) + "." + str(siy)
      c_used_key = str(ra) + "." + str(dec)
      if used_key not in iused and c_used_key not in cused:
         new_paired_stars.append(data)
         iused[used_key] = 1
         cused[c_used_key] = 1
   return(new_paired_stars)

def AzEltoRADec(az,el,cal_file,cal_params,json_conf):
   azr = np.radians(az)
   elr = np.radians(el)
   hd_datetime, hd_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(cal_file)
   #hd_datetime = hd_y + "/" + hd_m + "/" + hd_d + " " + hd_h + ":" + hd_M + ":" + hd_s
   if "device_lat" in cal_params:
      device_lat = cal_params['device_lat']
      device_lng = cal_params['device_lng']
      device_alt = cal_params['device_alt']
   else:
      device_lat = json_conf['site']['device_lat']
      device_lng = json_conf['site']['device_lng']
      device_alt = json_conf['site']['device_alt']

   obs = ephem.Observer()


   obs.lat = str(device_lat)
   obs.lon = str(device_lng)
   obs.elevation = float(device_alt)
   obs.date = hd_datetime 
   #print("AZ/RA DEBUG: ", device_lat, device_lng, device_alt, hd_datetime, az, el)
   #print("AZ2RA DATETIME:", hd_datetime)
   #print("AZ2RA LAT:", obs.lat)
   #print("AZ2RA LON:", obs.lon)
   #print("AZ2RA ELV:", obs.elevation)
   #print("AZ2RA DATE:", obs.date)
   #print("AZ2RA AZ,EL:", az,el)
   #print("AZ2RA RAD AZ,EL:", azr,elr)

   ra,dec = obs.radec_of(azr,elr)
   
   #print("AZ2RA RA,DEC:", ra,dec)

   return(ra,dec)

def fn_dir(file):
   fn = file.split("/")[-1]
   dir = file.replace(fn, "")
   return(fn, dir)

""" 

   Function for performing a lens fit across multi-image, multi-day star sets

"""




def minimize_poly_multi_star(merged_stars, json_conf,orig_ra_center=0,orig_dec_center=0,cam_id=None,master_file=None,mcp=None,show=0):
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
      #(cal_file,ra_center,dec_center,position_angle,pixscale,dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy, img_res,np_new_cat_x,np_new_cat_y) = star
      (cal_file , center_az, center_el, ra_center, dec_center, position_angle, pixscale, dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int) = star
      img_res = cat_dist

      err_list.append(img_res)
      cv2.circle(img,(six,siy), 10, (255), 1)
   std_dist = np.mean(err_list)
   cal_params = {}
   print("MS LEN:", len(merged_stars))
   print(merged_stars)
   if len(merged_stars) < 20:
      return(0,0,0)

   fit_img = np.zeros((1080,1920),dtype=np.uint8)
   fit_img = cv2.cvtColor(fit_img,cv2.COLOR_GRAY2RGB)


   # do x poly fwd
   if SHOW == 1:
      cv2.namedWindow(cam_id) 
   this_fit_img = fit_img.copy()
   for star in merged_stars:
      #(cal_file,ra_center,dec_center,position_angle,pixscale,dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy, img_res,np_new_cat_x,np_new_cat_y) = star
      (cal_file , center_az, center_el, ra_center, dec_center, position_angle, pixscale, dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int) = star
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
   if SHOW == 1:
      cv2.imshow(cam_id, simg)
      cv2.waitKey(30)


   # do x poly 
   field = 'x_poly'
   #cal_params['pixscale'] = 158.739329193

   if mcp is not None and mcp != 0:
      first_run = 0

      x_poly_fwd = mcp['x_poly_fwd'] 
      y_poly_fwd = mcp['y_poly_fwd'] 
      x_poly = mcp['x_poly'] 
      y_poly = mcp['y_poly'] 
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

   print("MERGED STARS:", len(merged_stars))
   res = reduce_fit_multi(x_poly,field, merged_stars, cal_params, fit_img, json_conf, cam_id,0,1)
   #res,updated_merged_stars = reduce_fit_multi(x_poly, "x_poly",merged_stars,cal_params,fit_img,json_conf,cam_id,1,show)



   std_dist, avg_dist = calc_starlist_res(merged_stars)
   print("INITIAL RES: ", res, strict)
   print("STD/AVG DIST: ", std_dist, avg_dist)
   res,updated_merged_stars = reduce_fit_multi(x_poly, "x_poly",merged_stars,cal_params,fit_img,json_conf,cam_id,1,show)

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
   res,updated_merged_stars = reduce_fit_multi(x_poly, "x_poly",merged_stars,cal_params,fit_img,json_conf,cam_id,1,show)
   for star in updated_merged_stars:
       
      #(cal_file,ra_center,dec_center,pos_angle,pixscale,dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy, img_res,np_new_cat_x,np_new_cat_y) = star
      (cal_file , center_az, center_el, ra_center, dec_center, position_angle, pixscale, dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int) = star
      #new_merged_stars.append(star)
      if img_res < std_dev_dist :
         new_merged_stars.append(star)
      else:
         print("REMOVING: ", star)
   merged_stars = new_merged_stars 
   options = {}
         
   mode = 0 
   res = scipy.optimize.minimize(reduce_fit_multi, x_poly, args=(field,new_merged_stars,cal_params,fit_img,json_conf,cam_id,mode,show), method='Nelder-Mead', options={})
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
   res,updated_merged_stars = reduce_fit_multi(x_poly, "x_poly",merged_stars,cal_params,fit_img,json_conf,cam_id,1,show)
   if res < 1:
      std_dev_dist = 2


   for star in updated_merged_stars:
      #(cal_file,ra_center,dec_center,pos_angle,pixscale,dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy, img_res, np_new_cat_x,np_new_cat_y) = star
      (cal_file , center_az, center_el, ra_center, dec_center, position_angle, pixscale, dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int) = star
      new_merged_stars.append(star)
      #if img_res < std_dev_dist :
      #   new_merged_stars.append(star)
   merged_stars = new_merged_stars 
   options = {}

   # now do x-poly again without the junk stars
   mode = 0 
   res = scipy.optimize.minimize(reduce_fit_multi, x_poly, args=(field,merged_stars,cal_params,fit_img,json_conf,cam_id,mode,show), method='Nelder-Mead', options={})
   x_poly = res['x']
   x_fun = res['fun']
   cal_params['x_poly'] = x_poly.tolist()
   cal_params['x_fun'] = x_fun


      
   # do y poly 
   field = 'y_poly'
   res = scipy.optimize.minimize(reduce_fit_multi, y_poly, args=(field,merged_stars,cal_params,fit_img,json_conf,cam_id,mode,show), method='Nelder-Mead', options={})
   y_poly = res['x']
   y_fun = res['fun']
   cal_params['y_poly'] = y_poly.tolist()
   cal_params['y_fun'] = y_fun
   


   # do x poly fwd
   field = 'x_poly_fwd'
   xa = .05
   fa = .05
   res = scipy.optimize.minimize(reduce_fit_multi, x_poly_fwd, args=(field,merged_stars,cal_params,fit_img,json_conf,cam_id,mode,show), method='Nelder-Mead'  )

   x_poly_fwd = res['x']
   x_fun_fwd = res['fun']
   cal_params['x_poly_fwd'] = x_poly_fwd.tolist()
   cal_params['x_fun_fwd'] = x_fun_fwd

   # do y poly fwd
   field = 'y_poly_fwd'
   res = scipy.optimize.minimize(reduce_fit_multi, y_poly_fwd, args=(field,merged_stars,cal_params,fit_img,json_conf,cam_id,mode,show), method='Nelder-Mead')
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
   cal_params['center_az'] = img_az
   cal_params['center_el'] = img_el
   return(1, cal_params, merged_stars )

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
      (cal_file , center_az, center_el, ra_center, dec_center, position_angle, pixscale, dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int) = star
      img_res = cat_dist
      ms_key = str(ra) + ":" + str(dec) + ":" + str(six) + ":" + str(siy)
      ms_index[ms_key] = star
      np_new_cat_x = np.float64(new_cat_x)
      np_new_cat_y = np.float64(new_cat_y)
      np_angle_to_center = find_angle((960,540), (np_new_cat_x, np_new_cat_y))
      img_angle_to_center = find_angle((960,540), (six, siy))
      ang_diff = abs(img_angle_to_center - np_angle_to_center)
      np_dist = calc_dist((six,siy), (np_new_cat_x, np_new_cat_y))
      col1,col2 = collinear(six,siy,np_new_cat_x,np_new_cat_y,960,540)
      print("COL:", col1,col2)
      if ang_diff > 1:

         print("BAD ANG:", six, siy, dcname, new_cat_x, new_cat_y, np_new_cat_x, np_new_cat_y, " -- ", img_angle_to_center, np_angle_to_center, ang_diff)
         bad = 1
      elif np_dist < 50:
         print("GOOD ANG:", six, siy, dcname, new_cat_x, new_cat_y, np_new_cat_x, np_new_cat_y, " -- ", img_angle_to_center, np_angle_to_center, ang_diff)
         color = (255)

         cv2.rectangle(img, (int(new_x-2), int(new_y-2)), (int(new_x + 2), int(new_y + 2)), (255), 1)
         line_dist = calc_dist((six,siy), (np_new_cat_x, np_new_cat_y))
         if line_dist > 20:
            cv2.line(img, (six,siy), (int(np_new_cat_x),int(np_new_cat_y)), (0,0,255), 1)
         else:
            cv2.line(img, (six,siy), (int(np_new_cat_x),int(np_new_cat_y)), (0,255,0), 1)
          
         cv2.circle(img,(six,siy), 5, (255), 1)
         if line_dist < 50:  
           np_ms = np.append(np_ms, [[ra,dec,six,siy,img_res]],axis=0 )
      else: 
         print("STAR MISSING SOME FIELDS!", star)
         continue

   if SHOW == 1:
      simg = cv2.resize(img, (960,540))
      cv2.imshow(cam_id, simg)
      cv2.imwrite("/mnt/ams2/tmp/fitmovies/star_img1.png", img)
      cv2.waitKey(30)


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
      gsize = 50
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

               (cal_file , center_az, center_el, ra_center, dec_center, position_angle, pixscale, dcname,mag,ra,dec,img_ra,img_dec,match_dist,orig_x,orig_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int) = info 
               cv2.rectangle(img, (int(new_x-2), int(new_y-2)), (int(new_x + 2), int(new_y + 2)), (255), 1)
               orig_line_dist = calc_dist((six,siy),(orig_x,orig_y)) 

               if orig_line_dist > 100:
                  cv2.line(img, (six,siy), (int(orig_x),int(orig_y)), (0,255,0), 1)
               else:
                  cv2.line(img, (six,siy), (int(orig_x),int(orig_y)), (0,128,0), 1)

               line_dist = calc_dist((six,siy),(new_cat_x,new_cat_y))
               if line_dist > 100:
                  print("BAD LINE DIST:", line_dist)
                  bad = 1
               else:
                  cv2.line(img, (six,siy), (int(new_cat_x),int(new_cat_y)), (255,255,255), 3)

               cv2.circle(img,(six,siy), 5, (255), 1)
               if bad == 0:
                  updated_merged_stars.append((cal_file , center_az, center_el, ra_center, dec_center, position_angle, pixscale, dcname,mag,ra,dec,img_ra,img_dec,match_dist,orig_x,orig_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int))  
            else:   
               print("No match for grid square :(")
   if SHOW == 1:
      simg = cv2.resize(img, (960,540))
      cv2.imshow(cam_id, simg)
      cv2.imwrite("/mnt/ams2/tmp/fitmovies/star_img2.png", img)
      cv2.waitKey(30)

   #return(merged_stars)
   print("UPDATED MERGED STARS", len(updated_merged_stars))
   return(updated_merged_stars)

def reduce_fit_multi(this_poly,field, merged_stars, cal_params, fit_img, json_conf, cam_id=None,mode=0,show=0):
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
      (cal_file , center_az, center_el, ra_center, dec_center, position_angle, pixscale, dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int) = star
      #if 157 < float(pixscale) < 163 and old_img_res > 2:
      #   pixscale = avgpixscale
      #if 157 < float(pixscale) < 163 :
      #   pixscale = avgpixscale
 
      if field == 'x_poly' or field == 'y_poly':
         new_cat_x, new_cat_y = distort_xy(0,0,ra,dec,float(ra_center), float(dec_center), x_poly, y_poly, float(1920), float(1080), float(position_angle),3600/float(pixscale))

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
         cal_params['position_angle'] = position_angle 
         cal_params['pixscale'] = pixscale 
         cal_params['imagew'] = 1920
         cal_params['imageh'] = 1080 
         new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(six,siy,cal_file,cal_params,json_conf)
         new_x, new_y= distort_xy(0,0,img_ra,img_dec,float(ra_center), float(dec_center), x_poly, y_poly, float(cal_params['imagew']), float(cal_params['imageh']), float(cal_params['position_angle']),3600/float(cal_params['pixscale']))

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
      #new_merged_stars.append((cal_file,ra_center,dec_center,pos_angle,pixscale,dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy, img_res, np_new_cat_x, np_new_cat_y))
      new_merged_stars.append((cal_file , center_az, center_el, ra_center, dec_center, position_angle, pixscale, dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int))

      total_res = total_res + img_res
     
 


   total_stars = len(merged_stars)
   if total_stars > 0:
      avg_res = total_res/total_stars
   else:
      avg_res = 999

   desc = "Cam: " + str(cam_id) + " Stars: " + str(total_stars) + " " + field + " Res: " + str(avg_res)[0:6] 
   cv2.putText(this_fit_img, desc,  (5,1070), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 1)

   if SHOW == 1:
      simg = cv2.resize(this_fit_img, (960,540))
      cv2.imshow(cal_params['cam_id'], simg) 
      cv2.waitKey(30)

   print("Total Residual Error:",field, total_res )
   print("Total Stars:", total_stars)
   print("Avg Residual Error:", avg_res )
   print("Show:", show)
   tries = tries + 1
   #print("Try:", tries)
   if mode == 0: 
      return(avg_res)
   else:
      return(avg_res, new_merged_stars)

def calc_starlist_res(ms):

   # compute std dev distance
   tot_res = 0
   close_stars = []
   dist_list = []
   for star in ms:

      if len(star) == 16:
         iname,mag,o_ra,o_dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,old_cat_x,old_cat_y,six,siy,cat_dist  =star 
      if len(star) == 17:
         iname,mag,o_ra,o_dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,old_cat_x,old_cat_y,six,siy,cat_dist,star_int  =star 
      if len(star) == 24:
         (cal_file , center_az, center_el, ra_center, dec_center, position_angle, pixscale, dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int) = star

      #(cal_file , center_az, center_el, ra_center, dec_center, position_angle, pixscale, dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int) = star
      #(cal_file,ra_center,dec_center,pos_angle,pixscale,dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy, img_res,np_new_cat_x,np_new_cat_y) = star
      #px_dist = calc_dist((six,siy),(new_cat_x,new_cat_y))
      dist_list.append(cat_dist)
   std_dev_dist = np.std(dist_list)
   avg_dev_dist = np.mean(dist_list)
   return(std_dev_dist, avg_dev_dist)


def arecolinear(points):
    xdiff1 = float(points[1][0] - points[0][0])
    ydiff1 = float(points[1][1] - points[0][1])
    xdiff2 = float(points[2][0] - points[1][0])
    ydiff2 = float(points[2][1] - points[1][1])

    # infinite slope?
    if xdiff1 == 0 or xdiff2 == 0:
        return xdiff1 == xdiff2
    elif ydiff1/xdiff1 == ydiff2/xdiff2:
        return True
    else:
        return False

def poly_fit_check(line_xs,line_ys, x,y, z=None):
   if z is None:
      if len(line_xs) >= 2:
         try:
            z = np.polyfit(line_xs,line_ys,1)
            f = np.poly1d(z)
         except:
            return(999)

      else:
         return(999)
   #print("Z:", z)
   dist_to_line = distance((x,y),z)
   return(dist_to_line)


def distance(point,coef):
    return abs((coef[0]*point[0])-point[1]+coef[1])/math.sqrt((coef[0]*coef[0])+1)


def get_cal_params(meteor_json_file):
   (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(meteor_json_file)
   before_files = []
   after_files = []
   cal_files= get_cal_files(meteor_json_file, cam)
   for cf,td in cal_files:
      (c_datetime, ccam, c_date_str,cy,cm,cd, ch, cmm, cs) = convert_filename_to_date_cam(cf)
      time_diff = f_datetime - c_datetime
      sec_diff= time_diff.total_seconds()
      if sec_diff <= 0:
         after_files.append((cf,sec_diff))
      else:
         before_files.append((cf,sec_diff))

   after_files = sorted(after_files, key=lambda x: (x[1]), reverse=False)[0:5]
   print("Calibs after this meteor.")
   before_data = []
   after_data = []
   for af in after_files:
      cpf, td = af
      cp = load_json_file(cpf)
      before_data.append((cpf, float(cp['center_az']), float(cp['center_el']), float(cp['position_angle']), float(cp['pixscale']), float(cp['total_res_px'])))

   before_files = sorted(before_files, key=lambda x: (x[1]), reverse=False)[0:5]
   print("Calibs before this meteor.")
   for af in before_files:
      cpf, td = af
      cp = load_json_file(cpf)
      if "total_res_px" in cp:
         after_data.append((cpf, float(cp['center_az']), float(cp['center_el']), float(cp['position_angle']), float(cp['pixscale']), float(cp['total_res_px'])))
      else:
         print("NO RES?", cpf, cp['center_az'], cp['center_el'], cp['position_angle'], cp['pixscale'])

   azs = [row[1] for row in before_data]
   els = [row[2] for row in before_data]
   pos = [row[3] for row in before_data]
   px = [row[4] for row in before_data]
   print("AZS:", azs)

   if len(azs) > 3:
      before_med_az = np.median(azs)
      before_med_el = np.median(els)
      before_med_pos = np.median(pos)
      before_med_px = np.median(px)
   else:
      print("PX:", px)
      before_med_az = np.mean(azs)
      before_med_el = np.mean(els)
      before_med_pos = np.mean(pos)
      before_med_px = np.mean(px)

   azs = [row[1] for row in after_data]
   els = [row[2] for row in after_data]
   pos = [row[3] for row in after_data]
   px = [row[4] for row in after_data]

   if len(azs) > 3:
      after_med_az = np.median(azs)
      after_med_el = np.median(els)
      after_med_pos = np.median(pos)
      after_med_px = np.median(px)
   else:
      after_med_az = np.mean(azs)
      after_med_el = np.mean(els)
      after_med_pos = np.mean(pos)
      after_med_px = np.mean(px)

   print("BEFORE MED:", before_med_az, before_med_el, before_med_pos, before_med_px)
   print("AFTER MED:", after_med_az, after_med_el, after_med_pos, after_med_px)

   autocal_dir = "/mnt/ams2/meteor_archive/" + STATION_ID + "/CAL/AUTOCAL/" + fy + "/solved/"
   mcp_file = autocal_dir + "multi_poly-" + STATION_ID + "-" + cam + ".info"
   if cfe(mcp_file) == 1:
      print("MCP:", mcp_file)
      mcp = load_json_file(mcp_file)
      # GET EXTRA STARS?
   else:
      mcp = None

   print("MCP:", mcp_file)
   before_cp = dict(mcp)
   after_cp = dict(mcp)
   before_cp['center_az'] = before_med_az
   before_cp['center_el'] = before_med_el
   before_cp['position_angle'] = before_med_pos
   before_cp['pixscale'] = before_med_px

   after_cp['center_az'] = after_med_az
   after_cp['center_el'] = after_med_el
   after_cp['position_angle'] = after_med_pos
   after_cp['pixscale'] = after_med_px

   return(before_cp, after_cp)

