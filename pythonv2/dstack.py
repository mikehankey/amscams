#!/usr/bin/python3
from lib.FileIO import cfe
import glob
import os
files = glob.glob("/mnt/ams2/SD/proc2/daytime/2020_02_16_14_2*.mp4")
out = ""
for file in files:
   img = file.replace(".mp4", "-stacked.png")
   if cfe(img) == 0:
      cmd= "./stackVideo.py sv " + file
      print(cmd)
   
      os.system(cmd)
   else:
      print("did it already.")

   out += "<a href=" + file + "><img src=" + img + "><BR>"

fp = open("/mnt/ams2/temp.html", "a")
fp.write(out)
 
