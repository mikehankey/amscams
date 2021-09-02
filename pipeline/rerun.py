#!/usr/bin/python3
from lib.PipeUtil import cfe, get_file_info, save_json_file, load_json_file
# script to re-run back events and remake the event cache files in the wasabi dir
import os
from datetime import datetime
from calendar import monthrange
import datetime as dt
start_year = '2021'
today = (datetime.now() - dt.timedelta(days = 1)).strftime("%Y_%m_%d")
current_year, current_month, current_day = today.split("_")

if cfe("rerun.run") == 1:
   print("Rerun is already running.")
else:
   os.system("touch rerun.run")
if cfe("rerun.log") == 1:
   size, tdiff = get_file_info("rerun.log")
else:
   rerun_log = {}
   tdiff = 9999
   save_json_file("rerun.log", rerun_log)

if tdiff > 1400:
   print("TDIFF:", tdiff)
   print("RUN rerun.py to sync last 30 days.")
else:
   print("Rerun has run within the last 12 hours so no need to do it again!")
   os.system("rm rerun.run")
   exit()


years = int(current_year) - int(start_year)
all_days = []
if years == 0:
   #just do current year
   for mon in range(1,int(current_month) + 1):
      if mon == int(current_month):
         end_days = int(current_day)
      else:
         end_days = int(monthrange(int(current_year), mon)[1])
      for day in range(1,end_days + 2) :
         if mon < 10:
            smon = "0" + str(mon)
         else:
            smon = str(mon)
         if day < 10:
            sday = "0" + str(day)
         else:
            sday = str(day)
         all_days.append((current_year + "_" +  smon + "_" + sday))

for day in sorted(all_days,reverse=True)[0:30]:
   print(day)

   cmd = "python3 DynaDB.py ddd " + day
   print(cmd)
   os.system(cmd)



   #cmd = "python3 Filter.py fd " + day
   #print(cmd)
   #os.system(cmd)
   #cmd = "python3 Meteor.py 10 " + day
   #print(cmd)
   #os.system(cmd)

os.system("rm rerun.run")
