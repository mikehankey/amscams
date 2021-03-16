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

#dump_frames()

def get_contours(frame):
   cont = []
   crop= []
   cnt_res = cv2.findContours(frame.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
   if len(cnt_res) == 3:
      (_, cnts, xx) = cnt_res
   elif len(cnt_res) == 2:
      (cnts, xx) = cnt_res
   for (i,c) in enumerate(cnts):
      x,y,w,h = cv2.boundingRect(cnts[i])
      if w > 1 and h > 1:
         cont.append((x,y,w,h))

   #cont = sorted(cont, key=lambda x: (x[2]+x[3]), reverse=True)[0:10]
   #cont = sorted(cont, key=lambda x: (x[0]), reverse=False)
   return(cont)

def mask_points(frame, points):
   for x,y,w,h in points:
      frame[y:y+h,x:x+w] = 0
   return frame

def tracker(vfile, first_frame=None):
   frames = load_frames_simple(vfile)
   #if first_frame is None:
   first_frame = cv2.cvtColor(frames[0], cv2.COLOR_BGR2GRAY)

   _, threshold = cv2.threshold(first_frame.copy(), 60, 255, cv2.THRESH_BINARY)
   threshold = cv2.dilate(threshold.copy(), None , iterations=4)
   stars = get_contours(threshold)
   first_frame = mask_points(first_frame, stars)
   print("STARS:", stars)
   #cv2.imshow('pepe', threshold)
   #cv2.waitKey(0)

   fn = vfile.split("/")[-1]
   el = fn.split("_")
   station,sequence,frmt,year,month,day,hour,minute,second,msec,cam = el
   date_str = year + "_" + month + "_" + day + "_" + hour + "_" + minute + "_" + second
   f_datetime = datetime.datetime.strptime(date_str, "%Y_%m_%d_%H_%M_%S")



   i = 0
   for frame in frames:
      bw_frame =  cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
      bw_frame = mask_points(bw_frame, stars)
      mframe = frame.copy()
      sub = cv2.subtract(bw_frame, first_frame)
      sub = mask_points(sub, stars)

      extra_sec = i / 25
      frame_time = f_datetime + datetime.timedelta(0,extra_sec)
      frame_time_str = frame_time.strftime("%Y_%m_%d_%H_%M_%S.%f")

      #sub[0:500,0:1920] = 0
      thresh_val = 50
      min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(sub)
      thresh_val = max_val - 100
      if thresh_val < 30:
         thresh_val = 30
      thresh_val = 10
      _, threshold = cv2.threshold(sub.copy(), thresh_val, 255, cv2.THRESH_BINARY)
      cnts= get_contours(threshold)
      print("LEN:", len(cnts), cnts)
      for cnt in cnts:
          x,y,w,h = cnt
          if x < 0:
             x = 0 
          if y + h >= 1080:
             y = 1080 - h
          
          #roi_img = frame[y:y+h,x:x+w]
          #roi_img = cv2.resize(roi_img,(1280,720))
          #mframe[100:820, 320:1600] = roi_img
          cv2.rectangle(mframe, (int(x), int(y)), (int(x+w) , int(y+h) ), (255, 255, 255), 1)
      show_frame = cv2.resize(mframe,(1280,720))
      cv2.putText(show_frame, str(frame_time_str),  (25, 1080), cv2.FONT_HERSHEY_SIMPLEX, .3, (200, 200, 200), 1)
      #show_frame = cv2.resize(threshold,(1280,720))
      cv2.imshow('pepe', show_frame)
      cv2.waitKey(10)
      i += 1
   return(first_frame)

vfiles = ["/mnt/ams2/CUSTOM/SPACEX/2021_03_14/ALL/AMS1_01_HD_2021_03_14_10_08_38_000_010003.mp4", "/mnt/ams2/CUSTOM/SPACEX/2021_03_14/ALL/AMS1_02_HD_2021_03_14_10_09_00_000_010003.mp4", "/mnt/ams2/CUSTOM/SPACEX/2021_03_14/ALL/AMS1_03_HD_2021_03_14_10_10_01_000_010003.mp4"]

vfiles = [ '/mnt/ams2/CUSTOM/SPACEX/2021_03_14/ALL/AMS7_01_HD_2021_03_14_10_08_39_000_010039.mp4', '/mnt/ams2/CUSTOM/SPACEX/2021_03_14/ALL/AMS7_02_HD_2021_03_14_10_09_00_000_010039.mp4', '/mnt/ams2/CUSTOM/SPACEX/2021_03_14/ALL/AMS7_03_HD_2021_03_14_10_10_00_000_010039.mp4']

vfiles = ['/mnt/ams2/CUSTOM/SPACEX/2021_03_14/ALL/AMS9_01_HD_2021_03_14_10_08_00_000_010052.mp4', '/mnt/ams2/CUSTOM/SPACEX/2021_03_14/ALL/AMS9_02_HD_2021_03_14_10_09_00_000_010052.mp4', '/mnt/ams2/CUSTOM/SPACEX/2021_03_14/ALL/AMS9_03_HD_2021_03_14_10_08_53_000_010051.mp4', '/mnt/ams2/CUSTOM/SPACEX/2021_03_14/ALL/AMS9_04_HD_2021_03_14_10_09_01_000_010051.mp4', '/mnt/ams2/CUSTOM/SPACEX/2021_03_14/ALL/AMS9_05_HD_2021_03_14_10_10_01_000_010051.mp4']



first_frame = None
for vfile in vfiles:
   first_frame = tracker(vfile, first_frame)
