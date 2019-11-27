import sys

from lib.Archive_Listing import *


# Allows to update an index of detections in the archive
# for a given year 
# or a given year & month

# usage
# Create_Archive_Index YEAR
# Create_Archive_Index YEAR MONTH

year = sys.argv[1]
if(sys.argv[2]):
   month = sys.argv[2]

if(month):
   write_month_index(int(month),int(year))
   print("INDEX FOR " + int(month) + "/" + int(year) +  " updated")
else:
   write_year_index(int(year))

 








