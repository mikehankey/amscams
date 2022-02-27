import glob
import simplejson as json
import time
import math
import os
import scipy.optimize
import numpy as np
import datetime, calendar
import cv2
from sklearn import linear_model, datasets
from skimage.measure import ransac, LineModelND, CircleModel
import requests

from sklearn.linear_model import RANSACRegressor
from sklearn.datasets import make_regression

from PIL import ImageFont, ImageDraw, Image, ImageChops

from Classes.DisplayFrame import DisplayFrame
from Classes.Detector import Detector
from Classes.Camera import Camera
from Classes.Calibration import Calibration
from lib.PipeAutoCal import gen_cal_hist,update_center_radec, get_catalog_stars, pair_stars, scan_for_stars, calc_dist, minimize_fov, AzEltoRADec , HMS2deg, distort_xy, XYtoRADec, angularSeparation
from lib.PipeUtil import load_json_file, save_json_file, cfe, check_running
from lib.FFFuncs import best_crop_size, ffprobe



class Events():
   def __init__(self, fv=None):
      self.year = None 
      self.mon = None 
      self.day = None 
      #self.date = year + "_" + month + "_" + day
      self.fv = fv
      self.event_dir = "/mnt/ams2/EVENTS/"
      self.cloud_event_dir = "/mnt/archive.allsky.tv/EVENTS/"
      self.all_events_file = self.event_dir + "ALL_EVENTS.json"
      self.json_conf = load_json_file("../conf/as6.json")
      self.station_id = self.json_conf['site']['ams_id']
      self.cloud_host = "https://archive.allsky.tv/"

   def do_ms_day(self, date):
      obs_ids = {}
      network = self.json_conf['my_network']
      min_cnt = {}
      min_cnt_file = "/mnt/ams2/meteors/" + date + "/" + self.station_id + "_" + date + "_EVENTS.info"
      for station_id in network:
         year = date.split("_")[0]
         day_url = "{:s}{:s}/METEORS/{:s}/{:s}/{:s}_OBS_IDS.info".format(self.cloud_host,station_id,year,date,date)
         print(day_url)

         response = requests.get(day_url)
         content = response.content.decode()
         try:
            obs_ids[station_id] = json.loads(content)
         except:
            print("No file.", day_url)

      for station_id in sorted(obs_ids):
         print(station_id, len(obs_ids[station_id]))
         obs_data = sorted(obs_ids[station_id], key=lambda x: (x[1]), reverse=False)
         for obs in obs_data:
            day, time = obs[1].split(" ")
            hour_min = time[0:5]
            print("   ", hour_min, time)
            if hour_min not in min_cnt:
               min_cnt[hour_min] = {} 
               min_cnt[hour_min]['stations'] = [] 
               min_cnt[hour_min]['obs'] = [] 
               min_cnt[hour_min]['times'] = [] 
               min_cnt[hour_min]['total_stations'] = 0 
            min_cnt[hour_min]['stations'].append(station_id)
            min_cnt[hour_min]['obs'].append(obs[0])
            min_cnt[hour_min]['times'].append(time)
            min_cnt[hour_min]['total_stations'] = len(set(min_cnt[hour_min]['stations']))
       

      for hour_min in min_cnt:
         if min_cnt[hour_min]['total_stations'] >= 2:
            if "pairs" not in min_cnt[hour_min]:
               min_cnt[hour_min]['pairs'] = {}
            min_cnt[hour_min]['pairs'] = self.find_make_pairs(min_cnt[hour_min], min_cnt[hour_min]['pairs'])
            if len(min_cnt[hour_min]['pairs']) >= 1:
               print(hour_min, len(min_cnt[hour_min]['pairs'].keys()), min_cnt[hour_min]['pairs'].keys()) 

      try:
         save_json_file(min_cnt_file, min_cnt)
         print(min_cnt_file)
      except:
         print("nothing to save")
 
   def find_make_pairs(self, ev_data, pairs):
      for i in range(0, len(ev_data['times'])):
         station = ev_data['stations'][i]
         obs = ev_data['obs'][i]
         time = ev_data['times'][i]
         h,m,s = time.split(":")
         for j in range(0, len(ev_data['times'])):
            jobs = ev_data['obs'][j]
            jstation = ev_data['stations'][j]
            if station == jstation:
               continue
            jtime = ev_data['times'][j]
            jh,jm,js = jtime.split(":")

            ob1 = station + "_" + obs 
            ob2 = jstation + "_" + jobs 

            temp = [ob1, ob2]
            temp = sorted(temp)
            key = temp[0] + "__" + temp[1]


            if key not in pairs:
               time_diff = abs(float(s) - float(js))
               if time_diff < 2:
                  pairs[key] = {} 
                  pairs[key]['time_diff'] = time_diff 
      return(pairs)        

   def status(self):
      self.all_events = load_json_file("/mnt/ams2/EVENTS/ALL_EVENTS.json")
      self.all_events = sorted(self.all_events, key=lambda x: (x['event_id']), reverse=True)
      for event in self.all_events:
         if event['solve_status'] == 'UNSOLVED' :
            print(event['event_id'], event['solve_status'] , event)
            cmd = "./solveWMPL.py se " + event['event_id'] + " " 
            print(cmd)
            os.system(cmd)


   def load_events(self):
      #fv['solve_status']  # 0 = not run, 1 = solved, -1 = failed -2 missing reductions
      #fv['start_date']
      #fv['end_date']
      #fv['stations'] # list of stations to include in list "," separated
      select_data = []
      fv = self.fv

      aes = self.event_dir + "ALL_EVENTS_SUMMARY.json"
      caes = self.cloud_event_dir + "ALL_EVENTS_SUMMARY.json"
      if cfe(self.event_dir,1) == 0:
         os.makedirs(event_dir)
      if cfe(aes) == 0:
         if cfe(caes) == 0:
            os.system(" cp " + caes + " " + aes)
      out = ""
      ae_data = load_json_file(aes)

      for row in ae_data:
         show_row = 0
         solve_status, event_id, event_datetime, stations, files, shower, ls, cs = row
         if fv['stations'] is not None:
            tsd = fv['stations']
            if "," not in tsd:
               temp = [tsd]
               tsd = temp
            else:
               temp = tsd.split(",")
               tsd = temp
            asd = stations
            for st in asd:
               for tst in tsd:
                  if st == tst:
                     show_row = 1
         else:
            show_row = 1
         if show_row == 1:
            select_data.append(row)

      self.select_data = sorted(select_data, key=lambda x: (x[2]), reverse=True)

   def render_events_list(self):
      matches = 0
      out_table = "<div class='row'>"
      out_table += "<div class='col'>Event ID</div><div class='col'>Status</div>"
      for data in self.select_data:
         show_row = 0
         solve_status, event_id, event_datetime, stations, files, shower, ls, cs = data
         print("DATA:", data)
         if self.fv['solve_status'] is None:
            show_row = 1
         elif self.fv['solve_status'] == "1" and "SUCCESS" in solve_status :
            show_row = 1
         elif self.fv['solve_status'] == "0" or "NOT SOLVED" in solve_status :
            show_row = 1
         elif self.fv['solve_status'] == "-1" and "FAILED" in solve_status :
            show_row = 1
         elif self.fv['solve_status'] == "-2" and "missing" in solve_status :
            show_row = 1
         if show_row == 1:
            matches += 1
            link = "/event_detail/" + str(event_id) + "/"
            href = "<a href=" + link + ">"
            out_table += "<div class='row'><div class='col'>" + href + str(event_id) + "</a></div><div class='col'>" + solve_status + "</div></div>\n"

      out_table += "</div>"
      head = "<div class='container' style='border: 1px #FFFFFF solid'>"
      head += "<div class='row'><div class='col-4'>" +  str(matches) + " events </div></div>"
      foot = "</div>"
      template = self.get_template("FlaskTemplates/EventViewerList.html")
      ev_header = self.get_template("FlaskTemplates/EventViewerHeader.html")
      ev_footer = self.get_template("FlaskTemplates/EventViewerFooter.html")
      template = template.replace("{EV_HEADER}", ev_header)
      template = template.replace("{EV_FOOTER}", ev_footer)
      template = template.replace("{EV_LIST}", head + out_table + foot)
      self.center_lat = 40
      self.center_lon = -46
      self.kml_link = "/EVENTS/ALL_TRAJECTORIES.kml"
      traj_iframe = """<iframe width=100% height=450 src="https://archive.allsky.tv/APPS/dist/maps/index.html?mf={:s}&lat={:s}&lon={:s}&zoom=3"></iframe>""".format(self.kml_link, str(self.center_lat), str(self.center_lon))

      self.orb_link = "https://archive.allsky.tv/EVENTS/ALL_ORBITS.json"
      orb_iframe = """<iframe width=100% height=450 src="https://orbit.allskycams.com/index_emb.php?file={:s}"></iframe>""".format(self.orb_link)
      self.stations_link = "https://archive.allsky.tv/EVENTS/ALL_STATIONS.kml"
      stations_iframe = """<iframe width=100% height=450 src="https://archive.allsky.tv/APPS/dist/maps/index.html?mf={:s}&lat={:s}&lon={:s}&zoom=3"></iframe>""".format(self.stations_link, str(self.center_lat), str(self.center_lon))
      self.radiant_link = "https://archive.allsky.tv/EVENTS/PLOTS_ALL_RADIANTS.json"
      rad_iframe = """<iframe width=100% height=660 src="https://archive.allsky.tv/APPS/dist/radiants.html?mf={:s}"></iframe>""".format(self.radiant_link)


      template = template.replace("{RADIANTS_IFRAME}", rad_iframe)
      template = template.replace("{TRAJECTORY_IFRAME}", traj_iframe)
      template = template.replace("{ORBIT_IFRAME}", orb_iframe)
      template = template.replace("{STATIONS_IFRAME}", stations_iframe)

      return(template)

   def make_missing_data_list(self):
      missing_data = []
      self.all_events = load_json_file(self.event_dir + "ALL_EVENTS.json")
      for data in self.all_events:
         good = 1
         if "solve_status" in data:
            if data['solve_status'] != "SUCCESS" and data['solve_status'] != "WMPL_FAILED":
               good = 0
         else:
            good = 0
         if "solution" not in data:
            good = 0
         if good == 0:
            print(data['event_id'], data['stations'])
            if "obs" not in data:
               print("MISSING OBS!")
               for i in range(0,len(data['stations'])):
                  missing_data.append((data['stations'][i], data['files'][i]))
            else:
               for station in data['obs']:
                  for ob_file in data['obs'][station]:
                     if "azs" in data['obs'][station][ob_file]:
                        if len(data['obs'][station][ob_file]['azs']) == 0:
                           print("    ******* MISSING AZS:", len(data['obs'][station][ob_file]['azs']))
                           missing_data.append((station, ob_file))

                     else:
                        print("    ******* MISSING AZS:", ob_file, data['obs'][ob_file])
                        missing_data.append((station, ob_file))
      missing_data = sorted(missing_data, key=lambda x: x[0], reverse=False)
      for data in missing_data:
         print(data)

      save_json_file("/mnt/ams2/EVENTS/ALL_MISSING_DATA.json", missing_data)
      cmd = " cp /mnt/ams2/EVENTS/ALL_MISSING_DATA.json /mnt/archive.allsky.tv/EVENTS/ALL_MISSING_DATA.json" 
      print(cmd)
      os.system(cmd)

                    

   def get_template(self, template_file):
      temp = ""
      fp = open(template_file, "r")
      for line in fp:
         temp += line
      return(temp)
