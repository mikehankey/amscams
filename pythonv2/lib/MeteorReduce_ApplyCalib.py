import json 
import os
import sys
from lib.FileIO import load_json_file, save_json_file
from lib.MeteorReduce_Calib_Ajax_Tools import XYtoRADec
from lib.MeteorReduce_Tools import name_analyser, get_frame_time


# AJAX CALL
def apply_calib_ajax(form): 
   json_file = form.getvalue('json_file') 
   apply_calib(json_file)


# Re-apply a calibration to a json file
def apply_calib(json_file):

   json_data = load_json_file(json_file)
   new_frames = []
   tmp_dt = []

   if('frames' in json_data):

      analysed_name = name_analyser(json_file)

      for frame in json_data['frames']:
          
         new_x,new_y,RA,Dec,AZ,el = XYtoRADec(frame['x'],frame['y'],analysed_name,json_data)
         new_frame = frame
         new_frame['dec'] = Dec
         new_frame['ra'] = RA
         new_frame['az'] = AZ
         new_frame['el'] = el
         tmp_dt.append(frame['dt'])
         new_frames.append(new_frame) 
   
      json_data['frames'] = new_frames   
 
      # Here we check if there's an issue with the dt
      if(list(set(tmp_dt))!=tmp_dt):
         
         new_frames = []

         # It means we have a Date & Time issue!
         # We need to fix it
         for frame in json_data['frames']:
            new_frame = frame
            new_frame['dt'] = get_frame_time(json_file,frame['fn'],analysed_name) 
            new_frames.append(new_frame) 
   
         json_data['frames'] = new_frames   


      # We save the file
      save_json_file(json_file,json_data)
 
      # run eval points to update dist_from_last and point_score
      os.system("cd /home/ams/amscams/pythonv2/; ./flex-detect.py ep " + json_file + ">/dev/null")
 
   return json.dumps(load_json_file(json_file) ,sort_keys=True,indent=4)
