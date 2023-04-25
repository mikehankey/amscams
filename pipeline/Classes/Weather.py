import sqlite3
from datetime import datetime as dt, date, timedelta
import requests
import time
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
import PIL

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
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
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
      self.json_conf = json_conf
      self.weather_condition_classes = sorted(load_json_file("weather_condition_classes.json"))


      self.station_id = json_conf['site']['ams_id']
      self.device_lat = json_conf['site']['device_lat']
      self.device_lng = json_conf['site']['device_lng']
      self.cams = []
      self.sd_frame_width = 640
      self.sd_frame_height = 360
      self.hd_frame_width = 1920 
      self.hd_frame_height = 1080 
      self.max_cols = self.hd_frame_width / self.sd_frame_width
      self.max_rows = self.hd_frame_height / self.sd_frame_height
      print("Max cols/rows:", self.max_cols, self.max_rows)

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
      try:
         self.model =load_model(self.weather_conditions_model_file)
         self.model.compile(loss='categorical_crossentropy',
            optimizer='rmsprop',
            metrics=['accuracy'])
         self.weather_check_config()
      except:
         print("AI FAILED TO LOAD MODEL")

   def help(self):
      print("""

  ____  _      _      _____ __  _  __ __ 
 /    || |    | |    / ___/|  |/ ]|  |  |
|  o  || |    | |   (   \_ |  ' / |  |  |
|     || |___ | |___ \__  ||    \ |  ~  |
|  _  ||     ||     |/  \ ||     ||___, |
|  |  ||     ||     |\    ||  .  ||     |
|__|__||_____||_____| \___||__|\_||____/ 
                                         
AllSky.com/ALLSKY7 - ALLSKYOS STATION SOFTWARE 
Copyright Mike Hankey LLC 2016-2022 
Use permitted for licensed users only.
Contact mike.hankey@gmail.com

This program is an interface for runnin the various weather features of the ALLKSKY7 

usage: python3.6 Weather.py [COMMAND] [EXTRA ARGUMENTS]

Supported command line arguments
         
load_weather - this will create the weather DB
               and then load all past historical
               images through the 'processing'. 
               includes: weather data condition 
               creation for sun status and forecast. 
               This loads all images / history from 
               /mnt/ams2/latest on the first run
               and then only the new data on subseqent 
               runs.

process_all -  this will take whatever 'snaps' exist 
               in the DB that have not yet been processed 
               and then process them through the ML pipeline. 
               This includes making 6 sample images 180x180 
               from the original SNAP, running those through 
               the weather predictor, saving the results, 
               making final AI WEATHER OBS REPORT and logging 
               that with the network. 

process_snap - this does all of the processing for a single 
               picture vs all outstanding


load_metar   - this will load forecast data from the METAR 
               office(s) to the local machine 
               (needed to maintain weather history)

stack_index  - this will re-index the existing stacks so they 
               can be used in the AI for history

Future Commands

status       - reports current active weather status across all cameras
               and available info. This should run automatically 
               at least 1 x 15 minutes (or faster) 
               via cronjob for as7-latest.py

station_info - report the current weather database 
               and processing status (last run, % complete, errors/notes)

What does this program do? -- it loads or creates weather data from APIs and functions and then makes sure all of the weather SNAPS are loaded into the db, run through the AI and reported to the network.
      """)

   def network_timelapse(self, station_id, cam_id, start_date, end_date):
      self.cloud_dir = "/mnt/archive.allsky.tv/" + station_id + "/LATEST/"
      y,m,d = start_date.split("_")
      y,m,d = int(y),int(m), int(d)
      start_dt = date(y,m,d)
      y,m,d = end_date.split("_")
      y,m,d = int(y),int(m), int(d)
      end_dt = date(y,m,d)
      delta = end_dt - start_dt # returns timedelta
      all_data = {}
      for i in range(delta.days + 1):
         day = start_dt + timedelta(days=i)
         day = str(day).replace("-", "_")
         hist_file = self.cloud_dir + day + "/history.json" 
         if os.path.exists(hist_file) is True:
            hist_data = load_json_file(hist_file)
            for interval in hist_data:
               # main frame
               im = PIL.Image.new(mode="RGB", size=(1920, 1080))
               px = 0
               py = 0
               cc = 0
               rc = 0
               cams = len(hist_data[interval])
              
               for cam_id in sorted(hist_data[interval]):

                  x1 = self.sd_frame_width * cc 
                  x2 = x1 + self.sd_frame_width
                  y1 = self.sd_frame_height * rc 
                  y2 = x1 + self.sd_frame_height
                  print("CAM:", cam_id, cc, rc, x1, x2, y1, y2)

                  if cam_id not in all_data:
                     all_data[cam_id] = {}
                     all_data[cam_id]['files'] = []
                  snap_file =  self.cloud_dir + day + "/" + hist_data[interval][cam_id]['snap_file']
                  snap_url = snap_file.replace("/mnt/", "https://")
                  all_data[cam_id]['files'].append(snap_file) 
                  img = self.fetch_image(snap_url)
                  img_pil = PIL.Image.fromarray(img)
                  Image.Image.paste(im, img_pil, (x1,y1))
                  #cv2.imshow('pepe', image)
                  #cv2.waitKey(30)
                  cc += 1
                  if cc % self.max_cols == 0:
                     rc += 1
                     cc = 0
               im_cv = np.array(im)
               im_cv = im_cv[:, :, ::-1].copy()
               cv2.imshow('pepe', im_cv) 
               cv2.waitKey(30)
         print(day, hist_file)

      exit()
      for cam_id in all_data:
         for sf in sorted(all_data[cam_id]['files'], reverse=False):
            if os.path.exists(sf) is True:
               surl = sf.replace("/mnt/", "https://")
               print(surl)

               #resp = requests.get(surl, stream=True).raw
               #image = np.asarray(bytearray(resp.read()), dtype="uint8")
               #image = cv2.imdecode(image, cv2.IMREAD_COLOR)
               image = self.fetch_image(surl)
  

               cv2.imshow('pepe', image)
               cv2.waitKey(30)

   def fetch_image(self, surl):
      resp = requests.get(surl, stream=True).raw
      image = np.asarray(bytearray(resp.read()), dtype="uint8")
      image = cv2.imdecode(image, cv2.IMREAD_COLOR)
      image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
      return(image)
   def index_latest(self): 
      
      latest_dir = "/mnt/ams2/latest/"
      idx_file = latest_dir + self.station_id + "_LATEST_INDEX.json" 
      if os.path.exists(idx_file) is True:
         idx = load_json_file(idx_file)
      else:
         idx = {}
      files = os.listdir(latest_dir)
      for f in files:
         if os.path.isdir(latest_dir + f) :
            print("ls " + latest_dir + f)
            exit()
            if f not in idx:
               idx[f] = os.listdir(latest_dir + f)
         print(f, len(idx[f]))
   def weather_check_config(self):
      # check some basic setup/config things about this station so we can perform all weather tasks!

      # 3 - do we have the "weather_config" val in as6.json
      # 4 - do we have the weather_db setup
      # 5 - have we scaned our past weather history
      # 6 - have we run the AI detect up to the most recent day
      # 7 - have we sync'd out our weather repo

      # 1 - do we have tensor flow, libs , models and class files installed? If not then no point in continuing!
      if "ml" in self.json_conf:
         if "tensor_flow" not in self.json_conf['ml']:
            print("Tensor flow not installed?")
            print("Problem with tensor flow install? exiting...")
         elif self.json_conf['ml']['tensor_flow'] is not True:
            print("Problem with tensor flow install? exiting...")
            exit()

      # 2 - are we running python3.6 (currently required)
      import platform
      running_py = platform.python_version()
      if "3.6" not in str(running_py):
         print("PyV:", running_py)
         print("Warning: not running python 3.6")
         #exit()
 
      if "weather" not in self.json_conf:
         print("NEED TO UPDATE THE WEATHER CONFIG!")
         # 1 - what is the metar station(s)
         # 2 - is the station in the US / NOAA servicable area?
         #   - if yes what is the GRID X,Y
         # 3 - If non-US, what alternative for forecast shall we use?
         print("Please add weather block to as6.json and include:")
         print("metar: YOUR_STATION")
         print("NOAA:forecastOffice YOUR_OFFICE")
         print("NOAA:gridX YOURX")
         print("NOAA:gridY YOURY")
      else:
         if "NOAA" in self.json_conf['weather']:
            self.NOAA = True
            self.forecastOffice = self.json_conf['weather']['NOAA']['forecastOffice']
            self.NOAA_GRID_X = self.json_conf['weather']['NOAA']['gridX']
            self.NOAA_GRID_Y = self.json_conf['weather']['NOAA']['gridY']
         else:
            self.NOAA = False

         #print("Basic weather setup is good")

   def status(self):
      print("CURRENT WEATHER STATUS...")
      # check and insert the free API thing we have
      # check and insert the METAR if possible
      # get the latest pics and run them through the AI (if not already done)
      # insert those results
      # log txt data with network or update wasabi? (pics are already there) 

   def weather_predict(self, img_file=None, img=None):
      import random
      rand = random.randint(0,100)
      img_height = 150
      img_width = 150
      if img is not None :
         if img_file is not None:
            temp_file = img_file.split("/")[-1]
         else:
            temp_file = "temp" + str(rand) + ".jpg"
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
      if img_file is not None:
         img_fn = img_file.split("/")[-1]
      else:
         img_fn = ""
      print("\r                                                                                                                                       ", end = "")
      string = "{} most likely belongs to {} with a {:.2f} % confidence.".format(img_fn, self.weather_condition_classes[np.argmax(score)], 100 * np.max(score))
      print("\r" + string, end= "")
      os.system("rm " + temp_file)
      
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
      os.system("clear")
      sql = "SELECT filename from ml_weather_snaps where samples_done != 1"
      sql = "select A.filename, A.local_datetime_key, sun_status, moon_status, forecast, A.ai_final from ml_weather_snaps A INNER JOIN weather_conditions B on A.local_datetime_key = B.local_datetime_key where A.samples_done != 1 order by A.filename DESC limit 100";
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
         #print("FILE:", filename)


   def process_weather_snap(self, snap_file, local_datetime_key, sun_status,nodb=False):
      # Here we will get the relevant meta data about the weather at this time
      # then we will cut the image into 6 sqaures/crops
      # then for each crop we will do weather_detect on it to get the class and confidence
      # then we will make the repo_label_dir which will be
      # {day_night_status}-{label} 
      # then save the weather square in the image folder
 



      #print("SNAP:", snap_file)

      station_id, cam, year, month, day, hour, minute = snap_file.split("_")

      latest_dir = "/mnt/ams2/latest/" + year + "_" + month + "_" + day + "/"
      img_file = latest_dir + snap_file
      img = cv2.imread(img_file)
      lcc = 0
      marked_img = img.copy()
      sc = 0
      resp = []
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
               learning_fn = img_file.split("/")[-1].replace(".jpg", "-" + str(lcc) + ".jpg")
               predict_class, predict_conf = self.weather_predict(learning_fn, learning_img)
               predict_name = predict_class
               resp.append((learning_fn, predict_class, predict_conf))

               if sc != 3 and sc != 7:
                  cv2.putText(marked_img, predict_name ,  (x1+11, y1+21), cv2.FONT_HERSHEY_SIMPLEX, .5, (0, 0, 0), 1) 
                  cv2.putText(marked_img, predict_name ,  (x1+10, y1+20), cv2.FONT_HERSHEY_SIMPLEX, .5, (150, 150, 150), 1) 
                  cv2.rectangle(marked_img, (x1, y1), (x2,y2), (128, 128, 128), 2)
               #print("PRED:", x1, y1, predict_class, predict_conf)

               learning_dir = self.weather_learning_dir + predict_class + "/" 
               if os.path.exists(learning_dir) is False:
                  os.makedirs(learning_dir)
               learning_file = learning_dir + img_file.split("/")[-1].replace(".jpg", "-" + str(lcc) + ".jpg")
               #if os.path.exists(learning_file):
               #   continue


               if learning_img.shape[0] == learning_img.shape[1]:
                  cv2.imwrite(learning_file, learning_img)
                  #print("Saved learning file:", x1,y1,x2,y2, row, col, learning_file)
                  learning_fn = learning_file.split("/")[-1]
                  try:
                  #if True:
                     if nodb is False:
                        self.insert_ml_weather_sample(learning_fn, station_id, cam, local_datetime_key, predict_class, predict_conf)
                  except:
                     foo = "bar"
                  lcc += 1
               sc += 1
         marked_file = img_file.replace(".jpg", "-marked.jpg")
         if nodb is False:
            sql = "UPDATE ml_weather_snaps set samples_done = 1 where filename = ?"
            update_vals = [snap_file]
            #print("UPDATE:", sql, update_vals)
            self.cur.execute(sql, update_vals)
            self.con.commit()

         #print("Saved:", marked_file)
         cv2.imwrite(marked_file, marked_img)
      return(resp)

   def update_weather_snaps_sample_status(self,filename):
      sql = "UPDATE ml_weather_snaps set samples_done = 1 where filename = ?"
      update_vals = [filename]
      self.cur.execute(sql, update_vals)
      self.con.commit()

   def load_database(self, in_day=None):
      if os.path.exists("worklog.json") is True:
         worklog = load_json_file("worklog.json")
      else:
         worklog = {}
         worklog['weather'] = {}
         worklog['weather']['days'] = {}
     
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

         ts = time.time()
         if os.path.isdir(ldir + day) is False:
            continue

         day_dt = datetime.datetime.strptime(day, "%Y_%m_%d")
         days_old = datetime.datetime.now() - day_dt 
         days_old = int(days_old.total_seconds()/86400)
         if day in worklog['weather']['days'] and days_old > 2:
            #print("We already did this day skip it!", day)
            continue


         hist_file = ldir + day + "/history.json"
         hist = load_json_file(hist_file)

         for kk in hist:
            #print("KK", kk)
            #print("HIST KK", hist[kk])

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

                  #print("ADDED NEW WEATHER CONDITION:", localtime, ep_info, forecast)
                  #print("FORECAST", forecast)
                  #print("MOON:", moon_phase, fractional_phase, percent_full)
                  #print("LOCALTIME:", localtime, utc_offset)

               # this is for the snap image
               if snap_file in self.db_keys_snaps:
                  print("SNAP INSDIDE DB ALREADY", snap_file)
                  
               else:
                  insert_vals = [station_id, snap_file, cam_id, localtime, "", 0]
                  sql = "INSERT INTO ml_weather_snaps (station_id, filename, camera_id, local_datetime_key, ai_final, samples_done) VALUES(?,?,?,?,?,?)"
                  self.cur.execute(sql, insert_vals)
                  self.con.commit()
                  self.db_keys[localtime] = 1
                  #print("INSERTED WEATHER SNAP:", snap_file)
         elp = time.time() - ts
         print("LOOP ELP:", elp)
         worklog['weather']['days'][day] = {}
         save_json_file("worklog.json", worklog)

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
         for cam in sorted(self.cams):
            if cam in index[key]:
               final_index[key][cam] = index[key][cam]
            else:
               final_index[key][cam] = ""

      save_file = day_dir + "/history.json"
      save_json_file(save_file, final_index)
      cloud_file = save_file.replace("/mnt/ams2", "/mnt/archive.allsky.tv/" + self.station_id )
      cloud_file = cloud_file.replace("latest", "LATEST")
      print("SAVED:", save_file)
      cmd = "cp " + save_file + " " + cloud_file
      os.system(cmd)

   def insert_ml_weather_sample(self, filename, station_id, camera_id, local_datetime_key, predict_class, predict_conf):
       sql = "INSERT OR REPLACE INTO ml_weather_samples (filename, station_id, camera_id, local_datetime_key, ai_sky_condition, ai_sky_condition_conf) VALUES(?,?,?,?,?,?)"
       insert_vals = [filename, station_id, camera_id, local_datetime_key, predict_class, predict_conf]
       self.cur.execute(sql, insert_vals)
       self.con.commit()




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
       #print("INSERTED:", self.cur.lastrowid)

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
