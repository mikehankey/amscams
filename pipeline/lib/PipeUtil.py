''' 

basic utility functions 

'''
import os
import time
import subprocess
import math
from pathlib import Path
import datetime
import cv2
#from PIL import ImageFont, ImageDraw, Image, ImageChops
import numpy as np
import ephem
#import simplejson as json
import json
import glob
import decimal
dec = decimal.Decimal


def dist_between_two_points(lat1,lon1,lat2,lon2):
   from math import radians, sin, cos, atan2, sqrt
   R = 6373.0
   lat1 = radians(lat1)
   lon1 = radians(lon1)
   lat2 = radians(lat2)
   lon2 = radians(lon2)
   dlon = lon2 - lon1
   dlat = lat2 - lat1
   a = (sin(dlat/2))**2 + cos(lat1) * cos(lat2) * (sin(dlon/2))**2
   c = 2 * atan2(sqrt(a), sqrt(1-a))
   distance = R * c

   return(distance)

def starttime_from_file(filename):
   (f_datetime, cam, f_date_str,fy,fmon,fd, fh, fm, fs) = convert_filename_to_date_cam(filename)
   trim_num = get_trim_num(filename)
   extra_sec = int(trim_num) / 25
   event_start_time = f_datetime + datetime.timedelta(0,extra_sec)
   return(event_start_time)


def get_localtime_offset(lat,lng,in_datetime):


   #tz = tf.timezone_at(float(lng), float(lat))
   bergamo = {"lat": float(lat), "lng": float(lng), "in_datetime": in_datetime}
   #minute_offset, utc_time, local_time = get_offset(**bergamo)
   minute_offset, utc_time, local_time = get_offset(**bergamo)
   local_time_str = local_time.strftime('%Y-%m-%d %H:%M') + " (UTC " + str(minute_offset/60) + ")"
   return(local_time_str, minute_offset/60)

def get_offset(*, lat, lng,in_datetime):
    """
    returns a location's time zone offset from UTC in minutes.
    local_time = today - dt.timedelta(hours = hour_offset)
    """
    import datetime as dt

    try:
       from timezonefinder import TimezoneFinder
       from pytz import timezone, utc
       # TIME ZONE!
       tf = TimezoneFinder()
    except:
       print("COULDN'T RUN ZIMEZONE!")
       exit()
    today = in_datetime 
    tz_target = timezone(tf.certain_timezone_at(lng=lng, lat=lat))
    # ATTENTION: tz_target could be None! handle error case
    today_target = tz_target.localize(today)
    today_utc = utc.localize(today)

    offset_min = (today_utc - today_target).total_seconds() / 60
    offset_hour = offset_min / 60
    local_time = today + dt.timedelta(hours = offset_hour)
    return (today_utc - today_target).total_seconds() / 60, today, local_time

def get_moon_phase(in_date= None, lat=None, lon=None):
   try:
      import pylunar
   except:
      print("pylunar not installed!")
      return(None)

   # set lat/lon (in hours minutes seconds!)
   # convert lat/lon decimal to hms
   i,d = str(lat).split(".")
   gi,gd = str(lon).split(".")

   # just need the whole/lat lon for moon phase!
   mi = pylunar.MoonInfo((i,0,0), (gi,0,0))

   # set the UTC time
   year,month,day,hour,minute,second = in_date.split("_")
   mi.update((int(year),int(month),int(day),int(hour),int(minute),int(second)))
   moon_age = mi.age()
   fractional_phase = mi.fractional_phase()
   phase_name = mi.phase_name()
   return(moon_age, fractional_phase, phase_name)


def ephem_info(device_lat, device_lng, capture_date):

   obs = ephem.Observer()

   obs.pressure = 0
   obs.horizon = '-0:34'
   obs.lat = device_lat
   obs.lon = device_lng
   obs.date = capture_date
   my_day = capture_date.split(" ")[0]

   sun = ephem.Sun()
   moon = ephem.Moon()


   sun_rise = str(obs.previous_rising(sun))
   sun_set = str(obs.next_setting(moon))
   moon_rise = str(obs.previous_rising(sun))
   moon_set = str(obs.next_setting(moon))

   sun.compute(obs)
   moon.compute(obs)

   (sun_alt, x,y) = str(sun.alt).split(":")
   (moon_alt, x,y) = str(moon.alt).split(":")

   saz = str(sun.az)
   moon_az = str(moon.az)

   #print("SUN/MOON:", saz, moon_az)
   (sun_az, x,y) = saz.split(":")
   (moon_az, x,y) = moon_az.split(":")
   if int(sun_alt) < -1:
      sun_status = "night"
   else:
      sun_status = "day"

   if -15 < int(sun_alt) < 1:
      if int(sun_az) < 180:
         sun_status = "dawn"
      else:
         sun_status = "dusk"


   return(sun_status, sun_az, sun_alt, sun_rise, sun_set, moon_az, moon_alt, moon_rise, moon_set)

def get_file_info(file):
   cur_time = int(time.time())
   if cfe(file) == 1:
      st = os.stat(file)

      size = st.st_size
      mtime = st.st_mtime
      tdiff = cur_time - mtime
      tdiff = tdiff / 60
      return(size, tdiff)
   else:
      return(0,0)


def remove_corrupt_files(json_conf):
   log = open("/mnt/ams2/logs/corrupt.txt", "a")

   files = glob.glob("/mnt/ams2/SD/*.mp4")
   for file in sorted(files):
      size, tdiff = get_file_info(file)
      if tdiff > 10 and size < 100:
         print("CORRUPT:", tdiff, size, file)
         cmd = "rm " + file
         print(cmd)
         os.system(cmd)
         log.write(str(tdiff)+","+str(size)+str( file)+"\n")
   # now HD
   files = glob.glob("/mnt/ams2/HD/*.mp4")
   for file in sorted(files):
      size, tdiff = get_file_info(file)
      if tdiff > 10 and size < 100:
         print("CORRUPT:", tdiff, size, file)
         cmd = "rm " + file
         print(cmd)
         os.system(cmd)
         log.write(str(tdiff)+","+str(size)+str( file)+"\n")
   log.close()

def meteors_only(objects):
   meteors = []
   for id in objects:
      print(objects[id])
      if "report" in objects[id]:
         if objects[id]['report']['meteor_yn'] == "Y":
            meteors.append(objects[id])
   return(meteors)


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

def day_or_night(capture_date, json_conf,extra=0):

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
   if extra == 0:
      return(sun_status)
   else:
      return(sun_status,sun_az,sun_alt)

def convert_filename_to_date_cam_old(file):
   el = file.split("/")
   filename = el[-1]
   if "trim" in filename:
      filename, xxx = filename.split("-")[:2]
   filename = filename.replace(".mp4" ,"")

   data = filename.split("_")
   fy,fm,fd,fh,fmin,fs,fms,cam = data[:8]
   f_date_str = fy + "-" + fm + "-" + fd + " " + fh + ":" + fmin + ":" + fs
   f_datetime = datetime.datetime.strptime(f_date_str, "%Y-%m-%d %H:%M:%S")
   cam = cam.replace(".png", "")
   cam = cam.replace(".jpg", "")
   cam = cam.replace(".json", "")
   cam = cam.replace(".mp4", "")
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
   print("LOADING:", json_file)
   #try:
   if True:
      #print("Trying:", json_file)
      with open(json_file, 'r' ) as infile:
         json_data = json.load(infile)
   #except:
   #   json_data = False
   return json_data 

def save_json_file(json_file, json_data, compress=False):
   if "cp" in json_data:
      if json_data['cp'] is not None:
         for key in json_data['cp']:
            #print(key, type(json_data['cp']))
            if type(json_data['cp'][key]) == np.ndarray:
               json_data['cp'][key] = json_data['cp'][key].tolist()


   with open("test.json", 'w') as outfile:
      json.dump(json_data, outfile, indent=4, allow_nan=True )
   outfile.close()
   try:
      test_json = load_json_file("test.json")
   except:
      print("trying to save failed:", json_file)
      return()
   # if this fails, the file is corrupt or there is a problem so do not save!

   with open(json_file, 'w') as outfile:
      if(compress==False):
         json.dump(json_data, outfile, indent=4, allow_nan=True )
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
   cam = cam.replace(".png", "")
   cam = cam.replace(".jpg", "")
   cam = cam.replace(".json", "")
   cam = cam.replace(".mp4", "")

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

def find_angle(p1,p2):
   myrad = math.atan2(p1[1]-p2[1],p1[0]-p2[0])
   mydeg = math.degrees(myrad)
   return(mydeg)


def collinear(x1, y1, x2, y2, x3, y3): 
   return ((y1 - y2) * (x1 - x3), (y1 - y3) * (x1 - x2));


def get_trim_num(file):
   el = file.split("-trim")
   at = el[1]
   at = at.replace("-SD.mp4", "")
   at = at.replace("-crop", "")
   at = at.replace("-HD.mp4", "")
   at = at.replace(".mp4", "")
   at = at.replace("-", "")
   at = at.replace(".json", "")
   at = at.replace("HDmeteor", "")
   at = at.replace("-stacked", "")
   at = at.replace("stacked", "")
   at = at.replace(".jpg", "")
   at = at.replace(".png", "")
   return(at)

def fn_dir(file):
   fn = file.split("/")[-1]
   dir = file.replace(fn, "")
   return(fn, dir)

def load_mask_imgs(json_conf):
   mask_files = glob.glob("/mnt/ams2/meteor_archive/" + json_conf['site']['ams_id'] + "/CAL/MASKS/*mask*.png" )
   mask_imgs = {}
   sd_mask_imgs = {}
   for mf in mask_files:
      mi = cv2.imread(mf, 0)
      omh, omw = mi.shape[:2]
      fn,dir = fn_dir(mf)
      fn = fn.replace("_mask.png", "")
      mi = cv2.resize(mi, (1920, 1080))
      sd = cv2.resize(mi, (omw, omh))
      mask_imgs[fn] = mi
      sd_mask_imgs[fn] = sd
   return(mask_imgs, sd_mask_imgs)

def mfd_roi(mfd=None, xs=None, ys=None, ex=0, ey=0):
   if mfd is not None:
      if len(mfd) == 0:
         return(0,0,1080,1080)
      xs = [row[2] for row in mfd]
      ys = [row[3] for row in mfd]
   x1 = min(xs) 
   y1 = min(ys) 
   x2 = max(xs) 
   y2 = max(ys) 
   mx = int(np.mean(xs))
   my = int(np.mean(ys))
   w = x2 - x1
   h = y2 - y1
   if w >= h:
      h = w
   else:
      w = h
   if w < 150 or h < 150:
      w = 150
      h = 150
   if w > 1079 or h > 1079 :
      w = 1060
      h = 1060
   w += ex
   h += ey
   x1 = mx - int(w / 2)
   x2 = mx + int(w / 2)
   y1 = my - int(h / 2)
   y2 = my + int(h / 2)
   w = x2 - x1
   h = y2 - y1

   if x1 < 0:
      x1 = 0
      x2 = w
   if y1 < 0:
      y1 = 0
      y2 = h
   if x2 >= 1920:
      x2 = 1919
      x1 = 1919 - w
   if y2 >= 1080:
      y2 = 1079
      y1 = 1079 - h
   return(x1,y1,x2,y2)


def bound_cnt_new(x1,y1,x2,y2,img, margin=.5):
   ih,iw = img.shape[:2]
   rw = x2 - x1
   rh = y2 - y1
   if rw > rh:
      rh = rw
   else:
      rw = rh
   rw += int(rw )
   rh += int(rh )
   if rw >= ih or rh >= ih:
      rw = int(ih*.95)
      rh = int(ih*.95)
   if rw < 100 or rh < 100:
      rw = 100
      rh = 100

   cx = int((x1 + x2)/2)
   cy = int((y1 + y2)/2)
   nx1 = cx - int(rw / 2)
   nx2 = cx + int(rw / 2)
   ny1 = cy - int(rh / 2)
   ny2 = cy + int(rh / 2)
   if nx1 <= 0:
      nx1 = 0
      nx2 = rw
   if ny1 <= 0:
      ny1 = 0
      ny2 = rh
   if nx2 >= iw:
      nx1 = iw-rw-1
      nx2 = iw-1
   if ny2 >= ih:
      ny2 = ih-1
      ny1 = ih-rh-1
   if ny1 <= 0:
      ny1 = 0
   if nx1 <= 0:
      nx1 = 0
   print("NX", nx1,ny1,nx2,ny2)
   return(nx1,ny1,nx2,ny2)
