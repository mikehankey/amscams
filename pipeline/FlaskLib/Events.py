#!/usr/bin/python3
import os
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


def all_events(json_conf, fv):
   #fv['solve_status']  # 0 = not run, 1 = solved, -1 = failed -2 missing reductions
   #fv['start_date'] 
   #fv['end_date'] 
   #fv['stations'] # list of stations to include in list "," separated
   select_data = []

   event_dir = "/mnt/ams2/EVENTS/"
   cloud_event_dir = "/mnt/archive.allsky.tv/EVENTS/"
   aes = event_dir + "ALL_EVENTS_SUMMARY.json"
   caes = cloud_event_dir + "ALL_EVENTS_SUMMARY.json"
   if cfe(event_dir,1) == 0:
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
   
   select_data = sorted(select_data, key=lambda x: (x[2]), reverse=True)

   matches = 0
   out_table = "<table>"
   out_table += "<tr><td>Event ID</td><td>Status</td></tr>"
   for data in select_data:
      show_row = 0
      solve_status, event_id, event_datetime, stations, files, shower, ls, cs = data
      print("DATA:", data)
      if fv['solve_status'] is None:
         show_row = 1
      elif fv['solve_status'] == "1" and "SUCCESS" in solve_status :
         show_row = 1
      elif fv['solve_status'] == "0" or "NOT SOLVED" in solve_status :
         show_row = 1
      elif fv['solve_status'] == "-1" and "FAILED" in solve_status :
         show_row = 1
      elif fv['solve_status'] == "-2" and "missing" in solve_status :
         show_row = 1
      if show_row == 1:
         matches += 1
         link = "/event_detail/" + str(event_id) + "/"
         href = "<a href=" + link + ">" 
         out_table += "<tr><td>" + href + str(event_id) + "</a></td><td>" + solve_status + "</td></tr>\n"

   out_table += "</table>"
   head = str(matches) + " events <br>"
   return(head + out_table)

def get_obs_data(date, json_conf):


   #os.system("./DynaDB.py cd " + date)
   #print("./DynaDB.py cd " + date)
  
   obs_data = {} 
   le_dir = "/mnt/ams2/meteor_archive/" + json_conf['site']['ams_id'] + "/EVENTS/" + date + "/"
   stations = json_conf['site']['multi_station_sync']
   if json_conf['site']['ams_id'] not in stations:
      stations.append(json_conf['site']['ams_id'])

   html = ""
   for station in stations:
      html += "<h1>" + station + "</h1>"
      obs_file = le_dir + station + "_" + date + ".json"
      if cfe(obs_file) == 1:
         obs = load_json_file(obs_file)
         obs_data[station] = obs
   return(obs_data)

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

   if "T" not in orb:
      orb['T'] = 0
   if "Tj" not in orb:
      orb['Tj'] = 0

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

def obs_json_to_html(obs, best, remote_urls = None):

   prev_file = obs['sd_video_file'].replace(".mp4", "-prev.jpg")
   year = prev_file[0:4]
   date = prev_file[0:10]
   station_id = obs['station_id']
   file = obs['sd_video_file']
   caption = ""
   if remote_urls is not None:
      rurl = remote_urls[obs['station_id']]
      link = remote_urls[station_id] + "/meteor/" + station_id + "/" + date + "/" + file + "/"
      href = "<a href=" + link + ">"
   else:
      href = ""

   prev_html = href + "<img width=320 height=180 class='' alt='" + prev_file + "' src=https://archive.allsky.tv/" + station_id + "/METEORS/" + year + "/" + date + "/" + station_id + "_" + prev_file + "><span>" + caption + "</span></a>\n"

   if best == 1:
      best_tag = "*"
   else:
      best_tag = ""
   html = "<table><tr><td>"
   html += """<PRE>
Station     : {:s} 
SD File     : {:s} {:s}
HD File     : {:s} 
Stars       : {:s} 
Ast Res     : {:s} 
Duration    : {:s} 
Revision    : {:s} 
Last Update : {:s} 
   """.format( str(obs['station_id']), str(obs['sd_video_file']), str(best_tag), str(obs['hd_video_file']), str(obs['calib'][6]), str(obs['calib'][7]), str(obs['duration']), str(obs['revision']), str(obs['last_update']) )
   html += "<table>"
   html += "<tr><td>DT</td><td>FN</td><td>X</td><td>Y</td><td>W</td><td>H</td><td>Int</td><td>RA</td><td>DEC</td><td>AZ</td><td>EL</td></tr> "
   for data in obs['meteor_frame_data']:
      dt, fn, x, y, w, h, pint, ra, dec, az, el = data
      html += "<tr><td>{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td></tr> \n".format( str(dt), str(fn), str(x), str(y), str(w), str(h), str(pint), str(ra), str(dec), str(az), str(el) )
   html += "</table>"
   html += "</td><td>" + prev_html + "</td></tr>"
   html += "</table>"

   return(html)

def event_detail_template():

   ### SUMMARY / TOP
   sum_html = """
   <table>
   <tr>
      <td>Event ID</td>
      <td>{EVENT_ID}</td>
   </tr>
   <tr>
      <td>Status</td>
      <td>{STATUS}</td>
   </tr>
   <tr>
      <td>Start Time</td>
      <td>{EVENT_START_TIME}</td>
   </tr>
   <tr>
      <td>Duration</td>
      <td>{DURATION}</td>
   </tr>
   <tr>
      <td>Velocity</td>
      <td>{VELOCITY}</td>
   </tr>
   <tr>
      <td>Ending Altitude</td>
      <td>{END_ALT}</td>
   </tr>
   </table>
   """

   ### OBS HTML
   obs_html = """
   <tr>
      <td>Stations</td>
      <td>{STATIONS}</td>
   </tr>
   <tr>
      <td>Files</td>
      <td>{FILES}</td>
   </tr>
   </table>

   """

   ### TRAJ HTML
   traj_html = """

   """

   ### ORB HTML
   orb_html = """

   """

   ### WMPL HTML
   wmpl_report_html = """

   """

   return(html)

def event_detail(event_id, json_conf):
   y = event_id[0:4]
   m = event_id[4:6]
   d = event_id[6:8]
   date = y + "_" + m + "_" + d
   le_dir = "/mnt/ams2/EVENTS/" + y + "/" + m + "/" + d + "/"
   le_file = le_dir + date + "_ALL_EVENTS.json"
   out = ""
   if cfe(le_file) == 1:
      events = load_json_file(le_file)
   for ev in events:
      if ev['event_id'] == event_id:
         event = ev
   out += le_file + "<BR>"
   out += str(len(events))
   #out += str(event)

   stations = event['stations']
   files = event['files']
   status = event['solve_status']
   dates = event['start_datetime']
   sol = event['solution']
   out += "Status:" + status + "<BR>"
   out += str(stations)
   out += str(files)
   template = event_detail_template()
   template = template.replace("{EVENT_ID}", event_id)
   template = template.replace("{STATUS}", status)
   template = template.replace("{EVENT_START_TIME}", min(dates))
   template = template.replace("{STATIONS}", str(stations))
   template = template.replace("{FILES}", str(files))

   return(template)

def event_detail_old(event_id, json_conf):
   y = event_id[0:4]
   m = event_id[4:6]
   d = event_id[6:8]
   date = y + "_" + m + "_" + d
   le_dir = "/mnt/ams2/meteor_archive/" + json_conf['site']['ams_id'] + "/EVENTS/" + date + "/"
   le_file = le_dir + date + "_events.json"
   events = load_json_file(le_file)
   this_event = None
   for event in events:
      if event_id == event['event_id']:
         this_event = event

   these_obs_files = this_event['files']
   these_stations = this_event['stations']
   these_obs = []
   best_obs = {}
   all_obs = get_obs_data(date, json_conf)
   if "solve_status" not in this_event:
      this_event['solve_status'] = "UNSOLVED"
   for station in all_obs:
      if station in these_stations:
         for obs in all_obs[station]:
            if obs['sd_video_file'] in these_obs_files:
               these_obs.append(obs)
   

   out = """ <PRE>
Event Summary 
Event ID         : {:s}
Start Datetime   : {:s}
Status           : {:s}
<hr>
   """.format(str(this_event['event_id']), str(min(this_event['start_datetime'])), str(this_event['solve_status']))
   #html += str(this_event)
   if "obs" in this_event:
      for station in this_event['obs']:
         for file in this_event['obs'][station]:
            print(station, file)
            key = station + ":" + file
            best_obs[key] = 1

      print("BEST OBS:", best_obs)
   #else:
   #   these_obs = []
   remote_urls = get_remote_urls(json_conf)

   for obs in these_obs:
      key = obs['station_id'] + ":" + obs['sd_video_file']
      if key in best_obs:
         best = 1
      else:
         best = 0
      print("THESE OBS BEST?", key, best)
      print("OBS", obs)
      obs_html = obs_json_to_html(obs, best,remote_urls)
      out += str(obs_html) + "<HR>"
      #out += "OBS:" + str(obs) + "<HR>"
   return(out)

def event_detail_old(event_id):
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
         link = remote_urls[station_id] + "/meteor/" + station_id + "/" + day + "/" + file + "/"
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
      if orb_link != "" and orb_link != "#":
         html += "<iframe src=\"" + orb_link + "\" width=800 height=440></iframe><br><a href=" + orb_link + ">Orbit</a><br>"
         html += "<div>" + orb_sum_html + "</div>"
      else:
         html += "<h2> ORBIT FAILED. POSSIBLY PROBLEM WITH POINT DATA / VELOCITY?"

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
         #link = remote_urls[station_id] + "/meteor/" + station_id + "/" + day + "/" + file + "/"
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
      link = remote_urls[station_id] + "/meteor/" + station_id + "/" + day + "/" + file + "/"
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

def list_event_days(json_conf):
   stations = json_conf['site']['multi_station_sync']
   remote_urls = get_remote_urls(json_conf)
   le_main_dir = "/mnt/ams2/meteor_archive/" + json_conf['site']['ams_id'] + "/EVENTS/" 
   edirs = glob.glob(le_main_dir + "*")
   out = ""
   event_days = []
   for ed in edirs:
      if cfe(ed,1) == 1:
         day = ed.split("/")[-1]
         ddd  = day.split("_")
         if len(ddd) == 3:
            event_days.append(day)
   for ed in sorted(event_days, reverse=True):
      href = "<a href=/events/" + ed + "/>" 
      out += href + ed + "</a><br>"

   return(out)
   #le_file = le_dir + date + "_events.json"

def list_events_for_day(date, recache=0):
   json_conf = load_json_file("../conf/as6.json")
   stations = json_conf['site']['multi_station_sync']
   remote_urls = get_remote_urls(json_conf)
   le_dir = "/mnt/ams2/meteor_archive/" + json_conf['site']['ams_id'] + "/EVENTS/" + date + "/"
   le_file = le_dir + date + "_events.json"

   ams_id = json_conf['site']['ams_id']
   html = ""

   if cfe(le_file) == 0 or recache == 1:
      html += "Re-caching DYNA DB DATA<br>"
      os.system("./DynaDB.py cd " + date)
      if cfe(le_file) == 1:
         #html += "loading event file after recache:" + le_file + "<br>"
         events = load_json_file(le_file)
      else:
         html += "No dyna events exist for this day:" + date + "<br>"
         events = []
   
   else:
      #html += "loading event file:" + le_file + "<br>"
      events = load_json_file(le_file)
   

   if len(events) == 0:
      return(html)
   else:
      html += str(len(events)) + " registered events."


   event_dir = "/mnt/ams2/meteor_archive/" + json_conf['site']['ams_id'] + "/EVENTS/" + date + "/" 

   solved_events = []
   unsolved_events = []

   bad_events = []

   for event in events:
      #html += str(event) + "<hr>"
      if "event_id" in event and "solve_status" in event:
         #html += str(event['event_id']) + " " + " " + event['solve_status'] + "<hr>"
         yo = 1
      else:
         #html += "MISSING STATUS?" + str(event) + "<hr>"
         if event not in unsolved_events:
            unsolved_events.append(event)
            print("UNSOLVED!")
      if "solve_status" in event:
         if "FAIL" in event['solve_status']:
            bad_events.append(event)

         else:
            solved_events.append(event)
      else:
         if event not in unsolved_events:
            unsolved_events.append(event)

   if len(solved_events) > 0:
      html += "<table>"
      html += "<tr><td>Event ID</td><td>Stations</td><td>Start Height</td><td>End Height</td><td>Vel Init</td><td>Vel Avg</td><td>a</td><td>e</td><td>i</td><td>Shower</td><td>Status</td></tr>"

   for event in solved_events:
      #print(event)
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
      shower_no = ""
      shower_code = ""
      if wmpl_status == 1:
         sol_dir = solution['sol_dir']
         orb = solution['orb']
         if "shower" in solution:
            shower_no = solution['shower']['shower_no']
            shower_code = solution['shower']['shower_code']
         if shower_no == -1:
            shower_no = ""
            shower_code = ""

          
         plink = sol_dir.replace("/mnt/ams2/meteor_archive/", "http://archive.allsky.tv/")
         plink += "/index.html"
         pref = "<a href=" + plink + ">"
         html += "<tr><td>" + pref + event_id + "</a></td><td>" + str(ustations) + "</td>\n"
        
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
         link = remote_urls[station_id] + "/meteor/" + station_id + "/" + day + "/" + file + "/"
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

      if "solve_status" in event:
         if "SUC" in event['solve_status']:
            event['solve_status'] = "SUCCESS"
   
         html += "<td colspan=8><a href=" + elink + ">" + event['solve_status'] + "</a></td>"

      else: 
         html += "<td><a href=" + elink + ">Not Solved yet</a></td>"
      html += "</tr>" 
        
   if len(solved_events) > 0:
      html += "</table>"

   if len(bad_events) > 0:
      html += ("<h1>Failed events</h1>")

      for event in bad_events:
         html += "<li><a href=/event_detail/" + event['event_id'] + ">" + event['event_id'] + "</a></li>\n"

   if len(unsolved_events) > 0:
      html += ("<h1>Unsolved</h1>")
      for event in unsolved_events:
         html += "<li><a href=/event_detail/" + event['event_id'] + ">" + event['event_id'] + "</a></li>\n"


   return(html)

