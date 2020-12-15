"""

Weather Related Functions

"""

import numpy as np
import cv2
import scipy.optimize

import glob
from datetime import datetime as dt
import datetime 

from lib.PipeAutoCal import get_best_cal, get_cal_files, fn_dir

#import math
import os
from lib.PipeAutoCal import fn_dir
from lib.PipeVideo import ffmpeg_splice, find_hd_file, load_frames_fast, find_crop_size, ffprobe, load_frames_simple
from lib.PipeUtil import load_json_file, save_json_file, cfe, get_masks, convert_filename_to_date_cam, buffered_start_end, get_masks, compute_intensity , bound_cnt, day_or_night, calc_dist
from lib.DEFAULTS import *
import glob
from lib.PipeImage import stack_frames

from matplotlib import pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
from lib.DEFAULTS import *
print(TL_IMAGE_DIR)


def sunset_tl(date, json_conf):
   print("Sunset:", date)
   afile = TL_DIR + "VIDS/" + date + "-audit.json"
    
   focus_cam = "cam1"
   if cfe(afile) == 1:
      adata = load_json_file(afile)
   else:
      print("Audit file not found.", afile)
      return()
   final_frames = {}
   for hour in sorted(adata):
      #print(key, adata[key][cam]['sun'], adata[key][cam]['sd_file'])
      for min in sorted(adata[hour]):
         hkey = '{:02d}'.format(hour)
         mkey = '{:02d}'.format(min)
         key = str(hkey) + "-" + str(mkey)
         for cam in sorted(adata[hour][min]):
            pos = str(mc_layout[cam])

         if key not in final_frames:
            final_frames[key] = { "1": "", "2": "", "3": "", "4": "", "5": "", "6": "" }
            final_frames[key][pos] = adata[hour][min][cam]['stack_file']
               
            stack_img = cv2.imread(stack_file)
            cv2.imshow('pepe', stack_img)
            #cv2.waitKey(50)

   for min_key in final_frames:
      print(min_key, final_frames[min_key])
      #outfile = tl_dir + "comp_" + min_key + ".jpg"
      #if cfe(outfile) == 0:
      #if True:
      #   make_six_image_comp(min_key, final_frames[min_key], 5)
      #else:
      #   print("skip.", min_key)
   #video_from_images(date, "comp", json_conf)



def stack_index(json_conf):
   cam_ids = []
   for cam_num in json_conf['cameras']:
      cams_id = json_conf['cameras'][cam_num]['cams_id']
      cam_ids.append(cams_id)
   night_stack_dir = "/mnt/ams2/meteor_archive/" + STATION_ID + "/STACKS/" 
   day_dirs = glob.glob(night_stack_dir + "*")
   html = "<table>"
   for day_dir in sorted(day_dirs, reverse=True):
      if cfe(day_dir, 1) == 0:
         continue
      html += "<tr>"
      fn, dir = fn_dir(day_dir)
      date = fn
      html += "<td>" + date + "</td>"
      for cam in sorted(cam_ids):
         file= day_dir + "/" + cam + "-night-stack.jpg"
         if cfe(file) == 1:
            url = day_dir + "/hours.html"
            
            html += "<td><a href=" + url + "><img src=" + file + "></a></td>"  
         else:
            html += "<td>" + " " + "</td>"  
      html += "</tr>"
   html += "</table>"
   fp = open(night_stack_dir + "all.html", "w")
   fp.write(html)
   fp.close()

def make_all_hourly_stacks(json_conf):
   days = glob.glob("/mnt/ams2/SD/proc2/*")
   for day_dir in sorted(days, reverse=True):
       
      day, dir = fn_dir(day_dir)
      el = day.split("_")
      if len(el) == 3:
         cmd = "./Process.py hs " + day
         os.system(cmd)
         print(cmd)

def hourly_stacks_html(date, json_conf):
   work_dir = "/mnt/ams2/SD/proc2/" + date + "/images/"
   night_stack_dir = "/mnt/ams2/meteor_archive/" + STATION_ID + "/STACKS/" + date + "/"
   hour_files = glob.glob(night_stack_dir + "*.jpg")
   html_data = {}
 
   night_images = {}
   day_images = {}
   
   cam_ids = []
   for cam_num in json_conf['cameras']:
      cams_id = json_conf['cameras'][cam_num]['cams_id']
      cam_ids.append(cams_id)
  
   for id in cam_ids:
      night_images[id] = [] 
      day_images[id] = [] 



   for file in sorted(hour_files, reverse=True):
      print(file)
      (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(file)
      sun_status, sun_az, sun_el = day_or_night(f_date_str, json_conf,1)
      if float(sun_el) > -15:
         print("DAYTIME FILE:", sun_el)

      fn, dir = fn_dir(file)
      if "night" not in file:
         el = fn.split("_")
         hour = el[3]
         cam = el[4].replace(".jpg", "")
         if hour not in html_data:
            html_data[hour] = {}
         html_data[hour][cam] = file

   html = "<table>"
   for h in range(0,24):
      hour = 23 - h
      hk =  '{:02d}'.format(int(hour))
      html += "<tr>"
      if hk in html_data:
        
         for cid in sorted(cam_ids):
            if cid in html_data[hk]:
               print("DATA:", html_data[hk][cid])
               fn, dir = fn_dir(html_data[hk][cid])
               print(fn)
               (y, m, d, h, c ) = fn.split("_")
               fdate = y + "/" + m + "/" + d + " " + h + ":00:00"
               sun_status, sun_az, sun_el = day_or_night(fdate, json_conf,1)
               print("SUN EL:",  sun_status, sun_az, sun_el)
               img = cv2.imread(html_data[hk][cid])
               if float(sun_el) < -20:
                  night_images[cid].append(img)
               else:
                  day_images[cid].append(img)
                  print("SKIP DAWN/DUSK:", sun_el)
               link = "/pycgi/webUI.py?cmd=browse_day&cams_id=" + cid + "&day=" + str(date) + "&hour=" + str(hour)
               html += "<td><a href=" + link + "><img src=" + html_data[hk][cid] + "></a></td>"
              
            else:
               print("Missing data for cam hour", cid, hk)
      else:
         print("No data for hour")     
      html += "</tr>"

   html += "</table>"
   for cam_id in night_images:
      print("NIGHT IMAGES:", cam_id, len(night_images[cam_id]))

      night_stack_image = stack_frames(night_images[cam_id], 1, None, "night")
      night_stack_file = "/mnt/ams2/SD/proc2/" + date + "/images/" + cam_id + "-night-stack.png"
      night_stack_file_jpg = "/mnt/ams2/meteor_archive/" + STATION_ID + "/STACKS/" + date + "/" + cam_id + "-night-stack.jpg"
      try:
         cv2.imwrite(night_stack_file, night_stack_image)
         cv2.imwrite(night_stack_file_jpg, night_stack_image)
         print(night_stack_file_jpg)
      except:
         print("Problem saving night stack file ", night_stack_file)
         exit()

      print(night_stack_file)

   fp = open(night_stack_dir + "hours.html", "w")
   fp.write(html)
   fp.close()
   print(night_stack_dir + "hours.html")
   stack_index(json_conf)


def meteor_night_stacks(date, json_conf):
   mdir = "/mnt/ams2/meteors/" + date + "/"
   stack_imgs = {}
   for cam in json_conf['cameras']:
      cams_id = json_conf['cameras'][cam]['cams_id']
      files = glob.glob(mdir + "*" + cams_id + "*.json")
      images = []
      for mf in files:
         if "reduced" not in mf and "stars" not in mf and "man" not in mf and "star" not in mf and "import" not in mf and "archive" not in mf:
            mj = load_json_file(mf)
            if "hd_stack" in mj:
               img = cv2.imread(mj['hd_stack'])
            elif "sd_stack" in mj:
               img = cv2.imread(mj['sd_stack'])
               img = cv2.resize(img,(1920,1080))
            images.append(img)
      print("IMAGES:", cams_id, len(images))
      if len(images) > 0:
         meteor_stack_image = stack_frames(images, 1, None, "night")
         stack_imgs[cams_id] = meteor_stack_image
         outfile = mdir + cams_id + "_meteors.jpg"
         print("SAVED:", outfile)
         cv2.imwrite(outfile, meteor_stack_image)

   if len(stack_imgs.keys()) == 6:
      comp_w = int((1920/2) * 2)
      comp_h = int((1080/2) * 3)
   elif len(stack_imgs.keys()) == 7:
      comp_w = int((1920/2) * 2)
      comp_h = int((1080/2) * 4)
   else:
      comp_w = 1920
      comp_h = int((1080/2) * len(stack_imgs.keys()) )

   comp = np.zeros((comp_h,comp_w,3),dtype=np.uint8)

   col = 0
   row = 0
   c = 0
   px1 = 0
   px2 = int(1920/2)   
   for cams_id in stack_imgs:
      #cams_id = json_conf['cameras'][cam]['cams_id']
      if c == 0:
         px1 = 0   
         px2 = int((1920/2))   
         py1 = int(row * (1080/2))
         py2 = int(py1 + (1080/2))
      elif c == 6 :
         px1 = int(0 + (1920/4))
         px2 = 1440
         py1 = 540 * 3
         py2 = 540 * 4
      elif c % 2 == 0 :
         px1 = 0   
         px2 = int((1920/2))   
         row += 1
         col = 1
         py1 = int(row * (1080/2))
         py2 = int(py1 + (1080/2))
      else:
         px1 = int((1920/2))   
         px2 = int(1920)   
         col = 2
         py1 = int(row * (1080/2))
         py2 = int(py1 + (1080/2))
      print("COMP XYS:", c, col, row, py1, py2, px1, px2)
      img = cv2.resize(stack_imgs[cams_id],(int(1920/2),int(1080/2)))
      comp[py1:py2,px1:px2] = img
      c += 1
   outfile = mdir + json_conf['site']['ams_id'] + "_meteors.jpg"
   cv2.imwrite(outfile, comp)
   print("Saved:", outfile)
   
def hourly_stacks(date, json_conf):
   hour_data = {}
   solar_hours = solar_info(date, json_conf)

   night_stack_dir = "/mnt/ams2/meteor_archive/" + STATION_ID + "/STACKS/" + date + "/"
   if cfe(night_stack_dir, 1) == 0:
      os.makedirs(night_stack_dir)
   work_dir = "/mnt/ams2/SD/proc2/" + date + "/images/"
   day_work_dir = "/mnt/ams2/SD/proc2/daytime/" + date + "/images/"
   for cam_num in json_conf['cameras']:
      cams_id = json_conf['cameras'][cam_num]['cams_id']
      if cams_id not in hour_data:
         hour_data[cams_id] = {}
      wild = work_dir + "*" + cams_id + "*-tn*"
      files = glob.glob(wild)
      for file in sorted(files):
         (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(file)
         if fh not in hour_data[cam]:
            hour_data[cam][fh] = {} 
            hour_data[cam][fh]['files'] = []
         hour_data[cam][fh]['files'].append(file)

      wild = day_work_dir + "*" + cams_id + "*-tn*"
      files = glob.glob(wild)
      print("DAY FILES:", wild, len(files))
      for file in sorted(files):
         (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(file)
         if fh not in hour_data[cam]:
            hour_data[cam][fh] = {} 
            hour_data[cam][fh]['files'] = []
         hour_data[cam][fh]['files'].append(file)

   for cam in hour_data:
       for hour in hour_data[cam]:
          print("HOUR DATA:", cam, hour, len(hour_data[cam][hour]['files']))

   for cam in hour_data:
       for hour in hour_data[cam]:
         images = []
         files = hour_data[cam][hour]['files']
         for file in files:
            (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(file)
            im = cv2.imread(file)
            images.append(im)
         print("SOLAR HOUR:", solar_hours[int(fh)])
         if int(fh) in solar_hours:
            sun_status, sun_az, sun_el = solar_hours[int(fh)]
            if float(sun_el) > -10:
               sun_status = "day"
         else:
            print("MISSING SOLAOR HOUR", int(fh))
            sun_status = "night"
         print("LAST HOUR/MIN SUN STATS:", fh, sun_status, len(images))
         hour_stack_image = stack_frames(images, 1, None, sun_status )
         if hour_stack_image is not None:
            hour_stack_file = night_stack_dir + fy + "_" + fm + "_" + fd + "_" + hour + "_" + cam + ".jpg"
            print(hour_stack_file, hour_stack_image.shape)
            cv2.imwrite(hour_stack_file, hour_stack_image)
         else:
            print("Data for Hour missing!")
   print("HOURLY1")
   hourly_stacks_html(date, json_conf)
   print("HOURLY2")

def tl_list(wild_dir, cam, fps = 25, json_conf=None, auonly = 1):
    files = glob.glob(wild_dir + "*" + cam + "*.jpg")
    list = ""
    dur = 1/ int(fps)
    for file in sorted(files): 
       if auonly == 1 and "-tl.jpg" in file:
          foo = 1
       else:
          list += "file '" + file + "'\n"
          list += "duration " + str(dur) + "\n"

    list_file = wild_dir + "/" + cam + "_list.txt"
    out_file = wild_dir + "/" + cam + ".mp4"
    fp = open(list_file, "w")
    fp.write(list)
    ow = 640
    oh = 360
    cmd = "/usr/bin/ffmpeg -r " + str(fps) + " -f concat -safe 0 -i " + list_file + " -c:v libx264 -pix_fmt yuv420p -vf 'scale=" + str(ow) + ":" + str(oh) + "' -y " + out_file
    print(cmd)
    os.system(cmd)

def aurora_tl(date, cam_num, json_conf):
   frate = 25
   dur = 1 / frate
   ow = 640
   oh = 360
   print(date,cam_num)
   afile = TL_DIR + "VIDS/" + date + "-audit.json"
   ad = load_json_file(afile)
   OUT_DIR = "/mnt/ams2/meteor_archive/" + STATION_ID + "/TL/AURORA/STACKS/" + date + "/" 
   cams_id = json_conf['cameras'][cam_num]['cams_id']
   cam_files = []
   for hour in ad:
      for min in ad[hour]:

         #comp = np.zeros((1080,1920,3),dtype=np.uint8)
         hk =  '{:02d}'.format(int(hour))
         mk =  '{:02d}'.format(int(min))
         if True:
            adata = ad[hour][min][cam_num]
            stack_file = None
            snap_file = None
            #print(adata)
            if len(adata['stack_file']) > 0:
               stack_file = adata['stack_file'][0]
            if len(adata['snap_file']) > 0:
               snap_file = adata['snap_file'][0]
            if stack_file is not None:
               fn,dir = fn_dir(stack_file)
            if snap_file is not None:
               fn,dir = fn_dir(snap_file)
            if stack_file is None and snap_file is None:
               continue
            print("FN:", fn)
            if "-" in fn:
               root = fn.split("-")[0]
            else:
               root = fn.split(".")[0]
            tl_fn = root + "-tl.jpg"

            tl_file = OUT_DIR + tl_fn
            print("TL FILE:", tl_file)
            if cfe(tl_file) == 0:
               if stack_file is not None and snap_file is not None:
                  snap_img = cv2.imread(snap_file)
                  stack_img = cv2.imread(stack_file)
                  snap_img = cv2.resize(snap_img,(640,360))
                  stack_img = cv2.resize(stack_img,(640,360))
                  tl_frame = cv2.addWeighted(snap_img, 0.8, stack_img, 0.2, 0.0)
                  print("BLEND!")
               elif snap_file is not None:
                  snap_img = cv2.resize(snap_img,(640,360))
                  stack_img = cv2.resize(stack_img,(640,360))
                  tl_frame = snap_img
               elif stack_file is not None:
                  stack_img = cv2.imread(snap_file)
                  stack_img = cv2.imread(stack_file)
                  tl_frame = stack_img

               cv2.imwrite(tl_file, tl_frame)
               print("writing")
            cam_files.append(tl_file)

   cam_files = glob.glob(OUT_DIR + "*" + cams_id + "*.jpg")
   print(OUT_DIR + "*" + cams_id + "*.jpg")
   list = ""
   fc = 0
   for file in sorted(cam_files, reverse=False):
      last_file = cam_files[fc-1]
      if fc+ 1 < len(cam_files):
         next_file = cam_files[fc+1]
      else: 
         next_file = file
      if True:
         list += "file '" + file + "'\n"
         list += "duration " + str(dur) + "\n"
      fc += 1
   list_file = OUT_DIR + "24HOUR_" + STATION_ID + "_" + cam_num + "_list.txt"
   out_file = OUT_DIR + "24HOUR_" + STATION_ID + "_" + cam_num + "_.mp4"
   fp = open(list_file, "w")
   fp.write(list)
   fp.close()

   cmd = "/usr/bin/ffmpeg -r " + str(frate) + " -f concat -safe 0 -i " + list_file + " -c:v libx264 -pix_fmt yuv420p -vf 'scale=" + str(ow) + ":" + str(oh) + "' -y " + out_file 
   os.system(cmd)
   print(list_file)
   print(out_file)


def batch_aurora(json_conf):
   files = glob.glob("au/*.jpg")
   for f in files:
      aur = detect_aurora(f)
      if aur != 0:
         if aur['detected'] == 1:
            print("AURORA DETECTED.")

def aurora_stack_vid(video, json_conf):
   #stack video frames in 
   (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(video)
   date = fy + "_" + fm + "_" + fd
   print("Load frames:", video)
   sd_frames = load_frames_simple(video)
   print("Frames Loaded.")
   AS_DIR = "/mnt/ams2/meteor_archive/" + STATION_ID + "/AURORA/STACKS/" + date + "/" + cam + "/" 
   if cfe(AS_DIR, 1) == 0:
      os.makedirs(AS_DIR)

   #root = video.replace(".mp4", "")
   #rfn, dir = fn_dir(root)
   #done_files = glob.glob(AS_DIR + rfn + "*.jpg")
   #print("CHECK:", AS_DIR + rfn + "*.jpg")
   #if len(done_files) > 5:
   #   print("ALREADY DONE.")
   #   return()

   sd_frames = load_frames_simple(video)
   fc = 0
   vid_fn = video.split("/")[-1]
   stack_fn = vid_fn.replace(".mp4", ".jpg")
   short_frames = []
   stack_lim = 10
   for frame in sd_frames:
      short_frames.append(frame)
      if fc % stack_lim == 0 and fc > 0 and len(short_frames) > 0:
         print("Stacking...")
         stack_image = stack_frames(short_frames)
         short_frames = []
         num = "{:04d}".format(fc)
         tfn = stack_fn.replace(".jpg", "-" + str(num) + ".jpg")
         outfile = AS_DIR + tfn 
         try:
            cv2.imwrite(outfile, stack_image)
            print(outfile)
         except: 
            print("ERROR:")
      fc += 1

def aurora_report(date, json_conf):
   aurora_sd_files = []
   aurora_hd_files = []
   cam_nums = json_conf['cameras'].keys()
   afile = TL_DIR + "VIDS/" + date + "-audit.json"
   ad = load_json_file(afile)
   outdir = TL_DIR + "AURORA/" + date + "/" 
   cache_dir = TL_DIR + "CACHE/" + date + "/"
   ROW_DIR = TL_DIR + "PICS/" + date + "/"
   if cfe(outdir,1) == 0:
      os.makedirs(outdir)
   if cfe(cache_dir,1) == 0:
      os.makedirs(cache_dir)
   list = ""
   html = ""
   row_file = None
   for hour in ad:
      for min in ad[hour]:
         comp = np.zeros((1080,1920,3),dtype=np.uint8)
         hk =  '{:02d}'.format(int(hour))
         mk =  '{:02d}'.format(int(min))
         coutfile = ROW_DIR + hk + "-" + mk + "-row.png"
         for cam_num in cam_nums:
            adata = ad[hour][min][cam_num]
            if "aurora" in adata:
               aud = adata['aurora']
               if "hist_data" in aud:
                  hist = aud['hist_data'] 
                  if hist['r'] > 0 and hist['b'] > 0:
                     rg = hist['g'] / hist['r']
                     bg = hist['g'] / hist['b']
                  else:
                     rg = 0
                     bg = 0
               else:
                  rg = 0
                  bg = 0
               if aud['detected'] == 1 and int(adata['sun'][2]) <= -10:
                  aud['detected'] = 1
               else:
                  aud['detected'] = 0
               if aud['detected'] == 1 :
            
                  row_file = ROW_DIR + "/" + str(hk) + "-" + str(mk) + "-row.png" 
                  if len(adata['sd_file']) > 0:
                     sd_file = adata['sd_file'][0]
                  else:
                     sd_file = ""
                  #if sd_file != "":
                  #   aurora_stack_vid(sd_file, json_conf)
                  if len(adata['hd_file']) > 0:
                     hd_file = adata['hd_file'][0]
                  else:
                     hd_file = ""
                  if sd_file != "":
                     aurora_sd_files.append(sd_file)
                  if hd_file != "":
                     aurora_hd_files.append(hd_file)
                  if len(adata['stack_file']) > 0:
                     row_file = adata['stack_file'][0]
                  elif len(adata['snap_file']) > 0:
                     row_file = adata['snap_file'][0]
                     if "png" in row_file:
                        row_tn = row_file.replace(".png", "-tn.jpg")
                     elif "jpg" in row_file:
                        row_tn = row_file.replace(".jpg", "-tn.jpg")
                     if cfe(row_tn) == 0:
                        im = cv2.imread(row_file)
                        im = cv2.resize(im,(THUMB_W,THUMB_H))
                        cv2.imwrite(row_tn, im)
                     row_file = row_tn
                  if cfe(row_file) == 1:
                     if sd_file != "":
                        html += "<a href=" + sd_file + ">"
                     html += "<img width="  + str(THUMB_W) + "height=" + str(THUMB_H) + " src='" + row_file + "'><br>"
                     if sd_file != "":
                        html += "</a>"
                     perm = aud['perm']
                     area = aud['area']
                     dom_color = aud['dom_color']
                     hist = aud['hist_data']
                     sun = adata['sun']
                     html += hk + ":" + mk + " " + cam_num + " " +  str(perm) + " " + str(area) + " " + str(adata['sun']) + str(rg) + " " + str(bg) + "<br>"
                     if hd_file != "":
                        html += hd_file + "<BR>"
                     #html += sd_file + "<BR>"
                     dur = 1 
                     list += "file '" + coutfile + "'\n"
                     list += "duration " + str(dur) + "\n"
                  else:
                     print("NO ROW!", row_file)
         #print(coutfile)
         #if cfe(coutfile) == 0:
         #   for lcam in layout:
         #      id = "cam" + str(lcam['position'])
         #      print(ad[hour][min])
   #exit()
   print(outdir)
   print(cache_dir)
   list_file = outdir + date + "_AURORA_list.txt" 
   outfile = outdir + date + "_" + STATION_ID + "_AURORA_list.mp4" 
   if cfe(outdir, 1) == 0:
      os.makedirs(outdir)
   fp = open(list_file, "w")
   fp.write(list)
   fp.close()
   html_file = list_file.replace("_list.txt", ".html")
   fp = open(html_file, "w")
   fp.write(html)
   fp.close()
   frate = 25
   if row_file is not None:
      row = cv2.imread(row_file)
      oh, ow = row.shape[:2]

      cmd = "/usr/bin/ffmpeg -r " + str(frate) + " -f concat -safe 0 -i " + list_file + " -c:v libx264 -pix_fmt yuv420p -vf 'scale=" + str(ow) + ":" + str(oh) + "' -y " + outfile 
      #os.system(("rm -rf " + dir))
   else:
      print("No aurora detected....")
      fn, dir = fn_dir(outfile)
      os.system(("rm -rf " + dir))
      return()
   #os.system(cmd)
   print(outfile)
   print(list_file)
   print(html_file)
   all_list = ""
   for cam_num in json_conf['cameras']:
      cams_id = json_conf['cameras'][cam_num]['cams_id']
      cmd = "./Process.py tl_list /mnt/ams2/meteor_archive/" + STATION_ID + "/TL/AURORA/STACKS/" + date + "/ " + cams_id + " 25"
      #os.system(cmd)
      print(cmd)
      coutfile = "/mnt/ams2/meteor_archive/" + STATION_ID + "/TL/AURORA/STACKS/" + date + "/" + cams_id + ".mp4"
      if cfe(coutfile) == 1:
         all_list += "file '" + coutfile + "'\n"
   out_dir = "/mnt/ams2/meteor_archive/" + STATION_ID + "/TL/AURORA/VIDS/" 
   if cfe(out_dir, 1) == 0:
      os.makedirs(out_dir)
   out_file = out_dir + "AURORA_" + STATION_ID + "_" + date + ".mp4"
   list_file = out_dir + "AURORA_" + STATION_ID + "_" + date + ".txt"
   fp = open(list_file, "w")
   fp.write(all_list)
   fp.close()
   ow = 640
   oh = 360
   cmd = "/usr/bin/ffmpeg -re -f concat -safe 0 -i " + list_file + " -y " + out_file
   print(cmd)
   #os.system(cmd)
   of2 = out_file.replace(".mp4", "-2.mp4")
   cmd = "/usr/bin/ffmpeg -i " + out_file + " -vf scale=" + str(ow) + ":" + str(oh) + " -aspect:v 640:360 -y " + of2 
   print(cmd)
   #os.system(cmd)
   print(out_file)
   #os.system("mv " + of2 + " " + out_file)
   print("AU FILES SD:", sorted(aurora_sd_files))
   print("AU FILES HD:", sorted(aurora_hd_files))
   # find the range for the aurora storm and copy all SD and HD files that fall into that range
   # for longer term backup (so they don't get auro deleted)
   AU_SRC_DIR = "/mnt/ams2/meteor_archive/" + STATION_ID + "/AURORA/SRC/"
   min_file =  sorted(aurora_sd_files)[0]
   max_file =  sorted(aurora_sd_files)[-1]
   print("AU FILES SD:", sorted(aurora_sd_files))
   print("AU FILES HD:", sorted(aurora_hd_files))
   (min_datetime, cam, f_date_str,fy,fm,fd, min_h, fmin, fs) = convert_filename_to_date_cam(min_file)
   (max_datetime, cam, f_date_str,fy,fm,fd, max_h, fmin, fs) = convert_filename_to_date_cam(max_file)
   sd_dir = "/mnt/ams2/SD/proc2/" + fy + "_" + fm + "_" + fd + "/"
   hd_dir = "/mnt/ams2/HD/"
   AU_HD_DIR = AU_SRC_DIR + "HD/" + date + "/" 
   AU_SD_DIR = AU_SRC_DIR + "SD/" + date + "/" 
   sd_files = glob.glob(sd_dir + "*.mp4")
   hd_files = glob.glob(hd_dir + fy + "_" + fd + "_" + fm + "*.mp4")


   print ("LOAD:", sd_dir + "*.mp4")
   min_h = int(min_h)
   max_h = int(max_h)
   if cfe(AU_SD_DIR, 1) == 0:
      os.makedirs(AU_SD_DIR)
   if cfe(AU_HD_DIR, 1) == 0:
      os.makedirs(AU_HD_DIR)

   sd_stack_dir = "/mnt/ams2/meteor_archive/" + STATION_ID + "/AURORA/STACKS/" + date + "/" 
   temp = glob.glob(sd_stack_dir + "*.jpg")
   print(sd_stack_dir + "*.jpg")
   sd_need_stack = []
   sd_stack_roots = {}
   for t in temp:
      fn, dir = fn_dir(t)
      root = fn.split("-")[0]
      print("ROOT:", root)
      sd_stack_roots[root] = 1

   for sdf in sorted(sd_files):
      if "trim" not in sdf:
         (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(sdf)
         if int(min_h) <= int(fh) <= int(max_h):
            fn, dir = fn_dir(sdf)
            root = fn.split("-")[0]
            root = root.replace(".mp4", "")
            if root in sd_stack_roots:
               print("SD FILE ALREADY STACKED.")
            else:
               print("SD FILE NEEDS TO BE STACKED.", root)
               sd_need_stack.append(sdf)

            save_file = AU_SD_DIR + fn
            if cfe(save_file) == 0:
               print(min_h, fh, max_h, sdf)
               print("SAVE FILE:", sdf, AU_SD_DIR)
               cmd = "cp " + sdf + " " + AU_SD_DIR
               print(cmd)
               os.system(cmd)

   for sdf in sorted(hd_files):
      if "trim" not in sdf:
         (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(sdf)
         if int(min_h) <= int(fh) <= int(max_h):
            fn,dir = fn_dir(sdf)
            save_file = AU_HD_DIR + fn
            if cfe(save_file) == 0:
               print(min_h, fh, max_h, sdf)
               print("SAVE HD FILE:", sdf, AU_HD_DIR)
               cmd = "cp " + sdf + " " + AU_HD_DIR
               print(cmd)
               os.system(cmd)
      
   for file in sd_need_stack:
      print("STACK:", file)
      aurora_stack_vid(file, json_conf)

def detect_aurora(img_file=None):
   print("DA:", img_file)
#   img_file = "aurora.jpg"
   max_rg = 0
   max_bg = 0
   best_quad = ""
   detect = 0
   img = cv2.imread(img_file)
   try:
      w,h = img.shape[:2]
   except:
      print("Bad image.", img_file)
      return(0)
   #cv2.imshow('pepe', img)
   #cv2.waitKey(0)
   matched = color_thresh_new(img, (60,80,70), (200,250,200))
   #cv2.imshow('pepe', matched)
   #cv2.waitKey(0)

   (hist_img, dom_color, hist_data) = histogram(img)
   
   if hist_data['r'] > 0:
      rg = hist_data['g'] / hist_data['r']
      bg = hist_data['g'] / hist_data['b']
   else:
      rg = 0
      bg = 0
   print("RG ALL:", rg, bg)
   # check 4 quads of image
   x1 = 0
   x2 = int(img.shape[1] / 2)
   y1 = 0
   y2 = int(img.shape[0] / 2)
   (hist_img, dom_color, hist_data) = histogram(img[y1:y2,x1:x2])
   if hist_data['r'] > 0:
      rg = hist_data['g'] / hist_data['r']
      bg = hist_data['g'] / hist_data['b']
   else:
      rg = 0
      bg = 0
   print("RG TL:", rg, bg)
   if rg > max_rg and bg > max_bg:
      max_rg = rg
      max_bg = bg
      best_quad = "TL"

   x1 = int(img.shape[1] / 2)
   x2 = img.shape[1]
   y1 = 0
   y2 = int(img.shape[0] / 2)
   (hist_img, dom_color, hist_data) = histogram(img[y1:y2,x1:x2])
   if hist_data['r'] > 0:
      rg = hist_data['g'] / hist_data['r']
      bg = hist_data['g'] / hist_data['b']
   else:
      rg = 0
      bg = 0
   print("RG TR:", rg, bg)
   if rg > max_rg and bg > max_bg:
      max_rg = rg
      max_bg = bg
      best_quad = "TR"

   x1 = int(img.shape[1] / 2)
   x2 = img.shape[1]
   y1 = int(img.shape[0] / 2)
   y2 = img.shape[0]
   (hist_img, dom_color, hist_data) = histogram(img[y1:y2,x1:x2])
   if hist_data['r'] > 0:
      rg = hist_data['g'] / hist_data['r']
      bg = hist_data['g'] / hist_data['b']
   else:
      rg = 0
      bg = 0
   print("RG BR:", rg, bg)
   if rg > max_rg and bg > max_bg:
      max_rg = rg
      max_bg = bg
      best_quad = "BR"

   x1 = 0
   x2 = int(img.shape[1] / 2)
   y1 = int(img.shape[0] / 2)
   y2 = img.shape[1]

   (hist_img, dom_color, hist_data) = histogram(img[y1:y2,x1:x2])
   if hist_data['r'] > 0:
      rg = hist_data['g'] / hist_data['r']
      bg = hist_data['g'] / hist_data['b']
   else:
      rg = 0
      bg = 0
   print("RG BL:", rg, bg)
   if rg > max_rg and bg > max_bg:
      max_rg = rg
      max_bg = bg
      best_quad = "BL"


   #cv2.imshow('pepe', hist_img)
   #cv2.waitKey(0)
   cnt_res = cv2.findContours(matched, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
   if len(cnt_res) == 3:
      (_, cnts, xx) = cnt_res
   elif len(cnt_res) == 2:
      (cnts, xx) = cnt_res
   aprox = []
   detected = 0
   perimeter = 0,
   for cnt in cnts:
      max_area = cv2.contourArea(cnt)

      perimeter = cv2.arcLength(cnt,True)
      epsilon = 0.01*cv2.arcLength(cnt,True)
      approx = cv2.approxPolyDP(cnt,epsilon,True)
      if max_area > 100:
         cv2.drawContours(img, [approx], -1, (0, 0, 255), 3)
         aprox.append(approx.tolist())
         print(dom_color, rg, bg)
         if dom_color == 'g' and (max_rg > 1.2 or max_bg > 1.2):
            detected = 1
            print("DETECTED!")
         try:
            perimeter = float(perimeter)
         except:
            perimeter = 0
         print("PERM/AREA:", perimeter, max_area) 

   if detected == 1 or (max_bg > 1.1 and max_rg > 1.1):
      try:
         perimeter = float(perimeter)
      except:
         perimeter = 0
      try:
         max_area = float(max_area)
      except:
         max_area = 0
      detected = 1
      #cv2.imshow('pepe', img)
      #cv2.waitKey(30)
      print("PERM:", perimeter)
      aur = {
         "detected": detected,
         "approx": aprox,
         "perm": float(perimeter),
         "area": float(max_area),
         "dom_color": dom_color,
         "max_rg": max_rg,
         "max_bg": max_bg,
         "best_quad": best_quad,
         "hist_data": hist_data
      }
      print("AU DETECTED.", max_rg, max_bg, perimeter, max_area)
   else:
      aur = {
         "detected": 0,
         "hist_data": hist_data
      }
      print("AU NOT DETECTED.", detected, max_rg, max_bg, best_quad)
   return(aur, hist_img,img)


def color_thresh_new(image, low=[60,0,0], high=[255,200,200]):
   gsize = 100
   try:
      height,width = image.shape[:2]
   except:
      return([])

   low_color_bound = np.array(low ,  dtype=np.uint8, ndmin=1)
   high_color_bound = np.array(high ,  dtype=np.uint8, ndmin=1)
   matched = cv2.inRange(image,low_color_bound, high_color_bound)
   return(matched)



def solar_info(date, json_conf):
   solar_hours = {}
   for i in range(0,24):
      date = date.replace("_", "/")
      date = date.replace("-", "/")
      f_date_str = date + ' {:02d}:{:02d}:00'.format(i,0) 
      sun_status, sun_az, sun_el = day_or_night(f_date_str, json_conf,1)
      solar_hours[i] = [sun_status, sun_az, sun_el]
      print(f_date_str, sun_status, sun_az, sun_el)
   return(solar_hours)

def multi_audit_tl(date, json_conf, outsize, outdir, frate, snaps_per_second):
   for cam_num in range(1, len(json_conf['cameras'].keys()) + 1):
      audit_tl(date, json_conf, str(cam_num),outsize, outdir, frate, snaps_per_second)

def multi_cam_audit_tl(date, json_conf, outsize, outdir, frate, snaps_per_second):
   ow, oh = outsize
   layout = layout_template(json_conf)
   snaps_per_second = int(snaps_per_second)
   frate = int(frate)
   dx_frames = int(frate / snaps_per_second)
   print(layout)
   afile = TL_DIR + "VIDS/" + date + "-audit.json"
   ad = load_json_file(afile)
   cache_dir = outdir + "CACHE/" + date + "/"
   if cfe(cache_dir, 1) == 0:
      os.makedirs(cache_dir)
   #os.system("rm " + cache_dir + "*")

   list = ""
   for hour in ad:
      for min in ad[hour]:
         comp = np.zeros((1080,1920,3),dtype=np.uint8)
         hk =  '{:02d}'.format(int(hour))
         mk =  '{:02d}'.format(int(min))
         coutfile = cache_dir + hk + "-" + mk + ".jpg"
         if cfe(coutfile) == 0:
            for lcam in layout:
               id = "cam" + str(lcam['position'])
               print(ad[hour][min])
               x1 = lcam['x1']
               y1 = lcam['y1']
               x2 = lcam['x2']
               y2 = lcam['y2']
               #   lcam = "cam" + str(id)
               dw, dh = lcam['dim']

               if len(ad[hour][min][id]['snap_file']) > 0:
                  snap_file = ad[hour][min][id]['snap_file'][0] 
                  if cfe(snap_file) == 1:
                     try:
                        snap = cv2.imread(snap_file)
                     except:
                        snap = np.zeros((dh,dw,3),dtype=np.uint8)
                  else: 
                     snap = np.zeros((dh,dw,3),dtype=np.uint8)
                  try:
                     snap = cv2.resize(snap,(dw,dh))
                  except:
                     snap = np.zeros((dh,dw,3),dtype=np.uint8)
                  print(hour, min, snap_file)
               else:
                  snap = np.zeros((dh,dw,3),dtype=np.uint8)
               comp[y1:y2,x1:x2] = snap
         else:
            comp = cv2.imread(coutfile)
         dur = .04 * dx_frames
         list += "file '" + coutfile + "'\n"
         list += "duration " + str(dur) + "\n"
         cv2.imwrite(coutfile, comp)
         #show = cv2.resize(comp,(1280,720))
         #cv2.imshow('pepe',show)
         #cv2.waitKey(30)
   fp = open(cache_dir + "list.txt", "w")
   fp.write(list)
   fp.close()               
   outfile = outdir + STATION_ID + "_" + date + "_multi.mp4"
   cmd = "/usr/bin/ffmpeg -r " + str(frate) + " -f concat -safe 0 -i " + cache_dir + "list.txt -c:v libx264 -pix_fmt yuv420p -vf 'scale=" + ow + ":" + oh + "' " + outfile 
   os.system(cmd)
   print(outfile)

def audit_tl(date, json_conf, tcam=None,outsize=None, outdir=None, frate=None, snaps_per_second=None):
   mc = input("Select Command: 1) Make 1 video for 1 cam 2) Make Multi-cam-video 3) Join 2 days together")
   if outsize is None: 
      tcam = input("Enter CAMS ID (1-7) or A for multi-cam video: ")
      outsize = input("Output size: 1080, 720, 360: [360] ")
      outdir = input("Output dir: starting with [/mnt/ams2/TL]: ")
      frate = input("TL Frame Rate FPS (1-25):[25] ")
      snaps_per_second = input("TL Snaps per second (relates to FPS) should be (1-25), but doesn't have to match FPS: ")

   if tcam == "":
      tcam = "1"
   if outsize == "":
      outsize = "360"
   if snaps_per_second == "":
      snaps_per_second = 2
   if outsize == "":
      outsize = "360"
   if outdir == "":
      outdir = "/mnt/ams2/TL/"
   if frate == "":
      frate = int(25)
   if outsize == "1080":
      ow = "1920"
      oh = "1080"
   if outsize == "720":
      ow = "1280"
      oh = "720"
   if outsize == "360":
      ow = "640"
      oh = "360"
   if outsize == "180":
      ow = "320"
      oh = "180"
   if tcam == "A" or tcam == "a":
      multi_audit_tl(date, json_conf, outsize, outdir, frate, snaps_per_second)
      exit()
      #multi_audit_tl(date, json_conf, )
      #exit()
   snaps_per_second = int(snaps_per_second)
   frate = int(frate)
   dx_frames = int(frate / snaps_per_second)

   if mc == "2":
      multi_cam_audit_tl(date, json_conf, (ow,oh), outdir, frate, snaps_per_second)
      exit()

   if dx_frames == 0:
      dx_frames = 2 

   tcam = "cam" + tcam
   TL_DIR = "/mnt/ams2/meteor_archive/" + STATION_ID + "/TL/"
   ROW_DIR = TL_DIR + "PICS/"
   afile = TL_DIR + "VIDS/" + date + "-audit.json"
   ad = load_json_file(afile)
   list = ""
   for hour in ad:
      for min in ad[hour]:
         hk =  '{:02d}'.format(int(hour))
         mk =  '{:02d}'.format(int(min))
         #print(cam , ad[hour][min][tcam])
         #for cam in ad[hour][min]:
         row_file = ROW_DIR + date + "/" + str(hk) + "-" + str(mk) + "-row.png" 
         if cfe(row_file) == 0:
            print("NO ROW:", row_file)
            #exit()
         print(hour, min, tcam , ad[hour][min][tcam]['snap_file'])
         dur = .04 * dx_frames
         if len(ad[hour][min][tcam]['snap_file']) > 0:
            list += "file '" + ad[hour][min][tcam]['snap_file'][0] + "'\n"
            list += "duration " + str(dur) + "\n"
   if cfe(outdir,1) == 0:
      os.makedirs(outdir)
   fp = open(outdir + "list.txt", "w")
   fp.write(list)
   fp.close()               
   outfile = outdir + STATION_ID + "_" + date + "_" + tcam + ".mp4"
   cmd = "/usr/bin/ffmpeg -r " + str(frate) + " -f concat -safe 0 -i " + outdir + "list.txt -c:v libx264 -pix_fmt yuv420p -vf 'scale=" + ow + ":" + oh + "' " + outfile 
   os.system(cmd)
   print(cmd)
            

def nexrad_time(nrf):
   fn, dir = fn_dir(nrf)
   el = fn.split("_")
   day, time = el[0], el[1]
   station = day[0:4]
   day = day.replace(station, "")
   year = day[0:4]
   mon = day[4:6]
   dom = day[6:8]
   h = time[0:2]
   m = time[2:4]
   s = time[4:6]
   time_str = year + "_" + mon + "_" + dom + "_" + h + "_" + m + "_" + s
   f_datetime = datetime.datetime.strptime(time_str, "%Y_%m_%d_%H_%M_%S") 
   return(time_str, f_datetime)

def make_file_matrix(day, files, nr_files):
   file_matrix = {}
   sec_bin = [0,30]
   for hour in range (0, 24):
      file_matrix[hour] = {}
      for min in range(0,60):
         file_matrix[hour][min] = {}
         for sec in sec_bin: 
            file_matrix[hour][min][sec] = {}
            file_matrix[hour][min][sec]['radar_file'] = []
            file_matrix[hour][min][sec]['cam_images'] = []

   for hour in file_matrix:
      for min in file_matrix[hour]:
         for sec in file_matrix[hour][min]:
            print(hour, min, sec, file_matrix[hour][min][sec])
            find_nr_file(day,hour,min,sec, nr_files)

   return(file_matrix)

def find_nr_file(day,hour,min,sec, nr_files):
  nrf = []
  f_date_str = day + "_" + str(hour) + "_" + str(min) + "_" + str(sec)
  f_dt = datetime.datetime.strptime(f_date_str, "%Y_%m_%d_%H_%M_%S") 
  for nf in nr_files :
     print("NF:", nf )
     nr_time_str, nr_dt = nexrad_time(nf)
     elapsed = (f_dt - nr_dt).total_seconds()
     nrf.append((nf, elapsed))
  elp_sort = sorted(nrf, key=lambda x: x[1], reverse=False)[0:25]
  print("NR:", elp_sort)
  exit()

def load_nexrad_files(day, files):
   NEXRAD_STATION = "KLWX"
   NEXRAD_DIR = "/mnt/archive.allsky.tv/NEXRAD/IMAGES/" + day + "/" 
   nr_files = []
   print( NEXRAD_DIR + NEXRAD_STATION + "*.png")
   nrfiles = glob.glob(NEXRAD_DIR + NEXRAD_STATION + "*.png")
   for nfile in nrfiles:
      nr_time = nexrad_time(nfile)
      nr_files.append(nfile)
   file_matrix = make_file_matrix(day, files, nr_files)

def extract_night_images(cam, day):
   global TL_IMAGE_DIR
   night_files = []
   night_images = []
   NIGHT_VID_DIR = "/mnt/ams2/SD/proc2/" + day + "/"
   NIGHT_IMG_DIR = "/mnt/ams2/SD/proc2/" + day + "/images/"
   temp_files = glob.glob(NIGHT_VID_DIR + "*" + cam + "*.mp4")
   for tf in temp_files:
      if "trim" not in tf and "crop" not in tf:
         night_files.append(tf)
   temp_files = extract_images(night_files)
   for nfile in night_files:
      fn, vdir = fn_dir(nfile )
      stack_file = vdir + "/images/" + fn
      stack_file = stack_file.replace(".mp4", "-stacked-tn.png")
      if cfe(stack_file) == 0:
         stack_file = stack_file.replace(".png", "jpg")
 
      
      vidfile = NIGHT_VID_DIR + fn
      night_images.append(vidfile)

   return(night_images)

   

def extract_images(files, outdir=None):

   global TL_IMAGE_DIR
   global TL_VIDEO_DIR
   if outdir is not None:
      TL_IMAGE_DIR = outdir
   fn, dir = fn_dir(files[0])
   day = fn[0:10]

   TL_IMAGE_DIR =  TL_IMAGE_DIR + day + "/"
   TL_VIDEO_DIR =  TL_VIDEO_DIR + day + "/"
   all_files = []
   if cfe(TL_IMAGE_DIR, 1) == 0:
      os.makedirs(TL_IMAGE_DIR)
   for file in sorted(files): 
      (f_datetime, cam, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(file)
      fs = int(fs)
      if fs > 30:
         # seconds to 60
         sec_to_60 = 60 - fs  
         sec_to_30 = 90 - fs  
      elif fs < 30:
         sec_to_60 = 60 - fs  
         sec_to_30 = 30 - fs  
      frame_to_60 = int(sec_to_60 * 25)
      frame_to_30 = int(sec_to_30 * 25)
      date_next_60 = f_datetime + datetime.timedelta(seconds=sec_to_60)
      date_next_30 = f_datetime + datetime.timedelta(seconds=sec_to_30)

      print(f_datetime, sec_to_60, sec_to_30 , date_next_60, date_next_30, frame_to_60, frame_to_30)
      if outdir is None:
         outfile = TL_IMAGE_DIR + date_next_60.strftime("%Y_%m_%d_%H_%M_%S_000_") + cam + ".jpg"
      else:
         outfile = outdir + date_next_60.strftime("%Y_%m_%d_%H_%M_%S_000_") + cam + ".jpg"
      if cfe(outfile) == 0:
         cmd = """ /usr/bin/ffmpeg -i """ + file + """ -vf select="between(n\,""" + str(frame_to_60) + """\,""" + str(frame_to_60+1) + """),setpts=PTS-STARTPTS" -y -update 1 """ + outfile + " >/dev/null 2>&1"
         print(cmd)
         os.system(cmd)
      if cfe(outfile) == 1:
         all_files.append(outfile)

      if outdir is None:
         outfile = TL_IMAGE_DIR + date_next_30.strftime("%Y_%m_%d_%H_%M_%S_000_") + cam + ".png"
      else:
         outfile = outdir + date_next_60.strftime("%Y_%m_%d_%H_%M_%S_000_") + cam + ".jpg"

      if cfe(outfile) == 0:
         cmd = """ /usr/bin/ffmpeg -i """ + file + """ -vf select="between(n\,""" + str(frame_to_30) + """\,""" + str(frame_to_30+1) + """),setpts=PTS-STARTPTS" -y -update 1 """ + outfile + " >/dev/null 2>&1"
         print(cmd)
         os.system(cmd)
      if cfe(outfile) == 1:
         all_files.append(outfile)
   return(all_files)

def min_shift(this_image, last_image, area):
   x1,y1,x2,y2 = area
   poly = np.zeros(shape=(2,), dtype=np.float64)
   #poly[0] = .0001
   #poly[1] = .0001
   res = scipy.optimize.minimize(reduce_shift, poly, args=(this_image,last_image,area), method='Nelder-Mead')
   new_poly = res['x']
   print("NEW POLY:", new_poly)
   shift_x = int(((y1*x1)**2)*new_poly[0])
   shift_y = int(((y1*x1)**2)*new_poly[1])


   print("SHIFT_X Y:", shift_x, shift_y)

def composite(images, labels, text_desc):
   cw = 1920
   ch = 1080 
   comp = np.zeros((ch,cw,3),dtype=np.uint8)
   nx = 0
   ny = 0
   method = 2

   ic = 0
   for image in images:
      if ic == 0:
         images[ic] = cv2.resize(images[ic],(1280,720))
      else:
         if len(image.shape) == 2:
            images[ic] = cv2.cvtColor(image,cv2.COLOR_GRAY2BGR)
         images[ic] = cv2.resize(images[ic],(640,360))
      ic += 1

   if method == 1:
      for image in images:
         if image.shape[0] != 360:
            image = cv2.resize(image, (640, 360))
         print("NX,NY", nx,ny)
         if len(image.shape) == 2:
            image = cv2.cvtColor(image,cv2.COLOR_GRAY2BGR)

         h,w = image.shape[:2]
         if nx + w <= cw:
            comp[ny:ny+h,nx:nx+w] = image
         else:
            nx = 0
            nx1 = 0
            nx2 = nx1 + w
            ny1 = ny + h
            ny2 = ny + h + h
            print("NX,NY", nx1,nx2, ny1,ny2)
            print("NEW SHAPE:", ny2-ny1, nx2-nx1)
            print("IMAGE SHAPE:", image.shape)
            comp[ny1:ny2,nx1:nx2] = image
            ny = ny + h
         nx = nx + w
   if method == 2:
      comp[360:1080,0:1280] = images[0]
      comp[0:360,0:640] = images[1]
      comp[0:360,640:1280] = images[2]
      comp[0:360,1280:1920] = images[3]
      comp[360:720,1280:1920] = images[4]
      comp[720:1080,1280:1920] = images[5]
      cv2.putText(comp, str(labels[0]),  (15,1055), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1) 
      cv2.putText(comp, str(labels[1]),  (15,345), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1) 
      cv2.putText(comp, str(labels[2]),  (655,345), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1) 
      cv2.putText(comp, str(labels[3]),  (1280+15,345), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1) 
      cv2.putText(comp, str(labels[4]),  (1280+15,345+360), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1) 
      cv2.putText(comp, str(labels[5]),  (1280+15,345+720), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1) 
      cv2.putText(comp, str(text_desc),  (15,1075), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1) 

   return(comp)

def reduce_shift(poly, this_image, last_image,area):
   x1,y1,x2,y2 = area
   this_area = this_image[y1:y2,x1:x2] 
   shift_x = int(((y1*x1)**2)*poly[0])
   shift_y = int(((y1*x1)**2)*poly[1])

   if abs(shift_x) > 100 or abs(shift_y) > 100:
      return(99999999999)

   lx1 = x1 + shift_x
   ly1 = y1 + shift_y
   lx2 = x2 + shift_x
   ly2 = y2 + shift_y

   if lx1 < 0 :
      return(9999999999999)
   if ly1 < 0 :
      return(9999999999999)
   if lx2 > this_image.shape[1]:
      return(9999999999999)
   if ly2 > this_image.shape[0]:
      return(9999999999999)

   #print("SHIFT", shift_x,shift_y)
   #print("AREA", x1,y1,x2,y2)
   #print("LA", lx1,ly1,lx2,ly2)

   last_area = last_image[ly1:ly2,lx1:lx2] 
   area_diff = cv2.subtract(this_area, last_area)
   show_img = this_image.copy()
 
   cv2.rectangle(show_img, (int(x1), int(y1)), (int(x2) , int(y2) ), (255, 255, 255), 1)
   cv2.rectangle(show_img, (int(lx1), int(ly1)), (int(lx2) , int(ly2) ), (150, 150, 150), 1)
   #cv2.imshow('reduce full', show_img)
   
   #cv2.imshow('reduce', this_area)
   #cv2.waitKey(0)
   #cv2.imshow('reduce', last_area)
   #cv2.waitKey(0)
   #cv2.imshow('reduce', area_diff)
   #cv2.waitKey(0)
   area_val = np.sum(area_diff)
   print("VAL:", shift_x, shift_y, area_val)
   return(area_val + ((shift_x**2) + (shift_y**2)))


def fill_mask(img):
   for col in range(0,img.shape[1]-1):
      for row in range(0,img.shape[0]-1):
         val = img[row,col]
         if val > 10:
            # block out rest of col 
            print("BLOCK:", col, row, val)
            img[row:img.shape[0],col] = 250
            #cv2.imshow('FILL MASK', img)
            #cv2.waitKey(0)
            break 
   return(img)

def sum_hist(data):
   sum = 0
   for i in range(0,len(data)-1):
      sum = sum + (i*data[i])
   return(sum)
   

def histogram(image):
   #fig = plt.figure()

   try:
      height,width = image.shape[:2]
   except:
      dom_color = 'n'
      hist_data = {'r': 0, 'g': 0, 'b': 0}
      return(image, dom_color, hist_data)
   color = ('b', 'g', 'r')
   hist_data = {}
   dom_val = 0
   for i,col in enumerate(color):

      histr = cv2.calcHist([image],[i],None,[256],[1,256])
      hist_data[col] = int(sum_hist(histr))
      if hist_data[col] > dom_val:
         dom_val = hist_data[col]
         dom_color = col
   #   plt.plot(histr,color = col)
   #   plt.xlim([0,256])
   #fig.canvas.draw()
   #img = np.fromstring(fig.canvas.tostring_rgb(), dtype=np.uint8, sep='')
   #img  = img.reshape(fig.canvas.get_width_height()[::-1] + (3,))

   # img is rgb, convert to opencv's default bgr
   #img = cv2.cvtColor(img,cv2.COLOR_RGB2BGR)

   img = None 

   # blue as % of green and red
   if hist_data['b'] > 0:
      green_blue_perc = hist_data['g'] / hist_data['b']
      red_blue_perc = hist_data['r'] / hist_data['b']
   else:
      green_blue_perc = 0
      red_blue_perc = 0
      dom_color = 'n'

   text1 = "DOM COLOR: " + dom_color
   text2 = "Green/Blue Perc: " +  str(green_blue_perc)[0:4]
   text3 = "Red/Blue Perc:" + str(red_blue_perc)[0:4]

   
   #cv2.putText(img, str(text1),  (40,10), cv2.FONT_HERSHEY_SIMPLEX, .4, (0, 0, 0), 1) 
   #cv2.putText(img, str(text2),  (40,30), cv2.FONT_HERSHEY_SIMPLEX, .4, (0, 0, 0), 1) 
   #cv2.putText(img, str(text3),  (40,50), cv2.FONT_HERSHEY_SIMPLEX, .4, (0, 0, 0), 1) 

   return(img, dom_color, hist_data)
   #plt.show()

def gradient(image):
   lap_img = cv2.Laplacian(image,cv2.CV_64F)
   #cv2.imshow("Gradient", lap_img)
   #cv2.waitKey(0)

def make_flat(cam,day,json_conf):
   print("Make flat:", cam, day)
   if cfe(MASK_DIR, 1) == 0:
      os.makedirs(MASK_DIR)
   mask_file = MASK_DIR + cam + "_mask.png"
   flat_file = MASK_DIR + cam + "_flat.png"

   if day is None: 
      date = datetime.datetime.now().strftime("%Y_%m_%d")
   else:
      date = day
   #if cfe(mask_file) == 0:
   if True:
      wild = "/mnt/ams2/SD/proc2/daytime/" + date + "/*" + cam + "*.mp4" 
      nwild = "/mnt/ams2/SD/proc2/" + date + "*" + cam + "*.jpg" 
      nstack_wild = "/mnt/ams2/SD/proc2/" + date + "/images/*" + cam + "*.jpg" 
      print(wild)
      files = glob.glob(wild)
      nfiles = glob.glob(nwild)
      nstacks = glob.glob(nstack_wild)
      for file in nfiles:
         files.append(file)
      if len(files) == 0:
         print("No files for this day", wild)
         return(None, None)
      med_frames = []
      mask_frames = []
      night_mask_frames = []
      fc = 0
      for file in sorted(files):
         if "trim" in file or "crop" in file :
            continue
         (f_datetime, cam, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(file)
         sun_status, sun_az, sun_el = day_or_night(f_date_str, json_conf,1)

         if -10 <= int(sun_el) <= 0:

            frames,color_frames,subframes,sum_vals,max_vals,pos_vals = load_frames_fast(file, json_conf, 1, 1, [], 1,[])
            med_frames.append(color_frames[0])
         if -5 <= int(sun_el) <= 0:
            print("MASK FRAMES:", file)
            frames,color_frames,subframes,sum_vals,max_vals,pos_vals = load_frames_fast(file, json_conf, 1, 1, [], 1,[])
            mask = color_thresh(color_frames[0]) 

            mask_frames.append(mask)

      night_images = []
      for file in sorted(nstacks):
         if "trim" in file or "crop" in file :
            continue
         (f_datetime, cam, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(file)
         sun_status, sun_az, sun_el = day_or_night(f_date_str, json_conf,1)
         if int(sun_el) < -10:
            img = cv2.imread(file)
            night_images.append(img)
      
      median_night = cv2.convertScaleAbs(np.median(np.array(night_images), axis=0))

      med_show = cv2.resize(median_night, (1280,720))
      med_show_gray = cv2.cvtColor(med_show, cv2.COLOR_BGR2GRAY)
      _, thresh= cv2.threshold(med_show_gray, 80, 255, cv2.THRESH_BINARY)
      thresh_dil = cv2.dilate(thresh.copy(), None , iterations=8)
      cnts = get_contours(thresh_dil)
      cv2.imwrite("/mnt/ams2/test.jpg", thresh_dil) 



      print("MASK FRAMES:", len(mask_frames), len(med_frames))
      if len(mask_frames) == 0:
         print("No good frames selected...")
         return(None, None)
      for frame in mask_frames:
         print(frame.shape)
      print("MASK FRAMES:", len(mask_frames))
      median_mask = cv2.convertScaleAbs(np.median(np.array(mask_frames), axis=0))
      median_flat = cv2.convertScaleAbs(np.median(np.array(med_frames), axis=0))
      median_mask = cv2.GaussianBlur(median_mask, (15, 15), 0)
      median_mask = cv2.dilate(median_mask.copy(), None , iterations=4)
      median_mask = fill_mask(median_mask)

      omh, omw = median_mask.shape[:2]

      median_mask = cv2.resize(median_mask, (1280,720))
      for x,y,w,h in cnts:
         print("ADDING EXTRA AREAS TO MASK", x,y,w,h)
         median_mask[y:y+w,x:x+w] = 255
      median_mask = cv2.resize(median_mask, (omw,omh))

      cv2.imwrite(mask_file, median_mask)
      cv2.imwrite(flat_file, median_flat)
      print(mask_file)
   else:
      print("LOADING:", mask_file)
      median_mask = cv2.imread(mask_file)
      median_flat = cv2.imread(flat_file)

   #cv2.imshow('MASK', median_mask)
   #cv2.imshow('FLAT', median_flat)
   #cv2.waitKey(0)
   return(median_mask, median_flat)


def track_clouds(cam, day, json_conf):
   use_snaps = 0
   SNAP_DIR = "/mnt/ams2/SNAPS/" 
   if day is None: 
      date = datetime.now().strftime("%Y_%m_%d")
   else:
      date = day
   files = []

   # load radar files

   color_mask, color_flat = make_flat(cam,day,json_conf)
   gray_mask = cv2.cvtColor(color_mask, cv2.COLOR_BGR2GRAY)
   gray_flat = cv2.cvtColor(color_flat, cv2.COLOR_BGR2GRAY)
   if use_snaps == 1:
      color_mask = cv2.resize(color_mask, (1920,1080))
      color_flat = cv2.resize(color_flat, (1920,1080))
      gray_mask = cv2.resize(gray_mask, (1920,1080))
      gray_flat = cv2.resize(gray_flat, (1920,1080))

   wild = "/mnt/ams2/SD/proc2/daytime/" + date + "/*" + cam + "*.mp4" 
 
   gray_med   = gray_flat
   print(wild)

   if use_snaps == 0:
      print(wild)
      files = glob.glob(wild)
      night_files = extract_night_images(cam, day)
      for nf in night_files:
         print("NIGHT FILES:", nf)
         files.append(nf) 
      files = extract_images(files)
   else:
      files = glob.glob(SNAP_DIR + day + "/*" + cam + "*1920x1080.jpg")

   #nrfiles = load_nexrad_files(day,files)
   exit()




   first_img = cv2.imread(files[0])
   frame_h, frame_w = first_img.shape[:2]

   # GET AZ GRID FOR THIS CAMERA
   cal_file = files[0]
   cal_files= get_cal_files(cal_file)
   print("CAL FILES:", cal_files)
   print("CAL FILE:", cal_file)
   if len(cal_files) > 0:
      cal_file = cal_files[0][0]
      fn, dir = fn_dir(cal_file)
      grid_glob = dir + "*azgrid.png"
      print(grid_glob)
      grid_files = glob.glob(grid_glob)
      if len(grid_files) > 0:
         grid_file = grid_files[0]
         grid_img = cv2.imread(grid_file)
         grid_img= cv2.resize(grid_img, (first_img.shape[1], first_img.shape[0]))


         #cv2.imshow('grid', grid_img)
         #cv2.waitKey()

   else:
      print("NO CAL FILES?")


   acc_frames = []
   image_acc = None
   all_frames = []
   last_sub = None
   id_thresh = None
   last_thresh = None


   for file in sorted(files):
      cnt_groups = []
      print("FILE:", file)
      (f_datetime, cam, f_date_str,fy,fmon,fd, fh, fm, fs) = convert_filename_to_date_cam(file)
      stack_wild = fy + "_" + fmon + "_" + fd + "_" + fh + "_" + fm + "*" + "_000_" + cam + "*"
      sun_status, sun_az, sun_el = day_or_night(f_date_str, json_conf,1)
      #if -5 <= int(sun_el) <= 90:
      if True:
         print(f_date_str, sun_status, sun_az, sun_el)
         #frames,color_frames,subframes,sum_vals,max_vals,pos_vals = load_frames_fast(file, json_conf, 1, 1, [], 1,[])
         color_frame = cv2.imread(file)
         orig_img = color_frame.copy()
 
         color_frame = cv2.subtract(color_frame, color_mask)
         frame = cv2.cvtColor(color_frame, cv2.COLOR_BGR2GRAY)
        

         #frame = frames[0]
         #color_frame = color_frames[0]

         #color_sub = cv2.subtract(color_frame, color_mask)
         if sun_status == "day":
            color_sub = cv2.subtract(color_frame, color_flat)
         else:
            color_sub = color_frame

         color_thresh = get_color_thresh(color_sub, 25,25,25,50,50,50)
         #color_thresh2 = get_color_thresh(color_sub, 51,51,51,75,75,75)
         color_thresh2 = get_color_thresh(color_sub, 75,75,75,101,101,101)

         show_img = color_sub.copy()

         all_frames.append(color_frame)
         gray = cv2.cvtColor(color_sub, cv2.COLOR_BGR2GRAY)
 

         sub = cv2.subtract(gray, gray_mask)
         sub = cv2.subtract(gray, gray_flat)
         hdr = histogram(color_sub) 
         if hdr is not None:
            (hist_img, dom_color, green_blue_perc, red_blue_perc) = hdr
         arr = []
         if last_sub is not None:
            image_diff = cv2.absdiff(sub.astype(frame.dtype), last_sub,)
            #cv2.imshow('diff', image_diff)
            _, id_thresh= cv2.threshold(image_diff, 5, 255, cv2.THRESH_BINARY)
            _, id_thresh_high = cv2.threshold(image_diff, 15, 255, cv2.THRESH_BINARY)
            id_thresh_dil = cv2.dilate(id_thresh.copy(), None , iterations=4)
            id_thresh_high_dil = cv2.dilate(id_thresh_high.copy(), None , iterations=4)
            #cv2.imshow('diff-thresh-dil', id_thresh_dil)
            #cv2.imshow('diff-thresh-high-dil', id_thresh_high_dil)

            cnts = get_contours(id_thresh_high_dil) 
            for x,y,w,h in cnts:
               cv2.rectangle(show_img, (int(x), int(y)), (int(x+w) , int(y+h) ), (255, 50, 50), 1)


            cnts = get_contours(id_thresh_dil) 
            if len(cnts) > 0:
               cnt_groups = group_contours(cnts)
               for id in cnt_groups:
                  grp = cnt_groups[id]
                  x1 = min(grp['x1'])
                  y1 = min(grp['y1'])
                  x2 = max(grp['x2'])
                  y2 = max(grp['y2'])
                  cv2.rectangle(show_img, (int(x1), int(y1)), (int(x2) , int(y2) ), (50, 255, 50), 2)

            top_cnts = sorted(cnts, key=lambda x: (x[2]+x[3]), reverse=True)[0:25]
            if len(cnts) > 5: 
               tc = top_cnts[5]
               #min_shift(color_sub, last_color_sub, [tc[0],tc[1],tc[0]+tc[2],tc[1]+tc[3]])
               #if last_thresh is not None:
               #   min_shift(id_thresh_dil, last_id_thresh_dil, [50,50,250,250])

            for x,y,w,h in cnts:
               arr.append((x,y))
               arr.append((x+w,y+h))

            if len(arr) > 1:
               res = cv2.boundingRect(np.asarray(arr))
               x,y,w,h = res
               cv2.rectangle(show_img,(x,y),(x+w,y+h),(0,0,255),1)

            top_cnts = sorted(cnts, key=lambda x: (x[2]+x[3]), reverse=True)[0:25]
            for x,y,w,h in top_cnts:
               cv2.rectangle(show_img, (int(x), int(y)), (int(x+w) , int(y+h) ), (50, 50, 50), 1)


            if image_acc is None :
               image_acc = id_thresh
               image_acc = np.float32(image_acc)
            else:
               hello = cv2.accumulateWeighted(id_thresh, image_acc, .7)
               show_acc = cv2.convertScaleAbs(image_acc)
               acc_frames.append(show_acc)
               #cv2.imshow('Image Acc', show_acc)

            

         #cv2.imshow('color sub', show_img)
         #cv2.imshow('med-sub', sub)
         #cv2.waitKey(30)
         last_sub = sub
         if id_thresh is not None and image_acc is not None:
            last_thresh = id_thresh
            last_thresh_high = id_thresh_high
            last_diff = image_diff 
            last_id_thresh_dil = id_thresh_dil
            show_img = cv2.addWeighted(show_img, .9, grid_img, .1, 0)

            fn, dir = fn_dir(file)
            text_desc = f_date_str + " " + fn 
            #, sun_status, sun_az, sun_el)
            if use_snaps == 0:
               comp_img_file = file.replace(".png", "-comp.jpg")
            else:
               comp_img_file = file.replace("-1920x1080.jpg", "-comp.jpg")
            print("COMP IMG FILE:", comp_img_file) 
            if cfe(comp_img_file) == 0:
            #if True:
               stack_dir = "/mnt/ams2/SD/proc2/" + day + "/images/" 
               stack_files = glob.glob(stack_dir + stack_wild)
               if len(stack_files) > 0:
                  stack_file = stack_files[0]
               else:
                  stack_file = None
               
               if stack_file is not None:
                  stack_img = cv2.imread(stack_file)
                  stack_img = cv2.resize(stack_img,(show_img.shape[1],show_img.shape[0]))
                  show_img = cv2.addWeighted(show_img, .6, stack_img, .4, 0)
               print("STACK:", stack_file)
               comp_img = composite([show_img, orig_img, image_acc, color_thresh, color_thresh2 , hist_img], ["Mask/Flat Subtracted","Original", "Diff with Previous", "Color Thresh","Color Thresh 2", "Histogram"], text_desc )
               #cv2.imshow("COMP FINAL", comp_img)
               #cv2.waitKey(45)
               print("WRITE:", comp_img_file)
               cv2.imwrite(comp_img_file, comp_img)
            else:
               comp_img = cv2.imread(comp_img_file)
               cv2.imshow('COMP', comp_img) 
               cv2.waitKey(15)
         last_color_sub = color_sub
   fn, dir = fn_dir(comp_img_file)
   outfile = dir + "/weather-" + day + "-" + cam + ".mp4"
   wild = dir + day + "*" + cam + "*comp.jpg"
   video_from_images(wild, outfile)
         

def group_contours(cnts):
   cnt_groups = {} 
   used = {}
   print("GROUP CNTS:", len(cnts))
   for x,y,w,h in cnts:
      key = str(x) + "." + str(y) + "." + str(w) + "." + str(h)
      if key in used:
         continue
      print("CNT:", x,y,w,h) 
      ccx = x + int(w/2)
      ccy = y + int(h/2)
      if len(cnt_groups) == 0:
         print("MAKE FIRST GROUP.")
         cnt_groups = make_cnt_group(x,y,w,h,cnt_groups, 1)
         continue 
      else:
         found = 0
         for id in cnt_groups:
            cnt_grp = cnt_groups[id]

            gx1 = min(cnt_grp['x1'])
            gy1 = min(cnt_grp['y1'])
            gx2 = max(cnt_grp['x2'])
            gy2 = max(cnt_grp['y2'])

            gcx = int((gx1+gx2)/2)
            gcy = int((gy1+gy2)/2)
            dist = calc_dist((ccx,ccy),(gcx,gcy))
            if dist < 25:
               print("UPDATE GROUP.")
               cnt_groups = update_cnt_group(x,y,w,h,cnt_groups, id)
               continue 
         if found == 0:
            next_id = max(cnt_groups.keys()) + 1
            print("Make New Group.", next_id)
            cnt_groups = make_cnt_group(x,y,w,h,cnt_groups, next_id)
      used[key] = 1

   print("LEN CNTS:", len(cnts), cnts)
   print("LEN GROUPS:", len(cnt_groups), cnt_groups)

   return(cnt_groups)
   
         

def make_cnt_group(x,y,w,h,cnt_groups, grp_id):
   cnt_groups[grp_id] = {}
   cnt_groups[grp_id]['x1'] = []
   cnt_groups[grp_id]['y1'] = []
   cnt_groups[grp_id]['x2'] = []
   cnt_groups[grp_id]['y2'] = []
   cnt_groups[grp_id]['x1'].append(x)
   cnt_groups[grp_id]['y1'].append(y)
   cnt_groups[grp_id]['x2'].append(x+w)
   cnt_groups[grp_id]['y2'].append(y+h)
   return(cnt_groups)

def update_cnt_group(x,y,w,h,cnt_groups, grp_id):
   cnt_groups[grp_id]['x1'].append(x)
   cnt_groups[grp_id]['y1'].append(y)
   cnt_groups[grp_id]['x2'].append(x+w)
   cnt_groups[grp_id]['y2'].append(y+h)
   return(cnt_groups)

   
# median_frame = cv2.convertScaleAbs(np.median(np.array(crop_frames), axis=0))


def detect_clouds(video_file,json_conf):
   frames,color_frames,subframes,sum_vals,max_vals,pos_vals = load_frames_fast(video_file, json_conf, 3, 1, [], 1,[])
   fc = 1
   for frame in frames:
       
      cv2.imshow('Viewer', color_frames[fc])
      cv2.waitKey(45)
      sub = color_thresh(color_frames[fc])

      #detect_in_grid(frame)
      fc += 1



def get_color_thresh(image, t1,t2,t3,t4,t5,t6):
   gsize = 100
   height,width = image.shape[:2]

   color_bound_low = np.array((t1,t2,t3) ,  dtype=np.uint8, ndmin=1)
   color_bound_high = np.array((t4,t5,t6) ,  dtype=np.uint8, ndmin=1)
   image_bound = cv2.inRange(image,color_bound_low, color_bound_high)
   #mask_image = 255- mask
   #cv2.imshow('color thresh', image_bound)
   #cv2.waitKey(0)
   return(image_bound)

def color_thresh(image, low=[60,0,0], high=[255,200,200]):
   gsize = 100
   height,width = image.shape[:2]

   low_color_bound = np.array((50,0,0) ,  dtype=np.uint8, ndmin=1)
   high_color_bound = np.array((225,225,225) ,  dtype=np.uint8, ndmin=1)
   mask = cv2.inRange(image,low_color_bound, high_color_bound)
   mask_image = 255- mask
   #cv2.imshow('mask', mask_image)
   #cv2.waitKey(45)
   gray   = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
   sub = cv2.subtract(gray, mask_image)


   #cv2.imshow('sub', sub)
   #cv2.waitKey(0)


   for w in range(0,width):
      for h in range(0,height):
         if (w == 0 and h == 0) or (w % gsize == 0 and h % gsize == 0):
            x1 = w
            x2 = w + gsize
            y1 = h
            y2 = h + gsize
            if x2 > width:
               x2 = width 
            if y2 > height:
               y2 = height 
            if x2 <= width and y2 <= height:
               grid_img = image[y1:y2,x1:x2]
               grid_val = np.mean(grid_img)
               #cv2.imshow('grid_img', grid_img)
               #cv2.waitKey(45)
   return(mask_image)



def detect_in_grid(image):
   gsize = 100
   height,width = image.shape[:2]
   img_avg_val= np.sum(image)
   grid_avg_vals = []







   for w in range(0,width):
      for h in range(0,height):
         if (w == 0 and h == 0) or (w % gsize == 0 and h % gsize == 0):
            x1 = w
            x2 = w + gsize
            y1 = h
            y2 = h + gsize
            if x2 > 1920:
               x2 = 1920
            if y2 > 1080:
               y2 = 1080
            if x2 <= width and y2 <= height:
               grid_img = image[y1:y2,x1:x2]
               grid_val = np.mean(grid_img)
               grid_avg_vals.append((x1,y1,x2,y2,grid_val))

            #cv2.rectangle(image, (int(x1), int(y1)), (int(x2) , int(y2) ), (50, 50, 50), 1)


   np_grid_vals = np.array(grid_avg_vals)
   med_grid = np.median(np_grid_vals[:,4])
   for data in grid_avg_vals:
      x1,y1,x2,y2,grid_val = data 
      grid_perc = grid_val / med_grid
      #print("MED GRID:", med_grid, grid_val, grid_val / med_grid)
      if grid_perc < .85 and y2 > height/2:
         image[y1:y2,x1:x2] = 40 

      cnt_img = image[y1:y2,x1:x2] 
      cavg = np.mean(cnt_img)  

      min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(cnt_img)
      best_thresh = find_best_thresh(cnt_img, max_val)
      px_diff = max_val - min_val
      print("BEST:", best_thresh)
      print("PXD:", px_diff)
      _, cnt_img_thresh= cv2.threshold(cnt_img, best_thresh, 255, cv2.THRESH_BINARY)
      cnts = get_contours(cnt_img_thresh) 
      print("CNTS:", cnts)
      for x,y,w,h in cnts:
         cv2.rectangle(image, (int(x+x1), int(y+y1)), (int(x+x1+w) , int(y+y1+h) ), (255, 255, 255), 1)

   #print("GRID VALS:", grid_avg_vals)
   cv2.imshow('Viewer', image)
   cv2.waitKey(45)

def get_contours(frame):
   cont = []
   img_h, img_w = frame.shape[:2]
   if len(frame.shape) > 2:
      frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
   cnt_res = cv2.findContours(frame.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
   if len(cnt_res) == 3:
      (_, cnts, xx) = cnt_res
   elif len(cnt_res) == 2:
      (cnts, xx) = cnt_res
   for (i,c) in enumerate(cnts):
      x,y,w,h = cv2.boundingRect(cnts[i])
      if (w > 5 and h > 5) and w != img_w and h != img_h:
         cont.append((x,y,w,h))
   return(cont)

def detect_features(image):

   min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(image)
   avg_val = np.mean(image)
   thresh = int(max_val-avg_val)
   low_thresh = 120
   high_thresh = 255
   #print("AVG, MIN, MAX", avg_val, min_val, max_val)   
   _, thresh_frame = cv2.threshold(image, low_thresh, high_thresh, cv2.THRESH_BINARY)
   mask_image = 255- thresh_frame
   cv2.imshow("TRESH", thresh_frame)
   cv2.waitKey(45)
   cv2.imshow("MASK", mask_image)
   cv2.waitKey(0)

def find_best_thresh(subframe, thresh):
   tvals = []
   tvals2 = []
   last_cnts = None
   # starting at max val lower thresh until there is more than 1 cnt, the step before this is the ideal thresh
   for i in range(0, 200):
      thresh = thresh - 10 
      _, threshold = cv2.threshold(subframe.copy(), thresh, 255, cv2.THRESH_BINARY)
      cv2.imshow("THRESH", threshold)
      cv2.waitKey(30)
      cnts = get_contours(threshold)
      if len(cnts) > 0:
         return(thresh)
      last_thresh = thresh
      last_cnts = len(cnts)
      if len(cnts) >= 1:
         tvals.append((thresh,len(cnts)))
      if thresh < 5:
         break
   if len(tvals) > 0:
      temp = sorted(tvals, key=lambda x: (x[0]), reverse=False)
      best_thresh = temp[0][0] 
   else:
      best_thresh = thresh

   return(best_thresh)

def get_contours(frame):
   cont = []
   img_h, img_w = frame.shape[:2]
   if len(frame.shape) > 2:
      frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
   cnt_res = cv2.findContours(frame.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
   if len(cnt_res) == 3:
      (_, cnts, xx) = cnt_res
   elif len(cnt_res) == 2:
      (cnts, xx) = cnt_res
   for (i,c) in enumerate(cnts):
      x,y,w,h = cv2.boundingRect(cnts[i])
      if (w > 1 or h > 1) and w != img_w and h != img_h:
         cont.append((x,y,w,h))
   return(cont)

def video_from_images(wild, outfile):

   cmd = "/usr/bin/ffmpeg -framerate 10 -pattern_type glob -i '" + wild + "' -c:v libx264 -pix_fmt yuv420p -y " + outfile + " >/dev/null 2>&1"
   print(cmd)
   os.system(cmd)
   outfile_lr = outfile.replace(".mp4", "-lr.mp4")
   cmd = "/usr/bin/ffmpeg -i " + outfile + " -vcodec libx264 -crf 30 -y " + outfile_lr
   os.system(cmd)

def layout_template(json_conf):
   layout6 = [
      {
         "position": 5,
         "x1": 0,
         "y1": 0,
         "x2": 640,
         "y2": 360,
         "dim": [640,360]
      },
      {
         "position": 1,
         "x1": 640,
         "y1": 0,
         "x2": 1280,
         "y2": 360,
         "dim": [640,360]
      },
      {
         "position": 2,
         "x1": 1280,
         "y1": 0,
         "x2" : 1920,
         "y2": 360,
         "dim": [640,360]
      },
      {
         "position": 3,
         "x1": 0,
         "y1": 360,
         "x2": 640,
         "y2": 720,
         "dim": [640,360]
      },
      {
         "position": 6,
         "x1": 640,
         "y1": 360,
         "x2": 1280,
         "y2": 720,
         "dim": [640,360]
      },
      {
         "position": 4,
         "x1": 1280,
         "y1": 360,
         "x2": 1920,
         "y2": 720,
         "dim": [640,360]
      },
   ]

   # position 4 is featured
   layout6f = [
      {
         "position": 5,
         "x1": 0,
         "y1": 0,
         "x2": 640,
         "y2": 360,
         "dim": [640,360]
      },
      {
         "position": 1,
         "x1": 640,
         "y1": 0,
         "x2": 1280,
         "y2": 360,
         "dim": [640,360]
      },
      {
         "position": 2,
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
         "x2": 1280,
         "y2": 1080,
         "dim": [1280,720]
      },
      {
         "position": 3,
         "x1": 1280,
         "y1": 360,
         "x2": 1920,
         "y2": 720,
         "dim": [640,360]
      },
      {
         "position": 6,
         "x1": 1280,
         "y1": 720,
         "x2": 1920,
         "y2": 1080,
         "dim": [640,360]
      },
   ]
   return(layout6f)



