#!/usr/bin/python3
import glob
import datetime
from datetime import datetime as dt
import os
from lib.FFFuncs import lower_bitrate 
from random import seed
from random import random
from random import randrange 

from lib.PipeUtil import load_json_file, cfe, get_file_info
json_conf = load_json_file("../conf/as6.json")
station_id = json_conf['site']['ams_id']
all_cams = {}
now = dt.now()
cur_date = now.strftime("%Y_%m_%d")
peak_dates = ['2021_08_10', '2021_08_11', '2021_08_12']

if cur_date not in peak_dates:
   print("Perseids Peak is over! EXIT", cur_date)
   exit()
cur_hour = now.strftime("%H")
cur_min = now.strftime("%M")
if int(cur_hour) > 0:
   last_hour = int(cur_hour) - 1
if last_hour < 10:
   last_hour = "0" + str(last_hour)
else:
   last_hour = str(last_hour)

for cam_num in json_conf['cameras']:
   cn = int(cam_num.replace("cam", ""))
   all_cams[cn] = json_conf['cameras'][cam_num]['cams_id']
   

# This script will copy minute files to the LIVE dir at some interval based on the schedule
# This does not copy continuously but just a few files per hour
# Files are then rotated through in the stream

# Minutes network wide are defined in the master file
os.system("cp /mnt/archive.allsky.tv/LIVE/Perseids2021.json ./")
os.system("cp /mnt/archive.allsky.tv/LIVE/photo_credits.json ./")
print("cp /mnt/archive.allsky.tv/LIVE/photo_credits.json ./")
photo_credits = load_json_file("photo_credits.json")
credits = photo_credits[station_id]
schedule = load_json_file("Perseids2021.json")

if station_id in schedule:
   my_schedule = schedule[station_id]
   my_minutes = schedule[station_id]['minutes']
   if "best_cams" in my_schedule:
      my_cams = my_schedule['best_cams']
   else:
      my_cams = [4]

   print("MY SCHEDULE:", my_schedule)
else:
   print("This station is not broadcasting.")
   exit()

cam_idx = randrange(len(my_cams)) 
print("ALL CAMS:", all_cams)
print("CAM IDX:", cam_idx)
my_cam_idx = my_cams[cam_idx]
selected_cam = all_cams[my_cam_idx]
print("SELECTED CAM:", all_cams[my_cam_idx])
print("BROADCAST PARAMS")
print("Current time:", cur_date, cur_hour, cur_min)
print(station_id, my_cams, my_minutes)
copy_files = []

for smin in my_minutes:
   if smin < 10:
      smin = "0" + str(smin)
   else:
      smin = str(smin)
   wild = cur_date + "_" + cur_hour + "_" + smin + "*" + selected_cam + "*"
   last_hour_wild = cur_date + "_" + last_hour + "_" + smin + "*" + selected_cam + "*"
   queue_file_dir = "/mnt/ams2/SD/" 
   proc_dir = "/mnt/ams2/SD/proc2/" + cur_date + "/"
   day_dir = "/mnt/ams2/SD/proc2/daytime/" + cur_date + "/"
   qfiles = glob.glob(queue_file_dir + wild + "*.mp4")
   pfiles = glob.glob(proc_dir + wild + "*.mp4")
   dfiles = glob.glob(day_dir + wild + "*.mp4")
   last_qfiles = glob.glob(queue_file_dir + last_hour_wild + "*.mp4")
   last_pfiles = glob.glob(proc_dir + last_hour_wild + "*.mp4")
   last_dfiles = glob.glob(day_dir + last_hour_wild + "*.mp4")


   for cfile in qfiles:
      print("CF:", cfile)
      copy_files.append(cfile)
   for cfile in pfiles:
      print("CF:", cfile)
      copy_files.append(cfile)
   for cfile in dfiles:
      print("CF:", cfile)
      copy_files.append(cfile)
   for cfile in last_qfiles:
      print("CF:", cfile)
      copy_files.append(cfile)
   for cfile in last_pfiles:
      print("CF:", cfile)
      copy_files.append(cfile)
   for cfile in last_dfiles:
      print("CF:", cfile)
      copy_files.append(cfile)

LIVE_CACHE_DIR = "/home/ams/amscams/pipeline/LIVE_CACHE/"
LIVE_CLOUD_DIR = "/mnt/archive.allsky.tv/" + station_id + "/LIVE_CACHE/"
print("COPY FILES:", copy_files)
if cfe(LIVE_CACHE_DIR, 1) == 0:
   os.makedirs(LIVE_CACHE_DIR)
if cfe(LIVE_CLOUD_DIR, 1) == 0:
   os.makedirs(LIVE_CLOUD_DIR)
scale_x = "640"
scale_y = "360"
text_x1 = "10"
text_y1 = "335"
text_x2 = "500"
text_y2 = "335"
# find current files that match the requested minutes 
for cf in copy_files:
   fn = cf.split("/")[-1]
   cache_file = LIVE_CACHE_DIR + fn
   temp_file = cache_file.replace(".mp4", "-TEMP.mp4")
   if cfe(cache_file) == 0:
      if cfe(cf) == 1: 
         sz, tdiff = get_file_info(cf)
         if float(tdiff) < 1.1:
            print("FILE NOT DONE YET." )
            continue
      else:
         continue
      date_str = fn[0:16] + " UTC"
      cmd = """ffmpeg -i """ + cf + """  -c:v libx264 -pix_fmt yuv420p -crf 30 -vf "scale=640:360,drawtext=fontfile=/usr/share/fonts/truetype/lato/Lato-Medium.ttf:text='""" + credits + """':fontcolor=white:fontsize=12:box=1:boxcolor=black@0.5:boxborderw=5:x=""" + text_x1 + """:y=""" + text_y1 + """,drawtext=fontfile=/usr/share/fonts/truetype/lato/Lato-Medium.ttf:text='""" + date_str + """':fontcolor=white:fontsize=12:box=1:boxcolor=black@0.5:boxborderw=5:x=""" + text_x2 + """:y=""" + text_y2 + """" -codec:a copy """ + cache_file 
      print(cmd)
      os.system(cmd)
      
      cloud_file = LIVE_CLOUD_DIR + fn
      if cfe(cloud_file) == 0:
         cmd = "cp " + cache_file + " " + cloud_file
         print(cmd)
         os.system(cmd)




