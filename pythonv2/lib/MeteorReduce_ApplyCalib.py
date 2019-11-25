import json
import cgi

from lib.FileIO import load_json_file, save_json_file
from lib.MeteorReduce_Calib_Ajax_Tools import XYtoRADec
from lib.MeteorReduce_Tools import name_analyser


# AJAX CALL
def apply_calib_ajax(form): 
   json_file = form.getvalue('json_file') 
  
   apply_calib_ajax(json_file)


# Re-apply a calibration to a json file
def apply_calib(json_file):

   json_data = load_json_file(json_file)
   new_frames = []

   if('frames' in json_data):
      for frame in json_data['frames']:
         print("BEFORE")
         print(frame)
         new_x,new_y,RA,Dec,AZ,el = XYtoRADec(frame['x'],frame['y'],name_analyser(json_file),json_data)
         new_frame = frame
         new_frame['dec'] = Dec
         new_frame['ra'] = RA
         new_frame['az'] = AZ
         new_frame['el'] = el
         new_frames.append(new_frame)
         print("AFTER")
         print(new_frame)
   
      json_data['frames'] = new_frames   

      # We save the file
      save_json_file(json_file,json_data)
 
   return json.dumps(load_json_file(json_file) ,sort_keys=True,indent=4)