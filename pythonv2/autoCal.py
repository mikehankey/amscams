#!/usr/bin/python3
#from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

import datetime
import time
import glob
import os
import math
import cv2
import math
import cgitb
import numpy as np
import scipy.optimize
from fitMulti import minimize_poly_params_fwd
from lib.VideoLib import get_masks, find_hd_file_new, load_video_frames
from lib.UtilLib import check_running, get_sun_info, fix_json_file, find_angle

from lib.ImageLib import mask_frame , stack_frames, thumb
#import matplotlib
#matplotlib.use('Agg')
#import matplotlib.pyplot as plt
import sys
#from caliblib import distort_xy,
from lib.CalibLib import distort_xy_new, find_image_stars, distort_xy_new, XYtoRADec, radec_to_azel, get_catalog_stars,AzEltoRADec , HMS2deg, get_active_cal_file, RAdeg2HMS, clean_star_bg, define_crop_box
from lib.UtilLib import calc_dist, find_angle, bound_cnt, cnt_max_px

from lib.UtilLib import angularSeparation, convert_filename_to_date_cam, better_parse_file_date
from lib.FileIO import load_json_file, save_json_file, cfe
from lib.UtilLib import calc_dist,find_angle
import lib.brightstardata as bsd
from lib.DetectLib import eval_cnt

def cp_meteor_index(day = None):
   recopy = 1
   network = json_conf['site']['network_sites'].split(",")
   station = json_conf['site']['ams_id']
   network.append(station)
   detect_index = {}
   for st in network:
      if day is None:
         data_file = "/mnt/ams2/meteor_archive/" + st + "/DETECTS/meteor_index.json"
      else:
         #MIKE
         year = day[0:4]
         mi_day_dir  = "/mnt/ams2/meteor_archive/" + st + "/DETECTS/MI/" + year + "/"
         wb_day_dir  = "/mnt/wasabi/" + st + "/DETECTS/MI/" + year + "/" 
         wasabi_file = wb_day_dir + day + "-meteor_index.json"
      
      if cfe(mi_day_dir, 1) == 0:
         os.makedirs(mi_day_dir)

      if cfe(wasabi_file) == 1:
         print("cp " + wasabi_file + " " + mi_day_dir)
         os.system("cp " + wasabi_file + " " + mi_day_dir)
      else:
         print("WASBI NOT FOUND:", wasabi_file)


def get_trim_num(video_file):
   # parse trim_num
   #video_file = json_file.replace(".json", "-HD.mp4")
   xxx = video_file.split("-")
   trim_num = xxx[-1].replace("trim", "")
   trim_num = trim_num.replace(".mp4", "")
   trim_num = trim_num.replace(".json", "")
   return(trim_num)


def month_detects(date_str):
   import calendar
   y,m,d = date_str.split("_")
   year = y
   month = m
   day = d
   m,d,y = int(m),int(d),int(y)
   date_dt = datetime.datetime.strptime(date_str, "%Y_%m_%d")
   print("Month", y,m,d)
   num_days = calendar.monthrange(y, m)[1]
   print(num_days)
   for day in range(1,num_days+1):
      if m < 10:
         mon_str = "0" + str(m)
      else:
         mon_str = str(m)
      if day < 10:
         day_str = "0" + str(day)
      else:
         day_str = str(day)
      run_date = str(y) + "_" + str(mon_str) + "_" + day_str
      cmd = "./autoCal.py run_detects " + run_date
      os.system(cmd)
      print(cmd)


def update_arc_detects():
   station_id = json_conf['site']['ams_id']
   detect_file = "/mnt/ams2/meteor_archive/" + station_id + "/DETECTS/ms_detects.json"
   detects = load_json_file(detect_file)
   td = 0
   for day in detects:
      print(day)
      for file in detects[day]:
         meteor_day = file[0:10]
         td = td + 1
         key_file = file
         file = "/mnt/ams2/meteors/" + meteor_day + "/" + file
         print("Update this file:", file)
         jd = load_json_file(file)
         if jd == 0:
            print("ERR:", file)
            continue
         if "archive_file" in jd:
            archive_file = jd['archive_file']
            if cfe(archive_file) == 1:
               print("This meteor has been archived, so lets make sure the archive file has the MS detect status set.", jd['archive_file'])
               arc_data = load_json_file(jd['archive_file'])
               if "multi_station" not in arc_data['info']:
                  arc_data['info']['multi_station'] = 1
               if "multi" not in arc_data:
                  arc_data['multi'] = {}
               print("DEBUG:", detects[day][key_file])
               multi = build_multi(detects[day][key_file])
               print("MULTI:", multi)
               # Also make sure the info['org_sd_vid'] and info['org_hd_vid'] are set to the correct values.
               org_sd_vid = file.replace(".json", ".mp4")
               if "hd_trim" in jd:
                  if jd['hd_trim'] is not None and jd['hd_trim'] != 0:
                     org_hd_vid = jd['hd_trim']
                     if arc_data['info']['org_hd_vid'] != org_hd_vid:
                        arc_data['info']['org_hd_vid'] = org_hd_vid
               if arc_data['info']['org_sd_vid'] != org_sd_vid:
                  arc_data['info']['org_sd_vid'] = org_sd_vid
               arc_data['multi'] = multi
               # now save the arc file with the updated info!
               save_json_file(archive_file, arc_data)
               print("SAVED:", archive_file)
   print("Total arc detects so far:", td)
          
def get_old_meteor_dir(file):
   meteor_day = file[0:10]
   new_file = "/mnt/ams2/meteors/" + meteor_day + "/" + file
   return(new_file)


def build_multi(data):
   multi = {}
   work = {}
   print("BUILD MULTI FROM:", data)

   multi['event_id'] = "pending" 
   cs = []
   for e_start in data['clip_starts']:
      dt_start = datetime.datetime.strptime(e_start, "%Y-%m-%d %H:%M:%S.%f")
      cs.append(int(dt_start.timestamp()))

   med_start = np.median(cs)
   med_datetime = datetime.datetime.fromtimestamp(med_start)
   multi['event_start'] = med_datetime.strftime("%Y-%m-%d %H:%M:%S.%f")

   multi['obs'] = [] 
   for i in range(0, len(data['stations'])):
      station = data['stations'][i]
      org_file = data['obs'][i] 
      arc_file = data['arc_files'][i] 

      if station not in work:
         work[station] = {}
         work[station]['station'] = station
         work[station]['files'] = []
      work[station]['files'].append((arc_file,org_file))
   for station in work:
      multi['obs'].append(work[station])
   return(multi)   

def run_detects(day):
   recopy = 0
   print("RUN DETECTS")
   network = json_conf['site']['network_sites'].split(",")
   station = json_conf['site']['ams_id']
   network.append(station)
   detect_index = {}  
   for st in network:
      data_file = "/mnt/ams2/meteor_archive/" + st + "/DETECTS/meteor_index.json"
      arc_station_dir = "/mnt/ams2/meteor_archive/" + st + "/"
      if cfe(arc_station_dir, 1) == 0:
         os.system("mkdir " + arc_station_dir)
         os.system("mkdir " + arc_station_dir + "/METEORS/")
         os.system("mkdir " + arc_station_dir + "/CAL/")
         os.system("mkdir " + arc_station_dir + "/DETECTS/")
      if cfe(data_file) == 0 or recopy == 1:
         wasabi_file = data_file.replace("ams2/meteor_archive", "wasabi")
         wasabi_file = wasabi_file + ".gz"
         print("DATA FILE NOT FOUND!", data_file, wasabi_file)
         if cfe(wasabi_file) == 1:
            data_file_z = data_file + ".gz"
            print("DETECT FILE MISSING FROM ARCHIVE, UPDATE.")
            print("cp " + wasabi_file + " " + data_file_z)
            os.system("cp " + wasabi_file + " " + data_file_z)
            os.system("gunzip -f " + data_file_z)

      if cfe(data_file) == 1:
         print(st, data_file)
         data = load_json_file(data_file)
      else:
         data = False
      if data != 0 and data is not False:
         if day in data:
            detect_index[st] = data[day]
      else:
         print("Could not open meteor index.json!")

   files = []
   min_meteors = {}
   files_station = {}

   print("DETECT INDEX:")

   for st in detect_index:
      print(st)
      for file in detect_index[st]:
         print("ST FILE:", st, file, detect_index[st][file])
         
         if "archive_file" in detect_index[st][file]:
            arc_file = detect_index[st][file]['archive_file']
         else:
            arc_file = "pending"
      
         fn = file.split("/")[-1]
         files_station[fn] = st 
         (file_date, cam_id, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(file)
         trim_num = get_trim_num(file)
         extra_sec = int(trim_num) / 25
         clip_start = file_date + datetime.timedelta(0,extra_sec)
         clip_start_str= clip_start.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
         min_fn = detect_index[st][file]['event_start_time'][0:16]
         min_fn = min_fn.replace("-","_")
         min_fn = min_fn.replace(":","_")
         min_fn = min_fn.replace(" ","_")

         if min_fn not in min_meteors:
            min_meteors[min_fn] = {}
            min_meteors[min_fn]['count'] = 0
            min_meteors[min_fn]['obs'] = []
            min_meteors[min_fn]['stations'] = []
            min_meteors[min_fn]['clip_starts'] = []
            min_meteors[min_fn]['arc_files'] = []
         min_meteors[min_fn]['obs'].append(fn)
         min_meteors[min_fn]['stations'].append(st)
         min_meteors[min_fn]['clip_starts'].append(clip_start_str)
         arc_fn = arc_file.split("/")[-1]
         min_meteors[min_fn]['arc_files'].append(arc_fn)
         min_meteors[min_fn]['count'] = len(set(min_meteors[min_fn]['stations']))
         min_meteors[min_fn]['event_start_time'] = detect_index[st][file]['event_start_time']
         files.append(file)

   for min in min_meteors:
      if min_meteors[min]['count'] > 1:
         for i in range(0, len(min_meteors[min]['obs'])):
            station = min_meteors[min]['stations'][i]
            station_file = min_meteors[min]['obs'][i]
            clip_start = min_meteors[min]['clip_starts'][i]
            print(min, station, station_file, clip_start)
         
   ms_meteors = {}
   for min in min_meteors:
      print(min, min_meteors[min])
      if min_meteors[min]['count'] > 1:
         for i in range(0,len(min_meteors[min]['obs'])):
            file = min_meteors[min]['obs'][i]
            clip_start = min_meteors[min]['clip_starts'][i]
            st = files_station[file]
            if st not in ms_meteors:
               ms_meteors[st] = {}

            ms_meteors[st][file] = {} 
            ms_meteors[st][file]['obs'] = min_meteors[min]['obs'] 
            ms_meteors[st][file]['stations'] = min_meteors[min]['stations'] 
            ms_meteors[st][file]['clip_starts'] = min_meteors[min]['clip_starts'] 
            ms_meteors[st][file]['arc_files'] = min_meteors[min]['arc_files'] 
            ms_meteors[st][file]['event_start'] = min_meteors[min]['event_start_time'] 
            ms_meteors[st][file]['count'] = min_meteors[min]['count'] 
            event_id, event_dir = check_add_event(ms_meteors[st][file])
            ms_meteors[st][file]['event_id'] = event_id
            print(min, min_meteors[min]['count'])

   for st in ms_meteors:
      print(st)
      master_detect_file = "/mnt/ams2/meteor_archive/" + st + "/DETECTS/ms_detects.json"
      if cfe(master_detect_file) == 1:
         master_detect = load_json_file(master_detect_file)
         if master_detect == 0:
            print("ERROR: can't load master detect file!", master_detect_file)
      else:
         master_detect = {}
      print("DAY:", day, ms_meteors[st])
      if st in ms_meteors:
         master_detect[day] = ms_meteors[st]
      save_json_file(master_detect_file, master_detect)
      print(master_detect_file) 

def check_add_event(ms_info):
   event_start = ms_info['event_start'].split(".")[0]
   obs_count = ms_info['count']
   
   event_start = event_start.replace("-","_")
   event_start = event_start.replace(":","_")
   event_start = event_start.replace(" ","_")

   if obs_count == 1:
      return(event_start, None)

   event_year = event_start[0:4]
   event_day = event_start[0:10]
   event_dir = "/mnt/ams2/meteor_archive/events/" + event_year + "/" + event_day + "/" + event_start
   event_id = event_start 
   check_existing = 0
    
   if cfe(event_dir, 1) == 0:
      # check to make sure there isn't another dir here within 1-3 seconds in the event the start time has changed due to an added obs      
      # that wasn't there
      check_existing = 0
   if check_existing == 0 and cfe(event_dir, 1) == 0:
      # safe to make a new event here
      print("Making: ", event_dir)
      os.makedirs(event_dir)
   else:
      print("Check lat lon for simultaneous meteors")
      # make sure this is the event by checking the existing epicenter lat/lon with this one. 
      # if the lat/lons are too far we have 2 events at the same time. Add a counter to the end of the timestamp /event id. 
 
   return(event_id, event_dir)
   


def check(day):
   red_files = glob.glob("/mnt/ams2/meteors/" + day + "/*reduced.json")
   for file in red_files:
      red = load_json_file(file)
      if "meteor_frame_data" in red:
         print("OK", file)
      else:
         print("BAD", file)
   ev_day = day.replace("_", "")
   ev_dirs = glob.glob("/mnt/ams2/events/*")
   print("EV DAY:", ev_day)
   for dir in ev_dirs:
      fn = dir.split("/")[-1]

      if ev_day == fn[0:8]:
         print(ev_day, fn[0:8])
         files = glob.glob(dir + "/*.json" )
         print(dir + "/*.json" )
         for file in files:
            print(file)
            try:
               evred = load_json_file(file)
            except:
               print("BAD FILE MISSING:", file)
            if "meteor_frame_data" in evred:
               print("OK", file)
            else:
               print("BAD NO FRAMES", file)

def mark_stars_on_image(img, cat_image_stars):
   image = Image.fromarray(img)
   draw = ImageDraw.Draw(image)
   font = ImageFont.truetype("/usr/share/fonts/truetype/freefont/FreeSans.ttf", 12, encoding="unic" )
   print(cat_image_stars[0])

   for star in cat_image_stars:
      color = "white"
      (name,mag,ra,dec,tmp1,tmp2,px_dist,new_cat_x,new_cat_y,tmp2,tmp3,new_cat_x,new_cat_y,ix,iy,px_dist) = star
      draw.rectangle((ix-10, iy-10, ix + 10, iy + 10), outline=color)
      draw.text((ix-10, iy-15), str(name), font = font, fill=color)
      #draw.ellipse((mx-1, my-1, mx+1, my+1),  outline ="white")
      #draw.ellipse((mx-3, my-3, mx+3, my+3),  outline ="white")

   return(np.asarray(image))


def star_merge_movie(json_conf):
   cam_id = "010005"
   starmerge_file = "/mnt/ams2/cal/hd_images/master_merge_010005.json"
   starmerge = load_json_file(starmerge_file)
   total_files = {}
   hd_cal_files = []
   meteor_files = []
   for star in starmerge:
      total_files[star[0]] = {}

   for file in total_files:
      print(file)
      if "reduced" in file and cfe(file) == 1 :
         mr = load_json_file(file)
         if 'hd_stack' in mr:
            print(mr['hd_stack'])
            if cfe(mr['hd_stack']) == 1:
               img = cv2.imread(mr['hd_stack'])
               if img.shape[0] != 1080:
                  img = cv2.resize(img, (1920,1080))

               if "cat_image_stars" in mr['cal_params']:
                  new_img = mark_stars_on_image(img, mr['cal_params']['cat_image_stars'])

                  show_img = cv2.resize(new_img, (960,540))
                  show_img = new_img
                  cv2.imshow('meteors', show_img)
                  cv2.waitKey(10)
                  meteor_files.append(file)
      elif cfe(file) == 1:
         hd_cal_files.append(file)

   for file in sorted(hd_cal_files):
      print(file)
      
      cp = load_json_file(file)
      cp_img = file.replace("-calparams.json", "-stacked.png")
      if cfe(cp_img) == 0:
         print("BAD:", cp_img)
      else:
         img = cv2.imread(cp_img)
         if img.shape[0] != 1080:
            img = cv2.resize(img, (1920,1080))

         if "cat_image_stars" in cp:
            new_img = mark_stars_on_image(img, cp['cat_image_stars'])

            show_img = cv2.resize(new_img, (960,540))
            show_img = new_img
            cv2.imshow('meteors', show_img)
            cv2.waitKey(10)


def cams_exp(file, json_conf):
   json_data = load_json_file(file)
   mfd = json_data['meteor_frame_data']
   for mf in mfd:
#['2019-01-07 11:08:32.640', 94, 820, 868, 11, 11, 164, 199.69, 39.85, 58.5, 25.92]

      print(mf[1],mf[2],mf[3],mf[7],mf[8],mf[9],mf[10],mf[6])

def bound_xy(x,y,iw,ih,sz):
   if x-sz < 0:
      x1 = 0
   else:
      x1 = x - sz
   if y-sz < 0:
      y1 = 0
   else:
      y1 = y - sz
   if x+sz > iw-1:
      x2 = iw -1
   else:
      x2 = x + sz
   if y+sz > ih-1:
      y2 = ih
   else:
      y2 = y + sz


   return(x1,y1,x2,y2)


def reset_reduce(json_conf, meteor_file):
   mjf = meteor_file
   mjf = mjf.replace(".json", "-reduced.json")
   if "reduced.json" not in mjf:
      print("BAD FILE!")
      exit()
   if cfe(mjf) == 0:
      print("BAD FILE!")
      exit()
   if "meteors" not in mjf:
      print("BAD FILE!")
      exit()
   if " " in mjf:
      print("BAD FILE!")
      exit()
   if ";" in mjf:
      print("BAD FILE!")
      exit()
   cmd = "rm " + mjf
   os.system(cmd)

   mf = mjf.replace("-reduced.json", ".json")
   cmd = "cd /home/ams/amscams/pythonv2/; ./detectMeteors.py raj " + mf 
   os.system(cmd)
   print(cmd)
   cmd = "cd /home/ams/amscams/pythonv2/; ./autoCal.py imgstars " + mf  
   os.system(cmd)
   print(cmd)
   cmd = "cd /home/ams/amscams/pythonv2/; ./autoCal.py cfit " + mf 
   os.system(cmd)
   print(cmd)
   cmd = "cd /home/ams/amscams/pythonv2/; ./autoCal.py imgstars " + mf  
   os.system(cmd)
   print(cmd)
   cmd = "cd /home/ams/amscams/pythonv2/; ./detectMeteors.py raj " + mf 
   os.system(cmd)
   cmd = "cd /home/ams/amscams/pythonv2/; ./autoCal.py imgstars " + mf  
   os.system(cmd)
   cmd = "cd /home/ams/amscams/pythonv2/; ./autoCal.py cfit " + mf 
   os.system(cmd)
   cmd = "cd /home/ams/amscams/pythonv2/; ./autoCal.py cfit " + mf 
   os.system(cmd)
   cmd = "cd /home/ams/amscams/pythonv2/; ./autoCal.py cfit " + mf 
   os.system(cmd)
   cmd = "cd /home/ams/amscams/pythonv2/; ./autoCal.py imgstars " + mf  
   os.system(cmd)


def get_meteor_dirs():
   meteor_dirs = []
   files = glob.glob("/mnt/ams2/meteors/*")
   for file in files:
      if "trash" not in file:
         if cfe(file,1) == 1:
            meteor_dirs.append(file)
   return(meteor_dirs)

def get_meteors(meteor_dir,meteor_data,rmeteor_data):
   glob_dir = meteor_dir + "*-trim*.mp4"
   files = glob.glob(meteor_dir + "/*-trim*.json")
   for file in files:
      if "calparams" not in file and "reduced" not in file and "manual" not in file:
         meteor_data.append(file)
      if "reduced" in file:
         rmeteor_data.append(file)
   return(meteor_data,rmeteor_data)




def meteor_index(json_conf, day = None, extra_cmd = ""):    
   station_id = json_conf['site']['ams_id']
   meteor_data = []
   rmeteor_data = []
   meteor_index = {}
   if day is None:
      meteor_dirs = get_meteor_dirs()
   else:
      meteor_dirs = ["/mnt/ams2/meteors/" + day + "/"]
   print("Got meteor dirs")
   for meteor_dir in meteor_dirs:
      print("Scanning...", meteor_dir)
      meteor_Data, rmeteor_data = get_meteors(meteor_dir, meteor_data, rmeteor_data)
   jobs = []
   jobs2 = []
   for meteor in sorted(meteor_data, reverse=True):
      day = meteor.split("/")[4]
      event_start_time = None
      if "reduced" not in meteor and "events" not in meteor and "framedata" not in meteor:
         if day not in meteor_index:
            meteor_index[day] = {}
         meteor_index[day][meteor] = {}
         rmeteor = meteor.replace(".json", "-reduced.json")
         meteor_data = load_json_file(meteor)
         if "archive_file" in meteor_data:
            if cfe(meteor_data['archive_file']) == 1:
               archived = 1
               meteor_index[day][meteor]['archive_file'] = meteor_data['archive_file']
               azs, els,ints,event_start_time = get_az_el_from_arc(meteor_data['archive_file'])
               meteor_index[day][meteor]['azs'] = azs
               meteor_index[day][meteor]['els'] = els
               meteor_index[day][meteor]['ints'] = ints 
               meteor_index[day][meteor]['event_start_time'] = event_start_time
         if "sd_objects" not in meteor_data:
            print("NO SD OBJ!", meteor )
            continue 
         for obj in meteor_data['sd_objects']:
            print("OBJ:", obj)
            #only do this on the meteor object!)
            # add event start time estimate only if arc time is not set!
            if event_start_time is None:
               trim_num = get_trim_num(meteor)
               print("TRIM NUM:", trim_num)
               extra_start_file_sec = int(trim_num) / 25
               event_start_fn = obj['history'][0][0]
               print("EVENT START FN:", event_start_fn, meteor)
               (file_date, cam_id, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(meteor)
               extra_sec = (int(event_start_fn) / 25) + extra_start_file_sec
               event_start = file_date + datetime.timedelta(0,extra_sec)
               event_start_str = event_start.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
               meteor_index[day][meteor]['event_start_time'] = event_start_str
         # if the archive file exists, get the az,el values and add to the index     
 
   sort_meteor_index = {}
   for day in sorted(meteor_index, reverse=True):
      sort_meteor_index[day] = {}
   for day in sorted(meteor_index, reverse=True):
      for meteor in meteor_index[day]:
         sort_meteor_index[day][meteor] = meteor_index[day][meteor]

   if day is None:
      save_json_file("/mnt/ams2/cal/hd_images/meteor_index.json", sort_meteor_index, False)

      ma_dir  = "/mnt/ams2/meteor_archive/" + station_id + "/DETECTS/" 
      wb_dir  = "/mnt/wasabi/" + station_id + "/DETECTS/" 
      if cfe(ma_dir,1) == 0:
         os.system("mkdir " + ma_dir)
      if cfe(wb_dir, 1) == 0:
         os.system("mkdir " + wb_dir)

      cmd = "cp /mnt/ams2/cal/hd_images/meteor_index.json /mnt/ams2/meteor_archive/" + station_id + "/DETECTS/"
      os.system(cmd)
      cmd = "gzip -f /mnt/ams2/cal/hd_images/meteor_index.json"
      os.system(cmd)
      cmd = "cp /mnt/ams2/cal/hd_images/meteor_index.json.gz /mnt/ams2/meteor_archive/" + station_id + "/DETECTS/"
      os.system(cmd)
      cmd = "cp /mnt/ams2/cal/hd_images/meteor_index.json.gz /mnt/wasabi/" + station_id + "/DETECTS/"
      os.system(cmd)

   else:
      year = day[0:4]
      mi_day_dir  = "/mnt/ams2/meteor_archive/" + station_id + "/DETECTS/MI/" + year + "/"
      wb_day_dir  = "/mnt/archive.allsky.tv/" + station_id + "/DETECTS/MI/" + year + "/"
      if cfe(mi_day_dir, 1) == 0:
         os.makedirs(mi_day_dir)
      if cfe(wb_day_dir, 1) == 0:
         os.makedirs(wb_day_dir)
      save_json_file(mi_day_dir + day + "-meteor_index.json", sort_meteor_index, False )   
      save_json_file(wb_day_dir + day + "-meteor_index.json", sort_meteor_index, False )   
      print("SAVED:", mi_day_dir + day + "-meteor_index.json")

   print(json_conf)


   fov_vars = {}
   fov_day = {}
   # make best day avg for fov vars
   for day in meteor_index:
      for meteor in meteor_index[day]:
         (f_datetime, cam_id, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(meteor)
         if cam_id not in fov_vars:
            fov_vars[cam_id] = {}
            fov_day[cam_id] = {}
         if day not in fov_vars[cam_id]:
            fov_vars[cam_id][day] = {}
            fov_vars[cam_id][day]['center_az'] = []
            fov_vars[cam_id][day]['center_el'] = []
            fov_vars[cam_id][day]['position_angle'] = []
            fov_vars[cam_id][day]['pixscale'] = []
         if 'center_az' in meteor_index[day][meteor]:
            fov_vars[cam_id][day]['center_az'].append( float(meteor_index[day][meteor]['center_az']))
            fov_vars[cam_id][day]['center_el'].append( float(meteor_index[day][meteor]['center_el']))
            fov_vars[cam_id][day]['position_angle'].append( float(meteor_index[day][meteor]['position_angle']))
            fov_vars[cam_id][day]['pixscale'].append( float(meteor_index[day][meteor]['pixscale']))

   for cam_id in fov_vars:
      for day in fov_vars[cam_id]:
         if len(fov_vars[cam_id][day]['pixscale']) > 3:
            if cam_id not in fov_day:
               fov_day[cam_id] = {}
            if cam_id not in fov_day[cam_id]:
               fov_day[cam_id][day] = {}
            fov_day[cam_id][day]['avg_center_az'] = np.mean(fov_vars[cam_id][day]['center_az'])
            fov_day[cam_id][day]['avg_center_el'] = np.mean(fov_vars[cam_id][day]['center_el'])
            fov_day[cam_id][day]['avg_position_angle'] = np.mean(fov_vars[cam_id][day]['position_angle'])
            fov_day[cam_id][day]['avg_pixscale'] = np.mean(fov_vars[cam_id][day]['pixscale'])

   save_json_file("/mnt/ams2/cal/hd_images/fov_vars.json", fov_day)



   if 'max_procs' in json_conf['site']:
      max_procs = json_conf['site']['max_procs']
   else: 
      max_procs = 4

   jc = 0
   for job in jobs:


      while (check_running("autoCal.py")) > max_procs:
         time.sleep(1)
      print(job)
      #if "010002" in job:
      os.system(job + " &")
      jc = jc + 1
 
   exit()

def get_az_el_from_arc(arc_file):
   event_start_time = None
   arc_data = load_json_file(arc_file)
   azs = []
   els = []
   ints = []
   if arc_data != 0:
      event_start_time = arc_data['frames'][0]['dt']
      for frame in arc_data['frames']:
         az = frame['az']
         el = frame['el']
         if "intensity" in frame:
            intensity = frame['intensity']
         else:
            intensity = 0
         azs.append(az)
         els.append(el)
         ints.append(intensity)
   return(azs,els,ints,event_start_time)

def find_best_fov(meteor_json_file, json_conf):
   found = 0
   rfile = meteor_json_file.replace(".json", "-reduced.json")
   if "mp4" in rfile:
      rfile = rfile.replace(".mp4", "-reduced.json")
   (f_datetime, cam_id, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(meteor_json_file)
   fov= load_json_file("/mnt/ams2/cal/hd_images/fov_vars.json")
   mj = load_json_file(rfile)
   fovs = []
   for day in fov[cam_id]:
      fov_date = datetime.strptime(day, "%Y_%m_%d")
      tdiff = abs((f_datetime-fov_date).total_seconds())
      fovs.append((day, tdiff, fov[cam_id][day]['avg_center_az'], fov[cam_id][day]['avg_center_el'], fov[cam_id][day]['avg_position_angle'], fov[cam_id][day]['avg_pixscale']))
        
   this_poly = np.zeros(shape=(4,), dtype=np.float64)
   if 'cal_params' in mj:
      cal_params = mj['cal_params']
   else:
      print("NO CAL")
      poss = get_active_cal_file(meteor_json_file)
      cal_params_file = poss[0][0]
      cal_params = load_json_file(cal_params_file)

   paired_stars = cal_params['cat_image_stars']
   oimg = np.zeros((1080,1920),dtype=np.uint8)


   start_res = reduce_fov_pos(this_poly, cal_params,meteor_json_file,oimg,json_conf, paired_stars,0,show)
   best_res = start_res 
   print("START RES:", start_res)
   fovs = sorted(fovs, key=lambda x: x[1], reverse=False)
   for fov in fovs:
      (date,tdif,center_az,center_el,position_angle,pixscale) = fov
      cal_params['center_az'] = center_az
      cal_params['center_el'] = center_el
      cal_params['position_angle'] = position_angle
      cal_params['pixscale'] = pixscale
   
      res = reduce_fov_pos(this_poly, cal_params,meteor_json_file,oimg,json_conf, paired_stars,0,show)
      if res < best_res:
         best_cal_params = cal_params
         best_res = res
         print("BEST:", date,tdif,center_az,center_el,position_angle,pixscale)
         found = 1
   if found == 0:
      print ("Could not find a better file. CFIT this one.")
      cmd = "./autoCal.py cfit " + meteor_json_file
      print(cmd)
      os.system("./autoCal.py cfit " + meteor_json_file)



def master_merge(tcam_id):
   print("CAM ID:", tcam_id)
   master_merge = []
   freecal_dirs = glob.glob("/mnt/ams2/cal/hd_images/*")
   cal_files = {}
   cam_day_sum = {}
   for fc in freecal_dirs:
      if cfe(fc, 1) == 1:
         merge_file = fc + "/starmerge-" + tcam_id + ".json"
         if cfe(merge_file) == 1:
            merge_data = load_json_file(merge_file)
      
            merge_len = len(merge_data[0])

            (f_datetime, cam_id, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(merge_file)
            if merge_len == 23:
               stars_in_merge = len(merge_data)
               if stars_in_merge > 20:
                  master_merge = master_merge + merge_data
            else:
               print("BAD MERGE LEN", master_merge = master_merge + merge_data)

   meteorcal_dirs = glob.glob("/mnt/ams2/meteors/*")
   for fc in meteorcal_dirs:
      if cfe(fc, 1) == 1:
         merge_file = fc + "/starmerge-" + tcam_id + ".json"
         if cfe(merge_file) == 1:
            print(merge_file)
            merge_data = load_json_file(merge_file)
            (f_datetime, cam_id, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(merge_file)
            master_merge = master_merge + merge_data

   master_merge_file = "/mnt/ams2/cal/hd_images/master_merge_" + tcam_id + ".json"

   save_json_file(master_merge_file, master_merge)
   cmd = "./autoCal.py run_merge " + master_merge_file + " " + tcam_id + " " + str(show) + " &"
   print(cmd)



def cal_index(json_conf):
   # BUILD FREE CAL INDEX

   freecal_dirs = glob.glob("/mnt/ams2/cal/freecal/*")
   cal_files = {}
   for fc in freecal_dirs:
      if cfe(fc, 1) == 1:
         base_name = fc.split("/")[-1]
         cp_file = fc + "/" + base_name + "-stacked-calparams.json"
         print("CP:", cp_file)
         if cfe(cp_file) == 1:
            cal_files[cp_file] = {}
            cal_files[cp_file]['base_dir'] = fc 
         else:
            cp_file = fc + "/" + base_name + "-calparams.json"
            if cfe(cp_file) == 1:
               cal_files[cp_file] = {}
               cal_files[cp_file]['base_dir'] = fc 
            else:
               print("NOT FOUND:", cp_file)
   for cp_file in cal_files:
      cj = load_json_file(cp_file)
      (f_datetime, cam_id, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(cp_file)
      if cj == 0:
         print("Bad file", cp_file)
         continue
      if 'center_az' not in cj:
         new_date = fy + "/" + fm + "/" + fd + " " + fh + ":" + fmin + ":" + fs
         az, el = radec_to_azel(cj['ra'],cj['dec'], new_date,json_conf)
         cj['center_az'] = az
         cj['center_el'] = el
         print("FIXING MISSING AZ/EL FROM CAL_PARMAS!")
         exit()
      else:
         print("CENTER AZ IS :", cj['center_az'], cj['center_el'])

      cal_files[cp_file]['cal_date'] = f_date_str
      cal_files[cp_file]['cam_id'] = cam_id 
      cal_files[cp_file]['center_az'] = cj['center_az']
      cal_files[cp_file]['center_el'] = cj['center_el']
      cal_files[cp_file]['pixscale'] = cj['pixscale']
      cal_files[cp_file]['position_angle'] = cj['position_angle']    
      cal_image_file = cp_file.replace("-calparams.json", ".png")
      if cfe(cal_image_file) == 0:
         cal_image_file = cp_file.replace("-calparams.json", "-stacked.png")
      if cfe(cal_image_file) == 0:
         cal_image_file = cp_file.replace("-calparams.json", ".png")
      if cfe(cal_image_file) == 0:
         print("IMG NOT FOUND:" , cal_image_file)
      cal_grid_file = cal_image_file.replace(".png", "-azgrid.png")
      if cfe(cal_grid_file) == 0:
         print("GRID NOT FOUND:" , cal_grid_file)

      cal_files[cp_file]['cal_image_file'] = cal_image_file 
      cal_files[cp_file]['cal_grid_file'] = cal_grid_file 
       
 
      if "cat_image_stars" in cj:
         #cal_files[cp_file]['cat_image_stars'] = cj['cat_image_stars']
         cal_files[cp_file]['total_stars'] = len(cj['cat_image_stars'])
      elif "close_stars" in cj:
         #cal_files[cp_file]['cat_image_stars'] = cj['close_stars']
         cal_files[cp_file]['total_stars'] = len(cj['close_stars'])
      else:
         print("NO CAT STARS:", cp_file)
         cal_files[cp_file]['cat_image_stars'] = []
         cal_files[cp_file]['total_stars'] = 0
      if "x_fun" in cj:
         cal_files[cp_file]['x_fun'] = cj['x_fun']
         cal_files[cp_file]['y_fun'] = cj['y_fun']
         cal_files[cp_file]['x_fun_fwd'] = cj['x_fun_fwd']
         cal_files[cp_file]['y_fun_fwd'] = cj['y_fun_fwd']
      else:
         print("No xfun?", cal_files[cp_file]['base_dir'])
         #cmd = "rm -rf " + cal_files[cp_file]['base_dir']
         #os.system(cmd)
         #print(cmd)
      if "total_res_px" in cj:
         cal_files[cp_file]['total_res_px'] = cj['total_res_px']
      else:
         cal_files[cp_file]['total_res_px'] = 0
      if "total_res_deg" in cj:
         cal_files[cp_file]['total_res_deg'] = cj['total_res_deg']         
      else:
         cal_files[cp_file]['total_res_deg'] = 0

   for cp_file in cal_files:
      print(cp_file)
      
      #print( cal_files[cp_file]['base_dir'], cal_files[cp_file]['cam_id'], cal_files[cp_file]['center_az'], cal_files[cp_file]['center_el'], cal_files[cp_file]['position_angle'], cal_files[cp_file]['pixscale'], cal_files[cp_file]['x_fun'], cal_files[cp_file]['y_fun'], cal_files[cp_file]['x_fun_fwd'], cal_files[cp_file]['y_fun_fwd'], cal_files[cp_file]['total_stars'] )
     
   print("saved : /mnt/ams2/cal/freecal_index.json")
   save_json_file("/mnt/ams2/cal/freecal_index.json", cal_files)

def hd_cal_index(json_conf, extra_cmd = ""):
   freecal_dirs = glob.glob("/mnt/ams2/cal/hd_images/*")
   cal_files = {}
   cam_day_sum = {}
   days = []
   for fc in freecal_dirs:

      if cfe(fc, 1) == 1:
         if cfe(fc + "/thumbs/", 1) == 0:
            os.system("mkdir " + fc + "/thumbs/")
         day_dir = fc.split("/")[-1]
         cal_files[day_dir] = {}
         if day_dir not in cam_day_sum:
            cam_day_sum[day_dir] = {}
            days.append(day_dir)

         # TEMP one time jobs here for batch fixing things.
         # will run command on every hdcal file in archive.

         #cmd = "./autoCal.py scan_hd_images " + day_dir
         #cmd = "./autoCal.py batch_hd_fit " + day_dir + " cfit_hdcal"
         if extra_cmd == 'cfit':
            cmd = "./autoCal.py batch_hd_fit " + day_dir + " cfit_hdcal"
            os.system(cmd)
         if extra_cmd == 'imgstars':
            cmd = "./autoCal.py batch_hd_fit " + day_dir + " imgstars"
            os.system(cmd)
         img_files = glob.glob(fc + "/*stacked.png")
         for imf in img_files:
            (f_datetime, cam_id, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(imf)
            cal_file = imf.replace("stacked.png", "calparams.json")

            if cam_id not in cal_files[day_dir]:
               cal_files[day_dir][cam_id] = {}
            if cam_id not in cam_day_sum[day_dir]:
               cam_day_sum[day_dir][cam_id] = {}
               cam_day_sum[day_dir][cam_id]['files_with_stars'] = 0
               cam_day_sum[day_dir][cam_id]['files_without_stars'] = 0
               cam_day_sum[day_dir][cam_id]['total_res_px_for_night'] = 0
               cam_day_sum[day_dir][cam_id]['total_res_deg_for_night'] = 0
               cam_day_sum[day_dir][cam_id]['avg_res_px_for_night'] = 0
               cam_day_sum[day_dir][cam_id]['avg_res_deg_for_night'] = 0
               cam_day_sum[day_dir][cam_id]['total_stars_tracked_for_night'] = 0
               cam_day_sum[day_dir][cam_id]['avg_res_px_for_night'] = 0
               cam_day_sum[day_dir][cam_id]['avg_res_deg_for_night'] = 0

            cal_files[day_dir][cam_id][imf] = {}
            if cfe(cal_file) == 0:
               print("NONE:", cal_file )
            else:
               print("CP:", cal_file)
               cp = load_json_file(cal_file)

               cp['cat_image_stars'] = remove_dupe_cat_stars(cp['cat_image_stars'])

               cal_files[day_dir][cam_id][imf]['center_az'] = cp['center_az']
               cal_files[day_dir][cam_id][imf]['center_el'] = cp['center_el']
               cal_files[day_dir][cam_id][imf]['position_angle'] = cp['position_angle']
               cal_files[day_dir][cam_id][imf]['pixscale'] = cp['pixscale']

               #if cp['total_res_px'] != 9999 and cp['total_res_deg'] != 9999:
               #   cal_files[day_dir][cam_id][imf]['total_res_px'] = cp['total_res_px']
               #   cal_files[day_dir][cam_id][imf]['total_res_deg'] = cp['total_res_deg']
               #elif "total_res_px" not in cal_files[day_dir][cam_id][imf]:
               #   cal_files[day_dir][cam_id][imf]['total_res_px'] = 0 
               #   cal_files[day_dir][cam_id][imf]['total_res_px'] = cp['total_res_px']
               #   cal_files[day_dir][cam_id][imf]['total_res_deg'] = cp['total_res_deg']
               #   cal_files[day_dir][cam_id][imf]['total_res_deg'] = 0 
               cal_files[day_dir][cam_id][imf]['total_res_px'] = cp['total_res_px']
               if len(cp['cat_image_stars']) > 0:
                  cal_files[day_dir][cam_id][imf]['total_res_deg'] = cp['total_res_deg']
               else:
                  cal_files[day_dir][cam_id][imf]['total_res_deg'] = 0
                  cal_files[day_dir][cam_id][imf]['total_res_px'] = 0

               cal_files[day_dir][cam_id][imf]['total_stars'] = len(cp['cat_image_stars'])
               cal_files[day_dir][cam_id][imf]['cat_image_stars'] = cp['cat_image_stars']
               print ("RES:", imf, cal_files[day_dir][cam_id][imf]['total_res_deg'] )
               if len(cp['cat_image_stars']) > 0 and cp['total_res_deg'] != 9999:
                  cam_day_sum[day_dir][cam_id]['files_with_stars'] = cam_day_sum[day_dir][cam_id]['files_with_stars'] + 1
                  cam_day_sum[day_dir][cam_id]['total_res_px_for_night'] = cam_day_sum[day_dir][cam_id]['total_res_px_for_night'] + cp['total_res_px'] 
                  cam_day_sum[day_dir][cam_id]['total_res_deg_for_night'] = cam_day_sum[day_dir][cam_id]['total_res_deg_for_night'] + cp['total_res_deg']
                  cam_day_sum[day_dir][cam_id]['total_stars_tracked_for_night'] = cam_day_sum[day_dir][cam_id]['total_stars_tracked_for_night'] + len(cp['cat_image_stars'])
                  cam_day_sum[day_dir][cam_id]['center_az'] = cp['center_az']
                  cam_day_sum[day_dir][cam_id]['center_el'] = cp['center_el']
                  cam_day_sum[day_dir][cam_id]['position_angle'] = cp['position_angle']
                  cam_day_sum[day_dir][cam_id]['pixscale'] = cp['pixscale']
               else:
                  cam_day_sum[day_dir][cam_id]['files_without_stars'] = cam_day_sum[day_dir][cam_id]['files_without_stars'] + 1

            if "-tn" not in imf:
               tn = imf.replace(".png", "-tn.png")
               fn = tn.split("/")[-1]
               new_tn = "/mnt/ams2/cal/hd_images/" + day_dir + "/thumbs/"  + fn
               if cfe(new_tn) == 0:
                  print("ER:", tn)
                  #exit()
                  thumb(imf, "", .15)
                  cmd = "mv " + tn + " " + new_tn
                  os.system(cmd)
                  print(cmd)
            if cam_day_sum[day_dir][cam_id]['files_with_stars'] > 0:
               cam_day_sum[day_dir][cam_id]['avg_res_px_for_night'] = cam_day_sum[day_dir][cam_id]['total_res_px_for_night'] / cam_day_sum[day_dir][cam_id]['files_with_stars']
               cam_day_sum[day_dir][cam_id]['avg_res_deg_for_night'] = cam_day_sum[day_dir][cam_id]['total_res_deg_for_night'] / cam_day_sum[day_dir][cam_id]['files_with_stars']

   save_json_file("/mnt/ams2/cal/hd_images/hd_cal_index-cam-day-sum.json", cam_day_sum)
   save_json_file("/mnt/ams2/cal/hd_images/hd_cal_index.json", cal_files)

   # run the night cal
   for day in days:
      cmd = "./autoCal.py night_cal " + day
      print(cmd)
      os.system(cmd)

    

def save_cal(starfile, master_cal_file, json_conf):
   print("Saving calibration files...")
   master_cal_params = load_json_file(master_cal_file)
   el = master_cal_file.split("/")
   fn = el[-1]
   date = fn[0:10]
   print("DATE:", date)

   cpm = {}
   for cam_id in master_cal_params:
      if "01" in cam_id:
         print(cam_id, len(master_cal_params[cam_id]))
         cpm[cam_id] = master_cal_params[cam_id]

   master_cal_params = cpm

   for cam_id in master_cal_params:
      print(cam_id, len(master_cal_params[cam_id]))
      if len(master_cal_params[cam_id]) > 6:
         cfbase = date + "_00_00_00_000_" + cam_id
         cf_dir = "/mnt/ams2/cal/freecal/" + cfbase + "/"
         cal_params_file = cf_dir + date + "_00_00_00_000_" + cam_id + "-calparams.json"
         cal_params = master_cal_params[cam_id]
         if cfe(cf_dir, 1) == 0:
            print("mkdir ", cf_dir)
            os.system("mkdir " + cf_dir)

         img_az = cal_params['center_az']
         img_el = cal_params['center_el']
         print("AZ:", img_az, img_el)
         rah,dech = AzEltoRADec(img_az,img_el,cal_params_file,cal_params,json_conf)
         rah = str(rah).replace(":", " ")
         dech = str(dech).replace(":", " ")
         ra_center,dec_center = HMS2deg(str(rah),str(dech))
         cal_params['ra_center'] = ra_center
         cal_params['dec_center'] = dec_center
         save_json_file(cal_params_file, cal_params)
         os.system("cp " + starfile + " " + cf_dir)


         os.system("./XYtoRAdecAzEl.py az_grid " + cal_params_file)

def multi_merge(all_stars, json_conf, day_dir, show = 0):
   cameras = json_conf['cameras']
   cam_ids = []
   x_fun = 4



   for cam_id in sorted(all_stars):
      master_cal_file = str(day_dir) + "/" + "master_cal_file_" + str(cam_id) + ".json"
      status = 0
      skip = 0
      if cfe(master_cal_file) == 1:
         mcj = load_json_file(master_cal_file)
         #x_fun = float(mcj['x_fun'])
         if mcj['x_fun'] < .5:
            print(" This master file is sub .8-pixel res, it is good for now. Skipping.")
            skip = 1
         #if x_fun < 2:
         #   x_fun = float(mcj['x_fun']) * 1.2
         #else:
         #   x_fun = float(mcj['x_fun']) * 2
      x_fun = 15
      merge_file = str(day_dir) + "/starmerge-" + str(cam_id) + ".json"
      print("MERGE FILE:", merge_file)
      print("CAMID",cam_id, x_fun, merge_file)

      merged_stars = all_stars[cam_id]

      multi_fit_merge = []
      for file in merged_stars:
         print(file)
         if cfe(file) == 1:
            img = np.zeros((1080,1920),dtype=np.uint8)
            img = cv2.resize(img, (1920,1080))
            for star in merged_stars[file]:
               print(star)
               cal_params_file,ra_center,dec_center,position_angle,pixscale,name,mag,ra,dec,img_ra,img_dec,match_dist,new_cat_x,new_cat_y,img_az,img_el,new_cat_x,new_cat_y,ix,iy, img_res,np_new_cat_x, np_new_cat_y = star

               cv2.circle(img,(ix,iy), 5, (128,128,128), 1)
               cv2.rectangle(img, (new_cat_x-2, new_cat_y-2), (new_cat_x + 2, new_cat_y + 2), (128, 128, 128), 1)
               cv2.line(img, (ix,iy), (new_cat_x,new_cat_y), (255), 2)
               multi_fit_merge.append(star)
            if show == 1:
               simg = cv2.resize(img, (960,540))
               cv2.imshow(cam_id, simg)
               cv2.waitKey(0)


      #new_cp = cal_params_file.replace("-calparams.json", "-calparams-master.json")
      master_cal_params = {}
      #if cfe(new_cp) == 0 :
      if True:
         #new_multi_fit_merge = remove_bad_pairs(multi_fit_merge)
         #new_multi_fit_merge = clean_pairs(multi_fit_merge, x_fun)
         new_multi_fit_merge = multi_fit_merge
         cal_params = {}
         cal_params = default_cal_params(cal_params,json_conf)
         # do 1 cam here
         merge_file = day_dir + "/starmerge-" + cam_id + ".json"
         for star in new_multi_fit_merge:
            print(len(star), star)
         save_json_file(merge_file, new_multi_fit_merge)
         print("saved ", merge_file)
         #print("QUIT")
         #exit()
         
         if skip == 0:
           
            cmd = "./autoCal.py run_merge " + merge_file + " " + cam_id + " " + str(show) + " &"
            print(cmd)
            #os.system(cmd)
      else:
         print("SKIPPING ALREADY DONE!")

def clean_pairs(merged_stars, inc_limit = 5, show = 0):
   merged_stars_orig = sorted(merged_stars, key=lambda x: x[19], reverse=False)
   merged_stars = sorted(merged_stars, key=lambda x: x[19], reverse=False)

   multi = 0
   good_merge = []
   print("TOTAL MERGED STARS:", len(merged_stars))
   img = np.zeros((1080,1920),dtype=np.uint8)
   dupe_check = {}
   close_stars = {}

   dist_list = []
   merged_stars = sorted(merged_stars, key=lambda x: x[20], reverse=False)
   for star in merged_stars:
      (cal_file,ra_center,dec_center,position_angle,pixscale,dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy, img_res) = star
      dist_list.append(img_res)
   std_dev_dist = np.std(dist_list) * 2 

   if std_dev_dist < 3:
      std_dev_dist = 5 

   for star in merged_stars:
      (cal_file,ra_center,dec_center,position_angle,pixscale,dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy, img_res) = star
      cv2.rectangle(img, (new_x-2, new_y-2), (new_x + 2, new_y + 2), (255), 1)
      cv2.line(img, (six,siy), (new_x,new_y), (255), 1)
      cv2.circle(img,(six,siy), 5, (255), 1)
   if show == 1:
      cv2.imshow('pepe', img)
      cv2.waitKey(0)

   for star in merged_stars:
      (cal_file,ra_center,dec_center,position_angle,pixscale,dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy, img_res) = star
      (f_datetime, cam_id, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(cal_file)
      print("STAR RES:", img_res)
      dupe_key = str(six) + "." + str(siy)
      dist_check = 0
      for key in dupe_check:
         ix, iy = key.split(".")
         dupe_dist = calc_dist((int(ix),int(iy)),(six,siy))
         if dupe_dist < 10 and dupe_dist != 0 and dupe_dist < std_dev_dist :
            dist_check = dist_check + 1
            #print("STAR DUPE DIST:", cam_id, six,siy,ix,iy,dupe_dist)
         

      #if img_res <= inc_limit and dupe_key not in dupe_check and dist_check == 0:
      if dupe_key not in dupe_check and dist_check < 2 and img_res < std_dev_dist:
         good_merge.append(star)
         cv2.rectangle(img, (new_x-2, new_y-2), (new_x + 2, new_y + 2), (255), 1)
         cv2.line(img, (six,siy), (new_x,new_y), (255), 1)
         cv2.circle(img,(six,siy), 5, (255), 1)
      else:
         print("DUPE STAR DETECTED:", six,siy)

      if dupe_key not in dupe_check:
         dupe_check[dupe_key] = 1 
      else: 
         dupe_check[dupe_key] = dupe_check[dupe_key] + 1
   if show == 1:
      cv2.imshow('pepe', img)
   cv2.waitKey(0)
   print("TOTAL GOOD MERGED STARS:", len(good_merge))
   return(good_merge)

def star_quad(x,y):
   iw = 1920
   ih = 1080
   hw = int(iw / 2)
   hh = int(ih / 2)
   quad = 0
   if x < hw and y < hh:
      quad = 1
   if x > hw and y < hh:
      quad = 2
   if x < hw and y > hh:
      quad = 3
   if x > hw and y > hh:
      quad = 4
   return(quad)

def remove_bad_pairs(merged_stars):
   good_merge = []
   quad_ang = {}
   quad_avg = [] 
   quad_ang[0] = []
   quad_ang[1] = []
   quad_ang[2] = []
   quad_ang[3] = []
   quad_ang[4] = []
   quad_avg.append(0)
   quad_avg.append(0)
   quad_avg.append(0)
   quad_avg.append(0)
   quad_avg.append(0)
   new_merged_stars = []
   for star in merged_stars:
      (cal_file,ra_center,dec_center,position_angle,dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy, img_res) = star
      angle = find_angle((new_cat_x, new_cat_y), (six,siy)) 
      quad = star_quad(six,siy)
      quad_ang[quad].append(angle)

   quad_avg[1] = np.mean(quad_ang[1])
   quad_avg[2] = np.mean(quad_ang[2])
   quad_avg[3] = np.mean(quad_ang[3])
   quad_avg[4] = np.mean(quad_ang[4])

   #print("MERGED STARS:", len(merged_stars))

   for star in merged_stars:
      good = 1
      (cal_file,ra_center,dec_center,position_angle,dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy, img_res) = star
      #print("ANG: ", new_cat_x,new_cat_y,six,siy)
      angle = find_angle((new_cat_x, new_cat_y), (six,siy)) 
      quad = star_quad(six,siy)
      avg_ang = quad_avg[quad]
      if match_dist > 5:
         ang_diff = abs(angle - avg_ang)
         if ang_diff > 20:
            #print("   ", dcname,quad,match_dist, angle,avg_ang, ang_diff)
            good = 0
      if good == 1:
         new_merged_stars.append(star) 


   return(new_merged_stars)


def clone_cal_params(cal_params_file, child_file,json_conf):
   fn = child_file.split("/")[-1]
   el = fn.split("-")
   fn = el[0]
   print("BASE NAME: ", fn)    
   image_file = child_file.replace("-calparams.json", "-stacked.png")
   (f_datetime, cam_id, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(image_file)

   meteor_json_file = image_file.replace("-stacked.png", "-reduced.json")
   meteor_json = load_json_file(meteor_json_file)
   hd_video_file = meteor_json['hd_video_file']
   hd_stack_file = hd_video_file.replace(".mp4", "-stacked.png")

   if cfe(hd_stack_file) == 0:
      print("HD FILE NOT FOUND!")
      hd_stack_file = meteor_json_file.replace(".json", "-stacked.png")
   hd_star_img = cv2.imread(hd_stack_file, 0)

   masks = get_masks(cam_id, json_conf,1)
   hd_star_img = mask_frame(hd_star_img, [], masks)

   img = hd_star_img
   image_file = hd_stack_file
   print("HD STACK FILE", image_file)

   cal_dir = "/mnt/ams2/cal/freecal/" + fn + "/"
   if cfe(cal_dir, 1) == 0:
      os.system("mkdir " + cal_dir) 
   new_cal_file = cal_dir + fn + "-calparams.json"

   print("CLONE CP: ", cal_params_file)    
   cal_params = load_json_file(cal_params_file)
   new_cal_params = cal_params
   center_az = cal_params['center_az']
   center_el = cal_params['center_el']
   print(image_file)
   rah,dech = AzEltoRADec(center_az,center_el,image_file,cal_params,json_conf)
   rah = str(rah).replace(":", " ")
   dech = str(dech).replace(":", " ")
   ra_center,dec_center = HMS2deg(str(rah),str(dech))
   new_cal_params['ra_center'] = ra_center
   new_cal_params['dec_center'] = dec_center

   close_stars = []
   #cat_image_stars, img = get_image_stars_from_catalog(image_file,json_conf,cal_params_file, masks, show = 0)

   cat_image_stars, img, no_match, res_err, match_per,cp_data = get_stars_from_image(image_file,json_conf, masks , cal_params, show = 0)

   for name,mag,ra,dec,new_cat_x,new_cat_y,ix,iy,px_dist,cal_params_file in cat_image_stars:
      close_stars.append(( name,mag,ra,dec,0,0,px_dist,new_cat_x,new_cat_y,0,0,new_cat_x,new_cat_y,ix,iy,px_dist))

   print("AZ/EL/RA/DEC:", center_az, center_el, ra_center, dec_center, len(close_stars))


   new_cal_params['close_stars']  = close_stars 
   print("SAVING CLONE:", new_cal_file)
   save_json_file(new_cal_file, new_cal_params)
   return(new_cal_params, new_cal_file)


def minimize_fov_pos(meteor_json_file, image_file, json_conf, cal_params = None, show=0 ):
   debug = open("debug.txt", "w")
   if cal_params is None:
      cal_params = load_json_file(cal_params_file)
   #if "fov_fit" in cal_params:
   #   if cal_params['fov_fit'] == 1:
   #      print("Skip already done the best we could do.")
         #return(0,0)
   cal_params['device_lat'] = json_conf['site']['device_lat']
   cal_params['device_lng'] = json_conf['site']['device_lng']
   cal_params['device_alt'] = json_conf['site']['device_alt']
   cal_params['orig_ra_center'] = cal_params['ra_center']
   cal_params['orig_dec_center'] = cal_params['dec_center']

   cal_params['orig_az_center'] = cal_params['center_az']
   cal_params['orig_el_center'] = cal_params['center_el']
   cal_params['orig_pos_ang'] = cal_params['position_angle']
   cal_params['orig_pixscale'] = cal_params['pixscale']

   close_stars = cal_params['cat_image_stars'] 

   print("BEFORE STARS:", len(close_stars))

   close_stars = remove_dupe_cat_stars(close_stars)
   cal_params['close_stars'] = close_stars
   paired_stars = cal_params['close_stars']
   #print("AFTER:", len(close_stars))
   org_az = cal_params['center_az']
   org_el = cal_params['center_el']
   org_pos = cal_params['position_angle']
   
   (f_datetime, cam_id, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(image_file)
   masks = get_masks(cam_id, json_conf,1)

   
   this_poly = np.zeros(shape=(4,), dtype=np.float64)
   #this_poly[0] = 0 
   #this_poly[1] = 0
   #this_poly[2] = 0

   #print(meteor_json_file)
   if "cal_params" not in meteor_json_file and "hd_images" in image_file:
      temp = {}
      temp['cal_params'] = cal_params
      meteor_json = temp


   if type(meteor_json_file) is str:
      #print("METEOR JSON FILE IS STRING")
      meteor_json_file = meteor_json_file.replace(".json", "-reduced.json")
      meteor_json = load_json_file(meteor_json_file)
      hd_video_file = meteor_json['hd_video_file']
      hd_stack_file = hd_video_file.replace(".mp4", "-stacked.png")
   else: 
      #print("METEOR JSON FILE IS DICT")
      #print(meteor_json_file)
      # something might break here...
      if "freecal" in image_file:
         meteor_json = {}
         meteor_json['cal_params'] = meteor_json_file 
         cal_params = meteor_json_file
      else:
         meteor_json['cal_params'] = cal_params 
      image_file = image_file.replace("-calparams", "")
      meteor_json_file = image_file.replace("-stacked.png", "-calparams.json")
      #print("MIKE MJF(calfile):", meteor_json_file)
      hd_stack_file = image_file
      hd_stack_file = hd_stack_file.replace("-stacked-stacked", "-stacked")
   if cfe(hd_stack_file) == 0:
      print("HD FILE NOT FOUND!", hd_stack_file)
      hd_stack_file = meteor_json_file.replace(".json", "-stacked.png")
   hd_star_img = cv2.imread(hd_stack_file, 0)
   img = hd_star_img
   image_file = hd_stack_file

   if cfe(image_file) == 0:
      image_file = meteor_json['sd_stack'].replace(".png", "-stacked.png")
 
   img = cv2.imread(image_file,0)
   oimg = img.copy()
   img = cv2.resize(img, (1920,1080))
   oimg = mask_frame(oimg, [], masks)
   img = mask_frame(img, [], masks)

  

   #print(cal_params['x_poly'])

   #print("CAL VARS:", cal_params['center_az'], cal_params['center_el'], cal_params['position_angle'], cal_params['pixscale'])
 
   cal_params_orig = cal_params.copy()
   #cal_params['x_poly'] = np.zeros(shape=(15,), dtype=np.float64)
   #cal_params['y_poly'] = np.zeros(shape=(15,), dtype=np.float64)

   res = reduce_fov_pos(this_poly, cal_params,image_file,oimg,json_conf, paired_stars,0,show)
   total_dist = 0
   if res < 2:
      res = 2
   #print("RES IS ", res)
   best_paired_stars = []
   for data in paired_stars:
      iname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,old_cat_x,old_cat_y,six,siy,cat_dist  = data
      new_x = int(new_x)  
      new_y = int(new_y)  
      six = int(six)  
      siy = int(siy)  
      cv2.rectangle(img, (new_x-2, new_y-2), (new_x + 2, new_y + 2), (255), 1)
      cv2.line(img, (six,siy), (new_x,new_y), (255), 1)
      cv2.circle(img,(six,siy), 5, (255), 1)
      total_dist = total_dist + match_dist
      cv2.putText(img, iname,  (six,siy), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 1)
      #print("DIST/RES:", cat_dist, res * 2)
      if True:
      #if cat_dist <= res * res:
         best_paired_stars.append(data)

   paired_stars = best_paired_stars

   desc = "Initial Res: " + str(res)
   cv2.putText(img, desc,  (20,50), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 1)
   show_img = cv2.resize(img, (960,540))
   #if show == 1:
      #cv2.imshow(cam_id, show_img)
      #cv2.waitKey(1) 

 
   print("START RES:", cam_id, res, len(paired_stars))   
   if res < .5: 
      # Res is good No need to recalibrate!
      #print("Res is good no need to recal")
      return(0,cal_params)

   res = scipy.optimize.minimize(reduce_fov_pos, this_poly, args=( cal_params,image_file,oimg,json_conf, paired_stars,1,show), method='Nelder-Mead')

   fov_pos_poly = res['x']
   fov_pos_fun = res['fun']
   cal_params['x_poly'] = cal_params_orig['x_poly']
   cal_params['y_poly'] = cal_params_orig['y_poly']
   final_res = reduce_fov_pos(fov_pos_poly, cal_params,image_file,img,json_conf, paired_stars,0,show)

   cal_params['fov_pos_poly'] = fov_pos_poly.tolist()
   cal_params['fov_pos_fun'] = fov_pos_fun
   cal_params['total_res_px'] = fov_pos_fun

   cal_params['center_az'] = float(cal_params['orig_az_center']) + float(fov_pos_poly[0] )
   cal_params['center_el'] = float(cal_params['orig_el_center']) + float(fov_pos_poly[1] )
   cal_params['position_angle'] = float(cal_params['position_angle']) + float(fov_pos_poly[2] )

   if type(meteor_json_file) is str:
      rah,dech = AzEltoRADec(cal_params['center_az'],cal_params['center_el'],meteor_json_file,cal_params,json_conf)
   else: 
      rah,dech = AzEltoRADec(cal_params['center_az'],cal_params['center_el'],image_file,cal_params,json_conf)
   rah = str(rah).replace(":", " ")
   dech = str(dech).replace(":", " ")
   ra_center,dec_center = HMS2deg(str(rah),str(dech))
   cal_params['ra_center'] = ra_center
   cal_params['dec_center'] = dec_center
   cal_params['fov_fit'] = 1 
   close_stars = []
   cat_image_stars, img = get_image_stars_from_catalog(image_file,json_conf,meteor_json_file, masks, cal_params, show = 0)
   for name,mag,ra,dec,new_cat_x,new_cat_y,ix,iy,px_dist,cal_params_file in cat_image_stars:
      close_stars.append(( name,mag,ra,dec,0,0,px_dist,new_cat_x,new_cat_y,0,0,new_cat_x,new_cat_y,ix,iy,px_dist))
   cal_params['close_stars'] =  close_stars
   cal_params['close_stars'] = paired_stars

   # update the reduction values with new calibration
   video_file = meteor_json_file.replace(".json", ".mp4")
   video_file = video_file.replace("-reduced", "")
   os.system("cd /home/ams/amscams/pythonv2; ./reducer3.py cm " + video_file + " >/mnt/ams2/tmp/rd3.txt")

   return(fov_pos_poly,cal_params)


def remove_dupe_cat_stars(paired_stars):
   used = {}
   new_paired_stars = []
   for data in paired_stars:
      if len(data) == 16:
         iname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,old_cat_x,old_cat_y,six,siy,cat_dist  = data
      if len(data) == 10:
         name,mag,ra,dec,new_cat_x,new_cat_y,six,siy,px_dist,cp_file = data
      used_key = str(six) + "." + str(siy)
      if used_key not in used:
         new_paired_stars.append(data)
         used[used_key] = 1
   return(new_paired_stars)


def reduce_fov_pos(this_poly, in_cal_params, cal_params_file, oimage, json_conf, paired_stars, min_run = 1, show=0):
   image = oimage.copy()
   image = cv2.resize(image, (1920,1080))
   # cal_params_file should be 'image' filename
   org_az = in_cal_params['center_az'] 
   org_el = in_cal_params['center_el'] 
   org_pixscale = in_cal_params['orig_pixscale'] 
   org_pos_angle = in_cal_params['orig_pos_ang'] 
   new_az = in_cal_params['center_az'] + this_poly[0]
   new_el = in_cal_params['center_el'] + this_poly[1]
   position_angle = float(in_cal_params['position_angle']) + this_poly[2]
   pixscale = float(in_cal_params['orig_pixscale']) + this_poly[3]
   #pixscale = float(in_cal_params['pixscale']) + this_poly[3]



   rah,dech = AzEltoRADec(new_az,new_el,cal_params_file,in_cal_params,json_conf)
   rah = str(rah).replace(":", " ")
   dech = str(dech).replace(":", " ")
   ra_center,dec_center = HMS2deg(str(rah),str(dech))

   in_cal_params['position_angle'] = position_angle
   in_cal_params['ra_center'] = ra_center
   in_cal_params['dec_center'] = dec_center
   in_cal_params['pixscale'] = pixscale 
   in_cal_params['device_lat'] = json_conf['site']['device_lat']
   in_cal_params['device_lng'] = json_conf['site']['device_lng']
   in_cal_params['device_alt'] = json_conf['site']['device_alt']

   for data in paired_stars:
      iname,mag,o_ra,o_dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,old_cat_x,old_cat_y,six,siy,cat_dist  = data
      cv2.rectangle(image, (old_cat_x-5, old_cat_y-5), (old_cat_x + 5, old_cat_y + 5), (255), 1)
      cv2.line(image, (six,siy), (old_cat_x,old_cat_y), (255), 1)
      cv2.circle(image,(six,siy), 10, (255), 1)

   fov_poly = 0
   pos_poly = 0
   x_poly = in_cal_params['x_poly']
   y_poly = in_cal_params['y_poly']
   #print(in_cal_params['ra_center'], in_cal_params['dec_center'], in_cal_params['center_az'], in_cal_params['center_el'], in_cal_params['position_angle'], in_cal_params['pixscale'], this_poly)
   cat_stars = get_catalog_stars(fov_poly, pos_poly, in_cal_params,"x",x_poly,y_poly,min=0)
   new_res = []
   new_paired_stars = []
   used = {}
   org_star_count = len(paired_stars)
   for cat_star in cat_stars:
      (name,mag,ra,dec,new_cat_x,new_cat_y) = cat_star
      dname = name.decode("utf-8")
      for data in paired_stars:
         iname,mag,o_ra,o_dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,old_cat_x,old_cat_y,six,siy,cat_dist  = data
#dname == iname:
         if (ra == o_ra and dec == o_dec) or (iname == dname and iname != ''):
            pdist = calc_dist((six,siy),(new_cat_x,new_cat_y))
            if pdist <= 50:
               new_res.append(pdist)
               used_key = str(six) + "." + str(siy)
               if used_key not in used: 
                  new_paired_stars.append((iname,mag,ra,dec,new_cat_x,new_cat_y,six,siy,pdist))
                   
                  used[used_key] = 1
                  new_cat_x,new_cat_y = int(new_cat_x), int(new_cat_y)
                  cv2.rectangle(image, (new_cat_x-5, new_cat_y-5), (new_cat_x + 5, new_cat_y + 5), (255), 1)
                  cv2.line(image, (six,siy), (new_cat_x,new_cat_y), (255), 1)
                  cv2.circle(image,(six,siy), 10, (255), 1)
          


   paired_stars = new_paired_stars
   tres  =0 
   for iname,mag,ra,dec,new_cat_x,new_cat_y,six,siy,pdist in new_paired_stars:
      tres = tres + pdist
     
   orig_star_count = len(in_cal_params['cat_image_stars'])

   if len(paired_stars) > 0:
      avg_res = tres / len(paired_stars) 
   else:
      avg_res = 9999999
      res = 9999999

   if orig_star_count > len(paired_stars):
      pen = orig_star_count - len(paired_stars)
   else:
      pen = 0
 
   avg_res = avg_res + (pen * 10)
   show_res = avg_res - (pen*10) 
   desc = "RES: " + str(show_res) + " " + str(len(new_paired_stars)) + " " + str(orig_star_count) + " PEN:" + str(pen)
   cv2.putText(image, desc,  (10,50), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 1)
   desc2 = "CENTER AZ/EL/POS" + str(new_az) + " " + str(new_el) + " " + str(in_cal_params['position_angle']) 
   cv2.putText(image, desc2,  (10,80), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 1)

   desc2 = "PX SCALE:" + str(in_cal_params['pixscale'])
   cv2.putText(image, desc2,  (10,110), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 1)


   print("AVG RES:", avg_res, len(paired_stars), "/", org_star_count, new_az, new_el, ra_center, dec_center, position_angle)
   if show == 1:
      show_img = cv2.resize(image, (960,540))
      if "cam_id" in in_cal_params:
         cv2.imshow(cam_id, show_img)
      else:
         cv2.imshow('pepe', show_img)
      if min_run == 1:
         cv2.waitKey(1) 
      else:
         cv2.waitKey(1) 
   in_cal_params['position_angle'] = org_pos_angle
   if min_run == 1:
      return(avg_res)
   else:
      return(show_res)


def minimize_lat_lon(json_conf,cal_params_file,all_paired_stars,show=0,latlon_poly=None):
   cal_params = load_json_file(cal_params_file)
   cal_params['device_lat'] = json_conf['site']['device_lat']
   cal_params['device_lon'] = json_conf['site']['device_lng']
   cal_params['device_alt'] = json_conf['site']['device_alt']
   cal_params['orig_ra_center'] = cal_params['ra_center']
   cal_params['orig_dec_center'] = cal_params['dec_center']
   cal_params['orig_pos_ang'] = cal_params['position_angle']

   org_lat = json_conf['site']['device_lat'] 
   org_lon = json_conf['site']['device_lng'] 
   org_alt = json_conf['site']['device_alt'] 
   org_az = cal_params['center_az'] 
   org_el = cal_params['center_el'] 
   json_conf['site']['org_device_lat']  = org_lat
   json_conf['site']['org_device_lng']  = org_lon
   json_conf['site']['org_device_alt']  = org_alt

   if latlon_poly is None:
      this_poly = np.zeros(shape=(3,), dtype=np.float64)
      this_poly[0] = .1
      this_poly[1] = .1
      this_poly[2] = 1
   else:
      this_poly = latlon_poly


   res = scipy.optimize.minimize(reduce_latlon, this_poly, args=(cal_params,cal_params_file,json_conf, all_paired_stars,show), method='Nelder-Mead')
   latlon_poly = res['x']
   latlon_fun = res['fun']
   cal_params['latlon_poly'] = latlon_poly.tolist()
   cal_params['latlon_fun'] = latlon_fun
   print(latlon_poly)
   print(latlon_fun)
   return(latlon_poly)

def reduce_latlon(this_poly, cal_params, cal_params_file, json_conf, all_paired_stars, show=0):





   all_night_res = []
   for image_file in all_paired_stars:
      paired_stars = all_paired_stars[image_file]
      cal_params_file = paired_stars[0][-1]
      cal_params = load_json_file(cal_params_file)
      cal_params['orig_ra_center'] = cal_params['ra_center']
      cal_params['orig_dec_center'] = cal_params['dec_center']
      (f_datetime, cam_id, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(cal_params_file)
      date = fy + "_" + fm + "_" + fd
      org_cal_date = fy + "/" + fm + "/" + fd + " " + fh + ":" + fmin + ":" + fs
      (f_datetime, cam_id, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(image_file)
      date = fy + "_" + fm + "_" + fd
      new_cal_date = fy + "/" + fm + "/" + fd + " " + fh + ":" + fmin + ":" + fs
      org_lat = json_conf['site']['org_device_lat'] 
      org_lon = json_conf['site']['org_device_lng'] 
      org_alt = json_conf['site']['org_device_alt'] 
      org_az = cal_params['center_az'] 
      org_el = cal_params['center_el'] 

   
      min_mod = 30
      lat = float(org_lat) + float(this_poly[0])
      lon = float(org_lon) + float(this_poly[1])
      alt = float(org_alt) + float(this_poly[2])
      #print("ORG LAT,LON:", org_lat,org_lon)
      #print("NEW LAT,LON:", lat,lon)

      json_conf['site']['device_lat'] = str(lat)
      json_conf['site']['device_lng'] = str(lon)
      json_conf['site']['alt'] = str(alt )

      orig_ra_center = cal_params['orig_ra_center']
      orig_dec_center = cal_params['orig_dec_center']

      #print("REFIND ORG AZ, EL WITH NEW LAT LON", orig_ra_center,orig_dec_center,lat,lon,alt)
      new_az, new_el= radec_to_azel(orig_ra_center,orig_dec_center, org_cal_date,json_conf)
      #print("NEW ORIG AZ/EL:", new_az,new_el)
      # print("AVG RES LATLON AZ,EL:", lat,lon,alt,new_az,new_el)
  
      rah,dech = AzEltoRADec(new_az,new_el,image_file,cal_params,json_conf)
      rah = str(rah).replace(":", " ")
      dech = str(dech).replace(":", " ")

      #rahh = RAdeg2HMS(rah)
      ra_center,dec_center = HMS2deg(str(rah),str(dech))


      cal_params['ra_center'] = ra_center
      cal_params['dec_center'] = dec_center

      fov_poly = cal_params['fov_poly']
      pos_poly = cal_params['pos_poly']
      x_poly = cal_params['x_poly']
      y_poly = cal_params['y_poly']
      cat_stars = get_catalog_stars(fov_poly, pos_poly, cal_params,"x",x_poly,y_poly,min=0)

      new_res = []
      new_paired_stars = []
      used = {}
      for cat_star in cat_stars:
         (name,mag,ra,dec,new_cat_x,new_cat_y) = cat_star
         dname = name.decode("utf-8")
         for iname,imag,ira,idec,inew_cat_x,inew_cat_y,ix,iy,ipx_dist,cp_file in paired_stars:
            pdist = calc_dist((ix,iy),(new_cat_x,new_cat_y))
            if pdist <= 15:
               new_res.append(pdist)
               used_key = str(ix) + "." + str(iy)
               if used_key not in used: 
                  new_paired_stars.append((iname,imag,ira,idec,inew_cat_x,inew_cat_y,ix,iy,ipx_dist))
               used[used_key] = 1



      tres = np.sum(new_res)
      missing = len(paired_stars) - len(new_paired_stars)
      extra_bad = missing * 1
      avg_res = (tres / len(new_paired_stars)) + missing
      all_night_res.append(avg_res)

   all_night_avg_res  = np.sum(all_night_res) / len(all_night_res)
   print("ALL NIGHT AVG RES:", all_night_avg_res)
   return(all_night_avg_res)

def get_sd_files(day,cam_id,json_conf):
   base_dir = json_conf['site']['proc_dir'] + "/" + day + "/images/*" + cam_id +  "*.png"
   sd_files = []
   all_files = sorted(glob.glob(base_dir))
   for file in all_files:
      if "-tn" not in file and "-night-stack" not in file and "-hd-stack" not in file:
         sd_files.append(file)

   return(sd_files)

def track_stars (day,json_conf,scmd='',cal_params_file=None,show=0):
   if show == 1:
      cv2.namedWindow('pepe')
   min_mod = 60

   # for each cam! 
   cameras = json_conf['cameras']
   cam_ids = []
   for camera in cameras:
      cam_ids.append((cameras[camera]['cams_id']))

   all_i_files = {}
   for cam_id in cam_ids:
      masks = get_masks(cam_id, json_conf,1)
      sd_files = get_sd_files(day,cam_id,json_conf)
      #print("SD FILES:", len(sd_files))
      if len(sd_files) == 0:
         continue
      poss = get_active_cal_file(sd_files[4])
      cal_params_file = poss[0][0]

      #print("CAL FILE:", cal_params_file) 
      fc = 0
      res_night = 0
      tres = 0
      latlon_poly = np.zeros(shape=(3,), dtype=np.float64)
      ufc = 1
      for file in sd_files:
         if fc % min_mod == 0:
            if cal_params_file is None:
               stars = get_image_stars(file,show) 
            else:
    
               #print("INFO:", file, cal_params_file)
               stars,img = get_image_stars_from_catalog(file,json_conf,cal_params_file, masks, show)
               tres = 0
               #print("STARS:", len(stars))
               if len(stars) > 0:
                  for star in stars:
                     tres = float(tres) + float(star[-2])
                  tres_avg = tres / len(stars)
                  res_night = res_night + tres_avg
                  if ufc > 0:
                     res_night_avg =res_night / ufc
                  else:
                     res_night_avg = res_night
                  #print(len(stars) , "STARS:", "RES:", tres_avg, res_night_avg)
                  all_i_files[file] = stars
               else:
                  res_night_avg = 999
             

               simg = cv2.resize(img, (960,540))
               desc = str(res_night_avg)
               cv2.putText(simg, desc,  (480,270), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
               if show == 1:
                  cv2.imshow('pepe', simg)
                  cv2.waitKey(1)
            ufc = ufc + 1
         fc = fc + 1
      res_night = 1
   
   star_track_file = "/mnt/ams2/cal/autocal/startrack/" + day + "-startrack.json"
   save_json_file(star_track_file, all_i_files)




   if scmd == 'latlon':
      orig_lat = json_conf['site']['device_lat']
      orig_lon = json_conf['site']['device_lng']
      orig_alt = json_conf['site']['device_alt']

      latlon_poly = minimize_lat_lon(json_conf,cal_params_file,all_i_files,show,latlon_poly)

      print("FINAL LAT LON POLY")
      print("------------------")
      print("Lat Poly: ", latlon_poly[0])
      print("Lon Poly: ", latlon_poly[1])
      print("Alt Poly: ", latlon_poly[2])
      new_lat = float(json_conf['site']['device_lat']) + float(latlon_poly[0])
      new_lon = float(json_conf['site']['device_lng']) + float(latlon_poly[1])
      new_alt = float(json_conf['site']['device_alt']) + float(latlon_poly[2])
      print("Orig Lat,Lon:", orig_lat,orig_lon,orig_alt)
      print("JSON Lat,Lon:", json_conf['site']['device_lat'], json_conf['site']['device_lng'])
      print("Orig Alt:", json_conf['site']['device_alt'])
      print("New Lat,Lon:", new_lat,new_lon)
      print("New Alt:", new_alt)

   return(all_i_files) 

def flatten_all_stars(all_stars, json_conf):
   cameras = json_conf['cameras']
   cam_ids = []
   multi_merge = {}
   cp_files = {}
   for camera in cameras:
      multi_merge[cameras[camera]['cams_id']]  = {}
      cp_files[cameras[camera]['cams_id']]  = ""

   for file in all_stars:
      print(file, len(all_stars))
      (f_datetime, cam_id, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(file)
      multi_merge[cam_id][file] = []
      for star in all_stars[file]:
         name,mag,ra,dec,new_cat_x,new_cat_y,ix,iy,px_dist,cal_params_file = star
         (f_datetime, cam_id, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(cal_params_file)
         cal_params = load_json_file(cal_params_file)
         cp_files[cam_id] = cal_params_file
         img_ra = ra
         img_dec = dec
         match_dist = px_dist
         ra_center = cal_params['ra_center']
         dec_center = cal_params['dec_center']
         img_az = cal_params['center_az']
         img_el = cal_params['center_el']
         img_res = px_dist
         # find new ra/dec center
         rah,dech = AzEltoRADec(img_az,img_el,file,cal_params,json_conf)
         rah = str(rah).replace(":", " ")
         dech = str(dech).replace(":", " ")
         ra_center,dec_center = HMS2deg(str(rah),str(dech))
         #print("CENTER AZ/EL", img_az, img_el, ra_center, dec_center)

         if match_dist < 5:
            multi_merge[cam_id][file].append((cal_params_file,ra_center,dec_center,name,mag,ra,dec,img_ra,img_dec,match_dist,new_cat_x,new_cat_y,img_az,img_el,new_cat_x,new_cat_y,ix,iy, img_res))
   return(multi_merge) 

def hd_cal(all_i_files, json_conf, day, show = 0):
   print("HD CAL")
   hd_day_dir = "/mnt/ams2/cal/autocal/hdimages/" + day + "/"
   if cfe(hd_day_dir, 1) == 0: 
      os.system("mkdir " + hd_day_dir)

   good_hd_stacks = []

   all_new_i_files = {}

   for file in all_i_files:
      hd_stack_file = file.replace("-stacked.png", "-hd-stacked.png")
      total_stars = len(all_i_files[file])
      if cfe(hd_stack_file) == 0:
         print(file, total_stars)
         hd_file, hd_trim,time_diff_sec, dur = find_hd_file_new(file, 0, 10, 0)
         print("LOADING:", hd_file)
         if hd_file is not None and total_stars > 10:
            frames = load_video_frames(hd_file, json_conf, 150,0,[],1)
            print(len(frames)) 
            stack_file, stack_img = stack_frames(frames, hd_file, 1)
            exit() 
         #print(stack_file, stack_img.shape) 
            cv2.imwrite(hd_stack_file, stack_img)
            good_hd_stacks.append(hd_stack_file)
 
         #print(file, hd_file, hd_trim,time_diff_sec,dur)
      else:
         print("HD FILE ALREADY DONE:", hd_stack_file, total_stars)
         if total_stars > 10:
            good_hd_stacks.append(hd_stack_file)

   for hd_stack_file in good_hd_stacks:
      (f_datetime, cam_id, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(file)
      masks = get_masks(cam_id, json_conf,0)

      hd_stack_img = cv2.imread(hd_stack_file,0)
      hd_stack_img = mask_frame(hd_stack_img, [], masks)
      print("HD:", hd_stack_file)

      poss = get_active_cal_file(hd_stack_file)
      cal_params_file = poss[0][0]
      masks = []

      cat_image_stars,img = get_image_stars_from_catalog(hd_stack_file,json_conf,cal_params_file, masks, show)

      all_new_i_files[hd_stack_file] = cat_image_stars
   #flat_stars = flatten_all_stars(all_i_files, json_conf)
   for file in all_new_i_files:
      hd_stack_img = cv2.imread(file,0)
      print("HD FILE:", file)
      file_stars = all_new_i_files[file]
      for file_star in file_stars:
         (name,mag,ra,dec,new_cat_x,new_cat_y,ix,iy,px_dist,cal_params_file) = file_star
         #(cal_params_file,ra_center,dec_center,name,mag,ra,dec,img_ra,img_dec,match_dist,new_cat_x,new_cat_y,img_az,img_el,new_cat_x,new_cat_y,ix,iy, img_res) = file_star
         #if px_dist < 10:
         #   cv2.rectangle(hd_stack_img, (new_cat_x-2, new_cat_y-2), (new_cat_x + 2, new_cat_y + 2), (128, 128, 128), 1)
         #   cv2.line(hd_stack_img, (ix,iy), (new_cat_x,new_cat_y), (255), 2)
         #   cv2.circle(hd_stack_img,(ix,iy), 5, (128,128,128), 1)

      plate_img, user_stars = make_plate_image(hd_stack_img, file_stars)
      plate_img_file = file.replace(".png", ".jpg")
      cv2.imwrite(plate_img_file, plate_img)
     
      el = plate_img_file.split("/")
      day_dir = el[-3] 
      fn = el[-1] 
      hd_day_dir = "/mnt/ams2/cal/autocal/hdimages/" + day_dir + "/"
      new_plate_img_file = hd_day_dir + fn
      solved_file = new_plate_img_file.replace(".jpg", ".solved")
      failed_file = new_plate_img_file.replace(".jpg", ".failed")

      user_star_file = new_plate_img_file.replace(".jpg", "-user-stars.json")
      json_user_stars = {}
      json_user_stars['user_stars'] = user_stars
      save_json_file(user_star_file, json_user_stars)

      if cfe(failed_file) == 0 and cfe(solved_file) == 0:
         if cfe(hd_day_dir, 1) == 0: 
            os.system("mkdir " + hd_day_dir)
         os.system("cp " + plate_img_file + " " + hd_day_dir)
         os.system("cp " + file + " " + hd_day_dir)

         os.system("./plateSolve.py " + new_plate_img_file)
      else: 
         print("SKIP: Astrometry solver already run on file:", solved_file, failed_file)
   
     

      if show == 1:
         show_img = cv2.resize(plate_img, (960,540))
         cv2.imshow('pepe', show_img)
         cv2.waitKey(1) 

   master_cal_params = avg_cal_files(hd_day_dir,json_conf)
   master_cal_params_file = hd_day_dir + day_dir + "-master_cal_params.json"
   all_star_file = hd_day_dir + day_dir + "-allstars.json"
   save_json_file(all_star_file, all_new_i_files)
   save_json_file(master_cal_params_file, master_cal_params)
   print(master_cal_params_file)
   print(all_star_file)

   #multi_merge(all_i_files,master_cal_params,json_conf)

   #multifit?

def avg_cal_files(cal_dir,json_conf):
   cameras = json_conf['cameras']
   cam_ids = []
   multi_merge = {}
   cp_files = {}
   master_cal_params = {}
   for camera in cameras:
      cam_id = cameras[camera]['cams_id']
      master_cal_params[cam_id] = {}
      glob_dir = cal_dir + "/*" + cam_id + "*-calparams.json"
      cp_files = glob.glob(glob_dir)
      m_az, m_el, m_px, m_pa = avg_cal_files_cam(cp_files)
      master_cal_params[cam_id]['center_az'] = float(m_az)
      master_cal_params[cam_id]['center_el'] = float(m_el)
      master_cal_params[cam_id]['pixscale'] = float(m_px)
      master_cal_params[cam_id]['position_angle'] = float(m_pa)
      master_cal_params[cam_id]['imagew'] = 1920
      master_cal_params[cam_id]['imageh'] = 1080
   return(master_cal_params)



def avg_cal_files_cam(cp_files):
   azs = []
   els = []
   pxs = []
   pas = []
   for cal_param_file in cp_files:
      print(cal_param_file)
      cal_params = load_json_file(cal_param_file)
      center_az = cal_params['center_az']
      center_el = cal_params['center_el']
      pixscale = cal_params['pixscale']
      position_angle = cal_params['position_angle']
      azs.append(center_az)
      els.append(center_el)
      pxs.append(pixscale)
      pas.append(position_angle)
   m_az = float(np.median(np.array(azs).astype(np.float)))
   m_el = float(np.median(np.array(els).astype(np.float)))
   m_px = float(np.median(np.array(pxs).astype(np.float)))
   m_pa = float(np.median(np.array(pas).astype(np.float)))

   for cal_param_file in cp_files:
      print(cal_param_file)
      cal_params = load_json_file(cal_param_file)
      center_az = cal_params['center_az']
      center_el = cal_params['center_el']
      pixscale = cal_params['pixscale']
      position_angle = cal_params['position_angle']
      cal_params['orig_center_az'] = center_az
      cal_params['orig_center_el'] = center_el
      cal_params['orig_pixscale'] = pixscale 
      cal_params['orig_position_angle'] = position_angle
      cal_params['center_az'] = m_az 
      cal_params['center_el'] = m_el 
      cal_params['pixscale'] = m_px 
      cal_params['position_angle'] = m_pa 



   return(m_az,m_el,m_px,m_pa) 
   

def make_plate_image(image, file_stars): 
   ih, iw = image.shape
   for file_star in file_stars:
      (name,mag,ra,dec,new_cat_x,new_cat_y,ix,iy,px_dist,cal_params_file) = file_star

   plate_image = np.zeros((ih,iw),dtype=np.uint8)
   hd_stack_img = image
   hd_stack_img_an = hd_stack_img.copy()
   star_points = []
   for file_star in file_stars:
      (name,mag,ra,dec,new_cat_x,new_cat_y,ix,iy,px_dist,cal_params_file) = file_star
         
      x,y = int(ix),int(iy)
      #cv2.circle(hd_stack_img_an, (int(x),int(y)), 5, (128,128,128), 1)
      y1 = y - 15
      y2 = y + 15
      x1 = x - 15
      x2 = x + 15
      x1,y1,x2,y2= bound_cnt(x,y,iw,ih,15)
      cnt_img = hd_stack_img[y1:y2,x1:x2]
      ch,cw = cnt_img.shape
      max_pnt,max_val,min_val = cnt_max_px(cnt_img)
      mx,my = max_pnt
      mx = mx - 15
      my = my - 15
      cy1 = y + my - 15
      cy2 = y + my +15
      cx1 = x + mx -15
      cx2 = x + mx +15
      cx1,cy1,cx2,cy2= bound_cnt(x+mx,y+my,iw,ih)
      if ch > 0 and cw > 0:
         cnt_img = hd_stack_img[cy1:cy2,cx1:cx2]
         bgavg = np.mean(cnt_img)
         cnt_img = clean_star_bg(cnt_img, bgavg + 3)

         cv2.rectangle(hd_stack_img_an, (x+mx-5-15, y+my-5-15), (x+mx+5-15, y+my+5-15), (128, 128, 128), 1)
         cv2.rectangle(hd_stack_img_an, (x+mx-15-15, y+my-15-15), (x+mx+15-15, y+my+15-15), (128, 128, 128), 1)
         star_points.append([x+mx,y+my])
         plate_image[cy1:cy2,cx1:cx2] = cnt_img

   points_json = {}
   points_json['user_stars'] = star_points

   return(plate_image,star_points)

def test_star(cnt_img, max_loc ):
   max_x, max_y = max_loc
   ch, cw = cnt_img.shape
   avg_px = np.mean(cnt_img)
   #print("TEST STAR:", max_x, max_y)
   star_points = {}
   five_point_flux = 0

   if max_x + 1 < cw and max_y + 1 < ch and max_x - 1 > 0 and max_y - 1 > 0:
      # main center point
      #key = str(max_x) + "." + str(max_y)
      #val = cnt_img[max_y,max_x]
      #star_points[key] = val

      # directly above center
      key = str(max_x+1) + "." + str(max_y)
      val = cnt_img[max_y,max_x+1]
      star_points[key] = val

      # directly below center
      key = str(max_x-1) + "." + str(max_y)
      val = cnt_img[max_y,max_x-1]
      star_points[key] = val

      # directly left of center
      key = str(max_x) + "." + str(max_y-1)
      val = cnt_img[max_y-1,max_x]
      star_points[key] = val

      # directly right of center
      key = str(max_x) + "." + str(max_y+1)
      val = cnt_img[max_y+1,max_x]
      star_points[key] = val

      for key in star_points:
         px_diff = star_points[key] - avg_px
         #print("STAR POINTS:", key, avg_px, star_points[key], px_diff)
         five_point_flux = five_point_flux + px_diff
   return(five_point_flux)

def find_star_in_crop(cnt_img):
   mx = 0
   my = 0
   star_status = 1 
   cnth,cntw = cnt_img.shape
   max_px = np.max(cnt_img)
   avg_px = np.mean(cnt_img)
   px_diff = max_px - avg_px
   min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(cnt_img)
   five_point_flux = test_star(cnt_img, max_loc)
   if five_point_flux < 60:
      return(0, 0,0,(0,0))


   thresh = int(max_px - (px_diff / 3))
   _, threshold = cv2.threshold(cnt_img.copy(), thresh, 255, cv2.THRESH_BINARY)

   #thresh_obj = cv2.dilate(threshold.copy(), None , iterations=4)
   cnt_res = cv2.findContours(threshold.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

   if len(cnt_res) == 3:
      (_, cnts, xx) = cnt_res
   elif len(cnt_res) == 2:
      (cnts, xx) = cnt_res
   cnt_cpy = cnt_img.copy()
   #print("CNTS:", len(cnts))
   if len(cnts) > 1:
      star_status = 0
      #print("Fail cnts:", len(cnts))
   if len(cnts) == 0:
      star_status = 0
      #print("Fail no cnts:", len(cnts))
   if len(cnts) > 0:
      for (i,c) in enumerate(cnts):
         x,y,w,h = cv2.boundingRect(cnts[i])
         #cv2.rectangle(cnt_cpy, (x, y), (x+w, y+h), (128, 128, 128), 1)
         if w < 1 or h < 1:
            #print("Fail cnt size < 1:", w,h)
            star_status = 0
         #print("WH:", w,h)
         if w > 10 or h > 10:
            #print("Fail cnt size > 10:", w,h)
            star_status = 0 

      mx = int(x + (w / 2))
      my = int(y + (h / 2))

   ch,cw = cnt_img.shape
   flux_img = cnt_img[y:y+h,x:x+w]
   tflux = np.sum(cnt_img)
   flux_size = cnt_img.shape[0],cnt_img.shape[1]
   bg_val = avg_px * flux_size[0] * flux_size[1]
   flux = tflux - bg_val 
   #print("FLUX: ", tflux, flux , bg_val) 

 
   #if ch != cw:
   #   star_status = 0
   #   return(0, 0,0,(0,0))
   #print(ch,cw)
   
   
   zx1 = []
   zx2 = []
   zy1 = []
   zy2 = []

   pxr = 3
   if max_px > 100:
      pxr = 5
   if max_px > 200:
      pxr = 6
   if max_px > 250:
      pxr = 9

   if px_diff > 2:
      for i in range (0,pxr):
         if mx + i < cw - 1:
            px_val = int(cnt_img[my,mx+i])
            zx1.append(px_val)
      for i in range (0,7):
         if mx - i >= 0:
            px_val = int(cnt_img[my,mx-i])
            zx2.append(px_val)
      for i in range (0,7):
         if my + i < ch - 1:
            px_val = int(cnt_img[my+i,mx])
            zy1.append(px_val)
      for i in range (0,7):
         if my - i >= 0:
            px_val = int(cnt_img[my-i,mx])
            zy2.append(px_val)
   if px_diff < 10:
      print("FAIL px_diff:", px_diff)
      star_status = 0

   if len(zx1) > 2 and len(zx2) > 2 and len(zy1) > 2 and len(zy2) > 2:
      sx1 = zx1[0] - zx1[-1]
      sx2 = zx2[0] - zx2[-1]

      sy1 = zy1[0] - zy1[-1]
      sy2 = zy2[0] - zy2[-1]
      # check total flux in each direction is high enough 

      # check shape is consistent each way
      shape_score = abs((sx1-sx2) - (sy1-sy2))
      brightness_score = sx1 + sx2 + sy1 + sy2

      #print("SCORE:", max_px, brightness_score, shape_score)
      #if max_px < 80:
      #   return(0, 0,0,(0,0))
      if brightness_score < 10:
         #return(0, 0,0,(0,0))
         #print("Fail brightness:", brightness_score)
         star_status = 0

      #if sx1 + sx2 + sy1 + sy2 < 30:
      #   return(0, 0,0,(0,0))
      ##if shape_score > 20 :
      #   return(0, 0,0,(0,0))


   #else:
      #return(0, 0,0,(0,0))
      #print("Fail zx,zy:", len(zx1), len(zx2), len(zy1), len(zy2))
      #star_status = 0

   cv2.putText(cnt_cpy, str(star_status),  (1,10), cv2.FONT_HERSHEY_SIMPLEX, .3, (255, 255, 255), 1)
   #cv2.imshow('pepe', cnt_cpy)
   #cv2.waitKey(0)
   if star_status == 0:
      return(0, 0,0,(0,0))
   else:
      return(max_px, avg_px,px_diff,(mx,my))

def get_cat_stars(file, cal_params_file, json_conf, cal_params = None):
   #print("GETTING CAT STARS:")
   #print("FILE:", file)
   #print("CP FILE:", cal_params_file)
   if cal_params == None:
      print("CAL PARAMS ARE NONE!")
      exit()
      cal_params = load_json_file(cal_params_file)

   if "lat" in cal_params:
      lat = cal_params['lat']
      lon = cal_params['lon']
      alt = cal_params['alt']
   else:
      lat = json_conf['site']['device_lat']
      lon = json_conf['site']['device_lng']
      alt = json_conf['site']['device_alt']
   ra_center = cal_params['ra_center']
   dec_center = cal_params['dec_center']
   center_az = cal_params['center_az']
   center_el = cal_params['center_el']
   rah,dech = AzEltoRADec(center_az,center_el,file,cal_params,json_conf)
   rah = str(rah).replace(":", " ")
   dech = str(dech).replace(":", " ")

   ra_center,dec_center = HMS2deg(str(rah),str(dech))

   cal_params['ra_center'] = ra_center
   cal_params['dec_center'] = dec_center
   fov_poly = 0 
   pos_poly = 0 
   x_poly = cal_params['x_poly']
   y_poly = cal_params['y_poly']

   cat_stars = get_catalog_stars(fov_poly, pos_poly, cal_params,"x",x_poly,y_poly,min=0)

   return(cat_stars)

def lookup_star_in_cat(ix,iy,cat_stars,no_poly_cat_stars, star_dist=10,):
   #print("LOOKUP:", ix,iy)
   close = []
   for cat_star in cat_stars:
      name,mag,ra,dec,new_cat_x,new_cat_y = cat_star
      # to get the plus do ra,dec fwd and then compare that to ix,iy to get the distance? Big improvement?
      px_dist = calc_dist((ix,iy),(new_cat_x,new_cat_y))
      close.append((ix,iy,px_dist,name,mag,ra,dec,new_cat_x,new_cat_y)) 
   temp = sorted(close, key=lambda x: x[2], reverse=False)
   closest = temp[0]
   six,siy,spx_dist,sname,smag,sra,sdec,snew_cat_x,snew_cat_y = closest

   key = str(closest[5]) + ":" + str(closest[6])
   if key in no_poly_cat_stars:
      no_poly_star = no_poly_cat_stars[key]
      np_name,np_mag,np_ra,np_dec,np_new_cat_x,np_new_cat_y = no_poly_star 
      np_angle_to_center = find_angle((960,540), (np_new_cat_x, np_new_cat_y)) 
      istar_angle_to_center = find_angle((960, 540), (ix,iy)) 
      istar_dist_to_center = calc_dist((ix, iy), (960,540)) 
      ang_diff =  abs(np_angle_to_center - istar_angle_to_center)
      #if ang_diff < 30: 
   else:
      print("NO POLY CAT STAR KEY FOUND.")
   star_dist = 20 
   if closest[2] < star_dist and ang_diff < 5:
      #print("NP STAR ANGLE/ I STAR ANG TO CENTER:", ix, iy, np_new_cat_x, np_new_cat_y, np_angle_to_center, istar_angle_to_center, istar_dist_to_center , closest[2] )
      #print("CLOSEST:", closest)
      return(1, closest)
   else:
      #print("FAIL NP STAR ANGLE/ I STAR ANG TO CENTER:", ix, iy, np_new_cat_x, np_new_cat_y, np_angle_to_center, istar_angle_to_center, istar_dist_to_center , closest[2] )
     
      return(0, closest)

def get_stars_from_image(file,json_conf,masks = [], cal_params = None, show = 0, strict = 0):
   if cal_params is not None:
      if "cat_image_stars" in cal_params:
         orig_cat_image_stars = cal_params['cat_image_stars']
      else:
         orig_cat_image_stars = []
   else:
      orig_cat_image_stars = []
   user_stars = []
   if len(orig_cat_image_stars) > 0:
      print("ORIG:", orig_cat_image_stars[0])
      for name,mag,ra,dec,tmp1,tmp2,px_dist,new_cat_x,new_cat_y,tmp3,tmp4,new_cat_x,new_cat_y,ix,iy,px_dist in orig_cat_image_stars:
         user_stars.append((ix,iy,0))
   img_stars = user_stars 
   if show == 1:
      cv2.namedWindow('pepe')
   print("FILE:",file)
   file = file.replace("-stacked-stacked", "-stacked")
   img = cv2.imread(file,0)
   img = cv2.resize(img, (1920,1080))
   mimg = mask_frame(img, [], masks)
   print("MASKING IMAGE:", masks)
   img = mimg.copy()
   (f_datetime, cam_id, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(file)

   if cal_params is None:
      poss = get_active_cal_file(file)
      cal_params_file = poss[0][0]
      cal_params = load_json_file(cal_params_file)
   else:
      cal_params_file = None

   #if "user_stars" in cal_params:
   #   user_stars = cal_params['user_stars']
   #   img_stars = user_stars
   
   if "center_az" not in cal_params:
      print("NO CENTER AZ!")
      exit()
      poss = get_active_cal_file(file)
      cal_params_file = poss[0][0]
      temp = load_json_file(cal_params_file)
      cal_params['pixscale'] = temp['pixscale']
      cal_params['imagew'] = temp['imagew']
      cal_params['imageh'] = temp['imageh']
      cal_params['center_az'] = temp['center_az']
      cal_params['center_el'] = temp['center_el']
      cal_params['position_angle'] = temp['position_angle']
      cal_params['x_poly'] = temp['x_poly']
      cal_params['y_poly'] = temp['y_poly']
      cal_params['x_poly_fwd'] = temp['x_poly_fwd']
      cal_params['y_poly_fwd'] = temp['y_poly_fwd']
   

   cp_data = cal_params


   cat_stars = get_cat_stars(file,file,json_conf,cal_params)
   orig_x_poly = cal_params['x_poly']
   orig_y_poly = cal_params['y_poly']
   cal_params['x_poly'] = np.zeros(shape=(15,), dtype=np.float64)
   cal_params['y_poly'] = np.zeros(shape=(15,), dtype=np.float64)

   np_cat_stars = get_cat_stars(file,file,json_conf,cal_params)
   no_poly_cat_stars = {}
   for cat_star in np_cat_stars:
      (name,mag,ra,dec,new_cat_x,new_cat_y) = cat_star
      key = str(ra) + ":" + str(dec)
      no_poly_cat_stars[key] = cat_star 
    
   
   cal_params['x_poly'] = orig_x_poly
   cal_params['y_poly'] = orig_y_poly

   gsize = 25 

   wc = 0
   hc = 0
   if user_stars is None:
      img_stars = []
      new_img_stars = []
   else:
      new_img_stars = user_stars 
   for w in range(0,1920):
      for h in range(0,1080):
         if (w == 0 and h == 0) or (w % gsize == 0 and h % gsize == 0):
            x1 = w
            x2 = w + gsize
            y1 = h 
            y2 = h + gsize
            if x2 > 1920:
               x2 = 1920
            if y2 > 1080:
               y2 = 1080 
            crop_area = img[y1:y2,x1:x2]
            min_val, max_val, min_loc, (mx,my) = cv2.minMaxLoc(crop_area)
            mx1 = mx + w - 15
            mx2 = mx + w + 15
            my1 = my + h - 15
            my2 = my + h + 15
            if mx1 < 0:
               mx1 = 0 
            if mx2 > 1920:
               mx2 = 1920
            if my1 < 0:
               my1 = 0 
            if my2 > 1080:
               my2 = 1080 
            cnt_img = img[my1:my2,mx1:mx2]

            (max_px, avg_px,px_diff,(mx,my)) = find_star_in_crop(cnt_img)
            flux = test_star(cnt_img, (mx,my))
            ix = mx1 + mx
            iy = my1 + my
            if px_diff > 0:
               cv2.circle(img,(ix,iy), 5, (128,128,128), 1)
               new_img_stars.append((ix,iy,flux))
         hc = hc + 1
      wc = wc + 1
   if show == 1:
      cv2.imwrite("/mnt/ams2/tmp/test.png", img)
      cv2.imshow('pepe', img)
      cv2.waitKey(0)
   cv2.imwrite("/mnt/ams2/tmp/test.png", img)

   total_res = 0
   tstars = 0
   img_stars = remove_dupe_img_stars(new_img_stars)
   cat_img_stars = []
   no_match_stars = []
   star_dist = 20
   img_stars = new_img_stars
   tstars = 0
   if strict == 1:
      star_dist = 5
   for star in img_stars:
      ix, iy,flux = star
      cv2.circle(img,(ix,iy), 5, (128,128,128), 1)
 
      status, star_info = lookup_star_in_cat(ix,iy,cat_stars,no_poly_cat_stars, star_dist)
      if status == 1:
         (ix,iy,px_dist,iname,mag,ra,dec,new_cat_x,new_cat_y) = star_info
         #(name,mag,ra,dec,new_cat_x,new_cat_y) = cat_star
         iname = iname.decode("utf-8")
         new_cat_x,new_cat_y = int(new_cat_x), int(new_cat_y)
         total_res = total_res + px_dist
         tstars = tstars + 1 
         cat_img_stars.append((iname,mag,ra,dec,new_cat_x,new_cat_y,ix,iy,px_dist,cal_params_file))
      else:
         no_match_stars.append(star)
         (ix,iy,px_dist,iname,mag,ra,dec,new_cat_x,new_cat_y) = star_info
         new_cat_x,new_cat_y = int(new_cat_x), int(new_cat_y)


   #cv2.imshow('pepe', img)
   #cv2.waitKey(0)
   # compute std dev distance
   tot_res = 0
   close_stars = []
   dist_list = []
   for name,mag,ra,dec,new_cat_x,new_cat_y,six,siy,px_dist,cp_file in cat_img_stars:
      px_dist = calc_dist((ix,iy),(new_cat_x,new_cat_y))
      dist_list.append(px_dist)
   std_dev_dist = np.std(dist_list)
   std_dev_dist = std_dev_dist * 3
   desc = "STD DEV DIST:" + str(std_dev_dist)
   tot_res = 0
   close_stars = []
   if std_dev_dist < 5:
      std_dev_dist = 5 

  
   for name,mag,ra,dec,new_cat_x,new_cat_y,six,siy,px_dist,cp_file in cat_img_stars:
      px_dist = calc_dist((six,siy),(new_cat_x,new_cat_y))
      #if px_dist <= std_dev_dist:
      if True:
         new_cat_x,new_cat_y = int(new_cat_x), int(new_cat_y)
         if show == 1:
            cv2.circle(img,(six,siy), 5, (128,128,128), 1)
            iname = name 
            cv2.putText(img, iname,  (ix,iy), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
            cv2.rectangle(img, (new_cat_x-5, new_cat_y-5), (new_cat_x+5, new_cat_y+5), (128, 128, 128), 1)
         close_stars.append((name,mag,ra,dec,new_cat_x,new_cat_y,six,siy,px_dist,cp_file))
         tot_res = tot_res + px_dist
      else:
         no_match_stars.append((name,mag,ra,dec,new_cat_x,new_cat_y,six,siy,px_dist,cp_file))
         cv2.circle(img,(ix,iy), 10, (128,128,128), 1)
         cv2.rectangle(img, (new_cat_x-10, new_cat_y-10), (new_cat_x+10, new_cat_y+10), (128, 128, 128), 1)
   
   tstars = len(close_stars)
   if tstars > 0:
      avg_res = tot_res / tstars
   else:
      avg_res = 9999

   nmt = len(no_match_stars)
   mt = len(close_stars)
   tt = nmt + mt
   if tt > 0:
      match_per = mt / tt
   else:
      match_per = 0
   if show == 1:
      desc = "Match %: " + str(match_per)[0:4]
      cv2.putText(img, desc,  (10,90), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)

      desc = "Stars:" + str(tstars)[0:4]
      cv2.putText(img, desc,  (10,120), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)

      desc = "Res Err:" + str(avg_res)[0:4]
      cv2.putText(img, desc,  (10,150), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
   

   if show == 1:    
      show_img = cv2.resize(img, (0,0),fx=.5, fy=.5)
      cv2.imshow('pepe', show_img)
      cv2.waitKey(1) 
   #cp_data['cat_img_stars'] = close_stars 
   close_stars = remove_dupe_cat_stars(close_stars)

   cal_params['cat_image_stars'] = close_stars 
   return(close_stars, img, no_match_stars, avg_res,match_per, cal_params)
   
def remove_dupe_img_stars(img_stars):
   index = {}
   new_list = []
   #print(img_stars)
   for x,y,flux in img_stars:
      key = str(x) + ":" + str(y)
      if key not in index:
         new_list.append((x,y,flux))
         index[key] = 1
      #else:
         #print("DUPE:",x,y)
   return(new_list)

def get_image_stars_from_catalog(file,json_conf,cal_params_file, masks = [], cal_params = None, show = 0):
   img = cv2.imread(file,0)
   img = cv2.resize(img, (1920,1080))
   img = mask_frame(img, [], masks)
   if cal_params is None: 
      cal_params = load_json_file(cal_params_file)
   if "lat" in cal_params:
      lat = cal_params['lat']
      lon = cal_params['lon']
      alt = cal_params['alt']
   else:
      lat = json_conf['site']['device_lat']
      lon = json_conf['site']['device_lng']
      alt = json_conf['site']['device_alt']

   ra_center = cal_params['ra_center']
   dec_center = cal_params['dec_center']
   center_az = cal_params['center_az']
   center_el = cal_params['center_el']
   #print("AZ CONVERT! ", file )
   rah,dech = AzEltoRADec(center_az,center_el,file,cal_params,json_conf)
   rah = str(rah).replace(":", " ")
   dech = str(dech).replace(":", " ")
   
   #rahh = RAdeg2HMS(rah)
   ra_center,dec_center = HMS2deg(str(rah),str(dech))


   #print("GET IMAGE STARS FROM CATALOG: ", center_az, center_el, ra_center, dec_center, file,cal_params_file)
   cal_params['ra_center'] = ra_center
   cal_params['dec_center'] = dec_center

   fov_poly = 0 
   pos_poly = 0 
   x_poly = cal_params['x_poly']
   y_poly = cal_params['y_poly']
   #print("GET CAT STARS:", ra_center, dec_center)
   cat_stars = get_catalog_stars(fov_poly, pos_poly, cal_params,"x",x_poly,y_poly,min=0)
   #cat_stars = cat_stars[0:50]

   cat_image_stars = []
   for cat_star in cat_stars:
      (name,mag,ra,dec,new_cat_x,new_cat_y) = cat_star
      name = name.decode("utf-8")
      new_cat_x = int(new_cat_x)
      new_cat_y = int(new_cat_y)
      ix,iy = find_img_point_from_cat_star(new_cat_x,new_cat_y,img)
      if ix != 0 and iy != 0: 
         px_dist = calc_dist((ix,iy),(new_cat_x,new_cat_y))
         if px_dist < 10:
            cat_image_stars.append((name,mag,ra,dec,new_cat_x,new_cat_y,ix,iy,px_dist,cal_params_file))


   # compute std dev distance
   tot_res = 0
   close_stars = []
   dist_list = []
   for name,mag,ra,dec,new_cat_x,new_cat_y,ix,iy,px_dist,cp_file in cat_image_stars:
      px_dist = calc_dist((ix,iy),(new_cat_x,new_cat_y))
      dist_list.append(px_dist)
   std_dev_dist = np.std(dist_list)
   desc = "STD DEV DIST:" + str(std_dev_dist)
   tot_res = 0
   close_stars = []
   
   cv2.putText(img, desc ,  (300,300), cv2.FONT_HERSHEY_SIMPLEX, .5, (255, 255, 255), 1)

   tot_res = 0
   for pstar in cat_image_stars:
      (name,mag,ra,dec,new_cat_x,new_cat_y,ix,iy,px_dist,cp_file) = pstar
      if px_dist <= std_dev_dist:
         cv2.rectangle(img, (new_cat_x-2, new_cat_y-2), (new_cat_x + 2, new_cat_y + 2), (128, 128, 128), 1)
         cv2.line(img, (ix,iy), (new_cat_x,new_cat_y), (255), 2)
         cv2.circle(img,(ix,iy), 5, (128,128,128), 1)
         tot_res = tot_res + px_dist
         close_stars.append(pstar)

   if len(close_stars) > 0:
      avg_res = tot_res / len(close_stars)
   else:
      avg_res = 9999
   desc = "AVG RES:" + str(avg_res)
   cv2.putText(img, desc ,  (400,400), cv2.FONT_HERSHEY_SIMPLEX, .5, (255, 255, 255), 1)
   #cv2.rectangle(img, (new_cat_x-2, new_cat_y-2), (new_cat_x + 2, new_cat_y + 2), (128, 128, 128), 1)

   return(close_stars,img)
   
def find_img_point_from_cat_star(cx,cy,img):
   ih, iw = img.shape
   sz = 20 
   x1 = cx - sz 
   x2 = cx + sz
   y1 = cy - sz
   y2 = cy + sz
   if x1 < 0 or y1 < 0:
      return(0,0)
   if x2 >= (iw -5) or y2 > (ih -5):
      return(0,0)
   cnt_img = img[y1:y2,x1:x2]
   max_px, avg_px, px_diff,max_loc = eval_cnt(cnt_img.copy())
   if px_diff < 20:
      return(0,0)
   #cv2.imshow('pepe',cnt_img)
   #cv2.waitKey(1)
   mx,my = max_loc
   nx = cx + mx - sz + 5
   ny = cy + my - sz + 5
   return(nx,ny) 

def get_image_stars(file,show=0):
   stars = []
   img = cv2.imread(file, 0)
   avg = np.mean(img) 
   best_thresh = avg + 12
   _, star_bg = cv2.threshold(img, best_thresh, 255, cv2.THRESH_BINARY)
   thresh_obj = cv2.dilate(star_bg, None , iterations=4)
   (_, cnts, xx) = cv2.findContours(thresh_obj.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
   cc = 0
   for (i,c) in enumerate(cnts):
      x,y,w,h = cv2.boundingRect(cnts[i])
      px_val = int(img[y,x])
      cnt_img = img[y:y+h,x:x+w]
      cnt_img = cv2.GaussianBlur(cnt_img, (7, 7), 0)
      max_px, avg_px, px_diff,max_loc = eval_cnt(cnt_img.copy())
      name = "/mnt/ams2/tmp/cnt" + str(cc) + ".png"
      #star_test = test_star(cnt_img)
      x = x + int(w/2)
      y = y + int(h/2)
      if px_diff > 5 and w > 1 and h > 1 and w < 50 and h < 50:
          stars.append((x,y,int(max_px)))
          cv2.circle(img,(x,y), 5, (128,128,128), 1)

      cc = cc + 1
   if show == 1:
      cv2.imshow('pepe', img)
      cv2.waitKey(1)

   temp = sorted(stars, key=lambda x: x[2], reverse=True)
   stars = temp[0:50]
   return(stars)

def test_star_old(cnt_img):
   ch,cw = cnt_img.shape
   avg = np.mean(cnt_img)
   min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(cnt_img)
   mx,my = max_loc
  
   #if abs(dx) > 2 or abs(dy) > 2:
      #print(x,y,cw,ch,"Failed bright center test ")
   #   return(0)

   px_diff = max_val - avg 
   if px_diff > 10:
      return(1)
   else: 
      return(0)

def sum_weather(all_i_files,json_conf):

   weather = {}
   weather_sum = {}
   for file in all_i_files:
      (f_datetime, cam_id, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(file)
      weather[fh] = []
      weather_sum[fh] = []
   for file in all_i_files:
      (f_datetime, cam_id, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(file)
      num_f = len(all_i_files[file])
      weather[fh].append(num_f)

   for fh in weather:
      if len(weather[fh]) > 5:
         avg_stars = np.sum(weather[fh]) / len(weather[fh])
      else:
         avg_stars = 0
      weather_sum[fh] = avg_stars
   return(weather_sum)

def default_cal_params(cal_params,json_conf):
   if 'fov_poly' not in cal_params:
      fov_poly = [0,0]
      cal_params['fov_poly'] = fov_poly
   if 'pos_poly' not in cal_params:
      pos_poly = [0]
      cal_params['pos_poly'] = pos_poly
   if 'x_poly' not in cal_params:
      x_poly = np.zeros(shape=(15,), dtype=np.float64)
      cal_params['x_poly'] = x_poly.tolist()
   if 'y_poly' not in cal_params:
      y_poly = np.zeros(shape=(15,), dtype=np.float64)
      cal_params['y_poly'] = x_poly.tolist()
   if 'x_poly_fwd' not in cal_params:
      x_poly = np.zeros(shape=(15,), dtype=np.float64)
      cal_params['x_poly_fwd'] = x_poly.tolist()
   if 'y_poly_fwd' not in cal_params:
      y_poly = np.zeros(shape=(15,), dtype=np.float64)
      cal_params['y_poly_fwd'] = x_poly.tolist()

   return(cal_params)

def star_res(meteor_json_file, json_conf, show):
   hdm_x = 2.7272
   hdm_y = 1.875
   (f_datetime, cam_id, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(meteor_json_file)

   if show == 1:
      cv2.namedWindow('pepe')
   if "-reduced" not in meteor_json_file :
      meteor_json_red_file = meteor_json_file.replace(".json", "-reduced.json")
   if cfe(meteor_json_file) == 0:
      print("Can't open :", meteor_json_file)
      exit()
   meteor_json = load_json_file(meteor_json_file) 
   if cfe(meteor_json_red_file) == 0:
      print("Can't open reduction file:", meteor_json_red_file)
      exit()

   print("loading:", meteor_json_red_file)
   meteor_json_red = load_json_file(meteor_json_red_file) 

   sd_stack_file = meteor_json_file.replace(".json", "-stacked.png")
   hd_video_file = meteor_json_red['hd_video_file']
   hd_stack_file = hd_video_file.replace(".mp4", "-stacked.png")
   if cfe(hd_stack_file) == 0:
      hd_stack_file = meteor_json_file.replace(".json", "-stacked.png")
   hd_star_img = cv2.imread(hd_stack_file, 0)
   masks = get_masks(cam_id, json_conf,1)
   mask_points = []
   for obj in meteor_json['sd_objects']:
      for data in obj['history']:
         ms_x= (data[1] +5 ) * hdm_x
         ms_y= (data[2] +5 ) * hdm_y
         mask_points.append((ms_x,ms_y))

   hd_star_img = mask_frame(hd_star_img, mask_points, masks)
   poss = get_active_cal_file(hd_video_file)
   cal_params_file = poss[0][0]
   cal_params = load_json_file(cal_params_file)
   if False:
      master_params_file = "master_cal_file_" + cam_id + ".json"
      master_params = load_json_file(master_params_file)
      cal_params['x_poly'] = master_params['x_poly']
      cal_params['y_poly'] = master_params['y_poly']
      cal_params['x_poly_fwd'] = master_params['x_poly_fwd']
      cal_params['y_poly_fwd'] = master_params['y_poly_fwd']
      save_json_file(cal_params_file, cal_params)
   #print("Closest Cal Params File:", cal_params_file)
   #cat_image_stars, img = get_image_stars_from_catalog(hd_stack_file,json_conf,cal_params_file, masks , show = 0)
   if cfe(hd_stack_file) == 0:
      hd_stack_file = sd_stack_file
   cat_image_stars, img, no_match, res_err, match_per = get_stars_from_image(hd_stack_file,json_conf, masks , cal_params, show = 0)
   total_res = 0
   #for x in cat_image_stars:
   #   print(x)

   found_stars = len(cat_image_stars)
   for pstar in cat_image_stars:
      (name,mag,ra,dec,new_cat_x,new_cat_y,ix,iy,px_dist,cp_file) = pstar
      total_res = total_res + px_dist
   if found_stars > 0:
      avg_res = total_res / found_stars
   else:
      avg_res = 9999

   meteor_json_red['residual_star_error'] = avg_res
   #save_json_file(meteor_json_red_file, meteor_json_red)

   #print("AVG RES FOR THIS METEOR REDUCTION IS: ", avg_res)
   

   if show == 1:
      show_img = cv2.resize(img, (0,0),fx=.5, fy=.5)
      cv2.imshow('pepe', show_img)
      cv2.waitKey(1)
   return(avg_res, found_stars,img)

def fix_js(json_file):
   new_json = fix_json_file(json_file)
   if new_json is not None:
      print("FIXED", json_file)
   else:
      print("JSON GOOD", json_file)


def batch_fix (json_conf):

   if 'procs' in json_conf['site']:
      max_procs = json_conf['site']['procs']
   else: 
      max_procs = 4

   meteor_dirs = glob.glob("/mnt/ams2/meteors/*")
   bad_files = [] 
   refit = 0

   jobs = []

   for meteor_dir in sorted(meteor_dirs,reverse=True):
      meteor_files = glob.glob(meteor_dir + "/*-reduced.json")
      for meteor_file in meteor_files:
         mf = meteor_file.replace("-reduced.json", ".json")
         fn = mf.split("/")[-1]
#         fix_js(mf)

         #cmd =  "./detectMeteors.py br " + mf + " 0"
         #jobs.append(cmd) 

         #cmd = "./autoCal.py imgstars " + mf + " 0"
         #jobs.append(cmd) 

         cmd =  "./autoCal.py cfit " + mf + " 0"
         jobs.append(cmd) 


         mfr = mf.replace(".json", "-reduced.json")
         #cmd = "./reducer.py " + mfr 
         #jobs.append(cmd) 

   running = check_running("autoCal.py")
   print("Jobs Running: ", running)

   jc = 0
   
   for job in jobs:
      while (check_running("autoCal.py")) > max_procs:       
         time.sleep(1)
      print(job)
      os.system(job + " &")
      #if jc > 10:
      #   print("Quit early.")
      #   exit()
      jc = jc + 1

def night_sum(date,json_conf, show=0):
   
   blank = np.zeros((1080,1920),dtype=np.uint8)
   if show == 1:
      cv2.namedWindow('pepe')
   night_sum_rpt = {}
   night_dir = "/mnt/ams2/cal/hd_images/" + date + "/*calparams.json"
   day_dir = "/mnt/ams2/cal/hd_images/" + date + "/"
   cal_files = glob.glob(night_dir) 
   merge_stars = {}
   for meteor_file in cal_files:
      (f_datetime, cam_id, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(meteor_file)
      if cam_id not in night_sum_rpt:
         night_sum_rpt[cam_id] = {}
      md = load_json_file(meteor_file)
      night_sum_rpt[cam_id][meteor_file] = {}
      night_sum_rpt[cam_id][meteor_file]['astro_res_err'] = md['astro_res_err'] 
      night_sum_rpt[cam_id][meteor_file]['total_stars'] = len(md['cat_image_stars']) 
      night_sum_rpt[cam_id][meteor_file]['center_az'] = str(md['center_az']) 
      night_sum_rpt[cam_id][meteor_file]['center_el'] = str(md['center_el']) 
      night_sum_rpt[cam_id][meteor_file]['position_angle'] = str(md['position_angle']) 
      night_sum_rpt[cam_id][meteor_file]['pixscale'] = str(md['pixscale']) 
      night_sum_rpt[cam_id][meteor_file]['cat_image_stars'] = md['cat_image_stars']

   master_imgs = {}
   last_imgs = {}
   best_cal = {}

   for cam_id in sorted(night_sum_rpt):
      print("cam_id","avg_res","total_stars")
      for mf in sorted(night_sum_rpt[cam_id]):
         img_file = mf.replace("-calparams.json", "-stacked.png")
         img = cv2.imread(img_file, 0)
         if cam_id not in master_imgs:
            master_imgs[cam_id] = blank.copy()
            last_imgs[cam_id] = img.copy()
         for star in night_sum_rpt[cam_id][mf]['cat_image_stars']: 
            #print(star)
            iname,mag,ra,dec,tmp1,tmp2,px_dist,new_cat_x,new_cat_y,tmp3,tmp4,new_cat_x,new_cat_y,ix,iy,px_dist = star

            cv2.circle(img,(ix,iy), 5, (128,128,128), 1)
            cv2.rectangle(img, (new_cat_x-2, new_cat_y-2), (new_cat_x + 2, new_cat_y + 2), (128, 128, 128), 1)
            cv2.putText(img, iname,  (ix,iy), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 1)

            cv2.circle(master_imgs[cam_id],(ix,iy), 5, (128,128,128), 1)
            cv2.rectangle(master_imgs[cam_id], (new_cat_x-2, new_cat_y-2), (new_cat_x + 2, new_cat_y + 2), (128, 128, 128), 1)
            #cv2.putText(master_imgs[cam_id], iname,  (ix,iy), cv2.FONT_HERSHEY_SIMPLEX, .3, (255, 255, 255), 1)
            blend_image = cv2.addWeighted(img, .7, master_imgs[cam_id], .3,0)
         if show == 1:
            cv2.imshow('pepe', blend_image)
            cv2.waitKey(120)
         print (cam_id, night_sum_rpt[cam_id][mf]['astro_res_err'],night_sum_rpt[cam_id][mf]['total_stars'],night_sum_rpt[cam_id][mf]['center_az'],night_sum_rpt[cam_id][mf]['center_el'])

   for cam_id in sorted(master_imgs):
      img = master_imgs[cam_id] 
      last = last_imgs[cam_id] 
      blend_image = cv2.addWeighted(last, .5, master_imgs[cam_id], .5,0)
      if show == 1:
         cv2.imshow('pepe', blend_image)
         cv2.waitKey(0)

   best_cal_res = {}
   best_cal_stars = {}
   best_cal_file = {}
   # find best file for each cam for the night 
   # and copy it to the freecal dir so it can be used
   for cam_id in sorted(master_imgs):
      if cam_id not in best_cal_res:
         best_cal_res[cam_id] = 9999
         best_cal_stars[cam_id] = 0
         best_cal_file[cam_id] = 0
      for mf in night_sum_rpt[cam_id]:
         astro_res_err = night_sum_rpt[cam_id][mf]['astro_res_err']
         total_stars = night_sum_rpt[cam_id][mf]['total_stars']
         if astro_res_err < best_cal_res[cam_id] and total_stars > best_cal_stars[cam_id]:
            best_cal_res[cam_id] = astro_res_err
            best_cal_stars[cam_id] = total_stars
            best_cal_file[cam_id] = mf 
         print(mf, astro_res_err)
   print("BEST CAL FILES FOR NIGHT!")
   for cam_id in best_cal_file:
      mf = best_cal_file[cam_id]
      cal_image = mf.replace("-calparams.json", "-stacked.png")
      fn = mf.split("/")[-1]
      base_name = fn[0:30]
      free_cal_dir = "/mnt/ams2/cal/freecal/" + base_name + "/"
      new_cal_file = free_cal_dir + base_name + "-calparams.json" 
      new_cal_image = free_cal_dir + base_name + "-stacked.png" 
      if cfe(free_cal_dir, 1) == 0:
          cmd = "mkdir " + free_cal_dir
          print(cmd)
          os.system(cmd)
      cmd = "cp " + mf + " " + new_cal_file
      print(cmd)
      os.system(cmd)

      cmd = "cp " + cal_image + " " + new_cal_image
      print(cmd)
      os.system(cmd)
      cmd = "./XYtoRAdecAzEl.py az_grid " + new_cal_file
      print(cmd)

      os.system(cmd)
      print(cam_id, base_name, night_sum_rpt[cam_id][mf]['astro_res_err'], night_sum_rpt[cam_id][mf]['total_stars'])
      

def night_cal(date,json_conf, show=0):
   night_dir = "/mnt/ams2/cal/hd_images/" + date + "/*calparams.json"
   day_dir = "/mnt/ams2/cal/hd_images/" + date + "/"
   cal_files = glob.glob(night_dir) 
   merge_stars = {}
   cam_centers = {}
#   for meteor_file in cal_files:
#      print(meteor_file)
#      md = load_json_file(meteor_file)
#      (f_datetime, cam_id, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(meteor_file)
#      if cam_id not in merge_stars:
#         merge_stars[cam_id] = {}
#      merge_stars[cam_id][meteor_file] = [] 
#      if 'cat_image_stars' in md:
#         cat_image_stars = md['cat_image_stars']
      #else:
#         print("NO CAT IMAGE STARS IN FILE", meteor_file)
#         cat_image_stars = []
   
#      for star in cat_image_stars:
#         if len(star) == 16:
#            name,mag,ra,dec,img_ra,img_dec,match_dist,new_cat_x,new_cat_y,img_az,img_el,new_cat_x,new_cat_y,ix,iy, img_res = star
#            #merge_stars[cam_id][meteor_file].append((meteor_file,md['ra_center'],md['dec_center'],md['position_angle'],md['pixscale'],name,mag,ra,dec,img_ra,img_dec,match_dist,new_cat_x,new_cat_y,img_az,img_el,new_cat_x,new_cat_y,ix,iy, img_res, 0, 0))
#         else:
#            print("BAD STAR:", meteor_file, len(star))

   cc = 0

#   night_dir = "/mnt/ams2/meteors/" + date + "/*reduced.json"
#   day_dir = "/mnt/ams2/meteors/" + date + "/"
   cal_files = glob.glob(night_dir)
   #merge_stars = {}
   #cam_centers = {}
   for cal_file in cal_files:
      np_cal_params = None
      print(cal_file)
      md = load_json_file(cal_file)
      (f_datetime, cam_id, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(cal_file)
      if cam_id not in merge_stars:
         merge_stars[cam_id] = {}
      merge_stars[cam_id][cal_file] = []
      if 'x_poly' in md:
         np_cal_params = md
         np_cal_params['x_poly'] = np.zeros(shape=(15,), dtype=np.float64)
         np_cal_params['y_poly'] = np.zeros(shape=(15,), dtype=np.float64)

         if 'cat_image_stars' in md:
            cat_image_stars = md['cat_image_stars']
      else:
         print("NO CAT IMAGE STARS IN FILE", cal_file)
         cat_image_stars = []

      print("CALP: ", cal_file, np_cal_params['center_az'], np_cal_params['center_el'])
      np_cat_stars = get_cat_stars(cal_file,cal_file,json_conf,np_cal_params)
#   np_angle_to_center = find_angle((960,540), (np_new_cat_x, np_new_cat_y))
      no_poly_cat_stars = {}
      for cat_star in np_cat_stars:
         (np_name,np_mag,np_ra,np_dec,np_new_cat_x,np_new_cat_y) = cat_star
         key = str(np_ra) + ":" + str(np_dec)
         no_poly_cat_stars[key] = cat_star

      avgpxscale = 162

      for star in cat_image_stars:
         bad = 0
         if len(star) == 16:
            name,mag,ra,dec,img_ra,img_dec,match_dist,new_cat_x,new_cat_y,img_az,img_el,new_cat_x,new_cat_y,ix,iy, img_res = star
            key = str(ra) + ":" + str(dec)
         else:
            bad = 1
            print("BAD STAR:", star)
           
         if key in no_poly_cat_stars:
            np_name,np_mag,np_ra,np_dec,np_new_cat_x,np_new_cat_y = no_poly_cat_stars[key]
            np_angle_to_center = find_angle((960,540), (np_new_cat_x, np_new_cat_y))
            img_angle_to_center = find_angle((960,540), (ix, iy))
            ang_diff = abs(img_angle_to_center - np_angle_to_center)
            #if md['pixscale'] < 157:  
            #   bad = 0
            #   print("BAD PIX SCALE:", cam_id, md['pixscale'])
            #if md['pixscale'] >  162:  
            #   bad = 0
            #   print("BAD PIX SCALE:", cam_id, md['pixscale'])
            if ang_diff > 1:
               print("BAD ANG:", cam_id, ix, iy, np_name, name, new_cat_x, new_cat_y, np_new_cat_x, np_new_cat_y, " -- ", img_angle_to_center, np_angle_to_center, ang_diff)
               bad = 1
            else:
               print("GOOD ANG:", cam_id, ix, iy, np_name, name, new_cat_x, new_cat_y, np_new_cat_x, np_new_cat_y, " -- ", img_angle_to_center, np_angle_to_center, ang_diff)
         if bad == 0:
            merge_stars[cam_id][cal_file].append((cal_file,md['ra_center'],md['dec_center'],md['position_angle'],md['pixscale'],name,mag,ra,dec,img_ra,img_dec,match_dist,new_cat_x,new_cat_y,img_az,img_el,new_cat_x,new_cat_y,ix,iy, img_res,np_new_cat_x, np_new_cat_y))

   cc = 0
 
   for day in merge_stars:
      for file in merge_stars[day]:
         print(file, merge_stars[day][file])

   multi_merge(merge_stars,json_conf,day_dir, show )

def meteor_cal_all(json_conf, show=0):
   procs = 24 
   meteor_dir = "/mnt/ams2/meteors/" 
   meteor_dirs = glob.glob(meteor_dir + "*") 
   jobs = []
   for dir in sorted(meteor_dirs):
      date = dir.split("/")[-1]
      print(dir,date)
      if cfe(dir,1) == 1:
         cmd = "./autoCal.py meteor_cal " + date
         print( cmd)
         jobs.append(cmd)
         #os.system(cmd)
  
   jc = 0
   for job in jobs:
      while (check_running("autoCal.py")) > procs:       
         #print("Waiting to run some jobs...")
         time.sleep(1)
      print("JOB:", job)
      os.system(job + " &")
      jc = jc + 1
      
   

def meteor_cal(date,json_conf, show=0):

   meteor_dir = "/mnt/ams2/meteors/" + date + "/*reduced.json"
   day_dir = "/mnt/ams2/meteors/" + date + "/"


   meteor_files = glob.glob(meteor_dir) 
   merge_stars = {}
   for meteor_file in meteor_files:
      print(meteor_file)
      md = load_json_file(meteor_file)
      np_cal_params = None
      no_poly_cat_stars = {}

      if 'cal_params' in md:
         if md['cal_params'] == None:
            print("NO cal. lets try to add it.")
            poss = get_active_cal_file(meteor_file)
            print(poss)
            cal_params_file = poss[0][0]
            cal_params = load_json_file(cal_params_file)
            md['cal_params'] = cal_params
            #except:
            #   print("Couldn't find a cal file for this camera. Skip for now.")
            #   continue

      if 'cal_params' in md:
         np_cal_params = md['cal_params']
         if md['cal_params'] != None:
            total_res_px = md['cal_params']['total_res_px']
         else:
            total_res_px = 999
         if total_res_px > 2 or len(md['cal_params']['cat_image_stars']) < 15:
            print("Skip this file!", total_res_px)
            continue
         np_cal_params['x_poly'] = np.zeros(shape=(15,), dtype=np.float64)
         np_cal_params['y_poly'] = np.zeros(shape=(15,), dtype=np.float64)
         #center_az = np_cal_params['center_az']
         #center_el = np_cal_params['center_el']
         #rah,dech = AzEltoRADec(center_az,center_el,meteor_file,np_cal_params,json_conf)
         #rah = str(rah).replace(":", " ")
         #dech = str(dech).replace(":", " ")
         #ra_center,dec_center = HMS2deg(str(rah),str(dech))
         #np_cal_params['ra_center'] = ra_center
         #np_cal_params['dec_center'] = dec_center


         np_cat_stars = get_cat_stars(meteor_file,meteor_file,json_conf,np_cal_params)
         no_poly_cat_stars = {}
         for cat_star in np_cat_stars:
            (np_name,np_mag,np_ra,np_dec,np_new_cat_x,np_new_cat_y) = cat_star
            key = str(np_ra) + ":" + str(np_dec)
            no_poly_cat_stars[key] = cat_star
      (f_datetime, cam_id, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(meteor_file)
      if cam_id not in merge_stars:
         merge_stars[cam_id] = {}
      merge_stars[cam_id][meteor_file] = [] 
      if 'cal_params' in md: 
         if 'cat_image_stars' in md['cal_params']:
            cat_image_stars = md['cal_params']['cat_image_stars']
      else:
         print("NO CAT IMAGE STARS IN FILE", meteor_file)
         cat_image_stars = []
  
      timg_res = 0 
      for star in cat_image_stars:
         name,mag,ra,dec,img_ra,img_dec,match_dist,new_cat_x,new_cat_y,img_az,img_el,new_cat_x,new_cat_y,ix,iy, img_res = star
         timg_res = timg_res + img_res
      if len(cat_image_stars) > 0:
         file_res = timg_res / len(cat_image_stars)
      print("FILE RES:", file_res)
      for star in cat_image_stars:
         name,mag,ra,dec,img_ra,img_dec,match_dist,new_cat_x,new_cat_y,img_az,img_el,new_cat_x,new_cat_y,ix,iy, img_res = star
         bad = 0
         key = str(ra) + ":" + str(dec)
       
         if key in no_poly_cat_stars:
            np_name,np_mag,np_ra,np_dec,np_new_cat_x,np_new_cat_y = no_poly_cat_stars[key]
            np_angle_to_center = find_angle((960,540), (np_new_cat_x, np_new_cat_y))
            img_angle_to_center = find_angle((960,540), (ix, iy))
            ang_diff = abs(img_angle_to_center - np_angle_to_center)
            #print(name, np_name, ix, iy, new_cat_x, new_cat_y, np_new_cat_x, np_new_cat_y)
            if ang_diff > 2:
               print("BAD ANG:", img_angle_to_center, np_angle_to_center, ang_diff)
               bad = 1
            else:
               print("GOOD ANG:", img_angle_to_center, np_angle_to_center, ang_diff)
         if bad == 0:
            merge_stars[cam_id][meteor_file].append((meteor_file,md['cal_params']['ra_center'],md['cal_params']['dec_center'],md['cal_params']['position_angle'],md['cal_params']['pixscale'],name,mag,ra,dec,img_ra,img_dec,match_dist,new_cat_x,new_cat_y,img_az,img_el,new_cat_x,new_cat_y,ix,iy, img_res, np_new_cat_x, np_new_cat_y))
 

         #merge_stars[cam_id][meteor_file].append((meteor_file,md['cal_params']['ra_center'],md['cal_params']['dec_center'],md['cal_params']['position_angle'],name,mag,ra,dec,img_ra,img_dec,match_dist,new_cat_x,new_cat_y,img_az,img_el,new_cat_x,new_cat_y,ix,iy, img_res))

   cc = 0

   multi_merge(merge_stars,json_conf,day_dir,show)


def meteor_cal_old(date,json_conf):
   print("Meteor cal:", date)
   merge_stars = {}
   cal_files = glob.glob("/mnt/ams2/cal/freecal/" + date + "*")
   print(cal_files)
   for cal_dir in cal_files:
      fn = cal_dir.split("/")[-1]
      cal_file = cal_dir + "/" + fn + "-calparams.json"
      if cfe(cal_file) == 0:
         cal_file = cal_dir + "/" + fn + "-stacked-calparams.json"
      print(cal_file)
      (f_datetime, cam_id, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(cal_file)
      if cam_id not in merge_stars:
         merge_stars[cam_id] = {}

      cp = load_json_file(cal_file)
      merge_stars[cam_id][cal_file] = [] 
      for name,mag,ra,dec,img_ra,img_dec,match_dist,new_cat_x,new_cat_y,img_az,img_el,new_cat_x,new_cat_y,ix,iy, img_res in cp['close_stars']:
         merge_stars[cam_id][cal_file].append((cal_file,cp['ra_center'],cp['dec_center'],cp['position_angle'],name,mag,ra,dec,img_ra,img_dec,match_dist,new_cat_x,new_cat_y,img_az,img_el,new_cat_x,new_cat_y,ix,iy, img_res))
            #merge_stars[cam_id][cal_file] = cp['close_stars']


   save_json_file("merge.txt", merge_stars)
   multi_merge(merge_stars,json_conf)
         
def get_hd_files_for_day_cam(day,cam_id ):
   glob_str = "/mnt/ams2/HD/" + day + "*" + cam_id + "*.mp4"
   print(glob_str)
   hd_files = glob.glob(glob_str)
   return(sorted(hd_files))

def make_hd_images(day, json_conf, mod=15):

   hd_cal_files = {}
   day_dir = "/mnt/ams2/cal/hd_images/" + day + "/"
   if cfe(day_dir, 1) == 0:
      os.system("mkdir " + day_dir )

   cameras = json_conf['cameras']
   for id in  cameras:
      cam_id = json_conf['cameras'][id]['cams_id'] 
      hd_cal_files[cam_id] = []
      print("CAM ID:", id, cam_id)
      hd_files = get_hd_files_for_day_cam(day,cam_id)
      fc = 0
      for hd_file in hd_files:
         (f_datetime, cam_id, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(hd_file)
         sun_status,sun_az,sun_el = get_sun_info(f_date_str, json_conf)
         if "trim" not in hd_file and sun_status == 'night':
            if fc % mod == 0:
               hd_cal_files[cam_id].append(hd_file) 
            fc = fc + 1

   for cam_id in hd_cal_files:
      for hd_file in hd_cal_files[cam_id]:
         new_file = hd_file.split("/")[-1]
         new_file = new_file.replace(".mp4", "-stacked.png")
         new_file = day_dir + new_file
         if cfe(new_file) == 0:
            frames = load_video_frames(hd_file, json_conf, 150,0,[],1)
            print(hd_file, len(frames))
            stack_file, stack_img = stack_frames(frames, hd_file, 0)
            print(stack_file)
            os.system("mv " + stack_file + " " + new_file)
            print(new_file)
         else:
            print("skip already done.")

def batch_hd_fit(day,json_conf,scmd):
   print("YES", day, scmd)
   if 'procs' in json_conf['site']:
      procs = json_conf['site']['procs']
   else: 
      procs = 4
   day_dir = "/mnt/ams2/cal/hd_images/" + day + "/"
   files = glob.glob(day_dir + "*calparams.json")
   jobs1 = []
   jobs2 = []
   jobs3 = []
   for file in files:
      if scmd == 'cfit':
         cmd = "./autoCal.py cfit_hdcal " + file + " 0"
         jobs1.append(cmd)
      if scmd == 'imgstars':
         cmd = "./autoCal.py imgstars " + file + " 0"
      
         jobs1.append(cmd)

   jc = 0
   for job in jobs1:
      while (check_running("autoCal.py")) > procs:       
         #print("Waiting to run some jobs...")
         time.sleep(1)
      print("JOB:", job)
      os.system(job + " &")
      jc = jc + 1
   jc = 0
   

def scan_hd_images(day,json_conf, show = 0):
   if show == 1:
      cv2.namedWindow('pepe')
   day_dir = "/mnt/ams2/cal/hd_images/" + day + "/"
   cameras = json_conf['cameras']
   for id in  cameras:
      cam_id = json_conf['cameras'][id]['cams_id'] 
      print(cam_id)
      masks = get_masks(cam_id, json_conf,1)
      print (day_dir + "*" + cam_id + "*.png")
      hd_files = glob.glob(day_dir + "*" + cam_id + "-stacked.png")
      for hd_file in sorted(hd_files):
         print(hd_file)
         close_stars = []
         cp_file = hd_file.replace("-stacked.png", "-calparams.json")
         if cfe(cp_file) == 0:
            img = cv2.imread(hd_file, 0)
            img = mask_frame(img, [], masks)
            avg_br = np.mean(img) 
            if avg_br < 65:
               (cat_image_stars, img, no_match_stars, avg_res,match_per,cp_data) = get_stars_from_image(hd_file,json_conf, masks, None, 0)
               for name,mag,ra,dec,new_cat_x,new_cat_y,ix,iy,px_dist,cal_params_file in cat_image_stars:
                  close_stars.append(( name,mag,ra,dec,0,0,px_dist,new_cat_x,new_cat_y,0,0,new_cat_x,new_cat_y,ix,iy,px_dist))

               if show == 1:
                  show_img = cv2.resize(img, (960,540))
                  cv2.putText(show_img, hd_file,  (5,500), cv2.FONT_HERSHEY_SIMPLEX, .5, (255, 255, 255), 1)
                  cv2.putText(show_img, "BR: " + str(avg_br),  (5,450), cv2.FONT_HERSHEY_SIMPLEX, .5, (255, 255, 255), 1)
                  cv2.imshow('pepe', show_img) 
                  cv2.waitKey(30)
               if 'cat_stars' in cp_data:
                  del cp_data['cat_stars'] 
               cp_data['cat_image_stars'] = close_stars
               if "cat_img_stars" in cp_data: 
                  del cp_data['cat_img_stars'] 
               #if "user_stars" in cp_data: 
               #   del cp_data['user_stars'] 
               if "close_stars" in cp_data: 
                  del cp_data['close_stars'] 
               
               save_json_file(cp_file, cp_data)
         else:
            print  (hd_file)
            img = cv2.imread(hd_file, 0)
            cp_file = hd_file.replace("-stacked.png", "-calparams.json")
            print("CP FILE: ", cp_file)
            cal_params = load_json_file(cp_file)

            for star in cal_params['cat_image_stars']:
               name,mag,ra,dec,temp1,temp2,px_dist,new_cat_x,new_cat_y,temp3,temp4,new_cat_x,new_cat_y,ix,iy,px_dist = star
   
            if show == 1:
               show_img = cv2.resize(img, (960,540))
               cv2.circle(img,(ix,iy), 5, (128,128,128), 1)
               cv2.rectangle(img, (new_cat_x-5, new_cat_y-5), (new_cat_x + 5, new_cat_y + 5), (128, 128, 128), 1)
               cv2.line(img, (ix,iy), (new_cat_x,new_cat_y), (255), 1)
               #cv2.putText(show_img, hd_file,  (5,500), cv2.FONT_HERSHEY_SIMPLEX, .5, (255, 255, 255), 1)
               #cv2.putText(show_img, "BR: " + str(avg_br),  (5,450), cv2.FONT_HERSHEY_SIMPLEX, .5, (255, 255, 255), 1)
               cv2.putText(show_img, "DONE! ", (5,500), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 1)       
               cv2.imshow('pepe', show_img) 
               cv2.waitKey(30)

def run_job(job, json_conf):
   fp = open(job)
   jobs = []
   for line in fp:
      line = line.replace("\n", "")
      print(line)   
      jobs.append(line)

   if 'max_procs' in json_conf['site']:
      max_procs = json_conf['site']['max_procs']
   else:
      max_procs = 4

   jc = 0
   job_name = "mikeTrajectory.py"
   #job_name = "reducer2.py"
   for job in jobs:


      while check_running(job_name) > max_procs:
         time.sleep(1)
      print(job)
      #if "010002" in job:
      os.system(job + " &")
      jc = jc + 1




cgitb.enable()

json_conf = load_json_file("../conf/as6.json")
cmd = sys.argv[1]
try:
   date = sys.argv[2]
except:
   date = None

try:
   show = int(sys.argv[3])
except: 
   show = 0
if cmd == 'weather':
   scmd = ""
   all_i_files = track_stars(date, json_conf, scmd, None, show)
   weather = sum_weather(all_i_files,json_conf)
   for key in sorted(weather):
      if weather[key] < 0:
         status = 'very bad' 
      if weather[key] < 10:
         status = 'bad' 
      if 10 < weather[key] < 20:
         status = 'ok' 
      if weather[key] >= 20:
         status = 'good' 
      if weather[key] >= 30:
         status = 'great' 
      print(key, weather[key], status)



if cmd == 'hd_cal':
  scmd = ''
  print("SHOW: ", show)
  all_i_files = track_stars(date, json_conf, scmd, None, show)
  hd_cal(all_i_files, json_conf, date,show)

if cmd == 'save_cal':
   starfile = sys.argv[2]
   master_cal_file = starfile.replace("-allstars.json", "-master_cal_params.json")
   save_cal(starfile, master_cal_file, json_conf)

if cmd == 'mm':
   starfile = sys.argv[2]
   master_cal_file = starfile.replace("-allstars.json", "-master_cal_params.json")
   all_i_files = load_json_file(starfile)
   master_cal_params = load_json_file(master_cal_file)
   multi_merge(all_i_files,master_cal_params,master_cal_file,json_conf)

if cmd == 'multi_fit':
   scmd = ''
   all_i_files = track_stars(date, json_conf, scmd, None, show)
   multi_merge(all_i_files,json_conf)

if cmd == 'all':
   cam_id = sys.argv[3]
   all_i_files = track_stars(date, json_conf, scmd, None, show)
   startrack_file = "/mnt/ams2/cal/autocal/startrack/" + date + "_" + cam_id + ".json"
   #save_json_file(startrack_file, starlist)
   #save_hd_files(starlist)
   #calibrate_hd_files(date,cam_id,json_conf)
if cmd == 'latlon':
   cal_params_file = sys.argv[2]
   #minimize_latlon(cal_params_file, json_conf)
if cmd == 'cfit':
   meteor_json = sys.argv[2]
   if "mp4" in meteor_json:
      meteor_json = meteor_json.replace(".mp4", ".json")
   if len(sys.argv) == 4:
      show = int(sys.argv[3])
   #os.system("./autoCal.py imgstars " + meteor_json + " " + str(show))
   meteor_json_file_red = meteor_json.replace(".json", "-reduced.json")
   mj = load_json_file(meteor_json_file_red)
   if 'cal_params' in mj:
      if 'total_res_deg' in mj['cal_params']:
         if 0 < mj['cal_params']['total_res_deg'] <= .08 :
            print("This file is good and doesn't need to be refit.")
            exit()
      if 'cat_img_stars' in mj['cal_params']:
         if len(mj['cal_param']['cat_image_stars']) < 5:
            print("There aren't enough stars to custom fit. Use best defaults instead.") 
            exit()
   else:
      os.system("./autoCal.py imgstars " + meteor_json)


   if 'hd_stack' in mj:
      image_file = mj['hd_stack']
   else:
      if "sd_stack" in mj:
         image_file = mj['sd_stack']

   if "cal_params" in mj:
      cal_params = mj['cal_params']
   else:
      cmd = "./autoCal.py imgstars " + meteor_json
      print("run image stars first", cmd)
      os.system(cmd)
      mj = load_json_file(meteor_json_file_red)
      print("MIKE:", meteor_json_file_red)
      cal_params = mj['cal_params']

   if "center_az" not in cal_params or "cat_image_stars" not in cal_params:
      os.system("./autoCal.py imgstars " + meteor_json)
      mj = load_json_file(meteor_json_file_red)
      cal_params = mj['cal_params']

   #print("START AZ:", cal_params['center_az'])
   #print("START EL:", cal_params['center_el'])
   #print("START POS:", cal_params['position_angle'])
   #print("STArt PIXSCALE:", cal_params['pixscale'])

   #print("FOV BEFORE:", cal_params['center_az'], cal_params['center_el'])
   fov_poly, cal_params = minimize_fov_pos(meteor_json, image_file, json_conf, cal_params, show)
   #print("FOV AFTER:", cal_params['center_az'], cal_params['center_el'])
   mj['cal_params'] = cal_params 
   #print(cal_params['x_poly'])
   #print("FINAL AZ:", cal_params['center_az'])
   #print("FINAL EL:", cal_params['center_el'])
   #print("FINAL POS:", cal_params['position_angle'])
   #print("FINAL PIXSCALE:", cal_params['pixscale'])

   print("SAVING JSON RED FILE: ", meteor_json_file_red)
   save_json_file(meteor_json_file_red, mj)
   cmd1 = "cd /home/ams/amscams/pythonv2/; ./autoCal.py imgstars " + meteor_json + " 0 > /mnt/ams2/tmp/autoCal.txt "
   #print(cmd1)
   #os.system(cmd1)
   #os.system("./autoCal.py imgstars " + meteor_json + " " + str(show))


if cmd == 'cfit_hdcal':
   cal_params_file = sys.argv[2]
   meteor_json = {}
   if len(sys.argv) == 4:
      show = int(sys.argv[3])
   cal_params = load_json_file(cal_params_file)
   image_file = cal_params_file.replace(".json", "-stacked.png")

   (f_datetime, cam_id, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(cal_params_file)
   fn = cal_params_file.split("/")[-1]
   day_dir = cal_params_file.replace(fn, "")
   master_cal_file = day_dir + "/master_cal_file_" + cam_id + ".json"
   if cfe(master_cal_file) == 1:
      #print ("USE MASTER _CAL", master_cal_file)
      mcf = load_json_file(master_cal_file)
      cal_params['x_poly'] = mcf['x_poly']
      cal_params['y_poly'] = mcf['y_poly']
      cal_params['x_poly_fwd'] = mcf['x_poly_fwd']
      cal_params['y_poly_fwd'] = mcf['y_poly_fwd']

   if "close_stars" in cal_params:
      meteor_json['cat_image_stars'] = cal_params['close_stars']
   elif "cat_image_stars" in cal_params:
      meteor_json['cat_image_stars'] = cal_params['cat_image_stars']
   else:
      print("NO CAT IMAGE STARS!")
      exit()
   image_file = image_file.replace("-calparams", "")
   #print("IMGAGE: ", image_file)

   (f_datetime, cam_id, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(cal_params_file)
   masks = get_masks(cam_id, json_conf,1)
   if "cat_image_stars" in cal_params:
      cat_image_stars = cal_params['cat_image_stars']
      close_stars = cat_image_stars
   else:
      cat_image_stars, img, no_match, res_err, match_per,cp_data = get_stars_from_image(image_file, json_conf, masks, cal_params, show)
      close_stars = []
      for name,mag,ra,dec,new_cat_x,new_cat_y,ix,iy,px_dist,cp_file in cat_image_stars:
         close_stars.append(( name,mag,ra,dec,0,0,px_dist,new_cat_x,new_cat_y,0,0,new_cat_x,new_cat_y,ix,iy,px_dist))
   cal_params['cat_image_stars'] = close_stars 

   fov_poly, cal_params = minimize_fov_pos(cal_params, image_file, json_conf, cal_params, show)

   cat_image_stars, img, no_match, res_err, match_per,cp_data = get_stars_from_image(image_file, json_conf, masks, cal_params, show)
   close_stars = []
   for name,mag,ra,dec,new_cat_x,new_cat_y,ix,iy,px_dist,cp_file in cat_image_stars:
      close_stars.append(( name,mag,ra,dec,0,0,px_dist,new_cat_x,new_cat_y,0,0,new_cat_x,new_cat_y,ix,iy,px_dist))
   cal_params['cat_image_stars'] = close_stars 

   save_json_file(cal_params_file, cal_params)
 
if cmd == "batch_fix":
   batch_fix(json_conf)

if cmd == 'star_res':
   meteor_json_file = sys.argv[2]
   res,stars,img = star_res(meteor_json_file, json_conf, show)
   print("RES:", res)

if cmd == 'imgstars' or cmd == 'imgstars_strict':
   if cmd == 'imgstars_strict':
      strict = 1
   else:
      strict = 0
   print("IMGSTARS")
   meteor_mode = 0
   if len(sys.argv) == 4:
      show = int(sys.argv[3])
   meteor_json_file = sys.argv[2]
   if ".mp4" in meteor_json_file:
      meteor_json_file = meteor_json_file.replace(".mp4", ".json")
   if "calparams" not in meteor_json_file:
      meteor_mode = 1
      meteor_json_file_red = meteor_json_file.replace(".json", "-reduced.json")
      meteor_json = load_json_file(meteor_json_file_red)
      for key in meteor_json :
         print(key)
      if "hd_stack" in meteor_json:
         file = meteor_json['hd_stack']
      else:
         print("No hd stack?", meteor_json)
         exit()
         hd_stack = meteor_json['hd_trim'].replace(".mp4", "-stacked.png")
         file = hd_stack
      if cfe(file) == 0:
         file = file.replace(".png", "-stacked.png")
         meteor_json['hd_stack'] = file
      if "cal_params" in meteor_json:
         cal_params = meteor_json['cal_params']
      else:
         poss = get_active_cal_file(file)
         cal_params_file = poss[0][0]
         cal_params = load_json_file(cal_params_file)
         print("Try to use cal params:", cal_params_file)
         meteor_json['cal_params'] = cal_params
         if "tried_cal" not in meteor_json:
            meteor_json['tried_cal'] = []
            meteor_json['tried_cal'].append(cal_params_file)
         else:
            already_tried = 1
            next_one = len(meteor_json['tried_cal'])
            cal_params_file = poss[next_one][0]
            cal_params = load_json_file(cal_params_file)
            meteor_json['cal_params'] = cal_params
            meteor_json['tried_cal'].append(cal_params_file)
            
         if len(meteor_json['tried_cal']) > 3:
            meteor_json['tried_cal'] = []
 
         meteor_json['cal_params'] = cal_params 
         print("Saving json file....", meteor_json_file_red)
         if "manual_update" not in cal_params:
            print("SAVING CALP:", meteor_json_file_red)
            save_json_file(meteor_json_file_red, meteor_json)
         else: 
            print("SAVING CALP:", meteor_json_file_red)
            save_json_file(meteor_json_file_red, meteor_json)
         print("Try to use cal params:", cal_params_file)
   else:
      print(meteor_json_file)
      try:
         meteor_json = load_json_file(meteor_json_file)
      except:
         print("Corrupt file:", meteor_json_file)
         os.system("rm " + meteor_json_file)
         exit()
      meteor_json_file_red = meteor_json_file
      cal_params = meteor_json
      file = meteor_json_file.replace("-calparams.json", "-stacked.png")

   (f_datetime, cam_id, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(file)
   masks = get_masks(cam_id, json_conf,1)
   if "meteor_frame_data" in meteor_json:
      (box_min_x,box_min_y,box_max_x,box_max_y) = define_crop_box(meteor_json['meteor_frame_data'])
      meteor_json['crop_box'] = (box_min_x,box_min_y,box_max_x,box_max_y)
      box_w = box_max_x - box_min_x 
      box_h = box_max_y - box_min_y
      mask_s = str(box_min_x) + "," + str(box_min_y) + "," + str(box_w) + "," + str(box_h)
      masks.append(mask_s)


   if cal_params == 0:
      poss = get_active_cal_file(file)
      cal_params_file = poss[0][0]
      cal_params = load_json_file(cal_params_file)
   if "center_az" not in cal_params:
      poss = get_active_cal_file(file)
      cal_params_file = poss[0][0]
      cal_params = load_json_file(cal_params_file)
      if meteor_mode == 1:
         meteor_json['cal_params'] = cal_params


   center_az = cal_params['center_az']
   center_el = cal_params['center_el']
   rah,dech = AzEltoRADec(center_az,center_el,meteor_json_file,cal_params,json_conf)
   rah = str(rah).replace(":", " ")
   dech = str(dech).replace(":", " ")
   ra_center,dec_center = HMS2deg(str(rah),str(dech))
   cal_params['ra_center'] = ra_center
   cal_params['dec_center'] = dec_center


   fn = meteor_json_file.split("/")[-1]
   day_dir = meteor_json_file.replace(fn, "")
   master_cal_file = "/mnt/ams2/cal/hd_images/" + "/master_cal_file_" + cam_id + ".json"
   if cfe(master_cal_file) == 1:
      print("MASTER:", master_cal_file)
      mcf = load_json_file(master_cal_file)
      cal_params['x_poly'] = mcf['x_poly']
      cal_params['y_poly'] = mcf['y_poly']
      cal_params['x_poly_fwd'] = mcf['x_poly_fwd']
      cal_params['y_poly_fwd'] = mcf['y_poly_fwd']

   if "pixscale" not in cal_params:
      cal_params['pixscale'] = 158
   if "imagew" not in cal_params:
      cal_params['imagew'] = 1920
   if "imageh" not in cal_params:
      cal_params['imageh'] = 1080 

   print("XPOLY0:", cal_params['x_poly'][0])
   print("FOV:", cal_params['center_az'], cal_params['center_el'])
   if cfe(file) == 0:
      if "calparams" in meteor_json_file:
         file = meteor_json_file.replace("-calparams.json", ".png")
         
      else:
         file = meteor_json['sd_stack'].replace(".png", "-stacked.png")
   print("CAL VARS:", cal_params['center_az'], cal_params['center_el'], cal_params['position_angle'], cal_params['pixscale'])
   if "cat_image_stars" in cal_params:
      if len(cal_params['cat_image_stars']) == 0:
         cat_image_stars, img, no_match, res_err, match_per,cp_data = get_stars_from_image(file, json_conf, masks, cal_params, show, strict)
      else:
         print("We already have stars.")
         exit()
   else:
      cat_image_stars, img, no_match, res_err, match_per,cp_data = get_stars_from_image(file, json_conf, masks, cal_params, show, strict)
   cal_params['total_res_px'] = res_err
   cal_params['total_res_deg'] = ((float(res_err) * float(cal_params['pixscale'])) / 60) / 60
   print("MATCH/NO MATCH: ", len(cat_image_stars), len(no_match))
   if len(cat_image_stars) > 0 and len(no_match) > 0:
      good_perc = len(cat_image_stars) / len(no_match)
   else:
      good_perc = 0
   if len(cat_image_stars) > 0 and len(no_match) == 0:
      good_perc = 1
   print("PERC GOOD:", good_perc)

   # failure loop
   if good_perc < .05 and res_err > 8:
      print("Problem here. Let's clean up. try again...", meteor_json_file )
      if 'cal_params' in meteor_json:
         del meteor_json['cal_params']  
      if 'cal_params_file' in meteor_json:
         del meteor_json['cal_params_file']  
      meteor_json['deleted_tries']  = 1
      meteor_json['tried_cal'] = []
      save_json_file(meteor_json_file_red, meteor_json)
 
      if "tried_cal" in meteor_json:
         print("WILL TRY A NEW CALIBRATION on next run...")
         if len(meteor_json['tried_cal']) < 4 :
            cmd = "./autoCal.py imgstars " + meteor_json_file + " 0"
            print(cmd)
            #os.system(cmd)
            exit()

      meteor_json['cal_params'] = cal_params  
      if "manual_update" not in cal_params:
         if meteor_mode == 1:
            save_json_file(meteor_json_file_red, meteor_json)
         else:
            save_json_file(meteor_json_file_red, cal_params)
      else: 
         print("no more saving cal stars for this file since they have been manually selected.")
     
      exit()


   # compute std dev distance
   tot_res = 0
   #close_stars = []
   dist_list = []
   sc = 0
   for name,mag,ra,dec,new_cat_x,new_cat_y,ix,iy,px_dist,cp_file in cat_image_stars:
      #px_dist = calc_dist((ix,iy),(new_cat_x,new_cat_y))
      #print("STAR DATA:", sc, name, new_cat_x, new_cat_y, ix, iy, px_dist)
      dist_list.append(px_dist)
      tot_res = tot_res + px_dist
      sc = sc + 1
   std_dev_dist = np.std(dist_list)
   close_stars = []

   for name,mag,ra,dec,new_cat_x,new_cat_y,ix,iy,px_dist,cp_file in cat_image_stars:
      if meteor_mode == 0:
         close_stars.append(( name,mag,ra,dec,0,0,px_dist,new_cat_x,new_cat_y,0,0,new_cat_x,new_cat_y,ix,iy,px_dist))
      if meteor_mode == 1:
         close_stars.append(( name,mag,ra,dec,0,0,px_dist,new_cat_x,new_cat_y,0,0,new_cat_x,new_cat_y,ix,iy,px_dist))

   if "cat_stars" in cal_params: 
      del cal_params['cat_stars']
   if "cat_img_stars" in cal_params: 
      del cal_params['cat_img_stars']
   #print("CHECK FOR USER STARS:")
   #if "user_stars" in cal_params.keys(): 
      #print("DELETE user_stars")
      #del cal_params['user_stars']
   
   if len(cat_image_stars) > 0:
      res_err = tot_res / len(cat_image_stars)
   else:
      res_err = 9999
   center_az = cal_params['center_az']
   center_el = cal_params['center_el']
   rah,dech = AzEltoRADec(center_az,center_el,file,cal_params,json_conf)
   rah = str(rah).replace(":", " ")
   dech = str(dech).replace(":", " ")
   ra_center,dec_center = HMS2deg(str(rah),str(dech))
   cal_params['ra_center'] = ra_center
   cal_params['dec_center'] = dec_center
   cal_params['astro_res_err'] = res_err
   cal_params['cat_image_stars'] = close_stars 



   #print("FILE: ", file)
   print("RES ERR: ", cam_id, tot_res, res_err, len(close_stars) )
   cal_params['total_res_px'] = res_err
   #print("MATCH STARS: ", len(close_stars))
   if meteor_mode == 0:     
      if "cal_params" in cal_params: 
         del cal_params['cal_params']
   if "close_stars" in cal_params: 
      del cal_params['close_stars']

   #print("Saving:", meteor_json_file_red)
   #save_json_file(meteor_json_file_red, meteor_json)
   if meteor_mode == 0:
      if "manual_update" not in cal_params:
         save_json_file(meteor_json_file_red, cal_params)
   else:
      meteor_json['cal_params'] = cal_params
      if "manual_update" not in cal_params:
         save_json_file(meteor_json_file_red, meteor_json)
   


if cmd == 'batch_hd_fit':
   date = sys.argv[2]
   if len(sys.argv) == 4:
      scmd = sys.argv[3]
   else:
      scmd = "imgstars"
   print(scmd)
   batch_hd_fit(date, json_conf, scmd)

if cmd == 'scan_hd_images':
   date = sys.argv[2]
   if date == "today":
      day = datetime.datetime.today().strftime('%Y_%m_%d')
      print(day)

   scan_hd_images(date, json_conf)
if cmd == 'make_hd_images':
   date = sys.argv[2]
   if date == "today":
      day = datetime.today().strftime('%Y_%m_%d')
      print(day)
   make_hd_images(day, json_conf)
   if date == "today":
      scan_hd_images(day, json_conf)
   if date == "today":
      batch_hd_fit(day, json_conf,'imgstars')
      batch_hd_fit(day, json_conf,'cfit')
   if date == "today":
      hd_cal_index(json_conf)

if cmd == 'night_cal':
   date = sys.argv[2]
   if len(sys.argv) == 4:
      show = int(sys.argv[3])
   print("date:", date)
   night_cal(date, json_conf, show)

if cmd == 'night_sum':
   date = sys.argv[2]
   if len(sys.argv) == 4:
      show = int(sys.argv[3])
   night_sum(date, json_conf, show)
if cmd == 'master_merge':
   cam_id = sys.argv[2]
   master_merge(cam_id)
if cmd == 'meteor_cal_all':
   meteor_cal_all(json_conf,show)

if cmd == 'meteor_cal':
   date = sys.argv[2]
   if len(sys.argv) == 4:
      show = int(sys.argv[3])
   print("date:", date)
   print("show:", show)
   meteor_cal(date, json_conf, show)
if cmd == 'run_merge':
   merge_file = sys.argv[2]
   if len(sys.argv) == 5:
      show = int(sys.argv[4])
   cam_id = sys.argv[3]
   new_starlist = merge_file.replace(".json", "-clean.json")
   if cfe(new_starlist) == 1:
      #merge_stars = load_json_file(new_starlist)
      merge_stars = load_json_file(merge_file)
   else:
      merge_stars = load_json_file(merge_file)
   cam_stars = {}
   master_cal_params = {}
   fn = merge_file.split("/")[-1]
   day_dir = merge_file.replace(fn, "")
   master_cal_file = day_dir + "/master_cal_file_" + cam_id + ".json"
   print("SHOW:", show)
   status, fin_cal_params, new_merge_stars = minimize_poly_params_fwd(merge_stars, json_conf,0,0,cam_id, master_cal_file,show )

   if type(fin_cal_params) is not int :
      for key in fin_cal_params:
         print(key)
         master_cal_params[key] = fin_cal_params[key]
      if status == 1 :
         print("SAVING MCF:", master_cal_file)
         save_json_file(master_cal_file, master_cal_params)
         save_json_file(new_starlist, new_merge_stars)
if cmd == "cal_index":
   cal_index(json_conf)
if cmd == "hd_cal_index":
   extra_cmd = ""
   if len(sys.argv) == 3:
      extra_cmd = sys.argv[2]
   hd_cal_index(hd_cal_index, extra_cmd)

if cmd == "meteor_index":
   extra_cmd = ""
   day = None
   if len(sys.argv) == 3:
      day = sys.argv[2]
   if(json_conf is not False):
      meteor_index(json_conf, day)

if cmd == "rr" or cmd == 'reset_reduce':
   reset_reduce(json_conf, sys.argv[2])
if cmd == "best_fov" or cmd == 'bf':
   find_best_fov(sys.argv[2], json_conf)
if cmd == "run_job" or cmd == 'rj' or cmd == 'jr':
   run_job(sys.argv[2], json_conf)
if cmd == "cams_exp" :
   check(sys.argv[2])
   cams_exp(sys.argv[2], json_conf)
if cmd == "star_merge_movie" or cmd == "smm":
   star_merge_movie(json_conf)
if cmd == "check":
   check(sys.argv[2])   
if cmd == "run_detects":
   run_detects(sys.argv[2])   
if cmd == "update_arc_detects" or cmd == 'uad':
   update_arc_detects()   
if cmd == "md" or cmd == 'month_detects':
   print("MD")
   month_detects(sys.argv[2])   
if cmd == "cp_mi" or cmd == 'cp_meteor_index':
   if len(sys.argv) == 3:
      print("DAY")
      cp_meteor_index(sys.argv[2])
   else:
      cp_meteor_index()



