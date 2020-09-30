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
POSSIBLE_ERRORS = [0.5,1,2,3,5]
POSSIBLE_ANG_VELOCITIES = [1,2,3,4,5,6,7,8,9,10,11,12,13,15,16,17,18,19,20,21,22,23,24,25]
POSSIBLE_SYNC = [0,1]
POSSIBLE_MULTI = [0,1]
POSSIBLE_POINT_SCORE = [3,5,10]

# VIDEO PREVIEW
DEFAULT_VIDEO_PREV_ON_ARCHIVE = 0

# TRASH FOLDER
TRASH_FOLDER = '/mnt/ams2/trash'
 
 
# Delete Multiple Detections at once

def delete_old_detection(arc_file):
   arc_js = load_json_file(arc_file)
   if arc_js == 0:
      print("Arc json doesn't exist", arc_file)
      return()

   if "org_sd_vid" in arc_js['info']:
      sd_base = arc_js['info']['org_sd_vid'].replace(".mp4", "")
   else:
      sd_base = None
      sd_fn = None
   if "org_hd_vid" in arc_js['info']:
      if arc_js['info']['org_hd_vid'] != 0: 
         hd_base = arc_js['info']['org_hd_vid'].replace(".mp4", "")
      else:
         hd_base = None
         hd_fn = None
   else:
      hd_base = None
      hd_fn = None

   if sd_base is not None:
      sd_fn = sd_base.split("/")[-1]
   if hd_base is not None:
      hd_fn = hd_base.split("/")[-1]
   
   if sd_fn is not None:
      day = sd_fn[0:10]
      sd_wild = "/mnt/ams2/meteors/" + day + "/" + sd_fn + "*"
   else:
      sd_wild = None

   if hd_fn is not None:
      day = hd_fn[0:10]
      hd_wild = "/mnt/ams2/meteors/" + day + "/" + hd_fn + "*"
   else:
      hd_wild = None

   # get the old min file detect name so we can move that too
   mf = sd_fn.split("-trim")[0]
   min_met = "/mnt/ams2/SD/proc2/" + day + "/data/" + mf + "-meteor.json"
   min_nomet = "/mnt/ams2/SD/proc2/" + day + "/data/" + mf + "-nometeor.json"
   min_cmd = "mv " + min_met + " " + min_nomet
   old_hd_cmd = "mv " + hd_wild + " /mnt/ams2/trash/"
   old_sd_cmd = "mv " + sd_wild + " /mnt/ams2/trash/"
   os.system(min_cmd) 

   os.system(old_hd_cmd) 
   os.system(old_sd_cmd) 

def delete_multiple_archived_detection(detections):

   # In case we only have one... it's a string
   if(isinstance(detections, str)):
      detections = [detections]

   for det in detections:

      analysed_name = name_analyser(det)
      # First open the arc file and get the 'old_vid' and hd vid values (these files need to be deleted too if they exist)
      delete_old_detection(det)

      # Next open the old json file and get HD filename (this will be one of the wildcards) (arc value may not be correct)
      # get wild card values for old sd and HD files
      # move all of these to trash



      # Remove the Cache files 
      cache_path = get_cache_path(analysed_name)
      if os.path.isdir(cache_path):
         shutil.rmtree(cache_path)


      #We move all the other files to TRASH_FOLDER

      # MOVE Json to trash
      if os.path.isfile(det): 
         cmd = "mv " + det +  " " + TRASH_FOLDER  
         os.system(cmd) 

      # Remove HD     
      det = det.replace('.json','-HD.mp4')
      if os.path.isfile(det):
         cmd = "mv " + det +  " " + TRASH_FOLDER  
         os.system(cmd) 

      # Remove SD
      det = det.replace('-HD','-SD')
      if os.path.isfile(det):
         cmd = "mv " + det +  " " + TRASH_FOLDER  
         os.system(cmd) 

      # Remove Crop
      det = det.replace('-SD','-HD-crop')
      if os.path.isfile(det):
         cmd = "mv " + det +  " " + TRASH_FOLDER  
         os.system(cmd) 

      # Remove crop thumb preview
      det = det.replace('-HD-crop','-HD-crop-thumb')
      if os.path.isfile(det):
         cmd = "mv " + det +  " " + TRASH_FOLDER  
         os.system(cmd) 



      # Update Index (?)
      #write_month_index(int(analysed_name['month']),int(analysed_name['year']))
      #write_year_index(int(analysed_name['year']))


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


      # IS MULTI (TEMPORARY SOLUTION WITH ONLY A BOOLEAN)
      try: 
         if('info' in detection_data):
            if('multi_station' in detection_data['info']):
               multi = 1
            else:
               multi = 0
         else:
            multi = 0
      except:
         multi = 0

      return mag,dur,red, res_error, ang_vel, point_score, sync, multi
   
   else:

      return "unknown","unknown",0,"unknown","unknown","unknown", "unknown"



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
         mag,dur,red, res_error, point_score, ang_vel, multi  =  get_diag_fields(analysed_detection_name['full_path'])
         
         new_detect = {
            "dur": dur,
            "red": red,
            "p": det,
            "mag": mag,
            "res_er":res_error,
            "point_score":point_score,
            "ang_v":ang_vel,
            "multi":multi
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
            #print("DET:", detection)             
            mag,dur,red, res_error, ang_vel, point_score, sync, multi  = get_diag_fields(detection)
            det = os.path.basename(detection)
            det = os.path.splitext(det)[0]

            # det[11:] => Here we also remove the Year, Month & Day of the detection 
            # since we know them from the JSON structure
            try:
               index_month['days'][int(cur_day)]
            except:
               index_month['days'][int(cur_day)] = []
 
            index_month['days'][int(cur_day)].append({'p':det[11:],'mag':mag,'dur':dur,'red':red,'res_er':res_error,'point_score':point_score,'ang_v':ang_vel,'sync':sync,'multi':multi})
 
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
                  
                  mag,dur,red, res_error, ang_vel, point_score, sync, multi = get_diag_fields(detection)


                  det = os.path.basename(detection)
                  det = os.path.splitext(det)[0]
                  # det[11:] => Here we also remove the Year, Month & Day of the detection 
                  # since we know them from the JSON structure
                  cur_day_data.append({'p':det[11:],'mag':mag,'dur':dur,'red':red,'res_er':res_error,'point_score':point_score,'ang_v':ang_vel,'sync':sync,'multi':multi})

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
   #print("INDEX FILE", index_file) 
   #exit()
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


   #print("<br><br> CRITER<br>")
   #print(criter)
   #print("<br><br> criteria<br>")
   #print(str(criteria))
   #print("<br><br> detection<br>")
   #print(detection)
   #print("<br><br>")

   # Point Score
   if(criter=='point_score'):
      if(int(detection[criter])<int(criteria[criter]) or detection[criter]=='unknown'):
         return False 

   # Res. ERROR
   if(criter=='res_er'):
      if(float(detection[criter])<=float(criteria[criter]) or detection[criter]=='unknown'):
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

   # Multi
   if(criter=='multi'):

      #print("<br>detection ")
      #print(detection)
      #print("<br>CRITER")
      #print(str(criter))
      #print("<br>CRITER VALUE ")
      #print(str(int(criteria[criter])))
      #print("<br>DETECT VALUE ")
      #print(str(int(detection[criter])))
      #print("<br>")

      if(int(criteria[criter])!=int(detection[criter])):
            #print("False<br>")
            #sys.exit(0)
            return False 
      #else:
         #print("TRUE<br>")


      #sys.exit(0)

   return True

# Get results on index from a certain date
def get_results_from_date_from_monthly_index(criteria,start_date,end_date,max_res_per_page,cur_page): 
 
   # Get the index of the selected or current year
   # for the END DATE
   json_index =  get_monthly_index(end_date.month,end_date.year) 

   # Nb of result not to display based on cur_page
   if(cur_page==1 or cur_page==0 ):
      number_of_res_to_give_up = 0
   else:
      number_of_res_to_give_up = max_res_per_page*(cur_page-1)

   #print("NUMBER OF RES TO GIVE UP " + str(number_of_res_to_give_up))
    
   # Get Station ID
   station_id = get_station_id()

   # Counter & Res
   res_counter = 0
   res_add_counter = 0
   res_to_return = [] 

   # Test if we are exploring the current Month & Year
   cur_year_and_month_test_START = False
   cur_year_and_month_test_END = False


   # Dict of day => total detection
   # so we can display the total # of detections for a given day 
   # even if we don't show all the detections
   all_days_details = {}

   while(json_index!=False):
 
      cur_month = json_index['month']
      cur_year  = json_index['year']

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

      # We sort the days
      for day in kk:

            # We get the total # of detections for the current in case we don't display them all
            all_days_details[str(cur_year)+'/'+ "{:02d}".format(int(cur_month))+'/'+"{:02d}".format(int(day))] = len(json_index['days'][day]) 

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
                        break    
                       

                  if(test==True):

                     # We add it only if it fits the pagination
                     if(len(res_to_return)<max_res_per_page and res_counter>=number_of_res_to_give_up):
                        # We complete the detection['p'] to get the full path (as the index only has compressed name)
                        detection['p'] = get_full_det_path(detection['p'],station_id,end_date,day)
                        res_to_return.append(detection)
                        #print("MAX " + str(max_res_per_page) + "<br>")
                        #print("len(res_to_return) " + str(len(res_to_return)) + "<br>")

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
         return res_to_return, res_counter, all_days_details
    

   return res_to_return, res_counter, all_days_details


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
def get_html_detection(det,detection,clear_cache,video_prev):

   # Do we have a thumb stack preview for this detection?
   preview = does_cache_exist(det,"preview","/*.jpg")
   
   if(len(preview)==0 or clear_cache is True):
      # We need to generate the thumbs 
      preview = generate_preview(det) 
   
   detection_id = det['name'].replace("_", "").replace(".json", "")
 

   # Get Video for preview
   path_to_vid = get_video(det['full_path'])       

   # Otherwise preview = preview (:)
   res_html = '<div id="'+detection_id+'" class="preview select-to mb-3'
   
   if(detection['red']==1):
      res_html += ' reduced">'
   else:
      res_html += '">'
 
   details_html = '<dl class="row mb-0 def mt-1">'

   details_html += '<dt class="col-12 list-onl title-list"><b>Cam #'+det['cam_id']+'</b> - <b>'+det['hour']+':'+det['min']+'</b></dt>'

   if(detection['mag']!='unknown'):
      details_html += '<dt class="col-6">Mag</dt><dd class="col-6">' + str(detection['mag']) + '</dd>'
   
   if(detection['dur']!='unknown'):
      details_html += '<dt class="col-6">Duration</dt><dd class="col-6">'+ str(detection['dur']) +'s</dd>'

   if(detection['res_er']!='unknown'):
      score =  str("{0:.4f}".format(float(detection['res_er'])))
      if detection['res_er'] > 3:
         score = "<b style='color:#ff0000'>" + score + "</b>"
      details_html += '<dt class="col-6">Res. Error</dt> <dd class="col-6">'+ score +'</dd>'
  
   if(detection['point_score']!='unknown'):
      score = str("{0:.4f}".format(float(detection['point_score'])))
      if detection['point_score'] > 3:
         score = "<b style='color:#ff0000'>" + score + "</b>"
      details_html += '<dt class="col-6">Point Score</dt><dd class="col-6">'+ score +'</dd>'

   if(detection['ang_v']!='unknown'):
      details_html += '<dt class="col-6">Ang. Velocity</dt><dd class="col-6">'+str("{0:.4f}".format(float(detection['ang_v'])))+'&deg;/s</dd>'
   
   if "sync" not in detection:  
      details_html += '<dt class="col-12"><div class="alert alert-danger p-1 m-0 text-center">Not synchronized</div></dt>'
   
   details_html += ' </dl>'   

   if "multi" in detection and int(detection['multi'])!=0:      
         details_html += "<div class='badge'>MULTI</div>"
         

   res_html += '  <a class="mtt has_soh" href="webUI.py?cmd=reduce2&video_file='+det['full_path']+'" title="Detection Reduce page">'
   res_html += '     <img alt="" class="img-fluid ns lz" src="'+preview[0]+'">'
   
   # Only if option is selected
   if(int(video_prev)==1):
      res_html += '     <video class="show_on_hover" preload="true" loop="true" autoplay="true" name="media" src="'+ det['full_path'].replace('.json','-SD.mp4')+'"><source type="video/mp4"></video>'
   
   res_html += '  </a>'
   res_html += '  <div class="list-onl">'+ details_html + '</div>'
   res_html += '  <div class="list-onl sel-box"><div class="custom-control big custom-checkbox">'
   res_html += '     <input type="checkbox" class="custom-control-input" id="chec_'+detection_id+'" name="'+detection_id+'">'     
   res_html += '     <label class="custom-control-label" for="chec_'+detection_id+'"></label>'
   res_html += '  </div></div>'
   res_html += '  <div class="d-flex justify-content-between pr">'
   res_html += '     <div class="pre-b gallery-only"><span class="mst">Cam #'+det['cam_id']+' - <b>'+det['hour']+':'+det['min']+'</b></span>'
   res_html += details_html
   
   
   res_html += '</div>'
   res_html += '     <div class="btn-toolbar pr-0 pb-0"><div class="btn-group"><a class="vid_link_gal col btn btn-primary btn-sm" title="Play Video" href="./video_player.html?video='+path_to_vid+'"><i class="icon-play"></i></a>'
   res_html += '     <a class="delete_meteor_archive_gallery col btn btn-danger btn-sm" title="Delete Detection" data-meteor="'+det['full_path']+'"><i class="icon-delete"></i></a></div></div>'
   res_html += '  </div></div>' 

   return res_html
 

# Get HTML version of each detection
def get_html_detections(res,all_days_details,clear_cache,version,video_prev):
 
   res_html = ''
   prev_date = None
   cur_count = 0 

   for detection in res:

      # We add the missing info to detection['p']
      # so the name analyser will work
      det = name_analyser(detection['p'])
      #print("DETECTION!:", det, detection)
      cur_date = get_datetime_from_analysedname(det) 
      
      if(prev_date is None):
         res_html += '<div class="h2_holder d-flex justify-content-between mr-5 ml-5"><h2>'+cur_date.strftime("%Y/%m/%d")+" - %TOTAL%</h2></div>"
         res_html += '<div class="gallery gal-resize row text-center text-lg-left '+version+' mb-5">'

      elif(cur_date.month != prev_date.month or cur_date.day != prev_date.day or cur_date.year != prev_date.year):
         if(cur_count>1):
            res_html = res_html.replace('%TOTAL%',str(cur_count)+ ' detections')
         else:
            res_html = res_html.replace('%TOTAL%',str(cur_count)+ ' detection only')
         res_html +=  '</div><div class="h2_holder d-flex justify-content-between "><h2>'+cur_date.strftime("%Y/%m/%d")+" - %TOTAL%</h2></div>"
         res_html += '<div class="gallery gal-resize row text-center text-lg-left '+version+' mb-5">'
        
         cur_count = 0

      
      prev_date = cur_date
 
      res_html += get_html_detection(det,detection,clear_cache,video_prev)
      cur_count+=1
   
   if('%TOTAL%' in res_html):

      new_total = str(cur_count)+ ' detection only'

      if(cur_count>1):
         new_total = str(cur_count)+ ' detections'
         
      # Check if we display them all
      if cur_date.strftime("%Y/%m/%d") in all_days_details and int(all_days_details[cur_date.strftime("%Y/%m/%d")]!=cur_count):
         new_total += ' out of ' +  str(all_days_details[cur_date.strftime("%Y/%m/%d")])  

      res_html = res_html.replace('%TOTAL%',new_total) 

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
      elif(val=='multi' and mag==1):
         st_val = "Multi-detections only"
      elif(val=='multi' and mag==0):
         st_val = "Single detections only"
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
 
   # Criteria (filters)
   selected_mag      = form.getvalue('magnitude')
   selected_error    = form.getvalue('res_er')
   selected_ang_vel  = form.getvalue('ang_v')
   selected_sync     = form.getvalue('sync')
   selected_pscore   = form.getvalue('point_score')
   selected_multi    = form.getvalue('multi')

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
   try:
      cookies = os.environ.get('HTTP_COOKIE').rstrip()
      rpp = NUMBER_OF_METEOR_PER_PAGE
      video_prev = DEFAULT_VIDEO_PREV_ON_ARCHIVE
   except:
      cookies = {}
      rpp = 50
      video_prev = 0

   if("archive_rpp" in cookies):
      tmp = cookies.split(";") 
      for cook in tmp:
         v = cook.split("=") 
         if('archive_rpp' in v[0]):
            rpp = v[1] 
         
   if("video_prev" in cookies):
      tmp = cookies.split(";") 
      for cook in tmp:
         v = cook.split("=") 
         if('video_prev' in v[0]):
            video_prev = v[1]       


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
   criteria_text = []
   
   # Build MAGNITUDES selector
   mag_select, criteria = create_criteria_selector(POSSIBLE_MAGNITUDES,'mag',selected_mag, criteria,  'All Magnitude', '>')
   template = template.replace("{MAGNITUDES}", mag_select)

   if selected_mag is not None and int(selected_mag) > -1:
      criteria_text.append("<a data-toggle='modal' data-target='#staticBackdrop' href='#' title='Magnitude'>Magnitude >" + str(selected_mag) +  "</a>")
    
   # Build ERRORS selector
   error_select, criteria = create_criteria_selector(POSSIBLE_ERRORS,'res_er',selected_error, criteria,  'All Resolution Error', '>')
   template = template.replace("{RES_ERRORS}", error_select)

   if selected_error is not None and float(selected_error) > -1:
      criteria_text.append("<a data-toggle='modal' data-target='#staticBackdrop' href='#' title='Resolution Error'>Resolution Error >" + str(selected_error) +  "</a>")

   # Build ANGULAR VELOCITIES selector
   ang_vel_select, criteria = create_criteria_selector(POSSIBLE_ANG_VELOCITIES,'ang_v',selected_ang_vel, criteria,  'All Angular Velocity', '>', unit='&deg;/s')
   template = template.replace("{ANG_VELOCITIES}", ang_vel_select) 
   
   if selected_ang_vel is not None and int(selected_ang_vel) > -1:
      criteria_text.append("<a data-toggle='modal' data-target='#staticBackdrop' href='#' title='Angular Velocity'>Angular Velocity >" + str(selected_ang_vel) +  "&deg;/s</a>")

   # Build SYNC selector 
   sync_select, criteria = create_criteria_selector(POSSIBLE_SYNC,'sync',selected_sync, criteria,  'All Synchronization', '')
   template = template.replace("{SYNC}", sync_select) 


   if selected_sync is not None and int(selected_sync) > -1:
      if(selected_sync==1):
         sel_text = "Synchronized only"
      else:
         sel_text= "NOT Synchronized only"
      criteria_text.append("<a data-toggle='modal' data-target='#staticBackdrop' href='#' title='Synchronization'>" + sel_text +  "</a>")
   
   
   # Build MULTI selector
   multi_select, criteria = create_criteria_selector(POSSIBLE_MULTI,'multi',selected_multi, criteria,  'All kind of detections', '')
   template = template.replace("{MULTI}", multi_select) 

   if selected_multi is not None and float(selected_multi) > -1:
      if(float(selected_multi)==1.0):
         sel_text = "Multi-detections only"
      else:
         sel_text= "Single detections only"
      criteria_text.append("<a data-toggle='modal' data-target='#staticBackdrop' href='#' title='Detection type'>" + sel_text +  "</a>")
 
   # Build POINT SCORE selector 
   point_score_select, criteria = create_criteria_selector(POSSIBLE_POINT_SCORE,'point_score',selected_pscore, criteria,  'All Score', '>')
   template = template.replace("{P_SCORE}", point_score_select) 
    
   if selected_pscore is not None and int(selected_pscore) > -1:
      criteria_text.append("<a data-toggle='modal' data-target='#staticBackdrop' href='#' title='Score'>Point Score >" + str(selected_pscore) +  "</a>")


   # Clear_cache
   if(clear_cache is None):
      clear_cache = False
   else:
      clear_cache = True

   # Day?
   has_limit_day = False

   if (start_datetime is None and end_datetime is None):
      start_datetime = datetime.now()- timedelta(days=30)
      end_datetime   = datetime.now() 
   else:
      start_datetime = datetime.strptime(start_datetime,"%Y/%m/%d") 
      end_datetime  = datetime.strptime(end_datetime,"%Y/%m/%d") 
      has_limit_day = True
   
   template = template.replace("{START_DATE}",start_datetime.strftime("%Y/%m/%d"));
   template = template.replace("{END_DATE}",end_datetime.strftime("%Y/%m/%d"));
    
   # Search the results through the monthly indexes
   res, total, all_days_details = get_results_from_date_from_monthly_index(criteria,start_datetime,end_datetime,int(nompp),cur_page)
   #print(res)
   #exit()
  
   # CREATE URL FOR THE PAGINATION
   pagination_url  = "/pycgi/webUI.py?cmd=archive_listing&meteor_per_page="+str(nompp)

   if(has_limit_day!=0):
      pagination_url += "&start_date="+str(start_datetime.strftime("%Y/%m/%d"))+"&end_date="+str(end_datetime.strftime("%Y/%m/%d"))
      
   for criter in criteria:
      pagination_url += "&"+criter+"="+str(criteria[criter])

   pagination = get_pagination(cur_page,total,pagination_url,int(nompp))

   found_text = ""
   if(pagination[2] != ''):
      found_text += "- Page  " + format(cur_page) + "/" +  format(pagination[2])     
 
      
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

   # UPDATE video_prev option
   if(int(video_prev)==1):
      template = template.replace("{VIDEO_PREVIEW_ACTIVE}", "active")
      template = template.replace("{NO_VIDEO_PREVIEW_ACTIVE}", "")
   else:
      template = template.replace("{VIDEO_PREVIEW_ACTIVE}", "")
      template = template.replace("{NO_VIDEO_PREVIEW_ACTIVE}", "active")      
 

   # Create HTML Version of each detection
   res_html = get_html_detections(res,all_days_details,clear_cache,version,video_prev) 
   if(res_html!=''):
      template = template.replace("{RESULTS}", res_html)

   #   # Pagination
   if(len(res)>=1 and pagination and pagination[0]):  
      template = template.replace("{PAGINATION}", pagination[0])
   else:
      template = template.replace("{PAGINATION}", "")
 
   criteria_text = ' - '.join(criteria_text)

   if(len(res)==0): 
      template = template.replace("{RESULTS}", "<div class='alert alert-danger mx-auto'>No detection found in your archive for your criteria. "+ criteria_text +"</div>")
      template = template.replace("{PAGINATION}", "") 
      template = template.replace("{FOUND}", "")
   elif((len(res))!=total):
      if(criteria_text==''):
         template = template.replace("{FOUND}", "<div style='background-color: transparent; line-height: 1rem; margin: 1rem 3rem;' class='alert alert-info page_h ml-3'>Displaying " + str(len(res)) + " out of " +  str(total)  + " detections. "+ found_text + "</div>")
      else:
         template = template.replace("{FOUND}", "<div style='background-color: transparent; line-height: 1rem; margin: 1rem 3rem;' class='alert alert-info page_h ml-3'>Displaying " + str(len(res)) + " out of " +  str(total)  + " detections. Filters: "+criteria_text+"  " + found_text + "</div>")

   elif(len(res)==1):
      if(criteria_text==''):
         template = template.replace("{FOUND}", "<div style='background-color: transparent; line-height: 1rem; margin: 1rem 3rem;' class='alert alert-info page_h ml-3'>Displaying only 1 detection matching your criteria. "+ found_text + "</div>")
      else:
         template = template.replace("{FOUND}", "<div style='background-color: transparent; line-height: 1rem; margin: 1rem 3rem;' class='alert alert-info page_h ml-3'>Displaying only 1 detection. Filters: "+criteria_text+"  " + found_text + "</div>")

   else:
      if(criteria_text==''):
         template = template.replace("{FOUND}", "<div style='background-color: transparent; line-height: 1rem; margin: 1rem 3rem;' class='alert alert-info page_h ml-3'>Displaying all " + str(len(res)) + " detections matching your criteria. "+ found_text + "</div>")
      else:
         template = template.replace("{FOUND}", "<div style='background-color: transparent; line-height: 1rem; margin: 1rem 3rem;' class='alert alert-info page_h ml-3'>Displaying all " + str(len(res)) + " detections. Filters: "+criteria_text+"  " + found_text + "</div>")


   # Display Template
   return template
