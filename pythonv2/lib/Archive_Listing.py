# coding: utf-8
import glob
import os
import json
import datetime
import sys

from lib.REDUCE_VARS import *
from lib.Get_Station_Id import get_station_id
from lib.FileIO import save_json_file, cfe, load_json_file
from lib.MeteorReduce_Tools import name_analyser, get_cache_path, get_thumbs, does_cache_exist, generate_preview, get_stacks, get_datetime_from_analysedname
from lib.PAGINATION_VARS import *
from lib.Pagination import get_pagination

ARCHIVE_LISTING_TEMPLATE = "/home/ams/amscams/pythonv2/templates/archive_listing.html"
 
# Function that read a json file (detection)
# and return the values of the corresponding Diagnostic Fields 
def get_diag_fields(detection):
 
   if(cfe(detection)):
      detection_data = load_json_file(detection)

      # IS REDUCED
      red = 0
      try:
         if('frames' in detection_data):
            if len(detection_data['frames'])>0:
               red = 1
      except:
         red = 0

      # DURATION
      try:
         dur = detection_data['info']['dur']
      except:
         dur = "unkown"

      # MAX PEAK (MAGNITUDE)
      try:
         mag = detection_data['info']['max_peak']
      except:
         mag = "unkown"

      return mag,dur,red
   
   else:

      return "unkown","unkown",0



# Detect if a detection already exists in a monthly index
# Ex: search_month_index('2019_11_16_07_51_52_000_010037-trim0670.json')
# return Frue if the detection exists in the index 11.json under /2019
# or False if it doesn't exist and couldn't be inserted
def add_to_month_index(detection, insert=True):
   analysed_detection_name = name_analyser(detection)
   station_id = get_station_id()
         
   # We transform the detection to have the format stored in the index 
   # ie 07_51_52_000_010037-trim0670
   det = os.path.basename(detection)
   det = os.path.splitext(det)[0]
   det = det[11:]
   
   # Get month index path from analysed name
   index_path = METEOR_ARCHIVE +  station_id + os.sep + METEOR + str(analysed_detection_name['year']) + os.sep + str(analysed_detection_name['month']) + os.sep +  str(analysed_detection_name['month'])+".json"
   
   # If the index doesn't exist, we create it
   if(cfe(index_path) == 0):
      write_month_index(int(analysed_detection_name['month']),int(analysed_detection_name['year']))

   if(cfe(index_path)):
      index_data = load_json_file(index_path)
      try:
         the_day = index_data['days'][str(analysed_detection_name['day'])]
      except:
         the_day = []

      # We search for the detection if it already exists in the JSON index
      for detections in the_day:
         if(detections['p']==det):
            return True
  
      # If we are here, it means we didn't find it 
      # so if we want to insert it, we do it here
      if(insert==True):
         mag, dur, red  =  get_diag_fields(analysed_detection_name['full_path'])
         
         new_detect = {
            "dur": dur,
            "red": red,
            "p": det,
            "mag": mag
         }

         # If the days already exist
         try:
            index_data['days'][str(analysed_detection_name['day'])]
         except:
            index_data['days'][str(analysed_detection_name['day'])] = {}

         index_data['days'][str(analysed_detection_name['day'])].append(new_detect)

         #print("new index")
         #print(index_data)

         # Update the index
         main_dir = METEOR_ARCHIVE + station_id + os.sep + METEOR + str(analysed_detection_name['year']) + os.sep + str(analysed_detection_name['month'])
         save_json_file(main_dir + os.sep + str(analysed_detection_name['month']) + ".json", index_data)

         #print("INDEX UPDATED")
         #print(main_dir + os.sep + str(analysed_detection_name['month']) + ".json")

         return True

   return False




# Create Index for a given month
def create_json_index_month(month,year):
   station_id = get_station_id()
   main_dir = METEOR_ARCHIVE +  station_id + os.sep + METEOR + str(year) + os.sep + str(month)

   index_month = {'station_id':station_id,'year':int(year),'month':int(month),'days':{}}
   
   for day in sorted(glob.iglob(main_dir + '*' + os.sep + '*', recursive=True), reverse=True):	
      cur_day = os.path.basename(os.path.normpath(day))
 
      # Test if it is an index
      if('json' not in cur_day):
         cur_day_data = {}

         for detection in sorted(glob.iglob(day + os.sep +  '*' + '.json', recursive=True), reverse=True):
             
            mag, dur, red = get_diag_fields(detection)
            det = os.path.basename(detection)
            det = os.path.splitext(det)[0]

            # det[11:] => Here we also remove the Year, Month & Day of the detection 
            # since we know them from the JSON structure
            try:
               index_month['days'][int(cur_day)]
            except:
               index_month['days'][int(cur_day)] = []
 
            index_month['days'][int(cur_day)].append({'p':det[11:],'mag':mag,'dur':dur,'red':red})

   return index_month             

# Create index for a given year
def create_json_index_year(year):

   station_id = get_station_id()
   main_dir = METEOR_ARCHIVE +  station_id + os.sep + METEOR + str(year)
 
   index_year = {'station_id':station_id,'year':int(year),'months':{}}
 
   for month in sorted(glob.iglob(main_dir + '*' + os.sep + '*', recursive=True), reverse=True):	
      cur_month = os.path.basename(os.path.normpath(month))

      # Test if it is an index
      if('json' not in cur_month):
         cur_month_data = {}
         
         for day in sorted(glob.iglob(month + '*' + os.sep + '*', recursive=True), reverse=True):	
            cur_day = os.path.basename(os.path.normpath(day))		
            cur_day_data = []
          
            for detection in sorted(glob.iglob(day + os.sep +  '*' + '.json', recursive=True), reverse=True):
               
               mag, dur, red = get_diag_fields(detection)
               
               det = os.path.basename(detection)
               det = os.path.splitext(det)[0]
               # det[11:] => Here we also remove the Year, Month & Day of the detection 
               # since we know them from the JSON structure
               cur_day_data.append({'p':det[11:],'mag':mag,'dur':dur,'red':red})
            
 
            try:
               cur_month_data[int(cur_day)]
            except:
               cur_month_data[int(cur_day)] = []
               
            # Add the day
            cur_month_data[int(cur_day)] = cur_day_data
 
         try:
               index_year['months'][int(cur_month)]
         except:
               index_year['months'][int(cur_month)] = []

         index_year['months'][int(cur_month)].append(cur_month_data)

   return index_year 


# Write index for a given month
def write_month_index(month, year):
   json_data = create_json_index_month(month, year) 

   # Write Index if we have data
   if('days' in json_data):
      if(len(json_data['days'])>0 ): 
         main_dir = METEOR_ARCHIVE + get_station_id()  + os.sep + METEOR + str(year) + os.sep + str(month)
         save_json_file(main_dir + os.sep + str(month) + ".json", json_data)
         return True
   
   return False
 
# Write index for a given year
def write_year_index(year):
   json_data = create_json_index_year(year) 

   # Write Index if we have data
   if('months' in json_data):
      if(len(json_data['months'])>0 ): 
         main_dir = METEOR_ARCHIVE + get_station_id()  + os.sep + METEOR + str(year)
         save_json_file(main_dir + os.sep + str(year) + ".json", json_data)
         return True
   
   return False


# Get index for a given year
def get_index(year):
   index_file = METEOR_ARCHIVE + get_station_id()  + os.sep + METEOR + str(year) + os.sep + str(year) + '.json'
   if(cfe(index_file)):
      return load_json_file(index_file)
   else:
      test = write_year_index(year)
      if(test):
         return load_json_file(index_file)
      else:
         return test


# Get results on index from a certain date
def get_results_from_date_from_yearindex(date,json_index,max_res): 
   res = []
   res_cnt = 0 
    

   for month in json_index['days']:
      print("CUR MONTH " + month))
      print("<br>")
      #print(str(month['month'])  + " <= " + str(date.month) + "?<br/>")
      #if(int(month['month'])<=date.month):
      #   for day in month['days']:
      #      if(int(month['month'])==date.month and int(day['day'])<=date.day and res_cnt<=max_res):
      #         #print("CUR DAY " +str(day['day']))
      #         #print("<br>")
      #          for dec in day['det']:
      #            if(res_cnt<=max_res):
      #               res.append(dec)
      #               #print("ADDED<br/>")
      #               res_cnt+=1 
      #      elif(int(month['month'])!=date.month and res_cnt<=max_res):
      #         for dec in day['det']:
      #            if(res_cnt<=max_res):
      #               res.append(dec)
      #               #print("ADDED<br/>")
      #                res_cnt+=1 
   return res


# Return full path of a detection based on its name
def get_full_path_detection(analysed_name):
   index_file = METEOR_ARCHIVE + analysed_name['station_id'] + os.sep + METEOR +  analysed_name['year'] + os.sep +  analysed_name['month'] + os.sep  +  analysed_name['day'] + os.sep 
   return index_file

# Return HD (or SD video) based on a file that can be anything (.json or .mp4)
def get_video(_file):
   if(".json" in _file):
      video_file = _file.replace('.json','-SD.mp4')
      if(cfe(video_file)==1):
         return video_file
      else:
         video_file = _file.replace('.json','-HD.mp4')
         return video_file
   else:
      return _file

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
         res_html += '<div class="h2_holder d-flex justify-content-between"><h2>'+cur_date.strftime("%Y/%m/%d")+'</h2></div>'
         res_html += '<div class="gallery gal-resize row text-center text-lg-left mb-5 mr-5 ml-5">'

      if(cur_date.month != prev_date.month or cur_date.day != prev_date.day):
         prev_date = cur_date
         res_html +=  '</div><div class="h2_holder d-flex justify-content-between"><h2>'+cur_date.strftime("%Y/%m/%d")+'</h2></div>'
         res_html += '<div class="gallery gal-resize row text-center text-lg-left mb-5 mr-5 ml-5">'
 

      # Do we have a thumb stack preview for this detection?
      preview = does_cache_exist(det,"preview","/*.jpg")

      if(len(preview)==0 or clear_cache is True):
         # We need to generate the thumbs 
         preview = generate_preview(det) 

      # Get Video for preview
      path_to_vid = get_video(det['full_path'])       
      
      # Otherwise preview = preview (:)
      res_html += '<div class="preview col-lg-2 col-md-3 select-to reduced">'
      res_html += '  <a class="mtt" href="webUI.py?cmd=reduce2&video_file='+det['full_path']+'" title="Detection Reduce page">'
      res_html += '     <img alt="" class="img-fluid ns lz" src="'+preview[0]+'">'
      res_html += '  </a>'
      res_html += '  <div class="list-onl"><span>Cam #'+det['cam_id']+' - <b>'+det['hour']+':'+det['min']+'</b></span></div>'
      res_html += '  <div class="list-onl sel-box"><div class="custom-control big custom-checkbox">'
      res_html += '     <input type="checkbox" class="custom-control-input" id="'+det['full_path']+'" name="'+det['full_path']+'">'     
      res_html += '     <label class="custom-control-label" for="'+det['full_path']+'"></label>'
      res_html += '  </div></div>'
      res_html += '  <div class="d-flex justify-content-between">'
      res_html += '     <div class="pre-b gallery-only">Cam #'+det['cam_id']+' - <b>'+det['hour']+':'+det['min']+'</b></div>'
      res_html += '     <div class="btn-toolbar pr-0 pb-0"><div class="btn-group"><a class="vid_link_gal col btn btn-primary btn-sm" title="Play Video" href="./video_player.html?video='+path_to_vid+'"><i class="icon-play"></i></a>'
      res_html += '     <a class="delete_meteor_archive_gallery col btn btn-danger btn-sm" title="Delete Detection" data-meteor="'+det['full_path']+'"><i class="icon-delete"></i></a></div></div>'
      res_html += '  </div></div>' 

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

   # NUMBER_OF_METEOR_PER_PAGE
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
   
   template = template.replace("{DATE}",the_date.strftime("%Y/%m/%d") )

   year = the_date.year

   # Get the index of the selected or current year
   index =  get_index(year)
   
   # Search the index
   if(index is not False):

      print("I AM CURRENTLY WORKING ON THIS PAGE - PLEASE OLD ON")
      res = get_results_from_date_from_yearindex(the_date,index,int(nompp))

      
      print(res)
      sys.exit(0)

      # If we don't have enough detection to display we try the previous year
      if(res):
         if(len(res)<NUMBER_OF_METEOR_PER_PAGE):
            the_date = datetime.datetime.strptime(str(year-1)+'_01_01',"%Y_%m_%d") 
            year = year -1
            index = get_index(year)

            if(index is not False):
               new_stop = int(meteor_per_page) - len(res)
               res2 = get_results_from_date_from_yearindex(the_date,index,new_stop)
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
      else:
         template = template.replace("{RESULTS}", "<div class='alert alert-danger'>No detection found your the archive.</div>")
         template = template.replace("{PAGINATION_DET}", "")    
         template = template.replace("{PAGINATION}", "")

   else:
      template = template.replace("{RESULTS}", "<div class='alert alert-danger'>No detection found your the archive.</div>")
      template = template.replace("{PAGINATION_DET}", "")    
      template = template.replace("{PAGINATION}", "")

   # Display Template
   return template