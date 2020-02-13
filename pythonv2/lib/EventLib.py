from random import randint
from lib.UtilLib import calc_dist
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
import numpy as np
import time
from lib.FileIO import cfe, load_json_file, save_json_file

def make_object_image(img, data):
   cvimg = cv2.imread(img)
   oimg = img.replace(".png", "-obj.png")
   for i in range(0,len(data['ofns'])):
      x = data['oxs'][i]
      y = data['oys'][i]
      cv2.circle(cvimg,(x,y), 1, (255,0,0), 1)
      cv2.imwrite(oimg, cvimg)

def calc_seg_len(data):
   fx = None
   last_dist_from_start = None
   fc = 0
   segs = []
   bad_segs = 0
   for i in range(0, len(data['ofns'])):
      x = data['oxs'][i]
      y = data['oys'][i]
      if fx is None:
         fx = x
         fy = x
      dist_from_start = calc_dist((fx,fy),(x,y))
      data['dist_from_start'] = dist_from_start
      if last_dist_from_start is not None:
         seg_len = int(abs(dist_from_start - last_dist_from_start))
         segs.append(seg_len)
         if seg_len == 0:
            bad_segs += 1
      else:
         segs.append(0)
      last_dist_from_start = dist_from_start
      fc += 1
   data['segs'] = segs
   data['med_seg'] = float(np.median(segs))
   for seg in segs:
      diff = abs(seg - data['med_seg'])
      if data['med_seg'] > 0:
         diff_diff = seg / data['med_seg']
         if diff_diff > 2 or diff_diff < .5:
            bad_segs += 1
   data['bad_seg_perc'] = bad_segs / (len(data['ofns']) - 1)
   data['bad_segs'] = bad_segs
   return(data) 

def classify_object(data, sd=1):
   fns = data['ofns']
   x = data['oxs']
   y = data['oys']
   hd_px_scale = 260   # arc seconds
   sd_px_scale = 260 * 2.72
   if sd == 1:
      px_scale = sd_px_scale
   else:
      px_scale = hd_px_scale

   px_dist = calc_dist((x[-1],y[-1]), (x[0],y[0]))

   angular_separation_px = np.sqrt((x[-1] - x[0])**2 + (y[-1] - y[0])**2) / float(fns[-1] - fns[0]) 
   angular_velocity_px = angular_separation_px * 25

   angular_separation_deg = (angular_separation_px * px_scale) / 3600

   # Convert to deg/sec
   #scale = (config.fov_h/float(config.height) + config.fov_w/float(config.width))/2.0
   #ang_vel = ang_vel*scale

   angular_velocity_deg = (angular_velocity_px * px_scale) / 3600
   report = {}
   report['px_dist'] = px_dist
   report['ang_sep_px'] = angular_separation_px
   report['ang_vel_px'] = angular_velocity_px
   report['ang_sep_deg'] = angular_separation_deg
   report['ang_vel_deg'] = angular_velocity_deg

   report['meteor_yn'] = "Y"

   # filter out detects with low CM 
   last_fn = None
   cm = 0 
   for fn in fns:
      if last_fn is not None: 
         if (last_fn + 1 == fn) or (last_fn + 2 == fn):
            cm += 1
      last_fn = fn
   if cm < 3:
      report['meteor_yn'] = "no"
   report['cm'] = cm

   # filter out detects that have too many dupe pix
   unq_keys = {}
   unq = 0

   for i in range(0, len(fns)):
      key = str(data['oxs'][i]) + "." + str(data['oys'][i])
      if key not in unq_keys:
         unq += 1
         unq_keys[key] = 1
   if len(data['oxs']) > 0:
      unq_perc = unq / len(data['oxs'])
      report['unq_perc'] = unq_perc
      report['unq'] = str(unq) + "/" + str(len(data['oxs'])) 
      report['unqkeys'] = str(unq_keys)
   if unq_perc < .7:
      report['meteor_yn'] = "no"
      
   # filter out detects that have too many bad seg lens 
   data = calc_seg_len(data)
   if data['bad_seg_perc'] >= .49:
      report['meteor_yn'] = "no"
   print(data['segs'])

   # filter out detects that are zig zagged or not moving in the same direction too much as % of frames

   

   # filter out detections that don't match ang vel or ang sep desired values 
   if report['meteor_yn'] == "Y" and float(report['ang_vel_deg']) > .5 and float(report['ang_vel_deg']) < 35:
      report['meteor_yn'] = "Y"
   else:
      report['meteor_yn'] = "no"

   if report['meteor_yn'] == "Y" and report['ang_sep_deg'] < .4:
      report['meteor_yn'] = "no"

   # filter out detects have more the 33% low or negative intensity frames 
   itc = 0
   for intense in data['oint']:
      if intense < 10:
         itc += 1
   if itc > 0:
      itc_perc = itc / len(data['oint'])
      report['neg_int_perc'] = itc_perc
      if itc_perc > .3:
         report['meteor_yn'] = "no" 
   report['segs'] = data['segs'] 
   report['bad_seg_perc'] = data['bad_seg_perc'] 

   return(report)

def DetectsQueue(form):
   files = glob.glob("/mnt/ams2/CAMS/queue/*detect*.json")
   html = ""
   nonhtml = ""
   md = 0
   nd = 0
   tot = 0
   for file in files:
      img = file.replace("-detect.json", "-stacked.png")
      imgf = img.split("/")[-1]
      day = imgf[0:10]
      img = "/mnt/ams2/SD/proc2/" + day+ "/images/" + imgf
      if cfe(img) == 0:
         img = "/mnt/ams2/CAMS/queue/" + imgf

      oimg = img.replace(".png", "-obj.png")


      if cfe(file) == 1:
         data = load_json_file(file)
         if "motion_objects" in data:
            for key in data['motion_objects']:
               if data['motion_objects'][key]['report']['meteor_yn'] == "Y":
                  if "ofns" in data['motion_objects'][key]:
                     if data['motion_objects'][key]['ofns'] is not None:
                        new_data = classify_object(data['motion_objects'][key])
            
                  if cfe(oimg) == 0:
                     make_object_image(img, data['motion_objects'][key])
               


                  report = "FNS:" + str(data['motion_objects'][key]['ofns']) + "<BR>"
                  report += "XS:" + str(data['motion_objects'][key]['oxs']) + "<BR>"
                  report += "YS:" + str(data['motion_objects'][key]['oys']) + "<BR>"
                  report += "INTS:" + str(data['motion_objects'][key]['oint']) + "<BR>"
                  report += "REPORT:" + str(new_data)
                  for rkey in data['motion_objects'][key]['report']:
                     report += rkey + ":" + str(data['motion_objects'][key]['report'][rkey]) + "<BR>"
                  report += "NEW DATA"
                  for rkey in new_data:
                     report += rkey + ":" + str(new_data[rkey]) + "<BR>"
                  vid = img.replace("-stacked.png", ".mp4")
                  vid_wild = img.replace("-stacked.png", "*.mp4")
                  if cfe(vid) == 0:
                     vid_link = "<a href=" + vid + ">" 
                  else:
                     vid_link = "" 
                  #temp = glob.glob(vid)
                  #if len(temp) > 0:
                  #   if cfe(temp[0]) == 0:
                  #      print(vid, " NO FOUND")
                  detect_html = "<figure>" + vid_link + "<img src=" + oimg + "></a><figcaption>" + report + "</figcaption></figure>"
                  if new_data['meteor_yn'] == "Y":
                     html = html + detect_html
                     md += 1
                  else:
                     nonhtml = nonhtml + detect_html
                     nd += 1
      tot = tot + 1

   print("Meteor Detections:" + str(md) + "<BR>")
   print(html)
   print("Non Meteor Detections:" + str(nd) + "<BR>")
   print(nonhtml)

def DetectsMain(form ):
   json_conf = load_json_file("/home/ams/amscams/conf/as6.json")
   station = json_conf['site']['ams_id']   
   print("<h1>Multi-station detections for ", station, "</h1>")
   detect_file = "/mnt/ams2/meteor_archive/" + station + "/DETECTS/ms_detects.json"
   detect_data = load_json_file(detect_file)
   events = {}
   for key in sorted(detect_data.keys(), reverse=True):
      for file in detect_data[key]:
         stations = detect_data[key][file]['stations']
         files = detect_data[key][file]['obs']
         arc_files = detect_data[key][file]['arc_files']
         event_id = detect_data[key][file]['event_id']
         event_start = detect_data[key][file]['event_start']
         count = detect_data[key][file]['count']
         if event_id not in events:
            events[event_id] = {} 

         events[event_id]['event_id'] = event_id
         events[event_id]['event_start'] = event_start 
         events[event_id]['count'] = count 
         events[event_id]['stations'] = stations
         events[event_id]['files'] = files 
         events[event_id]['arc_files'] = arc_files 
        
   for event_id in events:
      event_year = event_id[0:4]
      event_day = event_id[0:10]
      event_dir = "/mnt/ams2/meteor_archive/" + station + "/EVENTS/" + event_year + "/" + event_day + "/" + event_id + "/" 
      year,mon,day,hour,min,sec = event_id.split("_")
      report_base = year + mon + day + "_" + hour + min + sec
      report_file = report_base + "_report.txt"
      print(event_dir + report_file)
      if cfe(event_dir + report_file) == 1:
         print("<h1> <a href=" + event_dir + ">" + str(event_id) + "<a/></h1>")
      else:
         print("<h1> " + str(event_id) + "</h1>")
      print("Event Start Time: " + str(events[event_id]['event_start']) + "<BR>")
      pc = 0
      for af in events[event_id]['arc_files']:
         if af == 'pending':
            pc += 1
         #print("<span style='color: red'>Arc Files Pending: " + str(pc) + "</span><BR>")
      print("<table><tr><td>#</td><td>Station</td><td>Detect File</td><td>Arc File</td></tr>")
      for i in range(0,len(events[event_id]['arc_files'])):
         if pc > 0:
            style = "<span style='color: red'>"
         print("<tr><td>" + str(i) +  "</td><td>" + str(events[event_id]['stations'][i]) + "</td><td>" +  events[event_id]['files'][i] + "</td><td><a href=/pycgi/webUI.py?cmd=goto&station="+ events[event_id]['stations'][i] + "&" + "file=" + events[event_id]['arc_files'][i] + ">" + events[event_id]['arc_files'][i] + "</a> </td></tr>");
      print("</table>")



   event_dir = "/mnt/ams2/meteor_archive/" + station + "/EVENTS/" + str(event_year) + "/"
   if cfe(event_dir, 1) == 0:
      os.makedirs(event_dir)
   save_json_file(event_dir + str(event_year) + "-events.json", events)
   print("Saved:" + event_dir + str(event_year) + "-events.json") 
 

def DetectsDetail(form):
   print("..", station)

def EventsMain(json_conf, form):

   station_id = json_conf['site']['ams_id']
   year = form.getvalue("year")
   day = form.getvalue("day")
   show_multi = form.getvalue("show_multi")
   if show_multi is None:
      show_multi = 0
   show_solved = form.getvalue("show_solved")
   events_dir = "/mnt/ams2/meteor_archive/" + station_id + "/EVENTS/"
 
   if year is None:
      print("Select Event Year: <UL>")
      years = glob.glob("/mnt/ams2/meteor_archive/" + station_id + "/EVENTS/*")
      for file in years:
         tyear = file.split("/")[-1]
         print("<a href=webUI.py?cmd=events&year=" + tyear + ">" + tyear + "</a><br>")
   elif day is None:
      days = glob.glob("/mnt/ams2/meteor_archive/" + station_id + "/EVENTS/" + year + "/*")
 
      for tday in sorted(days, reverse=True):
         if cfe(tday, 1) == 1:
            sday = tday.split("/")[-1]
            print("<a href=webUI.py?cmd=events&year=" + year + "&day=" + sday + ">" + sday + "</a><br>")
   else:
      # show page for one day of events from one network group (not the global system )
      day_file = "/mnt/ams2/meteor_archive/" + station_id + "/EVENTS/" + year + "/" + day + "/" + day + "-events.json"
      events = load_json_file(day_file)

      network_sites = json_conf['site']['network_sites'].split(",")
      network_sites.append(json_conf['site']['ams_id'])
      net_desc = ""
      for ns in sorted(network_sites):
         if net_desc != "":
            net_desc += ","
         net_desc += ns 
      (single_station, multi_station,station_meteors) = event_stats(events)
      print("<h1>Meteor Nework Report for " + day + "</h1>")
      print("<P><B>Network Sites:</B> " + net_desc + "<br>")
      print("<P><B>Total Unique Meteors :</B> " + str(len(events)) + "<br>")
      print("<P><B>Total Multi Station Meteors :</B> <a href=webUI.py?cmd=events&year=" + year + "&day=" + day + "&show_multi=1>" + str(multi_station) + "<a/><br>")
      print("<P><B>Total Single Station Meteors :</B> " + str(single_station) + "<br>")
      print("<table>")
      print("<tr><td>Station</td><td>Total Observations</td><td>Single Station Meteors</td><td>Multi Station Meteors</td><td>Total Unique Meteors </td></tr>")

      for st in station_meteors:
         total_meteors = station_meteors[st]['single_station'] + station_meteors[st]['multi_station']
         print("<tr><td>" + st + "</td><td>" + str(station_meteors[st]['total_obs']) + "</td><td>" + str(station_meteors[st]['single_station']) + "</td><td>" + str(station_meteors[st]['multi_station']) + "</td><td>" + str(total_meteors) + "</td></tr>")
      print("</table>")
     
      print("<TABLE border=1>") 
      print("<TR><td>Event ID</td><td>Start Time</td><td>Obs</td><td>Solved</td></tr>") 
      for event_id in events:

         event = events[event_id]
         img_html = ""
         for i in range(0, len(event['stations'])):
            arc_file = event['arc_files'][i] 
            station = event['stations'][i] 
            old_file = event['files'][i].split("/")[-1]
            img = event['prev_imgs'][i]
            sol_text = ""
            if arc_file == "pending":
               link = "<div style='float: left'><figure><a href=webUI.py?cmd=goto&old=1&file=" + old_file + "&station_id=" + station + ">" 
               obs_desc = event['stations'][i] + "-pending"
            else:
               arc_fn = arc_file.split("/")[-1]
               el = arc_file.split("_")[7]
               other = el.split("-")
               cam_id = other[0]
               obs_desc = event['stations'][i] + "-" + cam_id
               for sol in event['solutions']:
                  type, file, status = sol
                  sol_text += type + " " + str(status) + "<BR>"
               link = "<div style='float: left'><figure><a href=webUI.py?cmd=goto&file=" + arc_fn + "&station_id=" + station + ">" 
            img_html += link + "<img src=" + img + "><figcaption>" + obs_desc + " " + event['clip_starts'][i] +  "</a></figcaption></figure></div>"
         elink = "<a href=webUI.py?cmd=event_detail&event_id=" + event_id + ">"
         if (int(show_multi) == 1 and event['count'] > 1) or show_multi == 0:
            print("<tr><td>" + elink + event_id + "</a></td><td>" +  event['event_start_time'] + "</td><td>" +img_html + "</td><td>" + sol_text + "</td></tr>")

      print("</TABLE>") 

def event_stats(events):
   single_station = 0
   multi_station = 0
   station_meteors = {}
   for event_id in events:
      event = events[event_id]
      st_set = set(event['stations'])
      stations = []
      for station in st_set:
         stations.append(station)
      if len(stations) == 1:
         st = stations[0]
         single_station += 1

         if st not in station_meteors:
            station_meteors[st] = {}
            station_meteors[st]['single_station'] = 0
            station_meteors[st]['multi_station'] = 0
            station_meteors[st]['total_obs'] = 0
         station_meteors[st]['single_station'] += 1
      else:
     
         multi_station += 1
         for st in stations:
            if st not in station_meteors:
               station_meteors[st] = {}
               station_meteors[st]['single_station'] = 0
               station_meteors[st]['multi_station'] = 0
               station_meteors[st]['total_obs'] = 0
            station_meteors[st]['multi_station'] += 1

      for st in event['stations']:
         station_meteors[st]['total_obs'] += 1

   return(single_station, multi_station,station_meteors)
 

def EventsMainOld(json_conf, form):
   station_id = json_conf['site']['ams_id']
   year = form.getvalue("year")
   show_solved = form.getvalue("show_solved")
   events_dir = "/mnt/ams2/meteor_archive/" + station_id + "/EVENTS/"
   print("<h1>Events Main</h1>")
   if year is None:
      print("Select Event Year: <UL>")
      years = glob.glob("/mnt/ams2/meteor_archive/" + station_id + "/EVENTS/*")
      for file in years:
         tyear = file.split("/")[-1]
         print("<a href=webUI.py?cmd=events&year=" + tyear + ">" + tyear + "</a><br>")
      exit()

   events_file = events_dir + year + "/" + year + "-events.json"
   events = load_json_file(events_file)
   print("<table border=1>")
   print("<tr><td>Event ID</td><td>Observations</td><td>Event Status</td></tr>")
  
   for event_id in events:
      row = ""
      event = events[event_id]

      status = "unsolved"
      slink = ""
      if "solutions" in event:
         status = ""
         for sol in event['solutions']:
            solver, report_file,solve_status = sol
            if solve_status == 0:
               ss = "failed"
            else:
               ss = "success"
               slink = "<a href=webUI.py?cmd=event_detail&event_id=" + event_id + ">"
            print(solver, solve_status, report_file, ss, "<BR>")
            status = status + solver + " " + ss  + "<BR>"

      row += "<tr><td>" + slink  + event_id + "</a></td><td>"
      for i in range(0, len(event['stations'])):
         arc_file = event['arc_files'][i]
         old_file = event['files'][i]
         of = old_file.split("/")[-1]
         year = of[0:4]
         day = of[0:10]
         station = event['stations'][i]
         prev_fn = of.replace(".json", "-prev-crop.jpg")
         
         prev_img = "/mnt/ams2/meteor_archive/" + station + "/DETECTS/PREVIEW/" + year + "/" + day + "/"  + prev_fn
         prev_imgs = ""
         if cfe(prev_img) == 1:
            prev_html = "<img src=" + prev_img + ">"  
         else:
            prev_html = ""
        
         if arc_file == "pending": 
            link = "<figure><a href=webUI.py?cmd=goto&old=1&file=" + old_file + "&station_id=" + station + ">" + prev_html 
            obs_desc = event['stations'][i] + "-pending"
         else:
            el = arc_file.split("_")[7]
            other = el.split("-")
            cam_id = other[0]
            obs_desc = event['stations'][i] + "-" + cam_id
            link = "<div style='float: left'><figure><a href=webUI.py?cmd=goto&file=" + arc_file + "&station_id=" + station + ">" + prev_html
         row += link + "<figcaption>" + obs_desc + "</figcaption></a></figure></div>"
      row += "</td>"
      row += "<td>" + str(status) + "</td></tr>"
      if status == 1 and show_solved == 1:
         print(row)
      else:
         print(row)
   print("</table>")


def ymd(file):
   y = file[0:4]
   m = file[4:6]
   d = file[6:8]
   return(y,m,d)

def check_file_status(event_id, station, old_file, arc_file):
   # is it in local archive dir
   # is it in wasbi archive dir
   # do we have a preview image for it 
   year,mon,day,hour,min,sec = event_id.split("_")
   dom = event_id[0:10]
   status = {}
   if "/mnt/" in old_file:
      old_file = old_file.split("/")[-1]
   prev_fn = old_file.replace(".json", "-prev-crop.jpg")
   prev_img = "/mnt/ams2/meteor_archive/" + station + "/DETECTS/PREVIEW/" + year + "/" + dom + "/"  + prev_fn
   prev_img_wb = "/mnt/wasabi/" + station + "/DETECTS/PREVIEW/" + year + "/" + dom + "/"  + prev_fn

   wb_arc_file = arc_file.replace("/ams2/meteor_archive", "wasabi")

   if cfe(prev_img) == 1:
      status['preview_image'] = [1, "Preview image exists in local archive."]
   elif cfe(prev_img_wb) == 1:
      status['preview_image'] = [2, "Preview exists in wasabi, but not local archive."]
   else:
      status['preview_image'] = [0, "Preview image not found locally or in wasabi."]

   if arc_file == "pending":
      status['arc_file'] = [0, "Observation has not been archived yet."]
   elif cfe(arc_file) == 1:
      status['arc_file'] = [1, "Arc file found in local archive."  ]
   elif cfe(wb_arc_file) == 1:
      status['arc_file'] = [2, "Arc file found in wasabi."  ]
   else:
      status['arc_file'] = [0, "Arc file not found in local archive or in wasabi." + arc_file]
   return(status)   

def make_prev_img(event_id, station, old_file):
   if "/mnt/" in old_file:
      old_file = old_file.split("/")[-1]
   year,mon,day,hour,min,sec = event_id.split("_")
   dom = event_id[0:10]
   prev_fn = old_file.replace(".json", "-prev-crop.jpg")
   prev_img = "/mnt/ams2/meteor_archive/" + station + "/DETECTS/PREVIEW/" + year + "/" + dom + "/"  + prev_fn
   prev_img_wb = "/mnt/wasabi/" + station + "/DETECTS/PREVIEW/" + year + "/" + dom + "/"  + prev_fn
   return(prev_img, prev_img_wb)

def EventDetail(json_conf, form):
   sync_urls = load_json_file("/home/ams/amscams/conf/sync_urls.json")
   event_id = form.getvalue("event_id")
   station_id = json_conf['site']['ams_id']
   event_year = event_id[0:4]
   event_day = event_id[0:10]
   event_dir = "/mnt/ams2/meteor_archive/" + station_id + "/EVENTS/" + event_year + "/" + event_day + "/" + event_id + "/" 
   events_file = "/mnt/ams2/meteor_archive/" + station_id + "/EVENTS/" + event_year + "/" + event_day + "/" + event_day + "-events.json"
   events_data = load_json_file(events_file)
   event = events_data[event_id]


   if cfe(event_dir, 1) == 0:
      solved = 0
      count = event['count']
      if count > 1:
         print("This event has not been run yet.<P>")
      else:
         print("This is a single station event and can't be solved.<P>")
   else:
      solved = 1

   if solved == 0 or solved == 1:
      solutions = event['solutions']
      print("<B>Event ID:</B>" + event_id+ "<P>")
      print("<TABLE border=1>")
      print("<TR><TD><b>Preview</td><td><b>Arc File</td><td><b>Old File</td><td><b>File Sync Status</td></tr>")
      for i in range(0, len(event['stations'])):
         station = event['stations'][i]
         event_start = event['clip_starts'][i]
         old_file = event['files'][i]
         arc_file = event['arc_files'][i]
         if "/mnt/" in old_file:
            old_file_desc = old_file.split("/")[-1]
         if "/mnt/" in arc_file:
            arc_desc = arc_file.split("/")[-1]
         else:
            arc_desc = arc_file
         obs_status = check_file_status(event_id, station, old_file, arc_file)
         prev_img, wb_prev_img = make_prev_img(event_id,station, old_file)
         print("<tr>")
         print("<td> <img src=" +  prev_img + "><br>" + station + " " + event_start + "</td>" )
         if arc_desc != 'pending':
            print("<td><a href=webUI.py?cmd=reduce2&video_file=" + arc_file + ">" + arc_desc + "</a></td>")
         else:
            url = sync_urls['sync_urls'][station]['sync_url'] + "/pycgi/webUI.py?cmd=reduce&video_file=" + old_file
            print("<td><a href=" + url + ">" + arc_desc + "</a></td>")
         print("<td>" +  old_file + "</td>")
         print("<td>" + obs_status['preview_image'][1] + "<BR>" + obs_status['arc_file'][1] + "</td>")
         print("</tr>")

   year,mon,day,hour,min,sec = event_id.split("_")
   report_base = year + mon + day + "_" + hour + min + sec
   report_file = report_base + "_report.txt"
   plots = glob.glob(event_dir + "*.png")
   reports = glob.glob(event_dir + "*.json")
   plot_list = ""
   for plot in sorted(plots):
      plot_name = plot.split("/")[-1]
      plot_list += "<img width=640 height=480 src=" + plot + ">" 
   report_list = ""
   for report in sorted(reports):
      report_name = report.split("/")[-1]
      report_list += "<a href=" + report + ">" + report_name + "</a><br>"

   if solved == 1:
      print("<table>")
      print("<tr><td><b>Event ID:</b></td><td>" + event_id + "</td></tr>")
      print("<tr><td><b>Event Dir:</b></td><td>" + event_dir + "</td></tr>")
      print("<tr><td><b>Reports:</b></td><td>" + report_list + "</td></tr>")
      print("</table>")
      print(plot_list)
   

def EventDetailOld(form):
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

