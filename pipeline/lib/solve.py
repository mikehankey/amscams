#!/usr/bin/python3
import decimal
from decimal import Decimal
import pickle
from lib.PipeUtil import load_json_file, save_json_file, cfe
import matplotlib
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import simplekml
import sys
import simplejson as json
#from lib.REDUCE_VARS import *
#from lib.Video_Tools_cv_pos import *
#from lib.Video_Tools_cv import *
from PIL import ImageFont, ImageDraw, Image, ImageChops
#from lib.VIDEO_VARS import *
#from lib.UtilLib import calc_dist,find_angle, best_fit_slope_and_intercept, calc_radiant
#from lib.MeteorTests import test_objects
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
#from lib.flexCal import flex_get_cat_stars, reduce_fov_pos
#import wmpl.Utils.TrajConversions as trajconv

#from lib.VideoLib import get_masks, find_hd_file_new, load_video_frames, sync_hd_frames, make_movie_from_frames, add_radiant

#from lib.UtilLib import check_running, angularSeparation
#from lib.CalibLib import radec_to_azel, clean_star_bg, get_catalog_stars, find_close_stars, XYtoRADec, HMS2deg, AzEltoRADec, get_active_cal_file

#from lib.ImageLib import mask_frame , stack_frames, preload_image_acc, thumb
#from lib.ReducerLib import setup_metframes, detect_meteor , make_crop_images, perfect, detect_bp, best_fit_slope_and_intercept, id_object, metframes_to_mfd

#from lib.MeteorTests import meteor_test_cm_gaps

import pymap3d as pm

from sympy import Point3D, Line3D, Segment3D, Plane
from boto3.dynamodb.conditions import Key, Attr

import boto3


json_conf = load_json_file("../conf/as6.json")

class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            # wanted a simple yield str(o) in the next line,
            # but that would mean a yield on the line with super(...),
            # which wouldn't work (see my comment below), so...
            return (str(o) for o in [o])
        return super(DecimalEncoder, self).default(o)

def todict(obj, classkey=None):
    if isinstance(obj, dict):
        data = {}
        for (k, v) in obj.items():
            data[k] = todict(v, classkey)
        return data
    elif hasattr(obj, "_ast"):
        return todict(obj._ast())
    elif hasattr(obj, "__iter__") and not isinstance(obj, str):
        return [todict(v, classkey) for v in obj]
    elif hasattr(obj, "__dict__"):
        data = dict([(key, todict(value, classkey)) 
            for key, value in obj.__dict__.items() 
            if not callable(value) and not key.startswith('_')])
        if classkey is not None and hasattr(obj, "__class__"):
            data[classkey] = obj.__class__.__name__
        return data
    else:
        return obj

def get_template(file):
   fp = open(file, "r")
   text = ""
   for line in fp:
      text += line
   return(text)


def event_stats(events):
   single_station = 0
   multi_station = 0
   station_meteors = {}
   for event_id in events:
      event = events[event_id]
      st_set = set(event['stations'])
      stations = []
      for station in st_set:
         stations.append(station)
      if len(stations) == 1:
         st = stations[0]
         single_station += 1

         if st not in station_meteors:
            station_meteors[st] = {}
            station_meteors[st]['single_station'] = 0
            station_meteors[st]['multi_station'] = 0
            station_meteors[st]['total_obs'] = 0
         station_meteors[st]['single_station'] += 1
      else:

         multi_station += 1
         for st in stations:
            if st not in station_meteors:
               station_meteors[st] = {}
               station_meteors[st]['single_station'] = 0
               station_meteors[st]['multi_station'] = 0
               station_meteors[st]['total_obs'] = 0
            station_meteors[st]['multi_station'] += 1

      for st in event['stations']:
         station_meteors[st]['total_obs'] += 1

   return(single_station, multi_station,station_meteors)


def make_event_day_index( day  ):
   year = day[0:4]
   event_year = year
   event_day = day
   station_id = json_conf['site']['ams_id']

   events_dir = "/mnt/ams2/meteor_archive/" + station_id + "/EVENTS/"
   day_file = "/mnt/ams2/meteor_archive/" + station_id + "/EVENTS/" + year + "/" + day + "/" + day + "-events.json"

   if cfe(day_file) == 1:
      # show page for one day of events from one network group (not the global system )
      day_file = "/mnt/ams2/meteor_archive/" + station_id + "/EVENTS/" + year + "/" + day + "/" + day + "-events.json"
      events = load_json_file(day_file)

      network_sites = json_conf['site']['network_sites'].split(",")
      network_sites.append(json_conf['site']['ams_id'])
      net_desc = ""
      for ns in sorted(network_sites):
         if net_desc != "":
            net_desc += ","
         net_desc += ns
      (single_station, multi_station,station_meteors) = event_stats(events)
      out = "<h1>Meteor Nework Report for " + day + "</h1>"
      out += "<P><B>Network Sites:</B> " + net_desc + "<br>"
      out += "<P><B>Total Unique Meteors :</B> " + str(len(events)) + "<br>"
      out += "<P><B>Total Multi Station Meteors :</B> " + str(multi_station) + "<a/><br>"
      out += "<P><B>Total Single Station Meteors :</B> " + str(single_station) + "<br>"
      out += "<table>"
      out += "<tr><td>Station</td><td>Total Observations</td><td>Single Station Meteors</td><td>Multi Station Meteors</td><td>Total Unique Meteors </td></tr>"

      rows_multi = ""
      rows_single = ""

      for st in station_meteors:
         total_meteors = station_meteors[st]['single_station'] + station_meteors[st]['multi_station']
         out += "<tr><td>" + st + "</td><td>" + str(station_meteors[st]['total_obs']) + "</td><td>" + str(station_meteors[st]['single_station']) + "</td><td>" + str(station_meteors[st]['multi_station']) + "</td><td>" + str(total_meteors) + "</td></tr>"
      out += "</table>"
      table_start = "<TABLE border=1>"
      table_start += "<TR><td>Event ID</td><td>Start Time</td><td>Obs</td><td>Solved</td></tr>"
      for event_id in events:

         event = events[event_id]
         img_html = ""
         for i in range(0, len(event['stations'])):
            arc_file = event['arc_files'][i]
            station = event['stations'][i]
            old_file = event['files'][i].split("/")[-1]
            img = event['prev_imgs'][i]
            sol_text = ""
            if arc_file == "pending":
               link = "<div style='float: left'><figure><a href=/pycgi/webUI.py?cmd=goto&old=1&file=" + old_file + "&station_id=" + station + ">"
               obs_desc = event['stations'][i] + "-pending"
            else:
               arc_fn = arc_file.split("/")[-1]
               el = arc_file.split("_")[7]
               other = el.split("-")
               cam_id = other[0]
               obs_desc = event['stations'][i] + "-" + cam_id
               for sol in event['solutions']:
                  type, file, status = sol
                  sol_text += type + " " + str(status) + "<BR>"
               link = "<div style='float: left'><figure><a href=/pycgi/webUI.py?cmd=goto&file=" + arc_fn + "&station_id=" + station + ">"
            img = img.replace("/mnt/ams2/meteor_archive", "")
            img_html += link + "<img src=" + img + "><figcaption>" + obs_desc + " " + event['clip_starts'][i] +  "</a></figcaption></figure></div>"
         #event_dir = "/meteor_archive/" + station_id + "/EVENTS/" + event_year + "/" + event_day + "/" + event_id + "/"
         event_dir = "/EVENTS/" + event_year + "/" + event_day + "/" + event_id + "/"
         elink = "<a href=" + event_dir + event_id + "-report.html>"
         if event['count'] > 1:
            rows_multi += "<tr><td>" + elink + event_id + "</a></td><td>" +  event['event_start_time'] + "</td><td>" +img_html + "</td><td>" + sol_text + "</td></tr>"
         else:
            rows_single += "<tr><td>" + elink + event_id + "</a></td><td>" +  event['event_start_time'] + "</td><td>" +img_html + "</td><td>" + sol_text + "</td></tr>"
      table_end = "</TABLE>"
      out += "<h2>Multi-station Meteors</h2>"
      out += table_start
      out += rows_multi
      out += table_end

      out += "<h2>Single-station Meteors</h2>"
      out += table_start
      out += rows_single
      out += table_end

      ev_index = "/mnt/ams2/meteor_archive/" + station + "/EVENTS/" + event_year + "/" + event_day + "/index.html"
      fp = open(ev_index, "w")
      fp.write( out)
      fp.close()
      was_ev = ev_index.replace("ams2/meteor_archive", "wasabi")
      os.system("cp " + ev_index + " " + was_ev)
      print(ev_index)

def make_prev_img(event_id, station, old_file):
   if "/mnt/" in old_file:
      old_file = old_file.split("/")[-1]
   year,mon,day,hour,min,sec = event_id.split("_")
   dom = event_id[0:10]
   prev_fn = old_file.replace(".json", "-prev-crop.jpg")
   prev_img = "/mnt/ams2/meteor_archive/" + station + "/DETECTS/PREVIEW/" + year + "/" + dom + "/"  + prev_fn
   prev_img_wb = "/" + station + "/DETECTS/PREVIEW/" + year + "/" + dom + "/"  + prev_fn
   return(prev_img, prev_img_wb)


def check_file_status(event_id, station, old_file, arc_file):
   # is it in local archive dir
   # is it in wasbi archive dir
   # do we have a preview image for it
   year,mon,day,hour,min,sec = event_id.split("_")
   dom = event_id[0:10]
   status = {}
   if "/mnt/" in old_file:
      old_file = old_file.split("/")[-1]
   prev_fn = old_file.replace(".json", "-prev-crop.jpg")
   prev_img = "/mnt/ams2/meteor_archive/" + station + "/DETECTS/PREVIEW/" + year + "/" + dom + "/"  + prev_fn
   prev_img_wb = "/mnt/wasabi/" + station + "/DETECTS/PREVIEW/" + year + "/" + dom + "/"  + prev_fn

   wb_arc_file = arc_file.replace("/ams2/meteor_archive", "wasabi")

   if cfe(prev_img) == 1:
      status['preview_image'] = [1, "Preview image exists in local archive."]
   elif cfe(prev_img_wb) == 1:
      status['preview_image'] = [2, "Preview exists in wasabi, but not local archive."]
   else:
      status['preview_image'] = [0, "Preview image not found locally or in wasabi."]

   if arc_file == "pending":
      status['arc_file'] = [0, "Observation has not been archived yet."]
   elif cfe(arc_file) == 1:
      status['arc_file'] = [1, "Arc file found in local archive."  ]
   elif cfe(wb_arc_file) == 1:
      status['arc_file'] = [2, "Arc file found in wasabi."  ]
   else:
      status['arc_file'] = [0, "Arc file not found in local archive or in wasabi." + arc_file]
   return(status)


def obs_html(event_id):
   sync_urls = load_json_file("/home/ams/amscams/conf/sync_urls.json")
   station_id = json_conf['site']['ams_id']
   event_year = event_id[0:4]
   event_day = event_id[0:10]
   event_dir = "/mnt/archive.allsky.tv/EVENTS/" + event_year + "/" + event_day + "/" + event_id + "/"
   events_file = "/mnt/archive.allsky.tv/EVENTS/" + event_year + "/" + event_day + "/" + event_day + "-events.json"
   events_data = load_json_file(events_file)
   event = events_data[event_id]

   out = ""

   if cfe(event_dir, 1) == 0:
      solved = 0
      count = event['count']
      if count > 1:
         out += "This event has not been run yet.<P>"
      else:
         out += "This is a single station event and can't be solved.<P>"
   else:
      solved = 1

   if solved == 0 or solved == 1:
      solutions = event['solutions']
      out += "<h2>Observations</h2>"
      for i in range(0, len(event['stations'])):
         station = event['stations'][i]
         event_start = event['clip_starts'][i]
         old_file = event['files'][i]
         arc_file = event['arc_files'][i]
         if "/mnt/" in old_file:
            old_file_desc = old_file.split("/")[-1]
         if "/mnt/" in arc_file:
            arc_desc = arc_file.split("/")[-1]
         else:
            arc_desc = arc_file
         obs_status = check_file_status(event_id, station, old_file, arc_file)
         prev_img, wb_prev_img = make_prev_img(event_id,station, old_file)

         if arc_desc != 'pending':
            sd_vid = arc_file.replace(".json", "-SD.mp4")
            sd_vid = sd_vid.replace("/mnt/ams2/meteor_archive", "")
            link =  "<a href=" + sd_vid + ">" 
         else:
            link = "<a href=" + url + "></a>" 
         prev_img = prev_img.replace("/mnt/ams2/meteor_archive", "")
         out += "<div style=\"float: left\">" + link
         out += "<figure><img src=" +  prev_img + "><figcaption>" + station + " " + event_start + "</a></figcaption></figure>" 
         #out += "<td>" +  old_file + "</td>"
         #out += "<td>" + obs_status['preview_image'][1] + "<BR>" + obs_status['arc_file'][1] + "</td>"
         out += "</div>"
   out += "<div style=\"clear: both\">" 
   return(out)

def report_html(event_id):
    
   template = get_template("templates/allsky.tv.event.html")


   year = event_id[0:4]
   day = event_id[0:10]
   station_id = json_conf['site']['ams_id']
   event_dir = "/mnt/ams2/meteor_archive/" + station_id + "/EVENTS/" + year + "/" + day + "/" + event_id + "/"
   event_file = event_dir + event_id + ".json" 
   plot_data_file = event_dir + event_id + "-plots.json" 
   job_data_file = event_dir + event_id + ".json" 
   html_report_file = event_file.replace(".json", "-report.html")
   jsons = glob.glob(event_dir + "*report.json")
   print(event_dir + "*report.json")
   print(jsons )
   vida_report = jsons[0]
   vida_data = load_json_file(vida_report)
   job_data = load_json_file(job_data_file)

   vida_plots = []
   scopes = [ "world" , "usa" , "europe" , "asia" , "africa" , "north america" , "south america" ]
   #sol_plots = [ 'los_residuals_all', 'all_spatial_residuals', 'lags_all_stations', 'dist_from_state_vector', 'velocity', 'ground_track', '3D_traj', 'iorbit' ]
   obs_plots = [ 'los_residuals_all', 'all_spatial_residuals'  ]
   orb_plots = [ 'iorbit' ]
   res_plots = [  ]

   traj_plots = [ 'ground_track', '3D_traj', 'velocity', 'lags_all_stations', 'dist_from_state_vector'  ]
   plot_data_file = plot_data_file.replace("/mnt/ams2/meteor_archive", "")

   for obsid in vida_data['observations']:
      res_plots.append("res_station_" + obsid)
   for pl in obs_plots:
      res_plots.append(pl)

   res_plot_html = "<P>"
   traj_plot_html = "<P>"
   orb_plot_html = "<P>"
   other_plot_html = "<P>"
   for plot in res_plots:
      res_plot_html += "<iframe width=950 height=560 src=\"/APPS/plots/index.html?j=" + plot_data_file + "&t=" + plot + "\"></iframe>"
   for plot in traj_plots:
      traj_plot_html += "<iframe width=950 height=560 src=\"/APPS/plots/index.html?j=" + plot_data_file + "&t=" + plot + "\"></iframe>"
   for plot in orb_plots:
      orb_plot_html += "<iframe width=950 height=560 src=\"/APPS/plots/index.html?j=" + plot_data_file + "&t=" + plot + "\"></iframe>"
   


   obs_out = obs_html(event_id)

   obs_file = event_dir + event_id + ".json"
   simple_solve_file = event_dir + event_id + "-simple.json"
   load_json_file(obs_file)
   load_json_file(simple_solve_file)
   report_html = "<h1>Meteor Event Solution Report</h1>"
   report_html += obs_out
   report_html += res_plot_html 
   report_html += "<h2>Event Summary</h2>"
   report_html += "<table border=1 cellpadding=0 cellspacing=0>"
   #report_html += "<tr><td>Event ID</td><td>" + event_id + "</td></tr>"
   report_html += "<tr><td>Event start date time</td><td>" +  job_data['event_utc'][:-3] + " UTC</td></tr>"
   report_html += "<tr><td>Track Start</td><td>" +  str(np.around(np.degrees(vida_data['rbeg_lat']), decimals=3)) + " " +  str(np.around(np.degrees(vida_data['rbeg_lon']), decimals=3)) +  " " +str(np.around(vida_data['rbeg_ele']/1000,decimals=3)) + "</td></tr>"
   report_html += "<tr><td>Track End</td><td>" +  str(np.around(np.degrees(vida_data['rend_lat']), decimals=3)) + " " +  str(np.around(np.degrees(vida_data['rend_lon']), decimals=3)) +  " " + str(np.around(vida_data['rend_ele'])/1000) + "</td></tr>"
   report_html += "<tr><td>Initial Velocity </td><td>" + str(np.around(float(vida_data['v_init'])/1000,decimals=2)) + " km/s</td></tr>"
   report_html += "<tr><td>Average Velocity </td><td>" + str(np.around(float(vida_data['v_avg'])/1000,decimals=2)) + " km/s</td></tr>"

   dl, dv =  vida_data['orbit']['rad_eci']['ra'].split(" = ")
   report_html += "<tr><td>Radiant RA (ECI)</td><td>" + dv + "</td></tr>"
   dl, dv =  vida_data['orbit']['rad_eci']['dec'].split(" = ")
   report_html += "<tr><td >Radiant Dec (ECI)</td><td>" + dv + "</td></tr>"

   report_html += "</table>"
   report_html += traj_plot_html
   report_html += "<h2>Orbit</h2>"


   report_html += "<table border=1 cellpadding=0 cellspacing=0>"

   report_html += "<tr><td >La Sun</td><td>" + vida_data['orbit']['orbit']['la_sun'] + " deg</td></tr>"
   report_html += "<tr><td >a</td><td>" + vida_data['orbit']['orbit']['a'] + " AU </td></tr>"
   report_html += "<tr><td >e</td><td>" + vida_data['orbit']['orbit']['e'] + "</td></tr>"
   report_html += "<tr><td >i</td><td>" + vida_data['orbit']['orbit']['i'] + " deg </td></tr>"
   report_html += "<tr><td >peri</td><td>" + vida_data['orbit']['orbit']['peri'] + " deg </td></tr>"
   report_html += "<tr><td >node</td><td>" + vida_data['orbit']['orbit']['node'] + " deg </td></tr>"
   report_html += "<tr><td >Pi</td><td>" + vida_data['orbit']['orbit']['Pi'] + " deg </td></tr>"
   report_html += "<tr><td >q</td><td>" + vida_data['orbit']['orbit']['q'] + " AU</td></tr>"
   report_html += "<tr><td >f</td><td>" + vida_data['orbit']['orbit']['f'] + " deg</td></tr>"
   report_html += "<tr><td >M</td><td>" + vida_data['orbit']['orbit']['M'] + " deg</td></tr>"
   report_html += "<tr><td >Q</td><td>" + vida_data['orbit']['orbit']['Q'] + " AU</td></tr>"
   report_html += "<tr><td >n</td><td>" + vida_data['orbit']['orbit']['n'] + " deg/day</td></tr>"
   report_html += "<tr><td >T</td><td>" + vida_data['orbit']['orbit']['T'] + " years</td></tr>"
   report_html += "<tr><td >Last perihelion JD</td><td>" + vida_data['orbit']['orbit']['last_peri_jd'] + "</td></tr>"
   report_html += "<tr><td >Tj</td><td>" + vida_data['orbit']['orbit']['Tj'] + "</td></tr>"
   report_html += "<tr><td >JD Reference</td><td>" + str(vida_data['orbit']['orbit']['jd_ref']) + "</td></tr>"
   report_html += "</table>"
   report_html += "<h2>Shower Association</h2>"
   report_html += "<table border=1 cellpadding=0 cellspacing=0>"

   report_html += "<tr><td >IAU No. </td><td>" + str(vida_data['orbit']['shower']['shower_no']) + "</td></tr>"
   report_html += "<tr><td >IAU Code. </td><td>" + str(vida_data['orbit']['shower']['shower_code']) + "</td></tr>"


   report_html += "</table>"
   report_html += orb_plot_html

   vida_report = vida_report.replace("/mnt/ams2", "")
   report_html += "<h2>Detailed Reports</h2>"
   report_html += "<a href=" + vida_report.replace(".json", ".txt") + ">WMPL Report</A> - " 
   kml_report = vida_report.replace(".json", ".kml")
   report_html += "<a href=" + kml_report + ">Event KML</A><BR>" 
   report_html += "<h2>JSON Files</h2>"
   simple_report = event_dir + event_id + "-simple.json" 
   input_report = event_dir + event_id + ".json" 
   report_html += "<a href=" + vida_report + ">WMPL</A> - " 
   report_html += "<a href=" + simple_report + ">Simple Solution</A> - " 
   report_html += "<a href=" + input_report + ">Solver Input File</A> - " 

   template = template.replace("{SOLUTION}", report_html)

   fp = open(html_report_file, "w")
   fp.write(template)
   fp.close() 
   wasabi_dir = event_dir.replace("ams2/meteor_archive", "wasabi")
   cmd = "cp " + event_dir + "*.json "+ wasabi_dir
   print(cmd)
   cmd = "cp " + event_dir + "*.html "+ wasabi_dir
   print(cmd)
   cmd = "cp " + event_dir + "*.txt "+ wasabi_dir
   print(cmd)
   print(html_report_file)

def vida_failed_plots(event_id):
   import redis
   dynamodb = boto3.resource('dynamodb')
   rkey = "E:" + event_id
   try:
      r = redis.Redis("allsky-redis.d2eqrc.0001.use1.cache.amazonaws.com", port=6379, decode_responses=True)
   except:
      r = None
   try:
      event_data = r.get(rkey)
      if event_data is not None:
         event_data = json.loads(event_data)
   except:
      event_data = get_dyna_event(dynamodb, event_id)
   print("EV:", event_data)

   print("V PLOTS FAILED.")
   year = event_id[0:4]
   mon = event_id[4:6]
   day = event_id[6:8]
   station_id = json_conf['site']['ams_id']
   event_dir = "/mnt/archive.allsky.tv/EVENTS/" + year + "/" + mon + "/" + day + "/" + event_id + "/"
   if cfe(event_dir,1) == 0:
      os.makedirs(event_dir)
   local_event_dir = "/mnt/ams2/EVENTS/" + year + "/" + mon + "/" + day + "/" + event_id + "/"
   if cfe(local_event_dir,1) == 0:
      os.makedirs(local_event_dir)
   event_file = event_dir + event_id + "-event.json"
   kml_file = event_dir + event_id + "-obs.kml"
   plot_json_out = event_dir + event_id + "-plots.json"
   print("EF:", event_file)
   if cfe(plot_json_out) == 1 and cfe(event_file) == 0:
      print("PLOTS DONE ALREADY FOR THIS EVENT!", plot_json_out )
      return()

   else:
      print("NO EVENT FILE!", event_file)
      #return()
   if cfe(event_file) == 1: 
      event_file_data = load_json_file(event_file)
   print("EVENT DATA:", event_data)
   dyna_obs_data = {}
   for i in range(0, len(event_data['stations'])):
      st_id = event_data['stations'][i]
      vid = event_data['files'][i]
      obs_key =st_id + "_" + vid
      ev_data = get_dyna_obs(dynamodb, st_id, vid)
      ev_data = json.loads((json.dumps(ev_data, use_decimal=True)))
      dyna_obs_data[obs_key] = ev_data
      dyna_obs_data[obs_key]['lat'] = event_data['lats'][i]
      dyna_obs_data[obs_key]['lon'] = event_data['lons'][i]
   plots = []

   avg_lat = np.mean(event_data['lats'])
   avg_lon = np.mean(event_data['lons'])


   plot = {}
   plot['plot_type'] = "html_block"
   text = """
                <div class="container" style="color: #cccccc">
                <h2 style="color: #cccccc">Event Failure Report for """ + event_id + """ </h2>
                </div>
   """
   plot['plot_html'] = text
   plots.append(plot)

   plot = {}
   plot['plot_type'] = "html_block"
   text = """
                <div class="container" style="color: #cccccc">
                <h2 style="color: #cccccc">Azimuth Start and End Lines</h2>
                </div>
   """
   plot['plot_html'] = text
   plots.append(plot)
   # use iframe for ground track

   track_iframe = "https://archive.allsky.tv/APPS/dist/maps/index.html?mf=/EVENTS/{:s}/{:s}/{:s}/{:s}/{:s}-obs.kml&lat={:s}&lon={:s}&zoom=4".format(year,mon,day,event_id,event_id,str(avg_lat),str(avg_lon))

   plot = {}
   plot['plot_id'] = "ground_track"
   plot['plot_name'] = "Ground Track"
   plot['plot_type'] = "iframe"
   plot['plot_url'] = track_iframe
   plots.append(plot)

   for key in dyna_obs_data:
      plot = {}
      plot['plot_type'] = "html_block"
      az1 = 0
      el1 = 0
      az2 = 0
      el2 = 0
      xs = []
      ys = []
      azs = []
      els = []

      #print(key, len(dyna_obs_data[key]['meteor_frame_data']),len(dyna_obs_data[key]['calib']))
      #print(dyna_obs_data[key])
      frame_rows = " NO FRAME DATA"
      if "meteor_frame_data" in dyna_obs_data[key]:
         if len(dyna_obs_data[key]['meteor_frame_data']) >= 3:
            lat = dyna_obs_data[key]['lat']
            lon = dyna_obs_data[key]['lon']
            az1 = dyna_obs_data[key]['meteor_frame_data'][0][9]
            el1 = dyna_obs_data[key]['meteor_frame_data'][0][10]
            az2 = dyna_obs_data[key]['meteor_frame_data'][-1][9]
            el2 = dyna_obs_data[key]['meteor_frame_data'][-1][10]
            az_lat_lon1 = find_point_from_az_dist(lat,lon,az1,300)
            az_lat_lon2 = find_point_from_az_dist(lat,lon,az2,300)
            start_az_line = [[lat,lon],[az_lat_lon1[0], az_lat_lon1[1]]]
            end_az_line = [[lat,lon],[az_lat_lon2[0], az_lat_lon2[1]]]
            dyna_obs_data[key]['start_az_line'] = start_az_line
            dyna_obs_data[key]['end_az_line'] = end_az_line
         print("AZ1/2:", key, az1,az2)
         frame_rows = '<table class="table table-dark table-striped table-hover td-al-m mb-2 pr-5">'
         frame_rows += """ <thead><tr>
               <th>Datetime</th> <th>#</th> <th>x</th> <th>y</th> <th>int</th>
               <th>ra</th> <th>dec</th> <th>az</th><th>el</th></tr></thead><tbody>
               """
         for row in dyna_obs_data[key]['meteor_frame_data']:
            (dt, frn, x, y, w, h, oint, ra, dec, az, el) = row
            frame_rows += """
               <tr> 
               <td>{:s}</td> <td>{:s}</td> <td>{:s}</td> <td>{:s}</td> <td>{:s}</td> 
               <td>{:0.1f}</td> <td>{:0.1f}</td> <td>{:0.1f}</td><td>{:0.1f}</td></tr>
            """.format (dt, str(frn), str(x), str(y), str(oint), ra, dec, az, el)
            xs.append(x)
            ys.append(y)
            azs.append(az)
            els.append(el)
         frame_rows += "</tbody></table>"
         dyna_obs_data[key]['frame_rows'] = frame_rows
         

      text = """
                <div class="container" style="color: #cccccc">
                <h2 style="color: #cccccc">""" + key + """</h2>
                </div>
      """ 
      plot['plot_html'] = text
      plots.append(plot)

      # add meteor image / canvas
      plot = {}
      plot['plot_name'] = "Meteor image " + obs_key
      plot['plot_type'] = "meteor_image"
      plot['plot_vid'] = dyna_obs_data[key]['sd_video_file']
      plot['media'] = get_meteor_media(dyna_obs_data[key]['station_id'], dyna_obs_data[key]['sd_video_file'])
      plot['station_id'] = dyna_obs_data[key]['station_id']
      plot['plot_xs'] = xs
      plot['plot_ys'] = ys
      if "SD.jpg" in plot['media']:
         plots.append(plot)
      else:
         print("NO SD IMG FOR OBS!")

      # NOW and Frame table 
      plot = {}
      plot['plot_type'] = "html_block"
      if "frame_rows" in dyna_obs_data[key]:
         text = """
                <div class="container" style="color: #cccccc">
                <h2 style="color: #cccccc">Meteor Frame Data</h2> """ + dyna_obs_data[key]['frame_rows'] + """
                </div>
         """ 
      else:
         text = """
                <div class="container" style="color: #cccccc">
                <h2 style="color: #cccccc">Meteor Frame Data is missing!</h2> </div>""" 
      print(text) 
      plot['plot_html'] = text
      plots.append(plot)

      # NOW do the xy position
      plot = {}
      plot['plot_id'] = "Meteor_Position" + "_" + obs_key
      plot['plot_name'] = "Meteor X,Y Position, station " + obs_key
      plot['plot_type'] = "xy_scatter"
      plot['plot_scaling'] = 0
      plot['opts'] = "meteor_pos"
      plot['plot_y_axis_reverse'] = 0
      plot['x_axis_position'] = "bottom"
      plot['y_axis_position'] = "left"
      plot['y_label'] = "Y"
      plot['x_label'] = "X"
      plot['y1_reverse'] = 1
      plot['y1_axis_scaleanchor'] = "x"
      plot['y1_axis_scaleratio'] = 1
      plot['x1_vals'] = xs
      plot['y1_vals'] = ys 
      plots.append(plot)


   fplots = {}
   fplots['plots'] = plots
   print(fplots['plots'])
   save_json_file(plot_json_out, fplots)
   print("Saved:", plot_json_out)

   # make kml for failed obs
   points = {}
   lines = {}
   polys = {}
   for obs_key in dyna_obs_data:
      el = obs_key.split("_")
      st_id = el[0]
      print(obs_key, dyna_obs_data[obs_key]['lat'])
      print(obs_key, dyna_obs_data[obs_key]['lon'])
      #print("FAZ:", obs_key, dyna_obs_data[obs_key]['start_az_line'])
      #print("FAZ2:", obs_key, dyna_obs_data[obs_key]['end_az_line'])
      if "start_az_line" in dyna_obs_data[obs_key]:
         line_key = obs_key + "start"
         lines[line_key] = {}
         lines[line_key]['start_lat'] = dyna_obs_data[obs_key]['start_az_line'][0][0]
         lines[line_key]['start_lon'] = dyna_obs_data[obs_key]['start_az_line'][0][1]
         lines[line_key]['start_alt'] = 100
         lines[line_key]['end_lat'] = dyna_obs_data[obs_key]['end_az_line'][1][0]
         lines[line_key]['end_lon'] = dyna_obs_data[obs_key]['end_az_line'][1][1]
         lines[line_key]['end_alt'] = 100000 
         lines[line_key]['desc'] = "Start " + st_id 

         line_key = obs_key + "end"
         lines[line_key] = {}
         lines[line_key]['start_lat'] = dyna_obs_data[obs_key]['start_az_line'][0][0]
         lines[line_key]['start_lon'] = dyna_obs_data[obs_key]['start_az_line'][0][1]
         lines[line_key]['start_alt'] = 100
         lines[line_key]['end_lat'] = dyna_obs_data[obs_key]['end_az_line'][1][0]
         lines[line_key]['end_lon'] = dyna_obs_data[obs_key]['end_az_line'][1][1]
         lines[line_key]['end_alt'] = 100000 
         lines[line_key]['desc'] = "End " + st_id 


      points[obs_key] = {}
      points[obs_key]['lat'] = dyna_obs_data[obs_key]['lat']
      points[obs_key]['lon'] = dyna_obs_data[obs_key]['lon']
      points[obs_key]['alt'] = 500
      points[obs_key]['desc'] = st_id 

   print("LINES:", lines)
   make_easykml(kml_file, points, lines, polys)


def get_meteor_media(station_id, sd_video_file):
   year = sd_video_file[0:4]
   date = sd_video_file[0:10]
   cloud_dir = "/mnt/archive.allsky.tv/" + station_id + "/METEORS/" + year + "/" + date + "/" 
   root_file = cloud_dir + station_id + "_" + sd_video_file.replace(".mp4", "")
   media_files = glob.glob(root_file + "*")
   media = {}
   for med in media_files:
      if "-" in med:
         el = med.split("-")
         ext1 = el[-1]
         ext2 = el[-2]
         media[ext1] = med.replace("/mnt/", "https://")
   return(media)

def get_dyna_event(dynamodb, event_id):
   if dynamodb is None:
      dynamodb = boto3.resource('dynamodb')


   table = dynamodb.Table('x_meteor_event')
   event_day = event_id[0:8]
   y = event_day[0:4]
   m = event_day[4:6]
   d = event_day[6:8]
   event_day = y + "_" + m + "_" + d

   try:
       response = table.get_item(Key={'event_day': event_day, 'event_id': event_id})
   except ClientError as e:
       print(e.response['Error']['Message'])
   else:
       event_data = json.loads(json.dumps(response['Item']), parse_float=Decimal)

   return(event_data)


def get_dyna_obs(dynamodb, station_id, sd_video_file):
   if dynamodb is None:
      dynamodb = boto3.resource('dynamodb')
   table = dynamodb.Table('meteor_obs')
   response = table.query(
      KeyConditionExpression='station_id = :station_id AND sd_video_file = :sd_video_file',
      ExpressionAttributeValues={
         ':station_id': station_id,
         ':sd_video_file': sd_video_file,
      }
   )
   if len(response['Items']) > 0:
      return(response['Items'][0])
   else:
      return(None)



def get_file_info(file):
   cur_time = int(time.time())
   st = os.stat(file)
   size = st.st_size
   mtime = st.st_mtime
   tdiff = cur_time - mtime
   tdiff = tdiff / 60
   return(size, tdiff)

def vida_plots(event_id):
   year = event_id[0:4]
   mon = event_id[4:6]
   day = event_id[6:8]

   
   station_id = json_conf['site']['ams_id']
   event_dir = "/mnt/archive.allsky.tv/EVENTS/" + year + "/" + mon + "/" + day + "/" + event_id + "/"
   local_event_dir = "/mnt/ams2/EVENTS/" + year + "/" + mon + "/" + day + "/" + event_id + "/"
   event_file = event_dir + event_id + "-event.json" 
   plot_json_out = event_dir + event_id + "-plots.json" 
   print("EF:", event_file)
   if cfe(event_file) == 1:
      if cfe(plot_json_out) == 1:
         ev_size, ev_age = get_file_info(event_file)
         plt_size, plt_age = get_file_info(plot_json_out)
         if plt_age < ev_age:
            print("PLOTS DONE ALREADY FOR THIS EVENT!", plt_age, ev_age)
            return()

   else:
      print("NO EVENT FILE!", event_file)
      return()

   event_data = load_json_file(event_file)

   # check if this has been done already. 



   event_obs = {}
   for station_id in event_data['obs']:
       for vid_file in event_data['obs'][station_id]:
          evd = event_data['obs'][station_id][vid_file]
          obs = {}
          obs['station_id'] = station_id
          obs['sd_video_file'] = vid_file
          obs['loc'] = evd['loc']
          obs['calib'] = evd['calib']
          obs['times'] = evd['times']
          obs['fns'] = evd['fns']
          obs['xs'] = evd['xs']
          obs['ys'] = evd['ys']
          obs['azs'] = evd['azs']
          obs['els'] = evd['els']
          obs['ras'] = evd['ras']
          obs['decs'] = evd['decs']
          obs['ints'] = evd['ints']
          obs['gc_azs'] = evd['gc_azs']
          obs['gc_els'] = evd['gc_els']
          event_obs[station_id] = obs

   jsons = glob.glob(event_dir + "*.json")
   print(event_dir + "*.json")
   print(jsons )
   print(event_dir)
   print(jsons)
   vida_report = jsons[0]
   pickle_file = local_event_dir + event_id + "_trajectory.pickle"
   cloud_pickle_file = event_dir + event_id + "_trajectory.pickle"
   print("P:", pickle_file)
   if cfe(pickle_file) == 0 :
      if cfe(cloud_pickle_file) == 1:
         if cfe(local_event_dir,1) == 0:
            os.makedirs(local_event_dir)
         os.system("cp " + cloud_pickle_file + " " + pickle_file)
   if cfe(pickle_file) == 1 :
      with open(pickle_file, 'rb') as handle:
         vida_data = pickle.load(handle)
         print(vida_report)
   elif cfe(cloud_pickle_file) == 1 :
         with open(cloud_pickle_file, 'rb') as handle:
            vida_data = pickle.load(handle)
            print(vida_report)

   else:
      print("NO PICKLE FILE:", local_event_dir)
      exit()

   vida_data = todict(vida_data)
   vida_file = local_event_dir + event_id + "_trajectory.json"
   vida_cloud_file = event_dir + event_id + "_trajectory.json"

   json_data = json.dumps(vida_data, default=convert)
   #save_json_file(vida_file, json_data)
   #os.system("cp " + vida_file + " " + vida_cloud_file)
   print(vida_data['orbit'].keys())

   #build arrays for res error plots (per-station res, all station res, all station ang res)



   plot_data = {}
   basic_colors = ['red', 'blue', 'green', 'orange', 'white']
   basic_shapes = ['square-dot', 'circle-dot', 'triangle-up-dot']
   bc = 0
   bs = 0
   #vida_data = load_json_file(vida_report)
   # build orbit plot / iframe
   qs = vida_data['orbit']
   print(qs)
   try:
      orbit_iframe = "https://orbit.allskycams.com/index_emb.php?name={:s}&&epoch={:s}&a={:s}&M={:s}&e={:s}&I={:s}&Peri={:s}&Node={:s}&P={:s}&q={:s}&T={:s}".format( str(event_id), str(qs['jd_ref']), str(qs['a']), str(math.degrees(qs['mean_anomaly'])), str(qs['e']), str(math.degrees(qs['i'])), str(math.degrees(qs['peri'])), str(math.degrees(qs['node'])), str(qs['T']), str(qs['q']), str(qs['jd_ref']))
   except:
      orbit_iframe = "" 
   orbit_iframe = orbit_iframe.replace(" ", "")

   observer_data = {}
   obs_points = []
   obs_vectors= []
   obs_names= []

   for obs_data in vida_data['observations']:
      print("OBS DATA KEYS:", obs_data.keys())
      print("OBS DATA:", obs_data)
      obs_key = obs_data['station_id']
      if obs_key not in observer_data:
         observer_data[obs_key] = {}
         lon = np.degrees(obs_data['lon'])
         lat = np.degrees(obs_data['lat'])
         alt = obs_data['ele']
         print(lat,lon,alt)
         #lat = vida_data['observations'][obs_key]['station_info'][3].replace(" ", "")
         #alt = vida_data['observations'][obs_key]['station_info'][4].replace(" ", "")
         meas1 = np.degrees(obs_data['meas1'][0])
         meas2 = np.degrees(obs_data['meas2'][0])
         start_el = np.degrees(obs_data['model_elev'][0])
         start_az = np.degrees(obs_data['model_azim'][0])
         start_el = np.degrees(obs_data['model_elev'][0])
         end_az = np.degrees(obs_data['model_azim'][-1])
         end_el = np.degrees(obs_data['model_elev'][-1])
         observer_data[obs_key]['location'] = [lat,lon,alt]
         obs_points.append([lat,lon])
         obs_names.append(obs_key)
         observer_data[obs_key]['start_az_el'] = [start_az,start_el]
         observer_data[obs_key]['end_az_el'] = [end_az,end_el]
      if obs_key not in plot_data:
         plot_data[obs_key] = {}
         plot_data[obs_key]['xs'] = []
         plot_data[obs_key]['ys'] = []
         plot_data[obs_key]['hres'] = []
         plot_data[obs_key]['vres'] = []
         plot_data[obs_key]['ang_res'] = []
         plot_data[obs_key]['lag'] = []
         plot_data[obs_key]['velocity'] = []
         plot_data[obs_key]['length'] = []
         plot_data[obs_key]['height'] = []
         plot_data[obs_key]['state_vect_dist'] = []
         plot_data[obs_key]['points'] = []
         plot_data[obs_key]['az_el'] = []
         plot_data[obs_key]['ra_dec'] = []
         plot_data[obs_key]['time_data'] = []
      for i in range(0, len(obs_data['model_azim'])-1 ):
         print("HRES:", obs_data['h_residuals'][i])
         print("HRES:", obs_data['v_residuals'][i])
         pd = obs_data
         plot_data[obs_key]['xs'].append(np.degrees(pd['model_azim'][i]))
         plot_data[obs_key]['ys'].append(np.degrees(pd['model_elev'][i]))
         plot_data[obs_key]['hres'].append(pd['h_residuals'][i])
         plot_data[obs_key]['vres'].append(pd['v_residuals'][i])
         plot_data[obs_key]['ang_res'].append(np.degrees(pd['ang_res'][i])*60)
         plot_data[obs_key]['lag'].append(pd['lag'][i])
         plot_data[obs_key]['velocity'].append(pd['velocities'][i]/1000)
         plot_data[obs_key]['length'].append(pd['length'][i])
         plot_data[obs_key]['height'].append(pd['model_ht'][i])
         print("H:", pd['model_ht'][i])
         plot_data[obs_key]['time_data'].append(pd['time_data'][i])
         plot_data[obs_key]['state_vect_dist'].append(pd['state_vect_dist'][i]/1000)
         plot_data[obs_key]['points'].append((np.degrees(pd['model_lat'][i]),np.degrees(pd['model_lon'][i]), np.degrees(pd['model_ht'][i])))
         plot_data[obs_key]['az_el'].append((np.degrees(pd['model_azim'][i]),np.degrees(pd['model_elev'][i])))
         plot_data[obs_key]['ra_dec'].append((np.degrees(pd['model_ra'][i]),np.degrees(pd['model_dec'][i])))

   plots = []

   plot = {}
   plot['plot_type'] = "html_block"
   text = """ 
                <div class="container" style="color: #cccccc">
                <h1 style="color: #cccccc">AllSky7 Event - """ + event_id + """</h1>
                </div>
   """
   plot['plot_html'] = text 
   plots.append(plot)

   plot = {}
   plot['plot_type'] = "html_block"
   text = """
                <div class="container" style="color: #cccccc">
                <h2 style="color: #cccccc">Orbit </h2>
                </div>
   """
   plot['plot_html'] = text
   plots.append(plot)


   plot = {}
   plot['plot_id'] = "iorbit"
   plot['plot_name'] = "Orbit"
   plot['plot_type'] = "iframe"
   plot['plot_url'] = orbit_iframe
   plots.append(plot)

   track_iframe = "https://archive.allsky.tv/APPS/dist/maps/index.html?mf=/EVENTS/{:s}/{:s}/{:s}/{:s}/{:s}-map.kml&lat={:s}&lon={:s}&zoom=4".format(year,mon,day,event_id,event_id,str(np.degrees(vida_data['rbeg_lat'])),str(np.degrees(vida_data['rbeg_lon'])))

   # make 2D observer and ground track map
   if False:
      plot = {}
      plot['plot_id'] = "ground_track"
      plot['scope'] = "europe"
      plot['plot_name'] = "Ground Track"
      plot['plot_type'] = "map"
      plot['x_label'] = "Latitude"
      plot['y_label'] = "Longitude"
      plot['points'] = obs_points
      plot['point_names'] = obs_names 
      plot['lines'] = obs_vectors
 
      ts_lat = float(np.degrees(vida_data['rbeg_lat']))
      ts_lon = float(np.degrees(vida_data['rbeg_lon']))
      te_lat = float(np.degrees(vida_data['rend_lat']))
      te_lon = float(np.degrees(vida_data['rend_lon']))
 
      plot['lines'].append((ts_lat,ts_lon,te_lat,te_lon))

      plots.append(plot)
   # use iframe for ground track
   track_iframe = "https://archive.allsky.tv/APPS/dist/maps/index.html?mf=/EVENTS/{:s}/{:s}/{:s}/{:s}/{:s}-map.kml&lat={:s}&lon={:s}&zoom=4".format(year,mon,day,event_id,event_id,str(np.degrees(vida_data['rbeg_lat'])),str(np.degrees(vida_data['rbeg_lon'])))
   plot = {}
   plot['plot_type'] = "html_block"
   text = """
                <div class="container" style="color: #cccccc">
                <h2 style="color: #cccccc">Ground Track</h2>
                </div>
   """
   plot['plot_html'] = text
   plots.append(plot)

   plot = {}
   plot['plot_id'] = "ground_track"
   plot['plot_name'] = "Ground Track"
   plot['plot_type'] = "iframe"
   plot['plot_url'] = track_iframe
   plots.append(plot)

   plot = {}
   plot['plot_type'] = "html_block"
   text = """
                <div class="container" style="color: #cccccc">
                <h2 style="color: #cccccc">Event Plots</h2>
                </div>
   """
   plot['plot_html'] = text
   plots.append(plot)

   # make 3D observer and ground track map
   plot = {}
   plot['plot_id'] = "3D_traj"
   plot['plot_name'] = "3D Trajectory"
   plot['plot_type'] = "3Dmap"
   plot['x_label'] = "Latitude"
   plot['y_label'] = "Longitude"
   plot['z_label'] = "Altitude"
   plot['points'] = obs_points
   plot['point_names'] = obs_names
   #plot['lines'] = obs_vectors

   ts_lat = float(np.degrees(vida_data['rbeg_lat']))
   ts_lon = float(np.degrees(vida_data['rbeg_lon']))
   ts_alt = float(vida_data['rbeg_ele']/1000)

   te_lat = float(np.degrees(vida_data['rend_lat']))
   te_lon = float(np.degrees(vida_data['rend_lon']))
   te_alt = float(vida_data['rend_ele']/1000)

   print("ALT:", ts_alt, te_alt)

   plot['lines'] = []
   plot['line_names'] = []
   plot['line_colors'] = []
   plot['lines'].append((ts_lat,ts_lon,ts_alt,te_lat,te_lon,te_alt))
   plot['line_names'].append("meteor")
   #plot['line_colors'].append("red")
   cc = 0
   for i in range(0, len(obs_points)):
      lat,lon = obs_points[i]
      plot['lines'].append((lat,lon,0,ts_lat,ts_lon,ts_alt))
      plot['lines'].append((lat,lon,0,te_lat,te_lon,te_alt))
      plot['line_names'].append("start")
      plot['line_names'].append("end")
      #plot['line_names'].append(obs_names[i] + " start")
      #plot['line_names'].append(obs_names[i] + " end")
      #plot['line_colors'].append('green')
      #plot['line_colors'].append('orange')

   plots.append(plot)

    
   # make the observed vs radiant LoS Residuals, all stations plot 
   plot = {}
   plot['plot_id'] = "los_residuals_all"
   plot['plot_name'] = "Observed vs. Radiant LoS Residuals, all stations"
   plot['x_label'] = "Time (s)"
   plot['y_label'] = "Angle (arc min)"
   series_c = 1
   for obs_key in plot_data:
      x_field = "x" + str(series_c) + "_vals"
      y_field = "y" + str(series_c) + "_vals"
      plot[x_field] = []
      plot[y_field] = plot_data[obs_key]['ang_res']
      plot['plot_type'] = "xy_scatter"
      x_data_label_field = "x" + str(series_c) + "_data_label"
      rmsd_ang = ""
      rmsd_ang = find_avg_abs_val(plot_data[obs_key]['ang_res'])
      plot[x_data_label_field] = obs_key + ", RMSD = " + str(rmsd_ang)
      for t in range(0, len(plot_data[obs_key]['ang_res'])):
         plot[x_field].append(t/25)
      series_c += 1
   plots.append(plot)

   # make the All Spatial Residuals By Height 
   plot = {}
   plot['plot_id'] = "all_spatial_residuals"
   plot['plot_name'] = "All spatial residuals"
   plot['x_label'] = "Total deviation (m)"
   plot['y_label'] = "Height (km)"
   series_c = 1
   for obs_key in plot_data:
      x_field = "x" + str(series_c) + "_vals"
      y_field = "y" + str(series_c) + "_vals"
      plot[x_field] = []
      plot[y_field] = plot_data[obs_key]['height']
      plot['plot_type'] = "xy_scatter"
      x_data_label_field = "x" + str(series_c) + "_data_label"
      avg_err = np.around( find_avg_abs_val(plot_data[obs_key]['vres'])  + find_avg_abs_val(plot_data[obs_key]['hres']), decimals=2)

      plot[x_data_label_field] = obs_key + ", RMSD = " + str(avg_err) + " m"
      for i in range(0, len(plot_data[obs_key]['vres'])):
         plot[x_field].append(plot_data[obs_key]['vres'][i]  + plot_data[obs_key]['hres'][i])
      series_c += 1
   plots.append(plot)

   # make the Lags, all station 
   plot = {}
   plot['plot_id'] = "lags_all_stations"
   plot['plot_name'] = "Lags, all stations"
   plot['x_label'] = "Lag (m)"
   plot['y_label'] = "Time (s)"
   series_c = 1
   plot['plot_y_axis_reverse'] = 1
   times = {}
   for obs_key in plot_data:
      x_field = "x" + str(series_c) + "_vals"
      y_field = "y" + str(series_c) + "_vals"
      x_line_on_field = "x" + str(series_c) + "_line_on"
      x_sym_field = "x" + str(series_c) + "_symbol_size"
      plot[x_field] = plot_data[obs_key]['lag']
      plot[y_field] = []
      #plot['plot_type'] = "xy_scatter"
      x_data_label_field = "x" + str(series_c) + "_data_label"
      plot[x_sym_field] = "4"
      plot[x_line_on_field] = 1

      plot[x_data_label_field] = obs_key 
      for i in range(0, len(plot_data[obs_key]['lag'])):
         lt = i/25
         plot[y_field].append(i/25)
         times[lt] = 1
      series_c += 1

   # add trend line for jac fit
   # Plot the Jacchia fit on all observations

   time_all = []
   for key in times:
      time_all.append(key)
   time_all = sorted(time_all)

   time_jacchia = np.linspace(np.min(time_all), np.max(time_all), 1000)
   jacc_x = jacchiaLagFunc(time_jacchia, vida_data['jacchia_fit'][0], vida_data['jacchia_fit'][1])

   tx1_vals = []
   ty1_vals = []
   for i in range(0, len(time_jacchia)):
      ty1_vals.append(float(time_jacchia[i]))
      tx1_vals.append(float(jacc_x[i]))

   plot['tx1_vals'] = tx1_vals 
   plot['ty1_vals'] = ty1_vals 
   plot['tx1_data_label'] = "Jacchia fit" 

   plots.append(plot)

   # make the Distance from state vector, all station 
   plot = {}
   plot['plot_id'] = "dist_from_state_vector"
   plot['plot_name'] = "Distance from state vector, Time residuals = "
   plot['x_label'] = "Distance from state vector (km)"
   plot['y_label'] = "Time (s)"
   series_c = 1
   plot['plot_y_axis_reverse'] = 1
   all_data = []
   for obs_key in plot_data:
      x_field = "x" + str(series_c) + "_vals"
      y_field = "y" + str(series_c) + "_vals"
      x_line_on_field = "x" + str(series_c) + "_line_on"
      x_sym_field = "x" + str(series_c) + "_symbol_size"
      plot[x_field] = plot_data[obs_key]['state_vect_dist']
      plot[y_field] = plot_data[obs_key]['time_data']
      plot['plot_type'] = "xy_scatter"

      for data in plot[x_field] :
         all_data.append(data)
      x_data_label_field = "x" + str(series_c) + "_data_label"
      #plot[x_sym_field] = "4"
      plot[x_line_on_field] = 1

      plot[x_data_label_field] = obs_key
      series_c += 1

   # Add the fitted velocity line

   # Get time data range
   t_min = min([np.min(plot_data[obs_key]['time_data']) for obs_key in plot_data])
   t_max = max([np.max(plot_data[obs_key]['time_data']) for obs_key in plot_data])
   t_range = np.linspace(t_min, t_max, 100)

   tx1_vals = lineFunc(t_range, vida_data['velocity_fit'][0], vida_data['velocity_fit'][1])/1000
   ty1_vals = t_range

   ftx1_vals = []
   fty1_vals = []
   for i in range(0, len(tx1_vals)):
      fty1_vals.append(float(ty1_vals[i]))
      ftx1_vals.append(float(tx1_vals[i]))

   plot['tx1_vals'] = ftx1_vals 
   plot['ty1_vals'] = fty1_vals 
   plot['tx1_data_label'] = "Fit" 


   plots.append(plot)

   # make veloity all stations
   plot = {}
   plot['plot_id'] = "velocity"
   plot['plot_name'] = "Velocity"
   plot['x_label'] = "Velocity (km/s)"
   plot['y_label'] = "Time (s)"
   series_c = 1
   plot['plot_y_axis_reverse'] = 1
   all_data = []
   for obs_key in plot_data:
      x_field = "x" + str(series_c) + "_vals"
      y_field = "y" + str(series_c) + "_vals"
      x_line_on_field = "x" + str(series_c) + "_line_on"
      #x_sym_field = "x" + str(series_c) + "_symbol_size"
      plot[x_field] = plot_data[obs_key]['velocity']
      plot[y_field] = plot_data[obs_key]['time_data']
      #plot['plot_type'] = "xy_scatter"

      for data in plot[x_field] :
         all_data.append(float(data))
      x_data_label_field = "x" + str(series_c) + "_data_label"
      #plot[x_sym_field] = "4"
      plot[x_line_on_field] = 0

      plot[x_data_label_field] = obs_key
      series_c += 1

   # Get time data range
   t_min = min([np.min(plot_data[obs_key]['time_data']) for obs_key in plot_data])
   t_max = max([np.max(plot_data[obs_key]['time_data']) for obs_key in plot_data])
   t_range = np.linspace(t_min, t_max, 100)

   time_jacchia = np.linspace(t_min, t_max, 1000)
   jacc_x = jacchiaVelocityFunc(time_jacchia, vida_data['jacchia_fit'][0], vida_data['jacchia_fit'][1], float(vida_data['v_init']))/1000

   tx1_vals = []
   ty1_vals = []
   for i in range(0, len(time_jacchia)):
 
      ty1_vals.append(float(time_jacchia[i]))
      tx1_vals.append(float(jacc_x[i]) )

   plot['tx1_vals'] = tx1_vals
   plot['ty1_vals'] = ty1_vals
   plot['tx1_data_label'] = "Jacchia fit"



   plots.append(plot)
  
   plot = {}
   plot['plot_type'] = "html_block"
   text = """
                <div class="container" style="color: #cccccc">
                <h2 style="color: #cccccc">Observations</h2>
                </div>
   """
   plot['plot_html'] = text
   plots.append(plot)

   # make the spatial res graph for each station
   for obs_key in plot_data:
      # figure out y vals (time)
      event_obs_data = event_obs[obs_key]
 
      plot = {}
      plot['plot_type'] = "html_block"
      text = """
                <div class="container" style="color: #cccccc">
                <h3 style="color: #cccccc">""" + event_obs_data['station_id'] + """</h3>
                </div>
      """
      plot['plot_html'] = text
      plots.append(plot)

      # add meteor image / canvas
      plot = {}
      plot['plot_name'] = "Meteor image " + obs_key
      plot['plot_type'] = "meteor_image"
      plot['plot_vid'] = event_obs_data['sd_video_file']
      plot['station_id'] = event_obs_data['station_id']
      plot['plot_xs'] = event_obs_data['xs']
      plot['plot_ys'] = event_obs_data['ys']
      plots.append(plot)



      # NOW do the xy position
      plot = {}
      plot['plot_id'] = "Meteor_Position" + "_" + obs_key
      #plot['plot_type'] = "xy_scatter"
      #plot['plot_subtype'] = "station_res_err"
      plot['plot_name'] = "Meteor X,Y Position, station " + obs_key
      plot['plot_type'] = "xy_scatter"
      plot['plot_scaling'] = 0
      plot['opts'] = "meteor_pos"
      plot['plot_y_axis_reverse'] = 0
      plot['x_axis_position'] = "bottom"
      plot['y_axis_position'] = "left"
      plot['y_label'] = "Y"
      plot['x_label'] = "X"
      plot['y1_reverse'] = 1
      plot['y1_axis_scaleanchor'] = "x"
      plot['y1_axis_scaleratio'] = 1 
      #avg_h_res = find_avg_abs_val(plot_data[obs_key]['hres'])
      #avg_v_res = find_avg_abs_val(plot_data[obs_key]['vres'])
      #plot['x1_data_label'] = obs_key + " Horizontal, RMSD = " + str(avg_h_res) + " m"
      #plot['x2_data_label'] = obs_key + " Vertical, RMSD = " + str(avg_v_res) + " m"
      #plot['x1_symbol'] = ""
      #plot['x2_symbol'] = ""
      #plot['x1_symbol_size'] = "3"
      #plot['x2_symbol_size'] = "3"
      #plot['x1_color'] = basic_colors[0]
      #plot['x2_color'] = basic_colors[1]
      plot['x1_vals'] = event_obs_data['xs']
      plot['y1_vals'] = event_obs_data['ys']
      #plot['x1_vals'] = plot_data[obs_key]['xs']
      #plot['y1_vals'] = plot_data[obs_key]['ys']
      plot['x2_vals'] = []
      plot['y2_vals'] = []
      if bc >= len(basic_colors):
         bc = 0
      color_idx = bc
      # figure out y vals (time)

      #plot['x1_symbol'] = basic_shapes[0]
      #plot['x2_symbol'] = basic_shapes[1]
      plots.append(plot)
      print("EVOBS", event_obs_data) 
      # first do the res
      plot = {}
      plot['plot_id'] = "res_station" + "_" + obs_key
      #plot['plot_type'] = "xy_scatter"
      #plot['plot_subtype'] = "station_res_err"
      plot['plot_name'] = "Residuals, station " + obs_key
      plot['plot_scaling'] = 0
      plot['plot_y_axis_reverse'] = 0
      plot['x_axis_position'] = "bottom"
      plot['y_axis_position'] = "left"
      plot['y_label'] = "Residuals (m)"
      plot['x_label'] = "Time (s)"
      avg_h_res = find_avg_abs_val(plot_data[obs_key]['hres'])
      avg_v_res = find_avg_abs_val(plot_data[obs_key]['vres'])
      plot['x1_data_label'] = obs_key + " Horizontal, RMSD = " + str(avg_h_res) + " m"
      plot['x2_data_label'] = obs_key + " Vertical, RMSD = " + str(avg_v_res) + " m"
      #plot['x1_symbol'] = ""
      #plot['x2_symbol'] = ""
      #plot['x1_symbol_size'] = "3"
      #plot['x2_symbol_size'] = "3"
      #plot['x1_color'] = basic_colors[0]
      #plot['x2_color'] = basic_colors[1]
      plot['x1_vals'] = []
      plot['y1_vals'] = plot_data[obs_key]['hres']
      plot['x2_vals'] = []
      plot['y2_vals'] = plot_data[obs_key]['vres']
      if bc >= len(basic_colors):
         bc = 0
      color_idx = bc

      for i in range(0, len(plot['y1_vals'])):
         plot['x1_vals'].append(i/25)
         plot['x2_vals'].append(i/25)

      plot['x1_symbol'] = basic_shapes[0]
      plot['x2_symbol'] = basic_shapes[1]

      plots.append(plot)


   bs = bs + 1
   fplots = {}
   fplots['plots'] = plots
   save_json_file(plot_json_out, fplots)
   print("SAVED:", plot_json_out)
   print("saved:", vida_file)

def convert(o):
    print (type(o))
    if isinstance(o, numpy.int64): return int(o)  
    if isinstance(o, numpy.uint8): return int(o)  
    if isinstance(o, numpy.bool_): return int(o)  
    if isinstance(o, datetime.datetime): return o.strftime("%Y-%m-%d %H:%M:%S")  
    raise TypeError

def lineFunc(x, m, k):
    """ A line function.

    Arguments:
        x: [float] Independant variable.
        m: [float] Slope.
        k: [float] Intercept.

    Return:
        y: [float] Line evaluation.
    """

    return m*x + k


def jacchiaLagFunc(t, a1, a2):
    ### TAKEN FROM WMPL ###
    """ Jacchia (1955) model for modeling lengths along the trail of meteors, modified to fit the lag (length
        along the trail minus the linear part, estimated by fitting a line to the first part of observations,
        where the length is still linear) instead of the length along the trail.

    Arguments:
        t: [float] time in seconds at which the Jacchia function will be evaluated
        a1: [float] 1st acceleration term
        a2: [float] 2nd acceleration term

    Return:
        [float] Jacchia model defined by a1 and a2, estimated at point in time t

    """

    return -np.abs(a1)*np.exp(np.abs(a2)*t)

def jacchiaVelocityFunc(t, a1, a2, v_init):
    ### TAKEN FROM WMPL ###
    """ Derivation of the Jacchia (1955) model, used for calculating velocities from the fitted model.

    Arguments:
        t: [float] Time in seconds at which the Jacchia function will be evaluated.
        a1: [float] 1st decelerationn term.
        a2: [float] 2nd deceleration term.
        v_init: [float] Initial velocity in m/s.
        k: [float] Initial offset in length.

    Return:
        [float] velocity at time t

    """

    print("T", t)
    print("A1", a1)
    print("A2", a2)
    print("VINIT", v_init)
    return v_init - np.abs(a1*a2)*np.exp(np.abs(a2)*t)




def find_avg_abs_val(values):
   abs_vals = []
   for val in values:
      abs_vals.append(abs(val))
   avg_val = np.mean(abs_vals)
   return(np.around(avg_val,decimals=2))


def run_detects(day):
   event_day = day
   event_year = day[0:4]
   network = json_conf['site']['network_sites'].split(",")
   this_station = json_conf['site']['ams_id']
   station = this_station
   network.append(station)
   detect_index = {}
   solved_events = []
   for st in sorted(network):
      data_file = "/mnt/ams2/meteor_archive/" + st + "/DETECTS/MI/" + event_year + "/" + event_day + "-meteor_index.json"
      event_dir = "/mnt/ams2/meteor_archive/" + st + "/EVENTS/" + event_year + "/" + event_day + "/"
      print(data_file)
      if cfe(event_dir, 1) == 1:
         event_files = glob.glob(event_dir + "/*")
         for ef in sorted(event_files):
            if cfe(ef,1) == 1:
               solved_events.append(ef)
      arc_station_dir = "/mnt/ams2/meteor_archive/" + st + "/"
      print("DATA FILE:", data_file)
      if cfe(data_file) == 1:
         data = load_json_file(data_file)
      else:
         data = False
      if data != 0 and data is not False:
         if day in data:
            detect_index[st] = data[day]
      else:
         print("Could not open meteor index.json!")

   files = []
   files_station = {}
   events = {}
   print("SOLVED EVENTS:", solved_events)

   for st in detect_index:
      print(st, len(detect_index[st]))
      for file in detect_index[st]:
         event, events = find_event(file, st, detect_index[st][file], events, solved_events)
        
   event_times = [] 
   for event_id in events:
      event_times.append((event_id, events[event_id]['event_start_time']))
   
   events_sorted = sorted(event_times, key=lambda x: x[1], reverse=False)
   ec = 1
   final_events = {}
   for data in events_sorted:
      event_id, event_time = data
      event = events[event_id]
      station_count = len(set(events[event_id]['stations']))
      prev_imgs = prev_img_from_file(None,None,events[event_id]['files'] ,events[event_id]['stations'])
      event_time_id, solutions = check_if_solved(events[event_id], solved_events)
      event['prev_imgs'] = prev_imgs
      event['event_id'] = event_time_id
      event['count'] = station_count
      event['solutions'] = solutions
      print(ec, event_time_id, station_count, events[event_id]['event_start_time'], events[event_id]['stations'], events[event_id]['files'], solutions )
      final_events[event_time_id] = event
      ec = ec + 1

   event_day_file = "/mnt/ams2/meteor_archive/" + this_station + "/EVENTS/" + event_year + "/" + event_day + "/" + event_day + "-events.json"
   event_day_dir = "/mnt/ams2/meteor_archive/" + this_station + "/EVENTS/" + event_year + "/" + event_day + "/" 
   if cfe(event_day_dir, 1) == 0:
      os.makedirs(event_day_dir)
   save_json_file(event_day_file, final_events)
   print("EVENT DAY FILE SAVED:", event_day_file)
   for event_id in final_events:
      event = final_events[event_id]
      station_count = len(set(final_events[event_id]['stations']))
      if station_count >= 2 and len(event['solutions']) == 0:
         print("./solve.py rec " + event_id)
         os.system("./solve.py rec " + event_id)

def check_if_solved(event, solved_events):
   tstart = event['event_start_time']
   tstart_dt = datetime.datetime.strptime(tstart, "%Y-%m-%d %H:%M:%S.%f")
   temp = tstart.split(".")
   event_id = temp[0]
   event_id = event_id.replace("-", "_")
   event_id = event_id.replace(":", "_")
   event_id = event_id.replace(" ", "_")
   solutions = []
   for se in solved_events:
      sf = se.split("/")[-1]
      sf_dt = datetime.datetime.strptime(sf, "%Y_%m_%d_%H_%M_%S")
      tdiff = abs((tstart_dt-sf_dt).total_seconds())
      if tdiff < 3:
         print("THIS EVENT IS ALREADY SOLVED!")
         event_id = sf
         jsons = glob.glob(se + "/*.json")
         for js in jsons:
            if "simple" in js:
               # Hankey solve
               hankey = load_json_file(js)
               hankey_status = 1
               for key in hankey['simple_solve']:
                  if hankey['simple_solve'][key]['track_start'][2] < 0 or hankey['simple_solve'][key]['track_end'][2] < 0:
                     hankey_status = 0
               solutions.append(('hankey_ip', js, hankey_status))

            if "_report" in js:
               # Vida solve
               vida_status = 1
               vida = load_json_file(js)
               if vida['rbeg_ele']  < 0 or vida['rend_ele'] < 0:
                  vida_status = 0
               solutions.append(('vida_ip', js, vida_status))

   return(event_id, solutions)

def prev_img_from_file(file=None,station=None,files=None,stations=None):
   prev_images = []
   if file is not None:
      print("NOT IMPLEMENTED YET")
      exit()
   if files is not None:
      for i in range(0,len(files)):
         file = files[i]
         station = stations[i]
         fn = file.split("/")[-1]
         fn = fn.replace(".json", "-prev-crop.jpg")
         year = fn[0:4]
         day = fn[0:10]
         prev_img_crop_dir = "/mnt/ams2/meteor_archive/" + station + "/DETECTS/PREVIEW/" + year + "/" + day + "/" 
         if cfe(prev_img_crop_dir,1) == 0:
            os.makedirs(prev_img_crop_dir)

         prev_img_crop = "/mnt/ams2/meteor_archive/" + station + "/DETECTS/PREVIEW/" + year + "/" + day + "/" + fn
         wb_prev_img_crop = "/mnt/wasabi/" + station + "/DETECTS/PREVIEW/" + year + "/" + day + "/" + fn  
         if cfe(prev_img_crop) == 0:
            if cfe(wb_prev_img_crop) == 1:
               os.system("cp " + wb_prev_img_crop + " " + prev_img_crop)
         prev_images.append(prev_img_crop)
   return(prev_images)


def find_event(file, station_id, detect_info, events,solved_events):
   found = 0
   if len(events) == 0: 
      event_id = 1
      events[event_id] = {}
      events[event_id]['event_start_time'] = detect_info['event_start_time'] 
      events[event_id]['event_id'] = event_id
      events[event_id]['stations'] = []
      events[event_id]['files'] = [] 
      events[event_id]['arc_files'] = []
      events[event_id]['clip_starts'] = []

      events[event_id]['stations'].append(station_id)
      events[event_id]['files'].append(file)
      if "archive_file" in detect_info:
         events[event_id]['arc_files'].append(detect_info['archive_file'])
      else:
         events[event_id]['arc_files'].append("pending")


      events[event_id]['clip_starts'].append(detect_info['event_start_time'])

      print("EVENT:", events[event_id])
      found = 1
   else:
      this_event_start_time = detect_info['event_start_time']
      this_event_start_time_dt = datetime.datetime.strptime(this_event_start_time, "%Y-%m-%d %H:%M:%S.%f")
 
      # check if the event already exists, if it does update it, else make a new one. 
      found = 0
      timed_events = []
      for event_id in events:
         event = events[event_id]
         event_start_time = event['event_start_time']
         event_start_time_dt = datetime.datetime.strptime(event_start_time, "%Y-%m-%d %H:%M:%S.%f")
         elapsed = abs((this_event_start_time_dt - event_start_time_dt).total_seconds())
         #print("EVENT EVAL:", event_id, this_event_start_time, event_start_time, elapsed)
         timed_events.append((event_id, elapsed))

      temp = sorted(timed_events, key=lambda x: x[1], reverse=False)
      if temp[0][1] < 60:
         found = 1
         event_id = temp[0][0]
         events[event_id]['stations'].append(station_id)
         events[event_id]['files'].append(file)
         if "archive_file" in detect_info:
            events[event_id]['arc_files'].append(detect_info['archive_file'])
         else:
            events[event_id]['arc_files'].append("pending")
         events[event_id]['clip_starts'].append(detect_info['event_start_time'])
   if found == 0:
      #event was not found so make a new one!
      event_id = len(events) + 1
      events[event_id] = {}
      events[event_id]['event_start_time'] = detect_info['event_start_time']
      events[event_id]['event_id'] = event_id
      events[event_id]['stations'] = []
      events[event_id]['files'] = []
      events[event_id]['arc_files'] = []
      events[event_id]['clip_starts'] = []

      events[event_id]['stations'].append(station_id)
      events[event_id]['files'].append(file)
      if "archive_file" in detect_info:
         events[event_id]['arc_files'].append(detect_info['archive_file'])
      else:
         events[event_id]['arc_files'].append("pending")
      events[event_id]['clip_starts'].append(detect_info['event_start_time'])

   # update event start time
   if len(events[event_id]['clip_starts']) > 1:
      dates = []
      for cs in events[event_id]['clip_starts']:
         dt = datetime.datetime.strptime(cs, "%Y-%m-%d %H:%M:%S.%f")
         dates.append(dt)
      event_start = avg_datetimes(dates, 1)

      events[event_id]['event_start_time'] = event_start

   # check if solved and update as needed

   return(event_id, events)   

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

def man_solve(values):
   print(values)
   wgs84 = pm.Ellipsoid('wgs84');
   lat1 = values['lat1']
   lon1 = values['lon1']
   alt1 = values['lat1']

   saz1 = values['saz1']
   eaz1 = values['eaz1']
   sel1 = values['sel1']
   eel1 = values['eel1']

   lat2 = values['lat2']
   lon2 = values['lon2']
   alt2 = values['lat2']

   saz2 = values['saz2']
   eaz2 = values['eaz2']
   sel2 = values['sel2']
   eel2 = values['eel2']


   x1, y1, z1 = pm.geodetic2ecef(float(lat1), float(lon1), float(alt1), wgs84)
   x2, y2, z2 = pm.geodetic2ecef(float(lat2), float(lon2), float(alt2), wgs84)
   
   # convert station lat,lon,alt,az,el to start and end vectors
   sveX1, sveY1, sveZ1, svlat1, svlon1,svalt1 = find_vector_point(float(lat1), float(lon1), float(alt1), saz1, sel1, 1000000)
   eveX1, eveY1, eveZ1, evlat1, evlon1,evalt1 = find_vector_point(float(lat1), float(lon1), float(alt1), eaz1, eel1, 1000000)

   sveX2, sveY2, sveZ2, svlat2, svlon2,svalt2 = find_vector_point(float(lat2), float(lon2), float(alt2), saz2, sel2, 1000000)
   eveX2, eveY2, eveZ2, evlat2, evlon2,evalt2 = find_vector_point(float(lat2), float(lon2), float(alt2), eaz2, eel2, 1000000)

   obs1 = Plane( \
   Point3D(x1,y1,z1), \
   Point3D(sveX1,sveY1,sveZ1), \
   Point3D(eveX1,eveY1,eveZ1))

   obs2 = Plane( \
   Point3D(x2,y2,z2), \
   Point3D(sveX2,sveY2,sveZ2), \
   Point3D(eveX2,eveY2,eveZ2))


   plane1 = Plane( \
      Point3D(x1,y1,z1), \
      Point3D(sveX1,sveY1,sveZ1), \
      Point3D(eveX1,eveY1,eveZ1))

   plane2 = Plane( \
      Point3D(x2,y2,z2), \
      Point3D(sveX2,sveY2,sveZ2), \
      Point3D(eveX2,eveY2,eveZ2))

   start_line1 = Line3D(Point3D(x1,y1,z1),Point3D(sveX1,sveY1,sveZ1))
   end_line1 = Line3D(Point3D(x1,y1,z1),Point3D(eveX1,eveY1,eveZ1))

   start_line2 = Line3D(Point3D(x2,y2,z2),Point3D(sveX2,sveY2,sveZ2))
   end_line2 = Line3D(Point3D(x2,y2,z2),Point3D(eveX2,eveY2,eveZ2))

   start_inter2 = plane2.intersection(start_line1)
   end_inter2 = plane2.intersection(end_line1)


   start_inter1 = plane1.intersection(start_line2)
   end_inter1 = plane1.intersection(end_line2)

   sx1,sy1,sz1 = read_inter(start_inter1)
   ex1,ey1,ez1 = read_inter(end_inter1)


   sx2,sy2,sz2 = read_inter(start_inter2)
   ex2,ey2,ez2 = read_inter(end_inter2)


   slat, slon, salt = pm.ecef2geodetic(sx1,sy1,sz1, wgs84)
   elat, elon, ealt = pm.ecef2geodetic(ex1,ey1,ez1, wgs84)


   slat2, slon2, salt2 = pm.ecef2geodetic(sx2,sy2,sz2, wgs84)
   elat2, elon2, ealt2 = pm.ecef2geodetic(ex2,ey2,ez2, wgs84)

   line1 = [slat,slon,salt,elat,elon,ealt]
   line2 = [slat2,slon2,salt2,elat2,elon2,ealt2]
   return(line1, line2)

def read_inter(inter):

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


   return(sx,sy,sz)




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
   #plt.show()
   kml_file = plot_file.replace(".png", ".kml")

   points = {}
   polys = {}
   print("MAKE KML", kml_file)
   # Now save the same info as a KML
   make_easykml(kml_file, points, lines, polys)
   print("Saved:", kml_file)

def make_easykml(kml_file, points={}, lines={}, polys={}):
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
   kml.save(kml_file)









def run_event_cmd(event_id):    
   year = event_id[0:4]
   mon = event_id[5:7]
   dom = event_id[8:10]
   day = event_id[0:10]
   station_id = json_conf['site']['ams_id']  

   events_file = "/mnt/ams2/meteor_archive/" + station_id + "/EVENTS/" + year + "/" + day + "/" + day + "-events.json"
   print(events_file)
   if cfe(events_file) == 1: 
      events = load_json_file(events_file)
   else:
      events = {}
   event = events[event_id]
   args = []
   for i in range(0,len(event['arc_files'])):
      arc = event['arc_files'][i]
      if "/mnt/ams2" in arc:
         arc = arc.split("/")[-1] 
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
      if "/mnt/ams2" in arc:
         arc = arc.split("/")[-1] 
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


def find_event_old(station, file, clip_start_time, events, captures):
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
            prev_dir = "/" + station + "/DETECTS/PREVIEW/" + year + "/" + day + "/"  
            prev_img = "/" + station + "/DETECTS/PREVIEW/" + year + "/" + day + "/"  + prev_fn
            wb_prev_img = "/mnt/archive.allsky.tv/" + station + "/DETECTS/PREVIEW/" + year + "/" + day + "/"  + prev_fn
            prev_imgs = ""
            if cfe(prev_dir, 1) == 0:
               os.makedirs(prev_dir)
            if cfe(prev_img) == 0:
               cmd = "cp " + wb_prev_img + " " + prev_img
               print(cmd)
               os.system(cmd)

def find_point_from_az_dist(lat,lon,az,dist):
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
if sys.argv[1] == "run_detects":
   run_detects(sys.argv[2])
if sys.argv[1] == "vida_failed_plots":
   vida_failed_plots(sys.argv[2])
if sys.argv[1] == "vida_plots":
   vida_plots(sys.argv[2])
if sys.argv[1] == "report_html":
   report_html(sys.argv[2])
if sys.argv[1] == "ei":
   make_event_day_index( sys.argv[2])
if sys.argv[1] == "man":
   # Robert and Los Alamos
   values = {
      'lat1' : 34.602065,
      'lon1' : -112.425065,
      'alt1' : 1500,
      'saz1' : 70.13,
      'sel1' : 15.6,
      'eaz1' : 84.81,
      'eel1' : 3.82,
      'lat2' : 35.88649,
      'lon2' : -106.276960,
      'alt2' : 2300,
      'saz2' : 260,
      'sel2' : 15,
      'eaz2' : 248,
      'eel2' : 8
   }
   # los alamos and nick
   values = {
      'lat1' : 35.88649,
      'lon1' : -106.276960,
      'alt1' : 2300,
      'saz1' : 260,
      'sel1' : 15,
      'eaz1' : 248,
      'eel1' : 8,
      'lat2' : 35.03290,
      'lon2' : -111.02157,
      'alt2' : 1600,
      'saz2' : 70.6,
      'sel2' : 29.76,
      'eaz2' : 74.58,
      'eel2' : 27.37
   }
   # robert and nick
   values = {
     'lat1' : 34.602065,
      'lon1' : -112.425065,
      'alt1' : 1500,
      'saz1' : 70.13,
      'sel1' : 15.6,
      'eaz1' : 84.81,
      'eel1' : 3.82,
      'lat2' : 35.03290,
      'lon2' : -111.02157,
      'alt2' : 1600,
      'saz2' : 70.6,
      'sel2' : 29.76,
      'eaz2' : 74.58,
      'eel2' : 27.37
   }


 #35.032900° / -111.021570°
#31.40 -70.60

#27.21 -74.58


   man_solve(values)
