#!/usr/bin/python3


import sys
import time
from PIL import ImageFont, ImageDraw, Image, ImageChops


from lib.PipeFiles import get_pending_files
from lib.PipeUtil import convert_filename_to_date_cam, day_or_night , load_json_file, save_json_file, cfe
from lib.PipeVideo import scan_stack_file
from lib.PipeDetect import detect_in_vals 



'''

   Process.py - main pipeline processing script.

'''

AMS_HOME = "/home/ams/amscams"
CONF_DIR = AMS_HOME + "/conf"
DATA_BASE_DIR = "/mnt/ams2"
PROC_BASE_DIR = "/mnt/ams2/SD/proc2"
PREVIEW_W = 300
PREVIEW_H = 169

json_conf = load_json_file(CONF_DIR +"/as6.json")
if "process_day" in json_conf:
   proc_day = 1



def scan_stack_pending(proc_day=0):
   proc_day = 0
   files = get_pending_files()
   for file in files:
      (f_datetime, cam, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(file)
      sun_status = day_or_night(f_date_str, json_conf)

      if proc_day == 0 and sun_status == 'day': 
         print("MOVE DAYTIME FILE:", sun_status, file)
      else:
         print("SCAN AND STACK FILE!")
         scan_stack_file(file)




if __name__ == "__main__":
   if len(sys.argv) >= 2:
      cmd = sys.argv[1]
   else:
      cmd = "default"
   if cmd == 'ssp':
      scan_stack_pending(proc_day)
   if cmd == 'ss':
      scan_stack_file(sys.argv[2])
   if cmd == 'dv':
      detect_in_vals(sys.argv[2])
