#!/usr/bin/python3

import ephem
import sys
import os
import glob
from amscommon import read_config

dir = sys.argv[1]
cam = sys.argv[2]
cams_id = sys.argv[3]
conf = read_config("/home/ams/fireball_camera/conf/config-1.txt")


def day_or_night(config, capture_date):

   obs = ephem.Observer()

   obs.pressure = 0
   obs.horizon = '-0:34'
   obs.lat = config['device_lat']
   obs.lon = config['device_lng']
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


def parse_date (this_file):

   el = this_file.split("/")
   file_name = el[-1]
   file_name = file_name.replace("_", "-")
   file_name = file_name.replace(".", "-")
   fnel = file_name.split("-")
   #print("FILE:", file_name, len(fnel))
   if len(fnel) == 11:
      xyear, xmonth, xday, xhour, xmin, xsec, xcam_num, ftype,fnum,fst,xext = fnel
   if len(fnel) == 10:
      xyear, xmonth, xday, xhour, xmin, xsec, xcam_num, ftype,fnum,xext = fnel
   if len(fnel) == 9:
      xyear, xmonth, xday, xhour, xmin, xsec, xcam_num, ftype, xext = fnel
   if len(fnel) == 8:
      xyear, xmonth, xday, xhour, xmin, xsec, xcam_num, xext = fnel

   cam_num = xcam_num.replace("cam", "")

   date_str = xyear + "-" + xmonth + "-" + xday + " " + xhour + ":" + xmin + ":" + xsec
   capture_date = date_str
   return(cam_num, date_str, xyear, xmonth, xday, xhour, xmin, xsec)


print("Rename MP4 files to work with cams and move them to the cams inject dir.")
print ("Dir: ", dir)
print ("Cam: ", cam)
mp4_files = glob.glob(dir + "/*-cam" + str(cam) + ".mp4")
print(dir + "/*-cam" + str(cam) + ".mp4")

for mp4_file in mp4_files:

   (cam_num, date_str, xyear, xmonth, xday, xhour, xmin, xsec) = parse_date(mp4_file)
   sun_status = day_or_night(conf, date_str)
   new_file = mp4_file.replace("-", "_")
   new_file = new_file.replace("cam" + str(cam), "000_" + str(cams_id))
   el = new_file.split("/")
   new_fn = el[-1]
   if sun_status == 'night':
      cmd = "mv " + mp4_file + " /mnt/ams2/CAMS/queue/" + new_fn
      os.system(cmd)
      print(cmd)
   else :
      cmd = "mv " + mp4_file + " /mnt/ams2/SD/proc/daytime/" + new_fn
      os.system(cmd)
      print(cmd)
