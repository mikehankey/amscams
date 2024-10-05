import sys
from lib.select_points import select_points
from lib.fit_lines import remove_outliers, fit_lines, find_best_fitting_line
from lib.multi_frame_image import multi_frame_image
import pickle
import glob
import sqlite3
import subprocess
import PySimpleGUI as sg
import math
import boto3
import matplotlib
import matplotlib.pyplot as plt
import simplekml
import time
import requests
import boto3
import redis
import numpy as np
import datetime
import simplejson as json
import os, select, sys
import shutil
import platform
from termcolor import colored
import s3fs
import numpy as np
from math import sin, cos, atan2, sqrt, radians, degrees
from lib.PipeUtil import fit_and_distribute
# Constants
EARTH_RADIUS_KM = 6371.0

#from Classes.MovieMaker import MovieMaker
#from Classes.RenderFrames import RenderFrames
from lib.PipeAutoCal import XYtoRADec , find_stars_with_grid

from prettytable import PrettyTable as pt
from calendar import monthrange
from boto3.dynamodb.conditions import Key
from RMS.Math import angularSeparation
from PIL import ImageFont, ImageDraw, Image, ImageChops
from ransac_lib import ransac_outliers
from sklearn.cluster import DBSCAN
from sklearn import metrics
from sklearn.datasets import make_blobs
from sklearn.preprocessing import StandardScaler
from multiprocessing import Process
from geopy.geocoders import Nominatim



from lib.resolutions import all_resolutions, find_resolution
from recal import get_catalog_stars, get_star_points, get_xy_for_ra_dec, minimize_fov, get_image_stars_with_catalog, do_photo, make_intro, save_movie_frame
from lib.PipeAutoCal import update_center_radec
from lib.Map import make_map,geo_intersec_point 
from lib.PipeEvent import get_trim_num
from lib.PipeTrans import fade , slide_left, hold
from lib.PipeDetect import get_contours_in_image, find_object, analyze_object
from lib.kmlcolors import *
from lib.PipeImage import stack_frames
from solveWMPL import convert_dy_obs, WMPL_solve, make_event_json, event_report
from lib.PipeUtil import load_json_file, save_json_file, get_trim_num, convert_filename_to_date_cam, starttime_from_file, dist_between_two_points, get_file_info, calc_dist, check_running, mfd_roi, bound_cnt, focus_area, get_template
from lib.intersecting_planes import intersecting_planes
from DynaDB import search_events, insert_meteor_event, delete_event, get_obs, update_dyna_table, delete_obs

import cv2
from lib.PipeVideo import load_frames_simple
from Classes.RenderFrames import RenderFrames 
from Classes.VideoEffects import VideoEffects

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(CustomEncoder, self).default(obj)

class AllSkyNetwork():
   def __init__(self):
      print(colored("Initializing AllSkyNetwork...", 'green'))
      self.dbdir = "/mnt/f/EVENTS/DBS/"
      print("   Load Render Frames")
      self.RF = RenderFrames()
      self.solving_node = "AWSB1"
      self.plane_pairs = {}
      self.errors = []
      self.custom_points = {}
      self.deleted_points = {}
      self.did_set_dates = None
      self.json_conf = load_json_file("../conf/as6.json")
      self.win_x = 1920
      self.win_y = 1080
      self.ignore = []
      self.planes = None

      if os.path.exists("admin_conf.json") is True:
         self.admin_conf = load_json_file("admin_conf.json")
         self.data_dir = self.admin_conf['data_dir']
      else:
         self.data_dir = "/mnt/f/"
      print("   Check start AI") 
      self.check_start_ai_server()
 

      print("   Load geolocator")
      self.geolocator = Nominatim(user_agent="geoapiExercises")

      self.good_obs_json = None
      self.user =  os.environ.get("USERNAME")
      if self.user is None:
         self.user =  os.environ.get("USER")
      self.platform = platform.system()

      self.home_dir = "/home/" + self.user + "/" 
      self.amscams_dir = self.home_dir + "amscams/"

      self.local_event_dir = self.data_dir + "EVENTS/"
      self.db_dir = self.local_event_dir + "DBS/"
      if os.path.exists(self.db_dir) is False:
         os.makedirs(self.db_dir)
      
      self.cloud_dir = "/mnt/archive.allsky.tv/"
      self.cloud_event_dir = "/mnt/archive.allsky.tv/EVENTS/"
      self.s3_event_dir = "/mnt/allsky-s3/EVENTS/"

      self.aws_r = redis.Redis("allsky-redis.d2eqrc.0001.use1.cache.amazonaws.com", port=6379, decode_responses=True)
      self.r = redis.Redis("localhost", port=6379, decode_responses=True)
      self.API_URL = "https://kyvegys798.execute-api.us-east-1.amazonaws.com/api/allskyapi"
      self.dynamodb = boto3.resource('dynamodb')

      # wasabi
      wasabi_file = "../conf/wasabi.txt"
      if os.path.exists(wasabi_file):
        with open(wasabi_file, 'r') as f:
            content = f.read()
            content = content.replace("\n","")
        wkey,wsec = content.split(":")
      #print(wkey)
      #print(wsec)
      self.s3wasabi = s3fs.S3FileSystem(
         key=wkey,
         secret=wsec,
         client_kwargs={'endpoint_url': 'http://s3.wasabisys.com'}
      )
      #s3 = s3fs.S3FileSystem(cache_timeout=3600)
      #wfiles = self.s3wasabi.ls('archive.allsky.tv/')
      #print("WFILES:", wfiles)
      #exit()
      print("   Load reconcile stations")
      self.load_reconcile_stations()
      self.help()
      print(colored("AllSkyNetwork Initializing Complete.", 'green'))


   def make_event_preview_images(self, date):
      # for each event, pic the best obs (longest or highest intensity)
      # make an roi crop of the meteor from that obs
      # save it in the event dir as event_id.jpg
      # copy to archive.allsky.tv event dir
      self.set_dates(date)
      ae = load_json_file(self.all_events_file)
      for row in ae:
         eid = row['event_id']
         obs = []
         ev_dir = self.local_evdir + eid + "/"
         cloud_ev_dir = self.cloud_evdir + eid + "/"
         ev_file = ev_dir + eid + ".jpg"
         cloud_ev_file = ev_dir + eid + ".jpg"
         for i in range(0, len(row['stations'])):
            obs_id = row['stations'][i] + "_" + row['files'][i].replace(".mp4", "")
            dur = len(row['start_datetime'][i])
            cloud_url, prev_file = self.obs_id_to_img_url(obs_id)

            obs.append((obs_id, cloud_url, prev_file, dur))
         obs = sorted(obs, key=lambda x: x[3], reverse=True)
         prev_file = obs[0][2]
         cloud_url = obs[0][1]

         

         if os.path.exists(ev_file) is False:
            # first see if the ROI file already exists
            
            cmd = "wget " + cloud_url + " -O " + ev_file
            print(cmd)
            os.system(cmd)

         print("TRYING:", ev_file)
         try:
            img = cv2.imread(ev_file)
            cv2.imshow('pepe', img)
            cv2.waitKey(0)
         except:
            print(eid, obs[0][2]) 
            print("FAILED TO GET :" + ev_file)

   def station_report(self, date):
      all_stations = load_json_file("host_response.json")
      self.set_dates(date)
      ae = load_json_file(self.all_events_file)
      print(len(ae))
      print("SSS")
      exit()
      for row in ae:
         print(row)
      for station_id in all_stations:
         d = all_stations[station_id]
         if d['op_status'] == "ACTIVE":
            print (station_id, d['op_status'], d['operator_name'], d['resp'] )

   def station_cal(self):
      #https://archive.allsky.tv/AMS1/CAL/plots/AMS1_010001_CAL_PLOTS.png
      # for each station, for each cam check the cal_plot exist and add to html
      timestamp = datetime.datetime.timestamp(datetime.datetime.now())
      html = "<h1>Station Calibrations</h1>"
      self.load_stations_file()
      print("Building calibrations...")
      for data in self.stations:
         print(data['station_id'])
         keys = list(data.keys())
         if "operator_name" in data:
            op_name = data['operator_name']
         else:
            op_name = "unknown"
         if "op_status" in data:
            op_status = data['op_status']
         else:
            op_status = "unknown"
         if op_status != "ACTIVE":
            continue
         if "cameras" in data:
            html += ("<h2>{:s}</h2>".format(data['station_id']))
            for cam_data in data['cameras']:
               if "cam_id" in cam_data:
                  # format 1 - preferred 
                  cams_id = cam_data['cam_id']
                  print("\t", cams_id)
               elif len(str(cam_data)) == 1:
                  cams_id =  data['cameras'][cam_data]
                  print("\t", cams_id)
               #else:
                  # format 2 - OLD / BAD 
                  #print("\tNo camera id data")
                  #print("DATA CAMERAS:", data['cameras'])
               cal_uri = "/{:s}/CAL/plots/{:s}_{:s}_CAL_PLOTS.jpg".format(data['station_id'], data['station_id'], cams_id)
               cal_url = "https://archive.allsky.tv" + cal_uri
               cal_file = "/mnt/archive.allsky.tv" + cal_uri
               if os.path.exists(cal_file) is True:
                  print(data['station_id'], op_name, cal_file, cal_url)
                  html += "<img src={:s}?{:s}><br>\n".format(cal_url, str(timestamp))
               else:
                  print(data['station_id'], cams_id, op_name, "NO CHART!")


         #else:
         #   print("\tNo cameras")
      fp = open("/mnt/ams2/station_cal.html", "w")
      fp.write(html)
      fp.close()

   def station_list(self, rcmd=None):
      print("RCMD is:", rcmd)
      all_stations = {}
      eu_missing = {}
      stations = load_json_file("/mnt/f/EVENTS/ALL_STATIONS.json")
      nolo = load_json_file("hosts-nologin.json")
      nologin = nolo['nologin']
      eu_stations = load_json_file("stations.json")
      print("ALL STATIONS (AWS DYNAMODB)")
      for data in stations:
         print("   ALL", data['station_id'], data['op_status'])
         st = data['station_id']
         all_stations[st] = data

      print("EU STATIONS (allsky7.net/stations.json)")
      for data in eu_stations['stations']:
         st = data['name']
         host = data['url'].replace("https://", "")
         print("   EU", st, host)
         if st not in all_stations:
            print("EU STATION NOT IN ALL STATIONS:", st, host)
            eu_missing[st] = data
            all_stations[st] = {}
            all_stations[st]['op_status'] = "NEW"
            all_stations[st]['vpn_ip'] = ""
         else:
            all_stations[st]['hostname'] = host
            if "vpn_ip" not in all_stations:
               all_stations[st]['vpn_ip'] = ""

      # load private network data 
      info_file = "/mnt/archive.allsky.tv/AMS1/info.txt"
      os.system("cp " + info_file + " ./info.txt")
      fp = open("info.txt")
      print("VPN STATIONS (private network)")
      for line in fp:
         line = line.replace("\n", "")
         if "10.8.0" in line and "vip" not in line:
            data = line.split(" ")[0]
            sid,ip = data.split(",")
            sid = "AMS" + str(sid)
            if sid in all_stations:
               all_stations[sid]['vpn_ip'] = ip
               if "hostname" not in all_stations[sid]:
                  all_stations[sid]['hostname'] = ""
               print(sid, ip)
            else:
               print("VPN Host missing from all stations!", sid, ip)
      fp.close()
      print("\nSPECIAL STATIONS (IP overrides)")
      fp = open("hosts.txt")
      for line in fp:
         line = line.replace("\n", "")
         if True:
            sid,ip = line.split(",")
            if sid in all_stations:
               all_stations[sid]['vpn_ip'] = ip
               if "hostname" not in all_stations[sid]:
                  all_stations[sid]['hostname'] = ""
               print(sid, ip)
            else:
               print("Special Host missing from all stations!", sid, ip)

      responses = {}
      for station_id in all_stations:
         if station_id in nologin:
            print("SKIP NO LOGIN:", station_id)
            continue
         if station_id == "AMS1":
            continue
         d = all_stations[station_id]
         if "vpn_ip" in d:
            vpn = d['vpn_ip']
         else:
            vpn = ""
         if "hostname" in d:
            hostname = d['hostname']
         else:
            hostname = ""

         print(station_id, d['op_status'], hostname, vpn) 

         #rcmd = "wget https://archive.allsky.tv/AMS123/gitpull.py -O /home/ams/gitpull.py ; /usr/bin/python3 /home/ams/gitpull.py"
         #rcmd = "uptime"
         # RUN REMOTE COMMAND
         #rcmd = "cd /home/ams/amscams/pipeline; git pull"

         if rcmd is not None:
            if vpn != "" :
               cmd = "ssh -o ConnectTimeout=10 " + vpn + " \"" + rcmd + "\""
               print("   VPN", cmd)
               if ":" not in vpn:
                  try:
                     print("RUN:", cmd)
                     output = subprocess.check_output(cmd, shell=True).decode("utf-8")
                     print("CMD OUTPUT:", output)
                  except:
                     output = "NOLOGIN"
               else:
                  output = vpn.split(":")[-1]
            elif hostname != "":
               cmd = "ssh -o ConnectTimeout=10 " + hostname + " \"" + rcmd + "\""
               print("   HOST", cmd)
               try:
                  print("RUN:", cmd)
                  output = subprocess.check_output(cmd, shell=True).decode("utf-8")
                  print("CMD OUTPUT:", output)
               except:
                  output = "NOLOGIN"
            else:
               print("   ", station_id, "OFFLINE")
               output = None

            if output is not None:
               print("RESP:",  station_id, output)
            if station_id not in responses:
               responses[station_id] = {}

         responses[station_id]['resp'] = output
         responses[station_id]['last_run'] = time.time()
         responses[station_id]['op_status'] = d['op_status']
         if "operator_name" in d:
            responses[station_id]['operator_name'] = d['operator_name']
         else:
            responses[station_id]['operator_name'] = "unknown"
         responses[station_id]['hostname'] = hostname
         responses[station_id]['vpn_ip'] = vpn
      save_json_file("hosts.json", responses)
      print("Saved host_response.json")

   def ignore_add_item(self, event_id, ignore_string):
      # convert id to date
      event_day = self.event_id_to_date(event_id)
      self.event_id = event_id
      self.set_dates(event_day)

      # MEDIA -- get media files from remote stations or wasabi
      local_event_dir = "/mnt/f/EVENTS/" + self.year + "/" + self.month + "/" + self.dom + "/" + self.event_id + "/"
      ignore_file = local_event_dir + event_id + "_IGNORE.json"
      if os.path.exists(ignore_file):
         ig = load_json_file(ignore_file)
      else:
         ig = []
      ig.append(ignore_string)
      save_json_file(ignore_file, ig)
      print(ignore_file)


   def admin_event_links(self, event_id):

      import webbrowser

      # list for event edit links
      self.event_id = event_id
      self.sync_log = {}
      stack_imgs = []
      hosts = load_json_file("hosts.json")
      fp = open("extra_hosts.txt")
      for line in fp:
         line = line.replace("\n", "")
         sid,surl = line.split(",")
         hosts[sid] = {}
         hosts[sid]['hostname'] = surl
         hosts[sid]['vpn_ip'] = ""

      # convert id to date
      event_day = self.event_id_to_date(event_id)
      self.set_dates(event_day)
      # MEDIA -- get media files from remote stations or wasabi
      local_event_dir = "/mnt/f/EVENTS/" + self.year + "/" + self.month + "/" + self.dom + "/" + self.event_id + "/"
      event_file = local_event_dir + event_id + "_OBS_DATA.json"
      good_obs_file = local_event_dir + event_id + "_GOOD_OBS.json"

      if os.path.exists(event_file) is True:
         evd = load_json_file(event_file)
      elif os.path.exists(good_obs_file) is True:
         evd = []
         good_obs = load_json_file(good_obs_file)
         for st in good_obs:
            for vf in good_obs[st]:
               oid = st + "_" + vf.replace(".mp4", "")
               evd.append(oid)

      else:
         print("NO OBS FILES FOUND!", event_file, good_obs_file)
      c = 0
      list_html = "<h1>" + event_id + "</h1>"
      for obs_id in sorted(evd):
         link = "none" 
         station_id = obs_id.split("_")[0]
         vid_file = obs_id.replace(station_id + "_", "")
         if station_id in hosts:
            host = hosts[station_id]['hostname'] 
            vpn_ip = hosts[station_id]['vpn_ip'] 
            #print(station_id, host, vpn_ip, obs_id)
            if host != "":
               if "http" not in host:
                  link = "https://" + host + "/meteor/" + station_id + "/" + vid_file[0:10] + "/" + vid_file + ".mp4/"
               else:
                  link = host + "/meteor/" + station_id + "/" + vid_file[0:10] + "/" + vid_file + ".mp4/"
            elif vpn_ip != "":
               link = "http://" + vpn_ip + "/meteor/" + station_id + "/" + vid_file[0:10] + "/" + vid_file + ".mp4/"
         else:
            #print(station_id, "NOT IN HOSTS")
            link = station_id + " - No active host : /meteor/" + station_id + "/" + vid_file[0:10] + "/" + vid_file + ".mp4/" 
         print(link)
         list_html += "<li>{:s} <a href={:s}>{:s}</a>\n".format(station_id, link, link)
         if c == 0:
            #webbrowser.open(link) # To open new window
            #print("OPEN NEW", link)
            webbrowser.open_new_tab(link) # To open new window
         else:
            webbrowser.open_new_tab(link) # To open new window
            #print("TAB ", link)
         c+= 1
      fp = open("/mnt/f/temp.html", "w")
      fp.write(list_html)
      fp.close()
      webbrowser.open("F:/temp.html") # To open new window
      #print(list_html)

   def filter_bad_detects(self, date):

      nav_header = self.make_page_header(date)
      template = ""
      tt = open("./FlaskTemplates/allsky-template-v2.html")
      for line in tt:
         template += line

      template = template.replace("{TITLE}", "ALLSKY7 ALL TIME EVENTS " )
      template = template.replace("AllSkyCams.com", "AllSky.com")

      stats_by_station = {}
      stats_by_min = {}
      stats_by_hour = {}
      self.set_dates(date)
      self.all_obs_file = self.local_evdir + self.date + "_ALL_OBS.json"
      data = load_json_file(self.all_obs_file)
      total = len(data)
      prob_stations = {}
      for row in data:
         #print(row['station_id'], row['sd_video_file'][11:16], row.keys())
         st = row['station_id']
         vid = row['sd_video_file']
         (f_datetime, cam_id, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(vid)
         st = st + "_" + cam_id
         if st not in stats_by_station:
            stats_by_station[st] = 0
         else:
            stats_by_station[st] += 1
         if True:
            if st not in stats_by_min:
               stats_by_min[st] = {}
            if st not in stats_by_hour:
               stats_by_hour[st] = {}
            hour = row['sd_video_file'][11:13]
            minute = row['sd_video_file'][11:16]
            if minute not in stats_by_min[st]:
               stats_by_min[st][minute] = 1
            else:
               stats_by_min[st][minute] += 1
            if hour not in stats_by_hour[st]:
               stats_by_hour[st][hour] = 1
            else:
               stats_by_hour[st][hour] += 1


      avg = int(total / len(stats_by_station.keys()  ))
      print("Stats By Station")
      for st in stats_by_station:
         if stats_by_station[st] > avg * 3:
            # detects too high
            print("*", st, stats_by_station[st])
            prob_stations[st] = {}
            prob_stations[st]['warnings'] = []
            prob_stations[st]['warnings'].append("Detects too high") 
         else:
            print(st, stats_by_station[st])


      min_avg = []
      hour_avg = []
      for st in stats_by_min:
         for minute in stats_by_min[st]:
             min_avg.append(stats_by_min[st][minute])
      for st in stats_by_hour:
         for hour in stats_by_hour[st]:
             hour_avg.append(stats_by_hour[st][hour])
      # scan problem stations by minute

      mavg = int(np.mean(min_avg))
      havg = int(np.mean(hour_avg))

      bad_minutes = {}
      bad_hours = {}

      print("Stats By Minute")
      for st in stats_by_min:
         if st not in bad_minutes:
            bad_minutes[st] = {}
         for minute in stats_by_min[st]:
            if stats_by_min[st][minute] > mavg * 2:
               print("EXCEEDS MIN AVG", st, minute, mavg, stats_by_min[st][minute])
               bad_minutes[st][minute] = [mavg, stats_by_min[st][minute]]

      print("Stats By Hour")
      for st in stats_by_hour:
         if st not in bad_hours:
            bad_hours[st] = {}
         for hour in stats_by_hour[st]:
            if  stats_by_hour[st][hour] > havg * 2:
               print("EXCEEDS HOUR AVG ", st, hour, havg, stats_by_hour[st][hour])
               bad_hours[st] = [mavg, stats_by_hour[st][hour]]
         

      bad_detects = []
      print("Bad Minutes")
      for row in data:
         minute = row['sd_video_file'][11:16]
         hour = row['sd_video_file'][11:13]
         station_id, cam_id = st.split("_")
         obs_id = station_id + "_" + row['sd_video_file'].replace(".mp4", "")
         st = row['station_id']
         vid = row['sd_video_file']
         (f_datetime, cam_id, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(vid)
         st = st + "_" + cam_id
         if st in bad_minutes:
            print("ST ROW", st, hour, minute)
            if minute in bad_minutes[st]:
               bad_detects.append(obs_id)
         elif st in stats_by_hour:
            if hour in bad_hours[st]:
               bad_detects.append(obs_id)
      bc = 0
      bd_file = self.local_evdir  + date + "_BAD_DETECTS.html"
      bd_js_file = self.local_evdir  + date + "_BAD_DETECTS.json"
      html = ""
      html += "<div style='width: 100%'>"
      last_st = None
      print("Bad Detects")
      for row in sorted(bad_detects):
         st_id = row.split("_")[0]
         vid = row.replace(st_id + "_", "")
         (f_datetime, cam_id, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(vid)

         print(bc, "BAD DETECT", row)

         html += self.meteor_cell_html(row, f_date_str)
         #html += self.obs_id_to_img_html(row)
         bc += 1 

      html += "</div>"
      save_json_file(bd_js_file, bad_detects)

      template = template.replace("{MAIN_CONTENT}", nav_header + html)

      fpo = open(bd_file, "w" )
      fpo.write(template)
      fpo.close()
      print(bd_file)
      

   def load_reconcile_stations(self):
      rec = False 
      if rec is True:
         geolocator = Nominatim(user_agent="geoapiExercises")
         API_URL = "https://kyvegys798.execute-api.us-east-1.amazonaws.com/api/allskyapi?cmd=get_stations&api_key=" + self.json_conf['api_key'] + "&station_id=" + self.json_conf['site']['ams_id']

         response = requests.get(API_URL)
         content = response.content.decode()
         content = content.replace("\\", "")
         if content[0] == "\"":
            content = content[1:]
            content = content[0:-1]
         jdata = json.loads(content)
         save_json_file("/mnt/f/EVENTS/ALL_STATIONS.json", jdata['all_vals'], True)

      dyna_station_data = load_json_file("/mnt/f/EVENTS/ALL_STATIONS.json")
      self.dyna_stations = {}
      name = None
      city = None
      state = None
      country = None
      for row in dyna_station_data:
         if "operator_name" in row:
            name = row['operator_name']
         else:
            row['operator_name'] = ""
         if "city" in row:
            city = row['city']
         else:
            row['city'] = ""
         if "state" in row:
            state = row['state']
         else:
            row['state'] = ""
         if "country" in row:
            country = row['country']
         else:
            row['country'] = ""
         self.dyna_stations[row['station_id']] = row

      sz, td = get_file_info("stations.json")
      if td / 60 / 24 > 1:
         print("    Refresh the stations file:", td/60/24)
         os.system("wget -q https://allsky7.net/stations/stations.json -O stations.json")
      self.station_data = load_json_file("stations.json")
      self.rurls = {}
      # load vpn hosts into rurls
      fp = open("vpn.txt")
      for line in fp:
         line = line.replace("\n", "")
         el = line.split(" ")
         host,ip = el[0].split(",")
         self.rurls["AMS" + host] = ip

      # update stations if the country code is not right

      for data in self.station_data['stations']:
         station = data['name']
         url = data['url']
         operator = data['operator']
         location = data['location']
         country = data['country']
         if country == "US-IA":
            country = "US"
         self.rurls[station] = url

         # make sure country is ok
         if station in self.dyna_stations and rec is True:

            if country != self.dyna_stations[station]['country']:
               print("AS7EU-DYNA COUNTRY MIS-MATCH:", station, country, "!=", self.dyna_stations[station]['country'], self.dyna_stations[station]['lat'], self.dyna_stations[station]['lon'])
               keys = {}
               keys['station_id'] = station
               update_vals = {}
               update_vals['country'] = country 
               update_dyna_table(self.dynamodb, "station", keys, update_vals)
         elif station not in self.dyna_stations :
            print("NOT IN DYNA:", station)

      for station_id in self.dyna_stations:
         row = self.dyna_stations[station_id] 
         if "location" not in self.dyna_stations and rec is True:
            Latitude = row['lat']
            Longitude = row['lon']
            station_id = row['station_id']
            if "geoloc" not in row:
               try:
                  location = geolocator.reverse(Latitude+","+Longitude)
                  time.sleep(.5)
                  keys = {}
                  keys['station_id'] = station_id
                  update_vals = {}
                  if location is not None:
                     update_vals['geoloc'] = location.raw['address'] 
                     update_dyna_table(self.dynamodb, "station", keys, update_vals)
                     print("UPDATE:", station_id, location.raw['address'])
               except:
                  print(station_id, "URL FAIL")
            else:
               if "geoloc" in row: 
                     
                  if "country_code" in row['geoloc']:
                     if row['geoloc']['country_code'].upper() == "GB":
                        row['geoloc']['country_code'] = "UK"

                     if row['geoloc']['country_code'].upper() == "US-AI":
                        row['geoloc']['country_code'] = "US"

                     if row['geoloc']['country_code'].upper() != row['country']:
                        print("MIS MATCH COUNTRY:", station_id, row['geoloc']['country_code'].upper(), row['country'] )
                        keys = {}
                        keys['station_id'] = station_id
                        update_vals = {}
                        update_vals['country'] =  row['geoloc']['country_code'].upper()
                        if update_vals['country'] == "US-IA":
                           update_vals['country'] == "US"
                           
                        update_dyna_table(self.dynamodb, "station", keys, update_vals)
                  else:
                     print("country code not in geoloc")

      self.station_loc = {}
      for st_id in self.dyna_stations:
         row = self.dyna_stations[st_id]
         lat = row['lat'] 
         lon = row['lon'] 
         alt = row['alt']
         self.station_loc[st_id] = [lat,lon,alt]
         

   def rerun_month (self, year_month):
      year, month = year_month.split("_")
      today = (datetime.datetime.now() - datetime.timedelta(days = 1)).strftime("%Y_%m_%d")
      current_year, current_month, current_day = today.split("_")
      year = int(year)
      month = int(month)
      all_days = []
      if month == int(current_month):
         end_days = int(current_day)
      else:

         end_days = int(monthrange(int(current_year), month)[1])
      for day in range(1,end_days + 2) :
         if month < 10:
            smon = "0" + str(month)
         else:
            smon = str(month)
         if day < 10:
            sday = "0" + str(day)
         else:
            sday = str(day)
         all_days.append((current_year + "_" +  smon + "_" + sday))
      for day in sorted(all_days,reverse=False):
         y,m,d = day.split("_")
         rmcmd = "rm /mnt/f/EVENTS/" + y + "/" + m + "/" + d + "/" + "*OBS*"
         print(rmcmd)
         runcmd = "./AllSkyNetwork.py do_all " + day
         print(runcmd)
   

   def quick_report(self, date):
     
      stats = {}
      if os.path.exists(self.local_evdir + date + "_BAD_DETECTS.json"):
         self.bad_detects = load_json_file(self.local_evdir + date + "_BAD_DETECTS.json")
      else:
         self.bad_detects = {}
      self.all_events_data = load_json_file(self.all_events_file)
      self.all_obs = load_json_file(self.all_obs_file)

      # get event ids from local db
      db_events = {}
      sql = """
         SELECT event_id,stations from events order by event_id 
      """
      self.cur.execute(sql)
      rows = self.cur.fetchall()
      for row in rows:
         event_id = row[0]
         db_events[event_id] = {}


      # obs by station
      for ob in self.obs_dict:
         st_id = self.obs_dict[ob]['station_id']
         if st_id not in stats:
            stats[st_id] = 1
         else:
            stats[st_id] += 1
      c = 1 
      temp = []

      # obs by station
      for st in stats:
         sti = int(st.replace("AMS", ""))
         temp.append((sti,stats[st]))

      for row in sorted(temp, key=lambda x: x[0], reverse=False):
         ams_id = "AMS{0:03d}".format(row[0])
         c += 1

      self.event_dict = {}
      for row in self.all_events_data:
         ev_id = row['event_id']
         self.event_dict[ev_id] = row

      files = os.listdir(self.local_evdir)
      for f in files:
         if os.path.isdir(self.local_evdir + f) :
            if f in self.event_dict and f in db_events:
               print("EVENT DIR EXISTS IN AWS DICT AND LOCAL DB", f)
            elif f in self.event_dict and f not in db_events:
               print("EVENT DIR EXISTS IN AWS DICT BUT NOT LOCAL DB", f)
            elif f not in self.event_dict and f in db_events:
               print("EVENT NOT IN AWS DICT BUT IS IN LOCAL DB", f)
               # pending / resolve it?
               cmd = "./AllSkyNetwork.py resolve_event " + f
               print(cmd)
               os.system(cmd)


            else:
               print("EVENT DIR NOT IN AWS DICT OR LOCAL DB (DELETE IT!)", self.local_evdir + f)
      

   def rsync_data_only(self, date):
      #self.set_dates(date)
      # this sync method is meant for remote workers
      # the worker will only transmit to the cloud the .pickle file for each event 
      # and any summary json or html files for the root. 
      # once transmitted a remote URL will be hit to trigger an unzip process and upload to the S3FS from the AWS server

      # make / clean up the temp upload dir 
      temp_dir = self.data_dir + "EVENTS/TEMP/"
      if os.path.exists(temp_dir) is False:
         os.makedirs(temp_dir)
      else:
         tfiles = os.listdir(temp_dir)
         for tf in tfiles:
            os.remove(temp_dir + tf)

      local_ev_dirs = os.listdir(self.local_evdir)


      for evd in local_ev_dirs:
         if "dbfiles" in evd:
            continue
         if os.path.isdir(self.local_evdir + evd) is True:
            evid = evd
            pickle_file = self.local_evdir + evd + "/" + evd + "_trajectory.pickle"
            temp_file = temp_dir + evd + "_trajectory.pickle"

            temp_obs_file = temp_dir + evd + "_GOOD_OBS.json"
            temp_fail_file = temp_dir + evd + "-fail.json"
            temp_event_file = temp_dir + evd + "-event.json"
            temp_map_file = temp_dir + evd + "_map.kml"

            good_obs_file = self.local_evdir + evd + "/" + evd + "_GOOD_OBS.json"
            fail_file = self.local_evdir + evd + "/" + evd + "-fail.json"
            event_file = self.local_evdir + evd + "/" + evd + "-event.json"
            map_file = self.local_evdir + evd + "/" + evd + "_map.kml"

            if os.path.exists(pickle_file) is True and os.path.exists(temp_file) is False:
               print(pickle_file, temp_file)
               shutil.copyfile(pickle_file, temp_file)
            if os.path.exists(good_obs_file) is True and os.path.exists(temp_obs_file) is False:
               shutil.copyfile(good_obs_file, temp_obs_file)
               print(good_obs_file, temp_obs_file)
            if os.path.exists(fail_file) is True and os.path.exists(temp_fail_file) is False:
               shutil.copyfile(fail_file, temp_fail_file)
               print(fail_file, temp_fail_file)
            if os.path.exists(event_file) is True and os.path.exists(temp_event_file) is False:
               print(event_file, temp_event_file)
               shutil.copyfile(event_file, temp_event_file)
            if os.path.exists(map_file) is True and os.path.exists(temp_map_file) is False:
               print(map_file, temp_map_file)
               shutil.copyfile(map_file, temp_map_file)

      if os.path.exists( temp_dir + date + "_dbfiles.tar") :
         os.remove( temp_dir + date + "_dbfiles.tar")
      if os.path.exists( temp_dir + date + "_dbfiles.tar.gz") :
         os.remove( temp_dir + date + "_dbfiles.tar.gz")

      cmd = "cd " + temp_dir +"; tar -cvf " + self.local_evdir + date + "_dbfiles.tar" + " "  + "*"
      os.system(cmd)

      #cmd = "gzip -f " + self.local_evdir + date + "_dbfiles.tar" 
      cmd = "7z a " + self.local_evdir + date + "_dbfiles.tar.7z " + self.local_evdir + date + "_dbfiles.tar"
      os.system(cmd)
      
      cmd = "cp " + self.local_evdir + date + "_dbfiles.tar.7z " + self.cloud_evdir + date + "_dbfiles.tar.7z "
      os.system(cmd)

      #cmd = "cp " + self.local_evdir + date + "_MIN_EVENTS.json " + self.cloud_evdir + date + "_MIN_EVENTS.json"
      #os.system(cmd)

      #cmd = "cp " + self.local_evdir + date + "_plane_pairs.json " + self.cloud_evdir + date + "_PLANE_PAIRS.json"
      #os.system(cmd)

      cmd = "rsync -auv --exclude '*OBS_DICT*' --exclude '*ALL_OBS*' " + self.local_evdir + "*.json " + self.cloud_evdir 
      print(cmd)
      os.system(cmd)

      cmd = "rsync -auv " + self.local_evdir + "*.info " + self.cloud_evdir 
      print(cmd)
      os.system(cmd)

      cmd = "rsync -auv " + self.local_evdir + "*.kml " + self.cloud_evdir 
      print(cmd)
      os.system(cmd)

      cmd = "rsync -auv " + self.local_evdir + "*.html " + self.cloud_evdir 
      print(cmd)
      os.system(cmd)

         

   def sync_dyna_day(self, date):
      #insert_meteor_event(dynamodb=None, event_id=None, event_data=None)
      print("SYNC DYNA DAY")
      events = search_events(self.dynamodb, date, None)
      print("DYNA EVENTS:", len(events))
      event_dict = {}
      for ev in events:
         event_id = ev['event_id']
         event_dict[event_id] = ev
      self.local_event_dir = self.data_dir + "EVENTS/"

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
      url = "https://archive.allsky.tv/EVENTS/ALL_STATIONS.json"
      local_file = self.local_event_dir + "/ALL_STATIONS.json"
      local_loc_file = self.local_event_dir + "station_locations.json"
      #print("LC:", local_loc_file)
      if os.path.exists(local_loc_file) is True:
         loc_info = load_json_file(local_loc_file)
      else:
         loc_info = None

      if os.path.exists(local_file) :
         sz, td = get_file_info(local_file)
         td = td / 60 /24 
      else:
         td = 999

      print("stations file syncd", td, "days ago")

      if td < 1:
         try:
            response = requests.get(url)
            content = json.loads(response.content.decode())
            save_json_file(self.local_event_dir + "/ALL_STATIONS.json", content)
         except:
            print("FAILED " + url)

      print(self.local_event_dir + "/ALL_STATIONS.json")
      self.stations = load_json_file(self.local_event_dir + "/ALL_STATIONS.json")
      self.station_dict = {}
      self.photo_credits = {}
      sc = 1
      for data in self.stations:
         sid = data['station_id']
         self.station_dict[sid] = data
         if "city" in data:
            city = data['city']
         else:
            city = "" 
         if "state" in data:
            state  = data['state']
         else:
            state = "" 

         if "country" in data:
            country = data['country']
         else:
            country = "" 

         if loc_info is not None:
            if sid in loc_info:
               if 'country_code' in loc_info[sid]:
                  lcountry = loc_info[sid]['country_code']
               else:
                  lcountry = None
            else:
               lcountry = None
            if lcountry is not None:
               if country != lcountry.upper():
                  country = lcountry.upper()
         else:
            print("LOC NONE")
         data['country'] = country
         if "operator_name" in data:
            operator_name = data['operator_name']
         else:
            operator_name = "" 
         if "inst_name" in data:
            inst_name = data['inst_name']
         else:
            inst_name = None
         if "obs_name" in data:
            obs_name = data['obs_name']
         else:
            obs_name = "" 
         if "photo_credit" in data:
            photo_credit = data['photo_credit']
         else:
            photo_credit = None

         #utf-8 UTF-8 name hacks
         operator_name = operator_name.replace("Ju00f6rg", "Jorg")
       
         if operator_name == "" or operator_name == " " :
            self.photo_credits[sid] = sid + " unknown"
         elif operator_name != "" and city != "" and state != "" and ("United States" in country or "US" in country):
            self.photo_credits[sid] = operator_name + " " + city + "," + state + " " +  country
         elif operator_name != "":
            self.photo_credits[sid] = operator_name + " " + city + "," + country
         else:
            self.photo_credits[sid] = sid
         #print(sc, self.photo_credits[sid])
         sc += 1

   #def day_prep(self, date):
   #   print("ok")

   def set_dates(self, date, refresh=True):
      if self.did_set_dates is True:
         return()
      self.year, self.month, self.day = date.split("_")
      self.dom = self.day
      self.date = date
      self.local_evdir = self.local_event_dir + self.year + "/" + self.month + "/" + self.day  + "/"
      self.cloud_evdir = self.cloud_event_dir + self.year + "/" + self.month + "/" + self.day   + "/"
      self.s3_evdir = self.s3_event_dir + "/" + self.year + "/" + self.month + "/" + self.day   + "/"
      self.obs_dict_file = self.local_evdir + self.date + "_OBS_DICT.json"


      self.did_set_dates = True
      self.all_obs_file = self.local_evdir + self.date + "_ALL_OBS.json"
      self.sync_log_file = self.local_evdir + date + "_SYNC_LOG.json"
      self.min_events_file = self.local_evdir + date + "_MIN_EVENTS.json"
      self.all_events_file = self.local_evdir + date + "_ALL_EVENTS.json"
      self.station_events_file = self.local_evdir + date + "_STATION_EVENTS.json"

      sz, age = get_file_info(self.all_obs_file)
      days_old = age/60/24
      if days_old > 1 and refresh is True:
         # input-select here
         print("Press enter to redownload the obs data file for this day, else we will use the cached file")
         i, o, e = select.select( [sys.stdin], [], [], 2 )
         if (i) :
            confirm = sys.stdin.readline().strip()

            if os.path.exists(self.all_obs_file):
               os.system("rm " + self.all_obs_file)
            if os.path.exists(self.obs_dict_file):
               os.system("rm " + self.obs_dict_file)


      self.all_obs_gz_file = self.local_evdir + self.date + "_ALL_OBS.json.gz"
      self.cloud_all_obs_file = self.cloud_evdir + self.date + "_ALL_OBS.json"
      self.cloud_all_obs_gz_file = self.cloud_evdir + self.date + "_ALL_OBS.json.gz"
      self.obs_review_file = self.local_evdir + date + "_OBS_REVIEWS.json"
      self.all_stations_file = self.local_event_dir + "/" + self.year + "/" + self.month + "/" + self.day + "/" + self.date + "_ALL_STATIONS.json"

      #self.all_stations_file = self.local_event_dir + "/" "ALL_STATIONS.json"
      if os.path.exists(self.all_stations_file) is True:
         self.all_stations = load_json_file(self.all_stations_file)
      else:
         self.all_stations = []
      self.station_loc = {}

      for row in self.all_stations:
         st_id , lat, lon, alt, city, network = row
         self.station_loc[st_id] = [lat,lon,alt]
      # DB FILE!
      self.db_file = self.db_dir + "/ALLSKYNETWORK_" + date + ".db"
      if os.path.exists(self.db_file) is False:
         os.system("cat ALLSKYNETWORK.sql | sqlite3 " + self.db_file)
      if os.path.exists(self.db_file) is False:
         print("DB FILE NOT FOUND.", self.db_file)
         return ()
      self.con = sqlite3.connect(self.db_file)
      self.con.row_factory = sqlite3.Row
      self.cur = self.con.cursor()

      if os.path.exists(self.local_evdir) is False:
         os.makedirs(self.local_evdir)
      if os.path.exists(self.cloud_evdir) is False:
         os.makedirs(self.cloud_evdir)

      print(self.local_evdir + "/" + self.date + "_OBS_DICT.json")

      local_size, tdd = get_file_info(self.all_obs_file + ".gz") 
      cloud_size, tdd = get_file_info(self.cloud_all_obs_file + ".gz") 

      if os.path.exists(self.cloud_all_obs_gz_file) is False and os.path.exists(self.all_obs_file) is False:
         print("Could not find:", self.all_obs_file, "or",  self.cloud_all_obs_gz_file)
         cmd = "./DynaDB.py udc " + date
         print(cmd)
         os.system(cmd)

      elif os.path.exists(self.all_obs_gz_file) is False and os.path.exists(self.cloud_all_obs_gz_file) is True: 
         shutil.copyfile(self.cloud_all_obs_gz_file, self.all_obs_gz_file)
         print("Unzipping ", self.all_obs_gz_file)
         os.system("gunzip -k -f " + self.all_obs_gz_file )
         # this will only work for ADMINS with AWS Credentials
      elif local_size < cloud_size:
         shutil.copyfile(self.cloud_all_obs_gz_file, self.all_obs_gz_file )
         print("Unzipping ", self.all_obs_gz_file )
         os.system("gunzip -k -f " + self.all_obs_gz_file )
      elif local_size >= cloud_size:
         print("Obs are in-sync", local_size, cloud_size)
         print(self.all_obs_file)
         print(self.cloud_all_obs_file)
      else:
         print("FAIL!!!", local_size, cloud_size)
         return()
         # this will only work for ADMINS with AWS Credentials
         #os.system("./DynaDB.py udc " + date)
      if os.path.exists(self.all_obs_file) is False: 
         os.system("./DynaDB.py udc " + date)

      if os.path.exists(self.obs_dict_file) is True: 
         try:
            self.obs_dict = load_json_file(self.local_evdir + "/" + self.date + "_OBS_DICT.json")
         except:
            print("CORRUPT OBS DICT?!", self.local_evdir + "/" + self.date + "_OBS_DICT.json")
            os.system("rm " + self.local_evdir + "/" + self.date + "_OBS_DICT.json")
            self.obs_dict = {}
      else:
         print("NO OBS DICT?!")
         self.obs_dict = {}

      if os.path.exists(self.obs_dict_file) is False or len(self.obs_dict.keys()) == 0:
         print("MAKE OBS DICT")
         self.make_obs_dict()
         self.obs_dict = load_json_file(self.local_evdir + "/" + self.date + "_OBS_DICT.json")
      
      # load events for day
      if os.path.exists(self.all_events_file) is True:
         self.all_events = load_json_file(self.all_events_file)
      else:
         self.all_events = []


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
            delete_event(self.dynamodb, event_day, ev_id)
         else:
            dyna_ids[ev_id] = ev

      mcc = 0
      for mc_id in mc_events:
         if mc_id not in dyna_ids:
             print(mcc, "ADD EVENT TO DYNAMO:", mc_id)
             self.dyna_insert_meteor_event(event_id, mc_events[mc_id])

             mcc += 1
      print(len(all_events_data), "existing DYNA events")

      for mc_id in mc_events:
         if mc_id not in sql_ids:
            print("MC ID NOT IN LOCAL SQL:", mc_id)
            event = mc_events[mc_id]
            self.insert_event(event)
         else:
            self.insert_event(event)

      for sql_id in sql_ids:
         if sql_id not in mc_events:
            print("SQL ID NOT IN MCE", sql_id)

      
      # check the event dirs on cloud system. remove those not in the mc_events dict 

   def review_coin_events(self,date,fix_bad=False): 
      # load minute events file and all events file
      # both of these should be in sync as should the local
      # sqlite db and the remote dynamo db! 
      # so literally 4 places for events, but dyna and allevents are the same, so 3 places: min_events, all_events, local db 
      # this function should make sure all of these things are in sync
      # the process starts with the MIN_EVENTS so that is the end-all-be-all
      # if it is not in the min events it is not a valid event and should be deleted
      # start1 = (45.0, -93.0)  # Latitude, Longitude
      # intersection = line_intersection(start1, heading1, start2, heading2)

      self.min_events_file = self.local_evdir + "/" + date + "_MIN_EVENTS.json"
      self.all_events_file = self.local_evdir + "/" + date + "_ALL_EVENTS.json"
      min_events = load_json_file(self.min_events_file)
      events = load_json_file(self.all_events_file)
      ev_dirs = {} 
      event_dict = {}
      min_dict = {}
      db_events = {}

      delete_events = {}

      # load dict for min events
      for minute in min_events:
         for eid in min_events[minute].keys():
            if "event_id" in min_events[minute][eid]:
               print(min_events[minute][eid]['event_id'], min_events[minute][eid]['start_datetime'])
               min_dict[min_events[minute][eid]['event_id']] = min_events[minute][eid]

      x = 0
      # load dict for all events (local copy of what is in dynamo)
      for event in events:
         event_id = event['event_id']
         event_dict[event_id] = event
         if event_id not in min_dict:
            x += 1
            print("DB EVENT NOT IN MIN DICT", x, event_id)
            delete_events[event_id] = True

      # load dict for all events dirs (local copy of what is in dynamo)
      ev_files = os.listdir(self.local_evdir)
      x = 0
      for ev in ev_files:
         if os.path.isdir(self.local_evdir + ev) is True and ev[0:2] == "20":
            ev_dirs[ev] = True
            if ev not in min_dict:
               x += 1
               print("EVENT DIR EVENT NOT IN MIN DICT", x, ev)
               delete_events[event_id] = True

      # load db events:

      sql = """
         SELECT event_id,event_status,run_date,run_times from events order by event_id 
      """
      self.cur.execute(sql)
      rows = self.cur.fetchall()
      for row in rows:
         event_id,event_status,run_date,run_times = row
         db_events[event_id] = {}
         db_events[event_id]['event_status'] = event_status
         db_events[event_id]['run_date'] = run_date
         db_events[event_id]['run_times'] = run_times
         if event_id not in min_dict:
            delete_events[event_id] = True

      print("TOTAL EVENT DIRS:", len(ev_dirs.keys()))
      print("TOTAL ALL EVENTS:", len(event_dict.keys()))
      print("TOTAL MIN EVENTS:", len(min_dict.keys()))
      print("NEED TO DELETE EVENTS:", len(delete_events.keys()))
      for event_id in delete_events:
         print("DELETE EVENT:", event_id)
         self.purge_event(event_id)
      x = 0
      ee = 0
      iv = 0
      for event_id in min_dict.keys():
         if event_id in event_dict:
            ind = True
            status = event_dict[event_id]['solve_status']
         else:
            ind = False 
            status = "Pending"
         if event_id in ev_dirs:
            indr = True
         else:
            indr = False 
         if indr is False or ind is False:
            print("Purge",event_id)
            self.purge_event(event_id)

         a = None
         e = None
         if event_id in event_dict:
            if "solution" in event_dict[event_id]:
               if "orb" in event_dict[event_id]['solution']:
                  a = event_dict[event_id]['solution']['orb']['a']
                  e = event_dict[event_id]['solution']['orb']['e']
            if a is None:
               print("Event is invalid: Incongruent observations -- There must be two or more intersecting observations.", event_id)
               ed = event_dict[event_id]
               md = min_dict[event_id]
               print(iv, ed['event_id'], md['start_datetime'], ed['stations'], ed['solve_status']) 
               #print(ee, event_id, status, a, event_dict[event_id].keys()) 
               iv += 1
               #os.system("./AllSkyNetwork.py resolve_event " + event_id + " x")
            elif a < -1 or e > 1:
               print("Event needs review: anomolous orbit -- The observations need review and cleanup to fix points or correct calibration.", event_id)
               ed = event_dict[event_id]
               md = min_dict[event_id]
               #print(ee, ed['event_id'], md['start_datetime'], ed['stations'], ed['solve_status']) 
               #print(ee, event_id, status, a, event_dict[event_id].keys()) 
               ee += 1
            else:
               print(x, "Event is valid:", event_id) 
               x += 1 

               #print(x, ed['event_id'], md['start_datetime'], ed['stations'], ed['solve_status']) 
      print("valid ", x)
      print("invalid ", iv)
      print("errors", ee)

   def day_coin_events(self,date,force=0):

      # load shadow Ban file
      sh_ban = "/mnt/f/shadow_ban.json"
      self.banned = load_json_file(sh_ban)

      self.get_min_obs_dict(date)


      self.plane_file = self.local_evdir + "/" + date + "_PLANE_PAIRS.json"
      self.min_events_file = self.local_evdir + "/" + date + "_MIN_EVENTS.json"
      if os.path.exists(self.plane_file) is True:
         self.plane_pairs = load_json_file(self.plane_file)
      else:
         self.plane_pairs = {}
      self.good_planes = []
      self.bad_planes = []
      self.load_stations_file()


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
         print("\rMIN COUNT:" + str(mcm) + " " + str(minute) + str(obs_count), end="")
         print("\n")
         # STOPPED HERE!
      ec = 0
      ecp = 0
      ecf = 0


      self.all_min_events = {}
      nowt = time.time()
      start = 0
      end = len(ocounts.keys())

      self.do_coin_work(ocounts, start,end)

      save_json_file(self.plane_file, self.plane_pairs)

      c = 0
      mc = 0
      for minute in self.all_min_events:
         print(colored("MINUTE:" + str(minute), "green"))
         for event_id in self.all_min_events[minute]:
            event = self.all_min_events[minute][event_id]
            if len(list(set(event['stations']))) > 1:
               #print("   ", c, "FINAL EVENTS:",  event['stations'], event['start_datetime'], event['ipoints'])
               new_event_id = self.insert_event(event)
               #print(event)
               print("ID:", event['event_id'])
               print("Start:", event['start_datetime'])
               self.all_min_events[minute][event_id]['event_id'] = new_event_id
               mc += 1


            #else:
               #print("   ", c, "SINGLE STATION EVENT:", event['stations'], event['start_datetime'])
            #score_data = self.score_obs(event['plane_pairs'])
            #for score, key in score_data[0:100]:
            #   ob1, ob2 = key.split("__")
            #   gd = ["GOOD", key, ob1, ob2, event['stime'], "", "", ""]
            #   if len(list(set(event['stations']))) > 1:
            #      self.insert_event(event)
            #   print("Skip single station events.")
            #print(c, "Good planes:", gd[2], gd[3],result[0])
            c += 1
      save_json_file(self.min_events_file, self.all_min_events)
      print("saved:", self.min_events_file)  
      print(len(self.all_min_events.keys()), "ROWS IN ALL MIN EVENTS")
      print(mc, "multi-station events found.")

   def do_coin_work(self, ocounts, start,end):
      minutes = list(ocounts.keys())
      for minute in minutes[start:end]:
         nowt = time.time() 
         print(colored("START MINUTE:" + str(minute), "blue"))
         if ocounts[minute]['count'] > 1:
            odata = self.get_station_obs_count(minute)
            elp = time.time() - nowt
            #min_obs = self.get_obs (minute)
            min_obs = self.min_obs_dict[minute]
            clean_min_obs = []
            for mo in min_obs:
                found_ban = False
                for b in self.banned:
                    if b in mo[0] :
                        print(colored("BANNED FROM MIN OBS: " + mo[0]), "red")
                        found_ban = True
                if found_ban is False:
                    clean_min_obs.append(mo)
                #if found_ban is True:
            min_events = self.min_obs_to_events(clean_min_obs)
            elp = time.time() - nowt
            self.all_min_events[minute] = min_events
         else:
            min_events = []
         elp = time.time() - nowt
         #print("EVENTS FOR MINUTE", minute, len(min_events))
         #for ev in min_events:
         #   print(ev, min_events[ev]['stations'], min_events[ev]['start_datetime'])
         print(colored("END MINUTE:" + str(minute), "blue"))
         #print("ELP:", elp)

   def insert_event(self, event):

      event_id = event['stime'].replace("-", "")
      event_id = event_id.replace(":", "")
      event_id = event_id.replace(" ", "_")
      if "." in event_id:
         event_id = event_id.split(".")[0]
      event['event_id'] = event_id

      # BUG FIX ? 15 for 10 minute 16 for 1 minute string!
      event_minute = event['stime'].replace("-", "_")[0:16]
      event_minute = event_minute.replace(":", "_")
      event_minute = event_minute.replace(" ", "_")
      event['event_day'] = event_minute[0:10] 

      print("\t\tEVENT ID:", event_id)
      print("\t\tEVENT MIN:", event_minute)
      sql = """
          SELECT event_id, event_minute, revision, stations, obs_ids, event_start_time, event_start_times,  
                 lats, lons, event_status, run_date, run_times
            FROM events 
            WHERE event_id = ?
      """

      svals = [event_id]
      self.cur.execute(sql, svals)
      print(sql, event_id)
      rows = self.cur.fetchall()
      print("EVENT", event) 
      print("ROWS", len(rows))
      if len(rows) == 0:
         print("\t\tNo events matching this event id exist!", event_id)
         # make a new event!
         sql = """
            INSERT OR REPLACE INTO events (event_id, event_minute, revision, 
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
         print("\t\tADD NEW EVENT!", event_id, len(ivals))
         self.cur.execute(sql, ivals)
         self.con.commit()
         if event_id == "20240518_224646":
            input("insert")

      else:
         #updated_existing = False
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
            self.update_event(ivals) 
            if event_id == "20240518_224646":
                input("update")

      return(event_id)

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

   def run_plane_jobs_OLDER(self, jobs,force=False):
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

      #save_json_file("min_events.json", min_events)
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
      return()
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

   # First, let's create some helper functions that we'll use later in the main function.
   
   def initialize_event(self, eid, station_id, lat, lon, alt, azs, els, ints, obs_file, stime):
      """
      Initialize a new event with the given parameters.
      """
      new_event = {
          'stations': [station_id],
          'lats': [lat],
          'lons': [lon],
          'alts': [alt],
          'files': [obs_file],
          'azs': [azs],
          'els': [els],
          'ints': [ints],
          'ipoints': [],
          'start_datetime': [stime],
          'stime': stime  # This seems to be the start time of the first observation in this event
      }
      return {eid: new_event}
   
   def check_time_match(self, stime, event_time, duration):
      """
      Check if the new observation's time is within the acceptable range of the event time.
      """
      # Your logic for dynamic time window goes here. For now, I'll assume a 10 second window as in the original code.
      if duration < 1:
         duration = 1 
      s_datestamp, s_timestamp = self.date_str_to_datetime(stime)
      t_datestamp, t_timestamp = self.date_str_to_datetime(event_time)
      time_diff = abs(s_timestamp - t_timestamp)
      if time_diff < duration * 3:
         print(colored("\tTIME DIFF < DUR:" + str(time_diff) + " < " +str( duration * 2), "green"))
      else:
         print(colored("\tTIME DIFF !< DUR:" + str(time_diff) + " !< " +str( duration * 2), "red"))
         print(s_timestamp, t_timestamp)
      return time_diff <= duration * 2 

   def check_distance_match(self, avg_lat, avg_lon, lat1, lon1, elevation):
      """
      Compute and check if the distance is within the acceptable range based on elevation.
      """
      # Your logic for dynamic distance based on elevation goes here. For now, I'll assume a 700 km limit.
      match_dist = dist_between_two_points(avg_lat, avg_lon, lat1, lon1)
      print("\tMATCH DIST:", match_dist)
      return match_dist < 600
   
   def check_azimuth_intersection(self, event, station_id, lat1, lon1, az1):
      """
      Check if the new observation's azimuth intersects with at least 50% of the existing event's azimuths.
      we should just pass in 1 new_az to check the start az is good
      """
      # Your logic for azimuth intersection goes here.
      intersects = 0
      for i in range(0,len(event['azs'])):
          st2 = event['stations'][i]
          az2 = event['azs'][i][0]
          lon2 = event['lons'][i]
          lat2 = event['lats'][i]
          print("\t", station_id, "->", st2)
          if station_id == st2:
              intersects += 1
          elif self.azimuths_intersect(lat1, lon1, az1, lat2, lon2, az2, 700):
          #if self.azimuths_intersect(az, new_az):  # Assuming azimuths_intersect() returns True or False
              intersects += 1
      print("\tAZ INTERSECT SCORE",intersects , "/", len(event['azs']))
      return (intersects / len(event['azs'])) >= 0.5
   
   # Now we can refactor the main function to make it cleaner and more modular.

   def check_make_events_new(self, min_events, station_id, obs_file, stime, duration, azs, els, ints):
      """
      Check if the new observation matches with any of the existing events.
         if it does add it to the event array
         else make a new event
      """
      print("\n*** START CHECK MAKE EVENTS FOR", obs_file)
      lat = float(self.station_dict[station_id]['lat'])
      lon = float(self.station_dict[station_id]['lon'])
      alt = float(self.station_dict[station_id]['alt'])
      #if station_id == 'AMS100' or station_id == 'AMS101':

      min_events_keys = min_events.keys()
      if len(min_events_keys) == 0:
          # Initialize the first event
          eid = 1
          print("\t\tINITIALIZE FIRST EVENT")
          min_events = self.initialize_event(eid, station_id, lat, lon, alt, azs, els, ints, obs_file, stime)
          return(min_events)
      else:
          matches = []
          for eid in min_events_keys:
              event = min_events[eid]
              event_time = event['stime']
              event_azs = event['azs']
              event_els = event['els']
              avg_lat = np.mean(event['lats'])
              avg_lon = np.mean(event['lons'])
   
              # Check time match
              if not self.check_time_match(stime, event_time, duration):
                  print("\t\tEVENT TIME CHECK FAILED TO MATCH (stime,event_time,dur)", station_id, obs_file, stime, event_time, duration)
                  continue
   
              # Check distance match
              if not self.check_distance_match(avg_lat, avg_lon, lat, lon, event_els[0]):
                  print("\t\tEVENT DISTANCE FAILED TO MATCH", station_id, obs_file)
                  continue
   
              # Check azimuth intersection
              if not self.check_azimuth_intersection(event, station_id, lat, lon, azs[0]):
                  print(colored("\t\tEVENT AZ INT FAILED TO MATCH","red"))
                  print("\t\tIgnoring AZ intersects for now ")
                  #continue
              else:
                  print("\t\tEVENT AZ INT PASSED")
              # If all checks pass, this observation matches with the existing event.
              
              matches.append(eid)
   
          # Your logic for updating min_events based on matches goes here.
          # ...
          print("\t\tMATCHES:", len(matches))  
          if len(matches) == 0:
             # No matches, so make a new event
             eid = max(min_events_keys) + 1
             print("\t\tMAKE NEW EVENT")
             new_data = self.initialize_event(eid, station_id, lat, lon, alt, azs, els, ints, obs_file, stime)
             min_events[eid] = new_data[eid]
             #return self.initialize_event(eid, station_id, lat, lon, alt, azs, els, ints, obs_file, stime)   
             return(min_events)
          else:
             # add this obs to the event
               print("\t\tADD TO EVENTS", matches)
               # if there is more than 1 match,we have to figure out which one is the better/best one. 
               # should it be closest in time or distance or both? 
               # or do we consider the az intersects
               if len(matches) > 1:
                  best_eid = None
                  close = 99999
                  for eid in matches : 
                     avg_lat = np.mean(min_events[eid]['lats'])
                     avg_lon = np.mean(min_events[eid]['lons'])
                     match_dist = dist_between_two_points(avg_lat, avg_lon, lat, lon)
                     if match_dist < close:
                        best_eid = eid
                        close = match_dist 

                     print("MMM", best_eid, eid, match_dist, min_events[eid])
                     matches = [best_eid]
               
               for eid in matches[0:1]:
                  min_events[eid]['stations'].append(station_id)
                  min_events[eid]['lats'].append(lat)
                  min_events[eid]['lons'].append(lon)
                  min_events[eid]['alts'].append(alt)
                  min_events[eid]['azs'].append(azs)
                  min_events[eid]['els'].append(els)
                  min_events[eid]['ints'].append(ints)
                  min_events[eid]['files'].append(obs_file)
                  min_events[eid]['start_datetime'].append(stime)
                  min_events[eid]['stime'] = self.average_times(min_events[eid]['start_datetime'])
                  print("\t\t", eid, min_events[eid]['stime'])
                  print("\t\t", eid, min_events[eid]['stations'])

               return(min_events) 
          print("\tEND CHECK MAKE EVENTS")
          return min_events

   # Note: The helper functions like dist_between_two_points() and azimuths_intersect() are assumed to be defined elsewhere.

   def azimuths_intersect(self, lat1, lon1, az1, lat2, lon2, az2, max_distance=700):
      """
      Check if the azimuths from two observations intersect within a maximum distance.

      Parameters:
      lat1, lon1, az1: Latitude, Longitude, and Azimuth of the first observation
      lat2, lon2, az2: Latitude, Longitude, and Azimuth of the second observation
      max_distance: The maximum distance for a 'good' intersection

      Returns:
      True if the azimuths intersect within max_distance, otherwise False
      """
      err_status, ipoint = geo_intersec_point(lat1, lon1, az1, lat2, lon2, az2)

      # Check if the intersection point exists and is within max_distance from either observer
      if not err_status:
         idist1 = dist_between_two_points(float(lat1), float(lon1), float(ipoint['x3']), float(ipoint['y3']))
         idist2 = dist_between_two_points(float(lat2), float(lon2), float(ipoint['x3']), float(ipoint['y3']))
         
         if idist1 <= max_distance and idist2 <= max_distance:
            return True

      return False

 
   def check_make_events(self, min_events, station_id, obs_file, stime,duration=3,azs=[],els=[],ints=[]):
      # see if this one obs is part of an event or new
      if duration < 1:
         duration = 1
      match_time = 0
      match_dist = 0
      matches = []
      lat = float(self.station_dict[station_id]['lat'])
      lon = float(self.station_dict[station_id]['lon'])
      alt = float(self.station_dict[station_id]['alt'])

      if len(azs) > 0:
         az1 = azs[0]
      else:
         az1 = None

      if len(min_events.keys()) == 0:
         eid = 1
         # first event
         min_events[eid] = {}
         min_events[eid]['stations'] = []
         min_events[eid]['lats'] = []
         min_events[eid]['lons'] = []
         min_events[eid]['alts'] = []
         min_events[eid]['files'] = []
         min_events[eid]['azs'] = []
         min_events[eid]['els'] = []
         min_events[eid]['ints'] = []
         min_events[eid]['ipoints'] = []
         min_events[eid]['start_datetime'] = []
         min_events[eid]['stations'].append(station_id)
         min_events[eid]['lats'].append(lat)
         min_events[eid]['lons'].append(lon)
         min_events[eid]['alts'].append(alt)
         min_events[eid]['azs'].append(azs)
         min_events[eid]['els'].append(els)
         min_events[eid]['ints'].append(ints)
         min_events[eid]['files'].append(obs_file)
         min_events[eid]['start_datetime'].append(stime)
         min_events[eid]['stime'] = stime
         return(min_events)
      else:
         # there are some events for this minute already.
         # loop over all and see if this event's time and distance is in range enough to be considered.
         ipoints = []
         for eid in min_events:
            this_time = min_events[eid]['stime']
            s_datestamp, s_timestamp = self.date_str_to_datetime(stime)
            t_datestamp, t_timestamp = self.date_str_to_datetime(this_time)
            time_diff = abs(s_timestamp - t_timestamp)
            #if the event start is within 6 seconds
            #sdur = duration * -2
            #edur = duration * 2
            if time_diff <= 10:
               avg_lat = np.mean(min_events[eid]['lats'])
               avg_lon = np.mean(min_events[eid]['lons'])
               match_dist = dist_between_two_points(avg_lat, avg_lon, lat, lon)
               match_dist2 = match_dist
               match_time = 1
               #print("   TIME DIFF, MATCH DIST:", time_diff, match_dist)
               if match_dist <= 0:
                  #print("SAME STATION MULTIPLE OBS MATCH")
                  #print("ADD MATCH 0", eid)

                  matches.append((eid, match_time, match_dist,None))

               elif match_dist < 700 :
                  match_dist = 1
                  #print("STATIONS:", station_id, obs_file, min_events[eid]['stations'], min_events[eid]['files'])
                  # check if this obs az1 intersects with the other obs az1s
                  intersect = True 
                  for i in range(0, len(min_events[eid]['lats'])):
                     
                     st = min_events[eid]['stations'][i]
                     lat2 = min_events[eid]['lats'][i]
                     lon2 = min_events[eid]['lons'][i]

                     if len(min_events[eid]['azs'][i]) > 0 and station_id != st:
                        az2 = min_events[eid]['azs'][i][0]
                        err_status, ipoint= geo_intersec_point(lat, lon, az1, lat2, lon2, az2)
                        try:
                           err_status, ipoint= geo_intersec_point(lat, lon, az1, lat2, lon2, az2)
                        except Exception as e :
                           #print("ERROR GETTING AN IPOINT!", lat, lon, az1, lat2, lon2, az2)
                           #print("ER:", str(e))
                           err_status = True
                        #print("   IPOINT:", ipoint)
                        if err_status is True:
                           # intersection failed
                           ipoint = [0,0]
                           idist = 0
                        #   print("   ADD MATCH 1", eid)
                           matches.append((eid, match_time, match_dist,None))
                           # failed
                        else:
                           lat2 = ipoint['x3']
                           lon2 = ipoint['y3']
                           idist = dist_between_two_points(float(lat), float(lon), float(lat2), float(lon2))
                           #print("   TIME DIFF:", time_diff)
                           #print("   DIST DIFF:", match_dist2)
                           #print("   2D INT:", lat,lon,az1, lat2,lon2,az2)
                           #print("   2D IPOINT:", ipoint)
                           #print("   2D IPOINT DIST:", idist)
                           # only accept events if the intersection is < 600 miles and not 0
                           if idist < 600 and idist != 0:
                              #print("   *** GOOD INTERSECT!", idist)
                              intersect = True
                           else:
                              #print("   *** BAD INTERSECT!", idist, ipoint)
                              intersect = False 
                        if intersect is True or intersect is False:
                           #print("   ADD MATCH 2", eid)
                           ipoints.append(ipoint)
                           matches.append((eid, match_time, match_dist,ipoints))
                     else:
                        #print("   ADD MATCH 3", eid, station_id, st)
                        ipoint = None
                        ipoints.append(ipoint)
                        matches.append((eid, match_time, match_dist, ipoints))
                  # before adding we should see if the points intersect!? or no?
                  # TIME FOR EVENTS COULD BE BETTER LONGER EVENTS & SHORTER NEEDS TO BE DYNAMIC MORE
            elif time_diff < 20:
               avg_lat = np.mean(min_events[eid]['lats'])
               avg_lon = np.mean(min_events[eid]['lons'])
               match_dist = dist_between_two_points(avg_lat, avg_lon, lat, lon)
               if match_dist < 600:
                  #print("Station Dist : ", match_dist)
                  #print("Times are: ", stime, this_time)
                  #print("Time diff is : ", time_diff)

                  # check if this obs az1 intersects with the other obs az1s
                  intersect = True
                  ipoint = None
                  for i in range(0, len(min_events[eid]['lats'])):
                     
                     st = min_events[eid]['stations'][i]
                     lat2 = min_events[eid]['lats'][i]
                     lon2 = min_events[eid]['lons'][i]

                     if len(min_events[eid]['azs'][i]) > 0 and station_id != st:
                        az2 = min_events[eid]['azs'][i][0]
                        err_status, ipoint= geo_intersec_point(lat, lon, az1, lat2, lon2, az2)
                        if err_status is True:
                           # intersection failed
                           ipoint = [0,0]
                           idist = 0
                           # failed
                        else:
                           lat2 = ipoint['x3']
                           lon2 = ipoint['y3']
                           idist = dist_between_two_points(float(lat), float(lon), float(lat2), float(lon2))
                           #print("TIME DIFF:", time_diff)
                           #print("DIST DIFF:", match_dist)
                           #print("2D INT:", lat,lon,az1, lat2,lon2,az2)
                           #print("2D IPOINT:", ipoint)
                           #print("2D IPOINT DIST:", idist)
                           if idist < 600:
                              intersect = True
                     ipoints.append(ipoint)
                  else:
                     ipoint = None
                  if intersect is True or intersect is False:
                     matches.append((eid, match_time, match_dist, ipoints))

      if len(matches) > 0:
         eid = matches[0][0]
         #if len(matches) == 1:
         #   print("We found a matching event. Add this obs to that event!")
         #else:
         #   print("We found MORE THAN ONE matching event. Pick the best one! How???")
         min_events[eid]['stations'].append(station_id)
         min_events[eid]['lats'].append(lat)
         min_events[eid]['lons'].append(lon)
         min_events[eid]['alts'].append(alt)
         min_events[eid]['azs'].append(azs)
         min_events[eid]['els'].append(els)
         min_events[eid]['ints'].append(ints)
         min_events[eid]['files'].append(obs_file)
         min_events[eid]['ipoints'].append(ipoints)
         min_events[eid]['start_datetime'].append(stime)
         avg_time = self.average_times(min_events[eid]['start_datetime'])
         min_events[eid]['stime'] = avg_time
      else:
         # No match make new! 
         eid = max(min_events.keys()) + 1 
         min_events[eid] = {}
         min_events[eid]['stations'] = []
         min_events[eid]['lats'] = []
         min_events[eid]['lons'] = []
         min_events[eid]['alts'] = []
         min_events[eid]['azs'] = []
         min_events[eid]['els'] = []
         min_events[eid]['ints'] = []
         min_events[eid]['files'] = []
         min_events[eid]['ipoints'] = []
         min_events[eid]['start_datetime'] = []
         min_events[eid]['stations'].append(station_id)
         min_events[eid]['lats'].append(lat)
         min_events[eid]['lons'].append(lon)
         min_events[eid]['alts'].append(alt)
         min_events[eid]['azs'].append(azs)
         min_events[eid]['els'].append(els)
         min_events[eid]['ints'].append(ints)
         min_events[eid]['files'].append(obs_file)
         min_events[eid]['ipoints'].append(ipoints)
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
      # This is where we group obs into events! 
      # IT should be close in time and distance
      # and the lines should intersect 
      missing_red = {}

      for row in min_obs:
         if len(row) >= 5:
            times = json.loads(row[5])
            if len(times) > 0:
               tt = times[0]
            else:
               tt = None
         else:
            print("\t\tOBS NOT REDUCED!", row)
            tt = None
            print("\t", row[3],tt)

      station_dists = {}
      #   SELECT station_id, event_id, event_minute, obs_id, fns, times, xs, ys, azs, els, ints, status, ignore 

      min_events = {}
      max_dur = 0
      for obs in min_obs:
         #print(obs)
         (station_id, event_id, event_minute, obs_id, fns, times, xs, ys, azs, els, ints, status, ignore) = obs 
         if type(azs) == str:
            azs = json.loads(azs) 
            els = json.loads(els) 
            ints = json.loads(ints) 


         times = json.loads(obs[5])
         duration=len(times) / 25
         if duration == 0:
            duration = 1
         if duration > max_dur:
            max_dur = duration

         if len(times) > 0:
            stime = times[0]
         else:
            stime = None
         obs_file = obs[3]
         station_id = obs[0]
         if stime is None:
            #print("NO REDUCTION!", station_id, obs[3])
            obs_id = station_id + "_" + obs_file
            if obs_id not in missing_red:
                missing_red[obs_id] = 1
            else:
                missing_red[obs_id] += 1
            continue
         try:
            lat = float(self.station_dict[station_id]['lat'])
            lon = float(self.station_dict[station_id]['lon'])
            alt = float(self.station_dict[station_id]['alt'])
         except:
            #print("NEW SITE ERROR!")
            continue
         point = lat * lon
         dd, tt = stime.split(" ")
         sec = tt.split(":")[-1]
         sec = float(sec)
         #min_events = self.check_make_events(min_events, station_id, obs_file, stime, duration,azs,els,ints)
         # min events should be a number dict
         min_events = self.check_make_events_new(min_events, station_id, obs_file, stime, max_dur,azs,els,ints)

      print("MINUTE EVENTS:", len(min_events))
      for eid in min_events:
         unique_stations_count = len(set(min_events[eid]['stations']))
         if unique_stations_count > 1:
            msg = f"\tMULTI STATION EVENT: {eid} {min_events[eid]['stations']} {unique_stations_count}"
            print(colored(msg,"green"))
         else:
            msg = f"\tSINGLE STATION EVENT: {eid} {min_events[eid]['stations']} {min_events[eid]['start_datetime']} "
            print(colored(msg,"cyan"))


      return(min_events)

      # BELOW HERE DOESN'T MATTER ANYMORE
      return()
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

   def get_min_obs_dict(self, date):


      self.min_obs_dict = {}
      sql = """
         SELECT station_id, event_id, event_minute, obs_id, fns, times, xs, ys, azs, els, ints, status, ignore 
           FROM event_obs
          WHERE obs_id like ?
      """
      vals = ["%" + date + "%"]
      self.cur.execute(sql, vals)
      rows = self.cur.fetchall()
      for row in rows:
         station_id, event_id, event_minute, obs_id, fns, times, xs, ys, azs, els, ints, status, ignore = row
         if event_minute not in self.min_obs_dict:
            self.min_obs_dict[event_minute] = []
         self.min_obs_dict[event_minute].append((station_id, event_id, event_minute, obs_id, fns, times, xs, ys, azs, els, ints, status, ignore))

   def get_obs(self, wild):   
      if wild in self.obs_dict:
         return((self.obs_edict[wild]))
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

   def get_all_obs(self, wild):   
      obs_data = []
      self.obs_edict = {}
      sql = """
         SELECT station_id, event_id, event_minute, obs_id, fns, times, xs, ys, azs, els, ints, status, ignore 
           FROM event_obs
          WHERE obs_id like ?
      """
      vals = ["%" + wild + "%"]
      #print(sql, vals)
      self.cur.execute(sql, vals)
      rows = self.cur.fetchall()
      for row in rows:
         station_id, event_id, event_minute, obs_id, fns, times, xs, ys, azs, els, ints, status, ignore = row
         fns = json.loads(fns)
         times = json.loads(times)
         xs = json.loads(xs)
         ys = json.loads(ys)
         azs = json.loads(azs)
         els = json.loads(els)
         ints = json.loads(ints)
         obs_data.append((station_id, event_id, event_minute, obs_id, fns, times, xs, ys, azs, els, ints, status, ignore))
         self.obs_edict[obs_id] = ((station_id, event_id, event_minute, obs_id, fns, times, xs, ys, azs, els, ints, status, ignore))
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
      #print(self.allsky_console)
      self.set_dates(date)
      # load all obs from the available ALL OBS file

      if os.path.exists(self.all_obs_file) is True: 
         self.all_obs = load_json_file(self.all_obs_file)
      ic = 0
      print("Inserting all obs")
      for obs in self.all_obs:
         # dict_keys(['dur', 'station_id', 'peak_int', 'hd_video_file', 'hd_roi', 'last_update', 
         # 'roi', 'sd_video_file', 'sync_status', 'ffp', 'meteor_frame_data', 'event_start_time', 'calib', 'event_id', 'hc']) 
         # dt, fn, x, y, w, h, oint, ra, dec, az, el
         # set the initial event_id to the minute of the capture


         temp_ev_id = obs['sd_video_file'][0:16]
         if "meteor_frame_data" not in obs:
            continue
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
         #print("INSERT", sql)
         #print("VALUES", ivals)
         ic += 1

      self.con.commit()

      print("\rTotal OBS for " + date + " : " + str(len(self.all_obs)) + "                                        ",end="")
      print("")


      
   def event_id_to_date(self, event_id):
      year = event_id[0:4]
      mon = event_id[4:6]
      day = event_id[6:8]
      date = year + "_" + mon + "_" + day
      return(date)

      

   def resolve_failed_day(self, event_day):
      sql = """
            SELECT event_id, event_minute, revision, stations, obs_ids, event_start_time, event_start_times,
                   lats, lons, event_status, run_date, run_times
              FROM events
             WHERE event_id like ?
               AND ( event_status like 'FAIL%' OR event_status like '%BAD%')
          ORDER BY event_id desc
      """
      print(sql)
      vals = [event_day + '%']
      self.cur.execute(sql, vals)
      rows = self.cur.fetchall()
      print("ROWS:", len(rows))
      for row in rows:
         event_id = row[0]
         print("Resolving:", event_id)
         self.resolve_event(event_id)

   def show_edits(self):
      for sd_vid in self.edits['sd_clips']:
         print("EDIT:", self.edits['sd_clips'][sd_vid]['status'], sd_vid, self.edits['sd_clips'][sd_vid].keys())

   def purge_invalid_events(self, event_day):
      self.set_dates(event_day)
      ev_dirs = os.listdir(self.local_evdir )

      invalid_event_file = self.local_evdir + "/" + event_day + "_INVALID_EVENTS.json"
      if os.path.exists(invalid_event_file) is True: 
         invalid_events = load_json_file(invalid_event_file)
      else:
         invalid_events = {}

      for evd in ev_dirs:
         if os.path.isdir(self.local_evdir + evd):
            if os.path.exists(self.local_evdir + evd + "/" + evd + "-fail.json") and os.path.exists(self.local_evdir + evd + "/" + evd + "-event.json") is False:
               print("Failed file found with no event file found for :", evd)
               if os.path.exists(self.local_evdir + evd + "/" + evd + "_GOOD_OBS.json") :
                  # make sure there are actually good obs for this file. If there are not at least 2 then the event is invalid! 
                  good_obs = load_json_file(self.local_evdir + evd + "/" + evd + "_GOOD_OBS.json")
                  gdso = 0
                  for station in good_obs: 
                     go = 0
                     for key in good_obs[station]:
                        go+= 1
                     if go >= 1:
                        gdso += 1

                  if gdso == 0:
                     print("THERE ARE NO GOOD OBS FOR THIS EVENT IT SHOULD BE DELETED!", evd)
                     invalid_events[evd] = 1
                     cmd = "rm -rf " + self.local_evdir + evd
                     print(cmd)
                     os.system(cmd)
      for event_id in invalid_events:
         sql = "DELETE FROM EVENTS WHERE event_id = ?"
         print(sql)
         self.cur.execute(sql, [event_id])
      self.con.commit()
      save_json_file(self.local_evdir + "/" + event_day + "_INVALID_EVENTS.json", invalid_events)

   def quick_day_status(self, event_day):
      print("Quick event stats!")
      obs_dict = load_json_file(self.obs_dict_file)
      all_obs = load_json_file(self.all_obs_file)
      min_events = load_json_file(self.min_events_file)
      all_events = load_json_file(self.all_events_file)
      db_events = {}
      sql = """
         SELECT event_id,stations from events order by event_id 
      """
      self.cur.execute(sql)
      rows = self.cur.fetchall()
      for row in rows:
         event_id = row[0]
         print(row[0], row[1])
         db_events[event_id] = {}


      print("ALL OBS", len(all_obs))
      print("OBS DICT", len(obs_dict.keys()))
      print("MINUTE EVENTS", len(min_events.keys()))
      print("ALL EVENTS", len(all_events))
      print("DB EVENTS", len(db_events.keys()))

      all_good_events = []
      for data in all_events:
         if len(set(data['stations'])) >= 2:
         #   print("GOOD", len(data['stations']), data['event_id'], data['solve_status'], data.keys())
            all_good_events.append(data)
         #else:
         #   print("BAD", len(data['stations']), data['event_id'], data['solve_status'], data.keys())
      if len(all_good_events) != len(all_events):
         print("SAVE ALL EVENT FILE.")
         save_json_file(self.all_events_file, all_good_events)

   def event_day_status(self, event_day):
      self.set_dates(event_day)
      self.load_stations_file()

      event_day_stats = self.sql_select_event_day_stats(self.date)

      by_station = """
      <table>
         <thead>
            <tr>
               <th>
                  Meteor Obs
               </th>
               <th>
                  Station 
               </th>
               <th>
                  Operator Info 
               </th>
            </tr>
         </thead>
         <tbody>
      """

      for row in event_day_stats["by_station"]:
         st, cc = row
         if st not in self.photo_credits:
            self.photo_credits[st] = "unknown"
         by_station += "<tr><td> {:s}</td><td> {:s}</td><td> {:s}</td></tr>".format(str(cc), st, self.photo_credits[st])
      by_station += "</tbody></table>"
      event_dict = {} 

      good = """
      <table>
         <thead>
            <tr>
               <th>
                  Event ID 
               </th>
               <th>
                  2D Intersections 
               </th>
               <th>
                  3D Planes 
               </th>
               <th>
                  WMPL Status 
               </th>
               <th>
                  AI Meteors 
               </th>
            </tr>
         </thead>
         <tbody>
      """
      for ev_data in event_day_stats["all_events"]:
         event_id, event_status, event_data = ev_data
         good += "<tr><td>{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td></tr> ".format(event_id, "", "", event_status, "")

         #solve_file = self.local_evdir + ev + "/" + ev + "-event.json" 
         print("DATA", ev_data)



      good += "</tbody></table>"


      out_file = self.local_evdir + "/" + event_day + "_log.html"

      self.all_obs_file = self.local_evdir + self.date + "_ALL_OBS.json"

      self.all_events_file = self.local_evdir + self.date + "_ALL_EVENTS.json"
      if os.path.exists(self.all_obs_file):
         all_obs = load_json_file(self.all_obs_file)
      else:
         all_obs = {}

      if os.path.exists(self.all_events_file):
         all_events = load_json_file(self.all_events_file)
      else:
         all_events = {}

      stats = ""
      for key in event_day_stats:
         if stats != "":
            stats += " AND " 
         stats += str(event_day_stats[key]) + " " + str(key) + " events "
         
      report = """
      <html lang="en-US">
         <head>
              <meta charset="UTF-8" />
              <meta name="viewport" content="width=device-width, initial-scale=1.0" />
              <meta http-equiv="X-UA-Compatible" content="ie=edge" />
              <meta name="msapplication-TileColor" content="#ffffff" />
              <meta name="msapplication-TileImage" content="/favicon/ms-icon-144x144.png" />
              <meta name="theme-color" content="#ffffff" /> <title>ALLSKY7 {:s} REPORT</title>
              <meta name="description" content="A modern and minimal CSS framework for terminal lovers."/>
        </head>
        <link rel="stylesheet" href="https://unpkg.com/terminal.css@0.7.2/dist/terminal.min.css" />
        <body class="terminal">
        <div class="container">
            <h1>AllSky7 Event Report for {:s}</h1>
            <section>

               <div class="terminal-card">
               <header>Database Reconciliation</header>
                  The network database contains {:s} observations spanning {:s} events. <br>
                  The solving node database database contains {:s} successful events, {:s} failed events and {:s} total observations.
                  
               </div>

               <div class="terminal-card">
               <header>Obs By Station</header>
               {:s}
               </div>

               <div class="terminal-card">
               <header>All Multi-Station Events</header>
               {:s}
               </div>




            </section>
         </body>
      </html>
      """.format(event_day, event_day, str(len(all_obs)), str(len(all_events)), str(event_day_stats['STATUS_SOLVED']), str(event_day_stats['STATUS_FAILED']), str(event_day_stats['TOTAL_OBS']), by_station, good )

      print(report)
      out = open( out_file, "w")
      out.write(report)
      print(out_file)

       
   def resolve_event_day(self, event_day):
      temp = load_json_file("cores.json")
      cores = temp['cores']
      self.set_dates(event_day)
      self.quick_day_status(event_day)
      sql = """
         SELECT event_id from events order by event_id 
      """
      self.cur.execute(sql)
      rows = self.cur.fetchall()
      for row in rows:
         running = check_running("python")

         while running > 32:
            print("Wait 10 seconds, already have", running, "processes")
            time.sleep(10)
            running = check_running("python")
            
         event_id = row[0]
         # if it has already solved or failed skip it
         ev_file = self.local_evdir + event_id + "/" + event_id + "_REVIEW.jpg"
         if os.path.exists(ev_file) is False:
            cmd = "/usr/bin/python3 AllSkyNetwork.py resolve_event " + event_id + " > /dev/null 2>&1 &" 
            print(cmd)
            os.system(cmd)

   def get_valid_obs(self, station_id, day):
      cloud_dir = "/mnt/archive.allsky.tv/" + station_id + "/METEORS/" + day[0:4] + "/" + day + "/"
      obs_ids_file = cloud_dir + day + "_OBS_IDS.info"
      if os.path.exists(obs_ids_file) is True:
         try:
            data = load_json_file(obs_ids_file) 
         except:
            print("BAD FILE", obs_ids_file)
            data = []
      else:
         data = []
      obs_ids = []
      for row in data:
         obs_ids.append(row[0])
      return(obs_ids)

   def load_event_obs(self, event_day):
      self.event_obs = {}
      if os.path.exists(self.all_events_file) is True:
         all_events_data = load_json_file(self.all_events_file)
      else:
         all_events_data = []
      for ev in all_events_data:
         for i in range(0, len(ev['stations'])):
            st = ev['stations'][i]
            fn = ev['files'][i].replace(".mp4", "")
            obs_id = st + "_" + fn
         self.event_obs[obs_id] = ev['event_id']
   
   def best_obs_day(self, event_day):

      nav_header = self.make_page_header(event_day)

      self.load_stations_file()
      st_list = []
      for sd in self.stations :
         #sd = self.stations[st_id]
         st_id = int(sd['station_id'].replace("AMS", ""))
         op_status = sd['op_status']
         st_key = "AMS" + str(st_id)
         if st_key in self.photo_credits:
            pc = self.photo_credits[st_key]
         else:
            pc = st_id
         print(st_id, st_key, op_status, pc)
         st_list.append((st_id, st_key, op_status, pc))

      ignore_stations = ["AMS202"]
      valid_obs = {}
      html = ""
      obs_by_int = []
      self.set_dates(event_day)
      self.quick_day_status(event_day)
      valid_obs_file = self.local_evdir + event_day + "_VALID_OBS.json"

      self.load_event_obs(event_day)
      for evo in self.event_obs:
         #print(evo, self.event_obs[evo])
         sql = "UPDATE event_obs set event_id = '{:s}' WHERE obs_id = '{:s}' ".format(self.event_obs[evo], evo)
         self.cur.execute(sql)
    
      self.con.commit()

      # build list of valid obs VALID OBS for 1 day for each station
      if os.path.exists(valid_obs_file) is True:
         valid_obs = load_json_file(valid_obs_file)
      sql = """
         SELECT event_id, obs_id, times, ints from event_obs order by event_id 
      """
      self.cur.execute(sql)
      rows = self.cur.fetchall()
      all_cmds = []

      for row in rows:
         event_id = row[0]
         obs_id = row[1]
         el = obs_id.split("_")
         station_id = el[0]
         if station_id in ignore_stations:
            continue
         if station_id not in valid_obs:
            valid_obs[station_id] = self.get_valid_obs(station_id, event_day)

         times = row[2]
         ints = row[3]
         jints = json.loads(ints)
         jtimes = json.loads(times)
         if len(jtimes) > 0:
            edate = jtimes[0]
            max_frames = len(jtimes)
         else:
            etime = " " 
            edate = " " 
            max_frames = 0
         if len(jints) > 0:
            max_int = max(jints)
         else:
            max_int = 0
         obs_key = obs_id.replace(station_id + "_", "")

         obs_by_int.append((event_id, obs_id, max_int, edate, max_frames))

      obs_by_int = sorted(obs_by_int, key=lambda x: (x[2]), reverse=True)
      single_station_html = ""
      obs_by_station_html = ""
      obs_by_station = {}
      mso = 0
      sso = 0
      html += "<div style='width: 100%'>"
      single_station_html += "<div style='width: 100%'>"
      for event_id, obs_id, ints, edate, max_frames in obs_by_int:
         st_id = obs_id.split("_")[0]
         if st_id not in obs_by_station:
            obs_by_station[st_id] = ""

         edate += "_" + event_id
         img_ht = self.meteor_cell_html(obs_id, edate, "")

         obs_by_station[st_id] += img_ht
         if str(event_id) == "0":
            single_station_html += img_ht
            sso += 1
         else:
            html += img_ht
            mso += 1
      html += "</div>"

      single_station_html += "</div>"
      template = ""
      tt = open("./FlaskTemplates/allsky-template-v2.html")
      for line in tt:
         template += line

      template = template.replace("{TITLE}", "ALLSKY7 EVENTS " + self.day)
      template = template.replace("AllSkyCams.com", "AllSky.com")
      self.local_evdir = self.local_event_dir + self.year + "/" + self.month + "/" + self.day  + "/"
      out_file_good = self.local_evdir + self.day + "_OBS_GOOD.html"
      out_file_bad = self.local_evdir + self.day + "_OBS_BAD.html"
      out_file_failed = self.local_evdir + self.day + "_OBS_FAIL.html"
      out_file_pending = self.local_evdir + self.day + "_OBS_PENDING.html"

      header = "<h4>{:s} Multi Station Observations Sorted By Intensity</h4>".format(str(mso))
      ms_temp = template.replace("{MAIN_CONTENT}", nav_header + header + html)
      fp = open( self.local_evdir + event_day + "_MULTI_STATION_INT.html", "w")
      fp.write(ms_temp)
      fp.close()

      header = "<h4>{:s} Single Station Observations Sorted By Intensity</h4>".format(str(sso))
      ss_temp = template.replace("{MAIN_CONTENT}", nav_header + header + single_station_html)
      fp = open( self.local_evdir + event_day + "_SINGLE_STATION_INT.html", "w")
      #fp.write("<h4>{:s} Single Station Observations Sorted By Intensity</h4>".format(str(sso)))
      fp.write(ss_temp)
      #fp.write(single_station_html)
      fp.close()



      fp = open( self.local_evdir + event_day + "_OBS_BY_STATION.html", "w")
 
      main_content = "<h1>{:s} Observations For {:s} grouped by station and sorted by intensity</h1>".format(str(sso), event_day)
      #fp.write("<h1>{:s} Observations For {:s} grouped by station and sorted by intensity</h1>".format(str(sso), event_day))

      st_list = sorted(st_list, key=lambda x: (x[0]), reverse=False)

      down_html = ""
      no_obs_html = ""
      for row in st_list:
         st_i_id, st_id, op_status, pc = row
         if op_status == "ACTIVE":
            pc = self.photo_credits[st_id]
            if st_id in obs_by_station:
               main_content += "<div><h1>{:s} - {:s}</h1>\n".format(st_id, pc)
               main_content += obs_by_station[st_id]
               main_content += "</div>\n"
            else:
               no_obs_html += ("<div><h1>{:s} - {:s}</h1>\n".format(st_id, pc))
               no_obs_html += ("No observations</div>") 
            main_content += "<div style='clear:both'></div><br>"
         else:
            down_html += "<li>{:s}".format(st_id)
      main_content += "<h1>No observations</h1><ul>" + no_obs_html + "</ul>"
      main_content += "<h1>Stations Down</h1><ul>" + down_html + "</ul>"
      template = template.replace("{MAIN_CONTENT}", nav_header + main_content)
      fp.write(template)
      fp.close()


      save_json_file(self.local_evdir + event_day + "_OBS_BY_INT.json", obs_by_int)
      save_json_file(self.local_evdir + event_day + "_VALID_OBS.json", valid_obs)
      print("SAVED:", self.local_evdir + event_day + "_MULTI_STATION_INT.html", "w")
      print("SAVED:", self.local_evdir + event_day + "_SINGLE_STATION_INT.html", "w")
      print("SAVED:", self.local_evdir + event_day + "_OBS_BY_STATION.html", "w")

   def review_event_day(self, event_day):
      self.set_dates(event_day)
      self.quick_day_status(event_day)
      #self.obs_timeline (event_day)
      if os.path.exists(self.sync_log_file):
         self.sync_log = load_json_file(self.sync_log_file)
      else:
         self.sync_log = {}
       
      sql = """
         SELECT event_id from events order by event_id 
      """
      self.cur.execute(sql)
      rows = self.cur.fetchall()
      all_cmds = []
 
      print(len(rows), " events on this day", event_day)
      print("Sync'ing media please wait...")
      if True:
         for row in rows:
            event_id = row[0]
            wget_cmds = self.get_event_media(event_id)
            all_cmds.extend(wget_cmds)
         all_cmds = sorted(all_cmds)

         print("Fetching media:", len(all_cmds))
         self.fast_cmds(all_cmds)
         save_json_file(self.sync_log_file, self.sync_log)

      print("All media downloaded. Ready to review events.")

      for row in rows:
         event_id = row[0]
         wget_cmds = self.get_event_media(event_id)
         self.review_event(event_id)

         (review_image, map_img, obs_imgs, marked_images, event_data, obs_data) = self.review_event_step2()
         if "2d_status" not in event_data:
            event_data = self.get_2d_status(event_data, obs_data)

         self.echo_event_data(event_data, obs_data)  

         event_data_file = self.local_evdir + self.event_id + "/" + self.event_id + "_EVENT_DATA.json"
         obs_data_file = self.local_evdir + self.event_id + "/" + self.event_id + "_OBS_DATA.json"
         save_json_file(event_data_file, event_data)
         save_json_file(obs_data_file, obs_data, True)

         if review_image is not None:
            cv2.imshow("pepe", review_image)
            cv2.waitKey(30)
         else:
            print("REVIEW IMAGE IS NONE!", review_image)

   def get_event_media(self, event_id):

      event_day = self.event_id_to_date(event_id)
      self.event_id = event_id
      self.edits_file = self.local_event_dir + self.event_id + "_EDITS.json"
      if os.path.exists(self.edits_file) is True:
         self.edits = load_json_file(self.edits_file)
      else:
         self.edits = {}
         self.edits['sd_clips'] = {} 

      self.show_edits()

      event_day = self.event_id_to_date(event_id)
      self.year = event_day[0:4]
      self.month = event_day[5:7]
      self.dom = event_day[8:10]
      self.date = self.year + "_" + self.month + "_" + self.dom
      


      self.sd_clips = {}

      # load event related files
      review_data = {}
      review_data['cloud_files'] = []
      local_event_dir = "/mnt/f/EVENTS/" + self.year + "/" + self.month + "/" + self.dom + "/" + self.event_id + "/" 
      self.ev_dir = local_event_dir 
      #self.local_event_dir = local_event_dir 
      event_file = self.ev_dir + event_id + "-event.json"
      good_obs_file = self.ev_dir + event_id + "_GOOD_OBS.json"
      planes_file = self.ev_dir + event_id + "_PLANES.json"

      event_data, obs_data, planes_data = None,None,None
      if os.path.exists(event_file):
         event_data = load_json_file(event_file)
      if os.path.exists(good_obs_file):
         obs_data = load_json_file(good_obs_file)
      if os.path.exists(planes_file):
         planes_data = load_json_file(planes_file)

      # Syncronize source media from host station or allsky archive
      missing_files = []
      wget_cmds = []
      if obs_data is not None:
         for station in obs_data:
            cloud_meteor_dir = "/mnt/archive.allsky.tv/" + station + "/METEORS/" + self.year + "/" + self.date + "/" 
            cloud_files_file = local_event_dir + station + "_CLOUDFILES.json"
            cloud_cal_dir = "/mnt/archive.allsky.tv/" + station + "/CAL/" 

            if os.path.exists(cloud_files_file) is False:
               if os.path.exists(cloud_meteor_dir) is True:
                  cloud_files = os.listdir(cloud_meteor_dir) 
               else:
                  cloud_files = []
               save_json_file(cloud_files_file, cloud_files)
            else:
               sz, td = get_file_info(cloud_files_file)
               if td / 60 > 10:
                  cloud_files = os.listdir(cloud_meteor_dir) 
                  save_json_file(cloud_files_file, cloud_files)
               else:    
                  cloud_files = load_json_file(cloud_files_file)

            for ofile in obs_data[station]:
               skip_remote = 0
               base_str = ofile.replace(".mp4", "")
               obs_id = station + "_" + ofile
               out_file = station + "_" + ofile
               if obs_id in self.sync_log:
                  self.sd_clips[out_file] = {} 
                  self.sd_clips[out_file]['status'] = True
                  continue

               if station in self.rurls:
                  rmp4 = self.rurls[station] + "/meteors/" + self.date +  "/" + ofile
               else:
                  skip_remote = 1
               # get the SD MP$
               out_file = station + "_" + ofile
               json_file = ofile.replace(".mp4", ".json")
               red_json_file = ofile.replace(".mp4", "-reduced.json")

               out_json_file = station + "_" + json_file
               out_red_json_file = station + "_" + red_json_file

               if skip_remote == 0:
                  rjson = self.rurls[station] + "/meteors/" + self.date +  "/" + json_file 
                  rred= self.rurls[station] + "/meteors/" + self.date +  "/" + red_json_file 
               cloud_dir = "/mnt/archive.allsky.tv/" + station + "/METEORS/" + self.date.split("_")[0] + "/" + self.date + "/" 
        
               local_file_ok = False
               if os.path.exists( local_event_dir + "/" + out_file) is True:
                  sz, td =  get_file_info(local_event_dir + "/" + out_file)
                  if sz > 0:
                     local_file_ok = True
                  else:
                     os.system("rm " + local_event_dir + "/" + out_file)

               if local_file_ok is False and skip_remote == 0 and os.path.exists( local_event_dir + "/" + out_file) is False and os.path.exists( local_event_dir + "/" + out_file + ".failed") is False:

                  # first try to get the file from the cloud dir!
                  of1 = out_file.replace(".mp4", "-360p.mp4")
                  of2 = out_file.replace(".mp4", "-180p.mp4")
                  if of1 in cloud_files:
                     print(of1, "found in cloudfiles!")
                     cmd = "cp " + cloud_dir + of1 + " " + local_event_dir + "/" + out_file 
                     os.system(cmd)
                     #print("CLOUD FILES", out_file, cloud_files)
                  elif of2 in cloud_files:
                     cmd = "cp " + cloud_dir + of2 + " " + local_event_dir + "/" + out_file 
                     os.system(cmd)
                  else:

                     cmd = "wget " + rmp4 + "  --timeout=1 --waitretry=0 --tries=1 --no-check-certificate -O " + local_event_dir + "/" + out_file
                     #print(cmd)
                     #os.system(cmd)
                     wget_cmds.append(cmd)

                  #if os.path.exists( local_event_dir + "/" + out_file) is False:
                  #   cmd = "touch " + local_event_dir + "/" + out_file + ".failed"
                  #   os.system(cmd)
               else:
                  print("Already have the file?", local_event_dir + "/" + out_file)
             
               if os.path.exists( local_event_dir + "/" + out_file) is True:
                  if out_file not in self.sd_clips:
                     self.sd_clips[out_file] = {} 
                  self.sd_clips[out_file]['status'] = True
                  if out_file not in self.sync_log:
                     self.sync_log[out_file] = {} 
                  self.sync_log[out_file]['status'] = "GOOD"
               else:
                  if out_file not in self.sd_clips:
                     self.sd_clips[out_file] = {} 
                  if out_file not in self.sync_log:
                     self.sync_log[out_file] = {} 
                  self.sync_log[out_file]['status'] = "SYNC_FAILED"
                  self.sd_clips[out_file]['status'] = False 
                  missing_files.append(out_file)
      #else:
      #   print("none for ", good_obs_file)


      return(wget_cmds)

   def event_data_movie(self, event_id, event_data, good_obs):
      data_movie_frames = []
      lines = []
      #cv2.namedWindow('pepe', cv2.WINDOW_NORMAL)
      #cv2.moveWindow("pepe", 1000, 50)
      #cv2.resizeWindow("pepe", 1920, 1080)
      points = []
      map_frames = []
      map_folder = self.ev_dir + "MAP_FRAMES/"
      #start_lat, start_lon, start_ele, end_lat, end_lon, end_ele, v_init, v_avg = event_data['traj']
      traj = event_data['traj']

      # DO MAPS 
      if os.path.exists(map_folder) is False:
         os.makedirs(map_folder)
      lines.append((traj['start_lat'], traj['start_lon'], traj['end_lat'], traj['end_lon'], 'red'))
      center_latlon = [traj['end_lat'], traj['end_lon']]
      for station_id in good_obs:
         slat,slon,alt = self.station_loc[station_id][:3]
         points.append((slat,slon,station_id,"green","o"))
         map_file = map_folder + station_id + ".jpg"
         if os.path.exists(map_file):
            map_img = cv2.imread(map_file)
            map_img = cv2.resize(map_img, (1920,1080))
         else:
            map_img = make_map(points, lines, center_latlon)
            map_img = cv2.resize(map_img, (1920,1080))
            cv2.imwrite(map_file, map_img)
            print("save geo")
            self.save_geo_json(points, lines)
            print("done save geo")
         map_frames.append(map_img)
         data_movie_frames.append(map_img)
         holds = hold(map_img, 10)
         for h in holds:
            data_movie_frames.append(h)

         map_img = cv2.resize(map_img, (1920,1080))
         cv2.resizeWindow("pepe", 1920, 1080)
         self.PREVIEW = True 
         if self.PREVIEW is True:
            cv2.imshow('pepe', map_img)
            cv2.waitKey(30)
         for vid in good_obs[station_id]:
            obs_id = station_id + "_" + vid
            map_file = map_folder + obs_id.replace(".mp4", ".jpg")
            if obs_id in self.obs_dict:
                obs_data = self.obs_dict[obs_id]
                azs = [row[9] for row in obs_data['meteor_frame_data']]
                els = [row[10] for row in obs_data['meteor_frame_data']]
                ints = [row[6] for row in obs_data['meteor_frame_data']]
                if len(azs) < 2:
                   continue
                az_start_point = self.find_point_from_az_dist(slat,slon,float(azs[0]),350)
                az_end_point = self.find_point_from_az_dist(slat,slon,float(azs[-1]),350)
                lines.append((slat, slon, az_start_point[0] , az_start_point[1], 'green'))
                lines.append((slat, slon, az_end_point[0] , az_end_point[1], 'orange'))
            else:
               print("ERR FINDING:", obs_id)
            if os.path.exists(map_file):
               map_img = cv2.imread(map_file)
               map_img = cv2.resize(map_img, (1920,1080))
            else:
               lines.append((traj['start_lat'], traj['start_lon'], traj['end_lat'], traj['end_lon'], 'red'))
               map_img = make_map(points, lines, center_latlon)
               print("SAVE")
               self.save_geo_json(points, lines)
               print("END SAVE")

               map_img = cv2.resize(map_img, (1920,1080))
               cv2.imwrite(map_file, map_img)
            map_frames.append(map_img)
            data_movie_frames.append(map_img)
            holds = hold(map_img, 10)
            for h in holds:
               data_movie_frames.append(h)

         #map_img = make_map(points, lines)
         #map_img = cv2.resize(map_img, (1920,1080))
            if self.PREVIEW is True:
               cv2.imshow('pepe', map_img)
               cv2.waitKey(30)

      if False:
         obs_jpgs = glob.glob(self.ev_dir + "AMS*.jpg")
         for jpg in obs_jpgs:
            if "roi" in jpg :
               continue
            if "1080p" not in jpg:
               continue
            img = cv2.imread(jpg)
            img = cv2.resize(img, (1920,1080))
            data_movie_frames.append(img)


            if self.PREVIEW is True:
               cv2.imshow('pepe', img)
               cv2.waitKey(30)
            holds = hold(img, 10)
            for h in holds:
               data_movie_frames.append(h)
               if self.PREVIEW is True:
                  cv2.imshow('pepe', h)
                  cv2.waitKey(30)

      # duplicate map frames
      #for fr in map_frames:
      #   data_movie_frames.append(fr)
      #   holds = hold(fr, 10)
      #   for h in holds:
      #      data_movie_frames.append(h)
      #   if self.PREVIEW is True:
      #      cv2.imshow('pepe', fr)
      #      cv2.waitKey(100)

      # DO 3D TRAJECTORY
      plot_dir = self.ev_dir + "PLOT_FRAMES/" 
      files = glob.glob(plot_dir + "*3D*.jpg")
      if len(files) > 0:
         first_img = cv2.imread(files[0])
         first_img = cv2.resize(first_img, (1920,1080))

         # TRANS
         extra = slide_left(map_img, first_img , "FF", 0)
         for e in extra:
            e = cv2.resize(e, (1920,1080))
            if True:
               data_movie_frames.append(e)
               if self.PREVIEW is True:
                  cv2.imshow('pepe', e)
                  cv2.waitKey(30)
      else:
         black_frame = np.zeros((1080,1920,3),dtype=np.uint8)
         img = black_frame

      for f in files:
         img = cv2.imread(f)
         img = cv2.resize(img, (1920,1080))
         data_movie_frames.append(img)

         holds = hold(img, 5)
         for h in holds:
            data_movie_frames.append(h)

         if self.PREVIEW is True:
            cv2.imshow('pepe', img)
            cv2.waitKey(100)

      # light curve
      lc_file = self.ev_dir + event_id + "_LIGHTCURVES.jpg"
      if os.path.exists(lc_file) is False:
         cmd = "cd plotly/ && /usr/bin/python3 plot_maker.py {:s} -p event_light_curves  ".format(event_id)
         print(cmd)
         os.system(cmd)
         time.sleep(1)
      lc_img = cv2.imread(lc_file)
      if lc_img is not None:
         lc_img = cv2.resize(lc_img, (1920,1080))
      else:
         print("NO IMAGE:", lc_file)
         lc_img = np.zeros((1080,1920,3),dtype=np.uint8)
      # TRANS
      extra = slide_left(img, lc_img, "FF", 0)
      for e in extra:
         e = cv2.resize(e, (1920,1080))
         if True:
            data_movie_frames.append(e)
            if self.PREVIEW is True:
               cv2.imshow('pepe', e)
               cv2.waitKey(30)
 
      # hold light curve frame
      holds = hold(lc_img, 25)
      for h in holds:
         data_movie_frames.append(h)

      # REMAINING FILES
      last_img = lc_img
      event_jpgs = glob.glob(self.ev_dir + event_id + "*.jpg")
      for jpg in event_jpgs:
         if "REVIEW" in jpg:
            review_img = cv2.imread(jpg)
            review_img = cv2.resize(review_img, (1920,1080))
            continue
         if "GALLERY" in jpg:
            gallery_img = cv2.imread(jpg)
            gallery_img = cv2.resize(gallery_img, (1920,1080))
            continue
         if "LIGHTCURVE" in jpg:
            continue
         if "OBS_MAP" in jpg:
            continue
         if "MAP" in jpg:
            continue

         img = cv2.imread(jpg)
         img = cv2.resize(img, (1920,1080))

         # TRANS
         extra = slide_left(last_img, img, "FF", 0)
         for e in extra:
            e = cv2.resize(e, (1920,1080))
            if True:
               data_movie_frames.append(e)
               if self.PREVIEW is True:
                  cv2.imshow('pepe', e)
                  cv2.waitKey(30)

         data_movie_frames.append(img)
         holds = hold(img, 15)
         for h in holds:
            data_movie_frames.append(h)

         if self.PREVIEW is True:
            cv2.imshow('pepe', img)
            cv2.waitKey(300)
         last_img = img

      # final run

      final = fade(img, review_img, 40)
      for ff in final:
         data_movie_frames.append(ff)
         if self.PREVIEW is True:
            cv2.imshow('pepe', ff)
            cv2.waitKey(30)

      holds = hold(review_img, 25)
      for h in holds:
         data_movie_frames.append(h)
         if self.PREVIEW is True:
            cv2.imshow('pepe', h)
            cv2.waitKey(300)
      data_movie_frames.append(review_img)
      if self.PREVIEW is True:
         cv2.imshow('pepe', review_img)
         cv2.waitKey(300)

      final = fade(review_img, gallery_img, 40)
      for ff in final:
         data_movie_frames.append(ff)
         if self.PREVIEW is True:
            cv2.imshow('pepe', ff)
            cv2.waitKey(30)

      holds = hold(gallery_img, 35)
      for h in holds:
         data_movie_frames.append(h)
         if self.PREVIEW is True:
            cv2.imshow('pepe', h)
            cv2.waitKey(300)

      data_movie_frames.append(gallery_img)
      if self.PREVIEW is True:
         cv2.imshow('pepe', gallery_img)
         cv2.waitKey(300)

      # with allsky logo then END! 
      #cv2.imshow('pepe', gallery_img)
      #cv2.waitKey(0)

      # fade into the logo then fade into black
      black_frame = np.zeros((1080,1920,3),dtype=np.uint8)
      cx = int((black_frame.shape[1] / 2) - ( self.RF.logo_1920.shape[1] / 2))
      cy = int((black_frame.shape[0] / 2) - ( self.RF.logo_1920.shape[0] / 2))
      black_logo = self.RF.watermark_image(black_frame,  self.RF.logo_1920, cx,cy, .9)

      cx = int((gallery_img.shape[1] / 2) - ( self.RF.logo_1920.shape[1] / 2))
      cy = int((gallery_img.shape[0] / 2) - ( self.RF.logo_1920.shape[0] / 2))
      # 10% opact
      image = self.RF.watermark_image(gallery_img,  self.RF.logo_1920, cx,cy, .1)
      frames = fade(gallery_img, image, 10)
      for frame in frames:
         data_movie_frames.append(frame)
         if self.PREVIEW is True:
            cv2.imshow('pepe', frame)
            cv2.waitKey(30)
      # 25% opact
      image = self.RF.watermark_image(frame,  self.RF.logo_1920, cx,cy, .25)
      frames = fade(frame, image, 10)
      for frame in frames:
         data_movie_frames.append(frame)
         if self.PREVIEW is True:
            cv2.imshow('pepe', frame)
            cv2.waitKey(30)
      # 50% opact
      image = self.RF.watermark_image(frame,  self.RF.logo_1920, cx,cy, .5)
      frames = fade(frame, image, 10)
      for frame in frames:
         data_movie_frames.append(frame)
         if self.PREVIEW is True:
            cv2.imshow('pepe', frame)
            cv2.waitKey(30)
      # 75% opact
      image = self.RF.watermark_image(frame,  self.RF.logo_1920, cx,cy, .75)
      frames = fade(frame, image, 10)
      for frame in frames:
         data_movie_frames.append(frame)
         if self.PREVIEW is True:
            cv2.imshow('pepe', frame)
            cv2.waitKey(30)

      # fade to black logo 
      image = self.RF.watermark_image(frame,  self.RF.logo_1920, cx,cy, .95)
      frames = fade(image, black_logo, 20)
      for frame in frames:
         data_movie_frames.append(frame)
         if self.PREVIEW is True:
            cv2.imshow('pepe', frame)
            cv2.waitKey(30)

      data_movie_frames.append(black_logo)
      if self.PREVIEW is True:
         cv2.imshow('pepe', black_logo)
         cv2.waitKey(30)
      frames = hold(black_logo, 50)
      for frame in frames:
         data_movie_frames.append(frame)
         if self.PREVIEW is True:
            cv2.imshow('pepe', frame)
            cv2.waitKey(30)

      for frame in data_movie_frames:
         if self.PREVIEW is True:
            cv2.imshow('pepe', frame)
            cv2.waitKey(30)
      return(data_movie_frames)

   def save_geo_json(self, points, lines):
      for point in points:
         print ("POINT:", point)
      for line in lines:
         print ("LINE:", line)

   def preview_frames(self, frames, wait=30):
      for frame in frames:
         cv2.imshow('pepe', frame)
         cv2.waitKey(wait)

   def review_event_movie(self, event_id):
      # get user input
      self.PREVIEW = True 
      self.MOVIE_FRAMES = []
      last_pic = np.zeros((1080,1920,3),dtype=np.uint8)
      self.load_stations_file()
      event_d, event_t = event_id.split("_")
      event_time = event_t[0:2] + ":" + event_t[2:4] + ":" + event_t[4:6]

      cv2.namedWindow('pepe', cv2.WINDOW_NORMAL)
      cv2.resizeWindow("pepe", 1920, 1080)

      event_day = self.event_id_to_date(event_id)
      self.set_dates(event_day)
      # MEDIA -- get media files from remote stations or wasabi
      self.ev_dir = self.local_evdir + event_id + "/"
      MOVIE_FRAMES_TEMP_FOLDER = self.ev_dir + "MOVIE_FRAMES/"
      if os.path.exists(MOVIE_FRAMES_TEMP_FOLDER) is False:
         os.makedirs(MOVIE_FRAMES_TEMP_FOLDER)

      self.movie_conf_file = self.ev_dir + event_id + "_MOVIE_CONF.json" 
      if os.path.exists(self.movie_conf_file):
         print(self.movie_conf_file)
         self.movie_conf = load_json_file(self.movie_conf_file)
      else:
         self.movie_conf = {}
         self.movie_conf['location'] = input("Enter the location of the fireball")
      if "hd_videos" not in self.movie_conf:
         self.movie_conf['hd_videos'] = {}

      save_json_file(self.movie_conf_file, self.movie_conf)

      event_file = self.ev_dir + event_id + "-event.json"
      good_obs_file = self.ev_dir + event_id + "_GOOD_OBS.json"
      obs_data_file = self.ev_dir + event_id + "_OBS_DATA.json"
      planes_file = self.ev_dir + event_id + "_PLANES.json"

      ignore_file = self.ev_dir + event_id + "_IGNORE.json"
      if os.path.exists(ignore_file) is True:
         self.ignore = load_json_file(ignore_file)
      else:
         self.ignore = []
      print("IG:", self.ignore)
      if os.path.exists(event_file) is True:
         event_data = load_json_file(event_file)

      if os.path.exists(good_obs_file) is True:
         good_obs = load_json_file(good_obs_file)
      if os.path.exists(obs_data_file) is True:
         obs_data = load_json_file(obs_data_file)

      #for s in good_obs:
      #   for o in good_obs[s]:
      #      print("GO", s,o)
      #for o in obs_data:
      #   print("OD", o)


      #print("END EARLY")
      #exit()
      # make the graps and animations part of the movie 
      data_frames = self.event_data_movie(event_id, event_data, good_obs)
      key = input("Data movie made. Press Y to review or enter to continue") 
      if key == "y" or key == "Y":
         for fr in data_frames:
            cv2.imshow('pepe', fr)
            cv2.waitKey(30)

      obs_vids = {}
      station_count = {}
      # compilation of all obs
      for station_id in good_obs:
         for sfile in good_obs[station_id]:
            obs_id = station_id  + "_" + sfile
            date = sfile[0:10]
            year= sfile[0:4]
            local_sd_vid = self.ev_dir + obs_id
            local_hd_vid = local_sd_vid.replace(".mp4", "-1080p.mp4")
            cloud_dir = "/mnt/archive.allsky.tv/" + station_id + "/METEORS/" + year + "/" + date + "/" 
            cloud_hd_vid = cloud_dir + obs_id.replace(".mp4",  "-1080p.mp4")
            if os.path.exists(cloud_hd_vid) is True and os.path.exists(local_hd_vid) is False:
               cmd = "cp " + cloud_hd_vid + " " + local_hd_vid
               print(cmd)
               os.system(cmd)

            if obs_id in self.obs_dict:
               hd_video_file = self.obs_dict[obs_id]['hd_video_file']
               if hd_video_file is None:
                   hd_video_file = "missing"
               remote_hd_vid = self.rurls[station_id] + "/meteors/" + event_day +  "/" + hd_video_file
               if os.path.exists(local_sd_vid):
                  print("   SD", local_sd_vid)
               else:
                  print("   NO LOCAL SD", local_sd_vid)

               if os.path.exists(local_hd_vid):
                  sz, elp = get_file_info(local_hd_vid)
               else:
                  sz = 0 
               
               if os.path.exists(local_hd_vid) and sz > 0:
                  print("   HD", local_hd_vid)
               else:
                  print("   NO LOCAL HD", local_hd_vid, sz)
                  if "noord" in remote_hd_vid:
                     remote_hd_vid = remote_hd_vid.replace("https", "http")
                  cmd = "wget " + remote_hd_vid + " -O " + local_hd_vid
                  print(cmd)
                  os.system(cmd)
               if os.path.exists(local_hd_vid) and sz > 0:
                  obs_vids[obs_id] = local_hd_vid
               else:
                  obs_vids[obs_id] = local_sd_vid
               if station_id in station_count:
                  station_count[station_id] += 1
               else:
                  station_count[station_id] = 1
      self.movie_conf['station_count'] = station_count
      my_text = {}
      my_text[0] = "A bright fireball occured on {:s} at {:s} over {:}.".format(event_day, event_time, self.movie_conf['location'])
      my_text[1] = "The event was observed by {:s} cameras across {:s} stations.".format(str(len(obs_vids.keys())), str(len(station_count)))
      my_text[2] = "Special thanks to the ALLSKY7 operators who recorded the event."

      my_text[0] = "A bright fireball occured over {:s} on {:s} at {:}.".format(self.movie_conf['location'], event_day, event_time )
      my_text[1] = "{:s} cameras across {:s} stations recored the event.".format(str(len(obs_vids.keys())), str(len(station_count)))
      my_text[2] = "Special thanks to the ALLSKY7 operators. "

      credits = []
      for st in station_count:
         photo_credit = self.photo_credits[st] 
         credits.append(st + " " + photo_credit)
         print (" ", st, photo_credit)

      self.movie_conf['photo_credits'] = credits 
      # ready to start the movie?
      language = 'en'

      fps = 25
      RF = RenderFrames()
      VE = VideoEffects()

      base_frame,mx1,my1,mx2,my2 = RF.tv_frame()
      cv2.imshow('pepe', base_frame)
      cv2.waitKey(30)

      # produced by 
      black_frame = np.zeros((1080,1920,3),dtype=np.uint8)
      #produced_by_text_frame = VE.show_text(["Produced by Mike Hankey..."], base_frame, 15, font_size=30, pos_y=480)
      #produced_by_text_frames = fade(black_frame, produced_by_text_frame, 40)
      #frame = produced_by_text_frame
      #self.preview_frames(produced_by_text_frames, 45)

      y_space = 20
      pos_y = int(1080 - (len(credits) * y_space))

      intro = True  
      font_size = 30
      if len(credits) < 9:
         pos_y = 480
      else:
         ddd = len(credits) - 9
         extra = 100 * ddd
         pos_y = 480 - 100
         if pos_y < 50:
            # need 2 columns!
            pos_y = 50
            font_size=20

      if intro is True: 
         credits_frame = VE.show_text(credits, base_frame, 3, font_size=font_size, pos_y=pos_y)         
         #self.preview_frames(credits_frame, 45)

      movie_frames_folder = self.ev_dir + "/movie_frames/"

      if os.path.exists(movie_frames_folder) is False:
         os.makedirs(movie_frames_folder)
      if intro is True: 
         iframes = make_intro(movie_frames_folder)
         for fr in iframes:
         #   cv2.imshow('pepe', fr)
         #   cv2.waitKey(0)
            self.MOVIE_FRAMES.append(fr)
      text_frames_dir = self.ev_dir + "/audio_text/"
      if os.path.exists(text_frames_dir) is False:
         os.makedirs(text_frames_dir)
      if intro is True:

         #for frame in produced_by_text_frames:
         #   self.MOVIE_FRAMES.append(frame)
         #   if self.PREVIEW is True:
         #      cv2.imshow('pepe', frame)
         #      cv2.waitKey(30)
#
#         for i in range(0, 15):
#            self.MOVIE_FRAMES.append(produced_by_text_frame)

         text_frames = VE.type_text([my_text[0]], base_frame, 2, font_size=30, pos_y=480)
         for frame in text_frames:
            self.MOVIE_FRAMES.append(frame)
            if self.PREVIEW is True:
               cv2.imshow('pepe', frame)
               cv2.waitKey(30)
         text_frames = VE.type_text([my_text[1]], base_frame, 2, font_size=30, pos_y=480)
         for frame in text_frames:
            self.MOVIE_FRAMES.append(frame)
            if self.PREVIEW is True:
               cv2.imshow('pepe', frame)
               cv2.waitKey(30)
         text_frames = VE.type_text([my_text[2]], base_frame, 2, font_size=30, pos_y=400)
         for frame in text_frames:
            self.MOVIE_FRAMES.append(frame)
            if self.PREVIEW is True:
               cv2.imshow('pepe', frame)
               cv2.waitKey(30)

      # INTRO IS ALMOST OVER 

      if intro is True:
         trans_frames = fade(frame, credits_frame, 50)
         for cf in trans_frames:
            self.MOVIE_FRAMES.append(cf)
            if self.PREVIEW is True:
               cv2.imshow('pepe', cf)
               cv2.waitKey(30)
            last_pic = cf
     
      for i in range(0, 25):
         self.MOVIE_FRAMES.append(credits_frame)
      # INTRO DONE
      
      # Build / load videos, stacks, ken burns
      last_pic = cv2.resize(last_pic, (1920,1080))
      all_media = self.load_process_media(obs_vids, event_id, last_pic)
      all_media_save = all_media.copy()
      #dict_keys(['video_file', 'stack_file', 'frames', 'stack_image', 
      # 'ken_burns_frames', 'ken_burns_data', 'hd_fns', 'med_sync', 'obs_data'])
      for obv in all_media_save:
         print("OBV", all_media_save[obv].keys())
         print("OBV", all_media_save[obv]['stack_file'])
         if "ken_burns_frames" in all_media_save[obv]:
            del(all_media_save[obv]['ken_burns_frames'])
         del(all_media_save[obv]['frames'])
         if "stack_image" in all_media_save[obv]:
            del(all_media_save[obv]['stack_image'])
         else:
            print(obv, "error missing stack media")
      self.movie_conf['all_media'] = all_media_save
      save_json_file(self.movie_conf_file, self.movie_conf)
      print("ALL MEDIA", all_media.keys())

      print("MOVIE IS READY TO PLAY....")
      input("PRESS [ENTER] TO START")
      #cmd = "./FFF.py imgs_to_vid /mnt/f/EVENTS/2023/05/27/20230527_010911/MOVIE_FRAMES/ 00 /mnt/f/EVENTS/2023/05/27/20230527_010911/MOVIE_FRAMES/20230527_010911_EVENT_MOVIE.mp4 25 28"
      output_movie_file = self.ev_dir + event_id + "_EVENT_MOVIE.mp4" 
      MOVIE_FRAME_NUMBER = 0

      base_frame,mx1,my1,mx2,my2 = RF.tv_frame()
      for dframe in self.MOVIE_FRAMES:
         if len(dframe) == 2:
            sframe, obs_id = dframe
            last_frame = sframe
         else:
            sframe = dframe
            obs_id = None
            last_frame = sframe

         #sframe = self.RF.watermark_image(frame, self.RF.logo_320, 1540, 25, .5, []) 
         #sframe = RF.frame_template("1920_1p", [frame])
        
         cv2.putText(sframe, str(MOVIE_FRAME_NUMBER),  (10,10), cv2.FONT_HERSHEY_SIMPLEX, .4, (255,255,255), 1)
         if MOVIE_FRAME_NUMBER > 200:
            fw = mx2 - mx1
            fh = my2 - my1
            rframe = cv2.resize(sframe, (fw,fh))
            sframe = base_frame.copy()
            sframe[my1:my2,mx1:mx2] = rframe
         print("Saving frame:", MOVIE_FRAME_NUMBER)
         if obs_id is not None:
            desc = obs_id.replace(".mp4", "")
            station_id = obs_id.split("_")[0]
            credits = station_id + " - " + self.photo_credits[station_id]
            length = len(credits) * 17
            #cv2.putText(sframe, str(credits),  (1920 - length,1040), cv2.FONT_HERSHEY_SIMPLEX, .8, (255,255,255), 2)
            cv2.putText(sframe, str(credits),  (1920 - length,1040), cv2.FONT_HERSHEY_DUPLEX, .8, (255,255,255), 1)
         
         save_movie_frame(sframe, MOVIE_FRAME_NUMBER, MOVIE_FRAMES_TEMP_FOLDER)   
         if self.PREVIEW is True:
            cv2.imshow('pepe', sframe)
            cv2.waitKey(30)
         MOVIE_FRAME_NUMBER += 1

      # now add the data frames parts
      # trans into first data frame
      map_frame = cv2.resize(data_frames[0], (1920,1080))
      print(last_frame.shape)
      print(map_frame.shape)
      trans_frames = fade(last_frame, map_frame, 25)
      for frame in trans_frames:
         rframe = cv2.resize(frame, (fw,fh))
         sframe = base_frame.copy()
         sframe[my1:my2,mx1:mx2] = rframe
         save_movie_frame(sframe, MOVIE_FRAME_NUMBER, MOVIE_FRAMES_TEMP_FOLDER)   
         if self.PREVIEW is True:
            cv2.imshow('pepe', sframe)
            cv2.waitKey(30)
         MOVIE_FRAME_NUMBER += 1
      
      # data frames
      for frame in data_frames:
         rframe = cv2.resize(frame, (fw,fh))
         sframe = base_frame.copy()
         sframe[my1:my2,mx1:mx2] = rframe
         save_movie_frame(sframe, MOVIE_FRAME_NUMBER, MOVIE_FRAMES_TEMP_FOLDER)   
         if self.PREVIEW is True:
            cv2.imshow('pepe', sframe)
            cv2.waitKey(30)
         MOVIE_FRAME_NUMBER += 1

      cmd = "./FFF.py imgs_to_vid {:s} 00 {:s} 25 28".format(movie_frames_folder, output_movie_file)
      print(cmd)
      os.system(cmd)

   

   def load_process_media(self, obs_vids, event_id, last_pic=None):
      
      all_media = {}
      for obv in sorted(obs_vids):
         video_file = obs_vids[obv]
         stack_file = obs_vids[obv].replace(".mp4", "-stacked.jpg")
         all_media[obv] = {}
         all_media[obv]['video_file'] = video_file
         all_media[obv]['stack_file'] = stack_file
         all_media[obv]['frames'] = load_frames_simple(video_file, (1920,1080))

         if last_pic is not None:
            print("last_pic", last_pic.shape)
            if len(all_media[obv]['frames']) == 0:
                continue
            print("frame", all_media[obv]['frames'][0].shape)
            extra = slide_left(last_pic, all_media[obv]['frames'][0] , "FF", 0)
            for e in extra:
               self.MOVIE_FRAMES.append(e)
               if self.PREVIEW is True:
                  cv2.imshow('pepe', e)
                  cv2.waitKey(30)

         if os.path.exists(stack_file) is True:
            all_media[obv]['stack_image'] = cv2.imread(stack_file)
         else:
            all_media[obv]['stack_image'] = stack_frames(all_media[obv]['frames'])
         cv2.imwrite(stack_file, all_media[obv]['stack_image'])
 
         roi = [300, 600,800,900]
 
         #all_media[obv]['ken_burns_frames']  

         cframes, kb_data, hd_fns, med_sync = self.ken_burns_effect(obv, all_media[obv]['frames'] )
         try:
            cframes, kb_data, hd_fns, med_sync = self.ken_burns_effect(obv, all_media[obv]['frames'] )
         except:
            continue

         print("MOVIE FRAMES (frames, kb_data, hd_fns):", obv, len(cframes), len(kb_data), len(hd_fns) )
         all_media[obv]['ken_burns_frames']  = cframes
         all_media[obv]['ken_burns_data']  = kb_data 
         all_media[obv]['hd_fns']  = hd_fns 
         all_media[obv]['med_sync']  = med_sync 


         obs_id = obv
         obs = self.obs_dict[obs_id]
         all_media[obv]['obs_data']  = obs 
         datetimes = [row[0] for row in obs['meteor_frame_data']]
         fns = [row[1] for row in obs['meteor_frame_data']]
         sd_fns = fns
         xs = [row[2] for row in obs['meteor_frame_data']]
         ys = [row[3] for row in obs['meteor_frame_data']]
         ints = [row[6] for row in obs['meteor_frame_data']]
         azs = [row[9] for row in obs['meteor_frame_data']]
         els = [row[10] for row in obs['meteor_frame_data']]
             
         fc = 0
         # remove movie banned from obv?
         #MAIN MOVIE HERE
         #for frame in  all_media[obv]['ken_burns_frames']:
         for frame in  all_media[obv]['frames']:
            # only show the ending frames if there is 'action' within 10 frames 
            if fc > min(hd_fns) - 15 or fc > 10:
               start = True
            else:
               start = False 
            if fc <= max(hd_fns) + 10 and start is True:
               self.MOVIE_FRAMES.append((frame, obv))
               if self.PREVIEW is True:
                  cv2.imshow('pepe',  frame)
                  cv2.waitKey(30)
            fc += 1
         last_pic = all_media[obv]['ken_burns_frames'][-1]

      # show ken burns videos stacks

      # show stacks
      for obv in all_media:
         print("STACKS:", obv, all_media[obv])
         if "stack_img" in all_media[obv]:
            this_pic = all_media[obv]['stack_image'] 
         else: 
            this_pic = np.zeros((1080,1920,3),dtype=np.uint8)
         if this_pic.shape[0] != 1080:
            this_pic = cv2.resize(this_pic, (1920,1080))
         if last_pic.shape[0] != 1080:
            last_pic = cv2.resize(last_pic, (1920,1080))
         trans_frames = fade(last_pic, this_pic, 25)
         last_pic = this_pic
         for cf in trans_frames:
            self.MOVIE_FRAMES.append((cf, obv))
            if self.PREVIEW is True:
               cv2.imshow('pepe', cf)
               cv2.waitKey(30)

         # show stack for almost a second
         for q in range(0,20):
            self.MOVIE_FRAMES.append((this_pic, obv))
            if self.PREVIEW is True:
               cv2.imshow('pepe',  all_media[obv]['stack_image'])
               cv2.waitKey(30)
      return(all_media)

   def ken_burns_effect(self, obs_id, frames ):
      # for each frame, zoom into the area a little bit more. 
      # that means we will crop the photo some
      # then resize it to the full size. 
      # to do this we should know the final max size and position and duration

      mask_img = self.auto_mask(frames[0])


      cframes = []
      obs = self.obs_dict[obs_id]
      datetimes = [row[0] for row in obs['meteor_frame_data']]
      fns = [row[1] for row in obs['meteor_frame_data']]
      sd_fns = fns
      xs = [row[2] for row in obs['meteor_frame_data']]
      ys = [row[3] for row in obs['meteor_frame_data']]
      ints = [row[6] for row in obs['meteor_frame_data']]
      azs = [row[9] for row in obs['meteor_frame_data']]
      els = [row[10] for row in obs['meteor_frame_data']]
      print("OBS", obs_id)
      print("XS:", xs)
      print("YS:", ys)
      # refit points?
      if False:
        fxs, fys = fit_and_distribute(xs, ys)
        xs = fxs
        ys = fys

      sync_done = False 
      if "all_media" in self.movie_conf: 
         if obs_id in self.movie_conf['all_media']:
            if "hd_fns" in self.movie_conf['all_media'][obs_id]:
               hd_fns = self.movie_conf['all_media'][obs_id]['hd_fns']
               med_sync = self.movie_conf['all_media'][obs_id]['med_sync']
               sync_done = True

      if sync_done is False:
         try:
            hd_fns, med_sync = self.sync_hd_frames(frames, fns, xs, ys)
         except:
            med_sync = 0
            hd_fns = sd_fns
      
      fns = hd_fns

      dur = len(frames)
      try:
         x1,y1,x2,y2 = min(xs), min(ys), max(xs), max(ys) 
      except:
         x1 = 0
         x2 = 1920
         y1 = 0
         y2 = 1080 
      cx = int((x1 + x2) / 2)
      cy = int((y1 + y2) / 2)


      if cx > x2:
         cx = int((cx - (x2  / 4)))
      else:
         cx = int((cx + (x2  / 4)))
      cy = int((cy + y2 ) / 2)

      cx = xs[0]
      cy = ys[0]
      min_w = x2 - x1
      min_h = y2 - y1
      min_w = 320 
      min_h = 180 
      min_width, min_height = find_resolution(min_w,min_h,all_resolutions)

      # build crop sizes array
      start_size = [1920,1080]
      fc = 0
      last_frame = None
      cx = None 
      cy = None

      # build frame lookup dict
      flookup = {} 
      kb_data = []
      print(fns)
      print(xs)
      print(ys)
      for i in range(0,len(fns)):
         fn = fns[i]
         if i < len(xs):
            x = xs[i]
            y = ys[i]
            flookup[fn] = [x,y]

      for i in range(0,len(frames)):
         # how fast to zoom 
         perc_step = 1 - ((i/(len(frames))) / 2)
         crop_width = 1920 - int((start_size[0] - (start_size[0] * perc_step)))
         crop_height = 1080 - int((start_size[1] - (start_size[1] * perc_step)))
         cw, ch = find_resolution(crop_width,crop_height,all_resolutions)
         frame = frames[i].copy()
         track_frame = cv2.subtract(frame, mask_img) 
         #cv2.imshow('pepe', track_frame)
         #cv2.waitKey(0)
         #if last_frame is not None:
         # real time tracking (not needed here?)
         if False:
            sub = cv2.subtract(track_frame, last_frame)
            sub =  cv2.cvtColor(sub, cv2.COLOR_BGR2GRAY)

            min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(sub)
            thresh_val = 80 
            _, thresh_image = cv2.threshold(sub, thresh_val, 255, cv2.THRESH_BINARY)
            cnts = get_contours_in_image(thresh_image)
            if len(cnts) > 0:
               cx = cnts[0][0] + cnts[0][2]
               cy = cnts[0][1] + cnts[0][3]
               for cnt in cnts:
                  print("CNTs", cnts)
            else:
               print("NO CNTS")
             



         if i in flookup:
            cx,cy = flookup[i] 
            #cy = ys[fc]
            #fc += 1

         if cx is None:
            cx = xs[0] 
            cy = ys[0] 

         # CX is tre track / focus point

         show_frame = frames[i].copy()

         #cv2.circle(show_frame, (cx,cy), int(5), (128,128,128),1)

         if cw < crop_width or ch < crop_height:
            cw = crop_width
            ch = crop_height
         if cw < min_width or ch < min_height:
            cw = min_width
            ch = min_height
          
         nx1 = int(cx - (cw / 2))
         nx2 = int(cx + (cw / 2))
         ny1 = int(cy - (ch / 2))
         ny2 = int(cy + (ch / 2))


         if nx1 <= 0:
            nx1 = 0
            nx2 = cw
         if ny1 <= 0:
            ny1 = 0
            ny2 = ch

         if nx2 >= 1920 :
            nx2 = 1920
            nx1 = 1920 - cw
         if ny2 >= 1080:
            ny2 = 1080 
            ny1 = 1080 - ch
         kb_data.append((i, nx1, ny1, nx2, ny2))
         #cv2.rectangle(show_frame, (int(nx1), int(ny1)), (int(nx2) , int(ny2) ), (255, 255, 255), 2)
         cropped_frame = show_frame[ny1:ny2,nx1:nx2]
         # disabled
         cropped_frame = cv2.resize(cropped_frame, (1920,1080))
         #cv2.imshow('pepe', cropped_frame)
         #cv2.waitKey(30)
         cframes.append(cropped_frame)
         #print("CROP SIZE", i, crop_width, crop_height , cw, ch)
         last_frame = track_frame
      return(cframes, kb_data, hd_fns, med_sync)            

   def sync_hd_frames(self, frames, fns, xs, ys):
      sync_vals = []
      hd_sd_sync = 0
      for i in range(0,len(fns)):
         fn = fns[i]
         x = xs[i]
         y = ys[i]
         if x >= 1920:
            x = 1919
         if y >= 1080:
            y = 1079 
         print(i, fn)
         brightest_frame_val = 0 
         brightest_frame_num = 0
         for fc in range(0, len(frames)):
            frame = frames[fc].copy()
            frame =  cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            val = frame[y,x]
            if val > brightest_frame_val:
               brightest_frame_val = val
               brightest_frame_num = fc 
               #print("  *", fc, val)
            #else:
               #print("   ", fc, val)
         if brightest_frame_num != 0:
            hd_sd_sync = fn - brightest_frame_num 
            sync_vals.append(hd_sd_sync)
         if len(sync_vals) > 50:
            break
         print("Brightest HD frame value {:s} found in HD frame {:s} maps to SD Frame {:s} SYNC=".format(str(brightest_frame_val), str(brightest_frame_num), str(fn)), str(hd_sd_sync))
      med_sync = int(np.median(sync_vals))
      print("MEDIAN SYNC VAL:", med_sync)
      hd_fns = []
      for fn in fns:
         hd_fn = fn - med_sync
         hd_fns.append(hd_fn)
      print("HD FNS", hd_fns)
      for i in range(0,len(fns)):
         fn = fns[i]
         hd_fn = hd_fns[i]
         x = xs[i]
         y = ys[i]

         if hd_fn > 0 and hd_fn < len(frames):
            hd_frame = frames[hd_fn].copy()
            cv2.circle(hd_frame, (x,y), int(5), (128,128,128),1)
            #cv2.imshow("pepe", hd_frame)
            #cv2.waitKey(0)
         else:
            print("HD FRAME DOESN NOT EXIST!", hd_fn)
      return(hd_fns, med_sync) 



   def review_event(self, event_id):
      cv2.namedWindow('pepe')
      cv2.resizeWindow("pepe", self.win_x, self.win_y)
      # the purpose of this function is to JUST get the MEDIA files for the event being reviewed.
      # see review_event_step2 for the remaining 

      # setup vars
      self.event_id = event_id
      self.sync_log = {}
      stack_imgs = []

      # convert id to date
      event_day = self.event_id_to_date(event_id)
      self.set_dates(event_day)
      # MEDIA -- get media files from remote stations or wasabi
      local_event_dir = "/mnt/f/EVENTS/" + self.year + "/" + self.month + "/" + self.dom + "/" + self.event_id + "/" 
      wget_cmds = self.get_event_media(event_id)
      self.fast_cmds(wget_cmds)

      ignore_file = local_event_dir + event_id + "_IGNORE.json"
      if os.path.exists(ignore_file) is True:
         ignore = load_json_file(ignore_file)
      else:
         ignore = []
      self.ignore = ignore

      self.dels = {}
      for out_file in self.sd_clips:
         #print("OUTFILE", out_file)
         for ig in ignore:
            if ig in out_file:
               self.dels[out_file] = 1
               print("IGNORE", out_file)
      for x in self.dels :
         del(self.sd_clips[x])
         print("DELETE:", x)
         
      # MEDIA -- now load frames and make stacks as needed
      for out_file in self.sd_clips:
         sfile = out_file.replace(".mp4", "-stacked.jpg")

         if out_file in self.edits['sd_clips']:
            if "custom_points" in  self.edits['sd_clips'][out_file]:
               self.sd_clips[out_file]['custom_points'] = self.edits['sd_clips'][out_file]['custom_points']
            if "deleted_points" in  self.edits['sd_clips'][out_file]:
               self.sd_clips[out_file]['deleted_points'] = self.edits['sd_clips'][out_file]['deleted_points']
            if "frame_data" in  self.edits['sd_clips'][out_file]:
               self.sd_clips[out_file]['frame_data'] = self.edits['sd_clips'][out_file]['frame_data']

         if os.path.exists(local_event_dir + sfile) is False:
            frames = load_frames_simple(local_event_dir + out_file)
            if len(frames) > 5:
               red_file = local_event_dir + out_file.replace(".mp4", "-reduced.json")
               if os.path.exists(red_file) is True:
                  try:
                     red_data = load_json_file(red_file) 
                  except:
                     red_data = {}
                     red_data['meteor_frame_data'] = []
                  self.sd_clips[out_file]['mfd'] = red_data['meteor_frame_data']

               simg = stack_frames(frames)
               cv2.imwrite(local_event_dir + sfile, simg)
               self.sd_clips[out_file]['stack_img'] = simg 
               self.sd_clips[out_file]['frames'] = frames 
               self.sd_clips[out_file]['status'] = True
               stack_imgs.append(simg)
            else:
               self.sd_clips[out_file]['status'] = False
         else:
            self.sd_clips[out_file]['stack_img'] = cv2.imread(local_event_dir + sfile)
            stack_imgs.append(self.sd_clips[out_file]['stack_img'])
            self.sd_clips[out_file]['frames'] = []
            self.sd_clips[out_file]['status'] = True
  
      return() 


   def obs_images_panel(self, map_img, event_data, obs_data, obs_imgs,marked_imgs):

      # MRH LAST 3/30/23
      # sort obs by longest and also remove dupes 
      # decide thumb size based on number of images! 
      if len(obs_imgs) <= 4:
         tw = int(1920/2) 
         th = int(1080/2)
      elif 4 < len(obs_imgs) <= 12:
         tw = 640 
         th = 360 
      elif 9 < len(obs_imgs) <= 30:
         tw = 384
         th = 216 

      else:
         tw = 320 
         th = 180

      gimg = np.zeros((1080,1920,3),dtype=np.uint8)
      gmimg = np.zeros((1080,1920,3),dtype=np.uint8)
      cc = 0
      rc = 0
      dupes = {}
      ranked_obs = []
      for obs_id in obs_imgs:
         flen = len(obs_data[obs_id]['xs'])
         ranked_obs.append((obs_id, flen))

      ranked_obs = sorted(ranked_obs, key=lambda x: (x[1]), reverse=True)

      for obs_id, flen in ranked_obs:
         stid = obs_id.split("_")[0]
         (f_datetime, cam_id, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(obs_id.replace(stid + "_" , ""))
         dkey = stid + "_" + cam_id 
         if dkey in dupes:
            continue
         else:
            dupes[dkey] = 1


         if obs_id + ".mp4" in self.obs_dict:
            calib = self.obs_dict[obs_id + ".mp4"]['calib']

         if obs_id not in obs_imgs:
            continue
         if obs_imgs[obs_id] is None:
            obs_imgs[obs_id] = np.zeros((1080,1920,3),dtype=np.uint8)

         img = obs_imgs[obs_id].copy()
         marked_img = cv2.resize(obs_imgs[obs_id], (1920,1080))
         rx1,ry1,rx2,ry2 = self.get_roi(obs_data[obs_id]['xs'], obs_data[obs_id]['ys'])
         x1 = cc * tw 
         x2 = x1 + tw 
         y1 = rc * th 
         y2 = y1 + th 

         cv2.rectangle(marked_img, (int(rx1), int(ry1)), (int(rx2) , int(ry2) ), (255, 255, 255), 2)

         if x2 > 1920:
            rc += 1
            y1 += th 
            y2 += th 
            x1 = 0
            x2 = tw 
            cc = 1
         else: 
            cc += 1
         try:
            thumb = cv2.resize(img, (tw,th))
            marked_thumb = cv2.resize(marked_img, (tw,th))
         except:
            thumb = np.zeros((th,tw,3),dtype=np.uint8)
            marked_thumb = np.zeros((th,tw,3),dtype=np.uint8)

         try:
            gimg[y1:y2,x1:x2] = thumb
            gmimg[y1:y2,x1:x2] = thumb 
         except:
            print("EXCEPTION WITH ROI:", x1,y1,x2,y2)


         try:
            gimg[y1:y2,x1:x2] = thumb
            gmimg[y1:y2,x1:x2] = marked_thumb
         except:
            print(x1,y1,x2,y2)
         cv2.imshow('pepe', gmimg)
         cv2.waitKey(60)



      cv2.imshow('pepe', gmimg)
      cv2.waitKey(60)

      # remove dupes from obs imgs
      for dk in dupes:
         if dk in obs_imgs:
            del obs_imgs[dk]

      temp = []

      gallery_image = gimg

      simg = np.zeros((1080,1920,3),dtype=np.uint8)
      map_img = cv2.resize(map_img, (1280,720))
      # do layout based on number of images availbable

      if len(obs_imgs) == 2:
         map_img = cv2.resize(map_img, (960,540))
         i = 0
         # map center would be (1920 / 2 ) - (960/2)
         x1 =  int((1920 / 2 ) - (960/2))
         x2 =  int((1920 / 2 ) + (960/2))
         simg[540:1080,x1:x2] = map_img
         for key in obs_imgs:
            obs_id = key
            show_img = cv2.resize(marked_imgs[key], (1920,1080))
            rx1,ry1,rx2,ry2 = self.get_roi(obs_data[key]['xs'], obs_data[key]['ys'])
            obs_imgs[key] = cv2.resize(show_img, (960,540))
            station_id = obs_id.split("_")[0]
            obs_datetime = obs_data[obs_id]['times'][0]
            label = station_id + " " + obs_datetime
            if i == 0:
               x1 = 0
               x2 = 960 
               y1 = 0
               y2 = 540
               simg[y1:y2,x1:x2] = cv2.resize(show_img, ((x2-x1), (y2-y1)))
               cv2.putText(simg, label,  (x1,y2-10), cv2.FONT_HERSHEY_SIMPLEX, .6, (0,255,0), 1)
            if i == 1:
               x1 = 960
               x2 = 1920 
               y1 = 0
               y2 = 540
               simg[y1:y2,x1:x2] = cv2.resize(show_img, ((x2-x1), (y2-y1)))
               cv2.putText(simg, label,  (x1, y2-10), cv2.FONT_HERSHEY_SIMPLEX, .6, (0,255,0), 1)
            i+= 1
      
      elif len(obs_imgs) == 3:
         map_img = cv2.resize(map_img, (960,540))
         i = 0
         # map center would be (1920 / 2 ) - (960/2)
         x1 = 960 
         x2 = 1920 
         y1 = 540
         y2 = 1080 

         simg[y1:y2,x1:x2] = map_img
         for key in obs_imgs:
            obs_id = key

            rx1,ry1,rx2,ry2 = self.get_roi(obs_data[key]['xs'], obs_data[key]['ys'])
            show_img = cv2.resize(marked_imgs[key].copy(), (1920,1080))
            cv2.rectangle(show_img, (int(rx1), int(ry1)), (int(rx2) , int(ry2) ), (255, 255, 255), 2)
            cv2.imshow('pepe', show_img)
            cv2.waitKey(40)


            obs_imgs[key] = cv2.resize(obs_imgs[key], (960,540))
            marked_imgs[key] = cv2.resize(show_img, (960,540))
            station_id = obs_id.split("_")[0]
            obs_datetime = obs_data[obs_id]['times'][0]
            label = station_id + " " + obs_datetime
            if i == 0:
               x1 = 0
               x2 = 960 
               y1 = 0
               y2 = 540
               #simg[y1:y2,x1:x2] = obs_imgs[key]
               simg[y1:y2,x1:x2] = cv2.resize(show_img, ((x2-x1), (y2-y1)))
               cv2.putText(simg, label,  (x1,y2-10), cv2.FONT_HERSHEY_SIMPLEX, .6, (0,255,0), 1)
            if i == 1:
               x1 = 960
               x2 = 1920 
               y1 = 0
               y2 = 540
               #simg[y1:y2,x1:x2] = obs_imgs[key]
               simg[y1:y2,x1:x2] = cv2.resize(show_img, ((x2-x1), (y2-y1)))
               cv2.putText(simg, label,  (x1, y2-10), cv2.FONT_HERSHEY_SIMPLEX, .6, (0,255,0), 1)
            if i == 2:
               x1 = 0 
               x2 = 960 
               y1 = 540
               y2 = 1080 
               #simg[y1:y2,x1:x2] = obs_imgs[key]
               simg[y1:y2,x1:x2] = cv2.resize(show_img, ((x2-x1), (y2-y1)))
               cv2.putText(simg, label,  (x1, y2-10), cv2.FONT_HERSHEY_SIMPLEX, .6, (0,255,0), 1)
            i+= 1

      else:
         map_img = cv2.resize(map_img, (1280,720))
         simg[0:720,0:1280] = map_img
         x1 = 1280
         x2 = 1920
         y1 = 0
         y2 = 360
         i = 0
         for key,val in ranked_obs:
            obs_id = key

            rx1,ry1,rx2,ry2 = self.get_roi(obs_data[key]['xs'], obs_data[key]['ys'])
            show_img = cv2.resize(marked_imgs[key].copy(), (1920,1080))
            cv2.rectangle(show_img, (int(rx1), int(ry1)), (int(rx2) , int(ry2) ), (255, 255, 255), 2)
            cv2.imshow('pepe', show_img)
            cv2.waitKey(40)

            try:
               obs_imgs[key] = cv2.resize(obs_imgs[key], (960,540))
            except:
               src_img = np.zeros((540,960,3),dtype=np.uint8)
            try:
               marked_imgs[key] = cv2.resize(show_img, (960,540))
            except:
               marked_imgs[key] = np.zeros((540,960,3),dtype=np.uint8)
            station_id = obs_id.split("_")[0]
            obs_datetime = obs_data[obs_id]['times'][0]
            label = station_id + " " + obs_datetime

            if obs_imgs[key] is None:
               obs_imgs[key] = np.zeros((360,640,3),dtype=np.uint8)

            if obs_imgs[key].shape[0] != 360:
               obs_imgs[key] = cv2.resize(obs_imgs[key], (640,360))
            if i == 0:
               #simg[y1:y2,x1:x2] = obs_imgs[key]
               simg[y1:y2,x1:x2] = cv2.resize(show_img, ((x2-x1), (y2-y1)))
               cv2.putText(simg, label,  (x1,y2-10), cv2.FONT_HERSHEY_SIMPLEX, .6, (0,255,0), 1)
            if i == 1:
               #simg[y1+360:y2+360,x1:x2] = obs_imgs[key]
               simg[y1+360:y2+360,x1:x2] = cv2.resize(show_img, ((x2-x1), (y2-y1)))
               cv2.putText(simg, label,  (x1,y2+360-10), cv2.FONT_HERSHEY_SIMPLEX, .6, (0,255,0), 1)
            if i == 2:
               #simg[y1+720:y2+720,x1:x2] = obs_imgs[key]
               simg[y1+720:y2+720,x1:x2] = cv2.resize(show_img, ((x2-x1), (y2-y1)))
               cv2.putText(simg, label,  (x1,y2+720-10), cv2.FONT_HERSHEY_SIMPLEX, .6, (0,255,0), 1)
            if i == 3:
               #simg[720:1080,0:640] = obs_imgs[key]
               y1 = 720
               y2 = 1080
               x1 = 0
               x2 = 640
               simg[y1:y2,x1:x2] = cv2.resize(show_img, ((x2-x1), (y2-y1)))
               cv2.putText(simg, label,  (10, y2-10), cv2.FONT_HERSHEY_SIMPLEX, .6, (0,255,0), 1)
            if i == 4:
               y1 = 720
               y2 = 1080
               x1 = 640
               x2 = 1280 
               #simg[720:1080,640:1280] = obs_imgs[key]
               simg[y1:y2,x1:x2] = cv2.resize(show_img, ((x2-x1), (y2-y1)))
               cv2.putText(simg, label,  (640+10, y2-10), cv2.FONT_HERSHEY_SIMPLEX, .6, (0,255,0), 1)
            i += 1

      simg = self.RF.watermark_image(simg, self.RF.logo_320, 1590, 10, .5, []) 
      return(simg, gallery_image)

   def get_roi(self, xs, ys):
      w = (max(xs) - min(xs)) + 50
      h = (max(ys) - min(ys)) + 50
      if w > h:
         h = w
      else:
         w = h
      x1 = int(np.mean(xs) - int(w/2) )
      y1 = int(np.mean(ys) - int(h/2) )

      if x1 < 0:
         x1 = 0
      if y1 < 0:
         y1 = 0
      x2 = int(x1 + w)
      y2 = int(y1 + h)
      if x2 > 1920:
         x2 = 1920 
         x1 = 1920 - w
      if y2 > 1080:
         y2 = 1080 
         y1 = 1080 - h
      return(int(x1),int(y1),int(x2),int(y2))


   def load_obs_images(self, obs_data):
      obs_imgs = {}
      marked_imgs = {}
      roi_imgs = {}
      ai_imgs = {}
      found = False
      for obs_id in obs_data:
         skip = False
         if "image_file" in obs_data[obs_id]:
            marked_file = obs_data[obs_id]['image_file'].replace(".jpg", "-marked.jpg")
            roi_file = obs_data[obs_id]['image_file'].replace(".jpg", "-roi.jpg")
         else:
            marked_file = None
            roi_file = None


         if marked_file is not None and os.path.exists(obs_data[obs_id]['image_file']) :
            obs_imgs[obs_id] = cv2.imread(obs_data[obs_id]['image_file'])
            found = True
            obs_data[obs_id]['media_res'] = "360p" 
         elif marked_file is not None and os.path.exists(obs_data[obs_id]['image_file'].replace("-stacked.jpg","-prev.jpg")):
            obs_imgs[obs_id] = cv2.imread(obs_data[obs_id]['image_file'].replace("-stacked.jpg","-prev.jpg"))
            found = True
            obs_data[obs_id]['media_res'] = "180p" 



         if marked_file is not None and os.path.exists(marked_file) is True:
            marked_imgs[obs_id] = cv2.imread(marked_file) 
            roi_imgs[obs_id] = cv2.imread(roi_file) 
            skip = True

         # only do this if the marked image is not already done!
         if found is True and skip is False:

            if obs_id in obs_imgs:
               try:
                  src_img = cv2.resize(obs_imgs[obs_id].copy(), (1920,1080))
                  show_img = src_img.copy()
               except:
                  src_img = np.zeros((1080,1920,3),dtype=np.uint8)
                  show_img = np.zeros((1080,1920,3),dtype=np.uint8)
            else:
               src_img = np.zeros((1080,1920,3),dtype=np.uint8)
               show_img = np.zeros((1080,1920,3),dtype=np.uint8)

            # get roi (this should be the entire area of meteor only). 
            rx1,ry1,rx2,ry2 = self.get_roi(obs_data[obs_id]['xs'], obs_data[obs_id]['ys'])
            mx = int(np.mean(obs_data[obs_id]['xs']))
            my = int(np.mean(obs_data[obs_id]['ys']))

            roi_img = src_img[ry1:ry2,rx1:rx2] 
            cv2.imwrite(roi_file, roi_img)

            gray_img =  cv2.cvtColor(src_img, cv2.COLOR_BGR2GRAY)

            gray_roi = gray_img[ry1:ry2,rx1:rx2] 
            min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(gray_roi)
      
            # V2 ROI is 64/64
            # V1 ROI is 224/224!

            ax1 = rx1 + mx - 112
            ax2 = rx1 + mx + 112
            ay1 = ry1 + my - 112
            ay2 = ry1 + my + 112

            w = ax2 - ax1
            h = ay2 - ay1
            if ax1 < 0:
               ax1 = 0
               ax2 = w
            if ay1 < 0:
               ay1 = 0
               ay2 = h
            if ax2 > 1920:
               ax2 = 1920
               ax1 = 1920 - w
            if ay2 > 1080:
               ay2 = 1080 
               ay1 = 1080 - h


            ai_img = src_img[ay1:ay2,ax1:ax2] 
            ai_imgs[obs_id] = ai_img
            roi_imgs[obs_id] = roi_img

            # image or image_file
            ai_resp = self.check_ai_img(ai_img, None)


            if "meteor_prev_yn" in ai_resp:
               if ai_resp['meteor_prev_yn'] > ai_resp['meteor_yn']:
                  ai_resp['meteor_yn'] = ai_resp['meteor_prev_yn']
            else:
               print("NO MYN AI_RESP:", ai_resp)
               ai_resp = {}
               ai_resp['meteor_yn'] = 51
               ai_resp['fireball_yn'] = 51
               ai_resp['mc_class'] = "meteor"
               ai_resp['mc_class_conf'] = 51
               #exit()
            class_data =  [
                ['Meteor', ai_resp['meteor_yn']], 
                ['Fireball', ai_resp['fireball_yn']], 
                [ai_resp['mc_class'], ai_resp['mc_class_conf']] 
                ]


            class_data = sorted(class_data, key=lambda x: (x[1]), reverse=True)
            obs_data[obs_id]['ai_resp'] = ai_resp
            obs_data[obs_id]['ai_class'] = class_data

            # save off all files and results for future learning?
            st = obs_id.split("_")[0]
            temp = obs_id.replace(st + "_", "")

            date = temp[0:10]
            self.learning_dir = "/mnt/f/AI/DATASETS/NETWORK/" + date + "/" + class_data[0][0] + "/"
            if os.path.exists(self.learning_dir) is False:
               os.makedirs(self.learning_dir)
            learn_file = obs_id.replace(".mp4", "") + "_" + str(ax1) + "_" + str(ay1) + "_" + str(ax2) + "_" + str(ay2) + ".jpg"
            cv2.imwrite(self.learning_dir + learn_file, ai_img)

            cv2.rectangle(show_img, (int(rx1), int(ry1)), (int(rx2) , int(ry2) ), (255, 255, 255), 2)

            if "ai_class" in obs_data[obs_id]:
               rc = 0
               for row in obs_data[obs_id]['ai_class']:
                  label, perc = row
                  offset = rc * 30
                  text = label.upper() + " " + str(round(perc,1)) + "%"
                  cv2.putText(show_img, text,  (rx2+20,ry1+10+offset), cv2.FONT_HERSHEY_SIMPLEX, .8, (0,255,0), 2)
                  rc += 1


            marked_imgs[obs_id] = show_img
            cv2.imwrite(marked_file, show_img, [cv2.IMWRITE_JPEG_QUALITY, 70])


      return(obs_imgs, marked_imgs, roi_imgs, ai_imgs, obs_data)

#   def fetch_video(self, obs_id, output_dir):
#      # try to fetch available videos for an obs id and copy to local output dir 
#      # look in these spots in this order
#      # wasabi, then host (IP or VPN), then if all fail, make/log a "host request"
#      print("FETCH VIDEO")

   def review_obs_frames(self, obs_data):
      # review frame x,y positions to sanity check them (maybe fix)
      #for sd_vid in self.sd_clips:
      #   if "frames" in self.sd_clips:
      #      print("SD CLIP:", sd_vid, len(self.sd_clips[sd_vid]['frames']))
      #   else:
      #      print("SD CLIP:", sd_vid, 0, "FRAMES")

     

      for r in obs_data:
         event_id, station_id, obs_id, fns, times, xs, ys, azs, els, ints, \
            status, ignore, ai_confirmed, human_confirmed, ai_data, prev_uploaded,sd_vid_file = r
         sd_vid = sd_vid_file.split("/")[-1]
         fd = {}
         if len(fns) == 0:
            print("ERROR: NO REDUCTION FOR OBS", obs_id, fns, xs, ys)
         if sd_vid not in self.sd_clips:

            self.sd_clips[sd_vid] = {}
            #print("SD CLIPS:", self.sd_clips.keys())
         if "roi_frames" not in self.sd_clips[sd_vid]:
            self.sd_clips[sd_vid]['roi_frames'] = []
         if "tracking_frames" not in self.sd_clips[sd_vid]:
            self.sd_clips[sd_vid]['tracking_frames'] = []

         for i in range(0,len(fns)):
            fn = int(fns[i])
            fd[fn] = {}
            fd[fn]['time'] = times[i]
            fd[fn]['x'] = xs[i]
            fd[fn]['y'] = ys[i]
            fd[fn]['azs'] = azs[i]
            fd[fn]['els'] = els[i]
            fd[fn]['ints'] = ints[i]
            rx1,ry1,rx2,ry2 = self.get_roi(xs, ys)
            fx1, fy1, fx2, fy2 = focus_area(rx1,ry1,rx2,ry2)
            mid_x = int((rx1 + rx2) / 2)
            mid_y = int((ry1 + ry2) / 2)
            if mid_x > 1920 / 2:
               hud_side = "left"
               hx1 = 0
               hx2 = 400
               hy1 = 0
               hy2 = 800
            else:
               hx1 = 1920 - 400
               hx2 = 1920 
               hy1 = 0
               hy2 = 800
               hud_side = "right"
 
         if os.path.exists(sd_vid_file) :
            frames = load_frames_simple(sd_vid_file)
            fc = 0
            for fr in frames:
               ofr = cv2.resize(fr, (1920,1080))
               fr = cv2.resize(fr, (1920,1080))
               cv2.rectangle(fr, (int(rx1), int(ry1)), (int(rx2) , int(ry2) ), (255, 255, 255), 2)
               cv2.rectangle(fr, (int(fx1), int(fy1)), (int(fx2) , int(fy2) ), (255, 255, 255), 2)
               if fc in fd:
                  show_fr = fr.copy()
                  mx = int(float(fd[fc]['x']))
                  my = int(float(fd[fc]['y']))

                  hud_frame = np.zeros((800,400,3),dtype=np.uint8)

                  bx1,by1,bx2,by2 = bound_cnt(mx, my,1920, 1080, 100) 
                  tracking_frame = ofr[by1:by2,bx1:bx2] 
                  roi_frame = ofr[ry1:ry2,rx1:rx2] 
                  self.sd_clips[sd_vid]['roi_frames'].append(roi_frame)
                  self.sd_clips[sd_vid]['tracking_frames'].append(tracking_frame)

                  try:
                     tracking_frame = cv2.resize(tracking_frame, (400,400))
                     roi_frame = cv2.resize(roi_frame, (400,400))
                     hud_frame[0:400,0:400] = roi_frame 
                     hud_frame[400:800,0:400] = tracking_frame 
                  except:
                     print("Track failed")

                  #cv2.imshow("roi", hud_frame)

                  radius = 5
                  cv2.circle(show_fr, (mx,my), int(radius), (128,128,128),1)
                  show_fr = self.crosshair(show_fr, int(mx),int(my))
                  show_fr[hy1:hy2,hx1:hx2] = hud_frame 
                  cv2.putText(show_fr, obs_id,  (20,20), cv2.FONT_HERSHEY_SIMPLEX, .8, (255,255,255), 2)
                  cv2.imshow('pepe', show_fr)
                  cv2.waitKey(0)

               else:
                  cv2.putText(fr, obs_id,  (20,20), cv2.FONT_HERSHEY_SIMPLEX, .8, (255,255,255), 2)
                  cv2.imshow('pepe', fr)
                  cv2.waitKey(0)
               fc += 1
            cv2.waitKey(0)
         
         else:
            print("NO VIDEO FILE!", sd_vid_file)
            time.sleep(5)

      if False:
         for sdv in self.sd_clips:
            #print(sdv)
            if "roi_frames" in self.sd_clips[sdv]:
            
               for fr in self.sd_clips[sdv]['roi_frames']:
                  fr = cv2.resize(fr, (1200,1200))
                  cv2.imshow('pepe', fr)
                  cv2.waitKey(150)

   def event_timeline (self, event_day):
      self.set_dates(event_day)
      tdata = ""
      count = 1
      for ev in self.all_events:
         if len(ev['start_datetime']) > 0:
            if len(ev['start_datetime'][0]) > 0:
               evtime = min(ev['start_datetime'][0])
               if tdata != "":
                  tdata += ",\n"
               desc = "Item " + str(count)
               tdata += "{id: " + "{:s}, content: '{:s}', start: '{:s}'".format(str(count), desc, evtime) + "}"
               count += 1

      out = """
        <!doctype html>
        <html>
        <head>
        <title>Timeline</title>
        <script type="text/javascript" src="https://unpkg.com/vis-timeline@latest/standalone/umd/vis-timeline-graph2d.min.js"></script>
        <link href="https://unpkg.com/vis-timeline@latest/styles/vis-timeline-graph2d.min.css" rel="stylesheet" type="text/css" />
        <style type="text/css">
            #visualization {
            width: 600px;
            height: 400px;
            border: 1px solid lightgray;
            }
        </style>
        </head>
        <body>
        <div id="visualization"></div>
        <script type="text/javascript">
        // DOM element where the Timeline will be attached
        var container = document.getElementById('visualization');
        
        // Create a DataSet (allows two way data-binding)
        var items = new vis.DataSet([ """ + tdata + """
        ]);

        // Configuration for the Timeline
        var options = {};

        // Create a Timeline
        var timeline = new vis.Timeline(container, items, options);
        </script>
        </body>
        </html>
      """
      fp = open("/mnt/ams2/timeline.html", "w")
      fp.write(out)
      fp.close()

   def crosshair(self, img, x,y):
      cv2.line(img, (int(x-50),int(y)), (int(x+50),int(y)), (255,255,255), 1)
      cv2.line(img, (int(x),int(y-50)), (int(x),int(y+50)), (255,255,255), 1)
      return(img)


   def review_event_step2(self):
      # drive this 100% from DB
      # get all current obs data
      # load stack imgs while you go

      # purpose here is to make the map file and multi-image review
      # if it is already done we can just return?
      # we should load it and return it though?


      self.load_stations_file()

      force = True 

      event_preview_dir = self.local_evdir + "/PREV/" 
      cloud_event_preview_dir = self.cloud_evdir + "/PREV/"
   
      event_preview_file = event_preview_dir + self.event_id + ".jpg"
      cloud_event_preview_file = cloud_event_preview_dir + self.event_id + ".jpg"

      if os.path.exists(event_preview_dir) is False:
         os.makedirs(event_preview_dir)
      if os.path.exists(cloud_event_preview_dir) is False:
         os.makedirs(cloud_event_preview_dir)

      obs_data_file = self.local_evdir + self.event_id + "/" + self.event_id + "_OBS_DATA.json"
      event_data_file = self.local_evdir + self.event_id + "/" + self.event_id + "_EVENT_DATA.json"
      map_img_file = self.local_evdir + self.event_id + "/" + self.event_id + "_MAP_FOV.jpg"
      review_img_file = self.local_evdir + self.event_id + "/" + self.event_id + "_REVIEW.jpg"
      gallery_img_file = self.local_evdir + self.event_id + "/" + self.event_id + "_GALLERY.jpg"
      self.map_kml_file = self.local_evdir + self.event_id + "/" + self.event_id + "_OBS_MAP.kml"
      self.planes_file = self.local_evdir + self.event_id + "/" + self.event_id + "_PLANES.json"

      if os.path.exists(self.planes_file) is True:
         self.planes = load_json_file(self.planes_file)
      else:
         self.planes = None
      # if the files exist already remove them
      if os.path.exists(map_img_file) is True:
         os.system("rm " + map_img_file)
      if os.path.exists(review_img_file) is True:
         os.system("rm " + review_img_file)

      #   everything is done already skip???
      #   if force is False and os.path.exists(obs_data_file) is True and os.path.exists(event_data_file) is True and os.path.exists(review_img_file) is True:
      #   obs_data = load_json_file(obs_data_file)
      #   event_data = load_json_file(event_data_file)
      #   map_img = cv2.imread(map_img_file)
      #   review_img = cv2.imread(review_img_file)
      #   event_data, obs_data, map_img,obs_imgs = self.get_event_obs()
      #   obs_imgs, marked_imgs, roi_imgs, ai_imgs, obs_data = self.load_obs_images(obs_data) 
      #   return(review_img, map_img, obs_imgs, marked_imgs, event_data, obs_data)
      #else:

      if True:
         event_data, obs_data1, map_img, obs_imgs = self.get_event_obs()
         obs_imgs, marked_imgs, roi_imgs, ai_imgs, obs_data = self.load_obs_images(obs_data1) 
         temp = event_data_file.split("/")[-1]
         edir = event_data_file.replace(temp, "")
         if os.path.exists(edir) is False:
            os.makedirs(edir)
         print("Saving json")
         save_json_file(event_data_file, event_data)
         save_json_file(obs_data_file, obs_data, True)
         cv2.imwrite(map_img_file, map_img, [cv2.IMWRITE_JPEG_QUALITY, 70])
         print("Saved json and wrote map")

     

      if "2d_status" not in event_data:
         event_data = self.get_2d_status(event_data, obs_data)

      ob_len = []
      for obs_id in obs_data:
         dur = len(obs_data[obs_id]['times'])
         ob_len.append((obs_id,dur))
      ob_len = sorted(ob_len, key=lambda x: x[1], reverse=True)
      obs_id,dur = ob_len[0]
      if obs_id in roi_imgs:
         roi_img = roi_imgs[obs_id].copy()
         if obs_id in obs_imgs:
            stack_img = obs_imgs[obs_id].copy()
            marked_img = marked_imgs[obs_id].copy()
         else:
            stack_img = np.zeros((1080,1920,3),dtype=np.uint8)
            marked_img = np.zeros((1080,1920,3),dtype=np.uint8)
         if obs_id + ".mp4" not in self.sd_clips:
            self.sd_clips[obs_id + ".mp4"] = {}

         self.sd_clips[obs_id + ".mp4"]['roi_img'] = roi_img
         self.sd_clips[obs_id + ".mp4"]['stack_img'] = stack_img
         self.sd_clips[obs_id + ".mp4"]['marked_img'] = marked_img 
         #roi_img = cv2.resize(roi_imgs[obs_id], (200,200))

         #cv2.imshow('roi', roi_img)
         #cv2.waitKey(30)
         cv2.imwrite(event_preview_file, roi_img)
         print("WROTE", event_preview_file)
         if os.path.exists(cloud_event_preview_file):
            os.system("cp " + event_preview_file + " " + cloud_event_prevew_file)
      else:
         print("ROI IMAGE MISSING FAILURE!", roi_imgs.keys())


      simg, gallery_image = self.obs_images_panel(map_img, event_data, obs_data, obs_imgs, marked_imgs)

      if "traj" in event_data:
         (sol_status, v_init, v_avg, start_ele, end_ele, a, e) = self.eval_sol(event_data)
         event_data['event_status'] = sol_status

      if event_data['2d_status'] == "FAILED":
         cv2.putText(simg, "INVALID 2D EVENT",  (20,20), cv2.FONT_HERSHEY_SIMPLEX, .8, (0,0,255), 2)
      else:
         cv2.putText(simg, "VALID 2D EVENT",  (20,20), cv2.FONT_HERSHEY_SIMPLEX, .8, (0,255,0), 2)
      if "BAD" in event_data['event_status'] :
         cv2.putText(simg, event_data['event_status'],  (20,60), cv2.FONT_HERSHEY_SIMPLEX, .8, (0,0,255), 2)
      else:
         cv2.putText(simg, event_data['event_status'],  (20,60), cv2.FONT_HERSHEY_SIMPLEX, .8, (0,255,0), 2)

      cv2.imwrite(review_img_file, simg, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
      cv2.imwrite(gallery_img_file, gallery_image, [int(cv2.IMWRITE_JPEG_QUALITY), 70])

      self.ignored_obs = {}
      if True:
         sql = """SELECT event_id, station_id, obs_id, fns, times, xs, ys, azs, els, ints, 
                       status, ignore, ai_confirmed, human_confirmed, ai_data, prev_uploaded 
                  FROM event_obs
                 WHERE event_id = ?
              ORDER BY obs_id
              """
         vals = [self.event_id]
         self.cur.execute(sql, vals)
         rows = self.cur.fetchall()
         obs_db = []
         stack_imgs = []
         not_found = []
         stack_imgs_dict = {}

         for row in rows:
            (event_id, station_id, obs_id, fns, times, xs, ys, azs, els, ints, \
               status, ignore, ai_confirmed, human_confirmed, ai_data, prev_uploaded ) = row
            ig = False
            for ig in self.ignore:
               if ig in obs_id:
                  self.ignored_obs[obs_id] = (event_id, station_id, obs_id, fns, times, xs, ys, azs, els, ints, \
                     status, ignore, ai_confirmed, human_confirmed, ai_data, prev_uploaded ) 
                  ig = True
                  continue
            if ig is True:
               continue
            times = json.loads(times)
            fns = json.loads(fns)
            xs = json.loads(xs)
            ys = json.loads(ys)
            azs = json.loads(azs)
            els = json.loads(els)
            ints = json.loads(ints)
            sd_vid_file = self.ev_dir + obs_id + ".mp4"
            stack_file = self.ev_dir + obs_id + "-stacked.jpg"
            obs_db.append((event_id, station_id, obs_id, fns, times, xs, ys, azs, els, ints, \
               status, ignore, ai_confirmed, human_confirmed, ai_data, prev_uploaded,sd_vid_file ))
            if os.path.exists(stack_file):
               stack_img = cv2.imread(stack_file)
               stack_img = cv2.resize(stack_img, (1920,1080))
               stack_imgs.append((stack_file, stack_img))
               stack_imgs_dict[obs_id] = stack_img
            else:
               stack_img = np.zeros((1080,1920,3),dtype=np.uint8)
               stack_imgs_dict[obs_id] = stack_img 
               not_found.append((stack_file, stack_img))

      # review_frames review frames
      if True:
         self.review_obs_frames(obs_db)
      cv2.imshow("pepe", simg)
      cv2.waitKey(30)

      return(simg, map_img, obs_imgs, marked_imgs, event_data, obs_data)

   def get_2d_status(self, event_data, obs_data):
      bad_obs = 0
      good_obs = 0
      for obs_id in obs_data:
         if obs_data[obs_id]['ignore'] is True:
            bad_obs+= 1
         else: 
            good_obs += 1
      if good_obs <= 1:
         event_data['2d_status'] = "FAILED"
      else:
         event_data['2d_status'] = str(good_obs) + " GOOD 2D STATIONS"

      return(event_data)

   def make_event_summary_image(self, edited_files, good_files, ignored_files, missing_files):
      edited_imgs = []
      good_imgs = []
      ignore_imgs = []
      missing_imgs = []
      for sd_vid in edited_files:
         stack_file = self.ev_dir + sd_vid.replace(".mp4", "-stacked.jpg")
         if os.path.exists(stack_file) is True:
            stack_img = cv2.imread(stack_file)
            edited_imgs.append(stack_img)
            print("EDITED FOUND", stack_file)
         else:
            print("EDITED missing stack", stack_file)

      for sd_vid in good_files:
         stack_file = self.ev_dir + sd_vid.replace(".mp4", "-stacked.jpg")
         if os.path.exists(stack_file) is True:
            stack_img = cv2.imread(stack_file)
            good_imgs.append(stack_img)
            print("GOOD FOUND", stack_file)
         else:
            print("GOOD missing", stack_file)

      for sd_vid in ignored_files:
         stack_file = self.ev_dir + sd_vid.replace(".mp4", "-stacked.jpg")
         if os.path.exists(stack_file) is True:
            stack_img = cv2.imread(stack_file)
            ignore_imgs.append(stack_img)
            print("IGNORE FOUND", stack_file)
         else:
            print("IGNORE missing", stack_file)
      for sd_vid in missing_files:
         stack_file = self.ev_dir + sd_vid.replace(".mp4", "-stacked.jpg")
         if os.path.exists(stack_file) is True:
            stack_img = cv2.imread(stack_file)
            missing_imgs.append(stack_img)
         else:
            print("missing", stack_file)

      for img in edited_imgs:
         img = cv2.resize(img, (640,360))
         cv2.rectangle(img, (int(1), int(1)), (int(639) , int(359) ), (0, 0, 255), 2)
         cv2.imshow('pepe', img)
         cv2.waitKey(30)
      for img in good_imgs:
         img = cv2.resize(img, (640,360))
         cv2.rectangle(img, (int(1), int(1)), (int(639) , int(359) ), (128, 128, 128), 2)
         cv2.imshow('pepe', img)
         cv2.waitKey(30)
      for img in ignore_imgs:
         img = cv2.resize(img, (640,360))
         cv2.rectangle(img, (int(1), int(1)), (int(639) , int(359) ), (0, 0, 128), 2)
         cv2.imshow('pepe', img)
         cv2.waitKey(30)

   def update_all_obs_xys(self, event_id, local_event_dir, RF, all_img):
      #for each SD clip get the contour and brightest pixels from the sub
      # show this vs the reduction info
      # allow operator to update points
      # allow operator to ignore obs
      if "ignore_obs" not in self.edits:
         self.edits['ignore_obs'] = {}

      go = True
      idx_keys = []
      for sd_vid in self.sd_clips:
         if self.sd_clips[sd_vid]['status'] is True:
            idx_keys.append(sd_vid)

      idx = -1
      while go is True:
         if idx == -1:
            show_img = all_img.copy()


            cv2.putText(show_img, event_id,  (10,1070), cv2.FONT_HERSHEY_SIMPLEX, .6, (0,255,0), 1)
            cv2.imshow('pepe', show_img)
            key = cv2.waitKey(0)
            # show all
            if key == 115:
               # S / NEXT
               idx += 1
            if key == 100:
               # D / PREV 
               idx = len(idx_keys) - 1


         else:
            # show stack image of 1 obs 
            sd_vid = idx_keys[idx]
            if self.sd_clips[sd_vid]['status'] is True:
               show_img = self.sd_clips[sd_vid]['stack_img'].copy() 
               #text_data = [[20,20,1,2,[255,255,255],"mike was here!"]]
               text_data = []
               show_frame = RF.frame_template("1920_1p", [show_img.copy()], text_data)
               if sd_vid in self.edits['ignore_obs']:
                  if self.edits['ignore_obs'][sd_vid] is True:
                     cv2.putText(show_frame, "IGNORE OBS",  (900,25), cv2.FONT_HERSHEY_SIMPLEX, .6, (0,0,255), 1)

               cv2.putText(show_frame, event_id + " : " + sd_vid.replace(".mp4", ""),  (1100,1070), cv2.FONT_HERSHEY_SIMPLEX, .6, (0,255,0), 1)

               cv2.putText(show_frame, str(idx),  (1900,25), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 1)
               if "frame_data" in self.sd_clips[sd_vid]:
                  for fd in self.sd_clips[sd_vid]['frame_data']:
                     print("FD", self.sd_clips[sd_vid]['frame_data'][fd])

                  exit()
               cv2.imshow('pepe', show_frame)
               key = cv2.waitKey(0)
               if key == 115:
                  # S / NEXT
                  print("PRESS S")
                  idx += 1
               elif key == 100:
                  # D / PREV 
                  print("PRESS D")
                  idx -= 1
               elif key == 27:
                  # [ESC]
                  self.save_edits()
                  print("EXIT!")
                  exit()
               elif key == 112:
                  # [P] - Play Video
                  if "frame_data" not in self.sd_clips[sd_vid]:
                     self.sd_clips[sd_vid]['frame_data'] = {}

                  #if "frame_data" not in self.sd_clips[sd_vid] :
                  if True:
                     self.sd_clips[sd_vid]['frame_data'],self.sd_clips[sd_vid]['subs'] = self.build_frame_data(sd_vid, self.sd_clips[sd_vid]['frames'])
                     print(sd_vid, self.sd_clips[sd_vid].keys())


                  #self.sd_clips[sd_vid]['frame_data'], self.sd_clips[sd_vid]['deleted_points'], self.sd_clips[sd_vid]['custom_points'] = self.play_video(sd_vid, self.sd_clips[sd_vid]['frames'], self.sd_clips[sd_vid]['subs'], RF, self.sd_clips[sd_vid]['frame_data'], self.sd_clips[sd_vid]['stack_img'])
                  self.sd_clips[sd_vid]['frame_data'], self.sd_clips[sd_vid]['deleted_points'], self.sd_clips[sd_vid]['custom_points'] = self.play_video(sd_vid, RF )

               elif key == 120:
                  # X / TOGGLE IGNORE  
                  sd_vid = idx_keys[idx]
                  if sd_vid in self.edits['ignore_obs']:
                     if self.edits['ignore_obs'][sd_vid] is True:
                        self.edits['ignore_obs'][sd_vid] = True
                        cv2.putText(show_img, "IGNORE OBS",  (900,25), cv2.FONT_HERSHEY_SIMPLEX, .6, (0,0,255), 1)
                     else:
                        self.edits['ignore_obs'][sd_vid] = False 
                  else:
                     self.edits['ignore_obs'][sd_vid] = True
                     cv2.putText(show_img, "IGNORE OBS",  (900,25), cv2.FONT_HERSHEY_SIMPLEX, .6, (0,0,255), 1)



            else:
               idx += 1

            print("KEY/IDX:", key, idx)
            if idx >= len(idx_keys):
               idx = -1
               print("END OF LIST RESET")
               
         continue

         for sd_vid in self.sd_clips:
            if self.sd_clips[sd_vid]['status'] is False:
               continue 
            sfile = sd_vid.replace(".mp4", "-stacked.jpg")
            self.sd_clips[sd_vid]['sub_frames'] = []
            self.sd_clips[sd_vid]['cnts'] = []

            if self.sd_clips[sd_vid]['status'] is True :
   
               show_frame = RF.frame_template("1920_1p", [self.sd_clips[sd_vid]['stack_img']])
               cv2.waitKey(30)
               temp = []
               for frame in self.sd_clips[sd_vid]['frames'][0:25]:
                  bw_frame =  cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                  temp.append(bw_frame)
               med_frame = cv2.convertScaleAbs(np.median(np.array(temp), axis=0))

               for frame in self.sd_clips[sd_vid]['frames']:
                  bw_frame =  cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                  sub = cv2.subtract(bw_frame,med_frame)
                  self.sd_clips[sd_vid]['sub_frames'].append(sub)

                  show_frame = RF.frame_template("1920_1p", [frame])

                  #cv2.imshow('pepe_sub', sub)
                  cv2.imshow('pepe', show_frame)
                  key = cv2.waitKey(500)
                  print("KEY", key)
            else:
               print("BAD OR MISSING VIDEO:", sd_vid)

      print("OK - OK")

   def save_edits(self):
      self.edits_data = {}
      for key in self.edits_data:
         dtype = type(self.edits_data[key])
         print(key, dtype)
         if str(dtype) == "list" or str(dtype) == "dict":
            print("LIST OR DICT HERE!")
            for skey in self.edits_data[key]: 
               print(skey, type(skey))
      for sd_vid in self.sd_clips:
         if "subs" in self.sd_clips[sd_vid]:
            del(self.sd_clips[sd_vid]['subs'])
         if "frames" in self.sd_clips[sd_vid]:
            del(self.sd_clips[sd_vid]['frames'])
         if "stack_img" in self.sd_clips[sd_vid]:
            del(self.sd_clips[sd_vid]['stack_img'])

      self.edits_data['sd_clips'] = dict(self.sd_clips)
      self.edits_data['ignore_obs'] = dict(self.edits['ignore_obs'])
      save_json_file(self.edits_file, self.edits_data, True)
      print("SAVED", self.edits_file )

   def frame_data_to_objects(self, frame_data):
      objects = {}
      xs = []
      ys = []
      for fc in frame_data:
         if "cnts" in frame_data[fc]:
            cnts = frame_data[fc]['cnts']
            for cnt in cnts:
               #x,y,w,h,meteor_flux,meteor_intensity = cnt
               x1,y1,x2,y2,cx,cy,radius,meteor_int,meteor_flux = cnt
               w = x2 - x1
               h = y2 - y1
               obj_id, objects = find_object(objects, fc,cx, cy, w, h, meteor_flux, 0, 0, None)
      meteor_objects = {} 
      non_meteor_objects = {} 
      last_biggest = None
      last_big = 0
      for obj in objects:
         objects[obj] = analyze_object(objects[obj], 1)
         if len(objects[obj]['oxs']) > last_big:
            last_biggest = obj
            last_big = len(objects[obj]['oxs'])
         print("OBJECT", obj, len(objects[obj]['oxs']), objects[obj]['report']['meteor'], objects[obj]['report']['bad_items'])
      best = {}
      best["1"] = objects[last_biggest]
      return(best)

   def graph_xys(self,xs,ys):

      plt.scatter(xs,ys) 
      #plt.gca().invert_yaxis()
      plt.savefig("temp.png")
      img = cv2.imread("temp.png")
      img = cv2.resize(img, (int(img.shape[1]*.5), int(img.shape[0]*.5)))
      cv2.imshow('graph', img)
      cv2.waitKey(30)

   def build_frame_data(self, sd_vid, frames):

      if sd_vid in self.edits['sd_clips']:
         if "deleted_points" in self.edits['sd_clips'][sd_vid]:
            self.sd_clips[sd_vid]['deleted_points'] =  self.edits['sd_clips'][sd_vid]['deleted_points']
         if "custom_points" in self.edits['sd_clips'][sd_vid]:
            self.sd_clips[sd_vid]['custom_points'] =  self.edits['sd_clips'][sd_vid]['custom_points']

      if "custom_points" not in self.sd_clips[sd_vid]:
         self.sd_clips[sd_vid]['custom_points'] = {}
      if "deleted_points" not in self.sd_clips[sd_vid]:
         self.sd_clips[sd_vid]['deleted_points'] = {}

      print("D:", self.sd_clips[sd_vid]['deleted_points'])
      print("C:", self.sd_clips[sd_vid]['custom_points'])
      print("SD CLIPS:", self.sd_clips[sd_vid].keys())
      print("SD E CLIPS:", self.edits['sd_clips'].keys())

      frame_data = {}
      fc = 0
      temp = []
      subs = {}
      hdm_x = 1920 / 640
      hdm_y = 1080 / 360
      for frame in frames[0:10]:
         bw_frame = cv2.resize(frame, (640,360))
         bw_frame =  cv2.cvtColor(bw_frame, cv2.COLOR_BGR2GRAY)
         temp.append(bw_frame)

      med_frame = cv2.convertScaleAbs(np.median(np.array(temp), axis=0))
      print("FRAMES:", len(frames))
      for frame in frames:
         frame = cv2.resize(frame, (640,360))
         frame_data[fc] = {}
         bw_frame =  cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
         sub = cv2.subtract(bw_frame,med_frame)
         min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(sub)
         subs[fc] = sub
         thresh_val = int(max_val * .6)
         _, thresh_image = cv2.threshold(sub, thresh_val, 255, cv2.THRESH_BINARY)
         cnts = get_contours_in_image(thresh_image)

         if len(cnts) >= 1:
            cnts = sorted(cnts, key=lambda x: x[2] * x[3], reverse=True)
            cnts = [cnts[0]]

         # if the frame exists inside the custom points 
         # override the default cnt with those values 
         print("BEFORE OVERRIDE CNTS:", cnts)
         if fc in self.sd_clips[sd_vid]['custom_points'] :
            x = int(self.sd_clips[sd_vid]['custom_points'][fc][0] / hdm_x )
            y = int(self.sd_clips[sd_vid]['custom_points'][fc][1] / hdm_y)
            w = int(self.sd_clips[sd_vid]['custom_points'][fc][2] / hdm_y)
            h = w
            cnts = [[x,y,w,h]]
         elif str(fc) in self.sd_clips[sd_vid]['custom_points']:
            sfc = str(fc)
            w = int(self.sd_clips[sd_vid]['custom_points'][sfc][2] / hdm_x)
            x = int(self.sd_clips[sd_vid]['custom_points'][sfc][0] / hdm_x ) - (w/2)
            y = int(self.sd_clips[sd_vid]['custom_points'][sfc][1] / hdm_y) - (w/2)
           

            cnts = [[x,y,w,w]]
         if fc in self.sd_clips[sd_vid]['deleted_points'] or str(fc) in self.sd_clips[sd_vid]['deleted_points']:
            cnts = []
            print(fc, "found in deleted points!")
            print("DELETE POINTS IS:", self.sd_clips[sd_vid]['deleted_points'])
         else:
            print(fc, "NOT found in deleted points!")
            print("DELETE POINTS IS:", self.sd_clips[sd_vid]['deleted_points'])

         print("AFTER OVERRIDE CNTS:", cnts)

         for cnt in cnts:
            x,y,w,h = cnt 
            if w > h:
               h = w
            else:
               w = h

            x1 = int(cnt[0] * hdm_x)
            y1 = int(cnt[1] * hdm_y)
            x2 = int(cnt[0] * hdm_x) + int(w * hdm_x)
            y2 = int(cnt[1] * hdm_y) + int(h * hdm_y)
            cx = ((x1 + x2) / 2) 
            cy = ((y1 + y2) / 2)
            if x2 - x1 > y2 - y1:
               radius = x2 - x1
            else:
               radius = y2 - y1
            meteor_int = np.sum(sub[y1:y2,x1:x2])
            if radius < 2:
               radius = 2

            if True:
               # for flux
               px1 = int((x1+x2)/2) - 50 
               px2 = int((x1+x2)/2) + 50 
               py1 = int((y1+y2)/2) - 50 
               py2 = int((y1+y2)/2) + 50 


               if px1 < 0:
                  px1 = 0
               if px2 > 1920:
                  px2 = 1920
               if py1 < 0:
                  py1 = 0
               if py2 > 1080:
                  py2 = 1080 
               pcx = ((px1 + px2) / 2) - px1
               pcy = ((py1 + py2) / 2) - py1
               temp = cv2.resize(subs[fc], (1920,1080))
               sub = cv2.resize(sub, (1920,1080))
               meteor_flux = do_photo(sub[py1:py2,px1:px2], (pcx,pcy), radius+1)
               if np.isnan(meteor_flux):
                  meteor_flux = 0
               if np.isnan(meteor_int):
                  meteor_int= 0

               # if this frame is insdie the deleted points or custom point fix it. 
               if fc in self.sd_clips[sd_vid]['deleted_points'] or str(fc) is self.sd_clips[sd_vid]['deleted_points']:
                  print("FRAME DELETED!")
               else:
                  frame_data[fc]['cnts'] = [[int(x1),int(y1),int(x2),int(y2),float(cx),float(cy),int(radius),int(meteor_int),int(meteor_flux)]]
               #print("FD:", frame_data[fc])
         fc += 1

      #print("FD:", frame_data)
      return(frame_data, subs)


   #self.play_video(sd_vid, self.sd_clips[sd_vid]['frames'], self.sd_clips[sd_vid]['subs'], RF, self.sd_clips[sd_vid]['frame_data'], self.sd_clips[sd_vid]['stack_img'])
   #def play_video(self, sd_vid, frames, subs, RF, frame_data ,stack_img):

   def get_event_obs(self):
      event_data = {}
      obs_data = {}
      extra_rows = {}
      st_pts = {}
      st_az_pts = {}
      obs_imgs = {}

      extra_obs_file = self.local_evdir + self.event_id + "/" + self.event_id + "_EXTRA_OBS.json"
      if os.path.exists(extra_obs_file) is True:
         extra_obs = load_json_file(extra_obs_file)
      else:
         extra_obs = {}
      for st in extra_obs:
         for vf in extra_obs[st]:
            obs_id = st + "_" + vf
            obs_data[obs_id] = extra_obs[st][vf]
            extra_rows[obs_id] = extra_obs[st][vf]
            print("ADD EXTRA OBS", obs_id)
      # get event info frirst
      sql = """
            SELECT event_id, event_minute, revision, event_start_time, event_start_times, stations, obs_ids, lats, lons, event_status, run_date, run_times
              FROM events
             WHERE event_id = ?
      """
      svals = [self.event_id]
      self.cur.execute(sql, svals)
      rows = self.cur.fetchall()
      data = []
      for row in rows:
         (event_id, event_minute, revision, event_start_time, event_start_times, stations, obs_ids, lats, lons, event_status, run_date, run_times ) = row
         event_data['event_id'] = event_id
         event_data['event_minute'] = event_minute
         event_data['revision'] = revision 
         event_data['event_start_time'] = event_start_time
         event_data['event_start_times'] = json.loads(event_start_times)
         event_data['stations'] = json.loads(stations)
         event_data['obs_ids'] = json.loads(obs_ids )
         event_data['lats'] = json.loads(lats )
         event_data['lons'] = json.loads(lons )
         event_data['event_status'] = event_status 
         event_data['run_date'] = run_date 
         event_data['run_times'] = run_times

      for obs_id in extra_rows:
         st = obs_id.split("_")[0]
         station_id = st
         event_data['stations'].append(st)
         event_data['obs_ids'].append(obs_id)
         event_data['event_start_times'].append(extra_rows[obs_id]['times'][0])
         if "lat" in extra_rows[obs_id]:
            event_data['lats'].append(extra_rows[obs_id]['lat'])
            event_data['lons'].append(extra_rows[obs_id]['lon'])
         else:
            lat,lon,alt =  extra_rows[obs_id]['loc']
            extra_rows[obs_id]['lat'] = lat
            extra_rows[obs_id]['lon'] = lon
            event_data['lats'].append(lat)
            event_data['lons'].append(lon)

         obs_data[obs_id] = {}
         obs_data[obs_id]['event_id'] = event_data['event_id']
         obs_data[obs_id]['event_minute'] = event_data['event_minute']
         obs_data[obs_id]['station_id'] = st
         obs_data[obs_id]['obs_id'] = obs_id

         lat = extra_rows[obs_id]['lat']
         lon = extra_rows[obs_id]['lon']
         obs_data[obs_id]['lat'] = extra_rows[obs_id]['lat']
         obs_data[obs_id]['lon'] = extra_rows[obs_id]['lon']
         st_pts[st] = [lat,lon,station_id.replace("AMS", "")]
         #obs_data[obs_id]['fns'] = json.loads(fns)
         obs_data[obs_id]['times'] = extra_rows[obs_id]['times']
         #obs_data[obs_id]['xs'] = json.loads(xs)
         #obs_data[obs_id]['ys'] = json.loads(ys)
         obs_data[obs_id]['azs'] = extra_rows[obs_id]['azs']
         obs_data[obs_id]['els'] = extra_rows[obs_id]['els']
         obs_data[obs_id]['ints'] = extra_rows[obs_id]['ints'] 
         obs_data[obs_id]['az_start_point'] = self.find_point_from_az_dist(lat,lon,float(extra_rows[obs_id]['azs'][0]),650)
         obs_data[obs_id]['az_end_point'] = self.find_point_from_az_dist(lat,lon,float(extra_rows[obs_id]['azs'][-1]),650)
         if station_id not in st_az_pts:
            st_az_pts[station_id] = []
         st_az_pts[station_id].append(obs_data[obs_id]['az_start_point'])
         st_az_pts[station_id].append(obs_data[obs_id]['az_end_point'])
         st_az_pts[obs_id] = [obs_data[obs_id]['az_start_point'], obs_data[obs_id]['az_end_point']]

      lc = 0 
      deleted = []
      good = []

      print("EVENT_DATA: ", event_data.keys())
      for obs_id in event_data['obs_ids']:
         
         go = True
         for ig in self.ignore:
            if ig in obs_id:
               print("SKIP IGNORE:", obs_id, ig)
               deleted.append(obs_id)
               go = False
         if go is True:
            good.append(obs_id)
      event_data['obs_ids'] = good


      # THIS IS A BUG!!! OBS NEED TO BE UPDATED SOMEWHERE / SOMEHOW WHAT DO WE DO NOW!
      # OBS ARE BEING RELOADED SOMEWHERE ELSE, BUT THE DB IS NOT UPDATED RIGHT
      # FIX THE BUG INSIDE THE SOLVE CALL
      self.ignored_obs = {}
      self.deleted_obs = {}
      for obs_id in event_data['obs_ids']:
         for ig in self.ignore:
            if ig in obs_id:
               print("SKIP IGNORE:", obs_id, ig)
               continue

         sql = """
            SELECT event_id, event_minute, station_id, obs_id, fns, times, xs, ys, azs, els, ints, status, ignore 
              FROM event_obs
             WHERE obs_id = ?
            """
         svals = [obs_id]
         self.cur.execute(sql, svals)
         rows = self.cur.fetchall()

         for row in rows:
            (event_id, event_minute, station_id, obs_id, fns, times, xs, ys, azs, els, ints, status, ignore ) = row
            print("    GET EVENT OBS FOR ", station_id + "_" + obs_id)

            ignore = False
            for ig in self.ignore:
               if ig in obs_id:
                  ignore = True
            if ignore is True:
               self.ignored_obs[obs_id] = (event_id, event_minute, station_id, obs_id, fns, times, xs, ys, azs, els, ints, status, ignore )

            # CHECK / UPDATE FROM AWS FIRST?
            sd_vid = obs_id.replace(station_id + "_", "") + ".mp4"
            dobs = get_obs(station_id, sd_vid)
            temp_obs = {}
            dobs['loc'] = [float(self.station_dict[station_id]['lat']), float(self.station_dict[station_id]['lon']), float(self.station_dict[station_id]['alt'])]

            if "aws_status" in dobs:
               if dobs['aws_status'] is False:
                  print("OBS WAS DELETED FROM AWS IGNORE IT!", dobs)
                  print("We should also delete it from the event, from the sqlplus event_obs table, the obs dict and the ALL obs file!")
                  print("That is a lot of places, so we will make a delete OBS and all references function later.")
                  print("For now we will just ignore / skip it.")
                  self.ignored_obs[obs_id] = (event_id, event_minute, station_id, obs_id, fns, times, xs, ys, azs, els, ints, status, ignore )
                  self.deleted_obs[obs_id] = (event_id, event_minute, station_id, obs_id, fns, times, xs, ys, azs, els, ints, status, ignore )
                  ignore = True
                  continue
               else:
                  temp = convert_dy_obs(dobs, temp_obs)
                  temp_obs = temp[station_id][sd_vid]



                  xs = temp_obs['xs']
                  ys = temp_obs['ys']
                  fns = temp_obs['fns']
                  times = temp_obs['times']
                  azs = temp_obs['azs']
                  els = temp_obs['els']
                  ints = temp_obs['ints']

                  #status = dobs['status']
                  #ignore= dobs['status']




            lat,lon,alt = self.station_loc[station_id][:3]
            obs_data[obs_id] = {}
            obs_data[obs_id]['event_id'] = event_data['event_id']
            obs_data[obs_id]['event_minute'] = event_data['event_minute']
            obs_data[obs_id]['station_id'] = station_id
            obs_data[obs_id]['obs_id'] = obs_id
            obs_data[obs_id]['lat'] = lat
            obs_data[obs_id]['lon'] = lon
            st_pts[station_id] = [lat,lon,station_id.replace("AMS", "")]

            if type(fns) == str:
               obs_data[obs_id]['fns'] = json.loads(fns)
            else:
               obs_data[obs_id]['fns'] = fns
            if type(times) == str:
               obs_data[obs_id]['times'] = json.loads(times)
            else:
               obs_data[obs_id]['times'] = times
            if type(xs) == str:
               obs_data[obs_id]['xs'] = json.loads(xs)
            else:
               obs_data[obs_id]['xs'] = xs
            if type(ys) == str:
               obs_data[obs_id]['ys'] = json.loads(ys)
            else:
               obs_data[obs_id]['ys'] = ys
            if type(azs) == str:
               obs_data[obs_id]['azs'] = json.loads(azs)
            else:
               obs_data[obs_id]['azs'] = azs
            if type(els) == str:
               obs_data[obs_id]['els'] = json.loads(els)
            else:
               obs_data[obs_id]['els'] = els
            if type(ints) == str:
               obs_data[obs_id]['ints'] = json.loads(ints)
            else:
               obs_data[obs_id]['ints'] = ints

            obs_data[obs_id]['status'] = status 
            obs_data[obs_id]['ignore'] = ignore 
            obs_data[obs_id]['image_file'] =  self.local_evdir + self.event_id + "/" + obs_id + "-stacked.jpg"

            print("FIND START POINT", obs_id, obs_data[obs_id]['azs'][0])
            print("FIND END POINT", obs_id, obs_data[obs_id]['azs'][-1])


            obs_data[obs_id]['az_start_point'] = self.find_point_from_az_dist(lat,lon,float(obs_data[obs_id]['azs'][0]),650)
            obs_data[obs_id]['az_end_point'] = self.find_point_from_az_dist(lat,lon,float(obs_data[obs_id]['azs'][-1]),650)
            if station_id not in st_az_pts:
               st_az_pts[station_id] = []
            st_az_pts[station_id].append(obs_data[obs_id]['az_start_point'])
            st_az_pts[station_id].append(obs_data[obs_id]['az_end_point'])
            st_az_pts[obs_id] = [obs_data[obs_id]['az_start_point'], obs_data[obs_id]['az_end_point']]

            if os.path.exists( obs_data[obs_id]['image_file']):
               print("YES, FOUND:", obs_data[obs_id]['image_file'])
               obs_img = cv2.imread(obs_data[obs_id]['image_file'])
               obs_img = cv2.resize(obs_img, (640,360))
               obs_imgs[obs_id] = obs_img
            else:
               print("OBS ID IS:", obs_id)
               # as a fallback copy the cloud prev file if it is not already copied
               date = obs_id.replace(station_id + "_", "")[0:10]
               year = date[0:4]
               cloud_prev_file = self.cloud_dir + station_id + "/METEORS/" + year + "/" + date + "/" + obs_id + "-prev.jpg"
               local_prev_file = self.local_evdir + self.event_id + "/" + obs_id + "-prev.jpg"
               if os.path.exists(local_prev_file) is False:
                  if os.path.exists(cloud_prev_file) is True:
                     cmd = "cp " + cloud_prev_file + " " + local_prev_file
                     os.system(cmd)
                     #wget_cmds.append(cmd)
                  else:
                     print("No cloud file found!", cloud_prev_file)
               if os.path.exists(local_prev_file) is True:
                  print("Using prev image", local_prev_file)
                  prev_img = cv2.imread(local_prev_file)
                  try:
                     prev_img = cv2.resize(prev_img, (1920,1080))
                     obs_imgs[obs_id] = prev_img 
                  except:
                     print("No image could be found for:", obs_id)
               else:
                   print("No image could be found for:", obs_id)


               
         lc += 1

      # here we should check how things intersect and mark obs that don't 
      # lat/lon & bearing of 2 stations
      # this should be a function or class!
      ipoints = {}
      points = [] 
      lines = [] 
      failed_combos = [] 
      for obs_id_1 in obs_data:
         if "obs_start_points" not in obs_data[obs_id_1]:
            obs_data[obs_id_1]['obs_start_points'] = []
            obs_data[obs_id_1]['obs_end_points'] = []
         for obs_id_2 in obs_data:
            if "obs_start_points" not in obs_data[obs_id_2]:
               obs_data[obs_id_2]['obs_start_points'] = []
               obs_data[obs_id_2]['obs_end_points'] = []
            station1 = obs_data[obs_id_1]['station_id']
            station2 = obs_data[obs_id_2]['station_id']
            if station1 == station2:
               continue
            itemp = sorted([obs_id_1, obs_id_2])
            ikey = itemp[0] + "__" + itemp[1]
            if ikey in ipoints:
               continue

            x1 = obs_data[obs_id_1]['lon'] 
            y1 = obs_data[obs_id_1]['lat'] 
            brng1 = obs_data[obs_id_1]['azs'][0]

            x2 = obs_data[obs_id_2]['lon'] 
            y2 = obs_data[obs_id_2]['lat'] 
            brng2 = obs_data[obs_id_2]['azs'][0]

            #start point
            try:
               ipoint = geo_intersec_point(x1, y1, brng1, x2, y2, brng2)
            except:
               ipoint = [0,0]



            #end point
            brng1 = obs_data[obs_id_1]['azs'][-1]
            brng2 = obs_data[obs_id_2]['azs'][-1]
            try:
               end_ipoint = geo_intersec_point(x1, y1, brng1, x2, y2, brng2)
            except:
               end_ipoint = [0,0]


            if ipoint[0] == True or end_ipoint[0] == True:
               failed_combos.append(ikey)
               # intersect failed...
            else:
               # intersect passed
               end_failed = False
               start_failed = False
               try:
                  start_station_dist = dist_between_two_points(y1, x1, ipoint[1]['y3'], ipoint[1]['x3']) 
               except:
                  start_station_dist = 9999

               try:
                  end_station_dist = dist_between_two_points(y1, x1, end_ipoint[1]['y3'], ipoint[1]['x3']) 
               except:
                  end_station_dist = 9999

               # only add a point if its within < 800 km away
               if end_station_dist > 800 and start_station_dist > 800:
                  start_failed = True
                  end_failed = True

               if start_failed is False and end_failed is False:
                  obs_data[obs_id_1]['obs_start_points'].append(( ipoint[1]['y3'], ipoint[1]['x3']))
                  obs_data[obs_id_2]['obs_start_points'].append(( ipoint[1]['y3'], ipoint[1]['x3']))

                  obs_data[obs_id_1]['obs_end_points'].append(( end_ipoint[1]['y3'], end_ipoint[1]['x3']))
                  obs_data[obs_id_2]['obs_end_points'].append(( end_ipoint[1]['y3'], end_ipoint[1]['x3']))
                  #points.append((ipoint[1]['x3'], ipoint[1]['y3'], 'i'))
            if len(obs_data[obs_id_1]['obs_end_points']) == 0 or len(obs_data[obs_id_1]['obs_start_points']) == 0:
               obs_data[obs_id_1]['status'] = "INVALID"
               obs_data[obs_id_1]['ignore'] = True
            else:
               obs_data[obs_id_1]['status'] = "VALID"
               obs_data[obs_id_1]['ignore'] = False 

            if len(obs_data[obs_id_2]['obs_end_points']) == 0 or len(obs_data[obs_id_2]['obs_start_points']) == 0:
               obs_data[obs_id_2]['status'] = "INVALID"
               obs_data[obs_id_2]['ignore'] = True
            else:
               obs_data[obs_id_2]['status'] = "VALID"
               obs_data[obs_id_2]['ignore'] = False 


            ipoints[ikey] = ipoint
            #print("IPOINT:", ikey, ipoint)

      # determine which stations are valid or not based on successful intersects
      valid_stations = {}
      for obs_id in obs_data:
         station_id = obs_id.split("_")[0]
         if station_id not in valid_stations:
            valid_stations[station_id] = {}
            valid_stations[station_id]['good_obs'] = 0
            valid_stations[station_id]['bad_obs'] = 0
         if obs_data[obs_id]['ignore'] is True:
            valid_stations[station_id]['bad_obs'] += 1
         else:
            valid_stations[station_id]['good_obs'] += 1

      for st in valid_stations:

         if valid_stations[st]['good_obs'] > 0 :
            valid_stations[station_id]['good_ratio'] = valid_stations[st]['good_obs'] / valid_stations[st]['good_obs'] + valid_stations[st]['bad_obs']
         else:
            valid_stations[station_id]['good_ratio'] = 0

         

      self.echo_event_data(event_data, obs_data)
      line_names = []
      if True:
         for st in st_pts:
            for sp, ep in st_az_pts[st]:
               station = st 
               slat = st_pts[st][0]
               slon = st_pts[st][1]
        
               if valid_stations[station_id]['good_ratio'] > 0:
                  points.append((slat,slon,station,"green","o"))
               else:
                  points.append((slat,slon,station,"red","x"))

               lines.append((st_pts[st][0], st_pts[st][1], st_az_pts[st][0][0] , st_az_pts[st][0][1], 'green'))
               lines.append((st_pts[st][0], st_pts[st][1], st_az_pts[st][1][0] , st_az_pts[st][1][1], 'orange'))
               line_names.append(st + " Start")
               line_names.append(st + " End")


      for obs_id in obs_data:
         for row in obs_data[obs_id_1]['obs_start_points']:
            points.append((row[0], row[1], "s"))
         for row in obs_data[obs_id_1]['obs_end_points']:
            points.append((row[0], row[1], "e"))
         st = obs_id.split("_")[0]
         med_end_lat = np.mean([row[0] for row in obs_data[obs_id_1]['obs_end_points']])
         med_end_lon = np.mean([row[1] for row in obs_data[obs_id_1]['obs_end_points']])
         med_start_lat = np.mean([row[0] for row in obs_data[obs_id_1]['obs_start_points']])
         med_start_lon = np.mean([row[1] for row in obs_data[obs_id_1]['obs_start_points']])

         #lines.append((st_pts[st][0], st_pts[st][1], med_start_lat, med_start_lon, 'pink'))
         #lines.append((st_pts[st][0], st_pts[st][1], med_end_lat, med_end_lon, 'purple'))


      if self.planes != None:
         self.make_kml(self.map_kml_file, points, lines, line_names)
         event_data['planes'] = self.planes['results']
      else:
         print("No planes file.")
         event_data['planes'] = None
      event_data['obs'] = obs_data

 
      #for key in self.planes:
      #   print(key, self.planes[key])
      #exit()
      event_data['event_id'] = self.event_id
      #self.make_plane_kml(event_data, self.planes)

      try:
         map_img = make_map(points, lines)
         self.save_geo_json(points, lines)
      except:
         print("FAILED TO MAP:", points, lines)
         map_img = np.zeros((1080,1920,3),dtype=np.uint8)

         map_img = make_map(points, lines)
         self.save_geo_json(points, lines)

      x1 = int(map_img.shape[1] / 2) - 960 
      x2 = int(map_img.shape[1] / 2) + 960 
      y1 = int(map_img.shape[0] / 2) - 540 
      y2 = int(map_img.shape[0] / 2) + 540 
      new_img = map_img[y1:y2,x1:x2]
      return(event_data, obs_data, new_img, obs_imgs)

   def echo_event_data(self,event_data, obs_data):
      tb = pt()
      tb.field_names = ['Field', 'Value']
      for key in event_data:
         if isinstance(event_data[key], list) is False:
            tb.add_row([key, event_data[key]])
         else:
            tb.add_row([key, len(event_data[key])])
      report = str(tb)
      report += "\n\n"

      for obs_id in obs_data:
         tb = pt()
         tb.field_names = ['Field', 'Value']
         for key in obs_data[obs_id]:
            if isinstance(obs_data[obs_id][key], list) is False:
               tb.add_row([key, obs_data[obs_id][key]])
            elif "points" in key: 
               tb.add_row([key, obs_data[obs_id][key]])
            else:
               if key == "azs" or key == "els":
                  tb.add_row([key, str( round(obs_data[obs_id][key][0],2)) + " / " + str( round(obs_data[obs_id][key][-1],2 )) ])
               else:
                  if obs_id in obs_data:
                     if len(obs_data[obs_id][key]) > 0:
                        tb.add_row([key, str( obs_data[obs_id][key][0]) + " / " + str( obs_data[obs_id][key][-1] ) ])
         report += str(tb)
         report += "\n"
      print(report)





   def find_point_from_az_dist(self,lat,lon,az,dist):
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


   def play_edit_video(self, sd_vid):
      #print("VID:", sd_vid)
      event_data, obs_data, map_img,obs_imgs = self.get_event_obs(sd_vid.replace(".mp4", ""))
      cv2.imshow('pepe', map_img)
      cv2.waitKey(30)
      for key in obs_imgs:
         cv2.imshow('pepe', obs_imgs[key])
         cv2.waitKey(30)

      print("OBS DATA",sd_vid, obs_data) 


   def play_video(self, sd_vid, RF):
      # edits should go into the DB!
      self.play_edit_video(sd_vid)
      return()

      frames = self.sd_clips[sd_vid]['frames']

      subs = self.sd_clips[sd_vid]['subs']
      frame_data = self.sd_clips[sd_vid]['frame_data']
      stack_img = self.sd_clips[sd_vid]['stack_img']
      if "custom_points" in self.sd_clips[sd_vid]:
         custom_points = self.sd_clips[sd_vid]['custom_points']
      else:
         custom_points = {}
      if "deleted_points" in self.sd_clips[sd_vid]:
         deleted_points = self.sd_clips[sd_vid]['deleted_points']
      else:
         deleted_points = {}

      print("SDCD", self.sd_clips[sd_vid].keys())

      temp = []
      cv2.namedWindow('pepe')
      cv2.setMouseCallback('pepe',self.meteor_mouse_click)
      hdm_x = 3
      hdm_y = 3
      go = True
      self.fc = 0
      self.deleted_points = {}
      self.custom_points = {}
      if sd_vid in self.sd_clips:
         if "custom_points" in self.sd_clips[sd_vid]:
            self.custom_points = self.sd_clips[sd_vid]['custom_points']
         if "deleted_points" in self.sd_clips[sd_vid]:
            self.deleted_points = self.sd_clips[sd_vid]['deleted_points']
      else:
         print(sd_vid, "not found in sd_clips data")

      print("CUSTOM", self.custom_points)
      print("DEL", self.deleted_points)
      stack_img= cv2.resize(stack_img, (1920,1080))
      print("KEYS FROM SD_CLIPS", self.sd_clips[sd_vid].keys())

      while go == True:
         
         if self.fc >= len(frames) or self.fc < 0:
            self.fc = 0
         frame = frames[self.fc]
         orig_frame = cv2.resize(frame.copy(), (1920,1080))
         self.active_frame = cv2.resize(frame.copy(), (1920,1080))

         frame = cv2.resize(frame, (1920,1080))
         show_frame = RF.frame_template("1920_pip1_tl", [frame])
         cnts = []
         if self.fc in self.custom_points:
            if len(self.custom_points[self.fc]) == 3:
               x,y,size = self.custom_points[self.fc]
               x1 = x - size
               x2 = x + size
               y1 = y - size
               y2 = y + size
               radius = size 
               meteor_int = 0
               meteor_flux = 0
               cx = int((x1 + x2) / 2)
               cy = int((y1 + y2) / 2)

               px1 = int((x1+x2)/2) - 50 
               px2 = int((x1+x2)/2) + 50 
               py1 = int((y1+y2)/2) - 50 
               py2 = int((y1+y2)/2) + 50 

               if px1 < 0:
                  px1 = 0
               if px2 > 1920:
                  px2 = 1920
               if py1 < 0:
                  py1 = 0
               if py2 > 1080:
                  py2 = 1080 
               pcx = ((px1 + px2) / 2) - px1
               pcy = ((py1 + py2) / 2) - py1
               temp = cv2.resize(subs[self.fc], (1920,1080))
               meteor_flux = do_photo(temp[py1:py2,px1:px2], (pcx,pcy), radius+1)

               frame_data[self.fc]['cnts'] = [[x1,y1,x2,y2,cx,cy,radius,meteor_int,meteor_flux]]

         if self.fc in frame_data:
            print(self.fc, frame_data[self.fc])
            if "cnts" in frame_data[self.fc]:
               cnts = frame_data[self.fc]['cnts']
         if len(cnts) >= 1 and self.fc not in self.deleted_points : #and self.fc not in self.custom_points:
               print("CNTS:", cnts[0])
               (x1,y1,x2,y2,cx,cy,radius,meteor_int,meteor_flux) = cnts[0]
               
               px1 = int((x1+x2)/2) - 50 
               px2 = int((x1+x2)/2) + 50 
               py1 = int((y1+y2)/2) - 50 
               py2 = int((y1+y2)/2) + 50 

               if px1 < 0:
                  px1 = 0
               if px2 > 1920:
                  px2 = 1920
               if py1 < 0:
                  py1 = 0
               if py2 > 1080:
                  py2 = 1080 
               pcx = ((px1 + px2) / 2) - px1
               pcy = ((py1 + py2) / 2) - py1

               crop_img = orig_frame[py1:py2,px1:px2]
               cv2.rectangle(frame, (int(x1), int(y1)), (int(x2) , int(y2) ), (255, 255, 255), 1)
               #if np.isnan(meteor_flux) is False:
               cv2.putText(frame, "FLUX" + str(int(meteor_flux)),  (x1,y2+10), cv2.FONT_HERSHEY_SIMPLEX, .6, (0,255,0), 1)
               cv2.putText(frame, "INT" + str(int(meteor_int)),  (x1,y2+20), cv2.FONT_HERSHEY_SIMPLEX, .6, (0,128,0), 1)
               crop_img = cv2.resize(crop_img,(400,400))
               cv2.line(crop_img , (int(200),int(0)), (int(200),int(400)), (255,255,255), 1)
               cv2.line(crop_img , (int(0),int(200)), (int(400),int(200)), (255,255,255), 1)
               show_frame = RF.frame_template("1920_pip1_tl", [frame, crop_img])

         else:
            print("NO OBJECTS!")
            show_frame = RF.frame_template("1920_pip1_tl", [frame])

         cv2.putText(show_frame, str(self.fc) + "",  (1800,25), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 1)
         cv2.imshow('pepe', show_frame)
         self.key = cv2.waitKey(0)
         if self.key == 102:
            print("NEXT", self.fc)
            self.fc += 1
         elif self.key == 97:
            print("PREV", self.fc)
            self.fc -= 1
         elif self.key == 27:
            go = False 
         elif self.key == 120:
            print("DELETE FRAME DATA", self.fc, frame_data[self.fc])
            self.deleted_points[self.fc] = True
               # delete frame data 
            if self.fc in self.custom_points:
               del self.custom_points[self.fc]
            frame_data[self.fc]['cnts'] = []
            print("AFTER DELETE FRAME DATA", frame_data[self.fc])
            self.fc += 1
         elif self.key == 27:
            go = False

      # END WHILE LOOP

      objects = self.frame_data_to_objects(frame_data)
      ints = []
      f = plt.figure()

      show_img = RF.frame_template("1920_1p", [stack_img])

      for obj in objects:
         xs = []
         ys = []
         if len(objects[obj]['oxs']) < 3:
            continue
         
         mx = int(np.mean(objects[obj]['oxs']))
         my = int(np.mean(objects[obj]['oys']))
         if max((objects[obj]['oxs'])) - min((objects[obj]['oxs'])) > max(objects[obj]['oys']) - min(objects[obj]['oys']):
            radius = max((objects[obj]['oxs'])) - min((objects[obj]['oxs']))
         else:
            radius = max((objects[obj]['oys'])) - min((objects[obj]['oys']))
         print("RAD:", mx,my, radius)
         cv2.circle(show_img, (mx,my), int(radius), (128,128,128),1)
         cv2.putText(show_img, str(obj),  (mx,my), cv2.FONT_HERSHEY_SIMPLEX, .8, (0,255,0), 1)
         cv2.imshow('pepe', show_img)
         cv2.waitKey(30)
      cv2.waitKey(30)
      
      return(frame_data, self.deleted_points, self.custom_points)

   def meteor_mouse_click(self,event,x,y,flags,param):
      if event == cv2.EVENT_LBUTTONDBLCLK:
         global mouseX, mouseY
         mouseX, mouseY = x,y 
         if self.fc in self.deleted_points:
            del self.deleted_points[self.fc]
         temp = self.active_frame.copy()
         bw_temp =  cv2.cvtColor(temp, cv2.COLOR_BGR2GRAY)

         # get roi around click
         x1 = x - 50
         x2 = x + 50
         y1 = y - 50
         y2 = y + 50
         if x1 < 0:
            x1 = 0
         if x2 > 1920 :
            x2 = 1920 
         if y1 < 0:
            y1 = 0
         if y2 > 1080:
            y2 = 1080  
         temp_crop = temp[y1:y2,x1:x2]
         bw_temp_crop =  cv2.cvtColor(temp_crop, cv2.COLOR_BGR2GRAY)
         max_val = bw_temp[y,x]
         thresh_val = int(max_val * .5)

         print("VALS:", mouseX,mouseY, self.fc, max_val, thresh_val)

         _, thresh_image = cv2.threshold(bw_temp_crop, thresh_val, 255, cv2.THRESH_BINARY)
         cv2.imshow('ccc', thresh_image)
         cv2.waitKey(30)
         cnts = get_contours_in_image(thresh_image)
         if len(cnts) > 1:
            cnts = sorted(cnts, key=lambda x: x[2] * x[3], reverse=True)
            cnts = cnts[0:1]

         for xx,yy,ww,hh in cnts:
            cv2.rectangle(temp, (int(x1+xx), int(y1+yy)), (int(x1+xx+ww) , int(y1+yy+hh) ), (255, 255, 255), 1)
         if ww > hh:
            hh = ww
         else:
            ww = hh

         self.custom_points[self.fc] = [int(mouseX),int(mouseY),int(ww)]
         cv2.circle(temp, (int(x),int(y)), int(ww), (128,128,128),1)
         cv2.imshow('pepe', temp)


   def station_events(self, date ):
      station_events = {}
      if os.path.exists(self.all_events_file) is True:
         all_events = load_json_file(self.all_events_file)
      else:
         os.system("./DynaDB.py udc " + date )
         if os.path.exists(self.all_events_file) is True:
            all_events = load_json_file(self.all_events_file)
         else:
            return()
      info_file = self.all_events_file.replace(".json", ".info")
      if os.path.exists(info_file) is True:
         os.system("rm " + info_file)
      for evd in all_events:
         #print(evd['event_id'], evd['stations'], evd['files']) 
         event_id = evd['event_id']
         for i in range(0, len(evd['stations'])):
            station_id = evd['stations'][i]
            obs_id = evd['files'][i]
            dict_key = station_id + "_" + obs_id
            if dict_key in self.obs_dict:
               obs_data = self.obs_dict[dict_key]
            else:
               #print("NO OBS DATA!", dict_key)
               obs_data = {}


            obs_id = obs_id.replace(".mp4", "")
            obs_id = obs_id.replace(date + "_", "")
            obs_id = obs_id.replace("_000_", "c")
            obs_id = obs_id.replace("_", "")
            obs_id = obs_id.replace("-", "")
            obs_id = obs_id.replace("trim", "t")

            if station_id not in station_events:
               station_events[station_id] = {}
            if obs_id not in station_events[station_id]:
               station_events[station_id][obs_id] = event_id.split("_")[1]
            print(station_id, obs_id, event_id)
      save_json_file(self.station_events_file, station_events, True)
      print("SAVED:", self.station_events_file)
      

   def review_data(self):
      # quick review!
      for sd_vid in self.sd_clips:
         print(sd_vid, self.sd_clips[sd_vid].keys())
         if "custom_points" in self.sd_clips[sd_vid]:
            print(self.sd_clips[sd_vid]['custom_points'])

   def todict(self, obj, classkey=None):
      if isinstance(obj, dict):
          data = {}
          for k, v in obj.items():
              data[k] = self.todict(v, classkey)
          return data
      elif hasattr(obj, "_ast"):
          return self.todict(obj._ast())
      elif hasattr(obj, "__iter__") and not isinstance(obj, (str, bytes)):
          return [self.todict(v, classkey) for v in obj]
      elif hasattr(obj, "__dict__"):
          data = dict(
              (key, self.todict(value, classkey))
              for key, value in obj.__dict__.items()
              if not callable(value) and not key.startswith('_')
          )
          if classkey is not None and hasattr(obj, "__class__"):
              data[classkey] = obj.__class__.__name__
          return data
      elif isinstance(obj, (np.integer, np.floating, np.ndarray)):
          return obj.item()
      elif isinstance(obj, (datetime.date, datetime.datetime)):
          return obj.isoformat()
      elif isinstance(obj, bool):
          return 'true' if obj else 'false'  # Convert boolean to string representation
      else:
          return obj

   def todict_old(self, obj, classkey=None):
      if isinstance(obj, dict):
         data = {}
         for k, v in obj.items():
            data[k] = self.todict(v, classkey)
         return data
      elif hasattr(obj, "_ast"):
         return self.todict(obj._ast())
      elif hasattr(obj, "__iter__") and not isinstance(obj, (str, bytes)):
         return [self.todict(v, classkey) for v in obj]
      elif hasattr(obj, "__dict__"):
         data = dict(
            (key, self.todict(value, classkey))
            for key, value in obj.__dict__.items()
            if not callable(value) and not key.startswith('_')
         )
         if classkey is not None and hasattr(obj, "__class__"):
            data[classkey] = obj.__class__.__name__
         return data
      elif isinstance(obj, (np.integer, np.floating, np.ndarray)):
         return obj.item()
      elif isinstance(obj, (datetime.date, datetime.datetime)):
         return obj.isoformat()
      else:
         return obj

   
   def load_event(self, event_id):
      event_file = self.local_evdir + event_id + "/" + event_id + "-event.json"
      obs_file = self.local_evdir + event_id + "/" + event_id + "_OBS_DATA.json"
      pickle_file = self.local_evdir + event_id + "/" + event_id + "_trajectory.pickle"
      
      
      
      
      if os.path.exists(event_file):
         data = load_json_file(event_file)
      if os.path.exists(obs_file):
         data['obs'] = load_json_file(obs_file)
         for key in data['obs']:
            print(key)
       
      if os.path.exists(pickle_file) is False:
         print("NO PICKLE FILE!", pickle_file)
      all_obs_res = {}
      with open(pickle_file, 'rb') as handle:
         wmpl_data = pickle.load(handle)
         data['traj'] = self.todict(wmpl_data)
         data['obs_res'] = {}
         all_res = []
         for obs in data['traj']['observations']:
            #'h_residuals', 'h_res_rms', 'v_residuals', 'v_res_rms'
            data['obs_res'][obs['station_id']] = abs(np.median(obs['h_residuals'])) + abs(np.median(obs['v_residuals'])) / 2





      return(data, event_file)

   def refine_event(self, event_day, event_id):
      # event_calibs must be run to setup data file before running this
      # prompt : You are a quality assurance agent who is tasked with reviewing the data from 
      # meteor events. This data includes the observations, calibrations, trajectory and orbit data.
      # you will also see links for the observation videos and residual errors. 
      # you will know the current x,y position of the meteor and geo values for az and el 
      # with all of this information you will re-acquire and fit the x,y values and re-run the event solution (or parts of it)
      # to see if the residuals are improved. We will start by loading all of the data into a large json dictionary you can review
      
      # for each obs we must evaluate and improve the x,y values
      # the stars and catalog and lens dirstortion model
      # the photometry for the event
      # we must also syncronize the frames and times across observations 
      # we should also make a matrix of all frames and obs across stations for the entire event. 
      
      local_cache = self.local_evdir + event_id + "/CACHE/" 
      obs_urls = []
      os.makedirs(local_cache, exist_ok=True)
     
      # load the big data file 
      data,event_file = self.load_event(event_id)

      if "calibs" not in data:
         data['calibs'] = {}
      
      # sort the stations by the residuals and get the observation urls   
      for station_camera in sorted(data['obs_res'], key=data['obs_res'].get, reverse=True): 
         print("STATION CAM", station_camera)
         # 'fns', 'times', 'xs', 'ys', 'azs', 'els', 'ints'
         if station_camera not in data['obs_res']:
            print(station_camera, "NOT IN OBS RES!")
         elif station_camera not in data['calibs']:
            print(station_camera, "NOT IN CALIBS !")
         else:
            print(station_camera, data['obs_res'][station_camera], data['calibs'][station_camera]['obs_url'])
            obs_urls.append(data['calibs'][station_camera]['obs_url'])
      # download the video files to the local cache   
      self.download_cache_videos(obs_urls, local_cache) 
      
      marked_points = self.manual_mark_meteor(obs_urls, local_cache) 
      
      

      # retrack the observations
      self.retrack_event(obs_urls, local_cache, marked_points) 
      
      # display the multi frame frames 
      self.multi_frame_event(event_day, event_id ) 

   def multi_frame_event(self, event_day, event_id):
      local_cache = self.local_evdir + event_id + "/CACHE/" 
      mf_dir = self.local_evdir + event_id + "/CACHE/MF/" 
      os.makedirs(mf_dir, exist_ok=True)
      frame_data = load_json_file(local_cache + "frame_data.json")
      for datetime_str in sorted(frame_data):
         # need all of the keys as strings in an array
         frames = []
         for frame in frame_data[datetime_str].keys():
            frames.append(frame)
         
         #frame_data[datetime_str].keys()
         print(datetime_str, frames)
         image = multi_frame_image(frames)
         # add the datetime_str to the image
         cv2.putText(image, datetime_str,  (10,25), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 1)
         cv2.imshow('pepe', image)
         cv2.waitKey(30)
         ofile = mf_dir + datetime_str + ".jpg"
         cv2.imwrite(ofile, image)
      # cat files with ffmpeg into a mp4
      #cmd = "ffmpeg -r 25 -pattern_type glob -i " + mf_dir + "*.jpg -vf fps=25 -y " + mf_dir + "multi_frame.mp4"
      cmd = f"ffmpeg -r 25 -pattern_type glob -i '{mf_dir}*.jpg' -vf fps=25 -y '{local_cache}{event_id}_multi_frame.mp4'"
      print(cmd)
      #os.system(cmd)      
      print("saved:", mf_dir + "multi_frame.mp4")
      
   def retrack_event(self, obs_urls, local_cache, marked_points=None):
      frame_data = {}
      for url in obs_urls:
         if url in marked_points:
            start, middle, end = marked_points[url]
            mask_img = np.zeros((1080,1920),dtype=np.uint8)
            cv2.line(mask_img, (start[0], start[1]), (middle[0], middle[1]), (255,255,255), 25)
            cv2.line(mask_img, (middle[0], middle[1]), (end[0], end[1]), (255,255,255), 25)
         else:
            start, middle, end = None, None, None
            mask_img = np.zeros((1080,1920),dtype=np.uint8)
         
         fn = url.split("/")[-1].replace(".mp4", "")
         local_file = local_cache + url.split("/")[-1]
         local_frames_dir = local_cache + fn 
         print("track:", local_frames_dir)
         frame_data, mask_img = self.retrack_obs(local_frames_dir, frame_data, mask_img)
         #frame_data, mask_img = self.retrack_obs(local_frames_dir, frame_data, mask_img)
         
         print(frame_data)
      save_json_file(local_cache + "frame_data.json", frame_data)
      print("saved:", local_cache + "frame_data.json")

   def manual_mark_meteor(self, obs_urls, local_cache):
      manual_points_file = local_cache + "manual_points.json"
      if os.path.exists(manual_points_file) is True:
         manual_points = load_json_file(manual_points_file)
      else:
         manual_points = {}
      
      for url in obs_urls:
         if url not in manual_points:
            fn = url.split("/")[-1].replace(".mp4", "")
            stack_file = local_cache + fn + "-stacked.jpg"
            if os.path.exists(stack_file) is True:
               stack_img = cv2.imread(stack_file)
               start, middle, end = select_points(stack_img)
         else:
            manual_points[url] = [start, middle, end]
      save_json_file(manual_points_file, manual_points) 
      return(manual_points)
      
   def download_cache_videos(self, obs_urls, local_cache):
      print(obs_urls)
      for url in obs_urls:
         fn = url.split("/")[-1].replace(".mp4", "")
         stack_file = local_cache + fn + "-stacked.jpg"
         local_file = local_cache + url.split("/")[-1]
         local_frames_dir = local_cache + fn
         if os.path.exists(local_frames_dir) is False:
            os.makedirs(local_frames_dir)
         frame_count = len(glob.glob(local_frames_dir + "/*.jpg"))   

         if os.path.exists(local_file) is True:
            print("Already downloaded:", local_file)
         else:
            print("Downloading:", url)
            cmd = "wget " + url + " -P " + local_cache
            os.system(cmd)
         if frame_count == 0:
            print("Extracting frames:", local_file)
            cmd = "ffmpeg -i " + local_file + " -vf fps=25 " + local_frames_dir + "/%04d.jpg"
            os.system(cmd)
         else:
            print("Already extracted frames:", local_file)
         #if os.path.exists(stack_file) is False:
         if True:
            files = glob.glob(local_frames_dir + "/*.jpg")
            stack_img = None
            
            brightness = []
            for f in files:
               frame = cv2.imread(f)
               bright = np.sum(frame)
               brightness.append(bright)
               if len(brightness) > 25:
                  avg_bright = np.mean(brightness[0:25])
               else:
                  avg_bright = 0
               if stack_img is None:
                  stack_img = frame
               else:
                  if avg_bright == 0 or bright < avg_bright * 3: 
                     stack_img = np.maximum(stack_img, frame)
                  else:
                     cv2.imshow('pepe', frame)
                     cv2.waitKey(30)
                     print("BRIGHT:", bright, avg_bright * 3)
                     input("SKIP CAUSE IT IS TOO BRIGHT!")
            cv2.imwrite(stack_file, stack_img)      

   def make_median_frames(self, frame_files=None, frames=None):
      frames = []
      if frame_files is not None:
         for f in frame_files:
            frame = cv2.imread(f)
            frames.append(frame)
      med_frame = cv2.convertScaleAbs(np.median(np.array(frames), axis=0))
      return(med_frame)
         

   def filename_to_datestamp(self, file):
      # AMS87_2024_05_18_22_46_00_000_010870-trim-1050-1080p/0413.jpg
      parts = file.split("/")
      obs_id = parts[-2]
      frame_id = parts[-1].replace(".jpg", "")
      root_file = obs_id.split("-")[0]
      trim_num = obs_id.split("-")[2]
      extra_seconds = int(trim_num) / 25  
      extra_seconds += int(frame_id) / 25
      rparts = root_file.split("_")
      datetime_str = rparts[1] + "_" + rparts[2] + "_" + rparts[3] + "_" + rparts[4] + "_" + rparts[5] + "_" + rparts[6] + "_" + rparts[7]
      datetime_stamp = datetime.datetime.strptime(datetime_str, "%Y_%m_%d_%H_%M_%S_%f")
      # add extra seconds to datetime_stamp
      datetime_stamp = datetime_stamp + datetime.timedelta(seconds=extra_seconds) 
      return(datetime_stamp)


   def fit_line(self, xs, ys):
      # first a series of x and y values
      # fit a line to the x and y values
      # return the slope and y-intercept
      # y = mx + b
      # m = (nΣ(xy) − ΣxΣy) / (nΣ(x^2) − (Σx)^2)
      # b = (Σy − mΣx) / n
      n = len(xs)
      xy = np.sum(np.array(xs) * np.array(ys))
      x2 = np.sum(np.array(xs) * np.array(xs))
      x = np.sum(xs)
      y = np.sum(ys)
      m = (n * xy - x * y) / (n * x2 - x * x)
      b = (y - m * x) / n
      
      # find start and end of line on 1920,1080 sized image
      x1 = 0
      y1 = int(m * x1 + b)
      x2 = 1920
      y2 = int(m * x2 + b)
      
      return(x1,y1,x2,y2)
    
      
      
   def retrack_obs(self, local_frames_dir, frame_data, mask_img=None):
      # load the tracking data
      #frame_data = {}
      objects = {}
      files = glob.glob(local_frames_dir + "/*.jpg")
      med_frame = self.make_median_frames(files[0:10], None )
      sub1 = None
      # loop over each frame and collect data
      all_xs = []
      all_ys = []
      frame_nums= []
      frame_times = []
      frame_xs = []
      frame_ys = []
      frame_ws = []
      frame_hs = []
      frame_ints = []
      fc = 0
      stack_img = None
      
      # loop over each frame file
      for file in sorted(files):
         datetime_stamp = self.filename_to_datestamp(file)
         # convert datetime_stamp to string
         datetime_str = datetime_stamp.strftime("%Y_%m_%d_%H_%M_%S_%f")
         if datetime_str not in frame_data:
            frame_data[datetime_str] = {}
         if file not in frame_data[datetime_str]:
            frame_data[datetime_str][file] = {}
            frame_data[datetime_str][file]['xs'] = []
            frame_data[datetime_str][file]['ys'] = []
            frame_data[datetime_str][file]['ws'] = []
            frame_data[datetime_str][file]['hs'] = []
         
         frame = cv2.imread(file)
         if mask_img is not None:
            frame = cv2.subtract(frame, mask_img)
         sub = cv2.subtract(frame, med_frame)
         if stack_img is None:
            stack_img = sub
         # also take away the 1st sub 
         if sub1 is not None:
            sub = cv2.subtract(sub, sub1)
         else:
            sub1 = sub
            
         #thresh the sub
         thresh_val = 50
         thresh_val = int(np.max(sub) * .75)
         if thresh_val < 85:
            thresh_val = 85 
         _, thresh_img = cv2.threshold(sub, thresh_val, 255, cv2.THRESH_BINARY)
         cnts = get_contours_in_image(thresh_img)
         show_img = sub.copy()
         stack_img = np.maximum(stack_img, sub)
         
         # get contours from the sub image
         # sort cnts by size
         cnts = sorted(cnts, key=lambda x: x[2] * x[3], reverse=True)
         for x,y,w,h in cnts[0:3]:
            if w > h:
               rad = int(w/2)
            else:
               rad = int(h/2)
            if w < 2 or h < 2:
               continue
            frame_data[datetime_str][file]['xs'].append(x)
            frame_data[datetime_str][file]['ys'].append(y)
            frame_data[datetime_str][file]['ws'].append(w)
            frame_data[datetime_str][file]['hs'].append(h)
            # draw rectangle around the contour
            cv2.rectangle(show_img, (x, y), (x + w, y + h), (255, 255, 255), 1) 
            # draw circle
            cx = int(x + w/2)
            cy = int(y + h/2)
            meteor_flux = int(np.sum(sub))
            obj_id, objects = find_object(objects, fc,cx, cy, w, h, meteor_flux, hd=1, sd_multi=0, cnt_img=None,obj_tdist=90, datetime_str=datetime_str)
            all_xs.append(int(cx))
            all_ys.append(int(cy))
            cv2.circle(show_img, (cx,cy), rad, (255,255,255), 1) 
            cv2.putText(show_img, str(obj_id),  (cx,cy), cv2.FONT_HERSHEY_SIMPLEX, .8, (0,255,0), 1)
         fc += 1
            
         frame_data[datetime_str][file]['int'] = int(np.sum(sub))
         frame_data[datetime_str][file]['time'] = datetime_str
         frame_ints.append(int(np.sum(sub)/1000000))
         frame_times.append(datetime_stamp)
         cv2.imshow('pepe', show_img)
         cv2.waitKey(30)
      # finished looping frames the first time 
      #if mask_img is None: 
      mask_img = np.zeros((1080,1920),dtype=np.uint8) 
      for obj_id in objects:
         objects[obj_id] = analyze_object(objects[obj_id], hd=1,strict=0)
         print(obj_id, objects[obj_id]['report']['meteor'], objects[obj_id]['report']['bad_items'] ) 
         if objects[obj_id]['report']['meteor'] == 1:
            x1,y1,x2,y2 = find_best_fitting_line(objects[obj_id]['oxs'], objects[obj_id]['oys'])
            cv2.line(mask_img, (int(x1),int(y1)), (int(x2),int(y2)), (255,255,255), 200)
            for i in range(0, len(objects[obj_id]['oxs'])):
               x = objects[obj_id]['oxs'][i]
               y = objects[obj_id]['oys'][i]
               w = objects[obj_id]['ows'][i]
               h = objects[obj_id]['ohs'][i]
               if w > 10:
                  w = 10
               if h > 10:
                  h = 10
               cx = int(x + w/2)
               cy = int(y + h/2)
               #mask_img[y:y+h,x:x+w] = 255
               cv2.putText(show_img, str(obj_id),  (cx,cy), cv2.FONT_HERSHEY_SIMPLEX, .8, (0,255,0), 1)
               
               cv2.imshow('pepe', mask_img)
               cv2.waitKey(30)
               
      cv2.imshow('pepe', stack_img)
      cv2.waitKey(30)
      
      cv2.imshow('pepe', show_img)
      cv2.waitKey(30)
      
      cv2.imshow('pepe', mask_img)
      cv2.waitKey(30)
         
      print(frame_nums)    
      print(frame_ints)    
      print(frame_times)    
      #plot the frame_ints 
      plt.plot(frame_ints)
      plt.savefig('plot.png')
      img = cv2.imread('plot.png')
      img = cv2.resize(img, (1920,1080))
      cv2.imshow('pepe', img)
      cv2.waitKey(30)
      # invert the mask img
      mask_img = cv2.bitwise_not(mask_img)
      if len(mask_img.shape) == 2:
         mask_img = cv2.cvtColor(mask_img, cv2.COLOR_GRAY2BGR)
      cv2.imshow('pepe', mask_img)
      cv2.waitKey(30)
      
      return(frame_data, mask_img)


   def event_calibs(self, event_day, event_id):
      self.load_stations_file()
      # load event data
      data,event_file = self.load_event(event_id)
      # define output html
      cal_sources_html_file = self.local_evdir + event_id + "/" + event_id + "_CAL_SOURCES.html"
      obs = []
      # see if we already found the calibs
      if "calibs" in data:
         calibs = data['calibs']
         print("Loading existing calib data.")
         print(calibs)
         calibs = {}
      else:
         print("NO existing calib data.")
         calibs = {}
         
      for key in data:
         print("KEY", key)
         if key == "obs":
            for key2 in data[key]:
               print("KEY2", key2)
               obs.append(key2)
      obs_urls = {}
      for obs_id in obs:
         print("OBS:", obs_id)
         root_id = obs_id.split("-")[0]
         parts = root_id.split("_")
         station_id, year, month, day, hour, minute, second, millisecond,cam_id = parts
         calib_key = station_id + "-" + cam_id
         obs_url = f"https://archive.allsky.tv/{station_id}/METEORS/{year}/{year}_{month}_{day}/{obs_id}-1080p.mp4"
         print(obs_url)
         obs_urls[calib_key] = obs_url
         if calib_key not in calibs:
            calibs[calib_key] = {}       
            #save_json_file(event_file, data, True)
         # get an array of calibration files four our camera around our event date
         print("GET CALIB FILES FOR ", station_id, cam_id)
         calibs[calib_key]['files'] = self.get_calib_files(station_id, cam_id, year, month, day, hour, minute, second )
         
         calibs[calib_key]['obs_url'] = obs_url
      html = """
            <!DOCTYPE html>
             <html lang="en">
             <head>
                 <meta charset="UTF-8">
                 <meta name="viewport" content="width=device-width, initial-scale=1.0">
                 <title>Float Image Left</title>
                 <style>
                    .float-left {
                        float: left;
                        margin-right: 10px; /* Optional: Add some space to the right of the image */
                    }
                </style>
            </head>
            <body>

      """


      for key in calibs:
         if "_" in key :
            station_id = key.split("_")[0]
         else:
            station_id = key.split("-")[0]
            
         lat = self.station_dict[station_id]['lat']
         lon = self.station_dict[station_id]['lon']
         alt = self.station_dict[station_id]['alt']
         photo_credit = self.photo_credits[station_id]
         lat = self.station_dict[station_id]['lat']
         lon = self.station_dict[station_id]['lon']
         alt = self.station_dict[station_id]['alt']
         url = calibs[key]['obs_url'] 
         html += f"<div style='clear:both'></div><div><h1><a href={url}>{key}</a></h1>"
         html += f"<p>{lat} {lon} {alt}<br>{photo_credit}</p></div>"
         for meteor_obs in calibs[key]['files']:
            url = meteor_obs.replace("/mnt/", "https://")
            img = url.replace("-1080p.mp4", "-prev.jpg")
            print("\t",url) 
            html += f"<div class='float-left'><a href={url}><img src={img}></a></div>"
      fp = open(cal_sources_html_file, "w")
      fp.write(html)
      fp.close()
      print("saved", cal_sources_html_file)
      data['calibs'] = calibs

      # Serialize the dict to a JSON string using the custom encoder
      json_string = json.dumps(data, cls=CustomJSONEncoder)

      # Save the JSON string to a file or use it as needed
      with open(event_file, 'w') as file:
         file.write(json_string)

      calibs_file = event_file.replace("-event.json", "_CALIBS.json")
      calibs_string = json.dumps(calibs, cls=CustomJSONEncoder)
      with open(calibs_file, 'w') as file:
         file.write(calibs_string)

      
      #save_json_file(calibs_file, calibs)
      print("DATA", data.keys())
      print("SAVED EVENT FILE WITH CALIBS:", event_file)





   def get_calib_files(self, station_id, cam_id, year, month, day, hour, minute, second ):
      calib_files = []
      # determine a date range for the calib files of +/- 5 days around the event datetime passed into the function 
      datestamp = year + "_" + month + "_" + day + "_" + hour + "_" + minute + "_" + second
      date = datetime.datetime.strptime(datestamp, "%Y_%m_%d_%H_%M_%S")
      print("GETTING CALIB FILES")
      for i in range(-15,15):
         calib_date = date + datetime.timedelta(days=i)
         print("CALIB DATE", calib_date)
         calib_year = calib_date.strftime("%Y")
         calib_date = calib_date.strftime("%Y_%m_%d")
         calib_dir = f"/mnt/archive.allsky.tv/{station_id}/METEORS/{calib_year}/{calib_date}/" 
         wild = f"{calib_dir}{station_id}*{cam_id}*1080p.mp4"
         files = glob.glob(wild)
         calib_files.extend(files)
      return(calib_files)      

   def resolve_event(self, event_id):
      cv2.namedWindow('pepe')
      cv2.resizeWindow("pepe", self.win_x, self.win_y)

      date = self.event_id_to_date(event_id)
      self.load_stations_file()
      valid_obs = {}
      self.set_dates(date)

      # if the event has already run we might want to auto 
      # ignore some obs based on the last run's status or res. 
      # if a solution file exists we can check the res and ignore the worst
      # if it failed we can check time and intersections to weed out bad obs
      # or plane tests
      # 

      event_file = self.local_evdir + event_id + "/" + event_id + "-event.json"
      ignore_file = self.local_evdir + event_id + "/" + event_id + "_IGNORE.json"
      if os.path.exists(event_file) is True:
         event = load_json_file(event_file)
      else:
         event = {}

      if os.path.exists(ignore_file) is True:
         ignore = load_json_file(ignore_file)
      else:
         ignore = []

      ban = "/mnt/f/shadow_ban.json"
      banned = load_json_file(ban)
      for b in banned:
         print("BANNED:", b)
         ignore.append(b)
      # select main event info from the local sqlite DB
      print("IG", ignore)
      sql = """
            SELECT event_id, event_minute, revision, stations, obs_ids, event_start_time, event_start_times,
                   lats, lons, event_status, run_date, run_times
              FROM events
             WHERE event_id = ?
          ORDER BY run_date desc 
             LIMIT 1

      """
      vals = [event_id]
      self.cur.execute(sql, vals)
      rows = self.cur.fetchall()

      xx = 0
      invalid_obs = {}

      for row in rows:
         (event_id, event_minute, revision, stations, obs_ids, event_start_time, event_start_times,  \
                 lats, lons, event_status, run_date, run_times) = row
         stations = json.loads(stations)
         obs_ids = json.loads(obs_ids)
         event_start_times = json.loads(event_start_times)
         lats = json.loads(lons)
         temp_obs = {}

         #if "ignore" in event:
         #   ignore = event['ignore']

         for obs_id in obs_ids:



            ig = False
            for item in ignore:
               if item in obs_id:
                  ig = True
                  print("IGNORE:", item, "IS IN", obs_id)
                  continue
            # skip the ignored obs
            if ig is True:
               print("SKIP:", obs_id)
               continue
            st_id = obs_id.split("_")[0]
            obs_fn = obs_id.replace(st_id + "_", "")
            if st_id not in valid_obs:
               valid_obs[st_id] = self.get_valid_obs(st_id, date)

            vid = obs_id.replace(st_id + "_", "") + ".mp4"
            dict_key = obs_id + ".mp4"

            # here we should fetch the latest obs from AWS 
            # to make sure we pick up any edits?
            sd_vid = dict_key.replace(st_id + "_", "")
            if dict_key not in self.obs_dict:
               self.obs_dict[dict_key] = {}
            if True:
               if True:
                  self.obs_dict[dict_key]['loc'] = [float(self.station_dict[st_id]['lat']), float(self.station_dict[st_id]['lon']), float(self.station_dict[st_id]['alt'])]
                  # HERE WE SHOULD GET NEW OBS DATA DIRECT FROM DYNA DB OR REFRESH THE OBS DICT?
                  # CALL THE SEARCH OBS DYN FUNC FOR THIS! NOT HARD???

                  skip = False
                  dobs = get_obs(st_id, sd_vid)
                  if "aws_status" in dobs:
                     if dobs['aws_status'] is False:
                        skip = True
                  if skip is False:
                     self.update_event_obs(dobs)
                     dobs['loc'] = self.obs_dict[dict_key]['loc']
                     temp_obs = convert_dy_obs(dobs, temp_obs)
               else:
                  print(dict_key, "not in obsdict. try deleting the file.")
                  print( self.obs_dict_file)
         self.good_obs = temp_obs

         # HERE WE CAN ADD EXTRA OBS FROM OTHER NETWORKS LIKE FRIPON
         extra_obs_file = self.local_evdir + event_id + "/" + event_id + "_EXTRA_OBS.json"
         if os.path.exists(extra_obs_file) is True:
            extra_obs = load_json_file(extra_obs_file)
         else:
            extra_obs = {}
         for st in extra_obs:
            for vf in extra_obs[st]:
               obs_id = st + "_" + vf
               temp_obs[st] = extra_obs[st]

         ev_dir = self.local_evdir + "/" + event_id + "/"
         if os.path.exists(ev_dir) is False:
            os.makedirs(ev_dir)
         good_obs_file = ev_dir + "/" + event_id + "_GOOD_OBS.json"
         #if os.path.exists(good_obs_file) is False:
         save_json_file(good_obs_file, temp_obs, True)
         self.solve_event(event_id, temp_obs, 1, 1)
         xx += 1

      if True:
         ev_dir = self.local_evdir + "/" + event_id + "/"
         plane_file = ev_dir + "/" + event_id + "_PLANES.json"

         plane_report = self.plane_test_event(obs_ids, event_id, event_status, False)
         save_json_file(plane_file, plane_report, True)

         event['planes'] = plane_report['results']
         event['event_id'] = event_id
         self.make_plane_kml(event, plane_report['results'])

      cmd = "rsync -av --update " + self.local_evdir + "/" + event_id + "/* " + self.cloud_evdir + "/" + event_id + "/"
      print("SKIPPING (for now)", cmd)
      #os.system(cmd)


   def update_obs_intensity(self, event_id, obs_id, obs_data=None, frames=None):
      self.event_id = event_id
      el = obs_id.split("_") 
      station_id = el[0] 
      date = el[1] + "_" + el[2] + "_" + el[3]
      self.set_dates(date)
      local_event_dir = "/mnt/f/EVENTS/" + self.year + "/" + self.month + "/" + self.dom + "/" + self.event_id + "/" 
      self.ev_dir = local_event_dir 


      if obs_data is None:
         obs_data = self.obs_dict[obs_id]
      sd_vid = self.ev_dir + station_id + "_" + obs_data['sd_video_file']

      datetimes = [row[0] for row in obs_data['meteor_frame_data']]
      fns = [row[1] for row in obs_data['meteor_frame_data']]
      xs = [row[2] for row in obs_data['meteor_frame_data']]
      ys = [row[3] for row in obs_data['meteor_frame_data']]
      ws = [row[4] for row in obs_data['meteor_frame_data']]
      hs = [row[5] for row in obs_data['meteor_frame_data']]
      ints = [row[6] for row in obs_data['meteor_frame_data']]
      azs = [row[9] for row in obs_data['meteor_frame_data']]
      els = [row[10] for row in obs_data['meteor_frame_data']]
      


      frames = load_frames_simple(sd_vid)
      last_frame = None
      for i in range(0,len(fns)):
         fn = fns[i]
         frame = frames[fn]
         frame = cv2.resize(frame, (1920,1080))
         gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

         x = xs[i]
         y = ys[i]
         r = 10
         r = self.find_size(frame,int(x),int(y))
         meteor_int = do_photo(gray_frame, (x,y), r+1)
         print("INT:", i, meteor_int)
         cv2.circle(frame, (int(x),int(y)), int(r), (0,255,255),2)
         cv2.imshow('pepe', frame)
         cv2.waitKey(30)
      print("SD VID:", sd_vid)
      
   def find_size(self,img,x,y):
      start_val = np.mean(img[y,x])

      fwhms = []
      fwhm = None
      for i in range(0,150):
         nx = x + i
         if nx >= 1920:
            nx = 1919 
            continue
         val = np.mean(img[y,nx])
         perc = val / start_val  
         if fwhm is None and (perc < .50 or val < 80):
            #print("*** X+", i, "VAL", nx,y,val, perc)
            fwhm = i
            fwhms.append(i)
            continue

      fwhm = None
      for i in range(0,150):
         nx = x - i
         if nx <= 0:
            nx = 0 
            continue
         val = np.mean(img[y,nx])
         perc = val / start_val  
         if fwhm is None and (perc < .50 or val < 80):
            fwhm = i
            fwhms.append(i)
            #print("*** X-", i, "VAL", nx,y,val, perc)
            break 

      fwhm = None
      for i in range(0,150):
         ny = y + i
         if ny >= 1080:
            ny = 1079 
            continue
         val = np.mean(img[ny,x])
         perc = val / start_val  
         if fwhm is None and (perc < .50 or val < 80):
            fwhm = i
            fwhms.append(i)
            #print("*** Y+", i, "VAL", x,ny,val, perc)
            break 

      fwhm = None
      for i in range(0,150):
         ny = y - i
         if ny <= 0:
            ny = 0  
            continue
         val = np.mean(img[ny,x])
         perc = val / start_val  
         if fwhm is None and (perc < .50 or val < 80):
            fwhm = i
            fwhms.append(i)
            #print("*** Y-", i, "VAL", x,y,val, perc)
            break 

      if len(fwhms) > 0 :
         mf = np.mean(fwhms)
         if mf > 5:
            return(np.mean(fwhms))
         else:
            return(5)
      else:
         return(10)

   def update_event_obs(self, obs):
      if "meteor_frame_data" not in obs:
         return() 
      if "aws_status" in obs:
         if obs['aws_status'] is False:
            print("false aws status, maybe this is a deleted obs?")
            return()
      obs_id = obs['station_id'] + "_" + obs['sd_video_file'].replace(".mp4", "")
      temp_ev_id = obs['sd_video_file'][0:16]
      datetimes = [row[0] for row in obs['meteor_frame_data']]
      fns = [row[1] for row in obs['meteor_frame_data']]
      xs = [row[2] for row in obs['meteor_frame_data']]
      ys = [row[3] for row in obs['meteor_frame_data']]
      ints = [row[6] for row in obs['meteor_frame_data']]
      azs = [row[9] for row in obs['meteor_frame_data']]
      els = [row[10] for row in obs['meteor_frame_data']]
      sql = """
         UPDATE event_obs SET fns = ?, times = ?, xs = ?, ys = ?, azs = ? , els = ?, ints = ?
                        WHERE obs_id = ?
      """
      ivals = [json.dumps(fns), json.dumps(datetimes), json.dumps(xs), json.dumps(ys), json.dumps(azs), json.dumps(els), json.dumps(ints), obs_id]
      self.cur.execute(sql,ivals)
      self.con.commit()
      

   def make_event_page(self, event_id):
      event_day = self.event_id_to_date(event_id)
      self.set_dates(event_day)
      good_obs_file = self.local_evdir + event_id + "/" + event_id + "_GOOD_OBS.json"   
      temp_obs = load_json_file(good_obs_file)
      dynamodb = boto3.resource('dynamodb')
      solve_dir = self.local_evdir + event_id + "/" 
      event_report(dynamodb, event_id, solve_dir, solve_dir, temp_obs)

   def day_load_solves(self, date):
      # uses self.update_obs_ids(event_id,obs_ids)

      solve_jobs = []
      self.set_dates(date)
      self.load_stations_file()
      self.errors = []
      if os.path.exists(self.obs_review_file) is True:
         self.ai_data = load_json_file(self.obs_review_file)
      else:
         self.ai_data = {}
      sql = """
            SELECT event_id, event_minute, revision, stations, obs_ids, event_start_time, event_start_times,  
                   lats, lons, event_status, run_date, run_times
              FROM events
             WHERE event_minute like ?
      """
      vals = [date + "%"]
      self.cur.execute(sql, vals)
      rows = self.cur.fetchall()
      print("ROWS:", len(rows))
      print("OBS DICT:", len(self.obs_dict.keys()))
      c = 1
      self.temp_obs = {}
      self.event_sol_data = {}
      self.event_sql_data = {}

      for row in rows:
         (event_id, event_minute, revision, stations, obs_ids, event_start_time, event_start_times,  \
                 lats, lons, event_status, run_date, run_times) = row
         self.event_sql_data[event_id] = (event_id, event_minute, revision, stations,  obs_ids, \
                 event_start_time, event_start_times, lats, lons, event_status, run_date, run_times)
         # decode json saved data
         stations = json.loads(stations)
         obs_ids = json.loads(obs_ids)
         event_start_times = json.loads(event_start_times)
         lats = json.loads(lons)

         #loop over obs and check for dupes
         for ob_id in obs_ids:
            if ob_id not in self.temp_obs :
               self.temp_obs[ob_id] = 0
            self.temp_obs[ob_id] += 1
            if self.temp_obs[ob_id] > 1:
               print("DUPE OBS USED!", ob_id, event_id)
         print("EV:",c,  event_id, event_status )
         c += 1

         # load the event.json

         ev_json_file = self.local_evdir + event_id + "/" + event_id + "-event.json"
         if os.path.exists(ev_json_file) is True:
            ev_data = load_json_file(ev_json_file)
            
         else:
            print(ev_json_file, "NOT FOUND!")
            ev_data = None
         self.event_sol_data[event_id] = ev_data

      # now all data is loaded into the arrays.
      # first make sure the SQL summary / event status is accurate 
      # to what is on the file system. Update as needed. 
      for event_id in self.event_sql_data:
         (tevent_id, event_minute, revision, stations,  obs_ids, event_start_time, event_start_times, 
                 lats, lons, event_status, run_date, run_times) = self.event_sql_data[event_id]
         if event_id in self.event_sol_data:
            sol_data = self.event_sol_data[event_id]
         else:
            sol_data = None
            self.event_sol_data[event_id] = None
         if sol_data is not None:
            sol_data['event_status'] = event_status
            (sol_status, v_init, v_avg, start_ele, end_ele, a, e) = self.eval_sol(sol_data)
            self.event_sol_data[event_id]['sol_status'] = sol_status
            print(event_id, sol_status)
            if a < 0 or e >= 1 or start_ele > 160000:
               event_status = "SOLVED:BAD"

            elif "GOOD" in sol_status:
               event_status = "SOLVED:GOOD"
            else:
               event_status = "SOLVED:BAD"
            sql = "UPDATE events set event_status = ? WHERE event_id = ?"
            vals = [event_status, event_id]
            print(sql, vals)
            self.cur.execute(sql, vals)
            self.con.commit()

            if "BAD" in sol_status:
               self.event_sol_data[event_id]['event_status'] = "BAD"
            # OBS STUFF / AI?
            #self.view_obs_ids(date, obs_ids)
            self.update_obs_ids(event_id,obs_ids)
            #print(event_status, sol_data.keys())
         else:
            self.update_obs_ids(event_id,obs_ids)

   def update_obs_ids(self, event_id, obs_ids):
      if isinstance(obs_ids, str) is True:
         obs_ids = json.loads(obs_ids)


      for ob_id in obs_ids:
         sql = "UPDATE event_obs set event_id = ? WHERE obs_id = ?"
         vals = [event_id, ob_id]
         print(sql, vals)
         self.cur.execute(sql, vals)
         self.con.commit()

   def eval_sol(self, data):
      event_status = data['event_status']
      v_init = round(data['traj']['v_init'] / 1000,2)
      v_avg = round(data['traj']['v_avg'] /1000,2)
      if "end_ele" in data['traj']:
        end_ele = round(data['traj']['end_ele']  / 1000,2)
        start_ele = round(data['traj']['start_ele'] / 1000,2)
      else:
        end_ele = 0
        start_ele = 0

      if "orb" in data:
         if data['orb'] is not None:
            if data['orb']['a'] is not None:
               a = data['orb']['a'] 
               e = data['orb']['e'] 
            else:
               a = -1
               e = 99
         else:
            a = -1
            e = 99
      else:
         a = -1
         e = 99
      sol_status = ""
      if v_init > 100 or v_avg > 100:
         sol_status += "BAD_VEL;"
      if start_ele >= 200 or start_ele < 0:
         sol_status += "BAD_TRAJ_START;"
      if end_ele >= 200 or end_ele < 0:
         sol_status += "BAD_TRAJ_END;"
      if a < 0:
         sol_status += "BAD_ORB_a;"
      if e > 1:
         sol_status += "BAD_ORB_e;"
      if sol_status == "":
         sol_status = "GOOD"

      return(sol_status, v_init, v_avg, start_ele, end_ele, a, e)

   def check_ai(self, ai_data):
      print(ai_data)
      meteor_obj_conf = 0
      meteor_prev_conf = 0
      if "objects" in ai_data:
         for row in ai_data['objects']:
            con = row[0]
            if con > 50:
               meteor_obj_conf = con
      if "ai" in ai_data:
         meteor_prev_conf = ai_data['ai']['meteor_prev_yn']
      print("METEOR OBJ FOUND:", meteor_obj_conf)
      print("METEOR PREV FOUND:", meteor_prev_conf)
      return(meteor_obj_conf, meteor_prev_conf)

   def view_obs_ids(self, date, obs_ids):
      year = date[0:4]
      imgs = []
      self.missing_prev_files = {}
      if isinstance(obs_ids, str) is True:
         obs_ids = json.loads(obs_ids)

      for ob_id in obs_ids:
         if "AMS" in ob_id:
            st_id = ob_id.split("_")[0]
         sd_vid = ob_id.replace(st_id + "_", "") + ".mp4" 
         if sd_vid in self.ai_data:
            label_data = self.ai_data[sd_vid]
            conf1, conf2 = self.check_ai(label_data)
         else:
            label_data = None
            local_prev_dir = self.local_evdir + "OBS/" 
            if os.path.exists(local_prev_dir) is False:
               os.makedirs(local_prev_dir)
            
            cloud_prev_file = "/mnt/archive.allsky.tv/" + st_id + "/METEORS/" + year + "/" + date + "/" + ob_id + "-prev.jpg"
            local_prev_file = self.local_evdir + "OBS/" + ob_id + "-prev.jpg"
            local_prev_file_alt = self.local_evdir + sd_vid.replace(".mp4", "-prev.jpg")
            if os.path.exists(local_prev_file_alt) is True:
               cmd = "mv " + local_prev_file_alt + " " + local_prev_file
               print("MOVE MIS_NAMED LOCAL FILE!")
               print(cmd)
               os.command(cmd)

            print(cloud_prev_file)
            print("NO AI DATA!!!")
            if os.path.exists(local_prev_file) is False:
               print("NO LOCAL PREV FILE!", local_prev_file)
               if os.path.exists(cloud_prev_file) is False:
                  print("NO CLOUD PREV FILE!", cloud_prev_file)
                  self.missing_prev_files[ob_id] = cloud_prev_file
                  self.reject_obs(st_id, ob_id, "NO PREV FILE")
               else:
                  cmd = "cp " + cloud_prev_file + " " + local_prev_file
                  print("COPY THE FILE!", cmd)
                  os.system(cmd)

         ev_file = self.local_evdir + "OBS/" + ob_id + "-prev.jpg"
         if os.path.exists(ev_file) is False:
            ev_file = ev_file.replace(st_id + "_", "")         
         if os.path.exists(ev_file) is True:
            img = cv2.imread(ev_file)
            imgs.append(img)
            print("LABELS:", label_data)
            cv2.imshow('pepe', img)
            cv2.waitKey(30)
         print(ev_file)
      print("MISSING PREV FILES:", len(self.missing_prev_files.keys()))

   def reject_obs(self, st_id, ob_id, reject_desc):
      sql = "INSERT OR REPLACE INTO rejected_obs (obs_id, reject_desc) VALUES(?,?)" 
      if st_id not in ob_id:
         ob_id = st_id + "_" + ob_id
      vals = [ob_id, reject_desc]
      self.cur.execute(sql, vals)
      self.con.commit()
      print("REJECTED:", st_id, ob_id, reject_desc)

      sql = "UPDATE event_obs set ignore = 1, status = ? WHERE obs_id = ?"
      vals = [reject_desc, ob_id]
      self.cur.execute(sql, vals)
      self.con.commit()


   def day_solve(self, date=None,force=0):
      solve_jobs = []
      done_jobs = []
      self.set_dates(date)
      self.load_stations_file()
      self.errors = []
      sql = """
            SELECT event_id, event_minute, revision, stations, obs_ids, event_start_time, event_start_times,  
                   lats, lons, event_status, run_date, run_times
              FROM events
             WHERE event_minute like ?
      """
      vals = [date + "%"]
      self.cur.execute(sql, vals)
      rows = self.cur.fetchall()
      for row in rows:
         (event_id, event_minute, revision, stations, obs_ids, event_start_time, event_start_times,  \
                 lats, lons, event_status, run_date, run_times) = row
         
         print("LOADING EVENT FROM LOCAL SQL:", event_id, event_status)
         stations = json.loads(stations)
         obs_ids = json.loads(obs_ids)
         event_start_times = json.loads(event_start_times)
         lats = json.loads(lons)
         temp_obs = {}
         if event_status == "SOLVED":
            continue
         for obs_id in obs_ids:
            st_id = obs_id.split("_")[0]
            vid = obs_id.replace(st_id + "_", "") + ".mp4"
            dict_key = obs_id + ".mp4"
            if st_id not in temp_obs:
               temp_obs[st_id] = {}
            if vid not in temp_obs[st_id]:
               try:
                  self.obs_dict[dict_key]['loc'] = [float(self.station_dict[st_id]['lat']), float(self.station_dict[st_id]['lon']), float(self.station_dict[st_id]['alt'])]
                  temp_obs = convert_dy_obs(self.obs_dict[dict_key], temp_obs)
               except:
                  print("Geo error with station!", st_id)
                  self.errors.append(("STATION GEO ERROR", st_id))

         #for st in temp_obs:
         #   for vd in temp_obs[st]:
         #      print(temp_obs[st][vd].keys())

      
         if event_status == "PENDING":
            solve_jobs.append((event_id, event_status, temp_obs))
         else:
           done_jobs.append((event_id, event_status, temp_obs))

         #self.solve_event(event_id, temp_obs, 1, force)
         
      cmd = "rsync -auv " + self.local_evdir + "/* " + self.cloud_evdir + "/"
      print(cmd)
      #os.system(cmd)
      #for job in solve_jobs:
      #   print("JOB:", job[0], job[1])
      print("Jobs to solve:", len(solve_jobs))
      print("Done jobs:", len(done_jobs))
      time.sleep(5)
      self.run_jobs(solve_jobs)
      #for job in solve_jobs:
      #   print(job[0], job[1])
      print("FINISHED RUN JOBS!", len(solve_jobs))

   def fast_cmds(self, jobs):
      # parallel process list of system cmds
      thread = {}
      if os.path.exists("cores.json") == 1:
         temp = load_json_file("cores.json")
         cores = temp['cores']
      else:
         cores = 4
      if cores > len(jobs):
         cores = 4
      cc = 0

      jobs_per_proc = int(len(jobs)/(cores-1))
      for i in range(0,cores):
         start = i * jobs_per_proc
         end = start + jobs_per_proc + 1
         if end > len(jobs):
            end = len(jobs)
         print(i, start, end)
         thread[i] = Process(target=self.cmd_runner, args=("thread" + str(i), jobs[start:end]))

      for i in range(0,cores):
         thread[i].start()
      for i in range(0,cores):
         thread[i].join()

   def cmd_runner(self, thread_number, cmds):
      for cmd in cmds:
         print("RUN", thread_number, cmd)
         os.system(cmd)

   def run_jobs(self, jobs):
      thread = {}
      if os.path.exists("cores.json") == 1:
         temp = load_json_file("cores.json")
         cores = temp['cores']
      else:
         cores = 4
      if cores > len(jobs):
         cores = 4
      cc = 0

      jobs_per_proc = int(len(jobs)/(cores-1))
      for i in range(0,cores):
         start = i * jobs_per_proc
         end = start + jobs_per_proc + 1
         if end > len(jobs):
            end = len(jobs)
         print(i, start, end)
         thread[i] = Process(target=self.wmpl_worker, args=("thread" + str(i), jobs[start:end]))

      for i in range(0,cores):
         thread[i].start()
      for i in range(0,cores):
         thread[i].join()

   def run_plane_jobs(self, jobs, force=False):
      thread = {}
      if os.path.exists("cores.json") == 1:
         temp = load_json_file("cores.json")
         cores = temp['cores']
      else:
         cores = 4
      if cores > len(jobs):
         cores = 4
      cc = 0

      jobs_per_proc = int(len(jobs)/(cores-1))
      for i in range(0,cores):
         start = i * jobs_per_proc
         end = start + jobs_per_proc + 1
         if end > len(jobs):
            end = len(jobs)
         #print(i, start, end)
         # CHANGE THIS LINE FOR DIFFERENT JOB
         thread[i] = Process(target=self.plane_worker, args=("thread" + str(i), jobs[start:end], force))

      for i in range(0,cores):
         thread[i].start()
      for i in range(0,cores):
         thread[i].join()

   def plane_worker(self, thread_number, job_list,force=False):
      for i in range(0,len(job_list)):
         event_id = job_list[i][0]
         key = job_list[i][1]
         ekey = event_id + "_" + key
         ob1 = job_list[i][2]
         ob2 = job_list[i][3]
         gd = ["GOOD", key, ob1, ob2]
         temp = self.r.get(ekey)
         if force is True:
            temp = None
         if temp is None:
            temp = self.plane_solve(gd)
            if len(temp) == 2:
               result,sanity = temp
            else:
               result = 99
               sanity = 99
            self.r.set(ekey, json.dumps([result,sanity]))
         else:
            result, sanity = json.loads(temp)
         #self.solve_event(event_id, temp_obs, 1, force)


   def wmpl_worker(self, thread_number, job_list):
      for i in range(0,len(job_list)):
         #print("WORKEr:", thread_number, job_list[i][0], job_list[i][1])
         event_id = job_list[i][0] 
         event_status = job_list[i][1] 
         temp_obs = job_list[i][2] 
         force = 1
         self.solve_event(event_id, temp_obs, 1, force)

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

      stats_data["STATUS_SOLVED"] = 0
      stats_data["STATUS_FAILED"] = 0

      vals = [event_day + "%"]
      self.cur.execute(sql, vals)
      rows = self.cur.fetchall()
      for row in rows:
         event_count = row[0]
         event_status = row[1]
         print("ROW", event_count, event_status)
         stats_data["STATUS_" + event_status] = event_count

      station_data = {}

      sql = """
         SELECT count(*) 
           FROM event_obs
      """

      vals = [event_day + "%"]
      self.cur.execute(sql)
      rows = self.cur.fetchall()
      stats_data["TOTAL_OBS"] = rows[0][0]

      stats_data["by_station"] = []
      sql = """
         select station_id, count(*) from event_obs group by station_id;
      """
      self.cur.execute(sql)
      rows = self.cur.fetchall()

      for row in rows:
         st, count = row


         stats_data["by_station"].append((st,count))

      stats_data["all_events"] = []
      sql = """
         select event_id from events 
      """
      self.cur.execute(sql)
      rows = self.cur.fetchall()

      for row in rows:
         event_id = row[0]

         failed_file = self.local_evdir + event_id + "/" + event_id + "-fail.json"
         solve_file = self.local_evdir + event_id + "/" + event_id + "-event.json"
         if os.path.exists(solve_file) is True:
            status = "SOLVED"
            event_data = load_json_file(solve_file)
         elif os.path.exists(failed_file) is True:
            status = "FAILED"
            event_data = load_json_file(failed_file)
         else:
            status = "PENDING"
            event_data = {}

         print(status, solve_file)
         stats_data["all_events"].append((event_id,status, event_data))






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

   def update_all_event_status(self, event_day):
      event_day = event_day.replace("_", "")
      event_day = event_day.replace("-", "")
      event_day = event_day.replace("/", "")
      sql = """
         SELECT event_id, event_minute, revision, event_start_time, event_start_times, 
                stations, obs_ids, lats, lons, event_status, run_date, run_times
           FROM events
          WHERE event_id like ?
      """
      vals = [event_day + '%']
      self.cur.execute(sql, vals)
      rows = self.cur.fetchall()
      for row in rows:
         ev_id = row[0]
         print(ev_id)
         self.check_event_status(ev_id)


   def check_event_status(self, event_id):
      # is the event defined in the .json files ? 
      # does the event exist in the allsky-s3 
      # does the event exist in the local filesystem
      # is the event in the sql db ?
      # is the event in the dynamodb ?
      # are there duplicates of this event on the local file system, s3f3, in sql or in dyanomdb

      # when we are done we should have the full event data object that goes to DYNA and also goes in the event.json file
      # if the event failed, or the event is pending we should still return the compele event.json data as best as we can.
      self.status_data = {}
      event_data = {}
      event_day = self.event_id_to_date(event_id)

      y,m,d = event_day.split("_")
      self.s3_event_day_dir = "/mnt/allsky-s3/EVENTS/" + y + "/" + m + "/" + d + "/"
      self.s3_event_id_dir = self.s3_event_day_dir + event_id + "/"

      self.cloud_event_day_dir = "/mnt/archive.allsky.tv/EVENTS/" + y + "/" + m + "/" + d + "/"
      self.cloud_event_id_dir = self.cloud_event_day_dir + event_id + "/"

      self.local_event_day_dir = self.data_dir + "EVENTS/" + y + "/" + m + "/" + d + "/"
      self.local_event_id_dir = self.local_event_day_dir + event_id + "/"



      # see if it is already up to date?
      sql_data = self.sql_select_event(event_id)
      if len(sql_data) > 0:
         self.event_in_sql = True
      else:
         self.event_in_sql = False

      if False:
      #if sql_data[9] != "PENDING" and sql_data[9] != "FAILED" and sql_data[9] != "SOLVED":
         try:
            self.status_data = json.loads(sql_data[9])
            self.local_event_id_dir = self.local_event_day_dir + event_id + "/"
            if "solve_status" in self.status_data:
               donothing = 1
               #return(self.status_data['solve_status'])

         except:
            print(sql_data[9])


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


      self.status_data['cloud_files'] = self.cloud_files
      self.status_data['local_files'] = self.local_files
      self.status_data['s3_files'] = self.s3_files

      if len(self.local_files) > 10 or len(self.s3_files) > 10:
         self.event_status = "SOLVED"
      elif "failed" in self.local_files or "failed" in self.s3_files and "event" not in self.local_files:
         self.event_status = "FAILED"
      else :
         self.event_status = "PENDING"

      self.status_data['event_status'] = self.event_status 

      if len(self.s3_files) == len(self.local_files) or len(self.s3_files) > len(self.local_files):
         self.event_archived = True
      else:
         self.event_archived = False

      self.status_data['event_archived'] = self.event_archived

      if os.path.exists(self.local_event_id_dir + event_id + "-fail.json") is True:
         try:
            self.event_fail_json = load_json_file(self.local_event_id_dir + event_id + "-fail.json")
         except:
            os.remove(self.local_event_id_dir + event_id + "-fail.json")
      elif os.path.exists(self.s3_event_id_dir + event_id + "-fail.json") is True:
         self.event_fail_json = load_json_file(self.s3_event_id_dir + event_id + "-fail.json")
      else:
         self.event_fail_json = None 

      if os.path.exists(self.local_event_id_dir + event_id + "-event.json") is True:
         try:
            self.event_json = load_json_file(self.local_event_id_dir + event_id + "-event.json")
         except:
            os.remove(self.local_event_id_dir + event_id + "-event.json")
      elif os.path.exists(self.s3_event_id_dir + event_id + "-event.json") is True:
         self.event_json = load_json_file(self.s3_event_id_dir + event_id + "-event.json")
      else:
         self.event_json = None 

      if os.path.exists(self.local_event_id_dir + event_id + "_GOOD_OBS.json") is True:
         try:
            self.good_obs_json = load_json_file(self.local_event_id_dir + event_id + "_GOOD_OBS.json")
         except:
            print("BAD FILE!", self.local_event_id_dir + event_id + "_GOOD_OBS.json")
            return()
            #os.remove(self.local_event_id_dir + event_id + "_GOOD_OBS.json")

      elif os.path.exists(self.s3_event_id_dir + event_id + "_GOOD_OBS.json") is True:
         self.good_obs_json = load_json_file(self.s3_event_id_dir + event_id + "_GOOD_OBS.json")
      elif os.path.exists(self.cloud_event_id_dir + event_id + "_GOOD_OBS.json") is True:
         self.good_obs_json = load_json_file(self.cloud_event_id_dir + event_id + "_GOOD_OBS.json")
      else:
         self.good_obs_json = None 
         print("GOOD OBS FILE NOT FOUND!", self.local_event_id_dir + event_id + "_GOOD_OBS.json" )
         return()
             
      print("Dirs :", self.local_event_id_dir, self.s3_event_id_dir)
      print("Local:", self.local_dir_exists, len(self.local_files))
      print("S3   :", self.s3_dir_exists, len(self.s3_files))
      print("Event Status:", self.event_status)
      print("Event Archived:", self.event_archived)
      self.status_data['local_event_id_dir'] = self.local_event_id_dir
      self.status_data['cloud_event_id_dir'] = self.cloud_event_id_dir
      self.status_data['event_status'] = self.event_status

      #if self.event_json is not None:
      #   print(self.event_json.keys())


      print("Event in SQL:", self.event_in_sql)
      #for i in range(0,len(sql_data)):
      #   print(i, sql_data[i])
      self.status_data['event_in_sql'] = self.event_in_sql

      dyna_data = self.get_dyna_event(event_id)



      if dyna_data is None:
         print("NO DYNA DATA:", self.event_in_sql)
         self.status_data['solve_status'] = None
         self.status_data['dyna'] = False 
      elif "solve_status" in dyna_data:
         self.status_data['dyna'] = True
         self.status_data['solve_status'] = dyna_data['solve_status']

      # update the event status field
      now_dt = datetime.datetime.now().strftime("%Y_%m_%d %H:%M:%S")
      sql = """
         UPDATE events SET event_status = ?,
                run_date = ?,
                revision = revision + 1,
                run_times = run_times + 1
          WHERE event_id = ?
      """
      #uvals = [json.dumps(self.status_data), now_dt, event_id]
      uvals = [self.event_status, now_dt, event_id]
      self.cur.execute(sql,uvals)
      self.con.commit()

      return(self.status_data['solve_status'])
 
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


      #print("STATUS DATA?", self.status_data)
      if self.good_obs_json is None:
         if "local_files" in self.status_data:
             
            #print("LOADING:", self.local_event_id_dir + event_id + "_GOOD_OBS.json")
            time.sleep(.1)
            try:
               self.good_obs_json = json.loads(self.local_event_id_dir + event_id + "_GOOD_OBS.json")
            except:
               print("FAILED TO LOAD:", self.local_event_id_dir + event_id + "_GOOD_OBS.json")
         #print("STATUS DATA?", self.status_data)
      
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
         return()

      if os.path.exists(self.local_event_id_dir + event_id + "-event.json") is True:
         self.event_json = load_json_file(self.local_event_id_dir + event_id + "-event.json")
      elif os.path.exists(self.s3_event_id_dir + event_id + "-event.json") is True:
         self.event_json = load_json_file(self.s3_event_id_dir + event_id + "-event.json")
      else:
         self.event_json = None


      if self.event_json is not None:
         event['solution'] = self.event_json
         event['solve_status'] = "SOLVED"
      elif self.event_fail_json is not None:
         event['solve_status'] = "FAILED"
      else:
         event['solve_status'] = "PENDING"
      

      return(event)

   def solve_event(self,event_id, temp_obs, time_sync, force):
      ev_dir = self.local_evdir + "/" + event_id
      if os.path.exists(ev_dir) is False:
         os.makedirs(ev_dir)
      good_obs_file = ev_dir + "/" + event_id + "_GOOD_OBS.json"


      if os.path.exists(ev_dir) is False:
         os.makedirs(ev_dir)

      # only solve if it has not already been solved.
      failed_file = ev_dir + "/" + event_id + "-fail.json"
      solve_file = ev_dir + "/" + event_id + "-event.json"
      save_json_file(good_obs_file, temp_obs, True)

      self.event_status = self.check_event_status(event_id)
      print("CURRENT STATUS FOR EVENT.", self.event_status)
      event_status = self.event_status
      solve_status = self.event_status

      if (self.event_status == "SOLVED" ) and force != 1:
         print("Already done this.")
         return() 


      if (os.path.exists(failed_file) is False and os.path.exists(solve_file) is False) or force == 1:
         print("Saving:" ,good_obs_file)

         new_run = True

         #solve_status = WMPL_solve(event_id, temp_obs, time_sync, force)
         try:
            print("RUNNING WMPL...")
            solve_status = WMPL_solve(event_id, temp_obs, time_sync, force)
         except Exception as e:
            print("*** EXCEPTION: WMPL_solve FAILED TO RUN!", str(e))
            #solve_status = WMPL_solve(event_id, temp_obs, time_sync, force)
         try:
            self.make_event_page(event_id)
         except:
            print("*** EXCEPTION: Make event page FAILED TO RUN!")
            status = "FAILED"
            self.make_event_page(event_id)

      else:
         print("WMPL ALREADY RAN...")
         new_run = False
         solve_status = "PENDING"

      print("WMPL SOLVE STATUS:", event_id, solve_status)
      if solve_status == "FAILED":
         time_sync=0
         print("IT LOOKS LIKE THE TIME SYNC FAILED. ")
         #solve_status = WMPL_solve(event_id, temp_obs, time_sync, force)
         #print("TRIED A SECOND TIME WITHOUT TIME SYNC!", solve_status)

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

         temp = self.good_obs_to_event(event_day, event_id)
         for key in temp:
            event_data[key] = temp[key]




         good_obs_file = self.local_evdir + event_id + "/" + event_id + "_GOOD_OBS.json"
         self.good_obs_json = load_json_file(good_obs_file)
         temp = self.good_obs_to_event(event_day, event_id)
         for key in temp:
            event_data[key] = temp[key]


         insert_meteor_event(self.dynamodb, event_id, event_data)
         cmd = "./plotTraj.py " + event_id
         print("DISABLED:", cmd)
         #os.system(cmd)

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

      print("DONE", event_id)

   def make_ai_img(self,prev_img,rx1,ry1,rx2,ry2):
      rx1,ry1,rx2,ry2 = int(rx1),int(ry1),int(rx2),int(ry2)  
      src_img = cv2.resize(prev_img, (1920,1080))
      show_img = cv2.resize(prev_img, (1920,1080))
      prev_img = cv2.resize(prev_img, (320,180))

      cv2.rectangle(show_img, (int(rx1), int(ry1 )), (int(rx2) , int(ry2) ), (255, 255, 255), 2)
      #print("SHOW IMG", show_img.shape)
      #cv2.imshow('inside make ai_img', show_img)
      
      #rx1 = 0
      #ry1 = 0
      if True:
         if True:
            gray_img = cv2.cvtColor(src_img, cv2.COLOR_BGR2GRAY)
         
            gray_roi = gray_img[ry1:ry2,rx1:rx2]
            if gray_roi is not None:
               print(rx1,ry1,rx2,ry2)
               #cv2.imshow('gray roi', gray_roi)

            min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(gray_roi)

            # V2 ROI is 64/64
            # V1 ROI is 224/224!

            ax1 = rx1 + mx - 112
            ax2 = rx1 + mx + 112
            ay1 = ry1 + my - 112
            ay2 = ry1 + my + 112

            w = ax2 - ax1
            h = ay2 - ay1
            if ax1 < 0:
               ax1 = 0
               ax2 = w
            if ay1 < 0:
               ay1 = 0
               ay2 = h
            if ax2 > 1920:
               ax2 = 1920
               ax1 = 1920 - w
            if ay2 > 1080:
               ay2 = 1080
               ay1 = 1080 - h

            ay1 = int(ay1 / 6)
            ay2 = int(ay2 / 6)
            ax1 = int(ax1 / 6)
            ax2 = int(ax2 / 6)
            ai_img = prev_img[ay1:ay2,ax1:ax2]
            print("MADE AI IMG:", ax1,ay1,ax2,ay2) 
            cv2.rectangle(src_img, (int(ax1), int(ay1 )), (int(ax2) , int(ay2) ), (255, 255, 255), 2)
            #cv2.imshow("SRC", src_img)
            #cv2.imshow("AI", ai_img)
            return(ai_img)

   def trans_img(self, img1, img2, dur_frms=10):
      if img1 is not None and img2 is not None:
         for i in range(1,dur_frms):
            perc = (i / (dur_frms) )  
            perc2 = 1 - perc
            img1 = cv2.resize(img1, (1920,1080))
            img2 = cv2.resize(img2, (1920,1080))
            blend = cv2.addWeighted(img1, perc, img2, perc2, .3)
            cv2.resizeWindow("pepe", 640, 360)
            cv2.imshow('pepe', blend)
            cv2.waitKey(30) 
         cv2.imshow('pepe', img1)
         cv2.waitKey(30) 

   def gui_options(self):

      if 'skip_non_hd_files' not in self.options: 
         self.options['skip_non_hd_files'] = False
      if 'skip_confirmed_non_meteors' not in self.options: 
         self.options['skip_confirmed_non_meteors'] = True
      if 'skip_confirmed_meteors' not in self.options: 
         self.options['skip_confirmed_meteors'] = False 
      if 'skip_confirmed_fireballs' not in self.options: 
         self.options['skip_confirmed_fireballs'] = False 
      if 'skip_single_station_obs' not in self.options: 
         self.options['skip_single_station_obs'] = True 
      if 'fade_trans_frames' not in self.options: 
         self.options['fade_trans_frames'] = True 
      if 'fade_seconds' not in self.options: 
         self.options['fade_seconds'] = 1
      today = datetime.datetime.now().strftime("%Y_%m_%d")
      if 'date' not in self.options: 
         self.options['date'] = today 
      layout = [
         [sg.Text('OBSERVATION CRITERIA', size =(25, 1))],
         [sg.Text('Date'), sg.InputText(key='date', size=20, default_text=self.options['date']),sg.CalendarButton("Select Date",close_when_date_chosen=True, target="date", format='%Y_%m_%d',size=(10,1))],
         [sg.Text('Include'), sg.InputText(key='days_before', size=5,default_text=self.options['days_before']), sg.Text('days before')],

         [sg.Text("SELECT SLIDESHOW OPTIONS")], 
         [sg.Checkbox(key='skip_non_hd_files',  text='Skip NON-HD Files', default=self.options['skip_non_hd_files'])], 
         [sg.Checkbox(key='skip_confirmed_non_meteors', text='Skip Confirmed Non Meteors', default=self.options['skip_confirmed_non_meteors'])], 
         [sg.Checkbox(key='skip_confirmed_fireballs', text='Skip Confirmed Fireballs', default=self.options['skip_confirmed_fireballs'])], 
         [sg.Checkbox(key='skip_confirmed_meteors', text='Skip Confirmed Meteors', default=self.options['skip_confirmed_meteors'])], 
         [sg.Checkbox(key='skip_single_station_obs', text='Skip Single Station Obs', default=self.options['skip_single_station_obs'])], 

         [sg.Checkbox(key='fade_trans_frames', text='Fade Transition Frames', default=self.options['fade_trans_frames'])], 
         [sg.Text('Fade Seconds'), sg.InputText(key='fade_seconds', size=3, default_text=self.options['fade_seconds'])],

         [sg.Text('ALLSKY7 Network Login', size =(25, 1))],
         [sg.Text('AS7 Username', size =(15, 1)), sg.InputText(key="as7_username", default_text=self.options['as7_username'], size=20)],
         [sg.Text('AS7 Password', size =(15, 1)), sg.InputText(key="as7_password", default_text=self.options['as7_password'], size=20)],


         [sg.Button("OK")]
      ]


      # Create the window
      window = sg.Window("ALLSKY7 SLIDE SHOW OPTIONS", layout)

      # Create an event loop
      while True:
         event, values = window.read()
         # End program if user closes window or
         # presses the OK button
         print(values)
         if event == "OK" or event == sg.WIN_CLOSED:
            self.options['skip_non_hd_files'] = values['skip_non_hd_files'] 
            self.options['skip_confirmed_non_meteors'] = values['skip_confirmed_non_meteors']
            self.options['skip_confirmed_meteors'] = values['skip_confirmed_meteors'] 
            self.options['skip_confirmed_fireballs'] = values['skip_confirmed_fireballs'] 
            self.options['date'] = values['date'] 
            self.options['days_before'] = values['days_before'] 
            self.options['fade_trans_frames'] = values['fade_trans_frames'] 
            self.options['fade_seconds'] = values['fade_seconds'] 
            self.options['as7_username'] = values['as7_username'] 
            self.options['as7_password'] = values['as7_password'] 

            print(self.options)
            save_json_file(self.opt_file, self.options)
            break

      window.close()

   def best_ev_stats(self, data):

      self.MM = MovieMaker()
      self.RF = RenderFrames()
      logo = self.RF.logo_320


      self.load_stations_file()
      rc = 0
      red_yes = 0
      red_yes_hd_meteor_yes = 0
      red_yes_hd_meteor_no = 0
      red_yes_sd_meteor_yes = 0
      red_yes_sd_meteor_no = 0
      red_no = 0
      red_meteors = []
      for row in data:
         obs_id = row['station_id'] + "_" + row['sd_video_file'].replace(".mp4", "")
         rkey = "AIO:" + obs_id
         rval = self.r.get(rkey)

         # set peak int to the new intensity match from the MFD
         # OR BETTER, set it from the MAX INT IN THE hd/sd meteors!
         max_int = max([rrr[6] for rrr in row['meteor_frame_data']])
         if rval is not None:
            red_yes += 1
            rval = json.loads(rval)
            max_int = 0
            max_dur = 0
          
            if rval['hdv'] != None:
               hdv_short = rval['hdv'].split("/")[-1][0:20]
            else:
               hdv_short = None
            if rval['sdv'] != None:
               sdv_short = rval['sdv'].split("/")[-1][0:20]
            else:
               sdv_short = None

            oid_short = obs_id[0:20]
            # check that the HDV and SDV match the OID! BUG FIX!
            if hdv_short is not None:
               if hdv_short != oid_short:
                  print("PROBLEM HDV DOESNT MATCH SDV/OID, BUG!", oid_short, hdv_short )
                  rval['hdv'] = None
                  rval['hdm'] = []
                  self.r.set(rkey, json.dumps(rval))
            if sdv_short is not None:
               if sdv_short != oid_short:
                  rval['sdv'] = None
                  rval['sdm'] = []
                  self.r.set(rkey, json.dumps(rval))
                  print("PROBLEM SDV DOESNT MATCH SDV/OID, BUG!", oid_short, sdv_short )


            if "hdm" in rval:
               if len(rval['hdm']) > 0:
                  red_yes_hd_meteor_yes += 1
               else:
                  red_yes_hd_meteor_no += 1

               for met in rval['hdm']:
                  hd_max_int = max(met['oint'])
                  hd_dur = len(met['oint']) / 25
                  if hd_max_int > max_int:
                     max_int = hd_max_int
                  if hd_dur > max_dur:
                     max_dur = hd_dur
            if "sdm" in rval:
               if len(rval['sdm']) > 0:
                  red_yes_sd_meteor_yes += 1
               else:
                  red_yes_sd_meteor_no += 1
               for met in rval['sdm']:
                  sd_max_int = max(met['oint'])
                  sd_dur = len(met['oint']) / 25
                  if sd_max_int > max_int:
                     max_int = sd_max_int
                  if sd_dur > max_dur:
                     max_dur = sd_dur

            if len(rval['hdm']) > 0 or len(rval['sdm']) > 0:
               red_meteors.append(rval)

            rval['obs_id'] = rkey.replace("AIO:", "")
            rval['peak_int'] = max_int
            rval['max_int'] = max_int
            rval['dur'] = max_dur
            
            self.r.set(rkey, json.dumps(rval))
         else:
            red_no += 1
         if rc % 1000 == 0:
            print("loaded", rc, "obs")

         rc += 1
      print("RED YES/NO", red_yes, red_no)
      print("RED HD METEOR YES/NO", red_yes_hd_meteor_yes, red_yes_hd_meteor_no)
      print("RED SD METEOR YES/NO", red_yes_sd_meteor_yes, red_yes_sd_meteor_no)
      
      # just loop over the best of with HD meteors found! 
      rc = 1
      #red_meteors = sorted(red_meteors, key=lambda x: x['peak_int'], reverse=True)
      red_meteors = sorted(red_meteors, key=lambda x: x['dur'], reverse=True)
      last_img = None
      dupe_pv = {}

      # main display loop
      for row in red_meteors:
         obs_id = row['obs_id'].replace("AIO:", "")
         station_id = obs_id.split("_")[0]
         if station_id in self.photo_credits:
            photo_credit = station_id + " - " + self.photo_credits[station_id]
         else:
            photo_credit = station_id + ""
         dkey = obs_id.split("-")[0]
         if dkey in dupe_pv:
            print("SKIP DUPE:", row)
            continue
         else:
            dupe_pv[dkey] = 1
         
         hdv = row['hdv']
         sdv = row['sdv']
         hdm = row['hdm']
         sdm = row['sdm']
         if "human_label" in row:
            human_label = row['human_label']
         else:
            human_label = ""
         if "non" in human_label:
            print("SKIP NON METEOR:", row)
            continue

         hd_stack_file = None
         sd_stack_file = None
         if hdv is not None:
            hd_stack_file = row['hdv'].replace(".mp4", "-stacked.jpg")
            if os.path.exists(hd_stack_file) is False:
               hd_frames = load_frames_simple(hdv)
               if len(hd_frames) > 0:
                  hd_stack_img = stack_frames(hd_frames)
                  cv2.imwrite(hd_stack_file, hd_stack_img)
         else:
            # continue if no HDM!A
            print("HDV:", hdv)
            #only skip if option says so!
            #continue
         if row['hdv'] is not None and os.path.exists(row['hdv']) is False:
            # continue if no HDV
            #only skip if option says so!
            print("HDV:", row['hdv'])
            #continue

         if sdv is not None:
            sd_stack_file = row['sdv'].replace(".mp4", "-stacked.jpg")
            if os.path.exists(sd_stack_file) is False:
               sd_frames = load_frames_simple(sdv)
               sd_stack_img = stack_frames(sd_frames)
               try:
                  cv2.imwrite(sd_stack_file, sd_stack_img)
               except:
                  print("SD STACK WRITE FAILED", sd_stack_img)
                  #continue

         sf = obs_id.replace(station_id + "_", "")
         sf = sf.split("-")[0]
         options = {}
         options['photo_credits'] = photo_credit
         if hd_stack_file is not None and os.path.exists(hd_stack_file) and len(hdm) > 0:
            hd_stack_img = cv2.imread(hd_stack_file)

            img1 = hd_stack_img
            hd_stack_img = self.RF.watermark_image(hd_stack_img, logo, 1590,940, .5)
            hd_stack_img = cv2.normalize(hd_stack_img, None, 255,0, cv2.NORM_MINMAX, cv2.CV_8UC1)
            cv2.putText(hd_stack_img, str(photo_credit),  (10,1060), cv2.FONT_HERSHEY_SIMPLEX, .6, (255,255,255), 1)
            cv2.putText(hd_stack_img, str(sf),  (1550,1060), cv2.FONT_HERSHEY_SIMPLEX, .6, (255,255,255), 1)
            cv2.putText(hd_stack_img, str(human_label),  (10,20), cv2.FONT_HERSHEY_SIMPLEX, .9, (0,0,255), 1)

            if last_img is not None:
               self.trans_img(hd_stack_img, last_img, dur_frms=25)
            cv2.imshow('pepe', hd_stack_img)
            img = hd_stack_img
            key = cv2.waitKey(2000)
            last_img = hd_stack_img
         elif sd_stack_file is not None and os.path.exists(sd_stack_file):
            sd_stack_img = cv2.imread(sd_stack_file)
            sd_stack_img = cv2.resize(sd_stack_img, (1920,1080))
            #sd_stack_img = self.RF.watermark_image(sd_stack_img, logo, 1590,940, .5)
            if sd_stack_img is None:
               print("NONE FOR SD STACK IMG!", sd_stack_file)
               continue
            cv2.putText(sd_stack_img, str(photo_credit),  (10,1060), cv2.FONT_HERSHEY_SIMPLEX, .6, (255,255,255), 1)
            cv2.putText(sd_stack_img, str(sf),  (1550,1060), cv2.FONT_HERSHEY_SIMPLEX, .6, (255,255,255), 1)
            #cv2.putText(img, str(sd_stack_img),  (10,20), cv2.FONT_HERSHEY_SIMPLEX, .9, (0,0,255), 1)

            if last_img is not None:
               self.trans_img(sd_stack_img, last_img, dur_frms=25)
            cv2.imshow('pepe', sd_stack_img)
            img = sd_stack_img
            key = cv2.waitKey(2000)
            last_img = sd_stack_img
         else:
            print("NOTHING GOOD TO SHOW!")
            print("NOT FOUND HD STACK FILE!", sd_stack_file)
            print("NOT FOUND SD STACK FILE!", sd_stack_file)
            continue

         if key != -1:
            print("KEY", key)
            if key == 102:

               updates = {}
               updates['human_label'] = "fireball"
               rkey = "AIO:" + obs_id
               self.update_red(rkey, updates)

               cv2.putText(img, str("fireball"),  (1000,600), cv2.FONT_HERSHEY_SIMPLEX, .9, (0,0,255), 1)
               cv2.imshow('pepe', img)
               cv2.waitKey(30)
            # KEY X
            if key == 120:

               updates = {}
               updates['human_label'] = "non meteor"
               rkey = "AIO:" + obs_id
               self.update_red(rkey, updates)
               cv2.putText(img, str("meteor"),  (1000,600), cv2.FONT_HERSHEY_SIMPLEX, .9, (0,0,255), 1)

               cv2.putText(img, str("non meteor"),  (1000,600), cv2.FONT_HERSHEY_SIMPLEX, .9, (0,0,255), 1)
               cv2.imshow('pepe', img)
               cv2.waitKey(30)
            # KEY M
            if key == 109:
               updates = {}
               updates['human_label'] = "meteor"
               rkey = "AIO:" + obs_id
               self.update_red(rkey, updates)
               cv2.putText(img, str("meteor"),  (1000,600), cv2.FONT_HERSHEY_SIMPLEX, .9, (0,0,255), 1)
               cv2.imshow('pepe', img)
               cv2.waitKey(30)

            # KEY P play video
            if key == 112:
               self.play_video_file(hdv,sdv,img)
               #cv2.imshow('pepe', img)
               key = cv2.waitKey(30)

            # Space bar pause / menu
            if key == 32:
               show_frame = self.make_menu_overlay(obs_id, img, data)
               cv2.imshow('pepe', show_frame)
               key = cv2.waitKey(0)

         print(rc, obs_id, row['peak_int'])
         rc += 1

   def play_video_file(self, sdv,hdv, stack_img):
      frames = []
      if os.path.exists(hdv) is True:
         frames = load_frames_simple(hdv)
      elif os.path.exists(sdv) is True:
         frames = load_frames_simple(hdv)

      if len(frames) > 0:
         ff = frames[0]
         lf = frames[-1]
         ff = cv2.resize(ff,(1920,1080))
         lf = cv2.resize(ff,(1920,1080))
         self.trans_img(stack_img, ff, dur_frms=10)
      for frame in frames:
         frame = cv2.resize(frame,(1920,1080))
         cv2.imshow('pepe', frame )
         cv2.waitKey(30)

      self.trans_img(lf, stack_img, dur_frms=10)
     

   def update_red(self, rkey, new_data):
      rval = self.r.get(rkey)
      if rval is not None:
         rval = json.loads(rval)
         for k in new_data:
            rval[k] = new_data[k]
         self.r.set(rkey, json.dumps(rval))
      print(rkey)
      print(rval)

   def get_red(self, rkey):
      rval = self.r.get(rkey)
      if rval is not None:
         rval = json.loads(rval)
      return(rval)

   def run_past_days(self):
      network_stats_file = self.dbdir + "network_stats.json"
      if os.path.exists(network_stats_file) is True:
         stats = load_json_file(network_stats_file)
      for day in stats:
         print(day, stats[day] )
         if "events_PENDING" in stats[day]:
            pending =  stats[day]['events_PENDING']
         else:
            pending = 0
         if "total_obs" in stats[day]:
            total_obs =  stats[day]['total_obs']
         else:
            total_obs = 0
         print(day, total_obs, pending)
         if pending > 3:
            cmd = "./AllSkyNetwork.py do_all " + day
            os.system(cmd)


      for i in range(0,365):
         pday = (datetime.datetime.now() - datetime.timedelta(days = i)).strftime("%Y_%m_%d")
         if pday not in stats:
            cmd = "./AllSkyNetwork.py do_all " + pday
            os.system(cmd)
            print("MISSING", pday)
         elif stats[pday]['total_obs'] < 200:
            print("LOW", pday)
            cmd = "./AllSkyNetwork.py do_all " + pday
            os.system(cmd)
         else:
            print("GOOD", pday)

   def db_tally(self):
      # get latest obs & event counts across all days/db files
      network_stats_file = self.dbdir + "network_stats.json"
      if os.path.exists(network_stats_file) is True:
         stats = load_json_file(network_stats_file)
      else:
         stats = {}

      files = os.listdir(self.dbdir)
      stats['totals_by_day'] = []
      stations_by_day = []
      for ff in files:
         if "ALLSKY" not in ff or "CALIBS" in ff:
            continue
         day = ff.replace("ALLSKYNETWORK_", "") 
         day = day.replace(".db", "") 
         db_file = self.db_dir + ff
         con = sqlite3.connect(db_file)
         #con.row_factory = sqlite3.Row
         cur = con.cursor()
         sql = "SELECT count(*) from event_obs"
         cur.execute(sql)
         rows = cur.fetchall()
         stats[day] = {}
         stats[day]['total_obs'] = rows[0][0]

         # events by status
         sql = "SELECT event_status, count(*) from events group by event_status "
         cur.execute(sql)
         rows = cur.fetchall()
         stats[day]['total_events'] = 0
         for row in rows:
            st, cc = row
            ec = "events_" + st 
            stats[day][ec] = cc
            stats[day]['total_events'] += cc 

         # obs count by station id
         sql = "SELECT station_id, count(*) from event_obs group by station_id"
         cur.execute(sql)
         rows = cur.fetchall()
         if "station_obs" not in stats[day]:
            stats[day]['station_obs'] = {}
         for row in rows:
            st, cc = row
            if st not in stats[day]['station_obs']:
               stats[day]['station_obs'][st] = {}
            stats[day]['station_obs'][st]['total_obs'] = cc
         stats[day]['total_stations'] = len(stats[day]['station_obs'].keys())
         stations_by_day.append(len(stats[day]['station_obs'].keys()))

         print(day,  stats[day]['total_stations'],  stats[day]['total_obs'],  stats[day]['total_events'])
         stats['totals_by_day'].append([day, stats[day]['total_stations'],  stats[day]['total_obs'],  stats[day]['total_events']])


      save_json_file(network_stats_file, stats)

   def rerun_station_events(self):
      dur = 365 
      for i in range(0,int(dur)):
         new_date = (datetime.datetime.now() - datetime.timedelta(days = i)).strftime("%Y_%m_%d")
         self.set_dates(new_date, refresh=False)
         y,m,d = new_date.split("_") 
         if os.path.exists(self.station_events_file) is False:
            self.station_events(new_date)
            cmd = "cp " + self.station_events_file + " " +  self.cloud_evdir 
            print(cmd)
            os.system(cmd)
 
   def get_event_status_day(self, date):
      self.db_file = self.db_dir + "/ALLSKYNETWORK_" + date + ".db"
      if os.path.exists(self.db_file) is False:
         print("DB FILE NOT FOUND.", self.db_file)
         return ()
      self.con = sqlite3.connect(self.db_file)
      self.con.row_factory = sqlite3.Row
      self.cur = self.con.cursor()
      sql = """
         SELECT event_status , count(*)
         FROM events
         GROUP BY event_status
      """
      self.cur.execute(sql)
      rows = self.cur.fetchall()
      final_data = []
      for row in rows:
         final_data.append((row[0],row[1]))
      return(final_data)

   def events_by_day_graph(self):
      # Produce all time events by day graph for 
      # plotly.js -- output will be used on a web page

      
      #self.sync_dyna_day(date)


      date_dt = datetime.datetime.now()
      dur = 30
      best_all = []
      best_valid_all = []
      best_ev_all = {}
      ev_by_day = {}
      load_obs = False
      load_valid_obs = False
      load_events = True 
      if True:
         for i in range(0,int(dur)):
            minus = (date_dt - datetime.timedelta(days = i)).strftime("%Y_%m_%d")
            tdate = minus
            y,m,d = minus.split("_") 
            ev_dir = "/mnt/f/EVENTS/{:s}/{:s}/{:s}/".format(y,m,d)
            aof = ev_dir + minus + "_ALL_OBS.json"
            aef = ev_dir + minus + "_ALL_EVENTS.json"
            aev = ev_dir + minus + "_VALID_OBS.json"
            if load_valid_obs is True :
               if os.path.exists(aev) is True:
                  v_data = load_json_file(aev)
                  for st in v_data:
                     for fn in v_data[st]:
                        oid = st + "_" + fn
                        best_valid_all.append(oid)
            if load_events is True :
               if os.path.exists(aef) is True:
                  ev_data = load_json_file(aef)
                  ev_by_day[tdate] = {}
                  ev_by_day[tdate]['total_events'] = len(ev_data)
                  for row in ev_data:
                      status = row['solve_status']
                      if status not in ev_by_day[tdate]:
                         ev_by_day[tdate][status] = 1
                      else:
                         ev_by_day[tdate][status] += 1

                  db_stats = self.get_event_status_day(tdate)
                  t = 0
                  for status, count in db_stats:
                     db_st = "DB_" + status
                     ev_by_day[tdate][db_st] = count 
                     t += count
                  ev_by_day[tdate]['db_total'] = t 
                 



            if load_obs is True :
               if os.path.exists(aof) is True:
                  data = load_json_file(aof)
                  best_all.extend(data)
               else:
                  print("MISSING:", aof)
            #print(tdate, len(best_all), "Total Items")
         #final_data = sorted(best_all, key=lambda x: x['peak_int'], reverse=True)

      for day in ev_by_day:
         print(day, ev_by_day[day])

   def event_obs_ids(self, ev):
       # return obs ids for event
       obs_ids = []
       if "obs_ids" in ev:
          return(ev['obs_ids'])
       else:
          for i in range(0,len(ev['stations'])):
             s = ev['stations'][i]
             f = ev['files'][i]
             o = s + "_" + f.replace(".mp4", "")
             obs_ids.append(o)
       return(obs_ids)

   def check_event_quality(self, a, e, s_alt, e_alt, vel):
      if a < 0 or e >= 1 or s_alt > 160000:
         event_status = "BAD"
      else :
         event_status = "GOOD"
      return(event_status)

   def publish_year(self, year):
      self.load_stations_file()

      import webbrowser
      event_dict_file = "/mnt/f/EVENTS/DBS/" + year + "_EVENT_DICT.json" 

      events = load_json_file(event_dict_file)
      events_qual = {}
      failed_obs = {}
      good_obs = {}
      bad_obs = {}

      events_qual['GOOD'] = 0 
      events_qual['BAD'] = 0 
      events_qual['FAILED'] = 0 
      c = 0
      intensity = []
      for event_id in events:
         ev = events[event_id]
         #print("PEAK:", ev['peak_int'])
         intensity.append((event_id, ev['peak_int']))
         if "orb" in ev:
            a = ev['orb']['a']
            e = ev['orb']['e']
            s_alt = ev['traj']['start_ele']
            e_alt = ev['traj']['end_ele']
            vel = ev['traj']['v_init']
            if a is None:
                quality = "FAILED"
            else: 
                quality = self.check_event_quality(events[event_id]['orb']['a'], events[event_id]['orb']['e'], s_alt, e_alt, vel)
                events_qual[quality] += 1
         else:
            events_qual['FAILED'] += 1
         obs_ids = self.event_obs_ids(ev)
         for oi in obs_ids:
            if quality == "GOOD":
               good_obs[oi] = {}
            elif quality == "BAD":
               bad_obs[oi] = {}
            elif quality == "FAILED":
               failed_obs[oi] = {}

         c += 1

      print(f"Total Events for {year}: {c}") 
      print("Events by quality:") 
      for ee in events_qual:
         print(ee, events_qual[ee])
      print("Observations:") 
      print("GOOD OBS", len(good_obs))
      print("BAD OBS", len(bad_obs))
      print("FAILED OBS", len(failed_obs))
      print("TOTAL OBS", len(good_obs) + len(bad_obs) + len(failed_obs))   

      print("Brightest events")
      intensity = sorted(intensity, key=lambda x: x[1], reverse=True)
      admin_event_review = {}
      for row in intensity[0:100]:
         print(row[0], row[1])
         self.event_day = self.event_id_to_date(row[0])
         self.event_id = row[0]
         self.set_date_db(self.event_day)
         path, win_path = self.goto_event(row[0])
         gallery_img_file = path + row[0] + "_GALLERY.jpg"

         if os.path.exists(gallery_img_file) is False:
            gallery_img = self.make_event_gallery()
         #webbrowser.open(win_path + "index.html") # To open new window

         #gallery_img_file = self.local_evdir + self.event_id + "/" + self.event_id + "_GALLERY.jpg"

   def make_event_gallery(self):
      event_data, obs_data1, map_img, obs_imgs = self.get_event_obs()

   def set_date_db(self, date):
             # DB FILE!
      self.db_file = self.db_dir + "/ALLSKYNETWORK_" + date + ".db"
      if os.path.exists(self.db_file) is False:
         os.system("cat ALLSKYNETWORK.sql | sqlite3 " + self.db_file)
      if os.path.exists(self.db_file) is False:
         print("DB FILE NOT FOUND.", self.db_file)
         return ()
      self.con = sqlite3.connect(self.db_file)
      self.con.row_factory = sqlite3.Row
      self.cur = self.con.cursor()

   def goto_event(self, event_id):
      import webbrowser
      self.event_day = self.event_id_to_date(event_id)
      y,m,d = self.event_day.split("_")
      self.set_dates(self.event_day)
      path = f"/mnt/f/EVENTS/{y}/{m}/{d}/{event_id}/"
      win_path = f"F:/EVENTS/{y}/{m}/{d}/{event_id}/"
      return(path, win_path)

   def year_report(self, year):
      year_dir = "/mnt/f/EVENTS/DBS/" + year + "/"
      events_by_shower = {}
      events_by_station = {}

      if os.path.exists(year_dir) is False:
         os.makedirs(year_dir)
      all_events_file = "/mnt/f/EVENTS/DBS/" + year + "_ALL_EVENTS.json" 
      event_dict_file = "/mnt/f/EVENTS/DBS/" + year + "_EVENT_DICT.json" 
      all_radiants_file = "/mnt/f/EVENTS/DAYS/" + year + "_ALL_RADIANTS.json" 
      shw_radiants_file = "/mnt/f/EVENTS/DAYS/" + year + "_SHW_RADIANTS.json" 
      spo_radiants_file = "/mnt/f/EVENTS/DAYS/" + year + "_SPO_RADIANTS.json" 

      if os.path.exists("/mnt/f/EVENTS/DBS/" + year + "_ALL_BAD_OBS.json") :
         all_bad_obs = load_json_file("/mnt/f/EVENTS/DBS/" + year + "_ALL_BAD_OBS.json" )
      else:
         all_bad_obs = []
      if os.path.exists("/mnt/f/EVENTS/DBS/" + year + "_DEL_OBS.json" ):
         deleted_obs = load_json_file("/mnt/f/EVENTS/DBS/" + year + "_DEL_OBS.json" )
      else:
         deleted_obs = []
      if os.path.exists(all_events_file) is True:
         all_events = load_json_file(all_events_file)
      else:
         all_events = {}

      if os.path.exists(event_dict_file) is True:
         event_dict = load_json_file("/mnt/f/EVENTS/DBS/" + year + "_EVENT_DICT.json" )
      else:
         event_dict = {}

      all_radiants = []
      spo_radiants = []
      shw_radiants = []



      status_rpt = {}
      pending = []
      shc = 0
      for event in all_events:
         event_dict[event['event_id']] = event
         if "solve_status" not in event:
            event['solve_status'] = "PENDING"
         status = event['solve_status']


         if "INVALID PLANES" in status :
            status = "FAILED"
         if "UNSOLVED" in status :
            status = "PENDING"
         if "SUCCESS" in status :
            status = "SOLVED"
         if "WMPL FAIL" in status :
            status = "FAILED"
         if status not in status_rpt:
            status_rpt[status] = 1
         else:
            status_rpt[status] += 1
         if status == "PENDING":
            pending.append(event['event_id'])
         if status == "SOLVED":
            if "shower" in event:
               if event['shower']['shower_code'] != "...":
                  shower = event['shower']['shower_code'] 
                  shc += 1
                  if shower not in events_by_shower:
                     events_by_shower[shower] = 1
                  else:
                     events_by_shower[shower] += 1
               else:
                  shower = "SPORADIC"
            else:
               shower = "SPORADIC"
            if "rad" in event:
               event['rad']['event_id'] = event['event_id']
               event['rad']['IAU'] = shower
               all_radiants.append(event['rad'])
               if shower != "SPORADIC":
                  shw_radiants.append(event['rad'])
               else:
                  spo_radiants.append(event['rad'])

      totals_by_shower = []

      print(f"{year} TOTAL EVENTS: {len(all_events)}")
      for sh in events_by_shower:
         totals_by_shower.append((sh, events_by_shower[sh]))

      totals_by_shower = sorted(totals_by_shower, key=lambda x: x[1], reverse=True)
      for row in totals_by_shower:
         print(row[0], row[1])

      save_json_file(all_radiants_file, all_radiants, True)
      save_json_file(spo_radiants_file, spo_radiants, True)
      save_json_file(shw_radiants_file, shw_radiants, True)
      print(all_radiants_file)
      print(spo_radiants_file)
      print(shw_radiants_file)

      for st in status_rpt:
         print(st, status_rpt[st])

      # rerun events
      for event_id in pending:
         cmd = "./AllSkyNetwork.py resolve_event " + event_id
         #print(cmd)
         #os.system(cmd)
         event_day = self.event_id_to_date(event_id)
         y,m,d = event_day.split("_")
         edir = "/mnt/f/EVENTS/" + y + "/" + m + "/" + d + "/" + event_id + "/" 
         efile = edir + event_id + "-event.json"
         ffile = edir + event_id + "-fail.json"
         if os.path.exists(efile) is True:
            status_rpt['SOLVED'] += 1
            status_rpt['PENDING'] -= 1
            event_dict[event_id]['solve_status'] = "SOLVED" 
         elif os.path.exists(ffile) is True:
            status_rpt['FAILED'] += 1
            status_rpt['PENDING'] -= 1
            event_dict[event_id]['solve_status'] = "FAILED" 
         #else:
         #   print("PENDING?", efile )
      for st in status_rpt:
         print(st, status_rpt[st])
      new_all_events = []
      for event_id in event_dict:
         new_all_events.append(event_dict[event_id])

      save_json_file(event_dict_file, event_dict, True)
      save_json_file(all_events_file , new_all_events, True)
      print(all_events_file)
      print(event_dict_file)

   def purge_event(self,event_id):
      event_day = self.event_id_to_date(event_id)
      y,m,d = event_day.split("_")
      date = y + "_" + m + "_" + d
      edir = "/mnt/f/EVENTS/" + y + "/" + m + "/" + d + "/" + event_id + "/"
      if os.path.exists(edir) is True:
         cmd = "rm -rf " + edir
         print(cmd)
         os.system(cmd)
      # delete from dynamo

      # delete from local sql
      sql = "DELETE FROM EVENTS WHERE event_id = ?"
      print(sql)
      self.cur.execute(sql, [event_id])
      self.con.commit()

      # delete from dynamo db
      delete_event(self.dynamodb, date, event_id)




   def delete_bad_detects(self,bad_detects_file):
      # too aggresive deleting real meteors on peak shower dates
      # and some other times. Whitelist the persieds and geminds peaks +/- 1 days
      print("EARLY EXIT!")
      exit()
      bad_detects = load_json_file(bad_detects_file)
      del_detects_file = bad_detects_file.replace("ALL_BAD", "DEL")
      del_detects = load_json_file(del_detects_file)
      for oid in bad_detects:
         if oid not in del_detects:
            del_detects[oid] = {}
      for oid in del_detects:
         st = oid.split("_")[0]
         vid  = oid.replace(st + "_", "")
         delete_obs(self.dynamodb, st, vid, 0, "NF")

      

   def all_year_events(self, year):
      # get all of the year's events into 1 table/data file
      date = year + "_12_31"
      date_dt = datetime.datetime.strptime(date, "%Y_%m_%d")
      deleted_obs = {}
      all_events = []
      all_bad_obs = []

      for i in range(0,365):
         ndate = (date_dt - datetime.timedelta(days = i)).strftime("%Y_%m_%d")
         y,m,d = ndate.split("_")
         evdir = "/mnt/f/EVENTS/" + y + "/" + m + "/" + d + "/" 
         obs_file = evdir + ndate + "_ALL_OBS.json"
         obs_file_gz = obs_file + ".gz"
         obs_dict_file = evdir + ndate + "_OBS_DICT.json"

         bad_detects_file = evdir + ndate + "_BAD_DETECTS.json"

         ev_file = evdir + ndate + "_ALL_EVENTS.json"
         ev_file_gz = ev_file + ".gz"

         # if date of obs_dict is older than obs then remake it.
         osz, otd = get_file_info(obs_file)
         osz, dtd = get_file_info(obs_dict_file)
         if dtd > otd:
            self.set_dates(date)
         if os.path.exists(obs_file):
            oby = True
         else:
            oby = False 
            if os.path.exists(obs_file_gz):
               oby = "gz"
               os.system("gunzip " + obs_file_gz)


         if os.path.exists(bad_detects_file):
            obdy = True
            bad_detects = load_json_file(bad_detects_file)
         else:
            bad_detects = {}
            obdy = False 

         if os.path.exists(obs_dict_file):
            obdy = True
         else:
            obdy = False 

         if os.path.exists(ev_file):
            evy = True
         else:
            evy = False 
            if os.path.exists(ev_file_gz):
               evy = "gz"
               os.system("gunzip " + ev_file_gz)

         print(ndate, evdir, oby, obdy, evy)
         if obdy is True:
            obs_dict = load_json_file(obs_dict_file)
         else:
            print("NO OBS DICT!")
            obs_dict = {}

         for oid in bad_detects:
            print("BD:", oid)
            oid = oid + ".mp4"
            all_bad_obs.append(oid)
            if oid in obs_dict:
               del(obs_dict[oid])
               print("BAD DETECT IN OBS DICT", oid)

         if evy is True:
            ev_data = load_json_file(ev_file)
            for row in ev_data:
               if "peak_int" in row:
                  peak_status = True 
                  if row['peak_int'] == 0:
                     peak_status = False
               else:
                  peak_status = False
               if "dur" in row:
                  dur_status = True 
                  if row['dur'] == 0:
                     dur_status = False
               else:
                  dur_status = False
               event_id = row['event_id']
               if peak_status is False or dur_status is False:
                  # Update peak status and dur_status for event
                  pks = []
                  durs = []
                  new_row = row.copy()
                  if "solution" in new_row:
                     del(new_row['solution'])
                  if "lats" in new_row:
                     del(new_row['lats'])
                  if "lons" in new_row:
                     del(new_row['lons'])
                  if "alts" in new_row:
                     del(new_row['alts'])
                  if "plot" in new_row:
                     del(new_row['plot'])
                  if "sol_dir" in new_row:
                     del(new_row['sol_dir'])
                  new_row['stations'] = []
                  new_row['files'] = []
                  new_row['start_datetime'] = []

                  if "stations" not in row:
                     row['stations'] = []

                  for i in range(0, len(row['stations'])):
                     st = row['stations'][i]
                     fl = row['files'][i]
                     tm = row['start_datetime'][i] 
                     if type(tm) == list:
                        if len(tm) > 0:
                           tm = tm[0]
                        else:
                           tm = ""
                     oid = st + "_" + fl
                     if oid in obs_dict:
                        new_row['stations'].append(st)
                        new_row['files'].append(fl)
                        new_row['start_datetime'].append(tm)
                        if "meteor_frame_data" in obs_dict[oid]:
                           ints = [row[6] for row in obs_dict[oid]['meteor_frame_data']]
                           if len(ints) > 0:
                              max_int = max(ints)
                              dur = len(ints) / 25
                           else:
                              max_int = 0
                              dur = 0
                           pks.append(max_int)
                           durs.append(dur)
                        else:
                           print("   ", oid, "NO MFD")
                     else:
                        print("   DICT MISSING OBS DELETED ?", oid)
                        # these obs ids no longer exist and should be removed from the event
                        # this may in turn invalidate the event
                        # so need to think about this...
                        deleted_obs[oid] = {}
                        deleted_obs[oid]['event_id'] = event_id
                         
                        #self.make_obs_dict(self)
                        #obs_dict = self.obs_dict
                  # 
                  if len(pks) > 0:
                     peak_int = max(pks)
                  else:
                     peak_int = 0
                  if len(durs) > 0:
                     dur = round(np.median(durs),3)
                  else:
                     dur = 0
                  #print("   ", event_id, peak_int, dur)
                  new_row['peak_int'] = peak_int
                  new_row['dur'] = dur
                  all_events.append(new_row)

      # save the all events file 
      # save the deleted obs
      # save the peak/duration info 
      save_json_file("/mnt/f/EVENTS/DBS/" + year + "_ALL_BAD_OBS.json", all_bad_obs, True)
      save_json_file("/mnt/f/EVENTS/DBS/" + year + "_DEL_OBS.json", deleted_obs, True)
      save_json_file("/mnt/f/EVENTS/DBS/" + year + "_ALL_EVENTS.json", all_events, True)

   def best_of(self, date, dur=30):

      self.MM = MovieMaker()
      self.RF = RenderFrames()
      self.logo = self.RF.logo_320
      #self.rerun_station_events()
      self.opt_file = "/mnt/f/EVENTS/DBS/view_options.json"
      self.img_cache_dir = "/mnt/f/AI/DATASETS/IMAGE_CACHE/"
      self.learning_dir = "/mnt/f/AI/DATASETS/NETWORK_PREV/MULTI_CLASS_V2/"


      if os.path.exists(self.opt_file):
         self.options = load_json_file(self.opt_file)
      else:
         self.options = {}
      # cache files
      self.load_stations_file()
      self.gui_options()
      date = self.options['date']
      dur = self.options['days_before']
      best_of_dir = "/mnt/f/EVENTS/BEST_OF/"
      all_best_file = best_of_dir + date + "_" + dur + "_BEST_OF_ALL.json"
      all_best_valid_file = best_of_dir + date + "_" + dur + "_BEST_VALID.json"

      all_ev_best_file = best_of_dir + date + "_" + dur + "_BEST_OF_ALL_EV.json"
      mc_best_file = best_of_dir + date + "_" + dur + "_BEST_OF_MULTI.json"
      ev_obs_file = best_of_dir + date + "_" + dur + "_BEST_EV_OBS.json"
      #ev_best_file = best_of_dir + date + "_" + dur + "_BEST_OF_EV.json"
      if os.path.exists(best_of_dir) is False:
         os.makedirs(best_of_dir)
      
      options = {}
      # skip items where the hc count > 2
      options['skip_hc'] = 9999 
      options['skip_non'] = True 
      options['skip_non_hc'] = 1
      options['play_video'] = True 

      cv2.namedWindow('pepe')
      cv2.resizeWindow("pepe", self.win_x, self.win_y)
      last_met_img = None
      admin_deleted_file = "/mnt/f/EVENTS/DBS/admin_deleted.json"
      self.net_ai_file = "/mnt/f/EVENTS/DBS/network_ai.json"
      if os.path.exists(admin_deleted_file):
         admin_del = load_json_file(admin_deleted_file)
      else:
         admin_del = {}
      if os.path.exists(self.net_ai_file):
         self.net_ai = load_json_file(self.net_ai_file)
      else:
         self.net_ai = {}

      

      if os.path.exists(all_best_file) and os.path.exists(all_ev_best_file) and os.path.exists(mc_best_file):
         update_needed = False 
      else:
         update_needed = True


      # merge network obs/event data for the last x days starting on date
      print("BEST OF LAST " + str(dur) + " DAYS SINCE " + date)
      date_dt = datetime.datetime.strptime(date, "%Y_%m_%d")


      # if the update has not run in a while refresh it
      if update_needed is False:
         #final_data = load_json_file(all_best_file)
         final_data = []
         ev_obs = load_json_file(ev_obs_file)

         self.best_ev_all = load_json_file(all_ev_best_file)
         mc_best = load_json_file(mc_best_file)
         best_valid_all = load_json_file(all_best_valid_file)

      else:
         best_all = []
         self.best_ev_all = {}
         best_valid_all = []
         for i in range(0,int(dur)):
            minus = (date_dt - datetime.timedelta(days = i)).strftime("%Y_%m_%d")
            tdate = minus
            y,m,d = minus.split("_") 
            ev_dir = "/mnt/f/EVENTS/{:s}/{:s}/{:s}/".format(y,m,d)
            aof = ev_dir + minus + "_ALL_OBS.json"
            aef = ev_dir + minus + "_ALL_EVENTS.json"
            aev = ev_dir + minus + "_VALID_OBS.json"
            if os.path.exists(aev) is True:
               v_data = load_json_file(aev)
               for st in v_data:
                  for fn in v_data[st]:
                     oid = st + "_" + fn
                     best_valid_all.append(oid)
            if os.path.exists(aef) is True:
               ev_data = load_json_file(aef)
               for row in ev_data:
                  event_id = row['event_id']
                  self.best_ev_all[event_id] = row 
            if os.path.exists(aof) is True:
               data = load_json_file(aof)
               best_all.extend(data)
            else:
               print("MISSING:", aof)
            print(minus, len(best_all), "Total Items")
         final_data = sorted(best_all, key=lambda x: x['peak_int'], reverse=True)
         save_json_file(all_best_file, final_data)
         save_json_file(all_best_valid_file, best_valid_all)
         i = 0
         go = True

         best = []
         mc_best = []
         for data in final_data: 
            if "prev.jpg" in  data['sync_status']:
               best.append(data)


         ev_obs = {}
         for event_id in self.best_ev_all:
            ev = self.best_ev_all[event_id]
            for i in range(0,len(ev['stations'])):
               obs_id = ev['stations'][i] + "_" + ev['files'][i]
               tdate = ev['files'][i][0:10]
               short_obs_id = self.convert_short_obs(tdate, obs_id)
               short_ev = ev['event_id'].split("_")[1]


               ev_obs[short_obs_id] = short_ev

         save_json_file(ev_obs_file, ev_obs)
         #save_json_file(ev_best_file, ev_obs, True)
         save_json_file(all_ev_best_file, self.best_ev_all, True)
         #print(len(ev_obs.keys()), "MULTI STATION OBS")
         print("BEST:", len(best))
         for data in best:
            obs_key = data['station_id'] + "_" + data['sd_video_file'] 
            if "peak_int" not in data:
               data['peak_int'] = 0

            short_obs_id = self.convert_short_obs(tdate, obs_key)

            if short_obs_id not in ev_obs:
               print("SKIP NOT MS", short_obs_id)
               continue
            else:
               mc_best.append(data)

         mc_best = sorted(mc_best, key=lambda x: x['peak_int'], reverse=True)

         save_json_file(mc_best_file, mc_best)
         print("Saved new best file:", mc_best_file)

      print("MULT STATION BEST LIST IS BUILT!")
      print(dur, "DAYS LEADING UP TO", date)
      print("MC BEST (MULTI + PREV) :", len(mc_best), "TOTAL OBS")
      print("ALL EV OBS (MULTI-STATION OBS) :", len(ev_obs), "TOTAL OBS")

      # View the good ones with best_ev_stats
      # or continue to run the AI on the prev and download the HD if fireball
      # continue also to human confirm
      print("ALL BEST VALID:", all_best_valid_file, len(best_valid_all))

      #self.db_tally()


      #self.best_ev_stats(mc_best)
      print("END OK", len(mc_best))

      print("BIG LOOP")
      i = 0

      #mc_best = sorted(mc_best, key=lambda x: x['dur'], reverse=True)
      mc_best = sorted(mc_best, key=lambda x: x['sd_video_file'], reverse=True)

      # loop over all of the 'best' meteors that match the options critera

      for data in mc_best:
         # each row of data contains an observation
         # the row might exist in redis already
         # if some redis vars are set then it can be skipped 
         # it might have AI detect data already (for its main obj)
         # the media files (SD & HD vids & stack pics) 'might' not exist locally yet, 
         #    media files could exist in 2 places remotely (host machine or cloud drive) 
         #    if we grab a media file from a remote host that is not already in the cloud 
         #    drive we should put it there to save the host having to reconcile use double bandwidth  . 
         # the row might have level 2 detection arrays (for SD and HD vids)

         # setup level 2 detection vars and base values
         hd_meteors = []
         sd_meteors = []
         hd_vid = None
         sd_vid = None
         hd_stack_img = None
         sd_stack_img = None

         #set obs key
         station_id = data['station_id'] 

         obs_key = data['station_id'] + "_" + data['sd_video_file'] 
         obs_id = obs_key
         tdate = data['sd_video_file'][0:10]
         short_obs_id = self.convert_short_obs(tdate, obs_key)

         # set redis key and check if the obs is already there
         rkey = "AIO:" + obs_key.replace(".mp4", "")
         rval = self.r.get(rkey) 
         if rval is None:
            rval = {}
         else:
            rval = json.loads(rval)
         if "human_label" in rval:
            human_label = rval
         else:
            human_label = "No human label yet" 
         # skip this row if certain options for skipping are met
         if self.options['skip_confirmed_non_meteors'] is True:
            if "human_label" in rval :
               if rval['human_label'] == "non":
                  print("SKIP NON!")
                  continue
            if obs_key in self.net_ai:
               if "human_label" in self.net_ai[obs_key]:
                  if self.net_ai[obs_key]['human_label'] == "non":
                     continue
         if self.options['skip_confirmed_meteors'] is True:
            if "human_label" in rval:
               if rval['human_label'] == "meteor" :
                  print("SKIP NON!")
                  continue
            if obs_key in self.net_ai:
               if "human_label" in self.net_ai[obs_key]:
                  if self.net_ai[obs_key]['human_label'] == "meteor":
                     continue
         if self.options['skip_confirmed_fireballs'] is True:
            if "human_label" in rval:
               if rval['human_label'] == "fireball" :
                  print("SKIP NON!")
                  continue
            if obs_key in self.net_ai:
               if "human_label" in self.net_ai[obs_key]:
                  if self.net_ai[obs_key]['human_label'] == "fireball":
                     rval['human_label'] = "fireball"
                     continue
         
         # skip if not a multi-station event
         if short_obs_id not in ev_obs:
            print("SKIP NOT MS",short_obs_id )
            continue
         else:
            # setup the event info 
            event_id = tdate.replace("_", "") + "_" + ev_obs[short_obs_id]
            event_data = self.best_ev_all[event_id]
            
         # check if this obs is already in the network_ai file
         # if it is then some work has already been done
         if obs_key in self.net_ai:
            ai_resp = self.net_ai[obs_key]
            test = []
            test.append(("meteor", int(ai_resp['meteor_yn'])))
            test.append(("fireball", int(ai_resp['fireball_yn']))) 
            test.append(( ai_resp['mc_class'], int(ai_resp['mc_class_conf'])))
            test = sorted(test, key=lambda x: x[1], reverse=True)
            ai_label = test[0][0]
            ai_conf = test[0][1]

            # Skip AI non meteors -- this should match with the options?
            # NEED MORE CODE HERE TO SUPPORT THE OPTIONS BETTER
            # WHAT AM I SKIPPING AND WHY 
            if "meteor" not in ai_label and "fireball" not in ai_label:
               continue

         # there is no point in working on obs that have zero media! 
         # we need at least a "prev.jpg" for this process to be worth while.
         # if no obs media has been sync'd we might as well continue
         if "prev.jpg" in  data['sync_status']:
             # setup the local cache variables to hold the various media types and resolutions
             # we will have stack pictures and videos at 180, 360 and 1080p

             # setup cloud dirs and files
             thumb_dir = "/mnt/archive.allsky.tv/" + data['station_id'] + "/METEORS/" + data['sd_video_file'][0:4] + "/" + data['sd_video_file'][0:10] + "/"
             thumb_file = thumb_dir + data['station_id'] + "_" + data['sd_video_file'].replace(".mp4", "-prev.jpg")
             local_thumb_dir = self.img_cache_dir + data['station_id'] + "/METEORS/" + data['sd_video_file'][0:4] + "/" + data['sd_video_file'][0:10] + "/"

             # if local dir doesn't exist make it
             if os.path.exists(local_thumb_dir) is False:
                os.makedirs(local_thumb_dir)

             # setup local files
             local_thumb_file = local_thumb_dir + data['station_id'] + "_" + data['sd_video_file'].replace(".mp4", "-prev.jpg")
             local_thumb_1080p_file = local_thumb_dir + data['station_id'] + "_" + data['sd_video_file'].replace(".mp4", "-1080p-stacked.jpg")
             local_thumb_360p_file = local_thumb_dir + data['station_id'] + "_" + data['sd_video_file'].replace(".mp4", "-360p-stacked.jpg")

             # if the file exists locally use that as the default
             if os.path.exists(local_thumb_file):
                thumb_file = local_thumb_file

             # use the higher resolution stack exists locally 
             # use that instead
             if os.path.exists(local_thumb_1080p_file) is True:
                prev_img = cv2.imread(local_thumb_1080p_file)
                res = "1080p"
             elif os.path.exists(local_thumb_360p_file) is True:
                prev_img = cv2.imread(local_thumb_360p_file)
                res = "360p"
             elif os.path.exists(local_thumb_file) is True:
                prev_img = cv2.imread(local_thumb_file)
                res = "180p"
             else:
                prev_img = cv2.imread(thumb_file)
                res = "180p"

             # if we started with a cloud prev image we should save the local verion!
             # otherwise higher res stacks will be made on the video loop
             if res == "180p" and os.path.exists(local_thumb_file) is False:
                print(prev_img, local_thumb_file)
                if prev_img is not None:
                   cv2.imwrite(local_thumb_file, prev_img)

             # if the prev img is not none (meaning we have at least the 180p picture)
             if prev_img is not None:
                # resize to 1080p 
                img = cv2.resize(prev_img,(1920,1080))
                x1,y1,x2,y2 = mfd_roi(data['meteor_frame_data'] )

                # check if the obs is already in the Network AI DB
                if obs_key in self.net_ai:
                   ai_resp = self.net_ai[obs_key]
                else:
                   # get the AI response for the MFD ROI
                   ai_img = self.make_ai_img(img, x1,y1,x2,y2)
                   ai_resp = self.check_ai_img(ai_img, None)

                   # for an AI meteor if this is a multi-station?
                   #if short_obs_id not in ev_obs:
                   #   ai_resp['meteor_yn'] = 99
                   #   ai_resp['multi_class'] = "meteor" 
                   #   ai_resp['multi_class_conf'] = 98

                   self.net_ai[obs_key] = ai_resp 

                   # save the AI img in a learning dir for future training
                   ai_dir = self.learning_dir + ai_resp['mc_class'] + "/"
                   if os.path.exists(ai_dir) is False:
                      os.makedirs(ai_dir)
                   ai_file = ai_dir + obs_key.replace(".mp4", "-ai.jpg")
                   if os.path.exists(ai_file) is False:
                      cv2.imwrite(ai_file, ai_img)

                # we should have AI response for the existing MFD ROI  

                # format the AI text on the image
                ai_text = str(int(ai_resp['meteor_yn'])) + "% Meteor " + str(int(ai_resp['fireball_yn'])) + "% fireball " + str(int(ai_resp['mc_class_conf'])) + "% " + ai_resp['mc_class']

                cv2.putText(img, str(ai_text),  (x1,y1-5), cv2.FONT_HERSHEY_SIMPLEX, .6, (255,255,255), 1)
                cv2.rectangle(img, (int(x1), int(y1 )), (int(x2) , int(y2) ), (255, 255, 255), 2)
                meteor_fn = thumb_file.split("/")[-1].replace("-prev.jpg", "")

                # ADD PHOTO CREDITS TO THE SHOW IMG
                if station_id in self.photo_credits:
                   photo_credit = station_id + " - " + self.photo_credits[station_id]
                else:
                   photo_credit = station_id + ""

                # WATERMARK THE SHOW IMG
                cv2.putText(img, str(photo_credit + " " + event_id),  (10,1060), cv2.FONT_HERSHEY_SIMPLEX, .6, (255,255,255), 1)
                cv2.putText(img, str(obs_id),  (1550,1060), cv2.FONT_HERSHEY_SIMPLEX, .6, (255,255,255), 1)
                cv2.putText(img, str(human_label),  (10,20), cv2.FONT_HERSHEY_SIMPLEX, .9, (0,0,255), 1)

                img = self.RF.watermark_image(img, self.logo, 1590,940, .5)
                img = cv2.normalize(img, None, 255,0, cv2.NORM_MINMAX, cv2.CV_8UC1)
                #cv2.putText(img, str(meteor_fn),  (300,20), cv2.FONT_HERSHEY_SIMPLEX, .6, (255,255,255), 1)

                metcon = False 
                if "human_label" in ai_resp:
                   desc = ai_resp['human_label'] 
                   if "human_confirmed" in ai_resp:
                      desc += " " + str(ai_resp['human_confirmed'] )
                      human_confirmed = ai_resp['human_confirmed'] 
                      if "meteor" not in desc and "fireball" not in desc and ai_resp['human_confirmed'] >= options['skip_non_hc'] :
                         print("SKIP: NON-METEOR HUMAN CONFIRMED >= ", options['skip_non_hc'])
                         continue
                      if human_confirmed >= options['skip_hc'] :
                         print("SKIP: REVIEW MODE ON AND HUMAN CONFIRMED >= ", options['skip_hc'])
                         continue

                   if "meteor" in ai_resp['human_label'] or "fireball" in ai_resp['human_label']:
                      cv2.putText(img, str(desc),  (x1,y2), cv2.FONT_HERSHEY_SIMPLEX, .9, (0,255,0), 1)
                      cv2.rectangle(img, (int(x1), int(y1 )), (int(x2) , int(y2) ), (0, 255, 0), 2)
                      metcon = True 

                   else:
                      cv2.putText(img, str(desc),  (x1,y2), cv2.FONT_HERSHEY_SIMPLEX, .9, (0,0,255), 1)
                      cv2.rectangle(img, (int(x1), int(y1 )), (int(x2) , int(y2) ), (0, 0, 255), 2)
                else:
                      cv2.putText(img, "NO HUMAN CONFIRM",  (x1,y2), cv2.FONT_HERSHEY_SIMPLEX, .9, (0,255,255), 1)

                # trans last to new img
                if last_met_img is not None and img is not None:
                   for i in range(0,10):
                      perc = i / 10
                      perc2 = 1 - perc
                      print(img.shape)
                      last_met_img = cv2.resize(last_met_img, (1920,1080))
                      blend = cv2.addWeighted(img, perc, last_met_img, perc2, .3)
                      cv2.resizeWindow("pepe", 1920, 1080)
                      cv2.imshow('pepe', blend)


                # EVENT PREVIEW
                ev_preview = self.make_event_preview(event_data)
                frame_canvas = np.zeros((1080,1920,3),dtype=np.uint8)
                frame_canvas[1080-ev_preview.shape[0]:1080,0:ev_preview.shape[1]] = ev_preview


 
                y1 = 1080 - ev_preview.shape[0]
                y2 = 1080 
                x1 = 0 
                x2 = ev_preview.shape[1] 
                #img[y1:y2,x1:x2] = ev_preview

                img_fr_ev = cv2.resize(img,(1600,900))
                img_canvas = frame_canvas.copy()
                img_canvas[0:900,0:1600] = img_fr_ev
                #img = img_canvas

                #show_frame = self.make_menu_overlay(obs_id, img, data)
                #cv2.imshow('pepe', img)
                cv2.imshow('pepe', img_canvas)
                if "human_confirmed" not in self.net_ai[obs_key] and "human_confirmed" not in rval:
                   key = cv2.waitKey(3000) 
                else:
                   key = cv2.waitKey(1000) 
                data['ai_resp'] = ai_resp
                play = True 
                if key != -1:
                   self.handle_keypress(key, img_canvas, rkey, rval)


                play = True

                # if the meteor is confirmed and the options
                if metcon is True and options['play_video'] is True and play is True:
                   if hd_stack_img is not None:
                      stack_img = hd_stack_img
                   elif sd_stack_img is not None:
                      stack_img = sd_stack_img
                   else:
                      stack_img = prev_img
                   
                   ximg,blend,obj_img,hd_vid, sd_vid,hd_meteors,sd_meteors = self.play_preview_video(obs_id, stack_img, data,frame_canvas)

                   ximg = cv2.resize(ximg,(1600,900))
                   img_canvas[0:900,0:1600] = ximg 

                   show_frame = img_canvas.copy()
                   show_frame = cv2.resize(show_frame,(1920,1080))

                   hdm = []
                   # biggest first
                   hd_meteors = sorted(hd_meteors, key=lambda x: max(x['ows']) + max(x['ohs']), reverse=True)
                   if len(hd_meteors) > 0:
                      fx1,fy1,fx2,fy2 = hd_meteors[0]['roi']
                   # check / merge HD meteors as needed
                   sc = 0
                   for met in hd_meteors:
                      x1,y1,x2,y2 = met['roi']
                      x1,y1,x2,y2 = int(x1),int(y1),int(x2),int(y2)
                      if sc > 0 and (fx1 <= x1 <= fx2 and fy1 <= y1 <= fy2 and fx1 <= x2 <= fx2 and fy1 <= y2 <= fy2):
                         continue
                      ai_img = self.make_ai_img(img, x1,y1,x2,y2)
                      ai_resp = self.check_ai_img(ai_img, None)
                      met['ai_resp'] = ai_resp
                      ai_opt = [ ["meteor", ai_resp['meteor_yn']], ["meteor", ai_resp['meteor_prev_yn']], ["fireball", ai_resp['fireball_yn']], [ai_resp['mc_class'], ai_resp['mc_class_conf']]]
                      ai_opt = sorted(ai_opt, key=lambda x: x[1], reverse=True)
                      ai_desc = ai_opt[0][0] + " " + str(round(ai_opt[0][1],1)) + "%"
                      met['ai_opt'] = ai_opt

                      if "meteor" in ai_opt[0][0] or "fireball" in ai_opt[0][0] or ai_resp['meteor_yn'] > 50 or ai_resp['fireball_yn'] > 50:
                         ai_no_meteor = True 
                         cv2.rectangle(show_frame, (int(x1), int(y1)), (int(x2) , int(y2) ), (255, 0, 0), 2)
                         print(show_frame.shape)
                         print(ai_desc)
                         print(x1,y2)
                         cv2.putText(show_frame, ai_desc,  (x1,y2), cv2.FONT_HERSHEY_SIMPLEX, .9, (255,0,0), 2)
                         print("HD METEOR")
                         hdm.append(met)
                      else:
                         ai_no_meteor = False 
                         cv2.rectangle(show_frame, (int(x1), int(y1)), (int(x2) , int(y2) ), (0, 0, 200), 2)
                         cv2.putText(show_frame, ai_desc,  (x1,y2), cv2.FONT_HERSHEY_SIMPLEX, .9, (0,0,255), 2)
                         print("HD NON METEOR")


                      sc += 1
                   if len(hdm) > 0:
                      hd_meteors = hdm

                   sdm = []
                   sd_meteors = sorted(sd_meteors, key=lambda x: max(x['ows']) + max(x['ohs']), reverse=True)
                   if len(sd_meteors) > 0:
                      fx1,fy1,fx2,fy2 = sd_meteors[0]['roi']
                   sc = 0
                   for met in sd_meteors:
                      x1,y1,x2,y2 = met['roi']
                      x1,y1,x2,y2 = int(x1),int(y1),int(x2),int(y2)
                      if sc > 0 and (fx1 <= x1 <= fx2 and fy1 <= y1 <= fy2 and fx1 <= x2 <= fx2 and fy1 <= y2 <= fy2):
                         continue
                      
                      ai_img = self.make_ai_img(img, x1,y1,x2,y2)
                      ai_resp = self.check_ai_img(ai_img, None)
                      cv2.rectangle(show_frame, (int(x1), int(y1)), (int(x2) , int(y2) ), (255, 255, 0), 2)
                      met['ai_resp'] = ai_resp
                      ai_opt = [ ["meteor", ai_resp['meteor_yn']], ["meteor", ai_resp['meteor_prev_yn']], ["fireball", ai_resp['fireball_yn']], [ai_resp['mc_class'], ai_resp['mc_class_conf']]]
                      ai_opt = sorted(ai_opt, key=lambda x: x[1], reverse=True)
                      ai_desc = ai_opt[0][0] + " " + str(round(ai_opt[0][1],1)) + "%"
                      met['ai_opt'] = ai_opt
                      if "meteor" in ai_opt[0][0] or "fireball" in ai_opt[0][0] or ai_resp['meteor_yn'] > 50 or ai_resp['fireball_yn'] > 50:
                         ai_no_meteor = True 
                         print(show_frame.shape)
                         print(ai_desc)
                         print(x1,y2)
                         cv2.putText(show_frame, ai_desc,  (x1,y2), cv2.FONT_HERSHEY_SIMPLEX, .9, (255,255,0), 2)
                         cv2.rectangle(show_frame, (int(x1), int(y1)), (int(x2) , int(y2) ), (255, 255, 0), 2)
                         print("SD METEOR", x1,y1,x2,y2)
                         sdm.append(met)
                      else:
                         ai_no_meteor = False 
                         cv2.rectangle(show_frame, (int(x1), int(y1)), (int(x2) , int(y2) ), (0, 0, 255), 2)
                         cv2.putText(show_frame, ai_desc,  (x1,y2), cv2.FONT_HERSHEY_SIMPLEX, .9, (0,0,255), 2)
                         print("SD NON METEOR")
                      sc += 1
                   if len(sdm) > 0:
                      sd_meteors = sdm
                   
                   cv2.imshow('pepe', img_canvas)
                   key = cv2.waitKey(1000) 
                last_met_img = img

                red_key = "AIO:" + obs_id.replace(".mp4", "")
                rval['hdm'] = hd_meteors
                rval['sdm'] = sd_meteors
                rval['hdv'] = hd_vid 
                rval['sdv'] = sd_vid 

                if key == 120:
                   rval['human_label'] = "non" 
                else: 
                   img,blend,obj_img,hd_vid, sd_vid,hd_meteors,sd_meteors = self.play_preview_video(obs_id, img, data,frame_canvas)
                   img = cv2.resize(img,(1600,900))
                   img_canvas[0:900,0:1600] = img 



                   try:
                      cv2.imshow('pepe', img_canvas)
                   except:
                      print("FAILED TO SHOW STACK!", sd_vid)
                   key = cv2.waitKey(300)


                self.r.set(red_key, json.dumps(rval))

                if "meteor" not in ai_resp['mc_class'] and  ai_resp['mc_class_conf'] > 80 or ((ai_resp['meteor_yn'] < 50 or ai_resp['meteor_prev_yn'] < 50) and ai_resp['fireball_yn'] < 50):
                   ai_no_meteor = True
                else: 
                   ai_no_meteor = False 

                if "human_label" in ai_resp:
                   key = cv2.waitKey(300)
                else:
                   key = cv2.waitKey(1000)
                self.handle_keypress(key, img, rkey, rval)

             i = i + 1

   def make_event_preview(self,event_data):
      print("EVENT PREVIEW :", event_data.keys())
      # determine canvas size (320 x 180 is ideal)
      total_prevs = len(event_data['stations'])
      if total_prevs <= 6:
         pw = 320
         ph = 180
         br = 6 - 1
      elif 6 < total_prevs <= 8:
         pw = 240 
         ph = 135 
         br = 8 - 1
      elif 8 < total_prevs <= 10:
         pw = 192 
         ph = 108
         br = 10 - 1
      else:
         pw = 192 
         ph = 108
         br = 10 - 1

      can_w = total_prevs * pw
      if can_w >= 1920:
         can_w = 1920


      canvas = np.zeros((180,1920,3),dtype=np.uint8)
        
      rc = 0
      rr = 0
      temp = []
      for i in range(0,len(event_data['stations'])):
         st = event_data['stations'][i]
         fl = event_data['files'][i]
         prev = self.load_preview_image(st, fl)
         temp.append((st,fl,prev))
      i = 0
      temp = sorted(temp, key=lambda x: x[1], reverse=True)
      for row in temp:
         st,fl,prev = row
         cx1 = (i * 320)
         cx2 = (i * 320) + 320
         cy1 = 0 
         cy2 = 180
         if cx1 >= 1920 or cx2 >= 1920: 
            break
         if prev is None:
            prev = np.zeros((180,320,3),dtype=np.uint8)
         if i >= br:
            break
         canvas[cy1:cy2,cx1:cx2] = prev
         i += 1
      return(canvas)

   def load_preview_image(self, station_id, video_file):

      cloud_dir = "/mnt/archive.allsky.tv/" + station_id + "/METEORS/" + video_file[0:4] + "/" + video_file[0:10] + "/"
      cloud_file = cloud_dir + station_id + "_" + video_file.replace(".mp4", "-prev.jpg")
      cloud_file_360p = cloud_dir + station_id + "_" + video_file.replace(".mp4", "-360p-stacked.jpg")
      cloud_file_1080p = cloud_dir + station_id + "_" + video_file.replace(".mp4", "-1080p-stacked.jpg")

      local_dir = self.img_cache_dir + station_id + "/METEORS/" + video_file[0:4] + "/" + video_file[0:10] + "/"
      local_file = local_dir + station_id + "_" + video_file.replace(".mp4", "-prev.jpg")
      if os.path.exists(local_dir) is False:
         os.makedirs(local_dir)

      if os.path.exists(local_file) is True:
         # if it is local read the image 
         img = cv2.imread(local_file)
         print(local_file, img.shape)
         return(img)
      elif os.path.exists(cloud_file) is True:
         # if it is in the cloud read it from there 
         # then save a local copy for next time
         img = cv2.imread(cloud_file)
         cv2.imwrite(local_file, img)
         return(img)

      else:
         return(None)



   def handle_keypress(self, key, img, rkey, rval ):

      if key == -1:
         return()

      human_label = ""
      print("KEY:", key)
      # KEY ESC - EXIT 
      if key == 27:
         exit()

      # KEY F - FIREBALL 
      if key == 102:
         human_label = "fireball" 
         rval['human_label'] = "fireball"
         if "human_confirmed" in rval:
            if rval['human_label'] == "fireball":
               rval['human_confirmed'] += 1
            else:
               rval['human_confirmed'] = 1
         else:
            rval['human_confirmed'] = 1

      # KEY X
      if key == 120:
         human_label = "non" 
         rval['human_label'] = "non"
         if "human_confirmed" in rval:
            if rval['human_label'] == "non":
               rval['human_confirmed'] += 1
            else:
               rval['human_confirmed'] = 1
         else:
            rval['human_confirmed'] = 1

      # KEY M
      if key == 109:
         human_label = "meteor" 
         rval['human_label'] = "meteor"
         if "human_confirmed" in rval:
            if rval['human_label'] == "non":
               rval['human_confirmed'] += 1
            else:
               rval['human_confirmed'] = 1
         else:
            rval['human_confirmed'] = 1

      cv2.putText(img, human_label,  (1000,600), cv2.FONT_HERSHEY_SIMPLEX, .9, (0,0,255), 1)
      self.r.set(rkey, json.dumps(rval))
      cv2.imshow('pepe', img)
      cv2.waitKey(30)
      play = False

      save_json_file(self.net_ai_file, self.net_ai)

   def convert_short_obs(self, date, obs_id): 
      #if obs id has AMS then make it short, else expand it. 
      #obs_id = ev['stations'][i] + "_" + ev['files'][i]
      print(obs_id)
      aid = obs_id.split("_")[0]
      short_obs_id = obs_id.replace(".mp4", "")
      short_obs_id = short_obs_id.replace("AMS", "")
      short_obs_id = short_obs_id.replace("trim", "t")
      short_obs_id = short_obs_id.replace("2022_", "")
      short_obs_id = short_obs_id.replace("_000_", "c")
      st = short_obs_id.split("_")[0]
      short_obs_id = short_obs_id.replace(st + "_", "")
      short_obs_id = short_obs_id.replace("_", "")
      short_obs_id = st + "_" + short_obs_id.replace("-", "")

      print(short_obs_id)
      return(short_obs_id)

   def make_menu_overlay(self, obs_id, stack_img, data):
      cv2.putText(stack_img, "MENU OPTIONS",  (int((1920/2)-300),200), cv2.FONT_HERSHEY_SIMPLEX, 2, (0,0,255), 1)
      cv2.putText(stack_img, "Press a key to label or interact with the observation" ,  (int((1920/2)-300),250), cv2.FONT_HERSHEY_SIMPLEX, .9, (0,0,255), 1)
      cv2.putText(stack_img, "(F)ireball" ,  (int((1920/2)-300),300), cv2.FONT_HERSHEY_SIMPLEX, .9, (0,0,255), 1)
      cv2.putText(stack_img, "(M)eteor" ,  (int((1920/2)-300),350), cv2.FONT_HERSHEY_SIMPLEX, .9, (0,0,255), 1)
      cv2.putText(stack_img, "(X) Non-meteor" ,  (int((1920/2)-300),400), cv2.FONT_HERSHEY_SIMPLEX, .9, (0,0,255), 1)
      cv2.putText(stack_img, "(N)orthern Lights" ,  (int((1920/2)-300),450), cv2.FONT_HERSHEY_SIMPLEX, .9, (0,0,255), 1)
      cv2.putText(stack_img, "(A)ir plane" ,  (int((1920/2)-300),500), cv2.FONT_HERSHEY_SIMPLEX, .9, (0,0,255), 1)
      cv2.putText(stack_img, "(B)ird" ,  (int((1920/2)-300),550), cv2.FONT_HERSHEY_SIMPLEX, .9, (0,0,255), 1)
      cv2.putText(stack_img, "(P)lay Video" ,  (int((1920/2)-300),600), cv2.FONT_HERSHEY_SIMPLEX, .9, (0,0,255), 1)
      cv2.putText(stack_img, "(D)uplicate Obs" ,  (int((1920/2)-300),650), cv2.FONT_HERSHEY_SIMPLEX, .9, (0,0,255), 1)
      cv2.putText(stack_img, "(E)dit Obs" ,  (int((1920/2)-300),700), cv2.FONT_HERSHEY_SIMPLEX, .9, (0,0,255), 1)
      cv2.putText(stack_img, "Space = Pause/Continue" ,  (int((1920/2)-300),750), cv2.FONT_HERSHEY_SIMPLEX, .9, (0,0,255), 1)
      #cv2.putText(stack_img, "OBS ID:" + obs_id,  (int((1920/2)-400),400), cv2.FONT_HERSHEY_SIMPLEX, 2, (0,0,255), 1)
      
      return(stack_img)

   def play_preview_video(self, obs_id, stack_img, data, frame_canvas=None):

      station = obs_id.split("_")[0]
      station_id = station
      fn = obs_id.replace(station + "_", "")
      human_label = ""
      human_confirmed = 0
      if "ai_resp" in data:
         if "human_confirmed" in data['ai_resp']:
            human_confirmed = data['ai_resp']['human_confirmed']
            human_label += " (" + str(human_confirmed) + ")"
         
      date = fn[0:10]
      thumb_dir = "/mnt/archive.allsky.tv/" + data['station_id'] + "/METEORS/" + data['sd_video_file'][0:4] + "/" + data['sd_video_file'][0:10] + "/"
      thumb_file = thumb_dir + data['station_id'] + "_" + data['sd_video_file'].replace(".mp4", "-180p.mp4")
      thumb_360p_file = thumb_dir + data['station_id'] + "_" + data['sd_video_file'].replace(".mp4", "-360p.mp4")
      thumb_1080p_file = thumb_dir + data['station_id'] + "_" + data['sd_video_file'].replace(".mp4", "-1080p.mp4")
      local_thumb_dir = self.img_cache_dir + data['station_id'] + "/METEORS/" + data['sd_video_file'][0:4] + "/" + data['sd_video_file'][0:10] + "/"
      if os.path.exists(local_thumb_dir) is False:
         os.makedirs(local_thumb_dir)
      local_thumb_file = local_thumb_dir + data['station_id'] + "_" + data['sd_video_file'].replace(".mp4", "-180p.mp4")
      local_thumb_360p_file = local_thumb_dir + data['station_id'] + "_" + data['sd_video_file'].replace(".mp4", "-360p.mp4")
      local_thumb_1080p_file = local_thumb_dir + data['station_id'] + "_" + data['sd_video_file'].replace(".mp4", "-1080p.mp4")
 
      vid_file = None
      print(thumb_file)
      print(thumb_360p_file)
      print(thumb_1080p_file)
      print(local_thumb_file)
      print(local_thumb_360p_file)
      print(local_thumb_1080p_file)
      # check local file first
      if os.path.exists(local_thumb_file):
         thumb_file = local_thumb_file
      hd = False 
      sd = False 
      # Try to grab the 1080p file first, if it doesn't exist already
      if os.path.exists(local_thumb_1080p_file) is False:
         print("NOT FOUND : local 1080p.mp4")
         if os.path.exists(thumb_1080p_file) is True:
            print("NOT FOUND : cloud 1080p.mp4")
            cmd = "cp " + thumb_1080p_file + " " + local_thumb_1080p_file
            print(cmd)
            os.system(cmd)
         else:
            # try to grab it from host
            if True: #skip_remote == 0:
               if station in self.rurls:
                  hd_vid = self.rurls[station] + "/meteors/" + date +  "/" + data['hd_video_file'] 
                  #sd_vid = self.rurls[station] + "/meteors/" + date +  "/" + data['sd_video_file'] 
                  if os.path.exists(local_thumb_1080p_file) is False:
                     cmd = "wget --timeout=1 --waitretry=0 --tries=1 --no-check-certificate  " + hd_vid + " -O " + local_thumb_1080p_file
                     print(cmd)
                     os.system(cmd)
                  hd_origin = hd_vid

               else:
                  hd_vid = station + "/meteors/" + date +  "/" + data['hd_video_file'] 
                  hd_origin = hd_vid
                  #sd_vid = station + "/meteors/" + date +  "/" + data['sd_video_file'] 
               print("HD:", hd)

      # define origin urls
      if station in self.rurls:
         sd_origin = self.rurls[station] + "/meteors/" + date +  "/" + data['sd_video_file'] 
         hd_origin= self.rurls[station] + "/meteors/" + date +  "/" + data['hd_video_file'] 
      else:
         sd_origin = "asos://" + station + "/meteors/" + date +  "/" + data['sd_video_file'] 
         hd_origin= "asos://" + station + "/meteors/" + date +  "/" + data['hd_video_file'] 

      # Try to grab the 360p file next 
      if os.path.exists(local_thumb_360p_file) is False:
         print("NOT FOUND : local 360p.mp4")
         if os.path.exists(thumb_360p_file) is True:
            print("NOT FOUND : cloud 360p.mp4")
            cmd = "cp " + thumb_360p_file + " " + local_thumb_360p_file
            print(cmd)
            os.system(cmd)
         elif os.path.exists(local_thumb_360p_file) is False:
            if station in self.rurls:
               sd_vid = self.rurls[station] + "/meteors/" + date +  "/" + data['sd_video_file'] 
               cmd = "wget --timeout=1 --waitretry=0 --tries=1 --no-check-certificate " + sd_vid + " -O " + local_thumb_360p_file
               print(cmd)
               os.system(cmd)
               sd_origin = sd_vid
            else:
               sd_vid = station + "/meteors/" + date +  "/" + data['sd_video_file'] 
               sd_origin = sd_vid
            print("SD:", sd)

      if os.path.exists(local_thumb_1080p_file) is True:
         vid_file = local_thumb_1080p_file
         hd = True
         hd_vid = local_thumb_1080p_file
      else:
         hd_vid = None
      if os.path.exists(local_thumb_360p_file) is True:
         vid_file = local_thumb_360p_file
         sd = True
         sd_vid = local_thumb_360p_file
      else:
         sd_vid = None

      # get the 180p as worst case scenario
      if os.path.exists(local_thumb_file) is True:
         vid_file = local_thumb_file 
      elif os.path.exists(local_thumb_file) is False:
         if os.path.exists(thumb_file) is True:
            print("NOT FOUND : cloud 180p.mp4")
            cmd = "cp " + thumb_file + " " + local_thumb_file
            print(cmd)
            os.system(cmd)
         if os.path.exists(local_thumb_file) is True:
            vid_file = local_thumb_file 

      print("VID FILE IS:", vid_file)
      print("STACK FILE IS:", vid_file.replace(".mp4", "-stacked.jpg"))

      # somewhere here we need to reduce and confirm the object is inside the HD!
      

      # TRACK HD AND SD METEORS
      # CHECK REDIS IF THIS IS ALREADY DONE?

      if vid_file is not None and os.path.exists(vid_file) is True:

         if hd == True:
            hd_frames = load_frames_simple(hd_vid)
            if len(hd_frames) > 0:
               hd_objs,hd_meteors,hd_obj_frame = self.track_objs(hd_frames, stack_img)
            else:
               print("ERR no hd frames:" + hd_vid)
               hd_frames = []
               hd_objs = {}
               hd_obj_frame = None
               hd_meteors = []
         else:
            hd_objs = {}
            hd_obj_frame = None
            hd_meteors = []
         if sd == True:
            sd_frames = load_frames_simple(sd_vid)
            if len(sd_frames) > 0:
               sd_objs,sd_meteors,sd_obj_frame = self.track_objs(sd_frames, stack_img)
            else:
               print("ERR no sd frames:" + sd_vid)
               sd_frames = []
               sd_objs = {}
               sd_obj_frame = None
               sd_meteors = []

         else:
            sd_objs = {}
            sd_obj_frame = None
            sd_meteors = []

         print("SD VID:", sd_vid, sd_origin)
         print("HD VID:", hd_vid, hd_origin)
         print("SD OBJS:", len(sd_objs))
         print("HD OBJS:", len(hd_objs))
         print("SD METEORS :", len(sd_meteors))
         print("HD HD METEORS:", len(hd_meteors))

         # if meteors exist in hd or sd frames use those frames instead of the 180p frames
         if len(hd_meteors) > 0:
            vid_file = hd_vid
         elif len(sd_meteors) > 0:
            vid_file = sd_vid

         frames = load_frames_simple(vid_file)

         if "360" in vid_file :
            hstack_file = vid_file.replace(".mp4", "-sd-stacked.jpg")
            if os.path.exists(hstack_file):
               simg = cv2.imread(hstack_file)
            else:
               sd_stack_img = stack_frames(frames)
               stack_img = sd_stack_img
               try:
                  cv2.imwrite(hstack_file, simg)
                  sd_stack_img = cv2.resize(simg, (1920,1080))
               except:
                  print("FAIL", hstack_file)

         if "1080" in vid_file:
            hstack_file = vid_file.replace(".mp4", "-hd-stacked.jpg")
            if os.path.exists(hstack_file):
               simg = cv2.imread(hstack_file)
            else:
               hd_stack_img = stack_frames(frames)
               stack_img = hd_stack_img
               try:
                  cv2.imwrite(hstack_file, simg)
                  hd_stack_img = cv2.resize(simg, (1920,1080))
               except:
                  print("FAIL", hstack_file)

         fc = 0
         fn = 0

         if station_id in self.photo_credits:
            photo_credit = station_id + " - " + self.photo_credits[station_id]
         else:
            photo_credit = station_id + ""

         for fr in frames:
            vfn = vid_file.split("/")[-1]
            fr = cv2.resize(fr, (1920,1080))
            stack_img = cv2.resize(stack_img, (1920,1080))
            if fc < 10:
               perc = (10 - fc) / 10
               perc2 = 1 - perc
               blend = cv2.addWeighted(stack_img, perc, fr, perc2, .3)
               fr = blend
            if fc >= len(frames) - 10:
               perc = (10 - fn) / 10
               perc2 = 1 - perc
               blend = cv2.addWeighted(fr, perc, stack_img, perc2, .3)
               fr = blend

               fn += 1
            cv2.putText(fr, "VIDEO : " + vfn,  (900,20), cv2.FONT_HERSHEY_SIMPLEX, .6, (0,0,255), 1)

            # WATERMARK THE FRAME!
            #fr = self.RF.watermark_image(fr, self.logo, 1590,940, .5)
            #fr = cv2.normalize(fr, None, 255,0, cv2.NORM_MINMAX, cv2.CV_8UC1)
            cv2.putText(fr, str(photo_credit),  (10,1060), cv2.FONT_HERSHEY_SIMPLEX, .6, (255,255,255), 1)
            cv2.putText(fr, str(obs_id),  (1450,1060), cv2.FONT_HERSHEY_SIMPLEX, .6, (255,255,255), 1)
            cv2.putText(fr, str(human_label),  (10,20), cv2.FONT_HERSHEY_SIMPLEX, .9, (0,0,255), 1)
            
            if frame_canvas is not None:
               fr = cv2.resize(fr,(1600,900))
               frm = frame_canvas.copy()
               frm[0:900,0:1600] = fr
            else:
               frm = fr
            cv2.imshow("pepe", frm)
            cv2.waitKey(30)
            fc += 1
      else:
         cv2.putText(stack_img, "NO VIDEO FOR : " + obs_id,  (20,20), cv2.FONT_HERSHEY_SIMPLEX, .9, (0,0,255), 1)
         cv2.imshow("pepe", stack_img)
         cv2.waitKey(30)


      blend = None
      obj_img = None

      return(stack_img,blend,obj_img,hd_vid,sd_vid,hd_meteors,sd_meteors)

   def track_objs(self, frames, stack_img, debug=False):
      stack_img = cv2.resize(stack_img, (1920,1080))
      meteors = []
      first = frames[0]
      fc = 0
      objects = {}
      last_max = 0
      mdfs = []
      for frame in frames:
         if fc == 0 or fc % 7 == 0:
            mdfs.append(frame)

      med_frame = cv2.convertScaleAbs(np.median(np.array(mdfs), axis=0))
      bwf =  cv2.cvtColor(med_frame, cv2.COLOR_BGR2GRAY)
      mask_img = self.auto_mask(med_frame)
      mask_bw =  cv2.cvtColor(mask_img, cv2.COLOR_BGR2GRAY)
      mask_bw =  cv2.resize(mask_bw, (frames[0].shape[1], frames[0].shape[0]))
      for frame in frames:
         o_frame = cv2.resize(frame, (1920,1080))
         bw =  cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
         bw = cv2.subtract(bw, mask_bw)
         sub = cv2.subtract(bw, bwf)
         min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(sub)
         avg_val = np.mean(sub)
         thresh_val = int(max_val * .8)
         if last_max > 0 and thresh_val < last_max * .5:
            thresh_val = last_max * .5
         if thresh_val < avg_val * 2:
            thresh_val = avg_val * 2 
         _, thresh_img = cv2.threshold(sub, thresh_val, 255, cv2.THRESH_BINARY)

         thresh_img = cv2.dilate(thresh_img, None, iterations=4)
         if max_val > last_max:
            last_max = max_val

         thresh_img = cv2.resize(thresh_img, (1920,1080))

         sub = cv2.resize(sub, (1920,1080))
         show_frame = thresh_img.copy()
         cnts = get_contours_in_image(thresh_img)
         cnt_num = 1
         for x,y,w,h in cnts:
            cx = x + (w/2)
            cy = y + (h/2)
            if w > h:
               radius = w
            else:
               radius = h 
            if len(show_frame.shape) == 2:
               show_frame = cv2.cvtColor(show_frame, cv2.COLOR_GRAY2BGR)
            cv2.rectangle(show_frame, (int(x), int(y)), (int(x+w) , int(y+h) ), (255, 255, 255), 2)
            meteor_flux = do_photo(sub, (cx,cy), radius+1)
            cv2.circle(show_frame, (int(cx),int(cy)), int(5), (0,255,255),2)
            obj_id, objects = find_object(objects, fc,cx, cy, w, h, meteor_flux, hd=1, sd_multi=0, cnt_img=None,obj_tdist=90)

            for obj_id in objects:
               ox = int(objects[obj_id]['oxs'][-1])
               oy = int(objects[obj_id]['oys'][-1])
               cv2.putText(show_frame, str(obj_id),  (ox,oy), cv2.FONT_HERSHEY_SIMPLEX, .6, (0,0,255), 1)
            #print(fc, cnt_num, obj_id, x,y,w,h,meteor_flux)
            cnt_num += 1
         if debug is True: 
            cv2.imshow('pepe', show_frame)
            cv2.waitKey(30)
         fc += 1

      # sum each obj
      show_frame = np.zeros((1080,1920,3),dtype=np.uint8)
      for obj_id in objects:
         print()
         print("OBJECT:", obj_id)
         print("FIELDS:", objects[obj_id].keys())
         print("FCS:", objects[obj_id]['ofns'])
         print("OXS:", objects[obj_id]['oxs'])
         print("OYS:", objects[obj_id]['oys'])
         print("OINTS:", objects[obj_id]['oint'])
         if np.mean(objects[obj_id]['oxs']) < 3:
            continue
         objects[obj_id] = analyze_object(objects[obj_id], hd=1,strict=1)

         ox = int(np.mean(objects[obj_id]['oxs']))
         oy = int(np.mean(objects[obj_id]['oys']))
         obj_class = objects[obj_id]['report']['class']
         #for key in  objects[obj_id]['report']:
         #   val = objects[obj_id]['report'][key]
         #   print(key,val)
         cv2.putText(show_frame, str(obj_id),  (ox,oy), cv2.FONT_HERSHEY_SIMPLEX, .6, (0,0,255), 1)
         cv2.putText(show_frame, str(obj_class),  (ox+15,oy), cv2.FONT_HERSHEY_SIMPLEX, .6, (0,0,255), 1)
         for i in range(0,len(objects[obj_id]['oxs'])):
            ox = int(objects[obj_id]['oxs'][i])
            oy = int(objects[obj_id]['oys'][i])
            if debug is True: 
               cv2.circle(show_frame, (int(ox),int(oy)), int(5), (0,255,0),2)
               cv2.imshow('pepe', show_frame)
               cv2.waitKey(30)
         if obj_class == "meteor":
            meteors.append(objects[obj_id])
         min_x = min(objects[obj_id]['oxs'])
         max_x = max(objects[obj_id]['oxs'])
         min_y = min(objects[obj_id]['oys'])
         max_y = max(objects[obj_id]['oys'])
         mean_x = np.mean(objects[obj_id]['oxs'])
         mean_y = np.mean(objects[obj_id]['oys'])
         rw = max_x - min_x
         rh = max_y - min_y
         if rw > rh:
            rh = rw
         else :
            rw = rh
         print("RW/RH", rw,rh)
         x1 = int(min_x - 10)
         x2 = int(max_x + 10)
         y1 = int(min_y - 10)
         y2 = int(max_y + 10)
         if x1 < 0:
            x1 = 0
            x2 = rw
         if y1 < 0:
            y1 = 0
            y2 = rh
         if x2 >= 1919:
            x1 = 1919 - rw
            x2 = 1919
         if y1 >= 1079:
            y1 = 1079 - rh 
            y2 = 1079
         rw = x2 - x1 
         rh = y2 - y1
         if rw > rh:
            rh = rw
         else :
            rw = rh
         rx1 = int(((x1 + x2) / 2) - (rw/2))
         ry1 = int(((y1 + y2) / 2) - (rh/2))
         rx2 = int(((x1 + x2) / 2) + (rw/2))
         ry2 = int(((y1 + y2) / 2) + (rh/2))
         if rx1 < 0:
            rx1 = 0
            rx2 = rw
         if ry1 < 0:
            ry1 = 0
            ry2 = rh
         if rx2 >= 1919:
            rx1 = 1919 - rw
            rx2 = 1919
         if ry1 >= 1079:
            ry1 = 1079 - rh 
            ry2 = 1079



         objects[obj_id]['true_roi'] = [x1,y1,x2,y2]
         objects[obj_id]['roi'] = [rx1,ry1,rx2,ry2]


         cv2.rectangle(show_frame, (int(rx1), int(ry1)), (int(rx2) , int(ry2) ), (0, 255, 0), 4)
         #cv2.putText(show_frame, ai_resp['mc_class'],  (rx1,ry1), cv2.FONT_HERSHEY_SIMPLEX, .6, (0,0,255), 1)
         if obj_class == "meteor":
            print("MET", rw, rh, objects[obj_id]['roi'])
            cv2.rectangle(show_frame, (int(x1), int(y1)), (int(x2) , int(y2) ), (0, 255, 0), 2)
            cv2.rectangle(show_frame, (int(rx1), int(ry1)), (int(rx2) , int(ry2) ), (0, 255, 0), 2)
         else:
            cv2.rectangle(show_frame, (int(x1), int(y1)), (int(x2) , int(y2) ), (0, 0, 255), 2)
            cv2.rectangle(show_frame, (int(rx1), int(ry1)), (int(rx2) , int(ry2) ), (0, 0, 255), 2)
            print("NON", rw, rh, objects[obj_id]['roi'])

      return(objects, meteors, show_frame)

   def plane_test_day(self, date):
      # for each event this day
      # check planes for each unique combo of obs

      self.set_dates(date)
      self.load_stations_file()
      qc_report = {}
      valid_obs = {}
      all_obs = {}

      # select events for this day
      sql = """
         SELECT event_id, event_status, stations, event_start_times, obs_ids 
           FROM events
          WHERE event_id like ?
      """
      orig_date = date
      date = date.replace("_", "")
      ivals = [date + "%"]
      self.cur.execute(sql,ivals)
      rows = self.cur.fetchall()
      final_data = []

      # for each event on this day
      for row in rows:
         event_id, event_status, stations, start_times, obs_ids = row
         stations = json.loads(stations)
         start_times = json.loads(start_times)
         obs_ids = json.loads(obs_ids)
         ev_dir = self.local_evdir + event_id + "/"
         if os.path.exists(ev_dir) is False:
            os.makedirs(ev_dir)
         plane_file = ev_dir + event_id + "_PLANES.json"

         # if the plane report has not been created yet
         # go ahead and make it

         if os.path.exists(plane_file) is False:
            plane_report = self.plane_test_event(obs_ids, event_id, event_status)
            save_json_file(plane_file, plane_report, True)
         else:
            plane_report = load_json_file(plane_file)

         # summarize and report on all planes
         for ekey in plane_report['results']:
            sanity,res = plane_report['results'][ekey] 
            tempkey = ekey.replace(event_id + "_", "")
            ob1, ob2 = tempkey.split("__")
            all_obs[ob1] = 0
            all_obs[ob2] = 0
            if sanity == 0:
               valid_obs[ob1] = 1
               valid_obs[ob2] = 1
               all_obs[ob1] = 1
               all_obs[ob2] = 1
         good_planes,total_planes = self.check_planes(plane_report['results'])
         print(event_id, event_status, str(good_planes) + " / " + str(total_planes) + " good planes")

         # determine the final status
         # update event status here?! At least put results in the event file
         

         # if WMPL STATUS IS BAD AND THERE ARE NO GOOD PLANES 
         # IT IS AN INVALID EVENT
         if "BAD" in event_status and good_planes == 0:
            event_status += ":INVALID"
         final_data.append((event_id, event_status, good_planes, total_planes))
      final_data = sorted(final_data, key=lambda x: x[1])
      print("Event solving status and plane status report")

      # just print out the results
      for row in final_data:
         (event_id, event_status, good_planes, total_planes) = row
         try:
            print(event_id, event_status, good_planes, total_planes, round((good_planes/total_planes)*100,1), "%")
         except:
            print("ERR:", good_planes,  total_planes)
      qc_report['final_data'] = final_data

      # make station stats
      st_stats = {}
      for ob in all_obs:
         st = ob.split("_")[0]
         if st not in st_stats:
            st_stats[st] = {}
            st_stats[st]['GOOD'] = 0 
            st_stats[st]['BAD'] = 0 
         if ob in valid_obs:
            st_stats[st]['GOOD'] += 1
            all_obs[ob] = 1
         else:
            st_stats[st]['BAD'] += 1
            all_obs[ob] = 0

      # print out station stats
      for st in st_stats:
         good = st_stats[st]['GOOD']
         bad = st_stats[st]['BAD']
         total = good + bad

      # save QC report
      qc_report['st_stats'] = st_stats
      qc_report['valid_obs'] = all_obs
      save_json_file(self.local_evdir + orig_date + "_QC.json", qc_report, True)
      print(self.local_evdir + orig_date + "_QC.json")


      # SAVE FAILED OBS REPORT 
      failed_obs_html = ""
      for obs_id in sorted(all_obs):
         if all_obs[obs_id] == 0:
            failed_obs_html += self.meteor_cell_html(obs_id, None)
      fpo = open(self.local_evdir + orig_date + "_FAILED_OBS.html", "w")
      fpo.write(failed_obs_html)
      fpo.close()

   def check_planes(self, planes):
      good = 0
      total = 0
      for ekey in planes:
         row = planes[ekey]
         x,y = row
         if x == 0:
            good += 1
         total += 1
      return(good, total)

   def update_meteor_days(self, selected_day=None):
      if selected_day is None:
         selected_day =  datetime.datetime.now().strftime("%Y_%m_%d")
      nav = self.make_day_nav(selected_day)
      fpout = open("/mnt/ams2/network_meteor_days.html", "w")
      fpout.write(nav)
      fpout.close()
      cmd = "cp /mnt/ams2/network_meteor_days.html /mnt/archive.allsky.tv/APPS/network_meteor_days.html"
      print(cmd)
      os.system(cmd)

   def make_day_nav(self, selected_day=None):

      files = os.listdir("/mnt/f/EVENTS/DBS/")

      date_selector = """
            <script>
$(document).ready(function () {
  $("#select-opt").change(function() {
    var base_url = "F:/"
    var $option = $(this).find(':selected');
    var url = $option.val();
    if (url != "") {
      //url += "?text=" + encodeURIComponent($option.text());
      // Show URL rather than redirect
      //$("#output").text(url);
      window.location.href = base_url + url;
    }
  });
});
            </script>
            <form>
            <select id="select-opt" class="selected_date" data-style="btn-primary">
      """
      for day in sorted(files, reverse=True):
         if "ALL" in day or "EVENT" in day or "SPO" in day or "SHW" in day or "DEL" in day:
            continue
         if day[:2] != "20":
            continue
         el = day.split("_")
         if len(el) != 3:
            continue

         day = day.replace("ALLSKYNETWORK_", "")
         day = day.replace(".db", "") 
         if "journal" in day or "CALIBS" in day:
            continue
         y,m,d = day.split("_")
         url = "/EVENTS/" + y + "/" + m + "/" + d + "/" + day + "_OBS_GOOD.html"

         if day == selected_day:
            
            date_selector += "<option selected value=" + url + ">" + day + "</option>"
         else:
            date_selector += "<option value=" + url + ">" + day + "</option>"

      date_selector += """
            </select>
            </form>


      """
      return(date_selector)


   def make_page_header(self, date=None):
      self.set_dates(date)
      self.local_evdir = self.local_event_dir + self.year + "/" + self.month + "/" + self.day  + "/"
      if os.path.exists(self.local_evdir + "shower_links_file.json"):
         showers = load_json_file(self.local_evdir + "shower_links_file.json")
      else:
         showers = []
      # shower links 1
      shower_links = "<p>"
      for shower in showers:
         print(shower)
         shower_links += """
         <a href={:s}.html>{:s}</a> {:s} -
         """.format(shower[0], shower[0], str(shower[1]))
      shower_links += "</p>" 

      #day_nav = self.make_day_nav(selected_day=date)
      img_err_handler = """
      <script>
             $('div').on("error", function() { // Detect if there is an image loading error
                alert("YO")
                $(this).attr('display',None);
                //$(this).attr('src', 'default.jpg'); // Set a default image path that will replace image error icon
             });
      </script>
      """


      day_nav = img_err_handler + """
                <input id='select-opt' value="{}" type="text" data-display-format="YYYY/MM/DD" data-action="reload" data-url-param="start_day" data-send-format="YYYY_MM_DD" class="datepicker form-control">
      """.format(date)
      event_date = date
      print("Publish Day", date)
      self.load_stations_file()
      self.set_dates(date)
      self.date = date
      self.help()

      qc_report = self.local_evdir + date + "_QC.json"
      if os.path.exists(qc_report):
         qc_data = load_json_file(qc_report)
      else:
         qc_data = {}

      if "valid_obs" in qc_data:
         all_obs = qc_data['valid_obs']
      else:
         all_obs = []

      self.get_all_obs(date)

      template = ""
      tt = open("./FlaskTemplates/allsky-template-v2.html")
      for line in tt:
         template += line

      template = template.replace("{TITLE}", "ALLSKY7 EVENTS " + event_date)
      template = template.replace("AllSkyCams.com", "AllSky.com")
      self.local_evdir = self.local_event_dir + self.year + "/" + self.month + "/" + self.day  + "/"
      out_file_good = self.local_evdir + date + "_OBS_GOOD.html"
      out_file_bad = self.local_evdir + date + "_OBS_BAD.html"
      out_file_failed = self.local_evdir + date + "_OBS_FAIL.html"
      out_file_pending = self.local_evdir + date + "_OBS_PENDING.html"

      if os.path.exists(self.cloud_evdir) is False:
         os.makedirs(self.cloud_evdir)


      report_file = self.local_evdir + date + "_day_report.json"
      #report_data = load_json_file(report_file)
      #print(report_file)
      #print(report_data.keys())

      sql = """
         SELECT event_id, event_status, stations, event_start_times, obs_ids
           FROM events
          WHERE event_id like ?
      """
      date = date.replace("_", "")
      ivals = [date + "%"]
      self.cur.execute(sql,ivals)
      rows = self.cur.fetchall()

      style = """
      <style>
       .center {
          margin: auto;
          width: 80%;
          padding: 10px;
          border: 2px solid #000000 ;
       }
      </style>
      """

      good_ev = 0
      bad_ev = 0
      fail_ev = 0
      pending_ev = 0
      for row in rows:
         event_id, event_status, stations, start_times, obs_ids = row
         print(event_status)
         if "GOOD" in event_status or ("SOLVED" in event_status and "BAD" not in event_status):
            good_ev += 1
         elif "BAD" in event_status:
            bad_ev += 1
         elif "FAIL" in event_status:
            fail_ev += 1
         else:
            pending_ev += 1

      stats_nav = """
           <script>
             function goto_ev(t) {
              url = window.location.href
              let result = url.includes("GOOD")
              if (result > 0) {
                 // WE ARE ON THE GOOD PAGE
                 if (t == "good") {
                    // do nothing!
                 }
                 else {
                    url = url.replace("GOOD", "BAD")
                    window.location.replace(url)
                 }
              }
              else {
                 // WE ARE ON THE BAD PAGE
                 if (t == "good") {
                    url = url.replace("BAD", "GOOD")
                    window.location.replace(url)
                 }
                 else {
                    // do nothing!
                 }
              }
             }
           </script>
      """

      links = """
      <h4>Multi Station Events</h4> 
      <div style="width: 100%; ">
      <a href={:s}_OBS_GOOD.html>Good """.format(event_date) + str(good_ev) + """</a> -
      <a href={:s}_OBS_BAD.html>Bad """.format(event_date) + str(bad_ev) + """</a> -
      <a href={:s}_OBS_FAIL.html>Fail """.format(event_date) + str(fail_ev) + """</a> -
      <a href={:s}_OBS_PENDING.html>Pending """.format(event_date) + str(pending_ev) + """</a></div><br>
      """
  
      stats_nav += links
      self.center_lat = 45
      self.center_lon = 0

      print("links:", links)

      self.kml_link = self.local_evdir.replace(self.data_dir, "/") + "ALL_TRAJECTORIES.kml"
      self.orb_file = "https://archive.allsky.tv" + self.local_evdir.replace(self.data_dir, "/") + "ALL_ORBITS.json"
      self.orb_link = "https://orbit.allskycams.com/index_emb.php?file={:s}".format(self.orb_file)

      print(self.orb_link)

      self.map_link = """https://archive.allsky.tv/APPS/dist/maps/index.html?mf={:s}&lat={:s}&lon={:s}&zoom=3""".format(self.kml_link, str(self.center_lat), str(self.center_lon))
      self.gallery_link = event_date + "_OBS_GOOD.html"
      self.data_table_link = event_date + "_EVENT_TABLE.html"
      self.obs_by_station_link = event_date + "_OBS_BY_STATION.html"
      self.int_multi_link = event_date + "_MULTI_STATION_INT.html"
      self.int_single_link = event_date + "_SINGLE_STATION_INT.html"
      short_date = event_date.replace("_", "")
      stats_nav += """
         <div style="width: 100%">
             <i class="fa-solid fa-map-location-dot"></i>

             <span class="fa-layers-text fa-inverse" data-fa-transform="shrink-8 down-3" style="font-weight:900"><a href={:s}>Trajectories</a></span>
             <!--
          <span class="fa-layers fa-fw fa-2xl" style="background:black; padding: 5px">
          </span>-->

             <i class="fa-solid fa-solar-system"></i>
             <span class="fa-layers-text fa-inverse" data-fa-transform="shrink-8 down-3" style="font-weight:900"><a href={:s}>Orbits</a></span>
             <!--
          <span class="fa-layers fa-fw fa-2xl" style="background:black; padding: 5px">
          </span>-->

             <i class="fa-solid fa-star-shooting"></i>
             <span class="fa-layers-text fa-inverse" data-fa-transform="shrink-8 down-3" style="font-weight:900"><a href=https://archive.allsky.tv/APPS/dist/radiants.html?d={:s}>Radiants</a></span>
             <!--
          <span class="fa-layers fa-fw fa-2xl" style="background:black; padding: 5px">
          </span>-->

             <i class="fa-solid fa-table-list"></i>
             <span class="fa-layers-text fa-inverse" data-fa-transform="shrink-8 down-3" style="font-weight:900"><a href={:s}>Data Table</a></span>
             <!--
          <span class="fa-layers fa-fw fa-2xl" style="background:black; padding: 5px">
          </span> -->

             <i class="fa-solid fa-gallery-thumbnails"></i>
             <span class="fa-layers-text fa-inverse" data-fa-transform="shrink-8 down-3" style="font-weight:900"><a href={:s}>Gallery</a></span>
             <!--
          <span class="fa-layers fa-fw fa-2xl" style="background:black; padding: 5px">
          </span>-->
         </div>
      """.format(self.map_link, self.orb_link, short_date, self.data_table_link, self.gallery_link )

      stats_nav += """
          <div style="width: 100%">
             <span class="fa-layers-text fa-inverse" data-fa-transform="shrink-8 down-3" style="font-weight:700"><a href={:s}>Observations By Station</a> | </span> 
             <span class="fa-layers-text fa-inverse" data-fa-transform="shrink-8 down-3" style="font-weight:700"><a href={:s}>By Intensity (multi station)</a> | </span>
             <span class="fa-layers-text fa-inverse" data-fa-transform="shrink-8 down-3" style="font-weight:700"><a href={:s}>By Intensity (single station)</a></span>
          </div>
             <!--
          <span class="fa-layers fa-fw fa-2xl" style="background:black; padding: 5px; width:100%">
          </span>-->
      """.format(self.obs_by_station_link, self.int_multi_link, self.int_single_link)

      stats_nav += shower_links

      good_html = ""

      good_html += style
      good_html += "<h3>Meteor Archive for " + date + " " + day_nav + "</h3>"
      #good_html += "<p><h4>Solved Events (GOOD)</h4></p>"
      good_html += "<p>" + stats_nav + "</p>"

      return(good_html)


   def publish_day(self, date=None):
      shower_html = {}
      #day_nav = self.make_day_nav(selected_day=date)

      day_nav = """
                <input id='select-opt' value="{}" type="text" data-display-format="YYYY/MM/DD" data-action="reload" data-url-param="start_day" data-send-format="YYYY_MM_DD" class="datepicker form-control">
      """.format(date)
      event_date = date
      print("Publish Day", date)
      self.load_stations_file()
      self.set_dates(date)
      self.date = date
      self.help()

      qc_report = self.local_evdir + date + "_QC.json"
      if os.path.exists(qc_report):
         qc_data = load_json_file(qc_report)
         all_obs = qc_data['valid_obs']
      else:
         qc_data = {}

      self.get_all_obs(date)   

      template = ""
      tt = open("./FlaskTemplates/allsky-template-v2.html")
      for line in tt:
         template += line

      template = template.replace("{TITLE}", "ALLSKY7 EVENTS " + event_date)
      template = template.replace("AllSkyCams.com", "AllSky.com")
      self.local_evdir = self.local_event_dir + self.year + "/" + self.month + "/" + self.day  + "/"
      default_header_file = self.local_evdir + date + "_HEADER.html"
      out_file_good = self.local_evdir + date + "_OBS_GOOD.html"
      out_file_bad = self.local_evdir + date + "_OBS_BAD.html"
      out_file_failed = self.local_evdir + date + "_OBS_FAIL.html"
      out_file_pending = self.local_evdir + date + "_OBS_PENDING.html"

      if os.path.exists(self.cloud_evdir) is False:
         os.makedirs(self.cloud_evdir)


      report_file = self.local_evdir + date + "_day_report.json" 
      #report_data = load_json_file(report_file)
      #print(report_file)
      #print(report_data.keys())

      sql = """
         SELECT event_id, event_status, stations, event_start_times, obs_ids 
           FROM events
          WHERE event_id like ?
      """
      date = date.replace("_", "")
      ivals = [date + "%"]
      self.cur.execute(sql,ivals)
      rows = self.cur.fetchall()
      style = """
      <style>
       .center {
          margin: auto;
          width: 80%;
          padding: 10px;
          border: 2px solid #000000 ;
       }
      </style>
      """

      good_ev = 0
      bad_ev = 0
      fail_ev = 0
      pending_ev = 0
      for row in rows:
         event_id, event_status, stations, start_times, obs_ids = row
         print(event_status)
         if "GOOD" in event_status or ("SOLVED" in event_status and "BAD" not in event_status):
            good_ev += 1
         elif "BAD" in event_status:
            bad_ev += 1
         elif "FAIL" in event_status:
            fail_ev += 1
         else:
            pending_ev += 1

      stats_nav = """
           <script>
             function goto_ev(t) {
              url = window.location.href
              let result = url.includes("GOOD")
              if (result > 0) {
                 // WE ARE ON THE GOOD PAGE
                 if (t == "good") {
                    // do nothing!
                 }
                 else {
                    url = url.replace("GOOD", "BAD")
                    window.location.replace(url)
                 }
              } 
              else {
                 // WE ARE ON THE BAD PAGE
                 if (t == "good") {
                    url = url.replace("BAD", "GOOD")
                    window.location.replace(url)
                 }
                 else {
                    // do nothing!
                 }
              }
             }
           </script>
      """

      #stats_nav += " <a href=javascript:goto_ev('good')>Good " + str(good_ev) + "</a> - "
      #stats_nav += " <a href=javascript:goto_ev('bad')>Bad " + str(bad_ev) + "</a> </p><p> "
      #stats_nav += "<a href=javascript:goto_ev('fail')>Fail " + str(fail_ev) + "</a> - "
      #stats_nav += "<a href=javascript:goto_ev('pending')>" + "Pending " + str(pending_ev) + "</a>"

      if os.path.exists(self.all_events_file) is True:
         all_events_data = load_json_file(self.all_events_file)
      else:
         all_events_data = []

      showers = {}
      # shower links 1
      for ev_data in all_events_data:
         print(ev_data.keys())
         if "solution" not in ev_data:
            continue
         if "orb" in ev_data:
            orb = ev_data['orb']
            if orb is None:
               continue
         if "solution" in ev_data:
            sol = ev_data['solution']
            if "SOLVED" not in ev_data['solve_status']:
               print(ev_data['solve_status'])
               continue


         if "shower" in ev_data:
            shower_code = ev_data['shower']['shower_code']
         else:
            shower_code = "..."

         if "orb" in ev_data:
            orb = ev_data['orb']
            if orb is not None:
               if orb['a'] is None:
                  continue
               if shower_code == "...":
                  if float(orb['a']) <= 0:
                     shower_code = "SPORADIC-BAD"
                  elif 0 < float(orb['a']) < 5.2:
                     shower_code = "SPORADIC-INNER"
                  else:
                     shower_code = "SPORADIC-OUTER"
         if shower_code not in showers:
            showers[shower_code] = 1
         else:
            showers[shower_code] += 1

      temp = []

      for shower in showers:
         print(shower)
         temp.append((shower, showers[shower]))
      showers = sorted(temp, key=lambda x: x[1], reverse=True)
      save_json_file(self.local_evdir + "shower_links_file.json", showers)
      # shower links 1 
      shower_links = "<p>"
      for shower in showers:
         print(shower)
         shower_links += """
         <a href={:s}.html>{:s}</a> {:s} - 
         """.format(shower[0], shower[0], str(shower[1]))
      shower_links += "</p>"


      links = """
      <a href={:s}_OBS_GOOD.html>Good """.format(event_date) + str(good_ev) + """</a> - 
      <a href={:s}_OBS_BAD.html>Bad """.format(event_date) + str(bad_ev) + """</a> -
      <a href={:s}_OBS_FAIL.html>Fail """.format(event_date) + str(fail_ev) + """</a> - 
      <a href={:s}_OBS_PENDING.html>Pending """.format(event_date) + str(pending_ev) + """</a>"""

      stats_nav += links
      self.center_lat = 45
      self.center_lon = 0 

      print("links:", links)

      self.kml_link = self.local_evdir.replace(self.data_dir, "/") + "ALL_TRAJECTORIES.kml"
      self.orb_file = "https://archive.allsky.tv" + self.local_evdir.replace(self.data_dir, "/") + "ALL_ORBITS.json"
      self.orb_link = "https://orbit.allskycams.com/index_emb.php?file={:s}".format(self.orb_file)

      print(self.orb_link)

      self.map_link = """https://archive.allsky.tv/APPS/dist/maps/index.html?mf={:s}&lat={:s}&lon={:s}&zoom=3""".format(self.kml_link, str(self.center_lat), str(self.center_lon))
      self.gallery_link = event_date + "_OBS_GOOD.html"
      self.data_table_link = event_date + "_EVENT_TABLE.html"

      self.obs_by_station_link = event_date + "_OBS_BY_STATION.html"
      self.int_multi_link = event_date + "_MULTI_STATION_INT.html"
      self.int_single_link = event_date + "_SINGLE_STATION_INT.html"

      short_date = event_date.replace("_", "")
      stats_nav += """
         </p>
         <P>
          <span class="fa-layers fa-fw fa-2xl" style="background:black; padding: 5px">
             <i class="fa-solid fa-map-location-dot"></i>

             <span class="fa-layers-text fa-inverse" data-fa-transform="shrink-8 down-3" style="font-weight:900"><a href={:s}>Trajectories</a></span>
          </span>

          <span class="fa-layers fa-fw fa-2xl" style="background:black; padding: 5px">
             <i class="fa-solid fa-solar-system"></i>
             <span class="fa-layers-text fa-inverse" data-fa-transform="shrink-8 down-3" style="font-weight:900"><a href={:s}>Orbits</a></span>
          </span>

          <span class="fa-layers fa-fw fa-2xl" style="background:black; padding: 5px">
             <i class="fa-solid fa-star-shooting"></i>
             <span class="fa-layers-text fa-inverse" data-fa-transform="shrink-8 down-3" style="font-weight:900"><a href=https://archive.allsky.tv/APPS/dist/radiants.html?d={:s}>Radiants</a></span>
          </span>

          <span class="fa-layers fa-fw fa-2xl" style="background:black; padding: 5px">
             <i class="fa-solid fa-table-list"></i>
             <span class="fa-layers-text fa-inverse" data-fa-transform="shrink-8 down-3" style="font-weight:900"><a href={:s}>Data Table</a></span>
          </span>

          <span class="fa-layers fa-fw fa-2xl" style="background:black; padding: 5px">
             <i class="fa-solid fa-gallery-thumbnails"></i>
             <span class="fa-layers-text fa-inverse" data-fa-transform="shrink-8 down-3" style="font-weight:900"><a href={:s}>Gallery</a></span>
          </span>

         </P>
      """.format(self.map_link, self.orb_link, short_date, self.data_table_link, self.gallery_link )

      stats_nav += """
          <div>
          <h3>Observations</h3>
          </div>
          <span class="fa-layers fa-fw fa-2xl" style="background:black; padding: 5px; width:100%">
             <span class="fa-layers-text fa-inverse" data-fa-transform="shrink-8 down-3" style="font-weight:700"><a href={:s}>By Station</a> | </span>
             <span class="fa-layers-text fa-inverse" data-fa-transform="shrink-8 down-3" style="font-weight:700"><a href={:s}>By Intensity (multi station)</a> | </span>
             <span class="fa-layers-text fa-inverse" data-fa-transform="shrink-8 down-3" style="font-weight:700"><a href={:s}>By Intensity (single station)</a></span>
          </span>
      """.format(self.obs_by_station_link, self.int_multi_link, self.int_single_link)

      stats_nav += shower_links

      good_html = ""
      all_bad_html = "" 
      bad_html = "" 
      fail_html = "" 
      pending_html = "" 
      default_header = "" 


      default_header += style
      default_header += "<h3>Meteor Archive for " + date + " " + day_nav + "</h3>" 
      default_header += "<p>" + stats_nav + "</p>"

      good_html += style
      good_html += "<h3>Meteor Archive for " + date + " " + day_nav + "</h3>" 
      good_html += "<h4>Solved Events (GOOD)</h4>"
      good_html += "<p>" + stats_nav + "</p>"

      all_bad_html += "<h3>Meteor Archive for " + date + " " + day_nav + "</h3>"
      all_bad_html += "<h4>Solved Events with Bad Solution</h4>"
      all_bad_html += "<p>" + stats_nav + "</p>"

      fail_html += "<h3>Meteor Archive for " + date + " " + day_nav + "</h3>"
      fail_html += "<h4>Failed Events </h4>"
      fail_html += "<p>" + stats_nav + "</p>"

      pending_html += "<h3>Meteor Archive for " + date + " " + day_nav + "</h3>"
      pending_html += "<h4>Pending Events </h4>"
      pending_html += "<p>" + stats_nav + "</p>"
 
      fpout = open(default_header_file, "w")
      fpout.write(default_header)
      fpout.close()


      stats = {}
      plane_desc = {}
      for row in rows:
         event_id, event_status, stations, start_times, obs_ids = row
         stations = json.loads(stations)
         start_times = json.loads(start_times)
         obs_ids = json.loads(obs_ids)
         ev_dir = self.local_evdir + event_id + "/"
         if os.path.exists(ev_dir) is False:
            os.makedirs(ev_dir)

         ev_file = ev_dir + event_id + "-event.json"
         ev_fail_file = ev_dir + event_id + "-fail.json"
         if os.path.exists(ev_file) is False:
            pick_file = ev_file.replace("-event.json", "_trajectory.pickle")
            # this should make the event.json if the pickle exists
            if os.path.exists(pick_file) is True:
               resp = make_event_json(event_id, ev_dir ,{})

         if os.path.exists(ev_file) is False and os.path.exists(ev_fail_file) is True:
            ev_sum = "<h3>Solve failed for event {}</h3>".format(event_id)
            ev_data = None
         elif os.path.exists(ev_file) is False and os.path.exists(ev_fail_file) is False: 
            ev_sum = "<h3>Solve for event {} has not been run.</h3>".format(event_id)
            ev_data = None

         else:
            ev_data = load_json_file(ev_file)
            if "shower" not in ev_data:
               ev_data["shower"] = {}
               ev_data['shower']["shower_code"] = "..."
            if "start_lat" not in ev_data['traj']:
               ev_data['traj']['start_lat'] = False
               continue
            if ev_data['orb']['a'] is not None and math.isnan(ev_data['traj']['start_lat']) is False:
               print("EVENT FILE FOUND:", ev_file)
               ev_sum = """
               <center>
               <table border=1 cellpadding=5 cellspacing=5>
               <tr>
                  <th>Start Alt</th>
                  <th>End Alt</th>
                  <th>Vel</th>
                  <th>a</th>
                  <th>e</th>
                  <th>i</th>
                  <th>q</th>
                  <th>Shower</th>
               </tr>
               <tr>
                  <th>{} km</th>
                  <th>{} km</th>
                  <th>{} km/s</th>
                  <th>{} </th>
                  <th>{}</th>
                  <th>{}</th>
                  <th>{}</th>
                  <th>{}</th>
               </tr>
               </table>
               </center>

               """.format(int(ev_data['traj']['start_ele']/1000), int(ev_data['traj']['end_ele']/1000), int(ev_data['traj']['v_init']/1000), round(ev_data['orb']['a'],4), round(ev_data['orb']['e'],4), round(ev_data['orb']['i'],4), round(ev_data['orb']['q'],4), ev_data['shower']['shower_code'])


         
                  

               #if shower not in by_shower:
               #   by_shower[shower] = []




            else:
               ev_sum = "Bad solve."

         if ev_data is not None:
            if "shower" in ev_data:
               if ev_data['shower']['shower_code'] == "...":
                  shower_code = "SPORADIC"
               else:
                  shower_code = ev_data['shower']['shower_code']
            else:
               shower_code = "SPORADIC"
         else:
            shower_code = "SPORADIC"
         if event_status is None:
            event_status = "PENDING"
         if "GOOD" in event_status or ("SOLVED" in event_status and "BAD" not in event_status and "FAIL" not in event_status) and ev_data is not None:
            if ev_data is not None:
               if "shower" not in ev_data:
                  print("No shower data in event")
               elif ev_data['shower']['shower_code'] == "...":
                  orb = ev_data['orb']
                  if "a" in orb:
                     if orb['a'] is not None:
                        if float(orb['a']) <= 0:
                           shower_code = "SPORADIC-BAD"
                        elif 0 < float(orb['a']) < 5.2:
                           shower_code = "SPORADIC-INNER"
                        else:
                           shower_code = "SPORADIC-OUTER"
               else:
                  shower_code = ev_data['shower']['shower_code']

            if shower_code not in shower_html:
               shower_html[shower_code] = ""
            temp_html = ""
            temp_html += "<div class='center'>"
            plane_file = ev_dir + "/" + event_id + "_PLANES.json"
            if os.path.exists(plane_file) is False:
               plane_report = self.plane_test_event(obs_ids, event_id, event_status)
               save_json_file(plane_file, plane_report, True)
            else:
               plane_report = load_json_file(plane_file)
            good_planes,total_planes = self.check_planes(plane_report['results'])
            plane_desc[event_id] = str(good_planes) + " / " + str(total_planes) + " PLANES"

            temp_html += "<h3>" + event_id + " - " + event_status + " " 
            temp_html += plane_desc[event_id] + "</h3>"
            temp_html += ev_sum

            for i in range(0,len(obs_ids)):

               st = stations[i]
               if st not in stats:
                  stats[st] = {}
                  stats[st]['good'] = 1
                  stats[st]['bad'] = 0
               stats[st]['good'] += 1
               obs_id = obs_ids[i]
               etime = start_times[i]
               #good_html += self.obs_id_to_img_html(obs_id)

               temp_html += self.meteor_cell_html(obs_id,etime)

               temp_html += "\n"
            temp_html += "<div style='clear: both'></div>"
            temp_html += "</div>"
            good_html += temp_html
            print("ADD TEMP HTML SHOWER CODE:", shower_code)
            shower_html[shower_code] += temp_html

         elif "BAD" in event_status :
            bad_html = "<div>"
            if "SPORADIC" in shower_code:
               shower_code = "SPORADIC-BAD"
            if shower_code not in shower_html:
               shower_html[shower_code] = ""

            # TEST BAD PLANES! 
            plane_file = ev_dir + "/" + event_id + "_PLANES.json"
            if os.path.exists(plane_file) is False:
               plane_report = self.plane_test_event(obs_ids, event_id, event_status)
               save_json_file(plane_file, plane_report, True)
            else:
               plane_report = load_json_file(plane_file)
            good_planes,total_planes = self.check_planes(plane_report['results'])
            plane_desc[event_id] = str(good_planes) + " / " + str(total_planes) + " PLANES"

            bad_html += "<h3>" + event_id + " - " + event_status + " " 
            bad_html += plane_desc[event_id] + "</h3>"
            bad_html += ev_sum
            #self.plane_test_event(obs_ids)
            for i in range(0,len(obs_ids)):
               st = stations[i]
               if st not in stats:
                  stats[st] = {}
                  stats[st]['good'] = 0
                  stats[st]['bad'] = 1
               stats[st]['bad'] += 1
             
               obs_id = obs_ids[i]
               etime = start_times[i]
               #bad_html += self.obs_id_to_img_html(obs_id)
               if obs_id in all_obs:
                  obs_status = all_obs[obs_id]
               else:
                  print(obs_id, "missing")
                  obs_status = "deleted"
               bad_html += self.meteor_cell_html(obs_id, etime, obs_status)
               bad_html += "\n"

            bad_html += "<div style='clear: both'></div>"
            bad_html += "</div>"
            shower_html[shower_code] += bad_html 
            all_bad_html += bad_html
         elif "FAILED" in event_status :
            fail_html += "<div>"

            # TEST BAD PLANES! 
            plane_file = ev_dir + event_id + "_PLANES.json"
            if os.path.exists(plane_file) is False:
               plane_report = self.plane_test_event(obs_ids, event_id, event_status)
               save_json_file(plane_file, plane_report, True)
            else:
               plane_report = load_json_file(plane_file)
            good_planes,total_planes = self.check_planes(plane_report['results'])
            plane_desc[event_id] = str(good_planes) + " / " + str(total_planes) + " PLANES"

            fail_html += "<h3>" + event_id + " - " + event_status + " " 
            fail_html += plane_desc[event_id] + "</h3>"
            #self.plane_test_event(obs_ids)
            for i in range(0,len(obs_ids)):
               st = stations[i]
               if st not in stats:
                  stats[st] = {}
                  stats[st]['good'] = 0
                  stats[st]['bad'] = 1
               stats[st]['bad'] += 1
             
               obs_id = obs_ids[i]
               etime = start_times[i]
               if obs_id in all_obs:
                  obs_status = all_obs[obs_id]
               else:
                  obs_status = "deleted"
               fail_html += self.meteor_cell_html(obs_id, etime, obs_status)
               fail_html += "\n"

            fail_html += "<div style='clear: both'></div>"
            fail_html += "</div>"
         else:
            pending_html += "<div>"

            # TEST BAD PLANES! 
            plane_file = ev_dir + event_id + "_PLANES.json"
            if os.path.exists(plane_file) is False:
               plane_report = self.plane_test_event(obs_ids, event_id, event_status)
               save_json_file(plane_file, plane_report, True)
            else:
               plane_report = load_json_file(plane_file)
            good_planes,total_planes = self.check_planes(plane_report['results'])
            plane_desc[event_id] = str(good_planes) + " / " + str(total_planes) + " PLANES"

            pending_html += "<h3>" + event_id + " - " + event_status + " " 
            pending_html += plane_desc[event_id] + "</h3>"
            #self.plane_test_event(obs_ids)
            for i in range(0,len(obs_ids)):
               st = stations[i]
               if st not in stats:
                  stats[st] = {}
                  stats[st]['good'] = 0
                  stats[st]['bad'] = 1
               stats[st]['bad'] += 1
             
               obs_id = obs_ids[i]
               etime = start_times[i]

               if "obs_id" in all_obs:
                  obs_status = all_obs[obs_id]
               else:
                  obs_status = "DELETED"
               pending_html += self.meteor_cell_html(obs_id, etime, obs_status)
               pending_html += "\n"

            pending_html += "<div style='clear: both'></div>"
            pending_html += "</div>"

      #

      for shower in shower_html:
         print("SHOWER OUT:", shower, shower_html[shower])
         iframe_file = self.local_evdir + "ALL_ORBITS-frame-{:s}.html".format(shower)
         iframe = ""
         if os.path.exists(iframe_file):
            fp = open(iframe_file)
            for line in fp:
               iframe += line

         out_file_shower = self.local_evdir + "{:s}.html".format(shower)
         temp = template.replace("{MAIN_CONTENT}", default_header + iframe + shower_html[shower])
         fpo = open(out_file_shower, "w")
         fpo.write(temp)
         fpo.close()
         print("SAVED:", out_file_shower)


      fpo = open(out_file_good, "w")
      temp = template.replace("{MAIN_CONTENT}", good_html)
      fpo.write(temp)
      fpo.close()

      temp = template.replace("{MAIN_CONTENT}", all_bad_html)
      fpo = open(out_file_bad, "w")
      fpo.write(temp)
      fpo.close()

      temp = template.replace("{MAIN_CONTENT}", fail_html)
      fpo = open(out_file_failed, "w")
      fpo.write(temp)
      fpo.close()

      temp = template.replace("{MAIN_CONTENT}", pending_html)
      fpo = open(out_file_pending, "w")
      fpo.write(temp)
      fpo.close()



      rpt_data = []
      for st in stats:
         g = stats[st]['good']
         b = stats[st]['bad']
         t = g + b
         bad_perc = b / t

         rpt_data.append((int(st.replace("AMS","")), bad_perc, g,b, t))
      rpt_data = sorted(rpt_data, key=lambda x: (x[1]), reverse=False)

      for row in rpt_data:
         st, bad_perc, g,b,t = row
         st_id = "AMS{:03}".format(st)
         #print(st_id + " " + str(round(bad_perc*100,1)) + "% of solves failed (" + str(b) + "/" + str(t) + " events)".format(st)  )


      # PUSH FINAL HTML TO CLOUD
      push_cmd = "cp " + self.local_evdir + "*.html " + self.cloud_evdir
      print(push_cmd)
      os.system(push_cmd)

      # station events

      self.station_events(event_date)
      push_cmd = "cp " + self.station_events_file + " " + self.cloud_evdir
      print(push_cmd)
      os.system(push_cmd)
      cmd = "/usr/bin/python3 EM.py aer " + event_date

      

   def plane_test_event(self, obs_ids, event_id, event_status, force=False):

      jobs = []

      results = {}
      good = 0
      bad = 0
      st_stats = {}
      ob_stats = {}
      good_planes = {}
      bad_planes = {}
      for ob1 in obs_ids:
         for ob2 in obs_ids:
            st1 = ob1.split("_")[0]
            st2 = ob2.split("_")[0]
            if ob1 != ob2 and st1 != st2:
               key = ob1 + "__" +ob2  
               gd = [event_id, key, ob1, ob2]
               jobs.append(gd)

      self.run_plane_jobs(jobs, force)

      plane_report = {}
      rkeys = self.r.keys(event_id + "*")
      for key in rkeys:
         temp = self.r.get(key)
         if temp is not None:
            result, sanity = json.loads(temp)
            results[key] = (sanity, result)

      plane_report['results'] = results

      return(plane_report)


   def obs_id_to_img_url(self,obs_id):
      el = obs_id.split("_")
      st = el[0]
      ff = obs_id.replace(st + "_", "")
      cloud_url = "https://archive.allsky.tv/" + st + "/METEORS/" + ff[0:4] + "/" + ff[0:10] + "/" + st + "_" + ff + "-prev.jpg"
      file_name = "/mnt/archive.allsky.tv/" + st + "/METEORS/" + ff[0:4] + "/" + ff[0:10] + "/" + st + "_" + ff + "-prev.jpg"
      return(cloud_url, file_name)

   def obs_id_to_img_html(self,obs_id):
      el = obs_id.split("_")
      st = el[0]
      ff = obs_id.replace(st + "_", "")
      cloud_url = "https://archive.allsky.tv/" + st + "/METEORS/" + ff[0:4] + "/" + ff[0:10] + "/" + st + "_" + ff + "-prev.jpg"
      play_link = """ <a href="javascript:click_icon('play', '""" + obs_id.replace(".jpg", "") + """')"> """
      html = play_link + """
         <img src="{:s}" onerror="this.display=None;"></a>
      """.format(cloud_url)
      return(html)

   def make_event_obs_html(self,row):
      event_id, event_status, stations, start_times, obs_ids = row
      out = """
         <div>

         </div>
      """

   def day_status(self, date=None):
      os.system("clear")
      self.load_stations_file()
      print("EEEE")
      exit()
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
         #print(data)
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
      save_json_file(report_file, day_report, True)
      print("\n\nsaved:", report_file)

   def day_publish(self, date):

      print("ok")

   def day_load(self, date):
      print("ok")

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
      save_json_file(self.obs_dict_file, self.obs_dict, True)

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
Copyright Mike Hankey LLC 2016-2022
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

      start_points = []
      end_points = []
      for key in planes:
         result, score = planes[key]
         if len(result) >= 2:
            end = result[0]
            start = result[-1]
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
            start_lat_diff = abs(med_start_lat - start[0])
            start_lon_diff = abs(med_start_lon - start[1])
            end_lat_diff = abs(med_end_lat - start[0])
            end_lon_diff = abs(med_end_lon - start[1])
            score = start_lat_diff + start_lon_diff + end_lat_diff + end_lon_diff
            score_data.append((score, key))
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
            solve_data['event_day'] = event_day

         temp = self.good_obs_to_event(event_day, event_id)
         for key in temp:
            solve_data[key] = temp[key]
         event_data = solve_data

      print(event_data)

      #insert_meteor_event(self.dynamodb, event_id, event_data)
      
   def meteor_cell_html(self, obs_id,edatetime=None,status=None):

      #print("METEOR CELL:", status)

      if edatetime is not None:
         edate, etime = edatetime.split(" ")
      else:
         edate = ""
         etime = ""
      if "prev.jpg" not in obs_id:
         obs_id += "-prev.jpg"
      cloud_root  = "/mnt/archive.allsky.tv/"
      cloud_vroot = "https://archive.allsky.tv/"
      station_id = obs_id.split("_")[0]
      year = obs_id.split("_")[1]
      month = obs_id.split("_")[2]
      dom = obs_id.split("_")[3]
      hour = obs_id.split("_")[4]
      minute = obs_id.split("_")[5]
      second = obs_id.split("_")[6]
      mili_second = obs_id.split("_")[7]
      cam = obs_id.split("_")[8].split("-")[0]

      day = year + "_" + month + "_" + dom
      cloud_dir = cloud_root + station_id + "/METEORS/" + year + "/" + day + "/"
      cloud_vdir = cloud_vroot + station_id + "/METEORS/" + year + "/" + day + "/"
      prev_img_file = cloud_dir + obs_id.replace(".mp4","-prev.jpg")
      prev_img_url = cloud_vdir + obs_id.replace(".mp4","-prev.jpg")
      div_id = obs_id.replace(".mp4", "")
      div_id = div_id.replace("-prev.jpg", "")

      if status == None:
         opacity = "1"
      elif status == 1:
         opacity = "1"
      else:
         opacity = "1"

      disp_text = station_id + " - " + cam + " - " +  etime #+ "<br>"
      video_url = prev_img_url.replace("-prev.jpg", "-180p.mp4")
      disp_text += """ <a href="javascript:play_video('{}','{}')"><i style='font-size: 12px' class="fas fa-play "></i></a>""".format(div_id, video_url)
      #if os.path.exists(prev_img_file) is True:
      if True:
         html = """
         <div id="{:s}" style="
              float: left;
              background-image: url('{:s}');
              background-repeat: no-repeat;
              background-size: 320px;
              width: 320px;
              height: 180px;
              margin: 25px; 
              opacity: {:s}; 
              "
              onerror="this.display=None;"
              >
              <div class="show_hider"> {:s} </div>
         </div>
         """.format(div_id, prev_img_url, opacity, disp_text)
      else:
         html = ""
         #station_id + " " + obs_id.replace(".mp4", "")
      return(html)


   def make_kml(self, kml_file, points, lines, line_names = None):
      print(len(points))
      print(len(lines))
      print(len(line_names))
      kml = simplekml.Kml()
      colors = self.get_kml_colors()
      #fol_day = kml.newfolder(name=self.date + " AS7 EVENTS")
      #fol_obs = fol_day.newfolder(name=self.date + " AS7 EVENTS")
      color = "FFFFFFFF"
      for point in points:
         print(point)
         lon = point[1]
         lat = point[0]
         text = point[2]
         pnt = kml.newpoint(name=text, coords=[(lon,lat)])

            #lines.append((st_pts[st][0], st_pts[st][1], st_az_pts[st][0][0] , st_az_pts[st][0][1], 'green'))
      c = 0
      for line in lines :
         if line_names is not None :
            name = line_names[c]
         else:
            name = ""
         lat1, lon1, lat2, lon2, color = line
         kline = kml.newlinestring(name=name , description="", coords=[(lon1,lat1,100),(lon2,lat2,100)])
         kline.altitudemode = simplekml.AltitudeMode.clamptoground
         kline.linestyle.color = color 
         kline.linestyle.colormode = "normal"
         kline.linestyle.width = "3"
         c += 1
      kml.save(kml_file)
      print("SAVED", kml_file)
      #for line in lines:

   def make_plane_kml(self, event, planes):
      print("   MAKE PLANE KML", event['event_id']) 
      event_id = event['event_id']
      kml = simplekml.Kml()
      colors = self.get_kml_colors()
      fol_day = kml.newfolder(name=self.date + " AS7 EVENTS")
      fol_obs = fol_day.newfolder(name=self.date + " AS7 EVENTS")
      color = "FFFFFFFF"

      for combo_key in event['planes']:
         ev_id = 0
         o_combo_key = combo_key.replace("EP:", "")
         #print("COMBO KEY IS:", combo_key)
         ob1,ob2 = combo_key.split("__")
         if True:
            line1 = event['planes'][combo_key][1]
            #line2 = event['planes'][combo_key][1]
            #color = event['planes'][combo_key]['color']
            color = "FFFFFFFF"
            try:
               pt1, pt2 = line1
            except:
               continue
            slat,slon,salt= pt1 
            elat,elon,ealt = pt2
            salt = salt * 1000
            ealt = ealt * 1000

            line = fol_day.newlinestring(name=combo_key, description="", coords=[(slon,slat,salt),(elon,elat,ealt)])
            line.altitudemode = simplekml.AltitudeMode.relativetoground
            line.linestyle.color = color
            line.linestyle.colormode = "normal"
            line.linestyle.width = "3"
            #print("PLANE:", (slon,slat,salt),(elon,elat,ealt))
            #slat,slon,salt,elat,elon,ealt = line2
            #line = fol_day.newlinestring(name=combo_key, description="", coords=[(slon,slat,salt),(elon,elat,ealt)])
            #line.altitudemode = simplekml.AltitudeMode.relativetoground
            #line.linestyle.color = color
            #line.linestyle.colormode = "normal"
            #line.linestyle.width = "3"
      self.plane_kml_file = self.local_evdir + "/" + event_id + "/" + event_id + "-planes.kml"
      #if os.path.exists(self.ev_dir + "/" + event['event_id']) is False:
      #   os.makedirs(self.event_dir + "/" + event['event_id'])
      kml.save(self.plane_kml_file)
      print(self.plane_kml_file)
      print("SAVED:", self.plane_kml_file)

   def get_kml_colors(self):
      colors = []
      for key in kml_colors:
         colors.append(kml_colors[key])
      return(colors)




   def check_start_ai_server(self):
      # test the AI server if not running start it and sleep for 30 seconds
      url = "http://localhost:5000/"
      try:
         response = requests.get(url)
         content = response.content.decode()
      except Exception as e:
         if "HTTP" in str(e):
            print(colored(" AI URL FAILED: " + url, 'red'))
            cmd = "/usr/bin/python3.6 AIServer.py > /dev/null 2>&1 & "
            #cmd = "/usr/bin/python3.6 AIServer.py " #> /dev/null 2>&1 & "
            print(colored(" Restarting AI Server: " + url, 'red'))
            print(colored(" Wait 40 seconds...: " + url, 'red'))
            print(" " + cmd)
            os.system(cmd)
            time.sleep(20)

   def check_ai_img(self, ai_image=None, ai_file=None):
      if ai_image is not None and ai_file is None:
         cv2.imwrite("/mnt/ams2/temp.jpg", ai_image)
         ai_file = "/mnt/ams2/temp.jpg"

      if True:
         url = "http://localhost:5000/AI/METEOR_ROI/?file={}".format(ai_file)
         try:
            response = requests.get(url)
            content = response.content.decode()
            content = json.loads(content)
            #print(content)
         except Exception as e:
            print("HTTP ERR:", e)
      
      return(content)

   def obs_timeline (self, event_date):
      html = """

  <script type="text/javascript" src="https://www.gstatic.com/charts/loader.js"></script>
  <script type="text/javascript">
  google.charts.load("current", {packages:["timeline"]});
  google.charts.setOnLoadCallback(drawChart);
  function drawChart() {

    var container = document.getElementById('example5.1');
    var chart = new google.visualization.Timeline(container);
    var dataTable = new google.visualization.DataTable();
    dataTable.addColumn({ type: 'string', id: 'Room' });
    dataTable.addColumn({ type: 'string', id: 'Name' });
    dataTable.addColumn({ type: 'date', id: 'Start' });
    dataTable.addColumn({ type: 'date', id: 'End' });
    dataTable.addRows([
     """
      sql = """
        SELECT obs_id FROM event_obs ORDER BY station_id;
      """
      self.cur.execute(sql)
      rows = self.cur.fetchall()

      js_rows = ""
      for row in rows:
         obs_id = row[0]
         elm = obs_id.split("_")
         st = elm[0]  
         hour = elm[4]  
         minute = elm[5]  
         second = elm[6]  
         ehour = hour
         eminute = minute 
         esec = str(int(second) + 5)
         if int(esec) >= 60:
            esec = str(int(esec) - 60)
            eminute = int(minute) + 1
            if int(minute) >= 60:
               eminute = "0"
               ehour = str(int(hour)+1)

            else:
               eminute = str(eminute)
         if js_rows != "":
            js_rows += ","

         js_rows += """[ '{:s}', '{:s}', new Date({:s}, {:s}, {:s}, {:s}, {:s}, {:s}), new Date({:s}, {:s}, {:s}, {:s}, {:s}, {:s})]""".format(st, st, "0","0","0",hour, minute, second,"0","0","0",ehour,eminute,esec)

         print(obs_id, hour, minute, second)
      html += js_rows + "]);"

      html += """

    var options = {
      timeline: { colorByRowLabel: true }
    };

    chart.draw(dataTable, options);
  }

  </script>

  <div id="example5.1" style="height: 100px;"></div>

   """

      print(html)

   def make_obs_object(self, obs_id):
      obj = {}   
      obj['obs_id'] = obs_id  
      obj['station_id'] = obs_id.split("_")[0]
      obj['primary'] = True
      obj['ignore'] = False
      obj['media_files'] = {}
      obj['data_files'] = {}
      obj['calibration'] = {}
      return(obs_id)

   def edit_event(self, event_id):
      event_day = self.event_id_to_date(event_id)
      year, month, day_of_month = event_day.split("_")
      self.local_event_id_dir = self.local_event_dir + year + "/" + month + "/" + day_of_month + "/" + event_id + "/"
      all_files = os.listdir(self.local_event_id_dir)

      obs_data = {}

      for ev in all_files:
         ftype = ""
         root_file = ""
         obs_id = ""
         trim_num = ""
         if "AMS" == ev[0:3]:
            if ".mp4" in ev:
               ftype = "mp4"
            if ".jpg" in ev:
               ftype = "jpg"
            if ".json" in ev:
               ftype = "json"
            if ".html" in ev:
               ftype = "html"

            felm = ev.split("-")
            if "CLOUDFILES" in ev:
               ftype = "json"
               root_file = felm[0] 
               obs_id = felm[0] 
            elif len(felm) >= 3:
               trim_num = felm[2]
               root_file = felm[0] 
               obs_id = root_file + "-trim-" + felm[2] 
            elif len(felm) == 1:
               ftype = "min_file"
               root_file = felm[0] 
               obs_id = root_file 
            else:
               ftype = "min_file"
               root_file = ev 
               obs_id = root_file 

            station_id = ev.split("_")[0]
            if station_id not in obs_data:
               obs_data[station_id] = {}
               obs_data[station_id]['obs'] = {}
            if root_file not in obs_data[station_id]['obs']:
               obs_data[station_id]['obs'][root_file] = {}
               obs_data[station_id]['obs'][root_file]['files'] = {}
            obs_data[station_id]['obs'][root_file]['files'][ev] = {} 

      for station in obs_data:
         for obs_id in obs_data[station]['obs']:
            if "mp4" in obs_id:
               gtype = "* MIN FILE"
            else:
               gtype = ""
            if "files" in obs_data[station]['obs'][obs_id]:
               for ofile in obs_data[station]['obs'][obs_id]['files']:
                  print("      ", ofile) #, obs_data[station]['obs'][obs_id]['files'][ofile])
            #else:
            #   print("NO FILES")

   def time_sync_frame_data(self):
      self.time_sync_data = {}
      self.unq_obs = {}
      for obs_fn in self.all_frame_data:
         self.unq_obs[obs_fn] = {}
         done = False
         for fc in self.all_frame_data[obs_fn]:
            if len(self.all_frame_data[obs_fn][fc]['cnts'] ) > 0:
               ft = self.all_frame_data[obs_fn][fc]['frame_time']
               if ft not in self.time_sync_data:
                  self.time_sync_data[ft] = {}
               if obs_fn not in self.time_sync_data[ft]:
                  self.time_sync_data[ft][obs_fn] = {}
               if fc not in self.time_sync_data[ft][obs_fn]:
                  self.time_sync_data[ft][obs_fn][fc] = {}
                  self.time_sync_data[ft][obs_fn][fc]['cnts'] = self.all_frame_data[obs_fn][fc]['cnts']
               # get the crop thumb
               else:
                  print("NO FRAMES FOR", obs_fn)



               #print("FRAME TIME:", obs_fn, self.all_frame_data[obs_fn][fc]['frame_time'])
               done = True


      tw = 320
      th = 180
      max_thumbs = 36
      max_cols = 6
      max_rows = 6
      mc = 0
      oc = 0
      rc = 0

      main_frame = np.zeros((1080,1920,3),dtype=np.uint8)
      for obs_id in self.unq_obs:
 
         x1 = oc * tw
         x2 = x1 + tw
         y1 = rc * th
         y2 = y1 + th
         self.unq_obs[obs_id] = [x1,y1,x2,y2]
         if oc >= max_cols - 1 :
            oc = 0
            rc += 1
         else:
            oc += 1
      for obs_id in self.unq_obs:
         x1,y1,x2,y2 = self.unq_obs[obs_id]
         cv2.putText(main_frame, str(obs_id),  (x1,y1), cv2.FONT_HERSHEY_SIMPLEX, .6, (255,255,255), 1)
         cv2.rectangle(main_frame, (int(x1), int(y1)), (int(x2) , int(y2) ), (255, 255, 255), 2)
         cv2.imshow('pepe', main_frame)
         cv2.waitKey(30)

 
      light_curves = {}
      for key in self.time_sync_data:
         main_frame = np.zeros((1080,1920,3),dtype=np.uint8)

         for obs_fn in self.time_sync_data[key]:
         #for obs_fn in self.unq_obs:
            fimg = np.zeros((th,tw,3),dtype=np.uint8)
            if obs_fn in self.time_sync_data[key]: 
               #print("OBS ID FOUND:", obs_fn, self.time_sync_data[key].keys())
               x1,y1,x2,y2 = self.unq_obs[obs_fn]
               if obs_fn in self.all_frames:
                  for fc in self.time_sync_data[key][obs_fn]:
                     fimg = np.zeros((th,tw,3),dtype=np.uint8)
                     print( key, obs_fn, fc, self.time_sync_data[key][obs_fn])
                     # NEED FRAME NUMBER???
                     if obs_fn in self.all_frames:
                        if int(fc) <= len(self.all_frames[obs_fn]):
                           fimg = self.all_frames[obs_fn][int(fc)]
                           #cv2.imshow('pepe', fimg)
               #else:
               #   print(obs_fn, "NOT FOUND IN ALL FRAMES", self.all_frames.keys())
            #else:
            #   print("OBS FNMISSING:", obs_fn, self.time_sync_data[key].keys())
            fimg_tn = cv2.resize(fimg,(tw,th))
            main_frame[y1:y2,x1:x2] = fimg_tn
         cv2.imshow('pepe', main_frame)
         cv2.waitKey(30)
         mc += 1   

   def remote_reducer(self, event_id):
      # this will reduce all files for this event 
      # per the latest calibs and standards
      # works with SD or HD files or both if both files exist 
      
      """ steps are:
      Main Group 1 steps
      1. identify video files for this event (they should be mp4 files in the event dir)
      2. download the calib files for each observation
      3. scan frames for motion contours and save in all_frames dict
      4. detect objects and save in the red_data dict as objects
      5. Have user determine ROI for each obs file
      6. save the red_data dict as a json file in the event dir
      7. Loop over the crop images and let the user override the x,y,w,h for each frame
      
      
      """
      
      
      cv2.namedWindow('pepe')
      cv2.resizeWindow("pepe", self.win_x, self.win_y)

      # setup vars and dates and get all files for this event
      date = self.event_id_to_date(event_id)
      self.set_dates(date)
      event_dir = self.local_event_dir + "/" + self.year + "/" + self.month + "/" + self.day  + "/" + event_id + "/"
      all_files = os.listdir(event_dir )
      
      all_frame_data_file = event_dir + event_id + "_ALL_FRAME_DATA.json"
      remote_reduce_file = event_dir + event_id + "_REMOTE_REDUCE.json"
      if os.path.exists(remote_reduce_file):
         self.red_data = load_json_file(remote_reduce_file)
      else:
         self.red_data = {}


      self.all_frames = {}
      self.mp4_files = []
      self.bad_mp4_files = []
      for hdf in all_files:
         if "mp4" not in hdf:
            continue
         if hdf not in self.red_data:
            self.red_data[hdf] = {}
         # not a huge deal, but we don't need to do this, just check if the file is ok?
         # we open the frames again in the next loop
         oframes = load_frames_simple(event_dir + hdf)

         if len(oframes) > 1:
            self.all_frames[hdf] = oframes
            self.mp4_files.append(hdf)
         else:
            self.bad_mp4_files.append(hdf)

      all_frame_data_file = event_dir + event_id + "_ALL_FRAME_DATA.json"


      if os.path.exists(all_frame_data_file):
         self.all_frame_data = load_json_file(all_frame_data_file)
         #self.time_sync_frame_data()
      else:
         self.all_frame_data = {}


      # loop over all files
      for hdf in self.mp4_files:
         # skip if non movie file
         if "mp4" not in hdf:
            continue
         print("WORKING ON:", hdf)

         self.all_frame_data[hdf] = {}
         # parse file name for station id and datetime, 
         station_id = hdf.split("_")[0]
         (f_datetime, cam_id, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(hdf.replace(station_id + "_" , ""))
         trim_num = get_trim_num(hdf)
         extra_sec = int(trim_num) / 25
         start_trim_frame_time = f_datetime + datetime.timedelta(0,extra_sec)

         # load frames
         oframes = load_frames_simple(event_dir + hdf)
         frames = []
         if len(oframes) == 0:
            print("NO FRAMES")
            continue 

         # resize frames to 1080p
         for frame in oframes:
            if oframes[0].shape[0] != 1080:
               self.red_data[hdf]['resolution'] = "SD"
               frame = cv2.resize(frame, (1920,1080))
            else:
               self.red_data[hdf]['resolution'] = "HD"
            frames.append(frame)
    
         # make median frame of 1st 3
         med_frame = cv2.convertScaleAbs(np.median(np.array(frames[0:3]), axis=0))

         # remove the station id from the filename
         hdfn = hdf.replace(station_id + "_", "")

         # get / update remote cal params
         cal_params, remote_json_conf,mask_img = self.get_remote_cal_params(station_id, cam_id, hdfn, f_datetime,med_frame)
         cp = {}
         print(cal_params)
         cp['center_az'] = cal_params['center_az']
         cp['center_el'] = cal_params['center_el']
         cp['position_angle'] = cal_params['position_angle']
         cp['pixscale'] = cal_params['pixscale']
         cp['x_poly'] = cal_params['x_poly']
         cp['y_poly'] = cal_params['y_poly']
         cp['y_poly_fwd'] = cal_params['y_poly_fwd']
         cp['x_poly_fwd'] = cal_params['x_poly_fwd']
         
         self.red_data[hdf]['cal_params'] = cp
         self.red_data[hdf]['location'] = remote_json_conf['site']['device_lat'], remote_json_conf['site']['device_lng'], remote_json_conf['site']['device_alt']
         
         # make show image for cal params
         show_img = med_frame.copy()
         #if False:
         print("CAL PARAMS:", cal_params)
         if cal_params is not None:
            for star in cal_params['cat_image_stars']:
               name,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,star_x,star_y,res_px,flux = star
               cv2.circle(show_img, (int(star_x),int(star_y)), int(5), (0,255,0),1)
               cv2.circle(show_img, (int(new_cat_x),int(new_cat_y)), int(5), (128,255,0),1)
 
         # make auto mask of bright spots
         bw_med =  cv2.cvtColor(med_frame, cv2.COLOR_BGR2GRAY)
         min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(bw_med)
         thresh_val = int(max_val * .8)

         avg_val = np.mean(bw_med)
         if thresh_val < avg_val * 1.5:
            thresh_val = avg_val * 1.5

         _, mask_image = cv2.threshold(bw_med, thresh_val, 255, cv2.THRESH_BINARY)
         mask_image = cv2.dilate(mask_image, None, iterations=8)
         cnts = get_contours_in_image(mask_image)
         for x,y,w,h in cnts:
            mask_image[y:y+h,x:x+w] = 255
         mask_image_bgr = cv2.cvtColor(mask_image, cv2.COLOR_GRAY2BGR)
         

         # loop over frames, subtract mask and get contours for 
         # what remains
         

         fc = 0
         objects = {}
         thresh_vals = []
         print("looping frames for ", hdf)
         # combine 2 images to one 
         mask_img = cv2.add(mask_img, mask_image_bgr)
         
         objects, stack_img = self.detect_objects(frames, med_frame, mask_img, start_trim_frame_time, hdf)
         marked_stack = stack_img.copy()
         for obj_id in objects:
            objects[obj_id] = analyze_object(objects[obj_id], 1)
            min_x = int(np.min(objects[obj_id]['oxs']) - 5)
            min_y = int(np.min(objects[obj_id]['oys']) - 5)
            max_x = int(np.max(objects[obj_id]['oxs']) + 5)
            max_y = int(np.max(objects[obj_id]['oys']) + 5)
            #print(objects[obj_id]['report'])
            cv2.putText(marked_stack, str(obj_id) + " " + str(objects[obj_id]['report']['meteor'] ),  (min_x,min_y), cv2.FONT_HERSHEY_SIMPLEX, .6, (255,255,255), 1)
            cv2.rectangle(marked_stack, (min_x, min_y), (max_x, max_y), (255,255,255), 1)
            
            #print(obj_id, objects[obj_id], objects[obj_id]['report'])
         
         self.red_data[hdf]['objects'] = objects
         if "manual_roi" not in self.red_data[hdf]:
            x1, y1, x2, y2 = self.select_roi(marked_stack)   
            self.red_data[hdf]['manual_roi'] = [x1,y1,x2,y2]
         else:
            x1, y1, x2, y2 = self.red_data[hdf]['manual_roi']
            
         self.red_data[hdf]['manual_clicks'] = self.pick_xy_crop(hdf, x1, y1, x2, y2, oframes)
         print("MANUAL FRAME DATA:", self.red_data[hdf]['manual_clicks'])

         # refine 
         #channel_imgs = self.review_frame_data(hdf)
         #self.track_with_channels(hdf, mask_image, med_frame, start_trim_frame_time, channel_imgs, frames)

         #channel_imgs2 = self.review_frame_data(hdf)
         #self.track_with_channels(hdf, mask_image, med_frame, start_trim_frame_time, channel_imgs, frames)

         #channel_imgs3 = self.review_frame_data(hdf)
         #print("Finished one file?", hdf)
         #cv2.waitKey(30)         
      print (event_dir + event_id + "_ALL_FRAME_DATA.json")
      print (event_dir + event_id + "_REMOTE_REDUCE.json")
      save_json_file(event_dir + event_id + "_ALL_FRAME_DATA.json", self.all_frame_data)
      save_json_file(event_dir + event_id + "_REMOTE_REDUCE.json", self.red_data)


   def mouse_callback(self, event, x, y, flags, param):
      if event == cv2.EVENT_LBUTTONDOWN:
         # Save the mouse click coordinates to the dictionary
         self.manual_clicks[self.fn] = [self.fn, x,y]
         param['clicks'].append((self.fn, x, y))
         tframe = self.frame.copy()
         cv2.circle(tframe, (x, y), 5, (0, 255, 255), 1)
         cv2.imshow('marked', tframe)
         

   def pick_xy_crop(self, hdf, x1, y1, x2, y2, frames):
      print("PICK XY CROP")
      crop_frames = []
      for frame in frames:
         frame = cv2.resize(frame, (1920, 1080))
         crop_frame = frame[y1:y2, x1:x2]
         crop_frames.append(crop_frame)
         #cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), 1)
         #cv2.imshow('pepe', frame)
         #cv2.waitKey(30)

      # Dictionary to store click positions
      if "manual_clicks" in self.red_data[hdf]:
         self.manual_clicks = self.red_data[hdf]['manual_clicks'] 
      else:
         self.manual_clicks = {}
      print("MANUAL CLICKS:", self.manual_clicks)
      manual_frame_data = {'clicks': []}   
      input("XXX")

      # Set up mouse callback with the manual_frame_data dictionary
      cv2.namedWindow('marked')
      # resize window to 2x the crop_frame size
      width = crop_frames[0].shape[1] * 2
      height = crop_frames[0].shape[0] * 2
      cv2.setMouseCallback('marked', self.mouse_callback, manual_frame_data)

      go = True
      i = 0
      med_frame = np.median(np.array(crop_frames), axis=0)
      med_frame = cv2.convertScaleAbs(med_frame)   
      while go:
         self.fn = i
         cv2.resizeWindow('marked', width, height)
         frame = crop_frames[i].copy()
         sub = cv2.subtract(frame, med_frame) 
         # double the frame size 200% its original size
         nw = int(frame.shape[1] * 2)
         nh = int(frame.shape[0] * 2)
         frame = cv2.resize(frame, (nw, nh)) 
         marked_frame = cv2.resize(frame, (nw, nh)) 
         self.frame = frame.copy()
         sub = cv2.resize(sub, (nw, nh)) 
         max_px = np.max(sub)
         thresh = max_px * 0.6
         if thresh < 10:
            thresh = 10
         _, thresh_img = cv2.threshold(sub, thresh, 255, cv2.THRESH_BINARY)
         cnts = get_contours_in_image(thresh_img)
         for x, y, w, h in cnts:
            cv2.rectangle(marked_frame, (int(x), int(y)), (int(x+w), int(y+h)), (255, 255, 255), 1)

         if i in self.manual_clicks:
            mf,mx,my = self.manual_clicks[i]
            cv2.circle(marked_frame, (mx, my), 5, (0, 69, 255), 0)
         elif str(i) in self.manual_clicks:
            mf,mx,my = self.manual_clicks[str(i)]
            cv2.circle(marked_frame, (mx, my), 5, (0, 69, 255), 0)
         #cv2.imshow('pepe', frame)
         #cv2.imshow('sub', sub)
         cv2.imshow('marked', marked_frame)
         key = cv2.waitKey(0)
         # 27 is escape
         if key == 27:
            go = False
         # 32 is space
         elif key == 32:
            i = i + 1 
         # a is previous frame
         elif key == ord('a'):
            i = i - 1
         # f is next frame
         elif key == ord('f'):
            i = i + 1
         # Reset to first frame if we go beyond the last frame
         if i >= len(crop_frames):
            i = 0

         # Print or process the saved click coordinates
         print("Clicked coordinates:", manual_frame_data['clicks'])
      #return manual_frame_data['clicks']
      return self.manual_clicks




   def pick_xy_crop_old(self, hdf, x1, y1, x2, y2, frames):
      print("PICK XY CROP")
      crop_frames = []
      for frame in frames:
         frame = cv2.resize(frame, (1920,1080))
         crop_frame = frame[y1:y2,x1:x2]
         crop_frames.append(crop_frame)
         cv2.rectangle(frame, (x1, y1), (x2, y2), (0,255,255), 1)
         cv2.imshow('pepe', frame)
         cv2.waitKey(30)
      manual_frame_data = {}
      go = True
      i = 0
      med_frame = np.median(np.array(crop_frames), axis=0)
      med_frame = cv2.convertScaleAbs(med_frame)   
      while go is True:
         frame = crop_frames[i].copy()
         sub = cv2.subtract(frame, med_frame) 
         # double the frame size 200% its original size
         nw = int(frame.shape[1] * 2)
         nh = int(frame.shape[0] * 2)
         frame = cv2.resize(frame, (nw,nh)) 
         marked_frame = cv2.resize(frame, (nw,nh)) 
         sub = cv2.resize(sub, (nw,nh)) 
         max_px = np.max(sub)
         thresh = max_px * .6
         if thresh < 10:
            thresh = 10
         _, thresh_img = cv2.threshold(sub, thresh, 255, cv2.THRESH_BINARY)
         cnts = get_contours_in_image(thresh_img)
         for x,y,w,h in cnts:
            cv2.rectangle(marked_frame, (int(x), int(y)), (int(x+w), int(y+h)), (255,255,255), 1)
          
         cv2.imshow('pepe', frame)
         cv2.imshow('sub', sub)
         cv2.imshow('marked', marked_frame)
         key = cv2.waitKey(0)
         # 27 is escape
         if key == 27:
            go = False
         # 32 is space
         if key == 32:
            i = i + 1 
         # a is previous frame
         if key == ord('a'):
            i = i - 1
         # f is next frame
         if key == ord('f'):
            i = i + 1
         # if the mouse is clicked save the x,y point 
         if i >= len(crop_frames):
            i = 0

   def select_roi(self, image):
      # Initialize variables
      roi = None
      dragging = False
      ix, iy = -1, -1
      img_copy = image.copy()
      confirmed = False

      def draw_rectangle(event, x, y, flags, param):
         nonlocal ix, iy, dragging, roi, img_copy
         if event == cv2.EVENT_LBUTTONDOWN:
            dragging = True
            ix, iy = x, y
            img_copy = image.copy()  # Reset the image on every new selection
         elif event == cv2.EVENT_MOUSEMOVE:
            if dragging:
               img_copy = image.copy()
               cv2.rectangle(img_copy, (ix, iy), (x, y), (0, 255, 0), 2)
               cv2.imshow('image', img_copy)
         elif event == cv2.EVENT_LBUTTONUP:
            dragging = False
            roi = (ix, iy, x, y)
            cv2.rectangle(img_copy, (ix, iy), (x, y), (0, 255, 0), 2)
            cv2.imshow('image', img_copy)

      def confirm_selection():
         nonlocal confirmed
         while True:
            print("Press 'y' to confirm selection or 'n' to restart.")
            key = cv2.waitKey(0)
            if key == ord('y'):
               confirmed = True
               break
            elif key == ord('n'):
               confirmed = False
               roi = None
               img_copy = image.copy()
               cv2.imshow('image', img_copy)
               break

      # Display the image and set up the mouse callback
      cv2.putText(img_copy, 'Click-drag-release to select meteor area, then press "y" to confirm or "n" to restart.', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
      cv2.imshow('image', img_copy)
      cv2.setMouseCallback('image', draw_rectangle)

      while True:
         cv2.waitKey(1)
         if roi is not None:
            confirm_selection()
            if confirmed:
               break

      cv2.destroyAllWindows()

      if roi:
         x1, y1, x2, y2 = roi
         x1, x2 = sorted([x1, x2])
         y1, y2 = sorted([y1, y2])
         return x1, y1, x2, y2
      else:
         return None





   def detect_objects(self, frames, med_frame, mask_img, start_trim_frame_time, hdf):
      objects = {}
      fc = 0
      stack_img = None
      if True:
         for frame in frames:
            if stack_img is None:
               stack_img = frame
            stack_img = np.maximum(frame, stack_img)
            # subtract dynamic mask ?
            frame = cv2.subtract(frame, mask_img)
            extra_sec = fc / 25
            frame_time = start_trim_frame_time + datetime.timedelta(0,extra_sec)
            frame_time_str = frame_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            sub = cv2.subtract(frame, med_frame)

            bw_sub =  cv2.cvtColor(sub, cv2.COLOR_BGR2GRAY)
            #bw_sub = cv2.subtract(bw_sub, mask_img)
            min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(bw_sub)
            avg_val = np.mean(bw_sub)
            thresh_val = int(max_val * .6)

            thresh_val = self.find_best_thresh(bw_sub)

            if thresh_val < 50:
               thresh_val = 50
            if thresh_val < avg_val:
               thresh_val = avg_val * 1.5
            _, thresh_image = cv2.threshold(bw_sub, thresh_val, 255, cv2.THRESH_BINARY)

            cnts = get_contours_in_image(thresh_image)
            self.all_frame_data[hdf][fc] = {}
            self.all_frame_data[hdf][fc]['cnts'] = []
            self.all_frame_data[hdf][fc]['frame_time'] = frame_time_str
            #input("Looping cnts")
            for x,y,w,h in cnts:
               mx = int(x + (w / 2))
               my = int(y + (h / 2))
               obj_id, objects = self.get_object(objects, fc, x,y,w,h)

               cv2.rectangle(thresh_image, (int(mx-25), int(my-25)), (int(mx+25) , int(my+25) ), (255, 255, 255), 2)
               cv2.putText(thresh_image, str(obj_id),  (mx-30,my-30), cv2.FONT_HERSHEY_SIMPLEX, .6, (255,255,255), 1)
               intensity = int(np.sum(bw_sub[y:y+h,x:x+w]))

               self.all_frame_data[hdf][fc]['cnts'].append((obj_id,int(x),int(y),int(w),int(h),int(intensity)))


            #cv2.imshow('pepe', thresh_image)
            #cv2.waitKey(30)
            fc += 1 
      return(objects, stack_img)

   def auto_mask(self, med_frame):
      # make auto mask of bright spots
      bw_med =  cv2.cvtColor(med_frame, cv2.COLOR_BGR2GRAY)
      min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(bw_med)
      thresh_val = int(max_val * .6)

      avg_val = np.mean(bw_med)
      if thresh_val < avg_val * 2:
         thresh_val = avg_val * 2 

      _, mask_image = cv2.threshold(bw_med, thresh_val, 255, cv2.THRESH_BINARY)
      mask_image = cv2.dilate(mask_image, None, iterations=8)
      cnts = get_contours_in_image(mask_image)
      for x,y,w,h in cnts:
         if w < 20 and h < 20:
            print("AMASK:", x,y,w,h)
            mask_image[y:y+h,x:x+w] = 255
      mask_image_bgr = cv2.cvtColor(mask_image, cv2.COLOR_GRAY2BGR)
      mask_image = cv2.resize(mask_image_bgr,(1920,1080))
      med_frame= cv2.resize(mask_image_bgr,(1920,1080))

      return(mask_image_bgr)

   def find_best_thresh(self, bw_sub):

      min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(bw_sub)
      avg_val = np.mean(bw_sub)
      thresh_val = max_val * .6
      go = True
      while go is True:
         thresh_val = thresh_val + 2 
         _, thresh_image = cv2.threshold(bw_sub, thresh_val, 255, cv2.THRESH_BINARY)
         cnts = get_contours_in_image(thresh_image)
         #print("THRESH", len(cnts), thresh_val)
         if len(cnts) < 3:
            go = False
      return(thresh_val)


   def track_with_channels(self, hdf, mask_image, med_frame, start_trim_frame_time, channel_imgs, frames):
      fc = 0
      objects = {}
      if True:
         for frame in frames:
            for cmask in channel_imgs:
               frame = cv2.subtract(frame, cmask)

            extra_sec = fc / 25
            frame_time = start_trim_frame_time + datetime.timedelta(0,extra_sec)
            frame_time_str = frame_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            sub = cv2.subtract(frame, med_frame)

            bw_sub =  cv2.cvtColor(sub, cv2.COLOR_BGR2GRAY)
            bw_sub = cv2.subtract(bw_sub, mask_image)
            min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(bw_sub)
            avg_val = np.mean(bw_sub)
            thresh_val = int(max_val * .6)
            if thresh_val < 50:
               thresh_val = 50
            if thresh_val < avg_val:
               thresh_val = avg_val * 1.5
            _, thresh_image = cv2.threshold(bw_sub, thresh_val, 255, cv2.THRESH_BINARY)

            cnts = get_contours_in_image(thresh_image)
            self.all_frame_data[hdf][fc] = {}
            self.all_frame_data[hdf][fc]['cnts'] = []
            self.all_frame_data[hdf][fc]['frame_time'] = frame_time_str
            for x,y,w,h in cnts:
               mx = int(x + (w / 2))
               my = int(y + (h / 2))
               obj_id, objects = self.get_object(objects, fc, x,y,w,h)

               cv2.rectangle(thresh_image, (int(mx-25), int(my-25)), (int(mx+25) , int(my+25) ), (255, 255, 255), 2)
               cv2.putText(thresh_image, str(obj_id),  (mx-30,my-30), cv2.FONT_HERSHEY_SIMPLEX, .6, (255,255,255), 1)
               intensity = np.sum(bw_sub[y:y+h,x:x+w])

               self.all_frame_data[hdf][fc]['cnts'].append((obj_id,int(x),int(y),int(w),int(h),int(intensity)))

            #cv2.imshow('pepe', frame)
            #cv2.putText(sub, frame_time_str,  (20,1060), cv2.FONT_HERSHEY_SIMPLEX, .6, (0,255,0), 1)

            cv2.imshow('pepe', thresh_image)
            cv2.waitKey(30)
            fc += 1

   def review_frame_data(self, hdf ):

      show_img = np.zeros((1080,1920,3),dtype=np.uint8)

      obj_xs = {}
      obj_ys = {}

      for xc in self.all_frame_data[hdf]:
         if len(self.all_frame_data[hdf][xc]['cnts']) > 1:
            objs = {}
            new_cnts = []
            for obj_id,x,y,w,h,i in self.all_frame_data[hdf][xc]['cnts']:
               if obj_id not in objs:
                  objs[obj_id] = {}
                  objs[obj_id]['xs'] = []
                  objs[obj_id]['ys'] = []
                  objs[obj_id]['ws'] = []
                  objs[obj_id]['hs'] = []
                  objs[obj_id]['is'] = []
               objs[obj_id]['xs'].append(x)
               objs[obj_id]['ys'].append(y)
               objs[obj_id]['ws'].append(w)
               objs[obj_id]['hs'].append(h)
               objs[obj_id]['is'].append(i)
            for obj_id in objs:
               mx = np.median(objs[obj_id]['xs'])
               my = np.median(objs[obj_id]['ys'])
               mw = np.median(objs[obj_id]['ws'])
               mh = np.median(objs[obj_id]['hs'])
               mi = np.median(objs[obj_id]['is'])
               new_cnts.append((obj_id, mx, my, mw, mh, mi))
            self.all_frame_data[hdf][xc]['cnts'] = new_cnts 

         # there should be just 1 cnt per obj now
         for obj_id,x,y,w,h,i in self.all_frame_data[hdf][xc]['cnts']:
            if obj_id not in obj_xs:
               obj_xs[obj_id] = []
            if obj_id not in obj_ys:
               obj_ys[obj_id] = []

            cv2.rectangle(show_img, (int(x), int(y)), (int(x+w) , int(y+h) ), (255, 255, 255), 1)
            cv2.imshow('pepe', show_img)
            cv2.waitKey(30)
            cx = int(x + (w/2))
            cy = int(y + (h/2))
            obj_xs[obj_id].append(cx)
            obj_ys[obj_id].append(cy)
            cv2.circle(show_img, (int(cx),int(cy)), int(5), (0,0,255),2)
      channel_imgs = []
      channel_img = None
      #matplotlib.use('TkAgg')

      for obj_id in obj_xs:
         channel_img = self.make_channel(obj_xs[obj_id],obj_ys[obj_id], 1920,1080, channel_img)

      channel_img = self.invert_image(channel_img)
      channel_img = cv2.cvtColor(channel_img,cv2.COLOR_GRAY2BGR)

      channel_imgs = [channel_img]
      return(channel_imgs)
            


   def get_object(self, objects, fn,mx,my,mw,mh,oint=0):
      if True:
         if len(objects.keys()) == 0:
            # make new there are none!
            objects[1] = {}
            objects[1]['ofns'] = [fn]
            objects[1]['oxs'] = [mx]
            objects[1]['oys'] = [my]
            objects[1]['ows'] = [mw]
            objects[1]['ohs'] = [mh]
            objects[1]['oint'] = [oint]
            #print("Make 1st obj")
            return(1, objects)

         # check existing
         cmx = mx + (mw/2)
         cmy = my + (mh/2)
         for oid in objects:
            #for cnt in objects[oid]['cnts']:
            for j in range(0, len(objects[oid]['oxs'])):
               ofn = objects[oid]['ofns'][j]
               ox = objects[oid]['oxs'][j]
               oy = objects[oid]['oys'][j]
               ow = objects[oid]['ows'][j]
               oh = objects[oid]['ohs'][j]
               oint = objects[oid]['oint'][j]
               #fn,ox,oy,ow,oh,oint = cnt
               cox = ox + (ow/2)
               coy = oy + (oh/2)
               dist = calc_dist((cmx,cmy), (cox,coy))
               fn_diff = ofn - fn
               if dist < 250:
                  objects[oid]['ofns'].append(fn)
                  objects[oid]['oxs'].append(mx)
                  objects[oid]['oys'].append(my)
                  objects[oid]['ows'].append(mw)
                  objects[oid]['ohs'].append(mh)
                  objects[oid]['oint'].append(oint)
                  return(oid, objects)
         # none found so far. make new
         oid = max(objects.keys()) + 1
         objects[oid] = {}
         objects[oid]['ofns'] = [fn]
         objects[oid]['oxs'] = [mx]
         objects[oid]['oys'] = [my]
         objects[oid]['ows'] = [mw]
         objects[oid]['ohs'] = [mh]
         objects[oid]['oint'] = [oint]
         
         
         return(oid, objects)

   def setup_cal_db(self):
      # connect to the main cal db
      db_file = self.db_dir + "ALLSKYNETWORK_CALIBS.db"
      if os.path.exists(db_file) is False:
         print("DB FILE NOT FOUND.", db_file)
         return ()
      self.cal_con = sqlite3.connect(db_file)
      self.cal_con.row_factory = sqlite3.Row
      self.cal_cur = self.cal_con.cursor()


   def remote_cal_one(self, full_file):

      # load up the med frame
      if "mp4" in full_file:
         frames = load_frames_simple(full_file)
         med_frame = cv2.convertScaleAbs(np.median(np.array(frames[0:10]), axis=0))
         med_file = full_file.replace(".mp4", "-med.jpg")
         med_frame = cv2.resize(med_frame, (1920,1080))
         cv2.imwrite(med_file, med_frame)

         full_file = med_file

      # connect to the main cal db
      db_file = self.db_dir + "ALLSKYNETWORK_CALIBS.db"
      print("DB FILE IS:", db_file)
      if os.path.exists(db_file) is False:
         print("DB FILE NOT FOUND.", db_file)
         return ()
      self.cal_con = sqlite3.connect(db_file)
      self.cal_con.row_factory = sqlite3.Row
      self.cal_cur = self.cal_con.cursor()

      if "\\" in full_file:
         full_file = full_file.replace("\\", "/")
    
      input_file = full_file.split("/")[-1]
      station_id = input_file.split("_")[0]

      (f_datetime, cam_id, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(input_file.replace(station_id + "_" , ""))

      # find / load the mask
      self.set_dates(input_file.replace(station_id + "_", "")[0:10])
      cloud_mask_file = "/mnt/archive.allsky.tv/" + station_id + "/CAL/MASKS/" + cam_id + "_mask.png"
      local_mask_dir = "/mnt/f/EVENTS/STATIONS/" + station_id + "/MASKS/" 
      local_mask_file = local_mask_dir + cam_id + "_mask.png"
      if os.path.exists(local_mask_dir) is False:
         os.makedirs(local_mask_dir)
      if os.path.exists(local_mask_file) is False:
         cmd = "cp " + cloud_mask_file + " " + local_mask_file
         os.system(cmd)

      if os.path.exists(local_mask_file) is True:
         mask_img = cv2.imread(local_mask_file)
         mask_img = cv2.resize(mask_img, (1920,1080))
      else:
         mask_img = np.zeros((1920,1080,3),dtype=np.uint8)

      # subtract mask from star image
      img = cv2.imread(full_file)
      img = cv2.resize(img, (1920,1080))
      img = cv2.subtract(img, mask_img)

      # get star points
      star_points,stars_image = get_star_points(input_file, img, {}, station_id, cam_id, {})
      star_points = sorted(star_points, key=lambda x: (x[2]), reverse=True)

      # get best defalt cal params
      cal_params,json_conf = self.get_remote_cal_params(station_id, cam_id, input_file.replace(station_id + "_", ""), f_datetime,img, star_points)

      cal_params['cat_image_stars'], cal_params['user_stars'] = get_image_stars_with_catalog(input_file.replace(station_id + "_", ""), cal_params, img)


      if cal_params['total_res_px'] >= 999:
         print("REMOTE CAL FAILED!", len(cal_params['user_stars']), len(cal_params['cat_image_stars']), cal_params['total_res_px'] )
         cv2.imshow('pepe', img)
         cv2.waitKey(30)
         exit()

      cal_params['user_stars'] = star_points
     
      if True:
         show_img = stars_image.copy()
         for star in cal_params['cat_image_stars']:
            name,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,star_x,star_y,res_px,flux = star
            cv2.circle(show_img, (int(star_x),int(star_y)), int(5), (0,255,0),2)
            cv2.rectangle(show_img, (int(new_cat_x-10), int(new_cat_y-10)), (int(new_cat_x+10) , int(new_cat_y+10) ), (255, 255, 255), 1)
            print("STAR FROM CAT STARS", star)
            cv2.imshow('pepe', show_img)
            cv2.waitKey(30)

      if cal_params is None:
         text1 = "NO CAL PARAMS FOUND!" 
         return()
      else:
         text1 = str(cal_params['center_az'])[0:4] + " / " \
            + str(cal_params['center_el'])[0:4] + " ::: " \
            + str(cal_params['ra_center'])[0:4] + " / " \
            + str(cal_params['dec_center'])[0:4] + " ::: " \
            + str(cal_params['position_angle'])[0:4] + " ::: " \
            + str(cal_params['pixscale'])[0:4] + " ::: " 

      # draw img stars on image
      if len(img.shape) == 2:
         img =  cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
      show_img = img.copy()

      if True:
         # draw cat_image_stars on image
         for star in cal_params['cat_image_stars']:
            name,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,star_x,star_y,res_px,flux = star
            cv2.circle(show_img, (int(star_x),int(star_y)), int(5), (0,255,0),2)
            cv2.rectangle(show_img, (int(new_cat_x-10), int(new_cat_y-10)), (int(new_cat_x+10) , int(new_cat_y+10) ), (255, 255, 255), 1)
            cv2.imshow('pepe', show_img)
            cv2.waitKey(30)

      for row in star_points[0:50]:
         mx, my, inten = row
         cv2.circle(show_img, (int(mx),int(my)), int(5), (128,128,128),2)
         cv2.imshow('pepe', stars_image)
         cv2.waitKey(30)
         print(row)

      extra_text = "Hello there..." 
      
      ifile = input_file.replace(station_id + "_", "")
      new_cp = minimize_fov(ifile, cal_params, ifile,img.copy(),json_conf, False,cal_params, extra_text, show=1)
      new_cp = minimize_fov(ifile, new_cp, ifile,img.copy(),json_conf, False,cal_params, extra_text, show=1)
      cal_params = new_cp

      if True:
         show_img = stars_image.copy()
         for star in cal_params['cat_image_stars']:
            name,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,star_x,star_y,res_px,flux = star

            new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(new_cat_x,new_cat_y,ifile,cal_params,json_conf)
            img_new_cat_x, img_new_cat_y = get_xy_for_ra_dec(cal_params, img_ra, img_dec)
            match_dist = angularSeparation(ra,dec,img_ra,img_dec)
            #cat_image_stars.append((name_ascii,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,x,y,res_px,flux))
            res_px = calc_dist((star_x,star_y), (new_cat_x,new_cat_y))
            print("RES FINAL:", res_px)

            cv2.circle(show_img, (int(star_x),int(star_y)), int(5), (0,255,0),2)
            cv2.rectangle(show_img, (int(new_cat_x-10), int(new_cat_y-10)), (int(new_cat_x+10) , int(new_cat_y+10) ), (255, 255, 255), 1)
            cv2.imshow('pepe', show_img)
            cv2.waitKey(30)


      cv2.putText(img, str(text1),  (int(20),int(20)), cv2.FONT_HERSHEY_SIMPLEX, .6, (255,255,255), 1)
      cv2.imshow('pepe', show_img)
      cv2.waitKey(30)


   def insert_last_best_cal(self, cp ):
      if "user_stars" not in cp:
         cp['user_stars'] = [] 
      ivals = [ cp['station_id'], cp['camera_id'], cp['cal_fn'], cp['cal_timestamp'], cp['center_az'], cp['center_el'], cp['ra_center'], cp['dec_center'], cp['position_angle'], cp['pixscale'], json.dumps(cp['user_stars']), json.dumps(cp['cat_image_stars']), json.dumps(cp['x_poly']), json.dumps(cp['y_poly']), json.dumps(cp['x_poly_fwd']), json.dumps(cp['y_poly_fwd']), cp['total_res_px'] ]
      isql = """INSERT OR REPLACE INTO last_best_cal
                (station_id, camera_id, calib_fn, cal_timestamp, az, el, ra, dec, position_angle, pixel_scale, 
                user_stars, cat_image_stars, x_poly, y_poly,x_poly_fwd, y_poly_fwd, res_px) 
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
             """
      #print(isql)
      #print(ivals)
      self.cal_cur.execute(isql, ivals)
      self.cal_con.commit()


   def get_remote_cal(self, station_id, cam_id, filename):
      # get the remote multi-poly file for this station if the local cached one is 
      # too old. 
      if station_id in self.rurls:
         remote_url = self.rurls[station_id]
      else:
         remote_url = None

      cloud_cal_dir = "/mnt/archive.allsky.tv/" + station_id + "/CAL/"
      cloud_cal_url = "https://archive.allsky.tv/" + station_id + "/CAL/"
      local_cal_dir = "/mnt/f/EVENTS/STATIONS/" + station_id + "/CAL/"
      local_cal_file = local_cal_dir + "multi_poly-" + station_id + "-" + cam_id + ".info"
      remote_cal_file = remote_url + "/cal/" + "multi_poly-" + station_id + "-" + cam_id + ".info"

      local_cal_file = local_cal_dir + station_id + "_" + cam_id + "_LENS_MODEL.json"
      remote_cal_file = cloud_cal_url + station_id + "_" + cam_id + "_LENS_MODEL.json"

      # check if the multi_poly exists if yes use it. else revert LENS

      local_conf_file = local_cal_dir + "as6.json"
      local_range_file = local_cal_dir + station_id + "_cal_range.json"
      if os.path.exists(local_range_file) is True:
         cal_range = load_json_file(local_range_file)
      else:
         cal_range = []
      if os.path.exists(local_cal_dir) is False:
         os.makedirs(local_cal_dir)
      if os.path.exists(local_conf_file) is True:
         print(local_conf_file)
         try:
            remote_json_conf = load_json_file(local_conf_file)
         except:
            os.system("rm " + remote_json_conf)
      else:
         print("NO LOCAL CAL CONF FILE EXISTS FETCH IT!", local_conf_file)
         cmd = "cp -r " + cloud_cal_dir + " " + local_cal_dir
         cmd = "rsync -auv --exclude *STAR_DB.json --exclude plots" + cloud_cal_dir + "* " + local_cal_dir
         os.system(cmd)
         print(cmd)

         exit()

      if os.path.exists(local_cal_file) is True:
         sz, td = get_file_info(local_cal_file)
         if td / 60 / 24 > 1:
            print("LOCAL CACHE FILE IS > 1 day old", td / 60 / 24, local_cal_file)
            cmd = "wget " + remote_cal_file + " -O " + local_cal_file
            print(cmd)
            os.system(cmd)
      else:
         cmd = "wget " + remote_cal_file + " -O " + local_cal_file
         print(cmd)
         os.system(cmd)

      if os.path.exists(local_cal_file) is True:
         print(local_cal_file)
         cp = load_json_file(local_cal_file)
         print("BEFORE RA:", cp['ra_center'], cp['dec_center'])
         print(filename)
         cp = update_center_radec(filename, cp,remote_json_conf)
         print("AFTER UP RA:", cp['ra_center'], cp['dec_center'])
      else:
         print("NO LOCAL CAL CACHE FILE EXISTS FETCH IT!", local_cal_file)
         exit()

      #for k in cp:
      #   if "stars" not in k:
      cp['cal_range'] = cal_range
      return(cp, remote_json_conf)

   def get_remote_cal_params(self, station_id, cam_id, obs_id, cal_date, show_img, star_points = [], daytime=True):
      self.load_stations_file()
      self.setup_cal_db()
      # not sure when / where this is loaded!
      # get the last best cal value if it exists
      self.cal_cur = self.cal_con.cursor()
      
      sql = """
         SELECT station_id, camera_id, calib_fn, cal_datetime, cal_timestamp, az, el, ra, dec, position_angle, pixel_scale, user_stars, cat_image_stars, x_poly, y_poly,x_poly_fwd,y_poly_fwd,res_px,res_deg 
           FROM last_best_cal 
          WHERE station_id = ?
            AND camera_id = ?
      """

      vals = [station_id, cam_id]
      self.cal_cur.execute(sql, vals)
      rows = self.cur.fetchall()

      print("GET REMOTE CAL FROM LAST BEST")
      print(len(rows))

      obs_dt = cal_date 
      cal_timestamp = datetime.datetime.timestamp(obs_dt)

      orig_img = show_img.copy()
      this_range = []
      cloud_cal_dir = "/mnt/archive.allsky.tv/" + station_id + "/CAL/"
      local_cal_dir = "/mnt/f/EVENTS/STATIONS/" + station_id + "/CAL/"
      remote_json_conf_file = local_cal_dir + "as6.json"
      
      local_mask_file = local_cal_dir + station_id + "_" + cam_id + "_mask.png" 
      remote_mask_file = cloud_cal_dir + "MASKS/" + cam_id + "_mask.png"
      if os.path.exists(local_cal_dir) is False: 
         os.path.exists(local_cal_dir)
      print("LOCAL MASK FILE:" + local_mask_file)
      print("REMOTE MASK FILE:" + remote_mask_file)
      if os.path.exists(local_mask_file) is False:
         if os.path.exists(remote_mask_file) is True:
            cmd = "cp " + remote_mask_file + " " + local_mask_file
            os.system(cmd)
      if os.path.exists(local_mask_file) is True:
         mask_img = cv2.imread(local_mask_file)
         mask_img = cv2.resize(mask_img, (1920,1080))
      else:
         mask_img = np.zeros((1080,1920,3),dtype=np.uint8) 
      #print("REMOTE MASK FILE:" + remote_mask_file)   
      #input("MASK FILE:" + local_mask_file)   
      
      # BUG
      #sz, td = get_file_info(remote_json_conf)
      #if td / 60 / 24 > 1:
      #   print("JC IS OLD! GET NEW ONE!")
      #   url = self.rurls[station_id]
      #   print(url + "/)

      print("RJC:", remote_json_conf_file)


      if os.path.isdir(local_cal_dir) is False:
         os.makedirs(local_cal_dir)
      if os.path.exists(remote_json_conf_file) is True:
         remote_json_conf = load_json_file(remote_json_conf_file)
         json_conf = remote_json_conf 
      else:
         # try to copy it?
         cloud_file = cloud_cal_dir + "as6.json"
         cmd = "cp " + cloud_file + " " + remote_json_conf_file
         os.system(cmd)
         remote_json_conf = load_json_file(remote_json_conf_file)
         json_conf = remote_json_conf 

      if os.path.exists(local_cal_dir) is False:
         os.makedirs(local_cal_dir)
      remote_cal_files = os.listdir(cloud_cal_dir) 
      best_res = 99999
      best_calib = None

      for rf in remote_cal_files:
         remote_file = cloud_cal_dir + rf
         local_file = local_cal_dir + rf
         if os.path.exists(local_file) is False and os.path.isdir(remote_file) is True:
            cmd = "cp " + remote_file + " " + local_file
            print(cmd)
            os.system(cmd)
      #print("All files should be sync'd")
      cal_range_file = local_cal_dir + station_id + "_cal_range.json"
      cloud_cal_range_file = cloud_cal_dir + station_id + "_cal_range.json"
      remote_json_conf = load_json_file(remote_json_conf_file)



      # remote json conf should come from the station_dict data not the old as6.json file!
      remote_json_conf['site']['device_lat'] = self.station_dict[station_id]['lat']
      remote_json_conf['site']['device_lng'] = self.station_dict[station_id]['lon']
      remote_json_conf['site']['device_alt'] = self.station_dict[station_id]['alt']

      lens_file = local_cal_dir + station_id + "_" + cam_id + "_LENS_MODEL.json"
      lens_file_old = local_cal_dir + "multi_poly-" + station_id + "-" + cam_id + ".info"
      cloud_lens_file_old = cloud_cal_dir   + "multi_poly-" + station_id + "-" + cam_id + ".info" 
      print("LOCAL OLD LENS FILE", lens_file_old)
      print("CLOUD LENS FILE", cloud_lens_file_old)
      
      if os.path.exists(lens_file) is True: 
         lens_model = load_json_file(lens_file)
      elif os.path.exists(lens_file_old) is True: 
         lens_model = load_json_file(lens_file_old)
      elif os.path.exists(cloud_lens_file_old) is True: 
         cmd = f"cp {cloud_lens_file_old} {lens_file}"
         os.system(cmd)
         lens_model = load_json_file(lens_file)
      else:
         lens_model = {}
         print(lens_file)
         print(lens_file_old)
         print("NO LENS MODEL!")
 
      if os.path.exists(cal_range_file) is False and os.path.exists(cloud_cal_range_file) is True:
         cmd = f"cp {cloud_cal_range_file} {cal_range_file}"
         print(cmd)
         os.system(cmd)

      if os.path.exists(cal_range_file) is True:
         cal_range_data = load_json_file(cal_range_file)
      else:
         print("NO CAL RANGE FOR ", station_id, cam_id, obs_id, cal_range_file)
         cal_range_data = []

      match_range_data = []
      for row in cal_range_data:
         rcam_id, rend_date, rstart_date, az, el, pos, pxs, res = row

         if np.isnan(az) is True:
            #print("NAN SKIP")
            continue
         #else:
         #   print(az, np.isnan(az))

         rcam_id = row[0]
         rend_date = row[1]
         rstart_date = row[2]

         rend_dt = datetime.datetime.strptime(rend_date, "%Y_%m_%d")
         rstart_dt = datetime.datetime.strptime(rstart_date, "%Y_%m_%d")

         if rcam_id == cam_id : #and np.isnan(az) == False:
            elp = abs((cal_date - rend_dt).total_seconds()) / 86400
            match_range_data.append(( cal_date, rend_dt, rstart_dt, elp, az, el, pos, pxs, res))
            #print("CALIB:", cal_date, rend_dt, rstart_dt, elp, az, el, pos, pxs, res)


      for mdata in match_range_data:
         show_img = orig_img.copy()



         rcam_id, best_rend_date, best_rstart_date, elp, best_az, best_el, best_pos, best_pxs, res = mdata

         lens_model['center_az'] = best_az 
         lens_model['center_el'] = best_el
         lens_model['position_angle'] = best_pos 
         lens_model['pixscale'] = best_pxs 
         temp = obs_id.replace(station_id + "_", "") 

         cal_params = update_center_radec(temp,lens_model,remote_json_conf)
         print(json.dumps(cal_params))
         cat_stars, short_bright_stars, cat_image = get_catalog_stars(cal_params)
         #print("RURL", self.rurls[station_id])
         #print("REMOTE:", remote_json_conf['site']['device_lat'], remote_json_conf['site']['device_lng'])
         used = {}
         # if it is day time or cloud don't bother with this
         if daytime is False:
            star_points = find_stars_with_grid(orig_img)
         else:
            star_points = []
         if False :
            for ix,iy,ii in star_points[0:250]:
               cv2.circle(show_img, (int(ix),int(iy)), int(5), (0,255,0),1)
               cv2.imshow('calib', show_img)
               cv2.waitKey(30)

         all_res = []
         cat_image_stars = []
         for star in cat_stars[0:100]:
            (name,mag,ra,dec,new_cat_x,new_cat_y,zp_cat_x,zp_cat_y) = star
            cv2.putText(show_img, str(name),  (int(new_cat_x-25),int(new_cat_y-25)), cv2.FONT_HERSHEY_SIMPLEX, .6, (255,255,255), 1)
            cv2.rectangle(show_img, (int(new_cat_x-25), int(new_cat_y-25)), (int(new_cat_x+25) , int(new_cat_y+25) ), (255, 255, 255), 1)

            # find closest image star! 
            dist_arr = []
            for ix,iy,ii in star_points[0:50]:
               this_dist = calc_dist((ix,iy),(new_cat_x,new_cat_y))
               if this_dist < 20:
                  dist_arr.append((this_dist, star, ii))
            dist_arr = sorted(dist_arr, key=lambda x: x[0], reverse=False)
            if len(dist_arr) > 0:
               closest_star = dist_arr[0][1]
               star_x = closest_star[4]
               star_y = closest_star[5]
               flux = dist_arr[0][2]
               res = dist_arr[0][0]
               all_res.append(res)

               new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(new_cat_x,new_cat_y,obs_id,cal_params,json_conf)
               img_new_cat_x, img_new_cat_y = get_xy_for_ra_dec(cal_params, img_ra, img_dec)
               match_dist = angularSeparation(ra,dec,img_ra,img_dec)
               #cat_image_stars.append((name_ascii,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,x,y,res_px,flux))
               res_px = calc_dist((star_x,star_y), (new_cat_x,new_cat_y))
               cat_image_stars.append((name,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,star_x,star_y,res_px,flux))
            #cv2.imshow('pepe', show_img)
            #cv2.waitKey(30)



         #print("CAT IMAGE STARS:", len(cat_image_stars))
         if len(all_res) > 0:
            avg_res = np.mean(all_res)
         else:
            avg_res = 999
         if avg_res < best_res :
            #print("*** BEST RES BEAT:", best_res, avg_res, cal_params['center_az'], cal_params['center_el'])
            best_res = avg_res
            best_calib = cal_params
            best_calib['cat_image_stars'] = cat_image_stars
            best_calib['total_res_px'] = avg_res 
            #cv2.imshow('calib', show_img)
            #cv2.waitKey(30)

 

      #print("REMOTE JSON CONF:", obs_id, best_calib, remote_json_conf)
      if best_calib is not None:
         best_calib = update_center_radec(obs_id,best_calib,remote_json_conf)

         obs_dt = cal_date #datetime.datetime.strptime(cal_date, "%Y-%m-%d %H:%M:%S.%f")
         cal_timestamp = datetime.datetime.timestamp(obs_dt)
         best_calib['cal_timestamp'] = cal_timestamp
         best_calib['cal_fn'] = obs_id
         best_calib['camera_id'] = cam_id
         best_calib['station_id'] = station_id
         #best_calib['cal_datetime'] = cal_date.strftime("%Y_%m_%d %H:%M:%S.%f")


         self.insert_last_best_cal(best_calib)


      return(best_calib, remote_json_conf, mask_img)




   def merge_obs(self, event_id ):
      event_day = self.event_id_to_date(event_id)
      self.event_id = event_id
      self.set_dates(event_day)

      good_obs_file = self.local_evdir + self.event_id + "/" + self.event_id + "_GOOD_OBS.json"
      good_obs = load_json_file(good_obs_file)
      time_matrix = {}
      for station in good_obs:

         if len(good_obs[station]) > 1:
            print("NEED TO MERGE!", station, len(good_obs[station]), "obs")
            for obs_id in good_obs[station]:
               (f_datetime, cam_id, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(obs_id.replace(station + "_" , ""))
               print(obs_id, good_obs[station][obs_id].keys())
               for i in range(0, len(good_obs[station][obs_id]['fns'])):
                  #print(obs_id, i, good_obs[station][obs_id]['times'][i])
                  time_key = good_obs[station][obs_id]['times'][i]
                  if station not in time_matrix:
                     time_matrix[station] = {}
                  if time_key not in time_matrix[station]:
                     time_matrix[station][time_key] = {}
                     time_matrix[station][time_key]['fns'] = []
                     time_matrix[station][time_key]['azs'] = []
                     time_matrix[station][time_key]['els'] = []
                     time_matrix[station][time_key]['gc_azs'] = []
                     time_matrix[station][time_key]['gc_els'] = []
                     time_matrix[station][time_key]['cam_ids'] = []
                  time_matrix[station][time_key]['fns'].append(good_obs[station][obs_id]['fns'][i])
                  time_matrix[station][time_key]['azs'].append(good_obs[station][obs_id]['azs'][i])
                  time_matrix[station][time_key]['els'].append(good_obs[station][obs_id]['els'][i])
                  #time_matrix[station][time_key]['gc_azs'].append(good_obs[station][obs_id]['gc_azs'][i])
                  #time_matrix[station][time_key]['gc_els'].append(good_obs[station][obs_id]['gc_els'][i])
                  time_matrix[station][time_key]['cam_ids'].append(cam_id)
            #for obs_id in good_obs[station]:
      for station in time_matrix:
         for time_key in time_matrix[station]:
            print(station, time_key, time_matrix[station][time_key] )







   def video_preview_html_js(self, video_urls):
      text_vars = ""
      for url in video_urls:
         if text_vars != "":
            text_vars += ",\n"
         text_vars += """'{:s}'""".format(url)

      js = """
      <div id="videoContainer" style="display:inline-block"></div>
      <b id="output" style="vertical-align:top"></b>
      <script>
      var videoContainer = document.getElementById('videoContainer'),
          output = document.getElementById('output'),
          nextVideo,
          videoObjects =
          [
              document.createElement('video'),
              document.createElement('video')
          ],
          vidSources =
          [
              {:s}
          ],
          nextActiveVideo = Math.floor((Math.random() * vidSources.length));
      
      videoObjects[0].inx = 0; //set index
      videoObjects[1].inx = 1;
      
      initVideoElement(videoObjects[0]);
      initVideoElement(videoObjects[1]);
      
      videoObjects[0].autoplay = true;
      videoObjects[0].src = vidSources[nextActiveVideo];
      videoContainer.appendChild(videoObjects[0]);
      
      videoObjects[1].style.display = 'none';
      videoContainer.appendChild(videoObjects[1]);
      
      function initVideoElement(video)
      {
          video.playsinline = true;
          video.muted = false;
          video.preload = 'auto'; //but do not set autoplay, because it deletes preload
      
          video.onplaying = function(e)
          {
              output.innerHTML = 'Current video source index: ' + nextActiveVideo;
              nextActiveVideo = ++nextActiveVideo % vidSources.length;
              if(this.inx == 0)
                  nextVideo = videoObjects[1];
              else
                  nextVideo = videoObjects[0];
              nextVideo.src = vidSources[nextActiveVideo];
              nextVideo.pause();
          };
      
          video.onended = function(e)
          {
              this.style.display = 'none';
              nextVideo.style.display = 'block';
              nextVideo.play();
          };
      }
      </script> 
      """.format(text_vars)
      
      return(js)      

   def slideshow(self, event_day):
      self.set_dates(event_day)
      print(self.local_evdir)
      sdirs = os.listdir(self.local_evdir)
      image_list = """      
         <!-- EVENT IMAGES LIST -->
         <div class="slideshow-container">
      """

      dots = """
         <div style="text-align:center">
      """
      dc = 1 

#<!-- The dots/circles -->
#<div style="text-align:center">

      for evd in sdirs:
         if os.path.exists(self.local_evdir + evd + "/" + evd + "_REVIEW.jpg") is True: 
            print (self.local_evdir + evd + "/" + evd + "_REVIEW.jpg") 
            image_list += """      
            <div class="mySlides fade">
               <div class="numbertext">1 / 3</div>
               <img src="{:s}/{:s}_REVIEW.jpg" style="width:100%">
               <div class="text">{:s}</div>
            </div>
            """.format(evd, evd, evd)
            dots += """
            <span class="dot" onclick="currentSlide({:s})"></span>
            """.format(str(dc))
            dc += 1

      dots += "</div>"

      image_list += """      
         </div>
      """

      image_list += dots

      fp = open("slideshow.html", "r")
      slide_html = ""
      for line in fp:
         slide_html += line
      slide_html = slide_html.replace("IMAGE_LIST", image_list)


      out = open(self.local_evdir + "slideshow.html", "w")
      out.write(slide_html)
      out.close()
      print("saved slide show:", self.local_evdir + "slideshow.html")
      

   def min_file_size(self, event_day):
      self.set_dates(event_day)
      os.system("find " + self.local_evdir + " | grep .jpg > jpgs.txt")
      fp = open("jpgs.txt")
      for line in fp:
         line = line.replace("\n", "")
         if "MAP_FOV" in line or "REVIEW" in line or "marked" in line:
            img = cv2.imread(line)
            cv2.imwrite(line, img, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
         print(line)

   def make_channel(self, XS,YS, fw=None, fh=None , channel_img = None):
      do_ransac = True 

      # Ransac long objs
      if len(XS) > 10 : 
         temp_xs = []
         temp_ys = []
         for i in range(0,len(XS)):
            temp_xs.append(int(XS[i]))
            temp_ys.append(int(YS[i]))
         try:
            resp = ransac_outliers(temp_xs,temp_ys,"")
            (IN_XS,IN_YS,OUT_XS,OUT_YS,line_X,line_Y,line_y_ransac,inlier_mask,outlier_mask) = resp
         except:
            do_ransac = False
         if do_ransac is True:
            XS = IN_XS
            YS = IN_YS
            temp_xs = []
            temp_ys = []
            for i in range(0,len(XS)):
               temp_xs.append(int(XS[i][0]))
               temp_ys.append(int(YS[i][0]))
            XS = temp_xs
            YS = temp_ys
            print("ARAN XS", XS)
            print("ARAN YS", XS)


      slope,intercept = self.best_fit_slope_and_intercept(XS, YS)


      if len(XS) < 2:
         channel_img = np.zeros((fh,fw),dtype=np.uint8)
         return(channel_img)

      line_regr = [slope * xi + intercept for xi in XS]

      if channel_img is None:
         channel_img = np.zeros((fh,fw),dtype=np.uint8)

      min_lin_x = XS[0]
      max_lin_x = XS[-1]
      min_lin_y = line_regr[0]
      max_lin_y = line_regr[-1]

      print("LINE:", XS, YS)
      cv2.line(channel_img, (int(min_lin_x),int(min_lin_y)), (int(max_lin_x),int(max_lin_y)), (255,255,255), 25)
      #channel_img = self.invert_image(channel_img)
      #if len(channel_img.shape) == 2:
      #   channel_img = cv2.cvtColor(channel_img,cv2.COLOR_GRAY2BGR)

      #cv2.imshow("channel", channel_img)

      return(channel_img)

   def best_fit_slope_and_intercept(self,xs,ys):
       xs = np.array(xs, dtype=np.float64)
       ys = np.array(ys, dtype=np.float64)
       if len(xs) < 3:
          return(0,0)
       if ((np.mean(xs)*np.mean(xs)) - np.mean(xs*xs)) == 0:
          m = (((np.mean(xs)*np.mean(ys)) - np.mean(xs*ys)) / 1)

       else:
          m = (((np.mean(xs)*np.mean(ys)) - np.mean(xs*ys)) /
            ((np.mean(xs)*np.mean(xs)) - np.mean(xs*xs)))

       b = np.mean(ys) - m*np.mean(xs)
       if math.isnan(m) is True:
          m = 1
          b = 1

       return m, b

   def invert_image(self, imagem):
      imagem = (255-imagem)
      return(imagem)

   def all_time_index(self):
      # make a link list / nav list of all days in the archive
      # with status / summary info and link to event main page
      # from there we go to the sub pages. 
      # can oversee all from this page. 
      # /EVENTS/index_all_time.html

      
      template = ""
      tt = open("./FlaskTemplates/allsky-template-v2.html")
      for line in tt:
         template += line

      template = template.replace("{TITLE}", "ALLSKY7 ALL TIME EVENTS " )
      template = template.replace("AllSkyCams.com", "AllSky.com")

      data_dir = "/mnt/f/EVENTS/DBS/"
      dbs = os.listdir(data_dir)
      by_year = {}


      tb = pt()
      tb.field_names = ['Date', "Total Stations", "Total Obs", "Solved Events", "Failed Events", "Pending Events"]
      for db in sorted(dbs, reverse=True):


         if "journal" in db or "ALLSKYNETWORK" not in db or "CALIBS" in db :
            continue
         db_file = data_dir + db
         sqlite3.connect(db_file)
         db_con = sqlite3.connect(db_file)
         db_con.row_factory = sqlite3.Row
         db_cur = db_con.cursor()


         date = db.replace("ALLSKYNETWORK_", "")
         date = date.replace(".db", "")
         y,m,d = date.split("_")
         if y not in by_year:
            by_year[y] = {}
            by_year[y]['days'] = []
         by_year[y]['days'].append(date)

         sql = "SELECT station_id from event_obs "
         db_cur.execute(sql)
         rows = db_cur.fetchall()
         status = {}
         reporting_stations = {}
         for row in rows:
            st = row
            reporting_stations[st] = 1

         total_stations = len(reporting_stations.keys())

         sql = "SELECT event_status, count(*) from events group by event_status"
         db_cur.execute(sql)
         rows = db_cur.fetchall()
         status = {}
         for row in rows:
            st, count = row
            status[st] = count


         sql = "SELECT count(*) from event_obs "
         db_cur.execute(sql)
         rows = db_cur.fetchall()
         obs_count = rows[0][0]



         st = ""
         print("")
         solved = 0
         failed = 0
         pending = 0
         for key in status:
            if st != "":
              st += ","
            st += key + str(status[key])
            if "FAIL" in st:
               failed += status[key]
            if "SOLVED" in st or "SUCCESS" in st:
               solved += status[key]
            if "PEND" in st:
               pending += status[key]

         print(db_file, obs_count, st)
         tb.add_row( [date, total_stations, obs_count, solved, failed, pending])

      print(tb)

   def dt_header(self):
      header = """
      <!doctype html>
      <html lang="en">
        <head>

                <style>
                        @import url("https://cdn.jsdelivr.net/npm/bootstrap-icons@1.4.1/font/bootstrap-icons.css");
                        @import url("https://cdn.datatables.net/1.10.25/css/jquery.dataTables.min.css");

                </style>

         <!-- Required meta tags -->
         <meta charset="utf-8">
         <meta name="viewport" content="width=device-width, initial-scale=1">
         <title>AllSky.com </title>
               <script src="https://cdn.plot.ly/plotly-2.2.0.min.js"></script>

               <script src="https://kit.fontawesome.com/25faff154f.js" crossorigin="anonymous"></script>
               <!-- Bootstrap CSS -->
               <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.0-beta3/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-eOJMYsd53ii+scO/bJGFsiCZc+5NDVN2yr8+0RDqr0Ql0h+rP48ckxlpbzKgwra6" crossorigin="anonymous">
               <link rel="alternate" type="application/rss+xml" title="RSS 2.0" href="https://www.datatables.net/rss.xml">
               <script src="https://ajax.googleapis.com/ajax/libs/jquery/3.6.0/jquery.min.js"></script>
               <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.0.0-beta3/dist/js/bootstrap.bundle.min.js" integrity="sha384-JEW9xMcG8R+pH31jmWH6WWP0WintQrMb4s7ZOdauHnUtxwoG2vI5DkLtS3qm9Ekf" crossorigin="anonymous"></script>
               <script type="text/javascript" language="javascript" src="https://cdn.datatables.net/1.10.24/js/jquery.dataTables.min.js"></script>

               <script>
                  all_classes = ['meteor', 'cloud', 'bolt', 'cloud-moon', 'cloud-rain',  'tree', 'planes', 'car-side', 'satellite', 'crow', 'bug','chess-board','question']
                  labels = ['meteor', 'clouds', 'lightening', 'moon', 'rain', 'tree', 'planes', 'cars', 'satellite', 'BIRDS', 'fireflies','noise','notsure']
               </script>
         </head>
      """
      return(header)

   def event_table(self, date):
      self.set_dates(date)
      event_file = self.local_evdir + self.year + "_" + self.month + "_" + self.day  + "_ALL_EVENTS.json"
      event_table_file = self.local_evdir + self.year + "_" + self.month + "_" + self.day  + "_EVENT_TABLE.html"
      if os.path.exists(event_file):
         solved_ev = load_json_file(event_file)
      else:
         print("NO", event_file)
         exit()

      nav_header = self.make_page_header(date)

      template = ""
      tt = open("./FlaskTemplates/allsky-template-v2.html")
      for line in tt:
         template += line

      template = template.replace("{TITLE}", "ALLSKY7 EVENTS " + self.day)
      template = template.replace("AllSkyCams.com", "AllSky.com")
      self.local_evdir = self.local_event_dir + self.year + "/" + self.month + "/" + self.day  + "/"
      out_file_good = self.local_evdir + self.day + "_OBS_GOOD.html"
      out_file_bad = self.local_evdir + self.day + "_OBS_BAD.html"
      out_file_failed = self.local_evdir + self.day + "_OBS_FAIL.html"
      out_file_pending = self.local_evdir + self.day + "_OBS_PENDING.html"



      out = self.dt_header()
      out += "<h3>Event Table for {:s}</h3>\n".format(date)
      out += "<div style='background: white'><table id='event_list' class='display'><thead>\n"
      out += "<tr> <th>Event ID</th> <th>Status</th><th>Stations</th> <th>Dur</th> <th>Vel</th> <th>End Alt</th> <th>Shower</th> <th>a</th> <th>e</th> <th>i</th> <th>peri</th> <th>q</th> <th>ls</th> <th>M</th> <th>P</th></tr></thead><tbody>\n"
      bad_events = []
      failed_events = []
      pending_events = []
      tb = pt()
      tb.field_names = ["ID","Status", "Stations"]

      for ev in solved_ev:
         v_init = 0
         e_alt = 0
         shower_code = ""
         stations = list(set(ev['stations']))
         ev_id = ev['event_id']
         st_str = ""
         event_status = ev['solve_status']
         #print("EVENT STATUS:", ev_id, event_status)
         if ev['solve_status'] == "FAILED":
            failed_events.append(ev)   
         #if "solution" not in ev:
         #   print("NO SOL",ev['solve_status'])
         for st in sorted(stations):
            #st = st.replace("AMS", "")
            if st_str != "":
               st_str += ", "
            st_str += st
         dur = 0
         status = ev['solve_status'] 
         if "solution" in ev:
            sol = ev['solution']
            if "traj" in ev['solution']:
               traj = ev['solution']['traj']
            else:
               continue
            orb = ev['solution']['orb']
            shower = ev['solution']['shower']
            v_init = str(int(traj['v_init']/1000))  + " km/s"
            e_alt = str(int(traj['end_ele']/1000))  + " km"
            shower_code = shower['shower_code']
            #dur = sol['duration']
            if orb['a'] is None or orb['a'] == "":
               orb['a'] = 0
               orb['e'] = 0
               orb['i'] = 0
               orb['peri'] = 0
               orb['q'] = 0
               orb['la_sun'] = 0
               orb['mean_anomaly'] = 0
               orb['T'] = 0
               bad_events.append(ev)   
         else:
            orb = {}
            orb['a'] = 0
            orb['e'] = 0
            orb['i'] = 0
            orb['peri'] = 0
            orb['q'] = 0
            orb['la_sun'] = 0
            orb['mean_anomaly'] = 0
            orb['T'] = 0
            bad_events.append(ev)   

         tb.add_row([ev_id, event_status, stations])

         ev_link =  """ <a href="javascript:make_event_preview('""" + ev_id + """')">"""
         ev_row = "<tr> <td ><span id='" + ev_id + "'>" + ev_link + "{:s}</a></span></td><td>{:s}</td><td>{:s}</td> <td>{:s}</td> <td>{:s}</td> <td>{:s}</td> <td>{:s}</td> <td>{:0.2f}</td> <td>{:0.2f}</td> <td>{:0.2f}</td> <td>{:0.2f}</td> <td>{:0.2f}</td> <td>{:0.2f}</td> <td>{:0.2f}</td> <td>{:0.2f}</td></tr>\n".format(ev_id, event_status, st_str, str(dur), str(v_init), str(e_alt), str(shower_code),float(orb['a']),float(orb['e']),float(orb['i']),float(orb['peri']),float(orb['q']),float(orb['la_sun']),float(orb['mean_anomaly']),float(orb['T']))
         out += ev_row
      out += """</tbody></table>
      </div>
      <br><br>
      <script>
         $(document).ready( function () {
            $('table.display').dataTable();
         })
      </script>

      """

      template = template.replace("{MAIN_CONTENT}", nav_header + out)

      print(tb)

      fp = open(event_table_file, "w")

      fp.write(template)
      fp.close()

      return(out)

   def reconcile_obs_day(self, date):
      self.set_dates(date)
      self.all_obs = load_json_file(self.all_obs_file)
      invalid = 0
      valid = 0

      valid_obs = {}
      for row in self.all_obs:
         station_id = row['station_id']
         obs_file = row['sd_video_file'].replace(".mp4", "")
         year = obs_file[0:4]
         obs_date = obs_file[0:10]
         if station_id not in valid_obs:
            valid_obs[station_id] = self.get_valid_obs(station_id, date)
         cfile = "/mnt/archive.allsky.tv/" + station_id + "/METEORS/" + year + "/" + obs_date + "/" + station_id + "_" + obs_file + "-prev.jpg"
         if obs_file in valid_obs[station_id]:
            print("VALID", station_id, obs_file)
            valid += 1
         else:
            el = obs_file.split("_")[0]
            print("INVALID", station_id, obs_file)
            invalid += 1
            # delete aws obs here!
            if os.path.exists(cfile):
               img = cv2.imread(cfile)
               simg = cv2.resize(img, (640,360))
               cv2.imshow('pepe', simg)
               cv2.waitKey(30)
      print("VALID:", valid)          
      print("INVALID:", invalid)          

   def reconcile_events_day(self, date):
      # make sure local event pool (sql/filesystem) and aws are all in sync with each other. 
      # delete events in AWS that are not existing here
      # otherwise update AWS if it is missing or the vals don't match. 

      # start with ev file for this day

      self.set_dates(date)


      ev_file = self.local_evdir  + date + "_ALL_EVENTS.json"
      ev_data = load_json_file(ev_file)

      # check aws first
      aws_ids = {}
      for data in ev_data:
         aws_ids[data['event_id']] = data
         sql = """
            SELECT event_id, event_status, run_date 
            FROM events
           WHERE event_id = ?
         """
         self.cur.execute(sql, [data['event_id']])
         rows = self.cur.fetchall()
         if len(rows) is True:
            print("AWS EVENT EXISTS LOCALLY", data['event_id']) 
            if data['solve_status'] == rows[0][1]:
               print("   Same status:", data['solve_status'], rows[0][1])
            else:
               print("   NOT Same status:", data['solve_status'], rows[0][1])

         else:
            print("AWS EVENT DOES NOT EXISTS LOCALLY", data['event_id']) 
            print("DELETE AWS EVENT")
            delete_event(self.dynamodb, date, data['event_id'])

      sql = """
            SELECT event_id, event_status, run_date 
            FROM events
      """
      
      self.sync_dyna_day(date)
      #self.cur.execute(sql)
      #rows = self.cur.fetchall()
      #for row in rows:
      #   event_id, event_status, run_date = row 
      #   if event_id not in aws_ids:
      #      print(event_id, "MISSING FROM AWS")
      #      print("NEED TO INSERT AWS")
      #   else:
      #      print(event_id, "EXISTS INSIDE AWS")



   def to_cartesian(lat, lon):
       """Convert lat/lon to Cartesian coordinates."""
       lat, lon = radians(lat), radians(lon)
       x = EARTH_RADIUS_KM * cos(lat) * cos(lon)
       y = EARTH_RADIUS_KM * cos(lat) * sin(lon)
       z = EARTH_RADIUS_KM * sin(lat)
       return np.array([x, y, z])
   
   def heading_vector(lat, lon, heading, distance=500):
       """Calculate the end point of the heading vector in Cartesian coordinates."""
       # Convert the starting point to Cartesian coordinates
       start_cartesian = to_cartesian(lat, lon)
   
       # Calculate the end point in lat/lon
       lat_rad = radians(lat)
       lon_rad = radians(lon)
       heading_rad = radians(heading)
   
       end_lat = asin(sin(lat_rad) * cos(distance / EARTH_RADIUS_KM) +
                      cos(lat_rad) * sin(distance / EARTH_RADIUS_KM) * cos(heading_rad))
       end_lon = lon_rad + atan2(sin(heading_rad) * sin(distance / EARTH_RADIUS_KM) * cos(lat_rad),
                                 cos(distance / EARTH_RADIUS_KM) - sin(lat_rad) * sin(end_lat))
   
       # Convert the end point to Cartesian coordinates
       end_cartesian = to_cartesian(degrees(end_lat), degrees(end_lon))
   
       # Return the heading vector (difference between end and start points)
       return end_cartesian - start_cartesian
   
   def line_intersection(start1, heading1, start2, heading2):
       """Find the intersection of two lines given by start points and headings."""
       # Convert the start points and headings to Cartesian coordinates
       start1_cartesian = to_cartesian(*start1)
       heading1_vector = heading_vector(*start1, heading1)
       
       start2_cartesian = to_cartesian(*start2)
       heading2_vector = heading_vector(*start2, heading2)
   
       # Line intersection calculation in 3D
       cross_product = np.cross(heading1_vector, heading2_vector)
       if np.allclose(cross_product, 0):
           return None  # Parallel or identical lines
   
       # Solving the system of linear equations to find the intersection point
       matrix = np.vstack([heading1_vector, -heading2_vector]).T
       try:
           t, s = np.linalg.solve(matrix, start2_cartesian - start1_cartesian)
       except np.linalg.LinAlgError:
           return None  # No solution, lines do not intersect
   
       intersection_point_cartesian = start1_cartesian + t * heading1_vector
   
       # Convert back to lat/lon
       x, y, z = intersection_point_cartesian
       lat = degrees(atan2(z, sqrt(x**2 + y**2)))
       lon = degrees(atan2(y, x))
   
       return lat, lon
   
   # Example usage
   #start1 = (45.0, -93.0)  # Latitude, Longitude
   #heading1 = 90           # East
   
   #start2 = (46.0, -94.0)  # Latitude, Longitude
   #heading2 = 180          # South
   
   #intersection = line_intersection(start1, heading1, start2, heading2)
   #print(intersection)
   
   
   
   
   
