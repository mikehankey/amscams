#!/usr/bin/python3 
import time
import os
import sys
from lib.PipeDetect import fireball
from lib.PipeUtil import load_json_file
json_conf = load_json_file("../conf/as6.json")
# script to fix data between 2022_05_28 and 2022_06_02
# loop over all meteors in this time and re-run fireball process

def get_mfiles(day):
   mfiles = []
   files = os.listdir("/mnt/ams2/meteors/" + day + "/")
   for ff in sorted(files):
      if "json" in ff:
         if "reduced" not in ff:
            rfile = "/mnt/ams2/meteors/" + day + "/" + ff.replace(".json", "-reduced.json")
            if os.path.exists(rfile) is False:
               mfiles.append("/mnt/ams2/meteors/" + day + "/" + ff.replace(".json", ".mp4") )
            else:
               print("DONE ALREADY!", rfile)
   return(mfiles)

if len(sys.argv) > 1:
    fix_days = sys.argv[1:]
else:
    fix_days = ['2022_12_12', '2022_12_13', '2022_12_14', '2022_12_15']

for day in fix_days:
   mfiles = get_mfiles(day)
   print(day, len(mfiles), "METEOR FILES STILL NEEDING REDUCTION")
   time.sleep(10)
   for mfile in mfiles:
      cmd = "./Process.py fireball " + mfile
      #print(cmd)
      os.system(cmd)
      fireball(mfile, json_conf)
   
