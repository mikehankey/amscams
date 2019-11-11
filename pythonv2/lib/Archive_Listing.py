# coding: utf-8
import glob
import os
import json
import datetime

from lib.REDUCE_VARS import *
from lib.Get_Station_Id import get_station_id
from lib.FileIO import save_json_file, cfe, load_json_file
from lib.MeteorReduce_Tools import name_analyser, get_cache_path, get_thumbs, does_cache_exist, generate_preview, get_stacks, get_datetime_from_analysedname
from lib.PAGINATION_VARS import *
from lib.Pagination import get_pagination

ARCHIVE_LISTING_TEMPLATE = "/home/ams/amscams/pythonv2/templates/archive_listing.html"

# Create index for a given year
def create_json_index_year(year):

   main_dir = METEOR_ARCHIVE + get_station_id() + '/' + METEOR + str(year)
   index_year = {'year':year,'months':[]}
 
   for month in sorted(glob.iglob(main_dir + '*' + os.sep + '*', recursive=True), reverse=True):	
      cur_month = os.path.basename(os.path.normpath(month))

      # Test if it is an index
      if('json' not in cur_month):
         cur_month_data = {'month':cur_month,'days':[]}
         
         for day in sorted(glob.iglob(month + '*' + os.sep + '*', recursive=True), reverse=True):	
            cur_day = os.path.basename(os.path.normpath(day))		
            cur_day_data = {'day':cur_day,'det':[]}
          
            for detection in sorted(glob.iglob(day + os.sep +  '*' + '.json', recursive=True), reverse=True):
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
      #print("CUR MONTH " +str(month['month']))
      #print("<br>")
      #print(str(month['month'])  + " <= " + str(date.month) + "?<br/>")
      if(int(month['month'])<=date.month):
         for day in month['days']:
            if(int(month['month'])==date.month and int(day['day'])<=date.day and res_cnt<=max_res):
               #print("CUR DAY " +str(day['day']))
               #print("<br>")
               for dec in day['det']:
                  if(res_cnt<=max_res):
                     res.append(dec)
                     #print("ADDED<br/>")
                     res_cnt+=1 
            elif(int(month['month'])!=date.month and res_cnt<=max_res):
               for dec in day['det']:
                  if(res_cnt<=max_res):
                     res.append(dec)
                     #print("ADDED<br/>")
                     res_cnt+=1 
   return res


# Return full path of a detection based on its name
def get_full_path_detection(analysed_name):
   index_file = METEOR_ARCHIVE + analysed_name['station_id'] + os.sep + METEOR +  analysed_name['year'] + os.sep +  analysed_name['month'] + os.sep  +  analysed_name['day'] + os.sep 
   return index_file


# Get HTML version of each detection
def get_html_detections(res,clear_cache):

   res_html = ''
   prev_date = None
   
   for detection in res:
      det = name_analyser(detection)
      det['full_path'] = get_full_path_detection(det) + det['full_path']
      
      cur_date = get_datetime_from_analysedname(det)
 
      if(prev_date is None):
         prev_date = cur_date
         res_html += '<div class="h2_holder  d-flex justify-content-between"><h2>'+cur_date.strftime("%Y-%m-%d")+'</h2></div>'

      if(cur_date.month != prev_date.month or cur_date.day != prev_date.day):
         prev_date = cur_date


      # Do we have a thumb stack preview for this detection?
      preview = does_cache_exist(det,"preview","/*.jpg")

      if(len(preview)==0 or clear_cache is True):
         # We need to generate the thumbs 
         preview = generate_preview(det) 
       
      # Otherwise preview = preview (:)
      res_html += '<div class="preview col-lg-2 col-md-3 select-to reduced">'
      res_html += '<a class="mtt" href="webUI.py?cmd=reduce2&video_file='+det['full_path']+'" title="Detection Reduce page">'
      res_html += '<img alt="" class="img-fluid ns lz" src="'+preview[0]+'">'
      res_html += '<span>'+det['cam_id']+'</span>'
      res_html += '</a>'
      res_html += '</div>'

   return res_html
 

 

# MAIN FUNCTION FOR THE ARCHIVE LISTING PAGE
def archive_listing(form):

   limit_day = form.getvalue('limit_day')
   cur_page  = form.getvalue('p')
   meteor_per_page = form.getvalue('meteor_per_page')
   clear_cache = form.getvalue('clear_cache')

   # Build the page based on template  
   with open(ARCHIVE_LISTING_TEMPLATE, 'r') as file:
      template = file.read()

   # Pagination
   if (cur_page is None) or (cur_page==0):
      cur_page = 1
   else:
      cur_page = int(cur_page)

   #NUMBER_OF_METEOR_PER_PAGE
   if(meteor_per_page is None):
      nompp = NUMBER_OF_METEOR_PER_PAGE
   else:
      nompp = int(meteor_per_page)

   
   # Build num per page selector
   ppp_select = ''
   for ppp in POSSIBLE_PER_PAGE:
      if(int(ppp)==nompp):
         ppp_select+= '<option selected value="'+str(ppp)+'">'+str(ppp)+' / page</option>'
      else:
         ppp_select+= '<option value="'+str(ppp)+'">'+str(ppp)+' / page</option>'  
   template = template.replace("{RPP}", ppp_select)


   # Clear_cache
   if(clear_cache is None):
      clear_cache = False
   else:
      clear_cache = True

   # Day?
   has_limit_day = False
   if (limit_day is None):
      the_date = datetime.datetime.now()
   else:
      the_date = datetime.datetime.strptime(limit_day,"%Y_%m_%d") 
      has_limit_day = True

   year = the_date.year

   # Get the index of the selected or current year
   index =  get_index(year)
 
   # Search the index
   if(index is not False):
      res = get_results_from_date(the_date,index,int(nompp))

      # If we don't have enough detection to display we try the previous year
      if(len(res)<NUMBER_OF_METEOR_PER_PAGE):
         the_date = datetime.datetime.strptime(str(year-1)+'_01_01',"%Y_%m_%d") 
         year = year -1
         index = get_index(year)

         if(index is not False):
            new_stop = int(meteor_per_page) - len(res)
            res2 = get_results_from_date(the_date,index,new_stop)
            res = res + res2

   if(has_limit_day==0):
      pagination = get_pagination(cur_page,len(res),"/pycgi/webUI.py?cmd=archive_listing&meteor_per_page="+str(nompp),int(nompp))
   else:
      pagination = get_pagination(cur_page,len(res),"/pycgi/webUI.py?cmd=archive_listing&limit_day="+str(the_date)+"&meteor_per_page="+str(nompp),int(nompp))

   if(pagination[2] != ''):
      template = template.replace("{PAGINATION_DET}", "Page  " + format(cur_page) + "/" +  format(pagination[2]))    
   else:
      template = template.replace("{PAGINATION_DET}", "")    
   
   # Create HTML Version of each detection
   res_html = get_html_detections(res,clear_cache) 
   template = template.replace("{RESULTS}", res_html)

   # Pagination
   if(len(res)>=1): 
      template = template.replace("{PAGINATION}", pagination[0])
   else:
      template = template.replace("{PAGINATION}", "")


   # Display Template
   return template