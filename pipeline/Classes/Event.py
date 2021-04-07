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



class Event():
   def __init__(self, event_id):
      self.event_id = event_id
      self.kml_link = None
      self.orb_link = None
      self.year = event_id[0:4]
      self.month = event_id[4:6]
      self.day = event_id[6:8]
      self.date = self.year + "_" + self.month + "_" + self.day
      self.local_event_dir = "/mnt/ams2/EVENTS/" + self.year + "/" + self.month + "/" + self.day + "/"
      self.local_event_file = self.local_event_dir + self.date + "_ALL_EVENTS.json"
      self.todays_events = []
      self.media = None


      if cfe(self.local_event_file) == 1:
         events = load_json_file(self.local_event_file)
      for ev in events:
         self.todays_events.append(ev['event_id'])
         if ev['event_id'] == event_id:
            event = ev
            self.event = ev
      self.event_start_time = min(event['start_datetime'])
      self.event['event_start_time'] = self.event_start_time
      if "solve_status" in event: 
         self.solve_status = event['solve_status']
      else:
         self.solve_status = "UNSOLVED"
      self.stations = event['stations']
      self.files = event['files']
      self.start_datetimes = event['start_datetime']
      if "obs" in event:
         for key in event['obs'].keys():
            print(key, event['obs'][key])
      if "solution" in event:
         if "traj" in event['solution']:
            self.center_lat, self.center_lon = self.center_obs(event['obs'])
            #self.solution = event['solution']
            self.duration = event['solution']['duration']
            self.trajectory = event['solution']['traj']
            self.orbit = event['solution']['orb']
            self.orb_link = event['solution']['orb']['link']
            self.shower = event['solution']['shower']
            self.rad = event['solution']['rad']
            self.plots = event['solution']['plot']
            self.solve_dir = event['solution']['sol_dir']
            self.cloud_solve_dir = self.solve_dir.replace("/mnt/ams2/", "/mnt/archive.allsky.tv/") 
            self.cloud_url = self.cloud_solve_dir.replace("/mnt/", "https://") 
            self.kml_link = event['solution']['sol_dir'] + self.event_id + "-map.kml"
            self.kml_link =self.kml_link.replace("/mnt/ams2", "")
            self.media = self.get_media_files()

            print("MEDIA:", self.media)

            self.simple_solve = event['solution']['simple_solve']
            self.kml = event['solution']['kml']

            print(self.solve_dir)
            print(self.cloud_url + "index.html")
      else:
         print("Solution is empty!", event['solution'])

   def parse_filename(self, filename):
      fn = filename.split("/")[-1]
      el = fn.split("_")
      fy,fmon,fd, fh, fm, fs, fss, fcam = el 
      el2 = fcam.split("-")
      cam = el2[0]
      date_str = fy + "_" + fmon + "_" + fd + "_" + fh + "_" + fm + "_" + fs
      f_datetime = datetime.datetime.strptime(date_str, "%Y_%m_%d_%H_%M_%S")
      return(f_datetime, cam, date_str,fy,fmon,fd, fh, fm, fs) 


   def get_media_files(self):
      files = glob.glob(self.solve_dir + "*")
      print("FILES:", files)
      media = {}
      media['plots'] = []
      media['jsons'] = []
      media['vids'] = []
      media['txt'] = []

      for file in files:
         if "jpg" in file:
            media['plots'].append(file)
         if "json" in file:
            media['jsons'].append(file)
         if "mp4" in file:
            media['vids'].append(file)
         if "txt" in file:
            media['txt'].append(file)
      return(media)

   def render_fail_template(self,template_file):
      # Solver failed, or did not run due to missing data or some other reason. 
      # Make a nice debug page so we can :
      #   1) figure out what happened 2) Correct the bad data 3) Re-run/reschedule event run
      template = ""
      fp = open(template_file, "r")
      for line in fp:
         template += line
      template = template.replace("{EVENT:EVENT_ID}", self.event_id)
      return(template)


   def render_template(self, template_file):
      if self.solve_status != "SUCCESS":
         template_file = template_file.replace(".html", "Fail.html")
         template = self.render_fail_template(template_file)
         return(template) 
      if "solution" not in self.event:
         template = "No solution for this event." 
         print(self.event)
         return(template)
      else:
         if "traj" not in self.event['solution']:
            template = "Solution for this event is empty."  + str(self.event['solution']) + " " + str(self.event['solve_status'])
            return(template)
      template = ""
      fp = open(template_file, "r")
      for line in fp:
         template += line

      for field in self.event:
         hfield = "{EVENT:" + field.upper() + "}"
         if hfield in template:
            template = template.replace(hfield, str(self.event[field]))
         print(field, hfield)

      for field in self.event['solution']:
         hfield = "{EVENT:SOLUTION:" + field.upper() + "}"
         if hfield in template:
            template = template.replace(hfield, str(self.event['solution'][field]))
         print(field, hfield)

      for field in self.event['solution']['traj']:
         hfield = "{EVENT:SOLUTION:TRAJ:" + field.upper() + "}"
         val = self.event['solution']['traj'][field]
         if "ele" in field:
            val = val / 1000
         if "lat" in field or "lon" in field or "ele" in field:
            val = str(val)[0:6]

         if hfield in template:
            template = template.replace(hfield, str(val))
         print(field, hfield)

      for field in self.event['solution']['orb']:
         hfield = "{EVENT:SOLUTION:ORB:" + field.upper() + "}"
         if hfield in template:
            template = template.replace(hfield, str(self.event['solution']['orb'][field]))
         print(field, hfield)

      # KML IFRAME
      if self.kml_link is not None: 
         kml_iframe = """
              <iframe width=100% height=450 src="https://archive.allsky.tv/APPS/dist/maps/index.html?mf={:s}&lat={:s}&lon={:s}"></iframe>
         """.format(self.kml_link, str(self.center_lat), str(self.center_lon))
      else:
         kml_iframe = "" 
      if self.orb_link is not None: 
         orb_iframe = """
              <iframe width=100% height=450 src="{:s}"></iframe>
         """.format(self.orb_link)
      else:
         orb_iframe = "" 

      template = template.replace("{KML_LINK}", "https://archive.allsky.tv" + self.kml_link)
      template = template.replace("{ORBIT_IFRAME}", orb_iframe)
      template = template.replace("{TRAJECTORY_IFRAME}", kml_iframe)

      # PLOTS
      if self.media is not None:
         plots = "<div class='container' >"
         for plot in self.media['plots']:
            plot_link = plot.replace("/mnt/ams2", "")
            plot_link = "https://archive.allsky.tv" + plot_link
            if "orb" not in plot_link and "ground" not in plot_link:
               plots += "<img width=320 height=240 class='img-thumbnail' src=" + plot_link +">"
         plots += "</div>"
      else:
         print("MEDIA IS NONE!", self.media)
         plots = ""

      template = template.replace("{PLOTS}", plots)

      # OBS
      obs_html = self.make_obs_html()
      template = template.replace("{OBSERVATIONS}", obs_html)

      return(template)

   def center_obs(self,obs_data):
      lats = []
      lons = []
      for st in obs_data:
         for fn in obs_data[st]:
            lat,lon,alt = obs_data[st][fn]['loc']
         lats.append(float(lat))
         lons.append(float(lon))
      return(np.mean(lats),np.mean(lons))

   def make_obs_html(self):
      
      html = "<div>"
      event = self.event
      if True:

         blocks = []
         for i in range(0, len(event['stations'])):
            temp = ""
            file = event['files'][i]
            (f_datetime, cam, f_date_str,fy,fmon,fd, fh, fm, fs) = self.parse_filename(file)
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



#EV = Event(event_id="20210402_013425")
