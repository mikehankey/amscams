import os
import scipy.optimize
import numpy as np
import datetime
import cv2
from pathlib import Path
import glob


from lib.PipeAutoCal import gen_cal_hist,update_center_radec, get_catalog_stars, pair_stars, scan_for_stars, calc_dist, minimize_fov, AzEltoRADec , HMS2deg, distort_xy , XYtoRADec, angularSeparation, use_default_cal
from lib.PipeUtil import load_json_file, save_json_file, cfe
from Classes.Camera import Camera

class CleanCal():
   def __init__(self, station_id):
      print("Clean Cal.")
      json_conf = load_json_file("../conf/as6.json")
      self.station_id = json_conf['site']['ams_id']
      self.lat = json_conf['site']['device_lat']
      self.lon = json_conf['site']['device_lng']
      self.alt = json_conf['site']['device_alt']
      self.fc_files = []
      self.fc_index = []
      self.bad_fc_files = []
      self.best_fc_files = []

   def load_freecal_files(self):
      fc_dirs = glob.glob("/mnt/ams2/cal/freecal/*")
      for fcd in fc_dirs:
         cal_name = fcd.split("/")[-1]
         cal_file1 = fcd + "/" + cal_name + "-stacked-calparams.json"
         cal_file2 = fcd + "/" + cal_name + "-calparams.json"
         if cfe(cal_file1) == 1:
            print("FOUND:", cal_file1)
            self.fc_files.append(cal_file1)
         elif cfe(cal_file2) == 1:
            print("FOUND:", cal_file2)
            self.fc_files.append(cal_file2)
         else:
            print("NO CAL FILE FOUND MISSING:", cal_file2, cal_file2)

   def load_freecal_index(self):
      temp = load_json_file("/mnt/ams2/cal/freecal_index.json")
      for key in temp:
         data = temp[key]
         data['key'] = key
         if "total_res_px" in data:
            self.fc_index.append(data)
         else:
            print("PX MISSING?", data)
      self.fc_index = sorted(self.fc_index, key=lambda x: x['total_res_px'], reverse=False)      
      for data in self.fc_index:
         print(data['cam_id'], data['total_res_px'], data['key'])

   def inspect_cal(self, cal_file):
      cp = load_json_file(cal_file)
      img_file = cal_file.replace("-calparams.json", ".png")
      img = cv2.imread(img_file)
      cv2.imshow('pepe',img)
      cv2.waitKey(0)
      new_user_stars = []
      new_cat_image_stars = []
      for data in cp['cat_image_stars']:
         dcname,mag,ra,dec,img_ra,img_dec,match_dist,org_x,org_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int = data 
         ix = int(six)
         iy = int(siy)
         img[iy,ix] = [0,128,128]
         sx1 = ix-5 
         sy1 = iy-5 
         sx2 = ix+5 
         sy2 = iy+5 
         star_cnt = img[sy1:sy2,sx1:sx2]
         result = self.inspect_star(star_cnt, data);
         if result is not None:
            dcname,mag,ra,dec,img_ra,img_dec,match_dist,org_x,org_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int = result 
            ix = int(six)
            iy = int(siy)
            img[iy,ix] = [128,128,0]
            cv2.imshow('pepe',img)
            cv2.waitKey(0)
            print("NEW STAR X,Y:", six, siy, star_int)
            new_user_stars.append((six,siy,star_int))
            new_cat_image_stars.append((dcname,mag,ra,dec,img_ra,img_dec,match_dist,org_x,org_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int))
      cp['user_stars'] = new_user_stars
      cp['cat_image_stars'] = new_cat_image_stars 
      cp['inspected'] = 1
      save_json_file(cal_file, cp)
      print("Saved:", cal_file)

   def inspect_star(self, star_cnt, cat_star_data):
      orig_star_cnt = star_cnt.copy()
      dcname,mag,ra,dec,img_ra,img_dec,match_dist,org_x,org_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int = cat_star_data 
      gray_star = cv2.cvtColor(star_cnt, cv2.COLOR_BGR2GRAY)
      min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(gray_star)
      thresh_val = max_val *.8
      _, thresh_img = cv2.threshold(gray_star.copy(), thresh_val, 255, cv2.THRESH_BINARY)
      star_cnt[my,mx] = [0,0,128]
      star_cnt[4,4] = [0,128,0]
      cv2.imshow('star', star_cnt)
      cv2.imshow('thresh', thresh_img)
      cv2.waitKey(0)
      print(cat_star_data)
      cnts = self.get_contours_in_image(thresh_img)
      if len(cnts) == 1:
         x,y,w,h,cx,cy,adjx,adjy = cnts[0]
         six += adjx
         siy += adjy
         star_int = int(np.sum(star_cnt[y:y+h,x:x+w]))
         return(dcname,mag,ra,dec,img_ra,img_dec,match_dist,org_x,org_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int)
      else:
         return None
  
   def get_contours_in_image(self, frame ):
      ih, iw = frame.shape[:2]
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
         if w > 1 or h > 1:
            cx = x + (w / 2)
            cy = y + (h / 2)
            adjx = cx - (iw/2)
            adjy = cy - (ih/2)
            cont.append((x,y,w,h,cx,cy,adjx,adjy))
      return(cont)

