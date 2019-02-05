#!/usr/bin/python3 

#from lib.CalMeteorLib import 
from lib.CalibLib import calibrate_camera, distort_xy_new
from lib.FileIO import load_json_file

import sys


json_conf = load_json_file("../conf/as6.json")

cmd = sys.argv[1]
#file = sys.argv[2]

if cmd == 'calcam':
   cams_id = sys.argv[2]
   calibrate_camera(cams_id, json_conf) 
