#!/usr/bin/python3
from lib.JSFuncs import video_preview_html_js
import requests
from lib.PipeManager import dist_between_two_points
import time
import json
import os
import matplotlib
matplotlib.use('agg')
import glob
from lib.PipeAutoCal import fn_dir
from DynaDB import get_event, get_obs, search_events, update_event, update_event_sol, insert_meteor_event, delete_event
from lib.PipeUtil import load_json_file, save_json_file, cfe, calc_dist, convert_filename_to_date_cam, check_running, get_trim_num, get_file_info
import sys
import numpy as np
import datetime
from datetime import datetime as dt
import math
#from lib.PipeSolve import simple_solvev2
# Import modules from WMPL
import wmpl.Utils.TrajConversions as trajconv
import wmpl.Utils.SolarLongitude as sollon
from wmpl.Trajectory import Trajectory as traj

import matplotlib
import matplotlib.ticker as plticker
#matplotlib.use('TkAgg')
from matplotlib import pyplot as plt

from wmpl.Utils.ShowerAssociation import associateShower


import boto3
from boto3.dynamodb.conditions import Key


import time
from wmpl.Utils.TrajConversions import equatorialCoordPrecession_vect, J2000_JD
import redis
admin_conf = load_json_file("admin_conf.json")
json_conf = load_json_file("../conf/as6.json")
station_id = json_conf['site']['ams_id']
api_key = json_conf['api_key']

if "local_mode" in admin_conf:
   r = redis.Redis(admin_conf['redis_host'], port=6379, decode_responses=True)


def get_aws_events(day):
   day = day.replace("_", "")
   url = "https://kyvegys798.execute-api.us-east-1.amazonaws.com/api/allskyapi?cmd=get_events&date=" + day + "&station_id=" + station_id + "&api_key=" + api_key
   print("GET AWS EVENTS:", url)
   response = requests.get(url)
   content = response.content.decode()
   events =json.loads(content)
   print(response)
   return(events)

def check_make_events(obs_time, obs, events):
   print("EVENTS:", len(events))
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
         if time_diff < 5:
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
            #else:
            #   print("REJECT STATION DIST!", station_dist)
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

def events_report(date, type="all"):
   year, mon, day = date.split("_")
   day_dir = "/mnt/f/EVENTS/" + year + "/" + mon + "/" + day + "/" 
   dyn_cache = day_dir 
   obs_file = dyn_cache + date + "_ALL_OBS.json"
   events_file = dyn_cache + date + "_ALL_EVENTS.json"
   events_index_file = dyn_cache + date + "_ALL_EVENTS_INDEX.json"
   stations_file = dyn_cache + date + "_ALL_STATIONS.json"
   event_index = load_json_file(events_index_file)
   events = load_json_file(events_file)
   updated_events = []

   # first merge in the DYNA data with the last event_index / detect run. 
   # we will need to update the DYNA event (if it exists) with the latest station/index info (Maybe a new obs has been added since last run). 
   # after this we will know the solve status and if we need to run the solve or not
   # we will also need to check to see if any of the obs revisions have changed, or if new obs have been added 
   # so that we can re-run the event. 

   for event in event_index:
      if "start_datetime" in event:
         event_id, uevent = find_existing_event(event, events)
         if event_id == 1:
            event= uevent
         updated_events.append(event)
      else:
         print("ERR:", event)
         return()


   return()
   rpt_s = ""
   rpt_u = ""
   rpt_f = ""
   rpt_r = ""
   final_event_index = []
   for event in updated_events:
      if event['total_stations'] > 1:
         if "solve_status" in event:
            status = event['solve_status']
         else:
            status = "unsolved"
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
            insert_meteor_event(None, event_id, event)
         event['event_status'] = status
         final_event_index.append(event)
         total_stations = len(set(event['stations']))
         if total_stations <= 1:
            print("NEED TO DELETE THIS EVENT AS IT ONLY HAS ONE STATION!")
            delete_event(None, event['event_day'], event['event_id'])

         if status == "SUCCESS":
            rpt_s += ("{:s}          {:s}     {:s}          {:s}\n".format(str(event_id), str(min(event['start_datetime'])), str(status), str(event['stations'])))
         elif status == "unsolved":
            rpt_u += ("{:s}          {:s}     {:s}          {:s}\n".format(str(event_id), str(min(event['start_datetime'])), str(status), str(event['stations'])))
         elif "FAILED" in status:
            rpt_f += ("{:s}          {:s}     {:s}          {:s}\n".format(str(event_id), str(min(event['start_datetime'])), str(status), str(event['stations'])))
         else:
            rpt_r += ("{:s}          {:s}     {:s}          {:s}\n".format(str(event_id), str(min(event['start_datetime'])), str(status), str(event['stations'])))

   save_json_file(events_index_file, final_event_index)

   print("Events Report For " + date)
   row_header = "Event ID                 Event Time                  Status                                Stations"
   print("Solved.")
   print(row_header)
   print(rpt_s)
   print("Unsolved.")
   print(row_header)
   print(rpt_u)
   print("Failed.")
   print(row_header)
   print(rpt_f)
   print("Missing Reduction.")
   print(row_header)
   print(rpt_r)
   print("saved:", events_index_file)


def find_existing_event(event, events):
   event_start_datetime = min(event['start_datetime'])
   obs_dt = datetime.datetime.strptime(event_start_datetime, "%Y-%m-%d %H:%M:%S.%f")
   for ev in events:
      ev_start_datetime = min(ev['start_datetime'])
      ev_dt = datetime.datetime.strptime(ev_start_datetime, "%Y-%m-%d %H:%M:%S.%f")
      time_diff = (obs_dt - ev_dt).total_seconds()

      matches = 0
      for ofile in event['files']:
         if ofile in ev['files']:
            matches += 1
      match_perc = matches / len(event['files'])

      if abs(match_perc) > .5:

         # UPDATE THE DYNA OBJ WITH LATEST INDEX DATA
         new_ev = dict(ev)
         new_ev['stations'] = event['stations']
         new_ev['files'] = event['files']
         new_ev['start_datetime'] = event['start_datetime']
         new_ev['lats'] = event['lats']
         new_ev['lons'] = event['lons']


         return(1,new_ev)
   return(0, None)

def define_events(date):
   year, mon, day = date.split("_")
   day_dir = "/mnt/f/EVENTS/" + year + "/" + mon + "/" + day + "/" 

   cmd = "./DynaDB.py udc " + date
   print(cmd)
   #os.system(cmd)

   dyn_cache = day_dir 
   obs_file = dyn_cache + date + "_ALL_OBS.json"
   events_file = dyn_cache + date + "_ALL_EVENTS.json"
   events_index_file = dyn_cache + date + "_ALL_EVENTS_INDEX.json"
   stations_file = dyn_cache + date + "_ALL_STATIONS.json"

   events = []
   if cfe(events_file) == 1:
      all_events = load_json_file(events_file)

   all_obs = load_json_file(obs_file)
   if cfe(stations_file) == 1:
      stations = load_json_file(stations_file)
   else:
      print("NO STATIONS FILE!?")
      return()
   station_loc = {}
   meteor_min = {}
   for data in stations:
      sid = data[0]
      lat = data[1]
      lon = data[2]
      station_loc[sid] = [lat,lon]

   obs_data_time = []

   stations_reporting = {}
   for obs in all_obs:
      # get station and lat/lon for station
      red_missing = 0
      station_id = obs['station_id']
      s_lat = station_loc[station_id][0]
      s_lon = station_loc[station_id][1]
      # get the time for the obs
      mftime = 0
      if station_id not in stations_reporting:
         stations_reporting[station_id] = 0
      else:
         stations_reporting[station_id] += 1


      if "meteor_frame_data" in obs:
         if len(obs['meteor_frame_data']) > 0:
            obs_time = obs['meteor_frame_data'][0][0]
            if "." in obs_time:
               obs_dt = datetime.datetime.strptime(obs_time, "%Y-%m-%d %H:%M:%S.%f")
            else:
               obs_dt = datetime.datetime.strptime(obs_time, "%Y-%m-%d %H:%M:%S")


            mftime = 1 
      if mftime == 0:
         (f_datetime, cam, f_date_str,fy,fmon,fd, fh, fm, fs) = convert_filename_to_date_cam(obs['sd_video_file'])
         trim_num = get_trim_num(obs['sd_video_file'])
         extra_sec = int(trim_num) / 25
         event_start_time = f_datetime + datetime.timedelta(0,extra_sec)
         obs_dt = event_start_time
         red_missing = 1
      obs_data_time.append((obs_dt, obs))

   obs_data_time = sorted(obs_data_time, key=lambda x: (x[0]), reverse=False)
   obs_by_min = {}
   #events = []

   for obs_dt, obs_data in obs_data_time:
      station_id = obs_data['station_id']
      s_lat = station_loc[station_id][0]
      s_lon = station_loc[station_id][1]
      obs_data['lat'] = s_lat
      obs_data['lon'] = s_lon
      hour = "{:02d}".format(obs_dt.hour)
      minute = "{:02d}".format(obs_dt.minute)
      key = hour + ":" + minute
      if key not in obs_by_min:
         obs_by_min[key] = {}
         obs_by_min[key]['stations'] = []
         obs_by_min[key]['files'] = []
         obs_by_min[key]['start_datetime'] = []
         obs_by_min[key]['lats'] = []
         obs_by_min[key]['lons'] = []
      obs_by_min[key]['stations'].append(station_id)
      obs_by_min[key]['files'].append(obs_data['sd_video_file'])
      obs_by_min[key]['start_datetime'].append(obs_dt)
      obs_by_min[key]['lats'].append(s_lat)
      obs_by_min[key]['lons'].append(s_lon)

      events = check_make_events(obs_dt, obs_data, events)

   ss_events = []
   ms_events = []
   for event in events:
      total_stations = len(set(event['stations']))
      event['total_stations'] = total_stations
      # convert datetimes to strings!
      new_times = []
      for ttt in event['start_datetime']:
          if isinstance(ttt,str) is True:
             time_str = ttt
          else:
             time_str = ttt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]


          #time_str = ttt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
          new_times.append(time_str)
      event['start_datetime'] = new_times    

      if total_stations > 1:
         ms_events.append(event)
      else:
         ss_events.append(event)

   tsr = len(stations_reporting.keys())
   print(str(tsr) + " Stations Reporting")
   for station in stations_reporting:
      print(station, stations_reporting[station])
   print(str(len(ss_events)) + " Single Station Events ")
   print(str(len(ms_events)) + " Multi Station Events ")
   for event in ms_events:
      print(min(event['start_datetime']), set(event['stations']))

   all_events = ms_events + ss_events
   save_json_file(events_index_file, all_events)
   print("saved:", events_index_file)
   cloud_events_index_file = events_index_file.replace("/mnt/f/", "/mnt/archive.allsky.tv/")
   cfn, cdir = fn_dir(cloud_events_index_file)
   if cfe(cdir,1) == 0:
      os.makedirs(cdir)
   #cmd = "cp " + events_index_file + " " + cloud_events_index_file
   #print("DISABLED!", cmd)
   #os.system(cmd)
   mins = []
   counts = []
   # Plot unq station obs by minute
   for key in obs_by_min:
      unq_stations = len(set(obs_by_min[key]['stations']))
      mins.append(key)
      counts.append(unq_stations)

   fig, ax = plt.subplots()
   ax.plot(mins, counts, '.r', alpha=0.6,
      label='Unique Station Observations Per Minute')
   #start,end = ax.get_xlim()
   #ax.xaxis.set_ticks(np.arange(start, end, .1))

   loc = plticker.MultipleLocator(60) # this locator puts ticks at regular intervals
   ax.xaxis.set_major_locator(loc)

   #plt.gca().invert_yaxis()
   plt.savefig("/mnt/f/test.png")
   print("saved /mnt/f/test.png")

   events_report(date)

def sanity_check_obs(obs):
   ignore = {}
   best_obs = {}
   for station_id in obs:
      if len(obs[station_id]) > 1:
         best_file = get_best_obs(obs[station_id])
         for vid in obs[station_id]:
            if vid == best_file:
               print(station_id, vid)
               data = obs[station_id][vid]
               obs[station_id][vid]['best'] = 1
               if "meteor_frame_data" in data:
                  print(data['meteor_frame_data'])
            else:
               ignore[station_id + "_" + vid] = 1
               obs[station_id][vid]['ignore'] = 1
      else:
         best_file = obs[station_id].keys()
         for key in obs[station_id].keys():
            best_file = key
      best_obs[station_id] = {} 
      best_obs[station_id][best_file] = obs[station_id][best_file]
      #print(best_obs[station_id][best_file]['gc_azs'])
      #print(best_obs[station_id][best_file]['gc_els'])
   return(best_obs)


def sanity_check_points(azs,els, ras, decs):
   from RMS.Math import angularSeparation
   bad_is = []
   for i in range(0,len(ras)):
      if i > 0:
         dist_to_last = angularSeparation(ras[i],decs[i], ras[i-1], decs[i-1])
      else:
         dist_to_last = 0
      if i != 0 and dist_to_last == 0:
         bad_is.append(i)
      print(i, ras[i], decs[i], dist_to_last)
   temp_azs = []
   temp_els = []

   print("BAD IS:", bad_is)
   good_azs = []
   good_els= []
   for i in range(0,len(azs)):
      if i in bad_is:
         print(i, "BAD", azs[i], els[i])
      else:
         print(i, "GOOD", azs[i], els[i])
         good_azs.append(azs[i])
         good_els.append(els[i])

   print("BEFORE SANITY AZ:", azs)
   print("BEFORE SANITY EL:", els)

   print("AFTER SANITY AZ:", good_azs)
   print("AFTER SANITY EL:", good_els)


   return(good_azs,good_els)

def GC_az_el(azs, els, ras=None,decs=None):

   import RMS.GreatCircle
   from RMS.Math import polarToCartesian, cartesianToPolar, angularSeparation
   import numpy as np
   from RMS import GreatCircle


   #azs,els= sanity_check_points(azs,els,ras, decs)


   azim = np.array(azs)
   elev = np.array(els)


   ### Fit a great circle to Az/Alt measurements and compute model beg/end RA and Dec ###

   # Convert the measurement Az/Alt to cartesian coordinates
   # NOTE: All values that are used for Great Circle computation are:
   #   theta - the zenith angle (90 deg - altitude)
   #   phi - azimuth +N of due E, which is (90 deg - azim)
   x, y, z = polarToCartesian(np.radians((90 - azim)%360), np.radians(90 - elev))

   # Fit a great circle
   C, theta0, phi0 = GreatCircle.fitGreatCircle(x, y, z)

   azs_gc = []
   els_gc = []

   # Get the first point on the great circle
   for i in range(0, len(azs)):
      phase1 = GreatCircle.greatCirclePhase(np.radians(90 - elev[i]), np.radians((90 - azim[i])%360), \
            theta0, phi0)
      alt1, azim1 = cartesianToPolar(*GreatCircle.greatCircle(phase1, theta0, phi0))
      alt1 = 90 - np.degrees(alt1)
      azim1 = (90 - np.degrees(azim1))%360
      #print("ORG/NEW:", azs[i], els[i], azim1, alt1)
      azs_gc.append(float(azim1))
      els_gc.append(float(alt1))
   return(azs_gc, els_gc)



def solve_status(day):
   date = day

   year, mon, day = date.split("_")
   day_dir = "/mnt/f/EVENTS/" + year + "/" + mon + "/" + day + "/" 
   dyn_cache = day_dir
   #dyn_cache = "/mnt/f/DYCACHE/"
   dynamodb = boto3.resource('dynamodb')
   obs_file = dyn_cache + date + "_ALL_OBS.json"
   events_file = dyn_cache + date + "_ALL_EVENTS.json"
   stations_file = dyn_cache + date + "_ALL_STATIONS.json"

   stations = []
   if cfe(events_file) == 1:
      print("Loading events file.", events_file)
      events = load_json_file(events_file)
   else:
      print("No events file.", events_file)
      events = []
   #events = search_events(dynamodb, day, stations)


   solved_html = ""
   not_solved_html = ""
   failed_html = ""
   for event in events:
      if "solve_status" in event :
         if "FAILED" in event['solve_status']:
            #len_az = len(event['obs'][station][file]['azs'])
            desc = ""
            for station in event['obs']:
               for file in event['obs'][station]:
                  len_az = len(event['obs'][station][file]['azs'])
                  if len_az == 0:
                     desc += station + " missing reduction "
            failed_html += event['event_id'] + " " + event['solve_status'] + str(event['stations']) + " " + desc + "\n"
            #for station in event['obs']:
            #   for file in event['obs'][station]:
            #      print (len(event['obs'][station][file]['azs']))
               #print(obs)
         elif "missing" in event['solve_status']:
             failed_html += "Missing reductions " + str(event['solve_status'])
         else:
            event_url = event['solution']['sol_dir'].replace("/mnt/f/meteor_archive/", "https://archive.allsky.tv/")
            solved_html += event['event_id'] + " " + event['solve_status'] + " " + event_url + "/index.html\n"
      else:

         if "solution" in event:
            if event["solution"] != 0:
               solved_html += event['event_id'] + " Solved.\n" 
         else:
            not_solved_html += event['event_id'] + " Not solved. " + str(event['stations']) + "\n"

   print(solved_html)
   print(failed_html)
   print(not_solved_html)

def get_best_obs(obs):
   print("WHICH OBS IS BEST!")
   best_dist = 99999
   best_len = 0 
   best_file = None
   best_res = None
   for file in obs:
      if best_file is None:
         best_file = file

      # BUG BEST OBS
      mid_x = np.mean(obs[file]['xs'])
      mid_y = np.mean(obs[file]['ys'])
      obs_len = len(obs[file]['azs'])
      dist_to_center = calc_dist((mid_x,mid_y), (1920/2, 1080/2))
 
      # choose file with best points!
      if obs_len > best_len:
         best_file = file
         best_len = obs_len 

      if False:
         if best_res is None:
            if "calib" in obs[file]:
               if len(obs[file]['calib']) > 4:
                  if obs[file]['calib'][-1] is not None:
                        best_res = obs[file]['calib'][-1]

         if "calib" in obs[file]:
            if len(obs[file]['calib']) > 4:
               if obs[file]['calib'][-1] is not None:
                  if obs[file]['calib'][-1] < best_res:
                     best_file = file
                     best_res = obs[file]['calib'][-1]
      print("FILE:", file)
      print("DIST TO CENTER:", dist_to_center)
      print("OBS KEYS:", obs[file]['calib'])


   print("BEST:", best_file)
   return(best_file)

def solve_month(wild):
   files = glob.glob("/mnt/f/meteors/" + wild + "*")
   mets = []
   for file in files:
      if cfe(file, 1) == 1:
         mets.append(file)
   for file in mets:
      day = file.split("/")[-1]
      solve_day(day)


def delete_events_day(date):
   year, mon, day = date.split("_")
   day_dir = "/mnt/f/EVENTS/" + year + "/" + mon + "/" + day + "/" 
   dyn_cache = day_dir 
   xxx = input("Are you sure you want to delete all events for " + date + " [ENTER] to cont or [CNTL-X] to quit.")
   events_file = dyn_cache + date + "_ALL_EVENTS.json"
   events = load_json_file(events_file)
   for event in events: 
      delete_event(None, event['event_day'], event['event_id'])

def make_vida_plots(day):
   date = day
   year, mon, dom = date.split("_")
   day_dir = "/mnt/f/EVENTS/" + year + "/" + mon + "/" + dom + "/"
   dyn_cache = day_dir
   #cmd = "./DynaDB.py udc " + day + " events"
   #print(cmd)
   #os.system(cmd)

   print("Solve day", day)
   dynamodb = boto3.resource('dynamodb')
   json_conf = load_json_file("../conf/as6.json")
   my_station = json_conf['site']['ams_id']
   stations = json_conf['site']['multi_station_sync']
   if my_station not in stations:
      stations.append(my_station)

   #events = search_events(dynamodb, day, stations)

   obs_file = dyn_cache + date + "_ALL_OBS.json"
   events_file = dyn_cache + date + "_ALL_EVENTS.json"
   evd = load_json_file(events_file)
   for key in evd:
      print(key)

def event_stats(events):
   stats = {}
   for ev in events:
      if "solve_status" in ev:
         ss = ev['solve_status']
      else:
         ss = "UNSOLVED"
      if ss not in stats:
         stats[ss] = 0
      
      stats[ss] += 1
      print(ev['event_id'], ss)
   for ss in stats:
      print(ss, stats[ss])

def solve_day(day, cores=16):
   date = day
   year, mon, dom = date.split("_")
   day_dir = "/mnt/f/EVENTS/" + year + "/" + mon + "/" + dom + "/" 
   if cfe(day_dir,1) == 0:
      os.makedirs(day_dir)
   dyn_cache = day_dir 
   #cmd = "./DynaDB.py udc " + day + " events"
   #print(cmd)
   #os.system(cmd)

   print("Solve day", day)
   dynamodb = boto3.resource('dynamodb')
   json_conf = load_json_file("../conf/as6.json")
   my_station = json_conf['site']['ams_id']
   stations = json_conf['site']['multi_station_sync']
   if my_station not in stations:
      stations.append(my_station)

   #events = search_events(dynamodb, day, stations)

   obs_file = dyn_cache + date + "_ALL_OBS.json"
   events_file = dyn_cache + date + "_ALL_EVENTS.json"
   events_index_file = dyn_cache + date + "_ALL_EVENTS_INDEX.json"
   print("Trying...", events_file)
   if cfe(events_file) == 1:
      size, tdiff = get_file_info(events_file)
   else:
      print("COULD NOT FIND EVENTS FILE!", events_file)
      size = 0
      tdiff = 0

   
   print("TDIFF!", tdiff)
   #if cfe(events_file) == 0:
   #if True:
   #   print("COPY MASTER EVENTS FILE FOR DAY", day)
   #   cf = events_file.replace("/mnt/f", "/mnt/archive.allsky.tv")
   #   cmd = "cp " + cf + " " + events_file
   #   os.system(cmd)


   #events_index = load_json_file(events_index_file)
   # get events from FILE ( no api) (events file is generated on cloud VM 1x per hour for current and passed day. It is faster / better cost to grab the event file from wasabi, than aws. 
   # it has all the info needed to deal with that day's events. 
   # we should also have the index file, with abbr version for faster client / display downloads
   print(events_file)
   events = load_json_file(events_file)
   event_stats(events)
   # get events from API
   #events = get_aws_events(day)
   print("TOTAL EVENTS:", len(events))
   #print("TOTAL INDEX:", len(events_index))
   total_events = len(events)
   ec = 0

   #for event in events_index:
   stats = {}
   for event in events:
      if "solve_status" in event:
         ss = event['solve_status']
      else:
         ss = "unsolved" 
      if ss in stats:
         stats[ss] += 1
      else:
         stats[ss] = 0
      if ss == "unsolve":
         if False:
         #if cfe(day_dir + event['event_id'] + "/" + event['event_id'] + "-event.json") == 1:
            stats[ss] -= 1
            ss = "solved"
            stats[ss] -= 1
            event['solve_status'] = "SUCCESS"
   for ss in stats:
      print(ss, stats[ss])

   for event in events:
      print("DY EV:", event['event_id'])
      go = 1
      time_sync = 1
      if "solve_status" in event:
         if event['solve_status'] == "SUCCESS":
            go = 0
         if event['solve_status'] == 'WMPL FAILED.':
            go = 1
            time_sync = 0
         if event['solve_status'] == "unsolved":
            go = 1
         print("Solve Status.", event['solve_status'] , go)

      #go = 1
      #cores = 0
      if go == 1:
         print("Not Solved yet, try to solve", event['event_id'])
         if "solve_status" in event:
            print("SS", event['solve_status'])
         if cores == 0:
            solve_event(event['event_id'])
         else:
             # this is a multi-core run so launch many threads and wait. 
             running = check_running("solveWMPL.py")
             print("POSSIBLE CORES:", cores)
             print("RUNNING:", running)
             if running < cores:
                
                cmd = "./solveWMPL.py se " + event['event_id'] + " " + str(time_sync) + " &"
                print(cmd)
                print("SKIP RUN!")
                os.system(cmd)
                #time.sleep(2)
             while running >= cores:
                time.sleep(5)
                running = check_running("solveWMPL.py")
                print(running, " solving processes running.")
      ec += 1

   #cmd = "./DynaDB.py udc " + day + " events"
   #print(cmd)
   #os.system(cmd)


def parse_extra_obs(extra):
   print("EXTRA OBS FILE:", extra)
   fp = open(extra)
   on = 0
   dc = 0
   dts = []
   azs = []
   els = []
   for line in fp:
      if on == 1:
         if dc == 0:
            fields = line.replace("\n", "").split(",")
            flc = 0
            for fl in fields:
               if fl == "datetime":
                  dti = flc
               if fl == "altitude":
                  alti = flc
               if fl == "azimuth":
                  azi = flc
               flc += 1
            print(fields)
         else:
            values = line.replace("\n", "").split(",")
            dt = values[dti]
            dt = dt.replace("T", " ")
            az = float(values[azi])
            el = float(values[alti])
            print(dt, az, el)
            dts.append(dt)
            azs.append(az)
            els.append(el)
         dc += 1
      if "telescope" in line:
         rd = line.replace("# - ","")
         rd = rd.replace("{telescope: ","")
         rd = rd.replace("}","")
         rd = rd.replace("\n","")
         station = rd
      if "original_raw_filename" in line:
         rd = line.replace("# - ","")
         rd = rd.replace("{original_raw_filename: ","")
         rd = rd.replace("}","")
         rd = rd.replace("\n","")
         obs_file = rd

      if "obs_latitude" in line:
         rd = line.replace("# - ","")
         rd = rd.replace("{obs_latitude: ","")
         rd = rd.replace("}","")
         rd = rd.replace("\n","")
         obs_lat = float(rd)
         print(obs_lat)
      if "obs_longitude" in line:
         rd = line.replace("# - ","")
         rd = rd.replace("{obs_longitude: ","")
         rd = rd.replace("}","")
         rd = rd.replace("\n","")
         obs_lon = float(rd)
         print(obs_lon)
      if "obs_elevation" in line:
         rd = line.replace("# - ","")
         rd = rd.replace("{obs_elevation: ","")
         rd = rd.replace("}","")
         rd = rd.replace("\n","")
         obs_alt = float(rd)
         print(obs_alt)
      if "# schema" in line:
         on = 1

   e_obs = {}
   times = []
   #for i in range(0,len(azs)):
   #   ft = i/25
   #   times.append(ft)
   e_obs['station'] = station
   e_obs['file'] = obs_file 
   e_obs['loc'] = [obs_lat,obs_lon,obs_alt]
   e_obs['azs'] = azs
   e_obs['els'] = els
   e_obs['start_datetime'] = dts
   print(e_obs)
   return(e_obs)

def get_event_data(date, event_id,json_conf=None):
   y,m,d = date.split("_")
   event_file = "/mnt/f/EVENTS/" + y + "/" + m + "/" + d + "/" + y + "_" + m + "_" + d + "_ALL_EVENTS.json" 
   event_dict_file = "/mnt/f/EVENTS/" + y + "/" + m + "/" + d + "/" + y + "_" + m + "_" + d + "_ALL_EVENTS_DICT.json" 
   obs_dict_file = "/mnt/f/EVENTS/" + y + "/" + m + "/" + d + "/" + y + "_" + m + "_" + d + "_OBS_DICT.json" 
   event_dict = {}
   if cfe(event_dict_file) == 1:
      try:
         event_dict = load_json_file(event_dict_file)
      except:
         print("CORRUPT EVENT DICT:", event_dict_file)
         return()
   else:
      event_dict = {}
   if cfe(event_file) == 1:
      events = load_json_file(event_file)
      for ev in events:
         ev_id = ev['event_id']
         event_dict[ev_id] = ev
            
   save_json_file(event_dict_file, event_dict)

   if event_id in event_dict:
      event_data = event_dict[event_id]
   else:
      print("EVENT DOES NOT EXIST IN THE EVENT DICT!", event_id)
      return()


   if cfe(obs_dict_file) == 1:
      obs_dict = load_json_file(obs_dict_file)
   else:
      print("NO OBS DICT!", obs_dict_file)
   

   obs_data = {}
   for i in range(0, len(event_data['stations'])):
      st = event_data['stations'][i]
      vid = event_data['files'][i]
      obs_key = st + ":" + vid
      obs_d = obs_dict[obs_key]
      obs_data[obs_key] = obs_d
   print("EVD:", event_data)
   print("OBD:", obs_data)
   resp = {}
   resp['event_data'] = event_data
   resp['obs_data'] = obs_data 
   return(resp)


def get_event_data_old2(date, event_id,json_conf=None):

   if json_conf is None:
      json_conf = load_json_file("../conf/as6.json")
   station_id = json_conf['site']['ams_id']
   api_key = json_conf['api_key']
   url = "https://kyvegys798.execute-api.us-east-1.amazonaws.com/api/allskyapi?cmd=get_event&event_date=" + date + "&event_id=" + event_id + "&station_id=" + station_id + "&api_key=" + api_key
   print("GET EVENT_DATA:", url)
   if True:
      response = requests.get(url)
      content = response.content.decode()
      #print(content)
      #content = content.replace("\\", "")
      #if content[0] == "\"":
      #   content = content[1:]
      #   content = content[0:-1]
      print(content)
      if "not found" in content:
         data = {}
         data['aws_status'] = False
      else:
         data = json.loads(content)
         data['aws_status'] = True
      return(data)

def get_event_data_old(date, event_id):

   year, mon, day = date.split("_")
   day_dir = "/mnt/f/EVENTS/" + year + "/" + mon + "/" + day + "/" 
   dyn_cache = day_dir 
   events_file = dyn_cache + date + "_ALL_EVENTS.json"
   if cfe(events_file) == 1:
      ev = load_json_file(events_file)
   else:
      return(None)
   for event in ev:
      print("SCANNING:", event_id, event['event_id'])
      if event_id == event['event_id']:
         return(event) 

def custom_solve(event_id):
    # event ID should point to an event dir with a good_obs file that is ready to go with obs!
    # good obs file sould be dict of:
    # station => file => then:
    # ['loc', 'calib', 'times', 'fns', 'xs', 'ys', 'azs', 'els', 'ras', 'decs', 'ints', 'revision', 'gc_azs', 'gc_els'])       
    year = event_id[0:4]
    mon = event_id[4:6]
    day = event_id[6:8]
    date = year + "_" + mon + "_" + day
    local_event_dir = "/mnt/f/EVENTS/" + year + "/" + mon + "/" + day + "/" + event_id + "/" 
    cloud_event_dir = "/mnt/archive.allsky.tv/EVENTS/" + year + "/" + mon + "/" + day + "/" + event_id + "/" 
    local_events_dir = "/mnt/f/EVENTS/" 
    good_obs_file = local_event_dir + event_id + "_GOOD_OBS.json"
    obs_data = []
    if os.path.exists(local_event_dir + event_id + "_GOOD_OBS.json") is False:
       print("Event file doesn't exist please make: " + local_event_dir + event_id + "_GOOD_OBS.json")
       exit()
       #return()
    else:
        good_obs = load_json_file(good_obs_file) 
    for obs in good_obs:
       for ofile in good_obs[obs]:
          print(obs, ofile, good_obs[obs][ofile].keys())

    WMPL_solve(event_id, good_obs, 0)

def solve_event(event_id, force=1, time_sync=1):
    year = event_id[0:4]
    mon = event_id[4:6]
    day = event_id[6:8]
    date = year + "_" + mon + "_" + day
    local_event_dir = "/mnt/f/EVENTS/" + year + "/" + mon + "/" + day + "/" + event_id + "/" 
    cloud_event_dir = "/mnt/archive.allsky.tv/EVENTS/" + year + "/" + mon + "/" + day + "/" + event_id + "/" 
    local_events_dir = "/mnt/f/EVENTS/" 
    ignore_file = local_event_dir + event_id + "_IGNORE.json"


    if cfe(local_event_dir + event_id + "-event.json") == 1:
       print("Event already done")
       #return()

    inspect_file = local_event_dir +  event_id + "-INSPECT.json"
    if False:
       if cfe(inspect_file) == 1:
          inspect_data = load_json_file(inspect_file)
       else:
          os.system("/usr/bin/python3.8 Inspect.py " + event_id)

          inspect_data = load_json_file(inspect_file)
       if "ignore_obs" in inspect_data:
          ignore_obs = inspect_data['ignore_obs']
       else:
          ignore_obs = {}

   # + year + "/" + mon + "/" + day + "/" 
    cloud_events_dir = "/mnt/archive.allsky.tv/EVENTS/" 
    #+ year + "/" + mon + "/" + day + "/" 

    if cfe(local_events_dir,1) == 0:
       os.makedirs(local_events_dir)
    if cfe(cloud_events_dir,1) == 0:
       os.makedirs(cloud_events_dir)

    # get stations file for this day
    cloud_stations_file = cloud_events_dir + "ALL_STATIONS.json"
    local_stations_file = local_events_dir + "ALL_STATIONS.json"
    #if cfe(local_stations_file) == 0:
    if cfe(cloud_stations_file) == 1:
       os.system("cp " + cloud_stations_file + " " + local_stations_file)
    else:
       print("NO CLOUD STATIONS FILE?", cloud_stations_file)
   
    print("LOCAL STATIONS FILE:", local_stations_file)

    all_stations_ar = load_json_file(local_stations_file)
    all_stations = {}
    print("ALL ST:", all_stations_ar)
    for data in all_stations_ar:
       print(data)
       st_id = data['station_id']
       all_stations[st_id] = data
    #print("AS:", all_stations[0])



    if cfe(cloud_event_dir, 1) == 0:
       os.makedirs(cloud_event_dir)
       cloud_event_files = []
    else:
       cloud_event_files = glob.glob(cloud_event_dir + "*") 

    if cfe(local_event_dir, 1) == 0:
       os.makedirs(local_event_dir)

    if len(cloud_event_files) > 1:
       print("This event was already processed.", cloud_event_files)
       
       #return()

    print("EVID:", event_id)


    json_conf = load_json_file("../conf/as6.json")
    ams_id = json_conf['site']['ams_id']
    solve_dir = local_event_dir 
    #nsinfo = load_json_file("../conf/network_station_info.json")

    dynamodb = boto3.resource('dynamodb')
    #event = get_event(dynamodb, event_id, 0)
    event_data =  get_event_data(date, event_id)
    print(event_data)
    event = event_data['event_data']
    eobs = event_data['obs_data']
    if event == None:
       print("There is no event data/event")
    ev_status = check_event_status(event)

    status = ev_status['status']
    if status == 1:
       print("This event was already solved successfully.", event_id)
       #return()
    if status == -1:
       print("This event was failed to solve.", event_id)
       #return()

    # Check if there are 3rd party network obs to import
    extra_obs_dir = local_event_dir + event_id + "/extra_obs/"
    if cfe(extra_obs_dir, 1) == 1:
       extra_obs = glob.glob(extra_obs_dir + "*")
    else:
       extra_obs = []
    #print("EXTRA", extra_obs)
    #exit()
    if event is not None:
       if "solution" in event and force != 1:
          if "solve_status" in event:
             if "FAIL" in event['solve_status']:
                print("The event ran and failed.")
                #return()
             else:
                print("The event ran and passed.")
                #return()


    obs = {}
    if os.path.exists(ignore_file) is True:
       ig = load_json_file(ignore_file)
       for t in ig:
          ignore_obs[t] = 1 
    if event is None:
       print("EVENT IS NONE!")
       return()

    if len(event) == 0:
       return()

    bad_obs = []
    for i in range(0, len(event['stations'])):
       t_station = event['stations'][i]
       t_file = event['files'][i]
       obs_key = t_station + "_" + t_file
       if obs_key in ignore_obs:
          print("IGNORE:", obs_key)
          #input("WAITING REMOVE THIS LINE!")

          continue
       dy_obs_data = eobs[t_station + ":" + t_file]
       print("DY OBS DATA:", dy_obs_data)
       if dy_obs_data is not None:
          if True:
             local_file = "/mnt/f/STATIONS/CONF/" + t_station + "_as6.json" 
             cloud_file = "/mnt/archive.allsky.tv/" + t_station + "/CAL/as6.json" 
             if cfe(local_file) == 0:
                os.system("cp "  + cloud_file + " " + local_file)

             # LOCAL REMOTE MODE FIX
             #red_key = "ST:" + t_station
             #red_val = r.get(red_key)
             if t_station not in all_stations:
                print("MISSING STATION IN FOR ", t_station)
                continue
             red_val = all_stations[t_station]
             print("RED VAL:", red_val)

             if red_val is not None:
                #red_val = json.loads(red_val)
                lat = red_val['lat']
                lon = red_val['lon']
                alt = red_val['alt']
                dy_obs_data['loc'] = [lat,lon,alt]
             else:
                jsi = load_json_file(local_file)
                dy_obs_data['loc'] = [jsi['site']['device_lat'], jsi['site']['device_lng'], jsi['site']['device_alt']]
          obs_data = convert_dy_obs(dy_obs_data, obs )
       else:
          print("DYNA OBS DATA IS NONE!")

    # sanity check the obs!
    print("USING THESE OBS:", obs_data)
    for obs in obs_data:
       print(obs)
    extra_obs_data = None
    if False:
       extra_obs = [
             "/mnt/f/EVENTS/2022/12/13/20221213_163728/EXTRA/2022-12-13T16_37_28_FRIPON_BEBR01.ecsv",
             "/mnt/f/EVENTS/2022/12/13/20221213_163728/EXTRA/2022-12-13T16_37_28_FRIPON_NLSN01_Revised.ecsv",
             "/mnt/f/EVENTS/2022/12/13/20221213_163728/EXTRA/2022-12-13T16_37_28_FRIPON_NLWN02.ecsv"
       ]
       extra_obs_data = []
       if len(extra_obs) > 0:
          for efile in extra_obs:
             edata = parse_extra_obs(efile)
             extra_obs_data.append(edata)


    #obs = sanity_check_obs(obs)

    # get WMPL ID (lowest start time)
    start_times = []
    #for ob in obs_data:
    #   print(ob)

    for station_id in obs_data:
        print("OBS STATION_ID", obs)
        if len(obs_data[station_id].keys()) > 1:
           file = get_best_obs(obs_data[station_id])
        else:
           for bfile in obs_data[station_id]:
               file = bfile


        if len(obs_data[station_id][file]['times']) > 0:
           start_times.append(obs_data[station_id][file]['times'][0])
        else:
           bad_obs.append(station_id + " missing reduction.")

    if len(start_times) == 0:
       status = ""
       for stat in bad_obs:
          status = status + stat
       solution= {}
       print("UPDATE DYNA SOL:", event_id) # , solution, obs, status)
       print("BAD OBS!:", event)
       print("BAD OBS!:", len(obs))
       status = "WMPL FAILED. BAD OBS DATA."
       for obs in obs_data:
          print("OBS:", obs)
       update_event_sol(None, event_id, solution, obs_data, status)
       return()

    event_start = sorted(start_times)[0]

    day = event_start[0:10]
    day = day.replace("-", "_")
    e_dir = event_start.replace("-", "")
    e_dir = e_dir.replace(":", "")
    e_dir = e_dir.replace(" ", "_")
    #solve_dir += day + "/" + e_dir 
    solve_dir = local_event_dir 
    if cfe(solve_dir, 1) == 0:
       os.makedirs(solve_dir)

    if cfe(solve_dir, 1) == 1:
       files = glob.glob(solve_dir + "/*")
       for file in files:
          print("DEL:", file)
       #os.system("rm " + solve_dir + "/*")
       #os.system("rmdir " + solve_dir )

    sol = simple_solvev2(obs_data)
    if extra_obs_data is not None:
       obs_data = add_extra_obs(extra_obs_data, obs_data)

    save_json_file(local_event_dir + "/" + event_id + "-simple.json", sol)
    save_json_file(local_event_dir + "/" + event_id + "-obs.json", obs_data)
    print("SAVED FILES IN:", solve_dir)
    if len(bad_obs) > 4:
       obs_data = {}
       solution = {}
       print("BAD OBS > 4!?")
       update_event_sol(None, event_id, solution, obs_data, str(bad_obs))
       return()
    else: 
       WMPL_solve(event_id, obs_data, time_sync)

    sf = glob.glob(solve_dir + "/*")
    solved_files = []
    for ss in sf :
       fn = ss.split("/")[-1]
       solved_files.append(fn)

    if len(solved_files) > 10:
       simple_status = 1
       wmpl_status = 1
    else:
       simple_status = 1
       wmpl_status = 0

    resp = make_event_json(event_id, solve_dir,ignore_obs)
    
    if resp == 0:
       print("FAILED TO SOLVE!")
       solution = {}
       #solution['obs'] = obs_data
       solution['plots'] = solved_files
       #if time_sync == 0:
       #   update_event_sol(None, event_id, solution, obs_data, "WMPL FAILED. TIME SYNC FAILED.")
       #else:
       if time_sync == 0:
          update_event_sol(None, event_id, solution, obs_data, "WMPL FAILEDx2")
       else:
          update_event_sol(None, event_id, solution, obs_data, "WMPL FAILED.")
       for obs in obs_data:
          print("OBS:", obs)
          for vid in obs_data[obs]:
             print("\t", vid)
             print("\t\tAZS:", obs_data[obs][vid]['azs'])
             print("\t\tELS:", obs_data[obs][vid]['els'])
       #cmd = "cd ../pythonv2; ./solve.py vida_failed_plots " + event_id
       #print(cmd)
       #os.system(cmd)
       return(0)
    solution,as_obs = resp

    print("EVID:", event_id)
    print("UPDATE EVENT SOL:")
    if time_sync == 1:
       update_event_sol(None, event_id, solution, as_obs, "SUCCESS")
    if time_sync == 0:
       update_event_sol(None, event_id, solution, as_obs, "SUCCESS")

    event_file = solve_dir + "/" + event_id + "-event.json"

    make_event_html(event_file)

    # remove the pngs and then copy the results to the cloud dir
    cloud_dir = solve_dir.replace("/mnt/f/", "/mnt/archive.allsky.tv/")
    if cfe(cloud_dir,1) == 0:
       os.makedirs(cloud_dir)

    #cmd = "cd ../pythonv2; ./solve.py vida_plots " + event_id
    #os.system(cmd)

    #cmd = "python3 Inspect.py merge " + event_id
    #os.system(cmd)

    print("REMOVEING PNGS?")
    cmd = "rm " + solve_dir + "/*.png"
    print(cmd)
    os.system(cmd)

    print("RSYNC EVENT CONTENT (BUFFERED/DELAYED RSYNC)")

    #cloud_dir = solve_dir.replace("/ams2", "/archive.allsky.tv")
    #fp = open(solve_dir + "/rsync.jobs", "a")
    #fp.write ("rsync -auv " + solve_dir + "* " + cloud_dir + "\n")
    #print("BUFFERED WRITE: rsync -auv " + solve_dir + "* " + cloud_dir + "\n")
    #fp.close()

    # uncommet for live rsync
    #cmd = "rsync -auv " + solve_dir + "* " + cloud_dir + "\n"
    #print(cmd)
    #os.system(cmd)




    #update_event(dynamodb, event_id, simple_status, wmpl_status, solve_dir)

def make_css():
   css = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body {
  background-color: #FFFFFF;
}


.container {
  padding: 5px;
  float: left;
  position: relative;
  width: 320px;
}

.image {
  opacity: 1;
  display: block;
  width: 100%;
  height: auto;
  transition: .5s ease;
  backface-visibility: hidden;
}

.middle {
  top: 50%;
  left: 50%;
  width: 100%
  transition: .5s ease;
  opacity: 0;
  position: absolute;
  text-align: center;
  transform: translate(-50%, -50%);
  -ms-transform: translate(-50%, -50%);
}

.container:hover .image {
  opacity: 0.3;
}

.container:hover .middle {
  opacity: 1;
}

.text {
  color: black;
  font-size: 16px;
}
</style>
</head>
<body >


   """
   return(css)

  #background-color: #0c0c0c;

def check_event_status(event):
   # status : 1 = solve success ; 0 = not solved ; -1 = failed solve; 2 = currently being solved
   if event is None:
      ev_status = {}
      ev_status['status'] = 0
      ev_status['lee'] = 0 
      ev_status['cee'] = 0
      return(ev_status)

   print("Checking event status:", event)
   status = 0
   if "solve_status" in event:
       print("Status: ", event['solve_status'])
       if event['solve_status'] == "SUCCESS":
          status = 1
   # check if the event is being worked on now.
   year = event['event_id'][0:4] 
   month = event['event_id'][4:6] 
   day = event['event_id'][6:8] 
   date = year + "_" + month + "_" + day
   local_event_exists = 0
   cloud_event_exists = 0
   legacy_event_dir = None
   cloud_event_dir = "/mnt/archive.allsky.tv/EVENTS/" + year + "/" + month + "/" + day + "/" + event['event_id'] + "/" 
   local_event_dir = "/mnt/f/EVENTS/" + year + "/" + month + "/" + day + "/" + event['event_id'] + "/" 
   if "solution" in event:
      if "solution" in event:
         if event['solution'] != 0:
            if "sol_dir" in event['solution']:
               legacy_event_dir = event['solution']['sol_dir'] + "/" 

      print("LOCAL DIR:", local_event_dir)
      print("CLOUD DIR:", cloud_event_dir)
      if legacy_event_dir is not None:
         if cfe(legacy_event_dir, 1) == 1:
            print("LEGECY DIR:", legacy_event_dir)

      if cfe(local_event_dir, 1) == 0:
         os.makedirs(local_event_dir)

      if cfe(local_event_dir, 1) == 1:
         lf = glob.glob(local_event_dir + "*")
         if len(lf) >= 1:
            local_event_exists = 1
      if cfe(cloud_event_dir, 1) == 1:
         cf = glob.glob(cloud_event_dir + "*")
         if len(cf) >= 1:
            cloud_event_exists = 1
      print("Local event status:", local_event_exists)
      print("CLOUD event status:", cloud_event_exists)
   ev_status = {}
   ev_status['status'] = status
   ev_status['lee'] = local_event_exists
   ev_status['cee'] = cloud_event_exists
   return(ev_status)


def make_event_html(event_json_file ):
   lfn, local_event_dir = fn_dir(event_json_file)
   css = make_css()
   dynamodb = None
   obs_file = event_json_file.replace("-event.json", "-obs.json")
   event_data = load_json_file(event_json_file)

   event_id = event_data['event_id']

   year = event_id[0:4]
   mon = event_id[4:6]
   day = event_id[6:8]
   date = year + "_" + mon + "_" + day
   #HHHH
   solve_dir = local_event_dir 
   xxx = solve_dir.split("/")[-1]


   event = get_event(dynamodb, event_id, 0)

   event_file = solve_dir + event_id + "-event.json"
   event_index_file = solve_dir + "index.html" 
   kml_url = vdir + event_id + "_map.kml"
   kml_file = solve_dir + event_id + "_map.kml"

   sd = solve_dir.split("/")[-1]
   if "." in sd:
      temp = sd.split(".")
      sdd = temp[0]
   else:
      sdd = sd 

   report_file = solve_dir + "/" + sdd + "_report.txt"
   if "/mnt/f" in kml_file:
      kml_file = kml_file.replace("/mnt/f", "")
   if "solution" not in event:
      print("NO SOLUTION IN EVENT!", event)
   else:
      if event["solution"] == 0:
         print("solve failed.")
         return(0)

   orb_link = event['solution']['orb']['link']

   obs_data = event_data['obs']

   sum_html = make_sum_html(event_id, event, solve_dir, obs_data)

   event['obs'] = obs_data
   obs_html = make_obs_html(event_id, event, solve_dir, obs_data)

   center_lat, center_lon = center_obs(obs_data)

   #kml_file = kml_file.replace("/meteor_archive/", "https://archive.allsky.tv/")
   
   map_html = "<div style='clear: both'> &nbsp; </div>"
   map_html += "<div>"
   map_html += "<h2>Trajectory</h2>"
   map_html += "<iframe border=0 src=\"https://archive.allsky.tv/APPS/dist/maps/index.html?mf=" + kml_url + "&zoom=5&&lat=" + str(center_lat) + "&lon=" + str(center_lon) + "&zoom=5\" width=800 height=440></iframe><br><a href=" + kml_url + ">KML DOWNLOAD</a><br>"

   map_html += "</div>"

   if orb_link != "" and orb_link != "#":
      orb_html = "<h2>Orbit</h2>"
      orb_html += "<iframe border=0 src=\"" + orb_link + "\" width=800 height=440></iframe><br><a href=" + orb_link + ">Full Screen</a><br>"
   else:
      orb_html = ""



   plot_html = "<h2>Plots</h2>"
   plot_html += "<div>\n"
   sol_jpgs = glob.glob(solve_dir + "/*.jpg")
   rand = str(time.time())
   for img in sorted(sol_jpgs):
      if "stacked" in img:
         continue
      img = img.replace("/mnt/f/", "https://archive.allsky.tv/")
      if "ground" not in img and "orbit" not in img:
         plot_html += "<div style='float:left; padding: 3px'><img width=600 height=480 src=" + img + "?" + rand + "></div>\n"

   plot_html += "</div>"

   # final report
   if cfe(report_file) == 1:
      rpt = open(report_file) 
      rpt_out = "<div style='clear:both'> &nbsp; </div><br>"

      rpt_out += "<h2>WMPL Report</h2><div><pre>"
      for line in rpt:
         rpt_out += line
      rpt_out += "</pre></div>"
   else:
      rpt_out = ""

   fp = open(event_index_file, "w")
   fp.write(css)
   fp.write(sum_html)
   fp.write(obs_html)
   fp.write(map_html)
   fp.write(orb_html)
   fp.write(plot_html)
   fp.write(rpt_out)
   fp.close() 

def make_sum_html(event_id, event, solve_dir, obs):

   # DEAD FUNCTION??? NOT USED!!! OLD !!! 

   XXX = "xxx"
   tj = event['solution']['traj']
   ob = event['solution']['orb']
   if "duration" in event:
      duration = float(event['duration'])
   else:
      duration = float(0)
   print("EVENT:", event)
   if "start_datetime" not in event:
      print("MISSING start_datetime!")
      return()
   elif len(event['start_datetime']) < 2:
      print("LESS THAN 2 start_datetime!")
      return()

   
   shower_code = event['solution']['shower']['shower_code']
   html = "<h2>Event Summary</h2>"
   html += "<table border=0 padding=3><tr><td>"
   html += "<table border=0 padding=5>"
   html += "<tr><td>Event ID</td>"
   html += "<td>" + str(event_id) + "</td></tr>"
   try:
      html += "<tr><td>Start Time</td>"
      html += "<td>" + str(event['start_datetime'][0]) + "</td></tr>"
   except:
      print("Missing Start datetime")
   html += "<tr><td>Duration</td>"
   html += "<td>" + str(duration) + "</td></tr>"
   html += "<tr><td>Start Height &nbsp; &nbsp; &nbsp; </td>"
   html += "<td>" + str(tj['start_ele']/1000)[0:5] + " km</td></tr>"
   html += "<tr><td>End Height</td>"
   html += "<td>" + str(tj['end_ele']/1000)[0:5] + " km</td></tr>"
   html += "<tr><td>Vel Init</td>"
   html += "<td>" + str(tj['v_init']/1000)[0:5] + " km/s</td></tr>"
   html += "<tr><td>Vel Avg</td>"
   html += "<td>" + str(tj['v_avg']/1000)[0:5] + " km/s</td></tr>"
   html += "<tr><td>Shower</td>"
   html += "<td>" + str(shower_code) + "</td></tr>"
   html += "</table>"

   html += "</td><td> &nbsp; &nbsp; </td><td>"
   html += "<table border=0>"
   html += "<tr><td>Semi Major Axis (a)</td>"
   html += "<td>" + str(ob['a'])[0:5] + "</td></tr>"
   html += "<tr><td>Eccentricty (e)</td>"
   html += "<td>" + str(ob['e'])[0:5] + "</td></tr>"
   html += "<tr><td>Inclination (i)</td>"
   html += "<td>" + str(ob['i'])[0:5] + "</td></tr>"
   html += "<tr><td>Peri (peri)</td>"
   html += "<td>" + str(ob['peri'])[0:5] + "</td></tr>"
   html += "<tr><td>Lon of Asc Node (node) &nbsp; &nbsp; &nbsp; </td>"
   html += "<td>" + str(ob['node'])[0:5] + "</td></tr>"
   html += "<tr><td>(q) &nbsp; &nbsp; &nbsp; </td>"
   html += "<td>" + str(ob['q'])[0:5] + "</td></tr>"
   #html += "<tr><td>q</td>"
   #html += "<td>" + str(ob['q'])[0:5] + "</td></tr>"
   html += "<tr><td>Period (T)</td>"

   if "T" in ob:
      html += "<td>" + str(ob['T'])[0:5] + "</td></tr>"
      print("T IS :", ob['T'])
   else: 
      html += "<td>" + "No Period Value!" + "</td></tr>"
      print("T IS MISSING FOR OB:" )
   html += "<tr><td>Mean Anomaly (M)</td>"
   html += "<td>" + str(ob['mean_anomaly'])[0:5] + "</td></tr>"
   html += "<tr><td>Julian Date (JD)</td>"
   html += "<td>" + str(ob['jd_ref']) + "</td></tr>"

   html += "</table>"
   html += "</td></tr>"
   html += "</table>"

   return(html)

def make_obs_html(event_id, event, solve_dir, obs):

   
   print("MAKE OBS HTML:", obs)
   html = "<h2>Observations</h2>"
   html += "<div>"

   if True:

      blocks = []
      for i in range(0, len(event['stations'])):
         temp = ""
         file = event['files'][i]
         (f_datetime, cam, f_date_str,fy,fmon,fd, fh, fm, fs) = convert_filename_to_date_cam(file)
         station_id = event['stations'][i]
         prev_file = file.replace(".mp4", "-prev.jpg")
         year = file[0:4]
         day = file[0:10]
         #link = remote_urls[station_id] + "/meteors/" + station_id + "/" + day + "/" + file + "/"
         if station_id not in event['obs']:
             print("ERROR: STATION DATA MISSING FROM EVENT OBS!", station_id)
             continue
         if file in event['obs'][station_id] : 
            if len(event['obs'][station_id][file]['azs']) >= 2:
               start_az =  event['obs'][station_id][file]['azs'][0]
               end_az =  event['obs'][station_id][file]['azs'][-1]
               start_el =  event['obs'][station_id][file]['els'][0]
               end_el =  event['obs'][station_id][file]['els'][-1]
               dur =  len(event['obs'][station_id][file]['els']) / 25
            else:
               start_az = 9999
               end_az = 9999
               start_el = 9999
               end_el = 9999
               dur = 0
         else:
            start_az = 9999
            end_az = 9999
            start_el = 9999
            end_el = 9999
            dur = 0

         start_time = event['start_datetime'][i]
         caption =  station_id + "-" + cam + "<br>" + start_time
         caption += "<br> " + str(start_az)[0:5] + " / " + str(start_el)[0:5]
         caption += "<br> " + str(end_az)[0:5] + " / " + str(end_el)[0:5]
         caption += "<br> " + str(dur)[0:5] + " sec" 
         temp += "   <div class='container'>\n "
         temp += "      <img class='image' src=https://archive.allsky.tv/" + station_id + "/METEORS/" + year + "/" + day + "/" + station_id + "_" + prev_file + ">\n"
         temp+="<div class='middle'><div class='text'>" + caption + "</div></div>"

         temp += "   </div>\n"

         blocks.append((caption, temp))

      last_id = None
      for id, block in sorted(blocks, key=lambda x: (x[0]), reverse=False):
         html += block
         #if last_id is not None and last_id != id:
         #   html += "<div style='clear:both'></div><br>"
         last_id = id
      #html += "   <div class='spacer'> &nbsp; </div>\n"

      #html += "</div>\n"
   html += "</div>"



   return(html)

def add_extra_obs(extra_obs, obs):

   #for data in extra_obs:
   #   print("DATA:", data)

   for data in extra_obs:
      print(data)
      station = data['station']
      obs_file = data['file']
      azs = data['azs']
      els = data['els']
      times = data['start_datetime']
      loc = data['loc']
      if station not in obs:
         obs[station] = {}
      if obs_file not in obs[station]:
         obs[station][obs_file] = {}
      obs[station][obs_file]['azs'] = azs
      obs[station][obs_file]['els'] = els
      obs[station][obs_file]['start_datetime'] = times
      obs[station][obs_file]['loc'] = loc
      obs[station][obs_file]['gc_azs'], obs[station][obs_file]['gc_els'] = GC_az_el(obs[station][obs_file]['azs'], obs[station][obs_file]['els'], obs[station][obs_file]['ras'],obs[station][obs_file]['decs'] )
   return(obs)

def convert_dy_obs(dy_obs_data, obs):
   if "station_id" not in dy_obs_data:
      print("MISSING STATION ID!!!!")
      return(obs)
   station = dy_obs_data['station_id']
   fn = dy_obs_data['sd_video_file']
   print("OBS:", obs)

   if station not in obs:
      print("OBS:", obs)
      obs[station] = {}
   if fn not in obs[station]:
      obs[station][fn] = {}

   if "calib" in dy_obs_data:
      calib = dy_obs_data['calib'] 
   else:
      dy_obs_data['calib'] = {}
      calib = {}
   obs[station][fn]['loc'] = dy_obs_data['loc']
   obs[station][fn]['calib'] = dy_obs_data['calib']
   obs[station][fn]['times'] = []
   obs[station][fn]['fns'] = []
   obs[station][fn]['xs'] = []
   obs[station][fn]['ys'] = []
   obs[station][fn]['azs'] = []
   obs[station][fn]['els'] = []
   obs[station][fn]['ras'] = []
   obs[station][fn]['decs'] = []
   obs[station][fn]['ints'] = []
   if "revision" in dy_obs_data:
      obs[station][fn]['revision'] = float(dy_obs_data['revision'])
   else:
      obs[station][fn]['revision'] = 1

   if "meteor_frame_data" in dy_obs_data:
      for row in dy_obs_data['meteor_frame_data']:
         (dt, frn, x, y, w, h, oint, ra, dec, az, el) = row
         obs[station][fn]['times'].append(dt)
         obs[station][fn]['fns'].append(float(frn))
         obs[station][fn]['xs'].append(float(x))
         obs[station][fn]['ys'].append(float(y))
         obs[station][fn]['azs'].append(float(az))
         obs[station][fn]['els'].append(float(el))
         obs[station][fn]['ras'].append(float(ra))
         obs[station][fn]['decs'].append(float(dec))
         obs[station][fn]['ints'].append(float(oint))
      obs[station][fn]['gc_azs'], obs[station][fn]['gc_els'] = GC_az_el(obs[station][fn]['azs'], obs[station][fn]['els'],  obs[station][fn]['ras'], obs[station][fn]['decs'])
   else:
      print("DELETE OBS FROM STATION NO FRAME DATA!!!!", station)
      del obs[station]
      



   return(obs)

def make_orbit_link(event_id, orb):
   if orb['a'] is None:
      link = ""
   else:
      link = "https://orbit.allskycams.com/index_emb.php?name={:s}&epoch={:f}&a={:f}&M={:f}&e={:f}&I={:f}&Peri={:f}&Node={:f}&P={:f}&q={:f}&T={:f}#".format(event_id, orb['jd_ref'], orb['a'], orb['mean_anomaly'], orb['e'], orb['i'], orb['peri'], orb['node'], orb['T'], orb['q'], orb['jd_ref'])
   #try:
   #   link = "https://orbit.allskycams.com/index_emb.php?name={:s}&epoch={:f}&a={:f}&M={:f}&e={:f}&I={:f}&Peri={:f}&Node={:f}&P={:f}&q={:f}&T={:f}#".format(event_id, orb['jd_ref'], orb['a'], orb['mean_anomaly'], orb['e'], orb['i'], orb['peri'], orb['node'], orb['T'], orb['q'], orb['jd_ref'])
   #except:
   #   link = ""
   return(link)

def make_event_json(event_id, solve_dir,ignore_obs):

   import pickle
   jpgs = glob.glob(solve_dir + "/*.jpg")
   jsons = glob.glob(solve_dir + "/*.json")
   pks = glob.glob(solve_dir + "/*.pickle")
   event_file = solve_dir + event_id + "-event.json"
   kml_file = solve_dir + event_id + "-event.kml"
   obs_file = solve_dir + event_id + "_GOOD_OBS.json"

   print("looking in solve dir", solve_dir)

   for js in jsons:
      if "GOOD_OBS.json" in js :
         obs_file = js
         kml_file = js.replace("GOOD_OBS.json", "map.kml")
      if "simple.json" in js:
         sol_file = js

   #print("SOL FILE:", sol_file)
   #print("KML FILE:", kml_file)

   #simple_solve = load_json_file(sol_file)
   
   print("MAKE EVENT JSON OBS FILE:", obs_file)
   if os.path.exists(obs_file):
      as_obs = load_json_file(obs_file)
   else:
      as_obs = {}

   #event_file = sol_file.replace("-simple.json", "-event.json")

   #print("OBS:", as_obs) 
   #print("SIMPLE:", simple_solve) 

   points = []
   lines = []
   

   station_data = {}
   for station_id in as_obs:
      for file in as_obs[station_id]:
         obs_key = station_id + "_" + file
         if obs_key in ignore_obs:
            status = "BAD"
         else:
            status = ""
         if station_id not in station_data:
            print(station_id)
            obs_data = as_obs[station_id][file]
            lat, lon, alt = obs_data['loc']
            station_data[station_id] = obs_data['loc']
            points.append((lon,lat,alt,status + station_id))

   if False:
      durs = []
      ss_lines = []
      for ss in simple_solve:
         print(ss)
         sol_key, start_lat, start_lon, start_ele, end_lat, end_lon, end_ele, dist, dur, vel = ss 
         durs.append(dur)
         (   skey1,skey2) = sol_key.split("_")
         station1,cam1 = skey1.split("-")
         station2,cam2 = skey2.split("-")
         ol_start_lat = station_data[station2][0]
         ol_start_lon = station_data[station2][1]
         ol_start_alt = station_data[station2][2]
         line_desc = "OL:" + sol_key
         ss_lines.append((ol_start_lon,ol_start_lat,ol_start_alt,start_lon,start_lat,start_ele,line_desc))
         ss_lines.append((ol_start_lon,ol_start_lat,ol_start_alt,end_lon,end_lat,end_ele,line_desc))

         line_desc = "SS:" + sol_key
      
         ss_lines.append((start_lon,start_lat,start_ele,end_lon,end_lat,end_ele,line_desc))

      if len(durs) > 0:
         duration = float(max(durs) / 25)
      else:
         duration = float(0)

   solution = {}
   solution['event_id'] = event_id
   #solution['duration'] = float(duration)
   solution['sol_dir'] = solve_dir 
#   solution['obs'] = as_obs
   #solution['simple_solve'] = simple_solve
   solution['traj'] = {}
   solution['orb'] = {}
   solution['rad'] = {}
   solution['plot'] = glob.glob(solve_dir)
   solution['shower'] = {}

   if len(pks) == 0:
      print("WMPL FAILED. NO EVENT JSON MADE.")
      fail_file = solve_dir + event_id + "-fail.json"
      fail = {}
      fail['failed'] = 1 
      print("WMPL FAIL FILE:", fail_file)
      save_json_file(fail_file, fail)

      #cloud_dir = solve_dir.replace("/ams2/", "/archive.allsky.tv/")
      #cmd = "rsync -auv " + solve_dir + "* " + cloud_dir 
      #os.system(cmd)

      #cloud_dir = solve_dir.replace("/ams2", "/archive.allsky.tv")
      #fp = open(solve_dir + "rsync.jobs", "a")
      #fp.write ("rsync -auv " + solve_dir + "* " + cloud_dir + "\n")
      #print("BUFFERED WRITE: rsync -auv " + solve_dir + "* " + cloud_dir + "\n")
      #fp.close()

      return(0)

   f = open(pks[0], 'rb')
   traj = pickle.load(f)

   html = "<PRE>"
   pdata = vars(traj)

   solution['traj']['start_lat'] = float(np.degrees(traj.rbeg_lat))
   solution['traj']['start_lon'] = float(np.degrees(traj.rbeg_lon))
   solution['traj']['start_ele'] = float(traj.rbeg_ele)

   solution['traj']['end_lat'] = float(np.degrees(traj.rend_lat))
   solution['traj']['end_lon'] = float(np.degrees(traj.rend_lon))
   solution['traj']['end_ele'] = float(traj.rend_ele)

   lines.append(( float(np.degrees(traj.rbeg_lon)), float(np.degrees(traj.rbeg_lat)), float(traj.rbeg_ele), float(np.degrees(traj.rend_lon)), float(np.degrees(traj.rend_lat)), float(traj.rend_ele), "WMPL"))

   # get 3d points for traj
   for obs in traj.observations:

      # Go through all observed points
      for i in range(obs.kmeas):

         point_info = []
 
         # FN
         point_info.append("{:3d}".format(i))

         point_info.append("{:>10s}".format(str(obs.station_id)))

         #point_info.append("{:>7d}".format(obs.ignore_list[i]))

         #point_info.append("{:9.6f}".format(obs.time_data[i]))
         #point_info.append("{:20.12f}".format(obs.JD_data[i]))

         #point_info.append("{:9.5f}".format(np.degrees(obs.meas1[i])))
         #point_info.append("{:9.5f}".format(np.degrees(obs.meas2[i])))

         #point_info.append("{:22.5f}".format(np.degrees(obs.azim_data[i])))
         #point_info.append("{:9.5f}".format(np.degrees(obs.elev_data[i])))

         #point_info.append("{:15.5f}".format(np.degrees(obs.model_azim[i])))
         #point_info.append("{:14.5f}".format(np.degrees(obs.model_elev[i])))

         #point_info.append("{:12.5f}".format(np.degrees(obs.ra_data[i])))
         #point_info.append("{:+13.5f}".format(np.degrees(obs.dec_data[i])))

         #point_info.append("{:13.5f}".format(np.degrees(obs.model_ra[i])))
         #point_info.append("{:+14.5f}".format(np.degrees(obs.model_dec[i])))

         #point_info.append("{:11.2f}".format(obs.model_eci[i][0]))
         #point_info.append("{:11.2f}".format(obs.model_eci[i][1]))
         #point_info.append("{:11.2f}".format(obs.model_eci[i][2]))

         #point_info.append("{:14.6f}".format(np.degrees(obs.model_lat[i])))
         #point_info.append("{:+15.6f}".format(np.degrees(obs.model_lon[i])))
         #point_info.append("{:10.2f}".format(obs.model_ht[i]))
         #point_info.append("{:10.2f}".format(obs.model_range[i]))


         #points.append(( float(np.degrees(obs.model_lon[i])), float(np.degrees(obs.model_lat[i])), float(obs.model_ht[i]), "3DP:" + str(obs.station_id) + "_{:03d}".format(i)))
         points.append(( float(np.degrees(obs.model_lon[i])), float(np.degrees(obs.model_lat[i])), float(obs.model_ht[i]), "3DP:" + str(obs.station_id) + "_{:3d}".format(i)))

         #point_info.append("{:10.2f}".format(obs.length[i]))
         #point_info.append("{:19.2f}".format(obs.state_vect_dist[i]))
         #point_info.append("{:8.2f}".format(obs.lag[i]))

         #point_info.append("{:9.2f}".format(obs.velocities[i]))
         #point_info.append("{:18.2f}".format(obs.velocities_prev_point[i]))

         #point_info.append("{:9.2f}".format(obs.h_residuals[i]))
         #point_info.append("{:9.2f}".format(obs.v_residuals[i]))
         #point_info.append("{:14.2f}".format(3600*np.degrees(obs.ang_res[i])))




   folder_name = "WMPL Solver"
   make_kml(kml_file, points, lines, folder_name)
   #print("SHOWER:" , traj.orbit.la_sun, traj.orbit.L_g, traj.orbit.B_g, traj.orbit.v_g)
   if traj.orbit.la_sun is not None:
      shower_obj = associateShower(traj.orbit.la_sun, traj.orbit.L_g, traj.orbit.B_g, traj.orbit.v_g)

      if shower_obj is None:
         shower_no = -1
         shower_code = '...'
      else:
         shower_no = shower_obj.IAU_no
         shower_code = shower_obj.IAU_code
   else:
         shower_no = -1
         shower_code = '...'



   #solution['kml']['points'] = points
   #solution['kml']['lines'] = lines

   solution['shower'] = {}
   solution['shower']['shower_no'] = float(shower_no)
   solution['shower']['shower_code'] = shower_code


   solution['traj']['v_init'] = float(traj.v_init)
   solution['traj']['v_avg'] = float(traj.v_avg)

   solution['orb']['jd_ref'] = traj.orbit.jd_ref
   if traj.orbit.la_sun is not None:
      solution['orb']['la_sun'] = np.degrees(traj.orbit.la_sun)
      solution['orb']['i'] = float(np.degrees(traj.orbit.i))
      solution['orb']['peri'] = float(np.degrees(traj.orbit.peri))
      solution['orb']['node'] = float(np.degrees(traj.orbit.node))
      solution['orb']['pi'] = float(np.degrees(traj.orbit.pi))
      solution['orb']['true_anomaly'] = float(np.degrees(traj.orbit.true_anomaly))
      if math.isnan(solution['orb']['true_anomaly']):
         solution['orb']['true_anomaly'] = 0
   else:
      solution['orb']['la_sun'] = 0
      solution['orb']['i'] = 0
      solution['orb']['peri'] = 0
      solution['orb']['node'] = 0
      solution['orb']['pi'] = 0
      solution['orb']['true_anomaly'] = 0
   solution['orb']['a'] = traj.orbit.a
   solution['orb']['e'] = traj.orbit.e
   solution['orb']['q'] = traj.orbit.q
   solution['orb']['Q'] = traj.orbit.Q
   if traj.orbit.true_anomaly is not None:
      if math.isnan(traj.orbit.true_anomaly) is True:
         solution['orb']['true_anomaly'] = 0
   if solution['orb']['true_anomaly'] == 0:
      solution['orb']['eccentric_anomaly'] = 0
      solution['orb']['mean_anomaly'] = 0
      solution['orb']['T'] = 0 
   else:
      if traj.orbit.eccentric_anomaly is not None and math.isnan(traj.orbit.eccentric_anomaly) is False:
         solution['orb']['eccentric_anomaly'] = float(np.degrees(traj.orbit.eccentric_anomaly))

         solution['orb']['mean_anomaly'] = float(np.degrees(traj.orbit.mean_anomaly))
      else:
         solution['orb']['eccentric_anomaly'] = 0
         solution['orb']['mean_anomaly'] = 0

   if traj.orbit.T is None:
      print("T IS NONE!")
      traj.orbit.T = 0
   if math.isnan(traj.orbit.T):
      print("T IS NAN!")
   if traj.orbit.T is not None:
      if math.isnan(traj.orbit.T) is True:
         solution['orb']['T'] = 0 
      else:
         solution['orb']['T'] = traj.orbit.T

   solution['rad']['apparent_ECI'] = {}
   solution['rad']['apparent_ECI']['ra'] = traj.orbit.ra
   solution['rad']['apparent_ECI']['dec'] = traj.orbit.dec
   solution['rad']['apparent_ECI']['v_avg'] = traj.orbit.v_avg
   solution['rad']['apparent_ECI']['v_inf'] = traj.orbit.v_inf
   solution['rad']['apparent_ECI']['azimuth_apparent'] = traj.orbit.azimuth_apparent
   solution['rad']['apparent_ECI']['elevation_apparent'] = traj.orbit.elevation_apparent

   solution['rad']['geocentric'] = {}
   solution['rad']['geocentric']['ra_g'] = traj.orbit.ra_g
   solution['rad']['geocentric']['dec_g'] = traj.orbit.dec_g
   solution['rad']['geocentric']['v_g'] = traj.orbit.v_g

   solution['rad']['ecliptic_geo'] = {}
   solution['rad']['ecliptic_geo']['L_g'] = traj.orbit.L_g
   solution['rad']['ecliptic_geo']['B_g'] = traj.orbit.B_g
   solution['rad']['ecliptic_geo']['v_h'] = traj.orbit.v_h

   solution['rad']['ecliptic_helio'] = {}
   solution['rad']['ecliptic_helio']['L_h'] = traj.orbit.L_h
   solution['rad']['ecliptic_helio']['B_h'] = traj.orbit.B_h
   solution['rad']['ecliptic_helio']['v_h_x'] = traj.orbit.v_h_x
   solution['rad']['ecliptic_helio']['v_h_y'] = traj.orbit.v_h_y
   solution['rad']['ecliptic_helio']['v_h_z'] = traj.orbit.v_h_z


   print(traj.orbit.e)
   print(traj.orbit.i)
   print(traj.orbit.peri)
   print(traj.orbit.node)
   print(traj.orbit.pi)
   print(traj.orbit.q)
   print(traj.orbit.Q)
   print(traj.orbit.true_anomaly)
   print(traj.orbit.eccentric_anomaly)
   print(traj.orbit.mean_anomaly)
   print("T", traj.orbit.T)
   print("TJ", traj.orbit.Tj)
   for line in str(traj.orbit).split("\n"):
      print("ORB:", line)

   ef , xxx = fn_dir(event_file)
   sol_name = ef[0:20]
   orb_link = make_orbit_link(ef, solution['orb'])
   solution['orb']['link'] = orb_link

   for obs in traj.observations:
      print(obs.station_id, obs.time_data)

   solution['event_id'] = event_id
   #solution['obs'] = as_obs
   save_json_file(event_file, solution)
   print("SAVED EVENT FILE:", event_file)
   return(solution,as_obs)

def make_kml(kml_file, points, lines, folder_name):
   import simplekml
   kml = simplekml.Kml()
   main_folder = kml.newfolder(name=folder_name)
   used = {}

   pc = 0
   colors = ['ff0b86b8', 'ffed9564', 'ff0000ff', 'ff00ffff', 'ffff0000', 'ff00ff00', 'ff800080', 'ff0080ff', 'ff336699', 'ffff00ff' ]
   # add station points 

   station_folders = {}

   for point in points:
      lon,lat,alt,station = point
      if "BAD" in station:
         status = "BAD"
         station = station.replace("BAD", "")
      else:
         status = "GOOD"
      if station not in used and "3DP:" not in station:
         station_folders[station] = main_folder.newfolder(name=station)
         color = colors[pc]
         pnt = station_folders[station].newpoint(name=station, coords=[(lon,lat,alt)])
         pnt.description = station
         pnt.style.labelstyle.color=color
#simplekml.Color.darkgoldenrod
         pnt.style.labelstyle.scale = 1
         if status == "BAD":
            pnt.style.iconstyle.icon.href = 'http://maps.google.com/mapfiles/kml/shapes/forbidden.png'
            pnt.style.iconstyle.color='ff0000ff'
         else:
            pnt.style.iconstyle.icon.href = 'https://maps.google.com/mapfiles/kml/shapes/placemark_circle.png'
            pnt.style.iconstyle.color=color
         pnt.altitudemode = simplekml.AltitudeMode.relativetoground

         used[station] = color
         pc += 1
         if pc >= len(colors):
            pc = 0
   linestring = {}
   lc = 0

   # add 3D points
   not_used = []
   for point in points:
      lon,lat,alt,station = point
      if "3DP:" in station:
         if "_" in station:
            tstation = station.split("_")[0]
            tstation = tstation.replace("3DP:", "")
         else:
            tstation = station
         print("S/T STATION:", station, tstation)
         if tstation in used:
            color = used[tstation]
         else: 
            color = "ff000000"
            not_used.append(station)
            continue 

         pnt = station_folders[tstation].newpoint(name="", coords=[(lon,lat,alt)])
         pnt.description = "" 
         pnt.style.labelstyle.color=color
#simplekml.Color.darkgoldenrod
         pnt.style.labelstyle.scale = 1
         pnt.style.iconstyle.icon.href = 'https://maps.google.com/mapfiles/kml/shapes/placemark_circle.png'
         pnt.style.iconstyle.color=color
         pnt.altitudemode = simplekml.AltitudeMode.relativetoground

         #used[station] = color
         pc += 1
         if pc >= len(colors):
            pc = 0
   print("NOT USED STATIONS:", not_used)
   line_folder = main_folder.newfolder(name="Trajectory")
   for line in lines:
      (lon1,lat1,alt1,lon2,lat2,alt2,line_desc) = line
      if "vect" in line_desc:
         linestring[lc] = line_folder.newlinestring(name="")
      else:
         linestring[lc] = line_folder.newlinestring(name=line_desc)
      linestring[lc].coords = [(lon1,lat1,alt1),(lon2,lat2,alt2)]
      linestring[lc].altitudemode = simplekml.AltitudeMode.relativetoground

      if "SS" in line_desc:
         linestring[lc].extrude = 0
         linestring[lc].style.linestyle.color=simplekml.Color.red
         linestring[lc].style.linestyle.width=2
      elif "WMPL" in line_desc:
         linestring[lc].style.linestyle.color=simplekml.Color.darkred
         linestring[lc].style.linestyle.width=5

      else:
         print("BLUE!")
         linestring[lc].extrude = 0
         if "end" in line_desc:
            linestring[lc].style.linestyle.color=simplekml.Color.goldenrod
         else:
            linestring[lc].style.linestyle.color=simplekml.Color.darkgoldenrod
      lc += 1
   kml.save(kml_file)
   print("saved", kml_file)

def check_fix_plots(event_id):
   
   year = event_id[0:4]
   month = event_id[4:6]
   day = event_id[6:8]
   event_dir = "/mnt/archive.allsky.tv/EVENTS/" + year + "/" + month + "/" + day + "/" + event_id + "/"
   local_event_dir = "/mnt/f/EVENTS/" + year + "/" + month + "/" + day + "/" + event_id + "/"
   print("EVENT ID:", event_id)
   print("EVDIR:", event_dir)
   print("LOCAL:", local_event_dir)

   if cfe(event_dir,1) == 1:
      ev_files = glob.glob(event_dir + "*")
      print("EVENT FILES:", ev_files)
      for ev_file in ev_files:
         if "index.html" in ev_file or "gz" in ev_file or "ALL" in ev_file or "AMS" in ev_file:
            continue
         ev_fn = ev_file.split("/")[-1]
         pl_id = ev_fn[0:15]
         if pl_id != event_id:
            print("PROB:", ev_fn, pl_id)
            new_file = ev_file.replace(pl_id, event_id)
            if ev_file != new_file:
               cmd = "mv " + ev_file + " " + new_file
               print("MOVE2", cmd)
               os.system(cmd)
         else:
            print("Good:", ev_fn, pl_id)

   if cfe(local_event_dir,1) == 1:
      ev_files = glob.glob(local_event_dir + "*")
      for ev_file in ev_files:
         if "index.html" in ev_file or "gz" in ev_file or "ALL" in ev_file or "AMS" in ev_file:
            continue
         ev_fn = ev_file.split("/")[-1]
         pl_id = ev_fn[0:15]
         if pl_id != event_id:
            print("PROB:", ev_fn, pl_id)
            new_file = ev_file.replace(pl_id, event_id)
            if ev_file != new_file:
               cmd = "mv " + ev_file + " " + new_file
               print("MOVE3")
               print(cmd)
               os.system(cmd)
         else:
            print("Good:", ev_fn, pl_id)


def event_id_to_date(event_id):
   year = event_id[0:4]
   mon = event_id[4:6]
   day = event_id[6:8]
   date = year + "_" + mon + "_" + day
   return(date)

def event_report(dynamodb, event_id, solve_dir, event_final_dir, obs):

    #orb_link = event['solution']['orb']['link']
    year = event_id[0:4]
    day = event_id_to_date(event_id)

    template = ""
    solve_dir = solve_dir.replace("//", "/")
    tt = open("./FlaskTemplates/allsky-template-v2.html")
    for line in tt:
       template += line

    template = template.replace("AllSkyCams.com", "AllSky.com")
    template = template.replace("{TITLE}", "ALLSKY EVENT " + event_id)

    print("EVREPORT:")
    print("SOLVE DIR:", solve_dir)
    print("FINAL DIR:", event_final_dir)


    final_event_id = event_final_dir.split("/")[-1]
    if final_event_id == "":
       final_event_id = event_final_dir.split("/")[-2]
       event_id = final_event_id
    if final_event_id == "":
       final_event_id = event_final_dir.split("/")[-2]
    event_id = final_event_id

    print("FINAL ID:", final_event_id)
    print("EVENT ID:", event_id)
 
    event_data_file = solve_dir + event_id + "-event.json"
    failed_data_file = solve_dir + event_id + "-fail.json"
    if os.path.exists(event_data_file):
       event_json = load_json_file(event_data_file)

       if "orb" in event_json:
          wmpl_status = "SOLVED"
    elif os.path.exists(failed_data_file) is True:
       event_json = {}
       wmpl_status = "FAILED"
    else:
       event_json = {}
       wmpl_status = "PENDING"

    event = {}
    event['solution'] = event_json

    #event = get_event(dynamodb, event_id, 0)



    print("EVENT:", event)
    if len(event) == 0:
       print("EVENT SOLUTION NOT FOUND!?")
       orb_link = ""
    else:
       if "orb" in event['solution']:
          orb_link = event['solution']['orb']['link']
       else:
          orb_link = ""

    obs_data_file = solve_dir + event_id + "_OBS_DATA.json"
    planes_data_file = solve_dir + event_id + "_PLANES.json"

    if os.path.exists(obs_data_file) is True:
       zobs_data = load_json_file(obs_data_file)
    else:
       zobs_data = []
    if os.path.exists(planes_data_file) is True:
       planes_data = load_json_file(planes_data_file)
    else:
       planes_data = {}

    plane_points = []
    failed_combos = []
    if "results" in planes_data:
       for pk in planes_data['results']:
          score, points = planes_data['results'][pk]
          print("POINTS:", points)
          if type(points) == int:
             failed_combos.append(pk)

          elif len(points) == 2:
             start_point, end_point = points
             plane_points.append((start_point, end_point))

    print(plane_points)
    if len(plane_points) > 0:
       status_3d = "Passed with " +  str(len(plane_points)) + " planes"
    else:
       status_3d = "Failed with " +  str(len(plane_points)) + " planes"


    
    good_2d = []

    for obs_id in zobs_data:
       #if "az_start_point, az_end_point obs_start_points obs_end_points
       print(obs_id, zobs_data[obs_id]['obs_start_points'],  zobs_data[obs_id]['obs_end_points'])
       if "obs_start_points" in zobs_data[obs_id] and "obs_end_points" in zobs_data[obs_id]:
          if len(zobs_data[obs_id]) > 0 and len(zobs_data[obs_id]) > 0: 
             print("GOOD?")
             good_2d.append(obs_id)

    if len(good_2d) > 0:
       status_2d = "Passed with " + str(len(good_2d)) + " Intersections"
    else: 
       status_2d = "Failed with " + str(len(good_2d)) + " Intersections"

    #solve_dir = solve_dir.replace("/mnt/f/", "")
    vdir = "https://archive.allsky.tv/" + solve_dir.replace("/mnt/f/", "") 
    #kml_file = solve_dir + event_id + "_map.kml"
    kml_file = vdir + event_id + "_map.kml"
    print("KML", kml_file)

    if orb_link != "" and orb_link != "#":
       #orb_html = "<div><h2>Orbit</h2>"
       orb_html = """<div style="width:80%; margin:0 auto; margin-top: 100px;">"""
       orb_html += "<h2>Orbit</h2>" 
       orb_html += "<iframe border=0 src=\"" + orb_link + "\" width=100% height=440></iframe><br><a href=" + orb_link + ">Full Screen</a><br></div>"
    else:
       orb_html = ""


    json_conf = load_json_file("../conf/as6.json")
    remote_urls = {}
    if "remote_urls" in json_conf['site']:
       for i in range(0, len(json_conf['site']['multi_station_sync'])):
          station = json_conf['site']['multi_station_sync'][i]
          if i in json_conf['site']['remote_urls']:
             url = json_conf['site']['remote_urls'][i]
          else: 
             url = ""
          remote_urls[station] = url
          print(station, url)

    solved_files = glob.glob(solve_dir + "/*")
    print(solve_dir + "*", solved_files)
    html = ""
    #html = """</div>\n"""
    html += """<div style='clear: both'> &nbsp;</div>\n"""
    html = """<div style="width:80%; margin:0 auto; margin-top: 100px;">"""
    
    #html += """<div>\n"""

    html += """<div style='clear: both; '> &nbsp;</div>\n"""

    #obs_html = """<div> <!-- start obs container-->\n"""
    obs_html = """<h2 style="margin-top: 100px">Observations</h2>\n"""

    obs_html += """<div style="width:80%; margin:0 auto; 100px; background: black; border: 1px #ffffff solid;">"""

    video_links = []

    temp =  {}
    st_list = ""
    for station_id in obs:
       if st_list != "":
          st_list += ", "
       if station_id not in temp:
          st_list += station_id 
       temp[station_id] = 1

 
    for station_id in obs:
       for obs_file in obs[station_id]:
          if len(obs[station_id].keys()) > 1:
             best_file = get_best_obs(obs[station_id])
          else:
             best_file = obs_file 

          prev_file = obs_file.replace(".mp4", "-prev.jpg")
          year = obs_file[0:4]
          day = obs_file[0:10]
          if station_id in remote_urls:
             link = remote_urls[station_id] + "/meteors/" + station_id + "/" + day + "/" + obs_file + "/"
          else:
             link = ""
          img_id = station_id + "_" + prev_file.replace(".jpg", "")
          img_link = "https://archive.allsky.tv/" + station_id + "/METEORS/" + year + "/" + day + "/" + station_id + "_" + prev_file 
          video_link = "https://archive.allsky.tv/" + station_id + "/METEORS/" + year + "/" + day + "/" + station_id + "_" + prev_file.replace("-prev.jpg", "-180p.mp4") 
          video_links.append(video_link)
          obs_html += """
           <div id="{:s}" style="
              float: left;
              background: black;
              background-image: url('{:s}');
              background-repeat: no-repeat;
              background-size: 320px;
              width: 320px;
              height: 180px;
              margin: 25px; 
              opacity: 1; 
              ">
              {:s} {:s}
           </div>
          """.format(img_id, img_link, station_id, obs_file)
          #html += "<img src=https://archive.allsky.tv/" + station_id + "/METEORS/" + year + "/" + day + "/" + station_id + "_" + prev_file + "></a>"
          #html += "<hr>"
          #obs_html += """<div style='clear: both'> &nbsp;</div>\n"""

    obs_html += "\n</div> <!-- END OBS-->"


    jpgs = []
    for sf in solved_files:
       print("SOLVED FILE:", sf)
       if final_event_id not in sf:
          print("EVENT ID MISMATCH:", sf, final_event_id)
       if "png" in sf:
          jpg_f = sf.replace(".png", ".jpg")
          jpgs.append(jpg_f)
          cmd = "convert " + sf + " -resize 600x600 -quality 60 " + jpg_f
          #if cfe(jpg_f) == 0:
          if True:
             print(cmd)
             os.system(cmd)
          else:
             print(jpg_f, " already made.")
    check_fix_plots(final_event_id)
    solved_files = glob.glob(solve_dir + "/*")
    print("SOLVED FILES:", solved_files)
    print("MOVE THE WMPL FILES TO THE FINAL EVENT DIR!")
    final_jpgs = []

    # move png to jpgs 
    for sf in solved_files:
       print("SOLVED FILE:", sf)
       if "AMS" in sf:
          continue
       fn, xxx = fn_dir(sf)
       fn = fn.replace(".png", ".jpg")
       new_file = event_final_dir + fn 

       cmd = "mv " + sf + " " + event_final_dir

       if sf != event_final_dir + fn and "png" not in fn:
          print("MOVE11:", cmd)
          os.system(cmd)
       if "jpg" in fn:
          final_jpgs.append(new_file)
       print(cmd)

    used = {}
    prev_files = []
    roi_files = []
    marked_files = []
    fov_files = []
    review_files = []
    all_prev_html = "<h2>All Observations</h2>"



    # add map to html

    center_lat, center_lon = center_obs(obs)
 

    map_html = "<div style='clear: both'> &nbsp; </div>"
   

    #map_html += "<div>"
    map_html = """<h2 style="margin-top: 100px">Trajectory</h2>"""
    map_html += """<div style="border: 1px #ffffff solid; background: black; width:80%; margin:0 auto; ">"""
    map_html += "<iframe border=0 src=\"https://archive.allsky.tv/APPS/dist/maps/index.html?mf=" + kml_file + "&zoom=5&&lat=" + str(center_lat) + "&lon=" + str(center_lon) + "&zoom=5\" width=100% height=440></iframe>"
    map_html += "</div>"
    map_html += "<a href=" + kml_file + ">KML Download</a><br>"


    plot_html = """<h2 style="margin-top: 100px">Plots</h2>"""
    plot_html += """<div style="width:80%; margin:0 auto; text-align: center; background: black; border: 1px #ffffff solid;">"""

    trash_html = ""
    for jpg in sorted(final_jpgs):
       if "stacked" in jpg:
          continue

       jpg = jpg.replace("/mnt/f/meteor_archive/", "")
       jpg_fn = jpg.split("/")[-1]
       ftype = None
       if "prev" in jpg: 
          ftype = "PREV"
          #all_prev_html += """<img src=""" + jpg_fn + """?""" + str(time.time()) + ">\n"""
          #img_id = station_id + "_" + prev_file.replace(".jpg", "")

          img_id = station_id + "_" + jpg_fn.replace(".jpg", "")
          img_link = "https://archive.allsky.tv/" + station_id + "/METEORS/" + year + "/" + day + "/" + station_id + "_" + jpg_fn 
          trash_html += """
            <div id="{:s}" style="
              float: left;
              background-image: url('{:s}');
              background-repeat: no-repeat;
              background-size: 320px;
              width: 320px;
              height: 180px;
              margin: 25px;
              opacity: 1;
              ">
              {:s}
            </div>
          """.format(img_id, img_link, station_id)


          prev_files.append(jpg)


       elif "marked" in jpg: 
          ftype = "MARKED"
          marked_files = 1
       elif "REVIEW" in jpg: 
          ftype = "REV"
          review_files = 1
       elif "roi" in jpg: 
          ftype = "ROI"
          roi_files = 1
       elif "FOV" in jpg: 
          ftype = "FOV"
          fov_files = 1
       elif jpg_fn not in used:
          ftype = "GRAPH"
       if ftype == "GRAPH":
           plot_html += """<div style="float:left; padding: 5px; text-align: center;"><img width="320" height=250 src=""" + jpg_fn + """?" + str(time.time()) + "></div>\n"""
       used[jpg_fn] = 1

    plot_html += """</div><div style="clear:both; margin: 25px">&nbsp;</div>"""


    report_file = solve_dir + event_id + "_report.txt"


    report_html = """<div style="width:80%; margin:0 auto; margin-top: 200px">"""
    report_html = "<h2>WMPL Report</h2>"
    report = """<pre class='bash' style="height: 400px">"""
    if os.path.exists(report_file) is True :
       rpt = open(report_file)
       for line in rpt:
          report += line 
    else:
       print("REPORT FILE NOT FOUND!", report_file, "FAIL")
       #exit()
       report = "Event solution failed or has not run."
    report += "</pre></div>"
    print("REPORT:", report)

    report_html += "<p>"
    #html += "<pre> WMPL REPORT\n" + report + "</pre>"
    report_html += report

    start_time = ""
    prev_video = video_preview_html_js(video_links)
    results_2d = ""
    planes_3d = ""
    wmpl_status = ""

    evs_html = "<h2>Event Summary </h2>\n"
    if "start_datetime" in event:
       all_start_time = min(event['start_datetime'])
       all_all = []
       for dd in all_start_time:
          all_all.append(dd)
          print(dd)
       start_time = min(all_all) 
       print("START TIME:", start_time) 
    else:
       start_time = ""


    # Plane files

    evs_html += """
       <div style="border: 1px #ffffff solid; background: black">

       <div style="float:left; background: black; color: white;">
          <table class="table" width="100%" style="color: white;">
       <tr>
          <td>
             Event ID :
          </td>
          <td>
             {:s} 
          </td>
       </tr>
       <tr>
          <td>
             Start Time:
          </td>
          <td>
             {:s} 
          </td>
       </tr>
       <tr>
          <td>
             Stations: 
          </td>
          <td>
             {:s}
          </td>
       </tr>
       <tr>
          <td>
             Status 2D: </td><td>{:s} </td>
       </tr>
       <tr>
          <td>
             3D Planes : </td><td> {:s} </td>
       </tr>
       <tr>
          <td>
             WMPL Solve Status: </td><td> {:s} </td>
       </tr>
       </table>
       </div> 

       <div style="float:left">

       <!--
       Ending Altitude : XXX <BR>
       Velocity : XXX <BR>
       Shower : XXX <BR>
       a: XXX <BR>
       e: XXX <BR>
       i: XXX <BR>
       q: XXX <BR>
       Publishing Status: <BR>
       -->


       </div>
       <div>
       {:s}
       </div>
       </div>

    """.format(event_id, str(start_time), st_list,  status_2d, status_3d, wmpl_status, prev_video)
    evs_html += "</div>\n"

    html += evs_html 

    html += obs_html 
    html += """<div style="clear: both;"> &nbsp; </div>"""

    html += map_html
    html += orb_html
    html += plot_html
    html += report_html 




    fp = open(solve_dir + "/index.html", "w")

    final_html = template.replace("{MAIN_CONTENT}", html)

    fp.write(final_html)


    print("SAVED INDEX:", event_final_dir + "/index.html")
    print("REPORT IS :", report)
    print("SOLVED FILES:", solved_files)
    # delete PNGS
    pngs = glob.glob(event_final_dir + "*.png")
    for png in pngs:
       cmd = "rm " + png
       os.system(cmd)


    # sync data to cloud
    #cloud_final_dir = event_final_dir.replace("/mnt/f/", "/mnt/archive.allsky.tv/")
    #cmd = "rsync -auv " + event_final_dir + " " + cloud_final_dir
    #print(cmd)

    #cloud_dir = solve_dir.replace("/ams2", "/archive.allsky.tv")
    #fp = open(solve_dir + "rsync.jobs", "a")
    #cloud_dir = solve_dir.replace("/ams2", "/archive.allsky.tv")
    #fp.write ("rsync -auv " + event_final_dir + "* " + cloud_final_dir + "\n")
    #print("BUFFERED WRITE: rsync -auv " + event_final_dir + "* " + cloud_final_dir + "\n")
    #fp.close()

def make_obs_table(obs):
   obs_header = """
      <table border=1>
      <tr>
         <th>Station</td>
         <th>File</td>
         <th>Time</td>
         <th>AZ</td>
         <th>EL AZ</td>
         <th>GC AZ</td>
         <th>GC EL AZ</td>
         <th>Intensity</td>
      </tr>
   """
   obs_html = ""
   for station in obs:
      obs_html += "<h1>" + station + "</h1>" + obs_header
      if len(obs[station].keys()) > 1:
         best = " * "
         for obs_file in obs[station]:
            best_file = obs_file
      else:
         best_file = get_best_obs(obs[station])
         best = " - " 

      for obs_file in obs[station]:
         if best_file == obs_file:
            print("BEST:", station, best_file, obs_file)
            best = " * " 
         else:
            best = " - " 
         for i in range(0,len(obs[station][obs_file]['azs'])): 
            time = obs[station][obs_file]['times'][i]
            az = obs[station][obs_file]['azs'][i]
            el = obs[station][obs_file]['els'][i]
            if "gc_azs" in obs[station][obs_file] : #and i <= len(obs[station][obs_file]['gc_azs']) - 1:
               gc_az = obs[station][obs_file]['gc_azs'][i]
               gc_el = obs[station][obs_file]['gc_els'][i]
            else:
               gc_az = obs[station][obs_file]['azs'][i]
               gc_el = obs[station][obs_file]['els'][i]
            flux = obs[station][obs_file]['ints'][i]
            obs_html += """
               <tr>
                  <td>{:s}</td>
                  <td>{:s}{:s}</td>
                  <td>{:s}</td>
                  <td>{:s}</td>
                  <td>{:s}</td>
                  <td>{:s}</td>
                  <td>{:s}</td>
                  <td>{:s}</td>
               </tr>
            """.format(station, best, obs_file, time, str(az)[0:6], str(el)[0:6], str(gc_az)[0:6], str(gc_el)[0:6], str(flux)[0:6])
      obs_html += "</table>"
      #obs_html += obs_header
   return(obs_html)

def WMPL_solve(event_id, obs,time_sync=1, force=0, dynamodb=None):
    time_sync = 1
    if dynamodb is None:
       dynamodb = boto3.resource('dynamodb')

    json_conf = load_json_file("../conf/as6.json")
    ams_id  = json_conf['site']['ams_id']

    year = event_id[0:4]
    mon = event_id[4:6]
    day = event_id[6:8]
    date = year + "_" + mon + "_" + day

    event_final_dir = "/mnt/f/EVENTS/" + year + "/" + mon + "/" + day + "/" + event_id + "/"
    solve_dir = "/mnt/f/EVENTS/" + year + "/" + mon + "/" + day + "/" + event_id + "/"
    solve_file = solve_dir + event_id + "-event.json"
    fail_file = solve_dir + event_id + "-fail.json"
    obs_file = solve_dir + event_id + "-obs.html"
    obs_table_html = make_obs_table(obs)

    fpout = open(obs_file, "w")
    fpout.write(obs_table_html)
    fpout.close()

    if cfe(solve_file) == 1 and force == 0:
       print("We already solved this event!")
    else:
       print("EVENT NOT SOLVED?!", solve_file, fail_file)
    meastype = 2

    # Reference julian date
    start_times = []

    # BEST OBS APPROACH
    print("OBS BEFORE ARE:")
    for st in obs:
       for sfile in obs[st]:
          print(st,sfile, obs[st][sfile].keys())
    use_best_obs = True 
    if use_best_obs is True:
       # here for each station pick 1 obs 
       for station_id in obs:
          file = None
          if len(obs[station_id].keys()) > 1:
             # get "best" file out of them all could be merge_obs too!
             file = get_best_obs(obs[station_id])
          else:
             # only one obs here
             for bfile in obs[station_id]:
                file = bfile
          if file is None:
             print("NO OBS FILE?!", station_id)
             continue
          #print(station_id, obs[station_id][file])
          if "times" in obs[station_id][file]:
             if len(obs[station_id][file]['times']) > 0:
                print("Adding to 'times'.")
                start_times.append(obs[station_id][file]['times'][0])   
          if "times" not in obs[station_id][file] and "start_datetime" in obs[station_id][file]:
          #   print("Adding to 'times'.")
             obs[station_id][file]['times'] = obs[station_id][file]['start_datetime']

    print("OBS AFTER BEST ARE:")
    for st in obs:
       for sfile in obs[st]:
          print(st,sfile, obs[st][sfile].keys())

    if len(start_times) == 0:
       print("THERE ARE NO OBS FOR THIS EVENT!")

       fail_file = solve_dir + event_id + "-fail.json"
       fail = {}
       fail['failed'] = 1 
       fail['no_obs_data'] = 1 
       print("FAIL FILE:", fail_file)
       save_json_file(fail_file, fail)

       return() 
       for station_id in obs:
          if len(obs[station_id].keys()) > 1:
             file = get_best_obs(obs[station_id])
          else:
             for bfile in obs[station_id]:
                file = bfile
          print(station_id, file, obs[station_id][file]['times'])
    else:
       print(solve_dir )
       #for sf in solved_files:
       #   print(sf)
       #event_report(solve_dir, event_final_dir, obs)
       #make_event_json(event_id, solve_dir,[])

    event_start = sorted(start_times)[0]
     
    day = event_start[0:10]
    day = day.replace("-", "_")
    e_dir = event_start.replace("-", "")
    e_dir = e_dir.replace(":", "")
    e_dir = e_dir.replace(" ", "_")
#    solve_dir 

    if "_" in event_start:
       ty,tm,td,th,tmm,ts = event_start.split("_")
       event_start = ty + "-" + tm + "-" + td + " " + th + ":" + tmm + ":" + ts
    event_start_dt = datetime.datetime.strptime(event_start, "%Y-%m-%d %H:%M:%S.%f")
    jd_ref = trajconv.datetime2JD(event_start_dt)


    # Init new trajectory solving
    if time_sync == 1:
       etv = True
    else:
       etv = False
    etv = True 
    # here we should auto adjust this based on if the timing previously failed?
    # or figure out a better way to deal with the timing?

    monte = False 
    #v_init_part = .25
    traj_solve = traj.Trajectory(jd_ref, output_dir=solve_dir, meastype=meastype, save_results=True, monte_carlo=monte, show_plots=False, max_toffset=5, v_init_part=.25, estimate_timing_vel=etv, show_jacchia=True  )
    earliest_time = None

 
    for station_id in obs:             
        for file in obs[station_id]:  # to revert change to if True
            o_times = obs[station_id][file]['times']
            event_start_dt = datetime.datetime.strptime(o_times[0], "%Y-%m-%d %H:%M:%S.%f")
            if earliest_time is None:
                earliest_time = event_start_dt
            else:
                if event_start_dt < earliest_time:
                    earliest_time = event_start_dt

    print("EARLIEST TIME:", earliest_time)
    #input("WAITING")

    # this is where we should use ALL obs or BEST obs or MERGE obs
    for station_id in obs:             
        for file in obs[station_id]:  # to revert change to if True
            #if len(obs[station_id].keys()) > 1:
            # file = get_best_obs(obs[station_id])
            #else:
            #    for bfile in obs[station_id]:
                    #file = bfile
         
        #if True:
        # to revert to best obs uncomment above and change for file line to if  True 
            try:
               lat,lon,alt = obs[station_id][file]['loc']
            except:
               continue
            lat,lon,alt = float(lat), float(lon), float(alt)
            # ADD/CONVERT great circle GC GREAT CIRCLE
            #CAM ID
            (f_datetime, cam_id, f_date_str,fy,fmon,fd, fh, fm, fs) = convert_filename_to_date_cam(file)
            obs[station_id][file]['gc_azs'], obs[station_id][file]['gc_els'] = GC_az_el(obs[station_id][file]['azs'], obs[station_id][file]['els'],  None,None)
            if "fps" in obs[station_id][file]:
               fps = obs[station_id][file]['fps']
            else:
               fps = 25

            if "gc_azs" in obs[station_id][file]:
               # to enable/disable GC (great circle) conversion comment/uncomment lines below
               #print("USING GC AZS:", station_id, obs[station_id][file]['gc_azs'])
               azs = np.radians(obs[station_id][file]['gc_azs'])
               els = np.radians(obs[station_id][file]['gc_els'])
               #print("USING GC AZS RADIANS:", station_id, azs)

               # comment / uncomment to use/not use GCs GCFIT GCfit GC Fit GCFit
               #azs = np.radians(obs[station_id][file]['azs'])
               #els = np.radians(obs[station_id][file]['els'])
            else:
               azs = np.radians(obs[station_id][file]['azs'])
               els = np.radians(obs[station_id][file]['els'])
            o_times = obs[station_id][file]['times']

            print("   STATION:", station_id)
            print("   FILE:", file)
            print("   TIMES:", o_times)
            print("   LAT:", lat)
            print("   LON:", lon)
            print("   ALT:", alt)
            print("   AZ:", azs)
            print("   ELS:", els)
            o_times[0] = o_times[0].replace("-", "_")
            o_times[0] = o_times[0].replace(":", "_")
            o_times[0] = o_times[0].replace(" ", "_")
            event_start_dt = datetime.datetime.strptime(o_times[0], "%Y_%m_%d_%H_%M_%S.%f")
            #this_event_start_dt = datetime.datetime.strptime(o_times[0], "%Y_%m_%d_%H_%M_%S.%f")
            # MY TIME SYNC?
            if earliest_time is None:
               earliest_time = event_start_dt
            else:
               if event_start_dt < earliest_time:
                  earliest_time = event_start_dt
            if len(azs) == 0:
                continue
            times = []

            # time sync bug possible?
            for frame_time in o_times:
                frame_time = frame_time.replace("-", "_")
                frame_time = frame_time.replace(":", "_")
                frame_time = frame_time.replace(" ", "_")
                frame_dt = datetime.datetime.strptime(frame_time, "%Y_%m_%d_%H_%M_%S.%f")

                # toggle time sync bug fix maybe??
                # value should be the time since the start of the event, NOT the start of the obs?
                #time_diff = (frame_dt - event_start_dt).total_seconds()

                time_diff = (frame_dt - earliest_time).total_seconds()
                print("*** EARLIEST TIME:", earliest_time)
                print("*** EVENT START TIME:", event_start_dt)
                print("*** TIME DIFF:", time_diff)
                times.append(time_diff)

            #for i in range(0,len(azs)):
            #    times.append(i/fps)
      
            #print("o", station_id, o_times)
            #print("n", station_id, times)
            # Set points for the first site
            print("   EVENT START DT:", event_start_dt)
            print("   SET WMPL OBS:", event_id, station_id, lat, lon, alt, azs, els, times)  
            print("   TIMES:", station_id, times)
            traj_solve.infillTrajectory(azs, els, times, np.radians(float(lat)), np.radians(float(lon)), alt, station_id=station_id + "-" + cam_id)
            print(   "-----")


    resp = traj_solve.run()
    print("TIMING MINIMIZE SUCCESS?:", traj_solve.timing_minimization_successful)
    if traj_solve.timing_minimization_successful is False:
       print("RUN WITHOUT THE TIME SYNC!")
       traj_solve = traj.Trajectory(jd_ref, output_dir=solve_dir, meastype=meastype, save_results=True, monte_carlo=monte, show_plots=False, max_toffset=5, v_init_part=.5, estimate_timing_vel=False, show_jacchia=True  )
       resp = traj_solve.run()
    print('t_ref_station', traj_solve.t_ref_station)
    #print('time_diffs', traj_solve.time_diffs)
    print('t_diffs_final', traj_solve.time_diffs_final)
    print('timing_res', traj_solve.timing_res)
    print('timing_stddev', traj_solve.timing_stddev)


    print("SOLVE FILE:", solve_file)

    #event_report(solve_dir, event_final_dir, obs)
    #make_event_json(event_id, solve_dir,[])

    #mj['wmpl'] = e_dir
    #save_json_file(meteor_file, mj)
    #print("Saved:", meteor_file) 

    #solved_files = glob.glob(solve_dir + "*")
    solve_files = os.listdir(solve_dir)
    if len(solve_files) == 0 or traj_solve.timing_minimization_successful is False:
       print("FAILED TO SOLVE. No files in solve dir:", solve_dir )
       cmd = "cd ../pythonv2; ./solve.py vida_failed_plots " + event_id
       print(cmd)
       #os.system(cmd)
       fail_file = solve_dir + event_id + "-fail.json"
       fail = {}
       fail['failed'] = 1 
       fail['timing_minimize'] = traj_solve.timing_minimization_successful
       #print("FAIL FILE:", fail_file)
       solve_status = "FAILED"
       save_json_file(fail_file, fail)
       for station_id in obs:
          if len(obs[station_id].keys()) > 1:
             file = get_best_obs(obs[station_id])
          else:
             for bfile in obs[station_id]:
                file = bfile
    else:
       print(solve_dir )
       #for sf in solved_files:
       #   print(sf)
       make_event_json(event_id, solve_dir,[])
       print("MADE EVENT JONS")
       solve_status = "SOLVED"

       #event_report(dynamodb, event_id, solve_dir, event_final_dir, obs)
       print("MADE EVENT REPORT")

       print("DONE SOLVE")

    print("DONE SOLVE", solve_status)
    return(solve_status)

# 1
def center_obs(obs_data):
   lats = []
   lons = []
   for st in obs_data:
      if len(obs_data[st]) > 0:
         for fn in obs_data[st]:
            lat,lon,alt = obs_data[st][fn]['loc']
            print("LAT LON:", lat,lon,alt)
         lats.append(float(lat))
         lons.append(float(lon))
  
   return(np.mean(lats),np.mean(lons))

def menu():
   valid_opt = ['1', '3', '4', '5']
   command = ""
   date = input("Enter the date you want to work on (YYYY_MM_DD): ")

   menu = """
      EVENT SOLVING OPTIONS FOR {:s}
      1) Update DYNA CACHE 
      2) Solve Status 
      3) Define Events 
      4) Solve All Events 
      5) Solve Single Event 
      q) Quit
   """.format(date)

   while command != "q" and command not in valid_opt:
      print(menu)
      command = input("enter command function\n")
      if command == "2":
         print("Solve Status")
         solve_status(date)

   if command == "1":
      print("Update DYNA Cache")
      cmd = "./DynaDB.py udc " + date
      print("DISABLED! RUN FROM AMAZON INSTEAD!")
      #os.system(cmd)
      print(cmd)
   if command == "3":
      print("Define Events")
      cmd = "./solveWMPL.py define_events " + date
      os.system(cmd)
      print(cmd)
   if command == "4":
      print("Solve ALL Events")
      cmd = "./solveWMPL.py sd " + date
      print(cmd)
   if command == "5":
      print("Solve Single Event")
      event_id = input("Enter event id: ") 
      cmd = "./solveWMPL.py sd " + event_id
      print(cmd)

def day_wizard(day):
      # sync the latest dyna cache for this day
   cmd = "./DynaDB.py udc " + day
   os.system(cmd)

   cmd = "./solveWMPL.py de " + day
   os.system(cmd)

   cmd = "./solveWMPL.py sd " + day
   os.system(cmd)

   cmd = "./DynaDB.py udc " + day + " events "
   os.system(cmd)





#event_json_file = "/mnt/f/meteor_archive/AMS1/EVENTS/2021_01_03/20210103_074325.960/20210103_074323-event.json"
#make_event_html(event_json_file)

if __name__ == "__main__":

   print(len(sys.argv))
   if len(sys.argv) == 1:
      print("RUN MENU.")
      menu()
      exit()

   cmd = sys.argv[1]
   meteor_file = sys.argv[2]


   if cmd == "solve":
      mj = load_json_file(meteor_file)
      obs = mj['multi_station_event']['obs']
      WMPL_solve(obs)
   if cmd == "report":
      WMPL_report(meteor_file)
   if cmd == "wiz":
      day_wizard(meteor_file)
   if cmd == "se":
      if len(sys.argv) > 3:
         time_sync = 0
      else:
         time_sync = 1
      solve_event(meteor_file, 1, time_sync)
   if cmd == "sd":
      solve_day(meteor_file)
   if cmd == "mej":
      make_event_json(meteor_file)
   if cmd == "meh":
      # make_event_html(event_json_file )
      make_event_html(meteor_file)
   if cmd == "sm":
      solve_month(meteor_file)
   if cmd == "status":
      solve_status(meteor_file)
   if cmd == "define_events" or cmd == "de":
      define_events(meteor_file)
   if cmd == "delete_events_day" :
      delete_events_day(meteor_file)
   if cmd == "cfp" :
      print(cmd)
      check_fix_plots(sys.argv[2])
   if cmd == "vida_plots" :
      make_vida_plots(meteor_file)
   if cmd == "events_report" or cmd == "er":
      if len(sys.argv) > 2:
         events_report(meteor_file, sys.argv[2])
      else:
         events_report(meteor_file)
   if cmd == "custom_solve" :
      print("YO")
      custom_solve(meteor_file)
