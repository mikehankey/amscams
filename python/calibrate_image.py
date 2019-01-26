#!/usr/bin/python3
import random
import cv2
import numpy as np
import sys
import os
import time 
from pathlib import Path
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
from PIL import ImageEnhance
import json
from caliblib import load_json_file, save_json_file, find_image_stars, find_image_stars_thresh, get_masks, convert_filename_to_date_cam, clean_star_bg
from detectlib import load_video_frames , median_frames,cfe, stack_frames


import brightstardata as bsd
mybsd = bsd.brightstardata()
bright_stars = mybsd.bright_stars


json_file = open('../conf/as6.json')
json_str = json_file.read()
json_conf = json.loads(json_str)
proc_dir = json_conf['site']['proc_dir']



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
      

def get_masks_old(this_cams_id):
   my_masks = []
   cameras = json_conf['cameras']
   for camera in cameras:
      if str(cameras[camera]['cams_id']) == str(this_cams_id):
         masks = cameras[camera]['masks']
         for key in masks:
            my_masks.append((masks[key]))

#   print(my_masks)

   return(my_masks)

def plot_bright_stars(jpg_file, image, star_data_file):
   bright_star_file = jpg_file.replace(".jpg", "-bright-stars.jpg")
   pil_image = Image.fromarray(image)
   draw = ImageDraw.Draw(pil_image)
   font = ImageFont.truetype("/usr/share/fonts/truetype/freefont/FreeSans.ttf", 12, encoding="unic" )


   for data in star_data_file:
      (name, cons, ra, dec, mag, ast_x, ast_y) = data.split(",")
      ast_x = int(float(ast_x))
      ast_y = int(float(ast_y))
      draw.ellipse((ast_x-4, ast_y-4, ast_x+4, ast_y+4), ) 
      draw.text((int(float(ast_x)), int(float(ast_y) )), name, font = font, fill=(255,255,255))
      pil_image.save(bright_star_file)


def parse_astr_star_file(star_data_file):
   bright_stars_found = [] 
   fp = open(star_data_file, "r")
   for line in fp:
      fields = line.split(" ")
      #print (len(fields) )
      if len(fields) == 8:
         star_name = fields[4]
         ast_x = fields[6]
         ast_y = fields[7]
         ast_x = ast_x.replace("(", "")
         ast_x = ast_x.replace(",", "")
         ast_y = ast_y.replace(")", "")
         ast_y = ast_y.replace("\n", "")
      elif len(fields) == 9 :
         star_name = fields[5]
         star_name = star_name.replace("(", "")
         star_name = star_name.replace(")", "")
         ast_x = fields[7]
         ast_y = fields[8]
         ast_x = ast_x.replace("(", "")
         ast_x = ast_x.replace(",", "")
         ast_y = ast_y.replace(")", "")
         ast_y = ast_y.replace("\n", "")
         #print(star_name)
         (status, bname, cons, ra,dec,mag) = find_star_by_name(star_name)
         #print(status, bname, cons, ra,dec, mag)
         if int(status) == 1:
            data = bname + "," + cons + "," + str(ra) + "," + str(dec) + "," + str(mag) + "," + str(ast_x) + "," + str(ast_y)
            #print("Bright Star found:", bname, cons, ra,dec, mag, "Near position", ast_x, ast_y)
            bright_stars_found.append(data)

   for data in bright_stars_found :
      print(data)

   return(bright_stars_found)

def find_star_by_name(star_name):
   for bname, cons, ra, dec, mag in bright_stars:
      cons = cons.decode("utf-8")
      name = bname.decode("utf-8")
      if name == star_name:
         return(1,name, cons, ra,dec,mag)
   return(0,0,0,0,0,0)


def make_nice_plate_image(median_image, star_px, cam_num):
   ih,iw = median_image.shape
   plate_base = np.zeros((ih,iw),dtype=np.uint8)

   #for x in range(0,plate_base.shape[1]):
   #   for y in range(0,plate_base.shape[0]):
   #      plate_base[y,x] = 5
#random.randint(int(5),int(7))

   for x,y,w,h in star_px:
      xd = abs(x-(iw/2))
      yd = abs(y-(ih/2))
      print("IMG W,H:", iw,ih)
      if xd < (iw * .33) and yd < (ih * .33):
         print(xd,yd,x,y)
         cnt_img = median_image[y:y+h,x:x+w]
         avg_px = np.mean(cnt_img)
         cnt_img = clean_star_bg(cnt_img, avg_px+6)
         plate_base[y:y+h,x:x+w] = cnt_img

   print(cam_num)
   masks = get_masks(cam_num, 1)
   print("MASKS:",  masks)
   for mask in masks:
      msx,msy,msw,msh = mask.split(",")
      print("ASK: ", msx,msy,msw,msh)
      plate_base[int(msy):int(msy)+int(msh),int(msx):int(msx)+int(msw)] = 0


   return(plate_base)



jpg_file = sys.argv[1]

if "mp4" in jpg_file:
   frames = load_video_frames(jpg_file, 10)
   #median_image = median_frames(frames)
   median_image = stack_frames(frames)
   cal_file = jpg_file.replace(".mp4", ".jpg")
   el = cal_file.split("/")
   cal_filename = el[-1] 
   cal_file = "/mnt/ams2/cal/tmp/" + cal_filename
   (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(cal_file)
   cam, trash = cam.split(".")
   median_image_pil = Image.fromarray(median_image)
   enhance = ImageEnhance.Brightness(median_image_pil)
   temp_img = enhance.enhance(.40)
   enhance = ImageEnhance.Contrast(temp_img)
   temp_img = enhance.enhance(.89)

   median_image_np  = np.asarray(temp_img)

   star_px = find_image_stars_thresh(median_image)

   if len(star_px) < 5 :
      print("Not enough stars in this image to calibrate.", len(star_px)) 
      exit()
   elif len(star_px) > 200:
      print("Too many stars to calibrate (dawn/dusk or clouds?)", len(star_px)) 
      exit()
   else:
      print("stars in this image to calibrate:", len(star_px)) 

   nice_plate = make_nice_plate_image(median_image, star_px, cam)

   #for x,y,w,h in star_px:
   #   cv2.circle(median_image_np, (int(x+(w/2)),int(y+(h/2))), 10, (255,255,0), 1)

   avg_px = np.mean(median_image_np)
   median_image_np = clean_star_bg(median_image_np, avg_px+6)
   os.system("rm /mnt/ams2/cal/tmp/*")
   cv2.imwrite(cal_file, median_image_np)

   print(len(frames))
   cv2.namedWindow('pepe')
   cv2.imshow('pepe', median_image_np)
   cv2.waitKey(0)
   
   jpg_file = cal_file





wcs_file = jpg_file.replace(".jpg", ".wcs")
grid_file = jpg_file.replace(".jpg", "-grid.png")

star_file = jpg_file.replace(".jpg", "-stars-out.jpg")
star_data_file = jpg_file.replace(".jpg", "-stars.txt")
astr_out = jpg_file.replace(".jpg", "-astrometry-output.txt")

wcs_info_file = jpg_file.replace(".jpg", "-wcsinfo.txt")
mapped_stars_file = jpg_file.replace(".jpg", "-mapped-stars.json")

quarter_file = jpg_file.replace(".jpg", "-1.jpg")



image = cv2.imread(jpg_file)
if len(image.shape) > 2:
   gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
else:
   gray = image
height = gray.shape[0] 
width = gray.shape[1] 



cmd = "/usr/local/astrometry/bin/solve-field " + jpg_file + " --crpix-center --cpulimit=30 --verbose --no-delete-temp --overwrite --width=" + str(width) + " --height=" + str(height) + " --scale-low 50 --scale-high 90 > " + astr_out + " 2>&1"
print(cmd)
os.system(cmd)
os.system("grep Mike " + astr_out + " >" +star_data_file + " 2>&1" )

solved_file = jpg_file.replace(".jpg", ".solved")
if cfe(solved_file):

   cmd = "/usr/bin/jpegtopnm " + jpg_file + "|/usr/local/astrometry/bin/plot-constellations -w " + wcs_file + " -o " + grid_file + " -i - -N -C -G 600"
   print (cmd)
   os.system(cmd)

   cmd = "/usr/local/astrometry/bin/wcsinfo " + wcs_file + " > " + wcs_info_file
   os.system(cmd)

   bright_star_data = parse_astr_star_file(star_data_file)
   plot_bright_stars(jpg_file, image, bright_star_data)
   bsd_file = wcs_file.replace(".wcs", "-bsd.txt")
   save_json_file(bsd_file, bright_star_data)
   save_cal_params(wcs_file)
   cmd = "./calib-gen2.py map_cal " + jpg_file 
   os.system(cmd)

   cmd = "./FitCal.py " + mapped_stars_file
   os.system(cmd)
   cal_params_file = mapped_stars_file.replace("-mapped-stars.json", "-calparams.json")
   cal_params = load_json_file(cal_params_file)
   print(cal_params)
   x_fun = cal_params['x_fun']
   y_fun = cal_params['y_fun']
   if float(x_fun) < 5 and float(y_fun) < 5:
      cmd = "mv " + cal_params_file + "/mnt/ams2/cal/good/"
      print(cmd)
      os.system(cmd)

      cmd = "mv " + cal_file + "/mnt/ams2/cal/good/"
      print(cmd)
      os.system(cmd)

