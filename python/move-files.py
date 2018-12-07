#!/usr/bin/python3
from as6libs import get_sun_info
import json
import time
import glob
import ephem
import subprocess
from pathlib import Path
import os
import datetime
from time import mktime
from pytz import utc


json_file = open('../conf/as6.json')
json_str = json_file.read()
json_conf = json.loads(json_str)


sd_video_dir = json_conf['site']['sd_video_dir']
hd_video_dir = json_conf['site']['hd_video_dir']
proc_dir = json_conf['site']['proc_dir']


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



def move_old_school_files():
   cmd = 'find /mnt/ams2/SD/ | grep .mp4'
   output = subprocess.check_output(cmd, shell=True).decode("utf-8")
   files = output.split('\n')
   for file in files:
      el = file.split("/")
      file_name = el[-1]
      if "trim" in file:
         cmd = "mv " +  file + " /mnt/ams2/SD/meteors/" + file_name
         os.system(cmd) 
         continue 

      (cam_num, date_str, xyear, xmonth, xday, xhour, xmin, xsec) = parse_date(file)
      sun_status,sun_az,sun_el = get_sun_info(date_str)

      date_dir = proc_dir + xyear + "-" + xmonth + "-" + xday
      file_exists = Path(date_dir)
      skip = 0
      if (file_exists.is_dir() is False):
         os.system("mkdir " + date_dir) 

      if sun_status == "day":
         cmd = "mv " +  file + " " + proc_dir + file_name
         os.system(cmd) 
      else:
         cmd = "mv " +  file + " " + date_dir + "/" + file_name
         os.system(cmd) 
      print (cmd)


def purge_sd_daytime_files():
   files = glob.glob(proc_dir + "daytime/*")
   for file in files:
      (cam_num, date_str, xyear, xmonth, xday, xhour, xmin, xsec) = parse_date(file)
      sun_status,sun_az,sun_el = get_sun_info(date_str)
      st = os.stat(file)
      cur_time = int(time.time())
      mtime = st.st_mtime
      tdiff = cur_time - mtime
      tdiff = tdiff / 60 / 60 / 24
      if sun_status == 'day' and tdiff > 1:
         print ("File is daytime and this many days old", tdiff, file)
         os.system("rm " + file)

def purge_hd_files():
   files = glob.glob(hd_video_dir + "*")
   for file in files:
      (cam_num, date_str, xyear, xmonth, xday, xhour, xmin, xsec) = parse_date(file)
      sun_status,sun_az,sun_el = get_sun_info(date_str)
      st = os.stat(file)
      cur_time = int(time.time())
      mtime = st.st_mtime
      tdiff = cur_time - mtime
      tdiff = tdiff / 60 / 60 / 24
      if sun_status == 'day' and tdiff > 1:
         print ("File is daytime and this many days old", tdiff, file)
         print("rm " + file)
         os.system("rm " + file)
      elif tdiff > 2:
         print ("File is nighttime and this many days old will be purged.", tdiff, file)
         print("rm " + file)
         os.system("rm " + file)

def purge_SD_proc_dir():
   files = glob.glob(proc_dir + "*")

   for file in files:
      st = os.stat(file)
      el = file.split("/") 
      date_file = el[-1]
      if date_file != 'daytime' and date_file != 'rejects':
         dir_date = datetime.datetime.strptime(date_file, "%Y_%m_%d") 
         print ("DIR DATE: ", dir_date)
         cur_time = int(time.time())
         mtime = mktime(utc.localize(dir_date).utctimetuple())

         tdiff = cur_time - mtime
         tdiff = tdiff / 60 / 60 / 24
         print (file, tdiff)
         if tdiff >= 45 and file != 'daytime' and file != 'rejects':
            print ("We should delete this dir in the archive. it is this many days old:", tdiff) 
            cmd = "rm -rf " + file
            os.system(cmd)
            print(cmd)


def move_processed_SD_files():

   files = glob.glob(sd_video_dir + "*stacked.jpg")
   #print("SUN:", sun_status)
   
   for file in files:
      el = file.split("/")
      if "-stack.jpg" in file:
         video_file = file.replace("-stack.jpg", ".mp4")
      else: 
         video_file = file.replace("-stacked.jpg", ".mp4")
      file_name = el[-1]
      vel = video_file.split("/")
      video_file_name = vel[-1]
      print ("Stack File:", file)
      print ("Video File:", video_file)
      (cam_num, date_str, xyear, xmonth, xday, xhour, xmin, xsec) = parse_date(file)
      sun_status,sun_az,sun_el = get_sun_info(date_str)
      print("SUN:", sun_status)

      date_dir = proc_dir + xyear + "-" + xmonth + "-" + xday
      file_exists = Path(date_dir)
      skip = 0
      if (file_exists.is_dir() is False):
         os.system("mkdir " + date_dir) 
      if sun_status == "day":
         cmd = "mv " +  file + " " + proc_dir + "daytime/" + file_name
         print(cmd)
         os.system(cmd) 
         cmd = "mv " +  video_file + " " + proc_dir + "daytime/" + video_file_name
         print(cmd)
         os.system(cmd) 
      else:
         if "-stacked" not in file_name:
            file_name = file_name.replace("stack", "stacked")

         cmd = "mv " +  file + " " + date_dir + "/" + file_name
         print(cmd)
         os.system(cmd) 

         cmd = "mv " +  video_file + " " + date_dir + "/" + video_file_name
         print(cmd)
         os.system(cmd) 
  
         wild_card = video_file.replace(".mp4", "*")
         cmd = "mv " +  wild_card + " " + date_dir + "/" 
         os.system(cmd) 
   


purge_hd_files()
purge_sd_daytime_files()
purge_SD_proc_dir()
