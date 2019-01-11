#!/usr/bin/python3

import ephem
import datetime
import glob
import math
import numpy as np
import os
import cv2
import sys
from pathlib import Path
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
import json

import brightstardata as bsd
mybsd = bsd.brightstardata()
bright_stars = mybsd.bright_stars


json_file = open('../conf/as6.json')
json_str = json_file.read()
json_conf = json.loads(json_str)
proc_dir = json_conf['site']['proc_dir']
lon = json_conf['site']['device_lng']
lat = json_conf['site']['device_lat']
alt = json_conf['site']['device_alt']

from detectlib import load_video_frames, median_frames, convert_filename_to_date_cam
from caliblib import find_bright_pixels, load_stars, find_stars, save_json_file, load_json_file, parse_astr_star_file, find_star_by_name, calc_dist

R = 6378.1

def Decdeg2DMS( Decin ):
   Decin = float(Decin)
   if(Decin<0):
      sign = -1
      dec  = -Decin
   else:
      sign = 1
      dec  = Decin

   d = int( dec )
   dec -= d
   dec *= 100.
   m = int( dec*3./5. )
   dec -= m*5./3.
   s = dec*180./5.

   if(sign == -1):
      out = '-%02d:%02d:%06.3f'%(d,m,s)
   else: out = '+%02d:%02d:%06.3f'%(d,m,s)

   return out


def RAdeg2HMS( RAin ):
   RAin = float(RAin)
   if(RAin<0):
      sign = -1
      ra   = -RAin
   else:
      sign = 1
      ra   = RAin

   h = int( ra/15. )
   ra -= h*15.
   m = int( ra*4.)
   ra -= m/4.
   s = ra*240.

   if(sign == -1):
      out = '-%02d:%02d:%06.3f'%(h,m,s)
   else: out = '+%02d:%02d:%06.3f'%(h,m,s)

   return out



def radec_to_azel(ra,dec,lat,lon,alt, caldate):
   body = ephem.FixedBody()
   print ("BODY: ", ra, dec)
   #body._epoch=ephem.J2000

   rah = RAdeg2HMS(ra)
   dech= Decdeg2DMS(dec)

   body._ra = rah
   body._dec = dech

   obs = ephem.Observer()
   obs.lat = ephem.degrees(lat)
   obs.lon = ephem.degrees(lon)
   obs.date = caldate
   obs.elevation=float(alt)
   body.compute(obs)
   az = str(body.az)
   el = str(body.alt)
   (d,m,s) = az.split(":")
   dd = float(d) + float(m)/60 + float(s)/(60*60)
   az = dd

   (d,m,s) = el.split(":")
   dd = float(d) + float(m)/60 + float(s)/(60*60)
   el = dd
   #az = ephem.degrees(body.az)
   return(az,el)


def distort_xy(x,y,img_w,img_h):
   strength = 1.8
   zoom = 1
   x_adj = 0
   y_adj = 0
   correctionRadius = math.sqrt(img_w ** 2 + img_h ** 2) / strength
   half_w = int(img_w/2) 
   half_h = int(img_h/2) 
   newX = x - half_w
   newY = y - half_h

   distance = math.sqrt(newX ** 2 + newY ** 2)
   r = distance / correctionRadius

   if r == 0:
      theta = 1
   else:
      theta = math.atan(r) / r

   sourceX = half_w + theta * newX * zoom
   sourceY = half_h + theta * newY * zoom

   sourceX = int(float(sourceX))
   sourceY = int(float(sourceY))

   #set color of pixel (x, y) to color of source image pixel at (sourceX, sourceY)
   newX = int(float(newX))
   newY = int(float(newY))
   if sourceY > img_h-1:
      sourceY = img_h-1
   if sourceX > img_w-1:
      sourceX = img_w-1
   return(sourceX,sourceY)

def make_med_stack(file, cal_file):
   med_stack_fn = cal_file.replace(".jpg", "-med_stack.jpg")
   frames = load_video_frames(file, 30)
   med_stack = median_frames(frames)
   cv2.imwrite(med_stack_fn, med_stack)
   return(med_stack)

def set_filenames(file):
   el = file.split("/")
   filename = el[-1]
   if ".mp4" in file:
      filename_base = filename.replace(".mp4", "")
   elif ".jpg" in file:
      filename_base = filename.replace(".jpg", "")

   cal_file = "/mnt/ams2/cal/" + filename

   if ".mp4" in cal_file:
      cal_file = cal_file.replace(".mp4", ".jpg")



   solved_file = "/mnt/ams2/cal/solved/" + filename_base + "/" + filename_base + ".jpg"
   med_stack_file = "/mnt/ams2/cal/solved/" + filename_base + "/" + filename_base + "-med_stack.jpg"
   stars_file = "/mnt/ams2/cal/solved/" + filename_base + "/" + filename_base + "-stars.txt"

   return(cal_file, med_stack_file, stars_file, solved_file)

def check_if_solved(solved_file):
   file_exists = Path(solved_file)
   if file_exists.is_file() is True:
      return(1)
   else:
      return(0)

def get_image(file):
   img = cv2.imread(file, 0 )
   return(img)

def draw_star_image(med_stack, star_px, astr_stars, grid_image, star_data_file,cal_date):
  
   mapped_star_file = star_data_file.replace("-stars.txt", "-mapped-stars.json") 
   med_stack_pil = Image.fromarray(med_stack)
   img_h,img_w = med_stack.shape
   med_stack_pil = med_stack_pil.convert("RGBA") 
   grid_image = grid_image.convert("RGBA") 
   draw = ImageDraw.Draw(med_stack_pil)
   font = ImageFont.truetype("/usr/share/fonts/truetype/freefont/FreeSans.ttf", 12, encoding="unic" )

   bright_stars_found,not_found = parse_astr_star_file(star_data_file, -10, 3)
   mag3_stars = pair_stars(star_px, bright_stars_found,img_w,img_h,20,med_stack)

   bright_stars_found,not_found = parse_astr_star_file(star_data_file, 3.1, 4)
   mag4_stars = pair_stars(star_px, bright_stars_found,img_w,img_h,20,med_stack)

   mapped_stars = []
   for good_star in mag3_stars:
      star_name, common_name, ra, dec, mag, sx, sy, mx, my = good_star
      (az, el) = radec_to_azel(ra,dec,lat,lon,alt, cal_date)
      azel = str('{0:.2f}'.format(az)) + " " + str( '{0:.2f}'.format(el))


      #azel = azel + str(ra) + " " + str(dec)
      print ("MAPPED STAR:", star_name, common_name, ra, dec, mag, sx,sy,mx,my, az,el)
      sx = float(sx)
      sy = float(sy)
      draw.rectangle((mx-10, my-10, mx + 10, my + 10), outline="blue")
      draw.ellipse((mx-5, my-5, mx+5, my+5),  outline ="blue")
      draw.ellipse((sx-5, sy-5, sx+5, sy+5),  outline ="green")
      draw.line((mx,my, sx,sy), fill=255)
      draw.text((sx-10, sy-20), str(common_name + "(" + str(star_name) + ")"), font = font, fill=(255,255,255))
      draw.text((sx-10, sy-30), azel , font = font, fill=(255,255,255))
      mapped_stars.append((star_name, common_name, ra, dec, mag, sx, sy, mx, my,az,el)) 
   cv2.imshow('pepe', np.asarray(med_stack_pil))
   cv2.waitKey(10)

   for good_star in mag4_stars:
      star_name, common_name, ra, dec, mag, sx, sy, mx, my = good_star
      (az, el) = radec_to_azel(ra,dec,lat,lon,alt, cal_date)
      azel = str('{0:.2f}'.format(az)) + " " + str( '{0:.2f}'.format(el))
      #azel = azel + str(ra) + " " + str(dec)
      sx = float(sx)
      sy = float(sy)
      draw.rectangle((mx-10, my-10, mx + 10, my + 10), outline="blue")
      draw.ellipse((mx-5, my-5, mx+5, my+5),  outline ="blue")
      draw.ellipse((sx-5, sy-5, sx+5, sy+5),  outline ="green")
      draw.line((mx,my, sx,sy), fill=255)
      draw.text((sx-10, sy-20), str(common_name + "(" + str(star_name) + ")"), font = font, fill=(255,255,255))
      draw.text((sx-10, sy-30), azel , font = font, fill=(255,255,255))
      mapped_stars.append((star_name, common_name, ra, dec, mag, sx, sy, mx, my,az,el))
   cv2.imshow('pepe', np.asarray(med_stack_pil))
   cv2.waitKey(10)


   save_json_file(mapped_star_file, mapped_stars)
   print(mapped_star_file)
   show_img = np.asarray(med_stack_pil)
   cv2.imshow('pepe', show_img)
   cv2.waitKey(10)
   
   alpha = Image.blend(med_stack_pil, grid_image, .4)
   return(np.asarray(alpha))

def pair_stars(my_stars, cat_stars, img_w,img_h,px_limit,image):
   px_limit_s = px_limit
   img_cpy = image.copy()
   hw = int(img_w / 2)
   hh = int(img_h / 2)
   cv2.imshow('pepe', image)
   cv2.waitKey(40)
   px_limit = float(px_limit)
   cat_stars = list(set(cat_stars))
   good_stars = []
   for cat_star in cat_stars:
      image = img_cpy.copy() 
      matches = []
      name, common_name, ra, dec, mag, astr_x,astr_y = cat_star
      name = cat_star[0] + " " + cat_star[1]
      cx = int(float(cat_star[5]))
      cy = int(float(cat_star[6]))
      dx,dy = distort_xy(cx,cy,img_w,img_h)
      dx = int(dx)
      dy = int(dy)
      cv2.rectangle(image, (cx, cy), (cx + 20, cy + 20), (255, 0, 0), 2)
      cv2.rectangle(image, (dx, dy), (dx + 10, dy + 10), (255, 0, 0), 2)
      cv2.putText(image, str(name),  (cx,cy+15), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,0,255), 1)
      cv2.line(image, (cx,cy), (dx,dy), (255), 1)
      cv2.imshow('pepe', image)
      cv2.waitKey(10)

      dx = float(dx)
      dy = float(dy)
      center_dist = calc_dist((hw,hh), (dx,dy))
      if center_dist > 600:
         px_limit = px_limit_s + 20
      if center_dist < 300:
         px_limit = px_limit_s - 10
      if 300 < center_dist < 600:
         px_limit = px_limit_s - 5 

      for mx,my in star_px:
 
         if mx - px_limit <= dx <= mx + px_limit and my - px_limit <= dy <= my  + px_limit:
            matches.append((name,common_name,ra,dec,mag,astr_x,astr_y,mx,my))
            cv2.line(image, (int(float(astr_x)),int(float(astr_y))), (int(float(mx)),int(float(my))), (255), 1)
            cv2.circle(image, (mx,my), 10, (255), 1)
            cv2.imshow('pepe', image)
            cv2.waitKey(10)
      if len(matches) == 1:
         good_stars.append(matches[0])
         matches = []   
            
   return(good_stars)


def pair_star(my_star, astr_stars,img_w,img_h,px_limit = 20, distort = 0):
   matches = []
   failed_matches = []
   mx, my = my_star
   for star in astr_stars:
      star_name, x, y = star
      x = int(float(x))
      y = int(float(y))
      if distort == 1:
         x,y = distort_xy(x,y,img_w,img_h)
      if (x - px_limit < mx < x + px_limit and y - px_limit < my < y + px_limit) :
         matches.append(star)
      elif (x - px_limit + 5 < mx < x + px_limit + 5 and y - px_limit +5 < my < y + px_limit +5) :
         matches.append(star)
      else:
         failed_matches.append(star)
       
   return(matches)

def find_non_cloudy_times(cal_date,cam_num):
   
   json_file = proc_dir + cal_date + "/" + "data/" + cal_date + "-weather-" + cam_num + ".json"
   found = check_if_solved(json_file)
   if found == 0: 
      glob_dir = proc_dir + cal_date + "/" + "images/*" + cal_date + "*" + cam_num + "*.png"
      files = glob.glob(glob_dir)
      weather_data = []
      files = sorted(files)
      for file in files:
         if "trim" not in file:
            status, stars, non_stars, cloudy_areas = check_for_stars(file)
            weather_data.append((file, status, stars, non_stars, cloudy_areas))

      save_json_file(json_file, weather_data)
   else:
      weather_data = load_json_file(json_file)

   wmin_data = {}
   for clip in weather_data:
      file, status, stars, non_stars, big_areas = clip
      (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(file)    
      f_date_str = str(fy) + "-" + str(fm) + "-" + str(fd) + "-" + str(fh) + "-" + fmin + "-00"
      if len(stars) > 30:
         status = "clear"
      #wmin = datetime.datetime.strptime(f_date_str, "%Y-%m-%d %H:%M:%S")
      wmin_data[f_date_str] = status

   return(wmin_data)

def check_for_stars(file):
   image = cv2.imread(file, 0)
   status, stars, non_stars, cloudy_areas = find_stars(image)

   return(status,stars,non_stars,cloudy_areas)

def deep_cal(cal_date, cam_num):
   weather = find_non_cloudy_times(cal_date, cam_num)
   #for wmin in weather:

   glob_dir = "/mnt/ams2/HD/" + cal_date + "*" + cam_num + "*.mp4"
   files = glob.glob(glob_dir)
   for file in files:
      if "trim" not in file and "meteor" not in file and "sync" and "linked" not in file:
         (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(file)    
      #   f_date_str = str(fy) + "-" + str(fm) + "-" + str(fd) + " " + str(fh) + ":" + fmin + ":00"
         f_date_str = str(fy) + "-" + str(fm) + "-" + str(fd) + "-" + str(fh) + "-" + fmin + "-00"
         #wmin = datetime.datetime.strptime(f_date_str, "%Y-%m-%d %H:%M:%S")
         if f_date_str in weather:
            status = weather[f_date_str]
            if status == 'clear':
               cal_file, med_stack, plate_image = make_cal_images(file)
               status, stars, non_stars, cloudy_areas = find_stars(med_stack)
               for sx,sy in stars:
                  cv2.circle(med_stack, (sx,sy), 3, (255), 1)


               small_frame = cv2.resize(med_stack, (0,0), fx=0.5, fy=0.5) 


               cv2.imshow('pepe', small_frame) 
               cv2.waitKey(40)
               if len(stars) > 10: 
                  med_stack_file = cal_file.replace(".jpg", "-med_stack.jpg")
                  cmd = "./calibrate_image.py " + cal_file
                  os.system(cmd)

               #cv2.imshow('pepe', plate_image) 
               #cv2.waitKey(40)
         #else:

def remove_close_stars(star_px):
   no_dupe_stars = [] 
   for star in star_px:
      exists = 0
      if len(star) == 5:
         star_name,sx,sy,x,y = star
      if len(star) == 2:
         sx,sy = star
      for star in no_dupe_stars:
         if len(star) == 5:
            ostar_name,ssx,ssy,ox,oy = star
         if len(star) == 2:
            ssx,ssy= star
         sx = int(sx)
         sy = int(sy)
         ssx = int(ssx)
         ssy = int(ssy)
         if ssx - 25 <= sx <= ssx + 25 and ssy - 25 <= sy <= ssy + 25 :
            exists = exists + 1

      if exists == 0:
         if len(star) == 5:
            no_dupe_stars.append((star_name,sx,sy,x,y))
         if len(star) == 2:
            no_dupe_stars.append((sx,sy))


   return(no_dupe_stars)
     
      

def make_cal_images(file):

   cal_file, med_stack_file, stars_file, solved_file = set_filenames(file)
   solved = check_if_solved(cal_file)
   #solved = 0
   if solved == 0:
      med_stack = make_med_stack(file, cal_file)
      star_px, plate_image = find_bright_pixels(med_stack, solved_file)
      cv2.imwrite(cal_file, plate_image)
      return(cal_file, med_stack, plate_image)
   else: 
      med_stack_file = cal_file.replace(".jpg", "-med_stack.jpg") 
      med_stack = cv2.imread(med_stack_file, 0)
      plate_image = cv2.imread(cal_file, 0)
      return(cal_file, med_stack, plate_image)

#or (dx - 10 < mx < dx + 10 and dy - 10 < my < dy + 10):


cv2.namedWindow('pepe')
cmd = sys.argv[1]
file = sys.argv[2]

if cmd == 'deep_cal':
   cal_date = sys.argv[2]
   cam = sys.argv[3]
   deep_cal(cal_date,cam)

if cmd == 'cal':
   cal_file, med_stack_file, stars_file, solved_file = set_filenames(file)
   (cal_date, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(file)    
   solved = check_if_solved(med_stack_file)
   if solved == 0:
      med_stack = make_med_stack(file, cal_file)
      star_px, plate_image = find_bright_pixels(med_stack, solved_file)
      cv2.imwrite(cal_file, plate_image)
      if len(star_px) > 10:
         cmd = "./calibrate_image.py " + cal_file
         os.system(cmd)
   else:
      med_stack = get_image(med_stack_file)
      star_px, plate_image = find_bright_pixels(med_stack, solved_file)
  
      h,w = plate_image.shape
      hh = int(h / 1.5)
      hw = int(w / 1.5)
   

      astr_stars = load_stars(stars_file)

      grid_file = stars_file.replace("-stars.txt", "-grid.png")
      grid_image = Image.open(grid_file)
      star_image = draw_star_image(med_stack, star_px, astr_stars, grid_image, stars_file,cal_date)

      cv2.imshow('pepe', star_image)
      cv2.waitKey(0)


