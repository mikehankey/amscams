#!/usr/bin/python3

import os
#import math
import cv2
#import math
import numpy as np
#import scipy.optimize
#import matplotlib.pyplot as plt
import sys
from lib.CalibLib import distort_xy_new, find_image_stars, distort_xy_new, XYtoRADec, AzEltoRADec, HMS2deg
#from lib.UtilLib import angularSeparation
from lib.FileIO import load_json_file, save_json_file, cfe
#from lib.UtilLib import calc_dist,find_angle
#import lib.brightstardata as bsd
#from lib.DetectLib import eval_cnt

def draw_grid_line(points, img, type, key, show_text = 0):
   pc = 0
   show_text = 1
   if type == 'el':
      for point in points:
         az,el,x,y = point
         if el == key:
            if pc > 0:
               cv2.line(img, (x,y), (last_x,last_y), (255), 2)
               if show_text == 1:
                  desc = str(az) 
                  cv2.putText(img, desc,  (x+3,y+15), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)

            last_x = x
            last_y = y
            pc = pc + 1
   if type == 'az':
      for point in points:
         az,el,x,y = point
         if az == key:

            if pc > 0:
               cv2.line(img, (x,y), (last_x,last_y), (255), 2)
               if show_text == 1:
                  desc = str(el) 
                  cv2.putText(img, desc,  (x+5,y-5), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
            last_x = x
            last_y = y
            pc = pc + 1
   return(img)

def az_grid(cal_file,cal_params,cal_image,iw,ih,show =0):
   print("AZ GRID FOR ", cal_file)

   new_x, new_y, img_ra,img_dec, center_az, center_el = XYtoRADec(iw/2,ih/2,cal_param_file,cal_params,json_conf)
   print("CENTER:", iw/2,ih/2,new_x,new_y,img_ra,img_dec,center_az,center_el)

   new_x, new_y, img_ra,img_dec, tl_az, tl_el = XYtoRADec(0,0,cal_param_file,cal_params,json_conf)
   print("TOP LEFT:", 0,0,new_x,new_y,img_ra,img_dec,tl_az,tl_el)

   if center_el > 70:
      start_el = 30
      end_el = 89.8
      start_az = 0
      end_az = 355
   else:
      start_az = center_az - 80
      end_az = center_az + 70
      start_el = center_el - 30
      end_el = center_el + 30
      if start_el < 0:
         start_el = 0
      if end_el >= 90:
         end_el = 89.7

   RA_center = float(cal_params['ra_center'])
   dec_center = float(cal_params['dec_center'])
   x_res = int(cal_params['imagew'])
   y_res = int(cal_params['imageh'])
   x_poly = cal_params['x_poly']
   y_poly = cal_params['y_poly']
   pos_angle_ref = float(cal_params['position_angle'])
   #F_scale = 1
   F_scale = 3600/float(cal_params['pixscale'])
   az_lines = []
   el_lines = []
   points = []
   #if start_az > end_az:
   #   start_az = start_az - 360

   print("START AZ, END AZ", start_az, end_az)
   for az in range(int(start_az),int(end_az)):
      for el in range(int(start_el),int(end_el)+30):
         if az % 10 == 0 and el % 10 == 0:
            print("GRID AZ-EL POINTS:", az,el)


   for az in range(int(start_az),int(end_az)):
      if az >= 360:
         az = az - 360

      for el in range(int(start_el),int(end_el)+30):
         if az % 5 == 0 and el % 5 == 0:

            rah,dech = AzEltoRADec(az,el,cal_param_file,cal_params,json_conf)
            rah = str(rah).replace(":", " ")
            dech = str(dech).replace(":", " ")
            ra,dec = HMS2deg(str(rah),str(dech))
            new_cat_x, new_cat_y = distort_xy_new (0,0,ra,dec,RA_center, dec_center, x_poly, y_poly, x_res, y_res, pos_angle_ref,F_scale)
            new_cat_x,new_cat_y = int(new_cat_x),int(new_cat_y)
            if new_cat_x > -200 and new_cat_x < 2420 and new_cat_y > -200 and new_cat_y < 1480:
               cv2.rectangle(cal_image, (new_cat_x-2, new_cat_y-2), (new_cat_x + 2, new_cat_y + 2), (128, 128, 128), 1)
               if new_cat_x > 0 and new_cat_y > 0:
                  az_lines.append(az)
                  el_lines.append(el)
               points.append((az,el,new_cat_x,new_cat_y))
   pc = 0
   for el in range (0,90):
      if el % 10 == 0:
         cal_image = draw_grid_line(points, cal_image, "el", el)
   for az in range (0,360):
      if az % 10 == 0:
         cal_image = draw_grid_line(points, cal_image, "az", az)

   if show ==1:
      cv2.namedWindow('pepe')
      show_img = cv2.resize(cal_image, (0,0),fx=.5, fy=.5)
      cv2.imshow('pepe', show_img)
      cv2.waitKey(0)

   az_grid_file = cal_file.replace(".jpg", "-azgrid.png")
   az_grid_file_half = cal_file.replace(".jpg", "-azgrid-half.png")
   az_grid_half_blend = cal_file.replace(".jpg", "-azgrid-half-blend.png")

   half_stack_file = cal_file.replace("-stacked.jpg", "-stacked.png")
   half_stack_img = cv2.imread(half_stack_file)
   half_stack_img = cv2.resize(half_stack_img, (0,0),fx=.5, fy=.5)

   az_grid_half_img = cv2.resize(cal_image, (0,0),fx=.5, fy=.5)

   az_grid_half_img_c = cv2.cvtColor(az_grid_half_img,cv2.COLOR_GRAY2RGB)

   print(half_stack_img.shape)
   print(az_grid_half_img_c.shape)

   blend_image = cv2.addWeighted(half_stack_img, .9, az_grid_half_img_c, .1,0)
   cv2.imwrite(az_grid_half_blend, blend_image)
   print(az_grid_half_blend)
   cv2.imwrite(az_grid_file, cal_image)
   cv2.imwrite(az_grid_file_half, az_grid_half_img)
   tr_grid_file = az_grid_file.replace(".png", "-t.png")
   cmd = "/usr/bin/convert " + az_grid_file + " " + tr_grid_file
   print(cmd)
   os.system(cmd)
   print(az_grid_file)




json_conf = load_json_file("../conf/as6.json")

if sys.argv[1] == 'az_grid':
   cmd = "az_grid"
   cal_param_file = sys.argv[2]
else:
   cmd = "fp"
   img_x = int(sys.argv[1])
   img_y = int(sys.argv[2])
   cal_param_file = sys.argv[3]


cal_params = load_json_file(cal_param_file)

if cmd == "fp":

   new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(img_x,img_y,cal_param_file,cal_params,json_conf)
   print("Orig X/Y", img_x, img_y) 
   print("Corrected RA/DEC ", img_ra, img_dec) 
   print("Corrected AZ/EL", img_az, img_el) 


if cmd == 'az_grid':

   cal_file = cal_param_file.replace("-calparams.json", ".jpg")
   cal_file = cal_file.replace("-calparams-master.json", ".jpg")
   if "master" in cal_file:
      cal_file = cal_file.replace("-master", "")

   print(cal_file)
   cal_image = cv2.imread(cal_file)
   if len(cal_image.shape) == 3:
      ih,iw,cl = cal_image.shape
   else:
      ih,iw = cal_image.shape
   cal_image = np.zeros((ih,iw),dtype=np.uint8)
   az_grid(cal_file,cal_params,cal_image,iw,ih)
   exit()

   print("AZ GRID...",iw,ih)

   img_x = 960
   img_y = 540
   new_x, new_y, img_ra,img_dec, center_az, center_el = XYtoRADec(img_x,img_y,cal_param_file,cal_params,json_conf)
   print(img_x,img_y,new_x,new_y,img_ra,img_dec,center_az,center_el)





   img_x = 0
   img_y = 0
   new_x, new_y, img_ra,img_dec, tl_az, tl_el = XYtoRADec(img_x,img_y,cal_param_file,cal_params,json_conf)

   img_x = 0 
   img_y = 1080
   new_x, new_y, img_ra,img_dec, bl_az, bl_el = XYtoRADec(img_x,img_y,cal_param_file,cal_params,json_conf)

   img_x = 1920
   img_y = 0
   new_x, new_y, img_ra,img_dec, tr_az, tr_el = XYtoRADec(img_x,img_y,cal_param_file,cal_params,json_conf)

   img_x = 1920
   img_y = 1080
   new_x, new_y, img_ra,img_dec, br_az, br_el = XYtoRADec(img_x,img_y,cal_param_file,cal_params,json_conf)



   print("CENTER AZ/EL", center_az,center_el)
   print("TOP LEFT AZ/EL", tl_az,tl_el)
   print("TOP RIGHT AZ/EL", tr_az,tr_el)
   print("BOTTOM LEFT AZ/EL", bl_az,bl_el)
   print("BOTTOM RIGHT AZ/EL", br_az,br_el)

   start_az = -30
   start_el = 1
   end_az = 140
   end_el = 89.9
   RA_center = float(cal_params['ra_center'])
   dec_center = float(cal_params['dec_center'])
   x_res = int(cal_params['imagew'])
   y_res = int(cal_params['imageh'])
   x_poly = cal_params['x_poly']
   y_poly = cal_params['y_poly']
   pos_angle_ref = float(cal_params['position_angle'])
   #F_scale = 1
   F_scale = 3600/float(cal_params['pixscale'])
   az_lines = []
   el_lines = []
   points = []
   if start_az > end_az:
      start_az = end_az - 180

   print("START AZ, END AZ", start_az, end_az)
   for az in range(int(start_az),int(end_az)): 
      if az < 0:
         az = az + 360

      for el in range(int(start_el),int(end_el)+30):
         if az % 10 == 0 and el % 10 == 0:

            rah,dech = AzEltoRADec(az,el,cal_param_file,cal_params,json_conf)
            rah = str(rah).replace(":", " ")
            dech = str(dech).replace(":", " ")
            ra,dec = HMS2deg(str(rah),str(dech))
            new_cat_x, new_cat_y = distort_xy_new (0,0,ra,dec,RA_center, dec_center, x_poly, y_poly, x_res, y_res, pos_angle_ref,F_scale)
            new_cat_x,new_cat_y = int(new_cat_x),int(new_cat_y)
            if new_cat_x > -200 and new_cat_x < 2420 and new_cat_y > -200 and new_cat_y < 1480:
               cv2.rectangle(cal_image, (new_cat_x-2, new_cat_y-2), (new_cat_x + 2, new_cat_y + 2), (128, 128, 128), 1)
               if new_cat_x > 0 and new_cat_y > 0:
                  az_lines.append(az)
                  el_lines.append(el)
               points.append((az,el,new_cat_x,new_cat_y))
   pc = 0
   for el in range (0,90):
      if el % 10 == 0: 
         cal_image = draw_grid_line(points, cal_image, "el", el)
   for az in range (0,360):
      if az % 10 == 0: 
         cal_image = draw_grid_line(points, cal_image, "az", az)

   # draw az/el markers
   az_lines = sorted(az_lines)
   min_az = az_lines[5]
   min_el = min(el_lines)
   min_el = 20
   print("Min az,el", min_az, min_el)
   cal_image = draw_grid_line(points, cal_image, "el", min_el, 1)
   print ("Now do the EL", min_az)
   cal_image = draw_grid_line(points, cal_image, "az", min_az, 1)

   #for point in points:
   #   az,el,x,y = point
   #   if el == 10:
   #      print("POINT:", point)
   #      if pc > 0:
   #         cv2.line(cal_image, (x,y), (last_x,last_y), (255), 2)
   #      last_x = x
   #      last_y = y
   #      pc = pc + 1
   cv2.namedWindow('pepe')
   show_img = cv2.resize(cal_image, (0,0),fx=.5, fy=.5)
   cv2.imshow('pepe', show_img)
   cv2.waitKey(0)
   az_grid_file = cal_file.replace(".jpg", "-azgrid.png")
   cv2.imwrite(az_grid_file, cal_image)
   tr_grid_file = az_grid_file.replace(".png", "-t.png")
   cmd = "/usr/bin/convert " + az_grid_file + " " + tr_grid_file
   print(cmd)
   os.system(cmd)
   print(az_grid_file)
