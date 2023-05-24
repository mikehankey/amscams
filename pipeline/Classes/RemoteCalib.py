import requests
import os
import scipy.optimize
import numpy as np
import datetime
import cv2
from pathlib import Path
from DynaDB import search_events, insert_meteor_event, delete_event, get_obs, update_dyna_table, delete_obs

from lib.PipeAutoCal import gen_cal_hist,update_center_radec, pair_stars, scan_for_stars, calc_dist, minimize_fov, AzEltoRADec , HMS2deg, distort_xy , XYtoRADec, angularSeparation, use_default_cal, convert_filename_to_date_cam
from recal import get_catalog_stars, get_star_points
from lib.PipeUtil import load_json_file, save_json_file, cfe
from lib.PipeVideo import load_frames_simple
#from Classes.Camera import Camera

class RemoteCalib():
   # class for calibrating remote stations and meteors 
   def __init__(self, station_id=None, cam_num=None,cam_id=None,datestr=None,meteor_file=None,cal_file=None):
      self.data_dir = "/mnt/f/"
      self.cloud_dir = "/mnt/archive.allsky.tv/"
      if meteor_file is None:
         self.mode = "calib"
         self.cal_file = cal_file 
      else:
         self.mode = "meteor"
         self.meteor_file = meteor_file
         if "AMS" in meteor_file:
            self.station_id = meteor_file.split("_")[0]
            self.vid_file = meteor_file.replace(self.station_id + "_", "")

            (f_datetime, cam_id, f_date_str,fy,fmon,fd, fh, fm, fs) = convert_filename_to_date_cam(self.vid_file)
            self.cloud_meteor_file = self.cloud_dir + self.station_id + "/METEORS/" + fy + "/" + f_date_str[0:10].replace("-", "_") + "/" + self.meteor_file.replace(".mp4",  "-360p.mp4")
            self.year = fy
            self.month = fmon
            self.dom = fd 
         self.datetime = f_datetime
         self.datestr = f_date_str.replace("-", "_")
         self.cam_id = cam_id 
      if station_id is not None:
         self.station_id = station_id
      if cam_num is not None:
         self.cam_num = cam_num 
      if cam_id is not None:
         self.cam_id = cam_id 
      if datestr is not None:
         self.datestr = self.datestr
      if meteor_file is not None:
         self.meteor_file = meteor_file 
      if cal_file is not None:
         self.cal_file = cal_file 
      if os.path.exists("hosts.json"):
         self.hosts = load_json_file("hosts.json")
      if self.station_id in self.hosts:
         if self.hosts[self.station_id] != "":
            self.host = self.hosts[self.station_id]['hostname']
         elif self.hosts[self.station_id]['vpn_ip'] != "":
            self.host = self.hosts[self.station_id]['vpn_ip']
         else:
            self.host = "offline"
      # local cache
      self.local_event_dir = self.data_dir + "EVENTS/" + self.year + "/" + self.month + "/" + self.dom + "/" 
      self.obs_dict_file = self.local_event_dir + self.datestr[0:10] + "_OBS_DICT.json"
      self.obs_dict = load_json_file(self.obs_dict_file)
      self.local_cal_dir = self.data_dir + "EVENTS/STATIONS/" + self.station_id + "/CAL/"
      self.local_mask_dir = self.data_dir + "EVENTS/STATIONS/" + self.station_id + "/CAL/MASKS/"
      self.mcp_file = self.local_cal_dir + "multi_poly-" + self.station_id + "-" + self.cam_id + ".info"
      self.as6_file = self.local_cal_dir + "as6.json"
      if os.path.exists(self.as6_file) is True:
         self.json_conf = load_json_file(self.as6_file)
      if os.path.exists(self.mcp_file) is True:
         self.cal_params = load_json_file(self.mcp_file)
         self.cal_params = update_center_radec(self.vid_file,self.cal_params,self.json_conf)


      if self.mode == "meteor":
         self.local_cal_img = self.local_cal_dir + "/IMAGES/" + self.meteor_file.replace(".mp4", "-med.jpg")
         self.local_meteor_file = self.local_cal_dir + "/IMAGES/" + self.meteor_file
         self.host_meteor_file = self.host + "/meteors/" + self.datestr + "/" + self.vid_file 
      if self.meteor_file in self.obs_dict:
         temp_cp = self.obs_dict[self.meteor_file]['calib']
         self.ra_center, self.dec_center, self.center_az, self.center_el, self.position_angle, self.pixscale, self.stars, self.total_res_px = temp_cp
         self.cal_params['ra_center'] = self.ra_center
         self.cal_params['dec_center'] = self.dec_center
         self.cal_params['center_az'] = self.center_az
         self.cal_params['center_el'] = self.center_el
         self.cal_params['position_angle'] = self.position_angle
         self.cal_params['pixscale'] = self.pixscale
         self.cal_params['stars'] = self.stars
         self.cal_params['total_res_px'] = self.total_res_px
         print("TEMP:", temp_cp)


   def remote_meteor_cal(self):
      # figure out the calib, lens model, available stars, refit if needed, re-apply points if needed
      # first find the meteor file / data
      # fetch the obs from api?
      if os.path.exists(self.local_cal_dir) is False:
         os.makedirs(self.local_cal_dir)
      local_cal_files = os.listdir(self.local_cal_dir)
      if True:
         cmd = """rsync -auv --exclude "PLOTS/" --exclude "plots/" """ + self.cloud_dir + self.station_id + "/CAL/* " + self.local_cal_dir + "/" 
         print(cmd)
         os.system(cmd)
         # need everything 
         # as6 conf

      # get image 


      print(self.cal_params)
      print(self.local_meteor_file)
      print(self.cloud_meteor_file)
      print(self.host_meteor_file)
      if os.path.exists(self.local_meteor_file) is False:
         if os.path.exists(self.cloud_meteor_file) is True:
            os.system("cp " + self.cloud_meteor_file + " " + self.local_meteor_file)
      frames = load_frames_simple(self.local_meteor_file)
      #for fr in frames:
      #   cv2.imshow('pepe', fr)
      #   cv2.waitKey(30) 
      median_frame = cv2.convertScaleAbs(np.median(np.array(frames), axis=0))
      self.median_frame = cv2.resize(median_frame, (1920,1080))
      cv2.imshow('pepe', self.median_frame)
      cv2.waitKey(30) 

      star_points, show_img = get_star_points(self.vid_file, self.median_frame, self.cal_params, self.station_id, self.cam_id, self.json_conf)
      for row in star_points:
         sx,sy,i = row
         cv2.circle(self.median_frame, (sx,sy), 10, (128,128,128),1)

      cat_stars, short_bright_stars, cat_image = get_catalog_stars(self.cal_params)
      for row in cat_stars:
         (name,mag,ra,dec,new_cat_x,new_cat_y,zp_cat_x,zp_cat_y) = row
         cv2.line(self.median_frame, (int(zp_cat_x),int(zp_cat_y)), (int(new_cat_x),int(new_cat_y)), (0,0,0), 10)
      cv2.imshow('pepe', self.median_frame)
      cv2.waitKey(0) 



