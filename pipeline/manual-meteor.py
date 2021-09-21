#!/usr/bin/python3
import datetime
from tabulate import tabulate
import sys
import numpy as np
from lib.PipeUtil import load_json_file, save_json_file, cfe, convert_filename_to_date_cam
from lib.PipeDetect import get_contours_in_image, find_object, analyze_object
from PIL import ImageFont, ImageDraw, Image, ImageChops
import os
import glob

import cv2

json_conf = load_json_file("../conf/as6.json")
show = 0

def menu():
   print("""
      1) Detect/Reduce and Import meteor-clip into the system

   """)
   cmd = input("Select command")

   if cmd == "1":
      man_detect(None)

def stack_stack(new_frame, stack_frame):
   pic1 = Image.fromarray(new_frame)
   pic2 = Image.fromarray(stack_frame)
   stacked_image=ImageChops.lighter(pic1,pic2)
   return(np.asarray(stacked_image))

def scan_meteor_video(meteor_video_file):
   mfn = meteor_video_file.split("/")[-1]
   print("Manual Meteor Scan")
   
   man_dir = "/mnt/ams2/MANUAL/" + mfn.replace(".mp4", "") + "/" 
   mjf = man_dir + mfn.replace(".mp4",".json") 
   stack_file = man_dir + mfn.replace(".mp4","-stacked.jpg") 
   stack_file_tn = man_dir + mfn.replace(".mp4","-stacked-tn.jpg") 
   if cfe(man_dir + mfn.replace(".mp4",".json")) == 1:
      mj = load_json_file (man_dir + mfn.replace(".mp4",".json"))
   else:

      print("This program allows remote scanning (other peoples station file). Please enter the AMSID for the station associated with the file you are working with.")
      station_id = input("Enter the station ID associated with this capture.")
      mj = {}
      mj['station_id'] = station_id
      mj['source_file'] = meteor_video_file
   if cfe(man_dir,1) == 0:
      os.makedirs(man_dir)
   if cfe(man_dir + mfn) == 0:
      os.system("cp " + meteor_video_file + " " + man_dir)
   meteor_video_file = man_dir + mfn
   mj['meteor_video_file'] = meteor_video_file 

   if "frame_data" not in mj: 

      cap = cv2.VideoCapture(meteor_video_file)
      objects = {}
      fc = 0
      active_mask = None
      small_mask = None
      thresh_adj = 0
      grabbed = True
      last_frame = None
      stacked_frame = None
      frame_data = {}
      fc = 0
      avgs = []
      sums = []
      HD = 0
      while grabbed is True:
         grabbed , frame = cap.read()

         if not grabbed :
            break
         if last_frame is None:
            last_frame = frame
         if stacked_frame is None:
            stacked_frame = frame


         sub = cv2.subtract(frame,stacked_frame)
         gray = cv2.cvtColor(sub, cv2.COLOR_BGR2GRAY)
         avg_sub = int(np.mean(sub))
         avgs.append(avg_sub)
         if len(avgs) < 50:
            thresh_val = int(np.mean(avgs))
         else:
            thresh_val = int(np.mean(avgs[:-40]))
         thresh_val = thresh_val * .3
         if thresh_val < 20:
            thresh_val = 20
         _, threshold = cv2.threshold(gray.copy(), thresh_val, 255, cv2.THRESH_BINARY)
         cnts = get_contours_in_image(threshold)
         if show == 1:
            cv2.imshow('stack', stacked_frame)
            cv2.imshow('thresh', threshold)
            cv2.imshow('orig', frame)
            cv2.imshow('sub', sub)
            cv2.waitKey(30)
         stacked_frame = stack_stack(frame,stacked_frame)
         frame_data[fc] = {}
         if len(cnts) > 0 and len(cnts) < 5:
            for cnt in cnts:
               x,y,w,h = cnt
               cnt_img = sub[y:y+h,x:x+w]
               cnt_int = int(np.sum(sub))
               cx = int(x + (w/2))
               cy = int(y + (h/2))
               object_id, objects = find_object(objects, fc,cx, cy, w, h, cnt_int, HD, 0, None)

            frame_data[fc]['cnts'] = cnts
         frame_data[fc]['sub_sum'] = int(np.sum(sub))
         if fc % 100 == 0:
            print("Proccessed...", fc)
         fc += 1


      mj['sd_wh'] = [last_frame.shape[1],last_frame.shape[0]]
      mj['frame_data'] = frame_data
      mj['objects'] = objects 
      cv2.imwrite(stack_file, stacked_frame) 
      stacked_frame_tn = cv2.resize(stacked_frame, (300,180))
      cv2.imwrite(stack_file_tn, stacked_frame_tn) 
   else:
      frame_data = mj['frame_data']
      objects = mj['objects']
      stacked_frame = cv2.imread(stack_file)
   save_json_file(mjf,mj)
   print("OBJECTS IN CLIP")

   if "choosen_object" not in mj:
      table_data = []
      table_header= ["CLASS", "OBJ ID", "FRAMES"]
      for obj in objects:
         if len(objects[obj]['ofns']) > 3:
            objects[obj] = analyze_object(objects[obj], 1,1)
            if objects[obj]['report']['meteor'] == 1:
               table_data.append(("METEOR", str(obj), str(objects[obj]['ofns'])))
            else:
               table_data.append(("NON METEOR", str(obj), str(objects[obj]['ofns'])))
      print(tabulate(table_data,headers=table_header))
      print("SELECT THE OBJECT YOU WANT TO CONFIRM AS METEOR.")
      print("If your meteor spans more then one object, enter the main ID.")
      good_obj = input("Enter the OBJECT ID of the meteor.")
      print(objects.keys())
      if good_obj in objects:
         meteor_obj = objects[good_obj]
      elif int(good_obj) in objects:
         meteor_obj = objects[int(good_obj)]
      else:
         print("Could not find the meteor obj")
         exit()

      mj['choosen_object'] = good_obj
      mj['meteor_obj'] = meteor_obj
      print("You selected:", good_obj)
      save_json_file(mjf,mj)
   else:
      meteor_obj = mj['meteor_obj']
   fw,fh = mj['sd_wh']

   print("Frames:", min(meteor_obj['ofns']), max(meteor_obj['ofns']))
   print("Xs:", min(meteor_obj['oxs']), max(meteor_obj['oxs']))
   print("Ys:", min(meteor_obj['oys']), max(meteor_obj['oys']))
   if "human_roi" in mj:
      x1,y1,x2,y2 = mj['human_roi']
   else:
      x1,y1,x2,y2 = get_roi(meteor_obj,fw,fh)
   print("X1",x1)
   print("Y2",y1)
   print("X2",x2)
   print("Y2",y2)
   if show == 1:
      show_stack = stacked_frame.copy() 
      cv2.rectangle(show_stack, (x1, y1), (x2,y2), (255, 255, 255), 1)
      cv2.imshow('pepe', show_stack)
      cv2.waitKey(0)
   print("CURRENT ROI:", x1,y1,x2,y2)
   good = "n"
   if "human_roi" not in mj:
      while good != "y":
         new_roi = input("New ROI? Press [ENTER] to use default. Otherwise enter new ROI values as X1,Y1,X2,Y2 exactly.")
         if new_roi != "":
            show_stack = stacked_frame.copy() 
            x1,y1,x2,y2 = new_roi.split(",")
            x1,y1,x2,y2 = int(x1),int(y1),int(x2),int(y2)
            print("NEW ROI", x1,y1,x2,y2 )
            show_stack = stacked_frame.copy() 
            cv2.rectangle(show_stack, (x1, y1), (x2,y2), (255, 255, 255), 1)
            cv2.imshow('pepe', show_stack)
            good = input("GOOD?")
            print("GOOD")
            cv2.waitKey(0)
         else:
            good = "y"
         mj['human_roi'] = [x1,y1,x2,y2]
   save_json_file(mjf,mj)

   print("INITIAL PROCESSING OF METEOR IS COMPLETED.")
   print("NOW WE WILL MAKE THE TRIM FILES.")
   print("TRIM START FRAME: ", meteor_obj['ofns'][0] - 25)
   print("TRIM END FRAME: ", meteor_obj['ofns'][-1] + 25)
   print("IF THIS LOOKS GOOD PRESS [ENTER] ELSE ENTER THE NEW START AND END FRAME")
   if "trim_start" not in mj:
      new_trim = input("[ENTER] to accept or new start end ")
      if new_trim == "":
         mj['trim_start'] = meteor_obj['ofns'][0] - 25
         mj['trim_end'] = meteor_obj['ofns'][-1] + 25
   sd_trim = meteor_video_file.replace(".mp4", "-trim-" + str(mj['trim_start']) + ".mp4") 
   mj['sd_trim'] = sd_trim
      
   if "sd_trim" not in mj:
      cmd = """ /usr/bin/ffmpeg -i """ + meteor_video_file + """ -vf select="between(n\,""" + str(mj['trim_start']) + """\,""" + str(mj['trim_end']) + """),setpts=PTS-STARTPTS" -y -update 1 -y """ + sd_trim + " >/dev/null 2>&1"
      print(cmd)
      os.system(cmd)
   print("SD TRIM FILE IS MADE.")

   # FIND IMPORT HD
   if "selected_hd" not in mj:
      mj['selected_hd'], hd_start,hd_end = find_hd(meteor_video_file)
   save_json_file(mjf,mj)
   if "hd_trim" not in mj:
      hd_fn = mj['selected_hd'].split("/")[-1]
      os.system("cp " + mj['selected_hd'] + " " + man_dir + hd_fn )
      if hd_start is not None:
         hd_trim = mj['selected_hd'].replace(".mp4", "-trim-" + str(hd_start) + "-" + "HD-meteor.mp4")
         cmd = """ /usr/bin/ffmpeg -i """ + mj['selected_hd'] + """ -vf select="between(n\,""" + str(hd_start) + """\,""" + str(hd_end) + """),setpts=PTS-STARTPTS" -y -update 1 -y """ + hd_trim + """ >/dev/null 2>&1"""
         print(cmd)
         os.system(cmd)
         mj['hd_trim'] = hd_trim
      else:
         mj['hd_trim'] = mj['selected_hd']
   save_json_file(mjf, mj)

   # calib
   if "cp" not in mj:
      apply_calib(mj)

def apply_calib(mj):
   print(mj.keys())
   (f_datetime, cam_id, f_date_str,fy,fmon,fd, fh, fm, fs) = convert_filename_to_date_cam(mj['sd_trim'])
   mj['cam_id'] = cam_id
   if mj['station_id'] == json_conf['site']['ams_id']:
      print("We are working on a local file, so we will use the local calibration.")
      local = 1
   else:
      print("This is a remote file. We need the calibration info before proceeding!")
      local = 0
   if local == 1:
      cal_day_hist_file = "/mnt/ams2/CAL/" + mj['station_id'] +  "_cal_range.json"
      mcp_file = "/mnt/ams2/CAL/multi_poly-" + mj['station_id'] +  "-" + cam_id + ".info"
      if cfe(cal_day_hist_file) == 0:
         print("Cal day hist file not found! Need to run cal manager to create defaults.", cal_day_hist_file)
      else:
         cal_hist = load_json_file(cal_day_hist_file)
      if cfe(mcp_file) == 0:
         print("MCP File does not exist. Need to make it before doing this. Run deep_cal", mcp_file)
      else:
         mcp = load_json_file(mcp_file)
   


   print("Trying to calibrate:", mj['station_id'], mj['cam_id'])
   find_default_cal(mj['station_id'], cam_id, cal_hist, f_datetime)

def find_default_cal(station_id, cam_id, cal_hist, meteor_date):
   cp = {}
   print("Finding best cal...")
   for row in cal_hist:
      if cam_id == row[0]:
         cal_end = datetime.datetime.strptime(row[1], "%Y_%m_%d")
         cal_start = datetime.datetime.strptime(row[2], "%Y_%m_%d")
         time_diff = (meteor_date - cal_end).total_seconds() / 86400
         print(time_diff, meteor_date, cal_end, cal_start)

def make_mj_mjr(man_mj):
   print("MAKE FINAL MJ FILES")

def find_hd(meteor_video_file):
   mfn = meteor_video_file.split("/")[-1]
   min_file = mfn.split("-trim")[0].replace(".mp4", "")
   el = min_file.split("_")
   hd_wild = min_file[0:18]
   print("LOOK FOR HD MATCHING ", hd_wild)

   # look in 3 places:
   # existing meteor dir
   # proc2/SD/YYYY_MM_DD/hd_save
   # ams2/HD
   md_files = glob.glob("/mnt/ams2/meteors/" + hd_wild[0:10] + "/" + hd_wild + "*HD*.mp4")
   proc_files = glob.glob("/mnt/ams2/SD/proc2/" + hd_wild[0:10] + "/hd_save/" + hd_wild + "*HD*.mp4")
   hd_min_files = glob.glob("/mnt/ams2/HD/" + hd_wild + "*.mp4")
   print("POSSIBLE HD FILES MATCHING:")
   print("METEOR DIR:", md_files)
   print("PROC DIR:", proc_files)
   print("HD DIR:", hd_min_files)
   fc = 0
   all_hd = []
   if len(md_files) > 0:
      for mf in md_files :
         print(fc, mf)
         all_hd.append(mf)
         fc += 1
   if len(proc_files) > 0:
      for mf in proc_files :
         print(fc, mf)
         all_hd.append(mf)
         fc += 1
   if len(hd_min_files) > 0:
      for mf in hd_min_files:
         print(fc, mf)
         all_hd.append(mf)
         fc += 1

   if fc > 0:
      selected_hd = input("Select the HD file.")
      selected_hd = all_hd[int(selected_hd)]
   else:
      print("NO ASSOCIATED HD FILES COULD BE FOUND.")

   if "trim" not in selected_hd:
      print("It looks like you have choosen a minute long HD. We need to split it before importing.")
      hd_trn = input("Enter the start and end trim frame numbers separated with space. (These should be close to the same as the SD)")
      hd_start,hd_end = hd_trn.split(" ")
   else:
      hd_start = None
      hd_end = None

   return(selected_hd, hd_start, hd_end)

      

def get_roi(meteor_obj,fw,fh):
   x1 = min(meteor_obj['oxs'])
   x2 = max(meteor_obj['oxs'])
   y1,y2 = min(meteor_obj['oys']), max(meteor_obj['oys'])
   x1 -= int(x1 * .15)
   x2 += int(x2 * .15)
   y1 -= int(y1 * .15)
   y2 += int(y2 * .15)
   w = x2 - x1
   h = y2 - y1
   if x1 < 0:
      x1 = 0
      x2 = w
   if y1 < 0:
      y1 = 0
      y2 = h
   if x2 >= fw:
      x2 = fw-1
      x1 = fw-w-1
   if y2 >= fh:
      y2 = fh-1
      y1 = fh-h-1
   return(x1,y1,x2,y2)


def man_detect(meteor_video_file):
   if meteor_video_file is None:
      meteor_video_file = input("Enter the full path and filename to the minute file or meteor trim file you want to import.")
   if cfe(meteor_video_file) == 1:
      print("found file.", meteor_video_file)  
      data = scan_meteor_video(meteor_video_file)

if len(sys.argv) > 1:
   man_detect(sys.argv[1])
else:
   menu()
