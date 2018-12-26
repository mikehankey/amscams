#!/usr/bin/python3
import cv2
import numpy as np
import sys
import os
import time 
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



def get_masks(this_cams_id):
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


jpg_file = sys.argv[1]



el = jpg_file.split("/")
if len(el) <= 1:
   jpg_file = "/var/www/html/out/cal/" + jpg_file 


wcs_file = jpg_file.replace(".jpg", ".wcs")
grid_file = jpg_file.replace(".jpg", "-grid.png")

star_file = jpg_file.replace(".jpg", "-stars-out.jpg")
star_data_file = jpg_file.replace(".jpg", "-stars.txt")
astr_out = jpg_file.replace(".jpg", "-astrometry-output.txt")

wcs_info_file = jpg_file.replace(".jpg", "-wcsinfo.txt")

quarter_file = jpg_file.replace(".jpg", "-1.jpg")



image = cv2.imread(jpg_file)
print(image.shape)
if len(image.shape) > 2:
   gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
else:
   gray = image
height = gray.shape[0] 
width = gray.shape[1] 

print (width, height)

crop_height = int(height / 2)
crop_width = int(width / 2)
start_x = 0
start_y = 0

#os.system("convert -crop " + str(crop_width) + "x" + str(crop_height) + "+" + str(start_x) + "+" + str(start_y) + " " + jpg_file + " " + quarter_file)
#print("convert -crop " + str(crop_height) + "x" + str(crop_width) + "+" + str(start_x) + "+" + str(start_y) + " " + jpg_file + " " + quarter_file)
#exit()

print("/usr/local/astrometry/bin/solve-field " + jpg_file + " --verbose --no-delete-temp --overwrite --width=" + str(width) + " --height=" + str(height) + " --scale-low 60 --scale-high 120 > " + astr_out)
os.system("/usr/local/astrometry/bin/solve-field " + jpg_file + " --verbose --no-delete-temp --overwrite --width=" + str(width) + " --height=" + str(height) + " --scale-low 50 --scale-high 110 > " + astr_out + " 2>&1")
os.system("grep Mike " + astr_out + " >" +star_data_file + " 2>&1" )

cmd = "/usr/bin/jpegtopnm " + jpg_file + "|/usr/local/astrometry/bin/plot-constellations -w " + wcs_file + " -o " + grid_file + " -i - -N -C -G 600"
print (cmd)
os.system(cmd)

cmd = "/usr/local/astrometry/bin/wcsinfo " + wcs_file + " > " + wcs_info_file
os.system(cmd)

bright_star_data = parse_astr_star_file(star_data_file)
plot_bright_stars(jpg_file, image, bright_star_data)

cmd = "./calibrate_image_step2.py " + jpg_file
os.system(cmd)

#cmd = "./fisheye-test.py " + jpg_file
#os.system(cmd)



# cleanup and move all extra files
el = jpg_file.split("/") 
temp = el[-1]
cal_dir = temp.replace(".jpg", "")
if os.path.exists("/mnt/ams2/cal/solved/" + cal_dir):
   print ("already done.")
else:
   os.mkdir("/mnt/ams2/cal/solved/" + cal_dir)

cmd = "mv /mnt/ams2/cal/" + cal_dir + "* /mnt/ams2/cal/solved/" + cal_dir + "/"
print (cmd)
os.system(cmd)
