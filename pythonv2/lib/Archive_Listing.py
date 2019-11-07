# coding: utf-8
import glob
import os

from lib.REDUCE_VARS import *
from lib.FileIO import save_json_file

path = "/mnt/ams2/meteor_archive/AMS7/METEOR/2019/"
index_year = {'year':2019,'months':[]}

# Create index for a given year
def create_json_index_year(year):
   main_dir = METEOR_ARCHIVE + get_station_id() + '/' + METEOR + str(year)
   index_year = {'year':year,'months':[]}

   for month in sorted(glob.iglob(main_dir + '*' + os.sep, recursive=False)):	
      cur_month = os.path.basename(os.path.normpath(month))
     
      cur_month_data = {'month':cur_month,'days':[]}
      
      for day in sorted(glob.iglob(month + '*' + os.sep, recursive=False)):	
         cur_day = os.path.basename(os.path.normpath(day))		
         cur_day_data = {'day':cur_day,'detections':[]}
         
         for detection in sorted(glob.iglob(day +  '*' + '.json', recursive=False)):
            
            cur_day_data['detections'].append(os.path.basename(detection))
         cur_month_data['days'].append(cur_day_data)
      index_year['months'].append(cur_month_data)

   return json.dumps(index_year)


# Write index for a given year
def write_index(year):
   json_data = create_json_index_year(year)

   # Index PATH
   if(json_data is not None):
      main_dir = METEOR_ARCHIVE + get_station_id() + '/' + METEOR + str(year)
      save_json_file(json_data, main_dir + os.sep + year + ".json")


write_index('2019')
