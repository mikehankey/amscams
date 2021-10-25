from lib.PipeUtil import cfe, load_json_file, save_json_file, convert_filename_to_date_cam, get_trim_num, get_file_info
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
from tabulate import tabulate

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return json.JSONEncoder.default(self, obj)

class EventReport():
   def __init__(self, cmd=None, day=None, month=None,year=None,date=None, use_cache=0):
      #os.system("./DynaDB.py udc " + date + " events")
      self.dynamodb = boto3.resource('dynamodb')
      admin_conf = load_json_file("admin_conf.json")
      self.admin_conf = admin_conf
      self.r = redis.Redis(admin_conf['redis_host'], port=6379, decode_responses=True)
      self.cmd = cmd
      self.date = date
      self.Y, self.M, self.D =  date.split("_")
      self.event_dir = "/mnt/ams2/EVENTS/" + self.Y + "/" + self.M + "/" + self.D + "/"
      self.event_cloud_dir = "/mnt/ams2/EVENTS/" + self.Y + "/" + self.M + "/" + self.D + "/"
      self.cloud_event_url = "https://archive.allsky.tv/EVENTS/" + self.Y + "/" + self.M + "/" + self.D + "/"

      # FILES THAT HOLD DATA
      # ALL_OBS
      # ALL_EVENTS
      # ALL_OBS_IDS
      # OBS_DICT
      # PLANE_PAIRS
      # MIN_REPORT
      # ALL_STATIONS
      # ALL_DEL
      self.all_obs_file = self.event_dir + self.date + "_ALL_OBS.json"
      self.event_kml_file = self.event_dir + self.date + "_ALL_EVENTS.kml"
      self.all_events_file = self.event_dir + self.date + "_ALL_EVENTS.json"
      self.event_dict_file = self.event_dir + self.date + "_EVENT_DICT.json"
      self.all_obs_ids_file = self.event_dir + self.date + "_ALL_OBS_IDS.json"
      self.obs_dict_file = self.event_dir + self.date + "_OBS_DICT.json"
      self.plane_pairs_file = self.event_dir + self.date + "_PLANE_PAIRS.json"
      self.min_report_file = self.event_dir + self.date + "_MIN_REPORT.json"
      self.all_stations_file = self.event_dir + self.date + "_ALL_STATIONS.json"
      self.all_del_file = self.event_dir + self.date + "_ALL_DEL.json"

      #if cfe(self.all_obs_file) == 1:
      #   self.all_obs = load_json_file(self.all_obs_file)
      #else:
      #   self.all_obs = {}
      if cfe(self.all_events_file) == 1:
         self.all_events = load_json_file(self.all_events_file)
      else:
         self.all_events = []
      if cfe(self.all_obs_ids_file) == 1:
         self.all_obs_ids = load_json_file(self.all_obs_ids_file)
      else:
         self.all_obs_ids = {}

      if cfe(self.obs_dict_file) == 1:
         self.obs_dict = load_json_file(self.obs_dict_file)
      else:
         self.obs_dict = {}

      if cfe(self.plane_pairs_file) == 1:
         self.plane_pairs = load_json_file(self.plane_pairs_file)
      else:
         self.plane_pairs = []

      if cfe(self.min_report_file) == 1:
         self.min_report = load_json_file(self.min_report_file)
      else:
         self.min_report= []

      if cfe(self.all_stations_file) == 1:
         self.all_stations = load_json_file(self.all_stations_file)
      else:
         self.all_stations = []
      self.event_dict = {}
      for row in self.all_events:
         self.event_dict[row['event_id']] = row

      rkeys = self.r.keys("EP:*" + self.date + "*")
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
            if ob1 in self.all_obs_ids:
               event_id = self.all_obs_ids[ob1]
               rval['event_id'] = event_id
               print("EVENT ID FOUND FOR THIS COMBO:", event_id, ob1, ob2 )
               self.r.set(gkey, json.dumps(rval))
               self.plane_pairs[gkey] = rval
            else:
               print("Event id not found.", ob1, ob2)
         print("RED:", rval)


      table_header = ["File", "Rows"]
      print("Data loaded for " + date)
      table_data = []
      table_data.append(("Stations", str(len(self.all_stations))))
      table_data.append(("Obs", str(len(self.all_obs_ids.keys()))))
      table_data.append(("Dict", str(len(self.obs_dict.keys()))))
      table_data.append(("Planes", str(len(self.plane_pairs))))
      table_data.append(("Events", str(len(self.all_events))))
      table_data.append(("Minutes", str(len(self.min_report))))
      print(tabulate(table_data,headers=table_header))

   def report_events(self):
      for plane_key in self.plane_pairs:
         if "obs1" in self.plane_pairs[plane_key]:
            obs1 = self.plane_pairs[plane_key]['obs1'].replace(":", "_")
            obs2 = self.plane_pairs[plane_key]['obs2'].replace(":", "_")
         else:
            a,b,c = plane_key.split("AMS")
            obs1 = "AMS" + b
            obs2 = "AMS" + c
            self.plane_pairs[plane_key]['obs1'] = obs1
            self.plane_pairs[plane_key]['obs2'] = obs2
         obs1_ev_id = None
         obs2_ev_id = None
         if obs1 in self.all_obs_ids:
            print("OBS1:", self.all_obs_ids[obs1])
            obs1_ev_id = self.all_obs_ids[obs1]
         if obs2 in self.all_obs_ids:
            print("OBS2:", self.all_obs_ids[obs2])
            obs2_ev_id = self.all_obs_ids[obs2]
         if "event_id" in self.plane_pairs[plane_key]:
            if self.plane_pairs[plane_key]['event_id'] in self.event_dict:
               minute = self.plane_pairs[plane_key]['obs1'].split(":")[1][0:16]
               event_id = self.plane_pairs[plane_key]['event_id']
               if "plane_pairs" not in self.event_dict[event_id] :
                  self.event_dict[event_id]['plane_pairs'] = []
               self.event_dict[event_id]['plane_pairs'].append(self.plane_pairs[plane_key])
               print("PLANE EVENT ID FOUND", event_id, obs1_ev_id, obs2_ev_id, obs1,obs2)
            else:
               print("PLANE EVENT ID IS NOT IN THE EVENT DICT!?", event_id, obs1_ev_id, obs2_ev_id, obs1, obs2)

      save_json_file (self.event_dict_file, self.event_dict)
      print(self.event_dict_file)

   def report_minutes(self):

      for plane_key in self.plane_pairs:
         print("PK", plane_key, self.plane_pairs[plane_key])
         el = plane_key.split("AMS")
         minute = el[1][0:16]
         if minute in self.min_report:
            if "plane_pairs" not in self.min_report[minute]:
               self.min_report[minute]['plane_pairs'] = []
               self.min_report[minute]['plane_pairs'].append(self.plane_pairs[plane_key])
            else:
               self.min_report[minute]['plane_pairs'].append(self.plane_pairs[plane_key])

      for row in self.all_events:
         if "files" not in row:
            print("THERE ARE NO FILES IN THE EVENT!")
            print(row)
            continue
         minute = row['files'][0][0:16]
         if minute in self.min_report:
            if "events" not in self.min_report[minute]:
               self.min_report[minute]['events'] = []
               self.min_report[minute]['events'].append(row['event_id'])
            else:
               self.min_report[minute]['events'].append(row['event_id'])

      print("MULTI-STATION MINUTE REPORT!")
 
      table_header = ["Minute", "Obs", "Stations", "Planes", "Events"]
      table_data = []
      for minute in sorted(self.min_report, reverse=True):
         if "station_count" in self.min_report[minute]:
            if self.min_report[minute]['station_count'] > 1:
               if "plane_pairs" not in self.min_report[minute]:
                  self.min_report[minute]['plane_pairs'] = []
               if "events" not in self.min_report[minute]:
                  self.min_report[minute]['events'] = []

               table_data.append((minute, str(self.min_report[minute]['count']), str(self.min_report[minute]['station_count']), str(len(self.min_report[minute]['plane_pairs'])), str(len(self.min_report[minute]['events']))))
 
      print(tabulate(table_data,headers=table_header))
      save_json_file(self.min_report_file, self.min_report)



   def kml_event_report(self):
      kml = simplekml.Kml()
      fol_day = kml.newfolder(name=self.date + " AS7 EVENTS")
      total_colors = len(kml_colors.keys()) - 1
      kcolors = []
      for key in kml_colors:
         kcolors.append(kml_colors[key])
      ec = 0
      for key in self.event_dict:
         if ec > total_colors:
            ec = 0
         color = kcolors[ec]
         print("KML EVENT DICT KEY: ", key)
         fol_sol = fol_day.newfolder(name=key)
         if "solve_status" in self.event_dict[key]:
            solve_status = self.event_dict[key]['solve_status']
         else:
            solve_status = "UNSOLVED"

         # station start / end AZ 2D Lines

         # For this folder add:
         # point for each station
         # the 3D WMPL trajectory if it exists

         # a line for each of the plane pairs
         if "plane_pairs" not in self.event_dict[key]:
            self.event_dict[key]['plane_pairs'] = []
         else:
            print("NO PP FOR KEY!", key)

         

         for pkey in self.event_dict[key]['planes']:
            data = self.event_dict[key]['planes'][pkey] 
            print("PLANE:", key, pkey)
            status, line1, line2 = data
            combo_key = key
            o_combo_key = combo_key.replace("EP:", "")
            el = o_combo_key.split("AMS")
            ob1, obs2 = pkey.split(":")
            if status == "plane_solved":
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
               print("Bad plane don't map.", status)

         if "solution" in self.event_dict[key]:
            go = False
            if "traj" in self.event_dict[key]['solution']:
               print("YO", key, solve_status, self.event_dict[key]['plane_pairs'])
               traj = self.event_dict[key]['solution']['traj']
               go = True
            if go is True:
               print(traj)
               line = fol_sol.newlinestring(name=key, description="", coords=[(traj['start_lon'],traj['start_lat'],traj['start_ele']),(traj['end_lon'],traj['end_lat'],traj['end_ele'])])
               event_kml_html,self.event_dict[key] = self.event_summary_html(self.event_dict[key])
               line.altitudemode = simplekml.AltitudeMode.relativetoground
               line.style.balloonstyle.text = event_kml_html
               line.style.balloonstyle.textcolor = simplekml.Color.rgb(0,0,0)
               line.linestyle.color = color
               line.linestyle.colormode = "normal"
               line.linestyle.width = "5"
               line.extrude = 1
            else:
               print("THERE IS NO TRAJ!", self.event_dict[key])
         else:
            print("THERE IS NO TRAJ!", self.event_dict[key])
         ec += 1


      kml.save(self.event_kml_file)

      cf = self.event_kml_file.replace("/ams2","/archive.allsky.tv")

      print(self.event_kml_file)
      os.system("cp " + self.event_kml_file + " " + cf)
      save_json_file(self.plane_pairs_file, self.plane_pairs)




   def event_summary_html(self, event):
      event = self.clean_event(event)
      if event['total_stations'] < 2:
         print("THIS EVENT IS NO LONGER VALID!", event)
         input("WAIT.")
      print(event['solution']['traj'].keys())
      traj = event['solution']['traj']

      html = "<table>"
      html += "<tr><td>Event ID:</td><td>{:s}</td></tr>".format(event['event_id'])
      html += "<tr><td>Start:</td><td>{:s} {:s} {:s}</td></tr>".format(str(round(traj['start_lat'],2)), str(round(traj['start_lon'],2)),str(round(traj['start_ele'],2)))
      html += "<tr><td>End:</td><td>{:s} {:s} {:s}</td></tr>".format(str(round(traj['end_lat'],2)), str(round(traj['end_lon'],2)),str(round(traj['end_ele'],2)))
      html += "<tr><td>Velocity:</td><td>{:s}km/s {:s}km/s</td></tr>".format(str(round(traj['v_init']/1000,2)), str(round(traj['v_avg']/1000,2)))
      html += "</table>"

      html += "<table>"
      for i in range(0,len(event['stations'])):
         st = event['stations'][i]
         vid = event['files'][i]
         (f_datetime, cam, f_date_str,fy,fmon,fd, fh, fm, fs) = convert_filename_to_date_cam(vid)
         year = vid[0:4]
         date = vid[0:10]
         prev_url = "https://archive.allsky.tv/" + st + "/METEORS/" + year + "/" + date + "/" + st + "_" + vid.replace(".mp4","-prev.jpg") 
         html += "<img src=" + prev_url + "><br>" + st + "-" + cam + " " + f_date_str + "<br>"

      event_plots = glob.glob(self.event_dir + event['event_id'] + "/*.jpg")
      html += "<h1>Plots</h1>"
      for ep in event_plots:

         pfn = ep.split("/")[-1]
         plot_url = self.cloud_event_url + event['event_id'] + "/" + pfn
         html += "<img src=" + plot_url + "><br>" 
         print("PLOT:", plot_url)

      return(html, event)

   def evaluate_event_planes(self):
      self.plane_pairs = load_json_file(self.plane_pairs_file)
      event_planes = {}
      for combo in self.plane_pairs:
         if "event_id" in self.plane_pairs[combo]:
            event_id = self.plane_pairs[combo]['event_id']
            if event_id not in event_planes:
               event_planes[event_id] = {}
               event_planes[event_id]['planes'] = {}
            event_planes[event_id]['planes'][combo] = self.plane_pairs[combo]

      self.event_planes_file = self.plane_pairs_file.replace("PLANE_PAIRS", "EVENT_PLANES")
      save_json_file(self.event_planes_file, event_planes)
      bad_stations = {}
      good_stations = {}

      for event_id in event_planes:
         start_lats = []
         start_lons = []
         start_alts = []
         end_lats = []
         end_lons = []
         end_alts = []
         for combo in event_planes[event_id]['planes']:
            data = event_planes[event_id]['planes'][combo]
            status = data['status']
            if "line1" in data and status == 'plane_solved':
               line1 = data['line1']
               line2 = data['line2']
               start_lats.append(data['line1'][0])
               start_lats.append(data['line2'][0])
               start_lons.append(data['line1'][1])
               start_lons.append(data['line2'][1])
               start_alts.append(data['line1'][2])
               start_alts.append(data['line2'][2])
               end_lats.append(data['line1'][3])
               end_lats.append(data['line2'][3])
               end_lons.append(data['line1'][4])
               end_lons.append(data['line2'][4])
               end_alts.append(data['line1'][5])
               end_alts.append(data['line2'][5])
               #print("LINES:", status, line1, line2)
            #else:
            #   print("NO LINE IN THIS DATA?:", data)
         if len(start_lats) > 0:
            med_start_lat = np.median(start_lats)
            med_start_lon = np.median(start_lons)
            med_start_alt = np.median(start_alts)
            med_end_lat = np.median(end_lats)
            med_end_lon = np.median(end_lons)
            med_end_alt = np.median(end_alts)
         else:
            med_start_lat = 0 
            med_start_lon = 0
            med_start_alt = 0
            med_end_lat = 0
            med_end_lon = 0
            med_end_alt = 0
            event_planes[event_id]['plane_status'] = "invalid - no valid planes"

         print("MEDIAN START AND END", event_id)
         print("START:", med_start_lat, med_start_lon, med_start_alt)
         print("END:", med_end_lat, med_end_lon, med_end_alt)
         dists = []
         for combo in event_planes[event_id]['planes']:
            data = event_planes[event_id]['planes'][combo]
            status = data['status']
            if status == 'plane_solved':
               slat,slon,salt,elat,elon,ealt = data['line1']
               slat2,slon2,salt2,elat2,elon2,ealt2 = data['line2']
               start_dist_diff = dist_between_two_points(med_start_lat, med_start_lon, slat, slon)
               end_dist_diff = dist_between_two_points(med_end_lat, med_end_lon, elat, elon)
               data['start_dist_diff'] = start_dist_diff
               data['end_dist_diff'] = end_dist_diff
               dists.append(start_dist_diff)
               dists.append(end_dist_diff)
               event_planes[event_id]['planes'][combo] = data
         med_dist = np.median(dists)
         event_planes[event_id]['med_dist'] = med_dist 
         for combo in event_planes[event_id]['planes']:
            data = event_planes[event_id]['planes'][combo]
            status = data['status']
            if status == 'plane_solved':
               st1,vid1 = data['obs1'].split(":")
               st2,vid2 = data['obs2'].split(":")
               if data['start_dist_diff'] > (med_dist * 3) or data['end_dist_diff'] > (med_dist * 3):

                  if st1 not in bad_stations:
                     bad_stations[st1] = 1
                  else:
                     bad_stations[st1] += 1
                  if st2 not in bad_stations:
                     bad_stations[st2] = 1
                  else:
                     bad_stations[st2] += 1

                  med_diff_status = "BAD"
               else:
                  med_diff_status = "GOOD"
                  if st1 not in good_stations:
                     good_stations[st1] = 1
                  else:
                     good_stations[st1] += 1
                  if st2 not in good_stations:
                     good_stations[st2] = 1
                  else:
                     good_stations[st2] += 1

          
               print(med_diff_status, "\tMED DIST:", data['start_dist_diff'], data['end_dist_diff'], st1,st2)

      print("BAD:", bad_stations)
      sbad = sorted(bad_stations.items(), key=lambda x: x[1], reverse=True)
      station_ratings = []
      used = {}
      for data in sbad:
         st,val = data
         used[st] = 1
         if st not in good_stations:
            good_stations[st] = 0
         if good_stations[st] > 0:
            good_perc = good_stations[st] / (good_stations[st] + val)

         station_ratings.append((st,good_stations[st],val,good_perc))
      station_ratings = sorted(station_ratings, key=lambda x: x[3], reverse=True)
      for data in station_ratings:
         print(data)
      for st in good_stations:
         if st not in used:
            print("100% GOOD!", st, good_stations[st])
      save_json_file(self.event_planes_file, event_planes)
      print("Saved:", self.event_planes_file)

      for event_id in event_planes:
         print("EVENT ID:", event_id)
         print("MED DIST:", round(event_planes[event_id]['med_dist'],2))
         for combo_key in event_planes[event_id]['planes']:
            data = event_planes[event_id]['planes'][combo_key]
            if "obs1" in data:
               st1, vid1 = data['obs1'].split(":")
               st2, vid2 = data['obs2'].split(":")
               if "start_dist_diff" in data:
                  dist1 = round(data['start_dist_diff'],2)
                  dist2 = round(data['end_dist_diff'],2)
               else:
                  dist1 = 9999
                  dist2 = 9999
               status = data['status']
               print("\t", st1, st2, status , dist1, dist2 )

   def split_good_bad(self, data):
      for combo_key in data:
         if "status" in data:
            st1, vid1 = data[combo_key]['obs1'].split(":")
            st2, vid2 = data[combo_key]['obs2'].split(":")
            status = data['status']
         else:
            status = "none"
         print("???")


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

   def kml_plane_pairs(self):
      self.all_events = load_json_file(self.all_events_file)
      self.plane_pairs = load_json_file(self.plane_pairs_file)

      kml = simplekml.Kml()
      fol_day = kml.newfolder(name=self.date + " Planes")
      fol_sol = fol_day.newfolder(name='Solved Planes')

      self.obs_event_ids = {}
      print(len(self.all_events), " total events.")
      print("Waiting.")
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
         ev_id = 0
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
         self.plane_pairs[combo_key]['event_id'] = ev_id
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
      save_json_file(self.plane_pairs_file)
      print("SAVED:", self.plane_pairs_file)
      os.system("cp " + self.plane_kml_file + " " + clf)
