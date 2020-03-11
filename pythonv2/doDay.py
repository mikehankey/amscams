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
import re
from datetime import datetime, timedelta
import subprocess
import random
import requests

from lib.Video_Tools import define_crop_video, crop_video_keep_meteor_centered
from lib.FileIO import load_json_file, save_json_file, cfe
from lib.UtilLib import check_running
from lib.Video_Tools_Fundamentals import create_cropped_video 

# REGEXP Used to get info from the paths
REGEX_REPORT = r"(\d{4})_(\d{2})_(\d{2})_(\d{2})_(\d{2})_(\d{2})_(\d{3})_(\w{6})-trim(\d{4}|\d{3}|\d{2}|\d{1})-prev-crop.jpg"
REGEX_GROUP_REPORT = ["name","year","month","day","hour","min","sec","ms","cam_id","trim"]
 
STATION_REPORT_TEMPLATE = "/home/ams/amscams/pythonv2/templates/allsky.tv.base.html"

# ARCHIVE PATH
ARCHIVE_PATH = "http://archive.allsky.tv" 
ARCHIVE_RELATIVE_PATH = "/mnt/archive.allsky.tv/"
 
PATH_TO_CONF_JSON = "/home/ams/amscams/conf/as6.json" 
json_conf = load_json_file(PATH_TO_CONF_JSON)

def analyse_report_file(file_name):
   matches = re.finditer(REGEX_REPORT, file_name, re.MULTILINE)
   res = {}
  
   for matchNum, match in enumerate(matches, start=1):
      for groupNum in range(0, len(match.groups())): 
         if(match.group(groupNum) is not None):
            res[REGEX_GROUP_REPORT[groupNum]] = match.group(groupNum)
         groupNum = groupNum + 1

   return res



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
   print(events)
   print(event_files)
   return(events,event_files)

def run_df():
   df_data = []
   mounts = {}
   if True:
      cmd = "df -h "
      output = subprocess.check_output(cmd, shell=True).decode("utf-8")
      #Filesystem                 Size  Used Avail Use% Mounted on

      for line in output.split("\n"):
         #line = line.replace("  ", " ")
         temp = " ".join(line.split())
         disk_data = temp.split(" ")
         if len(disk_data) > 5:
            file_system = disk_data[0]
            size = disk_data[1]
            used  = disk_data[2]
            avail = disk_data[3]
            used_perc = disk_data[4]
            mount = disk_data[5]
            print(mount, used_perc)
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


def add_section(id,link_from_tab,tab_content,TAB, TAB_CONTENT, cur=False):
   
   if(cur is True):
      ext_ = 'active'
      b = 'show'
   else:
      ext_ = ''
      b =''

   TAB += '<li class="nav-item"><a class="nav-link '+ext_+'" id="'+id+'-tab" data-toggle="tab" href="#'+id+'" role="tab" aria-controls="'+id+'" aria-selected="true">'+link_from_tab+'</a></li>'
   if(tab_content is not None):
      TAB_CONTENT += '<div class="tab-pane fade '+b+'  '+ext_+'" id="'+id+'" role="tabpanel" aria-labelledby="'+id+'-tab">'+tab_content+'</div>'
   
   return TAB, TAB_CONTENT 


def make_station_report(day, proc_info = ""):
   template = get_template(STATION_REPORT_TEMPLATE) 

   # print("PROC INFO:", proc_info)
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

   single_html, multi_html, info = html_get_detects(day, station, event_files, events)
  
   detect_count = info['mc']
 
   show_date = day.replace("_", "/")
 
   TAB= ''
   TAB_CONTENT = '' 

   # LIVE VIEW
   live_view_html = ""

   # Is it the current day? (otherwise we don't show anything)
   show_day_date =  datetime.strptime(show_day, '%m/%d/%Y')

   if(show_day_date == datetime.now() ) :
      if len(data['files']) > 0:
         data['files'] = sorted(data['files'], reverse=True)
         fn = data['files'][0].replace("/mnt/archive.allsky.tv", "")
         live_view_html += "<img src='" + fn + "' class='img-fluid'/>"
 
      TAB, TAB_CONTENT = add_section('live','Live View',live_view_html, TAB, TAB_CONTENT)
  
   # WEATHER SNAP SHOTS 
   we_html = ""
   if len(data['files']) > 0:
       
      for file in sorted(data['files'],reverse=True):
         fn = file.replace("/mnt/archive.allsky.tv", "")
         we_html += "<img src='" + fn + "' class='img-fluid weath'>"
   
   # We only display something... if we have something to display
   if(we_html!=''):
      # We add the toolbar
      we_html = '<div class="top_tool_bar"><a href="#" id="play_anim_thumb" class="btn btn-success"><span class="icon-youtube"></span> All Day Animation</a></div>' + we_html
      TAB, TAB_CONTENT = add_section('weather','Weather',we_html, TAB, TAB_CONTENT)
    
 
   # Add specific tool bar for meteors
   # (delete all/confirm all)
   multi_html = multi_html + single_html
   if(multi_html != '' ):
      multi_tb = '<div id="top_tool_bar"><div class="d-flex">'
      multi_tb += '<div class="control-group"><div class="m-0 p-0"><div class="input"><div id="lio_filters" class="btn-group" data-toggle="buttons-checkbox"><button class="btn btn-secondary active" id="lio_btn_all" aria-pressed="true">ALL</button><button class="btn btn-secondary" id="lio_btn_pnd"  aria-pressed="false">Pending ('+ str(info['pending_count']) +')</button><button class="btn btn-secondary" aria-pressed="false" id="lio_btn_arc">Archived ('+ str(info['arc_count']) +')</button></div></div></div></div>'
      multi_tb += '<div class="control-group ml-3"><div class="m-0 p-0"><div class="input"><div id="lio_sub_filters" class="btn-group" data-toggle="buttons-checkbox"><button class="btn btn-secondary active" id="lio_sub_btn_all" aria-pressed="true">ALL</button><button class="btn btn-secondary" id="lio_sub_btn_single"  aria-pressed="false">Single Station ('+ str(info['ss_count']) +')</button><button class="btn btn-secondary" aria-pressed="false" id="lio_sub_btn_multi">Multi-Stations ('+ str(info['ms_count']) +')</button></div></div></div></div>'
      multi_tb += '<div class="lio ml-auto"><button id="conf_all" class="btn btn-success">Confirm All</button> <button id="del_all" class="btn btn-danger">Delete All</button> <button id="cancel_all" class="btn btn-secondary">Cancel</button></div></div></div>'

      TAB, TAB_CONTENT = add_section('multi',"Meteors (" + str(info['ms_count']+info['ss_count']) + ")",multi_tb +"<div class='d-flex align-content-start flex-wrap'>" + multi_html  + "</div>", TAB, TAB_CONTENT, True) 
   else:
      TAB, TAB_CONTENT = add_section('multi',"Meteors (0)","<div class='alert alert-danger'>No Meteor Found for this day</div>", TAB, TAB_CONTENT, True) 

   # Single-station meteor
   template = template.replace("{TABS}", TAB)
   template = template.replace("{TABS_CONTENT}", TAB_CONTENT)
 
   # Proccess Info (last one)
   if(proc_info != ''):
      TAB, TAB_CONTENT = add_section('proc_info','Processing Info',proc_info, TAB, TAB_CONTENT) 

   template = template.replace("{RAND}",str(random.randint(0, 99999999)))
   
   fpo = open(html_index, "w")
   fpo.write(template)
   fpo.close()
   print(html_index)
  
 

def html_get_detects(day,tsid,event_files, events):
 
   year = day[0:4]
   month = day[5:7]
   d_day = day[8:]
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
   video_path = "" 
 
   if mid is not False:
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
            
               style = "multi"
               # look for the event solution dir
               event_dir = "/mnt/archive.allsky.tv/EVENTS/" + year + "/" + day + "/" + event_id + "/"
               event_vdir = "/EVENTS/" + year + "/" + day + "/" + event_id + "/"
               event_file = event_dir + event_id + "-report.html"
               event_vfile = event_vdir + event_id + "-report.html"
            
               if len(events[event_id]['solutions']) > 0 :
                  elink = "<a href=" + event_vfile + " class='T'>"
                  solved_count += 1  
               else: 
                  elink = "<a class='T'>"
                  not_run += 1
            else:
               event_id = None
               elink = "<a class='T'>"
         
            mfile = key.split("/")[-1]
            prev_crop = mfile.replace(".json", "-prev-crop.jpg")
            prev_full = mfile.replace(".json", "-prev-full.jpg")

            image_file = prev_crop
            if arc_file == "pending":
               css_class = "prevproc pending"
            else:
               css_class = "prevproc arc"

            if event_id is not None:
               css_class += " multi"
            else:
               css_class += " single"
               event_id = ""

            # Video PATH (HD)
            if(arc == 1):
               video_path = ARCHIVE_PATH + os.sep + tsid + os.sep + 'METEOR' + os.sep + year + os.sep + month + os.sep + d_day + os.sep + image_file.replace('-prev-crop.jpg','-HD.mp4')
               jreport_path = ARCHIVE_PATH + os.sep + tsid + os.sep + 'METEOR' + os.sep + year + os.sep + month + os.sep + d_day + os.sep + image_file.replace('-prev-crop.jpg','.html')
            else:
               video_path = ''
               jreport_path = ''    

            # We get more info 
            #print("(BEFORE AN) EVENT ID IS:", event_id) 
            analysed_name = analyse_report_file(image_file)
  
            dur = '' 

            # Create CROPPED VIDEO
            cropped_video_file = ''
            if(jreport_path!=''): 
               json_file = jreport_path.replace('.html',".json").replace(ARCHIVE_PATH,ARCHIVE_RELATIVE_PATH).replace('//','/')
               cropped_video_file = create_cropped_video(json_file.replace('.json',"-HD.mp4"),json_file,json_file.replace('.json',"-HD-cropped.mp4"))
               if(cropped_video_file is False):
                  cropped_video_file = 'X'
               else:
                  cropped_video_file = cropped_video_file.replace(ARCHIVE_RELATIVE_PATH,ARCHIVE_PATH+os.sep)


            if event_id is None or event_id == "none" or event_id == '': 


               # Get full version of the preview if video_path is empty
               if(video_path==''):
                  full_path = ARCHIVE_PATH + was_vh_dir + image_file.replace('crop','full')
                  request = requests.get(full_path)
                  if request.status_code == 200:
                     video_path = "<a href='"+full_path+"' class='img-link btn btn-secondary btn-sm'><span class='icon-eye'></span></a>"

               if(jreport_path!=''):
                  elink = "<a href=" + jreport_path + " class='T' data-src="+cropped_video_file+">"

               single_html += "<div class='"+css_class+"'>" + elink +  "<img src='"+was_vh_dir + image_file+"' class='img-fluid'></a>"
               single_html += "<div class='d-flex mb-2'><div class='mr-auto'><span>"+'<b>Cam#' + analysed_name['cam_id'] + '</b> '+ analysed_name['hour']+':'+analysed_name['min']+':'+analysed_name['sec']+'.'+analysed_name['ms'] + "</div>"
               single_html += "<div>"+video_path+"</div>"+dur+"</div></div>"
               ss_count += 1 
            else:

               if(event_id !=''):
                  event_id = "</span><span><b>Event</b> #" + str(event_id)  

               if(jreport_path!=''):
                  elink = "<a href=" + jreport_path + " class='T'  data-src="+cropped_video_file+">"

               multi_html += "<div class='"+css_class+"'>" + elink +  "<img src='"+was_vh_dir + image_file+"' class='img-fluid'></a>"
               multi_html += "<div class='d-flex mb-1'><div class='mr-auto'><span>"+'<b>Cam#' + analysed_name['cam_id'] + '</b> '+ analysed_name['hour']+':'+analysed_name['min']+':'+analysed_name['sec']+'.'+analysed_name['ms'] + event_id+"</div>"
               multi_html += "<div class='position-relative'><a href='"+video_path+"' class='vid-link btn btn-secondary btn-sm'><span class='icon-youtube'></span></a><span class='multi-b'>Multi</span></div>"+dur+"</div></div>"
               ms_count += 1

            video_path = '' 
            mc += 1
         else:
            html += "No meteors detected."            
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
  
   #os.system("git pull")
   proc_vids, proc_tn_imgs, day_vids,cams_queue,in_queue = get_processing_status(day)
   detect_files, arc_files = get_meteor_status(day)

   time_check = check_time(day) 
   # figure out how much of the day has completed processing
   rpt = """ 
      <dl class="row p-4">
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
   os.system("/home/ams/amscams/pythonv2/autoCal.py meteor_index " + day)
   print("AUTOCAL DONE")

   # make the detection preview images for the day
   os.system("/home/ams/amscams/pythonv2/flex-detect.py bmpi " + day)
   print("FLEXDETECT BMPI DONE")

   # make the detection preview images for the day
   os.system("/home/ams/amscams/pythonv2/wasabi.py sa " + day)
   print("WASABI SA DONE")
   
   make_station_report(day, rpt)
   print("STATION DONE ")

   # Make all the reports for the given day 
   for f in arc_files: 
      
      # Create REPORT PAGE
      ff = os.sep + f.replace(ARCHIVE_RELATIVE_PATH,'').replace('/mnt/ams2/meteor_archive/','')
      ff = ARCHIVE_RELATIVE_PATH + ff.replace('//','/')
      ff = ff.replace('//','/')
      print("PUBLISH REPORT FOR " + ff )
      #cmd = "python3 /home/ams/amscams/pythonv2/publish.py event_station_report " +  ff
      #os.system(cmd)

   print("DO ALL DAY DONE")
     

      

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
      
os.system("/home/ams/amscams/pythonv2/wasabi.py mnt")
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
