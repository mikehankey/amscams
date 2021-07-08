import os
import scipy.optimize
import numpy as np
import datetime
import cv2
from pathlib import Path
import glob

from lib.PipeAutoCal import gen_cal_hist,update_center_radec, get_catalog_stars, pair_stars, scan_for_stars, calc_dist, minimize_fov, AzEltoRADec , HMS2deg, distort_xy , XYtoRADec, angularSeparation, use_default_cal, minimize_poly_multi_star
from lib.PipeUtil import load_json_file, save_json_file, cfe
from Classes.Camera import Camera

class CloudCal():
   def __init__(self, station_id=None,cam_id=None, cal_file=None,meteor_file=None):
      self.station_id = station_id 
      self.cam_id = cam_id
      self.cal_file = cal_file
      self.meteor_file = meteor_file
      self.cloud_cal_dir = "/mnt/archive.allsky.tv/" + self.station_id + "/CAL/"
      self.cloud_cal_data_dir = "/mnt/archive.allsky.tv/" + self.station_id + "/CAL/DATA/"
      if cfe(self.cloud_cal_data_dir,1) == 0:
         os.makedirs(self.cloud_cal_data_dir)
      self.json_conf = load_json_file(self.cloud_cal_dir + "/as6.json")

      #(cal_file , center_az, center_el, ra_center, dec_center, position_angle, pixscale, dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int)

   def refit_fovs(self):

      cloud_cal_dir = "/mnt/archive.allsky.tv/" + self.station_id + "/CAL/SRC/CLOUD_CAL/" 
      temp = glob.glob(cloud_cal_dir + "*" + self.cam_id + "*")
      print(cloud_cal_dir + "*" + self.cam_id + "*")
      temp = ["/mnt/archive.allsky.tv/" + self.station_id + "/CAL/SRC/CLOUD_CAL/2021_07_04_04_52_13_000_011005"]
      for t in temp:
         cdir = t.split("/")[-1]
         cfile = cloud_cal_dir + cdir + "/" + cdir + "-stacked-calparams.json"
         ifile = cloud_cal_dir + cdir + "/" + cdir + ".jpg"

         if cfe(cfile) == 1:
            print("LOADING:", cfile)
            img = cv2.imread(ifile)
            #try:
            cal_params = load_json_file(cfile)
            cal_params_orig = load_json_file(cfile)
            #cal_params = update_center_radec(cfile,cal_params,self.json_conf)
            print("MINIMIZE FOV!", cfile)
            new_cal_params = minimize_fov(cfile, cal_params, cfile,img,self.json_conf )

            cal_params_orig['center_az'] = new_cal_params['center_az']
            cal_params_orig['center_el'] = new_cal_params['center_el']
            cal_params_orig['ra_center'] = new_cal_params['ra_center']
            cal_params_orig['dec_center'] = new_cal_params['dec_center']
            cal_params_orig['pixscale'] = new_cal_params['pixscale']
            cal_params_orig['position_angle'] = new_cal_params['position_angle']

            new_cfile = cfile.replace(".json", ".json.new")
            save_json_file(new_cfile, new_cal_params)
            save_json_file(cfile, cal_params_orig)
            print("SAVED", cfile, new_cfile)
            #except:
            #   print("ERROR LOADING!", cfile)
            #   continue

   def make_star_db(self):
      new_merged_stars = []
      cloud_cal_dir = "/mnt/archive.allsky.tv/" + self.station_id + "/CAL/SRC/CLOUD_CAL/" 
      temp = glob.glob(cloud_cal_dir + "*" + self.cam_id + "*")
      print(cloud_cal_dir + "*" + self.cam_id + "*")
      for t in temp:
         cdir = t.split("/")[-1]
         cfile = cloud_cal_dir + cdir + "/" + cdir + "-stacked-calparams.json"
         if cfe(cfile) == 1:
            print("LOADING:", cfile)
            try:
               cp = load_json_file(cfile)
               cp = update_center_radec(cfile,cp,self.json_conf)
            except:
               continue
            for star in cp['cat_image_stars']:
               dcname,mag,ra,dec,ra,dec,match_dist,new_cat_x,new_cat_y,ra,dec,new_cat_x,new_cat_y,six,siy,cat_dist,bp= star
               #name,mag,ra,dec,img_ra,img_dec,match_dist,new_cat_x,new_cat_y,ra,dec,new_cat_x,new_cat_y,six,siy,cat_dist,bp
               #dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,bp = star
               print("CAT IMG STARS STAR:", star)
               print("STARXYs:", six,siy,new_cat_x,new_cat_y)
               star_row = [cfile, cp['center_az'], cp['center_el'], cp['ra_center'], cp['dec_center'], cp['position_angle'], cp['pixscale'], dcname,mag,ra,dec,ra,dec,match_dist,new_cat_x,new_cat_y,ra,dec,new_cat_x,new_cat_y,six,siy,cat_dist,bp]
               print("AZ/EL RA/DEC SIXY/CATXY:", cp['center_az'], cp['center_el'], cp['ra_center'], cp['dec_center'], six,siy, new_cat_x, new_cat_y)
               new_merged_stars.append(star_row)
         else:
            print("NOT FOUND:", cfile)
      input("WAIT TO START")
      for star in new_merged_stars:
         print(star)
      save_json_file(self.cloud_cal_data_dir + self.cam_id + "_merged_stars.json", new_merged_stars)
      print(self.cloud_cal_data_dir + self.cam_id + "_merged_stars.json")

      mcp_file = self.cloud_cal_data_dir + "mcp_" + self.station_id + "_" + self.cam_id + ".json"
      if cfe(self.cloud_cal_data_dir + "mcp_" + self.station_id + "_" + self.cam_id + ".json") == 1:
         mcp = load_json_file(self.cloud_cal_data_dir + "mcp_" + self.station_id + "_" + self.cam_id + ".json")
         input("LOADED MCP! " + mcp_file)
      else:
         mcp = None
         input("COULD NOT LOADED MCP! " + mcp_file)


      status, cal_params, merged_stars  = minimize_poly_multi_star(new_merged_stars, self.json_conf,orig_ra_center=0,orig_dec_center=0,cam_id=self.cam_id,master_file=None,mcp=mcp,show=0)
      if status == 1:
         print("MULTI FIT SUCCESS!")
      print(self.cloud_cal_data_dir + "mcp_" + self.station_id + "_" + self.cam_id + ".json")
      if cal_params != 0:
         save_json_file(self.cloud_cal_data_dir + "mcp_" + self.station_id + "_" + self.cam_id + ".json", cal_params)
         save_json_file(self.cloud_cal_data_dir + "merged_stars_" + self.station_id + "_" + self.cam_id + ".json", merged_stars)
      print("SAVED:", self.cloud_cal_data_dir + "mcp_" + self.station_id + "_" + self.cam_id + ".json")
