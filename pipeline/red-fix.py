#!/usr/bin/python3 

import os

# script to fix data between 2022_05_28 and 2022_06_02
# loop over all meteors in this time and re-run fireball process

def get_mfiles(day):
   mfiles = []
   files = os.listdir("/mnt/ams2/meteors/" + day + "/")
   for ff in files:
      if "json" in ff:
         if "reduced" not in ff:
            mfiles.append("/mnt/ams2/meteors/" + day + "/" + ff.replace(".json", ".mp4") )
   return(mfiles)

fix_days = ['2022_06_02', '2022_06_01', '2022_05_31', '2022_05_30', '2022_05_29', '2022_05_28']

for day in fix_days:
   mfiles = get_mfiles(day)
   for mfile in mfiles:
      cmd = "./Process.py fireball " + mfile
      print(cmd)
      os.system(cmd)
   
