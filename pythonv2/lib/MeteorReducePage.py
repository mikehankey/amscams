import cgitb

from lib.MeteorReduce_Tools import * 
from lib.MeteorReduce_Calib_Tools import find_matching_cal_files, find_calib_file
 
PAGE_TEMPLATE = "/home/ams/amscams/pythonv2/templates/reducePage.v2.html"
 

# GENERATES THE REDUCE PAGE METEOR
# from a URL 
# cmd=reduce2
# &video_file=[PATH]/[VIDEO_FILE].mp4 or JSON File
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
   # Warning we can also pass the JSON file
   video_full_path = form.getvalue("video_file")

   if('.json' in video_full_path):
      json_full_path = video_full_path
      video_hd_full_path = video_full_path.replace('.json','-HD.mp4')
      video_full_path = video_hd_full_path
      video_sd_full_path = video_hd_full_path.replace('-HD','-SD')


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
 
   # Get the HD or SD stack
   tmp_analysed_name = name_analyser(json_full_path) 
   if(video_hd_full_path != ''):
      hd_stack = get_stacks(tmp_analysed_name,clear_cache,True)
   
   stack = get_stacks(tmp_analysed_name,clear_cache,False) 
   
   # Get the HD frames 
   HD_frames = get_HD_frames(tmp_analysed_name,clear_cache)
    
   # Get the thumbs (cropped HD frames) 
   try:
      HD_frames
   except NameError:
      # HD FRAMES NOT DEFINED
      print("")
   else:
      thumbs = get_thumbs(tmp_analysed_name,meteor_json_file,HD,HD_frames,clear_cache)
  
   # Fill Template with data
   template = template.replace("{VIDEO_FILE}", str(video_full_path))   # Video File  
   template = template.replace("{SD_VIDEO}",str(video_sd_full_path))   # SD Video File
   template = template.replace("{STACK}", str(stack))                  # Stack File 
   if(hd_stack is not None):
      template = template.replace("{HD_STACK}", str(hd_stack))                  # HD Stack File 
   
  


   # For the Event start time
   # either it has already been reduced and we take the time of the first frame
   start_time = 0
   if('frames' in meteor_json_file):
      if(len(meteor_json_file['frames'])>0):
         start_time = str(meteor_json_file['frames'][0]['dt'])
        
   # either we take the time of the file name
   if(start_time==0):
      start_time = analysed_name['year']+'-'+analysed_name['month']+'-'+analysed_name['day']+ ' '+ analysed_name['hour']+':'+analysed_name['min']+':'+analysed_name['sec']+'.'+analysed_name['ms']
   


   if('report' in meteor_json_file):
      report_details  =  ''
      report_details += '<dt class="col-6">Date &amp; Time</dt><dd class="col-6">'+start_time+'s</dd>'

      if('dur' in meteor_json_file['report']):
         report_details += '<dt class="col-6">Duration</dt><dd class="col-6">'+str(meteor_json_file['report']['dur'])+'s</dd>'
      if('max_peak' in meteor_json_file['report']):
         report_details += '<dt class="col-6">Magnitude</dt><dd class="col-6">'+str(meteor_json_file['report']['max_peak'])+'</dd>'
      if('angular_vel' in meteor_json_file['report']):
         report_details += '<dt class="col-6">Ang. Velocity</dt><dd class="col-6">'+str(meteor_json_file['report']['angular_vel'])+'&deg;/sec</dd>'

   if('calib' in meteor_json_file):
      if('device' in meteor_json_file['calib']):
         if('total_res_px' in meteor_json_file['calib']['device']):
            report_details += '<dt class="col-6">Res. Error</dt><dd class="col-6">'+str(meteor_json_file['calib']['device']['total_res_px'])+'</dd>'

 



   # We complete the template
   template = template.replace("{REPORT_DETAILS}", report_details)

   # Display some of the report info directly on the page
   #dist_per_elp: 9.661147849907783,
   #meteor_yn: "Y",
   #elp: 14,
   #y_dir_mod: -1,
   #min_max_dist: 144.91721774861674,
   #angular_sep: 6.0865231454419035,
   #moving: "moving",
   #bad_items: [],
   #max_cm: 14,
   #obj_class: "meteor",
   #dur: 0.56,
   #angular_vel: 10.144205242403173,
   #max_fns: 14,
   #x_dir_mod: 1,
   #max_peak: 7707

   # Display Template
   print(template)
