# coding: utf-8
import glob
import os
import json

from lib.REDUCE_VARS import *
from lib.Get_Station_Id import get_station_id
from lib.FileIO import save_json_file
 

# Create index for a given year
def create_json_index_year(year):

   main_dir = METEOR_ARCHIVE + get_station_id() + '/' + METEOR + str(year)
   index_year = {'year':year,'months':[]}
 
   for month in sorted(glob.iglob(main_dir + '*' + os.sep + '*', recursive=True)):	

      cur_month = os.path.basename(os.path.normpath(month))

      # Test if it is an index
      if('json' not in cur_month):
         cur_month_data = {'month':cur_month,'days':[]}
         
         for day in sorted(glob.iglob(month + '*' + os.sep + '*', recursive=True)):	
            cur_day = os.path.basename(os.path.normpath(day))		
            cur_day_data = {'day':cur_day,'detections':[]}
          
            for detection in sorted(glob.iglob(day + os.sep +  '*' + '.json', recursive=True)):
               cur_day_data['detections'].append(os.path.basename(detection))
            
            cur_month_data['days'].append(cur_day_data)
      
         index_year['months'].append(cur_month_data)

   return index_year 


# Write index for a given year
def write_index(year):
   json_data = create_json_index_year(year)

   print(json.dumps(json_data))

   # Write Index
   if(json_data['months'] is not None):
      print("NONE?<br/>")
      print(json_data['months'])
      main_dir = METEOR_ARCHIVE + get_station_id() + '/' + METEOR + str(year)
      save_json_file(main_dir + os.sep + year + ".json", json_data)
 


# MAIN FUNCTION FOR THE ARCHIVE LISTING PAGE
def archive_listing(form):

   write_index('2018')
   #limit_day = form.getvalue('limit_day')
   #cur_page  = form.getvalue('p')
   #meteor_per_page = form.getvalue('meteor_per_page')



