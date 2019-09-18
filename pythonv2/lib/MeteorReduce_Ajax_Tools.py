import sys
import cgitb
import json
import sys
import os

from lib.FileIO import cfe, load_json_file, save_json_file
from lib.MeteorReduce_Tools import get_cache_path, name_analyser, EXT_CROPPED_FRAMES, new_crop_thumb, get_HD_frame, get_thumb,  get_frame_time,Az_DEFAULT,El_DEFAULT, Ra_DEFAULT, Dec_DEFAULT, Intensity_DEFAULT, Maxpx_DEFAULT, W_DEFAULT, H_DEFAULT
 
# Create new cropped frame
# and add the corresponding info to the json file
def create_thumb(form):

   # Debug
   cgitb.enable()     

   # Get values
   org_frame = form.getvalue('src')
   x = int(form.getvalue('x'))
   y = int(form.getvalue('y'))
   frame_id = int(form.getvalue('fn'))

   json_file = form.getvalue('json_file')

   # Analyse the name
   analysed_name = name_analyser(json_file)
   
   # Create thumb destination
   dest =  get_cache_path(analysed_name,"cropped")+analysed_name['name_w_ext']+EXT_CROPPED_FRAMES+str(frame_id)+".png"

   # Update the JSON file accordingly
   # And create the frame
   #print("FROM CREATE THUMB WE SEND")
   #print(str(form))
   resp_frame = update_frame(form, True)

   print(json.dumps({'fr':new_crop_thumb(org_frame,x,y,dest),'resp': resp_frame}))
     
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
def update_frame(form, AjaxDirect = False):

   # Debug
   cgitb.enable()     

   # Update or creation
   update = False

   # Get Data 
   json_file = form.getvalue("json_file")
   mr = load_json_file(json_file)

   # Analyse the name
   analysed_name = name_analyser(json_file)

   resp = {}
   resp['error'] = []
   
   fn = form.getvalue("fn")
   x = form.getvalue("x")
   y = form.getvalue("y")
 
   # Recreate the corresponding thumb
   original_HD_frame = get_HD_frame(analysed_name,fn)   
   destination_cropped_frame = get_thumb(analysed_name,fn)  
   thumb_path = ''

   if(len(destination_cropped_frame)==0):
      # It's a creation
      destination_cropped_frame = []
      destination_cropped_frame.append(get_cache_path(analysed_name,"cropped")+"*"+EXT_CROPPED_FRAMES+str(fn)+".png")


   # We try to update the json file
   if "frames" in mr: 

      # FOR THE UDPDATES
      for ind, frame in enumerate(mr['frames']): 
         if int(frame['fn']) == int(fn):
             # It needs to be updated here!!
            frame['x'] = int(x)
            frame['y'] = int(y)
            update = True

      # FOR THE CREATION
      if(update is False):

         # Get the Frame time (as a string)
         dt = get_frame_time(mr,fn)

         # Get the new RA/Dec 
         new_x, new_y, RA, Dec, az, el =  XYtoRADec(int(x),int(y),analysed_name,json_file)

         # We need to create the entry in meteor_frame_data       
         new_entry = {
            'dt': dt,
            'x': int(x),
            'y': int(y),
            'fn': int(fn),
            'az': az,
            'el': el,
            'ra': RA,
            'dec': Dec,
            'intensity': Intensity_DEFAULT,
            'max_px': Maxpx_DEFAULT,
            'w': W_DEFAULT, 
            'h': H_DEFAULT
         }
         mr['frames'].append(new_entry)
 

   if(len(original_HD_frame)!=0 and len(destination_cropped_frame)!=0):  
      thumb_path = new_crop_thumb(original_HD_frame[0],int(x),int(y),destination_cropped_frame[0])
   else:
      resp['error'].append("Impossible to update the frame " + str(fn))

   # If it wasn't an update, it's a creation
   if(update == False and len(resp['error'])==0):
      # We need to create the entry in the json file
      resp['msg'] = "frame updated (but the JSON has NOT been updated yet since I need a small function for that X,Y,json =>). You can see the new thumb here: <div style='margin:2rem auto'><a href='" + thumb_path +"' target='_blank'><img src='"+thumb_path+"' style='display:block'/></a></div>"

   # We update the JSON 
   save_json_file(json_file, mr)
   
   # We compute the new stuff from the new meteor position within frames
   os.system("cd /home/ams/amscams/pythonv2/; ./reducer3.py cm " + json_file + " > /mnt/ams2/tmp/rrr.txt") 
   os.system("cd /home/ams/amscams/pythonv2/; ./reducer3.py cm " + json_file + " > /mnt/ams2/tmp/rrr.txt") 

   # Depending on how the function is used we can return the resp or display it as JSON
   if(AjaxDirect == True):
      return resp 
   else:
      print(json.dumps(resp))

# Update multiple frames 
def update_multiple_frames(form):
   
   # Debug
   cgitb.enable()  
   
   # Get Data 
   json_file = form.getvalue("json_file")
   all_frames_to_update = json.loads(form.getvalue("frames") )
   
   mr = load_json_file(json_file)

   # Analyse the name
   analysed_name = name_analyser(json_file)

   resp = {}
   resp['error'] = []
 
   # Update meteor_frame_data
   for val in all_frames_to_update:  

      if "frames" in mr:
         for ind, frame in enumerate(mr['frames']):
            if int(frame['fn']) == int(val['fn']):
               # It needs to be updated here!!
               frame['x'] = int(val['x'])
               frame['y'] = int(val['y'])

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
   meteor_file = form.getvalue("json_file")
   meteor_json = load_json_file(meteor_file)

   # TODO: DELETE ALSO THE CORRESPONDING THUMB HERE?

   # Update frames
   if "frames" in meteor_json:
      for ind, frame in enumerate(meteor_json['frames']):
         if int(frame['fn']) == int(fn):
            meteor_json['frames'].pop(ind)  
         
   response = {}
   response['message'] = 'frame #' + str(fn) + ' deleted'
   save_json_file(meteor_file, meteor_json)
   print(json.dumps(response))

# Update Catalog Stars
def update_cat_stars(form):
   
   # Get the values from the form
   hd_stack_file = form.getvalue("hd_stack_file")   # Stack
   points = form.getvalue("points")                 # All Stars points on the canvas
   type = form.getvalue("type")                     # ? - 'nopick' is the default option
   video_file = form.getvalue("video_file")         # Video file
   cal_params = None                                # ????
   meteor_red_file = form.getvalue("json_file")     
   
   # We parse the JSON
   if cfe(meteor_red_file) == 1:
      meteor_red = load_json_file(meteor_red_file)
   else:
      return "error JSON"

   # check if there are zero stars selected and zero in cat_img
   if points is None : 
      # I guess this function automatically find the stars
      cmd = "cd /home/ams/amscams/pythonv2/; ./autoCal.py imgstars " + video_file + " > /mnt/ams2/tmp/trs.txt"
      os.system(cmd)
      print(cmd)

   meteor_mode = 0  #???


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

      # Stars
      if 'calib' not in mr or 'stars' not in mr['calib']:
      
         rsp['status'] = 0
      
      else:

         # Copy original 
         sc = 0
  
         for star in mr['calib']['stars']:  
               max_res_px = float(max_res_px) + float(star["dist_px"])
               sc += 1 

         total_res_px  = max_res_px/ sc 
     
         mr['calib']['device']['total_res_px']  = total_res_px
         mr['calib']['device']['total_res_deg'] = total_res_px/mr['calib']['device']['scale_px'] 
         
         # Pass to JSON
         rsp['calib'] = mr['calib'] 

         # New Meteor Frame Data
         new_mfd = []
         
         if "frames" in mr: 
            # The frames have to be in the proper order!
            #temp = sorted(mr['frames'], key=lambda x: int(x[1]), reverse=False)
  
            # Get the folder where the thumbs are: 
            analysed_name = name_analyser(json_file)
            thumb_folder = get_cache_path(analysed_name,'thumbs') 
  
            for frame_data in mr['frames']:      
              
               # Pass the path to frame to JS
               path_to_frame = thumb_folder + analysed_name['name_w_ext']  + EXT_CROPPED_FRAMES + str(frame_data['fn']) + ".png"

               tmp_frame = frame_data
               tmp_frame['path_to_frame'] =path_to_frame

               # Add the frame with path to frame (thumb)
               new_mfd.append(tmp_frame) 

            rsp['frames'] = new_mfd
          
      rsp['status'] = 1
  
   else: 
      rsp['status'] = 0
         

   print(json.dumps(rsp))
