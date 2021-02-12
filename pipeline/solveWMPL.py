#!/usr/bin/python3

import os
import matplotlib
matplotlib.use('agg')
import glob
from lib.PipeAutoCal import fn_dir
from DynaDB import get_event, get_obs, search_events, update_event, update_event_sol
from lib.PipeUtil import load_json_file, save_json_file, cfe, calc_dist, convert_filename_to_date_cam
import sys
import numpy as np
import datetime
import math
from lib.PipeSolve import simple_solvev2
# Import modules from WMPL
import wmpl.Utils.TrajConversions as trajconv
import wmpl.Utils.SolarLongitude as sollon
from wmpl.Trajectory import Trajectory as traj


from wmpl.Utils.ShowerAssociation import associateShower


import boto3
from boto3.dynamodb.conditions import Key


import time
from wmpl.Utils.TrajConversions import equatorialCoordPrecession_vect, J2000_JD

def GC_az_el(azs, els):

   import RMS.GreatCircle
   from RMS.Math import polarToCartesian, cartesianToPolar
   import numpy as np
   from RMS import GreatCircle


   azim = np.array(azs)
   elev = np.array(els)

   ### Fit a great circle to Az/Alt measurements and compute model beg/end RA and Dec ###

   # Convert the measurement Az/Alt to cartesian coordinates
   # NOTE: All values that are used for Great Circle computation are:
   #   theta - the zenith angle (90 deg - altitude)
   #   phi - azimuth +N of due E, which is (90 deg - azim)
   x, y, z = polarToCartesian(np.radians((90 - azim)%360), np.radians(90 - elev))

   # Fit a great circle
   C, theta0, phi0 = GreatCircle.fitGreatCircle(x, y, z)

   azs_gc = []
   els_gc = []

   # Get the first point on the great circle
   for i in range(0, len(azs)):
      phase1 = GreatCircle.greatCirclePhase(np.radians(90 - elev[i]), np.radians((90 - azim[i])%360), \
            theta0, phi0)
      alt1, azim1 = cartesianToPolar(*GreatCircle.greatCircle(phase1, theta0, phi0))
      alt1 = 90 - np.degrees(alt1)
      azim1 = (90 - np.degrees(azim1))%360
      print("ORG/NEW:", azs[i], els[i], azim1, alt1)
      azs_gc.append(float(azim1))
      els_gc.append(float(alt1))
   return(azs_gc, els_gc)



def solve_status(day):
   dynamodb = boto3.resource('dynamodb')
   stations = []
   events = search_events(dynamodb, day, stations)
   solved_html = ""
   not_solved_html = ""
   failed_html = ""
   for event in events:
      if "solve_status" in event :
         if "FAILED" in event['solve_status']:
            failed_html += event['event_id'] + " " + event['solve_status'] + "\n"
         else:
            event_url = event['solution']['sol_dir'].replace("/mnt/ams2/meteor_archive/", "http://archive.allsky.tv/")
            solved_html += event['event_id'] + " " + event['solve_status'] + " " + event_url + "/index.html\n"
      else:
         if "solution" in event:
            if event["solution"] != 0:
               solved_html += event['event_id'] + " Solved.\n"

         else:
            not_solved_html += event['event_id'] + " Not solved.\n"
      #solve_event(event['event_id'])
   print(solved_html)
   print(failed_html)
   print(not_solved_html)

def get_best_obs(obs):
   best_dist = 99999
   best_file = None
   for file in obs:
      if best_file is None:
         best_file = file

      mid_x = np.mean(obs[file]['xs'])
      mid_y = np.mean(obs[file]['ys'])
      dist_to_center = calc_dist((mid_x,mid_y), (1920/2, 1080/2))
      if dist_to_center < best_dist:
         best_file = file
         best_dist = dist_to_center


   print("BEST:", best_file)
   return(best_file)

def solve_month(wild):
   files = glob.glob("/mnt/ams2/meteors/" + wild + "*")
   mets = []
   for file in files:
      if cfe(file, 1) == 1:
         mets.append(file)
   for file in mets:
      day = file.split("/")[-1]
      solve_day(day)

def solve_day(day):
   os.system("./DynaDB.py cd " + day)
   dynamodb = boto3.resource('dynamodb')
   json_conf = load_json_file("../conf/as6.json")
   my_station = json_conf['site']['ams_id']
   stations = json_conf['site']['multi_station_sync']
   if my_station not in stations:
      stations.append(my_station)

   events = search_events(dynamodb, day, stations)
   print("EV:", events)
   for event in events:
      print("DY EV:", event['event_id'])
      solve_event(event['event_id'])

def solve_event(event_id, force=1, time_sync=1):
    print("EVID:", event_id)
    json_conf = load_json_file("../conf/as6.json")
    ams_id = json_conf['site']['ams_id']
    solve_dir = "/mnt/ams2/meteor_archive/" + ams_id + "/EVENTS/"
    nsinfo = load_json_file("../conf/network_station_info.json")

    dynamodb = boto3.resource('dynamodb')
    event = get_event(dynamodb, event_id, 0)
    print("EVID:", event_id)
    print(event)
    if "solution" in event and force != 1:
       if "solve_status" in event:
          if "FAIL" in event['solve_status']:
             print("The event ran and failed.")
             return()
          else:
             print("The event ran and passed.")
             return()


    obs = {}
    print("EV:", event_id, event)
    if len(event) == 0:
       return()

    bad_obs = []
    for i in range(0, len(event['stations'])):
       t_station = event['stations'][i]
       t_file = event['files'][i]
       print(t_station, t_file)
       dy_obs_data = get_obs(dynamodb, t_station, t_file)
       dy_obs_data['loc'] = nsinfo[t_station]['loc']
       obs_data = convert_dy_obs(dy_obs_data, obs )

    for key in obs_data:
       print(key, obs_data[key])

    # get WMPL ID (lowest start time)
    start_times = []
    for station_id in obs:
        if len(obs[station_id].keys()) > 1:
           file = get_best_obs(obs[station_id])
        else:
           for bfile in obs[station_id]:
               file = bfile


        if len(obs[station_id][file]['times']) > 0:
           start_times.append(obs[station_id][file]['times'][0])
        else:
           bad_obs.append(station_id + " missing reduction.")

    if len(start_times) == 0:
       print("PROB: NO DATA?", event_id)
       return()

    event_start = sorted(start_times)[0]
    print("START TIMES:", start_times)
    print("WMPL START:", event_start)

    day = event_start[0:10]
    day = day.replace("-", "_")
    e_dir = event_start.replace("-", "")
    e_dir = e_dir.replace(":", "")
    e_dir = e_dir.replace(" ", "_")
    solve_dir += day + "/" + e_dir 
    print("SOLVE DIR:", solve_dir)
    if cfe(solve_dir, 1) == 0:
       os.makedirs(solve_dir)

    if cfe(solve_dir, 1) == 1:
       print("SOLVE DIR EXISTS FROM PAST RUN DELETE CONTENTS.")
       files = glob.glob(solve_dir + "/*")
       for file in files:
          print("DEL:", file)
       #xxx = input("DELETE PAST FILES?")
       os.system("rm " + solve_dir + "/*")

    print("SOLVE WITH THESE OBS:")
    for key in obs_data:
       print(key)
    sol = simple_solvev2(obs_data)
    print("SIMPLE:", sol)
    save_json_file(solve_dir + "/" + event_id + "-simple.json", sol)
    save_json_file(solve_dir + "/" + event_id + "-obs.json", obs)
    print("SAVED FILES IN:", solve_dir)
    if len(bad_obs) > 0:
       print("BAD OBS!", bad_obs)
       obs_data = {}
       solution = {}
       update_event_sol(None, event_id, solution, obs_data, str(bad_obs))
       return()
    else: 
       WMPL_solve(obs_data, time_sync)

    solved_files = glob.glob(solve_dir + "/*")
    if len(solved_files) > 10:
       simple_status = 1
       wmpl_status = 1
    else:
       simple_status = 1
       wmpl_status = 0

    resp = make_event_json(event_id, solve_dir)
    
    if resp == 0:
       print("FAILED TO SOLVE!")
       solution = {}
       #solution['obs'] = obs_data
       if time_sync == 0:
          update_event_sol(None, event_id, solution, obs_data, "WMPL FAILED. TIME SYNC FAILED.")
       else:
          update_event_sol(None, event_id, solution, obs_data, "WMPL FAILED.")

       return(0)
    solution,as_obs = resp

    print("EVID:", event_id)
    print("UPDATE EVENT SOL:")
    if time_sync == 1:
       update_event_sol(None, event_id, solution, as_obs, "SUCCESS")
    if time_sync == 0:
       update_event_sol(None, event_id, solution, as_obs, "TIME SYNC FAIL")

    event_file = solve_dir + "/" + event_id + "-event.json"

    make_event_html(event_file)

    # remove the pngs and then copy the results to the cloud dir
    cloud_dir = solve_dir.replace("/mnt/ams2/meteor_archive/", "/mnt/archive.allsky.tv/")
    if cfe(cloud_dir,1) == 0:
       os.makedirs(cloud_dir)
    cmd = "rm " + solve_dir + "/*.png"
    print(cmd)
    os.system(cmd)
    cmd = "cp " + solve_dir + "/* " + cloud_dir
    print(cmd)
    os.system(cmd)



    #update_event(dynamodb, event_id, simple_status, wmpl_status, solve_dir)

def make_css():
   css = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
.container {
  padding: 5px;
  float: left;
  position: relative;
  width: 320px;
}

.image {
  opacity: 1;
  display: block;
  width: 100%;
  height: auto;
  transition: .5s ease;
  backface-visibility: hidden;
}

.middle {
  top: 50%;
  left: 50%;
  width: 100%
  transition: .5s ease;
  opacity: 0;
  position: absolute;
  text-align: center;
  transform: translate(-50%, -50%);
  -ms-transform: translate(-50%, -50%);
}

.container:hover .image {
  opacity: 0.3;
}

.container:hover .middle {
  opacity: 1;
}

.text {
  color: black;
  font-size: 16px;
}
</style>
</head>
<body>


   """
   return(css)

  #background-color: #0c0c0c;

def make_event_html(event_json_file):
   css = make_css()
   dynamodb = None
   obs_file = event_json_file.replace("-event.json", "-obs.json")
   event_data = load_json_file(event_json_file)
   solve_dir = event_data['sol_dir']
   xxx = solve_dir.split("/")[-1]
 

   event_id = event_data['event_id']
   event = get_event(dynamodb, event_id, 0)

   event_file = solve_dir + "/" + event_id + "-event.json"
   event_index_file = solve_dir + "/index.html" 
   kml_file = solve_dir + "/" + event_id + "-map.kml"

   sd = solve_dir.split("/")[-1]
   if "." in sd:
      temp = sd.split(".")
      sdd = temp[0]
   else:
      sdd = sd 

   report_file = solve_dir + "/" + sdd + "_report.txt"
   if "/mnt/ams2" in kml_file:
      kml_file = kml_file.replace("/mnt/ams2", "")
   if "solution" not in event:
      print("NO SOLUTION IN EVENT!", event)
   print("EVENT SOL:", event['solution'])
   if event['solution'] == 0:
      print("solve failed.")
      return(0)
   orb_link = event['solution']['orb']['link']

   print("EVENT ID IS:", event_id)
   print("SOL DIR IS:", solve_dir)
   #obs_data = load_json_file(obs_file)
   obs_data = event['obs']
   # make the obs part
   sum_html = make_sum_html(event_id, event, solve_dir, obs_data)

   obs_html = make_obs_html(event_id, event, solve_dir, obs_data)

   center_lat, center_lon = center_obs(obs_data)

   kml_file = kml_file.replace("/meteor_archive/", "https://archive.allsky.tv/")
   
   map_html = "<div style='clear: both'> &nbsp; </div>"
   map_html += "<div>"
   map_html += "<h2>Trajectory</h2>"
   map_html += "<iframe src=\"https://archive.allsky.tv/APPS/dist/maps/index.html?mf=" + kml_file + "&lat=" + str(center_lat) + "&lon=" + str(center_lon) + "\" width=800 height=440></iframe><br><a href=" + kml_file + ">KML</a><br>"

   map_html += "</div>"

   if orb_link != "" and orb_link != "#":
      orb_html = "<h2>Orbit</h2>"
      orb_html += "<iframe border=0 src=\"" + orb_link + "\" width=800 height=440></iframe><br><a href=" + orb_link + ">Orbit</a><br>"
   else:
      orb_html = ""



   plot_html = "<h2>Plots</h2>"
   plot_html += "<div>\n"
   sol_jpgs = glob.glob(solve_dir + "/*.jpg")
   for img in sorted(sol_jpgs):
      print("PLOT IMAGE:", img)
      img = img.replace("/mnt/ams2/meteor_archive/", "https://archive.allsky.tv/")
      if "ground" not in img and "orbit" not in img:
         plot_html += "<div style='float:left; padding: 3px'><img width=600 height=480 src=" + img + "></div>\n"

   plot_html += "</div>"

   # final report
   if cfe(report_file) == 1:
      rpt = open(report_file) 
      rpt_out = "<div style='clear:both'> &nbsp; </div><br>"
      rpt_out += "<h2>WMPL Report</h2><div><pre>"
      for line in rpt:
         print("LINE:", line)
         rpt_out += line
      rpt_out += "</pre></div>"
   else:
      rpt_out = ""

   fp = open(event_index_file, "w")
   fp.write(css)
   fp.write(sum_html)
   fp.write(obs_html)
   fp.write(map_html)
   fp.write(orb_html)
   fp.write(plot_html)
   fp.write(rpt_out)
   fp.close() 


def make_sum_html(event_id, event, solve_dir, obs):
   XXX = "xxx"
   tj = event['solution']['traj']
   ob = event['solution']['orb']
   if "duration" in event:
      duration = float(event['duration'])
   else:
      duration = float(0)
   shower_code = event['solution']['shower']['shower_code']
   html = "<h2>Event Summary</h2>"
   html += "<table border=0 padding=3><tr><td>"
   html += "<table border=0 padding=5>"
   html += "<tr><td>Event ID</td>"
   html += "<td>" + str(event_id) + "</td></tr>"
   html += "<tr><td>Start Time</td>"
   html += "<td>" + str(event['start_datetime'][0]) + "</td></tr>"
   html += "<tr><td>Duration</td>"
   html += "<td>" + str(duration) + "</td></tr>"
   html += "<tr><td>Start Height &nbsp; &nbsp; &nbsp; </td>"
   html += "<td>" + str(tj['start_ele']/1000)[0:5] + " km</td></tr>"
   html += "<tr><td>End Height</td>"
   html += "<td>" + str(tj['end_ele']/1000)[0:5] + " km</td></tr>"
   html += "<tr><td>Vel Init</td>"
   html += "<td>" + str(tj['v_init']/1000)[0:5] + " km/s</td></tr>"
   html += "<tr><td>Vel Avg</td>"
   html += "<td>" + str(tj['v_avg']/1000)[0:5] + " km/s</td></tr>"
   html += "<tr><td>Shower</td>"
   html += "<td>" + str(shower_code) + "</td></tr>"
   html += "</table>"

   html += "</td><td> &nbsp; &nbsp; </td><td>"
   html += "<table border=0>"
   html += "<tr><td>Semi Major Axis (a)</td>"
   html += "<td>" + str(ob['a'])[0:5] + "</td></tr>"
   html += "<tr><td>Eccentricty (e)</td>"
   html += "<td>" + str(ob['e'])[0:5] + "</td></tr>"
   html += "<tr><td>Inclination (i)</td>"
   html += "<td>" + str(ob['i'])[0:5] + "</td></tr>"
   html += "<tr><td>Peri (peri)</td>"
   html += "<td>" + str(ob['peri'])[0:5] + "</td></tr>"
   html += "<tr><td>Lon of Asc Node (node) &nbsp; &nbsp; &nbsp; </td>"
   html += "<td>" + str(ob['node'])[0:5] + "</td></tr>"
   #html += "<tr><td>q</td>"
   #html += "<td>" + str(ob['q'])[0:5] + "</td></tr>"
   html += "<tr><td>Period (T)</td>"

   if "T" in ob:
      html += "<td>" + str(ob['T'])[0:5] + "</td></tr>"
      print("T IS :", ob['T'])
   else: 
      html += "<td>" + "No Period Value!" + "</td></tr>"
      print("T IS MISSING FOR OB:" )
   html += "<tr><td>Mean Anomaly (M)</td>"
   html += "<td>" + str(ob['mean_anomaly'])[0:5] + "</td></tr>"
   html += "<tr><td>Julian Date (JD)</td>"
   html += "<td>" + str(ob['jd_ref']) + "</td></tr>"

   html += "</table>"
   html += "</td></tr>"
   html += "</table>"

   return(html)

def make_obs_html(event_id, event, solve_dir, obs):
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
         start_az =  event['obs'][station_id][file]['azs'][0]
         end_az =  event['obs'][station_id][file]['azs'][-1]
         start_el =  event['obs'][station_id][file]['els'][0]
         end_el =  event['obs'][station_id][file]['els'][-1]
         dur =  len(event['obs'][station_id][file]['els']) / 25

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


def convert_dy_obs(dy_obs_data, obs):
   #print("DYO:", dy_obs_data)
   station = dy_obs_data['station_id']
   fn = dy_obs_data['sd_video_file']
   if station not in obs:
      obs[station] = {}
   if fn not in obs[station]:
      obs[station][fn] = {}

   calib = dy_obs_data['calib'] 
   obs[station][fn]['loc'] = dy_obs_data['loc']
   obs[station][fn]['calib'] = dy_obs_data['calib']
   obs[station][fn]['times'] = []
   obs[station][fn]['fns'] = []
   obs[station][fn]['xs'] = []
   obs[station][fn]['ys'] = []
   obs[station][fn]['azs'] = []
   obs[station][fn]['els'] = []
   obs[station][fn]['ras'] = []
   obs[station][fn]['decs'] = []
   obs[station][fn]['ints'] = []
   obs[station][fn]['revision'] = float(dy_obs_data['revision'])

   for row in dy_obs_data['meteor_frame_data']:
      (dt, frn, x, y, w, h, oint, ra, dec, az, el) = row
      obs[station][fn]['times'].append(dt)
      obs[station][fn]['fns'].append(float(frn))
      obs[station][fn]['xs'].append(float(x))
      obs[station][fn]['ys'].append(float(y))
      obs[station][fn]['azs'].append(float(az))
      obs[station][fn]['els'].append(float(el))
      obs[station][fn]['ras'].append(float(ra))
      obs[station][fn]['decs'].append(float(dec))
      obs[station][fn]['ints'].append(float(oint))
      


   obs[station][fn]['gc_azs'], obs[station][fn]['gc_els'] = GC_az_el(obs[station][fn]['azs'], obs[station][fn]['els'])

   print("OBS:", obs)
   return(obs)

def make_orbit_link(event_id, orb):
   if orb['a'] is None:
      link = ""
   else:
      link = "http://orbit.allskycams.com/index_emb.php?name={:s}&epoch={:f}&a={:f}&M={:f}&e={:f}&I={:f}&Peri={:f}&Node={:f}&P={:f}&q={:f}&T={:f}#".format(event_id, orb['jd_ref'], orb['a'], orb['mean_anomaly'], orb['e'], orb['i'], orb['peri'], orb['node'], orb['T'], orb['q'], orb['jd_ref'])
   #try:
   #   link = "http://orbit.allskycams.com/index_emb.php?name={:s}&epoch={:f}&a={:f}&M={:f}&e={:f}&I={:f}&Peri={:f}&Node={:f}&P={:f}&q={:f}&T={:f}#".format(event_id, orb['jd_ref'], orb['a'], orb['mean_anomaly'], orb['e'], orb['i'], orb['peri'], orb['node'], orb['T'], orb['q'], orb['jd_ref'])
   #except:
   #   link = ""
   return(link)

def make_event_json(event_id, solve_dir):

   import pickle
   jpgs = glob.glob(solve_dir + "/*.jpg")
   jsons = glob.glob(solve_dir + "/*.json")
   pks = glob.glob(solve_dir + "/*.pickle")

   for js in jsons:
      if "obs.json" in js:
         obs_file = js
         kml_file = js.replace("-obs.json", "-map.kml")
      if "simple.json" in js:
         sol_file = js

   print("SOL DIR:", solve_dir)
   print("SOL:", sol_file)
   simple_solve = load_json_file(sol_file)


   as_obs = load_json_file(obs_file)

   event_file = sol_file.replace("-simple.json", "-event.json")

   print("OBS:", as_obs) 
   print("SIMPLE:", simple_solve) 

   points = []
   lines = []
   

   station_data = {}
   for station_id in as_obs:
      for file in as_obs[station_id]:
         if station_id not in station_data:
            obs_data = as_obs[station_id][file]
            print(station_id)
            lat, lon, alt = obs_data['loc']
            station_data[station_id] = obs_data['loc']
            points.append((lon,lat,alt,station_id))

   durs = []
   for ss in simple_solve:
      print(ss)
      sol_key, start_lat, start_lon, start_ele, end_lat, end_lon, end_ele, dist, dur, vel = ss 
      durs.append(dur)
      (skey1,skey2) = sol_key.split("_")
      station1,cam1 = skey1.split("-")
      station2,cam2 = skey2.split("-")
      ol_start_lat = station_data[station2][0]
      ol_start_lon = station_data[station2][1]
      ol_start_alt = station_data[station2][2]
      line_desc = "OL:" + sol_key
      lines.append((ol_start_lon,ol_start_lat,ol_start_alt,start_lon,start_lat,start_ele,line_desc))
      lines.append((ol_start_lon,ol_start_lat,ol_start_alt,end_lon,end_lat,end_ele,line_desc))

      line_desc = "SS:" + sol_key
      
      lines.append((start_lon,start_lat,start_ele,end_lon,end_lat,end_ele,line_desc))

   if len(durs) > 0:
      duration = float(max(durs) / 25)
   else:
      duration = float(0)

   solution = {}
   solution['event_id'] = event_id
   solution['duration'] = float(duration)
   solution['sol_dir'] = solve_dir 
#   solution['obs'] = as_obs
   solution['simple_solve'] = simple_solve
   solution['traj'] = {}
   solution['orb'] = {}
   solution['rad'] = {}
   solution['plot'] = {}
   solution['kml'] = {}
   solution['shower'] = {}

   if len(pks) == 0:
      print("WMPL FAILED. NO EVENT JSON MADE.")
      return(0)

   f = open(pks[0], 'rb')
   traj = pickle.load(f)

   html = "<PRE>"
   pdata = vars(traj)

   solution['traj']['start_lat'] = float(np.degrees(traj.rbeg_lat))
   solution['traj']['start_lon'] = float(np.degrees(traj.rbeg_lon))
   solution['traj']['start_ele'] = float(traj.rbeg_ele)

   solution['traj']['end_lat'] = float(np.degrees(traj.rend_lat))
   solution['traj']['end_lon'] = float(np.degrees(traj.rend_lon))
   solution['traj']['end_ele'] = float(traj.rend_ele)

   lines.append(( float(np.degrees(traj.rbeg_lon)), float(np.degrees(traj.rbeg_lat)), float(traj.rbeg_ele), float(np.degrees(traj.rend_lon)), float(np.degrees(traj.rend_lat)), float(traj.rend_ele), "WMPL"))

   # get 3d points for traj
   for obs in traj.observations:

      # Go through all observed points
      for i in range(obs.kmeas):

         point_info = []
 
         # FN
         point_info.append("{:3d}".format(i))

         point_info.append("{:>10s}".format(str(obs.station_id)))

         #point_info.append("{:>7d}".format(obs.ignore_list[i]))

         #point_info.append("{:9.6f}".format(obs.time_data[i]))
         #point_info.append("{:20.12f}".format(obs.JD_data[i]))

         #point_info.append("{:9.5f}".format(np.degrees(obs.meas1[i])))
         #point_info.append("{:9.5f}".format(np.degrees(obs.meas2[i])))

         #point_info.append("{:22.5f}".format(np.degrees(obs.azim_data[i])))
         #point_info.append("{:9.5f}".format(np.degrees(obs.elev_data[i])))

         #point_info.append("{:15.5f}".format(np.degrees(obs.model_azim[i])))
         #point_info.append("{:14.5f}".format(np.degrees(obs.model_elev[i])))

         #point_info.append("{:12.5f}".format(np.degrees(obs.ra_data[i])))
         #point_info.append("{:+13.5f}".format(np.degrees(obs.dec_data[i])))

         #point_info.append("{:13.5f}".format(np.degrees(obs.model_ra[i])))
         #point_info.append("{:+14.5f}".format(np.degrees(obs.model_dec[i])))

         #point_info.append("{:11.2f}".format(obs.model_eci[i][0]))
         #point_info.append("{:11.2f}".format(obs.model_eci[i][1]))
         #point_info.append("{:11.2f}".format(obs.model_eci[i][2]))

         #point_info.append("{:14.6f}".format(np.degrees(obs.model_lat[i])))
         #point_info.append("{:+15.6f}".format(np.degrees(obs.model_lon[i])))
         #point_info.append("{:10.2f}".format(obs.model_ht[i]))
         #point_info.append("{:10.2f}".format(obs.model_range[i]))


         #points.append(( float(np.degrees(obs.model_lon[i])), float(np.degrees(obs.model_lat[i])), float(obs.model_ht[i]), "3DP:" + str(obs.station_id) + "_{:03d}".format(i)))
         points.append(( float(np.degrees(obs.model_lon[i])), float(np.degrees(obs.model_lat[i])), float(obs.model_ht[i]), "3DP:" + str(obs.station_id) + "_{:3d}".format(i)))

         #point_info.append("{:10.2f}".format(obs.length[i]))
         #point_info.append("{:19.2f}".format(obs.state_vect_dist[i]))
         #point_info.append("{:8.2f}".format(obs.lag[i]))

         #point_info.append("{:9.2f}".format(obs.velocities[i]))
         #point_info.append("{:18.2f}".format(obs.velocities_prev_point[i]))

         #point_info.append("{:9.2f}".format(obs.h_residuals[i]))
         #point_info.append("{:9.2f}".format(obs.v_residuals[i]))
         #point_info.append("{:14.2f}".format(3600*np.degrees(obs.ang_res[i])))





   make_kml(kml_file, points, lines)
   #print("SHOWER:" , traj.orbit.la_sun, traj.orbit.L_g, traj.orbit.B_g, traj.orbit.v_g)
   if traj.orbit.la_sun is not None:
      shower_obj = associateShower(traj.orbit.la_sun, traj.orbit.L_g, traj.orbit.B_g, traj.orbit.v_g)

      if shower_obj is None:
         shower_no = -1
         shower_code = '...'
      else:
         shower_no = shower_obj.IAU_no
         shower_code = shower_obj.IAU_code
   else:
         shower_no = -1
         shower_code = '...'



   solution['kml']['points'] = points
   solution['kml']['lines'] = lines

   solution['shower'] = {}
   solution['shower']['shower_no'] = float(shower_no)
   solution['shower']['shower_code'] = shower_code


   solution['traj']['v_init'] = float(traj.v_init)
   solution['traj']['v_avg'] = float(traj.v_avg)

   solution['orb']['jd_ref'] = traj.orbit.jd_ref
   if traj.orbit.la_sun is not None:
      solution['orb']['la_sun'] = np.degrees(traj.orbit.la_sun)
      solution['orb']['i'] = float(np.degrees(traj.orbit.i))
      solution['orb']['peri'] = float(np.degrees(traj.orbit.peri))
      solution['orb']['node'] = float(np.degrees(traj.orbit.node))
      solution['orb']['pi'] = float(np.degrees(traj.orbit.pi))
      solution['orb']['true_anomaly'] = float(np.degrees(traj.orbit.true_anomaly))
      if math.isnan(solution['orb']['true_anomaly']):
         solution['orb']['true_anomaly'] = 0
   else:
      solution['orb']['la_sun'] = 0
      solution['orb']['i'] = 0
      solution['orb']['peri'] = 0
      solution['orb']['node'] = 0
      solution['orb']['pi'] = 0
      solution['orb']['true_anomaly'] = 0
   solution['orb']['a'] = traj.orbit.a
   solution['orb']['e'] = traj.orbit.e
   solution['orb']['q'] = traj.orbit.q
   solution['orb']['Q'] = traj.orbit.Q
   if traj.orbit.true_anomaly is not None:
      if math.isnan(traj.orbit.true_anomaly) is True:
         solution['orb']['true_anomaly'] = 0
   if solution['orb']['true_anomaly'] == 0:
      solution['orb']['eccentric_anomaly'] = 0
      solution['orb']['mean_anomaly'] = 0
      solution['orb']['T'] = 0 
   else:
      if traj.orbit.eccentric_anomaly is not None and math.isnan(traj.orbit.eccentric_anomaly) is False:
         solution['orb']['eccentric_anomaly'] = float(np.degrees(traj.orbit.eccentric_anomaly))

         solution['orb']['mean_anomaly'] = float(np.degrees(traj.orbit.mean_anomaly))
      else:
         solution['orb']['eccentric_anomaly'] = 0
         solution['orb']['mean_anomaly'] = 0

   if traj.orbit.T is None:
      print("T IS NONE!")
      traj.orbit.T = 0
   if math.isnan(traj.orbit.T):
      print("T IS NAN!")
   #xxx = input("wait. for T:" + str(traj.orbit.T))
   if traj.orbit.T is not None:
      if math.isnan(traj.orbit.T) is True:
         solution['orb']['T'] = 0 
      else:
         solution['orb']['T'] = traj.orbit.T

   solution['rad']['apparent_ECI'] = {}
   solution['rad']['apparent_ECI']['ra'] = traj.orbit.ra
   solution['rad']['apparent_ECI']['dec'] = traj.orbit.dec
   solution['rad']['apparent_ECI']['v_avg'] = traj.orbit.v_avg
   solution['rad']['apparent_ECI']['v_inf'] = traj.orbit.v_inf
   solution['rad']['apparent_ECI']['azimuth_apparent'] = traj.orbit.azimuth_apparent
   solution['rad']['apparent_ECI']['elevation_apparent'] = traj.orbit.elevation_apparent

   solution['rad']['geocentric'] = {}
   solution['rad']['geocentric']['ra_g'] = traj.orbit.ra_g
   solution['rad']['geocentric']['dec_g'] = traj.orbit.dec_g
   solution['rad']['geocentric']['v_g'] = traj.orbit.v_g

   solution['rad']['ecliptic_geo'] = {}
   solution['rad']['ecliptic_geo']['L_g'] = traj.orbit.L_g
   solution['rad']['ecliptic_geo']['B_g'] = traj.orbit.B_g
   solution['rad']['ecliptic_geo']['v_h'] = traj.orbit.v_h

   solution['rad']['ecliptic_helio'] = {}
   solution['rad']['ecliptic_helio']['L_h'] = traj.orbit.L_h
   solution['rad']['ecliptic_helio']['B_h'] = traj.orbit.B_h
   solution['rad']['ecliptic_helio']['v_h_x'] = traj.orbit.v_h_x
   solution['rad']['ecliptic_helio']['v_h_y'] = traj.orbit.v_h_y
   solution['rad']['ecliptic_helio']['v_h_z'] = traj.orbit.v_h_z


   print(traj.orbit.e)
   print(traj.orbit.i)
   print(traj.orbit.peri)
   print(traj.orbit.node)
   print(traj.orbit.pi)
   print(traj.orbit.q)
   print(traj.orbit.Q)
   print(traj.orbit.true_anomaly)
   print(traj.orbit.eccentric_anomaly)
   print(traj.orbit.mean_anomaly)
   print("T", traj.orbit.T)
   print("TJ", traj.orbit.Tj)
   for line in str(traj.orbit).split("\n"):
      print("ORB:", line)

   ef , xxx = fn_dir(event_file)
   sol_name = ef[0:20]
   orb_link = make_orbit_link(ef, solution['orb'])
   solution['orb']['link'] = orb_link

   for obs in traj.observations:
      print(obs.station_id, obs.time_data)

   solution['event_id'] = event_id
   solution['obs'] = as_obs
   save_json_file(event_file, solution)
   print("SAVED EVENT FILE:", event_file)
   return(solution,as_obs)

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
         pnt.style.iconstyle.icon.href = 'http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png'
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
#simplekml.Color.darkgoldenrod
         pnt.style.labelstyle.scale = 1
         pnt.style.iconstyle.icon.href = 'http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png'
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




def event_report(solve_dir, obs):
    json_conf = load_json_file("../conf/as6.json")
    remote_urls = {}
    if "remote_urls" in json_conf['site']:
       for i in range(0, len(json_conf['site']['multi_station_sync'])):
          station = json_conf['site']['multi_station_sync'][i]
          url = json_conf['site']['remote_urls'][i]
          remote_urls[station] = url
          print(station, url)

    solved_files = glob.glob(solve_dir + "/*")
    print(solve_dir + "*", solved_files)
    html = ""
    report = ""

    for station_id in obs:
        if len(obs[station_id].keys()) > 1:
            file = get_best_obs(obs[station_id])
        else:
            for bfile in obs[station_id]:
                file = bfile
        prev_file = file.replace(".mp4", "-prev.jpg")
        year = file[0:4]
        day = file[0:10]
        link = remote_urls[station_id] + "/meteors/" + station_id + "/" + day + "/" + file + "/"
        html += "<h1>" + station_id + " " + file + "</h1>"
        #html += "<a href=" + link + ">"
        html += "<img src=https://archive.allsky.tv/" + station_id + "/METEORS/" + year + "/" + day + "/" + station_id + "_" + prev_file + "></a>"
        html += "<hr>"


    jpgs = []
    for sf in solved_files:
       if "report" in sf:
          fp = open(sf, "r")
          for line in fp:
             report += line
       if "png" in sf:
          jpg_f = sf.replace(".png", ".jpg")
          jpgs.append(jpg_f)
          cmd = "convert " + sf + " -resize 600x600 -quality 60 " + jpg_f
          #if cfe(jpg_f) == 0:
          if True:
             print(cmd)
             os.system(cmd)
          else:
             print(jpg_f, " already made.")

    for jpg in jpgs:
       jpg = jpg.replace("/mnt/ams2/meteor_archive/", "")
       html += "<img src=" + jpg + ">"
    html += "<p>"
    html += "<pre>" + report + "</pre>"
    fp = open(solve_dir + "/index.html", "w")
    fp.write(html)
    print("SAVED INDEX:", solve_dir + "/index.html")




def WMPL_solve(obs,time_sync=1):
    json_conf = load_json_file("../conf/as6.json")
    ams_id  = json_conf['site']['ams_id']
    solve_dir = "/mnt/ams2/meteor_archive/" + ams_id + "/EVENTS/"
    # Inputs are RA/Dec
    meastype = 2

    # Reference julian date
    start_times = []
    for station_id in obs:
        if len(obs[station_id].keys()) > 1:
           file = get_best_obs(obs[station_id])
        else:
           for bfile in obs[station_id]:
               file = bfile


        if len(obs[station_id][file]['times']) > 0:
           start_times.append(obs[station_id][file]['times'][0])   

    event_start = sorted(start_times)[0]
     
    day = event_start[0:10]
    day = day.replace("-", "_")
    e_dir = event_start.replace("-", "")
    e_dir = e_dir.replace(":", "")
    e_dir = e_dir.replace(" ", "_")
    solve_dir += day + "/" + e_dir 


    event_start_dt = datetime.datetime.strptime(event_start, "%Y-%m-%d %H:%M:%S.%f")
    jd_ref = trajconv.datetime2JD(event_start_dt)
    #print(event_start_dt, jd_ref)


    # Init new trajectory solving
    if time_sync == 1:
       etv = True
    else:
       etv = False
    traj_solve = traj.Trajectory(jd_ref, output_dir=solve_dir, meastype=meastype, save_results=True, monte_carlo=False, show_plots=False, max_toffset=3,v_init_part=.5, estimate_timing_vel=etv)
   
    for station_id in obs:
        if len(obs[station_id].keys()) > 1:
            file = get_best_obs(obs[station_id])
        else:
            for bfile in obs[station_id]:
                file = bfile
         
        if True:
            lat,lon,alt = obs[station_id][file]['loc']
            lat,lon,alt = float(lat), float(lon), float(alt)
            if "azs_gc" in obs[station_id][file]:
               azs = np.radians(obs[station_id][file]['azs_gc'])
               els = np.radians(obs[station_id][file]['els_gc'])
            else:
               azs = np.radians(obs[station_id][file]['azs'])
               els = np.radians(obs[station_id][file]['els'])
            times = obs[station_id][file]['times']
            print("STATION:", station_id)
            print("FILE:", file)
            print("TIMES:", times)
            print("LAT:", lat)
            print("LON:", lon)
            print("ALT:", alt)
            print("AZ:", azs)
            print("ELS:", els)
            if len(azs) == 0:
                continue
            times = []
            for i in range(0,len(azs)):
                times.append(i/25)
        
            # Set input points for the first site
            traj_solve.infillTrajectory(azs, els, times, np.radians(float(lat)), np.radians(float(lon)), alt, station_id=station_id)
            print("-----")


    traj_solve.run()



    #mj['wmpl'] = e_dir
    #save_json_file(meteor_file, mj)
    #print("Saved:", meteor_file) 

    solved_files = glob.glob(solve_dir + "*")
    if len(solved_files) == 0:
       print("FAILED TO SOLVE.")
       for station_id in obs:
          if len(obs[station_id].keys()) > 1:
             file = get_best_obs(obs[station_id])
          else:
             for bfile in obs[station_id]:
                file = bfile
          print(station_id, file, obs[station_id][file]['times'])
    else:
       print(solve_dir )
       for sf in solved_files:
          print(sf)
       event_report(solve_dir, obs)


def center_obs(obs_data):
   lats = []
   lons = []
   for st in obs_data:
      for fn in obs_data[st]:
         lat,lon,alt = obs_data[st][fn]['loc']
      lats.append(float(lat))
      lons.append(float(lon))
   return(np.mean(lats),np.mean(lons))


cmd = sys.argv[1]
meteor_file = sys.argv[2]

#event_json_file = "/mnt/ams2/meteor_archive/AMS1/EVENTS/2021_01_03/20210103_074325.960/20210103_074323-event.json"
#make_event_html(event_json_file)
#exit()


if cmd == "solve":
   mj = load_json_file(meteor_file)
   obs = mj['multi_station_event']['obs']
   WMPL_solve(obs)
if cmd == "report":
   WMPL_report(meteor_file)
if cmd == "se":
   solve_event(meteor_file)
if cmd == "sd":
   solve_day(meteor_file)
if cmd == "mej":
   make_event_json(meteor_file)
if cmd == "meh":
   make_event_html(meteor_file)
if cmd == "sm":
   solve_month(meteor_file)
if cmd == "status":
   solve_status(meteor_file)
