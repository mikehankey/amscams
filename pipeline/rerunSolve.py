#!/usr/bin/python3

# script to re-run back events and remake the event cache files in the wasabi dir
import time
import os
from datetime import datetime
from calendar import monthrange
import datetime as dt
from lib.PipeUtil import load_json_file, save_json_file
today = (datetime.now() - dt.timedelta(days = 1)).strftime("%Y_%m_%d")
current_year, current_month, current_day = today.split("_")
years = ['2022', '2021']
start_year = min(years)

year_span = int(current_year) - int(start_year)
all_days = []
for year in years :
   #just do current year
   if year == current_year:
      end_mon = current_month
      end_day = current_day
   else:
      end_mon = 12
   for mon in range(1,int(end_mon) + 1):
      if mon == int(end_mon) and year == current_year:
         end_days = int(current_day)
      else:
         end_days = int(monthrange(int(year), mon)[1])
      for day in range(1,end_days + 1) :
         if mon < 10:
            smon = "0" + str(mon)
         else:
            smon = str(mon)
         if day < 10:
            sday = "0" + str(day)
         else:
            sday = str(day)
         all_days.append((year + "_" +  smon + "_" + sday))


if os.path.exists("solve-hist.json"):
   solve_hist = load_json_file("solve-hist.json")
else:
   solve_hist = {}

days = sorted(all_days)

for day in sorted(days,reverse=True)[0:8]:
   #cmd = "./updateEventDay.py " + day #+ ">ev_run_log.txt 2>&1 "
   y,m,d = day.split("_")
   cloud_evf = "/mnt/archive.allsky.tv/EVENTS/" + y + "/" + m + "/" + d + "/" + day + "_OBS_GOOD.html"
   #if day not in solve_hist and os.path.exists(cloud_evf) is False:
   if True: 
      if True:
         cmd =  "/usr/bin/python3 AllSkyNetwork.py best_obs_day " + day
         print(cmd)
         os.system(cmd)

         #cmd =  "/usr/bin/python3 AllSkyNetwork.py rerun_failed " + day
         #os.system(cmd)

         #cmd =  "python3 AllSkyNetwork.py refresh_day " + day
         #os.system(cmd)

         #cmd =  "python3 AllSkyNetwork.py resolve_event_day " + day
         #print(cmd)
         #os.system(cmd)


      if False:
         cmd =  "python3 AllSkyNetwork.py solve_day " + day
         print(cmd)
         os.system(cmd)

         cmd =  "python3 AllSkyNetwork.py day_load_solves " + day
         print(cmd)
         os.system(cmd)

      if False:
         cmd =  "python3 AllSkyNetwork.py load_solves_day " + day
         print(cmd)
         os.system(cmd)

         cmd =  "python3 AllSkyNetwork.py publish_day " + day
         print(cmd)
         os.system(cmd)


      #cmd =  "python3 RN.py RN " + day
      #print(cmd)
      #time.sleep(1)
      #os.system(cmd)
   else:
      print("Skip day:", day)

   solve_hist[day] = 1
   #save_json_file("solve-hist.json", solve_hist)
   #cmd =  "python3 AllSkyNetwork.py day_load_sql " + day
   ##print(cmd)
   #os.system(cmd)
   #cmd =  "python3 AllSkyNetwork.py resolve_failed_day " + day
   #print(cmd)
   #os.system(cmd)

