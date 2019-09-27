import json
import re
import os
import glob
import shutil

from lib.FileIO import load_json_file,save_json_file
from lib.MeteorReduce_Tools import name_analyser, get_cache_path
from lib.REDUCE_VARS import *


# Get a new folder in meteor_archive
# from an old json file
def get_new_archive_folder(analysed_name):
   return METEOR_ARCHIVE + analysed_name['station_id'] + "/" + METEOR + analysed_name['year'] + "/" + analysed_name['month'] + "/" + analysed_name['day'] + "/"
   
# Fix the old files names that contains "-trim"
# so we can use the usual name_analyser
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

# Get new info (device & detection info) from an old JSON version
def get_new_info(json_f):
   return  {
      "info": {
         "station": json_f['station_name'],
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

   return {"stars": json.dumps(new_stars)}

# Convert a whole old JSON file following the new DTD
def convert(json_file_path):
   
   json_f = load_json_file(json_file_path)
   info = get_new_info(json_f)
   calib = get_new_calib(json_f)
   stars = get_new_stars(json_f)

   new_json = {"info": info['info'],"calib": calib['calib'],"stars": stars['stars']}
   
   return new_json


# Move new JSON file and HD video file to meteor_archive
# with a proper name, and in the proper folder
def move_old_to_archive(json_file_path):

   #ex:/mnt/ams2/meteors/2019_09_27/2019_09_27_05_27_46_000_010040-trim0277-reduced.json

   # We fix the old name to get the proper info
   fixed_json_file_path = fix_old_file_name(json_file_path)
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

   save_json_file(new_folder+analysed_name['name'], json_content)


   print("JSON SAVED TO " + new_folder+analysed_name['name'])

   # Move the video file
   shutil.copy2(video_file,new_folder+analysed_name['name'].replace(".json",".mp4"))
   print("VIDEO FILE SAVE TO " + new_folder+analysed_name['name'].replace(".json",".mp4") )
