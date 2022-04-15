#!/usr/bin/python3

# script to re-run back events and remake the event cache files in the wasabi dir
import os
from datetime import datetime
from calendar import monthrange
import datetime as dt
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

for day in sorted(all_days,reverse=True)[27:100]:
   cmd =  "python3 AllSkyNetwork.py do_all " + day
   print(cmd)
   os.system(cmd)
   cmd =  "python3 RN.py RN " + day
   print(cmd)
   os.system(cmd)

