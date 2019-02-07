import cv2
import cgi
import time
import glob
import os
from lib.FileIO import get_proc_days, get_day_stats, get_day_files , load_json_file, get_trims_for_file, get_days, save_json_file
from lib.VideoLib import get_masks
from lib.ImageLib import mask_frame 

def get_template(json_conf):
   template = ""
   fpt = open("/home/ams/amscams/pythonv2/templates/as6.html", "r")
   for line in fpt:
      template = template + line
   return(template) 

def make_day_preview(day_dir, json_conf):
   el = day_dir.split("/")
   day = el[-1]
   if day == "":
      day = el[-2]
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

   nav_html,bot_html = nav_links(json_conf,cmd)

   template = get_template(json_conf)
   stf = template.split("{BODY}")
   top = stf[0]
   bottom = stf[1]
   top = top.replace("{TOP}", nav_html)
   print(top)


   if cmd == 'override_detect':
      video_file = form.getvalue('video_file')
      override_detect(video_file,json_conf)
   if cmd == 'video_tools':
      video_tools(json_conf)
   if cmd == 'mask_admin':
      mask_admin(json_conf, form)

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
      examine(video_file)
   if cmd == '' or cmd is None or cmd == 'home':
      main_page(json_conf)   
   if cmd == 'calibration':
      calibration(json_conf)   
   if cmd == 'live_view':
      live_view(json_conf)   
   if cmd == 'meteors':
      meteors(json_conf)   
   if cmd == 'config':
      as6_config(json_conf)   
   if cmd == 'browse_detects':
      day = form.getvalue('day')
      type = form.getvalue('type')
      #type = 'meteor'
      #day = '2019_01_27'
      browse_detects(day,type,json_conf)   

   bottom = bottom.replace("{BOTTOMNAV}", bot_html)      
   print(bottom)
   #cam_num = form.getvalue('cam_num')
   #day = form.getvalue('day')

def calibration(json_conf):
   print("Calibration")

def meteors(json_conf):
   print("Meteors")

def live_view(json_conf):


   print ("<link href='https://fonts.googleapis.com/css?family=Roboto:100,400,300,500,700' rel='stylesheet' type='text/css'>")
   print ("<link href='scale.css' rel='stylesheet' type='text/css'>")
   print ("<div align=\"center\" class=\"fond\" style=\"width: 100%\">")
   print("<h2>Latest View</h2> Updated Once Every 5 Minutes")
   print ("<div>")
   rand=time.time()
   for cam_num in range(1,7):
      cam_key = 'cam' + str(cam_num)
      print(cam_key)
      cam_ip = json_conf['cameras'][cam_key]['ip']
      sd_url = json_conf['cameras'][cam_key]['sd_url']
      hd_url = json_conf['cameras'][cam_key]['hd_url']
      cams_id = json_conf['cameras'][cam_key]['cams_id']

      print ("<div class=\"style_prevu_kit\" style=\"background-color:#cccccc;\"><img src=/mnt/ams2/latest/" + cams_id + ".jpg?" + str(rand) + " width=640 height=360></div>")
   print ("</div>")
   print ("</div>")
   print ("</div>")


def as6_config(json_conf):
   print("AS6 Config")
   print("<UL>")
   print("<LI><a href=webUI.py?cmd=edit_system>Edit System Variables</a></LI>")
   print("<LI><a href=webUI.py?cmd=mask_admin>Mask Admin</a></LI>")
   print("<LI><a href=webUI.py?cmd=manage_alerts>Manage Alerts</a></LI>")
   print("<LI><a href=webUI.py?cmd=api_services>Cloud Sharing</a></LI>")
   print("</UL>")

def get_mask_img(cams_id, json_conf):
   proc_dir = json_conf['site']['proc_dir']
   days = get_days(json_conf)
   day = days[0]
   img_dir = proc_dir + day + "/images/"
   files = glob.glob(img_dir + "*" + cams_id + "*-stacked.png")
   return(files[0])

def save_masks(form,camera,cams_id, json_conf):
   hdm_x = 2.7272
   hdm_y = 1.875

   print("<h1>SAVE MASKS</h1>")
   total_masks = int(form.getvalue('total_masks'))
   mask_data = {}
   hd_mask_data = {}


   for i in range(0,total_masks) :
      field = "x" + str(i)
      x = int(form.getvalue(field))
      field = "y" + str(i)
      y = int(form.getvalue(field))
      field = "w" + str(i)
      w = int(form.getvalue(field))
      field = "h" + str(i)
      h = int(form.getvalue(field))
      mask_str = str(x) + "," + str(y) + "," + str(w) + "," + str(h)
      hd_mask_str = str(int(x*hdm_x)) + "," + str(int(y*hdm_y)) + "," + str(int(w*hdm_x)) + "," + str(int(h*hdm_y))
      mask_key = "mask" + str(i)
      hd_mask_key = "hd_mask" + str(i)
      mask_data[mask_key] = mask_str
      hd_mask_data[hd_mask_key] = hd_mask_str

   # check if new entry exists
   nx = form.getvalue("nx")
   ny = form.getvalue("ny")
   nw = form.getvalue("nw")
   nh = form.getvalue("nh")
   if nx is not None:
      nx,ny,nw,nh = int(nx),int(ny),int(nw),int(nh)
      mask_str = str(nx) + "," + str(ny) + "," + str(nw) + "," + str(nh)
      hd_mask_str = str(int(nx*hdm_x)) + "," + str(int(ny*hdm_y)) + "," + str(int(nw*hdm_x)) + "," + str(int(nh*hdm_y))
      mask_key = "mask" + str(i+1)
      hd_mask_key = "hd_mask" + str(i+1)
      mask_data[mask_key] = mask_str
      hd_mask_data[hd_mask_key] = hd_mask_str

   # save mask file for thumbnailer
   fp = open("/home/ams/amscams/conf/mask-" + cams_id  + ".txt", "w")
   for mask_key in mask_data:
      x,y,w,h = mask_data[mask_key].split(",")
      fp.write(x + " " + y + " " + w + " " +  h + "\n")
   fp.close()

   json_conf['cameras'][camera]['masks'] = mask_data
   json_conf['cameras'][camera]['hd_masks'] = hd_mask_data
   save_json_file('/home/ams/amscams/conf/as6.json', json_conf)


def mask_admin(json_conf,form):
   print("<h1>Mask Admin</h1>")
   subcmd = form.getvalue('subcmd')
   camera = form.getvalue('camera')
   cams_id = form.getvalue('cams_id')
   if subcmd == 'save_mask':
      save_masks(form, camera, cams_id, json_conf)

   if camera is None:
      for camera in json_conf['cameras']:
         cid = json_conf['cameras'][camera]['cams_id']
         print("<a href=webUI.py?cmd=mask_admin&camera=" + camera + "&cams_id=" + cid + ">" + cid + "<BR>")
   else:
      print("Masks for ", cams_id, "<BR>")
      imgf = get_mask_img(cams_id, json_conf) 
      masks = get_masks(cams_id, json_conf)
      img = cv2.imread(imgf, 0)
      tmasks = []
      for mask in masks:
         x,y,w,h = mask.split(",")
         x,y,w,h = int(x), int(y), int(w), int(h)
         cv2.rectangle(img, (x, y), (x + w, y + h), (128, 128, 128), -1)      
         tmasks.append((x,y,w,h))
      cv2.imwrite("/mnt/ams2/tmp.jpg", img)
      print("<img src=/mnt/ams2/tmp.jpg><br>")
      c = 0
      print("<p><form>")
      for mask in tmasks:
         (x,y,w,h) = mask
         print("MASK " + str(c) + ": " )
         print("X:<Input size=3 type=text name=x" + str(c) + " value=" + str(x) + ">")
         print("Y:<Input size=3 type=text name=y" + str(c) + " value=" + str(y) + ">")
         print("W:<Input size=3 type=text name=w" + str(c) + " value=" + str(w) + ">")
         print("H:<Input size=3 type=text name=h" + str(c) + " value=" + str(h) + "><BR>")
         c = c + 1
      print("<P>ADD NEW MASK " ": " )

      print("X:<Input size=3 type=text name=nx value=>")
      print("Y:<Input size=3 type=text name=ny value=>")
      print("W:<Input size=3 type=text name=nw value=>")
      print("H:<Input size=3 type=text name=nh value=>")
      print("<P><input type=hidden name=cmd value=mask_admin>")
      print("<input type=hidden name=subcmd value=save_mask>")
      print("<input type=hidden name=camera value=" + camera + ">")
      print("<input type=hidden name=cams_id value=" + cams_id + ">")
      print("<input type=hidden name=total_masks value="+str(c) +">")
      print("<input type=submit value=\"Save Masks\">")
      print("</form>")



def nav_links(json_conf, cmd):

   nav_top = """
      <div class="collapse navbar-collapse" id="navbar1">
         <ul class="navbar-nav ml-auto">
   """

   nav_item_active = """
      <li class="nav-item active">
         <a class="nav-link" href="{LINK}">{DESC}<span class="sr-only">(current)</span></a> </li>
   """

   nav_item = """
      <li class="nav-item">
         <a class="nav-link" href="{LINK}"> {DESC}</a></li>
   """

   nav_item_drop_down = """
      <li class="nav-item dropdown">
        <a class="nav-link  dropdown-toggle" href="#" data-toggle="dropdown">  Dropdown  </a>
          <ul class="dropdown-menu">
             <li><a class="dropdown-item" href="#"> Menu item 1</a></li>
             <li><a class="dropdown-item" href="#"> Menu item 2 </a></li>
          </ul>
      </li>
   """
   nav_bottom = """
<li class="nav-item">
<a class="btn ml-2 btn-warning" href="http://bootstrap-ecommerce.com">Download</a></li>
    </ul>
  </div>

   """

   # home - meteors - archive - calibration - config
   nav_links = {}
   nav_links['home'] = "Home"
   nav_links['meteors'] = "Meteors"
   nav_links['calibration'] = "Calibration"
   nav_links['live_view'] = "Live View"
   nav_links['video_tools'] = "Video Tools"
   nav_links['config'] = "Config"

  
   nav = ""
   bot_nav = ""
   for link in nav_links:
      if nav != "":
         #nav = nav + " - "
         bot_nav = bot_nav + " - "
      if cmd != link:
         temp = nav_item.replace("{LINK}", "webUI.py?cmd=" + link) 
         temp = temp.replace("{DESC}", nav_links[link]) 
      else:
         temp = nav_item_active.replace("{LINK}", "webUI.py?cmd=" + link) 
         temp = temp.replace("{DESC}", nav_links[link]) 
      nav = nav + temp 
      bot_nav = bot_nav + "<a href=webUI.py?cmd=" + link + ">" + nav_links[link] + "</a>"
   
   return(nav, bot_nav)

def video_tools(json_conf):
   print("video tools")
   print("<li>Join Two Clips</li>")
   print("<li>Trim Clip</li>")
   print("<li>Stack Video</li>")
   print("<li>Make Meteors Tonight Video</li>")
   print("<li>Make Timelapse</li>")

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

def override_detect(video_file,json_conf):
   base = video_file.replace(".mp4", "")
   el = base.split("/")
   base_dir = base.replace(el[-1], "")
   
   if "passed" in base:
      new_dir = base_dir.replace("passed", "failed")
      cmd = "mv " + base + "* " + new_dir
      os.system(cmd)
      print("Files moved to failed dir.")

   if "failed" in base: 
      new_dir = base_dir.replace("failed", "passed")
      cmd = "mv " + base + "* " + new_dir
      os.system(cmd)
      print("Files moved to meteor dir.")

def examine(video_file):
   print_css()
   stack_img = video_file.replace(".mp4", "-stacked.png")
   stack_obj_img = video_file.replace(".mp4", "-stacked-obj.png")
   base_js_name = "123"
   htclass='norm'
   print("<a href=" + video_file + ">")
   #print("<p><img src=" + stack_img + " ></a></p>")
   html_out = ""
   html_out = html_out + "<a href=\"" + video_file + "\"" \
         + " onmouseover=\"document.getElementById('" + base_js_name + "').src='" + stack_obj_img \
         + "'\" onmouseout=\"document.getElementById('" + base_js_name + "').src='" + stack_img+ "'\">"
   html_out = html_out + "<img class=\"" + htclass + "\" id=\"" + base_js_name + "\" src='" + stack_img+ "'></a><br>\n"
   print("<figure>")
   print(html_out)
   if "passed" in video_file:
      print("<a href=webUI.py?cmd=override_detect&video_file=" + video_file + " >Reject Meteor</a> - ")
   else:
      print("<a href=webUI.py?cmd=override_detect&video_file=" + video_file + " >Tag as Meteor</a> - ")

   print("<a href=webUI.py?cmd=reset&type=meteor&video_file=" + video_file + " >Re-run Detection</a>")

   print("</figure>")
   print("<p style='clear: both'></p>")
   json_file = video_file.replace(".mp4", ".json")

   json_data= load_json_file(json_file)
   print("<h2>Detection Test Results</h2>")   
   print("{:d} Object Detections <BR>".format(len(json_data)))

   meteor_output = ""
   non_meteor_output = ""
   for key in json_data:
      if key['meteor'] == 1:
         meteor_output = meteor_output + "<HR>Object ID: {:d}<BR>".format(key['oid'])
         meteor_output = meteor_output + "Meteor Y/N:    {:d}<BR>".format(key['meteor'])
         meteor_output = meteor_output + "Meteor Object <BR>"
         for test in key['test_results']:
            tname, status, desc = test
            meteor_output = meteor_output + "{:s} {:f} {:s}<BR>".format(tname,status,str(desc))
         for hist in key['history']:
            meteor_output = meteor_output + "{:s} <BR>".format(str(hist))
      else:
         non_meteor_output = non_meteor_output + "<HR>Object ID: {:d}<BR>".format(key['oid'])
         non_meteor_output = non_meteor_output + "Meteor Y/N:    {:d}<BR>".format(key['meteor'])
         non_meteor_output = non_meteor_output + "Meteor Object <BR>"
         for test in key['test_results']:
            tname, status, desc = test
            non_meteor_output = non_meteor_output + "{:s} {:f} {:s}<BR>".format(tname,status,str(desc))
         for hist in key['history']:
            non_meteor_output = non_meteor_output + "{:s} <BR>".format(str(hist))
   print(meteor_output)
   print(non_meteor_output)
  
def stack_file_from_video(video_file):
   el = video_file.split("/")
   fn = el[-1]
   base_dir = video_file.replace(fn, "")
   stack_file = base_dir + "images/" + fn 
   stack_file = stack_file.replace(".mp4", "-stacked.png")
   return(stack_file)


def print_css():
   print ("""
   <head>
      <style> 
         figure {
            text-align: center;
            font-size: smaller;
            float: left;
            border: thin silver solid;
            margin: 0.1em;
            padding: 0.1em;
         }

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
            width: 300px;
            margin: 0.2em;
            padding: 0.2em;
         }
         img.norm {
            border: thin silver solid;
            margin: 0.2em;
            padding: 0.2em;
         }
      </style>
   </head>
   """)


def browse_day(day,cams_id,json_conf):


   print_css()

   day_files = get_day_files(day,cams_id,json_conf)
   for base_file in sorted(day_files,reverse=True):
      video_file = base_file + ".mp4"
      stack_file = stack_file_from_video(video_file)
      stack_file_tn = stack_file.replace(".png", "-tn.png")
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
      print("<img id=" + base_js_name + " class='" + htclass + "' width=300 src=" + stack_file_tn + "></img></a>")

def browse_detects(day,type,json_conf):
   print_css()
   proc_dir = json_conf['site']['proc_dir']
   failed_files, meteor_files, pending_files,min_files = get_day_stats(proc_dir + day + "/", json_conf)
   if type == 'meteor':
      files = meteor_files
      show_day = day.replace("_", "/")
      print("<h1>Meteor Detections on {:s}</h1>".format(show_day))
      print("{:d} Meteors Detected<br>".format(len(files)))
   else:
      files = failed_files
   for file in sorted(files, reverse=True):
      stack_img = file.replace(".mp4", "-stacked.png")
      stack_obj_img = file.replace(".mp4", "-stacked-obj.png")
      el = stack_img.split("/")
      short = el[-1].replace("-stacked.png", "")
      xxx = short.split("-trim")
      short_name = xxx[0]
    
      #print("<a href=webUI.py?cmd=examine&video_file=" + file + ">")
      #print("<img src=" + stack_img + " width=400></a>{:s}".format(short_name))
      base_js_name=short_name.replace("_", "")
      htclass = "none"

      html_out = ""
      html_out = html_out + "<a href=\"webUI.py?cmd=examine&video_file=" + file + "\"" \
         + " onmouseover=\"document.getElementById('" + base_js_name + "').src='" + stack_obj_img \
         + "'\" onmouseout=\"document.getElementById('" + base_js_name + "').src='" + stack_img+ "'\">"
      html_out = html_out + "<img class=\"" + htclass + "\" id=\"" + base_js_name + "\" width='200' src='" + stack_img+ "'></a>\n"

      #print("<figure><img id=" + base_js_name + " class='" + htclass + "' width=300 src=" + stack_img + "></img></a><figcaption>" + short_name + "</figcaption></figure>")
      print("<figure>" + html_out + "<figcaption>" + short_name + "</figcaption></figure>")

   print("<div style=\"clear: both\"></div>")

def main_page(json_conf):

   print("<h1>AllSky6 Control Panel</h1>")    
   days = sorted(get_proc_days(json_conf),reverse=True)

   json_file = json_conf['site']['proc_dir'] + "json/" + "main-index.json"
   stats_data = load_json_file(json_file)

   for day in stats_data: 
      day_str = day
      day_dir = json_conf['site']['proc_dir'] + day + "/" 
      if "meteor" not in day_dir and "daytime" not in day_dir and "json" not in day_dir:
         failed_files = stats_data[day]['failed_files']
         meteor_files = stats_data[day]['meteor_files']
         pending_files = stats_data[day]['pending_files']

         html_row, day_x = make_day_preview(day_dir,json_conf)
         day_str = day.replace("_", "/")
         print("<h2>" + day_str + "</h2>")
         print("<a href=webUI.py?cmd=browse_detects&type=meteor&day=" + day + ">" \
            + str(meteor_files) + " Meteor Detections</a> - ")
         print("<a href=webUI.py?cmd=browse_detects&type=failed&day=" + day + ">" \
            + str(failed_files) + " Rejected Detections</a> - ")
         print(str(pending_files) + " Files Pending</a> ")
         print("<P>")
         print(html_row)

