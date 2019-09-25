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

MANUAL_RED_PAGE_TEMPLATE_STEP1 = "/home/ams/amscams/pythonv2/templates/manual_reduction_template_step1.html"
MANUAL_RED_PAGE_TEMPLATE_STEP2 = "/home/ams/amscams/pythonv2/templates/manual_reduction_template_step2.html"
MANUAL_RED_PAGE_TEMPLATE_STEP3 = "/home/ams/amscams/pythonv2/templates/manual_reduction_template_step3.html"

# Fix the old files names that contains "-trim"
def fix_old_file_name(filename):
   # We need to get the current stations ID (in as6.json)
   json_conf = load_json_file(JSON_CONFIG)
   station_id = json_conf['site']['ams_id']
   if("-reduced" in filename):
      filename = filename.replace("-reduced", "")

   if("trim" in filename):
      tmp_video_full_path_matches =  re.finditer(OLD_FILE_NAME_REGEX, filename, re.MULTILINE)
      tmp_fixed_video_full_path = ""
      for matchNum, match in enumerate(tmp_video_full_path_matches, start=1):
         for groupNum in range(0, len(match.groups())): 
            if("-" not in match.group(groupNum)):
               tmp_fixed_video_full_path = tmp_fixed_video_full_path + "_" + match.group(groupNum)
            groupNum = groupNum + 1

         # Remove first "_"
         tmp_fixed_video_full_path = tmp_fixed_video_full_path[1:]
         # Add an extension
         tmp_fixed_video_full_path += "_" + station_id
         
         if("HD" in filename):
            tmp_fixed_video_full_path +=  "_HD.json"
         else:
            tmp_fixed_video_full_path +=  "_SD.json"
         return tmp_fixed_video_full_path
   else:
      return filename


# Get cal_params new version from an old JSON version 
def get_new_calib(json_f):
   # If 'device_alt' isn't defined, we have to work with 'site_alt'...
   if "device_alt" not in json_f['cal_params']:
      json_f['cal_params']['device_alt'] = float(json_f['cal_params']['site_alt'])
      json_f['cal_params']['device_lat'] = float(json_f['cal_params']['site_lat'])  
      json_f['cal_params']['device_lng'] = float(json_f['cal_params']['site_lng'])  
 
   return { "calib":  
      { "device": {
         "alt":  float(json_f['cal_params']['device_alt']),
         "lat":  float(json_f['cal_params']['device_lat']),
         "lng":  float(json_f['cal_params']['device_lng']),
         "scale_px":  float(json_f['cal_params']['pixscale']),
         "poly": {
               "y_fwd": json_f['cal_params']['y_poly_fwd'],
               "x_fwd": json_f['cal_params']['x_poly_fwd']
         },
         "center": {
               "az": float(json_f['cal_params']['center_az']),  
               "ra": float(json_f['cal_params']['ra_center']), 
               "el": float(json_f['cal_params']['center_el']),
               "dec": float(json_f['cal_params']['dec_center']) 
         },
         "angle":  float(json_f['cal_params']['position_angle'])
      }      
   }}


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

   # Display Template
   print(template)


# Second Step of Manual Reduction: cropp of all frames + selection of start event
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

   # Is it an old or a new detection?
   if "meteor_archive" in video_file: 

      # IT'S A NEW ONE!

      # Get JSON
      meteor_red_file = video_file.replace('.mp4','.json')
      analysed_name = name_analyser(meteor_red_file)

      if cfe(meteor_red_file) == 1:

         # We parse the JSON
         mr = load_json_file(meteor_red_file)
         
         # We remove all the current frames
         mr['frames'] = []

         # We create the ones
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

            # We update the JSON with the new frames
            save_json_file(json_file, mr) 
     


      else: 
         print_error("<b>JSON File not found: " + meteor_red_file + "</b>")
 
         



   else:
      # It's an old detection, we're going to move the video file
      # And create a new json file
      print("IT'S AN OLD DETECTION - I CANNOT DEAL WITH IT FOR NOW")
      sys.exit(0)

      # First, we need to get the old reduction file path
      #old_json_file = video_file.replace('.mp4','-reduced.json')
      #if(cfe(old_json_file)==1):
      #   print(old_json_file  +  " exists")
      #else:
      #   print(old_json_file  +  " doesn't exist")


   # Fix eventual video file name (old version)
   tmp_fixed_video_full_path = fix_old_file_name(video_file)
   analysed_name = name_analyser(tmp_fixed_video_full_path)

   print('FIXED NAME')
   print(tmp_fixed_video_full_path)

   