#!/usr/bin/python3


import sys
import time
from PIL import ImageFont, ImageDraw, Image, ImageChops


from lib.PipeFiles import get_pending_files
from lib.PipeUtil import convert_filename_to_date_cam, day_or_night , load_json_file, save_json_file, cfe
from lib.PipeVideo import scan_stack_file, make_preview_video, make_preview_videos
from lib.PipeDetect import detect_in_vals 
from lib.PipeSync import sync_day 
from lib.PipeAutoCal import autocal , solve_field, cal_all, draw_star_image, freecal_copy, apply_calib, index_failed
from lib.PipeReport import autocal_report
from lib.PipeLIVE import meteor_min_files, broadcast_live_meteors, broadcast_minutes, meteors_last_night
from lib.PipeTimeLapse import make_tl_for_cam, video_from_images, six_cam_video, timelapse_all

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

   # Processing stars with the scan and stack
   # This function scans and stacks all pending files
   # Should be running all the time via cron
   if cmd == 'ssp':
      scan_stack_pending(proc_day)

   # Scan and stack a single file 
   if cmd == 'ss':
      scan_stack_file(sys.argv[2])

   # Detect events/meteors from the vals file
   if cmd == 'dv':
      detect_in_vals(sys.argv[2])

   # Sync a day's worth of meteors 
   # to the cloud
   if cmd == 'sd':
      sync_day(sys.argv[2])

   # Make preview videos for a specific meteor 
   if cmd == 'pv':
      make_preview_video(sys.argv[2], json_conf)

   # Make all preview videoss for a specific day 
   if cmd == 'pvs':
      make_preview_videos(sys.argv[2], json_conf)

   # auto calibrate one file
   if cmd == 'ac':
      autocal(sys.argv[2], json_conf)

   # solve the field from a plate image
   if cmd == 'sf':
      solve_field(sys.argv[2], json_conf)

   # calibrate all pending sense up files
   if cmd == 'ca':
      cal_all(json_conf)

   # draw star image for calibration file 
   if cmd == 'dsi':
      draw_star_image(sys.argv[2], None)

   # copy a new autocal file into the legacy freecal system (backward compatible) 
   if cmd == 'fccp':
      freecal_copy (sys.argv[2] , json_conf)

   # make the autocal report html
   if cmd == 'ac_rpt':
      autocal_report()
 
   # index the failed calibs
   if cmd == 'if':
      index_failed(json_conf)


   # LIVE BUFFERED VIDEO COMMANDS

   # make the meter min files for a day 
   if cmd == 'mmf':
      meteor_min_files(sys.argv[2], json_conf)
   if cmd == 'blm':
      broadcast_live_meteors()
   if cmd == 'apply_calib':
      apply_calib(sys.argv[2], json_conf)

   # Time Lapse Commands
   if cmd == 'tlc':
      make_tl_for_cam(sys.argv[2], sys.argv[3], json_conf)
   if cmd == 'tla':
      timelapse_all(sys.argv[2], json_conf)
   if cmd == 'vfi':
      video_from_images(sys.argv[2], sys.argv[3], json_conf)
   if cmd == 'scv':
      six_cam_video(sys.argv[2], json_conf)
   if cmd == 'bcm':
      broadcast_minutes(json_conf)
   if cmd == 'mln':
      meteors_last_night(json_conf)

