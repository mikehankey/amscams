import sqlite3
import boto3
import redis
from solveWMPL import convert_dy_obs, WMPL_solve
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


class AllSkyNetwork():
   def __init__(self):
      self.solving_node = "AWSB1"
      self.errors = []
      self.user =  os.environ.get("USERNAME")
      if self.user is None:
         self.user =  os.environ.get("USER")
      self.platform = platform.system()

      self.home_dir = "/home/" + self.user + "/" 
      self.amscams_dir = self.home_dir + "amscams/"
      self.db_dir = self.amscams_dir + "pipeline"

      self.local_event_dir = "/mnt/ams2/EVENTS"
      self.cloud_event_dir = "/mnt/archive.allsky.tv/EVENTS"
      self.s3_event_dir = "/mnt/allsky-s3/EVENTS"
      self.db_file = self.db_dir + "/ALLSKYNETWORK.db"
      if os.path.exists(self.db_file) is False:
         print("DB FILE NOT FOUND.", self.db_file)
         exit()
      self.con = sqlite3.connect(self.db_file)
      self.con.row_factory = sqlite3.Row
      self.cur = self.con.cursor()

      self.r = redis.Redis("allsky-redis.d2eqrc.0001.use1.cache.amazonaws.com", port=6379, decode_responses=True)
      self.API_URL = "https://kyvegys798.execute-api.us-east-1.amazonaws.com/api/allskyapi"
      self.dynamodb = boto3.resource('dynamodb')

      self.help()

   def sync_dyna_day(self, date):
      #insert_meteor_event(dynamodb=None, event_id=None, event_data=None)
      print("SYNC DYNA DAY")
      events = search_events(self.dynamodb, date, None)
      print("DYNA EVENTS:", len(events))
      event_dict = {}
      for ev in events:
         event_id = ev['event_id']
         event_dict[event_id] = ev
      self.local_event_dir = "/mnt/ams2/EVENTS"

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
      self.stations = load_json_file(self.local_event_dir + "/ALL_STATIONS.json")
      self.station_dict = {}
      for data in self.stations:
         sid = data['station_id']
         self.station_dict[sid] = data

   def day_prep(self, date):
      os.system("clear")

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

      print(self.local_evdir + "/" + self.date + "_OBS_DICT.json")

      local_size, tdd = get_file_info(self.all_obs_file + ".gz") 
      cloud_size, tdd = get_file_info(self.cloud_all_obs_file + ".gz") 

      if os.path.exists(self.all_obs_gz_file) is False and os.path.exists(self.cloud_all_obs_gz_file) is True: 
         print("COPY FILE:", self.cloud_all_obs_gz_file, self.all_obs_gz_file)
         shutil.copyfile(self.cloud_all_obs_gz_file, self.all_obs_gz_file)
         print("Unzipping ", self.all_obs_gz_file)
         os.system("gunzip -k " + self.all_obs_gz_file )
      elif local_size < cloud_size:
         print("COPY/UPDATE FILE:", self.cloud_all_obs_gz_file, self.all_obs_gz_file)
         shutil.copyfile(self.cloud_all_obs_gz_file, self.all_obs_gz_file )
         print("Unzipping ", self.all_obs_gz_file )
         os.system("gunzip -k -f " + self.all_obs_gz_file )
      elif local_size >= cloud_size:
         print("Obs are in-sync")
      else:
         print("FAIL!!!", local_size, cloud_size)
         exit()
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
             exit()

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

      self.plane_file = self.local_evdir + "/" + date + "_PLANE_PAIRS.json"
      self.min_events_file = self.local_evdir + "/" + date + "_MIN_EVENTS.json"
      if os.path.exists(self.plane_file) is True:
         self.plane_pairs = load_json_file(self.plane_file)
      else:
         self.plane_pairs = {}
      self.good_planes = []
      self.bad_planes = []
      self.load_stations_file()
      for data in self.stations:
         print(data.keys())

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
            print(mcm, minute, obs_count)
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

            min_obs = self.get_obs (minute)
            min_events = self.min_obs_to_events(min_obs)
            all_min_events[minute] = min_events
            print("MINUTE OBS:", minute, len(min_obs), len(min_events.keys()))




      save_json_file(self.plane_file, self.plane_pairs)
      save_json_file(self.min_events_file, all_min_events)

      c = 0
      for minute in all_min_events:
         for event_id in all_min_events[minute]:
            event = all_min_events[minute][event_id]
            print(c, "FINAL EVENTS:", event)
            score_data = self.score_obs(event['plane_pairs'])
            for score, key in score_data[0:100]:
               ob1, ob2 = key.split("__")
               gd = ["GOOD", key, ob1, ob2, event['stime'], "", "", ""]
               if len(list(set(event['stations']))) > 1:
                  self.insert_event(event)
               print("Skip single station events.")
            #print(c, "Good planes:", gd[2], gd[3],result[0])
            c += 1
            
      exit()


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
            #self.update_event(ivals) 

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

      save_json_file("min_events.json", min_events)
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
         lat = float(self.station_dict[station_id]['lat'])
         lon = float(self.station_dict[station_id]['lon'])
         alt = float(self.station_dict[station_id]['alt'])
         point = lat * lon
         dd, tt = stime.split(" ")
         sec = tt.split(":")[-1]
         sec = float(sec)
         print(station_id, obs_file, point, stime, sec)
         min_events = self.check_make_events(min_events, station_id, obs_file, stime)


      print("MIN EVENTS:")
      min_events_new = self.plane_test_min_events(min_events)

      for me in min_events:
         print("MIN EVENT:", me)
         print(" Stations:", len(min_events[me]['stations']))
         print("   Planes:", len(min_events[me]['plane_pairs']))
         print("      Obs:", len(min_events[me]['files']))

      # good.append(("(GOOD)", key, obs_id_1, obs_id_2, station_dists[key]['min_dist'], start_time_1, start_time_2, time_diff))

      return(min_events)

      exit()
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


   def get_obs(self, wild):   
      obs_data = []
      sql = """
         SELECT station_id, event_id, event_minute, obs_id, fns, times, xs, ys, azs, els, ints, status, ignore 
           FROM event_obs
          WHERE obs_id like ?
      """
      vals = ["%" + wild + "%"]
      self.cur.execute(sql, vals)
      rows = self.cur.fetchall()
      for row in rows:
         station_id, event_id, event_minute, obs_id, fns, times, xs, ys, azs, els, ints, status, ignore = row
         obs_data.append((station_id, event_id, event_minute, obs_id, fns, times, xs, ys, azs, els, ints, status, ignore))
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


   def day_load_solve_results(self, date=None):
      # check all SQL events for the day
      # update the EV status and solution 
      # based on file system results
      self.set_dates(date)
      self.load_stations_file()
      sql = """

            SELECT event_id, event_minute, revision, stations, obs_ids, event_start_time, event_start_times,  
                   lats, lons, event_status, run_date, run_times
              FROM events
             WHERE event_minute like ?
      """
      self.cur.execute(sql, [date + "%"])
      rows = self.cur.fetchall()
      for row in rows:
         (event_id, event_minute, revision, stations, obs_ids, event_start_time, event_start_times,  \
                 lats, lons, event_status, run_date, run_times) = row
         ev_dir = self.local_evdir + "/" + event_id + "/"
         if os.path.exists(ev_dir + event_id + "-event.json") is True:
            status = "SOLVED"
         elif os.path.exists(ev_dir + event_id + "-fail.json") is True:
            status = "FAILED"
         else:
            status = "PENDING"
         print(event_id, stations, status, ev_dir)
      
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
               self.obs_dict[dict_key]['loc'] = [float(self.station_dict[st_id]['lat']), float(self.station_dict[st_id]['lon']), float(self.station_dict[st_id]['alt'])]
               temp_obs = convert_dy_obs(self.obs_dict[dict_key], temp_obs)

         print("READY TO SOLVE??")
         for st in temp_obs:
            print("STATION:", st)
            for vd in temp_obs[st]:
               print("VID:", vd)
               print(temp_obs[st][vd].keys())

         self.solve_event(event_id, temp_obs, 1, 1)

      cmd = "rsync -av --update " + self.local_evdir + "/" + event_id + "/* " + self.cloud_evdir + "/" + event_id + "/"
      print(cmd)
      os.system(cmd)
      

   def day_solve(self, date=None,force=0):

      self.set_dates(date)
      self.load_stations_file()
      sql = """
            SELECT event_id, event_minute, revision, stations, obs_ids, event_start_time, event_start_times,  
                   lats, lons, event_status, run_date, run_times
              FROM events
             WHERE event_minute like ?
      """
      vals = [date + "%"]
      self.cur.execute(sql, vals)
      rows = self.cur.fetchall()
      #print("ROWS:", len(rows))
      #print("OBS DICT:", len(self.obs_dict.keys()))
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
               #try:
               print("STATION ID:", st_id)
               self.obs_dict[dict_key]['loc'] = [float(self.station_dict[st_id]['lat']), float(self.station_dict[st_id]['lon']), float(self.station_dict[st_id]['alt'])]
               temp_obs = convert_dy_obs(self.obs_dict[dict_key], temp_obs)
               #except:
               #   print("Geo error with station!", st_id)

         print("READY TO SOLVE??")
         for st in temp_obs:
            for vd in temp_obs[st]:
               print(temp_obs[st][vd].keys())

         print("FORCE:", force)
         self.solve_event(event_id, temp_obs, 1, force)
         
      cmd = "rsync -auv " + self.local_evdir + "/* " + self.cloud_evdir + "/"
      print(cmd)
      os.system(cmd)

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

   def check_event_status(self, event_id):
      # is the event defined in the .json files ? 
      # does the event exist in the allsky-s3 
      # does the event exist in the local filesystem
      # is the event in the sql db ?
      # is the event in the dynamodb ?
      # are there duplicates of this event on the local file system, s3f3, in sql or in dyanomdb

      # when we are done we should have the full event data object that goes to DYNA and also goes in the event.json file
      # if the event failed, or the event is pending we should still return the compele event.json data as best as we can.

      event_data = {}
      event_day = self.event_id_to_date(event_id)
      y,m,d = event_day.split("_")
      self.s3_event_day_dir = "/mnt/allsky-s3/EVENTS/" + y + "/" + m + "/" + d + "/"
      self.s3_event_id_dir = self.s3_event_day_dir + event_id + "/"

      self.cloud_event_day_dir = "/mnt/archive.allsky.tv/EVENTS/" + y + "/" + m + "/" + d + "/"
      self.cloud_event_id_dir = self.cloud_event_day_dir + event_id + "/"

      self.local_event_day_dir = "/mnt/ams2/EVENTS/" + y + "/" + m + "/" + d + "/"
      self.local_event_id_dir = self.local_event_day_dir + event_id + "/"

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

      if "failed" in self.local_files or "failed" in self.s3_files:
         self.event_status = "FAILED"
      elif len(self.local_files) > 10 or len(self.s3_files) > 10:
         self.event_status = "SOLVED"
      else :
         self.event_status = "PENDING"

      if len(self.s3_files) == len(self.local_files) or len(self.s3_files) > len(self.local_files):
         self.event_archived = True
      else:
         self.event_archived = False

      if os.path.exists(self.local_event_id_dir + event_id + "-fail.json") is True:
         self.event_fail_json = load_json_file(self.local_event_id_dir + event_id + "-fail.json")
      elif os.path.exists(self.s3_event_id_dir + event_id + "-fail.json") is True:
         self.event_fail_json = load_json_file(self.s3_event_id_dir + event_id + "-fail.json")
      else:
         self.event_fail_json = None 

      if os.path.exists(self.local_event_id_dir + event_id + "-event.json") is True:
         self.event_json = load_json_file(self.local_event_id_dir + event_id + "-event.json")
      elif os.path.exists(self.s3_event_id_dir + event_id + "-event.json") is True:
         self.event_json = load_json_file(self.s3_event_id_dir + event_id + "-event.json")
      else:
         self.event_json = None 

      if os.path.exists(self.local_event_id_dir + event_id + "_GOOD_OBS.json") is True:
         self.good_obs_json = load_json_file(self.local_event_id_dir + event_id + "_GOOD_OBS.json")
      elif os.path.exists(self.s3_event_id_dir + event_id + "_GOOD_OBS.json") is True:
         self.good_obs_json = load_json_file(self.s3_event_id_dir + event_id + "_GOOD_OBS.json")
      else:
         self.good_obs_json = None 
             
      print("Dirs :", self.local_event_id_dir, self.s3_event_id_dir)
      print("Local:", self.local_dir_exists, len(self.local_files))
      print("S3   :", self.s3_dir_exists, len(self.s3_files))
      print("Event Status:", self.event_status)
      print("Event Archived:", self.event_archived)

      if self.event_json is not None:
         print(self.event_json.keys())

      sql_data = self.sql_select_event(event_id)
      if len(sql_data) > 0:
         self.event_in_sql = True
      else:
         self.event_in_sql = False

      print("Event in SQL:", self.event_in_sql)
      #for i in range(0,len(sql_data)):
      #   print(i, sql_data[i])

      dyna_data = self.get_dyna_event(event_id)


      if dyna_data is None:
         print("NO DYNA DATA:", self.event_in_sql)
         return(None)
      elif "solve_status" in dyna_data:
         return(dyna_data['solve_status'])
      else:
         return(None)

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
         exit()

      if self.event_json is not None:
         event['solution'] = self.event_json
         event['solve_status'] = "SOLVED"
      elif self.event_fail_json is not None:
         event['solve_status'] = "FAILED"
      else:
         event['solve_status'] = "PENDING"
      

      return(event)
              
   def solve_event(self,event_id, temp_obs, time_sync, force):

      event_status = self.check_event_status(event_id)
      print("CURRENT STATUS FOR EVENT.", self.event_status)
      if (event_status is "SOLVED" or event_status is "FAILED") and force != 1:
         print("Already done this.")
         return() 

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
      if (os.path.exists(failed_file) is False and os.path.exists(solve_file) is False) or force == 1:
         print("Saving:" ,good_obs_file)
         save_json_file(good_obs_file, temp_obs)
         new_run = True
         try:
            WMPL_solve(event_id, temp_obs, time_sync, force)
         except:
            status = "FAILED"
      else:
         print("WMPL ALREADY RAN...")
         new_run = False

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

         insert_meteor_event(self.dynamodb, event_id, event_data)
         cmd = "./plotTraj.py " + event_id
         print(cmd)
         os.system(cmd)
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

   def publish_day(self, date=None):
      print("Publish Day", date)
      self.load_stations_file()
      self.set_dates(date)
      self.date = date
      self.help()

      report_file = self.local_evdir + date + "_day_report.json" 
      report_data = load_json_file(report_file)
      print(report_file)
      print(report_data.keys())


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

      #print("station_id, operator_name, city, country, op_status, reported_obs, total_events")
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
         #print(data['station_id'], data['operator_name'], data['city'], data['country'], data['op_status'], reported_obs, total_events)
         print(data)
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
      os.system("clear")

   def day_load(self, date):
      os.system("clear")

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
            print(key, start, end)
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
            print(key, start, end)
            start_lat_diff = abs(med_start_lat - start[0])
            start_lon_diff = abs(med_start_lon - start[1])
            end_lat_diff = abs(med_end_lat - start[0])
            end_lon_diff = abs(med_end_lon - start[1])
            score = start_lat_diff + start_lon_diff + end_lat_diff + end_lon_diff
            score_data.append((score, key))
            print("START DIFF:", start_lat_diff, start_lon_diff, end_lat_diff, end_lon_diff)
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
            print(ic, row)
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