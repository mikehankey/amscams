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
   event = get_event(None, event_id)
   remote_urls = get_remote_urls(json_conf)


   out = make_default_template(amsid, "events.html", json_conf)

   html = """   
      <div id='main_container' class='container-fluid h-100 mt-4 lg-l'>
   """

   sol_dir = "" 
   sol_jpgs = []
   sol_pickles = []
   sol_jsons = []
   if "solution" in event:
      if event['solution'] != 0:
         if "sol_dir" in event['solution']:
            sol_dir = event['solution']['sol_dir']
         else:
            print("SOLDIR IS MISSING FROM EVENT!")
      else:
         sol_dir = ""

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
      #obs_html = make_obs_html(event_id, event_data, "", obs_data)
      out = "no solution yet."  + str(event)
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
      obs_file = obs_file.replace("/meteor_archive/", "https://archive.allsky.tv/") 
      html += "<a href=" + obs_file + ">Obs</a> <p> \n</p>"


      html += "<h2>Trajectory</h2>"
      kml_file = kml_file.replace("/meteor_archive/", "https://archive.allsky.tv/") 
      html += "<iframe src=\"https://archive.allsky.tv/APPS/dist/maps/index.html?mf=" + kml_file + "&lat=" + str(center_lat) + "&lon=" + str(center_lon) + "\" width=800 height=440></iframe><br><a href=" + kml_file + ">KML</a><br>"
      html += traj_sum_html

      #html += "<a href=" + kml_file + ">KML</a><br>"

      html += "<h2>Orbit</h2>"
      if orb_link != "":
         html += "<iframe src=\"" + orb_link + "\" width=800 height=440></iframe><br><a href=" + orb_link + ">Orbit</a><br>"
         html += "<div>" + orb_sum_html + "</div>"

   html += "<h2>Plots</h2>"
   html += "<div class='gallery gal-resize reg row text-center text-lg-left'>\n"
   for img in sorted(sol_jpgs):
      img = img.replace("/mnt/ams2/meteor_archive/", "http://archive.allsky.tv/")
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


def make_obs_html_new(event_id, event, solve_dir, obs):
   html = "<h2>Observations</h2>"
   html += "<div>"

   if True:

      blocks = []
      for i in range(0, len(event['stations'])):
         temp = ""
         file = event['files'][i]
         (f_datetime, cam, f_date_str,fy,fmon,fd, fh, fm, fs) = convert_filename_to_date_cam(file)
         station_id = event['stations'][i]
         prev_file = file.replace(".mp4", "-prev.jpg")
         year = file[0:4]
         day = file[0:10]
         #link = remote_urls[station_id] + "/meteors/" + station_id + "/" + day + "/" + file + "/"
         start_az =  event['solution']['obs'][station_id][file]['azs'][0]
         end_az =  event['solution']['obs'][station_id][file]['azs'][-1]
         start_el =  event['solution']['obs'][station_id][file]['els'][0]
         end_el =  event['solution']['obs'][station_id][file]['els'][-1]
         dur =  len(event['solution']['obs'][station_id][file]['els']) / 25

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


def list_events_for_day(dynamo, date):
   json_conf = load_json_file("../conf/as6.json")
   stations = json_conf['site']['multi_station_sync']
   remote_urls = get_remote_urls(json_conf)


   ams_id = json_conf['site']['ams_id']
   #date = "2021_01_24"
   #response = dynamo.tables['meteor_obs'].query(
   #KeyConditionExpression='station_id = :station_id AND begins_with(sd_video_file, :date)',
   #   ExpressionAttributeValues={
   #          ':station_id': ams_id,
   #         ':date': date,
   #   }
   #)
   #print("R:", response['Items'])


   #events = search_events(None, date, stations)

   #KeyConditionExpression='event_day= :event_day ',
   #   ExpressionAttributeValues={
   #          ':event_day': date
   #   }
   #)
   #response = dynamo.tables['x_meteor_event'].query()

   response = dynamo.tables['x_meteor_event'].scan()

   events = response['Items']
   events= sorted(events, key=lambda x: x['event_id'], reverse=True)

   if len(events) == 0:
      return("There are no events registered for " + date)

   html = ""

   event_dir = "/mnt/ams2/meteor_archive/" + json_conf['site']['ams_id'] + "/EVENTS/" + date + "/" 
   html = "<table>"
   html += "<tr><td>Event ID</td><td>Stations</td><td>Start Height</td><td>End Height</td><td>Vel Init</td><td>Vel Avg</td><td>a</td><td>e</td><td>i</td><td>Shower</td><td>Status</td></tr>"
   for event in events:
      print(event)
      stations = event['stations']
      ustations = set(stations)
      files = event['files']
      event_id = event['event_id']

      wmpl_status = None
      sol_dir = None
      if "solution" in event:
         solution = event['solution']
         if solution != 0:
            if "sol_dir" in solution:
               if solution['sol_dir'] != 0:
                  wmpl_status = 1 
      ustations = str(ustations)
      ustations = ustations.replace("{", "")
      ustations = ustations.replace("}", "")
      ustations = ustations.replace("'", "")
      html += "<tr><td>" + event_id + "</td><td>" + str(ustations) + "</td>\n"
      shower_no = ""
      shower_code = ""
      if wmpl_status == 1:
         orb = solution['orb']
         if "shower" in solution:
            shower_no = solution['shower']['shower_no']
            shower_code = solution['shower']['shower_code']
         if shower_no == -1:
            shower_no = ""
            shower_code = ""
  
        
         traj = solution['traj']
         start_ele = traj['start_ele']
         end_ele = traj['end_ele']
         v_init = traj['v_init']
         v_avg = traj['v_avg']
         a = orb['a']
         e = orb['e']
         i = orb['i']
         html += "<td>" + str(start_ele/1000)[0:5] + " km</td><td>" + str(end_ele/1000)[0:5] + "km</td>\n"
         html += "<td>" + str(v_init/1000)[0:5] + " km/s</td><td>" + str(v_avg/1000)[0:5] + "km/s</td>\n"
         html += "<td>" + str(a)[0:5] + "</td><td>" + str(e)[0:5] + "</td>\n"
         html += "<td>" + str(i)[0:5] + "</td>"
         html += "<td>" + str(shower_code) + "</td>"
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
         if "solution" not in event:
            html += "<td colspan=8><a href=" + elink + ">Event not solved yet.</a></td>"
         elif solution == 0:
            html += "<td colspan=8><a href=" + elink + ">WMPL Solve Failed.</a></td>"
      else: 
         if wmpl_status == 0:
            html += "<td><a href=" + elink + ">Failed</a></td>"
         else:
            html += "<td><a href=" + elink + ">Solved</a></td>"
      html += "</tr>" 
        
   html += "</table>"

   return(html)

