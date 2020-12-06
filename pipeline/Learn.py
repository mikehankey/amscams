#!/usr/bin/python3
import glob
import os
import sys
from lib.PipeUtil import cfe, load_json_file

# clip all meteor videos and drop into learning dir
L_DIR = "/mnt/ams2/LEARN/METEORS/"
mdirs = glob.glob("/mnt/ams2/meteors/*")
for md in mdirs:
   if cfe(md, 1) == 1:
      jss = glob.glob(md + "/*.json")
      for js in jss:
         if "reduced" in js or "star" in js or "manual" in js or "import" in js or "archive" in js or "events" in js:
            print("SKIP REDUCED")
            continue
         mj = load_json_file(js)
         if mj == 0:
            continue
         vid = js.replace(".json", ".mp4")
         print("MJ:", js )
         start = 0
         end = 0
         try:
            if "sd_objects" in mj:
               if len(mj['sd_objects']) > 0:
                  if 'history' in mj['sd_objects'][0]:
                     if len(mj['sd_objects'][0]['history']) == 0:
                        continue 
                     print(vid, mj['sd_objects'][0]['history'][0], mj['sd_objects'][0]['history'][-1])
                  elif "ofns" in mj['sd_objects'][0]:
                     print(vid, mj['sd_objects'][0]['ofns'][0], mj['sd_objects'][0]['ofns'][-1])
            else:
               if "ofns" in mj:
                  print("MJ2:", vid, mj['ofns'][0], mj['ofns'][-1])
               else:
                  print("MJ3:", vid, mj)
         except:
            print("Failed to find objects!:", vid, mj)
            #for key in mj['sd_objects']:
            #   if 'ofns' in mj['sd_objects'][key]:
            #      print("MJ4:", vid, mj['sd_objects'][key]['ofns'][0], mj['sd_objects'][key]['ofns'][-1])
            exit()

