import json
import re
import os
import glob
import shutil
import sys
import cgitb
from datetime import datetime,timedelta

from lib.WebCalib import get_active_cal_file
from lib.FileIO import load_json_file,save_json_file, cfe
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

# Analysed and old file (containing "-tr im")
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
def move_old_detection_to_archive(json_file_path, old_video_file, display=False):

   cgitb.enable()

   # We fix the old name to get the proper info
   fixed_json_file_path = fix_old_file_name(json_file_path)

   # Get the closest param files
   param_files = get_active_cal_file(fixed_json_file_path)

   
   if(cfe(param_files[0][0])==0):
      print("PARAM FILES " + param_files[0][0]  + " not found" )
      sys.exit(0)

   # We parse the param
   param_json = load_json_file(param_files[0][0])

   # We create a temporary clean name to get the calib['dt']
   clean_param_json_name = param_files[0][0].replace('-stacked-calparams.json','_HD.mp4')
   param_json_analysed_name = name_analyser(clean_param_json_name)
   calib_dt = get_datetime_from_analysedname(param_json_analysed_name)
   calib_dt = datetime.strftime(calib_dt, '%Y-%m-%d %H:%M:%S')
   

   # Do we have the device info in param_json?
   if('device_alt' in param_json):
      dev_alt = float(param_json['device_alt'])
      dev_lng = float(param_json['device_lng'])
      dev_lat = float(param_json['device_lat'])
   else:
      # We look in the ".json" file
      t = load_json_file(json_file_path)
      if('device_alt' in t):
         dev_alt = float(t['device_alt'])
         dev_lng = float(t['device_lng'])
         dev_lat = float(t['device_lat'])
      else:
         # We need to look in as6.json (!!!!)
         t = load_json_file(JSON_CONFIG)
         try:
            dev_alt = float(t['site']['device_alt'])
            dev_lng = float(t['site']['device_lng'])
            dev_lat = float(t['site']['device_lat'])
         except:
            print("IMPOSSIBLE TO FIND the devivec alt, lng and lat")
            sys.exit(0)

   new_calib = { "calib":  
      {  "dt":   calib_dt,
         "org_file_name": os.path.basename(json_file_path),  # In case something goes wrong
         "device": { 
            "alt":  dev_alt,
            "lat":  dev_lat,
            "lng":  dev_lng,
            "scale_px":  float(param_json['pixscale']),
            "poly": {
                  "y_fwd": param_json['y_poly_fwd'],
                  "x_fwd": param_json['x_poly_fwd'],
                  "y": param_json['y_poly'],
                  "x": param_json['x_poly']
            },
            "center": {
                  "az": float(param_json['center_az']),  
                  "ra": float(param_json['ra_center']), 
                  "el": float(param_json['center_el']),
                  "dec": float(param_json['dec_center']) 
            },
            "angle":  float(param_json['position_angle'])
         },
         "stars" : []
   }}
     
   # Do we have a HD video for this detection?
   video_file = old_video_file

   # We parse the json
   data_json = load_json_file(json_file_path)

   # We get the date info from the fixed name
   # tan = temp analysed name
   tan = name_analyser(fixed_json_file_path)
   
   # We search for the HD Video  
   #HD = 0
   #date_str = tan['year'] + '_' + tan['month']  + '_' + tan['day']
   #search_hd = glob.glob('/mnt/ams2/meteors/' + date_str + '/' + date_str + '_' + tan['hour'] + '_' + tan['min'] + '_' + '*' + 'HD-meteor.mp4' )

   #if(len(search_hd)>0):
   #   video_file = search_hd[0]
   #   HD = 1
   #else:

      # Search with min approx
   #   search_hd = glob.glob('/mnt/ams2/meteors/' + date_str + '/' + date_str + '_' + tan['hour'] + '_' + '*' + '_' + tan['cam_id'] +  '*' + 'HD-meteor.mp4' )
   #   if(len(search_hd)>0):
   #      video_file = search_hd[0]
   #      HD = 1
   #   else:
   #      print("VIDEO NOT FOUND - We searched for " + '/mnt/ams2/meteors/' + date_str + '/' + date_str + '_' + tan['hour'] + '_' + tan['min'] + '_' + '*' + 'HD-meteor.mp4')
   #      sys.exit(0)

   # We we didn't find the HD yet, we can try to search somewhere else???? (TODO)
   
   # If we don't have the HD, we assume we have the SD (???)

   # TODO: TEST IF IT'S REALLY A HD VIDEO
   HD =  1

   # We build the new "info"
   new_info = {
      "info": {
         "station": get_station_id(),
         "hd": HD, # We assume we have the HD vid by default for the moment
         "device": param_json_analysed_name['cam_id'],
         "dur": 9999,
         "max_peak": 9999
      }
   }


   # Determine the folder where to put the files
   new_folder = get_new_archive_folder(tan)

   # If the new_folder doesn't exist, we create it
   if not os.path.exists(new_folder):
      os.makedirs(new_folder)
 
  
   # We add the HD to the name if we have one
   # TODO: TEST IF IT'S HD!!!
   if(HD==1):
      tan['name'] = tan['name'].replace("SD","HD")
   
   #print("<BR>We will create the file " + tan['name'] +'<br>')
   #print("IN THE DIR " + new_folder)
   #print("<br/>AND WE WILL MOVE THE VIDEO " + video_file)
   #print("WITH THE NAME " + tan['name'].replace(".json",".mp4") )
   #print(" THERE<br/>")


   # Move the video file
   end_video_file = new_folder+tan['name'].replace(".json",".mp4")
   shutil.copy2(video_file,end_video_file)
   if(display is True):
      print("VIDEO FILE SAVE TO " + end_video_file)

   # Create the definitive json_content
   json_content = {}
   json_content['calib'] = new_calib['calib']
   json_content['info'] = new_info['info']
   json_content['frames'] = []
   
   #print( "<br/><br/><br/>"+ new_folder + tan['name'])

   # Save the new JSON file
   save_json_file(new_folder + tan['name'], json_content)
   if(display is True):
      print("JSON SAVED TO " + new_folder + tan['name'])
   
 

   return new_folder + tan['name'],end_video_file