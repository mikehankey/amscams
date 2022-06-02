from lib.PipeUtil import cfe, load_json_file, save_json_file, convert_filename_to_date_cam, get_trim_num, get_file_info, calc_dist
#import pymap3d as pm
#wgs84 = pm.Ellipsoid('wgs84');
#from numba import jit
from solveWMPL import convert_dy_obs, WMPL_solve
import threading
from multiprocessing import Process
import time
from lib.kmlcolors import *
import glob 
import simplekml
from lib.PipeManager import dist_between_two_points
from DynaDB import get_event, get_obs, search_events, update_event, update_event_sol, insert_meteor_event, delete_event, search_trash, delete_obs
import numpy as np
import subprocess
import time
import datetime
import os
import redis
import simplejson as json
import boto3
from decimal import Decimal
from lib.solve import man_solve
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return json.JSONEncoder.default(self, obj)

class EventRunner():
   def __init__(self, cmd=None, day=None, month=None,year=None,date=None, use_cache=0):
     # os.system("./DynaDB.py udc " + date + " events")
      self.DATA_DIR = "/mnt/f/"
      self.cloud_host = "https://archive.allsky.tv/"
      self.dynamodb = boto3.resource('dynamodb')
      admin_conf = load_json_file("admin_conf.json")
      self.admin_conf = admin_conf
      self.r = redis.Redis(admin_conf['redis_host'], port=6379, decode_responses=True)
      self.cmd = cmd
      self.date = date 
      self.rejects = {}
      self.obs_event_ids = {}
      if date is not None:
         year,month,day = date.split("_")
      self.event_dict = {}
      print("DAY:", day)
      if day is not None:
         y,m,d = date.split("_")
         self.day = d
         self.month = m
         self.year = y 
         self.event_dir = self.DATA_DIR + "EVENTS/" + self.year + "/" + self.month + "/" + self.day + "/" 
         if cfe(self.event_dir, 1) == 0:
            os.makedirs(self.event_dir)

         self.cloud_event_dir = "/mnt/archive.allsky.tv/EVENTS/" + self.year + "/" + self.month + "/" + self.day + "/" 
         if cfe(self.event_dir, 1) == 0:
            os.makedirs(self.event_dir)
         if cfe(self.cloud_event_dir, 1) == 0:
            os.makedirs(self.cloud_event_dir)
         self.coin_events_file = self.DATA_DIR + "EVENTS/" + self.year + "/" + self.month + "/" + self.day + "/" + self.date + "_COIN_EVENTS.json"  
         self.all_good_obs_file = self.DATA_DIR + "EVENTS/" + self.year + "/" + self.month + "/" + self.day + "/" + self.date + "_ALL_GOOD_OBS.json"  
         self.solve_jobs_file = self.DATA_DIR + "EVENTS/" + self.year + "/" + self.month + "/" + self.day + "/" + self.date + "_SOLVE_JOBS.json"  
         self.ss_events_file = self.DATA_DIR + "EVENTS/" + self.year + "/" + self.month + "/" + self.day + "/" + self.date + "_SS_EVENTS.json"  
         self.all_events_file = self.DATA_DIR + "EVENTS/" + self.year + "/" + self.month + "/" + self.day + "/" + self.date + "_ALL_EVENTS.json"  
         self.all_events_index_file = self.DATA_DIR + "EVENTS/" + self.year + "/" + self.month + "/" + self.day + "/" + self.date + "_ALL_EVENTS_INDEX.json"  
         self.all_obs_file = self.DATA_DIR + "EVENTS/" + self.year + "/" + self.month + "/" + self.day + "/" + self.date + "_ALL_OBS.json"  
         self.obs_dict_file = self.all_obs_file.replace("ALL_OBS", "OBS_DICT")
         self.all_stations_file = self.DATA_DIR + "EVENTS/" + self.year + "/" + self.month + "/" + self.day + "/" + self.date + "_ALL_STATIONS.json"  
         self.single_station_file =  self.event_dir + self.date + "_ALL_SINGLE_STATION_METEORS.json"

         self.plane_pairs_file = self.DATA_DIR + "EVENTS/" + self.year + "/" + self.month + "/" + self.day + "/" + self.date + "_PLANE_PAIRS.json"  
         self.min_report = self.DATA_DIR + "EVENTS/" + self.year + "/" + self.month + "/" + self.day + "/" + self.date + "_MIN_REPORT.json"  
         self.possible = self.DATA_DIR + "EVENTS/" + self.year + "/" + self.month + "/" + self.day + "/" + self.date + "_POSSIBLE.json"  
         self.not_possible = self.DATA_DIR + "EVENTS/" + self.year + "/" + self.month + "/" + self.day + "/" + self.date + "_NOT_POSSIBLE.json"  


         self.cloud_all_events_file = "/mnt/archive.allsky.tv/EVENTS/" + self.year + "/" + self.month + "/" + self.day + "/" + self.date + "_ALL_EVENTS.json"  
         self.cloud_all_events_index_file = "/mnt/archive.allsky.tv/EVENTS/" + self.year + "/" + self.month + "/" + self.day + "/" + self.date + "_ALL_EVENTS_INDEX.json"  
         self.cloud_all_obs_file = "/mnt/archive.allsky.tv/EVENTS/" + self.year + "/" + self.month + "/" + self.day + "/" + self.date + "_ALL_OBS.json"  
         self.cloud_all_stations_file = "/mnt/archive.allsky.tv/EVENTS/" + self.year + "/" + self.month + "/" + self.day + "/" + self.date + "_ALL_STATIONS.json"  
         self.cloud_single_stations_file = "/mnt/archive.allsky.tv/EVENTS/" + self.year + "/" + self.month + "/" + self.day + "/" + self.date + "_ALL_SINGLE_STATION_METEORS.json"  

         if cfe(self.all_events_file) == 1:
            print("LOADING EVENTS FILE!", self.all_events_file)
            self.all_events = load_json_file(self.all_events_file)
            if isinstance(self.all_events, str) is True:
               self.all_events = json.loads(self.all_events)
            print("ALL EV:", len(self.all_events))
            updated_events = []
            for event in self.all_events:
               if "event_id" in event:
                  self.event_dict[event['event_id']] = event
                  updated_events.append(event)
               else:
                  print(event)
                  print("MISSING EVENT ID NEED TO MAKE IT!", event)
                  event['event_id'] = self.make_event_id(event)
                  updated_events.append(event)
            self.all_events = updated_events
            save_json_file(self.all_events_file, self.all_events)

            for ev in self.all_events:
               ev_id = ev['event_id']
               for i in range(0, len(ev['stations'])):
                  st = ev['stations'][i]
                  vid = ev['files'][i]
                  oid = st + "_" + vid
                  self.obs_event_ids[oid] = ev_id
            cc = 0
            self.obs_event_ids_file = self.all_events_file.replace("ALL_EVENTS", "ALL_OBS_IDS")
            save_json_file(self.obs_event_ids_file, self.obs_event_ids)
            print(self.obs_event_ids_file)
         else:
            print("ERROR: NOT FOUND:", self.all_events_file)
            self.all_events = []
         if len(self.all_events) == 0:
            print("0 events!")
         print("EVENT FILE:", self.all_events_file)
         # DOWNLOAD DYNA DATA IF IT DOESN'T EXIST
         # OR IF THE CACHE FILE IS OLDER THAN X MINUTES
         if cfe(self.all_events_index_file) == 0:
            print("ERROR MISSING:", self.all_events_index_file) 
            #exit()
         if use_cache == 0:
            #print("SKIP CACE")
            if "master" in self.admin_conf:
               os.system("./DynaDB.py udc " + self.date)

         if cfe(self.all_events_index_file) == 1:
            self.all_events_index = load_json_file(self.all_events_index_file)
         else:
            self.all_events_index = None
         size, tdiff = get_file_info(self.all_obs_file)

         print("OBS FILE:", self.all_obs_file)
         print("TD:", tdiff)
         if cfe(self.all_obs_file) == 1 and tdiff < 1000:
            self.all_obs = load_json_file(self.all_obs_file)
         else:
            self.all_obs = None
            print("NO OBS FILE DOWNLOAD FROM CLOUD!", self.all_obs_file)
            cf = self.all_obs_file.replace("/ams2", "/archive.allsky.tv")
            cf += ".gz"

            if cfe(cf) == 1:
               os.system("cp " + cf + " " + self.all_obs_file + ".gz")
               print("cp " + cf + " " + self.all_obs_file + ".gz")
               os.system("gunzip -f " + self.all_obs_file + ".gz")

            self.all_obs = load_json_file(self.all_obs_file)
         if False: #cfe(self.all_stations_file) == 1:
            self.all_stations = load_json_file(self.all_stations_file)
         else:
            self.all_stations = None
            cf = self.all_stations_file.replace("/ams2", "/archive.allsky.tv")
            if cfe(cf) == 1:
               os.system("cp " + cf + " " + self.all_stations_file)
            self.all_stations = load_json_file(self.all_stations_file)

         print("ALL STATIONS FILE:", self.all_stations_file)
         self.station_loc = {}
         for data in self.all_stations:
            sid = data[0]
            print("STATION_LOC:", sid)
            lat = data[1]
            lon = data[2]
            alt = data[3]
            self.station_loc[sid] = [lat,lon, alt]
      else:
         print("DAY IS NONE?")
      print("OBS FILE:", self.all_obs_file)

      for ev in self.all_events:
         event_id = ev['event_id']
         year = event_id[0:4]
         mon = event_id[4:6]
         dom = event_id[6:8]
         ev['event_day'] = year + "_" + mon + "_" + dom
         print(ev['event_id'], ev['stations'])
      #   insert_meteor_event(None, ev['event_id'], ev)


   def make_obs_dict(self):
      #if cfe(self.obs_dict_file) == 1: 
      #   self.obs_dict = load_json_file (self.obs_dict_file)
      #   return()
      #else:
      if cfe(self.obs_dict_file) == 1:
         sz, tdiff1 = get_file_info(self.all_obs_file)
         sz, tdiff2 = get_file_info(self.obs_dict_file)
      else:
         tdiff1 = 9999
         tdiff2 = 0
      if tdiff1 > tdiff2:
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
      for obs in self.all_obs:
         obs_key = obs['station_id'] + "_" + obs['sd_video_file']
         self.obs_dict[obs_key] = obs
      save_json_file(self.obs_dict_file, self.obs_dict)

   def obs_by_minute(self):
      self.obs_dict = {}
      obs_by_min = {}


      for obs in self.all_obs:
         minute_str = obs['sd_video_file'][0:16]
         obs_key = obs['station_id'] + ":" + obs['sd_video_file']
         self.obs_dict[obs_key] = obs
         if minute_str not in obs_by_min:
            obs_by_min[minute_str] = {}
            obs_by_min[minute_str]['count'] = 1 
            obs_by_min[minute_str]['obs'] = []
            obs_by_min[minute_str]['obs'].append(obs_key)
         else:
            obs_by_min[minute_str]['count'] += 1
            obs_by_min[minute_str]['obs'].append(obs_key)
         print("OBM", obs['station_id'], obs['sd_video_file'])
      
      possible = []
      not_possible = []
      for mr in obs_by_min:
         if obs_by_min[mr]['count'] > 1:
            sc = self.station_count(obs_by_min[mr]['obs'])
            print("SC IS:", sc)
            obs_by_min[mr]['station_count'] = sc
            if sc > 1:
               print("POSSIBLE?", mr, sc, obs_by_min[mr]['obs'])
               events,non_events = self.obs_to_events(obs_by_min[mr]['obs'])
               if len(events) > 0:
                  possible.append(events)
               if len(non_events) > 0:
                  not_possible.append(non_events)
               print("EV / NEV:", len(events), len(non_events))
               obs_by_min[minute_str]['possible_events'] = events 
               obs_by_min[minute_str]['not_possible_events'] = non_events 
            else:
               print("STATION COUNT:", sc)

      save_json_file(self.min_report, obs_by_min)
      save_json_file(self.possible, possible)
      save_json_file(self.not_possible, not_possible)
      print("saved:", self.min_report)
      print("saved:", self.possible)
      print("saved:", self.not_possible)



   def find_point_from_az_dist(self, lat,lon,az,dist):
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

   def make_plane_kml(self, event):
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

   def resolve_event(self, event_id):
      self.make_obs_dict()
      custom_obs_file = self.event_dir + event_id + "/" + event_id + "-custom-obs.json"
      print(custom_obs_file)
      custom_obs = {}
      if cfe(custom_obs_file) == 1:
         co = load_json_file(custom_obs_file)
         for o in co['custom_obs']:
            custom_obs[o] = {}
      else:
         custom_obs = None
      print("CUSTOM OBS:", custom_obs)
      if os.path.exists(self.coin_events_file) is False:
         cl_file = self.coin_events_file.replace("ams2/", "archive.allsky.tv/")
         if os.path.exists(cl_file) is True:
            os.system("cp " + cl_file + " " + self.coin_events_file)
            
      
      self.coin_events = load_json_file(self.coin_events_file) 
      event = self.coin_events[event_id]
      good_planes = {}
      #print(event.keys())
      print("EVOBS:", event['obs'])
      if custom_obs is not None:
         event['obs'] = custom_obs 

         event = self.coin_event_to_dyn_event(event)


      obs_report = ""

      for obs in event['obs']:
         qc_check = self.qc_obs_points(obs)
         print("QC CHECK:", obs, qc_check)
         event['obs'][obs]['qc'] = qc_check
         print("OBS IS:", obs)
         el = obs.split("_")
         station_id = el[0]
         video_file = obs.replace(station_id + "_", "")

         dobs = get_obs(station_id, video_file)
         self.obs_dict[obs] = dobs
         #print (dobs.keys())
         obs_report += station_id + " " + video_file 
         obs_report += "\n"
         if "meteor_frame_data" in dobs:
            for row in dobs['meteor_frame_data']:
               obs_report += str(row) + "\n"
         else:
            obs_report += "OBS Missing MFD data!\n"
         if qc_check['status_code'] == 0:
            obs_report += "FAILED QC! " + qc_check['desc']
         else:
            obs_report += "PASSED QC! " + qc_check['desc']

      fp = open("obs.txt", "w")
      fp.write(obs_report)
      fp.write(str(event))
      fp.close()

      #exit()
      #get_obs(station_id, sd_video_file):
      #event = self.do_planes_for_event(event, redo=1)
      self.coin_events[event_id] = event
      

      save_json_file(self.coin_events_file, self.coin_events)
      

      plane_good = []
      plane_bad = []
      for plane in event['planes']:
         status = (event['planes'][plane][0])
         if "solved" in status:
            plane_good.append((plane, event['planes'][plane]))
         else:
            plane_bad.append((plane,event['planes'][plane]))

      self.make_plane_kml(event)
      # LOAD THE LATEST OBS
      # DELETE EXISTING PLANES
      # REMAKE THE GOOD OBS
      # RERUN THE SOLVE
      #self.jobs.append(("WMPL_solve", event_id, good_obs, 1))


      print("RESOLVE?")
      if True:
         good_obs = {}
         good_planes = {}
         bad_planes = {}
         for plane in event['planes']:
            obs1, obs2 = plane.split(":")
            if event['planes'][plane][0] == "plane_solved":
               if obs1 in good_planes:
                  good_planes[obs1] += 1
               else:
                  good_planes[obs1] = 1
               if obs2 in good_planes:
                  good_planes[obs2] += 1
               else:
                  good_planes[obs2] = 1
            else:
               if obs1 in bad_planes:
                  bad_planes[obs1] += 1
               else:
                  bad_planes[obs1] = 1
               if obs2 in bad_planes:
                  bad_planes[obs2] += 1
               else:
                  bad_planes[obs2] = 1


         if True:
            for gp in good_planes:
               qc = self.coin_events[event_id]['obs'][gp]['qc']
               print("QC:", gp, qc)
               el = gp.split("_")
               station_id = el[0]
               s_lat = self.station_loc[station_id][0]
               s_lon = self.station_loc[station_id][1]
               s_alt = self.station_loc[station_id][2]
               print("STATION ID IS:", station_id, s_lat, s_lon, s_alt)
               print("GP IS:", gp) 
               self.obs_dict[gp]['loc'] = [s_lat,s_lon,s_alt] 
               if "station_id" not in self.obs_dict[gp]:
                  print("no data in obs dict for ", gp, self.obs_dict[gp])
                  continue
               good_obs = convert_dy_obs(self.obs_dict[gp], good_obs)

      if custom_obs is not None:
         good_obs = {}
         print("CUSTOM")
         print("STATION LOCATION:", self.station_loc.keys())
         for obs in event['obs']:
            print("OBS IS:", obs)
            el = obs.split("_")
            station_id = el[0]
            vid = obs.replace(station_id + "_", "")
            s_lat = self.station_loc[station_id][0]
            s_lon = self.station_loc[station_id][1]
            s_alt = self.station_loc[station_id][2]
            print("STATION ID IS:", station_id, s_lat, s_lon, s_alt)
            self.obs_dict[obs]['loc'] = [s_lat,s_lon,s_alt] 
            print("GOOD OBS:", len(good_obs))
            if obs not in self.obs_dict:
               print("OBS IS NOT IN TEHE OBS DICT!", obs)
            else:
               print("OBS IS IN THE OBS DICT!", obs)
               good_obs = convert_dy_obs(self.obs_dict[obs], good_obs)
               good_obs[station_id][vid]['loc'] =  [s_lat,s_lon,s_alt]
               print(good_obs)
               print("GOOD AFTER OBS:", len(good_obs))
   
      print("THE GOOD OBS!")
      for station_id in good_obs:
         for vid in good_obs[station_id]:
            print(station_id, vid)
            print(good_obs[station_id][vid]['loc'])
      obs_file = self.event_dir + event_id + "/" + event_id + "_GOOD_OBS.json"
      for st in good_obs:
         for vid in good_obs[st]:
            print("GOOD OBS:", st, vid)

      save_json_file(obs_file, good_obs)
      WMPL_solve(event_id, good_obs, 0, 1)


   def qc_obs_points(self, obs):
      print("OBS IS:", obs)
      obs_data = self.obs_dict[obs]
      if "meteor_frame_data" in obs_data:
         last_x = None
         last_y = None
         first_x = obs_data['meteor_frame_data'][0][2]
         first_y = obs_data['meteor_frame_data'][0][3]
         last_dist_from_start = 0
         dist_from_start = 0
         qc_data = []
         for row in obs_data['meteor_frame_data']:
            (frame_time_str, fn, hd_x, hd_y, sd_w, sd_h, oint, ra, dec, az, el) = row
            if last_x is not None:
               last_dist = calc_dist((last_x,last_y), (hd_x,hd_y))
               dist_from_start = calc_dist((first_x, first_y), (hd_x, hd_y))
            else:
               last_dist = 0
               dist_from_start = 0
            seg_len = dist_from_start - last_dist_from_start
            #print(obs, "MFD:", hd_x, hd_y, last_dist, dist_from_start, seg_len)
            qc_data.append((obs, hd_x,hd_y,last_dist, dist_from_start, seg_len))
            last_x = hd_x
            last_y = hd_y
            last_dist_from_start = dist_from_start
         qc_resp = self.eval_qc_data(qc_data)
         return(qc_resp)
      else:
         qc_response = {}
         qc_response['status_code'] = 0
         qc_response['desc'] = "FAILED QC: No MFD"
         
         return(qc_resp)

   def eval_qc_data(self, qc_data):
      segs = [row[5] for row in qc_data]
      med_seg = np.median(segs)
      if med_seg == 0:
         qc_response = {}
         qc_response['status_code'] = 0
         qc_response['desc'] = "FAILED QC: 0 median seg len"
         print("FAILED QC: 0 med seg len") 
         return(qc_response)

      bad = 0
      good = 0
      rc = 0
      print("QC CHECK")
      print("--------")
      for row in qc_data:
         med_seg_diff = abs(row[5] - med_seg)
         if (med_seg_diff > 5 or row[5] > med_seg * 2) and rc > 0 :
            ok = 0
            bad += 1
            print("   ", rc, row[1], row[2], "BAD MFD SEG", row )
         else:
            ok = 1
            good += 1
            print("   ", rc, row[1], row[2], "GOOD MFD SEG", row )
         #print(ok, "MED SEG DIFF:", med_seg, med_seg_diff, row)
         rc += 1
      if bad > 0 and good > 0:
         perc_good = 1 - (bad / good)
      elif good == 0:
         perc_good = 0
      else:
         perc_good = 1
      print("PERC GOOD:", perc_good)
      if perc_good < .5:
         qc_response = {}
         qc_response['status_code'] = 0
         qc_response['desc'] = "FAILED QC: " + str(int(perc_good*100)) + " % passed seg."
         return(qc_response)
      else:
         qc_response = {}
         qc_response['status_code'] = 1
         qc_response['desc'] = "PASSED QC"
         return(qc_response)

   def coin_solve(self):
      #self.event_dir + 
      coin_events = load_json_file(self.coin_events_file )
      self.make_obs_dict()
      self.jobs = []
      all_good_obs = {}

      for event_id in coin_events:
         print(event_id)
         if cfe(self.event_dir + event_id + "/", 1) == 0:
            os.makedirs(self.event_dir + event_id)
         obs_file = self.event_dir + event_id + "/" + event_id + "_GOOD_OBS.json"
         good_planes = {}
         bad_planes = {}
         good_obs = {}
         for plane in coin_events[event_id]['planes']:
            obs1, obs2 = plane.split(":")
            if coin_events[event_id]['planes'][plane][0] == "plane_solved":
               if obs1 in good_planes:
                  good_planes[obs1] += 1
               else:
                  good_planes[obs1] = 1
               if obs2 in good_planes:
                  good_planes[obs2] += 1
               else:
                  good_planes[obs2] = 1
            else:
               if obs1 in bad_planes:
                  bad_planes[obs1] += 1
               else:
                  bad_planes[obs1] = 1
               if obs2 in bad_planes:
                  bad_planes[obs2] += 1
               else:
                  bad_planes[obs2] = 1

         if len(good_planes) == 0:
            continue

         # if the obs file doesn't exist yet create it, otherwise load it.
         if cfe(obs_file) == 1:
            good_obs = load_json_file(obs_file)
         else:
            for gp in good_planes:
               if gp not in self.obs_dict:
                  print(gp, "not in obs dict!")
                  continue
               station_id = gp.split("_")[0]
               #print("LOC:", self.station_loc[station_id])
               s_lat = self.station_loc[station_id][0]
               s_lon = self.station_loc[station_id][1]
               s_alt = self.station_loc[station_id][2]
               self.obs_dict[gp]['loc'] = [s_lat,s_lon,s_alt] 
               good_obs = convert_dy_obs(self.obs_dict[gp], good_obs)
               #print("GOOD OBS?", good_obs)
               print("SAVING:", obs_file)
               save_json_file(obs_file, good_obs)

         #print("WMPL READY?", good_obs)
         all_good_obs[event_id] = good_obs
         for st in good_obs:
            for vid in good_obs[st]:
               print("   ST VID", st, vid)
               #print("GOOD OBS?", good_obs[st][vid])
         # TRY WITH TIME SYNC ON
         #WMPL_solve(event_id, good_obs, 1)
         self.jobs.append(("WMPL_solve", event_id, good_obs, 1))
         #for ob in good_obs:
         #   print(ob)
         for gp in bad_planes:
            print("BAD PLANES:", gp) #, bad_planes[gp])
         all_good_obs[event_id] = good_obs
      save_json_file(self.solve_jobs_file, self.jobs)
      save_json_file(self.all_good_obs_file, all_good_obs)
      print("SAVED:", self.solve_jobs_file)
      print("SAVED:", self.all_good_obs_file)
      self.run_solve_jobs()

   def plane_station_stats(self ):
      coin_events = load_json_file(self.coin_events_file)
      plane_stats = {}
      plane_stats = {}
      for ev_id in coin_events:
         planes = coin_events[ev_id]['planes']
         for pkey in planes:
            obs1, obs2 = pkey.split(":")
            st1 = obs1.split("_")[0]
            st2 = obs2.split("_")[0]
            status, line1, line2 = planes[pkey]
            if status == "plane_solved":
               if st1 not in plane_stats:
                  plane_stats[st1] = {}
                  plane_stats[st1]['solved'] = 1
                  plane_stats[st1]['failed'] = 0
               else:
                  plane_stats[st1]['solved'] += 1
               if st2 not in plane_stats:
                  plane_stats[st2] = {}
                  plane_stats[st2]['solved'] = 1
                  plane_stats[st2]['failed'] = 0
               else:
                  plane_stats[st2]['solved'] += 1
            else:
               if st1 not in plane_stats:
                  plane_stats[st1] = {}
                  plane_stats[st1]['solved'] = 0 
                  plane_stats[st1]['failed'] = 1
               else:
                  plane_stats[st1]['failed'] += 1
               if st2 not in plane_stats:
                  plane_stats[st2] = {}
                  plane_stats[st2]['solved'] = 0
                  plane_stats[st2]['failed'] = 1
               else:
                  plane_stats[st2]['failed'] += 1
            print(pkey, status)

      fail_rpt = []
      for station_id in plane_stats:

         failed = plane_stats[station_id]['failed']
         solved = plane_stats[station_id]['solved']
         total = failed + solved
         if total > 0:
            failed_perc = failed / total
         else:
            failed_perc = 0 
         print(station_id, plane_stats[station_id], failed_perc)
         fail_rpt.append((station_id, solved, failed, total, failed_perc))
      fail_rpt = sorted(fail_rpt, key=lambda x: (x[4]), reverse=True)
      for row in fail_rpt:
         print(row)

   def meteor_preview_html(self, obs_id):
      station_id = obs_id.split("_")[0]
      sd_vid = obs_id.replace(station_id + "_", "")
      year = sd_vid[0:4]
      day = sd_vid[0:10]
      img_thumb_url = self.cloud_host + station_id + "/METEORS/" + year + "/" + day + "/" + obs_id.replace(".mp4", "-prev.jpg")
      html = """
          <div class='meteor_thumb' style='float:left'>
          <img src=""" + img_thumb_url + """ onerror='this.style.display = "none"'><br>
          </div>
      """
      return(html)

   def EOD_summary(self):
      #self.obs_event_ids
      all_obs = load_json_file(self.all_obs_file)
      coin_events = load_json_file(self.coin_events_file)
      all_events = load_json_file(self.all_events_file)
      ss_events = load_json_file(self.ss_events_file)

      obs_list = []
      for data in all_obs:
         ob_id = data['station_id'] + "_" + data['sd_video_file']
         obs_list.append(ob_id)


      print("ALL OBS:", len(all_obs))
      print("COIN OBS:", len(coin_events.keys()))
      print("ALL EVENTS:", len(all_events))
      print("SS EVENTS:", len(ss_events))

   def coin_events(self):
      self.events = {}
      print("MAKE OBS DICT.")
      self.make_obs_dict()
      #if False:
      for obs in self.all_obs:
         station_id = obs['station_id']
         sd_vid = obs['sd_video_file']
         sd_vid = obs['sd_video_file']
         s_start_dt = self.starttime_from_file(sd_vid)

         new_event, self.events = self.get_make_event(self.events,station_id, sd_vid, s_start_dt)

      plane_jobs = []
      coin_events = {}
      ss_events = {}
      self.run_plane_jobs()
      missing_planes = 0
      for ev_id in sorted(self.events.keys(),reverse=True) :
         print(ev_id, len(self.events[ev_id]['stations'].keys()))
         if len(self.events[ev_id]['stations'].keys()) > 1:
            if "planes" not in self.events[ev_id]:
               rkey = "EVP:" + ev_id 
               rval = self.r.get(rkey)
               if rval is None:
                  print(ev_id, "NO RVAL!", rkey, rval)
                  e_planes_file = self.event_dir + ev_id + "/" + ev_id + "-planes.json"
                  if cfe(e_planes_file) == 1:
                     planes = load_json_file(e_planes_file)
                     self.events[ev_id]['planes'] = planes
                  else:
                     missing_planes += 1
               else:
                  print(ev_id, "YES RVAL!", rkey, rval)
                  self.events[ev_id]['planes'] = json.loads(rval)
            else:
               print("PLANES ARE GOOD FOR :", ev_id)
      print("ALL PLANES SHOULD BE DONE ARE THEY?")
      print("MISSING PLANES:", missing_planes)
      for ev_id in sorted(self.events.keys(),reverse=True) :
         print("CHECKING PLANES FOR EV_ID:", ev_id)
         if len(self.events[ev_id]['stations'].keys()) > 1:
            ndt = []
            for dt in self.events[ev_id]['start_times']:
               ndt.append(dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3])
            self.events[ev_id]['start_times'] = ndt
            # INSERT EVENT PLANES DATA HERE
            #self.events[ev_id] = self.do_planes_for_event(self.events[ev_id])
            if "planes" not in self.events[ev_id]:
               print("PLANES NOT IN EVENT!:", ev_id, self.events[ev_id].keys())
               rkey = "EVP:" + ev_id
               planes = self.r.get(rkey)
               if planes is not None:
                  planes = json.loads(planes)
                  print("REDIS PLANES FOUND:", rkey)
                  self.events[ev_id]['planes'] = planes
               else:
                  print("NO PLANES IN REDIS?", rkey)
                  self.events[ev_id] = self.do_planes_for_event(self.events[ev_id])
                  print("AFTER PLANE", self.events[ev_id])
                  self.r.set(rkey, json.dumps(self.events[ev_id]['planes']))
                  print("SET REDIS:", rkey)


            coin_events[ev_id] = self.events[ev_id]
            print(ev_id, len(self.events[ev_id]['stations'].keys()), " STATIONS")
         else:
            ndt = []
            for dt in self.events[ev_id]['start_times']:
               ndt.append(dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3])
            self.events[ev_id]['start_times'] = ndt


            ss_events[ev_id] = self.events[ev_id]
      save_json_file(self.coin_events_file, coin_events)
      save_json_file(self.ss_events_file, ss_events)
      print("SAVED:", self.coin_events_file)


      return()

      pos_obs = {}

      if False:
      #for data in possible:
         print("POSSIBLE EVENT DATA:", data)
         for row in data:
            print("POS:", row[4], row[5])
            obs1 = row[4].replace(":", "_")
            obs2 = row[5].replace(":", "_")
            pos_obs[obs1] = row
            pos_obs[obs2] = row

      ev_obs = []
      for key in sorted(pos_obs,reverse=True):
         station_id = key.split("_")[0]
         obs_file = key.replace(station_id + "_", "")
         ev_obs.append((station_id, obs_file))
         print(station_id, obs_file)
      ev_obs = sorted(ev_obs, key=lambda x: (x[1]), reverse=True)
      events = {}
      for data in ev_obs:
         station_id, sd_vid = data
         s_start_dt = self.starttime_from_file(sd_vid)
         print(station_id, sd_vid, s_start_dt)
         new_event, events = self.get_make_event(events,station_id, sd_vid, s_start_dt)

   def do_planes_for_event(self, event, redo=0):
      planes = {}
      e_planes_file = self.event_dir + event['event_id'] + "/" + event['event_id'] + "-planes.json"
      if cfe(self.event_dir + event['event_id'],1) == 0:
         os.makedirs(self.event_dir + event['event_id'])

      if cfe(e_planes_file) == 1 and redo == 0:
         planes = load_json_file(e_planes_file)
         event['planes'] = planes
         return(event)
      print("PLANES:", event['event_id'])
      for obs_id in event['obs']:
         st = obs_id.split("_")[0]
         for x_obs_id in event['obs']:
            x_st = x_obs_id.split("_")[0]
            if st != x_st:
               temp = sorted([obs_id, x_obs_id])
               plane_key = temp[0] + ":" + temp[1]
               if plane_key not in planes:
                  obs1 = self.obs_dict[obs_id]
                  obs2 = self.obs_dict[x_obs_id]
                  obs1['station_id'] = st
                  obs2['station_id'] = x_st
                  obs1['obs_id'] = obs_id
                  obs2['obs_id'] = x_obs_id
                  rkey = "IP:" + plane_key
                  rval = self.r.get(rkey)
                  #print("RVAL IS:", rval)
                  if redo == 1:
                     rval = None
                  if rval is None:
                     print("NO REDIS RESULT FOR:", rkey )
                     result = self.plane_test(obs1, obs2)
                     if result is not None:
                        self.r.set(rkey, json.dumps(result))
                     else:
                        failed_res = ['plane_failed', [0,0,0,0,0,0], [0,0,0,0,0,0]]
                        self.r.set(rkey, json.dumps(failed_res))
                  else:
                     print("GOT REDIS RESULT FOR:", rkey)
                     result = json.loads(rval)
                  if result is not None:
                     print(result)
                     if "failed" not in result:
                        status, line1, line2 = result
                        planes[plane_key] = result
                     else:
                        planes[plane_key] = ["FAILED", [],[]]
                          
                  else:
                     planes[plane_key] = "FAILED", [], [] 
      event['planes'] = planes

      rkey = "EVP:" + event['event_id'] 
      self.r.set(rkey, json.dumps(planes))
      print("SETTING REDIS PLANES:", rkey)
      save_json_file(e_planes_file, planes)

      #print(event['planes'])
      #result = self.plane_test(obs1, obs2)
      return(event)

   def get_make_event(self, events, station_id, sd_vid, s_start_dt):
      obs_id = station_id + "_" + sd_vid
      s_lat = self.station_loc[station_id][0]
      s_lon = self.station_loc[station_id][1]
      event_found = 0
      for event_id in events:
         event = events[event_id]
         tdiff = abs((min(event['start_times']) - s_start_dt).total_seconds())
         min_dist = 9999
         if tdiff < 3:
            for t_obs_id in event['obs']:
               if t_obs_id == obs_id:
                  continue
               s2 = t_obs_id.split("_")[0]
               s2_lat = self.station_loc[s2][0]
               s2_lon = self.station_loc[s2][1]
               station_dist = dist_between_two_points(s_lat, s_lon, s2_lat, s2_lon)
               print(station_id, s2, s_lat, s_lon, s2_lat, s2_lon, station_dist, tdiff)
               if station_dist < min_dist:
                  min_dist = station_dist



         #print(s_lat, s_lon, s2_lat, s2_lon, tdiff, min_dist)
         if abs(tdiff) < 3 and min_dist < 300:
            print("ADD TO EXISTING EVENT!", event_id)
            #print("OBS MATCH INFO:", obs_id, tdiff, min_dist)
            #print("EXISTING EVENT OBS:", event['obs'])
            event_found = 1
            new_event = event 
            new_event['obs'][obs_id] = {}
            new_event['stations'][station_id] = {}
            new_event['start_times'].append(s_start_dt) #.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            events[event_id] = new_event 
            return(new_event, events)
      if event_found == 0:
         new_event = {}
         new_event['start_times'] = []
         new_event['event_id'] = s_start_dt.strftime('%Y%m%d_%H%M%S')
         new_event['start_times'].append(s_start_dt) #.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
         new_event['stations'] = {}
         new_event['stations'][station_id] = {}
         new_event['obs'] = {}
         new_event['obs'][obs_id] = {}
      event_id = new_event['event_id']
      events[event_id] = new_event 
      print("MAKE NEW EVENT:", event_id )
      return(new_event, events)


   def do_plane_pairs(self, obs_by_min=None, possible=None, not_possible=None):
      if obs_by_min is None:
         obs_by_min = load_json_file(self.min_report)
         possible = load_json_file(self.possible)
         not_possible = load_json_file(self.not_possible)
      pc = 0
      for p in not_possible:
         print("NOT POSSIBLE", pc, p)
         pc += 1

      # load up obs data only for meteors that are 'possible' to solve. 
      pc = 0
      self.ms_obs = {}
      for pr in possible:
         for p in pr:
            print("POSSIBLE", p)
            obs1 = p[4]
            obs2 = p[5]
            self.ms_obs[obs1] = 1
            self.ms_obs[obs2] = 1
            pc += 1

      for obs in self.all_obs:
         st_id = obs['station_id']
         sd_vid = obs['sd_video_file']
         okey = st_id + ":" + sd_vid
         if okey in self.ms_obs:
            # This obs could be an event. Lets save the detail data.
            self.ms_obs[okey] = obs

      # Compute vector projection location for each possilbe to pre-screen
      if cfe(self.plane_pairs_file) == 0:
         self.plane_pairs = {}
      else:
         self.plane_pairs = load_json_file(self.plane_pairs_file)

      colors = self.get_kml_colors()
      cc = 0
      jobs = []
      for pr in possible:
         if cc > len(colors) - 1:
            cc = 0
         color = colors[cc]
         cc += 1
         for p in pr:
            print("POSSIBLE", p)
            obs1 = p[4]
            obs2 = p[5]
            #ms_obs[obs1] = 1
            #ms_obs[obs2] = 1
            pc += 1
            gkey = "".join(sorted([obs1,obs2]))
            rkey = "EP:".join(sorted([obs1,obs2]))
            if gkey not in self.plane_pairs and rkey not in self.plane_pairs:
               print("KEY NOT IN PLANE PAIRS?")
               jobs.append((obs1,obs2,color))

      print("JOBS:", len(jobs))
      self.run_jobs(jobs)
      rkeys = self.r.keys("EP:*" + self.date + "*")
      print("Finished run jobs") 
      for gkey in rkeys:
         rval = json.loads(self.r.get(gkey))
         gkey = gkey.replace("EP:", "")
         self.plane_pairs[gkey] = rval
         if "event_id" not in self.plane_pairs[gkey]:
            t, ob1, ob2 = gkey.split("AMS")
            ob1 = "AMS" + ob1
            ob1 = ob1.replace(":", "_")
            ob2 = "AMS" + ob2
            ob2 = ob1.replace(":", "_")
            if ob1 in self.obs_event_ids:
               event_id = self.obs_event_ids[ob1]
               rval['event_id'] = event_id
               print("EVENT ID FOUND FOR THIS COMBO:", event_id, ob1, ob2 )
               self.r.set(gkey, json.dumps(rval))
               self.plane_pairs[gkey] = rval
            else:
               print("Event id not found.", ob1, ob2)
         print("RED:", rval)

       
      print("Saving plane pairs file")
      save_json_file(self.plane_pairs_file, self.plane_pairs)


   def events_from_plane_pairs(self):
      # Check make events only from the successful plane pair obs
      self.plane_pairs = load_json_file(self.plane_pairs_file)
      new_events = []
      bad_keys = []
      print("Check Make Events")
      for gkey in self.plane_pairs:
         t, obs1,obs2 = gkey.split("AMS")
         obs_key1 = "AMS" + obs1
         obs_key2 = "AMS" + obs2
         if obs_key1 not in self.ms_obs or obs_key2 not in self.ms_obs:
            bad_keys.append(gkey)
            continue
         ob1 = self.ms_obs[obs_key1] 
         ob2 = self.ms_obs[obs_key2] 
         if True:
            obs_time = self.get_obs_datetime(ob1)
            print("EXISTING EVENT NOT FOUND FOR THIS OB.")

            if ob1['station_id'] in self.station_loc:
               ob1['lat'] = self.station_loc[ob1['station_id']][0]
               ob1['lon'] = self.station_loc[ob1['station_id']][1]
               print("CHECK MAKE EVENT:", obs_time, ob1)
               new_events = self.check_make_events(obs_time, ob1, new_events)
            else:
               print("STATION MISSING FROM SELF.station_loc", ob1['station_id'])

            obs_time = self.get_obs_datetime(ob2)
            if ob2['station_id'] in self.station_loc:
               ob2['lat'] = self.station_loc[ob2['station_id']][0]
               ob2['lon'] = self.station_loc[ob2['station_id']][1]
               new_events = self.check_make_events(obs_time, ob2, new_events)
            else:
               print("STATION MISSING FROM SELF.station_loc", ob2['station_id'])

      final_events = []
      for ev in new_events:
         #print("EVENT KEYS:", ev.keys())
         if "start_datetime" in ev:

            str_times = []
            for ttt in ev['start_datetime']:
               if isinstance(ttt,str) is True:
                  time_str = ttt
               else:
                  time_str = ttt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
               str_times.append(time_str)
            ev['start_datetime'] = str_times

            if "event_id" not in ev:
               ev['event_id'] = self.make_event_id(ev)
               print("NEW EVENT ID MADE!", ev['event_id'])


            final_events.append(ev)
      
      for ev in final_events:
         print("INSERT NEW EVENT.")
         print(ev)
         self.insert_new_event(ev)

      save_json_file(self.all_events_file, final_events)
      cf = self.all_events_file.replace("ams2/", "archive.allsky.tv/")
      print("Saved:", self.all_events_file)
      cmd = "cp " + self.all_events_file + " " + cf
      print(cmd)
      os.system(cmd)


      cf = self.plane_pairs_file.replace("ams2/", "archive.allsky.tv/")

      save_json_file(self.plane_pairs_file, self.plane_pairs)
      self.kml_plane_pairs()

      cmd = "cp " + self.plane_pairs_file + " " + cf
      print(cmd)
      os.system(cmd)

      self.all_obs_dict_file = self.all_obs_file.replace("ALL_OBS", "OBS_DICT")
      save_json_file(self.all_obs_dict_file, self.obs_dict)

      print("Saved:", self.plane_pairs_file)
      print("Saved:", self.all_obs_dict_file)

   def run_plane_jobs(self):
      jobs = []
      thread = {}
      if cfe("cores.json") == 1:
         temp = load_json_file("cores.json")
         cores = temp['cores']
      else:
         cores = 1
      cc = 0
      for ev_id in sorted(self.events.keys(),reverse=True) :
         if len(self.events[ev_id]['stations'].keys()) > 1:
            print("ADDING PLANE JOB:", cc, ev_id)
            jobs.append(ev_id)
            cc += 1
         else:
            print("SKIPPING PLANE JOB (SINGLE STATION) :", cc, ev_id)

      jobs_per_proc = int(len(jobs) / cores)
      print("THERE ARE ", cc, " TOTAL EVENTS FOR THIS DAY.")
      print("TOTAL PLANE JOBS:", len(jobs))
      print("JOBS PER PROC:", jobs_per_proc)
      for i in range(0,cores):
         start = i * jobs_per_proc 
         end = start + jobs_per_proc + 1
         print(i, start, end)
         thread[i] = Process(target=self.plane_worker, args=("thread" + str(i), jobs[start:end]))

      for i in range(0,cores):
         thread[i].start()
      for i in range(0,cores):
         thread[i].join()
      print("FINISHING RUNNING PLANE JOBS?") 

      ec = 0
      for ev_id in self.events:
         event = self.events[ev_id]
         if len(event['stations'].keys()) > 1:
            planes = self.r.get("EVP:" + ev_id)
            if planes is not None:
               planes = json.loads(planes)
               self.events[ev_id]['planes'] = planes
               print("EV PLANE IN REDIS:", "EVP:" + ev_id, ec, ev_id, self.events[ev_id].keys(), planes)
            else:
               e_planes_file = self.event_dir + ev_id + "/" + ev_id + "-planes.json"
               if cfe(e_planes_file) == 1:
                  planes = load_json_file(e_planes_file)
                  self.events[ev_id]['planes'] = planes
               print("*** EV PLANE NOT IN REDIS:", ec, ev_id, self.events[ev_id].keys(), planes)
            ec += 1

   def make_events_file_from_coin(self):
      self.station_loc = {}
      self.dyn_events = []
      for data in self.all_stations:
         sid = data[0]
         lat = data[1]
         lon = data[2]
         alt = data[3]
         self.station_loc[sid] = [lat,lon, alt]
      self.all_stations = load_json_file(self.all_stations_file)
      self.obs_dict = load_json_file(self.obs_dict_file)
      dyn_events = []
      coin_events = load_json_file(self.coin_events_file)
      for ev_id in coin_events:
         event_data = coin_events[ev_id]
         sol_file = self.event_dir + ev_id + "/" + ev_id + "-event.json"
         fail_file = self.event_dir + ev_id + "/" + ev_id + "-fail.json"
         if cfe(sol_file) == 1:
            solution = load_json_file(sol_file)
            if "obs" in solution:
               del solution['obs']
            if "kml" in solution:
               del solution['kml']
            solve_status = "SUCCESS"
         elif cfe(fail_file) == 1:
            solve_status = "WMPL FAILED"
            solution = None
         else:
            total_planes = len(event_data['planes'].keys())
            failed_planes = 0
            for kk in event_data['planes'].keys():
               stat = event_data['planes'][kk][0]
               print("PLANE STATUS:", kk, stat)
               if "invalid" in stat or "FAIL" in stat:
                  failed_planes += 1
            if failed_planes == total_planes:
               solve_status = "INVALID PLANES"
            else:
               solve_status = "UNSOLVED"
            solution = None

         event = coin_events[ev_id]
         dy_event = self.coin_event_to_dyn_event(event)
         dy_event['solve_status'] = solve_status
         if solution is not None:

            dy_event['solution'] = solution
            ttt = []
            for ddd in dy_event['mfd_dur']:
               if ddd is not None:
                  ttt.append(ddd)
            dy_event['solution']['duration'] = float(np.mean(ttt))
         self.dyn_events.append(dy_event)

      save_json_file(self.all_events_file, self.dyn_events)
      print("SAVED", self.all_events_file)

   def load_dyna_events(self):
      # AFTER THE EVENT FILE IS MADE
      # DELETE ANY EVENTS THAT ARE NOT "REAL"
      # THEN LOAD THESE IN
      cur_events = search_events(self.dynamodb, self.date, "" ) 
      print(len(cur_events))
      cur_ev = {}
      good_ev = {}
      for temp in cur_events:
         cur_ev[temp['event_id']] = {}

      events = load_json_file(self.all_events_file)
      for temp in events:
         good_ev[temp['event_id']] = {}

      for evi in cur_ev.keys():
         if evi not in good_ev:
            print("OLD EVENT ID NEEDS TO BE DELETED!", evi)
            delete_event(self.dynamodb, self.date, evi)
         else:
            print("OLD EVENT IS STILL GOOD.")

      for ev in events:
         new_sdt = []
         for i in range(0, len(ev['start_datetime'])):
            sd = ev['start_datetime'][i]
            if sd is None:
               sd = ev['files'][i]
               start_dt = self.starttime_from_file(sd)
               start_dt = start_dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
               new_sdt.append(start_dt)
            else:
               new_sdt.append(sd)
         ev['start_datetime'] = new_sdt
         print(ev['start_datetime']) 
         #print("INSERT NEW EV:", ev)
         
         self.insert_new_event(ev)

   def sync_event_day(self):
      coin_events = load_json_file(self.coin_events_file)
      for ev_id in coin_events:
         pickle_file = self.event_dir + ev_id + "/" + ev_id + "_trajectory.pickle"
         planes_file = self.event_dir + ev_id + "/" + ev_id + "-planes.kml"
         good_obs_file = self.event_dir + ev_id + "/" + ev_id + "_GOOD_OBS.json"
         event_file = self.event_dir + ev_id + "/" + ev_id + "-event.json"
         event_kml = self.event_dir + ev_id + "/" + ev_id + "-event.kml"
         event_index = self.event_dir + ev_id + "/" + "index.html"

         c_pickle_file = pickle_file.replace("ams2", "archive.allsky.tv")
         c_planes_file = planes_file.replace("ams2", "archive.allsky.tv")
         c_good_obs_file = good_obs_file.replace("ams2", "archive.allsky.tv")
         c_event_file = event_file.replace("ams2", "archive.allsky.tv")
         c_event_kml = event_kml.replace("ams2", "archive.allsky.tv")
         c_event_index = event_index.replace("ams2", "archive.allsky.tv")

         if ev_id not in self.event_dict:
            print(ev_id, "not in event_dict")
            continue
         if "solve_status" not in self.event_dict[ev_id]:
            ss = "UNSOLVED" 
         else:
            ss = self.event_dict[ev_id]['solve_status'] 
         print(ss, self.event_dir + ev_id + "/")
         if True:
            if cfe(self.cloud_event_dir + ev_id, 1) == 0:
               os.makedirs(self.cloud_event_dir + ev_id)
            if cfe(planes_file) == 1:
               if cfe(c_planes_file) == 0:
                  cp = "cp " + planes_file + " " + self.cloud_event_dir + ev_id + "/"
                  print(cp)
                  os.system(cp)

            if cfe(good_obs_file) == 1:
               if cfe(c_good_obs_file) == 0:
                  cp = "cp " + good_obs_file + " " + self.cloud_event_dir + ev_id + "/"
                  print(cp)
                  os.system(cp)


            if cfe(pickle_file) == 1:
               if cfe(c_pickle_file) == 0:
                  cp = "cp " + pickle_file + " " + self.cloud_event_dir + ev_id + "/"
                  print(cp)
                  os.system(cp)
            if cfe(event_file) == 1:
               if cfe(c_event_file) == 0:
                  cp = "cp " + event_file + " " + self.cloud_event_dir + ev_id + "/"
                  print(cp)
                  os.system(cp)
            if cfe(event_kml) == 1:
               if cfe(c_event_kml) == 0:
                  cp = "cp " + event_kml + " " + self.cloud_event_dir + ev_id + "/"
                  print(cp)
                  os.system(cp)
            if cfe(event_index) == 1:
               if cfe(c_event_index) == 0:
                  cp = "cp " + event_index + " " + self.cloud_event_dir + ev_id + "/"
                  print(cp)
                  os.system(cp)

            if cfe(self.cloud_event_dir + ev_id + "/" + ev_id, 1) == 1:
               print("rm " + self.cloud_event_dir + ev_id + "/" + ev_id)
               os.system("rm -rf " + self.cloud_event_dir + ev_id + "/" + ev_id)



   def sync_event_trash(self):
      coin_events = load_json_file(self.coin_events_file)
      cflog = self.event_dir + "cloud_files.txt"
      l_log = self.event_dir + "local_files.txt"
      print("CFLOG:", cflog)
      if cfe(cflog) == 0:
         print("find " + self.cloud_event_dir + "* >" + cflog)
         os.system("find " + self.cloud_event_dir + "* >" + cflog)
      else:
         sz, td = get_file_info(cflog)
         if td > 300:
            os.system("find " + self.event_dir + "*" > l_log)

      fp = open(cflog)
      cloud_files = {}
      local_files = {}
      for line in fp:
         line = line.replace("archive.allsky.tv", "ams2")
         cloud_files[line] = 1
      fp = open(l_log)
      cloud_files = {}
      for line in fp:
         line = line.replace("archive.allsky.tv", "ams2")
         local_files[line] = 1

      for lf in local_files:
         if lf in cloud_files:
            print ("EXISTS IN CLOUD:", lf)
         else:
            print ("MISSING IN CLOUD:", lf)


   def sync_event_files(self, ev_id):

      local_files = glob.glob(self.event_dir + ev_id + "/*")
      cloud_dir = self.cloud_event_dir + ev_id + "/"
      if cfe(cloud_dir, 1) == 0:
         os.makedirs(cloud_dir)
      for lf in local_files:
         lfn = lf.split("/")[-1]
         if cfe(cloud_dir + lfn) == 0:
            cmd = "cp " + lf + " " + cloud_dir
            print(cmd)
            os.system(cmd)


   def sync_event_dir(self):
      coin_events = load_json_file(self.coin_events_file)

      # fix bug dirs
      if False:
         for ev_id in coin_events:
            mistake_dir = self.cloud_event_dir + ev_id + "/" + ev_id + "/"
            if cfe(mistake_dir, 1) == 1:
               print("MISTAKE DIR EXISTS", mistake_dir)
               cmd = "mv " + mistake_dir + "*" + " " + self.cloud_event_dir + ev_id + "/"
               print(cmd)
               os.system(cmd)
               cmd = "rmdir " + mistake_dir 
               print(cmd)
               os.system(cmd)

      cmd = "find " + self.cloud_event_dir + " > " + self.event_dir + "cloud_files.txt"
      print(cmd)
      os.system(cmd)

      cmd = "find " + self.event_dir + " > " + self.event_dir + "local_files.txt"
      print(cmd)
      os.system(cmd)

      lf = {}
      cf = {}
      if cfe(self.event_dir + "cloud_fiels.txt") == 1:
         fp = open(self.event_dir + "cloud_files.txt", "r")
         for line in fp:
            line = line.replace("\n", "")
            cf[line] = {}
         fp.close()

      if cfe(self.event_dir + "cloud_fiels.txt") == 1:
         fp = open(self.event_dir + "local_files.txt", "r")
         for line in fp:
            line = line.replace("\n", "")
            lf[line] = {}
         fp.close()

      # check local files not on the cloud
      lc = 0
      for lfile in lf:
         cfile = lfile.replace("/ams2", "/archive.allsky.tv")
         if cfile not in cf:
            print(lc, "NEED TO PUSH:", lfile, cfile)
            lc+=1 

      #for cfile in cf:
      #exit()

      event_dir_files = glob.glob(self.event_dir + "*")
      cloud_event_dir_files = glob.glob(self.cloud_event_dir + "*")
      event_dirs = []
      cloud_dirs = []
      local_dict = {}
      cloud_dict = {}
      coin_dict = {}
      for ttt in event_dir_files:
         fn = ttt.split("/")[-1]
         if cfe(ttt, 1) == 1:
            local_dict[fn] = 1
            event_dirs.append(ttt) 
      for ttt in cloud_event_dir_files:
         fn = ttt.split("/")[-1]
         if cfe(ttt, 1) == 1:
            cloud_dict[fn] = 1
            cloud_dirs.append(ttt) 
      for ev_id in coin_events.keys():
         coin_dict[ev_id] = coin_events[ev_id]


      coin_stats = []
      local_stats = []
      cloud_stats = []
      print("COIN EVENTS:", len(coin_events.keys()))
      print("LOCAL EVENT DIRS:", len(event_dirs))
      print("REMOTE EVENT DIRS:", len(cloud_dirs))
      for ev_id in coin_dict:
         if ev_id not in local_dict:
            status_local = 0
         else:
            status_local = 1 
         if ev_id not in cloud_dict:
            status_cloud = 0
         else:
            status_cloud = 1 

         print("COIN DIRS STATUS")
         print(ev_id, status_local, status_cloud)
         coin_stats.append((ev_id, status_local, status_cloud))
      print("LOCAL DIR STATUS (0s are bad events / no longer valid and should be deleted.")
      for ld in local_dict:
         if ld in coin_dict:
            lstatus = 1
         else:
            lstatus = 0
            print("LOCAL STATUS", ld, lstatus)
         local_stats.append((ld, lstatus))

      print("CLOUD DIR STATUS (0s are bad events / no longer valid and should be deleted.")
      for ld in cloud_dict:
         if ld in coin_dict:
            lstatus = 1
         else:
            lstatus = 0
         print("CLOUD STATUS", ld, lstatus)
         cloud_stats.append((ld, lstatus))
          
      # for each local if the dir is not in the coin_dict remove it
      # for each cloud if the dir is not in the coin_dict remove it
      cloud_purge=[]
      for data in local_stats:
         if data[1] == 0:
            print("REMOVE LOCAL DIR:", data[0])
            cmd = "rm -rf " + self.event_dir + data[0]
            print(cmd)
            os.system(cmd)
      for data in cloud_stats:
         if data[1] == 0:
            print("REMOVE CLOUD DIR:", data[0])
            cmd = "rm -rf " + self.cloud_event_dir + data[0]
            print(cmd)
            cloud_purge.append(cmd)
      for data in coin_stats:
         if data[1] == 0:
            print("EVENT MISSING LOCAL DIR:", data[0])
            #os.system(cmd)
         if data[2] == 0:
            print("EVENT MISSING CLOUD DIR:", data[0])
            cmd = "cp -r " + self.event_dir + data[0] + " " + self.cloud_event_dir
            #print(cmd)
            #os.system(cmd)
            self.sync_event_files(data[0])
      save_json_file(self.cloud_event_dir + "cloud_purge.json", cloud_purge )
      print("saved" + self.cloud_event_dir + "cloud_purge.json", cloud_purge)
   

   def coin_event_to_dyn_event(self, event):
      print(event)
      stations = []
      files = []
      start_datetime = []
      lats = []
      lons = []
      alts = []
      mfd_dur = []
      event_day = ""
      event_id = ""
      for obs_id in event['obs']:
         if obs_id not in self.obs_dict:
            continue
         if "meteor_frame_data" in self.obs_dict[obs_id]:
            ob_mfd = self.obs_dict[obs_id]['meteor_frame_data']
         else:
            ob_mfd = None
         if ob_mfd is not None:
            if len(ob_mfd) > 0:
               dur_mfd = len(ob_mfd) / 25
               first_mfd_time = ob_mfd[0][0]
            else:
               dur_mfd = None
               first_mfd_time = None
         else:
            print("MISSING MFD!", obs_id)
            dur_mfd = None
            first_mfd_time = None
         st = obs_id.split("_")[0]
         vid = obs_id.replace(st + "_","")
         if self.station_loc[st] is None:
            print("STATION", st, "station_loc is NONE")
         else:
            stations.append(st)
            files.append(vid)
            lats.append(self.station_loc[st][0])
            lons.append(self.station_loc[st][1])
            alts.append(self.station_loc[st][2])
            mfd_dur.append(dur_mfd)
            start_datetime.append(first_mfd_time)
      print(stations)
      print(files)
      print(start_datetime)
      print(lats)
      print(lons)
      print(alts)
      print(dur_mfd)
      dy_event = event
      dy_event['stations'] = stations
      dy_event['files'] = files
      dy_event['start_datetime'] = start_datetime
      dy_event['lats'] = lats
      dy_event['lons'] = lons
      dy_event['alts'] = alts
      dy_event['mfd_dur'] = mfd_dur
      return(dy_event)

   def plane_worker(self, thread_name, jobs):
      c = 0
      for ev_id in jobs:

         print("THREAD:", thread_name, ev_id)
         self.events[ev_id] = self.do_planes_for_event(self.events[ev_id])
         rkey = "EVP:" + ev_id
         self.r.set(rkey, json.dumps(self.events[ev_id]['planes']))
         e_planes_file = self.event_dir + ev_id + "/" + ev_id + "-planes.json"
         save_json_file(e_planes_file, self.events[ev_id]['planes'])
         print("THREAD SET REDIS:", c, rkey)
         c += 1
         #print(self.events[ev_id]['planes'])
              

   def run_solve_jobs(self ):
      thread = {}
      if cfe("cores.json") == 1:
         temp = load_json_file("cores.json")
         cores = temp['cores']
      else:
         cores = 1
      self.solve_jobs = load_json_file(self.DATA_DIR + "EVENTS/" + self.year + "/" + self.month + "/" + self.day + "/" + self.date + "_SOLVE_JOBS.json")
      print(type(self.solve_jobs))
      jobs_per_proc = int(len(self.solve_jobs) / cores)
       
      print("TOTAL JOBS:", len(self.solve_jobs))
      print("JOBS PER PROC:", jobs_per_proc)
      for i in range(0,cores):
         start = i * jobs_per_proc 
         end = start + jobs_per_proc 
         print(i, start, end)
         thread[i] = Process(target=self.solve_worker, args=("thread" + str(i), self.solve_jobs[start:end]))

      for i in range(0,cores):
         thread[i].start()
      for i in range(0,cores):
         thread[i].join()

      #for job in self.solve_jobs:
      #   print(job[0], job[1])

   def solve_worker(self ,thread, jobs):
      for job in jobs:
         print(thread, job[0], job[1])
         event_id = job[1]
         good_obs = job[2]
         WMPL_solve(event_id, good_obs, 1)
         #cmd = "rsync -auv " + self.event_dir + event_id + "/* " +  self.cloud_event_dir + event_id 
         #print(cmd)
         #os.system(cmd)

         fp = open(self.event_dir + "rsync.jobs", "a")
         fp.write ("rsync -auv " + self.event_dir + event_id + "/* " + self.cloud_event_dir + event_id + "\n")
         fp.close()

   def run_jobs_old(self, jobs):
      # Multi-process/thread IP job runner. 
      workers = 30
      thread = {}
      if len(jobs) > workers:
         wp = int(len(jobs)/workers)
      else:
         wp = 1
      print("WORKERS:", workers)
      print("WORK PROCESSES:", wp)
      print("JOBS :", len(jobs))
      if len(jobs) > 0:
         for i in range(0,wp):
            start = i * wp
            end = start + wp
            print("Make thread with items :", i, start, end)
            thread[i] = Process(target=self.worker, args=("thread" + str(i), jobs[start:end]))

         for i in range(0,wp):
            thread[i].start()
            print(i, wp)
            time.sleep(1)
         for i in range(0,wp):
            thread[i].join()
            print(i, wp)
            time.sleep(1)

   
   def worker(self, thread_name, jobs):
      results = {}
      for job in jobs:
         obs1, obs2,color = job
         jkey = "".join([obs1,obs2])
         rkey = "EP:" + jkey
         rval = self.r.get(rkey)
         if rval is None:
         #if True:
            if True:

           # try:
               result = self.plane_test(obs1, obs2)

               # TRY USING JIT?
               obs1_key = obs1['obs_id']
               obs2_key = obs2['obs_id']
               st1 = obs1['station_id']
               st2 = obs2['station_id']
               sdv1 = obs1['sd_video_file']
               sdv2 = obs2['sd_video_file']
               lat1 = self.station_loc[st1][0]
               lon1 = self.station_loc[st1][1]
               lat2 = self.station_loc[st2][0]
               lon2 = self.station_loc[st2][1]
               mfd1 = self.obs_dict[obs1_key]['meteor_frame_data']
               mfd2 = self.obs_dict[obs2_key]['meteor_frame_data']

               #result = self.plane_test_jit(obs1_key, obs2_key, sdv1, sdv2, lat1,lon1,lat2,lon2,mfd1,mfd2)
               #print("PLANE TEST RESULT:", result)

               if result is not None:
                  status, line1, line2 = result
                  slat,slon,salt,elat,elon,ealt = line1
                  track_distance = self.track_dist(slat,slon,salt,elat,elon,ealt)
                  if obs1 in self.obs_event_ids:
                     self.plane_pairs[jkey] = self.obs_event_ids[obs1] 

                  self.plane_pairs[jkey] = {}
                  self.plane_pairs[jkey]['status'] = status
                  self.plane_pairs[jkey]['obs1'] = obs1 
                  self.plane_pairs[jkey]['obs2'] = obs2
                  self.plane_pairs[jkey]['2D_track_dist'] = track_distance
                  self.plane_pairs[jkey]['line1'] = line1
                  self.plane_pairs[jkey]['line2'] = line2
                  self.plane_pairs[jkey]['color'] = color
                  self.plane_pairs[jkey]['combo_key'] = jkey
                  result = self.plane_pairs[jkey]
                  results[jkey] = result
               else:
                  self.plane_pairs[jkey] = {}
                  self.plane_pairs[jkey]['obs1'] = obs1 
                  self.plane_pairs[jkey]['obs2'] = obs2
                  self.plane_pairs[jkey]['combo_key'] = jkey
                  self.plane_pairs[jkey]['color'] = color
                  self.plane_pairs[jkey]['status'] = "plane_failed" 
                  if obs1 in self.obs_event_ids:
                     self.plane_pairs[jkey] = self.obs_event_ids[obs1] 
                  result = self.plane_pairs[jkey]
                  results[jkey] = result

           # except:
           #    results[jkey] = None
            print(jkey, results[jkey])
            # call_function
            rval = json.dumps(results[jkey])
            self.r.set(rkey, rval)
            print("SETTING RVAL:", rkey, rval)
         else:
            self.plane_pairs[jkey] = json.loads(rval) 
            print("Plane already in redis!", jkey, rval)

   def make_event_id(self,event):
      ev_str = str(min(event['start_datetime']))
      if "." in ev_str:
         ev_dt = datetime.datetime.strptime(ev_str, "%Y-%m-%d %H:%M:%S.%f")
      else:
         ev_dt = datetime.datetime.strptime(ev_str, "%Y-%m-%d %H:%M:%S")
      event_id = ev_dt.strftime('%Y%m%d_%H%M%S')
      event_day = ev_dt.strftime('%Y_%m_%d')
      event['event_id'] = event_id
      return(event_id)

   def get_kml_colors(self):
      colors = []
      for key in kml_colors:
         colors.append(kml_colors[key])
      return(colors)

   def find_point_from_az_dist(self, lat,lon,az,dist):
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

   def kml_plane_pairs(self):
      self.all_events = load_json_file(self.all_events_file)
      self.plane_pairs = load_json_file(self.plane_pairs_file)

      kml = simplekml.Kml()
      fol_day = kml.newfolder(name=self.date + " Planes")
      fol_sol = fol_day.newfolder(name='Solved Planes')

      self.obs_event_ids = {}
      print(len(self.all_events), " total events.")
      for ev in self.all_events:
         ev_id = ev['event_id']
         for i in range(0, len(ev['stations'])):
            st = ev['stations'][i]
            vid = ev['files'][i]
            oid = st + "_" + vid
            self.obs_event_ids[oid] = ev_id
      cc = 0
      self.obs_event_ids_file = self.all_events_file.replace("ALL_EVENTS", "ALL_OBS_IDS")
      save_json_file(self.obs_event_ids_file, self.obs_event_ids)
      print("PLANE PAIRS:", len(self.plane_pairs))

      for combo_key in self.plane_pairs:
         o_combo_key = combo_key.replace("EP:", "")
         print("COMBO KEY IS:", combo_key)
         el = o_combo_key.split("AMS")
         print("EL:", el)
         ob1 = el[1]
         ob2 = el[2]
         ob1 = "AMS" + ob1.replace(":", "_")
         ob2 = "AMS" + ob2.replace(":", "_")
         if ob1 in self.obs_event_ids:
            ev_id = self.obs_event_ids[ob1]
         else:
            ev_id = "NO_EVENT_ID"
            print("obs not in obs_id file!", ob1)
         if "status" not in self.plane_pairs[combo_key]:
            print("combo key NOT in plane_pairs file???")
            continue
         print(ev_id, combo_key, self.plane_pairs[combo_key])
         if self.plane_pairs[combo_key]['status'] == "plane_solved":
            line1 = self.plane_pairs[combo_key]['line1']
            line2 = self.plane_pairs[combo_key]['line2']
            color = self.plane_pairs[combo_key]['color']
            slat,slon,salt,elat,elon,ealt = line1

            line = fol_sol.newlinestring(name=combo_key, description="", coords=[(slon,slat,salt),(elon,elat,ealt)])
            line.altitudemode = simplekml.AltitudeMode.relativetoground
            line.linestyle.color = color
            line.linestyle.colormode = "normal" 
            line.linestyle.width = "3"
            slat,slon,salt,elat,elon,ealt = line2
            line = fol_sol.newlinestring(name=combo_key, description="", coords=[(slon,slat,salt),(elon,elat,ealt)])
            line.altitudemode = simplekml.AltitudeMode.relativetoground
            line.linestyle.color = color 
            line.linestyle.colormode = "normal"
            line.linestyle.width = "3"
         else:
            print("BAD PP STATUS:", self.plane_pairs[combo_key]['status'])
      self.plane_kml_file = self.plane_pairs_file.replace(".json",".kml")
      kml.save(self.plane_kml_file)
      clf = self.plane_kml_file.replace("ams2/", "archive.allsky.tv/")
      print(self.plane_kml_file)

      os.system("cp " + self.plane_kml_file + " " + clf)




   def track_dist(self, slat,slon,salt,elat,elon,ealt):
      from geopy.distance import distance
      from geopy.point import Point
      a = Point(slat, slon, 0)
      b = Point(elat, elon, 0)
      dist = distance(a, b).km
      return(dist)

   #@jit(nopython=True)
   def plane_test_jit(self, obs1_key, obs2_key, sdv1, sdv2, lat1,lon1,lat2,lon2,mfd1,mfd2):
      if len(mfd1) > 1:
         az1s = mfd1[0][9]
         el1s = mfd1[0][10]
         az1e = mfd1[-1][9]
         el1e = mfd1[-1][10]
      else:
         return("obs1 missing_mfd_data", [0,0,0,0,0,0], [0,0,0,0,0,0])
         return(None)

      if len(mfd2) > 1:
         az2s = mfd2[0][9]
         el2s = mfd2[0][10]
         az2e = mfd2[-1][9]
         el2e = mfd2[-1][10]
      else:
         return("obs2 missing_mfd_data", [0,0,0,0,0,0], [0,0,0,0,0,0])

      if (az1s == 0 and el1s == 0) or (az2s == 0 or el2s == 0):
         return("missing_mfd_data", [0,0,0,0,0,0], [0,0,0,0,0,0])

      #station_dist = dist_between_two_points(s_lat, s_lon, lat, lon)
      alt = 0
      (sveX,sveY,sveZ,s1vlat,s1vlon,s1valt) = self.find_vector_point(lat1,lon1,alt,az1s,el1s,factor=1000000)
      values = {}
      values['lat1'] = lat1 
      values['lon1'] = lon1 

      values['saz1'] = az1s
      values['eaz1'] = az1e
      values['sel1'] = el1s 
      values['eel1'] = el1e

      values['lat2'] = lat2 
      values['lon2'] = lon2

      values['saz2'] = az2s
      values['eaz2'] = az2e
      values['sel2'] = el2s
      values['eel2'] = el2e

      try:
         result = man_solve(values)
      except:
         result = None
      if result is None:
         print("PLANE TEST FAILED FOR PAIR!", st1, st2)
         return("plane_failed", [0,0,0,0,0,0], [0,0,0,0,0,0])
      else:
         line1, line2 = result

         slat,slon,salt,elat,elon,ealt = line1
         track_distance = self.track_dist(slat,slon,salt,elat,elon,ealt)


         if 50000 <= line1[2] <= 150000 and 50000 <= line2[2] <= 150000 and track_distance <500:
            return("plane_solved", line1, line2)
         else:
            return("plane_invalid", line1, line2)

   def plane_test_fast(self, obs1, obs2):
      from intersecting_planes import intersecting_planes
      obs1_key = obs1['obs_id']
      obs2_key = obs2['obs_id']
      st1 = obs1['station_id']
      st2 = obs2['station_id']
      sdv1 = obs1['sd_video_file']
      sdv2 = obs2['sd_video_file']
      lat1 = self.station_loc[st1][0]
      lon1 = self.station_loc[st1][1]
      lat2 = self.station_loc[st2][0]
      lon2 = self.station_loc[st2][1]
      mfd1 = self.obs_dict[obs1_key]['meteor_frame_data']
      mfd2 = self.obs_dict[obs2_key]['meteor_frame_data']
      if len(mfd1) > 1:
         az1s = mfd1[0][9]
         el1s = mfd1[0][10]
         az1e = mfd1[-1][9]
         el1e = mfd1[-1][10]
      else:
         return("obs1 missing_mfd_data", [0,0,0,0,0,0], [0,0,0,0,0,0])
         return(None)

      if len(mfd2) > 1:
         az2s = mfd2[0][9]
         el2s = mfd2[0][10]
         az2e = mfd2[-1][9]
         el2e = mfd2[-1][10]
      else:
         return("obs2 missing_mfd_data", [0,0,0,0,0,0], [0,0,0,0,0,0])

      if (az1s == 0 and el1s == 0) or (az2s == 0 or el2s == 0):
         return("missing_mfd_data", [0,0,0,0,0,0], [0,0,0,0,0,0])
      ob1 = (lat1, lon1, alt1, az1s, el1s, az1e,el1e) 
      ob1 = (lat2, lon2, alt2, az2s, el2s, az2e,el2e) 
      ip_line1 = intersecting_planes(ob1,ob2)
      ip_line2 = intersecting_planes(ob2,ob1)

      return("plane_solved", line1, line2)

   def plane_test(self, obs1, obs2):
      #st1, sdv1 = obs1.split(":")
      #st2, sdv2 = obs2.split(":")
      obs1_key = obs1['obs_id']
      obs2_key = obs2['obs_id']
      st1 = obs1['station_id']
      st2 = obs2['station_id']
      sdv1 = obs1['sd_video_file']
      sdv2 = obs2['sd_video_file']
      lat1 = self.station_loc[st1][0]
      lon1 = self.station_loc[st1][1]
      lat2 = self.station_loc[st2][0]
      lon2 = self.station_loc[st2][1]
      mfd1 = self.obs_dict[obs1_key]['meteor_frame_data']
      mfd2 = self.obs_dict[obs2_key]['meteor_frame_data']
      if len(mfd1) > 1:
         az1s = mfd1[0][9]
         el1s = mfd1[0][10]
         az1e = mfd1[-1][9]
         el1e = mfd1[-1][10]
      else:
         return("obs1 missing_mfd_data", [0,0,0,0,0,0], [0,0,0,0,0,0])
         return(None)

      if len(mfd2) > 1:
         az2s = mfd2[0][9]
         el2s = mfd2[0][10]
         az2e = mfd2[-1][9]
         el2e = mfd2[-1][10]
      else:
         return("obs2 missing_mfd_data", [0,0,0,0,0,0], [0,0,0,0,0,0])

      if (az1s == 0 and el1s == 0) or (az2s == 0 or el2s == 0):
         return("missing_mfd_data", [0,0,0,0,0,0], [0,0,0,0,0,0])

      #station_dist = dist_between_two_points(s_lat, s_lon, lat, lon)
      alt = 0
      (sveX,sveY,sveZ,s1vlat,s1vlon,s1valt) = self.find_vector_point(lat1,lon1,alt,az1s,el1s,factor=1000000)
      values = {}
      values['lat1'] = lat1 
      values['lon1'] = lon1 

      values['saz1'] = az1s
      values['eaz1'] = az1e
      values['sel1'] = el1s 
      values['eel1'] = el1e

      values['lat2'] = lat2 
      values['lon2'] = lon2

      values['saz2'] = az2s
      values['eaz2'] = az2e
      values['sel2'] = el2s
      values['eel2'] = el2e

      try:
         result = man_solve(values)
      except:
         result = None
      if result is None:
         print("PLANE TEST FAILED FOR PAIR!", st1, st2)
         return("plane_failed", [0,0,0,0,0,0], [0,0,0,0,0,0])
      else:
         line1, line2 = result
         print("L1", line1)
         print("L2", line2)

         slat,slon,salt,elat,elon,ealt = line1
         track_distance = self.track_dist(slat,slon,salt,elat,elon,ealt)


         if 50000 <= line1[2] <= 150000 and 50000 <= line2[2] <= 150000 and track_distance <500:
            return("plane_solved", line1, line2)
         else:
            return("plane_invalid", line1, line2)

   def obs_to_events(self, min_data):
      combos = {}
      pos_events = []
      non_events = []
      for ob in min_data:
         st, sd = ob.split(":")
         start_dt = self.starttime_from_file(sd)
         lat = self.station_loc[st][0]
         lon = self.station_loc[st][1]
         for sob in min_data:
            
            s_st, s_sd = sob.split(":")
            s_start_dt = self.starttime_from_file(s_sd)
            obs1 = st + ":" + sd
            obs2 = s_st + ":" + s_sd
            c_key = "".join(sorted([obs1, obs2]))
            if st != s_st and c_key not in combos:
               combos[c_key] = {}
               s_lat = self.station_loc[s_st][0]
               s_lon = self.station_loc[s_st][1]
               station_dist = dist_between_two_points(s_lat, s_lon, lat, lon)
               time_diff = (start_dt - s_start_dt).total_seconds()

               status = []
               if station_dist > 300:
                  status.append("BAD DIST " + str(int(station_dist)))
                  non_events.append((c_key, station_dist , time_diff, status, obs1, obs2))
               elif abs(time_diff) > 5:
                  status.append("BAD TIME " + str(time_diff))
                  non_events.append((c_key, station_dist , time_diff, status, obs1, obs2))
               else:
                  status.append("GOOD DIST & TIME " + str(station_dist) + " " + str(time_diff))
                  pos_events.append((c_key, station_dist, time_diff, status, obs1, obs2))

      return(pos_events, non_events)

   def station_count(self, obs):
      sc = {}
      for ob in obs:
         st, vd = ob.split(":")
         sc[st] = 1
      return(len(sc.keys()))




   def find_vector_point(self, lat,lon,alt,az,el,factor=1000000):

      sveX, sveY, sveZ = pm.aer2ecef(az,el,200000, lat, lon, alt, wgs84)
      svlat, svlon, svalt = pm.ecef2geodetic(float(sveX), float(sveY), float(sveZ), wgs84)
      return(sveX,sveY,sveZ,svlat,svlon,svalt)

   def aws_stats(self):
      obs_files = glob.glob(self.DATA_DIR + "EVENTS/OBS/DAYS/*.json")
      stats_by_day = {}
      for obf in sorted(obs_files, reverse=True):
         day = obf.split("/")[-1].replace(".json", "")
         if day not in stats_by_day:
            stats_by_day[day] = {}
            stats_by_day[day]['station_stats'] = {}
         obd = load_json_file(obf)
         stats_by_day[day]['total_meteor_obs'] = len(obd)
         for row in obd:
            st = int(row[0])
            if st not in stats_by_day[day]['station_stats']:
               stats_by_day[day]['station_stats'][st] = {}
               stats_by_day[day]['station_stats'][st]['count'] = 0
            else:
               stats_by_day[day]['station_stats'][st]['count'] += 1

          
         print(day, len(stats_by_day[day]['station_stats'].keys()), len(obd))
      save_json_file(self.DATA_DIR + "EVENTS/ALL_STATS_BY_DAY.json", stats_by_day)
      print(self.DATA_DIR + "EVENTS/ALL_STATS_BY_DAY.json" )
      self.make_stats_html()

   def make_stats_html(self):
      stats_by_day = load_json_file(self.DATA_DIR + "EVENTS/ALL_STATS_BY_DAY.json")
      all_stations = {}
      for day in sorted(stats_by_day.keys(), reverse=True):
         for station in sorted(stats_by_day[day]['station_stats'].keys(), reverse=True):
            station = int(station)
            all_stations[station] = 1
      header = "Date"
      html = ""
      for station in sorted(all_stations.keys()):
         header += "\t" + """<a href=meteors.html?station_id=AMS""" + str(station) + ">" + str(station) + """</a>"""
      header += "\t" + "Total"
      html_header = "<table id='obs_stats' border=1><thead><tr><th>" + header.replace("\t", "</th><th>") + "</th></tr></thead><tbody>"
      print(html_header)
      html += html_header
      station_totals = {}
      total_total = 0
      for day in sorted(stats_by_day.keys(), reverse=True):
         row = day
         day_total = 0
         for station in sorted(all_stations.keys()):
            station = str(station)
            if station not in station_totals:
               station_totals[station] = 0

            if station in stats_by_day[day]['station_stats']:
               count = stats_by_day[day]['station_stats'][station]['count']
            else:
               count = 0
            station_totals[station] += count
            day_total += count
            total_total += count
            row += "\t" + str(count) 
         row += "\t" + str(day_total)
         html_row = "<tr><td>" + row.replace("\t", "</td><td>") + "</td></tr>"
         print(html_row)
         html += html_row
      row = "Total"
      for station in sorted(all_stations.keys()):
         station = str(station)
         row += "\t" + str(station_totals[station])
      row += "\t" + str(total_total)
      html_row = "<tr><td>" + row.replace("\t", "</td><td>") + "</td></tr>"
      print(html_row)
      html += html_row
      html += "</tbody></table>"

      fp = open(self.DATA_DIR + "EVENTS/METEOR_OBS_STATS.html", "w")
      fp.write(html)
      fp.close()
      cmd = "cp /mnt/ams2/EVENTS/METEOR_OBS_STATS.html /mnt/archive.allsky.tv/EVENTS/METEOR_OBS_STATS.html"
      print(cmd)
      os.system(cmd) 

      #print(row)

   def all_stations_kml(self):
      rkeys = self.r.keys("ST:*")
      all_stations = []
      for rkey in rkeys:
         rval = json.loads(self.r.get(rkey))
         all_stations.append(rval)

      kml = simplekml.Kml()
      self.all_stations_file = self.DATA_DIR + "EVENTS/ALL_STATIONS3.kml"
      for data in all_stations:
        if "lat" in data:
           lat = float(data['lat'])
        else:
           lat = 0
        if "lon" in data:
           lon = float(data['lon'])
        else:
           lon = 0
        pnt = kml.newpoint(name=data['station_id'], coords=[(round(lon,1),round(lat,1))])
      print("SAVE:", self.all_stations_file)
      kml.save(self.all_stations_file)
      self.cloud_stations_kml = self.all_stations_file.replace("/ams2/", "/archive.allsky.tv/")
      cmd = "cp " + self.all_stations_file + " " + self.cloud_stations_kml
      print(cmd)
      os.system(cmd)

   def del_bad_obs_from_events(self,date):
      sdate = date.replace("_", "")
      ekeys = self.r.keys("E:" + sdate + "*")
      all_obs = {}
      for ekey in ekeys:
         print(ekey)
         rval = json.loads(self.r.get(ekey))
         print(rval['stations'])
         print(rval['files'])



   def station_kml_for_day(self,date):
      kml = simplekml.Kml()
      self.date = date
      self.year, self.month, self.day = date.split("_")
      self.all_stations_file = self.DATA_DIR + "EVENTS/" + self.year + "/" + self.month + "/" + self.day + "/" + self.date + "_ALL_STATIONS.json"
      self.all_stations_kml = self.all_stations_file.replace(".json", ".kml")
      self.cloud_stations_kml = self.all_stations_kml.replace("ams2", "archive.allsky.tv")
      st_data = load_json_file(self.all_stations_file)
      for row in st_data:
         station_id = row[0]
         lat = row[1]
         lon = row[2]
         location = row[3]
         cluster = row[4]
         pnt = kml.newpoint(name=station_id, coords=[(round(lon,1),round(lat,1))])

      kml.save(self.all_stations_kml)
      cmd = "cp " + self.all_stations_kml + " " + self.cloud_stations_kml
      print(cmd)
      os.system(cmd)

   def make_vida_plots(self, date):
      dates = date.replace("_", "")
      events = self.r.keys("E:" + dates + "*")
      for ev in events:
         rval = json.loads(self.r.get(ev) )
         if "solve_status" in rval: 
            print(ev, rval['solve_status'])
            if rval['solve_status'] == "SUCCESS":
               cmd = "cd ../pythonv2/; ./solve.py vida_plots " + ev.replace("E:", "")
               print(cmd)
               os.system(cmd)
            else:
               cmd = "cd ../pythonv2/; ./solve.py vida_failed_plots " + ev.replace("E:", "")
               print(cmd)
               os.system(cmd)
         else:
            cmd = "cd ../pythonv2/; ./solve.py vida_failed_plots " + ev.replace("E:", "")
            print(cmd)
            os.system(cmd)


   def update_station_event_ids(self,date):
      dates = date.replace("_", "")
      events = self.r.keys("E:" + dates + "*")
      print("E:" + dates + "*")
      
      for ev in events:
         rval = json.loads(self.r.get(ev) )
         print(ev, rval['stations'])
         self.update_obs_event_id(rval)

   def update_obs_event_id(self, event_data):
      # update all impacted obs
      event_id = event_data['event_id']
      if "solve_status" in event_data:
         solve_status = event_data['solve_status']
      else:
         solve_status = "UNSOLVED"
      if self.dynamodb is None:
         self.dynamodb = boto3.resource('dynamodb')
      for i in range(0, len(event_data['stations'])):
         # setup vars/values
         station_id = event_data['stations'][i]
         sd_video_file = event_data['files'][i]
         if "solve_status" in event_data:
            solve_status = event_data['solve_status']
         else:
            solve_status = "UNSOLVED"
         event_id_val = event_id + ":" + solve_status

         # setup redis keys for obs and get vals
         okey = "O:" + station_id + ":" + sd_video_file
         oikey = "OI:" + station_id + ":" + sd_video_file
         ro_val = self.r.get(okey)
         roi_val = self.r.get(oikey)
         if ro_val is not None:
            ro_val = json.loads(ro_val)
            ro_val['event_id'] = event_id_val
            ro_val = json.dumps(ro_val, cls=DecimalEncoder)
            self.r.set(okey, ro_val)
         if roi_val is not None:
            roi_val = json.loads(roi_val)
            roi_val['ei'] = event_id_val
            roi_val = json.dumps(roi_val, cls=DecimalEncoder)
            self.r.set(oikey, roi_val)

         # update DYNA OBS with EVENT ID

         table = self.dynamodb.Table('meteor_obs')
         response = table.update_item(
            Key = {
               'station_id': station_id,
               'sd_video_file': sd_video_file
            },
         UpdateExpression="set event_id = :event_id_val",
         ExpressionAttributeValues={
            ':event_id_val': event_id_val,
         },
         ReturnValues="UPDATED_NEW"
      )

   def make_alltime_obs_index(self):
      oi_keys = self.r.keys("OI:*")
      all_obs = []
      c = 0
      for key in oi_keys:
         #key = key.replace("OI:", "")
         val = self.r.get(key)
         if val is not None:
            val = json.loads(val)
         else:
            continue
         #{'ei': 0, 't': '01:37:31.960', 'rv': 1, 'ss': 0, 'pi': 164025, 'du': 0, 'rs': 79.97, 'st': 2}
         rdata = []
         rsdata = []
         elm = key.split(":")
         station_id = int(elm[1].replace("AMS",""))
         root_file = elm[2]
         root_file = root_file.replace(".mp4", "")
         day = root_file[0:10]
         rdata = [station_id, root_file, val['ei'],val['t'],val['rv'],val['ss'],val['pi'],val['du'],val['rs'],val['st']]
         all_obs.append(rdata)
         c += 1
         if c % 1000 == 0:
            print(c)
      save_json_file(self.DATA_DIR + "EVENTS/ALL_OBS.json", all_obs)

   def make_all_obs_index(self, date):
      # USE DYNCACH INSTEAD OF REDIS!
      year,mon,day = date.split("_")
      day_dir = self.DATA_DIR + "EVENTS/" + year + "/" + mon + "/" + day + "/"
      cl_day_dir = "/mnt/archive.allsky.tv/EVENTS/" + year + "/" + mon + "/" + day + "/"
      dyn_cache = day_dir
      all_obs_file = dyn_cache + date + "_ALL_OBS.json"
      all_obs = load_json_file(all_obs_file)
      print(len(all_obs), " TOTAL OBS for ", date)

      in_date = date
      # this will make a key-only file of ALL obs in the redis DB (which should also include all obs in the dynadb
      # this file can be used for fast indexing of UIs and also reconciliation jobs on the host machines 
      if date is None:
         oi_keys = self.r.keys("OI:*")
      else:
         oi_keys = self.r.keys("OI:*" + date + "*")
      all_obs_by_station ={}
      all_obs_by_day ={}
      c = 0
      #for key in oi_keys:
      for row in all_obs:
         #key = key.replace("OI:", "")
         print(row)
         val = {}
         key = "OI:" + row['station_id'] + ":" + row['sd_video_file']
         if "event_id" in row:
            val['ei'] = row['event_id'] 
         if "sync_status" in row:
            val['ss'] = row['sync_status'] 
         if "peak_int" in row:
            val['pi'] = row['peak_int'] 
         if "dur" in row:
            val['du'] = row['dur'] 
         if "calib" in row:
            print("CAL:", row['calib'])
            if len(row['calib']) > 0:
               res = row['calib'][-1]
               stars = row['calib'][-2]
            else:
               res = 0
               stars = 0
            val['rs'] = res
            val['st'] = stars
         else:
            val['rs'] = 0
            val['st'] = 0

         if "revision" in row:
            val['rv'] = row['revision']
         else:
            val['rv'] = 1
         if "meteor_frame_data" in row:
            if len(row['meteor_frame_data']) > 1:
               val['t'] = row['meteor_frame_data'][0][0]
            else:
               start_dt = self.starttime_from_file(row['sd_video_file'])
               val['t'] = start_dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
         else:
            start_dt = self.starttime_from_file(row['sd_video_file'])
            val['t'] = ttt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
         #val['rv'] = min(row['event_id']['start_datetime'])
         root_file = row['sd_video_file'].replace(".mp4", "")
         rdata = [row['station_id'], root_file, val['ei'],val['t'],val['rv'],val['ss'],val['pi'],val['du'],val['rs'],val['st']]
         #val = self.r.get(key)
         #$if val is not None:
          #  val = json.loads(val)
         #else:
         #   continue
         #{'ei': 0, 't': '01:37:31.960', 'rv': 1, 'ss': 0, 'pi': 164025, 'du': 0, 'rs': 79.97, 'st': 2}

         rdata = []
         rsdata = []
         print ("KEY", key)
         elm = key.split(":")
         station_id = int(elm[1].replace("AMS",""))
            
         
         root_file = elm[2]
         root_file = root_file.replace(".mp4", "")
         day = root_file[0:10]
         if day not in all_obs_by_day:
            all_obs_by_day[day] = {}
            all_obs_by_day[day]['obs'] = []
         if station_id not in all_obs_by_station:
            all_obs_by_station[station_id] = {}
            all_obs_by_station[station_id]['obs'] = []
         short_root = str(station_id) + "_" + root_file.replace(day + "_", "")
         rdata = [station_id, root_file, val['ei'],val['t'],val['rv'],val['ss'],val['pi'],val['du'],val['rs'],val['st']]
         rsdata = [short_root, val['ei'],val['t'],val['rv'],val['ss'],val['pi'],val['du'],val['rs'],val['st']]
         #if int(station_id) == 1:
         #   print("RVAL:", val)
         all_obs_by_station[station_id]['obs'].append(rdata)
         all_obs_by_day[day]['obs'].append(rdata)
         c += 1
         if c % 1000 == 0:
            print(c)
      print("DONE BUILD. SAVING...")
      #save_json_file(self.DATA_DIR + "EVENTS/OBS/ALL_OBS_BY_STATION.json", all_obs_by_station)
      #save_json_file(self.DATA_DIR + "EVENTS/OBS/ALL_OBS_BY_DAY.json", all_obs_by_day)

      # NOW MAKE 1 FILE FOR EACH DAY AND 1 FILE FOR EACH STATION
      day_dir = self.DATA_DIR + "EVENTS/OBS/DAYS/"
      station_dir = self.DATA_DIR + "EVENTS/OBS/STATIONS/"
      cloud_day_dir = "/mnt/archive.allsky.tv/EVENTS/OBS/DAYS/"
      cloud_station_dir = "/mnt/archive.allsky.tv/EVENTS/OBS/STATIONS/"
      if cfe(day_dir,1) == 0:
         os.makedirs(day_dir)
      if cfe(station_dir,1) == 0:
         os.makedirs(station_dir)

      if cfe(cloud_day_dir,1) == 0:
         os.makedirs(cloud_day_dir)
      if cfe(cloud_station_dir,1) == 0:
         os.makedirs(cloud_station_dir)

      #for key in all_obs_by_station:
      #   station_file = station_dir + "AMS" + str(key) + ".json"
      #   save_json_file(station_file, all_obs_by_station[key]['obs'], True)
      #   print("Saving...", station_file)

      for key in all_obs_by_day:

         day_file = day_dir + key + ".json"
         date = key
         if in_date is None:
            day_file = self.DATA_DIR + "EVENTS/ALL_OBS.json"
         save_json_file(day_file, all_obs_by_day[key]['obs'], True)
         print("Saving...", day_file)

         if date is not None:
            cmd = "cp " + day_dir + "*" + date + "*" + " " + cloud_day_dir
            print(cmd)
            os.system(cmd)
      #cmd = "cp " + station_dir + "*" + " " + cloud_station_dir
      #os.system(cmd)


   def update_events_index_day(self, date):
      all_events = []
      from DynaDB import search_events
      dynamodb = boto3.resource('dynamodb')
      stations = None
      events = search_events(dynamodb, date, stations, nocache=0)
      for item in events:
         item = json.loads(json.dumps(item), parse_float=Decimal)
         key = "E:" + item['event_id']
         ev_idx = self.event_to_ev_index(item)
         ikey = "EI:" + item['event_id'] + ":" + ev_idx['ss']
         if ev_idx['ss'] == 'S':
            print("EV IDX:", ikey)
         if "obs" in item:
            del (item['obs'])
         vals = json.dumps(ev_idx)
         self.r.set(ikey,vals)
         all_events.append(ev_idx)
         print("SETTING:", ikey)

   def update_all_events_index(self):
      all_events = [] 
      dynamodb = boto3.resource('dynamodb')
      ####
      #
      # GET EVENTS
      #
      ###

      table = dynamodb.Table('x_meteor_event')
      response = table.scan()
      data = response['Items']
      for item in response['Items']:
         item = json.loads(json.dumps(item), parse_float=Decimal)
         key = "E:" + item['event_id']
         ev_idx = self.event_to_ev_index(item) 
         ikey = "EI:" + item['event_id'] + ":" + ev_idx['ss'] 
         #if 'solve_status' in item:
         #   print(ev_idx['id'], ev_idx['ss'], )
         if ev_idx['ss'] == 'S':
            print("EV IDX:", ev_idx)
         if "obs" in item:
            del (item['obs'])
         vals = json.dumps(ev_idx)
         self.r.set(ikey,vals)
         all_events.append(ev_idx)
         print("SETTING:", ikey)

      while 'LastEvaluatedKey' in response:
         response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
         for item in response['Items']:
            key = "E:" + item['event_id']
            ev_idx = self.event_to_ev_index(item) 
            ikey = "EI:" + item['event_id'] + ":" + ev_idx['ss'] 
            #if 'solve_status' in item:
            #   print(ev_idx['id'], ev_idx['ss'], )
            if "obs" in item:
               del (item['obs'])
            vals = json.dumps(ev_idx)
            self.r.set(ikey,vals)
            #print("SETTING:", ikey)
            all_events.append(ev_idx)
      all_events = json.loads(json.dumps(all_events), parse_float=Decimal)
      save_json_file(self.DATA_DIR + "EVENTS/ALL_EVENTS_INDEX.json", all_events, True)
      print("saved /mnt/ams2/EVENTS/ALL_EVENTS_INDEX.json")
      unsolved = []
      failed = []
      solved = []
      for event in all_events:
         if event['ss'] == "S":
            solved.append(event)
         if event['ss'] == "U":
            unsolved.append(event)
         if event['ss'] == "F":
            failed.append(event)
      save_json_file(self.DATA_DIR + "EVENTS/ALL_EVENTS_INDEX_SOLVED.json", solved, True)
      save_json_file(self.DATA_DIR + "EVENTS/ALL_EVENTS_INDEX_FAILED.json", failed, True)
      save_json_file(self.DATA_DIR + "EVENTS/ALL_EVENTS_INDEX_UNSOLVED.json", unsolved, True)
      cmd = "cp /mnt/ams2/EVENTS/ALL_EVENTS* /mnt/archive.allsky.tv/EVENTS/"
      print(cmd)
      os.system(cmd)

      #exit()

   def make_unsolved_list(self):
      ekeys = self.r.keys("E:*")
      solved = []
      unsolved = []
      failed = []
      c = 0
      for ekey in ekeys:
         data = json.loads(self.r.get(ekey))
         eid = ekey.replace("E:", "")
         if "solve_status" in data:
            solve_status = data['solve_status']
         else:
            solve_status = "UNSOLVED"
         if "SUCCESS" in solve_status:
            solved.append(eid)
         if "FAIL" in solve_status:
            failed.append(eid)
         if "UNSOLVED" in solve_status:
            unsolved.append(eid)
         c += 1
         if c % 1000 == 0:
            print(c)
      save_json_file(self.DATA_DIR + "EVENTS/UNSOLVED_IDS.json", unsolved)
      save_json_file(self.DATA_DIR + "EVENTS/FAILED_IDS.json", failed)
      save_json_file(self.DATA_DIR + "EVENTS/SOLVED_IDS.json", solved)
      print(self.DATA_DIR + "EVENTS/SOLVED_IDS.json")

   def purge_dead_meteors(self):
      all_obs_keys = self.r.keys("OI:*")
      print(len(all_obs_keys))
      c = 0
      bc = 0
      for key in sorted(all_obs_keys, reverse=True):
         el = key.split(":")
         station_id = el[1]
         sd_video_file = el[2]
         year = sd_video_file[0:4]
         day = sd_video_file[0:10]
         prev_img = "/mnt/archive.allsky.tv/" + station_id + "/METEORS/" + year + "/" + day + "/" + station_id + "_" + sd_video_file.replace(".mp4", "-prev.jpg")
         if cfe(prev_img) == 1:
            status = "good"
         else:
            status = "bad"
            print(c,prev_img, status)
            delete_obs(self.dynamodb, station_id, sd_video_file)
            bc += 1
         if c % 1000 == 0:
            print(c,prev_img, status)
         #print(station_id, sd_video_file)
         #if bc > 1:
         #   exit()
         c += 1

   def all_event_stats(self):
      all_events_file = self.DATA_DIR + "EVENTS/ALL_EVENTS_INDEX.json"
      event_orb_file = self.DATA_DIR + "EVENTS/ALL_EVENTS_INDEX_ORBS.json"

      solved_events_file = self.DATA_DIR + "EVENTS/ALL_EVENTS_INDEX_SOLVED.json"
      failed_events_file = self.DATA_DIR + "EVENTS/ALL_EVENTS_INDEX_FAILED.json"
      unsolved_events_file= self.DATA_DIR + "EVENTS/ALL_EVENTS_INDEX_UNSOLVED.json"

      solved_ids_file = self.DATA_DIR + "EVENTS/ALL_EVENTS_IDS_SOLVED.json"
      failed_ids_file = self.DATA_DIR + "EVENTS/ALL_EVENTS_IDS_FAILED.json"
      unsolved_ids_file= self.DATA_DIR + "EVENTS/ALL_EVENTS_IDS_UNSOLVED.json"

      event_stats_file = self.DATA_DIR + "EVENTS/ALL_EVENTS_INDEX_STATS.json"
      solved = load_json_file(solved_events_file)
      unsolved = load_json_file(unsolved_events_file)
      failed = load_json_file(failed_events_file)
      stats = {}
      orbs = []
      orb = []
      stats['solved'] = len(solved)
      stats['unsolved'] = len(unsolved)
      stats['failed'] = len(failed)

      ids = {}
      ids['solved']  = []
      ids['unsolved']  = []
      ids['failed']  = []
      for event in solved:
         orb = []
         ids['solved'].append(event['id'])
         stations = []
         #if "st" not in event:
         for st in event['st']:
            st = st.replace("AMS", "")
            stations.append(st)

         if event['a'] != 0:
            # still need shower!
            orb.append(event['id'])
            orb.append(stations)
            orb.append(event['dr'])
            if "vl" in event:
               orb.append(event['vl'])
            else:
               orb.append(0)
            if "ee" in event:
               orb.append(event['ee'])
            else:
               orb.append(0)
            #orbs.append(event['sr'])
            orb.append(event['a'])
            orb.append(event['e'])
            orb.append(event['i'])
            orb.append(event['pr'])
            orb.append(event['q'])
            orb.append(event['nd'])
            orb.append(event['la_sun'])
            orb.append(event['T'])
            orb.append(event['ma'])
            orb.append(event['rd'][0])
            orb.append(event['rd'][1])
            orb.append(event['rd'][2])
            orb.append(event['rd'][3])
            # id, dur, vel, ele, a, e, i, pr, q, nd, la_sun, T, ma, a_rad_ra, a_rad_dec,h_rad_ra,h_rad_dec
            orbs.append(orb)

#      solved_ids_file 
#      failed_ids_file 
#      unsolved_ids_file

      for event in unsolved:
         ids['unsolved'].append(event['id'])
      for event in failed:
         ids['failed'].append(event['id'] )
      stats['ids'] = ids
      save_json_file(event_orb_file, orbs, True)
      save_json_file(event_stats_file, stats, True)


      save_json_file(solved_ids_file, ids['solved'], True)
      save_json_file(unsolved_ids_file, ids['unsolved'], True)
      save_json_file(failed_ids_file, ids['failed'], True)

      solved_ids_file = self.DATA_DIR + "EVENTS/ALL_EVENTS_IDS_SOLVED.json"
      failed_ids_file = self.DATA_DIR + "EVENTS/ALL_EVENTS_IDS_FAILED.json"
      unsolved_ids_file= self.DATA_DIR + "EVENTS/ALL_EVENTS_IDS_UNSOLVED.json"


   def event_to_ev_index(self,item):
      # we want orbit vars
      # traj - vel, end alt, 
      # unq list of stations
      # max brightness
      # duration
      # status
      ev_idx = {}
      ev_idx['id'] = item['event_id']
      ev_idx['fl'] = []
      ev_idx['st'] = []
      if "stations" in item:
         for st in item['stations']:
            ev_idx['st'].append(st.replace("AMS", ""))
         for tfile in item['files']:
            tday = tfile[0:10]
            tfile = tfile.replace(tday, "")
            tfile = tfile.replace(".mp4", "")
            ev_idx['fl'].append(tfile)
         ev_idx['dt'] = min(item['start_datetime'])
      else:
         print("No stations in item?")
      if "solve_status" in item:
         ev_idx['ss'] = item['solve_status']
      else:
         ev_idx['ss'] = "U"
         return(ev_idx)
     
      if "FAIL" in ev_idx['ss'] :
         ev_idx['ss'] = "F"
         return(ev_idx)
      if "SUCCESS" in ev_idx['ss'] :
         ev_idx['ss'] = "S"
      if ev_idx['ss'] is None:
         ev_idx['ss'] = "U"

      elif "solution" in item and ev_idx['ss'] == 'S':
         sol = item['solution']
         
         ev_idx['dr'] = sol['duration']
         if "rad" in sol:
            if sol['rad']['apparent_ECI']['ra'] !=0 and  sol['rad']['apparent_ECI']['ra'] is not None and sol['rad']['ecliptic_helio']['L_h']is not None:
               ap_ra =  np.radians(np.degrees(float(sol['rad']['apparent_ECI']['ra']))-180)
               ap_dec =  np.radians(np.degrees(float(sol['rad']['apparent_ECI']['dec']))-180)

               hl_dec = np.degrees(float(sol['rad']['ecliptic_helio']['B_h']))
               hl_ra = np.degrees(float(sol['rad']['ecliptic_helio']['L_h']))
            else:
               ap_ra,ap_dec,hl_ra,hl_dec = [0,0,0,0]
         else:
            ap_ra,ap_dec,hl_ra,hl_dec = [0,0,0,0]
         ev_idx['rd'] = [ap_ra,ap_dec,hl_dec,hl_ra]

         if "shower" in item['solution']:
            ev_idx['sr'] = item['solution']['shower']['shower_code']
            if ev_idx['sr'] == "...":
               ev_idx['sr'] = ""
         if "orb" in item['solution']:
            orb = item['solution']['orb']
            if orb['a'] is not None:
               ev_idx['a'] = round(float(orb['a']),2)
               ev_idx['e'] = round(float(orb['e']),2)
               ev_idx['i'] = round(float(orb['i']),2)
               ev_idx['pr'] = round(float(orb['peri']),2)
               ev_idx['q'] = round(float(orb['q']),2)
               ev_idx['nd'] = round(float(orb['node']),2)
               ev_idx['la_sun'] = round(float(orb['la_sun']),2)
               ev_idx['T'] = round(float(orb['T']),2)
               ev_idx['ma'] = round(float(orb['mean_anomaly']),2)
            else:
               ev_idx['a'] = 0
               ev_idx['e'] = 0
               ev_idx['i'] = 0
               ev_idx['pr'] = 0
               ev_idx['q'] = 0
               ev_idx['nd'] = 0
               ev_idx['la_sun'] = 0
               ev_idx['T'] = 0
               ev_idx['ma'] = 0

         if "traj" in item:
            traj = item['traj']
            ev_idx['vl'] = round(float(item['traj']['v_init'])/1000, 2)
            ev_idx['ee'] = round(float(item['traj']['end_ele'])/1000,2)
         most_max_int = 0
         return(ev_idx)

      elif "soluion" not in item:
         ev_idx['ss'] = "U"
         return(ev_idx)
      else:
         ev_idx['ss'] = "F"
      


      # OINT NOT IN CURRENT OBS SO WE CAN'T DO THIS!
      #if "obs" in item:
      #   for obs in item['obs']:
      #      for ofile in item['obs'][obs]:
      #         print(item['obs'][obs][ofile])
      #         max_int = max(item['obs'][obs][ofile]['oint'])
      #         if max_int > most_max_int:
      #            most_max_int = max_int
      #   ev_idx['max_int'] = most_max_int
      #print(ev_idx)
      #exit()

   def update_missing_wmpl_keys(self):
      ev_keys = self.r.keys("E:*")
      for ev_key in sorted(ev_keys, reverse=True):
         event_id = ev_key.replace("E:", "")
         evdata = self.r.get(ev_key)
         if evdata is not None:
            evdata = json.loads(evdata)
            if "wmpl_id" in evdata:
               print("DONE")
            else :
               year = event_id[0:4]
               mon = event_id[4:6]
               dom = event_id[6:8]
               ev_index = "/mnt/archive.allsky.tv/EVENTS/" + year + "/" + mon + "/" + dom + "/" + event_id + "/index.html" 
               vel_file = ev_index.replace("index.html", event_id + "_velocities.jpg")
               if "solve_status" not in evdata:
                  continue

               if evdata['solve_status'] == "SUCCESS":
                  if cfe(vel_file) == 0:
                     print("NO VEL", vel_file)
                  if cfe(ev_index) == 1:
                     cmd = "grep velocities " + ev_index
                     try:
                        output = subprocess.check_output(cmd, shell=True).decode("utf-8") 
                        elm = output.split("/")
                        vel_elm = elm[8].split("_")
                        wmpl_id = vel_elm[0] + "_" + vel_elm[1]
                        evdata['wmpl_id'] = wmpl_id
                        self.r.set(ev_key, json.dumps(evdata))
                     except:
                        print("COULDNT RECOVER ID", vel_file)
      

   def update_all_stations_events(self):
      self.update_missing_wmpl_keys()
      exit()
      all_station_events = {}
      print("""
            UPDATE ALL STATION EVENTS
            Will create 1 master event file for each station in the wasabi/events dir for that staion.
      """)
      ev_keys = self.r.keys("E*")
      for ev_key in ev_keys:
         evdata = self.r.get(ev_key)
         if evdata is not None:
            evdata = json.loads(evdata)
         else:
            continue
         if "event_id" in evdata:
            event_id = evdata['event_id']
         else:
            event_id = 0
         if "solve_status" in evdata:
            solve_status = evdata['solve_status']
         else:
            solve_status = 0

         if "stations" not in evdata:
            print("PROBLEM EVENT:", ev_key )
            continue
         for i in range(0,len(evdata['stations'])):
            this_station = evdata['stations'][i]
            this_file = evdata['files'][i]
            if this_station not in all_station_events:
               all_station_events[this_station] = {}
               all_station_events[this_station]['events'] = []
            obs_ev_data = this_file + ":" + str(event_id) + ":" + str(solve_status)
            all_station_events[this_station]['events'].append(obs_ev_data)
      save_json_file(self.DATA_DIR + "EVENTS/ALL_STATIONS_EVENTS.json", all_station_events, True)
      for station_id in all_station_events:
         stjsf = self.DATA_DIR + "EVENTS/ALL_EVENTS_" + station_id + ".json"
         stjsf_zip = self.DATA_DIR + "EVENTS/ALL_EVENTS_" + station_id + ".json.gz"
         cloud_dir = "/mnt/archive.allsky.tv/EVENTS/STATIONS/" 
         save_json_file(stjsf, all_station_events[station_id], True)
         os.system("gzip -f " + stjsf)
         os.system("cp " + stjsf_zip +" " + cloud_dir)
         fn = stjsf_zip.split("/")[-1]
         print("SAVED:", cloud_dir + fn)
            

   def list_events_for_day(self):
      ec = 0
      self.file_index = {}
      for event in self.all_events:
         if "event_id" not in event:
            event['event_id'] = 0
         if "solve_status" not in event:
            event['solve_status'] = "UNSOLVED"
            self.all_events[ec]['solve_status'] = "UNSOLVED"
         if "total_stations" not in event:
            event['total_stations'] = len(set(event['stations']))
            self.all_events[ec]['total_stations'] = event['total_stations']
         if event['total_stations'] == 1:
            event['solve_status'] = "SINGLE STATION" 
         for file in event['files']:
            self.file_index[file] = event['event_id']
         ec += 1

      self.single_station_obs = []
      self.multi_station_obs = []

      self.get_rejected_meteors(self.date)
      #self.rejected_meteors =  search_trash(self.dynamodb, station_id, date, no_cache=0)
      #for key in self.rejects:
      #   obj = self.rejects[key]
      #   print("REJECTS:", key)
      good_obs = []
      if self.all_obs is not None:
         print("LEN OBS:", len(self.all_obs))
      else : 
         self.all_obs = []
      for ob in self.all_obs:
         st_id = ob['station_id']
         vid = ob['sd_video_file']
         key = st_id + "_" + vid
         if key not in self.rejects:
            good_obs.append(ob)
      self.all_obs = good_obs
      print("LEN OBS AFTER DELETES:", len(self.all_obs))

      for ob in self.all_obs:
         if ob['sd_video_file'] in self.file_index:
            event_id = self.file_index[ob['sd_video_file']]
            self.multi_station_obs.append(ob)
         else:
            if "deleted" in ob:
               if ob['deleted'] == 1:
                  continue
            event_id = self.check_existing_event(ob)
            if event_id == None:
               print("NO EVENT FOR OBS!", ob['station_id'], ob['sd_video_file'])
               self.single_station_obs.append(ob)
            else:
               print("THIS OB BELONGS TO THIS EVENT!", ob['station_id'], ob['sd_video_file'], event_id)
               exit()

      self.all_events = sorted(self.all_events, key=lambda x: (x['event_id']), reverse=True)
      for event in self.all_events:
         print("MSE:", event['event_id'], event['total_stations'], event['solve_status'])
      print("MS OBS:", len(self.multi_station_obs))
      print("SS OBS:", len(self.single_station_obs))

   def get_rejected_meteors(self, date):
      self.rejects = {}
      #for station_id in self.all_stations:
      #   print(station_id)
      for station_row in self.all_stations:
         station_id = station_row[0]
         print("DATE:", date)
         temp = search_trash(self.dynamodb, station_id, date, no_cache=0)
         for obj in temp:

            sd_vid = obj['sd_video_file']
            obs_key = station_id + "_" + sd_vid
            self.rejects[obs_key] = 1

   def update_events_for_day(self):
      new_events = []
      for ob in self.single_station_obs:
         found_existing = self.check_existing_event(ob) 
         if found_existing is not None:
            print("AN EVENT FOR THIS OBS WAS FOUND:", found_existing ) 
         else: 
            obs_time = self.get_obs_datetime(ob)
            print("EXISTING EVENT NOT FOUND FOR THIS OB.")

            if ob['station_id'] in self.station_loc:
               ob['lat'] = self.station_loc[ob['station_id']][0]
               ob['lon'] = self.station_loc[ob['station_id']][1]
               new_events = self.check_make_events(obs_time, ob, new_events)
            else:
               print("STATION MISSING FROM SELF.station_loc", ob['station_id'])
      new_mse = []
      new_sse = []
      for ne in new_events:
         total_stations = len(set(ne['stations']))
         if total_stations > 1:
            ne['total_stations'] = total_stations 
            str_times = []
            for ttt in ne['start_datetime']:
               if isinstance(ttt,str) is True:
                  time_str = ttt
               else:
                  time_str = ttt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
               str_times.append(time_str)
            ne['start_datetime'] = str_times
            #print("INSERT NEW EVENT:" )
            self.insert_new_event(ne)
            new_mse.append(ne)
         else:
            str_times = []
            for ttt in ne['start_datetime']:
               if isinstance(ttt,str) is True:
                  time_str = ttt
               else:
                  time_str = ttt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
               str_times.append(time_str)
            ne['start_datetime'] = str_times


            new_sse.append(ne)

      save_json_file(self.event_dir + self.date + "_ALL_SINGLE_STATION_METEORS.json", new_sse)
      print("SAVED:", self.event_dir + self.date + "_ALL_SINGLE_STATION_METEORS.json")
      if len(new_mse) > 0: 
         os.system("./DynaDB.py udc " + self.date + " events")
         print("./DynaDB.py udc " + self.date + " events")
         print("Updated CACHE with latest DynaDB!")

      #if len(new_mse) > 0 or cfe(self.cloud_all_events_file) == 0 or cfe(:
      if True:
         cmd = "cp " + self.all_events_file + " " + self.cloud_all_events_file
         print(cmd)
         os.system(cmd)
         cmd = "cp " + self.all_obs_file + " " + self.cloud_all_obs_file
         print(cmd)
         os.system(cmd)
         cmd = "cp " + self.all_stations_file + " " + self.cloud_all_stations_file
         print(cmd)
         os.system(cmd)
         cmd = "cp " + self.all_stations_file + " " + self.cloud_all_stations_file
         print(cmd)
         os.system(cmd)
         cmd = "cp " + self.single_station_file + " " + self.cloud_single_stations_file
         print(cmd)
         os.system(cmd)

      
      print("All events for today are made.")
      print(self.all_events_file)

      print(len(new_mse), "New events added.")

   def make_station_obs_html(self,date):
      station_html = {}
      good_obs = self.r.keys("OI:*" + date + "*") 
      year, month, day = date.split("_")
      station_info = {}
      station_header_html = {}
      stations = self.r.keys("ST:*")
      for st in stations:
         st = st.replace("ST:", "") 
         station_id = st
         skey = "ST:" + st
         sval = self.r.get(skey)
         if sval is not None:
            sval = json.loads(sval)
            station_info[st] = sval
            print(sval.keys())
            header_html = "<div class='container' style='color: white'> "
            #dict_keys(['station_id', 'operator_name', 'op_status', 'monitor', 'cameras', 'city', 'state', 'country', 'email', 'lat', 'lon', 'alt', 'obs_name', 'username', 'api_key', 'mac_addr', 'public_ip', 'registration']) header_html += "Station ID: " + sval['station_id'] + "<br>"
            header_html += """<div id="container" style="float:left">"""
            header_html += "<br>Station ID: " + sval['station_id'] + "<br>"
            header_html += "Operator Name: " + sval['operator_name'] + "<br>"
            if "obs_name" in sval:
               header_html += "Observatory: " + sval['obs_name'] + "<br>"
            if "op_status" in sval:
               header_html += "Status: " + sval['op_status'] + "<br>"
            if "city" in sval:
               header_html += "City: " + sval['city'] + "<br>"
            if "state" in sval:
               header_html += "State: " + sval['state'] + "<br>"
            if "country" in sval:
               header_html += "Country: " + sval['country'] + "<br>"
            if "lat" in sval:
               lat = sval['lat']
            if "lon" in sval:
               lon = sval['lon']
            station_link = "https://allsky7.net/stations/" + station_id + ".jpg"
            station_map = """ <iframe scrolling="no" width=768 height=432 src="https://archive.allsky.tv/APPS/dist/maps/index.html?mf=https://archive.allsky.tv/EVENTS/2021/08/04/2021_08_04_ALL_STATIONS.kml&lat=""" + str(lat) + """&lon=""" + str(lon) + """&zoom=8"></iframe>"""
            station_image = """
               <div class='obs_thumb' data-id='""" + station_id + """' style="float: left; opacity: """ + "1" + """; border: 1px """ + "WHITE" + """ solid; padding: 0px; margin: 10px; solid; background-image: url('""" + station_link + """'); background-repeat: no-repeat; background-size: 100%; height: 160px; width: 320px; "><span style='text-shadow: 2px 2px #000000; color: #FFFFFF; font-size: 10px;'>""" + station_id + " "  """</p></div>
            """

            
            header_html += "</div>"
            header_html += """<div id="container" style="float: left">"""
            header_html += station_image 
            header_html += "</div>"
            header_html += """<div id="container" style="float: left">"""
            header_html += station_map 
            header_html += "</div>"
            header_html += """<div style="clear:both"></div>"""
 
            header_html += "</div>"
            print(st, header_html)
            station_header_html[st] = header_html 
         else:
            station_header_html[st] = "NO CLOUD STATION DATA"

      for obs_key in good_obs:
         rid, station_id, sd_video_file = obs_key.split(":")
            
         obs_key = station_id + "_" + sd_video_file
         self.good_obs_keys[obs_key] = 1
         border_color= "white"
         desc_text = "" 
         img_link, img_html = self.make_obs_image(station_id,sd_video_file,border_color,desc_text)
         if station_id not in station_html:
            station_html[station_id] = ""
         station_html[station_id] += img_html + "\n"
         print(obs_key, img_link)
 
      outdir = self.DATA_DIR + "EVENTS/" + year + "/" + month + "/" + day + "/OBS/" 
      cloud_outdir = "/mnt/archive.allsky.tv/EVENTS/" + year + "/" + month + "/" + day + "/OBS/" 
      if cfe(outdir, 1)== 0:
         os.makedirs(outdir)
      if cfe(cloud_outdir, 1)== 0:
         os.makedirs(cloud_outdir)

      print(station_header_html.keys())
      for station_id in station_html:
         outfile = outdir + station_id + ".html"
         cloud_outfile = cloud_outdir + station_id + ".html"
         print("wrote", outfile)
         fp = open(outfile, "w")
         fp.write(station_header_html[station_id])
         fp.write(station_html[station_id])
         fp.close()
         cmd = "cp " + outfile + " " + cloud_outfile
         print(cmd)
         os.system(cmd)
      
   def quick_report(self,date):
      edate = date.replace("_","")
      events = self.r.keys("E:*" + edate + "*") 
      c = 1
      rpt = {}
      rpt['solved'] = 0
      rpt['failed'] = 0
      rpt['unsolved'] = 0
      for key in sorted(events):
         event_data = json.loads(self.r.get(key))
         if "solve_status" in event_data:
            print(event_data['event_id'], event_data['solve_status'])
            if "FAIL" in event_data['solve_status']:
               rpt['failed'] += 1
            else:
               rpt['solved'] += 1
         else:
            print(event_data['event_id'], "UNSOLVED")
            rpt['unsolved'] += 1
         c += 1
      for k in rpt:
         print(k, rpt[k])

 
   def EOD_coin_report(self):
      #self.coin_events_file = self.DATA_DIR + "EVENTS/" + self.year + "/" + self.month + "/" + self.day + "/" + self.date + "_COIN_EVENTS.json"  
      return()
      self.coin_events = load_json_file(self.coin_events_file)
      print("COIN EVENTS:", len(self.coin_events))
      print("ALL EVENTS:", len(self.all_events))
      stats = {} 
      for event_id in self.coin_events:
         solve_status = "UNSOLVED"
         if event_id in self.event_dict:
            ev_run_status = "SOLVER_RAN"
            if "solve_status" in self.event_dict[event_id]:
               solve_status = self.event_dict[event_id]['solve_status']
         else:
            ev_run_status = "UNSOLVED"
         print(event_id, ev_run_status, solve_status) # self.event_dict[event_id].keys())
         if solve_status not in stats:
            stats[solve_status] = {}
            stats[solve_status]['count'] = 1
            stats[solve_status]['event_ids'] = []
            stats[solve_status]['event_ids'].append(event_id)

         else:
            stats[solve_status]['count'] += 1
            stats[solve_status]['event_ids'].append(event_id)

      event_html = {}
      #meteor_preview_html(obs_id)

      fp_solved = open(self.event_dir + self.date + "_EVENTS_SOLVED.html", "w")
      fp_failed = open(self.event_dir + self.date + "_EVENTS_FAILED.html", "w")
      fp_invalid = open(self.event_dir + self.date + "_EVENTS_INVALID.html", "w")
      fp_unsolved = open(self.event_dir + self.date + "_EVENTS_UNSOLVED.html", "w")

      for status in stats:
         #print(status, stats[status]['count'])
         for eid in stats[status]['event_ids']:
            ev_link = self.event_dir.replace("/mnt/ams2", "") + eid + "/index.html" 
            if eid not in event_html:
               event_html[eid] = {}
               event_html[eid]['status'] = status 
               event_html[eid]['html'] = "<h1><a href=" + ev_link + ">" + eid + "</a></h1>" + "<h2>Preview</h2><div>"
            if eid in self.event_dict:
               print("   ", eid, sorted(set(self.event_dict[eid]['stations'])), self.event_dict[eid]['solve_status'], self.coin_events[eid]['obs'].keys() )
               for obs_id in self.coin_events[eid]['obs'].keys():
                  event_html[eid]['html'] += self.meteor_preview_html(obs_id)
               event_html[eid]['html'] += "</div><div style='clear: both'></div>"
               event_html[eid]['html'] += "<h2>Observations</h2><ul>"
               for obs_id in self.coin_events[eid]['obs'].keys():
                  event_html[eid]['html'] += "<li>" + obs_id + "</li>"
               event_html[eid]['html'] += "</ul>"
            else:
               print("   ", eid, "not in event dict!", self.coin_events[eid]['obs'])

      print("Done coin report")
      counts = {}
      counts['SOLVED'] = 0
      counts['FAILED'] = 0
      counts['INVALID'] = 0
      counts['UNSOLVED'] = 0

      for eid in event_html:
         print(eid, event_html[eid]['status'], event_html[eid]['html'])
         if "SUCCESS" in event_html[eid]['status'] and "UNSOLVED" not in event_html[eid]['status']:
            counts['SOLVED'] += 1 
            fp_solved.write(event_html[eid]['html'])
         if "FAIL" in event_html[eid]['status']:
            counts['FAILED'] += 1 
            fp_failed.write(event_html[eid]['html'])
         if "INVALID" in event_html[eid]['status']:
            counts['INVALID'] += 1 
            fp_invalid.write(event_html[eid]['html'])
         if "UNSOLVED" in event_html[eid]['status']:
            counts['UNSOLVED'] += 1 
            fp_unsolved.write(event_html[eid]['html'])
            #cmd = "python3 EVRun.py resolve " + self.date + " " + eid
            #print(cmd)
            #os.system(cmd)
      clat = 40 
      clon = 40
      map_file = "https://archive.allsky.tv/EVENTS/" + self.year + "/" + self.month + "/" + self.day + "/" + self.date + "_ALL_EVENTS.kml"
      main_html = "<h1>Meteor Ops Report for " + self.date + "</h1>"
      main_html += """
         <iframe width=100% height=450 src="https://archive.allsky.tv/APPS/dist/maps/index.html?mf={:s}&lat={:s}&lon=-{:s}&zoom=3"></iframe>
            <div class="carousel-caption d-none d-md-block">
               <p><a href="{:s}">KML Download</a></p>
            </div>
         </div>
      """.format(map_file, str(clat), str(clon), map_file)
      mfp = open(self.event_dir + "/index.html", "w")
      mfp.write(main_html)
      for status in counts:
         link = self.date + "_EVENTS_" + status + ".html"
         mfp.write("<a href=" + link + ">" + status + "</a> " + str(counts[status]) + "<br>")
      mfp.close()
      print(self.event_dir + "/index.html")

      #exit()


   def EOD_report(self, date):
      report_template_file = "allsky.tv/event_template.html"
      self.rejects = {}
      self.good_obs_keys = {}
      print("OI:*" + date + "*") 
      self.make_station_obs_html(date)
      good_obs = self.r.keys("OI:*" + date + "*") 
      print("GOOD OBS:", len(good_obs))
      y,m,d = date.split("_")
      year = y
      month = m
      day = d
      good_obs_data = load_json_file(self.DATA_DIR + "EVENTS/" + y + "/" + m + "/" + d + "/" + date + "_ALL_OBS.json")
      for data in good_obs_data:
         st = data['station_id']
         vid = data['sd_video_file']
         obs_key = st + "_" + vid
         self.good_obs_keys[obs_key] = data
      print("GOOD OBS FILE:", len(good_obs_data))
      print(self.DATA_DIR + "EVENTS/" + y + "/" + m + "/" + d + "/" + date + "_ALL_OBS.json")
      sdate = date.replace("_", "")
      fp = open(report_template_file)
      report_template = ""
      for line in fp:
         report_template += line

      self.vdir = self.event_dir.replace("/mnt/ams2", "")
      self.edir = self.event_dir
      self.cdir = self.event_dir.replace("/mnt/ams2", "/mnt/archive.allsky.tv")

      traj_file = self.edir + "ALL_TRAJECTORIES.kml"
      orb_file =  self.edir + "ALL_ORBITS.json"
      rad_file =  self.edir + "ALL_RADIANTS.json"
      stations_file= self.edir + date + "_ALL_STATIONS.json"

      if cfe(traj_file) == 0:
         print("MISSING", traj_file)
         exit()
      if cfe("MISSING", orb_file) == 0:
         print(orb_file)
         exit()
      if cfe("MISSING", rad_file) == 0:
         print(rad_file)
         exit()
      if cfe("MISSING", stations_file) == 0:
         print(stations_file)
         exit()
      traj_link = "https://archive.allsky.tv" + self.vdir + "ALL_TRAJECTORIES.kml"
      orb_link = "https://archive.allsky.tv" + self.vdir + "ALL_ORBITS.json"
      rad_link = "https://archive.allsky.tv" + self.vdir + "ALL_RADIANTS.json"
      stations_link = "https://archive.allsky.tv" + self.vdir + date + "_ALL_STATIONS.kml"

      print(traj_link)
      print(orb_link)
      print(rad_link)
      print(stations_link)
      short_date = self.date.replace("_", "")
      report_template = report_template.replace("{SHORT_DATE}", short_date)
      report_template = report_template.replace("{TRAJ_LINK}", traj_link)
      report_template = report_template.replace("{ORB_LINK}", orb_link)
      report_template = report_template.replace("{RAD_LINK}", rad_link)
      report_template = report_template.replace("{STATIONS_LINK}", stations_link)
      #print("OUT:", report_template) 
      station_report = {}
      obs = load_json_file(self.all_obs_file)
      if cfe(self.single_station_file) == 1:
         ssd = load_json_file(self.single_station_file)
      else:
         ssd = {}
      print("ALL EVENTS FILE:", self.all_events_file)
      msd = load_json_file(self.all_events_file)
      print(len(obs) , "total observations.")
      print(len(ssd) , "single station events.")
      print(len(msd) , "multi station events.")
      meteor_counts = {}
      meteor_counts_stations = {}
      for h in range(0,24):
          for m in range(1,5):
             bin = str(h) + "." + str(m)
             bin = str(h) 
             meteor_counts[bin] = {}
             meteor_counts[bin]['count'] = 0
             meteor_counts[bin]['stations'] = {}
             meteor_counts[bin]['avg'] = 0

      for data in ssd:
         bin = self.find_bin(min(data['start_datetime']))
         meteor_counts[bin]['count'] += 1

         used = {} 
         for i in range(0, len(data['stations'])): 
            station = data['stations'][i]
            if station in used:
               continue
            station_bin = station + "." + bin
            if station_bin not in meteor_counts_stations:
               meteor_counts_stations[station_bin] = 1 
            else:
               meteor_counts_stations[station_bin] += 1 
            if station not in meteor_counts[bin]['stations']:
               meteor_counts[bin]['stations'][station] = 1
            else:
               meteor_counts[bin]['stations'][station] += 1

            if station not in station_report:
               station_report[station] = {}
               station_report[station]['obs'] = 1
               station_report[station]['mse'] = 1
               station_report[station]['sse'] = 0 
            else:
               station_report[station]['obs'] += 1
               station_report[station]['mse'] += 1
               station_report[station]['sse'] += 0 
            used[station] = 1

      used = {} 
      for data in msd:
         bin = self.find_bin(min(data['start_datetime']))
         meteor_counts[bin]['count'] += 1
         for i in range(0, len(data['stations'])): 
            station = data['stations'][i]
            if station in used:
               continue
            station_bin = station + "." + bin
            if station_bin not in meteor_counts_stations:
               meteor_counts_stations[station_bin] = 1 
            else:
               meteor_counts_stations[station_bin] += 1 
            if station not in meteor_counts[bin]['stations']:
               meteor_counts[bin]['stations'][station] = 1
            else:
               meteor_counts[bin]['stations'][station] += 1


            if station not in station_report:
               station_report[station] = {}
               station_report[station]['obs'] = 1
               station_report[station]['mse'] = 1
               station_report[station]['sse'] = 0
            else:
               station_report[station]['obs'] += 1
               station_report[station]['mse'] += 1
               station_report[station]['sse'] += 0
            used[station] = 1
      num_keys = []
      for key in station_report.keys():
         num_key = int(key.replace("AMS",""))
         num_keys.append(num_key)

      for num_key in sorted(num_keys):
         station = "AMS" + str(num_key)
         print(station, station_report[station]['obs'], station_report[station]['mse'], station_report[station]['sse'])
      for event in msd:
         event_id = event['event_id']
         stations = event['stations']
         print("MS", event_id, stations)

      ssd = sorted(ssd, key=lambda x: x['start_datetime'][0], reverse=False)
      for event in ssd:
         files = event['files']
         stations = event['stations']
         #print("SS", stations, event['start_datetime'])

      mc_xs = []
      mc_ys = []
      mc_ays = []
      for key in meteor_counts:
         mc_xs.append(key)
         mc_ys.append(meteor_counts[key]['count'])
         station_count = len(meteor_counts[key]['stations'].keys())
         if station_count > 0:
            avg_count = meteor_counts[key]['count'] / station_count
            meteor_counts[key]['avg'] = avg_count 
         else:
            meteor_counts[key]['avg'] = 0
         mc_ays.append(meteor_counts[key]['count'])
        # print("TOTAL COUNT:", key, meteor_counts[key], meteor_counts[key]['avg'])
      rstations = {}
      for key in sorted(meteor_counts_stations.keys()):
         st, bin = key.split(".")
         if st not in rstations:
            rstations[st] = {}
            rstations[st][bin] = meteor_counts_stations[key]
         else:
            rstations[st][bin] = meteor_counts_stations[key]

      mc_report = []
      for key in rstations:
         hr = []
         for m in range(0,24):
            if str(m) in rstations[key]:
               hr.append(rstations[key][str(m)])
            else:
               hr.append(0)
         rstations[key] = hr

         print(key, rstations[key], int(np.sum(rstations[key])))
         mc_report.append((key,rstations[key],int(np.sum(rstations[key]))))
      print("TOTAL", mc_ys)
      mc_report.append(("TOTAL",mc_ys,int(np.sum(mc_ys))))
      mc_report_html = "<center><h2>Meteor Counts from reporting stations on " + date + "</h2>" 
      mc_report_html += "<table id='meteor_count_list' class='display' ><thead>"
      mc_report_html += "<tr><th>Station</th>"
      for d in range(0,24):
         mc_report_html += "<th>" + str(d) + "</th>"
      mc_report_html += "<th>Total</th></tr></thead><tbody>"

      for row in mc_report:
         sid, hours, total = row
         hour_cells = ""
         for hour in hours:
            hour_cells += "<td width=3%>" + str(hour) + "</td>"
            station_link = """ <a href="javascript:station_obs('https://archive.allsky.tv/EVENTS/""" + year + """/""" + month + """/""" + day + """/OBS/"""  + sid + """.html', '""" + sid + """','""" + date + """')"> """ 
         mc_report_html += "<tr><td>" + station_link + sid + "</a></td>" + hour_cells + "<td>" + str(total) + "</td></tr>"
      mc_report_html += "</tbody></table>"

      save_json_file(self.event_dir + self.date + "_METEOR_COUNTS.json", mc_report)
      print(self.event_dir + self.date + "_METEOR_COUNTS.json")
      import matplotlib
      #matplotlib.use('TkAgg')
      from matplotlib import pyplot as plt
      #plt.scatter(dom_obj['oxs'], dom_obj['oys'])
      plt.plot(mc_xs, mc_ys, c='red')
      plt.savefig("meteor_counts.png")
      cloud_dir = self.event_dir.replace("/mnt/ams2", "/mnt/archive.allsky.tv")

      solved_ev = []
      unsolved_ev = []
      failed_ev = []
      out = ""
      for row in msd:
         print(row.keys())
         if "solution" not in row:
            print("NO SOLUTION")
            unsolved_ev.append(row)
         else:
            if row['solve_status'] == "SUCCESS": 
               print("SOLVED!")
               solved_ev.append(row)
            else:
               print("FAILED!")
               failed_ev.append(row)
      print("Solved:", len(solved_ev))
      print("Un-Solved:", len(unsolved_ev))
      print("Failed:", len(failed_ev))

      mse_list_html = self.make_mse_solved_html(solved_ev)
      mse_list_solved_html = "<p>&nbsp;</p><h3>Observations for Solved Meteor Events </h3><p>Some of these observations might still need help with point refinement and/or astrometric calibration. </p>" + self.make_mse_failed_html(solved_ev, "green")

      mse_list_failed_html = "<p>&nbsp;</p><h3>Observations for Failed Meteor Events</h3><p>These observations need help with point picking and/or astrometric calibration. </p>" + self.make_mse_failed_html(failed_ev,"red")
      mse_list_unsolved_html = "<p>&nbsp;</p><h3>Observations for Unsolved Events</h3> <p>These observations have not been run or could not be run. Some might not be meteors at all. </p>" + self.make_mse_failed_html(unsolved_ev, "red")

      #ssd = sorted(ssd, key=lambda x: x['start_datetime'][0], reverse=False)
      ssd = sorted(ssd, key=lambda x: x['stations'][0], reverse=False)

      sse_list_html = "<p>&nbsp;</p><h3>Single Station Meteor Observations</h3> <p>Some of these observations might not be meteors. </p>" + self.make_sse_group_html(ssd, "white")

      mse_stats = """
      <p> &nbsp; </p>
      <h2>Multi-Station Events for """ + date + """</h2>
       <div id='mse_stats'>
          Total Multi-Station Events: """ + str(len(msd)) + """
          Solved: """ + str(len(solved_ev)) + """
          Failed: """ + str(len(failed_ev)) + """
          Unsolved: """ + str(len(unsolved_ev)) + """
       </div>

      """
      mse_report_html = "" + mse_stats + mse_list_html
     # + mse_list_html
      #for row in solved_ev:
      #   print(row.keys())
      for row in ssd:
         print(row)

      print("Meteor Count REPORT", mc_report_html)
      js = """
             <script>

                $('#date_nav').change(function()
                {
                val = $('#date_nav').val()
                el = val.split("-")
                year = el[0]
                mon = el[1]
                day = el[2]
                url = "/EVENTS/" + year + "/" + mon + "/" + day + "/report.html"
                window.location.href = url
                });

             $(document).ready( function () {
                $('table.display').dataTable();

             })


             </script>
      """
      report_template = report_template.replace("{MC_REPORT}", mc_report_html)
      report_template = report_template.replace("{MSE_REPORT}", mse_report_html)

      #report_template = report_template.replace("{SSE_LIST}", sse_list_html)
      sdate = date.replace("_","-")
      report_template = report_template.replace("{DATE}", sdate)
      report_template = report_template.replace("{JS}", js)

      out = open(self.edir + "report.html", "w")
      out.write(report_template)
      print(self.edir + "report.html")

      out.close()
      #cmd = "rsync -auv " + self.edir + "report.html " + self.cdir
      #print(cmd)
      #os.system(cmd)

      # make multi station events report
      # make single station obs report

      cmd = "cp " + self.edir + "report.html " + cloud_dir 
      print(cmd)
      os.system(cmd)
      print("YOYO")
      #MIKE!!!
      cmd = "rsync -auv " + self.event_dir + "* " + cloud_dir 
      #os.system(cmd)
      
      #plt.show()
         
      # STATION TOTAL OBS TOTAL SSE TOTAL MSE
   def make_mse_solved_html (self, solved_ev):
      #dict_keys(['start_datetime', 'files', 'lats', 'solve_status', 'stations', 'lons', 'event_id', 'event_day', 'solution', 'obs', 'total_stations'])
      #dict_keys(['duration', 'traj', 'shower', 'event_id', 'rad', 'plot', 'sol_dir', 'simple_solve', 'kml', 'orb'])
      out = "<h3>Successfully Solved </h3>"
      out += "<table id='event_list' class='display'><thead>"
      out += "<tr> <th>Event ID</th> <th>Stations</th> <th>Dur</th> <th>Vel</th> <th>End Alt</th> <th>Shower</th> <th>a</th> <th>e</th> <th>i</th> <th>peri</th> <th>q</th> <th>ls</th> <th>M</th> <th>P</th></tr></thead><tbody>"
      for ev in solved_ev:
         ev_id = ev['event_id']
         stations = list(set(ev['stations']))
         st_str = ""
         for st in sorted(stations):
            print("ST:", st)
            st = st.replace("AMS", "")
            if st_str != "":
               st_str += ","
            st_str += st
         print("STATIONS:", stations)
         print("STATIONS STRING:", st_str)
         sol = ev['solution']
         traj = ev['solution']['traj']
         orb = ev['solution']['orb']
         shower = ev['solution']['shower']
         v_init = str(int(traj['v_init']/1000))  + " km/s"
         e_alt = str(int(traj['end_ele']/1000))  + " km"
         shower_code = shower['shower_code']
         dur = sol['duration']
         if orb['a'] is None or orb['a'] == "":
            orb['a'] = 0
            orb['e'] = 0
            orb['i'] = 0
            orb['peri'] = 0
            orb['q'] = 0
            orb['la_sun'] = 0
            orb['mean_anomaly'] = 0
            orb['T'] = 0
         ev_link =  """ <a href="javascript:make_event_preview('""" + ev_id + """')">"""
         ev_row = "<tr> <td ><span id='" + ev_id + "'>" + ev_link + "{:s}</a></span></td> <td>{:s}</td> <td>{:s}</td> <td>{:s}</td> <td>{:s}</td> <td>{:s}</td> <td>{:0.2f}</td> <td>{:0.2f}</td> <td>{:0.2f}</td> <td>{:0.2f}</td> <td>{:0.2f}</td> <td>{:0.2f}</td> <td>{:0.2f}</td> <td>{:0.2f}</td></tr>".format(ev_id, st_str, str(dur), str(v_init), str(e_alt), str(shower_code),float(orb['a']),float(orb['e']),float(orb['i']),float(orb['peri']),float(orb['q']),float(orb['la_sun']),float(orb['mean_anomaly']),float(orb['T']))
         out += ev_row
      out += "</tbody></table>"


      return(out)

   def make_sse_group_html (self, events, border_color):
      out = "<div class='container-fluid'>"
      last_station = None
      for ev in events:

         stations = sorted(list(set(ev['stations'])))
         st_str = ""
         for st in stations:
            if st_str != "":
               st_str += ", "
            st_str += st

         obs = ""
         obs_images = ""
         fc = 0
         for i in range(0,len(ev['stations'])):
            station = ev['stations'][i]
            obs_file = ev['files'][i]
            if last_station != station:
               out += "<div style='clear:both'></div>"
               if last_station is None:
                  out += "<h4>" + station + "</h4><div>" 
               else:
                  out += "</div><div style='clear:both'></div>"
                  out += "<h4>" + station + "</h4><div>" 
            print("THIS ? LAST:", station, last_station)
            if True:
               if obs != "":
                  obs += ", "
               obs += station + "_" + obs_file + " "
               if fc == 0 and "event_id" in ev:
                  print("EV:", ev)
                  desc_text = ev['event_id']
               else:
                  desc_text = ""
               prev_file, prev_html = self.make_obs_image(station, obs_file, border_color, desc_text)
               obs_images += prev_html
               fc += 1

            last_station = station
            out += obs_images 
     
      out += "</div><div style='clear:both'></div>"
      return(out)

   def make_mse_failed_html (self, events, border_color):
      out = "<table width=80%>"
      for ev in events:
         
         stations = sorted(list(set(ev['stations'])))
         st_str = ""
         for st in stations:
            if st_str != "":
               st_str += ", "
            st_str += st

         obs = ""
         obs_images = ""
         fc = 0
         for i in range(0,len(ev['stations'])):
            station = ev['stations'][i]
            obs_file = ev['files'][i]
            if True:
               if obs != "":
                  obs += ", "
               obs += station + "_" + obs_file + " " 
               if fc == 0 and "event_id" in ev:
                  print("EV:", ev)
                  desc_text = ev['event_id']
               else:
                  desc_text = ""
               prev_file, prev_html = self.make_obs_image(station, obs_file, border_color, desc_text)
               obs_images += prev_html
               fc += 1
         out += "<tr><td>" + obs_images + "</td></tr>"
      out += "</table>"
      return(out)

   def make_obs_image(self, station_id,sd_video_file,border_color,desc_text):
      year = sd_video_file[0:4]
      day = sd_video_file[0:10]
      img_link = "https://archive.allsky.tv/" + station_id + "/METEORS/" + year + "/" + day + "/" + station_id + "_" + sd_video_file
      img_link = img_link.replace(".mp4", "-prev.jpg")
      roi_link = img_link.replace(".mp4", "-ROI.jpg")
      data_id = station_id + ":" + sd_video_file
      obs_key = station_id + "_" + sd_video_file
      if obs_key not in self.good_obs_keys or obs_key in self.rejects:
         opacity = ".5"
      else:
         opacity = "1"
      img_html = """
         <div class='obs_thumb' data-id='""" + data_id + """' style="float: left; opacity: """ + opacity + """; border: 1px """ + border_color + """ solid; padding: 0px; margin: 10px; solid; background-image: url('""" + img_link + """'); background-repeat: no-repeat; background-size: 100%; height: 180px; width: 320px; "><span style='text-shadow: 2px 2px #000000; color: #FFFFFF; font-size: 10px;'>""" + station_id + " " + desc_text +  """</p></div>
      """


      return(img_link, img_html)

   def make_mse_unsolved_html (self, events):
      out = "<h3>Unsolved Events</h3>"
      for ev in events:
         print(ev.keys)
      return(out)

   def find_bin(self, date_str):
      d,t = date_str.split(" ")
      h,m,s = t.split(":")
      mi = int(m)
      hi = int(h)
      b = None
      if 0 <= mi < 15:
         b = 1
      if 15 <= mi < 30:
         b = 2
      if 30 <= mi < 45:
         b = 3 
      if 45 <= mi < 60:
         b = 4 
      if b is None:
         print("ERROR:", date_str)
      bin = str(hi) + "." + str(b)
      bin = str(hi) 
      return(bin)

   def update_existing_event(self ):
      print("UPDATE EVENT???")

   def delete_existing_event(self):
      print("DELETE EVENT???")

   def insert_new_event(self, event):
      print("INSERT NEW EVENT:", event)
      #if "event_id" in event:
      #   event_id = event['event_id']
      #else:
      #   event_id = None
      if True:
         event_id = event['event_id']
         ev_str = str(min(event['start_datetime']))
         if "." in ev_str:
            ev_dt = datetime.datetime.strptime(ev_str, "%Y-%m-%d %H:%M:%S.%f")
         else:
            ev_dt = datetime.datetime.strptime(ev_str, "%Y-%m-%d %H:%M:%S")
         event_id = ev_dt.strftime('%Y%m%d_%H%M%S')
         event_day = ev_dt.strftime('%Y_%m_%d')
         event['event_id'] = event_id
         event['event_day'] = event_day
         # register the event in the dyna db please.
         print("INSERT METEOR EVENT!", event_id, "insert_meteor_event(None, event_id, event)")
         existing_event_data = get_event(self.dynamodb, event_id)
         if len(existing_event_data) == 0:
            existing_event_data = None
         print("EXISTING BEFORE INSERT!", existing_event_data)
         if existing_event_data is None:
            insert_meteor_event(None, event_id, event)
         else:
            print("THIS EVENT ALREADY EXISTS AND THIS INSERT IS A PROBLEM!")
            print("UNLESS THE INFO HAS CHANGED!")
            changed = 0
            if len(event['stations']) != len(existing_event_data['stations']):
               print("LOOKS LIKE A LEGIT UPDATE!")
               changed = 1
            if changed == 1:
               print("EXISTING EVENT, BUT CHANGES EXIST!")
               min_dist = self.compare_events(event,existing_event_data)
               if min_dist > 650:
                  event_id += "_D"
                  print("DUPE TIME EVENT DIST THRESH NOT MET!", event_id, min_dist)
               insert_meteor_event(None, event_id, event)
            print("IN ED:", event)
            print("EXISTING ED:", existing_event_data)

   def compare_events(self,event1,event2):
      avg_lat1 = np.mean(event1['lats'])
      avg_lon1 = np.mean(event1['lons'])
      avg_lat2 = np.mean(event2['lats'])
      avg_lon2 = np.mean(event2['lons'])

      min_lat1 = min(event1['lats'])
      min_lon1 = min(event1['lons'])
      min_lat2 = min(event2['lats'])
      min_lon2 = min(event2['lons'])

      max_lat1 = max(event1['lats'])
      max_lon1 = max(event1['lons'])
      max_lat2 = max(event2['lats'])
      max_lon2 = max(event2['lons'])


      event_diff_dist = dist_between_two_points(avg_lat1, avg_lon1, avg_lat2, avg_lon2)
      event_diff_min_dist = dist_between_two_points(min_lat1, min_lon1, min_lat2, min_lon2)
      event_diff_max_dist = dist_between_two_points(max_lat1, max_lon1, max_lat2, max_lon2)
      print("MEAN DISTANCE BETWEEN TWO EVENTS IS:", event_diff_dist)
      print("MIN LAT/LON DISTANCE BETWEEN TWO EVENTS IS:", event_diff_min_dist)
      print("MAX LAT/LON DISTANCE BETWEEN TWO EVENTS IS:", event_diff_max_dist)
      #dist_between_events = calc_dist((avg_lat1,avg_lat2),(
      return(min([event_diff_dist,event_diff_min_dist,event_diff_max_dist]))

   def check_existing_event(self, ob=None):
      found_event = None
      for event in self.all_events:
         if "." in min(event['start_datetime']):
            ev_dt = datetime.datetime.strptime(min(event['start_datetime']), "%Y-%m-%d %H:%M:%S.%f") 
         else:
            ev_dt = datetime.datetime.strptime(min(event['start_datetime']), "%Y-%m-%d %H:%M:%S") 
         if "event_start_time" not in ob:
            ob_dt = self.starttime_from_file(ob['sd_video_file'])
            ob['event_start_time'] = ob_dt.strftime( "%Y-%m-%d %H:%M:%S.%f")
            ev_dt = ob_dt 
            #ob['event_status_time'] = ob_dt
            #print("NO EVENT TIME!", event['event_id'], ob_dt, ob)
            #continue
         if "_" in ob['event_start_time']:
            el = ob['event_start_time'].split("_")
            print("BAD TIME!", el)
            y,m,d,h,mn,s = el[0:6]
            if "." in s:
               ss, ms = s.split(".")
               ms = ms[0:3]
               s = ss + "." + ms
            ob['event_start_time'] = y + "-" + m + "-" + d + " " + h + ":" + mn + ":" + s

         if ob['event_start_time'] == "" or ob['event_start_time'] == " " :
            ob_dt = self.starttime_from_file(ob['sd_video_file'])
            ob['event_start_time'] = ob_dt.strftime( "%Y-%m-%d %H:%M:%S.%f")
         #if " " not in ob['event_start_time']:
         #   # no date on time var add it
         #   print("DEBG:", ob['event_start_time'])
         #   
         #   date = ob['sd_video_file'][0:10]
         #   date = date.replace("_", "-")
         #   ob['event_start_time'] = date + " " + ob['event_start_time']
         if "." in ob['event_start_time']:
            if " " not in ob['event_start_time']:
               date = ob['sd_video_file'][0:10]
               date = date.replace("_", "-")
               ob['event_start_time'] = date + " " + ob['event_start_time']

            ob_dt = datetime.datetime.strptime(ob['event_start_time'], "%Y-%m-%d %H:%M:%S.%f")
         else:
            if ob['event_start_time'] == "":
               ob_dt = self.starttime_from_file(ob['sd_video_file'])
            else:
               ob_dt = datetime.datetime.strptime(ob['event_start_time'], "%Y-%m-%d %H:%M:%S")
         time_diff = (ob_dt - ev_dt).total_seconds() 
         if -5 <= time_diff < 5:
            in_range = self.obs_inrange(event, ob)
            if in_range != 0:
               found_event = event['event_id']
               #print("EV RANGE/TIME:", in_range, time_diff, ob['event_start_time'], min(event['start_datetime']))
      return(found_event)

   def obs_inrange(self, event, ob):
      inrange = 0
      for i in range(0,len(event['stations'])):
         lat = event['lats'][i]
         lon = event['lats'][i]
         s_lat = self.station_loc[ob['station_id']][0]
         s_lon = self.station_loc[ob['station_id']][1]
         station_dist = dist_between_two_points(s_lat, s_lon, lat, lon)
         if station_dist < 350:
            inrange = 1
      return(inrange)

   def get_obs_datetime(self, obs):
      if "meteor_frame_data" not in obs:
         obs_dt = self.starttime_from_file(obs['sd_video_file'])
         obs['meteor_frame_data'] = []
      if len(obs['meteor_frame_data']) > 0:
         obs_time = obs['meteor_frame_data'][0][0]
         if "_" in obs_time:
            print("BAD TIME!", obs_time)
            el = obs_time.split("_")
            print("EL:", el)
            print("BAD TIME!", el)
            y,m,d,h,mn,s = el[0:6]
            if "." in s:
               ss, ms = s.split(".")
               ms = ms[0:3]
               s = ss + "." + ms
               obs_time = y + "-" + m + "-" + d + " " + h + ":" + mn + ":" + s
            else:
               obs_time = y + "-" + m + "-" + d + " " + h + ":" + mn + ":" + s + ".000"
            print("NEW TIME", obs_time)


         if "." in obs_time:
            obs_dt = datetime.datetime.strptime(obs_time, "%Y-%m-%d %H:%M:%S.%f")
         else:
            obs_dt = datetime.datetime.strptime(obs_time, "%Y-%m-%d %H:%M:%S")
      else:
         obs_dt = self.starttime_from_file(obs['sd_video_file'])



      return(obs_dt)

   def starttime_from_file(self, filename):
      (f_datetime, cam, f_date_str,fy,fmon,fd, fh, fm, fs) = convert_filename_to_date_cam(filename)
      trim_num = get_trim_num(filename)
      extra_sec = int(trim_num) / 25
      event_start_time = f_datetime + datetime.timedelta(0,extra_sec)
      return(event_start_time)


   def check_make_events(self,obs_time, obs, events):
      if len(events) == 0:
         event = {}
         event['stations'] = []
         event['files'] = []
         event['start_datetime'] = []
         event['lats'] = []
         event['lons'] = []
         event['stations'].append(obs['station_id'])
         event['files'].append(obs['sd_video_file'])
         event['start_datetime'].append(obs_time)
         event['lats'].append(obs['lat'])
         event['lons'].append(obs['lon'])
         event = self.clean_event(event)

         events.append(event)
         return(events)

      new_events = []
      # check if this obs is part of an existing event
      ec = 0
      for event in events:
         found = 0
         times = event['start_datetime']
         for i in range(0, len(event['stations'])):
            e_time = event['start_datetime'][i]
            if isinstance(e_time,str) is True:
               if "." in e_time:
                  e_time = datetime.datetime.strptime(e_time, "%Y-%m-%d %H:%M:%S.%f")
               else:
                  e_time = datetime.datetime.strptime(e_time, "%Y-%m-%d %H:%M:%S")


            station = event['stations'][i]
            lat = event['lats'][i]
            lon = event['lons'][i]
            time_diff = (obs_time - e_time).total_seconds()
            if abs(time_diff) < 5:
             
               station_dist = dist_between_two_points(obs['lat'], obs['lon'], lat, lon)
               if station_dist < 350:
                  new_event = dict(event)
                  new_event['stations'].append(obs['station_id'])
                  new_event['files'].append(obs['sd_video_file'])
                  new_event['start_datetime'].append(obs_time)
                  new_event['lats'].append(obs['lat'])
                  new_event['lons'].append(obs['lon'])
                  found = 1
                  events[ec] = new_event
                  return(events)
         ec += 1

      # if we got this far it must be a new obs not related to any existing events
      # so make a new event and add it to the list
      if True:
         event = {}
         event['stations'] = []
         event['files'] = []
         event['start_datetime'] = []
         event['lats'] = []
         event['lons'] = []
         event['stations'].append(obs['station_id'])
         event['files'].append(obs['sd_video_file'])
         event['start_datetime'].append(obs_time)
         event['lats'].append(obs['lat'])
         event['lons'].append(obs['lon'])
         events.append(event)

      return(events)

   def clean_event(self, event):
      #1 remove duplicate keys/obs
      #2 make sure all obs in the event still exist
      #3 Re-calculate the total number of stations
      #4 Delete the event if it is no longer valid (<2 unique stations)
      #4 return clean event
      #['start_datetime', 'files', 'lats', 'solve_status', 'stations', 'lons',
      print("ST:", event['stations'])
      print("FILE:", event['files'])
      print("DATES:", event['start_datetime'])
      print("LATS:", event['lats'])
      print("LONS:", event['lons'])
      obs_keys = {}
      for i in range(0, len(event['stations'])):
         ok = event['stations'][i] + "_" + event['files'][i]
         obs_keys[ok] = [event['start_datetime'][i], event['lats'][i], event['lons'][i]]

      new_stations = []
      new_files = []
      new_start_datetime = []
      new_lats = []
      new_lons = []
      for key in obs_keys:
         el = key.split("_")
         st = el[0]
         vid = key.replace(st + "_", "")
         sdt, lat, lon = obs_keys[key]
         new_stations.append(st)
         new_files.append(vid)
         new_start_datetime.append(sdt)
         new_lats.append(lat)
         new_lons.append(lon)

      print("BEFORE:", len(event['stations']))
      print("AFTER:", len(new_stations))
      print(new_stations)
      print(new_files)
      print(new_start_datetime)
      print(event.keys())
      event['total_stations'] = len(set(new_stations))
      event['stations'] = new_stations
      event['files'] = new_files
      event['start_datetime'] = new_start_datetime
      event['lats'] = new_lats
      event['lons'] = new_lons
      return(event)

