from lib.PipeUtil import cfe, load_json_file, save_json_file, convert_filename_to_date_cam, get_trim_num
from lib.PipeManager import dist_between_two_points
from DynaDB import get_event, get_obs, search_events, update_event, update_event_sol, insert_meteor_event, delete_event
import numpy as np
import subprocess
import time
import datetime
import os
import redis
import json

class EventRunner():
   def __init__(self, cmd=None, day=None, month=None,year=None,date=None, use_cache=0):
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
            print(self.all_stations_file)
            self.all_stations = load_json_file(self.all_stations_file)
         else:
            self.all_stations = None

         print(len(self.all_stations), "TOTAL STATIONS")

         self.station_loc = {}
         for data in self.all_stations:
            sid = data[0]
            lat = data[1]
            lon = data[2]
            self.station_loc[sid] = [lat,lon]

   def update_missing_wmpl_keys(self):
      ev_keys = self.r.keys("E*")
      for ev_key in sorted(ev_keys, reverse=True):
         event_id = ev_key.replace("E:", "")
         evdata = self.r.get(ev_key)
         #print(ev_key, evdata)
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
                        print("EV:", evdata['wmpl_id'])
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
         #print(ev_key, evdata)
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

         print(ev_key, evdata.keys())
         if "stations" not in evdata:
            print("PROBLEM EVENT:", ev_key, evdata)
            #input()
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
         print(event['event_id'], event['solve_status'])
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
      print("SINGLE :", self.single_station_obs)
      new_events = []
      for ob in self.single_station_obs:
         found_existing = self.check_existing_event(ob) 
         print(ob['station_id'], found_existing)
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
         cmd = "cp " + self.single_station_file + " " + self.cloud_all_stations_file
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
         print("START TIME!:", ob['event_start_time'])

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
            print("EVENT START TIME IS BLANK!", ob)
            ob_dt = self.starttime_from_file(ob['sd_video_file'])
            print("OBDT:", ob_dt)
            ob['event_start_time'] = ob_dt.strftime( "%Y-%m-%d %H:%M:%S.%f")
         #if " " not in ob['event_start_time']:
         #   # no date on time var add it
         #   print("DEBG:", ob['event_start_time'])
         #   
         #   date = ob['sd_video_file'][0:10]
         #   date = date.replace("_", "-")
         #   ob['event_start_time'] = date + " " + ob['event_start_time']
         if "." in ob['event_start_time']:
            print(ob['event_start_time'])
            if " " not in ob['event_start_time']:
               date = ob['sd_video_file'][0:10]
               date = date.replace("_", "-")
               ob['event_start_time'] = date + " " + ob['event_start_time']

            ob_dt = datetime.datetime.strptime(ob['event_start_time'], "%Y-%m-%d %H:%M:%S.%f")
         else:
            if ob['event_start_time'] == "":
               ob_dt = self.starttime_from_file(ob['sd_video_file'])
            else:
               print("EVS:", ob['event_start_time'])
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
