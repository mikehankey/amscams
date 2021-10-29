import datetime
import os
import math
import cv2
import random
import numpy as np
from detectlib import eval_cnt
from scipy import signal
from scipy.interpolate import splrep, sproot, splev
from detectlib import mask_frame
from pathlib import Path
import json
import glob
import brightstardata as bsd
mybsd = bsd.brightstardata()
bright_stars = mybsd.bright_stars

json_file = open('../conf/as6.json')
json_str = json_file.read()
json_conf = json.loads(json_str)
proc_dir = json_conf['site']['proc_dir']
base_cal_dir = "/mnt/ams2/cal/"


def adjustLevels(img_array, minv, gamma, maxv, nbits=None):
    """ Adjusts levels on image with given parameters.
    Arguments:
        img_array: [ndarray] Input image array.
        minv: [int] Minimum level.
        gamma: [float] gamma value
        Mmaxv: [int] maximum level.
    Keyword arguments:
        nbits: [int] Image bit depth.
    Return:
        [ndarray] Image with adjusted levels.
    """

    if nbits is None:
        
        # Get the bit depth from the image type
        nbits = 8*img_array.itemsize


    input_type = img_array.dtype

    # Calculate maximum image level
    max_lvl = 2**nbits - 1.0

    # Limit the maximum level
    if maxv > max_lvl:
        maxv = max_lvl

    # Check that the image adjustment values are in fact given
    if (minv is None) or (gamma is None) or (maxv is None):
        return img_array

    minv = minv/max_lvl
    maxv = maxv/max_lvl
    interval = maxv - minv
    invgamma = 1.0/gamma

    # Make sure the interval is at least 10 levels of difference
    if interval*max_lvl < 10:

        minv *= 0.9
        maxv *= 1.1

        interval = maxv - minv
        


    # Make sure the minimum and maximum levels are in the correct range
    if minv < 0:
        minv = 0

    if maxv*max_lvl > max_lvl:
        maxv = 1.0
    

    img_array = img_array.astype(np.float64)

    # Reduce array to 0-1 values
    img_array = np.divide(img_array, max_lvl)

    # Calculate new levels
    img_array = np.divide((img_array - minv), interval)

    # Cut values lower than 0
    img_array[img_array < 0] = 0

    img_array = np.power(img_array, invgamma)

    img_array = np.multiply(img_array, max_lvl)

    # Convert back to 0-maxval values
    img_array = np.clip(img_array, 0, max_lvl)


    # Convert the image back to input type
    img_array.astype(input_type)
        

    return img_array

def gammaCorrection(intensity, gamma, bp=0, wp=255):
    # TAKEN FROM RMS/DENIS VIDA 
    """ Correct the given intensity for gamma. 
        
    Arguments:
        intensity: [int] Pixel intensity
        gamma: [float] Gamma.
    Keyword arguments:
        bp: [int] Black point.
        wp: [int] White point.
    Return:
        [float] Gamma corrected image intensity.
    """

    if intensity < 0:
        intensity = 0

    x = (intensity - bp)/(wp - bp)

    if x > 0:

        # Compute the corrected intensity
        return bp + (wp - bp)*(x**(1.0/gamma))

    else:
        return bp


def find_image_stars(cal_img):
   if cal_img.shape == 3:
      cal_img= cv2.cvtColor(cal_img, cv2.COLOR_BGR2GRAY)
   cal_img = cv2.GaussianBlur(cal_img, (7, 7), 0)
   #cal_img= cv2.convertScaleAbs(cal_img)
   cal_img = cv2.dilate(cal_img, None , iterations=4)
   (_, cnts, xx) = cv2.findContours(cal_img.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
   star_pixels = []
   non_star_pixels = []
   cloudy_areas = []
   for (i,c) in enumerate(cnts):
      x,y,w,h= cv2.boundingRect(cnts[i])
      if w > 1 and h > 1:
         star_pixels.append((x,y,w,h))
   return(star_pixels)

def find_image_stars_thresh(cal_img):
   if cal_img.shape == 3:
      cal_img= cv2.cvtColor(cal_img, cv2.COLOR_BGR2GRAY)
   cal_img = cv2.GaussianBlur(cal_img, (7, 7), 0)
   #cal_img= cv2.convertScaleAbs(cal_img)
   #cal_img = cv2.dilate(cal_img, None , iterations=4)
   avg_pix = np.mean(cal_img)

   best_thresh = find_best_thresh(cal_img, avg_pix)
   _, thresh_img = cv2.threshold(cal_img, best_thresh, 255, cv2.THRESH_BINARY)
   (_, cnts, xx) = cv2.findContours(thresh_img.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

   thresh_obj= cv2.convertScaleAbs(thresh_img)
   #cv2.imshow('pepe', thresh_img)
   #cv2.waitKey(0)

   #(_, cnts, xx) = cv2.findContours(cal_img.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
   star_pixels = []
   non_star_pixels = []
   cloudy_areas = []
   for (i,c) in enumerate(cnts):
      x,y,w,h= cv2.boundingRect(cnts[i])
      if w > 1 and h > 1:
         star_pixels.append((x,y,w,h))
   return(star_pixels)



def distort_xy_new(sx,sy,ra,dec,RA_center, dec_center, x_poly, y_poly, x_res, y_res, pos_angle_ref,F_scale=1):

   #print("INPUT", sx,sy,ra,dec,RA_center,dec_center,pos_angle_ref,F_scale)
   ra_star = ra
   dec_star = dec

   #F_scale = F_scale/10
   w_pix = 50*F_scale/3600
   #F_scale = 158 * 2
   #F_scale = 155
   #F_scale = 3600/16
   #F_scale = 3600/F_scale 
   #F_scale = 1

   RA_center = RA_center + (x_poly[12] * 100)
   RA_center = RA_center + (y_poly[12] * 100)

   dec_center = dec_center + (x_poly[13] * 100)
   dec_center = dec_center + (y_poly[13] * 100)

   # Gnomonization of star coordinates to image coordinates
   ra1 = math.radians(float(RA_center))
   dec1 = math.radians(float(dec_center))
   ra2 = math.radians(float(ra_star))
   dec2 = math.radians(float(dec_star))
   ad = math.acos(math.sin(dec1)*math.sin(dec2) + math.cos(dec1)*math.cos(dec2)*math.cos(ra2 - ra1))
   radius = math.degrees(ad)
   sinA = math.cos(dec2)*math.sin(ra2 - ra1)/math.sin(ad)
   cosA = (math.sin(dec2) - math.sin(dec1)*math.cos(ad))/(math.cos(dec1)*math.sin(ad))
   theta = -math.degrees(math.atan2(sinA, cosA))
   #theta = theta + pos_angle_ref - 90.0
   theta = theta + pos_angle_ref - 90 + x_poly[14]
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


def distort_xy(x,y,img_w,img_h,center_off_x=0,center_off_y=0,undistort=0, strength=1):
   #print ("CENTER OFF: ", center_off_x, center_off_y)
   zoom = 1
   x_adj = 0
   y_adj = 0
   half_w = int(img_w/2) + center_off_x
   half_h = int(img_h/2) + center_off_y
   newX = x - half_w
   newY = y - half_h
   dist_to_center = calc_dist((x,y),(half_w,half_h))
   #print(dist_to_center)
   if 0 < dist_to_center <= 100:
      strength = strength * .01
   if 100 < dist_to_center <= 200:
      strength = strength * 1
   if 200 < dist_to_center <= 300:
      strength = strength * 1
   if 300 < dist_to_center <= 400:
      strength = strength * 1
   if 400 < dist_to_center <= 500:
      strength = strength * 1.1
   if 500 < dist_to_center <= 550:
      strength = strength * 1.5
   if 550 < dist_to_center <= 600:
      strength = strength * 1.6
   if 600 < dist_to_center <= 700:
      strength = strength * 1.3
   if 700 < dist_to_center <= 800 :
      strength = strength * 2.0
   if 800 < dist_to_center <= 875:
      strength = strength * 1.8
   if 875 < dist_to_center <= 900 :
      strength = strength * 1.6
   if 900 < dist_to_center <= 2000 :
      strength = strength * 1.7
   correctionRadius = math.sqrt(img_w ** 2 + img_h ** 2) / strength
   distance = math.sqrt(newX ** 2 + newY ** 2)
   r = distance / correctionRadius
   if r == 0:
      theta = 1
   else:
      theta = math.atan(r) / r
   if undistort == 1:
      sourceX = newX
      sourceY = newY
   if undistort == 0:
      sourceX = half_w + theta * newX * zoom
      sourceY = half_h + theta * newY * zoom
   else:
      newX = half_w + (sourceX / theta)
      newY = half_h + (sourceY / theta)
   sourceX = int(float(sourceX))
   sourceY = int(float(sourceY))
   newX = int(float(newX))
   newY = int(float(newY))
   if sourceY > img_h-1:
      sourceY = img_h-1
   if sourceX > img_w-1:
      sourceX = img_w-1
   if newY > img_h-1:
      newY = img_h-1
   if newX > img_w-1:
      newX = img_w-1
   return(sourceX,sourceY,newX,newY)


def get_time_for_file(file):
   el = file.split("/")
   last = el[-1]
   extra = last.split("-")
   fn = extra[0]

   hel = fn.split("_")
   return(hel[0],hel[1],hel[2],hel[3],hel[4],hel[5],hel[7])


def apply_masks(image, masks):
   for mask in masks:
      msx,msy,msw,msh = mask.split(",")
      image[int(msy):int(msy)+int(msh),int(msx):int(msx)+int(msw)] = 0
   return(image)


def convert_filename_to_date_cam(file):
   el = file.split("/")
   filename = el[-1]
   filename = filename.replace(".mp4" ,"")
   if "-" in filename:
      xxx = filename.split("-")
      filename = xxx[0]
   fy,fm,fd,fh,fmin,fs,fms,cam = filename.split("_")
   f_date_str = fy + "-" + fm + "-" + fd + " " + fh + ":" + fmin + ":" + fs
   f_datetime = datetime.datetime.strptime(f_date_str, "%Y-%m-%d %H:%M:%S")
   return(f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs)


def find_hd_file(sd_file):
   if "png" in sd_file:
      sd_file = sd_file.replace("-stacked.png", ".mp4")
      sd_file = sd_file.replace("/images", "")
   print("SD FILE: ", sd_file)
   (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(sd_file)

   glob_dir = "/mnt/ams2/HD/" + str(fy) + "_" + str(fm) + "_" + str(fd) + "_" + str(fh) + "_" + fmin + "*" + cam + "*.mp4"
   print(glob_dir)
   hdfiles = glob.glob(glob_dir)
   print(hdfiles)
   if len(hdfiles) > 0:
      return(hdfiles[0])
   else:
      return(0)


def magic_contrast(image):
   cv2.imwrite("/mnt/ams2/cal/tmp/temp.png", image)
   os.system("convert /mnt/ams2/cal/tmp/temp.png -sigmoidal-contrast 8 /mnt/ams2/cal/tmp/temp2.png")
   new_image = cv2.imread("/mnt/ams2/cal/tmp/temp2.png", 0)
   os.system("rm /mnt/ams2/cal/tmp/temp.png ")
   os.system("rm /mnt/ams2/cal/tmp/temp2.png ")
   #cv2.imshow('pepe', new_image)
   #cv2.waitKey(10)
   return(new_image)



def check_for_stars(file, cam_num, hd=0):

   image = cv2.imread(file, 0)
   image = magic_contrast(image)
   #cam_num  = "010004"

   hd_file = find_hd_file(file)

   masks = get_masks(cam_num, hd)
   image = apply_masks(image, masks)


   status, stars, center_stars, non_stars, cloudy_areas = find_stars(image, cam_num, 1, 200, 10)
   image= mask_frame(image, non_stars, 25)
   status, stars, center_stars, non_stars, cloudy_areas = find_stars(image, cam_num, 1, 200, 10)
   for (x,y) in stars:
      cv2.circle(image, (x,y), 3, (255), 1)
   for (x,y) in center_stars:
      cv2.circle(image, (x,y), 6, (255), 1)
   #for (x,y) in non_stars:
   #   cv2.rectangle(image, (x-5, y-5), (x+5, y+5), (128, 128, 128), 2)
   for (x,y,w,h) in cloudy_areas:
      cv2.rectangle(image, (x, y), (w, h), (200, 200, 200), 2)

   if len(center_stars) > 10 or len(stars) > 30:
      print("CALIBRATE?: YES")
      print("STARS:", len(stars))
      print("CENTER STARS:", len(center_stars))
      cv2.putText(image, str("CALIBRATE"),  (100,120), cv2.FONT_HERSHEY_SIMPLEX, .8, (255,255,255), 1)
      status = "calibrate"
   elif len(stars) > 10:

      status = "clear"
      print("STATUS: CLEAR")
      cv2.putText(image, str("CLEAR"),  (100,100), cv2.FONT_HERSHEY_SIMPLEX, .8, (255,255,255), 1)
   else:
      status = "bad"


   #cv2.imshow('pepe', image)
   #cv2.waitKey(10)
   return(status,stars,center_stars,non_stars,cloudy_areas)


def check_if_solved(solved_file):
   file_exists = Path(solved_file)
   if file_exists.is_file() is True:
      return(1)
   else:
      return(0)


def summarize_weather(weather_data):


   hourly_weather = {}
   for wdata in weather_data:
      (file, status, stars, center_stars, non_stars, cloudy_areas) = wdata
      (fy,fm,fd,fh,fmin,fsec,cam_num) = get_time_for_file(file)
      key = fy + "_" + fm + "_" + fd + "_" + fh + "_" + cam_num
      if key not in hourly_weather:
         hourly_weather[key] = []
         hourly_weather[key].append(status)
      else:
         hourly_weather[key].append(status)


   for key in hourly_weather:
      print(key,hourly_weather[key])


def find_non_cloudy_times(cal_date,cam_num):
  
   weather_data = []
   json_file = proc_dir + cal_date + "/" + "data/" + cal_date + "-weather-" + cam_num + ".json"
   found = check_if_solved(json_file)
   found = 0
   print ("FOUND:", found, json_file)
   if found == 0:
      glob_dir = proc_dir + cal_date + "/" + "images/*" + cal_date + "*" + cam_num + "*.png"
      print("GOB:", glob_dir)
      files = glob.glob(glob_dir)
      files = sorted(files)
      fc = 0
      for file in files:
         if "trim" not in file:
            if fc % 10 == 0:
               status, stars, center_stars, non_stars, cloudy_areas = check_for_stars(file, cam_num, 0)
               weather_data.append((file, status, stars, center_stars, non_stars, cloudy_areas))
            fc = fc + 1

      save_json_file(json_file, weather_data)
   else:
      weather_data = load_json_file(json_file)

   print("WEATHER DATA: ", weather_data)
   print("WEATHER JSON: ", json_file)

   return(weather_data)


def brightness(image, brightness_value):
   # Convert BGR to HSV
   hsv = image
   #hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
   #height, width, channels = hsv.shape	
   height, width = hsv.shape	
   for x in range(height):
      for y in range(width):
         if hsv[x,y] + brightness_value > 255:
            hsv[x,y] = 255
         elif hsv[x,y] + brightness_value < 0:
            hsv[x,y] = 0
         else:
            hsv[x,y] += brightness_value
	# Write new pixel channel value
   #edit_img = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
   return hsv 

# Edit contrast
def contrast(image, contrast_value):	
   hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
   height, width, channels = image.shape	
   for x in range(height):
      for y in range(width):
         for c in range(channels):
            if image[x,y,c] + contrast_value > 255:
               image[x,y,c] = 255
            elif image[x,y,c] + contrast_value < 0:
               image[x,y,c] = 0
            else:
               image[x,y,c] += contrast_value
   return image

def get_masks(this_cams_id, hd = 0):
   hdm_x = 2.7272
   hdm_y = 1.875
   my_masks = []
   cameras = json_conf['cameras']
   for camera in cameras:
      if str(cameras[camera]['cams_id']) == str(this_cams_id):
         if hd == 1:
            masks = cameras[camera]['hd_masks']
         else:
            masks = cameras[camera]['masks']
         for key in masks:
            mask_el = masks[key].split(',')
            (mx, my, mw, mh) = mask_el
               #mx = mx * hdm_x
               #my = my * hdm_y
               #mw = mw * hdm_x
               #mh = mh * hdm_y
            masks[key] = str(mx) + "," + str(my) + "," + str(mw) + "," + str(mh)
            my_masks.append((masks[key]))

   return(my_masks)





def calc_dist(p1,p2):
   x1,y1 = p1
   x2,y2 = p2
   dist = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
   return dist


def save_json_file(json_file, json_data):
   with open(json_file, 'w') as outfile:
      json.dump(json_data, outfile)
   outfile.close()

def load_json_file(json_file):
   with open(json_file, 'r') as infile:
      json_data = json.load(infile)
   return(json_data)

def load_stars(cal_file):
   star_file = cal_file.replace(".jpg", "-stars.txt")
   sf = open(star_file, "r")
   starlist = []
   for line in sf:
      line = line.replace("\n", "")
      line = line.replace(" Mike Star: ", "")
      data = line.split(" ")
      if len(data) == 5:
         star_name = data[1]
         star_name = star_name.replace(" at ", "")
         star_img_x = data[3]
         star_img_x = star_img_x.replace("(", "")
         star_img_x = star_img_x.replace(",", "")
         star_img_y = data[4]
         star_img_y = star_img_y.replace(")", "")
         starlist.append((star_name, star_img_x, star_img_y))
   return(starlist)


def bound_cnt(x,y,img_w,img_h):
   sz = 10 

   if x - sz < 0:
      mnx = 0
   else:
      mnx = x - sz 

   if y - sz < 0:
      mny = 0
   else:
      mny = y - sz 

   if x + sz > img_w - 1:
      mxx = img_w - 1 
   else: 
      mxx = x + sz

   if y + sz > img_h -1:
      mxy = img_h - 1
   else:
      mxy = y + sz
   return(mnx,mny,mxx,mxy)


def clean_star_bg(cnt_img, bg_avg):
   cnt_img.setflags(write=1)
   for x in range(0,cnt_img.shape[1]):
      for y in range(0,cnt_img.shape[0]):
         px_val = cnt_img[y,x]
         if px_val < bg_avg:
            #cnt_img[y,x] = random.randint(int(bg_avg - 3),int(bg_avg+3))
            cnt_img[y,x] = 0
   return(cnt_img)
 

def find_stars(med_stack_all, cam_num, center = 0, center_limit = 200, pdif_factor = 10):   

   masks = get_masks(cam_num, hd = 0)
#   med_stack_all = mask_frame(med_stack_all, masks)

   img_height, img_width= med_stack_all.shape
   hh = img_height / 2
   hw = img_width / 2
   max_px = np.max(med_stack_all)
   avg_px = np.mean(med_stack_all)
   med_cpy = med_stack_all.copy()
   
   pdif = max_px - avg_px
   pdif = int(pdif / pdif_factor) + avg_px
   bg_avg = 0

   if avg_px > 60:
      return(0,[],[], [], [])

   best_thresh = find_best_thresh(med_stack_all, avg_px+5)
   _, star_bg = cv2.threshold(med_stack_all, best_thresh, 255, cv2.THRESH_BINARY)
   thresh_obj= cv2.convertScaleAbs(star_bg)
   (_, cnts, xx) = cv2.findContours(thresh_obj.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
   star_pixels = []
   non_star_pixels = []
   cloudy_areas = []
   for (i,c) in enumerate(cnts):
      x,y,w,h= cv2.boundingRect(cnts[i])
      if w < 30 and h < 30:
         cnt_img = med_stack_all[y:y+h,x:x+w]
         (max_px, avg_px,px_diff,max_loc) = eval_cnt(cnt_img)

         mx,my = max_loc
         cx = x + int(w/2) 
         cy = y + int(h/2)
         mnx,mny,mxx,mxy = bound_cnt(cx,cy,img_width,img_height)
         cnt_img = med_stack_all[mny:mxy,mnx:mxx]
         cnt_w,cnt_h = cnt_img.shape



         if cnt_w > 0 and cnt_h > 0:
            is_star = star_test(cnt_img)
            if is_star == 1:
               bg_avg = bg_avg + np.mean(cnt_img)
               star_pixels.append((cx,cy))
               cv2.circle(med_cpy, (int(cx),int(cy)), 5, (255,255,255), 1)
            else:
               cv2.rectangle(med_cpy, (cx-5, cy-5), (cx + 5, cy + 5), (255, 0, 0), 1)
               non_star_pixels.append((cx,cy))
      else:
         cloudy_areas.append((x,y,w,h))
         cv2.rectangle(med_cpy, (x, y), (x + w, y + w), (255, 0, 0), 3)

   center_stars = []
   for sx,sy in star_pixels:
      center_dist = calc_dist((hw,hh), (sx,sy))
      if abs(center_dist) < center_limit:
         center_stars.append((sx,sy))

   if len(non_star_pixels) > 0 and len(star_pixels) > 0:
      perc_cloudy = int(len(non_star_pixels) / len(star_pixels))  * 100
      desc = str(len(star_pixels)) + " stars " + str(len(non_star_pixels)) + " non stars " + str(perc_cloudy) + "% cloudy"

   else :
      perc_cloudy = 0
      perc_clear = 100
      desc = str(len(star_pixels)) + " stars " + str(len(non_star_pixels)) + " non stars " + str(perc_clear) + "% clear"

   status = ""

   if len(star_pixels) > 10:
      status = "clear"
   if len(non_star_pixels) > len(star_pixels) or len(star_pixels) <= 5:
      status = "cloudy"
   if len(non_star_pixels) == 0 and len(star_pixels) == 0:
      status = "cloudy"
   if len(non_star_pixels) >= 5 and len(star_pixels) <= 5:
       status = "partly cloudy "

   cv2.putText(med_cpy, str(status),  (10,300), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)  
   return(status,star_pixels, center_stars, non_star_pixels, cloudy_areas)

def find_best_thresh(image, start_thresh):
   go = 1
   tries = 0
   while go == 1:
      _, star_bg = cv2.threshold(image, start_thresh, 255, cv2.THRESH_BINARY)

      thresh_obj = cv2.dilate(star_bg, None , iterations=4)
      (_, cnts, xx) = cv2.findContours(thresh_obj.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
      #print("CNTS:", len(cnts), start_thresh)
      if len(cnts) > 70: 
         start_thresh = start_thresh + 1
      elif len(cnts) < 3:
         start_thresh = start_thresh - 1
      else: 
         go = 0
      if tries > 10:
         go = 0
      tries = tries + 1
   return(start_thresh)


def find_bright_pixels(med_stack_all, solved_file, cam_num):

   print("MAKE PLATE MED STACKED", med_stack_all.shape)
   img_height,img_width = med_stack_all.shape
   med_cpy = med_stack_all.copy()
   star_pixels = []
   max_px = np.max(med_stack_all)
   avg_px = np.mean(med_stack_all)
   pdif = max_px - avg_px
   pdif = int(pdif / 20) + avg_px
 
   best_thresh = find_best_thresh(med_stack_all, pdif)
   _, star_bg = cv2.threshold(med_stack_all, best_thresh, 255, cv2.THRESH_BINARY)


   #cv2.imshow('pepe', star_bg)
   #cv2.waitKey(10)
   #star_bg = cv2.GaussianBlur(star_bg, (7, 7), 0)
   thresh_obj = cv2.dilate(star_bg, None , iterations=4)
   #thresh_obj= cv2.convertScaleAbs(star_bg)
   (_, cnts, xx) = cv2.findContours(thresh_obj.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
   masked_pixels = []

   #for (i,c) in enumerate(cnts):
   #   x,y,w,h = cv2.boundingRect(cnts[i])
   #   cv2.rectangle(star_bg, (x, y), (x + w+5, y + h+5), (255, 0, 0), 1)

   bg_avg = 0

   for (i,c) in enumerate(cnts):
      x,y,w,h = cv2.boundingRect(cnts[i])
      if True and w < 10 and h < 10:
         cnt_img = med_stack_all[y:y+h,x:x+w]
         (max_px, avg_px,px_diff,max_loc) = eval_cnt(cnt_img)

         mx,my = max_loc
         cx = x + mx
         cy = y + my
         mnx,mny,mxx,mxy = bound_cnt(cx,cy,img_width,img_height) 
         cnt_img = med_stack_all[mny:mxy,mnx:mxx]
         cnt_w,cnt_h = cnt_img.shape
         if cnt_w > 0 and cnt_h > 0:
            is_star = star_test(cnt_img)
            if is_star >= 0:
               bg_avg = bg_avg + np.mean(cnt_img)
               star_pixels.append((cx,cy))
               cv2.circle(med_cpy, (int(cx),int(cy)), 5, (255,255,255), 1)
            else:
               cv2.rectangle(med_cpy, (cx-5, cy-5), (cx + 5, cy + 5), (255, 0, 0), 1)
         else:
               cv2.rectangle(med_cpy, (cx-15, cy-15), (cx + 15, cy + 15), (255, 0, 0), 1)

   if len(star_pixels) > 0:
      bg_avg = bg_avg / len(star_pixels)  
   else:
      bg_avg = 35

   file_exists = Path(solved_file)
   if file_exists.is_file() is False:
   #   print("MAKE PLATE ", solved_file)
   #   # if plate image does not exist! 
   #   plate_image = med_stack_all.copy()
   #   print("PLATE SHAPE", plate_image.shape)
   #   for x in range(0,plate_image.shape[1]):
   #      for y in range(0,plate_image.shape[0]):
   #         plate_image[y,x] = random.randint(int(0),int(5))
   #   plate_image = cv2.GaussianBlur(plate_image, (7, 7), 0) 

      plate_image= star_bg
      star_sz = 10
      for star in star_pixels:
         sx,sy = star
         mnx,mny,mxx,mxy = bound_cnt(sx,sy,img_width,img_height) 
         star_cnt = med_stack_all[mny:mxy,mnx:mxx]
         star_cnt = clean_star_bg(star_cnt, bg_avg+7)
         plate_image[mny:mxy,mnx:mxx] = star_cnt

   else:
      print("PLATE ALREADY SOLVED HERE! FIX", solved_file)
      plate_file = solved_file.replace("-grind.png", ".jpg")
      plate_image = cv2.imread(plate_file, 0)
 



   masks = get_masks(cam_num, 1)
   print("MASKS:",  masks)
   for mask in masks:
      msx,msy,msw,msh = mask.split(",")
      plate_image[int(msy):int(msy)+int(msh),int(msx):int(msx)+int(msw)] = 0

   plate_image[0:1080,0:200] = 0
   plate_image[0:1080,1720:1920] = 0

   #cv2.imshow('pepe', plate_image)
   #cv2.waitKey(10)

   return(star_pixels, plate_image)

def star_test(cnt_img):
   PX = []
   PY = []
   ch,cw = cnt_img.shape
   my = int(ch / 2)
   mx = int(cw / 2)
   max_px = np.max(cnt_img)
   avg_px = np.mean(cnt_img)
   px_diff = max_px - avg_px 

   for x in range(0,cw-1):
      px_val = cnt_img[my,x]
      PX.append(px_val)
      #cnt_img[my,x] = 255
   for y in range(0,ch-1):
      py_val = cnt_img[y,mx]
      PY.append(py_val)
      #cnt_img[y,mx] = 255

   ys_peaks = signal.find_peaks(PY)
   y_peaks = len(ys_peaks[0])
   xs_peaks = signal.find_peaks(PX)
   x_peaks = len(xs_peaks[0])


   if px_diff > 20:
      is_star = 1 
   else:
      is_star = 0

   return(is_star)

def astr_line(line):
   line = line.replace("\n", "")
   line = line.replace("  Mike Star: ", "")
   el = line.split(" at ")
   if "at" not in line:
      exit()

   if len(el) == 2:
      cname,num = el 
   else:
      print("fuck:", line)
      exit()
   num = num.replace(" ","")
   num = num.replace("(","")
   num = num.replace(")","")
   fields = line.split(" ")
   if "(" in cname:
      common_name, cat_name = cname.split("(")
      cname = cat_name
      cname = cname.replace(")", "")
      #cname.replace(cat_name, "")
   else:
      common_name = ""
   cname = cname.rstrip()
   common_name = common_name.rstrip()

   ast_x,ast_y = num.split(",")
   return(cname,common_name,ast_x,ast_y)

def parse_astr_star_file(star_data_file, limit_mag_start = -10, limit_mag_end = 3):
   bright_stars_found = []
   bright_stars_notfound = []
   fp = open(star_data_file, "r")
   for line in fp:
      status = 0
      bname = ""
      common_name = ""
      star_name, common_name, ast_x, ast_y = astr_line(line)

      (status, bname, cons, ra,dec,mag) = find_star_by_name(star_name, common_name)

      if int(status) == 1:
         data = bname + "," + cons + "," + str(ra) + "," + str(dec) + "," + str(mag) + "," + str(ast_x) + "," + str(ast_y)
         data = (bname, cons,ra,dec,mag,ast_x,ast_y)
         if limit_mag_start <= float(mag) <= limit_mag_end:
            bright_stars_found.append(data)
      else:
         data = (star_name,0,0,0,ast_x,ast_y)
         bright_stars_notfound.append(data)

   return(bright_stars_found, bright_stars_notfound)

def find_star_by_name(star_name, common_name, debug = 1):
   for bname, cname, ra, dec, mag in bright_stars:
      dbname = bname.decode("utf-8")
      dcname = cname.decode("utf-8")
      if star_name in dbname and star_name != "" and dbname != "":  
         return(1,dbname, dcname, ra,dec,mag)
      if common_name in dcname and common_name != "" and dcname != "":
         return(1,dbname, dcname, ra,dec,mag)
   print("Could not find", star_name, common_name, "in catalog!")
   exit()
   return(0,0,0,0,0,0)

