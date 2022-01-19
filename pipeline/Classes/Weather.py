import sqlite3
from datetime import datetime as dt
import requests

from decimal import Decimal
import pickle
import glob
import json
import math
import os
import scipy.optimize
import numpy as np
import datetime
import cv2
from sklearn import linear_model, datasets
from skimage.measure import ransac, LineModelND, CircleModel

from sklearn.linear_model import RANSACRegressor
from sklearn.datasets import make_regression

from PIL import ImageFont, ImageDraw, Image, ImageChops

from Classes.DisplayFrame import DisplayFrame
from Classes.Detector import Detector
from Classes.Camera import Camera
from Classes.Event import Event
from Classes.Calibration import Calibration
from lib.PipeAutoCal import gen_cal_hist,update_center_radec, get_catalog_stars, pair_stars, scan_for_stars, calc_dist, minimize_fov, AzEltoRADec , HMS2deg, distort_xy, XYtoRADec, angularSeparation 
from lib.PipeUtil import load_json_file, save_json_file, cfe, ephem_info, get_moon_phase, get_localtime_offset
from lib.FFFuncs import best_crop_size, ffprobe
import boto3
import socket
import sys
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras.models import *
import tensorflow.keras
from tensorflow.keras.models import load_model
from tensorflow.keras.models import Sequential
from tensorflow.keras.preprocessing.image import ImageDataGenerator, array_to_img, img_to_array, load_img


class Weather():

   def __init__(self):
      self.show = 1
      self.weather_learning_dir = "/mnt/ams2/datasets/weather/"
      json_conf = load_json_file("../conf/as6.json")
      self.weather_condition_classes = sorted(load_json_file("weather_condition_classes.json"))


      self.station_id = json_conf['site']['ams_id']
      self.device_lat = json_conf['site']['device_lat']
      self.device_lng = json_conf['site']['device_lng']
      self.cams = []
      self.db_file = self.station_id + "_WEATHER.db" 
      if os.path.exists(self.db_file) is False:
         self.make_weather_db()

      self.con = sqlite3.connect(self.station_id + "_WEATHER.db")
      self.con.row_factory = sqlite3.Row 
      self.cur = self.con.cursor()

      for cam_num in json_conf['cameras']:
         cams_id = json_conf['cameras'][cam_num]['cams_id']
         self.cams.append(cams_id)

      self.weather_conditions_model_file = "weather_condition_model.h5"

      self.model = Sequential()

      self.model =load_model(self.weather_conditions_model_file)
      self.model.compile(loss='categorical_crossentropy',
         optimizer='rmsprop',
         metrics=['accuracy'])

   def weather_predict(self, img_file=None, img=None):
      img_height = 150
      img_width = 150
      if img_file is None:
         temp_file = "temp.jpg"
         cv2.imwrite(temp_file, img)
      else:
         img = cv2.imread(img_file)
         temp_file = "temp.jpg"

      img = load_img(
         temp_file, target_size=(img_height, img_width)
      )
      img_array = img_to_array(img)
      img_array = tf.expand_dims(img_array, 0) # Create a batch

      predictions = self.model.predict(img_array)

      score = tf.nn.softmax(predictions[0])
      predicted_class = self.weather_condition_classes[np.argmax(score)]
      print(
       "This image most likely belongs to {} with a {:.2f} percent confidence."
       .format(self.weather_condition_classes[np.argmax(score)], 100 * np.max(score))
      )
      return(predicted_class, 100 * np.max(score))
         #cv2.imwrite(img_file, img)

   def make_weather_db(self):
      ml_weather_snaps_table = """
        CREATE TABLE "ml_weather_snaps" (
        "filename"	TEXT,
	"station_id"	TEXT,
	"camera_id"	TEXT,
	"local_time"	TEXT,
	"time_offset"	REAL,
	"sun_status"	TEXT,
	"sun_az"	REAL,
	"sun_el"	REAL,
	"moon_status"	TEXT,
	"moon_az"	REAL,
	"moon_el"	REAL,
	"forecast"	TEXT,
	"actual"	TEXT,
	"ai_final"	TEXT,
	"samples_done"	INT,
	PRIMARY KEY("filename")
        );
      """

      ml_weather_samples_table = """
        CREATE TABLE "ml_weather_samples" (
        "filename"	TEXT,
	"station_id"	TEXT,
	"camera_id"	TEXT,
	"local_datetime_key"	TEXT,
	"ai_sky_condition"	TEXT,
	"ai_sky_condition_conf"	INTEGER,
	"ai_cloud_type"	TEXT,
	"ai_cloud_type_conf"	INTEGER,
	"ai_phenom"	TEXT,
	"ai_phenom_conf"	INTEGER,
	"ai_severe"	TEXT,
	"ai_severe_conf"	INTEGER,
	"hm_sky_condition"	TEXT,
	"hm_cloud_type"	TEXT,
	"hm_phenom"	TEXT,
	"hm_severe"	TEXT,
	"repo_sync_status"	TEXT,
	PRIMARY KEY("filename")
        );

      """

      ml_weather_conditions = """
      CREATE TABLE "weather_conditions" (
	"station_id"	TEXT,
	"local_datetime_key"	TEXT,
	"utc_time_offset"	REAL,
	"sun_status"	TEXT,
	"sun_az"	REAL,
	"sun_el"	REAL,
	"moon_status"	TEXT,
	"moon_az"	REAL,
	"moon_el"	REAL,
	"forecast"	TEXT,
	"actual"	TEXT,
	"ai_final"	TEXT,
	"samples_done"	INT,
	PRIMARY KEY("station_id","local_datetime_key")
      );

      CREATE TABLE "metar" (
	"raw_text"	TEXT,
	"station_id"	INTEGER,
	"observation_time"	TEXT,
	"latitude"	REAL,
	"longitude"	REAL,
	"elevation_m"	REAL,
	"temp_c"	REAL,
	"dewpoint_c"	REAL,
	"wind_dir_degrees"	REAL,
	"wind_spped_kt"	REAL,
	"wind_gust_kt"	REAL,
	"visibility_statute_mi"	REAL,
	"altim_in_hg"	REAL,
	"sea_level_pressure_mb"	REAL,
	"sky_conditions"	TEXT,
	"pcp3hr_in"	REAL,
	"precip_in"	REAL,
	"flight_category"	TEXT,
	PRIMARY KEY("raw_text")
      );

      """

      print("*** DB FILE DOESN'T EXIST:", self.db_file)
      cmd = "cat WEATHER.sql | sqlite3 " + self.db_file
      print(cmd)
      os.system(cmd)
      input("Continue...")

   def index_local_stacks(self):
      local_stack_dir = "/mnt/ams2/METEOR_ARCHIVE/" + self.station_id + "/STACKS/" 
      stack_hist_file = local_stack_dir + self.station_id + "_hour_stack_history.json"
      # day/night stack files
      dns_hist_file = local_stack_dir + self.station_id + "_day_night_stack_history.json"
      if cfe(stack_hist_file) == 1:
         sds = load_json_file(stack_hist_file)
      else:
         sds = {}
      if cfe(stack_hist_file) == 1:
         dns = load_json_file(dns_hist_file)
      else:
         dns = {}

      stack_dirs = glob.glob(local_stack_dir + "*") 
      dc = 0
      for sd in sorted(stack_dirs, reverse=True):
         if cfe(sd, 1) != 1:
            continue
         day = sd.split("/")[-1]
         if day in sds and dc > 3:
            print("This is already done.", day)
         else:
            sds[day] = {} 
            dns[day] = {} 
            sds[day]['hour_stack_files'] = []
            dns[day]['day_stacks'] = []
            dns[day]['night_stacks'] = []
            sfs = glob.glob(sd+ "/*.jpg")
            for sf in sfs:
               sfn = sf.split("/")[-1]
               sfn = sfn.replace(day + "_", "")
               sfn = sfn.replace(".jpg", "")
               if "night" in sfn:
                  dns[day]['night_stacks'].append(sfn)
               elif "day" in sfn:
                  dns[day]['day_stacks'].append(sfn)
               else :
                  sds[day]['hour_stack_files'].append(sfn)
            save_json_file(sd + "_hours.json", sds[day]['hour_stack_files'])
            dc += 1

      save_json_file(stack_hist_file, sds, True)
      save_json_file(dns_hist_file, dns, True)
      print(stack_hist_file)
      print(dns_hist_file)


   def process_weather_snap_all(self):
      sql = "SELECT filename from ml_weather_snaps where samples_done != 1"
      sql = "select A.filename, A.local_datetime_key, sun_status, moon_status, forecast, A.ai_final from ml_weather_snaps A INNER JOIN weather_conditions B on A.local_datetime_key = B.local_datetime_key where A.samples_done != 1";
      self.cur.execute(sql)
      rows = self.cur.fetchall()
      for row in rows:
         filename = row[0] 
         local_datetime = row[1] 
         sun_status = row[2] 
         self.process_weather_snap(filename, local_datetime, sun_status )
         #try:
         #except:
         #   print("FAILED:", filename)
         print("FILE:", filename)


   def process_weather_snap(self, snap_file, local_datetime_key, sun_status):
      # Here we will get the relevant meta data about the weather at this time
      # then we will cut the image into 6 sqaures/crops
      # then for each crop we will do weather_detect on it to get the class and confidence
      # then we will make the repo_label_dir which will be
      # {day_night_status}-{label} 
      # then save the weather square in the image folder


      print("SNAP:", snap_file)

      station_id, cam, year, month, day, hour, minute = snap_file.split("_")

      latest_dir = "/mnt/ams2/latest/" + year + "_" + month + "_" + day + "/"
      img_file = latest_dir + snap_file
      img = cv2.imread(img_file)
      lcc = 0
      marked_img = img.copy()
      sc = 0
      if img is not None:
         for row in range(0,2):
            for col in range(0,4):

               x1 = 180 * col
               x2 = x1 + 180
               y1 = row * 180
               y2 = y1 + 180
               if x2 > img.shape[1]:
                  x1 = img.shape[1] - 180
                  x2 = img.shape[1] 
               learning_img = img[y1:y2,x1:x2]

               #predict_class, predict_conf = predict_weather(self.mc_model, learning_img)
               predict_class, predict_conf = self.weather_predict(None, learning_img)
               el = predict_class.split("_")
               predict_name = el[0] 
               try:
                  ver = int(el[1]) 
               except:
                  predict_name += el[1] 
               if sc != 3 and sc != 7:
                  cv2.putText(marked_img, predict_name ,  (x1+11, y1+21), cv2.FONT_HERSHEY_SIMPLEX, .5, (0, 0, 0), 1) 
                  cv2.putText(marked_img, predict_name ,  (x1+10, y1+20), cv2.FONT_HERSHEY_SIMPLEX, .5, (150, 150, 150), 1) 
                  cv2.rectangle(marked_img, (x1, y1), (x2,y2), (128, 128, 128), 2)
               #print("PRED:", x1, y1, predict_class, predict_conf)

               learning_dir = self.weather_learning_dir + "/" + sun_status.upper() + "_" + predict_class + "/" 
               if os.path.exists(learning_dir) is False:
                  os.makedirs(learning_dir)
               learning_file = learning_dir + "/" + img_file.split("/")[-1].replace(".jpg", "-" + str(lcc) + ".jpg")
               #if os.path.exists(learning_file):
               #   continue


               if learning_img.shape[0] == learning_img.shape[1]:
                  cv2.imwrite(learning_file, learning_img)
                  print("Saved learning file:", x1,y1,x2,y2, row, col, learning_file)
                  learning_fn = learning_file.split("/")[-1]
                  try:
                     self.insert_ml_weather_sample(learning_fn, station_id, cam, local_datetime_key, predict_class, predict_conf)
                     print("INSERTED", img_file)
                  except:
                     print("INsert failed.")
                  lcc += 1
               sc += 1
         marked_file = img_file.replace(".jpg", "-marked.jpg")
         print("Saved:", marked_file)
         cv2.imwrite(marked_file, marked_img)
      else:
         print("FAIL:", img_file)


   def load_database(self):
      self.db_keys = {}
      self.db_keys_snaps = {}
      sql = "SELECT local_datetime_key from weather_conditions order by local_datetime_key desc"
      self.cur.execute(sql)
      rows = self.cur.fetchall()
      for row in rows:
         local_datetime_key = row[0] 
         self.db_keys[local_datetime_key] = {} 

      sql = "SELECT filename from ml_weather_snaps order by filename desc"
      self.cur.execute(sql)
      rows = self.cur.fetchall()
      for row in rows:
         filename = row[0] 
         self.db_keys_snaps[filename] = {} 


      ldir = "/mnt/ams2/latest/"
      days = os.listdir(ldir)

      for day in sorted(days,reverse=True):
         if os.path.isdir(ldir + day) is False:
            continue
         hist_file = ldir + day + "/history.json"
         hist = load_json_file(hist_file)

         for kk in hist:
            for cam in sorted(hist[kk]):
               if "snap_file" not in hist[kk][cam]:
                  continue
               snap_file = (hist[kk][cam]['snap_file'])
               if "marked" in snap_file:
                  continue
               el = snap_file.split("_")
               station_id = el[0]
               cam_id = el[1]
               capture_date = el[2] + "-" + el[3] + "-" + el[4] + " " + el[5] + ":" + el[6].replace(".jpg", "")
               forecast_file = el[2] + "_" + el[3] + "_" + el[4] + "_" + el[5] + "_" + el[6].replace(".jpg", ".json")


               

               # get moon phase
               my_datetime = datetime.datetime.strptime(capture_date, "%Y-%m-%d %H:%M")
               my_datetime_str = my_datetime.strftime("%Y_%m_%d_%H_%M_0")

               # get the local time/utc offset
               localtime, utc_offset = get_localtime_offset(self.device_lat,self.device_lng, my_datetime)


               # this is for the weather conditions
               if localtime in self.db_keys:
                  print("Skip got it already.", localtime)
               else :

                  # get forecast if it exists
                  if os.path.exists(forecast_file) is True:
                     try:
                        forecast = load_json_file(forecast_file)
                     except:
                        forecast = {}
                  else:
                     forecast = {}
                  # get local time and ephem
                  ep_info = ephem_info(self.device_lat, self.device_lng, capture_date)
                  sun_status, sun_az, sun_alt, sun_rise, sun_set, moon_az, moon_alt, moon_rise, moon_set = ep_info
                  fractional_phase, percent_full, moon_phase = get_moon_phase(my_datetime_str, self.device_lat, self.device_lng)

                  insert_vals = [el[0], localtime, utc_offset, sun_status, float(sun_az), float(sun_alt), moon_phase, float(moon_az), float(moon_alt), str(forecast), "", "", 0]
                  sql = "INSERT INTO weather_conditions(station_id, local_datetime_key, utc_time_offset, sun_status, sun_az, sun_el, moon_status, moon_az, moon_el, forecast, actual, ai_final, samples_done) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)"
                  self.cur.execute(sql, insert_vals)
                  self.con.commit()
                  self.db_keys[localtime] = 1

                  print("FILE:", snap_file)
                  print("EP:", ep_info)
                  print("FORECAST", forecast)
                  print("MOON:", moon_phase, fractional_phase, percent_full)
                  print("LOCALTIME:", localtime, utc_offset)

               # this is for the snap image
               if snap_file in self.db_keys_snaps:
                  print("DONE ALRD", snap_file)
                  
               else:
                  insert_vals = [station_id, snap_file, cam_id, localtime, "", 0]
                  sql = "INSERT INTO ml_weather_snaps (station_id, filename, camera_id, local_datetime_key, ai_final, samples_done) VALUES(?,?,?,?,?,?)"
                  self.cur.execute(sql, insert_vals)
                  self.con.commit()
                  self.db_keys[localtime] = 1
                  print(sql)
                  print(insert_vals)


   def index_weather_snaps_all(self):
      dirs = glob.glob("/mnt/ams2/latest/*")
      latest_dirs = []
      cc = 0
      for d in sorted(dirs,reverse=True):

         if cfe(d, 1) == 1:
            latest_dirs.append(d)
            save_file = d + "/history.json"
            if cfe(save_file) == 0 or cc < 2:
               self.index_weather_snaps_day(d)
            cc += 1

   def index_weather_snaps_day(self, day_dir):
      index = {}
      files = glob.glob(day_dir + "/*.jpg")
      for snap in sorted(files, reverse=True):
         snap_fn = snap.split("/")[-1]
         snap_el = snap_fn.split("_")
         if "marked" in snap_fn :
            continue
         
         key = snap_el[5] + snap_el[6][0]
         cam = snap_el[1]
         if key not in index:
            index[key] = {}
         if cam not in index[key]:
            index[key][cam] = {}
         index[key][cam]['snap_file'] = snap_fn

      final_index = {}
      for key in sorted(index.keys(), reverse=True):
         final_index[key] = {}
         print("IND", index[key])
         for cam in sorted(self.cams):
            if cam in index[key]:
               print("YES", key, cam, index[key][cam])
               final_index[key][cam] = index[key][cam]
            else:
               final_index[key][cam] = ""

         print(key, index[key])
      save_file = day_dir + "/history.json"
      save_json_file(save_file, final_index)
      cloud_file = save_file.replace("/mnt/ams2", "/mnt/archive.allsky.tv/" + self.station_id )
      cloud_file = cloud_file.replace("latest", "LATEST")
      print("SAVED:", save_file)
      cmd = "cp " + save_file + " " + cloud_file
      os.system(cmd)

   def insert_ml_weather_sample(self, filename, station_id, camera_id, local_datetime_key, predict_class, predict_conf):
       sql = "INSERT INTO ml_weather_samples (filename, station_id, camera_id, local_datetime_key, ai_sky_condition, ai_sky_condition_conf) VALUES(?,?,?,?,?,?)"
       insert_vals = [filename, station_id, camera_id, local_datetime_key, predict_class, predict_conf]
       self.cur.execute(sql, insert_vals)
       self.con.commit()
       print(sql)
       print("INSERTED:", self.cur.lastrowid)

       sql = "UPDATE ml_weather_snaps set samples_done = 1 where filename = ?"
       insert_vals = [filename]
       print("UPDATE:", sql)
       print(insert_vals)
       self.cur.execute(sql, insert_vals)
       self.con.commit()
       exit()




   def insert_metar_record(self, blob):
       #sql = "INSERT INTO metar (raw_text, station_id, observation_time, latitude, longitude, elevation_m, temp_c, dewpoint_c, wind_dir_degrees, wind_speed_kt, wind_gust_kt, visibility_statute_mi, altim_in_hg, sea_level_pressure_mb, sky_conditions, pcp3hr_in, precip_in, flight_category) VALUES(_"
       strings = ['metar_type', 'raw_text', "station_id", "observation_time", "sky_conditions", "flight_category" ,"wx_string"]
       sql = "INSERT OR REPLACE INTO metar ("
       val_q = " VALUES ("
       start = 0
       insert_vals = [] 
       for key in sorted(blob.keys()):
          if start != 0:
             sql += ","
             val_q += ","
          else:
             start = 1

          sql += key 
          val_q += "?"
          if key in strings:
             if key == "sky_conditions":
                insert_vals.append(json.dumps(blob[key]))
             else:
                insert_vals.append(str(blob[key]))
          else:
             try:
                insert_vals.append(float(blob[key]))
             except:
                print("ERROR WITH : ", key)
                exit()
       val_q += ")"
       sql_stmt = sql + ")" + val_q
       print(sql_stmt)
       print(insert_vals)
       print(len(insert_vals))
       self.cur.execute(sql_stmt, insert_vals)
       self.con.commit()
       print("INSERTED:", self.cur.lastrowid)

   def get_metar_records(self, start_time, end_time, lat, lon, size=1):
       records = []
       from bs4 import BeautifulSoup as Soup
       min_lat = lat - size
       max_lat = lat + size
       min_lon = lon - size
       max_lon = lon + size
       url = "https://www.aviationweather.gov/adds/dataserver_current/httpparam?dataSource=metars&requestType=retrieve&format=xml&minLat={:s}&minLon={:s}&maxLat={:s}&maxLon={:s}&startTime={:s}&endTime={:s}".format(str(min_lat),str(min_lon),str(max_lat),str(max_lon),str(start_time),str(end_time))
       print(url)
       fp = open("metar.xml", "w")
       response = requests.get(url)
       content = response.content.decode()
       fp.write(content)

       fp = open("metar.xml").read()
       soup = Soup(fp, features="lxml")
       data = soup.data
       for row in data.children:
          sky_cond = []
          fields = []
          for field in row:
             if "<" in str(field):

                data = str(field).split("</")[0]
                if "sky_condition" in data:
                   if str(field) is not None:
                      field_str = str(field).replace("<sky_condition ", "")
                      field_str = field_str.replace("></sky_condition>", "")
                      fff = field_str.split(" ") 
                      blob = {}
                      for ff in fff:
                         f,v = ff.split("=")
                         blob[f] = v
                   else:
                      blob = {}
                   sky_cond.append(blob)
                else:
                   vvv = str(field).split("</")
                   vals = str(vvv[0]).split(">")
                   vals[0] = vals[0].replace("<", "")
                   fields.append(vals)
          if len(fields) > 0:
             blob = {}
             for xxx in fields:
                f = xxx[0]
                v = xxx[1]
                if "quality" not in f:
                   blob[f] = v

             blob['sky_conditions'] = sky_cond
             try:
                self.insert_metar_record(blob)
             except:
                print("METAR INSERT FAILED UNQ?", blob)
             records.append(blob)
       return(records)
