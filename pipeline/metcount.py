#!/usr/bin/python3

import sys
import redis
import os
from lib.PipeUtil import cfe, load_json_file, save_json_file
import json
r = redis.Redis("allsky-redis.d2eqrc.0001.use1.cache.amazonaws.com", port=6379, decode_responses=True)

def obs_count(date):
   special = ['AMS41', 'AMS42', 'AMS48']
   final_hour = {}
   final_min = {}
   final_bin = {}
   keys = r.keys("OI:*:" + date + "*")
   met_counts = {}
   met_counts_min = {}
   met_counts_bin = {}
   for key in keys:
      el = key.split(":")
      station = el[1]
      vid = el[2]
      dth = vid[0:13]
      dtm = vid[0:16]
      dtb = vid[0:15]
      if dth not in final_hour:
         final_hour[dth] = {}
      if dtm not in final_min:
         final_min[dtm] = {}
      if dtb not in final_bin:
         final_bin[dtb] = {}

      if station not in met_counts:
         met_counts[station] = {}
      if station not in met_counts_min:
         met_counts_min[station] = {}
      if station not in met_counts_bin:
         met_counts_bin[station] = {}
      if dth not in met_counts[station]:
         met_counts[station][dth] = 0
      if dtm not in met_counts_min[station]:
         met_counts_min[station][dtm] = 0
      if dtb not in met_counts_bin[station]:
         met_counts_bin[station][dtb] = 0

      met_counts[station][dth] += 1
      met_counts_min[station][dtm] += 1
      met_counts_bin[station][dtb] += 1
   for station in sorted(met_counts.keys()):
      for dtm in sorted(met_counts[station].keys()):
         if station not in final_hour[dtm]:
            final_hour[dtm][station] = met_counts[station][dtm]

   for station in sorted(met_counts_min.keys()):
      for dtm in sorted(met_counts_min[station].keys()):
         if dtm not in met_counts_min[station]:
            met_counts_min[station][dtm] = 0
         if station not in final_min[dtm]:
            final_min[dtm][station] = met_counts_min[station][dtm]

   for station in sorted(met_counts_bin.keys()):
      for dtm in sorted(met_counts_bin[station].keys()):
         if station not in final_bin[dtm]:
            final_bin[dtm][station] = met_counts_bin[station][dtm]
   #print(final_hour)
   print("type,time,AMS41,AMS42,AMS48")
   for hour in sorted(final_hour.keys()):
      row = hour 
      for st in sorted(special):
         #print(st) #,  final_hour[hour].keys())
         if st in final_hour[hour].keys():
            row += "," + str(final_hour[hour][st]) 
      
      print("HOUR," + row) #, final_hour[hour])
   for min in sorted(final_min.keys()):
      row = min 
      row_total = 0 
      for st in sorted(special):
         #print(st) #,  final_hour[hour].keys())
         if st in final_min[min].keys():
            row += "," + str(final_min[min][st]) 
            row_total += final_min[min][st]
      row += "," + str(row_total) 
      print("MIN," + row) #, final_hour[hour])

   for bin in sorted(final_bin.keys()):
      row = bin 
      row_total = 0
      for st in sorted(special):
         #print(st) #,  final_hour[hour].keys())
         if st in final_bin[bin].keys():
            row += "," + str(final_bin[bin][st]) 
            row_total += final_bin[bin][st]
      row += "," + str(row_total) 
      print("BIN," + row) #, final_hour[hour])

def ev_count(date):
   sdate = date.replace("_", "")
   keys = r.keys("E:" + sdate + "*")
   hour_stats = {}
   hour_min_stats = {}
   hour_bin_stats = {}
   all_events = []
   for key in keys:
      rval = json.loads(r.get(key))
      all_events.append(rval)
      el = key.replace("E:", "").split("_")
      rdate,rtime = el
      h = rtime[0:2]
      m = rtime[2:4]
      s = rtime[4:6]
      hkey = h
      hmkey = h + m
      hbkey = h + m[0]
      if hkey not in hour_stats:
         hour_stats[hkey] = 0
      if hmkey not in hour_min_stats:
         hour_min_stats[hmkey] = 0
      if hbkey not in hour_bin_stats:
         hour_bin_stats[hbkey] = 0
      hour_stats[hkey] += 1
      hour_min_stats[hmkey] += 1
      hour_bin_stats[hbkey] += 1
   for key in sorted(hour_stats):
      print(key, hour_stats[key])
   for key in sorted(hour_min_stats):
      print(key, hour_min_stats[key])
   for key in sorted(hour_bin_stats):
      print(key, hour_bin_stats[key])
   all_events = sorted(all_events, key=lambda x: (x['event_id']), reverse=False)
   #for rval in all_events:
   #   print(rval['event_id'], "\n\t", rval['stations'], "\n\t", rval['files'], "\n\t", rval['start_datetime'])
obs_count(sys.argv[1])

#ev_count(sys.argv[1])
