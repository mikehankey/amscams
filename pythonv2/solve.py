#!/usr/bin/python3
from lib.FileIO import load_json_file, save_json_file, cfe
import matplotlib
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import simplekml
import sys
import json
from lib.REDUCE_VARS import *
from lib.Video_Tools_cv_pos import *
from lib.Video_Tools_cv import *
from PIL import ImageFont, ImageDraw, Image, ImageChops
from lib.VIDEO_VARS import *
from lib.UtilLib import calc_dist,find_angle, best_fit_slope_and_intercept, calc_radiant
from lib.MeteorTests import test_objects
import datetime
import time
import glob
import os
import math
import cv2
import math
import numpy as np
import scipy.optimize
import ephem
from lib.flexCal import flex_get_cat_stars, reduce_fov_pos
import wmpl.Utils.TrajConversions as trajconv

from lib.VideoLib import get_masks, find_hd_file_new, load_video_frames, sync_hd_frames, make_movie_from_frames, add_radiant

from lib.UtilLib import check_running, angularSeparation
from lib.CalibLib import radec_to_azel, clean_star_bg, get_catalog_stars, find_close_stars, XYtoRADec, HMS2deg, AzEltoRADec, get_active_cal_file

from lib.ImageLib import mask_frame , stack_frames, preload_image_acc, thumb
from lib.ReducerLib import setup_metframes, detect_meteor , make_crop_images, perfect, detect_bp, best_fit_slope_and_intercept, id_object, metframes_to_mfd

from lib.MeteorTests import meteor_test_cm_gaps

import pymap3d as pm

from sympy import Point3D, Line3D, Segment3D, Plane


json_conf = load_json_file("../conf/as6.json")


def build_events(year):
   json_conf = load_json_file("/home/ams/amscams/conf/as6.json")
   station = json_conf['site']['ams_id']
   print("<h1>Multi-station detections for ", station, "</h1>")
   detect_file = "/mnt/ams2/meteor_archive/" + station + "/DETECTS/ms_detects.json"
   detect_data = load_json_file(detect_file)
   main_event_file = "/mnt/ams2/meteor_archive/" + station + "/EVENTS/" + year + "/" + year + "-events.json"
   main_event_dir = "/mnt/ams2/meteor_archive/" + station + "/EVENTS/" + year + "/" 
   if cfe(main_event_file) == 1:
      events = load_json_file(main_event_file)
   else:
      events = {}
   for key in sorted(detect_data.keys(), reverse=True):
      for file in detect_data[key]:
         stations = detect_data[key][file]['stations']
         files = detect_data[key][file]['obs']
         arc_files = detect_data[key][file]['arc_files']
         event_id = detect_data[key][file]['event_id']
         event_start = detect_data[key][file]['event_start']
         clip_starts = detect_data[key][file]['clip_starts']
         count = detect_data[key][file]['count']
         if event_id not in events:
            events[event_id] = {}

         events[event_id]['event_id'] = event_id
         events[event_id]['event_start'] = event_start
         events[event_id]['count'] = count
         events[event_id]['stations'] = stations
         events[event_id]['files'] = files
         events[event_id]['clip_starts'] = clip_starts
         events[event_id]['arc_files'] = arc_files

   updated_events = {}
   station_id = json_conf['site']['ams_id']
   for event_id in events:
      event = events[event_id]
      print("<h1>" + str(event_id) + "</h1>")
      print("Station Count: " + str(events[event_id]['count']) + "<BR>")
      print("Event Start Time: " + str(len(events[event_id]['event_start'])) + "<BR>")
      print("Stations: " + str(set(events[event_id]['stations'])) + "<BR>")
      print("Files: " + str(len(events[event_id]['files'])) + "<BR>")
      print("Arc Files: " + str(len(events[event_id]['arc_files'])) + "<BR>")

      event_year = event_id[0:4]
      event_day = event_id[0:10]

      event_dir = "/mnt/ams2/meteor_archive/" + station_id + "/EVENTS/" + event_year + "/" + event_day + "/" + event_id + "/"
      solutions = []
      print(event_dir)
      if cfe(event_dir,1) == 1:
         print("EVENT DIR EXISTS! " + event_dir + "/*.json")
         # a solving attmpt was made
         sol = glob.glob(event_dir + "/*.json")
         if len(sol) <= 1:
            status = "failed"
         else:
            for sfile in sol:
               sf = sfile.split("/")[-1]
               print(sfile)
               if "_report" in sfile:
                  rd = load_json_file(sfile)
                  if "rbeg_lat" in rd:
                     if rd['rbeg_lat'] < 0 or rd['rbeg_lon'] < 0:
                        solutions.append(('vida_ip', sf, 0))
                     else:
                        solutions.append(('vida_ip', sf, 1))
               if "-simple" in sfile:
                  sf = sfile.split("/")[-1]
                  status = 1
                  sd = load_json_file(sfile)
                  for key in sd['simple_solve']:
                
                     if "status" in sd['simple_solve'][key]:
                        if sd['simple_solve'][key]['status'] == "FAILED TO SOLVE":
                           status = 0 
                
                  solutions.append(('hankey_ip', sf, status))
            if len(solutions) > 0:
               event['solutions'] = solutions
         print("SOL:", solutions)
      updated_events[event_id] = event

      
   main_event_dir = "/mnt/ams2/meteor_archive/" + station + "/EVENTS/" + str(event_year) + "/"

   save_json_file(main_event_dir + str(event_year) + "-events.json", updated_events)
   print("Saved:" + main_event_dir + str(event_year) + "-events.json")




def look_for_file(station_id, main_meteor):
   obs = []
   my_meteor_datetime, my_cam1, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(main_meteor)
   station_dir = "/mnt/wasabi/" + station_id + "/METEOR/" + hd_y + "/" + hd_m + "/" + hd_d + "/" 
   print(station_id, my_meteor_datetime, station_dir)
   station_files = glob.glob(station_dir + "*.json")
   print("GLOB: " + station_dir + "*.json")
   for sf in station_files:
      sf_meteor_datetime, sf_cam1, sf_date, sf_y, sf_m, sf_d, sf_h, sf_M, sf_s = convert_filename_to_date_cam(sf)
      tdiff = abs((my_meteor_datetime-sf_meteor_datetime).total_seconds())
      if tdiff < 60 :
         print(sf, tdiff)
         obs.append(sf)
   return(obs)


def find_multi_station_matches(main_meteor):
   observations = {}
   json_conf = load_json_file("../conf/as6.json")
   this_station_id = json_conf['site']['ams_id']
   st_id = main_meteor.split("/")[4]
   if st_id == this_station_id:
      network_sites = json_conf['site']['network_sites'].split(",")
   else:
      json_conf = load_json_file("/mnt/ams2/meteor_archive/" + st_id + "/CAL/as6.json")
      print("/mnt/ams2/meteor_archive/" + st_id + "/CAL/as6.json")
      network_sites = json_conf['site']['network_sites'].split(",")
      print("JSON CONF!" + "/mnt/ams2/meteor_archive/" + st_id + "/CAL/as6.json")
   for station in network_sites:
      print("SISTER STATION:", station)
      obs = look_for_file(station, main_meteor)
      observations[station] = obs
      print("STATION:", station, obs)


   args = []
   for station in observations:
      for obs in observations[station]:
         args.append(obs)
   args.append(main_meteor)
   obs_info, event_id = make_event_obs_file(args)
   edir = "/mnt/ams2/events/" + event_id + "/"
   if cfe(edir, 1) == 0:
      os.system("mkdir " + edir)
   save_json_file(edir + event_id + ".json", obs_info)
   print(edir + event_id + ".json")
   cmd = "cd /home/ams/dvida/WesternMeteorPyLib/wmpl/Trajectory; python3 AS6Trajectory.py " + edir + event_id + ".json"
   print(cmd)
   os.system(cmd)

def make_event_obs_file(files):
   print("MAKE EVENT OBS FILES:", len(files))
   obs_info = {}
   # frame time from event start
   times = []
   # azs for each frame
   # els for each frame

   all_dates = []
   #for c in range(0,len(files)):
   for c in range(0,len(files)):
      print("LOADING OBS FILE:", files[c])
      obs_data = load_json_file(files[c])
      if obs_data is False:
         print("Failed to load.", files[c])
         exit()
      json_file = files[c]

      #obs_data['event_id'] = event_id
      #save_json_file(files[c], obs_data)
      thetas= []
      phis = []
      times = []
      fc = 0
      sf = int(obs_data['frames'][0]['fn'])
      for frame_data in obs_data['frames']:
         #meteor_frame_time_str,fn,hd_x,hd_y,w,h,max_px,ra,dec,az,el = frame_data
         meteor_frame_time_str = frame_data['dt']
         fn = frame_data['fn']
         hd_x = frame_data['x']
         hd_y = frame_data['y']
         w = 5
         h = 5
         max_px = 100
         ra = round(frame_data['ra'],4)
         dec = round(frame_data['dec'],4)
         az = round(frame_data['az'],4)
         el = round(frame_data['el'],4)
         print(ra,dec,az,el)
         tfc = int(fn) - sf
         #ft = datetime.datetime.strptime(meteor_frame_time_str, "%Y-%m-%d %H:%M:%S.%f")
         ref_time = tfc / 25
         times.append(float(ref_time))
         thetas.append(round(float(az),4))
         phis.append(round(float(el),4))
         fc = fc + 1
      obs_info[files[c]] = {}
      #obs_info[files[c]]['reduction'] = obs_data
      if 'lat' in obs_data['calib']['device']:
         obs_info[files[c]]['lat'] = obs_data['calib']['device']['lat']
         obs_info[files[c]]['lon'] = obs_data['calib']['device']['lng']
         obs_info[files[c]]['alt'] = obs_data['calib']['device']['alt']
      obs_info[files[c]]['times'] = times
      obs_info[files[c]]['phis'] = phis
      obs_info[files[c]]['thetas'] = thetas
      obs_info[files[c]]['station_id'] = obs_data['info']['station'].upper() + "-" + obs_data['info']['device']
      obs_info[files[c]]['sd_video_file'] = json_file
      obs_info[files[c]]['hd_video_file'] = json_file 
      event_start = obs_data['frames'][0]['dt']
      all_dates.append(datetime.datetime.strptime(event_start, "%Y-%m-%d %H:%M:%S.%f"))
      #obs_info[files[c]]['all_red'] = obs_data

   event_start = avg_datetimes(all_dates, 1)
   event_start_dt = datetime.datetime.strptime(event_start, "%Y-%m-%d %H:%M:%S.%f")
   event_id = event_start.replace(" ", "")
   event_id = event_id.replace(":", "")
   event_id = event_id.replace("-", "")
   event_id = event_id.replace(".", "")
   jd_ref = trajconv.datetime2JD(event_start_dt)
   print("JD REF:", event_start_dt, jd_ref)
   event_utc = event_start
   obs_info['event_id'] = event_id 
   obs_info['jd_ref'] = jd_ref
   obs_info['event_utc'] = event_utc
   return(obs_info,event_id)

def build_match_index_day(date):
   all_index = {}
   events = {}
   captures = []

   combined_index_file = "/mnt/ams2/events/combined_index_" + date + ".json"
   run_file = "/mnt/ams2/events/" + date + ".sh"
   os.system("rm " + run_file)
   if cfe(combined_index_file) == 0:
      print("Building Index.")
      this_station = json_conf['site']['ams_id']
      arc_folder = "/mnt/ams2/meteor_archive/" 
      all_index[this_station] = load_station_index(this_station, date, arc_folder)
      print(all_index)
      network_sites = json_conf['site']['network_sites'].split(",") 
      for station in network_sites:
         arc_folder = "/mnt/wasabi/" 
         all_index[station] = load_station_index(station, date, arc_folder)

      save_json_file(combined_index_file, all_index)
   else:
      print("Loading index...")
      all_index = load_json_file(combined_index_file)

   print(all_index)
   # Find multi-station-events
   for station in all_index:
      print(station, len(all_index[station]))
      for data in all_index[station]:
         file = date + "_" + data['p'] + ".json"
         clip_start_time = file_to_date(file)
         print(station, file, clip_start_time)
         captures.append([station, file, clip_start_time])

   for station, file, clip_start_time in captures:
      event_id, events = find_event(station, file, clip_start_time, events, captures)

   for event_id in events:
      total_stations = len(events[event_id]['stations'].keys())
      if total_stations >= 2:
         datetimeList = []
         event_args = [] 
         for station in events[event_id]['stations']:
            #events[event_id]['stations'][station]['files'][0]
            arc_dir = file_to_arc_dir(events[event_id]['stations'][station]['files'][0], station)
            event_args.append(arc_dir + events[event_id]['stations'][station]['files'][0])
            datetimeList.append(events[event_id]['stations'][station]['clip_times'][0])
         time_id = avg_datetimes(datetimeList)
         print(event_id, event_args, time_id)
         run_event(event_id, time_id, event_args)

def avg_datetimes(datetimeList, return_type = 0):
   if return_type == 0:
      avgTime=datetime.datetime.strftime(datetime.datetime.fromtimestamp(sum(map(datetime.datetime.timestamp,datetimeList))/len(datetimeList)),"%Y%m%d%H%M%S")
   elif return_type == 1:
      avgTime=datetime.datetime.strftime(datetime.datetime.fromtimestamp(sum(map(datetime.datetime.timestamp,datetimeList))/len(datetimeList)),"%Y-%m-%d %H:%M:%S.%f")
   return(avgTime)

def dist_from_center(arc_file):
   data = load_json_file(arc_file)
   print(arc_file)
   xs= []
   ys= []
   for frame in data['frames']:
      xs.append(frame['x'])
      ys.append(frame['y'])
   dist_x = np.mean(xs) 
   dist_y = np.mean(ys) 
   dist = calc_dist((960,540),(dist_x,dist_y))
   return(dist)

def find_vector_point(lat,lon,alt,az,el,factor=1000000):

   wgs84 = pm.Ellipsoid('wgs84');
   sveX, sveY, sveZ = pm.aer2ecef(az,el,1000000, lat, lon, alt, wgs84)
   svlat, svlon, svalt = pm.ecef2geodetic(float(sveX), float(sveY), float(sveZ), wgs84)
   return(sveX,sveY,sveZ,svlat,svlon,svalt)


def simple_solve(event_file):

   event_obs_data = load_json_file(event_file)
   print(event_file)
   event_utc = event_obs_data['event_utc']
   arg_date, arg_time = event_utc.split(" ")
   if event_obs_data == 0:
      print("Failed to load the event obs file!", event_file) 

   wgs84 = pm.Ellipsoid('wgs84');
   vfact = 1000000

   planes = {}
   meteor = {}
   meteor['observations'] = {}
   meteor['simple_solutions'] = {}


   for key in event_obs_data:
      if "METEOR" in key:
         # load station data
         obs_data = load_json_file(key)
         station_id = obs_data['info']['station']
         meteor['observations'][station_id] = {}
         meteor['observations'][station_id]['station'] = station_id.upper()
         meteor['observations'][station_id]['lat'] = event_obs_data[key]['lat'] 
         meteor['observations'][station_id]['lng'] = event_obs_data[key]['lon'] 
         meteor['observations'][station_id]['alt'] = event_obs_data[key]['alt'] 

         # convert obs location to ecef
         x, y, z = pm.geodetic2ecef(float(event_obs_data[key]['lat']), float(event_obs_data[key]['lon']), float(event_obs_data[key]['alt']), wgs84)
         meteor['observations'][station_id]['x'] = x
         meteor['observations'][station_id]['y'] = y
         meteor['observations'][station_id]['z'] = z   

         # populate obs with start and end az/el
         frames = obs_data['frames']
         meteor['observations'][station_id]['start_az'] = frames[0]['az']
         meteor['observations'][station_id]['start_el'] = frames[0]['el']
         meteor['observations'][station_id]['end_az'] = frames[-1]['az']
         meteor['observations'][station_id]['end_el'] = frames[-1]['el']
         meteor['observations'][station_id]['event_start_time'] = frames[0]['dt']
         meteor['observations'][station_id]['duration'] = float(len(frames)/25)

         # convert station lat,lon,alt,az,el to start and end vectors
         sveX, sveY, sveZ, svlat, svlon,svalt = find_vector_point(float(event_obs_data[key]['lat']), float(event_obs_data[key]['lon']), float(event_obs_data[key]['alt']), frames[0]['az'], frames[0]['el'], 1000000)
         eveX, eveY, eveZ, evlat, evlon,evalt = find_vector_point(float(event_obs_data[key]['lat']), float(event_obs_data[key]['lon']), float(event_obs_data[key]['alt']), frames[-1]['az'], frames[-1]['el'], 1000000)
         meteor['observations'][station_id]['sveX'] = sveX
         meteor['observations'][station_id]['sveY'] = sveY
         meteor['observations'][station_id]['sveZ'] = sveZ
         meteor['observations'][station_id]['svlat'] = svlat
         meteor['observations'][station_id]['svlon'] = svlon
         meteor['observations'][station_id]['svalt'] = svalt

         meteor['observations'][station_id]['eveX'] = eveX
         meteor['observations'][station_id]['eveY'] = eveY
         meteor['observations'][station_id]['eveZ'] = eveZ
         meteor['observations'][station_id]['evlat'] = evlat
         meteor['observations'][station_id]['evlon'] = evlon
         meteor['observations'][station_id]['evalt'] = evalt
 
         planes[station_id] = Plane( \
            Point3D(x,y,z), \
            Point3D(sveX,sveY,sveZ), \
            Point3D(eveX,eveY,eveZ))


   meteor_start_points = {}
   meteor_end_points = {}
   solution = {}

   print("Meteor observations loaded. Ready to compute simple solution.")
   for pkey in planes:
      plane = planes[pkey]
      for obs_id in meteor['observations']:
         print("PKEY/OBS:", pkey, obs_id)
         obs = meteor['observations'][obs_id]
         if obs_id != pkey.upper():
            point_key = pkey.upper() + "-" + obs_id
            meteor['simple_solutions'][point_key] = {}
            meteor_start_points[point_key] = []
            meteor_end_points[point_key] = []
            x = obs['x']
            y = obs['y']
            z = obs['z']
            svpx = obs['sveX']
            svpy = obs['sveY']
            svpz = obs['sveZ']

            evpx = obs['eveX']
            evpy = obs['eveY']
            evpz = obs['eveZ']

            start_line = Line3D(Point3D(x,y,z),Point3D(svpx,svpy,svpz))
            end_line = Line3D(Point3D(x,y,z),Point3D(evpx,evpy,evpz))
            inter = plane.intersection(start_line)


            if hasattr(inter[0], 'p1'):
               p1 = inter[0].p1
               p2 = inter[0].p2
               if p1[2] < p2[2]:
                  sx = float((eval(str(p1[0]))))
                  sy = float((eval(str(p1[1]))))
                  sz = float((eval(str(p1[2]))))
               else:
                  sx = float((eval(str(p2[0]))))
                  sy = float((eval(str(p2[1]))))
                  sz = float((eval(str(p2[2]))))


            else:
               sx = float((eval(str(inter[0].x))))
               sy = float((eval(str(inter[0].y))))
               sz = float((eval(str(inter[0].z))))

            inter = plane.intersection(end_line)

            if hasattr(inter[0], 'p1'):
               p1 = inter[0].p1
               p2 = inter[0].p2
               if p1[2] < p2[2]:
                  ex = float((eval(str(p1[0]))))
                  ey = float((eval(str(p1[1]))))
                  ez = float((eval(str(p1[2]))))
               else:
                  ex = float((eval(str(p2[0]))))
                  ey = float((eval(str(p2[1]))))
                  ez = float((eval(str(p2[2]))))
            else:
               ex = float((eval(str(inter[0].x))))
               ey = float((eval(str(inter[0].y))))
               ez = float((eval(str(inter[0].z))))


            meteor['simple_solutions'][point_key]['start_point']  = [sx,sy,sz]
            meteor['simple_solutions'][point_key]['end_point']  = [ex,ey,ez]
            slat, slon, salt = pm.ecef2geodetic(sx,sy,sz, wgs84)
            elat, elon, ealt = pm.ecef2geodetic(ex,ey,ez, wgs84)
            meteor['simple_solutions'][point_key]['start_point_lla']  = [slat,slon,salt]
            meteor['simple_solutions'][point_key]['end_point_lla']  = [elat,elon,ealt]

            meteor_start_points[point_key].append((sx,sy,sz))
            meteor_end_points[point_key].append((ex,ey,ez))

   print("Interesecting Planes Solution")
   meteor['simple_solve'] = {}
   for key in meteor_start_points:
      start_point = meteor_start_points[key][0]
      end_point =  meteor_end_points[key][0]
      print(start_point)
      track_distance = math.sqrt((end_point[0]-start_point[0])**2 + (end_point[1]-start_point[1])**2 + (end_point[2]-start_point[2])**2)
      print("TRACK DISTANCE:", key, track_distance)
      (st1, st2) = key.split("-")
      print("DURATION:", meteor['observations'][st1]['duration'])
      avg_vel = (track_distance / meteor['observations'][st1]['duration']) / 1000
      print("AVG VELOCITY:", avg_vel, " KM/second")


      slat, slon, salt = pm.ecef2geodetic(float(start_point[0]), float(start_point[1]), float(start_point[2]), wgs84)
      elat, elon, ealt = pm.ecef2geodetic(float(end_point[0]), float(end_point[1]), float(end_point[2]), wgs84)

      rah,dech,az,el,track_2d_dist,entry_angle = calc_radiant(elon,elat,ealt,slon,slat,salt,arg_date, arg_time)
      rah = str(rah).replace(":", " ")
      dech = str(dech).replace(":", " ")
      ra,dec= HMS2deg(str(rah),str(dech))
      print("RADIANT:", rah,dech,az,el,track_2d_dist,entry_angle)
      meteor['simple_solve'][key] = {}
      meteor['simple_solve'][key]['track_start'] = [slat, slon, salt]
      meteor['simple_solve'][key]['track_end'] = [elat, elon, ealt]
      meteor['simple_solve'][key]['radiant'] = [ra,dec]
      meteor['simple_solve'][key]['track_distance'] = track_distance
      meteor['simple_solve'][key]['event_duration'] = meteor['observations'][st1]['duration'] 
      meteor['simple_solve'][key]['velocity_avg'] = avg_vel 
      if ealt < 0 or salt < 0:
         meteor['simple_solve'][key]['status'] = "FAILED TO SOLVE"
      else:
         meteor['simple_solve'][key]['status'] = "SOLVED"


    
      print("Calc orbit")
      dd = arg_date.replace("-", "")
      tt = arg_time.replace(":", "") 
      etime = dd + "-" + tt
      etime2 = dd + tt
      orb_file = event_file.replace(".json", "-hankey-vida-orb.txt")
      #cmd = "cd /home/ams/dvida/WesternMeteorPyLib/wmpl/Trajectory; ./runOrb.py " + str(ra) + " " + str(dec) + " " + str(avg_vel) + " " + str(etime) + " " + str(elat) + " " + str(elon) + " " + str(ealt) + " " + orb_file
      #print(cmd)
      #os.system(cmd)


   simple_file = event_file.replace(".json", "-simple.json")
   save_json_file(simple_file, meteor)
   print("Simple Solution:", simple_file)
   plot_obs_traj(meteor, event_file)


   del(meteor['simple_solutions'])
   save_json_file(simple_file, meteor)

   return(simple_file)

def plot_obs_traj(meteor, event_file):
   matplotlib.use('GTK3Agg')
   meteor_file = event_file
   plot_file = event_file.replace(".json", "-simple-traj.png")
   points = []
   lines = []
   lats = []
   lons = []
   alts = []
   stations = []
   for key in meteor['observations']:
      print(key, meteor['observations'][key]['lat'])
      print(key, meteor['observations'][key]['lng'])
      stations.append(key)
      alts.append(float(meteor['observations'][key]['alt']))
      lats.append(float(meteor['observations'][key]['lat']))
      lons.append(float(meteor['observations'][key]['lng']))


   # structure the trajectory lines
   combo_names = [] 
   start_points = []
   end_points = [] 
   for key in meteor['simple_solutions']:
      start_point = meteor['simple_solutions'][key]['start_point_lla']
      end_point = meteor['simple_solutions'][key]['end_point_lla']
      combo_names.append(key)
      start_points.append(start_point)
      end_points.append(end_point)

   print("Stations:", stations)
   print("Lats:", lats)
   print("Lons:", lons)
   print("Solutions:", combo_names)
   print("Start Points:", start_points)
   print("End Points:", end_points)

   #fig_file = meteor_file.replace(".json", "-fig2.png")
   fig = plt.figure()
   ax = Axes3D(fig)


   #ax.text(Obs1Lon, Obs1Lat,Obs1Alt,Obs1Station,fontsize=10)
   ax.scatter3D(lats,lons,alts,c='r',marker='o')

   # plot trajectory line
   start_lats = []
   start_lons = []
   start_alts = []
   end_lats = []
   end_lons = []
   end_alts = []

   lines = {}

   for i in range(0, len(start_points)):
      slat,slon,salt = start_points[i]
      elat,elon,ealt = end_points[i]
      # Plot trajectory line
      ax.plot([slat,elat],[slon,elon],[salt,ealt])
      start_lats.append(slat)
      start_lons.append(slon)
      start_alts.append(salt)
      end_lats.append(elat)
      end_lons.append(elon)
      end_alts.append(ealt)
      line_key = str(i)
      lines[line_key] = {}
      lines[line_key]['start_lat'] = slat
      lines[line_key]['start_lon'] = slon
      lines[line_key]['start_alt'] = salt
      lines[line_key]['end_lat'] = elat
      lines[line_key]['end_lon'] = elon
      lines[line_key]['end_alt'] = ealt
      lines[line_key]['desc'] = line_key 

   # find median start and end points from each intersecting plane solution
   med_start_lat = float(np.median(start_lats)) 
   med_start_lon = float(np.median(start_lons)) 
   med_start_alt = float(np.median(start_alts)) 
   med_end_lat = float(np.median(end_lats)) 
   med_end_lon = float(np.median(end_lons)) 
   med_end_alt = float(np.median(end_alts)) 

   lines['med_trajectory'] = {}
   lines['med_trajectory']['start_lat'] = med_start_lat
   lines['med_trajectory']['start_lon'] = med_start_lon
   lines['med_trajectory']['start_alt'] = med_start_alt
   lines['med_trajectory']['end_lat'] = med_end_lat
   lines['med_trajectory']['end_lon'] = med_end_lon
   lines['med_trajectory']['end_alt'] = med_end_alt
   lines['med_trajectory']['desc'] = "Median Intersecting Planes Trajectory" 

   # plot lines from obs to start and end
   for i in range(0,len(lats)):
      name = stations[i] 
      lat = lats[i] 
      lon = lons[i] 
      alt = alts[i] 
      ax.plot([lat,med_start_lat],[lon,med_start_lon],[alt,med_start_alt])
      ax.plot([lat,med_end_lat],[lon,med_end_lon],[alt,med_end_alt])
      line_key = name + "-obs-start"
      lines[line_key] = {}
      lines[line_key]['start_lat'] = lat 
      lines[line_key]['start_lon'] = lon 
      lines[line_key]['start_alt'] = 0 
      lines[line_key]['end_lat'] = lines[str(i)]['start_lat']
      lines[line_key]['end_lon'] = lines[str(i)]['start_lon']
      lines[line_key]['end_alt'] = lines[str(i)]['start_alt']
      lines[line_key]['desc'] = line_key 

      line_key = name + "-obs-en"
      lines[line_key] = {}
      lines[line_key]['start_lat'] = lat 
      lines[line_key]['start_lon'] = lon 
      lines[line_key]['start_alt'] = 0
      lines[line_key]['end_lat'] = lines[str(i)]['end_lat']
      lines[line_key]['end_lon'] = lines[str(i)]['end_lon']
      lines[line_key]['end_alt'] = lines[str(i)]['end_alt']
      lines[line_key]['desc'] = line_key 


   plt.savefig(plot_file)
   plt.show()
   kml_file = plot_file.replace(".png", ".kml")

   points = {}
   polys = {}
   print("MAKE KML", kml_file)
   # Now save the same info as a KML
   make_easykml(kml_file, points, lines, polys)
   print("Saved:", kml_file)

def make_easykml(kml_file, points={}, lines={}, polys={}):
   print("Making KML", kml_file)
   print("Points:", points)
   print("LINES:", lines)
   print("Polys:", polys)
   
   colors = [
      'FF641E16',
      'FF512E5F',
      'FF154360',
      'FF0E6251',
      'FF145A32',
      'FF7D6608',
      'FF78281F',
      'FF4A235A',
      'FF1B4F72',
      'FF0B5345',
      'FF186A3B',
      'FF7E5109'
   ]


   kml = simplekml.Kml()

   cc = 0
   for key in lines:
      slat,slon,salt,sdesc =lines[key]['start_lat'], lines[key]['start_lon'],lines[key]['start_alt'], lines[key]['desc']
      elat,elon,ealt,edesc =lines[key]['end_lat'], lines[key]['end_lon'],lines[key]['end_alt'], lines[key]['desc']
      line = kml.newlinestring(name=sdesc, description="", coords=[(slon,slat,salt),(elon,elat,ealt)])
      line.altitudemode = simplekml.AltitudeMode.relativetoground
      if "color" in lines[key]:
         line.linestyle.color = lines[key]['color']
      else:
         line.linestyle.color = colors[cc]
      if "width" in lines[key]:
         line.linestyle.width= lines[key]['width']
      else:
         line.linestyle.width= 5
      print("LINE:", slat,slon,salt,sdesc, elat,elon,ealt,edesc)
      cc = cc + 1
      if cc >= len(colors):
         cc = 0


   for key in points:
      lat,lon,alt,desc =points[key]['lat'], points[key]['lon'],points[key]['alt'], points[key]['desc']
      point = kml.newpoint(name=desc,coords=[(lon,lat,alt)])
      if "icon" in points[key]:
          point.style.iconstyle.icon.href = points[key]['icon']
      else:
          point.style.iconstyle.icon.href = 'http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png'

   print("SAVED KML:", kml_file)
   kml.save(kml_file)









def run_event_cmd(event_id):    
   year = event_id[0:4]
   mon = event_id[5:7]
   dom = event_id[8:10]
   day = event_id[0:10]
   station_id = json_conf['site']['ams_id']  

   events_file = "/mnt/ams2/meteor_archive/" + station_id + "/EVENTS/" + year + "/" + year + "-events.json"
   print(events_file)
   if cfe(events_file) == 1: 
      events = load_json_file(events_file)
   else:
      events = {}
   event = events[event_id]
   args = []
   for i in range(0,len(event['arc_files'])):
      arc = event['arc_files'][i]
      if arc == 'pending':
         print("not all files have been archived. Can't solve yet!")
         return()
      st = event['stations'][i]
      ma_arc_file = "/mnt/ams2/meteor_archive/" + st + "/METEOR/" + year + "/" + mon + "/" + dom + "/" +  arc 
      wasabi_arc_file = "/mnt/wasabi/" + st + "/METEOR/" + year + "/" + mon + "/" + dom + "/" +  arc 
      if st != station_id:
         ma_sd = ma_arc_file.replace(".json", "-SD.mp4")
         ma_hd = ma_arc_file.replace(".json", "-HD.mp4")
         ws_sd = ma_sd.replace("ams2/meteor_archive", "wasabi")
         ws_hd = ma_hd.replace("ams2/meteor_archive", "wasabi")
         temp = ma_arc_file.split("/")[-1]
         ma_dir = ma_arc_file.replace(temp, "")
         if cfe(ma_dir, 1) == 0:
            os.makedirs(ma_dir)
         if cfe(ma_arc_file) == 0:
            cmd = "cp " + wasabi_arc_file + " " + ma_arc_file
            print(cmd)
            os.system(cmd)
         if cfe(ma_sd) == 0:
            cmd = "cp " + ws_sd + " " + ma_sd
            print(cmd)
            os.system(cmd)
         if cfe(ma_hd) == 0:
            cmd = "cp " + ws_hd + " " + ma_hd
            print(cmd)
            os.system(cmd)
         if cfe(ma_arc_file) == 0 :
            print("Could not sync file from wasabi. It must not be there yet. Aborting solve until all files are sync'd.") 
            return()


   #lets make sure there is only one obs per site.
   station_files = {}
   for i in range(0,len(event['arc_files'])):
      arc = event['arc_files'][i]
      st = event['stations'][i]
      ma_arc_file = "/mnt/ams2/meteor_archive/" + st + "/METEOR/" + year + "/" + mon + "/" + dom + "/" +  arc 
      dist = dist_from_center(ma_arc_file)
      if st not in station_files:
         station_files[st] = []
      station_files[st].append((ma_arc_file,dist))

   for st in station_files:
      if len(station_files[st]) > 1:
         # we have more than one match pick the best one
         temp = sorted(station_files[st], key=lambda x: x[1], reverse=False)
         arc = temp[0][0] 
         ma_arc_file = arc 
         args.append(ma_arc_file)
      else:
         arc = station_files[st][0][0]
         print("ARC:", arc)
         ma_arc_file = arc 
         args.append(ma_arc_file)

   event_dir = "/mnt/ams2/meteor_archive/" + station_id + "/EVENTS/" + year + "/" + day + "/" + event_id + "/"
   event_file = event_dir+ event_id + ".json"
   os.system("rm " + event_dir + "*")
   if cfe(event_dir, 1) == 0:
      os.makedirs(event_dir)

 
   print("ARGS:", args)
   obs_info, eid = make_event_obs_file(args)
   print(event_file)
   save_json_file(event_file, obs_info)

   # try to solve the event with various solvers
   solutions = []
   # first run a simple solve and see if this event can be solved in the simpliest way!

   #simple_file = simple_solve(event_file)

   simple_file = simple_solve(event_file)
   if simple_file != 0:
      solutions.append(('hankey_simple', 1, simple_file))
   else:
      solutions.append(('hankey_simple', 0, 0))
      print("Simple solve failed!")
  

   cmd = "cd /home/ams/dvida/WesternMeteorPyLib/wmpl/Trajectory; python3 AS6Trajectory.py " + event_dir + event_id + ".json"
   print(cmd)
   os.system(cmd)
   report_files = glob.glob(event_dir + "*_report.json")
   print("EVENT DIR:", event_dir)
   print("REPORT FILES:", report_files)
   if len(report_files) > 0:
      solutions.append(('vida_ip', 1, report_files[0]))
      vida = 1

   else:
      failed_file = event_file + ".failed"
      os.system("touch " + failed_file)
      vida = 0
      solutions.append(('vida_ip', 0, ""))

   event['solutions'] = solutions
   events[event_id] = event
   print("Saved : ", event_id, events_file)
   save_json_file(events_file, events)
   if len(report_files) > 0:
      print("make_event_kml " + report_files[0]) 
      make_event_kml(report_files[0])

   


def run_event(event_count, time_id, event_args):
   
   obs_info, event_id = make_event_obs_file(event_args)
   edir = "/mnt/ams2/events/" + event_id + "/"
   if cfe(edir, 1) == 0:
      os.system("mkdir " + edir)
   save_json_file(edir + event_id + ".json", obs_info)
   print(edir + event_id + ".json")
   day = event_id[0:8]
   fp = open(edir + "../" + day + ".sh", "a")
   cmd = "cd /home/ams/dvida/WesternMeteorPyLib/wmpl/Trajectory; python3 AS6Trajectory.py " + edir + event_id + ".json"
   print(cmd)
   fp.write(cmd + "\n")
   fp.close()
   #os.system(cmd)

def run(event_file):
   ed = load_json_file(event_file)
   event_args = []
   for file in ed:
      if "METEOR" in file:
         event_args.append(file)
   obs_info, event_id = make_event_obs_file(event_args)
   save_json_file(event_file,obs_info)

   cmd = "cd /home/ams/dvida/WesternMeteorPyLib/wmpl/Trajectory; python3 AS6Trajectory.py " + event_file
   print(cmd)
   #os.system(cmd)


def find_event(station, file, clip_start_time, events, captures):
   if len(events) == 0:
      event_id = 1
      events[event_id] = {}
      events[event_id]['stations'] = {}
      events[event_id]['stations'][station] = {}
      events[event_id]['stations'][station]['files'] = []
      events[event_id]['stations'][station]['files'].append(file)
      events[event_id]['stations'][station]['clip_times'] = []
      events[event_id]['stations'][station]['clip_times'].append(clip_start_time)
      events[event_id]['start_time'] = clip_start_time
      return(event_id, events)

   # check to see if there is already an event within 3 seconds of this event
   # if so update the event with this observation
   for event_id in events:
      event_start_time = events[event_id]['start_time']
      elapsed = abs((clip_start_time - event_start_time).total_seconds())
      if elapsed < 3:
         print("FOUND:", event_id, clip_start_time, event_start_time, elapsed)
         events = update_event(events, event_id, station, file, clip_start_time)
         return(event_id, events)

   # if we get to this point, the event has not been found already so make a new one
   new_event_id = max(events.keys()) + 1
   events, event_id = add_event(events, new_event_id, station, file, clip_start_time) 
   return(event_id, events)

def add_event(events, event_id, station, file, clip_start_time):
   events[event_id] = {}
   events[event_id]['stations'] = {}
   events[event_id]['stations'][station] = {}
   events[event_id]['stations'][station]['files'] = []
   events[event_id]['stations'][station]['clip_times'] = []
   events[event_id]['stations'][station]['files'].append(file)
   events[event_id]['stations'][station]['clip_times'].append(clip_start_time)
   events[event_id]['start_time'] = clip_start_time
   return(events, event_id)

def update_event(events, event_id, station, file, clip_start_time):
   if station not in events[event_id]['stations']:
      events[event_id]['stations'][station] = {}
      events[event_id]['stations'][station]['files'] = []
      events[event_id]['stations'][station]['clip_times'] = []
   events[event_id]['stations'][station]['clip_times'].append(clip_start_time)
   events[event_id]['stations'][station]['files'].append(file)
   return(events)

def file_to_date(file):
   fel = file.split("_")
   year = fel[0]
   mon = fel[1]
   day = fel[2]
   hour = fel[3]
   min = fel[4]
   sec = fel[5]
   msec = fel[6]
   cam_info = fel[7]
   cam_info = cam_info.replace(".json", "")
   cam_id, trim = cam_info.split("-")
   trim_sec = int(trim.replace("trim", "")) / 25
   f_date_str = year + "-" + mon + "-" + day + " " + hour + ":" + min + ":" + sec
   f_datetime = datetime.datetime.strptime(f_date_str, "%Y-%m-%d %H:%M:%S")

   clip_start_time = f_datetime + datetime.timedelta(0,trim_sec)
   return(clip_start_time)

def file_to_arc_dir(file, station):
   fel = file.split("_")
   year = fel[0]
   mon = fel[1]
   day = fel[2]
   hour = fel[3]
   min = fel[4]
   sec = fel[5]
   msec = fel[6]
   cam_info = fel[7]
   cam_info = cam_info.replace(".json", "")
   cam_id, trim = cam_info.split("-")
   arc_dir = "/mnt/wasabi/" + station + "/METEOR/" + year + "/" + mon + "/" + day + "/"
   return(arc_dir)


def load_station_index(this_station, date, arc_folder ):
   sdata = []
   year, month, day = date.split("_")
   index_file = arc_folder + this_station + "/METEOR/" + year + "/" + year + ".json"
   print(index_file)
   index_data = load_json_file(index_file)
   for st in index_data['months'][month]:
      for data in st[day]:
         sdata.append(data)
   return(sdata)

def make_event_kml(report_file):
   event_file = report_file
   kml_file = report_file.replace(".json", ".kml")
   report_data = load_json_file(report_file)

   monte_report_file = report_file.replace("_report.json", "_mc_report.json")
   mcf = monte_report_file.split("/")[-1]
   mcd = monte_report_file.replace(mcf, "")

   monte_file = mcd + "Monte Carlo" + mcf
   print("Report File: ", report_file)
   print("MONTE: ", monte_file)
   if cfe(monte_file) == 1:
      mc_data = load_json_file(monte_file)
   else:
      mc_data = None

   kml = simplekml.Kml()
   event_data = load_json_file(event_file)
   observers = {}
   done = {}
   obs_folder = kml.newfolder(name='Stations')
   #track_folder = kml.newfolder(name='Track')
   #monte_folder = kml.newfolder(name='Monte Carlo Track')
   colors = [
      'FF641E16',
      'FF512E5F',
      'FF154360',
      'FF0E6251',
      'FF145A32',
      'FF7D6608',
      'FF78281F',
      'FF4A235A',
      'FF1B4F72',
      'FF0B5345',
      'FF186A3B',
      'FF7E5109'
   ]


   for key in event_data:
      if "/mnt/" in key:
         print(event_data[key]['lat'])
         observers[key] = {}
         observers[key]['lat'] = event_data[key]['lat'] 
         observers[key]['lon'] = event_data[key]['lon'] 
         if "key" not in done:
            point = obs_folder.newpoint(name=event_data[key]['station_id'],coords=[(event_data[key]['lon'],event_data[key]['lat'])])
            done[key] = 1


   start_x,start_y,start_z = math.degrees(report_data['rbeg_lon']), math.degrees(report_data['rbeg_lat']), report_data['rbeg_ele']/1000
   end_x,end_y,end_z = math.degrees(report_data['rend_lon']), math.degrees(report_data['rend_lat']), report_data['rend_ele']/1000

   if mc_data is not None: 
      mc_start_x,mc_start_y,mc_start_z = math.degrees(mc_data['rbeg_lon']), math.degrees(mc_data['rbeg_lat']), mc_data['rbeg_ele']/1000
      mc_end_x,mc_end_y,mc_end_z = math.degrees(mc_data['rend_lon']), math.degrees(mc_data['rend_lat']), mc_data['rend_ele']/1000

   poly = kml.newpolygon(name='Meteor Track')
   poly.outerboundaryis = [(start_x,start_y,start_z*1000),(end_x,end_y,end_z*1000),(end_x,end_y,0),(start_x,start_y,0)]
   poly.altitudemode = simplekml.AltitudeMode.relativetoground
   poly.style.polystyle.color = simplekml.Color.red

   poly.style.polystyle.outline = 1

   if mc_data is not None:
      poly = kml.newpolygon(name='Monte Carlo Meteor Track')
      poly.outerboundaryis = [(mc_start_x,mc_start_y,mc_start_z*1000),(mc_end_x,mc_end_y,mc_end_z*1000),(mc_end_x,mc_end_y,0),(mc_start_x,mc_start_y,0)]
      poly.altitudemode = simplekml.AltitudeMode.relativetoground
      poly.style.polystyle.color = simplekml.Color.blue
      poly.style.polystyle.outline = 1

   # draw start / end obs lines
   for obs_key in report_data['observations']:
    
      station_info = report_data['observations'][obs_key]['station_info']
      olon= float(station_info[2].replace(" ", ""))


      olat = float(station_info[3].replace(" ", ""))
      oht = float(station_info[4].replace(" ", ""))
      print("ST:", station_info)
      print("LAT/LON:", olat, olon, oht)
      points = report_data['observations'][obs_key]['point_info']
      pt = points[0]
      ept = points[-1]
      slat = pt['model_lat']
      slon = pt['model_lon']
      sht = pt['model_ht'] 
      elat = ept['model_lat']
      elon = ept['model_lon']
      eht = ept['model_ht'] 
      print("LINE OBS/START:", olon,olat,oht,slon,slat,sht)
      desc = obs_key + " start"
      desc2 = obs_key + " end"
      line = kml.newlinestring(name=desc, description="", coords=[(olon,olat,oht),(slon,slat,sht)])
      line.altitudemode = simplekml.AltitudeMode.relativetoground
      line = kml.newlinestring(name=desc2, description="", coords=[(olon,olat,oht),(elon,elat,eht)])
      line.altitudemode = simplekml.AltitudeMode.relativetoground

   # draw start / end obs lines
   if mc_data is not None:
      for obs_key in mc_data['observations']:

         station_info = mc_data['observations'][obs_key]['station_info']
         olon= float(station_info[2].replace(" ", ""))


         olat = float(station_info[3].replace(" ", ""))
         oht = float(station_info[4].replace(" ", ""))
         print("ST:", station_info)
         print("LAT/LON:", olat, olon, oht)
         points = mc_data['observations'][obs_key]['point_info']
         pt = points[0]
         ept = points[-1]
         slat = pt['model_lat']
         slon = pt['model_lon']
         sht = pt['model_ht']
         elat = ept['model_lat']
         elon = ept['model_lon']
         eht = ept['model_ht']
         print("LINE OBS/START:", olon,olat,oht,slon,slat,sht)
         desc = obs_key + " start"
         desc2 = obs_key + " end"

   kml.save(kml_file)
   print(kml_file)
#

def make_sync_kml(sync_frames,meteor,master_key,obs_sol):




   cc = 0
   for key in sync_frames:
      for ekey in sync_frames[master_key]:
         for obs in obs_sol:
            xob,mob = obs.split("-")
            olon = observers[mob]['lon']
            olat = observers[mob]['lat']
            #sol_key = obs
            #sol_folder = kml.newfolder(name=sol_key)
            fl_msft = master_key + "_ft"
            fl_ft = obs + "_ft"
            fl_fn = obs + "_fn"
            fl_lon = obs + "_lon"
            fl_lat = obs + "_lat"
            fl_alt = obs + "_alt"
            fl_vfs = obs + "_vfs"
            #if fl_ft in sync_frames[master_key][ekey]:
            #   rpt = rpt + " " + str(sync_frames[master_key][ekey][fl_ft]) + " "
            if fl_lon in sync_frames[master_key][ekey]:
               ft = sync_frames[master_key][ekey][fl_msft]
               lon = float(sync_frames[master_key][ekey][fl_lon])
               lat = float(sync_frames[master_key][ekey][fl_lat])
               alt = float(sync_frames[master_key][ekey][fl_alt])  * 1000
               vfs = float(sync_frames[master_key][ekey][fl_vfs])
               color = colors[cc]
               #point = sol_folder.newpoint(coords=[(lon,lat,alt)])
               point = kml.newpoint(coords=[(lon,lat,alt)])

               point.altitudemode = simplekml.AltitudeMode.relativetoground
               point.style.iconstyle.icon.href = 'http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png'

               line = kml.newlinestring(name="", description="", coords=[(olon,olat,0),(lon,lat,alt)])
               line.altitudemode = simplekml.AltitudeMode.relativetoground
               line.linestyle.color = color

               point.style.iconstyle.color = color
               line = kml.newlinestring(name="", description="", coords=[(lon,lat,0),(lon,lat,alt)])
               line.altitudemode = simplekml.AltitudeMode.relativetoground
               line.linestyle.color = color
               fts = float(str(ft)[-6:])
               curve_data[obs]['xs'].append(fts)
               curve_data[obs]['ys'].append(vfs)
         cc = cc + 1
         if cc > len(colors)-1:
            cc = 0

   oc = 0
   pltz = {}
   for obs in curve_data:
      pltz[obs], = plt.plot(curve_data[obs]['xs'], curve_data[obs]['ys'])
      oc = oc + 1
      print("XS:", curve_data[obs]['xs'])
      print("YS:", curve_data[obs]['ys'])

   code1 = ""
   code2 = ""
   for obs in pltz:
      print(obs)
      if code1 != "":
         code1 = code1 + ","
      if code2 != "":
         code2 = code2 + ","
      code1 = code1 + "pltz['" + obs + "']"
      code2 = code2 + "\"" + obs + "\""
   fcode = "plt.legend((" + code1 + "),(" + code2 + "))"
   print(fcode)
   eval(fcode)
      #plt.legend(pltz[obs], obs)

   #plt.show()
   plt.title('Meteor Velocity KM/Second')
   plt.ylabel('KM/Sec From Start')
   plt.xlabel('Frame TIme 1/25 sec')
   vel_fig_file = meteor['meteor_file'].replace(".json", "-fig_vel.png")
   plt.savefig(vel_fig_file)
   print(vel_fig_file)

   kml_file = vel_fig_file.replace("-fig_vel.png",".kml")
   kml.save(kml_file)
   print(kml_file)

def sync_detects():
   network = json_conf['site']['network_sites'].split(",")
   for st in network:
      if cfe("/mnt/ams2/meteor_archive/" + st + "/DETECTS/", 1) == 0:
         os.system("mkdir /mnt/ams2/meteor_archive/" + st + "/DETECTS/")
      cmd = "cp /mnt/wasabi/" + st + "/DETECTS/meteor_index.json.gz /mnt/ams2/meteor_archive/" + st + "/DETECTS/"
      print(cmd)
      os.system(cmd)
      cmd = "gunzip -f /mnt/ams2/meteor_archive/" + st + "/DETECTS/meteor_index.json.gz"
      print(cmd)
      os.system(cmd)

def run_events(year):
   station_id = json_conf['site']['ams_id']
   event_file = "/mnt/ams2/meteor_archive/" + station_id + "/EVENTS/" + year + "/" + year + "-events.json"
   print("EVENT FILE:", event_file)
   events = load_json_file(event_file)
   for event_id in events:
      event = events[event_id]
      if 'status' not in event:
         cmd = "cd /home/ams/amscams/pythonv2; ./solve.py rec " + event_id 
         print(cmd)
         os.system(cmd)


def run_events_old(year):
   station_id = json_conf['site']['ams_id']
   event_file = "/mnt/ams2/meteor_archive/" + station_id + "/EVENTS/" + year + "/" + year + "-events.json"
   print("EVENT FILE:", event_file)
   events = load_json_file(event_file)
   for id in events:
      fail = 0
      event_id = id
      event = events[id]
      all_arc = 1
      ac = 0
      for af in event['arc_files']:
         if af == "pending":
            all_arc = 0
         ac = ac + 1
      if all_arc == 1:
         print("This event is ready to be solved.", id)
         all_arc_files = []
         for i in range(0,len(event['arc_files'])):
            station = event['stations'][i]
            arc_file = event['arc_files'][i]
            clip_start = event['clip_starts'][i]
            print(station, arc_file, clip_start)
            if station == station_id: 
               ma_file = "/mnt/ams2/meteor_archive/" + station + "/METEOR/" + arc_file[0:4] + "/" + arc_file[5:7] + "/" + arc_file[8:10] + "/" + arc_file
               all_arc_files.append(ma_file)
            if station != station_id: 
               wasabi_file = "/mnt/wasabi/" + station + "/METEOR/" + arc_file[0:4] + "/" + arc_file[5:7] + "/" + arc_file[8:10] + "/" + arc_file
               ma_file = "/mnt/ams2/meteor_archive/" + station + "/METEOR/" + arc_file[0:4] + "/" + arc_file[5:7] + "/" + arc_file[8:10] + "/" + arc_file
               all_arc_files.append(ma_file)
               if cfe(ma_file) == 0:
                  print("Remote Meteor info missing from MA!")
                  if cfe(wasabi_file) == 1:
                     print("WASBI EXISTS!", wasabi_file)
                     tmp = ma_file.split("/")[-1]
                     ma_dir = ma_file.replace(tmp, "")
                     if cfe(ma_dir, 1) == 0:
                        os.makedirs(ma_dir)
                     os.system("cp " + wasabi_file + " " + ma_file)
                  else:
                     print("NO WASABI FILE!", wasabi_file)
                     fail = 1
         if fail == 1:
            continue
 
         if fail == 0: 
            print("Lets solve the event...")
            print("But first, check that no else has started solving this one!")
            solve_status = check_solve_status(id)
            if solve_status == 1:
               print("This event is already solved or being worked on.")
               continue

            event_year = event_id[0:4]
            event_day = event_id[0:10]
            ma_event_dir = "/mnt/ams2/meteor_archive/" + station_id + "/EVENTS/" + event_year + "/" + event_day + "/" + event_id + "/"
            wasabi_event_dir = "/mnt/wasabi/" + station_id + "/EVENTS/" + event_year + "/" + event_day + "/"  + event_id + "/" 
            if cfe(ma_event_dir, 1) == 0:
               print("MAKING:", ma_event_dir)   
               os.makedirs(ma_event_dir)   
               print("MAKING WASBAI EVENT DIR:", wasabi_event_dir)   
               os.makedirs(wasabi_event_dir)   
            else:
               print("We aleady started on this one, did we finish?") 
               year,mon,day,hour,min,sec = event_id.split("_") 
               report_base = year + mon + day + "_" + hour + min + sec 
               report_file = report_base + "_report.txt"
               if cfe(ma_event_dir + report_file) == 1:
                  print("This event has been solved already.", event_id)
                  continue

            # 
            obs_info, new_event_id = make_event_obs_file(all_arc_files)
            print(obs_info)
            print(new_event_id)
            save_json_file(ma_event_dir + event_id + ".json", obs_info)
            print("EVENT FILE:", ma_event_dir + event_id + ".json")
            #cmd = "cd /home/ams/dvida/WesternMeteorPyLib/wmpl/Trajectory; python3 AS6Trajectory.py " + ma_event_dir + event_id + ".json"
            #print(cmd)
            #os.system(cmd)
            cmd = "cd /home/ams/amscams/; ./solve.py rec " + event_id 
            print(cmd)
            exit()

            if cfe(ma_event_dir + report_file) == 1:
               print("Event solved. Copy to wasabi.", event_id)
            else:
               print("Event failed to solved. Set fail flags.", event_id)
                  



           


def check_solve_status(event_id):
   network_sites = json_conf['site']['network_sites'].split(",")
   for st in network_sites:
      event_year = event_id[0:4]
      event_day = event_id[0:10]
      ma_event_dir = "/mnt/ams2/meteor_archive/" + st + "/EVENTS/" + event_year + "/" + event_day + "/" + event_id + "/"
      wasabi_event_dir = "/mnt/wasabi/" + st + "/EVENTS/" + event_year + "/" + event_day + "/"  + event_id + "/" 
      print("Checking...", st, wasabi_event_dir) 
      if cfe(wasabi_event_dir) == 1:
         return(1)
      else:
         return(0)
   
def update_event_index(year):
   station_id = json_conf['site']['ams_id']
   event_index = "/mnt/ams2/meteor_archive/" + station_id + "/EVENTS/" + year + "/" + year + "-events.json"

   print(event_index)
   event_data = load_json_file(event_index)
   for event_id in event_data:
      event_year,mon,event_day,hour,min,sec = event_id.split("_") 
      event_date = event_year + "_" + mon + "_" + event_day 
      ma_event_dir = "/mnt/ams2/meteor_archive/" + station_id + "/EVENTS/" + event_year + "/" + event_date + "/" + event_id + "/"
      wasabi_event_dir = "/mnt/wasabi/" + station_id + "/EVENTS/" + event_year + "/" + event_day + "/"  + event_id + "/" 
      event_file = ma_event_dir + event_id + ".json"
      event_status,event_status_desc,report_data = get_event_status(event_id, event_file)
      if event_status == 1:
         print("SOLVER STATUS:", event_status)
         for log in event_status_desc:
            print(log)
         run_cmd = "cd /home/ams/dvida/WesternMeteorPyLib/wmpl/Trajectory; python3 AS6Trajectory.py " + ma_event_dir + event_id + ".json"
         print(run_cmd)
         if report_data['IAU_code'] != '':
            print("IAU CODE:'" + str(report_data['IAU_code']) + "'")
      if event_status < 0:
         print("EVENT FAILED:", event_id)
         for log in event_status_desc:
            print(log)

def get_event_status(event_id ):
   # check if solution was attempted
   #ef = event_file.split("/")[-1]
   station_id = json_conf['station_id']
   event_year = event_id[0:4]
   event_dir = "/mnt/ams2/meteor_archive/" + station_id + "/EVENTS/" + event_year + "/" + event_id + "/"
   
   year,mon,day,hour,min,sec = event_id.split("_") 
   report_base = year + mon + day + "_" + hour + min + sec 
   report_file = event_dir + report_base + "_report.txt"
   fail_file = event_file + ".failed"
   bad_orbit = 0
   bad_res = 0
   bad_obs = []
   logger = []
   status = 0 
   rd = None
   if cfe(event_dir, 1) == 1:
      logger.append("Event run attempted.")
      if cfe(event_file) == 1:
         logger.append("Event run file created.")
      if cfe(fail_file) == 1:
         status = -1
         logger.append("Event run failed.")
      if cfe(report_file) == 1:
         report_json = report_file.replace(".txt", ".json")
         rd = load_json_file(report_json) 
         rpt_text = []
         fp = open(report_file, "r")
         for line in fp:
            rpt_text.append(line.replace("\n", ""))
            if "IAU code" in line:
               IAU_code = line.replace("IAU code =", "")
               IAU_code = IAU_code.replace("\n", "")
               IAU_code = IAU_code.replace(" ", "")
               IAU_code = IAU_code.replace("...", "")
         
               rd['IAU_code'] = IAU_code
         
          
         status = 1
         logger.append("Event solution computed successfully.")
         if "orbit" in rd:
            if rd['orbit']['a'] < 0 or rd['orbit']['e'] > 1:
               bad_orbit = 1
      else:
         logger.append("FAIL: Solver ran but failed to solve..")
      if (bad_orbit == 1):
         logger.append("FAIL: Event orbit is bad." + str(rd['orbit']['a']) + " " + str(rd['orbit']['e']))
         status = -2
      if (bad_res == 1):
         status = -2
         logger.append("FAIL: Bad residuals from." + str(bad_obs))
   return(status, logger, rd)

def sync_ms_previews(year):
   this_station = json_conf['site']['ams_id']
   events_dir = "/mnt/ams2/meteor_archive/" + this_station + "/EVENTS/" 
   events_file = events_dir + year + "/" + year + "-events.json"
   events = load_json_file(events_file)
   print("<table border=1>")
   print("<tr><td>Event ID</td><td>Observations</td><td>Event Status</td></tr>")

   for event_id in events:
      row = ""
      event = events[event_id]

      status = "unsolved"
      slink = ""
      if "solutions" in event:
         status = ""
         for sol in event['solutions']:
            solver, solve_status, report_file = sol
            if solve_status == 0:
               ss = "failed"
            else:
               ss = "success"
               slink = "<a href=webUI.py?cmd=event_detail&event_id=" + event_id + ">"
            status = status + solver + " " + ss  + "<BR>"

      row += "<tr><td>" + slink  + event_id + "</a></td><td>"
      for i in range(0, len(event['stations'])):
         arc_file = event['arc_files'][i]
         old_file = event['files'][i]
         of = old_file.split("/")[-1]
         year = of[0:4]
         day = of[0:10]
         station = event['stations'][i]
         prev_fn = of.replace(".json", "-prev-crop.jpg")
         if station != this_station:      
            prev_dir = "/mnt/ams2/meteor_archive/" + station + "/DETECTS/PREVIEW/" + year + "/" + day + "/"  
            prev_img = "/mnt/ams2/meteor_archive/" + station + "/DETECTS/PREVIEW/" + year + "/" + day + "/"  + prev_fn
            wb_prev_img = "/mnt/wasabi/" + station + "/DETECTS/PREVIEW/" + year + "/" + day + "/"  + prev_fn
            prev_imgs = ""
            if cfe(prev_dir, 1) == 0:
               os.makedirs(prev_dir)
            if cfe(prev_img) == 0:
               cmd = "cp " + wb_prev_img + " " + prev_img
               print(cmd)
               os.system(cmd)


if sys.argv[1] == "file":
   find_multi_station_matches(sys.argv[2])
if sys.argv[1] == "run":
   run(sys.argv[2])
if sys.argv[1] == "day":
   build_match_index_day(sys.argv[2])
if sys.argv[1] == "make_event_kml":
   make_event_kml(sys.argv[2])
if sys.argv[1] == "sync_detects":
   sync_detects()
if sys.argv[1] == "be":
   build_events(sys.argv[2])
if sys.argv[1] == "re":
   run_events(sys.argv[2])
if sys.argv[1] == "uei":
   update_event_index(sys.argv[2])
if sys.argv[1] == "rec":
   run_event_cmd(sys.argv[2])
if sys.argv[1] == "smp":
   sync_ms_previews(sys.argv[2])
