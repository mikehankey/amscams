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
import glob
import brightstardata as bsd
from caliblib import distort_xy
mybsd = bsd.brightstardata()
bright_stars = mybsd.bright_stars

import time
json_file = open('../conf/as6.json')
json_str = json_file.read()
json_conf = json.loads(json_str)
proc_dir = json_conf['site']['proc_dir']
lon = json_conf['site']['device_lng']
lat = json_conf['site']['device_lat']
alt = json_conf['site']['device_alt']
base_cal_dir = json_conf['site']['cal_dir']

from detectlib import load_video_frames, median_frames, convert_filename_to_date_cam, mask_frame
from caliblib import find_bright_pixels, load_stars, find_stars, save_json_file, load_json_file, parse_astr_star_file, find_star_by_name, calc_dist, get_masks, brightness, contrast, find_non_cloudy_times, summarize_weather, find_hd_file, magic_contrast

R = 6378.1

def cfe(file,dir = 0):
   if dir == 0:
      file_exists = Path(file)
      if file_exists.is_file() is True:
         return(1)
      else:
         return(0)
   if dir == 1:
      file_exists = Path(file)
      if file_exists.is_dir() is True:
         return(1)
      else:
         return(0)


def setup_cal_dir(cal_date, cam_num):

   cam_dir = "/mnt/ams2/cal/" + cam_num 
   base_dir = "/mnt/ams2/cal/" + cam_num + "/" + cal_date + "/" 
   sd = base_dir + "/solved/"
   fd = base_dir + "/failed/"
   bd = base_dir + "/bad/"
   dd = base_dir + "/data/"
   td = base_dir + "/tmp/"
   id = base_dir + "/images/"

   if cfe(cam_dir,1) == 0:
      os.system("mkdir " + cam_dir)
   if cfe(base_dir,1) == 0:
      os.system("mkdir " + base_dir)
   if cfe(sd,1) == 0:
      os.system("mkdir " + sd)
   if cfe(fd,1) == 0:
      os.system("mkdir " + fd)
   if cfe(bd,1) == 0:
      os.system("mkdir " + bd)
   if cfe(dd,1) == 0:
      os.system("mkdir " + dd)
   if cfe(td,1) == 0:
      os.system("mkdir " + td)
   if cfe(id,1) == 0:
      os.system("mkdir " + id)
   return(base_dir)   




def line_intersection(line1, line2):
    xdiff = (line1[0][0] - line1[1][0], line2[0][0] - line2[1][0])
    ydiff = (line1[0][1] - line1[1][1], line2[0][1] - line2[1][1]) #Typo was here
    x = 0
    y = 0

    def det(a, b):
        return a[0] * b[1] - a[1] * b[0]

    div = det(xdiff, ydiff)
    if div == 0:
       print("NO INTERSECT")
    else:
       d = (det(*line1), det(*line2))
       x = det(d, xdiff) / div
       y = det(d, ydiff) / div
    return x, y


def optics(cal_date, cam_num):
   lines = []
   solved_dir = base_cal_dir + cam_num + "/" + cal_date + "/solved/"
   all_json = load_all_json(cal_date,cam, solved_dir)
   image_file = all_json[0][-1]
   image_file = image_file.replace("-mapped-stars.json", ".jpg")
   print("IMAGE FILE:", image_file)
   image = cv2.imread(image_file, 0)
   img_h, img_w = image.shape
   for data in all_json:
      star_name, common_name, ra, dec, mag, cx, cy, mx, my, az, el, orig_file = data
      dist = calc_dist((cx,cy), (mx,my))
      cat_to_star_ang = calc_angle((cx,cy),(mx,my))
      dx, dy,nx,ny = distort_xy(cx,cy,img_w,img_h,0,0)
      cat_to_dist_ang = calc_angle((cx,cy),(dx,dy))

      ang_diff = abs(cat_to_dist_ang - cat_to_star_ang)


      if dist > 15 and ang_diff < 2:
         cv2.line(image, (int(cx),int(cy)), (mx,my), (255), 1)
         lines.append((cx,cy,mx,my))
         #lines.append((cx,cy,lcx,lcy))

   lcx, lcy = find_optical_center(lines)
   cv2.circle(image, (int(lcx),int(lcy)), 10, (255), 1)
   print("LENS CENTER X,Y:", lcx,lcy, (img_w/2) - lcx, (img_h/2) - lcy)
   cv2.imshow('pepe', image)
   cv2.waitKey(0)
      

def find_optical_center(lines):
   all_med_x = []
   all_med_y = []
   for i in range(0, len(lines)-1):
      all_ixs = []
      all_iys = []
      for j in range(i+1, len(lines)-1):
         A = lines[i][0],lines[i][1]
         B = lines[i][2],lines[i][3]
         C = lines[j][0],lines[j][1]
         D = lines[j][2],lines[j][3]
         ix,iy = line_intersection((A,B),(C,D))
         if ix > 0 and iy > 0:
            all_ixs.append(ix)
            all_iys.append(iy)

      if(len(all_ixs)) > 0:
         ix_median = np.median(all_ixs)
         iy_median = np.median(all_iys)
         if ix_median > 0:
            all_med_x.append(ix_median)
            all_med_y.append(iy_median)

   if len(all_med_x) > 0:
      center_x = np.median(all_med_x)
      center_y = np.median(all_med_y)
   else: 
      center_x = 0
      center_y = 0

   return(center_x, center_y)


def play_night(cal_date, cam_num, reverse = False):
   track_file = "/mnt/ams2/cal/solved/track_stars-" + cal_date + "-" + cam_num + ".txt"

   cmd = "find /mnt/ams2/cal/ |grep jpg |grep -v med_stack | grep -v bright |grep -v plate |grep -v track |grep -v mapped | grep 2019_01_11 |grep " + cam_num + " > " + track_file
   print(cmd)
   os.system(cmd)
   print(track_file)
   fp = open(track_file, "r")
   tracker = []

   for line in fp:
      line = line.replace("\n", "")
      track_file = line
      (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(line)
      tracker.append([track_file,f_datetime])


   for tfile, tdate in sorted(tracker, key=lambda x: x[1], reverse=reverse):
      img_file = tfile 
      img = cv2.imread(img_file, 0)
      cv2.imshow('pepe', img)
      cv2.waitKey(10)




def load_all_json(cal_date, cam_num,solved_dir):

   map_index_file = solved_dir + "/mapped_stars-" + cal_date + "-" + cam_num + ".txt" 
   cmd = "find " + solved_dir + " | grep " + cam_num + "-mapped-stars.json > " + map_index_file
   print(cmd)
   os.system(cmd)
   idx = open (map_index_file, "r")

   all_json_data = []
   for line in idx:
      line = line.replace("\n", "")
      json_data = load_json_file(line)
      for data in json_data:
         data.append(line)
         all_json_data.append(data)


   base_fn = all_json_data[0][-1]
   base_fn= base_fn.replace("-mapped-stars.json", ".jpg")
   
   print("BASE IMAGE:", base_fn)
   base_image = cv2.imread(base_fn)

   for data in all_json_data:
      star_name, common_name, ra, dec, mag, cx, cy, mx, my, az, el, orig_file = data
      cv2.circle(base_image, (mx,my), 10, (255), 1)
      az_txt = str(int(az)) + "/" + str(int(el))
      cv2.putText(base_image, str(az_txt),  (mx,my+15), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,0,255), 1)
   #cv2.imshow('pepe', base_image)
   #cv2.waitKey(40)   
   return(all_json_data)

def night_tracker(cal_date, cam_num, reverse=False):

   make_night_files(cal_date, cam_num)

   track_file = base_cal_dir + cam_num + "/" + cal_date + "/" + "track_stars-" + cal_date + "-" + cam_num + ".txt" 

   cmd = "find " + base_cal_dir + cam_num + "/" + cal_date + "/ |grep jpg |grep -v med_stack | grep -v trim | grep -v bright |grep -v plate |grep -v track |grep -v mapped | grep 2019_01_11 |grep " + cam_num + " > " + track_file
   print(cmd)
   os.system(cmd)
   print(track_file)

   fp = open(track_file, "r")
   tracker = []
   for line in fp:
      line = line.replace("\n", "")
      track_file = line 
      (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(line)    
      tracker.append([track_file,f_datetime])
   first_file = None
   last_tfile = None
   last_tdate = None
   image_np = None
   last_image_np = None
   alpha1 = None
   alpha_np = None


   last_solved_file = None
   lc = 0
   failed_tracks = {}
   for tfile, tdate in sorted(tracker, key=lambda x: x[1], reverse=reverse):
   #for tfile, tdate in sorted(tracker, key=lambda x: x[1], reverse=True):
      # load first tracking set
      if "solved" in tfile and first_file is None:
         med_stack = tfile.replace(".jpg", "-med_stack.jpg")
         last_solved_file = tfile
         json_file = tfile.replace(".jpg", "-mapped-stars.json")
         first_file = tfile
         first_data = load_json_file(json_file)
         first_image = cv2.imread(med_stack, 0)
         master_image = first_image.copy()
         first_image_np = np.asarray(first_image)
         master_image = draw_stars_on_img(first_image_np, first_data, "white", "box")  
         json_data = first_data
         new_json_data = json_data

         first_image_np = draw_stars_on_img(master_image, json_data, "white")  
         image_np = first_image_np
         #cv2.putText(first_image_np, "FIRST IMAGE",  (100,100), cv2.FONT_HERSHEY_SIMPLEX, .4, (255,255,255), 1)
         cv2.imshow('pepe', master_image)
         cv2.waitKey(40)
      elif "solved" in tfile :
         print ("************************ NEW SOLVE FILE! *****************************8")
         json_file = tfile.replace(".jpg", "-mapped-stars.json")
         json_data = load_json_file(json_file)
         merged_data = json_data
         master_image = draw_stars_on_img(master_image, json_data, "white", "anchor")  
         print("OLD JSON:", len(new_json_data))
         print("NEW JSON:", len(json_data))
         star_names = []

         for data in json_data:
            star_names.append(data[0])

         for data in new_json_data:
            print("OLD JSON:", lc, data[0], data)
           
            if data[0] not in star_names:
               print("DATA0", data[0], "NOT FOUND IN JSON DATA")
               merged_data.append(data)
            else:
               print("DATA0", data[0], "FOUND IN JSON DATA")
         new_json_data = merged_data

         for data in new_json_data:
            print("MERGD JSON:", lc, data)

         print("MERGED JSON:", len(new_json_data))
         image_np,new_json_data,failed_data = track_stars_in_image(image_np, new_json_data, tfile, first_file)
         master_image = draw_stars_on_img(master_image, new_json_data, "white", "trail")  
 

      if last_solved_file is not None and tfile != last_solved_file:
         print("SHAPE: ", first_image_np.shape) 
         image_np = cv2.imread(tfile, 0)
         image_np,new_json_data,failed_data = track_stars_in_image(image_np, new_json_data, tfile, first_file)
         master_image = draw_stars_on_img(master_image, new_json_data, "white", "trail")  
         for fail in failed_data:
            star_name = fail[0]
            if star_name in failed_tracks:
               failed_tracks[star_name] = failed_tracks[star_name] + 1
            else:
               failed_tracks[star_name] = 1
            if failed_tracks[star_name] <= 5:
               new_json_data.append(fail)
 

         #master_image = draw_stars_on_img(master_image, json_data, "trail")  

         if last_image_np is None:
            last_image_np = image_np


         #cv2.putText(first_image_np, "NEXT IMAGE",  (150,150), cv2.FONT_HERSHEY_SIMPLEX, .4, (255,255,255), 1)
         if lc % 2 == 0:
            cv2.imshow('pepe', image_np)
         else:
            cv2.imshow('pepe', master_image)
         cv2.waitKey(40)

      last_tfile = tfile 
      last_tdate = tdate
      if image_np is not None:
         last_image_np = image_np
      lc = lc + 1
   if reverse is True:
      sortorder = "track-back"
   else:
      sortorder = "track-forward"
   master_image_file = "/mnt/ams2/cal/master_data/" + cal_date + "_" + cam_num + "_" + sortorder + ".jpg"
   cv2.imwrite(master_image_file, master_image)
   return(master_image_file, master_image)
   
def track_stars_in_image(image, json_data, this_file, first_file)  :
   crop_size = 30
   new_data = []
   failed_data = []
   for data in json_data:
      if len(data) == 12:
         star_name, common_name, ra, dec, mag, cx, cy, mx, my, az, el, ofn= data
      if len(data) == 11:
         star_name, common_name, ra, dec, mag, cx, cy, mx, my, az, el = data

      mex = mx - crop_size 
      mxx = mx + crop_size
      mey = my - crop_size
      mxy = my + crop_size

      crop_img = image[mey:mxy,mex:mxx]

      min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(crop_img)
      bx, by = max_loc

      px_diff = max_val - min_val

      cv2.rectangle(image, (mex, mey), (mxx, mxy), (255, 0, 0), 2)
      #cv2.putText(image, str(first_file),  (100,100), cv2.FONT_HERSHEY_SIMPLEX, .4, (255,255,255), 1)
      #cv2.putText(image, str(this_file),  (100,150), cv2.FONT_HERSHEY_SIMPLEX, .4, (255,255,255), 1)

      #cv2.circle(image, (mx,my), 20, (255), 1)
      #cv2.imshow('pepe', image)
      #cv2.waitKey(10)

      mcx = int(mx + bx - crop_size)
      mcy = int(my + by - crop_size)
      print("TRACK: MX,MY,BX,BY,MCX,MCY:", star_name, mx,my,bx,by,mcx,mcy,bx-20,by-20, px_diff)
      ax = abs(bx - crop_size)
      ay = (by - crop_size)
      if px_diff > 10 and (ax < crop_size and ay < crop_size):
         print("STAR TRACKED:", px_diff)
         new_data.append([star_name, common_name, ra, dec, mag, cx, cy, mcx, mcy, az, el])
      else:
         print("TRACK PX DFF FAILED:", px_diff)
         #cv2.circle(image, (mx,my), 20, (255), 1)
         failed_data.append([star_name, common_name, ra, dec, mag, cx, cy, mcx, mcy, az, el])
   return(image, new_data, failed_data)

 
def draw_stars_on_img(image_np, json_data, color="white", track_type="box")  :
   image = Image.fromarray(image_np)
   draw = ImageDraw.Draw(image)
   font = ImageFont.truetype("/usr/share/fonts/truetype/freefont/FreeSans.ttf", 12, encoding="unic" )
   for data in json_data:
      if len(data) == 12:
         star_name, common_name, ra, dec, mag, cx, cy, mx, my, az, el,ofn = data
      if len(data) == 11:
         star_name, common_name, ra, dec, mag, cx, cy, mx, my, az, el = data
      az_txt = str(star_name) + " " + str(int(az)) + "/" + str(int(el))
      if track_type == "box":
         draw.rectangle((mx-20, my-20, mx + 20, my + 20), outline=color)
         draw.text((mx-35, my+30), str(az_txt), font = font, fill=color)
      if track_type == "trail":
         draw.ellipse((mx-1, my-1, mx+1, my+1),  outline ="white")
      if track_type == "anchor":
         draw.ellipse((mx-3, my-3, mx+3, my+3),  outline ="white")
   image_np = np.asarray(image)
   #cv2.imshow('pepe', image_np)
   #cv2.waitKey(10)
   return(image_np)
   


 
    

   


   

def calc_angle(pointA, pointB):
  changeInX = pointB[0] - pointA[0]
  changeInY = pointB[1] - pointA[1]
  ang = math.degrees(math.atan2(changeInY,changeInX)) #remove degrees if you want your answer in radians
  if ang < 0 :
     ang = ang + 360
  return(ang)


def ffmpeg_dump_cal_frame(video_file, cam_num):
   el = video_file.split("/")
   jpg_file = el[-1]
   final_out = jpg_file.replace(".mp4", ".jpg")
   final_out = base_cal_dir + "/tmp/" + final_out
   jpg_file = jpg_file.replace(".mp4", "%d.jpg")
   jpg_out = base_cal_dir + "/tmp/" + jpg_file 
   print(final_out)
   file_exists = Path(final_out)
   if file_exists.is_file() is False:
      syscmd = "/usr/bin/ffmpeg -i " + video_file + " -ss 00:00:01 -vframes 10 " + jpg_out
      print(syscmd)
      os.system(syscmd)

      files = glob.glob(base_cal_dir + "tmp/*.jpg")
      imgs = [] 
      for file in files:
         img = cv2.imread(file,0)
         imgs.append(img)

      print("IMGS:", len(imgs))
      med_stack = median_frames(imgs)
      #out_jpg = "/mnt/ams2/cal/" + final_out
      print("FINAL OUT:", final_out)
      cv2.imwrite(final_out, med_stack)
      status, stars = check_hd_stars(final_out, 600, 5, 10)
      time.sleep(1)
      for file in files:
         cmd = "rm " + file
         os.system(cmd)
   else:
      status, stars = check_hd_stars(final_out, cam_num, 600, 5)
   return(final_out, status, stars)

def check_hd_stars(image_file, cam_num, dlimit, blimit = 10):
   print("IMAGE FILE", image_file)
   image = cv2.imread(image_file,0)


   image = magic_contrast(image) 
   status, stars, center_stars, non_stars, cloudy_areas = find_stars(image, 1, dlimit, blimit)


   if len(stars) > 10:
      print ("Calibrate this one?")
      #time.sleep(10)
      img = image 
      #img = magic_contrast(img) 
      for star in stars:
         x,y = star
         cv2.circle(img, (x,y), 10, (255), 1)
         
      masks = get_masks(cam_num, 1)
      print("MASKS:",  masks)
      for mask in masks:
         msx,msy,msw,msh = mask.split(",")
         print("ASK: ", msx,msy,msw,msh)
         img[int(msy):int(msy)+int(msh),int(msx):int(msx)+int(msw)] = 0



     

      #cv2.imshow('pepe', img)
      #cv2.waitKey(1)
      #cmd = "./calibrate_image.py " + image_file 
      #os.system(cmd)


   return(status, stars)

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


def make_med_stack(file, cal_file):
   print ("VIDEO FILE: ", file)
   print ("CAL FILE: ", cal_file)
   med_stack_fn = cal_file.replace(".jpg", "-med_stack.jpg")
   frames = load_video_frames(file, 30)
   med_stack = median_frames(frames)
   print("MED STACK SIZE:", med_stack.shape)
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
   mag3_stars = pair_stars(star_px, bright_stars_found,img_w,img_h,10,med_stack)

   bright_stars_found,not_found = parse_astr_star_file(star_data_file, 3.1, 4)
   mag4_stars = pair_stars(star_px, bright_stars_found,img_w,img_h,10,med_stack)

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

def pair_stars(my_stars, cat_stars, img_w,img_h,px_limit,image,center_off_x=0,center_off_y=0):
   #px_limit = px_limit + 20
   px_limit_s = px_limit 
   img_cpy = image.copy()
   hw = int(img_w / 2)
   hh = int(img_h / 2)
   #cv2.imshow('pepe', image)
   #cv2.waitKey(40)
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
      dx,dy,nx,ny = distort_xy(cx,cy,img_w,img_h,center_off_x,center_off_y)
      dx = int(dx)
      dy = int(dy)
      cv2.rectangle(image, (cx, cy), (cx + 20, cy + 20), (255, 0, 0), 2)
      cv2.rectangle(image, (dx, dy), (dx + 10, dy + 10), (255, 0, 0), 2)
      cv2.putText(image, str(name),  (cx,cy+15), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,0,255), 1)
      cv2.line(image, (cx,cy), (dx,dy), (255), 1)
   #   cv2.imshow('pepe', image)
   #   cv2.waitKey(10)

      dx = float(dx)
      dy = float(dy)
      center_dist = calc_dist((hw,hh), (dx,dy))
      if center_dist > 600:
         px_limit = px_limit_s + 5
      #if center_dist < 300:
      #   px_limit = px_limit_s - 10
      #if 300 < center_dist < 600:
      #   px_limit = px_limit_s - 5 

      cat_to_dist_ang = calc_angle((cx,cy),(dx,dy))
      cat_to_dist_dist = calc_dist((cx,cy),(dx,dy))
 

#star_px
      for mx,my in my_stars:
         #print("PAIR:", cat_to_dist_ang, cat_to_dist_dist)
         if mx - px_limit <= dx <= mx + px_limit and my - px_limit <= dy <= my  + px_limit:
            passed = 1
            cat_to_star_ang = calc_angle((cx,cy),(mx,my))
            if cat_to_dist_dist > 20:
               if abs(cat_to_dist_ang - cat_to_star_ang)  > 1:
                  passed = 0
              
            if passed == 1: 
               ang_desc = str(cat_to_dist_ang) + " / " + str(cat_to_star_ang)
               matches.append((name,common_name,ra,dec,mag,astr_x,astr_y,mx,my))
               cv2.line(image, (int(float(astr_x)),int(float(astr_y))), (int(float(mx)),int(float(my))), (255), 1)
               cv2.putText(image, str(ang_desc),  (cx,cy+15), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,0,255), 1)
               cv2.circle(image, (mx,my), 10, (255), 1)
               #cv2.imshow('pepe', image)
               #cv2.waitKey(40)
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
         x,y,nx,ny  = distort_xy(x,y,img_w,img_h)
      if (x - px_limit < mx < x + px_limit and y - px_limit < my < y + px_limit) :
         matches.append(star)
      elif (x - px_limit + 5 < mx < x + px_limit + 5 and y - px_limit +5 < my < y + px_limit +5) :
         matches.append(star)
      else:
         failed_matches.append(star)
       
   return(matches)



def map_cal(cal_file):
   print("CAL:", cal_file)
   el = cal_file.split("/")
   file_name = el[-1]  
   base_name = file_name.replace(".jpg", "")
   video_file = "/mnt/ams2/HD/" + base_name + ".mp4"
   plate_file = cal_file
   med_stack_file = cal_file
   grid_file = cal_file.replace(".jpg", "-grid.png")
   star_data_file = cal_file.replace(".jpg", "-stars.txt")

   med_stack = cv2.imread(med_stack_file, 0)
   print("MED:", med_stack_file )
   print("MED:", med_stack_file, med_stack.shape)
   grid_image = Image.open(grid_file)
   (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(video_file)    
   status, stars = check_hd_stars(plate_file, 1200, 10)
   map_stars(stars, star_data_file, med_stack, grid_image, f_datetime, cam)

def map_cals(cal_date, cam_num):

   solved_dir = base_cal_dir + cam_num + "/" + cal_date + "/solved/"
   files = glob.glob(solved_dir + "*-grid.png" )
   print(solved_dir + "*-grid.png" )
   for file in files:
      if True:
         print(file)
         el = file.split("/")
         grid_file_name = el[-1]  
         base_file_name = grid_file_name.replace("-grid.png", "")  
        
         video_file = "/mnt/ams2/HD/" + base_file_name + ".mp4"
         plate_file = solved_dir + "/" + base_file_name + ".jpg" 
         med_stack_file = solved_dir + "/" + base_file_name + "-med_stack.jpg" 
         grid_file = solved_dir + "/" + base_file_name + "-grid.png" 
         star_data_file = solved_dir + "/" + base_file_name + "-stars.txt" 

         print("MS", med_stack_file)
         med_stack = cv2.imread(med_stack_file, 0)
         grid_image = Image.open(grid_file)
         (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(video_file)    
         status, stars = check_hd_stars(plate_file, cam_num, 1200, 10)
         map_stars(stars, star_data_file, med_stack, grid_image, f_datetime, cam_num)

def map_stars(star_px, star_data_file, med_stack, grid_image, cal_date, cam_num):

   mapped_star_file = star_data_file.replace("-stars.txt", "-mapped-stars.json") 
   med_stack_pil = Image.fromarray(med_stack)
   img_h,img_w = med_stack.shape
   med_stack_pil = med_stack_pil.convert("RGBA") 
   print(mapped_star_file)
   grid_image = grid_image.convert("RGBA") 
   draw = ImageDraw.Draw(med_stack_pil)
   font = ImageFont.truetype("/usr/share/fonts/truetype/freefont/FreeSans.ttf", 12, encoding="unic" )


   json_data = load_json_file("/mnt/ams2/cal/master_data/optics.json")
   print("JSON", json_data)
   center_off_x, center_off_y = json_data['optics'][cam_num]
   bright_stars_found,not_found = parse_astr_star_file(star_data_file, -10, 3)

   mag3_stars = pair_stars(star_px, bright_stars_found,img_w,img_h,10,med_stack,center_off_x,center_off_y)

   bright_stars_found,not_found = parse_astr_star_file(star_data_file, 3.1, 4)
   mag4_stars = pair_stars(star_px, bright_stars_found,img_w,img_h,10,med_stack,center_off_x,center_off_y)

   mapped_stars = []
   for good_star in mag3_stars:
      star_name, common_name, ra, dec, mag, sx, sy, mx, my = good_star
      print("CAL DATE: ", cal_date)
      (az, el) = radec_to_azel(ra,dec,lat,lon,alt, cal_date)
      azel = str('{0:.2f}'.format(az)) + " " + str( '{0:.2f}'.format(el))


      #azel = azel + str(ra) + " " + str(dec)
      print ("MAPPED STAR:", star_name, common_name, ra, dec, mag, sx,sy,mx,my, az,el)
      sx = float(sx)
      sy = float(sy)


      dx,dy,nx,ny = distort_xy(sx,sy,img_w,img_h,center_off_x,center_off_y)
      dddx,dddy,nx,ny = distort_xy(mx,my,img_w,img_h,center_off_x,center_off_y,1)
      print("DXNX:", dx,dy,nx,ny)
      cat_to_dist_ang = calc_angle((sx,sy),(dx,dy))
      cat_to_dist_dist = calc_dist((sx,sy),(dx,dy))
      cat_to_star_ang = calc_angle((sx,sy),(mx,my))
      ang_diff = int(cat_to_dist_ang - cat_to_star_ang)
      #ang_text = str(cat_to_dist_ang) + " / " + str(cat_to_star_ang) + " / " + str(ang_diff)
      ang_text = str(ang_diff)

      draw.rectangle((nx-12, ny-12, nx + 12, ny + 12), outline="red")
      draw.rectangle((mx-10, my-10, mx + 10, my + 10), outline="blue")
      draw.ellipse((dx-5, dy-5, dx+5, dy+5),  outline ="red")
      draw.ellipse((mx-5, my-5, mx+5, my+5),  outline ="blue")
      draw.ellipse((sx-5, sy-5, sx+5, sy+5),  outline ="green")
      draw.line((mx,my, sx,sy), fill=255)
      draw.text((sx-10, sy-20), str(common_name + "(" + str(star_name) + ")"), font = font, fill=(255,255,255))
      draw.text((sx-10, sy-30), azel , font = font, fill=(255,255,255))
      draw.text((sx-30, sy), ang_text, font = font, fill=(0,255,255))
      mapped_stars.append((star_name, common_name, ra, dec, mag, sx, sy, mx, my,az,el))
   #cv2.imshow('pepe', np.asarray(med_stack_pil))
   #cv2.waitKey(10)

   for good_star in mag4_stars:
      star_name, common_name, ra, dec, mag, sx, sy, mx, my = good_star
      (az, el) = radec_to_azel(ra,dec,lat,lon,alt, cal_date)
      azel = str('{0:.2f}'.format(az)) + " " + str( '{0:.2f}'.format(el))
      #azel = azel + str(ra) + " " + str(dec)
      sx = float(sx)
      sy = float(sy)
      dx,dy,nx,ny = distort_xy(sx,sy,img_w,img_h,center_off_x,center_off_y)
      dddx,dddy,nx,ny = distort_xy(mx,my,img_w,img_h,center_off_x,center_off_y,1)

      cat_to_dist_ang = calc_angle((sx,sy),(dx,dy))
      cat_to_dist_dist = calc_dist((sx,sy),(dx,dy))
      cat_to_star_ang = calc_angle((sx,sy),(mx,my))
      ang_diff = int(cat_to_dist_ang - cat_to_star_ang)
      #ang_text = str(cat_to_dist_ang) + " / " + str(cat_to_star_ang) + " / " + str(ang_diff)
      ang_text = str(ang_diff)

      draw.rectangle((nx-12, ny-12, nx + 12, ny + 12), outline="red")
      draw.rectangle((mx-10, my-10, mx + 10, my + 10), outline="blue")
      draw.ellipse((dx-5, dy-5, dx+5, dy+5),  outline ="red")
      draw.ellipse((mx-5, my-5, mx+5, my+5),  outline ="blue")
      draw.ellipse((sx-5, sy-5, sx+5, sy+5),  outline ="green")
      draw.text((sx-30, sy), ang_text, font = font, fill=(0,255,255))
      draw.line((mx,my, sx,sy), fill=255)
      draw.text((sx-10, sy-20), str(common_name + "(" + str(star_name) + ")"), font = font, fill=(255,255,255))
      draw.text((sx-10, sy-30), azel , font = font, fill=(255,255,255))
      mapped_stars.append((star_name, common_name, ra, dec, mag, sx, sy, mx, my,az,el))
   #cv2.imshow('pepe', np.asarray(med_stack_pil))
   #if cmd == 'map_cal':
   #   cv2.waitKey(10)
   #else:
   #   cv2.waitKey(10)
   
   map_image = mapped_star_file.replace(".json", ".jpg")
   print("MAP IMAGE:", map_image)
   cv2.imwrite(map_image, np.asarray(med_stack_pil))
   
   save_json_file(mapped_star_file, mapped_stars)
   print("DONE MAPPED STARS:", mapped_star_file)

def check_status(video_file):
   cal_file_exists = 0
   solved_cal_file_exists = 0
   failed_cal_file_exists = 0
   bad_cal_file_exists = 0
   el = video_file.split("/")
   fnbase = el[-1].replace(".mp4", "")
   cal_file = "/mnt/ams2/cal/" + fnbase + ".jpg"
   solved_cal_file = "/mnt/ams2/cal/solved/" + fnbase + "/" + fnbase + ".jpg"
   failed_cal_file = "/mnt/ams2/cal/failed/" + fnbase + "/" + fnbase + ".jpg"
   bad_cal_file = "/mnt/ams2/cal/bad/" + fnbase + "/" + fnbase + ".jpg"
   file_exists = Path(cal_file)
   if file_exists.is_file is True:
      cal_file_exists = 1
   file_exists = Path(solved_cal_file)
   if file_exists.is_file is True:
      solved_cal_file_exists = 1
      cal_file_exists = 1
   file_exists = Path(failed_cal_file)
   if file_exists.is_file is True:
      failed_cal_file_exists = 1
      cal_file_exists = 1
   file_exists = Path(bad_cal_file)
   if file_exists.is_file is True:
      bad_cal_file_exists = 1
      cal_file_exists = 1
   return(cal_file_exists, solved_cal_file_exists, failed_cal_file_exists, bad_cal_file_exists)


 
 
def calibrate_image(cal_file, cal_date,cam_num):
   print("CAlibrate:", cal_file)
   masks = get_masks(cam_num)
   med_file = cal_file.replace(".jpg", "-med_stack.jpg")
   solved_file = cal_file.replace(".jpg", "-grid.png")
   masks = get_masks(cam_num, 1)
   image = cv2.imread(cal_file, 0)
   cv2.imwrite(med_file, image)
   for mask in masks:
      msx,msy,msw,msh = mask.split(",")
      print("ASK: ", msx,msy,msw,msh)
      image[int(msy):int(msy)+int(msh),int(msx):int(msx)+int(msw)] = 0

   print("CAL FILE:", cal_file)
   image = magic_contrast(image) 
   
   star_px, plate_image = find_bright_pixels(image, solved_file, cam_num)

   cv2.imwrite(cal_file, plate_image)
   
   
   cv2.putText(image, str("Calibrating this image now!"),  (200,200), cv2.FONT_HERSHEY_SIMPLEX, .8, (255,255,255), 1)
   #cv2.imshow('pepe', image)
   #cv2.waitKey(10)



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

   cmd = "/usr/local/astrometry/bin/solve-field " + cal_file + " --crpix-center --cpulimit=30 --verbose --no-delete-temp --overwrite --width=" + str(width) + " --height=" + str(height) + " --scale-low 50 --scale-high 90 > " + astr_out + " 2>&1"
   print(cmd)
   os.system(cmd)
   os.system("grep Mike " + astr_out + " >" +star_data_file + " 2>&1" )

   cmd = "/usr/bin/jpegtopnm " + cal_file + "|/usr/local/astrometry/bin/plot-constellations -w " + wcs_file + " -o " + grid_file + " -i - -N -C -G 600"
   os.system(cmd)

   cmd = "/usr/local/astrometry/bin/wcsinfo " + wcs_file + " > " + wcs_info_file
   os.system(cmd)

   bright_star_data = parse_astr_star_file(star_data_file)
   #plot_bright_stars(cal_file, image, bright_star_data)
   solved = cfe(grid_file)

   return(solved)
 

def batch_cal(wmdata, cal_date, cam_num):
   base_cal_dir = setup_cal_dir(cal_date, cam_num)
   masks = get_masks(cam_num, 1)
   for wdata in wmdata:
      (file, status, stars, center_stars, non_stars, cloudy_areas) = wdata
      if status == 'calibrate':
         hd_file = find_hd_file(file)

         cal_file, status, stars = ffmpeg_dump_cal_frame(hd_file, cam_num)
         el = cal_file.split("/")
         cal_file_name = el[-1]
         print("mv " + cal_file + " " + base_cal_dir + "/tmp/")
         tmp_cal_file = base_cal_dir + "/tmp/" + cal_file_name
         cmd = "mv " + cal_file + " " + tmp_cal_file
         os.system(cmd)
         solved = calibrate_image(tmp_cal_file, cal_date, cam_num)
         if solved == 1:
            #cmd = "mkdir " + base_cal_dir + "/solved/" + cal_date
            #print(cmd)
            #os.system(cmd)
            cmd = "mv " + base_cal_dir + "/tmp/" + cal_date + "* " + base_cal_dir + "/solved/" 
            print(cmd)
            os.system(cmd)
         else:
            cmd = "mv " + cal_file + " " + base_cal_dir + "/failed/"
            os.system(cmd)
            cmd = "rm " + base_cal_dir + "/tmp/" + cal_date + "* "
            os.system(cmd)


def make_night_files(cal_date, cam_num):
   base_cal_dir = setup_cal_dir(cal_date, cam_num)
   cal_files = []
   masks = get_masks(cam_num)
   print("MASKS", masks)
   glob_dir = "/mnt/ams2/HD/" + cal_date + "*" + cam_num + "*.mp4"
   files = glob.glob(glob_dir)
   files = sorted(files)
   fc = 0
   for file in files:
      (cfe, scfe, fcfe, bcfe) = check_status(file)
      if "trim" not in file and "meteor" not in file and "sync" not in file and "linked" not in file :
         if fc % 5 == 0:
            if cfe == 0:
               cal_file, status, stars = ffmpeg_dump_cal_frame(file, cam_num)
               cmd = "mv " + cal_file + " " + base_cal_dir + "images/"
               os.system(cmd)
               print(cal_file, status, stars)
            if scfe == 0 and fcfe == 0 and bcfe == 0:
               cal_files.append((cal_file, status, stars))
         fc = fc + 1
   print("CAL FILES:", len(cal_files))



def make_hd_cal_images(cal_date, cam_num):
   cal_files = []
   masks = get_masks(cam_num)
   print("MASKS", masks)
   glob_dir = "/mnt/ams2/HD/" + cal_date + "*" + cam_num + "*.mp4"
   files = glob.glob(glob_dir)
   files = sorted(files)
   fc = 0
   for file in files:
      (cfe, scfe, fcfe, bcfe) = check_status(file) 
      if "trim" not in file and "meteor" not in file and "sync" not in file and "linked" not in file :
         if fc % 1 == 0:
            if cfe == 0:
               cal_file, status, stars = ffmpeg_dump_cal_frame(file, cam_num)
               print(cal_file, status, stars)
            if scfe == 0 and fcfe == 0 and bcfe == 0:
               cal_files.append((cal_file, status, stars))
         fc = fc + 1
   print("CAL FILES:", len(cal_files))

   good_cal = []
   bad_cal = []
   for cal_data in cal_files:
      cal_file, status, stars = cal_data
      if status == 'clear':
         if len(stars) > 10:
            good_cal.append(cal_data)
         else:
            bad_cal.append(cal_data)
      else:
         bad_cal.append(cal_data)
   print("GOOD CAL:", len(good_cal))
   print("BAD CAL:", len(bad_cal))
   cd = 0
   for cal_data in good_cal:
      cal_file, status, stars = cal_data
      if cd % 30 == 1:
         el = cal_file.split("/")
         fn = el[-1]
         med_stack_file = cal_file.replace(".jpg", "-med_stack.jpg")
         fn_base = fn.replace(".jpg", "")
         solved_dir = "/mnt/ams2/cal/solved/" + fn_base + "/"
         grid_file = solved_dir + fn_base + "-grid.png" 
         star_data_file = solved_dir + fn_base + "-stars.txt" 
         plate_file = solved_dir + fn_base + "-plate.jpg" 
         new_cal_file = solved_dir + fn_base + ".jpg" 
         video_file = cal_file
         video_file = video_file.replace(".jpg", ".mp4") 
         video_file = video_file.replace("cal", "HD") 
         med_stack = make_med_stack(video_file, cal_file)
         print("DEBUG fn_base:", fn_base)
         print("DEBUG solved_dir:", solved_dir)
         print("DEBUG plate_file:", plate_file)
         print("DEBUG star_data_file:", star_data_file)
         print("DEBUG star_data_file:", star_data_file)
         print("DEBUG video_file:", video_file)
         print("DEBUG cal_file:", cal_file)


         med_stack = mask_frame(med_stack, masks) 
         print("MED STACK!!!", masks)

         print("MED STACK SHAPE", med_stack.shape)
         star_px, plate_image = find_bright_pixels(med_stack, plate_file, cam_num)
         print("SIZE:", plate_image.shape) 
  
         cv2.putText(med_stack, str("GAY!"),  (mx,my+15), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,0,255), 1)

         cv2.imwrite(med_stack_file, med_stack)
         cv2.imwrite(cal_file, plate_image)
         #cv2.imshow('pepe', med_stack)
         #cv2.waitKey(10)
         
         cmd = "./calibrate_image.py " + cal_file
         os.system(cmd)

         solved = check_if_solved(grid_file)
         print("GRID FILE:", solved, grid_file)
         if solved == 1:
            grid_image = Image.open(grid_file)

            (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(video_file)    
            status, stars = check_hd_stars(new_cal_file, cam_num, 1200, 10)
            map_stars(stars, star_data_file, med_stack, grid_image, f_datetime, cam_num)
      cd = cd + 1 


def mkdir_if_not(dir):
   file_exists = Path(dir)
   if file_exists.is_dir() is False:
      os.system("mkdir " + dir)

def deep_cal(cal_date, cam_num):
   weather = find_non_cloudy_times(cal_date, cam_num)
   #for wmin in weather:
   solved_dir = "/mnt/ams2/HD/solved/" + cal_date
   failed_dir = "/mnt/ams2/HD/failed/" + cal_date
   bad_dir = "/mnt/ams2/HD/bad/" + cal_date
   mkdir_if_not(solved_dir)
   mkdir_if_not(failed_dir)
   mkdir_if_not(bad_dir)
   

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
                
               #cal_file, med_stack, plate_image = make_cal_images(file)
               status, stars, center_stars, non_stars, cloudy_areas = find_stars(med_stack, center=1)
               for sx,sy in stars:
                  cv2.circle(med_stack, (sx,sy), 3, (255), 1)


               small_frame = cv2.resize(med_stack, (0,0), fx=0.5, fy=0.5) 


               #cv2.imshow('pepe', small_frame) 
               #cv2.waitKey(40)
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
      star_px, plate_image = find_bright_pixels(med_stack, solved_file, cam_num)
      cv2.imwrite(cal_file, plate_image)
      return(cal_file, med_stack, plate_image)
   else: 
      med_stack_file = cal_file.replace(".jpg", "-med_stack.jpg") 
      med_stack = cv2.imread(med_stack_file, 0)
      plate_image = cv2.imread(cal_file, 0)
      return(cal_file, med_stack, plate_image)

def help():
   text = """
### PLAY DATA SET FOR ONE NIGHT ###
./calib-gen2.py play cal_date cam
./calib-gen2.py play 2019_01_11 010001

### FIND FOV CENTER USING ONE NIGHT OF CALIB DATA ###
./calib-gen2.py optics cal_date cam
./calib-gen2.py optics 2019_01_11 010001

### MAP STARS FOR ONE CALIBRATION RUN ###
./calib-gen2.py map_cal calibration_file
./calib-gen2.py map_cal /mnt/ams2/cal/010001/solved/YYYY....../cal_file_name.jpg

### MAP STARS FOR ALL CALIBRATION RUNS FOR ONE NIGHT AND CAMERA ###
./calib-gen2.py map_cals cal_date cam
./calib-gen2.py map_cals 2019_01_11 010001

### DEEP CAL ###
./calib-gen2.py deep_cal cal_date cam
 * Need to rework..

### WEATHER - Find best possible calibration files for the night based on the weather. ###
./calib-gen2.py weather cal_date cam

### NIGHT TRACKER - track stars for entire night
./calib-gen2.py weather cal_date cam

### CAL DIR - setup default calibration dirs for cam and day
./calib-gen2.py cal_dir cal_date cam

### CAL - calibrate a single file
./calib-gen2.py cal cal_date cam

####  HOW TO RUN / SEQUENCE TO RUN THINGS ###

for one night
   for each cam and 

      1) Determine first if the weather was good enough to calibrate. If it was, calibrate 3 frames per hour where possible. 

      ./calib-gen2.py weather cal_date cam
 
      2) Map the calibrations (should be done automatically), but if you want to redo them. 

      ./calib-gen2.py map_cals cal_date cam

      3) Find the optical field of view

      ./calib-gen2.py optics cal_date cam

      4) Re map the calibrations

      ./calib-gen2.py map_cals cal_date cam

      5) For the hours with stars, track them through the entire night 

      ./calib-gen2.py night_tracker cal_date cam
 
   

"""
   print(text)


   

cv2.namedWindow('pepe')
cmd = sys.argv[1]

if cmd == "help":
   help()

if cmd == 'play':
   cal_date = sys.argv[2]
   cam = sys.argv[3]
   play_night(cal_date, cam)

if cmd == 'optics':
   cal_date = sys.argv[2]
   cam = sys.argv[3]
   #all_json = load_all_json(cal_date, cam)
   optics(cal_date, cam)

if cmd == 'map_cal':
   cal_file = sys.argv[2]
   map_cal(cal_file)

if cmd == 'map_cals':
   cal_date = sys.argv[2]
   cam = sys.argv[3]
   #deep_cal(cal_date,cam)
   map_cals(cal_date,cam)


if cmd == 'deep_cal':
   cal_date = sys.argv[2]
   cam = sys.argv[3]
   #deep_cal(cal_date,cam)
   make_hd_cal_images(cal_date,cam)

if cmd == 'weather':
   cal_date = sys.argv[2] 
   cam_num = sys.argv[3] 
   weather = find_non_cloudy_times(cal_date, cam_num)
   summarize_weather(weather)
   #for wdata in weather:
   #   (file, status, stars, center_stars, non_stars, cloudy_areas) = wdata
   #   print(file,status)
   batch_cal(weather, cal_date, cam_num)

if cmd == 'night_tracker':
   cal_date = sys.argv[2] 
   cam_num = sys.argv[3] 
   mf1,mimg1 = night_tracker(cal_date, cam_num, True)
   mf2,mimg2 = night_tracker(cal_date, cam_num, False)
   pic1 = Image.fromarray(mimg1)
   pic2 = Image.fromarray(mimg2)
   alpha = Image.blend(pic1, pic2, .4)
   alpha_cv = np.asarray(alpha)
   cv2.imshow('pepe', alpha_cv)
   cv2.waitKey(0)
   #/mnt/ams2/cal/solved/track_stars-2019_01_11-010001.txt

if cmd == 'cal_dir':
   cal_date = sys.argv[2] 
   cam_num = sys.argv[3] 
   setup_cal_dir(cal_date, cam_num)
   
if cmd == 'cal':
   cal_file, med_stack_file, stars_file, solved_file = set_filenames(file)
   (cal_date, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(file)    
   solved = check_if_solved(med_stack_file)
   if solved == 0:
      med_stack = make_med_stack(file, cal_file)
      star_px, plate_image = find_bright_pixels(med_stack, solved_file, cam_num)
      cv2.imwrite(cal_file, plate_image)
      if len(star_px) > 10:
         cmd = "./calibrate_image.py " + cal_file
         os.system(cmd)
   else:
      med_stack = get_image(med_stack_file)
      star_px, plate_image = find_bright_pixels(med_stack, solved_file, cam_num)
  
      h,w = plate_image.shape
      hh = int(h / 1.5)
      hw = int(w / 1.5)
   

      astr_stars = load_stars(stars_file)

      grid_file = stars_file.replace("-stars.txt", "-grid.png")
      grid_image = Image.open(grid_file)
      star_image = draw_star_image(med_stack, star_px, astr_stars, grid_image, stars_file,cal_date)
      #cv2.imshow('pepe', star_image)
      #cv2.waitKey(10)


