import sqlite3
from datetime import datetime
import numpy as np
import cv2
import json
import datetime as dt
import os
from lib.PipeUtil import load_json_file, convert_filename_to_date_cam, get_trim_num, mfd_roi, save_json_file, bound_cnt
import sys
import glob

class AIWeather():

   def __init__(self):
      print("ASAI DB")
      self.home_dir = "/home/ams/amscams/"
      self.datasets_root = "/mnt/ams2/datasets/"

      self.today = datetime.now().strftime("%Y_%m_%d")

      self.json_conf = load_json_file("../conf/as6.json")
      self.station_id = self.json_conf['site']['ams_id']
      self.db_file = self.home_dir + "pipeline/" + self.station_id + "_WEATHER_SAMPLES.db"
      if os.path.exists(self.db_file ) is False:
         print("NO DB! make it first.", self.db_file)
         exit()

      self.con = self.connect_database()
      self.cur = self.con.cursor()

   def ephem_info(device_lat, device_lng, capture_date):

      obs = ephem.Observer()

      obs.pressure = 0
      obs.horizon = '-0:34'
      obs.lat = device_lat
      obs.lon = device_lng
      obs.date = capture_date
   
      sun = ephem.Sun()
      moon = ephem.Moon()

      sun_rise = obs.previous_rising(sun)
      sun_set = obs.next_setting(moon)
      moon_rise = obs.previous_rising(sun)
      moon_set = obs.next_setting(moon)
      sun.compute(obs)
      moon.compute(obs)

      (sun_alt, x,y) = str(sun.alt).split(":")
      (moon_alt, x,y) = str(moon.alt).split(":")

      saz = str(sun.az)
      moon_az = str(moon.az)
      (sun_az, x,y) = saz.split(":")
      (moon_az, x,y) = moon_az.split(":")
      if int(sun_alt) < -1:
         sun_status = "night"
      else:
         sun_status = "day"

      return(sun_status, sun_az, sun_alt, sun_rise, sun_set, moon_az, moon_alt, moon_rise, moon_set)


   def connect_database(self):
      con = sqlite3.connect(self.db_file)
      con.row_factory = sqlite3.Row
      return(con)

   def reindex_weather_samples(self):
      sql = "SELECT filename from ml_weather_samples order by filename desc"
      self.cur.execute(sql)
      rows = self.cur.fetchall()
      self.cur_index = {}
      for row in rows:
         root_file = row[0]
         self.cur_index[root_file] = {}

   def load_file(self, file):
      print("YO")
      # check the sun info (day/night, az,el)    
      # check the moon info (day/night, az,el)    
      # check the weather forecast (day/night, az,el)    
      # check the AI Condition 

   def day_night_scan(self):
      wdir = self.datasets_root + "weather_conditions/"
      labels = os.listdir(wdir) 
      for lab in sorted(labels):
         ldir = wdir + lab
         files = sorted(os.listdir(ldir))
         print(ldir, len(files))


   def load_forecast_history(self, file):
      if self.day_dict is None:
         self.day_dict = {}

      json_files = glob.glob(day_dir + "*.json")
      img_files = glob.glob(day_dir + "*.jpg")
      for jf in json_files:
         img_fn = jf.split("/")[-1]
         try:
            year, month, day, hour, minute = img_fn.split("_")
         except:
            continue
         minute = minute.replace(".json", "")
         f_date_str = str(year) + "-" + str(month) + "-" + str(day) + " " + str(hour) + ":" + str(minute)
         hkey = str(year) + "_" + str(month) + "_" + str(day) + "_" + str(hour) + "_" + str(minute)

         if hkey not in self.day_dict:
            self.day_dict[hkey] = {}
            for cam_id in cam_ids:
               self.day_dict[hkey][cam_id] = ""

         sun_status, sun_az, sun_el = day_or_night(f_date_str, json_conf,1)
         self.day_dict[hkey]['sun_status'] = sun_status


         try:
            self.day_dict[hkey]['weather'] = load_json_file(jf)
         except:
            self.day_dict[hkey]['weather'] = ""
