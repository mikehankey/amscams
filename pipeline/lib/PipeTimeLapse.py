'''
   functions for making timelapse movies
'''
import datetime as dt
from datetime import datetime
import glob
import sys
import os
from lib.PipeImage import  quick_video_stack, rotate_bound
import cv2
from lib.PipeWeather import detect_aurora, aurora_stack_vid, extract_images

from lib.PipeUtil import cfe, save_json_file, convert_filename_to_date_cam, load_json_file, day_or_night
from lib.PipeAutoCal import fn_dir, get_cal_files
from lib.DEFAULTS import *
import numpy as np
import subprocess 
import json
import logging


# Configure global logger
logger = logging.getLogger('global_logger')
logger.setLevel(logging.INFO)  # This ensures INFO and higher messages are handled

# Create file handler with appropriate level
file_handler = logging.FileHandler('/mnt/ams2/temp/app.log')
file_handler.setLevel(logging.INFO)  # Ensures this handler captures INFO level messages
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

# Add the file handler to the logger
logger.addHandler(file_handler)




def timelapse_diskspace(station_id):
   logger.info("Checking disk space for station: " + station_id)
   # figure out the values of disk space used by the timelapse programs
   # purge oldest files to make sure we don't go over maximum
   arc_dir = f"/mnt/ams2/meteor_archive/{station_id}/"

   # rules - delete jpgs that are >= 2 days old
   # keep - mp4 files unless total disk used is > 1 GB then delete
   folders_to_check = [arc_dir + "TL/PICS/", arc_dir + "TL/VIDS/", arc_dir + "TIME_LAPSE/"]
   
   for f in folders_to_check:
      # check disk usage of this folder
      res = subprocess.run(["du", "-sh", f], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
      # Check the exit status
      if res.returncode == 0:
         #print(res.stdout)
         files = glob.glob(f + "*") 
         for f in files:
            delete = False 
            # how old is this file
            file_time = os.path.getmtime(f)
            time_diff = datetime.now() - datetime.fromtimestamp(file_time)
           
            if os.path.isdir(f) :
               print(f"{f} is a dir", time_diff.days)
               subfiles = glob.glob(f + "/*")
               for sf in subfiles:
                  sub_time_diff = datetime.now() - datetime.fromtimestamp(os.path.getmtime(f))
                  if "jpg" in sf and sub_time_diff.days > 2:
                     delete = True
                  if "mp4" in sf and sub_time_diff.days > 30:
                     delete = True
                  if delete is True:
                     print("DEL", sf)
                     os.remove(sf)
               # delete folder if it is older than 30 days
               if time_diff.days > 30:
                  cmd = f"rm -rf {f}"
                  print(f"DEL FOLDER: {cmd}")
                  
            else:
               # delete any videos older than 90 days
               # delete any jpgs older than 2 days
               # delete any files that say "audit" older than 2 days
               if "mp4" in f and time_diff.days > 90:
                  delete = True
               elif "jpg" in f and time_diff.days > 2:
                  delete = True
               elif "audit" in f and time_diff.days > 2:
                  delete = True
               if delete is True:
                  print(f"Deleting {f}")
                  os.remove(f)
      else:
         print("Command failed!")
         print(res.stderr)
      


def aurora_fast(date, focus_cam = None, json_conf = None):
   snap_dir = "/mnt/ams2/SNAPS/" + date + "/360p/" 
   slow_stack_dir = "/mnt/ams2/meteor_archive/" + STATION_ID + "/AURORA/STACKS/" + date + "/" 

   rerun = 0
   if focus_cam is None:
      focus_cam = "cam2"
   cam_id_info, cam_num_info = load_cam_info(json_conf)
   data_file = TL_VIDEO_DIR + date + "-audit.json"

   fastest_data = []
   fast_data = []
   slow_data = []
   slowest_data = []
   #make_sd_snaps(date, json_conf, focus_cam)
   print(data_file)
   data = load_json_file(data_file)
   tl_frame_data = []
   final_data = []
   for h in range(0,24):
      for m in range(0,60):
            #play = "fastest"
            hour = str(h)
            MIN = str(m)
            for cam in cam_num_info:
               data[hour][MIN][cam]['play'] = "fastest"

               if float(data[hour][MIN][cam]['sun'][2]) <= -10 :
                  if len(data[hour][MIN][cam]['stack_file']) > 0:
                     stack_file = data[hour][MIN][cam]['stack_file'][0]
                     if rerun == 1: 
                        resp = detect_aurora(stack_file)
                        print("RUN DETECT!", hour, MIN, cam )
                        if resp != 0:
                           au,hist_img,marked_img = resp
                           data[hour][MIN][cam]['aurora'] = au

                        else:
                           au = {'detected': 0}


               if cam != focus_cam :
                  continue
               #print(h, m,cam)
               if 'aurora' in data[hour][MIN][cam]:
                  if data[hour][MIN][cam]['aurora']['detected'] == 1 and data[hour][MIN][cam]['aurora']['perm'] >0 :
                     #print(hour, MIN, cam, data[hour][MIN][cam]['aurora']['detected'])
                     slowest_data.append((hour,MIN,cam, data[hour][MIN][cam]['aurora']['area'], data[hour][MIN][cam]['stack_file'], data[hour][MIN][cam]['sd_file'], data[hour][MIN][cam]['hd_file']))
                     data[hour][MIN][cam]['play'] = "slowest"
                     #print("SLOWEST")
           
                     
                  elif data[hour][MIN][cam]['aurora']['detected'] == 1 : 
                     #print("SLOW", h,m)
                     slow_data.append((hour,MIN,cam, data[hour][MIN][cam]['aurora']['area'], data[hour][MIN][cam]['stack_file'], data[hour][MIN][cam]['sd_file'], data[hour][MIN][cam]['hd_file']))
                     data[hour][MIN][cam]['play'] = "slow"
                     print("SLOW", hour,MIN)
                  else:
                     fast_data.append((hour,MIN,cam, 0, data[hour][MIN][cam]['stack_file'], data[hour][MIN][cam]['sd_file'], data[hour][MIN][cam]['hd_file']))
                     #print(hour, MIN, cam, "FAST", data[hour][MIN][cam] )
                     data[hour][MIN][cam]['play'] = "fast"
                     #print("FAST")
               else:
                     #print(hour, MIN, cam, "FASTEST")
                     fastest_data.append((hour,MIN,cam, 0, data[hour][MIN][cam]['stack_file'], data[hour][MIN][cam]['sd_file'], data[hour][MIN][cam]['hd_file']))
                     data[hour][MIN][cam]['play'] = "fastest"
                     #print("FASTEST")
                    
   play_speed = {
      "cur": "fastest",
      "count": 0 
   }

   snap_dir = "/mnt/ams2/SNAPS/" + date + "/360p/" 
   final_files = []
   for h in range(0,24):
      for m in range(0,60):
         hour = str(h)
         MIN = str(m)
         if True:
            if True:
               cam = focus_cam
               play = data[hour][MIN][cam]['play']
               if len(data[hour][MIN][cam]['sd_file']) > 0:
                  sd_file = data[hour][MIN][cam]['sd_file'][0]
                  #print(hour, MIN, cam, play, sd_file )
                  if play_speed['cur'] != play:
                     last_play = play_speed['cur']
                     play_speed['cur'] = play

                     play_speed['count'] = 0
                  else:
                     play_speed['count'] += 1
                  if play_speed['count'] <= 10 and (play_speed['cur'] == 'fast' or play_speed['cur'] == 'fastest'):
                     play = last_play

                  if play == "slowest" or play == "slow":
                     fn,dir = fn_dir(sd_file)
                     ss_root = fn.replace(".mp4", "")
                     for i in range (0,1499):
                        if i % 10 == 0 and i > 0:
                           ss = ss_root + "-" + "{:04d}".format(i) + ".jpg"
                           slow_stack_file = slow_stack_dir + cam_num_info[cam] + "/" + ss 
                           #print("STACK:", slow_stack_file)
                           if i == 10: 
                              if cfe(slow_stack_file) == 1:
                                 #final_files.append(slow_stack_file)
                                 print("GOOD:", slow_stack_file)
                              else:
                                 print("MISSING SLOW STACK:", slow_stack_file)
                                 print("AURORA STACK:", sd_file)
                                 aurora_stack_vid(sd_file, json_conf)
                           if cfe(slow_stack_file) == 1:
                              fn,dir = fn_dir(slow_stack_file)
                              final_files.append((slow_stack_file,fn))
                     print("FINAL STACK", slow_stack_file) 
                  else:
                     hkey = '{:02d}'.format(h)
                     mkey = '{:02d}'.format(m)
                     snap_file = snap_dir + date + "_" + hkey + "_" + mkey + "_00_000_" + cam_num_info[cam] + ".jpg"
                     print("SNAP:", snap_dir, snap_file)
                     if cfe(snap_file) == 1:
                        
                        fn,dir = fn_dir(snap_file)
                        final_files.append((snap_file, fn))
                     else:
                        print("MISSING SNAP!:", snap_file )
                     print("FINAL SNAP ", snap_file) 

               else:
                  print("MISSING SD FILE:", hour, MIN, cam)
         #aurora_stack_vid(d[5][0], json_conf)
   list = ""
   dur = 1/25

   final_files = sorted(final_files, key=lambda x: x[1], reverse=False)
   for dfile in final_files:
      file, fn = dfile
      list += "file '" + file + "'\n"
      list += "duration " + str(dur) + "\n"
   au_vid_dir = "/mnt/ams2/meteor_archive/" + STATION_ID + "/AURORA/VIDS/"  
   au_vid_list = au_vid_dir + date + "_" + cam_num_info[focus_cam] + "_" + "list.txt"
   au_vid_file = au_vid_dir + date + "_" + cam_num_info[focus_cam] + "_SLOW_360p" + ".mp4"
   if cfe(au_vid_dir, 1) == 0:
      os.makedirs(au_vid_dir)
   fp = open(au_vid_list, "w") 
   fp.write(list)
   fp.close()
   print(au_vid_list)
   #exit()
   cmd = "/usr/bin/ffmpeg -f concat -safe 0 -i " + au_vid_list + " -c copy -y " + au_vid_file
   print(cmd)
   os.system(cmd)
   crf = au_vid_file.replace(".mp4", "-CRF20.mp4")
   width = "640"
   height = "360"
   cmd = "/usr/bin/ffmpeg -i " + au_vid_file + " -vcodec libx264 -crf 20 -vf 'scale=" + str(width) + ":" + str(height) + "' -y " + crf + " >/dev/null 2>&1"
   os.system(cmd)


def make_sd_snaps(date, json_conf,focus_cam=None):
   work_files = []
   cam_id_info, cam_num_info = load_cam_info(json_conf)
   data_file = TL_VIDEO_DIR + date + "-audit.json"
   data = load_json_file(data_file)
   snap_dir = "/mnt/ams2/SNAPS/" + date + "/360p/" 
   snap_dir = "/mnt/ams2/SNAPS/" + date + "/360p/" 
   if cfe(snap_dir) == 0:
      os.system("mkdir " + snap_dir)
   for h in range(0,24):
      print("Building file list for ", date, h)
      for m in range(0,60):
         hour = str(h)
         MIN = str(m)
         hkey = '{:02d}'.format(h)
         mkey = '{:02d}'.format(m)
         for cam in data[hour][MIN]:
            if focus_cam is not None:
               if cam != focus_cam:
                  continue
            if len(data[hour][MIN][cam]['sd_file']) > 0:
               sd_file = data[hour][MIN][cam]['sd_file'][0]
               fn,dir= fn_dir(sd_file)
               snap_fn = snap_dir + fn
               snap_fn = date + "_" + hkey + "_" + mkey + "_00_000_" + cam_num_info[cam] + ".jpg"
               snap_file = snap_dir + snap_fn
               if cfe(snap_file) == 0:              
                  work_files.append(sd_file)
            else:
               print("missing?", hour,MIN,data[hour][MIN][cam])

   for wf in sorted(work_files):
      print("TODO:", wf)

   print("Extracting images into", snap_dir)
   print("FILES LEFT:", len(work_files))
   extract_images(work_files, outdir=snap_dir)
   

def meteor_minutes(date):
   files = glob.glob("/mnt/ams2/meteors/" + date + "/*.json")
   meteors = {}
   for file in files:
      fn,dir = fn_dir(file)
      (sd_datetime, sd_cam, sd_date, sd_y, sd_m, sd_d, sd_h, sd_M, sd_s) = convert_filename_to_date_cam(file)
      key = '{:02d}-{:02d}'.format(sd_h,sd_m)
      if key not in meteors:
         meteors[key] = []
      meteors[key].append((sd_cam, fn))

def check_for_missing(min_file,cams_id,json_conf, missing = None):
   # DONT USE THIS ANYMORE
   missing = None
   cam_id_info, cam_num_info = load_cam_info(json_conf)
   print("LOOK FOR:", min_file)
   if missing is None:
      print("MISSING FILE LIST IS :", missing)
   else:
      print("MISSING FILE LIST IS :", len(missing))
   if missing is None:
      missing = []
      date = min_file[0:10] 
      hd_wild = "/mnt/ams2/HD/" + min_file + "*" + cams_id + "*.mp4"
      snap_wild = "/mnt/ams2/SNAPS/" + date + "/" + min_file  + "*" + cams_id  + "*.jpg"
      snap_wild2 = "/mnt/ams2/SNAPS/" + min_file  + "*" + cams_id + "*.png"
      sd_night = "/mnt/ams2/SD/proc2/" + date + "/"  + "*" + cams_id + min_file + "*.mp4"
      sd_day = "/mnt/ams2/SD/proc2/daytime/" + date + "/" + min_file  + "*" + cams_id + "*.mp4"
      sd_day2 = "/mnt/ams2/SD/proc2/daytime/" + min_file  + "*" + cams_id + "*.mp4"
      sd_pending = "/mnt/ams2/SD/" + min_file  + "*" + cams_id + "*.mp4"

      #min_file = min_file[0:10]
      #hd_wild = "/mnt/ams2/HD/" + min_file + "*." + cams_id + "*.mp4"
      #snap_wild = "/mnt/ams2/SNAPS/" + date + "/" + min_file  + "*" + cams_id  + "*.jpg"
      #snap_wild2 = "/mnt/ams2/SNAPS/" + min_file  + "*" + cams_id + "*.png"
      #sd_night = "/mnt/ams2/SD/proc2/" + date + "/"  + "*" + cams_id + min_file + "*.mp4"
      #sd_day = "/mnt/ams2/SD/proc2/daytime/" + date + "/" + min_file  + "*" + cams_id + "*.mp4"
      #sd_day2 = "/mnt/ams2/SD/proc2/daytime/" + min_file  + "*" + cams_id + "*.mp4"
      #sd_pending = "/mnt/ams2/SD/" + min_file  + "*" + cams_id + "*.mp4"



      for ff in glob.glob(hd_wild):
         missing.append(ff)
      for ff in glob.glob(snap_wild):
         missing.append(ff)
      for ff in glob.glob(snap_wild2):
         missing.append(ff)
      for ff in glob.glob(sd_night):
         missing.append(ff)
      for ff in glob.glob(sd_day):
         missing.append(ff)
      for ff in glob.glob(sd_day2):
         missing.append(ff)
      for ff in glob.glob(sd_pending):
         missing.append(ff)

      print("MISSING FILES AFTER GLOBS:", len(missing))
      time.sleep(5)

   # first check for pics
   for ms in missing:
      if "png" in ms or "jpg" in ms:
         # score use this file
         img = cv2.imread(ms)
         try:
            img = cv2.resize(img, (THUMB_W, THUMB_H))
            print("FOUND!", ms)
            return(img)
         except:
            print("Bad pic image.")
   # next check for vids
   for ms in missing:
      if "mp4" in ms:
         fn, dir = fn_dir(ms)
         mia_out = "/mnt/ams2/MIA/" + fn 
         mia_out = mia_out.replace(".mp4", ".png")
         if cfe(mia_out) == 1:
            img = cv2.imread(mia_out)
            if img.shape[0] != THUMB_H:
               img = cv2.resize(img, (THUMB_W, THUMB_H))
               cv2.imwrite(mia_out, img)
            return(img, missing)
         else:
            cmd = "/usr/bin/ffmpeg -ss 00:00:01.00 -i " + ms + " -frames:v 1 -y " + mia_out 
            print(cmd)
            os.system(cmd)
            img = cv2.imread(mia_out) 
            print("READING:", mia_out)
         try:
            img = cv2.resize(img, (THUMB_W, THUMB_H))
            return(img, missing)
         except:
            print("BAD FILE:", mia_out, missing)
            return(None, missing)



   return(None, missing)

def load_cam_info(json_conf):
   cam_num_info = {} 
   cam_id_info = {} 
   for cam in sorted(json_conf['cameras'].keys()):
      cams_id = json_conf['cameras'][cam]['cams_id']
      cam_id_info[cams_id] = cam
      cam_num_info[cam] = cams_id
   return(cam_id_info, cam_num_info)

def cv_plot_img(data, plot_img, color=[100,100,100]):
   w = len(data)
   print("DATA:", data)
   if plot_img is None:
      plot_img = np.zeros((256,w+1,3),dtype=np.uint8)
   x = 0
   for val in data:
      y2 = plot_img.shape[0] 
      y1 = y2 - val
      y2 = y1 + 1
      x1 = x 
      x2 = x+1 
      #print(y1,y2,x1,x2)
      for yy in range(y1,y2):
         for xx in range(x1,x2+1):
            plot_img[yy,xx] = color
      x = x + 1
   #cv2.imshow('graph', plot_img)
   #cv2.waitKey(0)
   return(plot_img)

def plot_min_int(date, json_conf):
   import matplotlib
   matplotlib.use('Agg')
   import matplotlib.pyplot as plt

   cam_id_info, cam_num_info = load_cam_info(json_conf)
   data_file = TL_VIDEO_DIR + date + "-audit.json"
   data = load_json_file(data_file)
   sum_ints = {}
   avg_ints = {}
   green_ints = {}
   blue_ints = {}
   red_ints = {}
   for cn in cam_num_info:
      sum_ints[cn] = []
      avg_ints[cn] = []
      green_ints[cn] = []
      blue_ints[cn] = []
      red_ints[cn] = []
   for hour in data:
      for minute in data[hour]:
         for cam in data[hour][minute]:
            print("AVG INT:", hour, minute, cam, data[hour][minute][cam]['avg_int'])
            sum_ints[cam].append(data[hour][minute][cam]['sum_int'] / 100000)
            avg_ints[cam].append(data[hour][minute][cam]['avg_int'])
            blue_ints[cam].append(data[hour][minute][cam]['color_int'][0])
            green_ints[cam].append(data[hour][minute][cam]['color_int'][1])
            red_ints[cam].append(data[hour][minute][cam]['color_int'][2])
   plot_img = None
   colors = [[0,0,200], [0,200,0], [200,0,0], [200,200,0],[0,200,200],[200,0,200], [200,200,200]]
   cc = 0
   for cam in sum_ints:
      xs = sum_ints[cam] 
      ys = avg_ints[cam]
      greens = green_ints[cam]
      reds  = red_ints[cam]
      blues  = blue_ints[cam]
      # plt.plot(xs)
      #plt.plot(ys)
      #plot_img = cv_plot_img(greens, plot_img, colors[cc])
      plot_img = cv_plot_img(greens, plot_img, [50,100,50])
      cc += 1
   save_file = data_file.replace("-audit.json", "-intensity.png")
   #plt.savefig(save_file)
   cv2.imwrite(save_file, plot_img)
   print(save_file)
   #plt.show()

def layout_template(date, json_conf):
   layout = [
      {
         "position": 1, 
         "x1": 0, 
         "y1": 0, 
         "x2": 640, 
         "y2": 360, 
         "dim": [640,360] 
      },
      {
         "position": 2, 
         "x1": 640, 
         "y1": 0, 
         "x2": 1280, 
         "y2": 360, 
         "dim": [640,360] 
      },
      {
         "position": 3, 
         "x1": 1280, 
         "y1": 0, 
         "x2" : 1920, 
         "y2": 360, 
         "dim": [640,360] 
      },
      {
         "position": 4, 
         "x1": 0, 
         "y1": 360, 
         "x2": 640, 
         "y2": 720, 
         "dim": [640,360] 
      },
      {
         "position": 5, 
         "x1": 640, 
         "y1": 360, 
         "x2": 1280, 
         "y2": 720, 
         "dim": [640,360] 
      },
      {
         "position": 6, 
         "x1": 1280, 
         "y1": 360, 
         "x2": 1920, 
         "y2": 720, 
         "dim": [640,360] 
      },
   ]
   return(layout)

def audit_min(date, json_conf):
   # audit min files
   # build index and make sure all files exist
   # make quick preview of all minutes as 1 row

   os.system("clear")
   mm = 0
   print("\rLoading camera info.", end="")
   cam_id_info, cam_num_info = load_cam_info(json_conf)
   # check the files that could be missig and why
   if os.path.exists(TL_VIDEO_DIR  ) is False:
      os.makedirs(TL_VIDEO_DIR  )
   data_file = TL_VIDEO_DIR + date + "-audit.json"

   print(f"\rLoading data file {data_file}." + " " * 50, end="")
   if cfe(TL_IMAGE_DIR + date, 1) == 0 :
      os.makedirs(TL_IMAGE_DIR + date)
   if cfe(data_file) == 0:
      data = {}
      new = 1
   else: 
      print(f"\rLoading {data_file} please wait..." + " " * 50, end="")
      data = load_json_file(data_file)
      new = 0
   #minutes = load_json_file(data_file)
   today = datetime.now().strftime("%Y_%m_%d")
   if today == date :
      limit_h = int(datetime.now().strftime("%H"))
      limit_m = int(datetime.now().strftime("%M"))
   else :
      limit_h = 23
      limit_m = 59

   hd_files = glob.glob("/mnt/ams2/HD/" + date + "*.mp4")
   sd_files = glob.glob("/mnt/ams2/SD/proc2/" + date + "/*.mp4")
   sd_day_files = glob.glob("/mnt/ams2/SD/proc2/daytime/" + date + "/*.mp4")
   sd_queue_files = glob.glob("/mnt/ams2/SD/" + date + "*.mp4")
   print("\rLoading daytime queue files." + " " * 50, end="")
   sd_day_queue_files = glob.glob("/mnt/ams2/SD/proc2/daytime/" + date + "*.mp4")
   # will need to fix later.
   print("\rLoading snap files.", end="" )
   snap_files= glob.glob("/mnt/ams2/SNAPS/" + date + "*.png")
   print("\rLoading meteor files." + " " * 50, end="" )

   mfiles = glob.glob("/mnt/ams2/meteors/" + date + "/*.json")
   detect_files = glob.glob("/mnt/ams2/SD/proc2/" + date + "/hd_save/*.mp4")
   meteor_files = []
   for mf in mfiles:
      if "reduced" not in mf and "stars" not in mf and "man" not in mf:
         meteor_files.append(mf)
   #snap_jpg_files= glob.glob("/mnt/ams2/SNAPS/" + date + "*.jpg")
   total_cams = len(json_conf['cameras'].keys())
   today = datetime.now().strftime("%Y_%m_%d")
   yesterday = (datetime.now() - dt.timedelta(days = 1)).strftime("%Y_%m_%d")
   if today == date : 
      limit_h = int(datetime.now().strftime("%H"))
      limit_m = int(datetime.now().strftime("%M"))
   else :
      limit_h = 23
      limit_m = 59

   if True:
      for h in range(0,24):
         print(f"\rHour: {h}" + " " * 50, end='', flush=True)
         hs = str(h)
         if hs not in data :
            data[hs] = {}
         #if h <= limit_h:
         if True:
            for m in range(0,60):
               ms = str(m)
               #if h == limit_h:
               #   if m > limit_m:
               #      continue
               if ms not in data[hs] :
                  data[hs][ms] = {}
               for cam in cam_num_info:
                  f_date_str = date + " " + str(h) + ":" + str(m) + ":00" 
                  f_date_str = f_date_str.replace("_", "/")
                  if cam not in data[hs][ms]:
                     sun_status, sun_az, sun_el = day_or_night(f_date_str, json_conf,1)
                     print(f"\r{hs} {ms} {cam} {sun_status} {sun_az} {sun_el}", end='', flush=True)
                     data[hs][ms][cam] = {}
                     data[hs][ms][cam]['cam_num'] = cam
                     data[hs][ms][cam]['id'] = cam_num_info[cam]
                     data[hs][ms][cam]['sd_file'] = []
                     data[hs][ms][cam]['hd_file'] = []
                     data[hs][ms][cam]['snap_file'] = []
                     data[hs][ms][cam]['stack_file'] = []
                     data[hs][ms][cam]['meteors'] = []
                     data[hs][ms][cam]['detects'] = []
                     data[hs][ms][cam]['weather'] = []
                     data[hs][ms][cam]['sun'] = [sun_status, sun_az, sun_el]
                     data[hs][ms][cam]['sum_int'] = 0
                     data[hs][ms][cam]['avg_int'] = 0
                     data[hs][ms][cam]['color_int'] = []
                  else:
                     sun_status, sun_az, sun_el = day_or_night(f_date_str, json_conf,1)
                     #print("E:", hs, ms, cam, sun_status, sun_az, sun_el)
                     print(f"\r{hs} {ms} {cam} {sun_status} {sun_az} {sun_el}", end='', flush=True)
                     data[hs][ms][cam]['sd_file'] = []
                     data[hs][ms][cam]['hd_file'] = []
                     data[hs][ms][cam]['snap_file'] = []
                     data[hs][ms][cam]['stack_file'] = []
                     data[hs][ms][cam]['meteors'] = []
                     data[hs][ms][cam]['detects'] = []
                     data[hs][ms][cam]['weather'] = []
                     data[hs][ms][cam]['sun'] = [sun_status, sun_az, sun_el]

   print("\rLooping HD Files" + " " * 50, end='', flush=True)
   for file in sorted(hd_files):
      (sd_datetime, sd_cam, sd_date, sd_y, sd_m, sd_d, sd_h, sd_M, sd_s) = convert_filename_to_date_cam(file)
      if "trim" not in file:

         cam_num = cam_id_info[sd_cam]
         sd_h = str(int(sd_h))
         sd_M = str(int(sd_M))
         data[sd_h][sd_M][cam_num]['hd_file'].append(file)

   print("\rLooping SD Night Files" + " " * 60, end='', flush=True)
   for file in sorted(sd_files):
      fn, dir = fn_dir(file)
      (sd_datetime, sd_cam, sd_date, sd_y, sd_m, sd_d, sd_h, sd_M, sd_s) = convert_filename_to_date_cam(file)
      if "trim" not in file:
         cam_num = cam_id_info[sd_cam]
         sd_h = str(int(sd_h))
         sd_M = str(int(sd_M))
         data[sd_h][sd_M][cam_num]['sd_file'].append(file)
         stack_file = dir + "images/" + fn
         stack_file = stack_file.replace(".mp4", "-stacked-tn.jpg")
         #if cfe(stack_file) == 0:
         #   stack_file = stack_file.replace(".png", ".jpg")
         #   if cfe(stack_file) == 0:
         #      print(f"\rMISSING: {stack_file}" + " " * 50, end="")
         show_file = stack_file.split("-")[0].split("/")[-1]
         if stack_file not in data[sd_h][sd_M][cam_num]['stack_file']:
            if os.path.exists(stack_file) is True:
               print(f"\rNight : {stack_file}" + " " * 50, end="")
               data[sd_h][sd_M][cam_num]['stack_file'].append(stack_file)
         else:
            print(f"\rDone : {show_file}" + " " * 50, end="")
            


   print("\rLooping SD DAY Files     " + " " * 60 , end='')
   current_date = datetime.now()
   for file in sorted(sd_day_files):
      (sd_datetime, sd_cam, sd_date, sd_y, sd_m, sd_d, sd_h, sd_M, sd_s) = convert_filename_to_date_cam(file)
      if sd_datetime > current_date :
         #print("Time in future skip!")
         #print(current_date, sd_datetime, type(current_date), type(sd_datetime))
         #input()
         continue
      fn, dir = fn_dir(file)
      if "trim" not in file:
         cam_num = cam_id_info[sd_cam]
         sd_h = str(int(sd_h))
         sd_M = str(int(sd_M))
         stack_file = dir + "images/" + fn
         stack_file = stack_file.replace(".mp4", "-stacked-tn.jpg")
         show_file = stack_file.split("-")[0].split("/")[-1]
         if stack_file not in data[sd_h][sd_M][cam_num]['stack_file']:
            if os.path.exists(stack_file) == 1:
                print(f"\rDay : {stack_file}" + " " * 50, end="")
                data[sd_h][sd_M][cam_num]['stack_file'].append(stack_file)
            else:
                print(f"\rMissing : {stack_file}" + " " * 50, end="")
         else:
            print(f"\rDay Done : {stack_file}" + " " * 50, end="")
         data[sd_h][sd_M][cam_num]['sd_file'].append(file)
   print("\rLooping SD DAY QUEUE Files" + " " * 50, end="")
   for file in sorted(sd_day_queue_files):
      (sd_datetime, sd_cam, sd_date, sd_y, sd_m, sd_d, sd_h, sd_M, sd_s) = convert_filename_to_date_cam(file)
      if "trim" not in file:
         cam_num = cam_id_info[sd_cam]
         sd_h = str(int(sd_h))
         sd_M = str(int(sd_M))
         data[sd_h][sd_M][cam_num]['sd_file'].append(file)
   for file in sorted(sd_queue_files):
      (sd_datetime, sd_cam, sd_date, sd_y, sd_m, sd_d, sd_h, sd_M, sd_s) = convert_filename_to_date_cam(file)
      if "trim" not in file:
         cam_num = cam_id_info[sd_cam]
         sd_h = str(int(sd_h))
         sd_M = str(int(sd_M))
         data[sd_h][sd_M][cam_num]['sd_file'].append(file)
   for file in sorted(snap_files):
      (sd_datetime, sd_cam, sd_date, sd_y, sd_m, sd_d, sd_h, sd_M, sd_s) = convert_filename_to_date_cam(file)
      if "trim" not in file:
         cam_num = cam_id_info[sd_cam]
         sd_h = str(int(sd_h))
         sd_M = str(int(sd_M))
         data[sd_h][sd_M][cam_num]['snap_file'].append(file)
   for file in sorted(meteor_files):
      (sd_datetime, sd_cam, sd_date, sd_y, sd_m, sd_d, sd_h, sd_M, sd_s) = convert_filename_to_date_cam(file)
      if "trim" not in file:
         cam_num = cam_id_info[sd_cam]
         sd_h = str(int(sd_h))
         sd_M = str(int(sd_M))
         data[sd_h][sd_M][cam_num]['meteors'].append(file)
   for file in sorted(detect_files):
      (sd_datetime, sd_cam, sd_date, sd_y, sd_m, sd_d, sd_h, sd_M, sd_s) = convert_filename_to_date_cam(file)
      if "trim" not in file:
         cam_num = cam_id_info[sd_cam]
         sd_h = str(int(sd_h))
         sd_M = str(int(sd_M))
         data[sd_h][sd_M][cam_num]['detects'].append(file)

   save_json_file(data_file, data)
   # update the intensity per minute and make the row pic
   TL_PIC_DIR = TL_IMAGE_DIR + date + "/"
   for hour in range(0,24):
       for minute in range(0,60):
         if hour > limit_h:
            continue
         if hour == limit_h:
            if minute >= limit_m:
               continue
         key = '{:02d}-{:02d}'.format(int(hour),int(minute))
         hs = str(hour)
         ms = str(minute)

         row_file = TL_PIC_DIR + key + "-row.png"
         show_file = row_file.split("-")[0].split("/")[-1]
         print(f"\rROW: {show_file}" + " " * 60, end="")
         redo = 0
         #if cfe(row_file) == 1:
         #   fs = os.stat(row_file)
         #   fsize = fs.st_size
         #   if fsize < 4000:
         #      redo = 1
         #      os.system("rm " + row_file)


         if os.path.exists(row_file) == 0 or redo == 1:
            min_file = None
            row_pic = make_row_pic(data[hs][ms], min_file, LOCATION + " " + date + " " + key.replace("-", ":") + " UTC", json_conf, cam_num_info)
            cv2.imwrite(row_file, row_pic)

         # try to detect aurora
         # maybe we can disable this.
         #for cam in data[hs][ms]:
         if False:
            stack_files = data[hs][ms][cam]['stack_file']
            sum_int = 0
            avg_int = 0
            color_int = [0,0,0]
            if len(stack_files) > 0:
               stack_file = stack_files[0]
            else:
               stack_file = None
            #if (cfe(stack_file) == 1 and data[hs][ms][cam]['sum_int'] == 0) or "aurora" not in data[hs][ms][cam]:
            if stack_file is not None:
               timg = cv2.imread(stack_file)
               #print(f"\rSUN: {hs}, {ms}, {cam}, {data[hs][ms][cam]['sun']}", end="" )
               if float(data[hs][ms][cam]['sun'][2]) <= -10 :
                  resp = detect_aurora(stack_file)
                  #print(f"\rRUN AURORA DETECT! {hs}, {ms}, {cam}, {stack_file}", end="")
                  if resp != 0:
                     au,hist_img,marked_img = resp
                  else:
                     au = {'detected': 0}

                  if au['detected'] == 1:
                     au_file = stack_file.replace("-stacked-tn.png", "-au-tn.jpg")
                     #html += "<img src=" + au_file + "><br>"
                     if cfe(au_file) == 0:
                        cv2.imwrite(au_file, marked_img)
                        #print(f"\rAUROA: {au_file}", end="")

               else:
                   au = { "detected": 0}
               try:
                  sum_int = int(np.sum(timg))
                  avg_int = int(np.mean(timg))
                  ci_b = int(np.mean(timg[0]))
                  ci_g = int(np.mean(timg[1]))
                  ci_r = int(np.mean(timg[2]))
                  data[hs][ms][cam]['aurora'] = au
                  data[hs][ms][cam]['sum_int'] = sum_int
                  data[hs][ms][cam]['avg_int'] = avg_int
                  data[hs][ms][cam]['color_int'] = [ci_b, ci_g, ci_r]
               except:
                  data[hs][ms][cam]['aurora'] = au
                  data[hs][ms][cam]['sum_int'] = 0 
                  data[hs][ms][cam]['avg_int'] = 0 
                  data[hs][ms][cam]['color_int'] = [0, 0, 0]
      
   save_json_file(data_file, data)

   print("Saved data file.", data_file)
   html = """
   <script>
   function show_hide(div_id) {
      var x = document.getElementById(div_id);
      if (x.style.display === "none") {
         x.style.display = "block";
      } else {
         x.style.display = "none";
      }
   }
   </script>
   """
   # find uptime
   updata = {}
   uptime_percs = []
   for hour in range(0,24):
      if hour not in updata:
         updata[hour] = {}
         updata[hour]['tfiles'] = 0
      if int(hour) <= int(limit_h):
         for min in range(0,60):
            if hour == limit_h and min >= limit_m:
               continue
            hs = str(hour)
            ms = str(minute)
            for cam in data[hs][ms]:
               tfiles = len(data[hs][ms][cam]['sd_file']) + len(data[hs][ms][cam]['hd_file'])
               updata[hour]['tfiles'] += tfiles

   for r_hour in range(0,24):
      s_hour = 23 - r_hour 
      if int(s_hour) <= int(limit_h):
         if html != "":
            html += str(s_hour) + "</table>"
         if s_hour == limit_h: 
            tot_m = limit_m 
         else:
            tot_m = 60
         uptime_perc = str((updata[hour]['tfiles'] / (tot_m*total_cams*2) * 100))[0:5]
         uptime_percs.append((hour,uptime_perc)) 
         html += " " + str(updata[hour]['tfiles']) + " files of " +  str(tot_m*total_cams*2) + " expected. " + uptime_perc + "% uptime "
         div_id = str(r_hour)
         html += "<div id='" + div_id + "' style='display: none'>"
         html += "<table border=1>"
         for r_min in range(0,60):
            s_min = 59 - r_min 
            if s_hour == limit_h and s_min >= limit_m:
               continue
            html += "<tr><td> " + str(s_hour) + ":" + str(s_min) + "</td>"
            hs = str(s_hour)
            ms = str(s_min)

            html += "<td>" + str(data[hs][ms][cam]['sun']) + "</td><td>" 
            for cam in data[hs][ms]:
            
               html += "<td>"
               if len(data[hs][ms][cam]['sd_file']) == 0:
                  html += "<font color=red>X</font> "
               else:
                  html += "<font color=green>&check;</font> " #+ str(data[hour][min][cam]['sd_file'])
               if len(data[hs][ms][cam]['stack_file']) > 0:
                  jpg = data[hs][ms][cam]['stack_file'][0].replace(".png", ".jpg")
                  if cfe(jpg) == 0:
                     cmd = "convert -quality 80 " + data[hs][ms][cam]['stack_file'][0] + " " + jpg 
                     print(cmd)
                     os.system(cmd)

                  #html += "<img src=" + data[hour][min][cam]['stack_file'][0] + ">"
                  url = jpg.replace("-stacked-tn.jpg", ".mp4")
                  url = url.replace("images/", "")
                  jpg = jpg.replace("/mnt/ams2", "")
                  url = url .replace("/mnt/ams2", "")
                  html += "<a href=" + url + "><img src=" + jpg + "></a><br>" + str(data[hs][ms][cam]['color_int'])
               else:
                  if len(data[hs][ms][cam]['hd_file']) == 0:
                     html += "<font color=red>X</font>"
                  else:
                     html += "<font color=green>&check;</font> "
               html += "</td>"
            html += "</tr>"
         html += "</table>"
         html += "</div>"
         html += "<a href=\"javascript: show_hide('" + div_id + "')\">Show/Hide " + div_id + "</a>" + str(data[hs][ms][cam]['sun']) + "<br>"

   html_file = data_file.replace(".json", ".html")
   out = open(html_file, "w")
   out.write(html)
   print(html_file)
   cloud_dir = "/mnt/archive.allsky.tv/" + STATION_ID + "/LOGS/"  
   if cfe(cloud_dir, 1) == 0:
      try:
         os.makedirs(cloud_dir)
      except:
         print("Perms?") 
   outfile = cloud_dir + date + "_" + STATION_ID + "_uptime.json"
   up_data = {}
   up_data['uptime'] = uptime_percs
   save_json_file(outfile, up_data)
   print("Saved:", outfile)

   iwild = TL_PIC_DIR = TL_IMAGE_DIR + date + "/*.png"
   tl_out = TL_VIDEO_DIR + date + "_row_tl.mp4"
   cmd = "/usr/bin/ffmpeg -framerate 12 -pattern_type glob -i \"" + iwild + "\" -c:v libx264 -pix_fmt yuv420p -y " + tl_out
   print(cmd)
   os.system(cmd)
   print(tl_out)
   make_tl_html()
   #sync_tl_vids()
 

def multi_cam_tl(date):
   ma_dir = "/mnt/ams2/meteor_archive/"
   tmp_dir = "/home/ams/tmp_vids/" 
   # RSYNC NETWORK SITES
   print(NETWORK_STATIONS)
   for st in NETWORK_STATIONS:
      if st == STATION_ID:
         continue
      arc_dir = "/mnt/archive.allsky.tv/" + st + "/TL/VIDS/" 
      local_dir = "/mnt/ams2/meteor_archive/" + st + "/TL/VIDS/" 
      if cfe(local_dir,1) == 0:
         os.makedirs(local_dir)
      cmd = "/usr/bin/rsync -av " + arc_dir + " " + local_dir
      print(cmd)
      #os.system(cmd)
   #exit()

   station_str = ""
   os.system("rm -rf " + tmp_dir + "/*")
   for station in NETWORK_STATIONS:
      print("DOING STATION:", station)
      video_file = ma_dir + station + "/TL/VIDS/" + date + "_row_tl.mp4"
      print(video_file)
      if cfe(video_file) == 0:
         print("NOT FOUND:", video_file)
         exit()
      station_str += station
      tt = tmp_dir + station + "/"
      if cfe(tt, 1) == 0:
         os.makedirs(tt)
      cmd = "/usr/bin/ffmpeg -i " + video_file + " " + tt + "frames%04d.png > /dev/null 2>&1"
      print(cmd)
      os.system(cmd)

   TID = NETWORK_STATIONS[0]  
   frames1 = glob.glob(tmp_dir + NETWORK_STATIONS[0] + "/*.png")
   print("DIR:", tmp_dir + NETWORK_STATIONS[0] + "/*.png")
   mc_out_dir = tmp_dir + "/MC/"
   final_out = "/mnt/ams2/meteor_archive/TL/" + date + "_" + station_str + ".mp4"
   if cfe(mc_out_dir, 1) == 0:
      os.makedirs(mc_out_dir)
   for frame in sorted(frames1):
      fn,dir = fn_dir(frame)
      print("FILE:", frame)
      mc_img = make_multi_cam_frame(frame, TID)
      cv2.imwrite(mc_out_dir + fn , mc_img)
   iwild = mc_out_dir + "*.png"
   cmd = "/usr/bin/ffmpeg -framerate 12 -pattern_type glob -i '" + iwild + "' -c:v libx264 -pix_fmt yuv420p -y " + final_out + " >/dev/null 2>&1"
   print(cmd)
   os.system(cmd)
   print("FINAL:", final_out)

def make_tl_html():
   print("MAKE HTML")
   TL_CLOUD_DIR = "/mnt/archive.allsky.tv/" + STATION_ID + "/TL/VIDS/"
   if os.path.exists(TL_CLOUD_DIR) is False:
      os.makedirs(TL_CLOUD_DIR) 
 
   html = "<h1>Time Lapse and Audits for " + STATION_ID + "</h1>"      
   html += "<p>Last updated:" + datetime.now().strftime("%Y_%m_%d") + "</p><ul>"
   vids = glob.glob(TL_VIDEO_DIR + "*.mp4")
   rsync_cmd = f"rsync -auv {TL_VIDEO_DIR}/*.mp4 {TL_CLOUD_DIR}"

   for vid in sorted(vids,reverse=True):
      
      vid_fn, vdir = fn_dir(vid)
      vid_desc = vid_fn[0:10]
      audit_fn = vid_fn.replace("_row_tl.mp4", "-audit.html")
      html += "<li>" + vid_desc + " - <a href=" + vid_fn + ">" + " Row Timelapse</a>" + " <!-- <a href=" + audit_fn + ">Audit</a>--></li>"
   html += "</ul>"
   oo = open(TL_VIDEO_DIR + "index.html", "w")
   oo.write(html)
   oo.close()
   print("saved:", TL_VIDEO_DIR + "index.html")
   try:
      TL_CLOUD_FILE = "/mnt/archive.allsky.tv/" + STATION_ID + "/TL/VIDS/index.html"
      oo = open(TL_CLOUD_FILE, "w")
      oo.write(html)
      oo.close()
   except:
      print("Cloud drive not connected.")
   cl_url = TL_CLOUD_FILE.replace("/mnt/", "https://")
   print(f"Audit file and time lapse saved on cloud here: {cl_url}")
   print(rsync_cmd)
   os.system(rsync_cmd)

def make_multi_cam_frame(frame, TID):
   mc_img = np.zeros((1080,1920,3),dtype=np.uint8)

   rc = 0
   for TS in NETWORK_STATIONS:
      TF = frame.replace(TID, TS)
      print("THIS FILE:", TF)
      img = cv2.imread(TF) 
      try:
         img = cv2.resize(img, (1920, 180))
      except:
         img = np.zeros((180,1920,3),dtype=np.uint8)

      ih,iw = img.shape[:2]
      y1 = (ih * rc)
      y2 = (y1+ih)
      mc_img[y1:y2,0:iw] = img
      rc += 1      
   #mc_img = cv2.resize(mc_img, (1280, 720))
   #cv2.imshow('MC', mc_img)
   #cv2.waitKey(30)   
   return(mc_img)
    
def purge_tl():
   # remove files older than 2 days from the MIA dir
   # remove folders older than 3 days from the TL pic dir
   MIA_DIR = "/mnt/ams2/MIA/"
   files = glob.glob(MIA_DIR + "*")
   tl_pic_dirs = glob.glob(TL_IMAGE_DIR + "*")
   for tld in tl_pic_dirs:
      fn, dir = fn_dir(tld)
      dir_date = datetime.strptime(fn, "%Y_%m_%d")
      elp = dir_date - datetime.now()
      days_old = abs(elp.total_seconds()) / 86400
      print(fn, days_old)
      if days_old > 3:
         cmd = "rm -rf " + tld
         print(cmd)
         os.system(cmd)


   for file in files:
      (sd_datetime, sd_cam, sd_date, sd_y, sd_m, sd_d, sd_h, sd_M, sd_s) = convert_filename_to_date_cam(file)
      elp = sd_datetime - datetime.now()
      days_old = abs(elp.total_seconds()) / 86400
      if days_old > 2:
         #print(file, days_old)
         cmd = "rm " + file
         #print(cmd)
         os.system(cmd)


def sync_tl_vids():
   CLOUD_TL_VIDEO_DIR = TL_VIDEO_DIR.replace("ams2/meteor_archive", "archive.allsky.tv")
   if cfe(CLOUD_TL_VIDEO_DIR, 1) == 0:
      os.makedirs(CLOUD_TL_VIDEO_DIR)
   cmd = "/usr/bin/rsync -av " + TL_VIDEO_DIR + "*.mp4 " + CLOUD_TL_VIDEO_DIR 
   print(cmd)
   os.system(cmd)

def make_file_matrix(day,json_conf):
   today = datetime.now().strftime("%Y_%m_%d")
   if day == today:
      last_hour =  int(datetime.now().strftime("%H")) + 1
   else:
      last_hour = 24
   file_matrix = {}
   #sec_bin = [0,30]
   for hour in range (0, last_hour):
      for min in range(0,60):
         key = '{:02d}-{:02d}'.format(hour,min)
         file_matrix[key] = {}
         file_matrix[key]
         for cam in sorted(json_conf['cameras'].keys()):
            file_matrix[key][cam] = ""


   return(file_matrix)


def tn_tl6(date,json_conf):

   purge_tl()
   TL_PIC_DIR = TL_IMAGE_DIR + date + "/"
   day_dir = "/mnt/ams2/SD/proc2/daytime/" + date + "/images/*.png"
   night_dir = "/mnt/ams2/SD/proc2/" + date + "/images/*.png"
   day_files = glob.glob(day_dir)
   night_files = glob.glob(night_dir)
   print("D", len(day_files))
   print("N", len(night_files))
   all_files = []
   for file in sorted(day_files):
      all_files.append(file)
   for file in sorted(night_files):
      all_files.append(file)
   for file in all_files:
      print(file)

   matrix = make_file_matrix(date,json_conf)
   if cfe("tmp_vids", 1) == 0:
      os.makedirs("tmp_vids")
   if cfe(TL_VIDEO_DIR, 1) == 0:
      os.makedirs(TL_VIDEO_DIR)
   if cfe(TL_PIC_DIR, 1) == 0:
      os.makedirs(TL_PIC_DIR)

   cam_id_info = {}
   default_cams = {}
   last_best = {}
   for cam in sorted(json_conf['cameras'].keys()):
      cams_id = json_conf['cameras'][cam]['cams_id']
      cam_id_info[cams_id] = cam
      default_cams[cam] = ""
      last_best[cam] = ""

   for file in sorted(all_files):
      if "night" in file:
         continue
      fn, dir = fn_dir(file)
      (sd_datetime, sd_cam, sd_date, sd_y, sd_m, sd_d, sd_h, sd_M, sd_s) = convert_filename_to_date_cam(file)
      key = '{:02d}-{:02d}'.format(int(sd_h),int(sd_M))
      if key not in matrix:
         matrix[key] = {}
         for cam in sorted(json_conf['cameras'].keys()):
            matrix[key][cam] = ""
 
      cid = cam_id_info[sd_cam]
      matrix[key][cid] = file

   # fill in missing frames 
   #for key in matrix:
   #   for cid in matrix[key]:
   #      if matrix[key][cid] == "":
   #         if last_best[cid] != "":
   #            matrix[key][cid] == last_best[cid]
   #      else:
   #         last_best[cid] = matrix[key][cid]

   data_file = TL_VIDEO_DIR + date + "-minutes.json"
   save_json_file(data_file, matrix)
   #os.system("rm tmp_vids/*")
   new = 0
   cam_id_info, cam_num_info = load_cam_info(json_conf)

   row_files = glob.glob(TL_PIC_DIR + "*row.png")
   for key in sorted(matrix.keys()):
      row_file = TL_PIC_DIR + key + "-row.png"
      row_file_tmp = TL_PIC_DIR + key + "-row_lr.jpg"
      redo = 0
      if row_file in row_files:
         fs = os.stat(row_file)
         fsize = fs.st_size
         if fsize < 4000:
            redo = 1
            exit()
      if row_file in row_files or redo == 1:
      #if True:
         if redo == 1:
            print("REDO!")
         h,m =key.split("-")
         min_file = date + "_" + h + "_" + m
         print(key, matrix[key])
         row_pic = make_row_pic(matrix[key], min_file, LOCATION + " " + date + " " + key.replace("-", ":") + " UTC", json_conf, cam_num_info)
         cv2.imwrite(row_file, row_pic)
         cmd = "convert -quality 80 " + row_file + " " + row_file_tmp
         os.system(cmd)
         #cmd = "mv " + row_file_tmp + " " + row_file
         #os.system(cmd)
         new += 1

   if new > 0:
      iwild = TL_PIC_DIR + "*-row.png"
      tl_out = TL_VIDEO_DIR + date + "_row_tl.mp4"
      tl_out_lr = TL_VIDEO_DIR + STATION_ID + "_" + date + "_row_tl_lr.mp4"
      #cmd = "/usr/bin/ffmpeg -framerate 12 -pattern_type glob -i '" + iwild + "' -c:v libx264 -pix_fmt yuv420p -y " + tl_out + " >/dev/null 2>&1"
      cmd = "/usr/bin/ffmpeg -framerate 12 -pattern_type glob -i \"" + iwild + "\" -c:v libx264 -pix_fmt yuv420p -y " + tl_out 
      print(cmd)
      os.system(cmd)
      #cmd = "/usr/bin/ffmpeg -i " + tl_out + " -vcodec libx264 -crf 30 -y " + tl_out_lr 
      # print(cmd)
      #os.system(cmd)
      #os.system("mv " + tl_out_lr + " " + tl_out)
      sync_tl_vids()
   else:
      print("No sync. nothing new?", new)
   make_tl_html()

      

def make_row_pic(data, min_file, text, json_conf, cam_num_info):
   default_w = 300
   default_h = 168
   imgs = [] 
   missing = None
   for cam in sorted(data.keys()):
      stack_files = data[cam]['stack_file']
      if len(stack_files) > 0:
         file = stack_files[0]
      else:
         file = ""
      cams_id = cam_num_info[cam]
      if file != "":
         img = cv2.imread(file)
      else:
         img = np.zeros((default_h,default_w,3),dtype=np.uint8)
      img = cv2.resize(img, (default_w, default_h))
      imgs.append(img)
   h,w = imgs[0].shape[:2]
   rw = w * len(data.keys())
   blank_image = np.zeros((h,rw,3),dtype=np.uint8)
   x = 0
   y = 0 
   ic = 0
   for img in imgs:
      x1 = x + (ic * w)
      x2 = x1 + w
      blank_image[y:y+h,x1:x2] = img
      ic += 1
   #cv2.imshow('row', blank_image)
   #cv2.waitKey(30)
   cv2.putText(blank_image, str(text),  (7,165), cv2.FONT_HERSHEY_SIMPLEX, .3, (25, 25, 25), 1)
   cv2.putText(blank_image, str(text),  (6,164), cv2.FONT_HERSHEY_SIMPLEX, .3, (140, 140, 140), 1)
   return(blank_image)

def timelapse_all(date, json_conf):


   for cam in json_conf['cameras']:
      cams_id = json_conf['cameras'][cam]['cams_id']
      make_tl_for_cam(date, cams_id, json_conf)

def make_tl_for_cam(date,cam, speed, json_conf):
   station_id = json_conf['site']['ams_id']
   hd_dir = "/mnt/ams2/HD/"
   snap_dir = hd_dir + "snaps/"
   cmd = f"./Process.py hd_snaps /mnt/ams2/HD/ {date} {cam}"
   print(cmd)
   os.system(cmd)

   print("OK")
   
   if os.path.exists(snap_dir) is False:
      os.makedirs(snap_dir)
   files = glob.glob(hd_dir + date + "*" + cam + "*.mp4")
   tl_dir = TL_DIR + date + "/"

   print("FILES:", files)

   if cfe(tl_dir, 1) == 0:
      os.makedirs(tl_dir)
   for file in sorted(files):
      if "trim" not in file:
         fn = file.split("/")[-1]
         out_file = tl_dir + fn.replace(".mp4", ".jpg")
         #out_file = hd_dir + "snaps/" + fn.replace(".mp4", ".jpg")
         if os.path.exists(out_file) is False:
            image, image_file = quick_video_stack(file, speed)
         #try:
         #except:
         #   continue
     
         #rot_image = rotate_bound(image, 72)
         #img_sm = cv2.resize(rot_image, (640, 360))
         #cv2.imshow('pepe', img_sm)
         #cv2.waitKey(0)

            try:
                cv2.imwrite(out_file, image)
            except:
                print("FAILED TO WRITE OUT: ", out_file)

         #cv2.imshow('pepe', show_frame)
         #cv2.waitKey(30)
   pics_dir = f"/mnt/ams2/meteor_archive/{station_id}/TIME_LAPSE/{date}/"
   video_from_images(pics_dir, date, cam, json_conf)

def video_from_images(pics_dir, date, wild, json_conf ):
   #TL_DIR = "/mnt/ams2/meteor_archive/" + STATION_ID + "/TL/VIDS/" + date + "/"
   TL_DIR = pics_dir
   tl_out = TL_DIR + "tl_" + date + "_" + wild + ".mp4"

   iwild = TL_DIR + "*" + wild + "*.jpg"

   print(iwild)
   cmd = "/usr/bin/ffmpeg -framerate 25 -pattern_type glob -i '" + iwild + "' -c:v libx264 -pix_fmt yuv420p -y " + tl_out + " >/dev/null 2>&1"
   print(cmd)
   os.system(cmd)
   print(tl_out)

def six_cam_video(date, json_conf):
   ### make 6 camera tl video for date
   station_id = json_conf['site']['ams_id']

   lc = 1
   mc_layout = {}
   for cam_id in MULTI_CAM_LAYOUT:
      mc_layout[cam_id] = lc
      lc += 1
   
 

   tl_dir = TL_DIR + date + "/"
   all_vids = {}
   #files = glob.glob("/mnt/ams2/HD/*" + date + "*.mp4")
   files = glob.glob(tl_dir + "*.jpg")
   print(tl_dir)
   for file in sorted(files):
      if "trim" in file or "comp" in file:
          
         continue
      fn = file.split("/")[-1]
      key = fn[0:16]
      cam = fn[24:30]
      print(key,cam)
      if key not in all_vids:
         all_vids[key] = {}
      if cam not in all_vids[key]:
         pos = mc_layout[cam]
         all_vids[key][cam] = fn


   print("VIDS:", len(all_vids))
   #MULTI_CAM_LAYOUT
   #5 1 2 
   #3 6 4
   final_frames = {}
   for day in all_vids:
      for cam_id in all_vids[day]:
         fn = all_vids[day][cam_id]
         key = fn[0:16]
         cam = fn[24:30]
         pos = str(mc_layout[cam])
         if key not in final_frames:
            final_frames[key] = { "1": "", "2": "", "3": "", "4": "", "5": "", "6": "" }
         final_frames[key][pos] = fn 


   save_json_file("test.json", final_frames)
   for min_key in final_frames:
      outfile = tl_dir + "comp_" + min_key + ".jpg"
      #if cfe(outfile) == 0:
      if True:
         make_six_image_comp(min_key, final_frames[min_key], 5)
      else:
         print("skip.", min_key)
   pics_dir = "/mnt/ams2/meteor_archive/{station_id}/TL/PICS/"
   video_from_images(pics_dir, date, "comp", json_conf)
       

def make_six_image_comp(min_key, data,featured=0):  
   pos = {}
   if featured == 0:
      pos["1"] = [0,360,0,640]
      pos["2"] = [0,360,640,1280]
      pos["3"] = [0,360,1280,1920]
      pos["4"] = [360,720,0,640]
      pos["5"] = [360,720,640,1280]
      pos["6"] = [360,720,1280,1920]
      pos["7"] = [360,720,1280,1920]
   if featured == 6:
      pos["1"] = [0,360,0,640]
      pos["2"] = [0,360,640,1280]
      pos["3"] = [0,360,1280,1920]
      pos["4"] = [360,720,1280,1920]
      # FEATURED HERE! 
      pos["5"] = [360,1080,0,1280]
      pos["6"] = [720,1080,1280,1920]
      pos["7"] = [360,720,1280,1920]
   if featured == 5:
      pos["1"] = [0,360,0,640]
      pos["2"] = [0,360,640,1280]
      pos["3"] = [0,360,1280,1920]
      pos["4"] = [360,720,1280,1920]
      # FEATURED HERE! 
      pos["6"] = [360,1080,0,1280]
      pos["5"] = [720,1080,1280,1920]
      pos["7"] = [360,720,1280,1920]

   date = min_key[0:10]
   blank_image = np.zeros((1080,1920,3),dtype=np.uint8)
   tl_dir = TL_DIR + date + "/"
   outfile = tl_dir + "comp_" + min_key + ".jpg"
   for key in data:  
      y1,y2,x1,x2 = pos[key]
      w = x2 - x1
      h = y2 - y1
      imgf =  tl_dir + data[key]
      img = cv2.imread(imgf)
      try:
         img_sm = cv2.resize(img, (w, h))
         #print(y1,y2,x1,x2)
         #print(img_sm.shape)
      except:
         print("Can't make this file!", key, data[key])
         img_sm = np.zeros((h,w,3),dtype=np.uint8)
      blank_image[y1:y2,x1:x2] = img_sm
   #if cfe(outfile) == 0:
   if True:
      print("saving :", outfile)
      cv2.imwrite(outfile, blank_image)
      #cv2.imshow('pepe', blank_image)
      #cv2.waitKey(0)
   else:
      print("Skip.")
