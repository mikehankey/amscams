#!/usr/bin/python3
import glob
import datetime
from datetime import datetime as dt
import os
from lib.FFFuncs import lower_bitrate 
from random import seed
from random import random
from random import randrange 

from lib.PipeUtil import load_json_file, cfe, get_file_info, day_or_night, convert_filename_to_date_cam, save_json_file
os.system("git pull")
json_conf = load_json_file("../conf/as6.json")

def do_hd_requests():
   station_id = json_conf['site']['ams_id']
   os.system("cp /mnt/archive.allsky.tv/LIVE/hd-requests.json ./")
   print("cp /mnt/archive.allsky.tv/LIVE/hd-requests.json ./")
   if cfe("hd_req_log.json") == 1:
      hd_log = load_json_file("./hd_req_log.json")
   else:
      hd_log = {}
   data = load_json_file("./hd-requests.json")
   if station_id in data:
      hd_requests = data[station_id]
   else: 
      print("NO HD REQUESTS.")
      return
   for req in hd_requests['hd_requests']:
      print(req)
      if req not in hd_log:
         # copy media for this file! 
         root_file = req.replace(".mp4", "")
         hd_log[req] = 1
         date = req[0:10]
         mdir ="/mnt/ams2/meteors/" + date + "/" 
         cloud_dir = "/mnt/archive.allsky.tv/" + station_id + "/MEDIA/" + date + "/" 
         if cfe(cloud_dir, 1) == 0:
            os.makedirs(cloud_dir)
         mfile = mdir + req.replace(".mp4", ".json")
         print("GET:", mfile)
         if cfe(mfile) == 1:
            mj = load_json_file(mfile)
            print(mj.keys())
            if "hd_trim" in mj:
               if cfe(mj['hd_trim']) == 1:
                  if cfe(cloud_dir + root_file + "-HD.mp4") == 0:
                     os.system("cp " + mj['hd_trim'] + " " + cloud_dir + root_file + "-HD.mp4")
                  else:
                     print("File already saved.")
            if cfe(cloud_dir + mj['sd_video_file']) == 0:
               os.system("cp " + mj['sd_video_file'] + " " + cloud_dir)
            if cfe(cloud_dir  + root_file + ".jpg") == 0:
               os.system("cp " + mj['sd_stack'] + " " + cloud_dir + root_file + ".jpg")
            if cfe(cloud_dir  + root_file + "-HD.jpg") == 0:
               os.system("cp " + mj['hd_stack'] + " " + cloud_dir + root_file + "-HD.jpg")
            hd_log[req] = 1
   save_json_file("hd_req_log.json", hd_log)
            

def get_weather(lat,lng):
   outfile = "weather.txt"
   url = "wttr.in/" + str(lat) + "," + str(lng) + "?0T --output " + outfile
   print(url)
   os.system("curl " + url)
   fp = open(outfile)
   lc = 0
   for line in fp:
      line = line.replace("\n", "")
      if lc == 2:
         status = line[16:]
      if lc == 3:
         temp = line[16:]
      if lc == 4:
         wind = line[16:]
      if lc == 5:
         wind_speed = line[16:]
      lc += 1
   weather_desc = "Forecast\: " + str(status) + " " + str(temp) 
   
   return(status, weather_desc)
 

do_hd_requests()
weather_status, weather_desc = get_weather(json_conf['site']['device_lat'],json_conf['site']['device_lng'])
print(weather_desc)

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
else:
   last_hour = 23
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
text_y1 = "320"
text_x2 = "500"
text_y2 = "340"
text_x3 = "10"
text_y3 = "340"
# find current files that match the requested minutes 
for cf in copy_files:
   fn = cf.split("/")[-1]
   (f_datetime, cam, f_date_str,fy,fmon,fd, fh, fm, fs) = convert_filename_to_date_cam(cf)
   date_str = f_date_str[0:-3] + " UTC"
   date_str = date_str.replace(":", "\\:")
   print(date_str)
   sun_status, sun_az, sun_el = day_or_night(f_date_str, json_conf,1) 

   extra_text = date_str + " " + weather_desc + " Solar Elevation \:" + str(sun_el) + "° " + sun_status + " time"
   extra_file_info = "_" + station_id + "-" + sun_status + "-" + weather_status.lower()  + ".mp4"
   extra_file_info = extra_file_info.replace(" ", "")
   cache_file = LIVE_CACHE_DIR + fn.replace(".mp4", extra_file_info)

   temp_file = cache_file.replace(".mp4", "-TEMP.mp4")
   if cfe(cache_file) == 0:
      if cfe(cf) == 1: 
         sz, tdiff = get_file_info(cf)
         if float(tdiff) < 1.1:
            print("FILE NOT DONE YET." )
            continue
      else:
         continue
      nothing = ""
      cmd = """/usr/bin/ffmpeg -i """ + cf + """  -c:v libx264 -pix_fmt yuv420p -crf 30 -vf "scale=640:360,drawtext=fontfile=/usr/share/fonts/truetype/lato/Lato-Medium.ttf:text='""" + credits + """':fontcolor=white:fontsize=12:box=1:boxcolor=black@0.5:boxborderw=5:x=""" + text_x1 + """:y=""" + text_y1 + """,drawtext=fontfile=/usr/share/fonts/truetype/lato/Lato-Medium.ttf:text='""" + nothing + """':fontcolor=white:fontsize=12:box=1:boxcolor=black@0.5:boxborderw=5:x=""" + text_x2 + """:y=""" + text_y2 + """,drawtext=fontfile=/usr/share/fonts/truetype/lato/Lato-Medium.ttf:text='""" + extra_text + """':fontcolor=white:fontsize=12:box=1:boxcolor=black@0.5:boxborderw=5:x=""" + text_x3 + """:y=""" + text_y3 + """" -codec:a copy """ + cache_file 
      print(cmd)
      os.system(cmd)
      
      cloud_file = LIVE_CLOUD_DIR + fn
      cloud_file = LIVE_CLOUD_DIR + fn.replace(".mp4", extra_file_info)
      if cfe(cloud_file) == 0:
         cmd = "cp " + cache_file + " " + cloud_file
         print(cmd)
         os.system(cmd)





