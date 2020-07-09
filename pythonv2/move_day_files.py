#!/usr/bin/python3

from lib.FileIO import load_json_file
from lib.UtilLib import get_sun_info, convert_filename_to_date_cam 

import os
import glob
import sys
json_conf = load_json_file("../conf/as6.json")

#file = sys.argv[1]
dir = "/mnt/ams2/SD/*.mp4"
files =glob.glob(dir)

for file in files:
   hd_datetime, hd_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(file)
   sun_status,sun_az,sun_el = get_sun_info(hd_date, json_conf)
   print(sun_status, file)
   if sun_status == 'day':
      cmd = "mv " + file + " /mnt/ams2/SD/proc2/daytime/"
      print(cmd)
      os.system(cmd)
