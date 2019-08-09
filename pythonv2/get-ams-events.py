#!/usr/bin/python3
# amsaware
# This script checks for AMS Fireball events and reports and
# checks the recordings of this device to see if the event was
# capture. If video files exist around the time of the event
# the files will be uploaded to the AMS for further analysis.
import settings
import sys
import os
import time as gtime
from os import listdir
from os.path import isfile, join
import json, requests
import numpy as np
from datetime import datetime, date, time, timedelta
from dateutil import parser
from lib.UtilLib import calc_radiant
from lib.FileIO import save_json_file, load_json_file

def run_orbit_for_event(data):
   event_time, start_lat, start_lon, start_alt, end_lat, end_lon, end_alt, vel = data
   arg_date, arg_time = event_time.split(" ")
   rah,dech,az,el,track_dist,entry_angle = calc_radiant(float(end_lon),float(end_lat),float(end_alt),float(start_lon),float(start_lat),float(start_alt),arg_date, arg_time)
   rah = str(rah).replace(":", " ")
   dech = str(dech).replace(":", " ")
   ra,dec= HMS2deg(str(rah),str(dech))

   dd = arg_date.replace("-", "")
   tt = arg_time.replace(":", "") + ".0"
   etime = dd + "-" + tt
   cmd = "cd /home/ams/dvida/WesternMeteorPyLib/wmpl/Trajectory; ./runOrb.py " + str(ra) + " " + str(dec) + " " + str(vel) + " " + str(etime) + " " + str(start_lat) + " " + str(start_lon) + " " + str(start_alt)
   print(cmd)
   os.system(cmd)
   print(etime, ra,dec)
   desc = event_time + "\n"
   desc = desc + "RA: " + str(ra)+ "\n"
   desc = desc + "DEC: " + str(dec)+ "\n"
   line = kml.newlinestring(name=event_time, description=desc, coords=[(start_lon,start_lat,start_alt*1000),(end_lon,end_lat,end_alt)])
   line.altitudemode = simplekml.AltitudeMode.relativetoground
   line.linestyle.color = "FF0000FF"
   line.linestyle.width= 5
   gc = gc + 1
   #else:
   #   print("BAD:", line)

   c = c + 1

   kml.save("ams-bolides.kml")


def get_events(myyear, min_reports, event_data):
   if event_data is None:
      event_data = {}
   api_key = "QwCsPJKr87y15Sy"
   url = settings.API_SERVER + "members/api/open_api/get_events"
   data = {'api_key' : api_key, 'year' : myyear, 'min_reports' : min_reports, 'format' : 'json'}
#, format' : 'json'}
   r = requests.get(url, params=data)
   my_data = r.json()
   for key in my_data['result']:
      okey = key
      #print(my_data['result'][okey])
      key = key.replace("Event #", "")
      key = key.replace("\n", "")
      event_data[key] = my_data['result'][okey]
      (y,e) = key.split("-")
      print (y,e)
   return(event_data)


def load_day_array(event_data, year, report_count, day_array = None):

   if day_array is None: 
      day_array = {}
   for d in range(1,367):
      if d not in day_array:
         day_array[d] = {}
      if year not in day_array[d]:
         day_array[d][year] = {}
      if "all_years_total" not in day_array[d]:
         day_array[d]['all_years_total'] = {}
      if report_count not in day_array[d]['all_years_total']:
         day_array[d]['all_years_total'][report_count] = 0

      day_array[d][year][report_count] = 0
      day_array[d][year]['utc_date'] = 0
      day_array[d]['utc_date'] = 0
      if 'years' not in day_array[d]:
         day_array[d]['years'] = []
      if d <= 365:
         dt = datetime(2010,1,1)
         dtdelta = timedelta(days=d-1)
         dt = dt + dtdelta
         day_array[d]['utc_date'] = dt.strftime("%Y-%m-%d")

   for event in event_data:
      utc_date, utc_time = event_data[event]['avg_date_utc'].split(" ")
      try:
         utc_datetime = datetime.strptime(event_data[event]['avg_date_utc'], "%Y-%m-%d %H:%M:%S")
         day_of_year = utc_datetime.timetuple().tm_yday
         print(utc_datetime, day_of_year)
         day_array[day_of_year][year][report_count] = day_array[day_of_year][year][report_count] + 1
         day_array[day_of_year]['all_years_total'][report_count] = day_array[day_of_year]['all_years_total'][report_count] + 1
         if year not in day_array[day_of_year]['years']:
            day_array[day_of_year]['years'].append(year)
         day_array[day_of_year][year]['utc_date'] = utc_date
         #day_array[day_of_year]['utc_date'] = utc_date
      except:
         print("BAD DATE OR EVENT!",  event)
         #day_array[day_of_year]['utc_date'] = utc_date


   for day in sorted(day_array):
      print(day, day_array[day][year]['utc_date'], day_array[day][year][report_count])

   return(day_array)

def load_jpl(day_array, event_data):
   jpl = open("fireball_data.csv", "r")
   jpl_data = {}

   for d in range(1,367):
      if d not in jpl_data:
         jpl_data[d] = 0
         sd = str(d)
         if "jpl" not in day_array[sd]:
            day_array[sd]['jpl'] = 0

   lc = 0
   for line in jpl:
      if lc >= 1:
         data = line.split(",")
         date = data[0]
         date = date.replace("\"", "")
         print(line)
         print(date)
         utc_datetime = datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
         day_of_year = str(utc_datetime.timetuple().tm_yday)
         print(day_of_year, date)
         year = date[0:4]
         if 'jpl' not in day_array[day_of_year]:
            day_array[day_of_year]['jpl'] = 1
         else:
            day_array[day_of_year]['jpl'] = day_array[day_of_year]['jpl'] + 1          
      lc = lc + 1

   for day in jpl_data:
      print(day, jpl_data[day])

   return(day_array, event_data)

def load_year(myyear, day_array, event_data):
   event_data = get_events(myyear, 10, event_data)
   day_array = load_day_array(event_data, myyear, "reports_10", day_array)
   return(day_array, event_data)

def close_approach_orbits():

   data_file = "amsdata/feb14-NEOs-unique.txt"
   #full_name,neo,epoch,epoch_mjd,epoch_cal,equinox,a,e,i,w,om,q,ma,ad,n,tp,tp_cal,per,per_y,moid,moid_ld

   fp = open(data_file, "r")
   lc = 0
   myneos = []
   os.system("rm amsdata/myneos.csv")
   for line in fp:
      line =line.replace("\n", "")
      if lc > 0:
         neo_name = line
         os.system("grep \"(" + neo_name + ")\" amsdata/neodb.csv >> amsdata/myneos.csv")
         myneos.append(neo_name)
      lc = lc + 1

   orb_file  = "amsdata/myneos.csv"
   fp = open(orb_file, "r")
   myorbs = {}
   for line in fp:
      line =line.replace("\n", "")
      line =line.replace("\"", "")
      full_name,neo,epoch,epoch_mjd,epoch_cal,equinox,a,e,i,w,om,q,ma,ad,n,tp,tp_cal,per,per_y,moid,moid_ld = line.split(",")
      print(full_name, epoch, equinox, a, e, i, w, om, q, ma, ad, n, tp, tp_cal, per, per_y, moid, moid_ld)
      myorbs[full_name] = {}
      name = full_name.replace(" ", "")
      myorbs[full_name]['name'] = name
      myorbs[full_name]['epoch'] = epoch
      myorbs[full_name]['utc_date'] = equinox
      myorbs[full_name]['T'] = epoch 
      myorbs[full_name]['vel'] = 0 
      myorbs[full_name]['a'] = a
      myorbs[full_name]['e'] = e
      myorbs[full_name]['I'] = i
      myorbs[full_name]['Peri'] = w
      myorbs[full_name]['Node'] = om
      myorbs[full_name]['q'] = q
      myorbs[full_name]['M'] = ma
      myorbs[full_name]['P'] = per_y

   save_json_file("amsdata/myorbs.json", myorbs)


   


def close_approach_data():
   data_file = "/mnt/NAS/cneos_closeapproach_data_1LD.csv"
   fp = open(data_file, "r")
   # object, date, ca_dist_nom, ca__dist_min, v_rel, v_inf, h_mag, est_size, x
   objects = {}
   ca_day_of_year = {}
    
   lc = 0
   for line in fp:
      line = line.replace("\n", "")
      line = line.replace("\"", "")
      data = line.split(",")
      if lc > 0:
         object, cn_date, ca_dist_nom, ca_dist_min, v_rel, v_inf, h_mag, est_size, x = data
         dist_vars = ca_dist_nom.split(" ")
         ld_dist = dist_vars[0] 
         date_vars = cn_date.split(" ")
         date = date_vars[0] 
         utc_datetime = datetime.strptime(date, "%Y-%b-%d")
         day_of_year = utc_datetime.timetuple().tm_yday
         if day_of_year not in ca_day_of_year:
            ca_day_of_year[day_of_year] = {}
            ca_day_of_year[day_of_year]['ca_count'] = 1
            ca_day_of_year[day_of_year]['objects'] = []
            ca_day_of_year[day_of_year]['objects'].append(object)
            ca_day_of_year[day_of_year]['date'] = date[5:11]
         else:
            ca_day_of_year[day_of_year]['ca_count'] = ca_day_of_year[day_of_year]['ca_count'] + 1
            ca_day_of_year[day_of_year]['objects'].append(object)

         if object not in objects:
            objects[object] = {}
            objects[object]['pass_count'] = 1
            objects[object]['pass_dates'] = []
            objects[object]['pass_dates'].append(date)
         else:
            objects[object]['pass_count'] = objects[object]['pass_count'] + 1
            objects[object]['pass_dates'].append(date)


         #print(object, day_of_year, date, ld_dist)
      lc = lc + 1

   for obj in objects:
      if objects[obj]['pass_count'] > 10:
         print(obj, objects[obj])

   for day in ca_day_of_year:
      print(day, ca_day_of_year[day]['date'], ca_day_of_year[day]['ca_count'])

   save_json_file("amsdata/ca_by_day.json", ca_day_of_year)
   save_json_file("amsdata/ca_objects.json", objects)

try:
   cmd = sys.argv[1]
except:
   print("missing cmd")

if cmd == 'run':

   day_array = None
   event_data = None
   all_event_data = {}

   myyear = 2019
   day_array, all_event_data[2019] = load_year(2019, day_array, event_data)
   day_array, all_event_data[2018] = load_year(2018, day_array, event_data)
   day_array, all_event_data[2017] = load_year(2017, day_array, event_data)
   day_array, all_event_data[2016] = load_year(2016, day_array, event_data)
   #day_array, all_event_data[2015] = load_year(2015, day_array, event_data)
   day_array, all_event_data[2014] = load_year(2014, day_array, event_data)
   day_array, all_event_data[2013] = load_year(2013, day_array, event_data)
   day_array, all_event_data[2012] = load_year(2012, day_array, event_data)
   day_array, all_event_data[2011] = load_year(2011, day_array, event_data)
   day_array, all_event_data[2010] = load_year(2010, day_array, event_data)
   day_array, all_event_data[2009] = load_year(2009, day_array, event_data)


   for day in day_array:
      all_years_total = day_array[day]['all_years_total']['reports_10']
      utc_date = day_array[day]['utc_date']
      print(day, utc_date, all_years_total)
   day_json_file = "amsdata/" + "event-totals-by-day.json"
   save_json_file(day_json_file, day_array)
   event_json_file = "amsdata/" + "ams-event-data.json"
   save_json_file(day_json_file, day_array)
   save_json_file(event_json_file, event_data)
elif cmd == 'jpl':   
   json_file = "amsdata/event-totals-by-day.json"
   ejson_file = "amsdata/ams-event-data.json"
   day_array = load_json_file(json_file)
   event_data = load_json_file(ejson_file)
   day_array, event_data = load_jpl(day_array, event_data)
   save_json_file(json_file, day_array)
   save_json_file(ejson_file, all_event_data)
elif cmd == 'ca':   
   close_approach_data()
elif cmd == 'cao':   
   close_approach_orbits()

elif cmd == 'rpt':   
   plot_days = []
   plot_events = []
   plot_years = []
   plot_scores = []
   json_file = "amsdata/event-totals-by-day.json"
   day_array = load_json_file(json_file)
   bin_data = {}
   bin_count = 0
   bin_data[0] = {}
   for day in day_array:
      if int(day) % 10 == 0:
         bin_count = bin_count + 1
         bin_data[bin_count] = {}
      if "reports_10" not in bin_data[bin_count]:
         bin_data[bin_count]['reports_10'] = 0
      bin_data[bin_count]['reports_10'] = bin_data[bin_count]['reports_10'] + day_array[day]['all_years_total']['reports_10'] 

      print(day, day_array[day]['utc_date'], day_array[day]['jpl'], day_array[day]['all_years_total']['reports_10'], len(day_array[day]['years']) , day_array[day]['all_years_total']['reports_10'] * len(day_array[day]['years']), (day_array[day]['all_years_total']['reports_10'] + day_array[day]['jpl']) * len(day_array[day]['years']) )
      plot_days.append(day)
      plot_events.append(day_array[day]['all_years_total']['reports_10'])
      plot_years.append(len(day_array[day]['years']))
      plot_scores.append(day_array[day]['all_years_total']['reports_10'] * len(day_array[day]['years']))

   bin_days = []
   bin_events = []
   for bind in bin_data:   
      print(bind, bin_data[bind])
      bin_days.append(bind)
      bin_events.append(bin_data[bind]['reports_10'])

   import matplotlib
   matplotlib.use('Agg')
   import matplotlib.pyplot as plt
   #fig = plt.figure()
   plt.plot(bin_days,bin_events)
   curve_file = "amsdata/events_by_day.png"
   plt.savefig(curve_file)

