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
   print("<h1>Event Detail: " + event + "</h1>")
   event_dir = "/mnt/ams2/events/" + event + "/"
   json_file = event_dir + event + ".json"
   print(json_file + "<BR>")
   obs_json = load_json_file(json_file)
   obs = []
   for key in obs_json:
      if "wasabi" in key:
         station  = key.split("/")[3]
         url= sync_urls['sync_urls'][station]['sync_url']
         year, mon, day = ymd(event)
         dkey = key.replace("wasabi", "ams2/meteor_archive")
         url += "/pycgi/webUI.py?cmd=reduce2&video_file=" + dkey 
         print("<a href=" + url + ">" + station + "</a><br>")
   img_files = glob.glob("/mnt/ams2/events/" + event + "/*.png") 
   for img in img_files:
      print("<div style='float: left'><img width=600 height=480 src=" + img + "></div>" )
   reports = glob.glob(event_dir + "*_report.txt")
   #print(event_dir + "*_report.txt")
   if len(reports) > 0:
      print("<iframe width=80% height=800 src=" + reports[0]+ "></iframe>")

