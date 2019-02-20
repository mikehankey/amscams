#!/usr/bin/python3 

import datetime
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

import numpy as np
import cv2
import glob
from pathlib import Path
import os
import sys
import lib.brightstardata as bsd

from lib.CalibLib import distort_xy_new, find_image_stars, distort_xy_new, XYtoRADec, AzEltoRADec, HMS2deg, radec_to_azel
from lib.UtilLib import angularSeparation, convert_filename_to_date_cam 

from lib.FileIO import load_json_file, save_json_file, cfe
from lib.UtilLib import calc_dist,find_angle
import lib.brightstardata as bsd
from lib.DetectLib import eval_cnt
from lib.ImageLib import draw_stars_on_img




mybsd = bsd.brightstardata()
bright_stars = mybsd.bright_stars
json_conf = load_json_file("/home/ams/amscams/conf/as6.json")

def get_catalog_stars(fov_poly, pos_poly, cal_params,dimension,x_poly,y_poly,min=0):
   catalog_stars = []
   possible_stars = 0
   img_w = int(cal_params['imagew'])
   img_h = int(cal_params['imageh'])
   RA_center = float(cal_params['ra_center']) + (1000*fov_poly[0])
   dec_center = float(cal_params['dec_center']) + (1000*fov_poly[1])
   F_scale = 3600/float(cal_params['pixscale'])

   fov_w = img_w / F_scale
   fov_h = img_h / F_scale
   fov_radius = np.sqrt((fov_w/2)**2 + (fov_h/2)**2)

   pos_angle_ref = cal_params['position_angle'] + (1000*pos_poly[0])
   x_res = int(cal_params['imagew'])
   y_res = int(cal_params['imageh'])

   center_x = int(x_res / 2)
   center_y = int(x_res / 2)

   bright_stars_sorted = sorted(bright_stars, key=lambda x: x[4], reverse=False)
 

   for bname, cname, ra, dec, mag in bright_stars_sorted:
      dcname = cname.decode("utf-8")
      dbname = bname.decode("utf-8")
      if dcname == "":
         name = dbname
      else:
         name = dcname

      ang_sep = angularSeparation(ra,dec,RA_center,dec_center)
      if ang_sep < fov_radius-(fov_radius * 0) and float(mag) < 4:
         print(x_poly,y_poly)
         new_cat_x, new_cat_y = distort_xy_new (0,0,ra,dec,RA_center, dec_center, x_poly, y_poly, x_res, y_res, pos_angle_ref,F_scale)

         possible_stars = possible_stars + 1
         #print(name, mag, new_cat_x, new_cat_y)
         dist_to_center = calc_dist((new_cat_x,new_cat_y), (img_w/2,img_h/2))
         if dist_to_center <= 600:
            catalog_stars.append((name,mag,ra,dec,new_cat_x,new_cat_y))

   cats = catalog_stars[0:-1]
   print(cats)
   return(cats)



def ffmpeg_dump_frames(video_file, temp_dir):
   el = video_file.split("/")
   jpg_file = el[-1]
   final_out = jpg_file.replace(".mp4", ".jpg")
   final_out = temp_dir + final_out
   jpg_file = jpg_file.replace(".mp4", "-%04d.png")
   jpg_out = temp_dir + jpg_file
   print(final_out)
   file_exists = Path(final_out)
   if file_exists.is_file() is False:
      syscmd = "/usr/bin/ffmpeg -i " + video_file + " -ss 00:00:00  " + jpg_out
      print(syscmd)
      print(syscmd)
      os.system(syscmd)

def get_files(temp_dir):
   nfiles = []
   files = glob.glob(temp_dir + "*.png")
   for file in files: 
      if "grid" not in file and "trans" not in file and "zz_" not in file:
         nfiles.append(file)
   return(sorted(nfiles))

def add_az_grid_to_frames(img_files, az_grid_file):
   grid_img = cv2.imread(az_grid_file)
   for img_file in img_files:
      out_file = img_file.replace(".png", "-grid.png")
      img = cv2.imread(img_file)
      #bc,gc,rc = cv2.split(img)
      #ac = np.ones(bc.shape,dtype=bc.dtype) * 50
      #img_BGRA = cv2.merge((bc,gc,rc,ac))
      print(img.shape, grid_img.shape)
      out_img = cv2.addWeighted(img, .7, grid_img, .3,0)
      cv2.imwrite(out_file, out_img)

def find_star_near_cat(img, cat_x, cat_y,size=20): 
   if img.shape == 3:
      ih,iw,ic = img.shape
   else:
      ih,iw = img.shape
   dist_to_center = calc_dist((cat_x,cat_y), (iw/2,ih/2))
   if dist_to_center > 400:
      size = size * 3 
   cy1 = cat_y - size
   cy2 = cat_y + size
   cx1 = cat_x - size
   cx2 = cat_x + size
   print("CX,CY:", cy1,cy2,cx1,cx2)
   cnt_img = img[cy1:cy2,cx1:cx2]
   min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(cnt_img)
   x,y = max_loc
   return(x+cx1,y+cy1)

def draw_meteor_frames(meteor_json, img_base, json_conf):
   cv2.namedWindow('pepe')
   hdc_x,hdc_y,hdc_x2,hdc_y2 = meteor_json['hd_box']
   el = img_base.split("meteor-")
   img_base = el[0]
   img_base = img_base + "meteor-"
   for frame in meteor_json['hd_objects']:
      
      fc,frame_time_str,x,y,w,h,hd_x,hd_y,ra,dec,rad,decd,az,el = frame
      print(x,y)

      frame_count = "{0:04d}".format( fc)
      img_file = img_base + frame_count + "-grid.png"
      print(img_file)
      img = cv2.imread(img_file)
      x,y = int(x+hdc_x), int(y+hdc_y)
      cv2.rectangle(img, (x,y), (x+ w, y+ h), (255, 0, 0), 1)
      desc =  str(az)[0:5] + "," + str(el)[0:5]
      cv2.putText(img, desc,  (x+w+10,y+int(h/2)), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
      show_img = cv2.resize(img, (0,0),fx=.5, fy=.5)
      cv2.imshow('pepe', show_img)
      cv2.imwrite(img_file, img)
      cv2.waitKey(40)

def seq_files(img_frames):
   for img_file in img_frames:
      print(img_file)
      grid_file = img_file.replace(".png", "-grid.png")
      el = img_file.split("/")
      fn = el[-1]
      dir = img_file.replace(fn, "")
      new_grid_file = dir + "grid-" + fn 
      cmd = "mv " + grid_file + " " + new_grid_file
      print(cmd)
      #os.system(cmd)
  


def make_trans_frames(img_frames):

   fc = 0
   for img_file in img_frames:
      print(img_file)
      grid_file = img_file.replace(".png", "-grid.png")
      trans_file = img_file.replace(".png", "-trans.png")
      perc1 = fc /  35
      perc2 = 1 - perc1 
      print(perc2, perc1)
      img = cv2.imread(img_file)
      grid_img = cv2.imread(grid_file)
      print(img_file, img.shape, grid_img.shape, perc2, perc1)

      out_img = cv2.addWeighted(img, perc2, grid_img, perc1,0)  
      show_img = cv2.resize(out_img, (0,0),fx=.5, fy=.5)
      cv2.imshow('pepe', show_img)
      cv2.waitKey(40)
      cv2.imwrite(grid_file, out_img)


      fc = fc + 1
      

video_file = sys.argv[1]
az_grid_file = sys.argv[2]
cal_param_file = sys.argv[3]
meteor_json_file = sys.argv[4]
stack_file = video_file.replace(".mp4", ".jpg")
print(stack_file)

cv2.namedWindow('pepe')


cal_params = load_json_file(cal_param_file)
meteor_json = load_json_file(meteor_json_file)


device_id = json_conf['site']['ams_id']
operator_name = json_conf['site']['operator_name']
obs_name = json_conf['site']['obs_name']
device_lat = json_conf['site']['device_lat']
device_lon = json_conf['site']['device_lng']

cal_file = video_file
hd_datetime, hd_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(cal_file)
cal_date = hd_datetime

temp_dir = "/mnt/ams2/tmp/"
img_files = get_files(temp_dir)



extra_start_sec = meteor_json['hd_trim_time_offset'] 
start_frame_time = hd_datetime + datetime.timedelta(0,extra_start_sec)
start_frame_str = hd_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]


azd = cal_params['center_az']
eld = cal_params['center_el']

first_frame = meteor_json['hd_objects'][0][0]
last_frame = meteor_json['hd_objects'][-1][0]

elp_frames = last_frame - first_frame
elp_time = elp_frames / 25

print(first_frame, last_frame, elp_time)

ev_start_sec = first_frame / 25
start_event_time = start_frame_time + datetime.timedelta(0,ev_start_sec)
start_event_str = start_event_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

first_x = int(meteor_json['hd_objects'][0][6])
first_y = int(meteor_json['hd_objects'][0][7])

first_w = int(meteor_json['hd_objects'][0][4])
first_h = int(meteor_json['hd_objects'][0][5])

first_x = first_x + int(first_w / 2)
first_y = first_y + int(first_h / 2)

first_az = meteor_json['hd_objects'][0][12]
first_el = meteor_json['hd_objects'][0][13]

last_az = meteor_json['hd_objects'][-1][12]
last_el = meteor_json['hd_objects'][-1][13]

last_x = int(meteor_json['hd_objects'][-1][6])
last_y = int(meteor_json['hd_objects'][-1][7])

last_x = last_x + int(first_w / 2)
last_y = last_y + int(first_h)

print(first_x,first_y)
print(last_x,last_y)
print(stack_file)
img = cv2.imread(stack_file)

base_img_file = img_files[-1]
base_img_file = base_img_file.replace("2019", "grid-2019")
base_img = cv2.imread(base_img_file)
grid_img = cv2.imread(az_grid_file)

temp_img = cv2.addWeighted(img, .7, base_img, .3,0)
img = temp_img
show_img = cv2.resize(img, (0,0),fx=.5, fy=.5)
cv2.imshow('pepe', show_img)
cv2.waitKey(0)


print("SHAPES:", img.shape)
desc = str(first_az)[0:6] + " / " + str(first_el)[0:6]
desc2 = str(last_az)[0:6] + " / " + str(last_el)[0:6]
cv2.putText(img, desc,  (first_x + 5,first_y), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
cv2.putText(img, desc2,  (last_x + 5,last_y), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
desc3 = "Event start time: " + start_event_str + " / Elapsed_time = " + str(elp_time)[0:6]
cv2.putText(img, desc3,  (1444,1060), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)

desc4 = device_id + " - " + obs_name + " / " + operator_name + " " + device_lat + " " + device_lon 
cv2.putText(img, desc4,  (10,1060), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
print("SHAPES:", img.shape)


print("SHAPES:", base_img_file, base_img.shape)

for i in range(0,75):
   perc1 = i /  75
   perc2 = 1 - perc1 

   out_img = cv2.addWeighted(base_img, perc2, img, perc1,0)
   out_img = img

   show_img = cv2.resize(out_img, (0,0),fx=.5, fy=.5)
   cv2.imshow('pepe', show_img)
   cv2.waitKey(0)
   last_file = "zz_meteor" + str(i) +".png"
   cv2.imwrite(last_file, out_img)
for i in range(76,125):
   out_img = img
   show_img = cv2.resize(out_img, (0,0),fx=.5, fy=.5)
   last_file = "zz_meteor" + str(i) +".png"
   cv2.imwrite(last_file, out_img)
   cv2.imshow('pepe', show_img)
   cv2.waitKey(0)

exit()


rah,dech = AzEltoRADec(azd,eld,cal_file,cal_params,json_conf)
rah = str(rah).replace(":", " ")
dech = str(dech).replace(":", " ")

ra,dec = HMS2deg(str(rah),str(dech))
print ("RA:DEC CENTER=", ra,dec)

cal_params['ra_center'] = ra
cal_params['dec_center'] = dec 
cat_stars = get_catalog_stars(cal_params['fov_poly'], cal_params['pos_ang'], cal_params,"x",cal_params['x_poly'],cal_params['y_poly'])
print(cat_stars)


#os.system("rm /mnt/ams2/tmp/*.png")
#ffmpeg_dump_frames(video_file, temp_dir)
#add_az_grid_to_frames(img_files, az_grid_file)
print(img_files[0])
img_file = img_files[0].replace("-grid", "")


img = cv2.imread(img_file, 0)
img_stars,star_img = find_image_stars(img)

good_cats = []
for star in cat_stars:
   name,mag,ra,dec,new_cat_x,new_cat_y = star
   new_x, new_y, img_ra,img_dec, tl_az, tl_el = XYtoRADec(new_cat_x,new_cat_y,cal_file,cal_params,json_conf)
   stc_az,stc_el = radec_to_azel(ra,dec, cal_date,json_conf)

   if stc_el > 0:
      print(name, new_cat_x, new_cat_y, tl_az, tl_el)

      good_cats.append((name,mag,ra,dec,new_cat_x,new_cat_y,tl_az,tl_el))
cats = good_cats

#print(json_conf)

device_id = json_conf['site']['ams_id']
operator_name = json_conf['site']['operator_name']
obs_name = json_conf['site']['obs_name']
device_lat = json_conf['site']['device_lat']
device_lon = json_conf['site']['device_lng']

#trim_num = 50
#start_frame_num = trim_num

#seq_files(img_files)
#make_trans_frames(img_files[0:35])

make_last_stack()

exit()

fc = 0
for img_file in img_files:
   img_file = img_file.replace(".png", "-grid.png")

   extra_sec = (fc) /  25
   frame_time = start_frame_time + datetime.timedelta(0,extra_sec)
   frame_time_str = frame_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
   print(fc, frame_time)

   img = cv2.imread(img_file)

   #img = draw_stars_on_img(img, cats, color="white", track_type="box")  
   desc = device_id + " - " + obs_name + " / " + operator_name + " " + device_lat + " " + device_lon 
   desc2 = frame_time_str
   cv2.putText(img, desc,  (10,1060), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
   cv2.putText(img, desc2,  (1730,1060), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
   cv2.imwrite(img_file, img)
   if fc % 100 == 0:
      show_img = cv2.resize(img, (0,0),fx=.5, fy=.5)
      cv2.imshow('pepe', show_img)
      cv2.waitKey(40)
   fc = fc + 1

#draw_meteor_frames(meteor_json, img_file, json_conf)

#for star in cat_stars:
#   name,mag,ra,dec,new_cat_x,new_cat_y = star
#   #x,y,w,h = star
#   new_cat_x, new_cat_y = int(new_cat_x),int(new_cat_y)
#   print(star)
#   ix,iy = find_star_near_cat(img,new_cat_x,new_cat_y,20)
#   cv2.rectangle(img, (new_cat_x-5, new_cat_y-5), (new_cat_x + 5, new_cat_y + 5), (255, 0, 0), 1)
#   cv2.rectangle(img, (ix-5, iy-5), (ix+ 5, iy+ 5), (255, 0, 0), 1)
cv2.namedWindow('pepe')


show_img = cv2.resize(img, (0,0),fx=.5, fy=.5)
cv2.imshow('pepe', show_img)
cv2.waitKey(0)


