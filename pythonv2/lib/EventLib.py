from random import randint
from sympy import Point3D, Line3D, Segment3D, Plane
import time
import math
import cv2
import cgi
import time
import glob
import os
import json
import cgitb
import re
import datetime
import time
from lib.FileIO import cfe, load_json_file

def DetectsMain(form ):
   json_conf = load_json_file("/home/ams/amscams/conf/as6.json")
   station = json_conf['site']['ams_id']   
   print("<h1>Multi-station detections for ", station, "</h1>")
   detect_file = "/mnt/ams2/meteor_archive/" + station + "/DETECTS/ms_detects.json"
   detect_data = load_json_file(detect_file)
   for key in sorted(detect_data.keys()):
      print("<h2>", key, "</h2>")
      for file in detect_data[key]:
         print(file, set(detect_data[key][file]['stations']), "<BR>")

def DetectsDetail(form):
   print("..", station)

def EventsMain(form):
   print("<h1>Event Main</h1>")
   events = []
   files = glob.glob("/mnt/ams2/events/*")
   for file in files: 
      if cfe(file, 1) == 1:
         ev = file.split("/")[-1]
         events.append(ev)
   for event in events:
      print("<a href=webUI.py?cmd=event_detail&event=" + event + ">" + event + "</a><BR>")

def ymd(file):
   y = file[0:4]
   m = file[4:6]
   d = file[6:8]
   return(y,m,d)

def EventDetail(form):
   sync_urls = load_json_file("/home/ams/amscams/conf/sync_urls.json")
   event = form.getvalue("event")
   out = ""
   out +=  "<h1>Event Detail: " + event + "</h1>\n"
   event_dir = "/mnt/ams2/events/" + event + "/"
   mc_event_dir = "/mnt/ams2/events/" + event + "/Monte\ Carlo/"
   cmd = "mv " + mc_event_dir + "* " + event_dir
   
   #print(cmd)

   print("<BASE HREF=" + event_dir + ">")
   json_file = event_dir + event + ".json"
   obs_json = load_json_file(json_file)

   rpt_jsons = glob.glob(event_dir + "*_report.json")
   for rpt in rpt_jsons:
       if "mc_" in rpt:
          rpt_data = load_json_file(rpt)
       else:
          mc_data = load_json_file(rpt)

   #solutions['ip']['embed'] = "http://orbit.allskycams.com/index_emb.php?name={:s}&&epoch={:s}&a={:s}&M={:s}&e={:s}&I={:s}&Peri={:s}&Node={:s}&P={:s}&q={:s}&T={:s}".format( str(fn), str(qs['epoch']), str(qs['a']), str(qs['M']), str(qs['e']), str(qs['I']), str(qs['Peri']), str(qs['Node']), str(qs['P']), str(qs['q']), str(qs['T']))
   #solutions['mc']['embed'] = "http://orbit.allskycams.com/index_emb.php?name={:s}&&epoch={:s}&a={:s}&M={:s}&e={:s}&I={:s}&Peri={:s}&Node={:s}&P={:s}&q={:s}&T={:s}".format( str(fn), str(qs['epoch']), str(qs['a']), str(qs['M']), str(qs['e']), str(qs['I']), str(qs['Peri']), str(qs['Node']), str(qs['P']), str(qs['q']), str(qs['T']))
   obs = []
   out += "<h2>Observations</h2>\n"
   for key in obs_json:
      hd_file = key.replace(".json", "-HD.mp4")
      wasabi_file = hd_file.replace("ams2/meteor_archive", "wasabi")
      if "wasabi" in hd_file :
         ma_hd_file = hd_file.replace("wasabi/", "ams2/meteor_archive/")
         if cfe(ma_hd_file) == 0:
            ma = ma_hd_file.split("/")[-1]
            md = ma_hd_file.replace(ma, "")
            os.system("cp " + hd_file + " " + md) 
            hd_file = ma_hd_file
      if "mnt" in hd_file and cfe(hd_file) == 0:
         wasbi_file = hd_file.replace("ams2/meteor_archive", "wasabi")
         if cfe(wasabi_file) == 1:
            ma = ma_hd_file.split("/")[-1]
            md = ma_hd_file.replace(ma, "")
            os.system("cp " + wasabi_file + " " + md) 

      fn = hd_file.split("/")[-1]
      ev_hd = fn
      if "/mnt/" in hd_file:
         if cfe(event_dir +  fn) == 0:
            os.system("cp " + hd_file + " " + event_dir)
      if "mnt" in key:
         if "wasabi" in key:
            station  = key.split("/")[3]
         else:
            station  = key.split("/")[4]
         url= sync_urls['sync_urls'][station]['sync_url']
         year, mon, day = ymd(event)
         dkey = key.replace("wasabi", "ams2/meteor_archive")
         url += "/pycgi/webUI.py?cmd=reduce2&video_file=" + dkey 

         img = ev_hd.replace(".mp4", ".png")
         img_tn = ev_hd.replace(".mp4", "-tn.png")
         if cfe(img_tn) == 0:
            #print("RESIZE:", img)
            image_data = cv2.imread(event_dir + img)
            if image_data is None:
               print(img + " is none")
            else:
                
               tn_img = cv2.resize(image_data, (240,135))
               cv2.imwrite(event_dir + img_tn, tn_img)
         #240x135
         #print(img_tn)

         #out_vel += "<div style='float: left'><figure><img width=600 height=480 src=" + img + "><figcaption>" + caption +"</figcaption></figure></div>\n" 
         out += "<div style='float: left'><figure><a href=" + ev_hd + "><img src=" + img_tn + "><figcaption>" + station + "</a></figcaption></figure></div>"
   out += "<div style='clear:both'>"
   img_files = glob.glob("/mnt/ams2/events/" + event + "/*.png") 
   out_orb = ""
   out_res = ""
   out_mc = ""
   out_lags  = ""
   out_lengths = ""
   out_track = ""
   out_vel = ""
   for img in img_files:
      img = img.replace("/mnt/ams2/events/" + event + "/", "")
      if "mc_" in img or "monte" in img:
         caption = "<p style='text-align: center'><b>Monte Carlo</b></p>"
      else:
         caption = "<p style='text-align: center'><b>Intersecting Planes</b></p>"
      if "orbit" in img:
         out_orb += "<div style='float: left'><figure><img width=600 height=480 src=" + img + "><figcaption>" + caption +"</figcaption></figure></div>\n" 
      if "residuals" in img:
         out_res += "<div style='float: left'><figure><img width=600 height=480 src=" + img + "><figcaption>" + caption +"</figcaption></figure></div>\n" 
      if "monte_carlo" in img:
         out_mc += "<div style='float: left'><figure><img width=600 height=480 src=" + img + "><figcaption>" + caption +"</figcaption></figure></div>\n" 
      if "lags" in img:
         out_lags  += "<div style='float: left'><figure><img width=600 height=480 src=" + img + "><figcaption>" + caption +"</figcaption></figure></div>\n" 
      if "lengths" in img:
         out_lengths += "<div style='float: left'><figure><img width=600 height=480 src=" + img + "><figcaption>" + caption +"</figcaption></figure></div>\n" 
      if "ground_track" in img:
         out_track += "<div style='float: left'><figure><img width=600 height=480 src=" + img + "><figcaption>" + caption +"</figcaption></figure></div>\n" 
      if "velocities" in img:
         out_vel += "<div style='float: left'><figure><img width=600 height=480 src=" + img + "><figcaption>" + caption +"</figcaption></figure></div>\n" 
   out += "<h2>Residuals</h2>"
   out += out_res 
   out += "<div style='clear:both'><h2>Lag</h2>"
   out += out_lags  
   out += "<div style='clear:both'><h2>Length</h2>"
   out += out_lengths 
   out += "<div style='clear:both'><h2>Monte Carlo</h2>"
   out += out_mc 
   out += "<div style='clear:both'><h2>Velocity</h2>"
   out += out_vel 
   out += "<div style='clear:both'><h2>Track</h2>"
   out += out_track 
   out += "<div style='clear:both'><h2>Orbit</h2>"
   out += out_orb 

   reports = glob.glob(event_dir + "*_report.txt")
   for i in range(0, len(reports)): 
      if "mc_" in reports[i]:
         out += "<div style='clear:both'><h2>Monte Carlo Report</h2>"
      else:
         out += "<div style='clear:both'><h2>Intersecting Planes Report</h2>"
      out += "<iframe width=80% height=800 src=" + reports[i]+ "></iframe>"


   print(out)
   fp = open(event_dir + "report.html", "w")
   fp.write(out)
   fp.close()

