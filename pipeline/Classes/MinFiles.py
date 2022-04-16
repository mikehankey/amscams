import sys
import os
import glob
import cv2
import numpy as np
from PIL import ImageFont, ImageDraw, Image, ImageChops



from lib.PipeUtil import cfe, load_json_file, save_json_file, fn_dir, load_mask_imgs
from Detector import Detector


class MinFiles:
   def __init__(self):
      self.sd_data_dir = "/mnt/ams2/SD/"
      self.hd_data_dir = "/mnt/ams2/SD/"      

   def check_load_day(self, date):
      files = os.listdir(self.sd_data_dir + "proc2/" + date + "/" )
      day_dir = self.sd_data_dir + "proc2/" + date + "/"
      proc_counts = {}
      vids_trim = []
      vids_crop = []
      vids_min = []
      imgs_stack = []
      imgs_first = []
      ai_json = []
      sub_dirs = []
      for ff in files:

         el = ff.split("_")
         if len(el) >= 8:
            cam_id = el[7]
         else:
            cam_id = None

         if cam_id is not None and "." in cam_id :
            cam_id = cam_id.split(".")[0]
         if cam_id is not None and "-" in cam_id :
            cam_id = cam_id.split("-")[0]

         if cam_id is not None and cam_id not in proc_counts:

            proc_counts[cam_id] = {}
            proc_counts[cam_id]['first_files'] = 0
            proc_counts[cam_id]['stack_files'] = 0
            proc_counts[cam_id]['min_files'] = 0

         if "mp4" in ff:
            if "trim" in ff:
               vids_trim.append(ff)
            elif "crop" in ff:
               vids_crop.append(ff)
            else:
               vids_min.append(ff)
               proc_counts[cam_id]['min_files'] += 1

         elif "jpg" in ff:
            if "first" in ff:
               imgs_first.append(ff)
               proc_counts[cam_id]['first_files'] += 1
            elif "stack" in ff:
               imgs_stack.append(ff)
               proc_counts[cam_id]['stack_files'] += 1
         elif "-ai" in ff:
            ai_json.append(ff)
         elif os.path.isdir(day_dir) is True:
            sub_dirs.append(ff)
         else:
            print("???", day_dir + ff)
      print("Total Files:      ", len(files))
      print(" Trim Files:      ", len(vids_trim))
      print("  Min Files:      ", len(vids_min))
      print(" Imgs Stack:      ", len(imgs_stack))
      print(" Imgs First:      ", len(imgs_first))
      print("    AI JSON:      ", len(ai_json))
      print("   SUB DIRS:      ", len(sub_dirs))
      for cid in sorted(proc_counts.keys()):
         print(cid)
         print("Min Files:", proc_counts[cid]['min_files'])
         print("Stack Files:", proc_counts[cid]['stack_files'])
         print("First Files:", proc_counts[cid]['first_files'])

      files_left = len(vids_min) - len(ai_json)
      print("Night Files Left to Process:", files_left)
      time_est = int(((files_left * 8) / 60)/60)
      time_est2 = int(((files_left * 4) / 60)/60)
      print("Time Estimate @ 8 seconds per file: ", time_est, "hours")
      print("Time Estimate @ 4 seconds per file: ", time_est2, "hours")
>>>>>>> 90c103db209317cac2b41b58b9d9af01c61fab77
