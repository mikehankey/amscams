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
      self.obs = None 
      self.event = None
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
      self.kml_file = self.local_event_dir + self.event_id + "-map.kml" 
      self.kml_link = self.kml_file.replace("/mnt/ams2", "")
      if cfe(self.local_event_dir,1) == 0:
         os.makedirs(self.local_event_dir)
      self.cloud_event_dir = self.local_event_dir.replace("/mnt/ams2", "/mnt/archive.allsky.tv")


      if cfe(self.local_event_file) == 1:
         events = load_json_file(self.local_event_file)
      for ev in events:
         self.todays_events.append(ev['event_id'])
         if ev['event_id'] == event_id:
            event = ev
            self.event = ev
      if self.event is not None:
         self.event_start_time = min(event['start_datetime'])
         self.event['event_start_time'] = self.event_start_time
      else:
         event = {}
         event['stations'] = []
         event['files'] = []
         event['start_datetime'] = []
         self.event = event
      if "solve_status" in event: 
         self.solve_status = event['solve_status']
      else:
         self.solve_status = "UNSOLVED"
      self.stations = event['stations']
      self.files = event['files']
      self.start_datetimes = event['start_datetime']
      if "obs" in event:
         self.obs = event['obs']
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
         print("Solution is empty!")

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
      ev_header = self.get_template("FlaskTemplates/EventViewerHeader.html")
      ev_footer = self.get_template("FlaskTemplates/EventViewerFooter.html")
      # Solver failed, or did not run due to missing data or some other reason. 
      # Make a nice debug page so we can :
      #   1) figure out what happened 2) Correct the bad data 3) Re-run/reschedule event run
      print("KML:")
      template = ""
      fp = open(template_file, "r")
      for line in fp:
         template += line

      if self.obs is not None:
         self.make_failed_kml() 
         self.center_lat, self.center_lon = self.center_obs(self.obs)
         traj_iframe = """<iframe width=100% height=450 src="https://archive.allsky.tv/APPS/dist/maps/index.html?mf={:s}&lat={:s}&lon={:s}"></iframe>""".format(self.kml_link, str(self.center_lat), str(self.center_lon))

         obs_html = self.make_obs_html() 
      else:
         obs_html = "<div class='container-lg' style='height: 450'><br><br><h1>Observation data not loaded for this event yet.</h1>"
         obs_table = self.obs_table()
         #obs_html = self.make_obs_html() 
         obs_html += "Waiting for stations to sync needed observations:<ul>\n"
         obs_html += obs_table
         obs_html += "</ul></div>"
         traj_iframe = "Data not loaded."
         self.kml_link = ""

      template = template.replace("{TRAJECTORY_IFRAME}", traj_iframe)
      template = template.replace("{KML_LINK}", self.kml_link)
      template = template.replace("{EVENT:EVENT_ID}", self.event_id)
      template = template.replace("{OBSERVATIONS}", obs_html)
      template = template.replace("{EV_HEADER}", ev_header)
      template = template.replace("{EV_FOOTER}", ev_footer)

      return(template)

   def obs_table(self):
      html = ""
      for i in range(0,len(self.stations)):
         station = self.stations[i]
         obs_file = self.files[i] 
         fn = obs_file.split("/")[-1]
         html += "<li>" + station + " " + fn + "</li>\n"
     
      return(html)
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
      
      html = "<!-- OBS HTML -->\n"
      html += "<div class='container'>\n"
      html += "<div class='row'>\n"
      event = self.event
      if True:

         for i in range(0, len(event['stations'])):
            temp = ""
            file = event['files'][i]
            (f_datetime, cam, f_date_str,fy,fmon,fd, fh, fm, fs) = self.parse_filename(file)
            station_id = event['stations'][i]
            prev_file = file.replace(".mp4", "-prev.jpg")
            year = file[0:4]
            day = file[0:10]
            #link = remote_urls[station_id] + "/meteors/" + station_id + "/" + day + "/" + file + "/"
            if "obs" in event:
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
            html += "<div class='col-md-4'>\n"
            html += "<img class='img-responsive' src=https://archive.allsky.tv/" + station_id + "/METEORS/" + year + "/" + day + "/" + station_id + "_" + prev_file + "><br>\n" + caption
            html += "</div>\n"

      html += "</div>"
      html += "</div>"

      return(html)

   def make_failed_kml(self):
      import simplekml
      import geopy
      from geopy.distance import geodesic
      #VincentyDistance

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
      
      for station in self.obs:
         if station not in used:
            print("ST:", station)
            station_folders[station] = kml.newfolder(name=station)
            for file in self.obs[station]:
               lat,lon,alt = self.obs[station][file]['loc']
               color = colors[pc]
               pnt = station_folders[station].newpoint(name=station, coords=[(lon,lat,alt)])
               pnt.description = station
               pnt.style.labelstyle.color=color
               pnt.style.labelstyle.scale = 1
               pnt.style.iconstyle.icon.href = 'https://maps.google.com/mapfiles/kml/shapes/placemark_circle.png'
               pnt.style.iconstyle.color=color
               pnt.altitudemode = simplekml.AltitudeMode.relativetoground

               used[station] = color


               if "azs" in self.obs[station][file]:
                  azs= self.obs[station][file]['azs']
                  print(station, azs[0])
                  print(station, azs[-1])

                  origin = geopy.Point(lat, lon)
                  destination_start = geodesic(kilometers=300).destination(origin, azs[0])
                  destination_end = geodesic(kilometers=300).destination(origin, azs[-1])
                  print("DEST:", destination_start.latitude, destination_start.longitude)
                  print("DEST:", destination_end.latitude, destination_end.longitude)
                  line_desc = station + " start"
                  linestring = kml.newlinestring(name=line_desc)
                  linestring.coords = [(lon,lat,alt),(destination_start.longitude,destination_start.latitude,alt)]
                  linestring.altitudemode = simplekml.AltitudeMode.relativetoground
                  linestring.extrude = 0

                  line_desc = station + " end"
                  linestring = kml.newlinestring(name=line_desc)
                  linestring.coords = [(lon,lat,alt),(destination_end.longitude,destination_end.latitude,alt)]
                  linestring.altitudemode = simplekml.AltitudeMode.relativetoground
                  linestring.extrude = 0




               else:
                  print(station, "NO MFD", self.obs[station][file].keys())
                  azs = None
               pc += 1

      kml.save(self.kml_file)
      if cfe(self.cloud_event_dir,1) == 0:
         os.makedirs(self.cloud_event_dir)
      cmd = "cp " + self.kml_file + " " + self.cloud_event_dir
      print("CMD:", cmd)
      os.system(cmd)


      print(self.kml_file)
      return(kml.kml())

   def get_template(self, template_file):
      temp = ""
      fp = open(template_file, "r")
      for line in fp:
         temp += line
      return(temp)

#EV = Event(event_id="20210402_013425")
