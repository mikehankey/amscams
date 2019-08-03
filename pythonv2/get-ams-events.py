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


def get_events(myyear, min_reports):

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
         dtdelta = timedelta(days=d)
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

def load_year(myyear, day_array):
   #event_data = get_events(myyear, 30)
   #day_array = load_day_array(event_data, myyear, "reports_30", day_array)
   #event_data = get_events(myyear, 20)
   #day_array = load_day_array(event_data, myyear, "reports_20", day_array)
   event_data = get_events(myyear, 10)
   day_array = load_day_array(event_data, myyear, "reports_10", day_array)
   return(day_array, event_data)

try:
   cmd = sys.argv[1]
except:
   print("missing cmd")

if cmd == 'run':

   day_array = None

   myyear = 2019
   day_array, event_data = load_year(2019, day_array)
   day_array, event_data = load_year(2018, day_array)
   day_array, event_data = load_year(2017, day_array)
   day_array, event_data = load_year(2016, day_array)
   #day_array, event_data = load_year(2015, day_array)
   day_array, event_data = load_year(2013, day_array)
   day_array, event_data = load_year(2012, day_array)
   day_array, event_data = load_year(2011, day_array)
   day_array, event_data = load_year(2010, day_array)
   day_array, event_data = load_year(2009, day_array)

   for day in day_array:
      all_years_total = day_array[day]['all_years_total']['reports_10']
      utc_date = day_array[day]['utc_date']
      print(day, utc_date, all_years_total)
   day_json_file = "amsdata/" + str(myyear) + "-event-totals-by-day.json"
   save_json_file(day_json_file, day_array)

elif cmd == 'rpt':   
   plot_days = []
   plot_events = []
   plot_years = []
   plot_scores = []
   json_file = "amsdata/2019-event-totals-by-day.json"
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

      print(day, day_array[day]['utc_date'], day_array[day]['all_years_total']['reports_10'], len(day_array[day]['years']) , day_array[day]['all_years_total']['reports_10'] * len(day_array[day]['years']))
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

