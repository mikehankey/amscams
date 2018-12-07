#!/usr/bin/python3
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


def get_bp_motion(motion_file):

   file = open(motion_file, "r")
   event = []
   events = []

   for line in file:
      line = line.replace("\n", "")
      (frameno, mo, bpf, cons_mo) = line.split(",");
      if (int(cons_mo) > 0):
         #print ("Cons:", cons_mo);
         event.append([frameno,mo,bpf,cons_mo])
      else:
         #print ("Event Len:", len(event)   )
         if len(event) > 10:
            events.append(event)
         event = []

   #event_count = 1
   #for event in events:
      #print ("Event:", event)
      #start_frame = int(event[0][0])
      #end_frame = int(event[-1][0])
      #frame_elp = int(end_frame) - int(start_frame)
      #start_sec = int(start_frame / 25) - 5
      #if start_sec <= 0:
      #   start_sec = 0
      #dur = int(frame_elp / 25) + 5 + 3
      #outfile = ffmpeg_trim(mp4_file, start_sec, dur, "-trim" + str(event_count))
      #event_count = event_count + 1;
      #print ("EVENT Start frame: ", start_frame, start_sec)
   #   print ("EVENT End frame: ", end_frame, start_sec + dur)
   #   print ("Total frames: ", frame_elp, dur)
      #reject_filters(outfile)
   return(events)



def examine_video_clip(video_file):
   (motion, reject, confirm) = get_motion_file(video_file)
   stack_file = video_file.replace(".mp4", "-stacked.png")
   motion_file = video_file.replace(".mp4", "-motion.txt")
   confirm_file = video_file.replace(".mp4", "-confirm.txt")
   cams_detect = 0
   frame_file_base = video_file.replace(".mp4", "")
   print("Detection Details: <UL>")
   if (motion == 1):
      print ("<LI>Motion detected " )
      if confirm == 1:
         frame_data = get_frame_data(confirm_file)
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
   for trim_file in trim_files:
      print ("SD Clip " + str(clips) + "<p><iframe width=640 height=480 src=" + trim_file + "></iframe></p>")
      print ("HD Clip " + str(clips))

   if motion == 1:
      # print out the motion details from CV2 motion detector
      print ("<h2>Bright Pixel Detection Details</h2>") 
      events = get_bp_motion(motion_file)
      ec = 1
      for event in events:
         print("Event " + str(ec))
         print ("<table border=1>")  
         print("<tr><td>Main Clip Frame #</td><td>Factor</td><td>Consectuive Frame</td><td>Frame Image</td></tr>")
         
         for mf in event:
            print ("<tr><td>" + str(mf[0]) + "</td><td>" + str(mf[2]) + "</td><td>" + str(mf[3]) + "</td></tr>")
         ec = ec + 1
         print ("</table>")

      if len(frame_data) > 0:
         print ("<h2>Motion Details</h2>") 
         #print ("<table border=1>")  
         #print("<tr><td>Trim Clip</td><td>Frame #</td><td>Contours (x,y,w,h)</td><td>Consectuive Frame</td><td>Frame Image</td></tr>")
        
         fc = 1
         for fd in frame_data:
            #print ("<tr><td>" + str(fd[0]) + "</td><td>" + str(fd[1]) + "</td><td>" )
            tc = fd[0]
            #print(fd[2])
            #for x,y,w,h in fd[2]:
            #   print (x,y,w,h,"<BR>") 
            frame_image = frame_file_base + "-trim" + str(tc) + "-fr" + str(fc) + "-tn.png"
            #print( "</td><td>" + str(fd[3]) + "</td><td><img src=" + frame_image + "></tr>")
            print("<div style='float: left'><img src=" + frame_image + "><br><caption>" + str(tc) + "-" + str(fc) )
            fd_temp = sorted(fd[2], key=lambda x: x[3], reverse=True)
            if len(fd_temp) > 0:
               x,y,w,h = fd_temp[0]
               print (x,y,w,h,"<BR>") 

            print(" </caption></div>")
            fc = fc + 1
            

   if cams_detect == 1:
      print ("<h2>Cams detection info</h2>") 


def get_trim_clips(video_file):
   trim_wildcard = video_file.replace(".mp4", "-trim*.mp4")
   trim_files = glob.glob(trim_wildcard)
   return(trim_files)

def get_frame_data(frame_data_file):
   fdf = open(frame_data_file)
   d = {}
   code = "frame_data = "
   for line in fdf:
      code = code + line
   exec (code,  d)

   return(d['frame_data'])

   

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
          
   else:
      print ("Scan file does not exists.", scan_file)
   
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
         master_stack_file = proc_dir + day + "/"  + cams_id + "-night-stack.png?" + str(rand_num)
         #master_stack_img = "<img alt='cam" + str(cn) + "' onmouseover='bigImg(this)' onmouseout='normalImg(this)' width=320 height=240 src='" + master_stack_file + "'>"
         #master_stack_img = "<img alt='cam" + str(cn) + "' onmouseover='normalImg(this)' onmouseout='normalImg(this)' width=320 height=240 src='" + master_stack_file + "'>"
         master_stack_img = "<img alt='cam" + str(cn) + "' width=320 height=240 src='" + master_stack_file + "'>"
         html = html + "<a href=archive-side.py?cmd=browse_day&day=" + day + "&cam_num=" + str(cn) + ">" + master_stack_img + "</a>" + "\n"
      html = html + "<P>"
      d = d + 1
   return(html)

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
   form = cgi.FieldStorage()
   debug = form.getvalue('debug')
   files = sorted(get_rejects(), reverse=True)
   for file in files:
      print("<img src=" + file + ">")

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
   print(str(od) + " objects auto detected<BR>")
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
      file_dict = parse_tags(tag_file, file_dict) 
   count = 0
   for file in files:
      jpg = file.replace(".mp4", "-stacked.png") 
      blend = file.replace(".mp4", "-blend.jpg") 
      #diff = file.replace(".mp4", "-diff.jpg") 
      diff = file.replace(".mp4", "-objects.jpg") 
      if jpg in img_dict:
         hit = int(img_dict[jpg]['hit'])
         status_desc = img_dict[jpg]['status_desc']   
      else: 
         hit = 0 
         status_desc = "rejected for brightness" 
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

main()


