#!/usr/bin/python3
import os
import sys

date = sys.argv[1]
el = date.split("_")
if len(el) == 2:
   year = el[0]
   month = el[1]
   cmd = "find /mnt/archive.allsky.tv/EVENTS/" + year + "/" + month + "/ > ./temp.txt" 
   print(cmd)
   os.system(cmd)
   
elif len(el) == 3:
   year = el[0]
   month = el[1]
   day = el[2]

   cmd = "find /mnt/archive.allsky.tv/EVENTS/" + year + "/" + month + "/" + day + "/ > ./temp.txt" 
   print(cmd)
   os.system(cmd)
#os.system(cmd)

fp = open("temp.txt", "r")
ev_data = {}
for line in fp:
   line = line.replace("\n", "")
   el = line.split("/")
   if len(el) == 9:
      ev_id = el[7]
      ev_file = el[8]
      if ev_id not in ev_data:
         ev_data[ev_id] = {}
         ev_data[ev_id]['files'] = []
         ev_data[ev_id]['files'].append(ev_file)
      else:
         ev_data[ev_id]['files'].append(ev_file)

for ev_id in ev_data:
   # 1 does this event have a pickle file? 
   # 2 does the event have some jpgs?
   # if yes to 1 and no to 2 then run the plotter
   pick = 0
   jpgs = 0
   for ff in ev_data[ev_id]['files']:
      if "pickle" in ff:
         pick = 1
      if "jpg" in ff:
         jpgs += 1
   print(pick, jpgs, ev_id, len(ev_data[ev_id]['files']))
   if pick >= 1 and jpgs < 4:
      print("SOLVED EVENT IS MISSING PLOTS RUN IT!", ev_id)
      cmd = "./plotTraj.py " + ev_id
      print(cmd)
      os.system(cmd)
