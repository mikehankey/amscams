# coding: utf-8
import sys  
import cgitb
import json
import os
import cv2
import numpy as np
import ephem 
import math
import chardet
import json

import lib.Decoded_BrightStar_Data as bsd

from lib.FileIO import cfe, load_json_file, save_json_file
from lib.REDUCE_VARS import *
from lib.MeteorReduce_Tools import get_HD_frames, get_cache_path, name_analyser, new_crop_thumb, get_HD_frame, get_thumb, get_frame_time, generate_cropped_frame
from lib.MeteorReduce_Calib_Tools import XYtoRADec
from lib.Old_JSON_converter import get_analysed_name
from lib.UtilLib import convert_filename_to_date_cam, angularSeparation, date_to_jd
from lib.CalibLib import find_close_stars
from lib.VIDEO_VARS import HD_W, HD_H
from lib.MeteorReduce_ApplyCalib import apply_calib

import io,sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
 
mybsd = bsd.Decoded_BrightStar_Data()
bright_stars = mybsd.bright_stars
 

# Used for changing the background of the canvas
# This function returns all the HD frames of a detection
# WARNING RETURNS ONLY THE 20 first and 20 last frames
def get_all_HD_frames(json_value):
 
   # Get the HD frames 
   # False=  we don't clear the cache
   HD_frames = get_HD_frames(name_analyser(json_value),False)
   
   if len(HD_frames)>=12:
      HD_frames = HD_frames[:6] + HD_frames[6:]
   
   # Return JSON
   print(json.dumps({'res':HD_frames[:29]})) 


# Create new cropped frame
# and add the corresponding info to the json file
def create_thumb(form):

   # Debug
   cgitb.enable()     

   # Get values
   org_frame = form.getvalue('src')
   x = int(form.getvalue('x'))
   y = int(form.getvalue('y'))
   frame_id = int(form.getvalue('fn')) # HD ID
   sd_frame_id = int(form.getvalue('sd_fn')) # SD ID
  
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
   fn = form.getvalue('fr') # The frame ID (SD!!)
   sd_fn = fn

   # WARNING THE +1 and -1 below are due to the fact that
   # Mike doesn't count the same way

   # Analyse the name
   analysed_name = get_analysed_name(json_file)
 
   frame_hd_sd_diff = 0

   # If SD & HD have been sync, we need to get the proper HD frame
   tmp_json = load_json_file(json_file)
   if('sync' in tmp_json):
      if('sd_ind' in tmp_json['sync'] and 'hd_ind' in tmp_json['sync']):
         frame_hd_sd_diff = int(tmp_json['sync']['hd_ind']) - int(tmp_json['sync']['sd_ind']) + int(sd_fn) +1
  

   # We should test if get_HD_frame's output is empty as the HD Frames
   # are all created by default on page load (recude2 page)
   # if they don't exist
   the_frame = get_HD_frame(analysed_name,frame_hd_sd_diff)
 
   the_frame = the_frame[0]
   # For return
   frame_hd_sd_diff = frame_hd_sd_diff -1 
   
   toReturn = {'id':frame_hd_sd_diff, 'full_fr':the_frame,'sd_id': int(sd_fn)}
  
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
   sd_fn = form.getvalue("sd_fn")
   x = form.getvalue("x")
   y = form.getvalue("y")
 
   # Recreate the corresponding thumb
   original_HD_frame = get_HD_frame(analysed_name,fn) 


   #print("ANALYSED NAME<br/>")
   #print(analysed_name)
   #print("<br/>SD FN<br/>")
   #print(str(sd_fn))

   destination_cropped_frame = get_thumb(analysed_name,sd_fn)  

   
   #print("IN UPDATE FRAME<br/>")
   #print("<br/>SD " + str(sd_fn))
   #print("<br/>HD " + str(fn))
   #print("<br/>ORG HD FRAME<br/>")
   #print(original_HD_frame)
   #print("<br/>Destination_cropped_frame<br/>")
   #print(destination_cropped_frame)
 
   thumb_path = ''
   
   # SWITCH TO SD #
   fn = sd_fn

   if(len(destination_cropped_frame)==0):
      # It's a creation
      #print("IT IS A CREATION")
      destination_cropped_frame = []
      destination_cropped_frame.append(get_cache_path(analysed_name,"cropped")+analysed_name['name_w_ext']+EXT_CROPPED_FRAMES+str(fn)+".png")
      #print("<br>DESTINATION:<br>")
      #print(destination_cropped_frame)

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
         dt = get_frame_time(mr,fn,analysed_name)

         # Get the new RA/Dec 
         new_x, new_y, RA, Dec, az, el =  XYtoRADec(int(x),int(y),analysed_name,mr)

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

         # We sort the frames
         mr['frames'] = sorted(mr['frames'], key=lambda k: k['fn']) 
 

   if(len(original_HD_frame)!=0 and len(destination_cropped_frame)!=0):  
      thumb_path = new_crop_thumb(original_HD_frame[0],int(x),int(y),destination_cropped_frame[0])
   else:
      resp['error'].append("Impossible to update the frame " + str(fn))

   # If it wasn't an update, it's a creation
   if(update == False and len(resp['error'])==0):
      # We need to create the entry in the json file
      #resp['msg'] = "frame updated (but the JSON has NOT been updated yet since I need a small function for that X,Y,json =>). You can see the new thumb here: <div style='margin:2rem auto'><a href='" + thumb_path +"' target='_blank'><img src='"+thumb_path+"' style='display:block'/></a></div>"
      resp['msg'] = "New Frame created"

   # We reapply the calibration for the new frame
   apply_calib(json_file)

   # We update the JSON with valid dist_from_last 
   #os.system("cd /home/ams/amscams/pythonv2/; ./flex-detect.py ep " + json_file + " > /dev/null")
   # IT SHOULD BE DONE IN apply_calib NOW!

   # We update the JSON 
   save_json_file(json_file, mr)
  
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
   
   all_updated = []

   # We get the sync values
   frame_hd_sd_diff = 0
   if('sync' in mr):
      if('sd_ind' in mr['sync'] and 'hd_ind' in mr['sync']):
         frame_hd_sd_diff = int(mr['sync']['hd_ind']) - int(mr['sync']['sd_ind'])

   # I pass the SD frame #
   # I want the HD frame in get_HD_frame

   # Update meteor_frame_data
   for val in all_frames_to_update:  

      if "frames" in mr:
         for ind, frame in enumerate(mr['frames']):

            if int(frame['fn']) == int(val['fn']):
              
               # It needs to be updated here!!
               frame['x'] = int(val['x'])
               frame['y'] = int(val['y'])
  
               # Regenerate the proper cropped (thumb)
               original_HD_frame = get_HD_frame(analysed_name,int(val['fn'])+int(frame_hd_sd_diff)+1) 

               #print("ORIGINAL HD FRAME ")
               #print(original_HD_frame)
                 
               crop = generate_cropped_frame(analysed_name,mr,original_HD_frame[0],int(val['fn'])+int(frame_hd_sd_diff)+1,int(val['fn']),frame['x'],frame['y'])

          
               if(crop==False):
                  resp['error'].append("Impossible to update the frame " + str(int(val['fn'])))
               else: 
                  all_updated.append(crop)
               
   # We update the JSON 
   save_json_file(json_file, mr)
   
   # We compute the new stuff from the new meteor position within frames
   apply_calib(json_file)

   # We add the result
   resp['msg'] = json.dumps(all_updated)
 
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


# Find max px info from cnt
def cnt_max_px(cnt_img):
  

   #print("IN cnt_max_px<br>")
   # WTF???
   try:
      # Make sure we only have one channel here
      cnt_img = cv2.cvtColor(cnt_img, cv2.COLOR_BGR2GRAY)
      # No Float
      cnt_img = cnt_img.astype('uint8') 
      cnt_img = cv2.GaussianBlur(cnt_img, (7, 7), 0)
   except:
      cnt_img = cnt_img
   #print(cnt_img)
   #sys.exit(0)

   min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(cnt_img)
   return(max_loc, min_val, max_val)

# Pin point stars from user selection
def pin_point_stars(image, points):   

   # DEBUG
   cgitb.enable()
   
   star_points = []
   for x,y in points:
      x,y = int(x),int(y)
      y1 = y - 15
      y2 = y + 15
      x1 = x - 15
      x2 = x + 15
      cnt_img = image[y1:y2,x1:x2]
      ch,cw = cnt_img.shape
      #if True:
      try:
         max_pnt,max_val,min_val = cnt_max_px(cnt_img)
         mx,my = max_pnt
         mx = mx - 15
         my = my - 15
         x = x + mx
         y = y + my

         star_cnt_img = image[y-2:y+2,x-2:x+2]

         #star_bg_int = np.median(star_cnt_img) * star_cnt_img.shape[0] * star_cnt_img.shape[1]
         #star_int = int(np.sum(cnt_img) - star_bg_int)
         star_int = int(np.sum(star_cnt_img) )
         star_points.append((x,y,star_int))
      except:
         #print("PROB!", image.shape, x1,y1, x2,y2, "<BR>")
         missed_star = 1
         #sys.exit(0)

   return star_points 


def distort_xy_new(sx,sy,ra,dec,RA_center, dec_center, x_poly, y_poly, x_res, y_res, pos_angle_ref,F_scale=1):

   ra_star = ra
   dec_star = dec

   #F_scale = F_scale/10
   w_pix = 50*F_scale/3600
   #F_scale = 158 * 2
   #F_scale = 155
   #F_scale = 3600/16
   #F_scale = 3600/F_scale
   #F_scale = 1

   # Gnomonization of star coordinates to image coordinates
   ra1 = math.radians(float(RA_center))
   dec1 = math.radians(float(dec_center))
   ra2 = math.radians(float(ra_star))
   dec2 = math.radians(float(dec_star))
   ad = math.acos(math.sin(dec1)*math.sin(dec2) + math.cos(dec1)*math.cos(dec2)*math.cos(ra2 - ra1))
   radius = math.degrees(ad)
   
   try:
      sinA = math.cos(dec2)*math.sin(ra2 - ra1)/math.sin(ad)
      cosA = (math.sin(dec2) - math.sin(dec1)*math.cos(ad))/(math.cos(dec1)*math.sin(ad))
   except:
      sinA = 0
      cosA = 0
   theta = -math.degrees(math.atan2(sinA, cosA))
   theta = theta + pos_angle_ref - 90.0
   #theta = theta + pos_angle_ref - 90 + (1000*x_poly[12]) + (1000*y_poly[12])
   #theta = theta + pos_angle_ref - 90



   dist = np.degrees(math.acos(math.sin(dec1)*math.sin(dec2) + math.cos(dec1)*math.cos(dec2)*math.cos(ra1 - ra2)))

   # Calculate the image coordinates (scale the F_scale from CIF resolution)
   X1 = radius*math.cos(math.radians(theta))*F_scale
   Y1 = radius*math.sin(math.radians(theta))*F_scale
   # Calculate distortion in X direction
   dX = (x_poly[0]
      + x_poly[1]*X1
      + x_poly[2]*Y1
      + x_poly[3]*X1**2
      + x_poly[4]*X1*Y1
      + x_poly[5]*Y1**2
      + x_poly[6]*X1**3
      + x_poly[7]*X1**2*Y1
      + x_poly[8]*X1*Y1**2
      + x_poly[9]*Y1**3
      + x_poly[10]*X1*math.sqrt(X1**2 + Y1**2)
      + x_poly[11]*Y1*math.sqrt(X1**2 + Y1**2))

   # Add the distortion correction and calculate X image coordinates
   #x_array[i] = (X1 - dX)*x_res/384.0 + x_res/2.0
   new_x = X1 - dX + x_res/2.0

   # Calculate distortion in Y direction
   dY = (y_poly[0]
      + y_poly[1]*X1
      + y_poly[2]*Y1
      + y_poly[3]*X1**2
      + y_poly[4]*X1*Y1
      + y_poly[5]*Y1**2
      + y_poly[6]*X1**3
      + y_poly[7]*X1**2*Y1
      + y_poly[8]*X1*Y1**2
      + y_poly[9]*Y1**3
      + y_poly[10]*Y1*math.sqrt(X1**2 + Y1**2)
      + y_poly[11]*X1*math.sqrt(X1**2 + Y1**2))

   # Add the distortion correction and calculate Y image coordinates
   #y_array[i] = (Y1 - dY)*y_res/288.0 + y_res/2.0
   new_y = Y1 - dY + y_res/2.0
   #print("DENIS RA:", X1, Y1, sx, sy, F_scale, w_pix, dist)
   #print("DENIS:", X1, Y1, dX, dY, sx, sy, F_scale, w_pix, dist)
   #print("THETA:",theta)
   #print("DENIS:", sx,sy,new_x,new_y, sx-new_x, sy-new_y)
   return(new_x,new_y)

 

def get_catalog_stars(cal_params):
    # Debug
   cgitb.enable()    

   catalog_stars = []
   possible_stars = 0
 
   img_w = HD_W
   img_h = HD_H
   RA_center = float(cal_params['device']['center']['ra']) 
   dec_center = float(cal_params['device']['center']['dec']) 
   x_poly = cal_params['device']['poly']['x'] 
   y_poly = cal_params['device']['poly']['y']
   pos_angle_ref = float(cal_params['device']['angle']) 

   F_scale = 3600/float(cal_params['device']['scale_px'])
   fov_w = img_w / F_scale
   fov_h = img_h / F_scale
   fov_radius = np.sqrt((fov_w/2)**2 + (fov_h/2)**2)

   pos_angle_ref = cal_params['device']['angle']  
   bright_stars_sorted = sorted(bright_stars, key=lambda x: x[4], reverse=False)

   #print('<meta charset="UTF-8">')

   for bname, cname, ra, dec, mag in bright_stars_sorted: 
      if cname  :
         name = cname 
      else:
         name = bname.encode('utf-8')
         name = str(name.decode('utf-8'))     
          
      ang_sep = angularSeparation(ra,dec,RA_center,dec_center)
      
      if ang_sep < fov_radius and float(mag) < 5.5:
         new_cat_x, new_cat_y = distort_xy_new (0,0,ra,dec,RA_center, dec_center, x_poly, y_poly, img_w, img_h, pos_angle_ref,F_scale)
         possible_stars = possible_stars + 1
         catalog_stars.append((name,mag,ra,dec,new_cat_x,new_cat_y))
     
   return(catalog_stars)

# Update Catalog Stars
def update_cat_stars(form): 

   # Debug
   cgitb.enable()    

   # Get the values from the form
   star_points = []
   hd_stack_file = form.getvalue("hd_stack_file")   # Stack
   points = form.getvalue("points")                 # All Stars points on the canvas
   type = form.getvalue("type")                     # ? - 'nopick' is the default option
   video_file = form.getvalue("video_file")         # Video file 
   meteor_red_file = form.getvalue("json_file")     
   hd_image = cv2.imread(hd_stack_file, 0)

   # We parse the JSON
   if cfe(meteor_red_file) == 1:
      meteor_red = load_json_file(meteor_red_file)
   else:
      return "error JSON"
   
   meteor_mode = 0  #???
   
   if(points):
      temps = points.split("|")


      for temp in temps:
         if len(temp) > 0:
            (x,y) = temp.split(",")
            x,y = int(float(x)),int(float(y))
            x,y = int(x)+5,int(y)+5
            x,y = x*2,y*2
            if x >0 and y > 0 and x<HD_W and y< HD_H:
               star_points.append((x,y))
       
 
      star_points = pin_point_stars(hd_image, star_points) 

     
      # get the center ra,dec based on the center_az,el and the current timestamp from the file 
      ra,dec = AzEltoRADec(meteor_red['calib'], video_file)
      meteor_red['calib']['device']['center']['ra'] = ra
      meteor_red['calib']['device']['center']['dec'] = dec
      
      if('img_dim' not in meteor_red['calib']['device']):
         meteor_red['calib']['device']['img_dim'] = [HD_W,HD_H]
   
      cat_stars = get_catalog_stars(meteor_red['calib'])

       #my_cat_stars = []
      my_close_stars = []

      #for name,mag,ra,dec,new_cat_x,new_cat_y in cat_stars:  
      #   my_cat_stars.append((name,mag,ra,dec,new_cat_x,new_cat_y)) 


      my_close_stars = []
      cat_dist = []
      used_cat_stars = {}
      used_star_pos = {}
      for ix,iy,star_int in star_points:
         close_stars = find_close_stars((ix,iy), cat_stars) 

         if len(close_stars) == 1:
            name,mag,ra,dec,cat_x,cat_y,scx,scy,cat_star_dist = close_stars[0]
            new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(ix,iy,video_file,meteor_red['calib'])
            new_star = {}
            new_star['name'] = name 
            new_star['mag'] = mag
            new_star['ra'] = ra
            new_star['dec'] =  dec
            new_star['dist_px'] = cat_star_dist 
            new_star['intensity'] = star_int
            cat_dist.append(cat_star_dist)

            # The image x,y of the star (CIRCLE)
            new_star['i_pos'] = [ix,iy]
            # The lens distorted catalog x,y position of the star  (PLUS SIGN)
            new_star['cat_dist_pos'] = [new_x,new_y]
            # The undistorted catalog x,y position of the star  (SQUARE)
            new_star['cat_und_pos'] = [cat_x,cat_y]

            # distorted position should be the new_x, new_y and + symbol
            # only add if this star/position combo has not already be used
            used_star = 0
            this_rakey = str(ra) + str(dec)
            if this_rakey not in used_cat_stars:
               my_close_stars.append(new_star)
               used_cat_stars[this_rakey] = 1
  

 
      meteor_red['calib']['stars'] = my_close_stars
      meteor_red['calib']['device']['total_res_px'] = float(np.mean(cat_dist)) 
      meteor_red['calib']['device']['total_res_deg'] = (float(np.mean(cat_dist)) * float(meteor_red['calib']['device']['scale_px'])) / 3600
      # Update JSON File
      save_json_file(meteor_red_file, meteor_red)


   # Apply the new calibration
   apply_calib(meteor_red_file)
      
   # Return the new JSON
   js_f = load_json_file(meteor_red_file)

   print(json.dumps(js_f))



def XYtoRADec(img_x,img_y,timestamp_file,cp):
 
   try:
      # OLD Approach
      hd_datetime, hd_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(timestamp_file)
   except:
      # NEW Approach with name analyser
      hd_y = int(timestamp_file['year'])
      hd_m = int(timestamp_file['month'])
      hd_d = int(timestamp_file['day'])
      hd_h = int(timestamp_file['hour'])
      hd_M = int(timestamp_file['min'])
      hd_s = int(timestamp_file['sec'])
      cp = cp['calib']

   F_scale = 3600/float(cp['device']['scale_px'])
   #F_scale = 24

   total_min = (int(hd_h) * 60) + int(hd_M)
   day_frac = total_min / 1440 
   hd_d = int(hd_d) + day_frac
   jd = date_to_jd(int(hd_y),int(hd_m),float(hd_d))

   lat = float(cp['device']['lat'])
   lon = float(cp['device']['lng'])

   # Calculate the reference hour angle
   T = (jd - 2451545.0)/36525.0
   Ho = (280.46061837 + 360.98564736629*(jd - 2451545.0) + 0.000387933*T**2 \
      - (T**3)/38710000.0)%360

   x_poly_fwd = cp['device']['poly']['x_fwd']
   y_poly_fwd = cp['device']['poly']['y_fwd']
   
   dec_d = float(cp['device']['center']['dec']) 
   RA_d = float(cp['device']['center']['ra']) 

   dec_d = dec_d + (x_poly_fwd[13] * 100)
   dec_d = dec_d + (y_poly_fwd[13] * 100)

   RA_d = RA_d + (x_poly_fwd[14] * 100)
   RA_d = RA_d + (y_poly_fwd[14] * 100)

   pos_angle_ref = float(cp['device']['angle']) + (1000*x_poly_fwd[12]) + (1000*y_poly_fwd[12])

   # Convert declination to radians
   dec_rad = math.radians(dec_d)

   # Precalculate some parameters
   sl = math.sin(math.radians(lat))
   cl = math.cos(math.radians(lat))
   
   if('img_dim' in cp['device']):
      x_det = img_x - int(cp['device']['img_dim'][0])/2
      y_det = img_y - int(cp['device']['img_dim'][1])/2
   else:
      # HD by default
      x_det = img_x - int(HD_W)/2
      y_det = img_y - int(HD_H)/2

   dx = (x_poly_fwd[0]
      + x_poly_fwd[1]*x_det
      + x_poly_fwd[2]*y_det
      + x_poly_fwd[3]*x_det**2
      + x_poly_fwd[4]*x_det*y_det
      + x_poly_fwd[5]*y_det**2
      + x_poly_fwd[6]*x_det**3
      + x_poly_fwd[7]*x_det**2*y_det
      + x_poly_fwd[8]*x_det*y_det**2
      + x_poly_fwd[9]*y_det**3
      + x_poly_fwd[10]*x_det*math.sqrt(x_det**2 + y_det**2)
      + x_poly_fwd[11]*y_det*math.sqrt(x_det**2 + y_det**2))

   # Add the distortion correction
   x_pix = x_det + dx 

   #print("ORIG X:", img_x)
   #print("X DET:", x_det)
   #print("DX :", dx)
   #print("NEWX :", x_pix)

   dy = (y_poly_fwd[0]
      + y_poly_fwd[1]*x_det
      + y_poly_fwd[2]*y_det
      + y_poly_fwd[3]*x_det**2
      + y_poly_fwd[4]*x_det*y_det
      + y_poly_fwd[5]*y_det**2
      + y_poly_fwd[6]*x_det**3
      + y_poly_fwd[7]*x_det**2*y_det
      + y_poly_fwd[8]*x_det*y_det**2
      + y_poly_fwd[9]*y_det**3
      + y_poly_fwd[10]*y_det*math.sqrt(x_det**2 + y_det**2)
      + y_poly_fwd[11]*x_det*math.sqrt(x_det**2 + y_det**2))

   # Add the distortion correction
   y_pix = y_det + dy 

   x_pix = x_pix / F_scale
   y_pix = y_pix / F_scale

   ### Convert gnomonic X, Y to alt, az ###

   # Caulucate the needed parameters
   radius = math.radians(math.sqrt(x_pix**2 + y_pix**2))
   theta = math.radians((90 - pos_angle_ref + math.degrees(math.atan2(y_pix, x_pix)))%360)

   sin_t = math.sin(dec_rad)*math.cos(radius) + math.cos(dec_rad)*math.sin(radius)*math.cos(theta)
   Dec0det = math.atan2(sin_t, math.sqrt(1 - sin_t**2))

   sin_t = math.sin(theta)*math.sin(radius)/math.cos(Dec0det)
   cos_t = (math.cos(radius) - math.sin(Dec0det)*math.sin(dec_rad))/(math.cos(Dec0det)*math.cos(dec_rad))
   RA0det = (RA_d - math.degrees(math.atan2(sin_t, cos_t)))%360

   h = math.radians(Ho + lon - RA0det)
   sh = math.sin(h)
   sd = math.sin(Dec0det)
   ch = math.cos(h)
   cd = math.cos(Dec0det)

   x = -ch*cd*sl + sd*cl
   y = -sh*cd
   z = ch*cd*cl + sd*sl

   r = math.sqrt(x**2 + y**2)

   # Calculate azimuth and altitude
   azimuth = math.degrees(math.atan2(y, x))%360
   altitude = math.degrees(math.atan2(z, r))
 

   ### Convert alt, az to RA, Dec ###

   # Never allow the altitude to be exactly 90 deg due to numerical issues
   if altitude == 90:
      altitude = 89.9999

   # Convert altitude and azimuth to radians
   az_rad = math.radians(azimuth)
   alt_rad = math.radians(altitude)

   saz = math.sin(az_rad)
   salt = math.sin(alt_rad)
   caz = math.cos(az_rad)
   calt = math.cos(alt_rad)

   x = -saz*calt
   y = -caz*sl*calt + salt*cl
   HA = math.degrees(math.atan2(x, y))

   # Calculate the hour angle
   T = (jd - 2451545.0)/36525.0
   hour_angle = (280.46061837 + 360.98564736629*(jd - 2451545.0) + 0.000387933*T**2 - T**3/38710000.0)%360

   RA = (hour_angle + lon - HA)%360
   dec = math.degrees(math.asin(sl*salt + cl*calt*caz))

   ### ###

   return(x_pix+img_x,y_pix+img_y,RA,dec,azimuth,altitude)



def AzEltoRADec(cp, video_file):
   (hd_datetime, sd_cam, sd_date, sd_y, sd_m, sd_d, sd_h, sd_M, sd_s) = convert_filename_to_date_cam(video_file)
   #print("DATE:", hd_datetime)
   #print("CP:", cp['device']['alt'], cp['device']['lat'],cp['device']['lng'],"<BR>" )
   #print("CP:", cp['device']['center']['az'], cp['device']['center']['el'] , cp['device']['scale_px'], cp['device']['angle'], "<BR>")
   azr = np.radians(cp['device']['center']['az'])
   elr = np.radians(cp['device']['center']['el'])

   obs = ephem.Observer()
   obs.lat = str(cp['device']['lat'])
   obs.lon = str(cp['device']['lng'])
   obs.elevation = float(cp['device']['alt'])
   obs.date = hd_datetime
   ra,dec = obs.radec_of(azr,elr)
   rah = str(ra).replace(":", " ")
   dech = str(dec).replace(":", " ")
   ra_center,dec_center = HMS2deg(str(rah),str(dech))

   return(ra_center,dec_center)

def HMS2deg(ra='', dec=''):
  RA, DEC, rs, ds = '', '', 1, 1
  if dec:
    D, M, S = [float(i) for i in dec.split()]
    if str(D)[0] == '-':
      ds, D = -1, abs(D)
    deg = D + (M/60) + (S/3600)
    DEC = '{0}'.format(deg*ds)
  
  if ra:
    H, M, S = [float(i) for i in ra.split()]
    if str(H)[0] == '-':
      rs, H = -1, abs(H)
    deg = (H*15) + (M/4) + (S/240)
    RA = '{0}'.format(deg*rs)
  
  if ra and dec:
    return (RA, DEC)
  else:
    return RA or DEC

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

         if(sc>0):
            total_res_px  = max_res_px/ sc 
         else:
            total_res_px = 9999

         if('device' in mr['calib']):
            if('total_res_px' in mr['calib']['device']):
               mr['calib']['device']['total_res_px']  = total_res_px
            if('scale_px' in mr['calib']['device']):
               if(float(mr['calib']['device']['scale_px'])!=0):
                  mr['calib']['device']['total_res_deg'] = total_res_px/float(mr['calib']['device']['scale_px'])
          
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
               tmp_frame['path_to_frame'] = path_to_frame

               # Add the frame with path to frame (thumb)
               new_mfd.append(tmp_frame) 

            rsp['frames'] = new_mfd

         # Meteor Report Data (POINT SCORE)
         if('report' in mr):
            if('point_score' in mr['report']):
               rsp['point_score'] = str(mr['report']['point_score'])
           
      rsp['status'] = 1
  
   else: 
      rsp['status'] = 0
         

   print(json.dumps(rsp))
