import sys
import calendar

from lib.Minutes_Tools import *
 

# Allows to update an index of detections in the archive
# for a given year 
# or a given year & month

# usage
# Create_Minute_Index YEAR MONTH
# Create_Minute_Index YEAR MONTH DAY

year = sys.argv[1]
month = sys.argv[2]
 
try: 
   day = sys.argv[3]
except:
   day = False


if(day):
   # ONE DAY ONLY
   write_day_minute_index(int(day),int(month),int(year))
   print(str(day) + "/" + str(month) + "/" + str(year)+ " minute index updated")
else:
   # FULL MONTH
   how_many_days = calendar.monthrange(int(year),int(month))[1]
   for x in range(1, how_many_days): 
      write_day_minute_index(int(x),int(month),int(year)) 
      print(str(day) + "/" + str(month) + "/" + str(year)+ " minute index updated")

 








