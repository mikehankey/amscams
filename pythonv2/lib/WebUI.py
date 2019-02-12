import cv2
import cgi
import time
import glob
import os
from lib.FileIO import get_proc_days, get_day_stats, get_day_files , load_json_file, get_trims_for_file, get_days, save_json_file, cfe
from lib.VideoLib import get_masks, convert_filename_to_date_cam
from lib.ImageLib import mask_frame 
from lib.CalibLib import radec_to_azel

def get_template(json_conf):
   template = ""
   fpt = open("/home/ams/amscams/pythonv2/templates/as6.html", "r")
   for line in fpt:
      template = template + line
   return(template) 

def make_day_preview(day_dir, stats_data, json_conf):
   el = day_dir.split("/")
   day = el[-1]
   if day == "":
      day = el[-2]
   day_str = day
   html_out = ""
   for cam in json_conf['cameras']:
      cams_id = json_conf['cameras'][cam]['cams_id']
      min_total = stats_data[cams_id] 
      obj_stack = day_dir + "/" + "images/"+ cams_id + "-night-stack.png"
      meteor_stack = day_dir + "/" + "images/" + cams_id + "-meteors-stack.png"
      if cfe(obj_stack) == 0:
         obj_stack = "/mnt/ams2/blank.jpg"
      if cfe(meteor_stack) == 0:
         meteor_stack = "/mnt/ams2/blank.jpg"

      day=day.replace("_","")
      html_out = html_out + "<figure><a href=\"webUI.py?cmd=browse_day&day=" + day_str + "&cams_id=" + cams_id \
         + "\" onmouseover=\"document.getElementById(" + day + cams_id + ").src='" + meteor_stack \
         + "'\" onmouseout=\"document.getElementById(" + day + cams_id + ").src='" + obj_stack + "'\">"
      html_out = html_out + "<img id=\"" + day+ cams_id + "\" width='200' height='163' src='" + obj_stack + "'></a><br><figcaption>" + str(min_total) + " Minutes</figcaption></figure>"
   return(html_out, day_str)

def parse_jsid(jsid):
   #print("JSID:", jsid)
   year = jsid[0:4]
   month = jsid[4:6]
   day = jsid[6:8]
   hour = jsid[8:10]
   min = jsid[10:12]
   sec = jsid[12:14]
   micro_sec = jsid[14:17]
   cam = jsid[17:23]
   trim = jsid[24:]
   trim = trim.replace(".json", "")
   video_file = "/mnt/ams2/meteors/" + str(year) + "_" + str(month) + "_" + str(day) + "/"  + year + "_" + month + "_" + day + "_" + hour + "_" + min + "_" + sec + "_" + micro_sec + "_" + str(cam) + "-" + trim + ".mp4"
   #print(video_file)
   #print(year,month,day,hour,min,sec,micro_sec,cam,trim)
   return(video_file)

def controller(json_conf):

   form = cgi.FieldStorage()
   cmd = form.getvalue('cmd')
   #cmd = "play_vid"
   if cmd == 'play_vid':
      jsid = form.getvalue('jsid')
      video_file = parse_jsid(jsid)
      print("Location: " + video_file + "\n\n")
      exit()

   print("Content-type: text/html\n\n")

   # do json functions up here and bypass the exta html
   if cmd == 'override_detect':
      video_file = form.getvalue('video_file')
      jsid = form.getvalue('jsid')
      override_detect(video_file,jsid,json_conf)
      exit()



   print_css()
   jq = do_jquery()
   

   nav_html,bot_html = nav_links(json_conf,cmd)

   template = get_template(json_conf)
   stf = template.split("{BODY}")
   top = stf[0]
   bottom = stf[1]
   top = top.replace("{TOP}", nav_html)

   obs_name = json_conf['site']['obs_name']

   top = top.replace("{OBSNAME}", obs_name)
   top = top.replace("{JQ}", jq)

   print(top)


      

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
      jsid = form.getvalue('jsid')
      if jsid is not None:
         video_file = parse_jsid(jsid)

      examine(video_file)
   if cmd == '' or cmd is None or cmd == 'home':
      main_page(json_conf)   
   if cmd == 'examine_cal':
      examine_cal(json_conf,form)   
   if cmd == 'calibration':
      calibration(json_conf,form)   
   if cmd == 'live_view':
      live_view(json_conf)   
   if cmd == 'meteors':
      meteors(json_conf, form)   
   if cmd == 'config':
      as6_config(json_conf)   
   if cmd == 'browse_detects':
      day = form.getvalue('day')
      type = form.getvalue('type')
      #type = 'meteor'
      #day = '2019_01_27'
      browse_detects(day,type,json_conf)   

   #bottom = bottom.replace("{JQ}", jq)      
   bottom = bottom.replace("{BOTTOMNAV}", bot_html)      
   print(bottom)
   #cam_num = form.getvalue('cam_num')
   #day = form.getvalue('day')

def get_cal_params(json_conf,cams_id):
   if cams_id is None:
      files = glob.glob("/mnt/ams2/cal/solved/*.json")
   else:
      files = glob.glob("/mnt/ams2/cal/solved/*" + cams_id + "*.json")
   return(files)

def examine_cal(json_conf,form):

   print("""
      <script>
      function swap_pic(img_id,img_src) {
         document.getElementById(img_id).src=img_src

      }
      </script>

      """)
   print("<p>Exmaine calibration</p>")
   cal_param = form.getvalue('cal_param')
   cal_file = cal_param.replace("-calparams.json", ".jpg") 
   orig_cal_file = cal_param.replace("-calparams.json", "-orig.jpg") 
   rect_file = cal_param.replace("-calparams.json", "-rect.jpg") 
   grid_file = cal_param.replace("-calparams.json", "-grid.png") 
   cal_fit_file = cal_param.replace("-calparams.json", "-calfit.jpg") 

   print("<figure><img id=\"cal_img\" width=1200 src=" + grid_file + ">")
   print("<figcaption>")
   #print("<a href=# onclick=\"swap_pic('cal_img', '" + orig_cal_file + "')\">Orig</a> -" )
   print("<a href=# onclick=\"swap_pic('cal_img', '" + cal_file + "')\">Src</a> -" )
   #print("<a href=# onclick=\"swap_pic('cal_img', '" + cal_file + "')\">Stars</a> -" )
   print("<a href=# onclick=\"swap_pic('cal_img', '" + grid_file + "')\">Grid</a> -" )
   print("<a href=# onclick=\"swap_pic('cal_img', '" + cal_fit_file + "')\">Fit</a> ")
   print("</figcaption></figure>" )
   print("<div style=\"clear: both\"></div>")
   json_data = load_json_file(cal_param )

   #orig_cal_file = cal_p


def calibration(json_conf,form):
   cams_id = form.getvalue('cams_id')
   print("Calibration")
   cal_params = get_cal_params(json_conf, cams_id)

   print("""
      <div style="float:right">
      <form>
       <select name=cam_id onchange="javascript:goto(this.options[selectedIndex].value)">
        <option value=>Filter By Cam</option>
        <option value=010001>010001</option>
        <option value=010002>010002</option>
        <option value=010003>010003</option>
        <option value=010004>010004</option>
        <option value=010005>010005</option>
        <option value=010006>010006</option>
        </select>
      </form>
      </div>
      """)



   stab,sr,sc,et,er,ec = div_table_vars()
   print(stab)

   print(sr+sc+"Date"+ec+sc+"Camera" + ec + sc + "Center RA/DEC" + ec + sc + "Center AZ/EL" + ec + sc +"Pixel Scale" + ec + sc + "Position Angle" + ec + sc + "Residual" + ec + er)
   for cal_param in sorted(cal_params,reverse=True):
      hd_datetime, hd_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(cal_param)
      json_data = load_json_file(cal_param )

      az,el = radec_to_azel(json_data['ra_center'],json_data['dec_center'], hd_datetime,json_conf)


      print(sr + sc + "<a href=webUI.py?cmd=examine_cal&cal_param=" + cal_param + ">" + hd_date + "</a>" + ec + sc + hd_cam + ec + sc + str(json_data['ra_center'])[0:6] + "/" + str(json_data['dec_center'])[0:5] + ec + sc + str(az)[0:5] + "/" + str(el)[0:5] + ec + sc + str(json_data['pixscale'])[0:5] + ec + sc + str(json_data['position_angle'])[0:5] + ec + sc + str(json_data['x_fun'])[0:4] + "," + str(json_data['y_fun'])[0:4] + ec + er)
   print(et)

def get_meteor_dirs(meteor_dir):
   meteor_dirs = []
   files = glob.glob("/mnt/ams2/meteors/*")
   for file in files:
      if "trash" not in file:
         if cfe(file,1) == 1:
            meteor_dirs.append(file)
   return(meteor_dirs)

def get_meteors(meteor_dir,meteors):
   glob_dir = meteor_dir + "*-trim*.mp4"
   files = glob.glob(meteor_dir + "/*-trim*.json")
   for file in files:
      meteors.append(file)
   return(meteors)
  

def meteors(json_conf,form): 
   limit_day = form.getvalue('limit_day')
   htclass = "none"
   print("<h1>Meteors</h1>")
   meteors = []
   meteor_base_dir ="/mnt/ams2/meteors/"
   meteor_dirs = sorted(get_meteor_dirs(meteor_base_dir), reverse=True)


   for meteor_dir in meteor_dirs:
      el = meteor_dir.split("/")
      this_date = el[-1]
      if limit_day is None: 
         meteors = get_meteors(meteor_dir, meteors)
      elif limit_day == this_date:
         meteors = get_meteors(meteor_dir, meteors)
         print("<p>{:d} meteors captured on {:s}.</p>".format(len(meteors), str(this_date)))
   if limit_day is None:
      print("<p>{:d} meteors captured since inception.</p>".format(len(meteors)))

   span = "<span id=\"{ID}\" class=\"context-menu-one btn btn-neutral\">"  
   end_span = "</span>"

   for meteor in sorted(meteors,reverse=True):
      stack_file_tn = meteor.replace('.json', '-stacked-tn.png')
      video_file = meteor.replace('.json', '.mp4')
      stack_obj_img = video_file.replace(".mp4", "-stacked-obj-tn.png")

      el = meteor.split("/")
      temp = el[-1].replace(".mp4", "")
      xxx = temp.split("-trim")
      desc = xxx[0] 
      base_js_name = el[-1].replace("_", "")
      base_js_name = base_js_name.replace(".json", "")
      base_js_name_img = "img_" + base_js_name
      fig_id = "fig_" + base_js_name
      


      html_out = ""
      this_span = span.replace("{ID}", base_js_name)
      html_out = html_out + "<figure id=\"" + fig_id + "\">" + this_span + "<a href=\"webUI.py?cmd=examine&video_file=" + video_file + "\"" \
         + " onmouseover=\"document.getElementById('" + base_js_name_img + "').src='" + stack_obj_img \
         + "'\" onmouseout=\"document.getElementById('" + base_js_name_img + "').src='" + stack_file_tn+ "'\">"
  
      html_out = html_out + "<img class=\"" + htclass + "\" id=\"" + base_js_name_img + "\" src='" + stack_file_tn+ "'></a>" + end_span + "<figcaption>" + desc + "</figcaption></figure>\n"

      print(html_out)
   print("<div style='clear: both'></div>")



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

def override_detect(video_file,jsid, json_conf):

   if jsid is not None:
      video_file = parse_jsid(jsid)

   base = video_file.replace(".mp4", "")
   el = base.split("/")
   base_dir = base.replace(el[-1], "")

   if "meteors" in base:
      new_dir = "/mnt/ams2/trash/"
      json_file = video_file.replace(".mp4", ".json")
      json_data = load_json_file(json_file)
      hd_trim = json_data['hd_trim']
      sd_video_file = json_data['sd_video_file']
      el = sd_video_file.split("/")
      sd_dir  = sd_video_file.replace(el[-1], "") 
      sd_fail = sd_dir.replace("passed","failed")
      sd_wild = sd_video_file.replace(".mp4", "*")
   
      cmd = "mv "  + sd_wild + " " + sd_fail   
      os.system(cmd)

      if hd_trim is not None:
         el = hd_trim.split("-trim-")
         ttt = el[0]
         xxx = ttt.split("/")
         hd_wild = base_dir + "/" + xxx[-1] + "*"
         cmd2 = "mv " + hd_wild + " /mnt/ams2/trash/"
         os.system(cmd2)
      else:
         cmd2 = ""

      cmd3 = "mv " + base + "* " + new_dir
      #print(cmd, "<BR>")
      os.system(cmd3)
      print("Detection moved to /mnt/ams2/trash (if you made a mistake the files can be retrieved from the trash folder.)<BR>" ) 
      print(cmd, "<BR>")
      print(cmd2, "<BR>")
      print(cmd3, "<BR>")
      
   
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
   print("<h1>Examine Meteor</h1>")
   el = video_file.split("/")
   fn = el[-1]
   meteor_dir = video_file.replace(fn, "")
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
   if "meteors" in video_file:
      print("<a href=webUI.py?cmd=override_detect&video_file=" + video_file + " >Reject Meteor</a>  ")
   else:
      print("<a href=webUI.py?cmd=override_detect&video_file=" + video_file + " >Tag as Meteor</a>  ")

   #print("<a href=webUI.py?cmd=reset&type=meteor&video_file=" + video_file + " >Re-run Detection</a>")

   print("</figure>")
   print("<p style='clear: both'></p>")
   json_file = video_file.replace(".mp4", ".json")


   json_data= load_json_file(json_file)
   meteor_info = meteor_info_table(json_data)
   print(meteor_info)
   # HD PART OF PAGE
   # SKIP OF NO HD_TRIM EXISTS

   hd_trim = json_data['hd_trim']
   hd_crop = json_data['hd_crop_file']
   if hd_trim is not None:
      print("<h2>HD Files</h2>")
      if "meteors" not in hd_trim:
         el = hd_trim.split("/")
         hd_trim = meteor_dir + el[-1]
         el = hd_crop.split("/")
         hd_crop= meteor_dir + el[-1]

      hd_trim_stacked = hd_trim.replace(".mp4", "-stacked.png")
      hd_crop_stacked = hd_crop.replace(".mp4", "-stacked.png")
      hd_trim_stacked_tn = hd_trim.replace(".mp4", "-stacked-tn.png")
      hd_crop_stacked_tn = hd_crop.replace(".mp4", "-stacked-tn.png")
      print("<figure><a href=" + hd_trim + "><img width=300 src=" + hd_trim_stacked_tn + "></a><figcaption>HD Video</figcaption></figure>")
      print("<figure><a href=" + hd_crop+ "><img src=" + hd_crop_stacked + "></a><figcaption>HD Crop Video</figcaption></figure><div style='clear: both'></div>")
      print("<a href=" + hd_trim_stacked + ">HD Stacked Image</a> - ")
      print("<a href=" + hd_crop_stacked + ">HD Cropped Image</a><br>")
   else:
      print("<p>No HD video for this meteor.</p>")   

   print("<h2>SD Objects</h2>")   
   print("<a href=javascript:show_hide_div('object_details')>")
   print("{:d} Object Detections</a> <BR>".format(len(json_data['sd_objects'])))

   meteor_output = "<div style='display:none;' id='object_details'" + ">Meteor Tests<BR>"
   non_meteor_output = ""
   stab,sr,sc,et,er,ec = div_table_vars()
   for key in json_data['sd_objects']:
      if key['meteor'] == 1:
         meteor_output = meteor_output + "<HR>Object ID: {:d}<BR>".format(key['oid'])
         meteor_output = meteor_output + "Meteor Y/N:    {:d}<BR>".format(key['meteor'])
         meteor_output = meteor_output + "\n\n<a href=javascript:show_hide_div('obj" + str(key['oid']) + "')>Show/Hide Details</a>"
         meteor_output = meteor_output + "<div style='display:none;' id=obj" + str(key['oid']) + ">Meteor Object <BR>"
         meteor_output = meteor_output + stab 
         for test in key['test_results']:
            tname, status, desc = test
            if tname == 'AVL':
               if len(desc) > 25:
                  temp= desc[0:25] + "..."
               meteor_output = meteor_output + sr + sc + tname + ec + sc + str(status) + ec + sc + str(temp) + ec + er
            else:
               meteor_output = meteor_output + sr + sc + tname + ec + sc + str(status) + ec + sc + str(desc) + ec + er
         meteor_output = meteor_output + et
         meteor_output = meteor_output + "\n<h2>Frame History</h2>\n"
         meteor_output = meteor_output + stab 
         meteor_output = meteor_output + sr + sc + "FN" + ec + sc + "x" + ec + sc + "y" + ec + sc + "w" + ec + sc + "h" + ec + sc + "bx" + ec + sc + "by" + ec + er
         for hist in key['history']:
            fn, x,y,w,h,bx,by = hist
            meteor_output = meteor_output + sr + sc + str(fn) + ec + sc + str(x) + ec + sc + str(y) + ec + sc + str(w) + ec + sc + str(h) + ec + sc + str(bx) + ec + sc + str(by) + ec + er
            #meteor_output = meteor_output + "{:s} <BR>".format(str(hist))
         meteor_output = meteor_output + et + "</div>\n\n"
      else:
         non_meteor_output = non_meteor_output + "<HR>Object ID: {:d}<BR>".format(key['oid'])
         non_meteor_output = non_meteor_output + "Meteor Y/N:    {:d}<BR>".format(key['meteor'])
         non_meteor_output = non_meteor_output + "<a href=javascript:show_hide_div('obj" + str(key['oid']) + "')>Show/Hide Details</a>"
         non_meteor_output = non_meteor_output + "<div style='display:none;' id=obj" + str(key['oid']) + "> NON Meteor Object <BR>"
         for test in key['test_results']:
            tname, status, desc = test
            non_meteor_output = non_meteor_output + "{:s} {:f} {:s}<BR>".format(tname,status,str(desc))
         for hist in key['history']:
            non_meteor_output = non_meteor_output + "{:s} <BR>".format(str(hist)) 
         non_meteor_output = non_meteor_output + "</div>"
   print(meteor_output)
   print(non_meteor_output)
   print("</div>")
   print("<h2>HD Objects</h2>")

def meteor_info_table(json_data):
   print("<h2>Meteor Info</h2>")
   start_time = "tesxt"
   stab,sr,sc,et,er,ec = div_table_vars()
   mi = stab 

   mi = mi + sr + sc + "Frame" + ec + sc + "Time" + ec + sc +"SD X,Y " + ec + sc + "SD RA,DEC" + ec + sc + "SD RA,DEC" + ec + sc + "SD AZ,EL" + ec 
   mi = mi + sc + "HD X,Y" + ec  + sc + "HD RA,DEC" + ec  + sc + "HD AZ,EL" + ec  + er

   mi = mi + sr + sc + "Start " + ec + sc + "Time" + ec + sc + "SD X,Y " + ec + sc + "SD RA,DEC" + ec + sc + "SD RA,DEC" + ec + sc + "SD AZ,EL" + ec 
   mi = mi + sc + "HD X,Y" + ec  + sc + "HD RA,DEC" + ec  + sc + "HD AZ,EL" + ec  + er
   mi = mi + sr + sc + "End" + ec + sc + "Time" + ec + sc + "SD X,Y " + ec + sc + "SD RA,DEC" + ec + sc + "SD RA,DEC" + ec + sc + "SD AZ,EL" + ec 
   mi = mi + sc + "HD X,Y" + ec  + sc + "HD RA,DEC" + ec  + sc + "HD AZ,EL" + ec  + er


   mi = mi + et 
   return(mi) 

def div_table_vars():
   start_table = """
      <div class="divTable" style="border: 1px solid #000;" >
      <div class="divTableBody">
   """
   start_row = """
      <div class="divTableRow">
   """
   start_cell = """
      <div class="divTableCell">
   """
   end_table = "</div></div>"
   end_row = "</div>"
   end_cell= "</div>"
   return(start_table, start_row, start_cell, end_table, end_row, end_cell)
  
def stack_file_from_video(video_file):
   el = video_file.split("/")
   fn = el[-1]
   base_dir = video_file.replace(fn, "")
   stack_file = base_dir + "images/" + fn 
   stack_file = stack_file.replace(".mp4", "-stacked.png")
   return(stack_file)


def do_jquery():
   jq = """
<script src="https://cdnjs.cloudflare.com/ajax/libs/jquery/3.3.1/jquery.min.js"></script>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/jquery-contextmenu/2.7.1/jquery.contextMenu.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/jquery-contextmenu/2.7.1/jquery.contextMenu.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/jquery-contextmenu/2.7.1/jquery.ui.position.js"></script>
<script>
    $(function() {
        $.contextMenu({
            selector: '.context-menu-one',
            callback: function(key, options) {
                id = options.$trigger.attr("id");
                var m = "clicked: " + key + id;
                if (key == 'reject') {
                   new_id = 'fig_' + id
                   $('#' + new_id).remove();
                   ajax_url = "webUI.py?cmd=override_detect&jsid=" + id
                   $.get(ajax_url, function(data) {
                      $(".result").html(data);
                   });
                }
                
                if (key == 'examine') {
                   window.location.href='webUI.py?cmd=examine&jsid=' + id
                   //alert("EXAMINE:")
                }
                if (key == 'play') {
                   //window.location.href='webUI.py?cmd=play_vid&jsid=' + id
                      $('#ex1').modal();
                      var year = id.substring(0,4);
                      var mon = id.substring(4,6);
                      var day = id.substring(6,8);
                      var hour = id.substring(8,10);
                      var min = id.substring(10,12);
                      var sec = id.substring(12,14);
                      var msec = id.substring(14,17);
                      var cam = id.substring(17,23);
                      var trim = id.substring(24,id.length);
                      var src_url = "/mnt/ams2/meteors/" + year + "_" + mon + "_" + day + "/" + year + "_" + mon + "_" + day + "_" + hour + "_" + min + "_" + sec + "_" + msec + "_" + cam + "-" + trim + ".mp4"
                      $('#v1').attr("src", src_url);

                }
                //window.console && console.log(m) || alert(m);
            },
            items: {
                "examine": {name: "Examine"},
                "play": {name: "Play Video"},
                "reject": {name: "Reject Meteor"},
                "confirm": {name: "Confirm Meteor"},
                "satellite": {name: "Mark as Satellite"},
                "quit": {name: "Quit", icon: function(){
                    return 'context-menu-icon context-menu-icon-quit';
                }}
            }
        });

        $('.context-menu-one').on('click', function(e){
            console.log('clicked', this);


        })
    });
</script>


   """
   return(jq)

def print_css():
   print ("""
   <head>

      <script>
         function goto(cams_id) {
            url_str = "webUI.py?cmd=calibration&cams_id=" + cams_id
            window.location.href=url_str
         }
      </script>

      <style> 

.divTable{
	display: table;
}
.divTableRow {
	display: table-row;
}
.divTableHeading {
	background-color: #EEE;
	display: table-header-group;
}
.divTableCell, .divTableHead {
	border: 1px solid #999999;
	display: table-cell;
	padding: 3px 10px;
        vertical-align: top;
}
.divTableCellDetect {
	border: 1px solid #ff0000;
	display: table-cell;
	padding: 3px 10px;
        vertical-align: top;
}
.divTableHeading {
	background-color: #EEE;
	display: table-header-group;
	font-weight: bold;
}
.divTableFoot {
	background-color: #EEE;
	display: table-footer-group;
	font-weight: bold;
}
.divTableBody {
	display: table-row-group;
}



         figure {
            text-align: center;
            font-size: smaller;
            float: left;
            padding: 0.2em;
            margin: 0.2em;
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
            width: 300px;
            margin: 0.1em;
            padding: 0.1em;
            border: thin silver solid;
         }
         img.norm {
            border: thin silver solid;
            margin: 0.2em;
            padding: 0.2em;
         }
      </style>
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
      if "meteor" not in day_dir and "daytime" not in day_dir and "json" not in day_dir and "trash" not in day_dir:
         failed_files = stats_data[day]['failed_files']
         meteor_files = stats_data[day]['meteor_files']
         pending_files = stats_data[day]['pending_files']

         html_row, day_x = make_day_preview(day_dir,stats_data[day], json_conf)
         day_str = day.replace("_", "/")
         print("<h2>" + day_str + "</h2>")
         print("<a href=webUI.py?cmd=meteors&limit_day=" + day + ">" \
            + str(meteor_files) + " Meteor Detections</a> - ")
         print("<a href=webUI.py?cmd=browse_detects&type=failed&day=" + day + ">" \
            + str(failed_files) + " Rejected Detections</a> - ")
         print(str(pending_files) + " Files Pending</a> ")
         print("<P>")
         print(html_row)
         print("</P><div style='clear: both'></div>")

