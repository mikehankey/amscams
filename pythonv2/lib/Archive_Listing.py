# coding: utf-8
import glob 
import sys, os 
import json 
import collections 
import shutil
import requests

from datetime import datetime, timedelta
from calendar import monthrange

from lib.REDUCE_VARS import *
from lib.Get_Station_Id import get_station_id
from lib.FileIO import save_json_file, cfe, load_json_file
from lib.MeteorReduce_Tools import name_analyser, get_cache_path, get_thumbs, does_cache_exist, generate_preview, get_stacks, get_datetime_from_analysedname
from lib.PAGINATION_VARS import *
from lib.Pagination import get_pagination

ARCHIVE_LISTING_TEMPLATE = "/home/ams/amscams/pythonv2/templates/archive_listing.html"

# QUERIES CRITERIA
POSSIBLE_MAGNITUDES = [130,140,150,160,170,180,190,200,210,220,230,240,250,260,270,280,290,300]
POSSIBLE_ERRORS = [0.5,0.6,0.8,0.9,1,1.1,1.2,1.3,1.4,1.5,1.6,1.7,1.8,1.9,2,2.5,3,3.5,4,5]
POSSIBLE_ANG_VELOCITIES = [1,2,3,4,5,6,7,8,9,10,11,12,13,15,16,17,18,19,20,21,22,23,24,25]
POSSIBLE_SYNC = [0,1]
POSSIBLE_POINT_SCORE = [3,5,10]
 
# Delete Multiple Detections at once
def delete_multiple_archived_detection(detections):
   
   # In case we only have one... it's a string
   if(isinstance(detections, str)):
      detections = [detections]

   for det in detections:

      analysed_name = name_analyser(det)

      # Remove the Cache files 
      cache_path = get_cache_path(analysed_name)
      if os.path.isdir(cache_path):
         shutil.rmtree(cache_path)
     
      # Remove Json
      if os.path.isfile(det):
         os.remove(det)

      # Remove HD     
      det = det.replace('.json','-HD.mp4')
      if os.path.isfile(det):
         os.remove(det)

      # Remove SD
      det = det.replace('-HD','-SD')
      if os.path.isfile(det):
         os.remove(det)

      # Update Index (?)
      write_month_index(int(analysed_name['month']),int(analysed_name['year']))
      write_year_index(int(analysed_name['year']))


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
         dur = "unknown"

      # MAX PEAK (MAGNITUDE)
      try:
         mag = detection_data['info']['max_peak']
      except:
         mag = "unknown"


      # RESIDUAL ERROR OF CALIBRATION
      try:
         res_error = detection_data['calib']['device']['total_res_px']
      except:
         res_error = "unknown"

      # ANGULAR VELOCITY
      try:
         ang_vel = detection_data['report']['angular_vel']
      except:
         ang_vel = "unknown"      
      # ANGULAR VELOCITY
      try:
         point_score = detection_data['report']['point_score']
      except:
         point_score = "unknown"

      # SYNC (HD/SD)
      try:
         if('sync' in detection_data):
            if('hd_ind' in detection_data['sync'] and 'sd_ind' in detection_data['sync']):
               sync = 1
         else:
            sync = 0
      except:
         sync = 0

      return mag,dur,red, res_error, ang_vel, point_score, sync
   
   else:

      return "unknown","unknown",0,"unknown","unknown","unknown"



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
   index_path = METEOR_ARCHIVE +  station_id + os.sep + METEOR + str(analysed_detection_name['year']) + os.sep + str(analysed_detection_name['month']).zfill(2) + os.sep +  str(analysed_detection_name['month']).zfill(2) +".json"
   
   # If the index doesn't exist, we create it
   if(cfe(index_path) == 0):
      write_month_index(int(analysed_detection_name['month']),int(analysed_detection_name['year']))

   # The next should be true after the creation og the index
   if(cfe(index_path) ==  1):
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
         mag,dur,red, res_error, point_score, ang_vel  =  get_diag_fields(analysed_detection_name['full_path'])
         
         new_detect = {
            "dur": dur,
            "red": red,
            "p": det,
            "mag": mag,
            "res_er":res_error,
            "point_score":point_score,
            "ang_v":ang_vel
         }

         # If the days already exist
         try:
            index_data['days'][str(analysed_detection_name['day'])]
         except:
            index_data['days'][str(analysed_detection_name['day'])] = {}

         index_data['days'][str(analysed_detection_name['day'])].append(new_detect)
 

         # Update the index
         main_dir = METEOR_ARCHIVE + station_id + os.sep + METEOR + str(analysed_detection_name['year']) + os.sep + str(analysed_detection_name['month']).zfill(2)
         save_json_file(main_dir + os.sep + str(analysed_detection_name['month']) + ".json", index_data, compress=True)

         # Update the corresponding Yearly index (?)
         write_year_index(int(analysed_detection_name['year']))

         return True

   return False




# Create Index for a given month
def create_json_index_month(month,year):

   station_id = get_station_id()
   main_dir = METEOR_ARCHIVE +  station_id + os.sep + METEOR + str(year) + os.sep + str(month).zfill(2)

   index_month = {'station_id':station_id,'year':int(year),'month':int(month),'days':{}}
   
   for day in sorted(glob.iglob(main_dir + '*' + os.sep + '*', recursive=True), reverse=True):	
      cur_day = os.path.basename(os.path.normpath(day))
 
      # Test if it is an index
      if('json' not in cur_day):
         cur_day_data = {}

         for detection in sorted(glob.iglob(day + os.sep +  '*' + '.json', recursive=True), reverse=True):
             
            mag,dur,red, res_error, ang_vel, point_score, sync  = get_diag_fields(detection)
            det = os.path.basename(detection)
            det = os.path.splitext(det)[0]

            # det[11:] => Here we also remove the Year, Month & Day of the detection 
            # since we know them from the JSON structure
            try:
               index_month['days'][int(cur_day)]
            except:
               index_month['days'][int(cur_day)] = []
 
            index_month['days'][int(cur_day)].append({'p':det[11:],'mag':mag,'dur':dur,'red':red,'res_er':res_error,'point_score':point_score,'ang_v':ang_vel,'sync':sync})
 
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

            if('json' not in cur_day):

               for detection in sorted(glob.iglob(day + os.sep +  '*' + '.json', recursive=True), reverse=True):
                  
                  mag,dur,red, res_error, ang_vel, point_score, sync = get_diag_fields(detection)


                  det = os.path.basename(detection)
                  det = os.path.splitext(det)[0]
                  # det[11:] => Here we also remove the Year, Month & Day of the detection 
                  # since we know them from the JSON structure
                  cur_day_data.append({'p':det[11:],'mag':mag,'dur':dur,'red':red,'res_er':res_error,'point_score':point_score,'ang_v':ang_vel,'sync':sync})

               #print("CUR DAY ")
               #print(cur_day)
               #print(os.path.normpath(day))
               #print(day)

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

         if(cur_month_data):
            index_year['months'][int(cur_month)].append(cur_month_data)

   return index_year 



# Write index for a given month
def write_month_index(month, year):
   json_data = create_json_index_month(month, year)  

   # Write Index if we have data
   if('days' in json_data): 
      main_dir = METEOR_ARCHIVE + get_station_id()  + os.sep + METEOR + str(year) + os.sep + str(month).zfill(2)

      if not os.path.exists(main_dir):
         os.makedirs(main_dir)

      with open(main_dir + os.sep + str(month).zfill(2) + ".json", 'w') as outfile:
         #Write compress format
         json.dump(json_data, outfile)
      outfile.close() 
      return True
   
   return False
 


# Write index for a given year
def write_year_index(year):
   json_data = create_json_index_year(year) 

   # Write Index if we have data
   if('months' in json_data):
      if(len(json_data['months'])>0 ): 
         main_dir = METEOR_ARCHIVE + get_station_id()  + os.sep + METEOR + str(year)
         save_json_file(main_dir + os.sep + str(year) + ".json", json_data, compress=True)
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

# Get index for a given month (and year)
def get_monthly_index(month,year):
   index_file = METEOR_ARCHIVE + get_station_id()  + os.sep + METEOR + str(year) + os.sep + str(month).zfill(2) + os.sep + str(month).zfill(2) + '.json'
   if(cfe(index_file)):
      return load_json_file(index_file)
   else:
      test = create_json_index_month(month,year)
      if(test):
         res = load_json_file(index_file)
         if(res):
            if('months' in res):
               #print("GET MONTHLY INDEX<br/>")
               #print(res['months'])
               if(res['months']=={"1": [], "2": [], "3": [], "4": [], "5": [], "6": [], "7": [], "8": [], "9": [], "10": [], "11": [], "12": []}):
                  return False
               else:
                  return test
            else:
               return False
         else:
            return False     
      else:
         return test


# Get detection full path based on a the limited string in the index
# ex: 'p': '22_36_24_000_010042-trim0519'
#      => '/mnt/ams2/meteor_archive/AMS7/METEOR/2019/11/16/2019_11_16_22_36_24_000_010042-trim0519.json' 
def get_full_det_path(path,station_id,date,day):
   return METEOR_ARCHIVE + station_id  + os.sep + METEOR + str(date.year) + os.sep + str(date.month).zfill(2) + os.sep + str(day).zfill(2) + os.sep + str(date.year) + '_' + str(date.month).zfill(2)+ '_' + str(day).zfill(2) + '_' + path + ".json"


# Test if a detection matches some criteria
def test_criteria(criter,criteria,detection):

   #print("<br>----------------------TEST CRITERIA<br>")
   #print("CRITER ")
   #print(criter)
   #print("<br>criteria ")
   #print(criteria)
   #print("<br>detection ")
   #print(detection)

   # Point Score
   if(criter=='point_score'):
      if(int(detection[criter])<int(criteria[criter]) or detection[criter]=='unknown'):
         return False 

   # Res. ERROR
   if(criter=='res_er'):
      if(float(detection[criter])>=float(criteria[criter]) or detection[criter]=='unknown'):
         #print("<br>RES ER  FALSE")
         return False
   
   # Magnitude
   if(criter=='mag'):
      if(float(detection[criter])<=float(criteria[criter]) or detection[criter]=='unknown'):
         #print("<br>mag  FALSE")
         return False
   
   # Angular Velocity
   if(criter=='ang_v'):
      #print("<br>ang_v !!!!!!!!!!<br>")  
      if(float(detection[criter])<=float(criteria[criter]) or detection[criter]=='unknown'):
         #print("<br>ang_v  FALSE")  
         return False 
      #print("<br>ang_v  TRUE")  

   # Sync
   if(criter=='sync' and criteria[criter]!=-1):
      if(int(detection[criter])!=int(criteria[criter]) or detection[criter]=='unknown'):
         return False

  

   return True

# Get results on index from a certain date
def get_results_from_date_from_monthly_index(criteria,start_date,end_date,max_res_per_page,cur_page): 

   #print("IN GET RESULTS --- ")
   #print("start_date : ")
   #print(start_date)
   #print("- end_date : ")
   #print(end_date) 
   #print("<br/>")

   #pprint("---------------<br>criteria ")
   #pprint(criteria)
   #pprint("<br>")

   # Get the index of the selected or current year
   # for the END DATE
   json_index =  get_monthly_index(end_date.month,end_date.year)

   #print("GET THE INDEX FOR " + str(end_date.month)  +'/' + str(end_date.year) +"<br>")

   # Nb of result not to display based on cur_page
   if(cur_page==1 or cur_page==0 ):
      number_of_res_to_give_up = 0
   else:
      number_of_res_to_give_up = max_res_per_page*(cur_page-1)
    
   # Get Station ID
   station_id = get_station_id()

   # Counter & Res
   res_counter = 0
   res_add_counter = 0
   res_to_return = [] 

   # Test if we are exploring the current Month & Year
   cur_year_and_month_test_START = False
   cur_year_and_month_test_END = False

   while(json_index!=False):
 
      cur_month = json_index['month']
      cur_year  = json_index['year']

      #print("<br>--------------<br>CUR MONTH " +  str(cur_month) +  " - CUR YEAR " +  str(cur_year) + "<br>")
      
      if(int(cur_month)==int(end_date.month) and int(cur_year)==int(end_date.year)): 
         cur_year_and_month_test_END = True
      else:
         cur_year_and_month_test_END = False
      
      if(int(cur_month)==int(start_date.month) and int(cur_year)==int(start_date.year)): 
         cur_year_and_month_test_START = True
      else:
         cur_year_and_month_test_START = False


      all_days =  json_index['days'] 
      keylist = list(all_days.keys())

      # We sort the days
      kk = sorted(keylist, key=int, reverse=True) 

      #print("cur_year_and_month_test_START " + str(cur_year_and_month_test_START) +"<br>")
      #print("cur_year_and_month_test_END " + str(cur_year_and_month_test_END) +"<br>")

      # We sort the days
      for day in kk:
 
            # We sort the detections within the day
            detections = sorted(json_index['days'][day], key=lambda k: k['p'], reverse=True)

            # If we are the current month & year END
            # and the current & year START
            # we need to take into account the days before end_date.day 
            # and the days after start_date.day
            if((     cur_year_and_month_test_START == True
                     and cur_year_and_month_test_END == True
                     and int(day)<=int(end_date.day)
                     and int(day)>=int(start_date.day)
               )
               or (      cur_year_and_month_test_START == False 
                     and cur_year_and_month_test_END == True
                     and int(day)<=int(end_date.day)
                  )
               or (      cur_year_and_month_test_START == False 
                     and cur_year_and_month_test_END == False
                     and int(year)<=int(end_date.year) 
                     and int(month)
                  )
            ):

               for detection in detections:

                  # Here we test the criteria
                  test = True

                  #pprint("---------------<br>criteria ")
                  #pprint(criteria)
                  #pprint("<br>")
                  

                  for criter in criteria:

                     #pprint(detection)
                     #pprint("<br>")

                     #pif(criter in detection):
                     #p   print("<br>detection[criter] " + str(detection[criter])+"<br>")  
                     #pelse:
                     #p   print("<br> " +  str(criter) + " not in detection<br>")

                     if(criter in detection and detection[criter]!='unknown'):
                        test = test_criteria(criter,criteria,detection)
                     else:
                        test = False
                     #p   print("<hr/>CRITER " + criter )
                     #p   print("<br>detection[criter] " + str(detection[criter]))      
      
                     if(test==False):
                        break   

                  if(test==True):

                     # We add it only if it fits the pagination
                     #if(len(res_to_return)<=max_res_per_page and res_counter>=number_of_res_to_give_up):

                     # We complete the detection['p'] to get the full path (as the index only has compressed name)
                     detection['p'] = get_full_det_path(detection['p'],station_id,end_date,day)
                     res_to_return.append(detection)

                     res_counter+=1  

      # Change Month & Year
      if(cur_month==1):
         cur_month = 12
         cur_year =  cur_year - 1
         json_index =  get_monthly_index(cur_month,cur_year)
  
         # Change the date backward
         week_day, numbers_of_days =  monthrange(cur_year,cur_month)
         end_date = end_date.replace(year=cur_year, month=cur_month,day=numbers_of_days) 

         #print("<br>11 - NEW END DATE ")
         #print(end_date)

      # Change Month only
      else:
         cur_month = cur_month -1 
         json_index =  get_monthly_index(cur_month,cur_year)

         # Change the date backward
         week_day, numbers_of_days =  monthrange(cur_year,cur_month)
         end_date = end_date.replace(year=cur_year, month=cur_month,day=numbers_of_days) 

         #print("<br>22 - NEW END DATE ")
         #print(end_date) 

      # We stop at the start_date
      if(end_date<=start_date):
         
         #print(" <br> start: ")
         #print(start_date)
         #print(" vs. end: ")
         #print(end_date)
         #print("STOP DATE TEST<br>")
         return res_to_return, res_counter
    
   return res_to_return, res_counter


# Return full path of a detection based on its name
def get_full_path_detection(analysed_name):
   index_file = METEOR_ARCHIVE + analysed_name['station_id'] + os.sep + METEOR +  analysed_name['year'] + os.sep +  analysed_name['month'].zfill(2) + os.sep  +  analysed_name['day'].zfill(2) + os.sep 
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



# GET HTML VERSION OF ONE DETECTION
def get_html_detection(det,detection,clear_cache):
   # Do we have a thumb stack preview for this detection?
   preview = does_cache_exist(det,"preview","/*.jpg")
   
   detection_id = det['name'].replace("_", "").replace(".json", "")
 
   if(len(preview)==0 or clear_cache is True):
      # We need to generate the thumbs 
      preview = generate_preview(det) 

   # Get Video for preview
   path_to_vid = get_video(det['full_path'])       

   # Otherwise preview = preview (:)
   res_html = '<div id="'+detection_id+'" class="preview col-lg-3 col-md-3 select-to mb-3'
   
   if(detection['red']==1):
      res_html += ' reduced">'
   else:
      res_html += '">'
 
   details_html = '<dl class="row mb-0 def mt-1">'

   details_html += '<dt class="col-12 list-onl title-list">Cam #'+det['cam_id']+' - <b>'+det['hour']+':'+det['min']+'</b></dt>'

   if(detection['mag']!='unknown'):
      details_html += '              <dt class="col-6">Mag</dt>  <dd class="col-6">' + str(detection['mag']) + '</dd>'
   
   if(detection['dur']!='unknown'):
      details_html += '              <dt class="col-6">Duration</dt>  	   <dd class="col-6">'+ str(detection['dur']) +'s</dd>'

   if(detection['res_er']!='unknown'):
      details_html += '              <dt class="col-6">Res. Error</dt>      <dd class="col-6">'+ str("{0:.4f}".format(float(detection['res_er'])))+'</dd>'
   #if(detection['point_score']!='unknown'):
   #   if detection['point_score'] > 3:
   #      span = "<font color='#FF0000'>"
   #      espan = "</font>"
   #   else:
   #      span = ""
   #      espan = ""
   #   details_html += '              <dt class="col-6">Point Score</dt>      <dd class="col-6">'+ span + str("{0:.4f}".format(float(detection['point_score']))) + espan +'</dd>'
   
      #details_html += '<dt class="col-6">Res. Error</dt><dd class="col-6">'+ str("{0:.4f}".format(float(detection['res_er'])))+'</dd>'
   

   #if(detection['ang_v']!='unknown'):
   #   details_html += '              <dt class="col-6">Ang. Velocity</dt>   <dd class="col-6">'+str("{0:.4f}".format(float(detection['ang_v'])))+'&deg;/s</dd>'

   if(detection['point_score']!='unknown'):
      score = str("{0:.4f}".format(float(detection['point_score'])))
      if detection['point_score'] > 3:
         score = "<b style='color:#ff0000'>" + score + "</b>"
      details_html += '<dt class="col-6">Point Score</dt><dd class="col-6">'+ score +'</dd>'

   if(detection['ang_v']!='unknown'):
      details_html += '<dt class="col-6">Ang. Velocity</dt><dd class="col-6">'+str("{0:.4f}".format(float(detection['ang_v'])))+'&deg;/s</dd>'
   
   if "sync" not in detection: 
   #if(detection['sync']!=1):
      details_html += '              <dt class="col-12"><div class="alert alert-danger p-1 m-0 text-center">Not synchronized</div></dt>'
 
   details_html += ' </dl>'   

   res_html += '  <a class="mtt has_soh" href="webUI.py?cmd=reduce2&video_file='+det['full_path']+'" title="Detection Reduce page">'
   res_html += '     <img alt="" class="img-fluid ns lz" src="'+preview[0]+'">'
#   res_html += '     <video class="show_on_hover" loop="true" autoplay="true" name="media" src="'+ det['full_path'].replace('.json','-SD.mp4')+'"><source type="video/mp4"></video>'
   res_html += '  </a>'
   res_html += '  <div class="list-onl">'+ details_html + '</div>'
   res_html += '  <div class="list-onl sel-box"><div class="custom-control big custom-checkbox">'
   res_html += '     <input type="checkbox" class="custom-control-input" id="chec_'+detection_id+'" name="'+detection_id+'">'     
   res_html += '     <label class="custom-control-label" for="chec_'+detection_id+'"></label>'
   res_html += '  </div></div>'
   res_html += '  <div class="d-flex justify-content-between">'
   res_html += '     <div class="pre-b gallery-only"><span class="mst">Cam #'+det['cam_id']+' - <b>'+det['hour']+':'+det['min']+'</b></span>'
   res_html += details_html
   
   
   res_html += '</div>'
   res_html += '     <div class="btn-toolbar pr-0 pb-0"><div class="btn-group"><a class="vid_link_gal col btn btn-primary btn-sm" title="Play Video" href="./video_player.html?video='+path_to_vid+'"><i class="icon-play"></i></a>'
   res_html += '     <a class="delete_meteor_archive_gallery col btn btn-danger btn-sm" title="Delete Detection" data-meteor="'+det['full_path']+'"><i class="icon-delete"></i></a></div></div>'
   res_html += '  </div></div>' 

   return res_html
 

# Get HTML version of each detection
def get_html_detections(res,clear_cache,version):

   res_html = ''
   prev_date = None
   cur_count = 0
  
   for detection in res:

      # We add the missing info to detection['p']
      # so the name analyser will work
      det = name_analyser(detection['p'])
      cur_date = get_datetime_from_analysedname(det) 
      
      if(prev_date is None):
         prev_date = cur_date
         res_html += '<div class="h2_holder d-flex justify-content-between mr-5 ml-5"><h2>'+cur_date.strftime("%Y/%m/%d")+" - %TOTAL%</h2></div>"
         res_html += '<div class="gallery gal-resize row text-center text-lg-left '+version+' mb-5 mr-5 ml-5">'

      elif(cur_date.month != prev_date.month or cur_date.day != prev_date.day or cur_date.year != prev_date.year):
         prev_date = cur_date
         if(cur_count>1):
            res_html = res_html.replace('%TOTAL%',str(cur_count)+ ' detections')
         else:
            res_html = res_html.replace('%TOTAL%',str(cur_count)+ ' detection only')
         res_html +=  '</div><div class="h2_holder d-flex justify-content-between mr-5 ml-5"><h2>'+cur_date.strftime("%Y/%m/%d")+" - %TOTAL%</h2></div>"
         res_html += '<div class="gallery gal-resize row text-center text-lg-left '+version+' mb-5 mr-5 ml-5">'
        
         cur_count = 0
 
 
      res_html += get_html_detection(det,detection,clear_cache)
      cur_count+=1
   
   if('%TOTAL%' in res_html):
      if(cur_count>1):
         res_html = res_html.replace('%TOTAL%',str(cur_count)+ ' detections')
      else:
         res_html = res_html.replace('%TOTAL%',str(cur_count)+ ' detection only')


   return res_html
 
 
# Create Criteria Selector
def create_criteria_selector(values, val, selected, criteria, all_msg, sign, unit=''):
   
   #print("IN CREATE CRITERIA<br>")
   #print("<br>VALUES :")
   #print(values)
   #print("<br>val :")
   #print(val)
   #print("<br>CRITERIA :")
   #print(criteria)
   #print("<br><br>SELECTED :")
   #print(selected)
   #print("<br><br>")
   
   # Build   selector
   select = ''
   one_selected = False

   # Add Default choice
   if selected is None:
       select+= '<option selected value="-1">'+all_msg+'</option>'
   else:
      one_selected = True 
      select+= '<option value="-1">'+all_msg+'</option>'
      criteria[val] = float(selected)

   for mag in values: 
 
      if(val=="sync" and mag==1):
         st_val = "Synchronized only"
      elif(val=="sync" and mag==0):
         st_val = "NOT Synchronized only"
      else:
         st_val = str(mag)

      if(one_selected==True):
         if(float(mag)==float(selected)):
            select+= '<option selected value="'+str(mag)+'">'+sign+st_val+ unit+'</option>'
         else:
            select+= '<option value="'+str(mag)+'">'+sign + st_val+ unit+'</option>'  
      else:
         select+= '<option value="'+str(mag)+'">'+sign + st_val+ unit+'</option>'  
   
   return select, criteria
    

# MAIN FUNCTION FOR THE ARCHIVE LISTING PAGE
def archive_listing(form): 
 
   cur_page  = form.getvalue('p')
   meteor_per_page = form.getvalue('meteor_per_page')
   clear_cache = form.getvalue('clear_cache')
   start_datetime = form.getvalue('start_date')
   end_datetime = form.getvalue('end_date')

   # Criteria
   selected_mag = form.getvalue('magnitude')
   selected_error = form.getvalue('res_er')
   selected_ang_vel = form.getvalue('ang_v')
   selected_sync = form.getvalue('sync')
   selected_pscore  = form.getvalue('point_score')

   # Build the page based on template  
   with open(ARCHIVE_LISTING_TEMPLATE, 'r') as file:
      template = file.read()

   # Page (for Pagination)
   if (cur_page is None) or (cur_page==0):
      cur_page = 1
   else:
      cur_page = int(cur_page)

   # NUMBER_OF_METEOR_PER_PAGE (for Pagination)

   # Do we have a cookie?
   cookies = os.environ.get('HTTP_COOKIE').rstrip()
   rpp = NUMBER_OF_METEOR_PER_PAGE
   if("archive_rpp" in cookies):
      tmp = cookies.split(";") 
      for cook in tmp:
         v = cook.split("=") 
         if('archive_rpp' in v[0]):
            rpp = v[1] 
   
   if(meteor_per_page is None):
      nompp = rpp
   else:
      nompp = int(meteor_per_page)  

   # Build num per page selector (for Pagination)
   ppp_select = ''
   for ppp in POSSIBLE_PER_PAGE:
      if(int(ppp)==int(nompp)):
         ppp_select+= '<option selected value="'+str(ppp)+'">'+str(ppp)+'/page</option>'
      else:
         ppp_select+= '<option value="'+str(ppp)+'">'+str(ppp)+'/page</option>'  
   template = template.replace("{RPP}", ppp_select)

   # LIST OF CRITERIA 
   criteria = {} 
   
   # Build MAGNITUDES selector
   mag_select, criteria = create_criteria_selector(POSSIBLE_MAGNITUDES,'mag',selected_mag, criteria,  'All Mag.', '>')
   template = template.replace("{MAGNITUDES}", mag_select)
    
   # Build ERRORS selector
   error_select, criteria = create_criteria_selector(POSSIBLE_ERRORS,'res_er',selected_error, criteria,  'All Res. Error', '<')
   template = template.replace("{RES_ERRORS}", error_select)

   # Build ANGULAR VELOCITIES selector
   ang_vel_select, criteria = create_criteria_selector(POSSIBLE_ANG_VELOCITIES,'ang_v',selected_ang_vel, criteria,  'All Ang. Vel.', '>', unit='&deg;/s')
   template = template.replace("{ANG_VELOCITIES}", ang_vel_select) 
   
   # Build SYNC selector 
   sync_select, criteria = create_criteria_selector(POSSIBLE_SYNC,'sync',selected_sync, criteria,  'All Sync.', '')
   template = template.replace("{SYNC}", sync_select) 
   
   # Build POINT SCORE selector 
   point_score_select, criteria = create_criteria_selector(POSSIBLE_POINT_SCORE,'point_score',selected_pscore, criteria,  'All Score', '>')
   template = template.replace("{P_SCORE}", point_score_select) 
    
   # Clear_cache
   if(clear_cache is None):
      clear_cache = False
   else:
      clear_cache = True

   # Day?
   has_limit_day = False

   if (start_datetime is None and end_datetime is None):
      start_datetime = datetime.now()- timedelta(days=1)
      end_datetime   = datetime.now() 
   else:
      start_datetime = datetime.strptime(start_datetime,"%Y/%m/%d") 
      end_datetime  = datetime.strptime(end_datetime,"%Y/%m/%d") 
      has_limit_day = True
   
   template = template.replace("{START_DATE}",start_datetime.strftime("%Y/%m/%d"));
   template = template.replace("{END_DATE}",end_datetime.strftime("%Y/%m/%d"));
    
   # Search the results through the monthly indexes
   res, total = get_results_from_date_from_monthly_index(criteria,start_datetime,end_datetime,int(nompp),cur_page)
  
   # CREATE URL FOR THE PAGINATION
   pagination_url  = "/pycgi/webUI.py?cmd=archive_listing&meteor_per_page="+str(nompp)

   if(has_limit_day!=0):
      pagination_url += "&start_date="+str(start_datetime.strftime("%Y/%m/%d"))+"&end_date="+str(end_datetime.strftime("%Y/%m/%d"))
      
   for criter in criteria:
      pagination_url += "&"+criter+"="+str(criteria[criter])

   pagination = get_pagination(cur_page,total,pagination_url,int(nompp))

   found_text = ""
   if(pagination[2] != ''):
      found_text += "<small>Page  " + format(cur_page) + "/" +  format(pagination[2])+"</small>"     
 
      
   # GALLERIE or LIST are managed with cookies
   # Do we have a cookie for gallery or list? 
   version = ''
   if("archive_view" in cookies):
      tmp = cookies.split(";")
      for cook in tmp:
         v = cook.split(";") 
         if('list' in v[0]):
            version = 'list'
   template = template.replace("{LIST_VIEW}", version)


   # Create HTML Version of each detection
   res_html = get_html_detections(res,clear_cache,version) 
   if(res_html!=''):
      template = template.replace("{RESULTS}", res_html)

   #   # Pagination
   if(len(res)>=1 and pagination and pagination[0]):  
      template = template.replace("{PAGINATION}", pagination[0])
   else:
      template = template.replace("{PAGINATION}", "")
 
   if(len(res)==0): 
      template = template.replace("{RESULTS}", "<div class='alert alert-danger mx-auto'>No detection found in your the archive for your criteria.</div>")
      template = template.replace("{PAGINATION}", "") 
      template = template.replace("{FOUND}", "")
   elif((len(res))!=total):
      template = template.replace("{FOUND}", "<div class='page_h ml-3'><small>Displaying " + str(len(res)) + " out of " +  str(total)  + " detections. </small>"+ found_text + "/div>")
   elif(len(res)==1):
      template = template.replace("{FOUND}", "<div class='page_h ml-3'><small>Displaying only 1 detection matching your criteria.</small> "+ found_text + "</div>")
   else:
      template = template.replace("{FOUND}", "<div class='page_h ml-3'><small>Displaying all " + str(len(res)) + " detections matching your criteria.</small> "+ found_text + "</div>")

   # Display Template
   return template
