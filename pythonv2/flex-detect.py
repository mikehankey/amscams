#!/usr/bin/python3

from sklearn.cluster import DBSCAN

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
import ephem
from lib.Video_Tools_cv import remaster
from lib.VideoLib import get_masks, find_hd_file_new, load_video_frames, sync_hd_frames, make_movie_from_frames, add_radiant

from lib.UtilLib import check_running, angularSeparation
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

json_conf = load_json_file("../conf/as6.json")


ARCHIVE_DIR = "/mnt/NAS/meteor_archive/"

def batch_move():
   files = glob.glob("/mnt/ams2/CAMS/queue/*.mp4")
   for video_file in files:
      if "trim" in video_file:
         trim = 1
      else:
         stack_file = video_file.replace(".mp4", "-stacked.png")
         meteor_file = video_file.replace(".mp4", "-meteor.json")
         fail_file = video_file.replace(".mp4", "-fail.json")
      if cfe(stack_file) == 1:
         # processing is done for this file
         video_fn = video_file.split("/")[-1]
         stack_fn = stack_file.split("/")[-1]
         meteor_fn = meteor_file.split("/")[-1]
         fail_fn = meteor_file.split("/")[-1]
         (hd_datetime, cam, sd_date, sd_y, sd_m, sd_d, sd_h, sd_M, sd_s) = convert_filename_to_date_cam(video_file)
         proc_dir = "/mnt/ams2/SD/proc2/" + sd_y + "_" + sd_m + "_" + sd_d + "/" 
         if cfe(proc_dir, 1) == 0:
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
   print("SUN AZ:", sun_az)
   print("SUN ALT:", sun_alt)
   return(int(sun_alt))


def objects_to_clips(meteor_objects):
   clips = []
   good_objs = []
   for obj in meteor_objects:
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
      confirm_meteor(file)

def minmax_xy(obj):
   min_x = min(obj['oxs'])
   max_x = max(obj['oxs'])
   min_y = min(obj['oys'])
   max_y = max(obj['oys'])
   return(min_x, min_y, max_x, max_y)

def confirm_meteor(meteor_json_file):
   video_file = meteor_json_file.replace("-meteor.json", ".mp4")
   print("CONFIRM:", video_file)
   (hd_datetime, cam, sd_date, sd_y, sd_m, sd_d, sd_h, sd_M, sd_s) = convert_filename_to_date_cam(video_file)
   sun_alt = find_sun_alt(hd_datetime)
   if sun_alt > -5:
      sun_up = 1
      print("SUN is up:", sun_alt)
   else:
      sun_up = 0
   
   meteor_objects = load_json_file(meteor_json_file)
   meteor_objects = objects_to_clips(meteor_objects)

   for obj in meteor_objects:
      start = obj['ofns'][0] - 25
      if start < 0:
         start = 0
      end = obj['ofns'][-1] + 25
      if end > 1499:
         end = 1499 
      print(obj['ofns'])
      if sun_up == 0:
         # Run deeper detection on clip

         trim_clip, trim_start, trim_end = make_trim_clip(video_file, start, end)
         frames,color_frames,subframes,sum_vals,max_vals = load_frames_fast(trim_clip, json_conf, 0, 0, [], 0,[])

         frame = frames[0]
         min_x, min_y,max_x,max_y = minmax_xy(obj)
         fx = int((min_x + max_x) / 2)
         fy = int((min_y + max_y) / 2)
         if max_x - min_x < 100 or max_y - min_y < 100:
            print("FRAME SIZE:", frame.shape[1], frame.shape[0])
            cx1,cy1,cx2,cy2= bound_cnt(fx,fy,frame.shape[1],frame.shape[0], 100)
         else:
            cx1,cy1,cx2,cy2= bound_cnt(fx,fy,frame.shape[1],frame.shape[0], 200)

         for i in range (0, len(frames) - 1):
            frame = frames[i]

            w =  frame.shape[1]
            subframe = subframes[i]
            total_w = frame.shape[1] * 2
            total_h = frame.shape[0] 
            show_frame = np.zeros((total_h,total_w,3),dtype=np.uint8)
            frame = cv2.cvtColor(frame,cv2.COLOR_GRAY2RGB)
            subframe = cv2.cvtColor(subframe,cv2.COLOR_GRAY2RGB)
            print("CX:", cx1,cy1, cx2,cy2)
            cv2.rectangle(frame, (cx1, cy1), (cx2, cy2), (255,255,255), 1, cv2.LINE_AA)
            cv2.rectangle(subframe, (cx1, cy1), (cx2, cy2), (255,255,255), 1, cv2.LINE_AA)

            show_frame[0:total_h,0:w] = frame
            show_frame[0:total_h,w:w+w] = subframe
     

            cv2.imshow('pepe', show_frame)
            cv2.waitKey(0)
         print(obj) 

def make_trim_clip(video_file, start, end):
   outfile = video_file.replace(".mp4", "-trim" + str(start) + ".mp4")
   cmd = "/usr/bin/ffmpeg -y -i " + video_file + " -vf select=\"between(n\," + str(start) + "\," + str(end) + "),setpts=PTS-STARTPTS\" " + outfile
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
   files = glob.glob(queue_dir + wild )
   fc = 0
   for video_file in files:
      stack_file = video_file.replace(".mp4", "-stacked.png")
      if cfe(stack_file) == 0:
         cmd = "./flex-detect.py qs " + video_file
         print(cmd)
         os.system(cmd)
         fc = fc + 1
      else:
         print("skipping")


def scan_old_meteor_dir(dir):
   files = glob.glob(dir + "*trim*.json" )
   for file in files:
      if "meteor.json" not in file and "fail.json" not in file:
         print(file)
         video_file = file.replace(".json", ".mp4")
         meteor_file = file.replace(".json", "-meteor.json")
         fail_file = file.replace(".json", "-fail.json")
         if cfe(meteor_file) == 0 and cfe(fail_file) == 0:
            print("Not processed yet. ", meteor_file, fail_file)
            if cfe(video_file) == 1:
               #quick_scan(video_file)
               cmd = "./flex-detect.py qs " + video_file
               print(cmd)
               os.system(cmd)
               #exit()
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
   print("DDD", input_file, ddd)
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
   filename = filename.replace(".mp4" ,"")

   data = filename.split("_")
   fy,fm,fd,fh,fmin,fs,fms,cam = data[:8]
   f_date_str = fy + "-" + fm + "-" + fd + " " + fh + ":" + fmin + ":" + fs
   f_datetime = datetime.datetime.strptime(f_date_str, "%Y-%m-%d %H:%M:%S")
   return(f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs)

def check_running():
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
         cv2.circle(thresh_img,(mx,my), 1, (255,255,255), 1)
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

def find_contours_in_frame(frame, thresh=25):
   contours = [] 
   _, threshold = cv2.threshold(frame.copy(), thresh, 255, cv2.THRESH_BINARY)
   thresh_obj = cv2.dilate(threshold.copy(), None , iterations=4)
   threshold = cv2.convertScaleAbs(thresh_obj)
  # cv2.imshow('pepe', threshold)
  # cv2.waitKey(70)
   cnt_res = cv2.findContours(threshold.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
   if len(cnt_res) == 3:
      (_, cnts, xx) = cnt_res
   elif len(cnt_res) == 2:
      (cnts, xx) = cnt_res
   if len(cnts) < 50:
      for (i,c) in enumerate(cnts):
         px_diff = 0
         x,y,w,h = cv2.boundingRect(cnts[i])
         #if w > 2 or h > 2:
         contours.append([x,y,w,h])
   return(contours)

def fast_bp_detect(gray_frames, video_file):
   subframes = []
   frame_data = []
   objects = {}
   np_imgs = np.asarray(gray_frames[0:50])
   median_frame = cv2.convertScaleAbs(np.median(np.array(np_imgs), axis=0))
   median_cnts = find_contours_in_frame(median_frame, 100)
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
      #if sum_val > 100:
      #   thresh = 10
      #   _, subframe = cv2.threshold(subframe.copy(), thresh, 255, cv2.THRESH_BINARY)
         #subframe = cv2.subtract(subframe, median_frame)
      #   sum_val =cv2.sumElems(subframe)[0]

      #cv2.imshow('pepe', subframe)
      #cv2.waitKey(0)
      #min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(subframe)
      #mask_points.append((mx,my))
      #cv2.imshow('pepe', subframe)
      #cv2.waitKey(0)
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
   median_cnts = find_contours_in_frame(median_frame, 100)
   mask_points = []
   for x,y,w,h in median_cnts:
      mask_points.append((x,y))
   #median_frame = mask_frame(median_frame, mask_points, [], 5)

   sum_vals = []
   running_sum = 0
   
 
   for frame in gray_frames:
      # Good place to save these frames for final analysis visual
      #cv2.imshow('pepe', frame)
      #cv2.waitKey(0)
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
         contours = find_contours_in_frame(subframe)     
         if len(contours) > 0:
            for ct in contours:
               object, objects = find_object(objects, fn,ct[0], ct[1], ct[2], ct[3])
            #print("CNTS:", contours, object)
      else:
         contours = []
 
      #min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(subframe)

      frame_data[fn]['sum_val'] = float(sum_val)
      frame_data[fn]['contours'] = contours
      last_frame = frame
      fn = fn + 1


   return(frame_data, subframes, objects) 

def detect_motion_in_frames(subframes, video_file, fn):

   median_subframe = cv2.convertScaleAbs(np.median(np.array(subframes), axis=0))

   cnt_frames = {} 
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
      thresh = 10
      _, threshold = cv2.threshold(image_diff.copy(), thresh, 255, cv2.THRESH_BINARY)

      thresh_obj = cv2.dilate(threshold.copy(), None , iterations=4)
      thresh_obj = cv2.convertScaleAbs(thresh_obj)
      # save this for final view
      #cv2.imshow('pepe', thresh_obj)
      #cv2.waitKey(70)
      #cv2.imshow('pepe', image_diff)
      #cv2.waitKey(70)

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
      #cv2.imshow('p', thresh_obj)
      #cv2.waitKey(10)
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

def analyze_object_final(object):

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
      objects_by_label[label]['ofns'].append(object['ofns'][i])
      objects_by_label[label]['oxs'].append(object['oxs'][i])
      objects_by_label[label]['oys'].append(object['oys'][i])
      objects_by_label[label]['ows'].append(object['ows'][i])
      objects_by_label[label]['ohs'].append(object['ohs'][i])
      i = i + 1     


   if len(objects_by_label) == 1:
      # there is only one cluster of frames so we are good. 
      object = analyze_object(object)
      return(object)
   else:
      # there is more than one cluster of frames, so we need to remove the erroneous frames 
      most_frames = 0
      for label in objects_by_label :
         if len(objects_by_label[label]['ofns']) > most_frames:
            most_frames = len(objects_by_label[label]['ofns'])
            best_label = label
   
   # update the object to include only data items from the best label (cluster)
   object['ofns'] = objects_by_label[best_label]['ofns']
   object['oxs'] = objects_by_label[best_label]['oxs']
   object['oys'] = objects_by_label[best_label]['oys']
   object['ows'] = objects_by_label[best_label]['ows']
   object['ohs'] = objects_by_label[best_label]['ohs']
   object = analyze_object(object)
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
        

   print("DIST FROM START:", dist_from_start)
   print("LINE SEGS:", np.median(line_segs), line_segs)
   print("XSEGS :", np.median(line_segs), line_segs)
   print("MS:", np.median(ms),ms)
   print("BS:", np.median(bs),bs)
   med_seg_len = np.median(line_segs)
   med_x_seg_len = np.median(x_segs)
   acl_poly = 0
   med_m = np.median(ms)
   med_b = np.median(bs)

   print("BS:", np.median(bs),bs)
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

   print("XS:", object['oxs'])
   print("YS:", object['oys'])
   print("EXS:", est_xs)
   print("EYS:", est_ys)
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
  # cv2.imshow('pepe', show_frame)   
  # cv2.imshow('pepe2', stacked_frame)   
  # cv2.waitKey(70)
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
     # cv2.imshow('pepe', show_frame)   
     # cv2.waitKey(70)

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
   print("XSEGS:", x_segs)

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
     # cv2.imshow('pepe', show_frame)   
     # cv2.waitKey(70)


   for i in range(0, len(object['oxs'])):
      res_x = abs(object['oxs'][i] - object['est_xs'][i])
      res_y = abs(object['oys'][i] - object['est_ys'][i])
      res_xs.append(res_x)
      res_ys.append(res_y)
      res_tot.append(res_x + res_y)


   print("XS:", object['oxs'])
   print("YS:", object['oys'])
   print("EXS:", est_xs)
   print("EYS:", est_ys)
   print("XRES :", res_xs)
   print("YRES :", res_ys)
   print("RES TOT:", res_tot)
   print("LINE SEGS:", line_segs)
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
      plt.plot(i, f(i), 'go')
      x = i
      y = int(f(i))
      #ox = x
      #oy = poly_y[cc]
      show_frame[y,x] = [0,0,255]
      new_ys.append(int(f(i)))
      cc = cc + 1
   for ox,oy in zip(poly_x, poly_y):
      show_frame[oy,ox] = [255,0,0]
  # cv2.imshow('pepe3', show_frame)
  # cv2.waitKey(70)
   print("NEW YS:", new_ys)
   plt.plot(poly_x, poly_y, 'x')
   ax = plt.gca()
   ax.invert_yaxis()
   plt.show()





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


def analyze_object(object):
   meteor_yn = "Y"
   obj_class = "undefined"
   ff = object['ofns'][0] 
   lf = object['ofns'][-1] 
   elp = lf - ff 
   min_x = min(object['oxs'])
   max_x = max(object['oxs'])
   min_y = min(object['oys'])
   max_y = max(object['oys'])
   min_max_dist = calc_dist((min_x, min_y), (max_x,max_y))
   if elp > 0:
      dist_per_elp = min_max_dist / elp
   else:
      dist_per_elp = 0

   if elp > 5 and dist_per_elp < 1 or dist_per_elp < 1:
      moving = "not moving"
      meteor_yn = "no"
      obj_class = "star"
   else:
      moving = "moving"
   if min_max_dist > 12 and dist_per_elp < .1:
      moving = "slow moving"
      meteor_yn = "no"
      obj_class = "plane"
   if min_max_dist > 12 and dist_per_elp < .1:
      moving = "slow moving"
      meteor_yn = "no"
      obj_class = "plane"
   if dist_per_elp < .8 and dist_per_elp > .1:
      moving = "slow moving"
      meteor_yn = "no"
      obj_class = "plane"

   #cm
   fc = 0
   cm = 0
   max_cm = 0
   last_fn = None
   for fn in object['ofns']:
      if last_fn is not None:
         if last_fn + 1 == fn or last_fn + 2 == fn: 
            cm = cm + 1
            if cm > max_cm :
               max_cm = cm
      
      fc = fc + 1
      last_fn = fn
   
   # classify the object
 
   if max_cm <= 3 and elp > 5 and min_max_dist < 8 and dist_per_elp < .01:
      obj_class = "star"
   if elp > 5 and min_max_dist > 8 and dist_per_elp >= .01 and dist_per_elp < 1:
      obj_class = "plane"
   if elp > 300:
      meteor_yn = "no"
   if elp < 2:
      meteor_yn = "no" 
   if cm < 2:
      meteor_yn = "no"
   if dist_per_elp > 5:
      meteor_yn = "Y"
   if min_max_dist < 5:
      obj_class = "star"
      meteor_yn = "no"

   if meteor_yn == "no":
      meteory_yn = "no"
   else: 
      meteory_yn = "Y"
      obj_class = "meteor"
  

   object['report'] = {}
   object['report']['elp'] = elp
   object['report']['min_max_dist'] = min_max_dist
   object['report']['dist_per_elp'] = dist_per_elp
   object['report']['moving'] = moving
   object['report']['max_cm'] = max_cm
   object['report']['max_fns'] = len(object['ofns']) - 1
   object['report']['obj_class'] = obj_class 
   object['report']['meteor_yn'] = meteor_yn
   object['report']['angular_separation'] = 0
   object['report']['angular_velocity'] = 0
   return(object)


def find_object(objects, fn, cnt_x, cnt_y, cnt_w, cnt_h):
   #obj_dist_thresh = 50
   obj_dist_thresh = 25 
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
      objects[obj_id]['ows'] = []
      objects[obj_id]['ohs'] = []
      objects[obj_id]['ofns'].append(fn)
      objects[obj_id]['oxs'].append(center_x)
      objects[obj_id]['oys'].append(center_y)
      objects[obj_id]['ows'].append(cnt_w)
      objects[obj_id]['ohs'].append(cnt_h)
      found_obj = obj_id
   if found == 1:
      objects[found_obj]['ofns'].append(fn)
      objects[found_obj]['oxs'].append(center_x)
      objects[found_obj]['oys'].append(center_y)
      objects[found_obj]['ows'].append(cnt_w)
      objects[found_obj]['ohs'].append(cnt_h)

   objects[found_obj] = analyze_object(objects[found_obj])

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

   print("GAP:", gap_to_cm_ratio, gap_to_elp_ratio, cons)

   if cons < 3:
      print("CONS MONTION TOO LOW!")
      return(0)

   if gap_to_cm_ratio > .2 and gap_to_elp_ratio > .2:
      print("GAP TEST GOOD!")
      return(1)
   else:
      print("GAP TEST FAILED!", gap_to_cm_ratio, gap_to_elp_ratio)
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
      #cv2.imshow('Pepe', show_frame)
      #cv2.waitKey(10)
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
         #cv2.imshow('pepe', subframe)
         #cv2.waitKey(10)
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

         #cv2.imshow('pepe', show_img)
         #cv2.waitKey(70) 
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
   events = []
   event = []
   event_info = []
   events_info = []
   cm = 0
   nomo = 0
   i = 0
   med_sum = np.median(sum_vals)
   med_max = np.median(max_vals)
   #median_frame = cv2.convertScaleAbs(np.median(np.array(subframes), axis=0))
   for sum_val in sum_vals:
      max_val = max_vals[i]
      #print(i, med_sum, med_max, sum_val , max_val)
      if sum_val > med_sum * 2 or max_val > med_max * 10:
         subframe = subframes[i]
         min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(subframe)
         if max_val > 10:
            event_info.append((sum_val, max_val, mx, my))
            event.append(i)
            cm = cm + 1
            nomo = 0
         else:
            nomo = nomo + 1
      else:
         nomo = nomo + 1
      if cm > 2 and nomo > 3:
         events.append(event)
         events_info.append(event_info)
         event = []
         event_info = []
         cm = 0
      elif nomo > 3:
         event = []
         event_info = []
         cm = 0
      i = i + 1

   i = 0
   objects = {}
   for event in events:
      object = None
      fc = 0
      for evi in events_info[i]:
         sv, mv, mx, my = evi
         fn = event[fc]
         object, objects = find_object(objects, fn,mx, my, 5, 5)
         fc = fc + 1
      i = i + 1


   pos_meteors = {}
   mc = 1
   for object in objects:
      if objects[object]['report']['min_max_dist'] > 5 and objects[object]['report']['max_cm'] >= 3 and objects[object]['report']['dist_per_elp'] > .8:
         pos_meteors[mc] = objects[object]
         mc = mc + 1

   #print("EVENTS:", events)
   #print("POS METEORS:", pos_meteors)

   return(events, pos_meteors)


def quick_scan(video_file):
   # 3 main parts
   # 1st scan entire clip for 'bright events' evaluating just the sub pixels in the subtracted frame
   # 2nd any bright events that match a meteor profile are sliced out and contours are found and logged for each frame
   # contours are turned into objects and evaluated
   # 3rd for any objects that might be meteors, create a longer clip around the event (+/-50 frames)
   # and run motion detection on those frames locating the objects. 

   debug = 0
   if "mp4" not in video_file:
      print("BAD INPUT FILE:", video_file)
      return(0, "bad input")
 
   #PREP WORK

   # start performance timer
   start_time = time.time()

   # set stack file and skip if it alread exists. 
   stack_file = video_file.replace(".mp4", "-stacked.png")
   if cfe(stack_file) == 1:
      print("Already done this.")
      #return()

   # setup variables
   cm = 0
   no_mo = 0
   event = []
   bright_events = []
   valid_events = []

   station_id = get_station_id(video_file)
   json_conf = load_json_conf(station_id)
   hd_datetime, hd_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(video_file)
   print("STATION:", station_id, video_file, start_time)

   # load the frames
   frames,color_frames,subframes,sum_vals,max_vals = load_frames_fast(video_file, json_conf, 0, 0, [], 0,[])
   events,pos_meteors = fast_check_events(sum_vals, max_vals, subframes)
   
   # check time after frame load
   elapsed_time = time.time() - start_time
   print("Loaded frames.", elapsed_time)
   print("Total Frames:", len(frames))
   print("Possible Meteors:", pos_meteors)
   # check to make sure frames were loaded
   if len(frames) < 5:
      print("bad input file.")
      return()




   # Stack the frames and report the run time
   stacked_frame = stack_frames_fast(frames)
   cv2.imwrite(stack_file, stacked_frame) 
   elapsed_time = time.time() - start_time
   print("Stacked frames.", elapsed_time)

   if len(pos_meteors) == 0:
      elapsed_time = time.time() - start_time
      print("ELAPSED TIME:", elapsed_time)
      print("NO METEORS:", elapsed_time)
      return(0, "No meteors found.")
   else:
      meteor_file = video_file.replace(".mp4", "-meteor.json")
      #save_json_file(meteor_file, pos_meteors)
      print("POSSIBL METEORS FOUND! Do deeper check.")
      elapsed_time = time.time() - start_time
      print("ELPASED TIME:", elapsed_time)

   # Only continue if we made it past the easy / fast detection


   ############################################################################
   # DETECTION PHASE 1
   # 
   # Make the subframes and detect the total pixels per subframe 
   bp_frame_data, subframes = fast_bp_detect(frames,video_file)
   elapsed_time = time.time() - start_time
   print("ELPASED TIME AFTER FAST BP DETECT :", elapsed_time)

   # Find events and objects inside the subframe frame date
   elapsed_time = time.time() - start_time
   print("ELPASED TIME BEFORE FIND EVENTS FROM BP DATA:", elapsed_time)
   events, objects = find_events_from_bp_data(bp_frame_data,subframes)

   if debug == 1:
      print("EVENTS")
      for event in events:
         print("EVENT:", event)

      print("OBJECTS")
      for obj in objects:
         print("OBJ:", obj, objects[obj])

   elapsed_time = time.time() - start_time
   print("ELPASED TIME:", elapsed_time)

   # Find the meteor like objects 
   meteors = []
   non_meteors = []
   for obj in objects:
      if len(objects[obj]['ofns']) > 2:
         objects[obj] = merge_obj_frames(objects[obj])
         objects[obj] = analyze_object_final(objects[obj])
      if objects[obj]['report']['meteor_yn'] == "Y":
         print ("********************* METEOR *********************")
         print(objects[obj]['ofns'])
         #objects[obj] = remove_bad_frames_from_object(objects[obj], frames,subframes)
         meteors.append(objects[obj])
      else:
         non_meteors.append(objects[obj])

   print("METEORS:", meteors) 
   if len(meteors) > 10:
      print("ERROR! Something like a bird.")
      non_meteors = meteors + non_meteors
      meteors = []

 

   print ("Meteor like objects.", len(meteors))
   if len(meteors) == 0:
      fail_file = video_file.replace(".mp4", "-fail.json")
      save_json_file(fail_file, non_meteors)
      print("NO METEORS FOUND!", fail_file)
      elapsed_time = time.time() - start_time
      print("ELPASED TIME NO METEORS:", elapsed_time)
      return(0, "No meteors found.")
   else:
      meteor_file = video_file.replace(".mp4", "-meteor.json")
      save_json_file(meteor_file, meteors)
      print("METEORS FOUND!", meteor_file)
      elapsed_time = time.time() - start_time
      print("ELPASED TIME:", elapsed_time)
      return(0, "Meteors found.")

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
            print("MAX SIZE IS:", sz ) 
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

            #cv2.imshow('pepe', show_frame)
            #cv2.waitKey(0)
            #print("SHAPE:", sub_cnt_frame.shape)

            sub_cnt_frame = cv2.resize(sub_cnt_frame, (0,0),fx=20, fy=20)
            min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(sub_cnt_frame)
            contours= find_contours_in_frame(sub_cnt_frame, int(max_val/2))
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

               #cv2.imshow('pepe', cnt_rgb)
               #cv2.waitKey(0)
               if "leading_x" not in real_meteors[meteor_obj]:
                  real_meteors[meteor_obj]['leading_x'] = []
                  real_meteors[meteor_obj]['leading_y'] = []

               #print("LEADING X INFO: ", cx1, cy1, le_x, le_y)
               real_meteors[meteor_obj]['leading_x'].append(int((le_x / 20) + cx1))
               real_meteors[meteor_obj]['leading_y'].append(int((le_y / 20) + cy1))


            cv2.circle(cnt_rgb,(mx,my), 5, (255,255,255), 1)
            if bad == 1:
               cv2.putText(cnt_rgb, "bad frame",  (25,25), cv2.FONT_HERSHEY_SIMPLEX, .3, (255, 255, 255), 1)
           
            #cv2.imshow('pepe', cnt_rgb)
            #cv2.waitKey(0) 
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
            #cv2.imshow('pepe', graph_xy)
            #cv2.waitKey(0)
            info = {}
            cf = color_frames[fn].copy()
            cv2.circle(cf,(lx,ly), 10, (255,255,255), 1) 
 
            custom_frame = make_custom_frame(cf,subframes[fn],tracker_cnt,graph, graph_xy, info)

            #graph = cv2.resize(graph, (150,500))
            #cv2.imshow('pepe', graph)
            #cv2.waitKey(0)
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
            #cv2.imshow('pepe', show_frame)
            #cv2.waitKey(0) 

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
            #cv2.imshow('pepe', show_frame)
            #cv2.waitKey(0)
         ec = ec + 1


     
   if False:
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

      #objects = []
      for event in valid_events:
        
         for fn in range(event[0], event[-1]):
            cv2.imshow('pepe', frames[fn])
            cv2.waitKey(70)



      save_json_file(data_file, event_json)
   elapsed_time = time.time() - start_time
   print("Total Run Time.", elapsed_time)

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

   cv2.imshow('pepe', custom_frame)
   cv2.waitKey(70)

def custom_graph(data_x,data_y,max_x,max_y,graph_x,graph_y,type):

   fig_x = graph_x / 100
   fig_y = graph_y / 100
   import matplotlib
   matplotlib.use('Agg')
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
   for object in meteors: 
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
         contours= find_contours_in_frame(subframes[fn])
         for ct in contours:
            object, objects = find_object(objects, fn,ct[0], ct[1], ct[2], ct[3])

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
            print("CNT:", fn, x,y,w,h)
            cnt_frames[fn]['xs'].append(x)
            cnt_frames[fn]['ys'].append(y)
            cnt_frames[fn]['ws'].append(w)
            cnt_frames[fn]['hs'].append(h)
      fn = fn + 1

   objects = find_cnt_objects(cnt_frames, objects)


   return(motion_events, objects)      


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
   last_frame = None

   color_frames = []
   frames = []
   subframes = []
   sum_vals = []
   max_vals = []
   frame_count = 0
   go = 1
   while go == 1:
      if True :
         _ , frame = cap.read()
         if frame is None:
            if frame_count <= 5 :
               cap.release()
               return(frames,color_frames,sub_frames,sum_vals,max_vals)
            else:
               go = 0
         else:
            #print("FRMAE:", frame_count)
            #color_frames.append(frame)
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

            if last_frame is not None:
               subframe = cv2.subtract(frame, last_frame)
               subframes.append(subframe)
               sum_val =cv2.sumElems(subframe)[0]
               if sum_val > 100:
                  min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(subframe)
               else:
                  max_val = 0
               sum_vals.append(sum_val)
               max_vals.append(max_val)

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
       
            if frame_count % 1 == 0:
               frames.append(frame)
            last_frame = frame
      frame_count = frame_count + 1
   cap.release()
   if len(crop) == 4:
      return(frames,x1,y1)
   else:
      return(frames, color_frames, subframes, sum_vals, max_vals)

        


cmd = sys.argv[1]
video_file = sys.argv[2]

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
