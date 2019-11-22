# coding: utf-8
import glob
import os
import json
import datetime
import sys
import collections 

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


      return mag,dur,red, res_error, ang_vel
   
   else:

      return "unknown","unknown",0,"unknown","unknown"



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
         mag,dur,red, res_error, ang_vel  =  get_diag_fields(analysed_detection_name['full_path'])
         
         new_detect = {
            "dur": dur,
            "red": red,
            "p": det,
            "mag": mag,
            "res_er":res_error,
            "ang_v":ang_vel
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
         main_dir = METEOR_ARCHIVE + station_id + os.sep + METEOR + str(analysed_detection_name['year']) + os.sep + str(analysed_detection_name['month']).zfill(2)
         save_json_file(main_dir + os.sep + str(analysed_detection_name['month']) + ".json", index_data)

         #print("INDEX UPDATED")
         #print(main_dir + os.sep + str(analysed_detection_name['month']) + ".json")

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
             
            mag,dur,red, res_error, ang_vel  = get_diag_fields(detection)
            det = os.path.basename(detection)
            det = os.path.splitext(det)[0]

            # det[11:] => Here we also remove the Year, Month & Day of the detection 
            # since we know them from the JSON structure
            try:
               index_month['days'][int(cur_day)]
            except:
               index_month['days'][int(cur_day)] = []
 
            index_month['days'][int(cur_day)].append({'p':det[11:],'mag':mag,'dur':dur,'red':red,'res_er':res_error,'ang_v':ang_vel})
 
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
                  
                  mag,dur,red, res_error, ang_vel = get_diag_fields(detection)


                  det = os.path.basename(detection)
                  det = os.path.splitext(det)[0]
                  # det[11:] => Here we also remove the Year, Month & Day of the detection 
                  # since we know them from the JSON structure
                  cur_day_data.append({'p':det[11:],'mag':mag,'dur':dur,'red':red,'res_er':res_error,'ang_v':ang_vel})

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
         json.dump(json_data, outfile, indent=4, sort_keys=True)
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

# Get index for a given month (and year)
def get_monthly_index(month,year):
   index_file = METEOR_ARCHIVE + get_station_id()  + os.sep + METEOR + str(year) + os.sep + str(month).zfill(2) + os.sep + str(month).zfill(2) + '.json'
   if(cfe(index_file)):
      return load_json_file(index_file)
   else:
      test = create_json_index_month(month,year)
      if(test):
         return load_json_file(index_file)
      else:
         return test


# Get results on index from a certain date
def get_results_from_date_from_monthly_index(criteria,date,json_index,max_res_per_page,cur_page): 
   res = []
   res_cnt = 0 
   cur_month_test = False

   # Nb of result not to display based on cur_page
   if(cur_page==1):
      number_of_res_to_give_up = 0
   else:
      number_of_res_to_give_up = max_res_per_page*cur_page

   
 
   if("days" in json_index and "month" in json_index):
      cur_month = json_index['month']
      
      if(int(cur_month)==int(date.month)):
         cur_month_test = True

      all_days =  json_index['days'] 
      keylist = list(all_days.keys())

      # We sort the days
      for day in sorted(keylist, key=int, reverse=True):

         # We sort the detections within the day
         detections = sorted(json_index['days'][day], key=lambda k: k['p'], reverse=True)

         if( (cur_month_test and int(day)<=int(date.day) and res_cnt<=max_res_per_page) 
          or (not cur_month_test and int(cur_month)<int(date.month)) and res_cnt<=max_res_per_page):
          
            for  detection  in  detections:
               if(res_cnt<=max_res_per_page):
 
                  # Here we test the criteria
                  test = True
                  for criter in criteria:

                     if(detection[criter]!='unknown'):
                        if(criter=='res_er'):
                           if(float(detection[criter])>=float(criteria[criter])):
                              test = False
   
                        if(criter=='mag'):
                           if(float(detection[criter])<=float(criteria[criter])):
                              test = False
   
                        if(criter=='ang_v'):
                           if(float(detection[criter])<=float(criteria[criter])):
                              test = False                     
   

                     if(test==False):
                        break   


                  if(test==True ):
                     # We complete the detection['p'] to get the full path (as the index only has compressed name)
                     # ex: 'p': '22_36_24_000_010042-trim0519'
                     #      => '/mnt/ams2/meteor_archive/AMS7/METEOR/2019/11/16/2019_11_16_22_36_24_000_010042-trim0519.json' 
                     detection['p'] = METEOR_ARCHIVE + get_station_id()  + os.sep + METEOR + str(date.year) + os.sep + str(date.month).zfill(2) + os.sep + str(day).zfill(2) + os.sep + str(date.year) + '_' + str(date.month).zfill(2)+ '_' + str(day).zfill(2) + '_' + detection['p'] + ".json"
                     res.append(detection)
                     res_cnt+=1 
                  #else:and res_cnt<=number_of_res_to_give_up
                  #   number_of_res_to_give_up-=1
  

   return res


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

   if(len(preview)==0 or clear_cache is True):
      # We need to generate the thumbs 
      preview = generate_preview(det) 

   # Get Video for preview
   path_to_vid = get_video(det['full_path'])       

   # Otherwise preview = preview (:)
   res_html = '<div class="preview col-lg-3 col-md-3 select-to mb-3'
   
   if(detection['red']==1):
      res_html += ' reduced">'
   else:
      res_html += '">'

   res_html += '  <a class="mtt has_soh" href="webUI.py?cmd=reduce2&video_file='+det['full_path']+'" title="Detection Reduce page">'
   res_html += '     <img alt="" class="img-fluid ns lz" src="'+preview[0]+'">'
   res_html += '     <video class="show_on_hover" loop="true" autoplay="true" name="media" src="'+ det['full_path'].replace('.json','-SD.mp4')+'"><source type="video/mp4"></video>'
   res_html += '  </a>'
   res_html += '  <div class="list-onl"><span>Cam #'+det['cam_id']+' - <b>'+det['hour']+':'+det['min']+'</b></span></div>'
   res_html += '  <div class="list-onl sel-box"><div class="custom-control big custom-checkbox">'
   res_html += '     <input type="checkbox" class="custom-control-input" id="'+det['full_path']+'" name="'+det['full_path']+'">'     
   res_html += '     <label class="custom-control-label" for="'+det['full_path']+'"></label>'
   res_html += '  </div></div>'
   res_html += '  <div class="d-flex justify-content-between">'
   res_html += '     <div class="pre-b gallery-only"><span class="mst">Cam #'+det['cam_id']+' - <b>'+det['hour']+':'+det['min']+'</b></span>'
   
   res_html += ' <dl class="row mb-0 def mt-1">'

   if(detection['mag']!='unknown'):
      res_html += '              <dt class="col-6">Mag</dt>             <dd class="col-6">' + str(detection['mag']) + '</dd>'
   
   if(detection['dur']!='unknown'):
      res_html += '              <dt class="col-6">Duration</dt>  	   <dd class="col-6">'+ str(detection['dur']) +'s</dd>'

   if(detection['res_er']!='unknown'):
      res_html += '              <dt class="col-6">Res. Error</dt>      <dd class="col-6">'+ str("{0:.4f}".format(float(detection['res_er'])))+'</dd>'
   
   if(detection['ang_v']!='unknown'):
      res_html += '              <dt class="col-6">Ang. Velocity</dt>   <dd class="col-6">'+str("{0:.4f}".format(float(detection['ang_v'])))+'&deg;/s</dd>'

   res_html += ' </dl>'
   
   res_html += '</div>'
   res_html += '     <div class="btn-toolbar pr-0 pb-0"><div class="btn-group"><a class="vid_link_gal col btn btn-primary btn-sm" title="Play Video" href="./video_player.html?video='+path_to_vid+'"><i class="icon-play"></i></a>'
   res_html += '     <a class="delete_meteor_archive_gallery col btn btn-danger btn-sm" title="Delete Detection" data-meteor="'+det['full_path']+'"><i class="icon-delete"></i></a></div></div>'
   res_html += '  </div></div>' 

   return res_html
 

# Get HTML version of each detection
def get_html_detections(res,clear_cache):

   res_html = ''
   cur_title = ''
   prev_date = None
   cur_counter = 0
   first = True
   
   for detection in res:

      # We add the missing info to detection['p']
      # so the name analyser will work
      det = name_analyser(detection['p'])
      cur_date = get_datetime_from_analysedname(det)
 
      if(prev_date is None): 
         print("BUILD FIRST TITLE "+cur_date.strftime("%Y/%m/%d")+"<br/>")
         prev_date = cur_date
         # FIRST TITLE
         cur_title  = '<div class="h2_holder d-flex justify-content-between"><h2>'+cur_date.strftime("%Y/%m/%d")+" - %TOTAL%</h2></div>"
         cur_title  += '<div class="gallery gal-resize row text-center text-lg-left mb-5 mr-5 ml-5">' 
      
      if(cur_date.month != prev_date.month or cur_date.day != prev_date.day or cur_date.year != prev_date.year):
         
         print("THE DATE CHANGE  "+cur_date.strftime("%Y/%m/%d")+"<br/>")

         if(first == True):
            print("THIS IS THE FIRST<br/>")
            res_html  = cur_title.replace('%TOTAL%',str(cur_counter) +  ' detections') + res_html
            first = False
         else:
            print("THIS IS NOT THE FIRST<br/>")
            res_html += cur_title.replace('%TOTAL%',str(cur_counter) +  ' detections')  
 
            prev_date   = cur_date 
            cur_counter = 0
            cur_title  =  '</div><div class="h2_holder d-flex justify-content-between"><h2>'+cur_date.strftime("%Y/%m/%d")+" -  %TOTAL%</h2></div>"
            cur_title  += '<div class="gallery gal-resize row text-center text-lg-left mb-5 mr-5 ml-5">'
      #else:
         

      print("WE ADD A DETECTION "+cur_date.strftime("%Y/%m/%d")+"<br/>")
      print("CT+1 "+cur_date.strftime("%Y/%m/%d")+"<br/>")
       
      res_html += get_html_detection(det,detection,clear_cache)
      cur_counter+=1     
     
   return res_html
 

 

# MAIN FUNCTION FOR THE ARCHIVE LISTING PAGE
def archive_listing(form): 

   limit_day = form.getvalue('limit_day')
   cur_page  = form.getvalue('p')
   meteor_per_page = form.getvalue('meteor_per_page')
   clear_cache = form.getvalue('clear_cache')

   # Criteria
   selected_mag = form.getvalue('magnitude')
   selected_error = form.getvalue('res_error')
   selected_ang_vel = form.getvalue('ang_vel')


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

   # LIST OF CRITERIA 
   criteria = {}

   # Build MAGNITUDES selector
   mag_select = ''
   one_mag_selected = False

   # Add Default choice
   if selected_mag is None:
       mag_select+= '<option selected value="-1">All Magnitudes</option>'
   else:
      one_mag_selected = True 
      mag_select+= '<option value="-1">All Magnitudes</option>'
      criteria['mag'] = float(selected_mag)

   for mag in POSSIBLE_MAGNITUDES:
      if(one_mag_selected==True):
         if(float(mag)==float(selected_mag)):
            mag_select+= '<option selected value="'+str(mag)+'">>'+str(mag)+'</option>'
         else:
            mag_select+= '<option value="'+str(mag)+'">>'+str(mag)+'</option>'  
      else:
         mag_select+= '<option value="'+str(mag)+'">>'+str(mag)+'</option>'  
   template = template.replace("{MAGNITUDES}", mag_select)

   # Build ERRORS selector
   error_select = ''
   one_error_selected = False

   # Add Default choice
   if selected_error is None:
       error_select+= '<option selected value="-1">All Res. Error</option>'
   else:
      one_error_selected = True 
      error_select+= '<option value="-1">All Res. Error</option>' 
      criteria['res_er'] = float(selected_error)


   
   for err in POSSIBLE_ERRORS:
      if(one_error_selected):
         if(float(err)==float(selected_error)):
            error_select+= '<option selected value="'+str(err)+'"><'+str(err)+'</option>'
         else:
            error_select+= '<option value="'+str(err)+'"><'+str(err)+'</option>'  
      else:
         error_select+= '<option value="'+str(err)+'"><'+str(err)+'</option>'  
   template = template.replace("{RES_ERRORS}", error_select)


   # Build ANGULAR VELOCITIES selector
   ang_vel_select = ''
   one_ang_vel_selected = False
 

   # Add Default choice
   if selected_ang_vel is None:
       ang_vel_select+= '<option selected value="-1">All Ang. Velocities</option>'
   else:
      one_ang_vel_selected = True 
      ang_vel_select+= '<option value="-1">All Ang. Velocities</option>' 
      criteria['ang_v'] = float(selected_ang_vel)

   for ang_vel in POSSIBLE_ANG_VELOCITIES:
      if(one_ang_vel_selected):
         if(float(selected_ang_vel)==float(ang_vel)):
            ang_vel_select+= '<option selected value="'+str(ang_vel)+'"><'+str(ang_vel)+'&deg;/s</option>'
         else:
            ang_vel_select+= '<option value="'+str(ang_vel)+'"><'+str(ang_vel)+'&deg;/s</option>'  
      else:
            ang_vel_select+= '<option value="'+str(ang_vel)+'"><'+str(ang_vel)+'&deg;/s</option>'  
   template = template.replace("{ANG_VELOCITIES}", ang_vel_select)



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
   month = the_date.month

   # Get the index of the selected or current year
   index =  get_monthly_index(month,year)
   
   # Search the index
   if(index is not False):

      res = get_results_from_date_from_monthly_index(criteria,the_date,index,int(nompp),cur_page)

      # If we don't have enough detection to display we try the previous year
      if(res):
         if(len(res)<NUMBER_OF_METEOR_PER_PAGE):
            the_date = datetime.datetime.strptime(str(year-1)+'_01_01',"%Y_%m_%d") 
            year = year -1
            index = get_index(year)

            if(index is not False):
               new_stop = int(meteor_per_page) - len(res)
               res2 = get_results_from_date_from_monthly_index(criteria,the_date,index,new_sto,cur_page)
               res = res + res2

         # CREATE URL FOR THE PAGINATION
         pagination_url  = "/pycgi/webUI.py?cmd=archive_listing&meteor_per_page="+str(nompp)

         if(has_limit_day!=0):
            pagination_url += "&limit_day="+str(the_date)
         
         for criter in criteria:
            pagination_url += "&"+criter+"="+str(criteria[criter])

         pagination = get_pagination(cur_page,len(res),pagination_url,int(nompp))

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