import re
import cgitb
import sys
import os.path
import cv2
import glob
import subprocess  
import math

import numpy as np

from datetime import datetime,timedelta
from pathlib import Path 
from PIL import Image

from lib.VideoLib import load_video_frames
from lib.FileIO import load_json_file, cfe, save_json_file
from lib.ReducerLib import stack_frames
from lib.REDUCE_VARS import *
from lib.VIDEO_VARS import * 
from lib.ImageLib import stack_stack,  mask_frame
from lib.Get_Station_Id import get_station_id 
from lib.UtilLib import convert_filename_to_date_cam, bound_cnt
from lib.Get_Cam_ids import get_mask 
from lib.CGI_Tools import *


# LOAD VIDEO FRAMES with MASKS
def load_video_framesX(trim_file, limit=0, mask=0,crop=()):
   (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(trim_file)
   cap = cv2.VideoCapture(trim_file)
   masks = get_mask(cam) 
   frames = [] 
   frame_count = 0
   go = 1

   while go == 1:
      if True :
         _ , frame = cap.read()
         if frame is None:
            if frame_count <= 5 :
               cap.release()
               return(frames)
            else:
               go = 0
         else:
           
            if limit != 0 and frame_count > limit:
               cap.release()
               return(frames)
            if len(frame.shape) == 3 :
               frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            if mask == 1 and frame is not None:
               if frame.shape[0] == 1080:
                  hd = 1
               else:
                  hd = 0
               masks = get_mask(cam)
               frame = mask_frame(frame, [], masks, 5)
            
            frames.append(frame) 
      frame_count+= 1
   cap.release()
   return frames




# Return the meteor general direction
def meteor_dir(fx,fy,lx,ly):
   # positive x means right to left (leading edge = lowest x value)
   # negative x means left to right (leading edge = greatest x value)
   # positive y means top to down (leading edge = greatest y value)
   # negative y means down to top (leading edge = lowest y value)
   dir_x = lx - fx 
   dir_y = ly - fy
   if dir_x < 0:
      x_dir_mod = 1
   else:
      x_dir_mod = -1
   if dir_y < 0:
      y_dir_mod = 1
   else:
      y_dir_mod = -1
   return(x_dir_mod, y_dir_mod)

# No idea... it's one of Mike's function
def distance(point,coef):
    return abs((coef[0]*point[0])-point[1]+coef[1])/math.sqrt((coef[0]*coef[0])+1)

# Distance between 2 points
def calc_dist(p1,p2):
   x1,y1 = p1
   x2,y2 = p2
   dist = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
   return dist

# No idea... it's one of Mike's function
def calc_score(frames):
   first_x = None
   last_x = None
   last_dist_from_start = None
   dists = []
   new_frames = []
   xs = []
   ys = []
   for frame in frames:
      x = frame['x']
      y = frame['y']
      xs.append(x)
      ys.append(y)
   for frame in frames:
      (dist_to_line, z, med_dist) = poly_fit_check(xs,ys, frame['x'],frame['y'])
      if first_x is None:
         first_x = frame['x']
         first_y = frame['y']
         first_fn = frame['fn']
         dist_from_start = 0
         dist_from_last = 0
      if last_x is not None:
         dist_from_start = calc_dist((first_x,first_y),(frame['x'],frame['y']))
      if last_dist_from_start is not None:
         dist_from_last = dist_from_start - last_dist_from_start
      else:
         last_dist_from_start = 0
         dist_from_last = 0
      last_x = frame['x']
      last_x = frame['y']
      last_dist_from_start = dist_from_start
      frame['dist_from_start'] = dist_from_start
      frame['dist_from_last'] = dist_from_last
      frame['dist_to_line'] = dist_to_line
      dists.append(dist_from_last)
      new_frames.append(frame)

   med_dist = np.median(dists)
   med_errs = []
   final_frames = []
   for frame in new_frames:
      if med_dist > 0 and frame['dist_from_last'] > 0:
         med_err = abs(med_dist - frame['dist_from_last']) + frame['dist_to_line']
         frame['med_err'] = med_err  
      else:
         med_err = 0
      med_errs.append(med_err)
      final_frames.append(frame)
   if len(med_errs) == 0:
      score = 999 
   else: 
      score = np.mean(med_errs)
   return(score, final_frames)


# No idea... it's one of Mike's function
def poly_fit_check(poly_x,poly_y, x,y, z=None):
   if z is None:
      if len(poly_x) >= 3:
         try:
            z = np.polyfit(poly_x,poly_y,1)
            f = np.poly1d(z)
         except:
            return(0)

      else:
         return(0) 
   dist_to_line = distance((x,y),z)

   all_dist = []
   for i in range(0,len(poly_x)):
      ddd = distance((poly_x[i],poly_y[i]),z)
      all_dist.append(ddd)

   med_dist = np.median(all_dist)
   show = 0 
 
   return(dist_to_line, z, med_dist)


# No idea... it's one of Mike's function
def line_info(frames):
   xs = []
   ys = []
   line_segs = []
   xdiffs = []
   ydiffs = []
   last_x = None

   for frame in frames:
       x = frame['x']
       y = frame['y']
       if last_x is not None:
          xdiffs.append(x - last_x)
          ydiffs.append(y - last_y)

       xs.append(frame['x'])
       ys.append(frame['y'])
       if('dist_from_last' in frame):
         line_segs.append(frame['dist_from_last'])
         last_x = x
         last_y = y

   tx = abs(xs[0] - xs[-1])
   ty = abs(ys[0] - ys[-1])
   med_seg = np.median(line_segs)

   mxd = np.median(xdiffs)
   myd = np.median(ydiffs)

   (dist_to_line, z, med_dist) = poly_fit_check(xs,ys, xs[0],ys[0])

   if ty > tx:
      return("y", z, med_dist,med_seg,mxd,myd)
   else:
      return("x", z, med_dist,med_seg,mxd,myd)


# Get Seg. Lenght (eval point) and update the json
def update_eval_points(json_file):

   jd = load_json_file(json_file)
   
   if("frames" in jd):
      frames = jd['frames']
 
   x_dir_mod,y_dir_mod = meteor_dir(frames[0]['x'], frames[0]['y'], frames[-1]['x'], frames[-1]['y'])
   dom,z,med_dist,med_seg,mxd,myd = line_info(frames) 
   
   # Why 3 Times? No idea, it's Mike's code
   ps_old, new_frames = calc_score(frames)
   ps_new, new_frames = calc_score(new_frames) 
   ps_new, new_frames = calc_score(new_frames)

   jd['report']['point_score'] = ps_new 
   jd['frames'] = new_frames 
   save_json_file(json_file,jd)
    


# Get intensity & update the json
def update_intensity(json_file, json_data, hd_video_file): 
    
   # Get Video frames 
   hd_frames = load_video_framesX(hd_video_file, 0,  1)
   
   # Get sync val
   sync = 0
   if('sync' in json_data):
      if('hd_ind' in json_data['sync']):
         if('sd_ind' in json_data['sync']):
            sync =  json_data['sync']['hd_ind'] - json_data['sync']['sd_ind']
   
   if('frames' in json_data):
      json_frames = json_data['frames'] 
      if(len(json_frames)>0 and len(hd_frames)>0):
           
         cx1,cy1,cx2,cy2 = bound_cnt(json_frames[0]['x'],json_frames[0]['y'],hd_frames[0].shape[1],hd_frames[0].shape[0], 20)
         # Frame 0 == Bg
         bg_cnt = hd_frames[0][cy1:cy2,cx1:cx2] 
         new_frames = []
         
         for frame in json_frames:   
            fn = frame['fn'] + sync
            cx1,cy1,cx2,cy2 = bound_cnt(frame['x'],frame['y'],hd_frames[0].shape[1],hd_frames[0].shape[0], 20)
            try:
               cnt = hd_frames[fn][cy1:cy2,cx1:cx2] 
               bg_cnt = hd_frames[0][cy1:cy2,cx1:cx2] 
               cnt_sub = cv2.subtract(cnt,bg_cnt)
               cnt_int = np.sum(cnt) - np.sum(bg_cnt)
               ff_sub = cv2.subtract(hd_frames[fn],hd_frames[0])
               ff_int = np.sum(ff_sub) 
               if cnt_int > 18446744073709:
                  cnt_int = 0
               if ff_int > 18446744073709:
                  ff_int = 0

               frame['intensity'] = int(cnt_int)
               frame['intensity_ff'] = int(ff_int) 
               new_frames.append(frame)
            except:
               # DONT DO ANYTHING 
               print('')

         json_data['frames'] = new_frames 
         save_json_file(json_file,json_data) 
   else:
      return False

  



# Apply calib to a given JSON
def reapply_calib(json_data, json_file_path):
   # We re-apply the calib in order to get the segment length & intensity
   # and re-compute the seg length
   if('frames' in json_data): 
      update_intensity(json_file_path, json_data, json_data['info']['hd_vid'])
      if(len(json_data['frames'])>0):
         if('dist_from_start' not in json_data['frames'][0]):
            update_eval_points(json_file_path)  





# Test if we can get a station id from an URL and return the station id or FALSE
def can_we_get_the_station_id(path):
   test = path.split(os.sep)
   try:
      # THE STATION ID SHOULD THE 4th element
      # ex: ['', 'mnt', 'ams2', 'meteor_archive', 'AMS8', 'METEOR', '2020', '01', '05', '2020_01_05_03_01_32_000_010038-trim0597-HD.mp4']
      return test[4]
   except:
      return False
 
 
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

   # Add the station id
   tmp_station_id = can_we_get_the_station_id(file_names)
   if(tmp_station_id  is not False):
      res['station_id'] = tmp_station_id
   else:
      res['station_id'] = get_station_id()
 
   return res


# Return a date & time object based on the name_analyser results
def get_datetime_from_analysedname(analysed_name):
   
   # Debug
   cgitb.enable()
   
   dt = ''
   dt = analysed_name['year']+'-'+analysed_name['month']+'-'+analysed_name['day']+' '+analysed_name['hour']+':'+analysed_name['min']+':'+analysed_name['sec']+'.'+analysed_name['ms']

   try:
      dt = analysed_name['year']+'-'+analysed_name['month']+'-'+analysed_name['day']+' '+analysed_name['hour']+':'+analysed_name['min']+':'+analysed_name['sec']+'.'+analysed_name['ms']
   except:
      print("CANNOT GET THE PROPER DATE & TIME FROM THE FILE " + analysed_name['full_path'])
      sys.exit(0)
   return datetime.strptime(dt, '%Y-%m-%d %H:%M:%S.%f')
 

# Return Cache folder name based on an analysed_file (parsed video file name)
# and cache_type = stacks | frames | cropped or thumbs
def get_cache_path(analysed_file_name, cache_type=''):
    # Build the path to the proper cache folder
   cache_path = CACHE_PATH + analysed_file_name['station_id'] +  "/" + analysed_file_name['year'] + "/" + analysed_file_name['month'] + "/" + analysed_file_name['day'] + "/" + os.path.splitext(analysed_file_name['name'])[0]

   if(cache_type == "frames"):
      cache_path += FRAMES_SUBPATH
   elif(cache_type == "stacks"):
      cache_path += STACKS_SUBPATH
   elif(cache_type == "cropped"  or cache_type == "thumbs"):
      cache_path += CROPPED_FRAMES_SUBPATH
   elif(cache_type == 'tmp_cropped'):
      cache_path += TMP_CROPPED_FRAMES_SUBPATH
   elif(cache_type == 'preview'):
      cache_path += PREVIEW
   elif(cache_type == 'tmp_hd_cropped_sync'):
      cache_path += TMP_HD_CROPPED_SUBFRAMES_SUBPATH
   elif(cache_type == 'tmp_sd_cropped_sync'):
      cache_path += TMP_SD_CROPPED_SUBFRAMES_SUBPATH
   elif(cache_type == 'graphs'):
      cache_path += GRAPHS
   return cache_path


# Get the path to the cache of a given detection 
# create the folder if it doesn't exists 
def does_cache_exist(analysed_file_name,cache_type,media_type = '/*.png'):

   # Debug
   cgitb.enable()

   # Get Cache Path
   cache_path = get_cache_path(analysed_file_name,cache_type)
 
   if(os.path.isdir(cache_path)):
      # We return the glob of the folder with all the images
      return sorted(glob.glob(cache_path+media_type))
   else:
      # We Create the Folder and return null
      os.makedirs(cache_path)
      # print(cache_path + " created")
      return []


# Compute the date & time of a frame based on the date & time of another one
def get_frame_time_from_f(frame_id, frame_id_org, frame_dt_org):
   
   # Compute the diff of frame between random_frame 
   # and frame_id 
   diff_fn = int(frame_id) - int(frame_id_org)

   # We multiple the frame # difference by 1/FPS 
   diff_fn = diff_fn * 1 / FPS_HD

   dt = datetime.strptime(frame_dt_org, '%Y-%m-%d %H:%M:%S.%f')

   # We add the diff in seconds
   dt = dt +  timedelta(0,diff_fn)
   dt = str(dt)
 
   # We remove the last 3 digits (from %f) 
   # or add them
   if(len(dt)==26):
      dt = dt[:-3]
   else:
      dt +=  ".000"

   # We return the Date as a string
   return dt


# Return a date & time based on a parsed json_file and the frame id
def get_frame_time(json,frame_id,analysed_name):

   res= False

   # We just need one existing frame and its date & time
   if("frames" in json):
 
      if(len(json['frames'])!=0):
         random_frame = json['frames'][0]
         res = True
         return get_frame_time_from_f(frame_id,random_frame['fn'],random_frame['dt'])
      else:
         res = False

   if(res is False):
 
      # Since we didn't find the frame time based on other frame time
      # we need to rely on the name of the file
      return get_frame_time_from_f(frame_id,0,analysed_name['year']+'-'+analysed_name['month']+'-'+analysed_name['day']+' '+analysed_name['hour']+':'+analysed_name['min']+':'+analysed_name['sec']+'.'+analysed_name['ms'])
 


# Get Specific cropped Frames from a frame ID and an analysed name
def get_thumb(analysed_name,frame_id):
   return glob.glob(get_cache_path(analysed_name,"cropped")+"*"+EXT_CROPPED_FRAMES+str(frame_id)+".png") 

# Get the thumbs (cropped frames) for a meteor detection
# Generate them if necessary
def get_thumbs(analysed_name,meteor_json_data,HD,HD_frames,clear_cache):

   # Debug
   cgitb.enable()

   # Do we have them already?
   thumbs = does_cache_exist(analysed_name,"cropped")
  
   if(len(thumbs)==0 or clear_cache is True or (clear_cache is True)):
      # We need to generate the thumbs 
      thumbs = generate_cropped_frames(analysed_name,meteor_json_data,HD_frames,HD,clear_cache)
   else:
      # We return them 
      thumbs = glob.glob(get_cache_path(analysed_name,"cropped")+"*"+EXT_CROPPED_FRAMES+"*.png") 
   return thumbs


# Create a thumb 
def new_crop_thumb(frame,x,y,dest,HD = True):
   if frame is None:
      return(None)

   # Debug
   cgitb.enable()
   img = cv2.imread(frame)  
   if img is None:
      # This frame is bad and the cache needs to be re-generated.
      return(None)

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

   # ON THE LEFT (VERIFIED)
   if(org_x<=0):

      # Part of the original image
      org_x = 0

      # Part of the thumb
      thumb_dest_x = int(THUMB_SELECT_W/2-x)
      thumb_dest_w = int(abs(thumb_dest_w - org_x))
 
   # ON RIGHT (VERIFIED)
   elif(org_x >= (org_w_HD-THUMB_SELECT_W)): 
      
      # Part of the original image
      org_w = org_w_HD
     
      # Destination in thumb (img) 
      thumb_dest_w =  HD_W - org_x
  
   # ON TOP (VERIFIED)
   if(org_y<=0):
 
      # Part of the original image
      org_y = 0 

      # Part of the thumb
      thumb_dest_y = int(THUMB_SELECT_H/2-y)
      thumb_dest_h = int(abs(thumb_dest_w - org_y))
       

   # ON BOTTOM
   if(org_y >= (org_h_HD-THUMB_SELECT_H)):

      # Part of the original image
      org_h = org_h_HD

      # Destination in thumb (img)
      thumb_dest_h = HD_H -  org_y 
  
   crop_img[thumb_dest_y:thumb_dest_h,thumb_dest_x:thumb_dest_w] = img[org_y:org_h,org_x:org_w]
   cv2.imwrite(dest,crop_img)
  
   return dest





# Create a preview (small jpg thumbs for the listings)
# based preferably from HD stack 
# based on a JSON file
def generate_preview(analysed_name):

   clear_cache = 0

   # Debug
   cgitb.enable()

   # Destination
   dest = does_cache_exist(analysed_name,"preview","/*.jpg")

   if(len(dest)==0):
      video_hd_full_path = analysed_name['full_path'].replace('.json','-HD.mp4')

      stack = ''

      # We generate the preview from the stack (HD first)
      if(cfe(video_hd_full_path)==1):
         stack = get_stacks(analysed_name,clear_cache,True) 
      else:
         video_sd_full_path = analysed_name['full_path'].replace('.json','-SD.mp4')
         if(cfe(video_sd_full_path)==1):
            stack = get_stacks(analysed_name,clear_cache,False)     

      if(stack!=''):   

         # We resize the stack and change it to a jpg
         stack_PIL = Image.open(stack)
         preview =  stack_PIL.resize((PREVIEW_W, PREVIEW_H))

         # We save the preview as a jpg 
         preview.save(get_cache_path(analysed_name,"preview")+analysed_name['name_w_ext']+'.jpg', 'jpeg')
      
      else:
         return "IMPOSSIBLE TO GENERATE THE PREVIEW"

   # Return the preview full path
   return get_cache_path(analysed_name,"preview")+analysed_name['name_w_ext']+'.jpg'       



# Create ONE cropped frame (thumb) for a meteor detection
# this is use after a manual picking
def generate_cropped_frame(analysed_name,meteor_json_data,the_HD_frame,the_HD_frame_fn,the_SD_frame_fn,x,y,HD=True):

   if(HD):
      destination =  get_cache_path(analysed_name,"cropped")+analysed_name['name_w_ext']+EXT_CROPPED_FRAMES+str(the_SD_frame_fn)+".png"
      out_hd_frame = destination.replace("frm", "HD-" + str(the_HD_frame_fn) + "-SD-")
      crop = new_crop_thumb(the_HD_frame,x,y,destination,HD)
      return crop
   else:
      return False

# Create the cropped frames (thumbs) for a meteor detection
def generate_cropped_frames(analysed_name,meteor_json_data,HD_frames,HD,clear_cache):

   # Debug
   cgitb.enable()
  
   # We get the frame data
   meteor_frame_data = meteor_json_data['frames']

   # Do we have sync with the corresponding hd_ind for a sd_ind?
   hd_frames_sd_frames_diff = 0  
   if('sync' in meteor_json_data and HD is True):
      hd_frames_sd_frames_diff = int(meteor_json_data['sync']['hd_ind'])-int(meteor_json_data['sync']['sd_ind'])
   
   # To store the cropped frames
   cropped_frames = [] 
   
   # If clear_cache, we delete all the files in the frame directory first
   if(clear_cache==1):
      fold = get_cache_path(analysed_name,"cropped")
      filelist = glob.glob(os.path.join(fold, "*.png"))
      for f in filelist:
         os.remove(f)

   if(HD):
      for frame in meteor_frame_data:
         frame_index = int(frame['fn'])+hd_frames_sd_frames_diff    
         destination =  get_cache_path(analysed_name,"cropped")+analysed_name['name_w_ext']+EXT_CROPPED_FRAMES+str(frame['fn'])+".png"
         org_HD_frame = HD_frames[frame_index]
         out_hd_frame = destination.replace("frm", "HD-" + str(frame_index) + "-SD-")
         crop = new_crop_thumb(org_HD_frame,frame['x'],frame['y'],destination,HD)
         cropped_frames.append(crop)
   
   return cropped_frames 
    


# Get the stacks for a meteor detection
# Generate it if necessary
def get_stacks(analysed_name,clear_cache,toHD):

   #print("IN GET STACKS " + get_cache_path(analysed_name,"stacks"))
 
   stacks_folder = does_cache_exist(analysed_name,"stacks")

   # Do we have the Stack for this detection 
   if(toHD):
      stacks = glob.glob(get_cache_path(analysed_name,"stacks")+"*"+"-HD"+"*") 
   else:
      stacks = glob.glob(get_cache_path(analysed_name,"stacks")+"*"+"-SD"+"*") 

   if(len(stacks)==0 or clear_cache is True):
      # We need to generate the Stacks 
      # Destination = 
      # get_cache_path(analysed_name,"stacks") + analysed_name['name_w_ext'] + ".png"
      if(toHD): 
         stacks =  generate_stacks(analysed_name['full_path'].replace('.json','-HD.mp4'),get_cache_path(analysed_name,"stacks")+analysed_name['name_w_ext']+"-HD.png",toHD)
      else: 
         stacks =  generate_stacks(analysed_name['full_path'].replace('.json','-SD.mp4'),get_cache_path(analysed_name,"stacks")+analysed_name['name_w_ext']+"-SD.png",False)

      stack_file = stacks
  
   else:
      stack_file = stacks[0]

   return stack_file
 

# Generate the Stacks for a meteor detection
def generate_stacks(video_full_path, destination, toHD):
    
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

   if stacked_image is not None and toHD is False: 
      # Resize  (STACK_W, STACK_H) & Save to destination 
      stacked_image = stacked_image.resize((STACK_W, STACK_H))
      stacked_image.save(destination)
   elif stacked_image is not None: 
      # Resize to HD (HD_W, HD_H)    
      stacked_image = stacked_image.resize((HD_W, HD_H))
      stacked_image.save(destination)
   elif stacked_image is None:
      print("Impossible to generate the stacks for " + video_full_path) 
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
   if(cfe(analysed_name['full_path'].replace('.json','-HD.mp4') )):
      cmd = 'ffmpeg -y -hide_banner -loglevel panic  -i ' + analysed_name['full_path'].replace('.json','-HD.mp4') + ' -s ' + str(HD_W) + "x" + str(HD_H) + ' ' +  destination + EXT_HD_FRAMES + '%04d' + '.png' 
      output = subprocess.check_output(cmd, shell=True).decode("utf-8")

   return glob.glob(destination+"*"+EXT_HD_FRAMES+"*.png")


# Generate SD frames for a meteor detection (warning: the SD video is first resized to HD)
def generate_SD_and_HD_frames_for_sync(analysed_name,destination,x_start,y_start,w,h):
   
   # Debug
   cgitb.enable() 

   # Frames
   frames  = []

   # video_sd_full_path
   video_sd_full_path = analysed_name['full_path'].replace('-HD.mp4','-SD.mp4')
   
   # we extract the frames from the SD resize video  
   cmd = 'ffmpeg   -i ' + video_sd_full_path +  ' -y -filter_complex "[0:v]scale=' + str(HD_W) + ":" + str(HD_H) + '[scale];[scale]crop='+str(w)+':'+str(h)+':'+str(x_start)+':'+str(y_start)+'[out]"  -map "[out]" ' +  destination  + os.sep + '/SD%04d' + '.png' 
   os.system(cmd)
      
   # We do the same with the frames from the HD video
   cmd = 'ffmpeg   -i ' + analysed_name['full_path'] +  ' -y -filter_complex "[0:v]crop='+str(w)+':'+str(h)+':'+str(x_start)+':'+str(y_start)+'[out]"  -map "[out]" ' +  destination  + os.sep + '/HD%04d' + '.png' 
   os.system(cmd)

 
   return glob.glob(destination  + os.sep + '/SD*.png'), glob.glob(destination  + os.sep + '/HD*.png')
