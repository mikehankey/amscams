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
from lib.FileIO import cfe, load_json_file, save_json_file

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

      print("<TABLE border=1>") 
      print("<TR><td>Event ID</td><td>Start Time</td><td>Obs</td><td>Solved</td></tr>") 
      for event_id in events:
         event = events[event_id]
         img_html = ""
         for img in event['prev_imgs']:
            img_html += "<img src=" + img + ">"
         print("<tr><td>" + event_id + "</td><td>" +  event['event_start_time'] + "</td><td>" +img_html + "</td></tr>")
      print("</TABLE>") 


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

def EventDetail(json_conf, form):
   event_id = form.getvalue("event_id")
   station_id = json_conf['site']['ams_id']
   event_year = event_id[0:4]
   event_day = event_id[0:10]
   event_dir = "/mnt/ams2/meteor_archive/" + station_id + "/EVENTS/" + event_year + "/" + event_day + "/" + event_id + "/" 
   year,mon,day,hour,min,sec = event_id.split("_")
   report_base = year + mon + day + "_" + hour + min + sec
   report_file = report_base + "_report.txt"
   plots = glob.glob(event_dir + "*.png")
   reports = glob.glob(event_dir + "*.json")
   plot_list = ""
   for plot in sorted(plots):
      plot_name = plot.split("/")[-1]
      plot_list += "<a href=" + plot + ">" + plot_name + "</a><br>"
   report_list = ""
   for report in sorted(reports):
      report_name = report.split("/")[-1]
      report_list += "<a href=" + report + ">" + report_name + "</a><br>"

   print("<table>")
   print("<tr><td><b>Event ID:</b></td><td>" + event_id + "</td></tr>")
   print("<tr><td><b>Event Dir:</b></td><td>" + event_dir + "</td></tr>")
   print("<tr><td><b>Plots:</b></td><td>" + plot_list + "</td></tr>")
   print("<tr><td><b>Reports:</b></td><td>" + report_list + "</td></tr>")
   print("</table>")
   

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

