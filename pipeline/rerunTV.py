#!/usr/bin/python3

# script to re-run back events and remake the event cache files in the wasabi dir
import os
from datetime import datetime
from calendar import monthrange
import datetime as dt
start_year = '2022'
today = (datetime.now() - dt.timedelta(days = 1)).strftime("%Y_%m_%d")
current_year, current_month, current_day = today.split("_")

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

for day in sorted(all_days,reverse=True)[0:20]:
#   solve_cmd = "./solveWMPL.py sd " + day
   #os.system(solve_cmd)
   ev_run_cmd = "python3 EVRun.py " + day + " EOD" 
   #os.system(ev_run_cmd)
   print(day)
for day in sorted(all_days,reverse=True)[0:10]:
#   solve_cmd = "./solveWMPL.py sd " + day
   #os.system(solve_cmd)
   #update_day = "python3 updateEventDay.py " + day 
   #update_day = "python3 EVRun.py " + day  + " EOD"
   dd_cmd = "./DynaDB.py udc " + day
   print(dd_cmd)
   os.system(dd_cmd)

   #udc_cmd = "./DynaDB.py udc " + day + " events"
   #os.system(udc_cmd)
   #print(day)
