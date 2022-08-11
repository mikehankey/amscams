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

days = sorted(all_days)[-60:]

checker = {}
for day in sorted(days,reverse=True):
   mdir = "/mnt/ams2/meteors/" + day + "/"
   files = os.listdir(mdir)
   for ff in files:
      if "json" not in ff:
         continue
      if "reduced" in ff:
         root_fn = ff.replace("-reduced.json", "")
         reduced = 1
         checker[root_fn] = 1
      else:
         root_fn = ff.replace(".json", "")
         if root_fn not in checker:
            checker[root_fn] = 0
   for check in checker:
      print(check, checker[check])
      if checker[check] == 0:
         cmd = "./Process.py fireball " + check + ".mp4"
         print(cmd)
         os.system(cmd)
   exit()
      

