#!/usr/bin/python3

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


json_file = open('../conf/as6.json')
json_str = json_file.read()
json_conf = json.loads(json_str)
proc_dir = json_conf['site']['proc_dir']


from detectlib import load_video_frames, median_frames, convert_filename_to_date_cam
from caliblib import find_bright_pixels, load_stars, find_stars, save_json_file, load_json_file

def distort_xy(x,y,img_w,img_h):
   strength = 1.8
   zoom = 1
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
   if newX % 1000 == 0:
      print ("NEW X,Y", x,y)
      print ("SOURCEX,Y", sourceX,sourceY)
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
   filename_base = filename.replace(".mp4", "")

   cal_file = "/mnt/ams2/cal/" + filename

   cal_file = cal_file.replace(".mp4", ".jpg")



   solved_file = "/mnt/ams2/cal/solved/" + filename_base + "/" + filename_base + ".jpg"
   med_stack_file = "/mnt/ams2/cal/solved/" + filename_base + "/" + filename_base + "-med_stack.jpg"
   stars_file = "/mnt/ams2/cal/solved/" + filename_base + "/" + filename_base + "-stars.txt"

   return(cal_file, med_stack_file, stars_file, solved_file)

def check_if_solved(solved_file):
   print(solved_file)
   file_exists = Path(solved_file)
   if file_exists.is_file() is True:
      return(1)
   else:
      return(0)

def get_image(file):
   #print("GET:", file)
   #exit()
   img = cv2.imread(file, 0 )
   return(img)

def draw_star_image(med_stack, star_px, astr_stars):
   med_stack_pil = Image.fromarray(med_stack)
   img_h,img_w = med_stack.shape
   
   draw = ImageDraw.Draw(med_stack_pil)
   font = ImageFont.truetype("/usr/share/fonts/truetype/freefont/FreeSans.ttf", 12, encoding="unic" )


   for mx,my in star_px:
      my_star = (mx,my)
      #if img_w - 500 < mx < img_w + 500: 
      if True:
         matches = pair_star(my_star, astr_stars,img_w,img_h)
            
         if len(matches) == 1:
            star_name, x,y = matches[0]
            x = int(float(x))
            y = int(float(y))
            print ("MY STAR: ", mx,my,star_name, x,y)
            draw.rectangle((mx-7, my-7, mx+7, my+7),  outline ="orange")
            draw.ellipse((x-7, y-7, x+7, y+7),  outline ="orange")
            draw.text((x-10, y+10), str(star_name), font = font, fill=(255))
            draw.line((x-7,y-7, mx-7,my-7), fill="white")

   for star in astr_stars:
      star_name, x, y = star
      x = int(float(x))
      y = int(float(y))
      dx,dy = distort_xy(x,y,img_w,img_h)
      print(star_name, x,y) 
      #draw.ellipse((dx-3, dy-3, dx+3, dy+3),  outline ="orange")
      #draw.rectangle((x-2, y-2, x+2, y+2),  outline ="orange")
      #draw.line((x,y, dx,dy), fill="white")
    #  draw.rectangle((dx-5, dy-5, dx+5, dy+5),  outline ="orange")

   
   return(np.asarray(med_stack_pil))

def pair_star(my_star, astr_stars,img_w,img_h):
   matches = []
   failed_matches = []
   mx, my = my_star
   for star in astr_stars:
      star_name, x, y = star
      x = int(float(x))
      y = int(float(y))
      x,y = distort_xy(x,y,img_w,img_h)
      if (x - 20 < mx < x + 20 and y - 20 < my < y + 20) :
         matches.append(star)
      elif (x - 25 < mx < x + 25 and y - 25 < my < y + 25) :
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
            print("FILE:", file)
            status, stars, non_stars, cloudy_areas = check_for_stars(file)
            weather_data.append((file, status, stars, non_stars, cloudy_areas))

      print("JSON FILE:", json_file)
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
   print("CHECK IN ", file)
   image = cv2.imread(file, 0)
   status, stars, non_stars, cloudy_areas = find_stars(image)

   return(status,stars,non_stars,cloudy_areas)

def deep_cal(cal_date, cam_num):
   weather = find_non_cloudy_times(cal_date, cam_num)
   #for wmin in weather:
   #   print(wmin, weather[wmin])

   glob_dir = "/mnt/ams2/HD/" + cal_date + "*" + cam_num + "*.mp4"
   print(glob_dir)
   files = glob.glob(glob_dir)
   for file in files:
      if "trim" not in file and "meteor" not in file and "sync" and "linked" not in file:
         print("FILE:", file)
         (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(file)    
      #   f_date_str = str(fy) + "-" + str(fm) + "-" + str(fd) + " " + str(fh) + ":" + fmin + ":00"
         f_date_str = str(fy) + "-" + str(fm) + "-" + str(fd) + "-" + str(fh) + "-" + fmin + "-00"
         #wmin = datetime.datetime.strptime(f_date_str, "%Y-%m-%d %H:%M:%S")
         if f_date_str in weather:
            status = weather[f_date_str]
            if status == 'clear':
               print(status, cam, file)
               cal_file, med_stack, plate_image = make_cal_images(file)
               status, stars, non_stars, cloudy_areas = find_stars(med_stack)
               print("MIKE STARS:", len(stars))
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
         #   print("weather data missing for this time:", f_date_str)

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
   print("done with ", cal_file)

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
   solved = check_if_solved(med_stack_file)
   print ("SOLVED:", solved)
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
      print("MY STAR PX:", star_px)
      print("STARS:", astr_stars)

      cv2.imshow('pepe', med_stack)
      cv2.waitKey(0)
      star_image = draw_star_image(med_stack, star_px, astr_stars)

      cv2.imshow('pepe', star_image)
      cv2.waitKey(0)


