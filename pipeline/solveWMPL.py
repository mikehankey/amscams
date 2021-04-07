#!/usr/bin/python3
from lib.PipeManager import dist_between_two_points
import time
import json
import os
import matplotlib
matplotlib.use('agg')
import glob
from lib.PipeAutoCal import fn_dir
from DynaDB import get_event, get_obs, search_events, update_event, update_event_sol, insert_meteor_event, delete_event
from lib.PipeUtil import load_json_file, save_json_file, cfe, calc_dist, convert_filename_to_date_cam, check_running, get_trim_num
import sys
import numpy as np
import datetime
from datetime import datetime as dt
import math
from lib.PipeSolve import simple_solvev2
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

def check_make_events(obs_time, obs, events):
   #print("EVENTS:", events)
   #print("OBS TIME:", obs_time)
   #print("OBS:", obs)
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
      #print(obs_time, event['start_datetime'])
      times = event['start_datetime']
      for i in range(0, len(event['stations'])):
         e_time = event['start_datetime'][i]
         station = event['stations'][i]
         lat = event['lats'][i]
         lon = event['lons'][i]
         time_diff = (obs_time - e_time).total_seconds()
         #print("THIS TIME DIFF:", time_diff, obs_time, e_time)
         if time_diff < 5:
            station_dist = dist_between_two_points(obs['lat'], obs['lon'], lat, lon)
            if station_dist < 500:
               print("STATION DIST!", station_dist)
               new_event = dict(event)
               new_event['stations'].append(obs['station_id'])
               new_event['files'].append(obs['sd_video_file'])
               new_event['start_datetime'].append(obs_time)
               new_event['lats'].append(obs['lat'])
               new_event['lons'].append(obs['lon'])
               found = 1
               events[ec] = new_event
               return(events)
            else:
               print("REJECT STATION DIST!", station_dist)
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
   day_dir = "/mnt/ams2/EVENTS/" + year + "/" + mon + "/" + day + "/" 
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
         exit()



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
   day_dir = "/mnt/ams2/EVENTS/" + year + "/" + mon + "/" + day + "/" 

   print("Update DYNA Cache")
   cmd = "./DynaDB.py udc " + date
   print(cmd)
   os.system(cmd)

   dyn_cache = day_dir 
   obs_file = dyn_cache + date + "_ALL_OBS.json"
   events_file = dyn_cache + date + "_ALL_EVENTS.json"
   events_index_file = dyn_cache + date + "_ALL_EVENTS_INDEX.json"
   stations_file = dyn_cache + date + "_ALL_STATIONS.json"

   events = []
   all_obs = load_json_file(obs_file)
   stations = load_json_file(stations_file)
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
   events = []

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
          time_str = ttt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
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
   cloud_events_index_file = events_index_file.replace("/mnt/ams2/", "/mnt/archive.allsky.tv/")
   cfn, cdir = fn_dir(cloud_events_index_file)
   if cfe(cdir,1) == 0:
      os.makedirs(cdir)
   cmd = "cp " + events_index_file + " " + cloud_events_index_file
   print(cmd)
   os.system(cmd)
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
   plt.savefig("/mnt/ams2/test.png")
   print("saved /mnt/ams2/test.png")

   events_report(date)


def GC_az_el(azs, els):

   import RMS.GreatCircle
   from RMS.Math import polarToCartesian, cartesianToPolar
   import numpy as np
   from RMS import GreatCircle


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
   day_dir = "/mnt/ams2/EVENTS/" + year + "/" + mon + "/" + day + "/" 
   dyn_cache = day_dir
   #dyn_cache = "/mnt/ams2/DYCACHE/"
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
            event_url = event['solution']['sol_dir'].replace("/mnt/ams2/meteor_archive/", "https://archive.allsky.tv/")
            solved_html += event['event_id'] + " " + event['solve_status'] + " " + event_url + "/index.html\n"
      else:

         if "solution" in event:
            if event["solution"] != 0:
               solved_html += event['event_id'] + " Solved.\n" 

         else:
            not_solved_html += event['event_id'] + " Not solved. " + str(event['stations']) + "\n"
      #solve_event(event['event_id'])
   print(solved_html)
   print(failed_html)
   print(not_solved_html)

def get_best_obs(obs):
   best_dist = 99999
   best_file = None
   for file in obs:
      if best_file is None:
         best_file = file

      mid_x = np.mean(obs[file]['xs'])
      mid_y = np.mean(obs[file]['ys'])
      dist_to_center = calc_dist((mid_x,mid_y), (1920/2, 1080/2))
      if dist_to_center < best_dist:
         best_file = file
         best_dist = dist_to_center


   print("BEST:", best_file)
   return(best_file)

def solve_month(wild):
   files = glob.glob("/mnt/ams2/meteors/" + wild + "*")
   mets = []
   for file in files:
      if cfe(file, 1) == 1:
         mets.append(file)
   for file in mets:
      day = file.split("/")[-1]
      solve_day(day)


def delete_events_day(date):
   year, mon, day = date.split("_")
   day_dir = "/mnt/ams2/EVENTS/" + year + "/" + mon + "/" + day + "/" 
   dyn_cache = day_dir 
   xxx = input("Are you sure you want to delete all events for " + date + " [ENTER] to cont or [CNTL-X] to quit.")
   events_file = dyn_cache + date + "_ALL_EVENTS.json"
   events = load_json_file(events_file)
   for event in events: 
      delete_event(None, event['event_day'], event['event_id'])

def solve_day(day, cores=20):
   date = day
   year, mon, dom = date.split("_")
   day_dir = "/mnt/ams2/EVENTS/" + year + "/" + mon + "/" + dom + "/" 
   dyn_cache = day_dir 
   cmd = "./DynaDB.py udc " + day + " events"
   print(cmd)
   os.system(cmd)
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
   events = load_json_file(events_file)
   events_index = load_json_file(events_index_file)

   print("TOTAL EVENTS:", len(events))
   print("TOTAL INDEX:", len(events_index))
   total_events = len(events)
   ec = 0

   for event in events_index:
      print("DY EV:", event['event_id'])
      if "solve_status" in event:
         print("Solve Status.", event['solve_status'] )
      else:
         print("Not Solved.")
         print(event)
         if cores == 0:
            solve_event(event['event_id'])
         else:
             # this is a multi-core run so launch many threads and wait. 
             running = check_running("solveWMPL.py")
             print("RUNNING:", running)
             if running < cores:
                cmd = "./solveWMPL.py se " + event['event_id'] + " &"
                os.system(cmd)
                print(cmd)
             while running >= cores:
                time.sleep(5)
                running = check_running("solveWMPL.py")
                print(running, " solving processes running.")
      ec += 1

   cmd = "./DynaDB.py udc " + day + " events"
   print(cmd)
   os.system(cmd)

   exit()
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

def get_event_data(date, event_id):
   year, mon, day = date.split("_")
   day_dir = "/mnt/ams2/EVENTS/" + year + "/" + mon + "/" + day + "/" 
   dyn_cache = day_dir 
   events_file = dyn_cache + date + "_ALL_EVENTS.json"
   ev = load_json_file(events_file)
   for event in ev:
      print("SCANNING:", event_id, event['event_id'])
      if event_id == event['event_id']:
         return(event) 

def solve_event(event_id, force=1, time_sync=1):
    year = event_id[0:4]
    mon = event_id[4:6]
    day = event_id[6:8]
    date = year + "_" + mon + "_" + day
    print("EID", event_id)
    print("Y", year)
    print("M", mon)
    print("D", day)
    print("Dt", date)
    local_event_dir = "/mnt/ams2/EVENTS/" + year + "/" + mon + "/" + day + "/" + event_id + "/" 
    cloud_event_dir = "/mnt/archive.allsky.tv/EVENTS/" + year + "/" + mon + "/" + day + "/" + event_id + "/" 
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
    nsinfo = load_json_file("../conf/network_station_info.json")

    dynamodb = boto3.resource('dynamodb')
    #event = get_event(dynamodb, event_id, 0)
    event =  get_event_data(date, event_id)
    ev_status = check_event_status(event)

    status = ev_status['status']
    if status == 1:
       print("This event was already solved successfully.", event_id)
       #return()
    if status == -1:
       print("This event was failed to solve.", event_id)
       return()

    # Check if there are 3rd party network obs to import
    extra_obs_dir = "/mnt/ams2/OTHEROBS/" + event_id + "/"
    if cfe(extra_obs_dir, 1) == 1:
       extra_obs = glob.glob(extra_obs_dir + "*")
    else:
       extra_obs = []

    if event is not None:
       if "solution" in event and force != 1:
          if "solve_status" in event:
             if "FAIL" in event['solve_status']:
                print("The event ran and failed.")
                return()
             else:
                print("The event ran and passed.")
                return()


    obs = {}
    print("EV:", event_id, event)
    if len(event) == 0:
       return()

    bad_obs = []
    for i in range(0, len(event['stations'])):
       t_station = event['stations'][i]
       t_file = event['files'][i]
       print(t_station, t_file)
       dy_obs_data = get_obs(dynamodb, t_station, t_file)
       if dy_obs_data is not None:
          if t_station in nsinfo:
             dy_obs_data['loc'] = nsinfo[t_station]['loc']
          else:
             local_file = "/mnt/ams2/STATIONS/CONF/" + t_station + "_as6.json" 
             cloud_file = "/mnt/archive.allsky.tv/" + t_station + "/CAL/as6.json" 
             if cfe(local_file) == 0:
                os.system("cp "  + cloud_file + " " + local_file)
             print("LOADING:", local_file)
             jsi = load_json_file(local_file)
             dy_obs_data['loc'] = [jsi['site']['device_lat'], jsi['site']['device_lng'], jsi['site']['device_alt']]
             print("LOC:", dy_obs_data['loc'], t_station)
          obs_data = convert_dy_obs(dy_obs_data, obs )

    exit()

    extra_obs_data = []
    if len(extra_obs) > 0:
       for efile in extra_obs:
          edata = parse_extra_obs(efile)
          extra_obs_data.append(edata)


    # get WMPL ID (lowest start time)
    start_times = []
    for station_id in obs:
        if len(obs[station_id].keys()) > 1:
           file = get_best_obs(obs[station_id])
        else:
           for bfile in obs[station_id]:
               file = bfile


        if len(obs[station_id][file]['times']) > 0:
           start_times.append(obs[station_id][file]['times'][0])
        else:
           bad_obs.append(station_id + " missing reduction.")

    if len(start_times) == 0:
       print("PROB: NO DATA?", event_id)
       return()

    event_start = sorted(start_times)[0]
    print("START TIMES:", start_times)
    print("WMPL START:", event_start)

    day = event_start[0:10]
    day = day.replace("-", "_")
    e_dir = event_start.replace("-", "")
    e_dir = e_dir.replace(":", "")
    e_dir = e_dir.replace(" ", "_")
    #solve_dir += day + "/" + e_dir 
    solve_dir = local_event_dir 
    print("SOLVE DIR:", solve_dir)
    if cfe(solve_dir, 1) == 0:
       os.makedirs(solve_dir)

    if cfe(solve_dir, 1) == 1:
       print("SOLVE DIR EXISTS FROM PAST RUN DELETE CONTENTS.")
       files = glob.glob(solve_dir + "/*")
       for file in files:
          print("DEL:", file)
       #os.system("rm " + solve_dir + "/*")
       #os.system("rmdir " + solve_dir )

    print("SOLVE WITH THESE OBS:")
    for key in obs_data:
       print(key)
    sol = simple_solvev2(obs_data)

    obs_data = add_extra_obs(extra_obs_data, obs_data)

    save_json_file(local_event_dir + "/" + event_id + "-simple.json", sol)
    save_json_file(local_event_dir + "/" + event_id + "-obs.json", obs)
    print("SAVED FILES IN:", solve_dir)
    if len(bad_obs) > 0:
       print("BAD OBS!", bad_obs)
       obs_data = {}
       solution = {}
       update_event_sol(None, event_id, solution, obs_data, str(bad_obs))
       return()
    else: 
       WMPL_solve(event_id, obs_data, time_sync)

    solved_files = glob.glob(solve_dir + "/*")
    if len(solved_files) > 10:
       simple_status = 1
       wmpl_status = 1
    else:
       simple_status = 1
       wmpl_status = 0

    resp = make_event_json(event_id, solve_dir)
    
    if resp == 0:
       print("FAILED TO SOLVE!")
       solution = {}
       #solution['obs'] = obs_data
       if time_sync == 0:
          update_event_sol(None, event_id, solution, obs_data, "WMPL FAILED. TIME SYNC FAILED.")
       else:
          update_event_sol(None, event_id, solution, obs_data, "WMPL FAILED.")

       return(0)
    solution,as_obs = resp

    print("EVID:", event_id)
    print("UPDATE EVENT SOL:")
    if time_sync == 1:
       update_event_sol(None, event_id, solution, as_obs, "SUCCESS")
    if time_sync == 0:
       update_event_sol(None, event_id, solution, as_obs, "TIME SYNC FAIL")

    event_file = solve_dir + "/" + event_id + "-event.json"

    make_event_html(event_file)

    # remove the pngs and then copy the results to the cloud dir
    cloud_dir = solve_dir.replace("/mnt/ams2/", "/mnt/archive.allsky.tv/")
    if cfe(cloud_dir,1) == 0:
       os.makedirs(cloud_dir)
    cmd = "rm " + solve_dir + "/*.png"
    print(cmd)
    os.system(cmd)
    cmd = "rsync -auv " + solve_dir + "* " + cloud_dir 
    print(cmd)
    os.system(cmd)



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
   #print(event)
   local_event_exists = 0
   cloud_event_exists = 0
   legacy_event_dir = None
   cloud_event_dir = "/mnt/archive.allsky.tv/EVENTS/" + year + "/" + month + "/" + day + "/" + event['event_id'] + "/" 
   local_event_dir = "/mnt/ams2/EVENTS/" + year + "/" + month + "/" + day + "/" + event['event_id'] + "/" 
   if "solution" in event:
      if "solution" in event:
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
   print("LOADING:", event_json_file)
   event_data = load_json_file(event_json_file)
 

   event_id = event_data['event_id']

   year = event_id[0:4]
   mon = event_id[4:6]
   day = event_id[6:8]
   date = year + "_" + mon + "_" + day
   #HHHH
   solve_dir = local_event_dir 
   print("SOLVE DIR IS #1:", solve_dir)
   xxx = solve_dir.split("/")[-1]


   event = get_event(dynamodb, event_id, 0)

   event_file = solve_dir + event_id + "-event.json"
   event_index_file = solve_dir + "index.html" 
   kml_file = solve_dir + event_id + "-map.kml"
   print("KML FILE:", kml_file)

   sd = solve_dir.split("/")[-1]
   if "." in sd:
      temp = sd.split(".")
      sdd = temp[0]
   else:
      sdd = sd 

   report_file = solve_dir + "/" + sdd + "_report.txt"
   if "/mnt/ams2" in kml_file:
      kml_file = kml_file.replace("/mnt/ams2", "")
   if "solution" not in event:
      print("NO SOLUTION IN EVENT!", event)
   else:
      if event["solution"] == 0:
         print("solve failed.")
         return(0)
   print("EVENT:", event)
   print("EVENT SOL:", event['solution'])

   orb_link = event['solution']['orb']['link']

   print("EVENT ID IS:", event_id)
   print("SOL DIR IS:", solve_dir)
   #obs_data = load_json_file(obs_file)
   obs_data = event['obs']
   # make the obs part
   sum_html = make_sum_html(event_id, event, solve_dir, obs_data)

   obs_html = make_obs_html(event_id, event, solve_dir, obs_data)

   center_lat, center_lon = center_obs(obs_data)

   kml_file = kml_file.replace("/meteor_archive/", "https://archive.allsky.tv/")
   
   map_html = "<div style='clear: both'> &nbsp; </div>"
   map_html += "<div>"
   map_html += "<h2>Trajectory</h2>"
   map_html += "<iframe src=\"https://archive.allsky.tv/APPS/dist/maps/index.html?mf=" + kml_file + "&lat=" + str(center_lat) + "&lon=" + str(center_lon) + "\" width=800 height=440></iframe><br><a href=" + kml_file + ">KML</a><br>"

   map_html += "</div>"

   if orb_link != "" and orb_link != "#":
      orb_html = "<h2>Orbit</h2>"
      orb_html += "<iframe border=0 src=\"" + orb_link + "\" width=800 height=440></iframe><br><a href=" + orb_link + ">Orbit</a><br>"
   else:
      orb_html = ""



   plot_html = "<h2>Plots</h2>"
   plot_html += "<div>\n"
   sol_jpgs = glob.glob(solve_dir + "/*.jpg")
   for img in sorted(sol_jpgs):
      print("PLOT IMAGE:", img)
      img = img.replace("/mnt/ams2/", "https://archive.allsky.tv/")
      if "ground" not in img and "orbit" not in img:
         plot_html += "<div style='float:left; padding: 3px'><img width=600 height=480 src=" + img + "></div>\n"

   plot_html += "</div>"

   # final report
   if cfe(report_file) == 1:
      rpt = open(report_file) 
      rpt_out = "<div style='clear:both'> &nbsp; </div><br>"
      rpt_out += "<h2>WMPL Report</h2><div><pre>"
      for line in rpt:
         print("LINE:", line)
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
   XXX = "xxx"
   tj = event['solution']['traj']
   ob = event['solution']['orb']
   if "duration" in event:
      duration = float(event['duration'])
   else:
      duration = float(0)
   shower_code = event['solution']['shower']['shower_code']
   html = "<h2>Event Summary</h2>"
   html += "<table border=0 padding=3><tr><td>"
   html += "<table border=0 padding=5>"
   html += "<tr><td>Event ID</td>"
   html += "<td>" + str(event_id) + "</td></tr>"
   html += "<tr><td>Start Time</td>"
   html += "<td>" + str(event['start_datetime'][0]) + "</td></tr>"
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
         if len(event['obs'][station_id][file]['azs']) >= 2:
            print(event['obs'][station_id])
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
      obs[station][obs_file]['gc_azs'], obs[station][obs_file]['gc_els'] = GC_az_el(obs[station][obs_file]['azs'], obs[station][obs_file]['els'])
   return(obs)

def convert_dy_obs(dy_obs_data, obs):
   #print("DYO:", dy_obs_data)
   station = dy_obs_data['station_id']
   fn = dy_obs_data['sd_video_file']
   if station not in obs:
      obs[station] = {}
   if fn not in obs[station]:
      obs[station][fn] = {}

   calib = dy_obs_data['calib'] 
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
   obs[station][fn]['revision'] = float(dy_obs_data['revision'])

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
      


   obs[station][fn]['gc_azs'], obs[station][fn]['gc_els'] = GC_az_el(obs[station][fn]['azs'], obs[station][fn]['els'])

   #print("OBS:", obs)
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

def make_event_json(event_id, solve_dir):

   import pickle
   jpgs = glob.glob(solve_dir + "/*.jpg")
   jsons = glob.glob(solve_dir + "/*.json")
   pks = glob.glob(solve_dir + "/*.pickle")

   print("looking in solve dir", solve_dir)

   for js in jsons:
      if "obs.json" in js:
         obs_file = js
         kml_file = js.replace("-obs.json", "-map.kml")
      if "simple.json" in js:
         sol_file = js


   print("SOL FILE:", sol_file)
   print("KML FILE:", kml_file)

   simple_solve = load_json_file(sol_file)


   as_obs = load_json_file(obs_file)

   event_file = sol_file.replace("-simple.json", "-event.json")

   print("OBS:", as_obs) 
   print("SIMPLE:", simple_solve) 

   points = []
   lines = []
   

   station_data = {}
   for station_id in as_obs:
      for file in as_obs[station_id]:
         if station_id not in station_data:
            obs_data = as_obs[station_id][file]
            print(station_id)
            lat, lon, alt = obs_data['loc']
            station_data[station_id] = obs_data['loc']
            points.append((lon,lat,alt,station_id))

   durs = []
   for ss in simple_solve:
      print(ss)
      sol_key, start_lat, start_lon, start_ele, end_lat, end_lon, end_ele, dist, dur, vel = ss 
      durs.append(dur)
      (skey1,skey2) = sol_key.split("_")
      station1,cam1 = skey1.split("-")
      station2,cam2 = skey2.split("-")
      ol_start_lat = station_data[station2][0]
      ol_start_lon = station_data[station2][1]
      ol_start_alt = station_data[station2][2]
      line_desc = "OL:" + sol_key
      lines.append((ol_start_lon,ol_start_lat,ol_start_alt,start_lon,start_lat,start_ele,line_desc))
      lines.append((ol_start_lon,ol_start_lat,ol_start_alt,end_lon,end_lat,end_ele,line_desc))

      line_desc = "SS:" + sol_key
      
      lines.append((start_lon,start_lat,start_ele,end_lon,end_lat,end_ele,line_desc))

   if len(durs) > 0:
      duration = float(max(durs) / 25)
   else:
      duration = float(0)

   solution = {}
   solution['event_id'] = event_id
   solution['duration'] = float(duration)
   solution['sol_dir'] = solve_dir 
#   solution['obs'] = as_obs
   solution['simple_solve'] = simple_solve
   solution['traj'] = {}
   solution['orb'] = {}
   solution['rad'] = {}
   solution['plot'] = {}
   solution['kml'] = {}
   solution['shower'] = {}

   if len(pks) == 0:
      print("WMPL FAILED. NO EVENT JSON MADE.")
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





   make_kml(kml_file, points, lines)
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



   solution['kml']['points'] = points
   solution['kml']['lines'] = lines

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
   solution['obs'] = as_obs
   save_json_file(event_file, solution)
   print("SAVED EVENT FILE:", event_file)
   return(solution,as_obs)

def make_kml(kml_file, points, lines):
   import simplekml
   kml = simplekml.Kml()
   used = {}

   pc = 0
   colors = ['ff0b86b8', 'ffed9564', 'ff0000ff', 'ff00ffff', 'ffff0000', 'ff00ff00', 'ff800080', 'ff0080ff', 'ff336699', 'ffff00ff' ]
   # add station points 

   station_folders = {}

   for point in points:
      lon,lat,alt,station = point
      if station not in used and "3DP:" not in station:
         station_folders[station] = kml.newfolder(name=station)
         color = colors[pc]
         pnt = station_folders[station].newpoint(name=station, coords=[(lon,lat,alt)])
         pnt.description = station
         pnt.style.labelstyle.color=color
#simplekml.Color.darkgoldenrod
         pnt.style.labelstyle.scale = 1
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
   for point in points:
      lon,lat,alt,station = point
      if "3DP:" in station:
         tstation, trash = station.split("_")
         tstation = tstation.replace("3DP:", "")
         print("S/T STATION:", station, tstation)
         color = used[tstation]
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

   line_folder = kml.newfolder(name="Trajectory")
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




def event_report(solve_dir, event_final_dir, obs):
    print("EVREPORT:")
    print("SOLVE DIR:", solve_dir)
    print("FINAL DIR:", event_final_dir)
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
    report = ""

    for station_id in obs:
        if len(obs[station_id].keys()) > 1:
            file = get_best_obs(obs[station_id])
        else:
            for bfile in obs[station_id]:
                file = bfile
        prev_file = file.replace(".mp4", "-prev.jpg")
        year = file[0:4]
        day = file[0:10]
        if station_id in remote_urls:
           link = remote_urls[station_id] + "/meteors/" + station_id + "/" + day + "/" + file + "/"
        else:
           link = ""
        html += "<h1>" + station_id + " " + file + "</h1>"
        #html += "<a href=" + link + ">"
        html += "<img src=https://archive.allsky.tv/" + station_id + "/METEORS/" + year + "/" + day + "/" + station_id + "_" + prev_file + "></a>"
        html += "<hr>"


    jpgs = []
    for sf in solved_files:
       if "report" in sf:
          fp = open(sf, "r")
          for line in fp:
             report += line
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

    print("MOVE THE WMPL FILES TO THE FINAL EVENT DIR!")
    final_jpgs = []
    for sf in solved_files:
       fn, xxx = fn_dir(sf)
       fn = fn.replace(".png", ".jpg")
       new_file = event_final_dir + fn 
       cmd = "mv " + sf + " " + event_final_dir
       print(cmd)
       os.system(cmd)
       if "jpg" in fn:
          final_jpgs.append(new_file)
       print(cmd)
      
    for jpg in final_jpgs:
       jpg = jpg.replace("/mnt/ams2/meteor_archive/", "")
       html += "<img src=" + jpg + ">"
       print(html)
    html += "<p>"
    html += "<pre>" + report + "</pre>"
    fp = open(solve_dir + "/index.html", "w")
    fp.write(html)
    print("SAVED INDEX:", event_final_dir + "/index.html")

    # sync data to cloud
    cloud_final_dir = event_final_dir.replace("/mnt/ams2/", "/mnt/archive.allsky.tv/")
    cmd = "rsync -auv " + event_final_dir + " " + cloud_final_dir
    print(cmd)



def WMPL_solve(event_id, obs,time_sync=1):
    json_conf = load_json_file("../conf/as6.json")
    ams_id  = json_conf['site']['ams_id']

    year = event_id[0:4]
    mon = event_id[4:6]
    day = event_id[6:8]
    date = year + "_" + mon + "_" + day

    event_final_dir = "/mnt/ams2/EVENTS/" + year + "/" + mon + "/" + day + "/" + event_id + "/"
    solve_dir = "/mnt/ams2/EVENTS/" + year + "/" + mon + "/" + day + "/" + event_id + "/"
    # Inputs are RA/Dec
    meastype = 2

    # Reference julian date
    start_times = []
    for station_id in obs:
        if len(obs[station_id].keys()) > 1:
           file = get_best_obs(obs[station_id])
        else:
           for bfile in obs[station_id]:
               file = bfile

        if len(obs[station_id][file]['times']) > 0:
           start_times.append(obs[station_id][file]['times'][0])   

    event_start = sorted(start_times)[0]
     
    day = event_start[0:10]
    day = day.replace("-", "_")
    e_dir = event_start.replace("-", "")
    e_dir = e_dir.replace(":", "")
    e_dir = e_dir.replace(" ", "_")
#    solve_dir 


    event_start_dt = datetime.datetime.strptime(event_start, "%Y-%m-%d %H:%M:%S.%f")
    jd_ref = trajconv.datetime2JD(event_start_dt)
    #print(event_start_dt, jd_ref)


    # Init new trajectory solving
    if time_sync == 1:
       etv = True
    else:
       etv = False
    traj_solve = traj.Trajectory(jd_ref, output_dir=solve_dir, meastype=meastype, save_results=True, monte_carlo=False, show_plots=False, max_toffset=3,v_init_part=.5, estimate_timing_vel=etv, show_jacchia=True  )
   
    for station_id in obs:
        if len(obs[station_id].keys()) > 1:
            file = get_best_obs(obs[station_id])
        else:
            for bfile in obs[station_id]:
                file = bfile
         
        if True:
            lat,lon,alt = obs[station_id][file]['loc']
            lat,lon,alt = float(lat), float(lon), float(alt)
            if "azs_gc" in obs[station_id][file]:
               azs = np.radians(obs[station_id][file]['azs_gc'])
               els = np.radians(obs[station_id][file]['els_gc'])
            else:
               azs = np.radians(obs[station_id][file]['azs'])
               els = np.radians(obs[station_id][file]['els'])
            times = obs[station_id][file]['times']

            print("STATION:", station_id)
            print("FILE:", file)
            print("TIMES:", times)
            print("LAT:", lat)
            print("LON:", lon)
            print("ALT:", alt)
            print("AZ:", azs)
            print("ELS:", els)
            if len(azs) == 0:
                continue
            times = []
            for i in range(0,len(azs)):
                times.append(i/25)
        
            # Set input points for the first site
            traj_solve.infillTrajectory(azs, els, times, np.radians(float(lat)), np.radians(float(lon)), alt, station_id=station_id)
            print("-----")


    traj_solve.run()



    #mj['wmpl'] = e_dir
    #save_json_file(meteor_file, mj)
    #print("Saved:", meteor_file) 

    solved_files = glob.glob(solve_dir + "*")
    if len(solved_files) == 0:
       print("FAILED TO SOLVE.")
       for station_id in obs:
          if len(obs[station_id].keys()) > 1:
             file = get_best_obs(obs[station_id])
          else:
             for bfile in obs[station_id]:
                file = bfile
          print(station_id, file, obs[station_id][file]['times'])
    else:
       print(solve_dir )
       for sf in solved_files:
          print(sf)
       event_report(solve_dir, event_final_dir, obs)


def center_obs(obs_data):
   lats = []
   lons = []
   for st in obs_data:
      for fn in obs_data[st]:
         lat,lon,alt = obs_data[st][fn]['loc']
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
      os.system(cmd)
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




print(len(sys.argv))
if len(sys.argv) == 1:
   print("RUN MENU.")
   menu()
   exit()

cmd = sys.argv[1]
meteor_file = sys.argv[2]

#event_json_file = "/mnt/ams2/meteor_archive/AMS1/EVENTS/2021_01_03/20210103_074325.960/20210103_074323-event.json"
#make_event_html(event_json_file)
#exit()


if cmd == "solve":
   mj = load_json_file(meteor_file)
   obs = mj['multi_station_event']['obs']
   WMPL_solve(obs)
if cmd == "report":
   WMPL_report(meteor_file)
if cmd == "wiz":
   day_wizard(meteor_file)
if cmd == "se":
   solve_event(meteor_file)
if cmd == "sd":
   solve_day(meteor_file)
if cmd == "mej":
   make_event_json(meteor_file)
if cmd == "meh":
   make_event_html(meteor_file)
if cmd == "sm":
   solve_month(meteor_file)
if cmd == "status":
   solve_status(meteor_file)
if cmd == "define_events" or cmd == "de":
   define_events(meteor_file)
if cmd == "delete_events_day" :
   delete_events_day(meteor_file)
if cmd == "events_report" or cmd == "er":
   if len(sys.argv) > 2:
      events_report(meteor_file, sys.argv[2])
   else:
      events_report(meteor_file)
