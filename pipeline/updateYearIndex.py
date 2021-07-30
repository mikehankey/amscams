import datetime, calendar
from datetime import datetime as dt
import sys
import os

def get_days(year,month):
   num_days = calendar.monthrange(year, month)[1]
   days = [datetime.date(year, month, day) for day in range(1, num_days+1)]
   return(days)


year = sys.argv[1]

cur_year = dt.now().strftime("%Y")
cur_mon = dt.now().strftime("%m")
cur_day = dt.now().strftime("%d")


all_days = []

for mon in range(1,13):
   if int(year) != int(cur_year):
      print("NOT IMPLEMENTED YET!", year, mon)
   else:
      if int(mon) <= int(cur_mon):
         dayz = get_days(int(year),int(mon))
         for day in dayz:
            m,y,d = str(day).split("-")
            if int(cur_mon) == int(mon):
               if int(d) <= int(cur_day):
                  all_days.append(day)
            else:
               all_days.append(day)
      #else:
      #   print("FUTURE!", int(mon), int(cur_mon))

for day in sorted(all_days, reverse=True):
   print(day)
   day_str = day.strftime("%Y_%m_%d")
   cmd = "python3 updateEventDay.py " + day_str
   print(cmd)
   os.system(cmd)
