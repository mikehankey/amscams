import sys

from lib.Archive_Listing import *
from lib.FileIO import *



# TEMP TEST
d = load_json_file_NOT_WORKING('~/amscams/conf/as6.json')

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
   # ONE MONTH ONLY
   write_month_index(int(month),int(year))
   print("INDEX FOR " + str(month) + "/" + str(year) +  " updated")
else:
   # FULL YEAR
   for x in range(1, 13): 
      write_month_index(int(x),int(year))
   write_year_index(int(year))
   print("INDEX FOR " + str(year) +  " updated")

 








