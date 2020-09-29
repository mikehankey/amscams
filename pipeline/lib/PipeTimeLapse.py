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
from lib.PipeUtil import cfe, save_json_file, convert_filename_to_date_cam, load_json_file, day_or_night
from lib.PipeAutoCal import fn_dir, get_cal_files
from lib.DEFAULTS import *
import numpy as np

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

def check_for_missing(min_file,cams_id,json_conf):
   cam_id_info, cam_num_info = load_cam_info(json_conf)
   print("LOOK FOR:", min_file)
   missing = []
   date = min_file[0:10] 
   hd_wild = "/mnt/ams2/HD/" + min_file + "*" + cams_id + "*.mp4"
   snap_wild = "/mnt/ams2/SNAPS/" + date + "/" + min_file  + "*" + cams_id  + "*.jpg"
   snap_wild2 = "/mnt/ams2/SNAPS/" + min_file  + "*" + cams_id + "*.png"
   sd_night = "/mnt/ams2/SD/proc2/" + date + "/"  + "*" + cams_id + min_file + "*.mp4"
   sd_day = "/mnt/ams2/SD/proc2/daytime/" + date + "/" + min_file  + "*" + cams_id + "*.mp4"
   sd_day2 = "/mnt/ams2/SD/proc2/daytime/" + min_file  + "*" + cams_id + "*.mp4"
   sd_pending = "/mnt/ams2/SD/" + min_file  + "*" + cams_id + "*.mp4"

   print(hd_wild)
   print(snap_wild)
   print(snap_wild2)
   print(sd_night)
   print(sd_day)
   print(sd_day2)
   print(sd_pending)

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

   # first check for pics
   for ms in missing:
      if "png" in ms or "jpg" in ms:
         # score use this file
         img = cv2.imread(ms)
         img = cv2.resize(img, (THUMB_W, THUMB_H))
         print("FOUND!", ms)
         return(img)
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
            return(img)
         else:
            cmd = "/usr/bin/ffmpeg -ss 00:00:01.00 -i " + ms + " -frames:v 1 -y " + mia_out 
            print(cmd)
            os.system(cmd)
            img = cv2.imread(mia_out) 
            print("READING:", mia_out)
         try:
            img = cv2.resize(img, (THUMB_W, THUMB_H))
            return(img)
         except:
            print("BAD FILE:", mia_out, missing)
            return(None)



   return(None)

def load_cam_info(json_conf):
   cam_num_info = {} 
   cam_id_info = {} 
   for cam in sorted(json_conf['cameras'].keys()):
      cams_id = json_conf['cameras'][cam]['cams_id']
      cam_id_info[cams_id] = cam
      cam_num_info[cam] = cams_id
   return(cam_id_info, cam_num_info)


def audit_min(date, json_conf):
   mm = 0
   cam_id_info, cam_num_info = load_cam_info(json_conf)
   # check the files that could be missig and why
   data_file = TL_VIDEO_DIR + date + "-audit.json"
   data = {}
   #minutes = load_json_file(data_file)
   hd_files = glob.glob("/mnt/ams2/HD/" + date + "*.mp4")
   sd_files = glob.glob("/mnt/ams2/SD/proc2/" + date + "/*.mp4")
   sd_day_files = glob.glob("/mnt/ams2/SD/proc2/daytime/" + date + "/*.mp4")
   sd_queue_files = glob.glob("/mnt/ams2/SD/" + date + "*.mp4")
   sd_day_queue_files = glob.glob("/mnt/ams2/SD/proc2/daytime/" + date + "*.mp4")
   print("HD:", len(hd_files))
   print("SD:", len(sd_files))
   print("SDD:", len(sd_day_files))
   print("SDQ:", len(sd_queue_files))
   print("SDDQ:", len(sd_day_queue_files))
   total_cams = len(json_conf['cameras'].keys())
   today = datetime.now().strftime("%Y_%m_%d")
   yesterday = (datetime.now() - dt.timedelta(days = 1)).strftime("%Y_%m_%d")
   if today == date : 
      limit_h = int(datetime.now().strftime("%H"))
      limit_m = int(datetime.now().strftime("%M"))
   else :
      limit_h = 23
      limit_m = 59

   for h in range(0,24):
      if h not in data:
         data[h] = {}
      for m in range(0,60):
         if m not in data[h]:
            data[h][m] = {}
         for cam in cam_num_info:
            if cam not in data[h][m]:
               f_date_str = date + " " + str(h) + ":" + str(m) + ":00" 
               f_date_str = f_date_str.replace("_", "/")
               sun_status, sun_az, sun_el = day_or_night(f_date_str, json_conf,1)
               print("SUN", f_date_str, sun_status, sun_az, sun_el)
               data[h][m][cam] = {}
               data[h][m][cam]['cam_num'] = cam
               data[h][m][cam]['id'] = cam_num_info[cam]
               data[h][m][cam]['sd_file'] = []
               data[h][m][cam]['hd_file'] = []
               data[h][m][cam]['stack_file'] = []
               data[h][m][cam]['meteors'] = []
               data[h][m][cam]['weather'] = []
               data[h][m][cam]['sun'] = [[sun_status, sun_az, sun_el]]

   for file in sorted(hd_files):
      (sd_datetime, sd_cam, sd_date, sd_y, sd_m, sd_d, sd_h, sd_M, sd_s) = convert_filename_to_date_cam(file)
      if "trim" not in file:
         #print("HD FILE:", sd_h, sd_M, sd_cam, cam_id_info[sd_cam])

         cam_num = cam_id_info[sd_cam]
         sd_h = int(sd_h)
         sd_M = int(sd_M)
         data[sd_h][sd_M][cam_num]['hd_file'].append(file)
   for file in sorted(sd_files):
      fn, dir = fn_dir(file)
      (sd_datetime, sd_cam, sd_date, sd_y, sd_m, sd_d, sd_h, sd_M, sd_s) = convert_filename_to_date_cam(file)
      if "trim" not in file:
         cam_num = cam_id_info[sd_cam]
         sd_h = int(sd_h)
         sd_M = int(sd_M)
         data[sd_h][sd_M][cam_num]['sd_file'].append(file)
         stack_file = dir + "images/" + fn
         stack_file = stack_file.replace(".mp4", "-stacked-tn.png")
         print("STACK:", stack_file)
         if cfe(stack_file) == 1:
            data[sd_h][sd_M][cam_num]['stack_file'].append(stack_file)
         else:
            print("STACK NOT FOUND!:", stack_file)
   for file in sorted(sd_day_files):
      (sd_datetime, sd_cam, sd_date, sd_y, sd_m, sd_d, sd_h, sd_M, sd_s) = convert_filename_to_date_cam(file)
      fn, dir = fn_dir(file)
      if "trim" not in file:
         cam_num = cam_id_info[sd_cam]
         sd_h = int(sd_h)
         sd_M = int(sd_M)
         stack_file = dir + "images/" + fn
         stack_file = stack_file.replace(".mp4", "-stacked-tn.png")
         print("DAY STACK:", stack_file)
         if cfe(stack_file) == 1:
            data[sd_h][sd_M][cam_num]['stack_file'].append(stack_file)
         else:
            print("DAY STACK NOT FOUND!:", stack_file)
         data[sd_h][sd_M][cam_num]['sd_file'].append(file)
   for file in sorted(sd_day_queue_files):
      (sd_datetime, sd_cam, sd_date, sd_y, sd_m, sd_d, sd_h, sd_M, sd_s) = convert_filename_to_date_cam(file)
      if "trim" not in file:
         cam_num = cam_id_info[sd_cam]
         sd_h = int(sd_h)
         sd_M = int(sd_M)
         data[sd_h][sd_M][cam_num]['sd_file'].append(file)
   for file in sorted(sd_queue_files):
      (sd_datetime, sd_cam, sd_date, sd_y, sd_m, sd_d, sd_h, sd_M, sd_s) = convert_filename_to_date_cam(file)
      if "trim" not in file:
         cam_num = cam_id_info[sd_cam]
         sd_h = int(sd_h)
         sd_M = int(sd_M)
         data[sd_h][sd_M][cam_num]['sd_file'].append(file)


   save_json_file(data_file, data)
   html = ""
   # find uptime
   updata = {}
   uptime_percs = []
   for hour in sorted(data.keys(), reverse=True):
      if hour not in updata:
         updata[hour] = {}
         updata[hour]['tfiles'] = 0
      if hour <= limit_h:
         for min in sorted(data[hour].keys(), reverse=True):
            if hour == limit_h and min >= limit_m:
               continue
            for cam in data[hour][min]:
               tfiles = len(data[hour][min][cam]['sd_file']) + len(data[hour][min][cam]['hd_file'])
               updata[hour]['tfiles'] += tfiles

   for hour in sorted(data.keys(), reverse=True):
      if hour <= limit_h:
         if html != "":
            html += str(hour) + "</table>"
         if hour == limit_h: 
            tot_m = limit_m 
         else:
            tot_m = 60
         uptime_perc = str((updata[hour]['tfiles'] / (tot_m*total_cams*2) * 100))[0:5]
         uptime_percs.append((hour,uptime_perc)) 
         html += " " + str(updata[hour]['tfiles']) + " files of " +  str(tot_m*total_cams*2) + " expected. " + uptime_perc + "% uptime <table border=1>"
         for min in sorted(data[hour].keys(), reverse=True):
            if hour == limit_h and min >= limit_m:
               continue
            html += "<tr><td> " + str(hour) + ":" + str(min) + "</td>"
            html += "<td>" + str(data[hour][min][cam]['sun']) + "</td>"
            for cam in data[hour][min]:
            
               html += "<td>"
               if len(data[hour][min][cam]['sd_file']) == 0:
                  html += "<font color=red>X</font> "
               else:
                  html += "<font color=green>&check;</font> " #+ str(data[hour][min][cam]['sd_file'])
               if len(data[hour][min][cam]['stack_file']) > 0:
                  jpg = data[hour][min][cam]['stack_file'][0].replace(".png", ".jpg")
                  if cfe(jpg) == 0:
                     cmd = "convert -quality 80 " + data[hour][min][cam]['stack_file'][0] + " " + jpg 
                     print(cmd)
                     os.system(cmd)

                  #html += "<img src=" + data[hour][min][cam]['stack_file'][0] + ">"
                  url = jpg.replace("-stacked-tn.jpg", ".mp4")
                  url = url.replace("images/", "")
                  html += "<a href=" + url + "><img src=" + jpg + "></a>"
               else:
                  if len(data[hour][min][cam]['hd_file']) == 0:
                     html += "<font color=red>X</font>"
                  else:
                     html += "<font color=green>&check;</font> "
               html += "</td>"
            html += "</tr>"
         html += "</table>"

   html_file = data_file.replace(".json", ".html")
   out = open(html_file, "w")
   out.write(html)
   print(html_file)
   cloud_dir = "/mnt/archive.allsky.tv/" + STATION_ID + "/LOGS/"  
   if cfe(cloud_dir, 1) == 0:
      os.makedirs(cloud_dir)
   outfile = cloud_dir + date + "_" + STATION_ID + "_uptime.json"
   up_data = {}
   up_data['uptime'] = uptime_percs
   save_json_file(outfile, up_data)
   print("Saved:", outfile)
 

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
   html = "<h1>Stacked Multi Camera Time Lapse for " + STATION_ID + "</h1>"      
   html += "<p>Last updated:" + datetime.now().strftime("%Y_%m_%d") + "</p><ul>"
   vids = glob.glob(TL_VIDEO_DIR + "*.mp4")
   for vid in sorted(vids,reverse=True):
      
      vid_fn, vdir = fn_dir(vid)
      vid_desc = vid_fn[0:10]
      html += "<li><a href=" + vid_fn + ">" + vid_desc + "</a></li>"
   html += "</ul>"
   oo = open(TL_VIDEO_DIR + "index.html", "w")
   oo.write(html)
   oo.close()
   print("saved:", TL_VIDEO_DIR + "index.html")
   TL_CLOUD_FILE = "/mnt/archive.allsky.tv/" + STATION_ID + "/TL/VIDS/index.html"
   oo = open(TL_CLOUD_FILE, "w")
   oo.write(html)
   oo.close()
   

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
   MIA_DIR = "/mnt/ams2/MIA/"
   files = glob.glob(MIA_DIR + "*")
   for file in files:
      (sd_datetime, sd_cam, sd_date, sd_y, sd_m, sd_d, sd_h, sd_M, sd_s) = convert_filename_to_date_cam(file)
      elp = sd_datetime - datetime.now()
      days_old = abs(elp.total_seconds()) / 86400
      print(file, days_old)


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
   for key in sorted(matrix.keys()):
      row_file = TL_PIC_DIR + key + "-row.png"
      row_file_tmp = TL_PIC_DIR + key + "-row_lr.jpg"
      redo = 0
      if cfe(row_file) == 1:
         fs = os.stat(row_file)
         fsize = fs.st_size
         if fsize < 4000:
            redo = 1
      if cfe(row_file) == 0 or redo == 1:
      #if True:
         if redo == 1:
            print("REDO!")
         h,m =key.split("-")
         min_file = date + "_" + h + "_" + m
         row_pic = make_row_pic(matrix[key], min_file, LOCATION + " " + date + " " + key.replace("-", ":") + " UTC", json_conf, cam_num_info)

         cv2.imwrite(row_file, row_pic)
         cmd = "convert -quality 80 " + row_file + " " + row_file_tmp
         os.system(cmd)
         #cmd = "mv " + row_file_tmp + " " + row_file
         #os.system(cmd)
         new += 1

         print("MAKE ROW:", key)
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
   for cam in sorted(data.keys()):
      file = data[cam]
      cams_id = cam_num_info[cam]
      if file != "":
         img = cv2.imread(file)
      else:
         print("MISSING DATA:", min_file, cams_id)
         missing_img = check_for_missing(min_file, cams_id, json_conf)
         if missing_img is not None:
            print("FIXED MISSING DATA FOR MIN/CAM:", min_file, cam)
            img = missing_img
         else:
            print("BAD NO DATA FOR MIN/CAM:", min_file, cam)
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

def make_tl_for_cam(date,cam, json_conf):
   print("TL:", cam, date)
   hd_dir = "/mnt/ams2/HD/"
   files = glob.glob(hd_dir + date + "*" + cam + "*.mp4")
   print("WILD:", hd_dir + date + "*" + cam + "*.mp4")
   tl_dir = TL_DIR + date + "/"
   print("FILES:", len(files))
   if cfe(tl_dir, 1) == 0:
      os.makedirs(tl_dir)
   for file in sorted(files):
      if "trim" not in file:
         fn = file.split("/")[-1]
         out_file = tl_dir + fn
         out_file = out_file.replace(".mp4", ".jpg")
         try:
            image = quick_video_stack(file, 1)
         except:
            continue
     
         #rot_image = rotate_bound(image, 72)
         #img_sm = cv2.resize(rot_image, (640, 360))
         #cv2.imshow('pepe', img_sm)
         #cv2.waitKey(0)

         if cfe(out_file) == 0:
           print(fn, file, out_file )
           try:
              cv2.imwrite(out_file, image)
           except:
              print("FAILED TO WRITE OUT: ", out_file)
         #cv2.imshow('pepe', show_frame)
         #cv2.waitKey(30)
   video_from_images(date, cam, json_conf)

def video_from_images(date, wild, json_conf ):
   TL_DIR = "/mnt/ams2/meteor_archive/" + STATION_ID + "/TL/VIDS/"
   tl_out = TL_DIR + "tl_" + date + "_" + wild + ".mp4"

   iwild = TL_DIR + "*" + wild + "*.jpg"

   print(iwild)
   cmd = "/usr/bin/ffmpeg -framerate 25 -pattern_type glob -i '" + iwild + "' -c:v libx264 -pix_fmt yuv420p -y " + tl_out + " >/dev/null 2>&1"
   print(cmd)
   os.system(cmd)
   print(tl_out)

def six_cam_video(date, json_conf):
   ### make 6 camera tl video for date

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
   video_from_images(date, "comp", json_conf)
       

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
