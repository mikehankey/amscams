#!/usr/bin/python3
import datetime
import cv2

from lib.PipeVideo import ffmpeg_cats, load_frames_simple
from lib.PipeUtil import cfe, save_json_file, load_json_file, convert_filename_to_date_cam
import os
import glob
# script to archive footage from longer events like space-x rockets or satellites


def archive_event_data():
   conf = load_json_file("spacex.json")
   
   title = conf['title']
   credits = conf['credits']
   ams_id = conf['ams_id']
   
   # define cams that caught the event
   cams = conf['cams']
   
   event_start_time = conf['event_start_time']
   event_end_time = conf['event_end_time']
   base_file = event_start_time[:-5]
   date = event_start_time[0:10]
   (year,month,day,hour,minute,second) = event_start_time.split("_" )
   sd_dir = "/mnt/ams2/SD/proc2/" + date + "/" 
   hd_dir = "/mnt/ams2/HD/"
   out_dir = "/mnt/ams2/CUSTOM/SPACEX/2021_03_14/"
   cloud_dir = "/mnt/archive.allsky.tv/" + ams_id + "/CUSTOM/SPACEX/2021_03_14/"
   if cfe(out_dir,1) == 0:
      os.makedirs(out_dir)
   if cfe(cloud_dir,1) == 0:
      os.makedirs(cloud_dir)
   
   os.system("rm " + out_dir + "*.mp4")
   os.system("rm " + cloud_dir + "*.mp4")
   
   start_dt = datetime.datetime.strptime(event_start_time, "%Y_%m_%d_%H_%M_%S")
   end_dt = datetime.datetime.strptime(event_end_time, "%Y_%m_%d_%H_%M_%S")
   
   min_diff = int((end_dt - start_dt).total_seconds() / 60)
   all_sd = []
   all_hd = []
   
   for cam in cams:
      for i in range(0, min_diff+1):
         mn = int(minute) + i
         mns = "{:02d}".format(mn)
         wild = base_file + str(mns) + "*" + cam + "*.mp4"
         print("B:", wild)
         sd_files = glob.glob(sd_dir + wild)
         for ff in sd_files:
            if "trim" not in ff:
               all_sd.append(ff)
         sd_files = glob.glob(hd_dir + wild)
         for ff in sd_files:
            if "trim" not in ff:
               all_hd.append(ff)
   
   html = "<h1>" + title + "</h1>"
   html += "<p>Photo Credit: " + credits + "</p>"
   html += "<h2>SD Files</h2>"
   
   for vf in all_sd:
      fn = vf.split("/")[-1]
      out_file = ams_id + "_" + "SD_" + fn
      cmd = "cp " + vf + " " + out_dir + out_file
      html += "<a href=" + out_file + ">" + out_file + "</a><br>\n"
      if cfe(out_dir + out_file) == 0:
         print(cmd)
         os.system(cmd)
      if cfe(cloud_dir + out_file) == 0:
         cmd = "cp " + vf + " " + cloud_dir + out_file
         print(cmd)
         os.system(cmd)
   
   html += "<h2>HD Files</h2>"
   
   for vf in all_hd:
      fn = vf.split("/")[-1]
      out_file = ams_id + "_" + "HD_" + fn
      cmd = "cp " + vf + " " + out_dir + out_file
      html += "<a href=" + out_file + ">" + out_file + "</a><br>\n"
      if cfe(out_dir + out_file) == 0:
         print(cmd)
         os.system(cmd)
      if cfe(cloud_dir + out_file) == 0:
         cmd = "cp " + vf + " " + cloud_dir + out_file
         print(cmd)
         os.system(cmd)
   data = {}
   data['sd_files'] = all_sd
   data['hd_files'] = all_hd
   save_json_file(out_dir + "files.json", data)
   out = open(out_dir + "index.html", "w")
   out.write(html)
   os.system("cp " + out_dir + "index.html" + " " + cloud_dir)
   print(out_dir)
   print(cloud_dir)

def cat_videos():
   work_dir = "/mnt/ams2/CUSTOM/SPACEX/2021_03_14/ALL/"
   out_dir = "/mnt/ams2/CUSTOM/SPACEX/2021_03_14/FINAL/"
   stations = ['AMS1', 'AMS7', 'AMS9', 'AMS15'] 
   station_files = {}
   for station in stations:
      station_files[station] = {}
      print(work_dir + station + "_*.mp4")
      station_files[station]['files'] = glob.glob(work_dir + station + "_*.mp4")

   #print(station_files)
   for station in station_files:
      print(station)
      for file in sorted(station_files[station]['files']):
         print(station, file)
      outfile = out_dir + station + "_spacex_2021_03_14"
      ffmpeg_cats(sorted(station_files[station]['files']), outfile)



def dump_frames():
   work_dir = "/mnt/ams2/CUSTOM/SPACEX/2021_03_14/ALL/"
   out_dir = "/mnt/ams2/CUSTOM/SPACEX/2021_03_14/FRAMES/"
   if cfe(out_dir,1) == 0:
      os.makedirs(out_dir)
   stations = ['AMS1', 'AMS7', 'AMS9', 'AMS15'] 
   station_files = {}
   for station in stations:
      station_files[station] = {}
      print(work_dir + station + "_*.mp4")
      station_files[station]['files'] = glob.glob(work_dir + station + "_*.mp4")

   #print(station_files)
   for station in station_files:
      for file in sorted(station_files[station]['files']):
         fn = file.split("/")[-1]
         if "ALL" in fn:
            continue
         el = fn.split("_")
         print(el)
         station,sequence,frmt,year,month,day,hour,minute,second,msec,cam = el
         date_str = year + "_" + month + "_" + day + "_" + hour + "_" + minute + "_" + second
         f_datetime = datetime.datetime.strptime(date_str, "%Y_%m_%d_%H_%M_%S")

         tdir = out_dir + fn.replace(".mp4", "")
         if cfe(tdir,1) == 0:
            os.makedirs(tdir)
         frames = load_frames_simple(file)
         for i in range(0, len(frames)):
            extra_sec = i / 25
            frame_time = f_datetime + datetime.timedelta(0,extra_sec)
            frame_time_str = frame_time.strftime("%Y_%m_%d_%H_%M_%S.%f")
            outfile = tdir + frame_time_str + ".jpg"
            print(frame_time, frame_time_str, outfile)
            cv2.imwrite(outfile, frames[i])
         #print("ST:", station, tdir, file, len(frames))
      #outfile = out_dir + station + "_spacex_2021_03_14"

dump_frames()
