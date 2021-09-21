#!/usr/bin/python3
import datetime
from tabulate import tabulate
import sys
import numpy as np
from lib.PipeUtil import load_json_file, save_json_file, cfe, convert_filename_to_date_cam
from lib.PipeDetect import get_contours_in_image, find_object, analyze_object
<<<<<<< HEAD
=======
from lib.PipeAutoCal import update_center_radec, get_image_stars, pair_stars, distort_xy, AzEltoRADec,HMS2deg

>>>>>>> ce70a2733787bcdfc13cc031e0b748d8efb78f19
from PIL import ImageFont, ImageDraw, Image, ImageChops
import os
import glob

import cv2

json_conf = load_json_file("../conf/as6.json")
show = 0

<<<<<<< HEAD
def menu():
=======
def menu(json_conf):
>>>>>>> ce70a2733787bcdfc13cc031e0b748d8efb78f19
   print("""
      1) Detect/Reduce and Import meteor-clip into the system

   """)
   cmd = input("Select command")

   if cmd == "1":
<<<<<<< HEAD
      man_detect(None)

def stack_stack(new_frame, stack_frame):
   pic1 = Image.fromarray(new_frame)
   pic2 = Image.fromarray(stack_frame)
   stacked_image=ImageChops.lighter(pic1,pic2)
   return(np.asarray(stacked_image))

def scan_meteor_video(meteor_video_file):
=======
      man_detect(None, json_conf)

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
            print("F_SCALE/AZ/EL/RA/DEC/X/Y", cp['pixscale'], F_scale, az,el,ra,dec,new_cat_x,new_cat_y)
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


   cv2.imshow('grid', grid_img)
   cv2.waitKey(0)
   cal_image = cv2.resize(cal_image, (1920,1080))
   blend_image = cv2.addWeighted(cal_image, .7, grid_img, .3,0) 
   cv2.imshow('grid', blend_image)
   cv2.waitKey(0)
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
            print("KEY/POINT/PC:", key, point,pc)
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



def scan_meteor_video(meteor_video_file,json_conf):
>>>>>>> ce70a2733787bcdfc13cc031e0b748d8efb78f19
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
<<<<<<< HEAD
   meteor_video_file = man_dir + mfn
   mj['meteor_video_file'] = meteor_video_file 
=======

   if mj['station_id'] == json_conf['site']['ams_id']:
      print("We are working on a local file, so we will use the local calibration.")
      local = 1
   else:
      print("This is a remote file. We need the calibration info before proceeding!")
      local = 0
      if cfe("/mnt/archive.allsky.tv/" + station_id + "/CAL/as6.json") == 0:
         print("There is no remote json_conf for this staion!", station_id)
         print("Copy the stations as6.json to: /mnt/archive.allsky.tv/" + station_id + "/CAL/as6.json")
         cmd = "cp /mnt/archive.allsky.tv/" + station_id + "/CAL/as6.json " + mj['man_dir'] + mj['station_id'] + "_conf.json"
         os.system(cmd)
         json_conf = load_json_file(mj['man_dir'] + mj['station_id'] + "_conf.json")




   meteor_video_file = man_dir + mfn
   mj['meteor_video_file'] = meteor_video_file 
   mj['man_dir'] = man_dir
>>>>>>> ce70a2733787bcdfc13cc031e0b748d8efb78f19

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
<<<<<<< HEAD
      apply_calib(mj)

def apply_calib(mj):
=======
      mj['cp'],json_conf = get_calib(mj,json_conf)
  
   star_img = cv2.resize(stacked_frame, (1920,1080))
   mj['cp']['user_stars'] = get_image_stars(mj['sd_trim'], star_img, json_conf,0)
   mj['cp'] = pair_stars(mj['cp'], mj['sd_trim'], json_conf, star_img)

   for x,y,i in mj['cp']['user_stars']:
      cv2.rectangle(star_img, (int(x-5), int(y-5)), (int(x+5) , int(y+5)), (255, 255, 255), 1)
   all_dist = []
   for row in mj['cp']['cat_image_stars']:
      print("CS:", row)
      (name,mag,ra,dec,ra,dec,match_dist,new_cat_x,new_cat_y,trash1,trash2,new_cat_x,new_cat_y,six,siy,cat_dist,star_int) = row
      all_dist.append(cat_dist)
      cv2.rectangle(star_img, (int(new_cat_x-5), int(new_cat_y-5)), (int(new_cat_x+5) , int(new_cat_y+5)), (128, 128, 255), 1)
      cv2.line(star_img, (new_cat_x,new_cat_y), (int(six),int(siy)), (100,100,100), 1)
      cv2.putText(star_img, name,  (new_cat_x, new_cat_y), cv2.FONT_HERSHEY_SIMPLEX, .5, (200, 200, 200), 1)


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

   cv2.imshow('pepe', star_img)
   cv2.waitKey(0)


   print("FINAL CP:")
   if mj['cp'] is None:
      print("Calparams not found:", mj['cp']) 

   else:
      print("Calparams found:", mj['cp']) 

   # make grid
   grid_image, blend_image = make_az_grid(stacked_frame, mj, json_conf)


   print("DONE")
   make_mfd(mj)

def make_mfd(mj):
   # MFD ROW = (dt, fn, x, y, w, h, oint, ra, dec, az, el) = row
   print("MAKE MFD FROM METEOR OBJECT!")
   print(mj['meteor_obj']['oxs'])
   print(mj['meteor_obj']['oys'])


def get_calib(mj, json_conf):
>>>>>>> ce70a2733787bcdfc13cc031e0b748d8efb78f19
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
<<<<<<< HEAD
=======
         mcp = None
>>>>>>> ce70a2733787bcdfc13cc031e0b748d8efb78f19
      else:
         mcp = load_json_file(mcp_file)
   

<<<<<<< HEAD

   print("Trying to calibrate:", mj['station_id'], mj['cam_id'])
   find_default_cal(mj['station_id'], cam_id, cal_hist, f_datetime)

def find_default_cal(station_id, cam_id, cal_hist, meteor_date):
   cp = {}
   print("Finding best cal...")
   for row in cal_hist:
=======
      print("Trying to calibrate:", mj['station_id'], mj['cam_id'])
      cp = find_default_cal(mj['station_id'], cam_id, cal_hist, mcp, f_datetime)
      mj['cp'] = cp
   if mj['station_id'] != json_conf['site']['ams_id']:
      print("GET REMOTE JSON CONF")
      if cfe("/mnt/archive.allsky.tv/" + station_id + "/CAL/as6.json") == 0:
         print("There is no remote json_conf for this staion!", station_id)
         print("Copy the stations as6.json to: /mnt/archive.allsky.tv/" + station_id + "/CAL/as6.json")
         cmd = "cp /mnt/archive.allsky.tv/" + station_id + "/CAL/as6.json " + mj['man_dir'] + mj['station_id'] + "_conf.json"
         os.system(cmd)
         json_conf = load_json_file(mj['man_dir'] + mj['station_id'] + "_conf.json")
   if mj['cp'] != None:
      mj['cp'] = update_center_radec(mj['sd_trim'],mj['cp'],json_conf)

   for key in mj['cp']:
      print(key, mj['cp'][key])
   return(cp,json_conf)

def find_default_cal(station_id, cam_id, cal_hist, mcp, meteor_date):
   cp = {}
   print("Finding best cal...")
   defaults = []
   for row in cal_hist:
      print("ROW:", row)
      tcam_id, start, end, az, el, pos, px, res = row
>>>>>>> ce70a2733787bcdfc13cc031e0b748d8efb78f19
      if cam_id == row[0]:
         cal_end = datetime.datetime.strptime(row[1], "%Y_%m_%d")
         cal_start = datetime.datetime.strptime(row[2], "%Y_%m_%d")
         time_diff = (meteor_date - cal_end).total_seconds() / 86400
<<<<<<< HEAD
         print(time_diff, meteor_date, cal_end, cal_start)
=======
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

   return(cp)

>>>>>>> ce70a2733787bcdfc13cc031e0b748d8efb78f19

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


<<<<<<< HEAD
def man_detect(meteor_video_file):
=======
def man_detect(meteor_video_file,json_conf):
>>>>>>> ce70a2733787bcdfc13cc031e0b748d8efb78f19
   if meteor_video_file is None:
      meteor_video_file = input("Enter the full path and filename to the minute file or meteor trim file you want to import.")
   if cfe(meteor_video_file) == 1:
      print("found file.", meteor_video_file)  
      data = scan_meteor_video(meteor_video_file,json_conf)

if len(sys.argv) > 1:
<<<<<<< HEAD
   man_detect(sys.argv[1])
else:
   menu()
=======
   man_detect(sys.argv[1], json_conf)
else:
   menu(json_conf)
>>>>>>> ce70a2733787bcdfc13cc031e0b748d8efb78f19
