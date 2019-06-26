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
from lib.PwdProtect import   login_page, check_pwd_ajax
from lib.Pagination import get_pagination
from lib.PrintUtils import get_meteor_date, get_date_from_file
from lib.FileIO import get_proc_days, get_day_stats, get_day_files , load_json_file, get_trims_for_file, get_days, save_json_file, cfe, save_meteor
from lib.VideoLib import get_masks, convert_filename_to_date_cam, ffmpeg_trim , load_video_frames
from lib.DetectLib import check_for_motion2 
from lib.SolutionsLib import solutions , sol_detail
from lib.MeteorTests import test_objects
from lib.ImageLib import mask_frame , draw_stack, stack_frames
from lib.CalibLib import radec_to_azel
from lib.WebCalib import calibrate_pic,make_plate_from_points, solve_field, check_solve_status, free_cal, show_cat_stars, choose_file, upscale_2HD, fit_field, delete_cal, add_stars_to_fit_pool, save_add_stars_to_fit_pool, reduce_meteor, reduce_meteor_ajax, find_stars_ajax, man_reduce, pin_point, get_manual_points, del_manual_points, sat_cap, HMS2deg, custom_fit, del_frame, clone_cal, reduce_meteor_new , update_red_info_ajax, update_hd_cal_ajax, add_frame_ajax, update_frame_ajax
from lib.UtilLib import calc_radiant
 

NUMBER_OF_METEOR_PER_PAGE = 60
NUMBER_OF_DAYS_PER_PAGE = 7
 

def run_detect(json_conf, form):
   temp_sd_video_file = form.getvalue("temp_sd_video_file")
   stack_file = temp_sd_video_file.replace(".mp4", "-stacked.png")
   obj_stack_file = temp_sd_video_file.replace(".mp4", "-stacked-obj.png")
   hd_datetime, hd_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(temp_sd_video_file)
   frames = load_video_frames(temp_sd_video_file, json_conf)
   objects = check_for_motion2(frames, temp_sd_video_file,hd_cam, json_conf,0)

   print("run:", temp_sd_video_file, len(frames))
   print("<span style=\"color: white>\">")

   objects,meteor_found = test_objects(objects,frames)
   stack_file,stack_img = stack_frames(frames, temp_sd_video_file)
   draw_stack(objects,stack_img,stack_file)
   print("<br><img src=" + obj_stack_file + ">")
   for object in objects:
      print("<HR>")
      for key in object:
         if key == 'test_results':
            for test in object['test_results']:
               (test_name,test_rest, test_desc) = test
               print(test_name,test_rest, test_desc,"<BR>")
         else:
            print(key, object[key], "<BR>")
   if meteor_found == 1:
      wild = temp_sd_video_file.replace(".mp4", ".*")
      el = temp_sd_video_file.split("/")
      fn = el[-1]
      day_dir = fn[0:10]
      proc_dir = json_conf['site']['proc_dir']
      cmd = "cp " + wild + " " + proc_dir + day_dir + "/passed/" 
      os.system(cmd)
      new_video_file = proc_dir + day_dir + "/passed/" + fn
      print("NEW VIDEO FILE:", new_video_file)
      save_meteor(temp_sd_video_file,objects,json_conf)

      cmd2 = "cd /home/ams/amscams/pythonv2/; ./detectMeteors.py doHD " + proc_dir + day_dir + "/passed/" + fn
      print("METEOR WAS FOUND! Copied clip to passed dir for final processing. It should appear in meteor archive within a minute. <br>",cmd)
      print(cmd2)
   else:
      print("Meteor was not found by detection code. Override test results here... (todo...)")
   print("</span>")

def manual_detect(json_conf, form):
   sd_video_file = form.getvalue('sd_video_file')
   el = sd_video_file.split("/")
   fn = el[-1]
   temp_sd_video_file = "/mnt/ams2/trash/" + fn
   cmd  = "cp " + sd_video_file + " " + temp_sd_video_file
   os.system(cmd)

   subcmd = form.getvalue('subcmd')
   stack_num = form.getvalue('stack_num')
   print("Manual detect<BR>")
   cmd = "cd /home/ams/amscams/pythonv2/; ./stackVideo.py 10sec " + sd_video_file
   print(cmd)
   os.system(cmd)
   if subcmd is None: 
      for i in range(0,6):

         rand = "?rand=" + str(randint(0,10000))
         stack_file = "/mnt/ams2/trash/stack" + str(i) + ".png" + rand
         print("<a href=webUI.py?cmd=manual_detect&sd_video_file=" + sd_video_file + "&subcmd=pick_stack&stack_num=" + str(i) + "><img src=" + stack_file + ">")


   if subcmd == 'pick_stack' or subcmd == 'retrim':
      if subcmd == 'pick_stack':
         print('trim')      
         trim_start_sec = (int(stack_num) * 10 * 25) / 25
         dur_sec = 10
         out_file_suffix = "-trim" + str(int(stack_num) * 10 * 25) 
      else:
         trim_start_sec = form.getvalue("trim_start_sec")
         dur_sec = form.getvalue("dur_sec")
         stack_num = int(float(trim_start_sec) * 25)
         out_file_suffix = "-trim" + str(int(stack_num) ) 


      ffmpeg_trim(temp_sd_video_file, trim_start_sec, dur_sec, out_file_suffix)
      #print("trimming clip:", temp_sd_video_file, trim_start_sec, dur_sec, out_file_suffix)
      print("<BR>")
      show_file = temp_sd_video_file.replace(".mp4", out_file_suffix + ".mp4")
      rand = "?rand=" + str(randint(0,10000))
      print(" <video autoplay id=\"v1\" loop controls src=\"" + show_file + rand + "\"> </video> ")
      print("<form><input type=hidden name=sd_video_file value='" + sd_video_file + "'>")
      print("<input type=hidden name=cmd value='manual_detect'>")
      print("<input type=hidden name=subcmd value='retrim'>")
      #print(trim_start_sec, dur_sec)
      print("Adjust the start time and duration to re-trim the clip.<BR>")
      print("Trim Start in Seconds (from start of 1 min clip):<input type=textg name=trim_start_sec value='" + str(trim_start_sec) + "'><br>")
      print("Trim Duration in Seconds: <input type=textg name=dur_sec value='" + str(dur_sec) + "'><br>")
      print("<input type=submit name=submit value='Re-Trim Clip'></form><br>")
   if subcmd == 'retrim':
     
      print("<P>If the trim clip looks good, run detect code on this clip: ", show_file)
      print("<form>")
      print("<input type=hidden name=cmd name='subcmd' value='run_detect'>")
      print("<input type=hidden name=temp_sd_video_file value='" + show_file + "'>")
      print("<input type=submit name=submit value='Run Detection Code On This Clip'><br>")
      print("</form>")

def get_template(json_conf, skin = None  ):
   
   template = ""
   skin = "as6ams"
   if skin == "as6ams":
      fpt = open("/home/ams/amscams/pythonv2/templates/as6ams.html", "r")
   else:
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
   #json_conf['cameras'] = sorted(json_conf['cameras'])
   #for cam in json_conf['cameras']:
   for i in range(1,7):
      #cam = i
      key = "cam" + str(i)
      cam = key
      cams_id = json_conf['cameras'][cam]['cams_id']
      try:
            min_total = stats_data[cams_id] 
      except KeyError:
            min_total = 0
      obj_stack = day_dir + "/" + "images/"+ cams_id + "-night-stack.png"
      meteor_stack = day_dir + "/" + "images/" + cams_id + "-meteors-stack.png"
      if cfe(obj_stack) == 0:
         obj_stack = "/dist/img/proccessing.png"
      if cfe(meteor_stack) == 0:
         meteor_stack = "/dist/img/proccessing.png"

      day=day.replace("_","")
 
      html_out = html_out + "<div class='preview col-lg-2 col-md-3 '>"
      html_out = html_out + "<a class='mtt' href='webUI.py?cmd=browse_day&day=" + day_str + "&cams_id="+cams_id+"'  title='Browse all day'>"
      html_out = html_out + "<img alt='" + day_str + "' class='img-fluid ns lz' src='" + obj_stack + "'>"
      html_out = html_out + "</a><span class='pre-b'>Cam #"+ cams_id+" - " + str(min_total) + " minutes</span></div>"     
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
   skin = form.getvalue('skin') 
   if cmd == 'play_vid':
      jsid = form.getvalue('jsid')
      video_file = parse_jsid(jsid)
      print("Location: " + video_file + "\n\n")
      exit() 

   print("Content-type: text/html\n\n")      

   #login
   if cmd == 'login':
      login_page()
      exit() 
   if cmd == 'check_pwd':
      user = form.getvalue("user")
      pwd = form.getvalue("pwd")
      check_pwd_ajax(user,pwd)
      exit()

   # do json ajax functions up here and bypass the exta html
   if cmd == 'override_detect':
      video_file = form.getvalue('video_file')
      jsid = form.getvalue('jsid')
      override_detect(video_file,jsid,json_conf)
      exit()
   if cmd == 'add_frame':
      add_frame_ajax(json_conf,form)
      exit()
   if cmd == 'update_frame_ajax':
      update_frame_ajax(json_conf,form)
      exit()
   if cmd == 'update_hd_cal_ajax':
      update_hd_cal_ajax(json_conf,form)
      exit()
   if cmd == 'update_red_info_ajax':
      update_red_info_ajax(json_conf,form)
      exit()
   if cmd == 'clone_cal':
      clone_cal(json_conf,form)
      exit()
   if cmd == 'custom_fit':
      custom_fit(json_conf,form)
      exit()
   if cmd == 'get_manual_points':
      get_manual_points(json_conf,form)
      exit()
   if cmd == 'del_frame':
      del_frame(json_conf,form)
      exit()
   if cmd == 'del_manual_points':
      del_manual_points(json_conf,form)
      exit()
   if cmd == 'pin_point':
      pin_point(json_conf,form)
      exit()
   if cmd == 'upscale_2HD':
      upscale_2HD(json_conf,form)
      exit()
   if cmd == 'make_plate_from_points':
      make_plate_from_points(json_conf,form)
      exit()
   if cmd == 'list_meteors':
      list_meteors(json_conf,form)
      exit()
   if cmd == 'solve_field':
      solve_field(json_conf,form)
      exit()
   if cmd == 'check_solve_status':
      check_solve_status(json_conf,form)
      exit()
   if cmd == 'show_cat_stars':
      show_cat_stars(json_conf,form)
      exit()
   if cmd == 'fit_field':
      fit_field(json_conf,form)
      exit()
   if cmd == 'reset_reduce':
      reset_reduce(json_conf,form)
      exit()
   if cmd == 'reduce_meteor_ajax':
      cal_params_file = form.getvalue("cal_params_file")
      meteor_json_file = form.getvalue("meteor_json_file")
      show= 0
      reduce_meteor_ajax(json_conf,meteor_json_file, cal_params_file, show)
      exit()
   if cmd == 'delete_cal':
      delete_cal(json_conf,form)
      exit()
   if cmd == 'find_stars_ajax':
      stack_file = form.getvalue("stack_file")
      find_stars_ajax(json_conf,stack_file)
      exit()
   if cmd == 'save_add_stars_to_fit_pool':
      save_add_stars_to_fit_pool(json_conf,form)
      exit()


   #print_css()
   jq = do_jquery()
   
   nav_html,bot_html = nav_links(json_conf,cmd)
   nav_html = ""

   template = get_template(json_conf, skin)
   stf = template.split("{BODY}")
   top = stf[0]
   bottom = stf[1]
   top = top.replace("{TOP}", nav_html)

   obs_name = json_conf['site']['obs_name']
   op_city =  json_conf['site']['operator_city']
   op_state = json_conf['site']['operator_state']
   station_name = json_conf['site']['ams_id'].upper()

   top = top.replace("{OBS_NAME}", obs_name)
   top = top.replace("{OP_CITY}", op_city)
   top = top.replace("{OP_STATE}", op_state)
   top = top.replace("{STATION_NAME}", station_name)
   top = top.replace("{JQ}", jq)

   print(top)
   extra_html = ""
   if cmd == 'reduce_new':
      extra_html = reduce_meteor_new(json_conf, form)
   if cmd == 'reduce':
      extra_html = reduce_meteor_new(json_conf, form)
   if cmd == 'solutions':
      solutions(json_conf, form)
   if cmd == 'sol_detail':
      sol_detail(json_conf, form)
   if cmd == 'rad_calc':
      rad_calc(json_conf, form)

   if cmd == 'free_cal':
      free_cal(json_conf, form)
   if cmd == 'sat_cap':
      sat_cap(json_conf, form)
   if cmd == 'man_reduce':
      extra_html = man_reduce(json_conf,form)

   if cmd == 'choose_file':
      choose_file(json_conf,form)
      
   if cmd == 'manual_detect':
      manual_detect(json_conf,form)
   if cmd == 'run_detect':
      run_detect(json_conf,form)
   if cmd == 'add_stars_to_fit_pool':
      add_stars_to_fit_pool(json_conf,form)

   if cmd == 'video_tools':
      video_tools(json_conf)
   if cmd == 'mask_admin':
      mask_admin(json_conf, form)
   if cmd == 'calibrate_pic':
      calibrate_pic(json_conf, form)
   if cmd == 'meteor_index':
      extra_html = meteor_index(json_conf, form)
   if cmd == 'hd_cal_index':
      extra_html = hd_cal_index(json_conf, form)
   if cmd == 'hd_cal_detail':
      extra_html = hd_cal_detail(json_conf, form)
   if cmd == 'calib_hd_cal_detail':
      extra_html = calib_hd_cal_detail(json_conf, form)

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
      main_page(json_conf,form) 
   if cmd == 'examine_cal':
      examine_cal(json_conf,form)   
   if cmd == 'calibration':
      calibration(json_conf,form)   
   if cmd == 'live_view':
      live_view(json_conf)   
   if cmd == 'meteors':
      meteors_new(json_conf, form)   
   if cmd == 'new_meteors':
      meteors_new(json_conf, form)   
   if cmd == 'config':
      as6_config(json_conf)   
   if cmd == 'browse_detects':
      day = form.getvalue('day')
      type = form.getvalue('type')
      #type = 'meteor'
      #day = '2019_01_27'
      browse_detects(day,type,json_conf,form)   

   #bottom = bottom.replace("{JQ}", jq)      
   bottom = bottom.replace("{BOTTOMNAV}", bot_html)      
   rand=time.time()
   bottom = bottom.replace("{RAND}", str(rand))
   bottom = bottom.replace("{EXTRA_HTML}", str(extra_html))
   print(bottom)
   #cam_num = form.getvalue('cam_num')
   #day = form.getvalue('day')

def reset_reduce(json_conf, form):
   mjf = form.getvalue("cal_params_file")
   mjf = mjf.replace(".json", "-reduced.json") 
   if "reduced.json" not in mjf:
      print("BAD FILE!")
      exit()
   if cfe(mjf) == 0:
      print("BAD FILE!")
      exit()
   if "meteors" not in mjf:
      print("BAD FILE!")
      exit()
   if " " in mjf:
      print("BAD FILE!")
      exit()
   if ";" in mjf:
      print("BAD FILE!")
      exit()
   cmd = "rm " + mjf 
   os.system(cmd)

   mf = mjf.replace("-reduced.json", ".json")
   cmd = "cd /home/ams/amscams/pythonv2/; ./detectMeteors.py raj " + mf + " > /mnt/ams2/tmp/dmt"
   os.system(cmd)
   print(cmd)
   cmd = "cd /home/ams/amscams/pythonv2/; ./autoCal.py imgstars " + mf + " > /mnt/ams2/tmp/dmt"
   os.system(cmd)
   print(cmd)
   #cmd = "cd /home/ams/amscams/pythonv2/; ./autoCal.py cfit " + mf + " > /mnt/ams2/tmp/dmt"
   #os.system(cmd)
   #print(cmd)
   #cmd = "cd /home/ams/amscams/pythonv2/; ./autoCal.py imgstars " + mf + " > /mnt/ams2/tmp/dmt"
   #os.system(cmd)
   #print(cmd)
   #cmd = "cd /home/ams/amscams/pythonv2/; ./detectMeteors.py raj " + mf + " > /mnt/ams2/tmp/dmty"
   #os.system(cmd)

   resp = {}
   resp['status'] = "reduction and cal params reset"
   print(json.dumps(resp))

def list_meteors(json_conf, form):
   meteor_date = form.getvalue("meteor_date")
   files = glob.glob("/mnt/ams2/meteors/" + meteor_date + "/*.json")
   meteors = []
   for file in files:
      if "reduced" in file:
         meteors.append(file)

   print(json.dumps(meteors))


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

def get_cal_files(json_conf,cams_id):

   files = glob.glob("/mnt/ams2/cal/freecal/*")
   cal_files = []
   for file in files:
      el = file.split("/")
      fn = el[-1]
      if cfe(file,1) == 1:
         cal_file = file + "/" + fn + "-calparams.json"
         if cfe(cal_file): 
            cal_file = cal_file.replace("-calparams.json", ".png")
            cal_files.append(cal_file)
         else:
            cal_file = file + "/" + fn + "-stacked-calparams.json"
            cal_file = cal_file.replace("-calparams.json", ".png")
            if cfe(cal_file): 
               cal_files.append(cal_file)
     
   return(cal_files)

def get_cam_ids(json_conf):
   cams = []
   cam_options = ""
   for i in range(1,7):
      cam_key ="cam" + str(i)
      cams_id = json_conf['cameras'][cam_key]['cams_id']
      cams.append(cams_id)
      cam_options = cam_options + "<option>" + cams_id + "</option>"
   return(cams, cam_options)

def calib_hd_cal_detail(json_conf, form):
   cfile = form.getvalue("cfile")
   fn = cfile.split("/")[-1]
   base_name = fn.replace("-stacked.png", "")
   freecal_dir = "/mnt/ams2/cal/freecal/" + base_name
   if cfe(freecal_dir) == 0:
      cmd = "mkdir " + freecal_dir
      os.system(cmd)
      print(cmd)
   cmd2 = "cp " + cfile + " " + freecal_dir + "/" + base_name + "-stacked.png"
   print(cmd)
   os.system(cmd)
   cmfile = cfile.replace("-stacked.png", ".mp4")
   print("<script>window.location.href='/pycgi/webUI.py?cmd=free_cal&input_file=" + cfile + "'</script>")
   return("ok")

def hd_cal_detail(json_conf, form):
   rand = str(time.time())
   cfile = form.getvalue("cfile")
   hd_stack_file = cfile
   cal_params_file = hd_stack_file.replace("-stacked.png", "-calparams.json")
   video_file = hd_stack_file.replace("-stacked.png", ".mp4")
   ci = load_json_file("/mnt/ams2/cal/hd_images/hd_cal_index.json")
   cp = load_json_file(cal_params_file)

   half_stack_file = cfile.replace("-stacked", "-half-stack")
   print(half_stack_file)
   if cfe(half_stack_file) == 0:
      img = cv2.imread(hd_stack_file)
      img = cv2.resize(img, (960,540))
      cv2.imwrite(half_stack_file, img)


   az_grid_file = cfile
   print("CAL DETAIL")
   #print("<img src=" + cfile + ">")
   print("""<div style='width: 80%'>
      <div style="float:left"><canvas id="c" width="960" height="540" style="border:2px solid #000000;"></canvas></div>
   </div>
         <a href="javascript:show_cat_stars('""" + video_file + "','" + hd_stack_file + "','" + cal_params_file + """', 'hd_cal_detail')">Show/Save Catalog Stars</a><BR>
         <a href=/pycgi/webUI.py?cmd=calib_hd_cal_detail&cfile=""" + cfile + """>Calibrate This Image</a><BR>
      <div style='clear: both'></div> 
<div id="star_list"></div>

      <P>&nbsp;</P>
      <P>&nbsp;</P>
      <P>&nbsp;</P>
      <P>&nbsp;</P>
   """)
   for star in cp['cat_image_stars']:
      (dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist) = star

      print(ra,dec, "<BR>") 


   js_html = """
     <script>
       var grid_by_default = false;
       var my_image = '""" + half_stack_file + """'
       var hd_stack_file = '""" + hd_stack_file + """'
       var az_grid_file = '""" + az_grid_file + """'
       var stars = [];
     </script>


     <div hidden>
      <img id='""" + half_stack_file + """' id='half_stack_file'>
      <img id='""" + az_grid_file + """' id='az_grid_file'>
      <img id='""" + half_stack_file + """' id='meteor_img'>
     </div>  

      <script>
      window.onload = function () {
            init_load('""" + str(cfile) + """');
      }
     </script>
   """

   return(js_html)

def meteor_index(json_conf, form):
 
   cgitb.enable()

   cam_id = form.getvalue("cam_id")
   day_limit = form.getvalue("day")
   cur_page  = form.getvalue('p')

   if (cur_page is None) or (cur_page==0):
      cur_page = 1
   else:
      cur_page = int(cur_page)


   mi = load_json_file("/mnt/ams2/cal/hd_images/meteor_index.json")

   meteor_start = (cur_page -1) * NUMBER_OF_METEOR_PER_PAGE 
   meteor_end = meteor_start + NUMBER_OF_METEOR_PER_PAGE
   smi = sorted(mi, reverse=True)

   for day in smi:	   
      for meteor_file in smi[day]:
            print(str(meteor_file))
 
   smi = sorted(mi, reverse=True)

   meteor_start = (cur_page -1) * NUMBER_OF_METEOR_PER_PAGE 
   meteor_end = meteor_start + NUMBER_OF_METEOR_PER_PAGE
   all_meteors = smi

   print("FROM " + str(meteor_start) + " TO " + str(meteor_end))
   print("LE " + str(len(smi)))   
   dsmi = smi[meteor_start:meteor_end]
   print("LED " + str(len(dsmi)))   

   for day in dsmi:
      print("D " + str(day) + "<br/>")
      print("DD " + str(dsmi[day]) + "<br/>")


   print("<h1>Meteor Index</h1>")
   print("<table class='table table-dark table-striped table-hover td-al-m m-auto table-fit'>")
   print("<thead><tr><th>&nbsp;</th><th>Meteor</th><th>Reduced</th><th>Multi-Station</th><th>AZ/EL FOV</th><th>Pos Ang</th><th>Pixscale</th><th>Stars</th><th>Res Px</th><th>Res Deg</th><th>Dur</th><th>Ang Sep</th><th>Mag</th><th>Seg Res</td><th>Missing Frames</th></tr></thead>")
   print("<tbody>")

   for day in dsmi:
      for meteor_file in dsmi[day]:
         hd_datetime, hd_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(meteor_file)
         if cam_id is None:
            show = 1
         elif cam_id == hd_cam:
            show = 1
         else:
            show = 0
         fn = meteor_file.split("/")[-1]
         fn = fn.replace(".json", "")
         video_file = meteor_file.replace(".json", ".mp4")
         link = "<a href='/pycgi/webUI.py?cmd=reduce&video_file=" + video_file + "' class='btn btn-primary'>" + get_meteor_date(video_file) + "</a>"

         if mi[day][meteor_file]['total_res_deg'] > .5:
               color = "lv1"
         elif .4 < mi[day][meteor_file]['total_res_deg'] < .5:
               color = "lv2"
         elif .3< mi[day][meteor_file]['total_res_deg'] < .4:
               color = "lv3"
         elif .2 < mi[day][meteor_file]['total_res_deg'] < .3:
               color = "lv4"
         elif .1 < mi[day][meteor_file]['total_res_deg'] < .2:
               color = "lv5"
         elif mi[day][meteor_file]['total_res_deg'] == 0:
               color = "lv6"
         elif mi[day][meteor_file]['total_res_deg'] == 9999:
               color = "lv7"
         elif 0 < mi[day][meteor_file]['total_res_deg'] < .1:
               color = "lv8"
         else:
               color = "lv7"
         if 'center_az' in mi[day][meteor_file]:
            az_el = str(mi[day][meteor_file]['center_az'])[0:5] + "/" +  str(mi[day][meteor_file]['center_el'])[0:5]
         else:
            az_el = ""
         if 'event_start_time' in mi[day][meteor_file]:
            fn = mi[day][meteor_file]['event_start_time'] + " - " + hd_cam 
         pos = ""
         pxs = ""
         ts = 0 
         if 'multi_station' in mi[day][meteor_file]:
            multi_text = "Y"
         else:
            multi_text = "N"
         if 'total_stars' in mi[day][meteor_file]:
            ts = str(mi[day][meteor_file]['total_stars'])
         if 'position_angle' in mi[day][meteor_file]:
            pos = str(mi[day][meteor_file]['position_angle'])[0:5]

         ass = ""
         dur = ""
         if 'angular_separation' in mi[day][meteor_file]:
            ass = mi[day][meteor_file]['angular_separation']
         else:
            ass = ""
         if 'event_duration' in mi[day][meteor_file]:
            dur = str(mi[day][meteor_file]['event_duration'])
         else:
            dur = ""
         
         fn = meteor_file.split("/")[-1] 
         if 'pixscale' in mi[day][meteor_file]:
            pxs = str(mi[day][meteor_file]['pixscale'])[0:5]
         if day_limit is not None:
            if day_limit == fn[0:10]:
               show = 1
            else:
               show = 0

         if "red_seg_res" in mi[day][meteor_file]:
            seg_res = mi[day][meteor_file]['red_seg_res']
         else:
            seg_res = 999
         if "frames_missing_before" in mi[day][meteor_file]:
            missing_frames = len(mi[day][meteor_file]['frames_missing_before'])
         else:
            missing_frames = 0

         if seg_res != 999 :
            if seg_res > 2 or missing_frames > 0:
               color = "lv1"
         if show == 1:
            print("<tr class='" + color + "'><td><div class='st'></div></td><td> {:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td><td> {:s}</td><td> {:s} </td><td>{:s}</td><td>{:s}</td><td>MAG</td><td>{:s}</td><td>{:s}</td></tr> ".format(link, str(mi[day][meteor_file]['reduced']), multi_text, az_el, pos, pxs, str(ts), str(mi[day][meteor_file]['total_res_px'])[0:5], str(mi[day][meteor_file]['total_res_deg'])[0:5], str(dur), str(ass), str(seg_res), str(missing_frames)))
          
   print("</tbody></table>")


def hd_cal_index(json_conf, form):
   
   cgitb.enable()

   js_img_array = {}
   cam_id_filter = form.getvalue("cam_id")
   print("<h1>Auto Calibration</h1>")
 
   ci = load_json_file("/mnt/ams2/cal/hd_images/hd_cal_index.json")
   cam_day_sum = load_json_file("/mnt/ams2/cal/hd_images/hd_cal_index-cam-day-sum.json")

   print('<div class="m-auto" style="max-width: 1730px;">')
   print('<table class="table table-dark table-striped table-hover m-3 td-al-m">')
   print('<thead><tr><th>Date</th><th>Cam ID</th><th>Images w/ Stars</th><th>Images w/o Stars</th><th>Total Stars For Night</th><th>Center AZ/EL</th><th>Position Angle</th><th>PixScale</th><th>Avg Res Px For Night</th><th>Avg Res Deg For Night</th></tr></thead>')
   print('<tbody>')

   for day in sorted(ci,reverse=True): 
         
      print('<tr><td colspan="10"><h6 class="mb-0">'+day.replace("_","/")+'</h6></td></tr>')

      for cam_id in sorted(ci[day],reverse=False):

         if "files_with_stars" in cam_day_sum[day][cam_id]:
            desc = str(cam_day_sum[day][cam_id]['files_with_stars']) + " files with stars / "
            desc = desc + str(cam_day_sum[day][cam_id]['files_without_stars']) + " files without stars "
         else:
            desc = ""
         
         div_id = str(day) + "_" + str(cam_id)
         show_link = '<a class="btn btn-sm btn-primary"><b>'+cam_id+'</b></a>'
 
         if cam_day_sum[day][cam_id]['avg_res_deg_for_night'] > .5:
               color = "lv1"
         elif .4 < cam_day_sum[day][cam_id]['avg_res_deg_for_night'] <= .5:
               color = "lv2"
         elif .3 < cam_day_sum[day][cam_id]['avg_res_deg_for_night'] <= .4:
               color = "lv3"
         elif .2 < cam_day_sum[day][cam_id]['avg_res_deg_for_night'] <= .3:
               color = "lv4"
         elif .1 < cam_day_sum[day][cam_id]['avg_res_deg_for_night'] <= .2:
               color = "lv8"
         elif 0 < cam_day_sum[day][cam_id]['avg_res_deg_for_night'] <= .1:
               color = "lv5"
         elif cam_day_sum[day][cam_id]['avg_res_deg_for_night'] == 0:
               color = "lv7"
         else: 
               color = "lv7"

         if cam_id_filter is None:
            show_row = 1
         elif cam_id == cam_id_filter:
            show_row = 1
         else:
            show_row = 0 

         if "position_angle" in cam_day_sum[day][cam_id]:
            fov_pos = str(cam_day_sum[day][cam_id]['position_angle'])[0:5] 
         else : 
            fov_pos = ""

         if "center_az" in cam_day_sum[day][cam_id]:
            az_el = str(str(cam_day_sum[day][cam_id]['center_az'])[0:5] + "/" + str(cam_day_sum[day][cam_id]['center_el'])[0:5])
         else : 
            az_el = ""
         if "position_angle" in cam_day_sum[day][cam_id]:
            pos_ang = str(str(cam_day_sum[day][cam_id]['position_angle'])[0:5])
         else : 
            pos_ang = ""
         if "pixscale" in cam_day_sum[day][cam_id]:
            px_scale = str(str(cam_day_sum[day][cam_id]['pixscale'])[0:5])
         else : 
            px_scale = ""

         if show_row == 1:
            print("<tr class='" + color + " clickable toggler' data-tog='#fr"+div_id+"'><td><div class='st'></div></td><td>{:s}</a></td><td>{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td></tr>".format(show_link, str(cam_day_sum[day][cam_id]['files_with_stars']), str(cam_day_sum[day][cam_id]['files_without_stars']), str(cam_day_sum[day][cam_id]['total_stars_tracked_for_night']), az_el, pos_ang, px_scale, str(cam_day_sum[day][cam_id]['avg_res_px_for_night'])[0:5],str(cam_day_sum[day][cam_id]['avg_res_deg_for_night'])[0:5]))
          
            print("<tr><td colspan='11' class='collapse' id='fr"+div_id+"'>")
            print("<div class='text-center text-lg-left gallery gal-resize d-flex flex-wrap' style='max-width: 1520px;'>")
            js_img_array["fr"+div_id] = []

            for cfile in sorted(ci[day][cam_id], reverse=True):
               if "total_res_deg" in ci[day][cam_id][cfile]:
                  trd = ci[day][cam_id][cfile]['total_res_deg']
                  trp = ci[day][cam_id][cfile]['total_res_px']
                  ts = ci[day][cam_id][cfile]['total_stars']
               else:
                  trd = 0 
                  trp = 0 
                  ts = 0 

               fn = cfile.split("/")[-1]
               tn = "/mnt/ams2/cal/hd_images/" + day + "/thumbs/" + fn 
               tn = tn.replace(".png", "-tn.png")
               detail_link = "webUI.py?cmd=hd_cal_detail&cfile=" + cfile
               if trp >= 5:
                  color = "style='color: #ff0000'"
               else:
                  color = ""
            
               
               js_img_array["fr"+div_id].append({'col':color, 'lk': detail_link, 'src': tn, 'st': str(ts), 'trp': str(trp)[0:5] , 'trd':  str(trd)[0:5]})
               #print('<div class="preview p-2"><a href="'+detail_link+'" class="m:ttt">')
               #print('<img data-src="'+tn+'" class="ns lz-shown" width="200" height="112"/>');
               #print('</a><span class="det" '+color+'><b>' + str(ts) + "</b> stars - <b>" + str(trp)[0:5] + "</b>Rpx - <b>" +  str(trd)[0:5] + "</b>Rd</span></div>")

             
            print("</div>")
            print("</td></tr> ")
   print("</div></table>")
   print("</div></div>")

   # Show the details dynamically to we speed up the page load (by A LOT)
   print("<script>var all_cal_details="+json.dumps(js_img_array)+"</script>") 
   return("")

def calibration(json_conf,form):
   cam_id_filter = form.getvalue("cam_id")

   print("<h1>Past Calibrations</h1>")
   ci = load_json_file("/mnt/ams2/cal/freecal_index.json")
   

   print("<table class='table table-dark table-striped table-hover td-al-m m-auto table-fit'>")
   print("<thead><tr><th>&nbsp;</th><th>Date</th><th>Cam ID</th><th>Stars</th><th>Center AZ/EL</th><th>Pos Angle</th><th>Pixscale</th><th>Res Px</th><th>Res Deg</th></tr></thead>")
   print("<tbody>")
 
   for cf in sorted(ci, reverse=True):
      if 'cal_image_file' in ci[cf]:
         link = "/pycgi/webUI.py?cmd=free_cal&input_file=" + ci[cf]['cal_image_file'] 
      else:
         link = ""
      if ci[cf]['total_res_deg'] > .5:
         color = "lv1"; #style='color: #ff0000'"
      elif .4 < ci[cf]['total_res_deg'] <= .5:
         color = "lv2"; #"style='color: #FF4500'"
      elif .3 < ci[cf]['total_res_deg'] <= .4:
         color = "lv3"; #"style='color: #FFFF00'"
      elif .2 < ci[cf]['total_res_deg'] <= .3:
         color = "lv4"; #"style='color: #00FF00'"
      elif .1 < ci[cf]['total_res_deg'] <= .2:
         color = "lv5"; #"style='color: #00ffff'"
      elif 0 < ci[cf]['total_res_deg'] <= .1:
         color = "lv8"; #"style='color: #0000ff'"
      elif ci[cf]['total_res_deg'] == 0:
         color = "lv7"; #"style='color: #ffffff'"
      else:
         color = "lv7"
      if cam_id_filter is None:
         show_row = 1
      elif cam_id == cam_id_filter:
         show_row = 1
      else:
         show_row = 0

      if show_row == 1: 
         print("<tr class='" + color + "'><td><div class='st'></div></td><td><a class='btn btn-primary' href='{:s}'>{:s}</a></td><td><b>{:s}</b></td><td>{:s}</td><td>{:s}/{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td></tr>".format( link, str(ci[cf]['cal_date']), \
            str(ci[cf]['cam_id']), str(ci[cf]['total_stars']), str(ci[cf]['center_az']), str(ci[cf]['center_el']), str(ci[cf]['position_angle']), \
            str(ci[cf]['pixscale']), str(ci[cf]['total_res_px']), str(ci[cf]['total_res_deg']) ))

   print("</tbody></table></div>")



def calibration_old(json_conf,form):
   cams_id = form.getvalue('cams_id')
   print("<h2>Calibration</h2>")
   print("<p><a href=webUI.py?cmd=free_cal>Make New Calibration</a></P>")
   print("<p>Or select a previous job to work on</p>")
   cal_files = get_cal_files(json_conf,cams_id)
   cams, cam_options = get_cam_ids(json_conf)
   print("""
      <div style="float: top-right">
      <form>
       <select name=cam_id onchange="javascript:goto(this.options[selectedIndex].value, '', 'calib')">
        <option value=>Filter By Cam</option>""")
   print(cam_options)
   print("""    
        </select>
      </form>
      </div>
      """)

   cal_files = sorted(cal_files, reverse=True)

   for file in cal_files:
      el = file.split("/")
      fn = el[-1]
      az_grid_file = file.replace(".png", "-azgrid-half.png")
      if cams_id is not None and cams_id in file:
         print("<figure><a href=webUI.py?cmd=free_cal&input_file=" + file + "><img width=354 src=" + az_grid_file + "><figcaption>"+ fn + "</figcaption></figure>")
   print("<div style=\"clear: both\"></div>")
   #cal_params = get_cal_params(json_conf, cams_id)




   stab,sr,sc,et,er,ec = div_table_vars()
   #print(stab)

   #print(sr+sc+"Date"+ec+sc+"Camera" + ec + sc + "Center RA/DEC" + ec + sc + "Center AZ/EL" + ec + sc +"Pixel Scale" + ec + sc + "Position Angle" + ec + sc + "Residual" + ec + er)
   #for cal_param in sorted(cal_params,reverse=True):
   #   hd_datetime, hd_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(cal_param)
   #   json_data = load_json_file(cal_param )

   #   az,el = radec_to_azel(json_data['ra_center'],json_data['dec_center'], hd_datetime,json_conf)


   #   print(sr + sc + "<a href=webUI.py?cmd=examine_cal&cal_param=" + cal_param + ">" + hd_date + "</a>" + ec + sc + hd_cam + ec + sc + str(json_data['ra_center'])[0:6] + "/" + str(json_data['dec_center'])[0:5] + ec + sc + str(az)[0:5] + "/" + str(el)[0:5] + ec + sc + str(json_data['pixscale'])[0:5] + ec + sc + str(json_data['position_angle'])[0:5] + ec + sc + str(json_data['x_fun'])[0:4] + "," + str(json_data['y_fun'])[0:4] + ec + er)
   #print(et)

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
      if "calparams" not in file and "reduced" not in file and "manual" not in file:
         meteors.append(file)
   return(meteors)

 
 
def meteors_new(json_conf,form):  

   cgitb.enable()

   limit_day = form.getvalue('limit_day')
   cur_page  = form.getvalue('p')

   if (cur_page is None) or (cur_page==0):
      cur_page = 1
   else:
      cur_page = int(cur_page)


   htclass = "none"
   meteors = []
   meteor_base_dir ="/mnt/ams2/meteors/"
   meteor_dirs = sorted(get_meteor_dirs(meteor_base_dir), reverse=True)
  
   header_out = "<div class='h1_holder  d-flex justify-content-between'>"
   html_out = ""

   norm_cnt = 0
   reduced_cnt = 0
   has_limit_day = 0
 
   for meteor_dir in meteor_dirs:
      el = meteor_dir.split("/")
      this_date = el[-1]
      if limit_day is None: 
         meteors = get_meteors(meteor_dir, meteors)
      elif limit_day == this_date:
         meteors = get_meteors(meteor_dir, meteors)
         has_limit_day = 1
         header_out = header_out + "<h1><span class='h'><span id='meteor_count'>"+format(len(meteors))+"</span> meteors</span> captured on"
         header_out = header_out + "<div class='input-group date datepicker' data-display-format='YYYY/MM/DD' data-action='reload' data-url-param='limit_day' data-send-format='YYYY_MM_DD'>"
         header_out = header_out + "<input value='"+str(this_date.replace("_", "/"))+"' type='text' class='form-control'>"
         header_out = header_out + "<span class='input-group-addon'><span class='icon-clock'></span></span></div></h1>"
   
   if limit_day is None and len(meteors)>=1:
      header_out = header_out + "<h1><span class='h'><span id='meteor_count'>"+format(len(meteors))+"</span> meteors</span> captured since inception</h1>"
   
   if len(meteors)>=1 :
      meteors_displayed = 0

      #NUMBER_OF_METEOR_PER_PAGE
      meteors = sorted(meteors,reverse=True)

      meteor_from       = NUMBER_OF_METEOR_PER_PAGE*cur_page
      total_number_page = math.ceil(len(meteors) / NUMBER_OF_METEOR_PER_PAGE)
      counter = 0
 
      meteor_start = (cur_page -1) * NUMBER_OF_METEOR_PER_PAGE 
      meteor_end = meteor_start + NUMBER_OF_METEOR_PER_PAGE
      all_meteors = meteors

      meteors = meteors[meteor_start:meteor_end]

      for idx, meteor in enumerate(meteors):
         # Minus 1 so we have NUMBER_OF_METEOR_PER_PAGE per page starting at 0
         if(counter<=NUMBER_OF_METEOR_PER_PAGE-1 and idx <= meteor_from):
            stack_file_tn = meteor.replace('.json', '-stacked-tn.png')
            video_file = meteor.replace('.json', '.mp4')
            stack_obj_img = video_file.replace(".mp4", "-stacked-obj-tn.png")
            reduce_file = meteor.replace(".json", "-reduced.json")
            reduced = 0
            if cfe(reduce_file) == 1:
               reduced = 1
            el = meteor.split("/")
            temp = el[-1].replace(".mp4", "")
            xxx = temp.split("-trim")
            desc = xxx[0] 
            desc_parts = desc.split("_")
            desc = desc_parts[1] + "/" + desc_parts[2] + " " + desc_parts[3] + ":" + desc_parts[4] + " - " + desc_parts[7]

            base_js_name = el[-1].replace("_", "")
            base_js_name = base_js_name.replace(".json", "")
            base_js_name_img = "img_" + base_js_name
            fig_id = "fig_" + base_js_name
            del_id =  base_js_name

            #We also can have fail or meteor (the css is ready for that)
            if reduced == 1: 
               htclass = "reduced"
               reduced_cnt = reduced_cnt + 1
            else: 
               htclass = "norm"
               norm_cnt = norm_cnt + 1

            html_out = html_out + "<div id='"+del_id+"' class='preview col-lg-2 col-md-3  "+ htclass +"'>"
            html_out = html_out + "<a class='mtt' href='webUI.py?cmd=reduce&video_file=" + video_file + "' data-obj='"+stack_obj_img+"' title='Go to Info Page'>"
            html_out = html_out + "<img alt='"+desc+"' class='img-fluid ns lz' src='" + stack_file_tn + "'>"
            html_out = html_out + "<span>" + desc + "</span></a>"     
            html_out = html_out + "<div class='btn-toolbar'><div class='btn-group'>"
            html_out = html_out + "<a class='vid_link_gal col btn btn-primary btn-sm' title='Play Video' href='./video_player.html?video=" + video_file + "&vid_id="+del_id+"'><i class='icon-play'></i></a>"
            html_out = html_out + "<a class='delete_meteor_gallery col btn btn-danger btn-sm' title='Delete Detection' data-meteor='" + del_id + "'><i class='icon-delete'></i></a>"
            html_out = html_out + "</div></div></div>"
            counter = counter + 1


      non_rec_cnt = len(meteors)-reduced_cnt
    
      #Create buttons
      #header_out = header_out + '<div class="btn-group btn-group-toggle" data-toggle="buttons">'
      #header_out = header_out + '<label class="btn btn-secondary active btn-met-all">'
      #header_out = header_out + '<input type="radio" name="meteor_select" id="all" autocomplete="off" checked=""> All '+ format(len(meteors)) +' meteors</label>'
      #header_out = header_out + '<label class="btn btn-secondary btn-met-reduced">'
      #header_out = header_out + '<input type="radio" name="meteor_select" id="reduced" autocomplete="off">All '+  format(reduced_cnt) +' Reduced Meteors Only</label>'
      #header_out = header_out + '<label class="btn btn-secondary">'
      #header_out = header_out + '<input type="radio" name="meteor_select" id="non_reduced" autocomplete="off">All '+ format(non_rec_cnt) +'  Non-Reduced Meteors Only</label>'
       
      if(has_limit_day==0):
         pagination = get_pagination(cur_page,len(all_meteors),"/pycgi/webUI.py?cmd=new_meteors",NUMBER_OF_METEOR_PER_PAGE)
      else:
         pagination = get_pagination(cur_page,len(all_meteors),"/pycgi/webUI.py?cmd=new_meteors&limit_day="+limit_day,NUMBER_OF_METEOR_PER_PAGE)

      if(pagination[2] != ''):
         header_out = header_out + "<div class='page_h'>Page  " + format(cur_page) + "/" +  format(pagination[2]) + "</div>"

   else:
      header_out = header_out + "<h1><span class='h'><span id='meteor_count'>0</span> meteor</span> captured on"
      header_out = header_out + "<div class='input-group date datepicker' data-display-format='YYYY/MM/DD' data-action='reload' data-url-param='limit_day' data-send-format='YYYY_MM_DD'>"
      header_out = header_out + "<input value='"+str(this_date.replace("_", "/"))+"' type='text' class='form-control'>"
      header_out = header_out + "<span class='input-group-addon'><span class='icon-clock'></span></span></div>"

   print(header_out+'</div></div>')
   print("<div id='main_container' class='container-fluid h-100 mt-4 lg-l'>")
   print("<div class='gallery gal-resize row text-center text-lg-left'>")
   print(html_out)
   print("</div>")
   #page,total_pages,url for pagination
   if(len(meteors)>=1):
      print(pagination[0])
   
   print("</div>") 
 


def meteors(json_conf,form): 
   print ("""
   


   """)


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
      reduce_file = meteor.replace(".json", "-reduced.json")
      reduced = 0
      if cfe(reduce_file) == 1:
         reduced = 1
      

      el = meteor.split("/")
      temp = el[-1].replace(".mp4", "")
      xxx = temp.split("-trim")
      desc = xxx[0] 
      desc_parts = desc.split("_")
      desc = desc_parts[1] + "/" + desc_parts[2] + " " + desc_parts[3] + ":" + desc_parts[4] + " - " + desc_parts[7]


      base_js_name = el[-1].replace("_", "")
      base_js_name = base_js_name.replace(".json", "")
      base_js_name_img = "img_" + base_js_name
      fig_id = "fig_" + base_js_name
      del_id =  base_js_name
      if reduced == 1: 
         htclass = "reduced"
      else: 
         htclass = "norm"

      buttons = "<br><a href=\"javascript:play_meteor_video('" + video_file + " ')\">Play</A> - " 
      #buttons = " <a class=\"vid-link\" href=\"" + video_file + "\">Play</a> -"
      #buttons = """
      #    <a href='""" + video_file + """'>Play</a>
#
#      """

      buttons = buttons + "<a href=\"webUI.py?cmd=reduce&video_file=" + video_file + "\"" + ">Info</A> - " 
      buttons = buttons + "<a href=\"javascript:reject_meteor('" + del_id + "')\">Del</A>" 

      html_out = ""
      this_span = span.replace("{ID}", base_js_name)
      html_out = html_out + "<figure id=\"" + fig_id + "\">" + this_span + "<a href=\"webUI.py?cmd=reduce&video_file=" + video_file + "\"" \
         + " onmouseover=\"document.getElementById('" + base_js_name_img + "').src='" + stack_obj_img \
         + "'\" onmouseout=\"document.getElementById('" + base_js_name_img + "').src='" + stack_file_tn+ "'\">"
  
      html_out = html_out + "<img width=282 height=192 class=\"" + htclass + "\" id=\"" + base_js_name_img + "\" src='" + stack_file_tn+ "'></a>" + end_span + "<figcaption>" + desc + str(buttons) + "</figcaption></figure>\n"

      print(html_out)
   print("<div style='clear: both'></div>")
   print("<script>var stars = []; var az_grid_file = '';</script>")



def live_view(json_conf):
 

   print("""<h1>Live</h1>
            <div class="container mt-3" style="max-width: 1500px;">
                  <p class="text-center"><b>Still pictures are updated in 5 minutes intervals. This page will automatically refresh in <span id="cntd">2:00</span>.</b></p>
                  <div class="gallery gal-resize row text-center text-lg-left mb-4">
   """)
 
   rand=time.time()
   for cam_num in range(1,7):
      cam_key = 'cam' + str(cam_num)
      cam_ip = json_conf['cameras'][cam_key]['ip']
      #sd_url = json_conf['cameras'][cam_key]['sd_url']
      #hd_url = json_conf['cameras'][cam_key]['hd_url']
      cams_id = json_conf['cameras'][cam_key]['cams_id']

      img = "/mnt/ams2/latest/" + cams_id + ".jpg"
      

      print('<div class="preview col-lg-4 mb-4"><a class="mtt img-link-gal" href="'+img+'" title="Live View">')
      print('<img alt="'+cams_id+'" class="img-fluid ns lz" src="'+img+'?r=' + str(rand) + '"><span><b>Cam '+cams_id+' ('+cam_ip+')</span></b></a></div>')

   print("</div></div></div>")

   #Countdown
   print("""
      <script>
      var timeoutHandle;
      function countdown(minutes) {
            var seconds = 60;
            var mins = minutes;
            if(mins==0) {
                  location.reload();
            }
            function tick() {
                  var counter = document.getElementById("cntd");
                  var current_minutes = mins-1
                  seconds--;
                  counter.innerHTML = current_minutes.toString() + ":" + (seconds < 10 ? "0" : "") + String(seconds);
                  if( seconds > 0 ) {
                        timeoutHandle = setTimeout(tick, 1000);
                  } else {
                        if(mins > 1){
                              setTimeout(function () { countdown(mins - 1); }, 1000);
                        }
                  }
            }
            tick();
      }
      countdown(5);
      </script>
   """)

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
   img_dir = "/mnt/ams2/latest/"

   #files = glob.glob(img_dir +  cams_id + ".jpg")
   file = img_dir + cams_id + ".jpg"
   sfile = img_dir + cams_id + "-sm.jpg"
   img = cv2.imread(file)
   simg = cv2.resize(img, (704,576))
   cv2.imwrite(sfile, simg)
   files = [sfile]

   return(sfile)

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
      #print(imgf) 
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
      bot_nav = bot_nav + "<a href=\"webUI.py?cmd=" + link + "\">" + nav_links[link] + "</a>"
   
   return(nav, bot_nav)

def video_tools(json_conf):
   print("<div class='alert alert-info m-3 text-center'>Coming soon</div>")
   #print("video tools")
   #print("<li>Join Two Clips</li>")
   #print("<li>Trim Clip</li>")
   #print("<li>Stack Video</li>")
   #print("<li>Make Meteors Tonight Video</li>")
   #print("<li>Make Timelapse</li>")

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
   failed_files, meteor_files, pending_files = get_trims_for_file(video_file)
   stack_file = stack_file_from_video(video_file)
   next_stack_file = stack_file_from_video(video_file)
  

   print("<h1>Examine One-Minute Clip - " +  get_meteor_date(video_file) +"</h1>")
   print("<div id='main_container' class='container-fluid d-flex h-100 mt-4 position-relative'>")

   print("<div class='h-100 flex-fixed-canvas'>")

   if os.path.isfile(stack_file):
      print("<a href='" + video_file + "' class='vid_link_gal mx-auto d-block' title='Click to Play'><img src='" + stack_file + "' class='mx-auto d-block img-fluid' style='width:100%'></a>")
   else:
      print("<div class='alert error'>The Stack Image isn't ready yet.</div>")

   print("</div>")
   print("<div class='flex-fixed-r-canvas h-100'>")
   print("<div class='box'><h2 class='mb-4'>Actions</h2>")
   print("<a class='btn btn-primary mx-auto d-block mb-2' href='webUI.py?cmd=manual_detect&sd_video_file=" + video_file + "'>Manually Detect</a>")
   print("<a class='btn btn-primary mx-auto d-block mb-2' href='webUI.py?cmd=choose_file&input_file=" + video_file + "'>Calibrate Star Field</a>")
   print("<a class='btn btn-primary mx-auto d-block mb-2' href='webUI.py?cmd=add_stars_to_fit_pool&input_file=" + video_file + "'>Add Stars To Fit Pool</a>")
   print("<a class='btn btn-primary mx-auto d-block mb-2' href='webUI.py?cmd=sat_cap&input_file=" + video_file + "&stack_file=" + stack_file + "&next_stack_file=" + next_stack_file + "'>Add / Reduce Satellite Capture</a>")
   print("</div>")

   print("<div class='box'><h2>Status</h2>")
   print("<div class='p-3'>")
 
   if len(pending_files) > 0:
      print("<p>Trim files for this clip are still pending processing. Please wait before manually processing this file.</p>")
      print("<ul>")
      for pending in pending_files:
         print("<li><a href=" + pending + ">" + pending + "</a></li>")
      print("</ul>")

   if len(meteor_files) > 0:
      print("<p class='text-center alert success'><b>Meteor DETECTED</b></p>")
      for meteor_file in meteor_files:
         meteor_stack = meteor_file.replace(".mp4", "-stacked.png")
         print("<a href='" + meteor_file + "' class='mx-auto d-block'>")
         print("<img src='" + meteor_stack + "' class='mx-auto d-block img-fluid'></a>")
         print("<a class='btn btn-primary mx-auto d-block mt-1 mb-3' href='webUI.py?cmd=examine&video_file=" + meteor_file + "'>Examine</a>")

   if len(failed_files) > 0: 
      print("<p class='text-center alert error'><b>NON METEOR Detection</b></p>")
      for fail_file in failed_files:
         fail_stack = fail_file.replace(".mp4", "-stacked.png")
         print("<a href='" + fail_file + "' class='mx-auto d-block'>")
         print("<img src='" + fail_stack + "' class='mx-auto d-block img-fluid'></a>")
         print("<a class='btn btn-primary mx-auto d-block  mt-1 mb-3' href='webUI.py?cmd=examine&video_file=" + fail_file + "'>Examine</a>")
        
   if len(failed_files) == 0 and len(meteor_files) == 0:
      print("<p class='text-center alert error'><b>NO Detection</b></p>")
   #print(failed_files,meteor_files)

   print("</div></div></div></div></div>") 

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
   
   #print_css()
   print("<h1>Examine Trim File</h1>")
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
   if "meteors" in video_file or "passed" in video_file:
      print("<a href=webUI.py?cmd=override_detect&video_file=" + video_file + " >Reject Meteor</a>  ")
   else:
      print("<a href=webUI.py?cmd=override_detect&video_file=" + video_file + " >Tag as Meteor</a>  ")

   #print("<a href=webUI.py?cmd=reset&type=meteor&video_file=" + video_file + " >Re-run Detection</a>")

   print("</figure>")
   print("<p style='clear: both'></p>")
   json_file = video_file.replace(".mp4", ".json")


   json_data= load_json_file(json_file)
   object_info = object_info_table(json_data)
   meteor_info = meteor_info_table(video_file, json_data)
   if meteor_info is not None:
      print(meteor_info)
   

   if "hd_trim" in json_data:
      hd_trim = json_data['hd_trim']
      hd_crop = json_data['hd_crop_file']
   else:
      hd_trim = None
      hd_crop = None
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

   print(object_info)


def get_obj_test_score(object):
   print("YO")

def default_tests():
   tests = {}
   tests['score'] = 0 
   tests['Moving'] = 0
   tests['Distance'] = 0
   tests['Hist Len']  = 0
   tests['Elp Frames'] = 0
   tests['AVL'] = 0
   tests['Big CNT'] = 0
   tests['Big/CM'] = 0
   tests['CM/Gaps'] = 0 
   tests['CM To Hist'] = 0
   tests['PX/Frame'] = 0
   tests['Moving'] = 0
   tests['Dupe Px'] = 0
   tests['Line Fit'] = 0
   tests['Peaks'] = 0
   return(tests)

def object_info_table(json_data):
   if "sd_objects" in json_data:
      sd_objects = json_data['sd_objects']
   else:
      sd_objects = json_data
   stab,sr,sc,et,er,ec = div_table_vars()
   oit = "<h3>Object Details</h3>" + stab
   oit = oit + sr + sc + "ID" + ec + sc + "Meteor" + ec + sc + "Score" + ec + sc + "Moving" + ec + sc + "Dist" + ec + sc + "Len" + ec + sc + "Elp Frms" + ec + sc + "AVL" + ec + sc + "Trailer" + ec + sc + "Big CNT" + ec + sc + "Big/CM" + ec + sc + "CM/Gaps" + ec + sc + "CM/Hist" + ec + sc + "PX/Frm" + ec + sc + "Dupe PX" + ec + sc +"Noise" + ec + sc + "Line Fit" + ec + sc + "Peaks" + ec + er  
   for obj in sd_objects:
      tests= default_tests()
      tests['score']  = 0
      test_detail = stab
      meteor_yn = obj['meteor']
      if meteor_yn == 1:
         meteor_yn = "Y"
      else:
         meteor_yn = "N"
    
      for test in obj['test_results']:
         name, result, descr = test
         tests[name] = result 
         test_detail = test_detail + sr + sc + str(name) + ec + sc + str(result) + ec + sc + str(descr) + ec + er
         tests['score']  = tests['score'] + int(result)
      test_detail = test_detail + et 
      total_tests = len(obj['test_results'])

      oit = oit + sr + sc + "<a href=\"javascript:show_hide_div('" + str(obj['oid']) + "')\">" + str(obj['oid']) + "</a>" + ec
      oit = oit +  sc + str(meteor_yn) + ec + sc + str(tests['score']) + ec + sc + str(tests['Moving']) + ec + sc + str(tests['Distance']) + ec + sc + str(tests['Hist Len']) + ec + sc + str(tests['Elp Frames']) + ec + sc + str(tests['AVL']) + ec + sc + str(tests['Trailer']) + ec + sc + str(tests['Big CNT']) + ec + sc + str(tests['Big/CM']) + ec + sc + str(tests['CM/Gaps']) + ec + sc + str(tests['CM To Hist']) + ec + sc + str(tests['PX/Frame']) + ec + sc + str(tests['Moving']) + ec + sc + str(tests['Dupe Px']) + ec + sc + str(tests['Line Fit']) + ec + sc + str(tests['Peaks']) + ec + er  
      oit = oit + sr + "<div id=\"" + str(obj['oid']) + "\" style=\"display: none; width: 100%\">" + test_detail + "</div>" + er
   oit = oit + et
   return(oit)
   return(oit)

def meteor_info_table(video_file,json_data):
   if "meteor_data" not in json_data:
      mi = "This meteor has not been reduce yet. "
      mi = mi + "<a href=webUI.py?cmd=reduce&video_file=" + video_file + ">Reduce Meteor Now</a>"
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



#$body = $("body");

#$(document).bind({
#    ajaxStart: function() {
#       $("#waiting").show();
#       //$body.addClass("waiting");
#       console.log("starting ajax")
#    },
#    ajaxStop: function() {
#       $("#waiting").hide();
#       //$body.removeClass("waiting");
#       console.log("ending ajax")
#    }
#});

#<script src="https://cdnjs.cloudflare.com/ajax/libs/jquery/3.3.1/jquery.min.js"></script>
#<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/jquery-contextmenu/2.7.1/jquery.contextMenu.min.css">
#<script src="https://cdnjs.cloudflare.com/ajax/libs/jquery-contextmenu/2.7.1/jquery.contextMenu.min.js"></script>
#<script src="https://cdnjs.cloudflare.com/ajax/libs/jquery-contextmenu/2.7.1/jquery.ui.position.js"></script>

   jq = """
<script>



</script>


   """

                #"confirm": {name: "Confirm Meteor"},
                #"satellite": {name: "Mark as Satellite"},
                #"quit": {name: "Quit", icon: function(){
                    #return 'context-menu-icon context-menu-icon-quit';


   return(jq)

def print_css():
   print ("""
<!--
      <script>
         function goto(var1,var2, type) {
            if (type == "calib") {
               url_str = "webUI.py?cmd=calibration&cams_id=" + var1
               window.location.href=url_str
            }
            if (type == "reduce") {
            
               url_str = "webUI.py?cmd=reduce&video_file=" + var1 + "&cal_params_file=" + var2
               window.location.href=url_str
            }
         }
      </script>
-->
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
            padding: 0.1em;
            margin: 0.1em;
         }
         img.reduced {
            border: thin ff9900 solid;
            background-color: ff9900;
            margin: 0.1em;
            padding: 0.1em;
         }

         img.meteor {
            border: thin red solid;
            background-color: red;
            margin: 0.1em;
            padding: 0.1em;
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
            margin: 0.1em;
            padding: 0.1em;
         }
      </style>
   """)


def browse_day(day,cams_id,json_conf):
   day_files = get_day_files(day,cams_id,json_conf)
   cc = 0
   all_files = []
   for base_file in sorted(day_files,reverse=True):
      all_files.append(base_file)

   print("<div class='h1_holder d-flex justify-content-between'><h1><span class='h'><span id='meteor_count'>"+format(len(day_files))+"</span> detections</span> on")
   print("<div class='input-group date datepicker' data-display-format='YYYY/MM/DD' data-action='reload' data-url-param='day' data-send-format='YYYY_MM_DD'>")
   print("<input value='"+str(day.replace("_", "/"))+"' type='text' class='form-control'>")
   print("<span class='input-group-addon'><span class='icon-clock'></span></span></div> by Cam #"+cams_id+"</h1>")
   print("<div><button class='btn btn-primary' id='play_anim_thumb' style='text-transform: initial;'><span class='icon-youtube'></span> All night Animation</button></div></div>") 
  
   print("<div id='main_container' class='container-fluid h-100 mt-4 lg-l'>")
   print("<div class='gallery gal-resize row text-center text-lg-left '>")
 

   for base_file in sorted(day_files,reverse=True):
      if cc + 1 < len(day_files) - 2:
         next_stack_file = all_files[cc+1]
      else:
         next_stack_file = all_files[cc] 
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
      base_js_name = el[-1].split('_')

      html_out =  "<div class='preview col-lg-2 col-md-3 "+ htclass +"'>"
      html_out = html_out + "<a class='mtt mb-3' href='webUI.py?cmd=examine_min&video_file=" + video_file + "&next_stack_file=" + next_stack_file +"&next_stack_file=" + next_stack_file + "' title='Examine'>"
      html_out = html_out + "<img class='ns lz' src='" + stack_file_tn + "'>"
      html_out = html_out + "<span>"+base_js_name[0] +"/" +base_js_name[1]+"/" +base_js_name[2] + " " +  base_js_name[3]+ ":" +  base_js_name[4]+ ":" +  base_js_name[5] +"</span>"
      html_out = html_out + "</a></div>"
      print(html_out) 
      cc = cc + 1

   print('</div></div>')

def browse_detects(day,type,json_conf,form):
   cgitb.enable()

   cur_page  = form.getvalue('p')

   if (cur_page is None) or (cur_page==0):
      cur_page = 1
   else:
      cur_page = int(cur_page)

   
   proc_dir = json_conf['site']['proc_dir']
   failed_files, meteor_files, pending_files,min_files = get_day_stats(day,proc_dir + day + "/", json_conf)
   show_day = day.replace("_", "/")

   title = "<div class='h1_holder d-flex justify-content-between'>"
  
   if type == 'meteor':
      files = meteor_files
      title = title + "<h1>" + format(len(files)) + " Meteor Detections on "+format(show_day)+"</h1>" 
   else:
      files = failed_files
      title = title + "<h1>" + format(len(files)) + " Non-Meteor Detections on " + format(show_day)+"</h1>" 
 
   html_out = "<div id='main_container' class='container-fluid h-100 mt-4 lg-l'>" 
   html_out = html_out + "<div class='gallery gal-resize row text-center text-lg-left'>"

   files = sorted(files, reverse=True)
   _from = (cur_page-1) * NUMBER_OF_METEOR_PER_PAGE
   _to = _from + NUMBER_OF_METEOR_PER_PAGE

   # slice the array for pagination
   real_files   = files[_from:_to] 

   for file in real_files:
      stack_img = file.replace(".mp4", "-stacked.png")
      stack_obj_img = file.replace(".mp4", "-stacked-obj.png")
      el = stack_img.split("/")
      short_name = get_meteor_date(file) 
      base_js_name=short_name.replace("_", "")

      html_out = html_out + "<div class='preview col-lg-2 col-md-3 mb-4 fail'>"
      html_out = html_out + "<a class='mtt' href='webUI.py?cmd=examine&video_file=" + file +"'  title='Examine'>"
      html_out = html_out + "<img alt='" + short_name + "' class='img-fluid ns lz' src='" + stack_img + "'>"
      html_out = html_out + "<span>" + short_name + "</span></a></div>"     
       
   
   html_out = html_out + "</div>"
   pagination =  get_pagination(cur_page,len(files),"/pycgi/webUI.py?cmd=browse_detects&type="+type+"&day="+day,NUMBER_OF_METEOR_PER_PAGE)
   
   print( title + "<div class='page_h'>Page  " + format(cur_page) + "/" +  format(pagination[2]) + "</div></div>")
   print(html_out)
   print(pagination[0])
   print("</div>")



def main_page(json_conf,form):

   cgitb.enable()   
   cur_page  = form.getvalue('p')
   end_day   = form.getvalue('limit_day')

   if (cur_page is None) or (cur_page==0):
      cur_page = 1
   else:
      cur_page = int(cur_page)

   if(end_day is not None):
      end_day_date = datetime.datetime.strptime(end_day,"%Y_%m_%d")
   
   days = sorted(get_proc_days(json_conf),reverse=True)
  
   # We remove the days we don't care about to speed up the page
   if(end_day is not None):
         for idx, d in enumerate(days):
            test_ends_with_int = re.search(r'\d+$', d)
            
            if test_ends_with_int is not None:
                  ddd = get_date_from_file(d) 


   json_file = json_conf['site']['proc_dir'] + "json/" + "main-index.json"
   stats_data = load_json_file(json_file)
  
   detections = sorted(stats_data,reverse=True)
   detections_form = NUMBER_OF_DAYS_PER_PAGE*cur_page
   total_number_page = math.ceil(len(detections) / NUMBER_OF_DAYS_PER_PAGE)
   counter = 0

   to_display = ""
   first_day = ""
   real_detections = []
   real_detections_to_display = []

   # Need a fist loop to cleanup (big waist of time & resources here)
   for idx, day in enumerate(detections): 
         
      #Default day if not defined
      if(end_day is None and idx==0):
         now = datetime.datetime.now()
         end_day_date = now
         end_day = end_day_date.strftime('%Y/%m/%d')

      day_str = day
      day_dir = json_conf['site']['proc_dir'] + day + "/" 

      # Use to compare with end
      day_cur_date = datetime.datetime.strptime(day_str,"%Y_%m_%d")
     
      if "meteor" not in day_dir and "daytime" not in day_dir and "json" not in day_dir and "trash" not in day_dir:
         real_detections.append(day) 

         if(end_day_date >= day_cur_date):
               real_detections_to_display.append(day)
  
   all_real_detections = real_detections

   day_start = (cur_page-1) * NUMBER_OF_DAYS_PER_PAGE
   day_end   = day_start + NUMBER_OF_DAYS_PER_PAGE
   
   # slice the array to just the values you want.
   real_detections = all_real_detections[day_start:day_end] 
   real_detections_to_display_d = real_detections_to_display[day_start:day_end] 
   
   for idx, day in enumerate(real_detections_to_display_d): 
      day_str = day
      day_dir = json_conf['site']['proc_dir'] + day + "/" 
      failed_files = stats_data[day]['failed_files']
      meteor_files = stats_data[day]['meteor_files']
      pending_files = stats_data[day]['pending_files']

      html_row, day_x = make_day_preview(day_dir,stats_data[day], json_conf)
      day_str = day.replace("_", "/")

      to_display  = to_display + "<div class='h2_holder  d-flex justify-content-between'>"
      to_display  = to_display + "<h2>"+day_str+" - <a class='btn btn-primary' href=webUI.py?cmd=meteors&limit_day=" + day + ">" + str(meteor_files) + " Meteors </a></h2>"
      to_display  = to_display + "<p><a href=webUI.py?cmd=browse_detects&type=failed&day=" + day + ">" + str(failed_files) + " Non-Meteors </a>"

      if(pending_files>0):
            to_display  = to_display + " - " + str(pending_files) + " Files Pending</a>"

      to_display  = to_display +"</div><div class='gallery gal-resize row text-center text-lg-left mb-5 mr-3 ml-3'>"
      to_display  = to_display + html_row
      to_display = to_display + "</div>"
      counter = counter + 1
 
   pagination =  get_pagination(cur_page,len(all_real_detections),"/pycgi/webUI.py?cmd=home",NUMBER_OF_DAYS_PER_PAGE)

   header_out = "<div class='h1_holder d-flex justify-content-between'><h1>Daily Dectections until "
   header_out = header_out + "<div class='input-group date datepicker' data-display-format='YYYY/MM/DD' data-action='reload' data-url-param='limit_day' data-send-format='YYYY_MM_DD'>"
   header_out = header_out + "<input value='"+ end_day +"' type='text' class='form-control'>"
   header_out = header_out + "<span class='input-group-addon'><span class='icon-clock'></span></span></div></h1>"
   header_out = header_out + "<div class='page_h'>Page  " + format(cur_page) + "/" +  format(pagination[2]) + "</div></div>" 

   print(header_out)
   print("<div id='main_container' class='container-fluid h-100 mt-4 lg-l'>")
   print(to_display)
   print(pagination[0])
   print("</div>")

def rad_calc(json_conf, form):
   event_date = form.getvalue("event_date")
   start_lon = form.getvalue("start_lon")
   if start_lon is not None:
      start_lon = float(form.getvalue("start_lon"))
      start_lat = float(form.getvalue("start_lat"))
      start_alt = float(form.getvalue("start_alt"))
      end_lon = float(form.getvalue("end_lon"))
      end_lat = float(form.getvalue("end_lat"))
      end_alt = float(form.getvalue("end_alt"))
      velocity= float(form.getvalue("velocity"))
   print("<h1>Meteor Orbit Calculator</h1>" )
   stab,sr,sc,et,er,ec = div_table_vars()

   if start_lon is None:
      print("""
          <form>
            Event Date: <input type=text name=event_date VALUE=YYYY-MM-DD HH:MM:SS> UTC<BR>
            Start Lat: <input type=text name=start_lat><BR>
            Start Lon: <input type=text name=start_lon><BR>
            Start Alt: <input type=text name=start_alt><BR>
            End Lat: <input type=text name=end_lat><BR>
            End Lon: <input type=text name=end_lon><BR>
            End Alt: <input type=text name=end_alt><BR>
            Velocity: <input type=text name=velocity><BR>
            <input type=submit name=submit value="Submit">
            <input type=hidden name=cmd value="rad_calc">
          </form>
      """)
   else:
      arg_date, arg_time = event_date.split(" ")

      rad_rah,rad_dech,rad_az,rad_el,track_dist,entry_angle = calc_radiant(end_lon,end_lat,end_alt,start_lon,start_lat,start_alt, arg_date, arg_time)
      rad_rah = str(rad_rah).replace(":", " ")
      rad_dech = str(rad_dech).replace(":", " ")
      ra,dec = HMS2deg(str(rad_rah),str(rad_dech))

      print("<h3>Input Data</h3>")
      print(stab)
      print(sr + sc + "Event Date" + ec +sc +str(event_date) + ec + er)
      print(sr + sc + "Start Point" + ec + sc + str(start_lon) + "," + str(start_lat) + "," + str(start_alt) + ec + er)
      print(sr + sc + "End Point" + ec + sc + str(end_lon) + "," + str(end_lat) + "," + str(end_alt) + ec + er)
      print(sr + sc + "Velocity" + ec + sc + str(velocity) + ec + er)
      print(et)

      print("<h3>Preprocess Input Data and get ready for Orbit</h3>")
      print("<h3>Determine Radiant Az, El, RA, Dec</h3>")
      #print("<h4>Step 1 - Determine 0KM and 80KM altitude end and start points</h4>")
      #print(stab)
      #print(sr + sc + "0KM Point" + ec + sc + str(zero_lon) + "," + str(zero_lat) + "," +  str(0) + ec + er)
      #print(sr + sc + "80KM Point" + ec + sc + str(hund_lon) + "," + str(hund_lat) + "," +  str(80) + ec + er)
      #print(et)
      print("<h4>Step 2 - Determine track distance and entry angle</h4>")
      print("<h5>Step 2a - Use haversine between end and start lat,lon,alt points to determine track ground length and radiant azimuth from the 0KM point</h5>")
      print(stab)
      print(sr + sc + "Track Distance" + ec + sc + str(track_dist) + ec + er)
      print(sr + sc + "Radiant AZ" + ec + sc + str(rad_az) + ec + er)
      print(et)
      print("<h5>Step 2b - To determine entry angle. Use pythagorian theorum to compute ground track distance between 0km and 80km longitude and latitude points. </h5>")
      print(stab)
      print(sr + sc + "Entry Angle (Radiant Elevation)" + ec + sc + str(entry_angle) + ec + er)
      print(et)

      print("<h4>Step 3 Convert Az,El to RA,Dec using pyehem and HMS2Deg</h4>")
      print(stab)
      print(sr + sc + "Radiant RA (HMS)" + str(rad_rah) + ec + er)
      print(sr + sc + "Radiant Dec (DMS)" + str(rad_dech) + ec + er)
      print(sr + sc + "Radiant RA " + str(ra) + ec + er)
      print(sr + sc + "Radiant Dec " + str(dec) + ec + er)
      print(et)

      # run orbit
      metorb = load_json_file("/home/ams/amscams/pythonv2/orbits/orbit-vars.json")
      event_start_time = event_date.replace(" ", "T")
      metorb['orbit_vars']['meteor_input']['start_time'] = event_start_time
      metorb['orbit_vars']['meteor_input']['end_point'] = [end_lon,end_lat,end_alt]
      metorb['orbit_vars']['meteor_input']['rad_az'] = rad_az
      metorb['orbit_vars']['meteor_input']['rad_el'] = entry_angle 
      metorb['orbit_vars']['meteor_input']['velocity'] = velocity

      save_json_file("/home/ams/amscams/pythonv2/orbits/orbit-vars.json",metorb)
      os.system("cd /home/ams/amscams/pythonv2/; ./mikeOrb.py > /dev/null")  
      time.sleep(1)
      new_metorb = load_json_file("/home/ams/amscams/pythonv2/orbits/orbit-vars.json")

      metorb = new_metorb
      #parsed = json.dumps(new_metorb)
      #parsed = json.loads(new_parsed)
      print("<h1>Orbit Calculation Steps</h1>")
      print("<h2>Step 1 : Determine Observed Radiant Sidereal Time, Hour Angle, RA,Dec & J2000 RA & Dec</h2>")
      print("<h2>Step 1a : Calculate JD from input UTC date</h2>")
      print(stab)
      print(sr + sc +"Event Time UTC " + ec + sc + str(metorb['orbit_vars']['date_vars']['event_time_utc']) + ec + er)
      print(sr + sc +"Julian Date For Time of Event" + ec + sc + str(metorb['orbit_vars']['date_vars']['jd_at_t']) + ec + er)
      print(et)
      print("<h2>Step 1b : Calculate T, Theta Rad & Maal3650 from the event JD </h2>")
      print(stab)
      print(sr + sc + "T" + ec + sc + str(metorb['orbit_vars']['date_vars']['T']) + ec + sc + "(JD-2451545)/36525" + ec +  er)
      theta_rad_formula = "(280.46061837+360.98564736629*(JD_AT_T-2451545)+((0.000387933*(T^2))-(T^3/38710000)))"
      print(sr + sc + "theta_rad" + ec + sc + str(metorb['orbit_vars']['date_vars']['theta_rad']) + ec + sc + theta_rad_formula + ec + er)

      print(sr + sc + "maal_360" + ec + sc + str(metorb['orbit_vars']['date_vars']['maal_360']) + ec + sc + "theta_rad/360" + ec +er)
      print(et)
      print("<h2>Step 1c : Calculate Greenwich Sidreal time & Local Sidereal Time</h2>")
      greenwich_formula = "theta_rad - (maal_360 * 360)"
      print(sr + sc + "Greenwich Sidereal" + ec + sc + str(metorb['orbit_vars']['date_vars']['greenwich_sidereal_time']) + ec + sc + greenwich_formula + ec +er)
      local_sr_formula = "impact longitude + greenwhich_sidereal"
      print(sr + sc + "Impact Point Sidereal " + ec + sc + str(metorb['orbit_vars']['date_vars']['local_sidereal_time_deg']) + ec + sc + local_sr_formula + ec +er)
      print("<h2>Step 1d : Calculate Hour Angle </h2>")
      print(stab)
      print(sr + sc + "Hour Angle " + ec + sc + str(metorb['orbit_vars']['date_vars']['local_sidereal_hour_angle']) + ec + sc + "" + ec +er)
      print(et)
      print("<h2>Step 1e : Calc Radiant RA/DEC</h2>")
      print(stab)
      print(sr + sc + "Observed Radiant RA " + ec + sc + str(metorb['orbit_vars']['radiants']['observed_radiant_position']['rad_ra']) + ec + sc + "" + ec +er)
      print(sr + sc + "Observed Radiant Dec " + ec + sc + str(metorb['orbit_vars']['radiants']['observed_radiant_position']['rad_dec']) + ec + sc + "" + ec +er)
      print(et)
      print("<h2>Step 1f : Calc Radiant J2000 RA/DEC</h2>")
      print(stab)
      print(sr + sc + "J2000 Observed Radiant RA " + ec + sc + str(metorb['orbit_vars']['radiants']['observed_radiant_position']['rad_raJ2']) + ec + sc + "" + ec +er)
      print(sr + sc + "J2000 Observed Radiant Dec " + ec + sc + str(metorb['orbit_vars']['radiants']['observed_radiant_position']['rad_decJ2']) + ec + sc + "" + ec +er)
      print(et)
      print("<h2>Part 2 : Convert Observed Radiant Position Geocentric Radiant Position</h2>")
      print("<h2>Step 1 : Compute Zenith Attraction, apparent radiant altitude, true radiant altitude</h2>")
      print("<h2>Step 2 : Compute Geocentric Hour Angle</h2>")
      print("<PRE><font color=white>")
      print(json.dumps( new_metorb, indent=4))
