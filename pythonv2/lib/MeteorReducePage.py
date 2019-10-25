import cgitb

from lib.MeteorReduce_Tools import * 
from lib.MeteorReduce_Calib_Tools import find_matching_cal_files, find_calib_file
 
PAGE_TEMPLATE = "/home/ams/amscams/pythonv2/templates/reducePage.v2.html"




# GENERATES THE REDUCE PAGE METEOR
# from a URL 
# cmd=reduce2
# &video_file=[PATH]/[VIDEO_FILE].mp4
def reduce_meteor2(json_conf,form):
   
   # Debug
   cgitb.enable()

   HD = True

   # Build the page based on template  
   with open(PAGE_TEMPLATE, 'r') as file:
      template = file.read()

   # Here we have the possibility to "empty" the cache, ie regenerate the files even if they already exists
   # we just need to add "clear_cache=1" to the URL
   if(form.getvalue("clear_cache") is not None):
      clear_cache = True
   else:
      clear_cache = False
 
   # Get Video File & Analyse the Name to get quick access to all info
   video_full_path = form.getvalue("video_file")

   # We need at least one video file
   if(video_full_path is not None):
      analysed_name = name_analyser(video_full_path)
   else:
      print_error("<b>You need to add a video file in the URL.</b>")

   # We get the proper json and the other video file
   if('HD' in video_full_path):
      video_hd_full_path = video_full_path
      video_sd_full_path = video_full_path.replace('-HD','-SD')
      json_full_path = video_full_path.replace('-HD.mp4','.json')
   else:
      video_sd_full_path = video_full_path 
      video_hd_full_path = video_full_path.replace('-SD','-HD')
      json_full_path = video_full_path.replace('-SD.mp4','.json')  
   
   if(cfe(video_hd_full_path)==0):
      video_hd_full_path = ''
      HD = False 
   
   if(cfe(video_sd_full_path)==0):
       print_error(video_sd_full_path + " <b>not found.</b><br/>At least one SD video is required.")

   if(cfe(json_full_path)==0):
       print_error(json_full_path + " <b>not found.</b><br>This detection may had not been reduced yet or the reduction failed.")

   # Test if the name is ok
   if(len(analysed_name)==0):
      print_error(video_full_path + " <b>is not valid video file name.</b>") 
  
   # Add the JSON Path to the template
   template = template.replace("{JSON_FILE}", str(json_full_path))   # Video File  

   # Parse the JSON
   meteor_json_file = load_json_file(json_full_path) 

   # Get the HD frames
   HD_frames = get_HD_frames(analysed_name,clear_cache)
   
   # Get the HD or SD stack
   tmp_analysed_name = name_analyser(json_full_path) 
   if(video_hd_full_path != ''):
      hd_stack = get_stacks(tmp_analysed_name,clear_cache,True)
   
   stack = get_stacks(tmp_analysed_name,clear_cache,False) 
   
    
   # Get the thumbs (cropped HD frames) 
   thumbs = get_thumbs(tmp_analysed_name,meteor_json_file,HD,HD_frames,clear_cache)
  
   # Fill Template with data
   template = template.replace("{VIDEO_FILE}", str(video_full_path))   # Video File  
   template = template.replace("{STACK}", str(stack))                  # Stack File 
   if(hd_stack is not None):
      template = template.replace("{HD_STACK}", str(hd_stack))                  # HD Stack File 
 
   template = template.replace("{EVENT_DURATION}", str(meteor_json_file['info']['dur']))          # Duration
   template = template.replace("{EVENT_MAGNITUDE}", str(meteor_json_file['info']['max_peak']))    # Peak_magnitude

   # For the Event start time
   # either it has already been reduced and we take the time of the first frame
   start_time = 0
   if('frames' in meteor_json_file):
      if(len(meteor_json_file['frames'])>0):
         start_time = str(meteor_json_file['frames'][0]['dt'])
        
   # either we take the time of the file name
   if(start_time==0):
      start_time = analysed_name['year']+'-'+analysed_name['month']+'-'+analysed_name['day']+ ' '+ analysed_name['hour']+':'+analysed_name['min']+':'+analysed_name['sec']+'.'+analysed_name['ms']
   
   # We complete the template
   template = template.replace("{EVENT_START_TIME}", start_time)

  
   # Note: the rest of the data are managed through JAVASCRIPT

   # Find Possible Calibration Parameters
   # Based on Date & Time of the first frame
   #calibration_files = find_matching_cal_files(analysed_name['cam_id'], datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S.%f'))

   # Find the one that is currently used based on meteor_json_file[calib][dt]
   # calib_dt = meteor_json_file['calib']['dt']
   #find_calib_json = find_calib_file(calib_dt,analysed_name['cam_id'])
  
   # Build a human readable date & time
   #calib_dt_h = calib_dt.replace("_", "/", 2).replace("_", " ", 1).replace("_",":")[:-4] # Ugly but not sure we can do something else
   #template = template.replace("{SELECTED_CAL_PARAMS_FILE_NAME}", calib_dt_h)     
   #template = template.replace("{SELECTED_CAL_PARAMS_FILE}", str(find_calib_json))      

   #print(str(calibration_files))

   #template =  get_stars_table(template,"{STAR_TABLE}",meteor_json_file,"{STAR_COUNT}")   # Stars table
   #template =  get_reduction_table(analysed_name,template,"{RED_TABLE}",meteor_json_file,'{FRAME_COUNT}') # Reduction Table

   #print(get_stars_table(meteor_json_file))

   # Display Template
   print(template)
