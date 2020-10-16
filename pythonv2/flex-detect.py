#!/usr/bin/python3

import subprocess
import copy
from lib.VIDEO_VARS import PREVIEW_W, PREVIEW_H, SD_W, SD_H
#hdm_x = 1920 / SD_W
#hdm_y = 1080 / SD_H

#print(SD_W,SD_H)

from sklearn.cluster import DBSCAN
from fitPairs import reduce_fit
from lib.REDUCE_VARS import *
from lib.Video_Tools_cv_pos import *
from lib.Video_Tools_cv import *
from PIL import ImageFont, ImageDraw, Image, ImageChops
from lib.VIDEO_VARS import *
from lib.UtilLib import calc_dist,find_angle, best_fit_slope_and_intercept, logger 
from lib.MeteorTests import test_objects
import datetime
import time
import glob
import os
import math
import cv2
import math
import numpy as np
import scipy.optimize
import ephem
from lib.flexCal import flex_get_cat_stars, reduce_fov_pos


from lib.VideoLib import get_masks, find_hd_file_new, load_video_frames, sync_hd_frames, make_movie_from_frames, add_radiant, ffmpeg_trim

from lib.UtilLib import check_running, angularSeparation
from lib.CalibLib import radec_to_azel, clean_star_bg, get_catalog_stars, find_close_stars, XYtoRADec, HMS2deg, AzEltoRADec, get_active_cal_file

from lib.ImageLib import mask_frame , stack_frames, preload_image_acc, thumb
from lib.ReducerLib import setup_metframes, detect_meteor , make_crop_images, perfect, detect_bp, best_fit_slope_and_intercept, id_object, metframes_to_mfd

from lib.MeteorTests import meteor_test_cm_gaps

from lib.flexLib import stack_frames_fast

import sys
from lib.CalibLib import distort_xy_new, find_image_stars, distort_xy_new, XYtoRADec, radec_to_azel, get_catalog_stars,AzEltoRADec , HMS2deg, get_active_cal_file, RAdeg2HMS, clean_star_bg
from lib.UtilLib import calc_dist, find_angle, bound_cnt, cnt_max_px, bound_leading_edge_cnt 

from lib.UtilLib import angularSeparation, convert_filename_to_date_cam, better_parse_file_date
from lib.FileIO import load_json_file, save_json_file, cfe
from lib.UtilLib import calc_dist,find_angle
import lib.brightstardata as bsd
from lib.DetectLib import eval_cnt, check_for_motion2

json_conf = load_json_file("../conf/as6.json")
show = 0

ARCHIVE_DIR = "/mnt/ams2/meteor_archive/"

def man_detect(trim_file):
   objects, frames = detect_meteor_in_clip(trim_file)
   stacked_sd_frame = stack_frames_fast_old(frames)
   print(stacked_sd_frame)
   
   sd_h, sd_w = frames[0].shape[:2]

   hdm_x = 1920 / sd_w
   hdm_y = 1080 / sd_h 
   meteors = only_meteors(objects)
   #print(hd_meteors)
   if len(meteors) == 1:
      print("One meteor detected!") 
      start_fn = meteors[0]['ofns'][0]
      end_fn = meteors[0]['ofns'][-1]
      ttt = trim_file.split("-trim")
      trim_num = ttt[1].replace("-", "")
      trim_num = trim_num.replace(".mp4", "")
      print("TRIM:", trim_num)

      hd_file, hd_trim,time_diff_sec, dur = find_hd_file_best(trim_file, int(trim_num) + start_fn, (end_fn-start_fn)+50, 1)
      print("HD FILE:", hd_trim)

      hd_x1,hd_y1,hd_x2,hd_y2,hd_mid_x,hd_mid_y = get_roi(None, meteors[0], hdm_x, hdm_y)

      hd_prev_crop=[hd_x1,hd_y1,hd_x2,hd_y2,hd_mid_x,hd_mid_y]

      #preview_crop(hd_trim, hd_x1,hd_y1,hd_x2,hd_y2)


      hd_crop_file = ffmpeg_crop(hd_trim,hd_x1,hd_y1,hd_x2-hd_x1,hd_y2-hd_y1, 0)


      trim_crop_file = trim_file.replace(".mp4", "-crop.mp4")

      hd_objects, hd_frames = detect_meteor_in_clip(hd_trim)
    
      print(hd_objects)
      stacked_hd_frame = stack_frames_fast_old(hd_frames )
      hd_meteors = only_meteors(hd_objects)
      print(hd_meteors)
      hd_meteors[0]['hd_trim'] = hd_trim
      calib,cal_params = apply_calib(hd_meteors[0], hd_frames)
      print(calib)
      print("BAD CALIB ERROR")
      exit()

      save_old_and_new_meteor(trim_file, hd_trim, meteors, hd_objects, stacked_sd_frame, stacked_hd_frame)
      print("SD:", trim_file)
      print("HD:", hd_trim)

def save_old_and_new_meteor(sd_trim, hd_trim, sd_objs,hd_objs, sd_stack, hd_stack, calib):
   sd_fn = sd_trim.split("/")[-1]
   hd_fn = hd_trim.split("/")[-1]
   day = sd_fn[0:10]
   mdir = "/mnt/ams2/meteors/" + day + "/"
   arc_file = ""
   js = {}
   sd_file = mdir + sd_fn
   hd_file = mdir + hd_fn
   sd_stack_file = sd_file.replace(".mp4", "-stacked.png")
   hd_stack_file = hd_file.replace(".mp4", "-stacked.png")
   js['sd_video_file'] = sd_file
   js['trim_clip'] = sd_file
   js['hd_video_file'] = hd_file
   js['hd_trim'] = hd_file
   js['archive_file'] = arc_file
   js['sd_objects'] = sd_objs
   js['hd_objects'] = hd_objs 
   js['hd_stack'] = hd_stack_file
   js['sd_stack'] = sd_stack_file
   old_meteor_json = sd_file.replace(".mp4" , ".json")
   save_json_file(old_meteor_json, js)
   os.system("cp " + sd_trim + " " + sd_file)
   os.system("cp " + hd_trim + " " + hd_file)
   cv2.imwrite(sd_stack_file, sd_stack)
   cv2.imwrite(hd_stack_file, hd_stack)
   print(old_meteor_json)

   # now save the new
   

def fix_arc_meteor(arc_file):
   arc_data = load_json_file(arc_file)
   sd_vid = arc_data['info']['sd_vid']
   hd_vid = arc_data['info']['hd_vid']
   frames = arc_data['frames']
   if 'stars' in arc_data['calib']:
      stars = arc_data['calib']['stars']
   else:
      stars = []
   # check if stars are missing, if they are re-cal the meteor
   if 'total_res_px' in arc_data['calib']['device']:
      total_res_px = arc_data['calib']['device']['total_res_px']
   else:  
      total_res_px = 9999


   if "refit" not in arc_data['calib']:
      arc_data['calib']['refit'] = 1
   else:
      arc_data['calib']['refit'] += 1

   if len(stars) == 0:
      print("STARS:", stars)
      os.system("./flex-detect.py ram " + arc_file)
      arc_data = load_json_file(arc_file)
      total_res_px = arc_data['calib']['total_res_px']
      stars = arc_data['calib']['stars']
   # refit the meteor
   if len(stars) > 5 and float(total_res_px) > 3:
      print("TOTAL RES:", total_res_px)
      print("STARS:", stars)
      print("RES:", total_res_px)
      os.system("./flex-detect.py faf " + arc_file)
   # check if frames are missing if they are re-detect
   #if len(frames) <= 3:
   if True:
      print("Re detect meteor!")   
      # try HD file first.
      hd_frames,hd_color_frames,hd_subframes,hd_sum_vals,hd_max_vals,hd_pos_vals = load_frames_fast(hd_vid, json_conf, 0, 0, [], 1,[])

      hd_x1 = 0
      hd_y1 = 0
      print("HD_VID:", hd_vid)
      hd_motion_objects,hd_meteor_frames = detect_meteor_in_clip(hd_vid, hd_subframes, 0,hd_x1,hd_y1,1)
      hd_meteors = only_meteors(hd_motion_objects)
      for hm in hd_meteors: 
         print(hm)
      (start_trim_time, sd_cam, sd_date, sd_y, sd_m, sd_d, sd_h, sd_M, sd_s) = convert_filename_to_date_cam(hd_vid)

      cal_params = calib_to_calparams(arc_data['calib'], hd_vid)
      frames = obj_to_frames(hd_meteors[0], start_trim_time,cal_params)
      arc_data['frames'] = frames
      save_json_file(arc_file, arc_data)
      os.system("python3 MakeCache.py " + arc_file)
      #sd_frames,sd_color_frames,sd_subframes,sum_vals,max_vals,pos_vals = load_frames_fast(sd_vid, json_conf, 0, 0, [], 1,[])


def make_crop_compo(meteor_file=None):
   if "/meteors/" in meteor_file:
      mj = load_json_file(meteor_file)
   else:
      aj = load_json_file(meteor_file)
      mj = None

   if mj is None:
      roi_crop = aj['info']


def find_hd_file_best(sd_file, trim_num, dur = 25, trim_on =1):
   video_file = sd_file
   print("FIND HD FILE NEW FOR :", sd_file)
   print("SD TRIM NUM: ", trim_num)
   print("SD DU : ", dur)
   print("TRIM ON : ", trim_on)
   hd_file = None
   (sd_datetime, sd_cam, sd_date, sd_y, sd_m, sd_d, sd_h, sd_M, sd_s) = convert_filename_to_date_cam(sd_file)
   day = sd_y + "_" + sd_m + "_" + sd_d
   #if trim_num > 1400:
      #hd_file, hd_trim = eof_processing(sd_file, trim_num, dur)
   #   time_diff_sec = int(trim_num / 25)
   #   if hd_file != 0:
   #      return(hd_file, hd_trim, time_diff_sec, dur)
   offset = int(trim_num) / 25
   meteor_datetime = sd_datetime + datetime.timedelta(seconds=offset)
   hd_glob = "/mnt/ams2/HD/" + sd_y + "_" + sd_m + "_" + sd_d + "_*" + sd_cam + "*.mp4"
   hd_files = sorted(glob.glob(hd_glob))
   hd_files_time = []
   for hd_file in hd_files:
      el = hd_file.split("_")
      if len(el) == 8 and "meteor" not in hd_file and "crop" not in hd_file and "trim" not in hd_file and "TL" not in hd_file:
 
         hd_datetime, hd_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(hd_file)
         time_diff = meteor_datetime - hd_datetime
         time_diff_sec = time_diff.total_seconds()
         if 0 <= time_diff_sec <= 60:
            print("TIME DIFF SEC:", time_diff_sec)
            hd_files_time.append((hd_file, time_diff_sec, hd_datetime))

   #print(hd_files_time)
   #exit()
   if len(hd_files_time) > 0:
      temp = sorted(hd_files_time, key=lambda x: x[1], reverse=False)

      hd_file = temp[0][0]
      time_diff_sec = temp[0][1]
      hd_datetime = temp[0][2]
      dur = int(dur)
   else:
      print("NO HD FILES FOUND!")
      #exit()

   if hd_file is not None:
      trim_adj = int(time_diff_sec * 25)
      print("METEOR TIME:", meteor_datetime)
      print("HD DATE TIME:", hd_datetime)
      print("TIME DIFF SEC", time_diff_sec)
      print("TRIM ADJ:", trim_adj)
      print("HD FILE:", hd_file)
      print("SD FILE:", video_file)

      hd_start = trim_adj 
      hd_end = trim_adj + dur 
      if hd_start < 0:
         hd_start = 0

      print("HD TRIM:", hd_start, hd_end, trim_adj, time_diff_sec)
      hd_trim , trim_start, trim_end = make_trim_clip(hd_file, hd_start, hd_end)
      print("SD/HD:", sd_file, hd_trim, trim_adj, trim_adj+dur)
      hd_proc_dir = "/mnt/ams2/SD/proc2/" + day + "/hd_save";
      if cfe(hd_proc_dir,1) == 0:
         os.makedirs(hd_proc_dir)
      cmd = "cp " + hd_file + " " + hd_proc_dir
      os.system(cmd)
      cmd = "cp " + hd_trim + " " + hd_proc_dir
      os.system(cmd)
      return(hd_file, hd_trim, time_diff_sec, dur)
   else:
      print("NO HD FOUND")
      hd_trim = None

   # No HD file was found. Trim out the SD Clip and then upscale it.
   #print("NO HD FILE FOUND.")
   hd_trim = upscale_sd_to_hd(sd_file)

   #time_diff_sec = int(trim_num / 25)
   #dur = int(dur) + 1 + 3
   #print("UPSCALE FROM SD!", time_diff_sec, dur)
   #time_diff_sec = time_diff_sec - 1
   #sd_trim = ffmpeg_trim(sd_file, str(time_diff_sec), str(dur), "-trim-" + str(trim_num) + "-SD-meteor")
   #hd_trim = upscale_sd_to_hd(sd_trim)
   #if "-SD-meteor-HD-meteor" in hd_trim:
   #   orig_hd_trim = hd_trim
   #   hd_trim = hd_trim.replace("-SD-meteor", "")
   #   hdf = hd_trim.split("/")[-1]
   #   os.system("mv " + orig_hd_trim + " /mnt/ams2/HD/" + hdf)
   #   print("HD F: mv " + orig_hd_trim + " /mnt/ams2/HD/" + hdf)
   #   hd_trim = "/mnt/ams2/HD/" + hdf

   return(sd_file,hd_trim,str(0),str(dur))


def finish_meteor(meteor_file):
   video_file = meteor_file.replace("-meteor.json", ".mp4")
   if "proc2" in meteor_file:
      video_file = video_file.replace("data/", "")
   if cfe(video_file) == 0:
      print("File not found.", video_file)
      exit()
   (f_datetime, cam, f_date_str,year,mon,dom, fh, fmin, fs) = convert_filename_to_date_cam(meteor_file)
   # after detect is made finish processing on meteor
   # convert to old and new json formats
   # save file in old
   # save files in new
   # make preview images
   # sync SD/HD clips
   # copy previews to wasabi
   # copy arc files to wasabi
   # make cache for archive & remake the 
   # save original detection min files /mnt/ams2/min_files/ 
   meteor_data = load_json_file(meteor_file)
   sd_meteors = meteor_data['sd_meteors']
   print("VID:", video_file)
   sd_frames,sd_color_frames,sd_subframes,sum_vals,max_vals,pos_vals = load_frames_fast(video_file, json_conf, 0, 0, [], 1,[])

   sd_h, sd_w = sd_color_frames[5].shape[:2]

   hdm_x = 1920 / sd_w
   hdm_y = 1080 / sd_h 

   if "hd_meteors" in meteor_data:
      hd_meteors = meteor_data['hd_meteors']
   else:
      hd_meteors = None
      print("We have no HD Meteors!") 
      hd_meteors = copy.deepcopy(meteor_data['sd_meteors'])
      new_hd_meteors = []
      for obj in hd_meteors: 
         hd_trim = upscale_sd_to_hd(obj['trim_clip'])
         obj['trim_clip'] = hd_trim
         hdxs = []
         hdys = []
         for ii in range(0, len(obj['oxs'])):
            hd_x = int(obj['oxs'][ii] * hdm_x)
            hd_y = int(obj['oys'][ii] * hdm_y)
            hdxs.append(hd_x)
            hdys.append(hd_y)
         obj['oxs'] = hdxs
         obj['oys'] = hdys
         new_hd_meteors.append(obj)
      hd_meteors = new_hd_meteors

      print("HD:", hd_meteors)
      print("SD:", sd_meteors)
 
 
   for i in range(0,len(sd_meteors)):
      sd_meteor = sd_meteors[i] 
      sd_frames,sd_color_frames,sd_subframes,sum_vals,max_vals,pos_vals = load_frames_fast(sd_meteors[i]['trim_clip'], json_conf, 0, 0, [], 1,[])
      if hd_meteors is not None:
         hd_meteor = hd_meteors[i] 
         hd_frames,hd_color_frames,hd_subframes,sum_vals,max_vals,pos_vals = load_frames_fast(hd_meteors[i]['trim_clip'], json_conf, 0, 0, [], 1,[])
      else:
         hd_meteor = None

      # save the original SD/HD min clips in case something happens in the trim
      sd_fn = sd_meteors[i]['trim_clip'].split("/")[-1]

      if hd_meteors is not None:
         hd_fn = hd_meteors[i]['trim_clip'].split("/")[-1]
         hd_meteors[i]['trim_clip'] = hd_fn
         hd_full = hd_fn.split("-trim")[0]
         if ".mp4" not in hd_full:
            hd_full  += ".mp4"
            hd_meteors[i]['hd_file'] = hd_full

      year = sd_fn[0:4]
      day = sd_fn[0:10]
      min_dir = "/mnt/ams2/min_save/" + year + "/" + day + "/" 
      old_meteor_dir = "/mnt/ams2/meteors/" + "/" + day + "/" 
      if cfe(min_dir, 1) == 0:
         os.makedirs(min_dir)
      if cfe(min_dir + sd_fn) == 0:
         os.system("cp " + sd_meteors[i]['trim_clip'] + " " + min_dir) 
      if cfe(min_dir + hd_fn) == 0:
         os.system("cp " + hd_meteors[i]['trim_clip'] + " " + min_dir) 
      if cfe(min_dir + hd_full) == 0:
         os.system("cp /mnt/ams2/HD/" + hd_full + " " + min_dir) 
   
      sd_start = min(sd_meteor['ofns'])
      sd_end = max(sd_meteor['ofns'])
      if hd_meteors is not None:
         hd_start = min(hd_meteor['ofns'])
         hd_end = max(hd_meteor['ofns'])
      buf_size = len(sd_meteor['ofns'])
      if buf_size < 10:
         buf_size = 10
      if buf_size > 50:
         buf_size = 50
      sd_t_start, sd_t_end = buffered_start_end(sd_start,sd_end, len(sd_frames), buf_size)
      sync_sd_frames = sd_color_frames[sd_t_start:sd_t_end]
      if hd_meteors is not None:
         hd_t_start, hd_t_end = buffered_start_end(hd_start,hd_end, len(hd_frames), buf_size)
         sync_hd_frames = hd_color_frames[hd_t_start:hd_t_end]


      # remap frame numbers
      orig_sd_ofns = sd_meteor['ofns']
      orig_hd_ofns = hd_meteor['ofns']
      new_sd_ofns = []
      new_hd_ofns = []
      for fn in orig_sd_ofns:
         new_sd_ofns.append(fn - sd_t_start)
      for fn in orig_hd_ofns:
         new_hd_ofns.append(fn - hd_t_start)
      sd_meteor['ofns'] = new_sd_ofns
      hd_meteor['ofns'] = new_hd_ofns

      # calculate clip and frame times
      (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(sd_meteor['trim_clip'])
      extra_sec = sd_t_start / 25

      sd_ftimes = []
      hd_ftimes = []
      start_trim_frame_time = f_datetime + datetime.timedelta(0,extra_sec)
      for fn in sd_meteor['ofns']:
         extra_sec = fn / 25
         frame_time = start_trim_frame_time + datetime.timedelta(0,extra_sec)
         sd_ftimes.append(frame_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3])
      sd_meteor['ftimes'] = sd_ftimes
      for fn in hd_meteor['ofns']:
         extra_sec = fn / 25
         frame_time = start_trim_frame_time + datetime.timedelta(0,extra_sec)
         hd_ftimes.append(frame_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3])
      hd_meteor['ftimes'] = hd_ftimes

      print("HD F:", len(sync_hd_frames))
      print("SD F:", len(sync_sd_frames))
     
      #for i in range(0,len(sync_sd_frames)):
      #   sd_frame = sync_sd_frames[i]
      #   hd_frame = cv2.resize(sync_hd_frames[i], (1280,720))
         #cv2.imshow('pepe', sd_frame)
         #cv2.imshow('pepehd', hd_frame)
         #cv2.waitKey(0)

      sd_trim_num = sd_t_start
      old_sd_fn = sd_fn.replace(".mp4", "-trim" + str(sd_trim_num)) + ".mp4"
      old_hd_fn = sd_fn.replace(".mp4", "-trim-" + str(sd_trim_num)) + "-HD-meteor.mp4"
      new_sd_fn = sd_fn.replace(".mp4", "-trim" + str(sd_trim_num))
      new_hd_fn = sd_fn.replace(".mp4", "-trim" + str(sd_trim_num))
      new_sd_file_name = min_dir + new_sd_fn + "-SD.mp4"
      new_hd_file_name = min_dir + new_sd_fn + "-HD.mp4"
      new_json_file_name = min_dir + new_sd_fn + ".json"

      sd_meteor['trim_clip'] = old_sd_fn  
      hd_meteor['trim_clip'] = old_hd_fn  


      print(new_sd_fn)
      print(new_hd_fn)
      print(new_sd_file_name)
      print(new_hd_file_name)

      make_movie_from_frames(sync_hd_frames, [0,len(sync_hd_frames) - 1], new_hd_file_name, 0)
      make_movie_from_frames(sync_sd_frames, [0,len(sync_sd_frames) - 1], new_sd_file_name, 0)

     

      old_json_data, new_json_data = make_json_files(sd_meteor,hd_meteor)



      print(old_json_data)
      old_js = old_sd_fn.replace(".mp4", ".json")
      old_json_file = old_meteor_dir + old_js 
      old_sd_file = old_meteor_dir + old_sd_fn 
      old_hd_file = old_meteor_dir + old_hd_fn 
      if cfe(old_meteor_dir, 1) == 0:
         os.makedirs(old_meteor_dir)
      print("cp " + new_sd_file_name + " " + old_sd_file )
      print("cp " + new_hd_file_name + " " + old_hd_file )

      os.system("cp " + new_sd_file_name + " " + old_sd_file )
      os.system("cp " + new_hd_file_name + " " + old_hd_file )
      os.system("./stackVideo.py sv " + old_sd_file )
      os.system("./stackVideo.py sv " + old_hd_file )
      print(old_json_file)
    
      hd_meteor['hd_trim'] = old_hd_file

      # convert / save new json format
      calib,cal_params = apply_calib(hd_meteor, hd_frames)
      calib = format_calib(old_sd_file, cal_params, old_sd_file)
      hd_meteor['calib'] = calib
      hd_meteor['cal_params'] = cal_params

      arc_fn = new_json_file_name.split("/")[-1]
      station_id = json_conf['site']['ams_id']
      arc_dir = "/mnt/ams2/meteor_archive/" + station_id + "/METEOR/" + year + "/" + mon + "/" + dom + "/"  
      arc_json = "/mnt/ams2/meteor_archive/" + station_id + "/METEOR/" + year + "/" + mon + "/" + dom + "/" + arc_fn
      arc_sd = arc_json.replace(".json", "-SD.mp4")
      arc_hd = arc_json.replace(".json", "-HD.mp4")

      old_json_data['archive_file'] = arc_json

      save_json_file(old_json_file, old_json_data )

      # save arc file
      if cfe(arc_dir, 1) == 0:
         os.makedirs(arc_dir)

      new_json = save_new_style_meteor_json(hd_meteor, new_json_file_name )
      os.system("cp " + new_hd_file_name + " " + arc_hd)
      print("cp " + new_hd_file_name + " " + arc_hd)
      os.system("cp " + new_sd_file_name + " " + arc_sd)
      print("cp " + new_sd_file_name + " " + arc_sd)
      print(new_json_file_name)

      new_json['info']['org_hd_vid'] = old_hd_file
      new_json['info']['org_sd_vid'] = old_sd_file
      new_json['info']['hd_vid'] = arc_hd
      new_json['info']['sd_vid'] = arc_sd

      save_json_file(arc_json, new_json)
      print("SAVED ARC:", arc_json)

      # Move work files to processed dir 
      if cfe("/mnt/ams2/CAMS/processed_meteors/", 1) == 0:
         os.makedirs("/mnt/ams2/CAMS/processed_meteors/")
      # mv orig video file, stack file and image stack to proc2 dirs
      video_file = meteor_file.replace("-meteor.json", ".mp4")
      vals_file = meteor_file.replace("-meteor.json", "-vals.json")
      stack_file = meteor_file.replace("-meteor.json", "-stacked.png")


      proc_dir = "/mnt/ams2/SD/proc2/" + day + "/"
      proc_img_dir = "/mnt/ams2/SD/proc2/" + day + "/images/"
      proc_data_dir = "/mnt/ams2/SD/proc2/" + day + "/data/"
      proc_hd_dir = "/mnt/ams2/SD/proc2/" + day + "/hd_saved/"
      if cfe(proc_img_dir,1) == 0:
         os.makedirs(proc_img_dir)
      if cfe(proc_data_dir,1) == 0:
         os.makedirs(proc_data_dir)
      if cfe(proc_hd_dir,1) == 0:
         os.makedirs(proc_hd_dir)
 

      cmd = "mv " + video_file + " " + proc_dir
      print(cmd)
      os.system(cmd)
      cmd = "mv " + stack_file + " " + proc_img_dir
      print(cmd)
      os.system(cmd)
      cmd = "mv " + meteor_file + " " + proc_data_dir
      print(cmd)
      os.system(cmd)
      cmd = "mv " + vals_file + " " + proc_data_dir
      print(cmd)
      os.system(cmd)
      msf = new_hd_file_name.split("/")[-1]

      min_save_files = new_hd_file_name.replace(msf, "*")
      cmd = "mv " + min_save_files + " " + proc_hd_dir
      os.system(cmd)
      print(cmd)

      # mv source HDs if we can:
      if hd_meteor is not None:
         hd_root = "/mnt/ams2/HD/" + hd_meteors[i]['trim_clip'].split("-trim")[0]
         cmd = "mv " + hd_root + "* " + min_save_files
         os.system(cmd)
         print(cmd)



      #arc_json_file = save_archive_meteor(video_file, syncd_sd_frames,syncd_hd_frames,frame_data,new_trim_num) 
      save_old_style_meteor_json(old_meteor_json_file, obj, trim_clip )

def make_json_files(sd_meteor, hd_meteor):
   file = sd_meteor['trim_clip']
   year = file[0:4]
   mon = file[5:7]
   dom = file[8:10]
   day = file[0:10]

   print("date:", year, mon, dom, day)

   old_json = {}
   new_json = {}
   new_json['calib'] = {}
   new_json['info'] = {}
   new_json['report'] = {}
   new_json['frames'] = {}
   new_json['sync'] = {}
  
   
   old_json['sd_video_file'] = "/mnt/ams2/meteors/" + day + "/" + sd_meteor['trim_clip']
   old_json['sd_stack'] = "/mnt/ams2/meteors/" + day + "/" + sd_meteor['trim_clip'].replace(".mp4", "-stacked.png")
   if hd_meteor is not None:
      old_json['hd_stack'] = "/mnt/ams2/meteors/" + day + "/" + hd_meteor['trim_clip'].replace(".mp4", "-stacked.png")
      old_json['hd_video_file'] = "/mnt/ams2/meteors/" + day + "/" + hd_meteor['trim_clip']
      old_json['hd_trim'] = "/mnt/ams2/meteors/" + day + "/" + hd_meteor['trim_clip']
   else:
      old_json['hd_stack'] = 0
      old_json['hd_video_file'] = 0
      old_json['hd_trim'] = 0

   old_json['status'] = ""
   old_json['total_frames'] = ""
   old_json['meteor'] = 1
   old_json['test_results'] = ""
   old_json['hd_trim_dir'] = ""
   old_json['hd_trim_time_offset'] = ""
   old_json['flex_detect'] = ""
   old_json['archive_file'] = ""
   old_json['sd_objects'] = []

   # make SD objects from new meteor
   sd_object = {}
   ofns = sd_meteor['ofns']
   oxs = sd_meteor['oxs']
   oys = sd_meteor['oys']
   ows = sd_meteor['ows']
   ohs = sd_meteor['ohs']
   oints = sd_meteor['oint']
   hist = []
   for i in range (0, len(ofns)-1):
      fn = ofns[i]
      x = oxs[i]
      y = oys[i]
      w = ows[i]
      h = ohs[i]
      oint = oints[i]
      hist.append((fn,x,y,w,h,0,0))
   sd_object['oid'] = 1
   sd_object['fc'] = len(ofns)
   sd_object['x'] = oxs[0]
   sd_object['y'] = oys[0]
   sd_object['w'] = max(ows)
   sd_object['h'] = max(ohs)
   sd_object['history'] = hist

   old_json['hd_objects'] = [] 
   old_json['sd_objects'].append( sd_object )


   return(old_json, new_json)

def make_object_image(img, data):
   cvimg = cv2.imread(img)
   oimg = img.replace(".png", "-obj.png")
   for i in range(0,len(data['ofns'])):
      x = data['oxs'][i]
      y = data['oys'][i]
      cv2.circle(cvimg,(x,y), 1, (255,0,0), 1)
      cv2.imwrite(oimg, cvimg)

def calc_seg_len(data):
   fx = None
   last_dist_from_start = None
   fc = 0
   segs = []
   bad_segs = 0
   for i in range(0, len(data['ofns'])):
      x = data['oxs'][i]
      y = data['oys'][i]
      if fx is None:
         fx = x
         fy = y
      dist_from_start = calc_dist((fx,fy),(x,y))
      data['dist_from_start'] = dist_from_start
      if last_dist_from_start is not None:
         seg_len = int(abs(dist_from_start - last_dist_from_start))
         segs.append(seg_len)
         if seg_len == 0:
            bad_segs += 1
      else:
         segs.append(0)
      last_dist_from_start = dist_from_start
      fc += 1
   data['segs'] = segs
   data['med_seg'] = float(np.median(segs))
   sc = 0
   for seg in segs:
      diff = abs(seg - data['med_seg'])
      if data['med_seg'] > 0 and sc > 0 and seg != 0:
         #print("SEG:", seg, data['med_seg']) 
         diff_diff = seg / data['med_seg']
         if diff_diff > 2 or diff_diff < .5:
            bad_segs += 1
      sc += 1
   if len(data['ofns']) - 1 > 0:
      data['bad_seg_perc'] = bad_segs / (len(data['ofns']) - 1)
   else:
      data['bad_seg_perc'] = 1 
   data['bad_segs'] = bad_segs
   return(data)

def classify_object(data, sd=1):
   fns = data['ofns']
   x = data['oxs']
   y = data['oys']
   hd_px_scale = 260   # arc seconds
   sd_px_scale = 260 * 2.72
   if sd == 1:
      px_scale = sd_px_scale
   else:
      px_scale = hd_px_scale

   px_dist = calc_dist((x[-1],y[-1]), (x[0],y[0]))

   angular_separation = np.sqrt((x[-1] - x[0])**2 + (y[-1] - y[0])**2) 
   angular_separation_px = np.sqrt((x[-1] - x[0])**2 + (y[-1] - y[0])**2) / float(fns[-1] - fns[0])
   angular_velocity_px = angular_separation_px * 25

   angular_separation_deg = (angular_separation * px_scale) / 3600

   # Convert to deg/sec
   #scale = (config.fov_h/float(config.height) + config.fov_w/float(config.width))/2.0
   #ang_vel = ang_vel*scale

   angular_velocity_deg = (angular_velocity_px * px_scale) / 3600
   report = {}
   report['px_dist'] = px_dist
   report['ang_sep_px'] = angular_separation_px
   report['ang_vel_px'] = angular_velocity_px
   report['ang_sep_deg'] = angular_separation_deg
   report['ang_vel_deg'] = angular_velocity_deg
   report['bad_items'] = []

   report['meteor_yn'] = "Y"

   # filter out detections that don't match ang vel or ang sep desired values
   if float(report['ang_vel_deg']) > .5 and float(report['ang_vel_deg']) < 80:
      report['meteor_yn'] = "Y"
   else:
      report['meteor_yn'] = "no"
      report['bad_items'].append("bad ang vel: " + str(report['ang_vel_deg']))

   if report['meteor_yn'] == "Y" and report['ang_sep_deg'] < .4:
      report['meteor_yn'] = "no"
      report['bad_items'].append("bad ang sep: " + str(report['ang_sep_deg']))
   if px_dist < 4:
      print("BAD PX", px_dist)
      report['meteor_yn'] = "no"
      report['bad_items'].append("bad px dist: " + str(report['px_dist']))

   # filter out detects with low CM
   last_fn = None
   cm = 1
   for fn in fns:
      if last_fn is not None:
         if (last_fn + 1 == fn) or (last_fn + 2 == fn):
            cm += 1
      last_fn = fn
   if cm < 3:
      report['meteor_yn'] = "no"
      report['bad_items'].append("low cm: " + str(cm))
   report['cm'] = cm

   # filter out detects that have too many dupe pix
   unq_keys = {}
   unq = 0

   for i in range(0, len(fns)):
      key = str(data['oxs'][i]) + "." + str(data['oys'][i])
      if key not in unq_keys:
         unq += 1
         unq_keys[key] = 1
   if len(data['oxs']) > 0:
      unq_perc = unq / len(data['oxs'])
      report['unq_perc'] = unq_perc
      report['unq'] = str(unq) + "/" + str(len(data['oxs']))
      report['unqkeys'] = str(unq_keys)
   if unq_perc < .7:
      report['meteor_yn'] = "no"
      report['bad_items'].append("bad unq %: " + str(unq_perc))

   # filter out detects that have too many bad seg lens
   data = calc_seg_len(data)
   if data['bad_seg_perc'] >= .49:
      report['meteor_yn'] = "no"
      report['bad_items'].append("bad seg %: " + str(data['bad_seg_perc']))

   # filter out detects that are zig zagged or not moving in the same direction too much as % of frames




   # filter out detects have more the 33% low or negative intensity frames
   itc = 0
   for intense in data['oint']:
      if intense < 0:
         itc += 1
   if itc > 0:
      itc_perc = itc / len(data['oint'])
      report['neg_int_perc'] = itc_perc
      if itc_perc > .3:
         report['meteor_yn'] = "no"
         report['bad_items'].append("bad neg int: " + str(report['neg_int_perc']))
   else: 
      report['neg_int_perc'] = 0
   report['segs'] = data['segs']
   report['bad_seg_perc'] = data['bad_seg_perc']

   #print("REPORT:", data['obj_id'], data['oint'], report)
   return(report)



def run_archive():
   if check_running("flex-detect.py bams") == 0:
      print("Archiver is not running.")
      os.system("./flex-detect.py bams 1 &")
   else:
      print("Archiver is running.")

def batch_archive_msm(mode):
   total_files = 0
   total_arc = 0
   station = json_conf['site']['ams_id']
   ms_detect_file = ARCHIVE_DIR + station + "/DETECTS/" + "ms_detects.json"
   ms_detect_report_file = ARCHIVE_DIR + station + "/DETECTS/" + "ms_detects_report.html"
   ms_data = load_json_file(ms_detect_file)
   out = ""
   failed_files = []
   no_reruns = 0
   for day in sorted(ms_data, reverse=True):
      for file in ms_data[day]:
         meteor_day = file[0:10]
         orig_meteor_json_file = "/mnt/ams2/meteors/" + meteor_day + "/" + file
         mjd = load_json_file(orig_meteor_json_file)
         video_file = orig_meteor_json_file.replace(".json", ".mp4")
         stack_thumb = orig_meteor_json_file.replace(".json", "-stacked-tn.png")
         prev_img = stack_thumb.replace("-stacked-tn.png", "-prev-crop.jpg")
         print("PREV", prev_img)
         if cfe(prev_img) == 1:
            stack_thumb = prev_img


         if mjd == 0:
            continue
         jsid = video_file.split("/")[-1]
         jsid = jsid.replace("_", "")
         jsid = jsid.replace(".mp4", "")
         del_link = " - <a href=/pycgi/webUI.py?cmd=override_detect&jsid=" + jsid + ">DEL</a>"

         if "archive_file" in mjd:
            if cfe(mjd['archive_file']) == 0:
               del(mjd['archive_file'])
               save_json_file(orig_meteor_json_file, mjd)

         if "archive_file" in mjd:
            print(orig_meteor_json_file + " ARCHIVED") 
            desc_long = file.replace(".json", "")

            desc = desc_long.split("-trim")[0]
            out += "<figure style=\"float: left; text-align: center\"><a href=/pycgi/webUI.py?cmd=reduce&video_file=" + video_file + "><img src=" + stack_thumb + "><figcaption style=\"font-size: x-medium\">" + desc + "</figcaption></a></figure>\n"
            total_arc +=1
         elif "arc_fail" in mjd and no_reruns == 1:
            failed_files.append((file, mjd['arc_fail']))
            print(orig_meteor_json_file + " ARCHIVED") 
            desc_long = file.replace(".json", "")
            desc = desc_long.split("-trim")[0]
            out += "<figure style=\"float: left; background-color: red; text-align: center\"><a href=/pycgi/webUI.py?cmd=reduce&video_file=" + video_file + "><img src=" + stack_thumb + "><figcaption style=\"font-size: x-medium\">" + desc + "</a> " + del_link + "</figcaption></figure>\n"
            total_arc +=1


         else:
            desc = file.replace(".json", "")

            print(del_link)
            out += "<figure style=\"float: left; background-color: coral; text-align: center\"><a href=/pycgi/webUI.py?cmd=reduce&video_file=" + video_file + "><img src=" + stack_thumb + "><figcaption style=\"font-size: x-medium\">" + desc + "</a>" + del_link + "</figcaption></a> </figure>\n"
            cmd = "./flex-detect.py debug2 " + video_file
            print(cmd)
            if mode == "1":
               os.system(cmd)
               if total_files > 200:
                  print("Finsihed run of 25 files. Exiting for now.", mode, total_files)
                  exit()
               #exit()
         if "archive_file" not in mjd:
            total_files += 1
   print(ms_detect_report_file)
   out = "<h1>Archive Report</h1> Total Meteors: " + str(total_files) + " Total Archived: " + str(total_arc) + "<P>" + out
   fp = open(ms_detect_report_file, "w")
   fp.write(out) 
   fp.close()
   for failed in failed_files:
      print(failed)

def fix_missing_hd(dir):
   files = glob.glob(dir + "*.json")
   for file in files:
      if "reduced" not in file:
         data = load_json_file(file)
         if "hd_trim" in data:
            if data['hd_trim'] == 0:
               print("hd trim is 0:", file)
               print("hd file is :", data['hd_video_file'])
               if data['hd_video_file'] != 0: 
                  hd_fn = data['hd_video_file'].split("/")[-1]
                  hd_fn = hd_fn.replace(".mp4", "*HD-meteor.mp4")
                  trim_wild = dir + hd_fn
                  trims = glob.glob(trim_wild)
                  if len(trims) > 0:
                     print("NEW FOUND TRIM IS :", trims[0])
                     data['hd_trim'] = trims[0]
                     save_json_file(file, data)
                  else:
                     print("No trims found.") 
               else:
                  print("no hd_video_file variable either!", file)

            else:
               print("hd trim is good:", file)
         else:
               print("hd_trim is missing.", file)

def stack_non_meteors():
   files = glob.glob("/mnt/ams2/non_meteors/*.mp4")
   for file in files:
      stack_file = file.replace(".mp4", "-stacked.png")
      data_file = file.replace(".mp4", "-detect.json")
      if cfe(data_file) == 1:
         data = load_json_file(data_file)
      else:
         data = []
      print("STACK:", stack_file, data)
      #if cfe(stack_file) == 0:
      if True:
         frames,color_frames,subframes,sum_vals,max_vals,pos_vals = load_frames_fast(file, json_conf, 0, 0, [], 0,[])
         stacked_file, stacked_image = stack_frames(frames, file, 0)
         for obj in data:
            x1,y1,x2,y2 = minmax_xy(obj)
            cv2.rectangle(stacked_image, (x1, y1), (x2, y2), (255,255,255), 1, cv2.LINE_AA)
            desc = obj['report']['obj_class']
            cv2.putText(stacked_image, desc,  (x1,y1), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)


def batch_move():
   files = glob.glob("/mnt/ams2/CAMS/queue/*.mp4")
   for video_file in files:
      if "trim" in video_file:
         trim = 1
         stack_file = video_file.replace(".mp4", "-stacked.png")
      
      else:
         trim = 0
         stack_file = video_file.replace(".mp4", "-stacked.png")
         meteor_file = video_file.replace(".mp4", "-meteor.json")
         fail_file = video_file.replace(".mp4", "-fail.json")
      if cfe(stack_file) == 1 and trim != 1:
         # processing is done for this file
         video_fn = video_file.split("/")[-1]
         stack_fn = stack_file.split("/")[-1]
         meteor_fn = meteor_file.split("/")[-1]
         fail_fn = meteor_file.split("/")[-1]
         (hd_datetime, cam, sd_date, sd_y, sd_m, sd_d, sd_h, sd_M, sd_s) = convert_filename_to_date_cam(video_file)
         proc_dir = "/mnt/ams2/SD/proc2/" + sd_y + "_" + sd_m + "_" + sd_d + "/" 
         if cfe(proc_dir, 1) == 0 or cfe(proc_dir + "images", 1 ) == 0:
            os.system("mkdir " + proc_dir)
            os.system("mkdir " + proc_dir + "failed")
            os.system("mkdir " + proc_dir + "passed")
            os.system("mkdir " + proc_dir + "images")
            os.system("mkdir " + proc_dir + "data")
         if cfe(meteor_file) == 0:
            cmd = "mv " + video_file + " " + proc_dir
            print(cmd)
            os.system(cmd)
            cmd = "mv " + stack_file + " " + proc_dir + "images/"
            print(cmd)
            os.system(cmd)
            if cfe(fail_file) == 1:
               cmd = "mv " + fail_file + " " + proc_dir + "failed/"
               print(cmd)
               os.system(cmd)
            #cmd = "mv " + meteor_file + " " + proc_dir + "passed/"

def find_sun_alt(capture_date):

   device_lat = json_conf['site']['device_lat']
   device_lng = json_conf['site']['device_lng']

   obs = ephem.Observer()

   obs.pressure = 0
   obs.horizon = '-0:34'
   obs.lat = device_lat
   obs.lon = device_lng
   obs.date = capture_date

   sun = ephem.Sun()
   sun.compute(obs)

   (sun_alt, x,y) = str(sun.alt).split(":")

   saz = str(sun.az)
   (sun_az, x,y) = saz.split(":")
   if int(sun_alt) < -1:
      sun_status = "night"
   else:
      sun_status = "day"
   return(int(sun_alt))


def objects_to_clips(meteor_objects):
   clips = []
   good_objs = []
   for obj in meteor_objects:
      if len(obj['ofns']) > 2:
         ok = 1 
         for clip in clips:
            if abs(obj['ofns'][0] - clip) < 25:
               ok = 0
         if ok == 1:
            clips.append(obj['ofns'][0])
            good_objs.append(obj)
      
   return(good_objs)

def batch_confirm():
   files = glob.glob("/mnt/ams2/CAMS/queue/*meteor.json")
   for file in files:
      print(file)
      confirm_meteor(file)

def minmax_xy(obj):
   min_x = min(obj['oxs'])
   max_x = max(obj['oxs'])
   min_y = min(obj['oys'])
   max_y = max(obj['oys'])
   return(min_x, min_y, max_x, max_y)

def save_new_style_meteor_json (meteor_obj, trim_clip ):
   print("MO:", meteor_obj)
   print("FTIMES:", meteor_obj['ftimes'])
   print("OFNS:", meteor_obj['ofns'])
   mj = {}
   (hd_datetime, cam, sd_date, sd_y, sd_m, sd_d, sd_h, sd_M, sd_s) = convert_filename_to_date_cam(trim_clip)
   mj['calib'] = meteor_obj['calib']
   #mj['dt'] = meteor_obj['dt']
   #meteor_obj['dt'] = hd_datetime
   tc = trim_clip.split("/")[-1]
   mj['info'] = {}
   mj['info']['station'] = json_conf['site']['ams_id'].upper()
   #mj['info']['hd_vid'] = meteor_obj['ma_hd_file']
   #mj['info']['sd_vid'] = meteor_obj['ma_sd_file']
   #mj['info']['org_hd_vid'] = meteor_obj['orig_hd_vid']
   #mj['info']['org_sd_vid'] = meteor_obj['orig_sd_vid']
   mj['info']['device'] = cam
   if "report" in meteor_obj:
      mj['report'] = meteor_obj['report']
      mj['report']['max_peak'] = max(meteor_obj['oint'])
      mj['report']['dur'] = len(meteor_obj['ofns'])/ 25

   mj['frames'] = []
   used_fn = {}
   for i in range(0, len(meteor_obj['ofns'])):
      fd = {}
      fd['fn'] = meteor_obj['ofns'][i] 
      fd['x'] = meteor_obj['oxs'][i]
      fd['y'] = meteor_obj['oys'][i]
      fd['dt'] = meteor_obj['ftimes'][i]

      new_x, new_y, ra ,dec , az, el = XYtoRADec(fd['x'],fd['y'],trim_clip,meteor_obj['cal_params'],json_conf)
      print("AZ:EL", fd['x'], fd['y'], az, el, fd['dt'], meteor_obj['cal_params']['ra_center'], meteor_obj['cal_params']['dec_center']) 

      fd['az'] = az 
      fd['el'] = el
      fd['dec'] = dec
      fd['ra'] = ra 

      fd['w'] = meteor_obj['ows'][i]
      fd['h'] = meteor_obj['ohs'][i]
      fd['max_px'] = meteor_obj['oint'][i]
      if fd['fn'] not in used_fn:
         mj['frames'].append(fd)
      used_fn[fd['fn']] = 1
   mj['sync'] = {}
   mj['sync']['sd_ind'] = meteor_obj['ofns'][0]
   mj['sync']['hd_ind'] = meteor_obj['ofns'][0]
   #mj['sync']['sd_ind'] = sd_start_frame
   #mj['sync']['hd_ind'] = hd_start_frame
   
   print("NEW METEOR SAVE!")
   print(mj)
   return(mj)

def archive_path(old_file):
   ofn = old_file.split("/")[-1]
   station_id = json_conf['site']['ams_id']
   (hd_datetime, cam, sd_date, sd_y, sd_m, sd_d, sd_h, sd_M, sd_s) = convert_filename_to_date_cam(old_file)
   new_archive_file = METEOR_ARCHIVE + station_id + "/" + METEOR + "/" + sd_y + "/" + sd_m + "/" + sd_d + "/" + ofn
   return(new_archive_file)
   
   

def save_old_style_meteor_json(meteor_json_file, meteor_obj, trim_clip ):
   #old json object
   mfj = meteor_json_file.split("/")[-1]
   meteor_dir = meteor_json_file.replace(mfj, "")
   if "hd_trim" in meteor_obj:
      if meteor_obj['hd_trim'] != 0:
         if "/mnt/ams2/HD" in meteor_obj['hd_trim'] :
            print("FIX HD TRIM!")
            hdf = meteor_obj['hd_trim'].split("/")[-1]
            hd_trim = meteor_dir + hdf 
            print("HDF!", hdf, hd_trim)
         else:
            hd_trim = meteor_obj['hd_trim']
   else:
      print("No HD trim in obj", meteor_obj)
      meteor_obj['hd_trim'] = 0
      meteor_obj['hd_video_file'] = 0
      meteor_obj['hd_crop'] = 0
      hd_trim = 0
   oj = {}
   oj['sd_video_file'] = meteor_json_file.replace(".json", ".mp4")
   sd_stack = meteor_json_file.replace(".json", "-stacked.png")

   oj['sd_stack'] = sd_stack
   oj['hd_stack'] = sd_stack
   oj['hd_video_file'] = meteor_obj['hd_video_file']
   oj['hd_trim'] = hd_trim
   oj['hd_crop_file'] = 0
   oj['hd_box'] = [0,0,0,0]
   oj['hd_objects'] = []
   if "new_json_file" in meteor_obj:
      oj['archive_file'] = archive_path(meteor_obj['new_json_file'])

   # make SD objects from new meteor
   sd_objects = {}
   ofns = meteor_obj['ofns']
   oxs = meteor_obj['oxs']
   oys = meteor_obj['oys']
   ows = meteor_obj['ows']
   ohs = meteor_obj['ohs']
   hist = []
   for i in range (0, len(ofns)-1):
      fn = ofns[i]
      x = oxs[i]
      y = oys[i]
      w = ows[i]
      h = ohs[i]
      hist.append((fn,x,y,w,h,0,0))
   sd_objects['oid'] = 1
   sd_objects['fc'] = len(ofns)
   sd_objects['x'] = oxs[0]
   sd_objects['y'] = oys[0]
   sd_objects['w'] = max(ows)
   sd_objects['h'] = max(ohs)
   sd_objects['history'] = hist
      

   oj['sd_objects'] = [sd_objects]
   oj['status'] = "moving"
   oj['total_frames'] = len(ofns)
   oj['meteor'] = 1
   oj['test_results'] = []
   oj['hd_trim_dur'] = []
   oj['hd_trim_time_offset'] = []
   oj['flex_detect'] = meteor_obj
   save_json_file(meteor_json_file, oj)

def detect_meteor_in_clip(trim_clip, frames = None, fn = 0, crop_x = 0, crop_y = 0, hd_in = 0):
   objects = {}
   print("DETECT METEORS IN VIDEO FILE:", trim_clip)
   #if hd_in == 1:
   #   exit()
   (hd_datetime, cam, sd_date, sd_y, sd_m, sd_d, sd_h, sd_M, sd_s) = convert_filename_to_date_cam(trim_clip)
   masks = get_masks(cam, json_conf,0)

   if trim_clip is None: 
      return(objects, []) 

   if frames is None :
        
      frames,color_frames,subframes,sum_vals,max_vals,pos_vals = load_frames_fast(trim_clip, json_conf, 0, 1, [], 0,[])
   if len(frames) == 0:
      return(objects, []) 

   if frames[0].shape[1] == 1920 or hd_in == 1:
      hd = 1
      sd_multi = 1
   else:
      hd = 0
      sd_multi = 1920 / frames[0].shape[1]

   image_acc = frames[0]
   image_acc = np.float32(image_acc)

   for i in range(0,len(frames)):
      frame = frames[i]
      blur_frame = cv2.GaussianBlur(frame, (7, 7), 0)
      alpha = .5
      hello = cv2.accumulateWeighted(blur_frame, image_acc, alpha)

   # preload the bg
   for frame in frames:
      frame = np.float32(frame)
      blur_frame = cv2.GaussianBlur(frame, (7, 7), 0)
      alpha = .5


      image_diff = cv2.absdiff(image_acc.astype(frame.dtype), blur_frame,)
      hello = cv2.accumulateWeighted(blur_frame, image_acc, alpha)


   for frame in frames:
      show_frame = frame.copy()
      frame = np.float32(frame)
      blur_frame = cv2.GaussianBlur(frame, (7, 7), 0)
      alpha = .5


      image_diff = cv2.absdiff(image_acc.astype(frame.dtype), blur_frame,)
      hello = cv2.accumulateWeighted(blur_frame, image_acc, alpha)

      show_frame = frame.copy()
      avg_px = np.mean(image_diff)
      min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(image_diff)
      thresh = max_val - 10
      if thresh < 5:
         thresh = 5

      cnts,rects = find_contours_in_frame(image_diff, thresh)
      icnts = []
      if len(cnts) < 5 and fn > 0:
         for (cnt) in cnts:
            px_diff = 0
            x,y,w,h = cnt
            if w > 1 and h > 1:
               intensity,mx,my,cnt_img = compute_intensity(x,y,w,h,frame,frames[0])
               cx = int(mx) 
               cy = int(my) 
               cv2.circle(show_frame,(cx+crop_x,cy+crop_y), 10, (255,255,255), 1)
               #print("DETECT X,Y:", fn, crop_x, crop_y, cx,cy)
               masked = check_pt_in_mask(masks, cx+crop_x, cy+crop_y)
               if masked == 0:
                  object, objects = find_object(objects, fn,cx+crop_x, cy+crop_y, w, h, intensity, hd, sd_multi, cnt_img)
               #print("MIKE OBJECTS:", fn, cx,cy,w,h,intensity)
               #if len(objects[object]['ofns']) > 2:
                  #le_x, le_y = find_leading_edge(objects[object]['report']['x_dir_mod'], objects[object]['report']['y_dir_mod'],cx,cy,w,h,frame)

                  objects[object]['trim_clip'] = trim_clip
                  cv2.rectangle(show_frame, (x, y), (x+w, y+h), (255,255,255), 1, cv2.LINE_AA)
                  desc = str(fn) + " " + str(intensity) + " " + str(objects[object]['obj_id']) + " " + str(objects[object]['report']['obj_class']) #+ " " + str(objects[object]['report']['ang_vel'])
                  cv2.putText(show_frame, desc,  (x,y), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
      
      show_frame = cv2.convertScaleAbs(show_frame)
      show = 0
      if show == 1:
         cv2.imshow('Detect Meteor In Clip', show_frame)
         cv2.waitKey(30)
      fn = fn + 1

   #for obj in objects:
   #   objects[obj] = analyze_object(objects[obj], hd)
   #   print("VIDEO DETECT:", objects[obj])


   if show == 1:
      cv2.destroyAllWindows()

   return(objects, frames)   

def merge_cnts(cnts): 
   merge_cnts = []
   for (i,c) in enumerate(cnts):
      px_diff = 0
      x,y,w,h = cv2.boundingRect(cnts[i])
      if len(merge_cnts) == 0:
         merge_cnts.append((x,y,w,h))
         

def compute_intensity(x,y,w,h,frame, bg_frame):
   frame = np.float32(frame)
   bg_frame = np.float32(bg_frame)
   cnt = frame[y:y+h,x:x+w]
   size=max(w,h)
   min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(cnt)
   cx1,cy1,cx2,cy2 = bound_cnt(x+mx,y+my,frame.shape[1],frame.shape[0], size)
   cnt = frame[cy1:cy2,cx1:cx2]
   bgcnt = bg_frame[cy1:cy2,cx1:cx2]


   sub = cv2.subtract(cnt, bgcnt)
   min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(cnt)
   val = int(np.sum(sub))

   #print(cnt.shape)
   #show_image = cv2.convertScaleAbs(cnt)


   return(val,cx1+mx,cy1+my, cnt)

def reject_meteor(meteor_json_file):
   min_file = meteor_json_file.replace("-meteor.json", ".mp4")
   (hd_datetime, cam, sd_date, sd_y, sd_m, sd_d, sd_h, sd_M, sd_s) = convert_filename_to_date_cam(min_file)
   meteor_date = sd_y + "_" + sd_m + "_" + sd_d
   stack_file = meteor_json_file.replace("-meteor.json", "-stacked.png")
   proc_dir = "/mnt/ams2/SD/proc2/" + sd_y + "_" + sd_m + "_" + sd_d + "/"
   if cfe(proc_dir, 1) == 0:
      os.system("mkdir " + proc_dir)
      os.system("mkdir " + proc_dir + "images")
      os.system("mkdir " + proc_dir + "failed")
      os.system("mkdir " + proc_dir + "passed")
   
   cmd = "mv " + min_file + " " + proc_dir 
   print(cmd)
   os.system(cmd)

   cmd = "mv " + stack_file + " " + proc_dir + "images/"
   print(cmd)
   os.system(cmd)

   wild_card = meteor_json_file.replace("-meteor.json", "*")
   cmd = "mv " + wild_card + " /mnt/ams2/non_meteors/"
   print(cmd)
   os.system(cmd)

def get_cat_image_stars(cat_stars, frame,cal_params_file):
   show_frame = frame.copy()
   cat_image_stars = []
   used_istars = {}
   used_cstars = {}
   for cat_star in cat_stars:
      name,mag,ra,dec,new_cat_x,new_cat_y = cat_star
      cx1,cy1,cx2,cy2 = bound_cnt(new_cat_x,new_cat_y,frame.shape[1],frame.shape[0], 50)
      c_key = str(new_cat_x) + str(new_cat_y)

      pos_star = frame[cy1:cy2,cx1:cx2]
      min_val, max_val, min_loc, (ix,iy)= cv2.minMaxLoc(pos_star)
      if max_val - min_val > 20:
         cv2.rectangle(show_frame, (cx1,cy1), (cx2, cy2), (128, 128, 128), 1)

      cx1,cy1,cx2,cy2 = bound_cnt(cx1+ix,cy1+iy,frame.shape[1],frame.shape[0], 20)
      pos_star = frame[cy1:cy2,cx1:cx2]
      star_avg = np.median(pos_star)
      star_sum = np.sum(pos_star)
      star_int = star_sum - (star_avg * (pos_star.shape[0] * pos_star.shape[1]))

      min_val, max_val, min_loc, (ix,iy)= cv2.minMaxLoc(pos_star)
      ix = ix + cx1
      iy = iy + cy1
      px_diff = max_val - star_avg
      i_key = str(ix) + str(iy)

      if (new_cat_x < 10 or new_cat_x > 1910) or (new_cat_y < 10 or new_cat_y > 1070):
         star_int = 0
         px_diff = 0
      if mag >= 4 and star_int > 25000:
         bad =  1
      else:
         bad = 0

      if mag <= 3:
         cv2.circle(show_frame,(int(new_cat_x),int(new_cat_y)), 20, (128,128,128), 1)
      if star_int > 100 and px_diff > 15:
         dist = calc_dist((ix,iy),(new_cat_x,new_cat_y))
         cv2.line(show_frame, (ix,iy), (int(new_cat_x),int(new_cat_y)), (255), 2)
         #print("POS STAR:", name, star_int, px_diff, bad,dist)

      if star_int > 50 and px_diff > 10 and bad == 0:
         cv2.circle(show_frame,(int(ix),int(iy)), 5, (255,255,255), 1)
         px_dist = calc_dist((ix,iy), (new_cat_x, new_cat_y))
         #name #.decode("unicode_escape")
         if px_dist < 10 and i_key not in used_istars and c_key not in used_cstars:
            #cat_image_stars.append((name.decode("unicode_escape"),mag,ra,dec,new_cat_x,new_cat_y,ix,iy,star_int,px_dist,cal_params_file))
            cat_image_stars.append((name,mag,ra,dec,new_cat_x,new_cat_y,ix,iy,star_int,px_dist,cal_params_file))
            used_istars[i_key] = 1
            used_cstars[c_key] = 1
   if show == 1:
      cv2.imshow('cat_stars', show_frame)
      cv2.waitKey(70)
   return(cat_image_stars)



def format_calib(trim_clip, cal_params, cal_params_file):
   calib = {}
   tc = trim_clip.split("/")[-1]
   calib['dt'] = tc[0:23]
   calib['device'] = {}
   calib['device']['poly'] = {}
   calib['device']['poly']['x_fwd'] = cal_params['x_poly_fwd']
   calib['device']['poly']['y_fwd'] = cal_params['y_poly_fwd']
   calib['device']['poly']['x'] = cal_params['x_poly']
   calib['device']['poly']['y'] = cal_params['y_poly']
   calib['device']['center'] = {}
   calib['device']['center']['az'] = cal_params['center_az']
   calib['device']['center']['el'] = cal_params['center_el']
   calib['device']['center']['ra'] = cal_params['ra_center']
   calib['device']['center']['dec'] = cal_params['dec_center']
   calib['stars'] = []

   if "cat_image_stars" in cal_params:
      for data in cal_params['cat_image_stars']:
         print("DATA LEN:", len(data), data)
         if len(data) == 11:
            (name,mag,ra,dec,new_cat_x,new_cat_y,ix,iy,intensity,px_dist,cpfile) = data
         if len(data) == 10:
            (name,mag,ra,dec,new_cat_x,new_cat_y,ix,iy,px_dist,cpfile) = data
         if len(data) == 16:
            (name,mag,ra,dec,img_ra,img_dec,px_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,ix,iy,cat_dist) = data
     
         star = {}
         star['name'] = name
         star['mag'] = mag
         star['ra'] = ra
         star['dec'] = dec
         star['dist_px'] = px_dist
         if "intensity" in star:
            star['intensity'] = int(intensity)
         else:
            star['intensity'] = 0 
         star['i_pos'] = [int(ix),int(iy)]
         star['cat_dist_pos'] = [int(new_cat_x),int(new_cat_y)]
         star['cat_und_pos'] = [int(new_cat_x),int(new_cat_y)]
         calib['stars'].append(star)
         print("ADDING STAR:", star)

   calib['img_dim'] = [1920,1080]

   if 'device_lat' in cal_params:
      calib['device']['alt'] = cal_params['device_alt']
      calib['device']['lat'] = cal_params['device_lat']
      calib['device']['lng'] = cal_params['device_lng']
   else:
      calib['device']['alt'] = json_conf['site']['device_alt']
      calib['device']['lat'] = json_conf['site']['device_lat']
      calib['device']['lng'] = json_conf['site']['device_lng']
   calib['device']['angle'] = cal_params['position_angle']
   calib['device']['scale_px'] = cal_params['pixscale']
   calib['device']['org_file'] = cal_params_file

   if "total_res_px" in cal_params:
      print("SCALE:", calib['device']['scale_px'], cal_params['total_res_px'])
      calib['device']['total_res_px'] = cal_params['total_res_px']
      calib['device']['total_res_deg'] = (float(cal_params['total_res_px']) * float(calib['device']['scale_px'])) / 3600
   else:
      cal_params['total_res_px'] = 99
      calib['device']['total_res_px'] = 99
      calib['device']['total_res_deg'] = (float(cal_params['total_res_px']) * float(calib['device']['scale_px'])) / 3600

   return(calib)

def get_image_stars(file,img=None, show=0):
   stars = []
   if img is None:
      img = cv2.imread(file, 0)
   avg = np.mean(img)
   best_thresh = avg + 12
   _, star_bg = cv2.threshold(img, best_thresh, 255, cv2.THRESH_BINARY)
   thresh_obj = cv2.dilate(star_bg, None , iterations=4)
   (_, cnts, xx) = cv2.findContours(thresh_obj.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
   cc = 0
   for (i,c) in enumerate(cnts):
      x,y,w,h = cv2.boundingRect(cnts[i])
      px_val = int(img[y,x])
      cnt_img = img[y:y+h,x:x+w]
      cnt_img = cv2.GaussianBlur(cnt_img, (7, 7), 0)
      max_px, avg_px, px_diff,max_loc = eval_cnt(cnt_img.copy())
      name = "/mnt/ams2/tmp/cnt" + str(cc) + ".png"
      #star_test = test_star(cnt_img)
      x = x + int(w/2)
      y = y + int(h/2)
      if px_diff > 5 and w > 1 and h > 1 and w < 50 and h < 50:
          stars.append((x,y,int(max_px)))
          cv2.circle(img,(x,y), 5, (128,128,128), 1)

      cc = cc + 1
   #if show == 1:
   #   cv2.imshow('pepe', img)
   #   cv2.waitKey(1)

   temp = sorted(stars, key=lambda x: x[2], reverse=True)
   stars = temp[0:50]
   return(stars)

def find_best_cat_stars(cat_stars, ix,iy, frame, cp_file):
   cx1,cy1,cx2,cy2 = bound_cnt(ix,iy,frame.shape[1],frame.shape[0], 5)
   intensity = int(np.sum(frame[cy1:cy2,cx1:cx2]))
   min_dist = 999 
   min_star = None 
   for cat_star in cat_stars:
      name,mag,ra,dec,new_cat_x,new_cat_y = cat_star

      dist = calc_dist((new_cat_x, new_cat_y), (ix,iy))
      if dist < min_dist and mag < 4:
         min_dist = dist
         min_star = cat_star
   name,mag,ra,dec,new_cat_x,new_cat_y = min_star
   px_dist = 0
   #cat_image_star = ((name.decode("unicode_escape"),mag,ra,dec,new_cat_x,new_cat_y,ix,iy,intensity,min_dist,cp_file))
   cat_image_star = ((name,mag,ra,dec,new_cat_x,new_cat_y,ix,iy,intensity,min_dist,cp_file))
   return(cat_image_star)

   

def refit_arc_meteor(archive_file):
   (cp_datetime, cam, sd_date, sd_y, sd_m, sd_d, sd_h, sd_M, sd_s) = convert_filename_to_date_cam(archive_file)
   station = json_conf['site']['ams_id']
   show = 0
   max_err = 50
   am = load_json_file(archive_file)
   hd_vid = am['info']['hd_vid']
   calib = am['calib']
   cal_params = load_cal_params_from_arc(calib)
  
   #master_lens_file = "/mnt/ams2/meteor_archive/" + station + "/CAL/master_lens_model/master_cal_file_" + cam + ".json"

   #if cfe(master_lens_file) == 1:
   #   print("Using master lens file")
   #   mld = load_json_file(master_lens_file)
   #   cal_params['x_poly'] = mld['x_poly']
   #   cal_params['y_poly'] = mld['y_poly']
   #   cal_params['y_poly_fwd'] = mld['y_poly_fwd']
   #   cal_params['x_poly_fwd'] = mld['x_poly_fwd']

   cat_stars = flex_get_cat_stars(archive_file, archive_file, json_conf, cal_params )

   hd_frames,hd_color_frames,hd_subframes,sum_vals,max_vals,pos_vals = load_frames_fast(hd_vid, json_conf, 0, 0, [], 1,[])
   frame = hd_frames[0]
   cframe = hd_color_frames[0]

   image_stars = get_image_stars(archive_file,frame, show=1)
   cat_image_stars = [] 

   res_err = []
   for star in image_stars:
      print("STAR:", star)
      best_star = find_best_cat_stars(cat_stars, star[0], star[1], frame, archive_file)
      if best_star[9] < max_err :
         res_err.append(best_star[9])

   std_err = float(np.std(res_err))
   med_err = float(np.median(res_err))
   print("MED ERR / STD DEV:", med_err, std_err)
   ac_err = med_err + std_err 

   for star in image_stars:
      #print("STAR:", star)
      best_star = find_best_cat_stars(cat_stars, star[0], star[1], frame, archive_file)
      #print("BEST:", best_star)
      if best_star[9] <  ac_err * 1.1:
         cv2.line(frame, (star[0], star[1]), (int(best_star[4]), int(best_star[5])), (128,128,128), 1) 
         cat_image_stars.append(best_star)
   if show == 1:
      cv2.imshow('pepe', frame)
      cv2.waitKey(70)

   this_poly = np.zeros(shape=(4,), dtype=np.float64)
   cal_params['cat_image_stars'] = cat_image_stars
   tries = 0 
   res = scipy.optimize.minimize(reduce_fov_pos, this_poly, args=( cal_params,archive_file,frame,json_conf, cat_image_stars,1,show), method='Nelder-Mead')
   print(res)
   fov_pos_poly = res['x']
   fov_pos_fun = res['fun']
   cal_params['x_poly'] = calib['device']['poly']['x']
   cal_params['y_poly'] = calib['device']['poly']['y']
   cal_params['fov_pos_poly'] = fov_pos_poly.tolist()
   cal_params['fov_pos_fun'] = fov_pos_fun

   cal_params['center_az'] = float(cal_params['orig_az_center']) + float(fov_pos_poly[0] )
   cal_params['center_el'] = float(cal_params['orig_el_center']) + float(fov_pos_poly[1] )
   cal_params['position_angle'] = float(cal_params['position_angle']) + float(fov_pos_poly[2] )
   cal_params['pixscale'] = float(cal_params['orig_pixscale']) + float(fov_pos_poly[3] )
   cal_params['orig_pos_angle'] = float(cal_params['position_angle']) + float(fov_pos_poly[2] )
   cal_params['orig_pixscale'] = float(cal_params['orig_pixscale']) + float(fov_pos_poly[3] )

   fov_pos_poly = np.zeros(shape=(4,), dtype=np.float64)
   final_res = reduce_fov_pos(fov_pos_poly, cal_params,archive_file,frame,json_conf, cat_image_stars,0,show)
   cal_params['total_res_px'] = final_res
   print("FINAL RES:", final_res)


   rah,dech = AzEltoRADec(cal_params['center_az'],cal_params['center_el'],archive_file,cal_params,json_conf)
   rah = str(rah).replace(":", " ")
   dech = str(dech).replace(":", " ")
   ra_center,dec_center = HMS2deg(str(rah),str(dech))
   cal_params['ra_center'] = ra_center
   cal_params['dec_center'] = dec_center
   cal_params['fov_fit'] = 1
   calib = format_calib(archive_file, cal_params, archive_file)
   am['calib'] = calib
   save_json_file(archive_file, am)
   print(archive_file)


   
def load_cal_params_from_arc(calib):
   print(calib)
   cal_params = {}
   cal_params['device_lat'] = calib['device']['lat']
   cal_params['device_lng'] = calib['device']['lng']
   cal_params['device_alt'] = calib['device']['alt']
   cal_params['orig_ra_center'] = calib['device']['center']['ra']
   cal_params['orig_dec_center'] = calib['device']['center']['dec']
   cal_params['orig_az_center'] = calib['device']['center']['az']
   cal_params['orig_el_center'] = calib['device']['center']['el']
   cal_params['orig_pos_ang'] = calib['device']['angle']
   cal_params['orig_pixscale'] = calib['device']['scale_px']
   cal_params['ra_center'] = calib['device']['center']['ra']
   cal_params['dec_center'] = calib['device']['center']['dec']
   cal_params['az_center'] = calib['device']['center']['az']
   cal_params['el_center'] = calib['device']['center']['el']
   cal_params['center_az'] = calib['device']['center']['az']
   cal_params['center_el'] = calib['device']['center']['el']
   cal_params['position_angle'] = calib['device']['angle']
   cal_params['pixscale'] = calib['device']['scale_px']
   cal_params['imagew'] = calib['img_dim'][0]
   cal_params['imageh'] = calib['img_dim'][1]

   cal_params['pixscale'] = calib['device']['scale_px']
   cal_params['x_poly'] = calib['device']['poly']['x']
   cal_params['y_poly'] = calib['device']['poly']['y']
   cal_params['x_poly_fwd'] = calib['device']['poly']['x_fwd']
   cal_params['y_poly_fwd'] = calib['device']['poly']['y_fwd']
   return(cal_params)


def apply_calib(obj , frames=None , user_station = None):
   if user_station is not None:
      remote_conf_file = "/mnt/archive.allsky.tv/" + user_station + "/CAL/as6.json"
      json_conf = load_json_file(remote_conf_file)
   else:
      json_conf = load_json_file("../conf/as6.json")


   if frames is None:
      if 'hd_trim' not in obj:
         print("ERROR:", obj)
         exit()
      if obj['hd_trim'] != 0:
         if cfe(obj['hd_trim']) == 1:   
            hd_frames,hd_color_frames,hd_subframes,sum_vals,max_vals,pos_vals = load_frames_fast(obj['hd_trim'], json_conf, 5, 0, [], 0,[])
            print("HD FRAMES:", len(hd_frames))
         elif "/mnt/ams2/HD/" in obj['hd_trim']:
            fl = obj['hd_trim'].split("/")[-1]
            m_date = fl[0:10]
            print("NEED TO UPDATE THE FILE PLEASE!", m_date, fl)
            obj['hd_trim'] = obj['hd_trim'].replace("/mnt/ams2/HD/", "/mnt/ams2/meteors/" + m_date + "/" )
            hd_frames,hd_color_frames,hd_subframes,sum_vals,max_vals,pos_vals = load_frames_fast(obj['hd_trim'], json_conf, 5, 0, [], 0,[])
      else:
         hd_frames,hd_color_frames,hd_subframes,sum_vals,max_vals,pos_vals = load_frames_fast(obj['trim_clip'], json_conf, 5, 0, [], 0,[])
         print("SD FRAMES:", len(hd_frames))
      frames = hd_frames

   frame = frames[0]
   frame = cv2.resize(frame, (1920,1080))

   # find best free cal files
   best_cal_files = get_best_cal_file(obj['trim_clip'], user_station)
   if best_cal_files is not None : 
      cal_params_file = best_cal_files[0][0]
   else:
      # use dummy cal file
      cal_params_file = "/home/ams/amscams/conf/2019_07_28_02_49_48_000_010004-stacked-calparams.json"
   (cp_datetime, cam, sd_date, sd_y, sd_m, sd_d, sd_h, sd_M, sd_s) = convert_filename_to_date_cam(cal_params_file)

   # find last_best_calib
   last_best_calibs = find_last_best_calib(obj['hd_trim'])
   print("Last Best Calib:", last_best_calibs)
   if len(last_best_calibs) > 0:
      (lp_datetime, cam, sd_date, sd_y, sd_m, sd_d, sd_h, sd_M, sd_s) = convert_filename_to_date_cam(last_best_calibs[0][0])
      (hd_datetime, cam, sd_date, sd_y, sd_m, sd_d, sd_h, sd_M, sd_s) = convert_filename_to_date_cam(obj['hd_trim'])
      delta1 = hd_datetime - lp_datetime
      delta2 = hd_datetime - cp_datetime
      if lp_datetime < cp_datetime:
         print("USE LAST BEST INSTEAD!")
         calib = load_json_file(last_best_calibs[0][0])
         calib['stars'] = []
         cal_params = calib_to_calparams(calib, obj['hd_trim'])
      else:
         print("USE STANDARD CALL!")
         cal_params = load_json_file(cal_params_file)
   else:
      cal_params = load_json_file(cal_params_file)
      print("USING LAST FREE CALIB!", cal_params_file)

   cal_params['device_lat'] = json_conf['site']['device_lat']
   cal_params['device_lng'] = json_conf['site']['device_lng']
   cal_params['device_alt'] = json_conf['site']['device_alt']
   cal_params['orig_ra_center'] = cal_params['ra_center']
   cal_params['orig_dec_center'] = cal_params['dec_center']

   cal_params['orig_az_center'] = cal_params['center_az']
   cal_params['orig_el_center'] = cal_params['center_el']
   cal_params['orig_pos_ang'] = cal_params['position_angle']
   cal_params['orig_pixscale'] = cal_params['pixscale']
   cal_params['cat_image_stars'] = []

   cat_stars = flex_get_cat_stars(obj['trim_clip'], cal_params_file, json_conf, cal_params )
   #cat_image_stars = get_cat_image_stars(cat_stars, frame, cal_params_file)
   archive_file = obj['hd_trim']
   try: 
      image_stars = get_image_stars(archive_file,frame, show=1)
   except :
      image_stars = []
   cat_image_stars = [] 
   calib_stars = [] 
   used_cat_stars = {}
   used_img_stars = {}
   for star in image_stars:
      print("STAR:", star)
      best_star = find_best_cat_stars(cat_stars, star[0], star[1], frame, archive_file)
      print("BEST:", best_star)
      istar_key = str(star[0]) + str(star[1])
      cstar_key = str(best_star[4]) + str(best_star[5])
      if istar_key not in used_img_stars and cstar_key not in used_cat_stars:
         cv2.line(frame, (star[0], star[1]), (int(best_star[4]), int(best_star[5])), (128,128,128), 1) 
         calib_star = {}
         cat_image_stars.append(best_star)
         used_img_stars[istar_key] = 1
         used_cat_stars[cstar_key] = 1



   if len(cat_image_stars) > 9999:
      this_poly = np.zeros(shape=(4,), dtype=np.float64)

      start_res = reduce_fov_pos(this_poly, cal_params, obj['hd_trim'],frame,json_conf, cat_image_stars,0,show)
      cal_params_orig = cal_params.copy()
      res = scipy.optimize.minimize(reduce_fov_pos, this_poly, args=( cal_params,obj['hd_trim'],frame,json_conf, cat_image_stars,1,show), method='Nelder-Mead')

      fov_pos_poly = res['x']
      fov_pos_fun = res['fun']
      cal_params['x_poly'] = cal_params_orig['x_poly']
      cal_params['y_poly'] = cal_params_orig['y_poly']
      final_res = reduce_fov_pos(fov_pos_poly, cal_params,obj['hd_trim'],frame,json_conf, cat_image_stars,0,show)
      print("FINAL RES:", final_res)
      cal_params['fov_pos_poly'] = fov_pos_poly.tolist()
      cal_params['fov_pos_fun'] = fov_pos_fun
      cal_params['total_res_px'] = final_res

      cal_params['center_az'] = float(cal_params['orig_az_center']) + float(fov_pos_poly[0] )
      cal_params['center_el'] = float(cal_params['orig_el_center']) + float(fov_pos_poly[1] )
      cal_params['position_angle'] = float(cal_params['position_angle']) + float(fov_pos_poly[2] )

      rah,dech = AzEltoRADec(cal_params['center_az'],cal_params['center_el'],obj['hd_trim'],cal_params,json_conf)
      rah = str(rah).replace(":", " ")
      dech = str(dech).replace(":", " ")
      ra_center,dec_center = HMS2deg(str(rah),str(dech))
      cal_params['ra_center'] = ra_center
      cal_params['dec_center'] = dec_center
      cal_params['fov_fit'] = 1
      close_stars = []

      cat_image_stars = get_cat_image_stars(cat_stars, frame,cal_params_file)

   cal_params['cat_image_stars'] = cat_image_stars

   calib = format_calib(obj['trim_clip'], cal_params, cal_params_file)
   print("CALIB:", calib)
   if len(calib['stars']) > 15 and cal_params['total_res_px'] < 2.4:
      last_best = calib.copy()
      del last_best['stars']
      json_file = obj['trim_clip'].replace(".mp4", ".json")
      lbf = json_file.split("/")[-1]
      station_id = json_conf['site']['ams_id']
      last_best_file = "/mnt/ams2/meteor_archive/" + station_id + "/CAL/last_best/" + lbf 
      last_best_file = last_best_file.replace("-SD", "")
      print("SAVING LAST BEST CALIB.",last_best_file)
      save_json_file(last_best_file, last_best)

   
   return(calib, cal_params)

def calib_to_calparams(calib, json_file ):
   cal_params = {}
   cal_params['x_poly'] = calib['device']['poly']['x'] 
   cal_params['y_poly'] = calib['device']['poly']['y'] 
   cal_params['y_poly_fwd'] = calib['device']['poly']['y_fwd'] 
   cal_params['x_poly_fwd'] = calib['device']['poly']['x_fwd'] 
   cal_params['center_ra'] = calib['device']['center']['ra'] 
   cal_params['center_dec'] = calib['device']['center']['dec'] 
   cal_params['ra_center'] = calib['device']['center']['ra'] 
   cal_params['dec_center'] = calib['device']['center']['dec'] 
   cal_params['center_az'] = calib['device']['center']['az'] 
   cal_params['center_el'] = calib['device']['center']['el'] 
   cal_params['pixscale'] = calib['device']['scale_px']
   cal_params['orig_pixscale'] = calib['device']['scale_px']
   cal_params['orig_pos_ang'] = calib['device']['angle']
   cal_params['orig_center_az'] = calib['device']['center']['az'] 
   cal_params['orig_center_el'] = calib['device']['center']['el'] 
   cal_params['orig_az_center'] = calib['device']['center']['az'] 
   cal_params['orig_el_center'] = calib['device']['center']['el'] 
   cal_params['position_angle'] = calib['device']['angle']
   if "img_dim" not in calib:
      calib['img_dim'] = [1920,1080]
   cal_params['imagew'] = calib['img_dim'][0]
   cal_params['imageh'] = calib['img_dim'][1]
   cat_image_stars = []

   if "stars" in calib:
      for star in calib['stars']:
         if "intensity" not in star:
            star['intensity'] = 0
         cat_star = (star['name'],star['mag'],star['ra'],star['dec'],star['cat_und_pos'][0],star['cat_und_pos'][1],star['i_pos'][0],star['i_pos'][1],star['intensity'], star['dist_px'],json_file)
         cat_image_stars.append(cat_star)
   else:
      calib['stars'] = [] 
   cal_params['cat_image_stars'] = cat_image_stars
   return(cal_params)

def batch_fit_all_arc_files():
   station_id = json_conf['site']['ams_id']
   os.system("find /mnt/ams2/meteor_archive/" + station_id + "/METEOR/ | grep .json |grep trim > /mnt/ams2/tmp/arc_files.txt")
   fp = open("/mnt/ams2/tmp/arc_files.txt", "r")
   for line in fp:
      line = line.replace("\n", "")
      fit_arc_file(line)
      os.system("cd /home/ams/amscams/pythonv2/; /usr/bin/python3 Apply_calib.py " + line)

def batch_fit_arc_file(date):
   year, mon, day = date.split("_")
   files = glob.glob("/mnt/ams2/meteor_archive/" + json_conf['site']['ams_id'] + "/METEOR/" + year + "/" + mon + "/" + day + "/*.json" )
   for file in files:
      js = load_json_file(file)
      if "stars" in js:
         if len(stars) > 0:
            cmd = "./flex-detect.py faf " + file
         else:
            cmd = "./flex-detect.py ram " + file
            print(cmd)
            os.system(cmd)
            cmd = "./flex-detect.py faf " + file
      else:
         cmd = "./flex-detect.py ram " + file
         print(cmd)
         os.system(cmd)
         cmd = "./flex-detect.py faf " + file

      print(cmd)
      os.system(cmd)

def remove_bad_stars(stars):
   new_stars = []
   err = []
   for star in stars:
      print(star)
      err.append(star['dist_px'])

   avg_err = np.mean(err)
   med_err = np.median(err)
   print("AVG STAR ERR:", avg_err)
   print("MEDIAN STAR ERR:", med_err)
   for star in stars:
      if star['dist_px'] < med_err * 7 or star['dist_px'] < 2:
         new_stars.append(star)
   return(new_stars)

def update_intensity(json_file):
   cnt_file = json_file.replace(".json", "-lc-cnt.png")
   ff_file = json_file.replace(".json", "-lc-ff.png")
   data = load_json_file(json_file)
   hd_file = json_file.replace(".json", "-HD.mp4")
   hd_frames,hd_color_frames,hd_subframes,sum_vals,max_vals,pos_vals = load_frames_fast(hd_file, json_conf, 0, 0, [], 0,[])
    

   sync = data['sync']['hd_ind'] - data['sync']['sd_ind']
   frames = data['frames']
   curve = {}
   fx = frames[0]['x']
   fy = frames[0]['y']
   cx1,cy1,cx2,cy2 = bound_cnt(fx,fy,hd_frames[0].shape[1],hd_frames[0].shape[0], 20)
   print(cx1,cy1,cx2,cy2)
   bg_cnt = hd_frames[0][cy1:cy2,cx1:cx2] 

   bg_int = []
   for i in range(0, len(hd_frames)):
      curve[i] = {}
      curve[i]['cnt_int'] = np.sum(bg_cnt)
      ff_sub = cv2.subtract(hd_frames[i],hd_frames[0])
      ff_int = np.sum(ff_sub) 
      bg_int.append(ff_int)


   for i in range(0, len(hd_frames)):
      curve[i]['ff_int'] = 0 
      curve[i]['cnt_int'] = 0

   ffs= []
   cnts= []
   new_frames = []
   for frame in frames:   
      fn = frame['fn'] + sync
      x = frame['x']
      y = frame['y']
      cx1,cy1,cx2,cy2 = bound_cnt(x,y,hd_frames[0].shape[1],hd_frames[0].shape[0], 20)
      print(fn, cy1,cy2,cx1,cx2)
      cnt = hd_frames[fn][cy1:cy2,cx1:cx2] 
      bg_cnt = hd_frames[0][cy1:cy2,cx1:cx2] 
      cnt_sub = cv2.subtract(cnt,bg_cnt)
      cnt_int = np.sum(cnt) - np.sum(bg_cnt)
      ff_sub = cv2.subtract(hd_frames[fn],hd_frames[0])
      ff_int = np.sum(ff_sub) 
      if cnt_int > 18446744073709:
         cnt_int = 0
      if ff_int > 18446744073709:
         ff_int = 0

      frame['intensity'] = int(cnt_int)
      frame['intensity_ff'] = int(ff_int)
      curve[fn]['cnt_int'] = cnt_int
      curve[fn]['ff_int'] = ff_int
      ffs.append(ff_int)
      cnts.append(cnt_int)
      new_frames.append(frame)

   data['frames'] = new_frames 
   save_json_file(json_file,data)
   print("Saved:", json_file)
   mf = max(ffs)
   mc = max(cnts)
   medf = np.median(ffs)
   medc = np.median(cnts)
   scale = mf / mc

   times = []
   values = []
   values2 = []
   for fn in curve:
      times.append(fn)
      values.append(curve[fn]['cnt_int'] )
      values2.append(curve[fn]['ff_int'] / scale)
      print(fn, curve[fn])     

   #plot_int(times,values, None,0,len(values), "Contour Intensity " , cnt_file)
   #plot_int(times,values2, None,0,len(values), "Full Frame Intensity", ff_file )
   print(cnt_file)
   print(ff_file)

def find_bad_line_points(xs,ys):

   fits_when_removed = []
   doesnt_fit_when_removed = []

   for i in range(0,len(xs)):
      temp_xs = xs.copy()
      temp_ys = ys.copy()
      temp_xs.pop(i)
      temp_ys.pop(i)
      (dist_to_line, z, med_dist) = poly_fit_check(temp_xs,temp_ys, xs[i],ys[i])
      if float(med_dist) < 5:
         print("FIT!", med_dist)
         fits_when_removed.append(i)   
      else:
         print("NO FIT!", med_dist)
         doesnt_fit_when_removed.append(i)   
      print(i, "INFO:", dist_to_line, med_dist)

   print("The line fits when these frames are removed:", fits_when_removed)   
   print("The doesn't fit when these frames are removed:", doesnt_fit_when_removed)   

def find_point_on_line(p1, p2, p3):
   x1, y1 = p1
   x2, y2 = p2
   x3, y3 = p3
   dx, dy = x2-x1, y2-y1
   det = dx*dx + dy*dy
   a = (dy*(y3-y1)+dx*(x3-x1))/det
   return x1+a*dx, y1+a*dy   

def plot_points(frames):
   print("PLOT POINTS!", frames)

   import matplotlib
   import matplotlib.pyplot as plt
   xs = []
   ys = []
   dists = []
   x_dists = []
   y_dists = []
   last_x = None
   ps, new_frames = calc_score(frames)
   for frame in new_frames:
      xs.append(frame['x'])
      ys.append(frame['y'])
      dists.append(frame['dist_from_last'])
      if last_x is not None:
         x_dists.append(frame['x'] - last_x)
         y_dists.append(frame['y'] - last_y)
      last_x = frame['x']
      last_y = frame['y']
   poly_x = np.array(xs)
   poly_y = np.array(ys)

   med_dist = np.median(dists)
   med_x_dist = np.median(x_dists)
   med_y_dist = np.median(y_dists)
 
   if len(y_dists) > 30:
      third = int(len(y_dists) / 3)
      med_y_dist1 = np.median(y_dists[0:third])
      med_y_dist2 = np.median(y_dists[third:third*2])
      med_y_dist3 = np.median(y_dists[third*3:-1])
      print("*****")
      print("MED Y DISTS:", med_y_dist1, med_y_dist2,med_y_dist3)

   # First check if these points can fit a line or not. If not there must be a bad point(s) in there.
   (dist_to_line, z, med_dist) = poly_fit_check(xs,ys, xs[0],ys[0])
   if med_dist > 2:
      print("This line can't be plotted!, There must be a bad frame somwhere")
      bad_frames = find_bad_line_points(xs,ys)
      print("BAD FRAMES:", bad_frames)
      #return(0)

   if len(poly_x) > 3:
      try:
         z = np.polyfit(poly_x,poly_y,1)
         f = np.poly1d(z)
      except:
         print("FAILED PLOTTING! not enough frames?")
         return(0)
   
   else:
      return(0)


   new_ys = []
   new_xs = []
   est_ys = []
   est_xs = []
   l_ys = []
   l_xs = []
 

   ls_x = poly_x[0] 
   ls_y = int(f(ls_x))
   le_x = poly_x[-1] 
   le_y = int(f(le_x))


   cc = 0
   first_x = poly_x[0]
   last_x = None
   last_y = None
   for i in range(0,len(poly_x)):
      #plt.plot(i, f(i), 'go')
      ox = poly_x[i]
      oy = poly_y[i]
      x = poly_x[i]
      y = int(f(x))
      if i > 0:
         est_x = poly_x[i-1] + med_x_dist
      else:
         est_x = x
      est_y = int(f(est_x))
      # align y / vert distance with last frame
      y_fixed = 0
      med_y_dist = np.median(y_dists)
      if i - 10 > 0:
         #med_y_dist = np.median(y_dists[i-10:i])
         med_y_dist = np.median(y_dists[i-10:i])

      if last_x is not None:
         if abs(oy - last_y) > abs(med_y_dist) * 1:
            adj_y = last_y + float(med_y_dist)
            #print("ALIGN Y:", last_y, oy, adj_y, med_y_dist)
            oy = adj_y
            y_fixed = 1
         else:
            adj_y = oy
      else:
         adj_y = oy

      lx,ly = find_point_on_line((ls_x,ls_y),(le_x,le_y),(ox,adj_y))
      l_xs.append(lx)
      l_ys.append(ly)
      new_ys.append(int(f(x)))
      new_xs.append(x)
      est_xs.append(est_x)
      est_ys.append(est_y)
      cc = cc + 1
      last_x = ox
      if y_fixed == 1:
         last_y = adj_y
      else:
         last_y = oy
   show = 0
   if show == 1:
      plt.plot(poly_x, poly_y, 'x')
      plt.plot(np.array(l_xs), np.array(l_ys), 'bs')
      plt.axis('equal')
      trendpoly = np.poly1d(z)
      plt.plot(poly_x,trendpoly(poly_x))
      ax = plt.gca()
      ax.invert_yaxis()
      plt.show()

   return(l_xs,l_ys)

def find_best_thresh(image ) :
   min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(image)
   avg_val = np.mean(image)
   px_diff = max_val - avg_val
   thresh = avg_val + (px_diff * .5)
   othresh = thresh
  
   cnts,rects = find_contours_in_frame(image, thresh)
   if len(cnts) == 1 and cnts[0][2] != image.shape[1] and cnts[0][2] > 1 and cnts[0][3] > 1:
      return(thresh)
   for i in range(0, int(px_diff)):
      thresh = max_val - i

      cnts,rects = find_contours_in_frame(image, thresh-10)
      print("BEST THRESH:", thresh, cnts)
      if len(cnts) == 1 and cnts[0][2] != image.shape[1]:
         return(thresh)
   return(othresh)

def center_cnt(image, x_dir_mod, y_dir_mod, dom):
   print("CENTER CNT!")
   min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(image)
   avg_val = np.mean(image)
   px_diff = max_val - avg_val
   #thresh = int(avg_val + (px_diff * .25))
   thresh = find_best_thresh(image)
   adj_x = 0
   adj_y = 0
   lcx = None

   #blur_cnt= cv2.GaussianBlur(image, (7, 7), 0)
   cnts,rects = find_contours_in_frame(image, thresh)

   print("CNTS:", cnts)
   if len(cnts) == 0:
      thresh = thresh - 10
      cnts,rects = find_contours_in_frame(image, thresh)
      print("CNTS 2nd try:", len(cnts), cnts)
      if len(cnts) == 0:
         print("NO CNT FOUND")
         cnts = [[200,200,5,5]]
         found = 0
      else:
         x,y,w,h = cnts[0]
         lcx,lcy = find_leading_corner(x,y,w,h,x_dir_mod,y_dir_mod,dom)
         cv2.rectangle(image, (x, y), (x+w, y+h), (255,255,255), 1, cv2.LINE_AA)
         cv2.circle(image,(lcx,lcy), 10, (0,255,0), 2)
   elif len(cnts) == 1:
      x,y,w,h = cnts[0]
      cv2.rectangle(image, (x, y), (x+w, y+h), (255,255,255), 1, cv2.LINE_AA)
      lcx,lcy = find_leading_corner(x,y,w,h,x_dir_mod,y_dir_mod,dom)
      cv2.circle(image,(lcx,lcy), 10, (0,255,0), 2)
   else:
      print("MANY CNTS:", len(cnts))
      cnt = find_best_cnt(cnts, x_dir_mod,y_dir_mod)
      x,y,w,h = cnt[0]
      cv2.rectangle(image, (x, y), (x+w, y+h), (255,255,255), 1, cv2.LINE_AA)
      lcx,lcy = find_leading_corner(x,y,w,h,x_dir_mod,y_dir_mod,dom)
      cv2.circle(image,(lcx,lcy), 10, (0,255,0), 2)

   if lcx is not None:
      adj_x = 200 - lcx - (int(w/2) * x_dir_mod)
      adj_y = 200 - lcy 
   else:
      print("NO ADJ X!")

   #cv2.imshow('pepe', image)
   #cv2.waitKey(0)

   return(adj_x,adj_y)

def find_leading_corner(x,y,w,h,x_dir_mod,y_dir_mod,dom):
   if y_dir_mod == -1:
      ly = y + h 
   else:
      ly = y
   if x_dir_mod == -1:
      lx = x + w 
   else:
      lx = x 
   return(lx,ly)   

def reduce_point_error(this_poly, frames, type):
   global tries
   errs = []
   # get line info
   x_dir_mod,y_dir_mod = meteor_dir(frames[0]['x'], frames[0]['y'], frames[-1]['x'], frames[-1]['y'])
   dom,z,med_dist,med_seg,mxd,myd = line_info(frames) 
   print("MXD:", mxd)
   print("MYD:", myd)
   i = 0
   last_x = None
   last_y = None
   xs = []
   ys = []
   for frame in frames:
      x = frame['x']
      y = frame['y']
      xs.append(x)
      ys.append(x)
   i = 0
   for frame in frames:
      if this_poly[i] > 5 :
         this_poly[i] =  5

      if this_poly[i] < -5:
         this_poly[i] = -5 
   
      x = frame['x']
      y = frame['y']
      fn = frame['fn']
      if type == 'x':
         x = x + this_poly[i] 
              
         if last_x is not None:

            (dist_to_line, z, med_dist) = poly_fit_check(xs,ys, x,ys[i])

            err = abs((x-last_x) - abs(mxd) ) + (dist_to_line*0)
            err = dist_to_line
            #print("ERR:",  abs(x-last_x) , abs(mxd),dist_to_line, err) 
            if fn == 28:
               print("FRAME X:", fn, x)
            errs.append(err)
             
      else:
         y = y + this_poly[i] 
         (dist_to_line, z, med_dist) = poly_fit_check(xs,ys, xs[i],y)
         if last_y is not None:
            err = abs((y-last_y) - abs(myd)) + (dist_to_line*0)
            err = dist_to_line
            errs.append(err)
      last_x = x 
      last_y = y
      i =i + 1
   print(type, tries, "RES ERR:", np.mean(errs))
 
   return(np.mean(errs))
      
def reduce_one_point_error(this_poly, frames, mfn):
   err = 0
   new_frames = []
   for frame in frames:
      if frame['fn'] == mfn:
         mx = frame['x'] + (this_poly[0]*1000)
         my = frame['y'] + (this_poly[1]*1000)
         frame['x'] = int(mx)
         frame['y'] = int(my)
      new_frames.append(frame)
   ps, new_frames = calc_score(new_frames)
   print("RES: ", ps)
   return(ps)

def minimize_one_point_error(frames,mfn):

   ps_old, new_frames = calc_score(frames)
   print("SCORE ORIG:", ps_old)
   this_poly = np.zeros(shape=(2,), dtype=np.float64)
   scipy.optimize.Bounds(-5,5)
   res = scipy.optimize.minimize(reduce_one_point_error, this_poly, args=( frames, mfn), method='Nelder-Mead')
   this_poly = res['x'].tolist()
   print("XY ADJ:", this_poly)
   return(this_poly)

def minimize_point_error(frames):

   global tries
   tries = 0
   new_frames = []
   fixes = []
   for frame in frames:
      fn = frame['fn']
      fx,fy = minimize_one_point_error(frames,fn)
      fx = int(fx * 1000)
      fy = int(fy * 1000)
      print("FIX:", fn,int(fx),int(fy))
      fixes.append((fx,fy))
   for fx,fy in fixes:
      print(fx,fy)
   exit()
   #res = plot_points(new_frames)
   return(new_frames)

def eval_points(json_file, frames=None, save=1):
   jd = load_json_file(json_file)
   if frames is None:
      frames = jd['frames']

   ps_old, new_frames = calc_score(frames)
   print("ORIG P SCORE:", ps_old)
   #new_frames = minimize_point_error(frames)
   ps_new, new_frames = calc_score(frames)
   print("OLD P SCORE:", ps_old)
   print("NEW P SCORE:", ps_new)


   x_dir_mod,y_dir_mod = meteor_dir(frames[0]['x'], frames[0]['y'], frames[-1]['x'], frames[-1]['y'])
   dom,z,med_dist,med_seg,mxd,myd = line_info(frames) 
   ps_new, new_frames = calc_score(new_frames)
   print("OLD/NEW SCORE:", ps_old, ps_new)
   jd['report']['point_score'] = ps_new 
   jd['frames'] = new_frames 
   #save = 0
   if save == 1:
      save_json_file(json_file,jd)
   #l_xs, l_ys = plot_points(frames)
   #l_xs, l_ys = plot_points(new_frames )
   print("SCORE:", ps_new)
   for frame in frames:
      print(frame['fn'], frame['dist_to_line'],frame['dist_from_last'])
   return(ps_new,new_frames)

def fix_up_points(json_file, frames=None, save=1):
   if save == 1:
      jd = load_json_file(json_file)
   if frames is None:
      data = load_json_file(json_file)
      frames = data['frames']
   xs = []
   ys = []
   fn = []
   new_frames = []
   first_x = None
   first_fn = None
   last_x = None
   last_dist_from_start = None
   dists = []
   point_score, new_frames = calc_score(frames)
   orig_point_score = point_score

   #print("Min,Max,Mean line err:", min(med_errs), max(med_errs),np.mean(med_errs), score)
   print("START SCORE: ", point_score)
   print("PLOT!")
   l_xs, l_ys = plot_points(new_frames )
   i = 0
  
   hd_file = json_file.replace(".json", "-HD.mp4") 
    
   hd_frames,hd_color_frames,hd_subframes,sum_vals,max_vals,pos_vals = load_frames_fast(hd_file, json_conf, 0, 0, [], 0,[])
   x_dir_mod,y_dir_mod = meteor_dir(new_frames[0]['x'], new_frames[0]['y'], new_frames[-1]['x'], new_frames[-1]['y'])
   dom,z,med_dist,med_seg,mxd,myd = line_info(new_frames) 
   avg_dist = calc_dist((new_frames[0]['x'],new_frames[0]['y']),(new_frames[-1]['x'], new_frames[-1]['y'])) / len(new_frames)
   adj_frames = []
   last_x = None
   temp_frames = []
   l_xs, l_ys = plot_points(new_frames )
   print("NEW MED SEG LEN:", med_seg)
   print("NEW AVG LEN:", avg_dist)

   for frame in new_frames:
      fn = frame['fn']
      lx  = int(l_xs[i])
      ly  = int(l_ys[i])
      if last_x is not None:
         last_dist = calc_dist((lx,ly),(last_x,last_y))
         if abs(last_dist - avg_dist) > 2:
            lx = last_x + mxd
            ly = last_y + myd

      print("FN:", fn, len(hd_frames))
      img = hd_frames[fn]
      cx1,cy1,cx2,cy2 = bound_cnt(lx,ly,img.shape[1],img.shape[0], 20)
      crop= img[cy1:cy2,cx1:cx2]
      big_cnt = cv2.resize(crop, (0,0),fx=10, fy=10)
      cv2.line(big_cnt, (200,0), (200,400), (100), 1)
      cv2.line(big_cnt, (0,200), (400,200), (100), 2)
      adj_x, adj_y = center_cnt(big_cnt, x_dir_mod, y_dir_mod, dom)
      adj_x = int(adj_x / 10)
      adj_y = int(adj_y / 10)
      cx1,cy1,cx2,cy2 = bound_cnt(lx-adj_x,ly-adj_y,img.shape[1],img.shape[0], 20)
      crop2 = img[cy1:cy2,cx1:cx2]
      big_cnt2 = cv2.resize(crop2, (0,0),fx=10, fy=10)
      cv2.line(big_cnt2, (200,0), (200,400), (100), 1)
      cv2.line(big_cnt2, (0,200), (400,200), (100), 2)
      if last_x is not None:
         last_dist = calc_dist((lx-adj_x,ly-adj_y),(last_x,last_y))
         if abs(last_dist - avg_dist) < 2:
            # new centered frame distance is ok to update
            print("Update frame with new value")
            frame['x'] = lx-adj_x
            frame['y'] = ly-adj_y
         else:
            print("Don't update with center adj, no good.", avg_dist, med_dist, last_dist)
            if last_x is None:
               frame['x'] = lx
               frame['y'] = ly
            else:
               frame['x'] = last_x + mxd
               frame['y'] = last_y + myd
          

      cv2.imshow('orig', big_cnt)
      cv2.imshow('center', big_cnt2)
      cv2.waitKey(0)
      i = i + 1
      adj_frames.append(frame)
      last_x = frame['x']
      last_y = frame['y']
      temp_frames.append(frame)
 
   new_frames = temp_frames
   l_xs, l_ys = plot_points(new_frames )
   point_score, new_frames = calc_score(new_frames)
   new_frames = fix_one_bad_frame(new_frames, avg_dist, mxd,myd)
   for frame in new_frames:
      print(frame)


   if save == 1:
      jd['report']['point_score'] = point_score 
      point_score, new_frames = calc_score(adj_frames)
      if point_score < orig_point_score:
         print("updateing frames with better score:", orig_point_score, point_score)
         jd['frames'] = new_frames 
         jd['report']['point_score'] = point_score 
      else:
         print("not saving new frames, old is better.", orig_point_score, point_score) 
      print("SAVED:", json_file)
      save_json_file(json_file, jd)


   return(point_score, new_frames) 

def fix_one_bad_frame(frames,avg_dist,mxd,myd):
   fix = 0
   last_x = None
   new_frames = []
   
   for frame in frames:
      x = frame['x']
      y = frame['y']
      if last_x is not None:
         dist = calc_dist((last_x,last_y),(x,y))
         if abs(dist - avg_dist) > 2 and fix == 0:
            print("FIX THIS FRAME!:", frame['fn'])
            print("ERROR :", abs(dist - avg_dist)) 
            new_x = last_x + mxd
            new_y = last_y + myd
            frame['x'] = new_x
            frame['y'] = new_y
            fix = 1
      last_x = x
      last_y = y
      new_frames.append(frame)
   return(new_frames)

def calc_score(frames):
   first_x = None
   last_x = None
   last_dist_from_start = None
   dists = []
   new_frames = []
   xs = []
   ys = []
   for frame in frames:
      x = frame['x']
      y = frame['y']
      xs.append(x)
      ys.append(y)
   for frame in frames:
      (dist_to_line, z, med_dist) = poly_fit_check(xs,ys, frame['x'],frame['y'])
      if first_x is None:
         first_x = frame['x']
         first_y = frame['y']
         first_fn = frame['fn']
         dist_from_start = 0
         dist_from_last = 0
      if last_x is not None:
         dist_from_start = calc_dist((first_x,first_y),(frame['x'],frame['y']))
      if last_dist_from_start is not None:
         dist_from_last = dist_from_start - last_dist_from_start
      else:
         last_dist_from_start = 0
         dist_from_last = 0
      last_x = frame['x']
      last_x = frame['y']
      last_dist_from_start = dist_from_start
      frame['dist_from_start'] = dist_from_start
      frame['dist_from_last'] = dist_from_last
      frame['dist_to_line'] = dist_to_line
      dists.append(dist_from_last)
      new_frames.append(frame)

   med_dist = np.median(dists)
   med_errs = []
   final_frames = []
   for frame in new_frames:
      if med_dist > 0 and frame['dist_from_last'] > 0:
         med_err = abs(med_dist - frame['dist_from_last']) + frame['dist_to_line']
         frame['med_err'] = med_err 
         print("MED ERR:", med_err)
         if med_err > 2:
            print("MED ERROR HIGH, TRY TO MINIMIZE!")
 
      else:
         med_err = 0
      med_errs.append(med_err)
      final_frames.append(frame)
   if len(med_errs) == 0:
      score = 999 
   else:
      #score = (max(med_errs)/min(med_errs)) * np.mean(med_errs)
      score = np.mean(med_errs)
   return(score, final_frames)


def find_best_cnt(cnts, xd,yd):
   hx = 0
   hy = 0
   lx = 99
   ly = 99
   cnt_tmp = [] 
   for x,y,w,h in cnts:
      my = y + h
      mx = x + w
      if w > 1 and h > 1:
         cnt_tmp.append((x,y,w,h,mx,my))
   if xd == 1 and yd == -1:
      # we want the cnt with the highest (y+h) and lowest x  (left to right top down)
      temp = sorted(cnt_tmp, key=lambda x: x[5], reverse=True)
      best_cnt = temp[0][0:4]
   if xd == -1 and yd == -1:
      # we want the cnt with the highest (y+h) and highest x (right to left top down)
      temp = sorted(cnt_tmp, key=lambda x: x[4], reverse=True)
      best_cnt = temp[0][0:4]

   if xd == -1 and yd == 1:
      print("TOP DOWN RIGHT TO LEFT")
      # we want the cnt with the lowest (y) and lowest x (right to left down to top)
      temp = sorted(cnt_tmp, key=lambda x: x[5], reverse=False)
      best_cnt = temp[0][0:4]
   if xd == 1 and yd == 1:
      # we want the cnt with the lowest (y) and lowest x (right to left down to top)
      temp = sorted(cnt_tmp, key=lambda x: x[5], reverse=False)
      best_cnt = temp[0][0:4]
   print("XD:", xd,yd)
   return([best_cnt] )

def abline(slope, intercept):
   """Plot a line from slope and intercept"""
   x_vals = np.array((0,1920))
   y_vals = intercept + slope * x_vals
   return(x_vals,y_vals)
   
      
def line_info(frames):
   xs = []
   ys = []
   line_segs = []
   xdiffs = []
   ydiffs = []
   last_x = None
   for frame in frames:
       x = frame['x']
       y = frame['y']
       if last_x is not None:
          xdiffs.append(x - last_x)
          ydiffs.append(y - last_y)
       xs.append(frame['x'])
       ys.append(frame['y'])
       line_segs.append(frame['dist_from_last'])
       last_x = x
       last_y = y
   tx = abs(xs[0] - xs[-1])
   ty = abs(ys[0] - ys[-1])
   med_seg = np.median(line_segs)

   mxd = np.median(xdiffs)
   myd = np.median(ydiffs)

   (dist_to_line, z, med_dist) = poly_fit_check(xs,ys, xs[0],ys[0])

   if ty > tx:
      return("y", z, med_dist,med_seg,mxd,myd)
   else:
      return("x", z, med_dist,med_seg,mxd,myd)

def fix_arc_points(json_file):
   json_conf = load_json_file("../conf/as6.json")
   st_id = json_file.split("/")[4]
   print("JSON FILE:", json_file)
   json_data = load_json_file(json_file)

   
   l_xs, l_ys = plot_points(json_data['frames'])

   if st_id != json_conf['site']['ams_id']:
      # this is a remote station, reload the json conf file!
      json_conf_file = "/mnt/ams2/meteor_archive/" + st_id + "/CAL/as6.json"  
      json_conf = load_json_file(json_conf_file)
   hd_file = json_file.replace(".json", "-HD.mp4")
   hd_frames,hd_color_frames,hd_subframes,sum_vals,max_vals,pos_vals = load_frames_fast(hd_file, json_conf, 0, 0, [], 0,[])
   print("HD FRAMES:", len(hd_frames))
   print("HD SUB FRAMES FRAMES:", len(hd_subframes))
   if 'x_dir_mod' in json_data['report']:
      xd = json_data['report']['x_dir_mod']
      yd = json_data['report']['y_dir_mod']
   else:
      fd = json_data['frames']
      print(fd, json_data)
      xd, yd = meteor_dir(fd[0]['x'],fd[0]['y'],fd[-1]['x'],fd[-1]['y'])
      json_data['report']['x_dir_mod'] = xd
      json_data['report']['y_dir_mod'] = yd

   # x=1 = right to left x=-1 left to rught
   # y=-1 = top to bottom y =1 bottom to top
   dom,z,med_dist,med_seg,mxd,myd = line_info(json_data['frames']) 
   new_frame_data = []
   frames = json_data['frames']
   ep_res = eval_points(json_file, frames, 0)
   for fd in frames:
      found = 1
      fn = fd['fn']
      x = fd['x']
      y = fd['y']
      cx1,cy1,cx2,cy2 = bound_cnt(x,y,hd_frames[0].shape[1],hd_frames[0].shape[0], 20)
      frame = hd_frames[fn]
      print("FRAME SHAPE: ", frame.shape)
      if frame.shape[0] != 1080:
         print("FRAME SIZE IS 1280x720 !")
         exit()
      cnt = frame[cy1:cy2,cx1:cx2]
      big_cnt = cv2.resize(cnt, (0,0),fx=10, fy=10)

      min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(big_cnt)
      thresh = max_val - 20
      avg_val = np.mean(big_cnt)
      #if thresh < avg_val:
      thresh = avg_val + 10
            
      blur_cnt= cv2.GaussianBlur(big_cnt, (7, 7), 0)
      cnts,rects = find_contours_in_frame(blur_cnt, thresh)
      if len(cnts) == 0:
         thresh = avg_val + 5
         cnts,rects = find_contours_in_frame(blur_cnt, thresh)
         print("CNTS 2nd try:", len(cnts))
         if len(cnts) == 0:
            cnts = [[200,200,5,5]]
            found = 0

      if len(cnts) > 1:
         thresh += 10
         cnts2,rects = find_contours_in_frame(big_cnt, thresh)
         if len(cnts2) > 1:
            max_val - 10
            cnts2,rects = find_contours_in_frame(big_cnt, thresh)

         if len(cnts2) == 1:
            cnts = cnts2
      if len(cnts) > 1:
         cnts = find_best_cnt(cnts, xd,yd) 

      # plot slope line 
      x_vals, y_vals = abline(z[0],z[1])
      ny_vals = []
      for yv in y_vals:
         ny_vals.append((yv))
      y_vals = ny_vals
      #cv2.line(frame, (int(x_vals[0]),int(y_vals[0])), (int(x_vals[-1]),int(y_vals[-1])), (255), 1)
      cnt = frame[cy1:cy2,cx1:cx2]
      big_cnt = cv2.resize(cnt, (0,0),fx=10, fy=10)

      cx,cy,cw,ch = cnts[0]
      # Now find offset from leading corner to center
      if xd == 1:
         # we want the corner with the lowest x 
         x_corner = cx
         x_corner2 = cx + int(cw / 2)
      else:
         x_corner = cx + cw - int(cw/2)
         x_corner2 = cx + cw 
      if yd == -1:
         y_corner = cy + ch - int(ch/2)
         y_corner2 = cy + ch
      else:
         y_corner = cy  
         y_corner2 = cy  + int(ch/2)

      small_cnt = big_cnt[y_corner:y_corner2,x_corner:x_corner2]
      blur_cnt= cv2.GaussianBlur(small_cnt, (7, 7), 0)
      avg_val = np.mean(blur_cnt)
      #if thresh < avg_val:
      thresh = avg_val + 5
      small_cnts,rects = find_contours_in_frame(small_cnt, thresh)

      if len(small_cnts) == 1 and found == 1:
         if xd == -1:
            # we want the corner with the highest x (because we are going backwards now)
            sadj_x = small_cnts[0][0] + int(small_cnts[0][2]) + x_corner
         else:
            sadj_x = small_cnts[0][0] + x_corner
         if yd == -1:
            #Bottom to top, we want the highest y (backwards)
            sadj_y = small_cnts[0][1] + int(small_cnts[0][3]) + y_corner
         else:
            sadj_y = small_cnts[0][1] + y_corner 
      else:
         sadj_x = 200
         sadj_y = 200

      # Now re-grab the CNT
      real_x = int((sadj_x / 10) + cx1)
      real_y = int((sadj_y / 10) + cy1)
      ncx1,ncy1,ncx2,ncy2 = bound_cnt(real_x,real_y,frame.shape[1],frame.shape[0], 20)
      fd['adj_x'] = real_x
      fd['adj_y'] = real_y
      fd['x'] = real_x
      fd['y'] = real_y
      new_frame_data.append(fd)
      adj_cnt = frame[ncy1:ncy2,ncx1:ncx2]
      adj_cnt = cv2.resize(adj_cnt, (0,0),fx=10, fy=10)

      # build small box around corner

      cv2.rectangle(big_cnt, (cx, cy), (cx+cw, cy+ch), (255,255,255), 1, cv2.LINE_AA)
      cv2.rectangle(big_cnt, (x_corner, y_corner), (x_corner2, y_corner2), (255,255,255), 1, cv2.LINE_AA)

      cv2.circle(big_cnt,(sadj_x,sadj_y), 10, (0,255,0), 2)
      cv2.line(big_cnt, (200,0), (200,400), (100), 1)
      cv2.line(big_cnt, (0,200), (400,200), (100), 2)
      cv2.line(adj_cnt, (200,0), (200,400), (100), 1)
      cv2.line(adj_cnt, (0,200), (400,200), (100), 2)
      print(big_cnt.shape)
      #cv2.imshow('pepe', big_cnt)
      #cv2.waitKey(0)
  
      bch, bcw = big_cnt.shape[:2]
      ach, acw = adj_cnt.shape[:2]
      if bch != bcw :
         big_cnt = cv2.resize(big_cnt, (400,400))
      if ach != acw:
         adj_cnt = cv2.resize(adj_cnt, (400,400))

      try: 
         if show == 1:
            frame[0:400,0:400] = big_cnt
            frame[400:800,0:400] = adj_cnt
            show_frame = cv2.resize(frame.copy(), (1280,720))
            cv2.imshow('pepe', show_frame)
            cv2.waitKey(50)
      except:
         print("failed to show frame")

   # parse trim_num
   video_file = json_file.replace(".json", "-HD.mp4")
   xxx = video_file.split("-")
   trim_num = xxx[-1].replace("trim", "")
   trim_num = trim_num.replace(".mp4", "")

   for fd in new_frame_data:
      print(fd)
   
   new_frame_data = fix_missing_frames(new_frame_data)
   new_frame_data = fix_bad_frames(new_frame_data)
   dur = len(new_frame_data) / 25
   json_data['report']['dur'] = dur

   res2 = eval_points(json_file, new_frame_data, 0)
   if res2 < ep_res:
      print("New points are better than old!")
      json_data['frames'] = new_frame_data
      save_json_file(json_file, json_data)
      res2 = eval_points(json_file, new_frame_data, 1)
   else:
      print("Old points are better than new!")

def fix_missing_frames(frame_data):
   new_frames = []
   last_fn = None
   fdiff = 0
   dom,z,med_dist,med_seg,mxd,myd = line_info(frame_data) 
   for frame in frame_data:
      fn = frame['fn']
      if last_fn is not None:
         fdiff = fn - last_fn
      if fdiff > 1:
         print("Missing frame detected!", fdiff)
         for i in range(0,fdiff-1):
            new_frame = frame.copy()
            new_fn = fn - (fdiff - i) + 1
            print("NEW FN:", new_fn, i)
            new_frame['fn'] = new_fn
            new_frame['x'] = frame['x'] - mxd
            new_frame['y'] = frame['y'] - mxd
            new_frames.append(new_frame) 
      last_frame = frame
      new_frames.append(frame)
      last_fn = fn
   return(new_frames)
 

def fix_bad_frames(frame_data):
   dom,z,med_dist,med_seg,mxd,myd = line_info(frame_data) 
   fc = 0
   xs = []
   ys = []
   last_x = None
   new_frames = []
   last_x = None
   for frame in frame_data:
      x = frame['x']
      y = frame['y']
      if fc > 0:
         err = abs(1 - (frame['dist_from_last'] / med_seg))
         if err < .3:
            print("FRAME GOOD:", frame['fn'], med_dist, med_seg, frame['dist_from_last'], err, x,y)
         else:
            if last_x is not None: 
               better_x = int(last_x + mxd)
               better_y = int(last_y + myd)
               print("FRAME BAD:", frame['fn'], med_dist, med_seg, frame['dist_from_last'], err, x,y, better_x, better_y, mxd,myd)
               x = better_x
               y = better_y
               frame['x'] = x
               frame['y'] = y 
                  

            else:
               print("FIRST FRAME :", frame['fn'], med_dist, med_seg, frame['dist_from_last'], err, x, y)
         new_frames.append(frame)
    
      xs.append(frame['x'])
      ys.append(frame['y'])
      fc += 1
      last_x = x
      last_y = y
   return(new_frames)

def frame_data_to_arc_frames(frame_data):
   frames = []
   for fn in frame_data :
      if "leading_x" in frame_data[fn]:


         frame = {}
         frame['fn'] = fn
         frame['x'] =  frame_data[fn]['leading_x']
         frame['y'] =  frame_data[fn]['leading_y']
         frame['w'] =  frame_data[fn]['blob_w']
         frame['h'] =  frame_data[fn]['blob_h']
         frame['intensity'] =  frame_data[fn]['blob_int']
         frame['dist_from_last'] =  frame_data[fn]['dist_from_last']
         frame['dist_from_start'] =  frame_data[fn]['dist_from_start']
         frames.append(frame)
   return(frames)

def add_arc_stars(cal_params):
   cal_params['device_lat'] = cal_params['site']['device_lat']
   cal_params['device_lng'] = cal_params['site']['device_lng']
   cal_params['device_alt'] = cal_params['site']['device_alt']
   cal_params['orig_ra_center'] = cal_params['ra_center']
   cal_params['orig_dec_center'] = cal_params['dec_center']

   cal_params['orig_az_center'] = cal_params['center_az']
   cal_params['orig_el_center'] = cal_params['center_el']
   cal_params['orig_pos_ang'] = cal_params['position_angle']
   cal_params['orig_pixscale'] = cal_params['pixscale']
   cal_params['cat_image_stars'] = []

   cat_stars = flex_get_cat_stars(obj['trim_clip'], cal_params_file, json_conf, cal_params )
   #cat_image_stars = get_cat_image_stars(cat_stars, frame, cal_params_file)
   archive_file = obj['hd_trim']
   image_stars = get_image_stars(archive_file,frame, show=1)
   cat_image_stars = []
   calib_stars = []
   used_cat_stars = {}
   used_img_stars = {}
   for star in image_stars:
      print("STAR:", star)
      best_star = find_best_cat_stars(cat_stars, star[0], star[1], frame, archive_file)
      print("BEST:", best_star)
      istar_key = str(star[0]) + str(star[1])
      cstar_key = str(best_star[4]) + str(best_star[5])
      if istar_key not in used_img_stars and cstar_key not in used_cat_stars:
         cv2.line(frame, (star[0], star[1]), (int(best_star[4]), int(best_star[5])), (128,128,128), 1)
         calib_star = {}
         cat_image_stars.append(best_star)
         used_img_stars[istar_key] = 1
         used_cat_stars[cstar_key] = 1

def get_stars_res(stars):
   dist = []
   for star in stars:
      dist.append(star['dist_px'])
   return(float(np.mean(dist)))


def fit_arc_file(json_file):
   json_conf = load_json_file("../conf/as6.json")
   st_id = json_file.split("/")[4]
   print("JSON FILE:", json_file)
   json_data = load_json_file(json_file)
   if "calib" in json_data:
      orig_calib = json_data['calib']
      orig_stars = json_data['calib']['stars']
      new_stars = update_arc_cat_stars(orig_calib,json_file,json_conf)
      star_res = get_stars_res(new_stars)
      print("Current star res is: ", star_res)

   if st_id != json_conf['site']['ams_id']:
      # this is a remote station, reload the json conf file!
      json_conf_file = "/mnt/ams2/meteor_archive/" + st_id + "/CAL/as6.json"  
      json_conf = load_json_file(json_conf_file)
   (hd_datetime, cam, sd_date, sd_y, sd_m, sd_d, sd_h, sd_M, sd_s) = convert_filename_to_date_cam(json_file)
   station = json_file.split("/")[4]
   master_lens_file = "/mnt/ams2/meteor_archive/" + station + "/CAL/master_lens_model/master_cal_file_" + cam + ".json"

   hd_file = json_file.replace(".json", "-HD.mp4")
   hd_frames,hd_color_frames,hd_subframes,sum_vals,max_vals,pos_vals = load_frames_fast(hd_file, json_conf, 0, 0, [], 0,[])
   frame = hd_frames[0]

   calib = json_data['calib']

   last_best_calibs = find_last_best_calib(json_file,orig_stars)
   if len(last_best_calibs) > 0:
      last_best_calib = load_json_file(last_best_calibs[0][0] )
      print("LAST BEST CALIB IS:", last_best_calib)
      last_best_calib['stars'] = orig_stars
      new_stars = update_arc_cat_stars(last_best_calib,json_file,json_conf)
      new_star_res = get_stars_res(new_stars)
      print("Star res with last best calib: ", new_star_res)
      if new_star_res < star_res: 
         print("Use last best!", last_best_calibs[0][0])
         calib['device'] = last_best_calib['device']
         calib['stars'] = new_stars
         cal_params = calib_to_calparams(calib, json_file)
      else:
         print("Use originla params !")
         cal_params = calib_to_calparams(calib, json_file)
      calib['device'] = last_best_calib['device']

   calib['stars'] = remove_bad_stars(calib['stars'])

   cal_params = calib_to_calparams(calib, json_file)

   orig = {}
   orig['center_az'] = cal_params['orig_az_center']
   orig['center_el'] = cal_params['orig_el_center']
   orig['pos_ang'] = cal_params['orig_pos_ang']
   orig['pixscale'] = cal_params['orig_pixscale']

   cat_image_stars = cal_params['cat_image_stars']
   if len(cat_image_stars) < 3:
      print("Not enough stars to fit!")
      if "stars" not in calib:
         calib['stars'] = []
      json_data['calib'] = calib
      print("Replacing calib with last best calib and saving.")
      save_json_file(json_file, json_data)
      return()

   if cfe(master_lens_file) == 1:
      print("Using master lens file")
      mld = load_json_file(master_lens_file)
      cal_params['x_poly'] = mld['x_poly']
      cal_params['y_poly'] = mld['y_poly']
      cal_params['y_poly_fwd'] = mld['y_poly_fwd']
      cal_params['x_poly_fwd'] = mld['x_poly_fwd']

   if True:
      this_poly = np.zeros(shape=(4,), dtype=np.float64)

      print(calib['device'])
      print(cal_params)

      start_res = reduce_fov_pos(this_poly, cal_params, json_file,frame,json_conf, cat_image_stars,0,show)
      print("Start Res:", start_res)
      cal_params_orig = cal_params.copy()
      res = scipy.optimize.minimize(reduce_fov_pos, this_poly, args=( cal_params,json_file,frame,json_conf, cat_image_stars,1,show), method='Nelder-Mead')

   

      print("RES:", res)

      fov_pos_poly = res['x']
      fov_pos_fun = res['fun']
      cal_params['x_poly'] = cal_params_orig['x_poly']
      cal_params['y_poly'] = cal_params_orig['y_poly']

      cal_params['fov_pos_poly'] = fov_pos_poly.tolist()
      cal_params['fov_pos_fun'] = fov_pos_fun



      cal_params['center_az'] = float(cal_params['orig_az_center']) + float(fov_pos_poly[0] )
      cal_params['center_el'] = float(cal_params['orig_el_center']) + float(fov_pos_poly[1] )

      cal_params['position_angle'] = float(cal_params['position_angle']) + float(fov_pos_poly[2] )
      #cal_params['orig_pos_angle'] = float(cal_params['orig_pos_ang']) + float(fov_pos_poly[2] )

      cal_params['pixscale'] = float(cal_params['orig_pixscale']) + float(fov_pos_poly[3] )
      #cal_params['orig_pixscale'] = float(cal_params['orig_pixscale']) + float(fov_pos_poly[3] )



      rah,dech = AzEltoRADec(cal_params['center_az'],cal_params['center_el'],json_file,cal_params,json_conf)
      rah = str(rah).replace(":", " ")
      dech = str(dech).replace(":", " ")
      ra_center,dec_center = HMS2deg(str(rah),str(dech))
      cal_params['ra_center'] = ra_center
      cal_params['dec_center'] = dec_center
      cal_params['fov_fit'] = 1

      this_poly = np.zeros(shape=(4,), dtype=np.float64)
      #final_res = reduce_fov_pos(this_poly, cal_params,json_file,frame,json_conf, cat_image_stars,0,show)
      #print("FINAL RES:", final_res)

      cal_params['total_res_px'] = fov_pos_fun

      #cat_image_stars = get_cat_image_stars(cat_stars, frame,cal_params_file)

   calib = format_calib(json_file, cal_params, json_file)
   new_stars = update_arc_cat_stars(calib,json_file,json_conf)
   calib['stars'] = new_stars
   save_json_file("test.json", new_stars)


   json_data['calib'] = calib
   save_json_file(json_file, json_data)
   print("FOV POLY:", fov_pos_poly)
   print("ORIG:", orig)
   print("FINAL", calib['device']) 


   # now do the lens fit, if requested:
   lens_fit =  1
   if lens_fit == 1:
      cal_params = minimize_poly_params_fwd(json_file, cal_params,json_conf)
   calib['device']['poly']['x'] = cal_params['x_poly']
   calib['device']['poly']['y'] = cal_params['y_poly']
   calib['device']['poly']['x_fwd'] = cal_params['x_poly_fwd']
   calib['device']['poly']['y_fwd'] = cal_params['y_poly_fwd']

   new_stars = update_arc_cat_stars(calib,json_file,json_conf)
   calib['stars'] = new_stars
   json_data['calib'] = calib
   save_json_file(json_file, json_data)
   if len(calib['stars']) > 15 and cal_params['total_res_px'] < 2.4:
      last_best = calib
      del last_best['stars']
      lbf = json_file.split("/")[-1]
      last_best_file = "/mnt/ams2/meteor_archive/" + station + "/CAL/last_best/" + lbf
      save_json_file(last_best_file, last_best)


   print(json_file)

# Catalog Stars
def update_arc_cat_stars(calib, json_file,json_conf):
   star_points = []
   cal_params = calib_to_calparams(calib, json_file)
   for star in calib['stars']:
      ix = star['i_pos'][0]
      iy = star['i_pos'][1]
      star_points.append((ix,iy))


   # Get the values from the form
   #hd_stack_file = form.getvalue("hd_stack_file")   # Stack
   #video_file = form.getvalue("video_file")         # Video file
   #meteor_red_file = form.getvalue("json_file")
   #hd_image = cv2.imread(hd_stack_file, 0)


   cat_stars = flex_get_cat_stars(json_file, json_file, json_conf, cal_params )


   my_close_stars = []
   cat_dist = []
   used_cat_stars = {}
   used_star_pos = {}

   if True:
      for ix,iy in star_points:
         close_stars = find_close_stars((ix,iy), cat_stars)

         if len(close_stars) == 1:
            name,mag,ra,dec,cat_x,cat_y,scx,scy,cat_star_dist = close_stars[0]
            #new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(ix,iy,video_file,meteor_red['calib'])
            new_x, new_y, img_ra ,img_dec , img_az, img_el = XYtoRADec(ix,iy,json_file,cal_params,json_conf)
            new_star = {}

            new_star['name'] = name
            new_star['mag'] = mag
            new_star['ra'] = ra
            new_star['dec'] =  dec
            new_star['dist_px'] = cat_star_dist
            cat_dist.append(cat_star_dist)

            # The image x,y of the star (CIRCLE)
            new_star['i_pos'] = [ix,iy]
            # The lens distorted catalog x,y position of the star  (PLUS SIGN)
            new_star['cat_dist_pos'] = [new_x,new_y]
            # The undistorted catalog x,y position of the star  (SQUARE)
            new_star['cat_und_pos'] = [cat_x,cat_y]

            # distorted position should be the new_x, new_y and + symbol
            # only add if this star/position combo has not already be used
            used_star = 0
            this_rakey = str(ra) + str(dec)
            if this_rakey not in used_cat_stars:
               my_close_stars.append(new_star)
               used_cat_stars[this_rakey] = 1

   return(my_close_stars)

def find_last_best_calib(input_file, orig_stars = None ):
   (f_datetime, cam_id, f_date_str,Y,M,D, H, MM, S) = better_parse_file_date(input_file)
   station_id = json_conf['site']['ams_id']
   matches = []
   cal_dir = "/mnt/ams2/meteor_archive/" + station_id + "/CAL/last_best/*.json"
   print(cal_dir)
   all_files = glob.glob(cal_dir)
   for file in all_files:
      if cam_id in file :
         el = file.split("/")
         fn = el[-1]
         cp = file 
         if cfe(cp) == 1:
            matches.append(cp)
         else:
            print("CP NOT FOUND!", cp)

   td_sorted_matches = []

   for match in matches:
      (t_datetime, cam_id, f_date_str,Y,M,D, H, MM, S) = better_parse_file_date(match)
      tdiff = abs((f_datetime-t_datetime).total_seconds())
      td_sorted_matches.append((match,f_date_str,tdiff))


   temp = sorted(td_sorted_matches, key=lambda x: x[2], reverse=False)

   if orig_stars is not None:
      res_sorted = []
      for td in temp:
         file = td[0]
         temp_calib = load_json_file(file)
         temp_calib['stars'] = orig_stars
         new_stars = update_arc_cat_stars(temp_calib,input_file,json_conf)
         star_res = get_stars_res(new_stars)
         res_sorted.append((file,star_res))

      temp = sorted(res_sorted, key=lambda x: x[1], reverse=False)

   #for file,res in temp:
   #   print(file,res)

   return(temp)


def convert_old_cal_files():
   station_id = json_conf['site']['ams_id']
   cal_dir = "/mnt/ams2/cal/freecal/*"
   all_files = glob.glob(cal_dir)
   matches = []
   for file in all_files:
      el = file.split("/")
      fn = el[-1]
      cp = file + "/" + fn + "-stacked-calparams.json"
      if cfe(cp) == 1:
         matches.append(cp)
      else:
         cp = file + "/" + fn + "-calparams.json"
         if cfe(cp) == 1:
            matches.append(cp)
   for cal_params_file in matches:
      cal_params = load_json_file(cal_params_file)
      print(cal_params_file)
      calib = format_calib(cal_params_file, cal_params, cal_params_file)
      print(calib)
      cf = cal_params_file.split("/")[-1]
      cf = cf.replace("-stacked", "")
      cf = cf.replace("-calparams", "")
      new_file = "/mnt/ams2/meteor_archive/" + station_id + "/CAL/last_best/" + cf
      save_json_file(new_file, calib)


def get_best_cal_file(input_file, user_station):
   #print("INPUT FILE", input_file)
   if "png" in input_file:
      input_file = input_file.replace(".png", ".mp4")
   (f_datetime, cam_id, f_date_str,Y,M,D, H, MM, S) = better_parse_file_date(input_file)

   # find all cal files from his cam for the same night
   matches = find_matching_cal_files(json_conf['site']['ams_id'], cam_id, f_datetime, user_station)
   #print("MATCHED:", matches)
   if len(matches) > 0:
      return(matches)
   else:
      return(None)


def confirm_meteor_OLD(meteor_json_file):
   if "maybe-meteors" in meteor_json_file:
      video_file = meteor_json_file.replace("-maybe-meteors.json", ".mp4")
      video_file = video_file.replace("data/", "")
   mj = load_json_file(meteor_json_file)
   meteors = only_meteors(mj['objects'])
   print(meteors)


   if old_scan == 0:
      video_file = meteor_json_file.replace("-meteor.json", ".mp4")
   else:
      video_file = meteor_json_file.replace(".json", ".mp4")
   orig_stack_file = meteor_json_file.replace("-meteor.json", "-stacked.png")
   print("CONFIRM:", video_file)
   (hd_datetime, cam, sd_date, sd_y, sd_m, sd_d, sd_h, sd_M, sd_s) = convert_filename_to_date_cam(video_file)

   masks = get_masks(cam, json_conf,0)

   meteor_date = sd_y + "_" + sd_m + "_" + sd_d
   sun_alt = find_sun_alt(hd_datetime)
   if sun_alt > -5:
      sun_up = 1
      print("SUN is up:", sun_alt)
   else:
      sun_up = 0
   
   meteor_objects = load_json_file(meteor_json_file)
   if old_scan == 1:
      mo = []
      if "flex_detect" in meteor_objects:
         mo.append(meteor_objects['flex_detect'])
      else:
         mo = quick_scan(video_file, 1)
      meteor_objects = mo
      print("METEOR OBJECTS:", len(meteor_objects))


   meteor_objects = objects_to_clips(meteor_objects)
   print("METEOR OBJECTS:", meteor_objects)

   # make trim clips for the possible meteors
   if old_scan == 0:
      if sun_up == 0:
         trim_clips, trim_starts, trim_ends,meteor_objects = make_trim_clips(meteor_objects, video_file)   
      else:
         trim_clips, trim_starts, trim_ends,meteor_objects = make_trim_clips(meteor_objects, video_file)   
         print("Process daytime file instead.", trim_clips)
   else:
      trim_clips = []
      trim_starts = []
      for mo in meteor_objects:
         print("MO:", mo)
         tc = mo['trim_clip'].replace("/mnt/ams2/CAMS/queue/", "/mnt/ams2/meteors/" + meteor_date + "/" )
         trim_clips.append(tc)
         xxx = video_file.split("-")
         trim_num = xxx[-1].replace("trim", "")
         trim_num = trim_num.replace(".mp4", "")
         trim_starts.append(int(trim_num))


   print("TRIM CLIPS!", trim_clips)
   print("TRIM METEORS!", len(meteor_objects))

   for mo in meteor_objects:
      print(mo)
   motion_meteors = []
   no_motion_meteors = []
   tc = 0
   for trim_clip in trim_clips:
      motion_objects,meteor_frames = detect_meteor_in_clip(trim_clip , None, trim_starts[tc])
      for mid in motion_objects:
         mobject = motion_objects[mid]
         if mobject['report']['meteor_yn'] == 'Y':
            motion_meteors.append(mobject)
         else:
            no_motion_meteors.append(mobject)
         
      tc = tc + 1


   print("Total motion meteors:", len(motion_meteors))
   for mm in motion_meteors:
      poly_fit(mm, motion_objects) 
   print("Total non motion meteors:", len(no_motion_meteors))
   for mo in no_motion_meteors:
      print(mo['report']['bad_items'])







   if len(motion_meteors) == 0:
      reject_meteor(meteor_json_file) 
      return()
   meteor_objects = motion_meteors

 
   old_meteor_dir = "/mnt/ams2/meteors/" + meteor_date + "/"
   oc =0
   old_meteor_dir = "/mnt/ams2/meteors/" + meteor_date + "/"
   for obj in meteor_objects:
      start = mm['ofns'][0]
      end = mm['ofns'][-1]
      # sync HD
      df = int ((end - start) / 25)
      hd_file, hd_trim,time_diff_sec, dur = find_hd_file_new(video_file, start, df, 1)
      print("START END:", start, end, df)
      print("HD TRIM:", hd_trim)
      if hd_trim is not None:
         print("HD SYNC:", hd_file, hd_trim, time_diff_sec, dur, df)
         # Make the HD stack file too.  And then sync the HD to SD video file.
         obj['hd_trim'] = hd_trim
         obj['hd_video_file'] = hd_file
         if hd_trim != 0 and cfe(hd_trim) == 1:
            hd_crop, crop_box = crop_hd(obj, meteor_frames[0])
            hd_crop_objects,hd_crop_frames = detect_meteor_in_clip(hd_crop, None, start, crop_box[0], crop_box[1])
            #refine_points(hd_crop, hd_crop_frames )
            obj['hd_crop_file'] = hd_crop
            obj['crop_box'] = crop_box 
            obj['hd_crop_objects'] = hd_crop_objects
            os.system("mv " + hd_trim + " " + old_meteor_dir)
         else:
            obj['hd_trim'] = 0
            obj['hd_video_file'] = 0

         print("REAL METEORS:", mm)
         process_meteor_files(obj, meteor_date, video_file, old_scan)
         oc = oc + 1

def process_meteor_files(obj, meteor_date, video_file, old_scan ):
   # save object to old style archive and then move the trim file and copy the stack file to the archive as well
   # move the new json dedtect file someplace else and then do the same for the new archive style
   trim_clip = obj['trim_clip']
   cx1, cy1,cx2,cy2= minmax_xy(obj)

   old_meteor_dir = "/mnt/ams2/meteors/" + meteor_date + "/"
   if cfe(old_meteor_dir, 1) == 0:
      os.system("mkdir " + old_meteor_dir)
   mf = trim_clip.split("/")[-1]
   mf = mf.replace(".mp4", ".json")
   meteor_json_file = video_file.replace(".mp4", "-meteor.json")
   old_meteor_json_file = old_meteor_dir + mf
   old_meteor_json_file = old_meteor_json_file.replace(".mp4", ".json")
   old_meteor_stack_file = old_meteor_json_file.replace(".json", "-stacked.png")
   orig_stack_file = video_file.replace(".mp4", "-stacked.png")

   if old_scan == 0:
      print("Save old meteor json", old_meteor_json_file)
      proc_dir = "/mnt/ams2/SD/proc2/" + meteor_date + "/" 
      # mv the trim video
      cmd = "mv " + trim_clip + " " + old_meteor_dir
      print(cmd)
      os.system(cmd)
      # copy the stack file

      cmd = "cp " + orig_stack_file + " " + proc_dir + "/images/"
      os.system(cmd)
      print(cmd)
      cmd = "mv " + orig_stack_file + " " + old_meteor_stack_file
      print(cmd)
      os.system(cmd)
      thumb(old_meteor_stack_file)
      stack_img = cv2.imread(old_meteor_stack_file)
      old_meteor_stack_obj_file = old_meteor_stack_file.replace(".png", "-obj.png")
      cv2.rectangle(stack_img, (cx1, cy1), (cx2, cy2), (255,255,255), 1, cv2.LINE_AA)
      cv2.imwrite(old_meteor_stack_obj_file, stack_img)
      thumb(old_meteor_stack_obj_file)

      # remove original meteor object file?
      cmd = "mv " + meteor_json_file + " /mnt/ams2/DEBUG/"
      print(cmd)
      os.system(cmd)
      one_min_file = meteor_json_file.replace("-meteor.json", ".mp4")
      if cfe(proc_dir, 1) == 0:
         os.system("mkdir " + proc_dir)
      cmd = "mv " + one_min_file + " " + proc_dir
      os.system(cmd)
      print(cmd)
      if old_scan == 0:
         save_old_style_meteor_json(old_meteor_json_file, obj, trim_clip )
   print("Meteor Files Processed and saved!", old_meteor_json_file)


def find_leading_edge(x_dir_mod, y_dir_mod,x,y,w,h,frame):
   if x_dir_mod == 1:
      leading_x = x
   else:
      leading_x = x + w
   if y_dir_mod == 1:
      leading_y = y
   else:
      leading_y =  y + h

   if True:
      leading_edge_x_size = int(w / 2)
      leading_edge_y_size = int(h / 2)

      le_x1 = leading_x
      le_x2 = leading_x + (x_dir_mod*leading_edge_x_size)
      le_y1 = leading_y
      le_y2 = leading_y + (y_dir_mod*leading_edge_y_size)
      tm_y = sorted([le_y1,le_y2])
      tm_x = sorted([le_x1,le_x2])
      le_x1 = tm_x[0]
      le_x2 = tm_x[1]
      le_y1 = tm_y[0]
      le_y2 = tm_y[1]

      le_cnt = frame[le_y1:le_y2,le_x1:le_x2]
      blur_frame = cv2.GaussianBlur(le_cnt, (7, 7), 0)
      min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(blur_frame)

      le_x = mx + (le_x1)
      le_y = my + (le_y1)
      cv2.circle(frame,(leading_x,leading_y), 10, (0,255,0), 1)
      cv2.circle(frame,(le_x,le_y), 5, (255,0,0), 1)
      #cv2.rectangle(frame, (x, y), (x+w, y+h), (255,255,255), 1, cv2.LINE_AA)
      cv2.rectangle(frame, (leading_x, leading_y), (leading_x+(x_dir_mod*leading_edge_x_size), leading_y+(y_dir_mod*leading_edge_y_size)), (255,255,255), 1, cv2.LINE_AA)





   return(le_x, le_y)
        
def refine_points_old(hd_crop, frames = None, color_frames = None):
   scx = 10
   scy = 10
   #hd_x1, hd_y1, hd_cw, hd_ch = crop_box
   if frames is None: 
      frames,color_frames,subframes,sum_vals,max_vals,pos_vals = load_frames_fast(hd_crop, json_conf, 0, 0, [], 0,[])
   fn = 0

   motion_objects,meteor_frames = detect_meteor_in_clip(hd_crop, frames, 0)
   meteors = {}
   for obj_id in motion_objects:
      obj = motion_objects[obj_id]
      if obj['report']['meteor_yn'] == "Y":
         meteors[obj_id] = obj
   motion_objects = meteors

   first_frame = frames[0]
   for obj in motion_objects:
      if "center_xs" not in motion_objects[obj]:
         motion_objects[obj]['crop_center_xs'] = []
         motion_objects[obj]['crop_center_ys'] = []
      for i in range(0, len(motion_objects[obj]['ofns'])):
         fn = motion_objects[obj]['ofns'][i]
         x = motion_objects[obj]['oxs'][i] - int(motion_objects[obj]['ows'][i]/2)
         y = motion_objects[obj]['oys'][i] - int(motion_objects[obj]['ohs'][i]/2) 
         w = motion_objects[obj]['ows'][i] 
         h = motion_objects[obj]['ohs'][i] 
         if color_frames is not None:
            show_frame = color_frames[fn].copy()
         else:
            show_frame = frames[fn].copy()
         frame = frames[fn]
         desc = str(fn) 

         cx1,cy1,cx2,cy2 = bound_cnt(x,y,frames[0].shape[1],frames[0].shape[0], 20)

         crop_img = frame[cy1:cy2,cx1:cx2]
         crop_bg = first_frame[cy1:cy2,cx1:cx2]
         crop_img_big = cv2.resize(crop_img, (0,0),fx=scx, fy=scy)
         crop_sub = cv2.subtract(crop_img,crop_bg)
         crop_sub_big = cv2.resize(crop_sub, (0,0),fx=scx, fy=scy)
         #min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(crop_sub_big)
         min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(crop_img_big)
         med_val = np.median(crop_img_big)
         px_diff = max_val - med_val
         
         thresh = med_val + (px_diff / 3)
         if thresh < med_val:
            thresh = med_val + 10 

         cnts,rects = find_contours_in_frame(crop_img_big, thresh)
         if len(cnts) > 1:
            cnts = merge_contours(cnts)
         for cnt in cnts:
            x, y, w, h = cnt 
            cv2.rectangle(crop_sub_big, (x, y), (x+w, x+h), (128,129,128), 1, cv2.LINE_AA)
            cv2.rectangle(crop_img_big, (x, y), (x+w, x+h), (128,129,128), 1, cv2.LINE_AA)
            main_x = int(((x+(w/2))/scx) + cx1)
            main_y = int(((y+(h/2))/scy) + cy1)
            mx1,my1,mx2,my2 = bound_cnt(main_x,main_y,show_frame.shape[1],show_frame.shape[0], 10)
            motion_objects[obj]['crop_center_xs'].append(main_x)
            motion_objects[obj]['crop_center_ys'].append(main_y) 


            cv2.rectangle(show_frame, (mx1, my1), (mx2, my2), (0,0,128), 1, cv2.LINE_AA)
            




   # Ok now that we have at least refined the main object's center, lets re-crop the frames around that 
   # and find the leading edge!
   if show == 1:
      cv2.destroyAllWindows()

   print(motion_objects)
   exit()

   for obj in motion_objects:
      x_dir_mod,y_dir_mod = meteor_dir(motion_objects[obj]['oxs'][0], motion_objects[obj]['oys'][0], motion_objects[obj]['oxs'][-1], motion_objects[obj]['oys'][-1])
      for i in range(0, len(motion_objects[obj]['ofns'])):
         fn = motion_objects[obj]['ofns'][i]
         x = motion_objects[obj]['oxs'][i] - int(motion_objects[obj]['ows'][i]/2)
         y = motion_objects[obj]['oys'][i] - int(motion_objects[obj]['ohs'][i]/2)
         w = motion_objects[obj]['ows'][i]
         h = motion_objects[obj]['ohs'][i]
         if "crop_center_xs" not in motion_objects[obj]:
            print("NO CENTER X", motion_objects[obj])
            exit() 
         center_x = motion_objects[obj]['crop_center_xs'][i]
         center_y = motion_objects[obj]['crop_center_ys'][i]
         if color_frames is not None:
            show_frame = color_frames[fn].copy()
         else:
            show_frame = frames[fn].copy()
         frame = frames[fn].copy()
         if color_frames is not None: 
            color_frame = color_frames[fn].copy()
         else:
            color_frame = frames[fn].copy()
         desc = str(fn)

         cx1,cy1,cx2,cy2 = bound_cnt(center_x,center_y,frames[0].shape[1],frames[0].shape[0], 10)
         crop_img = frame[cy1:cy2,cx1:cx2]
         crop_img_cl = color_frame[cy1:cy2,cx1:cx2]
         crop_img_big = cv2.resize(crop_img, (0,0),fx=scx, fy=scy)
         crop_img_big_cl = cv2.resize(crop_img_cl, (0,0),fx=scx, fy=scy)

         min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(crop_img_big)
         med_val = np.median(crop_img_big)
         px_diff = max_val - med_val

         thresh = med_val + (px_diff / 3)
         if thresh < med_val:
            thresh = med_val + 10

         cnts,rects = find_contours_in_frame(crop_img_big, thresh)
         if len(cnts) > 0:
            x,y,w,h = cnts[0]

            lx, ly = find_leading_edge(x_dir_mod, y_dir_mod,x,y,w,h,crop_img_big)
            lx = int(lx/scx) + cx1
            ly = int(ly/scy) + cy1
            if "leading_xs" not in motion_objects[obj]:
               motion_objects[obj]['leading_xs'] = []
               motion_objects[obj]['leading_ys'] = []
            motion_objects[obj]['leading_xs'].append(lx)
            motion_objects[obj]['leading_ys'].append(ly)


         cv2.circle(crop_img_big_cl,(lx,ly), 1, (255,255,255), 1)

   for obj in motion_objects:
      motion_objects[obj] = remove_bad_frames(motion_objects[obj])
      print("REFINED OBJECT!:", motion_objects[obj])

   for obj in motion_objects:
      xobj = motion_objects[obj]
      for i in range(0, len(xobj['ofns'])):
         fn = xobj['ofns'][i]
         lx = xobj['leading_xs'][i]
         ly = xobj['leading_ys'][i]
         ly = xobj['leading_ys'][i]
         if color_frames is not None:
            show_frame = color_frames[fn].copy()
         else:
            show_frame = frames[fn].copy()
         cv2.circle(show_frame,(lx,ly), 1, (0,0,255), 1)
         if show == 1:
            cv2.imshow("REFINE", show_frame)
            cv2.waitKey(70)

   return(motion_objects)

def calc_leg_segs(xobj):
   dist_from_start = []
   line_segs = []
   x_segs = []
   ms = []
   bs = []
   fx, fy = xobj['oxs'][0],xobj['oys'][0]
   # find distance from start point for each frame
   # turn that into seg_dist for each frame
   for i in range(0, len(xobj['ofns'])):
      tx = xobj['oxs'][i]
      ty = xobj['oys'][i]
      dist = calc_dist((fx,fy),(tx,ty))
      dist_from_start.append(dist)
      if i > 0 and i < len(xobj['ofns']) and len(xobj['ofns']) > 2:
         tm,tb = best_fit_slope_and_intercept([fx,tx],[fy,ty])
         seg_len = dist_from_start[i] - dist_from_start[i-1]
         line_segs.append(seg_len)
         x_segs.append(xobj['oxs'][i-1] - tx)
         ms.append(tm)
         bs.append(tb)

      else:
         line_segs.append(0)
         ms.append(0)
         bs.append(0)
   xobj['dist_from_start'] = dist_from_start
   xobj['line_segs'] = line_segs
   xobj['x_segs'] = x_segs
   xobj['ms'] = ms 
   xobj['bs'] = bs
   #del(xobj['crop_center_xs'])
   #del(xobj['crop_center_ys'])



   return(xobj)


def remove_bad_frames(obj):
   # frame bad if the intensity is negative really low 
   # frame bad if the line seg is way off from the med_seg_len
   print("REMOVE BAD!" )
   obj = calc_leg_segs(obj)
   new_fns, new_xs, new_ys, new_ws, new_hs, new_ints, new_lxs, new_lys,new_line_segs,new_dist_from_start = [],[],[],[],[],[],[],[],[],[]
   med_seg = np.median(obj['line_segs'])
   for i in range (0, len(obj['ofns'])-1):
      fn = obj['ofns'][i]
      x = obj['oxs'][i]
      y = obj['oys'][i]
      w = obj['ows'][i]
      h = obj['ohs'][i]
      ints = obj['oint'][i]
      lx = obj['leading_xs'][i]
      ly = obj['leading_ys'][i]
      line_seg = obj['line_segs'][i]
      dist_from_start = obj['dist_from_start'][i]
      if abs(line_seg - med_seg) > 2 or line_seg <= 0:
         bf = 1
      else:
         new_fns.append(fn)
         new_xs.append(x)
         new_ys.append(y)
         new_ws.append(w)
         new_hs.append(h)
         new_ints.append(ints)
         new_lxs.append(lx)
         new_lys.append(ly)
         new_line_segs.append(line_seg)
         new_dist_from_start.append(dist_from_start)
   obj['ofns'] = new_fns
   obj['oxs'] = new_xs 
   obj['oys'] = new_ys
   obj['ows'] = new_ws
   obj['ohs'] = new_hs
   obj['oint'] = new_ints
   obj['leading_xs'] = new_lxs
   obj['leading_ys'] = new_lys
   obj['line_segs'] = new_line_segs
   obj['dist_from_start'] = new_dist_from_start
   obj = analyze_object(obj)
      
   return(obj)
     
      
   

def crop_hd(obj, frame):
   hd_trim = obj['hd_trim']
   min_x, min_y,max_x,max_y = minmax_xy(obj)
   fx = int((min_x + max_x) / 2)
   fy = int((min_y + max_y) / 2)
   if max_x - min_x < 100 or max_y - min_y < 100:
      cx1,cy1,cx2,cy2= bound_cnt(fx,fy,frame.shape[1],frame.shape[0], 100)
   else:
      cx1,cy1,cx2,cy2= bound_cnt(fx,fy,frame.shape[1],frame.shape[0], 200)
   w = cx2 - cx1
   h = cy2 - cy1

   scale_x = 1920 / frame.shape[1]  
   scale_y = 1080 / frame.shape[0]  
   hd_x = int(cx1 * scale_x)
   hd_y = int(cy1 * scale_y)
   w = int(w * scale_x)
   h = int(h * scale_y)
 

   crop = "crop=" + str(w) + ":" + str(h) + ":" + str(hd_x) + ":" + str(hd_y)
   crop_out_file = hd_trim.replace(".mp4", "-crop.mp4")
   cmd = "/usr/bin/ffmpeg -i " + hd_trim + " -filter:v \"" + crop + "\" " + crop_out_file + " >/dev/null 2>&1"
   print(cmd)
   os.system(cmd)
   return(crop_out_file, (hd_x, hd_y, w, h))

    

def make_trim_clips(meteor_objects, video_file):
   trim_clips = []
   trim_starts = []
   trim_ends = []
   new_objs = []
   for obj in meteor_objects:
      start = obj['ofns'][0] - 25
      if start < 0:
         start = 0
      end = obj['ofns'][-1] + 25
      if end > 1499:
         end = 1499
      #print(obj['ofns'])
      # Run deeper detection on clip
      trim_clip, trim_start, trim_end = make_trim_clip(video_file, start, end)
      obj['trim_clip'] = trim_clip
      obj['trim_start'] = trim_start
      obj['trim_end'] = trim_end
      trim_clips.append(trim_clip)
      trim_starts.append(trim_start)
      trim_ends.append(trim_end)
      new_objs.append(obj)
   return(trim_clips, trim_starts, trim_ends,new_objs)


def make_trim_clip(video_file, start, end):
   outfile = video_file.replace(".mp4", "-trim-" + str(start) + ".mp4")
   cmd = "/usr/bin/ffmpeg -i " + video_file + " -vf select=\"between(n\," + str(start) + "\," + str(end) + "),setpts=PTS-STARTPTS\" " + outfile + " 2>&1 > /dev/null"
   print(cmd)
   if cfe(outfile) == 0:   
      print(cmd)
      os.system(cmd)
   return(outfile, start, end)

def scan_queue(cam):
   if cam != "a":
      wild = "*" + cam + ".mp4"
   else:
      wild = "*.mp4"
   queue_dir="/mnt/ams2/CAMS/queue/"
   files = sorted(glob.glob(queue_dir + wild ), reverse=True)
   fc = 0
   for video_file in files:
      stack_file = video_file.replace(".mp4", "-stacked.png")
      if cfe(stack_file) == 0 and "trim" not in video_file:
         quick_scan(video_file)
         #cmd = "./flex-detect.py qs " + video_file
         #print(cmd)
         #os.system(cmd)
         fc = fc + 1
      else:
         print("skipping")
   print("Finished scanning files", len(files))




def scan_old_meteor_dir(dir):
   files = glob.glob(dir + "*trim*.json" )
   print(dir + "*trim*.json" )
   print(files)
   for file in files:
      if "meteor.json" not in file and "fail.json" not in file and "reduced" not in file:
         print(file)
         jd = load_json_file(file)
         video_file = file.replace(".json", ".mp4")
         if cfe(video_file) == 1 and "archive_file" not in jd:
            debug(video_file)
         else:
            if cfe(jd['archive_file']) == 0:
               #quick_scan(video_file)
               debug(video_file)
            else:
               print("Done already.")

def find_clusters(points):

   data = np.array(points)
   data.reshape(-1, 1)
   db = DBSCAN(eps=10, min_samples=1).fit(data)
   labels = db.labels_
   return(labels)


def parse_file_data(input_file):
   el = input_file.split("/")
   fn = el[-1]
   try:
      good, bad = fn.split("-")
      ddd = good.split("_")
   except:
      good = fn.replace(".mp4", "")
      ddd = good.split("_")
   Y = ddd[0]
   M = ddd[1]
   D = ddd[2]
   H = ddd[3]
   MM = ddd[4]
   S = ddd[5]
   MS = ddd[6]
   CAM = ddd[7]
   extra = CAM.split("-")
   cam_id = extra[0]
   cam_id = cam_id.replace(".mp4", "")
   f_date_str = Y + "-" + M + "-" + D + " " + H + ":" + MM + ":" + S
   f_datetime = datetime.datetime.strptime(f_date_str, "%Y-%m-%d %H:%M:%S")
   return(f_datetime, cam_id, f_date_str,Y,M,D, H, MM, S)


def day_or_night(capture_date):

   device_lat = json_conf['site']['device_lat']
   device_lng = json_conf['site']['device_lng']

   obs = ephem.Observer()

   obs.pressure = 0
   obs.horizon = '-0:34'
   obs.lat = device_lat
   obs.lon = device_lng
   obs.date = capture_date

   sun = ephem.Sun()
   sun.compute(obs)

   (sun_alt, x,y) = str(sun.alt).split(":")

   saz = str(sun.az)
   (sun_az, x,y) = saz.split(":")
   if int(sun_alt) < 10:
      sun_status = "night"
   else:
      sun_status = "day"

   return(sun_status)


def convert_filename_to_date_cam(file):
   el = file.split("/")
   filename = el[-1]
   if "trim" in filename:
      filename, xxx = filename.split("-")[:2]
   filename = filename.replace(".mp4" ,"")

   data = filename.split("_")
   fy,fm,fd,fh,fmin,fs,fms,cam = data[:8]
   f_date_str = fy + "-" + fm + "-" + fd + " " + fh + ":" + fmin + ":" + fs
   f_datetime = datetime.datetime.strptime(f_date_str, "%Y-%m-%d %H:%M:%S")
   if "-" in cam:
      cel = cam.split("-")
      cam = cel[0]


   return(f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs)


def ffprobe(video_file):
   default = [704,576]
   cmd = "/usr/bin/ffprobe " + video_file + " > /tmp/ffprobe69.txt 2>&1"
   output = subprocess.check_output(cmd, shell=True).decode("utf-8")
   #try:
   #time.sleep(2)
   output = None
   if True:
      fpp = open("/tmp/ffprobe69.txt", "r")
      for line in fpp:
         if "Stream" in line:
            output = line
      fpp.close() 
      #print("OUTPUT: ", output)
      if output is None:
         print("FFPROBE PROBLEM:", video_file)
         exit()

      el = output.split(",")
      dim = el[3].replace(" ", "")
      w, h = dim.split("x") 
   return(w,h)

def check_running_proc():
   cmd = "ps -aux |grep \"process_data.py\" | grep -v grep"
   output = subprocess.check_output(cmd, shell=True).decode("utf-8")
   print(output)
   cmd = "ps -aux |grep \"process_data.py\" | grep -v grep | wc -l"
   output = subprocess.check_output(cmd, shell=True).decode("utf-8")
   output = int(output.replace("\n", ""))
   return(output)

def batch_quick():

   sd_video_dir = "/mnt/ams2/test/"

   #files = glob.glob(sd_video_dir + "/*SD.mp4")
   files = glob.glob(sd_video_dir + "/*.mp4")
   cc = 0
   files = sorted(files, reverse=True)
   for file in sorted(files, reverse=True):
      png = file.replace(".mp4", "-stacked.png")
      if cfe(png) == 0:
         (f_datetime, cam_id, f_date_str,fy,fmin,fd,fh, fm, fs) = parse_file_data(file)
         sun_status = day_or_night(f_date_str)
         cur_time = int(time.time())
         st = os.stat(file)
         size = st.st_size
         mtime = st.st_mtime
         tdiff = cur_time - mtime
         tdiff = tdiff / 60
         sun_status = day_or_night(f_date_str)
         print("TDIFF: ", tdiff, sun_status)
         if (tdiff > 3):
            if (sun_status == 'day'):
               print("Running:", file)
               quick_scan(file)
            else:
               print("Running:", file)
               quick_scan(file)
      else:
         print("already done.")


def remaster_arc(video_file):
   if "HD" in video_file: 
      json_file = video_file.replace("-HD.mp4", ".json")
   else:
      json_file = video_file.replace("-SD.mp4", ".json")
   out_file = video_file.replace(".mp4", "-pub.mp4")
   jd = load_json_file(json_file)
   frames,color_frames,subframes,sum_vals,max_vals,pos_vals = load_frames_fast(video_file, json_conf, 0, 0, [], 1,[])
   fds = jd['frames']
   meteor_obj = {}
   meteor_obj['oxs'] = []
   meteor_obj['oys'] = []
   for fd in fds:
      meteor_obj['oxs'].append(fd['x'])
      meteor_obj['oys'].append(fd['y'])
   remaster(color_frames,out_file,json_conf['site']['ams_id'], meteor_obj)

def remaster(frames, marked_video_file, station,meteor_object): 
   new_frames = []
   radiant = False
   fx = meteor_object['oxs'][0]
   fy = meteor_object['oys'][0]
   ax = np.mean(meteor_object['oxs'])
   ay = np.mean(meteor_object['oys'])

   cx1,cy1,cx2,cy2= bound_cnt(ax,ay,frames[0].shape[1],frames[0].shape[0], 100)
   #hdm_x = 1920 / 1280 
   #hdm_y = 1080 / 720
   hdm_x = 1
   hdm_y = 1
   cx1,cy1,cx2,cy2= int(cx1/hdm_x),int(cy1/hdm_y),int(cx2/hdm_x),int(cy2/hdm_y) 
   if "extra_logo" in json_conf['site']:
      logo_file = json_conf['site']['extra_logo']
      extra_logo = cv2.imread(logo_file, cv2.IMREAD_UNCHANGED)
   else:
      extra_logo = False
   #Get Date & time
   (hd_datetime, cam, sd_date, sd_y, sd_m, sd_d, sd_h, sd_M, sd_s) = convert_filename_to_date_cam(video_file)

   # Get Stations id & Cam Id to display
   station_id = station + "-" + cam
   station_id = station_id.upper()

   # Video Dimensions = as the first frame
   ih, iw = frames[0].shape[:2]
   start_sec = 0
   start_frame_time = hd_datetime + datetime.timedelta(0,start_sec)



   ams_logo = cv2.imread(AMS_WATERMARK, cv2.IMREAD_UNCHANGED)
   ams_logo_pos = "tl"
   if "extra_text" in json_conf['site']:
      extra_text = json_conf['site']['extra_text']
   extra_text_pos = "bl"
   date_time_pos = "br"
   extra_logo_pos = "tr"
   fc = 0
   for frame in frames:

      frame_sec = fc / FPS_HD
      frame_time = start_frame_time + datetime.timedelta(0,frame_sec)
      frame_time_str = frame_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
      fn = str(fc)
      hd_img = frame

      # Fading the box
      color = 150 - fc * 3
      if color > 50:
         cv2.rectangle(hd_img, (cx1, cy1), (cx2, cy2), (color,color,color), 1, cv2.LINE_AA)

      # Add AMS Logo
      hd_img = add_overlay_cv(hd_img, ams_logo, ams_logo_pos)

      # Add Eventual Extra Logo
      if(extra_logo is not False and extra_logo is not None):
         print("EXTRA:", extra_logo_pos) 
         hd_img = add_overlay_cv(hd_img,extra_logo,extra_logo_pos)

      # Add Date & Time
      frame_time_str = station_id + ' - ' + frame_time_str + ' UT'
      hd_img,xx,yy,ww,hh = add_text_to_pos(hd_img,frame_time_str,date_time_pos,2) #extra_text_pos => bl?

      # Add Extra_info
      if(extra_text is not False):
         hd_img,xx,yy,ww,hh = add_text_to_pos(hd_img,extra_text,extra_text_pos,2,True)  #extra_text_pos => br?

      # Add Radiant
      if(radiant is not False):
         if hd_img.shape[0] == 720 :
            rad_x = int(rad_x * .66666)
            rad_y = int(rad_y * .66666)
         hd_img = add_radiant_cv(radiant_image,hd_img,rad_x,rad_y,rad_name)

      new_frames.append(hd_img)
      fc = fc + 1

   make_movie_from_frames(new_frames, [0,len(new_frames) - 1], marked_video_file, 1)
   print('OUTPUT ' + marked_video_file )

def find_blob_center(fn, frame,bx,by,size,x_dir_mod,y_dir_mod):
   cx1,cy1,cx2,cy2= bound_cnt(bx,by,frame.shape[1],frame.shape[0],size)
   cnt_img = frame[cy1:cy2,cx1:cx2]
   min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(cnt_img)
   px_diff = max_val - min_val
   if px_diff < 10:
      #thresh_val = np.mean(cnt_img) - 5
      thresh_val = max_val - 10 
   else:
      thresh_val = max_val - int(px_diff /2)
   _ , thresh_img = cv2.threshold(cnt_img.copy(), thresh_val, 255, cv2.THRESH_BINARY)
   cnt_res = cv2.findContours(thresh_img.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
   if len(cnt_res) == 3:
      (_, cnts, xx) = cnt_res
   elif len(cnt_res) == 2:
      (cnts, xx) = cnt_res
   pos_cnts = []
   if len(cnts) > 3:
      # Too many cnts be more restrictive!
      thresh_val = max_val - int(px_diff /4)
      _ , thresh_img = cv2.threshold(cnt_img.copy(), thresh_val, 255, cv2.THRESH_BINARY)
      cnt_res = cv2.findContours(thresh_img.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
      if len(cnt_res) == 3:
         (_, cnts, xx) = cnt_res
      elif len(cnt_res) == 2:
         (cnts, xx) = cnt_res

   if len(cnts) > 0:
      for (i,c) in enumerate(cnts):
         x,y,w,h = cv2.boundingRect(cnts[i])
         if w > 1 or h > 1:
            size = w + h
            mx = int(x + (w / 2))
            my = int(y + (h / 2))
            cv2.rectangle(thresh_img, (x, y), (x+w, x+h), (255,255,255), 1, cv2.LINE_AA)
            pos_cnts.append((x,y,w,h,size,mx,my))
      if x_dir_mod == 1:
         temp = sorted(pos_cnts, key=lambda x: x[1], reverse=False)
      else:
         temp = sorted(pos_cnts, key=lambda x: x[1], reverse=True)
      if len(temp) > 0:
         (x,y,w,h,size,mx,my) = temp[0]
         min_val, max_val, min_loc, (bmx,bmy)= cv2.minMaxLoc(cnt_img)
         #blob_x = mx + cx1
         #blob_y = my + cy1
         blob_x = int(x + (w/2)) + cx1
         blob_y = int(y + (h/2)) + cy1
         max_px = max_val
         blob_w = w
         blob_h = h
         show_cnt = cnt_img.copy()
         desc = str(fn)
         cv2.putText(thresh_img, desc,  (3,10), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
         cv2.circle(thresh_img,(mx,my), 1, (255,255,255), 1)
         return(int(blob_x), int(blob_y),max_val,int(blob_w),int(blob_h))
      else:
         desc = str(fn) + "NF!"
         cv2.putText(thresh_img, desc,  (3,10), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
         return(int(bx), int(by),max_val,10,10)



# Add text over background
# WARNING: bg is NOT a cv image but a full path (for PIL)
# Position = br, bl, tr, tl (ex: br = bottom right)
# and line_number that corresponds to the # of the line to write
# ex: if line_number = 1 => first line at this position
#                    = 2 => second line at this position
# return updated cv matrix
def add_text_to_pos(background,text,position,line_number=1,bold=False):

    # Convert background to RGB (OpenCV uses BGR)
    cv2_background_rgb = cv2.cvtColor(background,cv2.COLOR_BGR2RGB)

    # Pass the image to PIL
    pil_im = Image.fromarray(cv2_background_rgb)
    draw = ImageDraw.Draw(pil_im)

    # use DEFAULT truetype font
    if(bold==True):
        font = ImageFont.truetype(VIDEO_FONT_BOLD, VIDEO_FONT_SIZE)
    else:
        font = ImageFont.truetype(VIDEO_FONT, VIDEO_FONT_SIZE)

    # Get Text position - see lib.Video_Tools_cv_lib
    y,x,w,h = get_text_position_cv(background,text,position,line_number,font)

    # Draw the text
    draw.text((x, y), text, font=font)

    # Get back the image to OpenCV
    cv2_im_processed = cv2.cvtColor(np.array(pil_im), cv2.COLOR_RGB2BGR)

    # We now return the image AND the box position of the text
    # so we can check if the meteors flies behind the text
    return cv2_im_processed,y,x,w,h


# Add semi-transparent overlay over background on x,y
# return updated cv matrix
def add_overlay_x_y_cv(background, overlay, x, y):

    background_width,background_height  = background.shape[1], background.shape[0]

    if x >= background_width or y >= background_height:
        return background

    h, w = overlay.shape[0], overlay.shape[1]

    if x + w > background_width:
        w = background_width - x
        overlay = overlay[:, :w]

    if y + h > background_height:
        h = background_height - y
        overlay = overlay[:h]

    if overlay.shape[2] < 4:
        overlay = np.concatenate(
            [
                overlay,
                np.ones((overlay.shape[0], overlay.shape[1], 1), dtype = overlay.dtype) * 255
            ],
            axis = 2,
        )

    overlay_image = overlay[..., :3]
    mask = overlay[..., 3:] / 255.0

    background[y:y+h, x:x+w] = (1.0 - mask) * background[y:y+h, x:x+w] + mask * overlay_image

    return background


# Add semi-transparent overlay over background
# Position = br, bl, tr, tl (ex: br = bottom right)
# return updated cv matrix
#def add_overlay_cv(background, overlay, position):
#    background_width,background_height  = background.shape[1], background.shape[0]
#    # Get overlay position - see lib.Video_Tools_cv_lib
#    #x,y = get_overlay_position_cv(background,overlay,position)
#    x = 5
#    y = 5
#    return add_overlay_x_y_cv(background, overlay, x, y)


# Add radiant to a frame
def add_radiant_cv(radiant_image,background,x,y,text):

    # Add Image if possible (inside the main frame)
    try:
        background = add_overlay_x_y_cv(background,radiant_image,x-int(radiant_image.shape[1]/2),y-int(radiant_image.shape[0]/2))
    except:
        background = background

    # Add text (centered bottom)
    background = add_text(background,text,x,y+int(radiant_image.shape[1]/2),True)

    return background




def load_json_conf(station_id):
   try:
      json_conf = load_json_file(ARCHIVE_DIR + station_id + "/CONF/as6.json")
   except:
      json_conf = load_json_file("/home/ams/amscams/conf/as6.json")
   return(json_conf)


def get_cal_params(input_file, station_id):
   if "png" in input_file:
      input_file = input_file.replace(".png", ".mp4")
   if "json" in input_file:
      input_file = input_file.replace(".json", ".mp4")
   (f_datetime, cam_id, f_date_str,Y,M,D, H, MM, S) = better_parse_file_date(input_file)

   # find all cal files from his cam for the same night
   matches = find_matching_cal_files(station_id, cam_id, f_datetime)
   if len(matches) > 0:
      return(matches)
   else:
      return(None)

def find_matching_cal_files(station_id, cam_id, capture_date, user_station):
   matches = []
   if user_station is None:
      cal_dir = "/mnt/ams2/cal/freecal/*"
   else:
      cal_dir = "/mnt/archive.allsky.tv/" + user_station + "/CAL/freecal/*"
   all_files = glob.glob(cal_dir)
   print("CAL DIR IS:", cal_dir)
   for cal_dir in all_files:
      if cam_id in cal_dir:
         if cfe(cal_dir, 1) == 1:
            cfs = glob.glob(cal_dir + "/*cal*.json") 
            if len(cfs) > 0: 
               print("FOUND:", cfs[0])
               matches.append(cfs[0])

   td_sorted_matches = []

   for match in matches:
      (t_datetime, cam_id, f_date_str,Y,M,D, H, MM, S) = better_parse_file_date(match)
      tdiff = abs((capture_date-t_datetime).total_seconds())
      td_sorted_matches.append((match,f_date_str,tdiff))

   temp = sorted(td_sorted_matches, key=lambda x: x[2], reverse=False)

   return(temp)

def get_station_id(video_file):
   tmp = video_file.split("/")
   for t in tmp:
      if "AMS" in t:
         station_id = t 
         return(station_id)
   else:
      return("AMS1")

def find_contours_in_frame(frame, thresh=25 ):
   contours = [] 
   result = []
   _, threshold = cv2.threshold(frame.copy(), thresh, 255, cv2.THRESH_BINARY)
   thresh_obj = cv2.dilate(threshold.copy(), None , iterations=4)
   threshold = cv2.convertScaleAbs(thresh_obj)
   cnt_res = cv2.findContours(threshold.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
   if len(cnt_res) == 3:
      (_, cnts, xx) = cnt_res
   elif len(cnt_res) == 2:
      (cnts, xx) = cnt_res
   show_frame = cv2.resize(threshold, (0,0),fx=.5, fy=.5)
   if len(cnts) > 20:
      print("RECT TOO MANY CNTS INCREASE THRESH!", len(cnts))
      thresh = thresh +5 
      _, threshold = cv2.threshold(frame.copy(), thresh, 255, cv2.THRESH_BINARY)
      thresh_obj = cv2.dilate(threshold.copy(), None , iterations=4)
      threshold = cv2.convertScaleAbs(thresh_obj)
      cnt_res = cv2.findContours(threshold.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

      if len(cnt_res) == 3:
         (_, cnts, xx) = cnt_res
      elif len(cnt_res) == 2:
         (cnts, xx) = cnt_res

   # now of these contours, remove any that are too small or don't have a recognizable blob
   # or have a px_diff that is too small

   rects = []
   recs = []
   if len(cnts) < 50:
      for (i,c) in enumerate(cnts):
         px_diff = 0

         x,y,w,h = cv2.boundingRect(cnts[i])
        

         if w > 1 or h > 1 and (x > 0 and y > 0):

            cnt_frame = frame[y:y+h, x:x+w]
            min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(cnt_frame)
            avg_val = np.mean(cnt_frame)
            if max_val - avg_val > 5 and (x > 0 and y > 0):
               rects.append([x,y,x+w,y+h])
               contours.append([x,y,w,h])

   #rects = np.array(rects)



   if len(rects) > 2:
      #print("RECT TOTAL CNT RECS:", len(rects))
      recs, weights = cv2.groupRectangles(rects, 0, .05)
      rc = 0
      #print("TOTAL RECT GROUPS:", len(recs))
      for res in recs:
         #print("RECT RESULT:", rc, res)
         rc = rc + 1

   #cv2.imshow("pepe", threshold)
   #cv2.waitKey(0)

   return(contours, recs)

def fast_bp_detect(gray_frames, video_file):
   subframes = []
   frame_data = []
   objects = {}
   np_imgs = np.asarray(gray_frames[0:50])
   median_frame = cv2.convertScaleAbs(np.median(np.array(np_imgs), axis=0))
   for sf in subframes:
      print(sf.shape)
   median_cnts,rects = find_contours_in_frame(median_frame, 100)
   mask_points = []
   for x,y,w,h in median_cnts:
      mask_points.append((x,y))
   #median_frame = mask_frame(median_frame, mask_points, [], 5)
   fc = 0
   last_frame = median_frame

   for frame in gray_frames:
      frame = mask_frame(frame, mask_points, [], 5)
      subframe = cv2.subtract(frame, last_frame)
      sum_val =cv2.sumElems(subframe)[0]

      frame_data.append(sum_val)
      subframes.append(subframe)
      last_frame = frame
      fc = fc + 1
   return(frame_data, subframes) 


def bp_detect( gray_frames, video_file):
   objects = {}
   mean_max = []
   subframes = []
   mean_max_avg = None
   frame_data = {}
   fn = 0
   last_frame = None

   np_imgs = np.asarray(gray_frames[0:50])
   median_frame = cv2.convertScaleAbs(np.median(np.array(np_imgs), axis=0))
   median_cnts,rects = find_contours_in_frame(median_frame, 100)
   mask_points = []
   for x,y,w,h in median_cnts:
      mask_points.append((x,y))
   #median_frame = mask_frame(median_frame, mask_points, [], 5)

   sum_vals = []
   running_sum = 0
   
 
   for frame in gray_frames:
      # Good place to save these frames for final analysis visual
      frame = mask_frame(frame, mask_points, [], 5)

      #if fn > 100 and fn % 50 == 0:
      #   np_imgs = np.asarray(gray_frames[fn-100:fn-50])
      #   running_sum = np.median(sum_vals[:-100])
      #   median_frame = cv2.convertScaleAbs(np.median(np.array(np_imgs), axis=0))

      if last_frame is None:
         last_frame = frame

      #extra_meteor_sec = int(fn) / 25


      frame_data[fn] = {}
      frame_data[fn]['fn'] = fn

      #medless_frame = cv2.subtract(frame, median_frame)

      subframe = cv2.subtract(frame,last_frame)
      #thresh = 10
      #_, threshold = cv2.threshold(subframe.copy(), thresh, 255, cv2.THRESH_BINARY)

      subframes.append(subframe)

      sum_val = np.sum(subframe)
      sum_vals.append(sum_val)

      if False:
         contours,rects = find_contours_in_frame(subframe)     
         if len(contours) > 0:
            for ct in contours:
               object, objects = find_object(objects, fn,ct[0], ct[1], ct[2], ct[3])
      else:
         contours = []
 
      #min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(subframe)

      frame_data[fn]['sum_val'] = float(sum_val)
      frame_data[fn]['contours'] = contours
      last_frame = frame
      fn = fn + 1


   return(frame_data, subframes, objects) 

def detect_motion_in_frames(subframes, video_file, fn):
   cnt_frames = {} 
   if len(subframes) == 0:
      return(cnt_frames)

   median_subframe = cv2.convertScaleAbs(np.median(np.array(subframes), axis=0))

   
   image_acc = np.empty(np.shape(subframes[0]))
  
   if len(image_acc.shape) > 2:
      image_acc = cv2.cvtColor(image_acc, cv2.COLOR_BGR2GRAY)

   #fn = 0
   for frame in subframes:
      frame = cv2.subtract(frame, median_subframe)
      cnt_frames[fn] = {}
      cnt_frames[fn]['xs'] = []
      cnt_frames[fn]['ys'] = []
      cnt_frames[fn]['ws'] = []
      cnt_frames[fn]['hs'] = []
     # image_acc = cv2.convertScaleAbs(image_acc)
     # frame = cv2.convertScaleAbs(frame)
      image_acc = np.float32(image_acc)
      frame = np.float32(frame)
      blur_frame = cv2.GaussianBlur(frame, (7, 7), 0)

      alpha = .5

      if len(frame.shape) > 2:
         frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

      image_diff = cv2.absdiff(image_acc.astype(frame.dtype), blur_frame,)
      #print(frame.shape, image_acc.shape)
      hello = cv2.accumulateWeighted(blur_frame, image_acc, alpha)
      min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(blur_frame)
      avg_val = np.median(blur_frame)
      thresh = avg_val + (max_val/1.3)
      _, threshold = cv2.threshold(image_diff.copy(), thresh, 255, cv2.THRESH_BINARY)
      thresh_obj = cv2.dilate(threshold.copy(), None , iterations=4)
      thresh_obj = cv2.convertScaleAbs(thresh_obj)
      # save this for final view
      print("THRESH", thresh)

      cnt_res = cv2.findContours(thresh_obj.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
      if len(cnt_res) == 3:
         (_, cnts, xx) = cnt_res
      elif len(cnt_res) == 2:
         (cnts, xx) = cnt_res


      if len(cnts) < 50:
         for (i,c) in enumerate(cnts):
            px_diff = 0
            x,y,w,h = cv2.boundingRect(cnts[i])
            if w > 2 and h > 2:
               cnt_frames[fn]['xs'].append(x)
               cnt_frames[fn]['ys'].append(y)
               cnt_frames[fn]['ws'].append(w)
               cnt_frames[fn]['hs'].append(h)
      fn = fn + 1
   return(cnt_frames)

def detect_objects_by_motion(frames, fn) :
   image_acc = frames[0]
   for frame in frames:
      blur_frame = cv2.GaussianBlur(frame, (7, 7), 0)

      alpha = .5

      image_diff = cv2.absdiff(image_acc.astype(frame.dtype), blur_frame,)
      hello = cv2.accumulateWeighted(blur_frame, image_acc, alpha)
      thresh = 25
      _, threshold = cv2.threshold(image_diff.copy(), thresh, 255, cv2.THRESH_BINARY)

      thresh_obj = cv2.dilate(threshold.copy(), None , iterations=4)
      thresh_obj = cv2.convertScaleAbs(thresh_obj)
      cnt_res = cv2.findContours(thresh_obj.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
      if len(cnt_res) == 3:
         (_, cnts, xx) = cnt_res
      elif len(cnt_res) == 2:
         (cnts, xx) = cnt_res

      if len(cnts) < 50:
         for (i,c) in enumerate(cnts):
            px_diff = 0
            x,y,w,h = cv2.boundingRect(cnts[i])
            if w > 2 and h > 2:
               cnt_frames[fn]['xs'].append(x)
               cnt_frames[fn]['ys'].append(y)
               cnt_frames[fn]['ws'].append(w)
               cnt_frames[fn]['hs'].append(h)
      fn = fn + 1
   return(cnt_frames)

  
def find_cnt_objects(cnt_frame_data, objects):
   #objects = {}
   for fn in cnt_frame_data: 
      cnt_xs = cnt_frame_data[fn]['xs']
      cnt_ys = cnt_frame_data[fn]['ys']
      cnt_ws = cnt_frame_data[fn]['ws']
      cnt_hs = cnt_frame_data[fn]['hs']
      for i in  range(0, len(cnt_xs)):
         object, objects = find_object(objects, fn,cnt_xs[i], cnt_ys[i], cnt_ws[i], cnt_hs[i])
   return(objects)

def cnt_size_test(object):
   big = 0
   for i in range(0,len(object['ofns'])):
      w = object['ows'][i]
      h = object['ohs'][i]
      if w > 75 and h > 75:
         big = big + 1
   big_perc = big / len(object['ofns'])
   return(big_perc)



def analyze_object_final(object, hd=0, sd_multi=1):
   #return(object)
   id = object['obj_id']

   # make sure all of the frames belong to the same cluster
   points = []
   frames = []
   for i in range(0, len(object['oxs'])):
      frames.append((object['ofns'][i], object['ofns'][i]))

   frame_labels = find_clusters(frames)
   objects_by_label = {}
   i = 0
   for label in frame_labels:
      if label not in objects_by_label:
         objects_by_label[label] = {}
         objects_by_label[label]['ofns'] = []
         objects_by_label[label]['oxs'] = []
         objects_by_label[label]['oys'] = []
         objects_by_label[label]['ows'] = []
         objects_by_label[label]['ohs'] = []
      objects_by_label[label]['obj_id'] = id
      objects_by_label[label]['ofns'].append(object['ofns'][i])
      objects_by_label[label]['oxs'].append(object['oxs'][i])
      objects_by_label[label]['oys'].append(object['oys'][i])
      objects_by_label[label]['ows'].append(object['ows'][i])
      objects_by_label[label]['ohs'].append(object['ohs'][i])
      i = i + 1     


   if len(objects_by_label) == 1:
      # there is only one cluster of frames so we are good. 
      object = analyze_object(object, hd, sd_multi)
      return(object)
   else:
      # there is more than one cluster of frames, so we need to remove the erroneous frames 
      most_frames = 0
      for label in objects_by_label :
         if len(objects_by_label[label]['ofns']) > most_frames:
            most_frames = len(objects_by_label[label]['ofns'])
            best_label = label
   
   # update the object to include only data items from the best label (cluster)
   object['obj_id'] = objects_by_label[best_label]['obj_id'] 
   object['ofns'] = objects_by_label[best_label]['ofns']
   object['oxs'] = objects_by_label[best_label]['oxs']
   object['oys'] = objects_by_label[best_label]['oys']
   object['ows'] = objects_by_label[best_label]['ows']
   object['ohs'] = objects_by_label[best_label]['ohs']



   object = analyze_object(object, hd, sd_multi, 1)
   return(object)

def remove_bad_frames_from_object(object,frames,subframes ):
   stacked_frame = stack_frames_fast(frames)
   stacked_frame = cv2.cvtColor(stacked_frame,cv2.COLOR_GRAY2RGB)

   line_segs = []
   x_segs = []
   y_segs = []
   dist_from_start = []
   ms = []
   bs = []

   ff = object['ofns'][0] 
   lf = object['ofns'][-1] 
   fx = object['oxs'][0] 
   fy = object['oys'][0] 
   m,b = best_fit_slope_and_intercept(object['oxs'],object['oys'])

   x_dir_mod,y_dir_mod = meteor_dir(object['oxs'][0], object['oys'][0], object['oxs'][-1], object['oys'][-1])

  
   #est_x = int(fx + x_dir_mod * (med_seg_len*fcc))
 

   # find distance from start point for each frame
   # turn that into seg_dist for each frame
   for i in range(0, len(object['ofns'])):
      tx = object['oxs'][i]
      ty = object['oys'][i]
      dist = calc_dist((fx,fy),(tx,ty))
      dist_from_start.append(dist)
      if i > 0 and i < len(object['ofns']):
         tm,tb = best_fit_slope_and_intercept([fx,tx],[fy,ty])
         seg_len = dist_from_start[i] - dist_from_start[i-1] 
         line_segs.append(seg_len)
         x_segs.append(object['oxs'][i-1] - tx)
         ms.append(tm)
         bs.append(tb)
      
      else:
         line_segs.append(9999)
         ms.append(9999)
         bs.append(9999)
        

   med_seg_len = np.median(line_segs)
   med_x_seg_len = np.median(x_segs)
   acl_poly = 0
   med_m = np.median(ms)
   med_b = np.median(bs)

   #print("BS:", np.median(bs),bs)
   est_xs = []
   est_ys = []

   for i in range(0, len(object['ofns'])):
      tx = object['oxs'][i]
      ty = object['oys'][i]
      if i > 0: 
         est_x = int((fx + (x_dir_mod) * (med_x_seg_len*i)) + acl_poly * i)
         est_y = int((m*est_x)+b)
         print("EST:", est_x,est_y)
         est_xs.append(est_x)
         est_ys.append(est_y)
      else:
         est_x = tx
         est_y = ty
         est_xs.append(est_x)
         est_ys.append(est_y)

   object['est_xs'] = est_xs
   object['est_ys'] = est_ys
   show_frame = stacked_frame.copy()
   scx = 2
   scy = 2
   show_frame = cv2.resize(show_frame, (0,0),fx=scx, fy=scy)
   new_oxs = []
   new_oys = []
   res_xs = []
   res_ys = []
   res_tot = []
   cl = 255
   for i in range(0, len(object['oxs'])):
      res_x = abs(object['oxs'][i] - object['est_xs'][i])
      res_y = abs(object['oys'][i] - object['est_ys'][i])
      res_xs.append(res_x)
      res_ys.append(res_y)
      res_tot.append(res_x + res_y)
      if res_x + res_y >= 4:
         show_frame[object['oys'][i]*scy,object['oxs'][i]*scx] = (0,0,cl)
         show_frame[object['est_ys'][i]*scy,object['est_xs'][i]*scx] = (cl,cl,0)
         cv2.line(show_frame, ((object['oxs'][i]*scx)-1,(object['oys'][i]*scy)-1), ((object['est_xs'][i]*scx)-1,(object['est_ys'][i]*scy)-1), (128,128,128), 1) 
         #cv2.circle(show_frame,(object['oxs'][i],object['oys'][i]), 5, (0,0,cl), 1)
         new_oxs.append(object['est_xs'][i])
         new_oys.append(object['est_ys'][i])
      else:
         show_frame[object['oys'][i]*scy,object['oxs'][i]*scx] = (0,cl,0)
         show_frame[object['est_ys'][i]*scy,object['est_xs'][i]*scx] = (0,cl,cl)
         new_oxs.append(object['oxs'][i])
         new_oys.append(object['oys'][i])
         #cv2.circle(show_frame,(object['oxs'][i],object['oys'][i]), 5, (0,cl,0), 1)
         #cv2.circle(show_frame,(object['est_xs'][i],object['est_ys'][i]), 5, (0,cl,cl), 1)
      #cv2.line(show_frame, (object['est_xs'][i], object['est_ys'][i]), (object['est_xs'][i]-10,object['est_ys'][i]), (128,128,128), 1) 
      #cv2.line(show_frame, (object['oxs'][i], object['oys'][i]), (object['oxs'][i]+10,object['oys'][i]), (128,128,128), 1) 
      cl = cl - 10
   print("RES X:", res_xs)
   print("RES Y:", res_ys)
   print("RES TOTAL:", res_tot)
   show_frame = stacked_frame.copy()
   show_frame = cv2.resize(show_frame, (0,0),fx=scx, fy=scy)
   for i in range(0, len(new_oxs) -1):
      x = new_oxs[i]
      y = new_oys[i]
      fn = object['ofns'][i]
      show_frame = frames[fn].copy()
      show_frame = cv2.resize(show_frame, (0,0),fx=scx, fy=scy)
      show_frame = cv2.cvtColor(show_frame,cv2.COLOR_GRAY2RGB)
      show_frame[y*scy,x*scx] = (0,cl,0)

   test_object = object
   test_object['oxs'] = new_oxs
   test_object['oys'] = new_oys
     
   calc_point_res(test_object,frames) 
   return(object)
   
def calc_point_res(object, frames):
   scx = 2
   scy = 2
   line_segs = []
   x_segs = []
   y_segs = []
   dist_from_start = []
   ms = []
   bs = []

   ff = object['ofns'][0]
   lf = object['ofns'][-1]
   fx = object['oxs'][0]
   fy = object['oys'][0]
   m,b = best_fit_slope_and_intercept(object['oxs'],object['oys'])

   x_dir_mod,y_dir_mod = meteor_dir(object['oxs'][0], object['oys'][0], object['oxs'][-1], object['oys'][-1])

 
   #est_x = int(fx + x_dir_mod * (med_seg_len*fcc))


   # find distance from start point for each frame
   # turn that into seg_dist for each frame
   for i in range(0, len(object['ofns'])):
      tx = object['oxs'][i]
      ty = object['oys'][i]
      dist = calc_dist((fx,fy),(tx,ty))
      dist_from_start.append(dist)
      if i > 0 and i < len(object['ofns']):
         tm,tb = best_fit_slope_and_intercept([fx,tx],[fy,ty])
         seg_len = dist_from_start[i] - dist_from_start[i-1]
         line_segs.append(seg_len)
         x_segs.append(object['oxs'][i-1] -tx)
         ms.append(tm)
         bs.append(tb)

      else:
         line_segs.append(9999)
         ms.append(9999)
         bs.append(9999)

   med_seg_len = np.median(line_segs)
   med_x_seg_len = np.median(x_segs)
   if med_x_seg_len == 0:
      med_x_seg_len = np.mean(x_segs)

   acl_poly = 0
   med_m = np.median(ms)
   med_b = np.median(bs)
   est_xs = []
   est_ys = []
   res_xs = []
   res_ys = []
   res_tot = []
   cl = 255

   for i in range(0, len(object['ofns'])):
      tx = object['oxs'][i]
      ty = object['oys'][i]
      fn = object['ofns'][i]
      if i > 0:
         est_x = int((fx + (x_dir_mod) * (med_x_seg_len*i)) + acl_poly * i)
         est_y = int((m*est_x)+b)
         print("M,B,EST_X:", m, b, est_x, i )
         print("EST INFO:", fx, x_dir_mod, med_x_seg_len, i )
         print("EST:", est_x,est_y)
         est_xs.append(est_x)
         est_ys.append(est_y)
      else:
         est_x = tx
         est_y = ty
         est_xs.append(est_x)
         est_ys.append(est_y)

      show_frame = frames[fn].copy()
      show_frame = cv2.resize(show_frame, (0,0),fx=scx, fy=scy)
      show_frame = cv2.cvtColor(show_frame,cv2.COLOR_GRAY2RGB)
      print(show_frame.shape)
      show_frame[ty*scy,tx*scx] = (0,cl,0)

      esx,esy = bound_point(est_x, est_y, show_frame)
      show_frame[esy,esx] = (0,cl,cl)


   for i in range(0, len(object['oxs'])):
      res_x = abs(object['oxs'][i] - object['est_xs'][i])
      res_y = abs(object['oys'][i] - object['est_ys'][i])
      res_xs.append(res_x)
      res_ys.append(res_y)
      res_tot.append(res_x + res_y)


   object['est_xs'] = est_xs
   object['est_ys'] = est_ys

   print(object)

   print("POLYFIT")
   import matplotlib
   import matplotlib.pyplot as plt

   poly_x = np.array(object['oxs'])
   poly_y = np.array(object['oys'])
   poly_est_x = np.array(object['est_xs'])

   print("POLY X:", poly_x)
   print("POLY Y:", poly_y)

   z = np.polyfit(poly_x,poly_y,1)
   f = np.poly1d(z)
   plt.axis('equal')

   #range(min(poly_x), max(poly_x)):
   new_ys = []

   #show_frame = frames[0] 
   show_frame = stack_frames_fast(frames)
   show_frame = cv2.cvtColor(show_frame,cv2.COLOR_GRAY2RGB)
   cc = 0
   for i in range(poly_x[0],poly_x[-1]):
      x = i
      y = int(f(i))
      #ox = x
      #oy = poly_y[cc]
      show_frame[y,x] = [0,0,255]
      new_ys.append(int(f(i)))
      cc = cc + 1
   for ox,oy in zip(poly_x, poly_y):
      show_frame[oy,ox] = [255,0,0]
   plt.plot(poly_x, poly_y, 'x')
   plt.plot(new_xs, new_ys, 'x')
   ax = plt.gca()
   ax.invert_yaxis()
   plt.show()

def poly_fit_check(poly_x,poly_y, x,y, z=None):
   if z is None:
      if len(poly_x) >= 3:
         try:
            z = np.polyfit(poly_x,poly_y,1)
            f = np.poly1d(z)
         except:
            return(0)

      else:
         return(0)
   #print("Z:", z)
   dist_to_line = distance((x,y),z)

   all_dist = []
   for i in range(0,len(poly_x)):
      ddd = distance((poly_x[i],poly_y[i]),z)
      all_dist.append(ddd)

   med_dist = np.median(all_dist)
   show = 0
   if show == 1:
      import matplotlib
      import matplotlib.pyplot as plt

      plt.plot(poly_x, poly_y, 'x')

      plt.axis('equal')
      trendpoly = np.poly1d(z)
      plt.plot(poly_x,trendpoly(poly_x))
      ax = plt.gca()
      ax.invert_yaxis()
      plt.show()



   return(dist_to_line, z, med_dist)

def poly_fit2(poly_x,poly_y):
   import matplotlib
   matplotlib.use('Agg')
   import matplotlib.pyplot as plt
   print("POLY:", len(poly_x), len(poly_y))

   if len(poly_x) > 5:
      try:
         z = np.polyfit(poly_x,poly_y,1)
         f = np.poly1d(z)
      except:
         return(0)

   else:
      return(0)


   new_ys = []
   new_xs = []

   cc = 0
   for i in range(poly_x[0],poly_x[-1]):
      #plt.plot(i, f(i), 'go')
      x = i
      y = int(f(i))
      new_ys.append(int(f(i)))
      new_xs.append(i)
      cc = cc + 1
   plt.plot(poly_x, poly_y, 'x')
   plt.plot(new_xs, new_ys, 'go')
   plt.axis('equal')
   #plt.xlim(0,704)
   #plt.ylim(0,576)
   trendpoly = np.poly1d(z)
   plt.plot(poly_x,trendpoly(poly_x))
   ax = plt.gca()
   ax.invert_yaxis()
   plt.show()
   line_res = []
   for i in range(0,len(poly_x)-1):
      px = poly_x[i]
      py = poly_y[i]
      dist_to_line = distance((px,py),z)
      line_res.append(dist_to_line)
   avg_line_res = np.mean(line_res)
   return(avg_line_res)


def poly_fit(object):
   #print("POLY FIT:", object['report'])
   import matplotlib
   matplotlib.use('Agg')
   import matplotlib.pyplot as plt

   poly_x = np.array(object['oxs'])
   poly_y = np.array(object['oys'])

   if len(poly_x) > 5:
      try:
         z = np.polyfit(poly_x,poly_y,1)
         f = np.poly1d(z)
      except:
         return(0)
        
   else:
      return(0)


   new_ys = []
   new_xs = []

   cc = 0
   for i in range(poly_x[0],poly_x[-1]):
      #plt.plot(i, f(i), 'go')
      x = i
      y = int(f(i))
      new_ys.append(int(f(i)))
      new_xs.append(i)
      cc = cc + 1
   plt.plot(poly_x, poly_y, 'x')
   plt.plot(new_xs, new_ys, 'go')
   plt.axis('equal')
   #plt.xlim(0,704)
   #plt.ylim(0,576)
   trendpoly = np.poly1d(z) 
   plt.plot(poly_x,trendpoly(poly_x))
   ax = plt.gca()
   ax.invert_yaxis()
   #plt.show()
   line_res = []
   for i in range(0,len(poly_x)-1):
      px = poly_x[i]
      py = poly_y[i]
      dist_to_line = distance((px,py),z)
      line_res.append(dist_to_line)
   avg_line_res = np.mean(line_res)
   return(avg_line_res)
      

def distance(point,coef):
    return abs((coef[0]*point[0])-point[1]+coef[1])/math.sqrt((coef[0]*coef[0])+1)



def bound_point(est_y, est_x, image):
   if True:
      if est_y < 0:
         est_y = 0
      else:
         est_y = est_y  
      if est_x < 0:
         esx = 0
      else:
         esx = est_x  
      if est_x > image.shape[1]:
         est_x = image.shape[1]
      if est_y > image.shape[0]:
         est_0 = image.shape[0]
   return(est_x, est_y)

def unq_points(object):
   points = {}
   tot = 0
   for i in range(0, len(object['oxs'])):
      x = object['oxs'][i]
      y = object['oys'][i]
      key = str(x) + "." + str(y)
      points[key] = 1
      tot = tot + 1

   unq_tot = len(points)
   perc = unq_tot / tot
   return(perc)


def big_cnt_test(object,hd=0):
   sizes = []
   big = 0
   sz_thresh = 20
   if hd == 1:
      sz_thresh = 40

   for i in range(0, len(object['ofns'])):
      w = object['ows'][i]
      h = object['ohs'][i]
      if w > sz_thresh:
         big += 1
      if h > sz_thresh:
         big += 1
      sizes.append(w)
      sizes.append(h)
   tot = len(sizes)
   if len(sizes) > 0:
      perc_big = big / len(sizes)
   return(perc_big)

  
def anal_int(ints):
   pos_vals = []
   neg_vals = []
   for int_val in ints:
      if int_val > 0:
         pos_vals.append(int_val)
      else:
         neg_vals.append(int_val)
   if len(neg_vals) > 0:
      pos_neg_perc = len(pos_vals) / len(neg_vals)
   else:
      pos_neg_perc = 0
   if len(pos_vals) == 0:
      return(0, 1, [])

   max_int = max(pos_vals)
   min_int = min(pos_vals)
   max_times = max_int / min_int
   perc_val = []
   for int_val in pos_vals:
      mxt = max_int / int_val
      perc_val.append(mxt)
   return(max_times, pos_neg_perc, perc_val)

def analyze_object(object, hd = 0, sd_multi = 1, final=0):
   # HD scale pix is .072 degrees per px
   # SD scale pix is .072 * sd_multi
   pix_scale = .072  # for HD

   if hd == 1:
      deg_multi = 1
      sd = 0
   else:
      deg_multi = 3 
      sd = 1


   bad_items = []

   xs = object['oxs']
   ys = object['oys']

   perc_big = big_cnt_test(object, hd)
   if "ofns" not in object:
      if "report" not in object:
         object['report'] = {}
         object['report']['meteor_yn'] = "no"
      else:
         object['report']['meteor_yn'] = "no"
      return(object)
   if len(object['ofns']) == 0:
      if "report" not in object:
         object['report'] = {}
         object['report']['meteor_yn'] = "no"
      else:
         object['report']['meteor_yn'] = "no"
      return(object)

   px_dist = calc_dist((min(xs),min(ys)), (max(xs),max(ys)))
   if px_dist < 4:
      if "report" not in object:
         object['report'] = {}
      object['report']['meteory_yn'] = "no"
      bad_items.append("Bad px dist" + str(px_dist))

   last_x = object['oxs'][-1]
   last_y = object['oys'][-1]
   last_fn = object['ofns'][-1]

   unq_perc = unq_points(object)
   if len(object['oxs']) >= 3 and unq_perc > .6:
      if len(object['oxs']) < 10:
         #print("START CALC LEG SEGS", object['oxs'])
         object = calc_leg_segs(object)
         #print("END CALC LEG SEGS")
   else:
      object['report'] = {}
      object['report']['meteor_yn'] = "no"
      object['report']['bad_items'] = ['not enough frames.']
      object['report']['obj_class'] = 'new'
      return(object)


   if len(object['ofns']) > 4:
      dir_test_perc = meteor_dir_test(object['oxs'],object['oys'])
   else:
      dir_test_perc = 0



   id = object['obj_id']
   meteor_yn = "Y"
   obj_class = "undefined"
   ff = object['ofns'][0] 
   lf = object['ofns'][-1] 
   elp = (lf - ff ) + 1
   xs = object['oxs']
   min_x = min(object['oxs'])
   max_x = max(object['oxs'])
   min_y = min(object['oys'])
   max_y = max(object['oys'])
   max_int = max(object['oint'])
   min_int = min(object['oint'])
   max_h = max(object['ohs'])
   max_w = max(object['ows'])
   #max_x = max_x + max_w
   #max_h = max_y + max_h

   int_max_times, int_neg_perc, int_perc_list = anal_int(object['oint'])

   med_int = float(np.median(object['oint']))
   intense_neg = 0
   for intense in object['oint']:
      if intense < 0:
         intense_neg = intense_neg + 1
   min_max_dist = calc_dist((min_x, min_y), (max_x,max_y))
   if len(object['ofns']) > 0:
      if final == 0:
          
         dist_per_elp = min_max_dist / len(object['ofns']) 
      else:
         if elp > 0:
            dist_per_elp = min_max_dist / elp
         else:
            dist_per_elp = 0
   else:
      dist_per_elp = 0

   #if len(object['ofns']) > 3 and perc_big >= .75 and len(object['ofns']) < 10:
   #   moving = "moving"
   #   meteor_yn = "no"
   #   obj_class = "car or object"
   #   bad_items.append("too many big percs")

   if elp > 5 and dist_per_elp < .1 :
      moving = "not moving"
      meteor_yn = "no"
      obj_class = "star"
      bad_items.append("too short and too slow")
   else:
      moving = "moving"
   if min_max_dist > 12 and dist_per_elp < .1:
      moving = "slow moving"
      meteor_yn = "no"
      obj_class = "plane"
      bad_items.append("too long and too slow")

   #cm
   fc = 0
   cm = 1
   max_cm = 1
   last_fn = None
   for fn in object['ofns']:
      if last_fn is not None:
         if last_fn + 1 == fn or last_fn + 2 == fn: 
            cm = cm + 1
            if cm > max_cm :
               max_cm = cm
      
      fc = fc + 1
      last_fn = fn
   if len(object['ofns']) > 1:
      x_dir_mod,y_dir_mod = meteor_dir(object['oxs'][0], object['oys'][0], object['oxs'][-1], object['oys'][-1])
   else:
      x_dir_mod = 0
      y_dir_mod = 0
   
   if len(object['ofns'])> 0:
      cm_to_len = max_cm / len(object['ofns'])
   else: 
      meteor_yn = "no"
      obj_class = "plane"
      bad_items.append("0 frames")
   if cm_to_len < .4:
      meteor_yn = "no"
      obj_class = "plane"
      bad_items.append("cm/len < .4.")

   if len(object['ofns']) >= 300:
      # if cm_to_len is acceptable then skip this. 
      if cm_to_len < .6:
         meteor_yn = "no"
         obj_class = "plane"
         bad_items.append("more than 300 frames in event and cm/len < .6.")



   # classify the object
 
   if max_cm <= 3 and elp > 5 and min_max_dist < 8 and dist_per_elp < .01:
      obj_class = "star"
   if elp > 5 and min_max_dist > 8 and dist_per_elp >= .01 and dist_per_elp < 1:
      obj_class = "plane"
   if elp > 300:
      meteor_yn = "no"
      bad_items.append("more than 300 frames in event.")
   if max_cm < 4:
      neg_perc = intense_neg / max_cm 
      if intense_neg / max_cm > .3:
         meteor_yn = "no" 
         bad_items.append("too much negative intensity for short event." + str(intense_neg))

   if max_cm > 0:
      neg_perc = intense_neg / max_cm 
      if intense_neg / max_cm > .5:
         meteor_yn = "no" 
         bad_items.append("too much negative intensity." + str(intense_neg))
   else:
      neg_perc = 0
   if elp < 2:
      meteor_yn = "no" 
      bad_items.append("less than 2 frames in event.")
   #if perc_big > .75 and len(object['ofns']) < 10:
   #   meteor_yn = "no"
   #   bad_items.append("too many big cnts." + str(perc_big))
   if max_cm < 3:
      meteor_yn = "no"
      bad_items.append("less than 2 consecutive motion.")
   if dist_per_elp > 5:
      meteor_yn = "Y"
   if med_int < 5 and med_int != 0:
      meteor_yn = "no"
      obj_class = "bird"
      bad_items.append("low or negative median intensity.")
   if dir_test_perc < .5 and dir_test_perc != 0 and elp > 10:
      #meteor_yn = "no"
      #obj_class = "noise"
      bad_items.append("direction test failed." + str(dir_test_perc))
   if unq_perc < .5:
      meteor_yn = "no"
      obj_class = "star or plane"
      bad_items.append("unique points test failed." + str(unq_perc))

   if max_cm > 0:
      elp_max_cm = elp / max_cm
      if elp / max_cm >2:
         obj_class = "plane"
         meteor_yn = "no"
         bad_items.append("elp to cm to high." + str(elp / max_cm))
   else:
      elp_max_cm = 0
   ang_vel = ((dist_per_elp * deg_multi) * pix_scale) * 25
   ang_dist = ((min_max_dist * deg_multi) * pix_scale) 

   if ang_dist < .2:
      meteor_yn = "no"
      bad_items.append("bad angular distance below .2.")
   if ang_vel < .9:
      meteor_yn = "no"
      bad_items.append("bad angular velocity below .9")

   if dir_test_perc < .6 and max_cm > 10:
      meteor_yn = "no"
      obj_class = "star"
      bad_items.append("dir test perc to low for this cm")

   if max_cm < 5 and elp_max_cm > 1.5 and neg_perc > 0:
      meteor_yn = "no"
      obj_class = "plane"
      bad_items.append("low max cm, high neg_perc, high elp_max_cm")

   if ang_vel < 1.5 and elp_max_cm > 2 and cm < 3:
      meteor_yn = "no"
      bad_items.append("short distance, many gaps, low cm")
      obj_class = "plane"


   if elp > 0:
      if min_max_dist * deg_multi < 1 and max_cm <= 3 and cm / elp < .75 :
         meteor_yn = "no"
         bad_items.append("short distance, many gaps, low cm")

   if meteor_yn == "Y" and final == 1:
      if max_cm > 0:
         elp_cm_perc = elp / max_cm
      else:
         elp_cm_perc = 0
      if elp_cm_perc < .5:
         meteor_yn = "no"
         obj_class = "plane"
         bad_items.append("to many elp frames compared to cm.")



   if len(bad_items) >= 1:
      meteor_yn = "no"
      if obj_class == 'meteor':
         obj_class = "not sure"

   if meteor_yn == "no":
      meteory_yn = "no"
   else: 
      meteory_yn = "Y"
      obj_class = "meteor"


   # create meteor 'like' score 
   score = 0
   if meteor_yn == "Y" and len(xs) > 5:
      avg_line_res = poly_fit(object) 
   else:
      avg_line_res = 0

   if avg_line_res > 13:
      meteor_yn = "no"
      obj_class = "noise"
      bad_items.append("bad average line res " + str(avg_line_res))

   if max_cm == elp == len(object['ofns']):
      score = score + 1
   if dir_test_perc == 2:
      score = score + 1
   if max_cm >= 5:
      score = score + 1
   if avg_line_res <= 1:
      score = score + 1
   if ang_vel > 2:
      score = score + 1
   if obj_class == "meteor":
      score = score + 5
   else:
      score = score - 3

   object['report'] = {}
  
   if meteor_yn == "Y": 
      print("possible meteor found", last_fn, last_x, last_y)


      class_rpt = classify_object(object, sd)
      object['report']['classify'] = class_rpt
      object['report']['meteor_yn'] = meteor_yn
  
      #object['report']['angular_sep_px'] = class_rpt['ang_sep_px'] 
      #object['report']['angular_vel_px'] = class_rpt['ang_vel_px']
      #object['report']['angular_sep'] = class_rpt['ang_sep_deg'] 
      #object['report']['angular_vel'] = class_rpt['ang_vel_deg']
      #object['report']['segs'] = class_rpt['segs']
      #object['report']['bad_seg_perc'] = class_rpt['bad_seg_perc']
      #object['report']['neg_int_perc'] = class_rpt['neg_int_perc']
      #object['report']['meteor_yn'] = class_rpt['meteor_yn'] 
      #object['report']['bad_items'] = class_rpt['bad_items'] 
   else: 
      object['report']['meteor_yn'] = meteor_yn

   object['report']['elp'] = elp
   object['report']['min_max_dist'] = min_max_dist
   object['report']['dist_per_elp'] = dist_per_elp
   object['report']['moving'] = moving
   object['report']['dir_test_perc'] = dir_test_perc
   object['report']['max_cm'] = max_cm
   object['report']['elp_max_cm'] = elp_max_cm
   object['report']['max_fns'] = len(object['ofns']) 
   object['report']['neg_perc'] = neg_perc
   object['report']['avg_line_res'] = avg_line_res 
   object['report']['obj_class'] = obj_class 
   object['report']['bad_items'] = bad_items 
   object['report']['x_dir_mod'] = x_dir_mod
   object['report']['y_dir_mod'] = y_dir_mod
   object['report']['score'] = score 

   return(object)

def calc_obj_dist(obj1, obj2):
   x1,y1,w1,h1 = obj1
   x2,y2,w2,h2 = obj2
   pts1 = []
   pts2 = []
   pts1.append((x1,y1))
   pts1.append((x1+w1,y1))
   pts1.append((x1,y1+h1))
   pts1.append((x1+w1,y1+h1))
   pts1.append((x1+int(w1/2),y1+int(h1/2)))

   pts2.append((x2,y2))
   pts2.append((x2+w2,y2))
   pts2.append((x2,y2+h2))
   pts2.append((x2+w2,y2+h2))
   pts2.append((x2+int(w2/2),y2+int(h2/2)))
   all_dist = []
   for a,b in pts1:
      for d,e in pts2:

         dist = calc_dist((a,b),(d,e))
         all_dist.append(dist)

   min_dist = min(all_dist)
   return(min_dist) 

def find_object(objects, fn, cnt_x, cnt_y, cnt_w, cnt_h, intensity=0, hd=0, sd_multi=1, cnt_img=None,classify=1):
   if hd == 1:
      obj_dist_thresh = 60
   else:
      obj_dist_thresh = 30 

   center_x = cnt_x 
   center_y = cnt_y  

   found = 0
   max_obj = 0
   for obj in objects:
      if 'oxs' in objects[obj]:
         ofns = objects[obj]['ofns']
         oxs = objects[obj]['oxs']
         oys = objects[obj]['oys']
         ows = objects[obj]['ows']
         ohs = objects[obj]['ohs']
         for oi in range(0, len(oxs)):
            hm = int(ohs[oi] / 2)
            wm = int(ows[oi] / 2)
            lfn = int(ofns[-1] )
            dist = calc_obj_dist((cnt_x,cnt_y,cnt_w,cnt_h),(oxs[oi], oys[oi], ows[oi], ohs[oi]))
            last_frame_diff = fn - lfn 
            if dist < obj_dist_thresh and last_frame_diff < 10:
               found = 1
               found_obj = obj
      if obj > max_obj:
         max_obj = obj
   if found == 0:
      obj_id = max_obj + 1
      objects[obj_id] = {}
      objects[obj_id]['obj_id'] = obj_id
      objects[obj_id]['ofns'] = []
      objects[obj_id]['oxs'] = []
      objects[obj_id]['oys'] = []
      objects[obj_id]['ows'] = []
      objects[obj_id]['ohs'] = []
      objects[obj_id]['oint'] = []
      objects[obj_id]['ofns'].append(fn)
      objects[obj_id]['oxs'].append(center_x)
      objects[obj_id]['oys'].append(center_y)
      objects[obj_id]['ows'].append(cnt_w)
      objects[obj_id]['ohs'].append(cnt_h)
      objects[obj_id]['oint'].append(intensity)
      found_obj = obj_id
   if found == 1:
      if "report" in objects[found_obj]:
         if True:
         #if objects[found_obj]['report']['obj_class'] == "meteor":
            # only add if the intensity is positive and the forward motion compared to the last highest FM is greater. 
            fm_last = calc_dist((objects[found_obj]['oxs'][0],objects[found_obj]['oys'][0]), (objects[found_obj]['oxs'][-1],objects[found_obj]['oys'][-1]))
            fm_this = calc_dist((objects[found_obj]['oxs'][0],objects[found_obj]['oys'][0]), (center_x, center_y))
            fm = fm_this - fm_last
            if intensity >= 0 and fm >= 0:
               objects[found_obj]['ofns'].append(fn)
               objects[found_obj]['oxs'].append(center_x)
               objects[found_obj]['oys'].append(center_y)
               objects[found_obj]['ows'].append(cnt_w)
               objects[found_obj]['ohs'].append(cnt_h)
               objects[found_obj]['oint'].append(intensity)

      else:
         objects[found_obj]['ofns'].append(fn)
         objects[found_obj]['oxs'].append(center_x)
         objects[found_obj]['oys'].append(center_y)
         objects[found_obj]['ows'].append(cnt_w)
         objects[found_obj]['ohs'].append(cnt_h)
         objects[found_obj]['oint'].append(intensity)

   unq_perc = unq_points(objects[found_obj])
   if classify ==1 :
      objects[found_obj] = analyze_object(objects[found_obj], hd, sd_multi, 1)

      if objects[found_obj]['report']['meteor_yn'] == 'Y':
         max_int = max(objects[found_obj]['oint'])
         if max_int > 25000:
            objects[found_obj]['report']['obj_class'] = "fireball"

   return(found_obj, objects)

def clean_object(obj):
   # Remove erroneous frames from end of object if they exist. 
   print("clean")

def meteor_dir_test(fxs,fys):
   fx = fxs[0]
   fy = fys[0]
   lx = fxs[-1]
   ly = fys[-1]
   fdir_x = lx - fx 
   fdir_y = ly - fy

   if fdir_x < 0:
      fx_dir_mod = 1
   else:
      fx_dir_mod = -1
   if fdir_y < 0:
      fy_dir_mod = 1
   else:
      fy_dir_mod = -1


   match = 0
   nomatch = 0

   for i in range(0,len(fxs)):
      x = fxs[i]
      y = fys[i]
      dir_x = x - fx 
      dir_y = y - fy
      if dir_x < 0:
         x_dir_mod = 1
      else:
         x_dir_mod = -1
      if dir_y < 0:
         y_dir_mod = 1
      else:
         y_dir_mod = -1

      if x_dir_mod == fx_dir_mod :
         match = match + 1
      else:
         nomatch = nomatch + 1

      if y_dir_mod == fy_dir_mod :
         match = match + 1
      else:
         nomatch = nomatch + 1

 
   if len(fxs) > 0: 
      perc = match / len(fxs)
   else:
      perc = 0
   return(perc)

def meteor_dir(fx,fy,lx,ly):
   # positive x means right to left (leading edge = lowest x value)
   # negative x means left to right (leading edge = greatest x value)
   # positive y means top to down (leading edge = greatest y value)
   # negative y means down to top (leading edge = lowest y value)
   dir_x = lx - fx 
   dir_y = ly - fy
   if dir_x < 0:
      x_dir_mod = 1
   else:
      x_dir_mod = -1
   if dir_y < 0:
      y_dir_mod = 1
   else:
      y_dir_mod = -1
   return(x_dir_mod, y_dir_mod)


def one_dir_test(object):
   last_x = None
   last_x_dir_mod = None
   first_x = object['oxs'][0]
   first_y = object['oys'][0]
   xerrs = 0
   yerrs = 0
   for i in range(0,len(object['oxs'])):
      fn = object['ofns'][i]
      x = object['oxs'][i]
      y = object['oys'][i]
      if last_x is not None:
         dir_x = first_x - x 
         dir_y = first_y - y
         if dir_x < 0:
            x_dir_mod = 1
         else:
            x_dir_mod = -1
         if dir_y < 0:
            y_dir_mod = 1
         else:
            y_dir_mod = -1
         if last_x_dir_mod is not None:
            if x_dir_mod != last_x_dir_mod:
               xerrs = xerrs + 1
            if y_dir_mod != last_y_dir_mod:
               yerrs = yerrs + 1

         last_x_dir_mod = x_dir_mod
         last_y_dir_mod = y_dir_mod
      last_x = x 
      last_y = y
   dir_mod_errs = xerrs + yerrs
   dir_mod_err_perc = dir_mod_errs / len(object['oxs'])
   if dir_mod_errs == 0:
      return(1)
   if dir_mod_err_perc > .2:
      return(0)
   else:
      return(1)

def dist_test(object):
   mn_x = min(object['oxs'])
   mn_y = min(object['oys'])
   mx_x = max(object['oxs'])
   mx_y = max(object['oys'])
   dist = calc_dist((mn_x, mn_y), (mx_x,mx_y))
   if dist < 5:
      return(0)
   else:
      return(1)

def gap_test(object):
   ofns = object['ofns']
   if "oid" in object:
      oid = object[oid]
   else:
      oid = "no object id"
   last_fn = None
   cons = 0
   gaps = 0
   gap_events = 0
   for fn in ofns:
      fn = int(fn)
      if last_fn is not None:

         if last_fn == fn:
            extra = 1
         elif last_fn + 1 == fn or last_fn + 2 == fn or last_fn + 3 == fn:
            cons = cons + 1
         else:
            gaps = gaps + (fn - last_fn)
            gap_events = gap_events + 1
      last_fn = fn
   elp_frames = int(ofns[-1]) - int(ofns[0])
   if cons > 0:
      gap_to_cm_ratio = gaps / cons
   else:
      gap_to_cm_ratio = 1


   if elp_frames > 0:
      gap_to_elp_ratio = gaps / elp_frames
   else:
      gap_to_elp_ratio = 1


   if cons < 3:
      #print("CONS MONTION TOO LOW!")
      return(0)

   #print("GAP TEST:", oid, ofns)
   #print("GAP TEST:", gap_events, gaps, cons, elp_frames, gap_to_cm_ratio, gap_to_elp_ratio)

   if gap_to_cm_ratio > .2 and gap_to_elp_ratio > .2 or (gaps == 0 and gap_events == 0):
      #print("GAP TEST GOOD!")
      return(1)
   else:
      #print("GAP TEST FAILED!", gap_to_cm_ratio, gap_to_elp_ratio)
      return(0)


def make_metframes(meteor_objects):
   ofns = meteor_objects[0]['ofns']
   oxs = meteor_objects[0]['oxs']
   oys = meteor_objects[0]['oys']
   metframes = {}
   i = 0
   for fn in ofns:
      ifn = int(fn)
      if fn not in metframes and ifn not in metframes:
         metframes[ifn] = {}
         metframes[ifn]['xs'] = []
         metframes[ifn]['ys'] = []
         metframes[ifn]['ws'] = []
         metframes[ifn]['hs'] = []
      metframes[ifn]['xs'].append(oxs[i])
      metframes[ifn]['ys'].append(oys[i])

      i = i + 1
   return(metframes)

def show_video(frames, meteor_objects, metframes):
   # SHOW FRAMES
   fn = 0


   fn = 0
   crop_size = 100
   show_frames = []
   show_spot = "tr"
   for frame in frames:
      if show_spot == "tl":
         show_y1 = 5
         show_y2 = 5 + crop_size * 2
         show_x1 = 5
         show_x2 = 5 + crop_size * 2
      if show_spot == "tr":
         show_y1 = 5
         show_y2 = 5 + crop_size * 2
         show_x1 = 1280 - (crop_size * 2) - 5
         show_x2 = 1280 -5

      show_frame = frame.copy()
      cnt_img = np.zeros((crop_size*2,crop_size*2,3),dtype=np.uint8)
      if fn in metframes:
         mx = int(np.mean(metframes[fn]['xs']))
         my = int(np.mean(metframes[fn]['ys']))
         if "blob_x" in metframes[fn]:
            blob_x = metframes[fn]['blob_x']
            blob_y = metframes[fn]['blob_y']
         else:
            blob_x = mx 
            blob_y = my 
         cx1,cy1,cx2,cy2= bound_cnt(blob_x,blob_y,frame.shape[1],frame.shape[0], 100)
         #print(cx1, cx2, cy1, cy2)
         cnt_img = frame[cy1:cy2,cx1:cx2]
         cnt_h, cnt_w = cnt_img.shape[:2]
         if show_spot == "tl":
            show_y1 = 5
            show_y2 = 5 + cnt_h
            show_x1 = 5
            show_x2 = 5 + cnt_w
         if show_spot == "tr":
            show_y1 = 5
            show_y2 = 5 + cnt_h
            show_x1 = 1280 - (cnt_w ) - 5
            show_x2 = 1280 -5
         #cv2.circle(show_frame,(blob_x,blob_y), 1, (0,0,255), 1)
         cv2.rectangle(show_frame, (blob_x-crop_size, blob_y-crop_size), (blob_x+ crop_size, blob_y + crop_size), (255, 255, 255), 1)
         show_frame = cv2.resize(show_frame, (1280,720))

      else:
         show_frame = cv2.resize(show_frame, (1280,720))

      show_frame[show_y1:show_y2,show_x1:show_x2] = cnt_img
      show_frames.append(show_frame)
      desc = str(fn)
      fn = fn + 1
   return(show_frames)

def sort_metframes(metframes):
   new_metframes = {}
   fns = []
   for fn in metframes:
      fns.append(int(fn))
   for fn in sorted(fns):
      fn = int(fn)
      if fn in metframes:
         new_metframes[fn] = metframes[fn]
   return(new_metframes)


def smooth_metframes(metframes, gray_frames):
   # first fill in any missing frames
   first_fn = None
   for fn in metframes:
      if first_fn is None:
         first_fn = fn
         first_ax = np.mean(metframes[fn]['xs'])
         first_ay = np.mean(metframes[fn]['ys'])
      last_fn = fn
      last_ax = np.mean(metframes[fn]['xs'])
      last_ay = np.mean(metframes[fn]['ys'])

   x_dir_mod, y_dir_mod = meteor_dir(first_ax, first_ay, last_ax, last_ay)
   print("X DIR, Y DIR", x_dir_mod, y_dir_mod)

   # determine seg lens
   xsegs = []
   ysegs = []
   last_ax = None
   for i in range (first_fn, last_fn):
      if i in metframes:
         ax = np.mean(metframes[i]['xs'])
         ay = np.mean(metframes[i]['ys'])
         if last_ax is not None:
            xsegs.append(ax-last_ax)
            ysegs.append(ay-last_ay)
         last_ax = ax
         last_ay = ay

   avg_x_seg = int(np.median(xsegs))
   avg_y_seg = int(np.median(ysegs))

   for i in range (first_fn, last_fn):
      if i in metframes:
         if x_dir_mod == 1:
            ax = np.min(metframes[i]['xs'])
         else:
            ax = np.max(metframes[i]['xs'])
         ay = np.mean(metframes[i]['ys'])

      if i not in metframes:
         print("ADD NEW METFRMAE FOPR FN:", i)
         metframes[i] = {}
         print(i, last_ax, avg_x_seg)
         est_x = int(last_ax + avg_x_seg)
         est_y = int(last_ay + avg_y_seg)
         ax = est_x
         ay = est_y

         metframes[i]['xs'] = [] 
         metframes[i]['ys'] = []
         #metframes[i]['xs'].append(est_x)
         #metframes[i]['ys'].append(est_y)
         metframes[i]['xs'].append(blob_x)
         metframes[i]['ys'].append(blob_y)
      else:
         print("METFRAMES FOR FN already exists:", i)
      blob_x, blob_y, max_val, blob_w, blob_h = find_blob_center(i, gray_frames[i],ax,ay,20, x_dir_mod, y_dir_mod)
      metframes[i]['blob_x'] = blob_x
      metframes[i]['blob_y'] = blob_y
      last_ax = ax
      last_ay = ay
   metframes = sort_metframes(metframes)
   metframes,seg_diff,xs,ys = comp_seg_dist(metframes, frames)

   cap = int(len(metframes) / 3) 
   med_seg_len = np.median(seg_diff[0:cap])

   print("BEST FIT:", xs, ys)
   m,b = best_fit_slope_and_intercept(xs,ys)

   first_frame = frames[0].copy()

   metconf = {}
   metconf['first_frame'] = first_frame
   metconf['fx'] = xs[0] 
   metconf['fy'] = ys[0] 
   metconf['med_seg_len'] = med_seg_len 
   metconf['m'] = m
   metconf['b'] = b
   metconf['x_dir_mod'] = x_dir_mod
   metconf['y_dir_mod'] = y_dir_mod

   # ACL POLY
   #this_poly = np.zeros(shape=(2,), dtype=np.float64)
   #this_poly[0] = -.05
   #this_poly[1] = -.01
   #mode = 0
   #res = scipy.optimize.minimize(reduce_acl, this_poly, args=( metframes, metconf,frames,mode,show), method='Nelder-Mead')
   #poly = res['x']
   #metconf['med_seg_len'] = float(metconf['med_seg_len'] + poly[0])
   #metconf['acl_poly'] = poly[1]
   #metconf['acl_poly'] = 0


   fcc = 0
   for fn in metframes:
      frame = frames[fn].copy()
      subframe = cv2.subtract(frame,first_frame)
      if "blob_x" in metframes:
         blob_x = metframes[fn]['blob_x']
         blob_y = metframes[fn]['blob_y']
         cv2.circle(subframe,(blob_x,blob_y), 10, (255,255,255), 1)
         fcc = fcc + 1


   return(metframes)

def comp_seg_dist(metframes, frames):
   last_x = None
   first_x = None
   dist_from_start = 0 
   last_dist_from_start = 0 
   segs = []
   dist_from_start_segs = []
   seg_diff = []
   xs = []
   ys = []

   for fn in metframes:
      if "blob_x" in metframes[fn]:
         blob_x = metframes[fn]['blob_x']
         blob_y = metframes[fn]['blob_y']
      else:
         blob_x = np.median(metframes[fn]['xs'])
         blob_y = np.median(metframes[fn]['ys'])
      if first_x is None:
         first_x = metframes[fn]['blob_x']
         first_y = metframes[fn]['blob_y']

      if last_x is not None:
         seg_dist = calc_dist((blob_x, blob_y), (last_x,last_y)) 
         dist_from_start = calc_dist((first_x, first_y), (blob_x,blob_y)) 
         segs.append(seg_dist)
         dist_from_start_segs.append(dist_from_start)
         dist_from_start_seg = dist_from_start - last_dist_from_start
         seg_diff.append(dist_from_start_seg)
         metframes[fn]['dist_from_start'] = dist_from_start
         metframes[fn]['seg_dist'] = seg_dist
         metframes[fn]['seg_diff'] = dist_from_start_seg 
      xs.append(blob_x)
      ys.append(blob_y)
      last_x = blob_x
      last_y = blob_y
      last_dist_from_start = dist_from_start 

   return(metframes, seg_diff , xs, ys)

def est_frame_pos():
   # now make estimate of frames based on seg len and m,b variables
   fcc = 0
   acl_poly = 0

   for fn in metframes:
      if fcc < first_cap:
         med_seg_len = first_seg_len
         m = first_m
         b = first_b
      #else:
      #   med_seg_len = np.median(seg_diff[fcc-10:fcc])
         #m,b = best_fit_slope_and_intercept(xs[fcc-10:fcc],ys[fcc-10:fcc])

      est_x = int((first_x + (-1*x_dir_mod) * (med_seg_len*fcc)) + acl_poly * fcc)
      est_y = int((m*est_x)+b)
      metframes[fn]['est_x'] = est_x
      metframes[fn]['est_y'] = est_y

      fcc = fcc + 1
      show_img = frames[fn].copy()
      if "blob_x" in metframes[fn]:
         blob_x = metframes[fn]['blob_x']
         blob_y = metframes[fn]['blob_y']
         cv2.circle(show_img,(blob_x,blob_y), 1, (0,0,255), 1)
         cv2.circle(show_img,(est_x,est_y), 1, (0,255,255), 1)

         print(fn, metframes[fn]['est_x'], metframes[fn]['est_y'], metframes[fn]['blob_x'], metframes[fn]['blob_y'])
   exit()

def reduce_acl(this_poly, metframes,metconf,frames,mode=0,show=0,key_field = ""):
   xs = []
   ys = []
   err = []
   fcc = 0
   m_10 = metconf['m']
   b_10 = metconf['b']
   acl_poly = this_poly[1]

   key_x = key_field + "blob_x"
   key_y = key_field + "blob_y"

   if "acl_med_seg_len" in metconf:
      med_seg = (this_poly[0] + np.float64(metconf['acl_med_seg_len']))
   else:
      med_seg = (this_poly[0] + np.float64(metconf['med_seg_len']))

   for fn in metframes:
      est_res = 0
      ifn = int(fn) -1
      img = frames[ifn].copy()
      img = cv2.resize(img, (1920,1080))
      if len(img.shape) == 2:
         img_gray = img
         img = cv2.cvtColor(img,cv2.COLOR_GRAY2RGB)
      else:
         img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

      est_x = int( metconf['fx'] + (-1*metconf['x_dir_mod'] * (med_seg*fcc)) + (acl_poly * (fcc*fcc)) )
      est_y = int((m_10*est_x)+b_10)

      cv2.circle(img,(est_x,est_y), 4, (0,255,255), 1)
      print(metframes[fn])
      if "key_x" in metframes[fn]:
         bp_x = metframes[fn][key_x]
         bp_y = metframes[fn][key_y]
         cv2.circle(img,(bp_x,bp_y), 4, (0,0,255), 1)
         xs.append(bp_x)
         ys.append(bp_y)
      else:
         bp_x = int(np.median(metframes[fn]['xs']))
         bp_y = int(np.median(metframes[fn]['ys']))
         

      bp_est_res = calc_dist((bp_x,bp_y), (est_x,est_y))
      hd_est_res = bp_est_res

      if mode == 1:
         metframes[fn]['est_x'] = est_x
         metframes[fn]['est_y'] = est_y
         metframes[fn]['acl_res'] = hd_est_res

      err.append(hd_est_res)

      cv2.putText(img, str(med_seg) + " " + str(acl_poly),  (10,10), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,0,255), 1)

      last_bp_x = bp_x
      last_bp_y = bp_y
      fcc = fcc + 1

      if len(xs) > 10:
         n_m_10,n_b_10 = best_fit_slope_and_intercept(xs[-10:],ys[-10:])
         if abs(n_b_10 - b_10) < 200:
            m_10 = n_m_10
            b_10 = n_b_10
   #print("ACL RES:", np.mean(err))
   if mode == 0:
      return(np.mean(err))
   else:
      return(np.mean(err), metframes)

# Notes:
# Pass in video file to get a detection and reduction

def flex_detect(video_file):
   hd_datetime, hd_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(video_file)
   motion_objects, motion_frames = detect_meteor_in_clip(video_file, None, 0)
   print(motion_objects)

def flex_detect_old(video_file):
   station_id = get_station_id(video_file)
   hd_datetime, hd_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(video_file)
   possible_cal_files = get_cal_params(video_file, station_id)
   #json_conf = load_json_conf(station_id)
   frames = load_video_frames(video_file, json_conf, 0, 0, [], 0)
   gray_frames = make_gray_frames(frames)
   detect_info = {}
   objects = {}

   json_file = video_file.replace(".mp4", ".json")
   manual_file = json_file.replace(".json", "-man.json")
   if cfe(manual_file) == 1:
      manual_fixes = load_json_file(manual_file)
   else:
      manual_fixes = {}
      manual_fixes['fixes'] = []

   if cfe(json_file) == 0:
      bp_frame_data, subframes = bp_detect(gray_frames,video_file)
      cnt_frame_data = detect_motion_in_frames(gray_frames, video_file)

      detect_info['bp_frame_data'] = bp_frame_data
      detect_info['cnt_frame_data'] = cnt_frame_data
      save_json_file(json_file, detect_info)
   else:
      detect_info = load_json_file(json_file)
      bp_frame_data = detect_info['bp_frame_data']
      cnt_frame_data = detect_info['cnt_frame_data']


   objects = find_cnt_objects(cnt_frame_data, objects)

   meteor_objects = []

   for obj in objects:
      if len(objects[obj]['oxs']) > 3:
         one_dir_test_result = one_dir_test(objects[obj])
         dist_test_result = dist_test(objects[obj])
         gap_test_result = gap_test(objects[obj])
         if one_dir_test_result == 1 and dist_test_result == 1 and gap_test_result == 1:
            print(obj, objects[obj])
            meteor_objects.append(objects[obj])

      if len(meteor_objects) == 0:
         print("No meteor objects.")
         for obj in objects:
            print(obj, objects[obj])


   metframes = make_metframes(meteor_objects )
   metframes = smooth_metframes(metframes, gray_frames)

   hdm_x = 1920 / 1280 
   hdm_y = 1080 / 720
   # apply manual corects
   for fix in manual_fixes['fixes']:
      fix_fn = fix['fn']  
      fix_x = int(fix['x'] * hdm_x)
      fix_y = int(fix['y'] * hdm_y)
 

      metframes[fix_fn]['blob_x'] = fix_x
      metframes[fix_fn]['blob_y'] = fix_y
      print("Fixing ", fix_fn)


   print("START METFRAMES", len(metframes))
   for fn in metframes:
      print(fn, metframes[fn])
   print("END METFRAMES")
   show_frames = show_video(frames, meteor_objects, metframes)
   marked_video_file = video_file.replace(".mp4", "-pub.mp4")
   remaster(show_frames, marked_video_file, station_id,meteor_objects[0])

def fast_check_events(sum_vals, max_vals, subframes):
   print("Fast check events.")
   events = []
   event = []
   event_info = []
   events_info = []
   cm = 0
   nomo = 0
   i = 0
   #med_sum = np.median(sum_vals[0:10])
   #med_max = np.median(max_vals[0:10])
   med_sum = np.median(sum_vals)
   med_max = np.median(max_vals)
   median_frame = cv2.convertScaleAbs(np.median(np.array(subframes[0:25]), axis=0))

   if subframes[0].shape[1] == 1920:
      hd = 1
      sd_multi = 1
   else:
      hd = 0
      sd_multi = 1920 / subframes[0].shape[1]

   for sum_val in sum_vals:
      
      #max_val = max_vals[i]
      subframe = subframes[i]
      #subframe = cv2.subtract(subframe, median_frame)
      min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(subframe)
      #print(i, med_sum, med_max, sum_val , max_val)
      if sum_val > med_sum * 2 or max_val > med_max * 2:
         min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(subframe)
         desc = str(i)
        
         if max_val > 10:
            #cv2.putText(subframe, str(desc),  (10,10), cv2.FONT_HERSHEY_SIMPLEX, .3, (255, 255, 255), 1)
            event_info.append((sum_val, max_val, mx, my))
            event.append(i)
            cm = cm + 1
            nomo = 0
         else:
            nomo = nomo + 1
      else:
         nomo = nomo + 1
      if cm > 2 and nomo > 5:
         events.append(event)
         events_info.append(event_info)
         event = []
         event_info = []
         cm = 0
      elif nomo > 5:
         event = []
         event_info = []
         cm = 0

      if show == 1:
         cv2.circle(subframe,(mx,my), 10, (255,0,0), 1)
         cv2.imshow('pepe', subframe)
         cv2.waitKey(70)

      i = i + 1

   if show == 1:
      cv2.destroyWindow('pepe')

   if len(event) >= 3:
      events.append(event)
      events_info.append(event_info)

   print("TOTAL EVENTS:", len(events))
   filtered_events = []
   filtered_info = []
   i = 0
   for ev in events:
      max_cm = calc_cm_for_event(ev)
      if max_cm >= 2:
         filtered_events.append(ev)
         filtered_info.append(events_info[i])
      else:
         print("FILTERED:", max_cm, ev)
         print("FILTERED:", events_info[i])
      i = i + 1
   print("FILTERED EVENTS:", len(filtered_events))
   events = filtered_events
   events_info = filtered_info

   i = 0
   objects = {}
   for event in events:
      ev_z = event[0]
      object = None
      fc = 0
      for evi in events_info[i]:
         sv, mv, mx, my = evi
         fn = event[fc]
         object, objects = find_object(objects, fn,mx, my, 5, 5, mv, hd, sd_multi)
         #print("OBJECT:", fn, object, objects[object])
         #if 500 <= ev_z <= 700:
         fc = fc + 1
      i = i + 1

   for obj in objects:
      object = objects[obj] 
      print("Analyzing object:", obj)
      objects[obj] = analyze_object_final(object, hd=0, sd_multi=1)

   pos_meteors = {}
   mc = 1
   for object in objects:
      if objects[object]['report']['meteor_yn'] == "Y":
         pos_meteors[mc] = objects[object]
         mc = mc + 1

   return(events, pos_meteors)

def calc_cm_for_event(event):
   cm = 0
   max_cm = 0
   last_fn = None
   for fn in event:
      if last_fn is not None:
         if last_fn + 1 == fn :
            cm = cm + 1
         else:
            if cm > max_cm :
               max_cm = cm + 1
            else:
               cm = 0
      last_fn = fn
   if cm > max_cm:
      max_cm = cm + 1
   return(max_cm)

def proc_move(video_file):
   fn = video_file.split("/")[-1]
   day = fn[0:10]
   stack_file = video_file.replace(".mp4", "-stacked.png")
   vals_file = video_file.replace(".mp4", "-vals.json")
   detect_file = video_file.replace(".mp4", "-detect.json")
   proc_dir = "/mnt/ams2/SD/proc2/" + day + "/" 
   if cfe(proc_dir + "images/", 1) == 0:
      os.makedirs(proc_dir + "images")
   if cfe(proc_dir + "data/", 1) == 0:
      os.makedirs(proc_dir + "data")
   cmd = "mv " + video_file + " " + proc_dir
   cmd2 = "mv " + stack_file + " " + proc_dir + "images/"
   cmd3 = "mv " + vals_file + " " + proc_dir + "data/"
   cmd4 = "mv " + detect_file + " " + proc_dir + "data/"
   os.system(cmd)
   os.system(cmd2)
   os.system(cmd3)
   print(cmd3)
   if cfe(detect_file) == 1:
      os.system(cmd4)

def batch_quickest_scan(cam=0):
   if cam == "0":
      files = glob.glob("/mnt/ams2/CAMS/queue/*.mp4")
   else:
      files = glob.glob("/mnt/ams2/CAMS/queue/*" + cam + "*.mp4")
   for file in sorted(files, reverse=True):
      if "trim" not in file:
         # start performance timer
         start_time = time.time()
         st = os.stat(file)
         size = st.st_size
         if size < 100:
 
            print("corrupt: rm " + file)
            os.system("rm " + file)
         else:
            quickest_scan(file)
         elapsed_time = time.time() - start_time
         print("SCAN TIME:", elapsed_time)
      else:
         print("Skipping trim file:", file)

def upscale_sd_to_hd(video_file):
   print("UPSCALE SD TO HD")
   new_video_file = video_file.replace(".mp4", "-HD-meteor.mp4")
   if cfe(new_video_file) == 0:
      cmd = "/usr/bin/ffmpeg -i " + video_file + " -vf scale=1920:1080 " + new_video_file
      os.system(cmd)
   return(new_video_file)

def quickest_scan(video_file):
   # only used for 1-minute incoming clips!
   if "mp4" not in video_file or cfe(video_file) == 0:
      print("BAD INPUT FILE:", video_file)
      return([])

   # start performance timer
   start_time = time.time()

   # set stack file and skip if it alread exists.
   stack_file = video_file.replace(".mp4", "-stacked.png")
   if cfe(stack_file) == 1 :
      print("Already done this.")
      return()

   # load the frames
   frames,color_frames,subframes,sum_vals,max_vals,pos_vals = load_frames_fast(video_file, json_conf, 0, 0, [], 0,[])
   elapsed_time = time.time() - start_time

   vals = {}
   vals['max_vals'] = max_vals
   vals['sum_vals'] = sum_vals
   vals_file = video_file.replace(".mp4", "-vals.json")

   print("Total Frames:", len(frames))
   print("Total Sub Frames:", len(subframes))
   print("Loaded frames.", elapsed_time)
   if len(max_vals) > 0:
      if max(max_vals) < 10:
         detects_found = 0
         # stack fast (skip 10) and return. 
         stacked_frame = stack_frames_fast(frames, 10)
         cv2.imwrite(stack_file, stacked_frame) 
         print("NO BRIGHT PX. SAVE STACK, move files AND QUIT!")
         #print(vals_file)
         save_json_file(vals_file, vals)
         proc_move(video_file)
         return()
   events,meteor_objs,non_meteor_objs = detect_with_max_vals(max_vals,sum_vals,subframes)
   # if no events exist fast stack and go
   if len(events) == 0:
      detects_found = 0
      # stack fast (skip 10) and return. 
      stacked_frame = stack_frames_fast(frames, 5)
      try:
         cv2.imwrite(stack_file, stacked_frame) 
      except:
         print("stack failed")
      print("NO EVENTS. SAVE STACK, move files AND QUIT!")
      save_json_file(vals_file, vals)
      #print(vals_file)
      proc_move(video_file)
      return()

   # if no meteors exist fast stack and go
   if len(meteor_objs) == 0:
      detects_found = 0
      # stack fast (skip 10) and return. 
      stacked_frame = stack_frames_fast(frames, 10)
      cv2.imwrite(stack_file, stacked_frame) 
      print("NO METEORS FOUND. SAVE STACK, move files AND QUIT!")
      print("MIGHT AS WELL SAVE NON-METEOR OBJECTS too?. ")
      #print(vals_file)
      save_json_file(vals_file, vals)
      proc_move(video_file)
      return()

   save_json_file(vals_file, vals)
   all_sd_meteors = []
   if len(meteor_objs) >= 1:
      print("More than 1 potential meteor detected. Examine all clips as one")
      allfn = []
      for obj in meteor_objs:
         print("POSSIBLE METEOR FOUND:", obj['ofns'])
         start = min(obj['ofns'])
         end = max(obj['ofns'])
         t_start, t_end = buffered_start_end(start,end, len(subframes), 10)
         motion_objects, motion_frames = detect_meteor_in_clip(video_file, subframes[t_start:t_end], t_start)
         sd_meteors = only_meteors(motion_objects)
         if sd_meteors is not None:
            for sdm in sd_meteors:
               all_sd_meteors.append(sdm)

   if len(all_sd_meteors) > 0:
      print("METEORS?", len(all_sd_meteors))
      sd_meteors = all_sd_meteors
   else:
      sd_meteors = None

   
   if sd_meteors is None :
      detects_found = 0
      # stack fast (skip 10) and return. 
      stacked_frame = stack_frames_fast(frames, 10)
      cv2.imwrite(stack_file, stacked_frame) 
      print("NO METEORS FOUND. SAVE STACK, move files AND QUIT!")
      print("MIGHT AS WELL SAVE NON-METEOR OBJECTS too?. ")
      vals['motion_objects'] = motion_objects
      #print(vals_file)
      save_json_file(vals_file, vals)
      proc_move(video_file)
      return()
   if len(sd_meteors) > 3:
      detects_found = 0
      # stack fast (skip 10) and return. 
      stacked_frame = stack_frames_fast(frames, 10)
      cv2.imwrite(stack_file, stacked_frame) 
      print("TOO MANY METEORS FOUND. THIS IS A CAR OR SOMETHING LIKE A CAR!")
      vals['motion_objects'] = motion_objects
      vals['sd_meteors'] = sd_meteors
      #print(vals_file)
      save_json_file(vals_file, vals)
      proc_move(video_file)
      return()
   detect_data = {}
   if motion_objects is not None:
      detect_data['motion_objects'] = motion_objects
   if sd_meteors is not None:
      detect_data['sd_meteors'] = sd_meteors

   print("POSSIBLE METEOR FOUND!")  
   for meteor in sd_meteors:
      id = meteor['obj_id']
      print(id, meteor['ofns'])
      print(id, meteor['oxs'])
      print(id, meteor['oys'])
      print(id, meteor['ows'])
      print(id, meteor['ohs'])
      print(id, meteor['report'])
      start = meteor['ofns'][0]
      df = meteor['ofns'][-1] - meteor['ofns'][0]
      print("DF = ", df)
      print("DF SEC = ", df/25)
      hd_file, hd_trim,time_diff_sec, dur = find_hd_file_new(video_file, start, df/25, 1)
      #if hd_trim is None:
         # we could not find a HD file, so just upscale the HD file
      #   hd_trim = upscale_sd_to_hd(video_file)
      detect_data['hd_trim'] = hd_trim
      hd_motion_objects, motion_frames = detect_meteor_in_clip(hd_trim)
      hd_meteors = only_meteors(hd_motion_objects)
      detect_data['hd_motion_objects'] = hd_motion_objects
      if hd_meteors is not None:
         detect_data['hd_meteors'] = hd_meteors
   stacked_frame = stack_frames_fast(frames, 1)
   detect_file = video_file.replace(".mp4", "-meteor.json")
   detect_data['hd_trim'] = hd_trim
   detect_data['sd_video_file'] = video_file 
   detect_data['hd_video_file'] = hd_file 
   save_json_file(detect_file, detect_data)
   save_json_file(vals_file, vals)
   cv2.imwrite(stack_file, stacked_frame) 
   print(stack_file)
   print("SD METEORS:", sd_meteors)
   print("HD METEORS:", hd_meteors)
   print("NON HD METEORS:")

   return()
 
   # METEOR EXISTS AND NEEDS TO BE PROCESSED!
   # FIND THE HD FILE
   # TRIM THE HD FILE
   # DETECT METEOR IN HD FILE
   # SYNC SD AND HD FRAMES 
   # SAVE SYNCD SD AND HD FILES AND NEW JSON IN METEOR ARCHIVE
   # CREATE CACHE FOR NEW ARCHIVE FILE  (in BG)
   # COPY BOTH FULL MIN SD AND HD FILE TO /mnt/ams2/min_saved/YEAR/DAY/FILE-HD or FILE-SD
   # Stack all frames in the full min file and move to PROC2 dir
   # Stack all frames in just the meteor CLIP and save that (somewhere (in archive) / tied to preview image
   # Apply the calib (find stars and find last best (but that's it))
    

   elapsed_time = time.time() - start_time
   print("Elapsed Time:", elapsed_time)
   

def detect_with_max_vals(max_vals, sum_vals,subframes):

   med_max = np.median(max_vals)
   if med_max < 5:
      med_max = 5

   cm = 0
   nomo = 0
   event = []
   events = []
   last_bp = 0
   objects = {}
   for i in range(0,len(max_vals)):
      if max_vals[i] > med_max:
         bp = 1
         nomo = 0
         # get the cnts (or bp) and track it as an object? 
         if i - 1 == last_bp:
            cm += 1
            event.append(i)
         last_bp = i
      else:
         bp = 0

      if bp == 0:
         if len(event) >= 3:
            events.append(event)
         event = []
         nomo = nomo + 1
         cm = 0
   if len(event) >= 3:
      events.append(event)

   for event in events:
      for i in event:
         #cv2.imshow('pepe', subframes[i])
         #cv2.waitKey(0)
         min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(subframes[i])
         cx1,cy1,cx2,cy2= bound_cnt(mx,my,subframes[0].shape[1],subframes[0].shape[0], 10)
         cnt_img = subframes[i][cy1:cy2,cx1:cx2]
         intensity = np.sum(cnt_img)
         object, objects = find_object(objects, i,mx, my, 5, 5, intensity, 0, 0, cnt_img)
         #cv2.rectangle(subframes[i], (cx1, cy1), (cx2, cy2), (255,255,255), 1, cv2.LINE_AA)
         #cv2.putText(subframes[i], str(object) + " " + str(intensity),  (cx1,cy1), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 1)


         #cv2.imshow('pepe', subframes[i])
         #cv2.waitKey(0)

   meteor_objs = []
   non_meteor_objs = []
   for obj in objects:
      #print(obj, objects[obj])
      if objects[obj]['report']['meteor_yn'] == "Y":
         meteor_objs.append(objects[obj])
         print("METEOR:", obj, objects[obj])
      else: 
         if len(objects[obj]['ofns']) > 3:
            print("NON METEOR:", obj, objects[obj]['ofns'], objects[obj]['report'])
            non_meteor_objs.append(objects[obj])
   return(events, meteor_objs,non_meteor_objs)   

def quick_scan(video_file, old_meteor = 0):
   # 3 main parts
   # 1st scan entire clip for 'bright events' evaluating just the sub pixels in the subtracted frame
   # 2nd any bright events that match a meteor profile are sliced out and contours are found and logged for each frame
   # contours are turned into objects and evaluated
   # 3rd for any objects that might be meteors, create a longer clip around the event (+/-50 frames)
   # and run motion detection on those frames locating the objects. 

   debug = 0
   if "mp4" not in video_file or cfe(video_file) == 0:
      print("BAD INPUT FILE:", video_file)
      return([])

   if "/mnt/ams2/meteors" in video_file:
      rescan = 1
   else:
      rescan = 0
   if rescan == 1:
      # Make sure this file is not already in the archive.
      jsf = video_file.replace(".mp4", ".json")
      ojs = load_json_file(jsf)
      if "archive_file" in ojs:
         if cfe(ojs['archive_file']) == 1:
            print("File has been archived already!")
            #return()
 
   #PREP WORK

   # start performance timer
   start_time = time.time()

   # set stack file and skip if it alread exists. 
   stack_file = video_file.replace(".mp4", "-stacked.png")
   if cfe(stack_file) == 1 and old_meteor == 0:
      print("Already done this.")
      #return([])

   # setup variables
   cm = 0
   no_mo = 0
   event = []
   bright_events = []
   valid_events = []

   station_id = get_station_id(video_file)
   #json_conf = load_json_conf(station_id)
   hd_datetime, hd_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(video_file)
   meteor_date = hd_y + "_" + hd_m + "_" + hd_d
   print("STATION:", station_id, video_file, start_time)

   # load the frames
   frames,color_frames,subframes,sum_vals,max_vals,pos_vals = load_frames_fast(video_file, json_conf, 0, 0, [], 0,[])
   elapsed_time = time.time() - start_time
   print("Total Frames:", len(frames))
   print("Loaded frames.", elapsed_time)
   # check to make sure frames were loaded
   if len(frames) < 5:
      print("bad input file.")
      return([])

   events,pos_meteors = fast_check_events(sum_vals, max_vals, subframes)

   mc = 1
   print("POS METEORS:", len(pos_meteors))
   meteors = {}
   for meteor in pos_meteors:
      pos_meteors[meteor] = analyze_object_final(pos_meteors[meteor])
      pos_meteors[meteor] = analyze_object(pos_meteors[meteor], 1, 1)
      if pos_meteors[meteor]['report']['meteor_yn'] == 'Y':
         print("POS METEOR:", pos_meteors[meteor])
         meteors[mc] = pos_meteors[meteor]
         mc = mc + 1
      else:
         print("NON METEOR:", pos_meteors[meteor])
         
   pos_meteors = meteors
   print("POS:", len(pos_meteors))

   # Stack the frames and report the run time
   stacked_frame = stack_frames_fast(frames)
   cv2.imwrite(stack_file, stacked_frame) 
   elapsed_time = time.time() - start_time
   print("Stacked frames.", elapsed_time)
   
   # check time after frame load
   elapsed_time = time.time() - start_time
   print("Ending fast detection.", elapsed_time)

   if len(pos_meteors) == 0:
      elapsed_time = time.time() - start_time
      print("ELAPSED TIME:", elapsed_time)
      print("NO METEORS:", elapsed_time)
        
      if rescan == 1:
         log_import_errors(video_file, "No meteors detected in 1st scan.")
      return([])
   if len(pos_meteors) > 1:
      # we may have more than 1 possible meteor.
      if rescan == 1:
         print("more than 1 pos meteor.", rescan)
         log_import_errors(video_file, "More than 1 possible meteor detected.")
         return([])

   meteor_file = video_file.replace(".mp4", "-meteor.json")
   # Only continue if we made it past the easy / fast detection
   all_motion_objects = []
   for object in pos_meteors:
      pos_meteors[object] = merge_obj_frames(pos_meteors[object])
      start, end = buffered_start_end(pos_meteors[object]['ofns'][0],pos_meteors[object]['ofns'][-1], len(frames), 50)
      print("BUFFERED START:", start, end)
      if rescan == 0:
         trim_clip, trim_start, trim_end = make_trim_clip(video_file, start, end)
         t_start = start
         t_end = end
      else:
         trim_clip = video_file
         trim_start = start
         t_start = 0
         t_end = -1
      motion_objects, motion_frames = detect_meteor_in_clip(trim_clip, frames[t_start:t_end], t_start)
      for obj in motion_objects:
         all_motion_objects.append(motion_objects[obj])

   objects = []
   print("Ending detecting SD in clip.", len(all_motion_objects))
   for mo in all_motion_objects:
      mo = analyze_object_final(mo)
      
      if mo['report']['meteor_yn'] == "Y" or len(mo['ofns']) > 25:
         print("CONFIRMED OBJECTS:", mo)
         objects.append(mo)
      else:
         print("NON CONFIRMED OBJECTS:", mo)


   #objects = all_motion_objects

   elapsed_time = time.time() - start_time
   print("ELPASED TIME:", elapsed_time)
   print("OBJECTS IN PLAY:", len(objects))
   # Find the meteor like objects 
   meteors = []
   non_meteors = []

   for obj in objects:
      if len(obj['ofns']) > 2:
         print("merge obj frames:", obj)
         print("merge obj frames:", obj['ofns'])
         #obj = analyze_object_final(obj)
         #print("analyze final obj frames:", obj)
      if obj['report']['meteor_yn'] == "Y":
         print ("********************* METEOR *********************")
         print(obj['ofns'])
         meteors.append(obj)
      else:
         print("NON METEOR:", obj)
         non_meteors.append(obj)


   if len(meteors) == 0:
      print("No meteors found." )
      detect_file = video_file.replace(".mp4", "-detect.json")
 
      if rescan == 0:
         save_json_file(detect_file, non_meteors)
      elapsed_time = time.time() - start_time
      print("ELPASED TIME:", elapsed_time)
      return([])
   if len(meteors) > 10:
      print("ERROR! Something like a bird.")
      non_meteors = meteors + non_meteors
      detect_file = video_file.replace(".mp4", "-detect.json")
      if rescan == 0:
         save_json_file(detect_file, non_meteors)
      return([])


   meteor_file = video_file.replace(".mp4", "-meteor.json")
   if rescan == 0:
      save_json_file(meteor_file, meteors)
   print("METEORS FOUND!", meteor_file)
   elapsed_time = time.time() - start_time
   print("ELPASED TIME:", elapsed_time)

   mjf = video_file.replace(".mp4", "-meteor.json")
   print("Process meteor.", mjf)

   old_meteor_dir = "/mnt/ams2/meteors/" + meteor_date + "/"
   if rescan == 1:
      for obj in meteors:
         mf = trim_clip.split("/")[-1]
         mf = mf.replace(".mp4", ".json")
         old_meteor_json_file = old_meteor_dir + mf
         md = load_json_file(old_meteor_json_file)
         obj['hd_trim'] = md['hd_trim']
         if "hd_video_file" in md:
            obj['hd_video_file'] = md['hd_video_file']
         if "hd_file" in md:
            obj['hd_video_file'] = md['hd_file']


         #if "hd_video_file" in md:
         #   obj['hd_video_file'] = md['hd_video_file']
         #   obj['hd_crop_file'] = md['hd_crop_file']
         #elif "hd_trim" in md:
         #   obj['hd_video_file'] = md['hd_trim']
         #   obj['hd_trim'] = md['hd_trim']
         #if obj['hd_trim'] != 0 :
         #   if "/mnt/ams2/HD" in obj['hd_video_file'] or "/mnt/ams2/HD" in obj['hd_trim']:
         #      new_dir = "/mnt/ams2/meteors/" + meteor_date + "/" 
         #      obj['hd_video_file'] = obj['hd_video_file'].replace("/mnt/ams2/HD/", new_dir)
         #      obj['hd_trim'] = obj['hd_trim'].replace("/mnt/ams2/HD/", new_dir)
             

         #obj['hd_crop_file'] = md['hd_crop_file']
         calib,cal_params = apply_calib(obj)
         obj['calib'] = calib
         obj['cal_params'] = cal_params 
         if obj['hd_trim'] == 0:
            print("Crap no hd_trim for this file.", obj['trim_clip'])
            fp = open("/mnt/ams2/meteors/import_errors.txt", "a")
            fp.write(str(obj['trim_clip']) + "," + str(obj['hd_trim'])+ "," + "SD & HD objects don't match\n")
            fp.close()


            return()
         else:
            new_json_file = sync_hd_sd_frames(obj)
         if new_json_file == 0:
            return(0)
        
         obj['new_json_file'] = new_json_file 
         save_old_style_meteor_json(old_meteor_json_file, obj, trim_clip )
         process_meteor_files(obj, meteor_date, video_file, rescan)
         print("VIDEO FILE:", video_file)
      return(meteors)

   final_meteors = []

   for obj in meteors:
      old_scan = 0
      start = obj['ofns'][0]
      end = obj['ofns'][-1]
      # sync HD
      df = int ((end - start) / 25)
      hd_file, hd_trim,time_diff_sec, dur = find_hd_file_new(video_file, start, df, 1)
      print("START END:", start, end, df)
      print("HD TRIM:", hd_trim)
      if hd_trim is not None and rescan == 0:
         print("HD SYNC:", hd_file, hd_trim, time_diff_sec, dur, df)
         # Make the HD stack file too.  And then sync the HD to SD video file.
         obj['hd_trim'] = hd_trim
         obj['hd_video_file'] = hd_file
         if hd_trim != 0 and cfe(hd_trim) == 1:
            #hd_crop, crop_box = crop_hd(obj, frames[0])
            #hd_crop_objects,hd_crop_frames = detect_meteor_in_clip(hd_crop, None, start, crop_box[0], crop_box[1])
            #refine_points(hd_crop, hd_crop_frames )
            #obj['hd_crop_file'] = hd_crop
            #obj['crop_box'] = crop_box
            #obj['hd_crop_objects'] = hd_crop_objects
            if rescan == 0:
               restack(obj['hd_trim'])
               print("mv " + hd_trim + " " + old_meteor_dir)
               os.system("mv " + hd_trim + " " + old_meteor_dir)
               #print("mv " + hd_crop + " " + old_meteor_dir)
               #os.system("mv " + hd_crop + " " + old_meteor_dir)
         else:
            obj['hd_trim'] = 0
            obj['hd_video_file'] = 0

      
      # restack the SD file
      restack(obj['trim_clip'])
      process_meteor_files(obj, meteor_date, video_file, rescan)
      print("VIDEO FILE:", video_file)
      final_meteors.append(obj)

   # do this as a separate process.
   #confirm_meteor(mjf)

   for obj in final_meteors:
      print(obj)

   return([])

def restack(file):

   if cfe(file) == 1:
      frames,color_frames,subframes,sum_vals,max_vals,pos_vals = load_frames_fast(file, json_conf, 0, 0, [], 0,[])
      print("RESTACK: ", file, len(frames))
      stack = stack_frames_fast(frames, 1)
      stack_file = file.replace(".mp4", "-stacked.png")
      print(stack.shape)
      cv2.imwrite(stack_file, stack)

def log_import_errors(video_file, message):
   fn = video_file.split("/")[-1]
   day = fn[0:10]
   log_file = "/mnt/ams2/meteors/" + day + "/import_errors.json"
   if cfe(log_file) == 1:
      log = load_json_file(log_file)
      if "import_errors.json" in log:
         log = {}
   else:
      log = {}
   log[video_file] = message
   save_json_file(log_file, log)

def only_meteors(objects, best_one=0):
   meteors = []
   for obj in objects:
      if objects[obj]['report']['meteor_yn'] == "Y":
         meteors.append(objects[obj])

   if len(meteors)  > 1: 
      nm = []
      for m in meteors:
         if m['report']['classify']['meteor_yn'] == "Y":
            #print(m['ofns'])
            #print(m)
            nm.append(m)
      meteors = nm
   return(meteors)

def refine_sync(sync_diff, sd_object, hd_object, hd_frame, sd_frame):
   max_err_x = 9999
   max_err_y = 9999
   sync_obj = {}

   print("SD FNS:", sd_object['ofns'])
   print("HD FNS:", hd_object['ofns'])
   hdm_x = hd_frame.shape[1] / sd_frame.shape[1]
   hdm_y = hd_frame.shape[0] / sd_frame.shape[0]

   # for the first SD frame, figure out which HD frame has the least error.

   for i in range(0,len(sd_object['ofns'])):
      sd_fn = sd_object['ofns'][i]
      sync_obj[sd_fn] = {}
      sync_obj[sd_fn]['err'] = 9999
      sd_x = sd_object['oxs'][i]
      sd_y = sd_object['oys'][i]
      up_sd_x = int(sd_x * hdm_x)
      up_sd_y = int(sd_y * hdm_y)
      for j in range(0,len(hd_object['ofns'])):

         hd_x = hd_object['oxs'][j]
         hd_fn = hd_object['ofns'][j]
         hd_y = hd_object['oys'][j]
         err_x = abs(up_sd_x - hd_x)
         err_y = abs(up_sd_y - hd_y)
         err = err_x + err_y
         if err < sync_obj[sd_fn]['err']:
            sync_obj[sd_fn]['hd_fn'] = hd_fn
            sync_obj[sd_fn]['err'] = err 
         
       
         print(sd_fn, hd_fn, up_sd_x, hd_x, up_sd_y, up_sd_x, err_x, err_y)

   i = 0
   for sync in sorted(sync_obj.keys()):
      if i == 0:
         hd_sd_sync = sync_obj[sync]['hd_fn'] - sync
      print(sync, sync_obj[sync])
      i = i + 1

   return(hd_sd_sync)

def sync_hd_sd_frames(obj):
   orig_obj = obj
   print("SYNC FRAMES!")
   print("HD TRIM:", obj['hd_trim'])
   print("SD TRIM:", obj['trim_clip'])
   sd_trim_num = get_trim_num(obj['trim_clip'])
   first_sd_frame = obj['ofns'][0]
   sd_frames,sd_color_frames,sd_subframes,sd_sum_vals,sd_max_vals,pos_vals = load_frames_fast(obj['trim_clip'], json_conf, 0, 0, [], 1,[])
   hd_frames,hd_color_frames,hd_subframes,hd_sum_vals,hd_max_vals,pos_vals = load_frames_fast(obj['hd_trim'], json_conf, 0, 0, [], 1,[])

   hd_objects,trash = detect_meteor_in_clip(obj['hd_trim'], hd_frames, 0, 0, 0)
   sd_objects,trash = detect_meteor_in_clip(obj['trim_clip'], sd_frames, 0, 0,0)
   all = hd_objects
   hdm_x = hd_frames[0].shape[1] / sd_frames[0].shape[1] 
   hdm_y = hd_frames[0].shape[0] / sd_frames[0].shape[0] 
   #sd_objects,hd_objects= pair_hd_sd_meteors(sd_objects, hd_objects, hdm_x, hdm_y)

   hd_objects = only_meteors(hd_objects)
   sd_objects = only_meteors(sd_objects)
   print("SD:", sd_objects)
   print("HD:", hd_objects )


   if len(hd_objects) == 0:
      for hdo in all:
         print(all[hdo])


   if len(hd_objects) == len(sd_objects) and len(sd_objects) > 0:
      print("We have a match!") 
      sd_ind = sd_objects[0]['ofns'][0]
      hd_ind = hd_objects[0]['ofns'][0]
      sync_diff = hd_ind - sd_ind
      sync_diff = refine_sync(sync_diff, sd_objects[0], hd_objects[0], hd_frames[0], sd_frames[0])

      sdf = []
      hdf = []
      for i in range(0, len(hd_objects[0]['ofns'])):
         hd_fn = hd_objects[0]['ofns'][i]
         sd_fn = hd_fn - sync_diff 
         print("SD,HD SYNC:", sd_fn, hd_fn)
         sd_frame = sd_frames[sd_fn]
         hd_frame = hd_frames[hd_fn]
         sdf.append(sd_fn)
         hdf.append(hd_fn)
         hd_frame = cv2.resize(hd_frame, (0,0),fx=.25, fy=.25)
   else:
      print("Problem sd and hd events don't match up perfectly...", len(sd_objects), len(hd_objects))
      #fp = open("/mnt/ams2/meteors/import_errors.txt", "a")
      #fp.write(orig_obj['trim_clip'] + "," + obj['hd_trim']+ "," + "SD & HD objects don't match\n")
      #fp.close()
      log_import_errors(orig_obj['trim_clip'], "Problem with sd and hd events don't match perfectly.")
      debug = 0
      if debug == 1:
         show_objects(sd_objects, "SD")
         show_objects(hd_objects, "HD")
      print("SD AND HD EVENTS DON'T LINE UP PERFECT! need to fix!", len(sd_objects), len(hd_objects))
      return(0)

   buf_size = 20
   sd_bs,sd_be = buffered_start_end(sdf[0],sdf[-1], len(hd_frames), buf_size)
   if sd_bs == 0:
      buf_size = sdf[0]
   hd_bs,hd_be = buffered_start_end(hdf[0],hdf[-1], len(hd_frames), buf_size)

   (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(obj['trim_clip'])
   new_sd_trim_num = sdf[0] - buf_size + sd_trim_num
   extra_sec = new_sd_trim_num / 25

   start_trim_frame_time = f_datetime + datetime.timedelta(0,extra_sec)




   xxx = obj['trim_clip'].split("/")[-1]
   fnw = xxx.split("-trim")[0]
   #new_trim = '{0:04d}'.format(int(new_sd_trim_num)) 
   new_trim = new_sd_trim_num
   new_hd_file_name = "/mnt/ams2/matmp/" + fnw + "-trim" + str(new_trim) + "-HD.mp4"
   new_sd_file_name = "/mnt/ams2/matmp/" + fnw + "-trim" + str(new_trim) + "-SD.mp4"
   new_json_file_name = "/mnt/ams2/matmp/" + fnw + "-trim" + str(new_trim) + ".json"


   new_hd_frames = hd_frames[hd_bs:hd_be]
   new_sd_frames = sd_frames[sd_bs:sd_be]
   new_hd_color_frames = hd_color_frames[hd_bs:hd_be]
   new_sd_color_frames = sd_color_frames[sd_bs:sd_be]

   hd_objects,trash = detect_meteor_in_clip(new_hd_file_name, new_hd_frames, 0, 0)
   sd_objects,trash = detect_meteor_in_clip(new_sd_file_name, new_sd_frames, 0, 0)
   
  
   hd_meteors = []
   ftimes = []
   for obj in hd_objects:
      hd_objects[obj] = analyze_object_final(hd_objects[obj])
      hd_objects[obj] = analyze_object(hd_objects[obj], 1, 1)
      
      if hd_objects[obj]['report']['meteor_yn'] == 'Y':
         print(hd_objects[obj]['ofns'])
         print(hd_objects[obj]['report'])
         hd_meteors.append(hd_objects[obj])

   hdm_x = new_hd_frames[0].shape[1] / new_sd_frames[0].shape[1] 
   hdm_y = new_hd_frames[0].shape[0] / new_sd_frames[0].shape[0] 
   if len(hd_meteors) > 1:
      print("PAIR!")
      hd_meteors = pair_sd_hd_meteors(sd_objects, hd_objects, hdm_x, hdm_y)
   
   if len(hd_meteors) == 0:

      print("NO HD METEORS FOUND. FAIL OVER TO SD METEORS?")
      exit()
   elif len(hd_meteors) == 1:
      meteor_obj = hd_meteors[0]
      make_movie_from_frames(new_hd_color_frames, [0,len(new_hd_frames) - 1], new_hd_file_name, 0)
      make_movie_from_frames(new_sd_color_frames, [0,len(new_hd_frames) - 1], new_sd_file_name, 0)

      meteor_obj['calib'] = orig_obj['calib']
      meteor_obj['hd_trim'] = orig_obj['hd_trim']
      meteor_obj['trim_clip'] = orig_obj['trim_clip']
      meteor_obj['hd_file'] = new_hd_file_name 
      meteor_obj['sd_file'] = new_sd_file_name 
      meteor_obj['dt'] = start_trim_frame_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

      hdm_x = new_hd_frames[0].shape[1] / new_sd_frames[0].shape[1] 
      hdm_y = new_hd_frames[0].shape[0] / new_sd_frames[0].shape[0] 
      for i in range(0,len(meteor_obj['ofns'])):
         if "ftimes" not in meteor_obj:
            meteor_obj['ftimes'] = []
         fn = meteor_obj['ofns'][i]
         hd_x = meteor_obj['oxs'][i]
         hd_y = meteor_obj['oys'][i]

         extra_meteor_sec = fn /  25
         meteor_frame_time = start_trim_frame_time + datetime.timedelta(0,extra_meteor_sec)
         meteor_frame_time_str = meteor_frame_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
         meteor_obj['ftimes'].append(meteor_frame_time_str)
         ftimes.append(meteor_frame_time)
         print("METEOR FRAME TIME:", meteor_frame_time_str)

         print("HD FN", fn)
         hd_frame = new_hd_frames[fn]
         cx1,cy1,cx2,cy2= bound_cnt(hd_x,hd_y,new_hd_frames[0].shape[1],new_hd_frames[0].shape[0], 20)
         hd_cnt = new_hd_frames[fn][cy1:cy2,cx1:cx2]

         sd_x = int(hd_x / hdm_x)
         sd_y = int(hd_y / hdm_y)
         cx1,cy1,cx2,cy2= bound_cnt(sd_x,sd_y,new_sd_frames[0].shape[1],new_sd_frames[0].shape[0], 20)
         #sd_frame = new_sd_frames[fn]
         #sd_cnt = new_sd_frames[fn][cy1:cy2,cx1:cx2]

         #show_img = sd_frame 
         #cv2.rectangle(show_img, (cx1, cy1), (cx2, cy2), (255,255,255), 1, cv2.LINE_AA)


   else:
      print("MORE THAN ONE METEOR OBJECT! NOT COOL!")
      #fp = open("/mnt/ams2/meteors/import_errors.txt", "a")
      #fp.write(str(orig_obj['trim_clip']) + "," + str(orig_obj['hd_trim'])+ "," + "MORE THAN ONE METEOR OBJECT\n")
      #fp.close()
      log_import_errors(orig_obj['trim_clip'], "More than one meteor object.")
      return(0)
   meteor_obj['dur'] = (ftimes[-1] - ftimes[0]).total_seconds()
   meteor_obj['cal_params'] = orig_obj['cal_params'] 
   new_json = save_new_style_meteor_json(meteor_obj, new_hd_file_name)
   save_json_file(new_json_file_name, new_json)
   move_to_archive(new_json_file_name)
   write_archive_index(fy,fm) 
   print(new_json_file_name)
   return(new_json_file_name)

def pair_hd_sd_meteors(sd_objects, hd_objects, hdm_x,hdm_y):
   matched_sd_meteor = []
   matched_hd_meteor = []
   last_x_err = 9999
   for hobj in hd_objects:
      if hd_objects[hobj]['report']['meteor_yn'] == 'Y':
         matched_hd_meteor = hd_objects[hobj]
         for sobj in sd_objects:
            if sd_objects[sobj]['report']['meteor_yn'] == 'Y':
               x_diff = int(sd_objects[sobj]['oxs'][0] * hdm_x) - hd_objects[hobj]['oxs'][0]
               print("XDIF:", x_diff)
               if x_diff < last_x_err:
                  matched_sd_meteor = sd_objects[sobj]
                  last_x_err = x_diff
   matches = []
   hd_matches = []
   matches.append(matched_sd_meteor)
   hd_matches.append(matched_hd_meteor)
   return([matches], [hd_matches] )

def pair_sd_hd_meteors(sd_objects, hd_objects, hdm_x,hdm_y):
   matched_hd_meteor = []
   last_x_err = 9999
   for sobj in sd_objects:
      if sd_objects[sobj]['report']['meteor_yn'] == 'Y':
         print("SD METEOR OBJECT:", sd_objects[sobj])
         for hobj in hd_objects:
            if hd_objects[hobj]['report']['meteor_yn'] == 'Y':
               print("HD METEOR OBJECT:", hd_objects[hobj])
               x_diff = int(sd_objects[sobj]['oxs'][0] * hdm_x) - hd_objects[hobj]['oxs'][0]
               print("XDIF:", x_diff)
               if x_diff < last_x_err:
                  matched_hd_meteor = hd_objects[hobj]
                  last_x_err = x_diff
 
   matches = []
   matches.append(matched_hd_meteor)
   return(matches)
               
      
   

def show_objects(objects, desc):
   for obj in objects:
      print(desc, "Object: ", obj)
      print(desc, "FNS:", obj['ofns'])   
      print(desc, "SXS:", obj['oxs'])   
      print(desc, "SYS:", obj['oys'])   
      print(desc, "WS:", obj['ows'])   
      print(desc, "HS:", obj['ohs'])   
      print(desc, "INTS:", obj['oint'])   
      for key in obj['report']:
         print("   ", desc, key, obj['report'][key])   

def old_detection_codes():
   exit()
   ############################################################################
   # DETECTION PHASE 2
   # For each meteor like object run motion detection on the frames containing the event

   # Loop over each possible meteor
   for object in meteors:   
      print("METEOR", object)
      # Determine start and end frames and then add 50 frames to either end (if they exist)
      start_fn = object['ofns'][0] - 50
      end_fn = object['ofns'][-1] + 50
      if start_fn < 0:
         start_fn = 0
      if end_fn > len(frames) - 1:
         end_fn = len(frames) - 1  

      # Detect motion contours in the frame set
      print("DETECTING MOTION CNTS", video_file)
      cnt_frames = detect_motion_in_frames(subframes[start_fn:end_fn], video_file, start_fn) 

      #for cnt in cnt_frames:
      #   print("CONTOUR:", cnt, cnt_frames[cnt])

      # DETECTION FINAL - PHASE 3
      print("DETECT PHASE 3!")
      # Determine the first and last frames that contain motion objects
      first_fn = None
      last_fn = 0
      for fn in cnt_frames:
         if len(cnt_frames[fn]['xs']) > 0:
            if first_fn is None:
               first_fn = fn 
            last_fn = fn 


      # Find the objects from the motion contours to make sure all of the contours belong to the meteor 
      
      final_objects = {} 
      print(cnt_frames)
      for xxx in cnt_frames:
         print(xxx, cnt_frames[xxx]) 


      final_objects = find_cnt_objects(cnt_frames, final_objects)
      real_meteors = {}

      for ooo in final_objects:
         print(ooo, final_objects[ooo])

      meteor_id = 1
      print("FIND MOTION CONTOURS!", final_objects)
      for obj in final_objects:

         final_objects[obj] = merge_obj_frames(final_objects[obj])

         if final_objects[obj]['report']['meteor_yn'] == 'Y':
            print("FINAL:", obj, final_objects[obj])
            
            real_meteors[meteor_id] = final_objects[obj]
            meteor_id = meteor_id + 1

      # check for missing frames inside the meteor start and end
      real_meteors = check_fix_missing_frames(real_meteors)

      meteor_crop_frames = {}
      # determine the brightest pixel point value and x,y position for each frame and save it in the object

      # determine the blob center x,y position and sum bg subtracted inensity value for each frame and save it in the object

      # determine the meteor's 'leading edge' x,y position and sum bg subtracted crop inensity value (based on bounded original CNT w,h) for each pixel and save it in the object

      # if there is just 1 meteor finish the job

      print("FINISH THE JOB!", real_meteors)

      for meteor_obj in real_meteors:
         bad_frames = []
         print("REAL METEOR:", meteor_obj, real_meteors[meteor_obj])
         # find the meteor movement direction:
         x_dir_mod,y_dir_mod = meteor_dir(real_meteors[meteor_obj]['oxs'][0], real_meteors[meteor_obj]['oys'][0], real_meteors[meteor_obj]['oxs'][-1], real_meteors[meteor_obj]['oys'][-1])

         meteor_crop_frames[meteor_obj] = []
         lc = 0
         if len(real_meteors[meteor_obj]['ofns']) != len(real_meteors[meteor_obj]['oxs']):
            print("BAD OBJECT: ", real_meteors[meteor_obj])
            return(0, "BAD OBJECT")
         print("RANGE:", 0, len(real_meteors[meteor_obj]['ofns'])-1)
         for jjj in range(0, len(real_meteors[meteor_obj]['ofns'])-1):
            bad = 0
            fn = real_meteors[meteor_obj]['ofns'][jjj]
            x = real_meteors[meteor_obj]['oxs'][jjj]
            y = real_meteors[meteor_obj]['oys'][jjj]
            w = real_meteors[meteor_obj]['ows'][jjj]
            h = real_meteors[meteor_obj]['ohs'][jjj]

            if w > h : 
               sz = int(w / 2)
            else:
               sz = int(h / 2)
            cx1,cy1,cx2,cy2= bound_cnt(x,y,frames[0].shape[1],frames[0].shape[0], sz)
            #print ("CONTOUR AREA:", cx1, cy1, cx2, cy2)
            show_frame = frames[fn]
           
            cnt_frame = frames[fn][cy1:cy2, cx1:cx2]
            cnt_bg = frames[fn-1][cy1:cy2, cx1:cx2]

            sub_cnt_frame = cv2.subtract(cnt_frame, cnt_bg)
            sum_val =cv2.sumElems(sub_cnt_frame)[0]
            cnt_val =cv2.sumElems(cnt_frame)[0]
            bg_val =cv2.sumElems(cnt_bg)[0]
            #print("INTESITY (BG, CNT, DIFF):", bg_val, cnt_val, sum_val)

            #print("SHAPE:", sub_cnt_frame.shape)

            sub_cnt_frame = cv2.resize(sub_cnt_frame, (0,0),fx=20, fy=20)
            min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(sub_cnt_frame)
            contours, rects= find_contours_in_frame(sub_cnt_frame, int(max_val/2))
            if len(contours) == 0:
               bad_frames.append(jjj)
               bad = 1
            if len(contours) > 0:
               contours = merge_contours(contours)

            cnt_rgb = cv2.cvtColor(sub_cnt_frame.copy(),cv2.COLOR_GRAY2RGB)
            desc = str(x_dir_mod) + "," + str(y_dir_mod)

            # x dir mod / y dir mod
            # -1 x is left to right, leading edge is right side of obj (x+w)
            # -1 y is top to down, leading edge is bottom side of obj (y+h)
            # +1 x is left to right, leading edge is right side of obj (x)
            # +1 y is top to down, leading edge is bottom side of obj (y)

            cv2.putText(cnt_rgb, str(desc),  (10,10), cv2.FONT_HERSHEY_SIMPLEX, .3, (255, 255, 255), 1)
            for x,y,w,h in contours:
               if x_dir_mod == 1:
                  leading_x = x 
               else:
                  leading_x = x + w 
               if y_dir_mod == 1:
                  leading_y = y 
               else:
                  leading_y =  y + h

               leading_edge_x_size = int(w / 2.5) 
               leading_edge_y_size = int(h / 2.5) 

               le_x1 = leading_x
               le_x2 = leading_x + (x_dir_mod*leading_edge_x_size)
               le_y1 = leading_y
               le_y2 = leading_y + (y_dir_mod*leading_edge_y_size)
               tm_y = sorted([le_y1,le_y2])
               tm_x = sorted([le_x1,le_x2])
               le_x1 = tm_x[0]
               le_x2 = tm_x[1]
               le_y1 = tm_y[0]
               le_y2 = tm_y[1]
               le_cnt = sub_cnt_frame[le_y1:le_y2,le_x1:le_x2]
               min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(le_cnt)
               #if le_cnt.shape[0] > 0 and le_cnt.shape[1] > 0:
               le_x = mx + (le_x1) 
               le_y = my + (le_y1) 
               cv2.circle(cnt_rgb,(le_x,le_y), 5, (255,0,0), 1)

               cv2.rectangle(cnt_rgb, (x, y), (x+w, y+h), (255,255,255), 1, cv2.LINE_AA) 
               cv2.rectangle(cnt_rgb, (leading_x, leading_y), (leading_x+(x_dir_mod*leading_edge_x_size), leading_y+(y_dir_mod*leading_edge_y_size)), (255,255,255), 1, cv2.LINE_AA) 

               if "leading_x" not in real_meteors[meteor_obj]:
                  real_meteors[meteor_obj]['leading_x'] = []
                  real_meteors[meteor_obj]['leading_y'] = []

               #print("LEADING X INFO: ", cx1, cy1, le_x, le_y)
               real_meteors[meteor_obj]['leading_x'].append(int((le_x / 20) + cx1))
               real_meteors[meteor_obj]['leading_y'].append(int((le_y / 20) + cy1))


            cv2.circle(cnt_rgb,(mx,my), 5, (255,255,255), 1)
            if bad == 1:
               cv2.putText(cnt_rgb, "bad frame",  (25,25), cv2.FONT_HERSHEY_SIMPLEX, .3, (255, 255, 255), 1)
           
            lc = lc + 1
      data_x = []
      data_y = []
      gdata_x = []
      gdata_y = []


      for id in real_meteors:
         meteor_obj = real_meteors[id]
         max_x = len(meteor_obj['ofns'])
         max_y = 0
         all_lx = []
         all_ly = []
         all_fn = []
         for i in range(0,len(meteor_obj['ofns'])-1):
            fn = meteor_obj['ofns'][i]
            if "leading_x" in meteor_obj:
               try:
                  lx = meteor_obj['leading_x'][i]
                  ly = meteor_obj['leading_y'][i]       
                  meteor_obj['no_leading_xy'] = 1
               except:
                  lx = meteor_obj['oxs'][i]
                  ly = meteor_obj['oys'][i]
               all_lx.append(lx)
               all_ly.append(ly)
               all_fn.append(fn)
            else:
               print("NO LEADING X FOUND FOR ", id, fn)


         for i in range(0,len(meteor_obj['ofns'])-1):
            fn = meteor_obj['ofns'][i]
            try:
               lx = meteor_obj['leading_x'][i]
               ly = meteor_obj['leading_y'][i]
            except:
               lx = meteor_obj['oxs'][i]
               ly = meteor_obj['oys'][i]
            gdata_x.append(lx)
            gdata_y.append(ly)
            lx1,ly1,lx2,ly2= bound_cnt(lx,ly,frames[0].shape[1],frames[0].shape[0], 30)
            tracker_cnt = color_frames[fn][ly1:ly2,lx1:lx2]
            tracker_bg = frames[0][ly1:ly2,lx1:lx2]

            tracker_cnt_gray = cv2.cvtColor(tracker_cnt, cv2.COLOR_BGR2GRAY)
            subtracker = cv2.subtract(tracker_cnt_gray, tracker_bg)
            sum_val =cv2.sumElems(subtracker)[0]
            data_y.append(sum_val)
            data_x.append(i)

            tracker_cnt = cv2.resize(tracker_cnt, (180,180))
            graph_x = 500 
            graph_y = 200 
            graph = custom_graph(data_x,data_y,max_x,max_y,graph_x,graph_y,"line")

            graph_xy = custom_graph(gdata_x,gdata_y,max(all_lx) + 10,max(all_ly)+10,300,300,"scatter")
            info = {}
            cf = color_frames[fn].copy()
            cv2.circle(cf,(lx,ly), 10, (255,255,255), 1) 
 
            custom_frame = make_custom_frame(cf,subframes[fn],tracker_cnt,graph, graph_xy, info)

            #graph = cv2.resize(graph, (150,500))
            cv2.line(tracker_cnt, (74,0), (74,149), (128,128,128), 1) 
            cv2.line(tracker_cnt, (0,74), (149,74), (128,128,128), 1) 

            #print("TRACKER SHAPE:", tracker_cnt.shape)
            show_frame = color_frames[fn]

            tr_y1 = color_frames[0].shape[0] - 5 - graph_y
            tr_y2 = tr_y1 + graph_y
            tr_x1 = 5
            tr_x2 = tr_x1 + graph_y

            gr_y1 = color_frames[0].shape[0] - 5 - graph_y
            gr_y2 = gr_y1 + graph_y

            gr_x1 = tr_x2 + 10 
            gr_x2 = gr_x1 + graph_x 


            #print("PLACEMENT:", tr_y1,tr_y2, tr_x1, tr_x2)

            #show_frame[tr_y1:tr_y2,tr_x1:tr_x2] = tracker_cnt 
            #show_frame[gr_y1:gr_y2,gr_x1:gr_x2] = graph 

            #print("LEAD:", fn,lx,ly)

            cv2.circle(show_frame,(lx,ly), 10, (255,255,255), 1)
            cv2.rectangle(show_frame, (tr_x1, tr_y1), (tr_x2, tr_y2), (255,255,255), 1, cv2.LINE_AA)

   # End of processing and meteor detection. 
   # Save data file, make trim clips
   # Apply calibration 
   # Upload / Register Meteor

      data_file = video_file.replace(".mp4", "-meteor.json")
      save_json_file(data_file, real_meteors)

   elapsed_time = time.time() - start_time
   print("Detected BP.", elapsed_time)
   bin_days = []
   bin_events = []
   bin_avgs = []
   bin_sums = []

   #for object in objects:
   #   for key in objects[object]['report']:
   #      print(object, key, objects[object]['report'][key])

   elapsed_time = time.time() - start_time
   print("Elapsed time:", elapsed_time)


   # Nothing matters after this????
   return(1, "Meteor Detected.")


   # Check for frames with 2x running sum brightness of the subtracted / frame. for frames with cm>= 3 create an event. there are trackable events with at least 3 frames of consecutive motion

   for fn in bp_frame_data:
      bin_days.append(fn)
      bin_avgs.append(bp_frame_data[fn]['avg_val'])
      bin_sums.append(bp_frame_data[fn]['sum_val'])
      bin_events.append(bp_frame_data[fn]['max_val'])
      if len(bin_sums) < 100:
         running_sum = np.median(bin_sums)
      else:
         running_sum = np.median(bin_sums[-99:])

      if bp_frame_data[fn]['sum_val'] > running_sum * 2:
         event.append(fn)
         cm = cm + 1
         no_mo = 0
      else:
         no_mo = no_mo + 1
      if cm >= 3 and no_mo >= 5:
         bright_events.append(event)
         cm = 0
         event = []
      if no_mo >= 5:
         cm = 0
         event = []

   # Review the events
   ec = 0
   for event in bright_events:
      if len(event) > 3:
         #for fn in event:
            #show_frame = frames[fn].copy()
            #cv2.circle(show_frame,(bp_frame_data[fn]['max_loc'][0],bp_frame_data[fn]['max_loc'][1]), 10, (255,255,255), 1)
            #desc = "EVENT: " + str(ec) + " FRAME: " + str(fn)
            #cv2.putText(show_frame, desc,  (10,10), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
         ec = ec + 1


     
   if False:
      import matplotlib
      #matplotlib.use('Agg')
      import matplotlib.pyplot as plt
      #fig = plt.figure()
      #plt.plot(bin_days,bin_events, bin_avgs, bin_sums)
      plt.plot(bin_days,bin_sums)
      #plt.show()
      curve_file = "figs/detect.png"
      plt.savefig(curve_file)

   if len(bright_events) > 0:
      for event in bright_events:
         ts_stat = []
         fail = 0
         for fn in range(event[0], event[-1]):
            thresh_val = 20
            _ , thresh_img = cv2.threshold(subframes[fn].copy(), thresh_val, 255, cv2.THRESH_BINARY)
            thresh_sub_sum = np.sum(thresh_img)
            if thresh_sub_sum > 0:
               #print("THRESH SUM:", fn, thresh_sub_sum)
               ts_stat.append(fn)
         if len(ts_stat) < 3:
            #print("Not a valid event, just noise.")
            fail = 1
         else:
            print("Possible event, Frames above thresh.", len(ts_stat))
            elp = ts_stat[-1] - ts_stat[0]
            
            ratio = len(ts_stat) / elp
            if ratio < .6:
               print("Thresh hit to elp frame ratio to low. Not valid event. ", elp, len(ts_stat), ratio)
               fail = 1

         if fail == 0: 
         
            print("EVENT:", event)
            objects = {}
            motion_events,objects = check_event_for_motion(subframes[event[0]-10:event[-1]+10], objects, event[0]-10)
            meteor_objects = meteor_tests(objects)
            print("METEOR?:", meteor_objects)
            if len(meteor_objects) > 0:
               valid_events.append(event)

               meteor_file = video_file.replace(".mp4", "-meteor.json")
               meteor_json = {}
               meteor_json['meteor'] = meteor_objects
               save_json_file(meteor_file, meteor_json)

               event_file = video_file.replace(".mp4", "-trim-" + str(event[0]) + ".mp4")
               subframe_event_file = video_file.replace(".mp4", "subframes-trim-" + str(event[0]) + ".mp4")
               make_movie_from_frames(frames, [event[0]-10,event[-1] - 1+10], event_file , 1)
               make_movie_from_frames(subframes, [event[0]-10,event[-1] - 1+10], subframe_event_file , 1)


   else:
      print("No bright events found.")

   if len(valid_events) > 0:
      data_file = video_file.replace(".mp4", "-events.json")
      event_json = {}
      event_json['events'] = valid_events




      save_json_file(data_file, event_json)
   elapsed_time = time.time() - start_time
   print("Total Run Time.", elapsed_time)

def buffered_start_end(start,end, total_frames, buf_size):
   print("BUF: ", total_frames)
   bs = start - buf_size
   if buf_size < 20:
      buf_size = 20
   be = end + buf_size
   if bs < 0:
      bs = 0
   if be >= total_frames:
      be = total_frames - 1

   return(bs,be)
    

def make_custom_frame(frame, subframe, tracker, graph, graph2, info):
   subframe = cv2.cvtColor(subframe,cv2.COLOR_GRAY2RGB)
   custom_frame = np.zeros((720,1280,3),dtype=np.uint8)
   small_frame = cv2.resize(frame, (900,506))
   small_subframe = cv2.resize(subframe, (320,180))

   tracker = cv2.resize(tracker, (200,200))
   # main frame location
   fx1 = 0 
   fy1 = 0 
   fx2 = 0 + small_frame.shape[1]
   fy2 = 0 + small_frame.shape[0]

   sfx1 = fx2
   sfy1 = 0
   sfx2 = sfx1 + small_subframe.shape[1]
   sfy2 = 0 + small_subframe.shape[0]

   xygx1 = sfx1
   xygx2 = sfx1 + graph2.shape[1]
   xygy1 = sfy2
   xygy2 = sfy2 + graph2.shape[0]

   #tracker location
   trx1 = 0
   try1 = small_frame.shape[0] 
   trx2 = trx1 + tracker.shape[1] 
   try2 = try1 + tracker.shape[0] 

   # graph location
   grx1 = trx2 
   gry1 = small_frame.shape[0] 
   grx2 = grx1 + graph.shape[1] 
   gry2 = gry1 + graph.shape[0] 

   custom_frame[fy1:fy2,fx1:fx2] = small_frame
   custom_frame[sfy1:sfy2,sfx1:sfx2] = small_subframe
   custom_frame[try1:try2,trx1:trx2] = tracker
   custom_frame[gry1:gry2,grx1:grx2] = graph
   custom_frame[xygy1:xygy2,xygx1:xygx2] = graph2 

   cv2.rectangle(custom_frame, (fx1, fy1), (fx2, fy2), (255,255,255), 1, cv2.LINE_AA)
   cv2.rectangle(custom_frame, (sfx1, sfy1), (sfx2, sfy2), (255,255,255), 1, cv2.LINE_AA)
   cv2.rectangle(custom_frame, (trx1, try1), (trx2, try2), (255,255,255), 1, cv2.LINE_AA)


def custom_graph(data_x,data_y,max_x,max_y,graph_x,graph_y,type):

   fig_x = graph_x / 100
   fig_y = graph_y / 100
   import matplotlib
   #matplotlib.use('Agg')
   import matplotlib.pyplot as plt

   fig = plt.figure(figsize=(fig_x,fig_y), dpi=100)
   plt.xlim(0,max_x)
   if type == 'line':
      plt.plot(data_x,data_y)
   if type == 'scatter':
      plt.scatter(data_x, data_y)
      ax = plt.gca()
      #ax.invert_xaxis()
      ax.invert_yaxis()

   curve_file = "figs/curve.png"
   fig.savefig(curve_file, dpi=100)
   plt.close()

   graph = cv2.imread(curve_file)
   return(graph)




def merge_contours(contours):
   cx = []
   cy = []
   cw = []
   ch = []
   new_contours = []
   for x,y,w,h in contours:
      cx.append(x)
      cy.append(y)
      cx.append(x+w)
      cy.append(y+h)
   nx = min(cx)
   ny = min(cy)
   nw = max(cx) - nx
   nh = max(cy) - ny

   new_contours.append((nx,ny,nw,nh))
   return(new_contours)

def merge_obj_frames(obj):
   merged = {}
   new_fns = []
   new_xs = []
   new_ys = []
   new_ws = []
   new_hs = []

   fns = obj['ofns']
   xs  = obj['oxs']
   ys  = obj['oys']
   ws  = obj['ows']
   hs  = obj['ohs']
   #for i in range(0, len(fns) - 1):
   for i in range (0,len(fns) -1):
      fn = fns[i]
      if fn not in merged: 
         merged[fn] = {}
         merged[fn]['xs'] = []
         merged[fn]['ys'] = []
         merged[fn]['ws'] = []
         merged[fn]['hs'] = []
      merged[fn]['xs'].append(xs[i])
      merged[fn]['ys'].append(ys[i])
      merged[fn]['ws'].append(ws[i])
      merged[fn]['hs'].append(hs[i])

   for fn in merged:
      merged[fn]['fx'] = int(np.mean(merged[fn]['xs']))
      merged[fn]['fy'] = int(np.mean(merged[fn]['ys']))
      merged[fn]['fw'] = int(max(merged[fn]['ws']))
      merged[fn]['fh'] = int(max(merged[fn]['hs']))
      new_fns.append(fn)
      new_xs.append(merged[fn]['fx'])
      new_ys.append(merged[fn]['fy'])
      new_ws.append(merged[fn]['fw'])
      new_hs.append(merged[fn]['fh'])

   obj['ofns'] = new_fns
   obj['oxs'] = new_xs
   obj['oys'] = new_ys
   obj['ows'] = new_ws
   obj['ohs'] = new_hs

   print(obj)

   return(obj)      

def check_fix_missing_frames(objects):
   for object in objects:
      fns = objects[object]['ofns']
      elp_fns = fns[-1] - fns[0]
      total_fns = len(fns) - 1
      if elp_fns == total_fns:
         print("NO MISSING FRAMES HERE! ", elp_fns, len(fns)-1)
      else:
         print("MISSING FRAMES FOUND IN METEOR FRAME SET FIXING! ", elp_fns, len(fns)-1)

   return(objects)

def object_report(objects):
   report = ""
   for object in objects: 
      report = report + "FNs: " +str(object['ofns'] + "\n")
      report = report + "Xs: " +str(object['oxs'] + "\n")
      report = report + "Ys: " +str(object['oys'] + "\n")

      for key in object['report']:
         report = report + "   " + str(key) + str(object['report'][key])
      start_fn = object['ofns'][0] - 50
      end_fn = object['ofns'][-1] + 50
      print("START END:", start_fn, end_fn)
      if start_fn < 0:
         start_fn = 0
      if end_fn > len(frames) - 1:
         end_fn = len(frames) - 1
      report = report + "START END: " + str(start_fn) + " " + str(end_fn)
   return(report)


def find_events_from_bp_data(bp_data,subframes):
   events = []
   event = []
   objects = {}
   avg_sum = np.median(bp_data)
   for i in range(0,len(bp_data)):
      if i > 0 and i < len(bp_data) - 1:
         if i > 50 and i < len(bp_data) - 50:
            avg_sum = np.median(bp_data[i-50:i])
         prev_sum_val = bp_data[i-1]
         sum_val = bp_data[i]
         next_sum_val = bp_data[i+1]
         if sum_val > avg_sum * 2 and prev_sum_val > avg_sum * 2:
            event.append(i)
         elif sum_val > avg_sum * 2 and prev_sum_val > avg_sum * 2 and next_sum_val > avg_sum * 2:
            event.append(i)
         elif sum_val > avg_sum * 2 and next_sum_val > avg_sum * 2:
            event.append(i)
         else:
            if len(event) > 2:
               events.append(event)
               event = []
            else:
               event = []

   for event in events:
      for fn in event:
         contours, rects= find_contours_in_frame(subframes[fn])
         for ct in contours:
            object, objects = find_object(objects, fn,ct[0], ct[1], ct[2], ct[3])

   print("EVENTS:",events)
   print("OBJECTS:",objects)

   return(events, objects) 

def meteor_tests(objects):
   meteor_objects = []
   for obj in objects:
      if len(objects[obj]['oxs']) > 3:
         one_dir_test_result = one_dir_test(objects[obj])
         dist_test_result = dist_test(objects[obj])
         gap_test_result = gap_test(objects[obj])

         if one_dir_test_result == 1 and dist_test_result == 1 and gap_test_result == 1:
            print(obj, objects[obj])
            meteor_objects.append(objects[obj])

      if len(meteor_objects) == 0:
         print("No meteor objects.")
         for obj in objects:
            print(obj, objects[obj])
   return(meteor_objects)

def check_event_for_motion(subframes, objects, fn):
   thresh_val = 20 
   motion_events = []
   cnt_frames = {} 
   #fn = 0
   for frame in subframes:
      cnt_frames[fn] = {}
      cnt_frames[fn]['xs'] = [] 
      cnt_frames[fn]['ys'] = [] 
      cnt_frames[fn]['ws'] = [] 
      cnt_frames[fn]['hs'] = [] 

      _ , thresh_img = cv2.threshold(frame.copy(), thresh_val, 255, cv2.THRESH_BINARY)
      cnt_res = cv2.findContours(thresh_img.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
      if len(cnt_res) == 3:
         (_, cnts, xx) = cnt_res
      elif len(cnt_res) == 2:
         (cnts, xx) = cnt_res
      pos_cnts = []
      if len(cnts) > 3:
         # Too many cnts be more restrictive!
         thresh_val = thresh_val + 5
         _ , thresh_img = cv2.threshold(thresh_img.copy(), thresh_val, 255, cv2.THRESH_BINARY)
         cnt_res = cv2.findContours(thresh_img.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
         if len(cnt_res) == 3:
            (_, cnts, xx) = cnt_res
         elif len(cnt_res) == 2:
            (cnts, xx) = cnt_res

      if len(cnts) > 0:
         for (i,c) in enumerate(cnts):
            x,y,w,h = cv2.boundingRect(cnts[i])
            cnt_frames[fn]['xs'].append(x)
            cnt_frames[fn]['ys'].append(y)
            cnt_frames[fn]['ws'].append(w)
            cnt_frames[fn]['hs'].append(h)
      fn = fn + 1

   objects = find_cnt_objects(cnt_frames, objects)


   return(motion_events, objects)      


def stack_frames_fast_old(frames, skip = 1, resize=None):
   stacked_image = None
   fc = 0
   for frame in frames:
      if resize is not None:
         frame = cv2.resize(frame, (resize[0],resize[1]))
      if fc % skip == 0:
         frame_pil = Image.fromarray(frame)
         if stacked_image is None:
            stacked_image = stack_stack(frame_pil, frame_pil)
         else:
            stacked_image = stack_stack(stacked_image, frame_pil)

      fc = fc + 1
   return(np.asarray(stacked_image))

def stack_stack(pic1, pic2):
   stacked_image=ImageChops.lighter(pic1,pic2)
   return(stacked_image)

def load_frames_fast(trim_file, json_conf, limit=0, mask=0,crop=(),color=0,resize=[]):
   print("TRIM FILE:", trim_file)
   (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(trim_file)
   cam = cam.replace("-vals.json", "")
   cap = cv2.VideoCapture(trim_file)
   masks = None
   last_frame = None
   last_last_frame = None

   print("CAM " + cam)

   if "HD" in trim_file:
      masks = get_masks(cam, json_conf,1)
   else:
      masks = get_masks(cam, json_conf,0)
   if "crop" in trim_file:
      masks = None

   color_frames = []
   frames = []
   subframes = []
   sum_vals = []
   pos_vals = []
   max_vals = []
   frame_count = 0
   go = 1
   while go == 1:
      if True :
         _ , frame = cap.read()
         if frame is None:
            if frame_count <= 5 :
               cap.release()
               return(frames,color_frames,subframes,sum_vals,max_vals,pos_vals)
            else:
               go = 0
         else:
            if color == 1:
               color_frames.append(frame)
            if limit != 0 and frame_count > limit:
               cap.release()
               return(frames,color_frames,subframes,sum_vals,max_vals,pos_vals)
            if len(frame.shape) == 3 :
               frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            if mask == 1 and frame is not None:
               if frame.shape[0] == 1080:
                  hd = 1
               else:
                  hd = 0
               if masks is not None:
                  frame = mask_frame(frame, [], masks, 5)

            if last_frame is not None:
               subframe = cv2.subtract(frame, last_frame)
               #subframe = mask_frame(subframe, [], masks, 5)
               sum_val =cv2.sumElems(subframe)[0]
  
               if sum_val > 10 and last_last_frame is not None:
                  _, thresh_frame = cv2.threshold(subframe, 15, 255, cv2.THRESH_BINARY)

                  sum_val =cv2.sumElems(thresh_frame)[0]
               subframes.append(subframe)


               if sum_val > 100:
                  min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(subframe)
               else:
                  max_val = 0
                  mx =0
                  my =0
               if frame_count < 5:
                  sum_val = 0
                  max_val = 0
               sum_vals.append(sum_val)
               max_vals.append(max_val)
               pos_vals.append((mx,my))

            if len(crop) == 4:
               ih,iw = frame.shape
               x1,y1,x2,y2 = crop
               x1 = x1 - 25
               y1 = y1 - 25
               x2 = x2 + 25
               y2 = y2 + 25
               if x1 < 0:
                  x1 = 0
               if y1 < 0:
                  y1 = 0
               if x1 > iw -1:
                  x1 = iw -1
               if y1 > ih -1:
                  y1 = ih -1
               crop_frame = frame[y1:y2,x1:x2]
               frame = crop_frame
            if len(resize) == 2:
               frame = cv2.resize(frame, (resize[0],resize[1]))
       
            frames.append(frame)
            if last_frame is not None:
               last_last_frame = last_frame
            last_frame = frame
      frame_count = frame_count + 1
   cap.release()
   if len(crop) == 4:
      return(frames,x1,y1)
   else:
      return(frames, color_frames, subframes, sum_vals, max_vals,pos_vals)


def update_hd_path(file):
   (hd_datetime, cam, sd_date, sd_y, sd_m, sd_d, sd_h, sd_M, sd_s) = convert_filename_to_date_cam(file)
   if "/mnt/ams2/HD/" in file:
      ff = file.split("/")[-1]
      new_file = "/mnt/ams2/meteors/" + sd_y + "_" + sd_m + "_" + sd_d + "/" + ff
      return(new_file)
   else:
      return(file)
     

def make_frame_crop_summary(frames, obj, trim_num_start):
   crops = []
   frame_data = {}
   print(obj)
   for i in range(obj['ofns'][0]-trim_num_start, obj['ofns'][-1]-trim_num_start+1):
      frame_data[i] = {}

   for i in range(0, len(obj['ofns'])):
      fn = obj['ofns'][i] - trim_num_start
      x = obj['oxs'][i]
      y = obj['oys'][i]
      w = obj['ows'][i]
      h = obj['ohs'][i]
      oint  = obj['oint'][i]

      frame_data[fn]['x'] = x
      frame_data[fn]['y'] = y
      frame_data[fn]['w'] = w
      frame_data[fn]['h'] = h
      frame_data[fn]['oint'] = oint

      oint = obj['oint'][i]
      print("FRAMES:", len(frames), fn)
      cx1,cy1,cx2,cy2 = bound_cnt(x,y,frames[0].shape[1], frames[0].shape[0],25)
      frame_data[fn]['frame_crop'] = [cx1,cy1,cx2,cy2]
      frame = frames[fn].copy()
     
      cv2.circle(frame,(x,y), 5, (255,255,255), 1)
  
 

   for fn in frame_data:
      if "x" not in frame_data[fn]:
         frame_data[fn]['x'] = last_x
         frame_data[fn]['y'] = last_y
         frame_data[fn]['w'] = last_w
         frame_data[fn]['h'] = last_h
         frame_data[fn]['fixed'] = 1
         cx1,cy1,cx2,cy2 = bound_cnt(x,y,frames[0].shape[1], frames[0].shape[0],10)
         frame_data[fn]['frame_crop'] = [cx1,cy1,cx2,cy2]
      else:
         x = frame_data[fn]['x']
         y = frame_data[fn]['y']
         w = frame_data[fn]['w']
         h = frame_data[fn]['h']

      last_x = x
      last_y = y
      last_w = w
      last_h = h


   # each crop is 50 x 50 so
   # so we can fit a max of 38 frames across an HD image
   # determine rows as total_frames / 38
   rows = math.ceil(len(frame_data) / 18)
   crop_sum_x = 1920
   crop_sum_y = rows * 100
   crop_sum_img = np.zeros((crop_sum_y,crop_sum_x,3),dtype=np.uint8)
  
   fc = 0 
   cc = 0 
   row_y = 0
   for fn in frame_data:
      cx1,cy1,cx2,cy2 = frame_data[fn]['frame_crop']
      x =  frame_data[fn]['x']
      y =  frame_data[fn]['y']
    
      if show == 1: 
         cv2.circle(frames[fn],(x,y), 2, (0,255,0), 1)   
         cv2.imshow("frame crop summary", frames[fn])
         cv2.waitKey(70)
      crop_img = frames[fn][cy1:cy2,cx1:cx2]

      nx1 = cc * 100
      nx2 = nx1 + 100
      ny1 = row_y 
      ny2 = row_y + 100
      crop_img = cv2.resize(crop_img,(100,100)) 
      crop_img = cv2.cvtColor(crop_img,cv2.COLOR_GRAY2RGB)
      if crop_img.shape[0] == 100 and crop_img.shape[1] == 100:
         crop_sum_img[ny1:ny2,nx1:nx2] = crop_img 
      if show == 1:
         cv2.imshow("frame crop summary", crop_img)
         cv2.waitKey(70)


      fc = fc + 1
      cc = cc + 1
      if fc % 18 == 0 and fc > 0 :
         row_y = row_y + 100
         cc  = 0
   if show == 1:
      cv2.imshow('frame crop summary', crop_sum_img)
      cv2.waitKey(70)

   if show == 1:
      cv2.destroyWindow('frame crop summary')


   return(crop_sum_img,frame_data)

def get_trim_num(file):
   xxx = file.split("trim")[-1]
   xxx = xxx.replace(".mp4", "")
   return(int(xxx))

def flex_sync_hd_frames(video_file, hd_frames, hd_crop_frames, sd_frames,obj):
   print("Sync HD Frames:")    
   crop_x = obj['crop_box'][0]
   crop_y = obj['crop_box'][1]

   #len(obj['ofns'])):  
   for i in range(0, 5):
       
      sd_fn = obj['ofns'][i]
      first_x = obj['oxs'][i]
      first_y = obj['oys'][i]
      first_w = obj['ows'][i]
      first_h = obj['ohs'][i]

      hdm_x =  hd_frames[0].shape[1] / sd_frames[0].shape[1] 
      hdm_y =  hd_frames[0].shape[0] / sd_frames[0].shape[0]

      hd_x1 = int(first_x * hdm_x) 
      hd_y1 = int(first_y * hdm_y) 
      hd_x2 = (int(first_x * hdm_x) ) + int(hdm_x * first_w)
      hd_y2 = (int(first_y * hdm_y) ) + int(hdm_y * first_h)

      

      cx1,cy1,cx2,cy2 = bound_cnt(hd_x1-crop_x,hd_y1-crop_y,hd_crop_frames[0].shape[1],hd_crop_frames[0].shape[0], 40)
      #cx1, cy1,cx2,cy2 = hd_x1,hd_y1, hd_x2, hd_y2 

      #find_hd_frame(hd_frames, cx1,cy1,cx2,cy2)
      find_hd_frame(hd_crop_frames, cx1,cy1,cx2,cy2)

def find_hd_frame(hd_crop_frames, cx1,cy1,cx2,cy2):
   last_frame = hd_crop_frames[0]
   max_int = 0
   max_px = 0
   max_fn = 0

   fc = 0
   for frame in hd_crop_frames:
      sub_frame = cv2.subtract(frame,last_frame)
      crop_hd_crop = sub_frame[cy1:cy2,cx1:cx2]
      min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(crop_hd_crop)
      intense = np.sum(crop_hd_crop)
      if intense >  max_int:
         max_int = intense
         best_fn_int = fc
      if max_val >  max_px:
         max_px = max_val
         best_fn_px = fc
       
      
      last_frame = frame
      fc = fc + 1
   print("Best matching frame: ", best_fn_int, best_fn_px)


def refine_points(frames, frame_data):
   last_frame = frames[0]
   max_vals = []
   seg_dists = []
   last_max_x = None
   last_max_y = None
   med_seg_dist = 0
   for fn in frame_data:
      frame = frames[fn].copy()
      subframe = cv2.subtract(frame,frames[0])
      cx1,cy1,cx2,cy2 = bound_cnt(frame_data[fn]['x'],frame_data[fn]['y'],frames[0].shape[1],frames[0].shape[0], 20)
      crop = subframe[cy1:cy2,cx1:cx2]
      min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(crop)
      max_vals.append(max_val)
      med_max_val = np.median(max_vals)
      max_x = mx + cx1
      max_y = mx + cy1
      frame_data[fn]['max_x'] = max_x
      frame_data[fn]['max_y'] = max_y
      frame_data[fn]['max_val'] = max_val
      if last_max_x is not None:
         frame_data[fn]['seg_dist'] = calc_dist((max_x, max_y) , (last_max_x, last_max_y))
         seg_dists.append(frame_data[fn]['seg_dist'])
         med_seg_dist = np.median(seg_dists)

      print("MED:", med_max_val, med_seg_dist)
      if max_val < med_max_val:
         frame_data[fn]['max_val_bad'] = max_val - med_max_val
      cx1,cy1,cx2,cy2 = bound_cnt(max_x,max_y,frames[0].shape[1],frames[0].shape[0], 20)
      crop = frame[cy1:cy2,cx1:cx2]
      last_max_x = max_x
      last_max_y = max_y
 
def review_meteor(video_file):
   custom_frame = np.zeros((1080,1920,3),dtype=np.uint8)
   json_file= video_file.replace(".mp4", ".json")
   stack_file = video_file.replace(".mp4", "-stacked.png")
   trim_num = get_trim_num(video_file)

   frames,color_frames,subframes,sum_vals,max_vals,pos_vals = load_frames_fast(video_file, json_conf, 0, 0, [], 0,[])


   if cfe(stack_file) == 1:
      stack_img = cv2.imread(stack_file)
   else:
      stack_file, stack_img = stack_frames(frames,video_file,0)
      stack_img = cv2.cvtColor(stack_img,cv2.COLOR_GRAY2RGB)

   data = load_json_file(json_file)  
   fd = data['flex_detect'] 

   sd_crop_sum_img,frame_data = make_frame_crop_summary(frames, fd, trim_num)

   #refine_points(frames, frame_data)

   hd_trim = update_hd_path(fd['hd_trim'])
   fd['hd_trim'] = hd_trim
   hd_crop_file = update_hd_path(fd['hd_crop_file'])
   if hd_trim != 0:
      hd_stack_file = hd_trim.replace(".mp4", "-stacked.png")
      half_stack_file = hd_trim.replace(".mp4", "half-stack.png")
      if cfe(hd_stack_file) == 0:
         print("HD STACK NOT EXIST")
         hd_frames,hd_color_frames,hd_subframes,sum_vals,max_vals,pos_vals = load_frames_fast(hd_trim, json_conf, 0, 0, [], 0,[])
         if cfe(hd_crop_file) == 1:
            hd_crop_frames,hd_crop_color_frames,hd_crop_subframes,sum_vals,max_vals,pos_vals = load_frames_fast(hd_crop_file, json_conf, 0, 0, [], 0,[])
         else:
            # make hd crop file and then load it in
            hd_crop_file, crop_box = crop_hd(fd, meteor_frames[0])
            fd['hd_crop_file'] = hd_crop_file
            hd_crop_frames,hd_crop_color_frames,hd_crop_subframes,sum_vals,max_vals,pos_vals = load_frames_fast(hd_crop_file, json_conf, 0, 0, [], 0,[])

         print("HDTRIM: ", hd_trim)
         print("FRAMES:", len(hd_frames))
         hd_stack_file, hd_stack_img = stack_frames(hd_frames,hd_trim,0)
         if show == 1:
            cv2.imshow('HD', hd_stack_img)
            cv2.waitKey(70)
         half_stack_img = cv2.resize(hd_stack_img, (0,0),fx=.5, fy=.5)
         cv2.imwrite(hd_stack_file, hd_stack_img) 
         cv2.imwrite(half_stack_file, half_stack_img) 
      else:
         print("HD STACK EXISTS")
         hd_frames,hd_color_frames,hd_subframes,sum_vals,max_vals,pos_vals = load_frames_fast(hd_trim, json_conf, 0, 0, [], 0,[])

         if cfe(hd_crop_file) == 1:
            hd_crop_frames,hd_crop_color_frames,hd_crop_subframes,sum_vals,max_vals,pos_vals = load_frames_fast(hd_crop_file, json_conf, 0, 0, [], 0,[])
         else:
            # make hd crop file and then load it in
            hd_crop_file, crop_box = crop_hd(fd, frames[0])
            fd['hd_crop_file'] = hd_crop_file
            hd_crop_frames,hd_crop_color_frames,hd_crop_subframes,sum_vals,max_vals,pos_vals = load_frames_fast(hd_crop_file, json_conf, 0, 0, [], 0,[])
         hd_stack_img = cv2.imread(hd_stack_file)
         if cfe(half_stack_file) == 1:
            half_stack_img = cv2.imread(half_stack_file)
         else:
            half_stack_img = cv2.resize(hd_stack_img, (0,0),fx=.5, fy=.5)
            cv2.imwrite(half_stack_file, half_stack_img) 
          
   if show == 1:
      cv2.destroyAllWindows("HD")
 

   #flex_sync_hd_frames(video_file, hd_frames, hd_crop_frames, frames,fd)


   print("Review Meteor Object:")
   x1,y1,x2,y2 = fd['crop_box']
   cv2.rectangle(stack_img, (x1, y1), (x2, y2), (255,255,255), 1, cv2.LINE_AA)
   for i in range(0, len(fd['ofns'])):
      x = fd['oxs'][i]
      y = fd['oys'][i]
      cv2.circle(stack_img,(x,y), 10, (255,255,255), 1)

   for key in fd:
      if key != 'hd_crop_objects' and key != 'report':
         print(key, fd[key])
      elif key == 'report':
         print("REPORT")
         for rk in fd['report']:
            print("   ", rk, fd['report'][rk])
   ih, iw = stack_img.shape[:2]
   hsih, hsiw = half_stack_img.shape[:2]


   for obj_id in fd['hd_crop_objects']:
      obj = fd['hd_crop_objects'][obj_id]
      print(obj)
      stack_img = draw_obj_on_frame(stack_img, obj)
      #x1,y1,x2,y2 = obj['crop_box']
      #cv2.rectangle(stack_img, (x1, y1), (x2, y2), (255,255,255), 1, cv2.LINE_AA)

   #custom_frame[0:ih,0:iw] = stack_img
   custom_frame[0:hsih,0:hsiw] = half_stack_img
   print("HSI:", half_stack_img.shape)
   print("HSI:", custom_frame.shape)
   print(ih, ih+hsih,0,hsiw)
   if show == 1:
      cv2.imshow('Review Meteor', custom_frame)
      cv2.waitKey(70)
       
def draw_obj_on_frame(frame, obj):
   for i in range(0, len(obj['ofns'])):
      x = obj['oxs'][i]
      y = obj['oys'][i]
      cv2.circle(frame,(x,y), 10, (0,255,0), 1)
   return(frame)

def write_archive_index(year,month):
   from lib.Archive_Listing import write_month_index, write_year_index
   print("Create json index month:", year, month)
   write_month_index(month,year)
   write_year_index(year)

   #write_index(year)

def move_to_archive(json_file):

   (hd_datetime, cam, sd_date, sd_y, sd_m, sd_d, sd_h, sd_M, sd_s) = convert_filename_to_date_cam(json_file)
   hd_vid = json_file.replace(".json", "-HD.mp4")
   sd_vid = json_file.replace(".json", "-SD.mp4")
   station_id = json_conf['site']['ams_id'].upper()
   meteor_dir = METEOR_ARCHIVE + station_id + "/" + METEOR + sd_y + "/" + sd_m + "/" + sd_d + "/"

   # If the new_folder doesn't exist, we create it
   if not os.path.exists(meteor_dir):
      os.makedirs(meteor_dir)

   # MOVE the files into the archive (All these files are prepped and named and ready to go.
   cmd = "cp /mnt/ams2/matmp/" + json_file + " " + meteor_dir
   print(cmd)
   os.system(cmd)
   cmd = "cp /mnt/ams2/matmp/" + hd_vid + " " + meteor_dir
   print(cmd)
   os.system(cmd)
   cmd = "cp /mnt/ams2/matmp/" + sd_vid + " " + meteor_dir
   print(cmd)
   os.system(cmd)
   cmd = "./MakeCache.py " + meteor_dir + json_file
   print(cmd)
   #os.system(cmd)
   return(meteor_dir)

def spectra(hd_stack):
   img = cv2.imread(hd_stack, 0)
   thresh_val = 100
   cnts,rects = find_contours_in_frame(img, thresh_val)
   for cnt in cnts:
      x,y,w,h = cnt
      if w > 20 or h > 20:
         cv2.rectangle(img, (x, y), (x+w, y+h), (255,255,255), 1, cv2.LINE_AA)

def rerun(video_file):
   day_dir = video_file[0:10]
   cmd = "cp /mnt/ams2/SD/proc2/" + day_dir + "/" + video_file + " /mnt/ams2/CAMS/queue/"
   print(cmd)
   os.system(cmd)
   cmd = "./flex-detect.py debug /mnt/ams2/CAMS/queue/" + video_file
   print(cmd)
   os.system(cmd)

def meteor_objects(objects):
   meteors = {}
   nonmeteors = {}
   mc = 1
   nc = 1
   for obj in objects:
      objects[obj] = analyze_object_final(objects[obj] )
      if objects[obj]['report']['meteor_yn'] == "Y":
         meteors[mc] = objects[obj]
         mc = mc + 1
      else:
         nonmeteors[nc] = objects[obj]
         nc = nc + 1
   return(meteors,nonmeteors)

def plot_int(times, values,values2=None,mstart=0,mend=0, title="", save_file=None):


   print("TIMES:", len(times))
   print("VALUES:", len(values))
   import matplotlib
   #matplotlib.use('Agg')
   import matplotlib.pyplot as plt
   fig = plt.figure()
   fig.suptitle(title, fontsize=16)
   if values2 is not None:
      if len(values) != len(values2)  :
         print("PROBLEM, unequal items in lists.")
         return()


   if values2 is None:
      plt.plot(times,values)
   else:
      plt.plot(mstart,0,"x")
      plt.plot(mend,0,"x")
      plt.plot(times,values)
      plt.plot(times,values2)
   plt.show()
   #curve_file = "figs/detect.png"
   #plt.savefig(curve_file)
   fig.savefig(save_file, dpi=100)

def analyze_intensity(curve1, curve2,subframes=None):
   int_frame_data = []
   mstart = None
   mend = None
   if len(curve1) <= 3 or len(curve2) <= 3:
      return(0,0,0,0)
   max_c1 = max(curve1)
   max_c2 = max(curve2)

   mult_c1 = []
   mult_c2 = []
   peak_c1 = 0
   peak_c2 = 0
   max_sd = 0
   max_hd = 0
   for i in range(0,len(curve1)):
      mp = curve1[i] / max_c1
      mult_c1.append(mp)
      if mp > peak_c1:
         peak_c1 = mp
         psdf = i
      if mp > .1:
         max_sd += 1

   for i in range(0,len(curve2)):
      mp = curve2[i] / max_c2
      mult_c2.append(mp)
      if mp > peak_c2:
         peak_c2 = mp
         phdf = i
      if mp > .1:
         max_hd += 1

   sd_off = phdf - psdf

   peak_hd = mult_c2.index(max(mult_c2))
   peak_sd = mult_c1.index(max(mult_c1))
   cm = 0
   for i in range(0,len(mult_c1)):
      met = 0
      if subframes is not None:
         try:
            min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(subframes[i])
            if max_val - min_val < 10:
               mx = 0
               my = 0
         except:
            mx = 0
            my = 0
      else:
         mx = 0
         my = 0
      if i + 4 < len(mult_c1):
         if mult_c1[i+4] > .2 or mult_c2[i+4] > .2:
            met = 1
      if i - 4 >= 0:
         if mult_c1[i-4] > .2 or mult_c2[i-4] > .2:
            met = 1
     
      if mult_c1[i] > .04 or mult_c2[i] > .04 or met == 1:
         cm = cm + 1
         if cm >= 3:
            #print("METEOR:", i, mult_c1[i], mult_c2[i], cm,mx,my)
            int_frame_data.append((i,1,mult_c1[i],mult_c2[i],cm,(mx,my)))
         else:
         #   mx = 0
         #   my = 0
            #print(i, mult_c1[i], mult_c2[i], cm)
            int_frame_data.append((i,0,mult_c1[i],mult_c2[i],cm,(mx,my)))
         if mstart is None:
            mstart = i
         mend = i
      else:
         #mx = 0
         #my = 0
         cm = 0
         #print(i, mult_c1[i], mult_c2[i],cm, mx,my)
         int_frame_data.append((i,0,mult_c1[i],mult_c2[i],cm,(mx,my)))
   return(int_frame_data,mstart,mend)

def sync_frame_curves(sd_curve, hd_curve, sd_frame, hd_frame):
   hdm_x = hd_frame.shape[1] / sd_frame.shape[1]
   hdm_y = hd_frame.shape[0] / sd_frame.shape[0]
   sd_xs = []
   sd_ys = []
   sd_ints = []
   sd_multi = []
   hd_xs = []
   hd_ys = []
   hd_ints = []
   hd_multi = []

   for key in sd_curve:
      if "points" in sd_curve[key]:
         x,y = sd_curve[key]['points']
         intensity = sd_curve[key]['intensity']
         sd_xs.append(int(x*hdm_x))
         sd_ys.append(int(y*hdm_y))
         sd_ints.append(intensity)
      else:
         sd_xs.append(0)
         sd_ys.append(0)
         sd_ints.append(0)
   sd_max_int = max(sd_ints)
   for i in range(0, len(sd_ints)):
      if sd_ints[i] > 0 and sd_max_int > 0:
         sd_multi.append(sd_ints[i] / sd_max_int)
      else:
         sd_multi.append(0)

   for key in hd_curve:
      if "points" in hd_curve[key]:
         x,y = hd_curve[key]['points']
         intensity = hd_curve[key]['intensity']
         hd_xs.append(x)
         hd_ys.append(y)
         hd_ints.append(intensity)
      else:
         hd_xs.append(0)
         hd_ys.append(0)
         hd_ints.append(0)
   hd_max_int = max(hd_ints)

   for i in range(0, len(hd_ints)):
      if hd_ints[i] > 0 and hd_max_int > 0:
         hd_multi.append(hd_ints[i] / hd_max_int)
      else:
         hd_multi.append(0)

   peak_sd = sd_multi.index(max(sd_multi))
   peak_hd = hd_multi.index(max(hd_multi))
   sd_off = peak_hd - peak_sd          
   
   low_err = 9999
   best_sync = None
   for i in range(-10,10):   
      sd_start = sd_off + i 
      merr,serr = min_curve_err(sd_start, sd_multi, hd_multi)
      #print("ERROR AT SYNC POINT:", sd_start, merr, serr)
      if serr < low_err and serr > 0 :
         low_err = serr
         best_sync = sd_start 

   print("LEN multi:", len(sd_multi), len(hd_multi))
   print("PEAK SD/HD:", peak_sd, peak_hd)
   print("BEST SYNC:", best_sync)
   print("SD OFF:", sd_off)

   return(best_sync )

def sync_curves(curve1, curve2):
   print("1:", curve1)
   print("2:", curve2)  
   max_c1 = max(curve1)
   max_c2 = max(curve2)

   mult_c1 = []
   mult_c2 = []
   peak_c1 = 0
   peak_c2 = 0
   max_sd = 0
   max_hd = 0
   phdf = 0
   psdf = 0
   for i in range(0,len(curve1)):
      if max_c1 > 0:
         mp = curve1[i] / max_c1
      else:
         mp = 0
      mult_c1.append(mp)
      if mp > peak_c1:
         peak_c1 = mp
         psdf = i
      if mp > .1:
         max_sd += 1

   for i in range(0,len(curve2)):
      if max_c1 > 0 and max_c2 > 0:
         mp = curve2[i] / max_c2
      else:
         mp = 0
      mult_c2.append(mp)
      if mp > peak_c2:
         peak_c2 = mp
         phdf = i
      if mp > .1:
         max_hd += 1
 
   sd_off = phdf - psdf
   
   peak_hd = mult_c2.index(max(mult_c2))
   peak_sd = mult_c1.index(max(mult_c1))
   
   #minimize the curve error between the two curves

   low_err = 999
   for i in range(-10,10):   
      sd_start = sd_off + i
      merr,serr = min_curve_err(sd_start, mult_c1, mult_c2)
      #print("ERROR AT SYNC POINT:", sd_start, merr, serr)
      if serr < low_err:
         low_err = serr
         best_sync = sd_start

   print("BEST SD SYNC ADJUST IS :", best_sync)
   print("PEAK SD SYNC ADJUST IS :", peak_hd - peak_sd)
   print("SD EVENT LEN:", max_sd)
   print("HD EVENT LEN:", max_hd)
   print("SD PEAK FN:", peak_sd, psdf)
   print("HD PEAK FN:", peak_hd, phdf)
   print("SYNC ERR:", low_err)
   event_len =  max([max_sd,max_hd])
   peak_sync = peak_hd - peak_sd
   return(best_sync, peak_sync, event_len, low_err)



def min_curve_err(sd_off, c1, c2):
   errors = []
   for i in range(0, len(c1)):
      if i + sd_off < len(c2) -1 and i < len(c1) -1 and i + sd_off > 0:
         #print("sd_off", sd_off, i, i+sd_off)
         err = abs(c1[i] - c2[i+sd_off])
         errors.append(err)
         #print("SYNC ERR:", i, i+sd_off, c1[i], c2[i+sd_off], err)
      #else:
      #   print("No suitable frames!", i, sd_off)
   if len(errors) > 0:
      med_err = np.median(errors)
      sum_err = np.sum(errors) 
   else:
      med_err = 0
      sum_err = 0

   #print("MED ERR:", sd_off, med_err, sum_err)
   return(med_err, sum_err)

def sync_frames(sd_frames,hd_frames,sd_subframes,hd_subframes,sd_sum_vals,hd_sum_vals,sd_sync):
   new_hd = []
   new_sd = []
   new_hd_sub = []
   new_sd_sub = []
   new_hd_sum = []
   new_sd_sum = []

   max_len = max(len(sd_frames),len(hd_frames))

   # if sd_sync is > 0 then we need to take a way HD FRAMES
   #if sd_sync > 0:
   sd_h,sd_w=sd_frames[0].shape[:2]
   hd_h,hd_w=hd_frames[0].shape[:2]
   if True:
      for i in range(0,max_len):
         hd_stat = ""
         sd_stat = ""
         sd_fn = i + sd_sync 
         hd_fn = i 
         print("WORKING", sd_fn, hd_fn)
         if (sd_fn < 0 or sd_fn >= len(sd_frames)) and (hd_fn > 0 and hd_fn <= len(hd_frames)):
            #make SD frame from HD frame
            sd_subframe = cv2.resize(hd_subframes[hd_fn], (sd_w,sd_h))
            sd_frame = cv2.resize(hd_frames[hd_fn], (sd_w,sd_h))
            sd_stat = "SD FRAME MADE FROM HD FRAME"
            print(sd_stat)
         elif sd_fn >= 0 and sd_fn < len(sd_frames):
            sd_subframe = sd_subframes[sd_fn]
            sd_frame = sd_frames[sd_fn]
            print("sd frame good")
         else:
            sd_frame = None
            print("no sd frame ")
         if hd_fn < 0 or hd_fn >= len(hd_frames):
            hd_subframe = cv2.resize(sd_subframes[hd_fn], (hd_w,hd_h))
            hd_frame = cv2.resize(sd_frames[hd_fn], (hd_w,hd_h))
            hd_stat = "HD FRAME MADE FROM SD FRAME"
            print(hd_stat)
         elif hd_fn >= 0 and hd_fn < len(hd_frames):
            hd_subframe = hd_subframes[hd_fn]
            hd_frame = hd_frames[hd_fn]
            print("hd frame good")
         else:
            hd_frame = None
            print("no hd frame ")

         if hd_frame is not None and sd_frame is not None:
            print(sd_fn, hd_fn, len(sd_frames), len(hd_frames), sd_stat, hd_stat)
            new_sd.append(sd_frame)
            new_sd_sub.append(sd_subframe)
            new_sd_sum.append(int(np.sum(sd_subframe)))

            new_hd.append(hd_frame)
            new_hd_sub.append(hd_subframe)
            new_hd_sum.append(int(np.sum(hd_subframe)))


   print("SD:", new_sd_sum) 
   print("HD:", new_hd_sum) 

   return(new_sd,new_hd,new_sd_sub,new_hd_sub,new_sd_sum,new_hd_sum)

def make_frame_data(buf_hd_subframes,buf_hd_frames,cnt_object,bp_object):
   frame_data = {}
   x_dir_mod,y_dir_mod = meteor_dir(bp_object['oxs'][0], bp_object['oys'][0], bp_object['oxs'][-1], bp_object['oys'][-1])


   print("cnt_object:", cnt_object)
   print("bp_object:", bp_object)
   for i in range(0,len(buf_hd_frames)+1):
      frame_data[i] = {}
   for i in range(0, len(cnt_object['ofns'])):
      fn = cnt_object['ofns'][i]
      x = cnt_object['oxs'][i]
      y = cnt_object['oys'][i]
      w = cnt_object['ows'][i]
      h = cnt_object['ohs'][i]
      if fn in frame_data:
         if 'ftimes' in cnt_object:
            dt  = cnt_object['ftimes'][i]
            frame_data[fn]['dt'] = dt
     
         if "cnts" not in frame_data[fn]:
            frame_data[fn]['cnts'] = []
         frame_data[fn]['cnts'].append((x,y,w,h))
         print("CNT FRAME DATA:", fn, frame_data[fn])

   for i in range(0, len(bp_object['ofns'])):
      fn = bp_object['ofns'][i] 
      x = bp_object['oxs'][i]
      y = bp_object['oys'][i]
      w = bp_object['ows'][i]
      h = bp_object['ohs'][i]
      if fn in frame_data:
         if "bps" not in frame_data[fn]:
            frame_data[fn]['bps'] = []
     
         frame_data[fn]['bps'].append((x,y,w,h))
      if fn in frame_data:
         print("BP FRAME DATA:", fn, frame_data[fn])

   # fill in any missing frames that exists between start and end
   start = cnt_object['ofns'][0]
   end = cnt_object['ofns'][-1]

   last_best = None
   for i in range(0,len(buf_hd_subframes)):
      print("START,END:", start, end, last_best)
      if start <= i <= end and "cnts" not in frame_data[i]:
         if last_best is not None:
            fn = i 
            print("ADD MISSING FRAME!", i, last_best)
            print("ADD MISSING FRAME DATA:", fn, frame_data[fn])
            last_x, last_y,last_w,last_h = last_best
            lcx1,lcy1,lcx2,lcy2 = bound_cnt(last_x, last_y,buf_hd_subframes[i].shape[1],buf_hd_subframes[i].shape[0])
            le_cnt_tmp = buf_hd_subframes[i][lcy1:lcy2,lcx1:lcx2]
            min_val, max_val, min_loc, (lmx,lmy)= cv2.minMaxLoc(le_cnt_tmp)
            frame_data[fn]['cnts'] = [[lcx1+lmx,lcy1+lmy,last_w,last_h]]

      # remove orphan frames if they exist
      #if i - 1 in frame_data and i + 1 in frame_data:
      #   if "cnts" in frame_data[i] and "cnts" not in frame_data[i-1] and "cnts" not in frame_data[i+1]:
      #      print("DELETE ORPHAN FRAME!")
      #      frame_data[i] = {}

      if "cnts" in frame_data[i]:
         last_best = frame_data[i]['cnts'][0]

   # now find the blob center for each frame
   last_bx = None
   first_bx = None
   last_dist_from_start = None
   max_dist_from_start = 0
   last_dists = []
   for i in range(0,len(buf_hd_frames)):
      bx = None
      if i not in frame_data:
         frame_data[i] = {}
      if "bps" in frame_data[i]:
         bx,by,bw,bh = frame_data[i]['bps'][0]
      elif "cnts" in frame_data[i]:
         bx,by,bw,bh = frame_data[i]['cnts'][0]
      if bx is not None : 
         if first_bx is None:
            first_bx = bx
            first_by = by
            last_dist_from_start = 0
         print(i)
         cx1,cy1,cx2,cy2 = bound_cnt(bx,by,buf_hd_frames[0].shape[1],buf_hd_frames[0].shape[0], 25)
         blob_cnt = buf_hd_frames[i][cy1:cy2,cx1:cx2]
         blob_int = int(np.sum(blob_cnt))
         blob_x, blob_y, max_val, blob_w, blob_h= find_blob_center(i, buf_hd_frames[i],bx,by,20, x_dir_mod, y_dir_mod)
         frame_data[i]['leading_x'] = blob_x
         frame_data[i]['leading_y'] = blob_y 
         frame_data[i]['blob_x'] = blob_x
         frame_data[i]['blob_y'] = blob_y 
         frame_data[i]['blob_w'] = blob_w
         frame_data[i]['blob_h'] = blob_h
         frame_data[i]['blob_int'] = blob_int
         frame_data[i]['dist_from_start'] = calc_dist((blob_x,blob_y),(first_bx,first_by))
         frame_data[i]['dist_from_last'] = frame_data[i]['dist_from_start'] - last_dist_from_start
         last_dist_from_start = frame_data[i]['dist_from_start']
         last_dists.append(frame_data[i]['dist_from_last'] )
         last_bx = blob_x
         last_by = blob_y
         last_fn = i 

   # CHECK/REMOVE BAD FRAMES AT END (check distance, check line_slope, check px diff, check intensity: if any of these fail delete the frame data)
   med_dist = np.median(last_dists)
   diff = abs(med_dist - frame_data[last_fn]['dist_from_last'])
   print("LAST DIFF ERROR:", med_dist, diff)
   if diff > 5:
      print("BAD LAST FRAME!", last_fn)
      frame_data[last_fn] = {}
   poly_x,poly_y = frame_data_to_poly_xy(frame_data)
   print("POLYX:", poly_x)
   print("POLYY:", poly_y)
   if len(poly_x) >= 4:
      if 'leading_x' not in frame_data[last_fn] :
         last_fn += -1

      if 'leading_x' in frame_data[last_fn] :
         print("PX:", poly_x[0:-2],poly_y[0:-2])
         print(frame_data[last_fn]['leading_x'],frame_data[last_fn]['leading_y'])
         results = poly_fit_check(poly_x[0:-2],poly_y[0:-2], frame_data[last_fn]['leading_x'],frame_data[last_fn]['leading_y'] )
         if results != 0:
            if len(results) == 3:
               dist_from_line,z,med_dist = results
            else: 
               dist_from_line,z,med_dist = 0,(0,0),0
            print("LAST POINT DIST FROM LINE:", dist_from_line, med_dist)
         
            if dist_from_line > 2 * med_dist:
               print("BAD FRAME!")
               #frame_data[last_fn] = {}
      


   for i in frame_data:
      print(i,frame_data[i])

   # now find the leading edge
   find_le = 1
   if find_le == 1:
      for i in range(0,len(buf_hd_subframes)):
         fxs = []
         fys = []
         if "blob_x" in frame_data[i]:
            bx = frame_data[i]['blob_x']
            by = frame_data[i]['blob_y']
            bw = frame_data[i]['blob_w']
            bh = frame_data[i]['blob_h']
            bx1,by1,bx2,by2 = bound_cnt(bx, by,buf_hd_subframes[i].shape[1],buf_hd_subframes[i].shape[0], 10)
            lcx1,lcy1,lcx2,lcy2 = bound_leading_edge_cnt(bx,by,buf_hd_subframes[i].shape[1],buf_hd_subframes[i].shape[0], x_dir_mod,y_dir_mod,20)
            #lcx1,lcy1,lcx2,lcy2 = bx1,by1,bx2,by2
            
            blob_cnt = buf_hd_frames[i][by1:by2,bx1:bx2].copy()
            le_cnt = buf_hd_frames[i][lcy1:lcy2,lcx1:lcx2].copy()


            print("BLOB CNT:", bx1,by1,bx2,by2)
            print("LE CNT:", lcx1,lcy1,lcx2,lcy2)
            le_cnt = cv2.GaussianBlur(le_cnt, (7, 7), 0)
            min_val, max_val, min_loc, (lmx,lmy)= cv2.minMaxLoc(le_cnt)
            contours, rects= find_contours_in_frame(le_cnt, int(max_val/2))
            if len(contours) >= 1:
            
               cnt_x,cnt_y,cnt_w,cnt_h = contours[0]
               cx = cnt_x + int(cnt_w/2)
               cy = cnt_y + int(cnt_h/2)
               cv2.circle(le_cnt,(cx,cy), 2, (255,255,255), 1)
               frame_data[i]['leading_x'] = lcx1+cx
               frame_data[i]['leading_y'] = lcy1+cy
            else:
               frame_data[i]['leading_x'] = lcx1+lmx
               frame_data[i]['leading_y'] = lcy1+lmy
            frame_data[i]['le_cnt'] = [lcx1,lcy1,lcx2,lcy2]
            #leading_edge_cnt = buf_hd_subframes[i][lcy1:lcy2,lcx1:lcx2]
            show = 0
            if show == 1:
               cv2.circle(le_cnt,(lmx,lmy), 3, (255,255,255), 1)
               cv2.imshow('blob', blob_cnt)
               cv2.waitKey(0)
               cv2.imshow('leading edge', le_cnt)
               cv2.waitKey(0)

   # Remove bad frames from end of meteor

   for fn in frame_data:
      print(fn, frame_data[fn])
   return(frame_data)

def frame_data_to_poly_xy(frame_data):
   poly_x = []
   poly_y = []
   for fn in frame_data:
      print(fn, frame_data[fn])
      if 'leading_x' in frame_data[fn]:
         poly_x.append(frame_data[fn]['leading_x'])
         poly_y.append(frame_data[fn]['leading_y'])
   return(poly_x,poly_y)

def frame_curve(meteor,frames):
   fdc = {}
   for i in range(0, len(frames)):
      fdc[i] = {}
   for i in range(0, len(meteor['ofns'])):
      fn = meteor['ofns'][i]
      x = meteor['oxs'][i]
      y = meteor['oys'][i]
      intensity = meteor['oint'][i]
      fdc[fn]['points'] = [x,y]

      fdc[fn]['intensity'] = intensity
   return(fdc)  

def debug2(video_file):
   show = 0
   # setup variables
   orig_sd_trim_num = get_trim_num(video_file)

   hd_datetime, hd_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(video_file)
   meteor_date = hd_y + "_" + hd_m + "_" + hd_d
   old_meteor_dir = "/mnt/ams2/meteors/" + hd_y + "_" + hd_m + "_" + hd_d + "/"
   mf = video_file.split("/")[-1]
   mf = mf.replace(".mp4", ".json")
   old_meteor_json_file = old_meteor_dir + mf 
   print(old_meteor_json_file)
   md = load_json_file(old_meteor_json_file)
   hd_trim = md['hd_trim']
   org_sd_vid = video_file 
   if "arc_fail" in md:
      print("PREV ARC FAIL:", md['arc_fail'])
      if md['arc_fail'] == "HD detection failed." or md['arc_fail'] == "No HD trim file exists.":
         print("TRY TO FIX!")
         new_video_file = video_file.replace(".mp4", "-HD-meteor.mp4")
         if cfe(new_video_file) == 0:
            cmd = "/usr/bin/ffmpeg -i " + video_file + " -vf scale=1920:1080 " + new_video_file 
            os.system(cmd)
            del md['arc_fail']
            md['hd_trim'] = new_video_file
            hd_trim = new_video_file
            print("HD FILE FIXED:", new_video_file)
            save_json_file(old_meteor_json_file, md)
         else:
            print("HD DETECT FAILED EVEN AFTER SD FIX.:", md['arc_fail'])
            return()
      elif md['arc_fail'] == "HD TRIM FILE NOT FOUND" :
         # make sure this is true.
         if 'hd_trim' in md:
            if md['hd_trim'] != 0 and md['hd_trim'] != None:
               if cfe(md['hd_trim']) == 1:
                  del md['arc_fail']
                  save_json_file(old_meteor_json_file, md)
      else:
         print("THE FILE FAILED THE ARC ALREADY:", md['arc_fail'])
         return()

   # load SD frames
   sd_frames,sd_color_frames,sd_subframes,sd_sum_vals,sd_max_vals,pos_vals = load_frames_fast(video_file, json_conf, 0, 0, [], 1,[])

   # load HD frames
   if hd_trim is not None and hd_trim != 0:
      hd_good = 1
      if "/mnt/ams2/HD" in hd_trim:
         mfn = hd_trim.split("/")[-1]
         mday = mfn[0:10]
         hd_trim = "/mnt/ams2/meteors/" + mday + "/" + mfn
   else:
      hd_good = 0
   if hd_good == 1:
      if cfe(hd_trim) == 1 and hd_good == 1:
         hd_frames,hd_color_frames,hd_subframes,hd_sum_vals,hd_max_vals,pos_vals = load_frames_fast(hd_trim, json_conf, 0, 0, [], 1,[])
         org_hd_vid = hd_trim 
      else:
         hd_good = 0
   if hd_good == 0:
      print("NO HD TRIM FILE FOUND. ")
      new_video_file = video_file.replace(".mp4", "-HD-meteor.mp4")
      cmd = "/usr/bin/ffmpeg -i " + video_file + " -vf scale=1920:1080 " + new_video_file 
      os.system(cmd)
      md['hd_trim'] = new_video_file
      if "arc_fail" in md:
         del(md['arc_fail'])
      save_json_file(old_meteor_json_file, md)
      hd_trim = new_video_file
      if cfe(hd_trim) == 1:
         hd_frames,hd_color_frames,hd_subframes,hd_sum_vals,hd_max_vals,pos_vals = load_frames_fast(hd_trim, json_conf, 0, 0, [], 1,[])
      else:
         print("HD FIX FAILED!")
         exit()
   

   motion_objects, motion_frames = detect_meteor_in_clip(video_file, sd_frames, 0)
   hd_motion_objects, hd_motion_frames = detect_meteor_in_clip(video_file, hd_frames, 0)

   error = 0
   sd_meteor = only_meteors(motion_objects,1)
   hd_meteor = only_meteors(hd_motion_objects,1)
   if sd_meteor is None or hd_meteor is None:
      print("Couldn't detect SD or HD meteor.")
      print("SD:", sd_meteor)
      print("HD:", hd_meteor)
      if sd_meteor is None:
         for mm in motion_objects:
            print("SD",mm, motion_objects[mm]['ofns'])
            print("SD",mm, motion_objects[mm]['report'])
      if hd_meteor is None:
         for mm in hd_motion_objects:
            print("HD",mm, hd_motion_objects[mm]['ofns'])
            print("HD",mm, hd_motion_objects[mm]['report'])
      if sd_meteor is None:
         md['arc_fail'] = "SD detection failed."
      if hd_meteor is None:
         md['arc_fail'] = "HD detection failed."
      if sd_meteor is None and hd_meteor is None:
         md['arc_fail'] = "HD and SD detection failed."

      print("Saving arc fail.", md['arc_fail'])
      save_json_file(old_meteor_json_file, md)
      return()

   sd_frame_curve = frame_curve(sd_meteor, sd_frames)
   hd_frame_curve = frame_curve(hd_meteor, hd_frames)

   best_sync_fr = sync_frame_curves(sd_frame_curve, hd_frame_curve, sd_frames[0], hd_frames[0])

   best_sync_sv,peak_sync_sv,ev_len,low_err = sync_curves(sd_sum_vals, hd_sum_vals )
   best_sync_mv,peak_sync_mv, mv_ev_len,mv_low_err = sync_curves(sd_max_vals, hd_max_vals)
   sd_geo_xs,sd_geo_ys,sd_geos = geo_vals(sd_meteor, hd_frames,sd_frames)
   hd_geo_xs,hd_geo_ys,hd_geos = geo_vals(hd_meteor, hd_frames, sd_frames)
   best_sync_geo_x,peak_sync_geo_x, geo_ev_len,geo_low_err = sync_curves(sd_geos, hd_geos)
   print("BEST SYNC GEOX:", best_sync_geo_x, peak_sync_geo_x, geo_low_err)


   print("BEST SYNC FR:", best_sync_fr )
   print("BEST SYNC SV:", best_sync_sv, peak_sync_sv, ev_len, low_err)
   print("BEST SYNC MV:", best_sync_mv, peak_sync_mv, mv_ev_len, mv_low_err)
   best_sync = int(np.median((best_sync_fr, best_sync_sv, best_sync_mv,best_sync_geo_x)))
   print("BEST SYNC:", best_sync)


   med_event_length = max([len(hd_meteor['ofns']),len(sd_meteor['ofns'])])
   ideal_buffer = int (med_event_length * 2) 
   if ideal_buffer > 25:
      ideal_buffer = 25 
   if ideal_buffer < 10:
      ideal_buffer = 10 
   if med_event_length > 100:
      ideal_buffer = 50

   

   print("*********** SYNC REPORT ************")
   print("BEST SD SYNC:            ", best_sync)
   print("HD FILE INFO             ")
   print("LEN HD_FRAMES            :", len(hd_frames))
   print("HD INITIAL START FRAME   :", hd_meteor['ofns'][0]) 
   print("HD INITIAL END FRAME     :", hd_meteor['ofns'][-1]) 
   print("HD EVENT LENGTH          :", hd_meteor['ofns'][-1] - hd_meteor['ofns'][0]) 

   print("HD INITIAL END BUFFER    :", len(hd_frames) - hd_meteor['ofns'][-1])
   print("HD ADJUSTED START FRAME  :", hd_meteor['ofns'][0] ) 
   print("HD ADJUSTED END FRAME    :", hd_meteor['ofns'][-1] ) 
   print("")
   print("SD FILE INFO         ")
   print("SD INITIAL START FRAME   :", sd_meteor['ofns'][0]) 
   print("LEN SD_FRAMES            :", len(sd_frames))
   print("SD INITIAL LAST FRAME    :", sd_meteor['ofns'][-1]) 

   print("SD INITIAL END BUFFER    :", len(sd_frames) - sd_meteor['ofns'][-1])

   print("SD EVENT LENGTH          :", sd_meteor['ofns'][-1] - sd_meteor['ofns'][0]) 
   print("SD ADJUSTED START FRAME  :", sd_meteor['ofns'][0] + best_sync) 

   print("SD ADJUSTED END FRAME    :", sd_meteor['ofns'][-1] + best_sync) 
   print("")
   print("IDEAL BUFFER             :", ideal_buffer)
   missing_hd_frames = 0
   # test to see if we have enough frames around the event for the ideal buffer to work
   if sd_meteor['ofns'][0] - ideal_buffer < 0:
      print("SD Meteor doesn't have enough frames for the ideal starting buffer!")
      

   if sd_meteor['ofns'][-1] + ideal_buffer > len(sd_frames):
      print("SD Meteor doesn't have enough frames for the ideal ending buffer!")
   if hd_meteor['ofns'][0] - ideal_buffer < 0:
      print("HD Meteor doesn't have enough frames for the ideal starting buffer!")
   
      missing_hd_frames_start = abs(hd_meteor['ofns'][0] - ideal_buffer)
      for extra in range(0,missing_hd_frames_start):

         blank_image = np.zeros((1080,1920),dtype=np.uint8)
         hd_frames.insert(0, blank_image)
         hd_color_frames.insert(0,blank_image)
         hd_subframes.insert(0,blank_image)
         hd_sum_vals.insert(0,0)
         hd_max_vals.insert(0,0)

   if hd_meteor['ofns'][-1] + ideal_buffer > len(hd_frames):
      missing_hd_frames_end =  abs((hd_meteor['ofns'][-1] + ideal_buffer) - len(hd_frames))

      for extra in range(0,missing_hd_frames_end):
          
         blank_image = np.zeros((1080,1920),dtype=np.uint8)
         hd_frames.append(blank_image)
         hd_color_frames.append(blank_image)
         hd_subframes.append(blank_image)
         hd_sum_vals.append(0)
         hd_max_vals.append(0)

   min_ran = min(len(sd_sum_vals),len(hd_sum_vals))


   ev_len = max( (sd_meteor['ofns'][-1] - sd_meteor['ofns'][0]), (hd_meteor['ofns'][-1] - hd_meteor['ofns'][0]))



   best_sync_final_s ,pk, ev_len,low_err_s = sync_curves(sd_sum_vals, hd_sum_vals )
   best_sync_final_m ,pk, ev_len,low_err_m = sync_curves(sd_max_vals, hd_max_vals )
   if low_err_s < low_err_m:
      final_sync = best_sync_final_s
   else:
      final_sync = best_sync_final_m

   sd_bs = hd_meteor['ofns'][0] - ideal_buffer - best_sync
   sd_be = hd_meteor['ofns'][0] + ev_len + ideal_buffer - best_sync

   # MMM
   hd_bs = (hd_meteor['ofns'][0] - missing_hd_frames - ideal_buffer)  
   hd_be = (hd_meteor['ofns'][0] + ev_len + ideal_buffer + missing_hd_frames) 
   if sd_bs < 0:
      sd_bs = 0
   if hd_bs < 0:
      hd_bs = 0



   # remap frame numbers of meteor objects to new sync'd buffer frames
   hd_fns = []
   sd_fns = []

   for fn in sd_meteor['ofns']:
      new_fn = (fn - sd_meteor['ofns'][0]) + ideal_buffer 
      sd_fns.append(new_fn)
   for fn in hd_meteor['ofns']:
      new_fn = (fn - hd_meteor['ofns'][0]) + ideal_buffer
      hd_fns.append(new_fn)

   sd_meteor['ofns'] = sd_fns
   hd_meteor['ofns'] = hd_fns

   syncd_sd_frames = sd_frames[sd_bs:sd_be]
   syncd_sd_color_frames = sd_color_frames[sd_bs:sd_be]
   syncd_sd_subframes = sd_subframes[sd_bs:sd_be]
   syncd_sd_sum_vals = sd_sum_vals[sd_bs:sd_be]
   syncd_sd_max_vals = sd_max_vals[sd_bs:sd_be]

   syncd_hd_frames = hd_frames[hd_bs:hd_be]
   syncd_hd_color_frames = hd_color_frames[hd_bs:hd_be]
   syncd_hd_subframes = hd_subframes[hd_bs:hd_be]
   syncd_hd_sum_vals = hd_sum_vals[hd_bs:hd_be]
   syncd_hd_max_vals = hd_max_vals[hd_bs:hd_be]


   best_sync_final_s ,pk, ev_len,low_err_s = sync_curves(syncd_sd_sum_vals, syncd_hd_sum_vals )
   best_sync_final_m ,pk, ev_len,low_err_m = sync_curves(syncd_sd_max_vals, syncd_hd_max_vals )

   if low_err_s < low_err_m:
      final_sync = best_sync_final_s
   else:
      final_sync = best_sync_final_m

   if final_sync != 0 and abs(final_sync) < 7:
      # if there is still some final sync error fix it by shifting things one more time
         sd_bs -= final_sync
         sd_be -= final_sync
         syncd_sd_frames = sd_frames[sd_bs:sd_be]
         syncd_sd_color_frames = sd_color_frames[sd_bs:sd_be]
         syncd_sd_subframes = sd_subframes[sd_bs:sd_be]
         syncd_sd_sum_vals = sd_sum_vals[sd_bs:sd_be]
         syncd_sd_max_vals = sd_max_vals[sd_bs:sd_be]



   frame_data = make_frame_data(syncd_hd_subframes,syncd_hd_frames,hd_meteor,hd_meteor)
   #view_syncd_frames(syncd_sd_frames, syncd_hd_frames, sd_meteor, hd_meteor)

   #plot_int(range(0,len(syncd_sd_sum_vals)),syncd_sd_sum_vals, syncd_hd_sum_vals,0,len(syncd_sd_sum_vals))
   #plot_int(range(0,len(syncd_sd_max_vals)),syncd_sd_max_vals, syncd_hd_max_vals,0,len(syncd_sd_max_vals))

   for fn in frame_data:
      print(fn, frame_data[fn])
   #show_detection(syncd_sd_frames, syncd_hd_frames, syncd_hd_sum_vals, frame_data)

   # if we got this far everything is good and we can save the movie clips and save the new json
   # but we should apply calibration to the capture first!
   print("******************************   PASSED *************************")
   new_trim_num = orig_sd_trim_num + sd_bs 
   arc_json_file = save_archive_meteor(video_file, syncd_sd_frames,syncd_hd_frames,frame_data,new_trim_num) 
   #os.system("./flex-detect.py faa " + arc_json_file)
   return("")
   #exit()

def arc_frames_to_obj(frames):
   fns = []
   xs = []
   ys = []
   ws = []
   hs = []
   oint = []
   ftimes = []
   for frame in frames:
      fns.append(frame['fn'])
      xs.append(frame['x'])
      ys.append(frame['y'])
      ws.append(frame['w'])
      hs.append(frame['w'])
      ftimes.append(frame['dt'])
      if "intensity" in frame:
         oint.append(frame['intensity'])
      else:
         oint.append(0)
   object = {}
   object['oid'] = 1 
   object['ofns'] = fns 
   object['oxs'] = xs
   object['oys'] = ys
   object['ows'] = ws
   object['ohs'] = hs
   object['oint'] = oint
   object['ftimes'] = ftimes
   return(object)

def frame_data_to_obj(frame_data):  
   fns = []
   xs = []
   ys = []
   ws = []
   hs = []
   oints = []
   for fn in frame_data:
      if "leading_x" in frame_data[fn]:
         fns.append(fn)
         xs.append(frame_data[fn]['leading_x'])
         ys.append(frame_data[fn]['leading_y'])
         ws.append(5)
         hs.append(5)
         if "intensity" in frame_data[fn]:
            oints.append(frame_data[fn]['intensity'])
         else:
            oints.append(0)
   object = {}
   object['obj_id'] = 1
   object['ofns'] = fns
   object['oxs'] = xs
   object['oys'] = ys
   object['ows'] = ws
   object['ohs'] = hs
   object['oint'] = oints
   object = analyze_object(object)
   return(object)

def obj_to_frames(hd_meteor, start_trim_time,cal_params):
   ofns = hd_meteor['ofns']
   xs = hd_meteor['oxs']
   ys = hd_meteor['oys']
   frames = []
   for i in range(0,len(ofns)):
      frame = {}
      frame['fn'] = ofns[i]
      frame['x'] = xs[i]
      frame['y'] = ys[i]
      frame['w'] = hd_meteor['ows'][i]
      frame['h'] = hd_meteor['ohs'][i]

      extra_meteor_sec = int(frame['fn']) /  25
      meteor_frame_time = start_trim_time+ datetime.timedelta(0,extra_meteor_sec)
      meteor_frame_time_str = meteor_frame_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
      frame['dt'] = meteor_frame_time_str

      new_x, new_y, ra ,dec , az, el = XYtoRADec(frame['x'],frame['y'],hd_meteor['trim_clip'],cal_params,json_conf)
      frame['az'] = az
      frame['el'] = el
      frame['ra'] = ra
      frame['dec'] = dec


      frames.append(frame)
   return(frames)  

def obj_to_arc_meteor(meteor_file):
   mj = load_json_file(meteor_file)

   (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(mj['sd_trim'])
   (f_datetime_hd, cam, f_date_str_hd,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(mj['hd_trim'])
   trim_num = int(mj['sd_trim'].split("-trim-")[1].replace(".mp4", ""))
   if ("-trim-") in mj['hd_trim']:
      
      hd_trim_num = mj['hd_trim'].split("-trim-")[1].replace("-HD-meteor.mp4", "")
      hd_trim_num = hd_trim_num.replace(".mp4", "")
      hd_trim_num = int(hd_trim_num)
   else:
      hd_trim_num = int(mj['hd_trim'].split("-trim")[1].replace(".mp4", ""))

   extra_sec_sd = trim_num / 25
   extra_sec_hd = hd_trim_num / 25
   start_trim_time_sd = f_datetime + datetime.timedelta(0,extra_sec_sd)
   start_trim_time_hd = f_datetime_hd + datetime.timedelta(0,extra_sec_hd)

   hd_meteor = None
   sd_meteor = None
   if len(mj['hd_meteors']) == 1 and len(mj['sd_meteors']) == 0:
      mj['sd_meteors'] = mj['hd_meteors']
   if len(mj['hd_meteors']) == 0 and len(mj['sd_meteors']) == 1:
      mj['hd_meteors'] = mj['sd_meteors']
   for key in mj['hd_meteors']:
      print(key)
      hd_meteor = key
   for key in mj['sd_meteors']:
      sd_meteor = key

   # apply the calib
   if hd_meteor is not None:
      hd_meteor['hd_trim'] = mj['hd_trim']
   else:
      print("HD:", hd_meteor) 
      print("SD:", sd_meteor) 
      hd_meteor = sd_meteor
   #print("MJ", mj)
   for key in mj:
      print(key, mj[key])
   #if "sd_trim" not in mj:
   sd_meteor['sd_trim'] = mj['sd_trim']
   calib,cal_params = apply_calib(hd_meteor)

   # make the frames
   if hd_meteor is None:
      hd_meteor = sd_meteor
      #hdm_x = 
      #hdm_y = 
   else:
      hdm_x = 1 
      hdm_y = 1

   ofns = hd_meteor['ofns']
   xs = hd_meteor['oxs']
   ys = hd_meteor['oys']
   frames = []
   for i in range(0,len(ofns)):
      frame = {}
      frame['fn'] = ofns[i]
      frame['x'] = xs[i]
      frame['y'] = ys[i]
      frame['w'] = hd_meteor['ows'][i]
      frame['h'] = hd_meteor['ohs'][i]

      extra_meteor_sec = int(frame['fn']) /  25
      meteor_frame_time = start_trim_time_hd + datetime.timedelta(0,extra_meteor_sec)
      meteor_frame_time_str = meteor_frame_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
      frame['dt'] = meteor_frame_time_str 
      print(frame)

      new_x, new_y, ra ,dec , az, el = XYtoRADec(frame['x'],frame['y'],mj['hd_trim'],cal_params,json_conf)
      frame['az'] = az 
      frame['el'] = el
      frame['ra'] = ra 
      frame['dec'] = dec


      frames.append(frame)

   arc_data = {}
   arc_data['info'] = {}     
   arc_data['info']['station'] = json_conf['site']['ams_id']     
   arc_data['info']['device'] = cam
   arc_data['info']['org_hd_vid'] = mj['old_hd_trim'] 
   arc_data['info']['org_sd_vid'] = mj['old_sd_trim'] 
   arc_data['info']['hd_vid'] = mj['arc_hd'] 
   arc_data['info']['sd_vid'] = mj['arc_sd'] 
   arc_data['frames'] = frames
   arc_data['report'] = hd_meteor['report']     
   arc_data['sync'] = {} 
   arc_data['sync']['sd_ind'] = ofns[0] 
   arc_data['sync']['hd_ind'] = ofns[0] 
   arc_data['calib'] = calib     

   print(arc_data['info'])

   return(arc_data)


def save_archive_meteor(video_file, syncd_sd_frames,syncd_hd_frames,frame_data,new_trim_num, save_vids=1) :
   # Determine trim clip start time and corresponding frame times
   # convert frames to obj
   # Apply the calib
   # Format the new json data
   # Find archive dir
   # Write out archive json
   # Save new sync'd videos in archive

   old_meteor_json_file = video_file.replace(".mp4", ".json") 
   print(old_meteor_json_file)
   omd = load_json_file(old_meteor_json_file)
   if "hd_trim" in omd:
      if omd['hd_trim'] is not None and omd['hd_trim'] != 0:
         orig_hd_vid = omd['hd_trim']
      else: 
         orig_hd_vid = 0
   else:
      orig_hd_vid = 0


   station_id = json_conf['site']['ams_id']

   (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(video_file)
   extra_sec = new_trim_num / 25
   start_trim_frame_time = f_datetime + datetime.timedelta(0,extra_sec)


   vfn = video_file.split("/")[-1]
   aa,bb = vfn.split("-trim")
   orig_file_str = aa
   archive_base_filename = aa + "-trim" + str(new_trim_num) 
   archive_year = archive_base_filename[0:4]
   archive_mon = archive_base_filename[5:7]
   archive_day = archive_base_filename[8:10]
   hd_fast_meteor  = frame_data_to_obj(frame_data) 
   hd_fast_meteor['dt'] = start_trim_frame_time.strftime('%Y-%m-%d %H:%M:%S.%f')
   hd_fast_meteor['orig_hd_vid'] = orig_hd_vid
   hd_fast_meteor['orig_sd_vid'] = video_file 
   hd_fast_meteor['dur'] = hd_fast_meteor['ofns'][-1] - hd_fast_meteor['ofns'][0] / 25
   for i in range(0,len(hd_fast_meteor['ofns'])):
      if "ftimes" not in  hd_fast_meteor:
         hd_fast_meteor['ftimes'] = []
         fn = hd_fast_meteor['ofns'][i]

      extra_meteor_sec = fn /  25
      meteor_frame_time = start_trim_frame_time + datetime.timedelta(0,extra_meteor_sec)
      meteor_frame_time_str = meteor_frame_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
      hd_fast_meteor['ftimes'].append(meteor_frame_time_str)
      print("METEOR FRAME TIME:", meteor_frame_time_str)




   print("ARCHIVE BASE FILE:", archive_base_filename)
   print("ARCHIVE DATE:", archive_year,archive_mon,archive_day)
   ma_dir = ARCHIVE_DIR + station_id + "/METEOR/" + archive_year + "/" + archive_mon + "/" + archive_day + "/" 
   print("ARCHIVE DIR:", ma_dir)
   ma_json_file = ma_dir + archive_base_filename + ".json"
   ma_sd_file = ma_dir + archive_base_filename + "-SD.mp4"
   ma_hd_file = ma_dir + archive_base_filename + "-HD.mp4"

   if not os.path.exists(ma_dir):
      os.makedirs(ma_dir) 

   hd_fast_meteor['trim_clip'] = ma_sd_file 
   hd_fast_meteor['hd_trim'] = orig_hd_vid
   hd_fast_meteor['ma_sd_file'] = ma_sd_file
   hd_fast_meteor['ma_hd_file'] = ma_hd_file

   
   calib,cal_params = apply_calib(hd_fast_meteor)
   calib = format_calib(ma_sd_file, cal_params, ma_sd_file)
   hd_fast_meteor['calib'] = calib
   hd_fast_meteor['cal_params'] = cal_params

   new_json = save_new_style_meteor_json(hd_fast_meteor, ma_json_file)
   new_json['info']['org_sd_vid'] = ma_sd_file 
   new_json['info']['org_hd_vid'] = ma_hd_file 
   save_json_file(ma_json_file, new_json)
   omd['archive_file'] = ma_json_file
   if "arc_fail" in omd:
      del(omd['arc_fail'])
   save_json_file(old_meteor_json_file, omd)

   if save_vids == 1:
      make_movie_from_frames(syncd_sd_frames, [0,len(syncd_sd_frames) ], ma_sd_file, 1)
      make_movie_from_frames(syncd_hd_frames, [0,len(syncd_hd_frames) ], ma_hd_file, 1)

   cmd = "./MakeCache.py " + ma_json_file
   os.system(cmd)

   #write_archive_index(archive_year,archive_mon)

   return(ma_json_file)




def geo_vals(meteor, hd_frames, sd_frames):
   sh,sw = sd_frames[0].shape[:2]
   hh,hw = hd_frames[0].shape[:2]
   hdm_x = hw / sw
   hdm_y = hh / sh
   geo_d = {}
   geo_x = []
   geo_y = []
   geos = []
   for i in range(0,len(hd_frames)):
      geo_d[i] = [0,0]

   for i in range(0,len(meteor['ofns'])):
      fn = meteor['ofns'][i]
      x = meteor['oxs'][i] * hdm_x
      y = meteor['oys'][i] * hdm_y
      geo_d[fn] = [x,y]
   for fn in geo_d:
      x,y = geo_d[fn]
      geo_x.append(x)
      geo_y.append(y)
      geos.append(x*y)

   return(geo_x, geo_y,geos)


def show_detection(buf_sd_frames, buf_hd_frames, buf_hd_sum_vals, frame_data):
   show = 1
   # find the crop size area
   xs = []
   ys = []
   for fn in frame_data:
      if "leading_x" in frame_data[fn]:
         xs.append(frame_data[fn]['leading_x'])
         ys.append(frame_data[fn]['leading_y'])
   print("FINAL REPORT:")
   print("LEN SD FRAMES:", len(buf_sd_frames))
   print("LEN HD FRAMES:", len(buf_hd_frames))
   print("LEN SUM VALS:", len(buf_hd_sum_vals))
   print("LEN FRAME DATA:", len(frame_data))
   if len(buf_sd_frames) > len(buf_hd_frames):
      hdl = len(buf_hd_frames)
      buf_sd_frames = buf_sd_frames[0:hdl]

   min_x, min_y,max_x,max_y = int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))
   cx1,cy1,cx2,cy2,mid_x,mid_y = find_crop_size(min_x,min_y,max_x, max_y)

   if show == 1:
      for i in range(0,len(buf_sd_frames)-1):
         #ifd = int_frame_data[i]
         #mx,my = ifd[5]
         sum_val = buf_hd_sum_vals[i] 
         print("FINAL SHOW:", i,sum_val)
         sd_show = buf_sd_frames[i].copy()
         hd_show = buf_hd_frames[i].copy()
         crop_hd = hd_show[cy1:cy2,cx1:cx2].copy()

         hd_show = cv2.cvtColor(hd_show,cv2.COLOR_GRAY2RGB)
         sd_show = cv2.cvtColor(sd_show,cv2.COLOR_GRAY2RGB)
         print(i, frame_data[i])
         if "leading_x" in frame_data[i]:
            lecx1,lecy1,lecx2,lecy2 = bound_cnt(frame_data[i]['leading_x'],frame_data[i]['leading_y'],buf_hd_frames[i].shape[1],buf_hd_frames[i].shape[0], 25)
            lead_cnt = buf_hd_frames[i][lecy1:lecy2,lecx1:lecx2]
            lead_cnt = cv2.cvtColor(lead_cnt,cv2.COLOR_GRAY2RGB)
            cv2.circle(hd_show,(frame_data[i]['leading_x'],frame_data[i]['leading_y']), 1, (0,255,0), 1)
         else:
            lead_cnt = None
         if "le_cnt" in frame_data[i]:
            lcx1,lcy1,lcx2,lcy2 = frame_data[i]['le_cnt']
            cv2.rectangle(hd_show, (lcx1, lcy1), (lcx2, lcy2), (255, 128, 128), 1)
         #if "best_x" in frame_data[i]:
         #   best_x = frame_data[i]['best_x']
         #   best_y = frame_data[i]['best_y']
         #   cv2.circle(hd_show,(best_x,best_y), 1, (0,0,255), 1)
      
         cv2.rectangle(hd_show, (cx1, cy1), (cx2, cy2), (255, 128, 128), 1)
         
         crop_show = cv2.resize(crop_hd, (960,540))
         crop_show = cv2.cvtColor(crop_show,cv2.COLOR_GRAY2RGB)
         sd_show = cv2.resize(sd_show, (960,540))
         hd_show = cv2.resize(hd_show, (960,540))
         desc = str(i) + " " + str(sum_val)
         cv2.putText(sd_show, desc,  (5,15), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
         custom_frame = np.zeros((1080,1920),dtype=np.uint8)
         custom_frame = cv2.cvtColor(custom_frame,cv2.COLOR_GRAY2RGB)
         custom_frame[0:540,0:960] = sd_show
         custom_frame[540:1080,0:960] = crop_show 
         custom_frame[0:540,960:1920] = hd_show
         if lead_cnt is not None:
            lead_cnt = cv2.resize(lead_cnt, (500,500))
            custom_frame[540:1040,960:1460] = lead_cnt 

         cv2.imshow('hd', custom_frame)
         cv2.waitKey(0)



def find_crop_size(min_x,min_y,max_x,max_y, hdm_x=1, hdm_y=1):
   if hdm_x != 1:
      sizes = [[1280,720],[1152,648],[1024,576],[869,504],[768,432], [640,360], [512, 288], [384, 216], [256, 144], [128,72]]
   else:
      sizes = [[704,576],[352, 237],[176,118]]
   
   w = max_x - min_x 
   h = max_y - min_y
   mid_x = int(((min_x + max_x) / 2))
   mid_y = int(((min_y + max_y) / 2))
   best_w = 1919
   best_h = 1079
   for mw,mh in sizes: 
      if w * 2 < mw and h * 2 < mh :
         best_w = mw
         best_h = mh



   if (best_w/2) + mid_x > 1920:
      cx1 = mid_x + (best_w + mid_x ) - 1920 
      cx1 = 1919 - best_w 
   elif mid_x - (best_w/2) < 0:
      cx1 = 0
   else:
      cx1 = int(mid_x - (best_w/2))
   if (best_h/2) + mid_y > 1080:
      cy1 = 1079 - best_h 
   elif mid_y - (best_h/2) < 0:
      cy1 = 0
   else:
      cy1 = int(mid_y -  (best_h/ 2))
   cx1 = int(cx1)
   cy1 = int(cy1) 
   cx2 = int(cx1 + best_w)
   cy2 = int(cy1 + best_h)
   return(cx1,cy1,cx2,cy2,mid_x,mid_y)


def frames_to_objects(frames):
   sd_multi = 1
   hd = 1
   objects = {}
   best_objects = {}
   meteor_objects = {}
   size = 10
   print("frames to objects start.")
   for i in range(0,len(frames)):
      frame = frames[i]
      min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(frame)
      thresh = max_val - 20
      if thresh < 10:
         thresh = 10
      cnts,rects = find_contours_in_frame(frame, thresh)
      cntc = 0
      for x,y,w,h in cnts:
         if w > 1 and h > 1 and w < 50 and h < 50:
            cx1,cy1,cx2,cy2 = bound_cnt(x,y,frame.shape[1],frame.shape[0], size)
            cnt_img = frame[cy1:cy2,cx1:cx2]
            bg_cnt_img = frames[0][cy1:cy2,cx1:cx2]
            cnt_sub = cv2.subtract(cnt_img, bg_cnt_img)
            intensity = int(np.sum(cnt_sub))
            cx = x + int(w/2)   
            cy = y + int(h/2)   
            object, objects = find_object(objects, i,cx, cy, w, h, intensity, hd, sd_multi, cnt_img)
            cntc += 1
   print("frames to objects dones.")
   obj_list = []
   for obj in objects:
      if objects[obj]['report']['score'] > 0:
         obj_list.append((obj,objects[obj]['report']['score']))
   best_objects = {}
   for id, score in sorted(obj_list, key=lambda x: x[1], reverse=True):
      print("ID SCORE:", id,score)
      best_objects[id] = objects[id]
   
   return(best_objects)


def points_to_objects(fns,xs,ys,frames=None):
   print("Points to objects")
   print(fns)
   print(xs)
   print(ys)
   print("FRAMES:", len(frames))
   sd_multi = 1
   hd = 1
   objects = {}
   best_objects = {}
   meteor_objects = {}
   size = 10
   for i in range(0,len(fns)):
      fn = fns[i]
      x = xs[i]
      y = ys[i]
      frame = frames[i]
      min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(frame)
      thresh = max_val - 20
      if thresh < 10:
         thresh = 10
      cnts,rects = find_contours_in_frame(frame, thresh)
      cx1,cy1,cx2,cy2 = bound_cnt(x,y,frame.shape[1],frame.shape[0], size)
      cnt_img = frame[cy1:cy2,cx1:cx2]
      object, objects = find_object(objects, fn,x, y, 5, 5, 100, hd, sd_multi, cnt_img)

   obj_list = []
   for obj in objects:
      if objects[obj]['report']['score'] > 0:
         obj_list.append((obj,objects[obj]['report']['score']))

   best_objects = {}
   for id, score in sorted(obj_list, key=lambda x: x[1], reverse=True):
      best_objects[id] = objects[id]
   return(best_objects)

def obj_report(data): 
   for key in data:
      if key == 'ofns' or key == 'report':
         print(key, data[key])

def debug(video_file):
   orig_sd_trim_num = get_trim_num(video_file)

   start_time = time.time() 

   hd_datetime, hd_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(video_file)
   meteor_date = hd_y + "_" + hd_m + "_" + hd_d
   old_meteor_dir = "/mnt/ams2/meteors/" + hd_y + "_" + hd_m + "_" + hd_d + "/"
   mf = video_file.split("/")[-1]
   mf = mf.replace(".mp4", ".json")
   old_meteor_json_file = old_meteor_dir + mf 
   print(old_meteor_json_file)
   md = load_json_file(old_meteor_json_file)
   hd_trim = md['hd_trim']
   org_sd_vid = video_file 


   # load SD & HD frames
   frames,color_frames,subframes,sum_vals,max_vals,pos_vals = load_frames_fast(video_file, json_conf, 0, 0, [], 1,[])
   if "/mnt/ams2/HD" in hd_trim:
      mfn = hd_trim.split("/")[-1]
      mday = mfn[0:10]
      hd_trim = "/mnt/ams2/meteors/" + mday + "/" + mfn

   if cfe(hd_trim) == 1:
      hd_frames,hd_color_frames,hd_subframes,hd_sum_vals,hd_max_vals,pos_vals = load_frames_fast(hd_trim, json_conf, 0, 0, [], 1,[])
      org_hd_vid = hd_trim 
   else:
      org_hd_vid = None 
      print("HD TRIM FILE NOT FOUND!", hd_trim)
      md['arc_fail'] = "HD TRIM FILE NOT FOUND" + str(hd_trim)
      save_json_file(old_meteor_json_file, md)
      return()


   events,pos_meteors = fast_check_events(sum_vals, max_vals, subframes)
   
   hd_events,hd_pos_meteors = fast_check_events(hd_sum_vals, hd_max_vals, hd_subframes)

   fast_meteors,fast_non_meteors = meteor_objects(pos_meteors)
   hd_fast_meteors,hd_fast_non_meteors = meteor_objects(hd_pos_meteors)

   print("FAST METEORS:", fast_meteors)
   print("FAST HD METEORS:", hd_fast_meteors)

   print("NO SD METEOR FOUND.", fast_non_meteors)

   motion_objects,meteor_frames = detect_meteor_in_clip(video_file, frames, 0)
   motion_found = 0
   for obj in motion_objects:
      if motion_objects[obj]['report']['meteor_yn'] == 'Y':
         fast_meteors[obj] = motion_objects[obj]
         motion_found = 1
         print("MOTION METEOR OBJECTS!", motion_objects[obj])
   if motion_found == 0 and len(fast_meteors) == 0:
      md['arc_fail'] = "NO FAST METEORS AND NO MOTION FOUND IN SD."
      save_json_file(old_meteor_json_file, md)
      print("MOTION NOT FOUND!")
      return()

   motion_objects,meteor_frames = detect_meteor_in_clip(video_file, hd_frames, 0)
   motion_found = 0
   for obj in motion_objects:
      if motion_objects[obj]['report']['meteor_yn'] == 'Y':
         hd_fast_meteors[obj] = motion_objects[obj]
         motion_found = 1
         print("MOTION METEOR OBJECTS!", motion_objects[obj])
   if motion_found == 0 or len(hd_fast_meteors) == 0:
      print("MOTION NOT FOUND IN HD CLIP!")
      print("NO HD METEOR FOUND.", fast_non_meteors)
      md['arc_fail'] = "NO HD METEOR FOUND"
      save_json_file(old_meteor_json_file, md)
      return()



   for key in fast_meteors:
      sd_meteor = fast_meteors[key] 
   for key in hd_fast_meteors:
      hd_meteor = hd_fast_meteors[key] 


   sync_diff = refine_sync(0, sd_meteor, hd_meteor, hd_frames[0], frames[0])

   buf_size = 20

   print(sd_meteor)
   print(hd_meteor)

   sd_bs,sd_be = buffered_start_end(sd_meteor['ofns'][0],sd_meteor['ofns'][-1], len(frames), buf_size)
   if sd_bs == 0:
      buf_size = sd_meteor['ofns'][0]
   hd_bs,hd_be = buffered_start_end(hd_meteor['ofns'][0],hd_meteor['ofns'][-1], len(hd_frames), buf_size)

   new_trim_num = orig_sd_trim_num + sd_bs
   new_sd_clip_file = video_file.replace("trim-" + str(orig_sd_trim_num), "trim-" + str(new_trim_num))
   new_sd_clip_file = new_sd_clip_file.replace(".mp4", "-SD.mp4")
 
   new_hd_clip_file = new_sd_clip_file.replace("-SD", "-HD")
   new_json_file = new_sd_clip_file.replace("-SD.mp4", ".json")

   new_sd_gframes = frames[sd_bs:sd_be]
   new_hd_gframes = hd_frames[hd_bs:hd_be]

   new_sd_frames = color_frames[sd_bs:sd_be]
   new_hd_frames = hd_color_frames[hd_bs:hd_be]

   new_sd_sum_vals = sum_vals[sd_bs:sd_be]
   new_hd_sum_vals = hd_sum_vals[hd_bs:hd_be]
   new_sd_max_vals = max_vals[sd_bs:sd_be]
   new_hd_max_vals = hd_max_vals[hd_bs:hd_be]
   new_sd_subframes = subframes[sd_bs:sd_be]
   new_hd_subframes = hd_subframes[hd_bs:hd_be]

   print("FRAMES:", len(hd_frames), len(new_hd_frames)) 


   print("LEN NEW FRAMES: ", len(new_sd_frames), len(new_hd_frames))

   elapsed_time = time.time() - start_time
   print("SYNC_DIFF:", sync_diff)
   print("ELAPSED:", elapsed_time)

   # remaster the sync'd SD and HD frames
   temp_hd = new_hd_clip_file.split("/")[-1] 
   temp_sd = new_sd_clip_file.split("/")[-1] 
   temp_js = new_json_file.split("/")[-1] 


   (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(video_file)
   extra_sec = new_trim_num / 25
   start_trim_frame_time = f_datetime + datetime.timedelta(0,extra_sec)


   make_movie_from_frames(new_hd_frames, [0,len(new_hd_frames) - 1], "/mnt/ams2/matmp/" + temp_hd , 0)
   make_movie_from_frames(new_sd_frames, [0,len(new_sd_frames) - 1], "/mnt/ams2/matmp/" + temp_sd , 0)

   events,pos_meteors = fast_check_events(new_sd_sum_vals, new_sd_max_vals, new_sd_subframes)
   hd_events,hd_pos_meteors = fast_check_events(new_hd_sum_vals, new_hd_max_vals, new_hd_subframes)
   fast_meteors,fast_non_meteors = meteor_objects(pos_meteors)
   hd_fast_meteors,hd_fast_non_meteors = meteor_objects(hd_pos_meteors)

   if len(hd_fast_meteors) == 0:
      motion_objects,meteor_frames = detect_meteor_in_clip(video_file, new_hd_gframes, 0)
      motion_found = 0
      for obj in motion_objects:
         if motion_objects[obj]['report']['meteor_yn'] == 'Y':
            hd_fast_meteors[obj] = motion_objects[obj]
            motion_found = 1
            print("MOTION METEOR OBJECTS!", motion_objects[obj])
      if motion_found == 0:
         print("MOTION NOT FOUND IN HD CLIP!")
         print("NO HD METEOR FOUND.", fast_non_meteors)
         return()




   print("SD FAST:", fast_meteors)
   print("HD FAST:", hd_fast_meteors)
   if len(fast_meteors) == 0 and len(hd_fast_meteors) == 0:
      print("No fast meteors found!")
      return()

   if len(fast_meteors) == len(hd_fast_meteors) and len(fast_meteors) > 0:
      print("SD & HD METEOR DETECTED AND SYNC'D!")
   

   restack("/mnt/ams2/matmp/" + temp_hd)
   restack("/mnt/ams2/matmp/" + temp_sd)

   for key in hd_fast_meteors:
      hd_fast_meteor = hd_fast_meteors[key] 

   hd_fast_meteor['trim_clip'] = "/mnt/ams2/matmp/" + temp_sd
   hd_fast_meteor['hd_trim'] = "/mnt/ams2/matmp/" + temp_hd
   hd_fast_meteor['dt'] = start_trim_frame_time.strftime('%Y-%m-%d %H:%M:%S.%f')
   hd_fast_meteor['hd_file'] = temp_hd 
   hd_fast_meteor['sd_file'] = temp_sd 
   hd_fast_meteor['report']['dur'] = hd_fast_meteor['ofns'][-1] - hd_fast_meteor['ofns'][0] / 25 
   #hd_fast_meteor['dur'] = hd_fast_meteor['ofns'][-1] - hd_fast_meteor['ofns'][0] / 25 
   for i in range(0,len(hd_fast_meteor['ofns'])):
      if "ftimes" not in hd_fast_meteor:
         hd_fast_meteor['ftimes'] = []
      fn = hd_fast_meteor['ofns'][i]

      extra_meteor_sec = fn /  25
      meteor_frame_time = start_trim_frame_time + datetime.timedelta(0,extra_meteor_sec)
      meteor_frame_time_str = meteor_frame_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
      hd_fast_meteor['ftimes'].append(meteor_frame_time_str)



   #process_meteor_files(hd_fast_meteor, meteor_date, video_file, 1)

   calib,cal_params = apply_calib(hd_fast_meteor)
   hd_fast_meteor['calib'] = calib
   hd_fast_meteor['cal_params'] = cal_params
   print(hd_fast_meteor)
   new_json = save_new_style_meteor_json(hd_fast_meteor, temp_js)
   new_json['info']['org_sd_vid'] = org_sd_vid
   new_json['info']['org_hd_vid'] = org_hd_vid
   save_json_file("/mnt/ams2/matmp/" + temp_js, new_json)
   arc_dir = move_to_archive(temp_js)
   md['archive_file'] = arc_dir + temp_js
   save_json_file(old_meteor_json_file, md)


   write_archive_index(fy,fm)
   print(temp_js)
   #return(new_json_file_name)





def check_archive(day, run):
   old_meteor_files = glob.glob("/mnt/ams2/meteors/" + day + "/*trim*.json")
   mdir = "/mnt/ams2/meteors/" + day
   if cfe(mdir, 1) == 0:
      print("No meteors for this day.")
      return()
   print("/mnt/ams2/meteors/" + day + "/*trim*.json")

   omf = []
   good = 0
   bad = 0
   for mf in old_meteor_files:
      if "reduced" not in mf and "archive_report" not in old_meteor_files:
         jd = load_json_file(mf)
         if "archive_file" in jd:
            if cfe(jd['archive_file']) == 1:
               archive_data = {}
               archive_data['orig_file'] = mf
               archive_data['archive_file'] = jd['archive_file']
               archive_data['status'] = 1
               good = good + 1
            else:
               archive_data = {}
               archive_data['orig_file'] = mf
               archive_data['status'] = 0
               bad = bad + 1
               if "arc_fail" in jd:
                  print("ALREADY TRIED AND FAILED:", jd['arc_fail'])
         else:
            archive_data = {}
            archive_data['status'] = 0
         if archive_data['status'] != 1:
            archive_data['orig_file'] = mf
            archive_data['status'] = 0
            bad = bad + 1
            mp4_file = mf.replace(".json", ".mp4")
            if "arc_fail" in jd:
               print("ALREADY TRIED AND FAILED:", jd['arc_fail'])
            cmd = "./flex-detect.py debug2 " + mp4_file
            print(cmd) 
            if run == 1: 
               os.system(cmd)
         # check HD
         #if cfe(jd['hd_trim']) == 0:
         #   print("HD TRIM MISSING!", jd['hd_trim'])
         print(jd)
         noHD = 0 
         if "hd_trim" in jd: 
            if jd['hd_trim'] is not None:
               hd_stack = jd['hd_trim'].replace(".mp4", "-stacked.png")
            else:
               noHD = 1
         else:
            print("HD TRIM MISSING FROM ORIG JS:", mp4_file)
            noHD = 1
         #if cfe(hd_stack) == 0:
         #   print("HD STACK NOT FOUND:", hd_stack)


         omf.append(archive_data)
   save_json_file("/mnt/ams2/meteors/" + day + "/archive_report.json", omf)
   print("ARCHIVE REPORT FOR " + day)
   print("SUCCESS:", good)
   print("FAILED:", bad)
   print("/mnt/ams2/meteors/" + day + "/archive_report.json" )


def minimize_poly_params_fwd(cal_params_file, cal_params,json_conf,show=1):
   global tries
   tries = 0
   #cv2.namedWindow('pepe')

   fit_img_file = cal_params_file.replace("-calparams.json", ".png")
   if cfe(fit_img_file) == 1:
      fit_img = cv2.imread(fit_img_file)
   else:
      fit_img = np.zeros((1080,1920),dtype=np.uint8)

   #if show == 1:
   #   cv2.namedWindow('pepe')
   x_poly_fwd = cal_params['x_poly_fwd']
   y_poly_fwd = cal_params['y_poly_fwd']
   x_poly = cal_params['x_poly']
   y_poly = cal_params['y_poly']

   close_stars = cal_params['cat_image_stars']
   # do x poly fwd

   x_poly_fwd = np.zeros(shape=(15,),dtype=np.float64)
   y_poly_fwd = np.zeros(shape=(15,),dtype=np.float64)
   x_poly = np.zeros(shape=(15,),dtype=np.float64)
   y_poly = np.zeros(shape=(15,),dtype=np.float64)
   img_az = cal_params['center_az']
   img_el = cal_params['center_el']
   # reshape teh cat image stars.
   new_stars = []
   for star in cal_params['cat_image_stars']:
      #(star['name'],star['mag'],star['ra'],star['dec'],star['cat_und_pos'][0],star['cat_und_pos'][1],star['i_pos'][0],star['i_pos'][1],star['intensity'], star['dist_px'],json_file)
      (dcname,mag,ra,dec,cat_x, cat_y, img_x,img_y,intensity, match_dist, json_file) = star
      #(dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy, img_res,json_file) = star
      new_star = (dcname,mag,ra,dec,ra,dec,match_dist,cat_x,cat_y,img_az,img_el,cat_x,cat_y,img_x,img_y, match_dist) 
      new_stars.append(new_star)
      print(star) 
   cal_params['cat_image_stars'] = new_stars
   #(dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy, img_res) = star
   # d o x poly
   field = 'x_poly'
   res = scipy.optimize.minimize(reduce_fit, x_poly, args=(field,cal_params,cal_params_file,fit_img,json_conf), method='Nelder-Mead')
   x_poly = res['x']
   x_fun = res['fun']
   cal_params['x_poly'] = x_poly.tolist()
   cal_params['x_fun'] = x_fun

   # do y poly
   field = 'y_poly'
   res = scipy.optimize.minimize(reduce_fit, y_poly, args=(field,cal_params,cal_params_file,fit_img,json_conf), method='Nelder-Mead')
   y_poly = res['x']
   y_fun = res['fun']
   cal_params['y_poly'] = y_poly.tolist()
   cal_params['y_fun'] = y_fun

   # do x poly fwd
   field = 'x_poly_fwd'
   res = scipy.optimize.minimize(reduce_fit, x_poly_fwd, args=(field,cal_params,cal_params_file,fit_img,json_conf), method='Nelder-Mead')
   x_poly_fwd = res['x']
   x_fun_fwd = res['fun']
   cal_params['x_poly_fwd'] = x_poly_fwd.tolist()
   cal_params['x_fun_fwd'] = x_fun_fwd

   # do y poly fwd
   field = 'y_poly_fwd'
   res = scipy.optimize.minimize(reduce_fit, y_poly_fwd, args=(field,cal_params,cal_params_file,fit_img,json_conf), method='Nelder-Mead')
   y_poly_fwd = res['x']
   y_fun_fwd = res['fun']
   cal_params['y_poly_fwd'] = y_poly_fwd.tolist()
   cal_params['y_fun_fwd'] = y_fun_fwd


   print("POLY PARAMS")
   print("X_POLY", x_poly)
   print("Y_POLY", y_poly)
   print("X_POLY_FWD", x_poly_fwd)
   print("Y_POLY_FWD", y_poly_fwd)
   print("X_POLY FUN", x_fun)
   print("Y_POLY FUN", y_fun)
   print("X_POLY FWD FUN", x_fun_fwd)
   print("Y_POLY FWD FUN", y_fun_fwd)


   #img_x = 960
   #img_y = 540
   #new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(img_x,img_y,cal_params_file,cal_params,json_conf)
   #cal_params['center_az'] = img_az
   #cal_params['center_el'] = img_el
   #save_json_file(cal_params_file, cal_params)
   return(cal_params)

def batch_make_preview_image(day=0):
   if day != 0:
      meteor_dirs = ["/mnt/ams2/meteors/" + day]
   else:
      meteor_dirs = glob.glob("/mnt/ams2/meteors/*")
   year = day[0:4]
 
   tv_dir = None 
   station_id = json_conf['site']['ams_id']
   out = ""
   wasabi_out = ""
   for md in sorted(meteor_dirs,reverse=True):
      mfs = glob.glob(md + "/*trim*.json")
      if len(mfs) > 0:
         meteor_day = md.split("/")[-1]

         out += "<div style='clear:both'></div><H1><a href=/pycgi/webUI.py?cmd=meteors&limit_day=" + meteor_day + ">" + meteor_day + "</h1>"
         wasabi_out += "<div style='clear:both'></div>"
      for mf in mfs:
         if "reduced" not in mf and "manual" not in mf and "framedata" not in mf and "events" not in mf:
            print(mf)
            pi = mf.replace(".json", "-prev-full.jpg")
            pc = mf.replace(".json", "-prev-crop.jpg")
            if cfe(pi) == 0:
               make_preview_image(mf)
            meteor_year = meteor_day[0:4]
 
            arc_dir = "/mnt/ams2/meteor_archive/" + station_id + "/DETECTS/PREVIEW/" + meteor_year + "/" + meteor_day + "/" 
            tv_dir = "/" + station_id + "/DETECTS/PREVIEW/" + meteor_year + "/" + meteor_day + "/" 
            if cfe(arc_dir, 1) == 0:
               os.makedirs(arc_dir)
            pif = pi.split("/")[-1]
            if cfe(arc_dir + pif) == 0:
               cmd = "cp " + pi + " " + arc_dir
               cmd2 = "cp " + pc + " " + arc_dir
               os.system(cmd)
               os.system(cmd2)
               print("Copy to archive.", cmd, cmd2)
            else:
               print("Already done", mf)

            link = "<a href=/pycgi/webUI.py?cmd=reduce&video_file=" + mf + ">"
            out +=  "<div style='float: left'>" + link + "<img src=" + pc + "></a></div>\n"
            wmf = mf.split("/")[-1]
            wasabi_link = "<a href=#" + wmf + ">"
            wpc = pc.split("/")[-1]
            wpc = tv_dir + wpc
            wasabi_out +=  "<div style='float: left'>" + wasabi_link + "<img src=" + wpc + "></a></div>\n"

   if tv_dir is None:
      print("No meteors found on this day.")
   else:
      print("TV:", tv_dir)

      if cfe("/mnt/archive.allsky.tv" + tv_dir, 1) == 0:
         os.makedirs( "/mnt/archive.allsky.tv" + tv_dir)
      station_id = json_conf['site']['ams_id']
      prev_file = "/mnt/ams2/meteor_archive/" + station_id + "/DETECTS/PREVIEW/" + year + "/" + day + "/" + "index.html"
      wasabi_prev_file = "/mnt/archive.allsky.tv/" + station_id + "/DETECTS/PREVIEW/" + year + "/" + day + "/" + "index.html"
      fp = open(prev_file, "w")
      fp.write(out)
      print(prev_file)
      print(wasabi_prev_file)

      fp = open(wasabi_prev_file, "w")
      fp.write(wasabi_out)
      print(prev_file)
      print("DONE.")

def make_preview_image(json_file):
   sd_xs = []
   sd_ys = []
   hd_stack= None
   sd_stack= None
   hd_stack_img = None
   sd_stack_img = None
   if "/mnt/ams2/meteors" in json_file:
      # old meteor 
      jd = load_json_file(json_file)
      if 'hd_trim' in jd:
       
         hd_trim = jd['hd_trim']
         if hd_trim is not None and hd_trim != 0:
            hd_stack = hd_trim.replace(".mp4", "-stacked.png")
            if "/mnt/ams2/HD" in hd_stack:
               sfn = hd_stack.split("/")[-1]
               day = sfn[0:10]  
               hd_stack = "/mnt/ams2/meteors/" +day + "/" + sfn
               if cfe(hd_stack) == 0:
                  print("HD STACK NOT FOUND:", hd_stack)
                  hd_stack = None

      if 'sd_stack' in jd:
         sd_stack = jd['sd_stack']
      else:
         sd_stack = json_file.replace(".json", "-stacked.png")
         if cfe(sd_stack) == 0:
            sd_stack = None   
      if "sd_objects" in jd:
         sd_xs = []
         sd_ys = []
         for obj in jd['sd_objects']:
            print(obj)
            if "meteor" in obj:
               if obj['meteor'] == 1 or obj['meteor'] == "1":
                  for hist in obj['history']:
                     x = hist[1]
                     y = hist[2]
                     sd_xs.append(x)
                     sd_ys.append(y)
            elif len(jd['sd_objects']) == 1:
               for hist in obj['history']:
                  x = hist[1]
                  y = hist[2]
                  sd_xs.append(x)
                  sd_ys.append(y)
 
            else:
               print("NO METEOR IN SD OBJ")

   if sd_stack is not None:
      sd_stack_img = cv2.imread(sd_stack,0)
      hdm_x = 1920 / sd_stack_img.shape[1]
      hdm_y = 1080 / sd_stack_img.shape[0]
      print(sd_stack_img.shape)
   else:
      hdm_x = 1920/704
      hdm_y = 1080/576
   if hd_stack is not None and hd_stack_img is None and cfe(hd_stack) == 1:
      print("HDS:", hd_stack)
      hd_stack_img = cv2.imread(hd_stack,0)
      try:
         print("HD LOAD:", hd_stack_img.shape)
      except:
         hd_stack = None
         hd_stack_img = None

   if hd_stack is not None:
      if cfe(hd_stack) == 0:
         hd_stack = None

   if sd_stack is None or hd_stack is None:
      print("MISSING STACKS!", sd_stack, hd_stack)
      if sd_stack is not None:
         sd_stack_img = cv2.imread(sd_stack,0)
         if hd_stack is None:
            hd_stack_img = cv2.resize(sd_stack_img, (1920,1080))
            hd_stack = sd_stack
       
   print("SD STAC:", sd_stack)
   print("HD STAC:", hd_stack)
   print("SD POINTS:", sd_xs,sd_ys)

   if len(sd_xs) == 0 and sd_stack_img is None:
      print("FAILED")
      return()

   if len(sd_xs) == 0:
      max_x = sd_stack_img.shape[1] 
      max_y = sd_stack_img.shape[0] 
      min_x = 0
      min_y = 0
   else:
      max_x = max(sd_xs) #* hdm_x
      max_y = max(sd_ys) #* hdm_y
      min_x = min(sd_xs) #* hdm_x
      min_y = min(sd_ys) #* hdm_y

   max_hd_x = max_x * hdm_x
   max_hd_y = max_y * hdm_y
   min_hd_x = min_x * hdm_x
   min_hd_y = min_y * hdm_y

   # if the arc file exists use the frame data from that.
   if "archive_file" in jd:
      axs = []
      ays = []
      ad = load_json_file(jd['archive_file'])
      print("USING ARC!")
      if ad != 0:
         if "frames" in ad:
            for fr in ad['frames']:
               axs.append(fr['x'])
               ays.append(fr['y'])
            if len(axs) > 1:
               avg_hd_x = int(np.mean(axs))
               avg_hd_y = int(np.mean(ays))
               max_hd_x = max(axs) #* hdm_x
               max_hd_y = max(ays) #* hdm_y
               min_hd_x = min(axs) #* hdm_x
               min_hd_y = min(ays) #* hdm_y
            else:
               max_hd_x = 1920
               max_hd_y = 1080
               min_hd_x = 0
               min_hd_y = 0
            print("USING ARC VALUES!")
   else:
      print("NO ARC YET")
          
 


   cv2.rectangle(sd_stack_img, (min_x, min_y), (max_x, max_y), (255,255,255), 1, cv2.LINE_AA)
   #cv2.imshow('pepe', sd_stack_img)
   #cv2.waitKey(0)
   if len(sd_xs) > 0:
      cx = int(np.mean(sd_xs) * hdm_x)
      cy = int(np.mean(sd_ys) * hdm_y)
   else:
      cx = 1920  / 2
      cy = 1080 / 2
   width = int((max_x - min_x) * hdm_x)
   height = int((max_y - min_y) * hdm_y)

   cx1,cy1,cx2,cy2,mid_x,mid_y = find_crop_size(min_hd_x, min_hd_y, max_hd_x,max_hd_y)

   if hd_stack is None or cfe(hd_stack) == 0 and sd_stack_img is not None:
      try:
         hd_stack_img = cv2.resize(sd_stack_img, (1920,1080))
         hd_stack = sd_stack
      except:
         print("FAILED!", json_file, sd_stack, hd_stack)
         return()
   

   if hd_stack is not None and hd_stack_img is not None:
      print(cy1,cy2,cx1,cx2)
      prev_img = hd_stack_img[cy1:cy2,cx1:cx2]
      print("HD STACK:", hd_stack)
      print("SD STACK:", sd_stack)
      try:
         prev_img = cv2.resize(prev_img, (240,135))
         prev_img_full = cv2.resize(hd_stack_img, (240,135))
      except:
         sd_stack_img = cv2.imread(sd_stack, 0)
         hd_stack_img = cv2.resize(sd_stack_img, (1920,1080))
         print(sd_stack_img.shape)
         prev_img = hd_stack_img[cy1:cy2,cx1:cx2]
         prev_img = cv2.resize(prev_img, (240,135))
         prev_img_full = cv2.resize(sd_stack_img, (240,135))
      cv2.rectangle(hd_stack_img, (cx1, cy1), (cx2, cy2), (255,255,255), 1, cv2.LINE_AA)
      #cv2.imshow('pepe', prev_img)
      #cv2.waitKey(30)
      prev_img_file = json_file.replace(".json", "-prev-crop.jpg")
      prev_img_full_file = json_file.replace(".json", "-prev-full.jpg")
      print("SAVED:", prev_img_file)
      print("SAVED:", prev_img_full_file)
      cv2.imwrite(prev_img_file, prev_img,[int(cv2.IMWRITE_JPEG_QUALITY), 80])
      cv2.imwrite(prev_img_full_file, prev_img_full,[int(cv2.IMWRITE_JPEG_QUALITY), 80])

   if "meteor_archive" in json_file:
      print("ARC")
      # new meteor 

   if sd_stack is None and hd_stack is None:
      print("Both stacks are none?")
      exit()
     
def bound_169(cx,cy,width,height): 
   cx1 = cx - int(width/2) 
   cx2 = cx + int(width/2) 
   cy1 = cy - int(height/2) 
   cy2 = cy + int(height/2) 
   if cx1 < 0:
      cx1 = 0
      cx2 = width
   if cx2 >= 1920:
      cx1 = 1919 - width 
      cx2 = 1919 

   if cy1 < 0:
      cy1 = 0
      cy2 = height 
   if cy2 >= 1080:
      cy1 = 1080 - height 
      cy2 = 1079
   return(cx1,cx2,cy1,cy2)


def ffmpeg_crop(video_file,x,y,w,h, notrim=0):
   print("WIDTH: ", w)
   print("HEIGT: ", h)
   crop_out_file = video_file.replace(".mp4", "-crop.mp4")

   crop = "crop=" + str(w) + ":" + str(h) + ":" + str(x) + ":" + str(y)
   
   cmd = "/usr/bin/ffmpeg -i " + video_file + " -filter:v \"" + crop + "\" " + crop_out_file + " >/dev/null 2>&1"
   print(cmd)
   if cfe(crop_out_file) == 0:
      os.system(cmd)
   return(crop_out_file)

def ffmpeg_trim_crop(video_file,start,end,x,y,w,h, notrim=0):
   """ Take in video filename start and end trim clip frame numbers and ROI 
       And then make a file -crop.mp4 with those params
   """
   if cfe(video_file) == 0:
      print("VIDEO FILE DOESN'T EXIST!", video_file)
      return(0,0)
   #ffinfo = ffprobe(video_file)
   #if ffinfo[0] == 0:
   #   return(0,0)

   # first trim the clip to a temp file
   if True:
      start_sec = int(start / 25) - 1
      dur = int((end - start ) / 25) + 1
      if start_sec < 10:
         start_sec = "0" + str(start_sec)
      if dur < 2:
         dur = "02"
      elif dur < 10:
         dur = "0" + str(dur)

   if notrim == 0:
      trim_out_file = video_file.replace(".mp4", "-trim-" + str(start).zfill(4) + ".mp4")
      crop_out_file = video_file.replace(".mp4", "-trim-" + str(start).zfill(4) + "-crop.mp4")
      #cmd = "/usr/bin/ffmpeg -i " + video_file + " -ss 00:00:" + str(start_sec) + " -t 00:00:" + str(dur) + " -c copy " + trim_out_file 
      
      cmd = "/usr/bin/ffmpeg -i " + video_file + " -vf select='between(n\," + str(start) + "\," + str(end) + ")' -vsync 0 " + trim_out_file + " > /dev/null 2>&1"
      print(cmd)
      if cfe(trim_out_file) == 0:
         os.system(cmd)
   else:
      trim_out_file = video_file 
      crop_out_file = video_file.replace(".mp4", "-crop.mp4")

   crop = "crop=" + str(w) + ":" + str(h) + ":" + str(x) + ":" + str(y)
   
   cmd = "/usr/bin/ffmpeg -i " + trim_out_file + " -filter:v \"" + crop + "\" " + crop_out_file + " > /dev/null 2>&1"
   print(cmd)
   if cfe(crop_out_file) == 0:
      os.system(cmd)
   return(trim_out_file, crop_out_file)

def find_hd(sd_file):
   # first try to find a trim clip if it exists already
   # if not found, try to find the full minute file
   # return trim clip or full min file


   (sd_datetime, sd_cam, sd_date, sd_y, sd_m, sd_d, sd_h, sd_M, sd_s) = convert_filename_to_date_cam(sd_file)
   hd_glob = "/mnt/ams2/HD/" + sd_y + "_" + sd_m + "_" + sd_d + "_" + sd_h + "_*" + sd_cam + "*.mp4"
   print("HD:", hd_glob)
   hd_files = sorted(glob.glob(hd_glob))
   hd = []
   for hd_file in hd_files:
      (hd_datetime, hd_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s) = convert_filename_to_date_cam(hd_file)
      t_diff = (hd_datetime - sd_datetime).total_seconds()
      if "crop" not in hd_file:
         hd.append((hd_file,t_diff,abs(t_diff)))
   hd_sort = sorted(hd, key=lambda x: x[2], reverse=False)     
   return(hd_sort)

def play_clip(video_file,cx1=0,cy1=0,cx2=0,cy2=0):
   sd_frames,sd_color_frames,sd_subframes,sum_vals,max_vals,pos_vals = load_frames_fast(video_file, json_conf, 0, 0, [], 1,[])
   for frame in sd_color_frames:

      cv2.rectangle(frame, (cx1, cy1), (cx2, cy2), (255,255,255), 1, cv2.LINE_AA)
      cv2.imshow('pepe', frame)
      cv2.waitKey(0)

def get_cam_sizes(day=None):
   if day is None:
      now = datetime.datetime.now()
      day = now.strftime("%Y_%m_%d")
   
   cam_size_info = {}
   for cam in json_conf['cameras']:
      w,h = 0,0
      ip = json_conf['cameras'][cam]['ip']
      sd_url  = json_conf['cameras'][cam]['sd_url']
      cams_id = json_conf['cameras'][cam]['cams_id']
      cam_files = glob.glob("/mnt/ams2/SD/proc2/" + day + "/*" + cams_id + "*.mp4")
      #print("/mnt/ams2/SD/proc2/" + day + "/*" + cams_id + "*.mp4")
      #print(cam_files)
      for cam_file in cam_files:
         #cam_file = cam_files[0]
         try:
            w,h = ffprobe(cam_file)
            break 
         except:
            print("ffprobe failed:", cam_file)
            continue
         print(cams_id, w, h)
      if w != 0:
         json_conf['cameras'][cam]['dim'] = [int(w),int(h)]
      
         cam_size_info[cams_id] = [int(w),int(h)]
   total_cams = len(json_conf['cameras'].keys())
   total_cams_size = len(cam_size_info.keys())
   save_json_file("../conf/as6.json", json_conf) 
   print("TOTAL CAMS / SIZES:", total_cams, total_cams_size)
   if total_cams > total_cams_size:
      print("Problem getting cams sizes!")
      #exit()
   return(cam_size_info)

def clean_bad_vals(day):
   cmd = "rm /mnt/ams2/SD/proc2/" + day + "/data/*trim*.json" 
   os.system(cmd)
   #exit()

def batch_vals(day):
   clean_bad_vals(day)
   cam_size_info = get_cam_sizes(day)
   #print(json_conf['cameras'])
   running = check_running(".py bv")
   print("RUNNING:", running)
   if running > 2:
      print("already running")
      exit()
   data_dir = "/mnt/ams2/SD/proc2/" + day + "/data/"
   temp = glob.glob(data_dir + "*.json")
   val_files = []
   all = {}
   for tem in temp:
      if "crop" not in tem and "-vals" in tem:
         val_files.append(tem)
      all[tem] = 1
   meteors = 0
   maybe_meteors = 0
   too_many = 0
   detects = 0
   vc = 0
   for vf in sorted(val_files, reverse=True):
      (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(vf)
      mf = vf.replace("-vals.json", "-meteor.json")
      nm = vf.replace("-vals.json", "-nometeor.json")
      df = vf.replace("-vals.json", "-detect.json")
      mmf = vf.replace("-vals.json", "-maybe-meteors.json")
      tf = vf.replace("-vals.json", "-toomany.json")
      if mf not in all and df not in all and tf not in all and mmf not in all and nm not in all:
      #if cfe(mf) == 0 and cfe(df) == 0 and cfe(tf) == 0 and cfe(mmf) == 0 and cfe(nm) == 0:
         sun_status = day_or_night(f_datetime)
         if sun_status == 'night':
            print("VF:", vf)
            detect_in_vals(vf, cam_size_info)
         else:
            print("Skip daytime file.")
            os.system("rm " + vf)
      else:
         if vc % 100 == 0:
            print(vc, "ALREADY DONE:")

      if mf in all:
         meteors += 1
      if mmf in all :
  
         maybe_meteors += 1
         #maybe = load_json_file(mmf)
         #if maybe != 0:
         #   for id in maybe['objects']:
         #      obj = maybe['objects'][id]
               #if obj['report']['meteor_yn'] == 'Y': 
               #   print("REPORT CLASS METEOR:",  obj['report']['meteor_yn'] ,  obj['report']['classify']['meteor_yn'] )
      if tf in all == 1:
         too_many += 1
      if df in all == 1:
         detects += 1
      vc += 1

   worked_files = meteors + maybe_meteors + too_many + detects
   print("VALS/COMPLETED:", len(val_files)-1, worked_files)
   print("METEORS:", meteors)
   print("MAYBE METEORS:", maybe_meteors)
   print("TOO MANY:", too_many)
   print("DETECTS :", detects)
   


def get_roi(pos_vals=None, object=None, hdm_x=1, hdm_y=1):
   print("HDM_X/HDM_Y", hdm_x, hdm_y)
   xs = []
   ys = []
   if pos_vals is not None:
      for x,y in ev['pos_vals']:
         print("POS VALS:", x,y)
         xs.append(int(x*hdm_x))
         ys.append(int(y*hdm_y))
         fn += 1
   elif object is not None:
      for i in range(0, len(object['oxs'])):
         xs.append(int(object['oxs'][i]) * hdm_x)
         ys.append(int(object['oys'][i]) * hdm_y)
   min_x = min(xs)
   max_x = max(xs)
   max_y = max(ys)
   min_y = min(ys)
   cx1,cy1,cx2,cy2,mid_x,mid_y = find_crop_size(min_x, min_y, max_x,max_y, hdm_x, hdm_y)

   return(cx1,cy1,cx2,cy2,mid_x,mid_y)

def check_pt_in_mask(masks, px,py):
   for m in masks:
      x1,y1,w,h = m.split(",")
      x1 = int(x1)
      y1 = int(y1)
      w = int(w)
      h = int(h)
      x2 = x1 + w
      y2 = y1 + h
      print("CHECK MASK:", px, py, x1 , x2 ,y1, y2)
      if py == 0 or px == 0:
         return(1)
      if x1 <= px <= x2 and y1 <= py <= y2:
         return(1)
   return(0)

def detect_in_vals(vals_file, cam_size_info):
   (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(vals_file)
   sun_status = day_or_night(f_datetime)
   print(sun_status)
   cam = cam.replace("-vals.json", "")

   masks = get_masks(cam, json_conf,0)
   day = fy + "_" + fm + "_" + fd
   trim_too = 0
   if "mp4" in vals_file and "proc2" in vals_file:
      vfn = vals_file.split("/")[-1]
      bsd = vals_file.replace(vfn, "")
      vals_file = bsd + "data/" + vfn
      vals_file = vals_file.replace(".mp4", "-vals.json")
   video_file = vals_file.replace("-vals.json", ".mp4")
   video_file = video_file.replace("data/", "")

   #w,h = ffprobe(video_file)
   w,h = cam_size_info[cam]
   hdm_x = 1920 / int(w)
   hdm_y = 1080 / int(h)

   data = load_json_file(vals_file)
   events = []
   data_x = []
   data_y = []
   cm =0
   last_i = None
   objects = {}
   if data is False:
      print(vals_file + " is none.")
      os.system("rm " + vals_file)
      return()
   for i in range(0,len(data['max_vals'])):
      #print(i, cm)
      if "pos_vals" in data:
         if i < len(data['pos_vals']) :
            if isinstance(data['pos_vals'][i], int) is False:
               x,y = data['pos_vals'][i]
            else :
               x,y = 0,0
         else :
            x,y = 0,0
      else:
         x,y = 0,0
      max_val = data['max_vals'][i]
      if max_val > 10:
         if last_i is not None and  last_i + 1 == i:
            cm += 1
         else:
            cm = 0
         data_x.append(x)
         data_y.append(y)
         #object, objects = find_object(objects, i,x, y, 10, 10, max_val, 0, 0, None,0)
      else:
         if cm >= 3:
            e_end = i
            e_start = i - cm
            #e_start -= 5
            #e_end += 5
            event = {}
            event['frames'] = [e_start,e_end]
            if "pos_vals" in data:
               event['pos_vals'] = data['pos_vals'][e_start:e_end]
            event['max_vals'] = data['max_vals'][e_start:e_end]
            event['sum_vals'] = data['sum_vals'][e_start:e_end]
            events.append(event)
         cm = 0
      last_i = i


   #print("End first vals profile", last_i )
   print("EVENTS FOUND:", len(events))
   for ev in events:
      {'frames': [1, 8], 'pos_vals': [[504, 472], [564, 420], [538, 426], [654, 392], [548, 424], [682, 354], [134, 418]], 'max_vals': [14.0, 14.0, 13.0, 16.0, 12.0, 17.0, 12.0], 'sum_vals': [0.0, 0.0, 0.0, 255.0, 0.0, 510.0, 0.0]}
      start_frame = ev['frames'][0]
      ff = 0
      for point in ev['pos_vals']:
         px,py = point
         max_val = ev['max_vals'][ff]
         fn = start_frame + ff
         ff += 1
         #data_x.append(x)
         #data_y.append(y)
         masked = check_pt_in_mask(masks, px, py)
         if masked == 0:
            object, objects = find_object(objects, fn,px, py, 10, 10, max_val, 0, 0, None,0)
            print("OBJ:", px, py, cam, object)
         #else:
         #   print("MASKED POINT!")

      #print(ev)
   for obj in objects: 
      objects[obj] = analyze_object(objects[obj], 0, 1, 1)
   bad_obj = []
   for obj in objects:
      if len(objects[obj]['oxs'] ) < 3:
         bad_obj.append(obj)
      #else:
      #   print(obj, objects[obj])
   for obj in bad_obj:
      del(objects[obj])
   #if len(events) > 0:
   #   exit()
   suspect_meteors = []
   clip_fns = []
   for obj in objects:
      if objects[obj]['report']['meteor_yn'] == "Y":
         clip_fns.append(min(objects[obj]['ofns']))
         clip_fns.append(max(objects[obj]['ofns']))
         #print(obj, objects[obj]['ofns'], objects[obj]['report']['meteor_yn'], objects[obj]['report']['bad_items']  )
         #print(objects[obj]['oxs'], objects[obj]['oys'])
         suspect_meteors.append(objects[obj])
      # check here for files with no POS vals. If they have good cm events then pluck them out and detect video on them 
      #else:
      #   print(obj, objects[obj]['ofns'], objects[obj]['report']['meteor_yn'], objects[obj]['report']['bad_items']  )

   if len(clip_fns) == 0:
      print("NO METEORS.")
      detect_info = {}
      detect_info['events'] = events 
      detect_info['objects'] = objects 
      detect_file = vals_file.replace("-vals.json", "-detect.json")
      save_json_file(detect_file, detect_info)
      return()

   if len(suspect_meteors) > 1:
      print("more than one many meteor!")
  
      for obj in objects:
         if objects[obj]['report']['meteor_yn'] == "Y":
            start = objects[obj]['ofns'][0]
            end = objects[obj]['ofns'][-1]
            start_fn, end_fn= buffered_start_end(start,end, 1499, 50)
            x,y,w,h = 0,0,0,0
            cx1,cy1,cx2,cy2,mid_x,mid_y = get_roi(None, objects[obj], hdm_x, hdm_y)
            #ffmpeg_trim_crop(video_file,start_fn,end_fn,cx1,cy1,cx2-cx1,cy2-cy1, 0)

      detect_info = {}
      detect_info['events'] = events 
      detect_info['objects'] = objects 
      detect_file = vals_file.replace("-vals.json", "-toomany.json")
      save_json_file(detect_file, detect_info)
      print("Too many meteors.", len(suspect_meteors))
      for m in suspect_meteors:
         print(m['report'])
      return()

   if len(suspect_meteors) > 0:
      print("SUSPECT METEOR FOUND!")
      detect_info = {}
      detect_info['events'] = events 
      detect_info['objects'] = objects 
      detect_info['maybe_meteors'] = suspect_meteors 
      detect_file = vals_file.replace("-vals.json", "-maybe-meteors.json")

      meteor_file = vals_file.replace("-vals.json", "-maybe-meteors.json")
      save_json_file(meteor_file, detect_info)
      print(meteor_file)
      complete_vals_detect(meteor_file)


   
   return()

def preview_crop(video_file, x1,y1,x2,y2,frames=None,obj=None):
   temp_dir = "/mnt/ams2/temp/"
   cmd = "/usr/bin/ffmpeg -i " + video_file + " -vf select='between(n\," + str(1) + "\," + str(2) + ")' -vsync 0 " + temp_dir + "frames%d.png > /dev/null"
   os.system(cmd)
   img = cv2.imread(temp_dir + "frames1.png")
   
   cv2.rectangle(img, (x1, y1), (x2, y2), (255,255,255), 1, cv2.LINE_AA)
   cv2.imshow('pepe', img) 
   cv2.waitKey(0)
   if frames is not None:
      for fimg in frames:
         cv2.rectangle(fimg, (x1, y1), (x2, y2), (255,255,255), 1, cv2.LINE_AA)
         if obj is not None:
            for i in range(0,len(obj['ofns'])):
               px = obj['oxs'][i]
               py = obj['oys'][i]
               cv2.circle(fimg,(px,py), 10, (100,0,0), 1)
         cv2.imshow('pepe', fimg) 
         cv2.waitKey(0)

   #cv2.imwrite('test' + str(x1) + ".jpg", img)

def meteor_report(meteor):
   if "report" in meteor:
      if meteor['report']['meteor_yn'] != "Y":
         return()
      print("FNss", meteor['ofns'])
      print("Xs", meteor['oxs'])
      print("Ys", meteor['oys'])
      print("Ws", meteor['ows'])
      print("Hs", meteor['ohs'])
      print("Ints", meteor['oint'])
      for key in meteor['report']:
         if key != "classify":
            print(key, meteor['report'][key])   
      print("CLASSIFY")
      for key in meteor['report']['classify']:
         print(key, meteor['report']['classify'][key])   

def frame_composite(crop_file = None, crop_frames = None, object = None ):
   """ Make frame composite image from crop_file or crop frames 
   """
   comp_info = {}
   if crop_file is not None:
      crop_frames,crop_color_frames,crop_subframes,sum_vals,max_vals,pos_vals = load_frames_fast(crop_file, json_conf, 0, 0, [], 1,[])
   print("total vid frames = ", len(crop_frames))
   print("crop size:", crop_frames[0].shape)
   fh,fw = crop_frames[0].shape[:2]
   print("total meteor frames:", len(object['ofns']))
   print("meteor frames:", object['ofns'])
   total_slots = (object['ofns'][-1] - object['ofns'][0]) + 10
   #total_slots = len(crop_frames)
   max_cols = math.ceil(1920 / crop_frames[0].shape[1])
   max_rows = math.ceil(1080 / crop_frames[0].shape[0])
   print("MAX ROWS/COLS IN 1920x1080 PIC FOR THIS PREV IMAGE SIZE:", max_cols, max_rows)
   total_frames_allowed = max_cols * max_rows 
   print("Total allowed frames:", total_frames_allowed) 
   print("Total frames needed:", total_slots) 
   rows_needed = math.ceil(total_slots / max_cols)
   print("ROWS NEEDED:", rows_needed)
   print("COLS :", max_cols)
   ciw = 1920
   cih = rows_needed * fh
   custom_frame = np.zeros((cih,ciw,3),dtype=np.uint8)

   last_fn = None
   min_fn = object['ofns'][0] - 5
   max_fn = object['ofns'][-1] + 5
   fc = min_fn 
   for r in range(0,rows_needed):
      for c in range(0, max_cols):
         x1 = c * fw 
         y1 = r * fh 
         x2 = x1 + fw
         y2 = y1 + fh
         #print("Row/Col:", r,c, x1,y1,x2,y2)
         custom_frame[y1:y2,x1:x2,0:3] = crop_color_frames[fc]
         cv2.imshow('pepe', custom_frame)
         cv2.waitKey(0)
         fc += 1
   comp_file = crop_file.replace("-crop.mp4", "-comp.jpg")
   cv2.imwrite(comp_file, custom_frame)
   comp_info['crop_file'] = crop_file 
   comp_info['min_fn'] = min_fn
   comp_info['max_fn'] = max_fn
   comp_info['frame_size'] = [fw,fh] 
   comp_info['comp_size'] = [custom_frame.shape[1], custom_frame.shape[0]]
   return(comp_file,custom_frame,comp_info)

def archive_meteor(meteor_file):
   old_sd_vid = None
   old_hd_vid = None
   mj = load_json_file(meteor_file)

   if "archive_file" in mj:
      if mj['archive_file'] != "":
         print("Already archived:", meteor_file)
         return()

   # File has not been archived yet. 
   if "trim_clip" in mj:
      old_sd_vid = mj['trim_clip']
   if "hd_trim" in mj:
      old_hd_vid = mj['hd_trim']
   if cfe(old_sd_vid):
      sd_frames,sd_color_frames,sd_subframes,sum_vals,max_vals,pos_vals = load_frames_fast(old_sd_vid, json_conf, 0, 0, [], 1,[])
   if cfe(old_hd_vid):
      hd_frames,hd_color_frames,hd_subframes,hd_sum_vals,hd_max_vals,hd_pos_vals = load_frames_fast(old_hd_vid, json_conf, 0, 0, [], 1,[])
   print("SD FRAMES:", len(sd_frames))
   print("HD FRAMES:", len(hd_frames))

   # detect on SD file
   motion_objects,meteor_frames = detect_meteor_in_clip(old_sd_vid, sd_frames, 0)
   sd_meteors = only_meteors(motion_objects)

   # Get ROI for this SD meteor
   hdm_x, hdm_y = get_hdm(sd_frames[0])
   #obj = hist_to_obj(mj['sd_objects'][0]['history'])
   cx1,cy1,cx2,cy2,mid_x,mid_y = get_roi(None, sd_meteors[0], 1, 1)

   print("HDMX:", hdm_x, hdm_y)
   hcx1,hcy1,hcx2,hcy2,mid_x,mid_y = get_roi(None, sd_meteors[0], hdm_x, hdm_y)
   
   #preview_crop(old_hd_vid, hcx1,hcy1,hcx2,hcy2, hd_frames)

   sd_crop_file = ffmpeg_crop(old_sd_vid,cx1,cy1,cx2-cx1,cy2-cy1, 0)

  
   hd_crop_file = ffmpeg_crop(old_hd_vid,hcx1,hcy1,hcx2-hcx1,hcy2-hcy1, 0)

   hd_motion_objects,hd_crop_frames = detect_meteor_in_clip(hd_crop_file, None, 0,hcx1,hcx2,0)

   sd_meteors = only_meteors(motion_objects)
   hd_meteors = only_meteors(hd_motion_objects)
   comp_file, comp_img,comp_info = frame_composite(hd_crop_file, None, hd_meteors[0])
   print(comp_file)
   comp_info['x1'] = hcx1
   comp_info['y1'] = hcy1
   comp_info['y1'] = hcy1
   comp_info['y2'] = hcy2
   print(comp_info)
   print("SD ROI:", cx1,cy1,cx2,cy2)
   print("HD ROI:", hcx1,hcy1,hcx2,hcy2)
   print(old_sd_vid)
   print(old_hd_vid)
   print(sd_crop_file)
   print(hd_crop_file)

   print("SD MO:", len(motion_objects))
   print("HD MO:", len(hd_motion_objects))
   print("SD FNS:", sd_meteors[0]['ofns'])
   print("HD FNS:", hd_meteors[0]['ofns'])

def hist_to_obj(hist):
   o = {}
   o['ofns'] = []
   o['oxs'] = []
   o['oys'] = []
   o['ows'] = []
   o['ohs'] = []
   o['oints'] = []
   for h in hist:
      o['ofns'].append(h[0])
      o['oxs'].append(h[1])
      o['oys'].append(h[2])
      o['ows'].append(h[3])
      o['ohs'].append(h[4])
      o['oints'].append(0)

   print(hist)
   print(o)
   return(o)

def get_hdm(frame):
   hdm_x = 1920 / frame.shape[1] 
   hdm_y = 1080 / frame.shape[0] 
   return(hdm_x, hdm_y)

def verify_toomany_detects(day=None):
   print("Verify too many.")
   if day == None:
      return("pass day!")
   print("/mnt/ams2/SD/proc2/" + day + "/data/*toomany.json")
   files = glob.glob("/mnt/ams2/SD/proc2/" + day + "/data/*toomany.json")
   for file in files:
      nm = file.replace("toomany", "nometeor")
      mm = file.replace("toomany", "meteor")
      df = file.replace("toomany", "detect")
      if cfe(nm) == 1:
         print("Too many file contains no meteors.")
         cmd = "mv " + file + " " + df 
         os.system(cmd)
         print(cmd)
      elif cfe(mm) == 1:
         print("Too many file contains meteors.")
         cmd = "mv " + file + " " + df 
         print(cmd)
         os.system(cmd)
      else:
         status = verify_toomany(file)
         print("VERIFY:", status, file)
     

def verify_toomany(file):
   js = load_json_file(file) 
   if js == 0:
      print("JS 0:", file)
      os.system("rm " + file)
      return()
      #exit()
   for obj in js['objects']:
      fr = len(js['objects'][obj]['oxs'])
      if fr > 5:
         js['objects'][obj]['report']['classify'] = classify_object(js['objects'][obj], sd=1)

   if js != 0:
      #os.system("rm " + js)

      meteors = only_meteors(js['objects'])
      print("METEORS:", len(meteors))
      if len(meteors) > 0:
         print("Total Events: ", len(js['events']))
         print("Total Objects: ", len(js['objects']))
         print("Meteors: ", len(meteors))
         js['maybe_meteors'] = meteors
         save_json_file(file, js)
         new_file = file.replace("toomany", "maybe-meteors")
         save_json_file(new_file, js)
         os.system("rm " + file)
         return(1)
      else:
         new_file = file.replace("toomany", "nometeors")
         cmd = "mv " + file + " " + new_file
         print(cmd)
         os.system(cmd)
         return(0)
   else:
      print("No good meteors here.")
      df = file.replace("toomany", "detect")
      cmd = "mv " + file + " " + df 
      print(cmd)
      os.system(cmd)
      return(0)


def verify_meteors(day=None):
   print("Verify Meteors")
   if day == None:
      days = glob.glob("/mnt/ams2/SD/proc2/*")
      for day in days:
         if cfe(day, 1) == 1 and ("json" not in day and "2019" not in day and "meteors" not in day and "all" not in day and 'daytime' not in day):
            # include the too many meteor files
            os.system("./flex-detect.py vtms " + day)
            glob_dir = day + "/data/*maybe-meteors.json"
            files = glob.glob(glob_dir)
            for file in files:
               (f_datetime, cam_id, f_date_str,fy,fmin,fd,fh, fm, fs) = parse_file_data(file)
               sun_status = day_or_night(f_datetime)

               if "trim" not in file:
                  #print("VERIFY:", sun_status, file)
                  verify_meteor(file)
               #else: 
               #   print("SKIP:", file)
   else:
      # include the too many meteor files
      os.system("./flex-detect.py vtms " + day)
      glob_dir = "/mnt/ams2/SD/proc2/" + day + "/data/*maybe-meteors.json"
      files = glob.glob(glob_dir)
      for file in files:
         (f_datetime, cam_id, f_date_str,fy,fmin,fd,fh, fm, fs) = parse_file_data(file)
         sun_status = day_or_night(f_datetime)
         if "trim" not in file:
            verify_meteor(file)
         else:
            os.system("rm " + file)
  
def load_cam_sizes():
   cam_size_info = {}
   global json_conf
   for cam in json_conf['cameras']: 
      
      cams_id = json_conf['cameras'][cam]['cams_id']
      if "dim" not in json_conf['cameras'][cam]:
         cam_size_info = get_cam_sizes()
         json_conf = load_json_file('../conf/as6.json')
      else:
         cam_size_info[cams_id] = json_conf['cameras'][cam]['dim']
   return(cam_size_info)

def verify_meteor(meteor_json_file):
   # Call this on a detection file to verify the detection as a meteor and make / save the trim clips
   fail = 0
   if cfe(meteor_json_file) == 0:
      print("No file bro.")
      return()
   (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(meteor_json_file)
   masks = get_masks(cam, json_conf,0)
   day = fy + "_" + fm + "_" + fd
   proc_dir = "/mnt/ams2/SD/proc2/" + day + "/hd_save/"
   if "maybe-meteors" in meteor_json_file:
      vals_file = meteor_json_file.replace("-maybe-meteors.json", "-vals.json")
      detect_file = meteor_json_file.replace("-maybe-meteors.json", "-detect.json")
      meteor_file = meteor_json_file.replace("-maybe-meteors.json", "-meteor.json")
      video_file = meteor_json_file.replace("-maybe-meteors.json", ".mp4")
      video_file = video_file.replace("data/", "")
   if "toomany" in meteor_json_file:
      vals_file = meteor_json_file.replace("-toomany.json", "-vals.json")
      detect_file = meteor_json_file.replace("-toomany.json", "-detect.json")
      meteor_file = meteor_json_file.replace("-toomany.json", "-meteor.json")
      video_file = meteor_json_file.replace("-toomany.json", ".mp4")
      video_file = video_file.replace("data/", "")

   cam_size_info = load_cam_sizes()
   w,h = cam_size_info[cam]
   if w == 0:
      #os.system("mv " + meteor_json_file + " " + detect_file)
      print("BAD TRIM FILE!", video_file)
      return()
   hdm_x = 1920 / int(w)
   hdm_y = 1080 / int(h)

   mj = load_json_file(meteor_json_file)
   if mj == None or mj == 0:
      print("No mj :", meteor_json_file)
      return()

   suspect_meteors = only_meteors(mj['objects'])


   good_met = []
   if len(suspect_meteors) > 0:
      for maybe in suspect_meteors:
         if maybe['report']['classify']['meteor_yn'] == 'Y':
            #meteor_report(maybe)
            masked_points = []
            masked_obj = 0 
            for i in range(0, len(maybe['oxs'])):
               mx = maybe['oxs'][i]
               my = maybe['oys'][i]
               masked = check_pt_in_mask(masks, mx, my)
               if masked == 1:
                  masked_points.append(i)
            if len(masked_points) > 0:
               perc = len(masked_points) / len(maybe['oxs']) 
               if perc > .5:
                  masked_obj = 1
                  print("SKIP MASKED OBJECT HERE!")
            if masked_obj == 0:
               good_met.append(maybe)
               print(cam, masks)
            print("MASKED POINTS:", masked_points)
         else:
            print("Failed 2nd classification. Not a real meteor.")
            meteor_report(maybe)
           # return()
         #cont = input("continue")
   suspect_meteors = good_met
   print(len(good_met), " suspect meteors")
   print(good_met)
   #cont = input("continue")

   if len(suspect_meteors) == 0:
      print("No real meteors found here.")
      # mv the maybe file to detect so we don't try to check it again. 
      os.system("mv " + meteor_json_file + " " + detect_file)
      return()

   if len(suspect_meteors) == 1:
      print("SUSPECT METEORS!")
      print(suspect_meteors)


   #print("SUS:", len(suspect_meteors))
   #exit()

   #if len(suspect_meteors) == 1:
   for i in range(0, len(suspect_meteors)):
      trim_file, start_fn,end_fn, cx1,cy1,cx2,cy2,mid_x,mid_y = get_vals_trim(video_file, suspect_meteors[i])

      #print("CX1,2 CY1,2:", cx1, cx2, cy1, cy2)
      #exit()

      print("MIKE TRIM FILE:", trim_file)

      if trim_file == 0:
         print("BAD TRIM FILE FOR :", video_file)
         os.system("mv " + meteor_json_file + " " + detect_file)
         print("MIKE! mv " + meteor_json_file + " " + detect_file)
         tm = detect_file.replace("detect", "toomany")
         os.system("rm " + tm )
         return()
      print("TF:", trim_file)
      sd_prev_crop=[cx1,cy1,cx2,cy2,mid_x,mid_y]
      #preview_crop(trim_file, cx1,cy1,cx2,cy2)
      trim_crop_file = trim_file.replace(".mp4", "-crop.mp4")
      sd_motion_objects,sd_meteor_frames = detect_meteor_in_clip(trim_crop_file, None, 0,cx1,cx2,0)
      #MIKE
      print(sd_motion_objects)
      sd_meteors = only_meteors(sd_motion_objects)
      print(sd_meteors)

      #exit()

      if sd_meteors is None:
         print("No real meteors found here.")

         # mv the maybe file to detect so we don't try to check it again. 
         os.system("mv " + meteor_json_file + " " + detect_file)
         print("MIKE! mv " + meteor_json_file + " " + detect_file)
         return()


      # if we made it this far we have a possible meteor detect. 
      print("START FN:", start_fn, end_fn)
      hd_file, hd_trim,time_diff_sec, dur = find_hd_file_best(trim_file, start_fn, end_fn-start_fn, 1)
      print("HD FILE:", hd_trim)

      hd_x1,hd_y1,hd_x2,hd_y2,hd_mid_x,hd_mid_y = get_roi(None, suspect_meteors[i], hdm_x, hdm_y)

      hd_prev_crop=[hd_x1,hd_y1,hd_x2,hd_y2,hd_mid_x,hd_mid_y]

      #preview_crop(hd_trim, hd_x1,hd_y1,hd_x2,hd_y2)


      hd_crop_file = ffmpeg_crop(hd_trim,hd_x1,hd_y1,hd_x2-hd_x1,hd_y2-hd_y1, 0)


      trim_crop_file = trim_file.replace(".mp4", "-crop.mp4")


      if sd_meteors is not None: 
         hd_motion_objects,hd_meteor_frames = detect_meteor_in_clip(hd_crop_file, None, 0,hd_x1,hd_y1,1)
         hd_meteors = only_meteors(hd_motion_objects)
         if hd_meteors is None: 
            hd_meteors =[]

         if len(sd_meteors) == 1 or len(hd_meteors) == 1:
            meteor = {}
            meteor['hd_motion_objects'] = hd_motion_objects
            meteor['motion_objects'] = sd_motion_objects
            meteor['hd_trim'] = hd_trim
            meteor['sd_trim'] = trim_file
            sd_meteors = meteors_only(sd_motion_objects)
            hd_meteors = meteors_only(hd_motion_objects)
            meteor['sd_meteors'] = sd_meteors
            meteor['hd_meteors'] = hd_meteors
            meteor['hd_prev_crop'] = hd_prev_crop 
            meteor['sd_prev_crop'] = sd_prev_crop 
            meteor_file = vals_file.replace("-vals.json", "-meteor.json")
            print("METEOR:", meteor_file)
            # Copy all media for this meteor to the proc hd_save dir
            if cfe(proc_dir, 1) == 0:
               os.makedirs(proc_dir)
            tfn = trim_file.split("/")[-1]
            tfn_hd = hd_trim.split("/")[-1]
            meteor['sd_trim'] = proc_dir + tfn
            meteor['hd_trim'] = proc_dir + tfn_hd
            os.system("cp " + hd_trim + " " + proc_dir)
            os.system("cp " + hd_crop_file + " " + proc_dir)
            os.system("cp " + trim_file + " " + proc_dir)
            os.system("cp " + trim_crop_file + " " + proc_dir)
            os.system("cp " + hd_file + " " + proc_dir)
            meteor_report(sd_meteors)
            meteor_report(hd_meteors)
            meteor['hdm_x'] = hdm_x
            meteor['hdm_y'] = hdm_y
            save_json_file(meteor_file, meteor)
            os.system("mv " + meteor_json_file + " " + detect_file)
            print("VERIFY METEOR.", meteor_file)

         else:
            print("Something wierd? Maybe a bird", len(sd_meteors), len(hd_meteors))
            print("No real meteors found here.")
            for o in hd_motion_objects:
               print("HD:", hd_motion_objects[o])
            for o in sd_motion_objects:
               print("SD:", sd_motion_objects[o])
            
            # mv the maybe file to detect so we don't try to check it again. 
            detect_file = detect_file.replace("-detect.json", "-nometeor.json")
            os.system("mv " + meteor_json_file + " " + detect_file)
            print("mv " + meteor_json_file + " " + detect_file)


            continue
      else:
         print("No meteors found.") 
         continue

      print("Saving final meteor...", sd_meteors, hd_meteors)
      save_final_meteor(meteor_file)

def regroup_objs(meteors):
     
   for meteor in meteors:
      print(meteor)
      groups = find_obj_groups(meteor, meteors)
      print("GROUPS:", groups)

def find_obj_groups(meteor, meteors):
   total = len(meteors)
   grouped = []
   for i in range(0, total):
      print(i)
      last_x = meteors[i]['oxs'][-1] 
      last_y = meteors[i]['oys'][-1] 
      tlx = meteors[i]['oxs'][-1] 
      tly = meteors[i]['oys'][-1] 
      dist = calc_dist((last_x,last_y),(tlx,tly))

      grouped.append(meteors[i]['obj_id'])
   return(grouped)
  
      

def final_meteor_test(mj):
   good_hd_meteors =[]
   good_sd_meteors =[]
   if len(mj['sd_meteors']) > 1:
      sd_meteors = regroup_objs(mj['sd_meteors'])
      print(len(mj['sd_meteors']))
      print("MORE THAN 1 METEOR!")
      mj['sd_meteors'] = sd_meteors
      return(0, good_sd_meteors, good_hd_meteors)

   if "hd_meteors" not in mj:
      mj['hd_meteors'] = meteors_only(mj['hd_motion_objects'])
      print("HD METEORS???:", len(mj['hd_meteors']))
      print(mj['hd_motion_objects'])
      


   for met in mj['sd_meteors']:
      print(met['ofns'], met['report']['meteor_yn'])
      obj = classify_object(met, sd=1)
      print("SD OBJ:", obj)
      if obj['meteor_yn'] == "Y":
         met['report']['classify'] = obj
         good_sd_meteors.append(met)
 

   for met in mj['hd_meteors']:
      print(met['ofns'], met['report']['meteor_yn'])
      obj = classify_object(met, sd=0)
      print("HD OBJ:", obj)
      if obj['meteor_yn'] == "Y":
         met['report']['classify'] = obj
         good_hd_meteors.append(met)

 
   print("Good SD meteors:", len(good_sd_meteors))
   print("Good HD meteors:", len(good_hd_meteors))

   if len(good_hd_meteors) > 1:
      reg = regroup_objs(good_hd_meteors) 
      print("TOO MANY GOOD HD METEORS!")

   if len(good_sd_meteors) > 1:
      reg = regroup_objs(good_hd_meteors) 
      print("TOO MANY GOOD HD METEORS!")
   if len(good_sd_meteors) == 1 or len(good_hd_meteors) == 1:
      status = 1
   else:
      status = 0

   return(status, good_sd_meteors, good_hd_meteors)

def get_trim_files(mj):
   for key in mj['motion_objects']:
      if mj['motion_objects'][key]['report']['meteor_yn'] == "Y":  
         sd_trim = mj['motion_objects'][key]['trim_clip']
   return(sd_trim,mj['hd_trim'])

def batch_save_final_meteor(day):
   if day != "0":
      dir = "/mnt/ams2/SD/proc2/" + day + "/data/*-meteor.json"
      print(dir)
      files = glob.glob(dir)
      for file in files:
         save_final_meteor(file)
   else:
      ps = load_json_file("/mnt/ams2/SD/proc2/json/proc_stats.json")
      for day in ps:
         dir = "/mnt/ams2/SD/proc2/" + day + "/data/*-meteor.json"
         print(dir)
         files = glob.glob(dir)
         for file in files:
            save_final_meteor(file)


def save_final_meteor(meteor_file):
   print("Save final meteor:", meteor_file)
   (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(meteor_file)
   day = fy + "_" + fm + "_" + fd
   proc_dir = "/mnt/ams2/SD/proc2/" + day + "/hd_save/"
   if cfe(meteor_file) == 0:
      print("This meteor file doesn't exist???", meteor_file)
      return() 

   mj = load_json_file(meteor_file)
   print(mj['motion_objects'])
   print(mj['hd_motion_objects'])
   good_sd_meteors = [] 
   good_hd_meteors = []
   for obj in mj['motion_objects']:
      if mj['motion_objects'][obj]['report']['meteor_yn'] == "Y":
         good_sd_meteors.append(mj['motion_objects'][obj])
         print("OBJ:", obj, mj['motion_objects'][obj])
   for obj in mj['hd_motion_objects']:
      if mj['hd_motion_objects'][obj]['report']['meteor_yn'] == "Y":
         good_hd_meteors.append(mj['hd_motion_objects'][obj])
   status = 1

   if len(good_sd_meteors) != 1 and len(good_hd_meteors) != 1:
      nometeor_file = meteor_file.replace("-meteor.json", "-nometeor.json")
      cmd = "mv " + meteor_file + " " + nometeor_file
      print("Some probs with this one:", meteor_file)
      print("SD/HD Meteors:", len(good_sd_meteors), len(good_hd_meteors))
      os.system(cmd)
      return()

   if status == 0:
      nometeor_file = meteor_file.replace("-meteor.json", "-nometeor.json")
      cmd = "mv " + meteor_file + " " + nometeor_file
      print(cmd)
      os.system(cmd)
      print("Final meteor test failed for: ", meteor_file) 
      return()
   else:
      mj['sd_meteors'] = good_sd_meteors
      mj['hd_meteors'] = good_hd_meteors

   if "sd_trim" not in mj:
      trim_file, hd_trim = get_trim_files(mj)
   else:
      hd_trim = mj['hd_trim']
      trim_file = mj['sd_trim']
   sd_meteors = mj['sd_meteors']
   if "hd_meteors" not in mj:
      print("BAD No hd meteors...?", hd_trim)
      exit()
   hd_meteors = mj['hd_meteors']
   real_meteors = []
   for meteor in sd_meteors:
      print(meteor)
      if meteor['report']['meteor_yn'] == 'Y' or len(meteor['report']['bad_items']) < 3:
         real_meteors.append(meteor)
   if len(real_meteors) == 0:
      for meteor in hd_meteors:
         print(meteor)
         if meteor['report']['meteor_yn'] == 'Y' or len(meteor['report']['bad_items']) < 3:
            real_meteors.append(meteor)

   

   if len(real_meteors) == 0:
      print("No real meteors here. WTF!? MV meteor.json file to -nometeor.json")
      for obj in mj['motion_objects']:
         print("METEOR?", mj['motion_objects'][obj])
      nmf = meteor_file.replace("-meteor.json", "-nometeor.json")
      cmd = "mv " + meteor_file + " " + nmf
      print(cmd)
      #os.system(cmd)
      return()

   print("SD METEOR:", real_meteors)
   print("HD METEOR:", hd_meteors)
   if len(sd_meteors) == 0 and len(hd_meteors) >= 1:
      sd_meteors = hd_meteors
      
   if len(hd_meteors) == 0 and len(sd_meteors) >= 1:
      hd_meteors = sd_meteors

   # if we made it this far we have a real meteor so lets finish it up. 
   if len(hd_meteors) > 0 : 
      old_json_data, new_json_data = make_json_files(sd_meteors[0],hd_meteors[0])
   else:
      old_json_data, new_json_data = make_json_files(sd_meteors[0],None)
   print(old_json_data)

   old_json_dir = "/mnt/ams2/meteors/" + day + "/"
   arc_dir = "/mnt/ams2/meteor_archive/" + json_conf['site']['ams_id'] + "/METEOR/" + fy + "/" + fm + "/" + fd + "/" 

   jsof = trim_file.split("/")[-1].replace(".mp4", ".json") 
   jsaf = trim_file.split("/")[-1].replace(".mp4", ".json") 

   hdf = hd_trim.split("/")[-1]
   sdf = trim_file.split("/")[-1]

   arc_hd = trim_file.split("/")[-1].replace(".mp4", "-HD.mp4") 
   arc_hd_crop = trim_file.split("/")[-1].replace(".mp4", "-HD-crop.mp4") 
   arc_sd = trim_file.split("/")[-1].replace(".mp4", "-SD.mp4") 

   mj['arc_hd'] = arc_dir + arc_hd
   mj['arc_sd'] = arc_dir + arc_sd 
   mj['archive_file'] = arc_dir + jsaf 

   print(old_json_dir + jsof)
   print(arc_dir + jsaf)
   print(arc_dir + arc_hd)
   print(arc_dir + arc_sd)

   if cfe(old_json_dir,1) == 0:
      os.makedirs(old_json_dir)
   if cfe(arc_dir,1) == 0:
      os.makedirs(arc_dir)

   os.system("cp " + hd_trim + " " + old_json_dir)
   os.system("cp " + trim_file + " " + old_json_dir)
   old_json_data['trim_clip'] = old_json_dir + sdf
   old_json_data['sd_video_file'] = old_json_dir + sdf
   old_json_data['hd_trim'] = old_json_dir + hdf

   stack_file = old_json_dir + sdf.replace(".mp4", "-stacked.png")
   hd_stack_file = old_json_dir + hdf.replace(".mp4", "-stacked.png")

   old_json_data['sd_stack'] = stack_file
   old_json_data['hd_stack'] = hd_stack_file


   mj['old_sd_trim'] = old_json_dir + sdf
   mj['old_hd_trim'] = old_json_dir + hdf

   sd_frames,sd_color_frames,sd_subframes,sum_vals,max_vals,pos_vals = load_frames_fast(trim_file, json_conf, 0, 0, [], 1,[])
   hd_frames,hd_color_frames,hd_subframes,hd_sum_vals,hd_max_vals,hd_pos_vals = load_frames_fast(hd_trim, json_conf, 0, 0, [], 1,[])
   if len(hd_frames) == 0:
      print("NO HD FRAMES!", hd_trim)
      hd_frames = sd_frames 
      hd_color_frames = sd_color_frames 
   stacked_img = stack_frames_fast(sd_color_frames, 1, None, "night", None)
   hd_stacked_img = stack_frames_fast(hd_color_frames, 1, None, "night", None)


   cv2.imwrite(stack_file, stacked_img)
   cv2.imwrite(hd_stack_file, hd_stacked_img)
   hd_tn = cv2.resize(hd_stacked_img, (PREVIEW_W,PREVIEW_H))
   sd_tn = cv2.resize(stacked_img, (PREVIEW_W,PREVIEW_H))
   cv2.imwrite(stack_file.replace(".png", "-tn.png"), stacked_img)
   cv2.imwrite(hd_stack_file.replace(".png", "-tn.png"), hd_stacked_img)
   stacked_img_obj = stacked_img
   if 'sd_prev_crop' not in mj:
      cx1,cy1,cx2,cy2,mid_x,mid_y = get_roi(None, real_meteors[0], 1, 1)
      mj['sd_prev_crop'] = [cx1,cy1,cx2,cy2,mid_x,mid_y]
      print(mj)
      print("BAD ERROR")
      exit()
      #err = open("/mnt/ams2/SD/proc2/json/errors.txt", "a")
      #err.write(trim_file + " |Missing Prev Crop|\n")
      #err.close()
      # return()

   cx1,cy1,cx2,cy2,midx,midy = mj['sd_prev_crop']
   cv2.rectangle(stacked_img_obj, (cx1, cy1), (cx2, cy2), (255,255,255), 1, cv2.LINE_AA)
   cv2.imwrite(stack_file.replace(".png", "-obj-tn.png"), stacked_img_obj)


   print(stack_file)
   print(hd_stack_file)



   save_json_file(meteor_file, mj)
   arc_data = obj_to_arc_meteor(meteor_file)
   arc_json_file = arc_data['info']['sd_vid'].replace("-SD.mp4", ".json")

   old_json_data['archive_file'] = arc_json_file 
   save_json_file(old_json_dir + jsof, old_json_data)

   save_json_file(arc_json_file, arc_data)
   hd_crop_file = hd_trim.replace(".mp4", "-crop.mp4")
   print("cp " + hd_trim + " " + arc_hd)
   print("cp " + hd_crop_file + " " + arc_hd_crop)
   print("cp " + trim_file + " " + arc_sd)
   os.system("cp " + hd_trim + " " + arc_dir + arc_hd)
   os.system("cp " + hd_crop_file + " " + arc_dir + arc_hd_crop)
   os.system("cp " + trim_file + " " + arc_dir + arc_sd)

   
   print(arc_json_file)
   os.system("/usr/bin/python3 MakeCache.py " + arc_json_file)


def meteors_only(objects):
   meteors = []
   for id in objects:
      if objects[id]['report']['meteor_yn'] == "Y":
         meteors.append(objects[id])
   return(meteors)


def get_vals_trim(video_file, obj, hdm_x=1,hdm_y=1):
   start = obj['ofns'][0]
   end = obj['ofns'][-1]
   start_fn, end_fn= buffered_start_end(start,end, 1499, 50)
   cx1,cy1,cx2,cy2,mid_x,mid_y = get_roi(None, obj, hdm_x, hdm_y)
   # override if the detection happened right at the start. 
   # merge 10 seconds of previous file with current file
   #if start_fn == 0: 
   if False:
      trim_file = merge_min_files(video_file, start_fn, end_fn, "before", cx1,cy1,cx2-cx1,cy2-cy1,0)
   else:
      trim_file, crop_file = ffmpeg_trim_crop(video_file,start_fn,end_fn,cx1,cy1,cx2-cx1,cy2-cy1, 0)



   return(trim_file, start_fn,end_fn, cx1,cy1,cx2,cy2,mid_x,mid_y)

def merge_min_files(video_file, start_fn, end_fn, type, x,y,w,h, notrim=0):
   if type == "before":
      fn = video_file.split("/")[-1]
      fdir = video_file.replace(fn, "")
      el = fn.split("_")

      # First get the previous file and clip it
      y,m,d,h,mm,s,ms,cam = el[0], el[1],el[2],el[3],el[4],el[5],el[6],el[7]
      cam = cam.replace(".mp4", "")
      t_datestr = y + "_" + m + "_" + d + "_" + h + "_" + mm + "_" + s
      t_datetime = datetime.datetime.strptime(t_datestr, "%Y_%m_%d_%H_%M_%S")
      b_datetime = t_datetime - datetime.timedelta(minutes = 1)
      print(t_datetime, b_datetime)
      new_file_wild = fdir + b_datetime.strftime('%Y_%m_%d_%H_%M_') + "*" + cam + "*.mp4"
      new_files = glob.glob(new_file_wild)
      print("WILD:", new_file_wild, new_files)
      
      if len(new_files) > 1:
         nn = [] 
         for xx in new_files:
            if "trim" not in xx:
               nn.append(xx)
         new_files = nn

      print("NEW FILES:", new_files)

      if len(new_files) == 0:
         trim_out_file = video_file.replace(".mp4", "-trim-" + str(start_fn) + ".mp4")
         cmd = "/usr/bin/ffmpeg -i " + video_file + " -vf select='between(n\," + str(0) + "\," + str(end_fn) + ")' -vsync 0 " + trim_out_file
         print(cmd)
         os.system(cmd)
         return(trim_out_file)
          
      if len(new_files) == 1:
         before_file = new_files[0]
         # cut off last 100 frames from this file:
         start = 1400
         end = 1499
         before_trim_out_file = before_file.replace(".mp4", "-trim-" + str(start) + ".mp4")
         trim_out_file = video_file.replace(".mp4", "-trim-" + str(start_fn) + ".mp4")
         cmd = "/usr/bin/ffmpeg -i " + before_file + " -vf select='between(n\," + str(start) + "\," + str(end) + ")' -vsync 0 " + before_trim_out_file
         print(cmd)
         os.system(cmd)
      # now clip the current file
         cmd = "/usr/bin/ffmpeg -i " + video_file + " -vf select='between(n\," + str(0) + "\," + str(end_fn) + ")' -vsync 0 " + trim_out_file
         print(cmd)
         os.system(cmd)
      # now merge the two clips into 1
      temp = fdir + fn
      temp = temp.replace(".mp4", ".txt")
      temp_out = fdir + fn
      temp_out = temp_out.replace(".mp4", "-temp.mp4")
      fp = open(temp, "w")
      fp.write("file '" + before_trim_out_file + "'\n")
      fp.write("file '" + trim_out_file + "'\n")
      fp.close()
      cmd = "/usr/bin/ffmpeg -f concat -safe 0 -i " +temp + " -c copy " + temp_out
      os.system(cmd) 

      # NOT NEEDED! now crop the newly merged trim
      #crop_out_file = temp_out.replace(".mp4", "-crop.mp4")

      #crop = "crop=" + str(w) + ":" + str(h) + ":" + str(x) + ":" + str(y)

      #cmd = "/usr/bin/ffmpeg -i " + trim_out_file + " -filter:v \"" + crop + "\" " + crop_out_file
      #os.system(cmd)
      #print(cmd)

      os.system("rm " + before_trim_out_file)
      os.system("rm " + trim_out_file)
      os.system("mv " + temp_out + " " + before_trim_out_file)

      return(before_trim_out_file)


def extract_frames(video_file,start,end,outfile):
   fn = video_file.split("/")[-1] + "-trim" + str(start)
   temp_dir = "/home/ams/tmpvids/" + fn + "/" 
   if cfe(temp_dir, 1) == 0:
      os.makedirs(temp_dir)
   cmd = "ffmpeg -i " + video_file + " -vf select='between(n\," + str(start) + "\," + str(end) + ")' -vsync 0 " + outfile + " > /dev/null"
   print(cmd)
   os.system(cmd)

def complete_vals_detect(meteor_file):
   print("Complete meteor.")
   # Now all that is left...
   # determine frame times
   # apply calib
   # format old and new json
   # copy files to arc dir and old json dir

def process_events(video_file,events):
   """ 
      Take in a minute file and the list of events (potential meteors). 
      Find the corresponding 'best' HD trim clip, or minute file
      Make trim clip and trim_crop clip of the original SD
      Make trim clip and trim_crop clip of the original HD
      Return array containing the filenames for all 4 clips 

   """
   hds = find_hd(video_file)

   event_files = []
   new_events = []
   for ev in events:
      print("EVENT:", ev )
      xs = []
      ys = []
      fn = ev['frames'][0]
      for x,y in ev['pos_vals']:
         xs.append(int(x*hdm_x))
         ys.append(int(y*hdm_y))
         fn += 1
      min_x = min(xs)
      max_x = max(xs)
      max_y = max(ys)
      min_y = min(ys)
      print(min_x,max_x,min_y,max_y)
      cx1,cy1,cx2,cy2,mid_x,mid_y = find_crop_size(min_x, min_y, max_x,max_y)
      print("CX:", cx1,cy1,cx2,cy2)   
      print(xs)
      print(ys)
      print(hdm_x)
      print(hdm_y)
      if len(hds) > 0:
         # We have an HD File.
         hd_vid = hds[0][0]
         if "trim" in hd_vid:
            print("trim in hd_vid")
            #play_clip(hd_vid, cx1,cy1,cx2,cy2)
            #hd_trim,hd_crop = ffmpeg_trim_crop(hd_vid,0,0,cx1,cy1,cx2-cx1,cy2-cy1,1)
         else:
            print("Dealing with 1 minute HD File.")
            #hd_trim,hd_crop = ffmpeg_trim_crop(hd_vid,ev['frames'][0],ev['frames'][-1],cx1,cy1,cx2-cx1,cy2-cy1,0)
      else:
         hd_trim = None
         hd_crop = None

      # trim and crop the SD file
      sd_cx1,sd_cx2,sd_cy1,sd_cy2 = int(cx1/hdm_x), int(cx2/hdm_x), int(cy1/hdm_y), int(cy2/hdm_y)
      buf_size = 10
      t_start, t_end = buffered_start_end(ev['frames'][0],ev['frames'][-1], ev['frames'][-1]-ev['frames'][0], buf_size)
      #sd_trim, sd_crop = ffmpeg_trim_crop(video_file,ev['frames'][0],ev['frames'][-1],sd_cx1,sd_cy1,sd_cx2-sd_cx1,sd_cy2-sd_cy1)
      #ev['event_files'] = [sd_trim,sd_crop,hd_trim,hd_crop,[cx1,cy1,cx2,cy2]]
      ev['event_files'] = [0,0,0,0,[0,0,0,0]]
      new_events.append(ev)
   return(new_events)




def plot_vals(vals_file):
   data = load_json_file(vals_file)
   
   import matplotlib
   matplotlib.use('Agg')
   import matplotlib.pyplot as plt
   fig = plt.figure()
   data_x = []
   data_y = []
   for i in range(0,len(data['max_vals'])):
      x,y = data['pos_vals'][i]
      max_val = data['max_vals'][i]
      if max_val > 10:
         data_x.append(x)
         data_y.append(y)
         print(i, x,y, max_val)

   plt.scatter(data_x, data_y)
   ax = plt.gca()
   ax.invert_yaxis()

   curve_file = "/var/www/html/plot.png"
   fig.savefig(curve_file, dpi=100)
   plt.close()


def basic_scan(video_file):

   vals = {}   
   start_time = time.time() 
   sd_frames,sd_color_frames,sd_subframes,sum_vals,max_vals,pos_vals = load_frames_fast(video_file, json_conf, 0, 0, [], 1,[])
   vals['sum_vals'] = sum_vals
   vals['max_vals'] = max_vals
   vals['pos_vals'] = pos_vals
   vals_file = video_file.replace(".mp4", "-vals.json")
   save_json_file(vals_file, vals, True)
   elapsed_time = time.time() - start_time
   print("LOAD & SCAN TIME:", elapsed_time)
   stacked_image = stack_frames_fast(sd_color_frames, 1, [PREVIEW_W, PREVIEW_H])

   elapsed_time = time.time() - start_time
   stack_file = video_file.replace(".mp4", "-stacked.png") 
   cv2.imwrite(stack_file, stacked_image)
   print(stack_file)
   print(vals_file)
   print("SCAN AND STACK TIME:", elapsed_time)



def injest(video_file):
   """ Function that will manually injest a daytime or non-detected meteor into the system
   """

   # first check to see if we are dealing with a HD source video. 
   # if we are, down-sample it so we have an SD video to work with (will be 10x faster than detecting in HD)

   cmd = "/usr/bin/ffprobe " + video_file + "  > /mnt/ams2/tmp/info.txt 2>&1"
   os.system(cmd) 

   # open output from ffprobe to find HD status
   fp = open("/mnt/ams2/tmp/info.txt", "r")
   probe_out = ""
   for line in fp:
      probe_out += line
   
   if "1920" in probe_out:
      print("We have an HD file for input. Downscale it first!")
      source_type = "HD"
      sd_video_file = video_file.replace(".mp4", "-SD.mp4")
   else: 
      source_type = "SD"
      sd_video_file = video_file
  
   # create SD downsample if it does not already exist 
   if cfe(sd_video_file) == 0:
      cmd = "/usr/bin/ffmpeg -i " + video_file + " -vf scale=640:360 " + sd_video_file
      os.system(cmd)

   user_station = input("Enter the AMS station number associated with this clip AMSX  \n")
   if user_station is not None:
      remote_conf_file = "/mnt/archive.allsky.tv/" + user_station + "/CAL/as6.json"
      json_conf = load_json_file(remote_conf_file)


   # load frames from SD video file
   sd_frames,sd_color_frames,sd_subframes,sum_vals,max_vals,pos_vals = load_frames_fast(sd_video_file, json_conf, 0, 0, [], 1,[])
   # check for events and possible meteors in frames
   events, pos_meteors = fast_check_events(sum_vals, max_vals, sd_subframes)

   # print the events in the clips
   ec = 0
   for event in events:
      print("EVENT:", ec, event)
      ec += 1

   # print the objects found in the clip (meteors will be classed and have meteor_yn=1)
   for meteor in pos_meteors:
      print("MET:", meteor)

   selected_event = int(input("Please enter the event number you think is the meteor\n"))
   #key = int(selected_event)
   meteor_event = events[selected_event]
   print("You selected:", meteor_event)
   user_trim_clip = input("Trim Clip (Y or N) \n")


   if user_trim_clip == "Y":
      # base initial buffer size off of total event length 
      buf_size = meteor_event[-1] - meteor_event[0]
      # trim buff size accordingly
      if buf_size < 10:
         buf_size = 10
      if buf_size > 50:
         buf_size = 50 
      buf_size = 100
      t_start, t_end = buffered_start_end(meteor_event[0],meteor_event[-1], len(sd_frames), buf_size)


      trim_clip, trim_start, trim_end = make_trim_clip(video_file, t_start, t_end)
      print("TRIM CLIP MADE:", trim_clip)
      print("Detecting meteors in trim clip:", trim_clip)
      motion_objects,meteor_frames = detect_meteor_in_clip(trim_clip , None, 0)

      meteor = None
      meteors = []
      for mo in motion_objects:
         if motion_objects[mo]['report']['meteor_yn'] == 'Y':
            print(mo, motion_objects[mo]) 
            meteors.append(motion_objects[mo])


      if meteor is None or len(meteors) > 1:
         print("Auto meteor detect failed or found more than 1 possible meteor. Select the best object.")
         for mo in motion_objects:
            print(mo, motion_objects[mo]['ofns'])
         selected_obj = int(input("Please enter the obj number you think is the meteor\n"))
         print("You selected:", selected_obj, motion_objects[selected_obj]['ofns'])
         meteor = motion_objects[selected_obj]
 

      ma_sd_file = trim_clip.replace(".mp4", "-SD.mp4")
      ma_hd_file = trim_clip.replace(".mp4", "-HD.mp4")
      ma_json_file = trim_clip.replace(".mp4", ".json")

      meteor['trim_clip'] = trim_clip 
      meteor['hd_trim'] = trim_clip 
      meteor['ma_sd_file'] = ma_sd_file 
      meteor['ma_hd_file'] = ma_hd_file


      calib,cal_params = apply_calib(meteor, meteor_frames, user_station)
      calib = format_calib(ma_sd_file, cal_params, ma_sd_file)
      meteor['calib'] = calib
      meteor['cal_params'] = cal_params

      # setup times in frames
      # get start of the 1 minute clip
      (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(trim_clip)
      day = fy + "_" + fm + "_" + fd
      # convert starting clip frame number to seconds
      extra_sec = t_start / 25
      # add trim num seconds to the min start time to get the trim clip start time
      start_trim_frame_time = f_datetime + datetime.timedelta(0,extra_sec)

      # loop over frames and get frame time for each frame
      ftimes = []
      for fn in meteor['ofns']:
         extra_sec = fn / 25
         frame_time = start_trim_frame_time + datetime.timedelta(0,extra_sec)
         ftimes.append(frame_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3])
      # save ftimes in meteor json
      meteor['ftimes'] = ftimes

      new_json = save_new_style_meteor_json(meteor, ma_json_file)

      arc_dir = "/mnt/ams2/meteor_archive/" + user_station + "/METEOR/" + fy + "/" + fm + "/" + day + "/"
      was_arc_dir = "/mnt/archive.allsky.tv/" + user_station + "/METEOR/" + fy + "/" + fm + "/" + day + "/"

      old_json_fn = ma_json_file.split("/")[-1]
      old_sd_fn = old_json_fn.replace(".json", ".mp4") 
      old_hd_fn = old_json_fn.replace(".json", "-HD-meteor.mp4") 

      old_meteor_dir = "/mnt/ams2/meteors/" + day + "/" 
      old_json_file = "/mnt/ams2/meteors/" + day + "/" + old_json_fn
      old_sd_vid = "/mnt/ams2/meteors/" + day + "/" + old_sd_fn
      old_hd_vid = "/mnt/ams2/meteors/" + day + "/" + old_hd_fn

      meteor['hd_trim'] = old_hd_vid
      meteor['trim_clip'] = old_sd_vid

      source_file = trim_clip

      # copy the source media file to the old and new meteor json locations
      # rescale the source file to SD or HD depending on what it was to begin with 
      if source_type == "HD":
         hd_source = source_file
         sd_source = ma_sd_file 
         if cfe(ma_sd_file) == 0:
            cmd = "/usr/bin/ffmpeg -i " + hd_source + " -vf scale=640:360 " + ma_sd_file 
            os.system(cmd)
      else:
         sd_source = source_file
         hd_source = ma_hd_file 
         if cfe(ma_hd_file) == 0:
            cmd = "/usr/bin/ffmpeg -i " + hd_source + " -vf scale=640:360 " + ma_hd_file 
            os.system(cmd)

      print("SOURCE JSON :", ma_json_file) 
      print("SOURCE HD :", hd_source) 
      print("SOURCE SD :", sd_source) 
      print("OLD JSON:", old_json_file)
      print("OLD SD VID:", old_sd_vid)
      print("OLD HD VID:", old_hd_vid)

      # save old json_file
      if cfe(old_meteor_dir, 1) == 0:
         os.makedirs(old_meteor_dir) 
      save_json_file(old_json_file, meteor) 

      # copy and media to old dir
      os.system("cp " + sd_source + " " + old_sd_vid) 
      os.system("cp " + hd_source + " " + old_hd_vid) 

      # arc json and media to new dir
      if cfe(arc_dir, 1) == 0:
         os.makedirs(arc_dir)

      arc_json_file = arc_dir + ma_json_file.split("/")[-1]
      arc_sd_file = arc_dir + ma_sd_file.split("/")[-1]
      arc_hd_file = arc_dir + ma_hd_file.split("/")[-1]

      # copy media to old dir
      os.system("cp " + sd_source + " " + old_sd_vid) 
      os.system("cp " + hd_source + " " + old_hd_vid) 

      # copy json & media to new dir
      if cfe(arc_dir, 1) == 0:
         os.makedirs(arc_dir)
      os.system("cp " + ma_json_file + " " + arc_json_file) 
      os.system("cp " + sd_source + " " + arc_sd_file) 
      os.system("cp " + hd_source + " " + arc_hd_file) 

      print("ARC:", arc_json_file)
      print("ARC SD VID:", arc_sd_file)
      print("ARC HD VID:", arc_hd_file)


      # copy json & media to wasabi dir
      was_dir = arc_dir.replace("ams2/meteor_archive", "archive.allsky.tv")
      if cfe(was_dir, 1) == 0:
         os.makedirs(was_dir)
      os.system("cp " + ma_json_file + " " + arc_json_file.replace("ams2/meteor_archive", "archive.allsky.tv")) 
      os.system("cp " + sd_source + " " + arc_sd_file.replace("ams2/meteor_archive", "archive.allsky.tv")) 
      os.system("cp " + hd_source + " " + arc_hd_file.replace("ams2/meteor_archive", "archive.allsky.tv")) 

      new_json['info']['hd_vid'] = arc_hd_file
      new_json['info']['sd_vid'] = arc_sd_file
      new_json['info']['org_sd_vid'] = old_sd_vid
      new_json['info']['org_hd_vid'] = old_hd_vid
      save_json_file(ma_json_file, new_json)
      save_json_file(arc_json_file, new_json)
      


cmd = sys.argv[1]
arg_str = ""
for arg in sys.argv:
   arg_str += arg + " "

logger("flex-detect.py", "main-" + cmd, "Flex detect running with args: " + arg_str)


if len(sys.argv) > 2:
   video_file = sys.argv[2]

if cmd == "injest":
   injest(video_file)
if cmd == "fd" or cmd == "flex_detect":
   flex_detect(video_file)

if cmd == "qs" or cmd == "quick_scan":
   quick_scan(video_file)

if cmd == "qb" or cmd == "batch":
   batch_quick()

if cmd == "som" or cmd == "scan_old_meteor_dir":
   scan_old_meteor_dir(video_file)
if cmd == "sq" or cmd == "scan_queue":
   scan_queue(video_file)
if cmd == "cm" or cmd == "confirm_meteor":
   confirm_meteor(video_file)
if cmd == "bc" or cmd == "batch_confirm":
   batch_confirm()
if cmd == "mfs" or cmd == "move_files":
   batch_move()
if cmd == "rp" or cmd == "refine_points":
   refine_points(video_file)
if cmd == "snm" or cmd == "stack_non_meteors":
   stack_non_meteors()
if cmd == "fmhd" or cmd == "fix_missing_hd":
   fix_missing_hd(video_file)
if cmd == "rm" or cmd == "review_meteor":
   review_meteor(video_file)
if cmd == "sp" or cmd == "spectra":
   spectra(video_file)
if cmd == "rr" or cmd == "rerun":
   rerun(video_file)
if cmd == "remaster":
   remaster_arc(video_file)
if cmd == "wi":
   write_archive_index(sys.argv[2], sys.argv[3])
if cmd == "debug" :
   debug(video_file)
if cmd == "ca" :
   if len(sys.argv) > 3:
      check_archive(video_file, 1)
   else:
      check_archive(video_file, 0)
if cmd == "ram" :
   refit_arc_meteor(video_file)
if cmd == "faf" :
   fit_arc_file(video_file)

if cmd == "bfaf" :
   batch_fit_arc_file(video_file)
if cmd == "debug2" :
   debug2(video_file)
if cmd == "coc" :
   convert_old_cal_files()
if cmd == "ui" :
   update_intensity(video_file)
if cmd == "batch_archive_msm" or cmd == "bams" :
   batch_archive_msm(video_file)
if cmd == "eval_points" or cmd == "ep" :
   eval_points(video_file)
if cmd == "ra" or cmd == "run_archive" :
   run_archive()
if cmd == "fix_arc_points" or cmd == "fap" :
   fix_arc_points(video_file)
if cmd == "fix_arc_all" or cmd == "faa" :
   eval_points(video_file)
   fix_arc_points(video_file)
   fit_arc_file(video_file)
   os.system("cd /home/ams/amscams/pythonv2; /usr/bin/python3 Apply_calib.py " + video_file)
   cache_file = video_file.replace("meteor_archive", "CACHE")
   el = cache_file.split("/")[-1]
   cache_dir = cache_file.replace(el, "")
   cmd = "rm " + cache_dir + "/THUMBS/*"
   print(cmd)
   #os.system(cmd)
   os.system("cd /home/ams/amscams/pythonv2; /usr/bin/python3 MakeCache.py " + video_file)
   os.system("cd /home/ams/amscams/pythonv2; /usr/bin/python3 Create_Archive_Index.py 2019" )

if cmd == "bfa" or cmd == "batch_fit_all_arc_files" :
   batch_fit_all_arc_files()
if cmd == "qqs" :
   quickest_scan(sys.argv[2])
if cmd == "bqqs" :
   print("BATCH QUICK!")
   batch_quickest_scan(sys.argv[2])
if cmd == "mpi" :
   make_preview_image(sys.argv[2])
if cmd == "bmpi" :
    
   batch_make_preview_image(sys.argv[2])
if cmd == "fm" :
   finish_meteor(sys.argv[2])
if cmd == "basic" :
   basic_scan(sys.argv[2])
if cmd == "plot_vals" :
   plot_vals(sys.argv[2])
if cmd == "detect_in_vals" or cmd == 'dv':
   file = sys.argv[2].split("/")[-1]
   day = file[0:10]
   cam_size_info = get_cam_sizes(day)
   detect_in_vals(sys.argv[2], cam_size_info)
if cmd == "batch_vals" or cmd == 'bv':
   ### this will run detects on a specific day
   if len(sys.argv) < 3:
      now = datetime.datetime.now()
      today = now.strftime("%Y_%m_%d")
      yest = datetime.datetime.strftime(datetime.datetime.now() - datetime.timedelta(1), '%Y_%m_%d')
      batch_vals(today)
      print(yest)
      batch_vals(yest)
   else:
      batch_vals(sys.argv[2])

if cmd == "verify_tms" or cmd == 'vtms':
   verify_toomany_detects(sys.argv[2])
if cmd == "verify_tm" or cmd == 'vtm':
   verify_toomany(sys.argv[2])

if cmd == "verify_meteor" or cmd == 'vm':
   verify_meteor(sys.argv[2])
if cmd == "verify_meteors" or cmd == 'vms':
   if len(sys.argv) == 3:
      verify_meteors(sys.argv[2])
   else:
      print("VMS")
      verify_meteors()

if cmd == "bsfm" or cmd == 'batch_save_final_meteor':
   print("bsfm")

   batch_save_final_meteor(sys.argv[2])

if cmd == "sfm" or cmd == 'save_final_meteor':
   save_final_meteor(sys.argv[2])
if cmd == "oam" or cmd == 'obj_to_arc_meteor':
   obj_to_arc_meteor(sys.argv[2])
if cmd == "am" or cmd == 'archive_meteor':
   archive_meteor(sys.argv[2])
if cmd == "fc" or cmd == 'frame_composite':
   frame_composite(sys.argv[2])
if cmd == "fam" or cmd == 'fix_arc_meteor':
   fix_arc_meteor(sys.argv[2])
if cmd == "man" :
   man_detect(sys.argv[2]) 
