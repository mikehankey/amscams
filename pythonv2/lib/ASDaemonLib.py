import os
from datetime import datetime, timedelta
import subprocess
import ephem
import glob
import json
from lib.UtilLib import check_running 
from lib.FileIO import cfe , save_json_file, load_json_file

def fix_days():
   proc_file = "/mnt/ams2/SD/proc2/json/proc_stats.json";
   if cfe(proc_file) == 0:
      return()
   proc_data = load_json_file(proc_file)
   for day in proc_data:
      if proc_data[day]['video_files'] - proc_data[day]['image_files'] > 10:
         print("Thumbs are missing for these days!")
         os.system("./scan_stack.py fms " + day + " > /dev/null 2>&1 &")
         return()

def update_proc_index(day ):
   proc_file = "/mnt/ams2/SD/proc2/json/proc_stats.json";
   if cfe(proc_file) == 1:
      proc_stats = load_json_file(proc_file)
   else:
      return()
   proc_stats[day] = get_proc_stats(day)
   save_json_file(proc_file)


def proc_index():
   proc_stats = {}
   proc_file = "/mnt/ams2/SD/proc2/json/proc_stats.json";
   if cfe(proc_file) == 1:
      proc_stats = load_json_file(proc_file)
   today = datetime.today()
   num_days = 14
   for i in range (0,int(num_days)):
      past_day = datetime.now() - timedelta(hours=24*i)
      past_day = past_day.strftime("%Y_%m_%d")
      proc_stats[past_day] = get_proc_stats(past_day)
      print(past_day, proc_stats[past_day])
   for day in proc_stats:
      print(day, proc_stats[day])
   save_json_file(proc_file, proc_stats) 
   print(proc_file)

def get_proc_stats(day):
   proc_dir = "/mnt/ams2/SD/proc2/" + day + "/"
   video_files = get_files(proc_dir, "*.mp4")
   image_files = get_files(proc_dir + "/images/", "*-tn.png")
   vals_files = get_files(proc_dir + "/data/", "*-vals.json")
   detect_files = get_files(proc_dir + "/data/", "*-detect.json")
   mm_files = get_files(proc_dir + "/data/", "*-maybe-meteors.json")
   nm_files = get_files(proc_dir + "/data/", "*-non-meteor.json")
   tm_files = get_files(proc_dir + "/data/", "*-toomany.json")
   m_files = get_files(proc_dir + "/data/", "*-meteor.json")
   proc_stats = {}
   proc_stats['video_files'] = len(video_files)
   proc_stats['image_files'] = len(image_files)
   proc_stats['vals_files'] = len(vals_files)
   proc_stats['detect_files'] = len(detect_files)
   proc_stats['mm_files'] = len(mm_files)
   proc_stats['nm_files'] = len(nm_files)
   proc_stats['tm_files'] = len(tm_files)
   proc_stats['m_files'] = len(m_files)
   return(proc_stats)

def update_latest(cam_info, pending_files):
   print(cam_info)
   print(pending_files)
   cc = {}
   for cd in cam_info:
      cam_id = cd['cam_id']
      if cam_id not in cc:
         cc[cam_id] = 0
      for ff in sorted(pending_files,reverse=True):
         if cam_id in ff:
            if cc[cam_id] > 1:
               outfile = "/mnt/ams2/latest/" + cam_id + ".jpg"
               extract_frames(ff,1,2,outfile)
               print(ff, outfile)
               break 
            cc[cam_id] += 1
         

def extract_frames(video_file,start,end,outfile,w=640,h=360):
   fn = video_file.split("/")[-1] + "-trim" + str(start)
   temp_dir = "/home/ams/tmpvids/" + fn + "/"
   if cfe(temp_dir, 1) == 0:
      os.makedirs(temp_dir)
   cmd = "ffmpeg -y -i " + video_file + " -vf select='between(n\," + str(start) + "\," + str(end) + ")' -vsync 0 " + outfile + ">/dev/null 2>&1" 
   print(cmd)
   os.system(cmd)


def run_vals_detect(day=None):
   running = check_running("flex-detect.py bv")
   if running == 0:

      proc_file = "/mnt/ams2/SD/proc2/json/proc_stats.json";
      if cfe(proc_file) == 0:
         return()
      proc_data = load_json_file(proc_file)
      for day in proc_data:
         if proc_data[day]['mm_files'] >= 1:
            print("Need to detect vals on this day!", day)
            os.system("./flex-detect.py bv " + day + " > /dev/null 2>&1 &")
            return()
   else:
      print("Vals detect is already running.")


def run_verify_meteors(day=None):
   running = check_running("flex-detect.py vms")
   if running == 0:
      cmd = "./flex-detect.py vms " + day + " > /dev/null 2>&1 &"
      print(cmd)
      os.system(cmd)
   else:
      print("Verify already running.")


def get_files(dir, match = None):
   if match is None:
      files = glob.glob(dir + "*")
   else:
      files = glob.glob(dir + match)
   return(files)

def exec_cmd(cmd):
   try:
      output = subprocess.check_output(cmd, shell=True).decode("utf-8")
      return(1, output)
   except:
      output = "Command failed." 
      return(0, output)


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

