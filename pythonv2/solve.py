#!/usr/bin/python3
from lib.FileIO import load_json_file, save_json_file, cfe
import simplekml
import sys
import json
from lib.REDUCE_VARS import *
from lib.Video_Tools_cv_pos import *
from lib.Video_Tools_cv import *
from PIL import ImageFont, ImageDraw, Image, ImageChops
from lib.VIDEO_VARS import *
from lib.UtilLib import calc_dist,find_angle, best_fit_slope_and_intercept
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
json_conf = load_json_file("../conf/as6.json")

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
      print("FILE:", files[c])
      obs_data = load_json_file(files[c])
      #obs_data['event_id'] = event_id
      #save_json_file(files[c], obs_data)
      thetas= []
      phis = []
      times = []
      fc = 0
      print("FRAMES:", len(obs_data['frames']))
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
      obs_info[files[c]]['sd_video_file'] = obs_data['info']['sd_vid']
      obs_info[files[c]]['hd_video_file'] = obs_data['info']['hd_vid']
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
   cmd = "cd /home/ams/dvida/WesternMeteorPyLib/wmpl/Trajectory; python3 AS6Trajectory.py " + event_file
   print(cmd)
   os.system(cmd)


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

def make_event_kml(event_file):
   kml_file = event_file.replace(".json", ".kml")
   report_file = event_file.replace(".json", "_report.json")
   rf = report_file.split("/")[-1]
   rf1 = rf[0:8] 
   rf2 = rf[8:14] 
   rd = report_file.replace(rf, rf1 + "_" + rf2 + "_report.json")
   report_file = rd
   print(rf1)
   print(rf2)
   print(rd)

   monte_report_file = report_file.replace("_report.json", "_mc_report.json")
   mcf = monte_report_file.split("/")[-1]
   mcd = monte_report_file.replace(mcf, "")

   monte_file = mcd + "Monte Carlo" + mcf
   print("Report File: ", report_file)
   print("MONTE: ", monte_file)
   mc_data = load_json_file(monte_file)

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

   report_data = load_json_file(rd)

   start_x,start_y,start_z = math.degrees(report_data['rbeg_lon']), math.degrees(report_data['rbeg_lat']), report_data['rbeg_ele']/1000
   end_x,end_y,end_z = math.degrees(report_data['rend_lon']), math.degrees(report_data['rend_lat']), report_data['rend_ele']/1000

   mc_start_x,mc_start_y,mc_start_z = math.degrees(mc_data['rbeg_lon']), math.degrees(mc_data['rbeg_lat']), mc_data['rbeg_ele']/1000
   mc_end_x,mc_end_y,mc_end_z = math.degrees(mc_data['rend_lon']), math.degrees(mc_data['rend_lat']), mc_data['rend_ele']/1000

   poly = kml.newpolygon(name='Meteor Track')
   poly.outerboundaryis = [(start_x,start_y,start_z*1000),(end_x,end_y,end_z*1000),(end_x,end_y,0),(start_x,start_y,0)]
   poly.altitudemode = simplekml.AltitudeMode.relativetoground
   poly.style.polystyle.color = simplekml.Color.red

   poly.style.polystyle.outline = 1

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
      #monte_folder.line = kml.newlinestring(name=desc, description="", coords=[(olon,olat,oht),(slon,slat,sht)])
      #monte_folder.line.altitudemode = simplekml.AltitudeMode.relativetoground
      #monte_folder.line = kml.newlinestring(name=desc2, description="", coords=[(olon,olat,oht),(elon,elat,eht)])
      #monte_folder.line.altitudemode = simplekml.AltitudeMode.relativetoground


      
      #color = colors[0]
      #line.linestyle.color = color
      #line = kml.newlinestring(name="", description="", coords=[(olon,olat,0),(lon,lat,alt)])


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



if sys.argv[1] == "file":
   find_multi_station_matches(sys.argv[2])
if sys.argv[1] == "run":
   run(sys.argv[2])
if sys.argv[1] == "day":
   build_match_index_day(sys.argv[2])
if sys.argv[1] == "make_event_kml":
   make_event_kml(sys.argv[2])
