#!/usr/bin/python3

import numpy as np
import sys
import time
from PIL import ImageFont, ImageDraw, Image, ImageChops

from datetime import datetime
import datetime as dt

from lib.PipeWeather import detect_clouds , make_flat, track_clouds, solar_info
from lib.PipeImage import quick_video_stack
from lib.PipeTrans import trans_test 
from lib.PipeManager import mln_report, mln_best, best_of , copy_super_stacks, super_stacks_to_video, multi_station_meteors, proc_status
from lib.PipeFiles import get_pending_files
from lib.PipeUtil import convert_filename_to_date_cam, day_or_night , load_json_file, save_json_file, cfe, remove_corrupt_files
from lib.PipeVideo import scan_stack_file, make_preview_videos, load_frames_simple, ffmpeg_cat , ffmpeg_cats
from lib.PipeDetect import detect_in_vals , obj_report, trim_events, detect_all, get_trim_num, trim_min_file, detect_meteor_in_clip, analyze_object, refine_meteor, refine_all_meteors, fireball
from lib.PipeSync import sync_day 
from lib.PipeAutoCal import autocal , solve_field, cal_all, draw_star_image, freecal_copy, apply_calib, index_failed, deep_calib, deep_cal_report, blind_solve_meteors, guess_cal, flatten_image, project_many, project_snaps, review_cals, star_db_mag, cal_report, review_all_cals, reverse_map, cal_index, sync_back_admin_cals, min_fov
from lib.PipeReport import autocal_report, detect_report 
from lib.PipeLIVE import meteor_min_files, broadcast_live_meteors, broadcast_minutes, meteors_last_night, mln_final, pip_video, mln_sync, super_stacks, meteor_index, fix_missing_images, fflist, resize_video, minify_file, make_preview_meteor, make_preview_meteors, sync_preview_meteors
from lib.PipeTimeLapse import make_tl_for_cam, video_from_images, six_cam_video, timelapse_all, tn_tl6, sync_tl_vids, multi_cam_tl, audit_min, purge_tl , plot_min_int
from lib.PipeMeteorDelete import delete_all_meteor_files



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

help = """

./Process.py is the main program for accessing functions in the allsky system. Many / most of these functions are called by cron jobs or other programs. 

For reference, the following functions are available through this program. 

Call / run like this:

./Process FUNC_NAME ARGS

DETECT FUNCTIONS

LIVE FUNCTIONS

PREVIEW METEOR FUNCTIONS

MANAGER FUNCTIONS

AUTOCAL FUNCTIONS

""" 

def scan_stack_pending(proc_day=0):
   proc_day = 0
   files = get_pending_files()
   events = {}
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

   # DETECTION COMMANDS
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
      events, objects,total_frames, = detect_in_vals(sys.argv[2])
      print("EVENTS:", len(events))
      #trim_events(sys.argv[2], events, total_frames)
      
      print("\n\nOBJECTS:", len(objects))
      for o in objects:
         print("OBJ:", objects[o])
      #obj_report(objects)

   if cmd == 'da':
      detect_all(sys.argv[2])
     


   # SYNC CLOUD COMMANDS

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

   # AUTO CALIBRATION COMMANDS
  
   # review solved cal files
   if cmd == 'rc':
      review_cals(json_conf, sys.argv[2] )
   if cmd == 'rac':
      review_all_cals(json_conf)

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
      autocal_report("solved")
      autocal_report("failed")

   if cmd == "deep_cal":
      deep_calib(sys.argv[2], json_conf)
   if cmd == "dc_report":
      deep_cal_report(sys.argv[2], json_conf)
 
   # index the failed calibs
   if cmd == 'if':
      index_failed(json_conf)

   if cmd == "blind": 
      if len(sys.argv) > 3:
         blind_solve_meteors(sys.argv[2],json_conf ,sys.argv[3])
      else:
         blind_solve_meteors(sys.argv[2],json_conf )
   if cmd == "guess": 
      guess_cal(sys.argv[2],json_conf)


   # LIVE BUFFERED VIDEO COMMANDS

   # make the meter min files for a day 
   if cmd == 'mmf':
      meteor_min_files(sys.argv[2], json_conf)
   if cmd == 'blm':
      broadcast_live_meteors()
   if cmd == 'apply_calib':
      apply_calib(sys.argv[2], json_conf)

   if cmd == 'bcm':
      broadcast_minutes(json_conf)
   if cmd == 'mln':
      if len(sys.argv) == 3:
         meteors_last_night(json_conf, sys.argv[2])
      else:
         meteors_last_night(json_conf, None)


   # TIME LAPSE COMMANDS 
   if cmd == 'audit':

      today = datetime.now().strftime("%Y_%m_%d")
      yesterday = (datetime.now() - dt.timedelta(days = 1)).strftime("%Y_%m_%d")
      if sys.argv[2] == "today":
         audit_min(today, json_conf)
      elif sys.argv[2] == "yest":
         audit_min(yesterday, json_conf)
      else:
         audit_min(sys.argv[2], json_conf)
   if cmd == 'tlc':
      make_tl_for_cam(sys.argv[2], sys.argv[3], json_conf)
   if cmd == 'tla':
      timelapse_all(sys.argv[2], json_conf)
   if cmd == 'vfi':
      video_from_images(sys.argv[2], sys.argv[3], json_conf)
   if cmd == 'scv':
      six_cam_video(sys.argv[2], json_conf)
   if cmd == 'tntl':
      if sys.argv[2] == 'today':
         today = datetime.now().strftime("%Y_%m_%d")
         tn_tl6(today,json_conf)
      elif sys.argv[2] == 'yest':
         yesterday = (datetime.now() - dt.timedelta(days = 1)).strftime("%Y_%m_%d")
         tn_tl6(yesterday,json_conf)
      else:
         tn_tl6(sys.argv[2],json_conf)
   if cmd == 'stlv':
      sync_tl_vids()
   if cmd == 'mctl':
      multi_cam_tl(sys.argv[2])



   # REPORTS
   if cmd == "detect_rpt":
      detect_report(sys.argv[2], json_conf)

   # MANAGER FUNCTIONS 

   if cmd == "proc_status":
      proc_status()
   if cmd == "mln_rpt":
      mln_report(sys.argv[2])
   if cmd == "mln_best":
      mln_best(sys.argv[2])

   # METEOR LAST NIGHT FUNCTIONS 
   if cmd == "mln_final":
      mln_final(sys.argv[2])
   if cmd == "pip":
      pip_video(sys.argv[2], json_conf)
   if cmd == "mln_sync":
      mln_sync(sys.argv[2], json_conf)
   if cmd == "trans_test":
      trans_test(sys.argv[2], sys.argv[3])
   if cmd == "super_stack":
      super_stacks(sys.argv[2])
   if cmd == "best_of":
      best_of()
   if cmd == "meteor_index":
      meteor_index(sys.argv[2])
   if cmd == "fmi":
      fix_missing_images(sys.argv[2])

   # MANAGER / EDITOR FUNCTIONS
   if cmd == "cp_super":
      copy_super_stacks(sys.argv[2])
   if cmd == "ssv":
      super_stacks_to_video()
   if cmd == "qvs":
      quick_video_stack(sys.argv[2])
   if cmd == "ffcat":
      ffmpeg_cat(sys.argv[2], sys.argv[3])
   if cmd == "ffcats":
      ffmpeg_cats(sys.argv)
   if cmd == "msm":
      multi_station_meteors(sys.argv[2])
   if cmd == "fflist":
      fflist(sys.argv[2], sys.argv[3])
   if cmd == "rv":
      resize_video(sys.argv[2], sys.argv[3], sys.argv[4])
   if cmd == "fmd":
      fix_meteor_dir(sys.argv[2])
   if cmd == "minify":
      LIVE_METEOR_DIR = "/mnt/ams2/nice/min/"
      text = "James Hannon, Otter Creek TWP USA"
      meteor_data = {}
      meteor_data[sys.argv[2]] = {}
      meteor_data[sys.argv[2]]['sd_w'] = "640"
      meteor_data[sys.argv[2]]['sd_h'] = "360"
      sd_frame = np.zeros((1080,1920,3),dtype=np.uint8)
      hd_frame = np.zeros((1080,1920,3),dtype=np.uint8)
      meteor_data[sys.argv[2]]['xs'] = [208, 219, 190, 173, 179, 172, 160, 177, 138, 176, 183, 170, 117, 111, 93, 83, 66, 61, 55, 49, 45, 137, 136, 252, 137, 225, 226, 136, 136, 231, 216, 252, 202, 231, 216, 197, 216]
      meteor_data[sys.argv[2]]['ys'] = [450, 632, 650]
      hd_outfile, hd_cropfile, cropbox_1080,cropbox_720 = minify_file(sys.argv[2], LIVE_METEOR_DIR, text, meteor_data[sys.argv[2]], sd_frame, hd_frame)
      print(hd_outfile, hd_cropfile)
   if cmd == "trim":
      trim_out_file = sys.argv[2].replace(".mp4", "-trim-" + sys.argv[3] + ".mp4")
      # in file, start trim end trim frame num
      trim_min_file(sys.argv[2], trim_out_file, sys.argv[3], sys.argv[4])
   if cmd == "dmf":
      delete_all_meteor_files(sys.argv[2])
   if cmd == "dmic":
      hd_objects, frames = detect_meteor_in_clip(sys.argv[2], None, 0, 0, 0, 0)
      for obj in hd_objects:
         hd_objects[obj] = analyze_object(hd_objects[obj])
         if hd_objects[obj]['report']['meteor'] == 1:
            print("METEOR:", hd_objects[obj])
         else:
            print("NON METEOR:",hd_objects[obj])

   # METEOR PREVIEW FUNCTIONS
   if cmd == "mpv":
      make_preview_meteor(sys.argv[2],json_conf )
   if cmd == "mpvs":
      make_preview_meteors(sys.argv[2],json_conf )
   if cmd == "sync_previews":
      sync_preview_meteors(sys.argv[2],json_conf )
   if cmd == "refine":
      refine_meteor(sys.argv[2],json_conf )
   if cmd == "refine_all":
      refine_all_meteors(sys.argv[2],json_conf )
   if cmd == "clouds":
      detect_clouds(sys.argv[2],json_conf )
   if cmd == "make_flat":
      if len(sys.argv) > 3:
         day = sys.argv[3]
      else:
         day = None
      make_flat(sys.argv[2],day, json_conf )
   if cmd == "track_clouds":
      if len(sys.argv) > 3:
         day = sys.argv[3]
      else:
         day = None
      track_clouds(sys.argv[2],day, json_conf )
   if cmd == "solar":
      solar_info(sys.argv[2], json_conf)
   if cmd == "rm_corrupt":
      remove_corrupt_files(json_conf)
   if cmd == "flatten":
      flatten_image(sys.argv[2], json_conf)
   if cmd == "pm":
      fs= []
      for i in range(2,len(sys.argv)):
         fs.append(sys.argv[i])
      project_many(fs, json_conf)
   if cmd == "ps":
      project_snaps(json_conf)
   if cmd == "starmag":
      star_db_mag(sys.argv[2], json_conf)
   if cmd == "purge_tl":
      purge_tl()
   if cmd == "plot_min_int":
      plot_min_int(sys.argv[2], json_conf)
   if cmd == "cal_report":
      cal_report(json_conf)
   if cmd == "reverse_map":
      reverse_map(json_conf)
   if cmd == "cal_index":
      for cam in json_conf['cameras']:
         cams_id = json_conf['cameras'][cam]['cams_id']
         cal_index(cams_id, json_conf)
   if cmd == "sbac":
      sync_back_admin_cals()
   if cmd == "min_fov":
      min_fov(sys.argv[2], json_conf)
   if cmd == "fireball":
      fireball(sys.argv[2], json_conf)
   
