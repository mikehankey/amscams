import sys
import cgitb
import json
import sys
import os

from lib.FileIO import cfe, load_json_file, save_json_file
from lib.MeteorReduce_Tools import get_cache_path, name_analyser, EXT_CROPPED_FRAMES, new_crop_thumb, get_HD_frame, get_thumb


# Because of bad use of JSON, we need to know the index of the values inside arrays 
INDEX_OF_FRAME_NUMBER_IN_meteor_frame_data  = 1
HD_X_meteor_frame_data  = 2
HD_Y_meteor_frame_data  = 3


# Create new cropped frame
def create_thumb(form):

   # Debug
   cgitb.enable()     

   # Get values
   org_frame = form.getvalue('src')
   x = form.getvalue(x)  
   y = form.getvalue(y)  
   frame_id = form.getvalue(fr_id)  

   json_file = form.getvalue('json_file')

   # Analyse the name
   analysed_name = name_analyser(json_file)
   
   # Create thumd destination
   destination =  get_cache_path(analysed_name,"cropped")+analysed_name['name_w_ext']+EXT_CROPPED_FRAMES+str(frame_id)+".png"

   print(json.dumps({'fr':new_crop_thumb(org_frame,int(x),int(y),dest)}))
     

# Get HD Frame
# return the path to the given HD frames  
def get_frame(form):

   # Debug
   cgitb.enable()     

   json_file = form.getvalue('json_file')
   fn = form.getvalue('fr') # The frame ID

   # Analyse the name
   analysed_name = name_analyser(json_file)

   # We should test if get_HD_frame's output is empty as the HD Frames
   # are all created by default on page load (recude2 page)
   # if they don't exist
   the_frame = get_HD_frame(analysed_name,fn)
   the_frame = the_frame[0]
   toReturn = {'id':fn, 'full_fr':the_frame}
  
   print(json.dumps(toReturn))


 

# Update one frame at a time
def update_frame(form):

   # Debug
   cgitb.enable()     

   # Get Data 
   json_file = form.getvalue("meteor_json_file")
   mr = load_json_file(json_file)

   # Analyse the name
   analysed_name = name_analyser(json_file)

   resp = {}
   resp['error'] = []
   
   fn = form.getvalue("fn")
   x = form.getvalue("x")
   y = form.getvalue("y")

   if "meteor_frame_data" in mr:
      for ind, frame in enumerate(mr['meteor_frame_data']): 
         if int(frame[INDEX_OF_FRAME_NUMBER_IN_meteor_frame_data]) == int(fn):
            # It needs to be updated here!!
            frame[HD_X_meteor_frame_data] = int(x)
            frame[HD_Y_meteor_frame_data] = int(y)

            # Recreate the corresponding thumb
            original_HD_frame = get_HD_frame(analysed_name,fn)   
            destination_cropped_frame = get_thumb(analysed_name,fn)    

            if(len(original_HD_frame)!=0 and len(destination_cropped_frame)!=0):  
               new_crop_thumb(original_HD_frame[0],int(x),int(y),destination_cropped_frame[0])
            else:
               resp['error'].append("Impossible to update the frame " + str(fn))
   
   # We update the JSON 
   save_json_file(json_file, mr)
   
   resp['msg'] = "frame  updated."  
   
   # We compute the new stuff from the new meteor position within frames
   os.system("cd /home/ams/amscams/pythonv2/; ./reducer3.py cm " + json_file + " > /mnt/ams2/tmp/rrr.txt") 
   os.system("cd /home/ams/amscams/pythonv2/; ./reducer3.py cm " + json_file + " > /mnt/ams2/tmp/rrr.txt") 

   print(json.dumps(resp))


# Update multiple frames 
def update_multiple_frames(form):
   
   # Debug
   cgitb.enable()  
   
   # Get Data 
   json_file = form.getvalue("meteor_json_file")
   all_frames_to_update = json.loads(form.getvalue("frames") )
   
   mr = load_json_file(json_file)

   # Analyse the name
   analysed_name = name_analyser(json_file)

   resp = {}
   resp['error'] = []
 
   # Update meteor_frame_data
   for val in all_frames_to_update:  

      if "meteor_frame_data" in mr:
         for ind, frame in enumerate(mr['meteor_frame_data']):
            if int(frame[INDEX_OF_FRAME_NUMBER_IN_meteor_frame_data]) == int(val['fn']):
               # It needs to be updated here!!
               frame[HD_X_meteor_frame_data] = int(val['x'])
               frame[HD_Y_meteor_frame_data] = int(val['y'])

               # Recreate the corresponding thumb
               original_HD_frame = get_HD_frame(analysed_name,val['fn'])   
               destination_cropped_frame = get_thumb(analysed_name,val['fn'])    

               if(len(original_HD_frame)!=0 and len(destination_cropped_frame)!=0): 
                  new_crop_thumb(original_HD_frame[0],int(val['x']),int(val['y']),destination_cropped_frame[0])
               else:
                  resp['error'].append("Impossible to update the frame " + str(int(val['fn'])))
   
         

   # We update the JSON 
   save_json_file(json_file, mr)
   
   resp['msg'] = "frames updated."  
   
   # We compute the new stuff from the new meteor position within frames
   os.system("cd /home/ams/amscams/pythonv2/; ./reducer3.py cm " + json_file + " > /mnt/ams2/tmp/rrr.txt") 
   os.system("cd /home/ams/amscams/pythonv2/; ./reducer3.py cm " + json_file + " > /mnt/ams2/tmp/rrr.txt") 

   print(json.dumps(resp))




# Delete a frame
# Input = the meteor json file & the frame #
def delete_frame(form):
 
   # Debug
   cgitb.enable() 

   # Frame Number
   fn = form.getvalue("fn")

   # JSON File
   meteor_file = form.getvalue("meteor_json_file")
   meteor_json = load_json_file(meteor_file)

   # Update meteor_frame_data
   if "meteor_frame_data" in meteor_json:
      for ind, frame in enumerate(meteor_json['meteor_frame_data']):
         if int(frame[INDEX_OF_FRAME_NUMBER_IN_meteor_frame_data]) == int(fn):
            meteor_json['meteor_frame_data'].pop(ind)  
         
   # Update metframes
   if "metframes" in meteor_json:     
      meteor_json['metframes'].pop(fn, None)
   
   response = {}
   response['message'] = 'frame deleted'
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
