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



class Events():
   def __init__(self, fv=None):
      self.year = None 
      self.mon = None 
      self.day = None 
      #self.date = year + "_" + month + "_" + day
      self.fv = fv
      self.event_dir = "/mnt/ams2/EVENTS/"
      self.cloud_event_dir = "/mnt/archive.allsky.tv/EVENTS/"

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

      template = template.replace("{TRAJECTORY_IFRAME}", traj_iframe)
      template = template.replace("{ORBIT_IFRAME}", orb_iframe)
      template = template.replace("{STATIONS_IFRAME}", stations_iframe)

      return(template)

   def get_template(self, template_file):
      temp = ""
      fp = open(template_file, "r")
      for line in fp:
         temp += line
      return(temp)
