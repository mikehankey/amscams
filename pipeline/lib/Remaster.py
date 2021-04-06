from PIL import Image, ImageDraw, ImageFont
from lib.FFFuncs import best_crop_size
import math
import scipy.optimize
from lib.UIJavaScript import *
import glob
from datetime import datetime as dtl
import datetime
#import math
import os
from lib.FFFuncs import ffprobe as ffprobe4, imgs_to_vid
from lib.PipeAutoCal import fn_dir, get_cal_files, get_image_stars, get_catalog_stars, pair_stars, update_center_radec, cat_star_report, minimize_fov, XYtoRADec, poly_fit_check
from lib.PipeVideo import ffmpeg_splice, find_hd_file, load_frames_fast, find_crop_size, ffprobe
from lib.PipeUtil import load_json_file, save_json_file, cfe, get_masks, convert_filename_to_date_cam, buffered_start_end, get_masks, compute_intensity , bound_cnt, day_or_night, calc_dist, get_trim_num
from lib.DEFAULTS import *
from lib.PipeMeteorTests import big_cnt_test, calc_line_segments, calc_dist, unq_points, analyze_intensity, calc_obj_dist, meteor_direction, meteor_direction_test, check_pt_in_mask, filter_bad_objects, obj_cm, meteor_dir_test, ang_dist_vel, gap_test, best_fit_slope_and_intercept
from lib.PipeImage import stack_frames

from lib.PipeDetect import get_move_info, find_object, analyze_object
from lib.PipeImage import stack_frames

import numpy as np
import cv2
import matplotlib
#matplotlib.use('TkAgg')
from matplotlib import pyplot as plt

from sklearn import linear_model, datasets
from skimage.measure import ransac, LineModelND, CircleModel



def make_final_json(mj, json_conf):
   station_id = json_conf['site']['ams_id']
   sd_vid = mj['sd_video_file']
   (f_datetime, camera_id, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(sd_vid)
   red_file = mj['sd_video_file'].replace(".mp4", "-reduced.json")
   if cfe(red_file) == 0:
      print("file not reduced!", red_file)
      return(None)
   else:
      mjr = load_json_file(red_file)

   hd_vid = mj['hd_trim']
   final_vid = mj['final_vid']
   if "hd_red" in mj:
      final_format = "HD"
      hd_mfd = mj['hd_red']['hd_mfd']
      sd_mfd = None
   else:
      final_format = "SD"
      sd_mfd = mjr['meteor_frame_data']
      hd_mfd = None

   cp = mj['cp']

   hd_crop_info = mj['hd_red']['hd_crop_info']
   if "multi_station_event" in mj:
      mse = {}
      if "event_id" in mj['multi_station_event']:
         mse['event_id'] = mj['multi_station_event']['event_id']
      if "event_file" in mj['multi_station_event']:
         mse['event_file'] = mj['multi_station_event']['event_file']
      if "orb_file" in mj['multi_station_event']:
         mse['orb_file'] = mj['multi_station_event']['orb_file']
      if "solve_status" in mj['multi_station_event']:
         mse['solve_status'] = mj['multi_station_event']['solve_status']
      else:
         mse['solve_status'] = "NOT SOLVED."
      mse['start_datetime'] = mj['multi_station_event']['start_datetime']
      mse['stations'] = mj['multi_station_event']['stations']
      mse['files'] = mj['multi_station_event']['files']
   else:
      mse = {}

   sdv_fn,dd = fn_dir(sd_vid)
   hdv_fn,dd = fn_dir(hd_vid)
   fin_fn,dd = fn_dir(final_vid)

   final_vid = mj['final_vid']
   # FOR THE OBSERVATION! 

   frame_data = []
   if hd_mfd is not None:
      for fn in sorted(hd_mfd.keys()):
         data = hd_mfd[fn]
         print(data)
         fro = {}
         fro['dt'] = data['dt']
         fro['fn'] = data['fn']
         fro['x'] = data['hd_lx']
         fro['y'] = data['hd_ly']
       
         fro['az'] = data['az']
         fro['el'] = data['el']
         fro['ra'] = data['ra']
         fro['dec'] = data['dec']
         fro['int'] = 0
         frame_data.append(fro)   
   elif sd_mfd is not None:
      for data in sd_mfd:
         (dt, fn, x, y, w, h, oint, ra, dec, az, el) = row
         fro = {}
         fro['dt'] = dt
         fro['fn'] = fn
         fro['x'] = x
         fro['y'] = y 
         fro['az'] = az
         fro['el'] = el
         fro['ra'] = ra
         fro['dec'] = dec
         fro['int'] = oint
         frame_data.append(fro)   

   final_json = {
      "info": {
         "station_id": station_id,
         "camera_id": camera_id,
         "loc": [json_conf['site']['device_lat'], json_conf['site']['device_lng'], json_conf['site']['device_alt']]
      },
      "multi_station_event" : mse,

      "media": {
         "sd_vid": sdv_fn,
         "hd_vid": hdv_fn,
         "final_vid": fin_fn,
         "final_format": final_format 
      },
      "frames": frame_data,

      "hd_crop_info" : hd_crop_info,
      "calib" : {
         "az" : cp['center_az'],
         "el" : cp['center_el'],
         "ra" : cp['ra_center'],
         "dec" : cp['dec_center'],
         "pos" : cp['position_angle'],
         "pxs" : cp['pixscale'],
         "total_stars" : len(cp['cat_image_stars']),
         "total_res_px" : cp['total_res_px']
      }

   }

   return(final_json)   

def remaster_month(wild,json_conf):
   print("REMASTER MONTH:", wild)
   days = glob.glob("/mnt/ams2/meteors/" + wild + "*")
   print("/mnt/ams2/meteors/" + wild + "*")
   for day_dir in sorted(days, reverse=True):
      day, fdir = fn_dir(day_dir)
      print("DAY:", day)
      if cfe(day_dir,1) == 1:
         remaster_day(day, json_conf)

def remaster_day(day,json_conf):

   print("REMASTER DAY:", day)
   mfs = []
   files = glob.glob("/mnt/ams2/meteors/" + day + "/*.json")
   for mf in files:
      if "reduced" not in mf and "stars" not in mf and "man" not in mf and "star" not in mf and "import" not in mf and "archive" not in mf and "cal" not in mf and "frame" not in mf:
         mfs.append(mf)
   for mf in mfs:
      print(mf)
      make_event_video(mf,json_conf)
   sync_final_day(day, json_conf)

def valid_calib(meteor_file, mj, image,json_conf):
   stars = get_image_stars(meteor_file, image, json_conf,0)

   tmj = dict(mj)

   tmj['cp']['user_stars'] = stars
   tmj['cp'] = pair_stars(tmj['cp'], meteor_file, json_conf, image)
   
   print("NEW IMG STARS:", len(tmj['cp']['user_stars']))
   print("NEW CAT STARS:", len(tmj['cp']['cat_image_stars']))
   print("NEW RES:", tmj['cp']['total_res_px'])

   print("ORIG IMG STARS:", len(mj['cp']['user_stars']))
   print("ORIG CAT STARS:", len(mj['cp']['cat_image_stars']))
   print("ORIG RES:", mj['cp']['total_res_px'])



   star_over = np.zeros((1080,1920,3),dtype=np.uint8)
   # Pass the image to PIL
   pil_im = Image.fromarray(star_over)
   draw = ImageDraw.Draw(pil_im)

   # use DEFAULT truetype font
   bold = False
   if(bold==True):
      font = ImageFont.truetype(VIDEO_FONT_BOLD, VIDEO_FONT_SMALL_SIZE)
   else:
      font = ImageFont.truetype(VIDEO_FONT, VIDEO_FONT_SMALL_SIZE)

    # Draw the text
   rez = []
   for star in mj['cp']['cat_image_stars']:
      print(star, len(star))
      name,mag,ra,dec,ra,dec,match_dist,new_cat_x,new_cat_y,foo,bar,new_cat_x,new_cat_y,six,siy,cat_dist,star_int = star
      rez.append(cat_dist)
      #cv2.putText(image, str(name),  (new_cat_x, new_cat_y), cv2.FONT_HERSHEY_SIMPLEX, .3, (255, 255, 255), 1)
      #cv2.circle(image,(six,siy), 5, (255,255,255), 1)
      draw.text((new_cat_x, new_cat_y), name, font=font, fill="white")

   # Get back the image to OpenCV
   cvimg = cv2.cvtColor(np.array(pil_im), cv2.COLOR_RGB2BGR)
   res_px = np.mean(rez)
   print("RES:", res_px, rez)

   return(mj['cp'], cvimg)

def mask_stars(image_stars, image):
   for star in image_stars:
      #name,mag,ra,dec,ra,dec,match_dist,new_cat_x,new_cat_y,foo,bar,new_cat_x,new_cat_y,six,siy,cat_dist,star_int = star
      (six,siy,sii) = star
      rx1,ry1,rx2,ry2 = bound_cnt(six,siy,image.shape[1],image.shape[0], 2) 
      if len(image.shape) == 3:
         image[ry1:ry2,rx1:rx2] = [0,0,0]
      else:
         image[ry1:ry2,rx1:rx2] = 0
   return(image)


def get_cont(frame):
   min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(frame)
   avg_val = np.mean(frame)
   thresh_val = avg_val +  ((max_val - avg_val) * .5)
   px_diff = max_val - avg_val
   print("PXD:", px_diff)
   if thresh_val < 10:
      thresh_val = 10
   #thresh_val = 25 
   _, threshold = cv2.threshold(frame.copy(), thresh_val, 255, cv2.THRESH_BINARY)


   cnt_res = cv2.findContours(threshold.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
   cnt_data = []
   if len(cnt_res) == 3:
      (_, cnts, xx) = cnt_res
   elif len(cnt_res) == 2:
      (cnts, xx) = cnt_res
   for (i,c) in enumerate(cnts):
      x,y,w,h = cv2.boundingRect(cnts[i])
      if w > 1 and h > 1:
         cnt_data.append((x,y,w,h))
   cnt_data = sorted(cnt_data, key=lambda x: (x[2]*x[3]), reverse=True)
   if len(cnt_data) > 1:
      bx,by,bw,bh = cnt_data[0]
      good_cnt = []
      good_cnt.append(cnt_data[0])
      for x,y,w,h in cnt_data[1:]:
         if (bx <= x <= bx+bw and by <= y <= by+bh) or (bx <= x+w <= bx+bw and by <= y+h <= by+bh):
            print("this cnt is inside a bigger one.")
         else:
            good_cnt.append((x,y,w,h))
      return(good_cnt)
   else:
      return(cnt_data)

def find_bright_spots(img):
   from RMS.ImageLib import adjustLevels
   gamma = 1

   ih,iw = img.shape[:2]
   step = int(ih / 4)
   bright_spots = []
   for i in range(0,4):
      y1 = i * step
      
      y2 = int(y1+step)
      if y2 >= ih:
         y2 = ih - 1
      part_img = img[y1:y2,0:iw]

      avg = np.mean(part_img)

      temp = adjustLevels(part_img, avg,gamma,255)
      temp = cv2.convertScaleAbs(temp)

      avg = np.mean(temp)
      _, threshold = cv2.threshold(temp.copy(), 40, 255, cv2.THRESH_BINARY)
      cnts = get_cont(threshold)
      for x,y,w,h in cnts:
         print(w,h)
         cv2.rectangle(threshold, (int(x), int(y)), (int(x+w) , int(y+h) ), (255, 255, 255), 1)
         bright_spots.append((x,y+y1,w,h))


      #cv2.imshow('pepe', threshold)
      #cv2.waitKey(0)
   return(bright_spots)

def add_spots_to_mask(image, spots):
   for x,y,w,h in spots:
      image[y:y+h,x:x+w] = 255
   return(image)


def scan_for_stars(image):
   from RMS.ImageLib import adjustLevels
   ih, iw = image.shape[:2]
   hor_size = int(ih / 10)
   stars = []
   for i in range(0, 10):
      y1 = i * hor_size
      y2 = y1 + hor_size
      o_row_img = image[y1:y2,0:iw]
      
      row_img = cv2.cvtColor(o_row_img, cv2.COLOR_BGR2GRAY)
      avg = np.mean(row_img) 
      avg = avg #- (avg/3)
      gamma = .8
      temp = adjustLevels(row_img, avg,gamma,255)
      temp = cv2.convertScaleAbs(temp)

      tavg = np.mean(temp) 
      tavg = tavg * 2
      if tavg < 10:
         tavg = 10
      print ("TAVG:", tavg)
      _, threshold = cv2.threshold(temp.copy(), tavg, 255, cv2.THRESH_BINARY)

      cnts = get_cont(threshold)
      for cnt in cnts:
         x,y,w,h = cnt 
         if w <= 8 and h <= 8:
            cv2.rectangle(o_row_img, (int(x), int(y)), (int(x+w) , int(y+h) ), (255, 255, 255), 1)
            cx = x + (w/2)
            cy = y + (h/2)
            star_img = row_img[y:y+h,x:x+h]
            star_int = np.sum(star_img)
            stars.append((cx, cy, star_int))
         else:
            cv2.rectangle(o_row_img, (int(x), int(y)), (int(x+w) , int(y+h) ), (0, 0, 255), 1)
            print("too big:",w,h)

   #   cv2.imshow('star finder adj', o_row_img)
   #   cv2.waitKey(0)
   #for star in stars:
   #   cv2.circle(image,(x,y), 4, (0,0,255), 1)
   #   print(star)
   #cv2.imshow('pepe', image)
   #cv2.waitKey(0)

   return(stars)

def reduce_remote_meteor(video_file, station_id, json_conf):

   # CONFIG / SETUP
   # set local and cloud dirs for station remote data 
   local_conf = "/mnt/ams2/STATIONS/" + station_id + "_as6.json"
   cloud_conf = "/mnt/archive.allsky.tv/" + station_id + "/CAL/as6.json"
   # check to make sure this is not our station
   if station_id != json_conf['site']['ams_id']:
      print("Working with remote meteor.")
   # copy the remote sites config file if we don't aready have it
   if cfe(local_conf) == 0:
      os.system("cp " + cloud_conf + " " + local_conf)
   else:
      print("We have the conf file.")
   # load remote conf
   if station_id != json_conf['site']['ams_id']:
      remote_conf = load_json_file(local_conf)
   else:
      remote_conf = json_conf



   frames,color_frames,subframes,sum_vals,max_vals,pos_vals = load_frames_fast(video_file, json_conf, 0, 0, 1, 1,[])
   stars = scan_for_stars(color_frames[0])
   close_cals,lens_model = get_remote_calib(station_id, video_file,remote_conf)
   calib = get_best_cal(video_file, frames[0], close_cals, stars, lens_model, remote_conf)
   print(calib)
   exit()


   frame_data,color_frames = scan_meteor_file(video_file, station_id, remote_conf, frames,color_frames,subframes)

   # now get remote calib info!

   if color_frames[0].shape[0] < 1080:
      sd_frame_data = frame_data


   for fro in frame_data:
      fn = int(fro['fn'])
      x = int(fro['x'])
      y = int(fro['y'])
      w = int(fro['w'])
      h = int(fro['h'])
      sf = color_frames[fn].copy()
      lx = int(fro['lx'])
      ly = int(fro['ly'])
 
      print(fro)
      sf[ly,lx] = [0,0,255]
      #cv2.rectangle(sf, (int(x), int(y)), (int(x+w) , int(y+h) ), (255, 255, 255), 1)
      cv2.imshow('final',  sf)
      cv2.waitKey(0)

def get_best_cal(video_file, cal_image, close_cals, stars,lens_model, json_conf):
   for td, cal_info in close_cals:
      #print(cal_info)
      calib = {}
      calib['ra_center'] = ""
      calib['dec_center'] = ""
      calib['center_az'] = cal_info[2]
      calib['center_el'] = cal_info[3]
      calib['position_angle'] = cal_info[4]
      calib['pixscale'] = cal_info[5]
      calib['user_stars'] = stars
      if "x_poly" in lens_model:
         calib['x_poly'] = lens_model['x_poly']
         calib['y_poly'] = lens_model['y_poly']
         calib['x_poly_fwd'] = lens_model['x_poly_fwd']
         calib['y_poly_fwd'] = lens_model['y_poly_fwd']
      else:
         calib['x_poly'] = np.zeros(shape=(15,), dtype=np.float64)
         calib['y_poly'] = np.zeros(shape=(15,), dtype=np.float64)
         calib['x_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)
         calib['y_poly_fwd'] = np.zeros(shape=(15,), dtype=np.float64)


      calib = update_center_radec(video_file,calib,json_conf)
      cp = pair_stars(calib, video_file, json_conf, cal_image)
      print("CP?", cal_info[1], cp['center_az'], cp['center_el'], cp['position_angle'], cp['pixscale'], cp['ra_center'], cp['dec_center'], cp['total_res_px'])
      for star in cp['cat_image_stars']:
         print(star)
      #print("RES:", cp['total_res_px'])
      #for star in cp['cat_image_stars'] :
      #   print(star)

def get_remote_calib(station_id,video_file,json_conf):
   (f_datetime, cams_id, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(video_file)
   trim_num = get_trim_num(video_file)
   print(f_datetime, trim_num)
   extra_sec = int(trim_num) / 25
   trim_time = f_datetime + datetime.timedelta(0,extra_sec)
   print("TRIM TIME IS:", trim_time)

      #first_dt = datetime.datetime.strptime(dt, "%Y-%m-%d %H:%M:%S.%f")

   print("Get remote calib for :", station_id, cams_id, f_date_str)
   local_cal_dir = "/mnt/ams2/STATIONS/" + "/CAL/"
   cloud_cal_dir = "/mnt/archive.allsky.tv/" + station_id + "/CAL/"
   # files needed: (multi_poly_AMSX-CAMID.info cal_day_hist.json, cal_history.json
   all_files = []
   all_files.append(('cal_day_hist.json', station_id + "_" + "cal_day_hist.json"))
   all_files.append(('cal_history.json', station_id + "_" + "cal_history.json"))
   for cam in json_conf['cameras']:
      cid = json_conf['cameras'][cam]['cams_id']
      all_files.append(("multi_poly-" + station_id + "-" + cid + ".info", station_id + "_" + cid + "_lens_model.json"))
      if cid == cams_id: 
         lm_file = local_cal_dir + station_id + "_" + cid + "_lens_model.json"
         if cfe(lm_file) == 1:
            lens_model = load_json_file(lm_file)
         else:
            print("NO LENS MODEL!")
            lens_model = None
   if cfe(local_cal_dir,1) == 0:
      os.makedirs(local_cal_dir)

   for file in all_files:
      of, lf = file
      cloud_file = cloud_cal_dir + of
      local_file = local_cal_dir + lf
      if cfe(local_file) == 0:
         cmd = "cp " + cloud_file + " " + local_file 
         print(cmd)
         os.system(cmd)
      else:
         print("we already have this file.", local_file)

   cal_day_hist = load_json_file(local_cal_dir + station_id + "_cal_day_hist.json")
   close_cals = []
   for cdh in cal_day_hist:
      if cdh[0] == cams_id:
         print(cdh)
         cal_date = cdh[1]
         cal_dt = datetime.datetime.strptime(cal_date, "%Y_%m_%d")
         time_diff = trim_time - cal_dt
         td = (time_diff.total_seconds()/60/60/24)
         close_cals.append((td, cdh))


   calib = {}
   calib['ra_center'] = ""
   calib['dec_center'] = ""
   calib['center_az'] = ""
   calib['center_el'] = ""
   calib['position_angle'] = ""
   calib['pix_scale'] = ""
   calib['x_poly'] = ""
   calib['y_poly'] = ""
   calib['x_poly_fwd'] = ""
   calib['y_poly_fwd'] = ""

   close_cals = sorted(close_cals, key=lambda x: (x[0]), reverse=False)

   return(close_cals[0:10], lens_model)


def scan_meteor_file(video_file,station_id, json_conf, frames=None, color_frames=None, subframes=None):

   # load video frames
   if frames is None:
      frames,color_frames,subframes,sum_vals,max_vals,pos_vals = load_frames_fast(video_file, json_conf, 0, 0, 1, 1,[])
   bright_spots = find_bright_spots(frames[0])
   main_mask = np.zeros((1080,1920),dtype=np.uint8)
   main_mask = add_spots_to_mask(main_mask, bright_spots)
   fc = 0
   frame_data = []

   # get initial contours inside each frame
   for oframe in frames:
      frame = cv2.subtract(oframe, frames[0]) 
      if main_mask.shape[0] != frame.shape[0]:
         main_mask = cv2.resize(main_mask, (frame.shape[1], frame.shape[0]))
      print(main_mask.shape, frame.shape)
      frame = cv2.subtract(frame, main_mask) 
      cnts = get_cont(frame)
      cnt_frame_data = [] 
      for cnt in cnts:
         x,y,w,h = cnt 
         #cv2.rectangle(frame, (int(x), int(y)), (int(x+w) , int(y+h) ), (255, 255, 255), 1)
         cnt_frame_data.append((x,y,w,h))
      frame_data.append((fc, cnt_frame_data))
      fc += 1

   # filter out duplicate contours 
   dupes = {}
   for data in frame_data:
      fn, cnts = data
      for cnt in cnts:
         x,y,w,h = cnt
         key = str(x) + "." + str(y)
         if key not in dupes:
            dupes[key] = 1
         else:
            dupes[key] += 1
   dupe_areas = {}

   for key in dupes: 
      print(key, dupes[key])
      if dupes[key] > 5:
         dupe_areas[key] = 1

   # APPLY RANSAC MODEL TO FILTER POINTS
   ffd = []
   XS = []
   YS = []
   for data in frame_data:
      good_cnts = []
      for x,y,w,h in data[1]:
         key = str(x) + "." + str(y)
         if key in dupe_areas:
            print("skip this cnt it is a dupe area. (star, ground light etc)")
         else:
            center_x = int(x + (w/2))
            center_y = int(y + (h/2))
            XS.append(center_x)
            YS.append(center_y)
            good_cnts.append((x,y,w,h))
      ffd.append((data[0], good_cnts))
   XS = np.array(XS)
   YS = np.array(YS)
   XS.reshape(-1, 1)
   YS.reshape(-1, 1)

   data = np.column_stack([XS,YS])
   model = LineModelND()
   model.estimate(data)
   model_robust, inliers = ransac(data, LineModelND, min_samples=2,
                               residual_threshold=10, max_trials=1000)

   outliers = inliers == False

   # generate coordinates of estimated models
   line_x = np.arange(XS.min(),XS.max())  #[:, np.newaxis]
   line_y = model.predict_y(line_x)
   line_y_robust = model_robust.predict_y(line_x)

   # make plot for ransac filter
   fig, ax = plt.subplots()
   ax.plot(data[outliers, 0], data[outliers, 1], '.r', alpha=0.6,
        label='Outlier data')
   ax.plot(data[inliers, 0], data[inliers, 1], '.b', alpha=0.6,
        label='Inlier data')
   plt.gca().invert_yaxis()
   XS = data[inliers,0]
   YS = data[inliers,1]
   #plt.show()

   XS = data[inliers,0]
   YS = data[inliers,1]

   # make mask around the good area XS/YS
   mask_img = np.zeros((oframe.shape[0],oframe.shape[1]),dtype=np.uint8)
   for i in range(0, len(XS)):
      if True:
         x = XS[i]
         y = YS[i]
         h = 10 
         w = 10 
         y1 = y - h
         y2 = y + w
         x1 = x - h
         x2 = x + h
         if y1 < 0:
            y1 = 0
         if x1 < 0:
            x1 = 0
         if x2 >= 1920:
            x2 = 1919 
         if y2 >= 1080:
            y2 = 1079 
         mask_img[y1:y2,x1:x2] = 255

   mask_img = cv2.dilate(mask_img.copy(), None , iterations=4)

   # find largest cnt in the mask and mute everything else
   cnts = get_cont(mask_img)
   if len(cnts) > 1:
      for cnt in cnts[1:]:
         x,y,w,h = cnt
         mask_img[y:y+h, x:x+w] = 0

   # invert mask img now we can subtract it
   mask_img = (255-mask_img)
   mask_img = add_spots_to_mask(mask_img, bright_spots)


   # get contours again with mask applied 
   frame_data = []
   dupes = {}
   fc = 0
   #cv2.imshow('P', mask_img)
   #cv2.waitKey(0)
   for oframe in frames:
      frame = cv2.subtract(oframe, frames[0]) 
      if mask_img.shape[0] != oframe.shape[0]:
         mask_img = cv2.resize(mask_img, (frame.shape[1], frame.shape[0]))

      frame = cv2.subtract(frame, mask_img)
      cnts = get_cont(frame)
      cnt_frame_data = [] 
      for cnt in cnts:
         x,y,w,h = cnt 
         key = str(x) + "." + str(y)
         if key not in dupes:
            dupes[key] = 1
         else:
            dupes[key] += 1
         cv2.rectangle(frame, (int(x), int(y)), (int(x+w) , int(y+h) ), (255, 255, 255), 1)
         cnt_frame_data.append((x,y,w,h))
      frame_data.append((fc, cnt_frame_data))
      #cv2.imshow("P", frame)
      #cv2.waitKey(0)
      fc += 1

   # REMOVE DUPE CNTS IF THEY STILL EXIST
   good_cnts = []
   clean_fd = []
   for data in frame_data:
      fn, cnts = data
      good_cnts = []
      for cnt in cnts:
         x,y,w,h = cnt 
         key = str(x) + "." + str(y)
         skip = 0
         if key in dupes:
            if dupes[key] > 2:
               skip = 1
         if skip == 0:
            good_cnts.append(cnt)
      clean_fd.append((fn, good_cnts))

   # BEST CNT PER FRAME
   # now all data should be pretty good but 
   # we have to choose the best cnt per frame

   last_x = None
   dist = 0

   # get movement info
   dom_dir, x_dir, y_dir = dir_info(clean_fd)

   frame_data = []
   for data in clean_fd:
      fn, cnts = data
      frame = color_frames[fn]

      if len(cnts) == 0:
         # no contours to deal with
         foo = 1
         best_cnt = None
      elif len(cnts) == 1:
         # just 1 cnt 
         best_cnt = cnts[0]
         x,y,w,h = cnts[0]
         center_x = int(x + (w/2))
         center_y = int(y + (h/2))
         #cv2.rectangle(frame, (int(x), int(y)), (int(x+w) , int(y+h) ), (255, 255, 255), 1)
         if last_x is not None:
            dist = calc_dist((center_x,center_y), (last_x,last_y))
         print(fn,x,y,dist)
         last_x = x
         last_y = y
      else:
         # many cnts we have to choose the best one
         last_best_x = None
         last_best_y = None
         for cnt in cnts:
            x,y,w,h = cnt
            #cv2.rectangle(frame, (int(x), int(y)), (int(x+w) , int(y+h) ), (255, 255, 255), 1)
            center_x = int(x + (w/2))
            center_y = int(y + (h/2))
            dist = calc_dist((center_x, center_y), (last_x,last_y))
            print(fn,x,y,dist)
            if last_best_x is None:
               last_best_x = x
               last_best_y = y
               best_cnt_x = cnt
            else:
               # is this x,y further down the track than the last best one?
               if x_dir == "right_to_left":
                  # we want the cnt that is lowest in x value
                  if x < last_best_x:
                     print("BETTER? ", x, last_best_x)
                     # this cnt is better for the x_val
                     best_cnt_x = cnt
                     last_best_x = x
               else:
                  # we want the cnt that is highest in x value
                  if x + w > last_best_x:
                     # this cnt is better for the x_val
                     best_cnt_ = cnt
                     last_best_x = x + w
            last_x = x
            last_y = y
         best_cnt = best_cnt_x  
         x,y,w,h= best_cnt
         #cv2.rectangle(frame, (int(x), int(y)), (int(x+w) , int(y+h) ), (0, 0, 255), 1)
      print("BEST:", best_cnt)
      frame_data.append((fn, best_cnt))

   # by now we have 1 leading edge cnt per frame
   # now we need to choose the leading edge or blob focus area (for fireballs)
   final_frame_data = []
   for data in frame_data:
      fn, cnts = data
      if cnts is not None:
         frame_obj = {}
         x,y,w,h= cnts
         lx, ly,cx,cy = get_leading_point(cnts, dom_dir, x_dir, y_dir) 
         frame_obj['fn'] = fn
         frame_obj['x'] = x
         frame_obj['y'] = y
         frame_obj['w'] = w
         frame_obj['h'] = h
         frame_obj['lx'] = lx
         frame_obj['ly'] = ly
         frame_obj['cx'] = cx
         frame_obj['cy'] = cy
         #meteor exists here
         frame = color_frames[fn]
         bw_frame = frames[fn]
 
         # this CNT is HUGE must be a fireball
         if w > 25 or h > 25:
            # We need to reduce the size of this cnt by raising the thresh
            cnt_img = bw_frame[y:y+h,x:x+w]
            min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(cnt_img)
            thresh_val = max_val - 20
            if thresh_val > 200:
               thresh_val = 200
            print("TV:", thresh_val)
            if thresh_val < 80:
               thresh_val = 80
            _, threshold = cv2.threshold(cnt_img.copy(), thresh_val, 255, cv2.THRESH_BINARY)
            cnts = get_cont(threshold)
            if len(cnts) == 0:
               foo = 1 
            elif len(cnts) == 1:
               sx,sy,sw,sh = cnts[0]
               slx, sly,scx,scy = get_leading_point(cnts[0], dom_dir, x_dir, y_dir) 
               slx += x
               sly += y
               scx += x
               scy += y
               print("SUB:", sw,sh)
            else:
               best_cnt = get_leading_cnt(cnts, dom_dir, x_dir, y_dir) 
               sx,sy,sw,sh = best_cnt 
               slx, sly,scx,scy = get_leading_point(best_cnt, dom_dir, x_dir, y_dir) 
               slx += x
               sly += y
               scx += x
               scy += y
               cnts = [best_cnt]
            if cnts is not None:
               frame_obj['sx'] = sx + x
               frame_obj['sy'] = sy + y
               frame_obj['sw'] = sw
               frame_obj['sh'] = sh
               frame_obj['slx'] = slx
               frame_obj['sly'] = sly
               frame_obj['scx'] = scx
               frame_obj['scy'] = scy
                

            #cv2.imshow("pepe2", threshold)
            #cv2.waitKey(30)
 
            #cv2.rectangle(frame, (int(x), int(y)), (int(x+w) , int(y+h) ), (0, 0, 255), 1)
      print(data)


      if cnts is not None:
         final_frame_data.append(frame_obj)
      #cv2.imshow("pepe", frame)
      #cv2.waitKey(30)

   # if we have more than 100 frames we are dealing with a bigger meteor and should determine
   # a rolling estimate before and after each frame and then check the leading points against 
   # this for QA purposes
   final_frame_data = sorted(final_frame_data, key=lambda x: (x['fn']), reverse=False)
   total_frames = len(final_frame_data)
   fc = 0
   xs = []
   ys = []

   for frame_obj in final_frame_data:
      lx = frame_obj['lx']
      ly = frame_obj['ly']
      x = frame_obj['x']
      y = frame_obj['y']
      w = frame_obj['w']
      h = frame_obj['h']
      cx = int(x + (w/2))
      cy = int(y + (h/2))
      if w > 50 and h > 50:
         # FRAME IS A BIG BURST
         xs.append(cx)
         ys.append(cy)
      elif w > 25 and h > 25:
         if "slx" in frame_obj:
            slx = frame_obj['slx']
            sly = frame_obj['sly']
            print("USING SLX!:", slx, sly)
            ex = int((lx + cx + slx) / 3)
            ey = int((ly + cy + sly) / 3)
         else:
            print("NO SLX?")
            ex = int((lx + cx ) / 2)
            ey = int((ly + cy ) / 2)
         xs.append(ex)
         ys.append(ey)
      else:
         ex = int((lx + cx ) / 2)
         ey = int((ly + cy ) / 2)
         xs.append(ex)
         ys.append(ey)

   # FINAL FINAL
   # UGH! This is the final final loop. 
   final_xs = []
   final_ys = []
   est_xs = []
   est_ys = []
   fc = 0
   frame_data = []
   for frame_obj in final_frame_data:
      print("FD:", frame_obj)
      frame = color_frames[fn]
      overlay = frame.copy()
      fn = frame_obj['fn']
      x = frame_obj['x']
      y = frame_obj['y']
      w = frame_obj['w']
      h = frame_obj['h']
      lx = frame_obj['lx']
      ly = frame_obj['ly']
      cx = int(x + (w/2))
      cy = int(y + (h/2))
      if "slx" in frame_obj:
         slx = frame_obj['slx']
         sly = frame_obj['sly']
      else:
         slx = lx
         sly = ly
      
      if fc >= 30 and total_frames - fc >= 30:
         est_buf = 30 
      elif fc >= 25 and total_frames - fc >= 25:
         est_buf = 25
      elif fc >= 20 and total_frames - fc >= 20:
         est_buf = 20 
      elif fc >= 15 and total_frames - fc >= 15:
         est_buf = 15
      elif fc >= 10 and total_frames - fc >= 10:
         est_buf = 10 
      elif fc >= 5 and total_frames - fc >= 5:
         est_buf = 5
      else:
         est_buf = None 
      if est_buf is not None:
         before_fc1 = fc-est_buf
         before_fc2 = fc-1
         after_fc1 = fc+1
         after_fc2 = fc+est_buf
         print("EST BUF:", before_fc1, before_fc2, after_fc1, after_fc2)
         est_before_x = int(np.mean(xs[fc-est_buf:fc-1]))
         est_before_y = int(np.mean(ys[fc-est_buf:fc-1]))
         est_after_x = int(np.mean(xs[fc+1:fc+est_buf]))
         est_after_y = int(np.mean(ys[fc+1:fc+est_buf]))
         est_x = int((est_before_x + est_after_x) / 2)
         est_y = int((est_before_y + est_after_y) / 2)
         print("EST!", est_buf)

         
      else:
         print("EST IS NONE!", est_buf)
         est_x = int((lx + cx) / 2)
         est_y = int((ly + cy) / 2)

      print("ALL POSSIBLE POINTS:", cx, cy, lx, ly, slx, sly, est_x, est_y)
      merge_x = int((cx + lx + slx + est_x) / 4)
      merge_y = int((cy + ly + sly + est_y) / 4)

      print("MERGE XY:", merge_x, merge_y)

      # find error between orig lx,ly, and est_x, est_y & merge_x, merge_y
      lxy_err = calc_dist((lx,ly), (est_x,est_y))
      mxy_err = calc_dist((lx,ly), (merge_x,merge_y))
      sxy_err = calc_dist((slx,sly), (est_x,est_y))
      cxy_err = calc_dist((cx,cy), (est_x,est_y))
      mean_err = (lxy_err + mxy_err + sxy_err + cxy_err) / 4
      print("ERROR (l/e,l/m,s/e,c/e):", lxy_err, mxy_err, sxy_err, cxy_err)
      good_xs = []
      good_ys = []
      if lxy_err < mean_err:
         good_xs.append(lx)
         good_ys.append(ly)
      if mxy_err < mean_err:
         good_xs.append(merge_x)
         good_ys.append(merge_y)
      if sxy_err < mean_err:
         good_xs.append(slx)
         good_ys.append(sly)
      if cxy_err < mean_err:
         good_xs.append(cx)
         good_ys.append(cy)
      good_xs.append(est_x)
      good_ys.append(est_y)
      good_xs.append(est_x)
      good_ys.append(est_y)

      if len(good_xs) > 1:
         best_x = int(np.mean(good_xs))
         best_y = int(np.mean(good_ys))
         print("BEST USING MEAN:", good_xs)
         print("BEST USING MEAN:", good_ys)
      else:
         best_x = est_x 
         best_y = est_y
         print("BEST USING EST:", est_x)
         print("BEST USING EST:", est_y)
      print("BEST:", best_x, best_y)
      cv2.circle(overlay,(best_x,best_y), 2, (0,0,255), 1)
      cv2.circle(overlay,(est_x,est_y), 2, (255,0,0), 1)
      est_best_err = calc_dist((best_x,best_y), (est_x,est_y))
      est_lx_err = calc_dist((lx,ly), (est_x,est_y))

      print("BEST ERROR:", est_best_err, est_lx_err) 
      final_x = int((est_x + best_x)/2)
      final_y = int((est_y + best_y)/2)
      frame_obj['final_x'] = final_x
      frame_obj['final_y'] = final_y
      print(frame_obj)
      cv2.line(overlay, (final_x-50,final_y), (final_x+50, final_y), (155,155,155,100), 1)
      cv2.line(overlay, (final_x,final_y-50), (final_x, final_y+50), (155,155,155,100), 1)
      alpha = .4
      show_frame = cv2.addWeighted(overlay, alpha, frame, 1- alpha, 0)
      final_xs.append(final_x)
      final_ys.append(final_y)
      est_xs.append(est_x)
      est_ys.append(est_y)
      #cv2.imshow('pepe', show_frame)
      #cv2.waitKey(0)
      fc += 1
      frame_data.append(frame_obj)

  
   frame_data = add_dist_info(frame_data)

   fig, ax = plt.subplots()
   ax.plot(final_xs, final_ys, '.r', alpha=0.6,
        label='final data')
   ax.plot(est_xs, est_ys, '.b', alpha=0.6,
        label='final data')
   plt.gca().invert_yaxis()
   #plt.show()

   return(frame_data, color_frames)

def add_dist_info(frame_data):
   last_x = None
   first_x = None
   last_dist_from_start = None
   new_frame_data = []
   for fo in frame_data:
      fx = fo['final_x']
      fy = fo['final_y']
      if first_x is None:
         first_x = fx
         first_y = fy
      if last_x is not None:
         dist_from_last = calc_dist((fx,fy), (last_x,last_y))
         xdiff = fx - last_x
         ydiff = fy - last_y
      else:
         dist_from_last = 0
         xdiff = 0
         ydiff = 0
      dist_from_start= calc_dist((first_x,first_y), (fx,fy))
      if last_dist_from_start is not None:
         seg_len = dist_from_start - last_dist_from_start
      else:
         seg_len = 0
      last_x = fx
      last_y = fy
      last_dist_from_start = dist_from_start
      fo['dist_from_start'] = dist_from_start
      fo['dist_from_last'] = dist_from_last
      fo['seg_len'] = seg_len
      fo['xdiff'] = xdiff
      fo['ydiff'] = ydiff 
      new_frame_data.append(fo)
      print(fx,fy, dist_from_start, dist_from_last, seg_len, xdiff, ydiff)
   return(new_frame_data)

def get_leading_point(cnt, dom_dir, x_dir, y_dir):
   x,y,w,h = cnt
   cx = int(x + (w/2))
   cy = int(y + (h/2))
   if x_dir == "right_to_left":
      # low x is best
      lx = x
   else:
      # high x is best
      lx = x + w
   if y_dir == "down_to_up":
      # low y is best
      ly = y 
   else:
      ly = y + h 

   #xxx = input("xxx")
   return(lx,ly, cx,cy)

def get_leading_cnt(cnts, dom_dir, x_dir, y_dir):
   last_best_x = None 
   for cnt in cnts:
      x,y,w,h = cnt
      print("LEADING CNT:", x,y,w,h)
      if last_best_x is None:
         last_best_x = x
         last_best_y = y
         best_cnt_x = cnt
         best_cnt_y = cnt
      else:
         # is this x,y further down the track than the last best one?
         if x_dir == "right_to_left":
            # we want the cnt that is lowest in x value
            if x < last_best_x:
               # this cnt is better for the x_val
               best_cnt_x = cnt
               last_best_x = x
               print("LOWER X IS BETTER THIS IS BEST? ", best_cnt_x)
         else:
            # we want the cnt that is highest in x value
            if x + w > last_best_x:
               # this cnt is better for the x_val
               best_cnt_x = cnt
               last_best_x = x + w
               print("HIGHER X IS BETTER THIS IS BEST? ", best_cnt_x)
         if y_dir == "down_to_up":
            # we want the cnt that is lowest in y value
            if y < last_best_y:
               # this cnt is better for the x_val
               best_cnt_y = cnt
               last_best_y = y
               print("LOWER Y IS BETTER THIS IS BEST? ", best_cnt_y)
         else:
            # we want the cnt that is highest in x value
            if y + h > last_best_y:
               # this cnt is better for the x_val
               best_cnt_y = cnt
               last_best_y = y + y
               print("HIGHER Y IS BETTER THIS IS BEST? ", best_cnt_y)

   print("BEST X:", best_cnt_x)
   print("BEST Y:", best_cnt_y)
   if best_cnt_x[0] != best_cnt_y[0]:
      print("BEST CNT Y/X are not the same! lets talk the bigger one")
      if best_cnt_x[2] +best_cnt_x[3] > best_cnt_y[2] + best_cnt_y[3]:
         best_cnt_x = best_cnt_x
      else:
         best_cnt_x = best_cnt_y

   return(best_cnt_x)

def dir_info(frame_data):
   first_x = None
   last_x= None
   for fn, cnts in frame_data:
      if first_x is None:
         if len(cnts) > 0:
            first_x = cnts[0][0]
            first_y = cnts[0][1]
      if len(cnts) > 0:
         last_x = cnts[0][0]
         last_y = cnts[0][1]
   if last_x is not None:
      x_diff = first_x - last_x
      y_diff = first_y - last_y
   else:
      x_diff = 0
      y_diff = 0
   if abs(x_diff) > abs(y_diff):
      dom_dir = "x"
   else:
      dom_dir = "y"
   if x_diff > 0:
      x_dir = "right_to_left"
   else:
      x_dir = "left_to_right"
   if y_diff > 0:
      y_dir = "down_to_up"
   else:
      y_dir = "up_to_down"
   return(dom_dir, x_dir, y_dir)
      


def make_event_video(meteor_file,json_conf):
   # setup input / env vars
   (f_datetime, cam, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(meteor_file)
   amsid = json_conf['site']['ams_id']
   if "/mnt/ams2" not in meteor_file:
      date = meteor_file[0:10]
      meteor_file = "/mnt/ams2/meteors/" + date + "/" + meteor_file
   
   red_file = meteor_file.replace(".json", "-reduced.json")

   # load meteor file
   if cfe(meteor_file) == 1:
      mj = load_json_file(meteor_file)
   else:
      print("NO MJF", meteor_file)
      return()

   if "hd_red" in mj:
      if "final_vid" in mj:
         if cfe(mj['final_vid']) == 1:
            print("Already did it.")
            #return()

   # load reduction file
   if cfe(red_file) == 1:
      mjr = load_json_file(red_file)
   else:
      print("NO MJR", red_file)
      return()

   mjr = load_json_file(red_file)
   sd_vid = mj['sd_video_file']

   # load HD video file

   if "hd_trim" in mj:
      hd_vid = mj['hd_trim']
   else:
      print("NO HD file so can't do hd reduce.")

      mj['hd_red'] = {}
      mj['hd_red']['status'] = 0
      mj['hd_red']['err'] = "no hd file."
      return(0)
   if cfe(sd_vid) == 1:
      sd_frames,sd_color_frames,sd_subframes,sd_sum_vals,sd_max_vals,sd_pos_vals = load_frames_fast(sd_vid, json_conf, 0, 0, 1, 1,[])
   if cfe(hd_vid) == 1:
      hd_frames,hd_color_frames,subframes,sum_vals,max_vals,pos_vals = load_frames_fast(hd_vid, json_conf, 0, 0, 1, 1,[])
   else:
      hd_vid = None

   # apply calib and make star overlay 
   mj['cp'],star_overlay = valid_calib(meteor_file, mj,hd_frames[0], json_conf) 
   print(sd_vid, hd_vid)
   print(len(subframes))
   sd_dts = []
   sd_fns = []
   sd_xs = []
   sd_ys = []

   # load SD meteor frame data
   if "user_mods" in mj:
      user_mods = mj['user_mods']['frames']
   else:
      user_mods = None
   if "meteor_frame_data" in mjr:
      mfd = mjr['meteor_frame_data']
   else:
      print("NO MFD:")
      mj['hd_red'] = {}
      mj['hd_red']['status'] = 0
      mj['hd_red']['err'] = "no sd mfd ."

      return()

   for row in mfd:
      (dt, fn, x, y, w, h, oint, ra, dec, az, el) = row
      sd_dts.append(dt)
      sd_fns.append(fn)
      if user_mods is not None:
         if fn in user_mods:
            x = user_mods[fn][0]
            y = user_mods[fn][1]
      sd_xs.append(x)
      sd_ys.append(y)

   # determine SD ROI area
   min_x = min(sd_xs) - 100
   min_y = min(sd_ys) - 100
   max_x = max(sd_xs) + 100
   max_y = max(sd_ys) + 100
   crop_area = [min_x, min_y, max_x, max_y]
   if min_x < 0:
      min_x = 0
   if min_y < 0:
      min_y = 0
   if max_x > 1919:
      max_x = 1919 
   if max_y > 1079:
      max_y = 1079

   # get movement info
   dom_dir, x_dir, y_dir = get_move_info(mj['best_meteor'], 10, 10)
   fi = 0

   # loop over HD subframes and find meteor objects in the frames
   hd_frame_data = {}
   last_x = None
   last_y = None
   last_dists = []
   last_dist = 0
   last_good_fn = None
   fx = None
   fy = None
   last_dist_from_start = 0
   mc = 0
   seg_len = None
   segs = []

   for frame in subframes:
      print("###########################################")
      print("FRAME:", fi)
      if fi > 2:  
         if preg_stack is None:
            preg_stack = stack_frames(subframes[0:2])
         else:
            temp = [preg_stack, last_frame]
            preg_stack = stack_frames(temp)
         frame = cv2.subtract(frame, preg_stack) 
      else:
         preg_stack = None
      frame = mask_stars(mj['cp']['user_stars'], frame)

      cframe = hd_color_frames[fi]
      crop_frame = frame[min_y:max_y, min_x:max_x]
      crop_frame = frame[min_y:max_y, min_x:max_x]
      min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(crop_frame)
      avg_val = np.mean(crop_frame)
      thresh_val = avg_val +  ((max_val - avg_val) * .10)
      #if thresh_val > 100:
      #   thresh_val = 100
      px_diff = max_val - avg_val
      print("PXD:", px_diff)
      if thresh_val < 10:
         thresh_val = 10 
      _, threshold = cv2.threshold(crop_frame.copy(), thresh_val, 255, cv2.THRESH_BINARY)

      conts = get_lead_contour_in_image(threshold, dom_dir,x_dir,y_dir,min_x,min_y,seg_len,last_x,last_y)
      if len(conts) == 0:
         hd_frame_data[fi] = {}


      #if len(conts) > 0:
      #   sf = cframe.copy()
      #   for x,y,w,h,lx,ly in conts:
      #      cv2.rectangle(sf, (int(x), int(y)), (int(x+w) , int(y+h) ), (255, 255, 255), 1)


      if len(conts) > 0:
         x,y,w,h,lx,ly = conts[0]
         if last_x is not None:
            dist_from_last = calc_dist((lx,ly),(last_x,last_y))
            if fx is not None:
               dist_from_start = calc_dist((lx,ly),(fx,fy))
            else:
               dist_from_start = 0
         else:
            dist_from_last = 0
            dist_from_start = 0
         last_dists.append(dist_from_last)

         if len(last_dists) > 1:
            med_last_dist = np.median(last_dists)

         if True:
            if last_good_fn is not None:
               frame_diff = fi - last_good_fn
            else:
               frame_diff = 0
            print("FRAME DIFF:", fi, last_good_fn, frame_diff)
            if True:
               print("LAST DIST:", dist_from_start, last_dist_from_start, (dist_from_start- last_dist_from_start))
                #and (dist_from_start- last_dist_from_start) > 0:
               #if last_good_fn is not None and (dist_from_start- last_dist_from_start) < 0:
               #   continue
               seg_len = dist_from_start - last_dist_from_start
               if mc > 2:
                  print("SEG:", seg_len, med_seg, abs(seg_len - med_seg))
                  if abs(seg_len - med_seg) > 10:
                     print("BAD SEG LEN SKIP!")
               #      continue

               hd_frame_data[fi] = {}
               hd_frame_data[fi]['fn'] = fi
               hd_frame_data[fi]['hd_x'] = x
               hd_frame_data[fi]['hd_y'] = y
               hd_frame_data[fi]['hd_lx'] = lx
               hd_frame_data[fi]['hd_ly'] = ly
               hd_frame_data[fi]['hd_w'] = w
               hd_frame_data[fi]['hd_h'] = h
               hd_frame_data[fi]['dist_from_last'] = dist_from_last
               hd_frame_data[fi]['dist_from_start'] = dist_from_start
               segs.append(seg_len)
               if len(segs) > 2:
                  med_seg = np.median(segs)
               else:
                  med_seg = seg_len
               hd_frame_data[fi]['seg_dist'] = dist_from_start - last_dist_from_start 
               #cv2.circle(cframe,(lx,ly), 2, (0,0,255), 1)
               last_good_fn = fi
               if fx is None:
                  fx = lx
                  fy = ly
               last_dist_from_start = dist_from_start
               mc += 1

         last_x = lx
         last_y = ly
      print("C:", conts)
      if SHOW == 1:
         cv2.imshow('pepe', cframe)
         cv2.waitKey(30)
      fi += 1
      last_frame = frame

   # now that we have the objs, determine consecutive motion and which are real vs bad

   cm = 0
   for hd_fn in hd_frame_data:
      data = hd_frame_data[hd_fn]
      frame = hd_color_frames[hd_fn]
      if "hd_lx" in data:
         if cm == 0:
            cm = 1
         else:
            cm = cm + 1
         rx1,ry1,rx2,ry2 = bound_cnt(data['hd_lx'],data['hd_ly'],frame.shape[1],frame.shape[0], 10) 


         roi_img = frame[ry1:ry2,rx1:rx2]

         last_good_fn = hd_fn
      else:
         if last_good_fn is not None:
            if hd_fn - last_good_fn > 4: 
               cm = 0


      data['fn'] = hd_fn
      data['cm'] = cm
      hd_frame_data[hd_fn] = data
      print(hd_fn, data)

   # determine HD event start and end frames
   event_start = None
   event_end = None
   events = []
   for hd_fn in hd_frame_data:
      data = hd_frame_data[hd_fn]
      if "hd_lx" in data:
         if event_start is None:
            if data['cm'] >= 1:
               if hd_fn + 3 in hd_frame_data:
                  if hd_frame_data[hd_fn+3]['cm'] >= 2:
                     event_start = hd_fn 
      if hd_fn +1 in hd_frame_data:
         if event_start is not None and event_end is None and data['cm'] == last_cm and 'hd_lx' not in data and "hd_lx" not in hd_frame_data[hd_fn+1] :
            event_end = hd_fn - 1
            if event_end - event_start >= 3:
               events.append((event_start, event_end))
               event_start = None
               event_end = None
      else:
         event_end = hd_fn - 1
      last_cm = data['cm']

   print("EVENT START END", event_start, event_end)
   print("EVENT START END", events)
   last_dist_from_start = None

   # group HD obj frames in objects
   objects = {}
   if len(events) == 0:
      for fn in hd_frame_data:
         data = hd_frame_data[fn]
         if "hd_lx" in data:
            HD = 1
            obj, objects = track_obj(objects, fn,data['hd_lx'], data['hd_ly'])
            objects[obj] = analyze_object(objects[obj], 1, 1)
            print("TRACK OBJECTS:", obj, objects[obj]['ofns'], objects[obj]['report'])
     



      sfs = []
      efs = []
      for obj in objects:
          if objects[obj]['report']['meteor'] == 1:
            print("METEOR OBJECT:", objects[obj])
            start_fn = objects[obj]['ofns'][0]
            end_fn = objects[obj]['ofns'][-1]
            sfs.append(start_fn)
            efs.append(end_fn)
      if len(sfs) > 0:
         events = [[min(sfs), max(efs)]]

   # splice out the 'main' hd event and handle multi-events
   print("LEN EVENTS:", len(events), events)
   if len(events) == 0:
      print("NO EVENTS!?")
      stack_image = stack_frames(hd_color_frames)
      if SHOW == 1:
         cv2.imshow('pepe', stack_image)
         cv2.waitKey(99)

      mj['hd_red'] = {}
      mj['hd_red']['status'] = 0
      mj['hd_red']['err'] = "no hd events found."

      return()

   if len(events) == 2:
      ff = events[0][0]
      lf = events[1][1]
      fn1 = events[0][1]
      fn2 = events[1][0]
      fd = fn2 - fn1
      print("FD!", fd)
      gap_dist = calc_dist((hd_frame_data[fn1]['hd_lx'], hd_frame_data[fn1]['hd_ly']), (hd_frame_data[fn2]['hd_lx'], hd_frame_data[fn2]['hd_ly']))
      print("GAP:", gap_dist)
      if fd < 10 and gap_dist < 50:
         print("merge these events.", fd, gap_dist)
         events[0] = [ff,lf]
      #exit()

   if len(events) > 2:
      for event in events:
         print(event)
      for obj in objects:
         print(objects[obj])
      print("MANY EVENTS!!!", events)
      stack_image = stack_frames(hd_color_frames)
      #cv2.imshow('pepe', stack_image)
      #cv2.waitKey(30)

      mj['hd_red'] = {}
      mj['hd_red']['status'] = 0
      mj['hd_red']['err'] = "too many hd events found."

      return()
   else:
      # load HD frame data into a key'd dict 

      hd_mfd_dict = {}
      fx = None
      fy = None
      last_x = None
      last_y = None
      missing = 0

      print("EVENT START END:", events[0][0],events[0][1])
      for i in range(events[0][0],events[0][1]):
         data = hd_frame_data[i]
         if fx is None and "hd_lx" in data:
            fx = data['hd_lx']
            fy = data['hd_ly']
            dist_from_start = 0
            hd_frame_data[i]['dist_from_start'] = dist_from_start
         else:
            if "hd_lx" in data:
               if last_x is not None:
                  
                  dist_from_last = calc_dist((last_x,last_y), (data['hd_lx'],data['hd_ly']))
                  hd_frame_data[i]['x_dist'] = last_x - data['hd_lx']
                  hd_frame_data[i]['y_dist'] = last_y - data['hd_ly']
               else:
                  dist_from_last = 0
                  hd_frame_data[i]['x_dist'] = 0 
                  hd_frame_data[i]['y_dist'] = 0
               dist_from_start = calc_dist((fx,fy),(data['hd_lx'],data['hd_ly']))
               if last_dist_from_start is not None:
                  seg_dist = dist_from_start - last_dist_from_start
                  hd_frame_data[i]['seg_dist'] = seg_dist
               else:
                  hd_frame_data[i]['seg_dist'] = 0
               hd_frame_data[i]['dist_from_last'] = dist_from_last
               hd_frame_data[i]['dist_from_start'] = dist_from_start
               last_dist_from_start = dist_from_start
            else:
               print("MISSING FRAME DATA!")
               missing += 1
         if "hd_lx" in data:
            last_x = data['hd_lx']
            last_y = data['hd_ly']



         hd_mfd_dict[i] = hd_frame_data[i]
         print(hd_frame_data[i])

   hd_frame_data = hd_mfd_dict
   if missing > 0:
      hd_frame_data = fill_missing_frames(hd_frame_data)

   # HD DATA SHOULD BE CLEANED UP AND COMPLETE NOW! 
   for fn in hd_frame_data:
      data = hd_frame_data[fn]
      frame = hd_color_frames[fn]
      show_frame = frame.copy()
      rx1,ry1,rx2,ry2 = bound_cnt(data['hd_lx'],data['hd_ly'],frame.shape[1],frame.shape[0], 10) 
      roi_img = frame[ry1:ry2,rx1:rx2]
      roi_big = cv2.resize(roi_img, (300,300))
      show_frame[0:300,0:300] = roi_big
      #cv2.rectangle(show_frame, (int(rx1), int(ry1)), (int(rx2) , int(ry2) ), (255, 255, 255), 1)
      if SHOW == 1:
         cv2.imshow('pepe', show_frame)
         cv2.waitKey(30)

      print(hd_frame_data[fn])

   # NOW SYNC WITH SD FRAMES:
   print("FINAL HD DATA:")
   # still need to : fill in time data and new az/el/ra/dec
   first_time = None
   mfd = mjr['meteor_frame_data']
   mfdd = {}
   for data in mfd:
      (dt, sd_fn, sd_x, sd_y, w, h, oint, ra, dec, az, el) = data
      mfdd[sd_fn] = {}
      mfdd[sd_fn]['dt'] = dt
      mfdd[sd_fn]['sd_x'] = sd_x
      mfdd[sd_fn]['sd_y'] = sd_y
   
   sd_hd_sync = sync_hd_sd_frames(mfd, hd_frame_data)
   final_hd_frames = []

   for hd_fn in hd_frame_data: 
      sd_fn = hd_fn + sd_hd_sync
      hd_frame_data[hd_fn]['sd_fn'] = hd_fn + sd_hd_sync
      if sd_fn in mfdd:
         hd_frame_data[hd_fn]['dt'] = mfdd[sd_fn]['dt']
         hd_frame_data[hd_fn]['sd_x'] = mfdd[sd_fn]['sd_x']
         hd_frame_data[hd_fn]['sd_y'] = mfdd[sd_fn]['sd_y']
         # respect the user mods over the auto points here.
         if sd_fn in user_mods:
            hd_frame_data[hd_fn]['hd_lx'] = user_mods[sd_fn][0]
            hd_frame_data[hd_fn]['hd_ly'] = user_mods[sd_fn][1]
            print("USER MOD FOUND!", sd_fn, hd_fn)
            xxx = input('xxx')

      hd_frame = hd_color_frames[hd_fn]
      sd_fn = hd_fn + sd_hd_sync
      if sd_fn < len(sd_color_frames):
         sd_frame = sd_color_frames[sd_fn]
      #cv2.imshow('hd', hd_frame)
      #cv2.imshow('sd', sd_frame)
      final_hd_frames.append(hd_frame)
      print(hd_frame_data[hd_fn])
   hd_frame_data = update_dists(hd_frame_data)
   hd_frame_data = update_times(hd_frame_data)

   # HD DATA is now SYNC'd with SD and updated 
   # NOW DO QUALITY CHECKS ON THE POINTS
   segs = []
   xds = []
   yds = []
   dfls = []
   for hd_fn in hd_frame_data: 
      if "x_dist" in hd_frame_data[hd_fn]:
         if hd_frame_data[hd_fn]['x_dist'] != 0:
            segs.append(hd_frame_data[hd_fn]['seg_dist'])
            xds.append(hd_frame_data[hd_fn]['x_dist'])
            yds.append(hd_frame_data[hd_fn]['y_dist'])
            dfls.append(hd_frame_data[hd_fn]['dist_from_last'])
      print("\n\nFINAL:", hd_frame_data[hd_fn])
   med_xd = np.median(xds)
   med_yd = np.median(yds)
   med_seg = np.median(segs)
   med_dfl = np.median(dfls)
   fnc = 0

   # DETERMINE EST X,Y if the POINT LOOKS BAD
   for hd_fn in hd_frame_data: 
      if "seg_dist" in hd_frame_data[hd_fn] and fnc > 1:
         seg_err = abs(hd_frame_data[hd_fn]['seg_dist'] - med_seg)
         dfl_err = abs(1 - abs(hd_frame_data[hd_fn]['dist_from_last'] / med_dfl))
         print("DFL ERR:", med_dfl, hd_frame_data[hd_fn]['dist_from_last'], dfl_err)
         if dfl_err > .5:
         #if False:
            print("POINT NEED HELP:", fnc, hd_frame_data[hd_fn])
            #est_x = hd_frame_data[hd_fn]['hd_lx']
            #est_y = hd_frame_data[hd_fn]['hd_ly']
            est_x = int(last_lx - med_xd)
            est_y = int(last_ly - med_yd)
            print("EST Y:", last_y, med_yd, est_y)
            hd_frame_data[hd_fn]['est_x'] = est_x
            hd_frame_data[hd_fn]['est_y'] = est_y
            print("LAST/NEW POINT:", hd_fn, last_x, last_y, est_x, est_y)
         else:
            print("POINT IS GOOD:", fnc, hd_frame_data[hd_fn])
      fnc += 1
      last_lx = hd_frame_data[hd_fn]['hd_lx']
      last_ly = hd_frame_data[hd_fn]['hd_ly']

   # MAKE A STACK IMAGE OF THE HD FRAMES
   stack_image = stack_frames(final_hd_frames)
   fc = 0
   axs = []
   ays = []
   for hd_fn in hd_frame_data: 
     
      data = hd_frame_data[hd_fn]
      print("DATA:", data)
      lx = data['hd_lx']
      ly = data['hd_ly']
      axs.append(lx)
      ays.append(ly)
      if dom_dir == 'x':
         if fc % 2 == 0:
            lx2 = lx 
            ly2 = ly - 20
            if "est_x" in hd_frame_data[hd_fn]:
               hd_frame_data[hd_fn]['est_x2'] = hd_frame_data[hd_fn]['est_x'] 
               hd_frame_data[hd_fn]['est_y2'] = hd_frame_data[hd_fn]['est_y'] - 20
         else:
            lx2 = lx 
            ly2 = ly + 20
            if "est_x" in hd_frame_data[hd_fn]:
               hd_frame_data[hd_fn]['est_x2'] = hd_frame_data[hd_fn]['est_x'] 
               hd_frame_data[hd_fn]['est_y2'] = hd_frame_data[hd_fn]['est_y'] + 20
      if dom_dir == 'y':
         if fc % 2 == 0:
            lx2 = lx - 20
            ly2 = ly 
            if "est_x" in hd_frame_data[hd_fn]:
               hd_frame_data[hd_fn]['est_x2'] = hd_frame_data[hd_fn]['est_x'] - 20
               hd_frame_data[hd_fn]['est_y2'] = hd_frame_data[hd_fn]['est_y'] 
         else:
            lx2 = lx + 20
            ly2 = ly 
            if "est_x" in hd_frame_data[hd_fn]:
               hd_frame_data[hd_fn]['est_x2'] = hd_frame_data[hd_fn]['est_x'] + 20
               hd_frame_data[hd_fn]['est_y2'] = hd_frame_data[hd_fn]['est_y'] 

      

      if "est_x" in hd_frame_data[hd_fn]:
         print("CORRECT:", hd_fn)
         #cv2.line(stack_image, (hd_frame_data[hd_fn]['est_x'],hd_frame_data[hd_fn]['est_y']), (hd_frame_data[hd_fn]['est_x2'],hd_frame_data[hd_fn]['est_y2']), (155,155,155), 1)
         #cv2.line(stack_image, (lx,ly), (lx2,ly2), (0,0,0), 1)
         #cv2.putText(stack_image, str(fc),  (hd_frame_data[hd_fn]['est_x2'], hd_frame_data[hd_fn]['est_y2']), cv2.FONT_HERSHEY_SIMPLEX, .3, (255, 255, 255), 1)
         #cv2.putText(stack_image, str(fc),  (lx2, ly2), cv2.FONT_HERSHEY_SIMPLEX, .3, (200, 200, 200), 1)
      else:
         foo = 1
         #cv2.line(stack_image, (lx,ly), (lx2,ly2), (100,100,100), 1)
         #cv2.putText(stack_image, str(fc),  (lx2, ly2), cv2.FONT_HERSHEY_SIMPLEX, .3, (200, 200, 200), 1)
      fc += 1

   min_x = min(axs) - 25
   min_y = min(ays) - 25
   max_x = max(axs) + 25
   max_y = max(ays) + 25
   if min_x < 0:
      min_x = 0
   if min_y < 0:
      min_y = 0
   if max_y > 1079:
      max_y = 1079 
   if max_x > 1919:
      max_x = 1919 

   print("AX", axs)
   print("AY", axs)
   print("MIN", min_x,min_y,max_x,max_y)
   crop_w, crop_h = best_crop_size([min_x,max_x], [min_y,max_y], 1920,1080)
   print("CROP WH:", crop_w,crop_h)
   cent_x = int(np.mean(axs))
   cent_y = int(np.mean(ays))
   cx1 = int(cent_x - (crop_w/2))
   cy1 = int(cent_y - (crop_h/2))
   cx2 = int(cent_x + (crop_w/2))
   cy2 = int(cent_y + (crop_h/2))
   if cx1 < 0:
      cx1 = 0
      cx2 = crop_w
   if cy1 < 0:
      cy1 = 0
      cy2 = crop_h
   if cx2 > 1919:
      cx1 = 1919 - crop_w
      cx2 = 1919 
   if cy2 > 1079:
      cy1 = 1079 - crop_h
      cy2 = 1079

   hd_crop_info = [cx1,cy1,cx2,cy2]
   print("CROP SIZE:", crop_w, crop_h)
   print("CROP INFO:", hd_crop_info)
   roi_img = stack_image[min_y:max_y,min_x:max_x]
   crop_stack = stack_image[cy1:cy2,cx1:cx2]
   rh, rw = roi_img.shape[0:2]

   print("RW, RH:", rw, rh)

   if rh * 5 < 800 and rw * 5 < 1400:
      # 
      nw = int(rw) * 5
      nh = int(rh) * 5
      enl = 5
   elif rh * 4 < 800 and rw * 4 < 1400:
      nw = int(rw) * 4 
      nh = int(rh) * 4 
      enl = 4
   elif rh * 3 < 800 and rw * 3 < 1400:
      nw = int(rw) * 3 
      nh = int(rh) * 3 
      enl = 3
   elif rh * 2 < 800 and rw * 2 < 1400:
      nw = int(rw) * 2
      nh = int(rh) * 2 
      enl = 2
   else:
      print("ROI TOO BIG TO ENLARGE?????:", rw, rh, rw* 5, rh * 5)
      nw = int(rw)  
      nh = int(rh) 
      enl = 1

   if max_x < 1920 / 2:
      # ideal loc right side
      ideal_x = 1
      print("IDEAL X = RIGHT")
   else: 
      ideal_x = -1
      print("IDEAL X = LEFT")

   if max_y < 1080 / 2:
      ideal_y = 1
      print("IDEAL Y = BOTTOM")
      # ideal loc bottom side
   else: 
      ideal_y = -1
      print("IDEAL Y = TOP")
   print("DOM DIR:", dom_dir)
   if dom_dir == "x":
      # put it under or over depending on the ideal
      if ideal_x == -1:
         roi_tlx = int((min_x+max_x)/2) - int(nw / 2)
      else:
         roi_tlx = int((min_x+max_x)/2) - int(nw/2)
      if ideal_y == -1:
         roi_tly = min_y + (50 * ideal_y) - int(nh)
      else:
         roi_tly = max_y + (50 * ideal_y)
   else:
      # put it left or right depending on ideal 
      if ideal_x == -1:
         roi_tlx = min_x + (50 * ideal_x) - int(nw ) - 50
      else:
         roi_tlx = max_x + (50 * ideal_x)
      if ideal_y == -1:
         roi_tly = int((max_y + min_y/2) - int(nh / 2 ))
      else:
         roi_tly = int((max_y + min_y/2) - int(nh / 2 ))

   if roi_tlx + nw > 1919:
      roi_tlx = 1919 - nw - 100
   if roi_tly + nh > 1079:
      roi_tly = 1079 - nh - 100
   if roi_tlx < 0:
      roi_tlx = 100
   if roi_tly < 0 :
      roi_tly = 100

   roi_img_big = cv2.resize(roi_img, (nw, nh))
   show_image = stack_image.copy() 
   print("ROI SHAPE:", roi_img_big.shape)
   print("region SHAPE:", nh, nw )
   print("region SHAPE:", roi_tly, roi_tly+nh,roi_tlx, roi_tlx+nw )
   if roi_img_big.shape[0] < 800:
      show_image[roi_tly:roi_tly+nh,roi_tlx:roi_tlx+nw] = roi_img_big
   cv2.rectangle(show_image, (int(roi_tlx), int(roi_tly)), (int(roi_tlx+nw) , int(roi_tly+nh) ), (255, 255, 255), 1)
   cv2.rectangle(show_image, (int(min_x), int(min_y)), (int(max_x) , int(max_y) ), (255, 255, 255), 1)
   blend_image = cv2.addWeighted(show_image, .8, star_overlay, .2,0)
   if SHOW ==1 :
      cv2.imshow('pepe', blend_image)
      cv2.waitKey(120)

   hd_fns = sorted(hd_frame_data.keys())
   if min(hd_fns) < 5:
      frame_buffer = min(hd_fns) - 1
   else:
      frame_buffer = 5
   # SAVE THE HD FRAMES IN CACHE AND THEN MAKE A FINAL VIDEO WITH BUFF +/-5
   print("HDFNS:", hd_fns)
   ff = min(hd_fns) - frame_buffer 
   lf = max(hd_fns) + 5
   if ff < 0:
      ff = 0
   if lf >= len(hd_color_frames):
      lf = len(hd_color_frames)
   print("FF,LF", ff, lf)

   start_dt = hd_frame_data[min(hd_fns)]['dt']
   start_dt = start_dt.replace("-", "_")
   start_dt = start_dt.replace(" ", "_")
   start_dt = start_dt.replace(":", "_")
   if "." in start_dt:
      start_dt = start_dt.replace(".", "_")
   else:
      start_dt += "_000"

   final_file_key = start_dt + "_" + amsid + "_" + cam 
   year = final_file_key[0:4]
   cache_dir = "/mnt/ams2/CACHE/" + year + "/" + final_file_key + "/" 
   cache_dir_cnt = "/mnt/ams2/CACHE/" + year + "/" + final_file_key + "_cnt/" 
   cache_dir_crop = "/mnt/ams2/CACHE/" + year + "/" + final_file_key + "_crop/" 
   if cfe(cache_dir, 1) == 0:
      os.makedirs(cache_dir)
   if cfe(cache_dir_crop, 1) == 0:
      os.makedirs(cache_dir_crop)

   if user_mods is not None:
      print("USER MODS:", user_mods)
      xxx = input("USER MODS exist.")

   print("CROP INFO:", hd_crop_info)
   cx1,cy1,cx2,cy2 = hd_crop_info
   for i in range(ff, lf+1):
      if i >= len(hd_color_frames):
         continue 
      frame = hd_color_frames[i]
      ffn = "{:04d}".format(int(i))
      crop_img = frame[cy1:cy2,cx1:cx2]
      print("CROP IMG:", hd_crop_info, crop_img.shape)
      if i in hd_frame_data:
         # over ride with maual detect data here if it exists
         print("SD FN:", sd_fn, type(sd_fn))
         sd_fn = str(hd_frame_data[i]['sd_fn'])
         if sd_fn in user_mods:
            lx = user_mods[sd_fn][0]
            ly = user_mods[sd_fn][1]
            hd_frame_data[i]['hd_lx'] = lx
            hd_frame_data[i]['hd_ly'] = ly
            xxx = input("USING USER MODS HERE.")
            cv2.circle(hd_color_frames[i],(lx,ly), 4, (0,0,255), 1)
         else:
            lx = hd_frame_data[i]['hd_lx']
            ly = hd_frame_data[i]['hd_ly']
         roi_img = make_roi_img(hd_color_frames[i], lx, ly, 25)
      if cfe(cache_dir_crop + final_file_key + "_" + ffn + ".jpg") == 0:
         crop_file = cache_dir_crop + final_file_key + "_" + ffn + ".jpg"
         crop_file_lr = cache_dir_crop + final_file_key + "_" + ffn + "_lr.jpg"
         print(cache_dir_crop + final_file_key)
         cv2.imwrite(cache_dir_crop + final_file_key + "_" + ffn + ".jpg", crop_img)
         os.system("convert -quality 60 " + crop_file + " " + crop_file_lr)
         os.system("mv " + crop_file_lr + " " + crop_file)
         print("saving...", cache_dir + final_file_key + "_" + ffn + ".jpg")

      if cfe(cache_dir + final_file_key + "_" + ffn + ".jpg") == 0:
         cv2.imwrite(cache_dir + final_file_key + "_" + ffn + ".jpg", hd_color_frames[i])
         print("saving...", cache_dir + final_file_key + "_" + ffn + ".jpg")


      if SHOW == 1:
         cv2.imshow('pepe', hd_color_frames[i])
         cv2.waitKey(30)
  
   day = final_file_key[0:10]
   final_dir = "/mnt/ams2/meteors/" + day + "/final/"
   if cfe(final_dir, 1) == 0:
      os.makedirs(final_dir)
   if cfe(final_dir + final_file_key + ".mp4") == 0:
      cmd = "./FFF.py imgs_to_vid " + cache_dir + " " + final_file_key + " " + final_dir + final_file_key + ".mp4" + " 25 28" 
      print(cmd)
      os.system(cmd)

   # save final images
   cv2.imwrite(final_dir + final_file_key + "_crop.jpg", crop_stack)
   cv2.imwrite(final_dir + final_file_key + "_stacked.jpg", stack_image)

   fstack_c = final_dir + final_file_key + "_crop.jpg"
   fstack_c_lr = fstack_c.replace(".jpg", "_lr.jpg")

   fstack = final_dir + final_file_key + "_stacked.jpg"
   fstack_lr = fstack.replace(".jpg", "_lr.jpg")

   print("FS:", fstack_c, fstack_c_lr)

   os.system("convert -quality 60 " + fstack_c + " " + fstack_c_lr)
   print("CROP: mv " + fstack_c_lr + " " + fstack_c)
   os.system("mv " + fstack_c_lr + " " + fstack_c)

   os.system("convert -quality 60 " + fstack + " " + fstack_lr)
   print("STACK: mv " + fstack_lr + " " + fstack)
   os.system("mv " + fstack_lr + " " + fstack)

   # Need a thumb stack and also a crop video here still
   thumb_stack = cv2.resize(stack_image, (320,180))
   thumb_stack_file = final_dir + final_file_key + "_stacked-tn.jpg"
   cv2.imwrite(thumb_stack_file, thumb_stack)
   lf = thumb_stack_file.replace(".jpg", "-lr.jpg")
   os.system("convert -quality 60 " + thumb_stack_file + " " + lf)
   os.system("mv " + lf + " " + thumb_stack_file )

   #if cfe(final_dir + final_file_key + "_crop.mp4") == 0:
   if True:
      cmd = "./FFF.py imgs_to_vid " + cache_dir_crop + " " + final_file_key + " " + final_dir + final_file_key + "_crop.mp4" + " 25 28" 
      print(cmd)
      os.system(cmd)

   # lower BR on cache full frame files (we do it here after the ffmpeg make movie call to not mess up the movie
   ffs = glob.glob(cache_dir + "*.jpg")
   for f in ffs:
      lf = f.replace(".jpg", "-lr.jpg")
      os.system("convert -quality 60 " + f + " " + lf)
      os.system("mv " + lf + " " + f )
      print("mv " + lf + " " + f )

   hd_frame_data = apply_cal_hdf(final_file_key, hd_frame_data, mj['cp'], json_conf)  

   mj['hd_red'] = {}
   mj['hd_red']['hd_mfd'] = hd_frame_data
   mj['final_vid'] = final_dir + final_file_key + ".mp4"
   mj['hd_red']['crop_area'] = crop_area
   mj['hd_red']['enl'] = enl
   mj['hd_red']['status'] = 1
   
   mj['hd_red']['frame_buf'] = frame_buffer
   mj['hd_red']['hd_crop_info'] = hd_crop_info
   save_json_file(meteor_file, mj)

   print("Saved.", meteor_file)
   print("Saved.", final_dir + final_file_key + "_crop.jpg")

   final_json = make_final_json(mj, json_conf)
   print("FINAL JSON MADE:", final_json)

   final_json_file = final_dir + final_file_key + ".json"
   save_json_file(final_json_file, final_json)
   print("FINAL JSON SAVED:", final_json_file)

def sync_final_day(day, json_conf):
   ams_id = json_conf['site']['ams_id']
   year = day[0:4]
   clf_index = "/mnt/ams2/meteors/" + day + "/cloud_files.txt"

   cloud_dir = "/mnt/archive.allsky.tv/" + ams_id + "/METEORS/" + year + "/" + day + "/"
   if cfe(cloud_dir, 1) == 0:
      os.makedirs(cloud_dir)


   os.system("ls -l /mnt/archive.allsky.tv/" + ams_id + "/METEORS/" + year + "/" + day + "/* > "  + clf_index)
   cloud_files = {}
   fp = open(clf_index)
   for line in fp:
      line = line.replace("\n", "")
      el = line.split() 
      if len(el) >= 8:
         cfn,xxx = fn_dir(el[8])
         cloud_files[cfn] = el[4]

   local_index = "/mnt/ams2/meteors/" + day + "/local_files.txt"
   os.system("ls -l /mnt/ams2/meteors/" + day + "/final/* > "  + local_index)
   local_files = {}
   fp = open(local_index)
   for line in fp:
      line = line.replace("\n", "")
      el = line.split() 
      if len(el) >= 8:
         lfn,xxx = fn_dir(el[8])
         local_files[lfn] = el[4]

   cloud_adds = []
   cloud_dels = []

   for local_file in local_files :
      if local_file not in cloud_files:
         print("File is NOT sync'd!", local_file)
         cloud_adds.append(local_file)
      elif local_files[local_file] != cloud_files[local_file]:
         print("Sizes don't match need to update!")
         cloud_adds.append(local_file)
      else:
         print("File is sync'd!", local_file)

   for cloud_file in cloud_files :
      if cloud_file not in local_files:
         print("This cloud file is not in the local files dir. Should we delete it from the cloud?", cloud_file)

   mses = {}
   for lfile in cloud_adds:
      lfroot = lfile
      lfroot = lfroot.replace("_stacked", "") 
      lfroot = lfroot.replace("_crop", "") 
      lfroot = lfroot.replace("-tn", "") 
      lfroot = lfroot.replace(".json", "") 
      lfroot = lfroot.replace(".mp4", "") 
      lfroot = lfroot.replace(".jpg", "") 
      if lfroot not in mses:
         jsf = "/mnt/ams2/meteors/" + day + "/final/" + lfroot + ".json"
         if cfe(jsf) == 1:
            js = load_json_file(jsf)
         else:
            print("NO JS!", jsf)
            js = {}
         #if "multi_station_event" in js:
         if True:
            mses[lfroot] = 1
         else:
            mses[lfroot] = 0
      if mses[lfroot] == 1:
         cmd = "cp /mnt/ams2/meteors/" + day + "/final/" + lfile + " " + "/mnt/archive.allsky.tv/" + ams_id + "/METEORS/" + year + "/" + day + "/" + lfile
         os.system(cmd)
         print(cmd) 

   print(mses)
   exit()


   arc_dir = "/mnt/archive.allsky.tv/" + ams_id + "/METEORS/" + year + "/" + day + "/"
   arc_files = glob.glob(arc_dir + "*")
   afs = {}
   for af in arc_files:
      afn, adir = fn_dir(af)
      afs[afn] = 1

   final_dir = "/mnt/ams2/meteors/" + day + "/final/"
   jsons = glob.glob(final_dir + "*.json")
   for jsf in jsons:
      jfn,jdir = fn_dir(jsf)
      fn_root = jfn.replace(".json", "")
      mj = load_json_file(jsf)
      if "multi_station_event" in mj:
         if "stations" in mj['multi_station_event']:
            if len(mj['multi_station_event']['stations']) >= 2:
            # ms event we should sync these files
               ffs = glob.glob(jdir + "/" + fn_root + "*")
               for ff in ffs:
                  ffn,fdir = fn_dir(ff)
                  if ffn not in afs:
                     print("File not inside the arc dir, we should copy it.", ffn, afs)
                     cmd = "cp " + ff + " " + arc_dir
                     print(cmd)
                     os.system(cmd)
                  else:
                     print("File already in archive.", ffn)


def apply_cal_hdf(file, hd_frame_data, cp, json_conf):
   for fn in hd_frame_data:
      data = hd_frame_data[fn]
      x = data['hd_lx']
      y = data['hd_ly']
      tx, ty, ra ,dec , az, el = XYtoRADec(x,y,file,cp,json_conf)
      hd_frame_data[fn]['az'] = az
      hd_frame_data[fn]['el'] = el
      hd_frame_data[fn]['ra'] = ra
      hd_frame_data[fn]['dec'] = dec
   return(hd_frame_data)

def make_roi_img(image, x, y, size):
   rx1 = x - size
   ry1 = y - size
   rx2 = x + size
   ry2 = y + size
   extra_x1 = None
   extra_x2 = None
   extra_y1 = None
   extra_y2 = None

   if rx1 < 0:
      extra_x1 = rx1
      rx1 = 0
   if ry1 < 0:
      extra_y1 = ry1
      ry1 = 0
   if rx2 >= 1919:
      extra_x2 = rx2 - 1919
      rx2 = 1919
   if ry2 >= 1079:
      extra_y2 = ry2 - 1079
      ry2 = 1079
   cnt_img = image[ry1:ry2,rx1:rx2]
   if cnt_img.shape[0] != 50 or cnt_img.shape[1] != 50:
      blank = np.zeros((50,50,3),dtype=np.uint8)
      if ry1 < 1080/2:
         print("CASE1")
         sy1 = 50 - cnt_img.shape[0]
         sy2 = 50
      else:
         print("CASE2")
         sy1 = 0
         #sy2 = 50 - cnt_img.shape[0]
         sy2 = cnt_img.shape[0]
      if rx1 < 1920/2:
         print("CASE3")
         sx1 = 50 - cnt_img.shape[1]
         sx2 = 50
      else:
         print("CASE4")
         sx1 = 0 
         sx2 = cnt_img.shape[1]
      print("AREA:", sy1,sy2,sx1,sx2)
      blank[sy1:sy2,sx1:sx2] = cnt_img 
      cnt_img = blank
   print(rx1,ry1,rx2,ry2)
   print(cnt_img.shape)
   return(1)



def update_times(hd_frame_data):

   fnc = 0
   first_time = None
   for hd_fn in hd_frame_data:
      if 'dt' in hd_frame_data[hd_fn] and first_time is None:
         first_time = [fnc, hd_frame_data[hd_fn]['sd_fn'], hd_frame_data[hd_fn]['dt']]
      fnc += 1
   first_frt, sd_fn, dt = first_time
   if "." in dt:
      first_dt = datetime.datetime.strptime(dt, "%Y-%m-%d %H:%M:%S.%f")
   else:
      first_dt = datetime.datetime.strptime(dt, "%Y-%m-%d %H:%M:%S.%f")
   print("FDT:", first_dt)
   neg_sec = (first_frt/ 25) * - 1
   clip_start_time = first_dt + datetime.timedelta(0,neg_sec)
   fnc = 0
   for hd_fn in hd_frame_data:
      extra_sec = fnc / 25
      fdt = clip_start_time + datetime.timedelta(0,extra_sec)
      fnc += 1
      hd_frame_data[hd_fn]['dt'] = fdt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
      print(fdt, hd_frame_data[hd_fn])
   return(hd_frame_data)

def update_dists(hd_frame_data):
   # recalc dist
   fx = None
   hd_mfd_dict = {}
   last_dist_from_start = None
   if True:
       for hd_fn in hd_frame_data:
         i = hd_fn
         data = hd_frame_data[hd_fn]
         if fx is None and "hd_lx" in data:
            fx = data['hd_lx']
            fy = data['hd_ly']
            dist_from_start = 0
            hd_frame_data[i]['dist_from_start'] = dist_from_start
            hd_frame_data[i]['seg_dist'] = 0
            hd_frame_data[i]['dist_from_last'] = 0
         else:
            if "hd_lx" in data:
               if last_x is not None:

                  dist_from_last = calc_dist((last_x,last_y), (data['hd_lx'],data['hd_ly']))
                  hd_frame_data[i]['x_dist'] = last_x - data['hd_lx']
                  hd_frame_data[i]['y_dist'] = last_y - data['hd_ly']
               else:
                  dist_from_last = 0
                  hd_frame_data[i]['x_dist'] = 0
                  hd_frame_data[i]['y_dist'] = 0
               dist_from_start = calc_dist((fx,fy),(data['hd_lx'],data['hd_ly']))
               if last_dist_from_start is not None:
                  seg_dist = dist_from_start - last_dist_from_start
                  hd_frame_data[i]['seg_dist'] = seg_dist
               else:
                  hd_frame_data[i]['seg_dist'] = 0
               hd_frame_data[i]['dist_from_last'] = dist_from_last
               hd_frame_data[i]['dist_from_start'] = dist_from_start
               last_dist_from_start = dist_from_start
            else:
               print("MISSING FRAME DATA!")
               missing += 1
         if "hd_lx" in data:
            last_x = data['hd_lx']
            last_y = data['hd_ly']



         hd_mfd_dict[i] = hd_frame_data[i]
         print("DISTS:", hd_frame_data[i])

   hd_frame_data = hd_mfd_dict



   return(hd_frame_data)

def sync_hd_sd_frames(mfd, hd_frame_data):
   print("******** SYNC")
   print("SD DATA:")
   diffs = []
   for data in mfd:
      (dt, sd_fn, sd_x, sd_y, w, h, oint, ra, dec, az, el) = data
      best_fn = 0
      best_dist = 9999
      for hd_fn in hd_frame_data:
         dist = calc_dist((sd_x, sd_y), (hd_frame_data[hd_fn]['hd_lx'],hd_frame_data[hd_fn]['hd_ly']))
         if dist < best_dist:
            best_fn = hd_fn
            best_dist = dist
         print(hd_frame_data[hd_fn])
      print("SD HD DIFF:", sd_fn - best_fn)
      diffs.append(sd_fn - best_fn)

   if len(diffs) > 2:
      med_diff = int(np.median(diffs))
   else:
      med_diff = int(np.mean(diffs))

   print("MED FRAME DIFF (sd-hd) = ",  med_diff)


   for hd_fn in hd_frame_data:
      print(hd_frame_data[hd_fn])
   return(med_diff)
   
def track_obj(objects, in_fn,in_x, in_y):
   fn_lim = 5
   dist_thresh = 40
   # no objects make 1st one
   if len(objects) == 0:
      obj_id = 1
      objects[obj_id] = {}
      objects[obj_id]['obj_id'] = 1
      objects[obj_id]['ofns'] = []
      objects[obj_id]['oxs'] = []
      objects[obj_id]['oys'] = []
      objects[obj_id]['ows'] = []
      objects[obj_id]['ohs'] = []
      objects[obj_id]['oint'] = []
      objects[obj_id]['ofns'].append(in_fn)
      objects[obj_id]['oxs'].append(in_x)
      objects[obj_id]['oys'].append(in_y)
      objects[obj_id]['ows'].append(5)
      objects[obj_id]['ohs'].append(5)
      objects[obj_id]['oint'].append(999)
      return(obj_id, objects)

   # see if we already have obj
   found = 0
   close_objs = []
   for obj_id in objects:
      dist = calc_dist((in_x,in_y),(objects[obj_id]['oxs'][-1],objects[obj_id]['oys'][-1]))
      fn_diff = in_fn - objects[obj_id]['ofns'][-1]
      print("OBJ:", in_fn, obj_id, dist)
      if dist < dist_thresh and fn_diff < 5:
         close_objs.append((obj_id, dist, fn_diff))

   if len(close_objs) > 0 :
      close_objs = sorted(close_objs, key=lambda x: (x[1]), reverse=False)
      print("CLOSE OBJS:", close_objs)
      obj_id = close_objs[0][0]
      objects[obj_id]['ofns'].append(in_fn)
      objects[obj_id]['oxs'].append(in_x)
      objects[obj_id]['oys'].append(in_y)
      objects[obj_id]['oint'].append(999)
      objects[obj_id]['ows'].append(5)
      objects[obj_id]['ohs'].append(5)
      return (obj_id, objects)

   # not found so make new
   obj_id = max(objects.keys()) + 1
   if True:
      objects[obj_id] = {}
      objects[obj_id]['obj_id'] = obj_id
      objects[obj_id]['ofns'] = []
      objects[obj_id]['oxs'] = []
      objects[obj_id]['oys'] = []
      objects[obj_id]['oint'] = []
      objects[obj_id]['ows'] = []
      objects[obj_id]['ohs'] = []
      objects[obj_id]['ofns'].append(in_fn)
      objects[obj_id]['oxs'].append(in_x)
      objects[obj_id]['oys'].append(in_y)
      objects[obj_id]['oint'].append(999)
      objects[obj_id]['ows'].append(5)
      objects[obj_id]['ohs'].append(5)
      return(obj_id, objects)


         




def fill_missing_frames(hd_frame_data):
   bad_frames = []
   xds = []
   yds = []
   for fn in hd_frame_data:
      data = hd_frame_data[fn]
      if "hd_lx" not in data:
         bad_frames.append(fn)
      else:
         if "x_dist" in data:
            xds.append(data['x_dist'])
            yds.append(data['y_dist'])

   med_x = np.median(xds)
   med_y = np.median(yds)

   for i in range(0, len(bad_frames)):
      bad_fn = bad_frames[i]
      if bad_fn - 1 in hd_frame_data:
         if 'hd_lx' in hd_frame_data[bad_fn - 1]:
            fix_x = int(hd_frame_data[bad_fn-1]['hd_lx'] - med_x)
            fix_y = int(hd_frame_data[bad_fn-1]['hd_ly'] - med_y)
            print("FIX FRAME:", bad_frames[i], med_x, med_y , fix_x, fix_y)
            hd_frame_data[bad_fn]['hd_lx'] = fix_x
            hd_frame_data[bad_fn]['hd_ly'] = fix_y

   # recalc dist
   fx = None
   hd_mfd_dict = {}
   last_dist_from_start = None
   if True:
       for hd_fn in hd_frame_data:
         i = hd_fn
         data = hd_frame_data[hd_fn]
         if fx is None and "hd_lx" in data:
            fx = data['hd_lx']
            fy = data['hd_ly']
            dist_from_start = 0
            hd_frame_data[i]['dist_from_start'] = dist_from_start
         else:
            if "hd_lx" in data:
               if last_x is not None:

                  dist_from_last = calc_dist((last_x,last_y), (data['hd_lx'],data['hd_ly']))
                  hd_frame_data[i]['x_dist'] = last_x - data['hd_lx']
                  hd_frame_data[i]['y_dist'] = last_y - data['hd_ly']
               else:
                  dist_from_last = 0
                  hd_frame_data[i]['x_dist'] = 0
                  hd_frame_data[i]['y_dist'] = 0
               dist_from_start = calc_dist((fx,fy),(data['hd_lx'],data['hd_ly']))
               if last_dist_from_start is not None:
                  seg_dist = dist_from_start - last_dist_from_start
                  hd_frame_data[i]['seg_dist'] = seg_dist
               else:
                  hd_frame_data[i]['seg_dist'] = 0
               hd_frame_data[i]['dist_from_last'] = dist_from_last
               hd_frame_data[i]['dist_from_start'] = dist_from_start
               last_dist_from_start = dist_from_start
            else:
               print("MISSING FRAME DATA!")
               missing += 1
         if "hd_lx" in data:
            last_x = data['hd_lx']
            last_y = data['hd_ly']



         hd_mfd_dict[i] = hd_frame_data[i]
         print("DISTS:", hd_frame_data[i])

   hd_frame_data = hd_mfd_dict

   return(hd_frame_data)

def get_lead_contour_in_image(frame, dom_dir,x_dir,y_dir,min_x=0,min_y=0,seg_len=None,last_x=None,last_y=None):
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
      print("CNT W/H:", w, h)
      if w > 1 and h > 1:
         cont.append((x+min_x,y+min_y,w,h))

   n_cont = []
   best_cnt = None
   best_x = None
   best_y = None
   best_dist = None
   this_dist = None
   print("CNTS:", cont)
   print("DOM:", dom_dir, x_dir, y_dir)
   if len(cont) > 0:
      for x,y,w,h in cont:
         if last_x is not None:
            print("THIS DIST:", (x+min_x,y+min_y),(last_x+min_x,last_y+min_y))
            this_dist = calc_dist((x+min_x,y+min_y),(last_x+min_x,last_y+min_y))
            print("******   CNT DIST EVAL:", seg_len, this_dist, abs(this_dist - seg_len))

         if best_cnt is None:
            if x_dir == "left_to_right" : # high x best
               best_x = x 
               best_w = w
               lx = x + w
            else:
               best_x = x 
               best_w = w
               lx = x 
            if y_dir == "up_to_down" : # high y best
               best_y = y 
               best_h = h
               ly = y + h
            else:
               best_y = y
               best_h = h
               ly = y 
            best_cnt = [x,y,w,h,lx,ly]
            best_dist = this_dist  
         else:
            if x_dir == "left_to_right" : # high x best
               if x + w > best_x + best_w: 
                  best_x = x 
                  best_w = w
                  lx = x + w
               elif x > best_x : 
                  best_x = x 
                  best_w = w
                  lx = x 
            else:
               if x < best_x:
                  best_x = x
                  best_w = w
                  lx = x

            if y_dir == 'up_to_down': # high is best
               if y + h > best_y + best_h: 
                  best_y = y 
                  best_h = h 
                  ly = y + h
               elif y < best_y  : 
                  best_y = y 
                  best_h = h 
                  ly = y 
            else:
               if y < best_y  : 
                  best_y = y 
                  best_h = h 
                  ly = y 
            print("BEST DIST THIS DIST:", best_dist, this_dist)
            if best_dist is not None :
               if this_dist < best_dist:
                  best_cnt = [best_x,best_y,best_w,best_h,lx,ly]

   for x,y,w,h in cont:
      print("CNT:", x,y,w,h)
      cv2.rectangle(frame, (int(x-min_x), int(y-min_y)), (int(x+w-min_x) , int(y+h-min_y) ), (255, 255, 255), 1)

   xs = []
   ys = []
   if len(cont) > 4:
      for x,y,w,h in cont:
         xs.append(x)
         ys.append(y)
         xs.append(x+w)
         ys.append(y+h)
      mx = int(np.mean(xs))
      my = int(np.mean(ys))
      mw = max(xs) - min(xs) 
      mh = max(ys) - min(ys) 
      best_cnt = [mx,my,mw,mh,mx,my]
      print("USING MEAN CNT!")


   if False:
      if best_cnt is not None:
         [x,y,w,h,lx,ly] = best_cnt
         cv2.circle(frame,(lx-min_x,ly-min_y), 4, (0,0,255), 1)
         cv2.imshow('pepe', frame)
         cv2.waitKey(30)
      else:
         print("NO CNTS!")
         cv2.imshow('pepe', frame)
         cv2.waitKey(30)
      
   if best_cnt is not None:
      print("BEST:", best_cnt)
      cont = [best_cnt]
   return(cont)

