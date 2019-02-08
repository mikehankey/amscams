#!/usr/bin/python3 

#from lib.CalMeteorLib import 
from lib.CalibLib import calibrate_camera, distort_xy_new, calibrate_pic
from lib.FileIO import load_json_file

import sys


json_conf = load_json_file("../conf/as6.json")

cmd = sys.argv[1]
#file = sys.argv[2]

if cmd == 'calpic':
   
   file = sys.argv[2]
   calibrate_pic(file,json_conf)

if cmd == 'calcam':
   #cams_id = sys.argv[2]
   if len(sys.argv) > 3:
      cal_date = sys.argv[3]
   else:
      cal_date = None
   cameras = json_conf['cameras']
   c = 0
   for camera in cameras:
      cams_id = cameras[camera]['cams_id']
      if c >= 0:
         calibrate_camera(cams_id, json_conf,cal_date) 
      c = c + 1
