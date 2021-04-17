#!/usr/bin/python3 

import glob
import os

files = sorted(glob.glob("/mnt/ams2/HD/2021_04_*.mp4"), reverse=True)
c = 0
for file in files[20:]:
   if "trim" in file:
      continue
   cmd = "/usr/bin/ffprobe " + file + " 2>&1 |grep fps"
   print(cmd)
   os.system(cmd)
   if c > 100:
      exit()
   c += 1

