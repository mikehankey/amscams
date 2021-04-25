from lib.PipeUtil import cfe, load_json_file, save_json_file, convert_filename_to_date_cam, get_trim_num
from lib.PipeManager import dist_between_two_points
from DynaDB import get_event, get_obs, search_events, update_event, update_event_sol, insert_meteor_event, delete_event

import datetime
import os

class EventRunner():
   def __init__(self, cmd=None, day=None, month=None,year=None,date=None):
      self.cmd = cmd
      self.date = date 
      if date is not None:
         year,month,day = date.split("_")
      self.event_dict = {}
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

      self.cloud_all_events_file = "/mnt/archive.allsky.tv/EVENTS/" + self.year + "/" + self.month + "/" + self.day + "/" + self.date + "_ALL_EVENTS.json"  
      self.cloud_all_events_index_file = "/mnt/archive.allsky.tv/EVENTS/" + self.year + "/" + self.month + "/" + self.day + "/" + self.date + "_ALL_EVENTS_INDEX.json"  
      self.cloud_all_obs_file = "/mnt/archive.allsky.tv/EVENTS/" + self.year + "/" + self.month + "/" + self.day + "/" + self.date + "_ALL_OBS.json"  
      self.cloud_all_stations_file = "/mnt/archive.allsky.tv/EVENTS/" + self.year + "/" + self.month + "/" + self.day + "/" + self.date + "_ALL_STATIONS.json"  


      if cfe(self.all_events_file) == 1:
         self.all_events = load_json_file(self.all_events_file)
         for event in self.all_events:
            self.event_dict[event['event_id']] = event
      else:
         print("ERROR: NOT FOUND:", self.all_events_file)
         self.all_events = None

      # DOWNLOAD DYNA DATA IF IT DOESN'T EXIST
      # OR IF THE CACHE FILE IS OLDER THAN X MINUTES
      if cfe(self.all_events_file) == 0:
         print("MISSING:", self.all_events_index_file) 
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
            event_id = self.check_existing_event(ob)
            if event_id == None:
               self.single_station_obs.append(ob)
            else:
               print("THIS OB BELONGS TO THIS EVENT!", ob['station_id'], ob['sd_video_file'], event_id)
               #print(event['stations'], event['files'])
               exit()
         #print(event_id, ob['station_id'], ob['sd_video_file'] )

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

            ob['lat'] = self.station_loc[ob['station_id']][0]
            ob['lon'] = self.station_loc[ob['station_id']][1]
            new_events = self.check_make_events(obs_time, ob, new_events)

      new_mse = []
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

      if len(new_mse) > 0: 
         os.system("./DynaDB.py udc " + self.date + " events")
         print("./DynaDB.py udc " + self.date + " events")
         print("Updated CACHE with latest DynaDB!")

      if len(new_mse) > 0 or cfe(self.cloud_all_events_file) == 0:
         cmd = "cp " + self.all_events_file + " " + self.cloud_all_events_file
         os.system(cmd)
         cmd = "cp " + self.all_obs_file + " " + self.cloud_all_obs_file
         os.system(cmd)
         cmd = "cp " + self.all_stations_file + " " + self.cloud_all_stations_file
         os.system(cmd)

      
      print("All events for today are made.")
      print(self.all_events_file)

      print(len(new_mse), "New events added.")



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
         if "." in ob['event_start_time']:
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
               print("EV RANGE/TIME:", in_range, time_diff, ob['event_start_time'], min(event['start_datetime']))
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
      if len(obs['meteor_frame_data']) > 0:
         obs_time = obs['meteor_frame_data'][0][0]
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

      #inp = input("A NEW EVENT NEEDS TO BE MADE!" )
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
