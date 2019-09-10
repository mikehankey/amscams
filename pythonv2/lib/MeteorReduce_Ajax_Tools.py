import sys
import cgitb
import json

from lib.FileIO import cfe, load_json_file 
from lib.MeteorReduce_Tools import get_cache_path, name_analyser, EXT_CROPPED_FRAMES
 

# Delete a frame
# Input = the meteor json file & the frame #
def delete_frame(form):

   # Debug
   cgitb.enable()

   print("IN DELETE FRAME")

   # Frame Number
   fn = form.getvalue("fn")

   # JSON File
   meteor_file = form.getvalue("meteor_json_file")
   meteor_json = load_json_file(meteor_file)

   #print("DELETING FRAME #" + fn)
   #print("FROM " + meteor_file)

   # Update metframes
   new_metframes = []
   for frame in meteor_json['metframes']: 
      print(frame['fn'] + " vs " + fn + "<br/>")
      if(frame['fn']!=fn):  
         print("NOT SKIPPED <br>")
         new_metframes.append(frame)
       
      
   meteor_json['metframes'] = new_metframes
   print(meteor_json)
   sys.exit(0)
      
 
   # Rebuild all frame data
   new_frame_data = []
   for data in meteor_json['meteor_frame_data']:
      tfn = data[1]
      if str(fn) == str(tfn):
         skip = 1
      else:
         new_frame_data.append(data)
   meteor_json['meteor_frame_data'] = new_frame_data
   
   # Rebuild metframes
   if "metframes" in meteor_json:
      if fn in meteor_json['metframes']:
         meteor_json['metframes'].pop(fn)
   response = {}
   response['message'] = 'frame deleted'
   response['frame_data'] = new_frame_data
   save_json_file(meteor_file, meteor_json)
   print(json.dumps(response))


# Return the JSON Files from a given reduction
# with modified info
def get_reduction_info(json_file):

   # Debug
   cgitb.enable()
  
   # Cnters
   total_res_deg = 0 
   total_res_px = 0 
   max_res_deg = 0 
   max_res_px = 0 

   # Output
   rsp = {}

   if cfe(json_file) == 1:

      # We load the JSON
      mr = load_json_file(json_file) 

      if "cal_params" in mr:
         if "cat_image_stars" in mr['cal_params']:

            # Get all the stars and compute max_res_deg & max_res_px
            rsp['cat_image_stars'] = mr['cal_params']['cat_image_stars'] 
            sc = 0
            for star in mr['cal_params']['cat_image_stars']:
               (dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist) = star
               max_res_deg = float(max_res_deg) + float(match_dist)
               max_res_px = float(max_res_px) + float(cat_dist )
               sc = sc + 1

            if "total_res_px" in mr['cal_params']:
               rsp['total_res_px']  = mr['cal_params']['total_res_px']
               rsp['total_res_deg'] = mr['cal_params']['total_res_deg']

            elif len(mr['cal_params']['cat_image_stars']) > 0:
               rsp['total_res_px']  = max_res_px/ sc
               rsp['total_res_deg'] = (max_res_deg / sc)  

         new_mfd = []
         
         if "meteor_frame_data" in mr: 
            temp = sorted(mr['meteor_frame_data'], key=lambda x: int(x[1]), reverse=False)


            # Get the folder where the thumbs are: 
            analysed_name = name_analyser(json_file)
            thumb_folder = get_cache_path(analysed_name,'thumbs') 
  
            for frame_data in temp:      
               frame_time, fn, hd_x,hd_y,w,h,max_px,ra,dec,az,el = frame_data 

               # Pass the path to frame to JS
               path_to_frame = thumb_folder + analysed_name['name_w_ext']  + EXT_CROPPED_FRAMES + str(fn) + ".png"
               new_mfd.append((frame_time,fn,hd_x,hd_y,w,h,max_px,ra,dec,az,el,path_to_frame)) 

            rsp['meteor_frame_data'] = new_mfd
          
      rsp['status'] = 1
  
   else: 
      rsp['status'] = 0
         

   print(json.dumps(rsp))
