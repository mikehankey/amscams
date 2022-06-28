#!/usr/bin/python3 

import glob
import os
from lib.FFFuncs import ffprobe

files = sorted(glob.glob("/mnt/ams2/SD/proc2/2022_06_28/*.mp4"), reverse=True)
c = 0
for file in files[20:]:
   if "trim" in file:
      continue

   resp = ffprobe(file)
   print(resp, file)
