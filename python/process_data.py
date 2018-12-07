#!/usr/bin/python3

import ephem
import json
import subprocess
import glob
import time
import datetime
import os

json_file = open('../conf/as6.json')
json_str = json_file.read()
json_conf = json.loads(json_str)



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
   if int(sun_alt) < -1:
      sun_status = "night"
   else:
      sun_status = "day"
   return(sun_status)


def convert_filename_to_date_cam(file):
   el = file.split("/")
   filename = el[-1]
   filename = filename.replace(".mp4" ,"")
   fy,fm,fd,fh,fmin,fs,fms,cam = filename.split("_")
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

def move_files_to_queue():

   sd_video_dir = json_conf['site']['sd_video_dir']
   hd_video_dir = json_conf['site']['hd_video_dir']
   cams_queue_dir = json_conf['site']['cams_queue_dir']
   proc_dir = json_conf['site']['proc_dir']
   cams_dir = json_conf['site']['cams_dir']

   files = glob.glob(sd_video_dir + "/*.mp4")
   cc = 0
   files = sorted(files, reverse=True)
   for file in sorted(files, reverse=True):
      (f_datetime, cam, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(file)
      sun_status = day_or_night(f_date_str)
      cur_time = int(time.time())
      st = os.stat(file)
      size = st.st_size
      print ("SIZE:", size)
      mtime = st.st_mtime
      tdiff = cur_time - mtime
      tdiff = tdiff / 60
      sun_status = day_or_night(f_date_str)
      if (tdiff > 3): 
         if (sun_status == 'day'):
            cmd = "mv " + file + " " + proc_dir + "daytime/" 
            os.system(cmd)
         else:
            cmd = "mv " + file + " " + cams_queue_dir 
            print(cmd)
            os.system(cmd)

   cmd = "cd " + cams_dir + "RunFolder/; ./thumb " + cams_queue_dir
   print(cmd)
   os.system(cmd)

running = check_running()
if (running <= 2):
   move_files_to_queue()
else:
   print ("Already Running: ", running)
