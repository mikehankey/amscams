import cgitb
import os
import sys
import json
import random

from lib.FileIO import load_json_file, save_json_file
from lib.MeteorReducePage import print_error 
from lib.MeteorReduce_Tools import get_stacks, get_cache_path, does_cache_exist, name_analyser, generate_SD_and_HD_frames_for_sync
from lib.CGI_Tools import redirect_to
from lib.VIDEO_VARS import *


MANUAL_SYNC_TEMPLATE_STEP1 = "/home/ams/amscams/pythonv2/templates/manual_sync_template_step0.html"
MANUAL_SYNC_TEMPLATE_STEP2 = "/home/ams/amscams/pythonv2/templates/manual_sync_template_step1.html"

# Last step of the manual sync: we update the json
def update_sync(form):
   json_file   = form.getvalue('json')
   sd = form.getvalue('sd') 
   hd = form.getvalue('hd')  

   # We parse the JSON
   mr = load_json_file(json_file)

   # It's a creation
   if('sync' not in mr): 
      mr['sync'] = {}
   
   mr['sync']['hd_ind'] = int(hd)
   mr['sync']['sd_ind'] = int(sd)

   save_json_file(json_file,mr)

   # We redirect to the reduce page with clearing cache
   redirect_to("/pycgi/webUI.py?cmd=reduce2&video_file=" + json_file + "&clear_cache=1&c=" + str(random.randint(0,100000000)), "reduction")
 

# Second  of the manual sync
def manual_synchronization_chooser(form):

   # Debug
   # cgitb.enable()

   video_file  = form.getvalue('video_file')  
   stack_file  = form.getvalue('stack_file')  
   type_file   = form.getvalue('type')  
   x_start     = float(form.getvalue('x_start'))
   y_start     = float(form.getvalue('y_start'))
   w           = float(form.getvalue('w'))
   h           = float(form.getvalue('h'))
   json_file   = form.getvalue('json')

   # Get Analysed name  
   analysed_name = name_analyser(video_file)

   # Create destination folder for the HD if necessary
   dest_folder = get_cache_path(analysed_name,'tmp_cropped_sync')
   cache_path  = does_cache_exist(analysed_name,'tmp_cropped_sync')

   # Create destination folder for the HD if necessary
   dest_hd_folder = get_cache_path(analysed_name,'tmp_hd_cropped_sync')
   cache_hd_path  = does_cache_exist(analysed_name,'tmp_hd_cropped_sync')
   dest_sd_folder = get_cache_path(analysed_name,'tmp_sd_cropped_sync')
   cache_sd_path  = does_cache_exist(analysed_name,'tmp_sd_cropped_sync')

   # Parse the JSON file
   mr = load_json_file(json_file) 

   # How many SD frames do we create?
   how_many_sd_frames = 4 
   
   starting_from = 0
   # What is the fn of the first frame?
   if 'frames' in mr :
      if len(mr['frames']) > 0 :
         if 'fn' in mr['frames'][0]:
            starting_from = mr['frames'][0]['fn']
   
  
   # Create the SD
   all_resized_sd, all_resized_hd = generate_SD_and_HD_frames_for_sync(analysed_name,dest_sd_folder,x_start,y_start,w,h)
   
   # Build the page based on template  
   with open(MANUAL_SYNC_TEMPLATE_STEP2, 'r') as file:
      template = file.read()
  
   # Create list of SD Cropped Frames for template
   sd_frame_html = ''
   for i,frame  in enumerate(sorted(all_resized_sd)):
      x = i+1
      sd_frame_html+=  '<a class="select_frame select_frame_btn" data-rel="'+str(x)+'"><span>SD#'+str(x)+'<i class="pos"></i></span><img src="'+frame+'?c='+str(random.randint(1,1000001))+'"/></a>'
 
   # We add ithe SD Frames to the template
   template = template.replace("{SD_CROPPED_FRAMES_SELECTOR}", sd_frame_html)  

   # Create list of SD Cropped Frames for template
   hd_frame_html = ''
   for i,frame  in enumerate(sorted(all_resized_hd)):
      x = i+1
      hd_frame_html+=  '<a class="select_frame select_frame_btn" data-rel="'+str(x)+'"><span>HD#'+str(x)+'<i class="pos"></i></span><img src="'+frame+'?c='+str(random.randint(1,1000001))+'"/></a>'
 
   # We add ithe SD Frames to the template
   template = template.replace("{HD_CROPPED_FRAMES_SELECTOR}", hd_frame_html)  
   
   # We add the JSON file to the template too
   template = template.replace("{JSON}", json_file)  
   

   print(template)  


# First step of the manual synchronization
def manual_synchronization(form):

   # Debug
   cgitb.enable()

   stack_file = form.getvalue('stack')
   video_file = form.getvalue('video')
   type_file  = form.getvalue('type')    # HD or SD
   json_file  = form.getvalue('json') 

   # Build the page based on template  
   with open(MANUAL_SYNC_TEMPLATE_STEP1, 'r') as file:
      template = file.read()
 
    # Video File
   if(video_file is None):
      print_error("<b>You need to add a video file in the URL.</b>")
       
   analysed_name = name_analyser(json_file)
   
   # No matter if the stack is SD or not
   # we resize it to HD
   stack = get_stacks(analysed_name,True, True)

   # We add it to the template
   template = template.replace("{STACK}", str(stack))  
  
   # Add Video to template
   template = template.replace("{VIDEO}", str(video_file))

   # Add Initial type to template
   template = template.replace("{TYPE}", str(type_file))

   # Add json
   template = template.replace("{JSON}",str(json_file))

   print(template)  