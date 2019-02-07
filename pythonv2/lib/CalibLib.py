import time
import subprocess
import math
from pathlib import Path
import datetime
import cv2
import numpy as np
import ephem
import glob
import os
from lib.VideoLib import load_video_frames, get_masks
from lib.ImageLib import stack_frames, median_frames, adjustLevels, mask_frame
from lib.UtilLib import convert_filename_to_date_cam, bound_cnt
from lib.FileIO import cfe, save_json_file
from lib.DetectLib import eval_cnt
from scipy import signal

def check_running():
   cmd = "ps -aux |grep solve-field | grep -v grep |wc -l"
   #cmd = "ps -aux |grep solve-field "
   output = subprocess.check_output(cmd, shell=True).decode("utf-8")
   output = int(output.replace("\n", ""))
   print("RUNNING:", output)
   if int(output) > 0:
      return(1)
   else:
      return(0)

def check_if_solved(cal_file):
   cal_wild = cal_file.replace(".jpg", "*")
   astr_files = []
   solved = 0
   for astr_file in sorted((glob.glob(cal_wild))):
      if 'wcs' in  astr_file:
         print("This image has been solved.")
         solved = 1
      astr_files.append(astr_file)
   return(solved, astr_files)


def save_cal_params(wcs_file):
   wcs_info_file = wcs_file.replace(".wcs", "-wcsinfo.txt")
   cal_params_file = wcs_file.replace(".wcs", "-calparams.json")
   fp =open(wcs_info_file, "r")
   cal_params_json = {}
   for line in fp:
      line = line.replace("\n", "")
      field, value = line.split(" ")
      if field == "imagew":
         cal_params_json['imagew'] = value
      if field == "imageh":
         cal_params_json['imageh'] = value
      if field == "pixscale":
         cal_params_json['pixscale'] = value
      if field == "orientation":
         cal_params_json['position_angle'] = float(value) + 180
      if field == "ra_center":
         cal_params_json['ra_center'] = value
      if field == "dec_center":
         cal_params_json['dec_center'] = value
      if field == "fieldw":
         cal_params_json['fieldw'] = value
      if field == "fieldh":
         cal_params_json['fieldh'] = value
      if field == "ramin":
         cal_params_json['ramin'] = value
      if field == "ramax":
         cal_params_json['ramax'] = value
      if field == "decmin":
         cal_params_json['decmin'] = value
      if field == "decmax":
         cal_params_json['decmax'] = value

   save_json_file(cal_params_file, cal_params_json)


def find_image_stars(cal_img):
   bgavg = np.mean(cal_img)
   thresh = bgavg * 1.5
   if thresh < 1:
      thresh =  10

   print("THREHS:", thresh)
   if cal_img.shape == 3:
      cal_img= cv2.cvtColor(cal_img, cv2.COLOR_BGR2GRAY)
   cal_img = cv2.GaussianBlur(cal_img, (7, 7), 0)
   _, threshold = cv2.threshold(cal_img.copy(), thresh, 255, cv2.THRESH_BINARY)
   #cal_img = cv2.dilate(threshold, None , iterations=4)
   cal_img= cv2.convertScaleAbs(threshold)
   (_, cnts, xx) = cv2.findContours(cal_img.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
   star_pixels = []
   non_star_pixels = []
   cloudy_areas = []
   for (i,c) in enumerate(cnts):
      x,y,w,h= cv2.boundingRect(cnts[i])
      if w > 1 and h > 1:
         star_pixels.append((x,y,w,h))
         #cv2.rectangle(cal_img, (x, y), (x + w, y + h), (128, 128, 128), 1)
   return(star_pixels,cal_img)

def last_sunrise_set(json_conf, cal_date = None):
   if cal_date == None:
      cal_date =  datetime.date.today().strftime("%Y-%m-%d %H:%M:%S")
   print("CAL DATE:", cal_date)
   device_lat = json_conf['site']['device_lat']
   device_lng = json_conf['site']['device_lng']

   obs = ephem.Observer()

   obs.pressure = 0
   obs.horizon = '-0:34'
   obs.lat = device_lat
   obs.lon = device_lng
   obs.date = cal_date

   sun = ephem.Sun()
   sun.compute(obs)
   last_sunrise = obs.previous_rising(ephem.Sun())
   last_sunset = obs.previous_setting(ephem.Sun())
   # if the sun is currently set, use the next sunset as the end time not prev
   timediff = last_sunrise - last_sunset
   print(last_sunrise, last_sunset)
   print(timediff)
   sr_datetime = last_sunrise.datetime().strftime('%Y-%m-%d %H:%M:%S')
   ss_datetime = last_sunset.datetime().strftime('%Y-%m-%d %H:%M:%S')
   print(sr_datetime)
   print(ss_datetime)
   sr_datetime_t = datetime.datetime.strptime(sr_datetime, "%Y-%m-%d %H:%M:%S")
   ss_datetime_t = datetime.datetime.strptime(ss_datetime, "%Y-%m-%d %H:%M:%S")

   time_diff = sr_datetime_t - ss_datetime_t
   hr = time_diff.seconds / (3600)   
   print(sr_datetime,ss_datetime,hr)
   return(sr_datetime_t, ss_datetime_t,hr)

def find_hd_file(cal_glob):
   print(cal_glob)
   files = glob.glob(cal_glob)
   return(files)

def calibrate_camera(cams_id, json_conf, cal_date = None, show=1):
   # unless passed in use the last night as the calibration date
   # check 1 frame per hour and if there are enough stars then 
   # attempt to plate solve with astrometry
   # if that succeeds fit the plate and save the calibration file

   # first find the time of the last sun rise and sun set...
   last_sunrise, last_sunset,hr = last_sunrise_set(json_conf, cal_date)
   print("Hours of Dark:", hr)
   for i in range (2,int(hr)-1):
      cal_date = last_sunset + datetime.timedelta(hours=i)
      cal_video = find_hd_file(cal_date.strftime('/mnt/ams2/HD/%Y_%m_%d_%H_%M*' + cams_id + '*.mp4') )
      if len(cal_video) == 0:
         continue 
      cal_file = cal_video[0].replace('.mp4', '.jpg')

      frames = load_video_frames(cal_video[0],json_conf,25)
      el = cal_file.split("/")
      cal_file = "/mnt/ams2/cal/tmp/" + el[-1]
      print(cal_file)
      #cal_image, cal_image_np = stack_frames(frames,cal_file) 
      cal_image_np =  median_frames(frames) 
      #cal_image_np = adjustLevels(cal_image_np, 55,1,255)
      masks = get_masks(cams_id, json_conf, hd = 1)
      cal_image_np = mask_frame(cal_image_np, [], masks)
      cal_star_file = cal_file.replace(".jpg", "-median.jpg")

      show_img = cv2.resize(cal_image_np, (0,0),fx=.4, fy=.4)
      cv2.putText(show_img, "Cal Image NP",  (50,50), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
      cv2.imshow('pepe', show_img)
      cv2.waitKey(10)
      (stars, plate_image) = make_plate_image(cal_image_np, cal_star_file, cams_id, json_conf)
      if show == 1:
         show_img = cv2.resize(plate_image, (0,0),fx=.4, fy=.4)
         cv2.namedWindow('pepe')
         cv2.putText(show_img, "Plate Image",  (50,50), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
         cv2.imshow('pepe', show_img)
         cv2.waitKey(10)
      cv2.imwrite(cal_file, plate_image)
      cv2.imwrite(cal_star_file, cal_image_np)

      print("STARS:", len(stars))
      if len(stars) >= 20 and len(stars) < 80:
         solved = plate_solve(cal_file,json_conf)
         print("SOLVED:", solved)
         if solved == 1:
            star_file = cal_file.replace(".jpg", "-mapped-stars.json")
            cmd = "./calFit.py " + star_file
            print(cmd)
            os.system(cmd)

def find_best_cal_file(hd_datetime, hd_cam):
   cal_file = None
   return(cal_file)

def reduce_object(object, sd_video_file, hd_file, hd_trim, hd_crop_file, hd_crop_box, json_conf, cal_file = None):

   hd_datetime, hd_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(hd_file)

   if cal_file is None:
      cal_file = find_best_cal_file(hd_datetime, hd_cam)

   el = hd_trim.split("-trim-")
   min_file = el[0] + ".mp4"
   print(el[1])
   ttt = el[1].split("-")
   trim_num = ttt[0]

   print("REDUCE OBJECT", trim_num)

   meteor_frames = []
   extra_sec = int(trim_num) / 25
   start_frame_time = hd_datetime + datetime.timedelta(0,extra_sec)
   start_frame_str = start_frame_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
   start_frame_num = object['history'][0][0]
   for hist in object['history']:
      fc,x,y,w,h,mx,my = hist
      hd_x = x + hd_crop_box[0] 
      hd_y = x + hd_crop_box[1] 

      extra_sec = (start_frame_num + fc) /  25
      frame_time = hd_datetime + datetime.timedelta(0,extra_sec)
      frame_time_str = frame_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
      if cal_file is None:
         ra, dec, rad, decd, az, el = 0,0,0,0,0,0
      meteor_frames.append((fc,frame_time_str,x,y,w,h,hd_x,hd_y,ra,dec,rad,decd,az,el))

   return(meteor_frames) 

def plate_solve(cal_file,json_conf):

   el = cal_file.split("/")

   wcs_file = cal_file.replace(".jpg", ".wcs")
   grid_file = cal_file.replace(".jpg", "-grid.png")

   star_file = cal_file.replace(".jpg", "-stars-out.jpg")
   star_data_file = cal_file.replace(".jpg", "-stars.txt")
   astr_out = cal_file.replace(".jpg", "-astrometry-output.txt")

   wcs_info_file = cal_file.replace(".jpg", "-wcsinfo.txt")

   quarter_file = cal_file.replace(".jpg", "-1.jpg")

   image = cv2.imread(cal_file)

   if len(image.shape) > 2:
      gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
   else:
      gray = image
   height = gray.shape[0]
   width = gray.shape[1]

   cmd = "/usr/local/astrometry/bin/solve-field " + cal_file + " --crpix-center --cpulimit=30 --verbose --no-delete-temp --overwrite --width=" + str(width) + " --height=" + str(height) + " --scale-low 50 --scale-high 90 > " + astr_out + " 2>&1 &"
   print(cmd) 
   os.system(cmd)

   running = check_running() 
   start_time = datetime.datetime.now()
   while running == 1:
      running = check_running() 
      cur_time = datetime.datetime.now()
      tdiff = cur_time - start_time
      print("running plate solve.", tdiff)
      time.sleep(10)
   
   time.sleep(3)

   os.system("grep Mike " + astr_out + " >" +star_data_file + " 2>&1" )

   cmd = "/usr/bin/jpegtopnm " + cal_file + "|/usr/local/astrometry/bin/plot-constellations -w " + wcs_file + " -o " + grid_file + " -i - -N -C -G 600"
   os.system(cmd)

   cmd = "/usr/local/astrometry/bin/wcsinfo " + wcs_file + " > " + wcs_info_file
   os.system(cmd)

   #bright_star_data = parse_astr_star_file(star_data_file)
   #plot_bright_stars(cal_file, image, bright_star_data)
   solved = cfe(grid_file)
   if solved == 1:
      save_cal_params(wcs_file)
   return(solved)

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

def make_plate_image(med_stack_all, cam_num, json_conf, show = 1):
   
   stars = []
   med_cpy = med_stack_all.copy()
   plate_image = med_stack_all
   if show == 1:
      show_img = cv2.resize(med_stack_all, (0,0),fx=.4, fy=.4)
      cv2.putText(show_img, "Make Plate Image",  (50,50), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
      cv2.imshow('pepe', show_img)
      cv2.waitKey(10)
   img_height,img_width = med_stack_all.shape
   max_px = np.max(med_stack_all)
   avg_px = np.mean(med_stack_all)
   best_thresh = find_best_thresh(med_stack_all, avg_px)

   _, star_thresh = cv2.threshold(med_stack_all, best_thresh, 255, cv2.THRESH_BINARY)
   thresh_obj = cv2.dilate(star_thresh, None , iterations=4)
   (_, cnts, xx) = cv2.findContours(thresh_obj.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

   plate_image= np.zeros((img_height,img_width),dtype=np.uint8)
   for (i,c) in enumerate(cnts):
      x,y,w,h = cv2.boundingRect(cnts[i])
      cnt_img = med_cpy[y:y+h,x:x+h]
      if True and w < 30 and h < 30:
         (max_px, avg_px,px_diff,max_loc) = eval_cnt(cnt_img)
 
         mx,my = max_loc
         cx = x + mx
         cy = y + my
         mnx,mny,mxx,mxy = bound_cnt(cx,cy,img_width,img_height)

         is_star = star_test(cnt_img)
         cnt_h, cnt_w = cnt_img.shape
         #cv2.putText(cnt_img, str(is_star),  (0,cnt_h-1), cv2.FONT_HERSHEY_SIMPLEX, .2, (255, 255, 255), 1)
         cv2.imshow('pepe', cnt_img)
         cv2.waitKey(1)

         if is_star == 1:
            cx = int(mnx + mxx / 2)
            cy = int(mny + mxy / 2)
            stars.append((cx,cy))
            cnt_img = med_cpy[mny:mxy,mnx:mxx]
            cnt_h,cnt_w = cnt_img.shape
            (max_px, avg_px,px_diff,max_loc) = eval_cnt(cnt_img)
            bp_x,bp_y = max_loc
            print("BPX:", bp_x,bp_y)
            #cv2.putText(cnt_img, str(is_star),  (0,cnt_h-1), cv2.FONT_HERSHEY_SIMPLEX, .2, (255, 255, 255), 1)
            #cv2.circle(cnt_img, (int(bp_x),int(bp_y)), 5, (255,255,255), 1)
            star_cnt = cnt_img
            ul = cnt_img[0,0] 
            ur = cnt_img[0,cnt_w-1] 
            ll =  cnt_img[cnt_h-1,0] 
            lr = cnt_img[cnt_h-1,cnt_w-1] 
             
            cavg = int((ul + ur + ll + lr) / 4)
            star_cnt = clean_star_bg(cnt_img, cavg+3)
            plate_image[mny:mxy,mnx:mxx] = cnt_img

   cv2.imshow('pepe', plate_image)
   cv2.waitKey(10)

   return(stars,plate_image)


def find_bright_pixels(med_stack_all, solved_file, cam_num, json_conf):

   show_img = cv2.resize(med_stack_all, (0,0),fx=.4, fy=.4)
   cv2.putText(show_img, "Find Bright Pixels",  (50,50), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
   cv2.imshow('pepe', show_img)
   cv2.waitKey(10)
   cams_id = cam_num
   img_height,img_width = med_stack_all.shape
   med_cpy = med_stack_all.copy()
   star_pixels = []
   max_px = np.max(med_stack_all)
   avg_px = np.mean(med_stack_all)
   pdif = max_px - avg_px
   pdif = int(pdif / 20) + avg_px

   best_thresh = find_best_thresh(med_stack_all, pdif)
   _, star_bg = cv2.threshold(med_stack_all, best_thresh, 255, cv2.THRESH_BINARY)
   thresh_obj = cv2.dilate(star_bg, None , iterations=4)
   #thresh_obj = star_bg
   (_, cnts, xx) = cv2.findContours(thresh_obj.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
   show_img = cv2.resize(thresh_obj, (0,0),fx=.4, fy=.4)
   cv2.putText(show_img, "Thresh OBJ",  (50,50), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
   cv2.imshow('pepe', show_img)
   cv2.waitKey(10)
   masked_pixels = []
   bg_avg = 0

   for (i,c) in enumerate(cnts):
      x,y,w,h = cv2.boundingRect(cnts[i])
      if True and w < 20 and h < 20:
         cnt_img = med_stack_all[y:y+h,x:x+w]
         cv2.imshow('pepe', cnt_img)
         cv2.waitKey(10)
         (max_px, avg_px,px_diff,max_loc) = eval_cnt(cnt_img)
         mx,my = max_loc
         cx = x + mx
         cy = y + my
         mnx,mny,mxx,mxy = bound_cnt(cx,cy,img_width,img_height)

         cnt_img = med_stack_all[mny:mxy,mnx:mxx]
         cv2.imshow('pepe', cnt_img)
         cv2.waitKey(10)

         cnt_w,cnt_h = cnt_img.shape
         if cnt_w > 0 and cnt_h > 0:
            is_star = star_test(cnt_img)
            is_star = 1
            if is_star >= 0:
               bg_avg = bg_avg + np.mean(cnt_img)
               star_pixels.append((cx,cy))
               cv2.circle(med_cpy, (int(cx),int(cy)), 5, (255,255,255), 1)
            else:
               cv2.rectangle(med_cpy, (cx-5, cy-5), (cx + 5, cy + 5), (255, 0, 0), 1)
         else:
               cv2.rectangle(med_cpy, (cx-15, cy-15), (cx + 15, cy + 15), (255, 0, 0), 1)


   show_img = cv2.resize(med_cpy, (0,0),fx=.4, fy=.4)
   cv2.putText(show_img, "Initial Stars Found",  (50,50), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
   cv2.imshow('pepe', show_img)
   cv2.waitKey(10)


   if len(star_pixels) > 0:
      bg_avg = bg_avg / len(star_pixels)
   else:
      bg_avg = 35

   file_exists = Path(solved_file)
   if True:
   #if file_exists.is_file() is False:
      plate_image= med_stack_all 
      plate_image= np.zeros((img_height,img_width),dtype=np.uint8)
      star_sz = 10
      for star in star_pixels:
         sx,sy = star
         print("STAR FOUND:", sx,sy)
         mnx,mny,mxx,mxy = bound_cnt(sx,sy,img_width,img_height)
         star_cnt = med_stack_all[mny:mxy,mnx:mxx]
         #star_cnt = clean_star_bg(star_cnt, bg_avg+7)
         plate_image[mny:mxy,mnx:mxx] = star_cnt
         cv2.imshow('pepe', star_cnt)
         cv2.waitKey(10)

   else:
      print("PLATE ALREADY SOLVED HERE! FIX", solved_file)
      plate_file = solved_file.replace("-grind.png", ".jpg")
      plate_image = cv2.imread(plate_file, 0)


   masks = get_masks(cams_id, json_conf, hd = 1)
   print("MASKS:",  masks)
   for mask in masks:
      msx,msy,msw,msh = mask.split(",")
      plate_image[int(msy):int(msy)+int(msh),int(msx):int(msx)+int(msw)] = 0

   plate_image[0:1080,0:200] = 0
   plate_image[0:1080,1720:1920] = 0

   #cv2.imshow('pepe', plate_image)
   #cv2.waitKey(10)

   return(star_pixels, plate_image)


def find_best_thresh(image, start_thresh):
   if len(image.shape) > 2:
      image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
   show_img = cv2.resize(image, (0,0),fx=.4, fy=.4)
   cv2.putText(show_img, "Find Best Thresh",  (50,50), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
   cv2.imshow('pepe', show_img)
   cv2.waitKey(10)

   go = 1
   tries = 0
   while go == 1:
      _, star_bg = cv2.threshold(image, start_thresh, 255, cv2.THRESH_BINARY)

      #thresh_obj = cv2.dilate(star_bg, None , iterations=4)
      #star_bg = cv2.convertScaleAbs(star_bg)
      (_, cnts, xx) = cv2.findContours(star_bg.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
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


def star_test(cnt_img):
   PX = []
   PY = []
   ch,cw = cnt_img.shape
   my = int(ch / 2)
   mx = int(cw / 2)
   max_px = np.max(cnt_img)
   avg_px = np.mean(cnt_img[0:])
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

   print(x_peaks)
   print(x_peaks)
   print(cnt_img.shape)

   if px_diff > 25 or max_px > 100:
      is_star = 1
      print("STAR PASSED:", px_diff, max_px)
   else:
      is_star = 0
      print("STAR FAILED:", px_diff,max_px)

   return(is_star)


def clean_star_bg(cnt_img, bg_avg):
   cnt_img.setflags(write=1)
   for x in range(0,cnt_img.shape[1]):
      for y in range(0,cnt_img.shape[0]):
         px_val = cnt_img[y,x]
         if px_val < bg_avg:
            #cnt_img[y,x] = random.randint(int(bg_avg - 3),int(bg_avg+3))
            cnt_img[y,x] = 0
   return(cnt_img)

