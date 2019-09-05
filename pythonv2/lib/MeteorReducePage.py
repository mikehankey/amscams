import re
import cgitb
import sys
import os.path
import cv2
import glob
import numpy as np
import subprocess 
import datetime

from pathlib import Path 
from PIL import Image
from lib.VideoLib import load_video_frames
from lib.FileIO import load_json_file 
from lib.ReducerLib import stack_frames
from lib.VIDEO_VARS import * 
from lib.ImageLib import stack_stack

# CURRENT CONFIG
JSON_CONFIG = "/home/ams/amscams/conf/as6.json"

# PATH WHERE ALL THE FILES GO 
MAIN_FILE_PATH = "/mnt/ams2/"
CACHE_PATH = MAIN_FILE_PATH + "CACHE/"

# Cache subfolders
FRAMES_SUBPATH= "/FRAMES/"          # For the HD Frames
CROPPED_FRAMES_SUBPATH = "/THUMBS/" # For the Cropped Frames (thumbs)
STACKS_SUBPATH   = "/STACKS/"       # For the Stacks

# PATTERN FOR THE FILE NAMES
# YYYY_MM_DD_HH_MM_SS_MSS_CAM_STATION[_HD].EXT
FILE_NAMES_REGEX = r"(\d{4})_(\d{2})_(\d{2})_(\d{2})_(\d{2})_(\d{2})_(\d{3})_(\w{6})_([^_^.]+)(_HD)?(\.)?(\.[0-9a-z]+$)"
FILE_NAMES_REGEX_GROUP = ["name","year","month","day","hour","min","sec","ms","cam_id","station_id","HD","ext"]

# EXTENSION FOR THE FRAMES
EXT_HD_FRAMES = "_HDfr"
EXT_CROPPED_FRAMES = "_frm"

# THUMBS (CROPPED FRAMES)
THUMB_W = 50
THUMB_H = 50
 
# SIZE OF THE SELECT BOX WHEN THE USER SELECTS THE METEOR FROM A HD FRAME
THUMB_SELECT_W = 50
THUMB_SELECT_H = 50

 
# Parses a regexp (FILE_NAMES_REGEX) a file name
# and returns all the info defined in FILE_NAMES_REGEX_GROUP
def name_analyser(file_names):
   matches = re.finditer(FILE_NAMES_REGEX, file_names, re.MULTILINE)
   res = {}
  
   for matchNum, match in enumerate(matches, start=1):
      for groupNum in range(0, len(match.groups())):
         if(match.group(groupNum) is not None):
            res[FILE_NAMES_REGEX_GROUP[groupNum]] = match.group(groupNum)
         groupNum = groupNum + 1

   # Get Name without extension if possible
   if(res is not None and "name" in res):
      res['name_w_ext'] = res['name'].split('.')[0]

   return res



# Return Cache folder name based on an analysed_file (parsed video file name)
# and cache_type = stacks | frames | cropped
def get_cache_path(analysed_file_name, cache_type):
    # Build the path to the proper cache folder
   cache_path = CACHE_PATH + analysed_file_name['station_id'] +  "/" + analysed_file_name['year'] + "/" + analysed_file_name['month'] + "/" + analysed_file_name['day'] + "/" + os.path.splitext(analysed_file_name['name'])[0]

   if(cache_type == "frames"):
      cache_path += FRAMES_SUBPATH
   elif(cache_type == "stacks"):
      cache_path += STACKS_SUBPATH
   elif(cache_type == "cropped"):
      cache_path += CROPPED_FRAMES_SUBPATH
   
   return cache_path


# Get the path to the cache of a given detection 
# create the folder if it doesn't exists 
def does_cache_exist(analysed_file_name,cache_type):

   # Debug
   cgitb.enable()

   # Get Cache Path
   cache_path = get_cache_path(analysed_file_name,cache_type)

   if(os.path.isdir(cache_path)):
      # We return the glob of the folder with all the images
      # print(cache_path + " exist")
      return glob.glob(cache_path+"*.png")
   else:
      # We Create the Folder and return null
      os.makedirs(cache_path)
      # print(cache_path + " created")
      return []



# Get the thumbs (cropped frames) for a meteor detection
# Generate them if necessary
def get_thumbs(video_full_path,analysed_name,meteor_json_file,HD,HD_frames,clear_cache):

   print('IN GET THUMBS<br>')

   # Do we have them already?
   thumbs = does_cache_exist(analysed_name,"cropped")

   if(len(thumbs)==0 or clear_cache is True):
      print("NO THUMB FOUND - WE NEED TO GENERATE THEM<br>")
      # We need to generate the thumbs 
      thumbs = generate_cropped_frames(video_full_path,analysed_name,meteor_json_file,HD_frames,HD)
   else:
      print("WE GOT THUMBS<br>")
      # We return them
      thumbs = glob.glob(get_cache_path(analysed_name,"cropped")+"*"+EXT_CROPPED_FRAMES+"*.png") 

   return thumbs

 
# Create a thumb 
def new_crop_thumb(frame,x,y,dest,HD):

   print("CREATING NEW THUMB to " + dest)

   # Debug
   cgitb.enable()
   
   img = cv2.imread(frame) 

   if(HD is True):
      org_w_HD = 1920
      org_h_HD = 1080
   else:
      org_w_HD = 1280
      org_h_HD = 720

   # Create empty image THUMB_WxTHUMB_H in black so we don't have any issues while working on the edges of the original frame 
   crop_img = np.zeros((THUMB_W,THUMB_H,3), np.uint8)

   # Default values
   org_x = x
   org_w = THUMB_SELECT_W + org_x
   org_y = y
   org_h = THUMB_SELECT_H + org_y   
   thumb_dest_x = 0
   thumb_dest_w = THUMB_W
   thumb_dest_y = 0
   thumb_dest_h = THUMB_H

   # We don't want to crop where it isn't possible so we test the edges
   diff_x_left  = (x-(THUMB_SELECT_W/2))
   diff_x_right = org_w_HD-(x+(THUMB_SELECT_W/2)) 
   diff_y_top   = (y-(THUMB_SELECT_H/2))
   diff_y_bottom = org_h_HD - (y+(THUMB_SELECT_H/2))

   # If the x is too close to the edge

   # ON THE LEFT
   if(diff_x_left<0):

      # Destination in thumb (img)
      thumb_dest_x = int(THUMB_W/2 - diff_x_left)

      # Part of original image
      org_x = 0
      org_w = org_select_w - thumb_dest_x  

   # ON RIGHT 
   elif(diff_x_right<0):

      # Destination in thumb (img) 
      thumb_dest_w = int(THUMB_W+diff_x_right)  

      # Part of original image 
      org_x = org_w_HD - thumb_dest_w
      org_w = org_w_HD   

   # ON TOP
   if(diff_y_top<0):

      # Destination in thumb (img)
      thumb_dest_y = int(THUMB_H/2 - diff_y_top)

      # Part of the original image
      org_y = 0
      org_h = org_select_h - thumb_dest_y

   elif(diff_y_bottom<0): 
      
      # Destination in thumb (img)
      thumb_dest_h = int(THUMB_H+diff_y_bottom)  

      # Part of the original image
      org_y =  org_h_HD - thumb_dest_h   
      org_h =  org_h_HD
   
      
   crop_img[thumb_dest_y:thumb_dest_h,thumb_dest_x:thumb_dest_w] = img[org_y:org_h,org_x:org_w]
   cv2.imwrite(dest,crop_img)
   return dest




# Create the cropped frames (thumbs) for a meteor detection
def generate_cropped_frames(video_full_path,analysed_name,meteor_json_file,HD_frames,HD):

   print("IN generate_cropped_frames <br>")

   # Debug
   cgitb.enable()
 
   # We parse the JSON
   meteor_json_file = load_json_file(meteor_json_file)
 
   # We get the frame data
   meteor_frame_data = meteor_json_file['meteor_frame_data']
   cropped_frames = []
    
   # WARNING
   # sometimes we have "event_start_time" in the JSON 
   # that is different from the start_time in the file name
   # (it was in "-trim" in the previous version of the reduce page)
   # so in order to get the proper HD frame to create the thumb
   # we need to get the proper index in HD_frames (which is not the numbered in the JSON file)
   if("event_start_time" in meteor_json_file): 
         start_video_time = datetime.datetime.strptime(analysed_name['year']+"-"+analysed_name['month']+"-"+analysed_name['day']+" "+analysed_name['hour']+":"+analysed_name['min']+":"+analysed_name['sec']+"."+analysed_name['ms'], "%Y-%m-%d %H:%M:%S.%f")
         print ("start_video_time {:%Y-%m-%d %H:%M:%S.%f}".format(start_video_time))
         start_event_time = datetime.datetime.strptime(meteor_json_file['event_start_time'], "%Y-%m-%d %H:%M:%S.%f")
         print ("start_event_time {:%Y-%m-%d %H:%M:%S.%f}".format(start_event_time))
         diff_in_sec  = (start_event_time-start_video_time).total_seconds()
         print(" THE DIFF IS " + diff_in_sec + " sec" )

   for frame in meteor_frame_data: 

      # Index of the frame 
      frame_index = int(frame[1])
      x = int(frame[2])
      y = int(frame[3])


      print("FRAME " + str(frame_index) + "<br/>")
      print("x " + str(x)+ "<br/>")
      print("y " + str(y)+ "<br/>")

      # We generate the thumb from the corresponding HD_frames
      # and add it to cropped_frames
      crop = new_crop_thumb(HD_frames[frame_index],x,y,get_cache_path(analysed_name,"cropped")+analysed_name['name_w_ext']+EXT_CROPPED_FRAMES+str(frame_index)+".png",HD)
      cropped_frames.append(crop)

   return cropped_frames


# Get the stacks for a meteor detection
# Generate it if necessary
def get_stacks(video_full_path,analysed_name,clear_cache):
   
   # Do we have the Stack for this detection 
   stacks = does_cache_exist(analysed_name,"stacks")

   if(len(stacks)==0 or clear_cache is True):
      # We need to generate the Stacks 
      # Destination = 
      # get_cache_path(analysed_name,"stacks") + analysed_name['name_w_ext'] + ".png"
      stack_file = generate_stacks(video_full_path,get_cache_path(analysed_name,"stacks")+analysed_name['name_w_ext']+".png")
   else:
      # We hope this is the first one in the folder (it should!!)
      stack_file = stacks[0]

   return stack_file


 

# Generate the Stacks for a meteor detection
def generate_stacks(video_full_path, destination):

   # Debug
   cgitb.enable() 
   
   # Get All Frames
   frames = load_video_frames(video_full_path, load_json_file(JSON_CONFIG), 0, 0)
 
   stacked_image = None

   # Create Stack 
   for frame in frames:
      frame_pil = Image.fromarray(frame)
      if stacked_image is None:
         stacked_image = stack_stack(frame_pil, frame_pil)
      else:
         stacked_image = stack_stack(stacked_image, frame_pil)

   # Save to destination 
   if stacked_image is not None:
      stacked_image.save(destination)
 
   return destination


# Get All HD Frames for a meteor detection
# Generate them if they don't exist
def get_HD_frames(video_full_path,analysed_name,clear_cache,):
   # Test if folder exists / Create it if not
   HD_frames = does_cache_exist(analysed_name,"frames")

   if(len(HD_frames)==0 or clear_cache is True):
      # We need to generate the HD Frame
      HD_frames = generate_HD_frames(video_full_path,get_cache_path(analysed_name,"frames")+analysed_name['name_w_ext'])
   else:
      # We get the frames from the cache 
      HD_frames = glob.glob(get_cache_path(analysed_name,"frames")+"*"+EXT_HD_FRAMES+"*.png") 
   
   return HD_frames


# Generate HD frames for a meteor detection
def generate_HD_frames(video_full_path, destination):

   # Frames
   frames  = []

   # Debug
   cgitb.enable() 
   
   # Get All Frames
   cmd = 'ffmpeg -y  -hide_banner -loglevel panic  -i ' + video_full_path + ' -s ' + HD_DIM + ' ' +  destination + EXT_HD_FRAMES + '_%04d' + '.png' 
   output = subprocess.check_output(cmd, shell=True).decode("utf-8")

   return glob.glob(destination+"*"+EXT_HD_FRAMES+"*.png")


# Display an error message on the page
def print_error(msg):
   print("<div id='main_container' class='container mt-4 lg-l'><div class='alert alert-danger'>"+msg+"</div></div>")
   sys.exit(0)
   


# GENERATES THE REDUCE PAGE METEOR
# from a URL 
# cmd=reduce2
# &video_file=[PATH]/[VIDEO_FILE].mp4
def reduce_meteor2(json_conf,form):
   
   # Debug
   cgitb.enable()

   # Here we have the possibility to "empty" the cache, ie regenerate the files even if they already exists
   # we just need to add "clear_cache=1" to the URL
   if(form.getvalue("clear_cache") is not None):
      clear_cache = True
   else:
      clear_cache = False

   # Get Video File & Analyse the Name to get quick access to all info
   video_full_path   = form.getvalue("video_file")

   if(video_full_path is not None):
      analysed_name = name_analyser(video_full_path)
   else:
      print_error("<b>You need to add a video file in the URL.</b>")

   # Test if the name is ok
   if(len(analysed_name)==0):
      print_error(video_full_path + " <b>is not valid video file name.</b>")
   elif(os.path.isfile(video_full_path) is False):
      print_error(video_full_path + " <b>not found.</b>")
  
   # Is it HD? & retrieve the related JSON file that contains the reduced data
   if("HD" in analysed_name):
      HD = True
      meteor_json_file = video_full_path.replace("_HD.mp4", ".json") 
   else:
      HD = False
      meteor_json_file = video_full_path.replace(".mp4", ".json")

   # Does the JSON file exists?
   if(os.path.isfile(meteor_json_file) is False):
      print_error(meteor_json_file + " <b>not found.</b><br>This detection may had not been reduced yet or the reduction failed.")
   
   # Get the HD frames
   HD_frames = get_HD_frames(video_full_path,analysed_name,clear_cache)

   # Get the stacks
   stack = get_stacks(video_full_path,analysed_name,clear_cache)
    
   # Get the thumbs (cropped HD frames)
   thumbs = get_thumbs(video_full_path,analysed_name,meteor_json_file,HD,HD_frames,clear_cache)

   #print('THUMBS<br>')
   #print(thumbs)

   #print('FRAMES<br>')
   #print(HD_frames)

   #print('STACKS<br>')
   #print(stack)