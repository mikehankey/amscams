#!/usr/bin/python3.6
import cv2
import time
import sys
import requests
import json
import os
from lib.PipeUtil import load_json_file, save_json_file
from lib.PipeVideo import load_frames_fast 
import numpy as np
from Classes.Detector import Detector
from lib.DEFAULTS import *
import glob
DD = Detector()

json_conf = load_json_file("../conf/as6.json")

def day_sum():
   station_id = json_conf['site']['ams_id']
   mif = "/mnt/ams2/meteors/" + json_conf['site']['ams_id'] + "_OBS_IDS.json"
   print("MIF", mif)
   obs_ids = load_json_file(mif)
   day_stats = {}
   day_data = []
   day_count = []
   for oid, ts in obs_ids:
      el = oid.split("_")
      day_key = el[1] + "_" + el[2] + "_" + el[3]
      if day_key not in day_stats:
         day_stats[day_key] = {}
         day_stats[day_key]['meteors'] = 1
      else:
         day_stats[day_key]['meteors'] += 1
   for day_key in sorted(day_stats.keys(), reverse=True):
   #   ai_file = "/mnt/ams2/meteors/" + day_key + "/" + station_id + "_" + day_key + "_AI_DATA.info"
   #   ai_run = os.path.exists(ai_file)
   #   print(day_key, day_stats[day_key], "AI:", ai_run, ai_file)
      day_count.append((day_key, day_stats[day_key]['meteors']))
   day_count = sorted(day_count, key=lambda x: x[1])
   for day_key, count in day_count:
      ai_file = "/mnt/ams2/meteors/" + day_key + "/" + station_id + "_" + day_key + "_AI_DATA.info"
      ai_run = os.path.exists(ai_file)
      print(day_key, day_stats[day_key], "AI:", ai_run, ai_file)

def ai_scan_all_days():
   if os.path.exists("ai_meteor_log.json") is True:
      ai_meteor_log = load_json_file("ai_meteor_log.json")
   else:
      ai_meteor_log = {}
   if "days" not in ai_meteor_log:
      ai_meteor_log['days'] = {}

   meteor_dir = "/mnt/ams2/meteors/"
   temp = os.listdir("/mnt/ams2/meteors/")
   mdays = []
   for t in temp:
      if t[0] == "2" :
         mdays.append(t)
   
   for day in sorted(mdays,reverse=True):
      print("DO", day)
      ai_scan_day(day)
      ai_meteor_log['days'][day] = {}
      save_json_file("ai_meteor_log.json", ai_meteor_log)
      print("DID", day)
      time.sleep(3)

def ai_reject_meteor(meteor_file, mj):
   print("   REJECT:", meteor_file, mj.keys())
   date = meteor_file[0:10]
   mdir = "/mnt/ams2/meteors/"  
   non_meteor_dir = "/mnt/ams2/non_meteors/" + date + "/"
   meteor_dir = "/mnt/ams2/meteors/" + date + "/"

   if "user_mods" in mj:
      if "frames" in mj['user_mods']:
         print("   KEEP: Human edits detected.")
         return("KEEP") 

   if "human_confirmed" in mj or "hc" in mj :
      print("   KEEP: Multi station or Human confirmed already")
      return("KEEP") 
   else:
      if os.path.exists(non_meteor_dir) is False:
         os.makedirs(non_meteor_dir)
      sd_root = mj['sd_video_file'].split("/")[-1].replace(".mp4", "")
      files = glob.glob(mdir + date + "/" + sd_root + "*")
      print("GLOB", mdir + date + "/" + sd_root + "*")
      print("FILES", len(files))
      if SHOW == 1:
         doit = input("Reject files press 'x' for Non-meteor ?")
         if doit == "X" or doit == "x":
            print("REJECT")
         else:
            mj['hc'] = 1
            save_json_file(meteor_dir + meteor_file, mj)
            print("HUMAN CONFIRMED")
            return("ACCEPTED")



      for sf in files:
         cmd = "mv -f " + sf + " " + non_meteor_dir 
         print(cmd)
         os.system(cmd)
      if "hd_trim" in mj:
         hd_root = mj['hd_trim'].split("/")[-1].replace(".mp4", "")
         if hd_root != "" :
            files = glob.glob(mdir + date + "/" + hd_root + "*")
         else:
            files = ""
         print("HD ROOT", meteor_file, hd_root)
         print("HD GLOB", mdir + date + "/" + hd_root + "*")
         for hf in files:
            cmd = "mv -f " + hf + " " + non_meteor_dir 
            print(cmd)
            os.system(cmd)
   return("REJECTED")

def get_contours_in_image(frame ):
   ih, iw = frame.shape[:2]

   cont = []
   if len(frame.shape) > 2:
      frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
   cnt_res = cv2.findContours(frame.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
   if len(cnt_res) == 3:
      (_, cnts, xx) = cnt_res
   elif len(cnt_res) == 2:
      (cnts, xx) = cnt_res
   for (i,c) in enumerate(cnts):
      x,y,w,h = cv2.boundingRect(cnts[i])
      if (w >= 1 or h >= 1) : # and (w < 10 and h < 10):
         cont.append((x,y,w,h))
   return(cont)

def format_response(resp):
   color = [0,255,0]
   if "meteor_yn" in resp:
      meteor_yn = round(max(resp['meteor_yn'], resp['fireball_yn'] ),1)
   else:
      meteor_yn = 0
   desc1 = str(meteor_yn) + "%" + " meteor"
   desc2 = str(round(resp['mc_class_conf'],1)) + "% " + resp['mc_class']
   if "meteor" not in resp['mc_class'] and resp['mc_class_conf'] > meteor_yn and meteor_yn < 50:
      # not a meteor 
      color = [0,0,255]
      desc = desc2 + " " + desc1
      meteor_yn = False
      print("CASE1")
   elif "meteor" not in resp['mc_class'] and resp['mc_class_conf'] > meteor_yn and meteor_yn < 50:
      color = [0,165,255]
      desc = desc2 + " " + desc1
      meteor_yn = False
      print("CASE2")

   else:
      desc = desc1 + " " + desc2
      meteor_yn = True
      print("CASE3")

   print(meteor_yn, desc)
   return(desc, color, meteor_yn)

def check_ai(roi_file):

   url = "http://localhost:5000/AI/METEOR_ROI/?file={}".format(roi_file)
   #print("URL:", url)
   try:
      response = requests.get(url)
      content = response.content.decode()
      content = json.loads(content)
      #print(content)
   except Exception as e:
      print("HTTP ERR:", e)
      content = {}
   return(content)

def sd_to_hd_roi(sd_x, sd_y, iw,ih):

   if True:
      hdm_x = 1920 / iw
      hdm_y = 1080/ ih

      hdx = int((sd_x * hdm_x) )
      hdy = int((sd_y * hdm_y) )

      hx1 = (sd_x * hdm_x) - (224/2)
      hy1 = (sd_y * hdm_y) - (224/2)
      hx2 = (sd_x * hdm_x) + (224/2)
      hy2 = (sd_y * hdm_y) + (224/2)

      hw = hx2 - hx1
      hh = hy2 - hy1
      if hw > hh :
         hh = hw
      else:
         hw = hh

      cx = (hx1 + hx2) / 2
      cy = (hy1 + hy2) / 2

      hx1 = int(cx - (hw/2))
      hx2 = int(cx + (hw/2))
      hy1 = int(cy - (hh/2))
      hy2 = int(cy + (hh/2))
      if hx1 < 0:
         hx1 = 0
         hx2 = 224
      if hy1 < 0:
         hy1 = 0
         hy2 = 224
      if hx2 >= 1920:
         hx1 = 1919 - 224
         hx2 = 1919
      if hy2 >= 1080:
         hy1 = 1079 - 224
         hy2 = 1079

   return(hx1,hy1,hx2,hy2, hdx, hdy)

def find_motion_objects(video_file):
   frames,color_frames,subframes,sum_vals,max_vals,pos_vals = load_frames_fast(video_file, json_conf, 0, 0, 1, 1,[])
   print("FIND MOTION OBJECTS IN VIDEO FILE:", video_file, len(frames))
   objects = {}
   fn = 0
   for frame in subframes:
      dil_img = cv2.dilate(frame, None, iterations=4)
      
      min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(dil_img)
      thresh_val = max_val * .8
      if thresh_val < 10:
         thresh_val = 10
      _, thresh_img = cv2.threshold(dil_img.copy(), thresh_val, 255, cv2.THRESH_BINARY)

      cnts = get_contours_in_image(thresh_img)
      for x,y,w,h in cnts:
         cx = x + (w/2)
         cy = y + (h/2)
         intensity = 0
         oid, objects = Detector.find_objects(fn,x,y,w,h,cx,cy,intensity,objects, 50)

      for obj_id in objects:
         status, objects[oid]['report'] = Detector.analyze_object(objects[obj_id]) 
 
      thresh_img = cv2.resize(thresh_img,(1920,1080))
      if SHOW == 1:
         cv2.imshow('pepe', thresh_img)
         cv2.waitKey(30)
      fn += 1

   # remove objs that are less than 3 frames
   del_obj = []
   for oid in objects:
      if len(objects[oid]['ofns'] ) <= 3:
         del_obj.append(oid)
   for d in del_obj:
      del(objects[d])

   return(objects)

def ai_scan_meteor_file(meteor_file, mj=None, location=None):
   # 
   # pass in the meteor json file and this will run the AI on all of the objects
   # 

   # sd objects might have more than one type of resolutions for the history!

   # load json files and images
   if location == None:
      location = "/mnt/ams2/meteors/"

   date = meteor_file[0:10]
   mj = None
   mjr = None
   mjf = location + date + "/" + meteor_file
   mjrf = location + date + "/" + meteor_file.replace(".json", "-reduced.json")
   stack_file = location + date + "/" + meteor_file.replace(".json", "-stacked.jpg")
   video_file = location + date + "/" + meteor_file.replace(".json", ".mp4")
   if os.path.exists(stack_file) is True:
      stack_img = cv2.imread(stack_file)
   else:
      stack_img = np.zeros((1080,1920,3),dtype=np.uint8)
   marked_stack = stack_img.copy()
   sdh, sdw = stack_img.shape[:2]
   


   if os.path.exists(mjf):
      try:
         if mj is None:
            mj = load_json_file(mjf)
      except:
         print("BAD:", mjf)
         return(None)
   if mj is None:
      print("NO MJ!")
      return(None)
   #if mj is not None and "hc" in mj and "meteor_objs" in mj:
   #   return(mj)
   if os.path.exists(mjrf):
      mjr = load_json_file(mjrf)

   if "ai_objects" not in mj: 
      ai_objects = find_motion_objects(video_file)
   else:
      ai_objects = mj['ai_objects']


   hdm_x = 1920 / marked_stack.shape[1]
   hdm_y = 1080 / marked_stack.shape[0]

   # loop over objects in the json file
   meteor_objs = []
   for oid in ai_objects:
      obj = ai_objects[oid]
      obj = ai_objects[oid]
      #xs = [row[1] for row in history]
      #ys = [row[2] for row in history]

      xs = obj['oxs']
      ys = obj['oys']
      ws = obj['ows']
      hs = obj['ohs']

      ax = int(int(np.mean(xs)) )
      ay = int(int(np.mean(ys)) )

      #marked_stack = cv2.resize(marked_stack,(int(marked_stack.shape[1]),int(marked_stack.shape[0])))

      marked_stack = cv2.resize(marked_stack,(int(1920),int(1080)))
      for i in range(0,len(xs)):
         x = int(xs[i] )
         y = int(ys[i] )
         w = int(ws[i] )
         h = int(hs[i] )
         cx = int(int(x + (w/2)) * hdm_x)
         cy = int(int(y + (h/2)) * hdm_y)
         if w > h:
            r = w
         else:
            r = h
         cv2.rectangle(marked_stack, (cx-5, cy-5), (cx+5, cy+5), (128,128,128), 2)
         if SHOW == 1:
            cv2.imshow("pepe", marked_stack)
            cv2.waitKey(30)
      if SHOW == 1:
         cv2.imshow("pepe", marked_stack)
         cv2.waitKey(90)

      #hx1, hy1, hx2, hy2,hx,hy = sd_to_hd_roi(ax, ay, marked_stack.shape[1],marked_stack.shape[0])
      hx1, hy1, hx2, hy2,hx,hy = sd_to_hd_roi(ax, ay, stack_img.shape[1],stack_img.shape[0])
      temp_stack = cv2.resize(stack_img,(1920,1080))
      roi_img = temp_stack[hy1:hy2,hx1:hx2]
      roi_txt = str(hx1) + "_" + str(hy1) + "_" + str(hx2) + "_" + str(hy2)
      roi_file = stack_file.replace("-stacked.jpg", "-ROI_" + roi_txt + ".jpg")
  

      cv2.imwrite(roi_file, roi_img)

      ai_data = check_ai(roi_file)
      desc , color, meteor_yn = format_response(ai_data)

      ai_objects[oid]['hd_roi'] = [hx1,hy1,hx2,hy2]
      ai_objects[oid]['ai_data'] = ai_data
      ai_objects[oid]['ai_desc'] = desc 
      ai_objects[oid]['ai_meteor_yn'] = meteor_yn
      if "report" in ai_objects[oid]:
         report_class = ai_objects[oid]['report']['class']
      else:
         report_class = "unknown"
      #print(desc, color)

      cv2.rectangle(temp_stack, (hx1, hy1), (hx2, hy2), color, 2)
      if hy2 > 1080 / 2:
         cv2.putText(temp_stack, str(oid) + " " + report_class + " " + desc,  (hx1,hy1-15), cv2.FONT_HERSHEY_SIMPLEX, .4, color, 1)
      else:
         cv2.putText(temp_stack, str(oid) + " " + report_class + " " + desc,  (hx1,hy2+15), cv2.FONT_HERSHEY_SIMPLEX, .4, color, 1)
      if SHOW == 1:
         cv2.imshow("pepe", temp_stack)
         cv2.waitKey(120)
      #print("WROTE:", roi_file)
      if meteor_yn is True:
         meteor_objs.append(oid)
      #   print(ai_data)
         mj['hd_roi'] = [hx1,hy1,hx2,hy2]
         mj['meteor_yn'] = ai_data['meteor_yn']
         mj['fireball_yn'] = ai_data['fireball_yn']
         mj['mc_class'] = ai_data['mc_class']
         mj['mc_class_conf'] = ai_data['mc_class_conf']
         mj['decision'] = "APPROVED"
         print("   METEOR YES:", oid, meteor_yn, ai_data)
      else:
         print("   METEOR NO:", oid, ai_data)
         
   mj['ai_objects'] = ai_objects
   mj['meteor_objs'] = meteor_objs
   save_json_file(mjf, mj)
   return(mj)

def ai_scan_day(day):
   mdir = "/mnt/ams2/meteors/" + day + "/"
   ai_file = mdir + "/" + json_conf['site']['ams_id'] + "_" + day + "_AI_DATA.info"
   ai_idx = {}
   if os.path.exists(ai_file) is True:
      temp = load_json_file(ai_file)
      for obj in temp:
         root_fn = obj[1]
         ai_idx[root_fn] = obj
   meteor_files = os.listdir("/mnt/ams2/meteors/" + day + "/")
   ai_info = []
   for mf in sorted(meteor_files):
      root_fn = mf.replace(".json", "")

      if root_fn in ai_idx:
         decision, root_fn, hd_vid, roi, meteor_yn_conf, fireball_yn_conf, mc_class, mc_class_conf = ai_idx[root_fn]
         if type(meteor_yn_conf) == dict:
            meteor_yn_conf = 99


         ai_info.append((decision, root_fn, hd_vid, roi, meteor_yn_conf, fireball_yn_conf, mc_class, mc_class_conf ))
         #if type(meteor_yn_conf) == dict:
         #   mj = load_json_file(mdir + mf)
         #   mj['meteor_yn_conf'] = 99
         #   meteor_yn_conf = 99
         #   save_json_file(mdir + mf, mj)
         if decision == "APPROVED" and (meteor_yn_conf > 50 or fireball_yn_conf > 50) or "meteor" in mc_class:
            print("SKIP ALREADY DID", root_fn)
            continue
      if "json" not in mf:
         continue
      if "reduced" in mf:
         continue
      mj = ai_scan_meteor_file(mf)
   
      if mj is not None:
         save_json_file(mdir + mf, mj)
      else:
         continue
      decision = "APPROVED"
      print(mdir + mf)
      print(mj) 
      if len(mj['meteor_objs']) == 0:
         hc = False
         if "hc" in mj or "human_confirmed" in mj:
            hc = True
         if "user_mods" in mj :
            if "frames" in "user_mods" :
               hc = True
         
         if hc is False: 
            decision = "REJECT"
            res = ai_reject_meteor(mf, mj)
            if res == "KEEP":
               decision = "APPROVED"
               mj['meteor_yn'] = True
               mj['hc'] = 1
         else:
            decision = "APPROVED"
      if "hd_trim" in mj:
         hd_vid = mj['hd_trim'].split("/")[-1]
      else:
         hd_vid = None
      if "meteor_yn" in mj : #or "hc" in mj :
         meteor_yn_conf = mj['meteor_yn']
          
         if "fireball_yn" in mj:
            fireball_yn_conf = mj['fireball_yn']
         else:
            fireball_yn_conf = 0
         if "mc_class" in mj:
            mc_class = mj['mc_class']
         else:
            mc_class = "unknown"
         if "mc_class_conf" in mj:
            mc_class_conf = mj['mc_class_conf']
         else:
            mc_class_conf = 0
         if "hd_roi" in mj:
            roi = mj['hd_roi']
         else:
            roi = [0,0,0,0]
         ai_info.append((decision, root_fn, hd_vid, roi, meteor_yn_conf, fireball_yn_conf, mc_class, mc_class_conf ))
         #print("AI OBJECTS:", mj['ai_objects'])
      elif "hc" in mj :
         roi = [0,0,0,0]
         
         ai_info.append(("APPROVED", root_fn, hd_vid, roi, 99, 99, "meteor", "99"))

      else:
         print("Reject", root_fn)
         decision = "REJECT"
         res = ai_reject_meteor(mf, mj)

   
   save_json_file(ai_file, ai_info)
   
if __name__ == "__main__":   
   day = sys.argv[1]
   if day == "ALL":
      ai_scan_all_days()
   elif day == "day_sum":
      day_sum()
   else:
      ai_scan_day(day)
