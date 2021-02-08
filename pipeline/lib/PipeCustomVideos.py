import glob
from lib.FFFuncs import best_crop_size, slow_stack_video
from lib.PipeUtil import load_json_file, save_json_file, cfe, day_or_night, convert_filename_to_date_cam, bound_cnt
from lib.PipeMeteorTests import gap_test
from lib.PipeDetect import get_contours_in_image, find_object, analyze_object, get_trim_num
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
SHOW = 0

def join_two(json_conf):
   one = sorted(glob.glob("./CACHE3/*"))
   two = sorted(glob.glob("./CACHE2/*"))
   print("JOIN", len(one))
   comp_h = 360
   comp_w = 640 * 2 
   for i in range(0, len(two)):

      #file1 = one[i]
      file2 = two[i]
      #img1 = cv2.imread(file1)
      img2 = cv2.imread(file2)
      #img1 = cv2.resize(img1,(640,360))
      img2 = cv2.resize(img2,(640,360))
      #comp = np.zeros((comp_h,comp_w,3),dtype=np.uint8)
      #comp[0:360,0:640] = img1
      #comp[0:360,640:1280] = img2
      #if i % 2 == 0:
      if True:
         out = file2.replace("CACHE2", "FINAL")
         #print("WROTE:", i, out)
         cv2.imwrite(out, img2)
         #cv2.imshow('pepe', img2)
         #cv2.waitKey(30)


def simple_TL(TL_CONF, json_conf):
   # slow stack speeds 10 SS = 1 min = 149 stacked frames = 6 seconds
   # slow stack speeds 25 SS = 1 min = 60 stacked frames = 2.3 seconds
   # SS = 50 = 1 minute = 30 stacked frames or 1.3 seconds
   tl_conf = load_json_file(TL_CONF)
   start_day = tl_conf['start_time'][0:10]
   end_day = tl_conf['end_time'][0:10]
   all_start_dt = datetime.strptime(tl_conf['start_time'], "%Y_%m_%d_%H_%M_%S")
   all_end_dt = datetime.strptime(tl_conf['end_time'], "%Y_%m_%d_%H_%M_%S")
   slow_stack_start,slow_stack_end,slow_stack_speed = tl_conf['slow_stacks'][0]
   ss_start_dt = datetime.strptime(slow_stack_start, "%Y_%m_%d_%H_%M_%S")
   ss_end_dt = datetime.strptime(slow_stack_end, "%Y_%m_%d_%H_%M_%S")
   cam = tl_conf['cams_id']
   night_files = glob.glob("/mnt/ams2/SD/proc2/" + start_day + "/*" + cam + "*.mp4")
   day_files = glob.glob("/mnt/ams2/SD/proc2/daytime/" + start_day + "/*" + cam + "*.mp4")
   all_files = []
   print(len(night_files), len(day_files))
   for file in night_files:
      (f_datetime, cam, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(file)
      fn,dir = fn_dir(file)
      sfile = "./CACHE2/" + fn
      sfile = sfile.replace(".mp4", "-0100.jpg")
      if ss_start_dt <= f_datetime <= ss_end_dt:
         print("CHECK:", sfile)
         if cfe(sfile) == 0:
            print("SLOW STACK!", file)
            slow_stack_video(file, "./CACHE2/", 50) 
         else:
            print("DONE SKIP", sfile)
         #cmd = "./FFF.py slow_stack " + file +  " ./CACHE2/ " + str(slow_stack_speed)
      #else:
  
         #print("wrong time", ss_start_dt, f_datetime, ss_end_dt)
         #os.system(cmd)
   for file in day_files:
      (f_datetime, cam, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(file)
      if ss_start_dt <= f_datetime <= ss_end_dt:
         print("SLOW STACK!", file)

         cmd = "./FFF.py slow_stack " + file +  " ./CACHE2/ " + str(slow_stack_speed)
         print(cmd)
         os.system(cmd)
   cmd = "/usr/bin/ffmpeg -framerate 25 -pattern_type glob -i './CACHE2/*.jpg' -c:v libx264 -pix_fmt yuv420p -y /mnt/ams2/CUSTOM_VIDEOS/" + start_day + "_" + cam + "_simple_tl.mp4"

def assemble_custom(TL_CONF, json_conf):
   min_index = {}
   tl_conf = load_json_file(TL_CONF)
   print(tl_conf)
   all_start_dt = datetime.strptime(tl_conf['start_time'], "%Y_%m_%d_%H_%M_%S")
   all_end_dt = datetime.strptime(tl_conf['end_time'], "%Y_%m_%d_%H_%M_%S")
   cache_dir = "./FINAL/"
   cams_id = tl_conf['cams_id']
   date = all_start_dt.strftime("%Y_%m_%d")
   mdir = "/mnt/ams2/meteors/" + date + "/" 
   jsons = glob.glob(mdir + "*" + cams_id + "*")
   reds = []

   date_dt = datetime.strptime(date, "%Y_%m_%d")
   ffy, fmm, fdd = date.split("_")
   yest = (date_dt - dt.timedelta(days = 1)).strftime("%Y_%m_%d")
   yest_dt = (date_dt - dt.timedelta(days = 1))

   mdir = "/mnt/ams2/meteors/" + date + "/" 
   jfiles = glob.glob(mdir + "*" + cams_id + "*.json")


   ymdir = "/mnt/ams2/meteors/" + yest + "/" 
   yfiles = glob.glob(ymdir + "*" + cams_id + "*.json")

   sun = Sun(float(json_conf['site']['device_lat']), float(json_conf['site']['device_lng']))

   try:
      sunrise =sun.get_sunrise_time(date_dt)
      sunset =sun.get_sunset_time(yest_dt)
      sunrise = datetime.strptime(sr, "%Y_%m_%d_%H_%M_%S")
      sunset = datetime.strptime(ss, "%Y_%m_%d_%H_%M_%S")
   except:
      sr = date + "_23_59_59"
      ss = date + "_00_00_00"
      sunrise = datetime.strptime(sr, "%Y_%m_%d_%H_%M_%S")
      sunset = datetime.strptime(ss, "%Y_%m_%d_%H_%M_%S")
      sunrise = utc.localize(sunrise) 
      sunset = utc.localize(sunset) 


   min_index = {}
   for n in range(int(((all_end_dt - all_start_dt).seconds)/60)+1):
      min_dt = all_start_dt + dt.timedelta(minutes=n)
      min_key = min_dt.strftime("%Y_%m_%d_%H_%M")
      min_index[min_key] = {}
      min_index[min_key]['snaps'] = []
      min_index[min_key]['slow_stacks'] = []
      min_index[min_key]['meteors'] = []


   # get TL Files
   tl_files = time_lapse_frames(date, cams_id, json_conf, sunset, sunrise)
   for tl in tl_files:
      (f_datetime, cam, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(tl)
      if all_start_dt < f_datetime < all_end_dt:
         good = 1
      else:
         continue
      fn, dir = fn_dir(tl)
      cache_file = "./CACHE/" + fn
      if cfe(cache_file) == 0:
         print("cp "+ tl + " ./CACHE/")
         os.system("cp "+ tl + " ./CACHE/")
         cimg = cv2.imread(cache_file)
         cv2.putText(cimg, str(f_date_str),  (1100,710), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
         op_desc = json_conf['site']['operator_name'] + " " + json_conf['site']['obs_name'] + " " + json_conf['site']['location']
         cv2.putText(cimg, str(op_desc),  (10,710), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
         if SHOW == 1:
            cv2.imshow('pepe', cimg)
            cv2.waitKey(30)
         cv2.imwrite(cache_file, cimg)



   cache1 = glob.glob("CACHE/*" + tl_conf['cams_id'] + "*")
   cache2 = glob.glob("CACHE2/*" + tl_conf['cams_id'] + "*")

   # get meteors
   for js in jsons:
      if "reduced" in js:
         reds.append(js)
   for red in reds:
      (f_datetime, cam, f_date_str,fy,fmon,fd, fh, fm, fs) = convert_filename_to_date_cam(red)
      if all_start_dt <= f_datetime <= all_end_dt :
         min_key = fy + "_" + fmon + "_" + fd + "_" + fh + "_" + fm
      rj = load_json_file(red)
      mfd = len(rj['meteor_frame_data'])
      if rj['meteor_frame_data'][0][2] - 100 < 0 or rj['meteor_frame_data'][0][2] + 100 > 1920:
         continue
      if mfd < 15:
         continue
      ff = rj['meteor_frame_data'][0][1]  - 10
      lf = rj['meteor_frame_data'][-1][1] + 15
      if mfd > 30:
         lf += 50 
      print(red, mfd , ff, lf)
      mframes = dump_meteor_frames(rj['hd_video_file'], ff, lf, "./FINAL/", json_conf)
      min_index[min_key]['meteors'] = mframes

   for min_key in min_index:
      min_key_dt = datetime.strptime(min_key, "%Y_%m_%d_%H_%M")
      for slow_start, slow_end , mod in tl_conf['slow_stacks']: 
         start_dt = datetime.strptime(slow_start, "%Y_%m_%d_%H_%M")
         end_dt = datetime.strptime(slow_end, "%Y_%m_%d_%H_%M")
         if start_dt <= min_key_dt <= end_dt:
            print("SLOW STACK NEEDED:", min_key)


   for slow_start, slow_end , mod in tl_conf['slow_stacks']: 
      start_dt = datetime.strptime(slow_start, "%Y_%m_%d_%H_%M")
      end_dt = datetime.strptime(slow_end, "%Y_%m_%d_%H_%M")

      for file in sorted(cache2):
         (f_datetime, cam, f_date_str,fy,fmon,fd, fh, fm, fs) = convert_filename_to_date_cam(file)
         if start_dt <= f_datetime <= end_dt :
            min_key = fy + "_" + fmon + "_" + fd + "_" + fh + "_" + fm
            if len(min_index[min_key]['meteors']) == 0:
               print("adding CACHE2:", min_key, file)
               min_index[min_key]['slow_stacks'].append(file)

   for min_key in min_index:
      if len(min_index[min_key]['meteors'])  == 0 and len(min_index[min_key]['slow_stacks']) > 0 :
         for i in range(0, len(min_index[min_key]['slow_stacks'])):
            if i % 1 == 0:
               cmd = "cp " + min_index[min_key]['slow_stacks'][i] + " " + cache_dir
               print(cmd)
               os.system(cmd)

   for file in cache1:
      if "meteor" in file:
         continue  
      (f_datetime, cam, f_date_str,fy,fmon,fd, fh, fm, fs) = convert_filename_to_date_cam(file)
      if all_start_dt <= f_datetime <= all_end_dt :
         min_key = fy + "_" + fmon + "_" + fd + "_" + fh + "_" + fm
         min_index[min_key]['snaps'].append(file)
   for key in min_index:
      if len(min_index[key]['meteors']) == 0 and len(min_index[key]['slow_stacks']) == 0:
         if len(min_index[key]['snaps']) > 0:
            cmd = "cp " + min_index[key]['snaps'][0] + " " + cache_dir
            os.system(cmd)

      print(key, min_index[key])

   cmd = "./FFF.py imgs_to_vid " + cache_dir + " " + cams_id + " /mnt/ams2/CUSTOM_VIDEOS/" + date + "_" + cams_id + "_meteors.mp4 25 24"
   print(cmd)
   os.system(cmd)
   cmd = "./FFF.py resize /mnt/ams2/CUSTOM_VIDEOS/" + date + "_" + cams_id + "_meteors.mp4 /mnt/ams2/CUSTOM_VIDEOS/" + date + "_" + cams_id + "_meteors-360p.mp4 640 360 25"
   os.system(cmd)
   cmd = "./FFF.py resize /mnt/ams2/CUSTOM_VIDEOS/" + date + "_" + cams_id + "_meteors.mp4 /mnt/ams2/CUSTOM_VIDEOS/" + date + "_" + cams_id + "_meteors-180p.mp4 320 180 28"
   os.system(cmd)

def dump_meteor_frames(hdf, ff, lf, cache_dir, json_conf):
   file_fn, file_dir = fn_dir(hdf)
   date = file_fn[0:10]
   hd_frames,hd_color_frames,subframes,sum_vals,max_vals,pos_vals = load_frames_fast(hdf, json_conf, 0, 0, 1, 1,[])
   frame_prefix = file_fn.replace(".mp4", "")
   files = glob.glob(cache_dir + frame_prefix + "*")
   if len(files) > 5:
      return(files)
   stars = get_image_stars(hdf, hd_frames[0].copy(), json_conf, 0)
   (f_datetime, cams_id, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(hdf)
   trim_num = get_trim_num(hdf)
   extra_sec = int(trim_num) / 25
   start_trim_frame_time = f_datetime + dt.timedelta(0,extra_sec)
   if ff < 0 :
      ff = 0
   if lf >= len(hd_frames) :
      lf = len(hd_frames)
   rcc = 0
   mframes = []
   if True:
      for fn in range(ff, lf):

         frame = hd_color_frames[fn]
         counter = "{:04d}".format(fn)
         frame_file = frame_prefix + "-" + counter + ".jpg"
         extra_sec = fn / 25
         frame_time = start_trim_frame_time + dt.timedelta(0,extra_sec)
         frame_time_str = frame_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]


         if rcc <= 10:
            if rcc <= 7 :
               rc_val = 130 + (rcc * 5)
            else:
               rc_val = rc_val - 5
          #cv2.rectangle(frame, (cx1, cy1), (cx2, cy2), (rc_val,rc_val,rc_val), 2, cv2.LINE_AA)

         show_frame = cv2.resize(frame,(1280,720))
         cv2.putText(show_frame, str(frame_time_str),  (1100,710), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
         op_desc = json_conf['site']['operator_name'] + " " + json_conf['site']['obs_name'] + " " + json_conf['site']['location']
         cv2.putText(show_frame, str(op_desc),  (10,710), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)

         #cv2.putText(show_frame, str("DETECT"),  (20,50), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
         #cv2.putText(show_frame, str(fn),  (20,70), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
         if SHOW == 1:
            cv2.imshow('pepe', show_frame)
            cv2.waitKey(30)
         mframes.append(cache_dir + frame_file)
         cv2.imwrite(cache_dir + frame_file, show_frame)
         rcc += 1

   return(mframes)

def assemble_custom_old(TL_CONF, json_conf):
   min_index = {}
   tl_conf = load_json_file(TL_CONF)
   print(tl_conf)
   all_start_dt = datetime.strptime(tl_conf['start_time'], "%Y_%m_%d_%H_%M_%S")
   all_end_dt = datetime.strptime(tl_conf['end_time'], "%Y_%m_%d_%H_%M_%S")

   cams_id = tl_conf['cams_id']
   date = all_start_dt.strftime("%Y_%m_%d")
   mdir = "/mnt/ams2/meteors/" + date + "/" 
   mdata_file = mdir + json_conf['site']['ams_id'] + "_" + date + "_" + cams_id + "_meteor_data.info"
   print(mdata_file)
   meteors = load_json_file(mdata_file)
   fmeteors = []
   bmeteors = []
   for meteor in meteors:
      if "obj_id" in meteor['objects']:
         print(meteor['hdf'], len(meteor['objects']['ofns']))
         if len(meteor['objects']['ofns']) >= 10:
            meteor['best'] = meteor['objects'][obj] = meteor['objects']
            fmeteors.append(meteor)
         else:
            bmeteors.append(meteor)
      else:
         for obj in meteor['objects']:
            print(meteor['hdf'], len(meteor['objects'][obj]['ofns']))
            if len(meteor['objects'][obj]['ofns']) >= 10:
               meteor['best'] = meteor['objects'][obj]
               fmeteors.append(meteor)
            else:
               bmeteors.append(meteor)

   for meteor in fmeteors:
      print("FINAL:", meteor['hdf'], len(meteor['best']['ofns']))
      root_fn, dir = fn_dir(meteor['hdf'])
      root_fn = root_fn.replace(".mp4", "")
      print("ROOT:", root_fn)

   exit()
   for meteor in bmeteors:
      print("BAD:", meteor['hdf'])

   for n in range(int(((all_end_dt - all_start_dt).seconds)/60)+1):
      min_dt = all_start_dt + dt.timedelta(minutes=n)
      min_key = min_dt.strftime("%Y_%m_%d_%H_%M")
      min_index[min_key] = []


   cache1 = glob.glob("CACHE/*" + tl_conf['cams_id'] + "*")
   cache2 = glob.glob("CACHE2/*" + tl_conf['cams_id'] + "*")
 
   # Add meteors first, then slow stacks, then single frame TLs
   used = {}
   for file in sorted(cache1):
      (f_datetime, cam, f_date_str,fy,fmon,fd, fh, fm, fs) = convert_filename_to_date_cam(file)
      if all_start_dt <= f_datetime <= all_end_dt :
         min_key = fy + "_" + fmon + "_" + fd + "_" + fh + "_" + fm
         print(min_key)
         if "meteor" in file:
            min_index[min_key].append(file)

   for key in min_index:
      if len(min_index[key]) > 25:
         used[key] = 1
      else:
         min_index[key] = []
   for slow_start, slow_end in tl_conf['slow_stacks']: 
      start_dt = datetime.strptime(slow_start, "%Y_%m_%d_%H_%M")
      end_dt = datetime.strptime(slow_end, "%Y_%m_%d_%H_%M")

      for file in sorted(cache2):
         (f_datetime, cam, f_date_str,fy,fmon,fd, fh, fm, fs) = convert_filename_to_date_cam(file)
         if start_dt <= f_datetime <= end_dt :
            min_key = fy + "_" + fmon + "_" + fd + "_" + fh + "_" + fm
            if min_key not in used:
               print("adding CACHE2:", min_key, file)
               min_index[min_key].append(file)

   for key in min_index:
      if len(min_index[key]) > 0:
         used[key] = 1

   for file in sorted(cache1):
      (f_datetime, cam, f_date_str,fy,fmon,fd, fh, fm, fs) = convert_filename_to_date_cam(file)
      if all_start_dt <= f_datetime <= all_end_dt :
         min_key = fy + "_" + fmon + "_" + fd + "_" + fh + "_" + fm
         if min_key not in used:
            print(min_key)
            min_index[min_key].append(file)
         else:
            print("ALREADY USED!", min_key)
  

   list = ""
   for key in min_index:
      if len(min_index[key]) > 0:
         for file in min_index[key]:
            list += "file '" + file + "'\n" 
   
   fp = open("list.txt", "w")
   fp.write(list)
   fp.close()
   exit()

   final_files = []
   for file in sorted(cache1):
      (f_datetime, cam, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(file)
      if start_dt <= f_datetime <= end_dt :
         final_files.append(file)


   print("FINAL 2", len(final_files))
   for slow_start, slow_end in tl_conf['slow_stacks']: 

      start_dt = datetime.strptime(slow_start, "%Y_%m_%d_%H_%M")
      end_dt = datetime.strptime(slow_end, "%Y_%m_%d_%H_%M")
      cmd = "./FFF.py slow_stack_range " + slow_start[0:10] + " " + slow_start[11:13] + " " + slow_end[11:13] + " " + tl_conf['cams_id']

      temp = []
      for file in sorted(cache2):
         (f_datetime, cam, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(file)
         if start_dt <= f_datetime <= end_dt :
            if "HD" not in file:
               if cam + "-" in file:
                  temp.append(file)

      if len(temp) == 0:
         print("NO SLOW FILES FOR THIS HOUR!")
         print("CMD:", cmd)
         os.system(cmd)
         cache2 = glob.glob("CACHE2/*" + tl_conf['cams_id'] + "*")

      for file in sorted(cache2):
         (f_datetime, cam, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(file)
         if start_dt <= f_datetime <= end_dt :
            if "HD" not in file:
               if cam + "-" in file:
                  print("ADDING SLOW:", file)

                  final_files.append(file)

   list = ''
   print("FINAL", len(final_files))
   final = []
   for file in sorted(final_files):
      fn,dir = fn_dir(file)
      final.append((dir,fn))

   final = sorted(final, key=lambda x: x[1], reverse=False)

   mon = 0
   fsl = 0
   for dir, file in final:

      if "meteor" in file or cams_id + "-" in file: 
         mon = 1
         fsl = 0
      else:
         mon = 0
         fsl += 1
      if mon == 1 or fsl > 1:
         list += "file '" + dir + "/" + file + "'\n"
   fp = open("list.txt", "w")
   fp.write(list)
   fp.close()
   print("wrote list: list.txt")


def hd_snaps(hd_dir, json_conf):
   snap_dir = hd_dir + "/snaps/"
   if cfe(snap_dir, 1) == 0:
      os.makedirs(snap_dir)
   hd_files = glob.glob(hd_dir + "*.mp4")
   for file in hd_files:
      fn, dir = fn_dir(file)
      outfile = snap_dir + fn
      outfile = outfile.replace(".mp4", ".jpg")
      cmd = """ /usr/bin/ffmpeg -i """ + file + """ -vf select="between(n\,""" + str(0) + """\,""" + str(1) + """),setpts=PTS-STARTPTS" -y -update 1 """ + outfile + " >/dev/null 2>&1"
      print(cmd)
      os.system(cmd)


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
      #if sunset <= f_datetime <= sunrise:
      if True:
         all_files.append(file)
      else:
         print("SKIPPING")
   for file in today_files:
      (f_datetime, cam, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(file)
      f_datetime= utc.localize(f_datetime) 
      #if int(fh) < 20:
      if True:
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
   print("TL FILES:", len(tl_files))
   return(tl_files)


def meteors_last_night_detect_data(date, cams_id, json_conf, hd_meteors):
    mdir = "/mnt/ams2/meteors/" + date + "/" 
    meteor_data = []
    for mf, hdf in hd_meteors:
       mdata = {}
       mdata['jsf'] = mf
       mdata['hdf'] = hdf
       #mj = load_json_file(mf)
       hd_frames,hd_color_frames,subframes,sum_vals,max_vals,pos_vals = load_frames_fast(hdf, json_conf, 0, 0, 1, 1,[])
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
       objects,hd_crop = detect_meteor_in_frames(mf , hd_color_frames,subframes,sum_vals,stars)
       mdata['objects'] = objects
       (f_datetime, cam, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(mf)
       trim_num = get_trim_num(mf)
       extra_sec = int(trim_num) / 25
       start_trim_frame_time = f_datetime + dt.timedelta(0,extra_sec)
       print("TRIM ", trim_num)
       print(start_trim_frame_time)
       mdata['start_trim_frame_time'] = start_trim_frame_time.strftime("%Y_%m_%d_%H_%M_%S")
       meteor_data.append(mdata)
    mdata_file = mdir + json_conf['site']['ams_id'] + "_" + date + "_" + cams_id + "_meteor_data.info"
    save_json_file(mdata_file, meteor_data)
    print("SAVED:", mdata_file)
    exit()

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

    try:
       sunrise =sun.get_sunrise_time(date_dt)
       sunset =sun.get_sunset_time(yest_dt)
       sunrise = datetime.strptime(sr, "%Y_%m_%d_%H_%M_%S")
       sunset = datetime.strptime(ss, "%Y_%m_%d_%H_%M_%S")
    except:
       sr = date + "_23_59_59"
       ss = date + "_00_00_00"
       sunrise = datetime.strptime(sr, "%Y_%m_%d_%H_%M_%S")
       sunset = datetime.strptime(ss, "%Y_%m_%d_%H_%M_%S")
       sunrise = utc.localize(sunrise) 
       sunset = utc.localize(sunset) 

    print("SS:", sunset, sunrise)


    tl_files = time_lapse_frames(date, cams_id, json_conf, sunset, sunrise)
    #exit()
    #tl_files = []
    #exit()

    # we only want meteors between dusk and dawn from the active date passed in. 
    for mf in yfiles:
       if "reduced" not in mf and "stars" not in mf and "man" not in mf and "star" not in mf and "import" not in mf and "archive" not in mf:
          (f_datetime, cam, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(mf)
          # only add meteors that happened after the sunset yesterday
          f_datetime= utc.localize(f_datetime) 
          #if sunset <= f_datetime <= sunrise:
          if True:
             meteors.append(mf)

    hd_meteors = []
    for mf in jfiles:
       # only add meteors BEFORE dawn,
       if "reduced" not in mf and "stars" not in mf and "man" not in mf and "star" not in mf and "import" not in mf and "archive" not in mf:
          (f_datetime, cam, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(mf)
          f_datetime= utc.localize(f_datetime) 
          #if sunset <= f_datetime <= sunrise:
          if True:
             meteors.append(mf)

    for meteor_file in meteors:

       mj = load_json_file(meteor_file)
       if "hd_trim" in mj:
          print("ADDING:", mj['hd_trim'])
          hd_meteors.append((meteor_file, mj['hd_trim']))
    hd_meteors = sorted(hd_meteors, key=lambda x: x[0], reverse=True)

    for data in hd_meteors:
       print(data)

    meteors_last_night_detect_data(date, cams_id, json_conf, hd_meteors)
    mdata_file = mdir + json_conf['site']['ams_id'] + "_" + date + "_" + cams_id + "_meteor_data.info"
    exit()
    #meteors_last_night_detect_data(date, cams_id, json_conf, hd_meteors)
    #exit()

    if cfe("./CACHE/", 1) == 0:
       os.makedirs("./CACHE/")
    #else:
    #   os.system("rm ./CACHE/*.jpg")

    for tl in tl_files:
       (f_datetime, cam, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(tl)
       fn, dir = fn_dir(tl)
       cache_file = "./CACHE/" + fn
       if cfe(cache_file) == 0:
          print("cp "+ tl + " ./CACHE/")
          os.system("cp "+ tl + " ./CACHE/")
          cimg = cv2.imread(cache_file)
          cv2.putText(cimg, str(f_date_str),  (1100,710), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
          op_desc = json_conf['site']['operator_name'] + " " + json_conf['site']['obs_name'] + " " + json_conf['site']['location']
          cv2.putText(cimg, str(op_desc),  (10,710), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
          if SHOW == 1:
             cv2.imshow('pepe', cimg)
             cv2.waitKey(30)
          cv2.imwrite(cache_file, cimg)

    meteor_data = []
    hd_meteors = sorted(hd_meteors, key=lambda x: x[0], reverse=False)
   

    for mf, hdf in hd_meteors:
       mdata = {}
       mdata['jsf'] = mf
       mdata['hdf'] = hdf
       #mj = load_json_file(mf)
       hd_frames,hd_color_frames,subframes,sum_vals,max_vals,pos_vals = load_frames_fast(hdf, json_conf, 0, 0, 1, 1,[])
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
       objects,hd_crop = detect_meteor_in_frames(mf , hd_color_frames,subframes,sum_vals,stars)
       mdata['objects'] = objects
       (f_datetime, cam, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(mf)
       trim_num = get_trim_num(mf)
       extra_sec = int(trim_num) / 25
       start_trim_frame_time = f_datetime + dt.timedelta(0,extra_sec)
       print("TRIM ", trim_num)
       print(start_trim_frame_time)
       mdata['start_trim_frame_time'] = start_trim_frame_time
       meteor_data.append(mdata)

       fns = []
       xs = []
       ys = []
       if len(objects) == 1:
          for obj in objects:
             ff = objects[obj]['ofns'][0] - 15
             lf = objects[obj]['ofns'][-1] + 15
             min_x = objects[obj]['oxs'][0] - 25
             min_y = objects[obj]['oys'][0] - 25
             max_x = objects[obj]['oxs'][-1] + 25
             max_y = objects[obj]['oys'][-1] + 25
       elif len(objects) == 0:
          print("NO METEOR FOUND!?")
          #continue
       else:
          print("MORE THAN ONE OBJECT!")
          ff = 0
          lf = len(hd_color_frames)
          min_x = 0
          min_y = 0
          max_x = 0
          max_y = 0

       if ff < 0:
          ff = 0
       if lf > len(hd_color_frames):
          lf = len(hd_color_frames)
       if min_x < 0:
          min_x = 0
       if min_y < 0:
          min_y = 0
       if min_x > 1920:
          min_x = 1919 
       if min_y > 1080:
          min_y = 1079 

       rcc = 0
       cx1, cy1,cx2,cy2 = hd_crop
       if lf - ff < 7:
          continue
       for fn in range(ff, lf):

          frame = hd_color_frames[fn]
          counter = "{:04d}".format(fn)
          frame_file = frame_prefix + "-" + counter + ".jpg"
          print(min_x,min_y,max_x,max_y)
          extra_sec = fn / 25
          frame_time = start_trim_frame_time + dt.timedelta(0,extra_sec)
          frame_time_str = frame_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]


          if rcc <= 15:
             if rcc <= 7 :
                rc_val = 130 + (rcc * 5)
             else:
                rc_val = rc_val - 5
          #cv2.rectangle(frame, (cx1, cy1), (cx2, cy2), (rc_val,rc_val,rc_val), 2, cv2.LINE_AA)

          show_frame = cv2.resize(frame,(1280,720))
          cv2.putText(show_frame, str(frame_time_str),  (1100,710), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
          op_desc = json_conf['site']['operator_name'] + " " + json_conf['site']['obs_name'] + " " + json_conf['site']['location']
          cv2.putText(show_frame, str(op_desc),  (10,710), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)

          #cv2.putText(show_frame, str("DETECT"),  (20,50), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
          #cv2.putText(show_frame, str(fn),  (20,70), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
          if SHOW == 1:
             cv2.imshow('pepe', show_frame)
             cv2.waitKey(30)
          cv2.imwrite("./CACHE/" + frame_file, show_frame)
          rcc += 1
    cmd = "./FFF.py imgs_to_vid ./CACHE/ " + cams_id + " /mnt/ams2/CUSTOM_VIDEOS/" + date + "_" + cams_id + ".mp4 25 28"
    print(cmd)
    os.system(cmd)

def detect_meteor_in_frames(file, hd_color_frames, subframes,sum_vals, stars):

   objects = {}
   last_frame = None
   fn = 0
   cm = 0
   nm = 0
   ff = 0
   lf = 0

   if True:
      for c in range(0, len(hd_color_frames)):

         cframe = hd_color_frames[c]
         frame = subframes[c]
         frame = blackout_stars(frame, stars)
         if last_frame is not None:
            subsub = cv2.subtract(frame, last_frame)
         else:
            subsub = frame
         thresh = 25
         _, threshold = cv2.threshold(subsub.copy(), thresh, 255, cv2.THRESH_BINARY)
         sum_val = int(np.sum(threshold))
         show_frame = cv2.resize(threshold,(1280,720))
         #cv2.imshow('pepe', show_frame)
         if sum_val > 80:
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
         if sum_val > 80:
            cnts = get_contours_in_image(threshold)
            for cnt in cnts:
               cx,cy,cw,ch = cnt
               cnt_img = subsub[cy:cy+ch,cx:cx+cw]
               max_val = int(np.sum(cnt_img))
               object, objects = find_object(objects, c,cx, cy, cw, ch, max_val, 1, 0, None)

   bad = []
   for obj in objects:
      if len(objects[obj]['ofns']) < 2:
         bad.append(obj)
         continue
      objects[obj] = analyze_object(objects[obj])
      gap_test_res , gap_test_info = gap_test(objects[obj]['ofns'])

      if objects[obj]['report']['meteor'] == 1 and gap_test_res != 0:
         meteor_obj = obj
         print("METEOR!")
      else:
         bad.append(obj)
   hd_crop = [0,0,0,0]
   for bb in bad:
      del objects[bb]

   if objects is None:
      print("NO OBJECTS FOUND!?")
      return([], hd_crop)
   elif len(objects) == 0:
      print("NO OBJECTS FOUND!?")
      return([], hd_crop)
   elif len(objects) == 1:
      oxs = objects[meteor_obj]['oxs']
      oys = objects[meteor_obj]['oys']
      cw, ch = best_crop = best_crop_size(oxs, oys, 1920,1080)
      cx = int(np.mean(oxs))
      cy = int(np.mean(oys))
      cx1 = int(cx - (cw/2))
      cy1 = int(cy - (ch/2))
      cx2 = int(cx1 + cw)
      cy2 = int(cy1 + ch)

      #cv2.rectangle(cframe, (cx1, cy1), (cx2, cy2), (255,255,255), 2, cv2.LINE_AA)
      #cv2.imshow('pepe', cframe)
      #cv2.waitKey(0)
      #print("BEST CROP:", best_crop)
      hd_crop = [cx1,cy1,cx2,cy2] 
      return(objects, hd_crop)
   else:
      print("MANY OBJECTS.")
      for obj in objects:
         return(objects[obj], hd_crop)


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
