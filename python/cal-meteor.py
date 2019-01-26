#!/usr/bin/python3

import os
import datetime
import cv2
import numpy as np
import calmeteorlib
import sys
from PIL import Image, ImageChops, ImageDraw, ImageFont

show = 0

from calmeteorlib import xy_to_radec, radec_to_azel
from caliblib import load_json_file, save_json_file, calc_dist, find_bright_pixels
from detectlib import load_video_frames, cfe, magic_contrast,convert_filename_to_date_cam
import json 

json_file = open('../conf/as6.json')
json_str = json_file.read()
json_conf = json.loads(json_str)
proc_dir = json_conf['site']['proc_dir']
lon = json_conf['site']['device_lng']
lat = json_conf['site']['device_lat']
alt = json_conf['site']['device_alt']
base_cal_dir = json_conf['site']['cal_dir']

def fixup_image(image):
   image.setflags(write=1)
   print("SHAPE:", image.shape)
   if image.shape == 3:
      image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
   avg_px = np.mean(image)
   for x in range(0,image.shape[1]):
      for y in range(0,image.shape[0]):
         if image[y,x] <= avg_px + 10:
            image[y,x] = 10 
         else:
            image[y,x] = image[y,x] * 2
   return(image)

def stack_stack(pic1, pic2):
   pic1_im = Image.fromarray(pic1)
   pic2_im = Image.fromarray(pic2)
   stacked_image=ImageChops.lighter(pic1_im,pic2_im)
   stacked_image_np = np.asarray(stacked_image)
   return(stacked_image_np)

def stack_plate(frames,meteor_json_frames):
   meteor_frames = []
   plate_stack = frames[0]
   first = None
   for key in meteor_json_frames:
      if first is None:
         first = int(key)
      meteor_frames.append(int(key))
      last = int(key)

   for x in range(first-3,last+30):
      meteor_frames.append(x)
   #for x in range(last+10,last+30):
   #   meteor_frames.append(x)


   fn = 0
   for frame in frames:
      if fn < 10:
         plate_stack = stack_stack(plate_stack, frame) 
      fn = fn + 1

   return(plate_stack)

def make_plate_crop(hd_trim, meteor_json): 
   frames = load_video_frames(hd_trim)
   (bmin_x,bmin_y,bmax_x,bmax_y) = meteor_json['box']
   (bbmin_x,bbmin_y,bbmax_x,bbmax_y) = meteor_json['bigger_box']
   trim_stack_img = cv2.imread(trim_stack, 0)
   plate_image = stack_plate(frames, meteor_json['frames'])
   plate_crop = plate_image[bbmin_y:bbmax_y,bbmin_x:bbmax_x]
   print("PLATECROP:", plate_crop.shape)
   return(plate_crop)

def decode_points(plate_crop, meteor_json,wcs_file):
   start_time = None
   moving = 0
   last_dist = None
   sdist = None
   fc = 0
   for key in meteor_json['frames']:
      end_time = meteor_json['frames'][key]['frame_time']
      x,y,w,h = meteor_json['frames'][key]['xywh']
      mx,my = meteor_json['frames'][key]['mxmy']
      cx,cy = meteor_json['frames'][key]['cxcy']
      if start_time is None:
         start_time = meteor_json['frames'][key]['frame_time']
         start_cy = cy
         start_cx = cx

      ra,dec,rad,decd = xy_to_radec (wcs_file, x, y)
      az,el = radec_to_azel(ra,dec,lat,lon,alt, start_time)
      meteor_json['frames'][key]['radec'] = [ra,dec]
      meteor_json['frames'][key]['radec_d'] = [rad,decd]
      meteor_json['frames'][key]['azel'] = [az,el]
      if fc == 0:
         meteor_json['frames'][key]['moving'] = 1
         start_radec = [ra,dec]
         start_radec_d = [rad,decd]
         start_azel = [az,el]
      else:
         sdist = abs(calc_dist((start_cx,start_cy),(cx,cy)))
         meteor_json['frames'][key]['moving'] = 1
      if last_dist is not None:
         if sdist > last_dist + 2:
            meteor_json['frames'][key]['moving'] = 1
            last_moving_frame = key
            end_radec = [ra,dec]
            end_radec_d = [rad,decd]
            end_azel = [az,el]
            last_cx = cx
            last_cx = cy
            moving = 1
            end_time = meteor_json['frames'][key]['frame_time']
         else:
            meteor_json['frames'][key]['moving'] = 0
            moving = 0
     
      print("DIST", start_cx, start_cy, cx,cy, last_dist, sdist, moving)
      if sdist is not None: 
         last_dist = sdist 

      fc = fc + 1
      

     
      #cv2.circle(plate_crop, (cx,cy), 1, (255), 1)
   if show == 1:
      cv2.imshow('pepe', plate_crop) 

   if "." in end_time:
      dt_end_time = datetime.datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S.%f")
   else:
      dt_end_time = datetime.datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
   if "." in start_time:
      dt_start_time = datetime.datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S.%f")
   else:
      dt_start_time = datetime.datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
   elp_time = (dt_end_time-dt_start_time).total_seconds()

   meteor_json['start_time'] = start_time
   meteor_json['end_time'] = end_time
   meteor_json['elp_time'] = elp_time
   meteor_json['start_radec'] = start_radec
   meteor_json['start_radec_d'] = start_radec_d
   meteor_json['start_azel'] = start_azel

   meteor_json['end_time'] = end_time
   meteor_json['end_azel'] = end_azel 
   meteor_json['end_radec'] = end_radec
   meteor_json['end_radec_d'] = end_radec_d


   return(plate_crop, meteor_json)

meteor_json_file = sys.argv[1]


meteor_json = load_json_file(meteor_json_file)
hd_trim_stack = meteor_json['hd_trim_stack']
hd_crop_stack = meteor_json['hd_crop_stack']
hd_trim_stack_img = cv2.imread(hd_trim_stack, 0)
trim_stack = meteor_json['trim_stack']
hd_trim = meteor_json['hd_trim']

cal_file = meteor_json['hd_crop_stack'].replace(".png", ".jpg")
cff = cal_file.split("/")
cal_fn = cff[-1]
meteor_day_dir = cal_file.replace(cal_fn, "")

new_wcs_file = meteor_day_dir + cal_fn
new_wcs_file = new_wcs_file.replace(".jpg", ".wcs")
new_grid_file = new_wcs_file.replace(".wcs", "-grid.png")
new_cal_file = meteor_day_dir + cal_fn
blend_file = new_wcs_file.replace(".wcs", "-blend.png")

print("WCS:", cal_fn, new_wcs_file)

cal_file = "/mnt/ams2/cal/tmp/" + cal_fn



plate_crop = make_plate_crop(hd_trim, meteor_json)

print("PLATE CROP:", cal_file)

#plate_crop = magic_contrast(plate_crop)
#plate_crop = fixup_image(plate_crop)
(f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(hd_trim)

star_px, plate_crop= find_bright_pixels(plate_crop, cal_file, cam)




noise_objs = meteor_json['noise_objs']
for obj in noise_objs:
   hist = obj['history']
   for fn,x,y,w,h,mx,my in hist:
      plate_crop[y:y+h,x:x+w] = 10

for key in meteor_json['frames']:
   x,y,w,h = meteor_json['frames'][key]['xywh']
   plate_crop[y-5:y+h+5,x-5:x+w+5] = 10
 
cv2.imwrite(cal_file, plate_crop)
print("PLATECROP:", plate_crop.shape)

if show == 1:
   cv2.namedWindow('pepe')
   cv2.imshow('pepe', plate_crop)
   cv2.waitKey(0)


print("./calibrate_image.py " + cal_file)
os.system("./calibrate_image.py " + cal_file)

wcs_file = cal_file.replace(".jpg", ".wcs")
grid_file = cal_file.replace(".jpg", "-grid.png")
bsd_file = cal_file.replace(".jpg", "-bsd.txt")





if cfe(wcs_file,0):

   print("PLATECROP:", plate_crop.shape)
   plate_crop, meteor_json = decode_points(plate_crop, meteor_json, wcs_file)
   print(meteor_json)
   bsd = load_json_file(bsd_file)
   meteor_json['bsd'] = bsd

   print("PLATE CROP Calibration Successful!") 
   meteor_json['plate_crop_solve'] = 1
   meteor_json['wcs_file'] = new_wcs_file
   meteor_json['grid_file'] = new_grid_file
   meteor_json['cal_file'] = new_cal_file
   meteor_json['blend_file'] = blend_file
   print("cp " + cal_file + " " + new_cal_file)
   print("cp " + grid_file + " " + new_grid_file)
   print("cp " + wcs_file + " " + new_wcs_file)
   os.system("cp " + cal_file + " " + new_cal_file)
   os.system("cp " + grid_file + " " + new_grid_file)
   os.system("cp " + wcs_file + " " + new_wcs_file)
else:
   print("PLATE CROP Calibration FAILED!") 
   meteor_json['plate_crop_solve'] = 0
   meteor_json['wcs_file'] = ""
   meteor_json['grid_file'] = "" 
   meteor_json['new_cal_file'] = new_cal_file


if cfe(wcs_file,0):
   hd_crop_stack_img = cv2.imread(hd_crop_stack)
   print("CROP STACK", hd_crop_stack )
   print("GRID FILE", new_grid_file )
   im1 = Image.open(hd_crop_stack)
   im1 = im1.convert("RGBA")
   w,h = im1.size
   print("W:", w,h,im1.mode)
   im2 = Image.open(new_grid_file)
   w,h = im2.size
   im2 = im2.convert("RGBA")
   print("W:", w,h,im2.mode)
   alpha_blend = Image.blend(im1, im2, alpha=.2)
   used_stars = []
   draw = ImageDraw.Draw(alpha_blend)
   font = ImageFont.truetype("/usr/share/fonts/truetype/freefont/FreeSans.ttf", 12, encoding="unic" )
   for bs in bsd:
      sn2,sn1,ra,dec,mag,sx,sy = bs.split(",")
      sx,sy = int(float(sx)),int(float(sy))
      star_name = sn1
      if star_name in used_stars:
         print("DUPE", star_name)
      else:
         print("Good", star_name, sx,sy)
         draw.rectangle((sx-5, sy-5, sx + 5, sy + 5), outline="White")
         draw.text((sx-35, sy), str(star_name), font = font, fill="White")
         used_stars.append(star_name)
   print(used_stars)
#   βCVn,Chara,188.4354,41.3575,4.2,140.746,216.197
   alpha_blend.save(blend_file)



 
   cmd = "./calib-gen2.py map_cal " + cal_file
   print(cmd)
   os.system(cmd)

   mapped_star_file = cal_file.replace(".jpg", "-mapped-stars.json")
   mapped_stars = load_json_file(mapped_star_file)
   meteor_json['mapped_stars'] = mapped_stars

save_json_file(meteor_json_file, meteor_json)

print(meteor_json_file)
