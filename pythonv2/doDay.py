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
import subprocess

from lib.FileIO import load_json_file, save_json_file, cfe
from lib.UtilLib import check_running

json_conf = load_json_file("../conf/as6.json")

def load_events(day):
   year = day[0:4]
   event_index = "/mnt/archive.allsky.tv/" + "/EVENTS/" + year + "/" + day + "/" + day +"-events.json"
   event_files_index = "/mnt/archive.allsky.tv/" + "/EVENTS/" + year + "/" + day + "/" + day + "-event-files.json"
   event_files = {}
   if cfe(event_index) == 1:
      events = load_json_file(event_index)
      for event in events:
         if events[event]['count'] >= 2:
            for file in events[event]['files']:
               event_files[file] = event
      #save_json_file(event_files_index,event_files ) 
      #print("Saved:", event_files_index)
   else:
      events = {}
      event_files = {}
   return(events,event_files)

def run_df():
   df_data = []
   mounts = {}
   if True:
      cmd = "df -h "
      output = subprocess.check_output(cmd, shell=True).decode("utf-8")
      #Filesystem                 Size  Used Avail Use% Mounted on

      for line in output.split("\n"):
         file_system = line[0:20]
         size = line[20:26]
         used = line[27:38]
         avail = line[38:44]
         used_perc = line[44:49]
         mount = line[49:].replace(" ", "")
         if mount == "/" or mount == "/mnt/ams2" or mount == "/mnt/archive.allsky.tv":
            df_data.append((file_system, size, used, avail, used_perc, mount))
            used_perc = used_perc.replace(" ", "")
            mounts[mount] = int(used_perc.replace("%", ""))
   else:
      print("Failed du")
   return(df_data, mounts)

def check_disk():
   df_data, mounts = run_df()

   if "/mnt/archive.allsky.tv" not in mounts:
      print("Wasabi is not mounted! Mounting now.")
      os.system("./wasabi.py mnt")
   if mounts["/mnt/ams2"] > 80:
      print("Data volume /mnt/ams2 is greater than 80%!", mounts["/mnt/ams2"]) 
   if mounts["/"] > 80:
      print("Root volume / is greater than 80%!", mounts["/mnt/ams2"]) 

   # first get the HD files and start deleting some of then (remove the last 12 hours) 
   # then check disk again if it is still over 80% delete some more. 
   # continue to do this until the disk is less than 80% or there are only a max of 2 days of HD files left
   if mounts["/mnt/ams2"] > 80:
      print("Data volume /mnt/ams2 is greater than 80%!", mounts["/mnt/ams2"]) 
      hd_files = sorted(glob.glob("/mnt/ams2/HD/*.mp4"))
      print(len(hd_files), " HD FILES")
      del_count = int(len(hd_files) / 10)
      for file in hd_files[0:del_count]:
         if "meteor" not in file:
            print("Delete this file!", file)
            os.system("rm " + file)

   # check SD dir  
   # if the disk usage is over 80% 
   # get folders in /proc2, delete the folders one at a time and re-check disk until disk <80% or max of 30 folders exist

   # remove trash and other tmp dirs

def batch(num_days):

   # first make sure the batch is not already running.
   running = check_running("doDay.py")
   print("Running:", running)
   if running > 2:
      print("Already running.")
      exit()

   today = datetime.today()
   for i in range (0,int(num_days)):
      past_day = datetime.now() - timedelta(hours=24*i)
      past_day = past_day.strftime("%Y_%m_%d")
      print(past_day)
      do_all(past_day)

def get_template(file):
   fp = open(file, "r")
   text = ""
   for line in fp:
      text += line
   return(text)


def add_section(link_from_tab,tab_content):
   TAB= ''
   TAB_CONTENT = ''
   link_from_tabst = link_from_tab.replace(" ", "")
   if(tab_content is not None):
      TAB = '<li class="nav-item"><a class="nav-link" id="'+link_from_tabst+'-tab" data-toggle="tab" href="#'+link_from_tabst+'" role="tab" aria-controls="'+link_from_tabst+'" aria-selected="true">'+link_from_tab+'</a></li>'
      TAB_CONTENT = '<div class="tab-pane fade show" id="'+link_from_tabst+'" role="tabpanel" aria-labelledby="'+link_from_tabst+'-tab">'+tab_content+'</div>'
   
   return TAB, TAB_CONTENT 


def make_station_report(day, proc_info = ""):
   template = get_template("templates/allsky.tv.base.html") 

   print("PROC INFO:", proc_info)
   # MAKE STATION REPORT FOR CURRENT DAY
   station = json_conf['site']['ams_id']
   year,mon,dom = day.split("_")
   show_day = mon + "/" + dom + "/"+ year
   STATION_RPT_DIR =  "/mnt/archive.allsky.tv/" + station + "/REPORTS/" + year + "/" + mon + "_" + dom + "/"
   NOAA_DIR =  "/mnt/archive.allsky.tv/" + station + "/NOAA/ARCHIVE/" + year + "/" + mon + "_" + dom + "/"
   
   template = template.replace("{STATION_ID}", station)
   template = template.replace("{DAY}", show_day)


   if cfe(STATION_RPT_DIR, 1) == 0:
      os.makedirs(STATION_RPT_DIR)
   
   html_index = STATION_RPT_DIR + "index.html"
   noaa_files = glob.glob(NOAA_DIR + "*.jpg")
   data = {}
   data['files'] = noaa_files

   events,event_files = load_events(day)
   single_html, multi_html,info= html_get_detects(day, station, event_files,events)
   detect_count = info['mc']
 
   show_date = day.replace("_", "/")
 
   TAB= ''
   TAB_CONTENT = ''


   # LIVE VIEW
   live_view_html = ""
   if len(data['files']) > 0:
      data['files'] = sorted(data['files'], reverse=True)
      fn = data['files'][0].replace("/mnt/archive.allsky.tv", "")
      live_view_html += "<img src='" + fn + "' class='img-fluid'/>"
 
   tabView, tabContentView = add_section('Live View',live_view_html)
   
   TAB += tabView
   TAB_CONTENT += tabContentView

   #template = template.replace("{LIVE_VIEW}", live_view_html)

   we_html = ""
   if len(data['files']) > 0:
      for file in sorted(data['files'],reverse=True):
         fn = file.replace("/mnt/archive.allsky.tv", "")
         we_html += "<img src='" + fn + "' class='img-fluid'>"
      weather_section = html_section("weather", "Weather Snap Shots", we_html)

   tabSec, tabContentSec = add_section('Weather Snap Shots',weather_section)
   TAB += tabView
   TAB_CONTENT += tabContentView

   
   
   template = template.replace("{TABS}", TAB)
   template = template.replace("{TABS_CONTENT}", TAB_CONTENT)

   template = template.replace("{WEATHER_SNAPSHOTS}", weather_section)

   proc_section = html_section("proc_info", "Processing Info", proc_info)
   template = template.replace("{PROC_REPORT}", proc_section)

   title = "Multi Station Meteors (" + str(info['ms_count']) + ")"
   meteor_section = html_section("multi_meteors", title , "<div class='d-flex align-content-start flex-wrap'>" + multi_html + "</div>")
   template = template.replace("{MULTI_METEORS}", meteor_section)

   title = "Single Station Meteors (" + str(info['ss_count']) + ")"
   meteor_section = html_section("single_meteors", title , "<div class='d-flex align-content-start flex-wrap'>" + single_html + "</div>")
   template = template.replace("{SINGLE_METEORS}", meteor_section)
 
   fpo = open(html_index, "w")
   fpo.write(template)
   fpo.close()
   print(html_index)
  
 

def html_section(ID, TITLE,CONTENT ):
   sec = """
      <div class="card box p-0">
         <div class="card-header" id="{ID}Heading">
            <h2 class="mb-0">
               <button class="btn btn-link p-0 d-block" type="button" data-toggle="collapse" data-target="#{ID}Content" aria-expanded="true"  aria-controls="{ID}Content">
                   {TITLE}
               </button>
            </h2>
         </div>
         <div id="{ID}Content" class="collapse" aria-labelledby="{ID}Heading" data-parent="#main_content">
            <div class="card-body">
                  {CONTENT}
            </div>
         </div>
      </div>

   """
   sec = sec.replace("{ID}", ID)
   sec = sec.replace("{TITLE}", TITLE)
   sec = sec.replace("{CONTENT}", CONTENT)
   return(sec)

def html_get_detects(day,tsid,event_files, events):
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
   mc = 0
   arc_count = 0
   pending_count = 0
   unique_met_count = 0
   ms_count = 0
   ss_count = 0
   solved_count = 0
   failed_count = 0
   not_run = 0
   single_html = ""
   multi_html = ""
   if day in mid:
      for key in mid[day]:
         if "archive_file" in mid[day][key]:
            arc = 1
            arc_file = mid[day][key]['archive_file']
            style = "arc"
            arc_count += 1
         else:
            arc = 0
            arc_file = "pending"
            style = "pending"
            pending_count += 1
         if key in event_files:
            event_id = event_files[key]
            
            event_info = events[event_id]

            print("KEY", key, event_files[key])
            style = "multi"
            # look for the event solution dir
            event_dir = "/mnt/archive.allsky.tv/EVENTS/" + year + "/" + day + "/" + event_id + "/"
            event_vdir = "/EVENTS/" + year + "/" + day + "/" + event_id + "/"
            event_file = event_dir + event_id + "-report.html"
            event_vfile = event_vdir + event_id + "-report.html"
         
            if len(events[event_id]['solutions']) > 0 :
               elink = "<a href=" + event_vfile + ">"
               solved_count += 1
               #else:
               #   print("NT F:", event_file)
               #   failed_count += 1
               #   elink = "<a>"
            else:
               print("Event not solved.", event_dir)
               elink = "<a>"
               not_run += 1
         else:
            event_id = None
            elink = "<a>"
         mfile = key.split("/")[-1]
         prev_crop = mfile.replace(".json", "-prev-crop.jpg")
         prev_full = mfile.replace(".json", "-prev-full.jpg")

         image_file = prev_crop
         if arc_file == "pending":
            css_class = "prevproc pending"
         else:
            css_class = "prevproc arc"
         #if event_id is not None:
         #   css_class = "prevproc multi"
         if event_id is None:
            event_id = "none"
    
         if event_id is None or event_id == "none":
            single_html += """
                             <div class="d-flex align-content-start flex-wrap">
                                 <div class="{:s}">
                                       {:s} 
                                        <img src="{:s}" class="img-fluid">
                                       </a>
                                        <span>{:s}</span>
                                   </div>
                             </div>
            """.format(css_class, elink, was_vh_dir + image_file, event_id)
            ss_count += 1
         else:
            multi_html += """
                             <div class="d-flex align-content-start flex-wrap">
                                 <div class="{:s}">
                                       {:s} 
                                        <img src="{:s}" class="img-fluid">
                                       </a>
                                        <span>{:s}</span>
                                   </div>
                             </div>
            """.format(css_class, elink, was_vh_dir + image_file, event_id)
            ms_count += 1

         mc += 1
   else:
      html += "No meteors detected."


   info = {}
   info['arc_count'] = arc_count
   info['pending_count'] = pending_count
   info['unique_met_count'] = unique_met_count
   info['ms_count'] = ms_count
   info['ss_count'] = ss_count
   info['solved_count'] = solved_count
   info['failed_count'] = failed_count
   info['not_run'] = not_run
   info['mc'] = mc 

   return(single_html, multi_html, info)


def html_header_footer(info=None): 
   html_header = ''
   html_footer = ''
   return(html_header, html_footer)

 


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
   arc_files = glob.glob(arc_dir + "*trim*.json")

   # filter out non-meteor or dupe meteor json files
   for df in dfiles:
      if "reduced" not in df and "manual" not in df and "stars" not in df:
         detect_files.append(df)

   return(detect_files, arc_files)
   

def do_all(day):
   os.system("git pull")
   proc_vids, proc_tn_imgs, day_vids,cams_queue,in_queue = get_processing_status(day)
   detect_files, arc_files = get_meteor_status(day)

   time_check = check_time(day)

   # figure out how much of the day has completed processing
   rpt = """ 
      <dl class="row">
         <dt class="col-3">Time Check</dt><dd class="col-9">{:s}</dd>
         <dt class="col-3">Processing report for day</dt><dd class="col-9">{:s}</dd>
         <dt class="col-3">Processing videos</dt><dd class="col-9">{:s}</dd>
         <dt class="col-3">Processed Thumbs</dt><dd class="col-9">{:s}</dd>
         <dt class="col-3">Un-Processed Daytime Videos</dt><dd class="col-9">{:s}</dd>
         <dt class="col-3">Un-Processed CAMS Queue</dt><dd class="col-9">{:s}</dd>
         <dt class="col-3">Un-Processed IN Queue</dt><dd class="col-9">{:s}</dd>
         <dt class="col-3">Possible Meteor Detections</dt><dd class="col-9">{:s}</dd>
         <dt class="col-3">Archived Meteors</dt><dd class="col-9">{:s}</dd>
         <dt class="col-3">Unique Meteors</dt><dd class="col-9">{:s}</dd>
         <dt class="col-3">Multi-station Events</dt><dd class="col-9">{:s}</dd>
         <dt class="col-3">Solved Events</dt><dd class="col-9">{:s}</dd>
         <dt class="col-3">Events That Failed to Solve</dt><dd class="col-9">{:s}</dd>
      </dl>
   """.format(str(time_check), str(day), str(len(proc_vids)), str(len(proc_tn_imgs)), str(len(day_vids)), str(len(cams_queue)), str(len(in_queue)), str(len(detect_files)), str(len(arc_files)), "UM", "MSM", "SE", "F")


   if len(cams_queue) < 10 and len(in_queue) < 10:
      proc_status = "up-to-date"

 
   # make the meteor detection index for today
   os.system("./autoCal.py meteor_index " + day)

   # make the detection preview images for the day
   os.system("./flex-detect.py bmpi " + day)

   # make the detection preview images for the day
   os.system("./wasabi.py sa " + day)

   make_station_report(day, rpt)

def check_time(day):
   now = datetime.now() 
   today = now.strftime("%Y_%m_%d")
   year, mon, dom = day.split("_")
   time_dir = "/mnt/archive.allsky.tv/" + json_conf['site']['ams_id'] + "/DETECTS/MI/" + year + "/" 
   time_file = time_dir + day + "-time.txt"
   if cfe(time_dir, 1) == 0:
      os.makedirs(time_dir)
   if today != day:
      return()
   else:
 
      cmd = "wget -q http://worldtimeapi.org/api/timezone/Europe/London.txt -O - |grep utc_datetime >> " + time_file + "; date -u >> "  + time_file
      os.system(cmd)
      print(time_file)
      fp = open(time_file, "r")
      lines = []
      for line in fp:
         lines.append(line)
      return (lines[-2] + " " + lines[-1])
      
os.system("./wasabi.py mnt")
cmd = sys.argv[1]

if cmd == "ct":
   check_time(sys.argv[2])

if cmd == "all":
   do_all(sys.argv[2])
if cmd == "msr":
   make_station_report(sys.argv[2])
if cmd == "batch":
   batch(sys.argv[2])
if cmd == "cd":
   check_disk()
