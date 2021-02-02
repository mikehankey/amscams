#!/usr/bin/python3

import numpy as np
from DynaDB import search_events, get_event
import boto3
from datetime import datetime
import json
from decimal import Decimal
import sys
from lib.PipeAutoCal import fn_dir
import glob
from lib.PipeUtil import cfe, load_json_file, save_json_file, convert_filename_to_date_cam
from FlaskLib.FlaskUtils import make_default_template
import boto3
import socket
import subprocess
from boto3.dynamodb.conditions import Key

def event_sum(ed):
   traj = ed['traj']
   orb = ed['orb']
   rad = ed['rad']
   plot = ed['plot']
   kml = ed['kml']
   for key in orb:
      print(key)



   traj = """
      <table>
      <tr><td>Start Lat/Lon</td><td>""" + str(traj['start_lat']) + " / " + str(traj['start_lon']) + """</td></tr>
      <tr><td>End Lat/Lon</td><td>""" + str(traj['end_lat']) + """ / """ + str(traj['end_lon']) + """</td></tr>
      <tr><td>Start Height</td><td>""" + str(traj['start_ele']) + """</td></tr>
      <tr><td>End Height</td><td>""" + str(traj['end_ele']) + """</td></tr>
      <tr><td>Velocity Init</td><td>""" + str(traj['v_init']) + """</td></tr>
      <tr><td>Velocity Avg</td><td>""" + str(traj['v_avg']) + """</td></tr>
      </table>
   """

   orb = """
      <table><tr><td>
      <table>
      <tr><td>a</td><td>""" + str(orb['a']) + """</td></tr>
      <tr><td>e</td><td>""" + str(orb['e']) + """</td></tr>
      <tr><td>i</td><td>""" + str(orb['i']) + """</td></tr>
      <tr><td>peri</td><td>""" + str(orb['peri']) + """</td></tr>
      <tr><td>node</td><td>""" + str(orb['node']) + """</td></tr>
      <tr><td>q</td><td>""" + str(orb['q']) + """</td></tr>
      </table>
      </td><td>

      <table>
      <tr><td>q</td><td>""" + str(orb['q']) + """</td></tr>
      <tr><td>Q</td><td>""" + str(orb['Q']) + """</td></tr>
      <tr><td>True Anomaly</td><td>""" + str(orb['true_anomaly']) + """</td></tr>
      <tr><td>Eccentric Anomaly</td><td>""" + str(orb['eccentric_anomaly']) + """</td></tr>
      <tr><td>Mean Anomally</td><td>""" + str(orb['mean_anomaly']) + """</td></tr>
      <tr><td>T</td><td>""" + str(orb['T']) + """</td></tr>
      <tr><td>Tj</td><td>""" + str(orb['Tj']) + """</td></tr>
      </table>

      </td></tr>
      </table>

   """

   return(traj,orb)


def event_detail(event_id):
   #import pandas as pd
   import pickle
   json_conf = load_json_file("../conf/as6.json")
   amsid = json_conf['site']['ams_id']
   dynamodb = boto3.resource('dynamodb')
   event = get_event(dynamodb, event_id)
   remote_urls = get_remote_urls(json_conf)


   out = make_default_template(amsid, "events.html", json_conf)

   html = """   
      <div id='main_container' class='container-fluid h-100 mt-4 lg-l'>
   """

   if "solution" in event:
      if "sol_dir" in event['solution']:
         sol_dir = event['solution']['sol_dir']
      else:
         sol_dir = "" 
         sol_jpgs = []
         sol_pickles = []
         sol_jsons = []
         print("SOLDIR IS MISSING FROM EVENT!")

   if sol_dir != "" and sol_dir is not None:
      sol_jpgs = glob.glob(sol_dir + "/*.jpg")
      sol_pickles = glob.glob(sol_dir + "/*.pickle")
      sol_jsons = glob.glob(sol_dir + "/*.json")
  
   event_file = ""
   full_event_file = ""
   obs_file = ""
   for js in sol_jsons:
      print("JS:", js)
      if "event" in js:
         full_event_file = js
      if "obs" in js:
         print("OBS FILE FOUND")
         obs_file = js.replace("/mnt/ams2", "")

   traj_sum_html = ""
   orb_sum_html = ""
   orb_link = ""
   
   no_sol = 0 
   if full_event_file != "" :
      event_data = load_json_file(full_event_file)
      orb_link = event_data['orb']['link']
      traj_sum_html, orb_sum_html = event_sum(event_data) 
   else:
      event_data = {}
      no_sol = 1
   
   print("FULL:", full_event_file)
   
   if no_sol == 1:
      obs_html = make_obs_html(event, remote_urls)
      out = "no solution yet." 
      out += obs_html
      return(out)
   

   kml_file = ""
   if obs_file != '':
      obs_data = load_json_file("/mnt/ams2/" + obs_file)
      center_lat, center_lon = center_obs(obs_data) 
      kml_file = obs_file.replace("-obs.json", "-map.kml")

 
   html += "<h2>Event ID: {:s}</h2>\n".format(event_id)
   # show obs 
   if True:
      html += "<h2>Observations</h2>\n"      
      html += "<div class='gallery gal-resize reg row text-center text-lg-left'>\n"

      blocks = []
      for i in range(0, len(event['stations'])):
         temp = ""
         file = event['files'][i]
         (f_datetime, cam, f_date_str,fy,fmon,fd, fh, fm, fs) = convert_filename_to_date_cam(file)
         station_id = event['stations'][i]
         prev_file = file.replace(".mp4", "-prev.jpg")
         year = file[0:4]
         day = file[0:10]
         link = remote_urls[station_id] + "/meteors/" + station_id + "/" + day + "/" + file + "/"
         caption =  station_id + "-" + cam
         temp += "<div id='" + prev_file + "' class='preview select-to multi'>\n "
         temp += "<a href=" + link + " class='mtt'>\n"
         temp += "<img width=320 height=180 class='img-fluid ns lz' alt='" + prev_file + "' src=https://archive.allsky.tv/" + station_id + "/METEORS/" + year + "/" + day + "/" + station_id + "_" + prev_file + "><span>" + caption + "</span></a>\n"
         #temp += "<img alt='" + prev_file + "' src=https://archive.allsky.tv/" + station_id + "/METEORS/" + year + "/" + day + "/" + station_id + "_" + prev_file + "><span>" + caption + "</span></a>\n"
         temp += "</div>\n"
         blocks.append((caption, temp))

      last_id = None
      for id, block in sorted(blocks, key=lambda x: (x[0]), reverse=False):
         html += block
         #if last_id is not None and last_id != id:
         #   html += "<div style='clear:both'></div><br>"
         last_id = id

      html += "</div>\n"
      html += "<a href=" + obs_file + ">Obs</a> <p> \n</p>"


      html += "<h2>Trajectory</h2>"
      html += "<iframe src=\"/dist/maps/index.html?mf=" + kml_file + "&lat=" + str(center_lat) + "&lon=" + str(center_lon) + "\" width=800 height=440></iframe><br><a href=" + kml_file + ">KML</a><br>"
      html += traj_sum_html

      #html += "<a href=" + kml_file + ">KML</a><br>"

      html += "<h2>Orbit</h2>"
      if orb_link != "":
         html += "<iframe src=\"" + orb_link + "\" width=800 height=440></iframe><br><a href=" + orb_link + ">Orbit</a><br>"
         html += "<div>" + orb_sum_html + "</div>"

   html += "<h2>Plots</h2>"
   html += "<div class='gallery gal-resize reg row text-center text-lg-left'>\n"
   for img in sorted(sol_jpgs):
      img = img.replace("/mnt/ams2", "")
      if "ground" not in img and "orbit" not in img:
         html += "<div style='float:left; padding: 3px'><img width=600 height=480 src=" + img + "></div>\n"

   html += "</div>"

   if False:
      f = open(sol_pickles[0], 'rb')
      object = pickle.load(f)

      from pprint import pprint
      html += "<PRE>"
      pdata = vars(object)
   

      for key in pdata:
         if key == "observations":
            for skey in pdata[key]:
               html += "key:" + str(key) + ":" + str(skey) + "\n"
             
         else:
            html += "key:" + str(key) + ":" + str(pdata[key]) + "\n"

   html += "</div></div><div>"
   out = out.replace("{MAIN_TABLE}", html)

   return(out)


def make_obs_html(event, remote_urls):

   temp_out = ""      
   temp_out += "<h2>Observations</h2>\n"
   temp_out += "<div class='gallery gal-resize reg row text-center text-lg-left'>\n"

   blocks = []
   for i in range(0, len(event['stations'])):
      temp = ""
      file = event['files'][i]
      (f_datetime, cam, f_date_str,fy,fmon,fd, fh, fm, fs) = convert_filename_to_date_cam(file)
      station_id = event['stations'][i]
      prev_file = file.replace(".mp4", "-prev.jpg")
      year = file[0:4]
      day = file[0:10]
      link = remote_urls[station_id] + "/meteors/" + station_id + "/" + day + "/" + file + "/"
      caption =  station_id + "-" + cam
      temp += "<div id='" + prev_file + "' class='preview select-to multi'>\n "
      temp += "<a href=" + link + " class='mtt'>\n"
      temp += "<img width=320 height=180 class='img-fluid ns lz' alt='" + prev_file + "' src=https://archive.allsky.tv/" + station_id + "/METEORS/" + year + "/" + day + "/" + station_id + "_" + prev_file + "><span>" + caption + "</span></a>\n"
      temp += "</div>\n"
      blocks.append((caption, temp))

   last_id = None
   for id, block in sorted(blocks, key=lambda x: (x[0]), reverse=False):
      temp_out += block
      last_id = id

   temp_out += "</div>\n"
   #temp_out += "<a href=" + obs_file + ">Obs</a> <p> \n</p>"

   return(temp_out)

def center_obs(obs_data):
   lats = []
   lons = []
   for st in obs_data:
      for fn in obs_data[st]:
         lat,lon,alt = obs_data[st][fn]['loc']
      lats.append(float(lat))
      lons.append(float(lon))
   return(np.mean(lats),np.mean(lons))


def get_remote_urls(json_conf=None):
   if json_conf is None:
      json_conf = load_json_file("../conf/as6.json")
   remote_urls = {}
   if "remote_urls" in json_conf['site']:
      for i in range(0, len(json_conf['site']['multi_station_sync'])):
         station = json_conf['site']['multi_station_sync'][i]
         url = json_conf['site']['remote_urls'][i]
         remote_urls[station] = url
   return(remote_urls)


def list_events_for_day(date):
   dynamodb = boto3.resource('dynamodb')
   json_conf = load_json_file("../conf/as6.json")
   stations = json_conf['site']['multi_station_sync']
   remote_urls = get_remote_urls(json_conf)
   events = search_events(dynamodb, date, stations)

   html = ""

   event_dir = "/mnt/ams2/meteor_archive/" + json_conf['site']['ams_id'] + "/EVENTS/" + date + "/" 
   html = "<table>"
   for event in events:
      print(event)
      stations = event['stations']
      ustations = set(stations)
      files = event['files']
      event_id = event['event_id']
      if "sol_dir" in event:
         sol_dir = event['sol_dir']
      else:
         sol_dir = None
      if "solution" in event:
         wmpl_status = 1 
      else:
         wmpl_status = None 

      html += "<tr><td>" + event_id + "</td><td>" + str(ustations) + "</td><td>\n"
      for i in range(0, len(event['stations'])):
         file = files[i]
         (f_datetime, cam, f_date_str,fy,fmon,fd, fh, fm, fs) = convert_filename_to_date_cam(file)
         station_id = stations[i]
         prev_file = file.replace(".mp4", "-prev.jpg")
         year = file[0:4]
         day = file[0:10]
         link = remote_urls[station_id] + "/meteors/" + station_id + "/" + day + "/" + file + "/"
         caption =  station_id + "-" + cam  
         #html += "<a href=" + link + ">"
         #html += "<figure><img src=https://archive.allsky.tv/" + station_id + "/METEORS/" + year + "/" + day + "/" + station_id + "_" + prev_file + "><figcaption>" + caption + "</figcaption></a></figure>"
      
      if sol_dir is not None:  
         #elink = sol_dir + "/index.html"
         #elink = elink.replace("/mnt/ams2", "")
         elink = "/event_detail/" + event_id + "/"
      else:
         #elink = "#"
         elink = "/event_detail/" + event_id + "/"

      if wmpl_status is None:
         html += "<td><a href=" + elink + ">Event not solved yet.</a></td>"
      else: 
         if wmpl_status == 0:
            html += "<td><a href=" + elink + ">Failed</a></td>"
         else:
            html += "<td><a href=" + elink + ">Solved</a></td>"
      html += "</tr>" 
        
   html += "</table>"

   return(html)

