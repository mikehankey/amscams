import json

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