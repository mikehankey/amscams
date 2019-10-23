import cgitb
import re
import os
import sys
import glob
import random
import json

from datetime import datetime,timedelta

from lib.FileIO import load_config, cfe, save_json_file
from lib.MeteorReducePage import print_error
from lib.MeteorReduce_Tools import *
from lib.MeteorReduce_Calib_Tools import XYtoRADec
from lib.REDUCE_VARS import *
from lib.VIDEO_VARS import *
from lib.CGI_Tools import redirect_to
from lib.Old_JSON_converter import fix_old_file_name, get_new_calib, convert, move_old_detection_to_archive, old_name_analyser

MANUAL_RED_PAGE_TEMPLATE_STEP0 = "/home/ams/amscams/pythonv2/templates/manual_reduction_template_step0.html"
MANUAL_RED_PAGE_TEMPLATE_STEP1 = "/home/ams/amscams/pythonv2/templates/manual_reduction_template_step1.html"
MANUAL_RED_PAGE_TEMPLATE_STEP2 = "/home/ams/amscams/pythonv2/templates/manual_reduction_template_step2.html"
MANUAL_RED_PAGE_TEMPLATE_STEP3 = "/home/ams/amscams/pythonv2/templates/manual_reduction_template_step3.html"
  
# (new) First step of Manual Reduction: select proper stack (HD | SD)
def manual_reduction(form):
   
   # Debug
   cgitb.enable()

   error = False

    # Get both video
   sd_video = form.getvalue('sd_video')
   hd_video = form.getvalue('video_file')

   # Get both stacks
   sd_stack = form.getvalue('sd_stack')
   hd_stack = form.getvalue('hd_stack')

   # Get JSON
   json_file = form.getvalue('json_file')

   # Test if they really exist
   if(cfe(sd_stack)==0):
      sd_stack = ''
   if(cfe(hd_stack)==0):
      hd_stack = '' 

   if(sd_stack == '' and hd_stack == ''):
      print_error("<b>Stacks not found.</b>")
      error = True

   # Build the page based on template  
   with open(MANUAL_RED_PAGE_TEMPLATE_STEP0, 'r') as file:
      template = file.read()

   if(error is False):
      # We display both stacks and ask the user to select which one he wants to use
      # Add sd_stack to template
      if(sd_stack is not ''):
         template = template.replace("{SD_STACK}", str(sd_stack))
      else:
         # We automatically select the HD
         # TODO!!!
         print("NO SD")

      if(hd_stack is not ''):
         template = template.replace("{HD_STACK}", str(hd_stack))
      else: 
         # We automatically select the SD
         # TODO!!!
         print("NO HD")

      # We add the videos to the  page
      template = template.replace("{HD_VIDEO}", str(hd_video))
      template = template.replace("{SD_VIDEO}", str(sd_video))

      template = template.replace("{JSON_FILE}", str(json_file))

   # Display Template
   print(template) 


# First Step of the Manual reduction: select start / end meteor position
def manual_reduction_step1(form):
    
   # Debug
   cgitb.enable()

   stack_file = form.getvalue('stack')
   video_file = form.getvalue('video')
   type_file  = form.getvalue('type')    # HD or SD
   json_file  = form.getvalue('json')


   # Build the page based on template  
   with open(MANUAL_RED_PAGE_TEMPLATE_STEP1, 'r') as file:
      template = file.read()

   # Here we have the possibility to "empty" the cache, ie regenerate the files (stacks) even if they already exists
   # we just need to add "clear_cache=1" to the URL
   if(form.getvalue("clear_cache") is not None):
      clear_cache = True
   else:
      clear_cache = False
 

   # Video File
   if(video_file is not None):
      tmp_fixed_video_full_path = fix_old_file_name(video_file)
      analysed_name = name_analyser(tmp_fixed_video_full_path)
      # We keep the original full_path anyway
      analysed_name['full_path'] = video_file
   else:
      print_error("<b>You need to add a video file in the URL.</b>")
   
   # No matter if the stack is SD or not
   # we resize it to HD
   stack = get_stacks(analysed_name,clear_cache, True)
   # We add it to the template
   template = template.replace("{STACK}", str(stack))  

   # Add Video to template
   template = template.replace("{VIDEO}", str(video_file))

   # Add Initial type to template
   template = template.replace("{TYPE}", str(type_file))

   # Add json
   template = template.replace("{JSON}",str(json_file))

   print(template)  



# Display Template# Second Step of Manual Reduction: cropp of all frames + selection of start event
def manual_reduction_cropper(form):

   video_file  = form.getvalue('video_file')  
   stack_file  = form.getvalue('stack_file')  
   type_file   = form.getvalue('type')  
   x_start     = float(form.getvalue('x_start'))
   y_start     = float(form.getvalue('y_start'))
   w           = float(form.getvalue('w'))
   h           = float(form.getvalue('h'))
   json_file   = form.getvalue('json')

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
   template = template.replace("{JSON}",str(json_file))
 
   # Add Thumbs to template
   thumbs_to_display = ''
   for i,img in enumerate(thumbs):
      x = i + 1
      thumbs_to_display +=  "<a class='frame_selector lz' data-rel='"+str(x)+"'><span>#"+str(x)+"</span><img src='"+img+"?c='"+str(random.randint(1,1000001))+"'/></a>"

   template = template.replace("{CROPPED_THUMBS_GALLERY}",  thumbs_to_display)      

   # Display Template
   print(template) 





# Third step of Manual Reduction: manual selection of the meteor position
def manual_reduction_meteor_pos_selector(form):

   video_file  = form.getvalue('video_file')  
   x_start = float(form.getvalue('x'))
   y_start = float(form.getvalue('y'))
   w = float(form.getvalue('w'))
   h = float(form.getvalue('h'))
   f = float(form.getvalue('f'))   # Number of the first frame
   json_file   = form.getvalue('json')

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
   template = template.replace("{JSON}", str(json_file)) 

   # Display Template
   print(template)


# Fourth Step : update of the JSON (THIS IS FOR THE OLD approach)
def manual_reduction_create_final_json2(form):
   video_file   = form.getvalue('video_file')  
   frames_info  = form.getvalue('frames')  

   # We parse the frames_info
   frames_info = json.loads(frames_info)

   print("HERE ARE THE FRAMES INFO TO ADD:<br/>")
   print(json.dumps(frames_info))
   sys.exit(0)



# Fourth Step : creation of the new JSON (THIS IS FOR THE /meteor_archive/ approach)
def manual_reduction_create_final_json(form):
   video_file   = form.getvalue('video_file')  
   frames_info  = form.getvalue('frames')  
   json_file    = form.getvalue('json')
  
   # We parse the frames_info
   frames_info = json.loads(frames_info)

   # Get JSON
   meteor_red_file = json_file
   analysed_name = name_analyser(meteor_red_file)

   if cfe(meteor_red_file) == 1:

      # We parse the JSON
      mr = load_json_file(meteor_red_file)
         
      # We remove all the current frames if they exist
      if('frames' in mr):
         del mr['frames']
         
      mr['frames'] = []
 
      # We get the dt of frame #0
      # based on the name of the file 
      # (with trim!!) 
      print("VIDEO FILE:<br/>")
      print(video_file)
      name_analysed = name_analyser(video_file)

      print("ANALYSED NAME:<br/>")
      print(name_analysed)
      sys.exit(0)
    
      # We create the new frames
      for frame in frames_info:
 
         # Get the Frame time (as a string)
         dt = get_frame_time(mr,frame['fn'],analysed_name)

          
 
         # Get the new RA/Dec 
         new_x, new_y, RA, Dec, az, el =  XYtoRADec(int(frame['x']),int(frame['y']),analysed_name,mr)
 
         # We need to create the new entry
         new_frame = {
            'dt': dt,
            'x': int(frame['x']),
            'y': int(frame['y']),
            'fn': int(frame['fn']),
            'az': az,
            'el': el,
            'ra': RA,
            'dec': Dec,
            'intensity': Intensity_DEFAULT,
            'max_px': Maxpx_DEFAULT,
            'w': W_DEFAULT, 
            'h': H_DEFAULT
         }
      
         mr['frames'].append(new_frame)


      # We need to update the total duration of the event 
      # based on the diff between the time of the last frame and the time of the first frame
      dt_start = datetime.strptime(mr['frames'][0]['dt'], "%Y-%m-%d %H:%M:%S.%f")
      dt_end   = datetime.strptime(mr['frames'][len(mr['frames'])-1]['dt'] , "%Y-%m-%d %H:%M:%S.%f")
      mr['info']['dur'] = timedelta.total_seconds( dt_end - dt_start )  

      # We update the JSON with the new frames
      save_json_file(meteor_red_file, mr) 
 
      redirect_to("/pycgi/webUI.py?cmd=reduce2&video_file=" + video_file + "&clear_cache=1&c=" + str(random.randint(0,100000000)), "reduction")
 
   else: 
      print_error("<b>JSON File not found: " + meteor_red_file + "</b>")
  
 
 

   