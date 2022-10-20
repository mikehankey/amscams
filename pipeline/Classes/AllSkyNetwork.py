import sqlite3
from prettytable import PrettyTable as pt
import math
import boto3
from boto3.dynamodb.conditions import Key
from RMS.Math import angularSeparation
from lib.PipeAutoCal import XYtoRADec 
from recal import get_catalog_stars, get_star_points, get_xy_for_ra_dec, minimize_fov, get_image_stars_with_catalog
from lib.PipeAutoCal import update_center_radec
from lib.Map import make_map,geo_intersec_point 
from lib.PipeEvent import get_trim_num
from prettytable import PrettyTable as pt
import matplotlib
import matplotlib.pyplot as plt
from recal import do_photo
from lib.PipeDetect import get_contours_in_image, find_object, analyze_object
from lib.kmlcolors import *
from lib.PipeImage import stack_frames
import simplekml
import time
import requests
import boto3
import redis
from solveWMPL import convert_dy_obs, WMPL_solve, make_event_json, event_report
import numpy as np
import datetime
import simplejson as json
import os
import shutil
import platform
from lib.PipeUtil import load_json_file, save_json_file, get_trim_num, convert_filename_to_date_cam, starttime_from_file, dist_between_two_points, get_file_info, calc_dist, check_running
from lib.intersecting_planes import intersecting_planes
from DynaDB import search_events, insert_meteor_event, delete_event, get_obs
from ransac_lib import ransac_outliers
from sklearn.cluster import DBSCAN
from sklearn import metrics
from sklearn.datasets import make_blobs
from sklearn.preprocessing import StandardScaler
from multiprocessing import Process
import cv2
from lib.PipeVideo import load_frames_simple
from Classes.RenderFrames import RenderFrames 

class AllSkyNetwork():
   def __init__(self):
      self.RF = RenderFrames()
      self.solving_node = "AWSB1"
      self.plane_pairs = {}
      self.errors = []
      self.custom_points = {}
      self.deleted_points = {}
      if os.path.exists("admin_conf.json") is True:
         self.admin_conf = load_json_file("admin_conf.json")
         self.data_dir = self.admin_conf['data_dir']
      else:
         self.data_dir = "/mnt/f/"
    
      self.check_start_ai_server()
  

      self.good_obs_json = None
      self.user =  os.environ.get("USERNAME")
      if self.user is None:
         self.user =  os.environ.get("USER")
      self.platform = platform.system()

      self.home_dir = "/home/" + self.user + "/" 
      self.amscams_dir = self.home_dir + "amscams/"

      self.local_event_dir = self.data_dir + "EVENTS/"
      self.db_dir = self.local_event_dir + "DBS/"
      if os.path.exists(self.db_dir) is False:
         os.makedirs(self.db_dir)
      
      self.cloud_dir = "/mnt/archive.allsky.tv/"
      self.cloud_event_dir = "/mnt/archive.allsky.tv/EVENTS/"
      self.s3_event_dir = "/mnt/allsky-s3/EVENTS/"

      self.aws_r = redis.Redis("allsky-redis.d2eqrc.0001.use1.cache.amazonaws.com", port=6379, decode_responses=True)
      self.r = redis.Redis("localhost", port=6379, decode_responses=True)
      self.API_URL = "https://kyvegys798.execute-api.us-east-1.amazonaws.com/api/allskyapi"
      self.dynamodb = boto3.resource('dynamodb')

      self.station_data = load_json_file("stations.json")
      self.rurls = {}
      for data in self.station_data['stations']:
         station = data['name']
         url = data['url']
         operator = data['operator']
         location = data['location']
         country = data['country']
         self.rurls[station] = url


      self.help()


   

   def quick_report(self, date):
      stats = {}
      for ob in self.obs_dict:
         st_id = self.obs_dict[ob]['station_id']
         if st_id not in stats:
            stats[st_id] = 1
         else:
            stats[st_id] += 1
      c = 1 
      temp = []
      for st in stats:
         sti = int(st.replace("AMS", ""))
         temp.append((sti,stats[st]))
      for row in sorted(temp, key=lambda x: x[0], reverse=False):
         ams_id = "AMS{0:03d}".format(row[0])
         print(c, ams_id, row[1])
         c += 1

      

   def rsync_data_only(self, date):
      #self.set_dates(date)
      # this sync method is meant for remote workers
      # the worker will only transmit to the cloud the .pickle file for each event 
      # and any summary json or html files for the root. 
      # once transmitted a remote URL will be hit to trigger an unzip process and upload to the S3FS from the AWS server

      # make / clean up the temp upload dir 
      temp_dir = self.data_dir + "EVENTS/TEMP/"
      if os.path.exists(temp_dir) is False:
         os.makedirs(temp_dir)
      else:
         tfiles = os.listdir(temp_dir)
         for tf in tfiles:
            os.remove(temp_dir + tf)

      local_ev_dirs = os.listdir(self.local_evdir)


      for evd in local_ev_dirs:
         if "dbfiles" in evd:
            continue
         if os.path.isdir(self.local_evdir + evd) is True:
            evid = evd
            pickle_file = self.local_evdir + evd + "/" + evd + "_trajectory.pickle"
            temp_file = temp_dir + evd + "_trajectory.pickle"

            temp_obs_file = temp_dir + evd + "_GOOD_OBS.json"
            temp_fail_file = temp_dir + evd + "-fail.json"
            temp_event_file = temp_dir + evd + "-event.json"
            temp_map_file = temp_dir + evd + "_map.kml"

            good_obs_file = self.local_evdir + evd + "/" + evd + "_GOOD_OBS.json"
            fail_file = self.local_evdir + evd + "/" + evd + "-fail.json"
            event_file = self.local_evdir + evd + "/" + evd + "-event.json"
            map_file = self.local_evdir + evd + "/" + evd + "_map.kml"

            if os.path.exists(pickle_file) is True and os.path.exists(temp_file) is False:
               print(pickle_file, temp_file)
               shutil.copyfile(pickle_file, temp_file)
            if os.path.exists(good_obs_file) is True and os.path.exists(temp_obs_file) is False:
               shutil.copyfile(good_obs_file, temp_obs_file)
               print(good_obs_file, temp_obs_file)
            if os.path.exists(fail_file) is True and os.path.exists(temp_fail_file) is False:
               shutil.copyfile(fail_file, temp_fail_file)
               print(fail_file, temp_fail_file)
            if os.path.exists(event_file) is True and os.path.exists(temp_event_file) is False:
               print(event_file, temp_event_file)
               shutil.copyfile(event_file, temp_event_file)
            if os.path.exists(map_file) is True and os.path.exists(temp_map_file) is False:
               print(map_file, temp_map_file)
               shutil.copyfile(map_file, temp_map_file)

      if os.path.exists( temp_dir + date + "_dbfiles.tar") :
         os.remove( temp_dir + date + "_dbfiles.tar")
      if os.path.exists( temp_dir + date + "_dbfiles.tar.gz") :
         os.remove( temp_dir + date + "_dbfiles.tar.gz")

      cmd = "cd " + temp_dir +"; tar -cvf " + self.local_evdir + date + "_dbfiles.tar" + " "  + "*"
      os.system(cmd)

      #cmd = "gzip -f " + self.local_evdir + date + "_dbfiles.tar" 
      cmd = "7z a " + self.local_evdir + date + "_dbfiles.tar.7z " + self.local_evdir + date + "_dbfiles.tar"
      os.system(cmd)
      
      cmd = "cp " + self.local_evdir + date + "_dbfiles.tar.7z " + self.cloud_evdir + date + "_dbfiles.tar.7z "
      os.system(cmd)

      #cmd = "cp " + self.local_evdir + date + "_MIN_EVENTS.json " + self.cloud_evdir + date + "_MIN_EVENTS.json"
      #os.system(cmd)

      #cmd = "cp " + self.local_evdir + date + "_plane_pairs.json " + self.cloud_evdir + date + "_PLANE_PAIRS.json"
      #os.system(cmd)

      cmd = "rsync -auv --exclude '*OBS_DICT*' --exclude '*ALL_OBS*' " + self.local_evdir + "*.json " + self.cloud_evdir 
      print(cmd)
      os.system(cmd)

      cmd = "rsync -auv " + self.local_evdir + "*.info " + self.cloud_evdir 
      print(cmd)
      os.system(cmd)

      cmd = "rsync -auv " + self.local_evdir + "*.kml " + self.cloud_evdir 
      print(cmd)
      os.system(cmd)

      cmd = "rsync -auv " + self.local_evdir + "*.html " + self.cloud_evdir 
      print(cmd)
      os.system(cmd)

         

   def sync_dyna_day(self, date):
      #insert_meteor_event(dynamodb=None, event_id=None, event_data=None)
      print("SYNC DYNA DAY")
      events = search_events(self.dynamodb, date, None)
      print("DYNA EVENTS:", len(events))
      event_dict = {}
      for ev in events:
         event_id = ev['event_id']
         event_dict[event_id] = ev
      self.local_event_dir = self.data_dir + "EVENTS/"

      sql_events = self.sql_select_events(date.replace("_", ""))
      for row in sql_events:
         (event_id, event_minute, revision, stations, obs_ids, event_start_time, event_start_times,  \
                 lats, lons, event_status, run_date, run_times) = row
         if event_id not in event_dict:
            self.check_event_status(event_id)
            event_data = self.good_obs_to_event(date, event_id)
            #print(event_id, "not in dynadb")
            #print(event_data)
            insert_meteor_event(self.dynamodb, event_id, event_data)

   def load_stations_file(self):
      url = "https://archive.allsky.tv/EVENTS/ALL_STATIONS.json"
      local_file = self.local_event_dir + "/ALL_STATIONS.json"
      local_loc_file = self.local_event_dir + "station_locations.json"
      print("LC:", local_loc_file)
      if os.path.exists(local_loc_file) is True:
         loc_info = load_json_file(local_loc_file)
      else:
         loc_info = None

      if os.path.exists(local_file) :
         sz, td = get_file_info(local_file)
         td = td / 60 /24 
      else:
         td = 999

      print("stations file syncd", td, "days ago")

      if td < 1:
         try:
            response = requests.get(url)
            content = json.loads(response.content.decode())
            save_json_file(self.local_event_dir + "/ALL_STATIONS.json", content)
         except:
            print("FAILED " + url)

      self.stations = load_json_file(self.local_event_dir + "/ALL_STATIONS.json")
      self.station_dict = {}
      self.photo_credits = {}
      sc = 1
      for data in self.stations:
         sid = data['station_id']
         self.station_dict[sid] = data
         if "city" in data:
            city = data['city']
         else:
            city = "" 
         if "state" in data:
            state  = data['state']
         else:
            state = "" 

         if "country" in data:
            country = data['country']
         else:
            country = "" 

         if loc_info is not None:
            if sid in loc_info:
               if 'country_code' in loc_info[sid]:
                  lcountry = loc_info[sid]['country_code']
               else:
                  lcountry = None
            if lcountry is not None:
               if country != lcountry.upper():
                  country = lcountry.upper()
         else:
            print("LOC NONE")
         data['country'] = country
         if "operator_name" in data:
            operator_name = data['operator_name']
         else:
            operator_name = "" 
         if "inst_name" in data:
            inst_name = data['inst_name']
         else:
            inst_name = None
         if "obs_name" in data:
            obs_name = data['obs_name']
         else:
            obs_name = "" 
         if "photo_credit" in data:
            photo_credit = data['photo_credit']
         else:
            photo_credit = None

       
         if operator_name == "" or operator_name == " " :
            self.photo_credits[sid] = sid + " unknown"
         elif operator_name != "" and city != "" and state != "" and ("United States" in country or "US" in country):
            self.photo_credits[sid] = operator_name + " " + city + "," + state + " " +  country
         elif operator_name != "":
            self.photo_credits[sid] = operator_name + " " + city + "," + country
         else:
            self.photo_credits[sid] = sid
         print(sc, self.photo_credits[sid])
         sc += 1
   def day_prep(self, date):
      print("ok")

   def set_dates(self, date):
      print("SET DATES FOR:", date)
      self.year, self.month, self.day = date.split("_")
      self.dom = self.day
      self.date = date
      self.local_evdir = self.local_event_dir + self.year + "/" + self.month + "/" + self.day  + "/"
      self.cloud_evdir = self.cloud_event_dir + self.year + "/" + self.month + "/" + self.day   + "/"
      self.s3_evdir = self.s3_event_dir + "/" + self.year + "/" + self.month + "/" + self.day   + "/"
      self.obs_dict_file = self.local_evdir + self.date + "_OBS_DICT.json"
      self.all_obs_file = self.local_evdir + self.date + "_ALL_OBS.json"
      self.sync_log_file = self.local_evdir + date + "_SYNC_LOG.json"
      self.min_events_file = self.local_evdir + date + "_MIN_EVENTS.json"
      self.all_events_file = self.local_evdir + date + "_ALL_EVENTS.json"
      self.station_events_file = self.local_evdir + date + "_STATION_EVENTS.info"

      self.all_obs_gz_file = self.local_evdir + self.date + "_ALL_OBS.json.gz"
      self.cloud_all_obs_file = self.cloud_evdir + self.date + "_ALL_OBS.json"
      self.cloud_all_obs_gz_file = self.cloud_evdir + self.date + "_ALL_OBS.json.gz"
      self.obs_review_file = self.local_evdir + date + "_OBS_REVIEWS.json"
      self.all_stations_file = self.local_event_dir + "/" + self.year + "/" + self.month + "/" + self.day + "/" + self.date + "_ALL_STATIONS.json"
      self.all_stations = load_json_file(self.all_stations_file)
      self.station_loc = {}
      for row in self.all_stations:
         st_id , lat, lon, alt, city, network = row
         self.station_loc[st_id] = [lat,lon,alt]


      # DB FILE!
      self.db_file = self.db_dir + "/ALLSKYNETWORK_" + date + ".db"
      print("DB FILE IS:", self.db_file)
      if os.path.exists(self.db_file) is False:
         os.system("cat ALLSKYNETWORK.sql | sqlite3 " + self.db_file)
      if os.path.exists(self.db_file) is False:
         print("DB FILE NOT FOUND.", self.db_file)
         return ()
      self.con = sqlite3.connect(self.db_file)
      self.con.row_factory = sqlite3.Row
      self.cur = self.con.cursor()

      if os.path.exists(self.local_evdir) is False:
         os.makedirs(self.local_evdir)
      if os.path.exists(self.cloud_evdir) is False:
         os.makedirs(self.cloud_evdir)

      print(self.local_evdir + "/" + self.date + "_OBS_DICT.json")

      local_size, tdd = get_file_info(self.all_obs_file + ".gz") 
      cloud_size, tdd = get_file_info(self.cloud_all_obs_file + ".gz") 

      if os.path.exists(self.cloud_all_obs_gz_file) is False and os.path.exists(self.all_obs_file) is False:
         print("Could not find:", self.cloud_all_obs_gz_file, "should we download it?")
         #input("Enter to continue (will start UDC process)")
         os.system("./DynaDB.py udc " + date)

      elif os.path.exists(self.all_obs_gz_file) is False and os.path.exists(self.cloud_all_obs_gz_file) is True: 
         print("COPY FILE:", self.cloud_all_obs_gz_file, self.all_obs_gz_file)
         shutil.copyfile(self.cloud_all_obs_gz_file, self.all_obs_gz_file)
         print("Unzipping ", self.all_obs_gz_file)
         os.system("gunzip -k -f " + self.all_obs_gz_file )
         # this will only work for ADMINS with AWS Credentials
      elif local_size < cloud_size:
         print("COPY/UPDATE FILE:", self.cloud_all_obs_gz_file, self.all_obs_gz_file)
         shutil.copyfile(self.cloud_all_obs_gz_file, self.all_obs_gz_file )
         print("Unzipping ", self.all_obs_gz_file )
         os.system("gunzip -k -f " + self.all_obs_gz_file )
      elif local_size >= cloud_size:
         print("Obs are in-sync", local_size, cloud_size)
         print(self.all_obs_file)
         print(self.cloud_all_obs_file)
      else:
         print("FAIL!!!", local_size, cloud_size)
         return()
         # this will only work for ADMINS with AWS Credentials
         #os.system("./DynaDB.py udc " + date)

      #if os.path.exists(self.all_obs_file) is False: 
      #   os.system("./DynaDB.py udc " + date)

      if os.path.exists(self.obs_dict_file) is True: 
         self.obs_dict = load_json_file(self.local_evdir + "/" + self.date + "_OBS_DICT.json")
      else:
         print("NO OBS DICT?!")
         self.obs_dict = {}

      if os.path.exists(self.obs_dict_file) is False or len(self.obs_dict.keys()) == 0:
         print("MAKE OBS DICT")
         self.make_obs_dict()
         self.obs_dict = load_json_file(self.local_evdir + "/" + self.date + "_OBS_DICT.json")
      print("OBS DICT:", len(self.obs_dict))

   def validate_events(self, date):
      event_day = date
      self.min_events_file = self.local_evdir + "/" + date + "_MIN_EVENTS.json"
      self.all_events_file = self.local_evdir + "/" + date + "_ALL_EVENTS.json"
      mc_events = {}
      if os.path.exists(self.min_events_file) is True:
         min_events_data = load_json_file(self.min_events_file)
      else:
         min_events_data = {}
      if os.path.exists(self.all_events_file) is True:
         all_events_data = load_json_file(self.all_events_file)
      else:
         all_events_data = []

      sql_ids = {}
      sql_events = self.sql_select_events(date.replace("_", ""))
      for i in range(0,len(sql_events)):
         ev_id = sql_events[i][0]
         sql_ids[ev_id] = {}

      print("ALL EVENTS   :", len(all_events_data))
      print("MINUTES      :", len(min_events_data))
      ec = 0
      for minute in min_events_data:
         for eid in min_events_data[minute]:
            estime = min_events_data[minute][eid]['stime']
            if "." in estime:
               event_id = estime.split(".")[0]
            else:
               event_id = estime
            event_id = event_id.replace("-", "")
            event_id = event_id.replace(":", "")
            event_id = event_id.replace(" ", "_")
            num_stations = len(set(min_events_data[minute][eid]['stations']))
            if num_stations > 1:
               print(ec, event_id, num_stations)
               mc_events[event_id] = min_events_data[minute][eid]
               ec += 1

      # check the event dirs on local system. remove those not in the mc_events dict 
      local_dirs = []
      temp = os.listdir(self.local_evdir)
      for tt in temp:
         if os.path.isdir(self.local_evdir + tt):
            local_dirs.append(tt)
      cloud_dirs = []
      temp = os.listdir(self.cloud_evdir)
      for tt in temp:
         if os.path.isdir(self.cloud_evdir + tt):
            cloud_dirs.append(tt)

      for ld in local_dirs:
         if ld not in mc_events:
            print("DEL LOCAL DIR:", self.local_evdir + ld)
            os.system("rm -rf " + self.local_evdir + ld)
      for ed in cloud_dirs:
         if ed not in mc_events:
            print("DEL CLOUD DIR:", self.cloud_evdir + ed)
            os.system("rm -rf " + self.cloud_evdir + ed)

      dyna_ids = {}
      for ev in all_events_data:
         ev_id = ev['event_id']
         if ev_id not in mc_events:
            print("DEL DYNAMO EVENT:", ev_id)
            delete_event(self.dynamodb, event_day, ev_id)
         else:
            dyna_ids[ev_id] = ev

      mcc = 0
      for mc_id in mc_events:
         if mc_id not in dyna_ids:
             print(mcc, "ADD EVENT TO DYNAMO:", mc_id)
             self.dyna_insert_meteor_event(event_id, mc_events[mc_id])

             mcc += 1
      print(len(all_events_data), "existing DYNA events")

      for mc_id in mc_events:
         if mc_id not in sql_ids:
            print("MC ID NOT IN LOCAL SQL:", mc_id)
            event = mc_events[mc_id]
            self.insert_event(event)

      for sql_id in sql_ids:
         if sql_id not in mc_events:
            print("SQL ID NOT IN MCE", sql_id)

      
      # check the event dirs on cloud system. remove those not in the mc_events dict 


   def day_coin_events(self,date,force=0):

      self.get_min_obs_dict(date)
      self.plane_file = self.local_evdir + "/" + date + "_PLANE_PAIRS.json"
      self.min_events_file = self.local_evdir + "/" + date + "_MIN_EVENTS.json"
      if os.path.exists(self.plane_file) is True:
         self.plane_pairs = load_json_file(self.plane_file)
      else:
         self.plane_pairs = {}
      self.good_planes = []
      self.bad_planes = []
      self.load_stations_file()
      #for data in self.stations:
      #   print(data.keys())

      sql = """
         SELECT event_minute, count(*) as ccc 
           FROM event_obs 
          WHERE event_minute like ?
       GROUP BY event_minute
      """
      vals = [date+'%']
      self.cur.execute(sql, vals)
      rows = self.cur.fetchall()

      ocounts = {}
      mcm = 0
      for row in rows:
         minute, obs_count = row[0], row[1]
         ocounts[minute] = {}
         ocounts[minute]['count'] = obs_count
         ocounts[minute]['stations'] = []
         ocounts[minute]['obs_ids'] = []
         if obs_count > 1:
            mcm += 1
            print("MIN COUNT:", mcm, minute, obs_count)
      ec = 0
      ecp = 0
      ecf = 0

      all_min_events = {}
      for minute in ocounts:
         #if minute != "2022_03_26_02_55":
         #   continue
         if ocounts[minute]['count'] > 1:
            odata = self.get_station_obs_count(minute)
            print("trying " + str(minute) + "...", len(odata), "stations this minute")

            #min_obs = self.get_obs (minute)
            min_obs = self.min_obs_dict[minute]
            min_events = self.min_obs_to_events(min_obs)
            all_min_events[minute] = min_events
            print("MINUTE OBS:", minute, len(min_obs), len(min_events.keys()))
       



      save_json_file(self.plane_file, self.plane_pairs)
      save_json_file(self.min_events_file, all_min_events)

      c = 0
      for minute in all_min_events:
         print("MINUTE:", minute)
         for event_id in all_min_events[minute]:
            print("EVENT ID :",  event_id)
            event = all_min_events[minute][event_id]
            #ob1, ob2 = key.split("__")
            if len(list(set(event['stations']))) > 1:
               print(c, "FINAL EVENTS:", event)
               self.insert_event(event)
            #score_data = self.score_obs(event['plane_pairs'])
            #for score, key in score_data[0:100]:
            #   ob1, ob2 = key.split("__")
            #   gd = ["GOOD", key, ob1, ob2, event['stime'], "", "", ""]
            #   if len(list(set(event['stations']))) > 1:
            #      self.insert_event(event)
            #   print("Skip single station events.")
            #print(c, "Good planes:", gd[2], gd[3],result[0])
            c += 1
            


   def insert_event(self, event):

      event_id = event['stime'].replace("-", "")
      event_id = event_id.replace(":", "")
      event_id = event_id.replace(" ", "_")
      if "." in event_id:
         event_id = event_id.split(".")[0]
      event['event_id'] = event_id

      print("EVENT:", event)
      event_minute = event['stime'].replace("-", "_")[0:15]
      event_minute = event_minute.replace(":", "_")
      event_minute = event_minute.replace(" ", "_")
      event['event_day'] = event_minute[0:10] 

      print("EVENT ID:", event_id)
      print("EVENT MIN:", event_minute)
      sql = """
          SELECT event_id, event_minute, revision, stations, obs_ids, event_start_time, event_start_times,  
                 lats, lons, event_status, run_date, run_times
            FROM events 
            WHERE event_id = ?
      """

      svals = [event_id]
      self.cur.execute(sql, svals)
      rows = self.cur.fetchall()

      
      if len(rows) == 0:
         print("No events matching this minute exist!", event_minute)
         # make a new event!
         sql = """
            INSERT INTO events (event_id, event_minute, revision, 
                        stations, obs_ids, event_start_time, event_start_times,  
                        lats, lons, event_status, run_date, run_times)
                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
         """
         revision = 1
         run_times = 1
         run_date = datetime.datetime.now().strftime("%Y_%m_%d")

         ivals = [event_id, event_minute, revision, \
                        json.dumps(event['stations']), json.dumps(event['files']), event['stime'], json.dumps(event['start_datetime']),  \
                        json.dumps(event['lats']), json.dumps(event['lons']), "PENDING", run_date, run_times]
         print("ADD NEW EVENT!", event_id, len(ivals))
         self.cur.execute(sql, ivals)
         self.con.commit()



      else:
         updated_existing = False
         if True:
            #(status, pair, obs1_id, obs2_id, station_dist, obs1_datetime, obs2_datetime, time_diff) = gd
            (event_id, event_minute, revision, stations, obs_ids, event_start_time, event_start_times, \
                 lats, lons, event_status, run_date, run_times) = rows[0]



            stations = json.loads(stations)
            obs_ids = json.loads(obs_ids)
            event_start_times= json.loads(event_start_times)
            lats = json.loads(lats)
            lons = json.loads(lons)

            ivals = [event_minute, revision, json.dumps(stations), json.dumps(obs_ids), json.dumps(event_start_times), \
                 json.dumps(lats), json.dumps(lons), event_status, run_date, run_times, event_id]
            self.update_event(ivals) 

      print("DONE")

   def update_event(self, ivals):
      c= 0
      for iv in ivals:
         print(iv, type(iv))
         c += 1
      sql = """UPDATE events SET
                    event_minute = ?, 
                    revision = ?,
                    stations = ?,
                    obs_ids = ?, 
                    event_start_times = ?, 
                    lats = ?, 
                    lons = ?, 
                    event_status = ?, 
                    run_date = ?, 
                    run_times = ?
             WHERE event_id = ?
      """
      print(sql)
      print(ivals)
      self.cur.execute(sql,ivals)
      self.con.commit()

   def OLD_avg_times(self, datetimes):
      times = []

   def run_plane_jobs_OLDER(self, jobs):
      for dt in datetimes:
         timestamp = datetime.datetime.timestamp(dt)
         times.append(timestamp)
      avg_time = np.mean(times)
      avg_datetime = datetime.datetime.fromtimestamp(avg_time)
      return(avg_datetime)

   def plane_test_min_events(self, min_events):

      #plane test all events in this minute
      pc = 0
      print("Plane testing...")
      for me in min_events:
         print("EVENT:", me)
         min_events[me]['plane_pairs'] = {}
         for i in range(0, len(min_events[me]['stations'])):
            st_1 = min_events[me]['stations'][i]
            obs_file_1 = min_events[me]['files'][i]
            for j in range(0, len(min_events[me]['stations'])):
               st_2 = min_events[me]['stations'][j]
               if st_1 == st_2:
                  # skip obs where both obs's station are the same 
                  continue

               obs_file_2 = min_events[me]['files'][j]
               key = "__".join(sorted([obs_file_1, obs_file_2]))
               if key not in  min_events[me]['plane_pairs'] :
                  gd = ["GOOD", key, obs_file_1, obs_file_2]
                  result = self.plane_solve(gd)
                  if len(result) == 2:
                     res, sanity = result
                  else:
                     res = {}
                     sanity = 0
                  #print(pc, obs_file_1, obs_file_2 )
                  #print(res, sanity)
                  min_events[me]['plane_pairs'][key] = [res, sanity]
                  pc += 1
               print("\r" + str(pc) , end="")

      #save_json_file("min_events.json", min_events)
      return(min_events)

      #good.append(("(GOOD)", key, obs_id_1, obs_id_2, station_dists[key]['min_dist'], start_time_1, start_time_2, time_diff))

   def plane_solve(self, gd ):
      # ONLY GD2, GD3 ARE USED
      # GD2 = OBS1_ID
      # GD3 = OBS2_ID

      obs1_data = self.get_obs(gd[2])
      st1 = gd[2].split("_")[0]
      st2 = gd[3].split("_")[0]

  

      obs2_data = self.get_obs(gd[3])
      obs1_id = gd[2]
      obs2_id = gd[3]
      plane_pair = obs1_id + "__" + obs2_id

      if plane_pair in self.plane_pairs:
         print("DONE ALREADY!")
         (res, sanity) = self.plane_pairs[plane_pair]
         return(res,sanity)

      lat1 = float(self.station_dict[st1]['lat'])
      lon1 = float(self.station_dict[st1]['lon'])
      alt1 = float(self.station_dict[st1]['alt'])
      lat2 = float(self.station_dict[st2]['lat'])
      lon2 = float(self.station_dict[st2]['lon'])
      alt2 = float(self.station_dict[st2]['alt'])

      obs1_data = obs1_data[0]
      obs2_data = obs2_data[0]
      #print("OBS1 DATA:", obs1_data)
      azs1 = obs1_data[8]
      els1 = obs1_data[9]
      if azs1 != "":
         azs1 = json.loads(azs1)
      else:
         azs1 = []
      if els1 != "":
         els1 = json.loads(els1)
      else:
         els1 = []

      azs2 = obs2_data[8]
      els2 = obs2_data[9]
      if azs2 != "":
         azs2 = json.loads(azs2)
      else:
         azs2 = []
      if els2 != "":
         els2 = json.loads(els2)
      else:
         els2 = []

      if len(azs1) > 1:
         az1_start = azs1[0]
         az1_end= azs1[-1]
         el1_start = els1[0]
         el1_end= els1[-1]
      else:

         ivals = [plane_pair, "FAILED", 5, 0, 0, 0, 0, 0, 0]
         self.insert_plane_pair(ivals)

         return([])

      if len(azs2) > 1:
         az2_start = azs2[0]
         az2_end= azs2[-1]
         el2_start = els2[0]
         el2_end= els2[-1]
      else:
         return([])

      obs1 = (float(lat1), float(lon1), float(alt1), float(az1_start), float(el1_start), float(az1_end),float(el1_end))

      obs2 = (float(lat2), float(lon2), float(alt2), float(az2_start), float(el2_start), float(az2_end),float(el2_end))

      try:
         res = intersecting_planes(obs1,obs2)
         #print(res)
      except:
         #print("failed to solve")
         res = []
         return(res)

      # do some sanity checks on the solution 
      # to determine if it is valid or not
      if len(res) < 2:
         return(res)
      track_start_dist1 = dist_between_two_points(float(lat1), float(lon1), float(res[0][0]), float(res[0][1]))
      track_end_dist1 = dist_between_two_points(float(lat1), float(lon1), float(res[-1][0]), float(res[-1][1]))

      track_start_dist2 = dist_between_two_points(float(lat2), float(lon2), float(res[0][0]), float(res[0][1]))
      track_end_dist2 = dist_between_two_points(float(lat2), float(lon2), float(res[-1][0]), float(res[-1][1]))

      track_length = dist_between_two_points(float(res[0][0]), float(res[0][1]), float(res[-1][0]), float(res[-1][1]))

      sanity = 0
      if track_start_dist1 > 500:
         sanity+= 1
      if track_end_dist1 > 500:
         sanity+= 1
      if track_start_dist2 > 500:
         sanity+= 1
      if track_end_dist2 > 500:
         sanity+= 1
      if track_length > 500:
         sanity+= 1

      # INSERT INTO DB
      if sanity < 2:
         status = "GOOD"
      else: 
         status = "BAD"
      ivals = [plane_pair, status, sanity, float(res[0][0]), float(res[0][1]), float(res[0][2]), float(res[-1][0]), float(res[-1][1]), float(res[-1][2])]
      self.insert_plane_pair(ivals)
      self.plane_pairs[plane_pair] = res, sanity

      return(res, sanity)

   def insert_plane_pair(self,ivals):
      return()
      sql = """
         INSERT OR REPLACE INTO event_planes (plane_pair, status, sanity, 
            start_lat, start_lon, start_alt, end_lat, end_lon, end_alt)
         VALUES (?,?,?,?,?,?,?,?,?)
      """
      self.cur.execute(sql,ivals)
      self.con.commit()
     
      table = """
       CREATE TABLE IF NOT EXISTS "event_planes" (
        "plane_pair"      TEXT,
        "status"      TEXT,
        "sanity"      INTEGER,
        "start_lat"      REAL,
        "start_lon"      REAL,
        "start_alt"      REAL,
        "end_lat"      REAL,
        "end_lon"      REAL,
        "end_alt"      REAL,
        PRIMARY KEY("plane_pair")
       );
      """


   def average_times(self, times):
      tt = []
      for stime in times:
         s_datestamp, s_timestamp = self.date_str_to_datetime(stime)
         tt.append(s_timestamp)
      avg_time = np.median(tt)
      dt = datetime.datetime.fromtimestamp(avg_time)
      dt_str = dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
      return(dt_str)

 
   def check_make_events(self, min_events, station_id, obs_file, stime):
      # see if this one obs is part of an event or new
      match_time = 0
      match_dist = 0
      matches = []
      lat = float(self.station_dict[station_id]['lat'])
      lon = float(self.station_dict[station_id]['lon'])
      alt = float(self.station_dict[station_id]['alt'])

      if len(min_events.keys()) == 0:
         eid = 1
         # first event
         min_events[eid] = {}
         min_events[eid]['stations'] = []
         min_events[eid]['lats'] = []
         min_events[eid]['lons'] = []
         min_events[eid]['alts'] = []
         min_events[eid]['files'] = []
         min_events[eid]['start_datetime'] = []
         min_events[eid]['stations'].append(station_id)
         min_events[eid]['lats'].append(lat)
         min_events[eid]['lons'].append(lon)
         min_events[eid]['alts'].append(alt)
         min_events[eid]['files'].append(obs_file)
         min_events[eid]['start_datetime'].append(stime)
         min_events[eid]['stime'] = stime
         return(min_events)
      else:
         # there are some events for this minute already.
         # loop over all and see if this event's time and distance is in range enough to be considered.
         for eid in min_events:
            this_time = min_events[eid]['stime']
            s_datestamp, s_timestamp = self.date_str_to_datetime(stime)
            t_datestamp, t_timestamp = self.date_str_to_datetime(this_time)
            time_diff = s_timestamp - t_timestamp
            #if the event start is within 3 seconds
            if -6 <= time_diff <= 6:
               avg_lat = np.mean(min_events[eid]['lats'])
               avg_lon = np.mean(min_events[eid]['lons'])
               match_dist = dist_between_two_points(avg_lat, avg_lon, lat, lon)
               #print("Time diff in range. Check Distance??", time_diff, match_dist)
               #if the dist between avg stations and this station is < 900 km
               match_time = 1
               if match_dist < 900:
                  match_dist = 1



                  # before adding we should see if the points intersect!? or no?
                  matches.append((eid, match_time, match_dist))
      if len(matches) > 0:
         eid = matches[0][0]
         #if len(matches) == 1:
         #   print("We found a matching event. Add this obs to that event!")
         #else:
         #   print("We found MORE THAN ONE matching event. Pick the best one! How???")
         min_events[eid]['stations'].append(station_id)
         min_events[eid]['lats'].append(lat)
         min_events[eid]['lons'].append(lon)
         min_events[eid]['alts'].append(alt)
         min_events[eid]['files'].append(obs_file)
         min_events[eid]['start_datetime'].append(stime)
         avg_time = self.average_times(min_events[eid]['start_datetime'])
         min_events[eid]['stime'] = avg_time
      else:
         #print("we could not find a matching event. We should add a new one.")
         eid = max(min_events.keys()) + 1 
         # first event
         min_events[eid] = {}
         min_events[eid]['stations'] = []
         min_events[eid]['lats'] = []
         min_events[eid]['lons'] = []
         min_events[eid]['alts'] = []
         min_events[eid]['files'] = []
         min_events[eid]['start_datetime'] = []
         min_events[eid]['stations'].append(station_id)
         min_events[eid]['lats'].append(lat)
         min_events[eid]['lons'].append(lon)
         min_events[eid]['alts'].append(alt)
         min_events[eid]['files'].append(obs_file)
         min_events[eid]['start_datetime'].append(stime)
         min_events[eid]['stime'] = stime
         return(min_events)

      return(min_events)

   def date_str_to_datetime(self, date_str):
      if "." in date_str:
         dt = datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S.%f") 
      else:
         dt = datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S") 
      ts = datetime.datetime.timestamp(dt)
      return(dt, ts)

   def min_obs_to_events(self, min_obs):
      # This is where we group obs into events! 
      # IT should be close in time and distance
      # and the lines should intersect 

      station_dists = {}
      #   SELECT station_id, event_id, event_minute, obs_id, fns, times, xs, ys, azs, els, ints, status, ignore 

      min_events = {}

      for obs in min_obs:
         times = json.loads(obs[5])
         if len(times) > 0:
            stime = times[0]
         else:
            stime = None
         obs_file = obs[3]
         station_id = obs[0]
         if stime is None:
            #print("NO REDUCTION!", station_id, obs[3])
            continue
         try:
            lat = float(self.station_dict[station_id]['lat'])
            lon = float(self.station_dict[station_id]['lon'])
            alt = float(self.station_dict[station_id]['alt'])
         except:
            print("NEW SITE ERROR!")
            continue
         point = lat * lon
         dd, tt = stime.split(" ")
         sec = tt.split(":")[-1]
         sec = float(sec)
         print(station_id, obs_file, point, stime, sec)
         min_events = self.check_make_events(min_events, station_id, obs_file, stime)


      #print("MIN EVENTS:")
      # maybe re-enable this later, but it takes too much time now
      # should be parallel process later?
      #min_events = self.plane_test_min_events(min_events)

      #for me in min_events:
      #   print("MIN EVENT:", me)
      #   print(" Stations:", len(min_events[me]['stations']))
         #print("   Planes:", len(min_events[me]['plane_pairs']))
      #   print("      Obs:", len(min_events[me]['files']))

      # good.append(("(GOOD)", key, obs_id_1, obs_id_2, station_dists[key]['min_dist'], start_time_1, start_time_2, time_diff))

      return(min_events)

      # BELOW HERE DOESN'T MATTER ANYMORE
      return()
      for mo_1 in min_obs:
                 
         station_id_1 = mo_1[0]
         obs_id_1 = mo_1[3]
         times_1 = mo_1[5]
         lat_1 = float(self.station_dict[station_id_1]['lat'])
         lon_1 = float(self.station_dict[station_id_1]['lon'])
         if times_1 == "":
            start_time_1 = starttime_from_file(obs_id_1.replace(station_id_1 + "_", ""))
         else:
            times_1 = json.loads(times_1)
            if len(times_1) > 0:
               start_time_1 = times_1[0]
               start_time_1 = datetime.datetime.strptime(start_time_1, "%Y-%m-%d %H:%M:%S.%f")
            else:
               start_time_1 = starttime_from_file(obs_id_1.replace(station_id_1 + "_", ""))

         for mo_2 in min_obs:
            station_id_2 = mo_2[0]
            obs_id_2 = mo_2[3]
            times_2 = mo_2[5]
            if station_id_1 == station_id_2:
               continue
            key = "-".join(sorted([station_id_1, station_id_2]))
            lat_2 = float(self.station_dict[station_id_2]['lat'])
            lon_2 = float(self.station_dict[station_id_2]['lon'])
            if times_2 == "":
               start_time_2 = starttime_from_file(obs_id_2.replace(station_id_2 + "_", ""))
            else:
               times_2 = json.loads(times_2)
               if len(times_2) > 0:
                  start_time_2 = times_2[0]
                  start_time_2 = datetime.datetime.strptime(start_time_2, "%Y-%m-%d %H:%M:%S.%f")
               else:
                  start_time_2 = starttime_from_file(obs_id_2.replace(station_id_2 + "_", ""))


            if key not in station_dists:
               min_dist = dist_between_two_points(lat_1,lon_1, lat_2, lon_2)
               station_dists[key] = {}
               station_dists[key]['obs_id_1'] = obs_id_1 
               station_dists[key]['obs_id_2'] = obs_id_2
               station_dists[key]['min_dist'] = min_dist
               station_dists[key]['start_time_1'] = start_time_1 
               station_dists[key]['start_time_2'] = start_time_2
               time_diff = abs((start_time_1 - start_time_2).total_seconds())
               station_dists[key]['time_diff'] = time_diff 

      good = []
      bad = []

      for key in station_dists:
         time_diff = station_dists[key]['time_diff'] 
         start_time_1 = station_dists[key]['start_time_1'] 
         start_time_2 = station_dists[key]['start_time_2'] 
         obs_id_1 = station_dists[key]['obs_id_1'] 
         obs_id_2 = station_dists[key]['obs_id_2'] 

         if station_dists[key]['min_dist'] < 1400:
            if time_diff > 5:
               bad.append(("(BAD TIME)", key, station_dists[key]['min_dist'], start_time_1, start_time_2, time_diff))
            else:
               good.append(("(GOOD)", key, obs_id_1, obs_id_2, station_dists[key]['min_dist'], start_time_1, start_time_2, time_diff))
         else:
            bad.append(("(BAD DIST)", key, station_dists[key]['min_dist'], start_time_1, start_time_2, time_diff))

      print("MINUTE GOOD/BAD EVENTS:", len(good), len(bad))
      return(good, bad)

   def get_min_obs_dict(self, date):
      self.min_obs_dict = {}
      sql = """
         SELECT station_id, event_id, event_minute, obs_id, fns, times, xs, ys, azs, els, ints, status, ignore 
           FROM event_obs
          WHERE obs_id like ?
      """
      vals = ["%" + date + "%"]
      self.cur.execute(sql, vals)
      rows = self.cur.fetchall()
      for row in rows:
         station_id, event_id, event_minute, obs_id, fns, times, xs, ys, azs, els, ints, status, ignore = row
         if event_minute not in self.min_obs_dict:
            self.min_obs_dict[event_minute] = []
         self.min_obs_dict[event_minute].append((station_id, event_id, event_minute, obs_id, fns, times, xs, ys, azs, els, ints, status, ignore))

   def get_obs(self, wild):   
      if wild in self.obs_dict:
         return((self.obs_edict[wild]))
      obs_data = []
      sql = """
         SELECT station_id, event_id, event_minute, obs_id, fns, times, xs, ys, azs, els, ints, status, ignore 
           FROM event_obs
          WHERE obs_id like ?
      """
      vals = ["%" + wild + "%"]
      #print(sql, vals)
      self.cur.execute(sql, vals)
      rows = self.cur.fetchall()
      for row in rows:
         station_id, event_id, event_minute, obs_id, fns, times, xs, ys, azs, els, ints, status, ignore = row
         obs_data.append((station_id, event_id, event_minute, obs_id, fns, times, xs, ys, azs, els, ints, status, ignore))
      return(obs_data)

   def get_all_obs(self, wild):   
      obs_data = []
      self.obs_edict = {}
      sql = """
         SELECT station_id, event_id, event_minute, obs_id, fns, times, xs, ys, azs, els, ints, status, ignore 
           FROM event_obs
          WHERE obs_id like ?
      """
      vals = ["%" + wild + "%"]
      #print(sql, vals)
      self.cur.execute(sql, vals)
      rows = self.cur.fetchall()
      for row in rows:
         station_id, event_id, event_minute, obs_id, fns, times, xs, ys, azs, els, ints, status, ignore = row
         fns = json.loads(fns)
         times = json.loads(times)
         xs = json.loads(xs)
         ys = json.loads(ys)
         azs = json.loads(azs)
         els = json.loads(els)
         ints = json.loads(ints)
         obs_data.append((station_id, event_id, event_minute, obs_id, fns, times, xs, ys, azs, els, ints, status, ignore))
         self.obs_edict[obs_id] = ((station_id, event_id, event_minute, obs_id, fns, times, xs, ys, azs, els, ints, status, ignore))
      return(obs_data)
          

   def get_station_obs_count(self, wild):
      odata = []
      # get unq station count for the minute
      sql = """
         SELECT station_id, count(*)
           FROM event_obs
          WHERE obs_id LIKE ?
       GROUP BY station_id 
      """
      vals = ["%" + wild + "%"]
      self.cur.execute(sql, vals)
      rows = self.cur.fetchall()
      for row in rows:
         station_id, obs_count = row
         #event_id, event_minute, station_id, obs_id, fns, times, xs, ys, azs, els, ints, status, ignore = row
         odata.append((station_id, obs_count))
      return(odata)

   def day_load_sql(self, date,force=0):
      # for 1 day, take available data from : Dynamo, Local File System, Cloud File System
      # and then populate the sqlite table for that day so we can quickly navigate/publish or reconcile
      table = """
        CREATE TABLE IF NOT EXISTS "event_obs" (
        "event_id"      TEXT,
        "event_minute"      TEXT,
        "station_id"     ,
        "obs_id"     TEXT UNIQUE,
        "fns" TEXT,
        "times" TEXT,
        "azs"   TEXT,
        "els"   TEXT,
        "ints"  TEXT,
        "status"        TEXT,
        "ignore"        INTEGER,
        PRIMARY KEY("obs_id")
       );
      """
      print(self.allsky_console)
      self.set_dates(date)
      # load all obs from the available ALL OBS file

      if os.path.exists(self.all_obs_file) is True: 
         self.all_obs = load_json_file(self.all_obs_file)
      ic = 0
      print("Inserting all obs")
      for obs in self.all_obs:
         # dict_keys(['dur', 'station_id', 'peak_int', 'hd_video_file', 'hd_roi', 'last_update', 
         # 'roi', 'sd_video_file', 'sync_status', 'ffp', 'meteor_frame_data', 'event_start_time', 'calib', 'event_id', 'hc']) 
         # dt, fn, x, y, w, h, oint, ra, dec, az, el
         # set the initial event_id to the minute of the capture


         temp_ev_id = obs['sd_video_file'][0:16]
         datetimes = [row[0] for row in obs['meteor_frame_data']]
         fns = [row[1] for row in obs['meteor_frame_data']]
         xs = [row[2] for row in obs['meteor_frame_data']]
         ys = [row[3] for row in obs['meteor_frame_data']]
         ints = [row[6] for row in obs['meteor_frame_data']]
         azs = [row[9] for row in obs['meteor_frame_data']]
         els = [row[10] for row in obs['meteor_frame_data']]
         sql = """INSERT OR REPLACE INTO event_obs 
                            (event_id, event_minute, station_id, obs_id, 
                             fns, times, xs, ys, azs, els, ints, status, ignore)
                  VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
               """
         obs_id = obs['station_id'] + "_" + obs['sd_video_file'].replace(".mp4", "")

         ivals = [0,temp_ev_id,obs['station_id'],obs_id, json.dumps(fns), json.dumps(datetimes), json.dumps(xs), json.dumps(ys), json.dumps(azs), json.dumps(els), json.dumps(ints), 0,0]
         self.cur.execute(sql, ivals)
         #print("INSERT", sql)
         #print("VALUES", ivals)
         ic += 1

      self.con.commit()

      print("\rTotal OBS for " + date + " : " + str(len(self.all_obs)) + "                                        ",end="")
      print("")


      
   def event_id_to_date(self, event_id):
      year = event_id[0:4]
      mon = event_id[4:6]
      day = event_id[6:8]
      date = year + "_" + mon + "_" + day
      return(date)

      

   def resolve_failed_day(self, event_day):
      sql = """
            SELECT event_id, event_minute, revision, stations, obs_ids, event_start_time, event_start_times,
                   lats, lons, event_status, run_date, run_times
              FROM events
             WHERE event_id like ?
               AND event_status like 'FAIL%'
               AND run_times < 4 
          ORDER BY event_id desc
      """
      vals = [event_day + '%']
      self.cur.execute(sql, vals)
      rows = self.cur.fetchall()
      print("ROWS:", len(rows))
      for row in rows:
         event_id = row[0]
         print("Resolving:", event_id)
         self.resolve_event(event_id)

   def show_edits(self):
      for sd_vid in self.edits['sd_clips']:
         print("EDIT:", self.edits['sd_clips'][sd_vid]['status'], sd_vid, self.edits['sd_clips'][sd_vid].keys())

   def purge_invalid_events(self, event_day):
      self.set_dates(event_day)
      ev_dirs = os.listdir(self.local_evdir )

      invalid_event_file = self.local_evdir + "/" + event_day + "_INVALID_EVENTS.json"
      if os.path.exists(invalid_event_file) is True: 
         invalid_events = load_json_file(invalid_event_file)
      else:
         invalid_events = {}

      for evd in ev_dirs:
         if os.path.isdir(self.local_evdir + evd):
            if os.path.exists(self.local_evdir + evd + "/" + evd + "-fail.json") and os.path.exists(self.local_evdir + evd + "/" + evd + "-event.json") is False:
               print("Failed file found with no event file found for :", evd)
               if os.path.exists(self.local_evdir + evd + "/" + evd + "_GOOD_OBS.json") :
                  # make sure there are actually good obs for this file. If there are not at least 2 then the event is invalid! 
                  good_obs = load_json_file(self.local_evdir + evd + "/" + evd + "_GOOD_OBS.json")
                  gdso = 0
                  for station in good_obs: 
                     go = 0
                     for key in good_obs[station]:
                        go+= 1
                     if go >= 1:
                        gdso += 1

                  if gdso == 0:
                     print("THERE ARE NO GOOD OBS FOR THIS EVENT IT SHOULD BE DELETED!", evd)
                     invalid_events[evd] = 1
                     cmd = "rm -rf " + self.local_evdir + evd
                     print(cmd)
                     os.system(cmd)
      for event_id in invalid_events:
         sql = "DELETE FROM EVENTS WHERE event_id = ?"
         print(sql)
         self.cur.execute(sql, [event_id])
      self.con.commit()
      save_json_file(self.local_evdir + "/" + event_day + "_INVALID_EVENTS.json", invalid_events)

   def quick_day_status(self, event_day):
      print("Quick event stats!")
      obs_dict = load_json_file(self.obs_dict_file)
      all_obs = load_json_file(self.all_obs_file)
      min_events = load_json_file(self.min_events_file)
      all_events = load_json_file(self.all_events_file)
      db_events = {}
      sql = """
         SELECT event_id,stations from events order by event_id 
      """
      self.cur.execute(sql)
      rows = self.cur.fetchall()
      for row in rows:
         event_id = row[0]
         print(row[0], row[1])
         db_events[event_id] = {}


      print("ALL OBS", len(all_obs))
      print("OBS DICT", len(obs_dict.keys()))
      print("MINUTE EVENTS", len(min_events.keys()))
      print("ALL EVENTS", len(all_events))
      print("DB EVENTS", len(db_events.keys()))

      all_good_events = []
      for data in all_events:
         if len(set(data['stations'])) >= 2:
         #   print("GOOD", len(data['stations']), data['event_id'], data['solve_status'], data.keys())
            all_good_events.append(data)
         #else:
         #   print("BAD", len(data['stations']), data['event_id'], data['solve_status'], data.keys())
      if len(all_good_events) != len(all_events):
         print("SAVE ALL EVENT FILE.")
         save_json_file(self.all_events_file, all_good_events)

   def event_day_status(self, event_day):
      self.set_dates(event_day)
      self.load_stations_file()

      event_day_stats = self.sql_select_event_day_stats(self.date)

      by_station = """
      <table>
         <thead>
            <tr>
               <th>
                  Meteor Obs
               </th>
               <th>
                  Station 
               </th>
               <th>
                  Operator Info 
               </th>
            </tr>
         </thead>
         <tbody>
      """

      for row in event_day_stats["by_station"]:
         st, cc = row
         if st not in self.photo_credits:
            self.photo_credits[st] = "unknown"
         by_station += "<tr><td> {:s}</td><td> {:s}</td><td> {:s}</td></tr>".format(str(cc), st, self.photo_credits[st])
      by_station += "</tbody></table>"
      event_dict = {} 

      good = """
      <table>
         <thead>
            <tr>
               <th>
                  Event ID 
               </th>
               <th>
                  2D Intersections 
               </th>
               <th>
                  3D Planes 
               </th>
               <th>
                  WMPL Status 
               </th>
               <th>
                  AI Meteors 
               </th>
            </tr>
         </thead>
         <tbody>
      """
      for ev_data in event_day_stats["all_events"]:
         event_id, event_status, event_data = ev_data
         good += "<tr><td>{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td></tr> ".format(event_id, "", "", event_status, "")

         #solve_file = self.local_evdir + ev + "/" + ev + "-event.json" 
         print("DATA", ev_data)



      good += "</tbody></table>"


      out_file = self.local_evdir + "/" + event_day + "_log.html"

      self.all_obs_file = self.local_evdir + self.date + "_ALL_OBS.json"

      self.all_events_file = self.local_evdir + self.date + "_ALL_EVENTS.json"
      if os.path.exists(self.all_obs_file):
         all_obs = load_json_file(self.all_obs_file)
      else:
         all_obs = {}

      if os.path.exists(self.all_events_file):
         all_events = load_json_file(self.all_events_file)
      else:
         all_events = {}

      stats = ""
      for key in event_day_stats:
         if stats != "":
            stats += " AND " 
         stats += str(event_day_stats[key]) + " " + str(key) + " events "
         
      report = """
      <html lang="en-US">
         <head>
              <meta charset="UTF-8" />
              <meta name="viewport" content="width=device-width, initial-scale=1.0" />
              <meta http-equiv="X-UA-Compatible" content="ie=edge" />
              <meta name="msapplication-TileColor" content="#ffffff" />
              <meta name="msapplication-TileImage" content="/favicon/ms-icon-144x144.png" />
              <meta name="theme-color" content="#ffffff" /> <title>ALLSKY7 {:s} REPORT</title>
              <meta name="description" content="A modern and minimal CSS framework for terminal lovers."/>
        </head>
        <link rel="stylesheet" href="https://unpkg.com/terminal.css@0.7.2/dist/terminal.min.css" />
        <body class="terminal">
        <div class="container">
            <h1>AllSky7 Event Report for {:s}</h1>
            <section>

               <div class="terminal-card">
               <header>Database Reconciliation</header>
                  The network database contains {:s} observations spanning {:s} events. <br>
                  The solving node database database contains {:s} successful events, {:s} failed events and {:s} total observations.
                  
               </div>

               <div class="terminal-card">
               <header>Obs By Station</header>
               {:s}
               </div>

               <div class="terminal-card">
               <header>All Multi-Station Events</header>
               {:s}
               </div>




            </section>
         </body>
      </html>
      """.format(event_day, event_day, str(len(all_obs)), str(len(all_events)), str(event_day_stats['STATUS_SOLVED']), str(event_day_stats['STATUS_FAILED']), str(event_day_stats['TOTAL_OBS']), by_station, good )

      print(report)
      out = open( out_file, "w")
      out.write(report)
      print(out_file)

       
   def resolve_event_day(self, event_day):
      temp = load_json_file("cores.json")
      cores = temp['cores']
      self.set_dates(event_day)
      self.quick_day_status(event_day)
      sql = """
         SELECT event_id from events order by event_id 
      """
      self.cur.execute(sql)
      rows = self.cur.fetchall()
      for row in rows:
         running = check_running("python")

         while running > 32:
            print("Wait 10 seconds, already have", running, "processes")
            time.sleep(10)
            running = check_running("python")
            
         event_id = row[0]
         # if it has already solved or failed skip it
         ev_file = self.local_evdir + event_id + "/" + event_id + "_REVIEW.jpg"
         if os.path.exists(ev_file) is False:
            cmd = "/usr/bin/python3 AllSkyNetwork.py resolve_event " + event_id + " > /dev/null 2>&1 &" 
            print(cmd)
            os.system(cmd)


   def review_event_day(self, event_day):
      self.set_dates(event_day)
      self.quick_day_status(event_day)
      #self.obs_timeline (event_day)
      if os.path.exists(self.sync_log_file):
         self.sync_log = load_json_file(self.sync_log_file)
      else:
         self.sync_log = {}
       
      sql = """
         SELECT event_id from events order by event_id 
      """
      self.cur.execute(sql)
      rows = self.cur.fetchall()
      all_cmds = []
 
      print(len(rows), " events on this day", event_day)
      print("Sync'ing media please wait...")
      if True:
         for row in rows:
            event_id = row[0]
            wget_cmds = self.get_event_media(event_id)
            all_cmds.extend(wget_cmds)
         all_cmds = sorted(all_cmds)

         print("Fetching media:", len(all_cmds))
         self.fast_cmds(all_cmds)
         save_json_file(self.sync_log_file, self.sync_log)

      print("All media downloaded. Ready to review events.")

      #exit()
      for row in rows:
         event_id = row[0]
         print("Get event media for :", event_id)
         wget_cmds = self.get_event_media(event_id)
         self.review_event(event_id)

         (review_image, map_img, obs_imgs, marked_images, event_data, obs_data) = self.review_event_step2()

         if "2d_status" not in event_data:
            event_data = self.get_2d_status(event_data, obs_data)



         self.echo_event_data(event_data, obs_data)  

         #cv2.imshow("pepe", map_img)
         #cv2.waitKey(0)
         event_data_file = self.local_evdir + self.event_id + "/" + self.event_id + "_EVENT_DATA.json"
         obs_data_file = self.local_evdir + self.event_id + "/" + self.event_id + "_OBS_DATA.json"
         save_json_file(event_data_file, event_data)
         save_json_file(obs_data_file, obs_data, True)

         if review_image is not None:
            cv2.imshow("pepe", review_image)
            cv2.waitKey(150)
         else:
            print("REVIEW IMAGE IS NONE!", review_image)


   def get_event_media(self, event_id):

      event_day = self.event_id_to_date(event_id)
      self.event_id = event_id
      self.edits_file = self.local_event_dir + self.event_id + "_EDITS.json"
      if os.path.exists(self.edits_file) is True:
         self.edits = load_json_file(self.edits_file)
      else:
         self.edits = {}
         self.edits['sd_clips'] = {} 

      self.show_edits()

      #print("Loaded:", self.edits_file)

      #if "sd_clips" in self.edits:
      #   for sd_vid in self.edits['sd_clips']:
      #      if "deleted_points" in self.edits['sd_clips'][sd_vid]:
      #         print("DEL:", self.edits['sd_clips'][sd_vid]['deleted_points'])
      #      if "custom_points" in self.edits['sd_clips'][sd_vid]:
      #         print("CUS:", self.edits['sd_clips'][sd_vid]['deleted_points'])

      #print("EDITS:", self.edits['sd_clips'].keys())

      #cv2.namedWindow('pepe')
      #cv2.resizeWindow("pepe", 1920, 1080)
      #cv2.moveWindow("pepe", 1400,100)
      #self.RF = RenderFrames()


      #sd = load_json_file("stations.json")
      #rurls = {}
      #for data in sd['stations']:
      #   station = data['name']
      #   url = data['url']
      #   rurls[station] = url

      event_day = self.event_id_to_date(event_id)
      self.year = event_day[0:4]
      self.month = event_day[5:7]
      self.dom = event_day[8:10]
      self.date = self.year + "_" + self.month + "_" + self.dom
      


      self.sd_clips = {}

      # load event related files
      review_data = {}
      review_data['cloud_files'] = []
      local_event_dir = "/mnt/f/EVENTS/" + self.year + "/" + self.month + "/" + self.dom + "/" + self.event_id + "/" 
      self.ev_dir = local_event_dir 
      #self.local_event_dir = local_event_dir 
      event_file = self.ev_dir + event_id + "-event.json"
      good_obs_file = self.ev_dir + event_id + "_GOOD_OBS.json"
      planes_file = self.ev_dir + event_id + "_PLANES.json"

      event_data, obs_data, planes_data = None,None,None
      if os.path.exists(event_file):
         event_data = load_json_file(event_file)
      if os.path.exists(good_obs_file):
         obs_data = load_json_file(good_obs_file)
      if os.path.exists(planes_file):
         planes_data = load_json_file(planes_file)

      #if event_data is not None:
         #print("Event")
      #   for key in event_data:
            #print("   ", key)
      #      if key == "traj" or key == "orb" or key == "rad" or key == "plot" or key == "shower":
      #         for skey in event_data[key]:
      #            print("   ", key, skey)
      #else:
      #   print("none for event_data")

      # now if there are any saved edits apply them to the data set. Then we will be ready to work on the file!

      #for sd_vid in self.edits['sd_clips']:
      #   print(sd_vid, self.edits['sd_clips'][sd_vid].keys())

      #if "sd_clips" in self.edits:
      #   for sd_vid in self.edits['sd_clips']:
      #      if sd_vid in self.edits['sd_clips']:
      #         print("LOADING EDITS FOR :", sd_vid)
      #         self.sd_clips[sd_vid] = self.edits['sd_clips'][sd_vid]
      #      else:
      #         print("NO EDITS FOR :", sd_vid)

      # Syncronize source media from host station or allsky archive
      missing_files = []
      wget_cmds = []
      if obs_data is not None:
         for station in obs_data:
            print(station)
            cloud_meteor_dir = "/mnt/archive.allsky.tv/" + station + "/METEORS/" + self.year + "/" + self.date + "/" 
            cloud_files_file = local_event_dir + station + "_CLOUDFILES.json"
            cloud_cal_dir = "/mnt/archive.allsky.tv/" + station + "/CAL/" 




            if os.path.exists(cloud_files_file) is False:
               cloud_files = os.listdir(cloud_meteor_dir) 
               save_json_file(cloud_files_file, cloud_files)
            else:
               cloud_files = load_json_file(cloud_files_file)

            for ofile in obs_data[station]:
               skip_remote = 0
               base_str = ofile.replace(".mp4", "")
               obs_id = station + "_" + ofile
               out_file = station + "_" + ofile
               if obs_id in self.sync_log:
                  self.sd_clips[out_file] = {} 
                  self.sd_clips[out_file]['status'] = True
                  continue

               if station in self.rurls:
                  rmp4 = self.rurls[station] + "/meteors/" + self.date +  "/" + ofile
               else:
                  skip_remote = 1
               # get the SD MP$
               out_file = station + "_" + ofile
               json_file = ofile.replace(".mp4", ".json")
               red_json_file = ofile.replace(".mp4", "-reduced.json")

               out_json_file = station + "_" + json_file
               out_red_json_file = station + "_" + red_json_file

               if skip_remote == 0:
                  rjson = self.rurls[station] + "/meteors/" + self.date +  "/" + json_file 
                  rred= self.rurls[station] + "/meteors/" + self.date +  "/" + red_json_file 

        
               # POOLING WGETS! 

               # REMOTE JSON FILE
               #if skip_remote == 0 and os.path.exists( local_event_dir + "/" + out_json_file) is False and \
               #        os.path.exists( local_event_dir + "/" + out_json_file + ".failed") is False:
               #   cmd = "wget " + rjson + " --timeout=1 --waitretry=0 --tries=1 --no-check-certificate -O " + local_event_dir + "/" + out_json_file
                  #print(cmd)
                  #os.system(cmd)
               #   wget_cmds.append(cmd)
               #   if os.path.exists( local_event_dir + "/" + out_json_file) is False:
               #      cmd = "touch " + local_event_dir + "/" + out_json_file + ".failed"
                     #os.system(cmd)
               #else:
               #   print("Already have the file?")

               # red file
               #if skip_remote == 0 and os.path.exists( local_event_dir + "/" + out_red_json_file) is False and os.path.exists( local_event_dir + "/" + out_red_json_file + ".failed") is False:
               #   cmd = "wget " + rred + "  --timeout=1 --waitretry=0 --tries=1 --no-check-certificate -O " + local_event_dir + "/" + out_red_json_file
                  #print(cmd)
                  #os.system(cmd)
               #   wget_cmds.append(cmd)
               #   if os.path.exists( local_event_dir + "/" + out_red_json_file) is False:
               #      cmd = "touch " + local_event_dir + "/" + out_red_json_file + ".failed"
                  #   os.system(cmd)
               #else:
               #   print("Already have the file?")

               # we only need the mp4 file -- everything else can be made

               if skip_remote == 0 and os.path.exists( local_event_dir + "/" + out_file) is False and os.path.exists( local_event_dir + "/" + out_file + ".failed") is False:
                  cmd = "wget " + rmp4 + "  --timeout=1 --waitretry=0 --tries=1 --no-check-certificate -O " + local_event_dir + "/" + out_file
                  #print(cmd)
                  #os.system(cmd)
                  wget_cmds.append(cmd)
                  if os.path.exists( local_event_dir + "/" + out_file) is False:
                     cmd = "touch " + local_event_dir + "/" + out_file + ".failed"
                  #   os.system(cmd)
               else:
                  print("Already have the file?", local_event_dir + "/" + out_file)
             
               if os.path.exists( local_event_dir + "/" + out_file) is True:
                  if out_file not in self.sd_clips:
                     self.sd_clips[out_file] = {} 
                  self.sd_clips[out_file]['status'] = True
                  if out_file not in self.sync_log:
                     self.sync_log[out_file] = {} 
                  self.sync_log[out_file]['status'] = "GOOD"
               else:
                  if out_file not in self.sd_clips:
                     self.sd_clips[out_file] = {} 
                  if out_file not in self.sync_log:
                     self.sync_log[out_file] = {} 
                  self.sync_log[out_file]['status'] = "SYNC_FAILED"
                  self.sd_clips[out_file]['status'] = False 
                  missing_files.append(out_file)
      #else:
      #   print("none for ", good_obs_file)


      return(wget_cmds)

   def review_event(self, event_id):
      # the purpose of this function is to JUST get the MEDIA files for the event being reviewed.
      # see review_event_step2 for the remaining 

      # setup vars
      self.event_id = event_id
      self.sync_log = {}
      stack_imgs = []

      # convert id to date
      event_day = self.event_id_to_date(event_id)

      # MEDIA -- get media files from remote stations or wasabi
      local_event_dir = "/mnt/f/EVENTS/" + self.year + "/" + self.month + "/" + self.dom + "/" + self.event_id + "/" 
      wget_cmds = self.get_event_media(event_id)
      self.fast_cmds(wget_cmds)

         
      # MEDIA -- now load frames and make stacks as needed
      for out_file in self.sd_clips:
         sfile = out_file.replace(".mp4", "-stacked.jpg")

         if out_file in self.edits['sd_clips']:
            #print(out_file, "EDITS:", self.edits['sd_clips'][out_file].keys())
            if "custom_points" in  self.edits['sd_clips'][out_file]:
               self.sd_clips[out_file]['custom_points'] = self.edits['sd_clips'][out_file]['custom_points']
            if "deleted_points" in  self.edits['sd_clips'][out_file]:
               self.sd_clips[out_file]['deleted_points'] = self.edits['sd_clips'][out_file]['deleted_points']
            if "frame_data" in  self.edits['sd_clips'][out_file]:
               self.sd_clips[out_file]['frame_data'] = self.edits['sd_clips'][out_file]['frame_data']

         if os.path.exists(local_event_dir + sfile) is False:
            frames = load_frames_simple(local_event_dir + out_file)
            if len(frames) > 5:
               red_file = local_event_dir + out_file.replace(".mp4", "-reduced.json")
               if os.path.exists(red_file) is True:
                  try:
                     red_data = load_json_file(red_file) 
                  except:
                     red_data = {}
                     red_data['meteor_frame_data'] = []
                  self.sd_clips[out_file]['mfd'] = red_data['meteor_frame_data']

               simg = stack_frames(frames)
               cv2.imwrite(local_event_dir + sfile, simg)
               self.sd_clips[out_file]['stack_img'] = simg 
               self.sd_clips[out_file]['frames'] = frames 
               self.sd_clips[out_file]['status'] = True
               stack_imgs.append(simg)
            else:
               self.sd_clips[out_file]['status'] = False
         else:
            self.sd_clips[out_file]['stack_img'] = cv2.imread(local_event_dir + sfile)
            stack_imgs.append(self.sd_clips[out_file]['stack_img'])
            #self.sd_clips[out_file]['frames'] = load_frames_simple(local_event_dir + out_file)
            self.sd_clips[out_file]['frames'] = []
            self.sd_clips[out_file]['status'] = True
 
  
      #self.all_imgs = self.RF.frame_template("1920_4p", stack_imgs)
      #cv2.imshow('pepe', self.all_imgs) 
      #cv2.waitKey(0)

      # the rest will be completed in review event step2?

      return() 


      if False:
         if planes_data is not None:
            print("PLANES")
            for key in planes_data['results']:
               print(" ", key)
         else:
            print("none for planes_data", planes_file)

      # now should have all mp4s local and jsons and data loaded into self.sd_clips array
      

      #self.update_all_obs_xys(event_id, self.sd_clips, local_event_dir)
      exit()

   def get_media_urls(self, event_data, obs_data):
      print("DOWNLOAD MEDIA DAY")


   def obs_images_panel(self, map_img, event_data, obs_data, obs_imgs,marked_imgs):

      # decide thumb size based on number of images! 
      if len(obs_imgs) <= 4:
         tw = int(1920/2) 
         th = int(1080/2)
      elif 4 < len(obs_imgs) <= 12:
         tw = 640 
         th = 360 
      elif 9 < len(obs_imgs) <= 30:
         tw = 384
         th = 216 

      else:
         tw = 320 
         th = 180

      gimg = np.zeros((1080,1920,3),dtype=np.uint8)
      gmimg = np.zeros((1080,1920,3),dtype=np.uint8)
      cc = 0
      rc = 0
      for obs_id in obs_imgs:
         if obs_id not in obs_imgs:
            continue
         if obs_imgs[obs_id] is None:
            obs_imgs[obs_id] = np.zeros((1080,1920,3),dtype=np.uint8)

         img = obs_imgs[obs_id].copy()
         marked_img = cv2.resize(obs_imgs[obs_id], (1920,1080))
         rx1,ry1,rx2,ry2 = self.get_roi(obs_data[obs_id]['xs'], obs_data[obs_id]['ys'])
         x1 = cc * tw 
         x2 = x1 + tw 
         y1 = rc * th 
         y2 = y1 + th 

         cv2.rectangle(marked_img, (int(rx1), int(ry1)), (int(rx2) , int(ry2) ), (255, 255, 255), 2)

         if x2 > 1920:
            rc += 1
            y1 += th 
            y2 += th 
            x1 = 0
            x2 = tw 
            cc = 1
         else: 
            cc += 1
         try:
            thumb = cv2.resize(img, (tw,th))
            marked_thumb = cv2.resize(marked_img, (tw,th))
         except:
            thumb = np.zeros((th,tw,3),dtype=np.uint8)
            marked_thumb = np.zeros((th,tw,3),dtype=np.uint8)

         try:
            gimg[y1:y2,x1:x2] = thumb
            gmimg[y1:y2,x1:x2] = thumb 
         except:
            print(x1,y1,x2,y2)

         cv2.imshow('pepe', gmimg)
         cv2.waitKey(90)

         try:
            gimg[y1:y2,x1:x2] = thumb
            gmimg[y1:y2,x1:x2] = marked_thumb
         except:
            print(x1,y1,x2,y2)
         cv2.imshow('pepe', gmimg)
         cv2.waitKey(90)



      gallery_image = gimg

      simg = np.zeros((1080,1920,3),dtype=np.uint8)
      map_img = cv2.resize(map_img, (1280,720))
      # do layout based on number of images availbable

      if len(obs_imgs) == 2:
         map_img = cv2.resize(map_img, (960,540))
         i = 0
         # map center would be (1920 / 2 ) - (960/2)
         x1 =  int((1920 / 2 ) - (960/2))
         x2 =  int((1920 / 2 ) + (960/2))
         simg[540:1080,x1:x2] = map_img
         for key in obs_imgs:
            obs_id = key
            show_img = cv2.resize(marked_imgs[key], (1920,1080))
            rx1,ry1,rx2,ry2 = self.get_roi(obs_data[key]['xs'], obs_data[key]['ys'])
     




            #obs_imgs[key] = cv2.resize(obs_imgs[key], (960,540))
            obs_imgs[key] = cv2.resize(show_img, (960,540))
            #marked_imgs[key] = cv2.resize(show_img, (960,540))
            station_id = obs_id.split("_")[0]
            obs_datetime = obs_data[obs_id]['times'][0]
            label = station_id + " " + obs_datetime
            if i == 0:
               x1 = 0
               x2 = 960 
               y1 = 0
               y2 = 540
               simg[y1:y2,x1:x2] = cv2.resize(show_img, ((x2-x1), (y2-y1)))
               cv2.putText(simg, label,  (x1,y2-10), cv2.FONT_HERSHEY_SIMPLEX, .6, (0,255,0), 1)
            if i == 1:
               x1 = 960
               x2 = 1920 
               y1 = 0
               y2 = 540
               simg[y1:y2,x1:x2] = cv2.resize(show_img, ((x2-x1), (y2-y1)))
               cv2.putText(simg, label,  (x1, y2-10), cv2.FONT_HERSHEY_SIMPLEX, .6, (0,255,0), 1)
            i+= 1
      
      elif len(obs_imgs) == 3:
         map_img = cv2.resize(map_img, (960,540))
         i = 0
         # map center would be (1920 / 2 ) - (960/2)
         x1 = 960 
         x2 = 1920 
         y1 = 540
         y2 = 1080 

         simg[y1:y2,x1:x2] = map_img
         for key in obs_imgs:
            obs_id = key

            rx1,ry1,rx2,ry2 = self.get_roi(obs_data[key]['xs'], obs_data[key]['ys'])
            show_img = cv2.resize(marked_imgs[key].copy(), (1920,1080))
            cv2.rectangle(show_img, (int(rx1), int(ry1)), (int(rx2) , int(ry2) ), (255, 255, 255), 2)
            cv2.imshow('pepe', show_img)
            cv2.waitKey(40)


            obs_imgs[key] = cv2.resize(obs_imgs[key], (960,540))
            marked_imgs[key] = cv2.resize(show_img, (960,540))
            station_id = obs_id.split("_")[0]
            obs_datetime = obs_data[obs_id]['times'][0]
            label = station_id + " " + obs_datetime
            if i == 0:
               x1 = 0
               x2 = 960 
               y1 = 0
               y2 = 540
               #simg[y1:y2,x1:x2] = obs_imgs[key]
               simg[y1:y2,x1:x2] = cv2.resize(show_img, ((x2-x1), (y2-y1)))
               cv2.putText(simg, label,  (x1,y2-10), cv2.FONT_HERSHEY_SIMPLEX, .6, (0,255,0), 1)
            if i == 1:
               x1 = 960
               x2 = 1920 
               y1 = 0
               y2 = 540
               #simg[y1:y2,x1:x2] = obs_imgs[key]
               simg[y1:y2,x1:x2] = cv2.resize(show_img, ((x2-x1), (y2-y1)))
               cv2.putText(simg, label,  (x1, y2-10), cv2.FONT_HERSHEY_SIMPLEX, .6, (0,255,0), 1)
            if i == 2:
               x1 = 0 
               x2 = 960 
               y1 = 540
               y2 = 1080 
               #simg[y1:y2,x1:x2] = obs_imgs[key]
               simg[y1:y2,x1:x2] = cv2.resize(show_img, ((x2-x1), (y2-y1)))
               cv2.putText(simg, label,  (x1, y2-10), cv2.FONT_HERSHEY_SIMPLEX, .6, (0,255,0), 1)
            i+= 1

      else:
         map_img = cv2.resize(map_img, (1280,720))
         simg[0:720,0:1280] = map_img
         x1 = 1280
         x2 = 1920
         y1 = 0
         y2 = 360
         i = 0
         for key in obs_imgs:
            obs_id = key

            rx1,ry1,rx2,ry2 = self.get_roi(obs_data[key]['xs'], obs_data[key]['ys'])
            show_img = cv2.resize(marked_imgs[key].copy(), (1920,1080))
            cv2.rectangle(show_img, (int(rx1), int(ry1)), (int(rx2) , int(ry2) ), (255, 255, 255), 2)
            cv2.imshow('pepe', show_img)
            cv2.waitKey(40)

            try:
               obs_imgs[key] = cv2.resize(obs_imgs[key], (960,540))
            except:
               src_img = np.zeros((540,960,3),dtype=np.uint8)
            try:
               marked_imgs[key] = cv2.resize(show_img, (960,540))
            except:
               marked_imgs[key] = np.zeros((540,960,3),dtype=np.uint8)
            station_id = obs_id.split("_")[0]
            obs_datetime = obs_data[obs_id]['times'][0]
            label = station_id + " " + obs_datetime

            if obs_imgs[key] is None:
               obs_imgs[key] = np.zeros((360,640,3),dtype=np.uint8)

            if obs_imgs[key].shape[0] != 360:
               obs_imgs[key] = cv2.resize(obs_imgs[key], (640,360))
            if i == 0:
               #simg[y1:y2,x1:x2] = obs_imgs[key]
               simg[y1:y2,x1:x2] = cv2.resize(show_img, ((x2-x1), (y2-y1)))
               cv2.putText(simg, label,  (x1,y2-10), cv2.FONT_HERSHEY_SIMPLEX, .6, (0,255,0), 1)
            if i == 1:
               #simg[y1+360:y2+360,x1:x2] = obs_imgs[key]
               simg[y1+360:y2+360,x1:x2] = cv2.resize(show_img, ((x2-x1), (y2-y1)))
               cv2.putText(simg, label,  (x1,y2+360-10), cv2.FONT_HERSHEY_SIMPLEX, .6, (0,255,0), 1)
            if i == 2:
               #simg[y1+720:y2+720,x1:x2] = obs_imgs[key]
               simg[y1+720:y2+720,x1:x2] = cv2.resize(show_img, ((x2-x1), (y2-y1)))
               cv2.putText(simg, label,  (x1,y2+720-10), cv2.FONT_HERSHEY_SIMPLEX, .6, (0,255,0), 1)
            if i == 3:
               #simg[720:1080,0:640] = obs_imgs[key]
               y1 = 720
               y2 = 1080
               x1 = 0
               x2 = 640
               simg[y1:y2,x1:x2] = cv2.resize(show_img, ((x2-x1), (y2-y1)))
               cv2.putText(simg, label,  (10, y2+720-10), cv2.FONT_HERSHEY_SIMPLEX, .6, (0,255,0), 1)
            if i == 4:
               y1 = 720
               y2 = 1080
               x1 = 640
               x2 = 1280 
               #simg[720:1080,640:1280] = obs_imgs[key]
               simg[y1:y2,x1:x2] = cv2.resize(show_img, ((x2-x1), (y2-y1)))
               cv2.putText(simg, label,  (640+10, y2+720-10), cv2.FONT_HERSHEY_SIMPLEX, .6, (0,255,0), 1)
            i += 1

      print("LEN OBS IMGS:", len(obs_imgs))
      simg = self.RF.watermark_image(simg, self.RF.logo_320, 1590, 10, .5, []) 
      return(simg, gallery_image)

   def get_roi(self, xs, ys):
      w = (max(xs) - min(xs)) + 50
      h = (max(ys) - min(ys)) + 50
      if w > h:
         h = w
      else:
         w = h
      x1 = int(np.mean(xs) - int(w/2) )
      y1 = int(np.mean(ys) - int(h/2) )

      if x1 < 0:
         x1 = 0
      if y1 < 0:
         y1 = 0
      x2 = int(x1 + w)
      y2 = int(y1 + h)
      if x2 > 1920:
         x2 = 1920 
         x1 = 1920 - w
      if y2 > 1080:
         y2 = 1080 
         y1 = 1080 - h
      return(x1,y1,x2,y2)


   def load_obs_images(self, obs_data):
      obs_imgs = {}
      marked_imgs = {}
      roi_imgs = {}
      ai_imgs = {}
      found = False
      for obs_id in obs_data:
         skip = False
         marked_file = obs_data[obs_id]['image_file'].replace(".jpg", "-marked.jpg")
         roi_file = obs_data[obs_id]['image_file'].replace(".jpg", "-roi.jpg")


         if os.path.exists(obs_data[obs_id]['image_file']) :
            obs_imgs[obs_id] = cv2.imread(obs_data[obs_id]['image_file'])
            found = True
            obs_data[obs_id]['media_res'] = "360p" 
         elif os.path.exists(obs_data[obs_id]['image_file'].replace("-stacked.jpg","-prev.jpg")):
            obs_imgs[obs_id] = cv2.imread(obs_data[obs_id]['image_file'].replace("-stacked.jpg","-prev.jpg"))
            found = True
            obs_data[obs_id]['media_res'] = "180p" 



         if os.path.exists(marked_file) is True:
            marked_imgs[obs_id] = cv2.imread(marked_file) 
            roi_imgs[obs_id] = cv2.imread(roi_file) 
            skip = True
            print("DONE ALREADY!")

         # only do this if the marked image is not already done!
         if found is True and skip is False:

            if obs_id in obs_imgs:
               try:
                  src_img = cv2.resize(obs_imgs[obs_id].copy(), (1920,1080))
                  show_img = src_img.copy()
               except:
                  src_img = np.zeros((1080,1920,3),dtype=np.uint8)
                  show_img = np.zeros((1080,1920,3),dtype=np.uint8)
            else:
               src_img = np.zeros((1080,1920,3),dtype=np.uint8)
               show_img = np.zeros((1080,1920,3),dtype=np.uint8)

            # get roi (this should be the entire area of meteor only). 
            rx1,ry1,rx2,ry2 = self.get_roi(obs_data[obs_id]['xs'], obs_data[obs_id]['ys'])
            mx = int(np.mean(obs_data[obs_id]['xs']))
            my = int(np.mean(obs_data[obs_id]['ys']))


            roi_img = src_img[ry1:ry2,rx1:rx2] 
            cv2.imwrite(roi_file, roi_img)

            gray_img =  cv2.cvtColor(src_img, cv2.COLOR_BGR2GRAY)

            gray_roi = gray_img[ry1:ry2,rx1:rx2] 
            min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(gray_roi)
      
            # V2 ROI is 64/64
            # V1 ROI is 224/224!

            ax1 = rx1 + mx - 112
            ax2 = rx1 + mx + 112
            ay1 = ry1 + my - 112
            ay2 = ry1 + my + 112

            w = ax2 - ax1
            h = ay2 - ay1
            if ax1 < 0:
               ax1 = 0
               ax2 = w
            if ay1 < 0:
               ay1 = 0
               ay2 = h
            if ax2 > 1920:
               ax2 = 1920
               ax1 = 1920 - w
            if ay2 > 1080:
               ay2 = 1080 
               ay1 = 1080 - h


            ai_img = src_img[ay1:ay2,ax1:ax2] 
            ai_imgs[obs_id] = ai_img
            roi_imgs[obs_id] = roi_img
            print("OBS IMG", ai_img.shape)
            print("AI IMG", ax1, ay1, ax2, ay2, ai_img.shape)

            # image or image_file
            ai_resp = self.check_ai_img(ai_img, None)
            if ai_resp['meteor_prev_yn'] > ai_resp['meteor_yn']:
               ai_resp['meteor_yn'] = ai_resp['meteor_prev_yn']

            class_data =  [
                ['Meteor', ai_resp['meteor_yn']], 
                ['Fireball', ai_resp['fireball_yn']], 
                [ai_resp['mc_class'], ai_resp['mc_class_conf']] 
                ]


            class_data = sorted(class_data, key=lambda x: (x[1]), reverse=True)
            print("AI RESP:", ai_resp) 
            print("AI CLASSIFICATION:", class_data) 
            obs_data[obs_id]['ai_resp'] = ai_resp
            obs_data[obs_id]['ai_class'] = class_data

            # save off all files and results for future learning?
            st = obs_id.split("_")[0]
            temp = obs_id.replace(st + "_", "")

            date = temp[0:10]
            self.learning_dir = "/mnt/f/AI/DATASETS/NETWORK/" + date + "/" + class_data[0][0] + "/"
            if os.path.exists(self.learning_dir) is False:
               os.makedirs(self.learning_dir)
            learn_file = obs_id.replace(".mp4", "") + "_" + str(ax1) + "_" + str(ay1) + "_" + str(ax2) + "_" + str(ay2) + ".jpg"
            cv2.imwrite(self.learning_dir + learn_file, ai_img)
            print("SAVING:", self.learning_dir + learn_file)




            cv2.rectangle(show_img, (int(rx1), int(ry1)), (int(rx2) , int(ry2) ), (255, 255, 255), 2)

            if "ai_class" in obs_data[obs_id]:
               rc = 0
               for row in obs_data[obs_id]['ai_class']:
                  label, perc = row
                  offset = rc * 30
                  text = label.upper() + " " + str(round(perc,1)) + "%"
                  cv2.putText(show_img, text,  (rx2+20,ry1+10+offset), cv2.FONT_HERSHEY_SIMPLEX, .8, (0,255,0), 2)
                  rc += 1


            #cv2.imshow('pepe', show_img)
            #cv2.waitKey(520)
            marked_imgs[obs_id] = show_img
            cv2.imwrite(marked_file, show_img, [cv2.IMWRITE_JPEG_QUALITY, 70])





      return(obs_imgs, marked_imgs, roi_imgs, ai_imgs, obs_data)

   def review_event_step2(self):
      # drive this 100% from DB
      # get all current obs data
      # load stack imgs while you go

      # purpose here is to make the map file and multi-image review
      # if it is already done we can just return?
      # we should load it and return it though?
      force = True 

      obs_data_file = self.local_evdir + self.event_id + "/" + self.event_id + "_OBS_DATA.json"
      event_data_file = self.local_evdir + self.event_id + "/" + self.event_id + "_EVENT_DATA.json"
      map_img_file = self.local_evdir + self.event_id + "/" + self.event_id + "_MAP_FOV.jpg"
      review_img_file = self.local_evdir + self.event_id + "/" + self.event_id + "_REVIEW.jpg"

      # if the files exist already remove them
      if os.path.exists(map_img_file) is True:
         os.system("rm " + map_img_file)
      if os.path.exists(review_img_file) is True:
         os.system("rm " + review_img_file)


      # everything is done already skip???
      if force is False and os.path.exists(obs_data_file) is True and os.path.exists(event_data_file) is True and os.path.exists(review_img_file) is True:
         obs_data = load_json_file(obs_data_file)
         event_data = load_json_file(event_data_file)
         map_img = cv2.imread(map_img_file)
         review_img = cv2.imread(review_img_file)
         #event_data, obs_data, map_img,obs_imgs = self.get_event_obs()
         
         obs_imgs, marked_imgs, roi_imgs, ai_imgs, obs_data = self.load_obs_images(obs_data) 
         print("REVIEW:", review_img_file)
         return(review_img, map_img, obs_imgs, marked_imgs, event_data, obs_data)
      else:
         event_data, obs_data, map_img, obs_imgs = self.get_event_obs()
         obs_imgs, marked_imgs, roi_imgs, ai_imgs, obs_data = self.load_obs_images(obs_data) 
         save_json_file(event_data_file, event_data)
         print("SAVING:", event_data_file)
         save_json_file(obs_data_file, obs_data, True)
         print("SAVING:", obs_data_file)
         cv2.imwrite(map_img_file, map_img, [cv2.IMWRITE_JPEG_QUALITY, 70])
         print("SAVING:", map_img_file)

      if "2d_status" not in event_data:
         print("GET 2D status")
         event_data = self.get_2d_status(event_data, obs_data)


      #for key in obs_data:
      #   print("OBS DATA KEYS:", key, obs_data.keys())

      simg, gallery_image = self.obs_images_panel(map_img, event_data, obs_data, obs_imgs, marked_imgs)


      if "traj" in event_data:
         (sol_status, v_init, v_avg, start_ele, end_ele, a, e) = self.eval_sol(event_data)
         event_data['event_status'] = sol_status

      if event_data['2d_status'] == "FAILED":
         cv2.putText(simg, "INVALID 2D EVENT",  (20,20), cv2.FONT_HERSHEY_SIMPLEX, .8, (0,0,255), 2)
      else:
         cv2.putText(simg, "VALID 2D EVENT",  (20,20), cv2.FONT_HERSHEY_SIMPLEX, .8, (0,255,0), 2)
      if "BAD" in event_data['event_status'] :
         cv2.putText(simg, event_data['event_status'],  (20,60), cv2.FONT_HERSHEY_SIMPLEX, .8, (0,0,255), 2)
      else:
         cv2.putText(simg, event_data['event_status'],  (20,60), cv2.FONT_HERSHEY_SIMPLEX, .8, (0,255,0), 2)

      cv2.imwrite(review_img_file, 255*simg, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
      print("SAVING:", review_img_file)


      print("DONE STEP2")

      return(simg, map_img, obs_imgs, marked_imgs, event_data, obs_data)
      # THIS IS OLD AND NO LONGER USED!

      sql = """SELECT event_id, station_id, obs_id, fns, times, xs, ys, azs, els, ints, 
                    status, ignore, ai_confirmed, human_confirmed, ai_data, prev_uploaded 
               FROM event_obs
              WHERE event_id = ?
           ORDER BY obs_id
           """
      vals = [self.event_id]
      print(sql, vals)
      self.cur.execute(sql, vals)
      rows = self.cur.fetchall()
      obs_db = []
      stack_imgs = []
      not_found = []
      stack_imgs_dict = {}
      for row in rows:
         (event_id, station_id, obs_id, fns, times, xs, ys, azs, els, ints, \
            status, ignore, ai_confirmed, human_confirmed, ai_data, prev_uploaded ) = row
         obs_db.append((event_id, station_id, obs_id, fns, times, xs, ys, azs, els, ints, \
            status, ignore, ai_confirmed, human_confirmed, ai_data, prev_uploaded ))
         sd_vid_file = self.ev_dir + obs_id + ".mp4"
         stack_file = self.ev_dir + obs_id + "-stacked.jpg"
         print(obs_id, fns, xs, ys)
         if os.path.exists(sd_vid_file):
            print("FOUND!", sd_vid_file) 
         else:
            print("NOT FOUND!", sd_vid_file) 
         if os.path.exists(stack_file):
            print("FOUND!", stack_file) 
            simg = cv2.imread(stack_file)
            cv2.resize(simg, (1920,1080))
            stack_imgs.append((stack_file, simg))
            stack_imgs_dict[obs_id] = simg
         else:
            print("NOT FOUND!", stack_file) 
            simg = np.zeros((1080,1920,3),dtype=np.uint8)
            stack_imgs_dict[obs_id] = simg
            not_found.append((stack_file, simg))


      # decide default thumb size
      stack_count = len(stack_imgs)
      if len(stack_imgs) > 0:
         pxs_per_img = (1920 * 1080) / len(stack_imgs)
      else:
         print("No stacks!" )
         exit()
      print("NOT FOUND", len(not_found))
      print("PXPI:", pxs_per_img) 
      dimen = [ [1920,1080], [1920/2,1080/2], [1920/3,1080/3], [1920/4,1080/4], [1920/4,1080/5], [1920/4,1080/6], [1920/4,1080/8], [1920/4,1080/10] ]
      for dim in dimen:
         avail = pxs_per_img / (dim[0] * dim[1])
         if avail > 1:
            iw, ih = int(dim[0]), int(dim[1])
            break
      print("RECOMMENDED SIZE:", iw, ih)

      exit()

      # make summary image of all obs
      cc = 0
      rc = 0
      comp_img = np.zeros((1080,1920,3),dtype=np.uint8)
 
      # define max rows/cols
      for sfile, img in stack_imgs:
         x1 = iw * cc 
         x2 = x1 + iw
         y1 = ih * rc 
         y2 = y1 + ih
         cc += 1
         if y2 >= 1920:
            cc = 0
         if iw * cc >= 1920:
            max_cols = cc
            cc = 0
            rc += 1

      max_rows = rc 
      cc = 0
      rc = 0
      for sfile, img in stack_imgs:
         if cc < 0:
            cc = max_cols - 1
         if cc > max_cols:
            cc = 0 
         thumb = cv2.resize(img, (iw,ih))
         x1 = iw * cc 
         x2 = x1 + iw
         y1 = ih * rc 
         y2 = y1 + ih
         cc += 1
         if iw * cc >= 1920:
            cc = 0
            rc += 1
         if rc > max_rows:
            rc = 0
         comp_img[y1:y2,x1:x2] = thumb
         show_img = self.RF.frame_template("1920_1p", [comp_img])
         #cv2.imshow("pepe", show_img)
         #cv2.waitKey(30)
      #cv2.waitKey(30)
      go = True
      oshow_img = show_img.copy()

      idx_keys = []
      for sd_vid in self.sd_clips:
         if self.sd_clips[sd_vid]['status'] is True:
            idx_keys.append(sd_vid)



      # display obs selector menu
      sc = 0
      cc = 0
      rc = 0
      idx = 0
      key = ""
      while go is True:
         show_img = oshow_img.copy()
         
         x1 = iw * cc 
         x2 = x1 + iw
         y1 = ih * rc 
         y2 = y1 + ih

         print("ST", idx, key, cc, rc, x1,y1,x2,y2)

         cv2.rectangle(show_img, (int(x1), int(y1)), (int(x2) , int(y2) ), (255, 255, 255), 2)

         cv2.imshow("pepe", show_img)
         key = cv2.waitKey(0)
         print("KEY PUSHED:", key)

         if key == 27:
            # esc 
            exit() 
         if key == 97:
            # left 
            cc -= 1
            if cc < 0:
              cc = max_cols - 1
              rc -= 1
            if rc < 0:
               rc = 0
               cc = 0
         if key == 102:
            # right 
            cc += 1
            if cc >= max_cols:
              cc = 0 
              rc += 1
         if key == 100:
            # down
            rc += 1
            if rc > max_rows:
               rc = 0
         if key == 115:
            # down
            print("DOWN")
            rc -= 1
            if rc < 0:
               rc = max_rows 
         idx = (rc * max_cols) + 1 + cc
      
         if key == 32:
            # esc 
            sd_vid = idx_keys[idx]
            self.sd_clips[sd_vid]['frame_data'],self.sd_clips[sd_vid]['subs'] = self.build_frame_data(sd_vid, self.sd_clips[sd_vid]['frames'])
            self.review_data()

            self.sd_clips[sd_vid]['frame_data'], self.sd_clips[sd_vid]['deleted_points'], self.sd_clips[sd_vid]['custom_points'] = self.play_video(sd_vid, self.RF )


         if idx > len(stack_imgs):
            cc = 0
            rc = 0
         if idx < 0 :
            idx = 0
            cc = 0
            rc = 0
         print(idx, key, cc, rc, x1,y1,x2,y2)


   def get_2d_status(self, event_data, obs_data):
      bad_obs = 0
      good_obs = 0
      for obs_id in obs_data:
         if obs_data[obs_id]['ignore'] is True:
            bad_obs+= 1
         else: 
            good_obs += 1
      if good_obs <= 1:
         event_data['2d_status'] = "FAILED"
      else:
         event_data['2d_status'] = str(good_obs) + " GOOD 2D STATIONS"

      print(event_data)
      return(event_data)

   def make_event_summary_image(self, edited_files, good_files, ignored_files, missing_files):
      print(edited_files)
      print(good_files)
      print(ignored_files)
      print(missing_files)
      edited_imgs = []
      good_imgs = []
      ignore_imgs = []
      missing_imgs = []
      for sd_vid in edited_files:
         print("EDITED:", sd_vid)
         stack_file = self.ev_dir + sd_vid.replace(".mp4", "-stacked.jpg")
         if os.path.exists(stack_file) is True:
            stack_img = cv2.imread(stack_file)
            edited_imgs.append(stack_img)
            print("EDITED FOUND", stack_file)
         else:
            print("EDITED missing stack", stack_file)

      for sd_vid in good_files:
         print("GOOD:", sd_vid)
         stack_file = self.ev_dir + sd_vid.replace(".mp4", "-stacked.jpg")
         if os.path.exists(stack_file) is True:
            stack_img = cv2.imread(stack_file)
            good_imgs.append(stack_img)
            print("GOOD FOUND", stack_file)
         else:
            print("GOOD missing", stack_file)
      for sd_vid in ignored_files:
         print("IGNORE:", sd_vid)
         stack_file = self.ev_dir + sd_vid.replace(".mp4", "-stacked.jpg")
         if os.path.exists(stack_file) is True:
            stack_img = cv2.imread(stack_file)
            ignore_imgs.append(stack_img)
            print("IGNORE FOUND", stack_file)
         else:
            print("IGNORE missing", stack_file)
      for sd_vid in missing_files:
         stack_file = self.ev_dir + sd_vid.replace(".mp4", "-stacked.jpg")
         print("MISSING:", sd_vid)
         if os.path.exists(stack_file) is True:
            stack_img = cv2.imread(stack_file)
            missing_imgs.append(stack_img)
         else:
            print("missing", stack_file)

      print(len(edited_imgs))
      print(len(good_imgs))
      print(len(ignore_imgs))
      for img in edited_imgs:
         img = cv2.resize(img, (640,360))
         cv2.rectangle(img, (int(1), int(1)), (int(639) , int(359) ), (0, 0, 255), 2)
         cv2.imshow('pepe', img)
         cv2.waitKey(30)
      for img in good_imgs:
         img = cv2.resize(img, (640,360))
         cv2.rectangle(img, (int(1), int(1)), (int(639) , int(359) ), (128, 128, 128), 2)
         cv2.imshow('pepe', img)
         cv2.waitKey(30)
      for img in ignore_imgs:
         img = cv2.resize(img, (640,360))
         cv2.rectangle(img, (int(1), int(1)), (int(639) , int(359) ), (0, 0, 128), 2)
         cv2.imshow('pepe', img)
         cv2.waitKey(30)

   def update_all_obs_xys(self, event_id, local_event_dir, RF, all_img):
      #for each SD clip get the contour and brightest pixels from the sub
      # show this vs the reduction info
      # allow operator to update points
      # allow operator to ignore obs
      if "ignore_obs" not in self.edits:
         self.edits['ignore_obs'] = {}

      go = True
      idx_keys = []
      for sd_vid in self.sd_clips:
         if self.sd_clips[sd_vid]['status'] is True:
            idx_keys.append(sd_vid)

      idx = -1
      while go is True:
         if idx == -1:
            show_img = all_img.copy()


            cv2.putText(show_img, event_id,  (10,1070), cv2.FONT_HERSHEY_SIMPLEX, .6, (0,255,0), 1)
            cv2.imshow('pepe', show_img)
            key = cv2.waitKey(0)
            # show all
            if key == 115:
               # S / NEXT
               idx += 1
            if key == 100:
               # D / PREV 
               idx = len(idx_keys) - 1


         else:
            # show stack image of 1 obs 
            sd_vid = idx_keys[idx]
            if self.sd_clips[sd_vid]['status'] is True:
               show_img = self.sd_clips[sd_vid]['stack_img'].copy() 
               #text_data = [[20,20,1,2,[255,255,255],"mike was here!"]]
               text_data = []
               show_frame = RF.frame_template("1920_1p", [show_img.copy()], text_data)
               if sd_vid in self.edits['ignore_obs']:
                  if self.edits['ignore_obs'][sd_vid] is True:
                     cv2.putText(show_frame, "IGNORE OBS",  (900,25), cv2.FONT_HERSHEY_SIMPLEX, .6, (0,0,255), 1)

               cv2.putText(show_frame, event_id + " : " + sd_vid.replace(".mp4", ""),  (1100,1070), cv2.FONT_HERSHEY_SIMPLEX, .6, (0,255,0), 1)

               cv2.putText(show_frame, str(idx),  (1900,25), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 1)
               if "frame_data" in self.sd_clips[sd_vid]:
                  for fd in self.sd_clips[sd_vid]['frame_data']:
                     print("FD", self.sd_clips[sd_vid]['frame_data'][fd])

                  exit()
               cv2.imshow('pepe', show_frame)
               key = cv2.waitKey(0)
               if key == 115:
                  # S / NEXT
                  print("PRESS S")
                  idx += 1
               elif key == 100:
                  # D / PREV 
                  print("PRESS D")
                  idx -= 1
               elif key == 27:
                  # [ESC]
                  self.save_edits()
                  print("EXIT!")
                  exit()
               elif key == 112:
                  # [P] - Play Video
                  if "frame_data" not in self.sd_clips[sd_vid]:
                     self.sd_clips[sd_vid]['frame_data'] = {}

                  #if "frame_data" not in self.sd_clips[sd_vid] :
                  if True:
                     self.sd_clips[sd_vid]['frame_data'],self.sd_clips[sd_vid]['subs'] = self.build_frame_data(sd_vid, self.sd_clips[sd_vid]['frames'])
                     print(sd_vid, self.sd_clips[sd_vid].keys())


                  #self.sd_clips[sd_vid]['frame_data'], self.sd_clips[sd_vid]['deleted_points'], self.sd_clips[sd_vid]['custom_points'] = self.play_video(sd_vid, self.sd_clips[sd_vid]['frames'], self.sd_clips[sd_vid]['subs'], RF, self.sd_clips[sd_vid]['frame_data'], self.sd_clips[sd_vid]['stack_img'])
                  self.sd_clips[sd_vid]['frame_data'], self.sd_clips[sd_vid]['deleted_points'], self.sd_clips[sd_vid]['custom_points'] = self.play_video(sd_vid, RF )

               elif key == 120:
                  # X / TOGGLE IGNORE  
                  sd_vid = idx_keys[idx]
                  if sd_vid in self.edits['ignore_obs']:
                     if self.edits['ignore_obs'][sd_vid] is True:
                        self.edits['ignore_obs'][sd_vid] = True
                        cv2.putText(show_img, "IGNORE OBS",  (900,25), cv2.FONT_HERSHEY_SIMPLEX, .6, (0,0,255), 1)
                     else:
                        self.edits['ignore_obs'][sd_vid] = False 
                  else:
                     self.edits['ignore_obs'][sd_vid] = True
                     cv2.putText(show_img, "IGNORE OBS",  (900,25), cv2.FONT_HERSHEY_SIMPLEX, .6, (0,0,255), 1)



            else:
               idx += 1

            print("KEY/IDX:", key, idx)
            if idx >= len(idx_keys):
               idx = -1
               print("END OF LIST RESET")
               
         continue

         for sd_vid in self.sd_clips:
            if self.sd_clips[sd_vid]['status'] is False:
               continue 
            sfile = sd_vid.replace(".mp4", "-stacked.jpg")
            self.sd_clips[sd_vid]['sub_frames'] = []
            self.sd_clips[sd_vid]['cnts'] = []

            if self.sd_clips[sd_vid]['status'] is True :
   
               show_frame = RF.frame_template("1920_1p", [self.sd_clips[sd_vid]['stack_img']])
               cv2.waitKey(0)
               temp = []
               for frame in self.sd_clips[sd_vid]['frames'][0:25]:
                  bw_frame =  cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                  temp.append(bw_frame)
               med_frame = cv2.convertScaleAbs(np.median(np.array(temp), axis=0))

               for frame in self.sd_clips[sd_vid]['frames']:
                  bw_frame =  cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                  sub = cv2.subtract(bw_frame,med_frame)
                  self.sd_clips[sd_vid]['sub_frames'].append(sub)

                  show_frame = RF.frame_template("1920_1p", [frame])

                  cv2.imshow('pepe_sub', sub)
                  cv2.imshow('pepe', show_frame)
                  key = cv2.waitKey(0)
                  print("KEY", key)
            else:
               print("BAD OR MISSING VIDEO:", sd_vid)

      print("OK - OK")

   def save_edits(self):
      self.edits_data = {}
      for key in self.edits_data:
         dtype = type(self.edits_data[key])
         print(key, dtype)
         if str(dtype) == "list" or str(dtype) == "dict":
            print("LIST OR DICT HERE!")
            for skey in self.edits_data[key]: 
               print(skey, type(skey))
      for sd_vid in self.sd_clips:
         if "subs" in self.sd_clips[sd_vid]:
            del(self.sd_clips[sd_vid]['subs'])
         if "frames" in self.sd_clips[sd_vid]:
            del(self.sd_clips[sd_vid]['frames'])
         if "stack_img" in self.sd_clips[sd_vid]:
            del(self.sd_clips[sd_vid]['stack_img'])

      self.edits_data['sd_clips'] = dict(self.sd_clips)
      self.edits_data['ignore_obs'] = dict(self.edits['ignore_obs'])
      save_json_file(self.edits_file, self.edits_data, True)
      print("SAVED", self.edits_file )

   def frame_data_to_objects(self, frame_data):
      objects = {}
      xs = []
      ys = []
      for fc in frame_data:
         if "cnts" in frame_data[fc]:
            cnts = frame_data[fc]['cnts']
            for cnt in cnts:
               #x,y,w,h,meteor_flux,meteor_intensity = cnt
               x1,y1,x2,y2,cx,cy,radius,meteor_int,meteor_flux = cnt
               w = x2 - x1
               h = y2 - y1
               obj_id, objects = find_object(objects, fc,cx, cy, w, h, meteor_flux, 0, 0, None)
      meteor_objects = {} 
      non_meteor_objects = {} 
      last_biggest = None
      last_big = 0
      for obj in objects:
         objects[obj] = analyze_object(objects[obj], 1)
         if len(objects[obj]['oxs']) > last_big:
            last_biggest = obj
            last_big = len(objects[obj]['oxs'])
         print("OBJECT", obj, len(objects[obj]['oxs']), objects[obj]['report']['meteor'], objects[obj]['report']['bad_items'])
      best = {}
      best["1"] = objects[last_biggest]
      return(best)

   def graph_xys(self,xs,ys):

      plt.scatter(xs,ys) 
      #plt.gca().invert_yaxis()
      plt.savefig("temp.png")
      img = cv2.imread("temp.png")
      img = cv2.resize(img, (int(img.shape[1]*.5), int(img.shape[0]*.5)))
      cv2.imshow('graph', img)
      cv2.waitKey(30)

   def build_frame_data(self, sd_vid, frames):
      print("BUILD FRAME DATA FOR :", sd_vid) 

      if sd_vid in self.edits['sd_clips']:
         if "deleted_points" in self.edits['sd_clips'][sd_vid]:
            self.sd_clips[sd_vid]['deleted_points'] =  self.edits['sd_clips'][sd_vid]['deleted_points']
         if "custom_points" in self.edits['sd_clips'][sd_vid]:
            self.sd_clips[sd_vid]['custom_points'] =  self.edits['sd_clips'][sd_vid]['custom_points']

      if "custom_points" not in self.sd_clips[sd_vid]:
         self.sd_clips[sd_vid]['custom_points'] = {}
      if "deleted_points" not in self.sd_clips[sd_vid]:
         self.sd_clips[sd_vid]['deleted_points'] = {}

      print("D:", self.sd_clips[sd_vid]['deleted_points'])
      print("C:", self.sd_clips[sd_vid]['custom_points'])
      print("SD CLIPS:", self.sd_clips[sd_vid].keys())
      print("SD E CLIPS:", self.edits['sd_clips'].keys())

      frame_data = {}
      fc = 0
      temp = []
      subs = {}
      hdm_x = 1920 / 640
      hdm_y = 1080 / 360
      for frame in frames[0:10]:
         bw_frame = cv2.resize(frame, (640,360))
         bw_frame =  cv2.cvtColor(bw_frame, cv2.COLOR_BGR2GRAY)
         temp.append(bw_frame)

      med_frame = cv2.convertScaleAbs(np.median(np.array(temp), axis=0))

      for frame in frames:
         frame = cv2.resize(frame, (640,360))
         frame_data[fc] = {}
         bw_frame =  cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
         sub = cv2.subtract(bw_frame,med_frame)
         min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(sub)
         subs[fc] = sub
         thresh_val = int(max_val * .6)
         _, thresh_image = cv2.threshold(sub, thresh_val, 255, cv2.THRESH_BINARY)
         cnts = get_contours_in_image(thresh_image)

         if len(cnts) >= 1:
            cnts = sorted(cnts, key=lambda x: x[2] * x[3], reverse=True)
            cnts = [cnts[0]]

         # if the frame exists inside the custom points 
         # override the default cnt with those values 
         print("BEFORE OVERRIDE CNTS:", cnts)
         if fc in self.sd_clips[sd_vid]['custom_points'] :
            x = int(self.sd_clips[sd_vid]['custom_points'][fc][0] / hdm_x )
            y = int(self.sd_clips[sd_vid]['custom_points'][fc][1] / hdm_y)
            w = int(self.sd_clips[sd_vid]['custom_points'][fc][2] / hdm_y)
            h = w
            cnts = [[x,y,w,h]]
         elif str(fc) in self.sd_clips[sd_vid]['custom_points']:
            sfc = str(fc)
            w = int(self.sd_clips[sd_vid]['custom_points'][sfc][2] / hdm_x)
            x = int(self.sd_clips[sd_vid]['custom_points'][sfc][0] / hdm_x ) - (w/2)
            y = int(self.sd_clips[sd_vid]['custom_points'][sfc][1] / hdm_y) - (w/2)
           

            cnts = [[x,y,w,w]]
         if fc in self.sd_clips[sd_vid]['deleted_points'] or str(fc) in self.sd_clips[sd_vid]['deleted_points']:
            cnts = []
            print(fc, "found in deleted points!")
            print("DELETE POINTS IS:", self.sd_clips[sd_vid]['deleted_points'])
         else:
            print(fc, "NOT found in deleted points!")
            print("DELETE POINTS IS:", self.sd_clips[sd_vid]['deleted_points'])

         print("AFTER OVERRIDE CNTS:", cnts)

         for cnt in cnts:
            x,y,w,h = cnt 
            if w > h:
               h = w
            else:
               w = h

            x1 = int(cnt[0] * hdm_x)
            y1 = int(cnt[1] * hdm_y)
            x2 = int(cnt[0] * hdm_x) + int(w * hdm_x)
            y2 = int(cnt[1] * hdm_y) + int(h * hdm_y)
            cx = ((x1 + x2) / 2) 
            cy = ((y1 + y2) / 2)
            if x2 - x1 > y2 - y1:
               radius = x2 - x1
            else:
               radius = y2 - y1
            meteor_int = np.sum(sub[y1:y2,x1:x2])
            if radius < 2:
               radius = 2

            if True:
               # for flux
               px1 = int((x1+x2)/2) - 50 
               px2 = int((x1+x2)/2) + 50 
               py1 = int((y1+y2)/2) - 50 
               py2 = int((y1+y2)/2) + 50 


               if px1 < 0:
                  px1 = 0
               if px2 > 1920:
                  px2 = 1920
               if py1 < 0:
                  py1 = 0
               if py2 > 1080:
                  py2 = 1080 
               pcx = ((px1 + px2) / 2) - px1
               pcy = ((py1 + py2) / 2) - py1
               temp = cv2.resize(subs[fc], (1920,1080))
               sub = cv2.resize(sub, (1920,1080))
               meteor_flux = do_photo(sub[py1:py2,px1:px2], (pcx,pcy), radius+1)
               if np.isnan(meteor_flux):
                  meteor_flux = 0
               if np.isnan(meteor_int):
                  meteor_int= 0

               # if this frame is insdie the deleted points or custom point fix it. 
               if fc in self.sd_clips[sd_vid]['deleted_points'] or str(fc) is self.sd_clips[sd_vid]['deleted_points']:
                  print("FRAME DELETED!")
               else:
                  frame_data[fc]['cnts'] = [[int(x1),int(y1),int(x2),int(y2),float(cx),float(cy),int(radius),int(meteor_int),int(meteor_flux)]]
               #print("FD:", frame_data[fc])
         print("BUILD FRAME DATA", fc, sd_vid)
         fc += 1

      #print("FD:", frame_data)
      return(frame_data, subs)


   #self.play_video(sd_vid, self.sd_clips[sd_vid]['frames'], self.sd_clips[sd_vid]['subs'], RF, self.sd_clips[sd_vid]['frame_data'], self.sd_clips[sd_vid]['stack_img'])
   #def play_video(self, sd_vid, frames, subs, RF, frame_data ,stack_img):

   def get_event_obs(self):
      # get event info frirst
      sql = """
            SELECT event_id, event_minute, revision, event_start_time, event_start_times, stations, obs_ids, lats, lons, event_status, run_date, run_times
              FROM events
             WHERE event_id = ?
      """
      svals = [self.event_id]
      self.cur.execute(sql, svals)
      rows = self.cur.fetchall()
      data = []
      #print(sql, svals)
      event_data = {}
      obs_data = {}
      for row in rows:
         (event_id, event_minute, revision, event_start_time, event_start_times, stations, obs_ids, lats, lons, event_status, run_date, run_times ) = row
         event_data['event_id'] = event_id
         event_data['event_minute'] = event_minute
         event_data['revision'] = revision 
         event_data['event_start_time'] = event_start_time
         event_data['event_start_times'] = json.loads(event_start_times)
         event_data['stations'] = json.loads(stations)
         event_data['obs_ids'] = json.loads(obs_ids )
         event_data['lats'] = json.loads(lats )
         event_data['lons'] = json.loads(lons )
         event_data['event_status'] = event_status 
         event_data['run_date'] = run_date 
         event_data['run_times'] = run_times

      lc = 0 
      st_pts = {}
      st_az_pts = {}
      obs_imgs = {}

      # THIS IS A BUG!!! OBS NEED TO BE UPDATED SOMEWHERE / SOMEHOW WHAT DO WE DO NOW!
      print("EVENT DATA:", event_data.keys())
      for obs_id in event_data['obs_ids']:
         sql = """
            SELECT event_id, event_minute, station_id, obs_id, fns, times, xs, ys, azs, els, ints, status, ignore 
              FROM event_obs
             WHERE obs_id = ?
            """
         svals = [obs_id]
         self.cur.execute(sql, svals)
         rows = self.cur.fetchall()
         for row in rows:
            (event_id, event_minute, station_id, obs_id, fns, times, xs, ys, azs, els, ints, status, ignore ) = row
            lat,lon,alt = self.station_loc[station_id][:3]
            obs_data[obs_id] = {}
            obs_data[obs_id]['event_id'] = event_data['event_id']
            obs_data[obs_id]['event_minute'] = event_data['event_minute']
            obs_data[obs_id]['station_id'] = station_id
            obs_data[obs_id]['obs_id'] = obs_id
            obs_data[obs_id]['lat'] = lat
            obs_data[obs_id]['lon'] = lon
            st_pts[station_id] = [lat,lon,station_id.replace("AMS", "")]

            obs_data[obs_id]['fns'] = json.loads(fns)
            obs_data[obs_id]['times'] = json.loads(times)
            obs_data[obs_id]['xs'] = json.loads(xs)
            obs_data[obs_id]['ys'] = json.loads(ys)
            obs_data[obs_id]['azs'] = json.loads(azs)
            obs_data[obs_id]['els'] = json.loads(els)
            obs_data[obs_id]['ints'] = json.loads(ints)
            obs_data[obs_id]['status'] = status 
            obs_data[obs_id]['ignore'] = ignore 
            obs_data[obs_id]['image_file'] =  self.local_evdir + self.event_id + "/" + obs_id + "-stacked.jpg"

            obs_data[obs_id]['az_start_point'] = self.find_point_from_az_dist(lat,lon,float(json.loads(azs)[0]),400)
            obs_data[obs_id]['az_end_point'] = self.find_point_from_az_dist(lat,lon,float(json.loads(azs)[-1]),400)
            st_az_pts[station_id] = [obs_data[obs_id]['az_start_point'], obs_data[obs_id]['az_end_point']]
            st_az_pts[obs_id] = [obs_data[obs_id]['az_start_point'], obs_data[obs_id]['az_end_point']]
            if os.path.exists( obs_data[obs_id]['image_file']):
               print("YES, FOUND:", obs_data[obs_id]['image_file'])
               obs_img = cv2.imread(obs_data[obs_id]['image_file'])
               obs_img = cv2.resize(obs_img, (640,360))
               obs_imgs[obs_id] = obs_img
            else:
               print("OBS ID IS:", obs_id)
               # as a fallback copy the cloud prev file if it is not already copied
               date = obs_id.replace(station_id + "_", "")[0:10]
               year = date[0:4]
               cloud_prev_file = self.cloud_dir + station_id + "/METEORS/" + year + "/" + date + "/" + obs_id + "-prev.jpg"
               local_prev_file = self.local_evdir + self.event_id + "/" + obs_id + "-prev.jpg"
               if os.path.exists(local_prev_file) is False:
                  if os.path.exists(cloud_prev_file) is True:
                     cmd = "cp " + cloud_prev_file + " " + local_prev_file
                     os.system(cmd)
                     #wget_cmds.append(cmd)
                  else:
                     print("No cloud file found!", cloud_prev_file)
               if os.path.exists(local_prev_file) is True:
                  print("Using prev image", local_prev_file)
                  prev_img = cv2.imread(local_prev_file)
                  try:
                     prev_img = cv2.resize(prev_img, (1920,1080))
                     obs_imgs[obs_id] = prev_img 
                  except:
                     print("No image could be found for:", obs_id)
               else:
                   print("No image could be found for:", obs_id)


               
         lc += 1

      # here we should check how things intersect and mark obs that don't 
      # lat/lon & bearing of 2 stations
      ipoints = {}
      points = [] 
      lines = [] 
      failed_combos = [] 
      for obs_id_1 in obs_data:
         if "obs_start_points" not in obs_data[obs_id_1]:
            obs_data[obs_id_1]['obs_start_points'] = []
            obs_data[obs_id_1]['obs_end_points'] = []
         for obs_id_2 in obs_data:
            if "obs_start_points" not in obs_data[obs_id_2]:
               obs_data[obs_id_2]['obs_start_points'] = []
               obs_data[obs_id_2]['obs_end_points'] = []
            station1 = obs_data[obs_id_1]['station_id']
            station2 = obs_data[obs_id_2]['station_id']
            if station1 == station2:
               continue
            itemp = sorted([obs_id_1, obs_id_2])
            ikey = itemp[0] + "__" + itemp[1]
            if ikey in ipoints:
               continue

            x1 = obs_data[obs_id_1]['lon'] 
            y1 = obs_data[obs_id_1]['lat'] 
            brng1 = obs_data[obs_id_1]['azs'][0]

            x2 = obs_data[obs_id_2]['lon'] 
            y2 = obs_data[obs_id_2]['lat'] 
            brng2 = obs_data[obs_id_2]['azs'][0]

            #start point
            try:
               ipoint = geo_intersec_point(x1, y1, brng1, x2, y2, brng2)
            except:
               ipoint = [0,0]



            #end point
            brng1 = obs_data[obs_id_1]['azs'][-1]
            brng2 = obs_data[obs_id_2]['azs'][-1]
            try:
               end_ipoint = geo_intersec_point(x1, y1, brng1, x2, y2, brng2)
            except:
               end_ipoint = [0,0]


            if ipoint[0] == True or end_ipoint[0] == True:
               failed_combos.append(ikey)
               # intersect failed...
            else:
               # intersect passed
               end_failed = False
               start_failed = False
               try:
                  start_station_dist = dist_between_two_points(y1, x1, ipoint[1]['y3'], ipoint[1]['x3']) 
               except:
                  start_station_dist = 9999
               print("COMBO:", obs_id_1, obs_id_2)
               print("SSD:", start_station_dist)

               try:
                  end_station_dist = dist_between_two_points(y1, x1, end_ipoint[1]['y3'], ipoint[1]['x3']) 
               except:
                  end_station_dist = 9999
               print("ESD:", end_station_dist)

               # only add a point if its within < 800 km away
               if end_station_dist > 800 and start_station_dist > 800:
                  start_failed = True
                  end_failed = True

               if start_failed is False and end_failed is False:
                  print("ADD POINT:", obs_id_1, obs_id_2, ipoint[1]['x3'], ipoint[1]['y3'])
                  obs_data[obs_id_1]['obs_start_points'].append(( ipoint[1]['y3'], ipoint[1]['x3']))
                  obs_data[obs_id_2]['obs_start_points'].append(( ipoint[1]['y3'], ipoint[1]['x3']))

                  print(end_ipoint)
                  obs_data[obs_id_1]['obs_end_points'].append(( end_ipoint[1]['y3'], end_ipoint[1]['x3']))
                  obs_data[obs_id_2]['obs_end_points'].append(( end_ipoint[1]['y3'], end_ipoint[1]['x3']))
                  #points.append((ipoint[1]['x3'], ipoint[1]['y3'], 'i'))
            if len(obs_data[obs_id_1]['obs_end_points']) == 0 or len(obs_data[obs_id_1]['obs_start_points']) == 0:
               obs_data[obs_id_1]['status'] = "INVALID"
               obs_data[obs_id_1]['ignore'] = True
            else:
               obs_data[obs_id_1]['status'] = "VALID"
               obs_data[obs_id_1]['ignore'] = False 

            if len(obs_data[obs_id_2]['obs_end_points']) == 0 or len(obs_data[obs_id_2]['obs_start_points']) == 0:
               obs_data[obs_id_2]['status'] = "INVALID"
               obs_data[obs_id_2]['ignore'] = True
            else:
               obs_data[obs_id_2]['status'] = "VALID"
               obs_data[obs_id_2]['ignore'] = False 


            ipoints[ikey] = ipoint
            #print("IPOINT:", ikey, ipoint)

      # determine which stations are valid or not based on successful intersects
      valid_stations = {}
      for obs_id in obs_data:
         station_id = obs_id.split("_")[0]
         if station_id not in valid_stations:
            valid_stations[station_id] = {}
            valid_stations[station_id]['good_obs'] = 0
            valid_stations[station_id]['bad_obs'] = 0
         if obs_data[obs_id]['ignore'] is True:
            valid_stations[station_id]['bad_obs'] += 1
         else:
            valid_stations[station_id]['good_obs'] += 1

      for st in valid_stations:
         if valid_stations[st]['good_obs'] > 0:
            print("VALID STATIONS:", st, valid_stations[st])
         if valid_stations[st]['good_obs'] > 0 :
            valid_stations[station_id]['good_ratio'] = valid_stations[st]['good_obs'] / valid_stations[st]['good_obs'] + valid_stations[st]['bad_obs']
            print("GOOD RATIO:", st, valid_stations[station_id]['good_ratio'])
         else:
            valid_stations[station_id]['good_ratio'] = 0

         

      self.echo_event_data(event_data, obs_data)

      if True:
         for st in st_pts:
            sp, ep = st_az_pts[st]
            station = st 
            slat = st_pts[st][0]
            slon = st_pts[st][1]
        
            if valid_stations[station_id]['good_ratio'] > 0:
               points.append((slat,slon,station,"green","o"))
            else:
               points.append((slat,slon,station,"red","x"))

            lines.append((st_pts[st][0], st_pts[st][1], st_az_pts[st][0][0] , st_az_pts[st][0][1], 'green'))
            lines.append((st_pts[st][0], st_pts[st][1], st_az_pts[st][1][0] , st_az_pts[st][1][1], 'orange'))


      for obs_id in obs_data:
         for row in obs_data[obs_id_1]['obs_start_points']:
            points.append((row[0], row[1], "s"))
         for row in obs_data[obs_id_1]['obs_end_points']:
            points.append((row[0], row[1], "e"))
         st = obs_id.split("_")[0]
         med_end_lat = np.mean([row[0] for row in obs_data[obs_id_1]['obs_end_points']])
         med_end_lon = np.mean([row[1] for row in obs_data[obs_id_1]['obs_end_points']])
         med_start_lat = np.mean([row[0] for row in obs_data[obs_id_1]['obs_start_points']])
         med_start_lon = np.mean([row[1] for row in obs_data[obs_id_1]['obs_start_points']])
         lines.append((st_pts[st][0], st_pts[st][1], med_start_lat, med_start_lon, 'pink'))
         lines.append((st_pts[st][0], st_pts[st][1], med_end_lat, med_end_lon, 'purple'))


      #lat1, lon1,lat2,lon2,cl
      #map_img = make_map(points, lines)
      try:
         map_img = make_map(points, lines)
      except:
         print("FAILED TO MAP:", points, lines)
         map_img = np.zeros((1080,1920,3),dtype=np.uint8)
         print("POINTS:", points)
         print("LINES:", lines)
         input("MAP FAILED WHY!")

         map_img = make_map(points, lines)

      x1 = int(map_img.shape[1] / 2) - 960 
      x2 = int(map_img.shape[1] / 2) + 960 
      y1 = int(map_img.shape[0] / 2) - 540 
      y2 = int(map_img.shape[0] / 2) + 540 
      new_img = map_img[y1:y2,x1:x2]
      return(event_data, obs_data, new_img, obs_imgs)

   def echo_event_data(self,event_data, obs_data):
      tb = pt()
      tb.field_names = ['Field', 'Value']
      for key in event_data:
         print(key, event_data[key])
         if isinstance(event_data[key], list) is False:
            tb.add_row([key, event_data[key]])
         else:
            tb.add_row([key, len(event_data[key])])
      report = str(tb)
      report += "\n\n"

      for obs_id in obs_data:
         tb = pt()
         tb.field_names = ['Field', 'Value']
         for key in obs_data[obs_id]:
            if isinstance(obs_data[obs_id][key], list) is False:
               tb.add_row([key, obs_data[obs_id][key]])
            elif "points" in key: 
               tb.add_row([key, obs_data[obs_id][key]])
            else:
               if key == "azs" or key == "els":
                  tb.add_row([key, str( round(obs_data[obs_id][key][0],2)) + " / " + str( round(obs_data[obs_id][key][-1],2 )) ])
               else:
                  tb.add_row([key, str( obs_data[obs_id][key][0]) + " / " + str( obs_data[obs_id][key][-1] ) ])
         report += str(tb)
         report += "\n"
      print(report)

      # MFD FOR EACH
      print ("METEOR FRAME DATA")
      for obs_id in obs_data:
         print("OBS:", obs_id, len(obs_data[obs_id]['fns']), "frames")
         #for i in range(0, len(obs_data[obs_id]['fns'])):
         #   print("{} {} {} {} {} ".format(obs_id, obs_data[obs_id]['fns'][i], obs_data[obs_id]['times'][i], obs_data[obs_id]['azs'][i], obs_data[obs_id]['els'][i]))




   def find_point_from_az_dist(self,lat,lon,az,dist):
      import math

      R = 6378.1 #Radius of the Earth
      brng = math.radians(az) #Bearing is 90 degrees converted to radians.
      d = dist #Distance in km


      lat1 = math.radians(lat) #Current lat point converted to radians
      lon1 = math.radians(lon) #Current long point converted to radians

      lat2 = math.asin( math.sin(lat1)*math.cos(d/R) +
      math.cos(lat1)*math.sin(d/R)*math.cos(brng))

      lon2 = lon1 + math.atan2(math.sin(brng)*math.sin(d/R)*math.cos(lat1),
             math.cos(d/R)-math.sin(lat1)*math.sin(lat2))

      lat2 = math.degrees(lat2)
      lon2 = math.degrees(lon2)

      return(lat2, lon2)


   def play_edit_video(self, sd_vid):
      print("VID:", sd_vid)
      event_data, obs_data, map_img,obs_imgs = self.get_event_obs(sd_vid.replace(".mp4", ""))
      cv2.imshow('pepe', map_img)
      cv2.waitKey(30)
      for key in obs_imgs:
         cv2.imshow('pepe', obs_imgs[key])
         cv2.waitKey(30)

      print("OBS DATA",sd_vid, obs_data) 


   def play_video(self, sd_vid, RF):
      # edits should go into the DB!
      self.play_edit_video(sd_vid)
      return()

      frames = self.sd_clips[sd_vid]['frames']

      subs = self.sd_clips[sd_vid]['subs']
      frame_data = self.sd_clips[sd_vid]['frame_data']
      stack_img = self.sd_clips[sd_vid]['stack_img']
      if "custom_points" in self.sd_clips[sd_vid]:
         custom_points = self.sd_clips[sd_vid]['custom_points']
      else:
         custom_points = {}
      if "deleted_points" in self.sd_clips[sd_vid]:
         deleted_points = self.sd_clips[sd_vid]['deleted_points']
      else:
         deleted_points = {}

      print("SDCD", self.sd_clips[sd_vid].keys())

      temp = []
      cv2.namedWindow('pepe')
      cv2.setMouseCallback('pepe',self.meteor_mouse_click)
      hdm_x = 3
      hdm_y = 3
      go = True
      self.fc = 0
      self.deleted_points = {}
      self.custom_points = {}
      if sd_vid in self.sd_clips:
         if "custom_points" in self.sd_clips[sd_vid]:
            self.custom_points = self.sd_clips[sd_vid]['custom_points']
         if "deleted_points" in self.sd_clips[sd_vid]:
            self.deleted_points = self.sd_clips[sd_vid]['deleted_points']
      else:
         print(sd_vid, "not found in sd_clips data")

      print("CUSTOM", self.custom_points)
      print("DEL", self.deleted_points)
      stack_img= cv2.resize(stack_img, (1920,1080))
      print("KEYS FROM SD_CLIPS", self.sd_clips[sd_vid].keys())

      while go == True:
         
         if self.fc >= len(frames) or self.fc < 0:
            self.fc = 0
         frame = frames[self.fc]
         orig_frame = cv2.resize(frame.copy(), (1920,1080))
         self.active_frame = cv2.resize(frame.copy(), (1920,1080))

         frame = cv2.resize(frame, (1920,1080))
         show_frame = RF.frame_template("1920_pip1_tl", [frame])
         cnts = []
         if self.fc in self.custom_points:
            if len(self.custom_points[self.fc]) == 3:
               x,y,size = self.custom_points[self.fc]
               x1 = x - size
               x2 = x + size
               y1 = y - size
               y2 = y + size
               radius = size 
               meteor_int = 0
               meteor_flux = 0
               cx = int((x1 + x2) / 2)
               cy = int((y1 + y2) / 2)

               px1 = int((x1+x2)/2) - 50 
               px2 = int((x1+x2)/2) + 50 
               py1 = int((y1+y2)/2) - 50 
               py2 = int((y1+y2)/2) + 50 

               if px1 < 0:
                  px1 = 0
               if px2 > 1920:
                  px2 = 1920
               if py1 < 0:
                  py1 = 0
               if py2 > 1080:
                  py2 = 1080 
               pcx = ((px1 + px2) / 2) - px1
               pcy = ((py1 + py2) / 2) - py1
               temp = cv2.resize(subs[self.fc], (1920,1080))
               meteor_flux = do_photo(temp[py1:py2,px1:px2], (pcx,pcy), radius+1)

               frame_data[self.fc]['cnts'] = [[x1,y1,x2,y2,cx,cy,radius,meteor_int,meteor_flux]]

         if self.fc in frame_data:
            print(self.fc, frame_data[self.fc])
            if "cnts" in frame_data[self.fc]:
               cnts = frame_data[self.fc]['cnts']
         if len(cnts) >= 1 and self.fc not in self.deleted_points : #and self.fc not in self.custom_points:
               print("CNTS:", cnts[0])
               (x1,y1,x2,y2,cx,cy,radius,meteor_int,meteor_flux) = cnts[0]
               
               px1 = int((x1+x2)/2) - 50 
               px2 = int((x1+x2)/2) + 50 
               py1 = int((y1+y2)/2) - 50 
               py2 = int((y1+y2)/2) + 50 

               if px1 < 0:
                  px1 = 0
               if px2 > 1920:
                  px2 = 1920
               if py1 < 0:
                  py1 = 0
               if py2 > 1080:
                  py2 = 1080 
               pcx = ((px1 + px2) / 2) - px1
               pcy = ((py1 + py2) / 2) - py1

               crop_img = orig_frame[py1:py2,px1:px2]
               cv2.rectangle(frame, (int(x1), int(y1)), (int(x2) , int(y2) ), (255, 255, 255), 1)
               #if np.isnan(meteor_flux) is False:
               cv2.putText(frame, "FLUX" + str(int(meteor_flux)),  (x1,y2+10), cv2.FONT_HERSHEY_SIMPLEX, .6, (0,255,0), 1)
               cv2.putText(frame, "INT" + str(int(meteor_int)),  (x1,y2+20), cv2.FONT_HERSHEY_SIMPLEX, .6, (0,128,0), 1)
               crop_img = cv2.resize(crop_img,(400,400))
               cv2.line(crop_img , (int(200),int(0)), (int(200),int(400)), (255,255,255), 1)
               cv2.line(crop_img , (int(0),int(200)), (int(400),int(200)), (255,255,255), 1)
               show_frame = RF.frame_template("1920_pip1_tl", [frame, crop_img])

         else:
            print("NO OBJECTS!")
            show_frame = RF.frame_template("1920_pip1_tl", [frame])

         cv2.putText(show_frame, str(self.fc) + "",  (1800,25), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 1)
         cv2.imshow('pepe', show_frame)
         self.key = cv2.waitKey(0)
         if self.key == 102:
            print("NEXT", self.fc)
            self.fc += 1
         elif self.key == 97:
            print("PREV", self.fc)
            self.fc -= 1
         elif self.key == 27:
            go = False 
         elif self.key == 120:
            print("DELETE FRAME DATA", self.fc, frame_data[self.fc])
            self.deleted_points[self.fc] = True
               # delete frame data 
            if self.fc in self.custom_points:
               del self.custom_points[self.fc]
            frame_data[self.fc]['cnts'] = []
            print("AFTER DELETE FRAME DATA", frame_data[self.fc])
            self.fc += 1
         elif self.key == 27:
            go = False

      # END WHILE LOOP

      objects = self.frame_data_to_objects(frame_data)
      ints = []
      f = plt.figure()

      show_img = RF.frame_template("1920_1p", [stack_img])

      for obj in objects:
         xs = []
         ys = []
         if len(objects[obj]['oxs']) < 3:
            continue
         
         mx = int(np.mean(objects[obj]['oxs']))
         my = int(np.mean(objects[obj]['oys']))
         if max((objects[obj]['oxs'])) - min((objects[obj]['oxs'])) > max(objects[obj]['oys']) - min(objects[obj]['oys']):
            radius = max((objects[obj]['oxs'])) - min((objects[obj]['oxs']))
         else:
            radius = max((objects[obj]['oys'])) - min((objects[obj]['oys']))
         print("RAD:", mx,my, radius)
         cv2.circle(show_img, (mx,my), int(radius), (128,128,128),1)
         cv2.putText(show_img, str(obj),  (mx,my), cv2.FONT_HERSHEY_SIMPLEX, .8, (0,255,0), 1)
         cv2.imshow('pepe', show_img)
         cv2.waitKey(30)
      cv2.waitKey(30)
      
      return(frame_data, self.deleted_points, self.custom_points)

   def meteor_mouse_click(self,event,x,y,flags,param):
      if event == cv2.EVENT_LBUTTONDBLCLK:
         global mouseX, mouseY
         mouseX, mouseY = x,y 
         if self.fc in self.deleted_points:
            del self.deleted_points[self.fc]
         temp = self.active_frame.copy()
         bw_temp =  cv2.cvtColor(temp, cv2.COLOR_BGR2GRAY)

         # get roi around click
         x1 = x - 50
         x2 = x + 50
         y1 = y - 50
         y2 = y + 50
         if x1 < 0:
            x1 = 0
         if x2 > 1920 :
            x2 = 1920 
         if y1 < 0:
            y1 = 0
         if y2 > 1080:
            y2 = 1080  
         temp_crop = temp[y1:y2,x1:x2]
         bw_temp_crop =  cv2.cvtColor(temp_crop, cv2.COLOR_BGR2GRAY)
         max_val = bw_temp[y,x]
         thresh_val = int(max_val * .5)

         print("VALS:", mouseX,mouseY, self.fc, max_val, thresh_val)

         _, thresh_image = cv2.threshold(bw_temp_crop, thresh_val, 255, cv2.THRESH_BINARY)
         cv2.imshow('ccc', thresh_image)
         cv2.waitKey(30)
         cnts = get_contours_in_image(thresh_image)
         if len(cnts) > 1:
            cnts = sorted(cnts, key=lambda x: x[2] * x[3], reverse=True)
            cnts = cnts[0:1]

         for xx,yy,ww,hh in cnts:
            cv2.rectangle(temp, (int(x1+xx), int(y1+yy)), (int(x1+xx+ww) , int(y1+yy+hh) ), (255, 255, 255), 1)
         if ww > hh:
            hh = ww
         else:
            ww = hh

         self.custom_points[self.fc] = [int(mouseX),int(mouseY),int(ww)]
         cv2.circle(temp, (int(x),int(y)), int(ww), (128,128,128),1)
         cv2.imshow('pepe', temp)


   def station_events(self, date):
      self.set_dates(date)
      station_events = {}
      all_events = load_json_file(self.all_events_file)
      for evd in all_events:
         #print(evd['event_id'], evd['stations'], evd['files']) 
         event_id = evd['event_id']
         for i in range(0, len(evd['stations'])):
            station_id = evd['stations'][i]
            obs_id = evd['files'][i]
            dict_key = station_id + "_" + obs_id
            if dict_key in self.obs_dict:
               obs_data = self.obs_dict[dict_key]
            else:
               #print("NO OBS DATA!", dict_key)
               obs_data = {}


            obs_id = obs_id.replace(".mp4", "")
            obs_id = obs_id.replace(date + "_", "")
            if station_id not in station_events:
               station_events[station_id] = {}
            if obs_id not in station_events[station_id]:
               station_events[station_id][obs_id] = event_id
            print(station_id, obs_id, event_id)
      save_json_file(self.station_events_file, station_events, True)
      print("SAVED:", self.station_events_file)
      

   def review_data(self):
      # quick review!
      for sd_vid in self.sd_clips:
         print(sd_vid, self.sd_clips[sd_vid].keys())
         if "custom_points" in self.sd_clips[sd_vid]:
            print(self.sd_clips[sd_vid]['custom_points'])
      input("ENTER TO CONT")


   def resolve_event(self, event_id):
      # This should pull down the latest OBS data from the API
      # so that it is current. Then do a FRESH resolve.
      # remove obs/stations if needed.
      # respect ignores etc. 

      date = self.event_id_to_date(event_id)
      self.set_dates(date)
      self.load_stations_file()

      # select main event info from the local sqlite DB
      sql = """
            SELECT event_id, event_minute, revision, stations, obs_ids, event_start_time, event_start_times,
                   lats, lons, event_status, run_date, run_times
              FROM events
             WHERE event_id = ?
          ORDER BY run_date desc 
             LIMIT 1

      """
      vals = [event_id]
      self.cur.execute(sql, vals)
      rows = self.cur.fetchall()

      xx = 0
      for row in rows:
         
         (event_id, event_minute, revision, stations, obs_ids, event_start_time, event_start_times,  \
                 lats, lons, event_status, run_date, run_times) = row

         stations = json.loads(stations)
         obs_ids = json.loads(obs_ids)
         event_start_times = json.loads(event_start_times)
         lats = json.loads(lons)
         temp_obs = {}
         
         ignore = ['2022_09_24_21_28_00_000_011134-trim-0012']

         # for each obs associated with this event
         # load the MOST RECENT OBS DATA
         # into the temp_obs array!

         for obs_id in obs_ids:
            ig = False
            for item in ignore:
               if item in obs_id:
                  print("IGNORE:", obs_id)
                  ig = True
            if ig is True:
               print("IGNORE:", ignore)
               continue
            st_id = obs_id.split("_")[0]
            vid = obs_id.replace(st_id + "_", "") + ".mp4"
            dict_key = obs_id + ".mp4"
            if st_id not in temp_obs:
               temp_obs[st_id] = {}

            # here we should fetch the latest obs from AWS 
            # to make sure we pick up any edits?
            print(st_id, dict_key)
            sd_vid = dict_key.replace(st_id + "_", "")
            #if vid not in temp_obs[st_id]:
            if dict_key not in self.obs_dict:
               self.obs_dict[dict_key] = {}
            if True:
               if True:
                  self.obs_dict[dict_key]['loc'] = [float(self.station_dict[st_id]['lat']), float(self.station_dict[st_id]['lon']), float(self.station_dict[st_id]['alt'])]
                  # HERE WE SHOULD GET NEW OBS DATA DIRECT FROM DYNA DB OR REFRESH THE OBS DICT?
                  # CALL THE SEARCH OBS DYN FUNC FOR THIS! NOT HARD???
                  dobs = get_obs(st_id, sd_vid)
                  dobs['loc'] = self.obs_dict[dict_key]['loc']
                  temp_obs = convert_dy_obs(dobs, temp_obs)
                  #temp_obs = convert_dy_obs(self.obs_dict[dict_key], temp_obs)
                  #print("OBS DICT FOR:", dict_key, self.obs_dict[dict_key])
                  #print("TEMP OBS KEYS:", dict_key, temp_obs.keys())
               else:
                  print(dict_key, "not in obsdict. try deleting the file.")
                  print( self.obs_dict_file)
                  #exit()

         self.good_obs = temp_obs
         #for st in temp_obs:
         #   print("STATION:", st)
         #   for vd in temp_obs[st]:
         #      print("VID:", vd)
         #      print(temp_obs[st][vd].keys())

         ev_dir = self.local_evdir + "/" + event_id
         if os.path.exists(ev_dir) is False:
            os.makedirs(ev_dir)
         good_obs_file = ev_dir + "/" + event_id + "_GOOD_OBS.json"
         #if os.path.exists(good_obs_file) is False:
         save_json_file(good_obs_file, temp_obs, True)
         print("RESOLVING EVENT:", event_id)

         self.solve_event(event_id, temp_obs, 1, 1)
         xx += 1

      cmd = "rsync -av --update " + self.local_evdir + "/" + event_id + "/* " + self.cloud_evdir + "/" + event_id + "/"
      print("SKIPPING (for now)", cmd)
      #os.system(cmd)

   def make_event_page(self, event_id):
      event_day = self.event_id_to_date(event_id)
      self.set_dates(event_day)
      good_obs_file = self.local_evdir + event_id + "/" + event_id + "_GOOD_OBS.json"   
      temp_obs = load_json_file(good_obs_file)
      dynamodb = boto3.resource('dynamodb')
      solve_dir = self.local_evdir + event_id + "/" 
      event_report(dynamodb, event_id, solve_dir, solve_dir, temp_obs)

   def day_load_solves(self, date):

      solve_jobs = []
      self.set_dates(date)
      self.load_stations_file()
      self.errors = []
      if os.path.exists(self.obs_review_file) is True:
         self.ai_data = load_json_file(self.obs_review_file)
      else:
         self.ai_data = {}
      sql = """
            SELECT event_id, event_minute, revision, stations, obs_ids, event_start_time, event_start_times,  
                   lats, lons, event_status, run_date, run_times
              FROM events
             WHERE event_minute like ?
      """
      vals = [date + "%"]
      self.cur.execute(sql, vals)
      rows = self.cur.fetchall()
      print("ROWS:", len(rows))
      print("OBS DICT:", len(self.obs_dict.keys()))
      c = 1
      self.temp_obs = {}
      self.event_sol_data = {}
      self.event_sql_data = {}

      for row in rows:
         (event_id, event_minute, revision, stations, obs_ids, event_start_time, event_start_times,  \
                 lats, lons, event_status, run_date, run_times) = row
         self.event_sql_data[event_id] = (event_id, event_minute, revision, stations,  obs_ids, \
                 event_start_time, event_start_times, lats, lons, event_status, run_date, run_times)
         # decode json saved data
         stations = json.loads(stations)
         obs_ids = json.loads(obs_ids)
         event_start_times = json.loads(event_start_times)
         lats = json.loads(lons)

         #loop over obs and check for dupes
         for ob_id in obs_ids:
            if ob_id not in self.temp_obs :
               self.temp_obs[ob_id] = 0
            self.temp_obs[ob_id] += 1
            if self.temp_obs[ob_id] > 1:
               print("DUPE OBS USED!", ob_id, event_id)
         print("EV:",c,  event_id, event_status )
         c += 1

         # load the event.json

         ev_json_file = self.local_evdir + event_id + "/" + event_id + "-event.json"
         if os.path.exists(ev_json_file) is True:
            ev_data = load_json_file(ev_json_file)
            
         else:
            print(ev_json_file, "NOT FOUND!")
            ev_data = None
         self.event_sol_data[event_id] = ev_data

      # now all data is loaded into the arrays.
      # first make sure the SQL summary / event status is accurate 
      # to what is on the file system. Update as needed. 
      for event_id in self.event_sql_data:
         (tevent_id, event_minute, revision, stations,  obs_ids, event_start_time, event_start_times, 
                 lats, lons, event_status, run_date, run_times) = self.event_sql_data[event_id]
         if event_id in self.event_sol_data:
            sol_data = self.event_sol_data[event_id]
         else:
            sol_data = None
            self.event_sol_data[event_id] = None
         if sol_data is not None:
            sol_data['event_status'] = event_status
            (sol_status, v_init, v_avg, start_ele, end_ele, a, e) = self.eval_sol(sol_data)
            self.event_sol_data[event_id]['sol_status'] = sol_status
            print(event_id, sol_status)
            if a < 0 or e >= 1 or start_ele > 160000:
               event_status = "SOLVED:BAD"

            elif "GOOD" in sol_status:
               event_status = "SOLVED:GOOD"
            else:
               event_status = "SOLVED:BAD"
            sql = "UPDATE events set event_status = ? WHERE event_id = ?"
            vals = [event_status, event_id]
            print(sql, vals)
            self.cur.execute(sql, vals)
            self.con.commit()

            if "BAD" in sol_status:
               self.event_sol_data[event_id]['event_status'] = "BAD"
            # OBS STUFF / AI?
            #self.view_obs_ids(date, obs_ids)
            self.update_obs_ids(event_id,obs_ids)
            #print(event_status, sol_data.keys())

   def update_obs_ids(self, event_id, obs_ids):
      if isinstance(obs_ids, str) is True:
         obs_ids = json.loads(obs_ids)


      for ob_id in obs_ids:
         sql = "UPDATE event_obs set event_id = ? WHERE obs_id = ?"
         vals = [event_id, ob_id]
         print(sql, vals)
         self.cur.execute(sql, vals)
         self.con.commit()

   def eval_sol(self, data):
      event_status = data['event_status']
      v_init = round(data['traj']['v_init'] / 1000,2)
      v_avg = round(data['traj']['v_avg'] /1000,2)
      end_ele = round(data['traj']['end_ele']  / 1000,2)
      start_ele = round(data['traj']['start_ele'] / 1000,2)

      if "orb" in data:
         if data['orb'] is not None:
            if data['orb']['a'] is not None:
               a = data['orb']['a'] 
               e = data['orb']['e'] 
            else:
               a = -1
               e = 99
         else:
            a = -1
            e = 99
      else:
         a = -1
         e = 99
      sol_status = ""
      if v_init > 100 or v_avg > 100:
         sol_status += "BAD_VEL;"
      if start_ele >= 200 or start_ele < 0:
         sol_status += "BAD_TRAJ_START;"
      if end_ele >= 200 or end_ele < 0:
         sol_status += "BAD_TRAJ_END;"
      if a < 0:
         sol_status += "BAD_ORB_a;"
      if e > 1:
         sol_status += "BAD_ORB_e;"
      if sol_status == "":
         sol_status = "GOOD"

      return(sol_status, v_init, v_avg, start_ele, end_ele, a, e)

   def check_ai(self, ai_data):
      print(ai_data)
      meteor_obj_conf = 0
      meteor_prev_conf = 0
      if "objects" in ai_data:
         for row in ai_data['objects']:
            con = row[0]
            if con > 50:
               meteor_obj_conf = con
      if "ai" in ai_data:
         meteor_prev_conf = ai_data['ai']['meteor_prev_yn']
      print("METEOR OBJ FOUND:", meteor_obj_conf)
      print("METEOR PREV FOUND:", meteor_prev_conf)
      return(meteor_obj_conf, meteor_prev_conf)

   def view_obs_ids(self, date, obs_ids):
      year = date[0:4]
      imgs = []
      self.missing_prev_files = {}
      if isinstance(obs_ids, str) is True:
         obs_ids = json.loads(obs_ids)

      for ob_id in obs_ids:
         if "AMS" in ob_id:
            st_id = ob_id.split("_")[0]
         sd_vid = ob_id.replace(st_id + "_", "") + ".mp4" 
         if sd_vid in self.ai_data:
            label_data = self.ai_data[sd_vid]
            conf1, conf2 = self.check_ai(label_data)
         else:
            label_data = None
            local_prev_dir = self.local_evdir + "OBS/" 
            if os.path.exists(local_prev_dir) is False:
               os.makedirs(local_prev_dir)
            
            cloud_prev_file = "/mnt/archive.allsky.tv/" + st_id + "/METEORS/" + year + "/" + date + "/" + ob_id + "-prev.jpg"
            local_prev_file = self.local_evdir + "OBS/" + ob_id + "-prev.jpg"
            local_prev_file_alt = self.local_evdir + sd_vid.replace(".mp4", "-prev.jpg")
            if os.path.exists(local_prev_file_alt) is True:
               cmd = "mv " + local_prev_file_alt + " " + local_prev_file
               print("MOVE MIS_NAMED LOCAL FILE!")
               print(cmd)
               os.command(cmd)

            print(cloud_prev_file)
            print("NO AI DATA!!!")
            if os.path.exists(local_prev_file) is False:
               print("NO LOCAL PREV FILE!", local_prev_file)
               if os.path.exists(cloud_prev_file) is False:
                  print("NO CLOUD PREV FILE!", cloud_prev_file)
                  self.missing_prev_files[ob_id] = cloud_prev_file
                  self.reject_obs(st_id, ob_id, "NO PREV FILE")
               else:
                  cmd = "cp " + cloud_prev_file + " " + local_prev_file
                  print("COPY THE FILE!", cmd)
                  os.system(cmd)

         ev_file = self.local_evdir + "OBS/" + ob_id + "-prev.jpg"
         if os.path.exists(ev_file) is False:
            ev_file = ev_file.replace(st_id + "_", "")         
         if os.path.exists(ev_file) is True:
            img = cv2.imread(ev_file)
            imgs.append(img)
            print("LABELS:", label_data)
            cv2.imshow('pepe', img)
            cv2.waitKey(30)
         print(ev_file)
      print("MISSING PREV FILES:", len(self.missing_prev_files.keys()))

   def reject_obs(self, st_id, ob_id, reject_desc):
      sql = "INSERT OR REPLACE INTO rejected_obs (obs_id, reject_desc) VALUES(?,?)" 
      if st_id not in ob_id:
         ob_id = st_id + "_" + ob_id
      vals = [ob_id, reject_desc]
      self.cur.execute(sql, vals)
      self.con.commit()
      print("REJECTED:", st_id, ob_id, reject_desc)

      sql = "UPDATE event_obs set ignore = 1, status = ? WHERE obs_id = ?"
      vals = [reject_desc, ob_id]
      self.cur.execute(sql, vals)
      self.con.commit()


   def day_solve(self, date=None,force=0):
      solve_jobs = []
      self.set_dates(date)
      self.load_stations_file()
      self.errors = []
      sql = """
            SELECT event_id, event_minute, revision, stations, obs_ids, event_start_time, event_start_times,  
                   lats, lons, event_status, run_date, run_times
              FROM events
             WHERE event_minute like ?
      """
      vals = [date + "%"]
      self.cur.execute(sql, vals)
      rows = self.cur.fetchall()
      for row in rows:
         (event_id, event_minute, revision, stations, obs_ids, event_start_time, event_start_times,  \
                 lats, lons, event_status, run_date, run_times) = row
         
         print("LOADING EVENT:", event_id, event_status)
         stations = json.loads(stations)
         obs_ids = json.loads(obs_ids)
         event_start_times = json.loads(event_start_times)
         lats = json.loads(lons)
         temp_obs = {}
         if event_status == "SOLVED":
            continue
         for obs_id in obs_ids:
            st_id = obs_id.split("_")[0]
            vid = obs_id.replace(st_id + "_", "") + ".mp4"
            dict_key = obs_id + ".mp4"
            if st_id not in temp_obs:
               temp_obs[st_id] = {}
            if vid not in temp_obs[st_id]:
               try:
                  self.obs_dict[dict_key]['loc'] = [float(self.station_dict[st_id]['lat']), float(self.station_dict[st_id]['lon']), float(self.station_dict[st_id]['alt'])]
                  temp_obs = convert_dy_obs(self.obs_dict[dict_key], temp_obs)
               except:
                  print("Geo error with station!", st_id)
                  self.errors.append(("STATION GEO ERROR", st_id))

         #for st in temp_obs:
         #   for vd in temp_obs[st]:
         #      print(temp_obs[st][vd].keys())

      
         if event_status == "PENDING":
            solve_jobs.append((event_id, event_status, temp_obs))

         #self.solve_event(event_id, temp_obs, 1, force)
         
      cmd = "rsync -auv " + self.local_evdir + "/* " + self.cloud_evdir + "/"
      print(cmd)
      #os.system(cmd)
      for job in solve_jobs:
         print("JOB:", job[0], job[1])
      self.run_jobs(solve_jobs)
      #for job in solve_jobs:
      #   print(job[0], job[1])
      print("FINISHED RUN JOBS!", len(solve_jobs))

   def fast_cmds(self, jobs):
      # parallel process list of system cmds
      thread = {}
      if os.path.exists("cores.json") == 1:
         temp = load_json_file("cores.json")
         cores = temp['cores']
      else:
         cores = 4
      if cores > len(jobs):
         cores = 4
      cc = 0

      jobs_per_proc = int(len(jobs)/(cores-1))
      for i in range(0,cores):
         start = i * jobs_per_proc
         end = start + jobs_per_proc + 1
         if end > len(jobs):
            end = len(jobs)
         print(i, start, end)
         thread[i] = Process(target=self.cmd_runner, args=("thread" + str(i), jobs[start:end]))

      for i in range(0,cores):
         thread[i].start()
      for i in range(0,cores):
         thread[i].join()

   def cmd_runner(self, thread_number, cmds):
      for cmd in cmds:
         print("RUN", thread_number, cmd)
         os.system(cmd)

   def run_jobs(self, jobs):
      thread = {}
      if os.path.exists("cores.json") == 1:
         temp = load_json_file("cores.json")
         cores = temp['cores']
      else:
         cores = 4
      if cores > len(jobs):
         cores = 4
      cc = 0

      jobs_per_proc = int(len(jobs)/(cores-1))
      for i in range(0,cores):
         start = i * jobs_per_proc
         end = start + jobs_per_proc + 1
         if end > len(jobs):
            end = len(jobs)
         print(i, start, end)
         thread[i] = Process(target=self.wmpl_worker, args=("thread" + str(i), jobs[start:end]))

      for i in range(0,cores):
         thread[i].start()
      for i in range(0,cores):
         thread[i].join()

   def run_plane_jobs(self, jobs):
      thread = {}
      if os.path.exists("cores.json") == 1:
         temp = load_json_file("cores.json")
         cores = temp['cores']
      else:
         cores = 4
      if cores > len(jobs):
         cores = 4
      cc = 0

      jobs_per_proc = int(len(jobs)/(cores-1))
      for i in range(0,cores):
         start = i * jobs_per_proc
         end = start + jobs_per_proc + 1
         if end > len(jobs):
            end = len(jobs)
         #print(i, start, end)
         # CHANGE THIS LINE FOR DIFFERENT JOB
         thread[i] = Process(target=self.plane_worker, args=("thread" + str(i), jobs[start:end]))

      for i in range(0,cores):
         thread[i].start()
      for i in range(0,cores):
         thread[i].join()

   def plane_worker(self, thread_number, job_list):
      for i in range(0,len(job_list)):
         event_id = job_list[i][0]
         key = job_list[i][1]
         ekey = event_id + "_" + key
         ob1 = job_list[i][2]
         ob2 = job_list[i][3]
         gd = ["GOOD", key, ob1, ob2]
         temp = self.r.get(ekey)
         if temp is None:
            temp = self.plane_solve(gd)
            if len(temp) == 2:
               result,sanity = temp
            else:
               result = 99
               sanity = 99
            self.r.set(ekey, json.dumps([result,sanity]))
         else:
            result, sanity = json.loads(temp)
         #self.solve_event(event_id, temp_obs, 1, force)


   def wmpl_worker(self, thread_number, job_list):
      for i in range(0,len(job_list)):
         #print("WORKEr:", thread_number, job_list[i][0], job_list[i][1])
         event_id = job_list[i][0] 
         event_status = job_list[i][1] 
         temp_obs = job_list[i][2] 
         force = 1
         self.solve_event(event_id, temp_obs, 1, force)

   def get_dyna_event(self, event_id):
      table = self.dynamodb.Table('x_meteor_event')
      event_day = event_id[0:8]
      y = event_day[0:4]
      m = event_day[4:6]
      d = event_day[6:8]
      event_day = y + "_" + m + "_" + d
      response = table.query(
         KeyConditionExpression='event_day= :event_day AND event_id= :event_id',
         ExpressionAttributeValues={
            ':event_day': event_day,
            ':event_id': event_id,
         }
      )

      if len(response['Items']) > 0:
         return(response['Items'][0])
      else:
         return(None)




   def sql_select_event_day_stats(self, event_day):
      stats_data = {}
      event_day = event_day.replace("_", "")
      event_day = event_day.replace("-", "")
      event_day = event_day.replace("/", "")

      sql = """
         SELECT count(*), event_status
           FROM events
          WHERE event_id like ?
       GROUP BY event_status
      """

      stats_data["STATUS_SOLVED"] = 0
      stats_data["STATUS_FAILED"] = 0

      vals = [event_day + "%"]
      self.cur.execute(sql, vals)
      rows = self.cur.fetchall()
      for row in rows:
         event_count = row[0]
         event_status = row[1]
         print("ROW", event_count, event_status)
         stats_data["STATUS_" + event_status] = event_count

      station_data = {}

      sql = """
         SELECT count(*) 
           FROM event_obs
      """

      vals = [event_day + "%"]
      self.cur.execute(sql)
      rows = self.cur.fetchall()
      stats_data["TOTAL_OBS"] = rows[0][0]

      stats_data["by_station"] = []
      sql = """
         select station_id, count(*) from event_obs group by station_id;
      """
      self.cur.execute(sql)
      rows = self.cur.fetchall()

      for row in rows:
         st, count = row


         stats_data["by_station"].append((st,count))

      stats_data["all_events"] = []
      sql = """
         select event_id from events 
      """
      self.cur.execute(sql)
      rows = self.cur.fetchall()

      for row in rows:
         event_id = row[0]

         failed_file = self.local_evdir + event_id + "/" + event_id + "-fail.json"
         solve_file = self.local_evdir + event_id + "/" + event_id + "-event.json"
         if os.path.exists(solve_file) is True:
            status = "SOLVED"
            event_data = load_json_file(solve_file)
         elif os.path.exists(failed_file) is True:
            status = "FAILED"
            event_data = load_json_file(failed_file)
         else:
            status = "PENDING"
            event_data = {}

         print(status, solve_file)
         stats_data["all_events"].append((event_id,status, event_data))






      return(stats_data)

   def sql_select_event(self, event_id):

      sql = """
         SELECT event_id, event_minute, revision, event_start_time, event_start_times, 
                stations, obs_ids, lats, lons, event_status, run_date, run_times
           FROM events
          WHERE event_id = ?
      """
      vals = [event_id]
      self.cur.execute(sql, vals)
      rows = self.cur.fetchall()
      if len(rows) > 0:
         return(rows[0])
      else:
         return([])

   def sql_select_events(self, event_day):

      sql = """
         SELECT event_id, event_minute, revision, event_start_time, event_start_times, 
                stations, obs_ids, lats, lons, event_status, run_date, run_times
           FROM events
          WHERE event_id like ?
      """
      vals = [event_day + '%']
      self.cur.execute(sql, vals)
      rows = self.cur.fetchall()
      return(rows)

   def update_all_event_status(self, event_day):
      event_day = event_day.replace("_", "")
      event_day = event_day.replace("-", "")
      event_day = event_day.replace("/", "")
      sql = """
         SELECT event_id, event_minute, revision, event_start_time, event_start_times, 
                stations, obs_ids, lats, lons, event_status, run_date, run_times
           FROM events
          WHERE event_id like ?
      """
      vals = [event_day + '%']
      self.cur.execute(sql, vals)
      rows = self.cur.fetchall()
      for row in rows:
         ev_id = row[0]
         print(ev_id)
         self.check_event_status(ev_id)


   def check_event_status(self, event_id):
      # is the event defined in the .json files ? 
      # does the event exist in the allsky-s3 
      # does the event exist in the local filesystem
      # is the event in the sql db ?
      # is the event in the dynamodb ?
      # are there duplicates of this event on the local file system, s3f3, in sql or in dyanomdb

      # when we are done we should have the full event data object that goes to DYNA and also goes in the event.json file
      # if the event failed, or the event is pending we should still return the compele event.json data as best as we can.
      self.status_data = {}
      event_data = {}
      event_day = self.event_id_to_date(event_id)

      y,m,d = event_day.split("_")
      self.s3_event_day_dir = "/mnt/allsky-s3/EVENTS/" + y + "/" + m + "/" + d + "/"
      self.s3_event_id_dir = self.s3_event_day_dir + event_id + "/"

      self.cloud_event_day_dir = "/mnt/archive.allsky.tv/EVENTS/" + y + "/" + m + "/" + d + "/"
      self.cloud_event_id_dir = self.cloud_event_day_dir + event_id + "/"

      self.local_event_day_dir = self.data_dir + "EVENTS/" + y + "/" + m + "/" + d + "/"
      self.local_event_id_dir = self.local_event_day_dir + event_id + "/"



      # see if it is already up to date?
      sql_data = self.sql_select_event(event_id)
      if len(sql_data) > 0:
         self.event_in_sql = True
      else:
         self.event_in_sql = False

      if False:
      #if sql_data[9] != "PENDING" and sql_data[9] != "FAILED" and sql_data[9] != "SOLVED":
         try:
            self.status_data = json.loads(sql_data[9])
            self.local_event_id_dir = self.local_event_day_dir + event_id + "/"
            if "solve_status" in self.status_data:
               donothing = 1
               #return(self.status_data['solve_status'])

         except:
            print(sql_data[9])
            input("Something is not right, status load from sql failed..." )


      self.s3_dir_exists = os.path.exists(self.s3_event_id_dir)
      self.local_dir_exists = os.path.exists(self.local_event_id_dir)
      self.cloud_dir_exists = os.path.exists(self.cloud_event_id_dir)

      if self.s3_dir_exists is True:
         self.s3_files = os.listdir(self.s3_event_id_dir)
      else:
         self.s3_files = []

      if self.local_dir_exists is True:
         self.local_files = os.listdir(self.local_event_id_dir)
      else:
         self.local_files = []

      if self.cloud_dir_exists is True:
         self.cloud_files = os.listdir(self.cloud_event_id_dir)
      else:
         self.cloud_files = []


      self.status_data['cloud_files'] = self.cloud_files
      self.status_data['local_files'] = self.local_files
      self.status_data['s3_files'] = self.s3_files

      if len(self.local_files) > 10 or len(self.s3_files) > 10:
         self.event_status = "SOLVED"
      elif "failed" in self.local_files or "failed" in self.s3_files and "event" not in self.local_files:
         self.event_status = "FAILED"
      else :
         self.event_status = "PENDING"

      self.status_data['event_status'] = self.event_status 

      if len(self.s3_files) == len(self.local_files) or len(self.s3_files) > len(self.local_files):
         self.event_archived = True
      else:
         self.event_archived = False

      self.status_data['event_archived'] = self.event_archived

      if os.path.exists(self.local_event_id_dir + event_id + "-fail.json") is True:
         try:
            self.event_fail_json = load_json_file(self.local_event_id_dir + event_id + "-fail.json")
         except:
            os.remove(self.local_event_id_dir + event_id + "-fail.json")
      elif os.path.exists(self.s3_event_id_dir + event_id + "-fail.json") is True:
         self.event_fail_json = load_json_file(self.s3_event_id_dir + event_id + "-fail.json")
      else:
         self.event_fail_json = None 

      if os.path.exists(self.local_event_id_dir + event_id + "-event.json") is True:
         try:
            self.event_json = load_json_file(self.local_event_id_dir + event_id + "-event.json")
         except:
            os.remove(self.local_event_id_dir + event_id + "-event.json")
      elif os.path.exists(self.s3_event_id_dir + event_id + "-event.json") is True:
         self.event_json = load_json_file(self.s3_event_id_dir + event_id + "-event.json")
      else:
         self.event_json = None 

      if os.path.exists(self.local_event_id_dir + event_id + "_GOOD_OBS.json") is True:
         try:
            self.good_obs_json = load_json_file(self.local_event_id_dir + event_id + "_GOOD_OBS.json")
         except:
            print("BAD FILE!", self.local_event_id_dir + event_id + "_GOOD_OBS.json")
            return()
            #os.remove(self.local_event_id_dir + event_id + "_GOOD_OBS.json")

      elif os.path.exists(self.s3_event_id_dir + event_id + "_GOOD_OBS.json") is True:
         self.good_obs_json = load_json_file(self.s3_event_id_dir + event_id + "_GOOD_OBS.json")
      elif os.path.exists(self.cloud_event_id_dir + event_id + "_GOOD_OBS.json") is True:
         self.good_obs_json = load_json_file(self.cloud_event_id_dir + event_id + "_GOOD_OBS.json")
      else:
         self.good_obs_json = None 
         print("GOOD OBS FILE NOT FOUND!", self.local_event_id_dir + event_id + "_GOOD_OBS.json" )
         return()
             
      print("Dirs :", self.local_event_id_dir, self.s3_event_id_dir)
      print("Local:", self.local_dir_exists, len(self.local_files))
      print("S3   :", self.s3_dir_exists, len(self.s3_files))
      print("Event Status:", self.event_status)
      print("Event Archived:", self.event_archived)
      self.status_data['local_event_id_dir'] = self.local_event_id_dir
      self.status_data['cloud_event_id_dir'] = self.cloud_event_id_dir
      self.status_data['event_status'] = self.event_status

      #if self.event_json is not None:
      #   print(self.event_json.keys())


      print("Event in SQL:", self.event_in_sql)
      #for i in range(0,len(sql_data)):
      #   print(i, sql_data[i])
      self.status_data['event_in_sql'] = self.event_in_sql

      dyna_data = self.get_dyna_event(event_id)



      if dyna_data is None:
         print("NO DYNA DATA:", self.event_in_sql)
         self.status_data['solve_status'] = None
         self.status_data['dyna'] = False 
      elif "solve_status" in dyna_data:
         self.status_data['dyna'] = True
         self.status_data['solve_status'] = dyna_data['solve_status']

      # update the event status field
      now_dt = datetime.datetime.now().strftime("%Y_%m_%d %H:%M:%S")
      sql = """
         UPDATE events SET event_status = ?,
                run_date = ?,
                revision = revision + 1,
                run_times = run_times + 1
          WHERE event_id = ?
      """
      #uvals = [json.dumps(self.status_data), now_dt, event_id]
      uvals = [self.event_status, now_dt, event_id]
      self.cur.execute(sql,uvals)
      self.con.commit()

      return(self.status_data['solve_status'])
 
   def good_obs_to_event(self, date, event_id):
      event = {}
      event['event_day'] = date
      event['event_id'] = event_id
      event['stations'] = []
      event['files'] = []
      event['start_datetime'] = []
      event['lats'] = []
      event['lons'] = []
      event['alts'] = []


      print("STATUS DATA?", self.status_data)
      if self.good_obs_json is None:
         if "local_files" in self.status_data:
             
            print("LOADING:", self.local_event_id_dir + event_id + "_GOOD_OBS.json")
            time.sleep(.1)
            try:
               self.good_obs_json = json.loads(self.local_event_id_dir + event_id + "_GOOD_OBS.json")
            except:
               print("FAILED TO LOAD:", self.local_event_id_dir + event_id + "_GOOD_OBS.json")
         print("STATUS DATA?", self.status_data)
      
      if self.good_obs_json is not None:
         for station in self.good_obs_json:
            for ofile in self.good_obs_json[station]:
               lat,lon,alt = self.good_obs_json[station][ofile]['loc']
               start_datetime = self.good_obs_json[station][ofile]['times']
               event['stations'].append(station)
               event['files'].append(ofile)
               event['start_datetime'].append(start_datetime)
               event['lats'].append(lat)
               event['lons'].append(lon)
               event['alts'].append(alt)
      else:
         print("good obs json is NONE!", self.local_event_id_dir + event_id + "_GOOD_OBS.json")
         return()

      if os.path.exists(self.local_event_id_dir + event_id + "-event.json") is True:
         self.event_json = load_json_file(self.local_event_id_dir + event_id + "-event.json")
      elif os.path.exists(self.s3_event_id_dir + event_id + "-event.json") is True:
         self.event_json = load_json_file(self.s3_event_id_dir + event_id + "-event.json")
      else:
         self.event_json = None


      if self.event_json is not None:
         event['solution'] = self.event_json
         event['solve_status'] = "SOLVED"
      elif self.event_fail_json is not None:
         event['solve_status'] = "FAILED"
      else:
         event['solve_status'] = "PENDING"
      

      return(event)



   def solve_event(self,event_id, temp_obs, time_sync, force):


      # flag2 is force?
      #self.check_event_status(event_id)
      ev_dir = self.local_evdir + "/" + event_id
      if os.path.exists(ev_dir) is False:
         os.makedirs(ev_dir)
      # Save good obs file!
      good_obs_file = ev_dir + "/" + event_id + "_GOOD_OBS.json"


      if os.path.exists(ev_dir) is False:
         os.makedirs(ev_dir)

      # only solve if it has not already been solved.
      failed_file = ev_dir + "/" + event_id + "-fail.json"
      solve_file = ev_dir + "/" + event_id + "-event.json"
      save_json_file(good_obs_file, temp_obs, True)

      self.event_status = self.check_event_status(event_id)
      print("CURRENT STATUS FOR EVENT.", self.event_status)
      event_status = self.event_status
      solve_status = self.event_status
      print("FORCE:", force)

      if (self.event_status == "SOLVED" or self.event_status == "FAILED") and force != 1:
         print("Already done this.")
         return() 


      if (os.path.exists(failed_file) is False and os.path.exists(solve_file) is False) or force == 1:
         print("Saving:" ,good_obs_file)

         new_run = True
         # debug only!
         for obs in temp_obs:
             print("TEMP OBS:", temp_obs)

         # if we are resolving then it prob failed
         # so lets set the time_sync to 0
         # we may change this logic later!
         time_sync = 0
         solve_status = WMPL_solve(event_id, temp_obs, time_sync, force)
         self.make_event_page(event_id)

         try:
            print("RUNNING WMPL...")
            solve_status = WMPL_solve(event_id, temp_obs, time_sync, force)
            self.make_event_page(event_id)
         except:
            print("WMPL FAILED TO RUN!")
            status = "FAILED"
      else:
         print("WMPL ALREADY RAN...")
         new_run = False
         solve_status = "PENDING"

      print("WMPL SOLVE STATUS:", event_id, solve_status)
      if solve_status == "FAILED":
         time_sync=0
         print("IT LOOKS LIKE THE TIME SYNC FAILED. WE WILL RESOLVE")
         #input("OK???")
         #solve_status = WMPL_solve(event_id, temp_obs, time_sync, force)
         #print("TRIED A SECOND TIME WITHOUT TIME SYNC!", solve_status)

      # determine solve status and update the DB
      pass_file = self.local_evdir + "/" + event_id + "/" + event_id + "-event.json"
      fail_file = self.local_evdir + "/" + event_id + "/" + event_id + "-fail.json"
      if os.path.exists(pass_file) is True:
         status = "SOLVED"
      elif os.path.exists(fail_file) is True:
         status = "FAILED"
         event_data = {}
         event_day = self.event_id_to_date(event_id)
         event_data['event_day'] = event_day

         temp = self.good_obs_to_event(event_day, event_id)
         for key in temp:
            event_data[key] = temp[key]

         insert_meteor_event(self.dynamodb, event_id, event_data)


      else:
         status = "PENDING"



      if status == "SOLVED" and new_run is True:
         event_data = load_json_file(pass_file) 
         if "event_day" not in event_data:
            event_day = self.event_id_to_date(event_id)
            event_data['event_day'] = event_day
         print(event_data)

         temp = self.good_obs_to_event(event_day, event_id)
         for key in temp:
            event_data[key] = temp[key]


         #print("GOOD OBS:", self.good_obs_json)


         good_obs_file = self.local_evdir + event_id + "/" + event_id + "_GOOD_OBS.json"
         self.good_obs_json = load_json_file(good_obs_file)
         #print("GOOD OBS:", self.good_obs_json)
         temp = self.good_obs_to_event(event_day, event_id)
         for key in temp:
            event_data[key] = temp[key]


         insert_meteor_event(self.dynamodb, event_id, event_data)
         cmd = "./plotTraj.py " + event_id
         print("DISABLED:", cmd)
         #os.system(cmd)

      print(pass_file)
      print(fail_file)
      print("STATUS:", status)
      # lets load whatever is available since it might have been missed
      # insert into our local DB solve table
      # also insert into the Dyna DB
      now_dt = datetime.datetime.now().strftime("%Y_%m_%d %H:%M:%S")
      sql = """
         UPDATE events SET event_status = ?,
                               run_date = ?,
                               revision = revision + 1,
                              run_times = run_times + 1
                         WHERE event_id = ?
      """
      uvals = [status, now_dt, event_id]
      self.cur.execute(sql,uvals)
      self.con.commit()

      print("DONE", event_id)


   def plane_test_day(self, date):
      # for each event this day
      # check planes for each unique combo of obs

      self.load_stations_file()
      qc_report = {}
      valid_obs = {}
      all_obs = {}

      # select events for this day
      sql = """
         SELECT event_id, event_status, stations, event_start_times, obs_ids 
           FROM events
          WHERE event_id like ?
      """
      orig_date = date
      date = date.replace("_", "")
      ivals = [date + "%"]
      self.cur.execute(sql,ivals)
      rows = self.cur.fetchall()
      final_data = []

      # for each event on this day
      for row in rows:
         event_id, event_status, stations, start_times, obs_ids = row
         stations = json.loads(stations)
         start_times = json.loads(start_times)
         obs_ids = json.loads(obs_ids)
         ev_dir = self.local_evdir + event_id + "/"
         if os.path.exists(ev_dir) is False:
            os.makedirs(ev_dir)
         plane_file = ev_dir + event_id + "_PLANES.json"

         # if the plane report has not been created yet
         # go ahead and make it

         if os.path.exists(plane_file) is False:
            plane_report = self.plane_test_event(obs_ids, event_id, event_status)
            save_json_file(plane_file, plane_report, True)
         else:
            plane_report = load_json_file(plane_file)

         # summarize and report on all planes
         for ekey in plane_report['results']:
            sanity,res = plane_report['results'][ekey] 
            tempkey = ekey.replace(event_id + "_", "")
            ob1, ob2 = tempkey.split("__")
            all_obs[ob1] = 0
            all_obs[ob2] = 0
            if sanity == 0:
               valid_obs[ob1] = 1
               valid_obs[ob2] = 1
               all_obs[ob1] = 1
               all_obs[ob2] = 1
         good_planes,total_planes = self.check_planes(plane_report['results'])
         print(event_id, event_status, str(good_planes) + " / " + str(total_planes) + " good planes")

         # determine the final status
         # update event status here?! At least put results in the event file
         

         # if WMPL STATUS IS BAD AND THERE ARE NO GOOD PLANES 
         # IT IS AN INVALID EVENT
         if "BAD" in event_status and good_planes == 0:
            event_status += ":INVALID"
         final_data.append((event_id, event_status, good_planes, total_planes))
      final_data = sorted(final_data, key=lambda x: x[1])
      print("Event solving status and plane status report")

      # just print out the results
      for row in final_data:
         (event_id, event_status, good_planes, total_planes) = row
         try:
            print(event_id, event_status, good_planes, total_planes, round((good_planes/total_planes)*100,1), "%")
         except:
            print("ERR:", good_planes,  total_planes)
      qc_report['final_data'] = final_data

      # make station stats
      st_stats = {}
      for ob in all_obs:
         st = ob.split("_")[0]
         if st not in st_stats:
            st_stats[st] = {}
            st_stats[st]['GOOD'] = 0 
            st_stats[st]['BAD'] = 0 
         if ob in valid_obs:
            print("GOOD OBS:", ob)
            st_stats[st]['GOOD'] += 1
            all_obs[ob] = 1
         else:
            print(" BAD OBS:", ob)
            st_stats[st]['BAD'] += 1
            all_obs[ob] = 0

      # print out station stats
      for st in st_stats:
         good = st_stats[st]['GOOD']
         bad = st_stats[st]['BAD']
         total = good + bad
         print(st, good, bad, round((good/total)*100,1))

      # save QC report
      qc_report['st_stats'] = st_stats
      qc_report['valid_obs'] = all_obs
      save_json_file(self.local_evdir + orig_date + "_QC.json", qc_report, True)
      print(self.local_evdir + orig_date + "_QC.json")


      # SAVE FAILED OBS REPORT 
      failed_obs_html = ""
      for obs_id in sorted(all_obs):
         print("OBS:", obs_id, all_obs[obs_id])
         if all_obs[obs_id] == 0:
            failed_obs_html += self.meteor_cell_html(obs_id, None)
      fpo = open(self.local_evdir + orig_date + "_FAILED_OBS.html", "w")
      fpo.write(failed_obs_html)
      fpo.close()

   def check_planes(self, planes):
      good = 0
      total = 0
      for ekey in planes:
         row = planes[ekey]
         x,y = row
         if x == 0:
            good += 1
         total += 1
      return(good, total)

   def update_meteor_days(self, selected_day=None):
      if selected_day is None:
         selected_day =  datetime.datetime.now().strftime("%Y_%m_%d")
      nav = self.make_day_nav(selected_day)
      fpout = open("/mnt/ams2/network_meteor_days.html", "w")
      fpout.write(nav)
      fpout.close()
      cmd = "cp /mnt/ams2/network_meteor_days.html /mnt/archive.allsky.tv/APPS/network_meteor_days.html"
      print(cmd)
      os.system(cmd)

   def make_day_nav(self, selected_day=None):

      files = os.listdir("/mnt/f/EVENTS/DBS/")

      date_selector = """
            <script>
$(document).ready(function () {
  $("#select-opt").change(function() {
    var base_url = "F:/"
    var $option = $(this).find(':selected');
    var url = $option.val();
    if (url != "") {
      //url += "?text=" + encodeURIComponent($option.text());
      // Show URL rather than redirect
      //$("#output").text(url);
      window.location.href = base_url + url;
    }
  });
});
            </script>
            <form>
            <select id="select-opt" class="selected_date" data-style="btn-primary">
      """
      for day in sorted(files, reverse=True):
         day = day.replace("ALLSKYNETWORK_", "")
         day = day.replace(".db", "") 
         if "journal" in day or "CALIBS" in day:
            continue
         print("DAY:", day)
         y,m,d = day.split("_")
         url = "/EVENTS/" + y + "/" + m + "/" + d + "/" + day + "_OBS_GOOD.html"

         if day == selected_day:
            
            date_selector += "<option selected value=" + url + ">" + day + "</option>"
         else:
            date_selector += "<option value=" + url + ">" + day + "</option>"

      date_selector += """
            </select>
            </form>


      """
      return(date_selector)

   def publish_day(self, date=None):

      #day_nav = self.make_day_nav(selected_day=date)

      day_nav = """
                <input id='select-opt' value="{}" type="text" data-display-format="YYYY/MM/DD" data-action="reload" data-url-param="start_day" data-send-format="YYYY_MM_DD" class="datepicker form-control">
      """.format(date)
      event_date = date
      print("Publish Day", date)
      self.load_stations_file()
      self.set_dates(date)
      self.date = date
      self.help()

      qc_report = self.local_evdir + date + "_QC.json"
      if os.path.exists(qc_report):
         qc_data = load_json_file(qc_report)
      else:
         qc_data = {}
      all_obs = qc_data['valid_obs']

      self.get_all_obs(date)   

      template = ""
      tt = open("./FlaskTemplates/allsky-template-v2.html")
      for line in tt:
         template += line

      template = template.replace("{TITLE}", "ALLSKY7 EVENTS " + event_date)
      template = template.replace("AllSkyCams.com", "AllSky.com")
      self.local_evdir = self.local_event_dir + self.year + "/" + self.month + "/" + self.day  + "/"
      out_file_good = self.local_evdir + date + "_OBS_GOOD.html"
      out_file_bad = self.local_evdir + date + "_OBS_BAD.html"
      out_file_failed = self.local_evdir + date + "_OBS_FAIL.html"
      out_file_pending = self.local_evdir + date + "_OBS_PENDING.html"

      if os.path.exists(self.cloud_evdir) is False:
         os.makedirs(self.cloud_evdir)


      report_file = self.local_evdir + date + "_day_report.json" 
      #report_data = load_json_file(report_file)
      #print(report_file)
      #print(report_data.keys())

      sql = """
         SELECT event_id, event_status, stations, event_start_times, obs_ids 
           FROM events
          WHERE event_id like ?
      """
      date = date.replace("_", "")
      ivals = [date + "%"]
      self.cur.execute(sql,ivals)
      rows = self.cur.fetchall()
      style = """
      <style>
       .center {
          margin: auto;
          width: 80%;
          padding: 10px;
          border: 2px solid #000000 ;
       }
      </style>
      """

      good_ev = 0
      bad_ev = 0
      fail_ev = 0
      pending_ev = 0
      for row in rows:
         event_id, event_status, stations, start_times, obs_ids = row
         print(event_status)
         if "GOOD" in event_status or ("SOLVED" in event_status and "BAD" not in event_status):
            good_ev += 1
         elif "BAD" in event_status:
            bad_ev += 1
         elif "FAIL" in event_status:
            fail_ev += 1
         else:
            pending_ev += 1

      stats_nav = """
           <script>
             function goto_ev(t) {
              url = window.location.href
              let result = url.includes("GOOD")
              if (result > 0) {
                 // WE ARE ON THE GOOD PAGE
                 if (t == "good") {
                    // do nothing!
                 }
                 else {
                    url = url.replace("GOOD", "BAD")
                    window.location.replace(url)
                 }
              } 
              else {
                 // WE ARE ON THE BAD PAGE
                 if (t == "good") {
                    url = url.replace("BAD", "GOOD")
                    window.location.replace(url)
                 }
                 else {
                    // do nothing!
                 }
              }
             }
           </script>
      """

      #stats_nav += " <a href=javascript:goto_ev('good')>Good " + str(good_ev) + "</a> - "
      #stats_nav += " <a href=javascript:goto_ev('bad')>Bad " + str(bad_ev) + "</a> </p><p> "
      #stats_nav += "<a href=javascript:goto_ev('fail')>Fail " + str(fail_ev) + "</a> - "
      #stats_nav += "<a href=javascript:goto_ev('pending')>" + "Pending " + str(pending_ev) + "</a>"


      links = """
      <a href={:s}_OBS_GOOD.html>Good """.format(event_date) + str(good_ev) + """</a> - 
      <a href={:s}_OBS_BAD.html>Bad """.format(event_date) + str(bad_ev) + """</a> </p><p> 
      <a href={:s}_OBS_FAIL.html>Fail """.format(event_date) + str(fail_ev) + """</a> - 
      <a href={:s}_OBS_PENDING.html>Pending """.format(event_date) + str(pending_ev) + """</a>"""

      stats_nav += links
      self.center_lat = 45
      self.center_lon = 0 

      print("links:", links)

      self.kml_link = self.local_evdir.replace(self.data_dir, "/") + "ALL_TRAJECTORIES.kml"
      self.orb_file = "https://archive.allsky.tv" + self.local_evdir.replace(self.data_dir, "/") + "ALL_ORBITS.json"
      self.orb_link = "https://orbit.allskycams.com/index_emb.php?file={:s}".format(self.orb_file)

      print(self.orb_link)

      self.map_link = """https://archive.allsky.tv/APPS/dist/maps/index.html?mf={:s}&lat={:s}&lon={:s}&zoom=3""".format(self.kml_link, str(self.center_lat), str(self.center_lon))
      self.gallery_link = event_date + "_OBS_GOOD.html"
      self.data_table_link = event_date + "_DATA_TABLE.html"
      short_date = event_date.replace("_", "")
      stats_nav += """
         </p>
         <P>
          <span class="fa-layers fa-fw fa-2xl" style="background:black; padding: 5px">
             <i class="fa-solid fa-map-location-dot"></i>

             <span class="fa-layers-text fa-inverse" data-fa-transform="shrink-8 down-3" style="font-weight:900"><a href={:s}>Trajectories</a></span>
          </span>

          <span class="fa-layers fa-fw fa-2xl" style="background:black; padding: 5px">
             <i class="fa-solid fa-solar-system"></i>
             <span class="fa-layers-text fa-inverse" data-fa-transform="shrink-8 down-3" style="font-weight:900"><a href={:s}>Orbits</a></span>
          </span>

          <span class="fa-layers fa-fw fa-2xl" style="background:black; padding: 5px">
             <i class="fa-solid fa-star-shooting"></i>
             <span class="fa-layers-text fa-inverse" data-fa-transform="shrink-8 down-3" style="font-weight:900"><a href=https://archive.allsky.tv/APPS/dist/radiants.html?d={:s}>Radiants</a></span>
          </span>

          <span class="fa-layers fa-fw fa-2xl" style="background:black; padding: 5px">
             <i class="fa-solid fa-table-list"></i>
             <span class="fa-layers-text fa-inverse" data-fa-transform="shrink-8 down-3" style="font-weight:900"><a href={:s}>Data Table</a></span>
          </span>

          <span class="fa-layers fa-fw fa-2xl" style="background:black; padding: 5px">
             <i class="fa-solid fa-gallery-thumbnails"></i>
             <span class="fa-layers-text fa-inverse" data-fa-transform="shrink-8 down-3" style="font-weight:900"><a href={:s}>Gallery</a></span>
          </span>

         </P>
      """.format(self.map_link, self.orb_link, short_date, self.data_table_link, self.gallery_link )
      good_html = ""
      bad_html = "" 
      fail_html = "" 
      pending_html = "" 

      good_html += style
      good_html += "<h3>Meteor Archive for " + date + " " + day_nav + "</h3>" 
      good_html += "<h4>Solved Events (GOOD)</h4>"
      good_html += "<p>" + stats_nav + "</p>"

      bad_html += "<h3>Meteor Archive for " + date + " " + day_nav + "</h3>"
      bad_html += "<h4>Solved Events with Bad Solution</h4>"
      bad_html += "<p>" + stats_nav + "</p>"

      fail_html += "<h3>Meteor Archive for " + date + " " + day_nav + "</h3>"
      fail_html += "<h4>Failed Events </h4>"
      fail_html += "<p>" + stats_nav + "</p>"

      pending_html += "<h3>Meteor Archive for " + date + " " + day_nav + "</h3>"
      pending_html += "<h4>Pending Events </h4>"
      pending_html += "<p>" + stats_nav + "</p>"



      stats = {}
      plane_desc = {}
      for row in rows:
         event_id, event_status, stations, start_times, obs_ids = row
         stations = json.loads(stations)
         start_times = json.loads(start_times)
         obs_ids = json.loads(obs_ids)
         ev_dir = self.local_evdir + event_id + "/"
         if os.path.exists(ev_dir) is False:
            os.makedirs(ev_dir)

         ev_file = ev_dir + event_id + "-event.json"
         ev_fail_file = ev_dir + event_id + "-fail.json"
         if os.path.exists(ev_file) is False:
            pick_file = ev_file.replace("-event.json", "_trajectory.pickle")
            # this should make the event.json if the pickle exists
            if os.path.exists(pick_file) is True:
               resp = make_event_json(event_id, ev_dir ,{})

         if os.path.exists(ev_file) is False and os.path.exists(ev_fail_file) is True:
            ev_sum = "<h3>Solve failed for event {}</h3>".format(event_id)
         elif os.path.exists(ev_file) is False and os.path.exists(ev_fail_file) is False: 
            ev_sum = "<h3>Solve for event {} has not been run.</h3>".format(event_id)

         else:
            ev_data = load_json_file(ev_file)
            if ev_data['orb']['a'] is not None:
               print("EVENT FILE FOUND:", ev_file)
               ev_sum = """
               <center>
               <table border=1 cellpadding=5 cellspacing=5>
               <tr>
                  <th>Start Alt</th>
                  <th>End Alt</th>
                  <th>Vel</th>
                  <th>a</th>
                  <th>e</th>
                  <th>i</th>
                  <th>q</th>
                  <th>Shower</th>
               </tr>
               <tr>
                  <th>{} km</th>
                  <th>{} km</th>
                  <th>{} km/s</th>
                  <th>{} </th>
                  <th>{}</th>
                  <th>{}</th>
                  <th>{}</th>
                  <th>{}</th>
               </tr>
               </table>
               </center>

               """.format(int(ev_data['traj']['start_ele']/1000), int(ev_data['traj']['end_ele']/1000), int(ev_data['traj']['v_init']/1000), round(ev_data['orb']['a'],4), round(ev_data['orb']['e'],4), round(ev_data['orb']['i'],4), round(ev_data['orb']['q'],4), ev_data['shower']['shower_code'])
            else:
               ev_sum = "Bad solve."



         if "GOOD" in event_status or ("SOLVED" in event_status and "BAD" not in event_status):
            good_html += "<div class='center'>"
            plane_file = ev_dir + event_id + "_PLANES.json"
            if os.path.exists(plane_file) is False:
               plane_report = self.plane_test_event(obs_ids, event_id, event_status)
               save_json_file(plane_file, plane_report, True)
            else:
               plane_report = load_json_file(plane_file)
            good_planes,total_planes = self.check_planes(plane_report['results'])
            plane_desc[event_id] = str(good_planes) + " / " + str(total_planes) + " PLANES"

            good_html += "<h3>" + event_id + " - " + event_status + " " 
            good_html += plane_desc[event_id] + "</h3>"
            good_html += ev_sum

            for i in range(0,len(obs_ids)):

               st = stations[i]
               if st not in stats:
                  stats[st] = {}
                  stats[st]['good'] = 1
                  stats[st]['bad'] = 0
               stats[st]['good'] += 1
               obs_id = obs_ids[i]
               etime = start_times[i]
               #good_html += self.obs_id_to_img_html(obs_id)

               good_html += self.meteor_cell_html(obs_id,etime)

               good_html += "\n"
            good_html += "<div style='clear: both'></div>"
            good_html += "</div>"
         elif "BAD" in event_status :
            bad_html += "<div>"

            # TEST BAD PLANES! 
            plane_file = ev_dir + event_id + "_PLANES.json"
            if os.path.exists(plane_file) is False:
               plane_report = self.plane_test_event(obs_ids, event_id, event_status)
               save_json_file(plane_file, plane_report, True)
            else:
               plane_report = load_json_file(plane_file)
            good_planes,total_planes = self.check_planes(plane_report['results'])
            plane_desc[event_id] = str(good_planes) + " / " + str(total_planes) + " PLANES"

            bad_html += "<h3>" + event_id + " - " + event_status + " " 
            bad_html += plane_desc[event_id] + "</h3>"
            bad_html += ev_sum
            #self.plane_test_event(obs_ids)
            for i in range(0,len(obs_ids)):
               st = stations[i]
               if st not in stats:
                  stats[st] = {}
                  stats[st]['good'] = 0
                  stats[st]['bad'] = 1
               stats[st]['bad'] += 1
             
               obs_id = obs_ids[i]
               etime = start_times[i]
               #bad_html += self.obs_id_to_img_html(obs_id)

               obs_status = all_obs[obs_id]
               bad_html += self.meteor_cell_html(obs_id, etime, obs_status)
               bad_html += "\n"

            bad_html += "<div style='clear: both'></div>"
            bad_html += "</div>"
         elif "FAILED" in event_status :
            fail_html += "<div>"

            # TEST BAD PLANES! 
            plane_file = ev_dir + event_id + "_PLANES.json"
            if os.path.exists(plane_file) is False:
               plane_report = self.plane_test_event(obs_ids, event_id, event_status)
               save_json_file(plane_file, plane_report, True)
            else:
               plane_report = load_json_file(plane_file)
            good_planes,total_planes = self.check_planes(plane_report['results'])
            plane_desc[event_id] = str(good_planes) + " / " + str(total_planes) + " PLANES"

            fail_html += "<h3>" + event_id + " - " + event_status + " " 
            fail_html += plane_desc[event_id] + "</h3>"
            #self.plane_test_event(obs_ids)
            for i in range(0,len(obs_ids)):
               st = stations[i]
               if st not in stats:
                  stats[st] = {}
                  stats[st]['good'] = 0
                  stats[st]['bad'] = 1
               stats[st]['bad'] += 1
             
               obs_id = obs_ids[i]
               etime = start_times[i]
               #bad_html += self.obs_id_to_img_html(obs_id)

               obs_status = all_obs[obs_id]
               fail_html += self.meteor_cell_html(obs_id, etime, obs_status)
               fail_html += "\n"

            fail_html += "<div style='clear: both'></div>"
            fail_html += "</div>"
         else:
            pending_html += "<div>"

            # TEST BAD PLANES! 
            plane_file = ev_dir + event_id + "_PLANES.json"
            if os.path.exists(plane_file) is False:
               plane_report = self.plane_test_event(obs_ids, event_id, event_status)
               save_json_file(plane_file, plane_report, True)
            else:
               plane_report = load_json_file(plane_file)
            good_planes,total_planes = self.check_planes(plane_report['results'])
            plane_desc[event_id] = str(good_planes) + " / " + str(total_planes) + " PLANES"

            pending_html += "<h3>" + event_id + " - " + event_status + " " 
            pending_html += plane_desc[event_id] + "</h3>"
            #self.plane_test_event(obs_ids)
            for i in range(0,len(obs_ids)):
               st = stations[i]
               if st not in stats:
                  stats[st] = {}
                  stats[st]['good'] = 0
                  stats[st]['bad'] = 1
               stats[st]['bad'] += 1
             
               obs_id = obs_ids[i]
               etime = start_times[i]
               #bad_html += self.obs_id_to_img_html(obs_id)

               obs_status = all_obs[obs_id]
               pending_html += self.meteor_cell_html(obs_id, etime, obs_status)
               pending_html += "\n"

            pending_html += "<div style='clear: both'></div>"
            pending_html += "</div>"




      fpo = open(out_file_good, "w")
      temp = template.replace("{MAIN_CONTENT}", good_html)
      fpo.write(temp)
      fpo.close()

      temp = template.replace("{MAIN_CONTENT}", bad_html)
      fpo = open(out_file_bad, "w")
      fpo.write(temp)
      fpo.close()

      temp = template.replace("{MAIN_CONTENT}", fail_html)
      fpo = open(out_file_failed, "w")
      fpo.write(temp)
      fpo.close()

      temp = template.replace("{MAIN_CONTENT}", pending_html)
      fpo = open(out_file_pending, "w")
      fpo.write(temp)
      fpo.close()




      rpt_data = []
      for st in stats:
         g = stats[st]['good']
         b = stats[st]['bad']
         t = g + b
         bad_perc = b / t

         rpt_data.append((int(st.replace("AMS","")), bad_perc, g,b, t))
      rpt_data = sorted(rpt_data, key=lambda x: (x[1]), reverse=False)

      for row in rpt_data:
         st, bad_perc, g,b,t = row
         st_id = "AMS{:03}".format(st)
         #print(st_id + " " + str(round(bad_perc*100,1)) + "% of solves failed (" + str(b) + "/" + str(t) + " events)".format(st)  )


      # PUSH FINAL HTML TO CLOUD
      push_cmd = "cp " + self.local_evdir + "*.html " + self.cloud_evdir
      print(push_cmd)
      os.system(push_cmd)

      # station events

      self.station_events(event_date)
      push_cmd = "cp " + self.station_events_file + " " + self.cloud_evdir
      print(push_cmd)
      os.system(push_cmd)
      cmd = "/usr/bin/python3 EM.py aer " + event_date

      

   def plane_test_event(self, obs_ids, event_id, event_status):

      jobs = []

      results = {}
      good = 0
      bad = 0
      st_stats = {}
      ob_stats = {}
      good_planes = {}
      bad_planes = {}
      for ob1 in obs_ids:
         for ob2 in obs_ids:
            st1 = ob1.split("_")[0]
            st2 = ob2.split("_")[0]
            if ob1 != ob2 and st1 != st2:
               key = ob1 + "__" +ob2  
               gd = [event_id, key, ob1, ob2]
               jobs.append(gd)

      print(event_id, event_status, "PLANE JOBS:", len(jobs))
      self.run_plane_jobs(jobs)

      plane_report = {}
      rkeys = self.r.keys(event_id + "*")
      for key in rkeys:
         temp = self.r.get(key)
         if temp is not None:
            result, sanity = json.loads(temp)
            results[key] = (sanity, result)

      plane_report['results'] = results

      return(plane_report)

   def obs_id_to_img_html(self,obs_id):
      el = obs_id.split("_")
      st = el[0]
      ff = obs_id.replace(st + "_", "")
      cloud_url = "https://archive.allsky.tv/" + st + "/METEORS/" + ff[0:4] + "/" + ff[0:10] + "/" + st + "_" + ff + "-prev.jpg"
      play_link = """ <a href="javascript:click_icon('play', '""" + obs_id.replace(".jpg", "") + """')"> """
      html = play_link + "<img src=" + cloud_url + "></a>"
      return(html)

   def make_event_obs_html(self,row):
      event_id, event_status, stations, start_times, obs_ids = row
      out = """
         <div>

         </div>
      """

   def day_status(self, date=None):
      os.system("clear")
      self.load_stations_file()

      exit()
      self.set_dates(date)
      self.date = date
      self.help()
      if os.path.exists(self.local_evdir) is True:
         local_files = os.listdir(self.local_evdir)
      else:
         local_files = []

      if os.path.exists(self.s3_evdir) is True:
         s3_files = os.listdir(self.s3_evdir)
      else:
         s3_files = []


      if os.path.exists(self.cloud_evdir) is True:
         cloud_files = os.listdir(self.cloud_evdir)
      else:
         cloud_files = []
      print(self.allsky_console)
      print("Date                   :   ", self.date)
      print("Local Files            :   ", len(local_files))
      print("AWS S3 Files           :   ", len(s3_files))
      print("Cloud Files            :   ", len(cloud_files))
      
      if os.path.exists(self.obs_dict_file) is True: 
         self.obs_dict = load_json_file(self.local_evdir + "/" + self.date + "_OBS_DICT.json")
      else:
         self.obs_dict = {}

      station_stats = {}
      for key in self.obs_dict:
         el = key.split("_")
         st_id = el[0]
         if st_id not in station_stats:
            station_stats[st_id] = {}
            station_stats[st_id]['total_obs'] = 0
         station_stats[st_id]['total_obs'] += 1
      print("Total Stations         :   ", len(self.stations))
      print("Stations Reporting     :   ", len(station_stats.keys()))
      print("Total Obs              :   ", len(self.obs_dict.keys()))


      sql_event_day_stats = self.sql_select_event_day_stats(self.date)


      sql_events = self.sql_select_events(self.date.replace("_", ""))

      failed_events = []
      solved_events = []
      pending_events = []
      for i in range(0, len(sql_events)):
         event_id, event_minute, revision, event_start_time, event_start_times, stations, obs_ids, lats, lons, event_status, run_date, run_times = sql_events[i]

         if event_status == "SOLVED":
            solved_events.append(event_id)
         elif event_status == "FAILED":
            failed_events.append(event_id)
         else:
            pending_events.append(event_id)


      print("Multi Station Events   :   ", len(sql_events))


      meta = {}
      meta['report_date'] = self.date
      meta['local_files'] = len(local_files)
      meta['s3_files'] = len(s3_files)
      meta['cloud_files'] = len(cloud_files)
      meta['total_stations'] = len(self.stations)
      meta['total_stations_reporting'] = len(station_stats.keys())
      meta['total_obs'] = len(self.obs_dict.keys())
      meta['event_status'] = {}


      for status in sql_event_day_stats:
          ev_status = status.replace("STATUS_", "")
          meta['event_status'][ev_status] = sql_event_day_stats[status]

          if "NEW" in status:
             print(status.replace("STATUS_", "   ") + "                 :   ", sql_event_day_stats[status])

          else:
             print(status.replace("STATUS_", "   ") + "              :   ", sql_event_day_stats[status])



      event_obs = {}
      obs_events = {}
      station_events = {}
      for row in sql_events:
         event_id, event_minute, revision, event_start_time, event_start_times, stations, obs_ids, lats, lons, event_status, run_date, run_times = row
         obs_ids = json.loads(obs_ids)
         event_obs[event_id] = obs_ids
         for obs_id in obs_ids:
            sid = obs_id.split("_")[0]
            obs_events[obs_id] = event_id
            if sid not in station_events:
               station_events[sid] = {}
            if event_id not in station_events[sid]:
               station_events[sid][event_id] = []
            station_events[sid][event_id] = obs_id

      day_report = {}
      day_report['event_obs'] = event_obs
      day_report['obs_events'] = obs_events
      day_report['station_events'] = station_events
      day_report['station_summary'] = []
      day_report['failed_events'] = failed_events
      day_report['solved_events'] = solved_events
      day_report['pending_events'] = pending_events

      for data in self.stations:
         st_id = data['station_id']
         if st_id in station_events:
            total_events = len(station_events[st_id].keys())
         else:
            total_events = 0
         if st_id in station_stats:
            reported_obs = station_stats[st_id]['total_obs']
         else:
            reported_obs = 0
         #print(data)
         if "op_status" not in data:
            self.errors.append(("STATION_MISSING_STATUS", data['station_id']))
         else:
            st1 = data['station_id']
            try:
               lat1 = float(self.station_dict[st1]['lat'])
               lon1 = float(self.station_dict[st1]['lon'])
               alt1 = float(self.station_dict[st1]['alt'])
            except:
               self.errors.append(("STATION_MISSING_GEO", data['station_id']))
            day_report['station_summary'].append((data['station_id'], data['operator_name'], data['city'], data['country'], data['op_status'], lat1, lon1, alt1, reported_obs, total_events))
      day_report['station_errors'] = self.errors
      day_report['meta'] = meta
      report_file = self.local_evdir + date + "_day_report.json" 
      save_json_file(report_file, day_report, True)
      print("\n\nsaved:", report_file)

   def day_publish(self, date):

      print("ok")

   def day_load(self, date):
      print("ok")

   def make_obs_dict(self):
      #if cfe(self.obs_dict_file) == 1:
      #   self.obs_dict = load_json_file (self.obs_dict_file)
      #   return()
      #else:
      if os.path.exists(self.obs_dict_file) is True:
         sz, tdiff1 = get_file_info(self.all_obs_file)
         sz, tdiff2 = get_file_info(self.obs_dict_file)
      else:
         tdiff1 = 9999
         tdiff2 = 0
      if tdiff1 < tdiff2:
         print("OBS DICT IS GOOD TO GO.")
         try:
            self.obs_dict = load_json_file(self.obs_dict_file )
            return()
         except:
            print("Problem with obs dict file reload it.")
      else:
         print("OBS DICT NEEDS UPDATE.")
         print("TDIFF ALL OBS:", tdiff1)
         print("TDIFF OBS DICT:", tdiff2)

      self.obs_dict = {}
      print("ALL OBS FILE:", self.all_obs_file)
      self.all_obs = load_json_file(self.all_obs_file)
      for obs in self.all_obs:
         obs_key = obs['station_id'] + "_" + obs['sd_video_file']
         self.obs_dict[obs_key] = obs
      save_json_file(self.obs_dict_file, self.obs_dict, True)

   def help(self):
      self.allsky_console = """

  ____  _      _      _____ __  _  __ __
 /    || |    | |    / ___/|  |/ ]|  |  |
|  o  || |    | |   (   \_ |  ' / |  |  |
|     || |___ | |___ \__  ||    \ |  ~  |
|  _  ||     ||     |/  \ ||     ||___, |
|  |  ||     ||     |\    ||  .  ||     |
|__|__||_____||_____| \___||__|\_||____/

AllSky.com/ALLSKY7 - NETWORK SOFTWARE
Copywrite Mike Hankey LLC 2016-2022
Use permitted for licensed users only.
Contact mike.hankey@gmail.com for questions.
      """

      self.allsky_console_help = """
This program is an interface for runnin the various network features of the ALLKSKY.com NETWORK

usage: python3.6 AllSkyNetwork.py [COMMAND] [ARGUMENTS]

Supported functions :

status [date]   -    Show network status report for that day.
      """
   def score_obs(self, planes):

      #min_data = load_json_file(min_file)
      #planes = min_data["1"]['plane_pairs']

      start_points = []
      end_points = []
      for key in planes:
         result, score = planes[key]
         if len(result) >= 2:
            end = result[0]
            start = result[-1]
            start_points.append(start)
            end_points.append(end)

      start_lats = [row[0] for row in start_points]
      start_lons = [row[1] for row in start_points]
      end_lats = [row[0] for row in end_points]
      end_lons = [row[1] for row in end_points]

      med_start_lat = np.median(start_lats)
      med_start_lon = np.median(start_lons)
      med_end_lat = np.median(end_lats)
      med_end_lon = np.median(end_lons)

      med_lat = (med_start_lat + med_end_lat) / 2
      med_lon = (med_start_lon + med_end_lon) / 2

      # NOW FILTER THE LIST OF POINTS TO MEDIAN STD
      best_start_points = []
      best_end_points = []
      score_data = []
      for key in planes:
         result, score = planes[key]
         if len(result) >= 2:
            end = result[0]
            start = result[-1]
            start_lat_diff = abs(med_start_lat - start[0])
            start_lon_diff = abs(med_start_lon - start[1])
            end_lat_diff = abs(med_end_lat - start[0])
            end_lon_diff = abs(med_end_lon - start[1])
            score = start_lat_diff + start_lon_diff + end_lat_diff + end_lon_diff
            score_data.append((score, key))
            start_points.append(start)
            end_points.append(end)

      score_data = sorted(score_data, key=lambda x: x[0])
      return(score_data)

      # No longer used below here

      scores = [row[0] for row in score_data]
      med_score = np.median(scores)
      std_score = np.std(scores)

      good_stations = {}
      good_obs = {}
      if len(score_data) > 100:
         top_5_percent = int(len(score_data) * .05)
         ic = 1
         for row in score_data[0:top_5_percent]:
            ob1,ob2 = row[1].split("__")
            st1 = ob1.split("_")[0]
            st2 = ob2.split("_")[0]
            if ob1 not in good_obs:
               good_obs[ob1] = 0
            if ob2 not in good_obs:
               good_obs[ob2] = 0
            if st1 not in good_stations:
               good_stations[st1] = 0
            if st2 not in good_stations:
               good_stations[st2] = 0
            good_stations[st1] += 1
            good_stations[st2] += 1
            good_obs[ob1] += 1
            good_obs[ob2] += 1
            ic += 1


      for row in score_data[0:top_5_percent]:
         key = row[1]
         result, score = planes[key]
         if len(result) >= 2:
            end = result[0]
            start = result[-1]
            print(key, start, end)
            best_start_points.append(start)
            best_end_points.append(end)

      start_lats = [row[0] for row in best_start_points]
      start_lons = [row[1] for row in best_start_points]

      end_lats = [row[0] for row in best_end_points]
      end_lons = [row[1] for row in best_end_points]

      print("START LAT: ", start_lats)
      print("START LON: ", start_lons)
      print("END LAT: ", end_lats)
      print("END LON: ", end_lons)
      return(score_data)

   def dyna_insert_meteor_event(self, event_id, mc_event_data):
      print("MC:", mc_event_data)
      self.check_event_status(event_id)
      event_day = self.event_id_to_date(event_id)
      pass_file = self.local_evdir + "/" + event_id + "/" + event_id + "-event.json"
      fail_file = self.local_evdir + "/" + event_id + "/" + event_id + "-fail.json"
      if os.path.exists(pass_file) is True:
         status = "SOLVED"
         event_data = {}

      elif os.path.exists(fail_file) is True:
         status = "FAILED"
         event_data = {}
         event_data['event_day'] = event_day

      else:
         status = "PENDING"
         event_data = {}


      temp = self.good_obs_to_event(event_day, event_id)
      print("TEMP:", temp)
      for key in temp:
         event_data[key] = temp[key]
      event_data['event_status'] = status

      if status == "SOLVED" :
         solve_data = load_json_file(pass_file)
         if "event_day" not in solve_data:
            event_day = self.event_id_to_date(event_id)
            solve_data['event_day'] = event_day

         temp = self.good_obs_to_event(event_day, event_id)
         for key in temp:
            solve_data[key] = temp[key]
         event_data = solve_data

      print(event_data)

      #insert_meteor_event(self.dynamodb, event_id, event_data)
      
   def meteor_cell_html(self, obs_id,edatetime=None,status=None):

      #print("METEOR CELL:", status)

      if edatetime is not None:
         edate, etime = edatetime.split(" ")
      else:
         edate = ""
         etime = ""
      if "prev.jpg" not in obs_id:
         obs_id += "-prev.jpg"
      cloud_root  = "/mnt/archive.allsky.tv/"
      cloud_vroot = "https://archive.allsky.tv/"
      station_id = obs_id.split("_")[0]
      year = obs_id.split("_")[1]
      month = obs_id.split("_")[2]
      dom = obs_id.split("_")[3]
      hour = obs_id.split("_")[4]
      minute = obs_id.split("_")[5]
      second = obs_id.split("_")[6]
      mili_second = obs_id.split("_")[7]
      cam = obs_id.split("_")[8].split("-")[0]

      day = year + "_" + month + "_" + dom
      cloud_dir = cloud_root + station_id + "/METEORS/" + year + "/" + day + "/"
      cloud_vdir = cloud_vroot + station_id + "/METEORS/" + year + "/" + day + "/"
      prev_img_file = cloud_dir + obs_id.replace(".mp4","-prev.jpg")
      prev_img_url = cloud_vdir + obs_id.replace(".mp4","-prev.jpg")
      div_id = obs_id.replace(".mp4", "")
      div_id = div_id.replace("-prev.jpg", "")

      if status == None:
         opacity = "1"
      elif status == 1:
         opacity = "1"
      else:
         opacity = "1"

      disp_text = station_id + " - " + cam + " - " +  etime #+ "<br>"
      video_url = prev_img_url.replace("-prev.jpg", "-180p.mp4")
      disp_text += """ <a href="javascript:play_video('{}','{}')"><i style='font-size: 12px' class="fas fa-play "></i></a>""".format(div_id, video_url)
      #if os.path.exists(prev_img_file) is True:
      if True:
         html = """
         <div id="{:s}" style="
              float: left;
              background-image: url('{:s}');
              background-repeat: no-repeat;
              background-size: 320px;
              width: 320px;
              height: 180px;
              margin: 25px; 
              opacity: {:s}; 
              ">
              <div class="show_hider"> {:s} </div>
         </div>
         """.format(div_id, prev_img_url, opacity, disp_text)
      else:
         html = ""
         #station_id + " " + obs_id.replace(".mp4", "")
      return(html)


   def make_plane_kml(self, event, planes):
      kml = simplekml.Kml()
      colors = self.get_kml_colors()
      fol_day = kml.newfolder(name=self.date + " AS7 EVENTS")
      fol_obs = fol_day.newfolder(name=self.date + " AS7 EVENTS")
      color = "FFFFFFFF"
      for ob in event['obs']:
         el = ob.split("_")
         station_id = el[0]
         if "meteor_frame_data" not in self.obs_dict[ob]:
            print(ob, "MISSING MFD!")
            continue
         if len(self.obs_dict[ob]['meteor_frame_data']) == 0:
            print("NO FRAME DATA", ob)
            continue
         start_az = self.obs_dict[ob]['meteor_frame_data'][0][-2]
         start_el = self.obs_dict[ob]['meteor_frame_data'][0][-1]
         end_az = self.obs_dict[ob]['meteor_frame_data'][-1][-2]
         end_el = self.obs_dict[ob]['meteor_frame_data'][-1][-1]
         print(ob, start_az, start_el, end_az, end_el)
         lat,lon,alt = self.station_loc[station_id][:3]
         pnt = kml.newpoint(name=station_id, coords=[(round(lon,1),round(lat,1))])
         dist = 300
         start_az_end_pt = self.find_point_from_az_dist(lat,lon,start_az,dist)
         end_az_end_pt = self.find_point_from_az_dist(lat,lon,end_az,dist)

         kline = fol_obs.newlinestring(name=ob + " START", description="", coords=[(lon,lat,alt),(start_az_end_pt[1],start_az_end_pt[0],alt)])
         kline.altitudemode = simplekml.AltitudeMode.clamptoground
         kline.linestyle.color = colors[0]
         kline.linestyle.colormode = "normal"
         kline.linestyle.width = "3"

         kline2 = fol_obs.newlinestring(name=ob + " END", description="", coords=[(lon,lat,alt),(end_az_end_pt[1],end_az_end_pt[0],alt)])
         kline2.altitudemode = simplekml.AltitudeMode.clamptoground
         kline.linestyle.color = colors[2]
         kline2.linestyle.colormode = "normal"
         kline2.linestyle.width = "3"



      for combo_key in event['planes']:
         ev_id = 0
         o_combo_key = combo_key.replace("EP:", "")
         print("COMBO KEY IS:", combo_key)
         ob1,ob2 = combo_key.split(":")
         print(ev_id, combo_key, event['planes'][combo_key])
         if event['planes'][combo_key][0] == "plane_solved":
            line1 = event['planes'][combo_key][1]
            line2 = event['planes'][combo_key][2]
            #color = event['planes'][combo_key]['color']
            color = "FFFFFFFF"
            slat,slon,salt,elat,elon,ealt = line1

            line = fol_day.newlinestring(name=combo_key, description="", coords=[(slon,slat,salt),(elon,elat,ealt)])
            line.altitudemode = simplekml.AltitudeMode.relativetoground
            line.linestyle.color = color
            line.linestyle.colormode = "normal"
            line.linestyle.width = "3"
            slat,slon,salt,elat,elon,ealt = line2
            line = fol_day.newlinestring(name=combo_key, description="", coords=[(slon,slat,salt),(elon,elat,ealt)])
            line.altitudemode = simplekml.AltitudeMode.relativetoground
            line.linestyle.color = color
            line.linestyle.colormode = "normal"
            line.linestyle.width = "3"
         else:
            print("BAD PP STATUS:", event['planes'][combo_key][0])
      self.plane_kml_file = self.event_dir + "/" + event['event_id'] + "/" + event['event_id'] + "-planes.kml"
      if os.path.exists(self.event_dir + "/" + event['event_id']) is False:
         os.makedirs(self.event_dir + "/" + event['event_id'])
      kml.save(self.plane_kml_file)
      print(self.plane_kml_file)
      print("SAVED:", self.plane_kml_file)

   def get_kml_colors(self):
      colors = []
      for key in kml_colors:
         colors.append(kml_colors[key])
      return(colors)




   def check_start_ai_server(self):
      # test the AI server if not running start it and sleep for 30 seconds

      url = "http://localhost:5000/"
      try:
         response = requests.get(url)
         content = response.content.decode()
         print(content)
      except Exception as e:
         if "HTTP" in str(e):
            print("HTTP ERR:", e)
            cmd = "/usr/bin/python3.6 AIServer.py > /dev/null 2>&1 & "
            #cmd = "/usr/bin/python3.6 AIServer.py " #> /dev/null 2>&1 & "
            print("Starting AI Sleep for 40 seconds.")
            print(cmd)
            os.system(cmd)
            time.sleep(20)

   def check_ai_img(self, ai_image=None, ai_file=None):
      if ai_image is not None and ai_file is None:
         print(ai_image.shape)
         cv2.imwrite("/mnt/ams2/temp.jpg", ai_image)
         ai_file = "/mnt/ams2/temp.jpg"

      if True:
         url = "http://localhost:5000/AI/METEOR_ROI/?file={}".format(ai_file)
         try:
            response = requests.get(url)
            content = response.content.decode()
            content = json.loads(content)
            print(content)
         except Exception as e:
            print("HTTP ERR:", e)
      
      return(content)

   def obs_timeline (self, event_date):
      html = """

  <script type="text/javascript" src="https://www.gstatic.com/charts/loader.js"></script>
  <script type="text/javascript">
  google.charts.load("current", {packages:["timeline"]});
  google.charts.setOnLoadCallback(drawChart);
  function drawChart() {

    var container = document.getElementById('example5.1');
    var chart = new google.visualization.Timeline(container);
    var dataTable = new google.visualization.DataTable();
    dataTable.addColumn({ type: 'string', id: 'Room' });
    dataTable.addColumn({ type: 'string', id: 'Name' });
    dataTable.addColumn({ type: 'date', id: 'Start' });
    dataTable.addColumn({ type: 'date', id: 'End' });
    dataTable.addRows([
     """
      sql = """
        SELECT obs_id FROM event_obs ORDER BY station_id;
      """
      self.cur.execute(sql)
      rows = self.cur.fetchall()

      js_rows = ""
      for row in rows:
         obs_id = row[0]
         elm = obs_id.split("_")
         st = elm[0]  
         hour = elm[4]  
         minute = elm[5]  
         second = elm[6]  
         ehour = hour
         eminute = minute 
         esec = str(int(second) + 5)
         if int(esec) >= 60:
            esec = str(int(esec) - 60)
            eminute = int(minute) + 1
            if int(minute) >= 60:
               eminute = "0"
               ehour = str(int(hour)+1)

            else:
               eminute = str(eminute)
         if js_rows != "":
            js_rows += ","

         js_rows += """[ '{:s}', '{:s}', new Date({:s}, {:s}, {:s}, {:s}, {:s}, {:s}), new Date({:s}, {:s}, {:s}, {:s}, {:s}, {:s})]""".format(st, st, "0","0","0",hour, minute, second,"0","0","0",ehour,eminute,esec)

         print(obs_id, hour, minute, second)
      html += js_rows + "]);"

      html += """

    var options = {
      timeline: { colorByRowLabel: true }
    };

    chart.draw(dataTable, options);
  }

  </script>

  <div id="example5.1" style="height: 100px;"></div>

   """

      print(html)

   def make_obs_object(self, obs_id):
      obj = {}   
      obj['obs_id'] = obs_id  
      obj['station_id'] = obs_id.split("_")[0]
      obj['primary'] = True
      obj['ignore'] = False
      obj['media_files'] = {}
      obj['data_files'] = {}
      obj['calibration'] = {}
      return(obs_id)

   def edit_event(self, event_id):
      event_day = self.event_id_to_date(event_id)
      year, month, day_of_month = event_day.split("_")
      self.local_event_id_dir = self.local_event_dir + year + "/" + month + "/" + day_of_month + "/" + event_id + "/"
      all_files = os.listdir(self.local_event_id_dir)

      obs_data = {}

      for ev in all_files:
         ftype = ""
         root_file = ""
         obs_id = ""
         trim_num = ""
         if "AMS" == ev[0:3]:
            if ".mp4" in ev:
               ftype = "mp4"
            if ".jpg" in ev:
               ftype = "jpg"
            if ".json" in ev:
               ftype = "json"
            if ".html" in ev:
               ftype = "html"

            felm = ev.split("-")
            if "CLOUDFILES" in ev:
               ftype = "json"
               root_file = felm[0] 
               obs_id = felm[0] 
            elif len(felm) >= 3:
               trim_num = felm[2]
               root_file = felm[0] 
               obs_id = root_file + "-trim-" + felm[2] 
            elif len(felm) == 1:
               ftype = "min_file"
               root_file = felm[0] 
               obs_id = root_file 
            else:
               ftype = "min_file"
               root_file = ev 
               obs_id = root_file 

            station_id = ev.split("_")[0]
            if station_id not in obs_data:
               obs_data[station_id] = {}
               obs_data[station_id]['obs'] = {}
            if root_file not in obs_data[station_id]['obs']:
               obs_data[station_id]['obs'][root_file] = {}
               obs_data[station_id]['obs'][root_file]['files'] = {}
            obs_data[station_id]['obs'][root_file]['files'][ev] = {} 
            print("STATION FILE:", station_id, root_file, obs_id, ev, ftype)
         else:
            print("EVENT FILE:", ev, ftype)

      for station in obs_data:
         print(station)
         for obs_id in obs_data[station]['obs']:
            if "mp4" in obs_id:
               gtype = "* MIN FILE"
            else:
               gtype = ""
            print("   ", obs_id, gtype)
            if "files" in obs_data[station]['obs'][obs_id]:
               for ofile in obs_data[station]['obs'][obs_id]['files']:
                  print("      ", ofile) #, obs_data[station]['obs'][obs_id]['files'][ofile])
            else:
               print("NO FILES")

   def time_sync_frame_data(self):
      self.time_sync_data = {}
      self.unq_obs = {}
      for obs_fn in self.all_frame_data:
         self.unq_obs[obs_fn] = {}
         done = False
         for fc in self.all_frame_data[obs_fn]:
            if len(self.all_frame_data[obs_fn][fc]['cnts'] ) > 0:
               ft = self.all_frame_data[obs_fn][fc]['frame_time']
               if ft not in self.time_sync_data:
                  self.time_sync_data[ft] = {}
               if obs_fn not in self.time_sync_data[ft]:
                  self.time_sync_data[ft][obs_fn] = {}
               if fc not in self.time_sync_data[ft][obs_fn]:
                  self.time_sync_data[ft][obs_fn][fc] = {}
                  self.time_sync_data[ft][obs_fn][fc]['cnts'] = self.all_frame_data[obs_fn][fc]['cnts']
               # get the crop thumb
               else:
                  print("NO FRAMES FOR", obs_fn)



               #print("FRAME TIME:", obs_fn, self.all_frame_data[obs_fn][fc]['frame_time'])
               done = True


      tw = 320
      th = 180
      max_thumbs = 36
      max_cols = 6
      max_rows = 6
      mc = 0
      oc = 0
      rc = 0

      main_frame = np.zeros((1080,1920,3),dtype=np.uint8)
      for obs_id in self.unq_obs:
 
         x1 = oc * tw
         x2 = x1 + tw
         y1 = rc * th
         y2 = y1 + th
         self.unq_obs[obs_id] = [x1,y1,x2,y2]
         if oc >= max_cols - 1 :
            oc = 0
            rc += 1
         else:
            oc += 1
      for obs_id in self.unq_obs:
         x1,y1,x2,y2 = self.unq_obs[obs_id]
         cv2.putText(main_frame, str(obs_id),  (x1,y1), cv2.FONT_HERSHEY_SIMPLEX, .6, (255,255,255), 1)
         cv2.rectangle(main_frame, (int(x1), int(y1)), (int(x2) , int(y2) ), (255, 255, 255), 2)
         cv2.imshow('pepe', main_frame)
         cv2.waitKey(30)

 
      light_curves = {}
      for key in self.time_sync_data:
         main_frame = np.zeros((1080,1920,3),dtype=np.uint8)

         for obs_fn in self.time_sync_data[key]:
         #for obs_fn in self.unq_obs:
            fimg = np.zeros((th,tw,3),dtype=np.uint8)
            if obs_fn in self.time_sync_data[key]: 
               #print("OBS ID FOUND:", obs_fn, self.time_sync_data[key].keys())
               x1,y1,x2,y2 = self.unq_obs[obs_fn]
               if obs_fn in self.all_frames:
                  for fc in self.time_sync_data[key][obs_fn]:
                     fimg = np.zeros((th,tw,3),dtype=np.uint8)
                     print( key, obs_fn, fc, self.time_sync_data[key][obs_fn])
                     # NEED FRAME NUMBER???
                     if obs_fn in self.all_frames:
                        if int(fc) <= len(self.all_frames[obs_fn]):
                           fimg = self.all_frames[obs_fn][int(fc)]
                           #cv2.imshow('pepe', fimg)
                          #cv2.waitKey(0)
               #else:
               #   print(obs_fn, "NOT FOUND IN ALL FRAMES", self.all_frames.keys())
            #else:
            #   print("OBS FNMISSING:", obs_fn, self.time_sync_data[key].keys())
            fimg_tn = cv2.resize(fimg,(tw,th))
            main_frame[y1:y2,x1:x2] = fimg_tn
         cv2.imshow('pepe', main_frame)
         cv2.waitKey(0)
         mc += 1   
      #exit()

   def remote_reducer(self, event_id):
      # this will reduce all files for this event 
      # per the latest calibs and standards
      # works with SD or HD files
      
      cv2.namedWindow('pepe')
      cv2.resizeWindow("pepe", 1920, 1080)

      # setup vars and dates and get all files for this event
      date = self.event_id_to_date(event_id)
      self.set_dates(date)
      event_dir = self.local_event_dir + "/" + self.year + "/" + self.month + "/" + self.day  + "/" + event_id + "/"
      all_files = os.listdir(event_dir )


      self.all_frames = {}
      self.mp4_files = []
      self.bad_mp4_files = []
      for hdf in all_files:
         if "mp4" not in hdf:
            continue
         oframes = load_frames_simple(event_dir + hdf)

         print("LOADING:", hdf, len(oframes))
         if len(oframes) > 1:
            self.all_frames[hdf] = oframes
            self.mp4_files.append(hdf)
         else:
            self.bad_mp4_files.append(hdf)
      #input("Loaded frames")

      all_frame_data_file = event_dir + event_id + "_ALL_FRAME_DATA.json"


      if os.path.exists(all_frame_data_file):
         self.all_frame_data = load_json_file(all_frame_data_file)
         self.time_sync_frame_data()
      else:
         self.all_frame_data = {}

      #exit()

      # loop over all files
      for hdf in self.mp4_files:
         # skip if non movie file
         if "mp4" not in hdf:
            continue

         self.all_frame_data[hdf] = {}
         # parse file name for station id and datetime, 
         station_id = hdf.split("_")[0]
         (f_datetime, cam_id, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(hdf.replace(station_id + "_" , ""))
         trim_num = get_trim_num(hdf)
         extra_sec = int(trim_num) / 25
         start_trim_frame_time = f_datetime + datetime.timedelta(0,extra_sec)

         # load frames
         oframes = load_frames_simple(event_dir + hdf)
         frames = []
         if len(oframes) == 0:
            print("NO FRAMES")
            continue 

         # resize frames to 1080p
         for frame in oframes:
            if oframes[0].shape[0] != 1080:
               frame = cv2.resize(frame, (1920,1080))
            frames.append(frame)
    
         # make median frame of 1st 3
         med_frame = cv2.convertScaleAbs(np.median(np.array(frames[0:3]), axis=0))


         hdfn = hdf.replace(station_id + "_", "")

         # get / update remote cal params
         cal_params, remote_json_conf = self.get_remote_cal_params(station_id, cam_id, hdfn, f_datetime,med_frame)

         # make show image for cal params
         show_img = med_frame.copy()
         if cal_params is not None:
            for star in cal_params['cat_image_stars']:
               name,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,star_x,star_y,res_px,flux = star
               cv2.circle(show_img, (int(star_x),int(star_y)), int(5), (0,255,0),2)
               cv2.circle(show_img, (int(new_cat_x),int(new_cat_y)), int(5), (128,255,0),2)
               cv2.imshow('pepe', show_img)
               cv2.waitKey(30)

            cv2.waitKey(30)
         #cat_stars, short_bright_stars, cat_image = get_catalog_stars(cal_params)
 
         # make auto mask of bright spots
         bw_med =  cv2.cvtColor(med_frame, cv2.COLOR_BGR2GRAY)
         min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(bw_med)
         thresh_val = int(max_val * .8)

         avg_val = np.mean(bw_med)
         if thresh_val < avg_val * 1.5:
            thresh_val = avg_val * 1.5

         _, mask_image = cv2.threshold(bw_med, thresh_val, 255, cv2.THRESH_BINARY)
         mask_image = cv2.dilate(mask_image, None, iterations=8)
         cnts = get_contours_in_image(mask_image)
         for x,y,w,h in cnts:
            mask_image[y:y+h,x:x+w] = 255

         mask_image_bgr = cv2.cvtColor(mask_image, cv2.COLOR_GRAY2BGR)

         # loop over frames, subtract mask and get contours for 
         # what remains

         fc = 0
         objects = {}
         thresh_vals = []
         for frame in frames:
            frame = cv2.subtract(frame, mask_image_bgr)
            extra_sec = fc / 25
            frame_time = start_trim_frame_time + datetime.timedelta(0,extra_sec)
            frame_time_str = frame_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            sub = cv2.subtract(frame, med_frame)

            bw_sub =  cv2.cvtColor(sub, cv2.COLOR_BGR2GRAY)
            bw_sub = cv2.subtract(bw_sub, mask_image)
            min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(bw_sub)
            avg_val = np.mean(bw_sub)
            thresh_val = int(max_val * .6)

            thresh_val = self.find_best_thresh(bw_sub)

            if thresh_val < 50:
               thresh_val = 50
            if thresh_val < avg_val:
               thresh_val = avg_val * 1.5
            _, thresh_image = cv2.threshold(bw_sub, thresh_val, 255, cv2.THRESH_BINARY)

            cnts = get_contours_in_image(thresh_image)
            self.all_frame_data[hdf][fc] = {}
            self.all_frame_data[hdf][fc]['cnts'] = []
            self.all_frame_data[hdf][fc]['frame_time'] = frame_time_str
            for x,y,w,h in cnts:
               mx = int(x + (w / 2))
               my = int(y + (h / 2))
               obj_id, objects = self.get_object(objects, fc, x,y,w,h)

               cv2.rectangle(thresh_image, (int(mx-25), int(my-25)), (int(mx+25) , int(my+25) ), (255, 255, 255), 2)
               cv2.putText(thresh_image, str(obj_id),  (mx-30,my-30), cv2.FONT_HERSHEY_SIMPLEX, .6, (255,255,255), 1)
               intensity = int(np.sum(bw_sub[y:y+h,x:x+w]))

               self.all_frame_data[hdf][fc]['cnts'].append((obj_id,int(x),int(y),int(w),int(h),int(intensity)))

            #cv2.imshow('pepe', frame)
            #cv2.putText(sub, frame_time_str,  (20,1060), cv2.FONT_HERSHEY_SIMPLEX, .6, (0,255,0), 1)

            cv2.imshow('pepe', thresh_image)
            cv2.waitKey(30)
            fc += 1

         # refine 
         channel_imgs = self.review_frame_data(hdf)
         self.track_with_channels(hdf, mask_image, med_frame, start_trim_frame_time, channel_imgs, frames)

         channel_imgs2 = self.review_frame_data(hdf)
         self.track_with_channels(hdf, mask_image, med_frame, start_trim_frame_time, channel_imgs, frames)

         channel_imgs3 = self.review_frame_data(hdf)
         print("Finished one file?", hdf)
         cv2.waitKey(30)         
      print (event_dir + event_id + "_ALL_FRAME_DATA.json")
      save_json_file(event_dir + event_id + "_ALL_FRAME_DATA.json", self.all_frame_data)

   def find_best_thresh(self, bw_sub):

      min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(bw_sub)
      avg_val = np.mean(bw_sub)
      thresh_val = max_val * .6
      go = True
      while go is True:
         thresh_val = thresh_val + 2 
         _, thresh_image = cv2.threshold(bw_sub, thresh_val, 255, cv2.THRESH_BINARY)
         cnts = get_contours_in_image(thresh_image)
         print("THRESH", len(cnts), thresh_val)
         if len(cnts) < 3:
            go = False
      return(thresh_val)


   def track_with_channels(self, hdf, mask_image, med_frame, start_trim_frame_time, channel_imgs, frames):
      fc = 0
      objects = {}
      if True:
         for frame in frames:
            for cmask in channel_imgs:
               frame = cv2.subtract(frame, cmask)

            extra_sec = fc / 25
            frame_time = start_trim_frame_time + datetime.timedelta(0,extra_sec)
            frame_time_str = frame_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            sub = cv2.subtract(frame, med_frame)

            bw_sub =  cv2.cvtColor(sub, cv2.COLOR_BGR2GRAY)
            bw_sub = cv2.subtract(bw_sub, mask_image)
            min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(bw_sub)
            avg_val = np.mean(bw_sub)
            thresh_val = int(max_val * .6)
            if thresh_val < 50:
               thresh_val = 50
            if thresh_val < avg_val:
               thresh_val = avg_val * 1.5
            _, thresh_image = cv2.threshold(bw_sub, thresh_val, 255, cv2.THRESH_BINARY)

            cnts = get_contours_in_image(thresh_image)
            self.all_frame_data[hdf][fc] = {}
            self.all_frame_data[hdf][fc]['cnts'] = []
            self.all_frame_data[hdf][fc]['frame_time'] = frame_time_str
            for x,y,w,h in cnts:
               mx = int(x + (w / 2))
               my = int(y + (h / 2))
               obj_id, objects = self.get_object(objects, fc, x,y,w,h)

               cv2.rectangle(thresh_image, (int(mx-25), int(my-25)), (int(mx+25) , int(my+25) ), (255, 255, 255), 2)
               cv2.putText(thresh_image, str(obj_id),  (mx-30,my-30), cv2.FONT_HERSHEY_SIMPLEX, .6, (255,255,255), 1)
               intensity = np.sum(bw_sub[y:y+h,x:x+w])

               self.all_frame_data[hdf][fc]['cnts'].append((obj_id,int(x),int(y),int(w),int(h),int(intensity)))

            #cv2.imshow('pepe', frame)
            #cv2.putText(sub, frame_time_str,  (20,1060), cv2.FONT_HERSHEY_SIMPLEX, .6, (0,255,0), 1)

            cv2.imshow('pepe', thresh_image)
            cv2.waitKey(30)
            fc += 1

   def review_frame_data(self, hdf ):

      show_img = np.zeros((1080,1920,3),dtype=np.uint8)

      obj_xs = {}
      obj_ys = {}

      for xc in self.all_frame_data[hdf]:
         if len(self.all_frame_data[hdf][xc]['cnts']) > 1:
            objs = {}
            new_cnts = []
            for obj_id,x,y,w,h,i in self.all_frame_data[hdf][xc]['cnts']:
               if obj_id not in objs:
                  objs[obj_id] = {}
                  objs[obj_id]['xs'] = []
                  objs[obj_id]['ys'] = []
                  objs[obj_id]['ws'] = []
                  objs[obj_id]['hs'] = []
                  objs[obj_id]['is'] = []
               objs[obj_id]['xs'].append(x)
               objs[obj_id]['ys'].append(y)
               objs[obj_id]['ws'].append(w)
               objs[obj_id]['hs'].append(h)
               objs[obj_id]['is'].append(i)
            for obj_id in objs:
               mx = np.median(objs[obj_id]['xs'])
               my = np.median(objs[obj_id]['ys'])
               mw = np.median(objs[obj_id]['ws'])
               mh = np.median(objs[obj_id]['hs'])
               mi = np.median(objs[obj_id]['is'])
               new_cnts.append((obj_id, mx, my, mw, mh, mi))
            self.all_frame_data[hdf][xc]['cnts'] = new_cnts 

         # there should be just 1 cnt per obj now
         for obj_id,x,y,w,h,i in self.all_frame_data[hdf][xc]['cnts']:
            if obj_id not in obj_xs:
               obj_xs[obj_id] = []
            if obj_id not in obj_ys:
               obj_ys[obj_id] = []

            cv2.rectangle(show_img, (int(x), int(y)), (int(x+w) , int(y+h) ), (255, 255, 255), 1)
            cv2.imshow('pepe', show_img)
            cv2.waitKey(30)
            cx = int(x + (w/2))
            cy = int(y + (h/2))
            obj_xs[obj_id].append(cx)
            obj_ys[obj_id].append(cy)
            cv2.circle(show_img, (int(cx),int(cy)), int(5), (0,0,255),2)
      channel_imgs = []
      channel_img = None
      #matplotlib.use('TkAgg')

      for obj_id in obj_xs:
         channel_img = self.make_channel(obj_xs[obj_id],obj_ys[obj_id], 1920,1080, channel_img)

         #plt.scatter(obj_xs[obj_id],obj_ys[obj_id]) 
         #cv2.imshow('pepe', channel_img)
         #cv2.waitKey(0)
         #plt.gca().invert_yaxis()
         #plt.show()
      channel_img = self.invert_image(channel_img)
      channel_img = cv2.cvtColor(channel_img,cv2.COLOR_GRAY2BGR)

      channel_imgs = [channel_img]
      return(channel_imgs)
            


   def get_object(self, objects, fn,mx,my,mw,mh):
      if True:
         if len(objects.keys()) == 0:
            # make new there are none!
            objects[1] = {}
            objects[1]['cnts'] = [[fn,mx,my,mw,mh]]
            print("Make 1st obj")
            return(1, objects)

         # check existing
         cmx = mx + (mw/2)
         cmy = my + (mh/2)
         for oid in objects:
            for cnt in objects[oid]['cnts']:
               fn,ox,oy,ow,oh = cnt
               cox = ox + (ow/2)
               coy = oy + (oh/2)
               dist = calc_dist((cmx,cmy), (cox,coy))
               if dist < 250:
                  objects[oid]['cnts'].append([fn,mx,my,mw,mh])
                  return(oid, objects)
         # none found so far. make new
         oid = max(objects.keys()) + 1
         objects[oid] = {}
         objects[oid]['cnts'] = [[fn,mx,my,mw,mh]]
         return(oid, objects)


   def remote_cal_one(self, full_file):

      # load up the med frame
      if "mp4" in full_file:
         frames = load_frames_simple(full_file)
         med_frame = cv2.convertScaleAbs(np.median(np.array(frames[0:10]), axis=0))
         med_file = full_file.replace(".mp4", "-med.jpg")
         med_frame = cv2.resize(med_frame, (1920,1080))
         cv2.imwrite(med_file, med_frame)
         #cv2.imshow('pepe', med_frame)
         #cv2.waitKey(0)

         full_file = med_file

      # connect to the main cal db
      db_file = self.db_dir + "ALLSKYNETWORK_CALIBS.db"
      print("DB FILE IS:", db_file)
      if os.path.exists(db_file) is False:
         print("DB FILE NOT FOUND.", db_file)
         return ()
      self.cal_con = sqlite3.connect(db_file)
      self.cal_con.row_factory = sqlite3.Row
      self.cal_cur = self.cal_con.cursor()

      if "\\" in full_file:
         full_file = full_file.replace("\\", "/")
    
      input_file = full_file.split("/")[-1]
      station_id = input_file.split("_")[0]

      (f_datetime, cam_id, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(input_file.replace(station_id + "_" , ""))

      # find / load the mask
      self.set_dates(input_file.replace(station_id + "_", "")[0:10])
      cloud_mask_file = "/mnt/archive.allsky.tv/" + station_id + "/CAL/MASKS/" + cam_id + "_mask.png"
      local_mask_dir = "/mnt/f/EVENTS/STATIONS/" + station_id + "/MASKS/" 
      local_mask_file = local_mask_dir + cam_id + "_mask.png"
      if os.path.exists(local_mask_dir) is False:
         os.makedirs(local_mask_dir)
      if os.path.exists(local_mask_file) is False:
         cmd = "cp " + cloud_mask_file + " " + local_mask_file
         os.system(cmd)

      if os.path.exists(local_mask_file) is True:
         mask_img = cv2.imread(local_mask_file)
         mask_img = cv2.resize(mask_img, (1920,1080))
      else:
         mask_img = np.zeros((1920,1080,3),dtype=np.uint8)

      # subtract mask from star image
      img = cv2.imread(full_file)
      img = cv2.resize(img, (1920,1080))
      img = cv2.subtract(img, mask_img)

      # get star points
      star_points,stars_image = get_star_points(input_file, img, {}, station_id, cam_id, {})
      star_points = sorted(star_points, key=lambda x: (x[2]), reverse=True)

      # get best defalt cal params
      input("GET CAL PARAMS")
      cal_params,json_conf = self.get_remote_cal_params(station_id, cam_id, input_file.replace(station_id + "_", ""), f_datetime,img, star_points)

      cal_params['cat_image_stars'], cal_params['user_stars'] = get_image_stars_with_catalog(input_file.replace(station_id + "_", ""), cal_params, img)

      input("DONE GET CAL PARAMS")

      if cal_params['total_res_px'] >= 999:
         print("REMOTE CAL FAILED!", len(cal_params['user_stars']), len(cal_params['cat_image_stars']), cal_params['total_res_px'] )
         cv2.imshow('pepe', img)
         cv2.waitKey(0)
         exit()

      cal_params['user_stars'] = star_points
     
      if True:
         show_img = stars_image.copy()
         for star in cal_params['cat_image_stars']:
            name,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,star_x,star_y,res_px,flux = star
            cv2.circle(show_img, (int(star_x),int(star_y)), int(5), (0,255,0),2)
            cv2.rectangle(show_img, (int(new_cat_x-10), int(new_cat_y-10)), (int(new_cat_x+10) , int(new_cat_y+10) ), (255, 255, 255), 1)
            print("STAR FROM CAT STARS", star)
            cv2.imshow('pepe', show_img)
            cv2.waitKey(0)

      if cal_params is None:
         text1 = "NO CAL PARAMS FOUND!" 
         return()
      else:
         text1 = str(cal_params['center_az'])[0:4] + " / " \
            + str(cal_params['center_el'])[0:4] + " ::: " \
            + str(cal_params['ra_center'])[0:4] + " / " \
            + str(cal_params['dec_center'])[0:4] + " ::: " \
            + str(cal_params['position_angle'])[0:4] + " ::: " \
            + str(cal_params['pixscale'])[0:4] + " ::: " 

      # draw img stars on image
      if len(img.shape) == 2:
         img =  cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
      show_img = img.copy()

      if True:
         # draw cat_image_stars on image
         for star in cal_params['cat_image_stars']:
            name,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,star_x,star_y,res_px,flux = star
            cv2.circle(show_img, (int(star_x),int(star_y)), int(5), (0,255,0),2)
            cv2.rectangle(show_img, (int(new_cat_x-10), int(new_cat_y-10)), (int(new_cat_x+10) , int(new_cat_y+10) ), (255, 255, 255), 1)
            cv2.imshow('pepe', show_img)
            cv2.waitKey(0)

      for row in star_points[0:50]:
         mx, my, inten = row
         cv2.circle(show_img, (int(mx),int(my)), int(5), (128,128,128),2)
         cv2.imshow('pepe', stars_image)
         cv2.waitKey(0)
         print(row)

      extra_text = "Hello there..." 
      
      ifile = input_file.replace(station_id + "_", "")
      new_cp = minimize_fov(ifile, cal_params, ifile,img.copy(),json_conf, False,cal_params, extra_text, show=1)
      print(new_cp['center_az'], new_cp['center_el'], new_cp['total_res_px'])
      input("MIN1 DONE")
      exit()
      new_cp = minimize_fov(ifile, new_cp, ifile,img.copy(),json_conf, False,cal_params, extra_text, show=1)
      print(new_cp['center_az'], new_cp['center_el'], new_cp['total_res_px'])
      input("MIN2 DONE")
      cal_params = new_cp
      if True:
         show_img = stars_image.copy()
         for star in cal_params['cat_image_stars']:
            name,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,star_x,star_y,res_px,flux = star

            new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(new_cat_x,new_cat_y,ifile,cal_params,json_conf)
            img_new_cat_x, img_new_cat_y = get_xy_for_ra_dec(cal_params, img_ra, img_dec)
            match_dist = angularSeparation(ra,dec,img_ra,img_dec)
            #cat_image_stars.append((name_ascii,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,x,y,res_px,flux))
            res_px = calc_dist((star_x,star_y), (new_cat_x,new_cat_y))
            print("RES FINAL:", res_px)

            cv2.circle(show_img, (int(star_x),int(star_y)), int(5), (0,255,0),2)
            cv2.rectangle(show_img, (int(new_cat_x-10), int(new_cat_y-10)), (int(new_cat_x+10) , int(new_cat_y+10) ), (255, 255, 255), 1)
            cv2.imshow('pepe', show_img)
            cv2.waitKey(30)


      cv2.putText(img, str(text1),  (int(20),int(20)), cv2.FONT_HERSHEY_SIMPLEX, .6, (255,255,255), 1)
      cv2.imshow('pepe', show_img)
      cv2.waitKey(0)


   def insert_last_best_cal(self, cp ):
      if "user_stars" not in cp:
         cp['user_stars'] = [] 
      ivals = [ cp['station_id'], cp['camera_id'], cp['cal_fn'], cp['cal_timestamp'], cp['center_az'], cp['center_el'], cp['ra_center'], cp['dec_center'], cp['position_angle'], cp['pixscale'], json.dumps(cp['user_stars']), json.dumps(cp['cat_image_stars']), json.dumps(cp['x_poly']), json.dumps(cp['y_poly']), json.dumps(cp['x_poly_fwd']), json.dumps(cp['y_poly_fwd']), cp['total_res_px'] ]
      isql = """INSERT OR REPLACE INTO last_best_cal
                (station_id, camera_id, calib_fn, cal_timestamp, az, el, ra, dec, position_angle, pixel_scale, 
                user_stars, cat_image_stars, x_poly, y_poly,x_poly_fwd, y_poly_fwd, res_px) 
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
             """
      #print(isql)
      #print(ivals)
      self.cal_cur.execute(isql, ivals)
      self.cal_con.commit()



   def get_remote_cal_params(self, station_id, cam_id, obs_id, cal_date, show_img, star_points = []):

      # get the last best cal value if it exists
      sql = """
         SELECT station_id, camera_id, calib_fn, cal_datetime, cal_timestamp, az, el, ra, dec, position_angle, pixel_scale, user_stars, cat_image_stars, x_poly, y_poly,x_poly_fwd,y_poly_fwd,res_px,res_deg 
           FROM last_best_cal 
          WHERE station_id = ?
            AND camera_id = ?
      """

      vals = [station_id, cam_id]
      self.cal_cur.execute(sql, vals)
      rows = self.cur.fetchall()

      obs_dt = cal_date 
      cal_timestamp = datetime.datetime.timestamp(obs_dt)

      orig_img = show_img.copy()
      this_range = []
      cloud_cal_dir = "/mnt/archive.allsky.tv/" + station_id + "/CAL/"
      local_cal_dir = "/mnt/f/EVENTS/STATIONS/" + station_id + "/CAL/"
      remote_json_conf_file = local_cal_dir + "as6.json"
      if os.path.isdir(local_cal_dir) is False:
         os.makedirs(local_cal_dir)
      if os.path.exists(remote_json_conf_file) is True:
         remote_json_conf = load_json_file(remote_json_conf_file)
         json_conf = remote_json_conf 
      else:
         print("NO REMOTE JSON CONF FILE:", remote_json_conf_file)
         # try to copy it?
         cloud_file = cloud_cal_dir + "as6.json"
         cmd = "cp " + cloud_file + " " + remote_json_conf_file
         os.system(cmd)
         remote_json_conf = load_json_file(remote_json_conf_file)
         json_conf = remote_json_conf 

         #exit()
      if os.path.exists(local_cal_dir) is False:
         os.makedirs(local_cal_dir)
      print("CLOUD:", cloud_cal_dir)
      remote_cal_files = os.listdir(cloud_cal_dir) 
      #print("REMOTE CAL FILES")

      best_res = 99999
      best_calib = None



      for rf in remote_cal_files:
         remote_file = cloud_cal_dir + rf
         local_file = local_cal_dir + rf
         if os.path.exists(local_file) is False and os.path.isdir(remote_file) is False:
            cmd = "cp " + remote_file + " " + local_file
            print(cmd)
            os.system(cmd)
      #print("All files should be sync'd")
      cal_range_file = local_cal_dir + station_id + "_cal_range.json"
      remote_json_conf = load_json_file(remote_json_conf_file)
      print(cal_range_file)
      lens_file = local_cal_dir + station_id + "_" + cam_id + "_LENS_MODEL.json"
      if os.path.exists(lens_file) is True: 
         lens_model = load_json_file(lens_file)
      else:
         print("NO LENS MODEL!")

      if os.path.exists(cal_range_file) is True:
         cal_range_data = load_json_file(cal_range_file)
      else:
         print("NO CAL RANGE FOR ", station_id, cam_id, obs_id)
         cal_range_data = []

      match_range_data = []
      for row in cal_range_data:
         rcam_id, rend_date, rstart_date, az, el, pos, pxs, res = row

         if np.isnan(az) is True:
            print("NAN SKIP")
            continue
         else:
            print(az, np.isnan(az))
            #exit()

         rcam_id = row[0]
         rend_date = row[1]
         rstart_date = row[2]

         rend_dt = datetime.datetime.strptime(rend_date, "%Y_%m_%d")
         rstart_dt = datetime.datetime.strptime(rstart_date, "%Y_%m_%d")

         if rcam_id == cam_id and np.isnan(az) == False:
            print("CAL RANGE MATCH:", az, el, pos, pxs, np.isnan(az) )
            elp = abs((cal_date - rend_dt).total_seconds()) / 86400
            match_range_data.append(( cal_date, rend_dt, rstart_dt, elp, az, el, pos, pxs, res))


      for mdata in match_range_data:
         show_img = orig_img.copy()



         rcam_id, best_rend_date, best_rstart_date, elp, best_az, best_el, best_pos, best_pxs, res = mdata

         lens_model['center_az'] = best_az 
         lens_model['center_el'] = best_el
         lens_model['position_angle'] = best_pos 
         lens_model['pixscale'] = best_pxs 
         temp = obs_id.replace(station_id + "_", "") 

         cal_params = update_center_radec(temp,lens_model,remote_json_conf)

         cat_stars, short_bright_stars, cat_image = get_catalog_stars(cal_params)
         used = {}
         if True:
            for ix,iy,ii in star_points[0:250]:
               cv2.circle(show_img, (ix,iy), int(5), (0,255,0),1)

         all_res = []
         cat_image_stars = []
         for star in cat_stars[0:100]:
            (name,mag,ra,dec,new_cat_x,new_cat_y,zp_cat_x,zp_cat_y) = star
            cv2.putText(show_img, str(name),  (int(new_cat_x-25),int(new_cat_y-25)), cv2.FONT_HERSHEY_SIMPLEX, .6, (255,255,255), 1)
            cv2.rectangle(show_img, (int(new_cat_x-25), int(new_cat_y-25)), (int(new_cat_x+25) , int(new_cat_y+25) ), (255, 255, 255), 1)

            # find closest image star! 
            dist_arr = []
            for ix,iy,ii in star_points[0:50]:
               this_dist = calc_dist((ix,iy),(new_cat_x,new_cat_y))
               if this_dist < 20:
                  dist_arr.append((this_dist, star, ii))
            dist_arr = sorted(dist_arr, key=lambda x: x[0], reverse=False)
            if len(dist_arr) > 0:
               closest_star = dist_arr[0][1]
               star_x = closest_star[4]
               star_y = closest_star[5]
               flux = dist_arr[0][2]
               res = dist_arr[0][0]
               all_res.append(res)

               new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(new_cat_x,new_cat_y,obs_id,cal_params,json_conf)
               img_new_cat_x, img_new_cat_y = get_xy_for_ra_dec(cal_params, img_ra, img_dec)
               match_dist = angularSeparation(ra,dec,img_ra,img_dec)
               #cat_image_stars.append((name_ascii,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,x,y,res_px,flux))
               res_px = calc_dist((star_x,star_y), (new_cat_x,new_cat_y))
               cat_image_stars.append((name,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,star_x,star_y,res_px,flux))
            #cv2.imshow('pepe', show_img)
            #cv2.waitKey(30)



         #print("CAT IMAGE STARS:", len(cat_image_stars))
         if len(all_res) > 0:
            avg_res = np.mean(all_res)
         else:
            avg_res = 999
         print("RES:", avg_res)
         if avg_res <= best_res :
            print("*** BEST RES BEAT:", best_res, avg_res, cal_params['center_az'], cal_params['center_el'])
            best_res = avg_res
            best_calib = cal_params
            best_calib['cat_image_stars'] = cat_image_stars
            best_calib['total_res_px'] = avg_res 
         cv2.imshow('pepe', show_img)
         cv2.waitKey(0)



      print("FINAL BEST CALIB:", best_calib['center_az'], best_calib['center_el'])
      print("FINAL BEST RES IS:", best_res)
      #print("REMOTE JSON CONF:", obs_id, best_calib, remote_json_conf)
      if best_calib is not None:
         best_calib = update_center_radec(obs_id,best_calib,remote_json_conf)

         obs_dt = cal_date #datetime.datetime.strptime(cal_date, "%Y-%m-%d %H:%M:%S.%f")
         cal_timestamp = datetime.datetime.timestamp(obs_dt)
         best_calib['cal_timestamp'] = cal_timestamp
         best_calib['cal_fn'] = obs_id
         best_calib['camera_id'] = cam_id
         best_calib['station_id'] = station_id
         #best_calib['cal_datetime'] = cal_date.strftime("%Y_%m_%d %H:%M:%S.%f")


         self.insert_last_best_cal(best_calib)


      return(best_calib, remote_json_conf)




   def merge_obs(self, event_id ):
      event_day = self.event_id_to_date(event_id)
      self.event_id = event_id
      self.set_dates(event_day)

      good_obs_file = self.local_evdir + self.event_id + "/" + self.event_id + "_GOOD_OBS.json"
      good_obs = load_json_file(good_obs_file)
      time_matrix = {}
      for station in good_obs:

         if len(good_obs[station]) > 1:
            print("NEED TO MERGE!", station, len(good_obs[station]), "obs")
            for obs_id in good_obs[station]:
               (f_datetime, cam_id, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(obs_id.replace(station + "_" , ""))
               print(obs_id, good_obs[station][obs_id].keys())
               for i in range(0, len(good_obs[station][obs_id]['fns'])):
                  #print(obs_id, i, good_obs[station][obs_id]['times'][i])
                  time_key = good_obs[station][obs_id]['times'][i]
                  if station not in time_matrix:
                     time_matrix[station] = {}
                  if time_key not in time_matrix[station]:
                     time_matrix[station][time_key] = {}
                     time_matrix[station][time_key]['fns'] = []
                     time_matrix[station][time_key]['azs'] = []
                     time_matrix[station][time_key]['els'] = []
                     time_matrix[station][time_key]['gc_azs'] = []
                     time_matrix[station][time_key]['gc_els'] = []
                     time_matrix[station][time_key]['cam_ids'] = []
                  time_matrix[station][time_key]['fns'].append(good_obs[station][obs_id]['fns'][i])
                  time_matrix[station][time_key]['azs'].append(good_obs[station][obs_id]['azs'][i])
                  time_matrix[station][time_key]['els'].append(good_obs[station][obs_id]['els'][i])
                  time_matrix[station][time_key]['gc_azs'].append(good_obs[station][obs_id]['gc_azs'][i])
                  time_matrix[station][time_key]['gc_els'].append(good_obs[station][obs_id]['gc_els'][i])
                  time_matrix[station][time_key]['cam_ids'].append(cam_id)
            #for obs_id in good_obs[station]:
      for station in time_matrix:
         for time_key in time_matrix[station]:
            print(station, time_key, time_matrix[station][time_key] )







   def video_preview_html_js(self, video_urls):
      text_vars = ""
      for url in video_urls:
         if text_vars != "":
            text_vars += ",\n"
         text_vars += """'{:s}'""".format(url)

      js = """
      <div id="videoContainer" style="display:inline-block"></div>
      <b id="output" style="vertical-align:top"></b>
      <script>
      var videoContainer = document.getElementById('videoContainer'),
          output = document.getElementById('output'),
          nextVideo,
          videoObjects =
          [
              document.createElement('video'),
              document.createElement('video')
          ],
          vidSources =
          [
              {:s}
          ],
          nextActiveVideo = Math.floor((Math.random() * vidSources.length));
      
      videoObjects[0].inx = 0; //set index
      videoObjects[1].inx = 1;
      
      initVideoElement(videoObjects[0]);
      initVideoElement(videoObjects[1]);
      
      videoObjects[0].autoplay = true;
      videoObjects[0].src = vidSources[nextActiveVideo];
      videoContainer.appendChild(videoObjects[0]);
      
      videoObjects[1].style.display = 'none';
      videoContainer.appendChild(videoObjects[1]);
      
      function initVideoElement(video)
      {
          video.playsinline = true;
          video.muted = false;
          video.preload = 'auto'; //but do not set autoplay, because it deletes preload
      
          video.onplaying = function(e)
          {
              output.innerHTML = 'Current video source index: ' + nextActiveVideo;
              nextActiveVideo = ++nextActiveVideo % vidSources.length;
              if(this.inx == 0)
                  nextVideo = videoObjects[1];
              else
                  nextVideo = videoObjects[0];
              nextVideo.src = vidSources[nextActiveVideo];
              nextVideo.pause();
          };
      
          video.onended = function(e)
          {
              this.style.display = 'none';
              nextVideo.style.display = 'block';
              nextVideo.play();
          };
      }
      </script> 
      """.format(text_vars)
      
      return(js)      

   def slideshow(self, event_day):
      self.set_dates(event_day)
      print(self.local_evdir)
      sdirs = os.listdir(self.local_evdir)
      image_list = """      
         <!-- EVENT IMAGES LIST -->
         <div class="slideshow-container">
      """

      dots = """
         <div style="text-align:center">
      """
      dc = 1 

#<!-- The dots/circles -->
#<div style="text-align:center">

      for evd in sdirs:
         if os.path.exists(self.local_evdir + evd + "/" + evd + "_REVIEW.jpg") is True: 
            print (self.local_evdir + evd + "/" + evd + "_REVIEW.jpg") 
            image_list += """      
            <div class="mySlides fade">
               <div class="numbertext">1 / 3</div>
               <img src="{:s}/{:s}_REVIEW.jpg" style="width:100%">
               <div class="text">{:s}</div>
            </div>
            """.format(evd, evd, evd)
            dots += """
            <span class="dot" onclick="currentSlide({:s})"></span>
            """.format(str(dc))
            dc += 1

      dots += "</div>"

      image_list += """      
         </div>
      """

      image_list += dots

      fp = open("slideshow.html", "r")
      slide_html = ""
      for line in fp:
         slide_html += line
      slide_html = slide_html.replace("IMAGE_LIST", image_list)


      out = open(self.local_evdir + "slideshow.html", "w")
      out.write(slide_html)
      out.close()
      print("saved slide show:", self.local_evdir + "slideshow.html")
      

   def min_file_size(self, event_day):
      self.set_dates(event_day)
      os.system("find " + self.local_evdir + " | grep .jpg > jpgs.txt")
      fp = open("jpgs.txt")
      for line in fp:
         line = line.replace("\n", "")
         if "MAP_FOV" in line or "REVIEW" in line or "marked" in line:
            img = cv2.imread(line)
            cv2.imwrite(line, img, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
         print(line)

   def make_channel(self, XS,YS, fw=None, fh=None , channel_img = None):
      do_ransac = True 

      # Ransac long objs
      if len(XS) > 10 : 
         temp_xs = []
         temp_ys = []
         for i in range(0,len(XS)):
            temp_xs.append(int(XS[i]))
            temp_ys.append(int(YS[i]))
         try:
            resp = ransac_outliers(temp_xs,temp_ys,"")
            (IN_XS,IN_YS,OUT_XS,OUT_YS,line_X,line_Y,line_y_ransac,inlier_mask,outlier_mask) = resp
         except:
            do_ransac = False
         if do_ransac is True:
            XS = IN_XS
            YS = IN_YS
            temp_xs = []
            temp_ys = []
            for i in range(0,len(XS)):
               temp_xs.append(int(XS[i][0]))
               temp_ys.append(int(YS[i][0]))
            XS = temp_xs
            YS = temp_ys
            print("ARAN XS", XS)
            print("ARAN YS", XS)


      slope,intercept = self.best_fit_slope_and_intercept(XS, YS)


      if len(XS) < 2:
         channel_img = np.zeros((fh,fw),dtype=np.uint8)
         return(channel_img)

      line_regr = [slope * xi + intercept for xi in XS]

      if channel_img is None:
         channel_img = np.zeros((fh,fw),dtype=np.uint8)

      min_lin_x = XS[0]
      max_lin_x = XS[-1]
      min_lin_y = line_regr[0]
      max_lin_y = line_regr[-1]

      print("LINE:", XS, YS)
      cv2.line(channel_img, (int(min_lin_x),int(min_lin_y)), (int(max_lin_x),int(max_lin_y)), (255,255,255), 25)
      #channel_img = self.invert_image(channel_img)
      #if len(channel_img.shape) == 2:
      #   channel_img = cv2.cvtColor(channel_img,cv2.COLOR_GRAY2BGR)

      #cv2.imshow("channel", channel_img)
      #cv2.waitKey(0)

      return(channel_img)

   def best_fit_slope_and_intercept(self,xs,ys):
       xs = np.array(xs, dtype=np.float64)
       ys = np.array(ys, dtype=np.float64)
       if len(xs) < 3:
          return(0,0)
       if ((np.mean(xs)*np.mean(xs)) - np.mean(xs*xs)) == 0:
          m = (((np.mean(xs)*np.mean(ys)) - np.mean(xs*ys)) / 1)

       else:
          m = (((np.mean(xs)*np.mean(ys)) - np.mean(xs*ys)) /
            ((np.mean(xs)*np.mean(xs)) - np.mean(xs*xs)))

       b = np.mean(ys) - m*np.mean(xs)
       if math.isnan(m) is True:
          m = 1
          b = 1

       return m, b

   def invert_image(self, imagem):
      imagem = (255-imagem)
      return(imagem)

   def all_time_index(self):
      # make a link list / nav list of all days in the archive
      # with status / summary info and link to event main page
      # from there we go to the sub pages. 
      # can oversee all from this page. 
      # /EVENTS/index_all_time.html

      
      template = ""
      tt = open("./FlaskTemplates/allsky-template-v2.html")
      for line in tt:
         template += line

      template = template.replace("{TITLE}", "ALLSKY7 ALL TIME EVENTS " )
      template = template.replace("AllSkyCams.com", "AllSky.com")

      data_dir = "/mnt/f/EVENTS/DBS/"
      dbs = os.listdir(data_dir)
      by_year = {}


      tb = pt()
      tb.field_names = ['Date', "Total Stations", "Total Obs", "Solved Events", "Failed Events", "Pending Events"]
      for db in sorted(dbs, reverse=True):


         if "journal" in db or "ALLSKYNETWORK" not in db or "CALIBS" in db :
            continue
         db_file = data_dir + db
         sqlite3.connect(db_file)
         db_con = sqlite3.connect(db_file)
         db_con.row_factory = sqlite3.Row
         db_cur = db_con.cursor()


         date = db.replace("ALLSKYNETWORK_", "")
         date = date.replace(".db", "")
         print(date)
         y,m,d = date.split("_")
         if y not in by_year:
            by_year[y] = {}
            by_year[y]['days'] = []
         by_year[y]['days'].append(date)

         sql = "SELECT station_id from event_obs "
         db_cur.execute(sql)
         rows = db_cur.fetchall()
         status = {}
         reporting_stations = {}
         for row in rows:
            st = row
            reporting_stations[st] = 1

         total_stations = len(reporting_stations.keys())

         sql = "SELECT event_status, count(*) from events group by event_status"
         db_cur.execute(sql)
         rows = db_cur.fetchall()
         status = {}
         for row in rows:
            st, count = row
            status[st] = count


         sql = "SELECT count(*) from event_obs "
         db_cur.execute(sql)
         rows = db_cur.fetchall()
         obs_count = rows[0][0]



         st = ""
         print("")
         solved = 0
         failed = 0
         pending = 0
         for key in status:
            if st != "":
              st += ","
            st += key + str(status[key])
            if "FAIL" in st:
               failed += status[key]
            if "SOLVED" in st or "SUCCESS" in st:
               solved += status[key]
            if "PEND" in st:
               pending += status[key]

         print(db_file, obs_count, st)
         tb.add_row( [date, total_stations, obs_count, solved, failed, pending])

      print(tb)

   def dt_header(self):
      header = """
      <!doctype html>
      <html lang="en">
        <head>

                <style>
                        @import url("https://cdn.jsdelivr.net/npm/bootstrap-icons@1.4.1/font/bootstrap-icons.css");
                        @import url("https://cdn.datatables.net/1.10.25/css/jquery.dataTables.min.css");

                </style>

         <!-- Required meta tags -->
         <meta charset="utf-8">
         <meta name="viewport" content="width=device-width, initial-scale=1">
         <title>AllSky.com </title>
               <script src="https://cdn.plot.ly/plotly-2.2.0.min.js"></script>

               <script src="https://kit.fontawesome.com/25faff154f.js" crossorigin="anonymous"></script>
               <!-- Bootstrap CSS -->
               <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.0-beta3/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-eOJMYsd53ii+scO/bJGFsiCZc+5NDVN2yr8+0RDqr0Ql0h+rP48ckxlpbzKgwra6" crossorigin="anonymous">
               <link rel="alternate" type="application/rss+xml" title="RSS 2.0" href="https://www.datatables.net/rss.xml">
               <script src="https://ajax.googleapis.com/ajax/libs/jquery/3.6.0/jquery.min.js"></script>
               <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.0.0-beta3/dist/js/bootstrap.bundle.min.js" integrity="sha384-JEW9xMcG8R+pH31jmWH6WWP0WintQrMb4s7ZOdauHnUtxwoG2vI5DkLtS3qm9Ekf" crossorigin="anonymous"></script>
               <script type="text/javascript" language="javascript" src="https://cdn.datatables.net/1.10.24/js/jquery.dataTables.min.js"></script>

               <script>
                  all_classes = ['meteor', 'cloud', 'bolt', 'cloud-moon', 'cloud-rain',  'tree', 'planes', 'car-side', 'satellite', 'crow', 'bug','chess-board','question']
                  labels = ['meteor', 'clouds', 'lightening', 'moon', 'rain', 'tree', 'planes', 'cars', 'satellite', 'BIRDS', 'fireflies','noise','notsure']
               </script>
         </head>
      """
      return(header)

   def event_table(self, date):
      self.set_dates(date)
      event_file = self.local_evdir + self.year + "_" + self.month + "_" + self.day  + "_ALL_EVENTS.json"
      event_table_file = self.local_evdir + self.year + "_" + self.month + "_" + self.day  + "_EVENT_TABLE.html"
      if os.path.exists(event_file):
         solved_ev = load_json_file(event_file)
      else:
         print("NO", event_file)
         exit()

      out = self.dt_header()
      out += "<h3>Event Table for </h3>\n".format(date)
      out += "<table id='event_list' class='display'><thead>\n"
      out += "<tr> <th>Event ID</th> <th>Status</th><th>Stations</th> <th>Dur</th> <th>Vel</th> <th>End Alt</th> <th>Shower</th> <th>a</th> <th>e</th> <th>i</th> <th>peri</th> <th>q</th> <th>ls</th> <th>M</th> <th>P</th></tr></thead><tbody>\n"
      bad_events = []
      failed_events = []
      pending_events = []
      for ev in solved_ev:
         v_init = 0
         e_alt = 0
         shower_code = ""
         stations = list(set(ev['stations']))
         ev_id = ev['event_id']
         st_str = ""
         event_status = ev['solve_status']
         print("EVENT STATUS:", event_status)
         if ev['solve_status'] == "FAILED":
            failed_events.append(ev)   
         #if "solution" not in ev:
         #   print("NO SOL",ev['solve_status'])
         for st in sorted(stations):
            #st = st.replace("AMS", "")
            if st_str != "":
               st_str += ","
            st_str += st
         dur = 0
         status = ev['solve_status'] 
         if "solution" in ev:
            sol = ev['solution']
            traj = ev['solution']['traj']
            orb = ev['solution']['orb']
            shower = ev['solution']['shower']
            v_init = str(int(traj['v_init']/1000))  + " km/s"
            e_alt = str(int(traj['end_ele']/1000))  + " km"
            shower_code = shower['shower_code']
            #dur = sol['duration']
            if orb['a'] is None or orb['a'] == "":
               orb['a'] = 0
               orb['e'] = 0
               orb['i'] = 0
               orb['peri'] = 0
               orb['q'] = 0
               orb['la_sun'] = 0
               orb['mean_anomaly'] = 0
               orb['T'] = 0
               bad_events.append(ev)   
         else:
            orb = {}
            orb['a'] = 0
            orb['e'] = 0
            orb['i'] = 0
            orb['peri'] = 0
            orb['q'] = 0
            orb['la_sun'] = 0
            orb['mean_anomaly'] = 0
            orb['T'] = 0
            bad_events.append(ev)   
         ev_link =  """ <a href="javascript:make_event_preview('""" + ev_id + """')">"""
         ev_row = "<tr> <td ><span id='" + ev_id + "'>" + ev_link + "{:s}</a></span></td><td>{:s}</td><td>{:s}</td> <td>{:s}</td> <td>{:s}</td> <td>{:s}</td> <td>{:s}</td> <td>{:0.2f}</td> <td>{:0.2f}</td> <td>{:0.2f}</td> <td>{:0.2f}</td> <td>{:0.2f}</td> <td>{:0.2f}</td> <td>{:0.2f}</td> <td>{:0.2f}</td></tr>\n".format(ev_id, event_status, st_str, str(dur), str(v_init), str(e_alt), str(shower_code),float(orb['a']),float(orb['e']),float(orb['i']),float(orb['peri']),float(orb['q']),float(orb['la_sun']),float(orb['mean_anomaly']),float(orb['T']))
         out += ev_row
      out += """</tbody></table>
      <script>
         $(document).ready( function () {
            $('table.display').dataTable();
         })
      </script>

      """

      fp = open(event_table_file, "w")

      fp.write(out)
      fp.close()

      return(out)


   def reconcile_events_day(self, date):
      # make sure local event pool (sql/filesystem) and aws are all in sync with each other. 
      # delete events in AWS that are not existing here
      # otherwise update AWS if it is missing or the vals don't match. 

      # start with ev file for this day

      self.set_dates(date)


      ev_file = self.local_evdir  + date + "_ALL_EVENTS.json"
      ev_data = load_json_file(ev_file)

      # check aws first
      aws_ids = {}
      for data in ev_data:
         aws_ids[data['event_id']] = data
         sql = """
            SELECT event_id, event_status, run_date 
            FROM events
           WHERE event_id = ?
         """
         self.cur.execute(sql, [data['event_id']])
         rows = self.cur.fetchall()
         if len(rows) is True:
            print("AWS EVENT EXISTS LOCALLY", data['event_id']) 
            if data['solve_status'] == rows[0][1]:
               print("   Same status:", data['solve_status'], rows[0][1])
            else:
               print("   NOT Same status:", data['solve_status'], rows[0][1])

         else:
            print("AWS EVENT DOES NOT EXISTS LOCALLY", data['event_id']) 
            print("DELETE AWS EVENT")
            delete_event(self.dynamodb, date, data['event_id'])

      sql = """
            SELECT event_id, event_status, run_date 
            FROM events
      """
      
      self.sync_dyna_day(date)
      #self.cur.execute(sql)
      #rows = self.cur.fetchall()
      #for row in rows:
      #   event_id, event_status, run_date = row 
      #   if event_id not in aws_ids:
      #      print(event_id, "MISSING FROM AWS")
      #      print("NEED TO INSERT AWS")
      #   else:
      #      print(event_id, "EXISTS INSIDE AWS")








