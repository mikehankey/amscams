import sqlite3
import time
import requests
import boto3
import redis
from solveWMPL import convert_dy_obs, WMPL_solve, make_event_json
import numpy as np
import datetime
import simplejson as json
import os
import shutil
import platform
from lib.PipeUtil import load_json_file, save_json_file, get_trim_num, convert_filename_to_date_cam, starttime_from_file, dist_between_two_points, get_file_info
from lib.intersecting_planes import intersecting_planes
from DynaDB import search_events, insert_meteor_event, delete_event

from sklearn.cluster import DBSCAN
from sklearn import metrics
from sklearn.datasets import make_blobs
from sklearn.preprocessing import StandardScaler
from multiprocessing import Process
import cv2

class AllSkyNetwork():
   def __init__(self):
      self.solving_node = "AWSB1"
      self.plane_pairs = {}
      self.errors = []
      if os.path.exists("admin_conf.json") is True:
         self.admin_conf = load_json_file("admin_conf.json")
         self.data_dir = self.admin_conf['data_dir']
      else:
         self.data_dir = "/mnt/ams2/"
    
  

      self.good_obs_json = None
      self.user =  os.environ.get("USERNAME")
      if self.user is None:
         self.user =  os.environ.get("USER")
      self.platform = platform.system()

      self.home_dir = "/home/" + self.user + "/" 
      self.amscams_dir = self.home_dir + "amscams/"

      self.local_event_dir = self.data_dir + "/EVENTS"
      self.db_dir = self.local_event_dir + "/DBS/"
      if os.path.exists(self.db_dir) is False:
         os.makedirs(self.db_dir)
      self.cloud_event_dir = "/mnt/archive.allsky.tv/EVENTS"
      self.s3_event_dir = "/mnt/allsky-s3/EVENTS"

      self.aws_r = redis.Redis("allsky-redis.d2eqrc.0001.use1.cache.amazonaws.com", port=6379, decode_responses=True)
      self.r = redis.Redis("localhost", port=6379, decode_responses=True)
      self.API_URL = "https://kyvegys798.execute-api.us-east-1.amazonaws.com/api/allskyapi"
      self.dynamodb = boto3.resource('dynamodb')

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
      temp_dir = self.data_dir + "/EVENTS/TEMP/"
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

      cmd = "cp " + self.local_evdir + date + "_MIN_EVENTS.json " + self.cloud_evdir + date + "_MIN_EVENTS.json"
      os.system(cmd)

      cmd = "cp " + self.local_evdir + date + "_plane_pairs.json " + self.cloud_evdir + date + "_PLANE_PAIRS.json"
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
      self.local_event_dir = self.data_dir + "/EVENTS"

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
      response = requests.get(url)
      content = json.loads(response.content.decode())
      save_json_file(self.local_event_dir + "/ALL_STATIONS.json", content)
      self.stations = load_json_file(self.local_event_dir + "/ALL_STATIONS.json")
      self.station_dict = {}
      for data in self.stations:
         sid = data['station_id']
         self.station_dict[sid] = data

   def day_prep(self, date):
      print("ok")

   def set_dates(self, date):
      print("SET DATES FOR:", date)
      self.year, self.month, self.day = date.split("_")
      self.date = date
      self.local_evdir = self.local_event_dir + "/" + self.year + "/" + self.month + "/" + self.day  + "/"
      self.cloud_evdir = self.cloud_event_dir + "/" + self.year + "/" + self.month + "/" + self.day   + "/"
      self.s3_evdir = self.s3_event_dir + "/" + self.year + "/" + self.month + "/" + self.day   + "/"
      self.obs_dict_file = self.local_evdir + self.date + "_OBS_DICT.json"
      self.all_obs_file = self.local_evdir + self.date + "_ALL_OBS.json"
      self.all_obs_gz_file = self.local_evdir + self.date + "_ALL_OBS.json.gz"
      self.cloud_all_obs_file = self.cloud_evdir + self.date + "_ALL_OBS.json"
      self.cloud_all_obs_gz_file = self.cloud_evdir + self.date + "_ALL_OBS.json.gz"
      self.obs_review_file = self.local_evdir + date + "_OBS_REVIEWS.json"
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
       

      input("WAIT")


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
            if -3 <= time_diff <= 3:
               avg_lat = np.mean(min_events[eid]['lats'])
               avg_lon = np.mean(min_events[eid]['lons'])
               match_dist = dist_between_two_points(avg_lat, avg_lon, lat, lon)
               print("Time diff in range. Check Distance??", time_diff, match_dist)
               if match_dist < 900:
                  match_time = 1
                  match_dist = 1
                  matches.append((eid, match_time, match_dist))
      if len(matches) > 0:
         eid = matches[0][0]
         if len(matches) == 1:
            print("We found a matching event. Add this obs to that event!")
         else:
            print("We found MORE THAN ONE matching event. Pick the best one! How???")
         min_events[eid]['stations'].append(station_id)
         min_events[eid]['lats'].append(lat)
         min_events[eid]['lons'].append(lon)
         min_events[eid]['alts'].append(alt)
         min_events[eid]['files'].append(obs_file)
         min_events[eid]['start_datetime'].append(stime)
         avg_time = self.average_times(min_events[eid]['start_datetime'])
         min_events[eid]['stime'] = avg_time
      else:
         print("we could not find a matching event. We should add a new one.")
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
            print("NO REDUCTION!", station_id, obs[3])
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


      print("MIN EVENTS:")
      # maybe re-enable this later, but it takes too much time now
      # should be parallel process later?
      #min_events = self.plane_test_min_events(min_events)

      for me in min_events:
         print("MIN EVENT:", me)
         print(" Stations:", len(min_events[me]['stations']))
         #print("   Planes:", len(min_events[me]['plane_pairs']))
         print("      Obs:", len(min_events[me]['files']))

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
         self.con.commit()
         print("\r" + str(ic) + " " +  obs_id, end="")
         ic += 1

      print("\rTotal OBS for " + date + " : " + str(len(self.all_obs)) + "                                        ",end="")
      print("")


      
   def event_id_to_date(self, event_id):
      year = event_id[0:4]
      mon = event_id[4:6]
      day = event_id[6:8]
      date = year + "_" + mon + "_" + day
      print(date)
      return(date)

      

   def resolve_failed_day(self, event_day):
      sql = """
            SELECT event_id, event_minute, revision, stations, obs_ids, event_start_time, event_start_times,
                   lats, lons, event_status, run_date, run_times
              FROM events
             WHERE event_id like ?
               AND event_status != 'SOLVED'
      """
      vals = [event_day + '%']
      self.cur.execute(sql, vals)
      rows = self.cur.fetchall()
      for row in rows:
         event_id = row[0]
         print("Resolving:", event_id)
         self.resolve_event(event_id)

   def resolve_event(self, event_id):
      date = self.event_id_to_date(event_id)
      self.set_dates(date)
      self.load_stations_file()
      sql = """
            SELECT event_id, event_minute, revision, stations, obs_ids, event_start_time, event_start_times,
                   lats, lons, event_status, run_date, run_times
              FROM events
             WHERE event_id = ?
      """
      vals = [event_id]
      self.cur.execute(sql, vals)
      rows = self.cur.fetchall()
      for row in rows:
         (event_id, event_minute, revision, stations, obs_ids, event_start_time, event_start_times,  \
                 lats, lons, event_status, run_date, run_times) = row

         stations = json.loads(stations)
         obs_ids = json.loads(obs_ids)
         event_start_times = json.loads(event_start_times)
         lats = json.loads(lons)
         temp_obs = {}
         for obs_id in obs_ids:
            st_id = obs_id.split("_")[0]
            vid = obs_id.replace(st_id + "_", "") + ".mp4"
            dict_key = obs_id + ".mp4"
            if st_id not in temp_obs:
               temp_obs[st_id] = {}
            if vid not in temp_obs[st_id]:
               if dict_key in self.obs_dict:
                  self.obs_dict[dict_key]['loc'] = [float(self.station_dict[st_id]['lat']), float(self.station_dict[st_id]['lon']), float(self.station_dict[st_id]['alt'])]
                  temp_obs = convert_dy_obs(self.obs_dict[dict_key], temp_obs)
               else:
                  print(dict_key, "not in obsdict. try deleting the file.")
                  print( self.obs_dict_file)
                  exit()

         print("READY TO SOLVE??")
         self.good_obs = temp_obs
         for st in temp_obs:
            print("STATION:", st)
            for vd in temp_obs[st]:
               print("VID:", vd)
               print(temp_obs[st][vd].keys())

         ev_dir = self.local_evdir + "/" + event_id
         if os.path.exists(ev_dir) is False:
            os.makedirs(ev_dir)
         good_obs_file = ev_dir + "/" + event_id + "_GOOD_OBS.json"
         if os.path.exists(good_obs_file) is False:
            save_json_file(good_obs_file, temp_obs)

         self.solve_event(event_id, temp_obs, 1, 1)

      cmd = "rsync -av --update " + self.local_evdir + "/" + event_id + "/* " + self.cloud_evdir + "/" + event_id + "/"
      print("SKIPPING (for now)", cmd)
      #os.system(cmd)

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
            if "GOOD" in sol_status:
               event_status = "SOLVED:GOOD"
            else:
               event_status = "SOLVED:BAD"
            sql = "UPDATE events set event_status = ? WHERE event_id = ?"
            vals = [event_status, event_id]
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
               #input("WAIT")

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
      print("ROWS:", len(rows))
      print("OBS DICT:", len(self.obs_dict.keys()))
      for row in rows:
         (event_id, event_minute, revision, stations, obs_ids, event_start_time, event_start_times,  \
                 lats, lons, event_status, run_date, run_times) = row
         
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
                  print("STATION ID:", st_id)
                  self.obs_dict[dict_key]['loc'] = [float(self.station_dict[st_id]['lat']), float(self.station_dict[st_id]['lon']), float(self.station_dict[st_id]['alt'])]
                  temp_obs = convert_dy_obs(self.obs_dict[dict_key], temp_obs)
               except:
                  print("Geo error with station!", st_id)
                  self.errors.append(("STATION GEO ERROR", st_id))

         print("READY TO SOLVE??")
         for st in temp_obs:
            for vd in temp_obs[st]:
               print(temp_obs[st][vd].keys())

         print("FORCE:", force)
      
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

      vals = [event_day + "%"]
      self.cur.execute(sql, vals)
      rows = self.cur.fetchall()
      for row in rows:
         event_count = row[0]
         event_status = row[1]
         stats_data["STATUS_" + event_status] = event_count
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

      self.local_event_day_dir = self.data_dir + "/EVENTS/" + y + "/" + m + "/" + d + "/"
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
            print("Continue")
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

      if self.event_json is not None:
         print(self.event_json.keys())


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
      
      #exit()
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
      save_json_file(good_obs_file, temp_obs)

      self.event_status = self.check_event_status(event_id)
      print("CURRENT STATUS FOR EVENT.", self.event_status)
      event_status = self.event_status
      solve_status = self.event_status
      if (self.event_status == "SOLVED" or self.event_status == "FAILED") and force != 1:
         print("Already done this.")
         return() 


      if (os.path.exists(failed_file) is False and os.path.exists(solve_file) is False) or force == 1:
         print("Saving:" ,good_obs_file)

         new_run = True
         # debug only!
         solve_status = WMPL_solve(event_id, temp_obs, time_sync, force)
         try:
            print("RUNNING WMPL...")
            solve_status = WMPL_solve(event_id, temp_obs, time_sync, force)
         except:
            print("WMPL FAILED TO RUN!")
            status = "FAILED"
      else:
         print("WMPL ALREADY RAN...")
         new_run = False
         solve_status = "PENDING"

      print("WMPL SOLVE STATUS:", solve_status)
      if solve_status == "FAILED":
         time_sync=0
         solve_status = WMPL_solve(event_id, temp_obs, time_sync, force)
         print("TRIED A SECOND TIME WITHOUT TIME SYNC!", solve_status)

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



   def event_status_day(self, date=None):
      print("Event status day!")

      report_file = self.local_evdir + date + "_day_report.json" 
      save_json_file(report_file, day_report)

   def plane_test_day(self, date):
      self.load_stations_file()
      qc_report = {}
      valid_obs = {}
      all_obs = {}
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
      for row in rows:
         event_id, event_status, stations, start_times, obs_ids = row
         stations = json.loads(stations)
         start_times = json.loads(start_times)
         obs_ids = json.loads(obs_ids)
         ev_dir = self.local_evdir + event_id + "/"
         if os.path.exists(ev_dir) is False:
            os.makedirs(ev_dir)
         plane_file = ev_dir + event_id + "_PLANES.json"
         if os.path.exists(plane_file) is False:
            plane_report = self.plane_test_event(obs_ids, event_id, event_status)
            save_json_file(plane_file, plane_report)
         else:
            plane_report = load_json_file(plane_file)
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
         if "BAD" in event_status and good_planes == 0:
            event_status += ":INVALID"
         final_data.append((event_id, event_status, good_planes, total_planes))
      final_data = sorted(final_data, key=lambda x: x[1])
      print("Event solving status and plane status report")
      for row in final_data:
         (event_id, event_status, good_planes, total_planes) = row
         try:
            print(event_id, event_status, good_planes, total_planes, round((good_planes/total_planes)*100,1), "%")
         except:
            print("ERR:", good_planes,  total_planes)
      qc_report['final_data'] = final_data

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
      for st in st_stats:
         good = st_stats[st]['GOOD']
         bad = st_stats[st]['BAD']
         total = good + bad
         print(st, good, bad, round((good/total)*100,1))

      qc_report['st_stats'] = st_stats
      qc_report['valid_obs'] = all_obs
      save_json_file(self.local_evdir + orig_date + "_QC.json", qc_report)
      print(self.local_evdir + orig_date + "_QC.json")

      failed_obs_html = ""
      for obs_id in all_obs:
         print("OBS:", obs_id, all_obs[obs_id])
         if all_obs[obs_id] == 0:
            failed_obs_html += self.meteor_cell_html(obs_id)
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
         if "journal" in day:
            continue
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

      print("Publish Day", date)
      self.load_stations_file()
      self.set_dates(date)
      self.date = date
      self.help()

      self.get_all_obs(date)   

      template = ""
      tt = open("./FlaskTemplates/allsky-template-v2.html")
      for line in tt:
         template += line
      tempalte = template.replace("AllSkyCams.com", "AllSky.com")
      self.local_evdir = self.local_event_dir + "/" + self.year + "/" + self.month + "/" + self.day  + "/"
      out_file_good = self.local_evdir + date + "_OBS_GOOD.html"
      out_file_bad = self.local_evdir + date + "_OBS_BAD.html"

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
         if "GOOD" in event_status:
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

      stats_nav += " <a href=javascript:goto_ev('good')>Good " + str(good_ev) + "</a> - "
      stats_nav += " <a href=javascript:goto_ev('bad')>Bad " + str(bad_ev) + "</a> </p><p> "
      stats_nav += "Fail " + str(fail_ev)
      stats_nav += " - " + "Pending " + str(pending_ev)
      stats_nav += """
         </p>
         <P>
          <span class="fa-layers fa-fw fa-2xl" style="background:black; padding: 5px">
             <i class="fa-solid fa-map-location-dot"></i>
             <span class="fa-layers-text fa-inverse" data-fa-transform="shrink-8 down-3" style="font-weight:900">Trajectories</span>
          </span>

          <span class="fa-layers fa-fw fa-2xl" style="background:black; padding: 5px">
             <i class="fa-solid fa-solar-system"></i>
             <span class="fa-layers-text fa-inverse" data-fa-transform="shrink-8 down-3" style="font-weight:900">Orbits</span>
          </span>

          <span class="fa-layers fa-fw fa-2xl" style="background:black; padding: 5px">
             <i class="fa-solid fa-star-shooting"></i>
             <span class="fa-layers-text fa-inverse" data-fa-transform="shrink-8 down-3" style="font-weight:900">Radiants</span>
          </span>

          <span class="fa-layers fa-fw fa-2xl" style="background:black; padding: 5px">
             <i class="fa-solid fa-table-list"></i>
             <span class="fa-layers-text fa-inverse" data-fa-transform="shrink-8 down-3" style="font-weight:900">Data Table</span>
          </span>

          <span class="fa-layers fa-fw fa-2xl" style="background:black; padding: 5px">
             <i class="fa-solid fa-gallery-thumbnails"></i>
             <span class="fa-layers-text fa-inverse" data-fa-transform="shrink-8 down-3" style="font-weight:900">Gallery</span>
          </span>

         </P>
      """
      good_html = ""
      bad_html = "" 

      good_html += style
      good_html += "<h3>Meteor Archive for " + date + " " + day_nav + "</h3>" 
      good_html += "<h4>Solved Events (GOOD)</h4>"
      good_html += "<p>" + stats_nav + "</p>"

      bad_html += "<h3>Meteor Archive for " + date + " " + day_nav + "</h3>"
      bad_html += "<h4>Failed Events (BAD)</h4>"
      bad_html += "<p>" + stats_nav + "</p>"

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
         if os.path.exists(ev_file) is False:
            pick_file = ev_file.replace("-event.json", "_trajectory.pickle")
            # this should make the event.json if the pickle exists
            if os.path.exists(pick_file) is True:
               resp = make_event_json(event_id, ev_dir ,{})

         if os.path.exists(ev_file) is False:
            ev_sum = "<h3>No event solve file: {}</h3>".format(ev_file)
         else:
            ev_data = load_json_file(ev_file)
            if ev_data['orb']['a'] is not None:
               print("EVENT FILE FOUND:", ev_file)
               #print(ev_data['traj'].keys())
               #print(ev_data['orb'].keys())
               #print(ev_data['rad'].keys())
               #print(ev_data['shower'].keys())
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



         if "BAD" not in event_status:
            good_html += "<div class='center'>"
            plane_file = ev_dir + event_id + "_PLANES.json"
            if os.path.exists(plane_file) is False:
               plane_report = self.plane_test_event(obs_ids, event_id, event_status)
               save_json_file(plane_file, plane_report)
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
         else:
            bad_html += "<div>"

            # TEST BAD PLANES! 
            plane_file = ev_dir + event_id + "_PLANES.json"
            if os.path.exists(plane_file) is False:
               plane_report = self.plane_test_event(obs_ids, event_id, event_status)
               save_json_file(plane_file, plane_report)
            else:
               plane_report = load_json_file(plane_file)
            good_planes,total_planes = self.check_planes(plane_report['results'])
            plane_desc[event_id] = str(good_planes) + " / " + str(total_planes) + " PLANES"

            bad_html += "<h3>" + event_id + " - " + event_status + " " 
            bad_html += plane_desc[event_id] + "</h3>"
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
               bad_html += self.meteor_cell_html(obs_id, etime)
               bad_html += "\n"

            bad_html += "<div style='clear: both'></div>"
            bad_html += "</div>"




      fpo = open(out_file_good, "w")
      temp = template.replace("{MAIN_CONTENT}", good_html)
      fpo.write(temp)
      fpo.close()
      temp = template.replace("{MAIN_CONTENT}", bad_html)
      fpo = open(out_file_bad, "w")
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
      save_json_file(report_file, day_report)
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
      self.all_obs = load_json_file(self.all_obs_file)
      for obs in self.all_obs:
         obs_key = obs['station_id'] + "_" + obs['sd_video_file']
         self.obs_dict[obs_key] = obs
      save_json_file(self.obs_dict_file, self.obs_dict)

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

      print(len(planes.keys()), "plane pairs")
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
            solve__data['event_day'] = event_day

         temp = self.good_obs_to_event(event_day, event_id)
         for key in temp:
            solve_data[key] = temp[key]
         event_data = solve_data

      print(event_data)
      input("wait")
      #insert_meteor_event(self.dynamodb, event_id, event_data)
      
   def meteor_cell_html(self, obs_id,edatetime=None):
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
              ">
              <div class="show_hider"> {:s} </div>
         </div>
         """.format(div_id, prev_img_url, disp_text)
      else:
         html = ""
         #station_id + " " + obs_id.replace(".mp4", "")
      return(html)
