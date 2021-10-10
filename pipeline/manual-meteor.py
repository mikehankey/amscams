#!/usr/bin/python3
from PIL import Image, ImageDraw, ImageFont
import math
import json
from RMS.Math import angularSeparation
VIDEO_FONT = "/home/ams/amscams/dist/fonts/Roboto_Condensed/RobotoCondensed-Regular.ttf"
VIDEO_FONT_BOLD = "/home/ams/amscams/dist/fonts/Roboto_Condensed/RobotoCondensed-Bold.ttf"
VIDEO_FONT_SIZE = 25
VIDEO_FONT_SMALL_SIZE = 16 # For Radiant
VIDEO_FONT_SMALL_COLOR = (250,250,209,255) # For Radiant

import datetime
from tabulate import tabulate
import sys
import numpy as np
from lib.PipeUtil import load_json_file, save_json_file, cfe, convert_filename_to_date_cam
from lib.PipeDetect import get_contours_in_image, find_object, analyze_object
from lib.PipeAutoCal import update_center_radec, get_image_stars, pair_stars, distort_xy, AzEltoRADec,HMS2deg, minimize_fov, XYtoRADec
from lib.FFFuncs import ffprobe
from PIL import ImageFont, ImageDraw, Image, ImageChops
import os
import glob

import cv2

local_json_conf = load_json_file("../conf/as6.json")
show = 1
user_clicks = []
mouseX = 0
mouseY = 0

def menu(json_conf):
   print("""
      1) Detect/Reduce and Import meteor-clip into the system
      2) Review and Refine Meteor Data

   """)
   cmd = input("Select command")

   if cmd == "1":
      man_detect(None, json_conf)
   if cmd == "2":
      meteor_vid = input("Enter the full path to the SD Video file for the meteor you want to review.")
      review_meteor( meteor_vid)

def review_meteor(meteor_vid):
   meteor_json_file = meteor_vid.replace(".mp4", ".json")
   print(meteor_json_file)
   man_json = load_json_file(meteor_json_file)
   for key in man_json:
      print(key)

   print("Select sub command.")
   print("1) Review/refine astrometry.")
   print("2) Review/refine points.")
   print("3) Create/Play 'debug' video .")
   cmd = input("Enter Command")
   if cmd == "3":
      debug_video(meteor_vid, man_json)

def debug_video(meteor_vid, man_json):
   global user_clicks
   global user_frames
   global frames 
   global f
   man_mjf = meteor_vid.replace(".mp4", ".json")
   sd_vid = man_json['sd_trim'] 
   hd_vid = man_json['hd_trim']
   channel_img = sd_vid.replace(".mp4","-channel.jpg")
   channel_mask = cv2.imread(channel_img)
   channel_mask_hd = cv2.resize(channel_mask, (1920,1080))
   print(sd_vid)
   print(hd_vid)
   use_hd = 0
   if cfe(hd_vid) == 1:
      use_hd = input("Use HD Video? [ENTER] for yes [N] for no.")
      if use_hd == "":
         use_hd = 1
   if use_hd == 1:
      meteor_video_file = man_json['hd_trim']
   else:
      meteor_video_file = man_json['sd_trim']

   cap = cv2.VideoCapture(meteor_video_file)

   grabbed = True
   last_frame = None
   stacked_frame = None

   frames = []
   if True:
      while grabbed is True:
         grabbed , frame = cap.read()
         if not grabbed :
            break
         frames.append(frame)

   quit = False
   f = 0

   fh, fw = frames[0].shape[:2]
   mfda = man_json['meteor_frame_data']
   mfd = {}
   for row in mfda:
      (frame_time_str, fn, hd_x, hd_y, sd_w, sd_h, oint, ra, dec, az, el) = row
      mfd[fn] = row

   cv2.namedWindow('pepe')
   cv2.setMouseCallback('pepe',draw_circle)

   user_frames = {}
   user_clicks = []
   f = 0

   desc = None
   color = [0,0,255]
   if "user_frames" in man_json:
      user_frames = man_json['user_frames']
   while quit == False:
      hd_x = None
      frame = frames[f].copy()
      if f in mfd and f not in user_frames:
         mfd_row = mfd[f]
         print("MFD FRAME FOUND!")
         (frame_time_str, fn, hd_x, hd_y, sd_w, sd_h, oint, ra, dec, az, el) = mfd_row
         color = [0,0,255]
      elif f in user_frames:
         hd_x,hd_y = user_frames[f]
         print("USER FRAME FOUND!")
         color = [0,255,0]

      if hd_x is not None:
         frame = draw_frame(frame, f, desc,hd_x,hd_y,color)
      cv2.putText(frame, "FN: " + str(f) ,  (25, fh - 25), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 200, 200), 1)
      cv2.imshow('pepe', frame)
      key = cv2.waitKey(0)

      print(f, key, user_frames)
      if key == 113:
         exit()
      if key == 97:
         f = f - 1
         if f < 0 : 
            f = 0
         frame = frames[f].copy()
         frame = draw_frame(frame, f, desc,hd_x,hd_y,color)
     #    cv2.imshow('pepe', frame)
         print("SHOWING FRAME:", f)
      if key == 102:
         f = f + 1
         if f >= len(frames) - 1 : 
            f = 0
         frame = frames[f].copy()
         frame = draw_frame(frame, f, desc,hd_x,hd_y,color)
     #    cv2.imshow('pepe', frame)
         print("SHOWING FRAME:", f)
      if key == 115:
         print("SAVE!")
         man_json['user_frames'] = user_frames
         save_json_file(man_mjf, man_json)

         user_clicks = []

def draw_frame(frame, f, desc, x, y,color):
   if x is not None:
      cv2.circle(frame,(int(x),int(y)), 3, color, 1)
   fh,fw = frame.shape[:2]
   cv2.putText(frame, "FN: " + str(f) ,  (25, fh - 25), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 200, 200), 1)
   return(frame)
   

def draw_circle(event,x,y,flags,param):
    global user_clicks
    global frames 

    global f
    global user_frames
    global mouseX,mouseY
    if event == cv2.EVENT_LBUTTONDBLCLK:
        #cv2.circle(frame,(x,y),100,(255,0,0),-1)
        mouseX,mouseY = x,y   
        user_clicks.append((x,y))
        frame = frames[f].copy()
        user_frames[f] = [x,y]
        fh,fw = frame.shape[:2]
        color = [0,255,0]
        frame = draw_frame(frame, f, None,x,y,color)
        #cv2.circle(frame,(int(x),int(y)), 3, (0,255,0), 1)
        #cv2.putText(frame, "FN: " + str(f) ,  (25, fh - 25), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 200, 200), 1)
        cv2.imshow('pepe', frame)
        #key = cv2.waitKey(0)

        print("CALLBACK:", frames[f], mouseX,mouseY)


def stack_stack(new_frame, stack_frame):
   pic1 = Image.fromarray(new_frame)
   pic2 = Image.fromarray(stack_frame)
   stacked_image=ImageChops.lighter(pic1,pic2)
   return(np.asarray(stacked_image))


def make_az_grid(cal_image, mj,json_conf):
   az_lines = []
   el_lines = []
   points = []
   cp = mj['cp']
   grid_img = np.zeros((1080,1920,3),dtype=np.uint8)
   flen = 4
   if flen == 8:
      wd = 40
      hd = 20
   else:
      wd = 80
      hd = 30

   if cp['center_el'] > 70:
     start_el = 30
     end_el = 89.8
     start_az = 0
     end_az = 355
   else:
      start_az = cp['center_az'] - wd
      end_az = cp['center_az'] + wd
      start_el = cp['center_el'] - hd
      end_el = cp['center_el'] + hd
      print("USING:" , start_az, end_az, cp['center_az'], wd)
      if start_el < 0:
         start_el = 0
      if end_el >= 90:
         end_el = 89.7

      if cp['center_az'] - wd < 0:
         start_az = cp['center_az'] -wd
         end_az = start_az + (wd * 2)
   print("GRID CENTER AZ:", cp['center_az'])
   print("GRID CENTER EL:", cp['center_el'])
   print("GRID START/END AZ:", start_az, end_az)
   print("GRID START/END EL:", start_el, end_el)
   print("CP PIXSCALE:", cp['pixscale'])
   F_scale = 3600/float(cp['pixscale'])

   for az in range(int(start_az),int(end_az)):
      if az >= 360:
         az = az - 360

      for el in range(int(start_el),int(end_el)+30):
         if az % 10 == 0 and el % 10 == 0:

            rah,dech = AzEltoRADec(az,el,mj['sd_trim'],cp,json_conf)
            rah = str(rah).replace(":", " ")
            dech = str(dech).replace(":", " ")
            ra,dec = HMS2deg(str(rah),str(dech))
            new_cat_x, new_cat_y = distort_xy(0,0,ra,dec,cp['ra_center'], cp['dec_center'], cp['x_poly'], cp['y_poly'], float(cp['imagew']), float(cp['imageh']), cp['position_angle'],F_scale)
            new_cat_x,new_cat_y = int(new_cat_x),int(new_cat_y)
            #print("F_SCALE/AZ/EL/RA/DEC/X/Y", cp['pixscale'], F_scale, az,el,ra,dec,new_cat_x,new_cat_y)
            if new_cat_x > -200 and new_cat_x < 2420 and new_cat_y > -200 and new_cat_y < 1480:
               cv2.rectangle(grid_img, (new_cat_x-2, new_cat_y-2), (new_cat_x + 2, new_cat_y + 2), (128, 128, 128), 1)
               if new_cat_x > 0 and new_cat_y > 0:
                  az_lines.append(az)
                  el_lines.append(el)
               points.append((az,el,new_cat_x,new_cat_y))


   pc = 0
   show_el = {}
   show_az = {}
   center_az = cp['center_az']
   for el in range (0,90):
      if el % 10 == 0:
         if el not in show_el:
            grid_img = draw_grid_line(points, grid_img, "el", el, cp['center_az'], cp['center_el'], 1)
   for az in range (0,360):
      if az % 10 == 0:
         grid_img = draw_grid_line(points, grid_img, "az", az, cp['center_az'], cp['center_el'], 1)


   # add 1 degree lines

   points = []
   for az in range(int(start_az),int(end_az)):
      if az >= 360:
         az = az - 360

      for el in range(int(start_el),int(end_el)+30):
         if az % 1 == 0 and el % 1 == 0:

            rah,dech = AzEltoRADec(az,el,mj['sd_trim'],cp,json_conf)
            rah = str(rah).replace(":", " ")
            dech = str(dech).replace(":", " ")
            ra,dec = HMS2deg(str(rah),str(dech))
            new_cat_x, new_cat_y = distort_xy(0,0,ra,dec,cp['ra_center'], cp['dec_center'], cp['x_poly'], cp['y_poly'], float(cp['imagew']), float(cp['imageh']), cp['position_angle'],F_scale)
            new_cat_x,new_cat_y = int(new_cat_x),int(new_cat_y)
            print("F_SCALE/AZ/EL/RA/DEC/X/Y", cp['pixscale'], F_scale, az,el,ra,dec,new_cat_x,new_cat_y)
            if new_cat_x > -200 and new_cat_x < 2420 and new_cat_y > -200 and new_cat_y < 1480:
               #cv2.rectangle(grid_img, (new_cat_x-2, new_cat_y-2), (new_cat_x + 2, new_cat_y + 2), (128, 128, 128), 1)
               if new_cat_x > 0 and new_cat_y > 0:
                  az_lines.append(az)
                  el_lines.append(el)
               points.append((az,el,new_cat_x,new_cat_y))
   for el in range (0,90):
      if el % 1 == 0:
         if el not in show_el:
            grid_img = draw_grid_line(points, grid_img, "el", el, cp['center_az'], cp['center_el'], 0)
   for az in range (0,360):
      if az % 1 == 0:
         grid_img = draw_grid_line(points, grid_img, "az", az, cp['center_az'], cp['center_el'], 0)

   # end 1 degree lines


   #cv2.imshow('grid', grid_img)
   #cv2.waitKey(0)
   cal_image = cv2.resize(cal_image, (1920,1080))
   blend_image = cv2.addWeighted(cal_image, .7, grid_img, .3,0) 
   #cv2.imshow('grid', blend_image)
   #cv2.waitKey(0)
   return(grid_img, blend_image)

def draw_grid_line(points, img, type, key, center_az, center_el, show_text = 1):
   pc = 0

   if type == 'el':
      for point in points:
         az,el,x,y = point
         if el == key:

            print("DRAW EL:", el)
            if pc > 0 :
               if el % 10 == 0:
                  cv2.line(img, (x,y), (last_x,last_y), (255,255,255), 2)
               else:
                  cv2.line(img, (x,y), (last_x,last_y), (128,128,128), 1)
               if (center_az - 5 <= az <=  center_az + 5) and show_text == 1: 
                  desc = str(el)
                  cv2.putText(img, desc,  (x+3,y+15), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)

            last_x = x
            last_y = y
            pc = pc + 1

   if type == 'az':
      min_el = center_el - 22
      if min_el <= 9:
         min_el = 0
      else:
         min_el = int(str(center_el - 22)[0] + "0")
      print("MIN EL:", min_el)
      pc = 0
      for point in points:
         az,el,x,y = point
         if az == key:
            #print("KEY/POINT/PC:", key, point,pc)
            if pc > 0 :
               if az % 10 == 0:
                  cv2.line(img, (x,y), (last_x,last_y), (255,255,255), 2)
               else:
                  cv2.line(img, (x,y), (last_x,last_y), (128,128,128), 1)
               print("THIS EL:", el)
            if (min_el - 5 <= el <= min_el + 5) and show_text == 1:
               desc = str(az)
               cv2.putText(img, desc,  (x+5,y-5), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
            last_x = x
            last_y = y
            pc = pc + 1
   return(img )



def scan_meteor_video(meteor_video_file,json_conf,mj = None, station_id = None):
   mfn = meteor_video_file.split("/")[-1]
   print("Manual Meteor Scan")
   if station_id is None:
      station_id = input("Enter the station ID associated with this capture.")
   man_dir = "/mnt/ams2/MANUAL/" + station_id + "_" + mfn.replace(".mp4", "") + "/" 

   mjf = man_dir + mfn.replace(".mp4",".json") 
   stack_file = man_dir + mfn.replace(".mp4","-stacked.jpg") 
   stack_file_tn = man_dir + mfn.replace(".mp4","-stacked-tn.jpg") 
   if cfe(man_dir + mfn.replace(".mp4",".json")) == 1 and mj is None:
      mj = load_json_file (man_dir + mfn.replace(".mp4",".json"))
   else:
      if mj is None:
         print("This program allows remote scanning (other peoples station file). Please enter the AMSID for the station associated with the file you are working with.")
         if station_id is None:
            station_id = input("Enter the station ID associated with this capture.")
         mj = {}
         mj['station_id'] = station_id
         mj['source_file'] = meteor_video_file
   mj['man_dir'] = man_dir
   if cfe(man_dir,1) == 0:
      os.makedirs(man_dir)
   if cfe(man_dir + mfn) == 0:
      os.system("cp " + meteor_video_file + " " + man_dir)

   if mj['station_id'] == json_conf['site']['ams_id']:
      print("We are working on a local file, so we will use the local calibration.")
      local_json_conf = json_conf
      local = 1
      remote = 0
   else:
      print("This is a remote file. We need the calibration info before proceeding!")
      remote_cal_dir = "/mnt/ams2/MANUAL/REMOTE_CAL/" + mj['station_id'] + "/"
      local = 0
      remote = 1
      if cfe("/mnt/archive.allsky.tv/" + mj['station_id'] + "/CAL/as6.json") == 0:
         print("There is no remote json_conf for this staion!", station_id)
         print("Copy the stations as6.json to: /mnt/archive.allsky.tv/" + station_id + "/CAL/as6.json")
         cmd = "cp /mnt/archive.allsky.tv/" + station_id + "/CAL/as6.json " + mj['man_dir'] + mj['station_id'] + "_conf.json"
         os.system(cmd)
         cmd = "cp /mnt/archive.allsky.tv/" + station_id + "/CAL/as6.json " + remote_cal_dir
         os.system(cmd)
      else:
         print("/mnt/archive.allsky.tv/" + mj['station_id'] + "/CAL/as6.json was found.") 
         cmd = "cp /mnt/archive.allsky.tv/" + station_id + "/CAL/as6.json " + mj['man_dir'] + mj['station_id'] + "_conf.json"
         os.system(cmd)
         cmd = "cp /mnt/archive.allsky.tv/" + station_id + "/CAL/as6.json " + remote_cal_dir
         os.system(cmd)

      json_conf = load_json_file(remote_cal_dir + "as6.json")
      print("REMOTE JSON CONF LOADED!")
      for key in json_conf['site']:
         print(key, json_conf['site'][key])
   input("CHECK JSON CONF VARS!")
   if "trim" in meteor_video_file:
      mj['using_trim_src'] = 1
   else:
      mj['using_trim_src'] = 0




   meteor_video_file = man_dir + mfn
   mj['meteor_video_file'] = meteor_video_file 
   mj['man_dir'] = man_dir

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
   mj['roi'] = [x1,y1,x2,y2]
   hdm_x = 1920 / stacked_frame.shape[1] 
   hdm_y = 1080 / stacked_frame.shape[0] 
   mj['hd_roi'] = [int(x1 * hdm_x), int(y1 * hdm_y), int(x2 * hdm_x), int(y2 * hdm_y)]
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
            if show == 1:
               cv2.rectangle(show_stack, (x1, y1), (x2,y2), (255, 255, 255), 1)
               cv2.imshow('pepe', show_stack)
               cv2.waitKey(0)
            good = input("GOOD?")
            print("GOOD")
         else:
            good = "y"
         mj['human_roi'] = [x1,y1,x2,y2]
   save_json_file(mjf,mj)

   print("INITIAL PROCESSING OF METEOR IS COMPLETED.")
   print("NOW WE WILL MAKE THE TRIM FILES.")
   print("TRIM START FRAME: ", meteor_obj['ofns'][0] - 25)
   print("TRIM END FRAME: ", meteor_obj['ofns'][-1] + 25)
   print("IF THIS LOOKS GOOD PRESS [ENTER] ELSE ENTER THE NEW START AND END FRAME")
   if mj['using_trim_src'] == 1:
      if "trim_start" not in mj:

         w,h,br,frames = ffprobe(meteor_video_file)
         print("There are ", frames, " in the clip.")
         new_trim = input("[ENTER] to accept or new start end ")
         if new_trim == "":
            mj['trim_start'] = meteor_obj['ofns'][0] - 25
            mj['trim_end'] = meteor_obj['ofns'][-1] + 25
         else:
            mj['trim_start'], mj['trim_end']  = new_trim.split(" ")
   else:
      print("Already have a trim file.")

   if mj['using_trim_src'] == 1:
      sd_trim = meteor_video_file 
   else:
      sd_trim = meteor_video_file.replace(".mp4", "-trim-" + str(mj['trim_start']) + ".mp4") 
   mj['sd_trim'] = sd_trim
     

   if "sd_trim" not in mj:
      cmd = """ /usr/bin/ffmpeg -i """ + meteor_video_file + """ -vf select="between(n\,""" + str(mj['trim_start']) + """\,""" + str(mj['trim_end']) + """),setpts=PTS-STARTPTS" -y -update 1 -y """ + sd_trim + " >/dev/null 2>&1"
      print(cmd)
      if mj['using_trim_src'] == 0:
         os.system(cmd)
   elif cfe(mj['sd_trim']) == 0:
      cmd = """ /usr/bin/ffmpeg -i """ + meteor_video_file + """ -vf select="between(n\,""" + str(mj['trim_start']) + """\,""" + str(mj['trim_end']) + """),setpts=PTS-STARTPTS" -y -update 1 -y """ + sd_trim + " >/dev/null 2>&1"
      print(cmd)
      os.system(cmd)
   print("SD TRIM FILE IS MADE.")

   # FIND IMPORT HD
   if "selected_hd" not in mj  :
      mj['selected_hd'], hd_start,hd_end = find_hd(meteor_video_file, mj)
      if mj['selected_hd'] == "" or mj['selected_hd'] is None:
         print(mj.keys())
         print("NO HD FILE FOUND/LINKED TO THIS EVENT. ")
         mj['selected_hd'] = input("enter full path of HD file or [ENTER] to skip.")
         if mj['selected_hd'] != "" : 
            mj['hd_trim'] = None
   if mj['selected_hd'] != "" and "start_hd_trim" not in mj :
      mj = man_clip_hd(mj['selected_hd'], mj)
   save_json_file(mjf,mj)
   if "hd_trim" not in mj and mj['selected_hd'] is not None:
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
   # GET 1st frame of trim for calibration and subtraction
   first_file = stack_file.replace("-stacked.jpg", "-first.jpg")
   first_trim_img = get_first_trim_img(mj['sd_trim'])
   if first_trim_img is not None:
      first_trim_img = cv2.resize(first_trim_img, (1920,1080))
      star_img = first_trim_img
      cv2.imwrite(first_file, first_trim_img)
   else:
      star_img = cv2.resize(stacked_frame, (1920,1080))


   #if "cp" not in mj:
   mj['cp'],json_conf = get_calib(mj,json_conf)
  
   mj['cp']['user_stars'] = get_image_stars(mj['sd_trim'], star_img, json_conf,0)
   print("USER STARS:", len(mj['cp']['user_stars']))
   good_user_stars = []
   for x,y,i in mj['cp']['user_stars']:
      if 100 <= y <= 980 and 100 <= x <= 1820:
         good_user_stars.append((x,y,i))
   mj['cp']['user_stars'] = good_user_stars

   mj['cp'] = pair_stars(mj['cp'], mj['sd_trim'], json_conf, star_img)

   for x,y,i in mj['cp']['user_stars']:
      cv2.rectangle(star_img, (int(x-5), int(y-5)), (int(x+5) , int(y+5)), (255, 255, 255), 1)
   all_dist = []

   all_res = [row[-2] for row in mj['cp']['cat_image_stars']]
   med_res = np.median(all_res)
   good_cat = []



   for row in mj['cp']['cat_image_stars']:
      print("CS:", row)
      (name,mag,ra,dec,ra,dec,match_dist,new_cat_x,new_cat_y,trash1,trash2,new_cat_x,new_cat_y,six,siy,cat_dist,star_int) = row
      print(type(name))
      print("MED RES/CAT DIST:", med_res, cat_dist)
      if cat_dist <= med_res * 1.1 and 200 <= new_cat_y <= 780 and 200 <= new_cat_x <= 1620:
         good_cat.append(row)

   if len(good_cat) > 8:
      # refit the field
      if "refit" not in mj:
         mj['cp'] = minimize_fov(mj['sd_trim'], mj['cp'], mj['sd_trim'] ,star_img,json_conf )
         del(mj['cp']['short_bright_stars'])
         if "no_match_stars" in mj:
            del(mj['no_match_stars'])
         mj['refit'] = 1

 

   save_json_file("test.json", mjf)

   if len(good_cat) > 0:
      mj['cp']['cat_image_stars'] = good_cat
   for row in mj['cp']['cat_image_stars']:
      (name,mag,ra,dec,ra,dec,match_dist,new_cat_x,new_cat_y,trash1,trash2,new_cat_x,new_cat_y,six,siy,cat_dist,star_int) = row
      all_dist.append(cat_dist)
      cv2.rectangle(star_img, (int(new_cat_x-5), int(new_cat_y-5)), (int(new_cat_x+5) , int(new_cat_y+5)), (128, 128, 255), 1)
      cv2.line(star_img, (new_cat_x,new_cat_y), (int(six),int(siy)), (100,100,100), 1)
   #   cv2.putText(star_img, name,  (new_cat_x, new_cat_y), cv2.FONT_HERSHEY_SIMPLEX, .5, (200, 200, 200), 1)

   # Draw star names
   # use DEFAULT truetype font
   bold = False
   if(bold==True):
      font = ImageFont.truetype(VIDEO_FONT_BOLD, VIDEO_FONT_SMALL_SIZE)
   else:
      font = ImageFont.truetype(VIDEO_FONT, VIDEO_FONT_SMALL_SIZE)
   pil_im = Image.fromarray(star_img)
   draw = ImageDraw.Draw(pil_im)
   for row in mj['cp']['cat_image_stars']:
      (name,mag,ra,dec,ra,dec,match_dist,new_cat_x,new_cat_y,trash1,trash2,new_cat_x,new_cat_y,six,siy,cat_dist,star_int) = row
      draw.text((new_cat_x, new_cat_y), name, font=font, fill="white")

   star_img = cv2.cvtColor(np.array(pil_im), cv2.COLOR_RGB2BGR)

   avg_res = float(np.mean(all_dist))

   if avg_res > 5:
      cv2.putText(star_img, "AVG RES: " + str(round(avg_res,2)) + " IS BAD. NO GOOD STARS OR BAD CALIB. USING DEFAULT CAL PARAMS.",  (20, 1050), cv2.FONT_HERSHEY_SIMPLEX, .5, (0, 0, 255), 1)
      mj['cp']['no_stars'] = 1
      mj['cp']['attempt_res'] = avg_res
      mj['cp']['use_default'] = 1
      mj['cat_image_stars'] = []
      mj['user_stars'] = []
   else:
      cv2.putText(star_img, "AVG RES: " + str(round(avg_res,2)) ,  (20, 1050), cv2.FONT_HERSHEY_SIMPLEX, .5, (0, 255, 0), 1)
      print("STARS AND RES FOR THIS METEOR FILE ARE ACCEPTABLE.")
      print("NOW WE CAN CUSTOM FIT THE CALIBRATION IF WE HAVE ENOUGH STARS.")
   if show == 1:
      cv2.imshow('pepe', star_img)
      cv2.waitKey(0)


   print("FINAL CP:")
   for field in mj['cp']:
      print(field, mj['cp'][field])
   for key in json_conf['site']:
      print(key, json_conf['site'][key])
   input()
   if mj['cp'] is None:
      print("Calparams not found:", mj['cp']) 

   else:
      print("Calparams found:", mj['cp']) 

   # make grid
   star_img_file = stack_file.replace("-stacked.jpg", "-stars.jpg")
   grid_img_file = stack_file.replace("-stacked.jpg", "-grid.jpg")
   blend_img_file = stack_file.replace("-stacked.jpg", "-blend.jpg")
   if cfe(grid_img_file) == 0:
      grid_image, blend_image = make_az_grid(stacked_frame, mj, json_conf)
   else:
      grid_image = cv2.imread(grid_img_file)
      blend_image = cv2.imread(blend_img_file)

   blend_image = cv2.addWeighted(blend_image, .8, star_img, .2,0) 
   star_img = cv2.addWeighted(star_img, .8, grid_image, .2,0) 

   cv2.imwrite(grid_img_file, grid_image)
   cv2.imwrite(blend_img_file, blend_image)
   cv2.imwrite(star_img_file, star_img)



   print("MFD TIME")
   mj = make_mfd(mj,json_conf, stacked_frame)

   save_json_file(mjf, mj)
   f_mj, f_mjr = make_mj_mjr(mj)

   print("OK IT LOOKS LIKE JUST ABOUT EVERYTHING IS MADE AND READY TO IMPORT INT THE METEOR DB!")
   import_yn = input("Import meteor into main meteor repository for " + mj['station_id'] + "? [y]es or [ENTER] for No.")
   if True:
      if remote == 0:
         meteor_dir = "/mnt/ams2/meteors/" + mj['sd_trim'].split("/")[-1][0:10] + "/" 
      else:
         meteor_dir = "/mnt/ams2/MANUAL/" + mj['sd_trim'].split("/")[-1].replace(".mp4", "") + "/" 
      if cfe(meteor_dir,1) == 0:
         os.makedirs(meteor_dir)
      print("METEOR DIR:", meteor_dir)
      mfn = mj['sd_trim'].split("/")[-1]
      day = mj['sd_trim'].split("/")[-1][0:10]
      if remote == 0:
         mjf = meteor_dir + mfn.replace(".mp4", ".json")
      else:
         mjf = meteor_dir + mfn.replace(".mp4", "-f.json")
      mjrf = meteor_dir + mfn.replace(".mp4", "-reduced.json")
      if cfe(mjf) == 1 or cfe(mjrf) == 1:
         yn = input("This meteor aleady exists in the meteor DB, do you want to overwrite it?")
      else:
         yn = "y"
      if yn == "Y" or yn == "y" :
         save_json_file(mjf, f_mj) 
         save_json_file(mjrf, f_mjr) 
         # Also copy: sd_trim, hd_trim, sd_stack, hd_stack, stack_tn, stack_obj_tn
         cmd = "cp " + mj['sd_trim'] + " " + meteor_dir
         print(cmd)
         os.system(cmd)
         cmd = "cp " + mj['hd_trim'] + " " + meteor_dir
         print(cmd)
         os.system(cmd)
         cmd = "cp " + mj['sd_trim'].replace(".mp4", "-stacked.jpg") + " " + meteor_dir
         print(cmd)
         os.system(cmd)
         cmd = "cp " + mj['sd_trim'].replace(".mp4", "-stacked-tn.jpg") + " " + meteor_dir
         print(cmd)
         os.system(cmd)

         sd_stack_file = mj['sd_trim'].replace(".mp4", "-stacked.jpg") 
         if mj['hd_trim'] is not None and mj['hd_trim'] != "":
            hd_stack = meteor_dir + f_mj['hd_stack'].split("/")[-1]
            print("HD TRIM/STACK", mj['hd_trim'], hd_stack)
            if cfe(hd_stack) == 0:
               hd_stack_img = stack_vid(mj['hd_trim'])
               cv2.imwrite(hd_stack, hd_stack_img)
         sd_stack_img = stack_vid(mj['sd_trim'])
         cv2.imwrite(sd_stack_file, sd_stack_img)
         stacked_frame_tn = cv2.resize(sd_stack_img, (300,180))
         cv2.imwrite(sd_stack_file.replace(".jpg", "-tn.jpg"), sd_stack_img)

         # make tn obj
         obj_stack_file = mj['sd_trim'].replace(".mp4", "-stacked-obj-tn.jpg") 
         obj_stack = cv2.rectangle(stacked_frame, (x1,y1),(x2,y2), (255,255,255), 1)
         cv2.imwrite(obj_stack_file, obj_stack)
         cmd = "cp " + mj['sd_trim'].replace(".mp4", "-stacked-obj-tn.jpg") + " " + meteor_dir
         print(cmd)
         os.system(cmd)
         if mj['hd_trim'] is not None and mj['hd_trim'] != "":
            cmd = "cp " + mj['hd_trim'].replace(".mp4", "-stacked.jpg") + " " + meteor_dir
            print(cmd)
            os.system(cmd)
         if remote == 0:
            os.system("./Process.py mmi_day " + day)

   if remote == 1:
      print("SINCE THIS IS A REMOTE SYSTEM REDUCTION...")
      print("you must copy the mj and mjr files back to the host system.")
      print("To do this login to the remote system and run these commands.")
      local_jc = load_json_file("../conf/as6.json")
      local_station_id = local_jc['site']['ams_id']
      c_mjf = mjf.replace("ams2/", "archive.allsky.tv/" + local_station_id + "/")
      c_mjrf = mjrf.replace("ams2/", "archive.allsky.tv/" + local_station_id + "/")

      local_meteor_dir = "/mnt/ams2/meteors/" + mj['sd_trim'].split("/")[-1][0:10] + "/" 
      cloud_dir = "/mnt/archive.allsky.tv/" + local_station_id + "/MANUAL/" + mj['sd_trim'].split("/")[-1] + "/" 
      mjfn = mjf.split("/")[-1]
      lmjfn = mjfn.replace("-f.json", ".json") 
      cmd = "cp " + c_mjf + " " + local_meteor_dir + lmjfn
      print(cmd) 
      cmd = "cp " + c_mjrf + " " + local_meteor_dir
      print(cmd) 
      cmd = "cp " + cloud_dir + "* " + local_meteor_dir
      print("Or just copy everything.")
      print(cmd) 

def stack_vid(video):
   print("Stacking video:", video)
   if True:
      cap = cv2.VideoCapture(video)
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
      stack_frame = None
      while grabbed is True:
         grabbed , frame = cap.read()
         if not grabbed :
            break
         if stacked_frame is None:
            stacked_frame = frame
         stacked_frame = stack_stack(frame,stacked_frame)
   return(stacked_frame)

def scan_meteor_trim(trim_clip, json_conf, mj,save_file=None,channel_img=None):

   mfn = trim_clip.split("/")[-1]
   print("Manual Meteor Scan")
   man_dir = mj['man_dir']
   mjf = man_dir + mfn.replace(".mp4",".json") 
   stack_file = man_dir + mfn.replace(".mp4","-stacked.jpg") 
   stack_file_tn = man_dir + mfn.replace(".mp4","-stacked-tn.jpg") 
   out = None

   if True:
      cap = cv2.VideoCapture(trim_clip)
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
         if channel_img is not None and frame is not None:
            frame = cv2.subtract(frame,channel_img)
         if last_frame is None:
            mj['sd_h'], mj['sd_w'] = frame.shape[:2]
            last_frame = frame
            first_frame = frame
            if save_file is not None and out is None:
               fourcc = cv2.VideoWriter_fourcc(*'avc1')
               out = cv2.VideoWriter(save_file,fourcc, 25, (mj['sd_w'],mj['sd_h']))


         if stacked_frame is None:
            stacked_frame = frame

         sub = cv2.subtract(frame,stacked_frame)
         sub = cv2.subtract(frame,first_frame)

         gray = cv2.cvtColor(sub, cv2.COLOR_BGR2GRAY)
         avg_sub = int(np.mean(sub))
         avgs.append(avg_sub)
         min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(gray)
         thresh_val = max_val * .75 
         if thresh_val < 100:
            thresh_val = 100 
         _, threshold = cv2.threshold(gray.copy(), thresh_val, 255, cv2.THRESH_BINARY)
         cnts = get_contours_in_image(threshold)
         if show == 1:
            cv2.imshow('stack', stacked_frame)
            cv2.imshow('thresh', threshold)
            cv2.imshow('orig', frame)
            cv2.imshow('sub', sub)
            cv2.waitKey(30)
         stacked_frame = stack_stack(last_frame,stacked_frame)
         frame_data[fc] = {}
         show_frame = sub
         colors = [[0,0,255],[0,255,0],[255,0,0],[255,255,0],[0,255,255]]
         oc = {}
         oci = 0
         if len(cnts) > 0 and len(cnts) < 5:
            for cnt in cnts:
               x,y,w,h = cnt
               cnt_img = sub[y:y+h,x:x+w]
               cnt_int = int(np.sum(sub))
               cx = int(x + (w/2))
               cy = int(y + (h/2))
               object_id, objects = find_object(objects, fc,cx, cy, w, h, cnt_int, HD, 0, None)
               if object_id not in oc:
                  oc[object_id] = oci
                  oci += 1
                  if oci > len(colors):
                     oci = 0


               cv2.rectangle(show_frame, (x, y), (x+w,y+h), (255, 255, 255), 1)
               cv2.putText(show_frame, str(object_id),  (x, y), cv2.FONT_HERSHEY_SIMPLEX, .3, colors[oci], 1)

            frame_data[fc]['cnts'] = cnts
         frame_data[fc]['sub_sum'] = int(np.sum(sub))
         if fc % 100 == 0:
            print("Proccessed...", fc)
         last_frame = frame
         if save_file is not None:
            out.write(show_frame)
         fc += 1


      mj['sd_w'], mj['sd_h'] = [last_frame.shape[1],last_frame.shape[0]]
      mj['frame_data'] = frame_data
      mj['objects'] = objects
      if channel_img is None:
         cv2.imwrite(stack_file, stacked_frame)
         stacked_frame_tn = cv2.resize(stacked_frame, (300,180))
         cv2.imwrite(stack_file_tn, stacked_frame_tn)
   else:
      frame_data = mj['frame_data']
      objects = mj['objects']
      stacked_frame = cv2.imread(stack_file)
   save_json_file(mjf,mj)
   print("OBJECTS IN CLIP")
   if out is not None:
      out.release()
   if "trim_object" not in mj:
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

      choice = False 
      while choice is False:
         good_obj = input("Enter the OBJECT ID of the meteor.")
         try:
            good_obj = int(good_obj)
            choice = True
         except:
            print("Bad input try again.")

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
   return(meteor_obj, objects)

def cloud_copy(mj,json_conf):
   yes_no = input("Do you want to copy the output files to the cloud? [y]es or [ENTER] for no. ")
   local_json_conf = load_json_file("../conf/as6.json")
   local_station_id = local_json_conf['site']['ams_id']

   if yes_no == "y" or yes_no == "Y":
      cloud_dir = "/mnt/archive.allsky.tv/" + local_station_id + "/MANUAL/" + mj['meteor_video_file'].split("/")[-1].replace(".mp4", "") + "/"
      local_dir = "/mnt/ams2/MANUAL/" + mj['meteor_video_file'].replace(".mp4", "").split("/")[-1] + "/"
      if cfe(cloud_dir,1) == 0:
         os.makedirs(cloud_dir)
      cmd = "cp " + local_dir + "*.jpg " + cloud_dir
      print(cmd)
      os.system(cmd)
      cmd = "cp " + mj['sd_trim'] + " " + cloud_dir
      print(cmd)
      os.system(cmd)

      cmd = "cp " + local_dir + "*.json " + cloud_dir
      print(cmd)
      os.system(cmd)
      if "hd_trim" in mj: 
         if mj["hd_trim"] is not None and mj['hd_trim'] != "":
            os.system("cp " + mj['hd_trim'] + " " + cloud_dir)

   input("wait")

def get_first_trim_img(video_file):
   print("TRY:", video_file)
   stacked_frame = None
   for i in range(0,50):
      cap = cv2.VideoCapture(video_file)
      grabbed , frame = cap.read()
      if stacked_frame is None:
         stacked_frame = frame
      else:
         stacked_frame = stack_stack(frame,stacked_frame)
   return(stacked_frame) 


def make_mfd(mj,json_conf,stack_img):
   # MFD ROW = (dt, fn, x, y, w, h, oint, ra, dec, az, el) = row
   #trim_start_time 
   extra_sec = int(mj['trim_start'])/25
   (f_datetime, cam_id, f_date_str,fy,fmon,fd, fh, fm, fs) = convert_filename_to_date_cam(mj['sd_trim'])
   start_trim_frame_time = f_datetime + datetime.timedelta(0,extra_sec)
   start_trim_frame_time_str = start_trim_frame_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

   print("MAKE MFD FROM METEOR OBJECT!")
   cc = 0
   colors = [[0,0,255],[0,255,0],[255,0,0],[255,255,0],[0,255,255]]
   if "clip_scan" not in mj:
      scan_save_file = mj['sd_trim'].replace(".mp4", "-channel.mp4")
      meteor_obj, objs = scan_meteor_trim(mj['sd_trim'],json_conf,mj,None)
      mj['trim_obj'] = meteor_obj
      for obj in objs:
         print(obj)
         print(objs[obj].keys())

         if cc >= len(colors) - 1:
            cc = 0
         else:
            cc += 1

         for i in range(0, len(objs[obj]['ofns'])):
            print(cc, i)
            cx = objs[obj]['oxs'][i] 
            cy = objs[obj]['oys'][i] 
            cv2.circle(stack_img,(cx,cy), 3, colors[cc], 1)
            if cx > 500:
               off = -10
            else:
               off = 10
         cv2.putText(stack_img, str(objs[obj]['obj_id']),  (cx-off, cy), cv2.FONT_HERSHEY_SIMPLEX, .3, colors[cc], 1)
   point_file = mj['sd_trim'].replace(".mp4", "-points.jpg")
   cv2.imwrite(point_file, stack_img)
   print(point_file)

   channel_img = make_meteor_channel(mj, stack_img)
   channel_img = cv2.cvtColor(channel_img, cv2.COLOR_GRAY2BGR)
   channel_file = point_file.replace("-points.jpg" , "-channel.jpg")
   stack_channel_file = point_file.replace("-points.jpg" , "-stack-channel.jpg")
   stack_channel_img = cv2.subtract(stack_img, channel_img) 
   cv2.imwrite(channel_file, channel_img)
   cv2.imwrite(stack_channel_file, stack_channel_img)

   save_meteor_scan_file = point_file.replace("-points.jpg" , "-channel.mp4")
   meteor_obj, objs = scan_meteor_trim(mj['sd_trim'],json_conf,mj,save_meteor_scan_file,channel_img)

   hdm_x = 1920 / stack_img.shape[1] 
   hdm_y = 1080 / stack_img.shape[0] 
   table_header = ["Datetime", "#","FN", "SD X", "SD Y", "HD X", "HD Y", "INT", "RA", "DEC", "AZ", "EL"]
   table_data = []
   meteor_frame_data = []
   for i in range(0,len(meteor_obj['ofns'])):
      hd_x = meteor_obj['oxs'][i] * hdm_x
      hd_y = meteor_obj['oys'][i] * hdm_y
      sd_x = meteor_obj['oxs'][i] 
      sd_y = meteor_obj['oys'][i] 
      sd_w = meteor_obj['ows'][i] 
      sd_h = meteor_obj['ohs'][i] 
      fn = meteor_obj['ofns'][i] 
      extra_sec = int(fn)/25
      frame_time = start_trim_frame_time + datetime.timedelta(0,extra_sec)
      frame_time_str = frame_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

      oint = meteor_obj['oint'][i] 
      new_x, new_y, ra,dec, az, el = XYtoRADec(hd_x,hd_y,mj['sd_trim'],mj['cp'],json_conf)
      table_data.append((frame_time_str, i, fn, sd_x, sd_y, hd_x, hd_y, oint, ra, dec, az, el))
      meteor_frame_data.append((frame_time_str, fn, hd_x, hd_y, sd_w, sd_h, oint, ra, dec, az, el))

   ang_sep = np.degrees(angularSeparation(np.radians(table_data[0][8]), np.radians(table_data[0][9]), np.radians(table_data[-1][8]), np.radians(table_data[-1][9])))
   dur = len(table_data)/25
   ang_vel = ang_sep / dur
   ints = [row[7] for row in table_data]
   
   print("SD Clip:", mj['sd_trim'].split("/")[-1])
   print("HD Clip:", mj['hd_trim'].split("/")[-1])
   print("Trim Clip Start Time:", start_trim_frame_time_str)
   print("Duration:", len(table_data)/25)
   print("Angular Separation:", round(ang_sep,2))
   print("Angular Velocity:", round(ang_vel,2), "deg/s")
   print("Peak Intensity:", max(ints))
   print("")

   mj['event_start_time'] = start_trim_frame_time_str
   mj['dur'] =  len(table_data)/25
   mj['ang_sep'] = round(ang_sep,2)
   mj['ang_vel'] = round(ang_vel,2)
   mj['peak_int'] = max(ints)
   mj['meteor_frame_data'] = meteor_frame_data
   
   print(tabulate(table_data,headers=table_header))
   return(mj)


def get_calib(mj, json_conf):
   print(mj.keys())
   (f_datetime, cam_id, f_date_str,fy,fmon,fd, fh, fm, fs) = convert_filename_to_date_cam(mj['sd_trim'])
   mj['cam_id'] = cam_id
   if mj['station_id'] == local_json_conf['site']['ams_id']:
      print("We are working on a local file, so we will use the local calibration.")
      local = 1
   else:
      print("This is a remote file. We need the calibration info before proceeding!")
      local = 0

   if local == 1:
      cal_day_hist_file = "/mnt/ams2/cal/" + mj['station_id'] +  "_cal_range.json"
      mcp_file = "/mnt/ams2/cal/multi_poly-" + mj['station_id'] +  "-" + cam_id + ".info"
      if cfe(cal_day_hist_file) == 0:
         print("Cal day hist file not found! Need to run cal manager to create defaults.", cal_day_hist_file)
         exit()
      else:
         cal_hist = load_json_file(cal_day_hist_file)
      if cfe(mcp_file) == 0:
         print("MCP File does not exist. Need to make it before doing this. Run deep_cal", mcp_file)
         mcp = None
      else:
         mcp = load_json_file(mcp_file)
   else:
      cl_cal_day_hist_file = "/mnt/archive.allsky.tv/" + mj['station_id'] +  "/CAL/" + mj['station_id'] + "_cal_range.json"
      cl_mcp_file = "/mnt/archive.allsky.tv/" + mj['station_id'] +  "/CAL/multi_poly-" + mj['station_id']  + "-" + cam_id + ".info"
      local_dir = "/mnt/ams2/MANUAL/REMOTE_CAL/" + mj['station_id'] + "/"

      cal_day_hist_file = local_dir + mj['station_id'] + "_cal_range.json"
      mcp_file = local_dir + "multi_poly-" + mj['station_id']  + "-" + cam_id + ".info"

      if cfe(local_dir, 1) == 0:
         os.makedirs(local_dir)
      os.system("cp " + cl_cal_day_hist_file + " " + local_dir)
      os.system("cp " + mcp_file + " " + local_dir)


      if cfe(cal_day_hist_file) == 0:
         print("Cal day hist file not found! Need to run cal manager to create defaults.", cal_day_hist_file)
         exit()
      else:
         cal_hist = load_json_file(cal_day_hist_file)
      if cfe(mcp_file) == 0:
         print("MCP File does not exist. Need to make it before doing this. Run deep_cal", mcp_file)
         mcp = None
      else:
         mcp = load_json_file(mcp_file)
   

   print("Trying to calibrate:", mj['station_id'], mj['cam_id'])
   cp = find_default_cal(mj['station_id'], cam_id, cal_hist, mcp, f_datetime)
   mj['cp'] = cp
   if mj['station_id'] != json_conf['site']['ams_id']:
      print("GET REMOTE JSON CONF")
      if cfe("/mnt/archive.allsky.tv/" + mj['station_id'] + "/CAL/as6.json") == 0:
         print("There is no remote json_conf for this staion!", station_id)
         print("Copy the stations as6.json to: /mnt/archive.allsky.tv/" + station_id + "/CAL/as6.json")
         cmd = "cp /mnt/archive.allsky.tv/" + mj['station_id'] + "/CAL/as6.json " + mj['man_dir'] + mj['station_id'] + "_conf.json"
         os.system(cmd)
         json_conf = load_json_file(mj['man_dir'] + mj['station_id'] + "_conf.json")
   if "cp" in mj:
      if mj['cp'] != None:
         mj['cp'] = update_center_radec(mj['sd_trim'],mj['cp'],json_conf)

      for key in mj['cp']:
         print(key, mj['cp'][key])
   return(cp,json_conf)

def find_default_cal(station_id, cam_id, cal_hist, mcp, meteor_date):
   cp = {}
   print("Finding best cal...", station_id, cam_id)
   defaults = []
   print("CAL HIST:", len(cal_hist))
   input("wait...")
   for row in cal_hist:
      print("ROW:", row)
      tcam_id, start, end, az, el, pos, px, res = row
      if math.isnan(az) is True:
         continue
      if cam_id == row[0]:
         cal_end = datetime.datetime.strptime(row[1], "%Y_%m_%d")
         cal_start = datetime.datetime.strptime(row[2], "%Y_%m_%d")
         time_diff = (meteor_date - cal_end).total_seconds() / 86400
         defaults.append((time_diff, tcam_id, start, end, az, el, pos, px, res))
         print(time_diff, meteor_date, cal_end, cal_start)
   if len(defaults) == 0:
      print("There is no default calibration to choose from!")
      best_cal = None
      cp = None
   else:
      defaults = sorted(defaults, key=lambda x: (x[0]), reverse=False)
      best_cal = defaults[0]
      print("THIS IS THE BEST CAL!")
      print(best_cal)
      cp['image_width'] = 1920
      cp['image_height'] = 1080
      cp['center_az'] = best_cal[4]
      cp['center_el'] = best_cal[5]
      cp['position_angle'] = best_cal[6]
      cp['pixscale'] = best_cal[7]
      cp['total_res_px'] = best_cal[8]
      cp['total_res_deg'] = (best_cal[8] * best_cal[7] ) / 3600
      if mcp is not None:
         cp['x_poly'] = mcp['x_poly']
         cp['y_poly'] = mcp['y_poly']
         cp['y_poly_fwd'] = mcp['y_poly_fwd']
         cp['x_poly_fwd'] = mcp['x_poly_fwd']
      cp['user_stars'] = []
      cp['cat_image_stars'] = []

   # we have to get the updated ra/dec for the center 
   print(cp)
   print("DEFAULT CP ABOVE")

   return(cp)


def make_mj_mjr(man_mj):
   print("MAKE FINAL MJ FILES")
   mj = {}
   mjr = {}

   mfn = man_mj['sd_trim'].split("/")[-1]
   date = mfn[0:10]
   mdir = "/mnt/ams2/meteors/" + date + "/" 

   hdfn = man_mj['hd_trim'].split("/")[-1]

   if "human_roi" in mj:
      x1,y1,x2,y2 = mj['human_roi']
   else:
      x1,y1,x2,y2 = get_roi(man_mj['meteor_obj'],man_mj['sd_w'],man_mj['sd_h'])
   mj['roi'] = [x1,y1,x2,y2]
   hdm_x = 1920 / man_mj['sd_w']
   hdm_y = 1080 / man_mj['sd_h']
   hdm_x_720 = 1920 / 1280
   hdm_y_720 = 1080 / 720
   mj['hd_roi'] = [int(x1 * hdm_x), int(y1 * hdm_y), int(x2 * hdm_x), int(y2 * hdm_y)]


   
   mj['sd_video_file'] = mdir + mfn
   mj['hd_trim'] = mdir + hdfn 
   mj['hd_video_file'] = mdir + hdfn 
   mj['sd_stack'] = mdir + mfn.replace(".mp4", ".jpg") 
   if "hd_trim" in man_mj:
      hd_stack = mdir + man_mj['hd_trim'].split("/")[-1].replace(".mp4", "-stacked.jpg")
      mj['hd_stack'] = hd_stack
   mfd = man_mj['meteor_frame_data']
   mj['roi'] = man_mj['roi']
   mj['hd_roi'] = man_mj['hd_roi']
   mj['sd_objects'] = man_mj['objects']

   if "report" not in man_mj['meteor_obj']:
      man_mj['meteor_obj'] = analyze_object(man_mj['meteor_obj'])

   man_mj['meteor_obj']['report']['ang_sep'] = man_mj['ang_sep']
   man_mj['meteor_obj']['report']['ang_dist'] = man_mj['ang_sep']
   man_mj['meteor_obj']['report']['ang_vel'] = man_mj['ang_vel']
   mj['best_meteor'] = man_mj['meteor_obj']
   mj['best_meteor']['dt'] = [row[0] for row in mfd]
   mj['best_meteor']['fns'] = [row[1] for row in mfd] 
   mj['best_meteor']['xs'] = [(row[2] / hdm_x_720) for row in mfd]
   mj['best_meteor']['ys'] = [(row[3] / hdm_y_720) for row in mfd]
   mj['best_meteor']['ws'] = [row[4] for row in mfd]
   mj['best_meteor']['hs'] = [row[5] for row in mfd]
   mj['best_meteor']['ccxs'] = [(row[2] /hdm_x_720) for row in mfd]
   mj['best_meteor']['ccys'] = [(row[3] /hdm_y_720) for row in mfd]
   mj['best_meteor']['ints'] = [row[6] for row in mfd]
   mj['best_meteor']['ras'] = [row[7] for row in mfd]
   mj['best_meteor']['decs'] = [row[8] for row in mfd]
   mj['best_meteor']['azs'] = [row[9] for row in mfd]
   mj['best_meteor']['els'] = [row[10] for row in mfd]
   mj['confirmed_meteors'] = [man_mj['meteor_obj']]
   mj['cp'] = man_mj['cp']

   (f_datetime, cam_id, f_date_str,fy,fmon,fd, fh, fm, fs) = convert_filename_to_date_cam(man_mj['sd_trim'])
   mjr = {}
   mjr['station_name'] = man_mj['station_id']
   mjr['device_name'] = cam_id
   mjr['sd_video_file'] = mj['sd_video_file']
   mjr['hd_video_file'] = mj['hd_trim']
   mjr['sd_stack'] = mj['sd_stack']
   mjr['hd_stack'] = mj['hd_stack']
   mjr['event_start_time'] = man_mj['event_start_time']
   mjr['peak_int'] = man_mj['peak_int']
   mjr['peak_magnitude'] = man_mj['peak_int']
   mjr['start_az'] = man_mj['meteor_frame_data'][0][-2]
   mjr['start_el'] = man_mj['meteor_frame_data'][0][-1]
   mjr['end_az'] = man_mj['meteor_frame_data'][-1][-2]
   mjr['end_el'] = man_mj['meteor_frame_data'][-1][-1]
   mjr['start_ra'] = man_mj['meteor_frame_data'][0][-4]
   mjr['start_dec'] = man_mj['meteor_frame_data'][0][-3]
   mjr['end_ra'] = man_mj['meteor_frame_data'][-1][-4]
   mjr['end_dec'] = man_mj['meteor_frame_data'][-1][-3]
   mjr['meteor_frame_data'] = man_mj['meteor_frame_data']
   mjr['ang_sep'] = man_mj['ang_sep']
   mjr['ang_vel'] = man_mj['ang_vel']
   mjr['crop_box'] = man_mj['hd_roi']
   mjr['cp'] = man_mj['cp']

   return(mj, mjr)

def find_hd(meteor_video_file, mj):
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
      selected_hd = input("Select the HD file. [Enter for None]")
      if selected_hd != "":
         selected_hd = all_hd[int(selected_hd)]
      else:
         selected_hd = None
   else:
      selected_hd = None
      print("NO ASSOCIATED HD FILES COULD BE FOUND.")
      hd_over = input("To manually add an HD source file, enter the full path and filename now.")
      if hd_over != "":
         selected_hd = hd_over  
      else:
         selected_hd = None


   if selected_hd is None:
      hd_start = None
      hd_end = None

   elif "trim" not in selected_hd:
      print("It looks like you have choosen a minute long HD. We need to split it before importing.")
      print("SD was clipped at: ", mj['trim_start'], mj['trim_end'])

      w,h,br,frames = ffprobe(hd_file)

      print("Enter the start and end trim frame numbers separated with space. ", frames, " total frames in the clip. (These should be close to the same as the SD)")
      hd_trn = input("Enter the start and end trim frame numbers")
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

def man_clip_hd(man_hd,mj):
   print("Manually Clip HD File", man_hd)
   print("SD File:", mj['meteor_video_file'])
   print("SD was clipped at: ", mj['trim_start'], mj['trim_end'])
   mj['start_hd_trim'] = input("Enter the start HD trim frame number.")
   mj['end_hd_trim'] = input("Enter the start HD trim frame number.")
   if cfe(man_hd) == 1:
      hd_fn = man_hd.split("/")[-1]
      local_hd = mj['man_dir'] + hd_fn 
      new_hd = mj['man_dir'] + hd_fn.replace(".mp4", "-trim-" + str(mj['start_hd_trim']) + "-HD-meteor.mp4") 
      if cfe(local_hd) == 0:
         os.system("cp " + man_hd + " " + local_hd)
      if cfe(new_hd) == 0:
         cmd = """ /usr/bin/ffmpeg -i """ + local_hd + """ -vf select="between(n\,""" + str(mj['start_hd_trim']) + """\,""" + str(mj['end_hd_trim']) + """),setpts=PTS-STARTPTS" -y -update 1 -y """ + new_hd + " >/dev/null 2>&1"
         print(cmd)
         os.system(cmd)
      mj['hd_trim'] = new_hd
   return(mj)

def make_meteor_channel(mj, stacked_image):
 # make channel
   if True:
      work_stack = stacked_image.copy()
      dom_obj = mj['trim_obj'] 
      slope,intercept = best_fit_slope_and_intercept(dom_obj['oxs'], dom_obj['oys'])
      reg_x = dom_obj['oxs'].copy()
      if dom_obj['oxs'][0] - dom_obj['oxs'][-1] > 0:
         # Right to left
         regm = -10
      else:
         regm = 10
      
      rx = dom_obj['oxs'][-1]
      if regm < 0:
         while rx > 0:

            rx = rx + regm
            reg_x.append(rx)
      if regm > 0:
         while rx < stacked_image.shape[1]:
            rx = rx + regm
            reg_x.append(rx)
      print("SLOPE:", slope, intercept)
      line_regr = [slope * xi + intercept for xi in reg_x]
      zero_x_y  = slope * 1 + intercept 
      print("ZXY:", zero_x_y)

      lx1 = dom_obj['oxs'][0]
      ly1 = dom_obj['oys'][0] 

      lx2 = reg_x[-1]
      ly2 = line_regr[-1]

      print("X", reg_x)
      print("Y", line_regr)
      print("LINE:", lx1, ly1,lx2, ly2)
      channel_img = np.zeros((mj['sd_h'],mj['sd_w']),dtype=np.uint8)
      cv2.line(channel_img, (int(lx1),int(ly1)), (int(lx2),int(ly2)), (255,255,255), 30)
      channel_img = invert_image(channel_img)

      return(channel_img)

def invert_image(imagem):
   imagem = (255-imagem)
   return(imagem)

def best_fit_slope_and_intercept(xs,ys):
   xs = np.array(xs, dtype=np.float64)
   ys = np.array(ys, dtype=np.float64)
   if len(xs) < 3:
      return(0,0)
   if ((np.mean(xs)*np.mean(xs)) - np.mean(xs*xs)) == 0:
      m = (((np.mean(xs)*np.mean(ys)) - np.mean(xs*ys)) / 1)

   else:
      m = (((np.mean(xs)*np.mean(ys)) - np.mean(xs*ys)) /
         ((np.mean(xs)*np.mean(xs)) - np.mean(xs*xs)))

      b = np.mean(ys) - m*np.mean(xs)
      if math.isnan(m) is True:
         m = 1
         b = 1

      return m, b

def man_detect(meteor_video_file,json_conf):
   if meteor_video_file is None:
      meteor_video_file = input("Enter the full path and filename to the minute file or meteor trim file you want to import.")
   if cfe(meteor_video_file) == 1:
      print("found file.", meteor_video_file)  
      data = scan_meteor_video(meteor_video_file,json_conf)

if len(sys.argv) > 1:
   man_detect(sys.argv[1], local_json_conf)
else:
   menu(local_json_conf)
