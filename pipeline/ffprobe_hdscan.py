#!/usr/bin/python3 

import glob
import os
from lib.FFFuncs import ffprobe
import sys

try:
   date = sys.argv[1]
   cam_id = sys.argv[2]
   time_of_day = sys.argv[3]
   ftype = sys.argv[4]
except:
   print("Usage: ./ffprobe_hdscan.py YYYY_MM_DD CAM_ID HOUR TYPE (HD or SD)")
   print("./ffprobe_hdscan.py 2023_07_20 010001 night HD")
   exit()

if time_of_day == "night":
   tod = ""
else:
   tod = "daytime"
if ftype == "SD" or ftype == "sd":

   wild = "/mnt/ams2/SD/proc2/{}/{}/*{}*.mp4".format(tod, date, cam_id)
else:
   wild = "/mnt/ams2/HD/{}*{}*.mp4".format(date, cam_id)

print(wild)
files = sorted(glob.glob(wild), reverse=True)
c = 0
data = {}
# show 20 files
for file in sorted(files[:20]):

   if "trim" in file:
      continue
   fn = file.split("/")[-1]
   hour = fn[0:13]
   if hour not in data:
      data[hour] = {}
      data[hour]['good'] = []
      data[hour]['bad'] = []

   resp = ffprobe(file)
   fps = resp[3] / 60
   if fps >= 20:
      data[hour]['good'].append(fn)
      print("GOOD", fps, fn, resp)
   else:   
      data[hour]['bad'].append(fn)
      print("BAD", fps, fn, resp)

for hour in data:
   total = len(data[hour]['good']) + len(data[hour]['bad'])
   print(hour, len(data[hour]['good']), len(data[hour]['bad']), total)

