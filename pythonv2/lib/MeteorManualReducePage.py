import cgitb
import re
import os
import sys
import glob
import random
import json

from lib.FileIO import load_config, cfe, save_json_file
from lib.MeteorReducePage import print_error
from lib.MeteorReduce_Tools import *
from lib.MeteorReduce_Calib_Tools import XYtoRADec
from lib.REDUCE_VARS import *
from lib.VIDEO_VARS import *
from lib.CGI_Tools import redirect_to
from lib.Old_JSON_conveter import fix_old_file_name, get_new_calib, convert

MANUAL_RED_PAGE_TEMPLATE_STEP1 = "/home/ams/amscams/pythonv2/templates/manual_reduction_template_step1.html"
MANUAL_RED_PAGE_TEMPLATE_STEP2 = "/home/ams/amscams/pythonv2/templates/manual_reduction_template_step2.html"
MANUAL_RED_PAGE_TEMPLATE_STEP3 = "/home/ams/amscams/pythonv2/templates/manual_reduction_template_step3.html"
  
# First Step of the Manual reduction: select start / end meteor position
def manual_reduction(form):
   
   # Debug
   cgitb.enable()

   video_file = form.getvalue('video_file')

   # Build the page based on template  
   with open(MANUAL_RED_PAGE_TEMPLATE_STEP1, 'r') as file:
      template = file.read()

   # Here we have the possibility to "empty" the cache, ie regenerate the files (stacks) even if they already exists
   # we just need to add "clear_cache=1" to the URL
   if(form.getvalue("clear_cache") is not None):
      clear_cache = True
   else:
      clear_cache = False

   # Get Video File & Analyse the Name to get quick access to all info
   video_full_path = form.getvalue("video_file")

   if(video_full_path is not None):
      tmp_fixed_video_full_path = fix_old_file_name(video_full_path)
      analysed_name = name_analyser(tmp_fixed_video_full_path)

      # We keep the original full_path anyway
      analysed_name['full_path'] = video_full_path
   else:
      print_error("<b>You need to add a video file in the URL.</b>")



   # Get the stacks 
   # True = We automatically resize the stack to HD dims so we can use it in the UI
   stack = get_stacks(analysed_name,clear_cache, True)
   template = template.replace("{STACK}", str(stack))   
   
   # Add Video to template
   template = template.replace("{VIDEO}", str(video_file))

   # Display Template# Second Step of Manual Reduction: cropp of all frames + selection of start event
def manual_reduction_cropper(form):

   video_file  = form.getvalue('video_file')  
   x_start = float(form.getvalue('x_start'))
   y_start = float(form.getvalue('y_start'))
   w = float(form.getvalue('w'))
   h = float(form.getvalue('h'))

   # Fix eventual video file name (old version)
   tmp_fixed_video_full_path = fix_old_file_name(video_file)
   analysed_name = name_analyser(tmp_fixed_video_full_path)

   # We keep the original full_path anyway
   analysed_name['full_path'] = video_file

   # Create destination folder if necessary
   dest_folder = get_cache_path(analysed_name,'tmp_cropped')
   cache_path  = does_cache_exist(analysed_name,'tmp_cropped')

   # If we already tmp cropped frames, we need to delete them
   if(len(cache_path)!=0):
      for f in cache_path:
         os.remove(os.path.join(cache_path, f))
 
   # Extract all the frames, resize to HD and crop
   cmd = 'ffmpeg   -i ' + analysed_name['full_path'] +  ' -filter_complex "[0:v]scale=' + str(HD_W) + ":" + str(HD_H) + '[scale];[scale]crop='+str(w)+':'+str(h)+':'+str(x_start)+':'+str(y_start)+'[out]"  -map "[out]" ' + dest_folder + '/%04d' + '.png' 
   output = subprocess.check_output(cmd, shell=True).decode("utf-8")  
   
   # Get all the newly created cropped frames
   thumbs = sorted(glob.glob(dest_folder+'/*.png'))

   # Build the page based on template  
   with open(MANUAL_RED_PAGE_TEMPLATE_STEP2, 'r') as file:
      template = file.read()

   # Add Data to template
   template = template.replace("{VIDEO}", str(video_file))
   template = template.replace("{X}", str(x_start))   
   template = template.replace("{Y}", str(y_start))  
   template = template.replace("{W}", str(w))   
   template = template.replace("{H}", str(h))       
 
   # Add Thumbs to template
   thumbs_to_display = ''
   for i,img in enumerate(thumbs):
      x = i + 1
      thumbs_to_display +=  "<a class='frame_selector' data-rel='"+str(x)+"'><span>#"+str(x)+"</span><img src='"+img+"?c='"+str(random.randint(1,1000001))+"'/></a>"

   template = template.replace("{CROPPED_THUMBS_GALLERY}",  thumbs_to_display)      

   # Display Template
   print(template)
   print(template)





# Third step of Manual Reduction: manual selection of the meteor position
def manual_reduction_meteor_pos_selector(form):

   video_file  = form.getvalue('video_file')  
   x_start = float(form.getvalue('x'))
   y_start = float(form.getvalue('y'))
   w = float(form.getvalue('w'))
   h = float(form.getvalue('h'))
   f = float(form.getvalue('f'))   # Number of the first frame

   # Build the page based on template  
   with open(MANUAL_RED_PAGE_TEMPLATE_STEP3, 'r') as file:
      template = file.read()

    # Fix eventual video file name (old version)
   tmp_fixed_video_full_path = fix_old_file_name(video_file)
   analysed_name = name_analyser(tmp_fixed_video_full_path)

   # We keep the original full_path anyway
   analysed_name['full_path'] = video_file

   # Get the cropped frames
   cropped_frames  = does_cache_exist(analysed_name,'tmp_cropped')

   real_cropped_frames = []
   real_cropped_frames_str = ""
 
   # We remove all the frames from cropped_frames that are before f
   # and create the HTML view for the top panel
   for i,cropped_frame in enumerate(cropped_frames):
      x = i + 1
      if(x>=int(f)):
         real_cropped_frames.append(cropped_frame)
         real_cropped_frames_str += "<a class='select_frame select_frame_btn' data-rel='"+str(x)+"'><span>#"+str(x)+"<i class='pos'></i></span><img src='"+cropped_frame+"?c="+str(random.randint(1,1000001))+"'/></a>"

   
   # Add the thumbs to navigator
   template = template.replace("{CROPPED_FRAMES_SELECTOR}",  real_cropped_frames_str)     
   
   # Add info to template
   template = template.replace("{X}", str(x_start))    
   template = template.replace("{Y}", str(y_start))   
   template = template.replace("{W}", str(w))    
   template = template.replace("{H}", str(h))  
   template = template.replace("{VIDEO}", str(video_file)) 
   
   # Display Template
   print(template)


# Fourth Step : creation of the new JSON
def manual_reduction_create_final_json(form):
   video_file   = form.getvalue('video_file')  
   frames_info  = form.getvalue('frames')  

   # We parse the frames_info
   frames_info = json.loads(frames_info)

   # First we test if it's an old file
   if METEOR_ARCHIVE not in video_file: 
      # It is an old file
      # so we need to create the new json 
      # and move the json and the video file under /meteor_archive
      json_file, video_file = move_old_to_archive(json_file_path)

   
 

   