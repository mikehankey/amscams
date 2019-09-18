import re
import cgitb
import sys
import os.path
import cv2
import glob
import numpy as np
import subprocess  

from datetime import datetime,timedelta
from pathlib import Path 
from PIL import Image

from lib.VideoLib import load_video_frames
from lib.FileIO import load_json_file 
from lib.ReducerLib import stack_frames
from lib.REDUCE_VARS import *
from lib.VIDEO_VARS import * 
from lib.ImageLib import stack_stack
 


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

   # Add the full file_names (often a full path) to the array so we don't have to pass the original when we need it
   res['full_path'] = file_names

   return res


# Return a date & time object based on the name_analyser results
def get_datetime_from_analysedname(analysed_name):
   dt = ''
   try:
      dt = analysed_name['year']+'-'+analysed_name['month']+'-'+analysed_name['day']+' '+analysed_name['hour']+':'+analysed_name['min']+':'+analysed_name['sec']+'.'+analysed_name['ms']
   except:
      print("CANNOT GET THE PROPER DATE & TIME FROM THE FILE " + analyse_name['full_path'])
      sys.exit(0)
   return datetime.strptime(dt, '%Y-%m-%d %H:%M:%S.%f');
 

# Return Cache folder name based on an analysed_file (parsed video file name)
# and cache_type = stacks | frames | cropped or thumbs
def get_cache_path(analysed_file_name, cache_type):
    # Build the path to the proper cache folder
   cache_path = CACHE_PATH + analysed_file_name['station_id'] +  "/" + analysed_file_name['year'] + "/" + analysed_file_name['month'] + "/" + analysed_file_name['day'] + "/" + os.path.splitext(analysed_file_name['name'])[0]

   if(cache_type == "frames"):
      cache_path += FRAMES_SUBPATH
   elif(cache_type == "stacks"):
      cache_path += STACKS_SUBPATH
   elif(cache_type == "cropped"  or cache_type == "thumbs"):
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


# Return a date & time based on a parsed json_file and the frame id
def get_frame_time(json,frame_id):

   # We just need one existing frame and its date & time
   if("frames" in json):
      random_frame = json['frames'][0]

      # Date & time and Frame ID for random_frame
      dt = random_frame['dt']
      fn = random_frame['fn']

      # Compute the diff of frame between random_frame 
      # and frame_id
      diff_fn = int(frame_id) - int(fn)

      # We multiple the frame # difference by 1/FPS 
      diff_fn = diff_fn * 1 / FPS_HD
 
      dt = datetime.strptime(dt, '%Y-%m-%d %H:%M:%S.%f')

      # We add the diff in seconds
      dt = dt +  timedelta(0,diff_fn)
      dt = str(dt)

      # We remove the last 3 digits (from %f)
      dt = dt[:-3]

      # We return the Date as a string
      return dt

   else:
      return ""

# Get Specific cropped Frames from a frame ID and an analysed name
def get_thumb(analysed_name,frame_id):
   return glob.glob(get_cache_path(analysed_name,"cropped")+"*"+EXT_CROPPED_FRAMES+str(frame_id)+".png") 

# Get the thumbs (cropped frames) for a meteor detection
# Generate them if necessary
def get_thumbs(analysed_name,meteor_json_data,HD,HD_frames,clear_cache):

   # Do we have them already?
   thumbs = does_cache_exist(analysed_name,"cropped")

   if(len(thumbs)==0 or clear_cache is True):
      # We need to generate the thumbs 
      thumbs = generate_cropped_frames(analysed_name,meteor_json_data,HD_frames,HD)
   else:
      # We return them
      thumbs = glob.glob(get_cache_path(analysed_name,"cropped")+"*"+EXT_CROPPED_FRAMES+"*.png") 

   return thumbs


# Create a thumb 
def new_crop_thumb(frame,x,y,dest,HD = True):

   # Debug
   cgitb.enable()
   img = cv2.imread(frame) 
   

   # We shouldn't have the need for that... (check with VIDEO_VARS values and the way we're creating the frames from the video)
   if(HD is True):
      org_w_HD = HD_W
      org_h_HD = HD_H
   else:
      org_w_HD = SD_W
      org_h_HD = SD_H

   # Create empty image THUMB_WxTHUMB_H in black so we don't have any issues while working on the edges of the original frame 
   crop_img = np.zeros((THUMB_W,THUMB_H,3), np.uint8)

   # Default values
   org_x = int(x - THUMB_SELECT_W/2)
   org_w = int(THUMB_SELECT_W + org_x)
   org_y = int(y  - THUMB_SELECT_H/2)
   org_h = int(THUMB_SELECT_H + org_y)    

   thumb_dest_x = 0
   thumb_dest_w = THUMB_W
   thumb_dest_y = 0
   thumb_dest_h = THUMB_H
 
   # If the x is too close to the edge

   # ON THE LEFT
   if(org_x<0):

      # Part of the original image
      org_w = org_x + THUMB_SELECT_W 
      org_x = 0
     
      # Destination in thumb (img)
      thumb_dest_x = org_w
       

   # ON RIGHT 
   elif(org_x > (org_w_HD-THUMB_SELECT_W)): 
      
      # Part of the original image
      org_w = org_w_HD
     
      # Destination in thumb (img) 
      thumb_dest_w =  HD_W - org_x

     
   # ON TOP
   if(org_y<0):
 
      # Part of the original image
      org_h = THUMB_SELECT_H + org_y  
      org_y = 0

      # Destination in thumb (img)
      thumb_dest_h = THUMB_H
      thumb_dest_y = thumb_dest_h - org_h

   # ON BOTTOM
   if(org_y > (org_h_HD-THUMB_SELECT_H)):

      # Part of the original image
      org_h = org_h_HD

      # Destination in thumb (img)
      thumb_dest_h = HD_H -  org_y 
    
   crop_img[thumb_dest_y:thumb_dest_h,thumb_dest_x:thumb_dest_w] = img[org_y:org_h,org_x:org_w]
   cv2.imwrite(dest,crop_img)
   return dest





# Create the cropped frames (thumbs) for a meteor detection
def generate_cropped_frames(analysed_name,meteor_json_data,HD_frames,HD):

   # Debug
   cgitb.enable()
    
   # We get the frame data
   meteor_frame_data = meteor_json_data['frames']
   cropped_frames = [] 
   
   for frame in meteor_frame_data: 
     
      frame_index = int(frame['fn']) # - 1 
 
      x = int(frame['x'])
      y = int(frame['y'])

      destination =  get_cache_path(analysed_name,"cropped")+analysed_name['name_w_ext']+EXT_CROPPED_FRAMES+str(frame_index)+".png"

      # WARNING THERE IS A -1 FROM THE LIST OF HD FRAMES!!!
      # BECAUSE THE JSON IS WRONG      
      org_HD_frame = HD_frames[frame_index-1]
 
      # We generate the thumb from the corresponding HD_frames
      # and add it to cropped_frames
      crop = new_crop_thumb(org_HD_frame,x,y,destination,HD)
      cropped_frames.append(crop)

   return cropped_frames


# Get the stacks for a meteor detection
# Generate it if necessary
def get_stacks(analysed_name,clear_cache):
   
   # Do we have the Stack for this detection 
   stacks = does_cache_exist(analysed_name,"stacks")

   if(len(stacks)==0 or clear_cache is True):
      # We need to generate the Stacks 
      # Destination = 
      # get_cache_path(analysed_name,"stacks") + analysed_name['name_w_ext'] + ".png"
      stack_file = generate_stacks(analysed_name['full_path'],get_cache_path(analysed_name,"stacks")+analysed_name['name_w_ext']+".png")
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

   # Resize  (STACK_W, STACK_H) & Save to destination 
   if stacked_image is not None: 
      stacked_image = stacked_image.resize((STACK_W, STACK_H))
      stacked_image.save(destination)
 
   return destination



# Get Specific HD Frames from a frame ID and an analysed name
def get_HD_frame(analysed_name,frame_id):
   # Format the frame_id so we always have 4 digits
   frame_id = str(frame_id).zfill(4)
   return glob.glob(get_cache_path(analysed_name,"frames")+"*"+EXT_HD_FRAMES+str(frame_id)+".png") 


# Get All HD Frames for a meteor detection
# Generate them if they don't exist
def get_HD_frames(analysed_name,clear_cache):
   # Test if folder exists / Create it if not
   HD_frames = does_cache_exist(analysed_name,"frames")

   if(len(HD_frames)==0 or clear_cache is True):
      # We need to generate the HD Frame
      HD_frames = generate_HD_frames(analysed_name,get_cache_path(analysed_name,"frames")+analysed_name['name_w_ext'])
   else:
      # We get the frames from the cache 
      HD_frames = glob.glob(get_cache_path(analysed_name,"frames")+"*"+EXT_HD_FRAMES+"*.png") 
   
   # IMPORTANT: we need to sort the frames so we can rely on the indexes in the list to access them
   HD_frames.sort()
   return HD_frames


# Generate HD frames for a meteor detection
def generate_HD_frames(analysed_name, destination):

   # Frames
   frames  = []

   # Debug
   cgitb.enable() 
   
   # Get All Frames
   cmd = 'ffmpeg -y -hide_banner -loglevel panic  -i ' + analysed_name['full_path'] + ' -s ' + str(HD_W) + "x" + str(HD_H) + ' ' +  destination + EXT_HD_FRAMES + '%04d' + '.png' 
   output = subprocess.check_output(cmd, shell=True).decode("utf-8")

   return glob.glob(destination+"*"+EXT_HD_FRAMES+"*.png")
