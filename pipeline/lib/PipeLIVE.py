'''

   functions for enabling various forms of live streaming



'''
import subprocess
import numpy as np
import cv2
import time
import random
import os

import glob
from lib.PipeReport import mk_css 
from lib.DEFAULTS import *
from lib.PipeDetect import detect_in_vals, detect_meteor_in_clip, crop_video, analyze_object
from lib.PipeVideo import find_crop_size, ffprobe, load_frames_fast
from lib.PipeUtil import convert_filename_to_date_cam, cfe, load_json_file, save_json_file, check_running, calc_dist 
from lib.PipeMeteorTests import * 
from lib.PipeImage import stack_frames, thumbnail, stack_stack, quick_video_stack
import datetime
from datetime import datetime as dt
from PIL import ImageFont, ImageDraw, Image, ImageChops
SHOW = 0

#/usr/bin/ffmpeg -i /mnt/ams2/HD/2020_07_30_23_57_23_000_010003.mp4 -vcodec libx264 -crf 30 -vf 'scale=1280:720' -y test.mp4

def get_valid_cams(json_conf):
   vcs = []
   for cam in json_conf['cameras']:
      cams_id = json_conf['cameras'][cam]['cams_id']
      vcs.append(cams_id)
   return(vcs)

def fix_missing_images(day):
   work_dir = ARC_DIR + "LIVE/METEORS/" + day + "/"
   jsons = glob.glob(work_dir + "*.json")
   for jsf in jsons:
      fn = jsf.split("/")[-1]
      ck = fn.split("_")
      if len(ck) > 3:
         print(jsf)
         vid = jsf.replace(".json",".mp4")
         crop_vid = jsf.replace(".json","-crop.mp4")
         crop_img = jsf.replace(".json","-crop.jpg")
         crop_img_tn = jsf.replace(".json","-crop-tn.jpg")
         img_tn = jsf.replace(".json","-tn.jpg")
         stack_img = jsf.replace(".json",".jpg")
         if cfe(vid) == 1:
            print(vid)
         else:
            print("missing:", vid)
        

         if cfe(crop_img) == 1:
            print(crop_img)
         else:
            print("missing:", crop_img)
 
         if cfe(crop_vid) == 1:
            print(crop_vid)
         else:
            print("missing:", crop_vid)
         if cfe(stack_img) == 1:
            print(stack_img)
         else:
            print("missing:", stack_img)
         if cfe(img_tn) == 1:
            print(img_tn)
         else:
            print("missing:", img_tn)
            thumbnail(img_tn, THUMB_W, THUMB_H)
         if cfe(crop_img_tn) == 1:
            print(crop_img_tn)
         else:
            print("missing:", crop_img_tn)
            print("TRY VIDEO STACK:", crop_vid)
            crop_stack_img = quick_video_stack(crop_vid )
            cv2.imwrite(crop_img, crop_stack_img)
            thumbnail(crop_img, THUMB_W, THUMB_H)
            exit()
   

def super_stacks_many(days ):
   json_conf = load_json_file("../conf/as6.json")
   et = json_conf['site']['extra_text']
   all_stacks = []
   valid_cams = get_valid_cams(json_conf)
   for day in days:
      WORK_DIR = ARC_DIR + "LIVE/METEORS/" + day + "/"
      ss = glob.glob (WORK_DIR + "*meteors.jpg")
      for s in ss: 
         all_stacks.append(s)


   shtml = {}
   #"<h1>METEORS FOR " + STATION_ID + " ON " + day + "</h1>"
   for stack in sorted(all_stacks):
      ifn = stack.split("/")[-1]
      xxx= ifn.split("-")
      day = xxx[0]
      cam = xxx[1]
      if cam not in valid_cams:
         continue
      if day not in shtml:
         shtml[day] = {} 
         shtml[day] = {} 
      if cam not in shtml: 
         ifn = stack.split("/")[-1]
         ifn = ifn.replace(".jpg", "-tn.jpg")
         print("IFN:", day, ifn)
         shtml[day][cam] = "<img src=./" + day + "/" + ifn + ">"
         print(shtml[day][cam])



      img = cv2.imread(stack)

      stack_tn = stack.replace(".jpg", "-tn.jpg")
      stack_med = stack.replace(".jpg", "-720.jpg")
      img_tn = cv2.resize(img, (THUMB_W,THUMB_H)) 
      img_med = cv2.resize(img, (1280,720)) 

      if cfe(stack_tn) == 0:
         cv2.imwrite(stack_tn, img_tn) 
      if cfe(stack_med) == 0:
         cv2.imwrite(stack_med, img_med) 

      fn = stack.split("/")[-1]
      date = fn[0:10]
      y,m,d = date.split("_")

      if int(d) < 10:
         d = d.replace("0")
      desc = et + " Perseid Meteor Shower - August " + str(d) + "th, 2020 "
      if SHOW == 1:
         cv2.putText(img, desc, (int(10), int(1070)),cv2.FONT_HERSHEY_SIMPLEX, .4, (255,255,255), 1)
         cv2.imshow('pepe', img)
         cv2.waitKey(0)

   # write out html and 1 wide per day image
   ohtml = ""
   TOTAL_CAMS = 6
   TOTAL_DAYS = len(shtml.keys())
   for day in sorted(shtml.keys()):
      all_day_img = np.zeros((THUMB_H,THUMB_W*TOTAL_CAMS,3),dtype=np.uint8)
      ohtml += "<h2>" + day + "</h2>\n"
      ohtml += "<div>\n"
      WORK_DIR = ARC_DIR + "LIVE/METEORS/" + day + "/"
      cc = 0
      for cam in sorted(shtml[day].keys()):
         print(day, cam, shtml[day][cam])
         ohtml += shtml[day][cam] + "/"
         sf = WORK_DIR + day + "-" + cam + "-meteors-tn.jpg"
         si = cv2.imread(sf)
         y1 = 0
         y2 = THUMB_H
         x1 = THUMB_W * cc
         x2 = x1 + THUMB_W
         cc += 1
         all_day_img[y1:y2,x1:x2] = si
         if SHOW == 1:
            cv2.imshow('pepe', all_day_img)
            cv2.waitKey(0)
      of = WORK_DIR + day + "-" + cam + "-meteors-allwide-tn.jpg"
      cv2.imwrite(of, all_day_img)
      print("WIDE:", of)

      ohtml += "</div>\n"
   fp = open(WORK_DIR + "../" + STATION_ID + "_METEORS.html", "w")
   fp.write(ohtml)
   fp.close()

   # Combine all images across all days into 1 image
   all_day_img = np.zeros((THUMB_H*TOTAL_DAYS,THUMB_W*TOTAL_CAMS,3),dtype=np.uint8)
   cc = 0
   rc = 0
   for day in sorted(shtml.keys()):
      WORK_DIR = ARC_DIR + "LIVE/METEORS/" + day + "/"
      for cam in sorted(shtml[day].keys()):
         sf = WORK_DIR + day + "-" + cam + "-meteors-tn.jpg"
         print("SF:", sf)
         si = cv2.imread(sf)


         y1 = rc * THUMB_H
         y2 = y1 + THUMB_H
         x1 = THUMB_W * cc
         x2 = x1 + THUMB_W
         if cc == TOTAL_CAMS -1 :
            cc = 0
            rc += 1
         else:
            cc += 1
         all_day_img[y1:y2,x1:x2] = si
         if SHOW == 1:
            cv2.imshow('pepe', all_day_img)
            cv2.waitKey(0)
   
   WORK_DIR = ARC_DIR + "LIVE/METEORS/" 
   of = WORK_DIR + STATION_ID + "-ALL-METEORS-ALL-DAYS.jpg" 
   print(all_day_img.shape)
   cv2.imwrite(of, all_day_img)
   print(of)


def super_stacks(day):
   WORK_DIR = ARC_DIR + "LIVE/METEORS/" + day + "/"
   sts = glob.glob(ARC_DIR + "LIVE/METEORS/" + day + "/*.jpg")
   stacks = []
   for st in sts:
      if "-crop" not in st and "-tn" not in st:
         stacks.append(st)  
   stack_images = {}
   sync_files = []
   for file in sorted(stacks):
      (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(file)
      of = WORK_DIR + day + "-" + cam + "-meteors.jpg"
      sync_files.append(of) 
      if True:
         try: 
            img = cv2.imread(file)
            print(cam, img.shape)
         except:
            print("COULD NOT READ THE STACK!", file)
            continue
         if img.shape[0] != 1080:
            print("RESIZE!")
            img = cv2.resize(img, (1920,1080)) 
            print(cam, img.shape)
         frame_pil = Image.fromarray(img)


         if cam not in stack_images: 
            stack_images[cam] = stack_stack(frame_pil, frame_pil)
         else:
            stack_images[cam] = stack_stack(stack_images[cam], frame_pil)
         if cam not in stack_images:
            stack_images[cam] = stacked_image 

         for cam in stack_images:
            of = WORK_DIR + day + "-" + cam + "-meteors.jpg"
            stack_images[cam].save(of)
            print("SAVING:", of)
  
   # sync
   if len(sf) == 0:
      print("NO SYNC FILES!")
      return()
   sf = sync_files[0].split("/")[-1]
   sdir = file.replace(sf, "")

   for file in sync_files:
      cloud_file = file.replace("ams2/meteor_archive", "archive.allsky.tv")
      if cfe(cloud_file) == 0:
         cmd = "cp " + file + " " + cloud_file
         print(cmd)
         os.system(cmd)

   #days = [ '2020_08_13', '2020_08_12', '2020_08_11', '2020_08_10']
   #super_stacks_many(days)

def resize_video(video_file, w, h):
   new_video_file = video_file.replace(".mp4", "-tn.mp4")
   if cfe(new_video_file) == 0:
      cmd = "/usr/bin/ffmpeg -i " + video_file + " -vf scale=\"" + str(w) + ":" + str(h) + "\" -y " + new_video_file
      os.system(cmd)
   return(new_video_file)

def mln_sync(day, json_conf):


   # sync tn jpgs 
   # sync full and crop mp4s 
   CLOUD_METEOR_DIR = "/mnt/archive.allsky.tv/" + STATION_ID + "/LIVE/METEORS/" + day + "/" 
   cfs = glob.glob(CLOUD_METEOR_DIR + "*")
   cloud_files = {}
   for cf in cfs:
      fn = cf.split("/")[-1]
      cloud_files[fn] = 1

   tns = glob.glob(ARC_DIR + "LIVE/METEORS/" + day + "/*tn.jpg")
   mp4s = glob.glob(ARC_DIR + "LIVE/METEORS/" + day + "/*.mp4")
   jsons = glob.glob(ARC_DIR + "LIVE/METEORS/" + day + "/*.json")
   htmls = glob.glob(ARC_DIR + "LIVE/METEORS/" + day + "/*.html")

   # SYNC IMAGES
   if cfe(CLOUD_METEOR_DIR,1) == 0:
      os.makedirs(CLOUD_METEOR_DIR)
   for tn in tns:
      fn = tn.split("/")[-1]
      cf = CLOUD_METEOR_DIR + fn
     
      if fn not in cloud_files:
         cmd = "cp " + tn + " " + cf
         print(cmd)
         os.system(cmd)
      else:
         print("already sync'd")

   # SYNC MP4s 
   for mp4 in mp4s:
      fn = mp4.split("/")[-1]
      cf = CLOUD_METEOR_DIR + fn
      if "crop-tn.mp4" in fn:
         if fn not in cloud_files:
            cmd = "cp " + mp4 + " " + cf
            print(cmd)
            os.system(cmd)

      if "crop" not in fn: 
         if fn not in cloud_files:
            cmd = "cp " + mp4 + " " + cf
            print("720:", cmd)
            os.system(cmd)
         else: 
            print("SYNC'D?", mp4, cf)
      else:
         if "-tn" not in fn:
            tnf = mp4.replace(".mp4", "-tn.mp4")
            tnfn = tnf.split("/")[-1]
            if cfe(tnf) == 0:
               print("RESIZE.")
               resize_video(mp4, THUMB_W, THUMB_H)
            if tnfn not in cloud_files:
               cf = CLOUD_METEOR_DIR + fn
               cmd = "cp " + mp4 + " " + cf
               os.system(cmd)
   # JSON & HTML

   for tn in jsons:
      fn = tn.split("/")[-1]
      cf = CLOUD_METEOR_DIR + fn
     
      if fn not in cloud_files:
         cmd = "cp " + tn + " " + cf
         print(cmd)
         os.system(cmd)
      else:
         print("already sync'd")
   for tn in htmls:
      fn = tn.split("/")[-1]
      cf = CLOUD_METEOR_DIR + fn
     
      #if fn not in cloud_files:
      if True:
         cmd = "cp " + tn + " " + cf
         print("SYNC REPORT:", cmd)
         os.system(cmd)
      else:
         print("already sync'd")

   cmd = "cp /mnt/ams2/meteor_archive/" + STATION_ID + "/LIVE/METEORS/" + STATION_ID + "*ALL* " + CLOUD_METEOR_DIR + "../"
   os.system(cmd)

   cmd = "cp /mnt/ams2/meteor_archive/" + STATION_ID + "/LIVE/METEORS/" + STATION_ID + "_METEORS.html " + CLOUD_METEOR_DIR + "../"
   os.system(cmd)


def pip_video(video_file, json_conf):
   crop_file = video_file.replace(".mp4", "-crop.mp4")
   js_file = video_file.replace(".mp4", ".json")
   frames,color_frames,subframes,sum_vals,max_vals,pos_vals = load_frames_fast(video_file, json_conf, 0, 1, [], 1,[])
   crop_frames,crop_color_frames,subframes,sum_vals,max_vals,pos_vals = load_frames_fast(crop_file, json_conf, 0, 1, [], 1,[])
   js = load_json_file(js_file)
   hcx1,hcy1,hcx2,hcy2 = js['cropbox_1080']
   cx1,cy1,cx2,cy2 = js['cropbox_720']

   # based on 720 location where should we put the PIP frame?
   if cx1 < 1280 / 2:
      hor = "left"
   else:
      hor = "right"
   if cy1 < 720 / 2:
      vert = "bottom"
   else:
      vert = "top"

   print("HOR:", hor)
   print("VERT:", vert)
   if hor == "right":
      pip_x1 = cx1 - int(crop_frames[0].shape[1] / 2)
      pip_x2 = (pip_x1 + crop_frames[0].shape[1])
   else:
      pip_x1 = cx1 + int(crop_frames[0].shape[1] / 2)
      pip_x2 = (pip_x1 + crop_frames[0].shape[1])

   pip_y1 = cy2 + int(crop_frames[0].shape[0] / 3)
   pip_y2 = (pip_y1 + crop_frames[0].shape[0]) 

   if pip_x1 < 0:
      print("ERROR X OUT ")

      exit()

   if pip_y2 >= 720:   
      pip_y1 = int(cy2 - int(crop_frames[0].shape[0] * 2 ))
      pip_y2 = int((pip_y1 + crop_frames[0].shape[0] ) )

   if pip_y1 <= 0:   
      pip_y1 = 0
      pip_y2 = int((pip_y1 + crop_frames[0].shape[0] ) )

   if pip_y2 - pip_y1 != crop_frames[0].shape[0]:
      print("SHAPE PROBLEM")
      time.sleep(500)
   
   fc = 0
   for cframe in color_frames:
      print("PIPY:", pip_y1, pip_y2)
      print("PIPX:", pip_y1, pip_y2)
      cframe[pip_y1:pip_y2,pip_x1:pip_x2] = crop_color_frames[fc]
      #cv2.line(cframe, (pip_x1,pip_y1), (cx1,cy1), (100,100,100), 1)
      #cv2.line(cframe, (pip_x2,pip_y2), (cx2,cy2), (100,100,100), 1)
      cv2.rectangle(cframe, (pip_x1, pip_y1), (pip_x2, pip_y2), (125,125,125), 1, cv2.LINE_AA)
      if SHOW == 1:
         cv2.imshow('pepe', cframe)
         cv2.waitKey(30)
      fc += 1
   print(js)


def find_best_object(objects):
   best_matches = []
   ld = 0
   for id in objects:
      obj = objects[id]
      uperc, upts = unq_points(objects[id])
      cm = obj_cm(obj['ofns'])
      el = (obj['ofns'][-1] - obj['ofns'][0]) + 1
      if el > 0:
         el_cm = el / cm 
      dist = calc_dist((obj['oxs'][0],obj['oys'][0]), (obj['oxs'][-1],obj['oys'][-1]))
      print("CM:", id, cm)
      print("UP:", id, uperc, upts)
      print("EL:", id, el)
      print("ELCM:", id, el_cm)
      print("Dist:", id, dist)
      if dist > ld:
         ld = dist
         longest_id = id
      print("")
      if cm == el and cm == upts and el_cm == 1:
         best_matches.append(obj)
   if len(best_matches) == 1:
      return(best_matches[0])
   else:
      # just return the longest
      print("Couldn't find best obj:", len(best_matches))
      return(objects[longest_id])

def make_overlay(x1,y1,x2,y2,oh=720,ow=1280):
   x = x1
   y = y1 
   w = x2 - x1 
   h = y2 - y1
   print("xy:", x1,y1,x2,y2)
   print("OV:", x,y,w,h)
   src = np.zeros((oh,ow,3),dtype=np.uint8)


   cv2.rectangle(src, (x, y), (x+w, y+h), (100,100,100), 1, cv2.LINE_AA)

   tmp = cv2.cvtColor(src, cv2.COLOR_BGR2GRAY)
   _,alpha = cv2.threshold(tmp,0,255,cv2.THRESH_BINARY)
   b, g, r = cv2.split(src)
   rgba = [b,g,r, alpha]
   dst = cv2.merge(rgba,4)
   cv2.imwrite("test.png", dst)
 

def get_random_cam(json_conf):
   cam_ids = []
   for cam in json_conf['cameras']:
      ci = json_conf['cameras'][cam]
      cam_ids.append(ci['cams_id'])
   rand_id = random.randint(0, len(cam_ids) - 1)
   return(cam_ids[rand_id])

def broadcast_minutes(json_conf):


   running = check_running("Process.py bcm")
   if running >= 3:
      print("Already running.")
      return()


   LIVE_CLOUD_MIN_DIR = LIVE_MIN_DIR.replace("ams2/meteor_archive", "archive.allsky.tv")
   if cfe(LIVE_CLOUD_MIN_DIR, 1) == 0:
      os.makedirs(LIVE_CLOUD_MIN_DIR)

   if cfe(LIVE_MIN_DIR, 1) == 0:
      os.makedirs(LIVE_MIN_DIR)

   # copy the broadcast file!
   os.system("git pull")
   #os.system("cp /mnt/archive.allsky.tv/LIVE/BROADCAST/broadcast.json ./broadcast.json") 
   bc = load_json_file("./broadcast.json" )
   for event in bc:
      name = event['name']
      start = event['start']
      end = event['end']
      start_time = dt.strptime(start, "%Y_%m_%d_%H_%M_%S") 
      end_time = dt.strptime(end, "%Y_%m_%d_%H_%M_%S") 
      now = dt.now()
      if start_time <= now <= end_time:
         print("The broadcast is running!")
         this_event = event
      else:
         print("There is no broadcast!")
         return()

   for vp in this_event['video_providers']:
      if vp['ams_id'] == STATION_ID:
         bid = vp['bid']
         operator = vp['operator']
         location = vp['location']
         text = operator + " " + location
         upload_mins = []
         for i in range(0,60):
            match = 0
            for b in bid:
               print(i, b)
               if i < 10:
                  if i == b:
                     upload_mins.append(i)
               else:
                  mm = str(i)[1]
                  if str(b) == str(mm):
                     upload_mins.append(i)


   print("Upload these minutes from the last 2 hours (if not already done)!", upload_mins)
   last_hour_dt = dt.now() - datetime.timedelta(hours=1)
   last_hour_string = last_hour_dt.strftime("%Y_%m_%d_%H_5")
   this_hour_string = now.strftime("%Y_%m_%d_%H")
   print("Last 2 hours: ", this_hour_string, last_hour_string)
   cam_id = None
   cam_id = get_random_cam(json_conf)
   min_files = get_min_files(cam_id, this_hour_string, last_hour_string, upload_mins)
   print(min_files)

   new = 0
   for file in min_files:
      fn = file.split("/")[-1]
      el = fn.split("_") 
      wild = el[0] + "_" + el[1] + "_" + el[2] + "_" + el[3] + "_" + el[4] + "*"
      check = glob.glob(LIVE_MIN_DIR + wild)
      #print(LIVE_MIN_DIR + wild, check)
      if len(check) == 0:
      #if True:
         minify_file(file, LIVE_MIN_DIR, text, None )
         new = new + 1
      else:
         print("We already made a file for this minute.")
   if new > 0:
      rsync(LIVE_MIN_DIR + "*", LIVE_CLOUD_MIN_DIR )
   

def rsync(src, dest):
   #cmd = "/usr/bin/rsync -v --ignore-existing " + src + " " + dest
   cmd = "/usr/bin/rsync -v --update " + src + " " + dest
   print(cmd)
   os.system(cmd)

def minify_file(file, outdir, text, md, sd_img = None, hd_img = None):

   print("MINIFY:", file)
   print(md)
   stack_file = file.replace(".mp4", "-stacked.png")
   stack_img = cv2.imread(stack_file)

   if md is not None:
      hdm_x = 1920 / int(md['sd_w']) 
      hdm_y = 1080 / int(md['sd_h']) 
      print("HDMX 1080:", hdm_x, hdm_y) 
      crop_box = find_crop_size(min(md['xs'])*hdm_x,min(md['ys'])*hdm_y,max(md['xs'])*hdm_x,max(md['ys'])*hdm_y, 1920, 1080, 1, 1)

      sx1,sy1,sx2,sy2,smx,smy = crop_box
      sx1,sy1,sx2,sy2 =  int(sx1),int(sy1),int(sx2),int(sy2)
      cropbox_1080 = [sx1,sy1,sx2,sy2]
      
      print(sx1,sy1,sx2,sy2 )
      #cv2.rectangle(hd_img, (sx1, sy1), (sx2, sy2), (255,255,255), 1, cv2.LINE_AA)


      nw = (sx2 - sx1) * 2
      nh = (sy2 - sy1) * 2
      print("NEW W/H:", nw,nh)

      hmx = int(int((sx1 + sx2) * hdm_x) / 2)
      hmy = int(int((sy1 + sy2) * hdm_y) / 2)

      hcx1 = sx1 
      hcy1 = sy1
      hcx2 = hcx1 + (sx2- sx1)
      hcy2 = hcy1 + (sy2- sy1)


      #cv2.rectangle(hd_img, (hcx1, hcy1), (hcx2, hcy2), (255,255,255), 1, cv2.LINE_AA)

      print("ORIG:", md)
      print("CROP:", crop_box[0])
      hdmy = 720 / 1080
      hdmx = 1280 / 1920
      print("HDMX 720:", hdmx, hdmy) 
      #hdmx = 1
      #hdmy = 1
      cx1 = int(crop_box[0] * hdmx)
      cy1 = int(crop_box[1] * hdmy)
      cx2 = int(crop_box[2] * hdmx)
      cy2 = int(crop_box[3] * hdmy)
      mx = int(crop_box[4] * hdmx)
      my = int(crop_box[5] * hdmy)
      crop_box = [cx1,cy1,cx2,cy2,mx,my]
      cropbox_720 = [cx1,cy1,cx2,cy2]
      print("CROP:", crop_box, file)
      make_overlay(cx1,cy1,cx2,cy2)
 

   start_time = time.time()
   fn = file.split("/")[-1]
   outfile = outdir + fn
   if cfe(outfile) == 0:

      #03\:05\:00\:00
      fn = file.split("/")[-1]
      el = fn.split("_")
      y = el[0] 
      mo = el[1] 
      d = el[2] 
      h = el[3] 
      m = el[4] 
      s = el[5] 
      date_txt = "UTC " + y + "/" + mo + "/" + d
      text += " " + date_txt + "_" 
      timecode = h + "\\:" + m + "\\:" + s + "\\:00"
      #timecode = h + "\\:" + m + "\\:" + s 
      cmd = """
      /usr/bin/ffmpeg -i """ + file + """ -vcodec libx264 -crf 35 -vf "scale='1280:720', drawtext=fontfile='fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf':text='""" + text + """ ':box=1: boxcolor=black@0.5: boxborderw=5:x=20:y=h-lh-1:fontsize=16:fontcolor=white:shadowcolor=black:shadowx=1:shadowy=1:timecode='""" + timecode + """':timecode_rate=25" """ + outfile  
#+ " >/dev/null 2>&1"
      if cfe(outfile) == 0:
         print(cmd)
         os.system(cmd)
    
      ## now add overlay
      if md is not None:
         temp_outfile = outfile.replace(".mp4", "-temp.mp4")
         cmd = """/usr/bin/ffmpeg -i """ + outfile + """ -i test.png -filter_complex "overlay=0:0" """ + temp_outfile 
         os.system(cmd)
         os.system("mv " + temp_outfile + " " + outfile)
         print("TEST HERE:", outfile) 
   
   # NOW MAKE THE CROP HD VIDEO
   hw = hcx2 - hcx1
   hh = hcy2 - hcy1
   crop_file = outfile.replace(".mp4", "-crop.mp4")
   if cfe(crop_file) == 0:
      crop_file = crop_video(file, hcx1, hcy1, hw, hh, crop_file)
   try:
      stack_img_crop = stack_img[hcy1:hcy1+hh,hcx1:hcx1+hw]
   except:
      print("NO HD FILE? STACK IS BAD", file)
      stack_img_crop = None


   elapsed_time = time.time() - start_time 
   print("TIME TO MINIFY FILE:", elapsed_time)
   print("MIN FILE:", outfile)
   print("CROP FILE:", crop_file)
   stack_file = outfile.replace(".mp4", ".jpg")
   stack_crop_file = crop_file.replace(".mp4", ".jpg")
   if stack_img_crop is not None:
      cv2.imwrite(stack_crop_file, stack_img_crop)
   cv2.imwrite(stack_file, stack_img)
   print("STACK FILE:", stack_file)
   print("STACK CROP FILE:", stack_crop_file)
   return(outfile, crop_file,cropbox_1080, cropbox_720)

        

def get_min_files(cam_id, this_hour_string, last_hour_string, upload_mins):
   now = dt.now()
   bc_clips = []
   files = glob.glob("/mnt/ams2/HD/" + this_hour_string + "*" + cam_id + "*.mp4")
   for file in sorted(files):

      (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(file)
      elp = now - f_datetime
      sec = elp.total_seconds()
   
      if "trim" not in file and sec > 120:
         el = file.split("_")
         min = el[4]
         print(min, file)
         if int(min) in upload_mins:
            bc_clips.append(file)
   if True:
      files = glob.glob("/mnt/ams2/HD/" + last_hour_string + "*" + cam_id + "*.mp4")
      for file in sorted(files):
       
         if "trim" not in file:
            el = file.split("_")
            min = el[4]
            print(min, file)
            if int(min) in upload_mins:
               bc_clips.append(file)
   return(bc_clips)

def cat_videos(in_wild, outfile):
   print("WILD:", in_wild)
   files = glob.glob(in_wild)
   list_file = outfile.replace(".mp4", "-ALL.txt")
   list = ""
   for file in sorted(files):
      if "ALL" not in file and "crop" not in file:
         list += "file '" + file + "'\n"
   fp = open(list_file, "w")
   fp.write(list)
   fp.close()
   cmd = "/usr/bin/ffmpeg -f concat -safe 0 -i " +list_file + " -c copy -y " + outfile
   print(cmd)
   os.system(cmd)
   print("LIST:", list)

def purge_deleted_live_files (live_dir, live_cloud_dir, day):

   cloud_files = glob.glob(live_cloud_dir + "*.mp4")
   live_meteors = glob.glob(live_dir + day + "*.mp4")
   meteor_dir = "/mnt/ams2/meteors/" + day + "/" 
   print("METEOR DIR:", meteor_dir)
   detected_meteors = glob.glob(meteor_dir + day + "*.mp4")
   for lm in live_meteors:
      fn = lm.split("/")[-1]
      dmf = meteor_dir + fn
      if dmf not in detected_meteors:
         wild = lm.replace(".mp4", "*")
         cmd = "rm " + wild
         wild_fn = fn.replace(".mp4", "*")
         cloud_file = live_cloud_dir + wild_fn
         print(cmd)
         os.system(cmd)
         if cloud_file in cloud_files:
            print("NEED TO DELETE THE CLOUD FILE!")
            cmd = "rm " + cloud_file 
            print(cmd)
            os.system(cmd)
         else:
            print("FILE IS NOT ON CLOUD!")
      else:
         print("\nSTILL GOOD:", lm, "\n")

def parse_hist(js):
   hist = js['sd_objects'][0]['history']
   fns = []
   xs = []
   ys = []
   ws = []
   hs = []
   for row in hist:
      fn,x,y,w,h,nn,no = row
      fns.append(fn)
      xs.append(x)
      ys.append(y)
      ws.append(w)
      hs.append(h)

   m = {}
   m['fns'] = fns
   m['xs'] = xs
   m['ys'] = ys
   m['ws'] = ws
   m['hs'] = hs
 
   return(m)      

def det_table(files, type = "meteor"):
   rpt = ""
   for file in sorted(files):
      vfn= file.split("/")[-1]
      vfn= vfn.replace("-crop-tn.jpg", ".mp4")
      img_url = file.split("/")[-1]
      img_url2 = img_url.replace("-crop", "")
      print("FILE:", file)
      print("URL:", img_url)
      print("URL2:", img_url2)
      fn = vfn.split("-")[0]

      rpt += "<div class='float_div' id='" + vfn + "'>"
      cvfn = vfn.replace(".mp4", "-crop.mp4")
      link = "<a href=\"javascript:swap_pic_to_vid('" + vfn + "', '" + cvfn + "')\">"
      rpt += link + """
         <img title="Meteor" src=\"""" + img_url + """\" onmouseover="this.src='""" + img_url2 + """'" onmouseout="this.src='""" + img_url + """'" /></a>
      """
      rpt += "<br><label style='text-align: center'>" + link + fn + "</a> <br>"
      rpt += "</label></div>"

      #rpt += "<div class='float_div'>"
      #rpt += "<img src=" + img + ">"
      #link = "<a href=" + mf + ">"
      #rpt += "<br><label style='text-align: center'>" + link + fn + "</a> <br>"
      #rpt += "</label></div>"

   return(rpt)


def mln_final(day):
   LIVE_METEOR_DIR = ARC_DIR + "LIVE/METEORS/" 
   LIVE_METEOR_DAY_DIR = ARC_DIR + "LIVE/METEORS/" + day + "/"
   if cfe(LIVE_METEOR_DAY_DIR, 1) == 0:
      os.makedirs(LIVE_METEOR_DAY_DIR)
   cmd = "mv " + LIVE_METEOR_DIR + day + "*.* " + LIVE_METEOR_DAY_DIR
   print(cmd)
   os.system(cmd)

   files = glob.glob(LIVE_METEOR_DAY_DIR + day + "*.jpg")
   for file in files:
      tnf = file.replace(".jpg", "-tn.jpg")
      if "-tn" not in file and cfe(tnf) == 0:
         try:
            img = thumbnail(file, PREVIEW_W, PREVIEW_H,tnf)
         except:
            print("BAD FILE:", file)
            continue
   files = glob.glob(LIVE_METEOR_DAY_DIR + day + "*-crop-tn.jpg")
   html = mk_css()
   html += swap_pic_to_vid()

   html += swap_pic_to_vid()
   print("FILES:", files)
   det_html = det_table(files)
   html += det_html

   out = open(LIVE_METEOR_DAY_DIR + day + "_report.html", "w")
   out.write(html)
   out.close()

def swap_pic_to_vid():
   js = """
   <script>
   function swap_pic_to_vid (div_id,vid_url) {
      var container = document.getElementById(div_id);
      content = " <video width='300' height='169'  id='video' src='" + vid_url + "' autoplay playsinline></video> <br><a href=''>" + 'back' + "</a>"

      container.innerHTML = content;
   }
   </script>

   """
   return(js)

def meteors_last_night(json_conf, day=None):
   sd_frame = None
   hd_frame = None
   # sync best meteors within the last 48 hours to the LIVE meteor dir
   station_id = json_conf['site']['ams_id']
   if "extra_text" in json_conf['site']:
      text = "AMSMeteors.org / " + json_conf['site']['extra_text']
   else: 
      text = "AMSmeters.org " 
   best_meteors = []
   LAST_NIGHT_DIR = ARC_DIR + "LIVE/METEORS_LAST_NIGHT/"
   LIVE_METEOR_DIR = ARC_DIR + "LIVE/METEORS/"
   FINAL_DIR = ARC_DIR + "LIVE/METEORS/" + day + "/"

   LAST_NIGHT_CLOUD_DIR = LIVE_METEOR_DIR.replace("ams2/meteor_archive", "archive.allsky.tv")
   LIVE_CLOUD_METEOR_DIR = LIVE_METEOR_DIR.replace("ams2/meteor_archive", "archive.allsky.tv")

   if cfe(LAST_NIGHT_CLOUD_DIR,1) == 0:
      os.makedirs(LAST_NIGHT_CLOUD_DIR)
   if cfe(LIVE_CLOUD_METEOR_DIR,1) == 0:
      os.makedirs(LIVE_CLOUD_METEOR_DIR)
   
   purge_deleted_live_files (LIVE_METEOR_DIR, LIVE_CLOUD_METEOR_DIR, day)

   if cfe(LIVE_METEOR_DIR,1) == 0:
      os.makedirs(LIVE_METEOR_DIR)
   if cfe(LAST_NIGHT_DIR,1) == 0:
      os.makedirs(LAST_NIGHT_DIR)
   if day is None:
      now = dt.now()
      day = now.strftime("%Y_%m_%d")
   else:   
      now = dt.strptime(day, "%Y_%m_%d")
      day = now.strftime("%Y_%m_%d")

   yesterday = now - datetime.timedelta(days = 1) 
   yest = yesterday.strftime("%Y_%m_%d")

   mdir = "/mnt/ams2/meteors/" + day + "/"

   purge_deleted_live_files (LIVE_METEOR_DIR, LIVE_CLOUD_METEOR_DIR, day)

   files = glob.glob(mdir + "*.json")
   meteor_data = {}

   # TESTING 1 FILE
   #files = ['/mnt/ams2/meteors/2020_08_13/2020_08_13_07_26_25_000_010002-trim-0176.json']

   for file in sorted(files):
      js = load_json_file(file)
      if "hd_trim" in js:
         hd_file = js['hd_trim']
      else:
         print("JS ERR NO HD TRIM:", js)
         continue 
      sdv = file.replace(".json", ".mp4")
      fn = hd_file.split("/")[-1]
      if cfe(FINAL_DIR + fn) == 1:
         print("SKIP DONE!", FINAL_DIR + fn)
         continue

      if cfe(sdv) == 1:
         if "sd_w" not in js:
            sd_w, sd_h,tf = ffprobe(sdv)
            js['sd_w'] = sd_w
            js['sd_h'] = sd_h
            save_json_file(file, js)
         else:
            sd_w = js['sd_w']
            sd_h = js['sd_h']

      if "vals_data" not in js:

         frames,color_frames,subframes,sum_vals,max_vals,pos_vals = load_frames_fast(sdv, json_conf, 0, 1, [], 1,[])
         sd_frame = frames[0]
         hd_frame = cv2.resize(sd_frame, (1920,1080)) 
         vals_data = {}
         vals_data['sum_vals'] = sum_vals
         vals_data['max_vals'] = max_vals
         vals_data['pos_vals'] = pos_vals

         print("DETECT IN VALS!")
         events, objects, total_frames = detect_in_vals(file, None, vals_data)
         print("DETECT IN CLIP!")
         sd_objects, frames = detect_meteor_in_clip(sdv, frames, fn = 0, crop_x = 0, crop_y = 0, hd_in = 0)
         print("END DETECT IN CLIP!")

         print("TEST METEORS!")
         sd_meteors = {}
         for id in sd_objects:
            sd_objects[id] = analyze_object(sd_objects[id]) 
            if sd_objects[id]['report']['meteor'] == 1:
               print("METEOR FOUND:", sd_objects[id])
               sd_meteors[id] = sd_objects[id]
         sd_objects = sd_meteors

         if len(sd_objects) >= 1:
            objects = sd_objects
       


         vals_data['events'] = events
         vals_data['objects'] = objects
         js['vals_data'] = vals_data
         save_json_file(file, js)
      else:
         vals_data = js['vals_data']

      events = vals_data['events']
      objects = vals_data['objects']

      mm = {}
      if len(objects) == 1:
         for obj in objects:
            #print(obj, objects[obj]['report']['meteor'], objects[obj]['report']['non_meteor'], objects[obj]['report']['bad_items'])
            fns = objects[obj]['ofns']
            xs = objects[obj]['oxs']
            ys = objects[obj]['oys']
            mm['xs'] = xs
            mm['ys'] = ys
      elif len(objects) == 0:
         print("NO OBJS!")
         continue 
      else:
         print("MANY OBJS!")
         best_obj = find_best_object(objects)
         print("BEST:", best_obj)
         fns = best_obj['ofns']
         xs = best_obj['oxs']
         ys = best_obj['oys']
         mm['xs'] = xs
         mm['ys'] = ys

      max_x = max(mm['xs'])
      min_x = min(mm['xs'])
      max_y = max(mm['ys'])
      min_y = min(mm['ys'])


           
          
      if 'sd_objects' not in js:
         print("ER:", js)
         exit 
      for id in js['vals_data']['objects']:
         meteor_obj = js['vals_data']['objects'][id]
      if len(meteor_obj['oxs']) >= 3:
         sdf = file.replace(".json", ".mp4")
         #mm = parse_hist(js)
         print("JS OBJS!", file, js['hd_trim'], mm)
         best_meteors.append(js['hd_trim'])
         hd_file = js['hd_trim']
         hdf = hd_file.split("/")[-1]
         mm['hd_file'] = js['hd_trim']
         mm['sd_file'] = sdf 
         mm['sd_w'] = sd_w 
         mm['sd_h'] = sd_h
         meteor_data[hdf] = mm
         test = "TESTING"
         hd_outfile, hd_cropfile, cropbox_1080,cropbox_720 = minify_file(mm['hd_file'], LIVE_METEOR_DIR, text, meteor_data[hdf], sd_frame, hd_frame)
         mjf = hd_outfile.replace(".mp4", ".json")
         meteor_obj['cropbox_1080'] = cropbox_1080
         meteor_obj['cropbox_720'] = cropbox_720
         meteor_obj['hd_file'] = js['hd_trim']
         meteor_obj['sd_file'] = sdf 
         meteor_obj['sd_w'] = sd_w 
         meteor_obj['sd_h'] = sd_h
         meteor_data[hdf]['meteor_obj'] = meteor_obj
         save_json_file(mjf, meteor_obj)
         print(mjf)
      print("END LOOP!", best_meteors)

   mdjsf = LIVE_METEOR_DIR + day + ".json"
   save_json_file(mdjsf, meteor_data) 
      

   #for bm in best_meteors:
   #   print("BEST:", bm)
   #   bmf = bm.split("/")[-1]
   #   md = bmf[0:10]
   #   hd_file = "/mnt/ams2/meteors/" + md + "/" + bmf
       
   #   minify_file(hd_file, LIVE_METEOR_DIR, text, meteor_data[bmf])

   cat_videos(LIVE_METEOR_DIR + day + "/" + day + "*.mp4", LAST_NIGHT_DIR + day + "-" + station_id  + ".mp4")
   os.system("rm " + LAST_NIGHT_DIR + "*.txt") 
   mln_final(day)
   meteor_index(day)
   print("FINAL!")

   super_stacks(day)
   mln_sync(day, json_conf)
   print("DONE MLN FOR", day)
   exit()

   rsync(LIVE_METEOR_DIR + "*", LIVE_CLOUD_METEOR_DIR )

   #rsync(LAST_NIGHT_DIR + "*", LAST_NIGHT_CLOUD_DIR)

def meteor_index(day):
   index = []
   files = glob.glob(ARC_DIR + "LIVE/METEORS/" + day + "/*.json")
   for file in files:
      fn = file.split("/")[-1]
      el = fn.split("_")
      if len(el) > 3:
         print(file)
         js = load_json_file(file)
         print(js)
         meteor = {}
         meteor['hd_file'] = js['hd_file'].split("/")[-1]
         meteor['sd_file'] = js['sd_file'].split("/")[-1]
         meteor['sd_w'] = js['sd_w']
         meteor['sd_h'] = js['sd_h'] 
         meteor['fns'] = js['ofns'] 
         meteor['xs'] = js['oxs'] 
         meteor['ys'] = js['oys'] 
         meteor['ints'] = js['oint'] 
         meteor['cropbox_1080'] = js['cropbox_1080'] 
         meteor['cropbox_720'] = js['cropbox_720'] 
         index.append(meteor)
   save_json_file(ARC_DIR + "LIVE/METEORS/" + day + "/" + day + "-" + STATION_ID + "-METEORS.json", index)
   print(ARC_DIR + "LIVE/METEORS/" + day + "/" + day + "-" + STATION_ID + "-METEORS.json" )

def test_meteors(objs):

   mobjs = {}

   for id in objs:
      obj = objs[id]

      uperc, upts = unq_points(obj)
      cm = obj_cm(obj['ofns'])
      if cm < 3:
         continue
      el = (obj['ofns'][-1] - obj['ofns'][0]) + 1
      if el > 0:
         el_cm = el / cm
      dist = calc_dist((obj['oxs'][0],obj['oys'][0]), (obj['oxs'][-1],obj['oys'][-1]))
      if dist < 5:
         continue
      (i_max_times, i_pos_neg_perc, i_perc_val) = analyze_intensity(obj['oint'])
      if i_max_times <= 1:
         continue
      if i_pos_neg_perc <= .75:
         continue


      res = meteor_direction_test(obj['oxs'], obj['oys'])
      print(obj)
      print("CM: ", cm)
      print("EL: ", el)
      print("EL_CM: ", el_cm)
      print("DIST PX: ", dist)
      print("Direction: ", res)
      print("Intensity Min Max Peak:", i_max_times)
      print("Intensity Pos/Nig Perc:" , i_pos_neg_perc)
      print("Intensity Perc Val:", i_perc_val) 
      obj['report'] = {}
      obj['report']['meteor_yn'] = 'Y'
      obj['report']['cm'] = cm
      obj['report']['el'] = el
      obj['report']['el_cm'] = el_cm
      obj['report']['dist_px'] = dist
      obj['report']['direction_test'] = res
      obj['report']['int_min_max'] = i_max_times
      obj['report']['int_pos_perc'] = i_pos_neg_perc
      mobjs[id] = obj
   return(mobjs)

def meteor_min_files(day, json_conf):
   year, month, dom = day.split("_")
   meteor_dir = METEOR_ARC_DIR + year + "/" + month + "/" + dom + "/"  
   hd_files = glob.glob("/mnt/ams2/HD/" + year + "_" + month + "_" + dom + "*")

   live_dir = ARC_DIR + "LIVE/" 
   if cfe(live_dir, 1) == 0:
      os.makedirs(live_dir)
   #print(meteor_dir)
   meteor_files = glob.glob(meteor_dir + "*.json")
   for meteor_file in meteor_files:
      print(meteor_file)
      cp = load_json_file(meteor_file)
      print(cp)
      print("ANG:", cp['report']['classify']['ang_sep_px'], cp['report']['classify']['ang_sep_deg'])
      if cp['report']['classify']['ang_sep_px'] < 7:
         continue
      hd_file = get_hd_min_file(meteor_file, hd_files)
      if hd_file == 0:
         print("HD FILE NOT FOUND.", hd_file)
         return()

      mf =meteor_file.split("/")[-1] 
      el = mf.split("-trim")
      mf_root = el[0]
      hdf = hd_file.split("/")[-1]
      min_out_file = live_dir + hdf
      
      if cfe(min_out_file) == 0: 
         cmd = "/usr/bin/ffmpeg -i " + hd_file + " -vcodec libx264 -crf 35 -vf 'scale=1280:720' -y " + min_out_file
         os.system(cmd)
         print(cmd)

def get_hd_min_file(meteor_file, hd_files):
   (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(meteor_file)
   search_str = fy + "_" + fm + "_" + fd + "_" + fh + "_" + fmin 
   for file in hd_files:
      if search_str in file and cam in file and "trim" not in file:
         return(file)


   print(search_str)
   if len(hd_files) == 1: 
      return(hd_files[0])
   if len(hd_files) > 1:
      for hdf in hd_files:
         if "trim" not in hdf:
            return(hdf)
   return(0)

def broadcast_live_meteors():
   LIVE_URL = "rtmp://a.rtmp.youtube.com/live2/"
   LIVE_KEY = "mg2f-1ub9-yehd-8h32-a3dh"
   live_files = {}
   live_dir = ARC_DIR + "LIVE/"
   live_files = update_live_files(live_dir, live_files)
   run = True
   lc = 0
   qc = 0
   tc = len(live_files.keys())
   while run == True:
      if qc == 0 or lc % 5 == 0:
         queue = build_queue(live_files) 
         save_json_file(live_dir + "livefiles.json", live_files)
         if len(queue) == 0:
            print("Oh no we have no files left in the queue :(")
            return()
      play_file = queue[0]
      broadcast_clip(play_file, LIVE_URL, LIVE_KEY)
      print("Play first movie in the queue:", play_file)
      live_files[play_file]['played'] = 1
      lc += 1 
   print(live_dir + "livefiles.json")

def build_queue(live_files):
   queue = []
   for lf in sorted(live_files.keys()):
      if live_files[lf]['played'] == 0:
         queue.append(lf)
   return(queue)

def update_live_files(live_dir, live_files):
   lfs = glob.glob(live_dir + "*.mp4")
   for lf in lfs:
      if lf not in live_files:
         live_files[lf] =  {"played": 0}
   return(live_files)

def broadcast_clip(SOURCE, URL, KEY):
   
   #YOUTUBE_URL="rtmp://a.rtmp.youtube.com/live2/cvep-ehuy-9tg5-737j"  # URL de base RTMP youtube
   #FB_URL="rtmps://live-api-s.facebook.com:443/rtmp/10157538776313530?s_bl=1&s_ps=1&s_sml=3&s_sw=0&s_vt=api-s&a=AbxBjTySKHROyaX9"
   #SOURCE="rtsp://192.168.76.74/user=admin&password=&channel=1&stream=0.sdp"              # Source UDP (voir les annonces SAP)
   LIVE_URL = URL + KEY
   FPS = "25"
   VBR = "256k"
   QUAL= "fast"
   ffmpeg = """
    /usr/bin/ffmpeg -ar 44100 -ac 2 -acodec pcm_s16le -f s16le -ac 2 -i /dev/zero  \
    -i """ + SOURCE + """ -deinterlace -vf scale=1280:720 \
    -vcodec libx264 -pix_fmt yuv420p -preset fast -r 25 -g $((25 * 2)) -b:v """ + VBR  + """ \
    -acodec libmp3lame -ar 44100 -threads 6 -qscale 3 -b:a 712000 -bufsize 512k \
    -f flv """ +  LIVE_URL
   print(ffmpeg)
   os.system(ffmpeg)
