#!/usr/bin/python3

import os

fp = open("mfiles.txt")
for line in fp:
   line = line.replace("\n", "")
   el = line.split("/")
   clip_file = el[-1]
   clip_file = clip_file.replace("-motion.txt", ".mp4")
   clip_file = "/mnt/ams2/SD/proc2/2018_12_05/" + clip_file
   motion_file = "/mnt/ams2/SD/proc2/rejects/" + line
   new_motion_file = "/mnt/ams2/SD/proc2/2018_12_05/" + line
   cmd = "mv " + motion_file + " /mnt/ams2/SD/proc2/2018_12_05/"
   print(cmd)
   os.system(cmd)
 
   #cmd = "mv " + clip_file + " /mnt/ams2/SD/proc2/2018_12_05/"
   #print(cmd)
   #os.system(cmd)

   cmd = "/home/ams/CAMS/python/parse-motion.py " + new_motion_file
   print(cmd)
   os.system(cmd)
