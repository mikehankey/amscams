''' 

basic utility functions 

'''
import subprocess
import math
from pathlib import Path
import datetime
import cv2
#from PIL import ImageFont, ImageDraw, Image, ImageChops
import numpy as np
import ephem
import json


def cnt_max_px(cnt_img):
   cnt_img = cv2.GaussianBlur(cnt_img, (7, 7), 0)
   min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(cnt_img)

   return(max_loc, min_val, max_val)


def bound_cnt(x,y,img_w,img_h,sz=10):
   if x - sz < 0:
      mnx = 0
   else:
      mnx = int(x - sz)

   if y - sz < 0:
      mny = 0
   else:
      mny = int(y - sz)

   if x + sz > img_w - 1:
      mxx = int(img_w - 1)
   else:
      mxx = int(x + sz)

   if y + sz > img_h -1:
      mxy = int(img_h - 1)
   else:
      mxy = int(y + sz)
   return(mnx,mny,mxx,mxy)

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

def day_or_night(capture_date, json_conf):

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
   return(f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs)

def make_meteor_dir(sd_video_file, json_conf):
   (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(sd_video_file)
   meteor_dir = "/mnt/ams2/meteors/" + fy + "_" + fm + "_" + fd + "/" 
   if cfe(meteor_dir, 1) == 0:
      os.system("mkdir " + meteor_dir)
   return(meteor_dir)

def cfe(file,dir = 0):
   if dir == 0:
      file_exists = Path(file)
      if file_exists.is_file() is True:
         return(1)
      else:
         return(0)
   if dir == 1:
      file_exists = Path(file)
      if file_exists.is_dir() is True:
         return(1)
      else:
         return(0)

def load_json_file(json_file):  
   #try:
   if True:
      with open(json_file, 'r' ) as infile:
         json_data = json.load(infile)
   #except:
   #   json_data = False
   return json_data 

def save_json_file(json_file, json_data, compress=False):
   with open(json_file, 'w') as outfile:
      if(compress==False):
         json.dump(json_data, outfile, indent=4, allow_nan=True)
      else:
         json.dump(json_data, outfile, allow_nan=True)
   outfile.close()

def get_masks(this_cams_id, json_conf, hd = 0):
   #hdm_x = 2.7272
   #hdm_y = 1.875
   my_masks = []
   cameras = json_conf['cameras']
   for camera in cameras:
      if str(cameras[camera]['cams_id']) == str(this_cams_id):
         if hd == 1:
            masks = cameras[camera]['hd_masks']
         else:
            masks = cameras[camera]['masks']
         for key in masks:
            mask_el = masks[key].split(',')
            (mx, my, mw, mh) = mask_el
            masks[key] = str(mx) + "," + str(my) + "," + str(mw) + "," + str(mh)
            my_masks.append((masks[key]))
   return(my_masks)

def convert_filename_to_date_cam(file, ms = 0):
   el = file.split("/")
   filename = el[-1]
   filename = filename.replace(".mp4" ,"")
   if "-" in filename:
      xxx = filename.split("-")
      filename = xxx[0]
   el = filename.split("_")
   if len(el) >= 8:
      fy,fm,fd,fh,fmin,fs,fms,cam = el[0], el[1], el[2], el[3], el[4], el[5], el[6], el[7]
   else:
      fy,fm,fd,fh,fmin,fs,fms,cam = "1999", "01", "01", "00", "00", "00", "000", "010001"
   if "-" in cam:
      cel = cam.split("-")
      cam = cel[0]

   #print("CAM:", cam)
   #exit()

   f_date_str = fy + "-" + fm + "-" + fd + " " + fh + ":" + fmin + ":" + fs
   f_datetime = datetime.datetime.strptime(f_date_str, "%Y-%m-%d %H:%M:%S")
   if ms == 1:
      return(f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs,fms)

   else:
      return(f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs)

def buffered_start_end(start,end, total_frames, buf_size):
   print("BUF: ", total_frames)
   bs = start - buf_size
   be = end + buf_size
   if bs < 0:
      bs = 0
   if be >= total_frames:
      be = total_frames - 1

   return(bs,be)

def angularSeparation(ra1,dec1, ra2,dec2):

   ra1 = math.radians(float(ra1))
   dec1 = math.radians(float(dec1))
   ra2 = math.radians(float(ra2))
   dec2 = math.radians(float(dec2))
   return math.degrees(math.acos(math.sin(dec1)*math.sin(dec2) + math.cos(dec1)*math.cos(dec2)*math.cos(ra2 - ra1)))


def check_running(progname, sec_grep = None):
   cmd = "ps -aux |grep \"" + progname + "\" | grep -v grep |wc -l"
    
   output = subprocess.check_output(cmd, shell=True).decode("utf-8")
   #print(cmd)
   #print(output)
   output = int(output.replace("\n", ""))
   if int(output) > 0:
      return(output)
   else:
      return(0)

def calc_dist(p1,p2):
   x1,y1 = p1
   x2,y2 = p2
   dist = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
   return dist


def date_to_jd(year,month,day):
    """
    Convert a date to Julian Day.
    Algorithm from 'Practical Astronomy with your Calculator or Spreadsheet',
        4th ed., Duffet-Smith and Zwart, 2011.
    Parameters
    ----------
    year : int
        Year as integer. Years preceding 1 A.D. should be 0 or negative.
        The year before 1 A.D. is 0, 10 B.C. is year -9.
    month : int
        Month as integer, Jan = 1, Feb. = 2, etc.
    day : float
        Day, may contain fractional part.
    Returns
    -------
    jd : float
        Julian Day
    Examples
    --------
    Convert 6 a.m., February 17, 1985 to Julian Day
    >>> date_to_jd(1985,2,17.25)
    2446113.75
    """
    if month == 1 or month == 2:
        yearp = year - 1
        monthp = month + 12
    else:
        yearp = year
        monthp = month

    # this checks where we are in relation to October 15, 1582, the beginning
    # of the Gregorian calendar.
    if ((year < 1582) or
        (year == 1582 and month < 10) or
        (year == 1582 and month == 10 and day < 15)):
        # before start of Gregorian calendar
        B = 0
    else:
        # after start of Gregorian calendar
        A = math.trunc(yearp / 100.)
        B = 2 - A + math.trunc(A / 4.)

    if yearp < 0:
        C = math.trunc((365.25 * yearp) - 0.75)
    else:
        C = math.trunc(365.25 * yearp)

    D = math.trunc(30.6001 * (monthp + 1))

    jd = B + C + D + day + 1720994.5

    return jd

def check_running(progname, sec_grep = None):
   cmd = "ps -aux |grep \"" + progname + "\" | grep -v grep |wc -l"

   output = subprocess.check_output(cmd, shell=True).decode("utf-8")
   #print(cmd)
   #print(output)
   output = int(output.replace("\n", ""))
   if int(output) > 0:
      return(output)
   else:
      return(0)

