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

         # We need to create the entry in meteor_frame_data       
         new_entry = {
            'dt': dt,
            'x': int(x),
            'y': int(y),
            'fn': int(fn),
            'az': Az_DEFAULT,
            'el': El_DEFAULT,
            'ra': Ra_DEFAULT,
            'dec': Dec_DEFAULT,
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
   
   # check if there are zero stars selected and zero in cat_img
   if cfe(meteor_red_file) == 1:

      meteor_red = load_json_file(meteor_red_file)

      if points is None :
         print("POINT IS NONE")
         cmd = "cd /home/ams/amscams/pythonv2/; ./autoCal.py imgstars " + meteor_red_file + " > /mnt/ams2/tmp/trs.txt"
         #print(cmd)
         os.system(cmd)

   meteor_mode = 0
   if cfe(meteor_red_file) == 1 and "reduced" in meteor_red_file:
      meteor_red = load_json_file(meteor_red_file)
      if "cal_params" in meteor_red:
         cal_params = meteor_red['cal_params']
         meteor_mode = 1
         cal_params_file = ""
         if "cat_image_stars" not in cal_params:
            mp4 = meteor_red_file.replace("-reduced.json", ".mp4")
            #os.system("cd /home/ams/amscams/pythonv2/; ./autoCal.py imgstars " + mp4)
            meteor_red = load_json_file(meteor_red_file)

         if "cat_image_stars" in cal_params:

            clean_close_stars = remove_dupe_cat_stars(cal_params['cat_image_stars'])
            cal_params['close_stars']  = clean_close_stars
            #cal_params['user_stars']  = cal_params['user_stars']
            
            #user_stars = cal_params['user_stars']
            user_stars = []
            used = {}
            for cstar in cal_params['cat_image_stars']:
               (iname,mag,ra,dec,tmp1,tmp2,px_dist,est_cat_x,est_cat_y,tmp3,tmp4,new_cat_x,new_cat_y,ix,iy,px_dist) = cstar
               key = str(ix) + "." + str(iy)
               here_now = 1
               if px_dist < 15:
                  for x,y in user_stars:
                     dst = calc_dist((x,y),(ix,iy))
                     if dst < 15:
                        here_now = 1
                  if here_now == 0:
                     user_stars.append((ix,iy))
            cal_params['user_stars']  = user_stars

            if "crop_box" in meteor_red:
               cal_params['crop_box']  = meteor_red['crop_box'] 
            if type == "first_load" or points is None:
               # this didn't work out the way we wanted it do. can delete
               if "cat_image_stars" not in cal_params:
                  video_json_file = video_file.replace(".mp4", ".json")
                  cmd = "cd /home/ams/amscams/pythonv2/; ./autoCal.py imgstars " + video_json_file + " > /mnt/ams2/tmp/trs.txt"
                  os.system(cmd)
               elif len(cal_params['cat_image_stars']) == 0:
                  video_json_file = video_file.replace(".mp4", ".json")
                  cmd = "cd /home/ams/amscams/pythonv2/; ./autoCal.py imgstars " + video_json_file + " > /mnt/ams2/tmp/trs.txt"
                  #os.system(cmd)

            
               print(json.dumps(cal_params))
               exit()
         (box_min_x,box_min_y,box_max_x,box_max_y) = define_crop_box(meteor_red['meteor_frame_data'])
         meteor_red['crop_box'] = (box_min_x,box_min_y,box_max_x,box_max_y) 

   if meteor_mode == 0:
      cal_params_file_orig = hd_stack_file.replace(".png", "-calparams.json")
      cpfo = cfe(cal_params_file_orig)

      user_stars = {}
      cal_params_file = form.getvalue("cal_params_file")

      if cal_params_file is None and cpfo == 0:
         cal_params_files = get_active_cal_file(hd_stack_file)
         cal_params_file = cal_params_files[0][0]
      elif cal_params_file is not None:
         cal_params_file = cal_params_file
      else:
         cal_params_file = cal_params_file_orig

   star_points = []
   if cfe(hd_stack_file) == 0:
      bad_hd = 1      
      print("BAD HD LINK! Try to fix...")

   #print("RED FILE:", meteor_red_file)
   user_points = {}
   if points is None:
      points = ""
      star_json = find_stars_ajax(json_conf, hd_stack_file, 0)
      
      #for x,y,mp in star_json['stars'][0:20]:
      #   star_points.append((x,y))
   else:
      temps = points.split("|")
      for temp in temps:
         if len(temp) > 0:
            (x,y) = temp.split(",")
            x,y = int(float(x)),int(float(y))
            x,y = int(x)+5,int(y)+5
            x,y = x*2,y*2
            if x >0 and y > 0 and x<1920 and y< 1080:


               star_points.append((x,y))
   points = star_points
   hd_stack_img = cv2.imread(hd_stack_file,0)
   points = pin_point_stars(hd_stack_img, points)

   for x,y in points:
      pk = str(x) + '.' + str(y)
      user_points[pk] = 1

   if meteor_mode == 0:
      user_stars['user_stars'] = points 
   else:
      cal_params['user_stars'] = points 
      user_stars = {}
      user_stars['user_stars'] = points 

   if meteor_mode == 0:
      if cfe(cal_params_file_orig) == 1:
         #print("CAL PARAMS:", cal_params_file_orig)
         cal_params = load_json_file(cal_params_file_orig)
      else:
         #print("CAL PARAMS:", cal_params_file)
         cal_params = load_json_file(cal_params_file)
   
   if meteor_mode == 1: 
      if 'crop_box' not in meteor_red:
         cal_params['crop_box'] = (0,0,0,0)
      else: 
         cal_params['crop_box'] = meteor_red['crop_box']
   else:
         cal_params['crop_box'] = (0,0,0,0)


   #else:
   #   user_star_file = hd_stack_file.replace("-stacked.png", "-user-stars.json")
   #   user_stars = load_json_file(user_star_file)
   #solved_file = cal_params_file.replace("-calparams.json", ".solved")
   #cal_params = load_json_file(cal_params_file)
   cal_params = default_cal_params(cal_params,json_conf)

   if 'parent' in cal_params:
      child = 1
   else:
      child = 0 
   #print("<HR>RA/DEC:", cal_params_file, child, cal_params['ra_center'], cal_params['dec_center'])
   if meteor_mode == 0:
      el1 = cal_params_file.split("/")
      el2 = hd_stack_file.split("/")
      temp1 = el1[-1]
      temp2 = el2[-1]
      temp1 = temp1[0:20]
      temp2 = temp2[0:20]
      if temp1 != temp2:
         child = 1
   else:
      child = 1

   #print("<HR>RA/DEC:", child, cal_params['ra_center'], cal_params['dec_center'])
   #print(cal_params['center_az'], cfe(solved_file))
   if child == 1:
      #update center/ra dec
      if "center_az" in cal_params :
         center_az = cal_params['center_az']
         center_el = cal_params['center_el']

         rah,dech = AzEltoRADec(center_az,center_el,hd_stack_file,cal_params,json_conf)
         rah = str(rah).replace(":", " ")
         dech = str(dech).replace(":", " ")
         ra_center,dec_center = HMS2deg(str(rah),str(dech))
      else:
         ra_center = cal_params['ra_center']
         dec_center = cal_params['dec_center']
      #print("RA/DEC ADJ:", ra_center, dec_center, "<HR>")
      #print("RA/DEC ORIG:", cal_params['ra_center'], cal_params['dec_center'], "<HR>")
      #print("CENTER AZ/EL:", center_az, center_el, "<HR>")
      cal_params['ra_center'] = ra_center
      cal_params['dec_center'] = dec_center

   #print("<HR>RA/DEC:", cal_params['ra_center'], cal_params['dec_center'])
   #print("<HR>", cal_params_file, "<HR>")
   if "imagew" not in cal_params:
      cal_params['imagew'] = 1920
      cal_params['imageh'] = 1080
   cat_stars = get_catalog_stars([], [], cal_params,"x",cal_params['x_poly'],cal_params['y_poly'],min=0)
   my_cat_stars = []
   my_close_stars = []


   for name,mag,ra,dec,new_cat_x,new_cat_y in cat_stars :
      dcname = str(name.decode("utf-8"))
      dbname = dcname.encode("utf-8")
      my_cat_stars.append((dcname,mag,ra,dec,new_cat_x,new_cat_y))
   #cal_params['cat_stars'] = my_cat_stars
   #cal_params['user_stars'] = user_stars
   total_match_dist = 0
   total_cat_dist = 0 
   total_matches = 0
   for ix,iy in user_stars['user_stars']:
   #   print(ix,iy)
      close_stars = find_close_stars((ix,iy), cat_stars) 
      for name,mag,ra,dec,new_cat_x,new_cat_y,six,siy,cat_dist in close_stars:
         dcname = str(name.decode("utf-8"))
         dbname = dcname.encode("utf-8")
         if meteor_mode == 0:
            new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(ix,iy,cal_params_file,cal_params,json_conf)
         else:
            new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(ix,iy,video_file,cal_params,json_conf)
         match_dist = abs(angularSeparation(ra,dec,img_ra,img_dec))
         ipk = str(six) + "." + str(siy)
         if ipk in user_points.keys() :
            my_close_stars.append((dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist))
         else:
            print(ipk,"not found<BR>", user_points.keys(), "<BR>")
         total_match_dist = total_match_dist + match_dist
         total_cat_dist = total_cat_dist + cat_dist
         total_matches = total_matches + 1


      #print(close_stars,"<BR>")
   #   print(close_stars, "<BR>")
   clean_close_stars = remove_dupe_cat_stars(my_close_stars)
   cal_params['close_stars'] = clean_close_stars 
   cal_params['cat_image_stars'] = clean_close_stars 
   #out = str(cal_params)
   #out = out.replace("'", "\"")
   #out = out.replace("(b", "(")
   this_cal_params_file = hd_stack_file.replace(".png", "-calparams.json")
   if meteor_mode == 0:
      cal_params['parent_cal'] = cal_params_file
   
   if total_matches > 0 :
      cal_params['total_res_deg'] = total_match_dist / total_matches
      cal_params['total_res_px'] = total_cat_dist / total_matches
   else:
      cal_params['total_res_deg'] = 9999
      cal_params['total_res_px'] = 9999
   cal_params['cal_params_file'] = this_cal_params_file
   cal_params['user_stars'] = user_stars['user_stars']

   # need to remove from cat stars any stars that are not on the users list. and then add them to a banned list for the file so they don't come back. 
   #print("NEED TO SAVE.")
   #if meteor_mode == 0:
   #   save_json_file(this_cal_params_file, cal_params) 
   if meteor_mode == 1:
      meteor_red['cal_params'] = cal_params
      meteor_red['manual_update'] = 1 
      save_json_file(meteor_red_file, meteor_red) 
   if meteor_mode == 0:
      meteor_red_file = meteor_red_file.replace(".png", "-calparams.json") 
      if type == 'hd_cal_detail':
         meteor_red_file = meteor_red_file.replace("reduced", "calparams")
      cal_params['manual_update'] = 1 
      save_json_file(meteor_red_file, cal_params) 
   print(json.dumps(cal_params))

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
