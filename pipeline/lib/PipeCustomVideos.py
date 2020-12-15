import glob
from lib.PipeUtil import load_json_file, save_json_file, cfe, day_or_night, convert_filename_to_date_cam, bound_cnt
import datetime as dt
from datetime import datetime 
from suntime import Sun, SunTimeException

from lib.PipeVideo import load_frames_fast
from lib.PipeAutoCal import fn_dir , get_image_stars
import cv2
import os
import numpy as np
import pytz
utc = pytz.UTC

def time_lapse_frames(date, cams_id, json_conf, sunset, sunrise):

   date_dt = datetime.strptime(date, "%Y_%m_%d")
   fy, mf, md = date.split("_")
   yest = (date_dt - dt.timedelta(days = 1)).strftime("%Y_%m_%d")
   print(date)
   print(yest)

   all_files = []
   yest_files = glob.glob("/mnt/ams2/SD/proc2/" + yest + "/*" + cams_id + "*.mp4")
   today_files = glob.glob("/mnt/ams2/SD/proc2/" + date + "/*" + cams_id + "*.mp4")
   for file in yest_files:
      (f_datetime, cam, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(file)
      f_datetime= utc.localize(f_datetime) 
      if sunset <= f_datetime <= sunrise:
         all_files.append(file)
   for file in today_files:
      (f_datetime, cam, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(file)
      f_datetime= utc.localize(f_datetime) 
      if int(fh) < 20:
         all_files.append(file)
   yest_snap_dir = "/mnt/ams2/SD/proc2/" + yest + "/snaps/"
   if cfe(yest_snap_dir,1) == 0:
      os.makedirs(yest_snap_dir)   
   snap_dir = "/mnt/ams2/SD/proc2/" + date + "/snaps/"
   if cfe(snap_dir,1) == 0:
      os.makedirs(snap_dir)   
   tl_files = []
   for file in sorted(all_files):
      if "trim" not in file and "crop" not in file:
         (f_datetime, cam, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(file)

         outfile = "/mnt/ams2/SD/proc2/" + fy + "_" + fmin + "_" + fd + "/snaps/" + fy + "_" + fmin + "_" + fd + "_" + fh + "_" + fm + "_" + fs + "_000_" + cams_id + ".jpg"
 
         if cfe(outfile) == 0:
            print("NOT FOUND:", outfile)
            cmd = """ /usr/bin/ffmpeg -i """ + file + """ -vf select="between(n\,""" + str(0) + """\,""" + str(1) + """),setpts=PTS-STARTPTS" -y -update 1 """ + outfile + " >/dev/null 2>&1"
            print(cmd)
            os.system(cmd)
            img = cv2.imread(outfile)
            img_big = cv2.resize(img,(1280,720))
            cv2.imwrite(outfile, img_big)
         tl_files.append(outfile)

         #os.system(cmd)
   return(tl_files)

def meteors_last_night_for_cam(date, cams_id, json_conf):
    meteors = []


    date_dt = datetime.strptime(date, "%Y_%m_%d")
    ffy, fmm, fdd = date.split("_")
    yest = (date_dt - dt.timedelta(days = 1)).strftime("%Y_%m_%d")
    yest_dt = (date_dt - dt.timedelta(days = 1))

    mdir = "/mnt/ams2/meteors/" + date + "/" 
    jfiles = glob.glob(mdir + "*" + cams_id + "*.json")


    ymdir = "/mnt/ams2/meteors/" + yest + "/" 
    yfiles = glob.glob(ymdir + "*" + cams_id + "*.json")

    sun = Sun(float(json_conf['site']['device_lat']), float(json_conf['site']['device_lng']))
    sunrise =sun.get_sunrise_time(date_dt)
    sunset =sun.get_sunset_time(yest_dt)

    print("SS:", sunset, sunrise)
    tl_files = time_lapse_frames(date, cams_id, json_conf, sunset, sunrise)
    #tl_files = []
    #exit()

    # we only want meteors between dusk and dawn from the active date passed in. 
    for mf in yfiles:
       if "reduced" not in mf and "stars" not in mf and "man" not in mf and "star" not in mf and "import" not in mf and "archive" not in mf:
          (f_datetime, cam, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(mf)
          # only add meteors that happened after the sunset yesterday
          f_datetime= utc.localize(f_datetime) 
          if sunset <= f_datetime <= sunrise:
             meteors.append(mf)

    hd_meteors = []
    for mf in jfiles:
       # only add meteors BEFORE dawn,
       if "reduced" not in mf and "stars" not in mf and "man" not in mf and "star" not in mf and "import" not in mf and "archive" not in mf:
          (f_datetime, cam, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(mf)
          f_datetime= utc.localize(f_datetime) 
          if sunset <= f_datetime <= sunrise:
             meteors.append(mf)

    for meteor_file in meteors:

       mj = load_json_file(meteor_file)
       if "hd_trim" in mj:
          hd_meteors.append((meteor_file, mj['hd_trim']))
    hd_meteors = sorted(hd_meteors, key=lambda x: x[0], reverse=True)

    if cfe("./CACHE/", 1) == 0:
       os.makedirs("./CACHE/")
    else:
       os.system("rm ./CACHE/*.jpg")

    for tl in tl_files:
       print("cp "+ tl + " ./CACHE/")
       os.system("cp "+ tl + " ./CACHE/")
    for mf, hdf in hd_meteors:
       print(mf, hdf)

       hd_frames,hd_color_frames,subframes,sum_vals,max_vals,pos_vals = load_frames_fast(hdf, json_conf, 0, 0, 1, 1,[])
       #start_fn, end_fn = find_start_end(sum_vals) 
       file_fn, file_dir = fn_dir(hdf)
       frame_prefix = file_fn.replace(".mp4", "") 
       avg_val = np.mean(sum_vals)
       med_val = np.median(sum_vals)
       fn = 0
       cm = 0
       nm = 0
       ff = 0
       lf = 0
       last_frame = None

       # get_stars in image
       stars = get_image_stars(hdf, hd_frames[0].copy(), json_conf, 0)

       for c in range(0, len(hd_color_frames)):

          frame = subframes[fn]
          frame = blackout_stars(frame, stars)
          if last_frame is not None:
             subsub = cv2.subtract(frame, last_frame)
          else:
             subsub = frame
          thresh = 100
          _, threshold = cv2.threshold(subsub.copy(), thresh, 255, cv2.THRESH_BINARY)
          sum_val = np.sum(threshold)
          #show_frame = cv2.resize(threshold,(1280,720))
          #cv2.imshow('pepe', show_frame)
          if sum_val > 1000:
             cm += 1
             nm = 0
          #   cv2.waitKey(0)
          else:
             nm += 1
          #   cv2.waitKey(30)
          
          if cm >= 2 and ff == 0:
             ff = fn - 10

          if lf == 0 and cm >= 2 and nm >= 10:
             lf = fn  
          print("FN:", fn, med_val, avg_val, sum_val, cm, nm, ff, lf)
          fn += 1
          last_frame = frame
       print("FIRST / LAST FRAME:", ff, lf)
       if ff == 0 and lf == 0:
          ff = 10
          lf = len(hd_frames) - 10
       if ff <= 0 :
          ff = 0
       if lf <= 0 :
          lf = len(hd_frames)

       #wait = input("waiting..")

       for fn in range(ff, lf):

          frame = hd_color_frames[fn]
          counter = "{:04d}".format(fn)
          frame_file = frame_prefix + "-" + counter + ".jpg"
          show_frame = cv2.resize(frame,(1280,720))

          #cv2.putText(show_frame, str("DETECT"),  (20,50), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
          #cv2.putText(show_frame, str(fn),  (20,70), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)

          #cv2.imshow('pepe', show_frame)
          #cv2.waitKey(30)
          cv2.imwrite("./CACHE/" + frame_file, show_frame)
    cmd = "./FFF.py imgs_to_vid ./CACHE/ " + fy + " /mnt/ams2/CUSTOM_VIDEOS/" + date + "_" + cams_id + ".mp4 25 28"
    print(cmd)
    os.system(cmd)

def blackout_stars(frame, stars):
   for star in stars:
      print(star)
      x,y,ii = star
      rx1,ry1,rx2,ry2 = bound_cnt(x, y,1920,1080, 10)
      frame[ry1:ry2,rx1:rx2] = 0
   #cv2.imshow('pepe', frame)
   #cv2.waitKey(0)
   return(frame)


def find_start_end(sum_vals):
   avg_val = np.mean(sum_vals)
   for c in range(0, len(sum_vals)):
      if sum_vals[c] > avg_val:
         print("*** VAL:", sum_vals[c])
      else:
         print("VAL:", sum_vals[c])
   exit()
