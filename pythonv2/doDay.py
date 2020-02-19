#!/usr/bin/python3

"""
This script is the work manager for each day. 
  * Run this script through the day to keep data up to date and in sync.
  * Run this script after a day has finished to close out all work relating to that day. 
  * Script will perform the following functions.
     - Make sure all processed video files, stack images and data file are in the right place
     - Create archive time lapse videos of 24 hours of stack images for the day
     - Create meteor index for the day
     - Make sure all meteor thumbs exist
     - Make sure all meteors have been moved to the archive
     - Delete any false meteors tagged by admins or others
     - Sync all relevant files for the day to wasabi (archive meteors, preview images, NOAA files, event date
     - Run detections for the day (if master node)
     - Run all event solutions for the day
     - Stack daytime images
     - Produce Ops report for the day
     - Purge Disk Space



"""

import os
import glob
import sys
from datetime import datetime, timedelta

from lib.FileIO import load_json_file, save_json_file, cfe

json_conf = load_json_file("../conf/as6.json")

def batch(num_days):

   today = datetime.today()
   for i in range (0,int(num_days)):
      past_day = datetime.now() - timedelta(hours=24*i)
      print(past_day)
   

def make_station_report(day, proc_info = ""):
   print("PROC INFO:", proc_info)
   # MAKE STATION REPORT FOR CURRENT DAY
   station = json_conf['site']['ams_id']
   detect_html = html_get_detects(day, station)
   year,mon,dom = day.split("_")
   NOAA_DIR =  "/mnt/archive.allsky.tv/" + station + "/NOAA/ARCHIVE/" + year + "/" + mon + "_" + dom + "/"
   if cfe(NOAA_DIR, 1) == 0:
      os.makedirs(NOAA_DIR)
   html_index = NOAA_DIR + "index.html"
   noaa_files = glob.glob(NOAA_DIR + "*.jpg")
   data = {}
   data['files'] = noaa_files
   header_html, footer_html = html_header_footer()


   html = header_html
   show_date = day.replace("_", "/")
   html += "<h1>" + station + " Daily Report for " + show_date + "</h1>\n"
   html += "<h2><a href=\"#\" onclick=\"showHideDiv('live_view')\">Live View</a></h2>\n <div id='live_view'>"
   if len(data['files']) > 0:
      data['files'] = sorted(data['files'], reverse=True)
      fn = data['files'][0].replace("/mnt/archive.allsky.tv", "")
      html += "<img src=" + fn + "><BR>\n"
      html += "</div>"

   html += "<h2><a href=\"#\" onclick=\"showHideDiv('live_snaps')\">Weather Snap Shots</a></h2>\n <div id='live_snaps' style='display: none'>"
   for file in sorted(data['files'],reverse=True):
      fn = file.replace("/mnt/archive.allsky.tv", "")
      html += "<img src=" + fn + "><BR>\n"
   html += "</div>"

   html += "<h2><a href=\"#\" onclick=\"showHideDiv('meteors')\">Meteors</a></h2>\n <div id='meteors'>"
   html += detect_html
   html += "</div>"

   html += "</div>"

   html += "<h2><a href=\"#\" onclick=\"showHideDiv('proc_info')\">Processing Info</a></h2>\n <div id='proc_info'>"
   html += "<PRE>" + proc_info + "</PRE>"
   html += "</div>"

   fpo = open(html_index, "w")
   fpo.write(html)
   fpo.close()
   print(html_index)


def html_get_detects(day,tsid):
   year = day[0:4]
   mi = "/mnt/ams2/meteor_archive/" + json_conf['site']['ams_id'] + "/DETECTS/MI/" + year + "/" +  day + "-meteor_index.json"
   print(mi)
   mid = load_json_file(mi)
   meteor_detects = []
   prev_dir = "/mnt/archive.allsky.tv/" + tsid + "/DETECTS/PREVIEW/" + year + "/" + day + "/" 
   prev_file = "/mnt/archive.allsky.tv/" + tsid + "/DETECTS/PREVIEW/" + year + "/" + day + "/" + "index.html"
   html = ""
   
   was_prev_dir = "/mnt/archive.allsky.tv/" + tsid + "/DETECTS/PREVIEW/" + year + "/" + day + "/" 
   was_vh_dir = "/" + tsid + "/DETECTS/PREVIEW/" + year + "/" + day + "/" 

   if day in mid:
      for key in mid[day]:
         mfile = key.split("/")[-1]
         prev_crop = mfile.replace(".json", "-prev-crop.jpg")
         prev_full = mfile.replace(".json", "-prev-full.jpg")
         html += "<img src=" + was_vh_dir + prev_crop + ">"
   else:
      html += "No meteors detected."

   return(html)


def html_header_footer(info=None):
   js = javascript()
   html_header = """
     <head>
        <meta http-equiv="Cache-control" content="public, max-age=500, must-revalidate">
   """
   html_header += js + """
     </head>
   """

   html_footer = """

   """
   return(html_header, html_footer)

def javascript():
   js = """
      <script>
      function showHideDiv(myDIV) {
         var x = document.getElementById(myDIV);
         if (x.style.display === "none") {
            x.style.display = "block";
         } else {
            x.style.display = "none";
         }
      }

      </script>
   """
   return(js)


def get_processing_status(day):
   proc_dir = "/mnt/ams2/SD/proc2/" + day + "/*"
   proc_img_tn_dir = "/mnt/ams2/SD/proc2/" + day + "/images/*tn.png"
   proc_vids = glob.glob(proc_dir)
   proc_tn_imgs = glob.glob(proc_img_tn_dir)

   #proc_img_dir = "/mnt/ams2/SD/proc2/" + day + "/images/*.png"
   #proc_imgs = glob.glob(proc_img_dir)


   day_vids = glob.glob("/mnt/ams2/SD/proc2/daytime/" + day + "*.mp4")
   cams_queue = glob.glob("/mnt/ams2/CAMS/queue/" + day + "*.mp4")
   in_queue = glob.glob("/mnt/ams2/SD/" + day + "*.mp4")
   return(proc_vids, proc_tn_imgs, day_vids,cams_queue,in_queue)

def get_meteor_status(day):
   detect_files = []
   arc_file = []
   year, mon, dom = day.split("_")
   detect_dir = "/mnt/ams2/meteors/" + day + "/"
   arc_dir = "/mnt/ams2/meteor_archive/" + json_conf['site']['ams_id'] + "/METEOR/" + year + "/" + mon + "/" + dom + "/"

   
   # get detect and arc files
   dfiles = glob.glob(detect_dir + "*trim*.json")
   arc_files = glob.glob(detect_dir + "*trim*.json")

   # filter out non-meteor or dupe meteor json files
   for df in dfiles:
      if "reduced" not in df and "manual" not in df and "stars" not in df:
         detect_files.append(df)

   return(detect_files, arc_files)
   

def do_all(day):
   proc_vids, proc_tn_imgs, day_vids,cams_queue,in_queue = get_processing_status(day)
   detect_files, arc_files = get_meteor_status(day)

   # figure out how much of the day has completed processing
   rpt = """
   Processing report for day: """ + day + """
   Processed Videos:""" + str(len(proc_vids)) + """
   Processed Thumbs:""" +  str(len(proc_tn_imgs)) + """
   Un-Processed Daytime Videos:""" +  str(len(day_vids)) + """
   Un-Processed CAMS Queue:""" + str(len(cams_queue)) + """
   Un-Processed IN Queue:""" + str(len(in_queue)) + """
   Possible Meteor Detections:""" + str(len(detect_files)) + """
   Archived Meteors :""" + str(len(arc_files)) + """
   Unique Meteors: ???"""  + """
   Multi-station Events: ???"""  + """
   Solved Events: ???"""  + """
   Events That Failed to Solve: ???""" 

   print ("RPT:", rpt)
   if len(cams_queue) < 10 and len(in_queue) < 10:
      proc_status = "up-to-date"

 
   # make the meteor detection index for today
   os.system("./autoCal.py meteor_index " + day)

   # make the detection preview images for the day
   os.system("./flex-detect.py bmpi " + day)

   # make the detection preview images for the day
   os.system("./wasabi.py sa " + day)

   make_station_report(day, rpt)


cmd = sys.argv[1]

if cmd == "all":
   do_all(sys.argv[2])
if cmd == "msr":
   make_station_report(sys.argv[2])
if cmd == "batch":
   batch(sys.argv[2])
