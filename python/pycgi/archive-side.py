#!/usr/bin/python3
import datetime
import math
import numpy as np
import json
from collections import defaultdict
#from random import *
import random
import glob
import subprocess 
import cgi
import cgitb
import os
video_dir = "/mnt/ams2/SD/"
from pathlib import Path


json_file = open('../../conf/as6.json')
json_str = json_file.read()
json_conf = json.loads(json_str)
proc_dir = json_conf['site']['proc_dir']


cgitb.enable()
print ("Content-type: text/html\n\n")
print (" <style> .active { background: #ff0000; } .inactive { background: #ffffff; } body { background-color: #000000; color: #ffffff } </style>")



def object_report (moving_objects, type):
   if len(moving_objects) > 0:
      print ("<table>")
      print("<TR><TD>Object ID</td><td>Count</td><td>Frist Frame</td><td>Last Frame</td><td>Slope</td><td>Distance</td><td>Elapsed Frames</td><td> px_per_frames</td><td> status</td></tr>")
   for object in moving_objects:
      (obj_id, count, first_frame, last_frame, slope, distance, elapsed_frames, px_per_frames, status) = object
      if type == 'meteor' and len(status) == 0:
         print ("<TR><TD>" + str(obj_id) + "</td><td>" + str(count) + "</td><td>" + str(first_frame) + "</td><td>" + str(last_frame) + "</td><td>" + str(slope) + "</td><td>" + str(distance) + "</td><td>" + str(elapsed_frames) + "</td><td>" + str(px_per_frames) + "</td><td>" +  str(status) + "</td></tr>") 
      else:
         if count >= 3:
            print ("<TR><TD>" + str(obj_id) + "</td><td>" + str(count) + "</td><td>" + str(first_frame) + "</td><td>" + str(last_frame) + "</td><td>" + str(slope) + "</td><td>" + str(distance) + "</td><td>" + str(elapsed_frames) + "</td><td>" + str(px_per_frames) + "</td><td>" +  str(status) + "</td></tr>") 
   if len(moving_objects) > 0:
      print ("</table>")
   return("", "")


def calc_dist(p1,p2):
   x1,y1 = p1
   x2,y2 = p2
   dist = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
   print ("<HR>DIST: ", x1,y1,x2,y2,dist,"<HR>")
   return dist


def find_slope(p1,p2):
   (x1,y1) = p1
   (x2,y2) = p2
   top = y2 - y1
   bottom = x2 - y2
   if bottom > 0:
      slope = top / bottom
   else:
      slope = "na"
   #print(x1,y1,x2,y2,slope)
   return(slope)


def get_bp_motion(motion_file):

   file = open(motion_file, "r")
   event = []
   events = []


   last_cons_mo = 0
   no_motion = 0

   for line in file:
      line = line.replace("\n", "")
      (frameno, mo, bpf, cons_mo) = line.split(",");
      if int(cons_mo) > 0:
         #print ("Cons:", cons_mo);
         #print (frameno,mo,bpf,cons_mo,no_motion)
         if int(cons_mo) != int(last_cons_mo):
            event.append([frameno,mo,bpf,cons_mo])
            no_motion = 0
      else:
         if len(event) >= 3 or no_motion >2:
            if len(event) > 2:
               events.append(event)
            event = []
         no_motion = no_motion +1
      last_cons_mo = cons_mo


   return(events)

def slope_match(pts, hist):
   slopes = []
   x,y = pts
   sm = 0
   print ("<BR> MATCHING SLOPE FOR X,Y: ", x,y, "<BR>")
   print ("<BR> HIST: ", hist, "<BR>")
   for hx,hy in hist:
      slope = find_slope((x,y),(hx,hy))
      print ("SLOPE:", x,y,hx,hy,slope,"<BR>")
      if slope != "na":
         slopes.append(slope)
   slope_avg = float(sum(slopes) / len(slopes))
   for sl in slopes:
      if slope_avg - .1 <= sl <= slope_avg + .1:
         sm = sm + 1
   if len(slopes) > 0:
      smp = sm / len(slopes)
   return(smp, sm)

def check_hist(x,y,hist):
   #print("<HR>LEN HIST: ", len(hist), "<HR>")
   for (fn,hx,hy) in hist:
      if hx - 20 <= x <= hx + 20 and hy - 20 <= y <= hy +20:
         return(1)
   return(0)

def find_object(fn, pt, moving_objects):
   x,y = pt
   prox_match = 0
   if moving_objects is None:
      lenstr = "0"
   else:
      lenstr = str(len(moving_objects))

   print ("<h4>Current Known Objects that could match x,y " + str(x) + "," + str(y) + " " + lenstr + "</h4>")
   if moving_objects is None:
      # there are no objects yet, so just add this one and return. 
      oid = 0
      mo = []
      moving_objects = np.array([ [[oid],[x],[y],[[fn,x,y],[fn,x,y]] ]])
      #print("NP SIZE & SHAPE:", np.size(moving_objects,0),np.size(moving_objects,1))
      return(oid, moving_objects)
   else:
      # match based on proximity to pixel history of each object 
      #print("NP SIZE & SHAPE:", np.size(moving_objects,0),np.size(moving_objects,1))
      #print("MOVING OBJECTS:", moving_objects[0])
      rowc = 0
      match_id = None
      for (oid,ox,oy,hist) in moving_objects:
         found_in_hist = check_hist(x,y,hist)
         #print("<BR>FOUND IN HIST?" , found_in_hist, "<BR>")
         if found_in_hist == 1:
            prox_match = 1
            match_id = oid

   #can't find match so make new one
   if prox_match == 0:
      oid = new_obj_id((x,y), moving_objects) 
      moving_objects = np.append(moving_objects, [ [[oid],[x],[y],[[fn,x,y],[fn,x,y]]] ], axis=0)
   else:
      oid,ox,oy,hist = moving_objects[match_id][0]
      hist.append([fn,x,y])
      moving_objects[match_id][0] = [ [[oid],[ox],[oy],[hist]] ]
      
   return(oid, moving_objects)

def new_obj_id(pt, moving_objects):
   x,y = pt
   #print ("<BR> MOVING OBJS : ", moving_objects)
   #np_mo = np.array([[[1],[44],[55],[1,44,55]],[[2],[33],[22],[2,33,22]]])
   max_id = np.max(moving_objects, axis=0)
   #print ("MAX:", max_id)
   new_id = max_id[0][0] + 1
   #print ("MAX ID IS : ", max_id)
   #print ("NEW ID IS : ", new_id)
   return(new_id) 

def track_objects(pts,moving_objects):
   x,y = pts
   found_object = 0
   idx = 0
   slope = 0 
   slope_obj_found = 0 
   smp = 0
   for (id,ox,oy,hist) in moving_objects:
      slope_obj_found = 0 
      smp = 0
      hc = 0
      for (hx,hy) in hist:
         if hx - 5 <= x <= hx + 5 and hy - 5 <= y <= hy +5:
            found_object = idx
         if hc > 0:
            slope = find_slope((hx,hy),(last_hx,last_hy))

         last_hx = hx
         last_hy = hy
         hc = hc + 1
      if len(hist) > 3:
         smp,smt = slope_match((x,y),hist)
      else:
         smp = 0
         smt = 0
    
      if smp >= .95 and smt > 10:
         print ("ID:", x,y, idx, "SMP:", smp, smt, "<BR>")
         slope_obj_found = idx
      idx = idx + 1
      
   if found_object == 0:
      print ("<BR>OBJECT NOT FOUND : ", found_object, slope_obj_found)
      if slope_obj_found != 0:
         found_object = slope_obj_found
      else:
         found_object = idx 
      object = (found_object, x, y, [[x,y]])
      moving_objects.append(object)
   else:
      #if slope_obj_found != 0 and (slope_obj_found != found_object):
      #   found_object = slope_obj_found
      print ("<BR>FOUND OBJECT IS : ", found_object)
      id, ox, oy, hist = moving_objects[found_object]
      hist.append(([x,y]))
      moving_objects[found_object] = (id,ox,oy,(hist))
   return(found_object, moving_objects)
      
      
def find_frame_data_file(video_file):
   el = video_file.split("/")
   fn = el[-1]
   fn_base = fn.replace(".mp4", "")
   dir_base = video_file.replace(fn, "")
   reject_file = dir_base + "data/" + fn_base + ".mp4-rejected.txt"
   confirm_file = dir_base + "data/" + fn_base + "-confirm.txt"
   file_exists = Path(reject_file)
   if file_exists.is_file() == True:
      return("reject", reject_file)
   file_exists = Path(confirm_file)
   if file_exists.is_file() == True:
      return("confirm", confirm_file)
   return("notfound", "")


def convert_filename_to_date_cam(file):
   el = file.split("/")
   filename = el[-1]
   filename = filename.replace(".mp4" ,"")
   fy,fm,fd,fh,fmin,fs,fms,cam = filename.split("_")
   f_date_str = fy + "-" + fm + "-" + fd + " " + fh + ":" + fmin + ":" + fs
   f_datetime = datetime.datetime.strptime(f_date_str, "%Y-%m-%d %H:%M:%S")
   return(f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs)


def get_motion_events(frame_data):
   events = []
   event = []
   no_motion = 0
   for frame in frame_data:
      (na, frame_no, hist, cons_mo) = frame
      #print(frame_no, hist, cons_mo, no_motion, "<BR>")
      if int(cons_mo) > 0:
         if int(cons_mo) != int(last_cons_mo):
            event.append([frame_no,hist,cons_mo])
            no_motion = 0
      else:
         if len(event) >= 3 and no_motion >2:
            if len(event) > 2:
               events.append(event)
            event = []
         no_motion = no_motion +1
      last_cons_mo = cons_mo
   return(events)   


def examine_video_clip(video_file):
   (motion, reject, confirm) = get_motion_file(video_file)
   jpg = video_file.replace(".mp4", "-stacked.png")
   el = jpg.split("/")
   fn = el[-1]
   base = jpg.replace(fn, "")
   stack_file = base + "/images/" + fn


   motion_file = stack_file.replace("-stacked.png", "-motion.txt")
   motion_file = motion_file.replace("images", "data")

   
   (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(video_file)
   print("1-MIN VIDEO START TIME: ", f_datetime, "<BR>")
   print("CAM NO: ", cam, "<BR>")
   print("1-MIN VIDEO FILE: <A target=_blank href=" + str(video_file) +  ">" + str(video_file) + "</a><br>")
   #print("STACK FILE: ", stack_file, "<BR>")
   print("MOTION FILE: ", motion_file, "<BR>")
   print("1-MIN STACK FILE:<BR><img src=" + stack_file + "><BR>")
   fp = open(motion_file, "r")
   print("<h1>Bright Pixel Detection in 1-MIN Clip</h1>")
   print ("<table border=1>")
   print("<TR><TD>Frame</td><td>BPF</td><td>Motion</td><td>Frame Time</td></tr>")
   for line in fp: 
      (frameno, mo, bpf, cons_mo) = line.split(",");
       
      if int(cons_mo) > 0:
         extra_sec = int(frameno) / 25 
         frame_time = f_datetime + datetime.timedelta(0,extra_sec)
         print("<TR><TD>" + str(frameno) + "</td><td>" + str(bpf) + "</td><td>" + str(cons_mo) + "</td><td>" + str(frame_time.time()) + "</td></tr>")

   print ("</table>")
   print ("<h1>Trimmed Clips</h1>")
   trim_files = get_trim_clips(video_file)
   for trim_file in trim_files:
      status, frame_data_file = find_frame_data_file(trim_file)
      print("TRIM VIDEO FILE : <a target=_blank href=" + str(trim_file) + ">" + str(trim_file) + "</a><BR>")
      meteor_video_file = trim_file.replace(".mp4", "-meteor.mp4")
      el = meteor_video_file.split("/")
      mvfn = el[-1]
 
      meteor_data_file = base + "/data/" + mvfn 
      meteor_data_file = meteor_data_file.replace(".mp4", ".txt")

      file_exists = Path(meteor_video_file)
      if file_exists.is_file() == True:
         print("METEOR VIDEO FILE : <a target=_blank href=" + str(meteor_video_file) + ">" + str(meteor_video_file) + "</a><BR>")
         
         moving_objects = get_code(meteor_data_file)
      print("FRAME DATA FILE: ", frame_data_file, "<BR>")
      frame_data = get_frame_data(frame_data_file)
      events = get_motion_events(frame_data)
      ec = 1
      print("<h1>Events</h1>")
      for event in events: 
         print ("<h2>Event #: " + str(ec) + " " + str(len(event)) + "</h2>")
         print("<table border=1>")
         print("<tr><td>Frame No</td><td>CNTs</td><Td>Cons Mo</td></tr>")
         for (frame_no, hist, cons_mo) in event:
            print ("<tr><td>" + str(frame_no) + "</td><td>")
            for cnt in hist:
               (cfn, x,y,w,h,fxt) = cnt
               print("" + str(x) + " " + str(y) + "<br>")
            print("</td><td>" + str(cons_mo) + "</td></tr>")
         ec = ec + 1
         print("</table>")
      
      #print ("<h1>Motion Detected Frames in Trimmed Clip</h1>")
      #print ("<table border=1>")
      #print("<TR><TD>Frame</td><td>Objects</td><td>Motion</td></tr>")
      #for (na, frame_no, hist, cons_mo) in frame_data:
      #   if len(hist) > 0 and int(cons_mo) > 0:
      #      print("<tr><td>" + str(frame_no) + "</td><td>" + str(hist) + "</td><td>" +  str(cons_mo) + "</td></tr>")
      #print ("</table>")
#
      print("<h1>Object Report</h1>")
      moving_objects = get_code(meteor_data_file)
      data, status = object_report(moving_objects, "meteor")  
 

   exit()

   cams_detect = 0
   frame_file_base = video_file.replace(".mp4", "")
   print("Detection Details: <UL>")
   print("SD 1-Minute Clip: <BR><a href=" + video_file + ">" + video_file + "</a><UL>")
   if (motion == 1):
      print ("<LI>Motion detected " )
      if confirm == 1:
         print("and confirmed.</li>")
      if reject == 1:
         print("but rejected.")
   else:
      print ("<LI>Motion NOT Detected</li>" )
   print("</UL>")
   print("<h2>Stack File</h2>")
   print("<img src=" + stack_file + ">")

   trim_files = get_trim_clips(video_file)
   print("<h2>Trimmed Clips</h2>")
   clips = 1 
   frame_data_sets = {}
   if motion == 1:
      events = get_bp_motion(motion_file)


   moving_objects = None
   tfc = 1
   for trim_file in trim_files:

      confirm_file = trim_file.replace(".mp4", "-confirm.txt")
      frame_data_sets[clips] = get_frame_data(confirm_file)
      #print("CONF: ", clips, confirm_file, "<BR>")
      print ("SD Clip " + str(clips) + "<p><iframe width=640 height=480 src=" + trim_file + "></iframe></p>")
      print ("HD Clip " + str(clips) + "<BR>")
      #print("BP DETECT DATA:", events[clips], "<BR>")
      #print("MOTION FRAME DATA:", frame_data_sets[clips], "<BR>")
      print ("<table border=1>")  
      print("<tr><td>Main Clip Frame #</td><td>Factor</td><td>Consectuive Frame</td></tr>")
      for mf in events[clips-1]:
         print ("<tr><td>" + str(mf[0]) + "</td><td>" + str(mf[2]) + "</td><td>" + str(mf[3]) + "</td></tr>")
      print ("</table>")
      fc = 1
      frame_data = frame_data_sets[clips]
      print("<table border=1>")
      print("<tr><td>Trim Clip</td><td>Frame #</td><td>Contours (x,y,w,h)</td><td>Consectuive Frame</td><td>Image</td></tr>")
      fc =1 
      for fd in frame_data:
         print ("<tr>") 
         print ("<td>" + str(fd[0]) + "</td><td>" + str(fd[1]) + "</td>" )
         print ("<td>")

         fd_temp = sorted(fd[2], key=lambda x: x[3], reverse=True)
         if len(fd_temp) > 0 and len(fd_temp) < 8:
            print("<table border=1 cellpadding=3 cellspacing=3>")
            print ("<tr><td>X</td><td>Y</td><td>W</td><td>H</td><td>OBJ ID</td></tr>")
            for x,y,w,h in fd_temp:
               #object, moving_objects = track_objects((x,y), moving_objects)
               object, moving_objects = find_object(tfc, (x,y), moving_objects)
               print ("<tr><td>" + str(x) + "</td><td>" + str(y) + "</td><td>" + str(w) + "</td><td>" + str(h) + "</td><td>" + str(object) + "</td> </tr>")
            print("</table>") 
         print ("</td><td>" + str(fd[3]) + "</td>" )
         frame_file_base = trim_file.replace(".mp4", "")
         frame_image = frame_file_base + "-fr" + str(fc) + "-tn.png"
         print("<td><img src=" + frame_image + "></td></tr>")
         fc = fc + 1
         tfc = tfc + 1
      print ("</table>")
      clips = clips + 1

   

   print ("<H1>Object Report</h1>")
   print ("<table border=1>")
   print ("<tr><td>Obj ID</td><td>Count</td><td>First</td><td>Last</td><td>Slope</td><td>Dist</td><td>Elapsed Frames</td><td>PX Dist/Frame</td><td>Status</td></tr>")
   for object in moving_objects:
      status = []
      hist = object[3]
      first = hist[0]
      last = hist[-1]
      p1 = first[1], first[2]
      p2 = last[1], last[2]
      hist_len = len(object[3]) - 1
      elp_frms = last[0] - first[0]  
 
      if hist_len > 3:
         slope = find_slope(p1,p2)
         dist = calc_dist(p1,p2)
      else:
         slope = "na"
         dist = 0
      if elp_frms > 0 and dist != "na":
         px_per_frame =dist / elp_frms 
      else:
         px_per_frame = 0
      if elp_frms > 200:
         status.append(('reject', 'object exists for too long to be a meteor.'))
      if px_per_frame < 1: 
         status.append(('reject', 'object does not move fast enough to be a meteor.'))
      if dist < 5:
         status.append(('reject', 'object does not move far enough to be a meteor.'))
      if hist_len < 3:
         status.append(('reject', 'object does not exist long enough.'))

      print ("<tr><td>" + str(object[0]) + "</td><td>" + str(hist_len) + "</td><td>" + str(first) + "</td><td>" + str(last) + "</td><td>" + str(slope) + "</td><td>" + str(dist) + "</td><td>" + str(elp_frms) + "</td><td>" + str(px_per_frame) + "</td><td>" + str(status) + "<td></tr>")
   print ("</table>")
   if cams_detect == 1:
      print ("<h2>Cams detection info</h2>") 


def get_trim_clips(video_file):
   trims = []
   trim_wildcard = video_file.replace(".mp4", "-trim*.mp4")
   trim_files = glob.glob(trim_wildcard)
   for trim in trim_files:
      if "meteor" not in trim:
         trims.append(trim)
   return(trims)

def get_frame_data(frame_data_file):
   fdf = open(frame_data_file)
   d = {}
   code = "frame_data = "
   for line in fdf:
      code = code + line
   exec (code,  d)

   return(d['frame_data'])


def get_code(code_file):
#   print(code_file)
   fdf = open(code_file)
   d = {}
   code = "data = "
   for line in fdf:
      code = code + line
   exec (code,  d)

   return(d['data'])  
 

def get_motion_file(video_file):
   motion_found = 0
   reject = 0
   confirm = 0
   el = video_file.split("/")
   motion_check = video_file.replace(".mp4", "-motion.txt")
   motion_fn = el[-1]
   motion_reject = proc_dir + "rejects/" + motion_fn
   # first check for motion file in proc2 dir
   file_exists = Path(motion_check)
   if file_exists.is_file() == True:
      # motion file still exists in proc2 dir, it must have been confirmed?
      motion_found = 1
      confirm = 1
   else:
      # motion file doesn't exists in proc2 dir, lets check_reject dir
      file_exists = Path(motion_reject)
      if file_exists.is_file() == True:
         # motion file found in reject dir
         motion_found = 1
         reject = 1
      else:
         # motion file not found. 
         motion_found = 0
   return(motion_found, reject, confirm)


def get_days():
   days = []
   files = os.listdir(proc_dir)
   for file in files:
      if file[0] == "2":
         # the above line will stop working in 980 years i.e. y3k
         days.append(file)
   return(sorted(days, reverse=True))

def load_scan_file(day, cam_num):
   scan_file = proc_dir + day + "/" + "cam" + str(cam_num) + ".txt" 
   img_dict = dict()
   file_exists = Path(scan_file)
   od = 0
   if (file_exists.is_file()):
      sfp = open(scan_file, "r")
      for line in sfp:
         (img_file, status_desc, hit) = line.split(",") 
         img_dict[img_file] = {}
         img_dict[img_file]['status_desc'] = status_desc
         img_dict[img_file]['hit'] = hit 
         if int(hit) == 1:
            od = od + 1
          
   
   return(img_dict, od)

def make_main_page():
   days = get_days()
   print(days)

def make_archive_links():


   days = get_days()
   d = 0
   html = ""
   for day in days:
      html = html + "<h2>" + day + "</h2> "
      for cn in range(1,7):
         #if cn != 1:
         #   html = html + " - "
         rand_num = random.randint(1,10000)
         cam_key = 'cam' + str(cn)
         cams_id = json_conf['cameras'][cam_key]['cams_id']


         master_stack_file = proc_dir + day + "/images/"  + cams_id + "-night-stack.png?" + str(rand_num)
         #master_stack_img = "<img alt='cam" + str(cn) + "' onmouseover='bigImg(this)' onmouseout='normalImg(this)' width=320 height=240 src='" + master_stack_file + "'>"
         #master_stack_img = "<img alt='cam" + str(cn) + "' onmouseover='normalImg(this)' onmouseout='normalImg(this)' width=320 height=240 src='" + master_stack_file + "'>"
         master_stack_img = "<img alt='cam" + str(cn) + "' width=320 height=240 src='" + master_stack_file + "'>"
         html = html + "<a href=archive-side.py?cmd=browse_day&day=" + day + "&cam_num=" + str(cn) + ">" + master_stack_img + "</a>" + "\n"
      html = html + "<P>"
      d = d + 1
   return(html)

def get_detection_files_for_day(day):
   glob_dir = proc_dir + day + "/data/*motion.txt" 
   motion_files = sorted(glob.glob(glob_dir), reverse=True)

   glob_dir = proc_dir + day + "/data/*trim*confirm.txt" 
   confirm_files = glob.glob(glob_dir)

   glob_dir = proc_dir + day + "/data/*meteor.txt" 
   meteor_files = sorted(glob.glob(glob_dir), reverse=True)

   glob_dir = proc_dir + day + "/data/*objfail.txt" 
   objfail_files = glob.glob(glob_dir)

   glob_dir = proc_dir + day + "/data/*rejected.txt" 
   reject_files = glob.glob(glob_dir)

   return(motion_files, confirm_files, meteor_files, objfail_files, reject_files)


def get_files_for_day_cam(day, cams_id):
      
   glob_dir = proc_dir + day + "/*" + str(cams_id) + ".mp4"
   files = glob.glob(glob_dir)
   return(sorted(files))

def get_rejects():
   glob_dir = proc_dir + "rejects" + "/*-stacked.png"
   files = glob.glob(glob_dir)
   return(files)

def mark_tag(word, tags):
   if word in tags:
      return("active")
   else:
      return("inactive")

def browse_rejects():
   debug = form.getvalue('debug')
   files = sorted(get_rejects(), reverse=True)
   for file in files:
      print("<img src=" + file + ">")

def browse_detections(day, cam):
   (motion_files, confirm_files, meteor_files, objfail_files, reject_files) = get_detection_files_for_day(day)
   type= form.getvalue('type')
   base_file_info = {}
   for file in meteor_files:
      el = file.split("-trim")
      base = el[0]
      base_file = base + ".mp4" 
      base_file_info[base_file] = "Meteor" 

   print ("<PRE><a href=archive-side.py?cmd=browse_detect&day=" + str(day) + "&type=motion>BRIGHT PIXEL DETECTIONS:" + str(len(motion_files)) + "</a>")
   print ("<PRE><a href=archive-side.py?cmd=browse_detect&day=" + str(day) + "&type=confirm>MOTION DETECTIONS:" + str(len(confirm_files)) + "</a>")
   print ("<PRE><a href=archive-side.py?cmd=browse_detect&day=" + str(day) + "&type=meteor>METEOR DETECTIONS:" + str(len(meteor_files)) + "</a>")
   print ("<PRE><a href=archive-side.py?cmd=browse_detect&day=" + str(day) + "&type=objfail>NON METEOR DETECTIONS:" + str(len(objfail_files)) + "</a>")
   print ("<PRE><a href=archive-side.py?cmd=browse_detect&day=" + str(day) + "&type=reject>NON MOTION REJECTED DETECTIONS :" + str(len(reject_files)) + "</a>")
   #print ("<PRE><a href=archive-side.py?cmd=browse_detect&day=" + str(day) + "&type=fps_fail>TRIM FPS FAILS:" + str(len(fps_fail_files)) + "</a>")
   #print ("<PRE>CONFIRM FILES:", len(confirm_files))
   #print ("<PRE>METEOR FILES:", len(meteor_files))
   #print ("<PRE>OBJ FAIL FILES:", len(objfail_files))
   #print ("<PRE>REJECT FILES:", len(reject_files))

   if type == 'meteor': 
      print ("<h1>Meteor Detections</h1>")
      for file in meteor_files:
         el = file.split("-trim")
         base = el[0]
         base = base.replace("data", "images") 
         img = base + "-stacked.png" 
         video_file = base + ".mp4"
         video_file = video_file.replace("images/", "")
         trim_file = file.replace("-meteor.txt", ".mp4") 
         trim_file = trim_file.replace("data/", "") 
         meteor_video_file = trim_file.replace(".mp4", "-meteor.mp4") 
         print("<img src=" + img + ">" )
         moving_objects = get_code(file)
         #print("<BR><a href=" + file + ">Meteor File</a><br>")
         print("<BR><a href=" + trim_file + ">Trim</a> - ")
         print("<BR><a href=" + meteor_video_file + ">Meteor</a><br>")
         print("<BR><a href=archive-side.py?cmd=examine&video_file=" + video_file + ">Examine</a><br>")
         data, status = object_report(moving_objects, "meteor")  

   if type == "confirm":
      print ("<h1>Motion Confirmations</h1>")
      for file in confirm_files:
         objfile = file.replace("-confirm.txt", "-objfail.txt")
         file_exists = Path(objfile)
         if file_exists.is_file():
            moving_objects = get_code(objfile)
         else:
            moving_objects = []

         meteor_file = file.replace("-confirm.txt", "-meteor.txt")
         file_exists = Path(meteor_file)
         if file_exists.is_file():
            meteor = 1
            moving_objects = get_code(meteor_file)
         else:
            meteor = 0

         el = file.split("-trim")
         base = el[0]
         base = base.replace("data", "images") 
         img = base + "-stacked.png" 
         if meteor == 1:
            desc = "<B>METEOR</B>"
         else:
            desc = "<B>non-meteor</B>"
         if len(moving_objects) == 0:
            desc = desc + "; No objects detected"

         print("<img src=" + img + "><br>" + desc + "<BR>")
         trim_file = file.replace("-confirm.txt", ".mp4") 
         trim_file = trim_file.replace("data/", "") 
         print("<BR><a target=_blank href=" + trim_file + ">Video Clip</a><br>")
         if meteor == 0:
            object_report(moving_objects, "objfail")
         else:
            object_report(moving_objects, "meteor")
         
 
   # BRIGHT PIXEL DETECTS
   if type == "motion":
      print ("<h1>All Bright Pixel Detections</h1>")
      for file in motion_files:
         el = file.split("-motion")
         base = el[0]
         base_file = base + ".mp4"
         base = base.replace("data", "images") 
         img = base + "-stacked.png" 
         if base_file in base_file_info:
            file_info = base_file_info[base_file]
         else:
            file_info = ""
         print("<img src=" + img + "><BR>" + file_info)

   if type == "objfail":
      print ("<h1>Object Detection Failures (no meteors detected)</h1>")
      for file in objfail_files: 
         print(file)
         el = file.split("-trim")
         base = el[0]
         base_file = base + ".mp4"
         base = base.replace("data", "images") 
         img = base + "-stacked.png" 
         if base_file in base_file_info:
            file_info = base_file_info[base_file]
         else:
            file_info = ""
         print("<img src=" + img + "><BR>" + file_info)

   

def browse_day(day, cam):
   form = cgi.FieldStorage()
   debug = form.getvalue('debug')
   detect_only = form.getvalue('detect_only')


   cam_key = 'cam' + str(cam)
   cam_ip = json_conf['cameras'][cam_key]['ip']
   sd_url = json_conf['cameras'][cam_key]['sd_url']
   hd_url = json_conf['cameras'][cam_key]['hd_url']
   cams_id = json_conf['cameras'][cam_key]['cams_id']


   if detect_only is None:
      detect_only = 0
   else:
      detect_only = int(detect_only)
   print("<script src=tag_pic.js></script>")
   print ("<h2><a href=archive-side.py>Home</a> -> Browse Day " + str(day) + " Cam " + str(cam) + "</h2>")
   report_file = proc_dir + str(day) + "/" + str(day) + "-cam" + str(cam) + "-report.txt"
   img_dict, od = load_scan_file(day, cam)
   files = get_files_for_day_cam(day, cams_id)
   file_dict = defaultdict()
   print(str(len(files)) + " total files <BR>")
   #print(str(od) + " objects auto detected<BR>")
   print ("<form action=archive-side.py>")
   print ("<input type=submit value='Show Detections Only'>")
   print ("<input type=hidden name=day value='" + day + "'>")
   print ("<input type=hidden name=cam_num value='" + str(cam) + "'>")
   print ("<input type=hidden name=detect_only value='1'>")
   print ("<input type=hidden name=cmd value='browse_day'>")
   print ("</form>")
   for file in files:
      file_dict[file] = {}
      file_dict[file]['tags'] = ""

   tag_file = proc_dir + str(day) + "/" + "tags-cam" + str(cam) + ".txt"
   file_exists = Path(tag_file)
   if (file_exists.is_file()):
      print ("OPEN TAG FILE")
      file_dict = parse_tags(tag_file, file_dict) 
   count = 0
   for file in files:
      jpg = file.replace(".mp4", "-stacked.png") 

      el = jpg.split("/")
      fn = el[-1]
    
      base = jpg.replace(fn, "")
      jpg = base + "/images/" + fn


      blend = file.replace(".mp4", "-blend.jpg") 
      #diff = file.replace(".mp4", "-diff.jpg") 
      diff = file.replace(".mp4", "-objects.jpg") 
      confirm_file = file.replace(".mp4", "-confirm.txt") 
      fe = Path(confirm_file)
      if (fe.is_file()):
         hit = 1
      else:
         hit = 0
      status_desc = "" 
      if (detect_only == 1 and hit == 1) or (detect_only == 0):
         tags = file_dict[file]['tags']
         print ("<div class='divTable'>")
         print ("<div class='divTableBody'>")
         print ("<div class='divTableRow'>")
         if int(hit) == 1:
            print ("<div class='divTableCellDetect'>")
         else:
            print ("<div class='divTableCell'>")
         #print ("<a href=" + file + " onmouseover=\"document.img" + str(count) + ".src='" + diff + "'\" onmouseout=\"document.img" + str(count) + ".src='" + jpg + "'\"><img name='img" + str(count) + "' src=" + jpg + "></a></div>")
         print ("<a href=archive-side.py?cmd=examine&video_file=" + file + " ><img name='img" + str(count) + "' src=" + jpg + "></a></div>")
         print ("<div class='divTableCell'>") 

         # start the button area here
         print ("<div class='divTable'>")
         print ("<div class='divTableBody'>")
         print ("<div class='divTableRow'>")
         print ("<div class='divTableCell'>")

         cls = mark_tag("meteor", tags)
         print ("<input type=button name=tag value=\"   meteor  \" onclick=\"javascript:tag_pic('" + file + "', 'meteor', event);\" class='" + cls + "'>")
         print ("</div></div>")
         print ("<div class='divTableRow'>")
         print ("<div class='divTableCell'>")

         cls = mark_tag("plane", tags)
         print ("<input type=button name=tag value=\"    plane   \" onclick=\"javascript:tag_pic('" + file + "', 'plane', event);\" class='" + cls + "'>")
         print ("</div></div>")
         print ("<div class='divTableRow'>")
         print ("<div class='divTableCell'>")

         cls = mark_tag("sat", tags)
         print ("<input type=button name=tag value=\"    sat      \" onclick=\"javascript:tag_pic('" + file + "', 'sat', event);\" class='" + cls + "'>")
         print ("</div></div>")
         print ("<div class='divTableRow'>")
         print ("<div class='divTableCell'>")

         cls = mark_tag("cloud", tags)
         print ("<input type=button name=tag value=\"   cloud   \" onclick=\"javascript:tag_pic('" + file + "', 'cloud', event);\" class='" + cls + "'>")
         print ("</div></div>")
         print ("<div class='divTableRow'>")
         print ("<div class='divTableCell'>")

         cls = mark_tag("notsure", tags)
         print ("<input type=button name=tag value=\"  notsure \" onclick=\"javascript:tag_pic('" + file + "', 'notsure', event);\" class='" + cls + "'>")
         print ("</div></div>")
         print ("<div class='divTableRow'>")
         print ("<div class='divTableCell'>")


         cls = mark_tag("interesting", tags)
         print ("<input type=button name=tag value=\"interesting\" onclick=\"javascript:tag_pic('" + file + "', 'interesting', event);\" class='" + cls + "'>")
         print ("</div></div>")
         print ("<div class='divTableRow'>")
         print ("<div class='divTableCell'>")



         cls = mark_tag("other", tags)
         print ("<input type=button name=tag value=\"   other    \" onclick=\"javascript:tag_pic('" + file + "', 'other', event);\" class='" + cls + "'>")
         print ("</div></div>")
         print ("</div>")
         print ("</div>")

         print (str(hit) + "-" + status_desc)
         print ("</div></div></div></div><P>")
         count = count + 1

         #print("</td><td>")
         if debug is not None:
            print("<img src=" + blend + "></a><BR></td><td><img src=" + diff + "></a><BR> </td></tr></table> ")


def main():
   rand_num = random.randint(1,10000)
   print ("<link rel='stylesheet' href='div_table.css?" + str(rand_num) + "'>")
   print("<script src='big-little-image.js'></script>")

   form = cgi.FieldStorage()
   cam_num = form.getvalue('cam_num')
   day = form.getvalue('day')

   cmd = form.getvalue('cmd')
   # for testn
   #cmd = "browse_day"
   #day = "2018-05-10"
   #cam_num = 5


   archive_links = make_archive_links()

   if cmd is None:
      print ("<h2>View Archive</h2>")
      print("Select a day and camera to browse.<P>")
      make_main_page()
      print(archive_links)
   if cmd == "browse_detect":
      browse_detections(day, cam_num)  
   if cmd == "browse_day":
      browse_day(day, cam_num)  
   if cmd == "browse_rejects":
      browse_rejects()  
   if cmd == "examine":
      video_file = form.getvalue('video_file')
      examine_video_clip(video_file)  

def parse_tags(tag_file, file_dict):
   fp = open(tag_file, "r");
   for line in fp:
      line = line.replace("\n", "")
      (cmd, tag, file) = line.split(",")
      if cmd == 'add':
         file_dict[file]['tags'] = file_dict[file]['tags'] + "," + tag
      else:
         file_dict[file]['tags'] = file_dict[file]['tags'].replace(tag, "")
   return(file_dict)   

form = cgi.FieldStorage()
main()


