#!/usr/bin/python3
import os
from lib.PipeUtil import load_json_file, save_json_file

mets = load_json_file("/mnt/ams2/EVENTS/ALL_OBS.json")
c = 0
mets = sorted(mets, key=lambda x: x[6], reverse=True)
top_2000 = []
by_station = {}
for met in mets:
   station_id, root_file, ei,t,rv,ss,pi,du,rs,st = met
   if station_id not in by_station:
      by_station[station_id] = []
   by_station[station_id].append(met)
   print(station_id,root_file,pi)
   top_2000.append(met)
   if c % 1000:
      print(c)
   if c == 5000:
      save_json_file("/mnt/ams2/EVENTS/top_2000.json", top_2000)
      cp = "cp /mnt/ams2/EVENTS/top_2000.json /mnt/archive.allsky.tv/EVENTS/"
      os.system(cp)
   c += 1

save_dir = "/mnt/ams2/EVENTS/OBS/STATIONS/"
for st in by_station:
   data = by_station[st]
   data = sorted(data, key=lambda x: x[6], reverse=True)
   save_json_file(save_dir + "AMS" + str(st) + ".json", data, True)
   cmd = "cp " + save_dir + "AMS" + str(st) + ".json " + "/mnt/archive.allsky.tv/EVENTS/OBS/STATIONS/"
   print(cmd)
   os.system(cmd)
   print(save_dir + "AMS" + str(st) + ".json")
