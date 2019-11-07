# coding: utf-8
import glob
import os
import json
import datetime

from lib.REDUCE_VARS import *
from lib.Get_Station_Id import get_station_id
from lib.FileIO import save_json_file, cfe, load_json_file
from lib.MeteorReduce_Tools import name_analyser
from lib.PAGINATION_VARS import *
 

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
            cur_day_data = {'day':cur_day,'det':[]}
          
            for detection in sorted(glob.iglob(day + os.sep +  '*' + '.json', recursive=True)):
               cur_day_data['det'].append(os.path.basename(detection))
            
            cur_month_data['days'].append(cur_day_data)
      
         index_year['months'].append(cur_month_data)

   return index_year 


# Write index for a given year
def write_index(year):
   json_data = create_json_index_year(year) 

   # Write Index if we have data
   if(len(json_data['months'])>0 ): 
      main_dir = METEOR_ARCHIVE + get_station_id() + '/' + METEOR + str(year)
      save_json_file(main_dir + os.sep + str(year) + ".json", json_data)
      return True
   
   return False


# Get index for a given year
def get_index(year):
   index_file = METEOR_ARCHIVE + get_station_id() + '/' + METEOR + str(year) + os.sep + str(year) + '.json'
   if(cfe(index_file)):
      return load_json_file(index_file)
   else:
      test = write_index(year)
      if(test):
         return load_json_file(index_file)
      else:
         return test

# Get results on index from a certain date
def get_results_from_date(date,json_index,max_res): 
   res = []
   res_cnt = 0

   for month in json_index['months']:
      #print(str(month['month'])  + " > " + str(date.month) + "<br/>")
      if(int(month['month'])>=date.month):
         for day in month['days']:
            if(int(day['day'])>=date.day and res_cnt<=max_res):
               for dec in day['det']:
                  if(res_cnt<max_res):
                     res.append(dec)
                     res_cnt+=1 
   
   return res


# Return full path of a detection based on its name
def get_full_path_detection(analysed_name):
   index_file = METEOR_ARCHIVE + analysed_name['station_id'] + os.sep + METEOR +  analysed_name['year'] + os.sep +  analysed_name['month'] + os.sep  +  analysed_name['day'] + os.sep 
   return index_file

# Get HTML version of each detection
def get_html_detections(res):
   res_html = ''
   for detection in res:
      det = name_analyser(detection)
      det['full_path'] = get_full_path_detection(det) + det['full_path']

      # Do we have a thumb stack preview for this detection?
      stacks_folder = does_cache_exist(det,"stacks")
      print(stacks_folder)
      print("<br>***********<br>")
      print(det)
      print("<br>***********<br>")

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

   # Meteor per page (default value)
   if(meteor_per_page is None):
      meteor_per_page = NUMBER_OF_METEOR_PER_PAGE

   # Day?
   if (limit_day is None):
      the_date = datetime.datetime.now()
   else:
      the_date = datetime.datetime.strptime(limit_day,"%Y_%m_%d") 

   year = the_date.year

   # Get the index of the selected or current year
   index =  get_index(year)
 
   # Search the index
   if(index is not False):
      res = get_results_from_date(the_date,index,int(meteor_per_page))

      # If we don't have enough detection to display we try the previous year
      if(len(res)<NUMBER_OF_METEOR_PER_PAGE):
         the_date = datetime.datetime.strptime(str(year-1)+'_01_01',"%Y_%m_%d") 
         year = year -1
         index = get_index(year)

         if(index is not False):
            new_stop = int(meteor_per_page) - len(res)
            res2 = get_results_from_date(the_date,index,new_stop)
            res = res + res2

   
   # Create HTML Version of each detection
   res_html = get_html_detections(res)
   print(res_html)