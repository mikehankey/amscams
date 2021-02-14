
import math
import scipy.optimize
from lib.UIJavaScript import *
import glob
from datetime import datetime as dt
import datetime
#import math
import os
from lib.FFFuncs import ffprobe as ffprobe4, imgs_to_vid
from lib.PipeAutoCal import fn_dir, get_cal_files, get_image_stars, get_catalog_stars, pair_stars, update_center_radec, cat_star_report, minimize_fov, XYtoRADec, poly_fit_check
from lib.PipeVideo import ffmpeg_splice, find_hd_file, load_frames_fast, find_crop_size, ffprobe
from lib.PipeUtil import load_json_file, save_json_file, cfe, get_masks, convert_filename_to_date_cam, buffered_start_end, get_masks, compute_intensity , bound_cnt, day_or_night
from lib.DEFAULTS import *
from lib.PipeMeteorTests import big_cnt_test, calc_line_segments, calc_dist, unq_points, analyze_intensity, calc_obj_dist, meteor_direction, meteor_direction_test, check_pt_in_mask, filter_bad_objects, obj_cm, meteor_dir_test, ang_dist_vel, gap_test, best_fit_slope_and_intercept
from lib.PipeImage import stack_frames

import numpy as np
import cv2




def make_event_video(meteor_file,json_conf)
   if "/mnt/ams2" not in meteor_file:
      date = meteor_file[0:10]
      meteor_file = "/mnt/ams2/meteors/" + date + "/" + meteor_file
      red_file = meteor_file.replace(".json", "")
      if cfe(meteor_file) == 1:
         mj = load_json_file(meteor_file)
      else:
         print("NO MJF", meteor_file)
         return()
      if cfe(red_file) == 1:
         print("NO MJR", red_file)
         return()
         mjr = load_json_file(red_file)
   sd_vid = mj['sd_video_file']
   hd_vid = mj['hd_trim']
   if cfe(sd_vid) == 0:
      sd_frames,sd_color_frames,sd_subframes,sd_sum_vals,sd_max_vals,sd_pos_vals = load_frames_fast(sd_vid, json_conf, 0, 0, 1, 1,[])
   if cfe(hd_vid) == 0:
      hd_vid = None
      hd_frames,hd_color_frames,subframes,sum_vals,max_vals,pos_vals = load_frames_fast(hd_vid, json_conf, 0, 0, 1, 1,[])

   sd_dts = []
   sd_fns = []
   sd_xs = []
   sd_ys = []
   for row in mfd:
      (dt, fn, x, y, w, h, oint, ra, dec, az, el) = row
      sd_dts.append(dt)
      sd_fns.append(fn)
      sd_xs.append(x)
      sd_ys.append(y)

   min_x = min(sd_xs) + 100
   min_y = min(sd_ys) + 100
   max_x = max(sd_xs) + 100
   max_y = max(sd_ys) + 100
   crop_area = [min_x, min_y, max_x, max_y]
   if min_x < 0:
      min_x = 0
   if min_y < 0:
      min_y = 0
   if max_x > 1919:
      max_x = 1919 
   if min_y > 1079:
      min_y = 1079

   for frame in subframes:
      crop_frame = frame[min_y:max_y, min_x:max_x]
      cv2.imshow('pepe', crop_frame)
