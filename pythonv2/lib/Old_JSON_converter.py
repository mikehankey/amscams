import json
import re
import os
import glob
import shutil
import sys
from datetime import datetime,timedelta

from lib.FileIO import load_json_file,save_json_file
from lib.MeteorReduce_Tools import name_analyser, get_cache_path, get_frame_time_from_f, get_datetime_from_analysedname
from lib.REDUCE_VARS import *
from lib.Get_Station_Id import get_station_id
from lib.VIDEO_VARS import FPS_HD

# Get a new folder in meteor_archive
# from an old json file
def get_new_archive_folder(analysed_name):
   if('station_id' not in analysed_name):
      station_id = get_station_id()
   else:
      station_id = analysed_name['station_id'] 
  
   return METEOR_ARCHIVE + station_id + "/" + METEOR + analysed_name['year'] + "/" + analysed_name['month'] + "/" + analysed_name['day'] + "/"

# Analysed and old file (containing "-trim")
# Parses a regexp (OLD_FILE_NAME_REGEX) a file name
# and returns all the info defined in OLD_FILE_NAME_REGEXGROUP
def old_name_analyser(file_names):
   matches = re.finditer(OLD_FILE_NAME_REGEX, file_names, re.MULTILINE)
   res = {}
  
   for matchNum, match in enumerate(matches, start=1):
      for groupNum in range(0, len(match.groups())):
         if(match.group(groupNum) is not None):
            res[OLD_FILE_NAME_REGEX_GROUP[groupNum]] = match.group(groupNum)
         groupNum = groupNum + 1

   # Get Name without extension if possible
   if(res is not None and "name" in res):
      res['name_w_ext'] = res['name'].split('.')[0]

   # Add the full file_names (often a full path) to the array so we don't have to pass the original when we need it
   res['full_path'] = file_names

   return res


# Fix the old files names that contains "-trim"
# so we can use the usual name_analyser
def fix_old_file_name(filename):
   # We need to get the current stations ID (in as6.json)
   json_conf = load_json_file(JSON_CONFIG)
   station_id = json_conf['site']['ams_id']
   if("-reduced" in filename):
      filename = filename.replace("-reduced", "")

   trim_value = 0 

   if("trim" in filename):

      matches =  re.finditer(OLD_FILE_NAME_REGEX, filename, re.MULTILINE)
      res = {}
  
      for matchNum, match in enumerate(matches, start=1):
         for groupNum in range(0, len(match.groups())):
            if(match.group(groupNum) is not None):
               res[OLD_FILE_NAME_REGEX_GROUP[groupNum]] = match.group(groupNum)
            groupNum = groupNum + 1
 
      # Get original Date & Time 
      org_dt = datetime.strptime(res['year']+'-'+res['month']+'-'+res['day']+' '+res['hour']+':'+res['min']+':'+res['sec']+'.'+res['ms'], '%Y-%m-%d %H:%M:%S.%f')

      # We convert the trim in seconds 
      trim_in_sec = float(res["trim"])/FPS_HD

      # We add the trim_in_sec
      org_dt = org_dt +  timedelta(0,trim_in_sec)

      # Create fixed name based on all data
      org_dt = org_dt.strftime("%Y_%m_%d_%H_%M_%S_%f")

      # [:-3] to only keep 4 digits for the microseconds
      toReturn =   org_dt[:-3] + '_'+res['cam_id']+'_'+get_station_id()

      if("HD" in filename):
         toReturn +=  "_HD.json"
      else:
         toReturn +=  "_SD.json"
 
      return toReturn
   else:
      return filename



# Get cal_params new version from an old JSON version 
def get_new_calib(json_f):

   # If 'device_alt' isn't defined, we have to work with 'site_alt'...
   if "device_alt" not in json_f['cal_params']:
      json_f['cal_params']['device_alt'] = float(json_f['cal_params']['site_alt'])
      json_f['cal_params']['device_lat'] = float(json_f['cal_params']['site_lat'])  
      json_f['cal_params']['device_lng'] = float(json_f['cal_params']['site_lng'])  
    
   new_dt = json_f['event_start_time']
   new_dt = new_dt.replace('/','_')
   new_dt = new_dt.replace(' ','_')
   new_dt = new_dt.replace(':','_')
   new_dt = new_dt.replace('.','_')
   new_dt = new_dt.replace('-','_')
 

   return { "calib":  
      {  "dt":   new_dt,
         "device": {
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
            "angle":  float(json_f['cal_params']['position_angle']),
      }      
   }}

# Get new info (device & detection info) from an old JSON version
def get_new_info(json_f):
   if('station_name' not in json_f):
      station_name = get_station_id()
   else:
      station_name = json_f['station_name']

   print("IN GET NEW INFO <br/>")
   print(json_f)
   sys.exit(0)

   return  {
      "info": {
         "station": station_name,
         "hd": 1, # We assume we have the HD vid by default (not a big deal if we dont)
         "device": json_f['device_name'],
         "dur": float(json_f['event_duration']),
         "max_peak": float(json_f['peak_magnitude'])
      }
   }

# Get new stars info from an old JSON version 
def get_new_stars(json_f):
   new_stars = []
   for star in json_f['cal_params']['cat_image_stars']:
      new_stars.append({
         "name": star[0],
         "mag": float(star[1]),
         "ra": float(star[2]),
         "dec": float(star[3]),
         "dist_px": float(star[6]),
         "i_pos": [float(star[7]),float(star[8])],
         "cat_dist_pos": [float(star[11]),float(star[12])],
         "cat_und_pos": [float(star[13]),float(star[14])]
      })

   return {"stars": new_stars}

# Convert a whole old JSON file following the new DTD
def convert(json_file_path):
   
   print("IN CONVERT<br>")
   print("INITIAL:<br/> ")
   print(json_file_path)
   
   json_f = load_json_file(json_file_path)
   
   print("<br>")
   print(json_f)


   # Convert info 
   info = get_new_info(json_f)

   # Add the original name with trim in case there's an issue
   info['info']['org_file_name'] = json_file_path

   calib = get_new_calib(json_f)
   stars = get_new_stars(json_f)

   # The stars belong to calib
   calib['calib']['stars'] = stars['stars']
   
   return {"info": info['info'],"calib": calib['calib']}


# Move new JSON file and HD video file to meteor_archive
# with a proper name, and in the proper folder
# from a old -reduced.json file
def move_old_detection_to_archive(json_file_path, display=False):
   
   # We fix the old name to get the proper info
   fixed_json_file_path = fix_old_file_name(json_file_path)
   
   # Do we have the HD version of the video? 
   parsed_old_file = load_json_file(json_file_path)
   
   if("hd_file" in parsed_old_file and cfe(hd_file)): 
      HD = 1
   else:
      HD = 0




   print("FIXED PATH ", fixed_json_file_path, "<br/>")
   sys.exit(0)

   analysed_name = name_analyser(fixed_json_file_path) 

   # Determine the folder where to put the files
   new_folder = get_new_archive_folder(analysed_name)

   # If the new_folder doesn't exist, we create it
   if not os.path.exists(new_folder):
      os.makedirs(new_folder)

   # We create the new json file from the old one
   json_content = convert(json_file_path)
 
   # Try to get the video (defined in the old json)
   parsed_json = load_json_file(json_file_path)

   # We need to determine the real start of the old json 
   # in order to get the proper name (ie with the date & time of the beginning of the video)
   # we need to start with getting the -trim.json file
 
   HD = False
   
   if "hd_video_file" in parsed_json:
      # We get the HD
      video_file = parsed_json['hd_video_file']
      HD = True
   elif "sd_video_file" in parsed_json:
      video_file = parsed_json['sd_video_file'] 
      # Since we don't have the HD video, we need to update the json
      json_content['info']['hd'] = 0
   else:
      print("IMPOSSIBLE TO RETRIEVE THE RELATED VIDEO")
      sys.exit(0)


   # Save the new JSON with the proper name 
   if(HD==True):
      analysed_name['name'] = analysed_name['name'].replace("SD","HD")

   json_file  = new_folder+analysed_name['name']

   save_json_file(json_file, json_content)
   if(display is True):
      print("JSON SAVED TO " + json_file)

   # Move the video file
   end_video_file = new_folder+analysed_name['name'].replace(".json",".mp4")
   shutil.copy2(video_file,end_video_file)
   if(display is True):
      print("VIDEO FILE SAVE TO " + end_video_file)

   return json_file,end_video_file