import glob
import time
import math
import os
import scipy.optimize
import numpy as np
import datetime, calendar 
import cv2
from sklearn import linear_model, datasets
from skimage.measure import ransac, LineModelND, CircleModel

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



class EventManager():
   def __init__(self, cmd=None, day=None, month=None,year=None):
      self.DF = DisplayFrame()
      self.cmd = cmd
      self.day = day
      self.month = month
      self.year = year
      self.data_dir = "/mnt/ams2/"
      self.all_events_summary_file = self.data_dir + "/EVENTS/ALL_EVENTS_SUMMARY.json"
      self.all_orbits_file = self.data_dir + "/EVENTS/ALL_ORBITS.json"
      self.all_trajectories_file = self.data_dir + "/EVENTS/ALL_TRAJECTORIES.json"
      self.all_radiants_file = self.data_dir + "/EVENTS/ALL_RADIANTS.json"

      if year is not None:
         self.batch_mode = "year"
         self.cloud_dir = "/mnt/archive.allsky.tv/EVENTS/" + self.year + "/" 
         self.cloud_file_index = self.cloud_dir + "cloud_event_files_" + self.year + ".txt"
      if month is not None:
         self.batch_mode = "month"
         self.year, self.month = month.split("_")
         self.cloud_dir = "/mnt/archive.allsky.tv/EVENTS/" + self.year + "/" + self.month + "/" 
         self.cloud_file_index = self.cloud_dir + "cloud_event_files_" + self.year + "_" + self.month + ".txt"
      if day is not None:
         print(self.day)
         self.year, self.month, self.day = day.split("_")
         self.batch_mode = "day"
         self.date = day
         self.cloud_dir = "/mnt/archive.allsky.tv/EVENTS/" + self.year + "/" + self.month + "/" + self.day + "/"
         self.cloud_file_index = self.cloud_dir + "cloud_event_files_" + self.year + "_" + self.month + "_" + self.day  
      self.local_dir = self.cloud_dir.replace("/archive.allsky.tv/", "/ams2/")
      self.local_file_index = self.cloud_file_index.replace("/archive.allsky.tv/", "/ams2/")
      self.all_events_dir = "/mnt/ams2/EVENTS/"
      self.all_events_traj = "/mnt/ams2/EVENTS/ALL_TRAJECTORIES.json"
      self.all_events_traj_kml = "/mnt/ams2/EVENTS/ALL_TRAJECTORIES.kml"
      self.cloud_all_events_traj_kml = "/mnt/archive.allsky.tv/EVENTS/ALL_TRAJECTORIES.kml"
      self.all_events_orb = "/mnt/ams2/EVENTS/ALL_ORBITS.json"
      self.cloud_event_dir = "/mnt/archive.allsky.tv/EVENTS/"

   def controller(self):
      if self.cmd is None:
         return()
      if self.cmd == "all_traj":
          cloud_files = self.make_all_traj_kml()
      if self.cmd == "cloud_files":
          cloud_files = self.update_html_index()
      if self.cmd == "de" or self.cmd == "define_events":
          self.define_events()
      if self.cmd == "aei" or self.cmd == "all_events_index":
          self.all_events_index_new()
      if self.cmd == "aer" or self.cmd == "all_events_report":
          self.all_events_report()
          self.make_period_files()
          cloud_files = self.make_all_traj_kml()
          os.system("python3 PLT.py")
      if self.cmd == "sus" or self.cmd == "solve_unsolved":
          self.solve_unsolved_events()
      if self.cmd == "re" or self.cmd == "reconcile_events":
          self.reconcile_events()

   def reconcile_events(self):
      now = datetime.datetime.now().strftime("%Y_%m_%d")
      nyear = now[0:4]
      nmonth = now[5:7]
      print("NY:",nyear)
      print("NM:",nmonth)
      print("Y:",self.year)
   #   exit()
      if nyear == self.year:
         print("RECONCILE THIS YEAR:", self.year)
      else:
         nmonth = 12
      for i in range(1,int(nmonth)+1):
         num_days = calendar.monthrange(int(self.year), i)[1]
         days = [datetime.date(int(self.year), int(i), day) for day in range(1, num_days+1)]
         for day_dt in days:
            if day_dt <= datetime.date.today():
               day = day_dt.strftime("%Y_%m_%d")
               cmd = "./solveWMPL.py de " + day
               print(cmd)
               os.system(cmd)
               cmd = "./DynaDB.py udc " + day
               print(cmd)
               cmd = "./solveWMPL.py sd " + day
               print(cmd)
               os.system(cmd)
               cmd = "./solveWMPL.py de " + day
               print(cmd)
               os.system(cmd)
               cmd = "./DynaDB.py udc " + day
               print(cmd)
      

   def define_events(self):

      if self.batch_mode == "year":
         print("Define events for the entire year")
         for i in range(1,13):
            num_days = calendar.monthrange(int(self.year), i)[1]
            days = [datetime.date(int(self.year), int(i), day) for day in range(1, num_days+1)]
            for day_dt in days:
               if day_dt <= datetime.date.today():
                  day = day_dt.strftime("%Y_%m_%d")
                  cmd = "./solveWMPL.py de " + day
                  print(cmd)
                  os.system(cmd)

      if self.batch_mode == "month":
         print("Define events for the entire month")
         num_days = calendar.monthrange(int(self.year), int(self.month))[1]
         days = [datetime.date(int(self.year), int(self.month), day) for day in range(1, num_days+1)]
         print("Define events for month.")

   def define_events(self):

      if self.batch_mode == "year":
         print("Define events for the entire year")
         for i in range(1,13):
            num_days = calendar.monthrange(int(self.year), i)[1]
            days = [datetime.date(int(self.year), int(i), day) for day in range(1, num_days+1)]
            for day_dt in days:
               if day_dt <= datetime.date.today():
                  day = day_dt.strftime("%Y_%m_%d")
                  cmd = "./solveWMPL.py de " + day
                  print(cmd)
                  os.system(cmd)

      if self.batch_mode == "month":
         print("Define events for the entire month")
         num_days = calendar.monthrange(int(self.year), int(self.month))[1]
         days = [datetime.date(int(self.year), int(self.month), day) for day in range(1, num_days+1)]
         print("Define events for month.")
         for day_dt in days:
            day = day_dt.strftime("%Y_%m_%d")
            cmd = "./solveWMPL.py de " + day
            print(cmd)

      if self.batch_mode == "day":
         print("Define events for on day")
         cmd = "./solveWMPL.py de " + self.date
         print(cmd)


   def all_events_index_new(self):
      now = datetime.datetime.now().strftime("%Y_%m_%d")
      years = []
      nyear = now[0:4]
      nmonth = now[5:7]
      temp = glob.glob("/mnt/ams2/EVENTS/*")
      for year_dir in temp:
         if cfe(year_dir, 1) == 1:
             year = year_dir.split("/")[-1]
             years.append(year)
      print("YEARS:", years)
      ev_files = []
      for year in years:
         if year == nyear:
            end_month = nmonth
         else:
            end_month = 12
         for i in range(1,int(nmonth)+1):
            num_days = calendar.monthrange(int(self.year), i)[1]
            days = [datetime.date(int(self.year), int(i), day) for day in range(1, num_days+1)]
            for day_dt in days:
               if year == nyear: 
                  end_dt = datetime.date.today()
                  #.strftime("%Y_%m_%d")
               else:
                  end_d = str(year) + "_12_31"  
                  end_dt = datetime.datetime.strptime(end_d, "%Y_%m_%d")
               day_dt = datetime.datetime(day_dt.year, day_dt.month, day_dt.day)
               end_dt = datetime.datetime(end_dt.year, day_dt.month, day_dt.day)

               print(type(day_dt), type(end_dt))
               if day_dt <= end_dt:
                  date_str = day_dt.strftime("%Y_%m_%d")
                  y,m,d = date_str.split("_")
                  ev_dir = "/mnt/ams2/EVENTS/" + y + "/" + m + "/" + d + "/" 
                  ev_file = ev_dir + date_str + "_ALL_EVENTS.json"
                  if cfe(ev_file) == 1:
                     print("THERE ARE EVENTS TODAY:", ev_file) 
                     ev_files.append(ev_file)
                  else:
                     print("THERE ARE NO EVENTS TODAY:", ev_file) 
                     cloud_ev_file = ev_file.replace("/mnt/ams2", "/mnt/archive.allsky.tv")
                     cloud_ev_dir = ev_dir.replace("/mnt/ams2", "/mnt/archive.allsky.tv")
                     if cfe(cloud_ev_file) == 1:
                        print("CLOUD EVENT FILE EXISTS. COPY THEM.")
                        if cfe(ev_dir, 1) == 0:
                           os.makedirs(ev_dir)
                        print("cp " + cloud_ev_dir + "*.json " + ev_dir)
                        os.system("cp " + cloud_ev_dir + "*.json " + ev_dir)
                        ev_files.append(ev_file)

      all_events = []
      day_summary = []
      events_summary = []
      for ev_file in ev_files:
         solve_info_file = ev_file.replace("_ALL_EVENTS", "_SOLVE_INFO")
         try:
            evd = load_json_file(ev_file)
            efn = ev_file.split("/")[-1]
            eday = efn[0:10]
            print("ADDING:", len(evd), "events")
         except:
            print("CORRUPT EVENT FILE!", ev_file)
         solved = 0
         failed = 0
         missing = 0
         unsolved = 0
         day_total = 0
         for data in evd:
            if "solution" not in data:
               data['solve_status'] = "UNSOLVED"
               status = "UNSOLVED"
            if "solve_status" in data:
               if "SUCCESS" in data['solve_status']:
                  solved += 1
                  status = "SUCCESS"
               if "UNSOLVED" in data['solve_status']:
                  unsolved += 1
                  status = "UNSOLVED"
               if "FAIL" in data['solve_status']:
                  failed += 1
                  status = "WMPL FAILED"
               if "missing" in data['solve_status']:
                  missing += 1
                  status = data['solve_status']
            else:
               unsolved += 1
               #print(data['event_id'], data['solve_status'] )
            day_total += 1   
            all_events.append(data)
            shower = ""
            if "solution" in data:
               if data['solution'] == 0:
                  del data['solution']
               elif "shower" in data['solution']:
                  shower = data['solution']['shower']['shower_code']
               else:
                  shower = ""

            events_summary.append( (status, data['event_id'], min(data['start_datetime']), data['stations'], data['files'], shower, 1, 1))
         day_data = {}
         day_data['date'] = eday
         day_data['total_events'] = day_total
         day_data['total_solved'] = solved
         day_data['total_unsolved'] = unsolved
         day_data['total_failed'] = failed
         day_data['total_missing'] = missing
         day_summary.append(day_data)
         print("TOTAL EVENTS thru:", eday, solved, unsolved, failed, missing)

      for data in day_summary:
         day = data['date']
         day_total = data['total_events']
         y,m,d = day.split("_")
         ev_dir = "/mnt/ams2/EVENTS/" + y + "/" + m + "/" + d + "/"  
         if cfe(ev_dir, 1) == 0:
            print("NO EVENT DIR!", ev_dir)
         else:
            print("EVENT DIR EXISTS", ev_dir)
            ev_file = ev_dir + day + "_ALL_EVENTS.json" 

         if day_total == 0:
            cmd = "./solveWMPL.py de " + day
            print(cmd)
            #input("RUN DETERMINE EVENTS?:" + cmd)
            #os.system(cmd)
            if cfe(solve_info_file) == 1:
               solve_info = load_json_file(solve_info_file)
            else:
               solve_info = {}
            solve_info['last_event_run'] = now
            print("SAVING SOLVE INFO FILES")
            save_json_file(solve_info_file, solve_info)
      save_json_file("/mnt/ams2/EVENTS/EVENTS_DAY_SUMMARY.json", day_summary)
      save_json_file("/mnt/ams2/EVENTS/ALL_EVENTS.json", all_events)

      save_json_file("/mnt/ams2/EVENTS/ALL_EVENTS_SUMMARY.json", events_summary)


   def make_all_traj_kml(self):
      import simplekml
      import geopy
      from geopy.distance import geodesic
      all_traj = load_json_file(self.all_events_traj)
      for traj in all_traj:
         print(traj)


      

      # given: lat1, lon1, b = bearing in degrees, d = distance in kilometers


      #lat2, lon2 = destination.latitude, destination.longitude

      kml = simplekml.Kml()
      used = {}

      pc = 0
      colors = ['ff0b86b8', 'ffed9564', 'ff0000ff', 'ff00ffff', 'ffff0000', 'ff00ff00', 'ff800080', 'ff0080ff', 'ff336699', 'ffff00ff' ]
      # add station points

      station_folders = {}
      used = {}
      pc = 0

      for tj in all_traj:
#{'end_ele': 65463.02962164887, 'v_avg': 19375.3589393399, 'end_lat': 40.2306482833715, 'start_lon': -76.75017937323105, 'start_lat': 40.20754500915026, 'start_ele': 83727.58043208688, 'v_init': 20026.277050047665, 'end_lon': -76.87984925733045}
         if tj['start_ele'] > 140000 or tj['end_ele'] > 140000 or tj['start_ele'] < 60000 or tj['end_ele'] < 5000:
            continue
         color = colors[pc]
         line_desc = tj['event_id'] 
         linestring = kml.newlinestring(name=line_desc)
         linestring.coords = [(tj['start_lon'],tj['start_lat'],tj['start_ele']),(tj['end_lon'],tj['end_lat'],tj['end_ele'])]
         linestring.altitudemode = simplekml.AltitudeMode.relativetoground
         linestring.extrude = 1

      kml.save(self.all_events_traj_kml)
      print("SAVED:", self.all_events_traj_kml)
      if cfe(self.cloud_event_dir,1) == 0:
         os.makedirs(self.cloud_event_dir)
      cmd = "cp " + self.all_events_traj_kml + " " + self.cloud_all_events_traj_kml
      print("CMD:", cmd)
      os.system(cmd)


      print(self.all_events_traj_kml)
      return(kml.kml())

   def all_events_report(self):
      c = 0
      print("All events report")
      all_events_file = "/mnt/ams2/EVENTS/ALL_EVENTS.json"
      all_events = load_json_file(all_events_file)
      print(len(all_events), "Total Events")
      events_summary = []
      all_orbits = {}
      all_trajectories = []
      all_radiants = []
      all_showers = []
      all_events = sorted(all_events, key=lambda x: (x['event_id']), reverse=True)
      for event in all_events:
         shower = ""
         if "solve_status" in event:
            status = event['solve_status']
         else:
            status = "NOT SOLVED"
         sts = ""
         fls = ""
         for i in range(0, len(event['stations'])):
            if i != 0:
               sts += ","
               fls += ","
            sts += event['stations'][i]
            fls += event['files'][i]
         if "solution" in event:
            if event['solution'] == 0:
               status = "OBS NOT LOADED"
               continue
            if "orb" in event['solution']:
               orb = event['solution']['orb']
               print("SOL:", event['solution'])
               orb['event_id'] = event['event_id']
               orb['vel_init'] = event['solution']['traj']['v_init']
               orb['event_datetime'] = min(event['start_datetime'])
               show_orb = self.make_show_orb(orb)
               if orb['T'] == 0 and orb['i'] == 0:
                  print("BAD ORB:", orb)
               else:
                  all_orbits[event['event_id']] = show_orb
            else:
               orb = None

            if "traj" in event['solution']:
               traj = event['solution']['traj']
               traj['event_id'] = event['event_id']
               all_trajectories.append(traj)
            else:
               traj = None

 
            if "rad" in event['solution']:
               radiants = event['solution']['rad']
               radiants['event_id'] = event['event_id']
               radiants['IAU'] = event['solution']['shower']['shower_code']
               all_radiants.append(radiants)
            else:
               radiants = None
               all_radiants.append(radiants)

            if "shower" in event['solution']:
               shower = event['solution']['shower']['shower_code']
               all_showers.append(shower)
            else:
               shower = ""

         e_year,e_month,e_day,e_hour,e_min,e_sec = self.parse_event_id(event['event_id'])
         local_ev_dir = "/mnt/ams2/EVENTS/" + e_year + "/" + e_month + "/" + e_day + "/" + event['event_id'] + "/" 
         cloud_ev_dir = "/mnt/archive.allsky.tv/EVENTS/" + e_year + "/" + e_month + "/" + e_day + "/" + event['event_id'] + "/" 
         if "SUCCESS" or "SOLVE" in status:
            lvd_status = 1
            cvd_status = 1
            #if cfe(local_ev_dir,1) == 1:
            #   lvd_status = 1
            #   cvd_status = 1
            #else:
            #   lvd_status = 0
            #   cvd_status = 0

            #if cfe(cloud_ev_dir,1) == 1:
            #   cvd_status = 1
            #else:
            #   cvd_status = 0

         else:
            lvd_status = 0
            cvd_status = 0
            print(local_ev_dir)
          
         rpt = "{:s} {:s} {:s} {:s} {:s} {:s} {:s} {:s}".format(status, str(event['event_id']), str(min(event['start_datetime'])), sts, fls, shower, str(lvd_status), str(cvd_status))
         #print(rpt)
         if c % 100 == 0:
            print("working", c)
         events_summary.append( (status, event['event_id'], min(event['start_datetime']), sts, fls, shower, lvd_status, cvd_status))
         c += 1

      save_json_file("/mnt/ams2/EVENTS/ALL_EVENTS_SUMMARY.json", events_summary)
      save_json_file("/mnt/ams2/EVENTS/ALL_ORBITS.json", all_orbits)
      save_json_file("/mnt/ams2/EVENTS/ALL_TRAJECTORIES.json", all_trajectories)
      save_json_file("/mnt/ams2/EVENTS/ALL_SHOWERS.json", all_showers)
      save_json_file("/mnt/ams2/EVENTS/ALL_RADIANTS.json", all_radiants)

      cmd = "cp /mnt/ams2/EVENTS/ALL_EVENTS_SUMMARY.json /mnt/archive.allsky.tv/EVENTS/"
      os.system(cmd)
      cmd = "cp /mnt/ams2/EVENTS/ALL_ORBITS.json /mnt/archive.allsky.tv/EVENTS/"
      os.system(cmd)
      cmd = "cp /mnt/ams2/EVENTS/ALL_TRAJECTORIES.json /mnt/archive.allsky.tv/EVENTS/"
      os.system(cmd)
      cmd = "cp /mnt/ams2/EVENTS/ALL_SHOWERS.json /mnt/archive.allsky.tv/EVENTS/"
      os.system(cmd)
      cmd = "cp /mnt/ams2/EVENTS/ALL_RADIANTS.json /mnt/archive.allsky.tv/EVENTS/"
      os.system(cmd)

      print("Saved json files in /mnt/ams2/EVENTS")

   def make_period_files (self):
      if cfe(self.all_events_summary_file) == 1:
         self.all_events = load_json_file(self.all_events_summary_file)
      if cfe(self.all_orbits_file) == 1:
         self.all_orbits = load_json_file(self.all_orbits_file)
      if cfe(self.all_trajectories_file) == 1:
         self.all_trajectories = load_json_file(self.all_trajectories_file)
      if cfe(self.all_radiants_file) == 1:
         self.all_radiants = load_json_file(self.all_radiants_file)
   


   def make_show_orb(self, orb):
      print("ORB:", orb )
      sorb = {}
      #sorb['color'] = "red"
      sorb['name'] = str(orb['event_id'])
      sorb['epoch'] = str(orb['jd_ref'])
      sorb['utc_date'] = str(orb['event_datetime'])
      sorb['T'] = str(orb['jd_ref'])
      sorb['vel'] = str(orb['vel_init'])
      sorb['a'] = str(orb['a'])
      sorb['e'] = str(orb['e'])
      sorb['I'] = str(orb['i'])
      sorb['Peri'] = str(orb['peri'])
      sorb['Node'] = str(orb['node'])
      sorb['q'] = str(orb['q'])
      sorb['M'] = str(orb['mean_anomaly'])
      sorb['P'] = str(orb['T'])
      return(sorb)


   def parse_event_id(self, event_id):
      Y = event_id[0:4]
      M = event_id[4:6]
      D = event_id[6:8]
      H = event_id[9:11]
      MIN = event_id[11:13]
      S = event_id[13:15]
      return(Y,M,D,H,MIN,S)



   def solve_unsolved_events(self):
      cores = 20
      events = load_json_file("/mnt/ams2/EVENTS/ALL_EVENTS_SUMMARY.json")
      unsolved = []
      for event in events:
         status, event_id, statrt_datetime, stations, files, shower, lvd_status,cvd_status= event
         if status == "UNSOLVED":
            unsolved.append(event)
      print(len(unsolved), "unsolved events.")

      for event in unsolved:
         status, event_id, statrt_datetime, stations, files, shower, lvd_status,cvd_status= event
         running = check_running("solveWMPL.py")
         print(running, "Solving processes running")
         if running < cores + 2:
            cmd = "./solveWMPL.py se " + event_id + " &"
            print(cmd)
            os.system(cmd)
         else:
            print("wait 30 seconds for solvers to complete.")
            time.sleep(30)




   def all_events_index(self):
      all_events = []
      os.system("find /mnt/ams2/EVENTS/ | grep ALL_EVENTS.json > /mnt/ams2/EVENTS/ALL_EVENTS.txt")
      fp = open("/mnt/ams2/EVENTS/ALL_EVENTS.txt")
      for line in fp:
         if "/mnt/ams2/EVENTS/ALL_EVENTS" in line:
            continue
         line = line.replace("\n", "")
         print("LOADING:", line)
         print("EV FILE:", line)
         try:
            ev_data = load_json_file(line)
         except:
            print("CORRUPT EVENT FILE:", line)
            xx = input("Waiting...")
            ev_data = []
         for data in ev_data:
            print("DATA:", data)
            all_events.append(data)
      save_json_file("/mnt/ams2/EVENTS/ALL_EVENTS.json", all_events)
      print("Saved", "/mnt/ams2/EVENTS/ALL_EVENTS.json")

   def update_html_index(self):
      cloud_files = self.get_event_cloud_file_list()
      html = ""
      for cloud_file in cloud_files:
         event_id = cloud_file.split("/")[-2]
         if "index.html" in cloud_file:
            url = cloud_file.replace("/mnt/", "https://")
            html += "<li><a href=" + url + ">" + event_id + "</a></li>\n"
      fp = open(self.local_dir + "index.html", "w")
      fp.write(html)
      fp.close()
      cmd =  "cp " + self.local_dir + "index.html" + " " + self.cloud_dir 
      os.system(cmd)
      print(html)

   def get_event_cloud_file_list(self):
      print("get cloud files for :", self.batch_mode, self.cloud_file_index)
      htmls = []
      if cfe(self.local_file_index) == 0:
         os.system("cp " + self.cloud_file_index + " " + self.local_file_index)
      if cfe(self.local_file_index) == 1:
         fp = open(self.local_file_index, "r")
         for line in fp:
            line = line.replace("\n", "")
            htmls.append(line)
      else:
         print("Could not open the local cloud file index!", self.local_file_index)
         print("cloud file index is", self.cloud_file_index)
      return(htmls)


   def help(self):
      print("""

         Event Manger Classer Helper - This is an admin class that should only be run by the solving node. 

         usage:
         python3 EventManager.py [CMD] [OPTIONS]

         example: (define events for day)
         python3 EventManager.py define_events YYYY_MM_DD -- will define all events for the day

         python3 EventManager.py solve_events YYYY_MM_DD -- will run WMPL on all events for the day 

         python3 EventManager.py solve_events YYYY_MM -- will run WMPL on all events for the month 

         python3 EventManager.py solve_events YYYY -- will run WMPL on all events for year 

         python3 EventManager.py sync_dyna YYYY_MM_DD -- Will download all dyna data (obs & events) for that day, month, year (same YYYY scheme as above)

         python3 EventManager.py cloud_files YYYY_MM_DD -- Will print report of all dyna data (obs & events) for that day, month, year

         python3 EventManager.py event_status YYYY_MM_DD -- Will print report of all dyna data (obs & events) for that day, month, year

         python3 EventManager.py index_html YYYY_MM_DD -- will build index lists for the date range supplied

      """)

if __name__ == "__main__":
   import sys

   if len(sys.argv) < 3:
      print("You need at least 2 args [CMD] [YYYY_MM_DD]. ")
   else:
      el = sys.argv[2].split("_")
      if len(el) == 3:
         EM = EventManager(cmd=sys.argv[1], day=sys.argv[2])
      if len(el) == 2:
         EM = EventManager(cmd=sys.argv[1], month=sys.argv[2])
      if len(el) == 1:
         print("YEAR:", sys.argv[2])
         EM = EventManager(cmd=sys.argv[1], year=sys.argv[2])
      EM.controller()
