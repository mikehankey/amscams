# coding: utf-8
import glob
import os
import json
import datetime

from lib.REDUCE_VARS import *
from lib.Get_Station_Id import get_station_id
from lib.FileIO import save_json_file, cfe, load_json_file
 

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

   # Write Index if we have data
   if(len(json_data['months'])>0 ): 
      main_dir = METEOR_ARCHIVE + get_station_id() + '/' + METEOR + str(year)
      save_json_file(main_dir + os.sep + year + ".json", json_data)


# Get index for a given year
def get_index(year):
   index_file = METEOR_ARCHIVE + get_station_id() + '/' + METEOR + str(year) + os.sep + str(year) + '.json'
   if(cfe(index_file)):
      return load_json_file(index_file)
   else:
      return None

# Get results on index from a certain date
def get_results_from_date(date,json_index): 
   res = []

   for month in json_index['months']:
      print(str(month['month'])  + " vs. " + str(date.month) + "<br/>")
      if(int(month['month'])<=date.month):
         for day in month['days']:
            if(int(day['day'])<=date.day):
               res.append(day['day']['detections'])

   
   print(res)


# MAIN FUNCTION FOR THE ARCHIVE LISTING PAGE
def archive_listing(form):
   limit_day = form.getvalue('limit_day')
   cur_page  = form.getvalue('p')
   meteor_per_page = form.getvalue('meteor_per_page')

   # Pagination
   if (cur_page is None) or (cur_page==0):
      cur_page = 1
   else:
      cur_page = int(cur_page)

   # Day?
   if (limit_day is None):
      the_date = datetime.datetime.now()
   else:
      the_date = datetime.datetime.strptime(limit_day,"%Y_%m_%d") 

   year = the_date.year

   # Get the index
   index =  get_index(year)

   # Search the index
   if(index is not None):
      res = get_results_from_date(the_date,index)
