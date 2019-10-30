#!/usr/bin/python3


from lib.Video_Tools_cv_pos import *
from PIL import ImageFont, ImageDraw, Image, ImageChops
from lib.VIDEO_VARS import *
from lib.UtilLib import calc_dist,find_angle, best_fit_slope_and_intercept
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
from lib.Video_Tools_cv import remaster
from lib.VideoLib import get_masks, find_hd_file_new, load_video_frames, sync_hd_frames, make_movie_from_frames, add_radiant

from lib.UtilLib import check_running, angularSeparation, bound_cnt
from lib.CalibLib import radec_to_azel, clean_star_bg, get_catalog_stars, find_close_stars, XYtoRADec, HMS2deg, AzEltoRADec, get_active_cal_file

from lib.ImageLib import mask_frame , stack_frames, preload_image_acc
from lib.ReducerLib import setup_metframes, detect_meteor , make_crop_images, perfect, detect_bp, best_fit_slope_and_intercept, id_object, metframes_to_mfd

from lib.MeteorTests import meteor_test_cm_gaps
from lib.Video_Tools_cv import remaster


import sys
from lib.CalibLib import distort_xy_new, find_image_stars, distort_xy_new, XYtoRADec, radec_to_azel, get_catalog_stars,AzEltoRADec , HMS2deg, get_active_cal_file, RAdeg2HMS, clean_star_bg
from lib.UtilLib import calc_dist, find_angle, bound_cnt, cnt_max_px

from lib.UtilLib import angularSeparation, convert_filename_to_date_cam, better_parse_file_date
from lib.FileIO import load_json_file, save_json_file, cfe
from lib.UtilLib import calc_dist,find_angle
import lib.brightstardata as bsd
from lib.DetectLib import eval_cnt, check_for_motion2

ARCHIVE_DIR = "/mnt/NAS/meteor_archive/"

def remaster(frames, marked_video_file, station,meteor_object): 
   new_frames = []
   radiant = False
   fx = meteor_object['oxs'][0]
   fy = meteor_object['oys'][0]
   cx1,cy1,cx2,cy2= bound_cnt(fx,fy,frames[0].shape[1],frames[0].shape[0], 100)
   hdm_x = 1920 / 1280 
   hdm_y = 1080 / 720
   cx1,cy1,cx2,cy2= int(cx1/hdm_x),int(cy1/hdm_y),int(cx2/hdm_x),int(cy2/hdm_y) 
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
   extra_text = "Sirko Molau - Ketzur, Germany"
   extra_text_pos = "bl"
   date_time_pos = "br"
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
      #hd_img = add_overlay_cv(hd_img, ams_logo, ams_logo_pos)

      # Add Eventual Extra Logo
      if(extra_logo is not False and extra_logo is not None):
         hd_img = add_overlay_cv(hd_img,extra_logo,extra_logo_pos)

      # Add Date & Time
      frame_time_str = station_id + ' - ' + frame_time_str + ' UT'
      #hd_img,xx,yy,ww,hh = add_text_to_pos(hd_img,frame_time_str,date_time_pos,2) #extra_text_pos => bl?

      # Add Extra_info
      #if(extra_text is not False):
      #   hd_img,xx,yy,ww,hh = add_text_to_pos(hd_img,extra_text,extra_text_pos,2,True)  #extra_text_pos => br?

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
         cv2.circle(thresh_img,(mx,my), 1, (0,0,255), 1)
         #cv2.imshow('cnt2', cnt_img)
         #cv2.imshow('cnt', thresh_img)
         #cv2.waitKey(10)
         return(int(blob_x), int(blob_y),max_val,int(blob_w),int(blob_h))
      else:
         desc = str(fn) + "NF!"
         cv2.putText(thresh_img, desc,  (3,10), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
         #cv2.imshow('cnt2', cnt_img)
         #cv2.imshow('cnt', thresh_img)
         #cv2.waitKey(10)
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
def add_overlay_cv(background, overlay, position):
    background_width,background_height  = background.shape[1], background.shape[0]
    # Get overlay position - see lib.Video_Tools_cv_lib
    #x,y = get_overlay_position_cv(background,overlay,position)
    x = 5
    y = 5
    return add_overlay_x_y_cv(background, overlay, x, y)


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
   json_conf = load_json_file(ARCHIVE_DIR + station_id + "/CONF/as6.json")
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

def find_matching_cal_files(station_id, cam_id, capture_date):
   matches = []
   cal_dir = ARCHIVE_DIR + station_id + "/CAL/*.json"
   all_files = glob.glob(cal_dir)
   for file in all_files:
      if cam_id in file :
         el = file.split("/")
         fn = el[-1]
         matches.append(file)

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

def make_gray_frames(frames):
   gray_frames = []
   for frame in frames:
      gray_cnt = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
      gray_frames.append(gray_cnt)
   return(gray_frames)

def make_small_gray_frames(frames):
   gray_frames = []
   for frame in frames:
      gray_cnt = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
      gray_cnt = cv2.resize(gray_cnt, (360,200))
      gray_frames.append(gray_cnt)
   return(gray_frames)

def bp_detect(frames, gray_frames, video_file):
   objects = []
   mean_max = []
   subframes = []
   mean_max_avg = None
   frame_data = {}
   fn = 0
   last_frame = None
   for frame in gray_frames:
      if last_frame is None:
         last_frame = frame
      extra_meteor_sec = int(fn) / 25
      #meteor_frame_time = clip_start_time + datetime.timedelta(0,extra_meteor_sec)
      #meteor_frame_time_str = meteor_frame_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

      show_frame = frame
      crop_img = np.zeros((200,200),dtype=np.uint8)
      #orig_frames.append(frame.copy())
      #frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
      #frame = mask_frame(frame, mask_points, masks,mask_size)
      #show_frame = frame.copy()

      frame_data[fn] = {}
      frame_data[fn]['fn'] = fn
      #frame_data[fn]['ft'] = meteor_frame_time_str
      #frame_data[fn]['frame_time'] = meteor_frame_time_str
      #frame_data[fn]['frame_time_str'] = meteor_frame_time_str
      blur_frame = cv2.GaussianBlur(frame, (7, 7), 0)
      blur_last = cv2.GaussianBlur(last_frame, (7, 7), 0)

      subframe = cv2.subtract(frame,last_frame)
      subframes.append(subframe)



      avg_val = np.mean(frame)
      sum_val = np.sum(subframe)
      min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(subframe)

      frame_data[fn]['avg_val'] = float(avg_val)
      frame_data[fn]['min_val'] = float(min_val)
      frame_data[fn]['max_val'] = float(max_val)
      frame_data[fn]['sum_val'] = float(sum_val)
      frame_data[fn]['mx'] = int(mx)
      frame_data[fn]['my'] = int(my)
      last_frame = frame
      fn = fn + 1

   return(frame_data, subframes) 

def detect_motion_in_frames(subframes, video_file):
   cnt_frames = {} 
   image_acc = np.empty(np.shape(subframes[0]))
  
   if len(image_acc.shape) > 2:
      image_acc = cv2.cvtColor(image_acc, cv2.COLOR_BGR2GRAY)

   fn = 0
   for frame in subframes:
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
      thresh = 25
      _, threshold = cv2.threshold(image_diff.copy(), thresh, 255, cv2.THRESH_BINARY)

      thresh_obj = cv2.dilate(threshold.copy(), None , iterations=4)
      thresh_obj = cv2.convertScaleAbs(thresh_obj)
      cv2.imshow('p', thresh_obj)
      cv2.waitKey(10)
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
  
def find_cnt_objects(cnt_frame_data):
   objects = {}
   for fn in cnt_frame_data: 
      cnt_xs = cnt_frame_data[fn]['xs']
      cnt_ys = cnt_frame_data[fn]['ys']
      cnt_ws = cnt_frame_data[fn]['ws']
      cnt_hs = cnt_frame_data[fn]['hs']
      for i in  range(0, len(cnt_xs)):
         object, objects = find_object(objects, fn,cnt_xs[i], cnt_ys[i], cnt_ws[i], cnt_hs[i])
   return(objects)


def find_object(objects, fn, cnt_x, cnt_y, cnt_w, cnt_h):
   obj_dist_thresh = 50
   center_x = cnt_x + int(cnt_w / 2)
   center_y = cnt_y + int(cnt_h / 2)

   found = 0
   max_obj = 0
   for obj in objects:
      if 'oxs' in objects[obj]:
         oxs = objects[obj]['oxs']
         oys = objects[obj]['oys']
         for oi in range(0, len(oxs)):
            dist = calc_dist((center_x, center_y), (oxs[oi], oys[oi]))
            if dist < obj_dist_thresh:
               found = 1
               found_obj = obj
      if obj > max_obj:
         max_obj = obj
   if found == 0:
      obj_id = max_obj + 1
      objects[obj_id] = {}
      objects[obj_id]['ofns'] = []
      objects[obj_id]['oxs'] = []
      objects[obj_id]['oys'] = []
      objects[obj_id]['ofns'].append(fn)
      objects[obj_id]['oxs'].append(center_x)
      objects[obj_id]['oys'].append(center_y)
      found_obj = obj_id
   if found == 1:
      objects[found_obj]['ofns'].append(fn)
      objects[found_obj]['oxs'].append(center_x)
      objects[found_obj]['oys'].append(center_y)

   return(found_obj, objects)

def meteor_dir(fx,fy,lx,ly):
   # positive x means right to left (leading edge = lowest x value)
   # negative x means left to right (leading edge = greatest x value)
   # positive y means down to up (leading edge = greatest y value)
   # negative y means left to right (leading edge = lowest y value)
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
      return(0)

   if gap_to_cm_ratio < .2 and gap_to_elp_ratio < .2:
      return(1)
   else:
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
      #cv2.putText(show_frame, desc,  (3,10), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
      cv2.imshow('Pepe', show_frame)
      cv2.waitKey(10)
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
            xsegs.append(abs(ax-last_ax))
            ysegs.append(abs(ay-last_ay))
         last_ax = ax
         last_ay = ay

   print(xsegs)
   print(ysegs)
   avg_x_seg = int(np.median(xsegs))
   avg_y_seg = int(np.median(ysegs))
   print("FIRST/LAST:", first_fn, last_fn)
   print("AVG SEGS:", avg_x_seg, avg_y_seg)

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
   #show = 1
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
         cv2.imshow('pepe', subframe)
         cv2.waitKey(10)
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

         cv2.imshow('pepe', show_img)
         cv2.waitKey(70) 
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

      if show == 1:
         cv2.imshow('pepe', img)
         cv2.moveWindow('pepe',25,25)
         cv2.waitKey(1)
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
   station_id = get_station_id(video_file)
   hd_datetime, hd_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(video_file)
   possible_cal_files = get_cal_params(video_file, station_id)
   json_conf = load_json_conf(station_id)
   frames = load_video_frames(video_file, json_conf, 0, 0, [], 0)
   gray_frames = make_gray_frames(frames)
   detect_info = {}

   json_file = video_file.replace(".mp4", ".json")
   manual_file = json_file.replace(".json", "-man.json")
   if cfe(manual_file) == 1:
      manual_fixes = load_json_file(manual_file)
   else:
      manual_fixes = {}
      manual_fixes['fixes'] = []

   if cfe(json_file) == 0:
      bp_frame_data, subframes = bp_detect(frames,gray_frames,video_file)
      cnt_frame_data = detect_motion_in_frames(gray_frames, video_file)
      detect_info['bp_frame_data'] = bp_frame_data
      detect_info['cnt_frame_data'] = cnt_frame_data
      save_json_file(json_file, detect_info)
   else:
      detect_info = load_json_file(json_file)
      bp_frame_data = detect_info['bp_frame_data']
      cnt_frame_data = detect_info['cnt_frame_data']


   objects = find_cnt_objects(cnt_frame_data)

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

def quick_scan(video_file):
   stack_file = video_file.replace(".mp4", "-stacked.png")
   if cfe(stack_file) == 1:
      print("Already done this.")
      return()
   cm = 0
   no_mo = 0
   event = []
   bright_events = []
   station_id = get_station_id(video_file)
   valid_events = []
   print("STATION:", station_id)
   hd_datetime, hd_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(video_file)

   json_conf = load_json_conf(station_id)
   frames = load_frames_fast(video_file, json_conf, 0, 0, [], 0,[360,200])
   #gray_frames = make_small_gray_frames(frames)
   stacked_frame = stack_frames_fast(frames)

   cv2.imwrite(stack_file, stacked_frame) 
   bp_frame_data, subframes = bp_detect(frames,frames,video_file)
   bin_days = []
   bin_events = []
   bin_avgs = []
   bin_sums = []
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
         #print("DETECT:", running_sum, fn, bp_frame_data[fn]['max_val'], bp_frame_data[fn]['avg_val'], bp_frame_data[fn]['sum_val'])
         #cv2.imshow('pepe', frames[fn])
         #cv2.waitKey(80)
         event.append(fn)
         cm = cm + 1
         no_mo = 0
      else:
         #print("NONE:", running_sum, fn, bp_frame_data[fn]['max_val'], bp_frame_data[fn]['avg_val'], bp_frame_data[fn]['sum_val'])
         no_mo = no_mo + 1
      if cm >= 3 and no_mo >= 5:
         bright_events.append(event)
         cm = 0
         event = []
      if no_mo >= 5:
         cm = 0
         event = []

     

   import matplotlib
   matplotlib.use('Agg')
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
            thresh_val = 10
            _ , thresh_img = cv2.threshold(subframes[fn].copy(), thresh_val, 255, cv2.THRESH_BINARY)
            thresh_sub_sum = np.sum(thresh_img)
            if thresh_sub_sum > 0:
               #print("THRESH SUM:", fn, thresh_sub_sum)
               ts_stat.append(fn)
         if len(ts_stat) < 3:
            print("Not a valid event, just noise.")
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
            valid_events.append(event)
   else:
      print("No bright events found.")

   if len(valid_events) > 0:
      data_file = video_file.replace(".mp4", "-events.json")
      event_json = {}
      event_json['events'] = valid_events

      for event in valid_events:
         for fn in range(event[0], event[-1]):
            cv2.imshow('pepe', frames[fn])
            cv2.waitKey(10)



      save_json_file(data_file, event_json)


def stack_frames_fast(frames):
   stacked_image = None
   fc = 0
   for frame in frames:
      if fc % 2 == 0:
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
   (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(trim_file)
   cap = cv2.VideoCapture(trim_file)
   masks = None

   frames = []
   frame_count = 0
   go = 1
   while go == 1:
      _ , frame = cap.read()
      if frame is None:
         if frame_count <= 5 :
            cap.release()
            return(frames)
         else:
            go = 0
      else:
         if limit != 0 and frame_count > limit:
            cap.release()
            return(frames)
         if len(frame.shape) == 3 and color == 0:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

         if mask == 1 and frame is not None:
            if frame.shape[0] == 1080:
               hd = 1
            else:
               hd = 0
            masks = get_masks(cam, json_conf,hd)
            print("GET MASKS HD:", hd, masks)
            frame = mask_frame(frame, [], masks, 5)

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
            #print("MIKE:", x1,y2,x2,y2)
            crop_frame = frame[y1:y2,x1:x2]
            frame = crop_frame
         if len(resize) == 2:
            frame = cv2.resize(frame, (resize[0],resize[1]))
       

         frames.append(frame)
         frame_count = frame_count + 1
   cap.release()
   if len(crop) == 4:
      return(frames,x1,y1)
   else:
      return(frames)



cmd = sys.argv[1]
video_file = sys.argv[2]

if cmd == "fd" or cmd == "flex_detect":
   flex_detect(video_file)

if cmd == "qs" or cmd == "quick_scan":
   quick_scan(video_file)
