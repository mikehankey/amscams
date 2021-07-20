from lib.PipeUtil import cfe, load_json_file, save_json_file, convert_filename_to_date_cam, get_trim_num
from lib.PipeManager import dist_between_two_points
from DynaDB import get_event, get_obs, search_events, update_event, update_event_sol, insert_meteor_event, delete_event
import numpy as np
import subprocess
import time
import datetime
import os
import redis
import simplejson as json
import boto3
from decimal import Decimal

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return json.JSONEncoder.default(self, obj)

class EventRunner():
   def __init__(self, cmd=None, day=None, month=None,year=None,date=None, use_cache=0):
      self.dynamodb = boto3.resource('dynamodb')
      admin_conf = load_json_file("admin_conf.json")
      self.r = redis.Redis(admin_conf['redis_host'], port=6379, decode_responses=True)
      self.cmd = cmd
      self.date = date 
      if date is not None:
         year,month,day = date.split("_")
      self.event_dict = {}
      if day is not None:
         self.day = day 
         self.month = month 
         self.year = year 
         self.event_dir = "/mnt/ams2/EVENTS/" + self.year + "/" + self.month + "/" + self.day + "/" 
         self.cloud_event_dir = "/mnt/archive.allsky.tv/EVENTS/" + self.year + "/" + self.month + "/" + self.day + "/" 
         if cfe(self.event_dir, 1) == 0:
            os.makedirs(self.event_dir)
         if cfe(self.cloud_event_dir, 1) == 0:
            os.makedirs(self.cloud_event_dir)
         self.all_events_file = "/mnt/ams2/EVENTS/" + self.year + "/" + self.month + "/" + self.day + "/" + self.date + "_ALL_EVENTS.json"  
         self.all_events_index_file = "/mnt/ams2/EVENTS/" + self.year + "/" + self.month + "/" + self.day + "/" + self.date + "_ALL_EVENTS_INDEX.json"  
         self.all_obs_file = "/mnt/ams2/EVENTS/" + self.year + "/" + self.month + "/" + self.day + "/" + self.date + "_ALL_OBS.json"  
         self.all_stations_file = "/mnt/ams2/EVENTS/" + self.year + "/" + self.month + "/" + self.day + "/" + self.date + "_ALL_STATIONS.json"  
         self.single_station_file =  self.event_dir + self.date + "_ALL_SINGLE_STATION_METEORS.json"

         self.cloud_all_events_file = "/mnt/archive.allsky.tv/EVENTS/" + self.year + "/" + self.month + "/" + self.day + "/" + self.date + "_ALL_EVENTS.json"  
         self.cloud_all_events_index_file = "/mnt/archive.allsky.tv/EVENTS/" + self.year + "/" + self.month + "/" + self.day + "/" + self.date + "_ALL_EVENTS_INDEX.json"  
         self.cloud_all_obs_file = "/mnt/archive.allsky.tv/EVENTS/" + self.year + "/" + self.month + "/" + self.day + "/" + self.date + "_ALL_OBS.json"  
         self.cloud_all_stations_file = "/mnt/archive.allsky.tv/EVENTS/" + self.year + "/" + self.month + "/" + self.day + "/" + self.date + "_ALL_STATIONS.json"  
         self.cloud_single_stations_file = "/mnt/archive.allsky.tv/EVENTS/" + self.year + "/" + self.month + "/" + self.day + "/" + self.date + "_ALL_SINGLE_STATION_METEORS.json"  


         if cfe(self.all_events_file) == 1:
            self.all_events = load_json_file(self.all_events_file)
            for event in self.all_events:
               self.event_dict[event['event_id']] = event
         else:
            print("ERROR: NOT FOUND:", self.all_events_file)
            self.all_events = []

         # DOWNLOAD DYNA DATA IF IT DOESN'T EXIST
         # OR IF THE CACHE FILE IS OLDER THAN X MINUTES
         if cfe(self.all_events_file) == 0:
            print("ERROR MISSING:", self.all_events_index_file) 
         if use_cache == 0:
            os.system("./DynaDB.py udc " + self.date)

         if cfe(self.all_events_index_file) == 1:
            self.all_events_index = load_json_file(self.all_events_index_file)
         else:
            self.all_events_index = None
         if cfe(self.all_obs_file) == 1:
            self.all_obs = load_json_file(self.all_obs_file)
         else:
            self.all_obs = None
         if cfe(self.all_stations_file) == 1:
            self.all_stations = load_json_file(self.all_stations_file)
         else:
            self.all_stations = None


         self.station_loc = {}
         for data in self.all_stations:
            sid = data[0]
            lat = data[1]
            lon = data[2]
            self.station_loc[sid] = [lat,lon]

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

   def make_all_obs_index(self, date):
      # this will make a key-only file of ALL obs in the redis DB (which should also include all obs in the dynadb
      # this file can be used for fast indexing of UIs and also reconciliation jobs on the host machines 
      if date is None:
         oi_keys = self.r.keys("OI:*2021_07*")
      else:
         oi_keys = self.r.keys("OI:*" + date + "*")
      all_obs_by_station ={}
      all_obs_by_day ={}
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
      #save_json_file("/mnt/ams2/EVENTS/OBS/ALL_OBS_BY_STATION.json", all_obs_by_station)
      #save_json_file("/mnt/ams2/EVENTS/OBS/ALL_OBS_BY_DAY.json", all_obs_by_day)

      # NOW MAKE 1 FILE FOR EACH DAY AND 1 FILE FOR EACH STATION
      day_dir = "/mnt/ams2/EVENTS/OBS/DAYS/"
      station_dir = "/mnt/ams2/EVENTS/OBS/STATIONS/"
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
         save_json_file(day_file, all_obs_by_day[key]['obs'], True)
         print("Saving...", day_file)

         if date is not None:
            cmd = "cp " + day_dir + "*" + date + "*" + " " + cloud_day_dir
            print(cmd)
            os.system(cmd)
      #cmd = "cp " + station_dir + "*" + " " + cloud_station_dir
      #os.system(cmd)

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

      save_json_file("/mnt/ams2/EVENTS/ALL_EVENTS_INDEX.json", all_events, True)
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
      save_json_file("/mnt/ams2/EVENTS/ALL_EVENTS_INDEX_SOLVED.json", solved, True)
      save_json_file("/mnt/ams2/EVENTS/ALL_EVENTS_INDEX_FAILED.json", failed, True)
      save_json_file("/mnt/ams2/EVENTS/ALL_EVENTS_INDEX_UNSOLVED.json", unsolved, True)
      cmd = "cp /mnt/ams2/EVENTS/ALL_EVENTS* /mnt/archive.allsky.tv/EVENTS/"
      os.system(cmd)

      #exit()

   def all_event_stats(self):
      all_events_file = "/mnt/ams2/EVENTS/ALL_EVENTS_INDEX.json"
      event_orb_file = "/mnt/ams2/EVENTS/ALL_EVENTS_INDEX_ORBS.json"

      solved_events_file = "/mnt/ams2/EVENTS/ALL_EVENTS_INDEX_SOLVED.json"
      failed_events_file = "/mnt/ams2/EVENTS/ALL_EVENTS_INDEX_FAILED.json"
      unsolved_events_file= "/mnt/ams2/EVENTS/ALL_EVENTS_INDEX_UNSOLVED.json"

      solved_ids_file = "/mnt/ams2/EVENTS/ALL_EVENTS_IDS_SOLVED.json"
      failed_ids_file = "/mnt/ams2/EVENTS/ALL_EVENTS_IDS_FAILED.json"
      unsolved_ids_file= "/mnt/ams2/EVENTS/ALL_EVENTS_IDS_UNSOLVED.json"

      event_stats_file = "/mnt/ams2/EVENTS/ALL_EVENTS_INDEX_STATS.json"
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

      solved_ids_file = "/mnt/ams2/EVENTS/ALL_EVENTS_IDS_SOLVED.json"
      failed_ids_file = "/mnt/ams2/EVENTS/ALL_EVENTS_IDS_FAILED.json"
      unsolved_ids_file= "/mnt/ams2/EVENTS/ALL_EVENTS_IDS_UNSOLVED.json"


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
      save_json_file("/mnt/ams2/EVENTS/ALL_STATIONS_EVENTS.json", all_station_events, True)
      for station_id in all_station_events:
         stjsf = "/mnt/ams2/EVENTS/ALL_EVENTS_" + station_id + ".json"
         stjsf_zip = "/mnt/ams2/EVENTS/ALL_EVENTS_" + station_id + ".json.gz"
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
               self.single_station_obs.append(ob)
            else:
               print("THIS OB BELONGS TO THIS EVENT!", ob['station_id'], ob['sd_video_file'], event_id)
               exit()

      for event in self.all_events:
         print(event['event_id'], event['total_stations'], event['solve_status'])
      print("MS OBS:", len(self.multi_station_obs))
      print("SS OBS:", len(self.single_station_obs))

   def update_events_for_day(self):
      new_events = []
      for ob in self.single_station_obs:
         found_existing = self.check_existing_event(ob) 
         if found_existing is not None:
            print("AN EVENT FOR THIS OBS WAS FOUND:", found_existing) 
         else: 
            obs_time = self.get_obs_datetime(ob)

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


   def EOD_report(self, date):
      report_template_file = "allsky.tv/event_template.html"
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
      stations_link = "https://archive.allsky.tv" + self.vdir + date + "_ALL_STATIONS.json"

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
      ssd = load_json_file(self.single_station_file)
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
               station_report[station]['mse'] = 0
               station_report[station]['sse'] = 1
            else:
               station_report[station]['obs'] += 1
               station_report[station]['mse'] += 0
               station_report[station]['sse'] += 1
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
         for m in range(0,23):
            if str(m) in rstations[key]:
               hr.append(rstations[key][str(m)])
            else:
               hr.append(0)
         rstations[key] = hr

         print(key, rstations[key], int(np.sum(rstations[key])))
         mc_report.append((key,rstations[key],int(np.sum(rstations[key]))))
      print("TOTAL", mc_ys)
      mc_report.append(("TOTAL",mc_ys,int(np.sum(mc_ys))))

      mc_report_html = "<table>"
      for row in mc_report:
         sid, hours, total = row
         hour_cells = ""
         for hour in hours:
            hour_cells += "<td>" + str(hour) + "</td>"
         mc_report_html += "<tr><td>" + sid + "</td>" + hour_cells + "<td>" + str(total) + "</td></tr>"
      mc_report_html = "</table>"

      save_json_file(self.event_dir + self.date + "_METEOR_COUNTS.json", mc_report)
      print(self.event_dir + self.date + "_METEOR_COUNTS.json")
      import matplotlib
      #matplotlib.use('TkAgg')
      from matplotlib import pyplot as plt
      #plt.scatter(dom_obj['oxs'], dom_obj['oys'])
      plt.plot(mc_xs, mc_ys, c='red')
      plt.savefig("meteor_counts.png")
      cloud_dir = self.event_dir.replace("/mnt/ams2", "/mnt/archive.allsky.tv")


      report_template = report_template.replace("{MC_REPORT}", mc_report_html)
      out = open(self.edir + "report.html", "w")
      out.write(report_template)
      print(self.edir + "report.html")

      out.close()
      #cmd = "rsync -auv " + self.edir + "report.html " + self.cdir
      #print(cmd)
      #os.system(cmd)

      cmd = "rsync -auv " + self.event_dir + "* " + cloud_dir 
      print(cmd)
      os.system(cmd)
      
      #plt.show()
         
      # STATION TOTAL OBS TOTAL SSE TOTAL MSE

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
      print("UPDATE EVENT!")

   def delete_existing_event(self):
      print("DELETE EVENT!")

   def insert_new_event(self, event):
      if "event_id" in event:
         event_id = event['event_id']
      else:
         event_id = None
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
         print(event_id, "insert_meteor_event(None, event_id, event)")
         insert_meteor_event(None, event_id, event)


   def check_existing_event(self, ob=None):
      found_event = None
      for event in self.all_events:
         if "." in min(event['start_datetime']):
            ev_dt = datetime.datetime.strptime(min(event['start_datetime']), "%Y-%m-%d %H:%M:%S.%f") 
         else:
            ev_dt = datetime.datetime.strptime(min(event['start_datetime']), "%Y-%m-%d %H:%M:%S") 
         if "event_start_time" not in ob:
            print("NO EVENT TIME!")
            continue
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
         if station_dist < 500:
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
               if station_dist < 500:
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
