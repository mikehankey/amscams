import sys

from lib.Archive_Listing import *


# Allows to update an index of detections in the archive
# for a given year 
# or a given year & month

# usage
# Create_Archive_Index YEAR
# Create_Archive_Index YEAR MONTH

year = sys.argv[1]
 

try:
   sys.argv[2]
   month = sys.argv[2]
except:
   month = False


if(month):
   write_month_index(int(month),int(year))
   print("INDEX FOR " + str(month) + "/" + str(year) +  " updated")
else:
   write_year_index(int(year))
   print("INDEX FOR " + str(year) +  " updated")

 








