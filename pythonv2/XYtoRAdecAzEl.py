#!/usr/bin/python3


#import os
#import math
import cv2
#import math
#import numpy as np
#import scipy.optimize
#import matplotlib.pyplot as plt
import sys
from lib.CalibLib import distort_xy_new, find_image_stars, distort_xy_new, XYtoRADec, AzEltoRADec, HMS2deg
#from lib.UtilLib import angularSeparation
from lib.FileIO import load_json_file, save_json_file, cfe
#from lib.UtilLib import calc_dist,find_angle
#import lib.brightstardata as bsd
#from lib.DetectLib import eval_cnt



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
   cal_image = cv2.imread(cal_file)
   print(cal_image.shape)

   print("AZ GRID...")

   img_x = 960
   img_y = 540
   new_x, new_y, img_ra,img_dec, center_az, center_el = XYtoRADec(img_x,img_y,cal_param_file,cal_params,json_conf)

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

   start_az = tl_az
   start_el = bl_el
   end_az = tr_az
   end_el = tr_el
   RA_center = float(cal_params['ra_center'])
   dec_center = float(cal_params['dec_center'])
   x_res = int(cal_params['imagew'])
   y_res = int(cal_params['imageh'])
   x_poly = cal_params['x_poly']
   y_poly = cal_params['y_poly']
   pos_angle_ref = float(cal_params['position_angle'])
   #F_scale = 1
   F_scale = 3600/float(cal_params['pixscale'])
   for az in range(int(start_az),int(end_az)):
      for el in range(int(start_el),int(end_el)+30):
         if az % 10 == 0 and el % 10 == 0:
            rah,dech = AzEltoRADec(az,el,cal_param_file,cal_params,json_conf)
            rah = str(rah).replace(":", " ")
            dech = str(dech).replace(":", " ")
            ra,dec = HMS2deg(str(rah),str(dech))
          
            new_cat_x, new_cat_y = distort_xy_new (0,0,ra,dec,RA_center, dec_center, x_poly, y_poly, x_res, y_res, pos_angle_ref,F_scale)
            print(az,el,"\t",rah,dech,"\t",ra,dec,"\t",new_cat_x,new_cat_y)
            #print("GRID POINT:", az,el,rah,dech,ra,dec,new_cat_x,new_cat_y)
            #print("GRID POINT:", rah,dech,ra,dec,new_cat_x,new_cat_y)
            new_cat_x,new_cat_y = int(new_cat_x),int(new_cat_y)
            cv2.rectangle(cal_image, (new_cat_x-2, new_cat_y-2), (new_cat_x + 2, new_cat_y + 2), (128, 128, 128), 1)
   cv2.namedWindow('pepe')
   show_img = cv2.resize(cal_image, (0,0),fx=.5, fy=.5)
   cv2.imshow('pepe', show_img)
   cv2.waitKey(0)
