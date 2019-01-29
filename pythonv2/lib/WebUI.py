import cgi
import os
from lib.FileIO import get_proc_days, get_day_stats, get_day_files , load_json_file, get_trims_for_file


def make_day_preview(day_dir, json_conf):
   el = day_dir.split("/")
   day = el[-1]
   day_str = day
   html_out = ""
   for cam in json_conf['cameras']:
      cams_id = json_conf['cameras'][cam]['cams_id']
      obj_stack = day_dir + "/" + "images/"+ cams_id + "-night-stack.png"
      meteor_stack = day_dir + "/" + "images/" + cams_id + "-meteors-stack.png"

      day=day.replace("_","")
      html_out = html_out + "<a href=\"webUI.py?cmd=browse_day&day=" + day_str + "&cams_id=" + cams_id \
         + "\" onmouseover=\"document.getElementById(" + day + cams_id + ").src='" + meteor_stack \
         + "'\" onmouseout=\"document.getElementById(" + day + cams_id + ").src='" + obj_stack + "'\">"
      html_out = html_out + "<img id=\"" + day+ cams_id + "\" width='200' src='" + obj_stack + "'></a>\n"
   return(html_out, day_str)
def controller(json_conf):
   
   form = cgi.FieldStorage()
   cmd = form.getvalue('cmd')

   if cmd == 'examine_min':
      video_file = form.getvalue('video_file')
      examine_min(video_file,json_conf)
   if cmd == 'browse_day':
      day = form.getvalue('day')
      cams_id = form.getvalue('cams_id')
      browse_day(day, cams_id,json_conf)
   if cmd == 'reset':
      video_file = form.getvalue('video_file')
      type = form.getvalue('reset')
      reset(video_file, type)
   if cmd == 'examine':
      video_file = form.getvalue('video_file')
#      video_file = "/mnt/ams2/SD/proc2/2019_01_28//passed/2019_01_28_01_56_16_000_010002-trim0545.mp4"
      examine(video_file)
   if cmd == '' or cmd is None:
      main_page(json_conf)   
   if cmd == 'browse_detects':
      day = form.getvalue('day')
      type = form.getvalue('type')
      #type = 'meteor'
      #day = '2019_01_27'
      browse_detects(day,type,json_conf)   
      
   cam_num = form.getvalue('cam_num')
   day = form.getvalue('day')

def reset(video_file, type):
   if "passed" in video_file:
      out_file = video_file.replace("passed/","")
   if "failed" in video_file:
      out_file = video_file.replace("failed/","")

   stack_file = video_file.replace(".mp4", "-stacked.png")
   json_file = video_file.replace(".mp4", ".json")
   cmd = "mv " + video_file + " " + out_file
   mv_cmd = cmd
   print(cmd)
   os.system(cmd)
   cmd = "rm " + stack_file 
   os.system(cmd)
   cmd = "rm " + json_file 
   os.system(cmd)
   print("reset:", out_file)  
   cmd = "cd /home/ams/amscams/pythonv2/; ./detectMeteors.py sf " + out_file + " > tmp.txt"
   os.system(cmd)
   fp = open("/home/ams/amscams/pythonv2/tmp.txt", "r")
   print("<PRE>")
   for line in fp:
      print(line)
   cmd2 = "echo \"" + mv_cmd + "\" >> /home/ams/amscams/pythonv2/tmp.txt"
   os.system(cmd2)
   cmd2 = "echo \"" + cmd + "\" >> /home/ams/amscams/pythonv2/tmp.txt"
   os.system(cmd2)

def examine_min(video_file,json_conf):
   print("<h1>Examine One-Minute Clip</h1>")
   failed_files, meteor_files = get_trims_for_file(video_file)
   stack_file = stack_file_from_video(video_file)
  
   print("<a href=" + video_file + ">")
   print("<img src=" + stack_file + ">")
   print("<br>" + video_file + "</a><br>")
   if len(meteor_files) > 0:
      print("<h2>Meteor Detected</h2>")
      for meteor_file in meteor_files:
         meteor_stack = meteor_file.replace(".mp4", "-stacked.png")
         print("<a href=" + meteor_file + ">")
         print("<img src=" + meteor_stack + "></a>")
         print("<br><a href=webUI.py?cmd=examine&video_file=" + meteor_file + ">Examine</a><br>")

   if len(failed_files) > 0:
      print("<h2>Non Meteor Detections</h2>")
      for fail_file in failed_files:
         fail_stack = fail_file.replace(".mp4", "-stacked.png")
         print("<a href=" + fail_file + ">")
         print("<img src=" + fail_stack + "></a>")
         print("<br><a href=webUI.py?cmd=examine&video_file=" + fail_file + ">Examine</a><br>")
        
   if len(failed_files) == 0 and len(meteor_files) == 0:
      print("<h2>No Detections</h2>")
   #print(failed_files,meteor_files)

def examine(video_file):
   stack_img = video_file.replace(".mp4", "-stacked.png")
   print("<a href=" + video_file + ">")
   print("<p><img src=" + stack_img + " ></a></p>")
   print("<a href=webUI.py?cmd=reject&type=meteor&video_file=" + video_file + " >Reject Meteor Detection</a> - ")
   print("<a href=webUI.py?cmd=reset&type=meteor&video_file=" + video_file + " >Re-run Meteor Detection</a>")
   json_file = video_file.replace(".mp4", ".json")
   #print(json_file)
   json_data= load_json_file(json_file)
   print("<h2>Detection Test Results</h2>")
   for key in json_data:
      print("<HR>", "Object ID: ", key['oid'], "<BR>")
      print("Meteor Y/N: ", key['meteor'], "<BR>")
      print("Test Results <BR>")
      for test in key['test_results']:
         tname, status, desc = test
         print(tname, status, desc, "<BR>")
  
def stack_file_from_video(video_file):
   el = video_file.split("/")
   fn = el[-1]
   base_dir = video_file.replace(fn, "")
   stack_file = base_dir + "images/" + fn 
   stack_file = stack_file.replace(".mp4", "-stacked.png")
   return(stack_file)

def browse_day(day,cams_id,json_conf):
   print ("""
   <head>
      <style> 
         img.meteor {
            border: thin red solid;
            background-color: red;
            margin: 0.3em;
            padding: 0.3em;
         }
         img.fail {
            border: thin silver solid;
            background-color: orange ;
            margin: 0.3em;
            padding: 0.3em;
         }
         img.none {
            border: thin silver solid;
            margin: 0.3em;
            padding: 0.3em;
         }
      </style>
   </head>
   """)
   #failed_files, meteor_files, pending_files = get_day_stats("/mnt/ams2/SD/proc2/" + day + "/", json_conf)
   day_files = get_day_files(day,cams_id,json_conf)
   for base_file in day_files:
      video_file = base_file + ".mp4"
      stack_file = stack_file_from_video(video_file)
      #stack_file = stack_file.replace(day, day + "/images/")
      #print(day_files[base_file])
      if day_files[base_file] == 'meteor':
         htclass = "meteor"
      elif day_files[base_file] == 'failed':
         htclass = "fail"
      else:
         htclass = "none"
      el = base_file.split("/")
      base_js_name = el[-1].replace("_", "")

      link = "<a href=\"webUI.py?cmd=examine_min&video_file=" + video_file + "\">" 
         #+ " onmouseover=\"document.getElementById('" + base_js_name + "').width=705\" " \
         #+ " onmouseout=\"document.getElementById('" + base_js_name + "').width=300\" " +  ">"
      print(link)  
      print("<img id=" + base_js_name + " class='" + htclass + "' width=300 src=" + stack_file + "></img></a>")

def browse_detects(day,type,json_conf):
   failed_files, meteor_files, pending_files = get_day_stats("/mnt/ams2/SD/proc2/" + day + "/", json_conf)
   if type == 'meteor':
      files = meteor_files
   else:
      files = failed_files
   for file in files:
      stack_img = file.replace(".mp4", "-stacked.png")
      print("<a href=webUI.py?cmd=examine&video_file=" + file + ">")
      print("<img src=" + stack_img + " width=400></a>")


def main_page(json_conf):
   print("<h1>AllSky6 Control Panel</h1>")    
   days = sorted(get_proc_days(json_conf),reverse=True)
   for day_dir in days:
      if "meteor" not in day_dir and "daytime" not in day_dir and "json" not in day_dir:
         failed_files, meteor_files, pending_files = get_day_stats(day_dir, json_conf)

         html_row, day = make_day_preview(day_dir,json_conf)
         day_str = day.replace("_", "/")
         print("<h2>" + day_str + "</h2>")
         print("<a href=webUI.py?cmd=browse_detects&type=meteor&day=" + day + ">" \
            + str(len(meteor_files)) + " Meteor Detections</a> - ")
         print("<a href=webUI.py?cmd=browse_detects&type=failed&day=" + day + ">" \
            + str(len(failed_files)) + " Rejected Detections</a> - ")
         print(str(len(pending_files)) + " Files Pending</a> ")
         print("<P>")
         print(html_row)
